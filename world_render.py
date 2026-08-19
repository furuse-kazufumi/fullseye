"""walker(四足/人型)を terrain 上で歩かせた姿を **headless で GIF 化**する。

Open3D の OffscreenRenderer は Windows で EGL 非対応のため、両者を 1 つの MuJoCo
XML に合成し MuJoCo 自身の offscreen renderer(この環境で headless 動作可)で描画する。
terrain も walker も MuJoCo geom なので単一モデルに畳める。物理シミュレーションはせず、
qpos を流し込み mj_forward の運動学だけで各フレームを描く(視覚合成)。

  import world_render as WR
  WR.render_walk_gif("out/go2_on_rolling.gif", walker="go2", terrain="rolling", gait="trot")
"""
from __future__ import annotations
import math
import re

import numpy as np


def _compose_xml(walker_xml: str, terrain_xml: str) -> str:
    """terrain の worldbody 内 geom を walker XML の worldbody へ注入(light は walker 側)。"""
    tbody = terrain_xml.split("<worldbody>", 1)[1].rsplit("</worldbody>", 1)[0]
    geoms = "".join(re.findall(r"<geom[^>]*/>", tbody))
    if "</worldbody>" not in walker_xml:
        raise ValueError("walker XML に </worldbody> が無い")
    return walker_xml.replace("</worldbody>", geoms + "</worldbody>", 1)


def _walk_qpos(walker: str, motion=None, gait=None, n_frames=90):
    """motion 名(npz)or gait 名から qpos(F, nq)を得る。"""
    import mujoco
    import scene_registry as R
    spec = R.resolve(walker)
    if spec is None:
        raise ValueError(f"walker '{walker}' 未登録")
    xml = open(spec["xml"], encoding="utf-8").read()
    mpath = R.motion(walker, motion) if (motion or not gait) else None
    if mpath:
        return xml, np.load(mpath).astype(float)
    if gait:
        import gaits as G
        m = mujoco.MjModel.from_xml_string(xml)
        d = mujoco.MjData(m); mujoco.mj_forward(m, d)
        q = G.build(m, np.asarray(d.qpos), gait, n_frames=n_frames)
        if q is None:
            raise ValueError(f"gait '{gait}' はこのモデルで生成不可")
        return xml, q.astype(float)
    raise ValueError("motion 名か gait を指定")


def render_walk_gif(out_gif, *, walker="go2", terrain="rolling", motion=None, gait=None,
                    z_offset=0.0, n_frames=90, width=640, height=480, fps=30,
                    max_gif_frames=90, orbit_deg=140.0, elevation=-18.0, distance=None,
                    lookat=(0, 0, 0.25), log=print):
    """walker を terrain 上で歩かせた姿を headless で GIF 保存。戻り値 dict。

    motion(npz 名)か gait(trot 等)のどちらかを指定。z_offset で walker を地形上へ持ち上げる。
    カメラは lookat を中心に orbit_deg だけ周回(歩行と地形の起伏を見せる)。
    """
    import mujoco
    import scene_registry as R
    from PIL import Image
    wxml, q = _walk_qpos(walker, motion=motion, gait=gait, n_frames=n_frames)
    tspec = R.resolve(terrain)
    if tspec is None:
        raise ValueError(f"terrain '{terrain}' 未登録")
    txml = open(tspec["xml"], encoding="utf-8").read()
    cxml = _compose_xml(wxml, txml)
    m = mujoco.MjModel.from_xml_string(cxml)
    d = mujoco.MjData(m)
    if q.shape[1] != m.nq:
        raise ValueError(f"motion nq={q.shape[1]} が合成モデル nq={m.nq} と不一致")
    q = q.copy(); q[:, 2] += float(z_offset)
    ext = float(np.max([abs(v) for v in tspec.get("lookat", [0, 0, 0])]) + tspec.get("radius", 3.0))
    dist = float(distance if distance is not None else max(3.2, tspec.get("radius", 3.0) * 1.35))

    ren = mujoco.Renderer(m, height=height, width=width)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = list(lookat); cam.distance = dist; cam.elevation = float(elevation)
    N = len(q)
    step = max(1, N // int(max_gif_frames))
    idxs = list(range(0, N, step))
    frames = []
    for k, t in enumerate(idxs):
        d.qpos[:] = q[t]; mujoco.mj_forward(m, d)
        cam.azimuth = 90.0 + orbit_deg * (k / max(1, len(idxs) - 1))
        ren.update_scene(d, camera=cam)
        frames.append(Image.fromarray(ren.render()))
    ren.close()
    frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / max(1, fps)), loop=0)
    log(f"headless GIF: {len(frames)} frames ({walker} on {terrain}) -> {out_gif}")
    return {"gif": out_gif, "frames": len(frames), "n_geom": int(m.ngeom), "nq": int(m.nq)}


if __name__ == "__main__":
    import sys
    walker = sys.argv[1] if len(sys.argv) > 1 else "go2"
    out = sys.argv[2] if len(sys.argv) > 2 else f"out/{walker}_on_rolling.gif"
    kw = dict(gait="trot") if walker in ("go2", "anymal", "spot") else dict(motion="walk", z_offset=0.16)
    render_walk_gif(out, walker=walker, terrain="rolling", log=lambda m: print(m, flush=True), **kw)
