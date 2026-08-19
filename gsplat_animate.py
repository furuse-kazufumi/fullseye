"""動く 3DGS ―― sim の body に各ガウシアンをリグ付けし、動きを剛体スキニングで再生。

フル 4D-GS は使わず、ロボットが剛体リンク集合であることを利用:
  1. 正準ポーズで 3DGS 学習(各ガウシアンの body 帰属を segmentation で確定)
  2. 各ガウシアンを所属 body のローカル座標で保持
  3. 動きの軌道(各フレームの body 姿勢=sim 真値)で剛体変換 -> gsplat で再描画 -> GIF

実行は fullseye_3dgs.setup_cuda_env() 後(native gsplat)。
"""
from __future__ import annotations
import os
import sys
import time
import math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import torch
import gsplat
import mujoco
import sim_source as S
from gsplat_train import ssim
from gsplat_train_native import _viewmat, _SH_C0, save_gaussians_ply
from PIL import Image


def _quat_to_R(q):
    q = q / q.norm(dim=-1, keepdim=True).clamp_min(1e-9)
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    N = q.shape[0]
    R = torch.empty(N, 3, 3, device=q.device, dtype=q.dtype)
    R[:, 0, 0] = 1 - 2 * (y * y + z * z); R[:, 0, 1] = 2 * (x * y - w * z); R[:, 0, 2] = 2 * (x * z + w * y)
    R[:, 1, 0] = 2 * (x * y + w * z); R[:, 1, 1] = 1 - 2 * (x * x + z * z); R[:, 1, 2] = 2 * (y * z - w * x)
    R[:, 2, 0] = 2 * (x * z - w * y); R[:, 2, 1] = 2 * (y * z + w * x); R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def _qmul(a, b):
    aw, ax, ay, az = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
    bw, bx, by, bz = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    return torch.stack([
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw], dim=1)


def _qinv(q):
    return q * torch.tensor([1., -1, -1, -1], device=q.device)


def _canned_motion(model, home_qpos, n_frames, amp, freq):
    """サイン波で hinge 関節を動かす qpos 軌道(root free joint は固定)。"""
    hinge_adr = []
    for j in range(model.njnt):
        if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE:
            hinge_adr.append(int(model.jnt_qposadr[j]))
    frames = []
    for i in range(n_frames):
        t = i / n_frames
        q = home_qpos.copy()
        for k, adr in enumerate(hinge_adr):
            q[adr] = home_qpos[adr] + amp * math.sin(2 * math.pi * freq * t + k * 0.7)
        frames.append(q)
    return frames


def _fixed_camera(lookat, radius, elevation_deg, view_azimuth, dev):
    la = tuple(float(x) for x in lookat)
    el = math.radians(elevation_deg)
    z = la[2] + radius * math.sin(el)
    rxy = radius * math.cos(el)
    az = 2 * math.pi * view_azimuth
    pos = np.array([la[0] + rxy * math.cos(az), la[1] + rxy * math.sin(az), z])
    f = np.array(la) - pos
    f /= np.linalg.norm(f)
    up = np.array([0, 0, 1.])
    zc = -f
    xc = np.cross(up, zc); xc /= np.linalg.norm(xc)
    yc = np.cross(zc, xc)
    c2w = torch.eye(4, device=dev)
    c2w[:3, 0] = torch.tensor(xc, dtype=torch.float32, device=dev)
    c2w[:3, 1] = torch.tensor(yc, dtype=torch.float32, device=dev)
    c2w[:3, 2] = torch.tensor(zc, dtype=torch.float32, device=dev)
    c2w[:3, 3] = torch.tensor(pos, dtype=torch.float32, device=dev)
    return _viewmat(c2w, dev)


def animate(scene, out_dir, *, n_views=36, iters=1000, res=256, radius=1.3,
            elevation_deg=22.0, lookat=(0, 0, 0.18), n_gauss=25000, n_test=2,
            sh_degree=2, n_frames=60, amp=0.5, freq=1.0, view_azimuth=0.6, log=print):
    dev = "cuda"
    os.makedirs(out_dir, exist_ok=True)
    s, names = S.orbit_scene(scene, n_views=n_views, radius=radius,
                             elevation_deg=elevation_deg, lookat=lookat,
                             width=res, height=res, keyframe=0)
    model, data = s._m, s._d
    home_qpos = np.asarray(data.qpos).copy()
    views = []
    for nm in names:
        rgb = torch.tensor(s.rgb(nm).astype(np.float32) / 255, device=dev)
        c2w = torch.tensor(s.camera_to_world(nm), dtype=torch.float32, device=dev)
        K = torch.tensor(s.intrinsics(nm), dtype=torch.float32, device=dev)
        views.append((rgb, _viewmat(c2w, dev), K))
    pts, cols, bids = [], [], []
    for nm in [names[i] for i in range(0, n_views, max(1, n_views // 12))]:
        pp, cc, bb = s.point_cloud_seg(nm, stride=2, max_range=3.0)
        d = np.linalg.norm(pp[:, :2] - np.array(lookat[:2]), axis=1)
        keep = (d < radius * 0.9) & (bb >= 0)
        pts.append(pp[keep]); cols.append(cc[keep]); bids.append(bb[keep])
    pts = np.concatenate(pts); cols = np.concatenate(cols).astype(np.float32) / 255
    bids = np.concatenate(bids)
    if len(pts) > n_gauss:
        sel = np.random.RandomState(0).choice(len(pts), size=n_gauss, replace=False)
        pts, cols, bids = pts[sel], cols[sel], bids[sel]
    from gsplat_torch import knn_scale
    scl = float(knn_scale(pts[:min(len(pts), 4000)], k=3).mean())
    N = len(pts)
    log(f"init {N} gaussians, bodies={sorted(set(bids.tolist()))[:10]}")

    means = torch.nn.Parameter(torch.tensor(pts, dtype=torch.float32, device=dev))
    quats = torch.nn.Parameter(torch.tensor(np.tile([1., 0, 0, 0], (N, 1)), dtype=torch.float32, device=dev))
    logscales = torch.nn.Parameter(torch.full((N, 3), float(np.log(scl)), device=dev))
    raw_op = torch.nn.Parameter(torch.full((N,), 2.0, device=dev))
    Kc = (sh_degree + 1) ** 2
    sh0 = torch.nn.Parameter(((torch.tensor(cols, device=dev) - 0.5) / _SH_C0).reshape(N, 1, 3))
    shN = torch.nn.Parameter(torch.zeros(N, Kc - 1, 3, device=dev))
    opt = torch.optim.Adam([
        {"params": [means], "lr": 1.6e-3}, {"params": [logscales], "lr": 5e-3},
        {"params": [quats], "lr": 1e-3}, {"params": [raw_op], "lr": 3e-2},
        {"params": [sh0], "lr": 2.5e-3}, {"params": [shN], "lr": 2.5e-3 / 20}])
    test_idx = set(int(round(i)) for i in np.linspace(0, n_views - 1, n_test + 2)[1:-1])
    train_v = [v for i, v in enumerate(views) if i not in test_idx]

    def render(vm, K, mu, qt):
        sh = torch.cat([sh0, shN], dim=1)
        out, _, _ = gsplat.rasterization(
            mu, qt / qt.norm(dim=-1, keepdim=True), torch.exp(logscales),
            torch.sigmoid(raw_op), sh, vm[None], K[None], res, res,
            sh_degree=sh_degree, packed=False, rasterize_mode="antialiased")
        return out[0].clamp(0, 1)

    t0 = time.time()
    for it in range(1, iters + 1):
        rgb, vm, K = train_v[np.random.randint(len(train_v))]
        img = render(vm, K, means, quats)
        loss = 0.8 * torch.abs(img - rgb).mean() + 0.2 * (1 - ssim(img, rgb))
        opt.zero_grad(); loss.backward(); opt.step()
        if it % 250 == 0:
            log(f"[iter {it}] loss={loss.item():.4f}")
    log(f"canonical train done in {time.time() - t0:.1f}s")

    # --- リグ付け: 各ガウシアンを所属 body のローカル座標へ ---
    bt0 = s.body_transforms()
    body_ids_t = torch.tensor(bids, device=dev, dtype=torch.long)
    uniq_bodies = sorted(set(bids.tolist()))
    with torch.no_grad():
        mu_w = means.detach()
        qt_w = quats.detach() / quats.detach().norm(dim=-1, keepdim=True)
        local_pos = torch.zeros_like(mu_w)
        local_quat = qt_w.clone()
        for b in uniq_bodies:
            idx = torch.nonzero(body_ids_t == b, as_tuple=True)[0]
            if idx.numel() == 0:
                continue
            pos0 = torch.tensor(bt0[b][0], dtype=torch.float32, device=dev)
            q0 = torch.tensor(bt0[b][1], dtype=torch.float32, device=dev).reshape(1, 4)
            R0 = _quat_to_R(q0)[0]
            local_pos[idx] = (mu_w[idx] - pos0) @ R0
            local_quat[idx] = _qmul(_qinv(q0).repeat(idx.numel(), 1), qt_w[idx])

    # --- モーション軌道 -> 各フレームを剛体スキニングで描画 ---
    qtraj = _canned_motion(model, home_qpos, n_frames, amp, freq)
    vm = _fixed_camera(lookat, radius, elevation_deg, view_azimuth, dev)
    Kcam = views[0][2]
    frames = []
    for q in qtraj:
        data.qpos[:] = q
        mujoco.mj_forward(model, data)
        bt = s.body_transforms()
        mu = local_pos.clone()
        qt = local_quat.clone()
        with torch.no_grad():
            for b in uniq_bodies:
                idx = torch.nonzero(body_ids_t == b, as_tuple=True)[0]
                if idx.numel() == 0:
                    continue
                posb = torch.tensor(bt[b][0], dtype=torch.float32, device=dev)
                qb = torch.tensor(bt[b][1], dtype=torch.float32, device=dev).reshape(1, 4)
                Rb = _quat_to_R(qb)[0]
                mu[idx] = local_pos[idx] @ Rb.T + posb
                qt[idx] = _qmul(qb.repeat(idx.numel(), 1), local_quat[idx])
            img = (render(vm, Kcam, mu, qt).detach().cpu().numpy() * 255).astype(np.uint8)
        frames.append(img)
    data.qpos[:] = home_qpos
    mujoco.mj_forward(model, data)
    s.close()

    imgs = [Image.fromarray(f) for f in frames]
    gif = os.path.join(out_dir, "motion.gif")
    imgs[0].save(gif, save_all=True, append_images=imgs[1:], duration=1000 // 30, loop=0)
    save_gaussians_ply(os.path.join(out_dir, "gaussians.ply"), means, logscales, quats, raw_op, sh0, shN)
    log(f"saved motion.gif ({n_frames} frames), gaussians.ply -> {out_dir}")
    return {"n": N, "frames": n_frames, "gif": gif}


if __name__ == "__main__":
    import fullseye_3dgs as F
    F.setup_cuda_env()
    scene_arg = sys.argv[1] if len(sys.argv) > 1 else "C:/dev/projects/mujoco_menagerie/unitree_go2/scene.xml"
    out_arg = sys.argv[2] if len(sys.argv) > 2 else "anim_out"
    animate(scene_arg, out_arg, log=lambda m: print(m, flush=True))
