"""员工手册与仓库文档检索：检索 → 证据组装 → 回答 → 引用检查。"""
ID = "documents"
TITLE = "知识检索问答"
DESCRIPTION = "从仓库文档和代码中查找依据，回答时附上文件与行号。"
MATERIAL_LABEL = "补充上下文（可选）"
REQUIRES_MATERIAL = False
STEPS = ["解析问题", "混合检索", "组装证据", "生成回答", "检查引用"]


def run(rag, request):
    return rag.answer(request.query, request.repository_ids, request.top_k,
                      "先直接回答，再解释依据；不能从证据确定的内容列为待确认。",
                      request.material)
