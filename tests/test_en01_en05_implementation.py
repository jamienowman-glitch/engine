"""Tests for EN-01 through EN-05 implementation.

Covers:
- EN-01: Error envelope standardization
- EN-02: GateChain emission & audit wiring
- EN-03: Canvas command durability + alias
- EN-04: Canvas snapshot/replay endpoints
- EN-05: Routing enforcement
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException

from engines.common.error_envelope import (
    error_response,
    missing_route_error,
    cursor_invalid_error,
)
from engines.identity.jwt_service import AuthContext
from engines.event_spine.routes import append_event, AppendEventRequest
from engines.event_spine.service_reject import MissingEventSpineRoute
from engines.strategy_lock.service import StrategyLockService
from engines.strategy_lock.repository import InMemoryStrategyLockRepository
from engines.budget.routes import read_policy
from engines.canvas_commands.models import (
    CommandEnvelope,
    RevisionResult,
    CanvasSnapshot,
    CanvasReplayEvent,
)
from engines.canvas_commands.service import (
    apply_command,
    get_canvas_snapshot,
    get_canvas_replay,
)
from engines.common.identity import RequestContext


# ============================================================================
# EN-01: Error Envelope Tests
# ============================================================================

class TestErrorEnvelope:
    """Test canonical error envelope structure."""
    
    def test_error_response_creates_proper_envelope(self):
        """error_response should raise HTTPException with ErrorEnvelope body."""
        with pytest.raises(HTTPException) as exc_info:
            error_response(
                code="test_error",
                message="Test message",
                status_code=400,
                gate="firearms",
                action_name="dangerous_action",
            )
        
        exc = exc_info.value
        assert exc.status_code == 400
        detail = exc.detail
        assert isinstance(detail, dict)
        assert "error" in detail
        assert detail["error"]["code"] == "test_error"
        assert detail["error"]["message"] == "Test message"
        assert detail["error"]["http_status"] == 400
        assert detail["error"]["gate"] == "firearms"
        assert detail["error"]["action_name"] == "dangerous_action"
    
    def test_error_envelope_with_details(self):
        """error_response should include details dict."""
        with pytest.raises(HTTPException) as exc_info:
            error_response(
                code="budget_exceeded",
                message="Budget exceeded",
                status_code=403,
                gate="budget",
                details={"current": 100, "limit": 50},
            )
        
        exc = exc_info.value
        assert exc.detail["error"]["http_status"] == 403
        assert exc.detail["error"]["details"]["current"] == 100
        assert exc.detail["error"]["details"]["limit"] == 50
    
    def test_missing_route_error(self):
        """missing_route_error should create 503 error with proper code."""
        with pytest.raises(HTTPException) as exc_info:
            missing_route_error(
                resource_kind="event_spine",
                tenant_id="t_tenant123",
                env="saas",
            )
        
        exc = exc_info.value
        assert exc.status_code == 503
        assert exc.detail["error"]["code"] == "event_spine.missing_route"
        assert exc.detail["error"]["http_status"] == 503
        assert exc.detail["error"]["resource_kind"] == "event_spine"
    
    def test_cursor_invalid_error(self):
        """cursor_invalid_error should create 410 error."""
        with pytest.raises(HTTPException) as exc_info:
            cursor_invalid_error("evt_old_12345")
        
        exc = exc_info.value
        assert exc.status_code == 410
        assert exc.detail["error"]["code"] == "event_spine.cursor_invalid"
        assert exc.detail["error"]["http_status"] == 410


# ============================================================================
# EN-02: GateChain Emission Tests
# ============================================================================

class TestGateChainEmission:
    """Test GateChain SAFETY_DECISION and audit emission."""
    
    @patch("engines.nexus.hardening.gate_chain.get_timeline_store")
    @patch("engines.nexus.hardening.gate_chain.emit_audit_event")
    def test_gate_chain_emits_pass_decision(self, mock_audit, mock_timeline):
        """GateChain should emit SAFETY_DECISION PASS on success."""
        from engines.nexus.hardening.gate_chain import GateChain
        
        # Mock all services
        mock_kill_switch = Mock()
        mock_kill_switch.ensure_action_allowed = Mock()
        
        mock_gate_chain = GateChain(kill_switch_service=mock_kill_switch)
        
        # Mock timeline
        mock_timeline_store = Mock()
        mock_timeline_store.append = Mock()
        mock_timeline.return_value = mock_timeline_store
        
        ctx = Mock(spec=RequestContext)
        ctx.tenant_id = "t_tenant123"
        ctx.mode = "saas"
        ctx.env = "prod"
        ctx.project_id = "proj456"
        ctx.surface_id = "canvas"
        ctx.request_id = "req789"
        ctx.run_id = "run000"
        ctx.step_id = "step001"
        ctx.trace_id = "trace111"
        ctx.user_id = "user123"
        
        # Run should succeed and emit PASS
        mock_gate_chain.run(
            ctx=ctx,
            action="create_node",
            surface="canvas",
            subject_type="canvas",
            subject_id="canvas_123",
            skip_metrics=True,
        )
        
        # Verify timeline.append was called
        assert mock_timeline_store.append.called
        call_args = mock_timeline_store.append.call_args
        assert call_args is not None
        # Event should be StreamEvent with PASS result
        event = call_args[0][1]
        assert event.data["result"] == "PASS"


# ============================================================================
# EN-03: Canvas Command Durability Tests
# ============================================================================

class TestCanvasCommandDurability:
    """Test canvas command durability with idempotency and concurrency."""
    
    def test_apply_command_idempotency(self):
        """apply_command should be idempotent via idempotency_key."""
        cmd = CommandEnvelope(
            id="cmd_1",
            type="update_node",
            canvas_id="canvas_1",
            base_rev=0,
            idempotency_key="idempotent_key_1",
            args={"node_id": "n1", "value": 42},
        )
        
        # First apply
        with patch("engines.canvas_commands.service.verify_canvas_access"), patch(
            "engines.chat.service.transport_layer._get_bus",
            return_value=MagicMock(add_message=MagicMock()),
        ):
            result1 = asyncio.run(
                apply_command(
                    tenant_id="t_canvas",
                    user_id="user456",
                    command=cmd,
                )
            )
        assert result1.status == "applied"
        assert result1.current_rev == 1
        
        # Second apply with same idempotency_key should return same rev
        with patch("engines.canvas_commands.service.verify_canvas_access"), patch(
            "engines.chat.service.transport_layer._get_bus",
            return_value=MagicMock(add_message=MagicMock()),
        ):
            result2 = asyncio.run(
                apply_command(
                    tenant_id="t_canvas",
                    user_id="user456",
                    command=cmd,
                )
            )
        assert result2.status == "applied"
        assert result2.current_rev == 1  # Not incremented
    
    def test_apply_command_conflict_detection(self):
        """apply_command should detect revision conflicts via base_rev."""
        cmd1 = CommandEnvelope(
            id="cmd_1",
            type="update_node",
            canvas_id="canvas_2",
            base_rev=0,
            idempotency_key="key1",
            args={"value": 1},
        )
        
        cmd2 = CommandEnvelope(
            id="cmd_2",
            type="update_node",
            canvas_id="canvas_2",
            base_rev=0,  # Expects rev 0, but after cmd1 it's rev 1
            idempotency_key="key2",
            args={"value": 2},
        )
        
        # Apply first command
        with patch("engines.canvas_commands.service.verify_canvas_access"), patch(
            "engines.chat.service.transport_layer._get_bus",
            return_value=MagicMock(add_message=MagicMock()),
        ):
            result1 = asyncio.run(
                apply_command(
                    tenant_id="t_canvas",
                    user_id="user456",
                    command=cmd1,
                )
            )
        assert result1.current_rev == 1
        
        # Second command with stale base_rev should conflict
        with patch("engines.canvas_commands.service.verify_canvas_access"), patch(
            "engines.chat.service.transport_layer._get_bus",
            return_value=MagicMock(add_message=MagicMock()),
        ):
            result2 = asyncio.run(
                apply_command(
                    tenant_id="t_canvas",
                    user_id="user456",
                    command=cmd2,
                )
            )
        assert result2.status == "conflict"
        assert result2.current_rev == 1
        assert result2.recovery_ops is not None  # Contains recovery info


# ============================================================================
# EN-04: Canvas Snapshot and Replay Tests
# ============================================================================

class TestCanvasSnapshotReplay:
    """Test snapshot and replay endpoints."""
    
    def test_canvas_snapshot_returns_head_rev(self):
        """Canvas snapshot should return head revision and state."""
        # First, apply a command
        cmd = CommandEnvelope(
            id="cmd_1",
            type="create_node",
            canvas_id="canvas_3",
            base_rev=0,
            idempotency_key="snap_key1",
            args={"node_id": "n1"},
        )
        
        with patch("engines.canvas_commands.service.verify_canvas_access"), patch(
            "engines.chat.service.transport_layer._get_bus",
            return_value=MagicMock(add_message=MagicMock()),
        ):
            asyncio.run(
                apply_command(
                    tenant_id="t_canvas",
                    user_id="user456",
                    command=cmd,
                )
            )
        
        # Get snapshot
        snapshot = asyncio.run(
            get_canvas_snapshot(
                canvas_id="canvas_3",
                tenant_id="t_canvas",
            )
        )
        
        assert isinstance(snapshot, CanvasSnapshot)
        assert snapshot.canvas_id == "canvas_3"
        assert snapshot.head_rev == 1
        assert snapshot.head_event_id is not None
    
    def test_canvas_replay_returns_events(self):
        """Canvas replay should return events after cursor."""
        cmd1 = CommandEnvelope(
            id="cmd_1",
            type="create_node",
            canvas_id="canvas_4",
            base_rev=0,
            idempotency_key="replay_key1",
            args={"node_id": "n1"},
        )
        
        cmd2 = CommandEnvelope(
            id="cmd_2",
            type="update_node",
            canvas_id="canvas_4",
            base_rev=1,
            idempotency_key="replay_key2",
            args={"node_id": "n1", "value": 10},
        )
        with patch("engines.canvas_commands.service.verify_canvas_access"), patch(
            "engines.chat.service.transport_layer._get_bus",
            return_value=MagicMock(add_message=MagicMock()),
        ):
            result1 = asyncio.run(
                apply_command(
                    tenant_id="t_canvas",
                    user_id="user456",
                    command=cmd1,
                )
            )
        
        with patch("engines.canvas_commands.service.verify_canvas_access"), patch(
            "engines.chat.service.transport_layer._get_bus",
            return_value=MagicMock(add_message=MagicMock()),
        ):
            asyncio.run(
                apply_command(
                    tenant_id="t_canvas",
                    user_id="user456",
                    command=cmd2,
                )
            )
        
        # Replay from start
        events = asyncio.run(
            get_canvas_replay(
                canvas_id="canvas_4",
                tenant_id="t_canvas",
                after_event_id=None,
            )
        )
        
        assert len(events) >= 1
        assert all(isinstance(e, CanvasReplayEvent) for e in events)
        
        # Replay from first event
        events_after_first = asyncio.run(
            get_canvas_replay(
                canvas_id="canvas_4",
                tenant_id="t_canvas",
                after_event_id=events[0].event_id,
            )
        )
        
        assert len(events_after_first) == len(events) - 1
    
    def test_canvas_replay_invalid_cursor(self):
        """Canvas replay with invalid cursor should raise 410 error."""
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                get_canvas_replay(
                    canvas_id="canvas_5",
                    tenant_id="t_canvas",
                    after_event_id="evt_invalid_999999",
                )
            )
        
        exc = exc_info.value
        assert exc.status_code == 410
        assert exc.detail["error"]["code"] == "canvas.cursor_invalid"
        assert exc.detail["error"]["http_status"] == 410


# ============================================================================
# EN-05: Routing Enforcement Tests
# ============================================================================

class TestRoutingEnforcement:
    """Test that missing routes return 503 with proper error envelope."""
    
    @patch("engines.canvas_commands.store_service.routing_registry")
    def test_canvas_command_store_missing_route_returns_503(self, mock_registry):
        """Canvas command store should return 503 on missing route."""
        from engines.canvas_commands.store_service import CanvasCommandStoreService
        
        # Mock registry with no route
        mock_reg_instance = Mock()
        mock_reg_instance.get_route = Mock(return_value=None)
        mock_registry.return_value = mock_reg_instance
        
        ctx = Mock(spec=RequestContext)
        ctx.tenant_id = "t_tenant123"
        ctx.env = "saas"
        ctx.project_id = "proj456"
        
        # Should raise 503 error
        with pytest.raises(HTTPException) as exc_info:
            service = CanvasCommandStoreService(ctx)
        
        exc = exc_info.value
        assert exc.status_code == 503
        assert exc.detail["error"]["code"] == "canvas_command_store.missing_route"
        assert exc.detail["error"]["http_status"] == 503


class TestEnvelopeDomains:
    """Cross-domain envelope shape checks."""

    def _auth(self, tenant_id: str) -> AuthContext:
        return AuthContext(
            user_id="user-1",
            email="user@example.com",
            tenant_ids=[tenant_id],
            default_tenant_id=tenant_id,
            role_map={},
        )

    def test_gate_chain_block_envelope(self):
        """GateChain block should carry gate + http_status in envelope."""
        from engines.nexus.hardening.gate_chain import GateChain

        class BlockingKillSwitch:
            def ensure_action_allowed(self, ctx, action):
                error_response(
                    code="kill_switch.blocked",
                    message="blocked",
                    status_code=403,
                    gate="kill_switch",
                )

        ctx = RequestContext(
            tenant_id="t_gate",
            env="dev",
            mode="saas",
            project_id="proj_gate",
            surface_id="canvas",
            request_id="req-gate",
            run_id="run-1",
            step_id="step-1",
            user_id="user-1",
        )

        gate_chain = GateChain(kill_switch_service=BlockingKillSwitch())

        with pytest.raises(HTTPException) as exc_info:
            gate_chain.run(
                ctx=ctx,
                action="create_node",
                surface="canvas",
                subject_type="canvas",
                subject_id="canvas-123",
            )

        error = exc_info.value.detail["error"]
        assert error["gate"] == "kill_switch"
        assert error["http_status"] == 403
        assert error["code"] == "kill_switch.blocked"

    def test_event_spine_missing_route_envelope(self):
        """event_spine missing route returns 503 envelope."""
        ctx = RequestContext(
            tenant_id="t_event",
            env="dev",
            mode="saas",
            project_id="proj_evt",
            request_id="req_evt",
            user_id="user_evt",
        )
        auth = self._auth(ctx.tenant_id)
        payload = AppendEventRequest(event_type="analytics", source="agent", run_id="run-1")

        with patch("engines.event_spine.routes.EventSpineServiceRejectOnMissing") as mock_svc:
            mock_svc.side_effect = MissingEventSpineRoute(ctx)
            with pytest.raises(HTTPException) as exc_info:
                append_event(payload=payload, context=ctx, auth=auth)

        error = exc_info.value.detail["error"]
        assert error["code"] == "event_spine.missing_route"
        assert error["http_status"] == 503

    def test_budget_policy_not_found_envelope(self):
        """Budget routes return envelope on missing policy."""
        tenant_id = "t_budget"
        ctx = RequestContext(
            tenant_id=tenant_id,
            env="dev",
            mode="saas",
            project_id="proj_budget",
            request_id="req_budget",
        )
        auth = self._auth(tenant_id)
        with patch("engines.budget.routes.get_budget_policy_repo") as mock_repo_fn:
            repo = MagicMock()
            repo.get_policy.return_value = None
            mock_repo_fn.return_value = repo

            with pytest.raises(HTTPException) as exc_info:
                read_policy(context=ctx, auth=auth)

        error = exc_info.value.detail["error"]
        assert error["code"] == "budget.policy_not_found"
        assert error["http_status"] == 404

    def test_strategy_lock_not_found_envelope(self):
        """Strategy lock lookups return uniform envelope when missing."""
        ctx = RequestContext(
            tenant_id="t_strategy",
            env="dev",
            mode="saas",
            project_id="proj_strategy",
            request_id="req_strategy",
        )
        svc = StrategyLockService(repo=InMemoryStrategyLockRepository())

        with pytest.raises(HTTPException) as exc_info:
            svc.get_lock(ctx, "missing-lock")

        error = exc_info.value.detail["error"]
        assert error["code"] == "strategy_lock.not_found"
        assert error["http_status"] == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
