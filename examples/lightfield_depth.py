# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lightfield_depth — ライトフィールド 17 op を「plenoptic 検査機を 1 台通す」筋で一巡する。

    py -3.11 examples/lightfield_depth.py

【この例が解く問題】
産業用 plenoptic カメラ(マイクロレンズアレイ = MLA を撮像素子の前に置き、
**単一センサ・単一ショット**で 2D 画像と画素ごとの深度を同時に得る)を
1 台、紙の上で設計して、そのセンサ生データから深度まで通しで復元する。
(1) 設計: 画素ピッチと MLA ピッチから角度分解能・空間分解能・基線長を出し、
    optics(薄レンズ・被写界深度)を**呼んで**リフォーカス可能レンジを求める。
(2) 撮像: 既知スロープの層でライトフィールドを合成し、MLA 生画像に畳んでから
    復号し直す(往復がビット一致 = 索引算術にオフバイワンが無い証明)。
(3) 視点: 中心視点(= 普通の 2D 画像)・任意サブアパーチャ・EPI を取り出す。
(4) リフォーカス: shift-and-add でスロープを掃引し、鮮鋭度が理論位置で
    ピークになること、**符号を反転すると外れる**ことを数値で示す。
(5) 合成開口: 開口マスクで被写界深度を制御し、median 縮約で**遮蔽物の裏**を
    復元する(視点の過半が見えていれば中央値は背景そのもの)。
(6) 深度: 焦点掃引の鮮鋭度ピーク(無バイアス)と EPI 傾き(高速だが |s|>1 で
    過小評価 = 正直に開示)の両方を出し、metric 深度へ換算する。
(7) 全焦点画像: 画素ごとに自分のスロープで合焦し、どの単一スライスよりも鋭い
    ことを実測で示す。

【グラウンドトゥルース(数値で嘘を弾く)】
1. lf_plenoptic_design: リフォーカスゲイン = 角度分解能(教科書値)。
   image_mm / magnification は optics.thin_lens と機械精度で一致。
2. lf_to_mla → lf_from_mla の往復が np.array_equal(ビット一致)。
3. EPI の端視点間ラグ = slope × (U-1) px ちょうど。
4. 整数スロープ + edge="wrap" のリフォーカスは元テクスチャを 1e-14 以内で復元。
   掃引の鮮鋭度ピークは真値ちょうど、-真値では外れる。
5. 一様マスクの合成開口 = 素の lf_refocus と 1e-14 以内で一致。
   radius=0 の開口 = 中心視点そのもの。
6. 遮蔽の過半が空いている画素で median 合成開口 = 隠れた背景と厳密一致。
7. depth_from_focus の argmax は真値ちょうど、Z = f_px·b/|s| は機械精度。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lightfield as L  # noqa: E402
import optics as O  # noqa: E402


def _sharpness(img):
    """勾配エネルギー(大きいほど鋭い)。例の中だけの物差し。"""
    gy, gx = np.gradient(img)
    return float((gy ** 2 + gx ** 2).mean())


def main():
    # ------------------------------------------------------------------ #
    # 1) 設計: 画素 3.45 µm / MLA 27.6 µm → 角度 8x8、optics を呼んで深度 #
    # ------------------------------------------------------------------ #
    design = L.lf_plenoptic_design(focal_mm=50.0, f_number=8.0, object_mm=300.0,
                                   pixel_um=3.45, mla_pitch_um=27.6,
                                   sensor_px=(2048, 2448))
    print("1) 設計(f=50 mm, f/8, 物体 300 mm, 画素 3.45 µm, MLA 27.6 µm, "
          "2048x2448):")
    print(f"   角度分解能 {design['angular_v']}x{design['angular_u']} "
          f"({design['n_views']} 視点)  空間分解能 "
          f"{design['spatial_h']}x{design['spatial_w']} "
          f"(画素数は {design['resolution_loss']} 分の 1 に)")
    print(f"   MLA ピッチは整数画素か = {design['pitch_is_integer']} "
          f"(実比 {design['angular_exact']:.4f})  "
          f"開口 {design['aperture_mm']:.3f} mm  "
          f"視点間基線 {design['baseline_mm']:.4f} mm")
    print(f"   被写界深度: 画素 CoC {design['dof_pixel_mm']:.3f} mm → "
          f"MLA CoC {design['dof_refocus_mm']:.3f} mm  "
          f"リフォーカスゲイン {design['refocus_gain']:.4f} "
          f"(理論 = 角度分解能 {design['angular_u']})")
    print(f"   深度分解能(視差 0.1 px 相当) {design['depth_precision_mm']:.3f} mm")
    assert abs(design["refocus_gain"] - design["angular_u"]) < 0.01
    lens = O.thin_lens(50.0, 300.0)                 # optics を再実装していない
    assert design["image_mm"] == lens["image_mm"]
    assert design["magnification"] == lens["magnification"]
    assert design["dof_refocus_mm"] == O.depth_of_field(50.0, 8.0, 300.0,
                                                        27.6e-3)["depth_mm"]

    # ------------------------------------------------------------------ #
    # 2) 撮像: 既知スロープの層 → ライトフィールド → MLA 生画像 → 復号     #
    # ------------------------------------------------------------------ #
    ANG, SIZE = 9, 64
    TRUE_SLOPE = 2.0                                # px / 視点 = 既知の深度
    lf, truth = L.lf_synthesize((TRUE_SLOPE,), (ANG, ANG), (SIZE, SIZE),
                                occlusion=False, texture_sigma=3.0,
                                edge="wrap", seed=0)
    raw = L.lf_to_mla(lf)
    decoded = L.lf_from_mla(raw, (ANG, ANG))
    print(f"2) 撮像: 光場 {lf.shape} → MLA 生画像 {raw.shape} → 復号 "
          f"{decoded.shape}")
    print(f"   往復ビット一致 = {np.array_equal(decoded, lf)}  "
          f"(索引算術 raw[t*V+v, s*U+u] == L[v,u,t,s])")
    assert np.array_equal(decoded, lf)
    assert raw.shape == (SIZE * ANG, SIZE * ANG)
    assert float(np.unique(truth)[0]) == TRUE_SLOPE
    # ピッチで割り切れない生画像は黙って切らずに ValueError(オフバイワン封じ)
    try:
        L.lf_from_mla(raw[:-1], (ANG, ANG))
        raise AssertionError("割り切れない生画像が通ってしまった")
    except ValueError as e:
        print(f"   端数のある生画像は fail-closed: {str(e).split('(')[0].strip()}")

    st = L.lf_stats(lf)
    print(f"   stats: {st['n_views']} 視点  中心 ({st['center_v']}, "
          f"{st['center_u']})  中心が実在視点か = {st['center_is_a_view']}  "
          f"測れる最大スロープ {st['max_slope_px']:.1f} px/視点")
    assert st["max_slope_px"] > TRUE_SLOPE          # 測定レンジ内であること

    # ------------------------------------------------------------------ #
    # 3) 視点: 中心視点(= 2D 画像)・サブアパーチャ・EPI                  #
    # ------------------------------------------------------------------ #
    centre = L.lf_center_view(lf)                   # plenoptic が「ついでに」出す 2D
    corner = L.lf_subaperture(lf, 0, 0)
    views = L.lf_views(lf)                          # images 型 = 既存 op への橋
    print(f"3) 視点: 中心視点 {centre.shape}  隅視点 {corner.shape}  "
          f"視点リスト {len(views)} 枚(images 型)")
    assert np.array_equal(centre, lf[ANG // 2, ANG // 2])
    assert np.array_equal(views[0], corner) and len(views) == ANG * ANG

    epi = L.lf_epi(lf, "u", SIZE // 2)               # (U, W) の EPI
    a = epi[0] - epi[0].mean()
    b = epi[-1] - epi[-1].mean()
    lag = int(np.correlate(b, np.tile(a, 2), "valid")[:SIZE].argmax())
    print(f"   EPI {epi.shape}: 端視点間のラグ 実測 {lag} px / "
          f"理論 slope×(U-1) = {TRUE_SLOPE * (ANG - 1):.0f} px")
    assert lag == int(TRUE_SLOPE * (ANG - 1))

    # ------------------------------------------------------------------ #
    # 4) リフォーカス: 掃引の鮮鋭度ピーク、符号を反転すると外れる          #
    # ------------------------------------------------------------------ #
    sweep = np.round(np.linspace(-4.0, 4.0, 81), 6)
    stack = L.lf_focal_stack(lf, sweep, edge="wrap")
    var = np.array([np.var(s[16:-16, 16:-16]) for s in stack])
    peak = float(sweep[int(var.argmax())])
    at_true = L.lf_refocus(lf, TRUE_SLOPE, edge="wrap")
    at_wrong = L.lf_refocus(lf, -TRUE_SLOPE, edge="wrap")
    print(f"4) リフォーカス: 掃引 {len(sweep)} 面の鮮鋭度ピーク {peak:+.2f} / "
          f"真値 {TRUE_SLOPE:+.2f}")
    print(f"   真値で合焦した像と中心視点の最大差 "
          f"{float(np.abs(at_true - centre).max()):.2e}(整数スロープ+wrap は厳密)")
    print(f"   符号を反転すると分散が "
          f"{np.var(at_true) / np.var(at_wrong):.1f} 倍悪化(符号の取り違え検出)")
    assert peak == TRUE_SLOPE
    assert np.abs(at_true - centre).max() < 1e-14
    assert np.var(at_true) > 4.0 * np.var(at_wrong)

    # ------------------------------------------------------------------ #
    # 5) 合成開口: 絞る / 遮蔽物の裏を median で覗く                       #
    # ------------------------------------------------------------------ #
    full = L.lf_aperture_mask((ANG, ANG), "square", radius=10.0)
    stopped = L.lf_aperture_mask((ANG, ANG), "circle", radius=1.0)
    pinhole = L.lf_aperture_mask((ANG, ANG), "circle", radius=0.0)
    print(f"5) 合成開口: 全開 {int((full > 0).sum())} 視点 / "
          f"絞り {int((stopped > 0).sum())} 視点 / ピンホール "
          f"{int((pinhole > 0).sum())} 視点(重みは総和 1 に正規化)")
    assert np.allclose(L.lf_synthetic_aperture(lf, TRUE_SLOPE, full, edge="wrap"),
                       at_true, atol=1e-14)         # 一様マスク = 素のリフォーカス
    assert np.allclose(L.lf_synthetic_aperture(lf, 0.0, pinhole), centre,
                       atol=1e-15)                  # ピンホール = 中心視点
    # 絞ると非合焦面のボケが減る = 被写界深度が伸びる
    off_full = np.var(L.lf_synthetic_aperture(lf, 0.0, full, edge="wrap"))
    off_stop = np.var(L.lf_synthetic_aperture(lf, 0.0, stopped, edge="wrap"))
    print(f"   非合焦(slope 0)での残存コントラスト: 全開 {off_full:.4f} → "
          f"絞り {off_stop:.4f}(絞るほど深度が伸びる)")
    assert off_stop > off_full

    # 遮蔽シーン: 背景(slope 0)の手前に slope 3 の遮蔽物が 25% を覆う
    rng = np.random.default_rng(7)
    from scipy.ndimage import gaussian_filter
    bg = gaussian_filter(rng.standard_normal((SIZE, SIZE)), 2.0, mode="wrap")
    bg = (bg - bg.min()) / (bg.max() - bg.min())
    blob = gaussian_filter(rng.standard_normal((SIZE, SIZE)), 2.0, mode="wrap")
    occ = blob >= np.quantile(blob, 0.75)           # 25% を覆う
    c = (ANG - 1) / 2.0
    lf_occ = np.empty((ANG, ANG, SIZE, SIZE))
    blocked = np.zeros((SIZE, SIZE))
    for v in range(ANG):
        for u in range(ANG):
            m = np.roll(occ, (int(3.0 * (v - c)), int(3.0 * (u - c))),
                        axis=(0, 1))
            lf_occ[v, u] = np.where(m, 0.95, bg)
            blocked += m
    blocked /= ANG * ANG
    mean_r = L.lf_synthetic_aperture(lf_occ, 0.0, reduce="mean", edge="wrap")
    med_r = L.lf_synthetic_aperture(lf_occ, 0.0, reduce="median", edge="wrap")
    rms = lambda x: float(np.sqrt(((x - bg)[occ] ** 2).mean()))
    print(f"   遮蔽物が中心視点の {occ.mean():.0%} を覆い、隠れた画素で塞がる"
          f"視点は最大 {blocked[occ].max():.0%}(過半未満)")
    print(f"   隠れた背景との RMS: 中心視点 {rms(lf_occ[ANG//2, ANG//2]):.4f} / "
          f"mean {rms(mean_r):.4f} / median {rms(med_r):.2e}(中央値は厳密復元)")
    assert blocked[occ].max() < 0.5
    assert rms(med_r) < 1e-12 < rms(mean_r)

    # ------------------------------------------------------------------ #
    # 6) 深度: 焦点掃引(無バイアス)と EPI 傾き(速いが偏る)             #
    # ------------------------------------------------------------------ #
    dff, conf = L.lf_depth_from_focus(lf, sweep, edge="wrap", subpixel=False)
    epi_s, energy = L.lf_epi_slope(lf)
    dff_med = float(np.median(dff))
    epi_med = float(np.median(epi_s[16:-16, 16:-16]))
    print(f"6) 深度: 焦点掃引 中央値 {dff_med:+.4f}(真値 {TRUE_SLOPE:+.2f}、"
          f"argmax は真値ちょうど)")
    print(f"   EPI 傾き 中央値 {epi_med:+.4f} = 真値の "
          f"{epi_med / TRUE_SLOPE:.1%}(|s|>1 で過小評価 — 正直な開示のとおり)")
    assert dff_med == TRUE_SLOPE
    assert 0.85 * TRUE_SLOPE < epi_med < TRUE_SLOPE   # 偏るが符号と桁は合う
    assert (conf > 0).any() and (energy > 0).any()

    focal_px = 50.0 / 27.6e-3                        # サブアパーチャ画素 = MLA ピッチ
    base = design["baseline_mm"]
    depth = L.lf_disparity_to_depth(dff, focal_px=focal_px, baseline=base)
    expect = focal_px * base / TRUE_SLOPE
    print(f"   metric 深度 = f_px·b/|s| = {float(np.median(depth)):.3f} mm / "
          f"閉形式 {expect:.3f} mm  (f_px={focal_px:.1f} px, b={base:.4f} mm)")
    assert abs(float(np.median(depth)) - expect) < 1e-9
    # 視差ゼロ(無限遠)は黙って inf を返さず fail-closed
    try:
        L.lf_disparity_to_depth(np.zeros((4, 4)), focal_px, base)
        raise AssertionError("視差ゼロが通ってしまった")
    except ValueError:
        print("   視差ゼロ(無限遠)は無言の inf ではなく ValueError")

    # ------------------------------------------------------------------ #
    # 7) 全焦点画像: 画素ごとに自分のスロープで合焦                        #
    # ------------------------------------------------------------------ #
    scene, gt = L.lf_synthesize((3.0, 0.0), (ANG, ANG), (SIZE, SIZE),
                                occlusion=True, coverage=0.4,
                                texture_sigma=2.0, edge="wrap", seed=5)
    levels = tuple(np.round(np.linspace(-1.0, 4.0, 21), 6))
    slope_map, _ = L.lf_depth_from_focus(scene, levels, edge="wrap",
                                         subpixel=False)
    aif = L.lf_all_in_focus(scene, slope_map, levels=levels, edge="wrap")
    slices = [_sharpness(s) for s in L.lf_focal_stack(scene, levels, edge="wrap")]
    agree = float((np.abs(slope_map - gt) < 1e-9).mean())
    print(f"7) 全焦点: 2 層シーン(slope 3 の手前が {(gt > 1.5).mean():.0%} を遮蔽)")
    print(f"   推定スロープが真値と一致した画素 {agree:.1%}")
    print(f"   鮮鋭度: 全焦点 {_sharpness(aif):.5f} > 最良の単一スライス "
          f"{max(slices):.5f}(最悪 {min(slices):.5f})")
    assert _sharpness(aif) > max(slices)
    assert agree > 0.5

    print("PASS: lightfield 17 op すべてが閉形式のグラウンドトゥルースと一致")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
