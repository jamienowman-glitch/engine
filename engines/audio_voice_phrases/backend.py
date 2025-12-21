from __future__ import annotations

from typing import List, Protocol, Dict, Any, Optional
from dataclasses import dataclass
import json

from engines.audio_voice_phrases.models import VoicePhraseDetectRequest
from engines.media_v2.service import MediaService

@dataclass
class PhraseCandidate:
    start_ms: float
    end_ms: float
    transcript: str
    confidence: float

class VoicePhrasesBackend(Protocol):
    def detect(self, req: VoicePhraseDetectRequest, media_service: MediaService) -> List[PhraseCandidate]:
        ...

class DefaultPhrasesBackend(VoicePhrasesBackend):
    def detect(self, req: VoicePhraseDetectRequest, media_service: MediaService) -> List[PhraseCandidate]:
        if not req.asset_id:
            return []
            
        # 1. Find Transcript Artifact
        # Logic: List artifacts for asset, look for kind='caption_track' (or 'asr_transcript')
        artifacts = media_service.list_artifacts_for_asset(req.asset_id)
        transcript_art = next((a for a in artifacts if a.kind in ("caption_track", "asr_transcript")), None)
        
        words = []
        if transcript_art:
            uri = transcript_art.uri
            try:
                # Attempt to read content.
                # If it's a GCS path, we need a client. 
                # If local, open.
                # We can try to use smart_open if installed, or standard open.
                
                content = None
                if uri.startswith("gs://"):
                    # Use GcsClient if we were injected or instantiate ad-hoc
                    # But better: try to use standard storage abstraction if available?
                    # For now, minimal robust logic:
                    from engines.storage.gcs_client import GcsClient
                    gcs = GcsClient()
                    # simplistic download
                    bucket_name, key = uri.replace("gs://", "", 1).split("/", 1)
                    blob = gcs._client.bucket(bucket_name).blob(key)
                    content = blob.download_as_text()
                else:
                    # Assume local path
                    with open(uri, 'r') as f:
                        content = f.read()

                if content:
                    data = json.loads(content)
                    if isinstance(data, list):
                        words = data
                    elif isinstance(data, dict):
                        words = data.get("segments", []) or data.get("words", [])
            except Exception as e:
                # Log warning?
                print(f"WARNING: Failed to load transcript from {uri}: {e}")
                pass
        
        # Fallback for V1/Stub behavior if no captions exist
        if not words:
            return []

        # 2. Merge
        return self._merge_words(words, req.max_gap_ms)

    def _merge_words(self, words: List[Dict[str, Any]], max_gap_ms: int) -> List[PhraseCandidate]:
        if not words:
            return []
            
        phrases = []
        current_words = [words[0]]
        
        for i in range(1, len(words)):
            prev = current_words[-1]
            curr = words[i]
            
            # Normalize keys
            p_end = prev.get("end_ms", prev.get("end", 0) * 1000)
            c_start = curr.get("start_ms", curr.get("start", 0) * 1000)
            
            gap = c_start - p_end
            
            if gap <= max_gap_ms:
                current_words.append(curr)
            else:
                phrases.append(self._build_candidate(current_words))
                current_words = [curr]
        
        if current_words:
            phrases.append(self._build_candidate(current_words))
            
        return phrases

    def _build_candidate(self, words: List[Dict[str, Any]]) -> PhraseCandidate:
        w0 = words[0]
        wn = words[-1]
        start = w0.get("start_ms", w0.get("start", 0) * 1000)
        end = wn.get("end_ms", wn.get("end", 0) * 1000)
        
        # Join text
        text_parts = [w.get("word", w.get("text", "")) for w in words]
        transcript = " ".join(text_parts).strip()
        
        # Conf
        confs = [w.get("conf", w.get("confidence", 0.0)) for w in words]
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        
        return PhraseCandidate(
            start_ms=float(start),
            end_ms=float(end),
            transcript=transcript,
            confidence=avg_conf
        )
