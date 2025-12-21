"""
Tests for PHASE_AV03: Asset Kits & Materials.

Covers:
- Kit registry and management
- Kit attachment with deterministic transforms
- UV/texel density validation
- Material preset application
"""
import pytest
from datetime import datetime

from engines.scene_engine.avatar.models import (
    KitSlot,
    KitMetadata,
    KitRegistry,
    KitAttachment,
    UVValidationResult,
    MaterialPreset,
)
from engines.scene_engine.avatar.service import (
    create_kit_registry,
    attach_kit,
    validate_kit_uv_density,
    apply_material_preset_to_kit,
)


class TestKitRegistry:
    """Test kit registry functionality."""
    
    def test_create_registry(self):
        """Creating a registry should work."""
        registry = create_kit_registry()
        
        assert registry.id is not None
        assert len(registry.kits) == 0
    
    def test_register_kit(self):
        """Registering a kit should add it to registry."""
        registry = create_kit_registry()
        
        kit = KitMetadata(
            kit_id="outfit_casual_1",
            slot=KitSlot.OUTFIT_FULL,
            name="Casual Outfit",
            compatible_body_types=["male", "female"]
        )
        registry.register_kit(kit)
        
        assert len(registry.kits) == 1
        assert registry.get_kit("outfit_casual_1") == kit
    
    def test_list_kits_by_slot(self):
        """Listing kits by slot should filter correctly."""
        registry = create_kit_registry()
        
        # Register multiple kits
        kit_outfit = KitMetadata(
            kit_id="outfit_1",
            slot=KitSlot.OUTFIT_FULL,
            name="Outfit 1"
        )
        kit_hair = KitMetadata(
            kit_id="hair_1",
            slot=KitSlot.HAIR,
            name="Hair 1"
        )
        kit_outfit2 = KitMetadata(
            kit_id="outfit_2",
            slot=KitSlot.OUTFIT_FULL,
            name="Outfit 2"
        )
        
        registry.register_kit(kit_outfit)
        registry.register_kit(kit_hair)
        registry.register_kit(kit_outfit2)
        
        # List by slot
        outfit_kits = registry.list_kits_by_slot(KitSlot.OUTFIT_FULL)
        hair_kits = registry.list_kits_by_slot(KitSlot.HAIR)
        
        assert len(outfit_kits) == 2
        assert len(hair_kits) == 1
        assert all(k.slot == KitSlot.OUTFIT_FULL for k in outfit_kits)


class TestKitAttachment:
    """Test kit attachment."""
    
    def test_attach_kit_basic(self):
        """Attaching a kit should create attachment record."""
        kit = KitMetadata(
            kit_id="outfit_1",
            slot=KitSlot.OUTFIT_FULL,
            name="Casual Outfit",
            compatible_body_types=["male", "female"]
        )
        
        attachment = attach_kit(kit, body_type="male", scale=1.0)
        
        assert attachment.kit_id == "outfit_1"
        assert attachment.body_type == "male"
        assert attachment.scale == 1.0
    
    def test_attach_kit_incompatible_body_type(self):
        """Attaching kit to incompatible body type should raise error."""
        kit = KitMetadata(
            kit_id="outfit_1",
            slot=KitSlot.OUTFIT_FULL,
            name="Male Outfit",
            compatible_body_types=["male"]
        )
        
        with pytest.raises(ValueError):
            attach_kit(kit, body_type="female")
    
    def test_attach_kit_scale_clamping(self):
        """Kit scale should be clamped to sensible range."""
        kit = KitMetadata(
            kit_id="outfit_1",
            slot=KitSlot.OUTFIT_FULL,
            name="Outfit"
        )
        
        # Test too large scale
        attachment = attach_kit(kit, body_type="male", scale=50.0)
        assert attachment.scale == 10.0  # Clamped max
        
        # Test too small scale
        attachment = attach_kit(kit, body_type="male", scale=0.01)
        assert attachment.scale == 0.1  # Clamped min
        
        # Test valid scale
        attachment = attach_kit(kit, body_type="male", scale=1.5)
        assert attachment.scale == 1.5
    
    def test_attach_kit_default_transforms(self):
        """Attaching without explicit transforms should use defaults."""
        kit = KitMetadata(
            kit_id="outfit_1",
            slot=KitSlot.OUTFIT_FULL,
            name="Outfit"
        )
        
        attachment = attach_kit(kit, body_type="male")
        
        assert attachment.position == [0.0, 0.0, 0.0]
        assert attachment.rotation == [0.0, 0.0, 0.0]
    
    def test_attach_kit_custom_transforms(self):
        """Attaching with custom transforms should apply them."""
        kit = KitMetadata(
            kit_id="outfit_1",
            slot=KitSlot.OUTFIT_FULL,
            name="Outfit"
        )
        
        pos = [0.1, 0.2, 0.3]
        rot = [0.1, 0.2, 0.3]
        
        attachment = attach_kit(kit, body_type="male", position=pos, rotation=rot)
        
        assert attachment.position == pos
        assert attachment.rotation == rot


class TestUVValidation:
    """Test UV/texel density validation."""
    
    def test_validate_valid_uvs(self):
        """Valid UV layout should pass validation."""
        vertices = [
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
        ]
        uvs = [
            [0.0, 0.0],
            [1.0, 0.0],
            [0.5, 1.0],
        ]
        
        result = validate_kit_uv_density(vertices, uvs)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_mismatched_counts(self):
        """Mismatched UV/vertex counts should fail."""
        vertices = [[0, 0, 0], [1, 0, 0]]
        uvs = [[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]]  # Extra UV
        
        result = validate_kit_uv_density(vertices, uvs)
        
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_validate_overlap_detection(self):
        """Overlapping UVs should be detected."""
        vertices = [[0, 0, 0], [1, 0, 0], [1, 1, 0]]
        uvs = [
            [0.0, 0.0],
            [0.0, 0.0],  # Duplicate UV
            [1.0, 1.0],
        ]
        
        result = validate_kit_uv_density(vertices, uvs)
        
        assert result.overlap_detected
    
    def test_validate_coverage_warning(self):
        """Poor UV coverage should generate warning."""
        vertices = [[0, 0, 0], [1, 0, 0], [1, 1, 0]]
        uvs = [
            [2.0, 2.0],  # Outside 0-1
            [3.0, 3.0],  # Outside 0-1
            [4.0, 4.0],  # Outside 0-1
        ]
        
        result = validate_kit_uv_density(vertices, uvs)
        
        assert len(result.warnings) > 0


class TestMaterialPreset:
    """Test material preset application."""
    
    def test_create_material_preset(self):
        """Creating a material preset should work."""
        preset = MaterialPreset(
            id="mat_fabric_cotton",
            name="Cotton Fabric",
            description="Natural cotton material",
            properties={
                "roughness": 0.5,
                "metallic": 0.0,
            }
        )
        
        assert preset.id == "mat_fabric_cotton"
        assert preset.properties["roughness"] == 0.5
    
    def test_apply_material_preset_to_kit(self):
        """Applying material preset should update kit."""
        kit_attachment = KitAttachment(
            kit_id="outfit_1",
            slot=KitSlot.OUTFIT_FULL,
            body_type="male"
        )
        
        preset = MaterialPreset(
            id="mat_fabric",
            name="Fabric"
        )
        
        kit_attachment = apply_material_preset_to_kit(kit_attachment, preset)
        
        # Check preset is recorded
        assert f"preset_{preset.id}" in kit_attachment.applied_materials


class TestKitWorkflow:
    """Integration tests for typical kit usage workflows."""
    
    def test_create_and_attach_outfit(self):
        """Create outfit kit and attach to avatar."""
        registry = create_kit_registry()
        
        # Create outfit kit
        outfit_kit = KitMetadata(
            kit_id="casual_outfit",
            slot=KitSlot.OUTFIT_FULL,
            name="Casual Outfit",
            compatible_body_types=["male", "female", "neutral"],
            default_scale=1.0,
            default_materials={
                "fabric_main": "mat_cotton",
                "fabric_accent": "mat_denim",
            }
        )
        registry.register_kit(outfit_kit)
        
        # Attach to avatar
        attachment = attach_kit(outfit_kit, body_type="male", scale=1.1)
        
        assert attachment.kit_id == "casual_outfit"
        assert attachment.scale == 1.1
        assert "fabric_main" in attachment.applied_materials
    
    def test_attach_multiple_kits(self):
        """Attach multiple kits (outfit + hair) to avatar."""
        registry = create_kit_registry()
        
        # Create kits
        outfit = KitMetadata(
            kit_id="outfit_1",
            slot=KitSlot.OUTFIT_FULL,
            name="Outfit"
        )
        hair = KitMetadata(
            kit_id="hair_1",
            slot=KitSlot.HAIR,
            name="Hair"
        )
        
        registry.register_kit(outfit)
        registry.register_kit(hair)
        
        # Attach both
        outfit_attach = attach_kit(outfit, body_type="female")
        hair_attach = attach_kit(hair, body_type="female")
        
        assert outfit_attach.slot == KitSlot.OUTFIT_FULL
        assert hair_attach.slot == KitSlot.HAIR
    
    def test_validate_and_apply_material(self):
        """Validate kit UVs and apply material preset."""
        # Create kit mesh (simple triangle)
        vertices = [[0, 0, 0], [1, 0, 0], [1, 1, 0]]
        uvs = [[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]]
        
        # Validate UVs
        uv_result = validate_kit_uv_density(vertices, uvs)
        assert uv_result.is_valid
        
        # Create and attach kit
        kit = KitMetadata(
            kit_id="validated_outfit",
            slot=KitSlot.OUTFIT_FULL,
            name="Outfit"
        )
        attachment = attach_kit(kit, body_type="male")
        
        # Apply material
        preset = MaterialPreset(
            id="mat_fancy",
            name="Fancy Material"
        )
        attachment = apply_material_preset_to_kit(attachment, preset)
        
        assert "preset_mat_fancy" in attachment.applied_materials


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
