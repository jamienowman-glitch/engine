"""Gate1 PII boundary tests ensuring sanitized payloads reach outbound calls."""

import logging

from engines.chat.service.llm_client import LLMClient
from engines.common.identity import RequestContext
from engines.logging.event_sink import InMemoryEventSink
from engines.nexus.vector_explorer.ingest_service import VectorIngestService
from engines.nexus.vector_explorer.service import VectorExplorerService


def _make_context() -> RequestContext:
    return RequestContext(
        tenant_id="t_acme",
        mode="saas",
        project_id="proj_gate",
        request_id="req_pii",
        surface_id="web",
        app_id="app_gate",
        user_id="user_gate",
    )


def test_llm_client_redacts_events_and_logs(caplog):
    caplog.set_level(logging.INFO)
    sink = InMemoryEventSink()
    client = LLMClient(event_sink=sink)
    ctx = _make_context()
    prompt = "Email foo@example.com and call 555-123-4567 for verification"

    response = client.call(prompt, ctx)

    assert "[REDACTED_EMAIL]" in response
    assert "[REDACTED_PHONE]" in response
    assert "foo@example.com" not in response
    assert "555-123-4567" not in response
    assert "foo@example.com" not in caplog.text
    assert "555-123-4567" not in caplog.text

    assert sink.events, "Expected an event to be emitted"
    event = sink.events[-1]
    assert event.agent_id == "llm_client"
    assert event.train_ok is False
    assert event.pii_flags["email"]
    assert event.pii_flags["phone"]
    assert "[REDACTED_EMAIL]" in event.input_text
    assert "[REDACTED_PHONE]" in event.input_text


def test_vector_query_redacts_before_matches(caplog):
    caplog.set_level(logging.INFO)
    sink = InMemoryEventSink()
    service = VectorExplorerService(event_sink=sink)
    ctx = _make_context()
    query = "Find SSN 123-45-6789 in docs"

    result = service.query(ctx, query)

    sanitized_query = result["query"]
    assert "[REDACTED_SSN]" in sanitized_query
    assert "123-45-6789" not in sanitized_query
    assert "123-45-6789" not in caplog.text

    assert sink.events
    event = sink.events[-1]
    assert event.agent_id == "vector_explorer_query"
    assert event.pii_flags["ssn"]
    assert event.train_ok is False
    assert "[REDACTED_SSN]" in event.input_text


def test_vector_ingest_redacts_documents_and_aggregates_flags(caplog):
    caplog.set_level(logging.INFO)
    sink = InMemoryEventSink()
    service = VectorIngestService(event_sink=sink)
    ctx = _make_context()
    documents = [
        "Public note with no PII",
        "Credit card 4111 1111 1111 1111 expires soon",
    ]

    result = service.ingest(ctx, documents)

    sanitized_docs = result["documents"]
    assert "[REDACTED_CC]" in sanitized_docs[1]
    assert "4111 1111 1111 1111" not in sanitized_docs[1]
    assert "4111 1111 1111 1111" not in caplog.text

    assert sink.events
    event = sink.events[-1]
    assert event.agent_id == "vector_explorer_ingest"
    assert event.pii_flags["credit_card"]
    assert event.train_ok is False
    assert event.additional_data["document_count"] == len(documents)
    assert "\n" in event.input_text
