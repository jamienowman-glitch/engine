from pathlib import Path
import json

import pytest

from engines.dataset.pack_jsonl.engine import run
from engines.dataset.pack_jsonl.types import PackJsonlInput, PackJsonlOutput


def test_pack_jsonl_builds_train_val(tmp_path: Path) -> None:
    bars = {"bars": [{"text": "line", "flow_pred": "half_time"}, {"text": "line2", "flow_pred": "skippy"}]}
    bars_path = tmp_path / "bars.json"
    bars_path.write_text(json.dumps(bars), encoding="utf-8")
    out_dir = tmp_path / "out"
    res = run(PackJsonlInput(bars_files=[bars_path], output_dir=out_dir))
    assert isinstance(res, PackJsonlOutput)
    assert res.total_samples == 2
    assert res.train_path.exists()
    assert res.val_path.exists()


def test_pack_jsonl_requires_files(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        PackJsonlInput(bars_files=[], output_dir=tmp_path)
