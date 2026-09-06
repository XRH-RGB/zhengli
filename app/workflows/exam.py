"""知识考核：以知识库为题目和参考答案来源。"""
ID = "exam"
TITLE = "知识出题与答题反馈"
DESCRIPTION = "根据仓库知识生成练习；提供作答时，按资料给出逐题反馈。"
MATERIAL_LABEL = "题目与作答（生成练习时可留空）"
REQUIRES_MATERIAL = False
STEPS = ["识别考核主题", "检索知识点", "生成题目或逐题反馈", "附参考依据"]


def run(rag, request):
    instruction = (
        "有题目与作答材料时，逐题输出参考答案、差异和学习建议；无作答时生成最多 5 道练习，"
        "附参考答案与来源。不要把练习反馈当作正式人事考核或录用决定。"
    )
    return rag.answer(request.query, request.repository_ids, request.top_k, instruction, request.material)
