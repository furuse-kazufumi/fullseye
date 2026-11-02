"""HALCON OpenCL 84-op correspondence matrix gate (E').

門: N1(Fullseye 対応あり) + N3(未対応) == 84。JSON から独立に数え直し、生成物の
見出しの数字と一致させる。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _data():
    return json.loads((ROOT / "docs" / "perf" / "halcon_opencl_parity.json").read_text(encoding="utf-8"))


def test_total_is_84():
    assert _data()["total"] == 84


def test_n1_plus_n3_equals_84_counted_independently():
    data = _data()
    rows = data["rows"]
    n1 = sum(1 for r in rows if r["fullseye_ops"])
    n3 = sum(1 for r in rows if not r["fullseye_ops"])
    assert n1 + n3 == 84, "independent count N1=%d N3=%d" % (n1, n3)
    assert data["n1_fullseye"] == n1
    assert data["n3_missing"] == n3
    # N2 は N1 の部分集合
    n2 = sum(1 for r in rows if r["fullseye_ops"] and r["gpu_path"])
    assert data["n2_gpu"] == n2 <= n1


def test_generator_is_idempotent():
    sys.path.insert(0, str(ROOT / "tools"))
    import gen_halcon_opencl_parity as g
    assert g.main(["--check"]) == 0


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
