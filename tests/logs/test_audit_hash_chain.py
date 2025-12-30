from __future__ import annotations

import json

from engines.common.identity import RequestContext
from engines.logging.audit_chain import AuditChainService, FileAuditRepository


def _build_context() -> RequestContext:
    return RequestContext(
        tenant_id="t_demo",
        mode="lab",
        project_id="p_audit",
        request_id="req-123",
        env="dev",
        surface_id="audit-surface",
        app_id="audit-app",
    )


def test_audit_hash_chain_append_and_verify(tmp_path) -> None:
    repo = FileAuditRepository(base_dir=tmp_path)
    service = AuditChainService(repository=repo)
    ctx = _build_context()
    for idx in range(3):
        service.record_event(
            ctx,
            action=f"op-{idx}",
            input_data={"payload": f"value-{idx}"},
            metadata={"sequence": idx},
        )

    records = service.verify_chain(ctx)
    assert len(records) == 3
    assert records[0].prev_hash == ""
    assert records[1].prev_hash == records[0].hash
    assert records[2].prev_hash == records[1].hash

    scope = service._scope_from_context(ctx)
    path = repo.path_for_scope(scope)
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 3

    tampered = json.loads(lines[1])
    tampered["payload"]["metadata"]["tampered"] = True
    lines[1] = json.dumps(tampered)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    try:
        service.verify_chain(ctx)
        raise AssertionError("tampering should be detected")
    except RuntimeError as exc:
        assert "hash mismatch" in str(exc)
