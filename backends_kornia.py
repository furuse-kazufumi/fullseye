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


def _norm(x):
    x = np.asarray(x, np.float64)
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


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
        "ヘシアン行列に基づくブロブ・コーナー応答。"
        "``kornia.feature.hessian_response`` を既定パラメータで呼び、絶対値を"
        "取って最大絶対値で正規化する。\n\n"
        "**a, b は未使用**（共通ヘルパー ``_resp`` が a, b を受け取るだけで捨てる）。"
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
        return _np(_m()["KF"].median_blur(_t(v), (k, k)))

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
        return np.clip(_np(_m()["KF"].motion_blur(_t(v), ks, float(360 * a),
                                                  float(2 * b - 1))), 0, 1)

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
        """
        return np.clip(_np(_m()["KE"].equalize_clahe(_t(v), clip_limit=1.0 + 4.0 * a)), 0, 1)

    def _laplacian(v, a, b):
        """ラプラシアン（2 階微分）によるエッジ・ブロブ応答。
        ``kornia.filters.laplacian`` を呼び、絶対値を取ってから最大絶対値で
        正規化する。

        a でカーネルサイズを 3/5/7/9 の 4 段階から選ぶ（``_k(a)``、``_median``
        と同じ量子化）。b は未使用。
        """
        return _norm(np.abs(_np(_m()["KF"].laplacian(_t(v), _k(a)))))

    def _resp(*attrs):
        return lambda v, a, b: _norm(np.abs(_np(_feat(*attrs)(_t(v)))))

    defs = [
        ("xkor_gaussian", "smoothing", IMAGE, IMAGE, _gauss),
        ("xkor_bilateral", "smoothing", IMAGE, IMAGE, _bilateral),
        ("xkor_median", "rank", IMAGE, IMAGE, _median),
        ("xkor_unsharp", "smoothing", IMAGE, IMAGE, _unsharp),
        ("xkor_motion_blur", "smoothing", IMAGE, IMAGE, _motion),
        ("xkor_canny", "segmentation", IMAGE, REGION, _canny),
        ("xkor_clahe", "gray", IMAGE, IMAGE, _clahe),
        ("xkor_laplacian", "edges", IMAGE, IMAGE, _laplacian),
        ("xkor_harris", "edges", IMAGE, IMAGE,
         lambda v, a, b: signed01(_np(_feat("harris_response")(_t(v), k=0.04 + 0.02 * a)))),
        ("xkor_gftt", "edges", IMAGE, IMAGE, _resp("gftt_response")),
        ("xkor_hessian", "edges", IMAGE, IMAGE, _resp("hessian_response")),
        ("xkor_dog", "edges", IMAGE, IMAGE, _resp("dog_response_single", "dog_response")),
    ]
    return [Op(n, c, "", i, o, _safe(f, o)) for (n, c, i, o, f) in defs]
