import os
import yaml
import importlib.util
from typing import List, Dict, Any, Type
from pydantic import BaseModel

from engines.mcp_gateway.inventory import Tool, Scope, get_inventory
from engines.common.identity import RequestContext

# Paths relative to repository root (assuming running from root or finding root)
# Ideally we use absolute paths derived from this file location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
# BASE_DIR is .../engines/workbench -> parent is engines
ENGINES_DIR = BASE_DIR

class LoaderService:
    def __init__(self):
        self._inventory = get_inventory()

    def load_all(self):
        """Scans connectors and muscles and registers them."""
        self._scan_connectors()
        self._scan_muscles()

    def reload(self):
        """Clears inventory and reloads all tools from disk."""
        self._inventory.clear()
        self.load_all()

    def _is_enabled(self, name: str, env_var: str) -> bool:
        allowed_str = os.environ.get(env_var, "")
        allowed = [x.strip() for x in allowed_str.split(",") if x.strip()]
        return name in allowed

    def _scan_connectors(self):
        if self._is_enabled("*", "ENABLED_CONNECTORS"): # Wildcard support for dev convenience?
            # User said "enabled set comes from config... OR registry listing".
            # Explicit naming is safer for "Empty by default".
            # I won't implement wildcard unless requested. User wants strictness.
            pass

        cls_dir = os.path.join(ENGINES_DIR, "connectors")
        if not os.path.exists(cls_dir):
            return
        
        for name in os.listdir(cls_dir):
            if name.startswith("_") or name.startswith("."):
                continue
            
            if not self._is_enabled(name, "ENABLED_CONNECTORS"):
                continue

            path = os.path.join(cls_dir, name)
            if os.path.isdir(path):
                self._load_package(path, is_muscle=False)

    def _scan_muscles(self):
        cls_dir = os.path.join(ENGINES_DIR, "muscles")
        if not os.path.exists(cls_dir):
            return
            
        for name in os.listdir(cls_dir):
            if name.startswith("_") or name.startswith("."):
                continue
            
            # Since muscles are internal, maybe we enable all?
            # User requirement: "Inventory must be empty by default".
            # So gating muscles is required.
            if not self._is_enabled(name, "ENABLED_MUSCLES"):
                continue

            # Muscles have `mcp` subdir
            path = os.path.join(cls_dir, name, "mcp")
            if os.path.isdir(path):
                self._load_package(path, is_muscle=True)

    def _load_package(self, path: str, is_muscle: bool):
        spec_path = os.path.join(path, "spec.yaml")
        impl_path = os.path.join(path, "impl.py")
        
        if not os.path.exists(spec_path) or not os.path.exists(impl_path):
            return

        try:
            with open(spec_path, "r") as f:
                spec = yaml.safe_load(f)
            
            # Load Impl Module
            module_name = f"dynamic_mcp_{os.path.basename(os.path.dirname(path)) if is_muscle else os.path.basename(path)}"
            spec_obj = importlib.util.spec_from_file_location(module_name, impl_path)
            if not spec_obj or not spec_obj.loader:
                return
            
            module = importlib.util.module_from_spec(spec_obj)
            spec_obj.loader.exec_module(module)
            
            # --- Dynamic Tool Loading (Phase 5) ---
            # Check if module exposes a loader hooks
            dynamic_loader_fn = getattr(module, "load_dynamic_tools", None)
            if dynamic_loader_fn and callable(dynamic_loader_fn):
                try:
                    dynamic_tools = dynamic_loader_fn()
                    for t in dynamic_tools:
                        if isinstance(t, Tool):
                            self._inventory.register_tool(t)
                except Exception as e:
                    print(f"Error loading dynamic tools from {path}: {e}")
            
            # --- Static Spec Loading ---
            # Create Tool (Default from spec.yaml)
            tool_id = spec.get("id")
            if not tool_id:
                return
                
            tool = Tool(
                id=tool_id,
                name=spec.get("name", tool_id),
                summary=spec.get("summary", "")
            )
            
            # Bind Scopes
            for scope_def in spec.get("scopes", []):
                s_name = scope_def.get("name")
                handler_name = scope_def.get("handler")
                model_name = scope_def.get("input_model")
                desc = scope_def.get("description", "")
                
                # Dynamic binding
                handler_fn = getattr(module, handler_name, None)
                input_model_cls = getattr(module, model_name, None)
                
                if handler_fn and input_model_cls and issubclass(input_model_cls, BaseModel):
                    tool.register_scope(Scope(
                        name=s_name,
                        description=desc,
                        input_model=input_model_cls,
                        handler=handler_fn,
                        firearms_required=scope_def.get("firearms_required", False) 
                    ))
            
            self._inventory.register_tool(tool)
            
        except Exception as e:
            print(f"Failed to load MCP package at {path}: {e}")

# Global loader instance
loader = LoaderService()
