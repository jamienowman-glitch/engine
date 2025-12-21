from engines.common.identity import RequestContext
from engines.kill_switch.models import KillSwitchUpdate
from engines.kill_switch.service import KillSwitchService, get_kill_switch_service, set_kill_switch_service
from engines.kill_switch.repository import InMemoryKillSwitchRepository
import pytest


def test_kill_switch_blocks_provider():
    repo = InMemoryKillSwitchRepository()
    svc = KillSwitchService(repo)
    set_kill_switch_service(svc)
    ctx = RequestContext(tenant_id="t_demo", env="dev")
    svc.upsert(ctx, KillSwitchUpdate(disable_providers=["aws"]))
    with pytest.raises(Exception):
        svc.ensure_provider_allowed(ctx, "aws")


def test_kill_switch_allows_if_not_set():
    repo = InMemoryKillSwitchRepository()
    svc = KillSwitchService(repo)
    set_kill_switch_service(svc)
    ctx = RequestContext(tenant_id="t_demo", env="dev")
    svc.ensure_provider_allowed(ctx, "gcp")
