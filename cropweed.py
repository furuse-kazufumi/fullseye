# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""作物と雑草を色と肌理で分ける: 可視 3 バンドの植物の色指標(ExG・ExR・ExGR・CIVE・NGRDI・VEG)、
超画素ごとの色と肌理の特徴、2 クラスの Fisher 判別(学習と採点)、被度の割合を宣言済みの境で段階に分ける判定。

## 何を作るか

圃場の RGB 画像から「作物の画素」と「雑草の画素」を分け、雑草の程度を段階で答える —— 毎年の外観検査の
アルゴリズムコンテストの 2026 年の課題(水田の水稲と雑草の割合を 4 段階で判定)と同じ型の問いを、
**学習器を載せずに**(numpy + scipy のルールベースと線形判別)組むための汎用 op。

1. ``plant_color_index`` —— 色度座標 r = R/(R+G+B) ほかで、文献の 6 つの指標を 1 つの口で返す。
   ExG = 2g − r − b(Woebbecke ら 1995)、ExR = 1.4r − g(Meyer ら 1998)、ExGR = ExG − ExR
   (Meyer と Camargo Neto 2008。**0 が植物と背景の境**という閾値の要らない指標)、
   CIVE = 0.441r − 0.811g + 0.385b + 18.78745(Kataoka ら 2003。色度座標に掛ける流儀 —— Guijarro ら 2011 —— に
   従う。**小さいほど植物**なので符号 ``vegetation_sign = -1`` を返す)、NGRDI = (G − R)/(G + R)(Tucker 1979)、
   VEG = g / (r^a b^(1−a))、a = 0.667(Hague ら 2006)。式の一覧は Hamuda ら 2016 の総説の表と照合した。
   ★暗い画素(R+G+B がほぼ 0)は色度が雑音だけで決まる —— **値を作らず NaN にして ``valid`` で印を付ける**。
   全画素が暗ければ拒否する。
2. ``superpixel_color_texture_features`` —— ラベル画像(超画素・格子・何でも)の各領域について 10 個の特徴
   (色指標 3 つの平均・色度 r と g の平均・明るさの平均と標準偏差・勾配の大きさの平均・構造テンソルの
   **向きの揃い**(coherence)・ExG の標準偏差)を (N, 10) の行列で返す。稲の葉は細長く向きが揃い、広葉の
   雑草や塊で生える雑草は揃わない —— この差を色と別の軸で拾うのが coherence。
3. ``fisher_lda_fit`` / ``fisher_lda_score`` —— 2 クラスの Fisher 線形判別。特徴を標準化し、
   w = Σ⁻¹(μ₁ − μ₀)(Σ はクラス内の共通共分散)、判定は w·z − c > 0、c は 2 つの正規分布の対数尤度比が 0 になる
   点(事前確率込み)。**閉形式**なので、門は (a) 等分散の 1 次元で境界が (μ₀ + μ₁)/2 に一致、(b) クラスを
   入れ替えると符号だけが反転、(c) 特徴をアフィン変換しても判定が変わらない。
4. ``cover_ratio_grade`` —— 被度(0..1)を **宣言した境** で段階 0..K に分ける。既定の境 (0.05, 0.25, 0.50) は
   植生調査の被度階級(Braun-Blanquet の 5 % / 25 % / 50 %)から借りた —— **注釈から決めない**。
   境からの距離(``margin``)も返すので、境の近くの判定がどれだけ脆いかが見える。

## 黙って間違わない(fail-closed)

空の入力・非有限値・[0, 1] の外・形の食い違い・クラスが 2 つでない・クラス内の共分散が退化して判別の向きが
決まらない・2 クラスの平均が同じ(どの向きにも分かれない)・境が単調増加でない —— どれも値を返さず
``ValueError`` で拒否する。
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Sequence

import numpy as np
from scipy import ndimage

#: 1 枚の画像の画素数の上限(他の 2-D 族と同じ桁)。
MAX_PIXELS = 50_000_000

#: ``plant_color_index`` の指標名 → (式, 植物で大きいなら +1 / 小さいなら -1, 出典)。
INDICES = {
    "exg": ("2g - r - b (chromatic coordinates)", 1, "Woebbecke et al. 1995, Trans. ASAE 38(1)"),
    "exr": ("1.4r - g (chromatic coordinates)", -1, "Meyer et al. 1998, Proc. SPIE 3543"),
    "exgr": ("ExG - ExR; 0 separates plant from background", 1,
             "Meyer and Camargo Neto 2008, Comput. Electron. Agric. 63"),
    "cive": ("0.441r - 0.811g + 0.385b + 18.78745 (chromatic coordinates)", -1,
             "Kataoka et al. 2003, Proc. IEEE/ASME AIM"),
    "ngrdi": ("(G - R) / (G + R)", 1, "Tucker 1979, Remote Sens. Environ. 8"),
    "veg": ("g / (r^0.667 b^0.333)", 1, "Hague et al. 2006, Precision Agric. 7"),
}

#: ``superpixel_color_texture_features`` の列名(この順)。
FEATURE_NAMES = ("exg_mean", "exgr_mean", "cive_mean", "chroma_r_mean", "chroma_g_mean",
                 "brightness_mean", "brightness_std", "gradient_mean", "orientation_coherence",
                 "exg_std")

#: 被度の段階の既定の境(Braun-Blanquet の被度階級 5 % / 25 % / 50 % から借りた)。
DEFAULT_GRADE_EDGES = (0.05, 0.25, 0.50)


# --------------------------------------------------------------------------- #
# 入力の検査                                                                    #
# --------------------------------------------------------------------------- #
def _num(v, name: str, op: str, lo: float = -math.inf, hi: float = math.inf,
         lo_open: bool = False) -> float:
    if isinstance(v, bool):
        raise ValueError("%s: %s must be a number (got bool)" % (op, name))
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number (got %r)" % (op, name, v)) from None
    if not math.isfinite(f) or f < lo or f > hi or (lo_open and f == lo):
        raise ValueError("%s: %s must be finite and in %s%g, %g] (got %r)"
                         % (op, name, "(" if lo_open else "[", lo, hi, v))
    return f


def _rgb(x, op: str) -> np.ndarray:
    """(H, W, 3) の RGB を [0, 1] の float64 に揃える。uint8 は 255 で割る。範囲の外は拒否。"""
    if isinstance(x, (str, bytes, dict)) or x is None:
        raise ValueError("%s: rgb must be an (H, W, 3) array" % op)
    a = np.asarray(x)
    if a.size == 0:
        raise ValueError("%s: rgb is empty" % op)
    if a.dtype.kind not in "biuf":
        raise ValueError("%s: rgb has dtype %s — must be real" % (op, a.dtype))
    if a.ndim != 3 or a.shape[2] != 3:
        raise ValueError("%s: rgb must have shape (H, W, 3), got %r" % (op, a.shape))
    if a.shape[0] * a.shape[1] > MAX_PIXELS:
        raise ValueError("%s: rgb has %d pixels > MAX_PIXELS=%d"
                         % (op, a.shape[0] * a.shape[1], MAX_PIXELS))
    if a.dtype == np.uint8:
        return a.astype(np.float64) / 255.0
    f = a.astype(np.float64)
    if not np.isfinite(f).all():
        raise ValueError("%s: rgb has non-finite values" % op)
    if f.min() < 0.0 or f.max() > 1.0:
        raise ValueError("%s: float rgb must lie in [0, 1] (got [%g, %g]); pass uint8 or rescale"
                         % (op, f.min(), f.max()))
    return f


def _index_maps(rgb: np.ndarray, dark_floor: float):
    """色度座標 r, g, b と、色度が決まる画素の印 ``valid``(明るさ = RGB の平均 >= dark_floor)。"""
    s = rgb.sum(axis=2)
    valid = (s / 3.0) >= dark_floor
    safe = np.where(valid, s, 1.0)
    r = np.where(valid, rgb[..., 0] / safe, np.nan)
    g = np.where(valid, rgb[..., 1] / safe, np.nan)
    b = np.where(valid, rgb[..., 2] / safe, np.nan)
    return r, g, b, valid


def _formula(name: str, rgb: np.ndarray, r, g, b, valid):
    """指標 1 つを計算する。式が定義されない画素は NaN にし、``valid`` から外す。"""
    if name == "exg":
        v = 2.0 * g - r - b
    elif name == "exr":
        v = 1.4 * r - g
    elif name == "exgr":
        v = (2.0 * g - r - b) - (1.4 * r - g)
    elif name == "cive":
        v = 0.441 * r - 0.811 * g + 0.385 * b + 18.78745
    elif name == "ngrdi":
        den = rgb[..., 1] + rgb[..., 0]
        ok = valid & (den > 0.0)
        v = np.where(ok, (rgb[..., 1] - rgb[..., 0]) / np.where(ok, den, 1.0), np.nan)
        return v, ok
    elif name == "veg":
        ok = valid & (np.nan_to_num(r) > 0.0) & (np.nan_to_num(b) > 0.0)
        rr = np.where(ok, r, 1.0)
        bb = np.where(ok, b, 1.0)
        v = np.where(ok, g / (rr ** 0.667 * bb ** 0.333), np.nan)
        return v, ok
    else:                                                  # pragma: no cover - 呼び出し側で検査済み
        raise ValueError(name)
    return np.where(valid, v, np.nan), valid


# --------------------------------------------------------------------------- #
# 1. 植物の色指標                                                               #
# --------------------------------------------------------------------------- #
def plant_color_index(rgb, *, index: str = "exg", dark_floor: float = 0.02) -> Dict[str, object]:
    """可視 3 バンドの植物の色指標(ExG・ExR・ExGR・CIVE・NGRDI・VEG)を画素ごとに計算する。

    ``rgb`` は (H, W, 3)。uint8 は 255 で割り、float は [0, 1] でなければ拒否する。``index`` は
    ``exg`` / ``exr`` / ``exgr`` / ``cive`` / ``ngrdi`` / ``veg``。ExG・ExR・ExGR・CIVE・VEG は色度座標
    r = R/(R+G+B)・g・b に掛け、NGRDI だけは生の (G − R)/(G + R)。
    明るさ(RGB の平均)が ``dark_floor`` 未満の画素は色度が雑音で決まるので **値を作らず NaN** にし、
    ``valid`` を False にする(VEG は r か b が 0、NGRDI は G + R が 0 の画素も外す)。
    返す: ``index``(H, W の float、NaN は未定義)・``valid``(bool)・``name``・``formula``・
    ``vegetation_sign``(植物で大きくなる指標は +1、CIVE と ExR は −1)・``citation``・``n_invalid``・
    ``threshold_zero_is_boundary``(ExGR だけ True: 0 が植物と背景の境)。
    空の入力・非有限値・範囲の外・未知の指標名・全画素が未定義のときは ``ValueError`` で拒否する。

    呼び出し例: ``fs.ledger.plant_color_index(img, index="exgr")["index"] > 0`` で植物の画素。
    """
    op = "plant_color_index"
    a = _rgb(rgb, op)
    if not isinstance(index, str) or index.lower() not in INDICES:
        raise ValueError("%s: index must be one of %s (got %r)" % (op, sorted(INDICES), index))
    name = index.lower()
    floor = _num(dark_floor, "dark_floor", op, 0.0, 1.0)
    r, g, b, valid = _index_maps(a, floor)
    v, ok = _formula(name, a, r, g, b, valid)
    n_ok = int(np.count_nonzero(ok))
    if n_ok == 0:
        raise ValueError("%s: no pixel is bright enough to define chromaticity (dark_floor=%g); "
                         "the index is undefined everywhere" % (op, floor))
    formula, sign, cite = INDICES[name]
    return {"index": v, "valid": ok, "name": name, "formula": formula,
            "vegetation_sign": sign, "citation": cite, "n_invalid": int(ok.size - n_ok),
            "threshold_zero_is_boundary": name == "exgr", "dark_floor": floor}


# --------------------------------------------------------------------------- #
# 2. 超画素ごとの色と肌理                                                       #
# --------------------------------------------------------------------------- #
def _labels(lab, shape, op: str) -> np.ndarray:
    a = np.asarray(lab)
    if a.size == 0:
        raise ValueError("%s: labels is empty" % op)
    if a.dtype.kind not in "biu":
        if a.dtype.kind == "f" and np.isfinite(a).all() and np.all(a == np.round(a)):
            a = a.astype(np.int64)
        else:
            raise ValueError("%s: labels must be integer, got dtype %s" % (op, a.dtype))
    if a.shape != tuple(shape):
        raise ValueError("%s: labels shape %r != image shape %r" % (op, a.shape, tuple(shape)))
    a = a.astype(np.int64)
    if a.min() < 0:
        raise ValueError("%s: labels must be >= 0 (0 = ignore)" % op)
    return a


def superpixel_color_texture_features(rgb, labels, *, dark_floor: float = 0.02,
                                      texture_sigma: float = 1.0,
                                      min_size: int = 4) -> Dict[str, object]:
    """ラベル画像の領域ごとに、色(植物の色指標・色度)と肌理(勾配・向きの揃い)の特徴 10 個を出す。

    ``rgb`` は (H, W, 3)(``plant_color_index`` と同じ約束)、``labels`` は同じ大きさの整数画像
    (0 は無視、1 以上が領域。超画素でも格子でもよい)。列は ``FEATURE_NAMES`` の順:
    ExG・ExGR・CIVE の平均、色度 r・g の平均、明るさ(RGB の平均)の平均と標準偏差、
    明るさの Gauss 勾配(σ = ``texture_sigma``)の大きさの平均、構造テンソルの向きの揃い
    coherence = √((Jxx − Jyy)² + 4Jxy²)/(Jxx + Jyy)(領域で和をとったテンソル。1 = 一方向、0 = 等方)、
    ExG の標準偏差。色の特徴は ``dark_floor`` 以上の明るさの画素だけで平均する。
    画素数が ``min_size`` 未満の領域と、色度の決まる画素が 1 つも無い領域は **行を作らず**
    ``dropped_ids`` に理由つきで残す(平均を 0 や NaN で埋めない)。
    返す: ``X``(N, 10)・``names``・``ids``(行ごとの領域番号)・``sizes``・``centroids``((N, 2) の [row, col])・
    ``dropped_ids``・``texture_sigma``。
    空の入力・形の食い違い・負のラベル・残る領域が 0 のときは ``ValueError`` で拒否する。
    """
    op = "superpixel_color_texture_features"
    a = _rgb(rgb, op)
    lab = _labels(labels, a.shape[:2], op)
    floor = _num(dark_floor, "dark_floor", op, 0.0, 1.0)
    sig = _num(texture_sigma, "texture_sigma", op, 0.0, 50.0, lo_open=True)
    if isinstance(min_size, bool) or not isinstance(min_size, (int, np.integer)) or min_size < 1:
        raise ValueError("%s: min_size must be an integer >= 1 (got %r)" % (op, min_size))
    r, g, b, valid = _index_maps(a, floor)
    exg = 2.0 * g - r - b
    exgr = exg - (1.4 * r - g)
    cive = 0.441 * r - 0.811 * g + 0.385 * b + 18.78745
    bright = a.mean(axis=2)
    gy = ndimage.gaussian_filter(bright, sig, order=(1, 0), mode="reflect")
    gx = ndimage.gaussian_filter(bright, sig, order=(0, 1), mode="reflect")
    gmag = np.hypot(gx, gy)

    flat = lab.ravel()
    n_lab = int(flat.max()) + 1
    size = np.bincount(flat, minlength=n_lab).astype(np.float64)
    vflat = valid.ravel()
    nval = np.bincount(flat, weights=vflat.astype(np.float64), minlength=n_lab)

    def _vsum(m, power=1):
        w = np.where(vflat, np.nan_to_num(m.ravel()) ** power, 0.0)
        return np.bincount(flat, weights=w, minlength=n_lab)

    def _asum(m, power=1):
        return np.bincount(flat, weights=m.ravel() ** power, minlength=n_lab)

    ids_all = np.arange(n_lab)
    keep = (ids_all >= 1) & (size >= min_size) & (nval >= 1)
    dropped = []
    for k in ids_all[1:]:
        if size[k] == 0:
            continue
        if size[k] < min_size:
            dropped.append((int(k), "smaller than min_size"))
        elif nval[k] < 1:
            dropped.append((int(k), "no pixel bright enough for chromaticity"))
    if not keep.any():
        raise ValueError("%s: no region left (all regions smaller than min_size=%d or too dark)"
                         % (op, int(min_size)))
    ids = ids_all[keep]
    nv = nval[ids]
    na = size[ids]

    def _vmean(m):
        return _vsum(m)[ids] / nv

    def _vstd(m):
        mu = _vsum(m)[ids] / nv
        return np.sqrt(np.maximum(_vsum(m, 2)[ids] / nv - mu * mu, 0.0))

    bm = _asum(bright)[ids] / na
    bs = np.sqrt(np.maximum(_asum(bright, 2)[ids] / na - bm * bm, 0.0))
    jxx = _asum(gx * gx)[ids]
    jyy = _asum(gy * gy)[ids]
    jxy = _asum(gx * gy)[ids]
    tr = jxx + jyy
    coh = np.where(tr > 1e-300, np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy * jxy) / np.where(tr > 1e-300, tr, 1.0), 0.0)
    X = np.column_stack([_vmean(exg), _vmean(exgr), _vmean(cive), _vmean(r), _vmean(g),
                         bm, bs, _asum(gmag)[ids] / na, coh, _vstd(exg)])
    rows, cols = np.indices(lab.shape)
    cy = np.bincount(flat, weights=rows.ravel().astype(np.float64), minlength=n_lab)[ids] / na
    cx = np.bincount(flat, weights=cols.ravel().astype(np.float64), minlength=n_lab)[ids] / na
    return {"X": X, "names": list(FEATURE_NAMES), "ids": ids.astype(np.int64),
            "sizes": na.astype(np.int64), "centroids": np.column_stack([cy, cx]),
            "dropped_ids": dropped, "texture_sigma": sig, "dark_floor": floor}


# --------------------------------------------------------------------------- #
# 3. 2 クラスの Fisher 判別                                                     #
# --------------------------------------------------------------------------- #
def _matrix(X, op: str, name: str = "X") -> np.ndarray:
    if isinstance(X, dict) and "X" in X:
        X = X["X"]
    a = np.asarray(X)
    if a.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if a.dtype.kind not in "biuf":
        raise ValueError("%s: %s must be real, got dtype %s" % (op, name, a.dtype))
    a = a.astype(np.float64)
    if a.ndim == 1:
        a = a[:, None]
    if a.ndim != 2:
        raise ValueError("%s: %s must be (N, D), got shape %r" % (op, name, a.shape))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s has non-finite values" % (op, name))
    return a


def fisher_lda_fit(X, y, *, ridge: float = 1e-6, prior1: Optional[float] = None) -> Dict[str, object]:
    """2 クラスの Fisher 線形判別を学習する(閉形式。反復なし)。

    ``X`` は (N, D) の特徴(``superpixel_color_texture_features`` の返りの dict もそのまま渡せる)、
    ``y`` は 0 / 1 の N 個のクラス。特徴を全体の平均と標準偏差で標準化し(分散 0 の列は尺度 1 のまま
    ``constant_columns`` に記録)、クラス内の共通共分散 Σ = (S₀ + S₁)/(N − 2) に
    ``ridge`` × tr(Σ)/D を足してから w = Σ⁻¹(μ₁ − μ₀)。判定の切片は 2 つの等分散正規分布の対数尤度比
    w·z − w·(μ₀ + μ₁)/2 + log(π₁/π₀) が 0 になる点(``prior1`` = π₁、既定は学習データの割合)。
    返す: ``w``・``bias``(score = z·w + bias、正ならクラス 1)・``mean``・``scale``・``mu0``・``mu1``・
    ``fisher_ratio``(J = (w·Δμ)²/(wᵀΣw)。分離の強さ)・``n0``・``n1``・``prior1``・``constant_columns``・``cond``。
    空の入力・y が 0/1 でない・各クラス 2 個未満・N ≤ 2・共分散の条件数が 1e12 を超える(向きが決まらない)・
    2 クラスの平均が同じとき(J = 0)は ``ValueError`` で拒否する。
    """
    op = "fisher_lda_fit"
    A = _matrix(X, op)
    yy = np.asarray(y)
    if yy.size == 0:
        raise ValueError("%s: y is empty" % op)
    if yy.dtype.kind == "b":
        yy = yy.astype(np.int64)
    if yy.dtype.kind not in "iuf" or yy.ndim != 1 or yy.shape[0] != A.shape[0]:
        raise ValueError("%s: y must be a 1-D array of %d labels (got shape %r)" % (op, A.shape[0], yy.shape))
    if not np.all(np.isin(yy, (0, 1))):
        raise ValueError("%s: y must hold only 0 and 1" % op)
    yy = yy.astype(np.int64)
    n1 = int(yy.sum())
    n0 = int(yy.size - n1)
    if n0 < 2 or n1 < 2:
        raise ValueError("%s: each class needs at least 2 samples (got n0=%d, n1=%d)" % (op, n0, n1))
    lam = _num(ridge, "ridge", op, 0.0, 1.0)
    if prior1 is None:
        p1 = n1 / float(n0 + n1)
    else:
        p1 = _num(prior1, "prior1", op, 0.0, 1.0, lo_open=True)
        if p1 >= 1.0:
            raise ValueError("%s: prior1 must be < 1 (got %r)" % (op, prior1))
    mean = A.mean(axis=0)
    sd = A.std(axis=0)
    const = [int(i) for i in np.nonzero(sd <= 1e-12 * (1.0 + np.abs(mean)))[0]]
    scale = np.where(sd <= 1e-12 * (1.0 + np.abs(mean)), 1.0, sd)
    Z = (A - mean) / scale
    Z0, Z1 = Z[yy == 0], Z[yy == 1]
    mu0, mu1 = Z0.mean(axis=0), Z1.mean(axis=0)
    S = (Z0 - mu0).T @ (Z0 - mu0) + (Z1 - mu1).T @ (Z1 - mu1)
    dof = n0 + n1 - 2
    Sig = S / dof
    D = Sig.shape[0]
    Sig = Sig + lam * (np.trace(Sig) / D if np.trace(Sig) > 0 else 1.0) * np.eye(D)
    cond = float(np.linalg.cond(Sig))
    if not math.isfinite(cond) or cond > 1e12:
        raise ValueError("%s: within-class covariance is degenerate (cond=%.3g); the discriminant "
                         "direction is not determined — add samples, drop collinear features or raise ridge"
                         % (op, cond))
    dmu = mu1 - mu0
    w = np.linalg.solve(Sig, dmu)
    quad = float(w @ Sig @ w)
    J = float((w @ dmu) ** 2 / quad) if quad > 0 else 0.0
    if not J > 1e-12:
        raise ValueError("%s: the two class means coincide (Fisher ratio %.3g); no direction separates them"
                         % (op, J))
    bias = float(-w @ (0.5 * (mu0 + mu1)) + math.log(p1 / (1.0 - p1)))
    return {"w": w, "bias": bias, "mean": mean, "scale": scale, "mu0": mu0, "mu1": mu1,
            "fisher_ratio": J, "n0": n0, "n1": n1, "prior1": p1, "constant_columns": const,
            "cond": cond, "ridge": lam, "n_features": int(D)}


def fisher_lda_score(model, X) -> Dict[str, object]:
    """``fisher_lda_fit`` の学習済みの判別で特徴を採点する(score > 0 をクラス 1 とする)。

    ``model`` は ``fisher_lda_fit`` の返り、``X`` は (N, D) の特徴(dict の ``X`` も可)。標準化は学習時の
    平均と尺度を使う。返す: ``score``(N)・``label``(0/1。**score がちょうど 0 はクラス 0**、宣言した規則)・
    ``margin``(|score| / ‖w‖ = 標準化空間で境界までの距離)・``n1``(クラス 1 と判定した数)。
    空の入力・列数の食い違い・非有限値・学習済みの判別でない ``model`` は ``ValueError`` で拒否する。
    """
    op = "fisher_lda_score"
    if not isinstance(model, dict) or not all(k in model for k in ("w", "bias", "mean", "scale")):
        raise ValueError("%s: model must be the dict returned by fisher_lda_fit" % op)
    A = _matrix(X, op)
    w = np.asarray(model["w"], np.float64)
    if A.shape[1] != w.shape[0]:
        raise ValueError("%s: X has %d columns but the model was fit on %d" % (op, A.shape[1], w.shape[0]))
    Z = (A - np.asarray(model["mean"], np.float64)) / np.asarray(model["scale"], np.float64)
    s = Z @ w + float(model["bias"])
    lab = (s > 0.0).astype(np.int64)
    nw = float(np.linalg.norm(w))
    return {"score": s, "label": lab, "margin": np.abs(s) / (nw if nw > 0 else 1.0),
            "n1": int(lab.sum())}


# --------------------------------------------------------------------------- #
# 4. 被度の段階                                                                 #
# --------------------------------------------------------------------------- #
def cover_ratio_grade(fraction, *, edges: Sequence[float] = DEFAULT_GRADE_EDGES) -> Dict[str, object]:
    """被度(面積の割合 0..1)を、**宣言した境** ``edges`` で段階 0..len(edges) に分ける。

    段階 k は edges[k−1] <= f < edges[k] (境ちょうどは上の段階)。既定の境 (0.05, 0.25, 0.50) は
    植生調査の被度階級(Braun-Blanquet の 5 % / 25 % / 50 %)から借りたもので、4 段階
    (0 少ない / 1 中程度 / 2 多い / 3 甚大)になる。注釈の分布から決めたものではない。
    ``fraction`` はスカラーか 1-D の配列。返す: ``grade``(int の配列)・``edges``・
    ``margin``(最も近い境までの距離。小さいほど判定が脆い)・``n_grades``・``counts``(段階ごとの数)。
    空の入力・非有限値・[0, 1] の外・境が (0, 1) の中で狭義単調増加でないときは ``ValueError`` で拒否する。
    """
    op = "cover_ratio_grade"
    if isinstance(fraction, (str, bytes, dict)) or fraction is None:
        raise ValueError("%s: fraction must be a number or a 1-D array" % op)
    f = np.atleast_1d(np.asarray(fraction))
    if f.size == 0:
        raise ValueError("%s: fraction is empty" % op)
    if f.dtype.kind not in "biuf" or f.ndim != 1:
        raise ValueError("%s: fraction must be a real scalar or 1-D array (got shape %r)" % (op, f.shape))
    f = f.astype(np.float64)
    if not np.isfinite(f).all() or f.min() < 0.0 or f.max() > 1.0:
        raise ValueError("%s: fraction must be finite and in [0, 1]" % op)
    e = np.asarray(edges, np.float64).ravel()
    if e.size == 0 or not np.isfinite(e).all() or e.min() <= 0.0 or e.max() >= 1.0 \
            or np.any(np.diff(e) <= 0.0):
        raise ValueError("%s: edges must be strictly increasing inside (0, 1) (got %r)" % (op, edges))
    grade = np.searchsorted(e, f, side="right").astype(np.int64)
    margin = np.min(np.abs(f[:, None] - e[None, :]), axis=1)
    counts = np.bincount(grade, minlength=e.size + 1).astype(np.int64)
    return {"grade": grade, "edges": e, "margin": margin, "n_grades": int(e.size + 1),
            "counts": counts}
