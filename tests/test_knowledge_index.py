import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from knowledge_context import KnowledgeContext


class KnowledgeIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.context = KnowledgeContext(self.root, max_items=1)

    def tearDown(self):
        self.temp.cleanup()

    def note(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def track_reads(self, action):
        reads = []
        original = Path.read_text

        def read(path, *args, **kwargs):
            if path.suffix == ".md":
                reads.append(path.name)
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", read):
            result = action()
        return result, reads

    def test_persistent_index_avoids_unchanged_bodies_and_loads_only_selected(self):
        self.note("risk.md", "---\ndescription: 止损纪律\n---\n# 止损\n严格执行规则")
        self.note("food.md", "---\ndescription: 厨房菜谱\n---\n# 烹饪\n清蒸鱼")
        _, reads = self.track_reads(self.context.read_entries)
        self.assertCountEqual(reads, ["risk.md", "food.md"])
        index = self.root / "registry.json"
        before = index.stat().st_mtime_ns
        # A fresh instance must use the on-disk index, not an in-process body cache.
        fresh = KnowledgeContext(self.root, max_items=1)
        entries, reads = self.track_reads(fresh.read_entries)
        self.assertEqual(len(entries), 2)
        self.assertEqual(reads, [])
        prompt, reads = self.track_reads(lambda: fresh.build("止损"))
        self.assertEqual(reads, ["risk.md"])
        self.assertIn("严格执行规则", prompt)
        self.assertNotIn("清蒸鱼", prompt)
        self.assertEqual(index.stat().st_mtime_ns, before)

    def test_incremental_edits_additions_deletions_and_renames(self):
        first = self.note("one.md", "# 第一条\n旧资料")
        second = self.note("two.md", "# 第二条\n其他资料")
        self.context.read_entries()
        first.write_text("# 第一条\n更新后的资料更长", encoding="utf-8")
        _, reads = self.track_reads(self.context.read_entries)
        self.assertEqual(reads, ["one.md"])
        self.note("new.md", "# 新增\n新增资料")
        _, reads = self.track_reads(self.context.read_entries)
        self.assertEqual(reads, ["new.md"])
        second.unlink()
        first.rename(self.root / "renamed.md")
        entries, reads = self.track_reads(self.context.read_entries)
        self.assertEqual(reads, ["renamed.md"])
        self.assertEqual({entry.path for entry in entries}, {"new.md", "renamed.md"})
        document = json.loads((self.root / "registry.json").read_text(encoding="utf-8"))
        self.assertEqual(set(document["entries"]), {"new.md", "renamed.md"})

    def test_registry_upgrade_preserves_sources_and_corruption_rebuilds(self):
        self.note("note.md", "# 知识\n参考资料")
        index = self.root / "registry.json"
        index.write_text(json.dumps({"packs": [{"id": "book", "source": "local", "skills": ["note"]}]}), encoding="utf-8")
        self.context.read_entries()
        document = json.loads(index.read_text(encoding="utf-8"))
        self.assertEqual(document["sources"], [{"id": "book", "source": "local"}])
        self.assertIn("note.md", document["entries"])
        index.write_text("{unfinished", encoding="utf-8")
        with self.assertLogs("knowledge_context", level="WARNING"):
            entries, reads = self.track_reads(self.context.read_entries)
        self.assertEqual(len(entries), 1)
        self.assertEqual(reads, ["note.md"])
        json.loads(index.read_text(encoding="utf-8"))
        index.unlink()
        entries, reads = self.track_reads(self.context.read_entries)
        self.assertEqual(reads, ["note.md"])
        self.assertEqual(len(entries), 1)

    def test_duplicate_becomes_available_when_original_deleted(self):
        original = self.note("a.md", "# 重复知识\n同一份正文")
        self.note("b.md", "# 重复知识\n同一份正文 \n")
        self.assertEqual([e.path for e in self.context.read_entries()], ["a.md"])
        original.unlink()
        entries, reads = self.track_reads(self.context.read_entries)
        self.assertEqual([e.path for e in entries], ["b.md"])
        self.assertEqual(reads, [])

    def test_read_only_location_falls_back_to_memory_index(self):
        self.note("note.md", "# 知识\n参考资料")
        with patch("knowledge_context.os.replace", side_effect=PermissionError("read only")):
            with self.assertLogs("knowledge_context", level="WARNING"):
                self.assertEqual(len(self.context.read_entries()), 1)
        entries, reads = self.track_reads(self.context.read_entries)
        self.assertEqual(len(entries), 1)
        self.assertEqual(reads, [])
        self.assertEqual(list(self.root.glob(".registry-*.tmp")), [])
