"use strict";

const $ = (id) => document.getElementById(id);
const state = { connected: false, enabled: false, busy: false, key: "", repositories: [], workflows: [], workflow: null, answer: "", result: "", sourceRequest: 0 };

// 未连接时仅显示功能目录，不生成假回答或假索引数据。
const offlineWorkflows = [
  ["documents", "知识检索问答", "检索仓库资料，回答附文件与行号。", "补充上下文（可选）", false],
  ["exam", "知识出题与答题反馈", "根据知识库生成练习和参考依据。", "题目与作答（可选）", false],
  ["meeting", "会议纪要整理", "结合会议文字与仓库背景提取纪要。", "会议文字记录", true],
  ["report", "日报与周报草稿", "整理工作记录，检索报告规范。", "工作记录", true],
  ["oa", "OA 制度与申请辅助", "检索制度并生成申请草稿。", "申请事项与已知信息", true],
  ["messages", "群消息整理", "提炼消息主题、问题与待办。", "群消息文字", true],
  ["training", "知识学习与培训建议", "按学习目标查找资料与练习。", "学习目标与知识疑问", true],
].map(([id, title, description, material_label, requires_material]) => ({ id, title, description, material_label, requires_material, steps: ["输入任务", "检索知识", "生成结果", "检查引用"], source: `app/workflows/${id}.py` }));

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function notice(message, error = false) {
  $("notice").textContent = message;
  $("notice").classList.toggle("error", error);
}

async function api(path, options = {}) {
  if (location.protocol === "file:") throw new Error("当前为本地静态文件。界面可查看，数据功能需在你准备运行后启动 Python 服务。");
  const response = await fetch(`/api${path}`, {
    ...options, headers: { "Content-Type": "application/json", ...(state.key ? { "X-API-Key": state.key } : {}), ...options.headers },
  });
  if (!response.ok) {
    let message = `请求失败（HTTP ${response.status}）`;
    try {
      const body = await response.json();
      message = Array.isArray(body.detail) ? body.detail.map(item => item.msg).join("；") : body.detail || message;
    } catch { /* 保留 HTTP 状态信息 */ }
    throw new Error(message);
  }
  return options.text ? response.text() : response.json();
}

function updateButtons() {
  $("ask-submit").disabled = !state.connected || !state.enabled || state.busy;
  $("workflow-submit").disabled = !state.connected || !state.enabled || state.busy;
  $("refresh").disabled = state.busy;
  document.querySelectorAll("[data-sync]").forEach(button => { button.disabled = !state.enabled || state.busy; });
  document.querySelectorAll("[data-remove]").forEach(button => { button.disabled = state.busy; });
}

async function action(button, label, job) {
  if (state.busy) return;
  state.busy = true;
  const old = button.textContent;
  button.disabled = true;
  button.textContent = label;
  updateButtons();
  try { await job(); }
  catch (error) { notice(error.message || "请求未完成，请检查连接。", true); }
  finally { state.busy = false; button.textContent = old; button.disabled = false; updateButtons(); }
}

function navigate() {
  const names = { chat: "知识问答", knowledge: "GitHub 知识库", workflows: "Python 工作流", settings: "模型与运行配置" };
  const id = Object.hasOwn(names, location.hash.slice(1)) ? location.hash.slice(1) : "chat";
  document.querySelectorAll(".view").forEach(view => { view.hidden = view.id !== `view-${id}`; });
  document.querySelectorAll(".nav-item").forEach(link => {
    const active = link.getAttribute("href") === `#${id}`;
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current");
  });
  $("page-label").textContent = names[id];
}

function selectedRepositories(id) {
  return [...$(id).selectedOptions].map(option => option.value).filter(Boolean);
}

function renderRepositories() {
  const repos = state.repositories;
  $("repo-count").textContent = repos.length;
  $("file-count").textContent = repos.reduce((n, r) => n + r.file_count, 0);
  $("chunk-count").textContent = repos.reduce((n, r) => n + r.chunk_count, 0);
  for (const id of ["chat-repositories", "workflow-repositories"]) {
    const previous = new Set(selectedRepositories(id));
    $(id).replaceChildren();
    if (!repos.length) $(id).append(new Option("请先添加知识库", ""));
    for (const repo of repos) {
      const option = new Option(`${repo.url.replace("https://github.com/", "")} · ${repo.indexed_at ? "已同步" : "未同步"}`, repo.id);
      option.selected = previous.size ? previous.has(repo.id) : Boolean(repo.indexed_at);
      $(id).append(option);
    }
  }
  $("repositories").replaceChildren();
  if (!repos.length) $("repositories").append(element("div", "panel empty", "还没有知识源。添加 GitHub 仓库后，可在开启执行模式时同步。"));
  for (const repo of repos) {
    const card = element("article", "panel repository-card");
    const header = element("header");
    const title = element("h3");
    const link = element("a", "", repo.url.replace("https://github.com/", ""));
    link.href = repo.url; link.target = "_blank"; link.rel = "noopener noreferrer";
    title.append(link);
    header.append(title, element("span", "pill", repo.indexed_at ? "已同步" : "待同步"));
    card.append(header, element("p", "", `分支 / 版本：${repo.branch || "默认分支"} · 范围：${repo.include_globs.join(", ")}`));
    card.append(element("p", "", `${repo.file_count} 个文件 · ${repo.chunk_count} 个片段${repo.commit_sha ? ` · 提交 ${repo.commit_sha.slice(0, 12)}` : ""}`));
    if (repo.indexed_at) card.append(element("p", "", `同步时间：${new Date(repo.indexed_at).toLocaleString()}`));
    const actions = element("div", "repository-actions");
    const sync = element("button", "button secondary small", "同步知识库");
    sync.dataset.sync = repo.id;
    sync.addEventListener("click", () => action(sync, "正在同步…", async () => {
      notice("正在读取仓库并生成嵌入，可能需要几分钟，请保持页面打开。");
      const result = await api(`/repositories/${repo.id}/sync`, { method: "POST" });
      state.repositories = await api("/repositories"); renderRepositories();
      const skips = result.skipped.length ? ` 跳过 ${result.skipped.length} 个文件：${result.skipped.map(s => `${s.path}（${s.reason}）`).join("；")}` : "";
      notice(`同步完成：${result.files} 个文本文件、${result.chunks} 个片段，提交 ${result.commit.slice(0, 12)}。${skips}`);
    }));
    const remove = element("button", "button danger small", "移除知识源");
    remove.dataset.remove = repo.id;
    remove.addEventListener("click", () => {
      if (!confirm("移除此知识源及本地索引？GitHub 仓库不会被修改，之后可重新添加。")) return;
      action(remove, "正在移除…", async () => {
        await api(`/repositories/${repo.id}`, { method: "DELETE" });
        state.repositories = await api("/repositories"); renderRepositories();
        notice("知识源及其本地索引已移除。");
      });
    });
    actions.append(sync, remove); card.append(actions); $("repositories").append(card);
  }
  updateButtons();
}

function renderWorkflows() {
  $("workflow-cards").replaceChildren();
  state.workflows.forEach((workflow, index) => {
    const card = element("button", "workflow-card");
    card.type = "button"; card.dataset.workflow = workflow.id;
    card.append(element("span", "number", `${String(index + 1).padStart(2, "0")} / PYTHON`), element("b", "", workflow.title), element("p", "", workflow.description));
    card.addEventListener("click", () => selectWorkflow(workflow));
    $("workflow-cards").append(card);
  });
  selectWorkflow(state.workflows.find(w => w.id === state.workflow?.id) || state.workflows[0]);
}

async function selectWorkflow(workflow) {
  if (!workflow) return;
  state.workflow = workflow;
  document.querySelectorAll("[data-workflow]").forEach(card => {
    const selected = card.dataset.workflow === workflow.id;
    card.classList.toggle("selected", selected); card.setAttribute("aria-pressed", String(selected));
  });
  $("workflow-title").textContent = workflow.title;
  $("material-label").textContent = workflow.material_label;
  $("workflow-material").required = workflow.requires_material;
  $("workflow-steps").replaceChildren(...workflow.steps.map(step => element("li", "", step)));
  $("source-path").textContent = workflow.source;
  const request = ++state.sourceRequest;
  if (!state.connected) { $("workflow-source").textContent = "尚未连接 Python 服务。完整源码在项目 app/workflows 目录。"; return; }
  $("workflow-source").textContent = "读取源码…";
  try {
    const source = await api(`/workflows/${workflow.id}/source`, { text: true });
    if (request === state.sourceRequest) $("workflow-source").textContent = source;
  } catch (error) { if (request === state.sourceRequest) $("workflow-source").textContent = error.message; }
}

function renderResult(result, workflow = false) {
  const answer = $(workflow ? "workflow-answer" : "answer");
  const sources = $(workflow ? "workflow-sources" : "sources");
  const warnings = $(workflow ? "workflow-warnings" : "answer-warnings");
  answer.classList.remove("empty"); answer.textContent = result.answer;
  sources.replaceChildren(); warnings.replaceChildren();
  for (const warning of result.warnings) warnings.append(element("div", "notice error", warning));
  for (const source of result.sources) {
    const card = element("article", "source-card");
    const link = element("a", "", `[${source.citation}] ${source.path}`);
    // 只使用 GitHub 来源链接，不把模型输出作为 HTML 或任意 URL 执行。
    const url = new URL(source.url);
    if (url.protocol === "https:" && url.hostname === "github.com") link.href = url.href;
    link.target = "_blank"; link.rel = "noopener noreferrer";
    card.append(link, element("p", "", `第 ${source.start_line}–${source.end_line} 行 · 检索排序分 ${source.score}（非可信度）`));
    const details = element("details"); details.append(element("summary", "muted", "查看原始片段"), element("pre", "", source.text));
    card.append(details); sources.append(card);
  }
  const copyText = result.answer + (result.sources.length ? "\n\n检索来源：\n" + result.sources.map(s => `[${s.citation}] ${s.path} ${s.url}`).join("\n") : "");
  if (workflow) state.result = copyText; else state.answer = copyText;
  $(workflow ? "copy-workflow" : "copy-answer").disabled = false;
}

async function refresh() {
  try {
    const [status, repos, workflows] = await Promise.all([api("/status"), api("/repositories"), api("/workflows")]);
    state.connected = true; state.enabled = status.execution_enabled; state.repositories = repos; state.workflows = workflows;
    $("connection").textContent = status.execution_enabled ? "服务已连接" : "配置模式";
    $("connection").className = `status ${status.execution_enabled ? "online" : "locked"}`;
    $("execution-mode").textContent = status.execution_enabled ? "已开启执行" : "执行已关闭";
    $("llm-model").textContent = status.llm_model;
    $("embedding-model").textContent = status.embedding_model;
    $("github-config").textContent = status.github_token_configured ? "服务端已配置" : "未配置 · 仅公开仓库";
    renderRepositories(); renderWorkflows();
    notice(status.execution_enabled ? "服务已连接。添加并同步知识库后即可提问。" : "当前为配置模式：可保存知识源、查看源码；仓库同步、模型调用和工作流执行均已关闭。");
  } catch (error) {
    state.connected = false; state.enabled = false;
    $("connection").textContent = "未连接服务"; $("connection").className = "status neutral";
    state.workflows = offlineWorkflows; renderWorkflows();
    notice(error.message || "未能连接 Python 服务。当前只可查看界面，尚未执行任何工作流。", true);
  }
  updateButtons();
}

$("repository-form").addEventListener("submit", event => {
  event.preventDefault();
  action(event.submitter, "正在保存…", async () => {
    const globs = $("repo-globs").value.split(/[,，]/).map(s => s.trim()).filter(Boolean);
    await api("/repositories", { method: "POST", body: JSON.stringify({ url: $("repo-url").value.trim(), branch: $("repo-branch").value.trim(), include_globs: globs }) });
    state.repositories = await api("/repositories"); renderRepositories();
    notice("知识源已保存，尚未同步或调用模型。"); $("repo-url").value = "";
  });
});

$("ask-form").addEventListener("submit", event => {
  event.preventDefault();
  action(event.submitter, "正在检索与生成…", async () => {
    const ids = selectedRepositories("chat-repositories");
    if (!ids.length) throw new Error("请先选择至少一个已同步的知识库。");
    notice("正在检索资料并生成回答，请保持页面打开。");
    const result = await api("/workflows/documents/run", { method: "POST", body: JSON.stringify({ query: $("question").value, repository_ids: ids, top_k: Number($("top-k").value) }) });
    renderResult(result); notice("回答已生成，请结合来源片段核对。");
  });
});

$("workflow-form").addEventListener("submit", event => {
  event.preventDefault();
  action(event.submitter, "正在执行…", async () => {
    const ids = selectedRepositories("workflow-repositories");
    if (!ids.length) throw new Error("请先选择至少一个已同步的知识库。");
    const workflow = state.workflow;
    notice(`正在处理：${workflow.title}。`);
    const result = await api(`/workflows/${workflow.id}/run`, { method: "POST", body: JSON.stringify({ query: $("workflow-query").value, material: $("workflow-material").value, repository_ids: ids, top_k: 6 }) });
    renderResult(result, true); notice(`${workflow.title}已生成结果，请人工核对。`);
  });
});

for (const [id, key] of [["copy-answer", "answer"], ["copy-workflow", "result"]]) {
  $(id).addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(state[key]); notice("结果及来源链接已复制。"); }
    catch { notice("浏览器未允许复制，请手动选择结果文本复制。", true); }
  });
}
$("connect").addEventListener("click", () => { state.key = $("access-key").value; $("access-key").value = ""; refresh(); });
$("refresh").addEventListener("click", refresh);
window.addEventListener("hashchange", navigate);
state.workflows = offlineWorkflows; navigate(); renderWorkflows(); refresh();
