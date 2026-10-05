# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tacscalib — 視触覚センサの照明を実機の較正球で較正し、example-based の勾配 LUT を第 2 実装にする(2026-10-05)。

物理シミュ × Fullseye 系列、tacsim(弾性膜 + カメラの合成と逆算、2026.196)の続き。tacsim は「3 色照明の Lambertian」を
自分で合成して自分で逆算した —— 真値も被験者も手元で作った。ここは**実機の画像**を持ち込み、順方向(法線 → 色)を較正して
逆方向(色 → 法線)を 2 つの独立な経路で解く:

  * **線形模型**(チャネルごとに I_c = a_c + l_c · n、12 パラメタ): 逆算は既存 op :func:`photometric.photometric_stereo`
    (``normalize=False``)をそのまま被験者にする。
  * **example-based の勾配 LUT**(法線の傾き θ・向き φ を bins × bins に切り、ビンごとに色の平均。位置の 2 次式つきの版は
    ビンごとに RGB = 6 係数 · [x², y², xy, x, y, 1]): 先行研究(arXiv:2109.04027 の較正手順 = 位置依存の多項式 LUT、
    Sensors 17(12):2762, 2017 の「全画像の平均」LUT)の考え方を読んで再実装した。コードは写していない。

真値は外から来る:
  * **球の半径**(既知球 R、較正パックに付く寸法)。接触円の内側で膜が球面にならうので、法線は閉形式
    n = (−x, −y, √(R² − r²))/R(tacsim の規約)。**R は較正にも評価にも入る**(両辺) —— 門が見ているのは「別の画像に一般化
    するか」で、R そのものは検証していない。
  * **手で当てた接触円**(中心・半径、整数 px、半径は 2 px 刻み)= 弱い真値。
  * 実機画像そのもの(arXiv:2109.04027 の作者が MIT ライセンスで公開した較正パック。置き場は環境変数 ``FULLSEYE_TAXIM_DATA``)。

op(台帳 ``tacscalib``、opsdrive、全部 numpy): :func:`calib_pack_load` 較正パックの読み込み(fail-closed)/
  :func:`sphere_normals_known` 既知球の法線 / :func:`lights_fit_from_sphere` 照明の較正(線形、``order=2`` で位置つき)/
  :func:`membrane_predict_rgb` 順方向 / :func:`gradient_lut_build` 勾配 LUT / :func:`gradient_lut_invert` LUT の逆引き
  (粗 → 細の探索、``method="exact"`` で総当たり)/ :func:`normal_error_map` 角誤差(atan2)/ :func:`sphere_cap_height` 球冠の高さ /
  :func:`field_position_sweep` 誤差の位置依存。アダプタ: :func:`poly_lut_invert`(外部の位置 2 次 LUT の書式を読んで同じ逆引きへ)。

試作で踏んだこと(正直に): (1) 位置の 2 次式を「30 行以上のビン」にだけ当てると、傾きの小さいビン(傾き 0 のビンは較正球 24 枚で
24 画素)が全部落ち、平らな所が 15° に張り付き 0〜15° が不感帯になった。直し方 = 接触から遠い輪を「平ら」として足す
(``flat_rgb``)+ 行の少ないビンは角度で最も近い多項式ビンの位置の項を借り、定数項だけを自分の平均に合わせる(``pool=True``)。
(2) 逆引きの総当たりは画素 × 6,000〜15,600 ビンで、データ門の時間の大半だった → 粗 → 細(3 × 3 ビンの区画の代表で上位 2 区画に
当たりを付け、その周りだけ細かく引く)。色 → 法線は多峰なので総当たりと同じビンを選ぶのは約 9 割 —— 一致率と角誤差の差を門にする。(3) 背景差分は位置つき LUT には要らない(背景も位置の 2 次式に
吸収される)が、位置に依らない経路では要る —— 経路で答えが逆になる。

規約: 画素の (行, 列) = (y, x)。法線は :mod:`photometric` と同じ (−∂h/∂x, −∂h/∂y, 1)/|·|、x = 列・y = 行。高さ h はへこむ向きが負。
長さは m(引数名に ``_mm`` が付くものだけ mm、``_px`` は画素)。角度はすべて atan2(acos は単位ベクトルの近くで丸めの床を持つ)。
"""
from __future__ import annotations

import math
import os

import numpy as np

import photometric as _ph

__all__ = [
    "calib_pack_load", "sphere_normals_known", "lights_fit_from_sphere", "membrane_predict_rgb",
    "gradient_lut_build", "gradient_lut_invert", "normal_error_map", "sphere_cap_height", "field_position_sweep",
    "poly_lut_invert", "linear_invert", "normals_to_angles", "PACK_KEYS",
]

#: 較正パックに必須のキー(1 つでも欠けたら ValueError、fail-closed)
PACK_KEYS = ("f0", "imgs", "touch_center", "touch_radius")


# ----------------------------------------------------------------------------------------------------------------------
# 小道具
def _shape2(shape, who: str) -> tuple:
    """(H, W) を正の整数 2 つとして読む(型が違えば ValueError)。"""
    try:
        H, W = int(shape[0]), int(shape[1])
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError("%s: shape must be (H, W), got %r" % (who, shape)) from exc
    if H < 1 or W < 1:
        raise ValueError("%s: shape must be positive, got %r" % (who, shape))
    return H, W


def _point2(p, who: str) -> tuple:
    """(行, 列) を有限の実数 2 つとして読む。"""
    try:
        y, x = float(p[0]), float(p[1])
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError("%s: centre must be (row, col), got %r" % (who, p)) from exc
    if not (math.isfinite(y) and math.isfinite(x)):
        raise ValueError("%s: centre must be finite" % who)
    return y, x


def normals_to_angles(normals):
    """法線 → (傾き θ ∈ 0..π/2, 向き φ ∈ −π..π)。θ = atan2(|n_xy|, n_z)、φ = atan2(n_y, n_x)。"""
    n = np.asarray(normals, np.float64)
    return np.arctan2(np.hypot(n[..., 0], n[..., 1]), n[..., 2]), np.arctan2(n[..., 1], n[..., 0])


def _bin_index(theta, phi, bins: int):
    """ビン割り(先行研究の較正手順と同じ): θ の 0..π/2 を (bins−1) 等分、φ の −π..π を (bins−1) 等分(floor、端は切る)。"""
    binm = bins - 1
    ix = np.floor(np.asarray(theta) / (0.5 * math.pi / binm)).astype(np.int64)
    iy = np.floor((np.asarray(phi) + math.pi) / (2.0 * math.pi / binm)).astype(np.int64)
    return np.clip(ix, 0, bins - 1), np.clip(iy, 0, bins - 1)


def _bin_centre_normals(bins: int) -> np.ndarray:
    """ビン (i, j) の中心の法線 (bins, bins, 3)。"""
    binm = bins - 1
    th = (np.arange(bins) + 0.5) * (0.5 * math.pi / binm)
    ph = (np.arange(bins) + 0.5) * (2.0 * math.pi / binm) - math.pi
    T, P = np.meshgrid(th, ph, indexing="ij")
    return np.stack([np.sin(T) * np.cos(P), np.sin(T) * np.sin(P), np.cos(T)], axis=-1)


def _pos_basis(rows, cols, basis: str, image_shape=None) -> np.ndarray:
    """位置の 2 次基底 [x², y², xy, x, y, 1]。``basis="unit"`` は画像寸法で x, y を −1..1 に、``"pixel"`` は画素のまま。"""
    r = np.asarray(rows, np.float64)
    c = np.asarray(cols, np.float64)
    if basis == "unit":
        Hh, Ww = float(image_shape[0]), float(image_shape[1])
        y = 2.0 * r / max(Hh - 1.0, 1.0) - 1.0
        x = 2.0 * c / max(Ww - 1.0, 1.0) - 1.0
    elif basis == "pixel":
        y, x = r, c
    else:
        raise ValueError("unknown position basis %r" % (basis,))
    return np.column_stack([x * x, y * y, x * y, x, y, np.ones_like(x)])


# ----------------------------------------------------------------------------------------------------------------------
# 読み込みと真値
def calib_pack_load(path: str, pitch_mm: float, ball_radius_mm: float) -> dict:
    """較正パック(npz)→ dict。キー ``f0``(背景 (H, W, 3) uint8)・``imgs``((N, H, W, 3))・``touch_center``((N, 2) = (列 x, 行 y))・
    ``touch_radius``((N,) px)を必須とし、中心は (行, 列) に並べ替えて ``centers`` で返す。

    ``pitch_mm`` [mm/px] と ``ball_radius_mm`` は呼び出し側が与える(パックの中に無い)。返り: ``f0``・``imgs``・``centers`` (N, 2)・
    ``radii`` (N,) [px]・``pitch``(m/px)・``pitch_mm``・``R_mm``・``R_px``(= 半径 / ピッチ)・``n``。
    データ置き場は呼び出し側が環境変数(例 ``FULLSEYE_TAXIM_DATA``)から組む。

    **Raises** ``ValueError``: キー欠落(綴り違いも)/ 形の不一致 / 画像 0 枚 / 中心が非有限 / 半径 ≤ 0 / pitch・球半径 ≤ 0。
    ``FileNotFoundError``: パスが無い。"""
    if not isinstance(path, (str, os.PathLike)):
        raise ValueError("calib_pack_load: path must be a str, got %s" % type(path).__name__)
    pm, rm = float(pitch_mm), float(ball_radius_mm)
    if not (math.isfinite(pm) and math.isfinite(rm) and pm > 0.0 and rm > 0.0):
        raise ValueError("calib_pack_load: pitch_mm and ball_radius_mm must be finite and > 0")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with np.load(path, allow_pickle=False) as d:
        missing = [k for k in PACK_KEYS if k not in d.files]
        if missing:
            raise ValueError("calib_pack_load: missing keys %s (have %s)" % (missing, sorted(d.files)))
        f0 = np.asarray(d["f0"])
        imgs = np.asarray(d["imgs"])
        tc = np.asarray(d["touch_center"], np.float64)
        tr = np.asarray(d["touch_radius"], np.float64)
    if f0.ndim != 3 or f0.shape[2] != 3:
        raise ValueError("calib_pack_load: f0 must be (H, W, 3), got %s" % (f0.shape,))
    if imgs.ndim != 4 or imgs.shape[1:] != f0.shape:
        raise ValueError("calib_pack_load: imgs must be (N, H, W, 3) matching f0, got %s" % (imgs.shape,))
    n = int(imgs.shape[0])
    if n < 1:
        raise ValueError("calib_pack_load: no images")
    if tc.shape != (n, 2) or tr.shape != (n,):
        raise ValueError("calib_pack_load: touch_center (N, 2) / touch_radius (N,) disagree with N=%d" % n)
    if not (np.all(np.isfinite(tc)) and np.all(np.isfinite(tr)) and np.all(tr > 0)):
        raise ValueError("calib_pack_load: non-finite centre or non-positive radius")
    return {"f0": f0, "imgs": imgs, "centers": tc[:, ::-1].copy(), "radii": tr, "pitch": pm * 1e-3, "pitch_mm": pm,
            "R_mm": rm, "R_px": rm / pm, "n": n}


def sphere_normals_known(shape, centre, a_px: float, R_px: float, inner: float = 1.0) -> dict:
    """既知球の押し込み: 接触円(中心 ``centre`` = (行, 列)、半径 ``a_px``)の内側で法線を閉形式で返す。

    n = (−dx, −dy, √(R² − r²))/R(dx = 列 − 中心の列、dy = 行 − 中心の行)。マスクは r < inner · min(a, R)(較正手順と同じく
    a と R の小さい方まで)。外側は (0, 0, 1)。返り: ``normals`` (H, W, 3)、``mask`` (H, W) bool、``r`` (H, W) [px]、
    ``theta``(傾き角 = atan2(r, √(R² − r²))、マスク外 0)。
    **Raises** ``ValueError``: shape・centre の形、a・R ≤ 0、inner が 0 < inner ≤ 1 の外。"""
    H, W = _shape2(shape, "sphere_normals_known")
    cy, cx = _point2(centre, "sphere_normals_known")
    a_px, R_px = float(a_px), float(R_px)
    if not (math.isfinite(a_px) and math.isfinite(R_px) and a_px > 0.0 and R_px > 0.0):
        raise ValueError("sphere_normals_known: a_px and R_px must be finite and > 0")
    if not (0.0 < float(inner) <= 1.0):
        raise ValueError("sphere_normals_known: inner must satisfy 0 < inner <= 1")
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    dy, dx = yy - cy, xx - cx
    r = np.hypot(dx, dy)
    mask = r < float(inner) * min(a_px, R_px)
    s = np.sqrt(np.maximum(R_px * R_px - r * r, 0.0))
    nrm = np.zeros((H, W, 3))
    nrm[..., 2] = 1.0
    nrm[mask, 0] = -dx[mask] / R_px
    nrm[mask, 1] = -dy[mask] / R_px
    nrm[mask, 2] = s[mask] / R_px
    theta = np.where(mask, np.arctan2(r, s), 0.0)
    return {"normals": nrm, "mask": mask, "r": r, "theta": theta}


# ----------------------------------------------------------------------------------------------------------------------
# 線形模型(順方向の較正)
def _as_lists(diffs, normals, masks, who):
    if isinstance(diffs, np.ndarray) and diffs.ndim == 3:
        diffs, normals, masks = [diffs], [normals], [masks]
    if not isinstance(diffs, (list, tuple)) or not isinstance(normals, (list, tuple)) or not isinstance(masks, (list, tuple)):
        raise ValueError("%s: give one (H, W, 3) image or lists of images / normals / masks" % who)
    if not (len(diffs) == len(normals) == len(masks)) or len(diffs) == 0:
        raise ValueError("%s: diffs / normals / masks must be same-length non-empty lists" % who)
    out = []
    for d, n, m in zip(diffs, normals, masks):
        d = np.asarray(d, np.float64)
        n = np.asarray(n, np.float64)
        m = np.asarray(m, bool)
        if d.ndim != 3 or d.shape[2] != 3 or d.shape != n.shape or d.shape[:2] != m.shape:
            raise ValueError("%s: shapes disagree %s %s %s" % (who, d.shape, n.shape, m.shape))
        out.append((d, n, m))
    return out


def lights_fit_from_sphere(diffs, normals, masks, order: int = 0) -> dict:
    """背景差分画像(1 枚か列)と既知法線から、チャネルごとの線形 Lambertian 模型を最小二乗で解く。

    ``order=0``: I_c = a_c + l_c · n(3 チャネル × 4 = 12 パラメタ)。``order=2``(診断用): 4 つの係数それぞれが位置の 2 次式
    (チャネルあたり 24、計 72 パラメタ)—— 線形模型の残差が「照明の非一様」か「反射の非線形」かを分ける。
    ``diffs`` (H, W, 3) かその列、``normals`` (H, W, 3) の列、``masks`` (H, W) bool の列。

    返り: ``order``、``L`` (3, 3)(行 c = l_c、長さ = チャネルの強度。order 2 は画像中心の値)、``ambient`` (3,)、``rms`` (3,)
    (当てはめ残差)、``n_rows``(使った画素数)、``cond``(設計行列の条件数)、order 2 は ``coef`` (4, 6, 3) と ``image_shape``。
    **Raises** ``ValueError``: 列の長さ・形の不一致 / order が 0・2 以外 / 画素が未知数より少ない / 法線が退化(平面上)。"""
    items = _as_lists(diffs, normals, masks, "lights_fit_from_sphere")
    if order not in (0, 2):
        raise ValueError("lights_fit_from_sphere: order must be 0 or 2")
    shape = items[0][0].shape[:2]
    A, B = [], []
    for d, n, m in items:
        if d.shape[:2] != shape:
            raise ValueError("lights_fit_from_sphere: all images must share one shape")
        F = np.column_stack([np.ones(int(m.sum())), n[m]])                      # (p, 4)
        if order == 2:
            ys, xs = np.nonzero(m)
            Pb = _pos_basis(ys, xs, "unit", shape)
            F = (F[:, :, None] * Pb[:, None, :]).reshape(len(ys), 24)
        A.append(F)
        B.append(d[m])
    A = np.concatenate(A)
    B = np.concatenate(B)
    if A.shape[0] < A.shape[1] * 3:
        raise ValueError("lights_fit_from_sphere: need >= %d pixels, got %d" % (A.shape[1] * 3, A.shape[0]))
    sv = np.linalg.svd(A, compute_uv=False)
    cond = float(sv[0] / max(sv[-1], 1e-300))
    if not (sv[-1] > 1e-9 * sv[0]):
        raise ValueError("lights_fit_from_sphere: degenerate normals (cond %.3g)" % cond)
    X, *_ = np.linalg.lstsq(A, B, rcond=None)
    res = B - A @ X
    out = {"order": int(order), "rms": np.sqrt(np.mean(res ** 2, axis=0)), "n_rows": int(A.shape[0]), "cond": cond}
    if order == 0:
        out.update({"L": X[1:].T.copy(), "ambient": X[0].copy()})
    else:
        coef = X.reshape(4, 6, 3)
        out.update({"coef": coef, "image_shape": tuple(int(v) for v in shape), "L": coef[1:, 5, :].T.copy(),
                    "ambient": coef[0, 5, :].copy()})
    return out


def membrane_predict_rgb(normals, fit: dict) -> np.ndarray:
    """法線 (H, W, 3) + :func:`lights_fit_from_sphere` の結果 → 背景差分 RGB の予測 (H, W, 3)(線形、クリップしない)。
    order 2 の結果は画素ごとに a(x, y)・L(x, y) を作る(画像の大きさは較正時と同じであること)。
    **Raises** ``ValueError``: 法線の形 / order 2 で画像の大きさが違う。"""
    n = np.asarray(normals, np.float64)
    if n.ndim != 3 or n.shape[2] != 3:
        raise ValueError("membrane_predict_rgb: normals must be (H, W, 3)")
    if not isinstance(fit, dict) or "L" not in fit:
        raise ValueError("membrane_predict_rgb: fit must come from lights_fit_from_sphere")
    if int(fit.get("order", 0)) == 0:
        return np.asarray(fit["ambient"], np.float64)[None, None, :] + np.einsum("hwk,ck->hwc", n, np.asarray(fit["L"], np.float64))
    if tuple(fit["image_shape"]) != n.shape[:2]:
        raise ValueError("membrane_predict_rgb: order-2 fit was made for %s, got %s" % (fit["image_shape"], n.shape[:2]))
    H, W = n.shape[:2]
    ys, xs = np.mgrid[0:H, 0:W]
    Pb = _pos_basis(ys.ravel(), xs.ravel(), "unit", (H, W))
    C = np.einsum("pk,fkc->pfc", Pb, np.asarray(fit["coef"], np.float64))       # (p, 4, 3)
    nn = n.reshape(-1, 3)
    return (C[:, 0, :] + np.einsum("pk,pkc->pc", nn, C[:, 1:, :])).reshape(H, W, 3)


def linear_invert(diff, fit: dict) -> np.ndarray:
    """線形模型の逆算 = 既存 op :func:`photometric.photometric_stereo`(``normalize=False``、強度つきの光源 = 較正した L)に
    ``diff − ambient`` を渡す(補助、台帳の外)。返り: 法線 (H, W, 3)。"""
    d = np.asarray(diff, np.float64) - np.asarray(fit["ambient"], np.float64)[None, None, :]
    nrm, _alb = _ph.photometric_stereo(np.moveaxis(d, -1, 0), np.asarray(fit["L"], np.float64), normalize=False)
    return np.asarray(nrm, np.float64)


# ----------------------------------------------------------------------------------------------------------------------
# 勾配 LUT(第 2 実装)
def gradient_lut_build(rgb_rows, normal_rows, bins: int = 125, positions=None, image_shape=None, flat_rgb=None,
                       flat_positions=None, min_rows_poly: int = 30, ridge: float = 1e-3, pool: bool = True) -> dict:
    """example-based の勾配 LUT: 法線の(傾き θ, 向き φ)を bins × bins に切り、各ビンに落ちた画素の RGB の**平均**を入れる
    (``np.add.at`` で重複した添字も全部足す)。``rgb_rows`` (P, 3)、``normal_rows`` (P, 3)。

    ``positions``((P, 2) = (行, 列))と ``image_shape`` を与えると位置依存版: ``min_rows_poly`` 行以上のビンに
    RGB = 6 係数 · [x², y², xy, x, y, 1] を当てる(x, y は画像寸法で −1..1、定数項以外に小さなリッジ)。``pool=True`` なら
    行の少ないビンは角度で最も近い多項式ビンの位置の項(5 係数)を借り、定数項だけを自分の行の平均に合わせる —— 位置の項を
    当てたビンだけで引くと傾きの小さいビンが全部落ちて 0〜15° が不感帯になる(試作で踏んだ罠)。
    ``flat_rgb``((F, 3)、位置つきなら ``flat_positions`` (F, 2) も)は「平らな例」= 法線 (0, 0, 1) として足す行(接触から
    遠い輪など、弱い真値)。

    返り: ``bins``、``mean_rgb`` (bins, bins, 3)(空のビンは nan)、``count`` (bins, bins)、``centre_normals`` (bins, bins, 3)、
    ``n_rows``、``n_flat``、``coef`` ((bins, bins, 6, 3) か None)、``basis``(``"unit"``)、``image_shape``、``poly_bins``・
    ``pooled_bins``(位置の項を当てた / 借りたビンの数)。
    **Raises** ``ValueError``: 形の不一致 / bins < 4 / min_rows_poly < 6 / 行が 0 / 非有限 / positions と image_shape の片方だけ /
    flat_positions だけ。"""
    rgb = np.asarray(rgb_rows, np.float64)
    nrm = np.asarray(normal_rows, np.float64)
    if rgb.ndim != 2 or rgb.shape[1] != 3 or nrm.shape != rgb.shape:
        raise ValueError("gradient_lut_build: rgb_rows and normal_rows must both be (P, 3)")
    if int(bins) < 4:
        raise ValueError("gradient_lut_build: bins must be >= 4")
    if int(min_rows_poly) < 6:
        raise ValueError("gradient_lut_build: min_rows_poly must be >= 6 (six coefficients per bin)")
    bins = int(bins)
    pos = None
    if (positions is None) != (image_shape is None):
        raise ValueError("gradient_lut_build: give positions and image_shape together")
    if positions is None and flat_positions is not None:
        raise ValueError("gradient_lut_build: flat_positions without positions")
    if positions is not None:
        pos = np.asarray(positions, np.float64)
        if pos.shape != (rgb.shape[0], 2):
            raise ValueError("gradient_lut_build: positions must be (P, 2) = (row, col)")
        image_shape = _shape2(image_shape, "gradient_lut_build")
    n_flat = 0
    if flat_rgb is not None:
        fr = np.asarray(flat_rgb, np.float64)
        if fr.ndim != 2 or fr.shape[1] != 3:
            raise ValueError("gradient_lut_build: flat_rgb must be (F, 3)")
        fn = np.zeros_like(fr)
        fn[:, 2] = 1.0
        if pos is not None:
            fp = np.asarray(flat_positions, np.float64) if flat_positions is not None else None
            if fp is None or fp.shape != (fr.shape[0], 2):
                raise ValueError("gradient_lut_build: flat_positions (F, 2) is required with positions")
            pos = np.concatenate([pos, fp])
        rgb, nrm, n_flat = np.concatenate([rgb, fr]), np.concatenate([nrm, fn]), int(fr.shape[0])
    if rgb.shape[0] == 0:
        raise ValueError("gradient_lut_build: no rows")
    if not (np.all(np.isfinite(rgb)) and np.all(np.isfinite(nrm))):
        raise ValueError("gradient_lut_build: non-finite rows")
    th, ph = normals_to_angles(nrm)
    ix, iy = _bin_index(th, ph, bins)
    s = np.zeros((bins, bins, 3))
    c = np.zeros((bins, bins))
    np.add.at(s, (ix, iy), rgb)
    np.add.at(c, (ix, iy), 1.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(c[..., None] > 0, s / np.maximum(c, 1.0)[..., None], np.nan)
    cn = _bin_centre_normals(bins)
    out = {"bins": bins, "mean_rgb": mean, "count": c, "centre_normals": cn, "n_rows": int(rgb.shape[0]), "n_flat": n_flat,
           "coef": None, "basis": "unit", "image_shape": None, "poly_bins": 0, "pooled_bins": 0}
    if pos is None:
        return out
    A = _pos_basis(pos[:, 0], pos[:, 1], "unit", image_shape)
    AtA = np.zeros((bins, bins, 6, 6))
    Atb = np.zeros((bins, bins, 6, 3))
    sA = np.zeros((bins, bins, 6))
    np.add.at(AtA, (ix, iy), A[:, :, None] * A[:, None, :])
    np.add.at(Atb, (ix, iy), A[:, :, None] * rgb[:, None, :])
    np.add.at(sA, (ix, iy), A)
    coef = np.zeros((bins, bins, 6, 3))
    coef[..., 5, :] = np.nan_to_num(mean)
    use = c >= int(min_rows_poly)
    if use.any():
        reg = np.diag([float(ridge)] * 5 + [0.0])
        M = AtA[use] + reg[None] * c[use][:, None, None]
        coef[use] = np.linalg.solve(M, Atb[use])
    n_pool = 0
    small = (c > 0) & ~use
    if pool and use.any() and small.any():
        sidx = np.argwhere(small)
        cnp = cn[use]                                   # (Kp, 3)
        coefp = coef[use]                               # (Kp, 6, 3)
        near = np.empty(len(sidx), np.int64)
        for k in range(0, len(sidx), 1024):            # 最も近い多項式ビン(中心法線の内積が最大 = 角度が最小)
            blk = cn[sidx[k:k + 1024, 0], sidx[k:k + 1024, 1]]
            near[k:k + 1024] = np.argmax(blk @ cnp.T, axis=1)
        c5 = coefp[near][:, :5, :]                      # (s, 5, 3)
        mA5 = sA[small][:, :5] / c[small][:, None]      # 自分の行の基底の平均
        const = mean[small] - np.einsum("sk,skc->sc", mA5, c5)
        cs = np.concatenate([c5, const[:, None, :]], axis=1)
        coef[small] = cs
        n_pool = int(len(sidx))
    out.update({"coef": coef, "image_shape": tuple(image_shape), "poly_bins": int(use.sum()), "pooled_bins": n_pool,
                "min_rows_poly": int(min_rows_poly)})
    return out


def _valid_bins(table: dict, min_count: int) -> np.ndarray:
    ok = np.asarray(table["count"]) >= int(min_count)
    if table.get("coef") is None:
        ok &= np.all(np.isfinite(table["mean_rgb"]), axis=-1)
    return ok


def _cell_representatives(valid: np.ndarray, count: np.ndarray, co: int) -> np.ndarray:
    """粗い区画(co × co ビン)ごとの代表ビン(平らな添字): 中身のあるビンのうち行が最も多いもの、同数なら区画の中央寄り。"""
    bins = valid.shape[0]
    ii, jj = np.nonzero(valid)
    cell = (ii // co) * ((bins + co - 1) // co) + (jj // co)
    off = (ii % co - 0.5 * (co - 1)) ** 2 + (jj % co - 0.5 * (co - 1)) ** 2
    score = np.asarray(count, np.float64)[ii, jj] - 1e-3 * off
    order = np.lexsort((-score, cell))
    _, first = np.unique(cell[order], return_index=True)
    sel = order[first]
    return ii[sel] * bins + jj[sel]


def _fine_candidates(best_flat: np.ndarray, bins: int, co: int) -> np.ndarray:
    """粗い当たりのビンの区画を中心に 3 × 3 区画(θ は端で切り、φ は周期で回す)の全ビン = (p, (3co)²) の平らな添字。"""
    bi, bj = best_flat // bins, best_flat % bins
    ci, cj = (bi // co) * co, (bj // co) * co
    d = np.arange(-co, 2 * co)
    I = np.clip(ci[:, None] + d[None, :], 0, bins - 1)                      # (p, 3co)
    J = np.mod(cj[:, None] + d[None, :], bins)
    return (I[:, :, None] * bins + J[:, None, :]).reshape(len(best_flat), -1)


_IU = np.triu_indices(6)
_IU_W = np.where(_IU[0] == _IU[1], 1.0, 2.0)


def _bin_features(table: dict) -> np.ndarray:
    """距離を 1 回の行列積にするためのビンごとの特徴 F (bins², f)。画素の特徴 G と d = G · F が |予測色 − 色|² − |色|² になる。

    位置なし: 予測色 k は定数 → F = [|k|², k] の 4 列。位置つき: k_c = A · C_c → |k|² = Aᵀ Q A(Q = Σ_c C_c C_cᵀ、上三角 21 項)、
    k · v = Σ_c v_c (A · C_c)(18 項)→ F = [Q の上三角 × 重み, C] の 39 列。float64 で持つ(画素の基底は x² ≈ 4e5 になりうる)。"""
    bins = int(table["bins"])
    coef = table.get("coef")
    if coef is None:
        k = np.nan_to_num(np.asarray(table["mean_rgb"], np.float64)).reshape(-1, 3)
        return np.column_stack([np.sum(k * k, axis=1), k])
    C = np.asarray(coef, np.float64).reshape(bins * bins, 6, 3)
    Q = np.einsum("kic,kjc->kij", C, C)
    return np.column_stack([Q[:, _IU[0], _IU[1]] * _IU_W[None, :], C.reshape(bins * bins, 18)])


def _pixel_features(vals, A) -> np.ndarray:
    """画素の特徴 G (P, f)(:func:`_bin_features` と対)。"""
    v = np.asarray(vals, np.float64)
    if A is None:
        return np.column_stack([np.ones(len(v)), -2.0 * v])
    A = np.asarray(A, np.float64)
    AA = A[:, _IU[0]] * A[:, _IU[1]]
    vA = (A[:, :, None] * v[:, None, :]).reshape(len(v), 18)
    return np.column_stack([AA, -2.0 * vA])


def _lut_search(vals, A, table, valid, method: str, coarse: int, chunk: int, topk: int = 2) -> np.ndarray:
    """各画素(``vals`` (P, 3)、位置つきなら基底 ``A`` (P, 6))に最も近いビンの平らな添字。距離は特徴の内積(BLAS の行列積)。

    粗 → 細の 2 段目は「同じ区画を当たりにした画素」をまとめ、区画の周り 3 × 3 区画のビンとだけ行列積をとる(画素ごとに候補を
    集めると候補の特徴の写しがメモリを食い、総当たりより遅くなった —— 実測)。"""
    bins = int(table["bins"])
    vflat = valid.ravel()
    F = _bin_features(table)
    G = _pixel_features(vals, A)
    P = len(G)
    co = int(coarse)
    use_coarse = method == "coarse" and co >= 2 and bins >= 3 * co
    reps = _cell_representatives(valid, table["count"], co) if use_coarse else np.flatnonzero(vflat)
    Fr = F[reps]
    kk = max(1, min(int(topk), len(reps))) if use_coarse else 1
    top = np.empty((P, kk), np.int64)
    for s in range(0, P, chunk):                                              # 1 段目: 総当たり(exact)か粗い代表(coarse)
        d = G[s:s + chunk] @ Fr.T
        rows = np.arange(len(d))
        for q in range(kk):                                                   # 上位 kk を argmin の繰り返しで(argpartition より速い)
            j = np.argmin(d, axis=1)
            top[s:s + chunk, q] = j
            d[rows, j] = np.inf
    if not use_coarse:
        return reps[top[:, 0]]
    # 2 段目: 色の近い上位 kk 区画それぞれについて、同じ区画を選んだ画素をまとめて周り 3 × 3 区画を細かく
    ncj = (bins + co - 1) // co
    best = np.full(P, -1, np.int64)
    dbest = np.full(P, np.inf)
    for q in range(kk):
        rb = reps[top[:, q]]
        cell = (rb // bins // co) * ncj + (rb % bins) // co
        order = np.argsort(cell, kind="stable")
        uniq, first = np.unique(cell[order], return_index=True)
        stops = np.append(first[1:], P)
        windows = _fine_candidates(rb[order[first]], bins, co)               # 区画ごとの候補(まとめて 1 回)
        for w, a, b in zip(windows, first, stops):
            idx = order[a:b]
            cand = w[vflat[w]]
            if len(cand) == 0:
                continue
            dd = G[idx] @ F[cand].T
            j = np.argmin(dd, axis=1)
            dm = dd[np.arange(len(idx)), j]
            better = dm < dbest[idx]
            dbest[idx[better]] = dm[better]
            best[idx[better]] = cand[j[better]]
    if np.any(best < 0):                     # 当たりの代表ビン自身が必ず窓に入るので起きないはず(起きたら黙って (0,0,1) にしない)
        raise RuntimeError("gradient_lut_invert: coarse-to-fine left %d pixels unassigned" % int(np.sum(best < 0)))
    return best


def gradient_lut_invert(rgb, table: dict, mask=None, min_count: int = 1, method: str = "coarse", coarse: int = 3,
                        topk: int = 2, chunk: int = 1024) -> np.ndarray:
    """RGB (H, W, 3) → 法線 (H, W, 3): 中身のあるビン(count ≥ ``min_count``)のうち色が最も近いものの中心法線。位置依存版の
    表(:func:`gradient_lut_build` に positions を与えたもの)は画素の位置で各ビンの色を予測してから比べる。

    ``method="coarse"``(既定): ``coarse`` × ``coarse`` ビンの区画ごとに代表(行の最も多いビン)を置いて色の近い上位 ``topk``
    区画を選び、それぞれの周り 3 × 3 区画だけ全ビンを比べる(粗 → 細)。``"exact"``: 全ビンの総当たり(基準)。
    色 → 法線は多峰(離れたビンがほぼ同じ色を持つ)なので、粗 → 細は総当たりと**同じビンを選ぶとは限らない**: 実機の 1 台目で
    一致は約 9 割、外れた画素も角誤差の中央値はほぼ同じ(門で測る)。
    ``mask`` の外は (0, 0, 1)。``min_count`` は使うビンの行数の下限: ノイズの無い合成なら 1 でよいが、実機では 1 行だけのビン
    (1 台目の較正 24 枚で 624 個)の色の平均がノイズそのもので、1 のままだと復元した深さが +18 % 偏る(行 10 以上で +6 %)。
    逆に位置の項を当てたビンだけ(``min_count=min_rows_poly``)で引くと傾き 0〜15° が不感帯になる。
    **Raises** ``ValueError``: 形 / mask の形 / method の綴り / coarse・topk・chunk が 1 未満 / 使えるビンが 0 /
    位置依存版で画像の大きさが違う。"""
    img = np.asarray(rgb, np.float64)
    if img.ndim != 3 or img.shape[2] != 3:
        raise ValueError("gradient_lut_invert: rgb must be (H, W, 3)")
    if method not in ("coarse", "exact"):
        raise ValueError("gradient_lut_invert: method must be 'coarse' or 'exact', got %r" % (method,))
    if int(coarse) < 1 or int(topk) < 1 or int(chunk) < 1:
        raise ValueError("gradient_lut_invert: coarse, topk and chunk must be >= 1")
    if not isinstance(table, dict) or not {"bins", "count", "mean_rgb", "centre_normals"} <= set(table):
        raise ValueError("gradient_lut_invert: table must come from gradient_lut_build or poly_lut_invert")
    H, W = img.shape[:2]
    m = np.ones((H, W), bool) if mask is None else np.asarray(mask, bool)
    if m.shape != (H, W):
        raise ValueError("gradient_lut_invert: mask must be (H, W)")
    valid = _valid_bins(table, min_count)
    if not valid.any():
        raise ValueError("gradient_lut_invert: no bins with count >= %d" % int(min_count))
    out = np.zeros((H, W, 3))
    out[..., 2] = 1.0
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        return out
    A = None
    if table.get("coef") is not None:
        if table["basis"] == "unit" and tuple(table["image_shape"]) != (H, W):
            raise ValueError("gradient_lut_invert: positional table was made for %s, got %s" % (table["image_shape"], (H, W)))
        A = _pos_basis(ys, xs, table["basis"], table["image_shape"])
    best = _lut_search(img[ys, xs], A, table, valid, method, coarse, int(chunk), int(topk))
    out[ys, xs] = np.asarray(table["centre_normals"], np.float64).reshape(-1, 3)[best]
    return out


def poly_lut_invert(rgb, poly: dict, mask=None, method: str = "coarse") -> np.ndarray:
    """アダプタ: 外部の**位置依存**多項式 LUT(``bins`` と ``grad_r`` / ``grad_g`` / ``grad_b`` = (bins, bins, 6)、ビンごとに
    6 係数 [x², y², xy, x, y, 1]・x = 列・y = 行を**画素のまま**で背景差分の各チャネルを表す書式)を、
    :func:`gradient_lut_invert` と同じ逆引き(同じビン割り・同じ粗 → 細)に通す。``rgb`` は外部の手順と同じ背景処理をした差分。
    外部の表は全ビンが埋まっているので全ビンを使う。
    **Raises** ``ValueError``: キー欠落 / 係数の形が (bins, bins, 6) でない / 非有限。"""
    if not hasattr(poly, "__getitem__"):
        raise ValueError("poly_lut_invert: poly must be a mapping")
    try:
        bins = int(np.asarray(poly["bins"]))
        g = [np.asarray(poly[k], np.float64) for k in ("grad_r", "grad_g", "grad_b")]
    except KeyError as exc:
        raise ValueError("poly_lut_invert: missing key %s" % exc) from exc
    if bins < 4 or any(x.shape != (bins, bins, 6) for x in g):
        raise ValueError("poly_lut_invert: coefficient tables must be (bins, bins, 6)")
    if not all(np.all(np.isfinite(x)) for x in g):
        raise ValueError("poly_lut_invert: non-finite coefficients")
    table = {"bins": bins, "coef": np.stack(g, axis=-1), "basis": "pixel", "image_shape": None,
             "count": np.ones((bins, bins)), "mean_rgb": np.stack([x[..., 5] for x in g], axis=-1),
             "centre_normals": _bin_centre_normals(bins)}
    return gradient_lut_invert(rgb, table, mask, min_count=1, method=method)


# ----------------------------------------------------------------------------------------------------------------------
# 評価
def normal_error_map(n_a, n_b) -> np.ndarray:
    """2 つの法線場の画素ごとの角度 [度] = atan2(|a × b|, a · b)(正規化しない —— 長さは atan2 の比で消える)。
    acos(a · b) は単位ベクトルの近くで丸めの床を持つ(1e-7° を 1e-4° と答える)ので使わない。
    **Raises** ``ValueError``: 形が違う / 最後の軸が 3 でない。"""
    a = np.asarray(n_a, np.float64)
    b = np.asarray(n_b, np.float64)
    if a.shape != b.shape or a.ndim < 1 or a.shape[-1] != 3:
        raise ValueError("normal_error_map: shapes must agree and end in 3")
    cr = np.linalg.norm(np.cross(a, b), axis=-1)
    dt = np.sum(a * b, axis=-1)
    return np.degrees(np.arctan2(cr, dt))


def sphere_cap_height(shape, centre, a_px: float, R_px: float, pitch: float) -> dict:
    """幾何学的な押し込み(弾性の裾なし)の真の高さ: 接触円の内側 h(r) = −(√(R² − r²) − √(R² − a²))、外側 0(a は min(a, R))。

    返り: ``h`` (H, W) [m]、``delta``(中心の深さ [m] = R − √(R² − a²))、``shape_rel``(h(r) − h(0) = R − √(R² − r²) [m]、a に
    依らない形、外側は nan)、``r`` [px]。``pitch`` [m/px]。
    **Raises** ``ValueError``: shape・centre の形、a・R・pitch ≤ 0。"""
    H, W = _shape2(shape, "sphere_cap_height")
    cy, cx = _point2(centre, "sphere_cap_height")
    R, a, p = float(R_px), float(a_px), float(pitch)
    if not (math.isfinite(R) and math.isfinite(a) and math.isfinite(p) and R > 0 and a > 0 and p > 0):
        raise ValueError("sphere_cap_height: a_px, R_px and pitch must be finite and > 0")
    a = min(a, R)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    r = np.hypot(yy - cy, xx - cx)
    s = np.sqrt(np.maximum(R * R - r * r, 0.0))
    sa = math.sqrt(max(R * R - a * a, 0.0))
    inside = r < a
    return {"h": np.where(inside, -(s - sa), 0.0) * p, "delta": (R - sa) * p, "shape_rel": np.where(inside, R - s, np.nan) * p, "r": r}


def field_position_sweep(centres, errors, image_shape) -> dict:
    """誤差の位置依存: 各画像の接触中心 (行, 列) と誤差(中央値など)を画像中心からの距離に対して並べ、最小二乗の傾き
    [誤差 / 100 px] と Spearman の順位相関(同順位は平均順位)を返す(numpy だけ)。
    返り: ``dist_px``・``err``・``slope_per_100px``・``intercept``・``spearman``・``n``。
    **Raises** ``ValueError``: 3 組未満 / 形の不一致 / 非有限 / image_shape の形。"""
    c = np.asarray(centres, np.float64)
    e = np.asarray(errors, np.float64)
    H, W = _shape2(image_shape, "field_position_sweep")
    if c.ndim != 2 or c.shape[1] != 2 or e.shape != (c.shape[0],) or c.shape[0] < 3:
        raise ValueError("field_position_sweep: need >= 3 (centre, error) pairs")
    if not (np.all(np.isfinite(c)) and np.all(np.isfinite(e))):
        raise ValueError("field_position_sweep: non-finite input")
    d = np.hypot(c[:, 0] - (H - 1) / 2.0, c[:, 1] - (W - 1) / 2.0)
    slope, icpt = np.polyfit(d / 100.0, e, 1)

    def _rank(v):
        o = np.argsort(v, kind="mergesort")
        r = np.empty(len(v))
        r[o] = np.arange(len(v), dtype=np.float64)
        for val in np.unique(v):                       # 同順位は平均順位
            sel = v == val
            if sel.sum() > 1:
                r[sel] = r[sel].mean()
        return r

    rd, re_ = _rank(d), _rank(e)
    sd, se = rd.std(), re_.std()
    rho = float(np.mean((rd - rd.mean()) * (re_ - re_.mean())) / (sd * se)) if sd > 0 and se > 0 else 0.0
    return {"dist_px": d, "err": e, "slope_per_100px": float(slope), "intercept": float(icpt), "spearman": rho, "n": int(len(e))}
