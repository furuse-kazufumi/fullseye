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
    # float32 で直に積む(最終テンソルは float32 なので float64 中間は純粋な無駄=転送床の主因)。
    # 値は float64→float32 と float32 直変換で同一(単一丸め)なので parity は不変。
    x = np.stack([np.asarray(i, np.float32) for i in imgs])[:, None, :, :]
    return torch.as_tensor(x, dtype=torch.float32, device=device)


def _from_batch(t):
    return [a[0] for a in t.detach().cpu().numpy().astype(np.float64)]


def _gauss_kernel(sigma, device):
    r = max(1, int(4.0 * sigma + 0.5))               # scipy truncate=4.0
    x = torch.arange(-r, r + 1, dtype=torch.float32, device=device)
    k = torch.exp(-(x * x) / (2 * sigma * sigma))
    return (k / k.sum())


def _sep_conv(t, k):
    """分離可能 conv(symmetric パディング)。scipy gaussian_filter の既定
    mode='reflect'(= numpy 'symmetric'、端複製)に一致させる。torch の
    'reflect'(端非複製)を使っていた旧版は sobel/dog/unsharp 系で端リングが
    ずれ、_norm 正規化を通じて全体に乗っていた(2026-08-31 修正)。"""
    r = (k.numel() - 1) // 2
    t = F.conv2d(_pad_sym(t, r, 3), k.view(1, 1, 1, -1))
    return F.conv2d(_pad_sym(t, r, 2), k.view(1, 1, -1, 1))


def _sym_idx(n, r, device):
    """symmetric(半標本)反射の gather index。scipy.ndimage の既定 mode='reflect'
    (= numpy 'symmetric'、端サンプルを複製 (d c b a | a b c d))を torch で再現する。
    torch の F.pad 'reflect' は端非複製の鏡映(numpy 'reflect' = scipy 'mirror')で別物。
    r>n でも周期 2n の折り返しで正しく反射する(大 σ gaussian で必須)。"""
    j = torch.arange(-r, n + r, device=device)
    m = torch.remainder(j, 2 * n)
    return torch.where(m >= n, 2 * n - 1 - m, m)


def _pad_sym(t, r, axis):
    """(B,1,H,W) の axis(2=H / 3=W)を symmetric で両側 r パディング(index_select)。"""
    return t.index_select(axis, _sym_idx(t.shape[axis], r, t.device))


def _sep_conv_sym(t, k):
    """symmetric パディング版の分離可能 conv。scipy gaussian_filter と bit 一致(全サイズ)。"""
    r = (k.numel() - 1) // 2
    t = F.conv2d(_pad_sym(t, r, 3), k.view(1, 1, 1, -1))
    t = F.conv2d(_pad_sym(t, r, 2), k.view(1, 1, -1, 1))
    return t


def _conv(t, ker, device):
    """2D conv(symmetric パディング = scipy ndimage 既定 mode='reflect')。
    cv2 系(BORDER_REFLECT_101 = torch 'reflect')の op はこれを使わず
    自前で F.pad(mode='reflect') すること(_cv_sharpen 参照)。"""
    k = torch.as_tensor(ker, dtype=torch.float32, device=device).view(1, 1, *ker.shape)
    r0, r1 = ker.shape[0] // 2, ker.shape[1] // 2
    return F.conv2d(_pad_sym(_pad_sym(t, r1, 3), r0, 2), k)


def _norm_b(t):
    mx = t.abs().amax(dim=(2, 3), keepdim=True).clamp_min(1e-8)
    return t / mx


def _k(a):
    return (3, 5, 7, 9)[min(3, int(a * 4))]


# each: (batch tensor, a, b, device) -> batch tensor
def _gaussian(t, a, b, dev):
    return _sep_conv_sym(t, _gauss_kernel(0.3 + 2.7 * a, dev))


def _mean(t, a, b, dev):
    # box mean。scipy uniform_filter 既定 mode='reflect'=symmetric に合わせる(全サイズ bit 一致)。
    k = _k(a)
    ker = torch.ones(1, 1, k, k, device=dev) / (k * k)
    r = k // 2
    return F.conv2d(_pad_sym(_pad_sym(t, r, 3), r, 2), ker)


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
    """(B,1,H,W) を symmetric パディングして k×k 近傍を (B, k*k, H, W) に展開。
    scipy median/percentile_filter の既定 mode='reflect'=symmetric に一致
    (旧版は torch 'reflect' で k=9 のとき端 4px がずれた。2026-08-31 修正)。"""
    r = k // 2
    p = _pad_sym(_pad_sym(t, r, 3), r, 2)
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
    m = F.conv2d(_pad_sym(_pad_sym(t, r, 3), r, 2), ker)
    m2 = F.conv2d(_pad_sym(_pad_sym(t * t, r, 3), r, 2), ker)
    return _norm_b(torch.sqrt((m2 - m * m).clamp_min(0.0)))


def _unsharp(t, a, b, dev):
    g = _sep_conv(t, _gauss_kernel(0.5 + 1.5 * b, dev))
    return t + (1.5 * a) * (t - g)


def _sigmoid(t, a, b, dev):
    return 1.0 / (1.0 + torch.exp(-(4.0 + 12.0 * a) * (t.clamp(0, 1) - (0.2 + 0.6 * b))))


def _illuminate(t, a, b, dev):
    # core(backends_auto _sh_lut "illuminate")= x + gain*(x - blur(x)) の大 σ unsharp。
    # blur は scipy gaussian_filter(mode='reflect'=symmetric)なので symmetric conv で bit 一致。
    sm = _sep_conv_sym(t, _gauss_kernel(3.0 + 12.0 * a, dev))
    return (t + (0.3 + 0.7 * b) * (t - sm)).clamp(0, 1)


def _signed01_b(t):
    """backend_safe.signed01 のバッチ版: 0->0.5, ±max->0/1(符号を保存)。"""
    m = t.abs().amax(dim=(2, 3), keepdim=True)
    return torch.where(m > 1e-8, (t / (2 * m) + 0.5).clamp(0, 1),
                       torch.full_like(t, 0.5))


def _fft_mask_b(t, cutoff, high):
    """core _fft_mask のバッチ版。半径 cutoff で低/高域マスクし逆変換の実部。"""
    H, W = t.shape[2], t.shape[3]
    fy = torch.fft.fftfreq(H, device=t.device)
    fx = torch.fft.fftfreq(W, device=t.device)
    rad = torch.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)      # (H,W)
    mask = (rad > cutoff) if high else (rad <= cutoff)
    F = torch.fft.fft2(t)
    return torch.fft.ifft2(F * mask.to(F.dtype)).real


def _lowpass(t, a, b, dev):
    return _fft_mask_b(t, 0.05 + 0.4 * a, False).clamp(0, 1)


def _highpass(t, a, b, dev):
    return _signed01_b(_fft_mask_b(t, 0.02 + 0.3 * a, True))


def _grad_dir(t, a, b, dev):
    gx = _conv(t, np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float32), dev)
    gy = _conv(t, np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], np.float32), dev)
    return (torch.atan2(gy, gx) + np.pi) / (2 * np.pi)


def _equalize(t, a, b, dev):
    """core _equalize のバッチ版: 256-bin ヒストグラム平坦化(bin 中心で線形補間)。

    core = np.interp(x, bin_centers, cdf)。bin_centers は一様なので、x を bin index に
    写して cdf を線形補間する(端は np.interp と同じくクランプ)。
    """
    x = t.clamp(0, 1)
    B = x.shape[0]
    flat = x.view(B, -1)
    hists = torch.stack([torch.histc(flat[i], bins=256, min=0.0, max=1.0)
                         for i in range(B)])          # (B,256)
    cdf = hists.cumsum(1)
    cdf = cdf / cdf[:, -1:].clamp_min(1e-12)          # (B,256) in [0,1]
    pos = (x * 256.0 - 0.5).clamp(0, 255)             # bin 中心 = (2i+1)/512
    lo = pos.floor().long()
    hi = (lo + 1).clamp(max=255)
    frac = pos - lo.float()
    lo_f = lo.view(B, -1)
    hi_f = hi.view(B, -1)
    clo = torch.gather(cdf, 1, lo_f).view_as(x)
    chi = torch.gather(cdf, 1, hi_f).view_as(x)
    return clo + frac * (chi - clo)


# ── 領域(2値)モルフォロジ: conv2d カウント + 閾値で ndimage.binary_* を bit 一致再現 ── #
# region も実体は 2D 二値配列。dilation = (近傍カウント>0)、erosion = (カウント==footprint 和)。
# zero-pad conv = ndimage の border_value=0 と一致(champion の binarize/count 用)。
# footprint: reg_* は cross(generate_binary_structure(2,1))で iterations=_it(a)、
# *_circle / erosion_golay は disk(_rad(a))(skimage.disk と同式 x²+y²≤r²)を単回適用。
def _disk_kernel(r, device):
    if r <= 0:
        return torch.ones(1, 1, 1, 1, device=device)
    ys = torch.arange(-r, r + 1, dtype=torch.float32, device=device)
    yy, xx = torch.meshgrid(ys, ys, indexing="ij")
    return ((xx * xx + yy * yy) <= r * r).float().view(1, 1, 2 * r + 1, 2 * r + 1)


def _cross_kernel(device):
    return torch.tensor([[0, 1, 0], [1, 1, 1], [0, 1, 0]],
                        dtype=torch.float32, device=device).view(1, 1, 3, 3)


def _bin_t(t):
    return (t > 0.5).float()


def _bdilate(x, fp):
    r0, r1 = fp.shape[2] // 2, fp.shape[3] // 2
    c = F.conv2d(F.pad(x, (r1, r1, r0, r0)), fp)     # zero-pad = border_value 0
    return (c > 0.5).float()                          # 近傍に 1 が一つでも → True


def _berode(x, fp):
    r0, r1 = fp.shape[2] // 2, fp.shape[3] // 2
    c = F.conv2d(F.pad(x, (r1, r1, r0, r0)), fp)
    return (c >= float(fp.sum()) - 0.5).float()       # footprint 全てが 1 → True


def _it_n(a):
    return 1 + int(a * 3)                             # core _it(a)


def _reg_dilate(t, a, b, dev):
    fp = _cross_kernel(dev)
    x = _bin_t(t)
    for _ in range(_it_n(a)):
        x = _bdilate(x, fp)
    return x


def _reg_erode(t, a, b, dev):
    fp = _cross_kernel(dev)
    x = _bin_t(t)
    for _ in range(_it_n(a)):
        x = _berode(x, fp)
    return x


def _erosion_golay(t, a, b, dev):                     # = binary_erosion(disk(_rad(a)))
    return _berode(_bin_t(t), _disk_kernel(_it_n(a), dev))


def _erosion_circle(t, a, b, dev):
    return _berode(_bin_t(t), _disk_kernel(_it_n(a), dev))


def _dilation_circle(t, a, b, dev):
    return _bdilate(_bin_t(t), _disk_kernel(_it_n(a), dev))


def _opening_circle(t, a, b, dev):                    # erosion → dilation(disk 単回)
    fp = _disk_kernel(_it_n(a), dev)
    return _bdilate(_berode(_bin_t(t), fp), fp)


def _cv_sharpen(t, a, b, dev):
    # core = cv2.filter2D(v, kernel=[[0,-a,0],[-a,1+4a,-a],[0,-a,0]]), clip[0,1]。
    # cv2.filter2D 既定 border=BORDER_REFLECT_101 = torch 'reflect'。相関(非反転)= conv2d。
    k = torch.tensor([[0.0, -a, 0.0], [-a, 1.0 + 4.0 * a, -a], [0.0, -a, 0.0]],
                     dtype=torch.float32, device=dev).view(1, 1, 3, 3)
    return F.conv2d(F.pad(t, (1, 1, 1, 1), mode="reflect"), k).clamp(0, 1)


def _tv_chambolle(img, weight, eps=2.0e-4, max_iter=200):
    """skimage.restoration.denoise_tv_chambolle(2D)のバッチ GPU 版(Rudin-Osher-Fatemi)。

    skimage `_denoise_tv_chambolle_nd` を忠実に写す(tau=1/(2·ndim)=0.25、勾配=前進差分、
    d=p の負の発散、E ベース停止)。バッチは per-image の E を追い、全画像が収束したら打ち切る
    (収束後の追加反復は不動点なので結果を変えない=faithful)。計算重なので転送律速でなく GPU が効く。
    """
    px = torch.zeros_like(img)
    py = torch.zeros_like(img)
    d = torch.zeros_like(img)
    tau = 0.25                                        # 1/(2*ndim), ndim=2
    npix = float(img.shape[2] * img.shape[3])
    B = img.shape[0]
    out_final = img.clone()
    done = torch.zeros(B, dtype=torch.bool, device=img.device)
    E_init = E_prev = None
    for i in range(max_iter):
        if i > 0:
            d = -(px + py)
            d[:, :, 1:, :] += px[:, :, :-1, :]        # ax=0(H)の後退差分
            d[:, :, :, 1:] += py[:, :, :, :-1]        # ax=1(W)
            out = img + d
        else:
            out = img
        # 画像ごと停止(skimage は per-image に eps 停止)。未収束の画像だけ out を更新し、
        # 収束済みは freeze(全画像を全反復回すと早期停止すべき画像を過剰平滑化して非faithful)。
        out_final = torch.where(done.view(B, 1, 1, 1), out_final, out)
        E = (d * d).sum(dim=(1, 2, 3))                # per-image
        g0 = torch.zeros_like(img)
        g1 = torch.zeros_like(img)
        g0[:, :, :-1, :] = out[:, :, 1:, :] - out[:, :, :-1, :]
        g1[:, :, :, :-1] = out[:, :, :, 1:] - out[:, :, :, :-1]
        norm = torch.sqrt(g0 * g0 + g1 * g1)
        E = E + weight * norm.sum(dim=(1, 2, 3))
        norm = norm * (tau / weight) + 1.0
        px = (px - tau * g0) / norm
        py = (py - tau * g1) / norm
        E = E / npix
        if i == 0:
            E_init = E.clamp_min(1e-12)
            E_prev = E
        else:
            done = done | (torch.abs(E_prev - E) < eps * E_init)
            E_prev = E
            if bool(done.all()):
                break
    return out_final


def _sk_tv(t, a, b, dev):
    return _tv_chambolle(t, weight=0.02 + 0.3 * a)


def _persp_matrix(src, dst):
    """4 点対応から透視変換 3x3(cv2.getPerspectiveTransform 相当、numpy 求解)。"""
    A, rhs = [], []
    for (sx, sy), (dx, dy) in zip(src, dst):
        A.append([sx, sy, 1, 0, 0, 0, -sx * dx, -sy * dx]); rhs.append(dx)
        A.append([0, 0, 0, sx, sy, 1, -sx * dy, -sy * dy]); rhs.append(dy)
    m = np.linalg.solve(np.asarray(A, np.float64), np.asarray(rhs, np.float64))
    return np.array([[m[0], m[1], m[2]], [m[3], m[4], m[5]], [m[6], m[7], 1.0]])


def _projective_region(t, a, b, dev):
    # core = cv2.warpPerspective(getPerspectiveTransform(src,dst), INTER_LINEAR, BORDER_REFLECT)。
    # grid_sample(bilinear, reflection)で近似。cv2 の warp 規約と bit 一致はしないため、
    # 採否は IoU/count 指標の保存で判定(bridge の validate)。
    Bn, _, H, W = t.shape
    d = 0.06 + 0.12 * a
    src = [[0, 0], [W, 0], [W, H], [0, H]]
    dst = [[W * d * b, H * d], [W * (1 - d * b), 0], [W, H], [0, H * (1 - d)]]
    Minv = np.linalg.inv(_persp_matrix(src, dst))       # dst->src(サンプリング用)
    ys, xs = torch.meshgrid(torch.arange(H, dtype=torch.float32, device=dev),
                            torch.arange(W, dtype=torch.float32, device=dev), indexing="ij")
    hom = torch.stack([xs, ys, torch.ones_like(xs)], dim=-1)          # (H,W,3)
    Mi = torch.as_tensor(Minv, dtype=torch.float32, device=dev)
    s = hom @ Mi.T
    sx = s[..., 0] / s[..., 2]
    sy = s[..., 1] / s[..., 2]
    gx = (2.0 * sx + 1.0) / W - 1.0                      # align_corners=False の画素中心写像
    gy = (2.0 * sy + 1.0) / H - 1.0
    grid = torch.stack([gx, gy], dim=-1).unsqueeze(0).expand(Bn, H, W, 2)
    return F.grid_sample(t, grid, mode="bilinear", padding_mode="reflection",
                         align_corners=False).clamp(0, 1)


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
    # diff_of_gauss: 旧版は「_norm が端差を全体に乗せるので faithful 不可」と
    # 結論していたが、真因は _sep_conv の torch 'reflect'(端非複製)だった。
    # symmetric 化(2026-08-31)で端差そのものが消え full-image で一致する。
    "diff_of_gauss": (_dog, "dog", "diff_of_gauss"),
    "gray_opening_rect": (_open_rect, "gopen", "gray_opening_rect"),
    "gray_closing_rect": (_close_rect, "gclose", "gray_closing_rect"),
    "gray_tophat": (_tophat, "tophat", "gray_tophat"),
    "gray_bothat": (_bothat, "bothat", "gray_bottomhat"),
    "std_image": (_std_filter, "std_filter", "deviation_image"),
    "unsharp_masking": (_unsharp, "unsharp", "unsharp_masking"),
    "sigmoid_image": (_sigmoid, "sigmoid", "sigmoid"),
    # wave 3: 周波数(torch.fft は numpy.fft を厳密に写す)
    "lowpass_image": (_lowpass, "lowpass", "lowpass_image"),
    "highpass_image": (_highpass, "highpass", "highpass_image"),
    # wave 5(先行): grad_dir(atan2 of sobel)
    "gradient_direction": (_grad_dir, "grad_dir", "grad_dir"),
    # wave 4: ヒストグラム(equalize は core を torch で厳密再現)
    "equalize_image": (_equalize, "equalize", "equalize_histo"),
    # wave: illuminate(大 σ unsharp、symmetric conv で scipy と bit 一致)。champion 頻出
    "illuminate": (_illuminate, "illuminate", "illuminate"),
    # wave: 領域(2値)モルフォロジ(conv2d カウント + 閾値、ndimage.binary_* と bit 一致)。
    #   binarize/count champion 用。REGION sort だが実体は 2D 二値配列なので gpu 常駐区間に載る。
    "reg_dilate": (_reg_dilate, "reg_dilate", "dilation_circle"),
    "reg_erode": (_reg_erode, "reg_erode", "erosion_circle"),
    "erosion_golay": (_erosion_golay, "erosion_golay", "erosion_golay"),
    "erosion_circle": (_erosion_circle, "erosion_circle", "erosion_circle"),
    "dilation_circle": (_dilation_circle, "dilation_circle", "dilation_circle"),
    "opening_circle": (_opening_circle, "opening_circle", "opening_circle"),
    # gray morphology(grey_dilation/erosion size=_k(a)= maxpool/minpool)= rect 版と同一機構
    "gdilate": (_dilate_rect, "gdilate", "gray_dilation"),
    "gerode": (_erode_rect, "gerode", "gray_erosion"),
    # cv_sharpen(3x3 conv、cv2.filter2D 既定 border=reflect と一致)。denoise champion 末尾
    "cv_sharpen": (_cv_sharpen, "cv_sharpen", "emphasize"),
    # projective_trans_region(透視ワープ、grid_sample 近似)。bit 一致でなく指標保存で採否判定
    "projective_trans_region": (_projective_region, "projective_trans_region", "projective_trans_region"),
    # simulate_defocus = uniform_filter(_k(a)) = box mean。_mean 流用(interior faithful)。denoise champion
    "simulate_defocus": (_mean, "simulate_defocus", "simulate_defocus"),
    # sk_tv = Chambolle TV(計算重・GPU 向き)。skimage を忠実に写す。bit でなく指標保存で採否
    "sk_tv": (_sk_tv, "sk_tv", ""),
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
