# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.fixture — 既知の良品/不良品セットで recipe + spec を検定する(検査ワークフロー層 #4)。

恒等式: 分離できる仕様 → passed / 締めすぎ → 良品が過検出で failed / 緩めすぎ → 不良品が見逃しで failed /
壊れた 1 枚は error で failed(fail-closed)/ 空セットは ValueError / margin は限界までの距離(負 = 超過)。
"""
import numpy as np
import pytest

import fullseye as fs
from fullseye.fixture import inspection_fixture, spec_margins


def _plate(bright_px_side=10, level=0.9, seed=0):
    rng = np.random.default_rng(seed)
    im = 0.30 + 0.02 * rng.standard_normal((64, 64))
    k = bright_px_side
    im[32 - k:32 + k, 32 - k:32 + k] = level
    return np.clip(im, 0, 1)


def _measure(im):
    return {"mean": float(im.mean()), "bright": float((im > 0.5).sum()), "grade": "A"}


@pytest.fixture
def sets(tmp_path):
    good = tmp_path / "good"; bad = tmp_path / "bad"
    good.mkdir(); bad.mkdir()
    for i in range(6):
        np.save(good / ("g%02d.npy" % i), _plate(10, seed=i))           # 明部 400 px
    for i, k in enumerate((13, 15, 7, 15)):
        np.save(bad / ("b%02d.npy" % i), _plate(k, seed=10 + i))        # 676 / 900 / 196 / 900 px
    return good, bad


SPEC = {"bright": {"nominal": 400.0, "tol": 60.0}, "mean": {"min": 0.2, "max": 0.6}, "grade": {"eq": "A"}}


def test_separable_spec_passes_with_margins(sets):
    good, bad = sets
    f = inspection_fixture(good, bad, None, measure=_measure, spec=SPEC)
    assert f["passed"] is True
    assert f["confusion"] == {"good": {"ok": 6, "ng": 0, "error": 0}, "bad": {"ok": 0, "ng": 4, "error": 0}}
    assert f["escapes"] == [] and f["false_rejects"] == [] and f["errors"] == []
    m = f["margins"]["bright"]
    assert m["n"] == 6 and m["min_margin"] == pytest.approx(60.0) and m["min_margin_norm"] == pytest.approx(1.0)
    assert f["margins"]["grade"] == {"n": 6, "violations": 0}
    assert f["detail"].startswith("passed: good 6/6 ok, bad 4/4 ng")
    assert "tightest margin" in f["detail"]


def test_too_tight_spec_fails_with_false_rejects(sets):
    good, bad = sets
    tight = dict(SPEC, mean={"min": 0.2, "max": 0.3})                     # 良品の mean ≈ 0.44 → 全部 ng
    f = inspection_fixture(good, bad, None, measure=_measure, spec=tight)
    assert f["passed"] is False
    assert len(f["false_rejects"]) == 6 and f["escapes"] == []
    assert f["margins"]["mean"]["min_margin"] < 0                         # 負 = 超過
    assert f["detail"].startswith("failed: 6 false reject(s)")


def test_too_loose_spec_fails_with_escapes(sets):
    good, bad = sets
    loose = dict(SPEC, bright={"nominal": 400.0, "tol": 600.0})           # 196〜900 px が全部通る(±400 では 900 がまだ ng)
    f = inspection_fixture(good, bad, None, measure=_measure, spec=loose)
    assert f["passed"] is False
    assert len(f["escapes"]) == 4 and f["false_rejects"] == []
    assert "4 escape(s)" in f["detail"] and "b00.npy" in f["detail"]


def test_a_broken_file_is_an_error_and_fails_the_fixture(sets):
    good, bad = sets
    (good / "g99.npy").write_bytes(b"broken")
    f = inspection_fixture(good, bad, None, measure=_measure, spec=SPEC)
    assert f["passed"] is False and len(f["errors"]) == 1
    assert f["confusion"]["good"]["error"] == 1 and "1 error(s)" in f["detail"]


def test_empty_set_and_broken_spec_fail_closed(sets, tmp_path):
    good, bad = sets
    empty = tmp_path / "empty"; empty.mkdir()
    with pytest.raises(ValueError):
        inspection_fixture(good, empty, None, measure=_measure, spec=SPEC)
    with pytest.raises(ValueError):
        inspection_fixture(good, bad, None, measure=_measure, spec={"bright": {"mx": 1}})


def test_reports_are_written_per_set(sets, tmp_path):
    good, bad = sets
    f = inspection_fixture(good, bad, None, measure=_measure, spec=SPEC, report_path=tmp_path / "fx.md", title="FX")
    assert f["good"]["report_path"].endswith("fx_good.md") and f["bad"]["report_path"].endswith("fx_bad.md")
    assert (tmp_path / "fx_good.md").read_text(encoding="utf-8").startswith("# FX / good")


def test_spec_margins_on_measurement_lists():
    ms = [{"w": 3.02, "a": 12.0, "g": "A"}, {"w": 2.97, "a": 14.9, "g": "B"}, {"w": float("nan"), "a": 10.0}]
    spec = {"w": {"nominal": 3.0, "tol": 0.05}, "a": {"min": 10, "max": 15}, "g": {"in": ["A"]}}
    m = spec_margins(ms, spec)
    assert m["w"]["n"] == 2 and m["w"]["min_margin"] == pytest.approx(0.02) and m["w"]["min_margin_norm"] == pytest.approx(0.4)
    assert m["a"]["n"] == 3 and m["a"]["min_margin"] == pytest.approx(0.0) and m["a"]["worst_value"] == 10.0
    assert m["a"]["min_margin_norm"] == pytest.approx(0.0)
    assert m["g"] == {"n": 2, "violations": 1}


def test_facade_exposes_the_fixture_layer():
    assert fs.inspection_fixture is inspection_fixture and fs.spec_margins is spec_margins
    assert {"inspection_fixture", "spec_margins"} <= set(fs.__all__)
