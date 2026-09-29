"""ballworld — 卓球台と球(模様つき)の真値つき合成世界(17 巡目): 世界の側が軌道・姿勢・接触時刻・模様の位置を持つ。

台は ITTF の規格(長さ 2.74 m、幅 1.525 m、高さ 0.76 m、ネット高 15.25 cm・長さ 1.83 m、側線・端線 2 cm、中央線 3 mm)。球は正 20 面体を
分割した球面メッシュ(半径 20 mm)で、模様(marker)は指定した向きから ``marker_angle`` 以内の面を黒く塗る。姿勢は (中心 p, 回転 R)。
描画は :func:`driveworld.world_camera`(色・ラベル・深度・面 id)。真値の投影は :func:`balltrack.reproject`。

ラベル: 20 table / 21 line / 22 net / 23 ball / 24 marker / 25 floor / 26 handle(けん玉)。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "BALL_LABELS", "table_params", "table_world", "ball_mesh", "add_ball", "ball_set_pose", "rotation_from_omega",
    "camera_rig", "ball_truth", "icosphere",
]

BALL_LABELS = {20: "table", 21: "line", 22: "net", 23: "ball", 24: "marker", 25: "floor", 26: "handle"}


def table_params(length: float = 2.74, width: float = 1.525, height: float = 0.76, net_height: float = 0.1525,
                 net_length: float = 1.83, line_width: float = 0.02, centre_line: float = 0.003) -> dict:
    """卓球台の表(既定 = ITTF 規格)。"""
    if min(length, width, height, net_height, net_length, line_width, centre_line) <= 0:
        raise ValueError("all table dimensions must be positive")
    return {"length": float(length), "width": float(width), "height": float(height), "net_height": float(net_height),
            "net_length": float(net_length), "line_width": float(line_width), "centre_line": float(centre_line)}


def _quad(x0, x1, y0, y1, z):
    V = np.array([[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]], np.float64)
    F = np.array([[0, 1, 2], [0, 2, 3]], np.int64)
    return V, F


def _box(x0, x1, y0, y1, z0, z1):
    V = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], np.float64)
    F = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
                  [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]], np.int64)
    return V, F


def table_world(tp: dict = None, *, floor: bool = True, floor_size: float = 8.0) -> dict:
    """台(天板 + 白線 + ネット)と床の世界。原点 = 天板の中心、x = 長手(±1.37)、y = 幅(±0.7625)、z 上。天板の上面 z = height。"""
    import driveworld as DW
    tp = tp or table_params()
    L, Wd, H = tp["length"], tp["width"], tp["height"]
    world = DW._empty_world()
    if floor:
        V, F = _quad(-floor_size / 2, floor_size / 2, -floor_size / 2, floor_size / 2, 0.0)
        DW.world_add(world, V, F, 25, (0.55, 0.52, 0.48), name="floor")
    V, F = _box(-L / 2, L / 2, -Wd / 2, Wd / 2, H - 0.03, H)
    DW.world_add(world, V, F, 20, (0.06, 0.22, 0.48), name="table")
    lw, z = tp["line_width"], H + 0.0005
    for (x0, x1, y0, y1) in ((-L / 2, L / 2, -Wd / 2, -Wd / 2 + lw), (-L / 2, L / 2, Wd / 2 - lw, Wd / 2),
                             (-L / 2, -L / 2 + lw, -Wd / 2, Wd / 2), (L / 2 - lw, L / 2, -Wd / 2, Wd / 2),
                             (-L / 2, L / 2, -tp["centre_line"] / 2, tp["centre_line"] / 2)):
        V, F = _quad(x0, x1, y0, y1, z)
        DW.world_add(world, V, F, 21, (0.95, 0.95, 0.95), name="line")
    # ネット = 上端の白いテープ(1.5 cm)+ 支柱 2 本 + 4 cm ごとの細い縦糸(描画器に透明は無いので、板でなく糸の列で「向こうが見える」)
    nl, nh = tp["net_length"], tp["net_height"]
    V, F = _box(-0.002, 0.002, -nl / 2, nl / 2, H + nh - 0.015, H + nh)
    DW.world_add(world, V, F, 22, (0.95, 0.95, 0.95), name="net_tape")
    for y in (-nl / 2, nl / 2):
        V, F = _box(-0.01, 0.01, y - 0.01, y + 0.01, H, H + nh)
        DW.world_add(world, V, F, 22, (0.25, 0.25, 0.28), name="net_post")
    ys = np.arange(-nl / 2 + 0.04, nl / 2 - 0.02, 0.04)
    Vs, Fs = [], []
    for y in ys:
        V, F = _box(-0.001, 0.001, y - 0.001, y + 0.001, H, H + nh - 0.015)
        Fs.append(F + 8 * len(Vs))
        Vs.append(V)
    DW.world_add(world, np.vstack(Vs), np.vstack(Fs), 22, (0.15, 0.15, 0.18), name="net_strings")
    world["bounds"] = (-L / 2, L / 2, -Wd / 2, Wd / 2)
    world["table"] = tp
    return world


def icosphere(radius: float = 1.0, subdiv: int = 3):
    """正 20 面体を ``subdiv`` 回 4 分割して球面へ射影したメッシュ (V, F)(外向き)。"""
    if radius <= 0 or subdiv < 0:
        raise ValueError("radius > 0, subdiv ≥ 0")
    t = (1.0 + np.sqrt(5.0)) / 2.0
    V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
                  [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], np.float64)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    F = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2],
                  [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5],
                  [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]], np.int64)
    for _ in range(subdiv):
        cache = {}
        Vl = list(V)
        F2 = []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                m = Vl[a] + Vl[b]
                m /= np.linalg.norm(m)
                cache[key] = len(Vl)
                Vl.append(m)
            return cache[key]

        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            F2 += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        V = np.asarray(Vl)
        F = np.asarray(F2, np.int64)
    return V * radius, F


def ball_mesh(radius: float = 0.02, subdiv: int = 3, color=(1.0, 0.55, 0.05), marker_dir=(0.0, 0.0, 1.0),
              marker_angle: float = 25.0, marker_color=(0.05, 0.05, 0.05), markers=None) -> dict:
    """球のメッシュ(原点 = 中心)と模様。``markers`` = [(dir, angle_deg), …] で複数の模様(None なら marker_dir 1 つ)。
    返り値 ``{"V", "F", "color" (M,3), "label" (M,) (23 or 24), "radius", "markers": [単位ベクトル …]}``。"""
    V, F = icosphere(radius, subdiv)
    cen = V[F].mean(axis=1)
    cen /= np.linalg.norm(cen, axis=1, keepdims=True)
    C = np.tile(np.asarray(color, np.float64), (len(F), 1))
    Lb = np.full(len(F), 23, np.int64)
    dirs = []
    for d, ang in (markers if markers is not None else [(marker_dir, marker_angle)]):
        d = np.asarray(d, np.float64)
        d = d / np.linalg.norm(d)
        m = cen @ d > np.cos(np.radians(ang))
        C[m] = np.asarray(marker_color, np.float64)
        Lb[m] = 24
        dirs.append(d)
    return {"V": V, "F": F, "color": C, "label": Lb, "radius": float(radius), "markers": dirs}


def add_ball(world: dict, mesh: dict, p, R=None, *, name: str = "ball") -> int:
    """球を姿勢 (p, R) で世界に足す。面ごとのラベル(球 23 / 模様 24)はそのまま。返り値 = objects の索引。"""
    import driveworld as DW
    p = np.asarray(p, np.float64).reshape(3)
    R = np.eye(3) if R is None else np.asarray(R, np.float64).reshape(3, 3)
    Vw = mesh["V"] @ R.T + p
    i = DW.world_add(world, Vw, mesh["F"], 23, mesh["color"], name=name,
                     extra={"local": mesh["V"].copy(), "center": p.copy(), "R": R.copy(), "radius": mesh["radius"],
                            "markers": [np.asarray(d, np.float64) for d in mesh["markers"]]})
    f0, f1 = world["objects"][i]["faces"]
    world["face_label"][f0:f1] = mesh["label"]
    return i


def ball_set_pose(world: dict, i: int, p, R) -> None:
    """球 i の姿勢を (p, R) にする(頂点だけ書き換える)。"""
    obj = world["objects"][i]
    if "local" not in obj:
        raise ValueError("objects[%d] is not a ball (use add_ball)" % i)
    p = np.asarray(p, np.float64).reshape(3)
    R = np.asarray(R, np.float64).reshape(3, 3)
    v0, v1 = obj["verts"]
    world["V"][v0:v1] = obj["local"] @ R.T + p
    obj["center"] = p.copy()
    obj["R"] = R.copy()


def rotation_from_omega(omega, dt: float) -> np.ndarray:
    """角速度 ω [rad/s] で dt 秒回す回転行列(Rodrigues)。R_{k+1} = R(ω dt) R_k。"""
    w = np.asarray(omega, np.float64).reshape(3)
    th = float(np.linalg.norm(w)) * dt
    if th < 1e-15:
        return np.eye(3)
    a = w / np.linalg.norm(w)
    Kx = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * Kx @ Kx


def camera_rig(tp: dict = None, *, n: int = 2, distance: float = 2.2, height: float = 1.7, fov_deg: float = 55.0,
               width: int = 1280, height_px: int = 1024) -> list:
    """台を囲むカメラ(n = 2: 両端の斜め上、n = 4: 4 隅)。返り値 ``[{"pose", "K", "eye"}, …]``、全部が台の中心を見る。"""
    import driveworld as DW
    tp = tp or table_params()
    L, Wd, H = tp["length"], tp["width"], tp["height"]
    target = np.array([0.0, 0.0, H + 0.1])
    if n == 2:
        eyes = [(-L / 2 - distance, Wd / 2 + 0.6, height), (L / 2 + distance, -Wd / 2 - 0.6, height)]
    elif n == 4:
        eyes = [(-L / 2 - distance, -Wd / 2 - distance * 0.5, height), (L / 2 + distance, -Wd / 2 - distance * 0.5, height),
                (L / 2 + distance, Wd / 2 + distance * 0.5, height), (-L / 2 - distance, Wd / 2 + distance * 0.5, height)]
    else:
        raise ValueError("n must be 2 or 4")
    K = DW.camera_intrinsics(fov_deg, width, height_px)
    return [{"pose": DW.camera_pose(e, target), "K": K, "eye": np.asarray(e, np.float64), "width": width, "height": height_px}
            for e in eyes]


def ball_truth(world: dict, i: int, cam: dict) -> dict:
    """球 i の真値の投影: 中心の (col, row)、像の半径 [px] (≈ f·r/深度)、模様の中心の (col, row)(裏側なら NaN)。"""
    import balltrack as BT
    obj = world["objects"][i]
    p = obj["center"]
    R = obj["R"]
    uv = BT.reproject(p[None], cam["pose"], cam["K"])[0]
    T = np.asarray(cam["pose"], np.float64)
    pc = T[:3, :3] @ p + T[:3, 3]
    depth = -pc[2]
    rad_px = float(cam["K"][0, 0] * obj["radius"] / depth) if depth > 0 else float("nan")
    marks = []
    for d in obj["markers"]:
        dw = R @ d                                   # 模様の向き(世界)
        q = p + obj["radius"] * dw
        qc = T[:3, :3] @ q + T[:3, 3]
        visible = (qc - pc) @ (-pc) > 0             # 模様がカメラ側の半球にある
        m_uv = BT.reproject(q[None], cam["pose"], cam["K"])[0]
        marks.append(m_uv if visible else np.array([np.nan, np.nan]))
    return {"uv": uv, "radius_px": rad_px, "depth": float(depth), "markers_uv": np.asarray(marks).reshape(-1, 2)}
