"""Tests for asset versioning and render lineage tracking."""

import unittest
from datetime import datetime
from engines.image_core.versioning import (
    AssetVersion, RenderLineageEntry, RenderLineage, VersionComparison,
    VersionStatus, AssetVersioningService, get_versioning_service
)


class TestAssetVersion(unittest.TestCase):
    """Test AssetVersion model."""
    
    def test_asset_version_creation(self):
        """Test creating an asset version."""
        version = AssetVersion(
            asset_id="img-123",
            version_number=1,
            artifact_id="art-456",
            file_hash="abc123def456",
            file_size=50000,
            mime_type="image/png"
        )
        
        self.assertEqual(version.asset_id, "img-123")
        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.status, VersionStatus.ACTIVE)
    
    def test_asset_version_with_metadata(self):
        """Test asset version with metadata."""
        version = AssetVersion(
            asset_id="img-123",
            version_number=2,
            artifact_id="art-789",
            file_hash="xyz789",
            file_size=55000,
            metadata={
                "created_by": "system",
                "description": "Updated with better quality",
                "tags": ["high-quality", "final"]
            }
        )
        
        self.assertEqual(version.metadata.description, "Updated with better quality")
        self.assertIn("high-quality", version.metadata.tags)
    
    def test_asset_version_previous_tracking(self):
        """Test version tracking with previous version."""
        version = AssetVersion(
            asset_id="img-123",
            version_number=3,
            artifact_id="art-999",
            file_hash="mmm333",
            file_size=60000,
            previous_version=2
        )
        
        self.assertEqual(version.previous_version, 2)


class TestRenderLineage(unittest.TestCase):
    """Test RenderLineage tracking."""
    
    def test_render_lineage_creation(self):
        """Test creating render lineage."""
        lineage = RenderLineage(
            render_id="render-123",
            tenant_id="tenant-1",
            env="prod",
            composition_hash="comp-hash-123",
            assets_used=[]
        )
        
        self.assertEqual(lineage.render_id, "render-123")
        self.assertIsNotNone(lineage.created_at)
    
    def test_render_lineage_with_assets(self):
        """Test lineage with asset entries."""
        entries = [
            RenderLineageEntry(
                asset_id="img-1",
                version_number=1,
                layer_id="layer-1",
                file_hash="hash1"
            ),
            RenderLineageEntry(
                asset_id="img-2",
                version_number=2,
                layer_id="layer-2",
                file_hash="hash2"
            )
        ]
        
        lineage = RenderLineage(
            render_id="render-123",
            tenant_id="tenant-1",
            env="prod",
            composition_hash="comp-hash",
            assets_used=entries
        )
        
        self.assertEqual(len(lineage.assets_used), 2)
    
    def test_get_asset_versions(self):
        """Test getting version used for specific asset."""
        entries = [
            RenderLineageEntry(asset_id="img-1", version_number=1, layer_id="l1", file_hash="h1"),
            RenderLineageEntry(asset_id="img-2", version_number=3, layer_id="l2", file_hash="h2"),
        ]
        
        lineage = RenderLineage(
            render_id="r1",
            tenant_id="t1",
            env="prod",
            composition_hash="ch",
            assets_used=entries
        )
        
        self.assertEqual(lineage.get_asset_versions("img-1"), 1)
        self.assertEqual(lineage.get_asset_versions("img-2"), 3)
        self.assertIsNone(lineage.get_asset_versions("img-3"))
    
    def test_get_all_assets(self):
        """Test getting all assets in lineage."""
        entries = [
            RenderLineageEntry(asset_id="img-1", version_number=1, layer_id="l1", file_hash="h1"),
            RenderLineageEntry(asset_id="img-2", version_number=2, layer_id="l2", file_hash="h2"),
        ]
        
        lineage = RenderLineage(
            render_id="r1",
            tenant_id="t1",
            env="prod",
            composition_hash="ch",
            assets_used=entries
        )
        
        all_assets = lineage.get_all_assets()
        self.assertEqual(all_assets, {"img-1": 1, "img-2": 2})


class TestAssetVersioningService(unittest.TestCase):
    """Test AssetVersioningService."""
    
    def setUp(self):
        """Initialize service."""
        self.service = AssetVersioningService()
    
    def test_create_version(self):
        """Test creating a new asset version."""
        version = self.service.create_version(
            asset_id="img-123",
            artifact_id="art-456",
            file_hash="hash123",
            file_size=50000,
            description="First version"
        )
        
        self.assertEqual(version.version_number, 1)
        self.assertIsNone(version.previous_version)
    
    def test_create_multiple_versions(self):
        """Test creating multiple versions of same asset."""
        v1 = self.service.create_version(
            asset_id="img-123",
            artifact_id="art-1",
            file_hash="h1",
            file_size=1000
        )
        
        v2 = self.service.create_version(
            asset_id="img-123",
            artifact_id="art-2",
            file_hash="h2",
            file_size=1100
        )
        
        self.assertEqual(v1.version_number, 1)
        self.assertEqual(v2.version_number, 2)
        self.assertEqual(v2.previous_version, 1)
    
    def test_get_version(self):
        """Test retrieving specific version."""
        created = self.service.create_version(
            asset_id="img-123",
            artifact_id="art-456",
            file_hash="hash123",
            file_size=50000
        )
        
        retrieved = self.service.get_version("img-123", 1)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.artifact_id, "art-456")
    
    def test_get_nonexistent_version(self):
        """Test getting non-existent version."""
        result = self.service.get_version("img-999", 1)
        self.assertIsNone(result)
    
    def test_get_latest_version(self):
        """Test getting latest active version."""
        self.service.create_version("img-123", "art-1", "h1", 1000)
        v2 = self.service.create_version("img-123", "art-2", "h2", 1100)
        
        latest = self.service.get_latest_version("img-123")
        
        self.assertIsNotNone(latest)
        self.assertEqual(latest.version_number, 2)
        self.assertEqual(latest.artifact_id, "art-2")
    
    def test_get_latest_skips_deprecated(self):
        """Test that get_latest ignores deprecated versions."""
        self.service.create_version("img-123", "art-1", "h1", 1000)
        v2 = self.service.create_version("img-123", "art-2", "h2", 1100)
        
        # Deprecate v2
        self.service.deprecate_version("img-123", 2)
        
        # Latest should now be v1
        latest = self.service.get_latest_version("img-123")
        self.assertEqual(latest.version_number, 1)
    
    def test_get_all_versions(self):
        """Test getting all versions."""
        self.service.create_version("img-123", "art-1", "h1", 1000)
        self.service.create_version("img-123", "art-2", "h2", 1100)
        self.service.create_version("img-123", "art-3", "h3", 1200)
        
        all_versions = self.service.get_all_versions("img-123")
        
        self.assertEqual(len(all_versions), 3)
        self.assertEqual(all_versions[0].version_number, 1)
        self.assertEqual(all_versions[2].version_number, 3)
    
    def test_deprecate_version(self):
        """Test deprecating a version."""
        self.service.create_version("img-123", "art-1", "h1", 1000)
        
        success = self.service.deprecate_version("img-123", 1)
        
        self.assertTrue(success)
        version = self.service.get_version("img-123", 1)
        self.assertEqual(version.status, VersionStatus.DEPRECATED)
    
    def test_archive_version(self):
        """Test archiving a version."""
        self.service.create_version("img-123", "art-1", "h1", 1000)
        
        success = self.service.archive_version("img-123", 1)
        
        self.assertTrue(success)
        version = self.service.get_version("img-123", 1)
        self.assertEqual(version.status, VersionStatus.ARCHIVED)
    
    def test_compare_versions(self):
        """Test comparing two versions."""
        self.service.create_version(
            "img-123",
            "art-1",
            "hash1",
            1000,
            description="Original"
        )
        self.service.create_version(
            "img-123",
            "art-2",
            "hash2",
            1500,
            description="Updated"
        )
        
        comparison = self.service.compare_versions("img-123", 1, 2)
        
        self.assertIsNotNone(comparison)
        self.assertTrue(comparison.content_different)
        self.assertEqual(comparison.size_a, 1000)
        self.assertEqual(comparison.size_b, 1500)
    
    def test_compare_identical_versions(self):
        """Test comparing identical versions."""
        self.service.create_version("img-123", "art-1", "hash1", 1000)
        self.service.create_version("img-123", "art-2", "hash1", 1000)
        
        comparison = self.service.compare_versions("img-123", 1, 2)
        
        self.assertFalse(comparison.content_different)
    
    def test_record_render_lineage(self):
        """Test recording render lineage."""
        assets_used = [
            RenderLineageEntry(asset_id="img-1", version_number=1, layer_id="l1", file_hash="h1"),
            RenderLineageEntry(asset_id="img-2", version_number=2, layer_id="l2", file_hash="h2"),
        ]
        
        lineage = self.service.record_render_lineage(
            render_id="render-123",
            tenant_id="tenant-1",
            env="prod",
            assets_used=assets_used,
            composition_hash="comp-hash"
        )
        
        self.assertEqual(lineage.render_id, "render-123")
        self.assertEqual(len(lineage.assets_used), 2)
    
    def test_get_render_lineage(self):
        """Test retrieving render lineage."""
        assets = [RenderLineageEntry(asset_id="img-1", version_number=1, layer_id="l1", file_hash="h1")]
        
        self.service.record_render_lineage(
            "render-123",
            "tenant-1",
            "prod",
            assets,
            composition_hash="ch"
        )
        
        retrieved = self.service.get_render_lineage("render-123")
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(len(retrieved.assets_used), 1)
    
    def test_get_renders_using_asset(self):
        """Test finding renders that used an asset."""
        assets1 = [RenderLineageEntry(asset_id="img-1", version_number=1, layer_id="l1", file_hash="h1")]
        assets2 = [RenderLineageEntry(asset_id="img-1", version_number=2, layer_id="l1", file_hash="h2")]
        
        self.service.record_render_lineage("r1", "t1", "prod", assets1, composition_hash="ch1")
        self.service.record_render_lineage("r2", "t1", "prod", assets2, composition_hash="ch2")
        
        renders = self.service.get_renders_using_asset("img-1")
        
        self.assertEqual(len(renders), 2)
    
    def test_get_renders_using_asset_specific_version(self):
        """Test finding renders using specific asset version."""
        assets1 = [RenderLineageEntry(asset_id="img-1", version_number=1, layer_id="l1", file_hash="h1")]
        assets2 = [RenderLineageEntry(asset_id="img-1", version_number=2, layer_id="l1", file_hash="h2")]
        
        self.service.record_render_lineage("r1", "t1", "prod", assets1, composition_hash="ch1")
        self.service.record_render_lineage("r2", "t1", "prod", assets2, composition_hash="ch2")
        
        renders = self.service.get_renders_using_asset("img-1", version_number=1)
        
        self.assertEqual(len(renders), 1)
    
    def test_get_renders_for_composition(self):
        """Test getting all renders for a composition."""
        assets = [RenderLineageEntry(asset_id="img-1", version_number=1, layer_id="l1", file_hash="h1")]
        
        self.service.record_render_lineage("r1", "t1", "prod", assets, composition_id="comp-1", composition_hash="ch1")
        self.service.record_render_lineage("r2", "t1", "prod", assets, composition_id="comp-1", composition_hash="ch2")
        self.service.record_render_lineage("r3", "t1", "prod", assets, composition_id="comp-2", composition_hash="ch3")
        
        renders = self.service.get_renders_for_composition("comp-1")
        
        self.assertEqual(len(renders), 2)
    
    def test_rerender_with_version(self):
        """Test getting data for re-rendering with different version."""
        assets = [RenderLineageEntry(asset_id="img-1", version_number=1, layer_id="l1", file_hash="h1")]
        
        self.service.record_render_lineage("r1", "t1", "prod", assets, composition_id="comp-1", composition_hash="ch")
        self.service.create_version("img-1", "art-1", "h1", 1000)
        self.service.create_version("img-1", "art-2", "h2", 1100)
        
        rerender_info = self.service.rerender_with_version("r1", "img-1", 2)
        
        self.assertIsNotNone(rerender_info)
        self.assertEqual(rerender_info["asset_to_update"], "img-1")
        self.assertEqual(rerender_info["new_version"], 2)
        self.assertEqual(rerender_info["new_artifact_id"], "art-2")


class TestVersioningEdgeCases(unittest.TestCase):
    """Test edge cases in versioning."""
    
    def setUp(self):
        """Initialize service."""
        self.service = AssetVersioningService()
    
    def test_size_change_calculation(self):
        """Test size change percentage calculation."""
        self.service.create_version("img-1", "art-1", "h1", 1000)
        self.service.create_version("img-1", "art-2", "h2", 2000)
        
        comparison = self.service.compare_versions("img-1", 1, 2)
        
        # 2000 - 1000 = 1000, 1000 / 1000 = 1.0, * 100 = 100%
        self.assertAlmostEqual(comparison.size_change_percent, 100.0, places=1)
    
    def test_multiple_assets_in_render(self):
        """Test render with multiple different assets."""
        assets = [
            RenderLineageEntry(asset_id="img-1", version_number=1, layer_id="bg", file_hash="h1"),
            RenderLineageEntry(asset_id="img-2", version_number=2, layer_id="fg", file_hash="h2"),
            RenderLineageEntry(asset_id="img-3", version_number=1, layer_id="accent", file_hash="h3"),
        ]
        
        lineage = self.service.record_render_lineage("r1", "t1", "prod", assets, composition_hash="ch")
        
        self.assertEqual(len(lineage.assets_used), 3)
        self.assertEqual(lineage.get_asset_versions("img-2"), 2)


if __name__ == "__main__":
    unittest.main()
