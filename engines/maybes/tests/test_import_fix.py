
from engines.maybes.schemas import MaybeSourceType
from engines.maybes import MaybeSourceType as MST_Init

def test_maybe_source_type_import():
    assert MaybeSourceType is not None
    assert MST_Init is not None
    assert MaybeSourceType.user == "user"
    assert MaybeSourceType.agent == "agent"
