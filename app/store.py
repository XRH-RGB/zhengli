import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id TEXT PRIMARY KEY, url TEXT NOT NULL, branch TEXT NOT NULL,
                    include_globs TEXT NOT NULL, commit_sha TEXT,
                    embedding_signature TEXT, indexed_at TEXT, file_count INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY, repository_id TEXT NOT NULL
                    REFERENCES repositories(id) ON DELETE CASCADE,
                    path TEXT NOT NULL, start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL, text TEXT NOT NULL,
                    url TEXT NOT NULL, vector TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS chunks_repository ON chunks(repository_id);
            """)

    def repositories(self):
        with self.connect() as db:
            rows = db.execute("""SELECT r.*, COUNT(c.id) AS chunk_count
                FROM repositories r LEFT JOIN chunks c ON c.repository_id=r.id
                GROUP BY r.id ORDER BY r.id""").fetchall()
        return [{**dict(row), "include_globs": json.loads(row["include_globs"])} for row in rows]

    def repository(self, repository_id):
        return next((r for r in self.repositories() if r["id"] == repository_id), None)

    def add_repository(self, repository_id, url, branch, include_globs):
        with self.connect() as db:
            db.execute("INSERT INTO repositories(id,url,branch,include_globs) VALUES(?,?,?,?)",
                       (repository_id, url, branch, json.dumps(include_globs)))

    def delete_repository(self, repository_id):
        with self.connect() as db:
            db.execute("DELETE FROM repositories WHERE id=?", (repository_id,))

    def replace_index(self, repository_id, commit, signature, file_count, chunks):
        # 一个事务替换完整快照；网络或嵌入失败不会删除旧索引。
        with self.connect() as db:
            db.execute("DELETE FROM chunks WHERE repository_id=?", (repository_id,))
            db.executemany("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?)", [
                (c["id"], repository_id, c["path"], c["start_line"], c["end_line"],
                 c["text"], c["url"], json.dumps(c["vector"])) for c in chunks
            ])
            db.execute("""UPDATE repositories SET commit_sha=?, embedding_signature=?,
                indexed_at=?, file_count=? WHERE id=?""",
                       (commit, signature, now(), file_count, repository_id))

    def chunks(self, repository_ids):
        if not repository_ids:
            return []
        placeholders = ",".join("?" for _ in repository_ids)
        with self.connect() as db:
            rows = db.execute(f"SELECT * FROM chunks WHERE repository_id IN ({placeholders})",
                              repository_ids).fetchall()
        return [{**dict(row), "vector": json.loads(row["vector"])} for row in rows]
