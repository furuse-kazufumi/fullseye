# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""1.0 前の修正 2026-11-05(hessian-np): ``hessian`` 型の産み手が torch の ``hessian3d`` だけだった。

素の ``pip install fullseye``(torch なし)では ``hessian_determinant`` / ``hessian_vesselness`` に
入力が届かず、型の鎖 ``voxel → hessian → voxel`` が行き止まりだった。numpy と scipy だけの産み手
``reprconv.voxel_to_hessian`` を足し、次を門にする:

* 返りの形が ``hessian3d`` と同じ(長さ 6 の list、各 (D,H,W) float32、順 zz, yy, xx, zy, zx, yx)。
* 真値: 2 次多項式 ½xᵀAx + bᵀx で内部の H = A(どの尺度でも)/ ガウス塊の中心で閉形式の値。
* ``sigma=0`` は ``hessian3d`` の 3 タップ核: torch があれば torch 版と、無ければ np.pad で
  書き下した独立実装と一致する(どちらの環境でも何かと比べる。skip しない)。
* torch を import できない interpreter で産み手 → 受け手 2 本が走り、管で vesselness が高く
  球で低い、球の中心で det H < 0(閉形式の値)になる。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import opsreprconv
import reprconv as rc

ROOT = Path(__file__).resolve().parents[1]
ORDER = ("zz", "yy", "xx", "zy", "zx", "yx")


def _grid(n=24):
    return np.mgrid[0:n, 0:n, 0:n].astype(np.float64)


def _quadratic(A, b, n=24):
    """f = ½ xᵀAx + bᵀx(座標の並びは (z, y, x))。H = A が真値。"""
    z, y, x = _grid(n) - n / 2.0
    X = (z, y, x)
    f = sum(b[i] * X[i] for i in range(3))
    for i in range(3):
        for j in range(3):
            f = f + 0.5 * A[i, j] * X[i] * X[j]
    return f + 620.0          # 明るさの底上げ: 和が 0 でない核ならここで Hxx が漏れる


A_TRUE = np.array([[1.5, 0.3, -0.4],
                   [0.3, -2.0, 0.7],
                   [-0.4, 0.7, 0.8]])
B_TRUE = np.array([0.5, -1.0, 2.0])
#: 成分 (zz, yy, xx, zy, zx, yx) の真値
H_TRUE = (A_TRUE[0, 0], A_TRUE[1, 1], A_TRUE[2, 2], A_TRUE[0, 1], A_TRUE[0, 2], A_TRUE[1, 2])


class TestShapeMatchesHessian3d:
    def test_list_of_six_float32_same_shape(self):
        vol = np.random.default_rng(0).random((7, 9, 11))
        h = rc.voxel_to_hessian(vol, sigma=1.0)
        assert isinstance(h, list) and len(h) == 6
        assert [c.shape for c in h] == [(7, 9, 11)] * 6
        assert {c.dtype for c in h} == {np.dtype(np.float32)}

    def test_registered_as_hessian_producer_from_voxel(self):
        meta = opsreprconv.OPSREPRCONV["voxel_to_hessian"]
        assert meta["in"] == ["voxel"] and meta["out"] == "hessian"

    def test_hessian_sort_has_a_numpy_producer_in_list_ops(self):
        import fullseye
        rows = fullseye.list_ops(include_ledger=True, include_algo=True)
        producers = sorted(r["name"] for r in rows if r.get("out_sort") == "hessian")
        assert len(producers) >= 2, producers
        assert "voxel_to_hessian" in producers and "hessian3d" in producers

    def test_op_index_lists_the_producer(self):
        idx = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
        rows = [o for o in idx["ops"] if o.get("name") == "voxel_to_hessian"]
        assert len(rows) == 1
        assert rows[0]["in_sorts"] == ["voxel"] and rows[0]["out_sort"] == "hessian"


class TestAnalyticTruth:
    @pytest.mark.parametrize("sigma", [0.0, 0.7, 1.0, 2.0])
    def test_quadratic_gives_constant_A_inside(self, sigma):
        h = rc.voxel_to_hessian(_quadratic(A_TRUE, B_TRUE), sigma=sigma)
        r = max(1, int(4.0 * sigma + 0.5)) + 1
        inner = (slice(r, -r),) * 3
        assert len(h) == len(H_TRUE) == 6
        for name, comp, want in zip(ORDER, h, H_TRUE):
            got = comp[inner].astype(np.float64)
            assert got.size > 0
            assert np.max(np.abs(got - want)) < 2e-4, (sigma, name, float(got.mean()), want)

    @pytest.mark.parametrize("s0,sigma", [(3.0, 1.5), (2.5, 1.0), (4.0, 2.0)])
    def test_gaussian_blob_centre_matches_closed_form(self, s0, sigma):
        """f = exp(−r²/2s0²) を σ で平滑 → 分散 s0²+σ²、振幅 (s0²/(s0²+σ²))^{3/2} のガウス。
        中心の H は対角 −A/(s0²+σ²)、非対角 0。"""
        n = 33
        z, y, x = _grid(n) - (n - 1) / 2.0
        f = np.exp(-(x * x + y * y + z * z) / (2 * s0 * s0))
        h = rc.voxel_to_hessian(f, sigma=sigma)
        s2 = s0 * s0 + sigma * sigma
        want_diag = -((s0 * s0 / s2) ** 1.5) / s2
        c = (n // 2,) * 3
        for k in range(3):
            assert abs(float(h[k][c]) - want_diag) < 0.02 * abs(want_diag), (k, float(h[k][c]), want_diag)
        for k in range(3, 6):
            assert abs(float(h[k][c])) < 1e-6
        # σ² 正規化(γ=1)はちょうど σ² 倍
        hn = rc.voxel_to_hessian(f, sigma=sigma, scale_normalize=True)
        np.testing.assert_allclose(np.asarray(hn[2], np.float64),
                                   np.asarray(h[2], np.float64) * sigma * sigma, rtol=1e-6, atol=1e-9)

    def test_constant_volume_gives_exact_zero(self):
        h = rc.voxel_to_hessian(np.full((9, 9, 9), 620.0), sigma=1.3)
        assert len(h) == 6
        assert max(float(np.max(np.abs(c))) for c in h) < 1e-9


def _tap3_reference(vol):
    """``hessian3d`` の docstring の核を np.pad + スライスで書き下した独立実装。"""
    v = np.asarray(vol, np.float64)
    p = np.pad(v, 1, mode="edge")
    D, H, W = v.shape

    def at(dz, dy, dx):
        return p[1 + dz:1 + dz + D, 1 + dy:1 + dy + H, 1 + dx:1 + dx + W]

    d2 = {-1: 1.0, 0: -2.0, 1: 1.0}
    d1 = {-1: -0.5, 0: 0.0, 1: 0.5}
    sm = {-1: 0.25, 0: 0.5, 1: 0.25}

    def sep(kz, ky, kx):
        out = np.zeros_like(v)
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                for c in (-1, 0, 1):
                    w = kz[a] * ky[b] * kx[c]
                    if w:
                        out += w * at(a, b, c)
        return out
    # 端は軸ごとに replicate して畳むのが hessian3d。上の 3 重和は 1 回の pad なので、
    # 3 軸が同時に端に掛かる角でも「軸ごとの replicate」と同じ値になる(pad edge は軸ごとに分離可能)
    return [sep(d2, sm, sm), sep(sm, d2, sm), sep(sm, sm, d2),
            sep(d1, d1, sm), sep(d1, sm, d1), sep(sm, d1, d1)]


class TestSigmaZeroIsTheHessian3dKernel:
    def test_matches_torch_or_independent_reference(self):
        vol = np.random.default_rng(3).random((10, 12, 14)).astype(np.float32) * 5.0
        got = rc.voxel_to_hessian(vol, sigma=0)
        try:
            import match3d
            ref = [t.cpu().numpy() for t in match3d.hessian3d(vol)]
            what = "torch hessian3d"
        except ImportError:
            ref = _tap3_reference(vol)
            what = "np.pad reference"
        assert len(got) == len(ref) == 6
        for name, g, r in zip(ORDER, got, ref):
            err = float(np.max(np.abs(np.asarray(g, np.float64) - np.asarray(r, np.float64))))
            assert err < 1e-5, (what, name, err)

    def test_independent_reference_agrees_too(self):
        """torch がある環境でも、書き下しの独立実装との一致を必ず確かめる。"""
        vol = np.random.default_rng(4).random((6, 7, 8))
        got = rc.voxel_to_hessian(vol, sigma=0)
        ref = _tap3_reference(vol)
        assert len(got) == 6
        for g, r in zip(got, ref):
            assert float(np.max(np.abs(np.asarray(g, np.float64) - r))) < 1e-6


_CHAIN_SCRIPT = r"""
import sys
sys.modules["torch"] = None            # torch を import できない interpreter(素の pip install 相当)
import numpy as np
import opsreprconv
n = 33
z, y, x = (np.mgrid[0:n, 0:n, 0:n].astype(float) - (n - 1) / 2.0)
tube = np.exp(-(x * x + y * y) / (2 * 2.0 ** 2))            # z に沿う明るい管、半径 2
ball = np.exp(-(x * x + y * y + z * z) / (2 * 2.5 ** 2))     # 明るい球、s0 = 2.5
ht = opsreprconv.call("voxel_to_hessian", tube, sigma=2.0)
hb = opsreprconv.call("voxel_to_hessian", ball, sigma=1.0)
vt = opsreprconv.call("hessian_vesselness", ht)
vb = opsreprconv.call("hessian_vesselness", hb)
db = opsreprconv.call("hessian_determinant", hb)
c = n // 2
print(repr((float(vt[c, c, c]), float(vb[c, c, c]), float(db[c, c, c]),
            float(vt[2:-2, c, c].min()), "torch" in sys.modules and sys.modules["torch"] is not None)))
"""


class TestChainRunsWithoutTorch:
    def test_voxel_to_hessian_to_consumers_without_torch(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        out = subprocess.run([sys.executable, "-c", _CHAIN_SCRIPT], cwd=str(ROOT), env=env,
                             capture_output=True, text=True, timeout=300)
        assert out.returncode == 0, out.stderr[-3000:]
        v_tube, v_ball, det_ball, v_tube_axis_min, torch_loaded = eval(out.stdout.strip().splitlines()[-1])
        assert torch_loaded is False
        assert v_tube > 0.5 and v_tube_axis_min > 0.5          # 管の軸上は全部高い
        # 球の中心は λ1=λ2=λ3 なので Ra = Rb = 1、S は中心で最大(c = S/2)→ 閉形式で
        # V = (1 − e^{−2})·e^{−2}·(1 − e^{−2}) ≈ 0.1012(α = β = 0.5)。管はその何倍も高い
        want_ball = (1 - np.exp(-2.0)) ** 2 * np.exp(-2.0)
        assert abs(v_ball - want_ball) < 0.01, (v_ball, want_ball)
        assert v_tube > 5 * v_ball
        s2 = 2.5 ** 2 + 1.0 ** 2
        want = (-((2.5 ** 2 / s2) ** 1.5) / s2) ** 3           # det = λ³(3 つとも同じ負の値)
        assert det_ball < 0 and abs(det_ball - want) < 0.06 * abs(want), (det_ball, want)


class TestRejects:
    @pytest.mark.parametrize("vol,sigma,kw,msg", [
        (np.zeros((0, 4, 4)), 1.0, {}, "empty"),
        (np.zeros((8, 8)), 1.0, {}, "sk_hessian"),
        (np.zeros((2, 3, 4, 5)), 1.0, {}, "3-D"),
        (np.full((4, 4, 4), np.nan), 1.0, {}, "non-finite"),
        (np.zeros((4, 4, 4)), -0.5, {}, "sigma"),
        (np.zeros((4, 4, 4)), float("inf"), {}, "sigma"),
        (np.zeros((4, 4, 4)), True, {}, "sigma"),
        (np.zeros((4, 4, 4)), 0.0, {"scale_normalize": True}, "scale_normalize"),
    ])
    def test_named_rejection(self, vol, sigma, kw, msg):
        with pytest.raises(ValueError, match=msg):
            rc.voxel_to_hessian(vol, sigma=sigma, **kw)
