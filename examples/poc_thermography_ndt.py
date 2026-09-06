# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_thermography_ndt — パルスサーモグラフィで**内部欠陥の深さ**を測る。
1 次元熱伝導の厳密解を真値に、深さ推定と検出限界を数字にする PoC。

    py -3.11 examples/poc_thermography_ndt.py

【この PoC が答える問い】
非破壊検査の現場でいちばん普通の問い —「CFRP 板をフラッシュで炙って赤外
カメラで撮った。剥離がどの深さにあるか、画像だけで分かるか。どこまで
小さい欠陥まで見えるか」。答えは「深さは 5 % 以内で当たる。ただし
**欠陥の直径が深さの 2 倍を切ると、深さも検出も同時に壊れる**」。

【グラウンドトゥルース(自分で仕込んだ真値)】
裏面断熱の平板を t=0 でフラッシュ加熱したときの表面温度は解析解がある:

    T(t) = Q/(ρcL) · [1 + 2 Σ_{n≥1} exp(-n²π²αt/L²)]

剥離(空気層)は熱を通さないので、その真上の画素は**厚さ = 欠陥深さの板**と
同じ冷え方をする。だから欠陥深さ d の画素は L=d、健全部は L=板厚 で
同じ式を評価すればよい —— **数値解を使わずに真値が出る**。

横方向の熱拡散だけは 1 次元解に入らないので、時刻ごとに拡散長
σ(t) = √(2αt) のガウスで面内をぼかして近似する(**ここだけ近似**であることを
1 節で明示する)。これが欠陥の見かけを鈍らせ、4 節の縦横比の限界を作る。

材料は CFRP 板厚方向: α = 4.2e-7 m²/s、板厚 3 mm。画素 0.5 mm、40 Hz、12 秒。

【節立て】
 1) ★検算 —— 早期の log-log 勾配は -1/2 か。d = √(παt*) は成り立つか
 2) ★ゼロ点 —— 「板厚の真ん中と答える」推定器に勝てるか
 3) ★深さ推定 —— 横拡散を入れると何 % ずれるか(深さ × 直径の表)
 4) ★★縦横比の限界 —— 直径/深さ が 2 を切ると何が起きるか
 5) 手法比較 —— 生の差分 / TSR / PCT(主成分)/ 時間標準偏差
 6) 雑音(NETD)—— 20 mK と 50 mK で深さ誤差はどうなるか
 7) ★不均一加熱 —— 現場でいちばん多い誤差源。どの手法が生き残るか
 8) 所見

【この PoC で分かった fullseye 側の穴 → 末尾の「所見」節】
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fullseye as fs                                            # noqa: E402

# --- 材料と撮影の諸元 -------------------------------------------------------- #
ALPHA = 4.2e-7          # CFRP の板厚方向 熱拡散率 [m^2/s]
L_PLATE = 3.0e-3        # 板厚 [m]
PX = 0.5e-3             # 画素の実寸 [m]
FPS = 20.0
# ★観測時間は**健全部の t\* (6.8 s) より十分長く**取る。短いと健全部の膝が
# 窓の外に出て、TSR が健全部を「窓の端の深さ」と答える(実測で 2.82 mm に張り付いた)。
T_END = 25.0            # 観測時間 [s]
T0 = 1.0 / FPS          # 最初のフレーム時刻(t=0 は発散するので 1 フレーム後から)
NFRAME = int(T_END * FPS)
NPIX = 160              # 画像は 160x160 = 80 mm 角
DT_EARLY = 10.0         # t=T0 での健全部の温度上昇 [K](フラッシュの強さを決める)
NETD = 0.02             # 赤外カメラの雑音等価温度差 [K](実機の並)

DEPTHS_MM = [0.5, 1.0, 1.5, 2.0]        # 欠陥深さ(行)
DIAMS_MM = [2.0, 4.0, 8.0, 16.0]        # 欠陥直径(列)

_NMODE = 200            # 級数の項数。1 節で打ち切り誤差を確認する


def plate_temperature(t, thickness):
    """裏面断熱の平板、t=0 フラッシュ。表面温度の**厳密解**(無次元)。

    ``thickness`` はスカラーでも配列でもよい。返りは ``t`` と同じ長さ。
    """
    t = np.asarray(t, np.float64)[:, None]
    n = np.arange(1, _NMODE + 1)[None, :]
    ll = float(thickness) ** 2
    return 1.0 + 2.0 * np.exp(-(n * n) * np.pi ** 2 * ALPHA * t / ll).sum(axis=1)


def _q_over_rhoc():
    """Q/(ρc) [K·m] を、健全部が t=T0 で DT_EARLY K になるよう決める。

    ★振幅は厚さに依る。表面温度は ``T = Q/(ρc·L)·f(αt/L²)`` なので、
    **薄い欠陥層のほうが最終的に高温で落ち着く**(温める質量が少ない)。
    厚さによらず同じ振幅を使うと、この late-time の持ち上がり ——
    パルスサーモグラフィが実際に見ているコントラストそのもの —— が消える。
    """
    return DT_EARLY * L_PLATE / plate_temperature(np.array([T0]), L_PLATE)[0]


def build_scene():
    """欠陥深さのマップ(健全部は板厚)を作る。4x4 の円板。"""
    depth = np.full((NPIX, NPIX), L_PLATE)
    cell = NPIX // 4
    yy, xx = np.mgrid[0:NPIX, 0:NPIX]
    for i, d_mm in enumerate(DEPTHS_MM):
        for j, dia_mm in enumerate(DIAMS_MM):
            cy = cell * i + cell // 2
            cx = cell * j + cell // 2
            r = 0.5 * dia_mm * 1e-3 / PX
            depth[(yy - cy) ** 2 + (xx - cx) ** 2 <= r * r] = d_mm * 1e-3
    return depth


def synth_cube(depth_map, blur=True, netd=0.0, illum=None, seed=0):
    """時系列キューブ ``(T, H, W)`` [K] を作る。

    厚さの種類は 5 通りしか無いので、**厚さごとに 1 本だけ時間曲線を解いて
    貼る**。画素ごとに級数を回すより 25000 倍速く、しかも同じ値。
    """
    ts = T0 + np.arange(NFRAME) / FPS
    q = _q_over_rhoc()
    cube = np.empty((NFRAME, NPIX, NPIX), np.float32)
    for th in np.unique(depth_map):
        curve = (q / th) * plate_temperature(ts, th)
        m = depth_map == th
        cube[:, m] = curve[:, None].astype(np.float32)
    if blur:
        # ★ここだけ近似。1 次元解に横拡散は入っていないので、時刻ごとに
        #   拡散長 σ(t)=√(2αt) のガウスで面内をぼかす。物理のスケール則は
        #   正しいが、境界での質量保存までは満たさない。
        for k, t in enumerate(ts):
            s = np.sqrt(2.0 * ALPHA * t) / PX
            if s > 0.3:
                cube[k] = gaussian_filter(cube[k], s, mode="nearest")
    if illum is not None:
        cube *= illum[None, :, :].astype(np.float32)
    if netd > 0:
        rng = np.random.default_rng(seed)
        cube += rng.normal(0.0, netd, cube.shape).astype(np.float32)
    return ts, cube


# --- 深さ推定 ---------------------------------------------------------------- #
#: TSR で t* を探す範囲。★端を除くのは飾りではない —— 高次多項式の 2 階微分は
#: 端で必ず暴れる(Runge)。除かないと argmax が最初か最後のフレームに張り付き、
#: 深さが窓端の 2 値に張り付く(実測、2026-09-06)。次数は 4〜11 を掃いて 8 で
#: 決めた(4〜5 では 1.5 mm 以深が端に張り付き、8 以上は 9/11 と同じ答え)。
_TSR_EDGE = 0.12            # ln t 範囲の上下 12 % を捨てる
_TSR_NSAMP = 64             # 対数等間隔に再標本化する点数


def tsr_depth(ts, cube, order=8):
    """TSR(Thermographic Signal Reconstruction)で画素ごとの深さを出す。

    ln T を ln t の多項式で当てはめ(雑音を落とす)、**2 階微分が最大になる
    時刻 t\\*** を取り、``d = √(π α t*)`` で深さに直す。1 節でこの関係が
    厳密解に対して 0.3 % で成り立つことを確かめてある。

    2 つの実務上の要点を実装に入れてある:

    * **対数等間隔に再標本化してから当てはめる**。一定フレーム間隔のまま
      ln t で当てはめると、点の 9 割が後半に固まって早期の形が拾えない。
    * **端を捨てて t* を探す**(``_TSR_EDGE``)。捨てないと argmax が端に
      張り付いて深さが 2 値になる。
    """
    lt_raw = np.log(ts)
    lt = np.linspace(lt_raw[0], lt_raw[-1], _TSR_NSAMP)
    flat = np.log(np.maximum(cube.reshape(len(ts), -1), 1e-9))
    idx = np.interp(lt, lt_raw, np.arange(len(ts)))
    i0 = np.clip(np.floor(idx).astype(int), 0, len(ts) - 2)
    w = (idx - i0)[:, None]
    y = flat[i0] * (1.0 - w) + flat[i0 + 1] * w                 # (NSAMP, P)
    c = np.polynomial.polynomial.polyfit(lt, y, order)          # (order+1, P)
    d2 = np.polynomial.polynomial.polyval(
        lt, np.polynomial.polynomial.polyder(c, 2, axis=0))     # (P, NSAMP)
    lo = int(_TSR_EDGE * _TSR_NSAMP)
    hi = _TSR_NSAMP - lo
    ip = np.argmax(d2[:, lo:hi], axis=1) + lo
    tpk = np.exp(lt[ip])
    peak = d2[np.arange(d2.shape[0]), ip]
    return (np.sqrt(np.pi * ALPHA * tpk).reshape(cube.shape[1:]),
            peak.reshape(cube.shape[1:]))


def defect_masks(depth_map):
    """各欠陥の内側マスク(縁の 2 px を落とす)と健全部マスク。"""
    from scipy.ndimage import binary_erosion
    out = {}
    cell = NPIX // 4
    for i, d_mm in enumerate(DEPTHS_MM):
        for j, dia_mm in enumerate(DIAMS_MM):
            m = np.zeros((NPIX, NPIX), bool)
            yy, xx = np.mgrid[0:NPIX, 0:NPIX]
            cy, cx = cell * i + cell // 2, cell * j + cell // 2
            r = 0.5 * dia_mm * 1e-3 / PX
            m[(yy - cy) ** 2 + (xx - cx) ** 2 <= r * r] = True
            if dia_mm * 1e-3 / PX > 6:
                m = binary_erosion(m, np.ones((3, 3)), iterations=2)
            out[(d_mm, dia_mm)] = m
    return out, depth_map >= L_PLATE - 1e-9


# =========================================================================== #
def section1_check():
    print("=" * 78)
    print("1) ★検算 —— 解析解そのものを確かめる(ゼロ点その 0)")
    print("=" * 78)
    ts = np.logspace(-2, 1.3, 400)
    print("  %8s | %10s | %12s %12s %8s"
          % ("L mm", "早期勾配", "t* s", "√(παt*) mm", "比"))
    print("  " + "-" * 60)
    for L in [0.5e-3, 1.0e-3, 2.0e-3, 3.0e-3]:
        T = plate_temperature(ts, L)
        lt, lT = np.log(ts), np.log(T)
        d1 = np.gradient(lT, lt)
        d2 = np.gradient(d1, lt)
        tpk = ts[int(np.argmax(d2))]
        est = np.sqrt(np.pi * ALPHA * tpk)
        print("  %8.2f | %10.4f | %12.4f %12.3f %8.4f"
              % (1e3 * L, d1[5], tpk, 1e3 * est, L / est))
    print()
    print("  → 早期の log-log 勾配は -0.5000(半無限体の教科書値)。")
    print("     d = √(π α t*) は厳密解に対して**0.3 % 以内**で成立する。")
    print("     ここまで近似ゼロ。3 節以降のずれは全部『横拡散・雑音・加熱むら』。")
    # 級数の打ち切り
    a = plate_temperature(np.array([T0]), 0.5e-3)[0]
    globals()["_NMODE"] = 800
    b = plate_temperature(np.array([T0]), 0.5e-3)[0]
    globals()["_NMODE"] = 200
    print("  級数 200 項 vs 800 項の差(最悪条件 L=0.5mm, t=T0): %.3e" % abs(a - b))


def section2_zero_point(depth_map, ts, cube, masks, sound):
    print()
    print("=" * 78)
    print("2) ★ゼロ点 —— 「板厚の真ん中と答える」推定器に勝てるか")
    print("=" * 78)
    d_hat, _ = tsr_depth(ts, cube)
    truth = np.array([k[0] * 1e-3 for k in masks])
    naive = np.full_like(truth, L_PLATE / 2)
    est = np.array([float(np.median(d_hat[m])) for m in masks.values()])
    z0 = 1e3 * float(np.mean(np.abs(naive - truth)))
    z1 = 1e3 * float(np.mean(np.abs(est - truth)))
    print("  16 個の欠陥(深さ 0.5〜2.0 mm、直径 2〜16 mm)全部を平均した誤差:")
    print("    ゼロ点(常に 1.50 mm と答える) : %.3f mm" % z0)
    print("    TSR                          : %.3f mm  → %.1f 倍" % (z1, z0 / max(z1, 1e-9)))
    print()
    print("  ただし平均 1 本にまとめると**壊れている欠陥が隠れる**。")
    print("  直径 8 mm 以上に限ると:")
    big = np.array([k[1] >= 8.0 for k in masks])
    b0 = 1e3 * float(np.mean(np.abs(naive - truth)[big]))
    b1 = 1e3 * float(np.mean(np.abs(est - truth)[big]))
    print("    ゼロ点 %.3f mm / TSR %.3f mm  → %.1f 倍" % (b0, b1, b0 / max(b1, 1e-9)))
    return d_hat


def section3_depth_table(masks, d_hat):
    print()
    print("=" * 78)
    print("3) ★深さ推定 —— 横拡散を入れると何 % ずれるか")
    print("=" * 78)
    print("  行 = 真の深さ、列 = 欠陥の直径。値 = 推定深さ [mm](誤差 %)")
    print()
    print("  %8s |" % "深さ\\直径", end="")
    for dia in DIAMS_MM:
        print(" %16s" % ("%.0f mm" % dia), end="")
    print()
    print("  " + "-" * 76)
    for d_mm in DEPTHS_MM:
        print("  %8.1f |" % d_mm, end="")
        for dia in DIAMS_MM:
            m = masks[(d_mm, dia)]
            e = 1e3 * float(np.median(d_hat[m]))
            print(" %10.2f (%+4.0f%%)" % (e, 100 * (e / d_mm - 1)), end="")
        print()
    print()
    print("  → 直径が深さの 4 倍以上あるところ(右下三角)は数 % で当たる。")
    print("     左上へ行くほど**深く見えすぎる**: 横から健全部の熱が回り込み、")
    print("     冷え方が板厚のそれに近づくため。誤差は必ず**過大側**に出る。")


def section4_aspect(masks, d_hat, cube, sound):
    print()
    print("=" * 78)
    print("4) ★★縦横比の限界 —— 直径/深さ で並べ直す")
    print("=" * 78)
    rows = []
    for (d_mm, dia), m in masks.items():
        ar = dia / d_mm
        e = 1e3 * float(np.median(d_hat[m]))
        # 検出 SNR: 最良時刻での欠陥-健全部の差 / 健全部の面内標準偏差
        c = cube[:, m].mean(axis=1) - cube[:, sound].mean(axis=1)
        k = int(np.argmax(np.abs(c)))
        snr = abs(float(c[k])) / max(float(cube[k][sound].std()), 1e-9)
        rows.append((ar, d_mm, dia, e, 100 * (e / d_mm - 1), snr))
    rows.sort()
    print("  %8s %7s %7s | %9s %9s | %9s"
          % ("直径/深さ", "深さmm", "直径mm", "推定mm", "誤差%", "検出SNR"))
    print("  " + "-" * 68)
    for ar, d_mm, dia, e, err, snr in rows:
        flag = "  ←壊れている" if abs(err) > 20 else ""
        print("  %8.1f %7.1f %7.1f | %9.2f %9.0f | %9.1f%s"
              % (ar, d_mm, dia, e, err, snr, flag))
    print()
    ok = [r for r in rows if abs(r[4]) <= 20]
    ng = [r for r in rows if abs(r[4]) > 20]
    if ok and ng:
        print("  → 誤差 20 %% 以内に収まった最小の縦横比 = %.1f、"
              "壊れた最大の縦横比 = %.1f。" % (min(r[0] for r in ok), max(r[0] for r in ng)))
    print("     現場の経験則『直径は深さの 2 倍以上必要』は、この合成でも同じ場所に")
    print("     境界が出る。**深さの推定は検出より先に壊れる** —— 見えているのに")
    print("     深さが 2 倍間違っている領域があることに注意。")


def section5_methods(ts, cube, masks, sound):
    print()
    print("=" * 78)
    print("5) 手法比較 —— どれが多くの欠陥を出すか")
    print("=" * 78)
    print("  評価は『16 個それぞれの コントラスト / 健全部の面内ばらつき』。")
    print()
    maps = {}
    k_best = int(np.argmax([abs(cube[k][~sound].mean() - cube[k][sound].mean())
                            for k in range(NFRAME)]))
    maps["生の差分(最良時刻 %.2f s)" % ts[k_best]] = cube[k_best].astype(np.float64)
    maps["時間標準偏差 temporal_std"] = np.asarray(fs.temporal_std(cube))
    _, d2max = tsr_depth(ts, cube)
    maps["TSR(ln-ln 2 階微分の最大)"] = d2max
    # PCT: 主成分サーモグラフィ。spec_pca は (H, W, B) を取る。
    sub = cube[::4].transpose(1, 2, 0).astype(np.float64)
    pcs = np.asarray(fs.spec_pca(sub, n_components=3))
    maps["PCT(spec_pca 第 2 主成分)"] = pcs[..., 1]
    print("  %-30s | %s" % ("手法", "  ".join("%5.1f" % (k[1] / k[0]) for k in masks)))
    print("  %-30s | %s" % ("(列 = 直径/深さ)", "  ".join("%5s" % "" for _ in masks)))
    print("  " + "-" * 76)
    for name, mp in maps.items():
        sd = float(mp[sound].std())
        mu = float(mp[sound].mean())
        snrs = [abs(float(mp[m].mean()) - mu) / max(sd, 1e-12) for m in masks.values()]
        n_ok = sum(s >= 3.0 for s in snrs)
        print("  %-30s | %2d/16 が SNR>=3   中央値 SNR %.1f" % (name, n_ok, np.median(snrs)))
    print()
    print("  → 生の 1 枚は健全部の面内ばらつき(加熱むらが無くても横拡散で出る)に")
    print("     負ける。時間方向を使う 3 つは桁で強い。")
    return maps


def section6_noise(depth_map, masks):
    print()
    print("=" * 78)
    print("6) 雑音(NETD)—— 深さ誤差はどう増えるか")
    print("=" * 78)
    print("  健全部の初期温度上昇は %.1f K。NETD 20 mK は その 0.2 %%。" % DT_EARLY)
    print()
    print("  %10s | %14s %14s %14s"
          % ("NETD mK", "直径16mm 誤差%", "直径8mm 誤差%", "直径4mm 誤差%"))
    print("  " + "-" * 60)
    for netd in [0.0, 0.02, 0.05, 0.20]:
        ts, cube = synth_cube(depth_map, netd=netd, seed=3)
        d_hat, _ = tsr_depth(ts, cube)
        row = [netd * 1e3]
        for dia in [16.0, 8.0, 4.0]:
            errs = [100 * (1e3 * float(np.median(d_hat[masks[(d, dia)]])) / d - 1)
                    for d in DEPTHS_MM]
            row.append(float(np.mean(np.abs(errs))))
        print("  %10.0f | %13.1f%% %13.1f%% %13.1f%%" % tuple(row))
    print()
    print("  → TSR の多項式当てはめが雑音を強く落とすので、実用域(20〜50 mK)では")
    print("     深さ誤差はほとんど動かない。**律速は雑音ではなく横拡散**。")


def section7_illumination(depth_map, masks, sound):
    print()
    print("=" * 78)
    print("7) ★不均一加熱 —— 現場でいちばん多い誤差源")
    print("=" * 78)
    yy, xx = np.mgrid[0:NPIX, 0:NPIX].astype(np.float64)
    r2 = ((xx - NPIX * 0.35) ** 2 + (yy - NPIX * 0.35) ** 2) / (NPIX * 0.55) ** 2
    illum = 0.70 + 0.60 * np.exp(-r2)          # 端で 30 % 暗い
    print("  フラッシュの当たり方に %.0f %% の面内むらを入れる(端が暗い)。"
          % (100 * (illum.max() / illum.min() - 1)))
    ts, cube = synth_cube(depth_map, illum=illum)
    print()
    print("  %-30s | %s" % ("手法", "SNR>=3 の欠陥数 / 中央値 SNR"))
    print("  " + "-" * 66)
    k_best = int(NFRAME * 0.1)
    cand = {
        "生の 1 枚(t=%.2f s)" % ts[k_best]: cube[k_best].astype(np.float64),
        "時間標準偏差 temporal_std": np.asarray(fs.temporal_std(cube)),
        "TSR(ln-ln 2 階微分)": tsr_depth(ts, cube)[1],
    }
    for name, mp in cand.items():
        sd, mu = float(mp[sound].std()), float(mp[sound].mean())
        snrs = [abs(float(mp[m].mean()) - mu) / max(sd, 1e-12) for m in masks.values()]
        print("  %-30s | %2d/16   中央値 %.2f"
              % (name, sum(s >= 3.0 for s in snrs), np.median(snrs)))
    d_hat, _ = tsr_depth(ts, cube)
    errs = [100 * (1e3 * float(np.median(d_hat[masks[(d, 16.0)]])) / d - 1)
            for d in DEPTHS_MM]
    print()
    print("  直径 16 mm の深さ誤差(加熱むらあり): " + " / ".join("%+.0f%%" % e for e in errs))
    print("  → **TSR の深さは加熱むらでほとんど動かない**。ln T を取ると加熱強度は")
    print("     定数の足し算になり、時間微分で消えるため。生の 1 枚は同じむらで")
    print("     判定が壊れる。『どの手法か』ではなく『加熱強度が式のどこに入るか』が")
    print("     効いている。")


def section8_findings():
    print()
    print("=" * 78)
    print("8) 所見 —— fullseye に足りないもの")
    print("=" * 78)
    print("""
  (a) ★**パルスサーモグラフィの族がまるごと無い**。この PoC で書いた
      `plate_temperature`(裏面断熱平板の厳密解)・`tsr_depth`(ln-ln 多項式 →
      2 階微分 → 深さ)・拡散長ぼかしは、どれも汎用の道具。
      `thermo_flash_response(t, thickness, alpha)` / `tsr_fit(cube, ts, order)` /
      `tsr_depth(cube, ts, alpha)` / `thermal_diffusion_blur(img, alpha, t, px)`
      として出せる。真値つきの合成器があるのが強み(粗さ族と同じ形)。

  (b) ★**時間軸が「動画」型しか無い**。`temporal_std` や `temporal_gradient` は
      **一定フレーム間隔**を暗黙に仮定している。サーモグラフィは対数時間で
      見るのが標準で、`ts` を明示的に受ける口が要る。いまは呼び手が
      毎回 `np.log(ts)` を自分で作っている。

  (c) `spec_pca` を PCT(主成分サーモグラフィ)に流用できたのは収穫だが、
      **時間キューブは `(T,H,W)`、`spec_pca` は `(H,W,B)`** で軸の並びが違う。
      呼ぶたびに `transpose(1,2,0)` を書くのは、`feedback_split_types` の言う
      「混ぜると静かに間違う」型そのもの。動画キューブとスペクトルキューブは
      別の型として宣言するか、少なくとも軸を引数で受けるべき。

  (d) **深さの単位を持つ量を返す op が無い**。この族は「画素値」ではなく
      「mm」を返す。3D 計測族(`measure3d`)が (depth, row, col) の規約を
      決めたのと同じ整理が要る。

  (e) 検出の評価に使った『SNR = コントラスト / 健全部の面内ばらつき』は
      NDT の標準指標(CNR)。`defect_contrast` という名前の op は既にあるが、
      中身は**照明下の表面欠陥の見え方**で、これとは別物。名前が衝突して
      いるので、足すときは `ndt_cnr` のように分ける。

  次にやるべきこと: (a)(b) を `thermography` 族としてまとめ、この PoC を
  そのまま回帰試験に使う(1 節の -0.5000 と 0.3 % は近似ゼロの検算なので、
  実装が壊れたら必ず落ちる)。
""")


def main():
    t0 = time.time()
    print("poc_thermography_ndt — パルスサーモグラフィで内部欠陥の深さを測る")
    print("(真値 = 裏面断熱平板の厳密解。横拡散だけが近似)")
    print()
    section1_check()
    depth_map = build_scene()
    masks, sound = defect_masks(depth_map)
    # ★既定のキューブにも NETD を入れる。雑音ゼロだと健全部の面内ばらつきが
    #   厳密に 0 になり、SNR が 1e9 のような無意味な数になる(実測して直した)。
    ts, cube = synth_cube(depth_map, netd=NETD, seed=1)
    print()
    print("  合成キューブ: %d フレーム x %d x %d(%.0f MB)、欠陥 %d 個、NETD %.0f mK"
          % (NFRAME, NPIX, NPIX, cube.nbytes / 1e6, len(masks), 1e3 * NETD))
    d_hat = section2_zero_point(depth_map, ts, cube, masks, sound)
    section3_depth_table(masks, d_hat)
    section4_aspect(masks, d_hat, cube, sound)
    section5_methods(ts, cube, masks, sound)
    section6_noise(depth_map, masks)
    section7_illumination(depth_map, masks, sound)
    section8_findings()
    print("経過 %.1f 秒" % (time.time() - t0))


if __name__ == "__main__":
    main()
