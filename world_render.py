"""walker(四足/人型)を terrain 上で歩かせた姿を **headless で GIF 化**する。

Open3D の OffscreenRenderer は Windows で EGL 非対応のため、両者を 1 つの MuJoCo
モデルに合成し MuJoCo 自身の offscreen renderer(この環境で headless 動作可)で描画する。
合成は MjSpec で行う(walker を from_file でロード=<include>/mesh を解決、terrain の
geom を worldbody に追加して compile)。物理シミュレーションはせず qpos を流し込み
mj_forward の運動学だけで各フレームを描く(視覚合成)。

  import world_render as WR
  WR.render_walk_gif("out/go2_on_rolling.gif", walker="go2", terrain="rolling", gait="trot")
"""
from __future__ import annotations
import re

import numpy as np

_GEOM_T = {"box": "mjGEOM_BOX", "ellipsoid": "mjGEOM_ELLIPSOID", "sphere": "mjGEOM_SPHERE",
           "capsule": "mjGEOM_CAPSULE", "cylinder": "mjGEOM_CYLINDER", "plane": "mjGEOM_PLANE"}


def _attr(tag, name):
    m = re.search(rf'{name}="([^"]*)"', tag)
    return m.group(1) if m else None


def _add_terrain_geoms(spec, terrain_xml, log):
    """terrain XML の <geom .../> を MjSpec の worldbody に primitive として追加。"""
    import mujoco
    tbody = terrain_xml.split("<worldbody>", 1)[1].rsplit("</worldbody>", 1)[0]
    wb = spec.worldbody
    n = 0
    for tag in re.findall(r"<geom[^>]*/>", tbody):
        gt = _attr(tag, "type") or "sphere"
        if gt not in _GEOM_T:
            continue
        g = wb.add_geom()
        g.type = getattr(mujoco.mjtGeom, _GEOM_T[gt])
        size = _attr(tag, "size"); pos = _attr(tag, "pos"); rgba = _attr(tag, "rgba")
        sz = [float(x) for x in size.split()] if size else [0.1, 0.1, 0.1]
        sz = (sz + [0.0, 0.0, 0.0])[:3]                     # MjSpec は size 長 3 を要求
        g.size = sz
        if pos:
            g.pos = [float(x) for x in pos.split()]
        if rgba:
            g.rgba = [float(x) for x in rgba.split()]
        g.contype = 0; g.conaffinity = 0                   # 視覚のみ(衝突不要)
        n += 1
    log(f"terrain geoms 注入: {n}")
    return n


def _build_model(walker, terrain, log):
    import mujoco
    import scene_registry as R
    wspec = R.resolve(walker); tspec = R.resolve(terrain)
    if wspec is None or tspec is None:
        raise ValueError(f"walker '{walker}' / terrain '{terrain}' の解決に失敗")
    spec = mujoco.MjSpec.from_file(wspec["xml"])            # include/mesh 解決つき
    _add_terrain_geoms(spec, open(tspec["xml"], encoding="utf-8").read(), log)
    return spec.compile(), tspec


def _walk_qpos(walker, motion=None, gait=None, n_frames=90):
    """motion 名(npz)or gait 名から qpos(F, nq)を得る。gait 用モデルは include 解決込み。"""
    import mujoco
    import scene_registry as R
    spec = R.resolve(walker)
    mpath = R.motion(walker, motion) if (motion or not gait) else None
    if mpath:
        return np.load(mpath).astype(float)
    if gait:
        import gaits as G
        m = mujoco.MjModel.from_xml_path(spec["xml"])       # from_path=include 解決
        d = mujoco.MjData(m); mujoco.mj_forward(m, d)
        q = G.build(m, np.asarray(d.qpos), gait, n_frames=n_frames)
        if q is None:
            raise ValueError(f"gait '{gait}' はこのモデルで生成不可")
        return q.astype(float)
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
    from PIL import Image
    q = _walk_qpos(walker, motion=motion, gait=gait, n_frames=n_frames)
    m, tspec = _build_model(walker, terrain, log)
    if q.shape[1] != m.nq:
        raise ValueError(f"motion nq={q.shape[1]} が合成モデル nq={m.nq} と不一致")
    q = q.copy(); q[:, 2] += float(z_offset)
    d = mujoco.MjData(m)
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
