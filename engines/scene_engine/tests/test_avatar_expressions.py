"""Tests for Avatar Expressions & Micro-Animations (P4)."""

import time
from engines.scene_engine.avatar.expressions import (
    AvatarExpressionKind,
    ExpressionState,
    MicroAnimationController,
    apply_expression_weights,
)
from engines.scene_engine.core.scene_v2 import SceneNodeV2, SceneV2
from engines.scene_engine.core.geometry import Transform, Vector3, Quaternion

def test_apply_expression_weights():
    # Setup Scene with Head
    head = SceneNodeV2(
        id="head", name="ReferenceHead", 
        transform=Transform(position=Vector3(x=0,y=0,z=0), rotation=Quaternion(x=0,y=0,z=0,w=1), scale=Vector3(x=1,y=1,z=1))
    )
    scene = SceneV2(id="s1", nodes=[head])
    
    state = ExpressionState()
    state.set(AvatarExpressionKind.SMILE, 0.8)
    state.set(AvatarExpressionKind.BLINK_LEFT, 0.5)
    
    apply_expression_weights(scene, state)
    
    # Check meta
    assert "expression_weights" in head.meta
    weights = head.meta["expression_weights"]
    assert weights["smile"] == 0.8
    assert weights["blink_left"] == 0.5

def test_micro_animation_blinking():
    # Verify controller logic
    ctrl = MicroAnimationController()
    state = ExpressionState()
    
    # Set next blink time to something small predictable
    ctrl.next_blink_time = 0.1
    ctrl.blink_timer = 0.0
    
    # Tick 1: No blink yet
    ctrl.tick(0.05, state)
    assert not ctrl.is_blinking
    assert state.get(AvatarExpressionKind.BLINK_LEFT) == 0.0
    
    # Tick 2: Trigger blink
    ctrl.tick(0.1, state) # total 0.15 > 0.1
    assert ctrl.is_blinking
    # Blink progress starts at 0.
    
    # Tick 3: Inside blink
    ctrl.tick(0.05, state)
    val = state.get(AvatarExpressionKind.BLINK_LEFT)
    assert val > 0.0
    
    # Tick 4: Finish blink
    ctrl.tick(0.5, state) # long time
    assert not ctrl.is_blinking
    assert state.get(AvatarExpressionKind.BLINK_LEFT) == 0.0
