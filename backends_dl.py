"""Optional torch backend — GPU-capable advanced ops + a pretrained-model hook.

If torch is installed, registers a few advanced iterative operators that run on GPU
when available (Perona-Malik anisotropic diffusion, self-guided filter). It also
exposes the extension point for LEARNED operators: drop TorchScript models (*.pt)
into IMGEVOLVE_MODEL_DIR and each is registered as a `dl_<name>` image->image op
(a trained denoiser/segmenter becomes a typed operator the evolution can use).

Honest: no weights ship here; the diffusion/guided ops are self-contained (no
downloads). Learned ops appear only when the user provides models.
"""
from __future__ import annotations

import os

import numpy as np


def _safe(fn, out_sort=None):
    from backend_safe import sanitize

    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:
            out = None
        return sanitize(out, v, out_sort)
    return w


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    out = []
    try:
        import torch
        import torch.nn.functional as F

        dev = "cuda" if torch.cuda.is_available() else "cpu"

        def _t(v):
            return torch.tensor(np.asarray(v, np.float32))[None, None].to(dev)

        def _np(t):
            return t.detach().cpu().numpy()[0, 0].astype(np.float64)

        def anisotropic(v, a, b):
            x = _t(v); K = 0.02 + 0.2 * a; iters = 5 + int(b * 15); lam = 0.2
            for _ in range(iters):
                dn = torch.roll(x, -1, 2) - x; ds = torch.roll(x, 1, 2) - x
                de = torch.roll(x, -1, 3) - x; dw = torch.roll(x, 1, 3) - x
                x = x + lam * (torch.exp(-(dn / K) ** 2) * dn + torch.exp(-(ds / K) ** 2) * ds
                               + torch.exp(-(de / K) ** 2) * de + torch.exp(-(dw / K) ** 2) * dw)
            return np.clip(_np(x), 0, 1)

        def guided(v, a, b):
            x = _t(v); r = 1 + int(a * 4); eps = 0.001 + 0.05 * b; k = 2 * r + 1

            def bf(t):
                return F.avg_pool2d(F.pad(t, (r, r, r, r), mode="reflect"), k, 1)

            mean_i = bf(x); var = bf(x * x) - mean_i * mean_i
            aa = var / (var + eps); bb = mean_i - aa * mean_i
            return np.clip(_np(bf(aa) * x + bf(bb)), 0, 1)

        out += [Op(n, c, h, IMAGE, IMAGE, _safe(f)) for (n, c, h, f) in [
            ("dl_aniso_diffusion", "smoothing", "anisotropic_diffusion", anisotropic),
            ("dl_guided_filter", "smoothing", "guided_filter", guided),
        ]]

        # --- learned-model extension point ----------------------------------- #
        mdir = os.environ.get("IMGEVOLVE_MODEL_DIR", "")
        if mdir and os.path.isdir(mdir):
            for f in sorted(os.listdir(mdir)):
                if f.endswith(".pt"):
                    try:
                        model = torch.jit.load(os.path.join(mdir, f), map_location=dev).eval()
                    except Exception:
                        continue

                    def run(v, a, b, _m=model):
                        with torch.no_grad():
                            return np.clip(_np(_m(_t(v))), 0, 1)

                    out.append(Op(f"dl_{os.path.splitext(f)[0]}", "learned", "apply_dl_model",
                                  IMAGE, IMAGE, _safe(run)))
    except Exception:
        pass
    return out
