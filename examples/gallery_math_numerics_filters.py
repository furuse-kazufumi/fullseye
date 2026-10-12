# -*- coding: utf-8 -*-
"""事例: 特殊関数・求積・NURBS・波源の数・離散化・ウェーブレットを閉形式で確かめる(数学の台帳 op ギャラリー)

平たく言うと:
  mathnumerics / mathgeometry / mathspectral / mathtransforms の op を、教科書に答えが載っている入力で 1 本ずつ呼ぶ。
  各行に「何を期待し、何が出て、合ったか」を印字し、外れたら exit 1。

確かめ方(op ごとの真値):
  * bessel           —— 半整数次の閉形式 J_{1/2} = √(2/πx) sin x・I_{1/2} = √(2/πx) sinh x・K_{1/2} = √(π/2x) e^{−x}、
                        J₀ の最初の零点 2.404825557695773、Wronskian J₁Y₀ − J₀Y₁ = 2/(πx)
  * gauss_cubature   —— 3 点 × 3 点で [0,1]×[0,2] の x⁵y⁵ を厳密に(= 16/9)、x⁶ では誤差が出る、3-D の箱の体積
  * nurbs_surface    —— 重み (1, √2/2, 1) の 2 次 NURBS を z へ押し出す: どの点も半径 1 の円柱の上(有理だから厳密)
  * n_sources_mdl    —— 8 素子の等間隔アレイに角度の違う 2 波源 + 白色雑音(seed 固定)で 2、雑音だけで 0
  * tf_bilinear      —— 1 次の低域 ω_c/(s + ω_c): Tustin の閉形式の係数、前歪みで ω_c の利得がちょうど 1/√2、
                        scipy.signal.bilinear(別実装)と一致
  * wavelet_filters  —— Haar = (1, 1)/√2、db2 = (1+√3, 3+√3, 3−√3, 1−√3)/(4√2)、db4 の偶数シフトの直交性と消失モーメント 4

    py -3.11 examples/gallery_math_numerics_filters.py
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import mathgeometry as MG  # noqa: E402
import mathnumerics as MN  # noqa: E402
import mathspectral as MS  # noqa: E402
import mathtransforms as MT  # noqa: E402

ROWS: list = []


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def demo_bessel() -> None:
    x = np.linspace(0.3, 12.0, 40)
    pairs = [("j", np.sqrt(2 / (math.pi * x)) * np.sin(x), "√(2/πx) sin x"),
             ("i", np.sqrt(2 / (math.pi * x)) * np.sinh(x), "√(2/πx) sinh x"),
             ("k", np.sqrt(math.pi / (2 * x)) * np.exp(-x), "√(π/2x) e^{−x}")]
    for kind, want, txt in pairs:
        got = MN.bessel(x, 0.5, kind)
        rel = float(np.max(np.abs(got - want) / np.abs(want)))
        check("bessel", f"kind = {kind!r}、次数 1/2、x ∈ [0.3, 12]", txt, f"相対差 最大 {rel:.1e}", rel < 1e-12)
    z = MN.bessel([2.404825557695773], 0, "j")[0]
    check("bessel", "J₀ の最初の零点", "J₀(2.404825557695773) = 0", f"{z:.1e}", abs(z) < 1e-15)
    w = MN.bessel(x, 1, "j") * MN.bessel(x, 0, "y") - MN.bessel(x, 0, "j") * MN.bessel(x, 1, "y")
    rel = float(np.max(np.abs(w * math.pi * x / 2 - 1)))
    check("bessel", "Wronskian J₁Y₀ − J₀Y₁", "2/(πx)", f"相対差 最大 {rel:.1e}", rel < 1e-12)


def demo_cubature() -> None:
    c = MN.gauss_cubature(3, 2, a=[0.0, 0.0], b=[1.0, 2.0])
    X, W = c["nodes"], c["weights"]
    i55 = float(W @ (X[:, 0] ** 5 * X[:, 1] ** 5))
    check("gauss_cubature", "3×3 点、[0,1]×[0,2] の x⁵y⁵(各軸 2n − 1 = 5 次)", "(1/6)(2⁶/6) = 16/9", f"{i55:.15f}",
          abs(i55 - 16 / 9) < 1e-13 and c["exact_degree_per_axis"] == 5)
    i6 = float(W @ X[:, 0] ** 6)
    check("gauss_cubature", "同じ節点で x⁶(6 次 = 2n)", "∫ = 2/7 から外れる(厳密は 5 次まで)", f"{i6:.10f}(差 {i6 - 2 / 7:+.2e})",
          abs(i6 - 2 / 7) > 1e-6)
    c3 = MN.gauss_cubature(2, 3, a=-1.0, b=[1.0, 2.0, 3.0])
    check("gauss_cubature", "2³ 点、箱 [−1,1]×[−1,2]×[−1,3] の体積", "2·3·4 = 24", f"{c3['weights'].sum():.14f}、節点 {len(c3['nodes'])}",
          abs(c3["weights"].sum() - 24) < 1e-12 and len(c3["nodes"]) == 8)


def demo_nurbs() -> None:
    ring = np.array([[1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    net = np.zeros((3, 2, 3))
    for j, zz in enumerate((0.0, 2.0)):
        net[:, j, :2] = ring
        net[:, j, 2] = zz
    w = np.array([[1.0, 1.0], [math.sqrt(0.5), math.sqrt(0.5)], [1.0, 1.0]])
    s = MG.nurbs_surface(net, w, degree=(2, 1), n=(33, 5))
    P = s["points"]
    rad = np.hypot(P[..., 0], P[..., 1])
    check("nurbs_surface", "重み (1, √2/2, 1) の 2 次 × 1 次(円柱の 1/4)", "全点で x² + y² = 1(< 1e-14)",
          f"|r − 1| 最大 {np.abs(rad - 1).max():.1e}", np.abs(rad - 1).max() < 1e-14)
    check("nurbs_surface", "高さの向き(1 次)", "z = 0, 0.5, …, 2 の等間隔", str(np.round(P[0, :, 2], 12).tolist()),
          np.allclose(P[0, :, 2], np.linspace(0, 2, 5), atol=1e-14))
    ends = (P[0, 0, :2], P[-1, 0, :2])
    V, F = s["mesh"]
    check("nurbs_surface", "端点と三角形メッシュ", "端 (1,0)・(0,1)、頂点 33·5、三角形 2·32·4",
          f"{np.round(ends[0], 14).tolist()}、{np.round(ends[1], 14).tolist()}、{len(V)}、{len(F)}",
          np.allclose(ends[0], [1, 0]) and np.allclose(ends[1], [0, 1]) and len(V) == 165 and len(F) == 256)


def _snapshots(M, K, angles_deg, snr_db, rng):
    m = np.arange(M)[:, None]
    X = np.zeros((M, K), complex)
    for a in angles_deg:
        steer = np.exp(1j * math.pi * m * math.sin(math.radians(a)))
        s = (rng.standard_normal(K) + 1j * rng.standard_normal(K)) / math.sqrt(2)
        X += steer * s[None, :]
    sig_n = 10 ** (-snr_db / 20)
    X += sig_n * (rng.standard_normal((M, K)) + 1j * rng.standard_normal((M, K))) / math.sqrt(2)
    return X


def demo_mdl() -> None:
    rng = np.random.default_rng(20261012)
    r2 = MS.n_sources_mdl(_snapshots(8, 400, [-20.0, 25.0], 10.0, rng))
    check("n_sources_mdl", "8 素子、−20° と 25° の 2 波源、SNR 10 dB、400 スナップショット", "2",
          f"{r2['n_sources']}(固有値 上 3 つ {np.round(r2['eigenvalues'][:3], 3).tolist()})", r2["n_sources"] == 2)
    r1 = MS.n_sources_mdl(_snapshots(8, 400, [10.0], 10.0, rng))
    check("n_sources_mdl", "同じ条件で 1 波源", "1", str(r1["n_sources"]), r1["n_sources"] == 1)
    r0 = MS.n_sources_mdl(_snapshots(8, 400, [], 0.0, rng))
    check("n_sources_mdl", "雑音だけ", "0", str(r0["n_sources"]), r0["n_sources"] == 0)


def demo_bilinear() -> None:
    fs, fc = 1000.0, 100.0
    wc = 2 * math.pi * fc
    r = MT.tf_bilinear([wc], [1.0, wc], fs)
    K = 2 * fs
    b_want = np.array([wc, wc]) / (K + wc)
    a_want = np.array([1.0, (wc - K) / (K + wc)])
    check("tf_bilinear", "ω_c/(s + ω_c)、f_c = 100 Hz、fs = 1 kHz(素の Tustin)", "b = ω_c(1, 1)/(K + ω_c)、a = (1, (ω_c − K)/(K + ω_c))",
          f"b {np.round(r['num_z'], 12).tolist()}、a {np.round(r['den_z'], 12).tolist()}",
          np.allclose(r["num_z"], b_want, atol=1e-15) and np.allclose(r["den_z"], a_want, atol=1e-15))
    try:
        from scipy import signal
        bz, az = signal.bilinear([wc], [1.0, wc], fs)
        d = max(float(np.abs(bz - r["num_z"]).max()), float(np.abs(az - r["den_z"]).max()))
        check("tf_bilinear", "同じ 1 次の系を scipy.signal.bilinear で(別実装)", "係数が一致(< 1e-14)",
              f"差 {d:.1e}", d < 1e-14)
        r2 = MT.tf_bilinear([1.0], [1.0, 0.5, 1.0], 10.0)
        b2, a2 = signal.bilinear([1.0], [1.0, 0.5, 1.0], 10.0)
        d2 = max(float(np.abs(b2 - r2["num_z"]).max()), float(np.abs(a2 - r2["den_z"]).max()))
        check("tf_bilinear", "2 次の系 1/(s² + 0.5s + 1)、fs = 10", "scipy.signal.bilinear と一致", f"差 {d2:.1e}", d2 < 1e-14)
    except ImportError:                                   # scipy は fullseye の必須依存だが念のため
        check("tf_bilinear", "scipy.signal.bilinear との照合", "scipy がある", "scipy が無い", False)
    rp = MT.tf_bilinear([wc], [1.0, wc], fs, prewarp_hz=fc)
    z = np.exp(1j * wc / fs)
    g = abs(np.polyval(rp["num_z"], z) / np.polyval(rp["den_z"], z))
    g0 = abs(np.polyval(r["num_z"], z) / np.polyval(r["den_z"], z))
    check("tf_bilinear", "前歪み f₀ = f_c で z = e^{jω_c/fs} の利得", f"連続系と同じ 1/√2 = {1 / math.sqrt(2):.12f}",
          f"{g:.12f}(前歪み無しは {g0:.6f})", abs(g - 1 / math.sqrt(2)) < 1e-13 and abs(g0 - 1 / math.sqrt(2)) > 1e-3)


def demo_wavelets() -> None:
    h1 = MT.wavelet_filters(1)
    check("wavelet_filters", "order = 1(Haar)", "(1, 1)/√2、g = (1, −1)/√2", f"{h1['lowpass'].tolist()}、{h1['highpass'].tolist()}",
          np.allclose(h1["lowpass"], [2 ** -0.5] * 2, atol=1e-15) and np.allclose(h1["highpass"], [2 ** -0.5, -(2 ** -0.5)], atol=1e-15))
    s3 = math.sqrt(3)
    want = np.array([1 + s3, 3 + s3, 3 - s3, 1 - s3]) / (4 * math.sqrt(2))
    h2 = MT.wavelet_filters(2)["lowpass"]
    check("wavelet_filters", "order = 2(db2)", "(1+√3, 3+√3, 3−√3, 1−√3)/(4√2)", f"差 {np.abs(h2 - want).max():.1e}",
          np.abs(h2 - want).max() < 1e-14)
    f4 = MT.wavelet_filters(4)
    h, g = f4["lowpass"], f4["highpass"]
    orth = max(abs(float(np.dot(h[2 * k:], h[:len(h) - 2 * k])) - (1.0 if k == 0 else 0.0)) for k in range(4))
    n = np.arange(len(g))
    mom = max(abs(float(np.sum(n ** k * g))) for k in range(4))
    check("wavelet_filters", "order = 4(長さ 8)", "Σ h[n]h[n+2k] = δ_k、Σ nᵏ g[n] = 0(k < 4)",
          f"直交の差 {orth:.1e}、モーメント最大 {mom:.1e}", len(h) == 8 and orth < 1e-12 and mom < 1e-9 and f4["vanishing_moments"] == 4)


def main() -> int:
    t0 = time.time()
    demo_bessel()
    demo_cubature()
    demo_nurbs()
    demo_mdl()
    demo_bilinear()
    demo_wavelets()
    w_op = max(len(r[0]) for r in ROWS)
    print(f"{'op':<{w_op}} | 確かめたこと | 期待 | 出た値 | 判定")
    for op, what, exp, got, ok in ROWS:
        print(f"{op:<{w_op}} | {what} | {exp} | {got} | {'合格' if ok else '★不合格'}")
    bad = [r for r in ROWS if not r[4]]
    if bad:
        print(f"FAIL: {len(bad)}/{len(ROWS)} 行が外れた({', '.join(sorted({r[0] for r in bad}))})")
        return 1
    print(f"PASS: {len({r[0] for r in ROWS})} op を {len(ROWS)} 行の真値で確認({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
