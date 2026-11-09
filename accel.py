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
    # 色(H,W,3)は (B,3,H,W) へ(第 3 便)。灰色は従来どおり (B,1,H,W)。
    # ★実測(第 3 便、2048² x50): np.stack + 1 枚ずつの f32 化が 1.4 s で、PCIe 片道 0.3 s より重かった
    # (一時配列の確保と page fault)。行き先を 1 回だけ確保して流し込むと一時配列が消える。値は同じ。
    first = np.asarray(imgs[0])
    x = np.empty((len(imgs),) + first.shape, np.float32)
    for k, im in enumerate(imgs):
        if np.shape(im) != first.shape:          # 代入の broadcast で黙って通さない(np.stack と同じく拒む)
            raise ValueError("batch images must share one shape, got %r and %r" % (first.shape, np.shape(im)))
        x[k] = im
    x = x[:, None, :, :] if x.ndim == 3 else np.moveaxis(x, 3, 1)
    return torch.as_tensor(x, dtype=torch.float32, device=device)


def _from_batch(t):
    x = t.detach().cpu().numpy().astype(np.float64)
    return [a[0] if a.shape[0] == 1 else np.moveaxis(a, 0, 2) for a in x]


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
    """core _norm のバッチ版。**素通し分岐が必須**: 旧版は clamp_min(1e-8) で必ず
    除算し、平坦画像の float32 丸め残差(~3e-8)をフルスケール 1.0 に増幅していた
    (敵対レビュー 2026-08-31 P1: sobel/canny 等 13 op が定数入力で全面破綻)。
    閾値は float32 雑音床(~3e-8)より上の 1e-6 に置く。core(f64, 閾値 1e-8)との
    差は「真の応答最大値が 1e-8..1e-6 の画像」でのみ生じるが、その帯域は f32 では
    どのみち表現不能なので、平坦入力を正しく通すことを優先する。"""
    mx = t.abs().amax(dim=(2, 3), keepdim=True)
    return torch.where(mx > 1e-6, t / mx.clamp_min(1e-12), t)


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
    # scipy percentile_filter は rank_filter(rank = int(p/100*n))で並べ替え第 rank 位。
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
    var = m2 - m * m
    # E[x²]−E[x]² は f32 で桁落ちし、平坦画像でも偽分散が残る(実測 k=9 で
    # 2.4e-7)。sqrt が 1e-4 級へ増幅し _norm_b の素通し閾値を超えてフルスケール化
    # する(P1 の std 変種)。桁落ち床の 4 倍 = 1e-6 未満の分散は 0 とみなす
    # (σ < 1e-3 は f32 では雑音と不可分)
    var = torch.where(var > 1e-6, var, torch.zeros_like(var))
    return _norm_b(torch.sqrt(var))


def _unsharp(t, a, b, dev):
    # core (`ops._unsharp`) と同じく出口で [0,1] に clip(2026-09-02)。
    # unsharp は定義上オーバーシュートするので、clip が片側だけだと
    # `apply(..., device="cuda")` と CPU で違う生値が返る。
    g = _sep_conv(t, _gauss_kernel(0.5 + 1.5 * b, dev))
    return (t + (1.5 * a) * (t - g)).clamp(0, 1)


def _sigmoid(t, a, b, dev):
    return 1.0 / (1.0 + torch.exp(-(4.0 + 12.0 * a) * (t.clamp(0, 1) - (0.2 + 0.6 * b))))


def _illuminate(t, a, b, dev):
    # core(backends_auto _sh_lut "illuminate")= x + gain*(x - blur(x)) の大 σ unsharp。
    # blur は scipy gaussian_filter(mode='reflect'=symmetric)なので symmetric conv で bit 一致。
    sm = _sep_conv_sym(t, _gauss_kernel(3.0 + 12.0 * a, dev))
    return (t + (0.3 + 0.7 * b) * (t - sm)).clamp(0, 1)


# ── Batch 2(2026-08-31): image→region の関門 op。otsu が CPU に残ると
#    その先の region morphology 島へ GPU 常駐のまま入れず転送が分断される。
def _otsu(t, a, b, dev):
    """core _otsu の逐語移植: 256-bin ヒストグラム → 間クラス分散 argmax → x >= そのビンの上端。"""
    # ヒストグラムと最終比較は float64 で行う(P3: f32 だと bin 境界直下の値が
    # 境界へ丸まり argmax が動く。histc の f64 規約は np.histogram と完全一致を実測)
    # ★2026-11-09: clamp(0, 1) はしない —— 範囲外の入力で中核(実データの範囲で切る)と答えが割れた(独立レビュー R4)。
    x = t
    B = x.shape[0]
    outs = []
    edges = torch.linspace(0.0, 1.0, 257, dtype=torch.float64, device=t.device)
    mids = (edges[:-1] + edges[1:]) / 2
    for i in range(B):
        xi = x[i].double()
        # ★2026-11-09: core と同じく有限な画素の最小〜最大を [0,1] に伸ばしてから 256 ビン(定数の像は伸ばさない)。
        fin = torch.isfinite(xi)
        if xi.numel() and not bool(fin.any()):
            # ★2026-11-09(2 回目の確認): 中核と同じく、有限な画素が 1 つも無ければ拒否する(以前は黙って値を返した)。
            raise ValueError("otsu: no finite pixel in the input (all NaN/inf) — a threshold is undefined; "
                             "mask or fill the NaN first (e.g. np.nan_to_num) or check np.isfinite(img).any()")
        if bool(fin.any()):
            lo_i, hi_i = xi[fin].min(), xi[fin].max()
            if bool(hi_i > lo_i):
                xi = (xi - lo_i) / (hi_i - lo_i)
        hist = torch.histc(xi, bins=256, min=0.0, max=1.0)
        p = hist / hist.sum().clamp_min(1.0)
        omega = torch.cumsum(p, 0)
        mu = torch.cumsum(p * mids, 0)
        mu_t = mu[-1]
        den = omega * (1 - omega)
        sb = torch.where(den > 1e-12,
                         (mu_t * omega - mu) ** 2 / den.clamp_min(1e-12),
                         torch.zeros_like(den))
        # ★CPU 側(ops._otsu)と同じく**ビンの上端**で切る(2026-09-26)。
        # 中点で切ると argmax ビンの背景画素が前景に混ざる。ここを直し忘れると
        # 同じ絵で CPU と GPU の答えが割れる(test_fast_parity が門)。
        if not bool((den > 1e-12).any()):
            outs.append((xi > 0).float())
        else:
            outs.append((xi >= edges[int(sb.argmax()) + 1]).float())
    return torch.stack(outs)


def _dyn_threshold(t, a, b, dev):
    k = _k(a)
    ker = torch.ones(1, 1, k, k, device=dev) / (k * k)
    r = k // 2
    m = F.conv2d(_pad_sym(_pad_sym(t, r, 3), r, 2), ker)
    # b=0.5 でオフセットが厳密 0 になり「t > mean(t)」の同値比較になる(P2)。
    # 定数/線形入力では core(f64)は厳密同値 → False、f32 は ±ulp で符号が
    # ランダムに割れる。|t−m| が f32 床以下なら同値(diff=0)とみなして core の
    # 同値セマンティクスに合わせる。実画像でこの帯域に載る画素は刃の上の
    # 画素だけで、そこは f64 でも撮像雑音以下の判定になっている
    d = t - m
    d = torch.where(d.abs() < 1e-6, torch.zeros_like(d), d)
    return (d > (b - 0.5) * 0.4).float()


def _canny(t, a, b, dev):
    g = _sep_conv_sym(t, _gauss_kernel(0.5 + 1.5 * a, dev))
    gx = _conv(g, np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float32), dev)
    gy = _conv(g, np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], np.float32), dev)
    m = _norm_b(torch.hypot(gx, gy))
    return (m > (0.1 + 0.5 * b)).float()


def _maxpool_sym(t, k):
    """symmetric パディングの maximum_filter(scipy 既定 mode='reflect' と一致)。"""
    r = k // 2
    return F.max_pool2d(_pad_sym(_pad_sym(t, r, 3), r, 2), k, stride=1)


def _local_max(t, a, b, dev):
    k = _k(a)
    return ((t >= _maxpool_sym(t, k)) & (t > (0.3 + 0.4 * b))).float()


def _adaptive_gauss(t, a, b, dev):
    g = _sep_conv_sym(t, _gauss_kernel(1.0 + 3.0 * a, dev))
    return (t > g + (b - 0.5) * 0.3).float()


# ── Batch 3(2026-08-31): 二値 reconstruction(境界フラッド)────────────────
def _fill_holes_bin(t, a, b, dev):
    """ndimage.binary_fill_holes(v>0.5) の忠実移植。

    補集合を画像境界から 4 近傍(scipy 既定 structure = cross)で測地拡張し、
    届かなかった背景 = 穴 として前景に加える。不動点までの反復は決定的で、
    収束後の追加反復は結果を変えない(= faithful)。
    """
    m = (t > 0.5).float()
    bg = 1.0 - m
    reach = torch.zeros_like(bg)
    reach[:, :, 0, :] = bg[:, :, 0, :]
    reach[:, :, -1, :] = bg[:, :, -1, :]
    reach[:, :, :, 0] = bg[:, :, :, 0]
    reach[:, :, :, -1] = bg[:, :, :, -1]
    while True:
        up = F.pad(reach[:, :, 1:, :], (0, 0, 0, 1))
        down = F.pad(reach[:, :, :-1, :], (0, 0, 1, 0))
        left = F.pad(reach[:, :, :, 1:], (0, 1, 0, 0))
        right = F.pad(reach[:, :, :, :-1], (1, 0, 0, 0))
        grown = torch.clamp(reach + up + down + left + right, 0, 1) * bg
        if torch.equal(grown, reach):
            break
        reach = grown
    return torch.clamp(m + (bg - reach), 0, 1)


def _bilateral(t, a, b, dev):
    """core _bilateral の逐語移植: 5x5 shift 総和(edge-clamp = _shift の replicate)。
    25 シフト x exp の反復で計算重 = 転送律速でなく GPU が効く型。"""
    ss, sr, r = 1.0 + 3.0 * a, 0.05 + 0.4 * b, 2
    out = torch.zeros_like(t)
    wsum = torch.zeros_like(t)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            sh = _shift(t, dy, dx)
            w = float(np.exp(-(dx * dx + dy * dy) / (2 * ss * ss))) \
                * torch.exp(-((sh - t) ** 2) / (2 * sr * sr))
            out = out + w * sh
            wsum = wsum + w
    return out / wsum.clamp_min(1e-8)


def _signed01_b(t):
    """backend_safe.signed01 のバッチ版: 0->0.5, ±max->0/1(符号を保存)。
    閾値は f32 雑音床より上の 1e-6(P1/P6: FFT 残差が 1e-8 を超えて分岐が
    逆に倒れ、非 2 冪サイズの平坦画像で highpass が 0.5 ずれていた)。"""
    m = t.abs().amax(dim=(2, 3), keepdim=True)
    return torch.where(m > 1e-6, (t / (2 * m) + 0.5).clamp(0, 1),
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
    ang = (torch.atan2(gy, gx) + np.pi) / (2 * np.pi)
    # 勾配が f32 雑音床以下の画素は core の atan2(0,0)=0 → 0.5 に合わせる
    # (P1: 平坦画像で雑音の位相がランダムになり mean 0.25 へ崩れていた)
    flat = torch.hypot(gx, gy) < 1e-6
    return torch.where(flat, torch.full_like(ang, 0.5), ang)


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
    # 1px 幅/高さの次元は torch 'reflect' が拒否する(P4 クラッシュ)。長さ 1 の
    # 次元では reflect101 も replicate も同じ「唯一の画素の複製」なので replicate へ。
    k = torch.tensor([[0.0, -a, 0.0], [-a, 1.0 + 4.0 * a, -a], [0.0, -a, 0.0]],
                     dtype=torch.float32, device=dev).view(1, 1, 3, 3)
    p = F.pad(t, (0, 0, 1, 1), mode="reflect" if t.shape[2] > 1 else "replicate")
    p = F.pad(p, (1, 1, 0, 0), mode="reflect" if t.shape[3] > 1 else "replicate")
    return F.conv2d(p, k).clamp(0, 1)


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


_RB_CACHE: dict = {}


def _rolling_ball(t, a, b, dev):
    """``sk_rolling_ball`` = ``clip(v - skimage.restoration.rolling_ball(v, radius=5+int(20a)), 0, 1)``。

    skimage の背景は**非平坦な収縮 1 回**: ``bg[p] = min_k (v[p+k] + (h_c - h_k))``(``h`` = 球の高さ
    ``ball_kernel``、窓の外は +inf で埋める)。2026-11-03 に 40x37 の乱数画像・半径 7 で skimage と
    float64 で差 0 を確かめてから写した。窓の画素ごとに 1 回ずつずらした画像と最小を取る(半径 15 で 709 回)。
    球の表は skimage の ``ball_kernel`` をそのまま使う(この op は skimage が在るときだけ登録簿に載る)。
    """
    from skimage.restoration import ball_kernel
    r = 5 + int(a * 20)
    if r not in _RB_CACHE:
        k = ball_kernel(r, 2)
        c = np.array(k.shape) // 2
        fin = np.isfinite(k)
        d = (k[tuple(c)] - k)[fin]
        ii, jj = np.nonzero(fin)
        _RB_CACHE[r] = (int(c[0]), int(c[1]), ii.tolist(), jj.tolist(), d.astype(np.float64).tolist())
    cy, cx, ii, jj, dd = _RB_CACHE[r]
    H, W = t.shape[2], t.shape[3]
    P = F.pad(t, (cx, cx, cy, cy), value=float("inf"))
    bg = torch.full_like(t, float("inf"))
    for i, j, dv in zip(ii, jj, dd):
        torch.minimum(bg, P[:, :, i:i + H, j:j + W] + dv, out=bg)
    return (t - bg).clamp(0, 1)


def _persp_matrix(src, dst):
    """4 点対応から透視変換 3x3(cv2.getPerspectiveTransform 相当、numpy 求解)。"""
    A, rhs = [], []
    for (sx, sy), (dx, dy) in zip(src, dst):
        A.append([sx, sy, 1, 0, 0, 0, -sx * dx, -sy * dx]); rhs.append(dx)
        A.append([0, 0, 0, sx, sy, 1, -sx * dy, -sy * dy]); rhs.append(dy)
    m = np.linalg.solve(np.asarray(A, np.float64), np.asarray(rhs, np.float64))
    return np.array([[m[0], m[1], m[2]], [m[3], m[4], m[5]], [m[6], m[7], 1.0]])


def _projective_warp(t, a, b, dev):
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


def _projective_region(t, a, b, dev):
    """region 版: core は _rebinarise(>0.5)で {0,1} 契約を回復するので合わせる。
    旧版は補間の中間値をそのまま返し契約違反 + region→feature で値が壊れた(P5)。
    再二値化後の集合は core と IoU 1.000(実測)。image 版の twin
    (projective_trans_image)は core も連続のままなので _projective_warp を使う。"""
    return (_projective_warp(t, a, b, dev) > 0.5).float()


# ── GPU 第 2 便 D'(2026-11-02): 穴埋め 7 op。全件 parity 内部差 < 2e-6(torch CPU で実測)、
#    loco(RTX 5090)の実寸 bench(転送込み、2048² x50)で CPU 登録経路に対し 8〜144x。
#    採否基準 = 実寸で >= 5x(docs/perf/gpu_fill_2026-11-02.md)。abs_image(3.1x、転送床)は登録しない。
_SOBEL_X = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float32)
_SOBEL_Y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], np.float32)


def _corner_response(t, a, b, dev):
    """core _corner_response(Harris 応答)の逐語移植: ndimage.sobel(= 3x3 sobel、symmetric)→
    構造テンソル 3 成分を gaussian(σ=0.5+2a)→ det − 0.04·tr² → _signed01。"""
    gx = _conv(t, _SOBEL_X, dev)
    gy = _conv(t, _SOBEL_Y, dev)
    k = _gauss_kernel(0.5 + 2.0 * a, dev)
    axx = _sep_conv_sym(gx * gx, k)
    ayy = _sep_conv_sym(gy * gy, k)
    axy = _sep_conv_sym(gx * gy, k)
    return _signed01_b(axx * ayy - axy * axy - 0.04 * (axx + ayy) ** 2)


def _aniso_diffusion(t, a, b, dev):
    """core anisotropic(Perona–Malik、縁は複製 = Neumann)の逐語移植。K=0.05+0.25b、
    反復 2+int(8a)、刻み 0.2。反復 x 全画素の指数計算で計算重 = GPU が効く型(実測 144x)。
    2026-11-05(敵対的検証 第 2 巡 P7)まで CPU と同じく torch.roll の周期境界だった。"""
    K = 0.05 + 0.25 * b
    y = t.clone()
    for _ in range(2 + int(a * 8)):
        dn = torch.cat([y[:, :, 1:], y[:, :, -1:]], 2) - y
        ds = torch.cat([y[:, :, :1], y[:, :, :-1]], 2) - y
        de = torch.cat([y[:, :, :, 1:], y[:, :, :, -1:]], 3) - y
        dw = torch.cat([y[:, :, :, :1], y[:, :, :, :-1]], 3) - y
        y = y + 0.2 * (torch.exp(-(dn / K) ** 2) * dn + torch.exp(-(ds / K) ** 2) * ds
                       + torch.exp(-(de / K) ** 2) * de + torch.exp(-(dw / K) ** 2) * dw)
    return y.clamp(0, 1)


def _bandpass(t, a, b, dev):
    """core bandpass: lo=0.02+0.15a < |f| < hi=0.2+0.3b の環状マスク → ifft 実部 → signed01。"""
    lo, hi = 0.02 + 0.15 * a, 0.2 + 0.3 * b
    H, W = t.shape[2], t.shape[3]
    fy = torch.fft.fftfreq(H, device=t.device)
    fx = torch.fft.fftfreq(W, device=t.device)
    rad = torch.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)
    Ft = torch.fft.fft2(t)
    mask = ((rad > lo) & (rad < hi)).to(Ft.dtype)
    return _signed01_b(torch.fft.ifft2(Ft * mask).real)


def _binomial(t, a, b, dev):
    """core binomial: (1+x)^(n−1) の係数(n=_k(a))を正規化した分離可能 correlate(symmetric)。"""
    n = _k(a)
    w = np.array((np.poly1d([1, 1]) ** (n - 1)).coeffs, np.float32)
    w = w / w.sum()
    return _sep_conv_sym(t, torch.as_tensor(w, dtype=torch.float32, device=dev))


def _box_sym(t, w, dev):
    ker = torch.ones(1, 1, w, w, device=dev) / (w * w)
    r = w // 2
    return F.conv2d(_pad_sym(_pad_sym(t, r, 3), r, 2), ker)


def _local_contrast_norm(t, a, b, dev):
    """core dc_local_contrast_norm: 窓 w=_win(a)(3..15 奇数)の (I−μ)/(σ+floor)、0.5 中心、0.25 倍。"""
    w = int(round(3 + a * 12))
    w = w + 1 if w % 2 == 0 else w
    w = max(3, min(15, w))
    mu = _box_sym(t, w, dev)
    var = _box_sym(t * t, w, dev) - mu * mu
    sd = torch.sqrt(var.clamp_min(0.0))
    return (0.5 + 0.25 * ((t - mu) / (sd + (0.02 + 0.18 * b)))).clamp(0, 1)


def _cos_image(t, a, b, dev):
    return (torch.cos(2 * np.pi * t.clamp(0, 1)) + 1.0) / 2.0


def _companding_mu_law(t, a, b, dev):
    """core _companding_mu_law: μ=1+254a 対数圧縮 → 2^(1+round(7b)) 段に量子化 → 伸張。"""
    x = t.clamp(0, 1)
    mu = 1.0 + 254.0 * float(np.clip(a, 0.0, 1.0))
    q = float((1 << (1 + int(round(float(np.clip(b, 0.0, 1.0)) * 7)))) - 1)
    y = torch.round(torch.log1p(mu * x) / np.log1p(mu) * q) / q
    return (torch.expm1(y * np.log1p(mu)) / mu).clamp(0, 1)


# ── GPU 第 3 便(2026-11-02): HALCON OpenCL 48 件 + required 名簿の分類。
#    ここの kernel は **候補**で、FILL3_ADOPTED に載った名前だけが ACCEL に入る(実寸 >= 5x +
#    parity 内部差 < 5e-3)。不採用の kernel も計測を再現できるよう消さない。
#    採否と数字の正本 = docs/perf/gpu_fill3_2026-11-02.md / docs/perf/logs/fill3_*.json。
def _x01(t):
    return t.clamp(0, 1)


def _asin_image(t, a, b, dev):
    return torch.asin(_x01(t)) / (np.pi / 2)


def _acos_image(t, a, b, dev):
    return torch.acos(_x01(t)) / np.pi


def _atan_image(t, a, b, dev):
    return torch.atan(_x01(t)) / (np.pi / 2)


def _exp_image(t, a, b, dev):
    return torch.expm1(_x01(t)) / (np.e - 1.0)


def _log_image(t, a, b, dev):
    return torch.log1p(_x01(t)) / np.log(2.0)


def _sin_image(t, a, b, dev):
    return (torch.sin(2 * np.pi * _x01(t)) + 1.0) / 2.0


def _sqrt_image(t, a, b, dev):
    return torch.sqrt(_x01(t))


def _tan_image(t, a, b, dev):
    return _signed01_b(torch.tan((_x01(t) - 0.5) * (np.pi * 0.9)))


def _abs_image(t, a, b, dev):
    return t.abs()


def _gamma_image(t, a, b, dev):
    # core "gamma_image"(backends_auto)。冪は 0.3+2.5a で、core "gamma"(0.5+1.5a)とは別物。
    return _x01(t) ** (0.3 + 2.5 * a)


def _lut_trans(t, a, b, dev):
    """core f2_lut_trans: 256 段の sigmoid LUT(f64 で作って f32 へ)を 8 bit 量子化値で引く。"""
    gain, pivot = 1.0 + 12.0 * float(a), 0.15 + 0.70 * float(b)
    x = np.linspace(0.0, 1.0, 256)
    raw = 1.0 / (1.0 + np.exp(-gain * (x - pivot)))
    lo, hi = float(raw[0]), float(raw[-1])
    lut = (raw - lo) / (hi - lo) if (hi - lo) > 1e-9 else x
    idx = torch.round(t * 255.0).clamp(0, 255).long()
    return torch.as_tensor(lut, dtype=torch.float32, device=dev)[idx].clamp(0, 1)


def _median_rect(t, a, b, dev):
    """core median_rect: size=(_k(a), _k(b)) の矩形メディアン。scipy の順位 = n//2。"""
    k0, k1 = _k(a), _k(b)
    p = _pad_sym(_pad_sym(t, k1 // 2, 3), k0 // 2, 2)
    n = k0 * k1
    u = F.unfold(p, kernel_size=(k0, k1)).view(t.shape[0], n, t.shape[2], t.shape[3])
    return u.sort(dim=1).values[:, n // 2:n // 2 + 1]


def _mirror_image(t, a, b, dev):
    if a < 0.34:
        return t.flip(2)
    if a < 0.67:
        return t.flip(3)
    return t.transpose(2, 3)


def _convert_image_type(t, a, b, dev):
    """core it_convert_image_type: L = round(2+254a) 段に量子化。round は両者とも偶数丸め。"""
    x = _x01(t)
    levels = max(2, min(256, int(round(2 + float(np.clip(a, 0.0, 1.0)) * 254))))
    return torch.round(x * (levels - 1)) / (levels - 1)


def _crop_domain(t, a, b, dev):
    H, W = t.shape[2], t.shape[3]
    frac = float(np.clip(a, 0.0, 1.0))
    wh, ww = int(round(H * frac)), int(round(W * frac))
    out = torch.zeros_like(t)
    if wh >= 1 and ww >= 1:
        r0, c0 = (H - wh) // 2, (W - ww) // 2
        out[:, :, r0:r0 + wh, c0:c0 + ww] = t[:, :, r0:r0 + wh, c0:c0 + ww]
    return _x01(out)


def _resize_bl(crop, H, W):
    """backends_imgtools._resize(map_coordinates order=1、linspace(0, h-1, H))と同じ格子。"""
    if crop.shape[2:] == (H, W):
        return crop
    return F.interpolate(crop, size=(H, W), mode="bilinear", align_corners=True)


def _crop_part(t, a, b, dev):
    H, W = t.shape[2], t.shape[3]
    frac = float(np.clip(a, 0.05, 0.95))
    ch, cw = max(1, int(round(H * frac))), max(1, int(round(W * frac)))
    r0, c0 = (H - ch) // 2, (W - cw) // 2
    return _resize_bl(t[:, :, r0:r0 + ch, c0:c0 + cw], H, W)


def _crop_rectangle1(t, a, b, dev):
    H, W = t.shape[2], t.shape[3]
    m = float(np.clip(a, 0.0, 0.45))
    r1, c1 = int(round(H * m)), int(round(W * m))
    r2, c2 = max(r1 + 1, H - r1), max(c1 + 1, W - c1)
    return _resize_bl(t[:, :, r1:r2, c1:c2], H, W)


def _disk_offsets(r):
    return [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
            if dx * dx + dy * dy <= r * r]


def _morph_disk(t, r, erode):
    """ndimage.grey_erosion/dilation(footprint=disk(r)、mode='reflect'=symmetric)の移植。
    円盤は点対称なので grey_dilation の footprint 反転は効かない。"""
    H, W = t.shape[2], t.shape[3]
    p = _pad_sym(_pad_sym(t, r, 3), r, 2)
    out = None
    for dy, dx in _disk_offsets(r):
        s = p[:, :, r + dy:r + dy + H, r + dx:r + dx + W]
        out = s if out is None else (torch.minimum(out, s) if erode else torch.maximum(out, s))
    return out


def _gray_erosion_shape(t, a, b, dev):
    return _morph_disk(t, _it_n(a), True)


def _gray_dilation_shape(t, a, b, dev):
    return _morph_disk(t, _it_n(a), False)


def _gray_opening_shape(t, a, b, dev):
    r = _it_n(a)
    return _morph_disk(_morph_disk(t, r, True), r, False)


def _gray_closing_shape(t, a, b, dev):
    r = _it_n(a)
    return _morph_disk(_morph_disk(t, r, False), r, True)


def _texture_laws(t, a, b, dev):
    """core texture_laws(kind=variance): 大域平均を引いてから局所分散 → _norm。"""
    k = _k(a)
    x0 = t - t.mean(dim=(2, 3), keepdim=True)
    m = _box_sym(x0, k, dev)
    m2 = _box_sym(x0 * x0, k, dev)
    return _norm_b((m2 - m * m).clamp_min(0.0))


def _gauss_deriv_kernel(sigma, dev):
    """scipy _gaussian_kernel1d(order=1)の相関側の重み(truncate=4)。符号は hypot で消える。"""
    r = int(4.0 * sigma + 0.5)
    x = np.arange(-r, r + 1, dtype=np.float64)
    phi = np.exp(-0.5 * x * x / (sigma * sigma))
    phi = phi / phi.sum()
    return (torch.as_tensor(phi, dtype=torch.float32, device=dev),
            torch.as_tensor(-x / (sigma * sigma) * phi, dtype=torch.float32, device=dev))


def _derivate_gauss(t, a, b, dev):
    s = 0.5 + 2.5 * a
    g, d = _gauss_deriv_kernel(s, dev)
    r = (g.numel() - 1) // 2
    px = _pad_sym(t, r, 3)
    py = _pad_sym(t, r, 2)
    gy = F.conv2d(_pad_sym(F.conv2d(px, g.view(1, 1, 1, -1)), r, 2), d.view(1, 1, -1, 1))
    gx = F.conv2d(_pad_sym(F.conv2d(py, g.view(1, 1, -1, 1)), r, 3), d.view(1, 1, 1, -1))
    return _norm_b(torch.hypot(gx, gy))


# ── 3 次 B スプライン標本化(ndimage.affine_transform order=3 の移植)。第 2 便が「grid_sample は
#    双線形なので画素一致しない」と外した幾何ワープ族は、前置フィルタ + B3 重みを torch で書けば取れる。
_SPLINE_POLE = float(np.sqrt(3.0) - 2.0)
_SPLINE_R = 14                                      # |z|^14 ≈ 1e-8。FIR 打ち切りの誤差は f32 床以下


def _spline_prefilter(t):
    """scipy spline_filter(order=3, mode='reflect')の FIR 版。無限長の因果+反因果 IIR の
    インパルス応答 c[n] = (-6z/(1-z^2))·z^|n| を打ち切り、symmetric パディングで畳む。"""
    z, r = _SPLINE_POLE, _SPLINE_R
    k = -6.0 * z / (1.0 - z * z) * z ** np.abs(np.arange(-r, r + 1, dtype=np.float64))
    ker = torch.as_tensor(k, dtype=torch.float32, device=t.device)
    return _sep_conv_sym(t, ker)


def _b3_weights(f):
    f2, f3 = f * f, f * f * f
    return ((1 - f) ** 3 / 6.0, (3 * f3 - 6 * f2 + 4) / 6.0,
            (-3 * f3 + 3 * f2 + 3 * f + 1) / 6.0, f3 / 6.0)


def _sym_map(i, n):
    """整数添字を symmetric(d c b a | a b c d)に畳む。frozen な torch.remainder で周期 2n。"""
    m = torch.remainder(i, 2 * n)
    return torch.where(m >= n, 2 * n - 1 - m, m)


def _spline_sample(c, ys, xs):
    """(B,1,H,W) の係数 c を出力格子 (ys,xs)(f64、入力座標系)で標本化。"""
    H, W = c.shape[2], c.shape[3]
    y0, x0 = torch.floor(ys), torch.floor(xs)
    wy = _b3_weights((ys - y0).float())
    wx = _b3_weights((xs - x0).float())
    y0, x0 = y0.long(), x0.long()
    out = 0.0
    for i in range(4):
        iy = _sym_map(y0 + i - 1, H)
        for j in range(4):
            ix = _sym_map(x0 + j - 1, W)
            out = out + wy[i] * wx[j] * c[:, :, iy, ix]
    return out


def _affine_coords(H, W, M, off, dev):
    ys, xs = torch.meshgrid(torch.arange(H, dtype=torch.float64, device=dev),
                            torch.arange(W, dtype=torch.float64, device=dev), indexing="ij")
    return (float(M[0][0]) * ys + float(M[0][1]) * xs + float(off[0]),
            float(M[1][0]) * ys + float(M[1][1]) * xs + float(off[1]))


def _affine_spline(t, M, off, dev):
    yy, xx = _affine_coords(t.shape[2], t.shape[3], M, off, dev)
    return _spline_sample(_spline_prefilter(t), yy, xx)


def _affine_warp(t, a, b, dev):
    ang = np.deg2rad(-20 + 40 * a)
    M = np.array([[np.cos(ang), -np.sin(ang) + (b - 0.5) * 0.4], [np.sin(ang), np.cos(ang)]])
    c = (np.array(t.shape[2:], np.float64) - 1) / 2      # 画素中心の規約(CPU と同じ、敵対的検証 2026-11-05 P8)
    return _affine_spline(t, M, c - M @ c, dev)


def _rotate_image(t, a, b, dev):
    """ndimage.rotate(angle=-45+90a, reshape=False, mode='reflect') の行列を逐語で組む。"""
    th = np.deg2rad(-45 + 90 * a)
    c, s = np.cos(th), np.sin(th)
    M = np.array([[c, s], [-s, c]])
    ctr = (np.array(t.shape[2:], np.float64) - 1) / 2
    return _affine_spline(t, M, ctr - M @ ctr, dev)


def _zoom_factor(t, a, b, dev):
    sr, sc = 0.7 + 0.6 * a, 0.7 + 0.6 * b
    H, W = t.shape[2], t.shape[3]
    return _affine_spline(t, np.diag([1 / sr, 1 / sc]),
                          ((H - 1) / 2 * (1 - 1 / sr), (W - 1) / 2 * (1 - 1 / sc)), dev)   # 中心 (H-1)/2(P8)


def _rescale_img(t, a, b, dev):
    """core rescale_img: b で補間次数 (0,1,3,3) を選ぶ。次数 3 以外も同じ座標で書く。"""
    s = 0.7 + 0.6 * a
    H, W = t.shape[2], t.shape[3]
    order = (0, 1, 3, 3)[min(3, int(float(np.clip(b, 0.0, 1.0)) * 4))]
    off = ((H - 1) / 2 * (1 - 1 / s), (W - 1) / 2 * (1 - 1 / s))      # 中心 (H-1)/2(P8)
    yy, xx = _affine_coords(H, W, np.diag([1 / s, 1 / s]), off, dev)
    if order == 3:
        return _spline_sample(_spline_prefilter(t), yy, xx)
    if order == 1:
        y0, x0 = torch.floor(yy), torch.floor(xx)
        fy, fx = (yy - y0).float(), (xx - x0).float()
        y0, x0 = y0.long(), x0.long()
        y1, x1 = _sym_map(y0 + 1, H), _sym_map(x0 + 1, W)
        y0, x0 = _sym_map(y0, H), _sym_map(x0, W)
        return ((1 - fy) * ((1 - fx) * t[:, :, y0, x0] + fx * t[:, :, y0, x1])
                + fy * ((1 - fx) * t[:, :, y1, x0] + fx * t[:, :, y1, x1]))
    iy = _sym_map(torch.floor(yy + 0.5).long(), H)
    ix = _sym_map(torch.floor(xx + 0.5).long(), W)
    return t[:, :, iy, ix]


def _zoom_size(t, a, b, dev):
    """core zoom_image_size: 全体を (ht,wt) へ order=1 で標本化し、キャンバス左上へ置く。"""
    H, W = t.shape[2], t.shape[3]
    ht, wt = max(1, int(round(H * (0.5 + a)))), max(1, int(round(W * (0.5 + b))))
    # 画素中心合わせ(CPU と同じ、敵対的検証 2026-11-05 P9): 出力 o -> 入力 (o+0.5)·H/ht - 0.5
    ys = (torch.arange(ht, dtype=torch.float64, device=dev) + 0.5) * (H / ht) - 0.5
    xs = (torch.arange(wt, dtype=torch.float64, device=dev) + 0.5) * (W / wt) - 0.5
    y0, x0 = torch.floor(ys), torch.floor(xs)
    fy, fx = (ys - y0).float().view(1, 1, -1, 1), (xs - x0).float().view(1, 1, 1, -1)
    y0, x0 = y0.long(), x0.long()
    y1, x1 = _sym_map(y0 + 1, H), _sym_map(x0 + 1, W)
    y0, x0 = _sym_map(y0, H), _sym_map(x0, W)
    rows = (1 - fy) * t.index_select(2, y0) + fy * t.index_select(2, y1)
    small = (1 - fx) * rows.index_select(3, x0) + fx * rows.index_select(3, x1)
    out = torch.zeros_like(t)
    hh, ww = min(H, ht), min(W, wt)
    out[:, :, :hh, :ww] = small[:, :, :hh, :ww]
    return out


# 色(B,3,H,W)。灰色入力(C=1)は core の _to_color と同じく 3 チャンネルへ複製する。
def _color_in(t):
    return _x01(t.repeat(1, 3, 1, 1) if t.shape[1] == 1 else t[:, :3])


def _rgb_to_gray(t, a, b, dev):
    c = _color_in(t)
    return c[:, 0:1] * 0.299 + c[:, 1:2] * 0.587 + c[:, 2:3] * 0.114


def _linear_trans_color(t, a, b, dev):
    c = _color_in(t)
    th = np.pi * a
    M = np.array([[0.6 + 0.4 * np.cos(th), 0.2, 0.2], [0.2, 0.6 + 0.4 * np.sin(th), 0.2],
                  [0.2, 0.2, 0.6]], np.float64)
    M = torch.as_tensor(M / M.sum(1, keepdims=True), dtype=torch.float32, device=dev)
    return torch.einsum("ij,bjhw->bihw", M, c)


def _principal_comp(t, a, b, dev):
    """core _principal_comp。固有ベクトルの符号を core と揃えるため、共分散は device 上で f64、
    固有分解は host の numpy(LAPACK)で解く。f32 だと縮退成分の雑音 / (ptp+1e-8) が増幅される。"""
    c = _color_in(t).double()
    B, _, H, W = c.shape
    out = []
    for i in range(B):
        X = c[i].view(3, -1)
        Xm = X - X.mean(dim=1, keepdim=True)
        cov = (Xm @ Xm.T / (Xm.shape[1] - 1)).detach().cpu().numpy()
        w, vec = np.linalg.eigh(cov)
        vec = torch.as_tensor(vec[:, np.argsort(w)[::-1]].copy(), dtype=torch.float64, device=dev)
        proj = vec.T @ Xm
        lo = proj.amin(dim=1, keepdim=True)
        ptp = proj.amax(dim=1, keepdim=True) - lo
        out.append(((proj - lo) / (ptp + 1e-8)).view(3, H, W).float())
    return torch.stack(out)


# n-ary(io = [(B,1,H,W), ...])。単入力の ACCEL とは別表。mask は io[1] がそのまま核になる。
def _nary_add(io, a, b, dev):
    return ((_x01(io[0]) + _x01(io[1])) * (0.5 + a) + (b - 0.5)).clamp(0, 1)


def _nary_sub(io, a, b, dev):
    return ((_x01(io[0]) - _x01(io[1])) * (0.5 + a) + b).clamp(0, 1)


def _nary_mult(io, a, b, dev):
    return (_x01(io[0]) * _x01(io[1]) * (0.5 + 1.5 * a) + (b - 0.5)).clamp(0, 1)


def _nary_div(io, a, b, dev):
    return (_x01(io[0]) / _x01(io[1]).clamp_min(1e-3) * (0.1 + 0.9 * a)).clamp(0, 1)


def _nary_abs_diff(io, a, b, dev):
    return ((_x01(io[0]) - _x01(io[1])).abs() * (0.5 + 1.5 * a)).clamp(0, 1)


def _nary_max(io, a, b, dev):
    return torch.maximum(_x01(io[0]), _x01(io[1]))


def _nary_min(io, a, b, dev):
    return torch.minimum(_x01(io[0]), _x01(io[1]))


def _nary_convol(io, a, b, dev):
    """core _convol: 相関(F.conv2d は反転しない = 相関)。mask は 1 枚目の mask を全バッチに使う。
    大きいマスクは ndimage.correlate が O(N·mask) なのに対し GPU は 1 回の conv2d。"""
    x, ker = _x01(io[0]), io[1][0, 0]
    ker = ker / (ker.abs().sum() + 1e-8)
    r0, r1 = ker.shape[0] // 2, ker.shape[1] // 2
    p = _pad_sym(_pad_sym(x, r1, 3), r0, 2)
    return F.conv2d(p, ker.view(1, 1, *ker.shape))[:, :, :x.shape[2], :x.shape[3]].clamp(0, 1)


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
    # Batch 2(2026-08-31): image→region 関門。otsu で GPU 区間の分断が消える
    "otsu": (_otsu, "otsu", "binary_threshold"),
    "dyn_threshold": (_dyn_threshold, "dyn_threshold", "dyn_threshold"),
    "canny": (_canny, "canny", "edges_image"),
    # ★2026-10-02: HALCON 名は ``local_max``(画素精度のマスク)。以前は ``local_max_sub_pix`` と書いていた。
    "local_max": (_local_max, "local_max", "local_max"),
    "adaptive_gauss_thresh": (_adaptive_gauss, "adaptive_gauss_thresh", "local_threshold"),
    # Batch 3: 二値 reconstruction(fill_up は fill_holes と同一 core 実装の twin)
    "fill_holes": (_fill_holes_bin, "fill_holes", "fill_up"),
    "fill_up": (_fill_holes_bin, "fill_up", "fill_up"),
    # bilateral(25 シフト反復 = 計算重で GPU 向き)
    "bilateral": (_bilateral, "bilateral", "bilateral_filter"),
    # GPU 第 2 便 D'(2026-11-02): 実寸 bench で >= 5x の 7 op(docs/perf/gpu_fill_2026-11-02.md)
    "corner_response": (_corner_response, "corner_response", "points_harris"),
    "anisotropic_diffusion": (_aniso_diffusion, "anisotropic_diffusion", "anisotropic_diffusion"),
    "bandpass_image": (_bandpass, "bandpass_image", "bandpass_image"),
    "binomial_filter": (_binomial, "binomial_filter", "binomial_filter"),
    "dc_local_contrast_norm": (_local_contrast_norm, "dc_local_contrast_norm", ""),
    "cos_image": (_cos_image, "cos_image", "cos_image"),
    "companding_mu_law": (_companding_mu_law, "companding_mu_law", ""),
    # rolling ball(非平坦な収縮、窓の画素数だけずらして最小)。「FA — scratch」の途中の CPU の段だった
    "sk_rolling_ball": (_rolling_ball, "sk_rolling_ball", ""),
}


# ── HALCON twin 別名(2026-08-31)────────────────────────────────────────────
# registry には core op と同一実装の「HALCON 名の twin」が多数ある。bridge の
# _seg_kind は core 名の完全一致で GPU 判定するため、twin にも ACCEL 行が要る。
# 全件、構造化 blob + PARITY_AB 全点の自動探索で core と数値一致を実測してから
# 登録した(塩ノイズ二値は erosion 全消え等の縮退で偽陽性を出すため使わない。
# r3_label_to_region は灰色ラベル画像でレベル選択という別動作をするため棄却)。
def _regize(fn):
    """二値化(>0.5)してから既存 kernel を通す region 別名用ラッパ。
    core の region op は _bin(v)=v>0.5 で始まるので、灰色入力でも一致する。"""
    def g(t, a, b, dev):
        return fn((t > 0.5).float(), a, b, dev)
    return g


def _reg_copy(t, a, b, dev):
    """union1: 全連結成分の和 = 前景マスクそのもの(二値化コピー)。"""
    return (t > 0.5).float()


def _reg_invert(t, a, b, dev):
    """complement: 1 - 前景マスク。"""
    return 1.0 - (t > 0.5).float()


_TWIN_ALIASES = (
    # (registry 名, kernel 関数, halcon 名)
    ("bit_not", _invert, "bit_not"),
    ("deviation_image", _std_filter, "deviation_image"),
    ("diff_of_gauss", _dog, "diff_of_gauss"),
    ("dual_rank", _percentile, "dual_rank"),
    ("eliminate_min_max", _median, "eliminate_min_max"),
    ("equ_histo_image", _equalize, "equ_histo_image"),
    ("gauss_filter", _gaussian, "gauss_filter"),
    ("gauss_image", _gaussian, "gauss_image"),
    ("gray_bothat", _bothat, "gray_bothat"),
    ("gray_closing", _close_rect, "gray_closing"),
    ("gray_closing_rect", _close_rect, "gray_closing_rect"),
    ("gray_dilation", _dilate_rect, "gray_dilation"),
    ("gray_dilation_rect", _dilate_rect, "gray_dilation_rect"),
    ("gray_erosion", _erode_rect, "gray_erosion"),
    ("gray_erosion_rect", _erode_rect, "gray_erosion_rect"),
    ("gray_opening", _open_rect, "gray_opening"),
    ("gray_opening_rect", _open_rect, "gray_opening_rect"),
    ("gray_range_rect", _range_rect, "gray_range_rect"),
    ("gray_tophat", _tophat, "gray_tophat"),
    ("invert_image", _invert, "invert_image"),
    ("mean_image", _mean, "mean_image"),
    ("median_image", _median, "median_image"),
    ("median_separate", _median, "median_separate"),
    ("median_weighted", _median, "median_weighted"),
    ("prewitt_amp", _prewitt, "prewitt_amp"),
    ("projective_trans_image", _projective_warp, "projective_trans_image"),
    ("projective_trans_image_size", _projective_warp, "projective_trans_image_size"),
    ("rank_image", _percentile, "rank_image"),
    ("rank_rect", _percentile, "rank_rect"),
    ("roberts", _roberts, "roberts"),
    ("scale_image", _scale, "scale_image"),
    ("sobel_amp", _sobel, "sobel_amp"),
    ("sobel_dir", _grad_dir, "sobel_dir"),
    ("local_threshold", _adaptive_gauss, "local_threshold"),
    ("nonmax_suppression_amp", _local_max, "nonmax_suppression_amp"),
    # region sort(core は _bin(v)=v>0.5 で開始するので、灰色入力とも一致する)
    ("dilation_rectangle1", _regize(_dilate_rect), "dilation_rectangle1"),
    ("dilation_seq", _reg_dilate, "dilation_seq"),
    ("erosion_seq", _reg_erode, "erosion_seq"),
    ("invert_region", _reg_invert, "complement"),
    ("opening_golay", _opening_circle, "opening_golay"),
    ("remove_noise_region", _opening_circle, "remove_noise_region"),
    ("r2_union1", _reg_copy, "union1"),
)

for _rname, _fn, _hal in _TWIN_ALIASES:
    _key = _rname if _rname not in ACCEL else _rname + "@twin"
    ACCEL[_key] = (_fn, _rname, _hal)
del _rname, _fn, _hal, _key

# ── GPU 第 3 便の候補表(core 名 -> (kernel, HALCON 名))。ACCEL に入るのは FILL3_ADOPTED だけ。
#    採否は tools/gen_gpu_fill3_report.py が実測ログから判定し、この表と食い違うと門が落ちる。
FILL3_KERNELS = {
    "abs_image": (_abs_image, "abs_image"), "acos_image": (_acos_image, "acos_image"),
    "asin_image": (_asin_image, "asin_image"), "atan_image": (_atan_image, "atan_image"),
    "exp_image": (_exp_image, "exp_image"), "log_image": (_log_image, "log_image"),
    "sin_image": (_sin_image, "sin_image"), "sqrt_image": (_sqrt_image, "sqrt_image"),
    "tan_image": (_tan_image, "tan_image"), "gamma_image": (_gamma_image, "gamma_image"),
    "f2_lut_trans": (_lut_trans, "lut_trans"), "median_rect": (_median_rect, "median_rect"),
    "mirror_image": (_mirror_image, "mirror_image"),
    "it_convert_image_type": (_convert_image_type, "convert_image_type"),
    "it_crop_domain": (_crop_domain, "crop_domain"), "it_crop_part": (_crop_part, "crop_part"),
    "it_crop_rectangle1": (_crop_rectangle1, "crop_rectangle1"),
    "gray_erosion_shape": (_gray_erosion_shape, "gray_erosion_shape"),
    "gray_dilation_shape": (_gray_dilation_shape, "gray_dilation_shape"),
    "gray_opening_shape": (_gray_opening_shape, "gray_opening_shape"),
    "gray_closing_shape": (_gray_closing_shape, "gray_closing_shape"),
    "texture_laws": (_texture_laws, "texture_laws"), "derivate_gauss": (_derivate_gauss, "derivate_gauss"),
    "affine_trans_image": (_affine_warp, "affine_trans_image"), "affine_warp": (_affine_warp, "affine_trans_image"),
    "affine_trans_image_size": (_affine_warp, "affine_trans_image_size"),
    "rotate_image": (_rotate_image, "rotate_image"), "rotate_img": (_rotate_image, "rotate_image"),
    "zoom_image_factor": (_zoom_factor, "zoom_image_factor"), "rescale_img": (_rescale_img, "zoom_image_factor"),
    "zoom_image_size": (_zoom_size, "zoom_image_size"),
    "rgb1_to_gray": (_rgb_to_gray, "rgb1_to_gray"), "rgb3_to_gray": (_rgb_to_gray, "rgb3_to_gray"),
    "linear_trans_color": (_linear_trans_color, "linear_trans_color"),
    "principal_comp": (_principal_comp, "principal_comp"),
}
#: 実寸 2048² x50 で >= 5.0x かつ parity < 5e-3(docs/perf/gpu_fill3_2026-11-02.md)
FILL3_ADOPTED = (
    "tan_image", "f2_lut_trans", "median_rect", "it_crop_part", "it_crop_rectangle1", "texture_laws",
    "derivate_gauss", "affine_trans_image", "affine_warp", "affine_trans_image_size",
    "rotate_image", "rotate_img", "zoom_image_factor", "principal_comp",
)
ACCEL.update({(n if n not in ACCEL else n + "@twin"): (FILL3_KERNELS[n][0], n, FILL3_KERNELS[n][1])
              for n in FILL3_ADOPTED})

NARY_KERNELS = {
    "add_image": _nary_add, "sub_image": _nary_sub, "mult_image": _nary_mult, "div_image": _nary_div,
    "abs_diff_image": _nary_abs_diff, "max_image": _nary_max, "min_image": _nary_min, "convol_image": _nary_convol,
}
NARY_ADOPTED = ("convol_image",)
#: core n-ary 名 -> kernel。``fullseye.apply([x0, x1], name, device=...)`` の GPU 経路。
NARY_ACCEL = {n: NARY_KERNELS[n] for n in NARY_ADOPTED}


def run_nary(name, inputs, a=0.5, b=0.4, device="cpu"):
    """n-ary op を 1 組の入力で走らせる。第 2 入力は形が違ってよい(convol_image の核)。"""
    io = [_to_batch([x], device) for x in inputs]
    return _from_batch(NARY_ACCEL[name](io, a, b, device).clamp(0, 1))[0]


# ── 領域の解析(2026-11-03): 連結成分のラベル付け + 領域ごとの集計 ─────────────────────────
# 実装と門は accel_label(``tests/test_accel_label.py``)。採用は実測の門(一致・定数でない・単独 5 倍 /
# 常駐 1 倍)を通った op だけ(``accel_label.ADOPTED``、根拠 ``fullseye/data/GPU_ACCEL_USE.json``)。
# REDUCERS(領域 -> 特徴・ベクトル)は 0..1 に切らず 1 枚ごとの np の値を返し、鎖では区間の最後に置く。
REDUCERS: frozenset = frozenset()
if _HAS_TORCH:
    import accel_label as _accel_label
    for _key, _row in _accel_label.table().items():
        if _row[1] in _accel_label.ADOPTED:
            ACCEL[_key] = _row
    REDUCERS = frozenset(k for k in _accel_label.REDUCERS if k in ACCEL)
    del _key, _row


def _b_falls_back(name, a, b) -> bool:
    """accel op *name* の kernel が ``(a, b)`` を忠実に写せず、core に回すべきか。

    ★敵対的検証 2026-11-05 第 2 巡 T6: ``b > 0.5`` で端の扱い(``ops._border``)・構造要素の形
    (``ops._se``)を選ぶ core op(``fast._KNOB_B_OPTIONED``)に対し、ここの kernel は**歴史的な規約
    (reflect / 正方形)しか実装していない**。以前は ``b`` を黙って無視し、``device="cuda"`` だけ答えが
    変わっていた(a=0.5 で median 0.528・mean_box 0.311・gaussian 0.265・gdilate 0.424 …)。
    CPU の高速 twin(``fast.apply_fast``)と同じ判定で、選択肢が新しい間は core へ回す
    —— 速くはならないが、答えは ``device="cpu"`` と 1 ビットも変わらない。
    """
    row = ACCEL.get(name)
    if row is None:
        return False
    import fast
    return fast._b_selects_a_new_option(row[1], a, b)


def _core_batch(name, imgs, a, b):
    """:func:`_b_falls_back` の受け皿: core op を 1 枚ずつ float64 で走らせ、kernel と同じく 0..1 に切る。"""
    import ops
    core = ops.RT[ACCEL[name][1]]
    return [np.clip(np.asarray(core(np.asarray(im, np.float64).copy(), a, b), np.float64), 0.0, 1.0)
            for im in imgs]


def run_batch(name, imgs, a=0.5, b=0.4, device="cpu"):
    """Run one accel op over a batch of images; returns a list of 2-D arrays.

    :data:`REDUCERS`(領域 -> 特徴・ベクトル)は 1 枚ごとの ``np.float64`` / 1-D 配列のリスト(0..1 に切らない)。
    ``b`` が kernel の実装していない選択肢を選ぶとき(:func:`_b_falls_back`)は core で答える。
    """
    fn = ACCEL[name][0]
    if _b_falls_back(name, a, b):
        return _core_batch(name, imgs, a, b)
    t = _to_batch(imgs, device)
    if name in REDUCERS:
        return list(fn(t, a, b, device))
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
    steps = list(steps)
    for i, (name, a, b) in enumerate(steps):
        if name in REDUCERS:
            # 特徴を返す段は区間の最後(次の段は特徴を受ける op で、GPU の区間には載らない)
            if i != len(steps) - 1:
                raise ValueError("accel reducer %r must be the last step of a resident segment" % name)
            return list(ACCEL[name][0](t, a, b, device))
        if _b_falls_back(name, a, b):
            # 区間の途中でも core へ(1 往復増えるが、b の選択を無視するよりよい —— T6)
            t = _to_batch(_core_batch(name, _from_batch(t), a, b), device)
            continue
        t = ACCEL[name][0](t, a, b, device).clamp(0, 1)
    return _from_batch(t)


def _interior_max(ref, got, m=3):
    """Max abs diff ignoring an m-px border (pooling/reflect borders differ)."""
    return float(np.max(np.abs(ref[m:-m, m:-m] - got[m:-m, m:-m]))) if ref.shape[0] > 2 * m else \
        float(np.max(np.abs(ref - got)))


# parity の (a, b) スイープ点。旧版は (0.5, 0.4) の 1 点だけで、a>=0.75 のとき
# _k(a)=9(半径 4px)が固定 3px マージンに食い込む穴があった(2026-08-31 修正)。
#: interior 差の判定閾値。★2026-09-20(GenSpark 第 32・33 報 N116): 0.0002 の差に "exact" と出て、
#: 語が実測と矛盾していた —— 判定は閾値で決まるので、語に閾値を添える。
PARITY_TOL = 5e-3
PARITY_CLOSE = 5e-2


def parity_flag(inter: float) -> str:
    """Label for an interior max-difference: ``match(<5e-3)`` / ``close(<5e-2)`` / ``differ(>=5e-2)``."""
    if inter < PARITY_TOL:
        return "match(<%g)" % PARITY_TOL
    if inter < PARITY_CLOSE:
        return "close(<%g)" % PARITY_CLOSE
    return "differ(>=%g)" % PARITY_CLOSE


PARITY_AB = ((0.5, 0.4), (0.25, 0.75), (0.8, 0.2), (0.0, 0.5), (1.0, 0.9))


def parity(device="cpu"):
    """Difftest every accel op against the CORE registry op it reproduces.

    マージンは a ごとにカーネル半径 +1(最低 3px)。symmetric パディング修正後の
    conv 系 op は full-image でも一致するが、pooling 系(erode/dilate 等)は端の
    規約差が原理的に残るため interior 判定を維持する(accel_vol._op_margin と同思想)。
    """
    import ops
    rng = np.random.default_rng(7)
    imgs = [np.clip(rng.random((64, 64)) * 0.6 + 0.2 * (np.mgrid[0:64, 0:64][1] / 64), 0, 1)
            for _ in range(4)]
    # 敵対レビュー 2026-08-31 P1/P3: 乱数画像だけでは (a) 平坦入力での _norm 系の
    # 雑音増幅、(b) f32 丸めによる otsu の bin ずれ、を捕捉できない
    imgs.append(np.full((64, 64), 0.42))                      # 定数(平坦)画像
    imgs.append(np.round(imgs[0] * 255.0) / 255.0)            # uint8 量子化画像
    rows = []
    # 方向(角度)op は値が mod 1 の円環量: 勾配 ~0 の画素で atan2 が −π/+π に
    # 割れると線形差は 1.0 になるが 0.0 と 1.0 は同一方向。円環距離で測る
    circular = {"gradient_direction", "sobel_dir"}
    for name, (fn, core_name, halcon) in ACCEL.items():
        if core_name not in ops.RT:
            continue
        full = inter = 0.0
        if name in REDUCERS:
            # 特徴は 0..1 に切らずに比べる(個数・面積は整数で完全一致、形の量は相対差)
            for a, b in PARITY_AB:
                got = run_batch(name, imgs, a, b, device)
                for i, im in enumerate(imgs):
                    ref = np.asarray(ops.RT[core_name](im.copy(), a, b), np.float64)
                    g = np.asarray(got[i], np.float64)
                    d = float(np.max(np.abs(ref - g) / np.maximum(1.0, np.abs(ref)))) if ref.shape == g.shape else 1.0
                    full = inter = max(full, d)
            rows.append((name, halcon, full, inter))
            continue
        for a, b in PARITY_AB:
            m = max(3, _k(a) // 2 + 1)
            got = run_batch(name, imgs, a, b, device)
            for i, im in enumerate(imgs):
                ref = np.clip(ops.RT[core_name](im.copy(), a, b), 0, 1)
                g = np.asarray(got[i])
                d = np.abs(ref - g)
                if name in circular:
                    d = np.minimum(d, 1.0 - d)
                binary = (set(np.unique(ref)) <= {0.0, 1.0}
                          and set(np.unique(g)) <= {0.0, 1.0})
                if binary:
                    # 二値出力 op は max-diff だと「刃の上の 1 画素」(量子化入力の
                    # 有理数同値 — core 自身の答えが f64 丸め雑音で決まる不定画素)
                    # で即 1.0 になる。系統誤差は不一致率で十分捕まる(P2 の
                    # ramp+b=0.5 は 50% 不一致)ので、二値は不一致率で測る
                    full = max(full, float(d.mean()))
                    inter = max(inter, float(d[m:-m, m:-m].mean())
                                if d.shape[0] > 2 * m else float(d.mean()))
                else:
                    full = max(full, float(np.max(d)))
                    inter = max(inter, _interior_max(d, np.zeros_like(d), m))
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
    ok = sum(1 for _, _, _, inter in rows if inter < PARITY_TOL)
    print("parity vs core registry op  (full = incl. borders, interior = 3px-inset):")
    for name, halcon, full, inter in sorted(rows, key=lambda r: -r[3]):
        print("  %-20s (%-18s)  full=%.4f interior=%.4f  %s" % (name, halcon or "-", full, inter, parity_flag(inter)))
    print("interior-faithful (<5e-3): %d / %d  — borders differ only by reflect/pool convention"
          % (ok, len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
