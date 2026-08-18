"""Fullseye Studio 3D ビューア adapter — Open3D 連携(RViz2 相当の 3D 知覚可視化, F6).

要件 F6: 「Studio = HDevelop(2D)+ RViz2(3D: 点群/6D pose/mesh/grid)」の 3D 側を、
再実装せず Open3D を裏に据えて実現する。統一 registry の op 出力(render_hint)を Open3D
geometry へ変換し、① 対話ウィンドウ(mouse ナビ=RViz2 相当)② PLY エクスポート
③ オフスクリーン画像(GL 可なら)で見せる。Open3D 不在/GL 不可でも graceful に劣化。

  geoms = to_geometries(result, "point_cloud")   # 純 geometry 構築(GL 不要=テスト可)
  show_interactive(geoms)                         # Open3D 対話ウィンドウ(desktop GL)
  img = render_offscreen(geoms)                   # 画像 or None(EGL headless 不可なら None)
  export_ply(geoms, "scene.ply")                  # 常に可(外部ビューアで開ける)

★環境注意: EGL headless オフスクリーンは一部 Windows で不可([[reference_mujoco_gl_remote_desktop]])。
対話ウィンドウは desktop GL で動く。オフスクリーン不可時 Studio は matplotlib 3D にフォールバック。
"""
from __future__ import annotations

import numpy as np


_VERBOSITY_SET = False


def available() -> bool:
    """Open3D が import できるか(optional extra)。冗長ログは抑制。"""
    global _VERBOSITY_SET
    try:
        import open3d as o3d
        if not _VERBOSITY_SET:
            try:
                o3d.utility.set_verbosity_level(o3d.utility.VerbosityLevel.Error)
            except Exception:
                pass
            _VERBOSITY_SET = True
        return True
    except Exception:
        return False


# ── op 出力(render_hint)→ Open3D geometry(GL 不要)──────────────────────────── #
def _cloud_geometry(pts, colormap="viridis"):
    import open3d as o3d
    import matplotlib
    pts = np.asarray(pts, float).reshape(-1, 3)
    pc = o3d.geometry.PointCloud()
    pc.points = o3d.utility.Vector3dVector(pts)
    if len(pts):
        z = pts[:, 2]
        zn = (z - z.min()) / (z.ptp() + 1e-9)
        pc.colors = o3d.utility.Vector3dVector(matplotlib.colormaps[colormap](zn)[:, :3])
    return pc


def _frame_geometry(R, t, size=0.4):
    import open3d as o3d
    f = o3d.geometry.TriangleMesh.create_coordinate_frame(size=size)
    T = np.eye(4); T[:3, :3] = np.asarray(R, float); T[:3, 3] = np.asarray(t, float).ravel()[:3]
    f.transform(T)
    return f


def _mesh_geometry(points, triangles):
    import open3d as o3d
    m = o3d.geometry.TriangleMesh()
    m.vertices = o3d.utility.Vector3dVector(np.asarray(points, float).reshape(-1, 3))
    m.triangles = o3d.utility.Vector3iVector(np.asarray(triangles, int).reshape(-1, 3))
    m.compute_vertex_normals()
    m.paint_uniform_color([0.6, 0.7, 0.85])
    return m


def to_geometries(result, hint) -> list:
    """op 出力を render_hint に応じた Open3D geometry のリストへ(GL 不要)。
    3D 化できないもの(image/region/contour 等)は空リスト(→ Studio は 2D 側で描く)。"""
    if not available():
        return []
    import open3d as o3d
    geoms = []
    if hint == "point_cloud":
        pts = result
        if isinstance(result, dict):
            pts = result.get("points", result.get("points_3d", result.get("point_3d")))
        pts = np.asarray(pts, float)
        if pts.ndim == 2 and pts.shape[1] == 3 and len(pts):
            geoms.append(_cloud_geometry(pts))
            geoms.append(o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.3))
        # mesh(dict {points, triangles})
        if isinstance(result, dict) and "triangles" in result and "points" in result:
            geoms.append(_mesh_geometry(result["points"], result["triangles"]))
    elif hint == "pose":
        R, t = np.eye(3), np.zeros(3)
        if isinstance(result, np.ndarray) and result.shape == (4, 4):
            R, t = result[:3, :3], result[:3, 3]
        elif isinstance(result, dict):
            R = np.asarray(result.get("R", np.eye(3)))
            t = np.asarray(result.get("t", np.zeros(3))).ravel()[:3]
        geoms.append(_frame_geometry(R, t, size=0.5))
        geoms.append(o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.25))  # world 原点
    return geoms


def ground_grid(size=3.0, n=13):
    """z=0 の地面グリッド(RViz2 の Grid Display 相当)。"""
    if not available():
        return None
    import open3d as o3d
    lines, pts = [], []
    xs = np.linspace(-size, size, n)
    for i, x in enumerate(xs):
        pts += [[x, -size, 0], [x, size, 0], [-size, x, 0], [size, x, 0]]
        base = i * 4
        lines += [[base, base + 1], [base + 2, base + 3]]
    ls = o3d.geometry.LineSet()
    ls.points = o3d.utility.Vector3dVector(np.asarray(pts, float))
    ls.lines = o3d.utility.Vector2iVector(np.asarray(lines, int))
    ls.paint_uniform_color([0.6, 0.6, 0.6])
    return ls


# ── 表示バックエンド ────────────────────────────────────────────────────────── #
def show_interactive(geometries, title="Fullseye 3D", grid=True) -> bool:
    """Open3D 対話ウィンドウで表示(mouse ナビ=RViz2 相当)。desktop GL が要る。
    Visualizer API で常用品質に: 暗背景 / 点サイズ / world 原点軸 / 見やすい初期ビュー。
    ★ブロッキング(閉じるまで戻らない)。Studio からは launch_detached を使う(非ブロック)。"""
    if not available() or not geometries:
        return False
    import open3d as o3d
    geoms = list(geometries)
    if grid and (g := ground_grid()) is not None:
        geoms.append(g)
    geoms.append(o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.3))  # world 原点
    try:
        vis = o3d.visualization.Visualizer()
        vis.create_window(window_name=title, width=1000, height=760)
        for g in geoms:
            vis.add_geometry(g)
        opt = vis.get_render_option()
        opt.background_color = np.array([0.09, 0.10, 0.12])   # 暗背景(点群が映える)
        opt.point_size = 3.0
        opt.show_coordinate_frame = False
        vc = vis.get_view_control()
        vc.set_front([0.4, -0.7, 0.55]); vc.set_up([0, 0, 1])
        vc.set_lookat(geoms[0].get_center() if hasattr(geoms[0], "get_center") else [0, 0, 0])
        vc.set_zoom(0.8)
        vis.run()
        vis.destroy_window()
        return True
    except Exception:
        # Visualizer が使えない環境は素の draw_geometries に劣化
        try:
            o3d.visualization.draw_geometries(geoms, window_name=title, width=1000, height=760)
            return True
        except Exception:
            return False


def render_offscreen(geometries, width=480, height=360):
    """オフスクリーンで numpy 画像へ。GL(EGL)不可なら None(→ Studio は matplotlib に fallback)。"""
    if not available() or not geometries:
        return None
    import open3d as o3d
    try:
        r = o3d.visualization.rendering.OffscreenRenderer(width, height)
    except Exception:
        return None
    try:
        mat = o3d.visualization.rendering.MaterialRecord(); mat.shader = "defaultUnlit"
        all_pts = []
        for i, g in enumerate(geometries):
            r.scene.add_geometry(f"g{i}", g, mat)
            if hasattr(g, "get_center"):
                all_pts.append(np.asarray(g.get_center()))
        center = np.mean(all_pts, axis=0) if all_pts else np.zeros(3)
        r.setup_camera(60.0, center, center + [2, -2, 2], [0, 0, 1])
        return np.asarray(r.render_to_image())
    except Exception:
        return None


def export_ply(geometries, path) -> bool:
    """geometry を .ply へ書き出し(GL 不要=常に可。外部 Open3D/CloudCompare/RViz2 で開ける)。"""
    if not available() or not geometries:
        return False
    import open3d as o3d
    merged_cloud = o3d.geometry.PointCloud()
    merged_mesh = o3d.geometry.TriangleMesh()
    has_cloud = has_mesh = False
    for g in geometries:
        if isinstance(g, o3d.geometry.PointCloud):
            merged_cloud += g; has_cloud = True
        elif isinstance(g, o3d.geometry.TriangleMesh):
            merged_mesh += g; has_mesh = True
    if has_mesh:
        o3d.io.write_triangle_mesh(str(path), merged_mesh)
    elif has_cloud:
        o3d.io.write_point_cloud(str(path), merged_cloud)
    else:
        return False
    return True


def save_scene(geometries, scene_dir) -> str:
    """geometry リストを scene_dir に PLY バンドル化(clouds/meshes)+ manifest.json。
    別プロセス起動(desktop 常用)の受け渡し用。返り値 = manifest パス。"""
    import json
    import os
    if not available():
        return ""
    import open3d as o3d
    os.makedirs(scene_dir, exist_ok=True)
    entries = []
    for i, g in enumerate(geometries):
        if isinstance(g, o3d.geometry.PointCloud) and len(g.points):
            fn = f"g{i}_cloud.ply"
            o3d.io.write_point_cloud(os.path.join(scene_dir, fn), g)
            entries.append({"kind": "cloud", "file": fn})
        elif isinstance(g, o3d.geometry.TriangleMesh) and len(g.vertices):
            fn = f"g{i}_mesh.ply"
            o3d.io.write_triangle_mesh(os.path.join(scene_dir, fn), g)
            entries.append({"kind": "mesh", "file": fn})
        # LineSet(grid 等)は launcher 側で再生成するので保存しない
    manifest = os.path.join(scene_dir, "manifest.json")
    with open(manifest, "w", encoding="utf-8") as fh:
        json.dump({"entries": entries}, fh)
    return manifest


def load_scene(manifest) -> list:
    """save_scene の manifest から geometry リストを復元(別プロセスの launcher 用)。"""
    import json
    import os
    if not available():
        return []
    import open3d as o3d
    scene_dir = os.path.dirname(manifest)
    with open(manifest, encoding="utf-8") as fh:
        spec = json.load(fh)
    geoms = []
    for e in spec.get("entries", []):
        path = os.path.join(scene_dir, e["file"])
        if e["kind"] == "cloud":
            geoms.append(o3d.io.read_point_cloud(path))
        elif e["kind"] == "mesh":
            m = o3d.io.read_triangle_mesh(path)
            m.compute_vertex_normals()
            geoms.append(m)
    return geoms


def launch_detached(geometries, title="Fullseye 3D") -> bool:
    """3D ウィンドウを **別プロセス** で起動(desktop 常用: Studio を固めない/GL 落ちを隔離)。
    geometry を一時 PLY バンドルに保存し、viewer3d_launch.py を detached 起動して即戻る。"""
    import os
    import subprocess
    import sys
    import tempfile
    if not available() or not geometries:
        return False
    try:
        scene_dir = tempfile.mkdtemp(prefix="fs3d_")
        manifest = save_scene(geometries, scene_dir)
        if not manifest:
            return False
        launcher = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewer3d_launch.py")
        # console flash 回避: pythonw があれば優先(GUI サブプロセスにコンソール窓を出さない)
        exe = sys.executable
        pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.exists(pyw):
            exe = pyw
        kwargs = {"close_fds": True}
        if os.name == "nt":
            # DETACHED_PROCESS | CREATE_NO_WINDOW(コンソール窓を出さず親から独立)
            kwargs["creationflags"] = 0x00000008 | 0x08000000
        subprocess.Popen([exe, launcher, manifest, title], **kwargs)
        return True
    except Exception:
        return False


def backend_status() -> dict:
    """3D バックエンドの honest な能力レポート(Studio が表示)。"""
    st = {"open3d": available(), "offscreen": False, "interactive": "desktop GL 依存"}
    if available():
        try:
            import open3d as o3d
            o3d.visualization.rendering.OffscreenRenderer(64, 64)
            st["offscreen"] = True
        except Exception:
            st["offscreen"] = False
    return st


if __name__ == "__main__":
    print("== Fullseye viewer3d(Open3D 連携)==")
    print("backend:", backend_status())
    rng = np.random.default_rng(0)
    cloud = rng.random((300, 3))
    geoms = to_geometries(cloud, "point_cloud")
    print(f"point_cloud -> {len(geoms)} geometry")
    pose = np.eye(4); pose[:3, 3] = [0.5, 0.2, 0.3]
    print(f"pose -> {len(to_geometries(pose, 'pose'))} geometry")
    img = render_offscreen(geoms)
    print("offscreen image:", None if img is None else img.shape,
          "(None=EGL 不可 → Studio は matplotlib 3D)")
    ok = export_ply(geoms, __import__("os").path.join(
        __import__("os").path.dirname(__file__), "out_gallery", "viewer3d_demo.ply"))
    print("export_ply:", ok, "(外部 Open3D で開ける)")
