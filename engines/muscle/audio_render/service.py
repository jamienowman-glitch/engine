from __future__ import annotations

import os
import uuid
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any

from engines.media_v2.service import MediaService, get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest, DerivedArtifact
from engines.audio_render.models import RenderRequest, RenderResult
from engines.audio_render.planner import build_ffmpeg_mix_plan, get_export_preset_config
from engines.audio_mix_buses.service import get_audio_mix_buses_service

class AudioRenderService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()

    def render_sequence(self, req: RenderRequest) -> RenderResult:
        # 1. Resolve Graph
        mix_graph = None
        if req.mix_preset_id:
            bus_service = get_audio_mix_buses_service()
            mix_graph = bus_service.get_mix_graph(req.mix_preset_id)
            
        # 2. Build Plan
        inputs, filter_complex, output_maps, bus_metadata = build_ffmpeg_mix_plan(
            req.sequence, 
            self.media_service, 
            mix_graph,
            export_preset=req.export_preset
        )
        
        # 3. Execution
        # Outputs configuration
        master_filename = f"render_{uuid.uuid4().hex[:8]}.{req.output_format}"
        master_path = Path(tempfile.gettempdir()) / master_filename
        
        outputs_to_register = [] # list of (path, kind, tags, meta)
        
        cmd = ["ffmpeg", "-y", "-v", "error"]
        
        for inp in inputs:
            cmd.extend(["-i", inp])
            
        cmd.extend(["-filter_complex", filter_complex])
        
        # Master Output
        preset_config = get_export_preset_config(req.export_preset)
        master_bus_meta = bus_metadata.get("master", {})
        master_meta = {
            "bpm": req.sequence.bpm,
            "tracks_count": len(req.sequence.tracks),
            "mix_preset": req.mix_preset_id,
            "bus_id": master_bus_meta.get("bus_id", "master"),
            "roles": master_bus_meta.get("roles", ["master"]),
            "export_preset": master_bus_meta.get("export_preset", req.export_preset),
            "loudnorm_target": master_bus_meta.get("loudnorm_target", preset_config["loudnorm_target"]),
            "headroom_db": master_bus_meta.get("headroom_db", preset_config["headroom_db"]),
            "limiter_thresh": master_bus_meta.get("limiter_thresh", preset_config["limiter_thresh"]),
            "dithered": master_bus_meta.get("dithered", preset_config["dither"])
        }
        if "master" in output_maps:
            cmd.extend(["-map", output_maps["master"]])
            cmd.append(str(master_path))
            outputs_to_register.append((master_path, "audio_render", ["generated", "render", "mixdown"], master_meta))
        else:
            raise RuntimeError("No master output in plan")

        # Stems
        if req.stems_export:
            for map_name, node in output_maps.items():
                if map_name == "master": continue
                
                stem_filename = f"stem_{map_name}_{uuid.uuid4().hex[:8]}.{req.output_format}"
                stem_path = Path(tempfile.gettempdir()) / stem_filename
                
                cmd.extend(["-map", node, str(stem_path)])
                bus_info = bus_metadata.get(map_name, {})
                stem_meta = {
                    "bus_id": bus_info.get("bus_id", map_name),
                    "roles": bus_info.get("roles", []),
                    "gain_db": bus_info.get("gain_db"),
                    "export_preset": bus_info.get("export_preset", req.export_preset),
                    "limiter_thresh": bus_info.get("limiter_thresh", preset_config["limiter_thresh"]),
                    "headroom_db": bus_info.get("headroom_db", preset_config["headroom_db"]),
                    "loudnorm_target": bus_info.get("loudnorm_target", preset_config["loudnorm_target"]),
                    "dithered": bus_info.get("dithered", preset_config["dither"])
                }
                outputs_to_register.append((stem_path, "audio_bus_stem", ["generated", "stem", f"bus:{map_name}"], stem_meta))
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg render failed: {e.stderr.decode()}")
            
        # 4. Upload & Register
        master_art_id = None
        master_uri = None
        stems_meta = []
        
        parent_asset_id = None # Master asset becomes parent? Or derived from sequence? 
        # Usually render is new asset.
        
        for path, kind, tags, extra_meta in outputs_to_register:
            if not path.exists():
                continue
                
            content = path.read_bytes()
            
            up_req = MediaUploadRequest(
                tenant_id=req.sequence.tenant_id,
                env=req.sequence.env,
                kind="audio",
                source_uri="pending",
                tags=tags
            )
            
            new_asset = self.media_service.register_upload(up_req, path.name, content)
            
            # If this is master, it's the main result
            if kind == "audio_render":
                parent_asset_id = new_asset.id
                art = self.media_service.register_artifact(
                    ArtifactCreateRequest(
                        tenant_id=req.sequence.tenant_id,
                        env=req.sequence.env,
                        parent_asset_id=new_asset.id,
                        kind=kind,
                        uri=new_asset.source_uri,
                        meta=master_meta
                    )
                )
                master_art_id = art.id
                master_uri = art.uri
            else:
                # Stem
                art = self.media_service.register_artifact(
                    ArtifactCreateRequest(
                        tenant_id=req.sequence.tenant_id,
                        env=req.sequence.env,
                        parent_asset_id=parent_asset_id or new_asset.id, # Link stems to master asset if possible? or keep independent?
                        # If master registered first, we can link.
                        kind=kind, # type: ignore
                        uri=new_asset.source_uri,
                        meta=extra_meta
                    )
                )
                stems_meta.append({"bus": extra_meta.get("bus_id"), "artifact_id": art.id})
                
            path.unlink()

        return RenderResult(
            artifact_id=master_art_id,
            uri=master_uri,
            duration_ms=req.sequence.duration_ms,
            meta={"stems": stems_meta}
        )

_default_service: Optional[AudioRenderService] = None

def get_audio_render_service() -> AudioRenderService:
    global _default_service
    if _default_service is None:
        _default_service = AudioRenderService()
    return _default_service
