# -*- coding: utf-8 -*-
"""事例: 分布の距離・検定・行列の分解と関数を閉形式と往復で確かめる(数学の台帳 op ギャラリー: mathestimation / mathops)

平たく言うと:
  「2 つのヒストグラムはどれだけ違うか」「この差は偶然か」「行列を分けて掛け戻すと元に戻るか」を、
  答えが紙と鉛筆で分かる入力で 1 本ずつ呼ぶ。各行に「何を期待し、何が出て、合ったか」を印字し、外れたら exit 1。

確かめ方(op ごとの真値):
  * hist_distance      —— 正規分布 N(0,1) と N(1,1) を細かく離散化: KL = 1/2、Bhattacharyya = 1/8(閉形式)、
                          重ならない 2 つで JS = log 2・Hellinger = 1、χ² は手計算 1/3
  * mat_expm           —— 歪対称 3×3 の e^A = Rodrigues の回転行列、対角行列は対角の exp
  * mat_logm           —— log(e^X) = X の往復、30° の回転の対数 = 角 π/6 の歪対称、負の固有値は拒む
  * stat_chi2_gof      —— 度数 (10, 20, 30, 40) と一様: χ² = 20、自由度 3、p = erfc(√(x/2)) + √(2x/π) e^{−x/2}
  * stat_ks_test       —— 正規分位点 (i − ½)/n の標本は D = 1/(2n)、重ならない 3 対 3 は D = 1・p = 2/C(6,3)
  * stat_ttest_paired  —— 差 (1, 2, 3): t = 2√3、自由度 2、p = 1 − t/√(t² + 2)(自由度 2 の t 分布の閉形式)
  * mat_cholesky       —— L₀L₀ᵀ を分けると L₀ に戻る、log|A| = 2 Σ log L₀ᵢᵢ、正定値でなければ拒む
  * mat_eig            —— 回転の固有値 e^{±iθ}、推移行列の固有値 1 の固有ベクトル = 定常分布 (5/6, 1/6)
  * mat_lu             —— PA = LU で |L| ≤ 1、ピボット無しの古典的失敗 [[1e-20, 1], [1, 1]] で A[1,1] = 1 が消える

    py -3.11 examples/gallery_math_stats_linalg.py
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import mathestimation as ME  # noqa: E402
import mathops as M  # noqa: E402

ROWS: list = []


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def _raises(fn, *a, **k) -> bool:
    try:
        fn(*a, **k)
    except ValueError:
        return True
    return False


def _gauss(x, mu):
    return np.exp(-0.5 * (x - mu) ** 2) / math.sqrt(2 * math.pi)


def demo_distances() -> None:
    x = np.linspace(-12.0, 13.0, 20001)
    p, q = _gauss(x, 0.0), _gauss(x, 1.0)
    kl = ME.hist_distance(p, q, "kl")
    check("hist_distance", "KL(N(0,1) ‖ N(1,1))、2 万区分", "Δμ²/2 = 0.5", f"{kl:.10f}", abs(kl - 0.5) < 1e-8)
    bh = ME.hist_distance(p, q, "bhattacharyya")
    check("hist_distance", "Bhattacharyya(同じ 2 つ)", "Δμ²/8 = 0.125", f"{bh:.10f}", abs(bh - 0.125) < 1e-8)
    check("hist_distance", "KL(p ‖ p)", "0(等号は同一分布)", f"{ME.hist_distance(p, p, 'kl'):.1e}", ME.hist_distance(p, p, "kl") == 0.0)
    a, b = [1, 1, 0, 0], [0, 0, 1, 1]
    js, he = ME.hist_distance(a, b, "js"), ME.hist_distance(a, b, "hellinger")
    check("hist_distance", "重ならない 2 つ: JS / Hellinger", f"ln 2 = {math.log(2):.6f} / 1",
          f"{js:.12f} / {he:.12f}", abs(js - math.log(2)) < 1e-12 and abs(he - 1.0) < 1e-12)
    c2 = ME.hist_distance([1, 0], [1, 1], "chi2")
    check("hist_distance", "χ²: p = (1, 0)、q = (½, ½)", "½((¼)/(3/2) + (¼)/(½)) = 1/3", f"{c2:.15f}", abs(c2 - 1 / 3) < 1e-15)


def _skew(w):
    return np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]], float)


def demo_expm_logm() -> None:
    axis = np.array([1.0, 2.0, 2.0]) / 3.0
    th = 0.7
    K = _skew(axis)
    R_rod = np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K
    R = ME.mat_expm(th * K)
    err = float(np.abs(R - R_rod).max())
    check("mat_expm", "歪対称 θ[k]×(θ = 0.7、k = (1,2,2)/3)", "Rodrigues の I + sinθ K + (1 − cosθ) K²", f"差 {err:.1e}", err < 1e-14)
    D = ME.mat_expm(np.diag([0.5, -1.0, 2.0]))
    check("mat_expm", "対角 (0.5, −1, 2)", "対角 (e^0.5, e^−1, e^2)", np.array2string(np.diag(D), precision=6),
          np.allclose(D, np.diag(np.exp([0.5, -1.0, 2.0])), rtol=1e-14, atol=0))

    X = np.array([[0.1, 0.4, -0.2], [0.0, -0.3, 0.5], [0.2, 0.1, 0.2]])
    back = ME.mat_logm(ME.mat_expm(X))
    e2 = float(np.abs(back - X).max())
    check("mat_logm", "e^X の主対数で X に戻る往復(固有値の虚部は小さい)", "X に戻る(< 1e-12)", f"差 {e2:.1e}", e2 < 1e-12)
    c, s = math.cos(math.pi / 6), math.sin(math.pi / 6)
    L = ME.mat_logm(np.array([[c, -s], [s, c]]))
    check("mat_logm", "30° の回転", "[[0, −π/6], [π/6, 0]]", str(np.round(L + 0.0, 12).tolist()),
          np.allclose(L, [[0, -math.pi / 6], [math.pi / 6, 0]], atol=1e-13))
    check("mat_logm", "diag(−1, 2)(負の実固有値)", "ValueError(実の主対数が無い)",
          "拒んだ" if _raises(ME.mat_logm, np.diag([-1.0, 2.0])) else "通った", _raises(ME.mat_logm, np.diag([-1.0, 2.0])))


def demo_tests() -> None:
    r = ME.stat_chi2_gof([10, 20, 30, 40])
    x = 20.0
    p3 = math.erfc(math.sqrt(x / 2)) + math.sqrt(2 * x / math.pi) * math.exp(-x / 2)
    check("stat_chi2_gof", "度数 (10, 20, 30, 40) を一様と比べる", f"χ² = (225+25+25+225)/25 = 20、df 3、p = {p3:.6e}",
          f"{r['chi2']}、{r['df']}、{r['p']:.6e}", r["chi2"] == 20.0 and r["df"] == 3 and abs(r["p"] / p3 - 1) < 1e-10)
    r2 = ME.stat_chi2_gof([2, 3, 5], [1, 1, 2])
    check("stat_chi2_gof", "期待の比 1:1:2 を総数 10 に合わせる", "期待 (2.5, 2.5, 5)、χ² = 0.2、5 未満の区分 2",
          f"{r2['chi2']:.12f}、{r2['low_expected']}", abs(r2["chi2"] - 0.2) < 1e-12 and r2["low_expected"] == 2)

    from statistics import NormalDist
    n = 50
    xs = np.array([NormalDist().inv_cdf((i - 0.5) / n) for i in range(1, n + 1)])
    k = ME.stat_ks_test(xs)
    check("stat_ks_test", f"正規分位点 (i − ½)/{n} の標本と標準正規", f"D = 1/(2n) = {1 / (2 * n)}", f"{k['D']:.15f}", abs(k["D"] - 1 / (2 * n)) < 1e-12)
    k2 = ME.stat_ks_test([1, 2, 3], [4, 5, 6])
    check("stat_ks_test", "2 標本 (1,2,3) と (4,5,6)", "D = 1、厳密な p = 2/C(6,3) = 0.1", f"{k2['D']}、{k2['p']:.12f}",
          k2["D"] == 1.0 and abs(k2["p"] - 0.1) < 1e-12)

    t = ME.stat_ttest_paired([3, 5, 7], [2, 3, 4])
    tw = 2 * math.sqrt(3)
    pw = 1 - tw / math.sqrt(tw * tw + 2)
    check("stat_ttest_paired", "差 d = (1, 2, 3)", f"t = 2/(1/√3) = {tw:.12f}、df 2、p = {pw:.12f}",
          f"{t['t']:.12f}、{t['df']}、{t['p']:.12f}、平均差 {t['mean_diff']}",
          abs(t["t"] - tw) < 1e-12 and t["df"] == 2 and abs(t["p"] - pw) < 1e-12 and t["mean_diff"] == 2.0)
    check("stat_ttest_paired", "差がすべて 1(分散 0)", "ValueError", "拒んだ" if _raises(ME.stat_ttest_paired, [2, 3], [1, 2]) else "通った",
          _raises(ME.stat_ttest_paired, [2, 3], [1, 2]))


def demo_decomp() -> None:
    L0 = np.array([[2.0, 0, 0], [-1.0, 3.0, 0], [0.5, 1.5, 1.0]])
    ch = M.mat_cholesky(L0 @ L0.T)
    ld = 2 * math.log(2 * 3 * 1)
    check("mat_cholesky", "A = L₀L₀ᵀ(対角 2, 3, 1)", f"L = L₀、log|A| = 2 log 6 = {ld:.12f}",
          f"差 {np.abs(ch['L'] - L0).max():.1e}、{ch['log_det']:.12f}", np.allclose(ch["L"], L0, atol=1e-14) and abs(ch["log_det"] - ld) < 1e-13)
    check("mat_cholesky", "[[1, 2], [2, 1]](固有値 −1 を持つ)", "ValueError(正定値でない)",
          "拒んだ" if _raises(M.mat_cholesky, [[1.0, 2.0], [2.0, 1.0]]) else "通った", _raises(M.mat_cholesky, [[1.0, 2.0], [2.0, 1.0]]))

    th = 0.6
    e = M.mat_eig([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    want = np.array([np.exp(1j * th), np.exp(-1j * th)])
    check("mat_eig", "角 0.6 の 2-D 回転", "e^{±0.6i}(|w| = 1、虚部の降順)", np.array2string(e["w"], precision=10),
          np.allclose(e["w"], want, atol=1e-15) and e["residual"] < 1e-15)
    P = np.array([[0.9, 0.1], [0.5, 0.5]])
    e2 = M.mat_eig(P.T)
    v = np.real(e2["V"][:, 0])
    v = v / v.sum()
    check("mat_eig", "推移行列 [[0.9, 0.1], [0.5, 0.5]] の転置", "固有値 (1, 0.4)、固有値 1 の向き = (5/6, 1/6)",
          f"{np.round(e2['w'].real, 14).tolist()}、{np.round(v, 14).tolist()}",
          np.allclose(e2["w"], [1.0, 0.4], atol=1e-15) and np.allclose(v, [5 / 6, 1 / 6], atol=1e-15))

    A = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 10.0]])
    lu = M.mat_lu(A)
    ok = (np.allclose(lu["P"] @ A, lu["L"] @ lu["U"], atol=1e-14) and np.abs(lu["L"]).max() <= 1.0
          and np.allclose(np.triu(lu["U"]), lu["U"]) and np.allclose(np.diag(lu["L"]), 1.0)
          and abs(abs(np.prod(np.diag(lu["U"]))) - 3.0) < 1e-12)
    check("mat_lu", "部分ピボット(A = [[1,2,3],[4,5,6],[7,8,10]]、|det| = 3)", "PA = LU、|L| ≤ 1、|Π U_ii| = 3",
          f"残差 {lu['residual']:.1e}、|Π U_ii| = {abs(np.prod(np.diag(lu['U']))):.12f}", ok)
    bad = M.mat_lu([[1e-20, 1.0], [1.0, 1.0]], pivoting="none")
    LU = bad["L"] @ bad["U"]
    check("mat_lu", "ピボット無しで [[1e-20, 1], [1, 1]]", "乗数 1e20・LU の (1,1) が 0(元の 1 が消える)",
          f"L[1,0] = {bad['L'][1, 0]:.0e}、(LU)[1,1] = {LU[1, 1]}、成長 {bad['growth']:.0e}",
          bad["L"][1, 0] == 1e20 and LU[1, 1] == 0.0 and bad["residual"] == 1.0)
    good = M.mat_lu([[1e-20, 1.0], [1.0, 1.0]])
    check("mat_lu", "同じ行列を部分ピボットで", "行を入れ替え残差 0", f"残差 {good['residual']}", good["residual"] == 0.0)


def main() -> int:
    t0 = time.time()
    demo_distances()
    demo_expm_logm()
    demo_tests()
    demo_decomp()
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
