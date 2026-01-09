import pytest
from engines.nexus.schemas import SpaceKey, Scope

def test_space_key_import_and_usage():
    """Test that SpaceKey can be imported and instantiated correctly."""
    key = SpaceKey(
        scope=Scope.TENANT,
        tenant_id="t_acme",
        env="prod",
        project_id="p123",
        surface_id="marketing",
        space_id="main"
    )

    assert key.scope == Scope.TENANT
    assert key.tenant_id == "t_acme"
    assert str(key) == "Scope.TENANT:t_acme:prod:p123:marketing:main"

def test_dependencies_import():
    """Test that new dependencies can be imported."""
    import lancedb
    import fsspec
    import s3fs
    import gcsfs
    import adlfs

    assert lancedb.__version__ is not None
