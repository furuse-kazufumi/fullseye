"""kendamaworld — けん玉(けん + 皿胴 + 3 つの皿 + 穴のある玉 + 糸)の真値つき合成世界と、画像だけから玉の軌道を予測する知覚
(18 巡目、ballworld の上に載る別モジュール: ballworld は触らない)。

**形**(寸法は :func:`kendama.kendama_params` の kp。公表値・ユーザー提供の JKA 16-2 型の説明・仮定の区別はそちらの docstring):
 - けん(剣): x 軸まわりの回転体。けん先(+x の端、玉の穴に入る短い円柱 + 丸い先)→ 細い首 → 皿胴を貫く胴 → 下へ太くなる握り
   (段と盛り上がった輪)→ 中皿(−x の端、外向きに開いた浅い皿)。けん先 → 中皿の縁 = ``ken_length``(160 mm)。
 - 皿胴: けんと直角(z 軸)の短く太い円柱で、両端がラッパのように開いて大皿(+z)・小皿(−z)になる(凹んだ皿)。
   大皿の縁 〜 小皿の縁 = ``width``(70 mm)。皿胴の中心はけん先から ``cross_from_tip``。
 - 玉: 直径 60 mm の球 + 大きな穴(くぼみ: 直径 = 2·hole_radius、暗い壁と底、極から hole_depth の深さ)。穴の軸は玉の局所座標の
   :data:`HOLE_AXIS_LOCAL`(玉は穴の軸まわりの回転体なので、穴の軸の両端に頂点がある)。糸穴は大きな穴の反対側(-HOLE_AXIS_LOCAL)と置く。
 - 糸: 皿胴の糸穴(手元 + kp["tie_offset"])→ 玉の糸穴(玉の表面)を結ぶ細い角柱。弛んでいても真っ直ぐに描く(描画の簡略化)。

**局所座標**: 原点 = 皿胴の中心、けん = +x(けん先が +x)、皿胴の軸 = +z(大皿が +z)。世界へは kp の技の姿勢
(kp["R_ken"]、持つ所 kp["grip"] を手元に)で置く(:func:`kendama_pose`)。
ラベル: 27 けん・皿胴の胴、28 大皿、29 糸、30 小皿、31 中皿、32 玉の穴(玉 23、床 25 は ballworld と同じ)。
色: けん = 木、大皿 = 赤、小皿 = 紫、中皿 = 青、玉 = 橙、穴 = 暗い茶、糸 = 暗い灰(ラベルごとに見分けがつくように)。

**知覚**(:func:`camera_perceiver`): 世界を描き、橙の玉を色度で検出し、DLT で三角測量し、ひもが弛んだ(画像から: 玉と糸穴の距離が
ひもの長さより margin 以上短い)後のコマに重力つきの放物線を当てて (p̂, v̂) を返す。真値 (p, v) は **描画のためだけ** に使う。
寸法の辞書 ``kp`` は ``kendama.kendama_params`` の返り値(ここでは辞書の鍵だけを見る。kendama を import しない)。
"""
from __future__ import annotations

import time

import numpy as np

import ballworld as BW
import driveworld as DW

__all__ = [
    "KEN_LABELS", "ken_mesh", "add_ken", "ken_set_pose", "string_mesh", "add_string", "string_set",
    "kendama_world", "kendama_rig", "ken_truth", "kendama_pose", "camera_perceiver", "kendama_clearance",
]

KEN_LABELS = {27: "ken", 28: "big_cup", 29: "string", 30: "small_cup", 31: "base_cup", 32: "ball_hole"}

CUP_WALL = 0.0                  #: 皿の縁の上の平らな幅 [m]: 0 = 鋭い縁(玉は縁の半径 r_c の円に乗る = 物理の r_c と同じ所)
_BOWL = (0.97, 0.85, 0.6, 0.3)   #: 皿の内側の輪郭: 縁の半径の割合 f で深さ d·√(1 − f²)(楕円の皿: 縁の近くで急に深い = 玉は縁にだけ触れる)
STRING_COLOR = (0.18, 0.18, 0.20)
CUP_COLOR = (0.85, 0.15, 0.15)   #: 大皿
SMALL_CUP_COLOR = (0.55, 0.30, 0.72)
BASE_CUP_COLOR = (0.20, 0.45, 0.82)
KEN_COLOR = (0.75, 0.55, 0.35)
BALL_COLOR = (1.0, 0.55, 0.05)
HOLE_COLOR = (0.10, 0.06, 0.03)
#: 玉の局所座標での大きな穴の軸(向きは任意: 玉は この軸まわりの回転体で作る。値は以前の icosphere の頂点 (0, 1, φ) の向きのまま)
HOLE_AXIS_LOCAL = np.array([0.0, 1.0, (1.0 + 5 ** 0.5) / 2.0]) / np.linalg.norm([0.0, 1.0, (1.0 + 5 ** 0.5) / 2.0])

_KP_KEYS = ("ball_radius", "string", "pendulum_length", "cup_radius_big", "cup_radius_small", "cup_radius_base", "cup_depth",
            "cup_depth_small", "cup_depth_base", "ken_length", "width", "cross_radius", "ken_radius", "cross_from_tip",
            "hole_radius", "hole_depth")


def _check_kp(kp: dict) -> dict:
    """寸法の辞書を検証(鍵が揃い、全部が正で有限、けんの輪郭が組める長さ)。tie_offset / cup_offset / cup_axis も写す。"""
    if not isinstance(kp, dict):
        raise ValueError("kp must be a dict (kendama.kendama_params)")
    missing = [k for k in _KP_KEYS + ("tie_offset", "cup_offset", "cup_axis") if k not in kp]
    if missing:
        raise ValueError("kp lacks keys: %s" % ", ".join(missing))
    out = {k: float(kp[k]) for k in _KP_KEYS}
    if not all(np.isfinite(v) for v in out.values()) or min(out.values()) <= 0:
        raise ValueError("all kendama dimensions must be positive and finite")
    for k in ("cup_radius_big", "cup_radius_small", "cup_radius_base"):
        if out[k] <= max(CUP_WALL, out["cross_radius"] if k != "cup_radius_base" else out["ken_radius"]) + 0.002:
            raise ValueError("%s must exceed the body it flares from" % k)
    if out["ken_length"] - out["cross_from_tip"] < 0.057 or out["cross_from_tip"] <= out["cross_radius"] + 0.004:
        raise ValueError("ken_length / cross_from_tip too short to build the ken profile")
    if out["width"] < 0.045:
        raise ValueError("width too small for the cross piece (needs ≥ 45 mm for two cups and the body)")
    for k in ("tie_offset", "cup_offset", "cup_axis"):
        a = np.asarray(kp[k], np.float64).reshape(-1)
        if a.shape != (3,) or not np.all(np.isfinite(a)):
            raise ValueError("%s must be a finite (3,) vector" % k)
        out[k] = a.copy()
    R = np.asarray(kp.get("R_ken", np.eye(3)), np.float64).reshape(3, 3)
    if not np.all(np.isfinite(R)) or np.abs(R @ R.T - np.eye(3)).max() > 1e-9 or np.linalg.det(R) < 0:
        raise ValueError("R_ken must be a rotation")
    out["R_ken"] = R
    out["grip"] = np.asarray(kp.get("grip", np.zeros(3)), np.float64).reshape(3).copy()
    out["catch_cup"] = str(kp.get("catch_cup", "big"))
    if out["catch_cup"] not in ("big", "small", "base"):
        raise ValueError("catch_cup must be big / small / base")
    return out


def _revolve(profile, n: int = 24):
    """(r, z) の閉じた輪郭を z 軸まわりに n 分割で回した閉メッシュ (V, F)。輪郭は r–z 平面で反時計回り(面積 > 0)に並べると外向き。
    r = 0 の点は軸上の 1 頂点に潰す(軸上の 2 点を結ぶ区間は面を作らない)。"""
    prof = [(float(r), float(z)) for r, z in profile]
    if len(prof) < 3 or n < 3:
        raise ValueError("profile needs ≥ 3 points and n ≥ 3")
    th = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    c, s = np.cos(th), np.sin(th)
    Vs, start, axis = [], [], []
    for r, z in prof:
        start.append(sum(len(v) for v in Vs))
        if r == 0.0:
            Vs.append(np.array([[0.0, 0.0, z]]))
            axis.append(True)
        else:
            Vs.append(np.column_stack([r * c, r * s, np.full(n, z)]))
            axis.append(False)
    V = np.vstack(Vs)
    F = []
    m = len(prof)
    for k in range(m):
        k1 = (k + 1) % m
        if axis[k] and axis[k1]:
            continue
        for j in range(n):
            j1 = (j + 1) % n
            A = start[k] if axis[k] else start[k] + j
            B = start[k] if axis[k] else start[k] + j1
            C = start[k1] if axis[k1] else start[k1] + j1
            D = start[k1] if axis[k1] else start[k1] + j
            if axis[k]:
                F.append([A, C, D])
            elif axis[k1]:
                F.append([A, B, C])
            else:
                F.append([A, B, C])
                F.append([A, C, D])
    return V, np.asarray(F, np.int64)


def _profile_area(profile) -> float:
    """輪郭 (r, z) の符号つき面積(反時計回りで正)。"""
    P = np.asarray(profile, np.float64)
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _ken_profile(k: dict):
    """けんの輪郭 (r, s)(s = けんの軸、+s がけん先、原点 = 皿胴の中心)。中皿の底 → 縁 → 握りの段と輪 → 皿胴の下で細く →
    首 → けん先(穴に入る部分は穴の半径より細い)。反時計回り。"""
    s_t = k["cross_from_tip"]
    s_b = -(k["ken_length"] - k["cross_from_tip"])
    rc, rci, d3 = k["cup_radius_base"], k["cup_radius_base"] - CUP_WALL, k["cup_depth_base"]
    hr, hd, cr, kr = k["hole_radius"], k["hole_depth"], k["cross_radius"], k["ken_radius"]
    r_sp = min(0.0075, 0.88 * hr)                      # けん先の円柱(穴より細い)
    r_neck = min(0.97 * hr, kr - 0.0008)              # 穴の口の高さの首(穴より細い)
    grip = max(kr + 0.0043, 0.7 * rc)                 # 握りの太さ(皿胴の下の細い所から中皿へ向けて太くなる)
    bowl = [(f * rci, s_b + d3 * (1.0 - f * f) ** 0.5) for f in reversed(_BOWL)]
    return [(0.0, s_b + d3)] + bowl + ([(rci, s_b)] if rci < rc else []) + [(rc, s_b), (rc, s_b + 0.003),
            (grip, s_b + 0.016), (grip, s_b + 0.026), (grip + 0.0015, s_b + 0.028), (grip + 0.0015, s_b + 0.034),
            (grip - 0.0005, s_b + 0.036), (kr - 0.0005, -cr - 0.004), (kr - 0.0005, cr + 0.002), (r_neck, s_t - hd),
            (r_sp, s_t - hd + 0.004), (r_sp, s_t - 0.004), (0.6 * r_sp, s_t - 0.001), (0.0, s_t)]


def _cross_profile(k: dict):
    """皿胴の輪郭 (r, z)(z = 皿胴の軸、+z が大皿、原点 = 皿胴の中心)。小皿の底 → 小皿の縁 → ラッパ → 胴 → ラッパ → 大皿の縁 → 大皿の底。"""
    hz = 0.5 * k["width"]
    rs, rb, rx = k["cup_radius_small"], k["cup_radius_big"], k["cross_radius"]
    ds, db = k["cup_depth_small"], k["cup_depth"]
    fl = 0.020                                        # ラッパの長さ(縁から胴まで)
    rsi, rbi = rs - CUP_WALL, rb - CUP_WALL
    small = [(f * rsi, -hz + ds * (1.0 - f * f) ** 0.5) for f in reversed(_BOWL)]
    big = [(f * rbi, hz - db * (1.0 - f * f) ** 0.5) for f in _BOWL]
    return [(0.0, -hz + ds)] + small + ([(rsi, -hz)] if rsi < rs else []) + [(rs, -hz), (rs, -hz + 0.0015),
            (rx + 0.35 * (rs - rx), -hz + 0.006), (rx + 0.1 * (rs - rx), -hz + 0.012), (rx, -hz + fl),
            (rx, hz - fl), (rx + 0.1 * (rb - rx), hz - 0.012), (rx + 0.35 * (rb - rx), hz - 0.006), (rb, hz - 0.0015),
            (rb, hz)] + ([(rbi, hz)] if rbi < rb else []) + big + [(0.0, hz - db)]


_Z_TO_X = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])   # 回転体の軸 z → けんの軸 +x(det = +1)


def ken_mesh(kp: dict, *, n: int = 32) -> dict:
    """けん + 皿胴(大皿・小皿)+ 中皿のメッシュ。原点 = 皿胴の中心(手元)、けん = +x(けん先が +x)、皿胴の軸 = +z(大皿が上)。

    面ラベル: 27 けん・皿胴の胴、28 大皿(皿胴の +z のラッパと皿)、30 小皿(−z)、31 中皿(けんの −x の端の開いた部分)。
    返り値 ``{"V", "F", "color" (M,3), "label" (M,), "parts": {"ken": (f0, f1), "cross": (f0, f1)}, "anchors": {...},
    "cup_radius", "cup_depth", "ken_length"}``。anchors(局所座標)= ``cross`` (0 = 皿胴の中心)、``spike_tip``、``base_rim``(中皿の縁の中心)、
    ``big_rim``(大皿の縁の中心)、``small_rim``、``tie``(皿胴の糸穴 (0, −cross_radius, 0))、``big_axis`` (+z)、``small_axis`` (−z)、
    ``base_axis`` (−x)、``ken_axis`` (+x)、``grip``(技の持つ所 = kp["grip"])。
    2 つの閉じた回転体(けん・皿胴)は交わって置かれる(描画は深度で解く)。面は全部外向き(符号つき体積 > 0)。"""
    k = _check_kp(kp)
    kp_ = _ken_profile(k)
    cp_ = _cross_profile(k)
    if _profile_area(kp_) <= 0 or _profile_area(cp_) <= 0:
        raise ValueError("profile is not counter-clockwise (dimensions out of range)")
    s = np.array([z for _, z in kp_])
    i_rim = int(np.flatnonzero(s == s.min())[-1])                 # 中皿の縁の外の角から先(外側の輪郭)は s が単調に増える
    if np.any(np.diff(s[i_rim:]) < -1e-12):
        raise ValueError("ken profile is not monotone (dimensions out of range)")
    Vk, Fk = _revolve(kp_, n)
    Vk = Vk @ _Z_TO_X.T
    Vc, Fc = _revolve(cp_, n)
    V = np.vstack([Vk, Vc])
    F = np.vstack([Fk, Fc + len(Vk)])
    s_b = -(k["ken_length"] - k["cross_from_tip"])
    ck = Vk[Fk].mean(axis=1)
    cc = Vc[Fc].mean(axis=1)
    lab_k = np.where(ck[:, 0] < s_b + 0.012, 31, 27)
    hz = 0.5 * k["width"]
    lab_c = np.where(cc[:, 2] > hz - 0.020 + 1e-9, 28, np.where(cc[:, 2] < -hz + 0.020 - 1e-9, 30, 27))
    Lb = np.concatenate([lab_k, lab_c]).astype(np.int64)
    pal = {27: KEN_COLOR, 28: CUP_COLOR, 30: SMALL_CUP_COLOR, 31: BASE_CUP_COLOR}
    C = np.array([pal[int(x)] for x in Lb], np.float64)
    anchors = {"cross": np.zeros(3), "spike_tip": np.array([k["cross_from_tip"], 0.0, 0.0]), "base_rim": np.array([s_b, 0.0, 0.0]),
               "big_rim": np.array([0.0, 0.0, hz]), "small_rim": np.array([0.0, 0.0, -hz]),
               "tie": np.array([0.0, -k["cross_radius"], 0.0]), "big_axis": np.array([0.0, 0.0, 1.0]),
               "small_axis": np.array([0.0, 0.0, -1.0]), "base_axis": np.array([-1.0, 0.0, 0.0]), "ken_axis": np.array([1.0, 0.0, 0.0]),
               "grip": k["grip"].copy()}
    return {"V": V, "F": F, "color": C, "label": Lb, "parts": {"ken": (0, len(Fk)), "cross": (len(Fk), len(Fk) + len(Fc))},
            "anchors": anchors, "cup_radius": k["cup_radius_big"], "cup_depth": k["cup_depth"], "ken_length": k["ken_length"]}


def _ball_mesh_with_hole(kp: dict, subdiv: int = 3) -> dict:
    """玉 = 穴の軸まわりの回転体(:func:`_revolve`): 球面(直径 60 mm、橙)は穴の縁(軸からの角 asin(r_h / r_b))で終わり、そこから
    **くぼみ**(暗い壁 + 底、ラベル 32)が穴の底まで入る。底の高さ = 中心から r_b − hole_depth(穴の深さは極から測る: けん先を底まで
    挿すと全長 180 mm、:func:`kendama_params`)。穴の反対の極に頂点がある(糸穴、全長の門)。赤道の輪は偶数分割(直径が厳密に 2 r_b)。

    以前は「玉の表面から 0.3 mm 浮かせた暗い円盤」だった: メッシュの描画では穴に見えるが、3D Gaussian Splatting(gsplatnp)は
    ガウシアンを中心の深さで並べて重ねるため、斜めから見ると手前の玉のガウシアンが円盤を覆って穴が消えた(40 姿勢で 0 回検出、
    メッシュでは 14 回)。本物の穴はくぼみなので、形のほうを本物に合わせた。``subdiv`` は緯度の刻みの細かさ(2 → 12・3 → 16・4 → 24 段)。
    穴の軸 = :data:`HOLE_AXIS_LOCAL`。ラベル 23(玉)/ 32(穴の壁と底)。"""
    k = _check_kp(kp)
    rb, rh, hd = k["ball_radius"], k["hole_radius"], k["hole_depth"]
    if not (0.0 < rh < rb and rh < hd < 2.0 * rb):
        raise ValueError("need 0 < hole_radius < ball_radius and hole_radius < hole_depth < 2 ball_radius")
    n_lat = {1: 8, 2: 12, 3: 16}.get(int(subdiv), 24)
    a_rim = float(np.arcsin(rh / rb))                                  # 穴の縁の、軸からの角
    # 南極(糸穴の側)から穴の縁まで: 軸からの角 π → a_rim。赤道(π/2)を必ず通す
    ang = np.unique(np.concatenate([np.linspace(np.pi, a_rim, n_lat + 1), [0.5 * np.pi]]))[::-1]
    prof = [(0.0 if abs(t - np.pi) < 1e-15 else rb * np.sin(t), rb * np.cos(t)) for t in ang]
    prof[-1] = (rh, float(np.sqrt(rb * rb - rh * rh)))                # 縁は厳密に
    z_rim, z_bot = prof[-1][1], rb - hd
    n_wall = max(2, int(np.ceil((z_rim - z_bot) / (0.25 * rh))))
    prof += [(rh, z) for z in np.linspace(z_rim, z_bot, n_wall + 1)[1:]] + [(0.0, z_bot)]
    V, F = _revolve(prof, 32)
    n_sphere_rings = len(ang)
    # 面の区分: 輪郭の区間 k(k → k + 1)が球面か、くぼみか。_revolve は区間ごとに n(または 2n)枚を順に出す
    cols, labs = [], []
    for kk in range(len(prof)):
        k1 = (kk + 1) % len(prof)
        on_axis = (prof[kk][0] == 0.0, prof[k1][0] == 0.0)
        if on_axis[0] and on_axis[1]:
            continue
        m = 32 if (on_axis[0] or on_axis[1]) else 64
        hole = kk >= n_sphere_rings - 1
        cols.append(np.tile(np.asarray(HOLE_COLOR if hole else BALL_COLOR, np.float64), (m, 1)))
        labs.append(np.full(m, 32 if hole else 23, np.int64))
    C = np.vstack(cols)
    Lb = np.concatenate(labs)
    assert len(C) == len(F)
    a = HOLE_AXIS_LOCAL
    Rh = _rot_from_to(np.array([0.0, 0.0, 1.0]), a)
    return {"V": V @ Rh.T, "F": F, "color": C, "label": Lb, "radius": rb, "markers": [], "hole_axis": a.copy()}


def _rot_from_to(a, b) -> np.ndarray:
    """単位ベクトル a を b に回す最小の回転行列(Rodrigues)。反平行なら a に直交な軸まわりに π。"""
    a = np.asarray(a, np.float64) / np.linalg.norm(a)
    b = np.asarray(b, np.float64) / np.linalg.norm(b)
    c = float(a @ b)
    v = np.cross(a, b)
    s = float(np.linalg.norm(v))
    if s < 1e-12:
        if c > 0:
            return np.eye(3)
        u = np.cross(a, [1.0, 0.0, 0.0])
        if np.linalg.norm(u) < 1e-6:
            u = np.cross(a, [0.0, 1.0, 0.0])
        u /= np.linalg.norm(u)
        return 2.0 * np.outer(u, u) - np.eye(3)
    Kx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + Kx + Kx @ Kx * ((1.0 - c) / (s * s))


def add_ken(world: dict, mesh: dict, p, R=None, *, name: str = "ken") -> int:
    """けんを姿勢 (p = 皿胴の中心, R) で世界に足す(面ラベル 27/28/30/31 はそのまま)。返り値 = objects の索引。"""
    p = np.asarray(p, np.float64).reshape(3)
    R = np.eye(3) if R is None else np.asarray(R, np.float64).reshape(3, 3)
    Vw = mesh["V"] @ R.T + p
    i = DW.world_add(world, Vw, mesh["F"], 27, mesh["color"], name=name,
                     extra={"kind": "ken", "local": mesh["V"].copy(), "center": p.copy(), "R": R.copy(),
                            "anchors": {a: np.asarray(v, np.float64).copy() for a, v in mesh.get("anchors", {}).items()},
                            "cup_radius": mesh["cup_radius"], "cup_depth": mesh["cup_depth"], "ken_length": mesh["ken_length"]})
    f0, f1 = world["objects"][i]["faces"]
    world["face_label"][f0:f1] = mesh["label"]
    return i


def ken_set_pose(world: dict, i: int, p, R) -> None:
    """けん i の姿勢を (p, R) にする(頂点だけ書き換える)。けんでない物体は ValueError。"""
    obj = world["objects"][i]
    if obj.get("kind") != "ken":
        raise ValueError("objects[%d] is not a ken (use add_ken)" % i)
    p = np.asarray(p, np.float64).reshape(3)
    R = np.asarray(R, np.float64).reshape(3, 3)
    v0, v1 = obj["verts"]
    world["V"][v0:v1] = obj["local"] @ R.T + p
    obj["center"] = p.copy()
    obj["R"] = R.copy()


def string_mesh(p_ball, p_cup, radius: float = 0.0015):
    """2 点(玉の糸穴 p_ball と皿胴の糸穴 p_cup)を結ぶ細い角柱(4 面 + 両端、8 頂点 12 面、外向き)。断面は 2·radius 角。
    両点が一致すると ValueError。"""
    a = np.asarray(p_ball, np.float64).reshape(3)
    b = np.asarray(p_cup, np.float64).reshape(3)
    if radius <= 0:
        raise ValueError("radius > 0")
    d = b - a
    L = float(np.linalg.norm(d))
    if not np.isfinite(L) or L < 1e-12:
        raise ValueError("p_ball and p_cup coincide")
    d /= L
    ref = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(d, ref)
    u /= np.linalg.norm(u)
    v = np.cross(d, u)                                   # (u, v, d) が右手系 → _box の面の向きがそのまま外向き
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]       # _box の頂点順 (x0,y0),(x1,y0),(x1,y1),(x0,y1)
    V = np.array([e + radius * (sx * u + sy * v) for e in (a, b) for sx, sy in corners])
    _, F = BW._box(0, 1, 0, 1, 0, 1)
    return V, F


def add_string(world: dict, p_ball, p_cup, *, radius: float = 0.0015, color=STRING_COLOR, name: str = "string") -> int:
    """糸(ラベル 29、暗い灰)を世界に足す。返り値 = objects の索引。"""
    V, F = string_mesh(p_ball, p_cup, radius)
    return DW.world_add(world, V, F, 29, color, name=name,
                        extra={"kind": "string", "radius": float(radius),
                               "p_ball": np.asarray(p_ball, np.float64).reshape(3).copy(),
                               "p_cup": np.asarray(p_cup, np.float64).reshape(3).copy()})


def string_set(world: dict, i: int, p_ball, p_cup) -> None:
    """糸 i の両端を (p_ball, p_cup) に置き直す(頂点だけ書き換える)。糸でない物体は ValueError。"""
    obj = world["objects"][i]
    if obj.get("kind") != "string":
        raise ValueError("objects[%d] is not a string (use add_string)" % i)
    V, _ = string_mesh(p_ball, p_cup, obj["radius"])
    v0, v1 = obj["verts"]
    world["V"][v0:v1] = V
    obj["p_ball"] = np.asarray(p_ball, np.float64).reshape(3).copy()
    obj["p_cup"] = np.asarray(p_cup, np.float64).reshape(3).copy()


def kendama_pose(world: dict, hand, p_ball, *, R_ken=None, R_ball=None) -> dict:
    """けん玉の世界の状態を置く: けん(1 つの剛体。持つ所 kp["grip"] を手元 ``hand`` に、姿勢 ``R_ken`` 既定 = kp の技の姿勢
    kp["R_ken"]: 皿胴の中心 = hand − R·grip)、玉(中心 ``p_ball``)、
    糸(皿胴の糸穴 → 玉の糸穴)。``R_ball`` 既定 = 玉の糸穴(−HOLE_AXIS_LOCAL)が皿胴の糸穴を向く回転(玉の回転は解かない:
    張っている間は正しく、飛翔中は近似)。返り値 ``{"tie", "cup" (受ける皿の縁の中心), "cup_axis", "cross" (皿胴の中心), "string_hole", "hole_axis" (大きな穴の向き、世界),
    "R_ball"}``。
    ``world`` は :func:`kendama_world` のもの(world["kendama"] が要る)。"""
    if "kendama" not in world:
        raise ValueError("world has no kendama (use kendama_world)")
    idx = world["kendama"]
    kd = world["objects"][idx["ken"]]
    hand = np.asarray(hand, np.float64).reshape(3)
    p_ball = np.asarray(p_ball, np.float64).reshape(3)
    if not (np.all(np.isfinite(hand)) and np.all(np.isfinite(p_ball))):
        raise ValueError("hand and p_ball must be finite")
    kk = world["kendama"]["kp"]
    R_ken = np.asarray(kk.get("R_ken", np.eye(3)) if R_ken is None else R_ken, np.float64).reshape(3, 3)
    an = kd["anchors"]
    O = hand - R_ken @ np.asarray(kk.get("grip", np.zeros(3)), np.float64)
    ken_set_pose(world, idx["ken"], O, R_ken)
    tie = O + R_ken @ an["tie"]
    cc = kk.get("catch_cup", "big")
    rb = world["kendama"]["kp"]["ball_radius"]
    if R_ball is None:
        d = tie - p_ball
        dn = float(np.linalg.norm(d))
        R_ball = _rot_from_to(-HOLE_AXIS_LOCAL, d / dn) if dn > 1e-9 else np.eye(3)
    R_ball = np.asarray(R_ball, np.float64).reshape(3, 3)
    BW.ball_set_pose(world, idx["ball"], p_ball, R_ball)
    sh = p_ball - rb * (R_ball @ HOLE_AXIS_LOCAL)
    if float(np.linalg.norm(tie - sh)) > 1e-9:
        string_set(world, idx["string"], sh, tie)
    return {"tie": tie, "cup": O + R_ken @ an[cc + "_rim"], "cup_axis": R_ken @ an[cc + "_axis"], "cross": O, "string_hole": sh,
            "hole_axis": R_ball @ HOLE_AXIS_LOCAL, "R_ball": R_ball}


def kendama_world(kp: dict, *, floor: bool = True, floor_size: float = 4.0, hand=(0.0, 0.0, 1.0), p_ball=None,
                  hang_deg: float = 12.0, hang_dir=(1.0, -1.0, 0.0), subdiv: int = 3, n: int = 32) -> dict:
    """床 + けん(kp の技の姿勢 R_ken、持つ所 kp["grip"] を ``hand`` に)+ 穴のある玉 + 糸の世界。原点は床、z 上。
    玉は皿胴の糸穴からひもの有効長(kp["pendulum_length"])だけ下(真下から ``hang_deg`` だけ ``hang_dir`` 側へ振れた位置 ——
    斜め (1, −1) なら方位 0° と 90° の両カメラから横ずれが見える)。``p_ball`` を渡せばそこに置く。
    床は 0.25 m の升に割る(1 枚の大きな四角形だとカメラの背後にかかる三角形ごと落ちて床が消える)。
    返り値の world["kendama"] = ``{"ken", "ball", "string"}``(objects の索引)+ ``"kp"``。"""
    k = _check_kp(kp)
    world = DW._empty_world()
    if floor:
        V, F = DW._grid_plane(-floor_size / 2, floor_size / 2, -floor_size / 2, floor_size / 2, 0.25, 0.0)
        DW.world_add(world, V, F, 25, (0.55, 0.52, 0.48), name="floor")
    hand = np.asarray(hand, np.float64).reshape(3)
    i_ken = add_ken(world, ken_mesh(kp, n=n), hand - k["R_ken"] @ k["grip"], k["R_ken"])
    tie = hand - k["R_ken"] @ k["grip"] + k["R_ken"] @ np.array([0.0, -k["cross_radius"], 0.0])
    if p_ball is None:
        a = np.radians(hang_deg)
        h = np.asarray(hang_dir, np.float64).reshape(3) * (1.0, 1.0, 0.0)
        hn = float(np.linalg.norm(h))
        if hn < 1e-12:
            raise ValueError("hang_dir must have a horizontal component")
        p_ball = tie + k["pendulum_length"] * (np.sin(a) * h / hn + np.array([0.0, 0.0, -np.cos(a)]))
    p_ball = np.asarray(p_ball, np.float64).reshape(3)
    i_ball = BW.add_ball(world, _ball_mesh_with_hole(kp, subdiv), p_ball, np.eye(3))
    i_str = add_string(world, p_ball, tie)
    world["kendama"] = {"ken": i_ken, "ball": i_ball, "string": i_str, "kp": dict(k)}
    kendama_pose(world, hand, p_ball)
    return world


def kendama_rig(kp: dict = None, *, n: int = 2, distance: float = 1.5, height: float = 1.05, fov_deg: float = 45.0,
                width: int = 480, height_px: int = 360, target=(0.0, 0.0, 1.0)) -> list:
    """振り上げの空間(x, y ∈ ±0.4 m、z ∈ 0.55〜1.45 m: 手元 1.0 m、ひも 0.42 m、持ち上げ 0.265 m)を見るカメラの組。
    n = 2: 方位 0° と 90°、n = 4: 90° ごと。全部が ``target``(既定 (0, 0, 1.0))を見る。
    返り値 ``[{"pose", "K", "eye", "width", "height"}, …]``(ballworld.camera_rig と同型)。"""
    if kp is not None:
        _check_kp(kp)
    if n == 2:
        az = (0.0, 90.0)
    elif n == 4:
        az = (0.0, 90.0, 180.0, 270.0)
    else:
        raise ValueError("n must be 2 or 4")
    if distance <= 0 or fov_deg <= 0 or fov_deg >= 180:
        raise ValueError("distance > 0, 0 < fov_deg < 180")
    tgt = np.asarray(target, np.float64).reshape(3)
    K = DW.camera_intrinsics(fov_deg, width, height_px)
    cams = []
    for a in az:
        e = np.array([tgt[0] + distance * np.cos(np.radians(a)), tgt[1] + distance * np.sin(np.radians(a)), height])
        cams.append({"pose": DW.camera_pose(e, tgt), "K": K, "eye": e, "width": int(width), "height": int(height_px)})
    return cams


def ken_truth(world: dict, i_ken: int, cam: dict) -> dict:
    """けん i_ken の真値の投影: 受ける皿の縁の中心(anchors[kp["catch_cup"] + "_rim"] を姿勢で動かした点)の (col, row)、深度、
    像での皿の半径 [px](大皿の半径で)、
    ``visible``(カメラの前にあり画素が像の内側)。ballworld.ball_truth と同型。"""
    import balltrack as BT
    obj = world["objects"][i_ken]
    if obj.get("kind") != "ken":
        raise ValueError("objects[%d] is not a ken (use add_ken)" % i_ken)
    an = obj.get("anchors") or {}
    cc = world.get("kendama", {}).get("kp", {}).get("catch_cup", "big")
    p = obj["center"] + obj["R"] @ np.asarray(an.get(cc + "_rim", np.zeros(3)), np.float64)
    uv = BT.reproject(p[None], cam["pose"], cam["K"])[0]
    T = np.asarray(cam["pose"], np.float64)
    pc = T[:3, :3] @ p + T[:3, 3]
    depth = -pc[2]
    rad_px = float(cam["K"][0, 0] * obj["cup_radius"] / depth) if depth > 0 else float("nan")
    w, h = int(cam["width"]), int(cam["height"])
    visible = bool(depth > 0 and np.isfinite(uv).all() and 0 <= uv[0] <= w - 1 and 0 <= uv[1] <= h - 1)
    return {"uv": uv, "p": p, "depth": float(depth), "radius_px": rad_px, "visible": visible}


def _region_distance(Q, profile):
    """子午面の点 Q (N, 2) = (r, z) から輪郭 (r, z) の閉じた領域までの符号つき距離(外 > 0、内 < 0)。回転体では 3-D の距離と一致する。
    軸上の辺(r = 0 の 2 点を結ぶ辺)は面ではないので距離から除く。"""
    P = np.asarray(profile, np.float64)
    A = P
    Bp = np.roll(P, -1, axis=0)
    face = ~((A[:, 0] == 0.0) & (Bp[:, 0] == 0.0))
    Q = np.asarray(Q, np.float64).reshape(-1, 2)
    AB = Bp - A
    L2 = np.maximum(np.sum(AB * AB, axis=1), 1e-30)
    tt = np.clip(((Q[:, None, :] - A[None]) * AB[None]).sum(axis=2) / L2[None], 0.0, 1.0)
    C = A[None] + tt[..., None] * AB[None]
    d = np.linalg.norm(Q[:, None, :] - C, axis=2)
    d[:, ~face] = np.inf
    dmin = d.min(axis=1)
    # 偶奇規則で内外(全辺で)
    x, y = Q[:, 0][:, None], Q[:, 1][:, None]
    y0, y1 = A[:, 1][None], Bp[:, 1][None]
    x0, x1 = A[:, 0][None], Bp[:, 0][None]
    cross = ((y0 > y) != (y1 > y)) & (x < x0 + (y - y0) * (x1 - x0) / np.where(y1 != y0, y1 - y0, 1e-30))
    inside = (cross.sum(axis=1) % 2) == 1
    return np.where(inside, -dmin, dmin)


def kendama_clearance(kp: dict, hand, p_ball, *, R_ken=None, grip=None) -> dict:
    """玉の表面からけん玉(けん・皿胴の回転体)までの隙間 [m](負 = 玉がけん玉にめり込んでいる)。kp の技の姿勢(R_ken、持つ所 grip)で
    手元 ``hand``、玉の中心 ``p_ball``(どちらも (3,) か (N, 3))。回転体までの距離は子午面の輪郭までの 2-D の距離と厳密に等しい
    ので、メッシュの離散化によらない。返り値 ``{"gap" (N,), "ken" (N,), "cross" (N,)}``(ken / cross = 各部品までの隙間)。
    物理はけん玉と玉の衝突を解かないので、この量で「玉がけん玉を突き抜けた」step を数える(門・正直な報告に使う)。
    ``R_ken``(19 巡目、連続技の持ち替え): 姿勢を kp["R_ken"] の代わりに (3, 3) か時刻ごとの (N, 3, 3) で渡す。``grip`` = 持つ所(局所)の
    上書き。どちらも None なら今まで通り。"""
    k = _check_kp(kp)
    H = np.asarray(hand, np.float64).reshape(-1, 3)
    Pb = np.asarray(p_ball, np.float64).reshape(-1, 3)
    if len(H) == 1 and len(Pb) > 1:
        H = np.repeat(H, len(Pb), axis=0)
    if H.shape != Pb.shape or not (np.all(np.isfinite(H)) and np.all(np.isfinite(Pb))):
        raise ValueError("hand and p_ball must be finite (3,) or (N, 3) of the same length")
    Rk = np.asarray(k["R_ken"] if R_ken is None else R_ken, np.float64)
    gr = np.asarray(k["grip"] if grip is None else grip, np.float64).reshape(3)
    if Rk.ndim == 3:
        if Rk.shape != (len(Pb), 3, 3):
            raise ValueError("R_ken must be (3, 3) or (N, 3, 3)")
        d = np.einsum("ni,nij->nj", Pb - H, Rk) + gr
    else:
        d = (Pb - H) @ Rk.reshape(3, 3) + gr                                 # けんの局所座標(皿胴の中心が原点)
    q_ken = np.column_stack([np.hypot(d[:, 1], d[:, 2]), d[:, 0]])          # けん: 軸 x
    q_cross = np.column_stack([np.hypot(d[:, 0], d[:, 1]), d[:, 2]])        # 皿胴: 軸 z
    rb = k["ball_radius"]
    gk = _region_distance(q_ken, _ken_profile(k)) - rb
    gc = _region_distance(q_cross, _cross_profile(k)) - rb
    return {"gap": np.minimum(gk, gc), "ken": gk, "cross": gc}


# ─────────────────────────────── 画像だけの知覚 ───────────────────────────────

def _render_window(world, cam, x0: int, y0: int, w: int, h: int):
    """カメラ cam の像の窓 [x0, x0 + w) × [y0, y0 + h) だけを描く(内部パラメータの主点をずらす = 全体を描いて切り出すのと同じ画素)。"""
    K = np.asarray(cam["K"], np.float64).copy()
    K[0, 2] -= x0
    K[1, 2] -= y0
    return DW.world_camera(world, cam["pose"], K, int(w), int(h))["color"]


def camera_perceiver(world: dict, rig: list, *, fps: float = 100.0, pixel_noise: float = 0.0, rng=None, slack_margin: float = 0.005,
                     min_frames: int = 3, window: int = 128, color_tol: float = 0.12, g: float = 9.81, keep_frames: bool = False,
                     slack_frames: int = 2, min_fill: float = 0.6, reject: float = 0.004, render_fn=None, holes: bool = True,
                     flight_from: str = "tie", flight_margin: float = 0.012):
    """画像だけから玉の (p̂, v̂) を出す知覚 ``perceive(t, p, v, scene) → (p̂, v̂) | None``(:func:`kendama.kendama_simulate` 用、
    属性 ``observe_all = True`` で毎 step 呼ばれる)。**真値 (p, v) は世界を描くためだけに使い、v は読まない。**

    コマの時刻 k / fps ごとに: (1) :func:`kendama_pose` で世界(けん = scene["hand"]、玉 = p、糸)を置き、各カメラで描く
    (玉の周り ``window`` 画素の窓だけを描く: 窓は前のコマの検出(放物線が当たっていればその予測)から決め、検出が無い・窓の縁に
    かかったら全画面を描き直す —— 窓の画素は全画面の切り出しと同じ)、(2) :func:`balltrack.ball_detect`(chroma、橙)で玉を検出し
    画素に σ = ``pixel_noise`` のガウス雑音を足す、(3) 2 台以上で見えれば :func:`balltrack.triangulate_dlt` で 3-D に戻す、
    (4) 「弛んだ」= 三角測量した玉と皿胴の糸穴(scene["tie"]: 手の自己受容で分かる)の距離がひもの有効長より ``slack_margin``
    以上短いコマが ``slack_frames`` 回続いたら(1 回だと画素雑音 2 px で張っている間に誤検出した —— 測って退けた)、
    その最初のコマ以降の点に重力 g 既知の放物線(:func:`kendama.parabola_fit_g` と同じ式、未知 6)を最小二乗で当てる
    (``min_frames`` 点以上)。返り値 = 当てた放物線を t へ外挿した (p̂, v̂)。放物線がまだ無ければ None(計画は動かない)。

    世界の玉の姿勢(描画の約束、真値): scene["taut"] の間は糸穴が皿胴の糸穴を向き、弛んだら最後の姿勢のまま(``R_ball`` に記録)。
    記録(属性): ``frames`` = [{"t", "p_hat" (3,) or NaN, "uv" [(col,row)…], "full" [bool…], "tie", "hole_uv", "hole_dir"}]、
    ``R_ball`` = 各コマの玉の真の姿勢(穴の真の向き = R_ball @ HOLE_AXIS_LOCAL: 門の真値)、``slack_frame``(弛みを
    検出したコマの索引 or None)、``fits`` = [(t_frame, n_used, p_ref, v_ref, t_ref)]、``render_s``(描画 + 検出の合計秒)、
    ``n_render``(描いた窓の数)、``images``(``keep_frames=True`` のとき各カメラの全画面 …… 重いので図のときだけ)。
    ``render_fn(world, cam) → (H, W, 3) float``: 描画を差し替える口(既定 = :func:`driveworld.world_camera` のメッシュ描画。
    3DGS など)。窓だけを描くときは cam の K(主点をずらした)・width・height を窓に合わせた辞書を渡す。
    ``holes=True``: 玉の窓の中で :func:`kendama.hole_detect` で穴を探し(雑音を足す前の画素で)、2 台で見えたコマは穴の重心を
    三角測量して玉の中心からの向き ``hole_dir``(世界の単位ベクトル)を記録する(皿の技では報告だけ、計画には使わない)。
    ``flight_from="cup"``(19 巡目、連続技): 「飛び始め」を糸の弛みでなく、三角測量した玉と皿に乗った玉の位置(scene["rest"] = 受けている皿の
    縁の中心 + h_c·軸: 手元の自己受容で分かる)の距離が ``flight_margin`` を超えたコマが ``slack_frames`` 回続いたこと で決める(皿に乗っている
    間のコマは当てはめに入れない)。scene["R_ken"] があればけんをその姿勢で描く(持ち替え)。``perceive.reset()`` で今の放物線を捨て、次の
    飛び始めを待つ(記録 ``flights`` = 飛び始めのコマの索引の列)。既定 "tie" は今まで通り。
    fail-closed: fps ≤ 0、pixel_noise < 0、min_frames < 2、window < 32、カメラ 2 台未満、kendama の無い世界は ValueError。"""
    import balltrack as BT
    if "kendama" not in world:
        raise ValueError("world has no kendama (use kendama_world)")
    if not (np.isfinite(fps) and fps > 0) or not (np.isfinite(pixel_noise) and pixel_noise >= 0):
        raise ValueError("need fps > 0 and pixel_noise ≥ 0")
    if int(min_frames) < 2 or int(window) < 32 or len(rig) < 2 or slack_margin <= 0 or g <= 0 or int(slack_frames) < 1 \
            or not (0.0 <= min_fill <= 1.0) or reject <= 0:
        raise ValueError("need min_frames ≥ 2, window ≥ 32, ≥ 2 cameras, slack_margin > 0, g > 0, slack_frames ≥ 1, "
                         "0 ≤ min_fill ≤ 1, reject > 0")
    if flight_from not in ("tie", "cup") or not (flight_margin > 0):
        raise ValueError("flight_from must be 'tie' or 'cup', flight_margin > 0")
    if pixel_noise > 0 and rng is None:
        rng = np.random.default_rng(0)
    L = float(world["kendama"]["kp"]["pendulum_length"])
    poses = np.array([c["pose"] for c in rig])
    Ks = np.array([c["K"] for c in rig])
    dt_f = 1.0 / float(fps)
    win = int(window)
    zhat = np.array([0.0, 0.0, 1.0])
    st = {"next": 0, "fit": None, "last_uv": [None] * len(rig), "prev_uv": [None] * len(rig), "run": 0, "R_ball": None}

    def _render(cam, K=None, w=None, h=None):
        cam2 = dict(cam)
        if K is not None:
            cam2["K"], cam2["width"], cam2["height"] = K, int(w), int(h)
        if render_fn is not None:
            return np.asarray(render_fn(world, cam2), np.float64)
        return DW.world_camera(world, cam2["pose"], cam2["K"], int(cam2["width"]), int(cam2["height"]))["color"]

    def _hole(img, d, x0, y0):
        if not holes or d is None:
            return np.full(2, np.nan)
        from kendama import hole_detect
        hd = hole_detect(img, (d["col"], d["row"]), d["radius"])
        return np.array([hd["col"] + x0, hd["row"] + y0]) if hd["found"] else np.full(2, np.nan)

    def _detect(img):
        c = BT.ball_detect(img, mode="chroma", color=BALL_COLOR, color_tol=color_tol, radius_range=(2.5, 80))
        c = [d for d in c if d["fill"] >= min_fill]
        return c[0] if c else None

    def _observe(cam_i, cam, pred_uv):
        W, H = int(cam["width"]), int(cam["height"])
        if pred_uv is not None and np.all(np.isfinite(pred_uv)):
            x0 = int(round(min(max(pred_uv[0] - win / 2, 0), W - win)))
            y0 = int(round(min(max(pred_uv[1] - win / 2, 0), H - win)))
            Kw = np.asarray(cam["K"], np.float64).copy()
            Kw[0, 2] -= x0
            Kw[1, 2] -= y0
            img = _render(cam, Kw, min(win, W), min(win, H))
            perceive.n_render += 1
            d = _detect(img)
            if d is not None:
                c, r, rad = d["col"], d["row"], d["radius"]
                inner = (c - rad > 1 or x0 == 0) and (c + rad < img.shape[1] - 2 or x0 + img.shape[1] == W) \
                    and (r - rad > 1 or y0 == 0) and (r + rad < img.shape[0] - 2 or y0 + img.shape[0] == H)
                if inner:
                    return np.array([c + x0, r + y0]), False, None, _hole(img, d, x0, y0)
        img = _render(cam)
        perceive.n_render += 1
        d = _detect(img)
        uv = np.array([d["col"], d["row"]]) if d is not None else np.full(2, np.nan)
        return uv, True, img, _hole(img, d, 0, 0)

    def _fit(tt, PP):
        """重力既知の放物線(t_ref = 最後の点)。残差が max(``reject``, 3.5 × 頑健な σ) を超える点があれば最悪の 1 点を落として当て直す(けんに一部
        隠れた玉の重心のずれ: 測って 20 mm の外れ値が出た)。点が min_frames を割るまでは落とさない。"""
        keep = np.ones(len(tt), bool)
        while True:
            tau = tt[keep] - tt[-1]
            A = np.column_stack([np.ones_like(tau), tau])
            Y = PP[keep] + np.outer(0.5 * g * tau * tau, zhat)
            coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
            res = np.linalg.norm(A @ coef - Y, axis=1)
            j = int(np.argmax(res))
            if res[j] <= max(reject, 3.5 * 1.4826 * float(np.median(res))) or keep.sum() <= int(min_frames):
                return coef, int(keep.sum())
            keep[np.flatnonzero(keep)[j]] = False

    def _frame(t, p, scene):
        t0 = time.perf_counter()
        # 玉の姿勢(描画の約束): 張っている間は糸穴が結び目を向く、弛んだら最後の姿勢のまま飛ぶ(弛んだ玉にトルクは無い)
        Rk = scene.get("R_ken")
        if (scene.get("taut", True) and flight_from == "tie") or st["R_ball"] is None:
            st["R_ball"] = kendama_pose(world, scene["hand"], p, R_ken=Rk)["R_ball"]
        else:
            kendama_pose(world, scene["hand"], p, R_ball=st["R_ball"], R_ken=Rk)
        perceive.R_ball.append(st["R_ball"].copy())
        uvs, full, imgs, huv = [], [], [], []
        for ci, cam in enumerate(rig):
            pred = None
            if st["fit"] is not None:
                f = st["fit"]
                tau = t - f["t_ref"]
                pp = f["p"] + f["v"] * tau - 0.5 * g * tau * tau * zhat
                pred = BT.reproject(pp[None], cam["pose"], cam["K"])[0]
            elif st["last_uv"][ci] is not None:
                pred = st["last_uv"][ci] + (st["last_uv"][ci] - st["prev_uv"][ci] if st["prev_uv"][ci] is not None else 0.0)
            uv, was_full, img, hole_uv = _observe(ci, cam, pred)
            huv.append(hole_uv)
            if keep_frames:
                if img is None:
                    img = _render(cam)
                imgs.append(img)
            if np.all(np.isfinite(uv)):
                st["prev_uv"][ci], st["last_uv"][ci] = st["last_uv"][ci], uv.copy()
                if pixel_noise > 0:
                    uv = uv + rng.normal(0.0, pixel_noise, 2)
            else:
                st["prev_uv"][ci] = st["last_uv"][ci] = None
            uvs.append(uv)
            full.append(was_full)
        U = np.array(uvs)
        ok = np.isfinite(U).all(axis=1)
        p_hat = BT.triangulate_dlt(U[ok], poses[ok], Ks[ok])["p"] if ok.sum() >= 2 else np.full(3, np.nan)
        HU = np.array(huv)
        okh = np.isfinite(HU).all(axis=1)
        hole_dir = np.full(3, np.nan)
        if okh.sum() >= 2 and np.all(np.isfinite(p_hat)):
            HN = HU[okh] + (rng.normal(0.0, pixel_noise, HU[okh].shape) if pixel_noise > 0 else 0.0)
            hp = BT.triangulate_dlt(HN, poses[okh], Ks[okh])["p"]
            dv = hp - p_hat
            if np.linalg.norm(dv) > 1e-9:
                hole_dir = dv / np.linalg.norm(dv)
        perceive.frames.append({"t": t, "p_hat": p_hat, "uv": [u.copy() for u in uvs], "full": full,
                                "tie": np.asarray(scene["tie"], np.float64).copy(), "hole_uv": [h.copy() for h in huv],
                                "hole_dir": hole_dir})
        if keep_frames:
            perceive.images.append(imgs)
        k = len(perceive.frames) - 1
        if flight_from == "cup":
            rest = scene.get("rest")
            short = bool(rest is not None and np.all(np.isfinite(p_hat))
                         and float(np.linalg.norm(p_hat - np.asarray(rest, np.float64))) > flight_margin)
        else:
            short = bool(np.all(np.isfinite(p_hat)) and float(np.linalg.norm(p_hat - perceive.frames[k]["tie"])) < L - slack_margin)
        st["run"] = st["run"] + 1 if short else 0
        if perceive.slack_frame is None and st["run"] >= int(slack_frames):
            perceive.slack_frame = k - int(slack_frames) + 1
            perceive.flights.append(perceive.slack_frame)
        if perceive.slack_frame is not None:
            tt = np.array([f["t"] for f in perceive.frames[perceive.slack_frame:]])
            PP = np.array([f["p_hat"] for f in perceive.frames[perceive.slack_frame:]])
            good = np.isfinite(PP).all(axis=1)
            if good.sum() >= int(min_frames):
                coef, used = _fit(tt[good], PP[good])
                st["fit"] = {"p": coef[0].copy(), "v": coef[1].copy(), "t_ref": float(tt[good][-1]), "n": used}
                perceive.fits.append((t, used, coef[0].copy(), coef[1].copy(), float(tt[good][-1])))
        perceive.render_s += time.perf_counter() - t0

    def perceive(t, p, v=None, scene=None):
        if scene is None or "hand" not in scene or "tie" not in scene:
            raise ValueError("camera_perceiver needs scene={'hand', 'tie', …} (kendama_simulate passes it)")
        t = float(t)
        while st["next"] * dt_f <= t + 1e-9:
            tf = st["next"] * dt_f
            st["next"] += 1
            if tf < t - dt_f:                      # 呼ばれなかった過去のコマは描けない(世界がその時刻に無い)→ 飛ばす
                continue
            _frame(t, np.asarray(p, np.float64).reshape(3), scene)
        f = st["fit"]
        if f is None:
            return None
        tau = t - f["t_ref"]
        return f["p"] + f["v"] * tau - 0.5 * g * tau * tau * zhat, f["v"] - g * tau * zhat

    def reset():
        st["fit"], st["run"] = None, 0
        perceive.slack_frame = None

    perceive.reset = reset
    perceive.flights = []
    perceive.observe_all = True
    perceive.R_ball = []
    perceive.frames = []
    perceive.fits = []
    perceive.images = []
    perceive.slack_frame = None
    perceive.render_s = 0.0
    perceive.n_render = 0
    perceive.fps = float(fps)
    return perceive
