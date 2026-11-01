# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""画像を先に正規化し、画像ごとに意味が変わらない単位でしきい値を決める。"""
from __future__ import annotations

import numpy as np


_POLARITIES = ("bright", "dark")
_SIGMA_POLARITIES = ("bright", "dark", "both")
_STANDARDIZE_METHODS = ("zscore", "robust", "percentile")


def _finite_image(image, op: str) -> np.ndarray:
    """Return one non-empty finite 2-D floating image or fail closed."""
    x = np.asarray(image, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError(f"{op}: image must be a 2-D array")
    if x.size == 0:
        raise ValueError(f"{op}: empty input has no intensity distribution")
    if not np.isfinite(x).all():
        raise ValueError(f"{op}: image must contain only finite values")
    return x


def ptile_threshold(image, p: float = 0.01, polarity: str = "bright") -> float:
    """P-tile 法で面積率 *p* を明または暗側に置くグレー値しきい値を返す。

    Doyle (1962) の P-tile 法に従い、画素を明るさ順に並べ、指定した側の
    ``ceil(p * N)`` 画素と残りの境界をしきい値にする。隣接する 2 値の中点を
    返すため、値が異なる境界では ``image > threshold`` (``bright``)または
    ``image < threshold`` (``dark``)が指定個数をそのまま選ぶ。同値画素が境界を
    またぐ離散ヒストグラムでは面積率を厳密に分けられないため、その同値を
    しきい値として返す。画素を恣意的に間引いて割合だけを合わせることはしない。

    Parameters
    ----------
    image : array-like
        有限値だけからなる空でない 2-D 画像。値域は限定しない。
    p : float
        前景にしたい面積率。``0 < p < 1``。``p=0`` / ``p=1`` は境界の両側が
        存在せず、有限なしきい値を定義できないため ``ValueError`` で拒否する。
    polarity : {'bright', 'dark'}
        ``bright`` は明るい側、``dark`` は暗い側を面積率 *p* にする。

    Returns
    -------
    float
        元画像と同じグレー値単位のしきい値。

    **空入力は分布を持たないため拒否し、しきい値を捏造しない。**

    References
    ----------
    W. Doyle, "Operations Useful for Similarity-Invariant Pattern Recognition,"
    *Journal of the ACM*, 9(2), 1962, pp. 259-267.
    """
    x = _finite_image(image, "ptile_threshold")
    if not np.isfinite(p) or not 0.0 < float(p) < 1.0:
        raise ValueError("ptile_threshold: p must satisfy 0 < p < 1")
    if polarity not in _POLARITIES:
        raise ValueError("ptile_threshold: polarity must be 'bright' or 'dark'")
    values = np.sort(x, axis=None)
    # ceil(p*N) can equal N even though p < 1 (for example p=.999 on a 4x4
    # image).  A split outside the last histogram bin has no second endpoint.
    # Keep both sides non-empty; a singleton has no boundary and its sole grey
    # value is the only finite threshold consistent with a constant histogram.
    if values.size == 1:
        return float(values[0])
    count = min(values.size - 1, max(1, int(np.ceil(float(p) * values.size))))
    split = values.size - count if polarity == "bright" else count
    lower, upper = float(values[split - 1]), float(values[split])
    return lower + 0.5 * (upper - lower)


def image_standardize_raw(image, method: str = "zscore", p_lo: float = 1.0,
                          p_hi: float = 99.0) -> np.ndarray:
    """画像全体を z-score・頑健 MAD・百分位のいずれかで零中心に標準化する。

    ``zscore`` は ``(x - mean) / population_std``。``robust`` は
    ``(x - median) / (1.4826 * MAD)`` で、正規分布の標準偏差と尺度を合わせる。
    ``percentile`` は *p_lo* / *p_hi* 分位点の中点を 0、両者を -1 / +1 に写す。
    出力は常に ``float64`` の生の尺度単位であり、入力のクリップはしない。この関数は
    σ単位を必要とする数値処理向けで、``image`` sort の ``[0,1]`` 契約には登録しない。

    Parameters
    ----------
    image : array-like
        有限値だけからなる空でない 2-D 画像。値域は限定しない。
    method : {'zscore', 'robust', 'percentile'}
        ``robust`` は外れ値が平均と標準偏差を動かす場合、``percentile`` は装置ごとの
        利得とオフセットを指定分位点で揃えたい場合に使う。
    p_lo, p_hi : float
        ``percentile`` の百分位。``0 <= p_lo < p_hi <= 100``。ほかの方式では未使用。

    Returns
    -------
    numpy.ndarray
        零中心の ``float64`` 画像。z-score は平均 0・母分散 1、robust は中央値 0・
        補正 MAD 1、percentile は指定分位点の中点 0。

    **空入力は尺度を推定できないため拒否する。定数入力は全 0 を返す（理由: 偏差が
    なく、0 除算を避けながら零中心という意味を保つ唯一の有限な退化値だから）。**

    References
    ----------
    F. R. Hampel, "The Influence Curve and Its Role in Robust Estimation,"
    *Journal of the American Statistical Association*, 69(346), 1974.
    P. J. Rousseeuw and C. Croux, "Alternatives to the Median Absolute
    Deviation," *Journal of the American Statistical Association*, 88(424), 1993.
    """
    x = _finite_image(image, "image_standardize_raw")
    if method not in _STANDARDIZE_METHODS:
        raise ValueError("image_standardize_raw: method must be 'zscore', 'robust', or 'percentile'")
    if method == "zscore":
        center = float(np.mean(x))
        scale = float(np.std(x))
    elif method == "robust":
        center = float(np.median(x))
        scale = 1.4826 * float(np.median(np.abs(x - center)))
    else:
        if (not np.isfinite(p_lo) or not np.isfinite(p_hi)
                or not 0.0 <= float(p_lo) < float(p_hi) <= 100.0):
            raise ValueError("image_standardize_raw: percentiles must satisfy 0 <= p_lo < p_hi <= 100")
        lo, hi = np.percentile(x, [float(p_lo), float(p_hi)])
        center = float(lo + 0.5 * (hi - lo))
        scale = float(0.5 * (hi - lo))
    if not np.isfinite(scale) or scale <= 0.0:
        return np.zeros_like(x, dtype=np.float64)
    return (x - center) / scale


def image_standardize(image, method: str = "zscore", p_lo: float = 1.0,
                      p_hi: float = 99.0, clip_sigma: float = 3.0) -> np.ndarray:
    """画像を標準化し、± ``clip_sigma`` の尺度を ``[0,1]`` へ写す。

    :func:`image_standardize_raw` の零中心の結果を ``[-clip_sigma,
    +clip_sigma]`` でクリップし、0 を 0.5 とする強度画像へ線形変換する。標準化は本来
    σ単位の実数を返すが、Fullseye の ``image`` sort は ``[0,1]`` が契約なので既定の
    公開 op はこの符号付き強度表現を使う。生の σ 単位が必要なら、非 image-sort の
    :func:`image_standardize_raw` を使う。

    Parameters
    ----------
    image, method, p_lo, p_hi
        :func:`image_standardize_raw` と同じ。
    clip_sigma : float
        ``[0,1]`` の両端へ写す正の有限な尺度幅。既定の 3 は -3σ / +3σ を 0 / 1
        に対応させる。

    Returns
    -------
    numpy.ndarray
        ``[0,1]`` 内の ``float64`` 画像。

    **空入力は尺度を推定できないため拒否する。定数入力は全 0.5 を返す（理由: raw
    標準化の偏差 0 を、符号付き強度表現の中立点へ写すため）。**
    """
    if not np.isfinite(clip_sigma) or float(clip_sigma) <= 0.0:
        raise ValueError("image_standardize: clip_sigma must be a positive finite number")
    raw = image_standardize_raw(image, method=method, p_lo=p_lo, p_hi=p_hi)
    width = float(clip_sigma)
    return np.clip(0.5 + raw / (2.0 * width), 0.0, 1.0)


def sigma_threshold(image, k: float = 3.0, polarity: str = "bright",
                    standardization: str = "none") -> np.ndarray:
    """標準化画像を *k* σで二値化し、必要なら先に頑健標準化する。

    ``bright`` は ``x > k``、``dark`` は ``x < -k``、``both`` は
    ``abs(x) > k``。*k* は生の輝度ではなく標準偏差単位なので、利得・オフセットが
    異なる画像へ同じ値を移せる。生画像から直接使う場合は
    ``standardization='robust'`` を選ぶと、中央値と ``1.4826 * MAD`` で先に標準化する。

    Parameters
    ----------
    image : array-like
        有限値だけからなる空でない 2-D 画像。``standardization='none'`` では既に零中心・
        σ単位であることを呼び出し側が保証する。
    k : float
        正の有限値。検査で試す典型的な起点は 2〜5 σだが、用途に応じて範囲外も許す。
    polarity : {'bright', 'dark', 'both'}
        明欠陥、暗欠陥、または両側の外れを選ぶ。
    standardization : {'none', 'robust'}
        ``robust`` は :func:`image_standardize` の MAD 方式を内部で適用する。

    Returns
    -------
    numpy.ndarray
        条件を満たす画素が ``True`` の 2-D マスク。

    **空入力は σ単位を検査できないため拒否し、空マスクへ黙って落とさない。**

    Notes
    -----
    標準正規雑音の片側誤検出率は ``0.5 * erfc(k / sqrt(2))``、両側は
    ``erfc(k / sqrt(2))``。これは独立画素を仮定した期待値である。
    """
    x = _finite_image(image, "sigma_threshold")
    if not np.isfinite(k) or float(k) <= 0.0:
        raise ValueError("sigma_threshold: k must be a positive finite number")
    if polarity not in _SIGMA_POLARITIES:
        raise ValueError("sigma_threshold: polarity must be 'bright', 'dark', or 'both'")
    if standardization not in ("none", "robust"):
        raise ValueError("sigma_threshold: standardization must be 'none' or 'robust'")
    if standardization == "robust":
        x = image_standardize_raw(x, method="robust")
    if polarity == "bright":
        return x > float(k)
    if polarity == "dark":
        return x < -float(k)
    return np.abs(x) > float(k)


__all__ = ["ptile_threshold", "image_standardize", "image_standardize_raw", "sigma_threshold"]
