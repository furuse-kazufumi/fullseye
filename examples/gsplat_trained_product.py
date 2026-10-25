# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gsplat_trained_product — 商品を「撮って」3DGS を学習し、ブラウザのビューアにする(GPU・torch が要る)。

    py -3.11 examples/gsplat_trained_product.py                      # out/gsplat_trained/ に書く
    py -3.11 examples/gsplat_trained_product.py --out docs/gsplat    # 公開ページと同じ場所

``gsplat_product_viewer.py`` の 3DGS はメッシュから初期化したもの。こちらは写真から学習する本来の流れを
合成の撮影で通す:

1. ヘッドホン(Fullseye の符号付き距離場の op + marching cubes のメッシュ)を、周りの 48 視点から
   ``driveworld.world_camera``(メッシュのラスタライザ)で撮る。光は世界に固定(視点ごとにカメラ系へ直して渡す)。
2. 初期値はメッシュの面からまばらに取った 3,000 点(写真の 3DGS でいう SfM の点群の代わり)。色は灰色から始める。
3. ``gsplat_train.train_scene``(純 torch の 3DGS、SSIM 損失 + 増やす / 刈る)を GPU で学習。6 視点は学習に使わず
   検査に回し、その PSNR を出す。
4. 学習したガウシアン(位置・大きさ・四元数・色・不透明度)を ``gs_viewer_html`` で 1 枚の HTML にする。

GPU の torch は既定のインタプリタに無いことが多いので、学習だけを ``FULLSEYE_TORCH_PYTHON``(CUDA の torch が入った
python)で別プロセスとして走らせる。見つからなければ SKIP を出して 0 で終わる(黙って CPU で何十分も回さない)。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

N_VIEWS, N_TEST, RES, ITERS = 48, 6, 192, 2000
#: 学習の背景(gsplat_torch.render_tiled の既定と同じ)。撮影もこの色にする(違うと縁が背景色の差を学んでしまう)。
BG = (0.29, 0.30, 0.31)


def _views(out_dir: str) -> str:
    """撮影(numpy): 視点ごとの画像・c2w・K と初期の点群を npz に書く。"""
    import driveworld
    import gsviewer
    import mesh as _mesh
    sys.path.insert(0, os.path.join(ROOT, "examples"))
    import gsplat_product_viewer as P
    w = P.headphones()
    lo, hi = w["V"].min(0), w["V"].max(0)
    tgt = 0.5 * (lo + hi)
    rad = float(np.linalg.norm(hi - lo)) * 0.5
    dist = rad / np.sin(np.radians(35.0) / 2) * 1.05
    scale = 1.0 / rad
    K = gsviewer._intrinsics(35.0, RES, RES)
    light_w = np.array([0.3, -0.5, 0.8]) / np.linalg.norm([0.3, -0.5, 0.8])
    imgs, c2ws = [], []
    rng = np.random.default_rng(0)
    for i in range(N_VIEWS):
        yaw = 360.0 * i / N_VIEWS + rng.uniform(-3, 3)
        pitch = (-10.0, 15.0, 40.0)[i % 3] + rng.uniform(-4, 4)
        pose = gsviewer._orbit_pose(tgt, yaw, pitch, dist)
        r = driveworld.world_camera(w, pose, K, RES, RES, light=pose[:3, :3] @ light_w, ambient=0.35, sky=BG)
        imgs.append(np.clip(r["color"], 0, 1).astype(np.float32))
        c2w = np.linalg.inv(pose)
        c2w[:3, 3] = (c2w[:3, 3] - tgt) * scale                     # 学習は「物の半径 ≈ 1」の座標で(学習率が絶対量のため)
        c2ws.append(c2w.astype(np.float32))
    P0 = (_mesh.sample_surface(w["V"], w["F"], 3000, seed=1) - tgt) * scale
    path = os.path.join(out_dir, "trained_views.npz")
    np.savez_compressed(path, imgs=np.stack(imgs), c2w=np.stack(c2ws), K=K.astype(np.float32), pts=P0.astype(np.float32),
                        target=tgt, dist=dist, scale=scale)
    return path


def _train(npz: str, out: str, iters: int) -> None:
    """学習(torch・CUDA): ``gsplat_train.train_scene`` → ガウシアンを npz に書く。"""
    import torch
    import gsplat_train as T
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is not available in this interpreter")
    d = np.load(npz)
    dev = "cuda"
    views = [(torch.tensor(d["imgs"][i], device=dev), torch.tensor(d["c2w"][i], device=dev),
              torch.tensor(d["K"], device=dev)) for i in range(len(d["imgs"]))]
    test_idx = tuple(range(0, len(views), len(views) // N_TEST))[:N_TEST]
    torch.manual_seed(0)
    np.random.seed(0)
    cols = np.full((len(d["pts"]), 3), 0.5)
    t0 = time.time()
    gm, hist = T.train_scene(views, d["pts"].astype(np.float64), cols, RES, RES, iters=iters, device=dev, test_idx=test_idx,
                             densify_until=int(iters * 0.6), log=lambda s: print(s, flush=True))
    with torch.no_grad():
        q = gm.quats / gm.quats.norm(dim=1, keepdim=True).clamp_min(1e-9)
        np.savez_compressed(out, xyz=gm.means.cpu().numpy(), scale=torch.exp(gm.log_scales).cpu().numpy(),
                            rot=q.cpu().numpy(), rgb=_squash(gm.colors).cpu().numpy(),
                            opacity=_squash(gm.raw_opacity).cpu().numpy(),
                            meta=json.dumps({"train_psnr": hist["train_psnr"], "test_psnr": hist["test_psnr"],
                                             "best_test": hist["best_test"], "n": int(gm.n), "seconds": time.time() - t0,
                                             "iters": iters, "views": len(views), "test_views": len(test_idx),
                                             "res": RES}))


def _squash(x):
    """ロジスティック関数 1 / (1 + e^−x)(学習は色と不透明度をこの逆関数の空間で持つ)。"""
    import torch
    return 1.0 / (1.0 + torch.exp(-x))


def _torch_python() -> str | None:
    cand = [os.environ.get("FULLSEYE_TORCH_PYTHON", ""), sys.executable]
    for py in cand:
        if not py or not os.path.exists(py):
            continue
        r = subprocess.run([py, "-c", "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 3)"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode == 0:
            return py
    return None


NOTE = {
    "ja": "合成の撮影 48 視点(メッシュのラスタライザ、光は世界に固定)から GPU で学習した 3DGS です。初期値はメッシュの面から"
          "取った 3,000 点。検査用の 6 視点の PSNR は {test:.1f} dB(学習に使っていない視点)。",
    "en": "A 3DGS trained on the GPU from 48 synthetic photographs (mesh rasteriser, light fixed in the world). Initialised "
          "from 3,000 points sampled on the mesh. PSNR on 6 held-out views: {test:.1f} dB.",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "gsplat_trained"))
    ap.add_argument("--iters", type=int, default=ITERS)
    ap.add_argument("--train", nargs=2, metavar=("VIEWS_NPZ", "OUT_NPZ"), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.train:
        _train(a.train[0], a.train[1], a.iters)
        return 0
    os.makedirs(a.out, exist_ok=True)
    py = _torch_python()
    if py is None:
        print("SKIP: no Python with CUDA torch (set FULLSEYE_TORCH_PYTHON)")
        return 0
    t0 = time.time()
    npz = _views(a.out)
    print("views: %d x %dx%d (%.1f s)" % (N_VIEWS, RES, RES, time.time() - t0))
    gpath = os.path.join(a.out, "trained_gaussians.npz")
    env = dict(os.environ, PYTHONPATH=ROOT)
    subprocess.run([py, os.path.abspath(__file__), "--train", npz, gpath, "--iters", str(a.iters)], check=True,
                   stdin=subprocess.DEVNULL, env=env)
    import gsviewer
    with np.load(gpath) as g:                                         # 閉じないと Windows では消せない
        meta = json.loads(str(g["meta"]))
        gs = {k: g[k].astype(np.float64) for k in ("xyz", "scale", "rot", "rgb", "opacity")}
    v = np.load(npz)
    s, tgt = float(v["scale"]), np.asarray(v["target"], np.float64)
    gs["xyz"] = gs["xyz"] / s + tgt                                   # 学習の座標 → 元の座標(m)
    gs["scale"] = gs["scale"] / s
    note = {l: NOTE["ja" if l == "ja" else "en"].format(test=meta["best_test"]) for l in ("ja", "en")}
    title = {"ja": "ヘッドホン — 学習した 3DGS", "en": "Headphones — trained 3DGS"}
    r = gsviewer.gs_viewer_html(gs, os.path.join(a.out, "headphones_trained.html"), title=title, lang=["ja", "en"], note=note,
                                camera={"yaw": -62.0, "pitch": 18.0})
    v.close()
    os.remove(npz)
    os.remove(gpath)
    print("trained: %d Gaussians, held-out PSNR %.2f dB (best), train PSNR %.2f dB, %.0f s on GPU"
          % (meta["n"], meta["best_test"], meta["train_psnr"], meta["seconds"]))
    print("viewer: %s  %.2f MB  dims %s mm" % (r["path"], r["bytes"] / 1048576, " x ".join("%.0f" % r["dims_mm"][k] for k in "WDH")))
    ok = r["external_urls"] == 0 and meta["best_test"] > 20.0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
