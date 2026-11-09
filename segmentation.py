"""特徴空間分類・領域成長・マーカー watershed(HALCON "Segmentation" chapter genuine, numpy).

グレー/多次元特徴空間での画素分類、gray 類似度での領域拡張、マーカー制御 watershed。
学習型(GMM/MLP/SVM)は別ドメインのため対象外。image = 2D float64、region = bool 2D。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "check_difference", "class_2dim_sup", "learn_ndim_norm", "class_ndim_norm",
    "class_2dim_unsup", "classify_image_class_lut", "expand_gray", "regiongrowing_n",
    "watersheds_marker",
]


def _img(a):
    return np.asarray(a, dtype=np.float64)


def check_difference(image, ref_image, tol=0.1):
    """基準画像との差が tol を超える画素を領域として返す(check_difference)。"""
    return np.abs(_img(image) - _img(ref_image)) > float(tol)


def class_2dim_sup(image1, image2, ref_region):
    """2 チャネル特徴空間で ref_region の分布に入る画素を分類(教師つき)(class_2dim_sup)。

    空の入力(``image1`` が 0 要素)は ValueError。"""
    if np.asarray(image1).size == 0:   # ★2026-10-11 台帳の空入力の門: 生の例外でなく名指しで拒否
        raise ValueError("class_2dim_sup: image1 is empty — pass at least one element")
    a = _img(image1); b = _img(image2); m = np.asarray(ref_region, bool)
    fa = a[m]; fb = b[m]
    lo_a, hi_a = fa.min(), fa.max(); lo_b, hi_b = fb.min(), fb.max()
    return (a >= lo_a) & (a <= hi_a) & (b >= lo_b) & (b <= hi_b)


def learn_ndim_norm(features_fg, features_bg=None):
    """特徴ベクトル群から正規分布クラス(平均・共分散)を学習(learn_ndim_norm)。"""
    X = np.asarray(features_fg, float).reshape(len(features_fg), -1)
    mu = X.mean(0); cov = np.cov(X.T) + 1e-6 * np.eye(X.shape[1])
    model = {"mean": mu, "cov": cov, "inv": np.linalg.inv(cov)}
    if features_bg is not None:
        Xb = np.asarray(features_bg, float).reshape(len(features_bg), -1)
        model["bg_mean"] = Xb.mean(0)
    return model


def class_ndim_norm(feature_images, model, thresh=3.0):
    """ND 特徴画像を学習済み正規分布クラスで分類(Mahalanobis 距離 < thresh)(class_ndim_norm)。
    feature_images: (H,W,D) or D 枚の 2D。"""
    F = feature_images
    if isinstance(F, (list, tuple)):
        F = np.stack([_img(f) for f in F], axis=-1)
    F = np.asarray(F, float)
    H, W, D = F.shape
    diff = F.reshape(-1, D) - model["mean"]
    md = np.einsum("ij,jk,ik->i", diff, model["inv"], diff)
    return (np.sqrt(md) < thresh).reshape(H, W)


def class_2dim_unsup(image1, image2, n_clusters=3, iters=20):
    """2 チャネル特徴空間を k-means で教師なし分類(class_2dim_unsup)。ラベル画像を返す。"""
    a = _img(image1); b = _img(image2)
    X = np.column_stack([a.ravel(), b.ravel()])
    rng = np.random.default_rng(0)
    C = X[rng.choice(len(X), int(n_clusters), replace=False)]
    for _ in range(int(iters)):
        d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(2)
        lab = d.argmin(1)
        newC = np.array([X[lab == k].mean(0) if (lab == k).any() else C[k]
                         for k in range(int(n_clusters))])
        if np.allclose(newC, C):
            break
        C = newC
    return lab.reshape(a.shape)


def classify_image_class_lut(image, lut):
    """グレー LUT による画素分類(閾値/ラベル LUT)(classify_image_class_lut)。

    空の入力(``image`` が 0 要素)は ValueError。
    """
    if (len(image) if isinstance(image, (list, tuple)) else np.asarray(image).size) == 0:   # ★2026-10-12 空入力の方針 A: 黙って値を返さず、何が空かを名指しで拒否
        raise ValueError("classify_image_class_lut: image is empty — pass at least one element")
    im = _img(image); L = len(lut)
    idx = np.clip((im * (L - 1)).round().astype(int), 0, L - 1)
    return np.asarray(lut)[idx]


def expand_gray(image, seed_region, tol=0.05):
    """seed から gray 類似(|Δ|<tol)で領域を膨張(expand_gray)。

    空の入力(``image`` が 0 要素)は ValueError。"""
    if np.asarray(image).size == 0:   # ★2026-10-11 台帳の空入力の門: 生の例外でなく名指しで拒否
        raise ValueError("expand_gray: image is empty — pass at least one element")
    from scipy.ndimage import binary_dilation
    im = _img(image); reg = np.asarray(seed_region, bool).copy()
    ref = im[reg].mean() if reg.any() else 0.0
    for _ in range(1000):
        cand = binary_dilation(reg) & ~reg & (np.abs(im - ref) < tol)
        if not cand.any():
            break
        reg |= cand
    return reg


def regiongrowing_n(feature_images, tol=0.05, min_size=1):
    """多チャネル特徴の類似性で画像全体を領域分割(regiongrowing_n)。ラベル画像を返す。"""
    F = feature_images
    if isinstance(F, (list, tuple)):
        F = np.stack([_img(f) for f in F], axis=-1)
    F = np.asarray(F, float)
    if F.ndim == 2:
        F = F[..., None]
    H, W, D = F.shape
    labels = np.zeros((H, W), int); cur = 0
    from collections import deque
    for r0 in range(H):
        for c0 in range(W):
            if labels[r0, c0]:
                continue
            cur += 1; ref = F[r0, c0]
            q = deque([(r0, c0)]); labels[r0, c0] = cur; size = 0
            while q:
                r, c = q.popleft(); size += 1
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and not labels[rr, cc]:
                        if np.abs(F[rr, cc] - ref).max() < tol:
                            labels[rr, cc] = cur; q.append((rr, cc))
    return labels


def watersheds_marker(image, markers):
    """マーカー制御 watershed 分割(watersheds_marker)。markers: int ラベル画像(0=未割当)。

    空の入力(``image`` が 0 要素)は ValueError。``image`` と形の違う ``markers``、整数でない・
    負・非有限の ``markers`` も ValueError(整数値の float と bool は受ける)。
    ``skimage.segmentation.watershed`` をそのまま呼び、scikit-image が無ければ
    MissingDependencyError(画像を見ない最近傍へは落ちない)。
    """
    # ★2026-11-09 点検: 以前は except Exception で「マーカーからの最近傍」(画像を一切見ない
    #   Voronoi)へ黙って落ち、image 80x80 に markers 60x60 を渡すと例外なしで 60x60 を返した。
    #   float の markers は切り捨てで 0.9→0 になりマーカーが消えた。numpy だけで同じ答えを出す
    #   双子は無い(平坦部の同値の割り振りが違う)ので代替は置かない。numpy+scipy だけで閉じる
    #   分水嶺は blob2d.blob_split。
    if (len(image) if isinstance(image, (list, tuple)) else np.asarray(image).size) == 0:   # ★2026-10-12 空入力の方針 A: 黙って値を返さず、何が空かを名指しで拒否
        raise ValueError("watersheds_marker: image is empty — pass at least one element")
    im = _img(image)
    mk = _as_marker_labels(markers, im.shape)
    try:
        from skimage.segmentation import watershed
    except ImportError as exc:   # ★2026-11-09: 不在のときだけ、名指しで拒否(他の例外は外へ出す)
        from backend_safe import missing_dependency
        raise missing_dependency("skimage", "marker-controlled watershed has no numpy twin with the same answer",
                                 op="watersheds_marker") from exc
    return watershed(im, markers=mk)


def _as_marker_labels(markers, shape):
    """``markers`` を検査して int64 のラベル画像にする(watersheds_marker の入力の門)。

    ★2026-11-09: ``np.asarray(markers, int)`` は 0.9→0・1.8→1 と切り捨て、マーカー 1 個が
    黙って消えて番号もずれた。整数値でない float は ValueError にする。
    """
    m = np.asarray(markers)
    if m.shape != tuple(shape):
        raise ValueError("watersheds_marker: markers shape %s != image shape %s — pass a label image "
                         "of the same shape as the image" % (m.shape, tuple(shape)))
    if m.dtype.kind == "b":
        return m.astype(np.int64)
    if m.dtype.kind in "iu":
        out = m.astype(np.int64)
    elif m.dtype.kind == "f":
        if not np.isfinite(m).all():
            raise ValueError("watersheds_marker: markers contain NaN/inf — labels must be finite integers")
        if not np.array_equal(m, np.round(m)):
            bad = m[m != np.round(m)]
            raise ValueError("watersheds_marker: markers must be integer labels; got non-integer values "
                             "such as %r (truncating them would merge or drop markers)" % (float(bad.flat[0]),))
        out = m.astype(np.int64)
    else:
        raise ValueError("watersheds_marker: markers must be an integer label image, got dtype %s" % m.dtype)
    if out.size and out.min() < 0:
        raise ValueError("watersheds_marker: markers must be >= 0 (0 = unassigned), got min %d" % int(out.min()))
    return out
