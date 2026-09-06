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
  * 生の plenoptic フレーム(マイクロレンズアレイ式のカメラが出す生画像)を通したい場合、
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

    3D の平面の視差は**画像座標の 1 次関数**になる。平面 n・X = d 上の点は
    X = Z*(x/f, y/f, 1) だから Z*(n1*x + n2*y + n3*f) = d*f、すなわち 1/Z が
    (x, y) の 1 次関数 = s も 1 次関数。だから「傾いた面」は s(x) = s0 + g*x で
    厳密に表せる —— 近似ではない。

この PoC が示すこと:

1. **真値を自分で作る** —— 背景平面・手前平面・傾いた面の 3 層を、層ごとに
   解析的な逆写像で各視点へ描く(傾いた面の逆写像も閉形式: x' = x*(1+g*du)
   + s0*du を解くだけ)。中心視点は恒等写像なので、真値スロープ地図はそのまま
   中心視点座標で書ける。符号の規約は「整数スロープの 1 平面を作って
   ``lf_refocus`` で戻すと元テクスチャに 8.9e-16 で一致、符号を反転すると
   0.38 ずれる」で検算した。
2. **ゼロ点を 2 つ置く** —— (a) 全画素を同じ深度と答える定数推定、しかも
   RMSE を最小にする**最良の**定数(真値の平均。実際には知り得ない = 最強の
   定数)。(b) 同じ光場から**視点を 2 枚だけ**取り出した素のブロック
   マッチング(``stereo.disparity_subpixel``)。
3. **勝敗は設定で入れ替わる、と正直に書く** —— 9x9・``interp="cubic"`` の
   焦点度だけが 2 眼ゼロ点を上回った(スロープ RMSE 0.0153 対 0.0252、1.6 倍)。
   **既定の ``interp="linear"`` では 0.0752 で 2 眼に 3.0 倍負ける**し、
   3x3 / 5x5 では cubic でも負ける。81 視点のうち 2 枚しか使わない手法に
   負けている間は、足りないのはデータではなく推定器である。EPI 傾きは
   どの角度分解能でも 2 眼に負けたままだった。
4. **角度分解能を振る** —— 3x3 / 5x5 / 9x9。基線長が倍なら視差起因の誤差は
   半分、という予測と実測を並べる(焦点度は 3.97 倍 -> 2.59 倍で予測以上、
   EPI 傾きは偏りが支配して**改善しない**)。
5. **壊れる条件** —— 無テクスチャ / 遮蔽境界 / 鏡面反射の 3 つで境界を数字にする。
   鏡面だけは焦点度が圧勝する(誤差 0.4 % 対 2 眼 100 %)—— 多視点だから
   ではなく、見ている量が測光整合性ではなく鮮鋭度だから。

★ この PoC が出した道具の穴(op 本体は直していない):

  (a) **``lf_depth_from_focus`` の既定 ``interp="linear"`` はスロープを整数へ
      吸着させる。** shift-and-add の双 1 次補間は「整数シフトだけボケない」ので、
      焦点尺度のピークが整数スロープへ引き寄せられる。視点を**厳密な Fourier
      シフト**で作って生成側の補間を排除したうえで実測(5x5、80x80、掃引 0.05
      刻み): 真値 1.08 -> 1.0062 / 1.15 -> 1.0118 / 1.30 -> 1.4750 /
      1.85 -> 1.9882。最大 0.175 px/view のずれ = **深度で 12 %**。
      ``interp="cubic"`` を渡すと同じ入力で 1.0765 / 1.1462 / 1.3002 / 1.8538
      (残差 0.005 以下)。主シーンでも RMSE 0.0752 -> 0.0153 と 4.9 倍違う。
      module docstring は「Bilinear resampling blurs … pass ``interp="cubic"``
      when that matters」と書いているが、**深度 op の既定が linear のままで、
      吸着の大きさも書かれていない**。さらに docstring の実測「argmax landed
      exactly on the true slope in 18 of 18」は真値が 0.0/±0.5/±1.0/±1.5/±2.0
      = **すべて掃引格子上の丸い数**で構成されており、整数吸着を原理的に検出
      できない試験だった。cubic は約 4.5 倍遅い(実測 469 ms -> 2093 ms、
      9x9x96x96、掃引 61 面)ので、既定を変えるなら速度の注記も要る。
  (b) **``lf_epi_slope`` の ``min_energy=1e-10`` は既定では何も止めない。**
      テクスチャ 0(振幅 0.005 のセンサノイズだけ)の光場でも energy 中央値は
      6.2e-4 = 既定の 6e6 倍で、**ゲート率 0.0 %**。同時に slope は真値 1.30 に
      対し -0.006 まで崩れる。docstring の「threshold on ``energy`` instead of
      being handed a plausible-looking number」は正しいが、しきい値の目安が
      無く既定値は実質無効 —— 呼び出し側が場面ごとに較正するしかない。
  (c) **``lf_epi_slope`` の偏りはノイズでも増える。** docstring はスロープの
      大きさ由来の偏り(|s|>1 で過小)を正直に開示しているが、SNR 依存は書かれて
      いない。実測(真値 1.30、5x5、ノイズ sigma 0.005 固定): コントラスト
      1.0 で 1.236、0.1 で 0.844、0.03 で 0.195。同じ入力で 2 眼ブロック
      マッチングは 1.302 / 1.311 / 1.363。ノイズは視点ごとに独立で視差 0
      なので、構造テンソルの分母を埋めてスロープを 0 へ引く。
  (d) **``lf_disparity_to_depth`` はスカラを渡すと docstring と違う形を返す。**
      「a scalar in gives a 0-d array out, so downstream code has one type to
      handle」と書いてあるが、実際は ``shape == (1,)``。原因は
      ``_as_float_array`` の ``np.ascontiguousarray`` で、これは 0-d を 1-d へ
      昇格させる。numpy 2.x では ``float(result)`` が
      ``TypeError: only 0-dimensional arrays can be converted to Python
      scalars`` で落ちる(本 PoC を書いていて実際に踏んだ)。
  (e) **(塞がった / 2026-09-06)``stereo.disparity_subpixel`` の RuntimeWarning。**
      以前は ``np.where(denom > 1e-12, 0.5 * (cm - cp) / denom, 0.0)`` が
      **両枝を評価する**ため、``denom == 0`` の画素(平坦領域)で
      「invalid value encountered in divide」が漏れていた。値は捨てられるので
      結果は正しく、汚れるのは呼び出し側のログだけ —— という種類の穴。
      いまは ``np.divide(..., out=, where=)`` に替わっていて、この PoC が
      「族の中で不統一」と指摘した ``lightfield.lf_epi_slope`` と同じ形になった。
      最小再現(16x16 の階段画像 2 枚を ``disparity_subpixel(a, b, 8, 5, "ssd")``)
      は第 10 節に残してあり、**警告が戻ってきたら落ちる**向きで固定してある。
  (f) **``MAX_STACK_SLICES = 256`` が深度分解能の天井。** ``lf_depth_from_focus``
      の分解能は掃引点数で決まる op なのに、その上限が 256 面であることは
      docstring に書かれていない(0..3 の範囲なら 0.0118 px/view が下限)。
      なお掃引を 61 点から 241 点へ細かくしても誤差は改善しない(実測 0.0733 ->
      0.0810 で悪化)—— 限界は掃引の粗さではなく (a) の補間だから。
  (g) **同じ族の中で ``edge`` の既定が食い違う。** ``lf_synthesize`` は
      ``edge="wrap"``、``lf_refocus`` / ``lf_depth_from_focus`` は
      ``edge="nearest"``。合成した光場をそのまま深度 op に渡すと境界の扱いが
      黙って入れ替わる。
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
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


def scalar_depth_mm(s):
    """``lf_disparity_to_depth`` をスカラで呼ぶ(穴 (d) を迂回する読み方)。

    docstring は 0-d 配列が返ると書いているが実際は ``shape == (1,)`` なので、
    ``float()`` が numpy 2.x で TypeError になる。``.reshape(-1)[0]`` で読む。
    """
    return float(np.asarray(L.lf_disparity_to_depth(s, F_PX, BASELINE_MM)).reshape(-1)[0])


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


def null_block_match(lf, *, block=7, method="ssd", wings="one"):
    """ゼロ点 B: 同じ光場から**視点を 2 枚だけ**使う素のブロックマッチング。

    中心視点 (vc, uc) を基準に、水平方向の端視点 u=0 と対応を取る。
    ``stereo`` の規約は ``L[y, x] == R[y, x - d]`` なので、中心視点を L、
    u=0 の視点を R に置くと ``d = s * uc`` がそのまま出る。真値地図は中心視点
    座標なので、基準フレームを合わせるために端視点どうし(基線 U-1)ではなく
    中心 - 端(基線 uc = (U-1)/2)を使う。

    ``wings="both"`` は反対側の翼(列を反転して同じ matcher に通す)も取って
    平均する —— これは**視点 3 枚**なので「2 眼」とは呼ばない。表では別行。
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

    無限遠側に極があるので中央値で見る(平均は 1 画素で発散しうる)。
    """
    z_est = L.lf_disparity_to_depth(np.clip(np.abs(est[mask]), 1e-3, None),
                                    F_PX, BASELINE_MM)
    z_gt = slope_to_depth_mm(gt[mask])
    return float(np.median(np.abs(z_est - z_gt) / z_gt) * 100.0)


def region_masks(gt, border=14, clean_dist=8, edge_dist=3):
    """内側 / 深度不連続から離れた清浄域 / 遮蔽境界 と、不連続までの距離。"""
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
    print(f"  {'層':>14}{'s [px/view]':>14}{'Z [mm]':>12}")
    for name, s in (("背景平面", 0.43), ("傾いた面 左端", 0.95),
                    ("傾いた面 右端", 1.71), ("手前平面", 1.87)):
        print(f"  {name:>14}{s:>14.2f}{scalar_depth_mm(s):>12.1f}")
    print("  平面の視差は画像座標の 1 次関数(1/Z が 1 次だから)。")
    print("  「傾いた面」は s(x) = s0 + g*x で厳密 —— 近似ではない。")

    # 符号の規約: 生成側(+s で大きい u ほど右へ)と lf_refocus(-s でシフト
    # して足す)が一致していることを、整数スロープの厳密復元で確かめる。
    rng0 = np.random.default_rng(3)
    tex80 = _texture((80, 80), 2.0, rng0)
    lf_int = fourier_plane((5, 5), 1.0, tex80)
    back = L.lf_refocus(lf_int, 1.0, edge="wrap")
    wrong = L.lf_refocus(lf_int, -1.0, edge="wrap")
    print(f"  符号の検算: s=1.0 の 1 平面を lf_refocus(+1.0) で戻すと元テクスチャ"
          f"との最大差 {float(np.abs(back - tex80).max()):.2e}")
    print(f"              符号を反転すると {float(np.abs(wrong - tex80).max()):.2e}"
          f"(取り違えれば一目で分かる)")

    lf9, gt = make_scene((9, 9), noise=0.01, seed=0)
    inner, clean, bnd, dist = region_masks(gt)
    x = np.arange(W)[None, :] * np.ones((H, 1))
    tilt = clean & (gt > 0.9) & (gt < 1.8)
    fit = np.polyfit(x[tilt], gt[tilt], 1)
    print(f"  合成: 光場 {lf9.shape}(センサノイズ sigma 0.01)/ 真値地図 {gt.shape}")
    print(f"  傾いた面の真値を x の 1 次で当てると残差 "
          f"{float(np.abs(np.polyval(fit, x[tilt]) - gt[tilt]).max()):.2e}"
          f"(勾配 {fit[0]:.5f} px/view/px)")

    print("\n=== 2. ゼロ点 —— 定数と 2 眼ブロックマッチングを上回るか(9x9)===")
    est = {}
    est["定数(最良・1 枚)"] = null_constant(gt, clean)
    est["BM(2 枚)"] = null_block_match(lf9)
    est["BM(3 枚・両翼平均)"] = null_block_match(lf9, wings="both")
    est["EPI 傾き(81 枚)"] = lf_epi(lf9)[0]
    est["焦点度 既定 linear(81 枚)"] = lf_focus(lf9)[0]
    est["焦点度 cubic(81 枚)"] = lf_focus(lf9, interp="cubic")[0]
    print(f"  評価域 = 深度不連続から 8 px 以上離れた内側 {int(clean.sum())} 画素")
    print(f"  {'手法':>26}{'MAE':>9}{'RMSE':>9}{'偏り':>9}{'深度誤差 中央値':>17}")
    rmse = {}
    for name, e in est.items():
        mae, r, bias = slope_err(e, gt, clean)
        rmse[name] = r
        print(f"  {name:>26}{mae:>9.4f}{r:>9.4f}{bias:>+9.4f}"
              f"{depth_rel_err(e, gt, clean):>16.2f}%")
    print("  → 単位は px/view。定数ゼロ点の RMSE は真値の標準偏差そのもの。")
    print(f"  → 定数ゼロ点に対しては "
          f"{rmse['定数(最良・1 枚)'] / rmse['焦点度 cubic(81 枚)']:.0f} 倍。"
          f"「深度らしきものが出た」で満足しないための下限は越えている。")
    print(f"  → 2 眼ゼロ点(視点 2 枚)に対しては、**cubic でようやく "
          f"{rmse['BM(2 枚)'] / rmse['焦点度 cubic(81 枚)']:.1f} 倍**。")
    print(f"     既定の linear のままだと逆に "
          f"{rmse['焦点度 既定 linear(81 枚)'] / rmse['BM(2 枚)']:.1f} 倍**負ける**"
          f"(整数吸着 = 4 章)。EPI 傾きは "
          f"{rmse['EPI 傾き(81 枚)'] / rmse['BM(2 枚)']:.1f} 倍負けたまま。")
    print("     81 視点のうち 2 枚しか使わない手法と競っている時点で、足りない")
    print("     のはデータではなく推定器の方 —— 少なくともランバートで十分に")
    print("     テクスチャのある面では。")
    # 図: 3 層シーンと、推定と、その差。差は評価域の外(境界)で大きい。
    # パネルは 96 px しかないので、題は短く(長いと注釈 op が拒否する)。
    dff_cub = est["焦点度 cubic(81 枚)"]
    figs.save_grid("scene_and_depth",
                   [lf9[4, 4], gt, dff_cub, dff_cub - gt],
                   ["中心視点", "真値 s", "焦点度 cubic", "推定−真値"],
                   title="3 層シーンとスロープ地図 [px/view]",
                   signed=[False, False, False, True],
                   caption="差が立つのは深度不連続の縁だけ(5-b で距離ごとに数える)。")

    print("\n=== 3. 角度分解能 —— 基線が倍なら誤差は半分か ===")
    print(f"  {'角度':>8}{'基線 [step]':>12}{'EPI 傾き':>11}{'焦点度 cubic':>14}"
          f"{'BM 2 枚':>10}{'焦点度の改善比':>16}")
    prev = None
    rows = {}
    for ang in (3, 5, 9):
        lf = lf9 if ang == 9 else make_scene((ang, ang), noise=0.01, seed=0)[0]
        r_epi = slope_err(lf_epi(lf)[0], gt, clean)[1]
        r_dff = slope_err(lf_focus(lf, interp="cubic")[0], gt, clean)[1]
        r_bm = slope_err(null_block_match(lf), gt, clean)[1]
        ratio = (prev / r_dff) if prev else float("nan")
        rows[ang] = (r_epi, r_dff, r_bm)
        print(f"  {ang}x{ang:<6}{(ang - 1) / 2.0:>12.1f}{r_epi:>11.4f}"
              f"{r_dff:>14.4f}{r_bm:>10.4f}{ratio:>16.2f}")
        prev = r_dff
    print("  → 予測: 視差の推定精度が px 単位で一定なら、スロープの誤差は基線に")
    print("     反比例する。基線を倍にするごとに改善比 2.0 が出れば予測どおり。")
    print("  → 焦点度は 3.97 -> 2.59 で**予測より速く**良くなる。基線だけでなく")
    print("     足し合わせる視点数も 9 -> 25 -> 81 と増えるので当然ではある。")
    print("  → 2 眼 BM は 5x5 -> 9x9 で頭打ちになる(基線は倍でも改善は 1.3 倍)。")
    print("     傾いた面が窓の中で変化する分の誤差は基線を伸ばしても消えないから。")
    print("     **順位が入れ替わるのは 9x9 だけ** —— 3x3 / 5x5 では 2 眼が勝つ。")
    print("  → EPI 傾きは予測に従わない。視点を増やしても良くならず、むしろ悪化")
    print("     する。分散ではなく偏りだから(docstring の |s|>1 で過小評価)。")

    print("\n=== 4. ★ 焦点度は整数スロープへ吸着する(道具の穴 (a))===")
    print("  視点は**厳密な Fourier シフト**で作る(生成側の補間をゼロにして、")
    print("  ボケが op 側のものだと確定させる)。5x5、80x80、掃引 0.05 刻み。")
    print(f"  {'真値':>8}{'linear(既定)':>16}{'cubic':>10}{'EPI':>9}{'BM 2 枚':>10}")
    snap = {}
    for s_true in (1.00, 1.08, 1.15, 1.30, 1.85):
        lf = fourier_plane((5, 5), s_true, tex80)
        i = (slice(14, -14), slice(14, -14))
        lin = float(np.median(lf_focus(lf, edge="wrap")[0][i]))
        cub = float(np.median(lf_focus(lf, interp="cubic", edge="wrap")[0][i]))
        ep = float(np.median(lf_epi(lf)[0][i]))
        bm = float(np.median(null_block_match(lf)[i]))
        snap[s_true] = (lin, cub)
        print(f"  {s_true:>8.2f}{lin:>16.4f}{cub:>10.4f}{ep:>9.4f}{bm:>10.4f}")
    s_axis = sorted(snap)
    figs.save_plot("focus_snapping",
                   [("真値(恒等)", s_axis, s_axis),
                    ("linear(既定)", s_axis, [snap[s][0] for s in s_axis]),
                    ("cubic", s_axis, [snap[s][1] for s in s_axis])],
                   xlabel="真のスロープ [px/view]", ylabel="推定スロープ [px/view]",
                   title="焦点度は整数スロープへ吸着する(既定 linear)",
                   caption="linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。"
                           "cubic は恒等線に乗る。生成側の補間はゼロ(Fourier シフト)。")
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

    print("\n=== 5-a. 壊れる条件: 無テクスチャ ===")
    print("  真値 1.30 の 1 平面(5x5)、センサノイズ sigma 0.005 固定で")
    print("  テクスチャ振幅だけを落とす。SNR = コントラスト / 0.005。")
    print(f"  {'コントラスト':>13}{'SNR':>7}{'焦点度':>9}{'EPI':>9}{'BM 2 枚':>10}"
          f"{'energy':>11}{'ゲート率':>11}")
    tex_break = {}
    for contrast in (1.0, 0.3, 0.1, 0.03, 0.01, 0.0):
        tex = 0.5 + contrast * (tex80 - 0.5)
        lf = fourier_plane((5, 5), 1.30, tex)
        lf = lf + np.random.default_rng(9).normal(0.0, 0.005, lf.shape)
        i = (slice(14, -14), slice(14, -14))
        dff = float(np.median(lf_focus(lf, interp="cubic", edge="wrap")[0][i]))
        sl, energy = lf_epi(lf)
        ep = float(np.median(sl[i]))
        bm = float(np.median(null_block_match(lf)[i]))
        gated = 100.0 * float((energy[i] <= 1e-10).mean())
        tex_break[contrast] = (dff, ep, bm)
        print(f"  {contrast:>13.3f}{contrast / 0.005:>7.0f}{dff:>9.3f}{ep:>9.3f}"
              f"{bm:>10.3f}{float(np.median(energy[i])):>11.3g}{gated:>10.1f}%")
    figs.save_table("texture_breakdown",
                    ["コントラスト", "SNR", "焦点度", "EPI", "BM 2 枚"],
                    [["%.3f" % c, "%.0f" % (c / 0.005)]
                     + ["%.3f" % v for v in tex_break[c]]
                     for c in (1.0, 0.3, 0.1, 0.03, 0.01, 0.0)],
                    title="無テクスチャで壊れる順(真値 1.30 px/view)",
                    caption="EPI は SNR 20 で既に -35 %。焦点度は SNR 20 まで"
                            "持ちこたえ、そこから整数 1.0 / 2.0 へ落ちる。")
    print("  → 境界は SNR 20 と SNR 6 の間。EPI 傾きは SNR 20 で既に -35 %、")
    print("     SNR 6 で -85 %。ノイズは視点ごとに独立で視差 0 なので、構造")
    print("     テンソルの分母をノイズが埋めてスロープを 0 へ引く。焦点度は")
    print("     SNR 20 まで持ちこたえ、そこから整数 1.0 / 2.0 へ落ちる。")
    print("  → ★ 穴 (b): ``min_energy=1e-10`` の既定ゲートは**テクスチャ 0 でも")
    print("     0.0 % しか止めない**(純ノイズの energy が既定の 6e6 倍)。")
    print("     confidence は返るが、しきい値は呼び出し側が場面ごとに較正するしかない。")
    try:
        L.lf_disparity_to_depth(np.zeros((4, 4)), F_PX, BASELINE_MM)
        raise AssertionError("視差ゼロが通ってしまった")
    except ValueError:
        print("  → 視差ゼロ(= 本来ゲートすべき画素)を深度へ渡すと ValueError。")
        print("     無言の inf ではないのは正しい。far_depth で明示的に飽和させる。")

    print("\n=== 5-b. 壊れる条件: 遮蔽境界 ===")
    print("  主シーン(9x9)で、深度不連続からの距離ごとに誤差を測る。")
    print(f"  {'距離 [px]':>11}{'画素数':>8}{'焦点度 cubic':>14}{'EPI':>9}{'BM 2 枚':>10}")
    dff9 = est["焦点度 cubic(81 枚)"]
    epi9 = est["EPI 傾き(81 枚)"]
    bm9 = est["BM(2 枚)"]
    band = {}
    for lo, hi, label in ((0, 1, "0-1"), (1, 3, "1-3"), (3, 5, "3-5"),
                          (5, 9, "5-9"), (9, 1e9, "9 以上")):
        m = inner & (dist >= lo) & (dist < hi)
        vals = [slope_err(e, gt, m)[1] for e in (dff9, epi9, bm9)]
        band[label] = vals
        print(f"  {label:>11}{int(m.sum()):>8}{vals[0]:>14.3f}{vals[1]:>9.3f}"
              f"{vals[2]:>10.3f}")
    labels = ("0-1", "1-3", "3-5", "5-9", "9 以上")
    d_rep = [0.5, 2.0, 4.0, 7.0, 12.0]      # 帯の代表距離(9 以上は 12 px で置く)
    figs.save_plot("occlusion_bands",
                   [(nm, d_rep, [band[k][i] for k in labels])
                    for i, nm in enumerate(("焦点度 cubic", "EPI 傾き", "BM 2 枚"))],
                   xlabel="深度不連続からの距離 [px](帯の代表値)",
                   ylabel="スロープ RMSE [px/view]",
                   title="遮蔽境界の影響半径",
                   caption="境界から 5 px 離れれば内側の水準に戻る。影響半径は"
                           "開口の見込み視差(最大 7.5 px)と同じ桁。")
    print(f"  → 境界に接する画素(0-1 px)の誤差は内側(9 px 以上)の "
          f"{band['0-1'][0] / band['9 以上'][0]:.0f} 倍(焦点度)/ "
          f"{band['0-1'][2] / band['9 以上'][2]:.0f} 倍(2 眼)。")
    print("     境界から 5 px 離れれば内側の水準に戻る。影響半径は開口の見込み")
    print("     視差(最大 s*(U-1)/2 = 7.5 px)と同じ桁で、どの手法も遮蔽を")
    print("     モデル化していない(リフォーカスは平均、BM は 1 対 1 対応)。")
    print("     ライトフィールドの遮蔽ロバスト性は lf_synthetic_aperture の")
    print("     median 縮約の側にあり、**深度 op には入っていない**。")

    print("\n=== 5-c. 壊れる条件: 鏡面反射 ===")
    print("  真値 1.30 の面(5x5)に、視点とともに**別のスロープで動く**")
    print("  ハイライトを足す(鏡面は面ではなく光源の鏡像を見せるので視差が違う)。")
    print("  ハイライトは sigma 6 px のガウス。振幅はテクスチャの全振幅 1.0 に対する比。")
    print(f"  {'ハイライトの s':>15}{'振幅':>7}{'焦点度 内':>12}{'EPI 内':>10}"
          f"{'BM 内':>10}{'BM 外':>10}")
    yy, xx = np.mgrid[0:80, 0:80].astype(np.float64)
    core = np.hypot(yy - 40, xx - 40) < 8
    outer = (np.hypot(yy - 40, xx - 40) > 22) & (np.hypot(yy - 40, xx - 40) < 34)
    spec = {}
    for s_spec, amp in ((1.30, 1.0), (-2.0, 0.3), (-2.0, 0.6), (-2.0, 1.0)):
        lf = fourier_plane((5, 5), 1.30, tex80)
        for v in range(5):
            for u in range(5):
                hy, hx = 40 + s_spec * (v - 2), 40 + s_spec * (u - 2)
                lf[v, u] += amp * np.exp(
                    -((yy - hy) ** 2 + (xx - hx) ** 2) / (2 * 6.0 ** 2))
        dff = lf_focus(lf, interp="cubic", edge="wrap")[0]
        ep = lf_epi(lf)[0]
        bm = null_block_match(lf)
        md = lambda z, m: float(np.median(z[m]))  # noqa: E731
        spec[(s_spec, amp)] = (md(dff, core), md(ep, core), md(bm, core))
        print(f"  {s_spec:>+15.2f}{amp:>7.1f}{md(dff, core):>12.3f}"
              f"{md(ep, core):>10.3f}{md(bm, core):>10.3f}{md(bm, outer):>10.3f}")
    d_in, e_in, b_in = spec[(-2.0, 1.0)]
    print(f"  → ここだけライトフィールドが圧勝する。ハイライトが s=-2.0 で動き")
    print(f"     振幅 1.0 のとき、2 眼 BM はハイライト内で {b_in:.3f}(真値 1.30、")
    print(f"     誤差 {100 * abs(b_in / 1.30 - 1):.0f} %)、EPI 傾きは {e_in:.3f} まで"
          f"崩れるのに、焦点度は {d_in:.3f}(誤差 {100 * abs(d_in / 1.30 - 1):.1f} %)。")
    print("     理由: 対応ベースの手法(BM・EPI 構造テンソル)は**測光整合性**を")
    print("     仮定するのでハイライトが仮定を壊す。焦点度が見るのは**鮮鋭度**で、")
    print("     滑らかなハイライトは高周波をほとんど持たずピーク位置を動かさない。")
    print("     = 「多視点だから強い」のではなく「見ている量が違うから強い」。")
    print("     面と同じ速さで動くハイライト(s=+1.30)なら誰も壊れない = 効いて")
    print("     いるのは輝度の変化ではなく**視差の食い違い**だと確かめられる。")

    print("\n=== 6. 速度(この機械での実測)===")
    lf_big = make_scene((9, 9), seed=1)[0]
    print(f"  入力 {lf_big.shape} = {lf_big.size:,} 要素 "
          f"({lf_big.nbytes / 2 ** 20:.1f} MiB)")
    ms = {}
    for label, fn in (
            ("EPI 傾き(掃引なし)", lambda: lf_epi(lf_big)),
            (f"焦点度(掃引 {len(SWEEP)} 面, linear)", lambda: lf_focus(lf_big)),
            (f"焦点度(掃引 {len(SWEEP)} 面, cubic)",
             lambda: lf_focus(lf_big, interp="cubic")),
            ("BM 2 枚", lambda: null_block_match(lf_big)),
            ("リフォーカス 1 面", lambda: L.lf_refocus(lf_big, 1.0)),
    ):
        t0 = time.perf_counter()
        fn()
        ms[label] = 1e3 * (time.perf_counter() - t0)
        print(f"  {label:<32}{ms[label]:>9.1f} ms")
    print("  → 焦点度は掃引 1 面ごとに 81 視点をシフトして足すので、掃引点数に")
    print("     比例する。EPI 傾きは 1 パスで 1 桁以上速い。")
    cubic_cost = (ms[f"焦点度(掃引 {len(SWEEP)} 面, cubic)"]
                  / ms[f"焦点度(掃引 {len(SWEEP)} 面, linear)"])
    print(f"  → ★ 精度のために要る cubic は linear の {cubic_cost:.1f} 倍遅い。")
    print("     既定を cubic にするなら、この代償も併記が要る。")
    print("  → 2 眼 BM は画像 2 枚しか触らないので 2 桁速い。9x9 でようやく")
    print("     精度が並ぶことを思うと、**単一露光であること**と**リフォーカス**")
    print("     こそがライトフィールドの取り分で、深度の数字そのものではない。")

    # ---- 自己検査(速さは assert しない)----------------------------------- #
    # 1. 符号の規約: 整数スロープ + wrap のリフォーカスは厳密に元へ戻る
    assert float(np.abs(back - tex80).max()) < 1e-9, "符号かシフト量の規約が違う"
    assert float(np.abs(wrong - tex80).max()) > 0.05, \
        "符号を反転しても同じ = 検算になっていない"
    # 2. 深度換算は閉形式ちょうど
    assert abs(scalar_depth_mm(1.87) - F_PX * BASELINE_MM / 1.87) < 1e-9
    # 2b. ★ 穴 (d): docstring は 0-d と言うが実際は (1,)
    assert np.asarray(L.lf_disparity_to_depth(1.87, F_PX, BASELINE_MM)).shape == (1,), \
        "0-d が返るようになった = 穴 (d) が直った(docstring の記述を消してよい)"
    # 3. ライトフィールドは定数ゼロ点を大きく上回る
    assert rmse["焦点度 cubic(81 枚)"] < 0.1 * rmse["定数(最良・1 枚)"], \
        "定数ゼロ点すら 10 倍上回れていない"
    # 4. 2 眼ゼロ点との勝敗 —— この PoC の正直な結論そのもの
    assert rmse["焦点度 cubic(81 枚)"] < rmse["BM(2 枚)"], \
        "9x9 + cubic でも 2 眼に勝てない(結論の書き換えが要る)"
    assert rmse["焦点度 既定 linear(81 枚)"] > 2.0 * rmse["BM(2 枚)"], \
        "既定 linear が 2 眼に勝った = 穴 (a) が直った?"
    assert rmse["EPI 傾き(81 枚)"] > rmse["BM(2 枚)"], "EPI 傾きが 2 眼に勝った"
    # 5. 角度分解能: 焦点度は基線に応じて改善、EPI 傾きはしない
    assert rows[9][1] < rows[5][1] < rows[3][1], "基線を伸ばしても焦点度が改善しない"
    assert rows[3][2] < rows[3][1], "3x3 では 2 眼が勝つはず(逆転は 9x9 だけ)"
    assert rows[9][0] > 0.8 * rows[3][0], "EPI 傾きが基線で改善してしまった"
    # 6. ★ 穴 (a): 既定 linear は 1.15 を 1.0 側へ引く、cubic は引かない
    lin_115, cub_115 = snap[1.15]
    assert abs(lin_115 - 1.15) > 5.0 * abs(cub_115 - 1.15), \
        "整数吸着が再現しない(op が直った?なら docstring の穴 (a) を消してよい)"
    assert abs(cub_115 - 1.15) < 0.01, "cubic でも合わない = 別の原因がある"
    assert abs(snap[1.00][0] - 1.00) < 1e-3, "整数スロープは既定でも当たるはず"
    # 7. 無テクスチャで EPI は 0 へ崩れ、min_energy 既定は何も止めない
    assert abs(tex_break[0.0][1]) < 0.1, "テクスチャ 0 で EPI が 0 へ落ちない"
    assert abs(tex_break[1.0][1] - 1.30) < 0.1, "テクスチャ十分でも EPI が合わない"
    lf_flat = fourier_plane((5, 5), 1.30, np.full((80, 80), 0.5))
    lf_flat = lf_flat + np.random.default_rng(9).normal(0.0, 0.005, lf_flat.shape)
    _, energy_flat = lf_epi(lf_flat)
    assert float((energy_flat <= 1e-10).mean()) == 0.0, \
        "min_energy 既定が何かを止めた = 穴 (b) が直った?"
    assert float(np.median(energy_flat)) > 1e-5, "純ノイズの energy が小さすぎる"
    # 8. 遮蔽境界で誤差が跳ね、離れると戻る
    assert band["0-1"][0] > 4.0 * band["9 以上"][0], "境界で誤差が跳ねない"
    assert band["1-3"][0] > band["5-9"][0] > band["9 以上"][0], \
        "境界からの距離で誤差が単調に減らない"
    # 9. 鏡面: 焦点度は耐え、対応ベースは壊れる
    assert abs(d_in - 1.30) < 0.05, "焦点度が鏡面で壊れた"
    assert abs(b_in - 1.30) > 10.0 * abs(d_in - 1.30), "2 眼が鏡面で壊れない"
    assert abs(spec[(1.30, 1.0)][2] - 1.30) < 0.1, \
        "面と同じ速さで動くハイライトでも壊れる = 鏡面の効果ではない"
    # 10. ★ 穴 (e) は 2026-09-06 に塞がった。**塞がった状態を固定する**側へ
    #     書き換えてある(以前は「警告が出ること」を assert していた)。
    step_a = np.zeros((16, 16))
    step_a[:, 8:] = 1.0
    step_b = np.zeros((16, 16))
    step_b[:, 6:] = 1.0
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        step_out = np.asarray(S.disparity_subpixel(step_a, step_b, 8, 5, "ssd"))
    leaked = [str(c.message) for c in caught
              if issubclass(c.category, RuntimeWarning) and "divide" in str(c.message)]
    assert not leaked, "平坦領域の divide 警告が戻ってきた: %s" % leaked[:2]
    # 警告を消しただけで値まで変わっていないこと(where= の外は 0 のまま)。
    assert np.all(np.isfinite(step_out)), "警告は消えたが NaN/Inf が出ている"
    # 11. 掃引点数の上限は 256(深度分解能の天井、穴 (f))
    try:
        L.lf_depth_from_focus(lf_int, np.linspace(0.0, 3.0, 257))
        raise AssertionError("257 面が通ってしまった")
    except ValueError:
        pass
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
