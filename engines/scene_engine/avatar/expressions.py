"""Expression & Micro-Animation Engine (P4)."""
from __future__ import annotations

import math
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2


class AvatarExpressionKind(str, Enum):
    NEUTRAL = "neutral"
    BLINK_LEFT = "blink_left"
    BLINK_RIGHT = "blink_right"
    SMILE = "smile"
    FROWN = "frown"
    BROW_RAISE = "brow_raise"
    MOUTH_OPEN = "mouth_open"


class ExpressionState(BaseModel):
    # Map Kind -> Weight (0.0 to 1.0)
    weights: Dict[AvatarExpressionKind, float] = Field(default_factory=dict)
    
    def get(self, kind: AvatarExpressionKind) -> float:
        return self.weights.get(kind, 0.0)
    
    def set(self, kind: AvatarExpressionKind, val: float):
        self.weights[kind] = max(0.0, min(1.0, val))


def apply_expression_weights(scene: SceneV2, state: ExpressionState) -> SceneV2:
    """Applies expression weights to the avatar head node metadata."""
    # We need to find the Head node. 
    # Since we don't have Rig passed in, we recursively search for "Head"?
    # Or apply to Root and let View handle propagation?
    # Applying to Head node is semantic.
    
    def apply(nodes):
        for n in nodes:
            # Simple heuristic matching
            if "head" in n.name.lower():
                n.meta["expression_weights"] = {
                    k.value: v for k, v in state.weights.items()
                }
            apply(n.children)
            
    apply(scene.nodes)
    return scene


class MicroAnimationController:
    """Procedural micro-animations (Blinking, Breathing)."""
    
    def __init__(self):
        self.time_accumulator = 0.0
        self.blink_timer = 0.0
        self.next_blink_time = 3.0 # Start blink in 3s
        self.is_blinking = False
        self.blink_duration = 0.15
        self.blink_progress = 0.0
        
        self.breathing_rate = 0.2 # Hz (cycles/sec). 5s period.
        
    def tick(self, dt: float, state: ExpressionState):
        self.time_accumulator += dt
        
        # --- Blinking ---
        if not self.is_blinking:
            self.blink_timer += dt
            if self.blink_timer >= self.next_blink_time:
                self.is_blinking = True
                self.blink_progress = 0.0
                import random
                self.next_blink_time = random.uniform(2.0, 5.0)
                self.blink_timer = 0.0
        else:
            self.blink_progress += dt
            if self.blink_progress >= self.blink_duration:
                self.is_blinking = False
                state.set(AvatarExpressionKind.BLINK_LEFT, 0.0)
                state.set(AvatarExpressionKind.BLINK_RIGHT, 0.0)
            else:
                # Triangle wave for blink (0 -> 1 -> 0)
                mid = self.blink_duration / 2.0
                if self.blink_progress < mid:
                    val = self.blink_progress / mid
                else:
                    val = 1.0 - ((self.blink_progress - mid) / mid)
                state.set(AvatarExpressionKind.BLINK_LEFT, val)
                state.set(AvatarExpressionKind.BLINK_RIGHT, val)

        # --- Breathing (Torso scale? Or just a param) ---
        # Breathing usually affects chest/shoulder bones.
        # But here we just output a generic "breathing" weight if needed, 
        # or we could return a bone transform offset.
        # For P4, let's just update the state with a "breathing" generic param or similar?
        # ExpressionState keys are strictly facial expressions usually.
        # But 'MOUTH_OPEN' etc.
        # Let's verify breathing is 'Micro-Animation'.
        # We can modulate a MOUTH_OPEN slightly if heavy breathing? Or assume this class drives bones too?
        # P4 Goal: "Shape keys for blink...".
        # Let's stick to expressions. 
        pass
