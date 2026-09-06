from . import documents, exam, meeting, report, oa, messages, training

WORKFLOWS = {module.ID: module for module in (
    documents, exam, meeting, report, oa, messages, training
)}


def catalog():
    return [{"id": m.ID, "title": m.TITLE, "description": m.DESCRIPTION,
             "material_label": m.MATERIAL_LABEL, "requires_material": m.REQUIRES_MATERIAL,
             "steps": m.STEPS, "source": f"app/workflows/{m.__name__.split('.')[-1]}.py"}
            for m in WORKFLOWS.values()]
