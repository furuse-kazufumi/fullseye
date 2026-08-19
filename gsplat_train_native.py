"""gsplat ネイティブ backend で sim シーンを 3DGS 学習(高速・高解像)。

純 torch(gsplat_torch)の桁違い高速版。gsplat.rasterization で forward。viewmat は
OpenGL c2w → OpenCV world-to-cam(F=diag(1,-1,-1))へ変換。実行は vcvars+CUDA_PATH の
bat 経由(gsplat が import 時に CUDA toolkit を要求するため)。
"""
from __future__ import annotations
import os, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import torch
import gsplat
import sim_source as S
from gsplat_train import ssim
from PIL import Image

_F4 = torch.tensor([[1., 0, 0, 0], [0, -1., 0, 0], [0, 0, -1., 0], [0, 0, 0, 1.]])


def _viewmat(c2w, dev):
    return (_F4.to(dev) @ torch.linalg.inv(c2w))


def train(scene, out_dir, *, n_views=36, iters=1000, res=256, radius=1.3,
          elevation_deg=22.0, lookat=(0, 0, 0.18), n_gauss=20000, n_test=3, log=print):
    dev = "cuda"
    os.makedirs(out_dir, exist_ok=True)
    s, names = S.orbit_scene(scene, n_views=n_views, radius=radius,
                             elevation_deg=elevation_deg, lookat=lookat,
                             width=res, height=res, keyframe=0)
    views = []
    for nm in names:
        rgb = torch.tensor(s.rgb(nm).astype(np.float32) / 255, device=dev)
        c2w = torch.tensor(s.camera_to_world(nm), dtype=torch.float32, device=dev)
        K = torch.tensor(s.intrinsics(nm), dtype=torch.float32, device=dev)
        views.append((rgb, _viewmat(c2w, dev), K))
    pts, cols = [], []
    for nm in [names[i] for i in range(0, n_views, max(1, n_views // 12))]:
        pp, cc = s.point_cloud_rgb(nm, stride=2, max_range=3.0)
        d = np.linalg.norm(pp[:, :2] - np.array(lookat[:2]), axis=1)
        keep = d < radius * 0.85
        pts.append(pp[keep]); cols.append(cc[keep])
    s.close()
    pts = np.concatenate(pts); cols = np.concatenate(cols).astype(np.float32) / 255
    sel = np.random.RandomState(0).choice(len(pts), size=min(n_gauss, len(pts)), replace=False)
    pts, cols = pts[sel], cols[sel]
    # 初期スケール = 近傍距離(粗く: 全体の中央最近傍)
    from gsplat_torch import knn_scale
    scl = knn_scale(pts[:min(len(pts), 4000)], k=3).mean() if len(pts) else 0.02

    means = torch.nn.Parameter(torch.tensor(pts, dtype=torch.float32, device=dev))
    quats = torch.nn.Parameter(torch.tensor(
        np.tile([1., 0, 0, 0], (len(pts), 1)), dtype=torch.float32, device=dev))
    logscales = torch.nn.Parameter(torch.full((len(pts), 3), float(np.log(scl)), device=dev))
    raw_op = torch.nn.Parameter(torch.full((len(pts),), 2.0, device=dev))
    logit_c = torch.nn.Parameter(torch.logit(torch.tensor(cols, device=dev).clamp(1e-4, 1 - 1e-4)))

    test_idx = set(int(round(i)) for i in np.linspace(0, n_views - 1, n_test + 2)[1:-1])
    train_v = [v for i, v in enumerate(views) if i not in test_idx]
    test_v = [views[i] for i in test_idx]
    opt = torch.optim.Adam([
        {"params": [means], "lr": 1.6e-3}, {"params": [logscales], "lr": 5e-3},
        {"params": [quats], "lr": 1e-3}, {"params": [raw_op], "lr": 3e-2},
        {"params": [logit_c], "lr": 1e-2}])

    def render(viewmat, K):
        out, _, _ = gsplat.rasterization(
            means, quats / quats.norm(dim=-1, keepdim=True), torch.exp(logscales),
            torch.sigmoid(raw_op), torch.sigmoid(logit_c),
            viewmat[None], K[None], res, res)
        return out[0].clamp(0, 1)

    def psnr(a, b):
        mse = torch.mean((a - b) ** 2).item()
        return 99.0 if mse < 1e-12 else 10 * np.log10(1 / mse)

    def ev(vs):
        with torch.no_grad():
            return float(np.mean([psnr(render(vm, K), rgb) for rgb, vm, K in vs]))

    log(f"init {len(pts)} gaussians, {n_views} views ({len(train_v)} train/{len(test_v)} test), res={res}")
    t0 = time.time()
    for it in range(1, iters + 1):
        rgb, vm, K = train_v[np.random.randint(len(train_v))]
        img = render(vm, K)
        loss = 0.8 * torch.abs(img - rgb).mean() + 0.2 * (1 - ssim(img, rgb))
        opt.zero_grad(); loss.backward(); opt.step()
        if it % 200 == 0:
            log(f"[iter {it}] loss={loss.item():.4f} train={ev(train_v):.2f} test={ev(test_v):.2f}")
    torch.cuda.synchronize(); dt = time.time() - t0
    tp = ev(test_v)
    log(f"RESULT test_psnr={tp:.2f} train_psnr={ev(train_v):.2f} n={len(pts)} in {dt:.1f}s ({iters/dt:.1f} it/s)")
    # 新規視点 + ターンテーブル
    ti = sorted(test_idx)[0]
    rgb, vm, K = views[ti]
    out = (render(vm, K).detach().cpu().numpy() * 255).astype(np.uint8)
    gt = (rgb.cpu().numpy() * 255).astype(np.uint8)
    Image.fromarray(np.concatenate([gt, np.full((res, 8, 3), 255, np.uint8), out], 1)).save(
        os.path.join(out_dir, "novelview.png"))
    # turntable
    import math
    la = tuple(float(x) for x in lookat); el = math.radians(elevation_deg)
    z = la[2] + radius * math.sin(el); rxy = radius * math.cos(el)
    frames = []
    for i in range(48):
        az = 2 * math.pi * i / 48
        pos = np.array([la[0] + rxy * math.cos(az), la[1] + rxy * math.sin(az), z])
        f = np.array(la) - pos; f /= np.linalg.norm(f); up = np.array([0, 0, 1.])
        if abs(f @ up) > 0.999: up = np.array([0, 1., 0])
        zc = -f; xc = np.cross(up, zc); xc /= np.linalg.norm(xc); yc = np.cross(zc, xc)
        c2w = torch.eye(4, device=dev)
        c2w[:3, 0] = torch.tensor(xc, dtype=torch.float32, device=dev)
        c2w[:3, 1] = torch.tensor(yc, dtype=torch.float32, device=dev)
        c2w[:3, 2] = torch.tensor(zc, dtype=torch.float32, device=dev)
        c2w[:3, 3] = torch.tensor(pos, dtype=torch.float32, device=dev)
        with torch.no_grad():
            frames.append((render(_viewmat(c2w, dev), K).detach().cpu().numpy() * 255).astype(np.uint8))
    imgs = [Image.fromarray(f) for f in frames]
    imgs[0].save(os.path.join(out_dir, "turntable.gif"), save_all=True, append_images=imgs[1:], duration=60, loop=0)
    log(f"saved novelview.png, turntable.gif -> {out_dir}")
    return {"test_psnr": tp, "n": len(pts), "sec": dt}


if __name__ == "__main__":
    scene = sys.argv[1] if len(sys.argv) > 1 else "C:/dev/projects/mujoco_menagerie/unitree_go2/scene.xml"
    out = sys.argv[2] if len(sys.argv) > 2 else "gsplat_native_out"
    train(scene, out, res=256, iters=1000, n_gauss=20000, log=lambda m: print(m, flush=True))


_SH_C0 = 0.28209479177387814   # SH DC 基底: rgb = C0 * sh0 + 0.5


def train_densify(scene, out_dir, *, n_views=36, iters=1500, res=256, radius=1.3,
                  elevation_deg=22.0, lookat=(0, 0, 0.18), n_gauss_init=8000,
                  n_test=3, sh_degree=3, log=print):
    """gsplat DefaultStrategy で densify/prune しながら学習(soft さ改善版)。

    点群で少なめに初期化 → 高勾配領域を split/clone、低不透明度を prune。
    sh_degree>0 で view-dependent color(SH、反射/光沢を再現)。hold-out PSNR。
    """
    import math
    from gsplat.strategy import DefaultStrategy
    dev = "cuda"
    os.makedirs(out_dir, exist_ok=True)
    s, names = S.orbit_scene(scene, n_views=n_views, radius=radius,
                             elevation_deg=elevation_deg, lookat=lookat,
                             width=res, height=res, keyframe=0)
    views = []
    for nm in names:
        rgb = torch.tensor(s.rgb(nm).astype(np.float32) / 255, device=dev)
        c2w = torch.tensor(s.camera_to_world(nm), dtype=torch.float32, device=dev)
        K = torch.tensor(s.intrinsics(nm), dtype=torch.float32, device=dev)
        views.append((rgb, _viewmat(c2w, dev), K))
    pts, cols = [], []
    for nm in [names[i] for i in range(0, n_views, max(1, n_views // 12))]:
        pp, cc = s.point_cloud_rgb(nm, stride=2, max_range=3.0)
        d = np.linalg.norm(pp[:, :2] - np.array(lookat[:2]), axis=1)
        keep = d < radius * 0.85
        pts.append(pp[keep]); cols.append(cc[keep])
    s.close()
    pts = np.concatenate(pts); cols = np.concatenate(cols).astype(np.float32) / 255
    sel = np.random.RandomState(0).choice(len(pts), size=min(n_gauss_init, len(pts)), replace=False)
    pts, cols = pts[sel], cols[sel]
    from gsplat_torch import knn_scale
    scl = float(knn_scale(pts[:min(len(pts), 4000)], k=3).mean())

    N0 = len(pts)
    K = (sh_degree + 1) ** 2
    sh0 = ((torch.tensor(cols, device=dev) - 0.5) / _SH_C0).reshape(N0, 1, 3)   # DC=点群色
    shN = torch.zeros(N0, K - 1, 3, device=dev)
    params = torch.nn.ParameterDict({
        "means": torch.nn.Parameter(torch.tensor(pts, dtype=torch.float32, device=dev)),
        "scales": torch.nn.Parameter(torch.full((N0, 3), float(np.log(scl)), device=dev)),
        "quats": torch.nn.Parameter(torch.tensor(np.tile([1., 0, 0, 0], (N0, 1)),
                                                 dtype=torch.float32, device=dev)),
        "opacities": torch.nn.Parameter(torch.full((N0,), 2.0, device=dev)),
        "sh0": torch.nn.Parameter(sh0),
        "shN": torch.nn.Parameter(shN),
    }).to(dev)
    lrs = {"means": 1.6e-3, "scales": 5e-3, "quats": 1e-3, "opacities": 3e-2,
           "sh0": 2.5e-3, "shN": 2.5e-3 / 20}
    optimizers = {k: torch.optim.Adam([{"params": params[k], "lr": lrs[k], "name": k}], eps=1e-15)
                  for k in params}
    strategy = DefaultStrategy(verbose=False, refine_start_iter=int(iters * 0.1),
                               refine_stop_iter=int(iters * 0.6), reset_every=int(iters * 0.3),
                               refine_every=max(50, iters // 20),
                               prune_opa=0.05, grow_grad2d=0.0006, absgrad=True)
    strategy.check_sanity(params, optimizers)
    state = strategy.initialize_state(scene_scale=float(radius))

    test_idx = set(int(round(i)) for i in np.linspace(0, n_views - 1, n_test + 2)[1:-1])
    train_v = [v for i, v in enumerate(views) if i not in test_idx]
    test_v = [views[i] for i in test_idx]

    def render(vm, Kc):
        sh = torch.cat([params["sh0"], params["shN"]], dim=1)      # (N,K,3) SH 係数
        out, _, info = gsplat.rasterization(
            params["means"], params["quats"] / params["quats"].norm(dim=-1, keepdim=True),
            torch.exp(params["scales"]), torch.sigmoid(params["opacities"]),
            sh, vm[None], Kc[None], res, res, sh_degree=sh_degree,
            packed=False, absgrad=strategy.absgrad, rasterize_mode="antialiased")
        return out[0].clamp(0, 1), info

    def psnr(a, b):
        mse = torch.mean((a - b) ** 2).item()
        return 99.0 if mse < 1e-12 else 10 * np.log10(1 / mse)

    def ev(vs):
        with torch.no_grad():
            return float(np.mean([psnr(render(vm, K)[0], rgb) for rgb, vm, K in vs]))

    log(f"init {N0} gaussians (densify対象), {n_views} views, res={res}")
    t0 = time.time()
    for it in range(1, iters + 1):
        rgb, vm, K = train_v[np.random.randint(len(train_v))]
        img, info = render(vm, K)
        info["means2d"].retain_grad()
        loss = 0.8 * torch.abs(img - rgb).mean() + 0.2 * (1 - ssim(img, rgb))
        strategy.step_pre_backward(params, optimizers, state, it, info)
        for o in optimizers.values():
            o.zero_grad()
        loss.backward()
        for o in optimizers.values():
            o.step()
        strategy.step_post_backward(params, optimizers, state, it, info, packed=False)
        if it % 300 == 0:
            log(f"[iter {it}] loss={loss.item():.4f} n={params['means'].shape[0]} "
                f"train={ev(train_v):.2f} test={ev(test_v):.2f}")
    torch.cuda.synchronize(); dt = time.time() - t0
    tp = ev(test_v); nfin = params["means"].shape[0]
    log(f"RESULT test_psnr={tp:.2f} train_psnr={ev(train_v):.2f} n={nfin} (init {N0}) in {dt:.1f}s")

    from PIL import Image
    ti = sorted(test_idx)[0]; rgb, vm, K = views[ti]
    out = (render(vm, K)[0].detach().cpu().numpy() * 255).astype(np.uint8)
    gt = (rgb.cpu().numpy() * 255).astype(np.uint8)
    Image.fromarray(np.concatenate([gt, np.full((res, 8, 3), 255, np.uint8), out], 1)).save(
        os.path.join(out_dir, "novelview.png"))
    la = tuple(float(x) for x in lookat); el = math.radians(elevation_deg)
    z = la[2] + radius * math.sin(el); rxy = radius * math.cos(el)
    frames = []
    for i in range(48):
        az = 2 * math.pi * i / 48
        pos = np.array([la[0] + rxy * math.cos(az), la[1] + rxy * math.sin(az), z])
        f = np.array(la) - pos; f /= np.linalg.norm(f); up = np.array([0, 0, 1.])
        if abs(f @ up) > 0.999: up = np.array([0, 1., 0])
        zc = -f; xc = np.cross(up, zc); xc /= np.linalg.norm(xc); yc = np.cross(zc, xc)
        c2w = torch.eye(4, device=dev)
        c2w[:3, 0] = torch.tensor(xc, dtype=torch.float32, device=dev)
        c2w[:3, 1] = torch.tensor(yc, dtype=torch.float32, device=dev)
        c2w[:3, 2] = torch.tensor(zc, dtype=torch.float32, device=dev)
        c2w[:3, 3] = torch.tensor(pos, dtype=torch.float32, device=dev)
        with torch.no_grad():
            frames.append((render(_viewmat(c2w, dev), K)[0].detach().cpu().numpy() * 255).astype(np.uint8))
    imgs = [Image.fromarray(f) for f in frames]
    imgs[0].save(os.path.join(out_dir, "turntable.gif"), save_all=True, append_images=imgs[1:], duration=60, loop=0)
    log(f"saved novelview.png, turntable.gif -> {out_dir}")
    return {"test_psnr": tp, "n": nfin, "sec": dt}


def save_gaussians_ply(path, means, scales_log, quats, opacities_raw, sh0, shN=None):
    """3DGS 標準 .ply(INRIA 形式)で書き出す。SuperSplat 等の Web ビューアで開ける。

    means(N,3) / scales_log(N,3, log) / quats(N,4, wxyz) / opacities_raw(N, logit) /
    sh0(N,1,3, SH DC) / shN(N,K-1,3, 高次SH or None)。ビューアが exp/sigmoid を適用。
    """
    import numpy as _np
    m = means.detach().cpu().numpy().astype(_np.float32)
    sc = scales_log.detach().cpu().numpy().astype(_np.float32)
    q = quats.detach().cpu().numpy().astype(_np.float32)
    q = q / (_np.linalg.norm(q, axis=1, keepdims=True) + 1e-9)
    op = opacities_raw.detach().cpu().numpy().astype(_np.float32).reshape(-1, 1)
    dc = sh0.detach().cpu().numpy().astype(_np.float32).reshape(len(m), 3)      # (N,3)
    N = len(m)
    cols = [("x", m[:, 0]), ("y", m[:, 1]), ("z", m[:, 2]),
            ("nx", _np.zeros(N, _np.float32)), ("ny", _np.zeros(N, _np.float32)),
            ("nz", _np.zeros(N, _np.float32)),
            ("f_dc_0", dc[:, 0]), ("f_dc_1", dc[:, 1]), ("f_dc_2", dc[:, 2])]
    if shN is not None and shN.shape[1] > 0:
        rest = shN.detach().cpu().numpy().astype(_np.float32)                    # (N,K-1,3)
        rest = _np.transpose(rest, (0, 2, 1)).reshape(N, -1)                     # channel-major
        for i in range(rest.shape[1]):
            cols.append((f"f_rest_{i}", rest[:, i]))
    cols.append(("opacity", op[:, 0]))
    cols += [("scale_0", sc[:, 0]), ("scale_1", sc[:, 1]), ("scale_2", sc[:, 2])]
    cols += [("rot_0", q[:, 0]), ("rot_1", q[:, 1]), ("rot_2", q[:, 2]), ("rot_3", q[:, 3])]
    names = [c[0] for c in cols]
    data = _np.stack([c[1] for c in cols], axis=1).astype(_np.float32)
    header = ["ply", "format binary_little_endian 1.0", f"element vertex {N}"]
    header += [f"property float {n}" for n in names] + ["end_header"]
    with open(path, "wb") as f:
        f.write(("\n".join(header) + "\n").encode("ascii"))
        f.write(data.tobytes())
    return path
