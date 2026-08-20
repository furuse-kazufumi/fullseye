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
        g.group = 1                                        # 地形専用 group(接地レイキャスト用)
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


def _walk_qpos(walker, motion=None, gait=None, n_frames=90, travel=0.0):
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
        q = G.build(m, np.asarray(d.qpos), gait, n_frames=n_frames, travel=travel)
        if q is None:
            raise ValueError(f"gait '{gait}' はこのモデルで生成不可")
        return q.astype(float)
    raise ValueError("motion 名か gait を指定")


def _terrain_height(m, d, x, y, geomgroup):
    """(x,y) 直上から地面へレイを落とし terrain(group1)表面の z を返す(無交差は 0)。"""
    import mujoco
    pnt = np.array([float(x), float(y), 3.0]); vec = np.array([0.0, 0.0, -1.0])
    gid = np.array([-1], np.int32)
    dist = mujoco.mj_ray(m, d, pnt, vec, geomgroup, True, -1, gid)
    return (3.0 - dist) if dist >= 0 else 0.0


_FOOT_HINTS = ("foot", "calf", "shank", "lower_leg", "lowerleg", "toe", "wheel")


def _foot_geoms(m):
    """歩行体の接地点になりうる geom(足先/下腿)の id を返す。名前で拾えないモデルでは
    「地形(group1)以外の全 geom」にフォールバック(=最下点で接地判定)。"""
    import mujoco
    ids = []
    for g in range(m.ngeom):
        b = int(m.geom_bodyid[g])
        nm = (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b) or "").lower()
        if any(h in nm for h in _FOOT_HINTS):
            ids.append(g)
    if not ids:                                            # 名前で拾えない→terrain以外を全部
        ids = [g for g in range(m.ngeom) if int(m.geom_group[g]) != 1]
    return ids


def _ground_snap(m, d, foot_ids, ggroup):
    """各足 geom 直下の terrain 高さにレイを落とし、最も低い足がちょうど接地するのに必要な
    root z の下げ量(=足底と地形の最小ギャップ)を返す。d は事前に mj_forward 済みのこと。"""
    import mujoco
    min_gap = None
    for g in foot_ids:
        fx, fy, fz = d.geom_xpos[g]
        bottom = float(fz) - float(m.geom_rbound[g])       # 足 geom の最下点(外接球半径)
        tz = _terrain_height(m, d, fx, fy, ggroup)
        gap = bottom - tz
        if min_gap is None or gap < min_gap:
            min_gap = gap
    return min_gap if min_gap is not None else 0.0


def render_walk_gif(out_gif, *, walker="go2", terrain="rolling", motion=None, gait=None,
                    z_offset=0.0, travel=0.0, track=None, ground_follow=None, foot_clear=0.0,
                    n_frames=90, width=640, height=480,
                    fps=30, max_gif_frames=90, orbit_deg=140.0, elevation=-18.0, distance=None,
                    lookat=(0, 0, 0.25), log=print):
    """walker を terrain 上で歩かせた姿を headless で GIF 保存。戻り値 dict。

    motion(npz 名)か gait(trot 等)のどちらかを指定。z_offset で walker を地形上へ持ち上げる。
    travel>0 で gait を前進させ地形を横断(root x を移動)。track で True にするとカメラ lookat が
    root x を追従(既定は travel>0 のとき自動追従)。カメラは lookat 中心に orbit_deg 周回。
    """
    import mujoco
    from PIL import Image
    q = _walk_qpos(walker, motion=motion, gait=gait, n_frames=n_frames, travel=travel)
    if track is None:
        track = travel > 0
    if ground_follow is None:
        ground_follow = travel > 0                          # 横断時は地形に接地させる
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
    base_lx = float(lookat[0])
    ggroup = np.zeros(6, np.uint8); ggroup[1] = 1           # terrain(group1)のみレイ対象
    foot_ids = _foot_geoms(m)
    mujoco.mj_forward(m, d)                                 # static geom 位置を確定
    for k, t in enumerate(idxs):
        d.qpos[:] = q[t]
        if ground_follow:
            # まず root 直下の地形高さで概算リフト → forward → 各足直下の地形を見て、最も低い
            # 足がちょうど接地するよう root z を微修正(起伏に沿って全足が地形に触れる)。
            hz = _terrain_height(m, d, q[t, 0], q[t, 1], ggroup)
            d.qpos[2] = q[t, 2] + hz
            mujoco.mj_forward(m, d)
            gap = _ground_snap(m, d, foot_ids, ggroup)     # 最下足と地形の隙間
            d.qpos[2] -= (gap - float(foot_clear))         # 隙間を詰めて接地(foot_clear=余裕)
        mujoco.mj_forward(m, d)
        cam.azimuth = 90.0 + orbit_deg * (k / max(1, len(idxs) - 1))
        if track:
            cam.lookat[0] = base_lx + float(q[t, 0])       # 移動する root x を追従
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
    if walker in ("go2", "anymal", "spot"):
        kw = dict(gait="trot", travel=2.2, ground_follow=True)   # 地形を接地しながら横断
    else:
        kw = dict(motion="walk", z_offset=0.16)
    render_walk_gif(out, walker=walker, terrain="rolling", log=lambda m: print(m, flush=True), **kw)
