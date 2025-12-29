"""
Integration tests: ModeCTX + EventEnvelope unified baseline (Gate 1).
Tests the complete flow: HTTP headers → RequestContext → EventEnvelope → Events.
"""

import pytest
from engines.common.identity import RequestContext, RequestContextBuilder
from engines.dataset.events.contract import (
    EventEnvelope,
    Mode,
    StorageClass,
    DatasetEvent,
    StreamEvent,
    build_envelope_from_context,
)


class TestModeCTXToEnvelopeIntegration:
    """Test integration between ModeCTX and EventEnvelope."""
    
    def test_headers_to_envelope_pipeline(self):
        """Full pipeline: HTTP headers → RequestContext → EventEnvelope."""
        # 1. Parse headers with ModeCTX
        headers = {
            "X-Mode": "saas",
            "X-Tenant-Id": "t_acme",
            "X-Project-Id": "proj_123",
            "X-Request-Id": "req_abc",
            "X-App-Id": "app_chat",
            "X-Surface-Id": "web",
            "X-User-Id": "user_xyz",
        }
        ctx = RequestContextBuilder.from_headers(headers)
        
        # 2. Verify RequestContext
        assert ctx.tenant_id == "t_acme"
        assert ctx.mode == "saas"
        assert ctx.project_id == "proj_123"
        assert ctx.request_id == "req_abc"
        
        # 3. Build envelope from context
        envelope = build_envelope_from_context(ctx, storage_class=StorageClass.DATASET)
        
        # 4. Verify envelope (mode properly converted)
        assert envelope.tenant_id == "t_acme"
        assert envelope.mode == Mode.SAAS
        assert envelope.project_id == "proj_123"
        assert envelope.request_id == "req_abc"
    
    def test_x_env_rejection_blocks_envelope(self):
        """X-Env rejection in ModeCTX prevents envelope creation."""
        headers = {
            "X-Env": "staging",  # FORBIDDEN
            "X-Mode": "saas",
            "X-Tenant-Id": "t_acme",
            "X-Project-Id": "proj_123",
        }
        
        # ModeCTX rejects X-Env
        with pytest.raises(ValueError, match="X-Env"):
            RequestContextBuilder.from_headers(headers)
    
    def test_mode_only_requirement_propagates_to_envelope(self):
        """Mode-only requirement enforced at both RequestContext and EventEnvelope."""
        # 1. RequestContext rejects legacy mode
        headers = {
            "X-Mode": "dev",  # LEGACY
            "X-Tenant-Id": "t_acme",
            "X-Project-Id": "proj_123",
        }
        with pytest.raises(ValueError):
            RequestContextBuilder.from_headers(headers)
        
        # 2. Direct envelope creation also rejects legacy mode
        with pytest.raises(ValueError):
            EventEnvelope(
                tenant_id="t_acme",
                mode="dev",
                project_id="proj_123",
                request_id="req_abc",
            )
    
    def test_dataset_event_with_mode_context(self):
        """DatasetEvent integrates mode from RequestContext."""
        # Build context
        ctx = RequestContext(
            tenant_id="t_acme",
            mode="enterprise",
            project_id="proj_xyz",
            request_id="req_train_001",
            app_id="app_ml",
        )
        
        # Build event with envelope from context
        envelope = build_envelope_from_context(
            ctx,
            storage_class=StorageClass.DATASET,
            run_id="run_train_v1",
        )
        event = DatasetEvent(
            envelope=envelope,
            event_type="output",
            agent_id="agent_llm",
            output_text="training output",
            train_ok=True,
        )
        
        # Verify mode is correctly propagated
        assert event.envelope.mode == Mode.ENTERPRISE
        assert event.envelope.run_id == "run_train_v1"
    
    def test_stream_event_with_mode_context(self):
        """StreamEvent integrates mode from RequestContext."""
        # Build context
        ctx = RequestContext(
            tenant_id="t_system",
            mode="lab",
            project_id="proj_bootstrap",
            request_id="req_stream_001",
        )
        
        # Build stream event with envelope
        envelope = build_envelope_from_context(
            ctx,
            storage_class=StorageClass.REALTIME,
        )
        event = StreamEvent(
            envelope=envelope,
            event_type="chunk",
            content="streaming output",
            persist=True,
        )
        
        # Verify mode is correctly propagated
        assert event.envelope.mode == Mode.LAB
        assert event.envelope.storage_class == StorageClass.REALTIME


class TestModeEnforcementConsistency:
    """Test consistent mode enforcement across ModeCTX and EventEnvelope."""
    
    def test_valid_modes_accepted_everywhere(self):
        """Valid modes (saas|enterprise|lab) work in both ModeCTX and EventEnvelope."""
        valid_modes = ["saas", "enterprise", "lab"]
        
        for mode in valid_modes:
            # Test RequestContext
            ctx = RequestContext(
                tenant_id="t_acme",
                mode=mode,
                project_id="proj_123",
            )
            assert ctx.mode == mode
            
            # Test EventEnvelope
            envelope = EventEnvelope(
                tenant_id="t_acme",
                mode=mode,
                project_id="proj_123",
                request_id="req_abc",
            )
            assert envelope.mode.value == mode
    
    def test_invalid_modes_rejected_everywhere(self):
        """Invalid modes rejected in both ModeCTX and EventEnvelope."""
        invalid_modes = ["dev", "development", "staging", "stage", "prod", "production"]
        
        for invalid_mode in invalid_modes:
            # Test RequestContext
            headers = {
                "X-Mode": invalid_mode,
                "X-Tenant-Id": "t_acme",
                "X-Project-Id": "proj_123",
            }
            with pytest.raises(ValueError):
                RequestContextBuilder.from_headers(headers)
            
            # Test EventEnvelope
            with pytest.raises(ValueError):
                EventEnvelope(
                    tenant_id="t_acme",
                    mode=invalid_mode,
                    project_id="proj_123",
                    request_id="req_abc",
                )
    
    def test_required_scope_fields_enforced(self):
        """Required scope fields enforced in both systems."""
        # RequestContext requires tenant_id, mode, project_id
        with pytest.raises(ValueError):
            RequestContext(tenant_id="", mode="saas", project_id="proj_123")
        
        # EventEnvelope requires tenant_id, mode, project_id, request_id
        with pytest.raises(ValueError):
            EventEnvelope(
                tenant_id="",
                mode="saas",
                project_id="proj_123",
                request_id="req_abc",
            )


class TestEndToEndPipeline:
    """Test complete end-to-end pipeline: headers → context → events."""
    
    def test_http_to_dataset_event_pipeline(self):
        """Complete pipeline from HTTP headers to DatasetEvent."""
        # 1. Simulate HTTP request with ModeCTX headers
        headers = {
            "X-Mode": "enterprise",
            "X-Tenant-Id": "t_acme",
            "X-Project-Id": "proj_ml",
            "X-Request-Id": "req_http_001",
            "X-App-Id": "app_training",
            "X-Surface-Id": "batch",
            "X-User-Id": "service_trainer",
        }
        
        # 2. Parse with ModeCTX
        ctx = RequestContextBuilder.from_headers(headers)
        
        # 3. Build envelope from context
        envelope = build_envelope_from_context(
            ctx,
            storage_class=StorageClass.DATASET,
            run_id="run_batch_20250101",
        )
        
        # 4. Create DatasetEvent
        event = DatasetEvent(
            envelope=envelope,
            event_type="training_output",
            agent_id="agent_trainer",
            output_text="model output",
            train_ok=True,
        )
        
        # 5. Verify full chain
        assert event.envelope.tenant_id == "t_acme"
        assert event.envelope.mode == Mode.ENTERPRISE
        assert event.envelope.project_id == "proj_ml"
        assert event.envelope.request_id == "req_http_001"
        assert event.envelope.app_id == "app_training"
        assert event.envelope.surface_id == "batch"
        assert event.envelope.actor_id == "service_trainer"
        assert event.envelope.run_id == "run_batch_20250101"
        assert event.event_type == "training_output"
    
    def test_sse_to_stream_event_pipeline(self):
        """Pipeline for SSE/WS: HTTP headers to StreamEvent (for transport)."""
        # 1. Simulate SSE request headers
        headers = {
            "X-Mode": "saas",
            "X-Tenant-Id": "t_customer",
            "X-Project-Id": "proj_app",
            "X-Request-Id": "req_sse_001",
        }
        
        # 2. Parse with ModeCTX
        ctx = RequestContextBuilder.from_headers(headers)
        
        # 3. Build envelope for realtime
        envelope = build_envelope_from_context(
            ctx,
            storage_class=StorageClass.REALTIME,
        )
        
        # 4. Create StreamEvent for transport
        event = StreamEvent(
            envelope=envelope,
            event_type="chunk",
            content="token stream data",
            persist=False,  # Don't persist live chunks
        )
        
        # 5. Convert to dict for JSON transport
        event_dict = event.to_dict()
        
        # 6. Verify transportability
        assert event_dict["mode"] == "saas"
        assert event_dict["tenant_id"] == "t_customer"
        assert event_dict["event_type"] == "chunk"
        assert event_dict["storage_class"] == "realtime"
        assert event_dict["content"] == "token stream data"


class TestSingleSourceOfTruth:
    """Test that ModeCTX and EventEnvelope share single source of truth for mode."""
    
    def test_mode_enum_matches(self):
        """Mode values in RequestContext match Mode enum in EventEnvelope."""
        from engines.common.identity import RequestContext as RC
        
        # RequestContext.VALID_MODES should match Mode enum
        ctx = RequestContext(
            tenant_id="t_test",
            mode="saas",
            project_id="p1",
        )
        
        envelope = EventEnvelope(
            tenant_id="t_test",
            mode="saas",
            project_id="p1",
            request_id="req1",
        )
        
        # Both accept "saas"
        assert ctx.mode == "saas"
        assert envelope.mode == Mode.SAAS
    
    def test_tenant_format_consistency(self):
        """Tenant format ^t_[a-z0-9_-]+ enforced in both."""
        valid_tenants = ["t_acme", "t_my_tenant", "t_123"]
        invalid_tenants = ["acme", "T_acme", "t_"]
        
        for valid_tenant in valid_tenants:
            # Both accept valid format
            ctx = RequestContext(
                tenant_id=valid_tenant,
                mode="saas",
                project_id="p1",
            )
            assert ctx.tenant_id == valid_tenant
            
            envelope = EventEnvelope(
                tenant_id=valid_tenant,
                mode="saas",
                project_id="p1",
                request_id="req1",
            )
            assert envelope.tenant_id == valid_tenant
        
        for invalid_tenant in invalid_tenants:
            # Both reject invalid format
            with pytest.raises(ValueError):
                RequestContext(
                    tenant_id=invalid_tenant,
                    mode="saas",
                    project_id="p1",
                )
            
            with pytest.raises(ValueError):
                EventEnvelope(
                    tenant_id=invalid_tenant,
                    mode="saas",
                    project_id="p1",
                    request_id="req1",
                )
