"""純 torch 3DGS の実用トレーナ: SSIM 損失 + 適応的 densify/prune + オービット学習/描画。

gsplat_torch.render を用い、実シーン(MuJoCo menagerie 等)を新規視点合成する。densify=
高勾配ガウシアンの複製、prune=低不透明度/巨大の除去。optimizer は densify 時に再構築
(momentum リセットは許容)。honest 指標: hold-out 視点 PSNR。
"""
from __future__ import annotations
import numpy as np
import torch
import torch.nn.functional as F
import gsplat_torch as G


# ---- SSIM(微分可能, 11x11 gaussian) -------------------------------------
def _gauss_kernel(win=11, sigma=1.5, device="cpu"):
    x = torch.arange(win, dtype=torch.float32, device=device) - win // 2
    g = torch.exp(-(x ** 2) / (2 * sigma ** 2)); g = g / g.sum()
    k = (g[:, None] * g[None, :])
    return k[None, None]                       # (1,1,win,win)


def ssim(a, b, win=11):
    """a,b: (H,W,3) in [0,1]。1 - 平均 SSIM を損失に使う。"""
    dev = a.device
    k = _gauss_kernel(win, device=dev).repeat(3, 1, 1, 1)
    A = a.permute(2, 0, 1)[None]; B = b.permute(2, 0, 1)[None]
    pad = win // 2
    mu_a = F.conv2d(A, k, padding=pad, groups=3); mu_b = F.conv2d(B, k, padding=pad, groups=3)
    mu_a2, mu_b2, mu_ab = mu_a * mu_a, mu_b * mu_b, mu_a * mu_b
    va = F.conv2d(A * A, k, padding=pad, groups=3) - mu_a2
    vb = F.conv2d(B * B, k, padding=pad, groups=3) - mu_b2
    vab = F.conv2d(A * B, k, padding=pad, groups=3) - mu_ab
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    s = ((2 * mu_ab + c1) * (2 * vab + c2)) / ((mu_a2 + mu_b2 + c1) * (va + vb + c2))
    return s.mean()


def _make_opt(gm, lr=1.0):
    return torch.optim.Adam([
        {"params": [gm.means], "lr": 1.6e-3 * lr},
        {"params": [gm.log_scales], "lr": 5e-3 * lr},
        {"params": [gm.quats], "lr": 1e-3 * lr},
        {"params": [gm.colors], "lr": 1e-2 * lr},
        {"params": [gm.raw_opacity], "lr": 3e-2 * lr}])


def _raw(gm):
    return (gm.means.detach(), gm.log_scales.detach(), gm.quats.detach(),
            gm.colors.detach(), gm.raw_opacity.detach())


def _from_raw(means, log_scales, quats, colors, raw_opacity, device):
    gm = G.GaussianModel(means.cpu().numpy(), np.zeros((len(means), 3)),
                         np.ones((len(means), 3)) * 0.02, device=device)
    with torch.no_grad():
        gm.means.copy_(means); gm.log_scales.copy_(log_scales); gm.quats.copy_(quats)
        gm.colors.copy_(colors); gm.raw_opacity.copy_(raw_opacity)
    return gm


def densify_and_prune(gm, grad_accum, *, prune_opacity=0.02, grad_thresh=None,
                      max_gaussians=60000, max_scale=0.3, device="cuda"):
    """低不透明度/巨大を prune、高勾配を clone。新しい gm を返す(統計 dict 付き)。

    max_scale: これより大きい等方スケールのガウシアン(floater)を除去。過学習の
    hold-out 悪化を抑える。"""
    m, ls, q, c, o = _raw(gm)
    opacity = torch.sigmoid(o)
    big = torch.exp(ls).max(dim=1).values > max_scale
    keep = (opacity > prune_opacity) & (~big)
    m, ls, q, c, o, ga = m[keep], ls[keep], q[keep], c[keep], o[keep], grad_accum[keep]
    n_pruned = int((~keep).sum())
    n_cloned = 0
    if len(m) < max_gaussians and grad_thresh is not None:
        hi = ga > grad_thresh
        if hi.any():
            scale = torch.exp(ls[hi])
            jit = (torch.randn_like(m[hi]) * scale * 0.5)
            m2 = torch.cat([m, m[hi] + jit]); ls2 = torch.cat([ls, ls[hi]])
            q2 = torch.cat([q, q[hi]]); c2 = torch.cat([c, c[hi]])
            o2 = torch.cat([o, o[hi]])
            m, ls, q, c, o = m2, ls2, q2, c2, o2
            n_cloned = int(hi.sum())
    gm2 = _from_raw(m, ls, q, c, o, device)
    return gm2, {"pruned": n_pruned, "cloned": n_cloned, "n": gm2.n}


def train_scene(views, init_pts, init_cols, H, W, *, iters=800, device="cuda",
                test_idx=(), lambda_ssim=0.2, densify_every=100, densify_until=600,
                log=print):
    """views: list[(rgb(H,W,3),c2w,K)]。init_pts/cols: 点群初期化。戻り値 (gm, history)。"""
    scales = G.knn_scale(init_pts, k=3)
    gm = G.GaussianModel(init_pts, init_cols, scales, device=device)
    train = [v for i, v in enumerate(views) if i not in set(test_idx)]
    test = [views[i] for i in test_idx] if test_idx else []
    opt = _make_opt(gm)
    grad_accum = torch.zeros(gm.n, device=device)
    grad_count = torch.zeros(gm.n, device=device)

    def ev(vs):
        if not vs:
            return float("nan")
        with torch.no_grad():
            return float(np.mean([G.psnr(G.render(gm, c2w, K, H, W), rgb) for rgb, c2w, K in vs]))

    hist = []
    best = {"test": -1.0, "raw": None, "n": gm.n, "it": 0}

    def _snapshot(it):
        tp = ev(test)
        if test and tp > best["test"]:
            best.update(test=tp, raw=tuple(x.clone() for x in _raw(gm)), n=gm.n, it=it)
        return tp

    for it in range(1, iters + 1):
        rgb, c2w, K = train[np.random.randint(len(train))]
        img = G.render(gm, c2w, K, H, W)
        l1 = torch.abs(img - rgb).mean()
        loss = (1 - lambda_ssim) * l1 + lambda_ssim * (1 - ssim(img, rgb))
        opt.zero_grad(); loss.backward()
        with torch.no_grad():
            if gm.means.grad is not None:
                grad_accum += gm.means.grad.norm(dim=1); grad_count += 1
        opt.step()
        if it % densify_every == 0 and it <= densify_until:
            g = grad_accum / grad_count.clamp_min(1)
            thr = torch.quantile(g[torch.isfinite(g)], 0.90) if torch.isfinite(g).any() else None
            gm, st = densify_and_prune(gm, g, grad_thresh=thr, device=device)
            opt = _make_opt(gm)
            grad_accum = torch.zeros(gm.n, device=device); grad_count = torch.zeros(gm.n, device=device)
            log(f"[iter {it}] densify: n={st['n']} (+{st['cloned']} clone / -{st['pruned']} prune) "
                f"train_psnr={ev(train):.2f} test_psnr={_snapshot(it):.2f}")
        elif it % 100 == 0:
            log(f"[iter {it}] loss={loss.item():.4f} n={gm.n} train_psnr={ev(train):.2f} test_psnr={_snapshot(it):.2f}")
        hist.append((it, gm.n))
    # early-stopping: hold-out で最良のモデルを採用(過学習の最終劣化を避ける)
    final_test = ev(test)
    if test and best["raw"] is not None and best["test"] > final_test:
        gm = _from_raw(*best["raw"], device)
        log(f"[best] test_psnr={best['test']:.2f} @iter{best['it']} (final was {final_test:.2f}) を採用")
    return gm, {"train_psnr": ev(train), "test_psnr": ev(test), "n": gm.n,
                "best_test": best["test"], "best_it": best["it"]}


def render_turntable(gm, K, H, W, *, n_frames=48, radius=1.6, elevation_deg=20,
                     lookat=(0, 0, 0.25), device="cuda"):
    """学習済み gm をオービット描画して (n_frames,H,W,3) uint8 を返す(GIF 用)。"""
    import math
    la = tuple(float(x) for x in lookat)
    el = math.radians(elevation_deg)
    z = la[2] + radius * math.sin(el); rxy = radius * math.cos(el)
    frames = []
    for i in range(n_frames):
        az = 2 * math.pi * i / n_frames
        pos = np.array([la[0] + rxy * math.cos(az), la[1] + rxy * math.sin(az), z])
        f = np.array(la) - pos; f /= np.linalg.norm(f)
        up = np.array([0, 0, 1.0])
        if abs(f @ up) > 0.999:
            up = np.array([0, 1.0, 0])
        zc = -f; xc = np.cross(up, zc); xc /= np.linalg.norm(xc); yc = np.cross(zc, xc)
        c2w = torch.eye(4, device=device)
        c2w[:3, 0] = torch.tensor(xc, dtype=torch.float32, device=device)
        c2w[:3, 1] = torch.tensor(yc, dtype=torch.float32, device=device)
        c2w[:3, 2] = torch.tensor(zc, dtype=torch.float32, device=device)
        c2w[:3, 3] = torch.tensor(pos, dtype=torch.float32, device=device)
        with torch.no_grad():
            img = (G.render(gm, c2w, K, H, W).detach().cpu().numpy() * 255).astype(np.uint8)
        frames.append(img)
    return np.stack(frames)
