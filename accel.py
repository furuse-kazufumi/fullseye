"""GPU-ready batched backend — the same operators, high throughput.

The CPU registry runs one image at a time through scipy/OpenCV. For throughput
(and to exploit the user's RTX 5090) the hot, vectorisable operators also have a
torch implementation that processes a whole BATCH (N,1,H,W) at once on a chosen
device. `--device cuda` runs them on the GPU; on CPU, batching + fused kernels
still beat the per-image Python loop.

Honesty (feedback_cpu_short_poc_before_gpu / beat_the_null): the fast path must
produce the SAME result as the CPU reference. `parity()` difftests every accel op
against its registry op; `bench.py` measures images/sec vs the numpy baseline.
This environment is torch-CPU only, so GPU numbers are measured on the user's box
with --device cuda — never claimed here.

Reflect padding matches scipy's default so the interiors agree; morphology uses
pool ops whose borders differ slightly (disclosed via the parity tolerance).

    py -3.11 accel.py                  # list accel ops + CPU parity vs registry
    py -3.11 accel.py --device cuda    # (on a CUDA box) same, on the GPU
"""
from __future__ import annotations

import argparse
import os

import numpy as np

try:
    import torch
    import torch.nn.functional as F
    _HAS_TORCH = True
except Exception:  # pragma: no cover
    _HAS_TORCH = False

HERE = os.path.dirname(os.path.abspath(__file__))


def _to_batch(imgs, device):
    x = np.stack([np.asarray(i, np.float64) for i in imgs])[:, None, :, :]
    return torch.as_tensor(x, dtype=torch.float32, device=device)


def _from_batch(t):
    return [a[0] for a in t.detach().cpu().numpy().astype(np.float64)]


def _gauss_kernel(sigma, device):
    r = max(1, int(4.0 * sigma + 0.5))               # scipy truncate=4.0
    x = torch.arange(-r, r + 1, dtype=torch.float32, device=device)
    k = torch.exp(-(x * x) / (2 * sigma * sigma))
    return (k / k.sum())


def _sep_conv(t, k):
    r = (k.numel() - 1) // 2
    kh = k.view(1, 1, 1, -1)
    kv = k.view(1, 1, -1, 1)
    t = F.pad(t, (r, r, 0, 0), mode="reflect")
    t = F.conv2d(t, kh)
    t = F.pad(t, (0, 0, r, r), mode="reflect")
    return F.conv2d(t, kv)


def _conv(t, ker, device):
    k = torch.as_tensor(ker, dtype=torch.float32, device=device).view(1, 1, *ker.shape)
    r0, r1 = ker.shape[0] // 2, ker.shape[1] // 2
    return F.conv2d(F.pad(t, (r1, r1, r0, r0), mode="reflect"), k)


def _norm_b(t):
    mx = t.abs().amax(dim=(2, 3), keepdim=True).clamp_min(1e-8)
    return t / mx


def _k(a):
    return (3, 5, 7, 9)[min(3, int(a * 4))]


# each: (batch tensor, a, b, device) -> batch tensor
def _gaussian(t, a, b, dev):
    return _sep_conv(t, _gauss_kernel(0.3 + 2.7 * a, dev))


def _mean(t, a, b, dev):
    k = _k(a)
    ker = torch.ones(1, 1, k, k, device=dev) / (k * k)
    r = k // 2
    return F.conv2d(F.pad(t, (r, r, r, r), mode="reflect"), ker)


def _sobel(t, a, b, dev):
    gx = _conv(t, np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float32), dev)
    gy = _conv(t, np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], np.float32), dev)
    return _norm_b(torch.hypot(gx, gy))


def _laplace(t, a, b, dev):
    return _norm_b(_conv(t, np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], np.float32), dev).abs())


def _gamma(t, a, b, dev):
    return t.clamp(0, 1) ** (0.5 + 1.5 * a)


def _invert(t, a, b, dev):
    return 1.0 - t.clamp(0, 1)


def _scale(t, a, b, dev):
    return ((0.5 + 1.5 * a) * t + (b - 0.5)).clamp(0, 1)


def _threshold(t, a, b, dev):
    return (t > a).float()


def _erode_rect(t, a, b, dev):
    k = _k(a)
    return -F.max_pool2d(-t, k, stride=1, padding=k // 2)


def _dilate_rect(t, a, b, dev):
    k = _k(a)
    return F.max_pool2d(t, k, stride=1, padding=k // 2)


def _range_rect(t, a, b, dev):
    k = _k(a)
    return _norm_b(F.max_pool2d(t, k, stride=1, padding=k // 2)
                   + F.max_pool2d(-t, k, stride=1, padding=k // 2))


# ── wave 1: 密画素並列で core と <5e-3 一致する追加 op(2026-08-26)───────────── #
def _unfold_reflect(t, k):
    """(B,1,H,W) を reflect パディングして k×k 近傍を (B, k*k, H, W) に展開。"""
    r = k // 2
    p = F.pad(t, (r, r, r, r), mode="reflect")
    return F.unfold(p, kernel_size=k).view(t.shape[0], k * k, t.shape[2], t.shape[3])


def _median(t, a, b, dev):
    k = _k(a)
    return _unfold_reflect(t, k).median(dim=1, keepdim=True).values


def _percentile(t, a, b, dev):
    # scipy percentile_filter は rank_filter(rank = int(p/100*(n-1)))で並べ替え第 rank 位。
    # torch.quantile の補間法とはずれるので、同じ rank 規則で sort して取り出す。
    k = _k(a)
    n = k * k
    rank = min(n - 1, int(int(5 + 90 * b) / 100.0 * n))   # scipy: int(p/100*n)
    u = _unfold_reflect(t, k)                       # (B, n, H, W)
    return u.sort(dim=1).values[:, rank:rank + 1]


def _prewitt(t, a, b, dev):
    gx = _conv(t, np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], np.float32), dev)
    gy = _conv(t, np.array([[-1, -1, -1], [0, 0, 0], [1, 1, 1]], np.float32), dev)
    return _norm_b(torch.hypot(gx, gy))


def _shift(t, dy, dx):
    """_shift_edge(v,dy,dx) の torch 版(replicate パディングで端を複製)。"""
    py0, py1 = max(dy, 0), max(-dy, 0)
    px0, px1 = max(dx, 0), max(-dx, 0)
    p = F.pad(t, (px0, px1, py0, py1), mode="replicate")
    H, W = t.shape[2], t.shape[3]
    return p[:, :, py1:py1 + H, px1:px1 + W]


def _roberts(t, a, b, dev):
    d1 = t - _shift(t, -1, -1)
    d2 = _shift(t, 0, -1) - _shift(t, -1, 0)
    return _norm_b(torch.hypot(d1, d2))


def _dog(t, a, b, dev):
    g1 = _sep_conv(t, _gauss_kernel(0.5 + 2.0 * a, dev))
    g2 = _sep_conv(t, _gauss_kernel(1.0 + 4.0 * b, dev))
    return _norm_b((g1 - g2).abs())


def _open_rect(t, a, b, dev):
    k = _k(a)
    e = -F.max_pool2d(-t, k, stride=1, padding=k // 2)
    return F.max_pool2d(e, k, stride=1, padding=k // 2)


def _close_rect(t, a, b, dev):
    k = _k(a)
    d = F.max_pool2d(t, k, stride=1, padding=k // 2)
    return -F.max_pool2d(-d, k, stride=1, padding=k // 2)


def _tophat(t, a, b, dev):
    return _norm_b((t - _open_rect(t, a, b, dev)).clamp_min(0))


def _bothat(t, a, b, dev):
    return _norm_b((_close_rect(t, a, b, dev) - t).clamp_min(0))


def _std_filter(t, a, b, dev):
    k = _k(a)
    ker = torch.ones(1, 1, k, k, device=dev) / (k * k)
    r = k // 2
    m = F.conv2d(F.pad(t, (r, r, r, r), mode="reflect"), ker)
    m2 = F.conv2d(F.pad(t * t, (r, r, r, r), mode="reflect"), ker)
    return _norm_b(torch.sqrt((m2 - m * m).clamp_min(0.0)))


def _unsharp(t, a, b, dev):
    g = _sep_conv(t, _gauss_kernel(0.5 + 1.5 * b, dev))
    return t + (1.5 * a) * (t - g)


def _sigmoid(t, a, b, dev):
    return 1.0 / (1.0 + torch.exp(-(4.0 + 12.0 * a) * (t.clamp(0, 1) - (0.2 + 0.6 * b))))


# accel op name -> (fn, the CORE registry op NAME it reproduces, its HALCON name)
ACCEL = {
    "gauss_filter": (_gaussian, "gaussian", "gauss_filter"),
    "mean_image": (_mean, "mean_box", "mean_image"),
    "sobel_amp": (_sobel, "sobel_mag", "sobel_amp"),
    "laplace": (_laplace, "laplace", "laplace"),
    "gamma_image": (_gamma, "gamma", "pow_image"),
    "invert_image": (_invert, "invert", "invert_image"),
    "scale_image": (_scale, "scale_clip", "scale_image"),
    "threshold": (_threshold, "threshold", "threshold"),
    "gray_erosion_rect": (_erode_rect, "min_filter", "gray_erosion_rect"),
    "gray_dilation_rect": (_dilate_rect, "max_filter", "gray_dilation_rect"),
    "gray_range_rect": (_range_rect, "morph_grad", "gray_range_rect"),
    # wave 1
    "median_image": (_median, "median", "median_image"),
    "rank_percentile": (_percentile, "percentile", "rank_image"),
    "prewitt_amp": (_prewitt, "prewitt_mag", "prewitt_amp"),
    "roberts_amp": (_roberts, "roberts_mag", "roberts"),
    # diff_of_gauss は core が |g1-g2| を _norm(全体 max abs)で割るため、大 sigma で
    # 端の reflect 規約差が正規化係数を通じて全体スケールに乗る(interior 12px でも
    # 0.10 残る)。faithful にできないので accel には載せず CPU(core)へ委ねる。honest。
    "gray_opening_rect": (_open_rect, "gopen", "gray_opening_rect"),
    "gray_closing_rect": (_close_rect, "gclose", "gray_closing_rect"),
    "gray_tophat": (_tophat, "tophat", "gray_tophat"),
    "gray_bothat": (_bothat, "bothat", "gray_bottomhat"),
    "std_image": (_std_filter, "std_filter", "deviation_image"),
    "unsharp_masking": (_unsharp, "unsharp", "unsharp_masking"),
    "sigmoid_image": (_sigmoid, "sigmoid", "sigmoid"),
}


def run_batch(name, imgs, a=0.5, b=0.4, device="cpu"):
    """Run one accel op over a batch of images; returns a list of 2-D arrays."""
    fn = ACCEL[name][0]
    t = _to_batch(imgs, device)
    out = fn(t, a, b, device).clamp(0, 1)
    return _from_batch(out)


def run_pipeline(steps, imgs, device="cpu"):
    """Run a CHAIN of accel ops keeping the batch RESIDENT on the device.

    ``steps`` = [(op_name, a, b), ...]. Transfer host->device once, apply every op
    on the GPU without round-tripping, transfer back once.

    This is the E2E lever: per-op ``run_batch`` re-transfers the whole batch each
    call, so a single cheap op is dominated by PCIe transfer (measured: batch
    throughput is flat across ops = transfer-bound, and trivial ops like threshold
    LOSE to the CPU). A real inspection pipeline is a *sequence* of ops; keeping
    the data resident amortises the one transfer over the whole chain, which is
    where the GPU actually wins end-to-end. Same math as the CPU chain (parity via
    ``pipeline_parity``); the only difference is border conventions (reflect/pool).
    """
    t = _to_batch(imgs, device)
    for name, a, b in steps:
        t = ACCEL[name][0](t, a, b, device).clamp(0, 1)
    return _from_batch(t)


def _interior_max(ref, got, m=3):
    """Max abs diff ignoring an m-px border (pooling/reflect borders differ)."""
    return float(np.max(np.abs(ref[m:-m, m:-m] - got[m:-m, m:-m]))) if ref.shape[0] > 2 * m else \
        float(np.max(np.abs(ref - got)))


def parity(device="cpu"):
    """Difftest every accel op against the CORE registry op it reproduces."""
    import ops
    rng = np.random.default_rng(7)
    imgs = [np.clip(rng.random((64, 64)) * 0.6 + 0.2 * (np.mgrid[0:64, 0:64][1] / 64), 0, 1)
            for _ in range(6)]
    rows = []
    for name, (fn, core_name, halcon) in ACCEL.items():
        if core_name not in ops.RT:
            continue
        got = run_batch(name, imgs, 0.5, 0.4, device)
        full = inter = 0.0
        for i, im in enumerate(imgs):
            ref = np.clip(ops.RT[core_name](im.copy(), 0.5, 0.4), 0, 1)
            full = max(full, float(np.max(np.abs(ref - got[i]))))
            inter = max(inter, _interior_max(ref, got[i]))
        rows.append((name, halcon, full, inter))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    if not _HAS_TORCH:
        print("torch not available — accel disabled")
        return 1
    dev = a.device if (a.device == "cpu" or torch.cuda.is_available()) else "cpu"
    if dev != a.device:
        print("[accel] CUDA not available here; falling back to CPU (run on the RTX 5090 for GPU).")
    print("accel ops: %d  | device=%s | torch=%s" % (len(ACCEL), dev, torch.__version__))
    rows = parity(dev)
    ok = sum(1 for _, _, _, inter in rows if inter < 5e-3)
    print("parity vs core registry op  (full = incl. borders, interior = 3px-inset):")
    for name, halcon, full, inter in sorted(rows, key=lambda r: -r[3]):
        flag = "exact" if inter < 5e-3 else ("close" if inter < 5e-2 else "differ")
        print("  %-20s (%-18s)  full=%.4f interior=%.4f  %s" % (name, halcon, full, inter, flag))
    print("interior-faithful (<5e-3): %d / %d  — borders differ only by reflect/pool convention"
          % (ok, len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
