import base64
import fnmatch
import re
from pathlib import PurePosixPath
from urllib.parse import quote, urlsplit

import httpx


class ServiceError(Exception):
    """可安全显示给用户的业务错误。"""


def parse_repository(url: str) -> str:
    parsed = urlsplit(url.strip())
    parts = parsed.path.strip("/").removesuffix(".git").split("/")
    if (parsed.scheme != "https" or parsed.netloc != "github.com" or
            parsed.query or parsed.fragment or len(parts) != 2 or
            any(not re.fullmatch(r"[A-Za-z0-9_.-]+", p) or p in {".", ".."} for p in parts)):
        raise ServiceError("请填写 https://github.com/所有者/仓库 格式的地址。")
    return "/".join(parts)


def allowed_path(path: str, patterns: list[str]) -> bool:
    parts = PurePosixPath(path).parts
    blocked = {".git", ".github", "node_modules", ".venv", "venv", "__pycache__", "data"}
    if any(p in blocked or p.startswith(".env") for p in parts):
        return False
    if PurePosixPath(path).suffix.lower() not in {".md", ".txt", ".rst", ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".json", ".yaml", ".yml", ".toml"}:
        return False
    return any(fnmatch.fnmatchcase(path, p) or
               (p.startswith("**/") and fnmatch.fnmatchcase(path, p[3:])) for p in patterns)


class GitHubSource:
    def __init__(self, settings):
        self.settings = settings

    def snapshot(self, repository):
        settings = self.settings
        name = parse_repository(repository["url"])
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        # 主机固定，拒绝重定向，不下载压缩包，也不检出或执行仓库代码。
        with httpx.Client(base_url="https://api.github.com", headers=headers,
                          timeout=settings.request_timeout, follow_redirects=False) as client:
            def get(path):
                response = client.get(path)
                if response.status_code != 200:
                    raise ServiceError(f"GitHub 读取失败（HTTP {response.status_code}），请检查仓库、分支、令牌和限流。")
                return response.json()

            branch = repository["branch"] or get(f"/repos/{name}")["default_branch"]
            commit = get(f"/repos/{name}/commits/{quote(branch, safe='')}")
            sha = commit["sha"]
            tree_sha = commit["commit"]["tree"]["sha"]
            tree = get(f"/repos/{name}/git/trees/{tree_sha}?recursive=1")
            if tree.get("truncated"):
                raise ServiceError("仓库目录过大，GitHub 返回了截断结果。请使用较小的知识仓库；旧索引已保留。")
            entries = [e for e in tree["tree"] if e["type"] == "blob" and
                       e.get("mode") in {"100644", "100755"} and
                       allowed_path(e["path"], repository["include_globs"])]
            if len(entries) > settings.max_files:
                raise ServiceError(f"匹配文件超过 {settings.max_files} 个，请缩小文件匹配范围。")
            files, skipped = [], []
            for entry in entries:
                if entry.get("size", 0) > settings.max_file_bytes:
                    skipped.append({"path": entry["path"], "reason": "超过文件大小上限"})
                    continue
                blob = get(f"/repos/{name}/git/blobs/{entry['sha']}")
                if blob.get("encoding") != "base64":
                    raise ServiceError("GitHub 返回了不支持的文件编码。")
                raw = base64.b64decode(blob["content"])
                if len(raw) > settings.max_file_bytes:
                    skipped.append({"path": entry["path"], "reason": "超过文件大小上限"})
                    continue
                try:
                    content = raw.decode("utf-8-sig")
                except UnicodeDecodeError:
                    skipped.append({"path": entry["path"], "reason": "非 UTF-8 文本"})
                    continue
                if "\x00" in content or content.startswith("version https://git-lfs.github.com/spec/"):
                    skipped.append({"path": entry["path"], "reason": "二进制或 Git LFS 指针"})
                    continue
                files.append({"path": entry["path"], "text": content,
                              "url": f"https://github.com/{name}/blob/{sha}/{quote(entry['path'], safe='/')}"})
        return {"commit": sha, "files": files, "skipped": skipped}
