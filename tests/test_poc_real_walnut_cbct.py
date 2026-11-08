# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``examples/poc_real_walnut_cbct.py`` と取得道具の門(実データが無くても回る部分)。

Gates of the walnut cone-beam CT PoC and its fetch tool that run without the data.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

import realdata
from examples import poc_real_walnut_cbct as poc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import fetch_walnut_cbct as fetch  # noqa: E402


def test_synthetic_gates_pass_and_measure_something():
    g = poc.Gates()
    res = poc.synthetic_gates(g)
    assert len(g.rows) == 3 and not g.failed(), g.failed()
    assert 0.0 <= res["adjoint_gap"] < 1e-10 and res["warp_err_px"] < 1e-9


def test_fit_geometry_reads_a_rolled_and_shifted_detector():
    beta = np.deg2rad(1.2 * np.arange(300))
    th = math.radians(-0.3)
    n = np.stack([-np.sin(beta), np.cos(beta), 0 * beta], 1)
    uh = np.stack([np.cos(beta), np.sin(beta), 0 * beta], 1)
    z = np.array([0.0, 0.0, 1.0])
    s = -50.0 * n + np.array([0, 0, -0.2])
    d = s + 150.0 * n - 0.5 * z + 0.25 * uh
    u = (np.cos(th) * uh - np.sin(th) * z) * 0.2
    v = (np.sin(th) * uh + np.cos(th) * z) * 0.2
    fit = poc.fit_geometry(np.hstack([s, d, u, v]))
    assert fit["dso"] == pytest.approx(50.0, abs=1e-9) and fit["dsd"] == pytest.approx(150.0, abs=1e-9)
    assert fit["theta_deg"] == pytest.approx(-0.3, abs=1e-9)          # 符号つき
    assert fit["dh_mm"] == pytest.approx(-0.5, abs=1e-9) and fit["da_mm"] == pytest.approx(0.25, abs=1e-9)
    assert fit["src_z"] == pytest.approx(-0.2, abs=1e-12)
    assert fit["step_deg"] == pytest.approx(1.2, abs=1e-9)


def test_ideal_warp_without_roll_and_offset_is_a_pure_binning_map():
    fit = {"theta_deg": 0.0, "du": 0.1, "da_mm": 0.0, "dh_mm": 0.0}
    # 実検出器 972 × 768 を 8 × 8 に束ね、上下 2 行を落とした 121 × 96。中心は元の画素の (383.5, 485.5)
    W = poc.ideal_warp(fit, 8, poc.DET_ROWS - 4, 2, poc.DET_COLS // 8, (poc.DET_ROWS - 4) // 8)
    # 束ねた画素 (x, y) は、中心を合わせた理想の格子の同じ番号へ写る
    for x, y in [(0, 0), (47, 60), (95, 120)]:
        q = W @ np.array([x, y, 1.0])
        assert q[0] == pytest.approx(x, abs=1e-12) and q[1] == pytest.approx(y, abs=1e-12)


def test_box_weights_cover_the_coarse_voxel_exactly():
    for ratio in (2, 3, 4, 5):
        off, w = poc._box_weights(ratio)
        assert w.sum() == pytest.approx(1.0)
        assert np.array_equal(off, -off[::-1]) and np.allclose(w, w[::-1])     # 中心に対して対称
        # 箱の幅は ratio × 0.1 mm(偶数は両端の半分の重みで 1 画素ぶん)
        width = (len(w) if ratio % 2 else len(w) - 1) * 0.1
        assert width == pytest.approx(ratio * 0.1)
        assert float(np.sum(off * w)) == pytest.approx(0.0, abs=1e-15)


def test_plane_down_of_a_constant_is_the_constant():
    a = np.full((poc.REF_N, poc.REF_N), 0.0237)
    for n, ratio in ((127, 3), (97, 4)):
        out = poc._plane_down(a, n, ratio)
        assert out.shape == (n, n) and np.allclose(out, 0.0237, atol=1e-15)


def test_score_reports_the_absolute_scale():
    ref = np.zeros((64, 64))
    ref[20:44, 20:44] = 0.02
    mask = np.ones_like(ref, bool)
    sc = poc.score(1.1 * ref, ref, mask)
    assert sc["scale"] == pytest.approx(1.1) and sc["rmse"] > 0 and sc["ssim"] < 1.0


def test_missing_data_is_none_and_a_tampered_manifest_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_WALNUT_CBCT_DATA", str(tmp_path))
    assert realdata.walnut_cbct_root(required=False) is None
    with pytest.raises(realdata.RealDataError, match="fetch_walnut_cbct"):
        realdata.walnut_cbct_root(required=True)
    (tmp_path / realdata.WALNUT_CBCT_MANIFEST).write_text(json.dumps([["a", 1, "0" * 64]]), encoding="ascii")
    with pytest.raises(realdata.RealDataError, match="SHA-256"):
        realdata.walnut_cbct_root(required=False)


def test_manifest_round_trip_checks_every_member(tmp_path, monkeypatch):
    (tmp_path / "x.bin").write_bytes(b"walnut")
    digest = realdata.walnut_cbct_write_manifest(tmp_path, ["x.bin"])
    monkeypatch.setattr(realdata, "WALNUT_CBCT_MANIFEST_SHA256", digest)
    assert realdata.walnut_cbct_root(required=True, root=tmp_path) == tmp_path
    (tmp_path / "x.bin").write_bytes(b"walnuT")
    with pytest.raises(realdata.RealDataError, match="SHA-256"):
        realdata.walnut_cbct_root(required=True, root=tmp_path)


def test_the_fetch_list_is_what_the_poc_reads():
    pre = "Walnut1/"
    names = [pre + "Projections/tubeV2/scan_%06d.tif" % i for i in range(1201)]
    names += [pre + "Projections/tubeV2/" + n for n in ("scan_geom_corrected.geom", "di000000.tif", "io000000.tif",
                                                         "io000001.tif", "scan settings.txt", "data settings XRE.txt")]
    names += [pre + "Reconstructions/%s_%06d.tiff" % (r, k) for r in ("full_AGD_50", "fdk_pos2", "fdk_pos1")
              for k in range(501)]
    got = fetch.wanted(names)
    assert len(got) == 300 + 1 + 6 + 2 * 501          # 300 枚 + 同じ角度の撮り直し 1 枚 + 付属 6 + 参照 2 × 501
    assert not any("fdk_pos1" in n for n in got)
    assert pre + "Projections/tubeV2/scan_001200.tif" in got and pre + "Projections/tubeV2/scan_000000.tif" in got
    assert pre + "Projections/tubeV2/scan_000004.tif" in got and pre + "Projections/tubeV2/scan_000002.tif" not in got
    with pytest.raises(SystemExit, match="zip"):
        fetch.wanted([n for n in names if not n.endswith("scan_001200.tif")])


def test_fetch_refuses_to_go_online_in_ci(monkeypatch, tmp_path):
    monkeypatch.setenv("CI", "1")
    with pytest.raises(SystemExit, match="CI"):
        fetch.fetch(tmp_path)
