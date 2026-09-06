"""日报周报：使用用户提供的工作记录生成草稿。"""
ID = "report"
TITLE = "日报与周报草稿"
DESCRIPTION = "结合工作记录和仓库规范，整理进展、问题与下一步计划。"
MATERIAL_LABEL = "工作记录"
REQUIRES_MATERIAL = True
STEPS = ["读取工作记录", "检索报告规范", "整理进度与问题", "生成报告草稿"]


def run(rag, request):
    return rag.answer(request.query, request.repository_ids, request.top_k,
        "生成报告草稿：已完成、进行中、阻塞、下一步。不虚构工作量、日期、完成情况。"
        "用户记录与仓库依据分开标注；没有发送或推送能力，不声称已发送。", request.material)
