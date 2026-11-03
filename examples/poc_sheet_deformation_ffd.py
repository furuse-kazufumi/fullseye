# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_sheet_deformation_ffd — 印刷したシートの変形を B-spline FFD で推定し、真値で誤差の地図を作る。

    py -3.11 examples/poc_sheet_deformation_ffd.py

【この例が示すこと】
ラベル・フィルム・紙のようなシート状の対象は、下に異物を噛む・吸着が弱い・搬送で引っ張られると、
面内に**滑らかで局所的な**変形が出る。5 つの領域 —— 点の格子 / 文字の塊 / 格子縞のベタ /
**縦棒だけのバーコード** / **何も印刷していない余白** —— を持つシートに、既知の変形場(異物の膨らみ 2 か所 =
放射状の押し出し + 搬送方向の弱い引き伸ばし)を掛け、``register_ffd`` で推定する。真の場が分かっているので、
誤差を**画素ごと・領域ごと・成分ごと**に出し、どこで何が壊れるかを数で示す。

【グラウンドトゥルース(すべて assert で落とす)】
1. 模様が 2 方向にある 3 領域(点・文字・格子縞)で、FFD(格子 8 px)の終点誤差 EPE の平均 < 0.15 px。
2. 既存の ``demons_register`` も同じ真値・同じ向きで、同じ 3 領域の EPE の平均 < 0.3 px(場の向きの約束が揃っている)。
3. ★アフィンの ECC は局所の膨らみを表せない(同じ 3 領域で EPE の平均 > 0.5 px)。
4. ★開口問題: 縦棒だけのバーコードでは、縦(dy)の誤差が横(dx)の誤差の 3 倍を超える(縦には模様が無い)。
5. ★余白では場が決まらない: 余白の EPE の中央値 > 2 方向の模様の領域の 2 倍。
6. ★格子の分解能の限界: 波長 24 px の皺は、2 方向の模様の 3 領域で測って、格子 8 → 12 → 16 px と
   誤差が単調に増え、16 px は 8 px の 3 倍超(余白とバーコードは場が決まらないので混ぜない)。
   ★その余白では、曲げの罰だけ(Rueckert 1999 の既定)だと場が真の振幅 1.5 px の数倍まで暴れる。
   ``membrane_weight``(1 階微分の罰)で余白の暴れは抑えられるが、模様のある所の精度と引き換え
   —— 両立しないので既定は曲げだけのまま、両側の数を出す。
7. 雑音が増えると誤差が増える(σ = 0 → 0.05 で EPE の平均が単調に増える)。
8. 鎖: ``registration_to_flow2d`` → PIV 族の ``piv_flow_magnitude`` で変位の大きさの地図
   (模様のある領域の最大が真値と 0.3 px 以内)。

【読み方】各節は「真値 / 推定 / 差」。PASS 行が出れば全部通っている。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import intensityreg as ir  # noqa: E402
import opspiv  # noqa: E402

N = 160


def printed_sheet(seed=0):
    """5 つの領域を持つシート(値は反射率 [0, 1])。→ (画像, {領域名: bool の地図})。

    寸法 [px]: 点の格子(0〜80, 0〜80、ピッチ 10・半径 2.2)/ 文字の塊(80〜160, 0〜80)/
    格子縞のベタ(0〜64, 80〜160、ピッチ 8 の縦横の白抜き線)/ バーコード(64〜112, 80〜160、縦棒だけ)/
    余白(112〜160, 80〜160、紙の地合いだけ)。
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    img = np.full((N, N), 0.92)                                   # 紙の白
    reg = {
        "dots": (xx < 80) & (yy < 80),
        "text": (xx >= 80) & (yy < 80),
        "crosshatch": (xx < 64) & (yy >= 80),
        "barcode": (xx >= 64) & (xx < 112) & (yy >= 80),
        "margin": (xx >= 112) & (yy >= 80),
    }
    img[reg["dots"] & (np.hypot((xx % 10) - 5, (yy % 10) - 5) < 2.2)] = 0.15
    for _ in range(70):                                           # 文字の塊(大きさの違う矩形)
        x0, y0 = rng.integers(82, 154), rng.integers(2, 74)
        w, h = rng.integers(2, 9), rng.integers(4, 10)
        img[y0:y0 + h, x0:x0 + w] = rng.uniform(0.1, 0.4)
    ch = reg["crosshatch"]
    img[ch] = 0.35
    img[ch & (((xx % 8) < 2) | ((yy % 8) < 2))] = 0.8             # 縦横の白抜き線
    widths = rng.integers(1, 5, 40)                               # バーコード: 幅 1〜4 px の縦棒
    x = 66
    for w_ in widths:
        if x + w_ > 110:
            break
        img[80:160, x:x + w_] = 0.1
        x += w_ + int(rng.integers(1, 4))
    img = ndimage.gaussian_filter(img, 0.8)                       # 印刷のにじみ
    img += 0.01 * ndimage.gaussian_filter(rng.normal(0, 1, img.shape), 1.0)   # 紙の地合い(余白にも弱く残る)
    return np.clip(img, 0, 1), reg


def bulge_field(stretch=0.006):
    """異物の膨らみ 2 か所(放射状の押し出し、最大 3.0 px と 2.0 px)+ 搬送方向(x)の弱い引き伸ばし。→ (2,N,N) の (dy, dx)。"""
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    f = np.zeros((2, N, N))
    for cx, cy, amp, R in ((60.0, 60.0, 3.0, 26.0), (105.0, 118.0, 2.0, 22.0)):
        dx, dy = xx - cx, yy - cy
        prof = np.exp(-(dx * dx + dy * dy) / (2 * R * R))
        k = amp / (R * np.exp(-0.5))                              # r = R で最大 = amp
        f += np.stack([k * dy * prof, k * dx * prof])
    f[1] += stretch * (xx - N / 2)
    return f


def _region_stats(A, reg, name):
    m = A["mask"] & reg[name]
    e = A["error_map"][m]
    dy = np.abs(A["est_flow2d"][0] - A["true_flow2d"][0])[m]
    dx = np.abs(A["est_flow2d"][1] - A["true_flow2d"][1])[m]
    return {"mean": float(e.mean()), "median": float(np.median(e)), "dy": float(dy.mean()), "dx": float(dx.mean())}


def main():
    sheet, reg = printed_sheet()
    g = bulge_field()
    gm = np.hypot(g[0], g[1])
    print("シート %s px、真の変位の最大 %.3f px(膨らみ 3.0 px と 2.0 px + 引き伸ばし 0.6 %%)" % (sheet.shape, gm.max()))
    two_way = ("dots", "text", "crosshatch")

    print("\n1-3. 同じ真値で 3 つの方法(領域ごとの EPE の平均 [px])")
    print("   %-14s %7s %7s %10s %8s %7s" % ("方法", "点", "文字", "格子縞", "バーコード", "余白"))
    res = {}
    for name, meth, kw in (("FFD 格子 8 px", "ffd", {}), ("demons(既存)", "demons", {"iters": 200, "sigma": 2.0}),
                           ("ECC アフィン", "ecc", {"motion": "affine"})):
        A = ir.register_accuracy_map(sheet, g, method=meth, method_kwargs=kw, noise_sigma=0.005, seed=1)
        st = {r: _region_stats(A, reg, r) for r in reg}
        res[meth] = (A, st)
        print("   %-14s %7.3f %7.3f %10.3f %8.3f %7.3f" % (name, *(st[r]["mean"] for r in reg)))
    tw = {meth: float(np.mean([res[meth][1][r]["mean"] for r in two_way])) for meth in res}
    print("   2 方向の模様の 3 領域の平均: FFD %.3f / demons %.3f / ECC %.3f px" % (tw["ffd"], tw["demons"], tw["ecc"]))
    assert tw["ffd"] < 0.15 and tw["demons"] < 0.3 and tw["ecc"] > 0.5
    figs.save_grid("sheet_ffd_error_maps",
                   [sheet, res["ffd"][0]["moving"], res["ffd"][0]["error_map"], res["demons"][0]["error_map"]],
                   captions=["printed sheet (5 regions)", "deformed (true field, max %.2f px)" % gm.max(),
                             "FFD EPE [px]", "demons EPE [px]"],
                   gray=[True, True, False, False], vrange=[None, None, (0.0, 2.0), (0.0, 2.0)],
                   colorbar=[False, False, True, True], unit="px",
                   caption="register_accuracy_map: error per pixel against the known field")
    figs.save_table("sheet_ffd_regions", ["method", *reg.keys()],
                    [[m, *("%.3f" % res[m][1][r]["mean"] for r in reg)] for m in res],
                    title="EPE mean per region [px]")

    print("\n4. ★開口問題: バーコード(縦棒だけ)では縦の成分が決まらない(FFD)")
    st = res["ffd"][1]
    print("   バーコード: dy の誤差 %.3f px / dx の誤差 %.3f px(%.1f 倍)"
          % (st["barcode"]["dy"], st["barcode"]["dx"], st["barcode"]["dy"] / st["barcode"]["dx"]))
    print("   格子縞(比べる相手): dy %.3f / dx %.3f px" % (st["crosshatch"]["dy"], st["crosshatch"]["dx"]))
    assert st["barcode"]["dy"] > 3.0 * st["barcode"]["dx"]

    print("\n5. ★余白では場が決まらない(FFD)")
    e2 = float(np.median([st[r]["median"] for r in two_way]))
    print("   余白の EPE 中央値 %.3f px / 2 方向の模様の領域 %.3f px(%.1f 倍)"
          % (st["margin"]["median"], e2, st["margin"]["median"] / e2))
    for row in res["ffd"][0]["by_texture"]:
        print("   勾配の強さ %.4f〜%.4f: EPE 中央値 %.3f px(%d 画素)"
              % (row["grad_lo"], row["grad_hi"], row["epe_median"], row["n"]))
    assert st["margin"]["median"] > 2.0 * e2

    print("\n6. ★格子の分解能の限界(波長 24 px の皺、2 方向の模様の 3 領域で測る)")
    wr = ir.smooth_test_field(sheet.shape, amplitude=1.5, wavelength=24, seed=1)
    e = {}
    for sp in (8, 12, 16):
        A = ir.register_accuracy_map(sheet, wr, method="ffd", method_kwargs={"grid_spacing": sp})
        e[sp] = float(np.mean([_region_stats(A, reg, r)["mean"] for r in two_way]))
        print("   格子 %2d px: EPE 平均 %.3f px(余白 %.3f px)" % (sp, e[sp], _region_stats(A, reg, "margin")["mean"]))
    assert e[8] < e[12] < e[16] and e[16] > 3.0 * e[8]

    print("\n6b. ★余白での暴れと膜の罰(同じ皺、格子 12 px)")
    print("   %16s %18s %16s %16s" % ("membrane_weight", "余白の推定の最大[px]", "余白の EPE[px]", "模様の EPE[px]"))
    blow = {}
    for mem in (0.0, 0.1, 1.0):
        A = ir.register_accuracy_map(sheet, wr, method="ffd", method_kwargs={"grid_spacing": 12, "membrane_weight": mem})
        mm = A["mask"] & reg["margin"]
        mx = float(np.hypot(A["est_flow2d"][0], A["est_flow2d"][1])[mm].max())
        tex_e = float(np.mean([_region_stats(A, reg, r)["mean"] for r in two_way]))
        blow[mem] = (mx, tex_e)
        print("   %16.1f %18.2f %16.3f %16.3f" % (mem, mx, _region_stats(A, reg, "margin")["mean"], tex_e))
    true_max = float(np.hypot(wr[0], wr[1]).max())
    assert blow[0.0][0] > 3.0 * true_max                      # 曲げだけだと余白で真の最大の 3 倍超へ暴れる
    assert blow[1.0][0] < blow[0.0][0] / 2                    # 膜の罰で抑えられる

    print("\n7. 雑音を増やすと")
    prev = -1.0
    for ns in (0.0, 0.01, 0.02, 0.05):
        v = ir.register_accuracy_map(sheet, g, method="ffd", noise_sigma=ns, seed=2)["epe_mean"]
        print("   雑音 σ = %.2f: EPE 平均 %.3f px" % (ns, v))
        assert v > prev
        prev = v

    print("\n8. 鎖: registration_to_flow2d → piv_flow_magnitude")
    M, _ = ir.synthesize_moving(sheet, g)
    flow = ir.registration_to_flow2d(ir.register_ffd(sheet, M))
    mag = opspiv.get("piv_flow_magnitude")(flow)
    tex = (reg["dots"] | reg["text"] | reg["crosshatch"])
    tex[:8] = tex[-8:] = False
    tex[:, :8] = tex[:, -8:] = False
    print("   模様のある領域の変位の大きさの最大 真値 %.3f px / 推定 %.3f px" % (gm[tex].max(), mag[tex].max()))
    assert abs(mag[tex].max() - gm[tex].max()) < 0.3

    for name, arr in (("error_map", res["ffd"][0]["error_map"]), ("magnitude", mag)):
        assert np.isfinite(arr).all() and float(np.ptp(arr)) > 0.0, name
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
