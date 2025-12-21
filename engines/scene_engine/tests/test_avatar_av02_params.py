"""
Tests for PHASE_AV02: Parametric Avatar Builder.

Covers:
- Parameter sliders with bounds
- Avatar presets (male/female/child)
- History/undo stack
- Deterministic seeding
"""
import pytest
from datetime import datetime

from engines.scene_engine.avatar.models import (
    AvatarParamSlider,
    AvatarParamSet,
    AvatarPreset,
    AvatarParamHistory,
    AvatarBuilder,
)
from engines.scene_engine.avatar.service import (
    create_avatar_builder,
    apply_preset_to_builder,
    set_param_value,
    undo_avatar_change,
    DEFAULT_PARAM_SLIDERS,
    AVATAR_PRESETS,
)


class TestAvatarParamSlider:
    """Test parameter slider functionality."""
    
    def test_slider_clamping(self):
        """Slider should clamp values to [min, max]."""
        slider = AvatarParamSlider(
            name="height",
            min_value=1.0,
            max_value=2.0,
            default_value=1.5
        )
        
        # Test clamping
        assert slider.clamp(0.5) == 1.0  # Below min
        assert slider.clamp(1.5) == 1.5  # In range
        assert slider.clamp(2.5) == 2.0  # Above max
    
    def test_slider_defaults(self):
        """Slider should have sensible defaults."""
        for name, slider in DEFAULT_PARAM_SLIDERS.items():
            assert slider.min_value < slider.default_value < slider.max_value
            assert slider.category in ["body", "face", "hair"]


class TestAvatarParamSet:
    """Test parameter set management."""
    
    def test_create_param_set(self):
        """Creating a param set should work."""
        params = {
            "height": 1.75,
            "chest_width": 0.55,
        }
        param_set = AvatarParamSet(values=params, seed="test_seed")
        
        assert param_set.values == params
        assert param_set.seed == "test_seed"
        assert param_set.created_at is not None
    
    def test_param_set_determinism(self):
        """Same params with same seed should hash identically."""
        params1 = AvatarParamSet(
            values={"height": 1.75, "chest_width": 0.55},
            seed="test"
        )
        params2 = AvatarParamSet(
            values={"height": 1.75, "chest_width": 0.55},
            seed="test"
        )
        
        # Same content -> same hash
        assert params1.compute_hash() == params2.compute_hash()
        
        # Different params -> different hash
        params3 = AvatarParamSet(
            values={"height": 1.80, "chest_width": 0.55},
            seed="test"
        )
        assert params3.compute_hash() != params1.compute_hash()
    
    def test_param_set_seed_affects_hash(self):
        """Different seeds should produce different hashes."""
        params1 = AvatarParamSet(values={"height": 1.75}, seed="seed1")
        params2 = AvatarParamSet(values={"height": 1.75}, seed="seed2")
        
        assert params1.compute_hash() != params2.compute_hash()


class TestAvatarPreset:
    """Test avatar presets."""
    
    def test_preset_apply(self):
        """Preset should apply overrides to params."""
        preset = AvatarPreset(
            id="test_preset",
            name="Test",
            base_params={"height": 2.0, "chest_width": 0.6},
            seed="test"
        )
        
        base_params = {"height": 1.5, "chest_width": 0.5, "face_width": 0.15}
        result = preset.apply_to_params(base_params)
        
        # Should override height and chest_width, keep face_width
        assert result["height"] == 2.0
        assert result["chest_width"] == 0.6
        assert result["face_width"] == 0.15
    
    def test_builtin_presets_exist(self):
        """Builtin presets should be defined."""
        assert "casual_male" in AVATAR_PRESETS
        assert "casual_female" in AVATAR_PRESETS
        assert "child" in AVATAR_PRESETS
    
    def test_preset_genders(self):
        """Presets should have correct genders."""
        male_preset = AVATAR_PRESETS["casual_male"]
        female_preset = AVATAR_PRESETS["casual_female"]
        child_preset = AVATAR_PRESETS["child"]
        
        assert male_preset.gender == "male"
        assert female_preset.gender == "female"
        assert child_preset.gender == "child"
    
    def test_preset_determinism(self):
        """Applying same preset twice should be identical."""
        preset = AVATAR_PRESETS["casual_male"]
        
        params1 = preset.apply_to_params({"height": 1.0})
        params2 = preset.apply_to_params({"height": 1.0})
        
        assert params1 == params2


class TestAvatarBuilder:
    """Test avatar builder state machine."""
    
    def test_create_default_builder(self):
        """Creating default builder should work."""
        builder = create_avatar_builder()
        
        assert builder.id is not None
        assert builder.param_set is not None
        assert len(builder.history_stack) == 0
        assert builder.max_history_depth == 100
    
    def test_create_builder_with_preset(self):
        """Creating builder with preset should apply it."""
        builder = create_avatar_builder(preset_name="casual_male")
        
        # Check that preset values are applied
        assert builder.param_set.values["height"] == 1.75
        assert builder.param_set.values["chest_width"] == 0.55
        assert builder.param_set.seed == "casual_male_seed"
    
    def test_apply_preset_invalid(self):
        """Applying invalid preset should raise error."""
        builder = create_avatar_builder()
        
        with pytest.raises(ValueError):
            apply_preset_to_builder(builder, "nonexistent_preset")
    
    def test_apply_preset_adds_to_history(self):
        """Applying preset should add old state to history."""
        builder = create_avatar_builder(preset_name="casual_male")
        initial_height = builder.param_set.values["height"]
        
        # Apply different preset
        builder = apply_preset_to_builder(builder, "casual_female")
        
        # Check history has entry
        assert len(builder.history_stack) == 1
        history_entry = builder.history_stack[0]
        assert history_entry.param_set.values["height"] == initial_height
    
    def test_set_param_value_clamping(self):
        """Setting param should clamp to bounds."""
        builder = create_avatar_builder()
        
        # Set height above max
        builder = set_param_value(builder, "height", 5.0)
        
        # Should be clamped
        assert builder.param_set.values["height"] == DEFAULT_PARAM_SLIDERS["height"].max_value
    
    def test_set_param_adds_to_history(self):
        """Setting param should add old state to history."""
        builder = create_avatar_builder()
        initial_height = builder.param_set.values["height"]
        
        builder = set_param_value(builder, "height", 2.0)
        
        # Check history
        assert len(builder.history_stack) == 1
        assert builder.history_stack[0].param_set.values["height"] == initial_height
    
    def test_set_invalid_param(self):
        """Setting non-existent param should raise error."""
        builder = create_avatar_builder()
        
        with pytest.raises(ValueError):
            set_param_value(builder, "nonexistent_param", 1.0)
    
    def test_undo_single_change(self):
        """Undoing one change should restore prior state."""
        builder = create_avatar_builder()
        initial_height = builder.param_set.values["height"]
        
        # Make change
        builder = set_param_value(builder, "height", 2.0)
        assert builder.param_set.values["height"] == 2.0
        
        # Undo
        builder = undo_avatar_change(builder)
        assert builder.param_set.values["height"] == initial_height
    
    def test_undo_multiple_changes(self):
        """Undoing multiple changes should restore in correct order."""
        builder = create_avatar_builder()
        
        # Make several changes
        builder = set_param_value(builder, "height", 1.8)
        builder = set_param_value(builder, "chest_width", 0.6)
        builder = set_param_value(builder, "face_width", 0.18)
        
        # Undo in reverse order
        builder = undo_avatar_change(builder)
        assert builder.param_set.values["face_width"] != 0.18
        
        builder = undo_avatar_change(builder)
        assert builder.param_set.values["chest_width"] != 0.6
        
        builder = undo_avatar_change(builder)
        assert builder.param_set.values["height"] != 1.8
    
    def test_undo_empty_history(self):
        """Undoing with empty history should not crash."""
        builder = create_avatar_builder()
        initial_height = builder.param_set.values["height"]
        
        # Try to undo with no history
        builder = undo_avatar_change(builder)
        
        # Should be unchanged
        assert builder.param_set.values["height"] == initial_height
    
    def test_history_max_depth(self):
        """History should respect max depth limit."""
        builder = create_avatar_builder()
        builder.max_history_depth = 5
        
        # Make 10 changes
        for i in range(10):
            builder = set_param_value(builder, "height", 1.5 + i * 0.01)
        
        # History should only contain last 5
        assert len(builder.history_stack) <= 5
    
    def test_param_set_determinism(self):
        """Same param values + seed should hash identically."""
        builder1 = create_avatar_builder(preset_name="casual_male")
        builder2 = create_avatar_builder(preset_name="casual_male")
        
        # Same seed should produce same hash
        hash1 = builder1.param_set.compute_hash()
        hash2 = builder2.param_set.compute_hash()
        assert hash1 == hash2


class TestAvatarBuilderWorkflow:
    """Integration tests for typical avatar builder workflows."""
    
    def test_create_male_avatar(self):
        """Create a male avatar from scratch."""
        builder = create_avatar_builder(preset_name="casual_male")
        
        assert builder.param_set.values["height"] == 1.75
        assert builder.param_set.values["eye_size"] == 1.0
    
    def test_create_female_avatar_and_modify(self):
        """Create female avatar and tweak parameters."""
        builder = create_avatar_builder(preset_name="casual_female")
        
        # Increase height slightly
        builder = set_param_value(builder, "height", 1.70)
        assert builder.param_set.values["height"] == 1.70
        
        # Increase eye size
        builder = set_param_value(builder, "eye_size", 1.25)
        assert builder.param_set.values["eye_size"] == 1.25
    
    def test_switch_presets_with_undo(self):
        """Switch between presets and undo."""
        builder = create_avatar_builder(preset_name="casual_male")
        male_height = builder.param_set.values["height"]
        
        # Switch to female
        builder = apply_preset_to_builder(builder, "casual_female")
        female_height = builder.param_set.values["height"]
        assert female_height != male_height
        
        # Undo to male
        builder = undo_avatar_change(builder)
        assert builder.param_set.values["height"] == male_height
    
    def test_deterministic_generation(self):
        """Same workflow should produce same result."""
        def build_avatar():
            b = create_avatar_builder(preset_name="casual_male")
            b = set_param_value(b, "height", 1.80)
            b = set_param_value(b, "face_width", 0.17)
            return b.param_set.compute_hash()
        
        hash1 = build_avatar()
        hash2 = build_avatar()
        assert hash1 == hash2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
