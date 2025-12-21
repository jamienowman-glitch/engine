"""Scripting Hooks."""
from __future__ import annotations

from typing import Callable, Dict, Optional
from engines.scene_engine.core.scene_v2 import SceneV2

# Registry type: Name -> Function(SceneV2) -> SceneV2
ScriptFunc = Callable[[SceneV2], SceneV2]

class ScriptRegistry:
    _scripts: Dict[str, ScriptFunc] = {}
    
    @classmethod
    def register(cls, name: str, func: ScriptFunc):
        cls._scripts[name] = func
        
    @classmethod
    def get(cls, name: str) -> Optional[ScriptFunc]:
        return cls._scripts.get(name)
        
    @classmethod
    def run(cls, name: str, scene: SceneV2) -> SceneV2:
        func = cls.get(name)
        if func:
            return func(scene)
        return scene
        
    @classmethod
    def clear(cls):
        cls._scripts.clear()
