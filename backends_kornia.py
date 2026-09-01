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
    from backend_safe import sanitize

    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:
            out = None
        return sanitize(out, v, out_sort)
    return w


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


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    if not _HAS:
        return []

    def _gauss(v, a, b):
        s = 0.3 + 2.7 * a
        return _np(_m()["KF"].gaussian_blur2d(_t(v), (5, 5), (s, s)))

    def _bilateral(v, a, b):
        return np.clip(_np(_m()["KF"].bilateral_blur(
            _t(v), (5, 5), 0.05 + 0.4 * b, (1.0 + 3.0 * a,) * 2)), 0, 1)

    def _median(v, a, b):
        k = _k(a)
        return _np(_m()["KF"].median_blur(_t(v), (k, k)))

    def _unsharp(v, a, b):
        s = 0.5 + 2.0 * b
        return np.clip(_np(_m()["KF"].unsharp_mask(_t(v), (5, 5), (s, s))), 0, 1)

    def _motion(v, a, b):
        # kornia は float32 の畳み込みなので重み和の丸めで 1 をわずかに超えることが
        # ある(実測 max=1+2e-7)。`image` は [0,1] 契約なので出口で clip する
        # (`ops._apply` が段間で掛けている clip と同じ = パイプライン結果は不変)。
        ks = 2 * int(2 + a * 6) + 1
        return np.clip(_np(_m()["KF"].motion_blur(_t(v), ks, float(360 * a),
                                                  float(2 * b - 1))), 0, 1)

    def _canny(v, a, b):
        low = 0.1 + 0.3 * a
        _, edges = _m()["KF"].canny(_t(v), low_threshold=low,
                                    high_threshold=max(low + 1e-3, 0.3 + 0.4 * b))
        return _np(edges)

    def _clahe(v, a, b):
        return np.clip(_np(_m()["KE"].equalize_clahe(_t(v), clip_limit=1.0 + 4.0 * a)), 0, 1)

    def _laplacian(v, a, b):
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
