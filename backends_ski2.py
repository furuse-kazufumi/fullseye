"""scikit-image incorporation (round 2) — distinctive functions not yet wrapped.

Mined from skimage's submodules: multi-Otsu, geometric-mean rank filter,
morphological reconstruction, h-maxima, diameter opening, isotropic closing, HOG
visualisation, Kitchen-Rosenfeld corners, the Radon transform, the inverse
Gaussian gradient, and Wiener deconvolution. `xsk2_` prefix; exception-safe;
outputs in the pipeline convention.
"""
from __future__ import annotations

import numpy as np

from backend_safe import signed01


def _safe(fn, out_sort=None):
    """Fail-soft wrapper -> the shared, RECORDING guard (backend_safe.guard).

    A failure degrades to a sort-valid fallback exactly as before, but the event
    is now written to the fallback ledger and strict mode re-raises, so a
    permanently broken op can no longer masquerade as a working identity.
    """
    from backend_safe import guard
    return guard(fn, out_sort)


def _norm(x):
    x = np.asarray(x, np.float64)
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    try:
        from skimage import filters, morphology, feature, segmentation, transform, restoration
    except Exception:
        return []

    def _u8(v):
        return (np.clip(np.asarray(v, np.float64), 0, 1) * 255).astype(np.uint8)

    def _multiotsu(v, a, b):
        """大津の判別分析法（Otsu's method）を多値に拡張した多値大津法で階調を
        量子化する。``skimage.filters.threshold_multiotsu`` を使う。

        a はクラス数を 3 または 4 に切り替える（``3 + int(a > 0.5)``）。
        **5 クラス以上は実装していない**——多値大津はしきい値の全探索コストが
        ``bins ** (classes - 1)`` で増えるため、実測（128x128）で 3 クラス
        0.0008 秒に対し 5 クラスは 2.435 秒（3239 倍）かかり、進化ループ 1 世代
        だけで実行が止まって見えるほど遅い（画像サイズにはほぼ依らない）。
        4 クラスなら 0.025 秒に収まる。b は未使用。しきい値で量子化した後
        ``(cls-1)`` で割って [0,1] に正規化する。
        """
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        # クラス数は 3..4。**5 は入れない**: skimage の多値大津は閾値の全探索で
        # コストが O(bins^(classes-1)) なので、1 段増やすだけで桁が変わる。
        # 実測 2026-09-02(128x128): a=1.0 で 5 クラス = 2.435 秒、a=0.0 の
        # 3 クラス = 0.0008 秒 —— **3239 倍**。画像サイズには依らない
        # (32/128/512 px でどれも約 1.6 秒)ので、大きさを絞っても効かない。
        # 進化ループは 1 世代で数百回 op を叩くため、この 1 op だけで実行が
        # 止まって見える。4 クラスなら 0.025 秒で、階調も十分に増える。
        cls = 3 + int(a > 0.5)                        # 3..4 classes
        th = filters.threshold_multiotsu(x, classes=cls)
        return np.digitize(x, th).astype(np.float64) / (cls - 1)

    def _reconstruction(v, a, b):
        """モルフォロジー再構成（reconstruction by dilation）。
        ``skimage.morphology.reconstruction`` を method="dilation" で呼ぶ。

        シード画像を「元画像から a に応じた深さだけ暗くしたもの」
        （``x - (0.05 + 0.25*a)``）として自動生成し、そのシードをマスク画像
        （元画像そのもの）まで測地学的に膨張させる。a はシードの深さ（大きい
        ほど多くの山が消える）を振る。b は未使用。小さな明るい斑点やノイズを
        消しつつ、大きな構造の輪郭は保つ（オープニングより形状の崩れが少ない）。
        """
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        seed = np.clip(x - (0.05 + 0.25 * a), 0, 1)
        return morphology.reconstruction(seed, x, method="dilation")

    def _h_maxima(v, a, b):
        """h-maxima 変換（局所極大のうち高さ h 未満のものを消す）。
        ``skimage.morphology.h_maxima`` を呼ぶ。

        a が高さのしきい値 h（``0.05 + 0.3 * a``、範囲 0.05〜0.35）を振る。
        b は未使用。出力は極大が残った画素を 1 とする二値画像（`region`）。
        h が小さいほど微小なノイズ状の極大まで拾い、大きいほど際立った山だけ
        残る。
        """
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        return morphology.h_maxima(x, 0.05 + 0.3 * a).astype(np.float64)

    def _radon(v, a, b):
        """ラドン変換によるサイノグラム（投影データ）。
        ``skimage.transform.radon`` を、画像の長辺に合わせた本数の角度
        （0〜180 度、``linspace`` で等間隔）で呼び、結果を元の画像サイズに
        リサイズしてから最大値で正規化する。

        a, b は未使用（角度本数は画像サイズから自動で決まる）。CT 再構成の
        順投影に相当する処理で、直線状の構造ほどサイノグラム上に強いパターン
        が出る。
        """
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        theta = np.linspace(0.0, 180.0, max(x.shape), endpoint=False)
        sino = transform.radon(x, theta=theta)
        return _norm(transform.resize(sino, x.shape, anti_aliasing=True))

    def _wiener(v, a, b):
        """ウィーナー逆畳み込み（既知の点拡がり関数を使ったデブラー）。
        ``skimage.restoration.wiener`` を呼ぶ。

        PSF はガウシアン形状を仮定して自前生成し、a が PSF の広がり
        （標準偏差 ``0.5 + 1.5*a``、5x5 窓）を振る。b がバランス項
        （``0.05 + 0.5*b``。ノイズ対信号比の逆数に相当し、大きいほどノイズ
        抑制寄りになる）を振る。**入力画像のボケが実際にこの想定ガウシアン
        PSF と一致している場合にのみ有効**で、PSF の形が違うとリンギングや
        復元失敗が出る。
        """
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        yy, xx = np.mgrid[-2:3, -2:3]
        psf = np.exp(-(xx * xx + yy * yy) / (2 * (0.5 + 1.5 * a) ** 2))
        psf /= psf.sum()
        return np.clip(restoration.wiener(x, psf, balance=0.05 + 0.5 * b), 0, 1)

    def _hog(v, a, b):
        """HOG（Histogram of Oriented Gradients）特徴量の可視化画像。
        ``skimage.feature.hog`` を ``visualize=True`` で呼び、可視化画像側を
        返す（特徴ベクトル自体は捨てる）。

        a がセル 1 辺のピクセル数（``6 + 2*int(a*3)``、6/8/10/12 の 4 段階）を
        振る。方向数は 8、ブロックは 2x2 に固定。b は未使用。出力は最大値で
        正規化した勾配方向強度の可視化であり、HOG 特徴ベクトルそのものでは
        ない。
        """
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        _, hog_img = feature.hog(x, orientations=8, pixels_per_cell=(6 + 2 * int(a * 3),) * 2,
                                 cells_per_block=(2, 2), visualize=True)
        return _norm(hog_img)

    defs = [
        ("xsk2_multiotsu", "segmentation", IMAGE, IMAGE, _multiotsu),
        ("xsk2_rank_geomean", "rank", IMAGE, IMAGE,
         lambda v, a, b: filters.rank.geometric_mean(_u8(v), morphology.disk(1 + int(a * 3))).astype(np.float64) / 255),
        ("xsk2_reconstruction", "morphology", IMAGE, IMAGE, _reconstruction),
        ("xsk2_h_maxima", "segmentation", IMAGE, REGION, _h_maxima),
        ("xsk2_diameter_opening", "morphology", IMAGE, IMAGE,
         lambda v, a, b: morphology.diameter_opening(np.clip(v, 0, 1), diameter_threshold=4 + int(a * 30))),
        ("xsk2_isotropic_close", "region", REGION, REGION,
         lambda v, a, b: morphology.isotropic_closing(binm(v), 1 + a * 4).astype(np.float64)),
        ("xsk2_hog", "texture", IMAGE, IMAGE, _hog),
        ("xsk2_corner_kr", "edges", IMAGE, IMAGE,
         lambda v, a, b: signed01(np.nan_to_num(feature.corner_kitchen_rosenfeld(np.clip(v, 0, 1))))),
        ("xsk2_radon", "frequency", IMAGE, IMAGE, _radon),
        ("xsk2_inv_gauss_grad", "edges", IMAGE, IMAGE,
         lambda v, a, b: segmentation.inverse_gaussian_gradient(np.clip(v, 0, 1), alpha=50 + 150 * a)),
        ("xsk2_wiener", "restoration", IMAGE, IMAGE, _wiener),
    ]
    return [Op(n, c, "", i, o, _safe(f, o)) for (n, c, i, o, f) in defs]
