"""待执行的核心回归测试；不请求网络、不调用真实模型。"""
import tempfile
import unittest
from pathlib import Path

from app.config import Settings
from app.github import ServiceError, allowed_path, parse_repository
from app.rag import RAG, chunk_file, tokens
from app.store import Store


class CoreTests(unittest.TestCase):
    def test_repository_url_is_restricted(self):
        self.assertEqual(parse_repository("https://github.com/XRH-RGB/zhengli.git"), "XRH-RGB/zhengli")
        for bad in ["http://github.com/a/b", "https://github.com.evil/a/b", "https://github.com/a/b/tree/main", "https://github.com/a/b?x=1"]:
            with self.assertRaises(ServiceError):
                parse_repository(bad)

    def test_root_glob_and_secret_exclusion(self):
        self.assertTrue(allowed_path("README.md", ["**/*.md"]))
        self.assertTrue(allowed_path("docs/制度.md", ["**/*.md"]))
        self.assertFalse(allowed_path(".env.json", ["**/*.json"]))
        self.assertFalse(allowed_path("node_modules/a/index.py", ["**/*.py"]))
        self.assertFalse(allowed_path("image.png", ["**/*"]))

    def test_chunking_covers_long_lines_without_losing_text(self):
        text = "知识库说明\n" + "a" * 900 + "\n最后一行"
        chunks = list(chunk_file({"url": "https://github.com/a/b/blob/sha/doc.md", "path": "doc.md", "text": text}, 300, 40))
        self.assertGreater(len(chunks), 3)
        self.assertEqual(chunks[0]["start_line"], 1)
        self.assertEqual(chunks[-1]["end_line"], 3)
        self.assertTrue(all(len(c["text"]) <= 300 for c in chunks))
        self.assertIn("最后一行", chunks[-1]["text"])

    def test_chinese_tokens_include_bigrams(self):
        self.assertIn("知识", tokens("知识库 RAG_CONFIG"))
        self.assertIn("rag_config", tokens("知识库 RAG_CONFIG"))

    def test_failed_snapshot_rolls_back_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.sqlite3")
            store.initialize()
            store.add_repository("r", "https://github.com/a/b", "", ["**/*.md"])
            chunk = {"id": "c1", "path": "a.md", "start_line": 1, "end_line": 1,
                     "text": "旧内容", "url": "https://github.com/a/b/blob/sha/a.md#L1", "vector": [1.0]}
            store.replace_index("r", "old", "model", 1, [chunk])
            import sqlite3
            with self.assertRaises(sqlite3.IntegrityError):
                store.replace_index("r", "new", "model", 2, [chunk, chunk])
            self.assertEqual(store.repository("r")["commit_sha"], "old")
            self.assertEqual(store.chunks(["r"])[0]["text"], "旧内容")

    def test_model_change_fails_before_embedding(self):
        class FakeModels:
            signature = "new"
            def embed(self, texts):
                raise AssertionError("不应调用嵌入")
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.sqlite3")
            store.initialize()
            store.add_repository("r", "https://github.com/a/b", "", ["**/*.md"])
            store.replace_index("r", "sha", "old", 0, [])
            rag = RAG(Settings(_env_file=None), store, None, FakeModels())
            with self.assertRaisesRegex(ServiceError, "嵌入模型配置已改变"):
                rag.retrieve("问题", ["r"], 4)


if __name__ == "__main__":
    unittest.main()
