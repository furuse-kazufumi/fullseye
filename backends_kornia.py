"""Kornia incorporation — GPU-native (torch) differentiable image operators.

Kornia runs on torch tensors, so these operators execute on the GPU when a CUDA
device is available (set IMGEVOLVE_KORNIA_DEVICE=cuda on the RTX 5090). They add
distinctive detectors/filters (Harris/GFTT/Hessian/DoG responses, motion &
bilateral blur, CLAHE) and are the torch-native path for those ops. Registry use
is per-image; honest note: on CPU this is not faster than scipy — the speed is on
GPU / in batch. Exception-safe; `xkor_` prefix; halcon="".

**torch and kornia are imported LAZILY** (first ``xkor_*`` call). Measured on this
machine, importing them at module load cost ~700 ms (torch) + ~135 ms (kornia),
paid by every ``import ops`` — hence by every Studio start — even when no
``xkor_*`` op was ever executed. Registration only needs to know the two are
*installable*, which :func:`importlib.util.find_spec` answers without running
their ``__init__``.

Honest limits of that swap (both unreachable with the pinned kornia 0.8.3):
  * a torch/kornia present on the path but broken at import used to make the 12
    ``xkor_*`` ops vanish from the registry; now they register and each call
    degrades through ``_safe`` to the sanitized fallback;
  * ``xkor_gftt`` / ``xkor_hessian`` / ``xkor_dog`` used to be registered only
    after a ``getattr`` probe of ``kornia.feature``. The probe needs the module
    loaded, so the three names are now declared statically and the attribute is
    resolved on the first call (``dog_response_single`` preferred, then
    ``dog_response``, matching the old probe order). A kornia old enough to lack
    one would therefore expose a degrading op rather than no op.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import re

import numpy as np

from backend_safe import signed01


def _installed(mod: str) -> bool:
    """True when *mod* is importable, without executing it (cheap path probe)."""
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:  # pragma: no cover - broken meta path finder
        return False


_HAS = _installed("torch") and _installed("kornia")
_MODS: dict = {}


def _m() -> dict:
    """Import torch/kornia on first use; cache the submodules and the device."""
    if not _MODS:
        import torch

        dev = os.environ.get("IMGEVOLVE_KORNIA_DEVICE", "cpu")
        if dev == "cuda" and not torch.cuda.is_available():
            dev = "cpu"
        _MODS.update(torch=torch, _DEV=dev,
                     KF=importlib.import_module("kornia.filters"),
                     KFEAT=importlib.import_module("kornia.feature"),
                     KE=importlib.import_module("kornia.enhance"))
    return _MODS


def _safe(fn, out_sort=None):
    """Fail-soft wrapper -> the shared, RECORDING guard (backend_safe.guard).

    A failure degrades to a sort-valid fallback exactly as before, but the event
    is now written to the fallback ledger and strict mode re-raises, so a
    permanently broken op can no longer masquerade as a working identity.
    """
    from backend_safe import guard
    return guard(fn, out_sort)


def _t(v):
    s = _m()
    x = np.clip(np.asarray(v, np.float64), 0, 1).astype(np.float32)
    return s["torch"].as_tensor(x, device=s["_DEV"])[None, None]


def _np(t):
    return t.detach().cpu().numpy()[0, 0].astype(np.float64)


def _own_border(fn, v, r, mode):
    """``fn`` を **自前の境界**(``numpy.pad`` の ``mode``)で呼び、元の大きさに切り戻す。

    画像の外側に半径 ``r`` ぶん ``mode`` で画素を足してから kornia に渡し、内側を
    切り出す。切り出した画素の窓は足した画素の内側に収まるので、kornia が自分で
    どんな境界を置いても(版で既定が変わっても)結果は変わらない。窓が 1 段だけの
    filter(median・motion・laplacian・gaussian の差 = DoG)では、kornia 自身の境界と
    同じ ``mode`` を渡せば **値は 1 ビットも変わらない**。

    もう一つの効き目: torch の鏡映(reflect)は「半径 < 画像の辺」でしか動かず、
    4x4 の画像に 9x9 の窓で ``Padding size should be less than…`` を投げて op が
    fallback に落ちていた。``numpy.pad`` の reflect は半径が辺を超えても折り返しを
    繰り返して足せる(同じ規約をそのまま外へ延ばしたもの)ので、小さい画像も通る。

    経緯(2026-10-24): kornia 0.9.0 で ``median_blur`` と ``motion_blur`` の境界が
    0 埋めから鏡映に変わった(16x16 の乱数画像で縁の画素が最大 0.77 ずれた)。
    版で変わったのは境界だけではない —— ``spatial_gradient`` の 2 階微分の正規化
    (→ ``xkor_hessian``)と ``equalize_clahe`` の中身(→ ``xkor_clahe``)も変わった。
    xkor_* の全 op を両版で比べる門は ``tests/test_kornia_version_drift_2026_10_24.py``。
    """
    r = int(r)
    x = np.clip(np.asarray(v, np.float64), 0, 1)
    if r > 0:
        x = np.pad(x, r, mode=mode)            # "constant" は 0 を足す
    y = _np(fn(_t(x)))
    return y[r:y.shape[0] - r, r:y.shape[1] - r]


def _zero_border(fn, v, ksize):
    """``fn`` を **外側 0 埋め** の境界で呼ぶ(kornia 0.8 の median / motion の規約)。

    kornia 0.9.0 で ``median_blur`` と ``motion_blur`` の境界が 0 埋めから鏡映に
    変わった。窓の半径ぶん 0 を自前で足すので版に依らない(:func:`_own_border`)。
    """
    return _own_border(fn, v, int(ksize) // 2, "constant")


def _kornia_version() -> tuple:
    """入っている kornia の (major, minor)。読めなければ (0, 0)(= 古い側に倒す)。"""
    _m()
    m = re.match(r"(\d+)\.(\d+)", str(getattr(importlib.import_module("kornia"),
                                             "__version__", "")))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


#: ``kornia.feature.harris_response`` / ``gftt_response`` の窓(7x7 ガウシアン、鏡映)の半径。
#: 画像の辺がこれ以下だと torch の鏡映が例外を出す。
_CORNER_WINDOW_R = 3
#: ``dog_response_single(σ1=1.0, σ2=1.6)`` の大きい方のガウシアン(13x13)の半径。
_DOG_R = 6


def _norm(x, ref=None):
    """最大絶対値で正規化する。ただし **応答が丸め屑しか無いときは正規化しない**。

    kornia は float32 で計算するので、一様な画像にゼロ和カーネル(ラプラシアン・
    DoG)を当てても厳密に 0 にはならず 1e-7 級の屑が残る。その屑を屑自身の最大値で
    割ると **全画素が 1.0 になり、空フレームが「全面が最大エッジ」として返る**
    (実測 2026-09-16: 一様 0.09 の画像で ``xkor_laplacian`` が全画素 1.0、一様 0.08
    では 3.6e-9)。従来の床 ``1e-8`` は **float32 の屑より下**にあり、屑が床を跨ぐ
    たびに出力が 0 と全面 1.0 の間で反転していた。

    床は入力の大きさに対する相対量で決める。固定値にすると、暗い画像(最大 1e-3
    など)で本物の弱い応答まで消える。``1e-5 x |入力|max`` は float32 の相対誤差
    (1.2e-7)にカーネルの L1(9x9 で最大 16 程度)を掛けた屑の 5 倍以上あり、かつ
    16-bit 画像の量子化幅(1.5e-5)より下なので実信号は削らない。
    """
    x = np.asarray(x, np.float64)
    mx = float(np.max(np.abs(x)))
    scale = 1.0 if ref is None else max(float(np.max(np.abs(np.asarray(ref, np.float64)))), 1e-12)
    return x / mx if mx > 1e-5 * scale else np.zeros_like(x)


def _k(a):
    return (3, 5, 7, 9)[min(3, int(a * 4))]


def _feat(*attrs):
    """First existing ``kornia.feature`` attribute among *attrs* (resolved lazily)."""
    KFEAT = _m()["KFEAT"]
    for a in attrs:
        fn = getattr(KFEAT, a, None)
        if fn is not None:
            return fn
    raise AttributeError("kornia.feature has none of %s" % (attrs,))


#: lambda で定義された op の説明（lambda に docstring は書けない）。
#: ops.py の登録ループが Op.doc に積む。キーは op 名。
DOCS = {
    "xkor_harris": (
        "Harris コーナー応答。``kornia.feature.harris_response`` を呼び、符号付き"
        "応答を ``signed01`` で [0,1] に写像する（コーナーは正、エッジは負に出る"
        "Harris 応答の符号情報を保ったまま可視化域に収める）。\n\n"
        "a が Harris のスコア係数 k（``0.04 + 0.02 * a``、経験的に 0.04〜0.06 の"
        "範囲で使われる値）を振る。b は未使用。"
    ),
    "xkor_gftt": (
        "GFTT（Good Features To Track、Shi-Tomasi）コーナー応答。"
        "``kornia.feature.gftt_response`` を既定パラメータで呼び、絶対値を取って"
        "最大絶対値で正規化する。\n\n"
        "**a, b は未使用**（共通ヘルパー ``_resp`` が a, b を受け取るだけで捨てる）。"
    ),
    "xkor_hessian": (
        "ヘシアン行列の行列式 det H = Ixx·Iyy − Ixy² によるブロブ・コーナー応答。"
        "``kornia.filters.spatial_gradient`` の 5x5 Sobel 2 階微分カーネルを正規化なし"
        "（``normalized=False``）で掛けて 64 で割り（2 次・3 次の曲面で微分値そのものに"
        "なる）、端は複製、絶対値を取って最大絶対値で正規化する。\n\n"
        "**a, b は未使用**。``kornia.feature.hessian_response`` を呼ばないのは、kornia 0.9 で "
        "2 階微分カーネルの正規化が変わったため（0.8 は各カーネルを絶対値和で割るので Ixy だけが "
        "64/36 倍に効き、行列式が Hessian の行列式にならない。同じ画像で内側の値が最大 0.68 "
        "ずれた）。正規化を自前で固定したので版に依らず、0.9 の値と一致する。"
    ),
    "xkor_dog": (
        "DoG（Difference of Gaussians）ブロブ応答。"
        "``kornia.feature.dog_response_single``（無ければ ``dog_response`` に"
        "フォールバック）を既定パラメータで呼び、絶対値を取って最大絶対値で"
        "正規化する。\n\n"
        "**a, b は未使用**。使用する kornia のバージョンによって"
        "``dog_response_single`` が無い場合は古い ``dog_response`` へ自動で"
        "切り替わる。"
    ),
}


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    if not _HAS:
        return []

    def _gauss(v, a, b):
        """ガウシアンぼかし（kornia の GPU ネイティブ実装）。torch テンソル上で
        ``kornia.filters.gaussian_blur2d`` を 5x5 カーネル・シグマ可変で掛ける。

        a はシグマを 0.3〜3.0 の範囲で振る（``0.3 + 2.7 * a``）。b は未使用。
        CPU 実行では scipy 版と比べて速くはならない（GPU・バッチ実行時に効く
        実装。``IMGEVOLVE_KORNIA_DEVICE=cuda`` で GPU に乗る）。
        """
        s = 0.3 + 2.7 * a
        return _np(_m()["KF"].gaussian_blur2d(_t(v), (5, 5), (s, s)))

    def _bilateral(v, a, b):
        """バイラテラルフィルタ（エッジ保存平滑化）。``kornia.filters.bilateral_blur``
        を 5x5 カーネルで呼ぶ。

        a は空間方向のシグマ（``1.0 + 3.0 * a``、範囲 1.0〜4.0）、b は明度方向の
        シグマ（``0.05 + 0.4 * b``、範囲 0.05〜0.45）を振る。値が近い画素だけを
        混ぜるため、平滑化しつつエッジは保たれる。
        """
        return np.clip(_np(_m()["KF"].bilateral_blur(
            _t(v), (5, 5), 0.05 + 0.4 * b, (1.0 + 3.0 * a,) * 2)), 0, 1)

    def _median(v, a, b):
        """メディアン（中央値）フィルタ。``kornia.filters.median_blur`` を呼ぶ。

        a でカーネルサイズを 3/5/7/9 の 4 段階から選ぶ
        （``(3,5,7,9)[min(3, int(a*4))]``）。b は未使用。ごま塩ノイズなど
        外れ値ノイズに強く、ガウシアンぼかしよりエッジを保ちやすい。
        """
        k = _k(a)
        # 境界は外側 0 埋め(kornia 0.8 の規約。0.9 の鏡映に任せない —— _zero_border)
        return _zero_border(lambda x: _m()["KF"].median_blur(x, (k, k)), v, k)

    def _unsharp(v, a, b):
        """アンシャープマスク（鮮鋭化）。``kornia.filters.unsharp_mask`` を 5x5
        カーネルで呼ぶ。

        **a は未使用**、b がぼかしのシグマ（``0.5 + 2.0 * b``、範囲 0.5〜2.5）を
        振る。元画像から低周波成分（ぼかし版）を引いた差分を強調して足し戻す
        古典的な鮮鋭化。
        """
        s = 0.5 + 2.0 * b
        return np.clip(_np(_m()["KF"].unsharp_mask(_t(v), (5, 5), (s, s))), 0, 1)

    def _motion(v, a, b):
        """モーションブラー。``kornia.filters.motion_blur`` を呼ぶ。

        a がカーネル長とブラー角度の**両方**を振る
        （カーネルサイズ ``2*int(2+a*6)+1`` = 5〜17、角度 ``360*a`` 度）ため、
        この 2 つは独立には制御できない。b はブラー方向のオフセット
        （``2*b-1``、範囲 -1〜1）を振る。kornia は float32 の畳み込みなので
        重み和の丸めで出力が 1 をわずかに超えることがある(実測 max=1+2e-7)。
        `image` は [0,1] 契約なので出口で clip する（`ops._apply` が段間で
        掛けている clip と同じで、パイプライン全体の結果は変わらない）。
        """
        # kornia は float32 の畳み込みなので重み和の丸めで 1 をわずかに超えることが
        # ある(実測 max=1+2e-7)。`image` は [0,1] 契約なので出口で clip する
        # (`ops._apply` が段間で掛けている clip と同じ = パイプライン結果は不変)。
        ks = 2 * int(2 + a * 6) + 1
        # 境界は外側 0 埋め(kornia 0.8 の規約。0.9 の鏡映に任せない —— _zero_border)
        return np.clip(_zero_border(
            lambda x: _m()["KF"].motion_blur(x, ks, float(360 * a),
                                             float(2 * b - 1)), v, ks), 0, 1)

    def _canny(v, a, b):
        """Canny 法によるエッジ（二値領域）検出。``kornia.filters.canny`` を呼び、
        返り値のうち二値エッジマップ（``edges``）を採用する（勾配強度側は捨てる）。

        a が低いしきい値（``0.1 + 0.3 * a``）、b が高いしきい値
        （``max(低いしきい値 + 1e-3, 0.3 + 0.4 * b)``、低い方を必ず上回るよう
        下駄を履かせている）を振る。出力の sort は `region`。
        """
        low = 0.1 + 0.3 * a
        _, edges = _m()["KF"].canny(_t(v), low_threshold=low,
                                    high_threshold=max(low + 1e-3, 0.3 + 0.4 * b))
        return _np(edges)

    def _clahe(v, a, b):
        """CLAHE（コントラスト制限適応ヒストグラム均等化）。
        ``kornia.enhance.equalize_clahe`` を呼ぶ。

        a がクリップ制限（``1.0 + 4.0 * a``、範囲 1.0〜5.0）を振る。値が大きい
        ほどコントラストが強く持ち上がる代わりにノイズも強調されやすい。
        b は未使用。

        **kornia 0.9 以上が要る**。0.8 以前の ``equalize_clahe`` は OpenCV の CLAHE と
        平均 0.04〜0.17、最大 0.46 ずれる（0.9 でヒストグラムの bin・切った余りの配り方・
        LUT の丸め・タイル補間が直った）。版で値が黙って変わらないよう、0.9 未満では
        理由つきで断る。タイルの格子は 8x8 を明示して渡す。
        """
        ver = _kornia_version()
        if ver < (0, 9):
            raise ValueError(
                "xkor_clahe は kornia 0.9 以上が要る(入っているのは %d.%d): 0.8 以前の "
                "equalize_clahe は OpenCV の CLAHE と最大 0.46 ずれ、0.9 で直った。"
                "版で値が変わる結果は出さない —— kornia を 0.9 以上に上げる" % ver)
        return np.clip(_np(_m()["KE"].equalize_clahe(
            _t(v), clip_limit=1.0 + 4.0 * a, grid_size=(8, 8))), 0, 1)

    def _laplacian(v, a, b):
        """ラプラシアン（2 階微分）によるエッジ・ブロブ応答。
        ``kornia.filters.laplacian`` を呼び、絶対値を取ってから最大絶対値で
        正規化する。

        a でカーネルサイズを 3/5/7/9 の 4 段階から選ぶ（``_k(a)``、``_median``
        と同じ量子化）。b は未使用。
        """
        k = _k(a)
        # 境界は鏡映(kornia の既定)を自前で足す —— 値は同じで、4x4 に 9x9 の窓でも落ちない
        return _norm(np.abs(_own_border(
            lambda x: _m()["KF"].laplacian(x, k, border_type="reflect", normalized=True),
            v, k // 2, "reflect")), v)

    def _corner(v, call):
        """コーナー応答を kornia で。画像の辺が窓(7x7 の鏡映)以下のときだけ自前で鏡映を足す。

        harris / gftt は「勾配(端は複製)→ 7x7 ガウシアン(端は鏡映)」の 2 段なので、
        外側に足すと普通の大きさの画像では縁の値が変わる。kornia が例外を出す大きさ
        (辺 <= 3)に限って足す —— それ以外の画像の値は 1 ビットも変えない。
        """
        if min(np.shape(v)[:2]) <= _CORNER_WINDOW_R:
            return _own_border(call, v, _CORNER_WINDOW_R, "reflect")
        return _np(call(_t(v)))

    def _harris(v, a, b):
        return signed01(_corner(v, lambda x: _feat("harris_response")(x, k=0.04 + 0.02 * a)))

    def _resp(attr):
        # a, b は受け取るだけで捨てる(DOCS["xkor_gftt"])。kornia は呼ぶ時に引く(遅延 import)
        return lambda v, a, b: _norm(np.abs(_corner(v, lambda x: _feat(attr)(x))), v)

    def _hessian(v, a, b):
        # 正規化なしの 5x5 Sobel 2 階カーネル(Ixx, Ixy, Iyy)を 64 で割る = 微分値そのもの。
        # kornia の normalized=True は 0.8 と 0.9 で割る数が違う(DOCS["xkor_hessian"])。
        # 版でカーネルの符号が 3 本そろって反転しても det は変わらない。端は複製(両版)。
        g = _m()["KF"].spatial_gradient(_t(v), mode="sobel", order=2, normalized=False) / 64.0
        dxx, dxy, dyy = g[:, :, 0], g[:, :, 1], g[:, :, 2]
        return _norm(np.abs(_np(dxx * dyy - dxy * dxy)), v)

    def _dog(v, a, b):
        fn = _feat("dog_response_single", "dog_response")
        if getattr(fn, "__name__", "") != "dog_response_single":   # 古い kornia の代替
            return _norm(np.abs(_np(fn(_t(v)))), v)
        # 2 つのガウシアン(9x9・13x13、端は鏡映)の差。鏡映を自前で足す —— 値は同じで、
        # 4x4 の画像でも落ちない。σ は既定に頼らず明示する。
        return _norm(np.abs(_own_border(lambda x: fn(x, 1.0, 1.6), v, _DOG_R, "reflect")), v)

    defs = [
        ("xkor_gaussian", "smoothing", IMAGE, IMAGE, _gauss),
        ("xkor_bilateral", "smoothing", IMAGE, IMAGE, _bilateral),
        ("xkor_median", "rank", IMAGE, IMAGE, _median),
        ("xkor_unsharp", "smoothing", IMAGE, IMAGE, _unsharp),
        ("xkor_motion_blur", "smoothing", IMAGE, IMAGE, _motion),
        ("xkor_canny", "segmentation", IMAGE, REGION, _canny),
        ("xkor_clahe", "gray", IMAGE, IMAGE, _clahe),
        ("xkor_laplacian", "edges", IMAGE, IMAGE, _laplacian),
        ("xkor_harris", "edges", IMAGE, IMAGE, _harris),
        ("xkor_gftt", "edges", IMAGE, IMAGE, _resp("gftt_response")),
        ("xkor_hessian", "edges", IMAGE, IMAGE, _hessian),
        ("xkor_dog", "edges", IMAGE, IMAGE, _dog),
    ]
    return [Op(n, c, "", i, o, _safe(f, o)) for (n, c, i, o, f) in defs]
