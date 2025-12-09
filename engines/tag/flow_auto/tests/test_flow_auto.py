from engines.tag.flow_auto.engine import run
from engines.tag.flow_auto.types import FlowAutoInput, FlowAutoOutput


def test_flow_auto_predicts_pairs_and_half_time() -> None:
    bars = [
        {"bar_index": 1, "syllables": 8, "bpm": 120},
        {"bar_index": 2, "syllables": 9, "bpm": 120},
    ]
    out = run(FlowAutoInput(bars=bars))
    assert isinstance(out, FlowAutoOutput)
    assert len(out.flow_pairs) == 1
    assert bars[0]["flow_pred"] == "half_time"


def test_flow_auto_triplet_machine() -> None:
    bars = [
        {"bar_index": 1, "syllables": 24, "bpm": 140},
        {"bar_index": 2, "syllables": 22, "bpm": 140},
    ]
    out = run(FlowAutoInput(bars=bars))
    assert out.flow_pairs[0].flow_pred == "triplet_machine"
