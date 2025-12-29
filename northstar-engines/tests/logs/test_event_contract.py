"""
Tests for EventEnvelope + DatasetEvent + StreamEvent (Gate 1).
Validates mode enforcement, required envelope fields, and integration with RequestContext.
"""

import pytest
from engines.dataset.events.contract import (
    EventEnvelope,
    Mode,
    StorageClass,
    EventSeverity,
    DatasetEvent,
    StreamEvent,
    build_envelope_from_context,
)
from engines.common.identity import RequestContext


class TestEventEnvelopeValidation:
    """Test EventEnvelope creation and validation."""
    
    def test_valid_envelope_creation(self):
        """Valid envelope with all required fields."""
        envelope = EventEnvelope(
            tenant_id="t_acme",
            mode=Mode.SAAS,
            project_id="proj_123",
            request_id="req_abc",
        )
        assert envelope.tenant_id == "t_acme"
        assert envelope.mode == Mode.SAAS
        assert envelope.project_id == "proj_123"
        assert envelope.request_id == "req_abc"
        assert envelope.trace_id  # auto-generated
        assert envelope.event_id  # auto-generated
    
    def test_valid_envelope_mode_string(self):
        """Mode can be initialized as string, converts to enum."""
        envelope = EventEnvelope(
            tenant_id="t_acme",
            mode="enterprise",  # string
            project_id="proj_123",
            request_id="req_abc",
        )
        assert envelope.mode == Mode.ENTERPRISE
    
    def test_missing_tenant_id(self):
        """Missing tenant_id raises ValueError."""
        with pytest.raises(ValueError, match="tenant_id is required"):
            EventEnvelope(
                tenant_id="",
                mode=Mode.SAAS,
                project_id="proj_123",
                request_id="req_abc",
            )
    
    def test_invalid_tenant_id_format(self):
        """Tenant_id must start with t_."""
        with pytest.raises(ValueError, match="tenant_id must start with t_"):
            EventEnvelope(
                tenant_id="acme",  # missing t_
                mode=Mode.SAAS,
                project_id="proj_123",
                request_id="req_abc",
            )
    
    def test_missing_mode(self):
        """Missing mode raises ValueError."""
        with pytest.raises(ValueError, match="mode is required"):
            EventEnvelope(
                tenant_id="t_acme",
                mode=None,
                project_id="proj_123",
                request_id="req_abc",
            )
    
    def test_invalid_mode_value(self):
        """Invalid mode value raises ValueError."""
        with pytest.raises(ValueError, match="mode must be one of"):
            EventEnvelope(
                tenant_id="t_acme",
                mode="dev",  # LEGACY, not allowed
                project_id="proj_123",
                request_id="req_abc",
            )
    
    def test_valid_modes(self):
        """All valid modes: saas, enterprise, lab."""
        for valid_mode in [Mode.SAAS, Mode.ENTERPRISE, Mode.LAB]:
            envelope = EventEnvelope(
                tenant_id="t_acme",
                mode=valid_mode,
                project_id="proj_123",
                request_id="req_abc",
            )
            assert envelope.mode == valid_mode
    
    def test_missing_project_id(self):
        """Missing project_id raises ValueError."""
        with pytest.raises(ValueError, match="project_id is required"):
            EventEnvelope(
                tenant_id="t_acme",
                mode=Mode.SAAS,
                project_id="",
                request_id="req_abc",
            )
    
    def test_missing_request_id(self):
        """Missing request_id raises ValueError."""
        with pytest.raises(ValueError, match="request_id is required"):
            EventEnvelope(
                tenant_id="t_acme",
                mode=Mode.SAAS,
                project_id="proj_123",
                request_id="",
            )
    
    def test_storage_class_enum(self):
        """Storage class can be string or enum."""
        envelope1 = EventEnvelope(
            tenant_id="t_acme",
            mode=Mode.SAAS,
            project_id="proj_123",
            request_id="req_abc",
            storage_class=StorageClass.DATASET,
        )
        assert envelope1.storage_class == StorageClass.DATASET
        
        envelope2 = EventEnvelope(
            tenant_id="t_acme",
            mode=Mode.SAAS,
            project_id="proj_123",
            request_id="req_abc",
            storage_class="cost",
        )
        assert envelope2.storage_class == StorageClass.COST
    
    def test_envelope_to_dict(self):
        """Envelope converts to dict correctly."""
        envelope = EventEnvelope(
            tenant_id="t_acme",
            mode=Mode.SAAS,
            project_id="proj_123",
            request_id="req_abc",
            app_id="app_xyz",
            surface_id="surf_123",
        )
        d = envelope.to_dict()
        assert d["tenant_id"] == "t_acme"
        assert d["mode"] == "saas"
        assert d["project_id"] == "proj_123"
        assert d["request_id"] == "req_abc"
        assert d["app_id"] == "app_xyz"
        assert d["surface_id"] == "surf_123"


class TestDatasetEvent:
    """Test DatasetEvent with envelope."""
    
    def test_valid_dataset_event(self):
        """Valid DatasetEvent with envelope."""
        envelope = EventEnvelope(
            tenant_id="t_acme",
            mode=Mode.LAB,
            project_id="proj_123",
            request_id="req_abc",
        )
        event = DatasetEvent(
            envelope=envelope,
            event_type="input",
            agent_id="agent_chat",
            input_text="hello",
            output_text="hi there",
        )
        assert event.envelope.tenant_id == "t_acme"
        assert event.event_type == "input"
        assert event.input_text == "hello"
    
    def test_dataset_event_to_dict(self):
        """DatasetEvent converts to dict."""
        envelope = EventEnvelope(
            tenant_id="t_acme",
            mode=Mode.SAAS,
            project_id="proj_123",
            request_id="req_abc",
        )
        event = DatasetEvent(
            envelope=envelope,
            event_type="output",
            agent_id="agent_xyz",
            train_ok=True,
        )
        d = event.to_dict()
        assert d["tenant_id"] == "t_acme"
        assert d["mode"] == "saas"
        assert d["event_type"] == "output"
        assert d["agent_id"] == "agent_xyz"
        assert d["train_ok"] is True


class TestStreamEvent:
    """Test StreamEvent with envelope."""
    
    def test_valid_stream_event(self):
        """Valid StreamEvent with envelope."""
        envelope = EventEnvelope(
            tenant_id="t_acme",
            mode=Mode.ENTERPRISE,
            project_id="proj_123",
            request_id="req_abc",
            storage_class=StorageClass.REALTIME,
        )
        event = StreamEvent(
            envelope=envelope,
            event_type="chunk",
            content="token stream...",
            persist=True,
        )
        assert event.envelope.tenant_id == "t_acme"
        assert event.envelope.mode == Mode.ENTERPRISE
        assert event.event_type == "chunk"
        assert event.content == "token stream..."
    
    def test_stream_event_to_dict(self):
        """StreamEvent converts to dict (for transport)."""
        envelope = EventEnvelope(
            tenant_id="t_acme",
            mode=Mode.SAAS,
            project_id="proj_123",
            request_id="req_abc",
            storage_class=StorageClass.REALTIME,
        )
        event = StreamEvent(
            envelope=envelope,
            event_type="start",
            content="",
            persist=False,
        )
        d = event.to_dict()
        assert d["tenant_id"] == "t_acme"
        assert d["mode"] == "saas"
        assert d["storage_class"] == "realtime"
        assert d["event_type"] == "start"


class TestBuildEnvelopeFromContext:
    """Test building EventEnvelope from RequestContext."""
    
    def test_build_from_valid_context(self):
        """Build envelope from RequestContext."""
        ctx = RequestContext(
            tenant_id="t_acme",
            mode="saas",
            project_id="proj_123",
            request_id="req_abc",
            app_id="app_xyz",
            surface_id="surf_123",
            user_id="user_456",
        )
        envelope = build_envelope_from_context(ctx)
        assert envelope.tenant_id == "t_acme"
        assert envelope.mode == Mode.SAAS
        assert envelope.project_id == "proj_123"
        assert envelope.request_id == "req_abc"
        assert envelope.app_id == "app_xyz"
        assert envelope.surface_id == "surf_123"
        assert envelope.actor_id == "user_456"
    
    def test_build_with_custom_fields(self):
        """Build envelope with custom scope fields."""
        ctx = RequestContext(
            tenant_id="t_system",
            mode="lab",
            project_id="proj_bootstrap",
            request_id="req_001",
        )
        envelope = build_envelope_from_context(
            ctx,
            storage_class=StorageClass.DATASET,
            run_id="run_12345",
            step_id="step_01",
        )
        assert envelope.tenant_id == "t_system"
        assert envelope.mode == Mode.LAB
        assert envelope.run_id == "run_12345"
        assert envelope.step_id == "step_01"
        assert envelope.storage_class == StorageClass.DATASET
    
    def test_build_creates_valid_dataset_event(self):
        """Build envelope and create DatasetEvent."""
        ctx = RequestContext(
            tenant_id="t_acme",
            mode="enterprise",
            project_id="proj_xyz",
            request_id="req_123",
        )
        envelope = build_envelope_from_context(ctx, storage_class=StorageClass.DATASET)
        event = DatasetEvent(
            envelope=envelope,
            event_type="output",
            agent_id="agent_chat",
            output_text="response text",
            train_ok=True,
        )
        assert event.envelope.mode == Mode.ENTERPRISE
        assert event.output_text == "response text"


class TestModeEnforcementInEnvelope:
    """Test that mode-only enforcement is applied in envelopes."""
    
    def test_reject_legacy_env_values(self):
        """Legacy env values in mode field are rejected."""
        legacy_values = ["dev", "development", "staging", "stage", "prod", "production"]
        for legacy_value in legacy_values:
            with pytest.raises(ValueError, match="mode must be one of"):
                EventEnvelope(
                    tenant_id="t_acme",
                    mode=legacy_value,
                    project_id="proj_123",
                    request_id="req_abc",
                )
    
    def test_only_saas_enterprise_lab_allowed(self):
        """Only saas, enterprise, lab modes allowed."""
        valid_modes = ["saas", "enterprise", "lab"]
        for mode_str in valid_modes:
            envelope = EventEnvelope(
                tenant_id="t_acme",
                mode=mode_str,
                project_id="proj_123",
                request_id="req_abc",
            )
            assert envelope.mode.value == mode_str


class TestEnvelopeIntegration:
    """Test envelope + context integration."""
    
    def test_context_to_event_pipeline(self):
        """Full pipeline: RequestContext → Envelope → Event."""
        # 1. Create RequestContext
        ctx = RequestContext(
            tenant_id="t_acme",
            mode="saas",
            project_id="proj_123",
            request_id="req_abc",
            app_id="app_chat",
            surface_id="web",
            user_id="user_xyz",
        )
        
        # 2. Build envelope from context
        envelope = build_envelope_from_context(
            ctx,
            storage_class=StorageClass.DATASET,
            run_id="run_001",
        )
        
        # 3. Create event with envelope
        event = DatasetEvent(
            envelope=envelope,
            event_type="output",
            agent_id="agent_llm",
            output_text="generated response",
            train_ok=True,
        )
        
        # 4. Verify full chain
        assert event.envelope.tenant_id == ctx.tenant_id
        assert event.envelope.mode == Mode.SAAS
        assert event.envelope.project_id == ctx.project_id
        assert event.envelope.request_id == ctx.request_id
        assert event.envelope.run_id == "run_001"
        assert event.output_text == "generated response"
    
    def test_stream_event_for_transport(self):
        """StreamEvent ready for transport (SSE/WS)."""
        ctx = RequestContext(
            tenant_id="t_acme",
            mode="enterprise",
            project_id="proj_xyz",
            request_id="req_stream_001",
        )
        envelope = build_envelope_from_context(
            ctx,
            storage_class=StorageClass.REALTIME,
        )
        event = StreamEvent(
            envelope=envelope,
            event_type="chunk",
            content="token1 token2 token3",
            persist=True,
        )
        
        # Convert to dict for JSON transport
        d = event.to_dict()
        assert d["mode"] == "enterprise"
        assert d["storage_class"] == "realtime"
        assert d["content"] == "token1 token2 token3"
