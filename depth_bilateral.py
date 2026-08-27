# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""depth_bilateral — エッジ保存の深度/レンジ画像デノイズ(range_image / spherical_proj の後段)。

深度センサ(ToF / structured-light / spinning LiDAR)の出力は必ずノイズと**無効画素**
(no-return, 影, 反射欠損)を含む。素朴なガウス平滑はノイズを消す代わりに前景/背景の**段差
(不連続)** をぼかしてしまい、下流の法線推定・地面除去・把持点判定を壊す。bilateral filter は
**空間近接**と**深度近接**の二重重みで平滑するため、段差を跨いだ画素を自然に排除し不連続を保存する。

  out[p] = (1/Wp) Σ_q  Gs(||p-q||) · Gr(|f[p]-f[q]|) · depth[q]
  Wp     =         Σ_q  Gs(||p-q||) · Gr(|f[p]-f[q]|)

* :func:`bilateral_filter_depth` … range 重みを深度自身の差 |depth[p]-depth[q]| で作る古典 bilateral。
* :func:`joint_bilateral` … range 重みを別の**ガイド画像**(RGB 輝度・清浄なチャネル)の差で作る
  cross/joint bilateral。深度が荒くてもガイドの鮮鋭なエッジで段差を保存できる。
* :func:`fill_holes` … 無効画素(穴)を近傍の有効画素から**調和(ラプラス)緩和**で補間。
  線形場(平面)は離散調和の不動点なので平面を(反復収束で)厳密に復元する。max_radius を超える
  深い穴は補間せず無効のまま残す(fail-closed)。

差別化(honest): backends の cv_bilateral は cv2 依存の**汎用画像** bilateral。ここは numpy(+scipy)
のみで、深度特有の**無効画素の除外**(NaN/sentinel を重みから外し値を捏造しない)と**穴埋め補間**を
併せ持つ。range_image が organized 深度→法線/エッジ、spherical_proj が点群→レンジ画像を担い、本
モジュールはその**手前の前処理**(生レンジ画像のデノイズ・穴埋め)を担当する。

スケール規約: sigma は物理量そのもの。空間 sigma は画素単位、range sigma は深度(またはガイド)の
値の単位。深度を k 倍して range sigma も k 倍すれば出力も厳密に k 倍(閉形式のスケール共変性)。
コード内に絶対 epsilon の閾値は無く(無効判定は非有限 or 完全一致 sentinel のみ)、スケール依存しない。
"""
from __future__ import annotations

import numpy as np

__all__ = ["bilateral_filter_depth", "joint_bilateral", "fill_holes"]


def _valid_mask(depth: np.ndarray, invalid) -> np.ndarray:
    """有効画素マスク: 非有限(NaN/Inf)は常に無効、invalid(既定 0)に完全一致する画素も無効。

    invalid=None なら非有限のみを無効とみなす。閾値は完全一致(スケール不変)で絶対 epsilon を使わない。
    """
    d = np.asarray(depth, dtype=float)
    m = np.isfinite(d)
    if invalid is not None:
        m &= d != float(invalid)
    return m


def _check_sigmas(spatial_sigma: float, range_sigma: float) -> tuple[float, float]:
    """sigma が正の有限値かを検査して (spatial, range) を返す(縮退入力は fail-closed)。"""
    ss = float(spatial_sigma)
    sr = float(range_sigma)
    if not np.isfinite(ss) or ss <= 0.0:
        raise ValueError(f"spatial_sigma must be a positive finite number, got {spatial_sigma!r}")
    if not np.isfinite(sr) or sr <= 0.0:
        raise ValueError(f"range_sigma must be a positive finite number, got {range_sigma!r}")
    return ss, sr


def _bilateral_core(
    values: np.ndarray,
    edge: np.ndarray,
    spatial_sigma: float,
    range_sigma: float,
    val_valid: np.ndarray,
    edge_valid: np.ndarray,
    truncate: float,
) -> np.ndarray:
    """bilateral の共通核: values を平均し range 重みは edge の差で作る(無効画素は重み 0 で除外)。

    近傍が寄与する条件 = その画素で values も edge も有効。中心画素が処理される条件も同じで、
    満たさない中心画素(穴・ガイド欠損)は元値のまま残す(値を捏造しない = fail-closed)。
    """
    values = np.asarray(values, dtype=float)
    edge = np.asarray(edge, dtype=float)
    H, W = values.shape
    contrib = val_valid & edge_valid  # 近傍として使える画素

    # 無効画素は有限のプレースホルダに置換(重み 0 で寄与しないが NaN 伝播を防ぐため)。
    v_safe = np.where(val_valid, values, 0.0)
    e_safe = np.where(edge_valid, edge, 0.0)

    radius = max(int(np.ceil(float(truncate) * spatial_sigma)), 1)
    # reflect パディング(scipy.ndimage 既定と同じ境界規約)。
    vp = np.pad(v_safe, radius, mode="reflect")
    ep = np.pad(e_safe, radius, mode="reflect")
    cp = np.pad(contrib.astype(float), radius, mode="reflect")

    inv2s2 = 1.0 / (2.0 * spatial_sigma * spatial_sigma)
    inv2r2 = 1.0 / (2.0 * range_sigma * range_sigma)

    num = np.zeros((H, W), dtype=float)
    den = np.zeros((H, W), dtype=float)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            ws = np.exp(-(dy * dy + dx * dx) * inv2s2)  # 空間重み(スカラ)
            vs = vp[radius + dy : radius + dy + H, radius + dx : radius + dx + W]
            es = ep[radius + dy : radius + dy + H, radius + dx : radius + dx + W]
            cs = cp[radius + dy : radius + dy + H, radius + dx : radius + dx + W]
            de = es - e_safe
            wr = np.exp(-(de * de) * inv2r2)  # range(深度/ガイド)重み
            w = ws * wr * cs
            num += w * vs
            den += w

    center_ok = contrib
    out = np.array(values, dtype=float, copy=True)
    # 中心が有効なら den には自分自身(ws=wr=1)が必ず入るので den>0。
    good = center_ok & (den > 0.0)
    out[good] = num[good] / den[good]
    return out


def bilateral_filter_depth(
    depth: np.ndarray,
    spatial_sigma: float,
    range_sigma: float,
    *,
    invalid: float | None = 0.0,
    truncate: float = 3.0,
) -> np.ndarray:
    """深度画像の bilateral filter(段差保存デノイズ)。→ float64 (H,W)。

    range 重みは深度自身の差で作る。無効画素(非有限 or sentinel=invalid)は近傍として寄与せず、
    中心が無効なら元値のまま(穴埋めは :func:`fill_holes` の役目)。spatial_sigma は画素単位、
    range_sigma は深度値の単位(段差 > range_sigma なら段差を跨がず、ノイズ std < range_sigma
    ならノイズを平滑する)。truncate=3 でガウス窓半径 = ceil(3*spatial_sigma)。
    """
    d = np.asarray(depth, dtype=float)
    if d.ndim != 2:
        raise ValueError(f"bilateral_filter_depth expects a 2D depth image, got shape {d.shape}")
    ss, sr = _check_sigmas(spatial_sigma, range_sigma)
    valid = _valid_mask(d, invalid)
    return _bilateral_core(d, d, ss, sr, valid, valid, truncate)


def joint_bilateral(
    depth: np.ndarray,
    guide: np.ndarray,
    spatial_sigma: float,
    range_sigma: float,
    *,
    invalid: float | None = 0.0,
    truncate: float = 3.0,
) -> np.ndarray:
    """joint / cross bilateral: 平滑対象は depth、range 重みは guide の差で作る。→ float64 (H,W)。

    深度が荒くても清浄な guide(RGB 輝度・別センサ)の鮮鋭なエッジで段差を保存できる。range_sigma は
    **guide 値の単位**。guide が非有限の画素、および depth が無効な画素は寄与しない。guide と depth は
    同一形状必須(fail-closed)。
    """
    d = np.asarray(depth, dtype=float)
    g = np.asarray(guide, dtype=float)
    if d.ndim != 2:
        raise ValueError(f"joint_bilateral expects a 2D depth image, got shape {d.shape}")
    if g.shape != d.shape:
        raise ValueError(f"guide shape {g.shape} must match depth shape {d.shape}")
    ss, sr = _check_sigmas(spatial_sigma, range_sigma)
    valid = _valid_mask(d, invalid)
    gvalid = np.isfinite(g)
    return _bilateral_core(d, g, ss, sr, valid, gvalid, truncate)


def fill_holes(
    depth: np.ndarray,
    max_radius: float,
    *,
    invalid: float | None = 0.0,
    max_iter: int | None = None,
    rel_tol: float = 1e-6,
) -> np.ndarray:
    """無効画素(穴)を近傍有効画素から調和(ラプラス)緩和で補間。→ float64 (H,W)。

    各穴画素の最寄り有効画素までの距離が max_radius 以下なら補間対象、超える深い穴は補間せず NaN で残す
    (fail-closed)。補間は 4 近傍平均の反復(Dirichlet 境界=元の有効画素)で、線形場(平面)は離散
    調和関数の不動点なので反復収束とともに平面を厳密復元する。初期値は最寄り有効画素値(EDT)。

    max_iter 既定は穴サイズに応じて自動設定、rel_tol は深度スケール相対の収束判定。全画素無効の入力は
    補間の足場が無いため ValueError(fail-closed)。
    """
    from scipy import ndimage

    d = np.asarray(depth, dtype=float)
    if d.ndim != 2:
        raise ValueError(f"fill_holes expects a 2D depth image, got shape {d.shape}")
    r = float(max_radius)
    if not np.isfinite(r) or r <= 0.0:
        raise ValueError(f"max_radius must be a positive finite number, got {max_radius!r}")

    valid = _valid_mask(d, invalid)
    out = np.array(d, dtype=float, copy=True)
    if valid.all():
        return out  # 穴なし
    if not valid.any():
        raise ValueError("fill_holes: no valid pixels to interpolate from (fully invalid input)")

    holes = ~valid
    # 各穴画素→最寄り有効画素の距離と、その有効画素のインデックス(初期値用)。
    dist, (iy, ix) = ndimage.distance_transform_edt(holes, return_indices=True)
    fillable = holes & (dist <= r)

    # 穴を一旦有限化(非有効=sentinel/NaN を 0 に)し、補間対象は最寄り有効値で初期化。
    out[holes] = 0.0
    if fillable.any():
        out[fillable] = d[iy[fillable], ix[fillable]]

        # スケール相対の収束閾値。
        scale = float(np.median(np.abs(d[valid])))
        if not np.isfinite(scale) or scale == 0.0:
            scale = 1.0
        tol = rel_tol * scale

        # 4 近傍のうち「値を持つ画素(有効 or 補間対象)」だけで平均。
        part = valid | fillable
        if max_iter is None:
            # 半径 r の穴の Jacobi 収束は O(r^2) 反復で足りる(小穴なら十分収束)。
            max_iter = int(min(4000, max(64, np.ceil(8.0 * (r + 1.0) ** 2))))

        for _ in range(max_iter):
            vp = np.pad(out, 1, mode="edge")
            pp = np.pad(part.astype(float), 1, mode="constant")
            nsum = (
                vp[:-2, 1:-1] * pp[:-2, 1:-1]
                + vp[2:, 1:-1] * pp[2:, 1:-1]
                + vp[1:-1, :-2] * pp[1:-1, :-2]
                + vp[1:-1, 2:] * pp[1:-1, 2:]
            )
            ncnt = pp[:-2, 1:-1] + pp[2:, 1:-1] + pp[1:-1, :-2] + pp[1:-1, 2:]
            new = np.where(ncnt > 0.0, nsum / np.where(ncnt > 0.0, ncnt, 1.0), out)
            delta = np.max(np.abs(new[fillable] - out[fillable])) if fillable.any() else 0.0
            out[fillable] = new[fillable]
            if delta < tol:
                break

    # max_radius を超える深い穴は補間せず無効(NaN)で残す(fail-closed)。
    out[holes & ~fillable] = np.nan
    return out
