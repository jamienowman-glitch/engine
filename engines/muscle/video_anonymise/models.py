from pydantic import BaseModel
from typing import Optional, List

class AnonymiseFacesRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    sequence_id: str
    filter_strength: Optional[float] = None  # 1.0 = strong, 0.6 = medium

class AnonymiseFacesResult(BaseModel):
    sequence_id: str
    clips_modified_count: int
    clip_ids: List[str]
