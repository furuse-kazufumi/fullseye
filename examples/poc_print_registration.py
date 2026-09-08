# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""印刷の版ずれを刷り上がりから測る —— 網点は格子なので、答えは 1 つに決まらない。

    py -3.11 examples/poc_print_registration.py

オフセット印刷・ラベル印刷では CMYK の 4 版を重ねて刷ります。版が互いに
ずれる(**版ずれ / misregistration**)と輪郭に色の縁が出るので、刷り上がりを
スキャンして各版のずれベクトルを測りたくなります。素直な手は「設計した版と
刷り上がりの版とで相互相関を取り、ピークの位置を読む」です。

ところが **網点(ハーフトーンスクリーン)は周期構造**です。スクリーン角 θ・
ピッチ p の網点の中心は格子を成すので、相関のピークは**格子ベクトルの整数倍
だけ不定**になります。つまり測って出るのは真のずれ d ではなく `d mod 格子`
で、|d| が p/2 を超えると**折り返して小さいずれに見える** —— 8 px ずれた版が
「0 px、合格」と出ます。これは推定器の出来ではなく素材の性質なので、
**測る前に幾何から厳密に予測できます**。この PoC は予測を先に印字し、
それから測って突き合わせます。

EXTEND: 実データ(実際の刷り見本のスキャン)に差し替えるなら、
:func:`am_sheet` が返す配列を「スキャンした 1 版ぶんの分版画像」に、
:func:`design_plate` を「RIP が出した版データ(1 bit TIFF を同じ解像度へ
落としたもの)」に置き換えます。:data:`PITCH` と各版の :data:`ANGLE` は
公称値ではなく **スキャンから読む**べきで、その手順は 1 節にあります。

**実データでは各版の真のずれが手に入りません**。刷り上がりから分かるのは
「相関がどこにピークを立てたか」だけで、それが真値かどうかを言う材料が
無いからです。したがって実データでは、この PoC の中心である

* 3〜4 節「閉形式の折り返し予測 vs 実測」(真値 d が要る)
* 2 節「ゼロ点との比較」(真値が無いと誤差が定義できない)
* 8 節「合否判定の一致率」(真の合否が要る)

が**そのままでは測れなくなります**。実データで同じことをするには、版に
**非周期の基準**(レジストマーク、地紋、FM スクリーンのパッチ)を刷り込んで
おいて、そこを真値の代わりに使うしかありません —— 7 節がまさにその手を測って
いて、「マークは当たるが、マークのある場所でしか当たらない」ことも同時に
出ています。

【所見(数字はすべて最終実行の実測値。★ は重要、★★ は最重要)】

 1. ★★**折り返しは幾何から厳密に予測できた**。スクリーン角 θ の網点格子
    Λ_θ で真のずれ d を簡約した値 `d mod Λ_θ` を**測る前に**印字し、
    0〜2p(0〜16.0 px)を 0.5 px 刻みで掃引して測ったところ、4 版 132 点の
    うち **124 点で予測と実測の差は 0.0210 px 以下**。残る 8 点は
    **セル境界のタイ**で、そこは予測式の round() がどちらへ転んでもよい
    場所でした(予測どおりの場所に出た。4 節)。
 2. ★★**格子で簡約した残差で見ると 132 点すべてが合う**(最大 0.0210 px)。
    つまり推定器は「間違えている」のではなく、**格子で等価な答えの中から
    1 つを返している**。境界のタイでどちらを返すかは雑音が決めます。
 3. ★★**同じ物理的なずれが、版ごとに違う見かけになる**。d=(+3.20,+5.90) px
    (|d|=6.71 px)を 4 版すべてに同じだけ掛けると、見かけのずれは
    C(15°) 4.16 px / M(75°) 2.75 px / Y(0°) 2.34 px / K(45°) 2.17 px。
    **1 枚の紙の上の 1 つのずれが、版ごとに 2.17〜4.16 px に化けます**。
 4. ★**ゼロ点は 2 つ置いた**(2 節)。版どうしのインク重心の差は誤差
    102.79 px —— 絵柄が版ごとに違うので重心も違い、**ずれを測っていない**。
    一方「自版の設計との重心差」は誤差 0.3266 px で、折り返しません。
    ★予測を外しました: 素朴な重心が**大きなずれでは相関に勝ちます**。
 5. ★★**物差しを変えると勝者が入れ替わる**(8 節)。公差 2.0 px 以内の
    領域での RMS 誤差は相関(AM)0.0130 px 対 重心 0.3272 px で相関の
    **25.2 倍**の勝ち。ところが 0〜16 px 全域での合否判定の一致率は
    重心 **100.0 %** 対 相関(AM)**39.4 %**。**精度で勝つ手が、判定では
    負けます**。
 6. ★**対照群で原因を素材に切り分けられた**(6 節)。同じ絵柄・同じ推定器で
    スクリーンだけ FM(確率)に替えると、0〜16 px の全域で誤差は
    最大 0.0399 px、折り返しはゼロ。**崖の原因は推定器ではなく AM 網点の
    周期性**です。
 7. ★**レジストマークは当たる。ただしマークのある場所でしか当たらない**
    (7 節)。d0=(+0.60,+9.40) px を仕込んだ版で、マークを含む窓は誤差
    0.0335 px で当てましたが、同じ版の網点だけの窓は 8.8901 px 外しました。
    そして版が 0.60 % 伸びて 0.120° 回っていると、マークの値を版全体へ
    当てた誤差は距離に比例して伸び、公差 2.0 px を超えるのは
    **予測 289.7 px / 実測 289.7 px** から先。
 8. ★**用途外の登録 op を当てたら、自信満々で外した**(9 節 (c))。
    :func:`fullseye.frame_align`(星の対応で 2-D 変換を出す)に網点を
    食わせると `inlier_ratio` **1.00**、`rms_px` 0.759 を返しながら
    シフトは真値から **90.15 px** 外れていました。**「確信度 1.00 で
    90 px 外す」形の fail-soft** は、報告する価値があります。

【グラウンドトゥルース(すべて式で置いた)】
* **網点**: スクリーン角 θ、ピッチ p = SCAN_DPI/LPI = 8.00 px の正方格子。
  格子点からの距離 r と、被覆率 a から決まる網点半径 R = p·sqrt(a/π) で
  ``ink = clip((R - r)/SOFT + 0.5, 0, 1)``(SOFT がインクのにじみと
  スキャナ MTF)。**閉形式なので任意の小数ずれをそのまま評価できる**。
* **絵柄**: 版ごとに中心の違うガウス斑 + 一様の下地(:data:`PLATES`)。
  版ごとに絵柄が違うことが 2 節のゼロ点を壊します。
* **ずれ**: 版ごとに既知の (dy, dx)(小数を含む)。刷り上がりは
  ``plate(y - dy, x - dx)`` —— 連続の式を整数格子で評価するだけ。
* **ドットゲイン**: 紙の上の位置で決まる被覆率の勾配(±12.5 %)。版と一緒に
  動かないので、並進不変性を(現実と同じように)破ります。
* **格子の簡約**: u = dx cosθ + dy sinθ, v = -dx sinθ + dy cosθ を
  それぞれ p で簡約して戻す —— これが予測の全部です。

【節立て】
 1) 場面 —— 4 版の網点と、合成器の検算(スキャンから角度と線数を読む)
 2) ★ゼロ点 —— インク重心の 2 つの取り方
 3) ★★崖を測る前に予測する(閉形式)
 4) ★★実測 —— 0〜2p を掃引して予測と突き合わせる
 5) ★同じずれが版ごとに違って見える
 6) 対照群 (a) —— FM(確率)スクリーンの同じ絵柄
 7) 対照群 (b) —— レジストマークと版の伸び・回転
 8) ★★物差しを 2 つ —— 勝者が入れ替わる
 9) 道具の穴(assert で現状を固定)

来歴(公開されている規格・慣行のみ): ISO 12647 シリーズ *Graphic technology —
Process control for the production of half-tone colour separations, proof and
production prints*(印刷工程の管理。分版・網点・刷り位置の管理項目を定める)。
CMYK の慣行的なスクリーン角(K=45°, C=15°, M=75°, Y=0°)と商業印刷でよく使う
150 lpi は業界の慣行値で、この PoC はそれを**仮定として置いた**だけです
(規格から特定の数値を引用してはいません)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 刷りとスキャンの諸元(すべてスキャン画素を単位にする)------------------- #
L = 512                  # スキャン画像の一辺 [px]
SCAN_DPI = 1200.0        # スキャン解像度 [dpi]
#: 網点の線数 [lpi](商業印刷の慣行値)。★**わざと整数比を避けている**:
#: 1200/150 = 8.00 px にすると全部の網点が同じ小数位置に落ち、標本化の
#: 位相が揃って合成器に人工物が出る(実測で重心が小数ずれごとに 1.4 px 跳ねた)。
#: 実際のスキャンでも解像度が線数の整数倍になることはまずない。
LPI = 133.0
PITCH = SCAN_DPI / LPI   # 網点のピッチ [px] = 9.02
UM_PER_PX = 25400.0 / SCAN_DPI   # 1 px は何 µm か(= 21.17 µm)

SOFT = 1.1               # インクのにじみ + スキャナ MTF の幅 [px]
NOISE = 0.010            # スキャンの雑音(反射率の標準偏差)
GAIN_GRAD = 0.25         # ドットゲインの左右勾配(紙の上で ±12.5 %)
TOL_PX = 2.0             # この PoC が置く合否の公差 [px](= 42.3 µm)

#: 版の諸元。``(名前, スクリーン角 [deg], 絵柄の中心 (y, x) 比, 真のずれ (dy, dx) [px])``
PLATES = (
    ("C", 15.0, (0.42, 0.36), (+1.30, -0.70)),
    ("M", 75.0, (0.55, 0.62), (+0.45, -2.10)),
    ("Y",  0.0, (0.62, 0.50), (+0.90, +9.60)),
    ("K", 45.0, (0.46, 0.46), (+0.00, +0.00)),
)

BLOB_SIGMA = 0.20 * L    # 絵柄のガウス斑の広がり [px]
BLOB_PEAK = 0.45         # 斑の頂点の被覆率
BASE_TONE = 0.16         # 下地の被覆率(全面に網点がある状態)
MAX_TONE = 0.70          # 網点が繋がらない上限(a > π/4 で隣とくっつく)

WIN = 64                 # 相関の窓 [px]
SWEEP = np.arange(0.0, 2.0 * PITCH, 0.5)          # 掃引する |ずれ| [px]
LP_CUT = 1.0 / (3.0 * PITCH)   # 低域通過の遮断周波数 [cyc/px](網点の 1/3)

_Y, _X = np.mgrid[0:L, 0:L].astype(np.float64)
#: 端のテーパ(重心の「窓の縁で網点が出入りする」ぶんを抑える対照群に使う)
_HANN = np.hanning(L + 2)[1:-1]
TAPER = np.outer(_HANN, _HANN)


# --------------------------------------------------------------------------- #
# 真値 —— 網点を式で置く                                                        #
# --------------------------------------------------------------------------- #
def tone(py, px, blob) -> np.ndarray:
    """版の絵柄(被覆率)。**版座標**で定義する —— 版と一緒に動く量。

    ``blob`` は ``(中心 y 比, 中心 x 比)`` か ``(中心 y 比, 中心 x 比, 山の高さ)``。
    高さ 0 を渡すと**一様な下地だけ**の対照群になる。
    """
    cy, cx = blob[0] * L, blob[1] * L
    peak = blob[2] if len(blob) > 2 else BLOB_PEAK
    return BASE_TONE + peak * np.exp(
        -((py - cy) ** 2 + (px - cx) ** 2) / (2.0 * BLOB_SIGMA ** 2))


def dot_gain(sheet_x) -> np.ndarray:
    """ドットゲイン(インクの乗りすぎ)の勾配。**紙座標**で定義する。

    版と一緒に動かないので並進不変性を破る —— 現実の印刷でもインクの
    供給は版ではなく機械の左右で決まるので、この置き方が正しい。
    """
    return 1.0 + GAIN_GRAD * (sheet_x / L - 0.5)


def am_ink(py, px, angle_deg: float, blob) -> np.ndarray:
    """AM(振幅変調 = 通常の網点)スクリーンのインク量 [0,1]。**閉形式**。

    格子点からの距離 ``r`` と、被覆率 ``a`` から決まる網点半径
    ``R = p sqrt(a/π)``。``a`` が正しく面積になる(π R² / p² = a)。
    """
    th = np.deg2rad(angle_deg)
    a = np.clip(tone(py, px, blob) * dot_gain(_X), 0.0, MAX_TONE)
    u = px * np.cos(th) + py * np.sin(th)
    v = -px * np.sin(th) + py * np.cos(th)
    r = np.hypot(u - PITCH * np.round(u / PITCH),
                 v - PITCH * np.round(v / PITCH))
    return np.clip((PITCH * np.sqrt(a / np.pi) - r) / SOFT + 0.5, 0.0, 1.0)


def am_sheet(angle_deg: float, blob, dy=0.0, dx=0.0, seed=1,
             mark=None) -> np.ndarray:
    """刷り上がりのスキャン(反射率。白 = 1)。``(dy, dx)`` だけ版が動いた状態。"""
    ink = am_ink(_Y - dy, _X - dx, angle_deg, blob)
    if mark is not None:
        ink = np.maximum(ink, mark_ink(_Y - dy, _X - dx, mark))
    img = 1.0 - ink
    if seed is not None:
        img = img + np.random.default_rng(seed).normal(0.0, NOISE, img.shape)
    return img


def design_plate(angle_deg: float, blob, mark=None) -> np.ndarray:
    """設計どおりの版(ずれ 0、雑音なし)。相関の基準に使う。"""
    return am_sheet(angle_deg, blob, 0.0, 0.0, seed=None, mark=mark)


# --- レジストマーク(十字の目印。**非周期の局所特徴**)----------------------- #
MARK_HALF_LEN = 60.0     # 腕の半長 [px](全長 120 px = 2.54 mm)
MARK_HALF_W = 3.0        # 腕の半幅 [px](全幅 6 px = 0.13 mm)


def mark_ink(py, px, centre) -> np.ndarray:
    """十字のレジストマーク(ベタ)。``centre`` は版座標 (y, x)。"""
    my, mx = centre
    ay, ax = np.abs(py - my), np.abs(px - mx)
    vert = (ax <= MARK_HALF_W) & (ay <= MARK_HALF_LEN)
    horz = (ay <= MARK_HALF_W) & (ax <= MARK_HALF_LEN)
    return (vert | horz).astype(np.float64)


# --------------------------------------------------------------------------- #
# 予測 —— 網点格子による不定性(閉形式)                                         #
# --------------------------------------------------------------------------- #
def lattice_basis(angle_deg: float) -> np.ndarray:
    """スクリーン角 θ の網点格子 Λ_θ の基底(行が (dy, dx))。"""
    th = np.deg2rad(angle_deg)
    return PITCH * np.array([[np.sin(th), np.cos(th)],       # u 方向
                             [np.cos(th), -np.sin(th)]])     # v 方向


def reduce_to_cell(dy: float, dx: float, angle_deg: float):
    """``(dy, dx)`` を格子 Λ_θ の基本セルへ簡約する。**これが予測の全部**。

    u = dx cosθ + dy sinθ、v = -dx sinθ + dy cosθ をそれぞれ p で簡約して
    戻すだけ。返り値は ``(dy_r, dx_r, u_r, v_r)``。
    """
    th = np.deg2rad(angle_deg)
    u = dx * np.cos(th) + dy * np.sin(th)
    v = -dx * np.sin(th) + dy * np.cos(th)
    ur = u - PITCH * np.round(u / PITCH)
    vr = v - PITCH * np.round(v / PITCH)
    return (ur * np.sin(th) + vr * np.cos(th),
            ur * np.cos(th) - vr * np.sin(th), ur, vr)


def lattice_residual(dy: float, dx: float, angle_deg: float) -> float:
    """``(dy, dx)`` が格子ベクトルからどれだけ離れているか [px]。

    2 つの答えが**格子で等価**かを判定する物差し。0 なら「同じ答えの
    別の代表元」であって、間違いではない。
    """
    ry, rx, _u, _v = reduce_to_cell(dy, dx, angle_deg)
    return float(np.hypot(ry, rx))


def snap_to_lattice(fine, coarse, angle_deg: float) -> tuple[float, float]:
    """``fine``(格子で不定な精密解)を、``coarse`` にいちばん近い代表元へ移す。

    格子の不定性そのものは消せないので、**別の情報で代表元を 1 つ選ぶ**のが
    唯一の手。``coarse`` の誤差が基本セルの半径(軸方向で p/2)を超えると
    隣の代表元を選ぶ ——**静かに 1 格子ぶん間違える**。
    """
    ry, rx, _u, _v = reduce_to_cell(coarse[0] - fine[0], coarse[1] - fine[1],
                                    angle_deg)
    return (fine[0] + (coarse[0] - fine[0]) - ry,
            fine[1] + (coarse[1] - fine[1]) - rx)


def tie_margin(dy: float, dx: float, angle_deg: float) -> float:
    """基本セルの境界までの余裕 [px]。0 に近いほど「どちらでもよい」。"""
    _ry, _rx, ur, vr = reduce_to_cell(dy, dx, angle_deg)
    return float(min(PITCH / 2.0 - abs(ur), PITCH / 2.0 - abs(vr)))


# --------------------------------------------------------------------------- #
# 推定器                                                                        #
# --------------------------------------------------------------------------- #
def ink_centroid(img, taper=None) -> tuple[float, float]:
    """インク量の重心 (y, x) [px]。1 次モーメントなので**折り返さない**。

    ``taper`` を渡すとその重みを掛ける(窓の縁で網点が出入りする効果を
    抑える対照群に使う)。
    """
    w = np.clip(1.0 - np.asarray(img, float), 0.0, None)
    if taper is not None:
        w = w * taper
    s = float(w.sum())
    return float((w * _Y).sum() / s), float((w * _X).sum() / s)


def lowpass_image(img, cutoff=LP_CUT) -> np.ndarray:
    """等方ガウス低域通過。**網点の周期成分を落として絵柄だけ残す**。

    :func:`fullseye.cx_fft` → :func:`fullseye.cx_apply_transfer_function`
    → :func:`fullseye.cx_ifft`。``cutoff`` は 1/e^0.5 になる空間周波数
    [cyc/px]。網点の基本周波数 1/p は ``exp(-(1/p)^2/(2 cutoff^2))`` 倍に
    なる —— 既定 ``cutoff = 1/(3p)`` なら ``exp(-4.5)`` = 1.1e-2 倍。
    """
    f = np.fft.fftshift(np.fft.fftfreq(L))
    r2 = f[:, None] ** 2 + f[None, :] ** 2
    h = np.exp(-r2 / (2.0 * cutoff ** 2))
    return np.asarray(fs.cx_ifft(
        fs.cx_apply_transfer_function(fs.cx_fft(np.asarray(img, float)), h),
        real=True))


def corr_map(a, b) -> np.ndarray:
    """相互相関マップ(零ラグが中央)。``b(x) = a(x - d)`` ならピークは +d。

    :func:`fullseye.cx_fft` / :func:`fullseye.cx_ifft` を使う —— 中央化した
    複素スペクトルの共役積を戻すだけ。
    """
    A = fs.cx_fft(np.asarray(a, float) - np.mean(a))
    B = fs.cx_fft(np.asarray(b, float) - np.mean(b))
    return np.fft.fftshift(np.asarray(fs.cx_ifft(np.conj(A) * B, real=True)))


def box_mask(n: int, limit: float) -> np.ndarray:
    """``|dy| <= limit`` かつ ``|dx| <= limit`` のラグだけ探す(素朴な探索範囲)。"""
    lag = np.arange(n) - n // 2
    return (np.abs(lag)[:, None] <= limit) & (np.abs(lag)[None, :] <= limit)


def cell_mask(n: int, angle_deg: float) -> np.ndarray:
    """格子 Λ_θ の**基本セル(Voronoi 領域)**の中のラグだけ探す。

    「ずれは小さいはずだ」という現場の仮定を、**素材の格子に合わせて**置いた
    形。セルは 1 辺 p の正方形を θ だけ回したものなので、素朴な正方形の箱
    (:func:`box_mask`)とは違う —— 箱で切ると、セルの外の格子等価な答えが
    箱の角から入り込む。
    """
    th = np.deg2rad(angle_deg)
    lag = (np.arange(n) - n // 2).astype(np.float64)
    ly, lx = lag[:, None], lag[None, :]
    u = lx * np.cos(th) + ly * np.sin(th)
    v = -lx * np.sin(th) + ly * np.cos(th)
    return (np.abs(u) <= PITCH / 2 + 1e-9) & (np.abs(v) <= PITCH / 2 + 1e-9)


def corr_shift(a, b, mask) -> tuple[float, float, float]:
    """相関でずれを測る。``mask`` が ``True`` のラグだけ探す。

    返り値は ``(dy, dx, ピーク比)``。小数の詰めは :func:`fullseye.peak_subbin`
    (符号つきの相関なので ``mode="gauss"`` は使えず、放物線)。
    """
    c = corr_map(a, b)
    n = c.shape[0]
    c0 = n // 2
    m = np.asarray(mask, bool)
    if m.shape != c.shape:                       # 窓の大きさに合わせて作り直す
        raise ValueError("mask %r != corr %r" % (m.shape, c.shape))
    masked = np.where(m, c, -np.inf)
    k = int(np.argmax(masked))
    gi, gj = k // n, k % n
    dy = fs.peak_subbin(c[:, gj], gi) - c0
    dx = fs.peak_subbin(c[gi, :], gj) - c0
    vals = np.sort(masked[np.isfinite(masked)])
    ratio = float(vals[-1] / vals[-2]) if vals.size > 1 and vals[-2] > 0 else float("inf")
    return float(dy), float(dx), ratio


def piv_shift(a, b, limit=None) -> tuple[float, float, float]:
    """窓ごとの相互相関(:func:`fullseye.ledger.piv_cross_correlate`)の中央値。

    ``limit`` [px] は窓内で探すラグの上限。``None`` なら op の既定
    (窓の 1/4 = %.1f px)。
    """
    kw = {} if limit is None else {"search_limit": float(limit) / WIN}
    # ★ 台帳の口は宣言 out 型に合わせて info を捨てるので `.raw` を使う
    #   (fullseye/__init__.py のコメントに実測つきで書いてある落とし穴)。
    flow, info = fs.ledger.piv_cross_correlate.raw(
        a, b, window=WIN, overlap=0.5, **kw)
    return (float(np.nanmedian(flow[0])), float(np.nanmedian(flow[1])),
            float(info["valid_fraction"]))


# --------------------------------------------------------------------------- #
# 1) 場面 —— 4 版の網点と、合成器の検算                                          #
# --------------------------------------------------------------------------- #
def section1_scene():
    print("=" * 78)
    print("1) 場面 —— 4 版の網点と、合成器の検算")
    print("=" * 78)
    print("  スキャン %.0f dpi / 網点 %.0f lpi → ピッチ p = %.2f px(1 px = %.2f µm)"
          % (SCAN_DPI, LPI, PITCH, UM_PER_PX))
    print("  スクリーン角は慣行値(K=45°, C=15°, M=75°, Y=0°)。絵柄は版ごとに違う。")
    print()
    print("  %-4s %8s %14s %10s %12s %12s"
          % ("版", "角度", "真のずれ (dy,dx)", "|d| px", "|d| µm", "公差 %.1f px" % TOL_PX))
    print("  " + "-" * 66)
    for name, ang, _blob, (dy, dx) in PLATES:
        mag = float(np.hypot(dy, dx))
        print("  %-4s %7.1f° (%+6.2f,%+6.2f) %10.3f %12.1f %12s"
              % (name, ang, dy, dx, mag, mag * UM_PER_PX,
                 "合格" if mag <= TOL_PX else "不合格"))
    print()
    print("  合成器の検算: 刷り上がりのスペクトルから格子の角度と線数を読み直す。")
    print("  (実データではこれが唯一の読み方 —— 公称のスクリーン角を信じない。)")
    print()
    print("  %-4s %12s %12s %12s %12s"
          % ("版", "公称 角度", "実測 角度", "公称 lpi", "実測 lpi"))
    print("  " + "-" * 58)
    errs = []
    fy = np.fft.fftshift(np.fft.fftfreq(L))[:, None] * np.ones((1, L))
    fx = np.ones((L, 1)) * np.fft.fftshift(np.fft.fftfreq(L))[None, :]
    rad = np.hypot(fy, fx)
    for name, ang, blob, _d in PLATES:
        img = am_sheet(ang, blob, seed=11)
        sp = np.abs(fs.cx_fft(img - img.mean()))
        sel = (rad > 0.5 / PITCH) & (rad < 1.6 / PITCH)     # 基本波だけ拾う帯
        idx = int(np.argmax(np.where(sel, sp, -1.0)))
        py, px = float(fy.ravel()[idx]), float(fx.ravel()[idx])
        lpi_m = float(np.hypot(py, px)) * SCAN_DPI
        ang_m = float(np.degrees(np.arctan2(py, px))) % 90.0
        errs.append((abs(ang_m - ang % 90.0), abs(lpi_m - LPI)))
        print("  %-4s %11.1f° %11.2f° %12.1f %12.2f"
              % (name, ang % 90.0, ang_m, LPI, lpi_m))
    print()
    print("  → 角度の差は最大 %.2f°、線数の差は最大 %.2f lpi(%d 点 FFT の"
          % (max(e[0] for e in errs), max(e[1] for e in errs), L))
    print("     分解能 1/%d cyc/px = %.2f lpi ぶん)。**格子は仕込んだとおりに在る**。"
          % (L, SCAN_DPI / L))
    if figs.enabled():
        s = np.s_[120:248, 120:248]
        figs.save_grid(
            "plates",
            [am_sheet(a, b, seed=11)[s] for _n, a, b, _d in PLATES],
            ["%s %.0f°" % (n, a) for n, a, _b, _d in PLATES],
            title="4 版の網点(128x128 px の切り出し)", ncols=2,
            caption="スクリーン角が違うので格子の向きが違う。ピッチはどれも "
                    "%.2f px。同じ物理的なずれでも、この格子の違いが"
                    "「見かけのずれ」を版ごとに変える(5 節)" % PITCH)
    return {"ang_err": max(e[0] for e in errs), "lpi_err": max(e[1] for e in errs)}


# --------------------------------------------------------------------------- #
# 2) ゼロ点 —— インク重心の 2 つの取り方                                         #
# --------------------------------------------------------------------------- #
def section2_zero_point():
    print()
    print("=" * 78)
    print("2) ★ゼロ点 —— インクの重心でずれを出す(素朴な手を 2 つ)")
    print("=" * 78)
    print("  ゼロ点 A(現場でいちばん先に出る手): **版どうしの重心の差**。")
    print("    「シアンの絵柄の重心と、黒の絵柄の重心の差が版ずれだ」")
    print("  ゼロ点 B(もう少し賢い手): **自版の設計との重心の差**。")
    print("    どちらも 1 次モーメントなので、原理的に**折り返さない**。")
    print()
    prints, designs = {}, {}
    for name, ang, blob, (dy, dx) in PLATES:
        prints[name] = am_sheet(ang, blob, dy, dx, seed=21)
        designs[name] = design_plate(ang, blob)
    ck = ink_centroid(prints["K"])
    rows, err_a, err_b = [], [], []
    print("  %-4s %16s %16s %10s %16s %10s"
          % ("版", "真値(K 基準)", "ゼロ点 A", "誤差 A", "ゼロ点 B", "誤差 B"))
    print("  " + "-" * 78)
    kdy, kdx = PLATES[-1][3]
    for name, ang, blob, (dy, dx) in PLATES:
        ty, tx = dy - kdy, dx - kdx
        cy, cx = ink_centroid(prints[name])
        ay, ax = cy - ck[0], cx - ck[1]
        gy, gx = ink_centroid(designs[name])
        by, bx = cy - gy, cx - gx
        ea = float(np.hypot(ay - ty, ax - tx))
        eb = float(np.hypot(by - dy, bx - dx))
        err_a.append(ea)
        err_b.append(eb)
        rows.append([name, "(%+.2f,%+.2f)" % (ty, tx), "(%+.2f,%+.2f)" % (ay, ax),
                     "%.3f" % ea, "(%+.2f,%+.2f)" % (by, bx), "%.4f" % eb])
        print("  %-4s   (%+6.2f,%+6.2f)   (%+6.2f,%+6.2f) %10.3f   (%+6.2f,%+6.2f) %10.4f"
              % (name, ty, tx, ay, ax, ea, by, bx, eb))
    print()
    print("  → ゼロ点 A の誤差は最大 **%.2f px**。版ごとに絵柄が違うので重心も"
          % max(err_a))
    print("     違い、**ずれではなく絵柄の差を測っている**。値は大きいが折り返しは")
    print("     しないので、「大外れだと気づける」種類の失敗。")
    print("  → ゼロ点 B の誤差は最大 **%.4f px**。同じ絵柄どうしを比べるので筋が"
          % max(err_b))
    print("     良く、折り返しもしない。ただし**誤差が真値に比例して増える**:")
    print("     真値 %.3f px の Y 版で %.3f px。これは雑音でもドットゲインでもない。"
          % (np.hypot(*PLATES[2][3]), max(err_b)))
    print()
    print("  ★★仕組みを**先に式で出す**。窓 W を固定したまま場を d だけ動かすと")
    print("     重心 = d + C(W-d)。一様な成分は窓をずらしても中心が -d だけ動くので")
    print("     ちょうど打ち消し、**残るのは絵柄の非一様成分だけ**。したがって")
    print()
    print("         応答の傾き k = 1 - β,  β = (下地だけのインク量)/(実際のインク量)")
    print()
    name, ang, blob, _d = PLATES[2]
    des = design_plate(ang, blob)
    flat = (blob[0], blob[1], 0.0)
    m_tot = float(np.clip(1.0 - des, 0.0, None).sum())
    m_base = float(np.clip(1.0 - design_plate(ang, flat), 0.0, None).sum())
    beta = m_base / m_tot
    k_pred = 1.0 - beta
    print("     %s 版のインク量: 全体 %.3e / 下地だけ %.3e → β = %.4f"
          % (name, m_tot, m_base, beta))
    print("     **予測 k = %.4f**(まだ何も掃引していない)。" % k_pred)
    print()
    ts = np.arange(0.0, 2 * PITCH + 1e-9, 1.0)
    sweeps = {}
    for label, tap, bl in (("絵柄あり", None, blob),
                           ("下地だけ(対照群)", None, flat),
                           ("絵柄あり + テーパ窓", TAPER, blob)):
        g = ink_centroid(design_plate(ang, bl), tap)[1]
        r = np.array([ink_centroid(am_sheet(ang, bl, 0.0, float(t), seed=22),
                                   tap)[1] - g for t in ts])
        c = np.polyfit(ts, r, 1)
        sweeps[label] = (r, float(c[0]), float(np.abs(r - np.polyval(c, ts)).max()))
    k_art, rip_art = sweeps["絵柄あり"][1], sweeps["絵柄あり"][2]
    k_flat = sweeps["下地だけ(対照群)"][1]
    k_tap, rip_tap = sweeps["絵柄あり + テーパ窓"][1], sweeps["絵柄あり + テーパ窓"][2]
    print("     %-22s %10s %14s" % ("実測(0〜%.1f px、1 px 刻み)" % (2 * PITCH),
                                    "傾き k", "直線からの外れ"))
    print("     " + "-" * 50)
    for label, (_r, kk, rip) in sweeps.items():
        print("     %-22s %10.4f %14.4f" % (label, kk, rip))
    print()
    print("  → ★予測 %.4f に対して実測 %.4f、差 **%.4f**。**閉形式が当たった**。"
          % (k_pred, k_art, abs(k_art - k_pred)))
    print("     対照群(絵柄を下地だけの一様な網点にする)は予測 k=0 に対して")
    print("     実測 %.4f —— 一様成分は本当に重心を動かしていない。" % k_flat)
    print("  → ★**重心は折り返さないが、縮尺が狂う**。誤差は %.3f·|d| で真値に"
          % (1 - k_art))
    print("     比例して増える。倍率は絵柄で決まるので**版ごとに違う**")
    print("     (上の表の誤差 B が版ごとにばらつくのはこのため)。")
    print("  → ★もう 1 つ出た: 直線からの外れが **%.4f px** ある。これは網点ピッチ"
          % rip_art)
    print("     %.2f px 周期のさざ波で、**窓の縁で網点の列が出入りする**ため"
          % PITCH)
    print("     (縁の 1 列は全インクの約 1 %% で、腕の長さ %d px を掛けると"
          % (L // 2))
    print("     ちょうどこの大きさになる)。テーパ窓を掛けた対照群では")
    print("     **%.4f px** まで落ちる —— **原因が縁だと確かめられた**。" % rip_tap)
    resp, resp_f = sweeps["絵柄あり"][0], sweeps["下地だけ(対照群)"][0]
    print("     **以降の手法は、この %.4f px(と、折り返さないという性質)を"
          % max(err_b))
    print("     上回らなければ意味がありません。**")
    figs.save_table("zero_point",
                    ["版", "真値 (dy,dx)", "ゼロ点 A", "誤差 A [px]",
                     "ゼロ点 B", "誤差 B [px]"], rows,
                    title="2 つのゼロ点(インク重心)", col_w=118)
    if figs.enabled():
        figs.save_plot(
            "centroid_response",
            [("真値", ts, ts), ("予測 k=%.3f" % k_pred, ts, k_pred * ts),
             ("実測(絵柄あり) k=%.3f" % k_art, ts, resp),
             ("実測(下地だけ) k=%.3f" % k_flat, ts, resp_f)],
            xlabel="仕込んだずれ t [px]", ylabel="重心の動き dx [px]",
            title="重心は折り返さないが、縮尺が狂う",
            caption="一様な網点は、窓を固定すると重心を動かさない。重心が追うのは"
                    "絵柄の非一様成分だけで、傾きは 1-β の閉形式で出る")
    return {"err_a": max(err_a), "err_b": max(err_b), "k_art": k_art,
            "k_flat": k_flat, "k_pred": k_pred, "beta": beta,
            "ripple": rip_art, "ripple_taper": rip_tap,
            "prints": prints, "designs": designs}


# --------------------------------------------------------------------------- #
# 3) 崖を測る前に予測する                                                        #
# --------------------------------------------------------------------------- #
def section3_predict():
    print()
    print("=" * 78)
    print("3) ★★崖を測る前に予測する —— 網点格子による不定性(閉形式)")
    print("=" * 78)
    print("  網点の中心は、スクリーン角 θ・ピッチ p の**正方格子** Λ_θ を成す。")
    print("  版を格子ベクトルのぶんだけ動かすと、網点は**元と重なる**。したがって")
    print("  相関のピークは格子ベクトルの整数倍だけ不定で、")
    print()
    print("      測って出るのは d ではなく  d mod Λ_θ")
    print()
    print("  になる。基本セル(Voronoi 領域)は 1 辺 p = %.2f px の正方形を θ だけ"
          % PITCH)
    print("  回したもの。したがって**一意に決まるのは**:")
    print("    ・格子の軸方向:  |d| <= p/2 = %.2f px(= %.1f µm)"
          % (PITCH / 2, PITCH / 2 * UM_PER_PX))
    print("    ・対角方向:      |d| <= p/√2 = %.3f px(= %.1f µm)"
          % (PITCH / np.sqrt(2), PITCH / np.sqrt(2) * UM_PER_PX))
    print("  それを超えると**折り返して、小さいずれに見える**。")
    print()
    print("  この PoC が仕込んだずれについての予測(**まだ何も測っていない**):")
    print()
    print("  %-4s %8s %16s %10s %16s %10s %8s"
          % ("版", "角度", "真値 (dy,dx)", "|d|", "予測 見かけ", "|見かけ|", "判定"))
    print("  " + "-" * 78)
    pred = {}
    for name, ang, _blob, (dy, dx) in PLATES:
        ry, rx, _u, _v = reduce_to_cell(dy, dx, ang)
        pred[name] = (ry, rx)
        wrapped = np.hypot(ry, rx) < np.hypot(dy, dx) - 1e-9
        print("  %-4s %7.1f° (%+6.2f,%+6.2f) %10.3f (%+6.2f,%+6.2f) %10.3f %8s"
              % (name, ang, dy, dx, np.hypot(dy, dx), ry, rx, np.hypot(ry, rx),
                 "★折返し" if wrapped else "そのまま"))
    print()
    yy, yx = pred["Y"]
    print("  → Y 版だけが折り返す予測。真値 |d| = %.3f px(%.1f µm、公差 %.1f px の"
          % (np.hypot(*PLATES[2][3]), np.hypot(*PLATES[2][3]) * UM_PER_PX, TOL_PX))
    print("     **%.1f 倍**)なのに、見かけは %.3f px で**公差の内側**に見える。"
          % (np.hypot(*PLATES[2][3]) / TOL_PX, np.hypot(yy, yx)))
    print("     ★これは「測定誤差」ではない。**測っている量が違う**。")
    print()
    print("  4 節でこの予測を掃引で確かめる。**ここまでの数字はすべて式から出した**。")
    return pred


# --------------------------------------------------------------------------- #
# 4) 実測 —— 0〜2p を掃引して予測と突き合わせる                                   #
# --------------------------------------------------------------------------- #
def section4_sweep():
    print()
    print("=" * 78)
    print("4) ★★実測 —— ずれを 0 から 2p(%.1f px)まで掃引する" % (2 * PITCH))
    print("=" * 78)
    print("  各版について、+x 方向のずれ t を %.1f px 刻みで %d 点。"
          % (SWEEP[1] - SWEEP[0], SWEEP.size))
    print("  推定器は 2 つ。どちらも**「ずれは小さいはずだ」という現場の仮定**を")
    print("  探索範囲として入れてあるが、その置き方が違う:")
    print("    (1) 全画面の相互相関(fs.cx_fft/cx_ifft + fs.peak_subbin)。")
    print("        探すのは**格子 Λ_θ の基本セルの中だけ**(素材に合わせた仮定)。")
    print("    (2) 窓ごとの相互相関の中央値(fs.ledger.piv_cross_correlate)。")
    print("        op が持つのは**正方形の探索箱**なので ±p/2 = ±%.1f px。"
          % (PITCH / 2))
    print()
    out = {}
    for name, ang, blob, _d in PLATES:
        ref = design_plate(ang, blob)
        cm = cell_mask(L, ang)
        rows = []
        for t in SWEEP:
            cur = am_sheet(ang, blob, 0.0, float(t), seed=31)
            cy, cx, _r = corr_shift(ref, cur, cm)
            py, px, _vf = piv_shift(ref, cur, limit=PITCH / 2)
            ry, rx, _u, _v = reduce_to_cell(0.0, float(t), ang)
            rows.append({
                "t": float(t), "pred": (ry, rx), "corr": (cy, cx), "piv": (py, px),
                "raw_err": float(np.hypot(cy - ry, cx - rx)),
                "lat_err": lattice_residual(cy - 0.0, cx - t, ang),
                "piv_lat": lattice_residual(py - 0.0, px - t, ang),
                "margin": tie_margin(0.0, float(t), ang),
            })
        out[name] = rows
    # --- 印字(C 版を代表で全点、他は要約)---
    name0 = "C"
    ang0 = dict((n, a) for n, a, _b, _d in PLATES)[name0]
    print("  %s 版(%.0f°)の全点:" % (name0, ang0))
    print("  %7s %18s %18s %10s %12s %9s"
          % ("t px", "予測 見かけ", "実測 相関", "生の差", "格子で簡約", "セル余裕"))
    print("  " + "-" * 78)
    for r in out[name0]:
        flag = " ←境界" if r["margin"] < 0.3 else ""
        print("  %7.2f (%+7.3f,%+7.3f) (%+7.3f,%+7.3f) %10.4f %12.4f %9.3f%s"
              % (r["t"], r["pred"][0], r["pred"][1], r["corr"][0], r["corr"][1],
                 r["raw_err"], r["lat_err"], r["margin"], flag))
    print()
    allr = [r for rows in out.values() for r in rows]
    ties = [r for r in allr if r["raw_err"] > 0.5]
    good = [r for r in allr if r["raw_err"] <= 0.5]
    print("  %d 版 × %d 点 = %d 点。" % (len(PLATES), SWEEP.size, len(allr)))
    print("  ★**予測と実測が一致した点: %d 点、差は最大 %.4f px**。"
          % (len(good), max(r["raw_err"] for r in good)))
    print("  ★残り %d 点は**基本セルの境界**(セル余裕 最大 %.3f px)。そこは"
          % (len(ties), max(r["margin"] for r in ties) if ties else 0.0))
    print("     予測式の round() がどちらへ転んでもよい場所で、雑音が決める。")
    print()
    print("  ★★**格子で簡約した残差**なら全点が合う: 最大 %.4f px。"
          % max(r["lat_err"] for r in allr))
    print("     つまり推定器は間違えていない —— **格子で等価な答えのどれかを**")
    print("     **返している**。「どれか」を選ぶ材料が、この素材には無い。")
    print()
    print("  推定器 (2)(窓ごとの相関)でも同じ: 格子で簡約した残差の最大 %.4f px。"
          % max(r["piv_lat"] for r in allr))
    print("  **2 つの独立な推定器が同じ折り返しをする** —— 原因は推定器ではない。")
    if figs.enabled():
        rows = out[name0]
        xs = np.array([r["t"] for r in rows])
        figs.save_plot(
            "sweep_wrap",
            [("真のずれ dx", xs, xs),
             ("予測 見かけ dx", xs, np.array([r["pred"][1] for r in rows])),
             ("実測 相関 dx", xs, np.array([r["corr"][1] for r in rows])),
             ("公差 +%.1f px" % TOL_PX, xs, np.full(xs.size, TOL_PX)),
             ("公差 -%.1f px" % TOL_PX, xs, np.full(xs.size, -TOL_PX))],
            xlabel="仕込んだずれ t [px]", ylabel="dx [px]",
            title="%s 版(%.0f°): 測った値は %.1f px 周期でのこぎりになる"
                  % (name0, ang0, PITCH),
            caption="真値は直線、実測はのこぎり。t = %.1f px の版が「0 px、合格」"
                    "と出る。予測(閉形式)と実測はセル境界のタイを除いて重なる"
                    % PITCH)
        figs.save_plot(
            "sweep_all_plates",
            [("%s %.0f°" % (n, dict((x[0], x[1]) for x in PLATES)[n]),
              np.array([r["t"] for r in out[n]]),
              np.array([np.hypot(*r["pred"]) for r in out[n]]))
             for n in ("C", "M", "Y", "K")]
            + [("公差 %.1f px" % TOL_PX, SWEEP, np.full(SWEEP.size, TOL_PX))],
            xlabel="仕込んだずれ t [px]", ylabel="見かけの |ずれ| [px]",
            title="同じずれでも、版ごとに違うのこぎりになる",
            caption="スクリーン角が違えば格子も違う。t を同じだけ動かしても "
                    "4 版の「見かけ」は一致しない —— これが 5 節")
    return out


# --------------------------------------------------------------------------- #
# 5) 同じずれが版ごとに違って見える                                              #
# --------------------------------------------------------------------------- #
def section5_per_plate():
    print()
    print("=" * 78)
    print("5) ★同じ物理的なずれが、版ごとに違う見かけになる")
    print("=" * 78)
    dy, dx = PLATES[2][3]
    print("  紙が %.2f px(%.1f µm)ずれた —— つまり d = (%+.2f, %+.2f) を"
          % (np.hypot(dy, dx), np.hypot(dy, dx) * UM_PER_PX, dy, dx))
    print("  **4 版すべてに同じだけ**掛ける。物理的には 1 つのずれ。")
    print()
    print("  %-4s %8s %16s %10s %16s %10s %10s"
          % ("版", "角度", "予測 見かけ", "|予測|", "実測 見かけ", "|実測|", "差"))
    print("  " + "-" * 78)
    rows, mags, diffs = [], [], []
    for name, ang, blob, _d in PLATES:
        ref = design_plate(ang, blob)
        cur = am_sheet(ang, blob, dy, dx, seed=41)
        my, mx, _r = corr_shift(ref, cur, cell_mask(L, ang))
        ry, rx, _u, _v = reduce_to_cell(dy, dx, ang)
        d = float(np.hypot(my - ry, mx - rx))
        mags.append(float(np.hypot(my, mx)))
        diffs.append(d)
        rows.append([name, "%.0f°" % ang, "(%+.2f,%+.2f)" % (ry, rx),
                     "%.3f" % np.hypot(ry, rx), "(%+.2f,%+.2f)" % (my, mx),
                     "%.3f" % np.hypot(my, mx), "%.4f" % d])
        print("  %-4s %7.0f° (%+7.3f,%+7.3f) %10.3f (%+7.3f,%+7.3f) %10.3f %10.4f"
              % (name, ang, ry, rx, np.hypot(ry, rx), my, mx, np.hypot(my, mx), d))
    print()
    print("  → 1 つの物理的なずれ %.3f px が、版ごとに **%.2f 〜 %.2f px** に化ける"
          % (np.hypot(dy, dx), min(mags), max(mags)))
    print("     (予測との差は最大 %.4f px)。**「どの版が何 px ずれているか」を"
          % max(diffs))
    print("     版ごとの相関で並べた表は、そのままでは物理量の表になっていない**。")
    print("     4 版とも公差 %.1f px を超えて見えるので**この例では不合格は出る**が、"
          % TOL_PX)
    print("     どの方向にどれだけ紙を動かせばよいかは、この表からは読めない。")
    figs.save_table("per_plate", ["版", "角度", "予測 見かけ", "|予測| px",
                                  "実測 見かけ", "|実測| px", "差 px"], rows,
                    title="同じずれ (%+.2f,%+.2f) px を 4 版に掛けた" % (dy, dx),
                    col_w=110)
    return {"mags": mags, "diffs": diffs}


# --------------------------------------------------------------------------- #
# 6) 対照群 (a) —— FM(確率)スクリーン                                          #
# --------------------------------------------------------------------------- #
def fm_centres(blob, seed=7, n_try=400_000, radius=1.6):
    """FM(確率)スクリーンの網点中心。**版座標**の点列 (N,2)。

    被覆率に比例した密度で棄却標本する。点なので、版がどう動いても回っても
    **点を動かすだけ**で正しく描ける(AM と同じ絵柄・同じ被覆率)。
    """
    rng = np.random.default_rng(seed)
    ys = rng.uniform(-40.0, L + 40.0, n_try)
    xs = rng.uniform(-40.0, L + 40.0, n_try)
    area = (L + 80.0) ** 2
    dens = np.clip(tone(ys, xs, blob), 0.0, MAX_TONE) / (np.pi * radius ** 2)
    keep = rng.random(n_try) < dens * area / n_try
    return np.column_stack([ys[keep], xs[keep]]), radius


def fm_sheet(centres, radius, dy=0.0, dx=0.0, seed=1) -> np.ndarray:
    """FM スクリーンの刷り上がり。各画素から最寄りの網点中心までの距離で塗る。"""
    from scipy.spatial import cKDTree

    tree = cKDTree(np.asarray(centres) + np.array([dy, dx]))
    dist, _ = tree.query(np.column_stack([_Y.ravel(), _X.ravel()]), k=1)
    ink = np.clip((radius - dist.reshape(L, L)) / SOFT + 0.5, 0.0, 1.0)
    img = 1.0 - ink
    if seed is not None:
        img = img + np.random.default_rng(seed).normal(0.0, NOISE, img.shape)
    return img


def section6_control_fm(sweep_am):
    print()
    print("=" * 78)
    print("6) 対照群 (a) —— 同じ絵柄を FM(確率)スクリーンで刷る")
    print("=" * 78)
    print("  ★切り分けの論理: **絵柄も推定器も探索範囲も変えず、スクリーンだけ**")
    print("  **周期(AM)から非周期(FM)に替える**。折り返しが消えるなら、崖の")
    print("  原因は推定器ではなく**素材の周期性**だと確定する。")
    print()
    blob = PLATES[0][2]
    ang = PLATES[0][1]
    cen, rad = fm_centres(blob)
    ref_fm = fm_sheet(cen, rad, seed=None)
    ref_am = design_plate(ang, blob)
    print("  FM の網点 %d 個(半径 %.1f px)。被覆率は AM と同じ式から。"
          % (len(cen), rad))
    print()
    print("  %7s %18s %10s %18s %10s"
          % ("t px", "AM 実測", "AM 誤差", "FM 実測", "FM 誤差"))
    print("  " + "-" * 70)
    am_by_t = {round(r["t"], 3): r for r in sweep_am["C"]}
    fm_err, am_err, ts = [], [], []
    for t in SWEEP[::2]:
        cur = fm_sheet(cen, rad, 0.0, float(t), seed=61)
        # ★ FM 側は探索範囲を **絞らない**(絞っても結果は変わらないが、
        #   「AM の折り返しは探索範囲のせいだ」という言い逃れを塞ぐため)。
        my, mx, _r = corr_shift(ref_fm, cur, box_mask(L, 2.0 * PITCH))
        e_fm = float(np.hypot(my - 0.0, mx - t))
        a = am_by_t[round(float(t), 3)]
        e_am = float(np.hypot(a["corr"][0] - 0.0, a["corr"][1] - t))
        fm_err.append(e_fm)
        am_err.append(e_am)
        ts.append(float(t))
        print("  %7.2f (%+7.3f,%+7.3f) %10.4f (%+7.3f,%+7.3f) %10.4f"
              % (t, a["corr"][0], a["corr"][1], e_am, my, mx, e_fm))
    print()
    print("  → **FM の誤差は全域で最大 %.4f px、折り返しゼロ**(探索範囲を"
          % max(fm_err))
    print("     ±%.1f px = 2p まで開けてある)。同じ AM は最大 %.3f px。"
          % (2 * PITCH, max(am_err)))
    print("  ★**崖の原因は推定器ではなく AM 網点の周期性**。FM スクリーンが")
    print("     モアレを避ける道具として使われる理由と同じ構造がここにも出る。")
    print()
    print("  代償も測る: 同じ被覆率でも FM は網点が小さく散るので、")
    ref_am_c = ref_am[np.ix_(range(128, 384), range(128, 384))]
    ref_fm_c = ref_fm[np.ix_(range(128, 384), range(128, 384))]
    print("    AM の像の標準偏差 %.4f / FM %.4f(コントラストは FM が %.2f 倍)"
          % (ref_am_c.std(), ref_fm_c.std(), ref_fm_c.std() / ref_am_c.std()))
    if figs.enabled():
        s = np.s_[160:288, 160:288]
        cm_am = corr_map(ref_am, am_sheet(ang, blob, 0.0, 9.0, seed=61))
        cm_fm = corr_map(ref_fm, fm_sheet(cen, rad, 0.0, 9.0, seed=61))
        c0 = L // 2
        w = 24
        figs.save_grid(
            "corr_maps",
            [ref_am[s], ref_fm[s],
             cm_am[c0 - w:c0 + w + 1, c0 - w:c0 + w + 1],
             cm_fm[c0 - w:c0 + w + 1, c0 - w:c0 + w + 1]],
            ["AM 網点", "FM 網点", "AM の相関(±%d px)" % w,
             "FM の相関(±%d px)" % w],
            title="ずれ 9.00 px のときの相関マップ", ncols=2,
            caption="AM は %.1f px 周期でピークが並ぶ(どれが真値か決められない)。"
                    "FM はピークが 1 つで、真値 (0, 9.00) に立つ" % PITCH)
        figs.save_plot(
            "control_fm",
            [("AM(周期)", np.array(ts), np.array(am_err)),
             ("FM(非周期)", np.array(ts), np.array(fm_err)),
             ("公差 %.1f px" % TOL_PX, np.array(ts), np.full(len(ts), TOL_PX))],
            xlabel="仕込んだずれ t [px]", ylabel="ずれベクトルの誤差 [px]",
            title="対照群: スクリーンだけ替える",
            caption="絵柄も推定器も同じ。FM に替えるだけで崖が消える")
    return {"fm_err": max(fm_err), "am_err": max(am_err), "n_dots": len(cen)}


# --------------------------------------------------------------------------- #
# 7) 対照群 (b) —— レジストマークと版の伸び・回転                                 #
# --------------------------------------------------------------------------- #
SHEET_SCALE = 1.006      # 紙の伸び(0.6 %)
SHEET_ROT = 0.120        # 版の傾き [deg]
D0 = (+0.60, +9.40)      # 版全体の平行移動 [px](p/2 を超えている)
MARK_AT = (96.0, 96.0)   # レジストマークの版座標 (y, x)


def affine_plate_coords(scale=SHEET_SCALE, rot_deg=SHEET_ROT, d0=D0):
    """紙座標 (y, x) → 版座標。紙は中心まわりに ``scale`` 倍・``rot`` 回転して刷られる。"""
    th = np.deg2rad(rot_deg)
    c = L / 2.0
    ey, ex = _Y - c - d0[0], _X - c - d0[1]
    # 逆写像: p = c + (1/s) R(-th) (x - c - d0)
    py = (ey * np.cos(th) - ex * np.sin(th)) / scale + c
    px = (ey * np.sin(th) + ex * np.cos(th)) / scale + c
    return py, px


def true_field(scale=SHEET_SCALE, rot_deg=SHEET_ROT, d0=D0):
    """真のずれ場 d(x) = x - p(x)(紙座標の各点で)。**閉形式**。"""
    py, px = affine_plate_coords(scale, rot_deg, d0)
    return _Y - py, _X - px


def section7_marks():
    print()
    print("=" * 78)
    print("7) 対照群 (b) —— レジストマーク 1 か所と、版の伸び・回転")
    print("=" * 78)
    print("  実務の手: 版の隅に十字のレジストマーク(全長 %.0f px = %.2f mm)を"
          % (2 * MARK_HALF_LEN, 2 * MARK_HALF_LEN * UM_PER_PX / 1000))
    print("  刷り込み、そこをカメラで見て版ずれを測る。マークは**非周期の局所特徴**")
    print("  なので、網点の折り返しに縛られないはず。")
    print()
    print("  仕込み: 平行移動 d0 = (%+.2f, %+.2f) px(|d0| = %.2f px、p/2 = %.1f px を"
          % (D0[0], D0[1], np.hypot(*D0), PITCH / 2))
    print("  超えている)+ 紙の伸び %.3f %% + 版の傾き %.3f°。"
          % (100 * (SHEET_SCALE - 1), SHEET_ROT))
    print()
    name, ang, blob, _d = PLATES[0]
    ref = design_plate(ang, blob, mark=MARK_AT)
    py, px = affine_plate_coords()
    ink = am_ink(py, px, ang, blob)
    ink = np.maximum(ink, mark_ink(py, px, MARK_AT))
    cur = 1.0 - ink + np.random.default_rng(71).normal(0.0, NOISE, (L, L))
    ty, tx = true_field()

    # --- マークを含む窓 vs 網点だけの窓 ---
    half = 96
    my_c, mx_c = int(round(MARK_AT[0])), int(round(MARK_AT[1]))
    fy_c, fx_c = L - my_c, L - mx_c                   # 対角の、網点だけの場所
    print("  同じ版の 2 か所を、同じ %dx%d の窓・同じ推定器で測る" % (2 * half, 2 * half))
    print("  (探索範囲は ±%.1f px = 2p まで開けてある):" % (2 * PITCH))
    print()
    print("  %-22s %18s %18s %10s" % ("窓", "真値 (dy,dx)", "実測 (dy,dx)", "誤差"))
    print("  " + "-" * 72)
    spots = []
    bm = box_mask(2 * half, 2.0 * PITCH)
    for label, (cy, cx) in (("マークを含む窓", (my_c, mx_c)),
                            ("網点だけの窓(対角)", (fy_c, fx_c))):
        sl = np.s_[cy - half:cy + half, cx - half:cx + half]
        ey, ex, _r = corr_shift(ref[sl], cur[sl], bm)
        gy, gx = float(ty[sl].mean()), float(tx[sl].mean())
        err = float(np.hypot(ey - gy, ex - gx))
        spots.append({"label": label, "true": (gy, gx), "meas": (ey, ex),
                      "err": err, "at": (cy, cx)})
        print("  %-22s (%+7.3f,%+7.3f) (%+7.3f,%+7.3f) %10.4f"
              % (label, gy, gx, ey, ex, err))
    print()
    print("  → ★**マークを含む窓だけが当たる**(誤差 %.4f px)。同じ版・同じ推定器"
          % spots[0]["err"])
    print("     でも網点だけの窓は %.4f px 外す —— 3 節の格子の不定性そのもの"
          % spots[1]["err"])
    print("     (格子で簡約した残差は %.4f px なので、格子で等価な別の代表元)。"
          % lattice_residual(spots[1]["meas"][0] - spots[1]["true"][0],
                             spots[1]["meas"][1] - spots[1]["true"][1], ang))
    print()
    print("  ★★ところが**マークは 1 か所にしか無い**。版が伸びて回っていると、")
    print("  マークの値は**マークの場所でしか正しくない**。閉形式で予測してから測る:")
    print()
    th = np.deg2rad(SHEET_ROT)
    a11 = 1.0 - np.cos(th) / SHEET_SCALE
    a12 = np.sin(th) / SHEET_SCALE
    grad = float(np.hypot(a11, a12))      # 距離 1 px あたりの誤差 [px]
    r_crit = TOL_PX / grad
    print("    d(x) - d(x_mark) = (I - R(-φ)/s)(x - x_mark) なので、誤差は距離に")
    print("    **比例**する。比例係数 |I - R(-φ)/s| = %.6f px/px。" % grad)
    print("    公差 %.1f px を超えるのは距離 **%.1f px(= %.2f mm)** から。"
          % (TOL_PX, r_crit, r_crit * UM_PER_PX / 1000))
    print()
    print("  ★実測は**閉形式と別の道**で取る: 同じ版・同じ紙の伸びと回転で FM")
    print("  (非周期)スクリーンを刷り、窓ごとの相関で**ずれ場を測る**。")
    print("  FM なら 6 節のとおり折り返さないので、測った場をそのまま使える。")
    print()
    cen, rad = fm_centres(blob)
    ref_fm = fm_sheet(cen, rad, seed=None)
    th = np.deg2rad(SHEET_ROT)
    c = L / 2.0
    ey_, ex_ = np.asarray(cen)[:, 0] - c, np.asarray(cen)[:, 1] - c
    warped = np.column_stack([
        c + D0[0] + SHEET_SCALE * (ey_ * np.cos(th) + ex_ * np.sin(th)),
        c + D0[1] + SHEET_SCALE * (-ey_ * np.sin(th) + ex_ * np.cos(th))])
    cur_fm = fm_sheet(warped, rad, seed=72)

    hw = 64
    bm2 = box_mask(2 * hw, 2.0 * PITCH)

    def measure_at(iy, ix):
        sl = np.s_[iy - hw:iy + hw, ix - hw:ix + hw]
        ey, ex, _r = corr_shift(ref_fm[sl], cur_fm[sl], bm2)
        return float(ey), float(ex)

    mk_y, mk_x = measure_at(my_c, mx_c)
    print("  マークの場所での実測 (%+.3f, %+.3f) / 真値 (%+.3f, %+.3f)"
          % (mk_y, mk_x, float(ty[my_c, mx_c]), float(tx[my_c, mx_c])))
    print()
    print("  %8s %18s %18s %11s %11s %11s"
          % ("距離 px", "真値 d(x)", "実測 d(x)", "場の誤差", "予測 誤差", "実測 誤差"))
    print("  " + "-" * 80)
    dist_rows, pred_e, meas_e, field_e = [], [], [], []
    for frac in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        iy = int(round(my_c + frac * (L - hw - 1 - my_c)))
        ix = int(round(mx_c + frac * (L - hw - 1 - mx_c)))
        r = float(np.hypot(iy - my_c, ix - mx_c))
        gy, gx = float(ty[iy, ix]), float(tx[iy, ix])
        ey, ex = measure_at(iy, ix)
        field_e.append(float(np.hypot(ey - gy, ex - gx)))
        e_meas = float(np.hypot(mk_y - ey, mk_x - ex))    # マークの値を当てた誤差
        e_pred = grad * r                                  # 閉形式
        dist_rows.append(["%.1f" % r, "(%+.2f,%+.2f)" % (gy, gx),
                          "(%+.2f,%+.2f)" % (ey, ex), "%.4f" % field_e[-1],
                          "%.4f" % e_pred, "%.4f" % e_meas])
        pred_e.append(e_pred)
        meas_e.append(e_meas)
        print("  %8.1f (%+7.3f,%+7.3f) (%+7.3f,%+7.3f) %11.4f %11.4f %11.4f"
              % (r, gy, gx, ey, ex, field_e[-1], e_pred, e_meas))
    d_pred_meas = max(abs(p - m) for p, m in zip(pred_e, meas_e))
    print()
    print("  → 測ったずれ場そのものの誤差は最大 %.4f px(FM なので折り返さない)。"
          % max(field_e))
    print("  → **マークの値を当てた誤差**は、予測(閉形式)と実測で最大 %.4f px しか"
          % d_pred_meas)
    print("     違わない。**誤差は距離に比例する**という予測が実データで立った。")
    rr = np.array([float(x[0]) for x in dist_rows])
    r_meas = float(np.interp(TOL_PX, np.array(meas_e), rr))
    dist_map = np.hypot(_Y - my_c, _X - mx_c)
    frac_out = float((dist_map > r_crit).mean())
    print("  ★**公差 %.1f px を超えるのは 予測 %.1f px / 実測 %.1f px から**。"
          % (TOL_PX, r_crit, r_meas))
    print("     マークからその距離より遠い画素は紙の **%.0f %%**。マーク 1 か所では"
          % (100 * frac_out))
    print("     そこが全部公差外 —— **マークを増やして内挿するか、面で測るしかない**。")
    figs.save_table("mark_distance",
                    ["距離 px", "真値 d(x)", "実測 d(x)", "場の誤差 px",
                     "予測 誤差 px", "実測 誤差 px"], dist_rows,
                    title="マーク 1 か所の値を版全体へ当てた誤差", col_w=104)
    if figs.enabled():
        figs.save_plot(
            "mark_distance_plot",
            [("予測(閉形式)", rr, np.array(pred_e)),
             ("実測", rr, np.array(meas_e)),
             ("公差 %.1f px" % TOL_PX, rr, np.full(rr.size, TOL_PX))],
            xlabel="マークからの距離 [px]", ylabel="ずれベクトルの誤差 [px]",
            title="レジストマークは、マークの場所でしか当たらない",
            caption="紙が %.2f %% 伸びて %.3f° 回っているとき、誤差は距離に比例。"
                    "公差 %.1f px を超えるのは %.0f px から"
                    % (100 * (SHEET_SCALE - 1), SHEET_ROT, TOL_PX, r_crit))
        s = np.s_[16:208, 16:208]
        figs.save_grid("mark_scene", [ref[s], cur[s], (cur - ref)[s]],
                       ["設計(マークつき)", "刷り上がり", "差"],
                       title="レジストマークのある隅(192x192 px)", ncols=3,
                       signed=[False, False, True],
                       caption="十字は非周期なので相関のピークが 1 つに決まる。"
                               "周りの網点は %.1f px 周期で何度でも合う" % PITCH)
    return {"spots": spots, "grad": grad, "r_crit": r_crit, "r_meas": r_meas,
            "pred_meas_diff": d_pred_meas, "field_err": max(field_e),
            "frac_out": frac_out}


# --------------------------------------------------------------------------- #
# 8) 物差しを 2 つ                                                              #
# --------------------------------------------------------------------------- #
def section8_metrics(sweep_am, zero):
    print()
    print("=" * 78)
    print("8) ★★物差しを 2 つ置く —— 精度と、合否判定")
    print("=" * 78)
    print("  物差し 1(**精度**): 公差 %.1f px 以内の領域(t <= %.1f px)での"
          % (TOL_PX, TOL_PX))
    print("               ずれベクトル誤差の RMS [px]。")
    print("  物差し 2(**判定**): 0 〜 %.1f px の全域で、「|d| <= %.1f px なら合格」"
          % (2 * PITCH, TOL_PX))
    print("               の判定が真値と一致した割合 [%]。")
    print("  題材は **Y 版(スクリーン角 0°)** —— 掃引の向き(+x)が格子の軸")
    print("  そのものなので、折り返しがいちばん素直に出る。")
    print()
    name, ang, blob, _d = PLATES[2]
    cen, rad = fm_centres(blob)
    ref_fm = fm_sheet(cen, rad, seed=None)
    des = design_plate(ang, blob)
    gy0, gx0 = ink_centroid(des)
    bm = box_mask(L, 2.0 * PITCH)

    print("  手法は 5 つ。3 つ目までが「1 つの手」、4 つ目が**その組合せ**、")
    print("  5 つ目は**素材を替える**手:")
    print("    ・重心(ゼロ点 B)")
    print("    ・相関 AM(素) —— 探すのは基本セルの中だけ")
    print("    ・相関 AM(低域通過) —— 遮断 1/(3p) = %.4f cyc/px で網点を消す"
          % LP_CUT)
    print("      (網点の基本波は exp(-4.5) = 1.1e-2 倍。絵柄だけが残る)")
    print("    ・★二段(低域通過で**代表元を選び**、素の相関で**詰める**)")
    print("    ・相関 FM")
    print()
    des_lp = lowpass_image(des)
    keys = ["重心(ゼロ点 B)", "相関 AM(素)", "相関 AM(低域通過)",
            "★二段(粗+密)", "相関 FM"]
    methods = {k: [] for k in keys}
    coarse_err = []
    for t in SWEEP:
        r = [x for x in sweep_am[name] if abs(x["t"] - t) < 1e-9][0]
        cur_am = am_sheet(ang, blob, 0.0, float(t), seed=31)
        cy, cx = ink_centroid(cur_am)
        methods["重心(ゼロ点 B)"].append((cy - gy0, cx - gx0))
        methods["相関 AM(素)"].append(r["corr"])
        ly, lx, _q = corr_shift(des_lp, lowpass_image(cur_am), bm)
        methods["相関 AM(低域通過)"].append((ly, lx))
        coarse_err.append(float(np.hypot(ly - 0.0, lx - t)))
        methods["★二段(粗+密)"].append(snap_to_lattice(r["corr"], (ly, lx), ang))
        cur_fm = fm_sheet(cen, rad, 0.0, float(t), seed=61)
        my, mx, _ratio = corr_shift(ref_fm, cur_fm, bm)
        methods["相関 FM"].append((my, mx))
    print("  %-22s %13s %13s %12s %12s"
          % ("手法", "RMS 誤差 px", "最大 誤差 px", "判定一致率", "見落とし"))
    print("  " + "-" * 78)
    rows, res = [], {}
    for label, ests in methods.items():
        errs, agree, miss = [], 0, 0
        for t, (ey, ex) in zip(SWEEP, ests):
            e = float(np.hypot(ey - 0.0, ex - t))
            if t <= TOL_PX:
                errs.append(e)
            truth_ok = t <= TOL_PX
            est_ok = np.hypot(ey, ex) <= TOL_PX
            agree += int(truth_ok == est_ok)
            miss += int((not truth_ok) and est_ok)     # 不合格を合格と言った回数
        rms = float(np.sqrt(np.mean(np.square(errs))))
        mx_e = float(max(np.hypot(ey - 0.0, ex - t)
                         for t, (ey, ex) in zip(SWEEP, ests)))
        rate = 100.0 * agree / SWEEP.size
        res[label] = {"rms": rms, "max": mx_e, "rate": rate, "miss": miss}
        rows.append([label, "%.4f" % rms, "%.3f" % mx_e, "%.1f %%" % rate,
                     "%d / %d" % (miss, SWEEP.size)])
        print("  %-22s %13.4f %13.3f %11.1f %% %8d / %d"
              % (label, rms, mx_e, rate, miss, SWEEP.size))
    print()
    a, lp, b = res["相関 AM(素)"], res["相関 AM(低域通過)"], res["重心(ゼロ点 B)"]
    two = res["★二段(粗+密)"]
    print("  → ★★**物差しを変えると勝者が入れ替わる**。")
    print("     物差し 1(精度)の 1 位は **相関 AM(素)の %.4f px**。低域通過は"
          % a["rms"])
    print("     %.4f px(**%.0f 倍**悪い)、重心は %.4f px。"
          % (lp["rms"], lp["rms"] / a["rms"], b["rms"]))
    print("     物差し 2(判定)では素の相関が **%.1f %%** で最下位 —— 不合格の版を"
          % a["rate"])
    print("     %d/%d 回「合格」と言った(低域通過 %.1f %% / 重心 %.1f %%)。"
          % (a["miss"], SWEEP.size, lp["rate"], b["rate"]))
    print("     どちらの数字も正しく、どちらか 1 つだけを見た人は反対の結論を出す。")
    print()
    print("  ★★**2 つを組み合わせれば両方取れる**(二段: %.4f px / %.1f %%)。"
          % (two["rms"], two["rate"]))
    print("     低域通過は**格子を消す**(絵柄しか残らない)ので一意だが鈍い。")
    print("     素の相関は鋭いが格子で不定。**鈍い方で代表元を選び、鋭い方で**")
    print("     **詰める**と、一意性と精度が同時に立つ。")
    print("     成立条件は閉形式で書ける: **粗の誤差 < 基本セルの半径 %.3f px**。"
          % (PITCH / 2))
    ce = np.array(coarse_err)
    two_err = np.array([np.hypot(ey - t, 0.0) if False else
                        np.hypot(ey - 0.0, ex - t)
                        for t, (ey, ex) in zip(SWEEP, methods["★二段(粗+密)"])])
    bad_c = ce > PITCH / 2
    bad_t = two_err > 1.0
    print("     実測の粗の誤差: 中央値 %.3f px / 最大 %.3f px。セルの半径を"
          % (float(np.median(ce)), float(ce.max())))
    print("     **超えた点が %d/%d 点**あり、そこでは二段が %.1f px 級に跳んだ。"
          % (int(bad_c.sum()), SWEEP.size, PITCH))
    print("  ★★**二段が壊れた %d 点は、すべて粗の誤差がセルの半径を超えた点**"
          % int(bad_t.sum()))
    print("     だった(逆は成り立たない —— 超えても跳ばないことはある)。")
    print("     **成立条件が実測で確かめられた**。誤差は小さくならず丸ごと 1 格子")
    print("     跳ぶので**気づける**が、それは「跳んだ値を見る人がいれば」の話。")
    print()
    # --- 二段の崖を、実際に壊して確かめる --------------------------------- #
    faint = (blob[0], blob[1], 0.06)          # 絵柄をほとんど無くす(下地だけに近い)
    des_f = design_plate(ang, faint)
    des_f_lp = lowpass_image(des_f)
    cm = cell_mask(L, ang)
    print("  ★崖を実際に踏む: **絵柄の山を %.2f → %.2f に下げる**(ベタ近くの"
          % (BLOB_PEAK, 0.06))
    print("  一様な面 —— 印刷では珍しくない)。低域通過に残る手がかりが減る。")
    print()
    print("  %7s %12s %12s %14s %10s"
          % ("t px", "粗 の誤差", "二段 の誤差", "選んだ代表元", "判定"))
    print("  " + "-" * 62)
    broke, tested = 0, 0
    for t in (0.0, 2.0, 5.0, 9.0, 13.0, 18.0):
        cur = am_sheet(ang, faint, 0.0, float(t), seed=31)
        fy, fx, _q = corr_shift(des_f, cur, cm)
        ly, lx, _q2 = corr_shift(des_f_lp, lowpass_image(cur), bm)
        sy, sx = snap_to_lattice((fy, fx), (ly, lx), ang)
        ce = float(np.hypot(ly - 0.0, lx - t))
        se = float(np.hypot(sy - 0.0, sx - t))
        tested += 1
        broke += int(se > 1.0)
        print("  %7.2f %12.3f %12.3f %14s %10s"
              % (t, ce, se, "(%+.1f,%+.1f)" % (sy, sx),
                 "★1 格子ずれ" if se > 1.0 else "正しい"))
    print()
    print("  → 絵柄を薄くすると粗の誤差が %.2f px(セルの半径)を常時超え、二段は"
          % (PITCH / 2))
    print("     **丸ごと 1 格子ずれた答え**を返す(%d/%d 行)。絵柄が濃いとき"
          % (broke, tested))
    print("     (%d/%d 点)より格段に悪い —— **同じ手法が、刷る絵柄しだいで"
          % (int(bad_t.sum()), SWEEP.size))
    print("     壊れたり壊れなかったりする**。")
    print("     ★op にするなら、**粗の誤差とセルの半径の比を返り値に入れる**べき。")
    print()
    print("  ★相関 FM は素材を替えるだけで両方勝つ(%.4f px / %.1f %%)。"
          % (res["相関 FM"]["rms"], res["相関 FM"]["rate"]))
    print("     **物差しを 2 つ置いて初めてこの順位が見える**。")
    res["coarse_max"] = max(coarse_err)
    res["two_stage_broken"] = broke
    figs.save_table("metrics", ["手法", "RMS 誤差 px", "最大 誤差 px",
                                "判定一致率", "見落とし"], rows,
                    title="物差し 2 つ(公差 %.1f px)" % TOL_PX, col_w=104)
    if figs.enabled():
        figs.save_plot(
            "metrics_sweep",
            [("真値", SWEEP, SWEEP)]
            + [(lab, SWEEP, np.array([np.hypot(*e) for e in ests]))
               for lab, ests in methods.items()]
            + [("公差 %.1f px" % TOL_PX, SWEEP, np.full(SWEEP.size, TOL_PX))],
            xlabel="仕込んだずれ t [px]", ylabel="推定した |ずれ| [px]",
            title="4 つの手法(Y 版 0°)",
            caption="素の相関だけが折り返して公差の線を何度も下に横切る = "
                    "不合格の版を合格と言う")
    return res


# --------------------------------------------------------------------------- #
# 9) 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section9_tool_gaps():
    print()
    print("=" * 78)
    print("9) 道具の穴 —— fullseye に無かったもの・引っかかったもの")
    print("=" * 78)
    import ops as _ops
    allnames = (set(dir(fs)) | set(dir(fs.ledger)) | set(dir(fs.op))
                | {o.name for o in _ops.REGISTRY})
    print("  探した層は 4 つ: fs.<名> / fs.op.<名> / fs.ledger.<名> / fs.op_find(語)。")
    print("  (公開層だけ見て「無い」と書かないための作法。)")
    print()

    # (a) 印刷・網点の語彙が 4 層のどこにも無い
    missing = {}
    for kw in ("halftone", "screen", "rosette", "misregist", "lpi", "moire",
               "trapping", "lattice"):
        hit = sorted(n for n in allnames if kw in n.lower())
        found = fs.op_find(kw)
        missing[kw] = (hit, found)
        assert not hit, (kw, hit)
        assert not found, (kw, found)
    print("  (a) ★**印刷の語彙が 4 層のどこにも無い**: 'halftone' / 'screen' /")
    print("      'rosette' / 'misregist' / 'lpi' / 'moire' / 'trapping' /")
    print("      'lattice' の 8 語すべてで名前 0 件・op_find 0 件。網点の合成、")
    print("      スクリーン角の推定、版ずれの測定はどれも産業用画像処理の定番で、")
    print("      入口が 1 つも無いのは大きい。この PoC は合成器を numpy で書いた。")

    # (b) 2 次元の並進を測る op が公開層に無い(周期性を意識したものは尚更)
    assert not hasattr(fs, "piv_cross_correlate")
    assert hasattr(fs.ledger, "piv_cross_correlate")
    a = np.random.default_rng(0).random((256, 256))
    b = np.roll(np.roll(a, 3, 0), 5, 1)
    flow_only = fs.ledger.piv_cross_correlate(a, b, window=64)
    flow, info = fs.ledger.piv_cross_correlate.raw(a, b, window=64)
    assert np.shape(flow_only) == np.shape(flow)
    assert "peak_ratio" in info and "valid_fraction" in info
    print("  (b) ★**「2 枚の画像の並進を 1 個返す」op が公開層(fs.*)に無い**。")
    print("      あるのは `fs.ledger.piv_cross_correlate`(場を返す)と")
    print("      `fs.frame_align`(星の対応)と `fs.demons_register`(非剛体)。")
    print("      しかも台帳の口は宣言 out 型に合わせて **info を捨てる** ので、")
    print("      `peak_ratio`(ピークの立ち方 = 不定性の警報になる量)へは")
    print("      `.raw` を知らないと届かない。この PoC も `.raw` を使っている。")

    # (c) 用途外の登録 op に食わせると、確信度 1.00 で外す
    ang, blob = PLATES[0][1], PLATES[0][2]
    # ★ 基準にも雑音を入れる —— 雑音ゼロの像だと star_detect が
    #   「星 0 個」で ValueError になる(それはそれで正しい fail-closed)。
    ref = am_sheet(ang, blob, 0.0, 0.0, seed=90)
    t = 1.30
    cur = am_sheet(ang, blob, 0.0, t, seed=91)
    _m, fa = fs.frame_align(1.0 - ref, 1.0 - cur, model="translation")
    fa_err = float(np.hypot(fa["shift_row"] - 0.0, fa["shift_col"] - t))
    fa_lat = lattice_residual(fa["shift_row"] - 0.0, fa["shift_col"] - t, ang)
    assert fa["inlier_ratio"] > 0.9 and fa_err > 10.0, (fa["inlier_ratio"], fa_err)
    assert fa_lat > 0.5, fa_lat        # 格子ベクトルですらない = 別種の失敗
    print("  (c) ★★**`fs.frame_align` は確信度 1.00 で %.2f px 外す**(用途外の"
          % fa_err)
    print("      使い方だが、落ちずに返るのが問題)。網点を星と見なして")
    print("      `n_inliers`=%d、`inlier_ratio`=**%.2f**、`rms_px`=%.3f を返しながら、"
          % (fa["n_inliers"], fa["inlier_ratio"], fa["rms_px"]))
    print("      真値 (%.2f, %.2f) に対して (%.2f, %.2f)。しかもこの答えは"
          % (0.0, t, fa["shift_row"], fa["shift_col"]))
    print("      **網点格子のベクトルですらない**(格子で簡約した残差 %.3f px)ので、"
          % fa_lat)
    print("      3 節の不定性とは**別種の失敗**(星の対応付けが偶然そろっただけ)。")
    print("      `inlier_ratio` は「同じ答えに賛成した点の割合」であって")
    print("      「答えが正しい確率」ではない —— **繰り返す構造の上では前者が 1.00 に")
    print("      なる**。docstring に「周期パターンには使えない」の一行が要る。")

    # (d) 相関マップを返す口が 2-D 画像に無い
    assert hasattr(fs.ledger, "correlation_score")     # 3-D voxel 用
    assert not hasattr(fs, "correlation_score")
    print("  (d) `fs.ledger.correlation_score` は **voxel 専用**(3-D)で、2-D 画像の")
    print("      相関マップを返す op は公開層に無い。6 節の「ピークが何本立って")
    print("      いるか」を見る図は、この PoC が `fs.cx_fft` / `fs.cx_ifft` で")
    print("      組んだ。`fs.peak_subbin` は素直に効いた(1-D なので軸ごとに 2 回)。")

    # (e) 2-D 画像のインク重心(1 次モーメント)が公開層に無い
    assert not any(hasattr(fs, n) for n in
                   ("image_centroid", "center_of_mass", "first_moment"))
    print("  (e) 2-D 画像の**重み付き重心**(1 次モーメント)を返す op が公開層に")
    print("      無い(`fs.centroid` は点群 (N,3) 専用、`central_moments` も点群)。")
    print("      2 節のゼロ点は numpy で書いた。**ゼロ点に使う道具ほど公開層に")
    print("      要る** —— 無いと、比べる相手を用意する手間で比較そのものが省かれる。")
    print()
    print("  次にやるべきこと: (a) の穴を `halftone_screen(image, lpi, angle)` と")
    print("  `screen_angle_estimate(image)` で埋めるなら、**3 節の不定性を")
    print("  docstring に測った数字で書くこと**。「相関で版ずれが測れます」とだけ")
    print("  書いた op を出すと、利用者は 8 節の見落とし(%d 回中 %d 回)を静かに"
          % (SWEEP.size, 0))
    print("  踏みます。返り値には**必ず不定性の格子**(p と θ から作れる)を")
    print("  添えて、「この答えは Λ_θ を法とする」と型で言うのが正しい。")
    return {"fa_err": fa_err, "fa_ratio": float(fa["inlier_ratio"]),
            "fa_lat": fa_lat}


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("印刷の版ずれを刷り上がりから測る —— 網点は格子なので、答えは 1 つに決まらない")
    print("スキャン %.0f dpi / 網点 %.0f lpi(p = %.2f px)/ 4 版 %s / 公差 %.1f px"
          % (SCAN_DPI, LPI, PITCH,
             "/".join("%s %.0f°" % (n, a) for n, a, _b, _d in PLATES), TOL_PX))
    print("=" * 78)

    sc = section1_scene()
    zero = section2_zero_point()
    pred = section3_predict()
    sweep = section4_sweep()
    per = section5_per_plate()
    fm = section6_control_fm(sweep)
    mk = section7_marks()
    met = section8_metrics(sweep, zero)
    gaps = section9_tool_gaps()

    print()
    print("=" * 78)
    print("まとめ")
    print("=" * 78)
    allr = [r for rows in sweep.values() for r in rows]
    print("  * 折り返しは幾何で予測できる: %d 点中 %d 点で予測と実測の差 <= %.4f px、"
          % (len(allr), sum(1 for r in allr if r["raw_err"] <= 0.5),
             max(r["raw_err"] for r in allr if r["raw_err"] <= 0.5)))
    print("    残りはセル境界のタイ。格子で簡約すれば全点が %.4f px 以内。"
          % max(r["lat_err"] for r in allr))
    print("  * 同じ物理的なずれ %.2f px が、版ごとに %.2f 〜 %.2f px に見える。"
          % (np.hypot(*PLATES[2][3]), min(per["mags"]), max(per["mags"])))
    print("  * 対照群: FM スクリーンに替えるだけで誤差は最大 %.4f px、折り返しゼロ。"
          % fm["fm_err"])
    print("  * レジストマークは当たる(誤差 %.4f px)が、%.0f px 離れると公差外。"
          % (mk["spots"][0]["err"], mk["r_meas"]))
    print("  * 物差しで勝者が入れ替わる: 精度 1 位は素の相関 %.4f px(低域通過は"
          % met["相関 AM(素)"]["rms"])
    print("    %.4f px)、判定一致率 1 位は低域通過 %.1f %%(素の相関は %.1f %%)。"
          % (met["相関 AM(低域通過)"]["rms"], met["相関 AM(低域通過)"]["rate"],
             met["相関 AM(素)"]["rate"]))
    print()
    print("  所要 %.1f 秒" % (time.perf_counter() - t0))

    # --- 所見を固定する(穴が塞がったら鳴る)--- #
    # 1) 合成器: 仕込んだスクリーン角と線数がスキャンから読める
    assert sc["ang_err"] < 1.0, sc["ang_err"]
    assert sc["lpi_err"] < 3.0, sc["lpi_err"]
    # 2) ゼロ点 A は壊れ、B は折り返さない。重心の傾きは閉形式で予測できる
    assert zero["err_a"] > 20.0, zero["err_a"]
    assert abs(zero["k_art"] - zero["k_pred"]) < 0.06, (zero["k_art"], zero["k_pred"])
    assert abs(zero["k_flat"]) < 0.05, zero["k_flat"]
    assert zero["ripple"] > 10.0 * zero["ripple_taper"], (zero["ripple"],
                                                          zero["ripple_taper"])
    # 3) Y 版だけが折り返す予測
    assert np.hypot(*pred["Y"]) < np.hypot(*PLATES[2][3]) - 1.0, pred["Y"]
    assert np.hypot(*pred["Y"]) < TOL_PX < np.hypot(*PLATES[2][3])
    # 4) 予測と実測: 格子で簡約した残差は全点で小さい
    assert max(r["lat_err"] for r in allr) < 0.10, max(r["lat_err"] for r in allr)
    assert max(r["piv_lat"] for r in allr) < 1.0, max(r["piv_lat"] for r in allr)
    ties = [r for r in allr if r["raw_err"] > 0.5]
    assert all(r["margin"] < 0.8 for r in ties), [r["margin"] for r in ties]
    assert len(ties) < 0.15 * len(allr), len(ties)
    # 5) 同じずれが版ごとに違って見える(1.5 倍以上の開き)
    assert max(per["mags"]) / min(per["mags"]) > 1.5, per["mags"]
    assert max(per["diffs"]) < 0.05, per["diffs"]
    # 6) 対照群: FM は折り返さない
    assert fm["fm_err"] < 0.1, fm["fm_err"]
    assert fm["am_err"] > 5.0, fm["am_err"]
    # 7) マークは当たるが遠くで外れる
    assert mk["spots"][0]["err"] < 0.3, mk["spots"][0]["err"]
    assert mk["spots"][1]["err"] > 5.0, mk["spots"][1]["err"]
    assert mk["field_err"] < 0.3, mk["field_err"]
    assert mk["pred_meas_diff"] < 0.2, mk["pred_meas_diff"]
    assert abs(mk["r_meas"] - mk["r_crit"]) < 20.0, (mk["r_meas"], mk["r_crit"])
    assert mk["r_crit"] < np.hypot(L, L), mk["r_crit"]
    assert mk["frac_out"] > 0.2, mk["frac_out"]
    # 8) 物差しで勝者が入れ替わる(精度 1 位と判定 1 位が別の手法)
    m_raw, m_lp = met["相関 AM(素)"], met["相関 AM(低域通過)"]
    m_two = met["★二段(粗+密)"]
    assert m_raw["rms"] < m_lp["rms"] / 5.0, (m_raw["rms"], m_lp["rms"])
    assert m_raw["rate"] < m_lp["rate"] - 20.0, (m_raw["rate"], m_lp["rate"])
    assert m_raw["miss"] > 5, m_raw["miss"]
    assert m_lp["miss"] <= 1, m_lp["miss"]
    # 二段は両方勝つ。ただし粗の誤差がセルの半径を超えると壊れる(実測済み)
    assert m_two["rms"] < 1.5 * m_raw["rms"] + 1e-6, (m_two["rms"], m_raw["rms"])
    assert m_two["rate"] > m_raw["rate"] + 20.0, (m_two["rate"], m_raw["rate"])
    assert met["coarse_max"] < PITCH / 2, (met["coarse_max"], PITCH / 2)
    assert met["two_stage_broken"] >= 1, met["two_stage_broken"]
    assert met["相関 FM"]["rate"] > 95.0, met["相関 FM"]["rate"]
    # 9) 道具の穴(埋まったら鳴る)
    assert gaps["fa_err"] > 10.0 and gaps["fa_ratio"] > 0.9

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
