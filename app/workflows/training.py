"""学习建议：根据知识问题推荐学习资料。"""
ID = "training"
TITLE = "知识学习与培训建议"
DESCRIPTION = "根据学习目标和知识疑问，推荐仓库中的阅读顺序与练习。"
MATERIAL_LABEL = "学习目标与知识疑问"
REQUIRES_MATERIAL = True
STEPS = ["梳理学习目标", "检索学习材料", "规划阅读顺序", "生成练习建议"]


def run(rag, request):
    return rag.answer(request.query, request.repository_ids, request.top_k,
        "输出知识问题、对应阅读材料（引用）、学习顺序和自测建议。仅提供学习辅助，"
        "不要推断个人能力等级，不做人事绩效、晋升、录用决定。", request.material)
