"""共通 I/F(unified)の op を決まった手順で呼ぶと実現するレシピ。

  『3DGS 地形を SuGaR でメッシュ化し、その上を evis がメッシュで歩く』

手順(すべて u.ops[...] = 共通 I/F 経由):
  1. sugar_mesh(terrain)   … 地形シーンを 3DGS→表面整列→Poisson でメッシュ抽出
  2. animate_mesh(walker, static_mesh=terrain)
                            … 歩行 qpos で walker の真値メッシュを再生(地形メッシュを合成)

interactive=True で desktop 窓を開く(要 desktop GL)。False では合成バンドルだけ作って
manifest を返す(headless 検証用)。
"""
from __future__ import annotations
import os

import numpy as np


def world_walk(out_dir, *, terrain="terrain", walker="evis", motion="walk",
               z_offset=0.16, iters=1400, res=220, mesh_method="tsdf",
               interactive=True, log=print):
    import unified as u
    import scene_registry as R
    import sim_source as S
    if mesh_method == "sugar":
        import fullseye_3dgs as F
        F.setup_cuda_env()          # SuGaR は GPU 必須(TSDF は sim 深度のみで不要)
    os.makedirs(out_dir, exist_ok=True)

    # --- 手順1: 地形をメッシュ化(共通 I/F op)。tsdf=GPU不要・清潔、sugar=3DGS由来 ---
    tspec = R.resolve(terrain)
    if tspec is None:
        raise ValueError(f"terrain '{terrain}' が未登録")
    fr = dict(radius=tspec["radius"], elevation_deg=tspec["elevation_deg"], lookat=tspec["lookat"])
    if mesh_method == "tsdf":
        tr = u.ops["tsdf_mesh"](tspec["xml"], os.path.join(out_dir, "terrain"),
                                n_views=48, res=res, voxel=0.02, log=log, **fr)
    else:
        tr = u.ops["sugar_mesh"](tspec["xml"], os.path.join(out_dir, "terrain"),
                                 n_views=40, iters=iters, res=res, n_gauss_init=9000,
                                 flatten=0.03, log=log, **fr)
    terrain_ply = tr["mesh_ply"]
    log(f"terrain mesh: {tr['vertices']} 頂点 -> {terrain_ply}")

    # --- 手順2: walker のメッシュを地形の上で歩かせる(共通 I/F: animate_mesh op)---
    wspec = R.resolve(walker)
    mpath = R.motion(walker, motion)
    if wspec is None or mpath is None:
        raise ValueError(f"walker '{walker}' / motion '{motion}' が未解決")
    qpos = np.load(mpath).copy()
    qpos[:, 2] += z_offset                       # 地形の上へ持ち上げる(視覚合成)
    xml = open(wspec["xml"], encoding="utf-8").read()

    if interactive:
        proc = u.ops["animate_mesh"](xml, qpos, title=f"{walker} walks on {terrain}",
                                     static_mesh=terrain_ply)
        log("desktop 窓で再生起動(evis on SuGaR terrain)")
        return {"terrain_ply": terrain_ply, "launched": proc is not None}
    # headless: 合成バンドルだけ作る(窓は開かない)
    src = S.MuJoCo(xml)
    manifest = src.save_animation(os.path.join(out_dir, "compose"), qpos,
                                  fps=30, title=f"{walker} on {terrain}",
                                  static_mesh=terrain_ply)
    src.close()
    return {"terrain_ply": terrain_ply, "manifest": manifest,
            "n_frames": int(len(qpos)), "vertices": tr["vertices"]}


if __name__ == "__main__":
    import sys
    r = world_walk(sys.argv[1] if len(sys.argv) > 1 else "world_walk_out",
                   interactive=("--headless" not in sys.argv),
                   log=lambda m: print(m, flush=True))
    print("DONE", r)
