"""会议纪要：输入文字记录，结合仓库中的术语、项目和规范。"""
ID = "meeting"
TITLE = "会议纪要整理"
DESCRIPTION = "整理粘贴的会议文字，用仓库资料补充项目背景和术语依据。"
MATERIAL_LABEL = "会议文字记录"
REQUIRES_MATERIAL = True
STEPS = ["接收会议文字", "检索项目背景", "提取决议与待办", "区分事实和待确认项"]


def run(rag, request):
    return rag.answer(request.query, request.repository_ids, request.top_k,
        "输出会议主题、讨论要点、明确决议、待办表和待确认项。负责人、期限仅来自会议材料，"
        "没有则写待确认；仓库背景必须引用。会议文字标为用户提供材料。不要声称已转录录音。",
        request.material)
