"""消息整理：处理粘贴的群消息，不连接或发送飞书消息。"""
ID = "messages"
TITLE = "群消息整理"
DESCRIPTION = "从消息文字中提炼主题、待办和问题，并检索仓库背景。"
MATERIAL_LABEL = "群消息文字"
REQUIRES_MATERIAL = True
STEPS = ["接收消息文字", "检索相关背景", "按主题整理", "提取明确待办"]


def run(rag, request):
    return rag.answer(request.query, request.repository_ids, request.top_k,
        "按主题总结消息，分别列明确待办、负责人、期限和未解决问题；不明的信息写待确认。"
        "对用户消息标注材料来源，对仓库背景标注引用。不声称已连接或发送到飞书。", request.material)
