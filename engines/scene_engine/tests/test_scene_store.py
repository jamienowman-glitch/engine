"""Tests for Scene Store (Level B)."""
from unittest.mock import MagicMock, patch

from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.core.types import Camera
from engines.scene_engine.store.models import LoadSceneRequest, SaveSceneRequest
from engines.scene_engine.store.service import SceneStoreService


def test_save_and_load_scene_dry_run():
    # Only verify logic flow, mock firestore key parts
    with patch("engines.scene_engine.store.service.firestore") as mock_fs:
        # Mock client
        mock_client = MagicMock()
        mock_fs.Client.return_value = mock_client
        mock_col = MagicMock()
        mock_client.collection.return_value = mock_col
        mock_doc_ref = MagicMock()
        mock_col.document.return_value = mock_doc_ref
        
        # Service
        service = SceneStoreService(client=mock_client)
        
        # Data
        scene = SceneV2(id="test_scene")
        
        # Save
        service.save_scene(SaveSceneRequest(scene=scene, name="My Scene"))
        
        # Assert calls
        mock_col.document.assert_called_with("test_scene")
        mock_doc_ref.set.assert_called()
        args, _ = mock_doc_ref.set.call_args
        envelope = args[0]
        assert envelope["scene_id"] == "test_scene"
        assert envelope["name"] == "My Scene"
        assert envelope["scene_data"]["id"] == "test_scene"

        # Load Mock
        mock_doc_snap = MagicMock()
        mock_doc_snap.exists = True
        mock_doc_snap.to_dict.return_value = envelope
        mock_doc_ref.get.return_value = mock_doc_snap
        
        # Load
        res = service.load_scene(LoadSceneRequest(scene_id="test_scene"))
        assert res.scene.id == "test_scene"
