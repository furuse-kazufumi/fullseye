# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""連鎖ファザー wave-4 TYPEMISS 第 3 層 7 op の型契約回帰。

ops3d/ops1d の目録が宣言する out 型と call() の実返却が一致すること
(=「目録の型の嘘」の再発防止)を、正本の検証関数 tools/chain_fuzz.TYPE_CHECKS
で固定する。先例: tests/test_volprobe.py::test_ops3d_call_returns_declared_types。

対象(wave-4 署名):
  - local_min_max_funct_1d  dict{"max","min"}      → table 宣言に修正
  - match_funct_1d_trans    dict{"shift","score"}  → table 宣言に修正
  - mean_curvature          (N,) ndarray           → signal 宣言に修正
  - gaussian_curvature      (N,) ndarray           → signal 宣言に修正
  - curvature_torsion       (kappa, tau) 同格対    → adapter stack で (2,N) pairs
  - arc_length              (cumulative, total)    → adapter で全長 float(measurement)
  - surface_form_error      (residual, rms, pv)    → adapter で pv float(measurement)
"""
import numpy as np
import pytest

pytest.importorskip("torch")   # ops3d は torch 依存モジュールを束ねる

import ops1d
import ops3d
from tools.chain_fuzz import TYPE_CHECKS


def _check(registry, name, value):
    """registry の宣言 out 型に対する TYPE_CHECKS を value が通ることを表明。"""
    out = registry[name]["out"]
    check = TYPE_CHECKS.get(out)
    assert check is not None, f"{name}: 宣言型 {out!r} が TYPE_CHECKS に無い(語彙の穴)"
    assert check(value), (
        f"{name}: declared {out!r} but call() returned "
        f"{type(value).__name__}{getattr(value, 'shape', '')}")


def _helix(n=60, a=2.0, b=0.5):
    """螺旋 r=(a cosθ, a sinθ, bθ) — curve3d の GT 検証にも使う標準曲線。"""
    th = np.linspace(0.0, 4.0 * np.pi, n)
    return np.stack([a * np.cos(th), a * np.sin(th), b * th], axis=1)


def _sphere_points(n=80, seed=0):
    """半径 1 の球面上の点群(曲率 op 用の実データ)。"""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal((n, 3))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


# --------------------------------------------------------------------------- #
# ops1d(funct1d)— dict 返却 → table 宣言
# --------------------------------------------------------------------------- #
def test_local_min_max_funct_1d_table():
    """local_min_max_funct_1d: dict{"max","min"} が table 宣言を通る。"""
    y = np.sin(np.linspace(0, 4 * np.pi, 64))
    r = ops1d.call("local_min_max_funct_1d", y)
    assert ops1d.OPS1D["local_min_max_funct_1d"]["out"] == "table"
    _check(ops1d.OPS1D, "local_min_max_funct_1d", r)
    assert set(r) == {"max", "min"} and len(r["max"]) >= 1 and len(r["min"]) >= 1


def test_match_funct_1d_trans_table():
    """match_funct_1d_trans: dict{"shift","score"} が table 宣言を通り、shift が復元される。"""
    y1 = np.sin(np.linspace(0, 4 * np.pi, 128))
    y2 = np.roll(y1, 5)                      # y2 = y1 を右へ 5 → shift = -5
    r = ops1d.call("match_funct_1d_trans", y1, y2)
    assert ops1d.OPS1D["match_funct_1d_trans"]["out"] == "table"
    _check(ops1d.OPS1D, "match_funct_1d_trans", r)
    assert r["shift"] == -5


# --------------------------------------------------------------------------- #
# ops3d(curvature3d)— 点ごと (N,) 曲率列 → signal 宣言
# --------------------------------------------------------------------------- #
def test_mean_curvature_signal():
    """mean_curvature: (N,) 配列が signal 宣言を通る(単位球で |H|≈1)。"""
    p = _sphere_points()
    r = ops3d.call("mean_curvature", p, k=25)
    assert ops3d.OPS3D["mean_curvature"]["out"] == "signal"
    _check(ops3d.OPS3D, "mean_curvature", r)
    assert r.shape == (len(p),)
    assert np.median(np.abs(r)) == pytest.approx(1.0, rel=0.3)


def test_gaussian_curvature_signal():
    """gaussian_curvature: (N,) 配列が signal 宣言を通る(単位球で K≈1)。"""
    p = _sphere_points()
    r = ops3d.call("gaussian_curvature", p, k=25)
    assert ops3d.OPS3D["gaussian_curvature"]["out"] == "signal"
    _check(ops3d.OPS3D, "gaussian_curvature", r)
    assert r.shape == (len(p),)
    assert np.median(r) == pytest.approx(1.0, rel=0.3)


# --------------------------------------------------------------------------- #
# ops3d(curve3d)— 同格タプルは stack、補助つきタプルは本体を剥がす
# --------------------------------------------------------------------------- #
def test_curvature_torsion_pairs():
    """curvature_torsion: (kappa, tau) が adapter で (2,N) に stack され pairs 宣言を通る。"""
    c = _helix()
    r = ops3d.call("curvature_torsion", c)
    assert ops3d.OPS3D["curvature_torsion"]["out"] == "pairs"
    _check(ops3d.OPS3D, "curvature_torsion", r)
    assert isinstance(r, np.ndarray) and r.shape == (2, len(c))
    # 螺旋の解析値 κ=a/(a²+b²)=0.4706, τ=b/(a²+b²)=0.1176(端点は数値微分が乱れる)
    a2b2 = 2.0 ** 2 + 0.5 ** 2
    assert np.median(r[0]) == pytest.approx(2.0 / a2b2, rel=0.1)
    assert np.median(r[1]) == pytest.approx(0.5 / a2b2, rel=0.1)


def test_arc_length_measurement():
    """arc_length: (cumulative, total) が adapter で全長 float に剥がれ measurement を通る。"""
    c = _helix()
    r = ops3d.call("arc_length", c)
    assert ops3d.OPS3D["arc_length"]["out"] == "measurement"
    _check(ops3d.OPS3D, "arc_length", r)
    # 螺旋の解析全長 = θ_max·√(a²+b²)(折れ線近似なのでわずかに短い)
    exact = 4.0 * np.pi * np.sqrt(2.0 ** 2 + 0.5 ** 2)
    assert 0.99 * exact < r <= exact


# --------------------------------------------------------------------------- #
# ops3d(match3d)— (residual, rms, pv) → pv を剥がして measurement
# --------------------------------------------------------------------------- #
def test_surface_form_error_measurement():
    """surface_form_error: adapter が pv(残差 peak-to-valley)を返し measurement を通る。"""
    yy, xx = np.mgrid[0:16, 0:16].astype(float)
    height = 0.3 * xx + 0.1 * yy               # 傾いた理想平面 → 残差 0
    bump = height.copy()
    bump[8, 8] += 1.0                           # 1 点の欠陥 → pv ≈ 1
    r_flat = ops3d.call("surface_form_error", height, degree=1)
    r_bump = ops3d.call("surface_form_error", bump, degree=1)
    assert ops3d.OPS3D["surface_form_error"]["out"] == "measurement"
    _check(ops3d.OPS3D, "surface_form_error", r_flat)
    _check(ops3d.OPS3D, "surface_form_error", r_bump)
    assert r_flat == pytest.approx(0.0, abs=1e-9)
    assert r_bump == pytest.approx(1.0, rel=0.05)


def test_opsmath_call_returns_declared_types():
    """math 次元追加(2026-09-01)の初走行で mat_svd/mat_eigh が「宣言 table・
    実際 tuple」の型の嘘として検出された回帰。opsmath.call() が全 16 op で
    宣言 out 型どおり返すことを TYPE_CHECKS で固定する。"""
    import opsmath
    rng = np.random.default_rng(0)
    A = rng.standard_normal((6, 4))
    S = rng.standard_normal((5, 5))
    spd = S @ S.T + 5.0 * np.eye(5)
    x = np.linspace(0.0, 1.0, 16)
    y = np.sin(x * 6.0)
    args = {
        "mat_solve": (spd, np.ones(5)), "mat_lstsq": (A, np.ones(6)),
        "mat_svd": (A,), "mat_eigh": (spd,), "mat_pinv": (A,),
        "mat_cond": (spd,),
        "stat_describe": (y,), "stat_histogram": (y,),
        "stat_covariance": (A,), "stat_correlation": (A,),
        "stat_zscore": (y,),
        "interp_linear": (x, y, x[:8] + 0.01),
        "interp_cubic": (x, y, x[:8] + 0.01),
        "poly_fit": (x, y, 3), "poly_eval": (np.array([1.0, 0.0, -1.0]), x),
        "poly_roots": (np.array([1.0, 0.0, -1.0]),),
    }
    from tools.chain_fuzz import TYPE_CHECKS
    missing = [n for n in opsmath.OPSMATH if n not in args]
    assert not missing, f"test args missing for: {missing}"
    for name, a in args.items():
        out_t = opsmath.OPSMATH[name]["out"]
        val = opsmath.call(name, *a)
        check = TYPE_CHECKS.get(out_t)
        assert check is not None, f"{name}: unknown declared type {out_t!r}"
        assert check(val), (name, out_t, type(val).__name__)
    # 素の API は数学慣習の tuple を維持(unpacking 互換)
    U, s, Vt = opsmath.get("mat_svd")(A)
    assert U.shape[0] == 6 and Vt.shape[1] == 4
