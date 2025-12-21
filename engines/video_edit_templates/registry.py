from typing import Dict, Optional
from engines.video_edit_templates.models import EditTemplate

class TemplateRegistry:
    def __init__(self):
        self._templates: Dict[str, EditTemplate] = {}

    def register(self, template: EditTemplate):
        self._templates[template.id] = template

    def get(self, template_id: str) -> Optional[EditTemplate]:
        return self._templates.get(template_id)

_registry = TemplateRegistry()

def get_template_registry() -> TemplateRegistry:
    return _registry
