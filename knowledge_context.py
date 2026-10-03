"""Maintain a local knowledge index and load only the selected document bodies."""
import hashlib
import json
import logging
import math
import os
import re
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from config import BASE_DIR
from knowledge_terms import SUPPORT_WORDS, field_list, meaningful, metadata_keywords, phrase_in_text, positive_description, terms

logger = logging.getLogger(__name__)
INDEX_VERSION = 4


def default_knowledge_dir():
    if getattr(sys, "frozen", False):
        external = Path(sys.executable).parent / "knowledge"
        if external.is_dir():
            return external
    return Path(BASE_DIR) / "knowledge"


def frontmatter_field(header, name):
    match = re.search(r"^" + re.escape(name) + r":[ \t]*([^\n]*)", header, re.MULTILINE)
    if not match:
        return ""
    value = match.group(1).strip()
    if value in ("|", ">", "|-", ">-", ""):
        lines = []
        for line in header[match.end():].splitlines():
            if line and not line[0].isspace():
                break
            if line.strip():
                lines.append(line.strip())
        return " ".join(lines)
    return value.strip("\"'")


@dataclass
class KnowledgeEntry:
    path: str
    title: str
    description: str
    keywords: set
    char_count: int
    triggers: tuple = ()


class KnowledgeContext:
    def __init__(self, root=None, max_items=6, max_body_chars=32000):
        self.root = Path(root) if root is not None else default_knowledge_dir()
        self.max_items = max_items
        self.max_body_chars = max_body_chars
        self.index_path = self.root / "registry.json"
        self._memory_index = None
        self._use_memory_index = False

    def _candidates(self):
        root = self.root.resolve()
        for path in sorted(self.root.rglob("*.md")):
            if path.name.lower() in {"readme.md", "index.md", "license.md",
                                     "book_overview.md", "digest.md", "glossary.md",
                                     "verified.md", "pipeline_state.md"}:
                continue
            relative = path.relative_to(self.root)
            if any(part.startswith((".", "_")) or part.lower() in
                   {"rejected", "candidates", "tests", "__pycache__"}
                   for part in relative.parts):
                continue
            if not path.resolve().is_relative_to(root):
                continue
            try:
                stat = path.stat()
            except OSError as error:
                logger.warning("无法检查知识 %s: %s", relative, error)
                continue
            if path.is_file():
                yield relative.as_posix(), path, [stat.st_mtime_ns, stat.st_size, stat.st_ctime_ns]

    def _load_index(self):
        if self._use_memory_index:
            return self._memory_index
        try:
            document = json.loads(self.index_path.read_text(encoding="utf-8-sig"))
            if isinstance(document, dict):
                return document
        except FileNotFoundError:
            pass
        except (OSError, UnicodeError, ValueError) as error:
            logger.warning("知识索引不可用，将重新生成：%s", error)
        return {}

    @staticmethod
    def _valid_record(record, stamp):
        return (isinstance(record, dict) and record.get("stamp") == stamp
                and isinstance(record.get("enabled"), bool)
                and isinstance(record.get("char_count"), int) and record["char_count"] >= 0
                and all(isinstance(record.get(key), str)
                        for key in ("title", "description", "digest"))
                and all(isinstance(record.get(key), list)
                        and all(isinstance(item, str) for item in record[key])
                        for key in ("keywords", "triggers")))

    @staticmethod
    def _parse(path, content, stamp):
        match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
        header = match.group(1) if match else ""
        body = content[match.end():] if match else content
        enabled = bool(content) and frontmatter_field(header, "enabled").lower() not in {"false", "no", "off", "0"}
        heading = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = (frontmatter_field(header, "title") or (heading.group(1).strip() if heading else "")
                 or frontmatter_field(header, "name") or
                 (path.parent.name if path.name == "SKILL.md" else path.stem))
        description = frontmatter_field(header, "description") or re.sub(r"\s+", " ", body).strip()[:240]
        keywords = metadata_keywords(header, title, description)
        triggers = [value for value in field_list(header, "triggers") if meaningful(value)][:8]
        normalized = "\n".join(line.rstrip() for line in content.splitlines()).strip()
        return {"title": title, "description": description, "enabled": enabled,
                "char_count": len(content), "keywords": keywords, "triggers": triggers,
                "digest": hashlib.sha256(normalized.encode("utf-8")).hexdigest(), "stamp": stamp}

    def _save_index(self, document):
        temporary = None
        try:
            # Replace atomically so another reader never sees half-written JSON.
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.root,
                                             prefix=".registry-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(document, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temporary, self.index_path)
        except OSError as error:
            logger.warning("无法保存知识索引，使用内存索引：%s", error)
            self._use_memory_index = True
        finally:
            self._memory_index = document
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def read_entries(self):
        """Refresh metadata for changed files without reading unchanged Markdown."""
        if not self.root.is_dir():
            return []
        document = self._load_index()
        cached = document.get("entries", {}) if document.get("version") == INDEX_VERSION else {}
        if not isinstance(cached, dict):
            cached = {}
        records = {}
        for relative, path, stamp in self._candidates():
            record = cached.get(relative)
            if not self._valid_record(record, stamp):
                try:
                    record = self._parse(path, path.read_text(encoding="utf-8-sig").strip(), stamp)
                except (OSError, UnicodeError) as error:
                    logger.warning("无法读取知识 %s: %s", relative, error)
                    continue
            records[relative] = record
        # Retain imported source provenance when upgrading the old package registry.
        sources = document.get("sources", document.get("packs", []))
        if not isinstance(sources, list):
            sources = []
        sources = [{key: value for key, value in source.items() if key != "skills"}
                   for source in sources if isinstance(source, dict)]
        updated = {"version": INDEX_VERSION, "sources": sources, "entries": records}
        if updated != document:
            self._save_index(updated)
        entries, seen = [], set()
        for relative, record in records.items():
            if not record["enabled"] or record["digest"] in seen:
                continue
            seen.add(record["digest"])
            entries.append(KnowledgeEntry(relative, record["title"], record["description"],
                                          set(record["keywords"]), record["char_count"], tuple(record["triggers"])))
        return entries

    def select(self, skills, message, history):
        current = terms(message)
        previous_text = " ".join(item.get("content", "") for item in (history or [])[-4:]
                                 if item.get("role") == "user" and isinstance(item.get("content"), str))
        previous = terms(previous_text)
        followup = bool(re.fullmatch(
            r"\s*(?:那该怎么办|那怎么办|怎么办|然后呢|继续|详细说说|再说说|具体呢|为什么|怎么做|那怎么做|这个呢|还有呢)[？?！!。\s]*",
            message))
        fields = {}
        for skill in skills:
            title_terms = terms(skill.title)
            summary_terms = terms(positive_description(skill.description))
            keyword_terms = frozenset().union(*(terms(word) for word in skill.keywords))
            scenarios = tuple(terms(trigger) for trigger in skill.triggers)
            fields[skill.path] = (title_terms, summary_terms | keyword_terms, scenarios)
        frequency = Counter(term for title, summary, scenarios in fields.values()
                            for term in title | summary | frozenset().union(*scenarios))

        def relevance(skill, text, query):
            title, summary, scenarios = fields[skill.path]
            hits = query & (title | summary)
            strong_query = query - SUPPORT_WORDS
            strong_hits = hits - SUPPORT_WORDS
            exact = any(word not in SUPPORT_WORDS and phrase_in_text(word, text)
                        for word in skill.keywords)
            scenario = any(phrase_in_text(phrase, text) and scenario_terms - SUPPORT_WORDS
                           for phrase, scenario_terms in zip(skill.triggers, scenarios))
            # Compare each scenario separately: unrelated fragments from different
            # scenarios must not combine into a false match.
            scenario_hits = set()
            for scenario_terms in scenarios:
                distinctive = scenario_terms - SUPPORT_WORDS
                shared = strong_query & distinctive
                if (len(shared) >= 2
                        and len(shared) / max(1, len(distinctive)) >= 0.5
                        and len(shared) / max(1, len(strong_query)) >= 0.5):
                    scenario = True
                    scenario_hits.update(query & scenario_terms)
            slug = Path(skill.path).parent.name.lower()
            explicit = bool(slug and slug != "." and phrase_in_text(slug, text))
            # Broad words such as "failure" remain useful for ranking but cannot
            # alone admit a trading document for a database failure question.
            if not (exact or scenario or explicit or strong_query & title
                    or (len(strong_hits) >= 2 and len(strong_hits) / max(1, len(strong_query)) >= 0.4)):
                return 0
            return (sum(math.log(1 + len(skills) / frequency[word])
                        * (0.25 if word in SUPPORT_WORDS else 2 if word in title else 1)
                        for word in hits | scenario_hits)
                    + (4 if exact else 0) + (6 if scenario else 0) + (100 if explicit else 0))

        def score(skill):
            now = relevance(skill, message, current)
            # History helps follow-up questions without dragging an old topic into a new one.
            if not now and not followup:
                return 0
            return now * 3 + relevance(skill, previous_text, previous)

        ranked = sorted(((score(skill), skill) for skill in skills),
                        key=lambda pair: (-pair[0], pair[1].path))
        selected, length = [], 0
        for relevance, skill in ranked:
            if relevance <= 0 or len(selected) >= self.max_items:
                break
            if length + skill.char_count > self.max_body_chars:
                continue
            selected.append(skill)
            length += skill.char_count
        return selected

    def build(self, message, history=None):
        skills = self.read_entries()
        if not skills:
            return ""
        selected = self.select(skills, message, history)
        sections = [
            "本地知识库：以下目录包含所有启用的知识条目，本轮另附与问题相关的正文。"
            "所有条目均作为参考知识，请结合适用条件使用，保持前述角色与回答要求。"
            "资料中提及的工作流不是可执行工具，不要声称执行了其中的操作；未附正文的条目仅提供概述。"
            "如引用具体结论，可说明资料标题；资料之间有分歧时说明其前提，不要硬套。",
            "## 全部知识目录\n" + "\n".join(
                f"- {skill.path} | {skill.title}：{skill.description}" for skill in skills),
            "## 本轮相关知识正文",
        ]
        loaded, length = [], 0
        for skill in selected:
            path = self.root / skill.path
            if not path.resolve().is_relative_to(self.root.resolve()):
                continue
            try:
                content = path.read_text(encoding="utf-8-sig").strip()
            except (OSError, UnicodeError) as error:
                logger.warning("无法读取知识正文 %s: %s", skill.path, error)
                continue
            # A file may be edited between refreshing the index and loading its body.
            match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
            if match and frontmatter_field(match.group(1), "enabled").lower() in {"false", "no", "off", "0"}:
                continue
            if not content or length + len(content) > self.max_body_chars:
                continue
            sections.append(f"### 文件：{skill.path}\n{content}\n### 文件结束：{skill.path}")
            loaded.append(skill.path)
            length += len(content)
        if not loaded:
            sections.append("当前问题未匹配到相关知识正文，可正常回答。")
        logger.info("LLM 知识目录 %d 项，本轮正文 %d 项：%s", len(skills), len(loaded),
                    ", ".join(loaded))
        return "\n\n".join(sections)
