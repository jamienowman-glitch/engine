from __future__ import annotations

import json
import logging
import hashlib
from typing import Optional, List, Dict, Any

from engines.audio_hits.service import AudioHitsService, get_audio_hits_service
from engines.audio_hits.models import HitDetectRequest, HitDetectResult
from engines.audio_loops.service import AudioLoopsService, get_audio_loops_service
from engines.audio_loops.models import LoopDetectRequest, LoopDetectResult
from engines.audio_voice_phrases.service import AudioVoicePhrasesService, get_audio_voice_phrases_service
from engines.audio_voice_phrases.models import VoicePhraseDetectRequest, VoicePhraseDetectResult

from engines.audio_field_to_samples.models import FieldToSamplesRequest, FieldToSamplesResult

logger = logging.getLogger(__name__)


class AudioFieldToSamplesService:
    def __init__(
        self,
        hits_service: Optional[AudioHitsService] = None,
        loops_service: Optional[AudioLoopsService] = None,
        phrases_service: Optional[AudioVoicePhrasesService] = None
    ):
        self.hits_service = hits_service or get_audio_hits_service()
        self.loops_service = loops_service or get_audio_loops_service()
        self.phrases_service = phrases_service or get_audio_voice_phrases_service()

    def process_asset(self, req: FieldToSamplesRequest) -> FieldToSamplesResult:
        import concurrent.futures

        errors: Dict[str, str] = {}
        min_quality_score = max(0.0, min(1.0, req.min_quality_score))

        def run_hits() -> HitDetectResult:
            if not req.run_hits:
                return HitDetectResult()
            try:
                hit_req = HitDetectRequest(
                    tenant_id=req.tenant_id, env=req.env, user_id=req.user_id,
                    asset_id=req.asset_id,
                    **req.hit_params
                )
                return self.hits_service.detect_hits(hit_req)
            except Exception as exc:
                errors["hits"] = str(exc)
                return HitDetectResult()

        def run_loops() -> LoopDetectResult:
            if not req.run_loops:
                return LoopDetectResult()
            try:
                loop_req = LoopDetectRequest(
                    tenant_id=req.tenant_id, env=req.env, user_id=req.user_id,
                    asset_id=req.asset_id,
                    **req.loop_params
                )
                return self.loops_service.detect_loops(loop_req)
            except Exception as exc:
                errors["loops"] = str(exc)
                return LoopDetectResult()

        def run_phrases() -> VoicePhraseDetectResult:
            if not req.run_phrases:
                return VoicePhraseDetectResult()
            try:
                phrase_req = VoicePhraseDetectRequest(
                    tenant_id=req.tenant_id, env=req.env, user_id=req.user_id,
                    asset_id=req.asset_id,
                    **req.phrase_params
                )
                return self.phrases_service.detect_phrases(phrase_req)
            except Exception as exc:
                errors["phrases"] = str(exc)
                return VoicePhraseDetectResult()

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            f_hits = executor.submit(run_hits)
            f_loops = executor.submit(run_loops)
            f_phrases = executor.submit(run_phrases)

            hit_result = f_hits.result()
            loop_result = f_loops.result()
            phrase_result = f_phrases.result()

        hit_ids, hit_details = self._score_and_filter(
            hit_result.artifact_ids,
            hit_result.events,
            hit_result.meta.get("scores", {}),
            min_quality_score,
            kind="hits"
        )
        loop_ids, loop_details = self._score_and_filter(
            loop_result.artifact_ids,
            loop_result.loops,
            loop_result.meta.get("scores", {}),
            min_quality_score,
            kind="loops"
        )
        phrase_ids, phrase_details = self._score_and_filter(
            phrase_result.artifact_ids,
            phrase_result.phrases,
            phrase_result.meta.get("scores", {}),
            min_quality_score,
            kind="phrases"
        )

        dedup_hits = self._dedup_ordered(hit_ids)
        dedup_loops = self._dedup_ordered(loop_ids)
        dedup_phrases = self._dedup_ordered(phrase_ids)

        backend_versions = {
            "hits": hit_result.meta.get("backend_info", {}).get("backend_version"),
            "loops": loop_result.meta.get("backend_info", {}).get("backend_version"),
            "phrases": phrase_result.meta.get("backend_info", {}).get("backend_version"),
        }
        cache_key = self._build_cache_key(req, min_quality_score, backend_versions)
        summary_meta: Dict[str, Any] = {
            "hits_count": len(dedup_hits),
            "loops_count": len(dedup_loops),
            "phrases_count": len(dedup_phrases),
            "cache_key": cache_key,
            "backend_versions": backend_versions,
            "min_quality_score": min_quality_score,
            "score_details": {
                "hits": {k: hit_details[k] for k in dedup_hits if k in hit_details},
                "loops": {k: loop_details[k] for k in dedup_loops if k in loop_details},
                "phrases": {k: phrase_details[k] for k in dedup_phrases if k in phrase_details},
            },
            "filtered_counts": {
                "hits": max(0, len(hit_result.artifact_ids) - len(dedup_hits)),
                "loops": max(0, len(loop_result.artifact_ids) - len(dedup_loops)),
                "phrases": max(0, len(phrase_result.artifact_ids) - len(dedup_phrases)),
            }
        }
        if errors:
            summary_meta["errors"] = errors
            logger.warning("Field_to_samples encountered partial errors: %s", errors)

        return FieldToSamplesResult(
            asset_id=req.asset_id,
            hit_artifact_ids=dedup_hits,
            loop_artifact_ids=dedup_loops,
            phrase_artifact_ids=dedup_phrases,
            summary_meta=summary_meta
        )

    def _score_and_filter(
        self,
        artifact_ids: List[str],
        events: List[Any],
        score_map: Dict[str, Any],
        min_score: float,
        kind: str
    ) -> tuple[list[str], Dict[str, Dict[str, float]]]:
        filtered = []
        details: Dict[str, Dict[str, float]] = {}
        score_map = score_map or {}
        for idx, art_id in enumerate(artifact_ids):
            event = events[idx] if idx < len(events) else None
            score = score_map.get(art_id)
            if score is None:
                score = self._score_from_event(event, kind)
            score = max(0.0, min(1.0, float(score)))
            if score >= min_score:
                filtered.append(art_id)
                details[art_id] = {
                    "score": score,
                    "offset_ms": self._offset_from_event(event)
                }
        return filtered, details

    def _score_from_event(self, event: Any, kind: str) -> float:
        if not event:
            return 0.5
        if kind == "hits":
            peak = getattr(event, "peak_db", None)
            if peak is None:
                return 0.5
            peak_clamped = max(-60.0, min(0.0, float(peak)))
            return (peak_clamped + 60.0) / 60.0
        confidence = getattr(event, "confidence", None)
        if confidence is None:
            return 0.5
        return max(0.0, min(1.0, float(confidence)))

    def _offset_from_event(self, event: Any) -> float:
        if not event:
            return 0.0
        return float(getattr(event, "source_start_ms", 0.0) or 0.0)

    def _dedup_ordered(self, artifact_ids: List[str]) -> List[str]:
        seen = set()
        ordered = []
        for art_id in artifact_ids:
            if art_id not in seen:
                seen.add(art_id)
                ordered.append(art_id)
        return ordered

    def _build_cache_key(
        self,
        req: FieldToSamplesRequest,
        min_quality_score: float,
        backend_versions: Dict[str, Optional[str]]
    ) -> str:
        components = [
            req.asset_id,
            req.run_hits,
            req.run_loops,
            req.run_phrases,
            min_quality_score,
            json.dumps(req.hit_params, sort_keys=True),
            json.dumps(req.loop_params, sort_keys=True),
            json.dumps(req.phrase_params, sort_keys=True),
            backend_versions.get("hits"),
            backend_versions.get("loops"),
            backend_versions.get("phrases"),
        ]
        raw = "|".join(str(c) for c in components)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

_default_service: Optional[AudioFieldToSamplesService] = None

def get_audio_field_to_samples_service() -> AudioFieldToSamplesService:
    global _default_service
    if _default_service is None:
        _default_service = AudioFieldToSamplesService()
    return _default_service
