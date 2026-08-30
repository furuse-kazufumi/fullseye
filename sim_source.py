"""F4 sim-source アダプタ — 物理シミュが視覚 op に入力を供給する同一契約.

分業(honest, FullSense の核): **fullseye は物理をやらない**。RGB/depth/LiDAR/真値は
シミュ側(sim-source)が供給し、視覚 op(fullseye)がそれを計算する。sim-source は
OSS アダプタ(``oss_adapter.py``)と同じ F1〜F4 契約に従う: config オブジェクト + 動詞
メソッド + ``.backend`` / ``.available`` + 不在時は明示エラー(optional-extras)。

共通の動詞(要件 §5-F4):
  ``.intrinsics(cam)``   カメラ内部行列 K(GL 不要・fovy から算出)
  ``.rgb(cam)``          RGB フレーム(GL 描画)
  ``.depth(cam)``        メトリック深度(GL 描画)
  ``.point_cloud(cam)``  深度を逆投影した world 点群 → elevation_map 等の視覚 op が消費
  ``.ground_truth()``    真の body 姿勢(honest 評価の真値源・GL 不要)

MuJoCo は本環境で headless 描画が動く=実供給。Gazebo/IsaacSim は未接続の honest scaffold
(``.available=False``、動詞は「未接続」を明示 raise)。
"""
from __future__ import annotations

import numpy as np


class MuJoCo:
    """MuJoCo sim-source: RGB/深度を描画し、K を算出、真値姿勢を出し、深度を逆投影して
    world 点群にする(視覚 op が消費)。model は MjModel / .xml パス / XML 文字列を受ける。"""

    backend = "mujoco"
    available = True

    def __init__(self, model, data=None, width: int = 320, height: int = 240) -> None:
        import mujoco
        self._xml = None
        if isinstance(model, str):
            if model.strip().endswith(".xml"):
                self._xml = open(model, encoding="utf-8").read()
                model = mujoco.MjModel.from_xml_path(model)
            else:
                self._xml = model
                model = mujoco.MjModel.from_xml_string(model)
        self._m = model
        self._d = data if data is not None else mujoco.MjData(model)
        mujoco.mj_forward(self._m, self._d)
        self.width, self.height = int(width), int(height)
        self._renderer = None

    # -- カメラ列挙 / 解決 -------------------------------------------------
    def cameras(self) -> list:
        import mujoco
        names = [mujoco.mj_id2name(self._m, mujoco.mjtObj.mjOBJ_CAMERA, i)
                 for i in range(self._m.ncam)]
        return [n for n in names if n]

    def _cam_id(self, cam) -> int:
        import mujoco
        if isinstance(cam, int):
            return cam
        cid = mujoco.mj_name2id(self._m, mujoco.mjtObj.mjOBJ_CAMERA, cam)
        if cid < 0:
            raise ValueError(f"MuJoCo: camera {cam!r} not found. Candidates: {self.cameras()}")
        return cid

    # -- GL 不要 -----------------------------------------------------------
    def intrinsics(self, cam=0) -> np.ndarray:
        """内部行列 K(fovy=垂直画角 + 解像度から。正方画素前提 fx=fy)。"""
        cid = self._cam_id(cam)
        fovy = float(self._m.cam_fovy[cid])
        H, W = self.height, self.width
        fy = 0.5 * H / np.tan(np.radians(fovy) / 2.0)
        return np.array([[fy, 0.0, W / 2.0], [0.0, fy, H / 2.0], [0.0, 0.0, 1.0]])

    def ground_truth(self) -> dict:
        """真の body 姿勢 {name: (pos(3,), quat(4,))}(honest 評価の真値源)。"""
        import mujoco
        out = {}
        for b in range(self._m.nbody):
            nm = mujoco.mj_id2name(self._m, mujoco.mjtObj.mjOBJ_BODY, b)
            if nm:
                out[nm] = (self._d.xpos[b].copy(), self._d.xquat[b].copy())
        return out

    # -- カメラ外部姿勢(3DGS/NeRF データセット用) -----------------------
    def camera_to_world(self, cam=0) -> np.ndarray:
        """カメラ→世界の 4x4 変換(OpenGL 規約: -Z 前方 / +Y 上)。

        MuJoCo のカメラ frame はそのまま OpenGL 規約なので `cam_xmat` が c2w 回転、
        `cam_xpos` が原点になる。nerfstudio/3DGS の `transform_matrix` に直接使える。
        姿勢推定(COLMAP)が sim では不要 ―― これが sim-source の強み。"""
        cid = self._cam_id(cam)
        R = np.asarray(self._d.cam_xmat[cid]).reshape(3, 3)
        t = np.asarray(self._d.cam_xpos[cid])
        c2w = np.eye(4)
        c2w[:3, :3] = R
        c2w[:3, 3] = t
        return c2w

    def extrinsics(self, cam=0) -> np.ndarray:
        """世界→カメラの 4x4(w2c = camera_to_world の逆)。"""
        return np.linalg.inv(self.camera_to_world(cam))

    def project(self, pts_world: np.ndarray, cam=0):
        """世界点 (N,3) を画素 (u,v) と視線方向深度に投影(姿勢検証用)。

        戻り値 (uv(N,2), depth(N,)). OpenGL 規約(-Z 前方): 深度 = -z_cam、
        v は下向き画像座標に合わせて反転。camera_to_world/intrinsics の自己検証に使う。"""
        pts = np.atleast_2d(np.asarray(pts_world, dtype=float))
        w2c = self.extrinsics(cam)
        cam_pts = (w2c[:3, :3] @ pts.T).T + w2c[:3, 3]       # (N,3) カメラ座標
        z = -cam_pts[:, 2]                                    # -Z 前方 → 前方深度
        K = self.intrinsics(cam)
        fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
        u = cx + fx * (cam_pts[:, 0] / -cam_pts[:, 2])
        v = cy - fy * (cam_pts[:, 1] / -cam_pts[:, 2])
        return np.stack([u, v], axis=1), z

    # -- GL 描画 -----------------------------------------------------------
    def _rend(self):
        import mujoco
        if self._renderer is None:
            self._renderer = mujoco.Renderer(self._m, height=self.height, width=self.width)
        return self._renderer

    def close(self) -> None:
        """GL レンダラを明示的に閉じる(glfw 終了順ノイズの回避)。"""
        r = self._renderer
        self._renderer = None
        if r is not None:
            try:
                r.close()
            except Exception:
                pass

    def rgb(self, cam=0) -> np.ndarray:
        r = self._rend()
        r.disable_depth_rendering()
        r.update_scene(self._d, camera=cam)
        return r.render()

    def depth(self, cam=0) -> np.ndarray:
        r = self._rend()
        r.enable_depth_rendering()
        r.update_scene(self._d, camera=cam)
        dep = r.render().copy()
        r.disable_depth_rendering()
        return dep

    def save_gsplat_dataset(self, out_dir: str, cams=None, *, with_depth=False) -> str:
        """named カメラ群を 3DGS/nerfstudio 形式(transforms.json + images/)で書き出す。

        姿勢推定(COLMAP)不要 ―― c2w は camera_to_world() から直接。実写 3DGS に対する
        sim-source の優位点。多視点が要るときは capture_orbit()(モジュール関数)を使う。
        戻り値: transforms.json のパス。"""
        import os, json
        from PIL import Image as _PILImage
        cams = list(cams) if cams is not None else self.cameras()
        if not cams:
            raise RuntimeError("save_gsplat_dataset: no named cameras. Use capture_orbit() instead.")
        img_dir = os.path.join(out_dir, "images")
        os.makedirs(img_dir, exist_ok=True)
        K = self.intrinsics(cams[0])
        meta = {"w": int(self.width), "h": int(self.height),
                "fl_x": float(K[0, 0]), "fl_y": float(K[1, 1]),
                "cx": float(K[0, 2]), "cy": float(K[1, 2]),
                "camera_model": "PINHOLE", "frames": []}
        for i, cam in enumerate(cams):
            rgb = self.rgb(cam)
            fp = f"images/{i:04d}.png"
            _PILImage.fromarray(rgb).save(os.path.join(out_dir, fp))
            frame = {"file_path": fp,
                     "transform_matrix": self.camera_to_world(cam).tolist()}
            if with_depth:
                import numpy as _np
                dp = f"images/{i:04d}_depth.npy"
                _np.save(os.path.join(out_dir, dp), self.depth(cam))
                frame["depth_file_path"] = dp
            meta["frames"].append(frame)
        path = os.path.join(out_dir, "transforms.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        return path

    def _geom_local_mesh(self, g):
        """geom g を **local 座標**の Open3D メッシュにする(world 変換は呼び手が per-frame で適用)。
        アニメ再生で毎フレーム作り直さないための素材。未対応(plane/hfield)は None。"""
        import mujoco
        import open3d as o3d
        m = self._m
        t = int(m.geom_type[g]); size = m.geom_size[g]
        mesh = None
        if t == mujoco.mjtGeom.mjGEOM_SPHERE:
            mesh = o3d.geometry.TriangleMesh.create_sphere(radius=float(size[0]), resolution=12)
        elif t == mujoco.mjtGeom.mjGEOM_BOX:
            mesh = o3d.geometry.TriangleMesh.create_box(*(2.0 * size[:3]).tolist())
            mesh.translate((-size[:3]).tolist())                       # 原点中心へ
        elif t == mujoco.mjtGeom.mjGEOM_CYLINDER:
            mesh = o3d.geometry.TriangleMesh.create_cylinder(
                radius=float(size[0]), height=float(2.0 * size[1]), resolution=16)
        elif t == mujoco.mjtGeom.mjGEOM_CAPSULE:
            mesh = o3d.geometry.TriangleMesh.create_cylinder(
                radius=float(size[0]), height=float(2.0 * size[1]), resolution=16)
            for sgn in (1.0, -1.0):                                    # 両端の半球
                cap = o3d.geometry.TriangleMesh.create_sphere(radius=float(size[0]), resolution=12)
                cap.translate([0, 0, sgn * float(size[1])]); mesh += cap
        elif t == mujoco.mjtGeom.mjGEOM_ELLIPSOID:
            mesh = o3d.geometry.TriangleMesh.create_sphere(radius=1.0, resolution=12)
            mesh.vertices = o3d.utility.Vector3dVector(np.asarray(mesh.vertices) * size[:3])
        elif t == mujoco.mjtGeom.mjGEOM_MESH:
            did = int(m.geom_dataid[g])
            if did >= 0:
                va, vn = int(m.mesh_vertadr[did]), int(m.mesh_vertnum[did])
                fa, fn = int(m.mesh_faceadr[did]), int(m.mesh_facenum[did])
                V = np.asarray(m.mesh_vert[va:va + vn]).reshape(-1, 3).astype(float)
                F = np.asarray(m.mesh_face[fa:fa + fn]).reshape(-1, 3).astype(np.int32)
                mesh = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(V),
                                                 o3d.utility.Vector3iVector(F))
        if mesh is None:
            return None
        mesh.compute_vertex_normals()
        mesh.paint_uniform_color(np.asarray(m.geom_rgba[g])[:3].clip(0, 1).tolist())
        return mesh

    def scene_geometries(self, skip_plane: bool = True) -> list:
        """MuJoCo の geom を **実形状の Open3D メッシュ**に変換(world 変換・色つき)。
        evis/ロケット等のモデルを 3D 窓で「そのままの姿」で見るための橋。プリミティブ
        (sphere/box/capsule/cylinder/ellipsoid)と mesh に対応。plane/hfield は既定でスキップ
        (地面はビューアの grid が担う)。GL 不要=geometry 構築のみ(表示は viewer3d)。"""
        d = self._d
        geoms = []
        for g in range(self._m.ngeom):
            mesh = self._geom_local_mesh(g)
            if mesh is None:
                continue
            T = np.eye(4)
            T[:3, :3] = np.asarray(d.geom_xmat[g]).reshape(3, 3)
            T[:3, 3] = np.asarray(d.geom_xpos[g])
            mesh.transform(T)
            geoms.append(mesh)
        return geoms

    def point_cloud(self, cam=0, stride: int = 2, max_range: float | None = None) -> np.ndarray:
        """深度を逆投影した world 点群 (N,3)。背景(遠クリップ面)は除外。
        視覚 op(``elevation_map`` 等)にそのまま渡せる = sim→vision の橋。"""
        dep = self.depth(cam)
        cid = self._cam_id(cam)
        K = self.intrinsics(cam)
        fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
        H, W = dep.shape
        vs, us = np.mgrid[0:H:stride, 0:W:stride]
        z = dep[::stride, ::stride]
        far = float(z.max())
        keep = z < (max_range if max_range is not None else far * 0.99)
        # カメラ座標(右 x, 上 y, 前 -z)へ逆投影
        X = (us - cx) * z / fx
        Y = -(vs - cy) * z / fy
        Z = -z
        cam_pts = np.stack([X, Y, Z], axis=-1)[keep]
        # world へ: cam_xmat 列 = カメラ軸の world 表現 → world = R @ p + pos
        R = self._d.cam_xmat[cid].reshape(3, 3)
        pos = self._d.cam_xpos[cid]
        return cam_pts @ R.T + pos

    def segmentation(self, cam=0):
        """(H,W) の body id 画像(背景/未対応は -1)。動く 3DGS のリグ付けに使う。"""
        import mujoco
        r = self._rend()
        r.enable_segmentation_rendering()
        r.update_scene(self._d, camera=cam)
        seg = r.render().copy()
        r.disable_segmentation_rendering()
        gid = seg[..., 0]
        body = np.full(gid.shape, -1, dtype=np.int64)
        valid = (gid >= 0) & (gid < self._m.ngeom)
        body[valid] = self._m.geom_bodyid[gid[valid]]
        return body

    def point_cloud_seg(self, cam=0, stride: int = 2, max_range: float | None = None):
        """色付き world 点群 + body 帰属 (points(N,3), colors(N,3)uint8, body_ids(N,))。

        動く 3DGS(リグ付き)用: 各点がどの MuJoCo body 由来かを segmentation で確定。"""
        pts, cols = self.point_cloud_rgb(cam, stride=stride, max_range=max_range)
        # point_cloud_rgb と同じ keep マスクを再現して body を対応づける
        dep = self.depth(cam)
        z = dep[::stride, ::stride]
        far = float(z.max())
        keep = z < (max_range if max_range is not None else far * 0.99)
        body_img = self.segmentation(cam)[::stride, ::stride]
        bids = body_img[keep]
        return pts, cols, bids.astype(np.int64)

    def body_transforms(self):
        """全 body の (pos(3), quat(4)) を現在の状態で返す(list, index=body id)。"""
        return [(self._d.xpos[b].copy(), self._d.xquat[b].copy()) for b in range(self._m.nbody)]

    def point_cloud_rgb(self, cam=0, stride: int = 2, max_range: float | None = None):
        """色付き world 点群 (points(N,3), colors(N,3) uint8)。3DGS gaussian 初期化用。

        point_cloud と同一の逆投影(検証済み cam_xmat/cam_xpos 経路)+ 同画素の RGB。"""
        dep = self.depth(cam)
        cid = self._cam_id(cam)
        K = self.intrinsics(cam)
        fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
        H, W = dep.shape
        vs, us = np.mgrid[0:H:stride, 0:W:stride]
        z = dep[::stride, ::stride]
        far = float(z.max())
        keep = z < (max_range if max_range is not None else far * 0.99)
        X = (us - cx) * z / fx
        Y = -(vs - cy) * z / fy
        Z = -z
        cam_pts = np.stack([X, Y, Z], axis=-1)[keep]
        R = self._d.cam_xmat[cid].reshape(3, 3)
        pos = self._d.cam_xpos[cid]
        pts = cam_pts @ R.T + pos
        rgb = self.rgb(cam)[::stride, ::stride][keep]
        return pts, rgb.astype(np.uint8)

    def save_animation(self, scene_dir, qpos, fps: int = 30, title: str = "Fullseye 3D",
                       static_mesh=None) -> str:
        """モデル XML + qpos 軌道 (T, nq) をアニメバンドルに保存(別プロセス再生用)。
        rollout の qpos 列を渡すと歩行/着陸を『動き』で見られる。返り値 = manifest パス。
        XML 由来で構築した MuJoCo にのみ有効(再生側でモデルを再構築するため)。
        static_mesh(.ply パス)を渡すと、その静的メッシュ(SuGaR 地形等)も一緒に表示する。"""
        import json
        import os
        import shutil
        if self._xml is None:
            raise RuntimeError("save_animation requires an XML-derived MuJoCo instance (passing an MjModel directly is not supported)")
        os.makedirs(scene_dir, exist_ok=True)
        qpos = np.asarray(qpos, float)
        with open(os.path.join(scene_dir, "model.xml"), "w", encoding="utf-8") as fh:
            fh.write(self._xml)
        np.save(os.path.join(scene_dir, "qpos.npy"), qpos)
        spec = {"kind": "animation", "model": "model.xml", "frames": "qpos.npy",
                "fps": int(fps), "title": title, "n_frames": int(len(qpos))}
        if static_mesh and os.path.isfile(static_mesh):
            shutil.copy(static_mesh, os.path.join(scene_dir, "static.ply"))
            spec["static_mesh"] = "static.ply"
        manifest = os.path.join(scene_dir, "manifest.json")
        with open(manifest, "w", encoding="utf-8") as fh:
            json.dump(spec, fh, ensure_ascii=False)
        return manifest


def play_animation(manifest) -> bool:
    """アニメバンドルを Open3D 窓で再生(別プロセスの launcher が呼ぶ)。
    毎フレーム qpos を流し込み mj_forward → 各 geom の world 変換だけ更新(メッシュは再利用)。
    再生後はウィンドウを開いたまま(mouse ナビ可)。desktop GL が要る。"""
    import json
    import os
    import time
    import mujoco
    import open3d as o3d
    d = os.path.dirname(manifest)
    with open(manifest, encoding="utf-8") as fh:
        spec = json.load(fh)
    m = mujoco.MjModel.from_xml_string(open(os.path.join(d, spec["model"]), encoding="utf-8").read())
    data = mujoco.MjData(m)
    qpos = np.load(os.path.join(d, spec["frames"]))
    fps = int(spec.get("fps", 30)); title = spec.get("title", "Fullseye 3D")
    src = MuJoCo(m, data)
    # geom ごとに (local メッシュ, local 頂点) を一度だけ作る
    items = []
    for g in range(m.ngeom):
        mesh = src._geom_local_mesh(g)
        if mesh is not None:
            items.append((g, mesh, np.asarray(mesh.vertices).copy()))
    vis = o3d.visualization.Visualizer()
    vis.create_window(window_name=title, width=1000, height=760)
    opt = vis.get_render_option()
    opt.background_color = np.array([0.09, 0.10, 0.12]); opt.point_size = 3.0
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/spikes")
    try:
        import viewer3d as _v3d
        grid = _v3d.ground_grid()
        if grid is not None:
            vis.add_geometry(grid)
    except Exception:
        pass
    vis.add_geometry(o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.3))
    if spec.get("static_mesh"):                       # SuGaR 地形など静的メッシュを合成
        try:
            terr = o3d.io.read_triangle_mesh(os.path.join(d, spec["static_mesh"]))
            terr.compute_vertex_normals()
            vis.add_geometry(terr)
        except Exception:
            pass
    for _, mesh, _v in items:
        vis.add_geometry(mesh)

    def apply_frame(t):
        data.qpos[:] = qpos[t]; mujoco.mj_forward(m, data)
        for g, mesh, base in items:
            R = np.asarray(data.geom_xmat[g]).reshape(3, 3)
            pos = np.asarray(data.geom_xpos[g])
            mesh.vertices = o3d.utility.Vector3dVector(base @ R.T + pos)
            mesh.compute_vertex_normals()
            vis.update_geometry(mesh)

    apply_frame(0)
    vis.reset_view_point(True)
    dt = 1.0 / max(1, fps)
    for t in range(len(qpos)):        # 再生
        apply_frame(t)
        if not vis.poll_events():
            vis.destroy_window(); return True
        vis.update_renderer()
        time.sleep(dt)
    vis.run()                          # 再生後は静止表示のまま(閉じるまで)
    vis.destroy_window()
    return True


def launch_animation(model_xml, qpos, title: str = "Fullseye 3D", fps: int = 30,
                     static_mesh=None):
    """アニメを **別プロセス** で再生起動し Popen を返す(失敗時 None)。Studio を固めない。
    static_mesh(.ply)を渡すと SuGaR 地形等の静的メッシュも一緒に表示する。"""
    import os
    import subprocess
    import sys
    import tempfile
    try:
        scene_dir = tempfile.mkdtemp(prefix="fs3danim_")
        src = MuJoCo(model_xml)
        manifest = src.save_animation(scene_dir, qpos, fps=fps, title=title,
                                      static_mesh=static_mesh)
        launcher = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spikes", "anim_launch.py")
        exe = sys.executable
        pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.exists(pyw):
            exe = pyw
        kwargs = {"close_fds": True}
        if os.name == "nt":
            kwargs["creationflags"] = 0x00000008 | 0x08000000
        return subprocess.Popen([exe, launcher, manifest], **kwargs)
    except Exception as e:
        # None is documented as "no GL" — but a bad motion npy / missing mesh lands here too,
        # so leave a trace instead of erasing the difference (still fail-soft for callers).
        print(f"[launch_animation] suppressed {type(e).__name__}: {e}", flush=True)
        return None


class _Scaffold:
    """未接続の sim-source(optional-extras の honest scaffold)。動詞は明示 raise。"""
    available = False

    def __init__(self, *a, **k) -> None:
        pass

    def _na(self, *a, **k):
        raise RuntimeError(f"{self.backend} sim-source is not connected (optional). "
                           f"This environment uses MuJoCo; connecting {self.backend} requires a separate bridge.")

    cameras = intrinsics = rgb = depth = point_cloud = ground_truth = _na


class Gazebo(_Scaffold):
    """Gazebo sim-source(未接続 scaffold)。gz-transport ブリッジで RGB/depth/真値を供給予定。"""
    backend = "gazebo"


class IsaacSim(_Scaffold):
    """Isaac Sim sim-source(未接続 scaffold)。omni.replicator ブリッジで供給予定。"""
    backend = "isaacsim"


# (namespace, name, class, render_hint) — 統一 registry(F2/F3)へ登録するエントリ
SOURCES = [
    ("sim", "MuJoCo", MuJoCo, "point_cloud"),
    ("sim", "Gazebo", Gazebo, "point_cloud"),
    ("sim", "IsaacSim", IsaacSim, "point_cloud"),
]


def backends() -> dict:
    """{name: {'backend':..., 'available':...}} — どの sim-source が実供給できるか。"""
    return {name: {"backend": cls.backend, "available": bool(cls.available)}
            for _, name, cls, _ in SOURCES}


def _orbit_positions(n_views, radius, elevation_deg, lookat):
    """リング上の n_views カメラ位置とその lookat を返す。"""
    import math
    lookat = tuple(float(x) for x in lookat)
    el = math.radians(elevation_deg)
    z = lookat[2] + radius * math.sin(el)
    r_xy = radius * math.cos(el)
    out = []
    for i in range(int(n_views)):
        az = 2.0 * math.pi * i / float(n_views)
        out.append((lookat[0] + r_xy * math.cos(az),
                    lookat[1] + r_xy * math.sin(az), z))
    return out, lookat


def orbit_scene(scene_path: str, *, n_views: int = 24, radius: float = 2.0,
                elevation_deg: float = 25.0, lookat=(0.0, 0.0, 0.3),
                fovy: float = 45.0, width: int = 200, height: int = 200,
                keyframe: int | None = 0):
    """assets 付き実シーン(.xml)にオービットカメラを MjSpec 注入し MuJoCo を返す。

    from_xml_string ではメッシュ参照が壊れるため、MjSpec でカメラ追加 → compile。
    戻り値: (MuJoCo instance, cam_names)。姿勢は検証済み cam_xpos/cam_xmat 経路。"""
    import mujoco
    spec = mujoco.MjSpec.from_file(scene_path)
    positions, la = _orbit_positions(n_views, radius, elevation_deg, lookat)
    names = []
    for i, pos in enumerate(positions):
        xy = _look_at_xyaxes(pos, la)
        xc = np.asarray(xy[:3]); yc = np.asarray(xy[3:]); zc = np.cross(xc, yc)
        R = np.stack([xc, yc, zc], axis=1)          # 列 = カメラ軸
        q = np.zeros(4); mujoco.mju_mat2Quat(q, R.reshape(9))
        cam = spec.worldbody.add_camera()
        nm = f"orbit{i:04d}"
        cam.name = nm; cam.pos = list(pos); cam.quat = q.tolist(); cam.fovy = fovy
        names.append(nm)
    model = spec.compile()
    data = mujoco.MjData(model)
    if keyframe is not None and model.nkey > keyframe:
        mujoco.mj_resetDataKeyframe(model, data, keyframe)
    mujoco.mj_forward(model, data)
    return MuJoCo(model, data, width=width, height=height), names


def capture_orbit_scene(scene_path: str, out_dir: str, *, with_depth=False, **kw) -> str:
    """orbit_scene で実シーンを撮影し 3DGS データセット化。戻り値 transforms.json。"""
    s, names = orbit_scene(scene_path, **kw)
    try:
        return s.save_gsplat_dataset(out_dir, names, with_depth=with_depth)
    finally:
        s.close()


def _look_at_xyaxes(pos, target, world_up=(0.0, 0.0, 1.0)):
    """カメラ位置 pos から target を見る MuJoCo camera の xyaxes(x,y の 6 値)。

    カメラ frame: +X 右 / +Y 上 / -Z 前方(視線)。z=-forward, x=up×z, y=z×x。"""
    pos = np.asarray(pos, float); target = np.asarray(target, float)
    f = target - pos
    n = np.linalg.norm(f)
    if n < 1e-9:
        raise ValueError("_look_at_xyaxes: pos and target coincide")
    f = f / n
    up = np.asarray(world_up, float)
    if abs(float(np.dot(f, up))) > 0.999:                 # 視線が up と平行 → 退避軸
        up = np.array([0.0, 1.0, 0.0])
    zc = -f                                               # camera +Z は視線の逆
    xc = np.cross(up, zc); xc /= np.linalg.norm(xc)       # 右
    yc = np.cross(zc, xc)                                 # 上(既に正規)
    return list(xc) + list(yc)


def capture_orbit(base_xml: str, out_dir: str, *, n_views: int = 24,
                  radius: float = 2.0, elevation_deg: float = 30.0,
                  lookat=(0.0, 0.0, 0.0), fovy: float = 45.0,
                  width: int = 400, height: int = 400, with_depth: bool = False) -> str:
    """base シーンをオービット多視点で撮り 3DGS/nerfstudio データセット化する。

    リング上に n_views 台の named カメラを XML 注入 → 検証済みの cam_xpos/cam_xmat 経路で
    c2w を得る(姿勢は sim ground-truth、COLMAP 不要)。戻り値: transforms.json パス。"""
    import math
    lookat = tuple(float(x) for x in lookat)
    el = math.radians(elevation_deg)
    z = lookat[2] + radius * math.sin(el)
    r_xy = radius * math.cos(el)
    cams_xml = []
    for i in range(int(n_views)):
        az = 2.0 * math.pi * i / float(n_views)
        px = lookat[0] + r_xy * math.cos(az)
        py = lookat[1] + r_xy * math.sin(az)
        xy = _look_at_xyaxes((px, py, z), lookat)
        cams_xml.append(
            f'<camera name="orbit{i:04d}" pos="{px:.6f} {py:.6f} {z:.6f}" '
            f'fovy="{fovy}" xyaxes="{" ".join(f"{v:.6f}" for v in xy)}"/>')
    inject = "".join(cams_xml)
    if "</worldbody>" not in base_xml:
        raise ValueError("capture_orbit: base_xml has no </worldbody>")
    xml = base_xml.replace("</worldbody>", inject + "</worldbody>", 1)
    s = MuJoCo(xml, width=width, height=height)
    try:
        cams = [f"orbit{i:04d}" for i in range(int(n_views))]
        return s.save_gsplat_dataset(out_dir, cams, with_depth=with_depth)
    finally:
        s.close()


if __name__ == "__main__":
    xml = ('<mujoco><worldbody><light pos="0 0 2"/>'
           '<geom type="box" size=".1 .1 .1" pos="0 0 .5"/>'
           '<camera name="c" pos="0 -1 .5" xyaxes="1 0 0 0 0 1"/></worldbody></mujoco>')
    s = MuJoCo(xml, width=160, height=120)
    print("cameras:", s.cameras(), "backend:", s.backend)
    print("K=\n", np.round(s.intrinsics("c"), 1))
    pc = s.point_cloud("c")
    print("point_cloud:", pc.shape, "centroid≈", np.round(pc.mean(0), 2), "(box at 0,0,0.5)")
    print("ground_truth keys:", list(s.ground_truth())[:4])
    print("backends:", backends())
