# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_robust_profile_filter — 深い傷が **平均線を凹ませる** のを、ロバストなガウス / スプラインは
どこまで防げるか。破綻点まで数える PoC。

    py -3.11 examples/poc_robust_profile_filter.py          # 図は out/figures/ に出る
    CI=1 py -3.11 examples/poc_robust_profile_filter.py     # 短い版(試行回数を減らす)

【問い】
粗さ計測では、断面からガウスフィルタでうねり(平均線)を引いて粗さを残す。ところが深い傷が
1 本あると、平均線がその傷に引かれて凹み、**傷の両側の健全な面が「山」に化ける**。傷そのものは
深さの数割しか出ず、傷の周りに偽の粗さが立つ。ロバスト版(重みを下げる反復)はこれを防ぐと
言われるが、**どこまで** か。汚染が半数に近づけば破綻するはずで、その点を数字で見たい。

【外部の真値(op と独立に立てたもの)】
  1. ガウスの伝達関数 ``exp(-π (α λc / λ)²)``(α² = ln2/π)。λ = λc でちょうど 0.5。
  2. 離散スプラインの伝達関数 ``1 / (1 + (sin(π dx/λ) / sin(π dx/λc))⁴)``(2 階差分の周波数応答から)。
  3. 合成した断面の **本当のうねり**(解析的な正弦の和)。これとの差が「引きずり量」。
  4. 密行列の第 2 実装(tests/test_roughness_robust.py)。反復の不動点が一致する。
  5. 既存の ``surface_filter``(ISO 16610-21 の別実装)。打ち切りを揃えると内部で一致する。

【新 op 3 本】``robust_gaussian_profile`` / ``robust_spline_profile`` / ``robust_gaussian_surface``
(``roughness`` 族、``prepare`` 区分)。式は論文のものを再実装した(文献は末尾)。

【節立て】
 1) 伝達関数 —— カットオフ波長で 0.5 か(既存の ``surface_filter`` は直す前 0.5095、2026-10-18 以降は 0.5000)
 2) 傷つき断面 —— 線形ガウスの平均線は凹み、ロバストは真のうねりに留まる
 3) ★破綻点 —— 汚染率を 0〜60 % に振って、ロバストが勝てなくなる所を探す
 4) 面 —— 傷の周りの「偽の山」(halo)を数える
 5) 探針と fail-closed —— 重みを 1 に固定すると門が落ちる / 収束しなければ拒否
 6) 所見

【出典】(式は論文のものから再実装した。論文の文・図・数値表は写していない。著者による再現の承認を
意味しない)
  * ISO 16610-21 / -22 / -31 / -32(ガウス・スプライン・ロバストの各フィルタ族。規格の本文は写していない)
  * 沼田・藤原・舟橋・輿水「高速 M 推定法を用いたロバストガウシアンフィルタの提案」, 精密工学会誌 76(2010)
  * 近藤・沼田・輿水, 精密工学会誌 79(7)(2013) / 外山ほか, 精密工学会誌 89(2)(2023)
  * Seewig, "Gaussian Regression Filters", in *Computational Surface and Roundness Metrology*, Springer (2009)
  * Krystek, "Form filtering by splines", Measurement 18 (1996) 9-15
  * Whittaker, Proc. Edinburgh Math. Soc. 41 (1923) / Eilers, "A perfect smoother", Anal. Chem. 75 (2003) 3631-3636
    (2 階差分の罰則つき平滑化)
  * Tukey の biweight: Mosteller & Tukey, *Data Analysis and Regression* (1977)
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import roughness as R                                            # noqa: E402

CI = bool(os.environ.get("CI"))
SEEDS = 3 if CI else 7
DX = 1.0                     # µm
LAMBDA_C = 80.0              # µm
NP = 2400                    # 断面の標本数
X = np.arange(NP) * DX
TRUE_AMP = 2.0               # 本当のうねりの振幅(µm)
TRUE_MEAN = TRUE_AMP * np.sin(2 * np.pi * X / 600.0 + 0.4)
INNER = slice(150, NP - 150)


def _alpha() -> float:
    """ISO のガウス定数。op の定数を読まず、ここで ln2/π から作り直す(両辺に同じ入力を渡さない)。"""
    return math.sqrt(math.log(2.0) / math.pi)


def gauss_closed(lam: float, lc: float = LAMBDA_C) -> float:
    return math.exp(-math.pi * (_alpha() * lc / lam) ** 2)


def spline_closed(lam: float, lc: float = LAMBDA_C, dx: float = DX) -> float:
    return 1.0 / (1.0 + (math.sin(math.pi * dx / lam) / math.sin(math.pi * dx / lc)) ** 4)


def amp_of(m: np.ndarray, lam: float, sl=slice(600, 1800)) -> float:
    """平均線に残った波長 λ の成分の振幅(正弦 + 余弦の最小二乗)。"""
    x = X[sl]
    basis = np.stack([np.sin(2 * np.pi * x / lam), np.cos(2 * np.pi * x / lam)], 1)
    coef, *_ = np.linalg.lstsq(basis, m[sl], rcond=None)
    return float(np.hypot(*coef))


def synth_profile(seed: int, frac: float = 0.0, kind: str = "spikes",
                  depth: float = 6.0, width: int = 8):
    """真のうねり + 雑音 σ=0.3 +(片側・下向きの)傷。傷の標本の位置も返す。"""
    rng = np.random.default_rng(seed)
    z = TRUE_MEAN + 0.3 * rng.standard_normal(NP)
    idx = np.zeros(NP, bool)
    if frac > 0.0:
        if kind == "spikes":
            idx = rng.random(NP) < frac
        else:
            while idx.sum() < int(frac * NP):
                s = int(rng.integers(0, NP - width))
                idx[s:s + width] = True
    z[idx] -= depth
    return z, idx


def drag(mean_line: np.ndarray) -> float:
    """引きずり量 = 平均線の、本当のうねりからの最大ずれ(端を除く)。"""
    return float(np.max(np.abs(mean_line - TRUE_MEAN)[INNER]))


def try_drag(fn, z):
    """反復が収束せず拒否されたら None(拒否は『壊れた値』より良い結果として数える)。"""
    try:
        return drag(fn(z)[1])
    except ValueError:
        return None


def lin_gauss(z):
    return R.robust_gaussian_profile(z, DX, LAMBDA_C, robust=False)


def rob_gauss(z):
    return R.robust_gaussian_profile(z, DX, LAMBDA_C)


def rob_spline(z):
    return R.robust_spline_profile(z, DX, LAMBDA_C)


def lin_spline(z):
    return R.robust_spline_profile(z, DX, LAMBDA_C, robust=False)


def main() -> bool:
    t_wall = time.perf_counter()
    t_cpu = time.process_time()
    print("poc_robust_profile_filter: 傷が平均線を凹ませる量と、ロバスト化の破綻点")
    print("  標本 %d 点 / dx=%g µm / λc=%g µm / 試行 %d 本%s" % (NP, DX, LAMBDA_C, SEEDS,
                                                         "(CI 短縮版)" if CI else ""))

    # ------------------------------------------------------------------ 1) 伝達関数
    print("\n[1] 伝達関数 —— 正弦波を通して平均線に残る振幅を測り、閉形式と比べる")
    lams = (30.0, 40.0, 60.0, 80.0, 120.0, 150.0, 240.0)
    rows = []
    for lam in lams:
        s = np.sin(2 * np.pi * X / lam)
        rows.append((lam, amp_of(lin_gauss(s)[1], lam), gauss_closed(lam),
                     amp_of(lin_spline(s)[1], lam), spline_closed(lam)))
    print("  %6s | %10s %10s | %10s %10s" % ("λ [µm]", "ガウス実測", "閉形式", "スプライン実測", "閉形式"))
    for lam, ag, cg, asp, cs in rows:
        print("  %6.0f | %10.6f %10.6f | %14.9f %10.6f" % (lam, ag, cg, asp, cs))
    err_g = max(abs(r[1] - r[2]) for r in rows)
    err_s = max(abs(r[3] - r[4]) for r in rows)
    # 既存の surface_filter(打ち切り ±0.75λc、2026-10-18 に ±λc/2 から広げた)がカットオフで何を返すか
    h = 160
    tile = np.tile(np.sin(2 * np.pi * X[:480] / LAMBDA_C), (h, 1))
    _, wav = R.surface_filter(tile, DX, lambda_c=LAMBDA_C, end_effect="reject")
    half_iso = float(np.abs(wav[wav.shape[0] // 2]).max())
    print("  カットオフ波長 λ=λc での振幅: 閉形式 0.5 / 新 op(ガウス)%.6f / スプライン %.9f / "
          "既存 surface_filter %.4f" % (rows[3][1], rows[3][3], half_iso))
    print("  → 既存の surface_filter も 4σ まで取るようになり 0.5 に %.1e で合う(直す前の 0.5095 は規格の文面の"
          "打ち切り ±λc/2 = 2.67σ の裾 0.8%% の欠け)。新 op は ±λc(5.3σ)で 0.5 に %.1e。"
          % (abs(half_iso - 0.5), abs(rows[3][1] - 0.5)))
    assert err_g < 1e-5, err_g
    assert err_s < 1e-9, err_s
    assert abs(half_iso - 0.5) < 1e-3, half_iso
    fine = np.geomspace(24.0, 480.0, 60)
    gx = fine
    figs.save_plot(
        "transfer_functions",
        [("ガウス(閉形式)", gx, np.array([gauss_closed(l) for l in gx])),
         ("スプライン(閉形式)", gx, np.array([spline_closed(l) for l in gx])),
         ("", np.array([r[0] for r in rows]), np.array([r[1] for r in rows])),
         ("", np.array([r[0] for r in rows]), np.array([r[3] for r in rows]))],
        xlabel="波長 λ [µm]  (λc = 80 µm)", ylabel="平均線への透過振幅",
        title="伝達関数: 線 = 閉形式、点 = 新 op の実測",
        caption="λ = λc = 80 µm でガウス・スプラインとも 0.5。点は閉形式の線の上に乗る"
                "(ガウス 1e-7、スプライン 1e-12 の差)。スプラインは遮断が鋭い。",
        kinds=["line", "line", "scatter", "scatter"],
        styles=["dashed", "dashed", None, None],
        colors=["reference", "emphasis", "reference", "emphasis"], size=(640, 400))

    # ------------------------------------------------------------------ 2) 傷つき断面
    zs, idx = synth_profile(1, 0.04, "scratches", depth=6.0, width=8)
    print("\n[2] 傷つき断面 —— 深さ 6 µm・幅 8 µm の溝を無作為に置く(傷の標本 %d 点 = %.1f%%)。雑音の σ は 0.3 µm"
          % (int(idx.sum()), 100.0 * idx.mean()))
    ml, mr, ms = lin_gauss(zs)[1], rob_gauss(zs)[1], rob_spline(zs)[1]
    d_l, d_r, d_s = drag(ml), drag(mr), drag(ms)
    z0, _ = synth_profile(1)
    d_clean = drag(rob_gauss(z0)[1])
    print("  引きずり量(真のうねりからの最大ずれ µm): 線形ガウス %.3f / ロバストガウス %.3f / "
          "ロバストスプライン %.3f   (傷なしのロバストガウスでも %.3f 残る)" % (d_l, d_r, d_s, d_clean))
    # 傷の脇(傷の標本を除く)の粗さ: 本当の粗さは σ=0.3 の雑音
    near = np.zeros(NP, bool)
    for i in np.flatnonzero(idx):
        near[max(0, i - 40):i + 40] = True
    near &= ~idx
    near[:150] = near[-150:] = False
    rms_l = float(np.sqrt(np.mean((zs - ml)[near] ** 2)))
    rms_r = float(np.sqrt(np.mean((zs - mr)[near] ** 2)))
    print("  傷の脇 ±40 µm(傷の標本は除く)の粗さ rms: 線形ガウス %.3f / ロバスト %.3f / 真値 0.300 µm"
          % (rms_l, rms_r))
    print("  → 線形は傷の脇の健全な面を粗さ %.1f 倍に見せる(偽の山)。ロバストは %.2f 倍。"
          % (rms_l / 0.3, rms_r / 0.3))
    assert d_r < 0.25 * d_l and d_s < 0.25 * d_l
    assert rms_l > 1.5 * rms_r
    sl = slice(750, 1350)
    figs.save_plot(
        "scratched_profile",
        [("傷つき断面", X[sl], zs[sl]),
         ("真のうねり", X[sl], TRUE_MEAN[sl]),
         ("線形ガウスの平均線", X[sl], ml[sl]),
         ("ロバストガウス", X[sl], mr[sl]),
         ("ロバストスプライン", X[sl], ms[sl])],
        xlabel="位置 x [µm]", ylabel="高さ [µm]",
        title="傷が線形の平均線を凹ませる(ロバストは真のうねりの上)",
        caption="細い線が傷つき断面。線形ガウスの平均線(赤)だけが傷のたびに凹み、"
                "ロバスト2本は真のうねり(破線)に重なる。",
        styles=[None, "dashed", None, None, None],
        colors=["neutral", "reference", "wrong", "right", "emphasis"], size=(720, 420))

    # ------------------------------------------------------------------ 3) 破綻点
    print("\n[3] 破綻点 —— 下向きの突起(深さ 6 µm)を標本の一定割合に混ぜ、%d 本の中央値を取る" % SEEDS)
    fracs = (0.0, 0.05, 0.10, 0.20, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60)
    table = {}
    print("  %6s | %10s %12s %14s | 拒否(収束せず)" % ("汚染率", "線形ガウス", "ロバストガウス", "ロバストスプライン"))
    for f in fracs:
        lin, rg, rs, refused = [], [], [], 0
        for sd in range(SEEDS):
            z, _ = synth_profile(100 + sd, f, "spikes")
            lin.append(drag(lin_gauss(z)[1]))
            for fn, bucket in ((rob_gauss, rg), (rob_spline, rs)):
                v = try_drag(fn, z)
                if v is None:
                    refused += 1
                else:
                    bucket.append(v)
        med = lambda a: float(np.median(a)) if a else float("nan")        # noqa: E731
        table[f] = (med(lin), med(rg), med(rs), refused)
        print("  %5.0f%% | %10.3f %12.3f %14.3f | %d" % (100 * f, *table[f]))
    assert table[0.20][1] < 0.25 * table[0.20][0] and table[0.20][2] < 0.25 * table[0.20][0]
    assert table[0.60][1] > 0.5 * table[0.60][0] and table[0.60][1] > TRUE_AMP * 0.5
    break_f = next((f for f in fracs if table[f][1] > 0.5 * table[f][0] and f > 0), None)
    print("  → ロバストガウスが線形の半分以下に抑えられなくなる最初の汚染率: %s"
          % ("%d%%" % round(100 * break_f) if break_f else "無し"))
    print("    理論上の破綻点は 50 %%(中央値)だが、線形解から反復を始めるので手前で崩れる。"
          "引きずりが真のうねりの振幅 %.1f µm を超えると『うねりを取り違えた』状態。" % TRUE_AMP)
    fx = np.array([100 * f for f in fracs])
    figs.save_plot(
        "breakdown_curve",
        [("線形ガウス", fx, np.array([table[f][0] for f in fracs])),
         ("ロバストガウス", fx, np.array([table[f][1] for f in fracs])),
         ("ロバストスプライン", fx, np.array([table[f][2] for f in fracs])),
         ("真のうねりの振幅", fx, np.full(fx.shape, TRUE_AMP))],
        xlabel="傷の標本の割合 [%]", ylabel="引きずり量 [µm]",
        title="破綻点: 20 % までは桁違いに強い、半数に近づくと線形と並ぶ",
        caption="線形の引きずりは汚染に比例して増える。ロバストは 30 % 付近まで雑音の床(0.1〜0.15 µm)に"
                "留まり、40 % を超えると破れる。破線 = 本当のうねりの振幅(これを超えると取り違え)。",
        styles=[None, None, None, "dotted"],
        colors=["wrong", "right", "emphasis", "reference"], size=(680, 420))

    # ------------------------------------------------------------------ 4) 面
    print("\n[4] 面 —— 傷 1 本(幅 4 µm・長さ 80 µm・深さ 6 µm)の周りの偽の山")
    n = 128
    lc = 16.0
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    wav2 = 1.0 * np.sin(2 * np.pi * xx / 150.0 + 0.3) + 0.6 * np.cos(2 * np.pi * yy / 130.0)
    rng_ = np.random.default_rng(3)
    rough2 = 0.1 * rng_.standard_normal((n, n))
    scratch = np.zeros((n, n))
    scratch[62:66, 24:104] = -6.0
    z2 = wav2 + rough2 + scratch
    rl, ml2, _ = R.robust_gaussian_surface(z2, DX, lc, robust=False)
    rr, mr2, info2 = R.robust_gaussian_surface(z2, DX, lc)
    band = np.zeros((n, n), bool)
    band[62 - 12:66 + 12, 24:104] = True
    band &= scratch == 0.0
    err_l = float(np.sqrt(np.mean((ml2 - wav2)[band] ** 2)))
    err_r = float(np.sqrt(np.mean((mr2 - wav2)[band] ** 2)))
    print("  傷の脇の帯(±12 µm)での平均面の誤差 rms: 線形 %.3f / ロバスト %.3f µm(反復 %d 回)"
          % (err_l, err_r, info2["iterations"]))
    assert err_r < 0.25 * err_l
    vr = (-1.2, 1.2)
    figs.save_grid(
        "scratched_surface",
        [z2 - z2.mean(), rl, rr, ml2 - mr2],
        captions=["入力(傷つきの面)", "線形ガウスの粗さ(傷の脇に偽の山)",
                  "ロバストの粗さ(傷だけが残る)", "平均面の差(線形 - ロバスト)"],
        title="面: 線形は傷の脇に偽の山を立てる、ロバストは傷だけを残す",
        ncols=2, signed=True, vrange=[(-3, 3), vr, vr, (-1.5, 1.5)],
        caption="橙 = 負、青 = 正。(b) の線形の粗さは、傷(橙)の脇に青い帯が立つ。平均面が傷の側へ凹んだぶんの"
                "偽の山で、傷そのものより広い。(c) のロバストは傷だけが残る。(d) が凹みの形そのもの。")

    # ------------------------------------------------------------------ 5) 探針と fail-closed
    print("\n[5] 探針と fail-closed")
    ratio_ok = table[0.20][1] / table[0.20][0]
    orig = R._biweight
    try:
        R._biweight = lambda r, cb: np.ones_like(r)
        z, _ = synth_profile(100, 0.20, "spikes")
        ratio_broken = drag(R.robust_gaussian_profile(z, DX, LAMBDA_C)[1]) / table[0.20][0]
    finally:
        R._biweight = orig
    print("  重み関数を 1 に固定: 20%% 汚染で ロバスト/線形 の引きずり比 %.2f → %.2f(門 < 0.25 が落ちる)"
          % (ratio_ok, ratio_broken))
    assert ratio_ok < 0.25 <= 0.5 < ratio_broken
    z, _ = synth_profile(100, 0.05, "spikes")
    try:
        R.robust_gaussian_profile(z, DX, LAMBDA_C, max_iter=1)
        raise AssertionError("max_iter=1 が通った(収束していないのに値を返した)")
    except ValueError as exc:
        print("  max_iter=1: 拒否 —— %s" % str(exc)[:70])
    for bad, kw in (("order=2", dict(order=2)), ("c=0", dict(c=0.0))):
        try:
            R.robust_gaussian_profile(z, DX, LAMBDA_C, **kw)
            raise AssertionError(bad + " が通った")
        except ValueError:
            print("  %s: 拒否" % bad)
    zw = z.copy()
    zw[1000:1300] -= 80.0
    try:
        R.robust_gaussian_profile(zw, DX, LAMBDA_C, truncate=0.5)
        raise AssertionError("窓より広い溝が通った")
    except ValueError:
        print("  窓(±λc/2)より広い溝: 外挿せず拒否")

    # ------------------------------------------------------------------ 6) 所見
    wall = time.perf_counter() - t_wall
    cpu = time.process_time() - t_cpu
    print("\n[6] 所見")
    print("  * 外れ値の無い断面でも、biweight は雑音の裾を刈るので線形とは一致しない"
          "(傷なしの引きずり: ロバスト %.3f µm / 線形 %.3f µm)。『外れ値が無ければ ISO と同じ』"
          "ではなく、『重み 1 なら同じ』が正しい(tests が既存 surface_filter と 1e-12 で一致を確認)。"
          % (d_clean, drag(lin_gauss(z0)[1])))
    print("  * 次数は 0/1 だけ。次数 2 は等価核が G(u)(3/2 - u²/2σ²) になり、λc で 85% 透過 —— "
          "カットオフの意味が変わるので拒否する。")
    print("  * 外部の真値は閉形式と合成した本当のうねり。実際のスタイラス断面での検証は未了。")
    print("  所要(CPU %.1f 秒 / 壁時計 %.1f 秒)" % (cpu, wall))
    assert cpu < 90.0, cpu
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("PASS: 伝達関数は閉形式に合い(ガウス %.0e / スプライン %.0e)、20%% 汚染で引きずりは線形の %.2f 倍、"
          "60%% では勝てない。" % (err_g, err_s, ratio_ok))
    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
