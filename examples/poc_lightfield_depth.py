# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ライトフィールドから深度を出す —— 既知の深度で作った光場に、ゼロ点を並べて突きつける。

    py -3.11 examples/poc_lightfield_depth.py

EXTEND: 実データに差し替えるなら :func:`make_scene` だけを差し替える。以降の
評価・ゼロ点・表は光場配列 ``(V, U, H, W)`` と真値スロープ地図 ``(H, W)`` の
2 つしか見ていない。

  * HCI 4D Light Field Benchmark(Honauer et al., ACCV 2016、
    https://lightfield-analysis.uni-konstanz.de/)が最も近い。9x9 の整流済み
    サブアパーチャ画像と**画素ごとの真値視差**が付き、その視差の単位は
    「隣接視点 1 ステップあたりの画素シフト」= 本モジュールの ``slope`` と
    **同じ量**なので、単位換算なしにそのまま真値として使える。読み込みは
    ``9x9`` 枚の PNG を ``lf[v, u]`` に並べ、``parameters.cfg`` の
    ``focal_length_mm`` / ``baseline_mm`` / ``sensor_size_mm`` から
    :func:`lightfield.lf_disparity_to_depth` の ``focal_px`` と ``baseline`` を
    作る(``focal_px = focal_length_mm / (sensor_size_mm / W)``)。
  * Stanford Light Field Archive(http://lightfield.stanford.edu/lfs.html)は
    17x17 の実写グリッドだが**真値深度が無い**ので、推定器どうしの比較には
    使えても本 PoC の 1 章(真値との突き合わせ)は成立しない。
  * 生の plenoptic フレーム(Lytro 等)を通したい場合、
    :func:`lightfield.lf_from_mla` は**整流済み**の生フレームしか受け取らない
    (マイクロレンズ中心のサブピクセル較正は同モジュールの範囲外だと明記されて
    いる)。白画像からの MLA 中心推定を自前で通してから渡すこと。

**データはこのリポジトリに同梱しない。** 上記はいずれも配布条件つきの外部
データセットで、取得は利用者が各サイトの条件に従って行う。成果物には出典
(HCI 4D LF Benchmark / Stanford Light Field Archive)を明記する。

視差と深度の変換式(この PoC が使う唯一の物理):

    スロープ s = 角度インデックス 1 ステップあたりの画素シフト [px/view]
    Z = focal_px * baseline / |s|        [baseline と同じ長さ単位]
    s = focal_px * baseline / Z

    平面(3D の平面)の視差は**画像座標の 1 次関数**になる。平面 n・X = d 上の
    点は X = Z*(x/f, y/f, 1) だから Z*(n1*x + n2*y + n3*f) = d*f、すなわち
    1/Z が (x, y) の 1 次関数 = s も 1 次関数。だから「傾いた面」は
    s(x) = s0 + g*x で厳密に表せる —— 近似ではない。

この PoC が示すこと:

1. **真値を自分で作る** —— 背景平面・手前平面・傾いた面の 3 層を、層ごとに
   解析的な逆写像で各視点へ描く(傾いた面の逆写像も閉形式: x' = x*(1+g*du)
   + s0*du を解くだけ)。中心視点は恒等写像なので、真値スロープ地図は
   そのまま中心視点座標で書ける。
2. **ゼロ点を 2 つ置く** —— (a) 全画素を同じ深度と答える定数推定、しかも
   RMSE を最小にする**最良の**定数(真値の平均。実際には知り得ない = 強い
   ゼロ点)。(b) 同じ光場から**視点を 2 枚だけ**取り出した素のブロック
   マッチング(stereo.disparity_subpixel)。
3. **結論は正直に** —— ランバート・十分なテクスチャの場面では、**2 眼ゼロ点が
   ライトフィールドの 2 手法を上回った**。81 視点のうち 2 枚しか使わない手法に
   負けるので、足りないのはデータではなく推定器である。ライトフィールド側が
   明確に勝ったのは**鏡面ハイライト**の 1 領域だけで、そこでは逆に 2 眼が
   壊滅する(誤差 85 % 対 2 %)。理由も測って書いた。
4. **角度分解能を振る** —— 3x3 / 5x5 / 9x9。基線長 (U-1) が倍になれば視差の
   推定誤差は半分、という予測と実測を並べる。
5. **壊れる条件** —— 無テクスチャ / 遮蔽境界 / 鏡面反射の 3 つで境界を数字にする。

★ この PoC が出した道具の穴(op 本体は直していない):

  (a) **``lf_depth_from_focus`` の既定 ``interp="linear"`` はスロープを整数へ
      吸着させる。** shift-and-add の双 1 次補間は「整数シフトだけボケない」ので、
      焦点尺度のピークが整数スロープへ引き寄せられる。視点を**厳密な Fourier
      シフト**で作って生成側の補間を排除したうえで実測(5x5、80x80、掃引 0.05
      刻み): 真値 1.08 -> 1.0062 / 1.15 -> 1.0118 / 1.30 -> 1.4750 /
      1.85 -> 1.9882。最大 0.175 px/view のずれ = **深度で 13 %**。
      ``interp="cubic"`` を渡すと同じ入力で 1.0765 / 1.1462 / 1.3002 / 1.8538 に
      なる(残差 0.005 以下)。module docstring は「Bilinear resampling blurs …
      pass ``interp="cubic"`` when that matters」と書いているが、**深度 op の
      既定が linear のままで、吸着の大きさも書かれていない**。
      さらに docstring の実測「argmax landed exactly on the true slope in 18 of
      18」は真値が 0.0/±0.5/±1.0/±1.5/±2.0 = **すべて掃引格子上の丸い数**で
      構成されており、整数吸着を原理的に検出できない試験だった。
  (b) **``lf_epi_slope`` の ``min_energy=1e-10`` は既定では何も止めない。**
      テクスチャ 0(振幅 0.005 のセンサノイズだけ)の光場でも energy 中央値は
      2.0e-3 = 既定の 2e7 倍で、**ゲート率 0.0 %**。同時に slope は 1.30 の真値に
      対し -0.006 まで崩れる。docstring の「threshold on ``energy`` instead of
      being handed a plausible-looking number」は正しいが、しきい値の目安が
      無く既定値は実質無効。呼び出し側が場面ごとに較正するしかない。
  (c) **``lf_epi_slope`` の偏りはノイズでも増える。** docstring はスロープの
      大きさ由来の偏り(|s|>1 で過小)を正直に開示しているが、SNR 依存は書かれて
      いない。実測(真値 1.30、5x5): コントラスト 1.0 で 1.241、0.1 で 0.822、
      0.03 で 0.181。同じ入力で 2 眼ブロックマッチングは 1.305 / 1.314 / 1.363。
  (d) **``stereo.disparity_subpixel`` が RuntimeWarning を漏らす。** 124 行目の
      ``np.where(denom > 1e-12, 0.5 * (cm - cp) / denom, 0.0)`` は両枝を評価する
      ため ``denom == 0`` の画素(平坦領域)で「invalid value encountered in
      divide」が出る。値は捨てられるので結果は正しいが、呼び出し側のログが
      汚れる。同じ状況で ``lightfield.lf_epi_slope`` は
      ``np.divide(..., out=, where=)`` を使っており、族の中で不統一。
      最小再現 = 16x16 の階段画像 2 枚を ``disparity_subpixel(a, b, 8, 5, "ssd")``。
  (e) **``MAX_STACK_SLICES = 256`` が深度分解能の天井。** ``lf_depth_from_focus``
      の分解能は掃引点数で決まる op なのに、その上限が 256 面であることは
      docstring に書かれていない(0..3 の範囲なら 0.0118 px/view が下限)。
      なお掃引を 61 点から 241 点へ細かくしても誤差は改善しない(実測 0.0733 ->
      0.0810 で悪化)—— 限界は掃引の粗さではなく (a) の補間だから。
  (f) **同じ族の中で ``edge`` の既定が食い違う。** ``lf_synthesize`` は
      ``edge="wrap"``、``lf_refocus`` / ``lf_depth_from_focus`` は
      ``edge="nearest"``。合成した光場をそのまま深度 op に渡すと境界の扱いが
      黙って入れ替わる。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lightfield as L  # noqa: E402
import stereo as S  # noqa: E402

# --- カメラ(この PoC の唯一の物理定数)------------------------------------
F_PX = 1200.0          # サブアパーチャ画像の焦点距離 [px]
BASELINE_MM = 0.5      # 視点 1 ステップの基線長 [mm] -> f*b = 600 mm*px
H = W = 96             # 主シーンの空間分解能
SWEEP = np.round(np.linspace(0.0, 3.0, 61), 6)   # 焦点掃引(0.05 px/view 刻み)


def slope_to_depth_mm(s):
    """s [px/view] -> Z [mm]。閉形式そのもの(op の答え合わせ用)。"""
    return F_PX * BASELINE_MM / np.abs(s)


def depth_to_slope(z_mm):
    """Z [mm] -> s [px/view]。"""
    return F_PX * BASELINE_MM / float(z_mm)


# --------------------------------------------------------------------------- #
# 1. 真値の合成                                                                #
# --------------------------------------------------------------------------- #
def _texture(shape, sigma, rng, contrast=1.0):
    """帯域制限ノイズ(周期的)。contrast で振幅だけ落とす。"""
    t = ndi.gaussian_filter(rng.standard_normal(shape), sigma, mode="wrap")
    t = (t - t.min()) / (t.max() - t.min())
    return 0.5 + contrast * (t - 0.5)


def _warp(img, du, dv, s0, g, order=3):
    """視点 (v, u) が見る像。中心視点座標 x の点は x + s(x)*du へ動く。

    s(x) = s0 + g*x なので x' = x*(1 + g*du) + s0*du。これは x について 1 次
    なので**逆写像も閉形式**: x = (x' - s0*du) / (1 + g*du)。y は x が決まれば
    y = y' - s(x)*dv。近似も反復解法も要らない。
    """
    hh, ww = img.shape
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float64)
    xs = (xx - s0 * du) / (1.0 + g * du)
    s = s0 + g * xs
    return ndi.map_coordinates(img, [yy - s * dv, xs], order=order,
                               mode="nearest")


def make_scene(angular, *, contrast=1.0, noise=0.0, seed=0, texture_sigma=2.0):
    """3 層シーンの光場 ``(V, U, H, W)`` と真値スロープ地図 ``(H, W)``。

    層(奥から): 背景平面 Z=1395 mm / 傾いた面 Z=632->351 mm / 手前平面 Z=321 mm。
    スロープはどれも半端な値にしてある —— 丸い値だと視差が整数になり、
    ブロックマッチングの量子化も焦点度の整数吸着も見えなくなるため。
    """
    rng = np.random.default_rng(seed)
    x = np.arange(W)[None, :] * np.ones((H, 1))
    y = np.arange(H)[:, None] * np.ones((1, W))
    x1, x2 = 56, 86
    g = (1.71 - 0.95) / (x2 - x1)              # 傾いた面: 0.95 -> 1.71 px/view
    layers = [
        # (s0, g, alpha, texture) 奥から手前へ
        (0.43, 0.0, np.ones((H, W)), _texture((H, W), texture_sigma, rng, contrast)),
        (0.95 - g * x1, g,
         ((x >= x1) & (x < x2) & (y >= 12) & (y < H - 12)).astype(np.float64),
         _texture((H, W), texture_sigma, rng, contrast)),
        (1.87, 0.0,
         ((x >= 14) & (x < 42) & (y >= 20) & (y < 72)).astype(np.float64),
         _texture((H, W), texture_sigma, rng, contrast)),
    ]
    V, U = angular
    vc, uc = (V - 1) / 2.0, (U - 1) / 2.0
    lf = np.zeros((V, U, H, W))
    for v in range(V):
        for u in range(U):
            acc = np.zeros((H, W))
            for s0, gg, alpha, tex in layers:
                a = _warp(alpha, u - uc, v - vc, s0, gg, order=1) >= 0.5
                acc = np.where(a, _warp(tex, u - uc, v - vc, s0, gg), acc)
            lf[v, u] = acc
    if noise:
        lf = lf + rng.normal(0.0, noise, lf.shape)
    gt = np.zeros((H, W))
    for s0, gg, alpha, tex in layers:
        gt = np.where(alpha >= 0.5, s0 + gg * x, gt)
    return lf, gt


def fourier_plane(angular, slope, texture):
    """1 平面だけの光場を**厳密な Fourier シフト**で作る(生成側の補間ゼロ)。

    周期的な帯域制限テクスチャなら小数シフトも厳密に表せる。整数吸着の測定で
    「ボケているのは生成側か op 側か」を切り分けるために要る。
    """
    V, U = angular
    vc, uc = (V - 1) / 2.0, (U - 1) / 2.0
    spec = np.fft.fft2(texture)
    lf = np.empty((V, U) + texture.shape)
    for v in range(V):
        for u in range(U):
            lf[v, u] = np.real(np.fft.ifft2(
                ndi.fourier_shift(spec, (slope * (v - vc), slope * (u - uc)))))
    return lf


# --------------------------------------------------------------------------- #
# 推定器(ゼロ点 2 つ + ライトフィールド 2 つ)                                #
# --------------------------------------------------------------------------- #
def null_constant(gt, mask):
    """ゼロ点 A: 全画素同じ深度。RMSE を最小にする**最良の**定数を与える。

    最良の定数は真値の平均(実際には知り得ない)。負けたら言い訳ができない
    ように、あえて最強の定数を渡す。RMSE は真値の標準偏差そのものになる。
    """
    return np.full(gt.shape, float(gt[mask].mean()))


def null_two_view(lf, *, block=7, method="ssd", wings="both"):
    """ゼロ点 B: 同じ光場から**視点を 2 枚だけ**使う素のブロックマッチング。

    中心視点 (vc, uc) を基準に、水平方向の端視点 u=0 と対応を取る。
    ``stereo`` の規約は ``L[y, x] == R[y, x - d]`` なので、中心視点を L、
    u=0 の視点を R に置くと ``d = s * uc`` がそのまま出る。真値地図は中心視点
    座標なので、基準フレームを合わせるために端視点どうし(基線 U-1)ではなく
    中心 - 端(基線 uc = (U-1)/2)を使う。``wings="both"`` は反対側の翼
    (列を反転して同じ matcher に通す)も取って平均し、実質フル開口にする。
    """
    V, U = lf.shape[:2]
    c_v, c_u = V // 2, U // 2
    uc = (U - 1) / 2.0
    max_disp = int(np.ceil(3.0 * uc)) + 2
    centre = lf[c_v, c_u]
    left = S.disparity_subpixel(centre, lf[c_v, 0], max_disp, block, method) / uc
    if wings != "both":
        return left
    right = S.disparity_subpixel(centre[:, ::-1], lf[c_v, -1][:, ::-1],
                                 max_disp, block, method)[:, ::-1] / uc
    return 0.5 * (left + right)


def lf_epi(lf, **kw):
    """ライトフィールド A: EPI 直線の構造テンソル(1 パス、掃引なし)。"""
    return L.lf_epi_slope(lf, **kw)


def lf_focus(lf, slopes=SWEEP, *, interp="linear", edge="nearest"):
    """ライトフィールド B: リフォーカス掃引の鮮鋭度ピーク。"""
    return L.lf_depth_from_focus(lf, slopes, interp=interp, edge=edge)


# --------------------------------------------------------------------------- #
# 評価                                                                         #
# --------------------------------------------------------------------------- #
def slope_err(est, gt, mask):
    """(MAE, RMSE, 符号つき偏り) [px/view]。"""
    d = est[mask] - gt[mask]
    return float(np.abs(d).mean()), float(np.sqrt((d ** 2).mean())), float(d.mean())


def depth_rel_err(est, gt, mask):
    """深度の相対誤差の中央値 [%]。Z = f*b/|s| なので |s_gt/s_est - 1| に等しい。

    無限遠側の極を持つので中央値で見る(平均は 1 画素で発散しうる)。
    """
    z_est = L.lf_disparity_to_depth(np.clip(np.abs(est[mask]), 1e-3, None),
                                    F_PX, BASELINE_MM)
    z_gt = slope_to_depth_mm(gt[mask])
    return float(np.median(np.abs(z_est - z_gt) / z_gt) * 100.0)


def region_masks(gt, border=14, clean_dist=8, edge_dist=3):
    """内側 / 深度不連続から離れた清浄域 / 遮蔽境界の 3 マスク。"""
    inner = np.zeros(gt.shape, bool)
    inner[border:-border, border:-border] = True
    jump = (ndi.maximum_filter(gt, 3) - ndi.minimum_filter(gt, 3)) > 0.1
    dist = ndi.distance_transform_edt(~jump)
    return inner, inner & (dist > clean_dist), inner & (dist <= edge_dist), dist


# --------------------------------------------------------------------------- #
def main():
    print("=== 1. 真値 —— 既知の深度から光場を作り、符号の規約を確かめる ===")
    print(f"  カメラ: focal_px = {F_PX:.0f} px, baseline = {BASELINE_MM} mm "
          f"-> f*b = {F_PX * BASELINE_MM:.0f} mm*px")
    print("  Z = f_px * baseline / |s|   (s = 角度 1 ステップあたりの画素シフト)")
    print(f"  {'層':>12}{'s [px/view]':>14}{'Z [mm]':>12}")
    for name, s in (("背景平面", 0.43), ("傾いた面 左端", 0.95),
                    ("傾いた面 右端", 1.71), ("手前平面", 1.87)):
        print(f"  {name:>12}{s:>14.2f}{slope_to_depth_mm(s):>12.1f}")
    print("  平面の視差は画像座標の 1 次関数(1/Z が 1 次だから)。")
    print("  「傾いた面」は s(x) = s0 + g*x で厳密 —— 近似ではない。")

    # 符号の規約: 生成側 (+s で大きい u ほど右へ) と lf_refocus (-s でシフト
    # して足す) が一致していることを、整数スロープの厳密復元で確かめる。
    rng0 = np.random.default_rng(3)
    tex80 = _texture((80, 80), 2.0, rng0)
    lf_int = fourier_plane((5, 5), 1.0, tex80)
    back = L.lf_refocus(lf_int, 1.0, edge="wrap")
    print(f"  符号の検算: s=1.0 の 1 平面を作り lf_refocus(+1.0) で戻すと "
          f"元テクスチャとの最大差 {float(np.abs(back - tex80).max()):.2e}")
    wrong = L.lf_refocus(lf_int, -1.0, edge="wrap")
    print(f"            符号を反転すると {float(np.abs(wrong - tex80).max()):.2e} "
          f"(取り違えれば一目で分かる)")

    lf9, gt = make_scene((9, 9), noise=0.01, seed=0)
    inner, clean, bnd, dist = region_masks(gt)
    x = np.arange(W)[None, :] * np.ones((H, 1))
    tilt = clean & (gt > 0.9) & (gt < 1.8)
    fit = np.polyfit(x[tilt], gt[tilt], 1)
    print(f"  合成: 光場 {lf9.shape}(センサノイズ sigma 0.01)/ 真値地図 {gt.shape}")
    print(f"  傾いた面の真値を x の 1 次で当てると残差 "
          f"{float(np.abs(np.polyval(fit, x[tilt]) - gt[tilt]).max()):.2e} "
          f"(勾配 {fit[0]:.5f} px/view/px)")

    print("\n=== 2. ゼロ点 —— 定数と 2 眼ブロックマッチングを上回るか(9x9)===")
    est = {}
    est["定数(最良)"] = null_constant(gt, clean)
    est["2 眼 BM(片翼)"] = null_two_view(lf9, wings="one")
    est["2 眼 BM(両翼)"] = null_two_view(lf9)
    est["EPI 傾き"] = lf_epi(lf9)[0]
    est["焦点度(既定 linear)"] = lf_focus(lf9)[0]
    est["焦点度(cubic)"] = lf_focus(lf9, interp="cubic")[0]
    print(f"  評価域 = 深度不連続から 8 px 以上離れた内側 {int(clean.sum())} 画素")
    print(f"  {'手法':>22}{'MAE':>9}{'RMSE':>9}{'偏り':>9}{'深度誤差 中央値':>16}")
    base_rmse = None
    for name, e in est.items():
        mae, rmse, bias = slope_err(e, gt, clean)
        if base_rmse is None:
            base_rmse = rmse
        print(f"  {name:>22}{mae:>9.4f}{rmse:>9.4f}{bias:>+9.4f}"
              f"{depth_rel_err(e, gt, clean):>15.2f}%")
    print("  → 単位は px/view。定数ゼロ点の RMSE は真値の標準偏差そのもの。")
    print(f"  → ライトフィールドは定数ゼロ点を "
          f"{base_rmse / slope_err(est['焦点度(cubic)'], gt, clean)[1]:.0f} 倍上回る。")
    print(f"     だが**2 眼ゼロ点には負けている**"
          f"(2 眼 {slope_err(est['2 眼 BM(両翼)'], gt, clean)[1]:.4f} < "
          f"焦点度 cubic {slope_err(est['焦点度(cubic)'], gt, clean)[1]:.4f})。")
    print("     2 眼は 81 視点のうち 2 枚しか使っていない。足りないのはデータでは")
    print("     なく推定器の方 —— 少なくともランバートで十分にテクスチャのある面では。")

    print("\n=== 3. 角度分解能 —— 基線が倍なら誤差は半分か ===")
    print(f"  {'角度':>8}{'基線 [step]':>12}{'EPI 傾き':>11}{'焦点度 cubic':>14}"
          f"{'2 眼 BM':>10}{'焦点度の改善比':>16}")
    prev = None
    rows = {}
    for ang in (3, 5, 9):
        lf = lf9 if ang == 9 else make_scene((ang, ang), noise=0.01, seed=0)[0]
        r_epi = slope_err(lf_epi(lf)[0], gt, clean)[1]
        r_dff = slope_err(lf_focus(lf, interp="cubic")[0], gt, clean)[1]
        r_bm = slope_err(null_two_view(lf), gt, clean)[1]
        ratio = (prev / r_dff) if prev else float("nan")
        rows[ang] = (r_epi, r_dff, r_bm)
        print(f"  {ang}x{ang:<6}{(ang - 1) / 2.0:>12.1f}{r_epi:>11.4f}"
              f"{r_dff:>14.4f}{r_bm:>10.4f}{ratio:>16.2f}")
        prev = r_dff
    print("  → 予測: 視差の推定精度が px 単位で一定なら、スロープの誤差は基線に")
    print("     反比例する。基線を倍にするごとに改善比 2.0 が出れば予測どおり。")
    print("  → 焦点度は予測に従う。EPI 傾きは**従わない** —— 視点を増やしても")
    print("     良くならない、あるいは悪化する。これは分散ではなく偏りだから")
    print("     (docstring の |s|>1 で過小評価する既知の偏り)。")

    print("\n=== 4. ★ 焦点度は整数スロープへ吸着する(道具の穴)===")
    print("  視点は**厳密な Fourier シフト**で作る(生成側の補間をゼロにして、")
    print("  ボケが op 側のものだと確定させる)。5x5、80x80、掃引 0.05 刻み。")
    print(f"  {'真値':>8}{'linear(既定)':>14}{'cubic':>10}{'EPI':>9}{'2 眼 BM':>10}")
    snap = {}
    for s_true in (1.00, 1.08, 1.15, 1.30, 1.85):
        lf = fourier_plane((5, 5), s_true, tex80)
        i = (slice(14, -14), slice(14, -14))
        lin = float(np.median(lf_focus(lf, edge="wrap")[0][i]))
        cub = float(np.median(lf_focus(lf, interp="cubic", edge="wrap")[0][i]))
        ep = float(np.median(lf_epi(lf)[0][i]))
        bm = float(np.median(null_two_view(lf)[i]))
        snap[s_true] = (lin, cub)
        print(f"  {s_true:>8.2f}{lin:>14.4f}{cub:>10.4f}{ep:>9.4f}{bm:>10.4f}")
    worst = max(snap, key=lambda k: abs(snap[k][0] - k))
    lin, cub = snap[worst]
    print(f"  → 既定 linear は最悪 {abs(lin - worst):.4f} px/view ずれる"
          f"(真値 {worst:.2f} -> {lin:.4f})。深度では "
          f"{100 * abs(worst / lin - 1):.1f} %。")
    print(f"     cubic は同じ入力で {cub:.4f}(残差 {abs(cub - worst):.4f})。")
    print("     双 1 次補間は整数シフトだけボケないので、焦点尺度のピークが")
    print("     整数スロープへ引き寄せられる。**深度 op の既定が linear なのは罠**。")
    print("     docstring の「18 of 18 で argmax が真値ちょうど」は真値が")
    print("     0.0/±0.5/±1.0/±1.5/±2.0 = 全部掃引格子上の丸い数で、この吸着を")
    print("     原理的に検出できない試験構成だった。")

    print("\n=== 5. 壊れる条件 (a) 無テクスチャ ===")
    print("  真値 1.30 の 1 平面、センサノイズ sigma 0.005 固定でテクスチャ振幅を落とす。")
    print(f"  {'コントラスト':>12}{'SNR':>7}{'焦点度':>9}{'EPI':>9}{'2 眼 BM':>10}"
          f"{'energy':>11}{'ゲート率':>10}")
    tex_break = {}
    for contrast in (1.0, 0.3, 0.1, 0.03, 0.01, 0.0):
        tex = 0.5 + contrast * (tex80 - 0.5)
        lf = fourier_plane((5, 5), 1.30, tex)
        lf = lf + np.random.default_rng(9).normal(0.0, 0.005, lf.shape)
        i = (slice(14, -14), slice(14, -14))
        dff = float(np.median(lf_focus(lf, interp="cubic", edge="wrap")[0][i]))
        sl, energy = lf_epi(lf)
        ep = float(np.median(sl[i]))
        bm = float(np.median(null_two_view(lf)[i]))
        gated = 100.0 * float((energy[i] <= 1e-10).mean())
        tex_break[contrast] = (dff, ep, bm)
        print(f"  {contrast:>12.3f}{contrast / 0.005:>7.0f}{dff:>9.3f}{ep:>9.3f}"
              f"{bm:>10.3f}{float(np.median(energy[i])):>11.3g}{gated:>9.1f}%")
    print("  → EPI 傾きは SNR 20(コントラスト 0.1)で既に -37 %、SNR 6 で崩壊する。")
    print("     ノイズは視点ごとに独立で視差 0 なので、構造テンソルの分母を")
    print("     ノイズが埋めてスロープを 0 へ引く。焦点度と 2 眼はもっと粘る。")
    print(f"  → ★ ``min_energy=1e-10`` の既定ゲートは**テクスチャ 0 でも 0.0 % しか")
    print("     止めない**(純ノイズの energy が既定の 2e7 倍)。confidence は")
    print("     返るが、しきい値は呼び出し側が場面ごとに較正するしかない。")
    try:
        L.lf_disparity_to_depth(np.zeros((4, 4)), F_PX, BASELINE_MM)
        raise AssertionError("視差ゼロが通ってしまった")
    except ValueError:
        print("  → 視差ゼロ(= ゲートされた画素)を深度へ渡すと ValueError。")
        print("     無言の inf ではないのは正しい。far_depth で明示的に飽和させる。")

    print("\n=== 5. 壊れる条件 (b) 遮蔽境界 ===")
    print("  主シーン(9x9)で、深度不連続からの距離ごとに誤差を測る。")
    print(f"  {'距離 [px]':>10}{'画素数':>8}{'焦点度 cubic':>14}{'EPI':>9}{'2 眼 BM':>10}")
    dff9 = est["焦点度(cubic)"]
    epi9 = est["EPI 傾き"]
    bm9 = est["2 眼 BM(両翼)"]
    band = {}
    for lo, hi, label in ((0, 1, "0-1"), (1, 3, "1-3"), (3, 5, "3-5"),
                          (5, 9, "5-9"), (9, 1e9, "9 以上")):
        m = inner & (dist >= lo) & (dist < hi)
        vals = [slope_err(e, gt, m)[1] for e in (dff9, epi9, bm9)]
        band[label] = vals
        print(f"  {label:>10}{int(m.sum()):>8}{vals[0]:>14.3f}{vals[1]:>9.3f}"
              f"{vals[2]:>10.3f}")
    print(f"  → 境界に接する画素(0-1 px)の誤差は内側(9 px 以上)の "
          f"{band['0-1'][0] / band['9 以上'][0]:.0f} 倍(焦点度)/ "
          f"{band['0-1'][2] / band['9 以上'][2]:.0f} 倍(2 眼)。")
    print("     境界から 5 px 離れれば内側の水準に戻る = 影響半径は開口の見込み")
    print("     視差(最大 s*(U-1)/2 = 7.5 px)と同じ桁。どの手法も遮蔽を")
    print("     モデル化していない(リフォーカスは平均、BM は 1 対 1 対応)。")

    print("\n=== 5. 壊れる条件 (c) 鏡面反射 ===")
    print("  真値 1.30 の面に、視点とともに**別のスロープで動く**ハイライトを足す")
    print("  (鏡面は面そのものではなく光源の鏡像を見せるので視差が違う)。")
    print(f"  {'ハイライトの s':>14}{'振幅':>7}{'焦点度 内':>11}{'EPI 内':>9}"
          f"{'2 眼 内':>10}{'2 眼 外':>10}")
    yy, xx = np.mgrid[0:80, 0:80].astype(np.float64)
    core = np.hypot(yy - 40, xx - 40) < 8
    outer = (np.hypot(yy - 40, xx - 40) > 22) & (np.hypot(yy - 40, xx - 40) < 34)
    spec = {}
    for s_spec, amp in ((1.30, 0.6), (0.0, 0.6), (-2.0, 0.3), (-2.0, 0.6)):
        base = fourier_plane((5, 5), 1.30, tex80)
        for v in range(5):
            for u in range(5):
                hy, hx = 40 + s_spec * (v - 2), 40 + s_spec * (u - 2)
                base[v, u] += amp * np.exp(
                    -((yy - hy) ** 2 + (xx - hx) ** 2) / (2 * 9.0 ** 2))
        dff = lf_focus(base, interp="cubic", edge="wrap")[0]
        ep = lf_epi(base)[0]
        bm = null_two_view(base)
        md = lambda z, m: float(np.median(z[m]))  # noqa: E731
        spec[(s_spec, amp)] = (md(dff, core), md(ep, core), md(bm, core))
        print(f"  {s_spec:>+14.2f}{amp:>7.1f}{md(dff, core):>11.3f}"
              f"{md(ep, core):>9.3f}{md(bm, core):>10.3f}{md(bm, outer):>10.3f}")
    d_in, e_in, b_in = spec[(-2.0, 0.6)]
    print(f"  → ここだけライトフィールドが明確に勝つ。ハイライトが s=-2.0 で動く")
    print(f"     とき、2 眼 BM はハイライト内で {b_in:.3f}(真値 1.30、誤差 "
          f"{100 * abs(b_in / 1.30 - 1):.0f} %)まで崩れるのに、焦点度は "
          f"{d_in:.3f}(誤差 {100 * abs(d_in / 1.30 - 1):.0f} %)。")
    print("     理由: 対応ベースの手法(BM・EPI 構造テンソル)は**測光整合性**を")
    print("     仮定するのでハイライトが仮定を壊す。焦点度が見るのは**鮮鋭度**で、")
    print("     滑らかなハイライト(sigma 9 px)は高周波をほとんど持たないため")
    print("     ピーク位置を動かさない。振幅を半分(0.3)にすると 2 眼は復活する。")
    print("     = 「多視点だから強い」のではなく「見ている量が違うから強い」。")

    print("\n=== 6. 速度(この機械での実測)===")
    lf_big = make_scene((9, 9), seed=1)[0]
    print(f"  入力 {lf_big.shape} = {lf_big.size:,} 要素 ({lf_big.nbytes / 2**20:.1f} MiB)")
    for label, fn in (
            ("EPI 傾き(掃引なし)", lambda: lf_epi(lf_big)),
            (f"焦点度(掃引 {len(SWEEP)} 面, linear)", lambda: lf_focus(lf_big)),
            (f"焦点度(掃引 {len(SWEEP)} 面, cubic)",
             lambda: lf_focus(lf_big, interp="cubic")),
            ("2 眼 BM(両翼, 2 枚 + 1 枚)", lambda: null_two_view(lf_big)),
            ("リフォーカス 1 面", lambda: L.lf_refocus(lf_big, 1.0)),
    ):
        t0 = time.perf_counter()
        fn()
        print(f"  {label:<34}{1e3 * (time.perf_counter() - t0):>9.1f} ms")
    print("  → 焦点度は掃引 1 面ごとに 81 視点をシフトして足すので、掃引点数に")
    print("     比例する。EPI 傾きは 1 パスで 1 桁以上速く、2 眼 BM は使う画像が")
    print("     3 枚だけなのでさらに速い。**精度でも 2 眼が勝っている**ので、")
    print("     ランバート面では速度と精度のトレードオフすら成立していない。")

    # ---- 自己検査(速さは assert しない)----------------------------------- #
    # 1. 符号の規約: 整数スロープ + wrap のリフォーカスは厳密に元へ戻る
    assert float(np.abs(back - tex80).max()) < 1e-9, "符号かシフト量の規約が違う"
    assert float(np.abs(wrong - tex80).max()) > 0.05, "符号を反転しても同じ = 検算になっていない"
    # 2. 深度換算は閉形式ちょうど
    assert abs(float(L.lf_disparity_to_depth(1.87, F_PX, BASELINE_MM))
               - F_PX * BASELINE_MM / 1.87) < 1e-9
    # 3. ライトフィールドは定数ゼロ点を大きく上回る
    r_const = slope_err(est["定数(最良)"], gt, clean)[1]
    r_dff = slope_err(est["焦点度(cubic)"], gt, clean)[1]
    r_bm = slope_err(est["2 眼 BM(両翼)"], gt, clean)[1]
    assert r_dff < 0.2 * r_const, "定数ゼロ点すら上回れていない"
    # 4. ただし 2 眼ゼロ点には負ける —— この PoC の正直な結論
    assert r_bm < r_dff, "2 眼ゼロ点に勝ってしまった(結論の書き換えが要る)"
    # 5. 角度分解能を上げると焦点度の誤差は減る(基線に反比例する向き)
    assert rows[9][1] < rows[5][1] < rows[3][1], "基線を伸ばしても改善しない"
    # 6. ★ 整数吸着: 既定 linear は 1.15 を 1.0 側へ引く、cubic は引かない
    lin_115, cub_115 = snap[1.15]
    assert abs(lin_115 - 1.15) > 5.0 * abs(cub_115 - 1.15), \
        "整数吸着が再現しない(op が直った?なら docstring の穴 (a) を消してよい)"
    assert abs(cub_115 - 1.15) < 0.01, "cubic でも合わない = 別の原因がある"
    # 7. 無テクスチャで EPI は 0 へ崩れ、min_energy 既定は何も止めない
    assert abs(tex_break[0.0][1]) < 0.1, "テクスチャ 0 で EPI が 0 へ落ちない"
    assert abs(tex_break[1.0][1] - 1.30) < 0.1, "テクスチャ十分でも EPI が合わない"
    lf_flat = fourier_plane((5, 5), 1.30, np.full((80, 80), 0.5))
    lf_flat = lf_flat + np.random.default_rng(9).normal(0.0, 0.005, lf_flat.shape)
    _, energy_flat = lf_epi(lf_flat)
    assert float((energy_flat <= 1e-10).mean()) == 0.0, \
        "min_energy 既定が何かを止めた(穴 (b) が直った?)"
    assert float(np.median(energy_flat)) > 1e-4, "純ノイズの energy が小さすぎる"
    # 8. 遮蔽境界で誤差が跳ねる
    assert band["0-1"][0] > 4.0 * band["9 以上"][0], "境界で誤差が跳ねない"
    assert band["1-3"][0] > band["5-9"][0], "境界からの距離で誤差が単調に減らない"
    # 9. 鏡面: 焦点度は耐え、対応ベースは壊れる
    d_in, e_in, b_in = spec[(-2.0, 0.6)]
    assert abs(d_in - 1.30) < 0.1, "焦点度が鏡面で壊れた"
    assert abs(b_in - 1.30) > 5.0 * abs(d_in - 1.30), "2 眼が鏡面で壊れない"
    assert abs(spec[(1.30, 0.6)][2] - 1.30) < 0.1, \
        "面と同じ速さで動くハイライトでも壊れる = 鏡面の効果ではない"
    # 10. 掃引点数の上限は 256(深度分解能の天井)
    try:
        L.lf_depth_from_focus(lf_int, np.linspace(0.0, 3.0, 257))
        raise AssertionError("257 面が通ってしまった")
    except ValueError:
        pass
    print("\nPASS")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
