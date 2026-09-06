# 智枢 OmniHub · GitHub RAG

根据用户提供的 `HTML.zip` 改造。前端保留智枢名称、蓝紫色风格与七类业务场景，将知识问答设为主入口；后端使用 Python 实现 GitHub 资料入库、混合检索与场景工作流，无需 Dify。

**交付状态：源码已编写，默认执行关闭；未安装依赖、未启动服务、未执行测试或模型调用。** 依赖版本与真实模型接口兼容性尚待运行验证。GitHub 上传状态以交付消息为准，链接本身不代表已上传成功。

目标仓库：[XRH-RGB/zhengli](https://github.com/XRH-RGB/zhengli)。它用于存放系统代码；运行后可以添加它或其他 GitHub 仓库作为知识源。

## 已实现的源码

- GitHub 公开或私有仓库读取，支持默认分支、指定分支、标签或提交。
- UTF-8 文本与代码筛选、按字符分块并保留行号、分批嵌入。
- SQLite 原子替换索引快照；同步失败保留旧索引，成功同步时清理该知识源旧片段。
- 向量余弦相似度 + 中文/英文 BM25 + RRF 排序，按上下文字符预算选择片段。
- 根据选定知识库回答，展示原始片段及固定提交的 GitHub 行号链接。
- 七个独立 Python 工作流模块，前端可以查看源码。
- 回答模型、嵌入模型、接口地址和密钥通过 `.env` 独立配置。
- 默认配置模式：可以保存知识源、阅读源码；同步与生成接口返回 HTTP 423。

## 目录

```text
app/
  main.py                  FastAPI 路由、访问控制、执行开关
  config.py                环境配置
  github.py                GitHub 文本快照读取
  store.py                 SQLite 知识库与索引
  models.py                兼容模型接口适配
  rag.py                   分块、索引、混合检索、引用编号检查
  workflows/               七类 Python 工作流
frontend/
  index.html               知识工作台
  report.html              改造后的项目汇报页
  style.css / app.js        样式与浏览器交互
tests/test_core.py          待执行的核心回归测试
docs/ACCEPTANCE.md          待运行验收清单
.env.example               无真实密钥的配置样例
requirements.txt           Python 依赖范围
```

## 准备运行时的步骤（本次未执行）

使用 Python 3.11 或更新版本，在项目根目录执行。以下 PowerShell 命令只供后续使用：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，至少填写 `LLM_MODEL`、`EMBEDDING_MODEL`，并按服务商要求填写地址和 API Key。

- `LLM_BASE_URL`：支持 `POST /chat/completions` 的接口根地址，通常含 `/v1`。
- `EMBEDDING_BASE_URL`：支持 `POST /embeddings` 的接口根地址。
- `LLM_API_KEY` / `EMBEDDING_API_KEY`：仅在后端使用；本地不要求密钥的兼容服务可留空。
- `GITHUB_TOKEN`：公开仓库可留空；私有仓库需要有目标知识源仓库 `Contents: read` 权限的令牌。
- `APP_API_KEY`：本机直连可留空；远程使用必须设置，在前端“模型与运行配置”页输入相同密钥。请使用反向代理提供 HTTPS。该共享密钥不是多用户权限系统。
- `EXECUTION_ENABLED=false`：保持只配置模式；准备实际同步和调用模型时才改为 `true`。

配置完成后手动启动：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

打开 `http://127.0.0.1:8000`。本版使用单进程任务锁，请保持 `--workers 1`。服务启动只创建本地 SQLite 数据库，不会自动读取 GitHub 或调用模型。原始 HTML/CSS 可直接查看，但本地文件方式没有数据功能；完整交互需通过 Python 服务。

### 首次问答

1. 在“GitHub 知识库”添加 `https://github.com/XRH-RGB/zhengli` 或实际知识仓库。
2. 分支可留空；文件规则默认 `**/*.md, **/*.txt, **/*.py`。根目录的同类文件也匹配。
3. 开启执行配置并重启后，点击“同步知识库”。此操作读取 GitHub 并调用嵌入接口。
4. 在知识问答页选择已同步知识库，输入问题。此操作调用嵌入与回答模型。
5. 查看答案下方的检索片段，点击链接核对源文件。

更换嵌入模型或嵌入接口地址后，先重新同步。即使模型名称相同，上游更换了模型权重，也应手动重新同步。私有仓库来源链接需要浏览器中的 GitHub 账号有访问权限。

## 工作流与原方案对应

| 原方案场景 | 本版 Python 模块 | 当前输出 |
| --- | --- | --- |
| 员工手册与内部文档检索 | `documents.py` | 知识问答与来源 |
| 出题与批阅 | `exam.py` | 练习、参考答案、学习反馈 |
| 会议录音与纪要 | `meeting.py` | 输入文字记录后整理纪要 |
| 日报周报生成与推送 | `report.py` | 根据文字工作记录生成草稿 |
| OA 自动识别提交 | `oa.py` | 制度检索、字段清单与申请草稿 |
| 飞书群消息汇总 | `messages.py` | 粘贴群消息后整理主题与待办 |
| 考核评估与培训 | `training.py` | 学习资料、阅读顺序和自测建议 |

录音转写、飞书实时连接/推送、OA 提交、正式人事考核未接入，不会声称完成这些外部操作。所有场景均先检索已选择的知识库。浏览器只负责交互，业务编排位于 Python 函数中。

新增工作流时，在 `app/workflows/` 编写包含元数据及 `run(rag, request)` 的本地 Python 模块，并显式加入 `WORKFLOWS` 注册表。服务不会从 GitHub 下载并执行任意工作流代码。

## 当前限制

- 本版适合单机、小型知识库；默认每知识源最多 300 个匹配文件、每文件 200 KB、5000 个片段。每次同步重新嵌入完整选定快照，不是增量嵌入。
- 读取 GitHub Git Trees / Blobs API。过大的、被 GitHub 截断的目录会报错；大文件、非 UTF-8 文本、二进制与 LFS 指针会跳过并返回说明。空索引不覆盖旧索引。
- 排除 `.env*`、依赖目录、`.git`、`.github`、`data` 等。该筛选不等同于敏感信息识别；只添加你允许发送给所配置模型服务的资料。
- 检索片段会发送给回答模型；被索引文本会发送给嵌入服务。`.env`、数据库和真实密钥不应上传 GitHub。
- SQLite 中保存原始片段和向量；没有多租户隔离。所有持有同一访问密钥的用户共享知识库。未配置密钥时只允许本机直连，避免用无密钥反向代理公开服务。
- 任务同步处理、单进程互斥，不含后台队列、取消、重试、进度百分比或历史会话持久化。刷新页面会丢失当前回答，正在服务端处理的任务可能继续完成。
- 引用检查只校验编号存在与否，不能证明模型结论被文档支持。界面展示的是检索排序分，不是可信度；输出需要人工核对。
- 未验证的依赖采用兼容范围，没有伪造锁文件；首次安装和测试通过后可再固定环境版本。

## 后续测试

本次未执行，下列命令需要先安装依赖：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

再按 [验收清单](docs/ACCEPTANCE.md) 验证真实 GitHub 与模型接口。

## 上传 GitHub

将本项目文件作为源码上传到目标仓库。不要只上传 ZIP 作为系统源码，也不要上传 `.env`、`.venv` 或 `data/`。如目标仓库已有内容，应保留原内容并选择独立目录或分支。GitHub Pages 只能托管静态前端，不能运行此 Python 后端；本次没有新增自动部署或自动执行的 GitHub Actions。

接口实现参考：[GitHub Git Trees API](https://docs.github.com/en/rest/git/trees)、[FastAPI 静态文件](https://fastapi.tiangolo.com/tutorial/static-files/)、[FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)。
