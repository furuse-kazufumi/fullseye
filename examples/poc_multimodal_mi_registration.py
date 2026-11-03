# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_multimodal_mi_registration — 可視カメラと長波長赤外カメラの基板の像を、相互情報量で合わせる(真値つき)。

    py -3.11 examples/poc_multimodal_mi_registration.py

【この例が示すこと】
寸法表から描いた基板(基材・銅の配線・はんだのパッド・IC・チップ抵抗)を、可視の反射率と、赤外の
放射(放射率 ε・温度 T、``ε T⁴ + (1-ε) T_amb⁴``、帯域の積分は T⁴ で近似)で 2 通りに撮る。銅は可視で
明るく赤外で暗い(放射率 0.05〜0.1 = 周りを映すだけ)、IC は可視で暗く赤外で明るい(熱い・放射率 0.95)
—— **明るさの対応が単調でない**。赤外カメラは画素が粗く(ぼけ σ=1.5)、2 台のカメラの間には既知の
アフィン(回転 2.5 度・1.03 倍・画像の中心のずれ (6, -4) px・わずかな剪断)がある。

【グラウンドトゥルース(すべて assert で落とす)】
1. 真の位置で 2 枚の相関係数は負(-0.1 未満)—— 相関で合わせる手法の前提が崩れている。
2. ``register_mi``(正規化相互情報量)は真のアフィンを 4 隅誤差 < 0.3 px で取り戻す。
3. ★``register_ecc`` は相関の 2 次近似の分母が負になり**拒否する**か、誤差 > 2 px(黙って合ったふりをしない)。
4. ★``aoi.register_image``(位相相関の並進)は回転と倍率が入るので ``consistent=False``。
5. 初期のずれ(真値からの並進 2〜16 px、8 方向)ごとの MI の成功率(4 隅誤差 < 0.5 px)の表 ——
   どこまで外れて始めても戻るか。2 px では全部戻る。

【読み方】各節は「真値 / 推定 / 差」。PASS 行が出れば全部通っている。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aoi  # noqa: E402
import examplefig as figs  # noqa: E402
import featmatch as fm  # noqa: E402
import intensityreg as ir  # noqa: E402

T_AMB = 295.0          # 周囲の温度 [K]

#: 材料 → (可視の反射率, 赤外の放射率, 温度 [K])。放射率は公開の代表値の幅の中の値
#: (研磨した銅 0.03〜0.1、はんだ 0.05〜0.1、FR-4 / ソルダーレジスト 0.9 前後、IC の樹脂 0.9〜0.95)。
MATERIALS = {
    "substrate": (0.30, 0.90, 313.0),
    "copper": (0.80, 0.07, 318.0),
    "pad": (0.90, 0.06, 323.0),
    "ic": (0.07, 0.95, 352.0),
    "resistor": (0.20, 0.92, 333.0),
    "resistor_cap": (0.85, 0.08, 330.0),
}

#: 基板の寸法表 [px](1 px ≈ 0.1 mm)。(材料, x0, y0, x1, y1)
LAYOUT = [
    ("ic", 40, 40, 100, 100), ("ic", 150, 110, 190, 150),
    ("resistor", 130, 40, 150, 50), ("resistor", 130, 60, 150, 70), ("resistor", 60, 130, 80, 140),
    ("resistor", 200, 50, 210, 70),
]
TRACES = [  # (x0, y0, x1, y1, 幅)
    (100, 55, 130, 45, 3), (100, 75, 130, 65, 3), (70, 100, 70, 130, 4), (150, 45, 205, 55, 2),
    (170, 110, 170, 70, 3), (20, 20, 210, 20, 3), (20, 20, 20, 170, 3), (80, 135, 150, 135, 2),
]


def render_board(shape=(180, 230), ss=3):
    """寸法表から材料の地図を描き、可視と赤外の像にする(ss 倍で描いて面積平均)。"""
    h, w = shape
    yy, xx = np.mgrid[0:h * ss, 0:w * ss].astype(float)
    x, y = (xx + 0.5) / ss, (yy + 0.5) / ss
    mat = np.full(yy.shape, "substrate", dtype=object)
    for x0, y0, x1, y1, wd in TRACES:
        t = np.clip(((x - x0) * (x1 - x0) + (y - y0) * (y1 - y0)) / max((x1 - x0) ** 2 + (y1 - y0) ** 2, 1e-9), 0, 1)
        mat[np.hypot(x - (x0 + t * (x1 - x0)), y - (y0 + t * (y1 - y0))) <= wd / 2] = "copper"
    for name, x0, y0, x1, y1 in LAYOUT:
        inside = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
        mat[inside] = name
        if name == "ic":                                       # IC の足のパッド
            for k in range(6):
                py = y0 + (k + 0.5) * (y1 - y0) / 6
                for px in (x0 - 4, x1 + 4):
                    mat[(np.abs(x - px) <= 3) & (np.abs(y - py) <= 1.5)] = "pad"
        if name == "resistor":                                 # 両端の電極
            if x1 - x0 >= y1 - y0:
                mat[inside & ((x < x0 + 4) | (x > x1 - 4))] = "resistor_cap"
            else:
                mat[inside & ((y < y0 + 4) | (y > y1 - 4))] = "resistor_cap"
    vis = np.zeros(yy.shape)
    ir_ = np.zeros(yy.shape)
    for name, (rho, eps, T) in MATERIALS.items():
        sel = mat == name
        vis[sel] = rho
        ir_[sel] = eps * T ** 4 + (1 - eps) * T_AMB ** 4      # Stefan-Boltzmann(帯域の積分は T⁴ で近似)
    vis = vis.reshape(h, ss, w, ss).mean((1, 3))
    ir_ = ir_.reshape(h, ss, w, ss).mean((1, 3))
    rng = np.random.default_rng(1)
    vis = vis + 0.04 * ndimage.gaussian_filter(rng.normal(0, 1, vis.shape), 1.0)    # 基材の織り目
    return np.clip(vis, 0, 1), ir_


def main():
    vis_big, ir_big = render_board()
    # 赤外のカメラ: 既知のアフィンで見て(大きな絵から切り出して縁を作らない)、ぼけ・雑音
    th = math.radians(2.5)
    s = 1.03
    A = s * np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]]) @ np.array([[1, 0.01], [0, 1.0]])
    o = 25
    n_h, n_w = 130, 180
    c = np.array([(n_w - 1) / 2.0, (n_h - 1) / 2.0])
    W = np.eye(3)
    W[:2, :2] = A
    W[:2, 2] = c + np.array([6.0, -4.0]) - A @ c                 # fixed(可視)の (x, y) → moving(赤外)の (x, y)
    T = np.array([[1, 0, o], [0, 1, o], [0, 0, 1.0]])
    irw = ir.warp_parametric(ir_big, T @ W @ np.linalg.inv(T))
    lo, hi = ir_big.min(), ir_big.max()
    irw = ndimage.gaussian_filter((irw - lo) / (hi - lo), 1.5)
    irw = np.clip(irw + np.random.default_rng(2).normal(0, 0.01, irw.shape), 0, 1)
    fixed = vis_big[o:o + n_h, o:o + n_w]
    moving = irw[o:o + n_h, o:o + n_w]
    print("可視 %s / 赤外 %s px、真のアフィン(可視 → 赤外):" % (fixed.shape, moving.shape))
    print("   " + np.array2string(W[:2], precision=4, suppress_small=True).replace("\n", "\n   "))

    print("\n1. 真の位置での明るさの対応")
    back = ir.warp_parametric(moving, np.linalg.inv(W))           # 赤外を可視の格子へ戻す(真値で)
    inner = (slice(10, -10), slice(10, -10))
    r = float(np.corrcoef(fixed[inner].ravel(), back[inner].ravel())[0, 1])
    for name in ("copper", "ic", "substrate"):
        rho, eps, Tk = MATERIALS[name]
        print("   %-10s 可視 %.2f / 赤外の放射 %.3e(ε=%.2f, %.0f K)" % (name, rho, eps * Tk ** 4 + (1 - eps) * T_AMB ** 4,
                                                                  eps, Tk))
    print("   相関係数 %.4f(負 = 明るい所が暗く写る)" % r)
    assert r < -0.1

    print("\n2. register_mi(正規化相互情報量、アフィン)")
    rm = ir.register_mi(fixed, moving, model="affine")
    e_mi = fm.corner_error(rm["warp"], W, fixed.shape)
    print("   推定のアフィン:\n   " + np.array2string(rm["warp"][:2], precision=4, suppress_small=True).replace("\n", "\n   "))
    print("   4 隅誤差 %.4f px、NMI %.4f、評価回数 %d" % (e_mi, rm["nmi"], rm["iterations"]))
    assert e_mi < 0.3
    figs.save_grid("multimodal_mi_pair", [fixed, moving, rm["warped"]],
                   captions=["visible (reflectance)", "LWIR (eps T^4), affine + blur", "LWIR aligned by register_mi"],
                   gray=True, caption="NMI affine: corner error %.3f px; correlation at truth %.3f" % (e_mi, r))

    print("\n3. ★register_ecc(相関係数の最大化)では")
    try:
        re_ = ir.register_ecc(fixed, moving, motion="affine")
        e_ecc = fm.corner_error(re_["warp"], W, fixed.shape)
        print("   返った(相関 %.4f)が 4 隅誤差 %.2f px" % (re_["metric"], e_ecc))
        assert e_ecc > 2.0
    except ValueError as ex:
        print("   拒否: %s" % str(ex)[:150])

    print("\n4. ★aoi.register_image(位相相関、並進だけ)では")
    rp = aoi.register_image(fixed, moving)
    print("   (dy, dx) = (%.3f, %.3f) px、residual %.4f、consistent=%s" % (rp["dy"], rp["dx"], rp["residual"],
                                                                   rp["consistent"]))
    assert not rp["consistent"]

    print("\n5. 初期のずれごとの MI の成功率(真値から並進をずらして開始、8 方向、4 隅誤差 < 0.5 px で成功)")
    print("   %8s %8s %16s" % ("ずれ[px]", "成功率", "4 隅誤差の中央値"))
    rates = {}
    for d in (2, 4, 8, 16):
        errs = []
        for k in range(8):
            ang = 2 * math.pi * (k + 0.25) / 8
            W0 = W.copy()
            W0[:2, 2] += d * np.array([math.cos(ang), math.sin(ang)])
            try:
                errs.append(fm.corner_error(ir.register_mi(fixed, moving, warp_init=W0)["warp"], W, fixed.shape))
            except ValueError:
                errs.append(np.inf)
        errs = np.asarray(errs)
        rates[d] = float((errs < 0.5).mean())
        print("   %8d %8.3f %16.3f" % (d, rates[d], float(np.median(errs))))
    assert rates[2] == 1.0
    figs.save_table("multimodal_mi_capture", ["offset_px", "success_rate"],
                    [[str(d), "%.3f" % v] for d, v in rates.items()], title="MI capture", caption="register_mi: success rate per initial offset (8 directions)")

    for name, arr in (("fixed", fixed), ("moving", moving), ("warped", rm["warped"])):
        assert np.isfinite(arr).all() and float(np.ptp(arr)) > 0.0, name
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
