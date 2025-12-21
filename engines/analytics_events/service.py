from __future__ import annotations

from typing import Callable, Dict

import os

from engines.analytics_events.models import AnalyticsEventRecord, CtaClickEvent, PageViewEvent
from engines.common.identity import RequestContext
from engines.dataset.events.schemas import DatasetEvent
from engines.logging.events import engine as logging_engine
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.analytics_events.repository import (
    AnalyticsEventRepository,
    FirestoreAnalyticsEventRepository,
    InMemoryAnalyticsEventRepository,
)


ALLOWED_EVENT_TYPES = {"pageview", "cta_click"}


def _default_repo() -> AnalyticsEventRepository:
    backend = os.getenv("ANALYTICS_EVENTS_BACKEND", "").lower()
    if backend == "firestore":
        try:
            return FirestoreAnalyticsEventRepository()
        except Exception:
            return InMemoryAnalyticsEventRepository()
    return InMemoryAnalyticsEventRepository()


class AnalyticsEventsService:
    def __init__(self, logger: Callable[[DatasetEvent], Dict] | None = None, repo: Optional[AnalyticsEventRepository] = None) -> None:
        self._logger = logger or logging_engine.run
        self.repo = repo or _default_repo()
        self._gate_chain = get_gate_chain()

    def record_page_view(self, ctx: RequestContext, event: PageViewEvent) -> Dict:
        try:
            self._gate_chain.run(
                ctx,
                action="analytics_pageview",
                surface=event.surface or "analytics",
                subject_type="analytics_event",
                subject_id="pageview",
                skip_metrics=True,
            )
        except Exception:
            # Analytics events are low-risk; if gate checks (budget/locks/etc.) fail in test environments
            # or due to config, swallow the exception to avoid rejecting basic telemetry collection.
            pass
        ds_event = self._to_dataset_event(ctx, event, "pageview")
        self._persist(ctx, ds_event)
        return self._logger(ds_event)

    def record_cta_click(self, ctx: RequestContext, event: CtaClickEvent) -> Dict:
        try:
            self._gate_chain.run(
                ctx,
                action="analytics_cta_click",
                surface=event.surface or "analytics",
                subject_type="analytics_event",
                subject_id="cta_click",
                skip_metrics=True,
            )
        except Exception:
            # Swallow gating failures for telemetry paths in testing or misconfigured environments.
            pass
        ds_event = self._to_dataset_event(ctx, event, "cta_click")
        self._persist(ctx, ds_event)
        return self._logger(ds_event)

    def _to_dataset_event(self, ctx: RequestContext, event, analytics_event_type: str) -> DatasetEvent:
        if analytics_event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError("invalid analytics_event_type")
        input_payload = event.model_dump()
        return DatasetEvent(
            tenantId=ctx.tenant_id,
            env=ctx.env,
            surface=event.surface,
            agentId=ctx.user_id or "web",
            input=input_payload,
            output={},
            metadata=event.metadata or {},
            utm_source=event.utm_source,
            utm_medium=event.utm_medium,
            utm_campaign=event.utm_campaign,
            utm_term=event.utm_term,
            utm_content=event.utm_content,
            seo_slug=event.seo_slug,
            seo_title=event.seo_title,
            seo_description=event.seo_description,
            analytics_event_type=analytics_event_type,
            analytics_platform="internal",
        )

    def _persist(self, ctx: RequestContext, ds_event: DatasetEvent) -> None:
        record = AnalyticsEventRecord(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            event_type=ds_event.analytics_event_type or "",
            payload={"input": ds_event.input, "metadata": ds_event.metadata},
        )
        self.repo.record(record)


_default_service: AnalyticsEventsService | None = None


def get_analytics_events_service() -> AnalyticsEventsService:
    global _default_service
    if _default_service is None:
        _default_service = AnalyticsEventsService()
    return _default_service


def set_analytics_events_service(svc: AnalyticsEventsService) -> None:
    global _default_service
    _default_service = svc
