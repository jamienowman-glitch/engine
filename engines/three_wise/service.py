from __future__ import annotations

import json
import os
from collections import Counter
from typing import Callable, List, Optional

from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.common.keys import SLOT_LLM_PRIMARY
from engines.common.selecta import SelectaResolver, get_selecta_resolver
from engines.three_wise.models import Opinion, ThreeWiseRecord, ThreeWiseVerdict
from engines.three_wise.repository import FirestoreThreeWiseRepository, InMemoryThreeWiseRepository, ThreeWiseRepository


def _default_repo() -> ThreeWiseRepository:
    backend = os.getenv("THREE_WISE_BACKEND", "").lower()
    if backend == "firestore":
        try:
            return FirestoreThreeWiseRepository()
        except Exception:
            return InMemoryThreeWiseRepository()
    return InMemoryThreeWiseRepository()


three_wise_repo: ThreeWiseRepository = _default_repo()


class ThreeWiseLLMClient:
    """Best-effort opinion generator using the llm_primary slot (Vertex/OpenAI/dev fallback)."""

    def __init__(
        self,
        selecta: Optional[SelectaResolver] = None,
        completion_fn: Optional[Callable[[str, dict], str]] = None,
    ) -> None:
        self._selecta = selecta or get_selecta_resolver()
        self._completion_fn = completion_fn

    def generate_opinion(self, ctx: RequestContext, question: str, context_text: Optional[str]) -> Opinion:
        selecta_res = self._selecta.resolve(ctx, SLOT_LLM_PRIMARY)
        model_id = (
            selecta_res.metadata.get("model")
            or selecta_res.metadata.get("model_id")
            or selecta_res.metadata.get("model_name")
            or (selecta_res.material.provider if selecta_res.material else None)
            or "unknown"
        )
        prompt = self._build_prompt(question, context_text)
        raw = self._invoke(prompt, selecta_res.metadata)
        verdict, reason = self._parse_verdict(raw)
        content = reason or raw.strip()
        return Opinion(model_id=model_id, content=content, verdict=verdict)

    def _invoke(self, prompt: str, metadata: dict) -> str:
        if self._completion_fn:
            return self._completion_fn(prompt, metadata)
        provider = (metadata.get("provider") or metadata.get("llm_provider") or "").lower()
        model_name = metadata.get("model") or metadata.get("model_id") or os.getenv("VERTEX_MODEL", "gemini-1.5-flash-002")
        # Prefer Vertex if available; otherwise fall back to a deterministic local stub.
        try:
            from google.cloud import aiplatform  # type: ignore

            aiplatform.init(project=metadata.get("project"), location=metadata.get("region") or os.getenv("GCP_REGION") or "us-central1")
            model = aiplatform.GenerativeModel(model_name)  # type: ignore[attr-defined]
            response = model.generate_content(prompt)  # type: ignore[call-arg]
            text = getattr(response, "text", None)
            if text:
                return text
            if getattr(response, "candidates", None):
                for cand in response.candidates:  # type: ignore[attr-defined]
                    parts = getattr(cand, "content", None)
                    if parts and getattr(parts, "parts", None):
                        joined = "".join(getattr(p, "text", "") for p in parts.parts)  # type: ignore[attr-defined]
                        if joined:
                            return joined
        except Exception:
            # Fall through to deterministic fallback below.
            pass
        # Local deterministic opinion when no provider is available (keeps tests stable).
        summary = metadata.get("summary") or metadata.get("model_summary") or "llm_primary"
        return json.dumps(
            {"verdict": "UNSURE", "reason": f"fallback opinion using {summary or provider or 'unknown_provider'}"}
        )

    @staticmethod
    def _build_prompt(question: str, context_text: Optional[str]) -> str:
        context_block = f"\nContext:\n{context_text}" if context_text else ""
        return (
            "You are providing an independent risk/quality opinion on a proposed change.\n"
            "Stay neutral; do not role-play a persona. Review the card and return a single JSON object.\n"
            "Allowed verdicts: APPROVE, REJECT, UNSURE. Use UNSURE if information is insufficient.\n"
            'Respond only with JSON like {"verdict":"APPROVE|REJECT|UNSURE","reason":"short justification"}.\n'
            f"Card:\nProposed change: {question}{context_block}\n"
            "Return your judgment now."
        )

    @staticmethod
    def _parse_verdict(raw: str) -> tuple[ThreeWiseVerdict, Optional[str]]:
        try:
            data = json.loads(raw)
            verdict_raw = str(data.get("verdict", "")).strip().lower()
            reason = data.get("reason")
            if verdict_raw in ThreeWiseVerdict.__members__:
                return ThreeWiseVerdict[verdict_raw], reason
        except Exception:
            pass
        # Lightweight heuristic if LLM returned prose instead of JSON.
        text = raw.lower()
        if "reject" in text:
            return ThreeWiseVerdict.reject, None
        if "approve" in text or "safe" in text:
            return ThreeWiseVerdict.approve, None
        return ThreeWiseVerdict.unsure, None


class ThreeWiseService:
    def __init__(self, repo: Optional[ThreeWiseRepository] = None, llm_client: Optional[ThreeWiseLLMClient] = None) -> None:
        self.repo = repo or three_wise_repo
        self._selecta = get_selecta_resolver()
        self._llm_client = llm_client or ThreeWiseLLMClient(selecta=self._selecta)

    def submit_question(self, ctx: RequestContext, question: str, context_text: Optional[str] = None) -> ThreeWiseRecord:
        mode = (os.getenv("THREE_WISE_MODE") or "stub").lower()
        opinion_count = int(os.getenv("THREE_WISE_COUNT", "3"))
        if mode not in {"real", "stub"}:
            mode = "stub"
        if mode == "stub":
            record = self._build_stub_record(ctx, question, context_text)
        else:
            record = self._run_real(ctx, question, context_text, opinion_count)
        record.metadata["mode"] = mode
        record.metadata["opinion_count"] = len(record.opinions)
        return self.repo.create(record)

    def list_records(self, ctx: RequestContext) -> List[ThreeWiseRecord]:
        return self.repo.list(ctx.tenant_id, ctx.env)

    def get_record(self, ctx: RequestContext, record_id: str) -> ThreeWiseRecord:
        rec = self.repo.get(ctx.tenant_id, ctx.env, record_id)
        if not rec:
            raise HTTPException(status_code=404, detail="three_wise_not_found")
        return rec

    # --- Internal helpers ---
    def _build_stub_record(self, ctx: RequestContext, question: str, context_text: Optional[str]) -> ThreeWiseRecord:
        opinions = [
            Opinion(model_id="stub-llm", content="baseline risk is low", verdict=ThreeWiseVerdict.approve),
            Opinion(model_id="stub-llm", content="flagging missing evidence", verdict=ThreeWiseVerdict.reject),
            Opinion(model_id="stub-llm", content="needs more context", verdict=ThreeWiseVerdict.unsure),
        ]
        verdict = self._aggregate_verdict(opinions)
        return ThreeWiseRecord(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            surface="three_wise",
            question=question,
            context=context_text,
            opinions=opinions,
            verdict=verdict,
            created_by=ctx.user_id,
        )

    def _run_real(self, ctx: RequestContext, question: str, context_text: Optional[str], opinion_count: int) -> ThreeWiseRecord:
        opinions: List[Opinion] = []
        for _ in range(max(1, opinion_count)):
            try:
                opinions.append(self._llm_client.generate_opinion(ctx, question, context_text))
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"three_wise_llm_error: {exc}")
        verdict = self._aggregate_verdict(opinions)
        return ThreeWiseRecord(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            surface="three_wise",
            question=question,
            context=context_text,
            opinions=opinions,
            verdict=verdict,
            created_by=ctx.user_id,
        )

    @staticmethod
    def _aggregate_verdict(opinions: List[Opinion]) -> ThreeWiseVerdict:
        if not opinions:
            return ThreeWiseVerdict.unsure
        counts = Counter([op.verdict for op in opinions if op.verdict])
        approve = counts.get(ThreeWiseVerdict.approve, 0)
        reject = counts.get(ThreeWiseVerdict.reject, 0)
        unsure = counts.get(ThreeWiseVerdict.unsure, 0)
        if approve > reject and approve >= unsure:
            return ThreeWiseVerdict.approve
        if reject > approve and reject >= unsure:
            return ThreeWiseVerdict.reject
        return ThreeWiseVerdict.unsure


_default_service: Optional[ThreeWiseService] = None


def get_three_wise_service() -> ThreeWiseService:
    global _default_service
    if _default_service is None:
        _default_service = ThreeWiseService()
    return _default_service


def set_three_wise_service(service: ThreeWiseService) -> None:
    global _default_service, three_wise_repo
    _default_service = service
    three_wise_repo = service.repo
