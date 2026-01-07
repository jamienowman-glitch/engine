from typing import Dict, Optional, List
from engines.policy.models import PolicyAttachment, Requirements

class PolicyService:
    def __init__(self):
        # In-memory store for now. Real impl would use Workbench Overlay Store.
        self._attachments: Dict[str, PolicyAttachment] = {}

    def set_policy(self, subject_id: str, attachment: PolicyAttachment) -> None:
        """
        subject_id: Could be a package_id or some other grouping.
        For now, we assume a global flat map or per-package map.
        Let's keep it simple: We store per 'tool_id' or 'package_id'.
        But `tools.call` knows `tool_id` and `scope_name`.
        The Overlay maps tool -> scope -> policy.
        
        So the PolicyService should probably ingest Overlays or be the Overlay Store itself.
        For separation of concerns, let's say PolicyService provides the `check` capability,
        and is fed configurations.
        """
        self._attachments[subject_id] = attachment

    def get_requirements(self, tool_id: str, scope_name: str) -> Requirements:
        """
        Resolve requirements for a specific tool scope.
        Strategy: Look for specific overrides.
        """
        # 1. Simple lookup in globally registered attachments?
        # A real implementation would look up the specific Overlay for this tool version.
        # Here we simulate by keys.
        
        # Flattened lookup simulation
        scope_full = f"{tool_id}.{scope_name}"
        
        # Search all attachments for this scope
        # (Inefficient, but functional for prototype)
        for att in self._attachments.values():
            if scope_full in att.scopes:
                return att.scopes[scope_full]
        
        # Default: Safe (no firearms)
        return Requirements()

# Global instance
_policy_service = PolicyService()

def get_policy_service() -> PolicyService:
    return _policy_service
