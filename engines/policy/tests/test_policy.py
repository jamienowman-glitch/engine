import pytest
from engines.policy.models import PolicyAttachment, Requirements
from engines.policy.service import PolicyService

def test_policy_resolution_default():
    svc = PolicyService()
    reqs = svc.get_requirements("any_tool", "any_scope")
    assert reqs.firearms is False
    assert len(reqs.licenses) == 0

def test_policy_resolution_configured():
    svc = PolicyService()
    
    att = PolicyAttachment(scopes={
        "dangerous.tool.nuke": Requirements(firearms=True, licenses=["atomic_auth"]),
        "safe.tool.echo": Requirements(firearms=False)
    })
    
    svc.set_policy("global_config", att)
    
    # Check safe
    reqs_safe = svc.get_requirements("safe.tool", "echo")
    assert reqs_safe.firearms is False
    
    # Check dangerous
    reqs_danger = svc.get_requirements("dangerous.tool", "nuke")
    assert reqs_danger.firearms is True
    assert "atomic_auth" in reqs_danger.licenses
    
    # Check unknown
    reqs_unknown = svc.get_requirements("dangerous.tool", "other")
    assert reqs_unknown.firearms is False
