"""Readable search phrases and dictionary-based word matching (no character grams)."""
import logging
import re
from collections import Counter
from functools import lru_cache

import jieba
import jieba.posseg


STOP_WORDS = frozenset("""
一个 一些 一种 一次 一起 一般 不同 不能 不会 不要 不是 不用 不足 不到 不了
什么 为什么 怎么 怎么样 如何 是否 可以 应该 需要 能够 可能 已经 进行 使用
用户 问题 方法 分析 解决 处理 相关 情况 场景 方面 内容 资料 知识 参考 说明
自己 他人 别人 他们 大家 这个 那个 这些 那些 这样 那样 时候 当前 今天 最近
希望 想要 知道 觉得 认为 出现 存在 例如 比如 主要 核心 通过 以及 因为 所以
帮助 建议 理解 解释 判断 考虑 特别 真正 结束 开始 完成 正文 标题
人们 看似 不合理 设计 评估 专业 试图 公司 企业
激活 典型 触发 信号 适用 例子
the and for with from this that when where how why what can could would should
skill skills trigger triggers application boundary reading interpretation execution
""".split())

# These words provide context but do not identify a knowledge topic on their own.
SUPPORT_WORDS = frozenset("""
失败 成功 成本 风险 情绪 压力 心理 计划 状态 长期 短期 时间 指标 目标
执行 结果 效果 变化 改变 错误 困难 原因 过程 提前 痛苦 重要 failure risk stress
""".split())


def meaningful(value):
    value = value.strip().lower()
    return (2 <= len(value) <= 48 and value not in STOP_WORDS
            and bool(re.search(r"[a-z\u3400-\u9fff]", value))
            and not re.fullmatch(r"(?:v\d+(?:[._-]\d+)*|[a-z]\d+)", value)
            and not re.search(r"https?://|\d{4}[-/]\d{1,2}[-/]\d{1,2}", value))


@lru_cache(maxsize=1)
def tokenizer():
    jieba.setLogLevel(logging.WARNING)
    return jieba.posseg.POSTokenizer(jieba.Tokenizer())


@lru_cache(maxsize=2048)
def terms(text):
    """Keep whole dictionary words, skipping particles, numbers and generic words."""
    result = set()
    for token in tokenizer().cut(text.lower(), HMM=False):
        if token.flag.startswith(("n", "v", "a")) or token.flag == "eng":
            if meaningful(token.word):
                result.add(token.word)
    return frozenset(result)


def field_list(header, name):
    """Read scalar, inline-list or simple indented-list metadata without splitting words."""
    match = re.search(r"^" + re.escape(name) + r":[ \t]*([^\n]*)", header, re.MULTILINE)
    if not match:
        return []
    value = match.group(1).strip()
    if not value:
        values = []
        for line in header[match.end():].splitlines():
            if line and not line[0].isspace():
                break
            item = re.match(r"\s+-\s+(.+)", line)
            if item:
                values.append(item.group(1).strip())
    else:
        # Quoted phrases may contain commas; only unquoted delimiters split items.
        values = re.findall(r'''"[^"]*"|'[^']*'|[^,，;；\[\]]+''', value)
    return [item.strip().strip("\"'") for item in values if item.strip()]


def positive_description(text):
    return re.split(r"不适用于|不适用场景|不适用：|不适用:|不用于", text, maxsplit=1)[0]


def metadata_keywords(header, title, description):
    keywords = []

    def add(value):
        value = value.strip().lower()
        if meaningful(value) and value not in keywords and len(keywords) < 16:
            keywords.append(value)

    for field in ("keywords", "tags", "triggers"):
        for value in field_list(header, field):
            # Longer scenarios belong in triggers; do not turn sentences into keywords.
            if len(value) <= 20 and not re.search(r"[，。！？,!?]", value):
                add(value)
    # Some imported descriptions contain a slash-separated Triggers section.
    positive = positive_description(description)
    inline = re.search(r"\bTriggers?\s*[:：]\s*([^。\n]+)", positive, re.IGNORECASE)
    if inline:
        for value in re.split(r"[/、;；]", inline.group(1)):
            add(value)
    for value in sorted(terms(title)):
        add(value)
    if len(keywords) >= 4:
        return keywords
    # Prefer words repeated across sentences; tie-break by first appearance.
    words = []
    for sentence in re.split(r"[。！？；\n]", positive):
        words.extend(sorted(terms(sentence)))
    frequencies = Counter(words)
    for value in sorted(frequencies, key=lambda word: (-frequencies[word], positive.lower().find(word), word)):
        add(value)
    return keywords


@lru_cache(maxsize=512)
def word_boundaries(text):
    boundaries, offset = {0}, 0
    for token in tokenizer().cut(text, HMM=False):
        offset += len(token.word)
        boundaries.add(offset)
    return frozenset(boundaries)


def phrase_in_text(phrase, text):
    """Match complete words/phrases, not 数据 inside 数据库 or valuation inside evaluation."""
    phrase, text = phrase.lower(), text.lower()
    if re.search(r"[a-z]", phrase):
        return bool(re.search(r"(?<![a-z0-9_-])" + re.escape(phrase) + r"(?![a-z0-9_-])", text))
    if not phrase or phrase not in text:
        return False
    boundaries = word_boundaries(text)
    return any(match.start() in boundaries and match.end() in boundaries
               for match in re.finditer(re.escape(phrase), text))
