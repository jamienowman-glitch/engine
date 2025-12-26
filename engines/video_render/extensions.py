from __future__ import annotations

from typing import List, Optional, Tuple, Dict, Any

from engines.media_v2.models import DerivedArtifact
from engines.media_v2.service import MediaService
from engines.video_regions.models import RegionAnalysisSummary
from engines.video_timeline.models import Clip, Filter

def resolve_region_masks_for_clip(
    media_service: MediaService,
    clip: Clip,
    filters: List[Filter]
) -> Dict[int, str]:
    region_filters: List[Tuple[int, str]] = [] # (index, region_type)
    for i, f in enumerate(filters):
        if not f.enabled:
            continue
        if f.type == "teeth_whiten":
            region_filters.append((i, "teeth"))
        elif f.type == "skin_smooth":
            region_filters.append((i, "skin"))
        elif f.type == "eye_enhance":
            region_filters.append((i, "eyes"))
        elif f.type == "face_blur":
            region_filters.append((i, "face"))

    print(f"DEBUG: region_filters={region_filters}")
    if not region_filters:
        return {}
    
    artifacts = media_service.list_artifacts_for_asset(clip.asset_id)
    print(f"DEBUG: Found {len(artifacts)} artifacts for asset {clip.asset_id}")
    for a in artifacts:
        print(f"DEBUG: Art kind={a.kind} id={a.id}")

    summary_art = next((a for a in artifacts if a.kind == "video_region_summary"), None)
    
    if not summary_art:
        print("DEBUG: No video_region_summary found")
        return {}
    
    try:
        import json
        from engines.video_regions.models import RegionAnalysisSummary
        print(f"DEBUG: Reading summary from {summary_art.uri}")
        with open(summary_art.uri, "r") as f:
            data = json.load(f)
            print(f"DEBUG: Loaded JSON: {data}")
            summary = RegionAnalysisSummary.model_validate(data)
            print(f"DEBUG: Validated summary model with {len(summary.entries)} entries")
    except Exception as e:
        print(f"DEBUG: Failed to read summary: {e}")
        import traceback
        traceback.print_exc()
        return {}
        
    mask_map = {}
    clip_in = clip.in_ms
    
    for idx, region_type in region_filters:
        print(f"DEBUG: Looking for region={region_type}")
        entry = next((e for e in summary.entries if e.region == region_type), None)
        if entry:
             print(f"DEBUG: Found entry: {entry}")
             mask_art = media_service.get_artifact(entry.mask_artifact_id)
             if mask_art:
                 print(f"DEBUG: Found mask artifact: {mask_art.uri}")
                 mask_map[idx] = mask_art.uri
             else:
                 print(f"DEBUG: Mask artifact {entry.mask_artifact_id} not found")
        else:
             print(f"DEBUG: No entry found for {region_type}")
                 
    return mask_map
