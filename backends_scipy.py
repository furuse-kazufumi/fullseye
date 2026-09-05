"""SciPy signal/fft incorporation — filters beyond ndimage.

scipy.signal and scipy.fft carry operators the ndimage-based core does not:
the adaptive Wiener filter, the 2-D discrete cosine transform, Savitzky-Golay
smoothing, and Gaussian gradient magnitude. `build()` wraps the distinctive,
single-gray-image ones; exception-safe, output in [0,1]. Prefixed `xsp_`.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

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


def _chamfer_dist(v, a, b):
    """City-block (chamfer) distance to the nearest background pixel, normalised to [0,1].

    ★2026-09-02: 縮退入力での **符号つきセンチネル** を潰す。
    ``scipy.ndimage.distance_transform_cdt`` は「背景画素が 1 つも無い」入力に対して
    距離ではなく **-1 を全画素に**書く(実測: ``np.ones((8,8), bool)`` -> min=max=-1)。
    旧実装はそれをそのまま ``_norm`` に通していたので、**塗り潰された領域の距離マップが
    一様 -1 の「画像」**になっていた —— 例外も警告も出ないまま値域 [0,1] の image 契約を
    破り、保存・表示では全面が黒に潰れる。

    背景が無い = どの画素も「無限に遠い」ので、正規化後の正直な答えは **一様 1.0**。
    前景が無いときは距離 0 の一様 0.0。どちらも符号つきの値を返さない。
    """
    m = np.asarray(v) > 0.5
    if not m.any():
        return np.zeros(m.shape, np.float64)      # 前景なし -> 距離 0
    if m.all():
        return np.ones(m.shape, np.float64)       # 背景なし -> どこも最遠 = 正規化 1.0
    return _norm(ndimage.distance_transform_cdt(m).astype(np.float64))


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    out = []
    try:
        from scipy import signal

        def _wiener(v, a, b):
            """Wiener 適応フィルタ（``scipy.signal.wiener``）でノイズを抑える。

            ``a`` は近傍窓のサイズを 3, 5, 7, 9 の奇数に振る（``k = 3 + 2*int(a*3)``、
            a=0 で 3、a に近い 1 で 9）。``b`` は未使用。局所分散からノイズ分散を
            自動推定する適応フィルタで、一様な強さで均すガウシアン/ミーンボックスと
            違い平坦な領域ほど強く均し、分散の大きい（エッジ/テクスチャの多い）領域は
            保存されやすい。ガウス性ノイズを仮定するので塩胡椒ノイズには不向き。
            出力は [0,1] にクリップする。
            """
            k = 3 + 2 * int(a * 3)
            return np.clip(signal.wiener(np.clip(v, 0, 1), (k, k)), 0, 1)

        def _savgol(v, a, b):
            """Savitzky-Golay フィルタで画像を平滑化する（列方向→行方向の順に 1 次元適用）。

            ``a`` は窓幅を 5, 7, 9, 11, 13 の奇数に振る（``w = 5 + 2*int(a*4)``）。
            多項式次数は 2 に固定。``b`` は未使用。窓内に 2 次多項式を最小二乗
            フィットして中心値を置き換える手法なので、単純な移動平均よりピークの
            高さや勾配を保ったまま平滑化できる。窓幅が画像サイズに対して大きすぎると
            境界の処理（``scipy`` の既定の外挿）の影響が強く出る。
            """
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            w = 5 + 2 * int(a * 4)
            y = signal.savgol_filter(x, w, 2, axis=1)
            return np.clip(signal.savgol_filter(y, w, 2, axis=0), 0, 1)

        def _hilbert_env(v, a, b):
            """解析信号（ヒルベルト変換）の振幅包絡線を行方向に取り出す。

            画素値を [-0.5, 0.5] に平行移動してから各行に 1 次元ヒルベルト変換
            （``scipy.signal.hilbert``）を掛け、複素解析信号の絶対値（瞬時振幅）を
            正規化して返す。``a``, ``b`` は未使用。周期的な縞模様やテクスチャの
            「包絡線」を強調するのに向き、位相情報は捨てて振幅だけを残す。列方向
            には掛からないため、結果は水平方向の変化にのみ反応する。
            """
            x = np.clip(np.asarray(v, np.float64), 0, 1) - 0.5
            return _norm(np.abs(signal.hilbert(x, axis=1)))

        out += [Op(n, c, "", i, o, _safe(f, o)) for (n, c, i, o, f) in [
            ("xsp_wiener", "smoothing", IMAGE, IMAGE, _wiener),
            ("xsp_savgol", "smoothing", IMAGE, IMAGE, _savgol),
            ("xsp_hilbert_env", "texture", IMAGE, IMAGE, _hilbert_env),
        ]]
    except Exception:
        pass

    try:
        from scipy import fft as sfft

        def _dct(v, a, b):
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            return _norm(np.log1p(np.abs(sfft.dctn(x, norm="ortho"))))

        def _dct_lowpass(v, a, b):
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            C = sfft.dctn(x, norm="ortho")
            keep = max(2, int((0.15 + 0.6 * a) * min(x.shape)))
            M = np.zeros_like(C)
            M[:keep, :keep] = C[:keep, :keep]
            return np.clip(sfft.idctn(M, norm="ortho"), 0, 1)

        def _dct_denoise(v, a, b):
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            C = sfft.dctn(x, norm="ortho")
            thr = (0.01 + 0.2 * a) * np.abs(C).max()
            return np.clip(sfft.idctn(np.where(np.abs(C) > thr, C, 0.0), norm="ortho"), 0, 1)

        out += [Op("xsp_dct", "frequency", "", IMAGE, IMAGE, _safe(_dct)),
                Op("xsp_dct_lowpass", "frequency", "", IMAGE, IMAGE, _safe(_dct_lowpass)),
                Op("xsp_dct_denoise", "smoothing", "", IMAGE, IMAGE, _safe(_dct_denoise))]
    except Exception:
        pass

    # scipy.signal spline / detrend + ndimage morphological laplace / chamfer distance
    try:
        from scipy import signal as _sig

        out += [
            Op("xsp_cspline_smooth", "smoothing", "", IMAGE, IMAGE, _safe(
                lambda v, a, b: np.clip(_sig.cspline2d(np.clip(np.asarray(v, np.float64), 0, 1),
                                                       1.0 + 40.0 * a), 0, 1))),
            Op("xsp_detrend_flatten", "gray", "", IMAGE, IMAGE, _safe(
                lambda v, a, b: _norm(_sig.detrend(_sig.detrend(
                    np.clip(np.asarray(v, np.float64), 0, 1), axis=0), axis=1)) * 0.5 + 0.5)),
        ]
    except Exception:
        pass
    out += [
        Op("xsp_morph_laplace", "edges", "", IMAGE, IMAGE, _safe(
            lambda v, a, b: signed01(ndimage.morphological_laplace(
                np.clip(v, 0, 1), size=3 + 2 * int(a * 3))))),
        Op("xsp_chamfer_dist", "region", "", "region", IMAGE, _safe(_chamfer_dist)),
    ]

    # Gaussian gradient magnitude (ndimage, but a distinct operator vs plain sobel)
    out += [Op("xsp_gauss_grad_mag", "edges", "", IMAGE, IMAGE, _safe(
        lambda v, a, b: _norm(ndimage.gaussian_gradient_magnitude(
            np.clip(v, 0, 1), sigma=0.5 + 2.5 * a))))]
    return out
