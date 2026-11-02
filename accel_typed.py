"""型付き op(sinogram / flow2d / points / voxel …)の GPU 経路(第 3 便, 2026-11-02)。

``accel.ACCEL`` は ``fn(batch, a, b, device)`` という 2 つまみ画像 op の表で、引数が型付きの op は
載らない。ここは ``accel_seam`` の継ぎ目で **core の入力検証をそのまま使い、計算核だけ** torch へ
差し替える::

    sino = accel_typed.call("radon_transform", image, device="cuda")

``TYPED_ACCEL`` に載るのは実寸 >= 5x と parity を実測した op だけ(``TYPED_ADOPTED``)。候補の核と
不採用の理由は ``docs/perf/gpu_fill3_2026-11-02.md``。parity は値域が [0,1] でないので
``max|cpu-gpu| / max|cpu| < 5e-3``(相対)で測る。
"""
from __future__ import annotations

import numpy as np

import accel_seam

try:
    import torch
    _HAS_TORCH = True
except Exception:  # pragma: no cover
    _HAS_TORCH = False


def _bilinear_zero(im, xs, ys):
    """tomography._bilinear_gather: 枠外の角は寄与 0(クランプしない)。"""
    h, w = im.shape
    x0, y0 = torch.floor(xs), torch.floor(ys)
    fx, fy = (xs - x0).float(), (ys - y0).float()
    x0, y0 = x0.long(), y0.long()
    out = 0.0
    for dy in (0, 1):
        for dx in (0, 1):
            xi, yi = x0 + dx, y0 + dy
            ok = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
            wgt = (fx if dx else 1.0 - fx) * (fy if dy else 1.0 - fy)
            out = out + im[yi.clamp(0, h - 1), xi.clamp(0, w - 1)] * wgt * ok
    return out


def _ray_grid(h, w, n_det, oversample, dev):
    s = torch.arange(n_det, dtype=torch.float64, device=dev) - (n_det - 1) / 2.0
    t_max = 0.5 * np.hypot(h, w) + 1.0
    n_t = int(np.ceil(2.0 * t_max * oversample)) + 1
    t_np = np.linspace(-t_max, t_max, n_t)
    return s, torch.as_tensor(t_np, device=dev), float(t_np[1] - t_np[0]), n_t


def k_project(dev):
    def fn(img, angles_rad, n_det, oversample=1):
        im = torch.as_tensor(np.asarray(img, np.float32), device=dev)
        h, w = im.shape
        s, t, dt, n_t = _ray_grid(h, w, n_det, oversample, dev)
        cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
        ang = torch.as_tensor(np.asarray(angles_rad, np.float64), device=dev)
        chunk = max(1, int(1.5e8 // (n_det * n_t)))
        out = []
        for i in range(0, ang.numel(), chunk):
            a = ang[i:i + chunk].view(-1, 1, 1)
            ca, sa = torch.cos(a), torch.sin(a)
            xs = s[None, :, None] * ca - t[None, None, :] * sa + cx
            ys = s[None, :, None] * sa + t[None, None, :] * ca + cy
            out.append(_bilinear_zero(im, xs, ys).double().sum(2) * dt)
        return torch.cat(out).cpu().numpy()
    return fn


def _bp_rows(rows, ang, size, n_det, dev):
    """rows (B,n_det) を角度 ang (B,) で (B,size,size) へ戻す(_backproject の 1 束)。"""
    grid = torch.arange(size, dtype=torch.float64, device=dev) - (size - 1) / 2.0
    a = ang.view(-1, 1, 1)
    s = grid[None, None, :] * torch.cos(a) + grid[None, :, None] * torch.sin(a) + (n_det - 1) / 2.0
    j0 = torch.floor(s)
    f = (s - j0).float()
    j0 = j0.long()
    ok = (j0 >= 0) & (j0 + 1 < n_det)
    jc = j0.clamp(0, n_det - 2).view(ang.numel(), -1)
    v0 = rows.gather(1, jc).view_as(f)
    v1 = rows.gather(1, jc + 1).view_as(f)
    return (v0 * (1.0 - f) + v1 * f) * ok


def k_backproject(dev):
    def fn(sino, angles_rad, size):
        n_det = sino.shape[1]
        rows = torch.as_tensor(np.asarray(sino, np.float32), device=dev)
        ang = torch.as_tensor(np.asarray(angles_rad, np.float64), device=dev)
        acc = torch.zeros((size, size), dtype=torch.float64, device=dev)
        chunk = max(1, int(1.2e8 // (size * size)))
        for i in range(0, ang.numel(), chunk):
            acc += _bp_rows(rows[i:i + chunk], ang[i:i + chunk], size, n_det, dev).double().sum(0)
        return acc.cpu().numpy()
    return fn


def k_filter(dev):
    def fn(sino, h_spec, n_pad):
        x = torch.as_tensor(np.asarray(sino, np.float64), device=dev)
        n_det = x.shape[1]
        p = torch.zeros((x.shape[0], n_pad), dtype=torch.float64, device=dev)
        p[:, :n_det] = x
        h = torch.as_tensor(np.asarray(h_spec), device=dev)
        return torch.fft.irfft(torch.fft.rfft(p, dim=1) * h[None, :], n=n_pad, dim=1)[:, :n_det].cpu().numpy()
    return fn


def k_sart(dev):
    def fn(x0, sino, rad, sz, n_det, n_it, lam, nonnegative, eps):
        x = torch.as_tensor(np.asarray(x0, np.float64), device=dev)
        y = torch.as_tensor(np.asarray(sino, np.float64), device=dev)
        s, t, dt, _n = _ray_grid(sz, sz, n_det, 1, dev)
        cc = (sz - 1) / 2.0
        ang = torch.as_tensor(np.asarray(rad, np.float64), device=dev)
        ones = torch.ones((sz, sz), dtype=torch.float32, device=dev)
        n_a = ang.numel()
        geom = []
        for i in range(n_a):
            ca, sa = torch.cos(ang[i]), torch.sin(ang[i])
            geom.append((s[:, None] * ca - t[None, :] * sa + cc, s[:, None] * sa + t[None, :] * ca + cc))
        row_sums = [_bilinear_zero(ones, xs, ys).double().sum(1) * dt for xs, ys in geom]
        one_row = torch.ones((1, n_det), dtype=torch.float32, device=dev)
        col_sums = [_bp_rows(one_row, ang[i:i + 1], sz, n_det, dev)[0].double().clamp_min(eps) for i in range(n_a)]
        for _ in range(n_it):
            for i in range(n_a):
                xs, ys = geom[i]
                fp = _bilinear_zero(x.float(), xs, ys).double().sum(1) * dt
                resid = (y[i] - fp) / row_sums[i].clamp_min(eps)
                bp = _bp_rows(resid.float()[None], ang[i:i + 1], sz, n_det, dev)[0].double()
                x = x + lam * bp / col_sums[i]
            if nonnegative:
                x = x.clamp_min(0.0)
        return x.cpu().numpy()
    return fn


_PIV_EPS = 1e-12


def _parabolic_v(cm, c0, cp):
    den = 2.0 * (cm - 2.0 * c0 + cp)
    return torch.where(den.abs() < _PIV_EPS, torch.zeros_like(den), (cm - cp) / den)


def _subpixel_v(corr, pi, pj, axis, mode, win):
    """pivops._subpixel のベクトル版。端の峰は 0、gauss3 の対数不能は放物線へ落とす。"""
    n = torch.arange(corr.shape[0], device=corr.device)
    p = pi if axis == 0 else pj
    inner = (p > 0) & (p < win - 1)
    pc = p.clamp(1, win - 2)
    if axis == 0:
        cm, c0, cp = corr[n, pc - 1, pj], corr[n, pc, pj], corr[n, pc + 1, pj]
    else:
        cm, c0, cp = corr[n, pi, pc - 1], corr[n, pi, pc], corr[n, pi, pc + 1]
    if mode == "gauss3":
        pos = (cm > 0) & (c0 > 0) & (cp > 0)
        lm, l0, lp = (torch.log(torch.where(pos, v, torch.ones_like(v))) for v in (cm, c0, cp))
        den = 2.0 * (lm - 2.0 * l0 + lp)
        g = torch.where(den.abs() < _PIV_EPS, torch.zeros_like(den), (lm - lp) / den)
        val = torch.where(pos, g, _parabolic_v(cm, c0, cp))
    elif mode == "parabolic":
        val = _parabolic_v(cm, c0, cp)
    else:
        tot = cm + c0 + cp
        val = torch.where(tot.abs() < _PIV_EPS, torch.zeros_like(tot), (cp - cm) / tot)
    return torch.where(inner, val, torch.zeros_like(val))


def _peak_ratio_v(search, pi, pj, top, win):
    """pivops._peak_ratio のベクトル版: 峰の 3x3 を除いた最大に対する比。"""
    idx = torch.arange(win, device=search.device)
    near = ((idx[None, :, None] - pi[:, None, None]).abs() <= 1) & ((idx[None, None, :] - pj[:, None, None]).abs() <= 1)
    second = search.masked_fill(near, -np.inf).amax(dim=(1, 2))
    bad = ~torch.isfinite(second) | (second <= 0)
    return torch.where(bad, torch.full_like(top, np.inf), top / second)


def _peak_batch(corr, keep_t, peak, win):
    search = corr if keep_t is None else corr.masked_fill(~keep_t, -np.inf)
    k = search.view(corr.shape[0], -1).argmax(dim=1)
    pi, pj = k // win, k % win
    n = torch.arange(corr.shape[0], device=corr.device)
    top = corr[n, pi, pj]
    c0 = win // 2
    dy = (pi - c0).double() + _subpixel_v(corr, pi, pj, 0, peak, win)
    dx = (pj - c0).double() + _subpixel_v(corr, pi, pj, 1, peak, win)
    return dy, dx, _peak_ratio_v(search, pi, pj, top, win), top


def _windows(img, r, c, win, dev):
    off = torch.arange(win, device=dev)
    return img[(r[:, None] + off)[:, :, None], (c[:, None] + off)[:, None, :]]


def k_piv(dev):
    def fn(A, B, rows, cols, win, pred, taper, weight, keep, subtract_mean, peak, h, w):
        At = torch.as_tensor(np.asarray(A, np.float64), device=dev)
        Bt = torch.as_tensor(np.asarray(B, np.float64), device=dev)
        rr, cc = np.meshgrid(rows, cols, indexing="ij")
        ra, ca = rr.ravel().astype(np.int64), cc.ravel().astype(np.int64)
        if pred is None:
            rb, cb = ra, ca
        else:
            rb = np.minimum(np.maximum(ra + pred[0].ravel(), 0), h - win)
            cb = np.minimum(np.maximum(ca + pred[1].ravel(), 0), w - win)
        sr, sc = rb - ra, cb - ca
        tp = None if taper is None else torch.as_tensor(taper, device=dev)
        wt = None if weight is None else torch.as_tensor(weight, device=dev)
        kt = None if keep is None else torch.as_tensor(keep, device=dev)
        ra, ca, rb, cb = (torch.as_tensor(v, device=dev) for v in (ra, ca, rb, cb))
        res = []
        for i in range(0, ra.numel(), 8192):
            j = i + 8192
            xa, xb = _windows(At, ra[i:j], ca[i:j], win, dev), _windows(Bt, rb[i:j], cb[i:j], win, dev)
            if subtract_mean:
                xa = xa - xa.mean(dim=(1, 2), keepdim=True)
                xb = xb - xb.mean(dim=(1, 2), keepdim=True)
            if tp is not None:
                xa, xb = xa * tp, xb * tp
            corr = torch.fft.fftshift(torch.fft.irfft2(
                torch.conj(torch.fft.rfft2(xa)) * torch.fft.rfft2(xb), s=(win, win)), dim=(1, 2))
            if wt is not None:
                corr = corr / wt
            dy, dx, pr, top = _peak_batch(corr, kt, peak, win)
            bad = ~torch.isfinite(top) | (top <= 0)
            nan = torch.full_like(dy, float("nan"))
            res.append((torch.where(bad, nan, dy), torch.where(bad, nan, dx), torch.where(bad, nan, pr)))
        fy, fx, pr = (torch.cat([r[q] for r in res]).cpu().numpy() for q in range(3))
        shp = (rows.size, cols.size)
        return (np.stack([(fy + sr).reshape(shp), (fx + sc).reshape(shp)]), pr.reshape(shp))
    return fn


def k_piv_ensemble(dev):
    def fn(frames, rows, cols, win, taper, weight, keep, peak):
        rr, cc = np.meshgrid(rows, cols, indexing="ij")
        ra = torch.as_tensor(rr.ravel().astype(np.int64), device=dev)
        ca = torch.as_tensor(cc.ravel().astype(np.int64), device=dev)
        tp = None if taper is None else torch.as_tensor(taper, device=dev)
        wt = None if weight is None else torch.as_tensor(weight, device=dev)
        kt = None if keep is None else torch.as_tensor(keep, device=dev)
        res = []
        for i in range(0, ra.numel(), 8192):
            r, c = ra[i:i + 8192], ca[i:i + 8192]
            prev = cross = None
            for fr in frames:
                x = _windows(torch.as_tensor(np.asarray(fr, np.float64), device=dev), r, c, win, dev)
                x = x - x.mean(dim=(1, 2), keepdim=True)
                if tp is not None:
                    x = x * tp
                sp = torch.fft.rfft2(x)
                if prev is not None:
                    term = torch.conj(prev) * sp
                    cross = term if cross is None else cross + term
                prev = sp
            acc = torch.fft.fftshift(torch.fft.irfft2(cross, s=(win, win)), dim=(1, 2))
            if wt is not None:
                acc = acc / wt
            dy, dx, pr, _top = _peak_batch(acc, kt, peak, win)
            res.append((dy, dx, pr))
        fy, fx, pr = (torch.cat([r[q] for r in res]).cpu().numpy() for q in range(3))
        shp = (rows.size, cols.size)
        return np.stack([fy.reshape(shp), fx.reshape(shp)]), pr.reshape(shp)
    return fn


def k_voxel_downsample(dev):
    def fn(P, voxel_size):
        p = torch.as_tensor(np.asarray(P, np.float64), device=dev)
        keys = torch.floor((p - p.amin(dim=0)) / float(voxel_size)).long()
        _u, inv = torch.unique(keys, dim=0, return_inverse=True) if _key_overflow(keys) else \
            torch.unique(_key_code(keys), return_inverse=True)
        m = int(inv.max()) + 1
        sums = torch.zeros((m, 3), dtype=torch.float64, device=dev)
        sums.index_add_(0, inv, p)
        cnt = torch.zeros(m, dtype=torch.float64, device=dev)
        cnt.index_add_(0, inv, torch.ones_like(inv, dtype=torch.float64))
        return (sums / cnt[:, None]).cpu().numpy()
    return fn


def _key_overflow(keys):
    span = (keys.amax(dim=0) + 1).tolist()
    return span[0] * span[1] * span[2] >= (1 << 62)


def _key_code(keys):
    # 辞書順を保つ 1 本の整数(core の np.unique(axis=0) と同じ順序になる)
    span = keys.amax(dim=0) + 1
    return (keys[:, 0] * span[1] + keys[:, 1]) * span[2] + keys[:, 2]


def k_occupancy(dev):
    def fn(P, lo, span, r):
        p = torch.as_tensor(np.asarray(P, np.float64), device=dev)
        lo_t = torch.as_tensor(np.asarray(lo, np.float64), device=dev)
        sp = torch.as_tensor(np.asarray(span, np.float64), device=dev)
        rr = torch.as_tensor(np.asarray(r, np.int64), device=dev)
        frac = (p - lo_t) / sp
        fi = frac[((frac >= 0.0) & (frac <= 1.0)).all(dim=1)]
        idx = torch.minimum((fi * rr.double()).long(), rr - 1)
        flat = (idx[:, 0] * rr[1] + idx[:, 1]) * rr[2] + idx[:, 2]
        g = torch.zeros(int(r[0] * r[1] * r[2]), dtype=torch.bool, device=dev)
        g[flat] = True
        return g.view(int(r[0]), int(r[1]), int(r[2])).cpu().numpy()
    return fn


def k_photometric(dev):
    def fn(Iv, Lpinv, H, W):
        I = torch.as_tensor(np.asarray(Iv, np.float32), device=dev)
        Lp = torch.as_tensor(np.asarray(Lpinv, np.float32), device=dev)
        g = Lp @ I
        albedo = torch.linalg.vector_norm(g, dim=0)
        good = albedo > 1e-8
        n = torch.where(good, g / albedo.clamp_min(1e-30), torch.zeros_like(g))
        n[2] = torch.where(good, n[2], torch.ones_like(n[2]))
        return (n.T.reshape(H, W, 3).cpu().numpy().astype(np.float64),
                albedo.reshape(H, W).cpu().numpy().astype(np.float64))
    return fn


def k_plane_sweep(dev):
    """plane_sweep_depth: 候補ごとに warp → |ref-warp| → box 平均、走行最小で (argmin 先頭一致)。
    cost 体積を host へ返さないのが要(D x H x W の往復が消える)。"""
    def fn(ref, src, Hs, depths, window, invalid_cost):
        r = torch.as_tensor(np.asarray(ref, np.float64), device=dev)
        s = torch.as_tensor(np.asarray(src, np.float64), device=dev)
        h, w = r.shape
        yy, xx = torch.meshgrid(torch.arange(h, dtype=torch.float64, device=dev),
                                torch.arange(w, dtype=torch.float64, device=dev), indexing="ij")
        best = torch.full((h, w), float("inf"), dtype=torch.float64, device=dev)
        arg = torch.zeros((h, w), dtype=torch.long, device=dev)
        anyf = torch.zeros((h, w), dtype=torch.bool, device=dev)
        win = int(window)
        pad = win // 2
        ker = torch.ones(1, 1, win, 1, dtype=torch.float64, device=dev)
        for i, H in enumerate(Hs):
            q = [float(H[j, 0]) * xx + float(H[j, 1]) * yy + float(H[j, 2]) for j in range(3)]
            bad = q[2].abs() < 1e-12
            z = torch.where(bad, torch.ones_like(q[2]), q[2])
            sx, sy = q[0] / z, q[1] / z
            ok = (~bad) & (sx >= 0) & (sx <= w - 1) & (sy >= 0) & (sy <= h - 1)
            x0 = torch.floor(sx).clamp(0, w - 2)
            y0 = torch.floor(sy).clamp(0, h - 2)
            fx, fy = sx - x0, sy - y0
            xi, yi = x0.long(), y0.long()
            warped = ((1 - fy) * ((1 - fx) * s[yi, xi] + fx * s[yi, xi + 1])
                      + fy * ((1 - fx) * s[yi + 1, xi] + fx * s[yi + 1, xi + 1]))
            cost = (r - warped).abs()
            if win > 1:
                fl = torch.where(ok, cost, torch.zeros_like(cost))[None, None]
                va = ok.double()[None, None]
                ksum = _box_zero(fl, win, pad, ker)
                cnt = _box_zero(va, win, pad, ker)
                c = torch.where(cnt >= 0.5, ksum / cnt.clamp_min(1.0),
                                torch.full_like(ksum, float("inf")))[0, 0]
            else:
                c = torch.where(ok, cost, torch.full_like(cost, float(invalid_cost)))
            anyf |= torch.isfinite(c)
            take = c < best
            best = torch.where(take, c, best)
            arg = torch.where(take, torch.full_like(arg, i), arg)
        return arg.cpu().numpy(), anyf.cpu().numpy()
    return fn


def _box_zero(x, win, pad, ker):
    y = torch.nn.functional.conv2d(torch.nn.functional.pad(x, (0, 0, pad, win - 1 - pad)), ker)
    return torch.nn.functional.conv2d(torch.nn.functional.pad(y, (pad, win - 1 - pad, 0, 0)), ker.transpose(2, 3))


def k_joint_bilateral(dev):
    def fn(v_safe, e_safe, contrib, radius, inv2s2, inv2r2):
        F = torch.nn.functional
        v = torch.as_tensor(np.asarray(v_safe, np.float32), device=dev)
        e = torch.as_tensor(np.asarray(e_safe, np.float32), device=dev)
        c = torch.as_tensor(np.asarray(contrib, np.float32), device=dev)
        H, W = v.shape
        pad = lambda x: F.pad(x[None, None], (radius,) * 4, mode="reflect")[0, 0]   # noqa: E731
        vp, ep, cp = pad(v), pad(e), pad(c)
        num = torch.zeros_like(v)
        den = torch.zeros_like(v)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                ws = float(np.exp(-(dy * dy + dx * dx) * inv2s2))
                sl = (slice(radius + dy, radius + dy + H), slice(radius + dx, radius + dx + W))
                de = ep[sl] - e
                w = ws * torch.exp(-(de * de) * inv2r2) * cp[sl]
                num += w * vp[sl]
                den += w
        return num.cpu().numpy().astype(np.float64), den.cpu().numpy().astype(np.float64)
    return fn


def k_temporal_bilateral(dev):
    def fn(frames, window, sigma_t, sigma_r):
        v = torch.as_tensor(np.asarray(frames, np.float32), device=dev)
        T = v.shape[0]
        age = torch.arange(window - 1, -1, -1, dtype=torch.float32, device=dev)
        wt_all = torch.exp(-(age * age) / (2.0 * sigma_t * sigma_t)).view(-1, 1, 1)
        out = []
        for t in range(T):
            w = v[max(0, t - window + 1):t + 1]
            cur = w[-1]
            dr = w - cur
            weight = wt_all[-w.shape[0]:] * torch.exp(-(dr * dr) / (2.0 * sigma_r * sigma_r))
            den = weight.sum(0)
            num = (weight * w).sum(0)
            out.append(torch.where(den > 0, num / torch.where(den > 0, den, torch.ones_like(den)), cur))
        return torch.stack(out).cpu().numpy().astype(np.float64)
    return fn


# op 名 -> (module, 関数名, その op が使う核 {継ぎ目名: 工場}, device 引数を直接取るか)
def _bind():
    tomo = {"tomography.project": k_project, "tomography.backproject": k_backproject,
            "tomography.filter": k_filter, "tomography.sart": k_sart}
    piv = {"pivops.correlate": k_piv, "pivops.ensemble": k_piv_ensemble}
    return {
        "radon_transform": ("tomography", "radon_transform", tomo, False),
        "radon_volume": ("tomography", "radon_volume", tomo, False),
        "backproject_sinogram": ("tomography", "backproject_sinogram", tomo, False),
        "filtered_backprojection": ("tomography", "filtered_backprojection", tomo, False),
        "fbp_volume": ("tomography", "fbp_volume", tomo, False),
        "sart_reconstruct": ("tomography", "sart_reconstruct", tomo, False),
        "piv_cross_correlate": ("pivops", "piv_cross_correlate", piv, False),
        "piv_multipass": ("pivops", "piv_multipass", piv, False),
        "piv_ensemble_correlate": ("pivops", "piv_ensemble_correlate", piv, False),
        "plane_sweep_depth": ("plane_sweep", "plane_sweep_depth", {"plane_sweep.depth": k_plane_sweep}, False),
        "joint_bilateral": ("depth_bilateral", "joint_bilateral", {"depth_bilateral.core": k_joint_bilateral}, False),
        "temporal_bilateral": ("videostream", "temporal_bilateral", {"videostream.temporal_bilateral": k_temporal_bilateral}, False),
        "voxel_grid_downsample": ("pcl_filter", "voxel_grid_downsample", {"pcl_filter.voxel": k_voxel_downsample}, False),
        "occupancy_grid": ("occupancy", "occupancy_grid", {"occupancy.grid": k_occupancy}, False),
        "photometric_stereo": ("photometric", "photometric_stereo", {"photometric.solve": k_photometric}, False),
        # 既存の device= 引数を持つ op(核の差し替えは要らない。parity と倍率だけ測る)
        "points_to_voxel": ("match3d", "points_to_voxel", {}, True),
        "scene_flow_lk": ("match3d", "scene_flow_lk", {}, True),
    }


CANDIDATES = _bind()
#: 実寸 >= 5x と parity を実測して採用した op(不採用は CANDIDATES に残すが台帳に載らない)。
TYPED_ADOPTED = ()
TYPED_ACCEL = {name: name for name in TYPED_ADOPTED}


def call(name, *args, device="cuda", **kwargs):
    """型付き op *name* を core の検証つきで呼び、計算核だけ *device* の torch で走らせる。

    未登録の名前は ``KeyError``(黙って CPU で走らせない)。``device="cpu"`` は torch CPU で
    同じ核を走らせる(parity の検算用)。候補の計測は :func:`call_candidate`。
    """
    if name not in TYPED_ACCEL:
        raise KeyError("no GPU path for typed op %r (registered: %s)" % (name, sorted(TYPED_ACCEL)))
    return call_candidate(name, *args, device=device, **kwargs)


def call_candidate(name, *args, device="cuda", **kwargs):
    """採否前の候補も呼べる計測用の入口(``tools/gpu_fill3_bench.py``)。"""
    if not _HAS_TORCH:
        raise ImportError("accel_typed needs torch")
    module, fname, kernels, takes_device = CANDIDATES[name]
    fn = getattr(__import__(module), fname)
    if takes_device:
        return fn(*args, device=device, **kwargs)
    with accel_seam.use({k: make(device) for k, make in kernels.items()}):
        return fn(*args, **kwargs)
