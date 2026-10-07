# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pivops —— 粒子画像流速測定(PIV)。画像対から密な変位場を出す。

## この族は何をする道具箱か

**2 枚の画像から、どこがどれだけ動いたかを測る**層です。入力はトレーサ粒子を
写した画像対(``(H, W)`` の実数配列 2 枚)、出力は窓ごとの変位ベクトル場
``(2, h, w)``(成分は ``(dy, dx)``、単位は画素)。流体計測(PIV)が本来の用途
ですが、原理は相互相関なので、粒子でなくても模様があるものなら動きが取れます。

## なぜこの族を足したか —— 在庫を数えた結果

2026-09-06 に型付きカタログ全体を走査したところ、**画像対から密な変位を出す op
は 1 つも無い**ことが分かりました。近いものはあります:

* ``scene_flow_lk`` —— Lucas-Kanade ですが **3 次元の体積用**(``(3,D,H,W)``)。
* ``estimate_flow`` / ``nearest_neighbor_flow`` —— **点群同士**のシーンフロー。
* ``correlation_score`` —— 体積同士の相関スカラ 1 個。
* ``features.match_keypoints`` —— **疎な**対応点。

つまり「2 枚の平面画像 → 密な変位場」だけが空いていました。``flow_dense`` 型は
存在しますが述語が ``(3, D, H, W)`` 限定で、作る op は ``scene_flow_lk`` の 1 本
だけです。本族はそこに :data:`FLOW2D_SHAPE` の 2 次元版を足します。

## 正しさの確かめ方 —— 真値は定義から作る

PIV は「それらしいベクトル図」が必ず出ます。目視は検証になりません。この族は
**変位場を先に決めて画像を作る**ので、真値が定義そのものです
(``tests/test_pivops.py``):

=================  ==============================  ==========================
変位場             閉形式                          実測(多段 64→32、320x320)
=================  ==============================  ==========================
一様並進           どの窓でも同じ (dy, dx)         偏り 0.003 px 以下、RMS 0.06
剛体回転 ω=0.01    渦度 = -2ω、発散 = 0            渦度 -0.01997、発散 -0.00006
一様膨張 s=0.01    発散 = 2s、渦度 = 0             発散 +0.01985、渦度 +0.00009
単純せん断 g=0.02  渦度 = g、発散 = 0              渦度 +0.01996、発散 -0.00003
=================  ==============================  ==========================

回転の渦度が**負**なのは規約どおりです。``(dy, dx) = (ω(c-cx), -ω(r-cy))`` は
画面上では時計回りに見える場で、この定義では負になります。テストを書いたとき
最初に符号を取り違えたのは**テストの側**でした(実装ではなく)。

さらに **独立な検算**を 1 本持ちます —— 非圧縮の流れなら発散が 0 のはずで、
真値と比べる評価とは別の経路で誤差の大きさが分かります(上の表の回転・せん断で
発散が 1e-4 台に収まっていることが、その検算が働いている証拠)。

## 既知の系統誤差(出るはずのものが出るか)

**ピークロッキング**: 相関ピークのサブピクセル推定は、真の変位の小数部が 0 や
0.5 のときに引き寄せられる偏りを持ちます。これは PIV の教科書的な系統誤差で、
:func:`piv_peak_locking` はその強さを測ります。**出ないほうがおかしい**ので、
テストは「小さいこと」ではなく「測れること」を固定しています。

## 単位と規約(取り違えると静かに間違う)

* 変位の単位は **画素/フレーム**。物理速度 [m/s] が欲しければ、画素寸法と
  フレーム間隔を掛ける —— :func:`piv_to_velocity` が**両方を必須引数**として
  受け取ります(既定値を置くと単位事故が既定になる)。
* 成分順は **(dy, dx)**。``dy`` は**行が増える向き**(画像の下向き)が正。
  ``scene_flow_lk`` の ``(dz, dy, dx)`` と同じ並びです。
* 渦度は画像座標系で ``d(dx)/dy - d(dy)/dx`` と定義します(行が下向きなので、
  この符号で**反時計回りが正**になる)。数学の xy 座標と行列の行方向は上下が
  逆なので、ここを曖昧にすると渦の向きが黙って反転します。
* 変位場は窓の中心に載ります。中心の座標は :func:`piv_cross_correlate` が返す
  情報表の ``rows`` / ``cols`` にあり、画像座標での位置です。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "FLOW2D_SHAPE", "PEAK_MODES", "WINDOW_FUNCS", "OUTLIER_FILL",
    "NORMALIZE_MODES",
    "piv_synth_particles", "piv_synth_pair", "piv_synth_sequence",
    "piv_cross_correlate", "piv_multipass",
    "piv_outlier_mask", "piv_replace_outliers",
    "piv_vorticity", "piv_divergence", "piv_flow_magnitude",
    "piv_sample_at_windows", "piv_error_stats", "piv_peak_locking",
    "piv_to_velocity",
    # --- 派生(2026-09-06 追加)---
    "piv_velocity_gradient", "piv_q_criterion", "piv_swirling_strength",
    "piv_strain_rate", "piv_flow_to_rgbimage", "piv_line_integral_convolution",
    "piv_deform_pass", "piv_ensemble_correlate", "piv_time_statistics",
    # --- 矢印図と流線(2026-10-03 追加)---
    "piv_streamlines", "piv_quiver", "piv_streamline_image",
]

#: 変位場の形の約束。``(2, h, w)`` で成分は ``(dy, dx)``、単位は画素/フレーム。
#: ``flow_dense``(``(3, D, H, W)`` の 3-D シーンフロー)とは**別の型**として
#: 扱う —— 形が違うので取り違えれば例外にはなるが、型の名前を共有すると
#: 台帳の宣言が嘘になる(3 成分を約束しているところへ 2 成分を返すことになる)。
FLOW2D_SHAPE = "(2, h, w) with components (dy, dx) in pixels per frame"

#: サブピクセル推定の方法。
#:
#: * ``"gauss3"``(既定) —— ピークとその両隣の**対数**を放物線で当てる。
#:   粒子像がガウス形なら相関ピークもガウス形になるので、これが素直。
#: * ``"parabolic"`` —— 対数を取らずに放物線を当てる。ピークロッキングが強い。
#: * ``"centroid"`` —— 3 点の重心。最も粗い。
#:
#: 3 つ並べてあるのは選択肢を増やすためではなく、**系統誤差の違いを測れる**
#: ようにするため(``piv_peak_locking`` で比較する)。
PEAK_MODES = ("gauss3", "parabolic", "centroid")

#: 相関の正規化。``"overlap"`` は窓関数の自己相関で割って、窓のずれに伴う
#: 重なり減少ぶんを打ち消す(零方向への偏りが消える)。``search_limit`` と
#: **必ず対で使う** —— 単独だと縁で 0 に近い値で割ることになり、実測で誤差が
#: 23 倍に悪化した(``piv_cross_correlate`` の表)。
NORMALIZE_MODES = ("overlap", "none")

#: 窓関数。``"hann"`` は窓の縁の不連続が相関に持ち込むリークを減らすが、
#: 有効な粒子数も減らす(縁の粒子の寄与が落ちる)ので万能ではない。
WINDOW_FUNCS = ("none", "hann")

#: 外れ値を埋める方法。``"nan"`` は**埋めない**(欠測として残す)。
OUTLIER_FILL = ("median", "linear", "nan")

_EPS = 1e-12


# =========================================================================
# 入力の検証(fail-closed)
# =========================================================================

def _img(a, name="image"):
    x = np.asarray(a, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError(f"{name} must be a 2-D (H, W) image, got shape {x.shape}")
    if x.size == 0:
        raise ValueError(f"{name} is empty")
    if not np.all(np.isfinite(x)):
        raise ValueError(f"{name} contains non-finite values; PIV has no meaning on them")
    return x


def _flow(f, name="flow"):
    x = np.asarray(f, dtype=np.float64)
    if x.ndim != 3 or x.shape[0] != 2:
        raise ValueError(
            f"{name} must be {FLOW2D_SHAPE}, got shape {x.shape}. "
            "3-D scene flow (3, D, H, W) belongs to scene_flow_lk, not here")
    return x


def _choice(v, name, allowed):
    if v not in allowed:
        raise ValueError(f"{name} must be one of {allowed}, got {v!r}")
    return v


def _positive(v, name):
    x = float(v)
    if not np.isfinite(x) or x <= 0:
        raise ValueError(f"{name} must be a finite positive number, got {v}")
    return x


def _window(window, shape, name="window"):
    w = int(window)
    if w < 8:
        raise ValueError(f"{name} must be >= 8 px (a smaller window has no peak to fit), got {w}")
    if w % 2:
        raise ValueError(f"{name} must be even so the zero shift sits on a sample, got {w}")
    if w > min(shape):
        raise ValueError(f"{name}={w} does not fit in an image of shape {shape}")
    return w


# =========================================================================
# 1. 合成 —— 真値を定義から作る
# =========================================================================

def piv_synth_particles(shape, density=0.02, diameter_px=2.5, seed=0,
                        intensity=(0.6, 1.0), background=0.0):
    """トレーサ粒子を撒いた 1 枚を作る。返りは ``(image, positions)``。

    粒子はガウス輝点(直径 = 1/e^2 幅ではなく**標準偏差の 2 倍**を
    ``diameter_px`` と呼ぶ、PIV の慣行)。位置は連続値なので、サブピクセルの
    真値を持つ画像が作れる。

    ``density`` は 1 画素あたりの粒子数。PIV の経験則では**窓あたり 5-10 個**が
    目安で、32x32 窓なら 0.005-0.01 に当たる。少なすぎると相関ピークが立たず、
    多すぎると粒子像が重なって個々の対応が失われる。

    Args:
        shape: ``(H, W)``。
        density: 画素あたりの粒子数(> 0)。
        diameter_px: 粒子像の直径 [px] (> 0)。
        seed: 乱数種。
        intensity: 粒子の明るさの範囲 ``(lo, hi)``。
        background: 一様な下駄。
    Returns:
        ``(image (H, W) float64, positions (N, 2) の (row, col))``。
    """
    h, w = (int(shape[0]), int(shape[1]))
    if h < 8 or w < 8:
        raise ValueError(f"shape must be at least (8, 8), got {shape}")
    d = _positive(diameter_px, "diameter_px")
    dens = _positive(density, "density")
    lo, hi = float(intensity[0]), float(intensity[1])
    if not (0.0 <= lo <= hi):
        raise ValueError(f"intensity must be 0 <= lo <= hi, got {intensity}")
    rng = np.random.default_rng(int(seed))
    n = max(1, int(round(dens * h * w)))
    # 縁で粒子が欠けると相関にバイアスが乗るので、外側にも撒いておく
    pad = 3.0 * d
    pos = np.column_stack([rng.uniform(-pad, h + pad, n),
                           rng.uniform(-pad, w + pad, n)])
    amp = rng.uniform(lo, hi, n)
    img = _render_particles((h, w), pos, amp, d) + float(background)
    return img, pos


def _render_particles(shape, pos, amp, diameter_px):
    """ガウス輝点を足し込む。粒子ごとに近傍の小窓だけを触る(全画面走査しない)。"""
    h, w = shape
    sigma = diameter_px / 2.0
    r = int(np.ceil(3.0 * sigma))
    img = np.zeros((h, w), np.float64)
    inv = 1.0 / (2.0 * sigma * sigma)
    for (py, px), a in zip(pos, amp):
        y0, y1 = int(np.floor(py)) - r, int(np.floor(py)) + r + 1
        x0, x1 = int(np.floor(px)) - r, int(np.floor(px)) + r + 1
        y0c, y1c, x0c, x1c = max(0, y0), min(h, y1), max(0, x0), min(w, x1)
        if y0c >= y1c or x0c >= x1c:
            continue
        yy = np.arange(y0c, y1c)[:, None] - py
        xx = np.arange(x0c, x1c)[None, :] - px
        img[y0c:y1c, x0c:x1c] += a * np.exp(-(yy * yy + xx * xx) * inv)
    return img


def piv_synth_pair(shape, displacement, density=0.02, diameter_px=2.5, seed=0,
                   noise_sigma=0.0, intensity=(0.6, 1.0), background=0.0):
    """既知の変位場を持つ画像対を作る。返りは ``(image_a, image_b, truth)``。

    **粒子を動かしてから 2 枚目を描く**(1 枚目を補間で歪めるのではない)。
    補間で作ると、補間の平滑化が「PIV が当てやすい絵」を作ってしまい、
    自分の実装を自分に有利な入力で測ることになる。

    Args:
        shape: ``(H, W)``。
        displacement: 変位の与え方。次のいずれか。

            * 長さ 2 の列 —— 一様並進 ``(dy, dx)`` [px]。
            * ``callable(rows, cols) -> (dy, dx)`` —— 位置に依存する場。
              引数は粒子の連続座標の配列。
        density / diameter_px / seed / intensity / background: :func:`piv_synth_particles` と同じ。
        noise_sigma: 2 枚それぞれに独立に足す加法ガウス雑音の標準偏差。
    Returns:
        ``(a (H, W), b (H, W), truth (2, H, W))``。``truth`` は**画素ごと**の
        真の変位で、窓の格子に落とすには :func:`piv_sample_at_windows` を使う。
    """
    h, w = (int(shape[0]), int(shape[1]))
    a, pos = piv_synth_particles((h, w), density, diameter_px, seed,
                                 intensity, background)
    rng = np.random.default_rng(int(seed) + 1)
    amp = rng.uniform(float(intensity[0]), float(intensity[1]), len(pos))
    # 1 枚目と同じ粒子・同じ明るさで描き直す(明るさが変わると相関が落ちる)
    a = _render_particles((h, w), pos, amp, diameter_px) + float(background)

    dy, dx = _displacement_at(displacement, pos[:, 0], pos[:, 1])
    pos2 = np.column_stack([pos[:, 0] + dy, pos[:, 1] + dx])
    b = _render_particles((h, w), pos2, amp, diameter_px) + float(background)

    gy, gx = np.mgrid[0:h, 0:w].astype(np.float64)
    ty, tx = _displacement_at(displacement, gy.ravel(), gx.ravel())
    truth = np.stack([np.reshape(ty, (h, w)), np.reshape(tx, (h, w))])

    s = float(noise_sigma)
    if s < 0:
        raise ValueError(f"noise_sigma must be >= 0, got {noise_sigma}")
    if s > 0:
        a = a + rng.normal(0.0, s, a.shape)
        b = b + rng.normal(0.0, s, b.shape)
    return a, b, truth


def piv_synth_sequence(shape, displacement, n_frames=8, density=0.02,
                       diameter_px=2.5, seed=0, noise_sigma=0.0,
                       intensity=(0.6, 1.0), background=0.0, jitter=0.0):
    """同じ粒子を繰り返し動かした画像列。返りは ``(frames, truth)``。

    :func:`piv_synth_pair` が 2 枚なのに対し、こちらは **1 つの流れを追い続けた
    列**を作る。アンサンブル相関と時間統計はこれでないと確かめられない ——
    独立な対を並べたものを列と呼ぶと、隣り合う 2 枚に対応関係が無く、
    統計が無意味になる(実測: 平均 0.73 px に対して変動の RMS が 4.05 px という、
    流れではなく作り方を測った数字が出た)。

    Args:
        shape: ``(H, W)``。
        displacement: 1 コマあたりの変位(:func:`piv_synth_pair` と同じ形式)。
        n_frames: コマ数(2 以上)。
        jitter: コマごとに**場全体へ**加える乱れの標準偏差 [px]。0 なら定常流。
            時間統計(変動・レイノルズ応力)を試すにはここを 0 より大きくする。

            ★ 粒子ごとに独立な乱れではなく**コマごとに一つ**の乱れにしてある。
            粒子ごとに振ると、窓の中で平均されて N の平方根ぶん小さくなり、
            仕込んだ値と測った値が合わない(実測: 仕込み 0.3 に対して 0.15)。
            それは PIV の性質であって間違いではないが、**時間統計の検証には
            使えない**ので、ここは非定常な流れそのものを模す形にした。
        density / diameter_px / seed / noise_sigma / intensity / background:
            :func:`piv_synth_pair` と同じ。
    Returns:
        ``(frames: list of (H, W), truth: (2, H, W))``。``truth`` は
        **1 コマあたり**の平均変位。
    """
    h, w = (int(shape[0]), int(shape[1]))
    n = int(n_frames)
    if n < 2:
        raise ValueError(f"n_frames must be >= 2, got {n_frames}")
    jit = float(jitter)
    if jit < 0:
        raise ValueError(f"jitter must be >= 0, got {jitter}")
    ns = float(noise_sigma)
    if ns < 0:
        raise ValueError(f"noise_sigma must be >= 0, got {noise_sigma}")
    _, pos = piv_synth_particles((h, w), density, diameter_px, seed,
                                 intensity, background)
    rng = np.random.default_rng(int(seed) + 1)
    amp = rng.uniform(float(intensity[0]), float(intensity[1]), len(pos))
    frames = []
    for k in range(n):
        img = _render_particles((h, w), pos, amp, diameter_px) + float(background)
        if ns > 0:
            img = img + rng.normal(0.0, ns, img.shape)
        frames.append(img)
        if k == n - 1:
            break
        dy, dx = _displacement_at(displacement, pos[:, 0], pos[:, 1])
        if jit > 0:                       # コマごとに一つ(場全体が揺れる)
            dy = dy + rng.normal(0.0, jit)
            dx = dx + rng.normal(0.0, jit)
        pos = np.column_stack([pos[:, 0] + dy, pos[:, 1] + dx])
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float64)
    ty, tx = _displacement_at(displacement, gy.ravel(), gx.ravel())
    truth = np.stack([np.reshape(ty, (h, w)), np.reshape(tx, (h, w))])
    return frames, truth


def _displacement_at(displacement, rows, cols):
    """変位の指定を ``(dy, dx)`` の配列に正規化する。"""
    if callable(displacement):
        dy, dx = displacement(np.asarray(rows, np.float64), np.asarray(cols, np.float64))
        dy = np.broadcast_to(np.asarray(dy, np.float64), np.shape(rows)).astype(np.float64)
        dx = np.broadcast_to(np.asarray(dx, np.float64), np.shape(rows)).astype(np.float64)
        return dy, dx
    v = np.asarray(displacement, np.float64)
    if v.shape != (2,):
        raise ValueError(
            "displacement must be a length-2 (dy, dx) or a callable(rows, cols) -> (dy, dx), "
            f"got shape {v.shape}")
    return np.full(np.shape(rows), v[0]), np.full(np.shape(rows), v[1])


# =========================================================================
# 2. 相互相関 —— 本体
# =========================================================================

def piv_cross_correlate(a, b, window=32, overlap=0.5, peak="gauss3",
                        window_func="hann", subtract_mean=True, shift=None,
                        normalize="overlap", search_limit=0.25):
    """窓ごとの相互相関で変位場を出す。返りは ``(flow, info)``。

    各窓で ``FFT`` を 2 回とって共役積の逆変換を取り(循環相関)、最大値の
    位置を整数変位、その周りの 3 点でサブピクセル変位を決める。

    **零方向への偏りとその補正(実測)**: 素の相互相関は変位を**零へ引き寄せる**。
    窓をずらすと重なる領域が減り、相関の値そのものが変位とともに落ちるからで、
    実測でも偏りは変位に比例した(win=32・Hann、``dx`` を 0.5 から 6 px まで
    振って偏り / (d/N) が 1.30, 1.29, 1.28, 1.28, 1.28 —— **傾き一定**)。

    ``normalize="overlap"`` はこれを、**窓関数の自己相関で割る**ことで補正する
    (重なり面積で正規化するのと同じ)。ただし縁では割る量が 0 に近づくので、
    ``search_limit`` で探索範囲を窓の 1/4 に絞るのと**必ず対にする**。実測:

    ===============  ==========  ==========  ==========
    dx [px]          補正なし    補正 + 1/4  補正のみ
    ===============  ==========  ==========  ==========
    1.0 の偏り       -0.0402     -0.0020     -0.2659
    5.0 の偏り       -0.2001     -0.0128     -0.9210
    5.0 の RMS       0.2081      0.0301      4.8881
    ===============  ==========  ==========  ==========

    右端が「探索を絞らずに正規化だけした」場合で、**補正が誤差を 23 倍に悪化
    させる**。片方だけ入れてはいけない、という測定結果をそのまま既定にしてある。

    Args:
        a, b: 画像対 ``(H, W)``。
        window: 窓の一辺 [px]。偶数・8 以上。
        overlap: 窓の重なり率 ``[0, 1)``。0.5 が慣行。
        peak: :data:`PEAK_MODES`。
        window_func: :data:`WINDOW_FUNCS`。
        subtract_mean: 窓ごとに平均を引く(背景の直流成分が中央に巨大な
            ピークを作るのを防ぐ)。**切ると零変位に張り付く**。
        shift: 予測変位 ``(2, h, w)``(多段用)。2 枚目の窓をこの整数量だけ
            ずらして切り出し、残差を測る。
        normalize: ``"overlap"``(既定)か ``"none"``。
        search_limit: 探索する変位の上限を窓の比で与える(既定 0.25 = PIV の
            「1/4 則」)。``None`` で無制限 —— ``normalize="overlap"`` との
            併用は上の表のとおり**悪化する**。
    Returns:
        ``(flow (2, h, w), info)``。``info`` は ``rows`` / ``cols``(窓中心の
        画像座標)、``peak_ratio``(第 1 ピーク / 第 2 ピーク。1 に近いほど
        当てにならない)、``window`` / ``overlap`` / ``peak`` を持つ dict。
    """
    A, B = _img(a, "a"), _img(b, "b")
    if A.shape != B.shape:
        raise ValueError(f"a and b must have the same shape, got {A.shape} and {B.shape}")
    win = _window(window, A.shape)
    ov = float(overlap)
    if not (0.0 <= ov < 1.0):
        raise ValueError(f"overlap must be in [0, 1), got {overlap}")
    _choice(peak, "peak", PEAK_MODES)
    _choice(window_func, "window_func", WINDOW_FUNCS)
    _choice(normalize, "normalize", NORMALIZE_MODES)
    if search_limit is not None:
        lim_frac = float(search_limit)
        if not (0.0 < lim_frac <= 0.5):
            raise ValueError(
                f"search_limit must be in (0, 0.5] or None, got {search_limit}")
    else:
        lim_frac = None

    step = max(1, int(round(win * (1.0 - ov))))
    h, w = A.shape
    rows = np.arange(0, h - win + 1, step)
    cols = np.arange(0, w - win + 1, step)
    if rows.size == 0 or cols.size == 0:
        raise ValueError(f"window={win} with overlap={ov} leaves no window in shape {A.shape}")

    pred = None
    if shift is not None:
        pred = _flow(shift, "shift")
        if pred.shape[1:] != (rows.size, cols.size):
            raise ValueError(
                f"shift must be (2, {rows.size}, {cols.size}) for this window grid, "
                f"got {pred.shape}")
        pred = np.rint(pred).astype(np.int64)

    taper = _taper(win, window_func)
    weight = _overlap_weight(win, taper) if normalize == "overlap" else None
    keep = _search_mask(win, lim_frac)
    flow = np.zeros((2, rows.size, cols.size))
    ratio = np.zeros((rows.size, cols.size))
    for i, r in enumerate(rows):
        for j, c in enumerate(cols):
            wa = A[r:r + win, c:c + win]
            if pred is None:
                sr = sc = 0
            else:
                sr, sc = int(pred[0, i, j]), int(pred[1, i, j])
            # 予測が画像の外を指したら**切り詰める**(nan にしない)。切り詰めた
            # ぶんは残差として測り直されるので測定は成立する。縁の窓を丸ごと
            # 欠測にすると、渦度・発散が縁から内側へ nan で伝播して**場全体が
            # 消える**(実測でそうなった)。
            r2 = min(max(r + sr, 0), h - win)
            c2 = min(max(c + sc, 0), w - win)
            sr, sc = r2 - r, c2 - c
            wb = B[r2:r2 + win, c2:c2 + win]
            dy, dx, pr = _correlate_window(wa, wb, taper, subtract_mean, peak,
                                           weight, keep)
            flow[0, i, j] = dy + sr
            flow[1, i, j] = dx + sc
            ratio[i, j] = pr

    info = {"rows": rows + (win - 1) / 2.0, "cols": cols + (win - 1) / 2.0,
            "peak_ratio": ratio, "window": win, "overlap": ov, "peak": peak,
            "window_func": window_func, "step": step,
            "normalize": normalize, "search_limit": search_limit,
            # ★ 相関の峰が立たない窓(テクスチャが無い・全面一様)は nan を返す
            #   —— 0 を返さないのは「動いていない」と「分からない」を混ぜないため。
            #   だが**何割が nan なのかは返り値からしか分からず**、``flow.mean()``
            #   が nan になって初めて気づく形だった(2026-09-06)。ここで数える。
            #   実測: 一様な背景に 16x16 の四角だけの画像では 98 窓中 16 窓しか
            #   有限にならない(0.163)。全面テクスチャなら 1.000。
            "valid_fraction": float(np.isfinite(flow[0]).mean())}
    return flow, info


def _taper(n, kind):
    if kind == "none":
        return None
    w = np.hanning(n + 2)[1:-1]           # 端が 0 にならない形(有効画素を残す)
    return np.outer(w, w)


def _overlap_weight(n, taper):
    """窓の重み(``taper``、無ければ 1)の自己相関 = ずらしたときの重なり量。

    これで割ると、相関の値が変位とともに落ちるぶんが打ち消され、ピーク位置の
    零方向への偏りが消える。**縁では 0 に近づくので探索範囲の制限と対**。
    """
    m = np.ones((n, n)) if taper is None else taper
    fm = np.fft.rfft2(m)
    w = np.fft.fftshift(np.fft.irfft2(np.conj(fm) * fm, s=(n, n)))
    return w / w.max()


def _search_mask(n, frac):
    """探索する変位の範囲(中央からの正方領域)。``frac`` が None なら全域。"""
    if frac is None:
        return None
    c0 = n // 2
    lim = max(1, int(n * frac))
    keep = np.zeros((n, n), bool)
    keep[c0 - lim:c0 + lim + 1, c0 - lim:c0 + lim + 1] = True
    return keep


def _corr_map(wa, wb, taper, subtract_mean, weight=None):
    """1 組の窓の相互相関マップ(零変位が中央)。アンサンブル相関と共用する。"""
    x, y = wa, wb
    if subtract_mean:
        x = x - x.mean()
        y = y - y.mean()
    if taper is not None:
        x = x * taper
        y = y * taper
    n = x.shape[0]
    corr = np.fft.fftshift(
        np.fft.irfft2(np.conj(np.fft.rfft2(x)) * np.fft.rfft2(y), s=(n, n)))
    return corr if weight is None else corr / weight


def _correlate_window(wa, wb, taper, subtract_mean, peak, weight=None, keep=None):
    """1 組の窓の相互相関 → ``(dy, dx, peak_ratio)``。"""
    corr = _corr_map(wa, wb, taper, subtract_mean, weight)
    n = corr.shape[0]
    search = corr if keep is None else np.where(keep, corr, -np.inf)
    k = int(np.argmax(search))
    pi, pj = divmod(k, n)
    top = corr[pi, pj]
    if not np.isfinite(top) or top <= 0:
        return np.nan, np.nan, np.nan
    dy = _subpixel(corr, pi, pj, 0, peak)
    dx = _subpixel(corr, pi, pj, 1, peak)
    ratio = _peak_ratio(search, pi, pj, top)
    c0 = n // 2
    return (pi - c0) + dy, (pj - c0) + dx, ratio


def _subpixel(corr, pi, pj, axis, mode):
    """ピークの両隣 1 点ずつで小数部を決める。端に張り付いたら 0 を返す。"""
    n = corr.shape[0]
    p = pi if axis == 0 else pj
    if p <= 0 or p >= n - 1:
        return 0.0
    if axis == 0:
        cm, c0, cp = corr[p - 1, pj], corr[p, pj], corr[p + 1, pj]
    else:
        cm, c0, cp = corr[pi, p - 1], corr[pi, p], corr[pi, p + 1]
    if mode == "gauss3":
        if cm <= 0 or c0 <= 0 or cp <= 0:      # 対数が取れないので放物線に落とす
            return _parabolic(cm, c0, cp)
        lm, l0, lp = np.log(cm), np.log(c0), np.log(cp)
        den = 2.0 * (lm - 2.0 * l0 + lp)
        return 0.0 if abs(den) < _EPS else (lm - lp) / den
    if mode == "parabolic":
        return _parabolic(cm, c0, cp)
    tot = cm + c0 + cp                          # centroid
    return 0.0 if abs(tot) < _EPS else (cp - cm) / tot


def _parabolic(cm, c0, cp):
    den = 2.0 * (cm - 2.0 * c0 + cp)
    return 0.0 if abs(den) < _EPS else (cm - cp) / den


def _peak_ratio(corr, pi, pj, top):
    """第 1 ピーク / 第 2 ピーク。第 1 ピークの 3x3 近傍を除いた最大で測る。"""
    n = corr.shape[0]
    y0, y1 = max(0, pi - 1), min(n, pi + 2)
    x0, x1 = max(0, pj - 1), min(n, pj + 2)
    masked = np.array(corr, dtype=np.float64, copy=True)
    masked[y0:y1, x0:x1] = -np.inf
    second = float(np.max(masked))
    if not np.isfinite(second) or second <= 0:
        return np.inf
    return float(top / second)


def piv_multipass(a, b, windows=(64, 32), overlap=0.5, peak="gauss3",
                  window_func="hann", outlier_threshold=2.0,
                  normalize="overlap", search_limit=0.25):
    """粗い窓から細かい窓へ段を下げる多段 PIV。返りは ``(flow, info)``。

    各段の結果を**次の段の予測変位**として使う(整数量だけ 2 枚目の窓をずらす)。
    段の間で外れ値を除いて埋めるのは意図的 —— 外れたベクトルをそのまま予測に
    使うと、その窓は次の段でも外れたまま固定される。

    Args:
        a, b: 画像対。
        windows: 大きい順の窓列。各段は前段の**倍数関係でなくてよい**が、
            格子が変わるので予測は最近傍で載せ替える。
        overlap / peak / window_func: :func:`piv_cross_correlate` と同じ。
        outlier_threshold: 段間の正規化中央値検定の閾値。``None`` で無効。
    Returns:
        最終段の ``(flow, info)``。``info["passes"]`` に各段の窓の大きさ。
    """
    wins = [int(w) for w in windows]
    if not wins:
        raise ValueError("windows must not be empty")
    if any(wins[i] < wins[i + 1] for i in range(len(wins) - 1)) is False and len(wins) > 1:
        pass                                    # 昇順でも動くが慣行は降順
    flow = info = None
    for k, win in enumerate(wins):
        pred = None
        if flow is not None:
            pred = _regrid(flow, info, win, overlap, np.asarray(a).shape)
        flow, info = piv_cross_correlate(a, b, win, overlap, peak, window_func,
                                         shift=pred, normalize=normalize,
                                         search_limit=search_limit)
        if outlier_threshold is not None and k < len(wins) - 1:
            mask = piv_outlier_mask(flow, outlier_threshold)
            flow = piv_replace_outliers(flow, mask, "median")
    info = dict(info)
    info["passes"] = tuple(wins)
    return flow, info


def _regrid(flow, info, win, overlap, shape):
    """前段の変位場を次段の窓格子へ最近傍で載せ替える。"""
    h, w = shape
    step = max(1, int(round(win * (1.0 - overlap))))
    rows = np.arange(0, h - win + 1, step) + (win - 1) / 2.0
    cols = np.arange(0, w - win + 1, step) + (win - 1) / 2.0
    # 真の最近傍(searchsorted は「右隣」を返し、粗い格子の中点より左の窓も右の粗ベクトルを取っていた)
    r0 = np.asarray(info["rows"], dtype=np.float64)
    c0 = np.asarray(info["cols"], dtype=np.float64)
    ri = np.argmin(np.abs(rows[:, None] - r0[None, :]), axis=1)
    ci = np.argmin(np.abs(cols[:, None] - c0[None, :]), axis=1)
    out = flow[:, ri][:, :, ci]
    return np.nan_to_num(out, nan=0.0)


# =========================================================================
# 3. 外れ値 —— 正規化中央値検定
# =========================================================================

def piv_outlier_mask(flow, threshold=2.0, epsilon=0.1):
    """正規化中央値検定(Westerweel & Scarano 2005)で外れベクトルを見つける。

    各ベクトルについて、8 近傍の中央値からの残差を**近傍残差の中央値**で割る。
    分母に ``epsilon``(既定 0.1 px、PIV の測定不確かさの目安)を足すのは、
    一様な場で分母が 0 になって全部が外れ値になるのを防ぐため —— この項が
    無いと、**理想的な入力ほど検定が壊れる**。

    ★**勾配の急な場では害になる**(2026-09-06 実測)。Rankine 型の渦
    (芯の半径 28 px)で多段 PIV を掛けたところ、閾値 2 が拾った 5 本は
    すべて**芯の縁**(中心から 32 px)に並び、実際の誤差は 0.07-0.45 px ——
    外れ値ではなく**速度分布が折れている場所**だった。近傍中央値で均すと
    RMS が 0.134 から 0.230 へ**悪化**する(閾値 5 では 1 本も拾わず 0.134 のまま)。

    検定は「近傍と違う = 間違い」という仮定に立つので、**本物の不連続を
    間違いと呼ぶ**。掛けるかどうかは場の性質を見て決めること。

    Args:
        flow: ``(2, h, w)``。
        threshold: この値を超えたら外れ値。慣行は 2。
        epsilon: 分母の下駄 [px]。
    Returns:
        ``(h, w)`` の bool。``True`` が外れ値(``nan`` も ``True``)。
    """
    f = _flow(flow)
    thr = _positive(threshold, "threshold")
    eps = float(epsilon)
    if eps < 0:
        raise ValueError(f"epsilon must be >= 0, got {epsilon}")
    _, h, w = f.shape
    pad = np.pad(f, ((0, 0), (1, 1), (1, 1)), mode="edge")
    neigh = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            neigh.append(pad[:, 1 + dy:1 + dy + h, 1 + dx:1 + dx + w])
    nb = np.stack(neigh)                              # (8, 2, h, w)
    with np.errstate(invalid="ignore", divide="ignore"):
        med = np.nanmedian(nb, axis=0)
        res = np.nanmedian(np.abs(nb - med), axis=0)
        norm = np.abs(f - med) / (res + eps)      # eps=0 かつ完全一様なら 0/0=nan
    bad = np.any(norm > thr, axis=0) | np.any(~np.isfinite(f), axis=0)
    return bad


def piv_replace_outliers(flow, mask, method="median"):
    """外れ値を近傍で埋める。``method="nan"`` なら**埋めずに欠測にする**。

    埋めた場所と実測を区別できなくなるのが埋め込みの代償なので、
    どこを埋めたかは呼ぶ側が ``mask`` として持っている前提にしてある
    (この op は mask を返さない —— 入力として受け取ったものだから)。
    """
    f = _flow(flow).copy()
    m = np.asarray(mask, bool)
    if m.shape != f.shape[1:]:
        raise ValueError(f"mask must be {f.shape[1:]}, got {m.shape}")
    _choice(method, "method", OUTLIER_FILL)
    if method == "nan":
        f[:, m] = np.nan
        return f
    work = f.copy()
    work[:, m] = np.nan
    _, h, w = f.shape
    pad = np.pad(work, ((0, 0), (1, 1), (1, 1)), mode="edge")
    neigh = [pad[:, 1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
             for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)]
    nb = np.stack(neigh)
    with np.errstate(invalid="ignore"):
        fill = np.nanmedian(nb, axis=0) if method == "median" else np.nanmean(nb, axis=0)
    f[:, m] = np.where(np.isfinite(fill[:, m]), fill[:, m], 0.0)
    return f


# =========================================================================
# 4. 場の量 —— 渦度・発散・大きさ
# =========================================================================

def _needs_a_grid(f, name):
    """微分できる大きさか。**numpy の内部メッセージを外に出さない**。

    連鎖ファザーが 32x32 の画像に窓 32 を当てて 1x1 の格子を作り、そこで
    ``np.gradient`` の "Shape of array too small to calculate a numerical
    gradient" が漏れた(2026-09-06 実測)。例外が出ること自体は正しいが、
    **どの op がなぜ拒否したのかが分からないメッセージ**は fail-closed の
    片肺になる。
    """
    if f.shape[1] < 2 or f.shape[2] < 2:
        raise ValueError(
            f"{name} needs a grid of at least 2x2 vectors to differentiate, "
            f"got {f.shape[1]}x{f.shape[2]}. Use a smaller window or more "
            "overlap so piv_cross_correlate returns more than one vector")


def _gradients(f, s):
    """速度勾配テンソルの 4 成分 ``(dudx, dudy, dvdx, dvdy)``。

    ``u`` は列方向の速度(``dx`` 成分)、``v`` は行方向の速度(``dy`` 成分)。
    ``x`` は列、``y`` は行。**行は下向き**なので、数学の xy 座標とは上下が
    逆になる —— 渦度の符号がここで決まる。
    """
    dudx = np.gradient(f[1], s, axis=1)
    dudy = np.gradient(f[1], s, axis=0)
    dvdx = np.gradient(f[0], s, axis=1)
    dvdy = np.gradient(f[0], s, axis=0)
    return dudx, dudy, dvdx, dvdy


def piv_vorticity(flow, spacing=1.0):
    """渦度 ``d(dx)/dy - d(dy)/dx``。**反時計回りが正**(画像座標での定義)。

    行が下向きに増える画像座標では、数学の xy 座標と上下が逆になる。この符号を
    決めずに書くと渦の向きが黙って反転するので、定義を docstring に固定する。

    Args:
        flow: ``(2, h, w)``。
        spacing: 隣り合うベクトルの間隔 [px] (``info["step"]``)。
    Returns:
        ``(h, w)``。単位は 1/フレーム(``spacing`` が画素なら)。
    """
    f = _flow(flow)
    _needs_a_grid(f, "piv_vorticity")
    s = _positive(spacing, "spacing")
    d_dx_dy = np.gradient(f[1], s, axis=0)       # dx 成分の行方向微分
    d_dy_dx = np.gradient(f[0], s, axis=1)       # dy 成分の列方向微分
    return d_dx_dy - d_dy_dx


def piv_divergence(flow, spacing=1.0):
    """発散 ``d(dy)/dy + d(dx)/dx``。**非圧縮なら 0** —— 独立な検算に使える。

    式: ``gradient(flow[0], spacing, axis=0) + gradient(flow[1], spacing, axis=1)``
    (``numpy.gradient``: 内部は中央差分、格子の端は片側差分)。
    ``flow[0]`` が行方向の変位 ``dy``、``flow[1]`` が列方向の変位 ``dx``、
    ``x`` = 列、``y`` = 行。行が下向きでも発散の符号は座標の向きに依らない
    (渦度 ``piv_vorticity`` とは違い、反転しない)。正 = 湧き出し、負 = 吸い込み。

    - ``flow``: ``(2, h, w)``、成分 ``(dy, dx)`` [px/frame] (``piv_cross_correlate`` /
      ``piv_multipass`` の返り値)。``h, w >= 2`` でないと微分できないので
      ``ValueError``(窓が大きすぎて 1 本しかベクトルが無い場合)。
      **有限性は検査しない** ―― ``piv_replace_outliers(method="nan")`` の NaN は
      隣接 2 セルへ広がる。
    - ``spacing``: ベクトル間隔 [px]、正の有限値。``info["step"]`` を渡す
      (既定 1.0 のままだと単位が「1/ベクトル間隔」になる)。
    - 返り値: ``(h, w)`` float64、単位 1/frame(``spacing`` が px のとき)。
      ``piv_to_velocity`` で m/s にした場と ``spacing`` を m にすれば 1/s。

    2-D PIV で平面外の速度成分があると非零になるので、「非圧縮なのに発散が
    大きい」は面外流か外れ値(``piv_outlier_mask``)の指標。
    ``piv_velocity_gradient`` は 4 成分すべてを返す。
    """
    f = _flow(flow)
    _needs_a_grid(f, "piv_divergence")
    s = _positive(spacing, "spacing")
    return np.gradient(f[0], s, axis=0) + np.gradient(f[1], s, axis=1)


def piv_flow_magnitude(flow):
    """``sqrt(dy^2 + dx^2)``。向きを捨てる**一方向**の変換。

    ``reprconv.flow_magnitude`` の 2 次元版。あちらは ``(3, D, H, W)`` 専用で、
    ここへ渡すと形で弾かれる(型を分けてある理由がこれ)。
    """
    f = _flow(flow)
    return np.hypot(f[0], f[1])


def piv_to_velocity(flow, pixel_size_m, dt_s):
    """画素/フレーム → m/s。**両方とも必須引数**(既定値を置かない)。

    単位の取り違えは例外を出さずに桁を変えるので、既定値を置くと事故が既定に
    なる —— ``demops`` の ``cell_size`` と同じ判断。

    Returns:
        ``(2, h, w)`` [m/s]。
    """
    f = _flow(flow)
    px = _positive(pixel_size_m, "pixel_size_m")
    dt = _positive(dt_s, "dt_s")
    return f * (px / dt)


# =========================================================================
# 5. 評価 —— 真値との突き合わせと系統誤差
# =========================================================================

def piv_sample_at_windows(field, info):
    """画素ごとの場 ``(2, H, W)`` を窓中心の格子へ落とす(最近傍)。

    真値は画素解像度で作られるが、PIV の出力は窓の格子に載る。**比べる前に
    同じ格子へ持ってくる**必要があり、その持ってき方(最近傍か窓内平均か)で
    誤差が変わる。ここは最近傍 —— 窓内平均にすると、勾配のある場で PIV 自身の
    平滑化と区別がつかなくなる。
    """
    f = _flow(field, "field")
    r = np.rint(np.asarray(info["rows"], np.float64)).astype(np.int64)
    c = np.rint(np.asarray(info["cols"], np.float64)).astype(np.int64)
    r = np.clip(r, 0, f.shape[1] - 1)
    c = np.clip(c, 0, f.shape[2] - 1)
    return f[:, r][:, :, c]


def piv_error_stats(flow, truth, trim=1):
    """真値との差の内訳。**偏りと散らばりを分けて**返す。

    どちらか一方だけを出すと、系統的にずれている実装が「誤差 0.3 px」として
    通ってしまう。偏り(平均誤差)と散らばり(標準偏差)は別の原因を指す。

    Args:
        flow: 推定 ``(2, h, w)``。
        truth: 同じ格子の真値 ``(2, h, w)``(:func:`piv_sample_at_windows` の返り)。
        trim: 外周から除く格子数。窓が画像の縁にかかると相関が落ちるので、
            既定で 1 列ぶん落とす。0 で全格子。
    Returns:
        dict: ``bias_dy`` / ``bias_dx`` / ``std_dy`` / ``std_dx`` / ``rms``
        (2 成分合わせた二乗平均平方根) / ``median_abs`` / ``p95_abs`` /
        ``n_valid`` / ``n_total``。
    """
    f, t = _flow(flow), _flow(truth, "truth")
    if f.shape != t.shape:
        raise ValueError(f"flow and truth must have the same shape, got {f.shape} and {t.shape}")
    k = int(trim)
    if k < 0:
        raise ValueError(f"trim must be >= 0, got {trim}")
    if k:
        if f.shape[1] <= 2 * k or f.shape[2] <= 2 * k:
            raise ValueError(f"trim={k} removes the whole grid of shape {f.shape[1:]}")
        f, t = f[:, k:-k, k:-k], t[:, k:-k, k:-k]
    err = f - t
    ok = np.all(np.isfinite(err), axis=0)
    e = err[:, ok]
    if e.size == 0:
        raise ValueError("no finite vector left to compare")
    mag = np.hypot(e[0], e[1])
    return {
        "bias_dy": float(np.mean(e[0])), "bias_dx": float(np.mean(e[1])),
        "std_dy": float(np.std(e[0])), "std_dx": float(np.std(e[1])),
        "rms": float(np.sqrt(np.mean(e[0] ** 2 + e[1] ** 2))),
        "median_abs": float(np.median(mag)), "p95_abs": float(np.percentile(mag, 95)),
        "n_valid": int(ok.sum()), "n_total": int(ok.size),
    }


def piv_peak_locking(flow, bins=20):
    """ピークロッキングの強さ。小数部の分布が一様からどれだけ外れているか。

    サブピクセル推定は、真の変位の小数部が 0 や 0.5 のときにそこへ引き寄せられる
    偏りを持つ(相関ピークの形と当てはめる関数の形が違うことから来る、PIV の
    教科書的な系統誤差)。**流れが一様でなければ小数部は一様分布に近いはず**で、
    そこからのずれを測る。

    指標 ``c0`` は**標本数に依らない**カイ二乗型のずれ:
    ``sum((n_i - n_bar)^2 / n_bar) / (bins - 1)``。一様分布から標本を取ると
    期待値 1 になるので、**1 前後なら一様と区別できない**、大きいほど偏っている。

    ★ ただしこの指標は「真の変位の小数部が一様である」ことを仮定する。窓の数が
    少ない場や、変位がゆっくり変わる場では**真値そのものの c0 も大きくなる**
    (実測: 線形ランプの真値で 82 —— 窓格子が 19 列しか無く小数部が離散的に
    しか現れないため)。したがって c0 は**同じ入力の真値と比べて**読むこと。

    **決定的な診断は別にある** —— 一様並進の小数部を 0 から 0.9 まで振り、
    推定値が対角線に乗るかを見る。実測(win=32、density 0.02):

    ==========  =================  ==================
    推定法      小数部誤差の RMS   最大絶対誤差
    ==========  =================  ==================
    gauss3      0.0037 px          0.0088 px
    parabolic   0.0104 px          0.0151 px
    centroid    0.2259 px          0.3701 px
    ==========  =================  ==================

    ``centroid`` は真値 0.1 を 0.02、0.9 を 0.98 と答える —— 整数へ引き寄せる
    教科書どおりの S 字。**出るはずのものが出た**ことの確認であって、
    実装の不具合ではない(だから 3 つとも残してある)。

    Args:
        flow: ``(2, h, w)``。
        bins: 小数部のヒストグラムの階級数。
    Returns:
        dict: ``c0``(両成分合わせた指標)、``hist``(``(2, bins)``)、
        ``frac_mean`` / ``frac_std``、``bins``。
    """
    f = _flow(flow)
    n = int(bins)
    if n < 4:
        raise ValueError(f"bins must be >= 4, got {n}")
    frac = np.mod(f, 1.0)
    hist = np.zeros((2, n))
    ok = np.isfinite(f)
    for i in range(2):
        v = frac[i][ok[i]]
        if v.size == 0:
            raise ValueError("no finite displacement to histogram")
        hist[i] = np.histogram(v, bins=n, range=(0.0, 1.0))[0]
    total = hist.sum()
    mean = total / (2.0 * n)
    c0 = (float(np.sum((hist - mean) ** 2) / mean) / (2.0 * n - 1.0)
          if total else float("nan"))
    return {"c0": c0, "hist": hist, "bins": n,
            "frac_mean": float(np.nanmean(frac[ok])),
            "frac_std": float(np.nanstd(frac[ok]))}



# =========================================================================
# 6. 派生 —— 渦の識別・可視化・時間統計・窓変形
# =========================================================================

def piv_velocity_gradient(flow, spacing=1.0):
    """速度勾配テンソルの成分と、そこから出る量をまとめて返す。

    渦度・発散・Q 基準・渦回転強度・ひずみ速度は**すべて同じ 4 つの微分**から
    出るので、勾配を 4 回計算し直さずに済むようにここへまとめる。個々の op
    (:func:`piv_vorticity` など)は単独でも使えるが、複数要るならこちら。

    Returns:
        dict: ``dudx`` / ``dudy`` / ``dvdx`` / ``dvdy``(各 ``(h, w)``)、
        ``vorticity`` / ``divergence`` / ``q`` / ``swirl`` / ``strain_rate``、
        ``spacing``。
    """
    f = _flow(flow)
    _needs_a_grid(f, "piv_velocity_gradient")
    sp = _positive(spacing, "spacing")
    a, b, c, d = _gradients(f, sp)
    tr, det = a + d, a * d - b * c
    disc = 0.25 * tr * tr - det
    exy = 0.5 * (b + c)
    return {
        "dudx": a, "dudy": b, "dvdx": c, "dvdy": d,
        "vorticity": b - c,                       # d(dx)/dy - d(dy)/dx
        "divergence": d + a,
        "q": -0.5 * (a * a + 2.0 * b * c + d * d),
        "swirl": np.where(disc < 0, np.sqrt(np.maximum(-disc, 0.0)), 0.0),
        "strain_rate": np.sqrt(2.0 * (a * a + d * d + 2.0 * exy * exy)),
        "spacing": sp,
    }


def piv_q_criterion(flow, spacing=1.0):
    """Q 基準 ``-tr(J^2)/2``。**回転がひずみを上回る**場所が正になる。

    渦度だけを見るとせん断層も光る(層流の壁近傍が渦に見える)ので、渦の抽出には
    こちらを使う。閉形式(解析場を直接与えた実測):

    * 剛体回転 ω=0.01 → ``+1.0e-4`` (= ω^2)
    * 一様膨張 s=0.01 → ``-1.0e-4`` (= -s^2)
    * 単純せん断 g=0.02 → ``0.0``(**せん断は渦ではない**、が要点)

    ★ 閾値を必要とする量である。``Q > 0`` だけでは薄い領域まで拾うので、
    閾値をどう決めたかを書かない渦可視化は、絵の美しさが閾値の産物である
    可能性を隠している。閾値を振ったときの面積変化を併記すること。
    """
    _needs_a_grid(_flow(flow), "piv_q_criterion")   # 内部ヘルパの名前で断らない
    return piv_velocity_gradient(flow, spacing)["q"]


def piv_swirling_strength(flow, spacing=1.0):
    """渦回転強度 λ_ci —— 速度勾配テンソルの複素固有値の虚部の大きさ。

    Q 基準と同じく「せん断と渦を区別する」量だが、こちらは**回転の角速度に
    等しい単位**を持つ(1/フレーム)。実測: 剛体回転 ω=0.01 で ``0.01``、
    一様膨張とせん断で ``0.0``。

    固有値が実数(= 回転していない)の場所は 0 を返す。各点で独立な 2x2 の
    固有値なので、格子全体をベクトル化して一度に解いている。
    """
    _needs_a_grid(_flow(flow), "piv_swirling_strength")   # 内部ヘルパの名前で断らない
    return piv_velocity_gradient(flow, spacing)["swirl"]


def piv_strain_rate(flow, spacing=1.0):
    """ひずみ速度の大きさ ``sqrt(2 e_ij e_ij)``。剛体回転では 0 になる。

    実測: 剛体回転 0.0 / 一様膨張 s=0.01 で 0.02 (= 2s) / 単純せん断 g=0.02 で
    0.02 (= g)。**回転だけを取り除いた変形の強さ**なので、Q 基準や λ_ci と
    合わせて見ると「渦かせん断か」が分かれる。
    """
    _needs_a_grid(_flow(flow), "piv_strain_rate")   # 内部ヘルパの名前で断らない
    return piv_velocity_gradient(flow, spacing)["strain_rate"]


def piv_flow_to_rgbimage(flow, scale=None):
    """色相 = 向き、明度 = 速さの標準的なフロー可視化。返りは ``(h, w, 3)``。

    ``reprconv.flow_to_rgbimage`` の 2 次元版(あちらは ``(3, D, H, W)`` の
    3-D シーンフロー専用で、平面フローは形で弾かれる)。

    **色相環の凡例を図の側で必ず一緒に焼くこと** —— 色の意味が書いていない
    フロー図は綺麗なだけで読めない。``scale`` を省くと最大の速さで正規化する
    ので、**図ごとに色の意味が変わる**。複数の図を並べるなら明示的に固定する。

    Args:
        flow: ``(2, h, w)``。
        scale: 明度 1.0 に対応する速さ [px]。``None`` で最大値。
    Returns:
        ``(h, w, 3)`` float64、値域 [0, 1]。
    """
    f = _flow(flow)
    mag = np.hypot(f[0], f[1])
    top = float(np.nanmax(mag)) if scale is None else _positive(scale, "scale")
    if not np.isfinite(top) or top <= 0:
        top = 1.0
    v = np.clip(np.nan_to_num(mag) / top, 0.0, 1.0)
    # 画面上の向き。行が下向きなので、上向きを 90 度にするには dy の符号を反転
    hue = (np.degrees(np.arctan2(-np.nan_to_num(f[0]), np.nan_to_num(f[1]))) % 360.0) / 60.0
    i = np.floor(hue).astype(np.int64) % 6
    frac = hue - np.floor(hue)
    p, q, t = np.zeros_like(v), v * (1.0 - frac), v * frac
    r = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [v, q, p, p, t, v])
    g = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [t, v, v, q, p, p])
    b = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


def piv_line_integral_convolution(flow, length=12, upsample=4, seed=0):
    """線積分畳み込み(LIC)—— 流れに沿って白色雑音をぼかした模様の画像。

    ベクトルの矢印は密にすると潰れ、疎にすると構造を見落とす。LIC は**画素ごと**
    に流線に沿って雑音を平均するので、密度の選択が要らない。向きの情報は落ちる
    (前後を区別しない)ので、**回転の向きを見たいときは矢印か色相図と併用する**。

    Args:
        flow: ``(2, h, w)``。
        length: 流線に沿って積分する片側の歩数。長いほど滑らかになるが、
            渦の芯のような曲率の大きい場所では**構造が伸びて嘘になる**。
        upsample: 出力の解像度倍率(格子は粗いので拡大してから積分する)。
        seed: 白色雑音の種。
    Returns:
        ``(h * upsample, w * upsample)`` float64、値域 [0, 1]。
    """
    f = _flow(flow)
    _needs_a_grid(f, "piv_line_integral_convolution")
    L = int(length)
    up = int(upsample)
    if L < 1:
        raise ValueError(f"length must be >= 1, got {length}")
    if up < 1:
        raise ValueError(f"upsample must be >= 1, got {upsample}")
    h, w = f.shape[1] * up, f.shape[2] * up
    rr = (np.arange(h) + 0.5) / up - 0.5
    cc = (np.arange(w) + 0.5) / up - 0.5
    fy = _bilinear(np.nan_to_num(f[0]), rr, cc)
    fx = _bilinear(np.nan_to_num(f[1]), rr, cc)
    mag = np.hypot(fy, fx)
    ok = mag > _EPS
    uy = np.where(ok, fy / np.where(ok, mag, 1.0), 0.0)
    ux = np.where(ok, fx / np.where(ok, mag, 1.0), 0.0)
    rng = np.random.default_rng(int(seed))
    noise = rng.random((h, w))
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float64)
    acc = np.array(noise, copy=True)
    for sign in (1.0, -1.0):
        py, px = gy.copy(), gx.copy()
        for _ in range(L):
            py = np.clip(py + sign * uy * up * 0.5, 0, h - 1)
            px = np.clip(px + sign * ux * up * 0.5, 0, w - 1)
            acc += noise[np.rint(py).astype(np.int64), np.rint(px).astype(np.int64)]
    out = acc / (2.0 * L + 1.0)
    lo, hi = float(out.min()), float(out.max())
    return (out - lo) / (hi - lo) if hi > lo else np.zeros_like(out)


def _bilinear(a, rows, cols):
    """``a`` を ``rows`` x ``cols`` の格子で双一次補間(端は複製)。"""
    h, w = a.shape
    r = np.clip(rows, 0, h - 1)
    c = np.clip(cols, 0, w - 1)
    r0 = np.floor(r).astype(np.int64)
    c0 = np.floor(c).astype(np.int64)
    r1 = np.minimum(r0 + 1, h - 1)
    c1 = np.minimum(c0 + 1, w - 1)
    wr = (r - r0)[:, None]
    wc = (c - c0)[None, :]
    top = a[np.ix_(r0, c0)] * (1 - wc) + a[np.ix_(r0, c1)] * wc
    bot = a[np.ix_(r1, c0)] * (1 - wc) + a[np.ix_(r1, c1)] * wc
    return top * (1 - wr) + bot * wr


def piv_deform_pass(a, b, flow, info, window=32, overlap=0.5, peak="gauss3",
                    window_func="hann", order=3):
    """窓変形つきの 1 段。予測変位で**画像そのものを歪めてから**相関を取る。

    整数ずらし(:func:`piv_cross_correlate` の ``shift``)は、窓の中で変位が
    一定という仮定を置く。回転やせん断のように**窓の中で変位が変わる**場では
    相関ピークが潰れるので、2 枚を予測の半分ずつ逆向きに歪めてから相関する
    (中央差分の変形)。

    Args:
        a, b: 画像対。
        flow: 予測変位 ``(2, h, w)``(``piv_multipass`` などの出力)。
        info: その ``info``(窓中心の座標が要る)。
        window / overlap / peak / window_func: 新しい段の設定。
        order: 変形に使う補間の次数(3 = 3 次スプライン)。
    Returns:
        ``(flow (2, h', w'), info)``。返る変位は**元の画像座標での総変位**。
    """
    from scipy import ndimage                     # core 依存(numpy と scipy)

    A, B = _img(a, "a"), _img(b, "b")
    if A.shape != B.shape:
        raise ValueError(f"a and b must have the same shape, got {A.shape} and {B.shape}")
    pred = _flow(flow, "flow")
    rows_n = len(np.atleast_1d(info["rows"]))
    cols_n = len(np.atleast_1d(info["cols"]))
    if pred.shape[1:] != (rows_n, cols_n):
        raise ValueError(
            f"flow is {pred.shape[1:]} but info describes a {rows_n}x{cols_n} grid; "
            "pass the info that came back with this flow")
    h, w = A.shape
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float64)
    # 粗い格子の予測を画素格子へ広げる
    rows = np.asarray(info["rows"], np.float64)
    cols = np.asarray(info["cols"], np.float64)
    py = _resample_to_pixels(np.nan_to_num(pred[0]), rows, cols, h, w)
    px = _resample_to_pixels(np.nan_to_num(pred[1]), rows, cols, h, w)
    # 中央差分の変形: a を -d/2、b を +d/2 だけ戻す
    wa = ndimage.map_coordinates(A, [gy - 0.5 * py, gx - 0.5 * px], order=order,
                                 mode="nearest")
    wb = ndimage.map_coordinates(B, [gy + 0.5 * py, gx + 0.5 * px], order=order,
                                 mode="nearest")
    residual, out_info = piv_cross_correlate(wa, wb, window, overlap, peak, window_func)
    base = np.stack([
        _sample_grid(py, out_info), _sample_grid(px, out_info)])
    out_info = dict(out_info)
    out_info["deformed"] = True
    return residual + base, out_info


def _resample_to_pixels(g, rows, cols, h, w):
    """粗い格子 ``g``(``rows`` x ``cols`` に載る)を画素格子へ双一次で広げる。"""
    if g.shape[0] < 2 or g.shape[1] < 2:
        return np.full((h, w), float(np.mean(g)))
    ri = np.interp(np.arange(h), rows, np.arange(g.shape[0]))
    ci = np.interp(np.arange(w), cols, np.arange(g.shape[1]))
    return _bilinear(g, ri, ci)


def _sample_grid(pixels, info):
    """画素格子の場を窓中心で拾う。"""
    r = np.clip(np.rint(np.asarray(info["rows"])).astype(np.int64), 0, pixels.shape[0] - 1)
    c = np.clip(np.rint(np.asarray(info["cols"])).astype(np.int64), 0, pixels.shape[1] - 1)
    return pixels[np.ix_(r, c)]


def piv_ensemble_correlate(images, window=32, overlap=0.5, peak="gauss3",
                           window_func="hann", normalize="overlap",
                           search_limit=0.25):
    """相関マップを**足してから**ピークを探す(アンサンブル相関)。

    粒子が少ない・雑音が多い場合、1 対ずつ測って平均すると**外れたベクトルの
    平均**になる。相関の段階で足すと、弱いピークが同じ場所に積み上がって
    立ち上がる。定常流(全対で変位が同じ)が前提。

    Args:
        images: 2 枚以上の画像の列。連続する対 ``(k, k+1)`` を使う。
        window / overlap / peak / window_func / normalize / search_limit:
            :func:`piv_cross_correlate` と同じ。
    Returns:
        ``(flow (2, h, w), info)``。``info["pairs"]`` に使った対の数。
    """
    seq = list(images)
    if len(seq) < 2:
        raise ValueError(f"images must hold at least 2 frames, got {len(seq)}")
    frames = [_img(x, f"images[{i}]") for i, x in enumerate(seq)]
    shape = frames[0].shape
    for i, x in enumerate(frames):
        if x.shape != shape:
            raise ValueError(f"images[{i}] has shape {x.shape} but images[0] has {shape}")
    win = _window(window, shape)
    ov = float(overlap)
    if not (0.0 <= ov < 1.0):
        raise ValueError(f"overlap must be in [0, 1), got {overlap}")
    _choice(peak, "peak", PEAK_MODES)
    _choice(window_func, "window_func", WINDOW_FUNCS)
    _choice(normalize, "normalize", NORMALIZE_MODES)
    step = max(1, int(round(win * (1.0 - ov))))
    h, w = shape
    rows = np.arange(0, h - win + 1, step)
    cols = np.arange(0, w - win + 1, step)
    if rows.size == 0 or cols.size == 0:
        raise ValueError(f"window={win} with overlap={ov} leaves no window in shape {shape}")
    taper = _taper(win, window_func)
    weight = _overlap_weight(win, taper) if normalize == "overlap" else None
    keep = _search_mask(win, None if search_limit is None else float(search_limit))
    c0 = win // 2
    flow = np.zeros((2, rows.size, cols.size))
    ratio = np.zeros((rows.size, cols.size))
    for i, r in enumerate(rows):
        for j, c in enumerate(cols):
            acc = np.zeros((win, win))
            for k in range(len(frames) - 1):
                acc += _corr_map(frames[k][r:r + win, c:c + win],
                                 frames[k + 1][r:r + win, c:c + win],
                                 taper, True, weight)
            search = acc if keep is None else np.where(keep, acc, -np.inf)
            idx = int(np.argmax(search))
            pi, pj = divmod(idx, win)
            flow[0, i, j] = (pi - c0) + _subpixel(acc, pi, pj, 0, peak)
            flow[1, i, j] = (pj - c0) + _subpixel(acc, pi, pj, 1, peak)
            ratio[i, j] = _peak_ratio(search, pi, pj, acc[pi, pj])
    info = {"rows": rows + (win - 1) / 2.0, "cols": cols + (win - 1) / 2.0,
            "peak_ratio": ratio, "window": win, "overlap": ov, "peak": peak,
            "window_func": window_func, "step": step, "normalize": normalize,
            "search_limit": search_limit, "pairs": len(frames) - 1}
    return flow, info


def piv_time_statistics(images, window=32, overlap=0.5, **kw):
    """画像列 → 時間平均・変動の RMS・レイノルズ応力。

    連続する対ごとに変位を測り、時間方向の統計を取る。乱流の記述はこの 3 つが
    出発点で、``u'v'`` の符号と大きさが運動量輸送そのものになる。

    **1 対だけでは意味が無い**(変動が定義できない)ので 3 枚以上を要求する。

    Args:
        images: 3 枚以上の画像列。
        window / overlap / kw: :func:`piv_cross_correlate` へ渡す。
    Returns:
        dict: ``mean``(``(2, h, w)``)、``rms``(同)、``reynolds``
        (``<u'v'>``、``(h, w)``)、``turbulence_intensity``、``n_pairs``、
        ``rows`` / ``cols`` / ``step``。
    """
    seq = list(images)
    if len(seq) < 3:
        raise ValueError(
            f"images must hold at least 3 frames to define a fluctuation, got {len(seq)}")
    flows, info = [], None
    for k in range(len(seq) - 1):
        f, info = piv_cross_correlate(seq[k], seq[k + 1], window, overlap, **kw)
        flows.append(f)
    stack = np.stack(flows)                       # (n, 2, h, w)
    mean = np.nanmean(stack, axis=0)
    fluct = stack - mean
    rms = np.sqrt(np.nanmean(fluct ** 2, axis=0))
    reynolds = np.nanmean(fluct[:, 0] * fluct[:, 1], axis=0)
    speed = np.hypot(mean[0], mean[1])
    with np.errstate(invalid="ignore", divide="ignore"):
        ti = np.where(speed > _EPS, np.hypot(rms[0], rms[1]) / speed, np.nan)
    return {"mean": mean, "rms": rms, "reynolds": reynolds,
            "turbulence_intensity": ti, "n_pairs": len(flows),
            "rows": info["rows"], "cols": info["cols"], "step": info["step"]}


# ---------------------------------------------------------------------------
# 矢印図と流線 —— MATLAB の quiver / streamline / streamslice に当たる出口
# (2026-10-03)。色相図と LIC だけでは「どちら向きに・どれだけ」が読めない。
# ---------------------------------------------------------------------------

_STREAM_STOPS = ("boundary", "stagnation", "collision", "closed", "self", "max_steps")


def _bilinear_at(a, r, c):
    """``a`` の 1 点 ``(r, c)`` での双一次補間(範囲内であることは呼び手が保証)。"""
    h, w = a.shape
    r0 = min(int(r), h - 2) if h > 1 else 0
    c0 = min(int(c), w - 2) if w > 1 else 0
    fr = r - r0
    fc = c - c0
    return ((a[r0, c0] * (1.0 - fc) + a[r0, c0 + 1] * fc) * (1.0 - fr)
            + (a[r0 + 1, c0] * (1.0 - fc) + a[r0 + 1, c0 + 1] * fc) * fr)


class _PointHash:
    """流線の標本点を升目で引く(Jobard–Lefer の「近すぎるか」判定)。"""

    def __init__(self, cell):
        self.cell = float(cell)
        self.bins = {}

    def _key(self, r, c):
        return (int(r // self.cell), int(c // self.cell))

    def add(self, r, c, line, idx):
        self.bins.setdefault(self._key(r, c), []).append((r, c, line, idx))

    def nearest_other(self, r, c, radius, ignore=None):
        """``radius`` 以内にある点のうち、``ignore(line, idx)`` が偽の最初の 1 つ。

        返りは ``(line, idx)`` か ``None``。自分の線の直近の点は呼び手が
        ``ignore`` で外す —— 数えると 1 歩目で自分に衝突する。
        """
        kr, kc = self._key(r, c)
        reach = int(np.ceil(radius / self.cell))
        r2 = radius * radius
        for dr in range(-reach, reach + 1):
            for dc in range(-reach, reach + 1):
                for (pr, pc, pl, pi) in self.bins.get((kr + dr, kc + dc), ()):
                    if ignore is not None and ignore(pl, pi):
                        continue
                    if (pr - r) ** 2 + (pc - c) ** 2 < r2:
                        return pl, pi
        return None


def _trace_one(fy, fx, seed, h_step, max_steps, vmin, grid, d_test, line_id, sign,
               offset=0):
    """種から片方向に RK4 で流線をたどる。返りは ``(points, stop)``。

    向きの場は**正規化した速度**(弧長で進む)。止まる理由:
    範囲外(boundary)/速さが ``vmin`` 未満(stagnation)/別の線に ``d_test``
    より近づいた(collision)/自分の始点に戻った(closed)/自分の途中に
    近づいた(self)/歩数の上限(max_steps)。

    ``offset``: この追跡の点が台帳で何番から振られるか(後ろ向きは前向きの
    続き)。自分の線の点のうち、この追跡の直近と、種の近く(前向きの最初の
    ``recent`` 点)は衝突に数えない。
    """
    H, W = fy.shape

    def vel(r, c):
        if not (0.0 <= r <= H - 1 and 0.0 <= c <= W - 1):
            return None
        vy = _bilinear_at(fy, r, c)
        vx = _bilinear_at(fx, r, c)
        s = (vy * vy + vx * vx) ** 0.5
        if s < vmin:
            return 0.0, 0.0, s
        return sign * vy / s, sign * vx / s, s

    pts = [(float(seed[0]), float(seed[1]))]
    # 自分の線で「直近」とみなす歩数。d_test をこの歩数で越えるまでは自己衝突を数えない
    recent = int(np.ceil(2.0 * d_test / h_step)) + 2
    travelled = 0.0
    r, c = pts[0]
    if grid is not None and offset == 0:
        grid.add(r, c, line_id, 0)
    for _ in range(int(max_steps)):
        k1 = vel(r, c)
        if k1 is None:
            return pts, "boundary"
        if k1[2] < vmin:
            return pts, "stagnation"
        k2 = vel(r + 0.5 * h_step * k1[0], c + 0.5 * h_step * k1[1])
        if k2 is None or k2[2] < vmin:
            return pts, "boundary" if k2 is None else "stagnation"
        k3 = vel(r + 0.5 * h_step * k2[0], c + 0.5 * h_step * k2[1])
        if k3 is None or k3[2] < vmin:
            return pts, "boundary" if k3 is None else "stagnation"
        k4 = vel(r + h_step * k3[0], c + h_step * k3[1])
        if k4 is None or k4[2] < vmin:
            return pts, "boundary" if k4 is None else "stagnation"
        nr = r + h_step / 6.0 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        nc = c + h_step / 6.0 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        if not (0.0 <= nr <= H - 1 and 0.0 <= nc <= W - 1):
            return pts, "boundary"
        travelled += ((nr - r) ** 2 + (nc - c) ** 2) ** 0.5
        if grid is not None:
            near_from = offset + len(pts) - recent

            def ignore(pl, pi):
                if pl != line_id:
                    return False
                if pi >= near_from:                  # この追跡の直近
                    return True
                if travelled <= 4.0 * d_test and pi < recent:
                    return True                      # まだ種の近く(前向きの出だし)
                return offset > 0 and pi < recent    # 後ろ向きは前向きの出だしを数えない
            hit = grid.nearest_other(nr, nc, d_test, ignore)
            if hit is not None:
                if hit[0] != line_id:
                    return pts, "collision"
                # 自分の始点付近へ戻った = 閉じた軌道(剛体回転・渦の芯の周り)
                if offset == 0 and hit[1] * h_step <= 3.0 * d_test:
                    pts.append((nr, nc))
                    return pts, "closed"
                return pts, "self"
        pts.append((nr, nc))
        if grid is not None:
            # 進めるたびに登録する(後で纏めて入れると、自分の始点へ戻っても見えない)
            grid.add(nr, nc, line_id, offset + len(pts) - 1)
        r, c = nr, nc
    return pts, "max_steps"


def piv_streamlines(flow, seeds=None, separation=None, step=0.25, max_length=None,
                    min_speed=1e-3, test_ratio=0.5):
    """流線を RK4 でたどる(MATLAB の ``stream2`` / ``streamslice`` に当たる)。

    ``seeds`` を省くと **Jobard–Lefer(1997)の等間隔配置**で種を自動で置く。
    流線どうしが ``separation`` 程度の間隔で並び、``test_ratio * separation``
    より近づいた所で打ち切る。矢印図は密にすると潰れ、種を手で置くと空白が
    残るが、この配置は**空白も重なりも作らない**(下の 2 つの性質を門にしている)。

    * 別々の流線の標本点どうしは ``test_ratio * separation`` より近づかない。
    * 速さが ``min_speed`` 以上の格子点はどれも、どこかの流線から
      ``separation`` 以内にある(取りこぼしの無さ)。

    座標は flow の格子(行 0 が上、``(row, col)``)。向きの場は速さで割って
    **弧長で進む**ので、1 歩は ``step`` 格子。速さは流線上の各点で別に返す。

    Args:
        flow: ``(2, h, w)``(``dy, dx``)。
        seeds: ``(n, 2)`` の ``(row, col)``。``None`` で自動配置。
        separation: 流線の間隔 [格子]。``None`` で ``max(h, w) / 25``(2 以上)。
        step: RK4 の 1 歩 [格子]。
        max_length: 片方向の最大の長さ [格子]。``None`` で ``4 * (h + w)``。
        min_speed: これより遅い所で止める(**最大の速さに対する比**)。
        test_ratio: 打ち切りの距離を ``separation`` の何倍にするか(0 < x ≤ 1)。
    Returns:
        dict(table): ``paths``(``(m_i, 2)`` の list、上流 → 下流の順)、
        ``speed``(各点の速さの list)、``seeds``、``stop``(``(後ろ, 前)`` の
        理由の組の list)、``n``、``separation``、``d_test``、``step``、
        ``stop_counts``(理由ごとの数)。
    Raises:
        ValueError: flow の形・非有限、パラメータ範囲外、種が格子の外。
    """
    f = _flow(flow)
    _needs_a_grid(f, "piv_streamlines")
    if not np.all(np.isfinite(f)):
        raise ValueError("piv_streamlines: flow holds non-finite values; replace outliers first "
                         "(piv_replace_outliers) — a NaN would end every line it touches")
    H, W = f.shape[1:]
    h_step = _positive(step, "step")
    d_sep = (max(2.0, max(H, W) / 25.0) if separation is None
             else _positive(separation, "separation"))
    tr = float(test_ratio)
    if not (0.0 < tr <= 1.0):
        raise ValueError(f"test_ratio must be in (0, 1], got {test_ratio}")
    if h_step > 0.5 * tr * d_sep:
        raise ValueError(f"step {h_step} is too coarse for separation {d_sep} "
                         f"(needs step <= {0.5 * tr * d_sep:g}); a step longer than half the "
                         "test distance jumps over neighbouring lines")
    L = 4.0 * (H + W) if max_length is None else _positive(max_length, "max_length")
    max_steps = int(np.ceil(L / h_step))
    fy, fx = f[0], f[1]
    vmax = float(np.max(np.hypot(fy, fx)))
    if vmax <= _EPS:
        raise ValueError("piv_streamlines: the flow is zero everywhere; there is nothing to trace")
    vmin = float(min_speed) * vmax
    d_test = tr * d_sep
    grid = _PointHash(d_sep)

    auto = seeds is None
    if auto:
        queue = []
        # 最初の種は最も速い格子点(止まった所から始めると 1 本目が空になる)
        mag = np.hypot(fy, fx)
        r0, c0 = np.unravel_index(int(np.argmax(mag)), mag.shape)
        queue.append((float(r0), float(c0)))
        # 取りこぼしを拾う予備の種: separation/2 間隔の格子
        sp = 0.5 * d_sep
        fall = [(float(r), float(c))
                for r in np.arange(0.0, H - 1 + 1e-9, sp)
                for c in np.arange(0.0, W - 1 + 1e-9, sp)]
    else:
        s = np.asarray(seeds, dtype=np.float64)
        if s.ndim != 2 or s.shape[1] != 2 or s.shape[0] == 0:
            raise ValueError(f"seeds must be (n, 2) (row, col), got shape {s.shape}")
        if not np.all(np.isfinite(s)):
            raise ValueError("seeds hold non-finite values")
        out = (s[:, 0] < 0) | (s[:, 0] > H - 1) | (s[:, 1] < 0) | (s[:, 1] > W - 1)
        if np.any(out):
            raise ValueError(f"{int(out.sum())} seed(s) lie outside the {H}x{W} grid "
                             "(rows 0..h-1, cols 0..w-1)")
        queue = [tuple(map(float, p)) for p in s]
        fall = []

    paths, speeds, used_seeds, stops = [], [], [], []
    qi, fi = 0, 0
    while True:
        if qi < len(queue):
            seed = queue[qi]
            qi += 1
        elif fi < len(fall):
            seed = fall[fi]
            fi += 1
        else:
            break
        sr, sc = seed
        if not (0.0 <= sr <= H - 1 and 0.0 <= sc <= W - 1):
            continue
        sv = (_bilinear_at(fy, sr, sc) ** 2 + _bilinear_at(fx, sr, sc) ** 2) ** 0.5
        if sv < vmin:
            if not auto:
                paths.append(np.array([[sr, sc]]))
                speeds.append(np.array([sv]))
                used_seeds.append((sr, sc))
                stops.append(("stagnation", "stagnation"))
            continue
        lid = len(paths)
        if auto and grid.nearest_other(sr, sc, d_sep) is not None:
            continue
        # 種の点は先に登録しない: 前向きの線を登録してから後ろ向きをたどる
        fwd, stop_f = _trace_one(fy, fx, seed, h_step, max_steps, vmin,
                                 grid if auto else None, d_test, lid, +1.0)
        if stop_f == "closed":
            bwd, stop_b = [(float(sr), float(sc))], "closed"
        else:
            # 後ろ向きの点の番号は前向きの続き(len(fwd) 以降)として登録する
            bwd, stop_b = _trace_one(fy, fx, seed, h_step, max_steps, vmin,
                                     grid if auto else None, d_test, lid, -1.0,
                                     offset=len(fwd))
        pts = np.array(bwd[::-1] + fwd[1:], dtype=np.float64)
        sp_ = np.hypot([_bilinear_at(fy, r, c) for r, c in pts],
                       [_bilinear_at(fx, r, c) for r, c in pts])
        paths.append(pts)
        speeds.append(sp_)
        used_seeds.append((sr, sc))
        stops.append((stop_b, stop_f))
        if auto:
            # 新しい種: 線の各点から左右へ separation だけずらした所(Jobard–Lefer)
            if len(pts) >= 2:
                d = np.gradient(pts, axis=0)
                n = np.hypot(d[:, 0], d[:, 1])
                n[n == 0] = 1.0
                nr, nc = -d[:, 1] / n, d[:, 0] / n
                every = max(1, int(round(0.5 * d_sep / h_step)))
                for k in range(0, len(pts), every):
                    for sg in (1.0, -1.0):
                        queue.append((pts[k, 0] + sg * d_sep * nr[k],
                                      pts[k, 1] + sg * d_sep * nc[k]))
    counts = {k: 0 for k in _STREAM_STOPS}
    for a, b in stops:
        counts[a] += 1
        counts[b] += 1
    return {"paths": paths, "speed": speeds, "seeds": np.array(used_seeds).reshape(-1, 2),
            "stop": stops, "n": len(paths), "separation": float(d_sep),
            "d_test": float(d_test), "step": float(h_step), "stop_counts": counts}


def _quiver_segments(flow, spacing, scale):
    """矢印の起点と先端(flow の格子座標、``(row, col)``)と、使った倍率。"""
    f = _flow(flow)
    H, W = f.shape[1:]
    sp = int(spacing)
    r = np.arange((H - 1) % sp // 2, H, sp)
    c = np.arange((W - 1) % sp // 2, W, sp)
    R, C = np.meshgrid(r, c, indexing="ij")
    vy = f[0][R, C]
    vx = f[1][R, C]
    mag = np.hypot(vy, vx)
    top = float(np.max(mag)) if mag.size else 0.0
    if scale is None:
        # MATLAB の自動倍率と同じ考え: 最も長い矢印が間隔の 0.9 倍
        k = 0.9 * sp / top if top > _EPS else 0.0
    else:
        k = _positive(scale, "scale")
    p0 = np.stack([R.ravel(), C.ravel()], axis=1).astype(np.float64)
    p1 = p0 + k * np.stack([vy.ravel(), vx.ravel()], axis=1)
    return p0, p1, k


def _stamp_segment(alpha, x0, y0, x1, y1, half):
    """線分の被覆率(縁 1 画素で線形に落とす)を ``alpha`` に最大値で重ねる。

    外接矩形だけを計算する(画像全体を毎回なめると矢印 400 本で十数秒かかる)。
    """
    H, W = alpha.shape
    pad = half + 1.0
    ca, cb = int(max(0, np.floor(min(x0, x1) - pad))), int(min(W - 1, np.ceil(max(x0, x1) + pad)))
    ra, rb = int(max(0, np.floor(min(y0, y1) - pad))), int(min(H - 1, np.ceil(max(y0, y1) + pad)))
    if ca > cb or ra > rb:
        return
    yy, xx = np.mgrid[ra:rb + 1, ca:cb + 1].astype(np.float64)
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / L2, 0.0, 1.0) if L2 > 0 else 0.0
    d = np.hypot(xx - (x0 + t * dx), yy - (y0 + t * dy))
    cov = np.clip(half + 0.5 - d, 0.0, 1.0)
    sub = alpha[ra:rb + 1, ca:cb + 1]
    np.maximum(sub, cov, out=sub)


def _stamp_triangle(alpha, tri):
    """三角形の被覆率(各辺からの符号つき距離で縁を 1 画素ぼかす)。"""
    H, W = alpha.shape
    t = np.asarray(tri, dtype=np.float64)
    ca, cb = int(max(0, np.floor(t[:, 0].min() - 1))), int(min(W - 1, np.ceil(t[:, 0].max() + 1)))
    ra, rb = int(max(0, np.floor(t[:, 1].min() - 1))), int(min(H - 1, np.ceil(t[:, 1].max() + 1)))
    if ca > cb or ra > rb:
        return
    yy, xx = np.mgrid[ra:rb + 1, ca:cb + 1].astype(np.float64)
    area = ((t[1, 0] - t[0, 0]) * (t[2, 1] - t[0, 1]) - (t[1, 1] - t[0, 1]) * (t[2, 0] - t[0, 0]))
    if abs(area) < 1e-12:
        return
    sgn = 1.0 if area > 0 else -1.0
    cov = np.ones_like(xx)
    for k in range(3):
        ax, ay = t[k]
        bx, by = t[(k + 1) % 3]
        ex, ey = bx - ax, by - ay
        n = np.hypot(ex, ey)
        sd = sgn * (ex * (yy - ay) - ey * (xx - ax)) / n      # 内側が正
        cov = np.minimum(cov, np.clip(sd + 0.5, 0.0, 1.0))
    sub = alpha[ra:rb + 1, ca:cb + 1]
    np.maximum(sub, cov, out=sub)


def _stamp_arrow(alpha, x0, y0, x1, y1, half, head_len, head_width):
    """起点 → 先端の矢印。矢じりが軸より長いときは軸長の 8 割まで相似に縮める。"""
    dx, dy = x1 - x0, y1 - y0
    L = float(np.hypot(dx, dy))
    if L <= 0.0:
        return
    if head_len > 0.8 * L:
        k = 0.8 * L / head_len
        head_len, head_width = head_len * k, head_width * k
    ux, uy = dx / L, dy / L
    bx, by = x1 - head_len * ux, y1 - head_len * uy
    _stamp_segment(alpha, x0, y0, bx, by, half)
    hw = 0.5 * head_width
    _stamp_triangle(alpha, [(x1, y1), (bx - hw * uy, by + hw * ux), (bx + hw * uy, by - hw * ux)])


def _composite(img, alpha, color):
    import annotate
    col = np.asarray(annotate._rgb(color), dtype=np.float64)
    a = alpha[..., None]
    return img * (1.0 - a) + col * a


def _canvas(background, shape_out):
    H, W = shape_out
    if background is None:
        return np.ones((H, W, 3))
    b = np.asarray(background, dtype=np.float64)
    if b.ndim == 2:
        b = np.repeat(b[..., None], 3, axis=2)
    if b.shape != (H, W, 3):
        raise ValueError(f"background must be ({H}, {W}) or ({H}, {W}, 3) — the flow grid "
                         f"times upsample — got {np.asarray(background).shape}")
    if not np.all(np.isfinite(b)):
        raise ValueError("background holds non-finite values")
    return np.clip(b, 0.0, 1.0)


_INK = (0.08, 0.08, 0.12)


def piv_quiver(flow, spacing=None, scale=None, upsample=8, background=None,
               color=_INK, width=1.5):
    """矢印図(MATLAB の ``quiver``)。返りは ``(h*upsample, w*upsample, 3)``。

    ``spacing`` 格子ごとに 1 本、起点を格子点に置き、先端を ``起点 + scale * v``
    に引く。``scale`` を省くと **最も長い矢印が間隔の 0.9 倍** になる(MATLAB の
    自動倍率と同じ考え方で、隣の矢印に重ならない)。**倍率は図ごとに変わる**
    ので、並べて比べる図では ``scale`` を固定する。長さが 1 画素に満たない
    矢印は描かない(向きの無い点は印と読まれる)。

    Args:
        flow: ``(2, h, w)``(``dy, dx``)。
        spacing: 矢印の間隔 [格子]。``None`` で長い辺に約 20 本。
        scale: 矢印の長さ = ``scale * 速さ`` [格子]。
        upsample: 出力の倍率(矢じりを描ける大きさにする)。
        background: ``(h*upsample, w*upsample)`` か ``(…, 3)``。``None`` で白。
            色相図(``piv_flow_to_rgbimage`` を拡大したもの)や LIC を敷ける。
        color / width: 矢印の色(palette の役割名か RGB)と軸の太さ [px]。
            既定は黒に近い墨色(色相図を敷いても読める)。
    Returns:
        ``(h*upsample, w*upsample, 3)`` float64、値域 [0, 1]。
    """
    f = _flow(flow)
    _needs_a_grid(f, "piv_quiver")
    if not np.all(np.isfinite(f)):
        raise ValueError("piv_quiver: flow holds non-finite values; replace outliers first")
    H, W = f.shape[1:]
    up = int(upsample)
    if up < 2:
        raise ValueError(f"upsample must be >= 2 (an arrowhead needs pixels), got {upsample}")
    sp = max(1, int(round(max(H, W) / 20.0))) if spacing is None else int(spacing)
    if sp < 1:
        raise ValueError(f"spacing must be >= 1, got {spacing}")
    half = 0.5 * _positive(width, "width")
    p0, p1, _k = _quiver_segments(f, sp, scale)
    img = _canvas(background, (H * up, W * up))
    alpha = np.zeros((H * up, W * up))
    head = max(4.0, 0.3 * sp * up)
    for a, b in zip(p0, p1):
        x0, y0 = (a[1] + 0.5) * up - 0.5, (a[0] + 0.5) * up - 0.5
        x1, y1 = (b[1] + 0.5) * up - 0.5, (b[0] + 0.5) * up - 0.5
        if np.hypot(x1 - x0, y1 - y0) < 1.0:
            continue
        _stamp_arrow(alpha, x0, y0, x1, y1, half, head, 0.7 * head)
    return _composite(img, alpha, color)


def piv_streamline_image(flow, upsample=8, background=None, color=_INK, width=1.5,
                         arrows=True, **stream_kw):
    """流線図(MATLAB の ``streamslice``)。返りは ``(h*upsample, w*upsample, 3)``。

    :func:`piv_streamlines` の等間隔配置で線を引き、各線の弧長の中ほどに
    向きの矢じりを 1 つ置く(LIC と違って**前後が読める**)。線の間隔が揃うので、
    **線の密度では速さを表さない** —— 速さを見たいときは ``background`` に
    ``piv_flow_magnitude`` か色相図を敷く。

    Args:
        flow: ``(2, h, w)``。
        upsample / background / color / width: :func:`piv_quiver` と同じ。
        arrows: 矢じりを置くか。
        **stream_kw: :func:`piv_streamlines` へ素通し(``separation`` など)。
    Returns:
        ``(h*upsample, w*upsample, 3)`` float64、値域 [0, 1]。
    """
    f = _flow(flow)
    up = int(upsample)
    if up < 2:
        raise ValueError(f"upsample must be >= 2, got {upsample}")
    half = 0.5 * _positive(width, "width")
    st = piv_streamlines(f, **stream_kw)
    H, W = f.shape[1:]
    img = _canvas(background, (H * up, W * up))
    alpha = np.zeros((H * up, W * up))
    head = max(5.0, 0.35 * st["separation"] * up)
    for pts in st["paths"]:
        if len(pts) < 2:
            continue
        xy = np.stack([(pts[:, 1] + 0.5) * up - 0.5, (pts[:, 0] + 0.5) * up - 0.5], axis=1)
        for (x0, y0), (x1, y1) in zip(xy[:-1], xy[1:]):
            _stamp_segment(alpha, x0, y0, x1, y1, half)
        if arrows:
            s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
            if s[-1] < 2.0 * head:
                continue
            k = int(np.searchsorted(s, 0.5 * s[-1]))
            j = int(np.searchsorted(s, s[k] - head))
            # 矢じりだけを描く(軸は流線そのもの)
            ux, uy = xy[k] - xy[j]
            n = float(np.hypot(ux, uy))
            if n <= 0:
                continue
            ux, uy = ux / n, uy / n
            tx, ty = xy[k]
            bx, by = tx - head * ux, ty - head * uy
            hw = 0.35 * head
            _stamp_triangle(alpha, [(tx, ty), (bx - hw * uy, by + hw * ux),
                                    (bx + hw * uy, by - hw * ux)])
    return _composite(img, alpha, color)
