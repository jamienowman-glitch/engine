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
    """
    Checks if any filters on the clip require region masks (teeth_whiten, skin_smooth).
    If so, looks up the RegionAnalysisSummary for the asset.
    Finds the matching mask artifact for the region type at the clip time.
    Returns a dict mapping filter index -> mask artifact URI.
    """
    
    # 1. Identify region-aware filters
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

    if not region_filters:
        return {}
    
    # 2. Look up summary
    # Scan artifacts for video_region_summary
    # Cache this lookup in service if expensive, but for now simple list
    artifacts = media_service.list_artifacts_for_asset(clip.asset_id)
    summary_art = next((a for a in artifacts if a.kind == "video_region_summary"), None)
    
    if not summary_art:
        # No regions analyzed
        return {}
    
    # 3. Load summary content
    # In V1 stub, content is in local file pointed to by URI.
    # Service needs to download/read it.
    # We assume URI is readable (local or generic open)
    try:
        # Resolve URI via service helper if GCS? passed in media service usually handles 'ensure_local' only during render.
        # Here we need to read JSON.
        # Assuming for V1 stub it's local.
        # Real implementation would use a helper to fetch JSON content.
        import json
        with open(summary_art.uri, "r") as f:
            data = json.load(f)
            summary = RegionAnalysisSummary.model_validate(data)
    except Exception:
        # Failed to read summary
        return {}
        
    mask_map = {}
    
    # 4. Find mask for each filter
    # For V1 stub, we assume 1 entry per region covers the whole file or we just use the first match.
    # Real logic: find entry overlapping clip.start_ms_on_timeline mapped to asset time.
    # Clip in/out ms refers to asset time.
    clip_in = clip.in_ms
    
    for idx, region_type in region_filters:
        # Find entry for this region
        # Trivial V1: First entry matching region
        entry = next((e for e in summary.entries if e.region == region_type), None)
        if entry:
             # Look up mask artifact from entry.mask_artifact_id
             mask_art = media_service.get_artifact(entry.mask_artifact_id)
             if mask_art:
                 mask_map[idx] = mask_art.uri
                 
    return mask_map
