# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""carlabridge — 外部の高写実シミュレータ(CARLA 0.9.16、コード MIT・アセット CC-BY)の撮影記録を Fullseye の世界の規約に写す橋。

自前の世界(:mod:`driveworld`)は真値を全部持つが写実ではない。CARLA は写実だが中の式は見えない。集大成の PoC は
**同じ場面を両方で撮り、同じルールベースの知覚を同じ門で採点する**。そのために要るのは「写す規約」であって、
CARLA そのものではない —— このモジュールは **numpy だけ**で動き、CARLA の Python パッケージもサーバも要らない。
撮影(サーバが要る)は repo の外のスクリプトが行い、その出力(npz の場面記録)だけをここで読む。

写す規約(どれも閉形式で、往復の門がある):
  * **座標系**: CARLA / UE4 は左手系(x 前・y 右・z 上、角は度、yaw は上から見て時計回りが +)。Fullseye は右手系
    (x 前・y 左・z 上、yaw は +x から反時計回り、ラジアン)。鏡映 M = diag(1, −1, 1) で **R_f = M R_c M、t_f = M t_c**
    (物体の局所系も鏡映する —— 車の「左」は両方で +y_f)。yaw は符号が反転し、roll・pitch の幾何(前上がり・右下がり)は保たれる。
  * **回転行列**: CARLA の ``Transform.get_matrix()`` と同じ式(:func:`carla_rotation_matrix`)。門 = CARLA の客体が返した
    行列を 3 つ焼き込んで照合(同じ式の第 2 実装)。
  * **カメラ**: CARLA のカメラは局所 +x を見て、像の右 = +y、上 = +z。render3d のカメラは局所 −z を見て、右 = +x、上 = +y。
    :func:`carla_camera_pose` は world → camera の 4×4(:func:`driveworld.camera_pose` と同じ型)を返す。門 = yaw 0 / 90 の
    カメラが ``look_at`` と一致。
  * **内部パラメータ**: CARLA は水平画角で f = W / (2 tan(fov/2))、主点 (W/2, H/2)(画素の角が整数)。Fullseye は画素の中心が
    整数なので主点は ((W−1)/2, (H−1)/2) —— :func:`intrinsics_to_fullseye` は主点を 0.5 画素ずらすだけ(f は同じ)。
  * **深度**: CARLA の深度カメラの生の像は 24 bit を R(下位)G B(上位)に分けた **像面からの距離**(光線長でない)で、
    d = (R + 256 G + 65536 B) / (2²⁴ − 1) · 1000 m。render3d の depth も像面からの距離なので、そのまま比べられる。
    往復 encode → decode の誤差 ≤ 1000 / (2²⁴ − 1) ≈ 6 × 10⁻⁵ m。
  * **意味ラベル**: CARLA 0.9.16 の 29 タグ(``carla.CityObjectLabel``、客体から読んで焼き込み)を :data:`driveworld.LABELS`
    に写す(:data:`TAG_TO_LABEL`)。空と未ラベルは −1。逆写像(:func:`carla_label_unmap`)は代表タグ 1 つに戻す。

場面記録(``table`` = dict、:func:`carla_scene_check` が鍵・形・型を検査して通さない物は ValueError):
  ``rgb`` (H,W,3) uint8 / ``depth_raw`` (H,W,3) uint8 / ``semantic`` (H,W) uint8 / ``instance`` (H,W,3) uint8(任意)/
  ``K`` (3,3) / ``cam_transform`` ``ego_transform`` ``lead_transform`` (6,) = [x, y, z, roll, pitch, yaw](CARLA の m・度、
  先行車なしは NaN)/ ``ego_extent`` ``lead_extent`` (3,) = 箱の半長 / ``meta`` = JSON 文字列(map・fov_deg・lead_distance_m …)。
  :func:`carla_scene_synthetic` は **自前の世界を CARLA の規約で記録**にする(撮影記録と同じ形)—— 橋の全部の往復の門と、
  CARLA が無い環境での見本に使う。

採点(両方の世界に同じ式):
  * :func:`lead_from_depth` —— 車のラベルの画素の深度の中央値(先行車の後ろ面は像面に平行なので深度は一定 = 後ろ面までの距離)と、
    車の最下行から平らな路面の式(:func:`driveenv.road_row_distance`)で出した水平距離。
  * :func:`lead_truth_depth` —— 記録の姿勢から閉形式: 後ろ面の中心 = 先行車の中心 − 半長 × 前方向、像面距離 = (後ろ面 − カメラ)·前方向。

限界(self_reported): CARLA の深度・意味分割の真値そのものは検証していない(CARLA の中は見えない)。確かめたのは
**写す規約が可逆である**ことと、**閉形式の真値(姿勢から出した距離)と CARLA の深度が合う**こと。ローリングシャッター・
LiDAR の反射率・レーダーの RCS は CARLA 0.9.16 に無い(調査 C)。インスタンス分割は運ぶだけで採点には使っていない。

参考: CARLA 0.9.16 PythonAPI(carla.Transform.get_matrix / sensor.camera.depth の復号式 / CityObjectLabel)。
Dosovitskiy ら (2017) CARLA: An Open Urban Driving Simulator, CoRL. Hautière ら (2006)(路面の行 → 距離)。
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np

__all__ = [
    "CARLA_TAGS", "TAG_TO_LABEL", "LABEL_TO_TAG", "DEPTH_SCALE_M", "DEPTH_CODE_MAX",
    "carla_labels", "carla_label_map", "carla_label_unmap",
    "carla_depth_decode", "carla_depth_encode",
    "carla_intrinsics", "intrinsics_to_fullseye", "intrinsics_to_carla",
    "carla_rotation_matrix", "carla_rotation_angles", "carla_transform_matrix",
    "carla_pose_to_world", "world_pose_to_carla", "carla_camera_pose", "camera_pose_to_carla", "carla_xy_yaw",
    "carla_scene_check", "carla_scene_load", "carla_scene_save", "carla_scene_synthetic",
    "carla_scene_world", "carla_scene_render", "lead_truth_depth", "lead_from_depth", "scene_pair_table",
]

#: CARLA 0.9.16 の ``carla.CityObjectLabel``(客体の ``names`` から 2026-10-04 に読んだ全数、255 = Any は除く)。
CARLA_TAGS = {
    0: "NONE", 1: "Roads", 2: "Sidewalks", 3: "Buildings", 4: "Walls", 5: "Fences", 6: "Poles", 7: "TrafficLight",
    8: "TrafficSigns", 9: "Vegetation", 10: "Terrain", 11: "Sky", 12: "Pedestrians", 13: "Rider", 14: "Car",
    15: "Truck", 16: "Bus", 17: "Train", 18: "Motorcycle", 19: "Bicycle", 20: "Static", 21: "Dynamic", 22: "Other",
    23: "Water", 24: "RoadLines", 25: "Ground", 26: "Bridge", 27: "RailTrack", 28: "GuardRail",
}
#: CARLA のタグ → :data:`driveworld.LABELS`(0 路面 / 1 縁石 / 2 車 / 3 信号機 / 4 標識 / 5 コーン / 6 障害物 / 7 歩行者 /
#: 8 レール / 9 白線 / 10 地形 / 11 水 / 12 横断歩道 / 13 木)。空と未ラベルは −1。歩道は縁石(車が乗らない縁)、
#: 二輪は車(走る物)、乗り手は歩行者(人)、建物・壁・柵・柱・ガードレール・橋・静物・動く物・その他は障害物にまとめる。
TAG_TO_LABEL = {
    0: -1, 1: 0, 2: 1, 3: 6, 4: 6, 5: 6, 6: 6, 7: 3, 8: 4, 9: 13, 10: 10, 11: -1, 12: 7, 13: 7, 14: 2, 15: 2, 16: 2,
    17: 8, 18: 2, 19: 2, 20: 6, 21: 6, 22: 6, 23: 11, 24: 9, 25: 10, 26: 6, 27: 8, 28: 6,
}
#: 逆写像の代表タグ(ラベル → タグ 1 つ)。往復 label → tag → label が恒等になる(門)。
LABEL_TO_TAG = {-1: 11, 0: 1, 1: 2, 2: 14, 3: 7, 4: 8, 5: 20, 6: 20, 7: 12, 8: 27, 9: 24, 10: 10, 11: 23, 12: 1, 13: 9}
DEPTH_SCALE_M = 1000.0
DEPTH_CODE_MAX = 256 ** 3 - 1
_SCENE_KEYS = ("rgb", "depth_raw", "semantic", "K", "cam_transform", "ego_transform", "lead_transform",
               "ego_extent", "lead_extent", "meta")
_MIRROR = np.diag([1.0, -1.0, 1.0])


# ----------------------------------------------------------------------------------------------------------------------
# 検査(fail-closed)
def _finite_vec(v, n, name, op):
    a = np.asarray(v, np.float64).reshape(-1)
    if a.size != n:
        raise ValueError("%s: %s must have %d values (got %d)" % (op, name, n, a.size))
    return a


def _transform6(t, name, op, allow_nan=False):
    a = _finite_vec(t, 6, name, op)
    if not allow_nan and not np.all(np.isfinite(a)):
        raise ValueError("%s: %s must be finite" % (op, name))
    return a


def _image_u8(a, name, op, channels):
    a = np.asarray(a)
    if a.dtype != np.uint8:
        raise ValueError("%s: %s must be uint8 (got %s)" % (op, name, a.dtype))
    if channels == 0:
        if a.ndim != 2:
            raise ValueError("%s: %s must be 2-D (got %s)" % (op, name, a.shape))
    elif a.ndim != 3 or a.shape[2] != channels:
        raise ValueError("%s: %s must be (H, W, %d) (got %s)" % (op, name, channels, a.shape))
    return a


# ----------------------------------------------------------------------------------------------------------------------
# ラベル
def carla_labels() -> list:
    """CARLA 0.9.16 の意味タグの表: ``[{"tag", "carla", "label", "fullseye"}, …]``(29 行、タグ順)。"""
    import driveworld
    return [{"tag": t, "carla": n, "label": TAG_TO_LABEL[t], "fullseye": driveworld.LABELS.get(TAG_TO_LABEL[t], "sky")}
            for t, n in sorted(CARLA_TAGS.items())]


def carla_label_map(semantic) -> np.ndarray:
    """CARLA の意味分割(タグの uint8 像)→ Fullseye のラベル像(int、−1 = 空・未ラベル)。未知のタグは ValueError。"""
    op = "carla_label_map"
    s = _image_u8(semantic, "semantic", op, 0)
    lut = np.full(256, -2, np.int64)
    for t, l in TAG_TO_LABEL.items():
        lut[t] = l
    out = lut[s]
    bad = np.unique(s[out == -2])
    if bad.size:
        raise ValueError("%s: unknown CARLA tags %s" % (op, bad.tolist()))
    return out


def carla_label_unmap(label) -> np.ndarray:
    """Fullseye のラベル像 → CARLA のタグ像(uint8、代表タグ)。:func:`carla_label_map` の逆(ラベル側で恒等)。"""
    op = "carla_label_unmap"
    l = np.asarray(label)
    if l.ndim != 2 or l.dtype.kind not in "iu":
        raise ValueError("%s: label must be a 2-D integer image" % op)
    lut = {k: v for k, v in LABEL_TO_TAG.items()}
    out = np.empty(l.shape, np.uint8)
    flat = l.reshape(-1)
    o = out.reshape(-1)
    for k in np.unique(flat):
        if int(k) not in lut:
            raise ValueError("%s: label %d has no CARLA tag" % (op, int(k)))
        o[flat == k] = lut[int(k)]
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 深度
def carla_depth_decode(depth_raw) -> np.ndarray:
    """CARLA の深度カメラの生の像(R 下位・G・B 上位の 24 bit)→ 像面からの距離 [m]。d = code / (2²⁴ − 1) · 1000。"""
    a = _image_u8(depth_raw, "depth_raw", "carla_depth_decode", 3).astype(np.float64)
    code = a[..., 0] + 256.0 * a[..., 1] + 65536.0 * a[..., 2]
    return code / DEPTH_CODE_MAX * DEPTH_SCALE_M


def carla_depth_encode(depth_m) -> np.ndarray:
    """像面からの距離 [m] → CARLA の生の深度像(uint8 (H,W,3))。inf と 1000 m 超は最大値、負と NaN は ValueError。"""
    op = "carla_depth_encode"
    d = np.asarray(depth_m, np.float64)
    if d.ndim != 2:
        raise ValueError("%s: depth must be 2-D" % op)
    if np.any(np.isnan(d)) or np.any(d < 0):
        raise ValueError("%s: depth must be >= 0 and not NaN" % op)
    code = np.rint(np.clip(d / DEPTH_SCALE_M, 0.0, 1.0) * DEPTH_CODE_MAX).astype(np.int64)
    out = np.empty(d.shape + (3,), np.uint8)
    out[..., 0] = code & 255
    out[..., 1] = (code >> 8) & 255
    out[..., 2] = (code >> 16) & 255
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 内部パラメータ
def carla_intrinsics(fov_deg: float, width: int, height: int) -> np.ndarray:
    """CARLA のカメラの K(**水平**画角 fov、f = W / (2 tan(fov/2))、主点 (W/2, H/2))。"""
    op = "carla_intrinsics"
    fov = float(fov_deg)
    W, H = int(width), int(height)
    if not (0.0 < fov < 180.0) or W <= 0 or H <= 0:
        raise ValueError("%s: need 0 < fov < 180 and positive size" % op)
    f = W / (2.0 * math.tan(math.radians(fov) / 2.0))
    return np.array([[f, 0.0, W / 2.0], [0.0, f, H / 2.0], [0.0, 0.0, 1.0]])


def _K(K, op):
    k = np.asarray(K, np.float64)
    if k.shape != (3, 3) or not np.all(np.isfinite(k)) or k[0, 0] <= 0 or k[1, 1] <= 0:
        raise ValueError("%s: K must be a finite 3x3 with positive focal lengths" % op)
    return k


def intrinsics_to_fullseye(K) -> np.ndarray:
    """CARLA の K(画素の角が整数、主点 W/2)→ Fullseye / render3d の K(画素の中心が整数、主点 (W−1)/2)。主点を 0.5 ずらすだけ。"""
    k = _K(K, "intrinsics_to_fullseye").copy()
    k[0, 2] -= 0.5
    k[1, 2] -= 0.5
    return k


def intrinsics_to_carla(K) -> np.ndarray:
    """:func:`intrinsics_to_fullseye` の逆(主点を 0.5 戻す)。"""
    k = _K(K, "intrinsics_to_carla").copy()
    k[0, 2] += 0.5
    k[1, 2] += 0.5
    return k


# ----------------------------------------------------------------------------------------------------------------------
# 姿勢
def carla_rotation_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """CARLA / UE4 の (roll, pitch, yaw)[度] → 3×3(``carla.Transform.get_matrix()`` の回転部と同じ式、左手系のまま)。"""
    for v, n in ((roll, "roll"), (pitch, "pitch"), (yaw, "yaw")):
        if not np.isfinite(float(v)):
            raise ValueError("carla_rotation_matrix: %s must be finite" % n)
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return np.array([
        [cp * cy, cy * sp * sr - sy * cr, -cy * sp * cr - sy * sr],
        [cp * sy, sy * sp * sr + cy * cr, -sy * sp * cr + cy * sr],
        [sp, -cp * sr, cp * cr],
    ])


def carla_rotation_angles(R) -> tuple:
    """3×3(CARLA の式)→ (roll, pitch, yaw)[度]。pitch = asin(R₂₀)、yaw = atan2(R₁₀, R₀₀)、roll = atan2(−R₂₁, R₂₂)。
    |pitch| = 90° の縮退は ValueError。"""
    r = np.asarray(R, np.float64)
    if r.shape != (3, 3) or not np.all(np.isfinite(r)):
        raise ValueError("carla_rotation_angles: R must be a finite 3x3")
    s = float(np.clip(r[2, 0], -1.0, 1.0))
    if abs(abs(s) - 1.0) < 1e-9:
        raise ValueError("carla_rotation_angles: pitch of +-90 deg (gimbal lock)")
    pitch = math.degrees(math.asin(s))
    yaw = math.degrees(math.atan2(r[1, 0], r[0, 0]))
    roll = math.degrees(math.atan2(-r[2, 1], r[2, 2]))
    return (roll, pitch, yaw)


def carla_transform_matrix(transform6) -> np.ndarray:
    """CARLA の [x, y, z, roll, pitch, yaw] → 4×4(world ← object、CARLA の座標のまま)= ``Transform.get_matrix()``。"""
    t = _transform6(transform6, "transform", "carla_transform_matrix")
    M = np.eye(4)
    M[:3, :3] = carla_rotation_matrix(t[3], t[4], t[5])
    M[:3, 3] = t[:3]
    return M


def carla_pose_to_world(transform6) -> np.ndarray:
    """CARLA の [x, y, z, roll, pitch, yaw] → Fullseye の 4×4(world ← object、右手系: y と yaw の符号が反転)。
    R_f = M R_c M、t_f = M t_c(M = diag(1, −1, 1))。物体の局所系は x 前・y 左・z 上(driveworld の車と同じ)。"""
    Mc = carla_transform_matrix(transform6)
    Mf = np.eye(4)
    Mf[:3, :3] = _MIRROR @ Mc[:3, :3] @ _MIRROR
    Mf[:3, 3] = _MIRROR @ Mc[:3, 3]
    return Mf


def world_pose_to_carla(T) -> np.ndarray:
    """Fullseye の 4×4(world ← object)→ CARLA の [x, y, z, roll, pitch, yaw]。:func:`carla_pose_to_world` の逆。"""
    M = np.asarray(T, np.float64)
    if M.shape != (4, 4) or not np.all(np.isfinite(M)):
        raise ValueError("world_pose_to_carla: T must be a finite 4x4")
    Rc = _MIRROR @ M[:3, :3] @ _MIRROR
    tc = _MIRROR @ M[:3, 3]
    r, p, y = carla_rotation_angles(Rc)
    return np.array([tc[0], tc[1], tc[2], r, p, y])


def carla_xy_yaw(transform6) -> tuple:
    """CARLA の姿勢 → carpath / driveworld の (x, y, yaw)(y と yaw の符号を反転、yaw はラジアン)。"""
    t = _transform6(transform6, "transform", "carla_xy_yaw")
    return (float(t[0]), float(-t[1]), float(-math.radians(t[5])))


def carla_camera_pose(cam_transform6) -> np.ndarray:
    """CARLA のカメラの世界姿勢 → render3d / driveworld の **world → camera** 4×4(:func:`driveworld.camera_pose` と同じ型)。
    CARLA のカメラは局所 +x を見て右 = +y・上 = +z、render3d は −z を見て右 = +x・上 = +y。"""
    Mf = carla_pose_to_world(cam_transform6)
    fwd, left, up = Mf[:3, 0], Mf[:3, 1], Mf[:3, 2]
    R = np.stack([-left, up, -fwd], axis=0)          # rows: right, up, -forward
    pose = np.eye(4)
    pose[:3, :3] = R
    pose[:3, 3] = -R @ Mf[:3, 3]
    return pose


def camera_pose_to_carla(pose) -> np.ndarray:
    """render3d の world → camera 4×4 → CARLA のカメラの [x, y, z, roll, pitch, yaw]。:func:`carla_camera_pose` の逆。"""
    P = np.asarray(pose, np.float64)
    if P.shape != (4, 4) or not np.all(np.isfinite(P)):
        raise ValueError("camera_pose_to_carla: pose must be a finite 4x4")
    R = P[:3, :3]
    eye = -R.T @ P[:3, 3]
    right, up, back = R[0], R[1], R[2]
    Mf = np.eye(4)
    Mf[:3, 0] = -back
    Mf[:3, 1] = -right
    Mf[:3, 2] = up
    Mf[:3, 3] = eye
    return world_pose_to_carla(Mf)


# ----------------------------------------------------------------------------------------------------------------------
# 場面記録
def carla_scene_check(scene) -> dict:
    """場面記録の鍵・形・型を検査して要約を返す(通らなければ ValueError)。
    返り値 = ``{"width", "height", "has_lead", "has_instance", "meta"(dict), "n_tags"}``。"""
    op = "carla_scene_check"
    if not isinstance(scene, dict):
        raise ValueError("%s: scene must be a dict" % op)
    missing = [k for k in _SCENE_KEYS if k not in scene]
    if missing:
        raise ValueError("%s: missing keys %s" % (op, missing))
    rgb = _image_u8(scene["rgb"], "rgb", op, 3)
    H, W = rgb.shape[:2]
    dr = _image_u8(scene["depth_raw"], "depth_raw", op, 3)
    sem = _image_u8(scene["semantic"], "semantic", op, 0)
    if dr.shape[:2] != (H, W) or sem.shape != (H, W):
        raise ValueError("%s: rgb / depth_raw / semantic sizes differ" % op)
    if "instance" in scene and scene["instance"] is not None:
        if _image_u8(scene["instance"], "instance", op, 3).shape[:2] != (H, W):
            raise ValueError("%s: instance size differs" % op)
    _K(scene["K"], op)
    _transform6(scene["cam_transform"], "cam_transform", op)
    _transform6(scene["ego_transform"], "ego_transform", op)
    lead = _transform6(scene["lead_transform"], "lead_transform", op, allow_nan=True)
    has_lead = bool(np.all(np.isfinite(lead)))
    if not has_lead and np.any(np.isfinite(lead)):
        raise ValueError("%s: lead_transform must be all finite or all NaN" % op)
    _finite_vec(scene["ego_extent"], 3, "ego_extent", op)
    le = _finite_vec(scene["lead_extent"], 3, "lead_extent", op)
    if has_lead and (not np.all(np.isfinite(le)) or np.any(le <= 0)):
        raise ValueError("%s: lead_extent must be positive when a lead is present" % op)
    meta = scene["meta"]
    if isinstance(meta, np.ndarray):
        meta = meta.item()
    if isinstance(meta, (bytes, bytearray)):
        meta = meta.decode("utf-8")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except json.JSONDecodeError as e:
            raise ValueError("%s: meta is not JSON (%s)" % (op, e))
    if not isinstance(meta, dict):
        raise ValueError("%s: meta must be a JSON object" % op)
    carla_label_map(sem)                                   # 未知タグはここで落ちる
    return {"width": int(W), "height": int(H), "has_lead": has_lead,
            "has_instance": bool("instance" in scene and scene["instance"] is not None),
            "meta": meta, "n_tags": int(np.unique(sem).size)}


def carla_scene_load(path) -> dict:
    """場面記録(npz)を読む → dict(``meta`` は dict に、``depth`` [m] を復号して足す)。無い・壊れている物は ValueError。"""
    op = "carla_scene_load"
    p = Path(str(path))
    if not p.is_file():
        raise ValueError("%s: no such file: %s" % (op, p))
    try:
        with np.load(str(p), allow_pickle=False) as z:
            scene = {k: z[k] for k in z.files}
    except (OSError, ValueError) as e:
        raise ValueError("%s: cannot read %s (%s)" % (op, p, e))
    info = carla_scene_check(scene)
    scene["meta"] = info["meta"]
    scene["depth"] = carla_depth_decode(scene["depth_raw"])
    scene["path"] = str(p)
    return scene


def carla_scene_save(scene, path) -> str:
    """場面記録を npz に書く(検査してから)。返り値 = 書いたパス。"""
    carla_scene_check(scene)
    out = {k: np.asarray(scene[k]) for k in _SCENE_KEYS if k != "meta"}
    if "instance" in scene and scene["instance"] is not None:
        out["instance"] = np.asarray(scene["instance"])
    meta = scene["meta"]
    out["meta"] = np.asarray(json.dumps(meta if isinstance(meta, dict) else json.loads(str(meta)), ensure_ascii=False))
    p = Path(str(path))
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(str(p), **out)
    return str(p)


# ----------------------------------------------------------------------------------------------------------------------
# 自前の世界 ↔ 場面
_ROAD_LEN = 160.0
_ROAD_W = 7.0
_EGO_X = 20.0


def _scene_world(lead_pose_f, lead_asset, asset_root=None):
    import drivecourse
    import driveworld
    course = drivecourse.course_road(length=_ROAD_LEN, width=_ROAD_W)
    props = []
    if lead_pose_f is not None:
        x, y, yaw = lead_pose_f
        props.append((lead_asset, float(x), float(y), float(yaw)))
    return driveworld.world_build(course, props=props, asset_root=asset_root)


def carla_scene_synthetic(lead_distance_m: float = 20.0, *, width: int = 320, height: int = 180, fov_deg: float = 90.0,
                          cam_height: float = 1.6, lateral: float = 0.0, lead_asset: str = "sedan",
                          asset_root=None) -> dict:
    """自前の世界(直線路 + 先行車)を **CARLA の規約の場面記録**にする(撮影記録と同じ鍵・型)。

    自車のカメラは (x = 20, y = 0, z = cam_height) で +x を向き、先行車(``lead_asset``)の後ろ面がカメラから
    ``lead_distance_m`` 先(横に ``lateral`` m、Fullseye の +y = 左)に来る。``lead_distance_m <= 0`` は先行車なし。
    返り値には ``depth`` [m] と ``label``(Fullseye のラベル像)と ``pose``(render3d の world → camera)も入れる
    (記録の鍵ではないが門で使う)。"""
    import driveworld
    op = "carla_scene_synthetic"
    d = float(lead_distance_m)
    W, H = int(width), int(height)
    if W <= 0 or H <= 0 or not np.isfinite(d) or cam_height <= 0:
        raise ValueError("%s: need positive size, finite distance and positive camera height" % op)
    if lead_asset not in driveworld.ASSETS:
        raise ValueError("%s: unknown asset %r" % (op, lead_asset))
    L, Wc, Hc = driveworld.ASSETS[lead_asset][2]
    eye = np.array([_EGO_X, 0.0, float(cam_height)])
    pose = driveworld.camera_pose(eye, eye + np.array([1.0, 0.0, 0.0]))
    Kc = carla_intrinsics(fov_deg, W, H)
    Kf = intrinsics_to_fullseye(Kc)
    has_lead = d > 0
    lead_f = (eye[0] + d + 0.5 * L, float(lateral), 0.0) if has_lead else None
    world = _scene_world(lead_f, lead_asset, asset_root)
    view = driveworld.world_camera(world, pose, Kf, W, H)
    rgb = np.clip(np.asarray(view["color"]) * 255.0 + 0.5, 0, 255).astype(np.uint8)
    label = np.asarray(view["label"], np.int64)
    depth = np.asarray(view["depth"], np.float64)
    depth = np.where(np.isfinite(depth) & (label >= 0), depth, DEPTH_SCALE_M)
    cam6 = camera_pose_to_carla(pose)
    ego_f = np.eye(4)
    ego_f[:3, 3] = [eye[0] - 1.5, 0.0, 0.0]            # 自車の中心はカメラの 1.5 m 後ろ(撮影記録と同じ取り付け)
    ego6 = world_pose_to_carla(ego_f)
    if has_lead:
        lead_T = np.eye(4)
        lead_T[:3, 3] = [lead_f[0], lead_f[1], 0.5 * Hc]
        lead6 = world_pose_to_carla(lead_T)
    else:
        lead6 = np.full(6, np.nan)
    meta = {"map": "fullseye:course_road", "frame": 0, "fixed_delta": 0.0, "fov_deg": float(fov_deg), "width": W,
            "height": H, "carla_version": "synthetic", "lead_distance_m": d if has_lead else None,
            "lead_blueprint": "fullseye:%s" % lead_asset, "ego_blueprint": "fullseye:camera", "weather": "lambert",
            "lateral_m": float(lateral), "cam_height_m": float(cam_height)}
    scene = {"rgb": rgb, "depth_raw": carla_depth_encode(depth), "semantic": carla_label_unmap(label), "K": Kc,
             "cam_transform": cam6, "ego_transform": ego6, "lead_transform": lead6,
             "ego_extent": np.array([2.25, 0.9, 0.725]), "lead_extent": np.array([0.5 * L, 0.5 * Wc, 0.5 * Hc]),
             "meta": meta, "depth": depth, "label": label, "pose": pose}
    carla_scene_check(scene)
    return scene


def carla_scene_world(scene, *, lead_asset: str = "sedan", asset_root=None) -> dict:
    """場面記録 → 自前の世界(直線路 + 記録の姿勢に置いた先行車)。カメラと先行車の相対配置を保ったまま、
    カメラを (20, 0) で +x 向きに正規化する(CARLA の地図の座標は使わない)。先行車なしなら道だけ。"""
    info = carla_scene_check(scene)
    cam_f = carla_pose_to_world(scene["cam_transform"])
    fwd = cam_f[:3, 0]
    yaw_c = math.atan2(fwd[1], fwd[0])
    lead_f = None
    if info["has_lead"]:
        lead_T = carla_pose_to_world(scene["lead_transform"])
        rel = lead_T[:3, 3] - cam_f[:3, 3]
        c, s = math.cos(-yaw_c), math.sin(-yaw_c)
        rx = c * rel[0] - s * rel[1]
        ry = s * rel[0] + c * rel[1]
        lead_yaw = math.atan2(lead_T[1, 0], lead_T[0, 0]) - yaw_c
        lead_f = (_EGO_X + rx, ry, lead_yaw)
    return _scene_world(lead_f, lead_asset, asset_root)


def carla_scene_render(scene, *, lead_asset: str = "sedan", asset_root=None) -> dict:
    """場面記録を自前の世界で撮り直す(同じ K・同じ取り付け高さ・同じ画角)→ driveworld.world_camera の像
    (``color`` / ``label`` / ``depth`` …)+ ``pose`` + ``K``。CARLA の像と**並べて**見るための片割れ。"""
    import driveworld
    info = carla_scene_check(scene)
    world = carla_scene_world(scene, lead_asset=lead_asset, asset_root=asset_root)
    cam_f = carla_pose_to_world(scene["cam_transform"])
    fwd = cam_f[:3, 0]
    pitch = math.atan2(fwd[2], math.hypot(fwd[0], fwd[1]))
    eye = np.array([_EGO_X, 0.0, float(cam_f[2, 3])])
    target = eye + np.array([math.cos(pitch), 0.0, math.sin(pitch)])
    pose = driveworld.camera_pose(eye, target)
    Kf = intrinsics_to_fullseye(scene["K"])
    view = driveworld.world_camera(world, pose, Kf, info["width"], info["height"])
    view["pose"] = pose
    view["K"] = Kf
    return view


# ----------------------------------------------------------------------------------------------------------------------
# 採点
def lead_truth_depth(scene) -> float:
    """記録の姿勢から閉形式: 先行車の後ろ面の中心までの**像面距離** [m]。後ろ面 = 中心 − 半長 × 先行車の前方向、
    像面距離 = (後ろ面 − カメラ)·カメラの前方向。先行車なしは inf。"""
    info = carla_scene_check(scene)
    if not info["has_lead"]:
        return float("inf")
    cam = carla_pose_to_world(scene["cam_transform"])
    lead = carla_pose_to_world(scene["lead_transform"])
    ex = float(np.asarray(scene["lead_extent"], np.float64)[0])
    rear = lead[:3, 3] - ex * lead[:3, 0]
    return float(np.dot(rear - cam[:3, 3], cam[:3, 0]))


def lead_from_depth(depth, label, K, cam_height: float, *, pitch: float = 0.0, band: float = 0.5,
                    car_label: int = 2) -> dict:
    """ルールベースの先行車の距離(両方の世界に同じ式):
    ``depth_median`` = 画像の中央の帯(幅 band × W)にある車の画素の深度の中央値(後ろ面は像面に平行なので一定)、
    ``row_distance`` = 車の最下行から平らな路面の式(driveenv.road_row_distance)で出した水平距離、
    ``bbox`` = (top, bottom, left, right)、``n_pixels``、``found``。車の画素が無ければ found = False(距離は inf)。"""
    import driveenv
    op = "lead_from_depth"
    D = np.asarray(depth, np.float64)
    Lb = np.asarray(label)
    if D.ndim != 2 or Lb.shape != D.shape:
        raise ValueError("%s: depth and label must be 2-D of the same size" % op)
    k = _K(K, op)
    if not (0.0 < float(band) <= 1.0) or float(cam_height) <= 0:
        raise ValueError("%s: need 0 < band <= 1 and positive camera height" % op)
    H, W = D.shape
    cols = np.arange(W)
    half = 0.5 * float(band) * W
    mask = (Lb == int(car_label)) & (np.abs(cols[None, :] - k[0, 2]) <= half)
    n = int(mask.sum())
    if n == 0:
        return {"found": False, "depth_median": float("inf"), "row_distance": float("inf"), "bbox": None, "n_pixels": 0}
    rows = np.where(mask.any(axis=1))[0]
    cs = np.where(mask.any(axis=0))[0]
    bottom = int(rows.max())
    dm = float(np.median(D[mask]))
    rd = float(driveenv.road_row_distance(np.array([bottom + 0.5]), k[1, 2], k[1, 1], float(cam_height), float(pitch))[0])
    return {"found": True, "depth_median": dm, "row_distance": rd,
            "bbox": (int(rows.min()), bottom, int(cs.min()), int(cs.max())), "n_pixels": n}


def scene_pair_table(scene, *, lead_asset: str = "sedan", asset_root=None) -> dict:
    """1 つの場面記録を **CARLA の像**と**自前の世界の像**の両方で採点して並べる。
    返り値 = ``{"truth", "carla": {...lead_from_depth}, "fullseye": {...}, "carla_error", "fullseye_error", "width", "height"}``
    (誤差 = depth_median − 真値、真値は :func:`lead_truth_depth`)。"""
    info = carla_scene_check(scene)
    truth = lead_truth_depth(scene)
    cam_f = carla_pose_to_world(scene["cam_transform"])
    fwd = cam_f[:3, 0]
    pitch = -math.atan2(fwd[2], math.hypot(fwd[0], fwd[1]))      # road_row_distance の俯角は下向き +
    h = float(cam_f[2, 3])
    Kf = intrinsics_to_fullseye(scene["K"])
    dep_c = scene["depth"] if "depth" in scene else carla_depth_decode(scene["depth_raw"])
    lab_c = carla_label_map(scene["semantic"])
    rc = lead_from_depth(dep_c, lab_c, Kf, h, pitch=pitch)
    view = carla_scene_render(scene, lead_asset=lead_asset, asset_root=asset_root)
    rf = lead_from_depth(view["depth"], view["label"], Kf, h, pitch=pitch)
    err = lambda r: (r["depth_median"] - truth) if (r["found"] and np.isfinite(truth)) else float("nan")
    return {"truth": truth, "carla": rc, "fullseye": rf, "carla_error": err(rc), "fullseye_error": err(rf),
            "width": info["width"], "height": info["height"], "view": view}
