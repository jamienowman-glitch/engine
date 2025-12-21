from __future__ import annotations
import json
import uuid
import tempfile
from pathlib import Path
from typing import Optional, List

from engines.media_v2.service import MediaService, get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.audio_field_to_samples.service import AudioFieldToSamplesService, get_audio_field_to_samples_service
from engines.audio_field_to_samples.models import FieldToSamplesRequest
from engines.audio_fx_chain.service import AudioFxChainService, get_audio_fx_chain_service
from engines.audio_fx_chain.models import FxChainRequest
from engines.audio_normalise.service import AudioNormaliseService, get_audio_normalise_service
from engines.audio_normalise.models import NormaliseRequest

from engines.sample_pack_engine.models import SamplePackRequest, SamplePackResult, SamplePackItem
from engines.sample_pack_engine.naming import SamplePackNamer

class SamplePackEngineService:
    def __init__(
        self,
        media_service: Optional[MediaService] = None,
        detect_service: Optional[AudioFieldToSamplesService] = None,
        fx_service: Optional[AudioFxChainService] = None,
        norm_service: Optional[AudioNormaliseService] = None
    ):
        self.media_service = media_service or get_media_service()
        self.detect_service = detect_service or get_audio_field_to_samples_service()
        self.fx_service = fx_service or get_audio_fx_chain_service()
        self.norm_service = norm_service or get_audio_normalise_service()

    def generate_pack(self, req: SamplePackRequest) -> SamplePackResult:
        namer = SamplePackNamer(req.name)
        pack_items: List[SamplePackItem] = []
        
        # 1. Iterate Inputs
        for asset_id in req.input_asset_ids:
            # Run Detection
            det_req = FieldToSamplesRequest(
                tenant_id=req.tenant_id, env=req.env, asset_id=asset_id,
                run_hits=True, run_loops=True, run_phrases=True
            )
            det_res = self.detect_service.process_asset(det_req)
            
            # Collect separated by type to preserve role knowledge
            # (artifacts kind changes after norm, so we must track it)
            labeled_artifacts = []
            for mid in det_res.hit_artifact_ids: labeled_artifacts.append((mid, "hit"))
            for mid in det_res.loop_artifact_ids: labeled_artifacts.append((mid, "loop"))
            for mid in det_res.phrase_artifact_ids: labeled_artifacts.append((mid, "phrase"))
            
            for art_id, source_type in labeled_artifacts:
                current_id = art_id
                
                # 2. FX
                if req.fx_preset_id:
                    fx_req = FxChainRequest(
                        tenant_id=req.tenant_id, env=req.env, artifact_id=current_id,
                        preset_id=req.fx_preset_id
                    )
                    fx_res = self.fx_service.apply_fx_chain(fx_req)
                    current_id = fx_res.artifact_id
                    
                # 3. Normalise
                norm_req = NormaliseRequest(
                    tenant_id=req.tenant_id, env=req.env, artifact_id=current_id,
                    target_lufs=req.normalise_target_lufs
                )
                norm_res = self.norm_service.normalise_artifact(norm_req)
                final_id = norm_res.artifact_id
                
                # Retrieve final artifact to get meta (params) for naming
                art = self.media_service.get_artifact(final_id)
                if not art: continue
                
                # Determine Role
                # Infer from Kind + Meta
                role = "unknown"
                tags = []
                bpm = art.meta.get("features", {}).get("bpm") or art.meta.get("bpm")
                
                if source_type == "hit":
                    # heuristic: check meta for specific hit type if available 
                    # (assuming detection puts 'kick', 'snare' in meta tags or similar)
                    meta_str = str(art.meta).lower()
                    if "kick" in meta_str: role = "kick"
                    elif "snare" in meta_str: role = "snare"
                    elif "hat" in meta_str: role = "hat"
                    else: role = "hit"
                    tags.append("hit")
                elif source_type == "loop":
                    role = "loop"
                    tags.append("loop")
                elif source_type == "phrase":
                    role = "phrase"
                    tags.append("phrase")
                    
                path = namer.get_path(role, tags, bpm)
                
                pack_items.append(SamplePackItem(
                    artifact_id=final_id,
                    path=path,
                    role=role,
                    meta=art.meta
                ))
                
        # 4. Generate Manifest
        manifest_data = {
            "name": req.name,
            "items": [item.dict() for item in pack_items]
        }
        
        manifest_json = json.dumps(manifest_data, indent=2)
        
        # 5. Register Pack Artifact
        # Create a JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(manifest_json)
            tmp_path = Path(f.name)
            
        up_req = MediaUploadRequest(
            tenant_id=req.tenant_id, env=req.env, kind="other",
            source_uri="pending", tags=["generated", "pack", "manifest"]
        )
        new_asset = self.media_service.register_upload(up_req, f"{req.name}_manifest.json", tmp_path.read_bytes())
        
        pack_art = self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=new_asset.id,
                kind="sample_pack", 
                uri=new_asset.source_uri,
                meta={"item_count": len(pack_items)}
            )
        )
        
        if tmp_path.exists():
            tmp_path.unlink()
            
        return SamplePackResult(
            pack_artifact_id=pack_art.id,
            pack_uri=pack_art.uri,
            items=pack_items,
            meta={"item_count": len(pack_items)}
        )

_default_service: Optional[SamplePackEngineService] = None

def get_sample_pack_engine_service() -> SamplePackEngineService:
    global _default_service
    if _default_service is None:
        _default_service = SamplePackEngineService()
    return _default_service
