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
