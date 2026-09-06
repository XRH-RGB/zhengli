import secrets
import threading
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .config import ROOT, Settings
from .github import GitHubSource, ServiceError, parse_repository
from .models import ModelClient
from .rag import RAG
from .store import Store
from .workflows import WORKFLOWS, catalog


@asynccontextmanager
async def lifespan(application):
    settings = Settings()
    store = Store(settings.database_path)
    store.initialize()
    application.state.settings = settings
    application.state.store = store
    application.state.rag = RAG(settings, store, GitHubSource(settings), ModelClient(settings))
    application.state.execution_lock = threading.Lock()
    yield


app = FastAPI(title="智枢 OmniHub RAG", version="1.0.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(ServiceError)
async def business_error(request, error):
    return JSONResponse(status_code=400, content={"detail": str(error)})


@app.exception_handler(httpx.HTTPError)
async def network_error(request, error):
    return JSONResponse(status_code=502, content={"detail": "外部接口连接失败或超时，请检查服务端网络和接口配置。"})


@app.middleware("http")
async def security_headers(request, call_next):
    # 不把堆栈、密钥或上游响应体返回浏览器。
    try:
        response = await call_next(request)
    except Exception:
        response = JSONResponse(status_code=500, content={"detail": "服务处理失败，请检查配置和接口响应格式。"})
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def authorize(request: Request, x_api_key: str = Header(default="")):
    settings = request.app.state.settings
    if settings.app_api_key:
        if not secrets.compare_digest(settings.app_api_key, x_api_key):
            raise HTTPException(401, "请输入有效的系统访问密钥。")
    else:
        # 无访问密钥时只允许本机直连；避免浏览器跨站调用本机接口。
        if not request.client or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
            raise HTTPException(403, "远程访问必须先配置 APP_API_KEY。")
        if request.url.hostname not in {"127.0.0.1", "localhost", "::1", "testserver"}:
            raise HTTPException(403, "无密钥模式只允许 localhost 地址。")
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "不允许跨站调用。")


def execution(request: Request):
    if not request.app.state.settings.execution_enabled:
        raise HTTPException(423, "当前为配置模式。请在 .env 设置 EXECUTION_ENABLED=true 并重启后再运行。")


class RepositoryInput(BaseModel):
    url: str = Field(max_length=300)
    branch: str = Field(default="", max_length=200)
    include_globs: list[str] = Field(default_factory=lambda: ["**/*.md", "**/*.txt", "**/*.py"], min_length=1, max_length=30)

    @field_validator("include_globs")
    @classmethod
    def validate_globs(cls, value):
        if any(not p.strip() or len(p) > 200 for p in value):
            raise ValueError("匹配规则不能为空或超过 200 字符。")
        return [p.strip() for p in value]


class RunInput(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    material: str = Field(default="", max_length=20000)
    repository_ids: list[str] = Field(min_length=1, max_length=20)
    top_k: int = Field(default=6, ge=1, le=12)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value):
        if not value.strip():
            raise ValueError("问题不能为空。")
        return value.strip()

    @field_validator("repository_ids")
    @classmethod
    def unique_repositories(cls, value):
        return list(dict.fromkeys(value))


API = [Depends(authorize)]
RUN = [Depends(authorize), Depends(execution)]


@app.get("/api/status", dependencies=API)
def status(request: Request):
    settings = request.app.state.settings
    return {"execution_enabled": settings.execution_enabled,
            "llm_model": settings.llm_model or "未配置",
            "embedding_model": settings.embedding_model or "未配置",
            "llm_configured": bool(settings.llm_model),
            "embedding_configured": bool(settings.embedding_model),
            "github_token_configured": bool(settings.github_token),
            "max_files": settings.max_files, "max_chunks": settings.max_chunks}


@app.get("/api/repositories", dependencies=API)
def repositories(request: Request):
    return request.app.state.store.repositories()


@app.post("/api/repositories", dependencies=API, status_code=201)
def add_repository(body: RepositoryInput, request: Request):
    name = parse_repository(body.url)
    repository_id = uuid.uuid4().hex
    request.app.state.store.add_repository(repository_id, f"https://github.com/{name}",
                                            body.branch.strip(), body.include_globs)
    return request.app.state.store.repository(repository_id)


@app.delete("/api/repositories/{repository_id}", dependencies=API)
def delete_repository(repository_id: str, request: Request):
    lock = request.app.state.execution_lock
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "任务处理中，请完成后再移除知识库。")
    try:
        if not request.app.state.store.repository(repository_id):
            raise HTTPException(404, "知识库不存在。")
        request.app.state.store.delete_repository(repository_id)
        return {"deleted": True}
    finally:
        lock.release()


@app.post("/api/repositories/{repository_id}/sync", dependencies=RUN)
def sync_repository(repository_id: str, request: Request):
    lock = request.app.state.execution_lock
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "已有同步或问答任务，请稍后重试。")
    try:
        repository = request.app.state.store.repository(repository_id)
        if not repository:
            raise HTTPException(404, "知识库不存在。")
        return request.app.state.rag.index(repository)
    finally:
        lock.release()


@app.get("/api/workflows", dependencies=API)
def workflows():
    return catalog()


@app.get("/api/workflows/{workflow_id}/source", dependencies=API, response_class=PlainTextResponse)
def workflow_source(workflow_id: str):
    module = WORKFLOWS.get(workflow_id)
    if not module:
        raise HTTPException(404, "工作流不存在。")
    # 仅输出注册过的固定 Python 文件；不接受任意路径或远程代码。
    return (ROOT / "app" / "workflows" / f"{module.__name__.split('.')[-1]}.py").read_text(encoding="utf-8")


@app.post("/api/workflows/{workflow_id}/run", dependencies=RUN)
def run_workflow(workflow_id: str, body: RunInput, request: Request):
    module = WORKFLOWS.get(workflow_id)
    if not module:
        raise HTTPException(404, "工作流不存在。")
    if module.REQUIRES_MATERIAL and not body.material.strip():
        raise HTTPException(422, f"请填写{module.MATERIAL_LABEL}。")
    lock = request.app.state.execution_lock
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "已有同步或问答任务，请稍后重试。")
    try:
        if not request.app.state.settings.llm_model:
            raise ServiceError("请先在 .env 配置 LLM_MODEL。")
        result = module.run(request.app.state.rag, body)
        return {"workflow": module.ID, **result}
    finally:
        lock.release()


@app.get("/api/architecture", dependencies=API)
def architecture():
    return {"indexing": ["GitHub 固定提交", "UTF-8 文本筛选", "保留行号分块", "批量嵌入", "SQLite 原子替换"],
            "query": ["问题向量化", "向量 + BM25 检索", "RRF 排序", "上下文预算", "Python 工作流", "来源编号检查"]}


app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")


@app.get("/")
@app.get("/index.html")
def index():
    return FileResponse(ROOT / "frontend" / "index.html")


@app.get("/report")
@app.get("/report.html")
def report_page():
    return FileResponse(ROOT / "frontend" / "report.html")


@app.get("/style.css")
def stylesheet():
    return FileResponse(ROOT / "frontend" / "style.css", media_type="text/css")


@app.get("/app.js")
def browser_script():
    return FileResponse(ROOT / "frontend" / "app.js", media_type="application/javascript")
