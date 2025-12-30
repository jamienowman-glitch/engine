"""Gate2 durability test for tenant/mode/project scoped memory."""

from pathlib import Path

from engines.common.identity import RequestContext
from engines.memory.repository import FileMemoryRepository
from engines.nexus.memory.models import SessionTurn
from engines.nexus.memory.service import SessionMemoryService


def _make_context() -> RequestContext:
    return RequestContext(
        tenant_id="t_system",
        mode="saas",
        project_id="proj_memory",
        surface_id="web",
        app_id="app_memory",
        user_id="user_memory",
        request_id="req_memory",
    )


def test_memory_persistence(tmp_path: Path) -> None:
    storage_dir = tmp_path / "memory_store"
    ctx = _make_context()
    repo_a = FileMemoryRepository(base_dir=str(storage_dir))
    service_a = SessionMemoryService(repo=repo_a)

    first_turn = SessionTurn(session_id="session-1", role="user", content="hello")
    second_turn = SessionTurn(session_id="session-1", role="assistant", content="durable")
    service_a.add_turn(ctx, "session-1", first_turn)
    service_a.add_turn(ctx, "session-1", second_turn)

    repo_b = FileMemoryRepository(base_dir=str(storage_dir))
    service_b = SessionMemoryService(repo=repo_b)

    snapshot = service_b.get_session(ctx, "session-1")
    assert len(snapshot.turns) == 2
    assert [turn.role for turn in snapshot.turns] == ["user", "assistant"]
    assert snapshot.turns[0].metadata.get("turn_id") == first_turn.turn_id
    assert snapshot.mode == "saas"
    assert snapshot.project_id == "proj_memory"
