import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "tools" / "merge_test_durations.py"


def test_merge_duration_files_uses_union_and_slower_duplicate(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    output = tmp_path / "merged.json"
    first.write_text(json.dumps({"tests/test_a.py::test_a": 1.0, "same": 2.0}))
    second.write_text(json.dumps({"tests/test_b.py::test_b": 3.0, "same": 1.0}))

    subprocess.run(
        [sys.executable, str(SCRIPT), str(first), str(second), "-o", str(output)],
        check=True,
    )

    assert json.loads(output.read_text()) == {
        "same": 2.0,
        "tests/test_a.py::test_a": 1.0,
        "tests/test_b.py::test_b": 3.0,
    }


def test_merge_rejects_non_mapping_input(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("[]")
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.run(
            [sys.executable, str(SCRIPT), str(bad), "-o", str(tmp_path / "out")],
            check=True,
        )


def test_merge_with_baseline_ignores_carried_over_values(tmp_path):
    """pytest-split は走らなかった試験の値をそのまま書き戻す。seed と同じ値は観測ではない。

    2026-10-22 の最初の run で、seed の平均値 0.8979 が実測(多くは 0.1 s 未満)に max で勝ち、
    17,310 件のうち 16,860 件が平均値のまま残った。
    """
    baseline = tmp_path / "baseline.json"
    shard_a = tmp_path / "a.json"
    shard_b = tmp_path / "b.json"
    output = tmp_path / "merged.json"
    baseline.write_text(json.dumps({"fast": 0.9, "slow": 0.9, "unmeasured": 0.9}))
    shard_a.write_text(json.dumps({"fast": 0.05, "slow": 0.9, "unmeasured": 0.9}))      # slow は持ち越し
    shard_b.write_text(json.dumps({"fast": 0.9, "slow": 3.0, "unmeasured": 0.9, "new": 0.2}))

    subprocess.run(
        [sys.executable, str(SCRIPT), str(shard_a), str(shard_b), "-o", str(output),
         "--baseline", str(baseline)],
        check=True,
    )

    assert json.loads(output.read_text()) == {
        "fast": 0.05,        # seed の 0.9 に負けない
        "new": 0.2,
        "slow": 3.0,
        "unmeasured": 0.9,   # 誰も測っていないので seed のまま
    }

