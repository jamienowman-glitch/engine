"""Editor Tools and Commands."""
from __future__ import annotations

from typing import List, Set, Optional
from enum import Enum

from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.core.geometry import Vector3
from engines.scene_engine.editor.history import Command, HistoryStack
from engines.scene_engine.editor.snapping import snap_to_grid

class EditorContext:
    def __init__(self, scene: SceneV2):
        self.scene = scene
        self.selection: Set[str] = set()
        self.history = HistoryStack()
        
    def get_selected_nodes(self) -> List[SceneNodeV2]:
        # Recursive finder
        found = []
        def traverse(nodes):
            for n in nodes:
                if n.id in self.selection:
                    found.append(n)
                traverse(n.children)
        traverse(self.scene.nodes)
        return found
        
    def find_node(self, node_id: str) -> Optional[SceneNodeV2]:
        res = None
        def traverse(nodes):
            nonlocal res
            if res: return
            for n in nodes:
                if n.id == node_id: 
                    res = n
                    return
                traverse(n.children)
        traverse(self.scene.nodes)
        return res


# --- Commands ---

class MoveNodeCommand(Command):
    def __init__(self, context: EditorContext, node_id: str, delta: Vector3):
        self.context = context
        self.node_id = node_id
        self.delta = delta
        self.applied = False
        
    def execute(self) -> bool:
        node = self.context.find_node(self.node_id)
        if node:
            node.transform.position.x += self.delta.x
            node.transform.position.y += self.delta.y
            node.transform.position.z += self.delta.z
            self.applied = True
            return True
        return False
        
    def undo(self):
        if self.applied:
            node = self.context.find_node(self.node_id)
            if node:
                node.transform.position.x -= self.delta.x
                node.transform.position.y -= self.delta.y
                node.transform.position.z -= self.delta.z


# --- Tools ---

class ToolKind(str, Enum):
    SELECT = "select"
    MOVE = "move"

class EditorTool:
    def __init__(self, kind: ToolKind):
        self.kind = kind
        
    def on_drag(self, context: EditorContext, delta: Vector3):
        pass
        
    def on_end(self, context: EditorContext):
        pass

class MoveTool(EditorTool):
    def __init__(self):
        super().__init__(ToolKind.MOVE)
        self.accumulated_delta = Vector3(x=0,y=0,z=0)
        
    def on_drag(self, context: EditorContext, delta: Vector3):
        # Preview move?
        # For P0, "on_end" commits the command.
        # "on_drag" might just update local temp state or apply directly?
        # If we apply directly, undo history gets spammed.
        # Let's accumulate.
        self.accumulated_delta.x += delta.x
        self.accumulated_delta.y += delta.y
        self.accumulated_delta.z += delta.z
        
    def apply(self, context: EditorContext):
        """Commits the move as a command."""
        nodes = context.get_selected_nodes()
        if not nodes: return
        
        # Batch command? For now single command per node or 1st node.
        # Group command left for future.
        for node in nodes:
            cmd = MoveNodeCommand(context, node.id, self.accumulated_delta)
            context.history.push_and_execute(cmd)
            
        self.accumulated_delta = Vector3(x=0,y=0,z=0)

