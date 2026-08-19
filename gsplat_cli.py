"""Fullseye 3DGS パイプライン CLI: MJCF シーン → オービット撮影 → 純 torch 3DGS 学習
→ ターンテーブル GIF / 新規視点 PNG / gaussians(.npz)/ report(.json)。

Studio からは .venv-gsplat の python で detached 起動する薄い配線で呼ぶ。単体でも:
  .venv-gsplat/Scripts/python.exe gsplat_cli.py <scene.xml|builtin> <out_dir> [--views N] [--iters N]
GPU(cu128 venv)必須。姿勢は sim 真値(COLMAP 不要)。
"""
from __future__ import annotations
import argparse
import json
import os

import numpy as np

_BUILTIN = {
    "go2": "C:/dev/projects/mujoco_menagerie/unitree_go2/scene.xml",
    "cassie": "C:/dev/projects/mujoco_menagerie/agility_cassie/scene.xml",
    "apollo": "C:/dev/projects/mujoco_menagerie/apptronik_apollo/scene.xml",
}


def run(scene: str, out_dir: str, *, n_views=36, iters=700, width=128, height=128,
        radius=1.3, elevation_deg=22.0, lookat=(0.0, 0.0, 0.18), n_test=3,
        turntable_frames=48, seed=0, log=print) -> dict:
    import torch
    import sim_source as S
    import gsplat_torch as G
    import gsplat_train as T
    from PIL import Image
    torch.manual_seed(seed); np.random.seed(seed)
    dev = "cuda"
    if not torch.cuda.is_available():
        raise RuntimeError("gsplat_cli: CUDA が無い。.venv-gsplat(cu128)の python で実行する。")
    path = _BUILTIN.get(scene, scene)
    if not path.endswith(".xml") or not os.path.exists(path):
        raise FileNotFoundError(f"scene が見つからない: {scene} (builtin={list(_BUILTIN)})")
    os.makedirs(out_dir, exist_ok=True)
    s, names = S.orbit_scene(path, n_views=n_views, radius=radius,
                             elevation_deg=elevation_deg, lookat=lookat,
                             width=width, height=height, keyframe=0)
    views = []
    for nm in names:
        rgb = torch.tensor(s.rgb(nm).astype(np.float32) / 255, device=dev)
        c2w = torch.tensor(s.camera_to_world(nm), dtype=torch.float32, device=dev)
        K = torch.tensor(s.intrinsics(nm), dtype=torch.float32, device=dev)
        views.append((rgb, c2w, K))
    pts, cols = [], []
    for nm in [names[i] for i in range(0, n_views, max(1, n_views // 9))]:
        pp, cc = s.point_cloud_rgb(nm, stride=3, max_range=3.0)
        d = np.linalg.norm(pp[:, :2] - np.array(lookat[:2]), axis=1)
        keep = d < (radius * 0.85)
        pts.append(pp[keep]); cols.append(cc[keep])
    Kref = views[0][2]
    s.close()
    pts = np.concatenate(pts); cols = np.concatenate(cols).astype(np.float32) / 255
    sel = np.random.choice(len(pts), size=min(6000, len(pts)), replace=False)
    pts, cols = pts[sel], cols[sel]
    test_idx = tuple(int(round(i)) for i in np.linspace(0, n_views - 1, n_test + 2)[1:-1])
    log(f"init {len(pts)} pts, {n_views} views, test={test_idx}")
    gm, res = T.train_scene(views, pts, cols, height, width, iters=iters, device=dev,
                            test_idx=test_idx, lambda_ssim=0.2, densify_every=100,
                            densify_until=int(iters * 0.43), log=log)
    # 出力
    rgb, c2w, K = views[test_idx[0]]
    out = (G.render_tiled(gm, c2w, K, height, width).detach().cpu().numpy() * 255).astype(np.uint8)
    gt = (rgb.cpu().numpy() * 255).astype(np.uint8)
    Image.fromarray(np.concatenate([gt, np.full((height, 6, 3), 255, np.uint8), out], 1)).save(
        os.path.join(out_dir, "novelview.png"))
    frames = T.render_turntable(gm, Kref, height, width, n_frames=turntable_frames,
                                radius=radius, elevation_deg=elevation_deg, lookat=lookat, device=dev)
    imgs = [Image.fromarray(f) for f in frames]
    imgs[0].save(os.path.join(out_dir, "turntable.gif"), save_all=True,
                 append_images=imgs[1:], duration=60, loop=0)
    np.savez(os.path.join(out_dir, "gaussians.npz"),
             means=gm.means.detach().cpu().numpy(), log_scales=gm.log_scales.detach().cpu().numpy(),
             quats=gm.quats.detach().cpu().numpy(), colors=gm.colors.detach().cpu().numpy(),
             raw_opacity=gm.raw_opacity.detach().cpu().numpy())
    report = {"scene": scene, "n_views": n_views, "iters": iters, "n_gaussians": res["n"],
              "test_psnr": round(res["test_psnr"], 3), "best_test_psnr": round(res["best_test"], 3),
              "best_it": res["best_it"], "train_psnr": round(res["train_psnr"], 3),
              "test_idx": list(test_idx), "resolution": [width, height]}
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    log(f"DONE {report}")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fullseye 3DGS pipeline (sim scene -> gaussians)")
    ap.add_argument("scene"); ap.add_argument("out_dir")
    ap.add_argument("--views", type=int, default=36); ap.add_argument("--iters", type=int, default=700)
    ap.add_argument("--res", type=int, default=128); ap.add_argument("--radius", type=float, default=1.3)
    a = ap.parse_args(argv)
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    run(a.scene, a.out_dir, n_views=a.views, iters=a.iters, width=a.res, height=a.res, radius=a.radius)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
