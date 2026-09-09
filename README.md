# RAG 知识工作台

把 GitHub 中的文档和代码整理成可查询的知识库。输入问题后，系统先查找相关资料，再生成回答，并附上文件和行号，方便你回到原文核对。会议纪要、周报、申请草稿等任务也可以使用同一套知识库。

[项目仓库](https://github.com/XRH-RGB/zhengli) · [详细使用指南](docs/USER_GUIDE.md) · [运行检查清单](docs/ACCEPTANCE.md)

## 可以做什么

| 任务 | 你需要提供 | 得到的结果 |
| --- | --- | --- |
| 知识问答 | 问题和已同步的知识库 | 回答、资料片段与原文链接 |
| 出题与答题反馈 | 出题要求，或题目和作答 | 练习题、参考答案或学习反馈 |
| 会议纪要 | 会议文字记录 | 讨论要点、决议和待办事项 |
| 日报与周报 | 工作记录和写作要求 | 可修改的报告草稿 |
| 制度与申请辅助 | 申请事项和已知信息 | 相关制度、需补充的字段和申请草稿 |
| 群消息整理 | 粘贴的消息文字 | 主题摘要、问题和待办事项 |
| 学习与培训 | 学习目标和知识疑问 | 阅读资料、学习顺序和自测建议 |

会议、消息等材料目前需要手动粘贴文字。生成后请核对内容，再复制到日常使用的文档或办公系统中。系统尚未接入录音转写、实时群消息、消息推送或 OA 提交。

## 第一次使用

以下以 Windows PowerShell 为例，需要 Python 3.11 或更新版本。配置示例和常见问题见[使用指南](docs/USER_GUIDE.md)。

1. 打开项目仓库，点击 **Code → Download ZIP**，下载后解压。进入能看到 `requirements.txt`、`.env.example`、`app` 和 `frontend` 的文件夹。
2. 在资源管理器地址栏输入 `powershell`，按回车。逐行输入：

   ```powershell
   python --version
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. 复制配置样例并用记事本打开。已有 `.env` 时，下列命令会保留原配置：

   ```powershell
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   notepad .env
   ```

4. 填写回答模型和嵌入模型的接口地址、模型名称及密钥。准备开始同步和提问时，将 `EXECUTION_ENABLED=false` 改为 `EXECUTION_ENABLED=true`，保存并关闭记事本。
5. 在同一个窗口启动服务：

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
   ```

6. 保持窗口打开，在浏览器访问 `http://127.0.0.1:8000`。进入“模型与运行配置”，检查模型名称是否与刚才填写的一致。
7. 打开“GitHub 知识库”，粘贴知识仓库地址，点击“保存知识源”，再点击仓库卡片上的“同步知识库”。出现“已同步”且文件数、片段数大于 0 后，就可以去“知识问答”输入问题了。

默认配置模式允许保存仓库信息和查看源码；同步与生成需要开启运行开关。服务启动本身不会自动同步仓库或调用模型。

## 日常使用

- **提问**：选择已同步的知识库，写清楚问题，点击“检索并回答”。展开回答下方的资料片段，点击文件链接核对原文。
- **整理材料**：进入“Python 工作流”，选择任务，填写要求并粘贴材料，选好知识库后点击“运行工作流”。核对后点击“复制结果”。
- **更新资料**：在 GitHub 修改文档后，回到知识库页面手动点击“同步知识库”。仓库内容不会自动更新到本地知识库。
- **停止服务**：在服务窗口按 `Ctrl+C`。下次使用时进入项目文件夹，再运行上面的启动命令。
- **修改模型**：编辑 `.env` 后重启。更换嵌入模型或其接口地址后，需要重新同步知识库。

## 配置与数据

回答模型和嵌入模型可以分别使用不同服务商，接口需要分别兼容 `/chat/completions` 和 `/embeddings`。各字段的填写方法见[使用指南](docs/USER_GUIDE.md)。

公开仓库可以不填令牌，但受匿名请求限额影响。私有仓库需要在服务端配置具有该仓库 `Contents: read` 权限的 `GITHUB_TOKEN`。浏览器登录 GitHub 不会自动授权 Python 服务。

本机使用可以留空 `APP_API_KEY`。远程使用需要设置访问密钥、通过 HTTPS 访问，并在页面输入相同密钥。同一密钥下的用户共享知识库。

同步时，资料会发送给嵌入服务；提问时，检索片段会发送给回答模型。请使用适合这些资料的模型服务。`.env` 保存配置和密钥，`data/` 保存本地数据库，这些文件应留在运行机器上。

## 项目结构

```text
app/
  main.py                  Web 接口与访问控制
  config.py                配置读取
  github.py                GitHub 文件读取
  store.py                 SQLite 知识库与索引
  models.py                模型接口
  rag.py                   分块、混合检索与引用检查
  workflows/               七类 Python 工作流
frontend/
  index.html               知识工作台及操作说明
  report.html              系统介绍
  style.css / app.js        页面样式与交互
docs/USER_GUIDE.md          详细使用指南
docs/ACCEPTANCE.md          运行检查清单
docs/DELIVERY_STATUS.md     验证记录
tests/test_core.py          核心测试
.env.example               配置样例
requirements.txt           Python 依赖
```

后端使用 FastAPI，检索结合语义向量、BM25 与融合排序，SQLite 保存文件片段和向量。工作流位于本地 Python 模块中，知识仓库中的代码只作为资料读取。新增工作流时，在 `app/workflows/` 编写模块，并加入 `WORKFLOWS` 注册表。

## 适用范围与验证

当前适合单机、小型知识库。默认每个知识源最多读取 300 个匹配文件，每个文件最多 200 KB，最多生成 5000 个片段；同步会重新处理所选范围。大文件、二进制文件、非 UTF-8 文件和 LFS 指针会被跳过，空结果或同步失败不会覆盖旧索引。

服务使用单进程任务锁，请保留 `--workers 1`。目前没有后台任务队列、多用户隔离或会话历史保存；刷新页面前请复制需要保留的结果。来源链接便于核对，但引用编号有效不代表结论一定正确。

目前完成了源码静态检查，依赖安装、服务启动、接口联调及运行测试仍待验证，详见[验证记录](docs/DELIVERY_STATUS.md)。准备验证时，安装依赖后运行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

随后按[运行检查清单](docs/ACCEPTANCE.md)验证知识库同步、问答与各类工作流。Python 后端需要运行环境，GitHub Pages 无法直接运行这个服务。
