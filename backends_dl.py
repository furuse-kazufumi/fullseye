"""Optional torch backend — GPU-capable advanced ops + a pretrained-model hook.

If torch is installed, registers a few advanced iterative operators that run on GPU
when available (Perona-Malik anisotropic diffusion, self-guided filter). It also
exposes the extension point for LEARNED operators: drop TorchScript models (*.pt)
into IMGEVOLVE_MODEL_DIR and each is registered as a `dl_<name>` image->image op
(a trained denoiser/segmenter becomes a typed operator the evolution can use).

Honest: no weights ship here; the diffusion/guided ops are self-contained (no
downloads). Learned ops appear only when the user provides models.

**torch is imported LAZILY** (first `dl_*` call), not at registration time.
Measured on this machine: ``import torch`` costs ~700 ms and used to be paid by
every ``import ops`` — i.e. by every Studio start and every CLI invocation — even
when no ``dl_*`` op was ever executed. Registration only needs to know that torch
is *installable*, which :func:`importlib.util.find_spec` answers without running
its ``__init__``. Honest limit of the swap: a torch that is present on the path
but broken (bad DLL, wrong CUDA build) used to make the two ops vanish from the
registry; now they register and each call degrades through ``_safe`` to the
sanitized fallback instead. The learned-model path still needs a real torch to
``torch.jit.load`` the weights, so it imports eagerly — but only when the user
actually set ``IMGEVOLVE_MODEL_DIR`` to a directory holding ``*.pt``.
"""
from __future__ import annotations

import importlib.util
import os

import numpy as np

_STATE: dict = {}


def _has(mod: str) -> bool:
    """True when *mod* is importable, without executing it (cheap path probe)."""
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:              # pragma: no cover - broken meta path finder
        return False


def _torch():
    """Import torch on first use and cache it plus the chosen device."""
    if not _STATE:
        import torch
        import torch.nn.functional as F

        _STATE.update(torch=torch, F=F,
                      dev="cuda" if torch.cuda.is_available() else "cpu")
    return _STATE


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
    s = _torch()
    return s["torch"].tensor(np.asarray(v, np.float32))[None, None].to(s["dev"])


def _np(t):
    return t.detach().cpu().numpy()[0, 0].astype(np.float64)


def anisotropic(v, a, b):
    torch = _torch()["torch"]
    x = _t(v); K = 0.02 + 0.2 * a; iters = 5 + int(b * 15); lam = 0.2
    for _ in range(iters):
        dn = torch.roll(x, -1, 2) - x; ds = torch.roll(x, 1, 2) - x
        de = torch.roll(x, -1, 3) - x; dw = torch.roll(x, 1, 3) - x
        x = x + lam * (torch.exp(-(dn / K) ** 2) * dn + torch.exp(-(ds / K) ** 2) * ds
                       + torch.exp(-(de / K) ** 2) * de + torch.exp(-(dw / K) ** 2) * dw)
    return np.clip(_np(x), 0, 1)


def guided(v, a, b):
    F = _torch()["F"]
    x = _t(v); r = 1 + int(a * 4); eps = 0.001 + 0.05 * b; k = 2 * r + 1

    def bf(t):
        return F.avg_pool2d(F.pad(t, (r, r, r, r), mode="reflect"), k, 1)

    mean_i = bf(x); var = bf(x * x) - mean_i * mean_i
    aa = var / (var + eps); bb = mean_i - aa * mean_i
    return np.clip(_np(bf(aa) * x + bf(bb)), 0, 1)


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    out = []
    if not _has("torch"):
        return out
    try:
        out += [Op(n, c, h, IMAGE, IMAGE, _safe(f)) for (n, c, h, f) in [
            ("dl_aniso_diffusion", "smoothing", "anisotropic_diffusion", anisotropic),
            ("dl_guided_filter", "smoothing", "guided_filter", guided),
        ]]

        # --- learned-model extension point ----------------------------------- #
        # Only this branch needs a live torch at registration time (the weights
        # have to be loaded to know which ops exist), and it is opt-in via env.
        mdir = os.environ.get("IMGEVOLVE_MODEL_DIR", "")
        if mdir and os.path.isdir(mdir):
            pts = [f for f in sorted(os.listdir(mdir)) if f.endswith(".pt")]
            if pts:
                s = _torch()
                for f in pts:
                    try:
                        model = s["torch"].jit.load(os.path.join(mdir, f),
                                                    map_location=s["dev"]).eval()
                    except Exception:
                        continue

                    def run(v, a, b, _m=model, _torch_mod=s["torch"]):
                        with _torch_mod.no_grad():
                            return np.clip(_np(_m(_t(v))), 0, 1)

                    out.append(Op(f"dl_{os.path.splitext(f)[0]}", "learned", "apply_dl_model",
                                  IMAGE, IMAGE, _safe(run)))
    except Exception:
        pass
    return out
