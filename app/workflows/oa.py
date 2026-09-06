"""OA 申请辅助：只生成草稿，不自动审批或提交。"""
ID = "oa"
TITLE = "OA 制度与申请辅助"
DESCRIPTION = "检索仓库制度，列出所需材料并生成可人工核对的申请草稿。"
MATERIAL_LABEL = "申请事项与已知信息"
REQUIRES_MATERIAL = True
STEPS = ["识别申请事项", "检索制度", "列出缺失信息", "生成申请草稿"]


def run(rag, request):
    return rag.answer(request.query, request.repository_ids, request.top_k,
        "输出适用制度（附引用）、申请所需字段、已知信息、缺失信息和申请草稿。"
        "没有制度依据就说明无法确认。不要批准申请，不要声称已提交到 OA。", request.material)
