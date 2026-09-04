# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""optscene — 光学系を**物理空間**に組んで、実際のカメラが撮るはずの画像を返す。

ユーザー方針(2026-09-05)「光学系を物理空間に再現する op が要る」「Virtualising
Machine Vision で出来ることを op で再現したい」。

これまでの仮想 MV(``visiondesign`` / ``defectgen`` / ``visionlab``)は
**「レンダラを持てないので画像でなく限界を返す」**という線引きで作ってあった。
本モジュールがその線引きを外す層で、mm 単位の 3-D 空間に部品・照明・カメラを置き、
実際に光線を飛ばして **画像 + 深度の真値 + 画素完全なマスク**を同時に返す。
真値が同じ計算から出るので、検査アルゴリズムを**採点できる**のがこの層の要点。

棲み分け(**再実装せず import して合成**):
  * 照明の幾何 = ``illumdesign.light_source``(ring/dome/bar/coaxial/backlight)を
    そのまま食う。放射照度・一様性の**設計**はあちら、空間での**撮像**がこちら。
  * 材質の分光反射率 = ``glassmirror``(Fresnel の誘電体・導体、Beer–Lambert)。
  * 仕上げの粗さ(異方性ローブの alpha_x/alpha_y)= ``metalfinish.finish_catalog``。
  * 硝材の分散 = ``raytrace.refractive_index``(Sellmeier 20 種)。
  * 実レンズの劣化(歪曲・視野依存 PSF・周辺光量・雑音)= ``lensimage.render_through_lens``
    を**後段**に掛ける。本モジュールは理想ピンホールの放射輝度までを担当する。

座標系: **z 上向き・mm**(``illumdesign`` と同じ。部品は z=0 の面に載る)。

**どれを使うか(用途が違うものは混ぜない)**:

===========================  =========================================================
やりたいこと                 使う op
===========================  =========================================================
検査画像 + 真値がほしい      ``render_optscene`` + ``optscene_depth`` /
                             ``optscene_mask`` / ``optscene_defect_mask``
学習データを大量にほしい     ``random_defects`` → ``inspection_dataset``
きれいな絵がほしい           ``render_studio``(環境光・多重反射・分散)
実センサの見え方にしたい     ``sensor_capture``(ショット雑音・飽和・量子化)
実レンズの劣化も入れたい     ``lensimage.render_through_lens`` を後段に
撮る前に限界だけ知りたい     ``visiondesign`` / ``visionlab``(画像を作らず限界を返す)
===========================  =========================================================

``render_optscene`` と ``render_studio`` は**同じシーンを食うが作り方が違う**。
前者は実在の照明器具を物理単位で置いて直接光だけを数える(だから測光に根拠があり、
真値と突き合わせられる)。後者は環境全体から光が来る前提で多重反射まで解く(だから
金属が金属に見えるが、明るさの絶対値には意味が無い)。検査の絵に多重反射を混ぜると
根拠が濁り、見せる絵に点光源だけを使うと金属が真っ黒になる(実測: 鏡面ローブの
ピークが 1.07e-96)。

使い方:
    import optscene, illumdesign
    part  = optscene.scene_sphere((0, 0, 5), 5.0, optscene.scene_material("lambert", albedo=0.55))
    stage = optscene.scene_plane(0.0, optscene.scene_material("lambert", albedo=0.15))
    cam   = optscene.optical_camera(focal_mm=25.0, pixel_um=3.45, resolution=(256, 256),
                                    working_distance_mm=200.0)
    light = illumdesign.light_source(kind="dome", radius_mm=80.0, height_mm=60.0, n=64)
    img   = optscene.render_optscene([part, stage], cam, [light])
    depth = optscene.optscene_depth([part, stage], cam)      # 真値 [mm]
    mask  = optscene.optscene_mask([part, stage], cam, 0)    # 画素完全な真値マスク
"""
from __future__ import annotations

import time

import numpy as np

import glassmirror as _gm
import metalfinish as _mf
import raytrace as _rt

__all__ = [
    "scene_material", "scene_plane", "scene_sphere", "scene_box", "scene_cylinder", "scene_difference",
    "optical_camera", "camera_rays", "reflect_rays",
    "trace_rays", "illumination_visibility",
    "surface_defect", "surface_finish", "random_defects", "render_optscene", "optscene_depth", "optscene_mask",
    "optscene_defect_mask", "optscene_instances", "sensor_catalog", "sensor_spec", "lens_spec", "light_spec", "light_wavelengths",
    "vision_layout", "layout_capture", "linescan_capture", "interface_budget", "optical_budget", "observe_surface", "defocus_blur", "diffraction_blur", "airy_radius_um", "sensor_capture", "inspection_dataset",
    "dataset_throughput", "env_studio", "env_lightbox", "render_studio",
]

_UP = np.array([0.0, 0.0, 1.0])
_RGB_UM = (0.610, 0.550, 0.465)          # R/G/B の代表波長 [µm](分散をこの 3 点で解く)
_MATERIALS = ("lambert", "conductor", "dielectric")


# --------------------------------------------------------------------------- #
# 小道具
# --------------------------------------------------------------------------- #
def _arr(x, name, n=None):
    a = np.asarray(x, dtype=np.float64)
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must be finite, got {x!r}")
    if n is not None and a.shape[-1] != n:
        raise ValueError(f"{name} must have last axis {n}, got shape {a.shape}")
    return a


def _pos(x, name):
    v = float(x)
    if not np.isfinite(v) or v <= 0.0:
        raise ValueError(f"{name} must be a positive finite number, got {x!r}")
    return v


def _unit(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    if np.any(n < 1e-12):
        raise ValueError("direction vector of zero length cannot be normalised")
    return v / n


def _safe_unit(v):
    """向きが定まらない行を許容する内部用(交差しなかった光線など)。"""
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


# --------------------------------------------------------------------------- #
# シーン記述
# --------------------------------------------------------------------------- #
def scene_material(kind: str = "lambert", albedo=0.6, metal: str = "al",
                   finish: str = "random", glass: str = "N-BK7",
                   sigma_per_mm: float = 0.0, roughness_um: float = 0.05) -> dict:
    """材質を 1 つ作る。``kind`` は lambert / conductor / dielectric の 3 種。

    3 種しか無いのは**混ぜると黙って間違う**からで、増やすなら型を分ける
    (拡散か・金属か・透明か で光線の行き先が根本的に変わる)。

    lambert: ``albedo``(スカラまたは RGB 3 要素)だけを使う完全拡散。
    conductor: ``metal``(``glassmirror.METALS``)の複素屈折率で色が決まり、
        ``finish``(``metalfinish.FINISHES``)で異方性ローブの幅が決まる。**色は指定しない**。
        ``roughness_um`` は面粗さ Rq [µm]。鏡面として返る割合が
        exp(-(4πσcosθ/λ)²) で決まる(Davies 1954 / Bennett-Porteus 1961)ので、
        鏡面(0.01 = 研磨)か拡散寄り(1.0 = 梨地)かはこの 1 つで決まる。
        **波長が式に入る**ので、同じ面でも光源の波長で見え方が変わる。
    dielectric: ``glass``(``raytrace.glass_catalog()``)の Sellmeier 分散で屈折し、
        ``sigma_per_mm`` の Beer–Lambert で吸収する。

    返り値: 上記を検証済みで格納した dict(他の scene_* op にそのまま渡す)。
    """
    if kind not in _MATERIALS:
        raise ValueError(f"kind must be one of {_MATERIALS}, got {kind!r}")
    m = {"kind": kind}
    if kind == "lambert":
        a = _arr(albedo, "albedo")
        if a.ndim == 0:
            a = np.repeat(a[None], 3)
        if a.shape != (3,):
            raise ValueError(f"albedo must be a scalar or 3 values, got shape {a.shape}")
        if np.any(a < 0.0) or np.any(a > 1.0):
            raise ValueError("albedo must lie in [0, 1] (energy conservation)")
        m["albedo"] = a
    elif kind == "conductor":
        if metal not in _gm.METALS:
            raise ValueError(f"metal must be one of {tuple(_gm.METALS)}, got {metal!r}")
        if finish not in _mf.FINISHES:
            raise ValueError(f"finish must be one of {tuple(_mf.FINISHES)}, got {finish!r}")
        rq = float(roughness_um)
        if not np.isfinite(rq) or rq < 0.0:
            raise ValueError(f"roughness_um must be finite and >= 0, got {roughness_um!r}")
        cat = _mf.finish_catalog()[finish]
        m.update(metal=metal, finish=finish, roughness_um=rq,
                 alpha_x=float(cat["alpha_x"]), alpha_y=float(cat["alpha_y"]))
    else:
        sig = float(sigma_per_mm)
        if not np.isfinite(sig) or sig < 0.0:
            raise ValueError(f"sigma_per_mm must be finite and >= 0, got {sigma_per_mm!r}")
        # 硝材名は raytrace 側で検証させる(カタログの単一真実源はあちら)
        m["n_rgb"] = np.array([float(_rt.refractive_index(glass, w)) for w in _RGB_UM])
        m.update(glass=glass, sigma_per_mm=sig)
    return m


def scene_plane(z_mm: float = 0.0, material=None, half_size_mm=None) -> dict:
    """z = ``z_mm`` の水平面(ステージ/コンベア)。``half_size_mm`` で有限の板にできる。

    有限板は (hx, hy) の半サイズ [mm]。省略すると無限平面(背景として使う)。
    """
    z = float(z_mm)
    if not np.isfinite(z):
        raise ValueError(f"z_mm must be finite, got {z_mm!r}")
    h = None if half_size_mm is None else _arr(half_size_mm, "half_size_mm", 2)
    if h is not None and np.any(h <= 0.0):
        raise ValueError("half_size_mm must be positive")
    return {"kind": "plane", "z": z, "half": h,
            "material": material or scene_material("lambert", 0.2)}


def scene_sphere(center_mm, radius_mm: float, material=None) -> dict:
    """球の部品。``center_mm`` は (x, y, z) [mm]、``radius_mm`` > 0。"""
    return {"kind": "sphere", "c": _arr(center_mm, "center_mm", 3),
            "r": _pos(radius_mm, "radius_mm"),
            "material": material or scene_material("lambert", 0.6)}


def scene_box(center_mm, half_size_mm, material=None) -> dict:
    """軸平行な直方体の部品(AABB)。``half_size_mm`` は各軸の半サイズ [mm]。"""
    h = _arr(half_size_mm, "half_size_mm", 3)
    if np.any(h <= 0.0):
        raise ValueError("half_size_mm must be positive in every axis")
    return {"kind": "box", "c": _arr(center_mm, "center_mm", 3), "h": h,
            "material": material or scene_material("lambert", 0.6)}


def scene_cylinder(center_mm, radius_mm: float, half_height_mm: float, material=None) -> dict:
    """z 軸に平行な有限円筒(端面つき)。**加工仕上げが実際に載る形**。

    旋盤の同心目は端面(円盤)に、ヘアラインとローレットは側面に出る ―― 球に
    ヘアラインを掛けるのは現実には珍しい(2026-09-05 のユーザー指摘)。薄くすれば
    円盤、厚くすれば軸物、``radius_mm`` を大きく取れば円板ステージにもなる。
    """
    return {"kind": "cylinder", "c": _arr(center_mm, "center_mm", 3),
            "r": _pos(radius_mm, "radius_mm"), "hz": _pos(half_height_mm, "half_height_mm"),
            "material": material or scene_material("lambert", 0.6)}


def scene_difference(solid: dict, cavity: dict) -> dict:
    """``solid`` から ``cavity`` をくり抜く(CSG の差集合)。**中空の部品**を作る唯一の手段。

    コップ = 外側の円筒 − 底より上にずらした内側の円筒。ほかにワッシャ、貫通穴、
    座ぐり ―― 実際の部品は穴が開いているほうが普通で、球だけでは足りない
    (2026-09-05 のユーザー指摘)。

    両方とも凸プリミティブ(sphere / box / cylinder)でなければならない。平面は
    体積を囲まないので拒否する(fail-closed)。入れ子にすれば穴を 2 つ空けられる。
    """
    for name, obj in (("solid", solid), ("cavity", cavity)):
        if not isinstance(obj, dict) or obj.get("kind") not in ("sphere", "box", "cylinder", "difference"):
            raise ValueError(f"{name} must be a sphere/box/cylinder/difference "
                             f"(a plane encloses no volume), got {obj.get('kind') if isinstance(obj, dict) else obj!r}")
    return {"kind": "difference", "a": solid, "b": cavity,
            "material": solid.get("material") or scene_material("lambert", 0.6)}


# --------------------------------------------------------------------------- #
# カメラ
# --------------------------------------------------------------------------- #
def optical_camera(focal_mm: float = 25.0, pixel_um: float = 3.45,
                   resolution=(256, 256), working_distance_mm: float = 200.0,
                   look_at_mm=(0.0, 0.0, 0.0), tilt_deg: float = 0.0,
                   azimuth_deg: float = 0.0) -> dict:
    """実在の諸元(焦点距離・画素ピッチ・解像度・作動距離)から理想ピンホールを組む。

    ``tilt_deg`` は真上(0°)からの傾き、``azimuth_deg`` はその方位。カメラは
    ``look_at_mm`` を見下ろす。返り値には内部行列 K [px] と姿勢 (R, t) が入る
    ―― ``calib`` / ``calibration3d`` 系の op と同じ規約なので、そのまま
    再投影や校正の検証に渡せる。

    視野は tan 半角 = (画素数/2 · 画素ピッチ) / 焦点距離 で決まる。作動距離での
    視野幅 [mm] を ``fov_mm`` に入れてあるので、部品が収まるかを見てから撮れる。
    """
    f = _pos(focal_mm, "focal_mm")
    px = _pos(pixel_um, "pixel_um") * 1e-3                      # µm → mm
    res = np.asarray(resolution, dtype=int)
    # 高さ 1 = ラインセンサ(linescan_capture が搬送しながら積む)
    if res.shape != (2,) or res[0] < 2 or res[1] < 1:
        raise ValueError(f"resolution must be (width >= 2, height >= 1), got {resolution!r}")
    wd = _pos(working_distance_mm, "working_distance_mm")
    tgt = _arr(look_at_mm, "look_at_mm", 3)
    tilt, az = np.radians(float(tilt_deg)), np.radians(float(azimuth_deg))
    if not (0.0 <= float(tilt_deg) < 90.0):
        raise ValueError("tilt_deg must be in [0, 90) (the camera must look down on the stage)")

    # 視線: 真上から tilt だけ倒し、azimuth で回す。eye は look_at から作動距離ぶん戻る
    view = np.array([np.sin(tilt) * np.cos(az), np.sin(tilt) * np.sin(az), np.cos(tilt)])
    eye = tgt + wd * view
    fwd = _unit((tgt - eye)[None])[0]
    ref = _UP if abs(float(fwd @ _UP)) < 0.999 else np.array([0.0, 1.0, 0.0])
    right = _unit(np.cross(fwd, ref)[None])[0]
    down = np.cross(fwd, right)                                 # 画像の +y は下向き(CV 規約)
    w, h = int(res[0]), int(res[1])
    fpx = f / px
    K = np.array([[fpx, 0.0, (w - 1) / 2.0], [0.0, fpx, (h - 1) / 2.0], [0.0, 0.0, 1.0]])
    R = np.stack([right, down, fwd])                            # world → camera
    return {"K": K, "R": R, "t": -R @ eye, "eye": eye, "forward": fwd,
            "width": w, "height": h, "focal_mm": f, "pixel_mm": px,
            "working_distance_mm": wd,
            "fov_mm": (w * px * wd / f, h * px * wd / f)}


def camera_rays(camera: dict) -> tuple:
    """カメラ dict → 全画素の光線 (origins (H·W, 3), directions (H·W, 3))。

    方向は単位ベクトル、原点はすべて視点。画素 (u, v) は行優先で並ぶので
    ``reshape(height, width, 3)`` で像に戻せる。K の逆写像で作っているため、
    交点を K で再投影すると元の画素に**厳密に**戻る(往復誤差 < 1e-9)。
    """
    K, R = camera["K"], camera["R"]
    w, h = camera["width"], camera["height"]
    vv, uu = np.mgrid[0:h, 0:w].astype(np.float64)
    cam = np.stack([(uu - K[0, 2]) / K[0, 0], (vv - K[1, 2]) / K[1, 1], np.ones_like(uu)], -1)
    d = _safe_unit(cam.reshape(-1, 3) @ R)                      # camera → world (R は直交)
    o = np.broadcast_to(camera["eye"], d.shape).copy()
    return o, d


def reflect_rays(directions, normals):
    """鏡面反射 d − 2(d·n)n。``glassmirror.refract_rays`` の相方(反射側が無かった)。

    入射・法線ともに (..., 3)。法線の向き(表裏)には依存しない。返り値は単位ベクトル。
    """
    d = _unit(_arr(directions, "directions", 3))
    n = _unit(_arr(normals, "normals", 3))
    if d.shape != n.shape:
        d, n = np.broadcast_arrays(d, n)
    return _safe_unit(d - 2.0 * (d * n).sum(-1, keepdims=True) * n)


# --------------------------------------------------------------------------- #
# 交差
# --------------------------------------------------------------------------- #
def _hit_plane(obj, o, d):
    dz = d[..., 2]
    ok = np.abs(dz) > 1e-12
    t = np.where(ok, (obj["z"] - o[..., 2]) / np.where(ok, dz, 1.0), np.inf)
    t = np.where(ok & (t > 1e-6), t, np.inf)
    if obj["half"] is not None:                                 # 有限板は板の外を捨てる
        p = o + np.where(np.isfinite(t), t, 0.0)[..., None] * d
        inside = (np.abs(p[..., 0]) <= obj["half"][0]) & (np.abs(p[..., 1]) <= obj["half"][1])
        t = np.where(inside, t, np.inf)
    return t


def _hit_sphere(obj, o, d, inside=False):
    oc = o - obj["c"]
    b = (oc * d).sum(-1)
    cc = (oc * oc).sum(-1) - obj["r"] ** 2
    disc = b * b - cc
    ok = disc > 0.0
    sq = np.sqrt(np.maximum(disc, 0.0))
    near, far = -b - sq, -b + sq
    t = far if inside else np.where(near > 1e-6, near, far)
    return np.where(ok & (t > 1e-6), t, np.inf)


def _hit_box(obj, o, d, inside=False):
    lo, hi = obj["c"] - obj["h"], obj["c"] + obj["h"]
    inv = 1.0 / np.where(np.abs(d) < 1e-12, 1e-12, d)
    t1, t2 = (lo - o) * inv, (hi - o) * inv
    tmin = np.max(np.minimum(t1, t2), axis=-1)
    tmax = np.min(np.maximum(t1, t2), axis=-1)
    t = tmax if inside else np.where(tmin > 1e-6, tmin, tmax)
    return np.where((tmax >= np.maximum(tmin, 0.0)) & (t > 1e-6), t, np.inf)


def _hit_cylinder(obj, o, d, inside=False):
    """側面(2 次)と端面(2 枚の円盤)の最小/最大交点。inside=True で射出側を返す。"""
    c, r, hz = obj["c"], obj["r"], obj["hz"]
    oc = o - c
    a = (d[..., 0] ** 2 + d[..., 1] ** 2)
    b = 2.0 * (oc[..., 0] * d[..., 0] + oc[..., 1] * d[..., 1])
    cc = oc[..., 0] ** 2 + oc[..., 1] ** 2 - r * r
    disc = b * b - 4.0 * a * cc
    ok = (disc > 0.0) & (a > 1e-15)
    sq = np.sqrt(np.maximum(disc, 0.0))
    aa = np.where(a > 1e-15, a, 1.0)
    cand = []
    for t in ((-b - sq) / (2.0 * aa), (-b + sq) / (2.0 * aa)):   # 側面
        z = oc[..., 2] + t * d[..., 2]
        cand.append(np.where(ok & (np.abs(z) <= hz) & (t > 1e-6), t, np.inf))
    dz = np.where(np.abs(d[..., 2]) > 1e-12, d[..., 2], 1e-12)
    for zc in (-hz, hz):                                          # 端面
        t = (zc - oc[..., 2]) / dz
        rad = (oc[..., 0] + t * d[..., 0]) ** 2 + (oc[..., 1] + t * d[..., 1]) ** 2
        cand.append(np.where((np.abs(d[..., 2]) > 1e-12) & (rad <= r * r) & (t > 1e-6), t, np.inf))
    st = np.stack(cand, 0)
    if inside:
        far = np.where(np.isfinite(st), st, -np.inf).max(0)
        return np.where(np.isfinite(far) & (far > 1e-6), far, np.inf)
    return st.min(0)


def _boundaries(obj, o, d):
    """凸プリミティブの入口/出口 t(当たらなければ両方 inf)。差集合の材料。"""
    if obj["kind"] == "sphere":
        oc = o - obj["c"]
        b = (oc * d).sum(-1)
        cc = (oc * oc).sum(-1) - obj["r"] ** 2
        disc = b * b - cc
        ok = disc > 0.0
        sq = np.sqrt(np.maximum(disc, 0.0))
        return (np.where(ok, -b - sq, np.inf), np.where(ok, -b + sq, np.inf))
    if obj["kind"] == "box":
        lo, hi = obj["c"] - obj["h"], obj["c"] + obj["h"]
        inv = 1.0 / np.where(np.abs(d) < 1e-12, 1e-12, d)
        t1, t2 = (lo - o) * inv, (hi - o) * inv
        tmin = np.max(np.minimum(t1, t2), axis=-1)
        tmax = np.min(np.maximum(t1, t2), axis=-1)
        ok = tmax >= tmin
        return (np.where(ok, tmin, np.inf), np.where(ok, tmax, np.inf))
    if obj["kind"] == "cylinder":
        c, r, hz = obj["c"], obj["r"], obj["hz"]
        oc = o - c
        a = d[..., 0] ** 2 + d[..., 1] ** 2
        b = 2.0 * (oc[..., 0] * d[..., 0] + oc[..., 1] * d[..., 1])
        cc = oc[..., 0] ** 2 + oc[..., 1] ** 2 - r * r
        disc = b * b - 4.0 * a * cc
        ok = (disc > 0.0) & (a > 1e-15)
        sq = np.sqrt(np.maximum(disc, 0.0))
        aa = np.where(a > 1e-15, a, 1.0)
        ts = []
        for t in ((-b - sq) / (2.0 * aa), (-b + sq) / (2.0 * aa)):
            z = oc[..., 2] + t * d[..., 2]
            ts.append(np.where(ok & (np.abs(z) <= hz), t, np.inf))
        dz = np.where(np.abs(d[..., 2]) > 1e-12, d[..., 2], 1e-12)
        for zc in (-hz, hz):
            t = (zc - oc[..., 2]) / dz
            rad = (oc[..., 0] + t * d[..., 0]) ** 2 + (oc[..., 1] + t * d[..., 1]) ** 2
            ts.append(np.where((np.abs(d[..., 2]) > 1e-12) & (rad <= r * r), t, np.inf))
        st = np.stack(ts, 0)
        fin = np.isfinite(st)
        any_hit = fin.any(0)
        lo = np.where(any_hit, np.where(fin, st, np.inf).min(0), np.inf)
        hi = np.where(any_hit, np.where(fin, st, -np.inf).max(0), np.inf)
        return (lo, hi)
    raise ValueError(f"cannot take a CSG interval of a {obj['kind']!r} primitive")


def _hit_difference(obj, o, d):
    """差集合 A − B の最初の交点。境界候補を並べ、A の内かつ B の外の点を採る。"""
    a0, a1 = _boundaries(obj["a"], o, d)
    b0, b1 = _boundaries(obj["b"], o, d)
    eps, tol = 1e-6, 1e-9
    best = np.full(o.shape[:1], np.inf)
    # A 由来の面: B に**覆われていない**ところだけが残る。境界が一致する面(コップの口が
    # 外筒の上面とちょうど同じ高さ、など)は「覆われている」側に倒す ―― 境界を除外すると
    # 穴の開いていない蓋が残り、口が塞がる(CSG の古典的な罠)
    for t in (a0, a1):
        ok = np.isfinite(t) & (t > eps)
        covered = np.isfinite(b0) & (t >= b0 - tol) & (t <= b1 + tol)
        best = np.minimum(best, np.where(ok & ~covered, t, np.inf))
    # B 由来の面: 空洞の壁。A の内側にある区間だけが実在する
    for t in (b0, b1):
        ok = np.isfinite(t) & (t > eps) & np.isfinite(a0)
        inside_a = (t > a0 + tol) & (t < a1 - tol)
        best = np.minimum(best, np.where(ok & inside_a, t, np.inf))
    return best


def _hit(obj, o, d, inside=False):
    if obj["kind"] == "difference":
        return _hit_difference(obj, o, d)
    if obj["kind"] == "plane":
        return _hit_plane(obj, o, d)
    if obj["kind"] == "sphere":
        return _hit_sphere(obj, o, d, inside)
    if obj["kind"] == "cylinder":
        return _hit_cylinder(obj, o, d, inside)
    return _hit_box(obj, o, d, inside)


def _residual(obj, p):
    """点がその面にどれだけ乗っているか [mm](0 = 表面上)。差集合の法線判定用。"""
    if obj["kind"] == "sphere":
        return np.abs(np.linalg.norm(p - obj["c"], axis=-1) - obj["r"])
    if obj["kind"] == "cylinder":
        q = p - obj["c"]
        return np.minimum(np.abs(np.hypot(q[..., 0], q[..., 1]) - obj["r"]),
                          np.abs(np.abs(q[..., 2]) - obj["hz"]))
    q = np.abs(p - obj["c"]) - obj["h"]
    return np.abs(q).min(-1)


def _normal(obj, p):
    if obj["kind"] == "difference":
        on_a = _residual(obj["a"], p) <= _residual(obj["b"], p)
        na, nb = _normal(obj["a"], p), _normal(obj["b"], p)
        return np.where(on_a[..., None], na, -nb)      # 空洞側の面は法線が裏を向く
    if obj["kind"] == "plane":
        return np.broadcast_to(_UP, p.shape).copy()
    if obj["kind"] == "sphere":
        return _safe_unit(p - obj["c"])
    if obj["kind"] == "cylinder":
        q = p - obj["c"]
        cap = np.abs(np.abs(q[..., 2]) - obj["hz"]) < 1e-4       # 端面か側面かで法線が違う
        side = _safe_unit(np.stack([q[..., 0], q[..., 1], np.zeros_like(q[..., 2])], -1))
        top = np.stack([np.zeros_like(q[..., 2]), np.zeros_like(q[..., 2]),
                        np.sign(q[..., 2])], -1)
        return np.where(cap[..., None], top, side)
    q = (p - obj["c"]) / obj["h"]                               # 最大成分の面が法線
    k = np.abs(q).argmax(-1)
    n = np.zeros_like(p)
    np.put_along_axis(n, k[..., None], np.sign(np.take_along_axis(q, k[..., None], -1)), -1)
    return n


def _uv_frame(obj, p):
    """表面の (u, v) [mm] と接線 2 本。欠陥を**面に貼る**ための座標。

    平面 = (x, y)、円筒の側面 = (弧長 rθ, z) で端面は (x, y)、直方体は面ごとの平面、
    球は (rθ, rφ)。展開できない形(差集合)は fail-closed —— 曖昧な貼り方を黙って
    選ぶと、学習データのラベルが**もっともらしく間違う**。
    """
    k = obj["kind"]
    if k == "plane":
        q = p - np.array([0.0, 0.0, obj["z"]])
        tu = np.broadcast_to(np.array([1.0, 0.0, 0.0]), p.shape)
        tv = np.broadcast_to(np.array([0.0, 1.0, 0.0]), p.shape)
        return q[..., 0], q[..., 1], tu.copy(), tv.copy()
    if k == "cylinder":
        q = p - obj["c"]
        cap = np.abs(np.abs(q[..., 2]) - obj["hz"]) < 1e-4
        th = np.arctan2(q[..., 1], q[..., 0])
        u = np.where(cap, q[..., 0], th * obj["r"])
        v = np.where(cap, q[..., 1], q[..., 2])
        az = _safe_unit(np.stack([-np.sin(th), np.cos(th), np.zeros_like(th)], -1))
        ex = np.broadcast_to(np.array([1.0, 0.0, 0.0]), p.shape)
        ey = np.broadcast_to(np.array([0.0, 1.0, 0.0]), p.shape)
        ez = np.broadcast_to(np.array([0.0, 0.0, 1.0]), p.shape)
        return u, v, np.where(cap[..., None], ex, az), np.where(cap[..., None], ey, ez)
    if k == "sphere":
        q = p - obj["c"]
        th = np.arctan2(q[..., 1], q[..., 0])
        ph = np.arccos(np.clip(q[..., 2] / obj["r"], -1.0, 1.0))
        n = _safe_unit(q)
        tu = _safe_unit(np.stack([-np.sin(th), np.cos(th), np.zeros_like(th)], -1))
        return th * obj["r"], ph * obj["r"], tu, _safe_unit(np.cross(n, tu))
    if k == "box":
        q = (p - obj["c"]) / obj["h"]
        ax = np.abs(q).argmax(-1)
        loc = p - obj["c"]
        u = np.where(ax == 0, loc[..., 1], loc[..., 0])
        v = np.where(ax == 2, loc[..., 1], loc[..., 2])
        e = np.eye(3)
        tu = np.where((ax == 0)[..., None], e[1], e[0])
        tv = np.where((ax == 2)[..., None], e[1], e[2])
        return u, v, np.broadcast_to(tu, p.shape).copy(), np.broadcast_to(tv, p.shape).copy()
    raise ValueError(f"surface_defect cannot map a {k!r} primitive "
                     "(no unambiguous surface parameterisation); attach the defect to the "
                     "plane/sphere/box/cylinder it is made of instead")


def surface_defect(primitive: dict, field, mask=None, uv_size_mm=(20.0, 20.0),
                   centre_mm=(0.0, 0.0), height_um: float = 0.0,
                   height_field=None) -> dict:
    """2-D の欠陥図を**部品の面に貼る**(``defectgen`` の出力をそのまま食う)。

    ``field`` は明るさの変調 (H, W)(0 = 変化なし、−0.3 = 30% 暗い傷)。
    ``height_um`` を与えると同じ図を**高さ**とも解釈し、勾配から法線を傾ける
    ―― これがあると、同じ傷がドーム照明では消え暗視野照明で光る、という
    **照明を変える意味**が再現される(外観検査 AI の学習データはここが本体)。

    ``height_field`` を別に渡すと、**色は変わらないが凹凸だけがある欠陥**(打痕・
    ひけ・浅い擦り傷)を作れる。``field`` を全ゼロにすれば純粋な地形欠陥になり、
    ドーム照明では消えて低角の暗視野照明で光る ―― この差こそ照明を選ぶ理由。

    ``uv_size_mm`` は貼り付ける実寸 [mm]、``centre_mm`` は面座標上の中心。
    ``mask`` を渡すとその画素が欠陥ラベル(``optscene_defect_mask`` が返す真値)。

    返り値は defect を付けた**新しい**プリミティブ(元は書き換えない)。
    """
    f = _arr(field, "field")
    if f.ndim != 2:
        raise ValueError(f"field must be a 2-D image, got shape {f.shape}")
    m = np.zeros(f.shape, bool) if mask is None else np.asarray(mask, bool)
    if m.shape != f.shape:
        raise ValueError(f"mask shape {m.shape} must match field shape {f.shape}")
    uv = _arr(uv_size_mm, "uv_size_mm", 2)
    if np.any(uv <= 0.0):
        raise ValueError("uv_size_mm must be positive")
    h = float(height_um)
    if not np.isfinite(h):
        raise ValueError(f"height_um must be finite, got {height_um!r}")
    out = dict(primitive)
    hf = f if height_field is None else _arr(height_field, "height_field")
    if hf.shape != f.shape:
        raise ValueError(f"height_field shape {hf.shape} must match field shape {f.shape}")
    out["defect"] = {"field": f, "mask": m, "uv": uv, "height_field": hf,
                     "centre": _arr(centre_mm, "centre_mm", 2), "height_mm": h * 1e-3}
    _uv_frame(out, np.zeros((1, 3)))                      # 貼れない形はここで落とす
    return out


_FINISHES_3D = ("turned", "hairline", "crosshatch", "blasted", "ground", "none")


def surface_finish(primitive: dict, kind: str = "turned", pitch_um: float = 120.0,
                   depth_um: float = 1.5, uv_size_mm=(20.0, 20.0), seed: int = 0,
                   shape=(384, 384)) -> dict:
    """部品の面に**加工目**(旋盤目・ヘアライン・ローレット・梨地・研削目)を刻む。

    欠陥ではない ―― 良品にも必ずあるので :func:`optscene_defect_mask` には出ない。
    それでも要るのは、加工目が**検査をいちばん難しくしている当人**だから。旋盤目と
    細い傷は暗視野で同じように光るので、加工目の無いつるつるの面で学習させた
    モデルは実機で加工目を全部欠陥と呼ぶ。

    ``kind``: turned(同心円)/ hairline(一方向)/ crosshatch(交差)/ blasted(梨地)/
    ground(研削)/ none。``pitch_um`` は目のピッチ、``depth_um`` は谷の深さ。
    どちらも実際の加工の値をそのまま入れる(旋盤の送りは 50-300 µm、Ra は 0.2-3 µm)。

    返り値は加工目を付けた**新しい**プリミティブ(元は書き換えない)。
    """
    if kind not in _FINISHES_3D:
        raise ValueError(f"kind must be one of {_FINISHES_3D}, got {kind!r}")
    uv = _arr(uv_size_mm, "uv_size_mm", 2)
    if np.any(uv <= 0.0):
        raise ValueError("uv_size_mm must be positive")
    pitch = _pos(pitch_um, "pitch_um") * 1e-3            # µm -> mm
    depth = float(depth_um)
    if not np.isfinite(depth) or depth < 0.0:
        raise ValueError(f"depth_um must be finite and >= 0, got {depth_um!r}")
    out = dict(primitive)
    if kind in ("turned", "hairline", "crosshatch", "none"):
        # 規則的な目は**解析的**に評価する。図に焼くとピッチが標本間隔に近づいた
        # ところでモアレになり、旋盤面に実在しない模様が出る(2026-09-05 の実測:
        # 120 µm ピッチ / 49.5 µm texel で中心に十字が立った)。閉じた式なら
        # ピッチをいくら細かくしても、拡大しても崩れない。
        #
        # ただし単一周期の正弦は加工目に見えない(同日のユーザー指摘)。実際の面は
        # 深さも間隔もばらつく = **帯域**を持つので、波数を対数正規で散らした数本の
        # 和にする。振幅は 1/k(粗い成分が Ra を支配する、実加工面と同じ形)、
        # 位相は乱数、ヘアラインには目の向きのゆらぎも入れる。
        rng = np.random.default_rng(int(seed) + 977)
        out["texture"] = {"analytic": kind, "pitch_mm": pitch,
                          "height_mm": depth * 1e-3, "kind": kind,
                          # 偏心はピッチの数倍程度(実機の芯出し残り)
                          "eccentric": tuple(rng.normal(0.0, 3.0 * pitch, 2)),
                          "octaves": _octaves(pitch, int(seed)),
                          "grain_mm": float(rng.uniform(2.0, 6.0)),
                          "components": _finish_components(kind, pitch, int(seed))}
    else:
        # 梨地・研削は不規則なので図を持つしかない。こちらは白色雑音なので
        # 標本化の限界がそのまま「その解像度での粗さ」になる(モアレの嘘は出ない)。
        H, W = int(shape[0]), int(shape[1])
        rng = np.random.default_rng(int(seed))
        if kind == "ground":
            v = (np.arange(H)[:, None] / H - 0.5) * float(uv[1])
            h = np.sin(2 * np.pi * v / pitch + rng.normal(0.0, 0.6, (H, 1))) * np.ones((1, W))
            h = h * (1.0 + 0.25 * rng.normal(0.0, 1.0, (H, W)))
        else:
            h = rng.normal(0.0, 1.0, (H, W))
        out["texture"] = {"height_field": h, "uv": uv, "centre": np.zeros(2),
                          "height_mm": depth * 1e-3, "kind": kind}
    _uv_frame(out, np.zeros((1, 3)))                      # 貼れない形はここで落とす
    return out


def _hash01(i, seed):
    """整数 -> [0,1) の決定的ハッシュ(splitmix64)。seed で完全に再現する。

    最初は LCG + 符号付き算術右シフトで書いていたが、負の整数で符号ビットが伝播して
    撹拌が効かず、**ノイズに擬似周期が残っていた**(2026-09-05 の実測: 傾き profile の
    自己相関の副ピークが 0.951 = ほぼ正弦)。符号なし 64bit の論理シフトで書き直す。
    """
    with np.errstate(over="ignore"):                  # 64bit の巻き戻りは仕様(ハッシュ)
        x = np.asarray(i, np.int64).astype(np.uint64)
        x = x * np.uint64(0x9E3779B97F4A7C15) + np.uint64(seed) * np.uint64(0xBF58476D1CE4E5B9)
        x = x ^ (x >> np.uint64(30))
        x = x * np.uint64(0xBF58476D1CE4E5B9)
        x = x ^ (x >> np.uint64(27))
        x = x * np.uint64(0x94D049BB133111EB)
        x = x ^ (x >> np.uint64(31))
    return (x >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def _noise1d(x, seed):
    """1 次元の勾配ノイズと**その微分**。五次補間なので二階微分まで連続。

    値は概ね [-1, 1]。加工目のような「不規則だが特徴的な間隔を持つ」profile を、
    図に焼かずに(= 標本化せずに)作れるのが要点。
    """
    i = np.floor(x)
    t = x - i
    ii = i.astype(np.int64)
    g0 = _hash01(ii, seed) * 2.0 - 1.0
    g1 = _hash01(ii + 1, seed) * 2.0 - 1.0
    a, b = g0 * t, g1 * (t - 1.0)
    u = t * t * t * (t * (t * 6.0 - 15.0) + 10.0)
    du = 30.0 * t * t * (t - 1.0) * (t - 1.0)
    val = a + u * (b - a)
    der = g0 + u * (g1 - g0) + du * (b - a)
    return val * 2.0, der * 2.0            # 振幅を概ね [-1,1] に揃える


def _octaves(pitch, seed, n=4, lacunarity=2.3, gain=0.7):
    """(波長 [mm], **傾きの重み**, seed) を n オクターブ。

    重みを「高さ」でなく**傾き**に付けるのが要点。面の見え方を決めるのは法線 = 傾きで、
    高さで正規化すると細かいオクターブの傾きが消えて、加工目がほとんど見えなくなる
    (2026-09-05 の実測: 旋盤面が真っ黒になった)。重みは二乗和 1 に揃える。
    """
    lam = pitch * lacunarity ** np.arange(n)[::-1]      # 粗い -> 細かい
    w = gain ** np.arange(n)[::-1]
    w = w / np.sqrt(np.sum(w ** 2))
    return [(float(l), float(a), int(seed) + 101 * k) for k, (l, a) in enumerate(zip(lam, w))]


def _finish_components(kind, pitch, seed, n=11):
    """加工目のスペクトル: (波数 k, 振幅, 位相, 目の向きのゆらぎ, 角度モード m)を n 本。

    波数は 1/pitch を中心に対数正規で散らす(実面の RSm 分布に近い)。振幅は 1/k で
    落とし、全体の RMS が 1 になるよう正規化するので、``depth_um`` がそのまま面の
    粗さ(Ra 相当)の意味になる。

    ``m`` は**角度モード**。旋盤目を半径だけの関数にすると全周が同位相の完全な同心円に
    なり、実物には無い対称性が出る(2026-09-05 のユーザー指摘)。実際には主軸と工具の
    びびりで角度方向にも変調がかかるので、低次の m を混ぜて対称性を壊す。
    """
    if kind == "none":
        return np.zeros((0, 8))
    rng = np.random.default_rng(seed)
    k0 = 2.0 * np.pi / pitch
    k = k0 * np.exp(rng.normal(0.0, 0.55, n))            # 間隔のばらつき
    a = (k0 / k) * np.exp(rng.normal(0.0, 0.35, n))      # 深さのばらつき(粗い成分ほど深い)
    a = a / np.sqrt(np.sum(a ** 2) / 2.0)                # 和の RMS を 1 に揃える
    ph = rng.uniform(0.0, 2.0 * np.pi, n)
    skew = rng.normal(0.0, 0.05, n) * k0                 # 目の向きのゆらぎ(まっすぐ過ぎない)
    m = np.round(rng.normal(0.0, 6.0, n))                # びびりの角度次数(低次が主)
    # 目方向のゆっくりした振幅変調(周期 2-8 mm)。線が濃淡を持つ実物の見え方を作る。
    # これが無いと完全に均一な格子、これを斜め成分でやると干渉して破線になる。
    q = 2.0 * np.pi / rng.uniform(2.0, 8.0, n)
    psi = rng.uniform(0.0, 2.0 * np.pi, n)
    depth_mod = rng.uniform(0.25, 0.75, n)
    return np.stack([k, a, ph, skew, m, q, psi, depth_mod], axis=1)


def _noise_tilt(spec, kind, amp, u, v, tu, tv, footprint):
    """勾配ノイズで作った加工目の法線の傾き。正弦の和と違い**周期が見えない**。

    hairline は「直交方向だけの 1 次元 profile × 目方向のゆっくりした濃淡」、
    turned は「半径方向の 1 次元 profile(偏心つき)× 角度方向のゆらぎ」。
    どのオクターブも、波長が画素の 2 倍を割ったら落とす(位相が復元できない領域で
    構造を作らない = 生成画像に実在しない模様を入れない)。
    """
    w = None if footprint is None else np.abs(np.asarray(footprint, float))
    ec = spec.get("eccentric", (0.0, 0.0))
    ue, ve = u - ec[0], v - ec[1]
    r = np.maximum(np.hypot(ue, ve), 1e-9)
    grain = spec.get("grain_mm", 4.0)
    du = np.zeros(np.shape(u))
    dv = np.zeros(np.shape(u))

    # 斑(まだら): 研磨圧・砥粒の当たりは面内でばらつくので、濃淡は目方向だけでなく
    # **2 次元の低周波むら**になる(2026-09-05 のユーザー指摘「実物はもう少し斑さが
    # ある」)。目方向に長いむら + 直交方向に短いむら の和で作る。
    along = u if kind != "turned" else np.arctan2(ve, ue) * r
    across = v if kind != "turned" else r
    ea, da = _noise1d(along / grain, spec["octaves"][0][2] + 7717)
    eb, db = _noise1d(across / (grain * 0.45), spec["octaves"][0][2] + 3313)
    env = 1.0 + 0.55 * ea + 0.45 * eb
    denv = 0.55 * da / grain                      # 目方向の変化
    denv_across = 0.45 * db / (grain * 0.45)      # 直交方向の変化(斑の境目)
    # 目立つ深い筋(実物のブラシ目には、たまにひときわ深い一本が混じる)。
    # 裾の重い分布にするため、しきい値を超えた分だけを強く増幅する
    across_pitch = across / (spec["pitch_mm"] * 6.0)
    pv, pd = _noise1d(across_pitch, spec["octaves"][0][2] + 5171)
    over = np.maximum(pv - 0.45, 0.0)
    env = env * (1.0 + 2.6 * over)
    gate = 2.6 * np.where(pv > 0.45, pd, 0.0) / (spec["pitch_mm"] * 6.0)
    denv_across = denv_across * (1.0 + 2.6 * over) + (1.0 + 0.55 * ea + 0.45 * eb) * gate

    # 基準の傾き: 同じ深さ・同じピッチの正弦が持つ最大傾き(2*pi*A/p)に合わせる
    k0 = 2.0 * np.pi / spec["pitch_mm"]
    for lam, a, sd in spec["octaves"]:
        A = amp * k0 * a                                 # **傾き**の振幅(高さではない)
        if w is not None:
            A = A * np.abs(np.sinc(w / lam)) * (lam > 2.0 * w)
        if kind == "hairline":
            val, der = _noise1d(v / lam, sd)
            dv += A * der * env + A * lam * val * denv_across
            du += A * lam * val * denv
        elif kind == "turned":
            val, der = _noise1d(r / lam, sd)
            g = A * der * env + A * lam * val * denv_across
            du += g * (ue / r)
            dv += g * (ve / r)
            du += A * lam * val * denv * (-ve / r)       # 角度方向のゆらぎ
            dv += A * lam * val * denv * (ue / r)
        else:                                            # crosshatch: 直交 2 方向
            _vu, ru = _noise1d(u / lam, sd)
            _vv, rv = _noise1d(v / lam, sd + 31)
            du += 0.5 * A * ru
            dv += 0.5 * A * rv
    return -du[..., None] * tu - dv[..., None] * tv


def _analytic_tilt(spec, u, v, tu, tv, footprint=None):
    """規則的な加工目の法線の傾きを閉じた式で返す(標本化しないのでモアレが出ない)。

    ``footprint`` に画素が面上で覆う幅 [mm] を渡すと、箱フィルタの応答
    sinc(w/p) を掛けて**解像できない目を平坦にする**。これが無いと、周期が画素より
    細かいときに実在しない模様(2026-09-05 の実測では放射状の花)が生成画像に入る。
    """
    kind, pitch, amp = spec["analytic"], spec["pitch_mm"], spec["height_mm"]
    if kind == "none" or amp == 0.0:
        return None
    octs = spec.get("octaves")
    if octs:
        return _noise_tilt(spec, kind, amp, u, v, tu, tv, footprint)
    comps = spec.get("components")
    if comps is None or len(comps) == 0:
        return None
    w = None if footprint is None else np.abs(np.asarray(footprint, float))
    du = np.zeros(np.shape(u))
    dv = np.zeros(np.shape(u))
    # 偏心: 工具の回転中心は部品中心と一致しない。ずらすとリングの幅が周で変わる
    ec = spec.get("eccentric", (0.0, 0.0))
    ue, ve = u - ec[0], v - ec[1]
    r = np.maximum(np.hypot(ue, ve), 1e-9)
    th = np.arctan2(ve, ue)
    for k, a, ph, skew, mode, q, psi, dmod in comps:
        A = amp * a
        if w is not None:
            # 画素は面積を積分する = 幅 w の箱フィルタ。周期 p の正弦は箱で積分すると
            # ちょうど sinc(w/p) 倍になる。ただし**高さ**に sinc を掛けるだけでは足りない:
            # 傾きの振幅は A·k ∝ 1/p で増えるので、細かい目ほど打ち消されずに残り、
            # 位相だけが折り返してモアレになる(2026-09-05 の実測: 8 µm ピッチでも
            # 600 µm と同じ振れ幅が残っていた)。ナイキスト(p < 2w)を割ったら位相は
            # 原理的に復元できないので、**構造を作らず平坦に倒す** ―― 生成器が
            # 実在しない模様を描かないための線引き。
            # 局所の空間周波数は半径方向 k と角度方向 m/r の合成
            k_loc = np.hypot(k, mode / r) if kind == "turned" else np.full(np.shape(u), k)
            pitch_i = 2.0 * np.pi / np.maximum(k_loc, 1e-12)
            A = A * np.abs(np.sinc(w / pitch_i)) * (pitch_i > 2.0 * w)
        if kind == "turned":                              # 旋盤の送り目 + びびり + 偏心
            c = A * np.cos(k * r + mode * th + ph)
            du += c * (k * ue / r - mode * ve / (r * r))
            dv += c * (k * ve / r + mode * ue / (r * r))
        elif kind == "hairline":
            # ブラシ目: 直交方向だけの 1 次元粗さ × 目方向のゆっくりした濃淡。
            # 斜め成分を足して干渉させると破線になる(2026-09-05 の実測)ので足さない。
            env = 1.0 + dmod * np.sin(q * u + psi)
            dv += A * k * np.cos(k * v + ph) * env
            du += A * np.sin(k * v + ph) * dmod * q * np.cos(q * u + psi)
        else:                                             # crosshatch(交差目/ローレット)
            du += 0.5 * A * k * np.cos(k * u + ph)
            dv += 0.5 * A * k * np.cos(k * v + ph)
    return -du[..., None] * tu - dv[..., None] * tv


def _sample_map(obj, p, spec, uv_frame):
    """面に貼った 1 枚の図を交点で拾う。返り (明るさ変調, 法線の傾き, 内側か)。"""
    u, v, tu, tv = uv_frame
    hf = spec.get("height_field")
    ref = spec.get("field", hf)
    H, W = ref.shape
    su, sv = float(spec["uv"][0]), float(spec["uv"][1])
    col = np.floor(((u - spec["centre"][0]) / su + 0.5) * W).astype(int)
    row = np.floor(((v - spec["centre"][1]) / sv + 0.5) * H).astype(int)
    inside = (col >= 0) & (col < W) & (row >= 0) & (row < H)
    ci, ri = np.clip(col, 0, W - 1), np.clip(row, 0, H - 1)
    mod = np.where(inside, spec["field"][ri, ci], 0.0) if "field" in spec \
        else np.zeros(p.shape[:1])
    tilt = np.zeros_like(p)
    if hf is not None and spec["height_mm"] != 0.0:       # 高さ図 -> 勾配 -> 法線を傾ける
        gy, gx = np.gradient(hf * spec["height_mm"])
        dhdu = np.where(inside, gx[ri, ci], 0.0) * W / su
        dhdv = np.where(inside, gy[ri, ci], 0.0) * H / sv
        tilt = -dhdu[..., None] * tu - dhdv[..., None] * tv
    return mod, tilt, inside, (ri, ci)


def _defect_sample(obj, p, footprint=None):
    """交点における (明るさ変調, 法線の傾き, 欠陥ラベル)。

    加工目(texture)と欠陥(defect)の**両方**を足すが、**ラベルは欠陥からしか
    作らない** ―― 加工目は良品にも必ずあるので、ラベルに混ぜたらデータが壊れる。
    """
    d, tex = obj.get("defect"), obj.get("texture")
    if d is None and tex is None:
        return np.zeros(p.shape[:1]), np.zeros_like(p), np.zeros(p.shape[:1], bool)
    frame = _uv_frame(obj, p)
    mod = np.zeros(p.shape[:1])
    tilt = np.zeros_like(p)
    lab = np.zeros(p.shape[:1], bool)
    if tex is not None:
        if "analytic" in tex:
            t = _analytic_tilt(tex, frame[0], frame[1], frame[2], frame[3], footprint)
            if t is not None:
                tilt = tilt + t
        else:
            _m, t, _in, _idx = _sample_map(obj, p, tex, frame)
            tilt = tilt + t
    if d is not None:
        m, t, inside, (ri, ci) = _sample_map(obj, p, d, frame)
        mod = mod + m
        tilt = tilt + t
        lab = inside & d["mask"][ri, ci]
    return mod, tilt, lab


def _check_scene(scene):
    if isinstance(scene, dict):
        scene = [scene]
    scene = list(scene)
    if not scene:
        raise ValueError("scene must contain at least one primitive")
    for i, obj in enumerate(scene):
        if not isinstance(obj, dict) or obj.get("kind") not in ("plane", "sphere", "box", "cylinder", "difference"):
            raise ValueError(f"scene[{i}] is not a scene_plane/scene_sphere/"
                             f"scene_box/scene_cylinder/scene_difference result")
    return scene


def trace_rays(scene, origins, directions) -> dict:
    """光線束を撃って最初の交点を返す(レンダラの素になる公開 op)。

    返り値 dict: ``t`` 距離 [mm](当たらなければ inf)、``index`` 当たった
    プリミティブの番号(-1 = 当たらず)、``point`` 交点 [mm]、``normal`` 単位法線
    (当たらなかった行は 0)。当たり判定は fail-closed で、シーンが空なら例外。
    """
    scene = _check_scene(scene)
    o = _arr(origins, "origins", 3).reshape(-1, 3)
    d = _unit(_arr(directions, "directions", 3).reshape(-1, 3))
    if o.shape != d.shape:
        raise ValueError(f"origins {o.shape} and directions {d.shape} must match")
    ts = np.stack([_hit(obj, o, d) for obj in scene], 0)
    idx = ts.argmin(0)
    t = np.take_along_axis(ts, idx[None], 0)[0]
    hit = np.isfinite(t)
    idx = np.where(hit, idx, -1)
    p = o + np.where(hit, t, 0.0)[..., None] * d
    n = np.zeros_like(p)
    for k, obj in enumerate(scene):
        m = idx == k
        if m.any():
            n[m] = _normal(obj, p[m])
    n = np.where(((n * d).sum(-1) > 0.0)[..., None], -n, n)     # 常に入射側を向かせる
    return {"t": t, "index": idx, "point": p, "normal": n}


# --------------------------------------------------------------------------- #
# 照明
# --------------------------------------------------------------------------- #
def _emitters(light):
    if not isinstance(light, dict) or "emitters" not in light or "directions" not in light:
        raise ValueError("light must be an illumdesign.light_source() result "
                         "(needs 'emitters' and 'directions')")
    e = _arr(light["emitters"], "light['emitters']", 3).reshape(-1, 3)
    a = _arr(light["directions"], "light['directions']", 3).reshape(-1, 3)
    if e.shape != a.shape:
        raise ValueError("light emitters and directions must have the same shape")
    return (e, _safe_unit(a), float(light.get("intensity", 1.0)),
            float(light.get("cos_exponent", 1.0)), _emitter_spread(e))


def _emitter_spread(e):
    """発光点群がどれだけ広がっているか [mm](= 1 点が代表する光源面の差し渡し)。

    照明は本来**面**であり、点の集まりで近似している。鏡面ローブの幅が 1 度しか
    ないのに光源が 24 点しか無いと、ローブは点の隙間に落ちて金属が真っ黒になる
    (2026-09-05 の実測: ピーク 1.07e-96)。そこで各発光点の最近傍距離をその点が
    代表する面の大きさとみなし、``_shade`` でローブをその角径ぶん広げる。
    近似だが、光源を細かくしていくと自然に元のローブへ戻る。
    """
    if len(e) < 2:
        return 0.0
    d = np.linalg.norm(e[:, None, :] - e[None, :, :], axis=-1)
    np.fill_diagonal(d, np.inf)
    return float(np.median(d.min(1)))


def illumination_visibility(scene, points, light) -> np.ndarray:
    """各点から見た**発光点の可視率** [0, 1](= 落ち影)。

    点ごとに全発光点への遮蔽を判定して平均する。バックライトのように部品の裏に
    光源がある配置では 0 になり、シルエットが立つ。返り値 (M,)。
    """
    scene = _check_scene(scene)
    p = _arr(points, "points", 3).reshape(-1, 3)
    e, _a, _i, _c, _s = _emitters(light)
    vis = np.zeros(p.shape[0])
    for src in e:
        v = src - p
        dist = np.linalg.norm(v, axis=-1, keepdims=True)
        d = v / np.maximum(dist, 1e-12)
        blocked = np.zeros(p.shape[0], bool)
        for obj in scene:
            th = _hit(obj, p + 1e-4 * d, d)
            blocked |= th < dist[:, 0]                          # 光源より手前で遮られたら影
        vis += ~blocked
    return vis / len(e)


def _light_background(lights, o, d):
    """光線が何にも当たらなかったときに**光源そのものが見える**放射輝度 (M,)。

    これが無いとバックライトが真っ黒になる ―― 透過照明は「光源を直接撮って、
    部品でそれを遮る」方式なので、光源が写らなければ原理的に成立しない。
    各発光点はその点が代表する面(半径 = 最近傍距離の半分)の Lambert 円板とみなす。
    """
    out = np.zeros(o.shape[:1])
    for light in lights:
        e, a, inten, cexp, spread = _emitters(light)
        # 器具の実体の大きさ。point 近似のままだと鏡像が細くなりすぎ、暗視野で
        # 反射がどの発光点にも当たらず真っ黒になる(2026-09-05 の実測)。
        # light["size_mm"] があればそれを使う(実物のリング照明は幅 10-30 mm)。
        rad = max(spread * 0.5, float(light.get("size_mm", 0.0)) * 0.5, 1e-3)
        area = np.pi * rad * rad
        for src, aim in zip(e, a):
            oc = o - src
            b = (oc * d).sum(-1)
            cc = (oc * oc).sum(-1) - rad * rad
            disc = b * b - cc
            t = -b - np.sqrt(np.maximum(disc, 0.0))
            seen = (disc > 0.0) & (t > 1e-6)
            cos_s = np.clip(-(d * aim).sum(-1), 0.0, 1.0)     # 発光面の正面から見るほど明るい
            out += np.where(seen, inten * cos_s ** cexp / area, 0.0)
    return out


def _thin_emitters(e, a, keep):
    """発光点を keep 個へ間引き、重みで明るさを保つ(面光源の照度は滑らかなので効く)。

    落ちるのは影の縁の柔らかさであって、明るさの絶対値ではない ―― 総和は
    len(e)/keep 倍で補正するので、平均の放射照度は保たれる。
    """
    n = len(e)
    if keep is None or keep >= n:
        return e, a, 1.0
    sel = np.linspace(0, n - 1, int(keep)).round().astype(int)   # 一様に間引く(層化)
    sel = np.unique(sel)
    return e[sel], a[sel], n / float(len(sel))


def _irradiance(scene, p, n, light, shadows=True, light_samples=None):
    """点 p・法線 n における放射照度 E と、代表的な入射方向を返す。"""
    e, a, inten, cexp, spread = _emitters(light)
    e, a, boost = _thin_emitters(e, a, light_samples)
    inten = inten * boost
    E = np.zeros(p.shape[0])
    Lsum = np.zeros_like(p)
    dist_sum = np.zeros(p.shape[0])
    wsum = np.zeros(p.shape[0])
    for src, aim in zip(e, a):
        v = src - p
        r2 = np.maximum((v * v).sum(-1), 1e-12)
        d = v / np.sqrt(r2)[..., None]
        cos_s = np.clip(-(d * aim).sum(-1), 0.0, 1.0)           # 光源側のランバート則
        cos_r = np.clip((d * n).sum(-1), 0.0, 1.0)              # 受光面側の傾き
        contrib = inten * (cos_s ** cexp) * cos_r / r2
        if shadows:
            dist = np.sqrt(r2)
            blocked = np.zeros(p.shape[0], bool)
            for obj in scene:
                blocked |= _hit(obj, p + 1e-4 * d, d) < dist
            contrib = np.where(blocked, 0.0, contrib)
        E += contrib
        Lsum += contrib[..., None] * d
        dist_sum += contrib * np.sqrt(r2)
        wsum += contrib
    # 寄与で重み付けした平均距離 → 光源 1 点の角径(ローブを広げる量)
    mean_d = np.where(wsum > 0.0, dist_sum / np.maximum(wsum, 1e-300), np.inf)
    return E, _safe_unit(Lsum), spread / np.maximum(mean_d, 1e-9)


# --------------------------------------------------------------------------- #
# 陰影
# --------------------------------------------------------------------------- #
def _ward(n, l, v, t, b, ax, ay):
    """異方性 Ward ローブ(Ward 1992)。粗さの値は metalfinish.finish_catalog が単一真実源。"""
    h = _safe_unit(l + v)
    ndl = np.clip((n * l).sum(-1), 1e-6, 1.0)
    ndv = np.clip((n * v).sum(-1), 1e-6, 1.0)
    ndh = np.clip((n * h).sum(-1), 1e-6, 1.0)
    ax, ay = np.asarray(ax, float), np.asarray(ay, float)
    hx, hy = (h * t).sum(-1) / ax, (h * b).sum(-1) / ay
    e = np.exp(-(hx * hx + hy * hy) / np.maximum(ndh * ndh, 1e-12))
    return e / (4.0 * np.pi * ax * ay * np.sqrt(np.maximum(ndl * ndv, 1e-12)))


def _tangent(n, finish):
    """仕上げの目の向き。circular は z 軸まわりの周方向、他は世界 x を面へ射影。"""
    if finish == "circular":
        t = np.cross(np.broadcast_to(_UP, n.shape), n)
    else:
        ax = np.array([1.0, 0.0, 0.0])
        t = ax - (n * ax).sum(-1, keepdims=True) * n
    bad = np.linalg.norm(t, axis=-1) < 1e-6
    if bad.any():
        alt = np.array([0.0, 1.0, 0.0])
        t = np.where(bad[..., None], alt - (n * alt).sum(-1, keepdims=True) * n, t)
    t = _safe_unit(t)
    return t, _safe_unit(np.cross(n, t))


def _specular_fraction(mat, cos_theta, wavelength_nm):
    """面粗さ σ の面が**鏡面として**返す割合(Davies 1954 / Bennett-Porteus 1961)。

    s = exp(-(4 π σ cosθ / λ)²)。σ << λ なら鏡(明視野で器具が映る)、σ >> λ なら
    ほぼ散乱(暗視野で光る)。この 1 本で明視野と暗視野の役割分担が決まる。
    """
    sigma_um = float(mat.get("roughness_um", 0.05))
    lam_um = float(wavelength_nm) * 1e-3
    g = 4.0 * np.pi * sigma_um * np.asarray(cos_theta, float) / max(lam_um, 1e-9)
    return np.exp(-np.minimum(g * g, 700.0))


def _specular_fixtures(scene, p, n, v, mat, lights, shadows, samples=24):
    """反射方向の先に**照明器具の実体**があるかを引いて、導体の見え方を決める。

    明視野/暗視野の違いはローブの値ではなく「器具が鏡像として見えるか」なので、
    反射方向を粗さローブで散らし、その先の発光面を数える。器具に当たった標本の
    割合と明るさがそのまま画素値になり、傷は法線が傾いて当たり外れが反転する。
    """
    t, b = _tangent(n, mat["finish"])
    refl = _safe_unit(-v - 2.0 * ((-v) * n).sum(-1, keepdims=True) * n)
    gx, gy = _lowdiscrepancy_gauss(int(samples), seed=17)
    acc = np.zeros(p.shape[:1])
    org = p + 1e-4 * n
    for a, bb in zip(gx, gy):
        rd = _safe_unit(refl + (mat["alpha_x"] * a) * t + (mat["alpha_y"] * bb) * b)
        lit = _light_background(lights, org, rd)
        if shadows and np.any(lit > 0.0):          # 途中に部品があれば器具は見えない
            blocked = np.zeros(p.shape[:1], bool)
            for obj in scene:
                blocked |= np.isfinite(_hit(obj, org, rd))
            lit = np.where(blocked, 0.0, lit)
        acc += lit
    acc /= len(gx)
    cos_v = np.clip((n * v).sum(-1), 0.0, 1.0)
    return acc[..., None] * _gm.metal_mirror_rgb(mat["metal"], cos_v)


def _shade(scene, hit, view, lights, ambient, depth, shadows, footprint=None,
           light_samples=None, wavelength_nm=550.0):
    """交点ごとの放射輝度 (M, 3)。材質で光線の行き先が変わる。"""
    p, n, idx = hit["point"], hit["normal"], hit["index"]
    out = np.full(p.shape, float(ambient))
    for k, obj in enumerate(scene):
        m = idx == k
        if not m.any():
            continue
        mat = obj["material"]
        pm, nm, vm = p[m], n[m], -view[m]
        fp = None if footprint is None else footprint[m]
        dmod, dtilt, _lab = _defect_sample(obj, pm, fp)    # 傷は明るさと法線の両方を変える
        if np.any(dtilt):
            nm = _safe_unit(nm + dtilt)
        col = np.full(pm.shape, float(ambient))
        for light in lights:
            E, ldir, theta = _irradiance(scene, pm, nm, light, shadows, light_samples)
            if mat["kind"] == "lambert":
                # 倍率ではなく**掛けたあとのアルベド**を [0,1] に収める。倍率を 1 で
                # 切ると、しみや付着物のような明るい欠陥が構造的に作れなくなる
                # (2026-09-05 の実測: 明るいしみのコントラストが -0.2% しか出ず、
                #  良品と区別が付かなかった)
                alb = np.clip(mat["albedo"] * np.maximum(1.0 + dmod, 0.0)[..., None], 0.0, 1.0)
                col += (E / np.pi)[..., None] * alb
            elif mat["kind"] == "conductor":
                # 粗さによる**拡散散乱**の項。鏡像の項(下の _specular_fixtures)だけだと
                # 暗視野が原理的に真っ黒になる ―― 平らな鏡が低角の器具を映すには面が
                # 39 度傾く必要があり、加工目の数度では届かない。実際の暗視野が成立
                # するのは、微小な粗さが光を広い角度へ散らすからである(2026-09-05 の実測)。
                t, b = _tangent(nm, mat["finish"])
                ax = np.hypot(mat["alpha_x"], theta)
                ay = np.hypot(mat["alpha_y"], theta)
                lobe = _ward(nm, ldir, vm, t, b, ax, ay)
                cos_v = np.clip((nm * vm).sum(-1), 0.0, 1.0)
                diffuse = 1.0 - _specular_fraction(mat, cos_v, wavelength_nm)
                col += (E * lobe * diffuse)[..., None] * _gm.metal_mirror_rgb(mat["metal"], cos_v)
            else:
                cos_i = np.clip((nm * vm).sum(-1), 0.0, 1.0)
                R = np.asarray(_gm.fresnel_dielectric(cos_i, 1.0, float(mat["n_rgb"][1])), float)
                col += (E * R / np.pi)[..., None]               # 表面の映り込み(拡散近似)
        if mat["kind"] == "conductor":
            cos_v = np.clip((nm * vm).sum(-1), 0.0, 1.0)
            spec = _specular_fraction(mat, cos_v, wavelength_nm)
            col = col + spec[..., None] * _specular_fixtures(
                scene, pm, nm, vm, mat, lights, shadows)
        if mat["kind"] == "dielectric" and depth > 0:
            col += _refract_through(scene, obj, pm, nm, view[m], lights, ambient, depth, shadows)
        out[m] = col
    return out


def _refract_through(scene, obj, p, n, d, lights, ambient, depth, shadows):
    """誘電体の内部を通した光(RGB それぞれの屈折率で解くので、縁に分散の色が出る)。"""
    nrgb, sigma = obj["material"]["n_rgb"], obj["material"]["sigma_per_mm"]
    res = np.zeros(p.shape)
    for ch in range(3):
        nk = float(nrgb[ch])
        cos_i = np.clip(-(d * n).sum(-1), 0.0, 1.0)
        R = np.asarray(_gm.fresnel_dielectric(cos_i, 1.0, nk), float)
        din, tir = _gm.refract_rays(d, n, 1.0, nk)
        din = _safe_unit(np.where(tir[..., None], reflect_rays(d, n), din))
        t_exit = _hit(obj, p + 1e-4 * din, din, inside=True)
        t_exit = np.where(np.isfinite(t_exit), t_exit, 0.0)
        q = p + (t_exit + 1e-4)[..., None] * din
        nq = -_normal(obj, q)                                   # 内側から見た法線
        absorb = np.asarray(_gm.beer_lambert_transmittance(t_exit, sigma), float)
        dout, tir2 = _gm.refract_rays(din, nq, nk, 1.0)
        dout = _safe_unit(np.where(tir2[..., None], reflect_rays(din, nq), dout))
        far = trace_rays(scene, q + 1e-4 * dout, dout)
        beyond = _shade(scene, far, dout, lights, ambient, depth - 1, shadows)
        beyond = np.where((far["index"] < 0)[..., None], float(ambient), beyond)
        res[:, ch] = (1.0 - R) * absorb * beyond[:, ch]
    return res


# --------------------------------------------------------------------------- #
# 出力 op
# --------------------------------------------------------------------------- #
def _subpixel_rays(camera, rows, cols, factor):
    """指定画素を factor×factor に割った光線(原点, 方向)。適応的な精細化に使う。"""
    K = camera["K"]
    f = int(factor)
    off = (np.arange(f) + 0.5) / f - 0.5
    du, dv = np.meshgrid(off, off, indexing="xy")
    u = cols[:, None] + du.ravel()[None, :]
    v = rows[:, None] + dv.ravel()[None, :]
    cam = np.stack([(u - K[0, 2]) / K[0, 0], (v - K[1, 2]) / K[1, 1], np.ones_like(u)], -1)
    d = _safe_unit(cam.reshape(-1, 3) @ camera["R"])
    return np.broadcast_to(camera["eye"], d.shape).copy(), d, f * f


def _refine_mask(col, idx, threshold, saturate=None):
    """精細化すべき画素: 幾何の縁 or 輝度勾配が大きい。飽和が確定した画素は除く。"""
    lum = col.mean(-1)
    edge = np.zeros(lum.shape, bool)
    for a in (0, 1):                                       # 物体が変わる境目
        edge |= idx != np.roll(idx, 1, axis=a)
        edge |= idx != np.roll(idx, -1, axis=a)
    g = np.zeros(lum.shape)
    for a in (0, 1):
        g = np.maximum(g, np.abs(lum - np.roll(lum, 1, axis=a)))
        g = np.maximum(g, np.abs(lum - np.roll(lum, -1, axis=a)))
    scale = max(float(np.percentile(lum, 99)), 1e-30)
    need = edge | (g > threshold * scale)
    if saturate is not None:                               # どうせ白飛びする画素は捨てる
        need &= lum < saturate
    return need


def _supersampled(camera, factor):
    """画素を factor×factor に割ったカメラ(視野・姿勢は同じ、標本だけ細かい)。"""
    f = int(factor)
    K = camera["K"].copy()
    K[0, 0] *= f
    K[1, 1] *= f
    K[0, 2] = K[0, 2] * f + (f - 1) / 2.0
    K[1, 2] = K[1, 2] * f + (f - 1) / 2.0
    out = dict(camera)
    out.update(K=K, width=camera["width"] * f, height=camera["height"] * f,
               pixel_mm=camera["pixel_mm"] / f)
    return out


def _box_average(img, factor):
    """factor×factor の箱平均で元の画素数に戻す(= 画素が面積を積分する)。"""
    f = int(factor)
    h, w = img.shape[0] // f, img.shape[1] // f
    return img.reshape(h, f, w, f, -1).mean(axis=(1, 3))


def _env_metal_term(scene, hit, view, env, samples):
    """導体だけに環境の映り込みを足す(見せる絵の手法を検査用に混ぜる任意の項)。

    拡散面には足さない ―― 拡散面の明るさは実在の照明器具で決まっており、そこに
    環境項を混ぜると測光の根拠が濁る。金属は「何が映っているか」で見え方が決まる
    ので、ここだけは環境が要る。
    """
    p, n, idx = hit["point"], hit["normal"], hit["index"]
    out = np.zeros(p.shape[:1] + (3,))
    for k, obj in enumerate(scene):
        m = idx == k
        if not m.any() or obj["material"]["kind"] != "conductor":
            continue
        mat = obj["material"]
        pm, nm, dm = p[m], n[m], view[m]
        _mod, tilt, _lab = _defect_sample(obj, pm)
        if np.any(tilt):
            nm = _safe_unit(nm + tilt)
        out[m] = _studio_metal(scene, pm, nm, dm, mat, 1, int(samples), env)
    return out


def render_optscene(scene, camera, lights, ambient: float = 0.0,
                    depth: int = 2, shadows: bool = True,
                    supersample: int = 1, adaptive: bool = False,
                    light_samples: int = None, edge_threshold: float = 0.06,
                    saturate_at: float = None, wavelength_nm: float = 550.0,
                    environment=None,
                    environment_gain: float = 1.0,
                    environment_samples: int = 12) -> np.ndarray:
    """**検査用**に撮る: 実在の照明器具を物理単位で置き直接光を数える(真値つき)。

    見た目を作るための多重反射・環境光は入れない。きれいな絵が要るなら
    :func:`render_studio` ―― **作り方が違う別の op** で、取り違えると測光の
    根拠が濁る。返り値は線形 RGB の放射輝度 (H, W, 3)、トーンマップ前。

    ``lights`` は ``illumdesign.light_source`` の結果(1 つでも並べてもよい)。
    ``ambient`` は一様な環境光、``depth`` は誘電体を通す再帰の深さ、
    ``shadows=False`` で落ち影を切る(速いが、影がある前提の検査には使えない)。
    ``supersample`` は 1 画素あたりの標本を n×n に増やす ―― 実際の画素は面積を
    積分するので、縁や加工目の階段状のギザギザはこれで消える(コストは n² 倍)。

    大量生成のための 3 つのつまみ(**速度は生成器の機能**):
      * ``adaptive=True`` ―― まず 1 標本で撮り、**幾何の縁と輝度勾配が大きい画素だけ**
        を n×n に割る。平坦な面には標本を捨てないので、縁の質を保ったまま速くなる。
      * ``light_samples`` ―― 面光源の発光点をこの数へ間引く(重みで明るさを補正)。
        落ちるのは影の縁の柔らかさで、明るさの絶対値ではない。
      * ``saturate_at`` ―― この輝度を超える画素は精細化しない(どうせ白飛びする)。

    ``wavelength_nm`` は光源の波長。面粗さ σ の面が鏡面として返す割合
    exp(-(4πσcosθ/λ)²) に入るので、**同じ面でも波長で見え方が変わる**。
    広帯域(ハロゲン)なら数波長で撮って足す、レーザーなら単一波長で撮る。

    ``environment`` を渡すと、**見せる絵の作り方をここに混ぜられる**: 金属の異方性
    ローブで環境を引いた分を ``environment_gain`` 倍して足す。ブラシ目の金属が
    金属に見えるのは環境が目に沿って引き伸ばされて映るからで、点光源だけでは硬い
    縞にしかならない(2026-09-05 のユーザー着眼)。既定は off ―― 測光の根拠が要る
    検査画像に、見た目のための項を黙って混ぜないため。``optscene.env_studio`` を
    渡すのが手軽で、自前の関数((...,3) 方向 -> (...,) 明るさ)でもよい。

    表示用に丸めたい場合は自分で ``**(1/2.2)`` する。実レンズの歪曲・PSF・
    周辺光量・センサ雑音を足すには ``lensimage.render_through_lens`` を後段に、
    量子化と読み出し雑音だけなら ``sensor_capture`` を後段に掛ける。
    """
    scene = _check_scene(scene)
    lights = [lights] if isinstance(lights, dict) else list(lights)
    if not lights:
        raise ValueError("lights must contain at least one illumdesign.light_source() result")
    if int(depth) < 0:
        raise ValueError(f"depth must be >= 0, got {depth!r}")
    ss = int(supersample)
    if ss < 1:
        raise ValueError(f"supersample must be >= 1, got {supersample!r}")
    if ss > 1 and not adaptive:
        fine = render_optscene(scene, _supersampled(camera, ss), lights, ambient=ambient,
                               depth=depth, shadows=shadows, supersample=1,
                               light_samples=light_samples, wavelength_nm=wavelength_nm,
                               environment=environment,
                               environment_gain=environment_gain,
                               environment_samples=environment_samples)
        return _box_average(fine, ss)
    o, d = camera_rays(camera)
    hit = trace_rays(scene, o, d)
    # 画素が面上で覆う幅 [mm]。加工目の前置フィルタ(解像できない目を平坦にする)に使う
    fp = np.where(np.isfinite(hit["t"]), hit["t"], 0.0) * camera["pixel_mm"] / camera["focal_mm"]
    col = _shade(scene, hit, d, lights, float(ambient), int(depth), bool(shadows), fp,
                 light_samples, float(wavelength_nm))
    if environment is not None and float(environment_gain) != 0.0:
        col = col + float(environment_gain) * _env_metal_term(
            scene, hit, d, environment, int(environment_samples))
    bg = float(ambient) + _light_background(lights, o, d)     # 光源が直接写る分
    col = np.where((hit["index"] < 0)[..., None], bg[..., None], col)
    if ss > 1 and adaptive:
        H, W = camera["height"], camera["width"]
        img = col.reshape(H, W, 3)
        need = _refine_mask(img, hit["index"].reshape(H, W), float(edge_threshold),
                            saturate_at)
        rows, cols = np.nonzero(need)
        if len(rows):
            ro, rd, nsub = _subpixel_rays(camera, rows.astype(float), cols.astype(float), ss)
            rhit = trace_rays(scene, ro, rd)
            rfp = (np.where(np.isfinite(rhit["t"]), rhit["t"], 0.0)
                   * camera["pixel_mm"] / (camera["focal_mm"] * ss))
            rc = _shade(scene, rhit, rd, lights, float(ambient), int(depth), bool(shadows),
                        rfp, light_samples, float(wavelength_nm))
            if environment is not None and float(environment_gain) != 0.0:
                rc = rc + float(environment_gain) * _env_metal_term(
                    scene, rhit, rd, environment, int(environment_samples))
            rbg = float(ambient) + _light_background(lights, ro, rd)
            rc = np.where((rhit["index"] < 0)[..., None], rbg[..., None], rc)
            img[rows, cols] = rc.reshape(len(rows), nsub, 3).mean(1)
        col = img.reshape(-1, 3)
    if float(ambient) == 0.0 and float(col.max()) == 0.0:
        # 真っ黒を黙って返さない。ほぼ必ず配置の誤りで、画像として渡ると後段が
        # 「検出ゼロ = 頑健」と誤読する(バックライトを不透明ステージで塞いだ等)
        raise ValueError(
            "render_optscene produced an all-zero image: every light contributes nothing "
            "to every visible surface. Common causes: a backlight (emitters below z=0) "
            "blocked by an opaque scene_plane, lights aimed away from the parts, or the "
            "parts lying outside the camera field of view "
            f"({camera['fov_mm'][0]:.2f} x {camera['fov_mm'][1]:.2f} mm at the working "
            "distance). Pass ambient>0 if a dark frame is genuinely intended.")
    return col.reshape(camera["height"], camera["width"], 3)


def optscene_depth(scene, camera, supersample: int = 1) -> np.ndarray:
    """深度の**真値** (H, W) [mm]。**光軸方向の z** であって視点からの斜距離ではない。

    深度カメラ・ステレオ・光切断が返すのはどれも光軸方向の z なので、それに合わせる
    (斜距離と混ぜると、視野の端ほど系統的にずれた真値で採点することになり、
    しかも中心では一致するので気づけない)。生の光線距離が要るなら
    trace_rays(...)["t"] を使う。

    当たらない画素は NaN。0 で埋めない ―― 「距離 0 の面」と区別できなくなる。
    """
    ss = int(supersample)
    if ss > 1:                                      # 真値も画像と同じ細かさで取れるように
        fine = optscene_depth(scene, _supersampled(camera, ss))
        return _box_average(fine[..., None], ss)[..., 0]
    o, d = camera_rays(camera)
    hit = trace_rays(scene, o, d)
    z = hit["t"] * (d @ camera["forward"])          # 斜距離 → 光軸成分
    return np.where(hit["index"] >= 0, z, np.nan).reshape(camera["height"], camera["width"])


def optscene_mask(scene, camera, index: int) -> np.ndarray:
    """``index`` 番のプリミティブが見えている画素の**真値マスク** (H, W) の bool。

    画素完全(アンチエイリアスしない)。検出結果との IoU をそのまま測れる。
    """
    scene = _check_scene(scene)
    i = int(index)
    if not (0 <= i < len(scene)):
        raise ValueError(f"index must be in [0, {len(scene)}), got {index!r}")
    o, d = camera_rays(camera)
    hit = trace_rays(scene, o, d)
    return (hit["index"] == i).reshape(camera["height"], camera["width"])


def optscene_defect_mask(scene, camera, index: int = None) -> np.ndarray:
    """**欠陥画素の真値マスク** (H, W)。学習・評価のラベルはこれを使う。

    ``index`` を省くとシーン中のすべての欠陥を合成する。画素完全で、レンダリングと
    同じ交差計算から出るので、検出結果との IoU をそのまま測れる。欠陥が
    **その照明で見えるかどうかとは無関係**に真値を返す ―― 見えないのに正解が
    あるのが外観検査の難しさで、そこを隠すと「検出ゼロ = 頑健」と誤読される。
    """
    scene = _check_scene(scene)
    o, d = camera_rays(camera)
    hit = trace_rays(scene, o, d)
    out = np.zeros(hit["index"].shape, bool)
    targets = range(len(scene)) if index is None else [int(index)]
    for k in targets:
        if not (0 <= k < len(scene)):
            raise ValueError(f"index must be in [0, {len(scene)}), got {index!r}")
        m = hit["index"] == k
        if not m.any():
            continue
        if scene[k].get("is_defect"):       # 異物は物体まるごとが欠陥
            out[m] = True
        elif scene[k].get("defect") is not None:
            _mod, _tilt, lab = _defect_sample(scene[k], hit["point"][m])
            out[m] = lab
    return out.reshape(camera["height"], camera["width"])


def inspection_dataset(scene, camera, lights, n: int = 8, seed: int = 0,
                       exposure_ms: float = 10.0, bit_depth: int = 8,
                       jitter_mm: float = 0.0, tilt_jitter_deg: float = 0.0,
                       intensity_jitter: float = 0.0, depth: int = 1,
                       defects: dict = None, supersample: int = 1,
                       adaptive: bool = False, light_samples: int = None,
                       environment=None, environment_gain: float = 1.0) -> list:
    """外観検査 AI の**学習画像を n 枚**、画素完全なラベル付きで生成する(検査用)。

    同じ部品を、照明(``lights`` に複数渡すと 1 枚ごとに巡回)・置き方
    (``jitter_mm`` の並進、``tilt_jitter_deg`` のカメラ傾き)・明るさ
    (``intensity_jitter`` の相対ゆらぎ)を振って撮る = ドメインランダム化。

    返り値は 1 枚あたり dict:
      ``image`` 量子化済み (H, W, 3) / ``defect_mask`` 欠陥の真値 /
      ``part_mask`` 部品の真値 / ``depth_mm`` 深度の真値 /
      ``meta`` 使った照明種別・露光・ゆらぎ量・欠陥ラベル(再現に必要な値をすべて)。

    ``defects`` に :func:`random_defects` の引数 dict を渡すと、**1 枚ごとに
    欠陥を引き直す**(``scene`` の先頭を対象にする)。これが外観検査 AI の学習
    データ生成そのもので、欠陥の種類・位置・大きさ・深さと照明が同時に振れる。

    ``seed`` を固定すれば決定的。**同じ欠陥でも照明を変えると見え方が変わる**
    ことがこの生成器の要点で、だから照明を振った枚数が効く。
    """
    scene = _check_scene(scene)
    lights = [lights] if isinstance(lights, dict) else list(lights)
    if not lights:
        raise ValueError("lights must contain at least one illumdesign.light_source() result")
    if int(n) < 1:
        raise ValueError(f"n must be >= 1, got {n!r}")
    rng = np.random.default_rng(int(seed))
    out = []
    px = int(camera["width"]) * int(camera["height"])
    for i in range(int(n)):
        t_start = time.perf_counter()
        light = dict(lights[i % len(lights)])
        gain = 1.0 + float(intensity_jitter) * float(rng.uniform(-1.0, 1.0))
        light["intensity"] = float(light.get("intensity", 1.0)) * gain
        shift = rng.uniform(-1.0, 1.0, 3) * float(jitter_mm)
        shift[2] = 0.0                                    # 部品は台の上を滑る(浮かない)
        labels = []
        base = scene
        if defects is not None:
            kw = dict(defects)
            kw["seed"] = int(rng.integers(0, 2 ** 31))
            made = random_defects(scene[0], **kw)
            base = [made["part"]] + made["objects"] + list(scene[1:])
            labels = made["labels"]
        moved = [_translate(obj, shift) for obj in base]
        cam = camera
        if float(tilt_jitter_deg) > 0.0:
            cam = optical_camera(
                focal_mm=camera["focal_mm"], pixel_um=camera["pixel_mm"] * 1e3,
                resolution=(camera["width"], camera["height"]),
                working_distance_mm=camera["working_distance_mm"],
                tilt_deg=float(rng.uniform(0.0, float(tilt_jitter_deg))),
                azimuth_deg=float(rng.uniform(0.0, 360.0)))
        rad = render_optscene(moved, cam, [light], depth=depth, supersample=supersample,
                              adaptive=adaptive, light_samples=light_samples,
                              environment=environment, environment_gain=environment_gain)
        t_render = time.perf_counter()
        out.append({
            "image": sensor_capture(rad, exposure_ms=exposure_ms, bit_depth=bit_depth,
                                    seed=int(rng.integers(0, 2 ** 31))),
            "defect_mask": optscene_defect_mask(moved, cam),
            "part_mask": optscene_mask(moved, cam, 0),
            "depth_mm": optscene_depth(moved, cam),
            "meta": {"light": light.get("kind", "?"), "intensity": gain,
                     "shift_mm": shift.tolist(), "exposure_ms": float(exposure_ms),
                     "defects": labels},
        })
        t_end = time.perf_counter()
        # 大量生成が通常運用なので、1 枚あたりの実測を残す(枚数を見積もる材料)。
        # render = 光線を飛ばす時間、labels = 真値 3 枚(深度・部品・欠陥)の時間。
        out[-1]["meta"].update(
            seconds=t_end - t_start,
            seconds_render=t_render - t_start,
            seconds_labels=t_end - t_render,
            pixels=px,
            pixels_per_second=px / max(t_end - t_start, 1e-12))
    return out


def dataset_throughput(dataset) -> dict:
    """:func:`inspection_dataset` の結果 → 生成スループットの実測まとめ。

    大量生成が通常運用なので、「この設定で 1 万枚に何時間かかるか」を見積もれる形で
    返す。返り値 dict: ``images`` / ``seconds_total`` / ``seconds_per_image`` /
    ``images_per_hour`` / ``pixels_per_second`` / ``render_fraction``(光線を飛ばす
    時間の割合。真値 3 枚のぶんが残り)。

    実測を持たない dict を渡したら fail-closed で落とす ―― 推定値を混ぜると
    「速い」の根拠が消える。
    """
    rows = list(dataset)
    if not rows:
        raise ValueError("dataset is empty; nothing to measure")
    try:
        sec = np.array([float(r["meta"]["seconds"]) for r in rows])
        ren = np.array([float(r["meta"]["seconds_render"]) for r in rows])
        px = np.array([float(r["meta"]["pixels"]) for r in rows])
    except (KeyError, TypeError) as e:
        raise ValueError("dataset rows must come from inspection_dataset (they carry the "
                         "measured timings in meta); got a row without %s" % e) from None
    total = float(sec.sum())
    return {"images": len(rows), "seconds_total": total,
            "seconds_per_image": total / len(rows),
            "images_per_hour": 3600.0 * len(rows) / max(total, 1e-12),
            "pixels_per_second": float(px.sum()) / max(total, 1e-12),
            "render_fraction": float(ren.sum()) / max(total, 1e-12)}


def _translate(obj, shift):
    """プリミティブを平行移動した写しを返す(元は書き換えない)。"""
    o = dict(obj)
    if o["kind"] == "difference":
        o["a"], o["b"] = _translate(o["a"], shift), _translate(o["b"], shift)
    elif o["kind"] == "plane":
        pass                                              # 無限平面は動かしても同じ
    else:
        o["c"] = o["c"] + shift
    return o


# --------------------------------------------------------------------------- #
# ランダム欠陥(外観検査 AI の学習データ)
# --------------------------------------------------------------------------- #
#: 表面の欠陥(傷・打痕・しみ)は面の変調として貼り、**異物は別の物体として置く**。
#: 同じ「欠陥」でも光の扱いが根本的に違うからで、異物は影を落とし部品を隠すが、
#: 傷は隠さない。1 つの型に混ぜると、影の出ない異物という嘘の学習データができる。
_SURFACE_KINDS = ("scratch", "crack", "pits", "blob", "stain")
_ALL_KINDS = _SURFACE_KINDS + ("foreign",)


def _defect_pattern(kind, shape, rng):
    """defectgen の 1 件を引き、(明るさ変調, 高さ, マスク, 寸法 [px]) にして返す。"""
    import defectgen as _dg
    h, w = shape
    seed = int(rng.integers(0, 2 ** 31))
    cx = float(rng.uniform(0.25, 0.75)) * w
    cy = float(rng.uniform(0.25, 0.75)) * h
    if kind == "scratch":
        size = float(rng.uniform(0.25, 0.6)) * w
        img, m = _dg.defect_scratch(shape, length_px=size, width_px=float(rng.uniform(1.5, 4.0)),
                                    angle_deg=float(rng.uniform(0, 180)),
                                    contrast=-float(rng.uniform(0.05, 0.35)), seed=seed,
                                    start=(cy, cx))
    elif kind == "crack":
        size = float(rng.uniform(0.2, 0.5)) * w
        img, m = _dg.defect_crack(shape, length_px=size, width_px=float(rng.uniform(1.0, 2.5)),
                                  angle_deg=float(rng.uniform(0, 180)),
                                  contrast=-float(rng.uniform(0.15, 0.45)), seed=seed)
    elif kind == "pits":
        size = float(rng.uniform(2.0, 6.0))
        img, m = _dg.defect_pits(shape, count=int(rng.integers(6, 40)), radius_px=size,
                                 contrast=-float(rng.uniform(0.1, 0.4)),
                                 clustering=float(rng.uniform(0.0, 0.8)), seed=seed)
    else:                                                   # blob / stain(汚れは浅い blob)
        size = float(rng.uniform(0.06, 0.18)) * w
        img, m = _dg.defect_blob(shape, radius_px=size, roughness=float(rng.uniform(0.2, 0.6)),
                                 contrast=(float(rng.uniform(0.08, 0.3)) if kind == "stain"
                                           else -float(rng.uniform(0.1, 0.35))),
                                 seed=seed, centre=(cy, cx))
    base = float(np.median(img))
    mod = img / base - 1.0 if base > 0.0 else img - np.mean(img)
    return mod, mod.copy(), np.asarray(m, bool), size


def _top_of(primitive):
    """部品の「上面」の高さと半径(異物を載せる場所)。載せられない形は None。"""
    k = primitive["kind"]
    if k == "cylinder":
        return float(primitive["c"][2] + primitive["hz"]), float(primitive["r"]), primitive["c"][:2]
    if k == "box":
        return (float(primitive["c"][2] + primitive["h"][2]),
                float(min(primitive["h"][0], primitive["h"][1])), primitive["c"][:2])
    if k == "plane":
        return float(primitive["z"]), None, np.zeros(2)
    return None


def random_defects(primitive: dict, count: int = 2, kinds=_ALL_KINDS, seed: int = 0,
                   uv_size_mm=(20.0, 20.0), height_um=(5.0, 40.0),
                   albedo_defects: bool = True, shape=(192, 192)) -> dict:
    """部品に**ランダムな欠陥**を作る(傷・割れ・ピット・しみ・打痕・異物)。

    外観検査 AI の学習データはこれが本体。1 回の呼び出しで ``count`` 件を引き、
    種類・位置・向き・大きさ・コントラスト・深さをすべて振る。``seed`` を固定すれば
    決定的なので、同じデータセットを再現できる。

    ``kinds`` から選ぶ。表面の欠陥(scratch/crack/pits/blob/stain)は面の変調として
    貼られ、**foreign(異物)は部品の上に置かれた別の物体**になる ―― 異物は影を
    落として部品を隠すが傷は隠さない、という違いを型で分けている。

    ``height_um`` は (最小, 最大) の深さ [µm]。``albedo_defects=False`` にすると
    **色は一切変えず凹凸だけ**の欠陥になり、ドーム照明では消えて暗視野で立つ
    (=照明を選ぶ意味が出る、いちばん難しい学習データ)。

    返り値 dict: ``part``(欠陥を貼った部品)/ ``objects``(異物のプリミティブ、
    シーンにそのまま足す)/ ``labels``(1 件ごとの種類・位置 [mm]・大きさ)。
    """
    for k in kinds:
        if k not in _ALL_KINDS:
            raise ValueError(f"kinds must be a subset of {_ALL_KINDS}, got {k!r}")
    if int(count) < 0:
        raise ValueError(f"count must be >= 0, got {count!r}")
    uv = _arr(uv_size_mm, "uv_size_mm", 2)
    lo, hi = (float(height_um[0]), float(height_um[1])) if np.ndim(height_um) else \
        (float(height_um), float(height_um))
    if not (0.0 <= lo <= hi):
        raise ValueError(f"height_um must be an increasing pair of non-negative values, "
                         f"got {height_um!r}")
    rng = np.random.default_rng(int(seed))
    H, W = int(shape[0]), int(shape[1])
    field = np.zeros((H, W))
    height = np.zeros((H, W))
    mask = np.zeros((H, W), bool)
    labels, objects = [], []
    top = _top_of(primitive)

    for _ in range(int(count)):
        kind = str(rng.choice(list(kinds)))
        if kind == "foreign":
            if top is None:
                raise ValueError("foreign objects can only be placed on a plane/box/cylinder "
                                 "top face; drop 'foreign' from kinds for this shape")
            z, rad, centre = top
            r = float(rng.uniform(0.15, 0.6))                # 異物の半径 [mm]
            lim = (rad - r) if rad is not None else float(uv[0]) * 0.5
            ang, rho = float(rng.uniform(0, 2 * np.pi)), float(np.sqrt(rng.random())) * max(lim, 0.0)
            pos = np.array([centre[0] + rho * np.cos(ang), centre[1] + rho * np.sin(ang), z + r])
            fo = scene_sphere(pos, r, scene_material("lambert", float(rng.uniform(0.05, 0.9))))
            fo["is_defect"] = True          # 異物そのものが欠陥。真値マスクに入れる
            objects.append(fo)
            labels.append({"kind": "foreign", "position_mm": pos.tolist(),
                           "size_mm": 2.0 * r, "height_um": r * 2e3})
            continue
        mod, hgt, m, size_px = _defect_pattern(kind, (H, W), rng)
        depth = float(rng.uniform(lo, hi))
        field = field + (mod if albedo_defects else 0.0)
        # 高さは **µm のまま**足す。ここで hi で割ると surface_defect 側の
        # height_um と二重に効いて深さが 1000 分の 1 になる(2026-09-05 に実測で発覚:
        # 凹凸だけの欠陥が暗視野でも -0.5% しか出ず「欠陥が無い」ように見えていた)
        height = height + hgt * depth
        mask |= m
        ys, xs = np.nonzero(m)
        cu = (xs.mean() / W - 0.5) * float(uv[0]) if len(xs) else 0.0
        cv = (ys.mean() / H - 0.5) * float(uv[1]) if len(ys) else 0.0
        labels.append({"kind": kind, "position_mm": [float(cu), float(cv)],
                       "size_mm": float(size_px / W * uv[0]), "height_um": depth})

    # height は µm の実寸なので、surface_defect には 1 µm 単位で渡す
    part = surface_defect(primitive, field, mask, uv_size_mm=uv,
                          height_um=1.0, height_field=height)
    return {"part": part, "objects": objects, "labels": labels}


# --------------------------------------------------------------------------- #
# 見せる絵(検査用とは作り方が違うので別の op にしてある)
# --------------------------------------------------------------------------- #
#: 検査用 ``render_optscene`` は「実在の照明器具を物理単位で置き、直接光を数え、
#: 真値を返す」。こちらは「環境全体から光が来て、金属は環境を映し、ガラスは
#: 環境を屈折させる」。同じシーンを食うが目的が違う -- 検査の絵に多重反射を
#: 混ぜると測光の根拠が濁り、見せる絵に点光源だけを使うと金属が真っ黒になる
#: (2026-09-05 の実測: 鏡面ローブのピークが 1.07e-96)。
def _smoothstep_box(a, c, half, soft):
    t = np.clip((half + soft - np.abs(a - c)) / max(soft, 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def env_studio(directions, key: float = 12.0, fill: float = 3.2,
               horizon: float = 0.45, sky: float = 0.14, ground: float = 0.05):
    """スタジオ環境の放射輝度(方向 -> 明るさ)。**無彩色**。

    ソフトボックス 2 枚 + 天空の勾配 + 細い水平の帯。色を付けないのは、金属の色が
    環境ではなく **Fresnel(n, k) から出ている**ことを絵の中で保証するため。
    ``directions`` は (..., 3) の単位ベクトル(z 上向き)。返り値はその形の (...,)。
    """
    d = _safe_unit(_arr(directions, "directions", 3))
    up = np.clip(d[..., 2], -1.0, 1.0)
    az = np.arctan2(d[..., 0], d[..., 1])
    el = np.arcsin(up)
    e = float(ground) + float(sky) * np.clip(up, 0.0, 1.0) ** 1.5
    e = e + float(key) * _smoothstep_box(az, -0.85, 0.34, 0.22) * _smoothstep_box(el, 0.66, 0.22, 0.20)
    e = e + float(fill) * _smoothstep_box(az, 1.30, 0.18, 0.18) * _smoothstep_box(el, 0.26, 0.40, 0.18)
    e = e + float(horizon) * _smoothstep_box(el, 0.015, 0.012, 0.035)
    return e


def env_lightbox(directions, base: float = 0.45, key: float = 4.0,
                 elevation: float = 0.85, width: float = 0.55,
                 azimuth_width: float = 1.1, floor: float = 0.25):
    """撮影ボックスの環境(広い天井の明かり + ほんのり明るい周囲)。**無彩色**。

    :func:`env_studio` が「劇的に見せる」ための暗い部屋 + 小さいソフトボックス 2 灯
    なのに対し、こちらは**加工面が加工面に見える**ための環境。2026-09-05 の実測で
    分かった 2 つの条件を満たすように作ってある:

      * 周囲が明るいこと ―― 暗い環境だとアルミが真っ黒になる(反射率 ~0.9 の金属が
        黒く写るのは、映るものが黒いから)。
      * それでも**勾配があること** ―― 完全に一様な環境では、どんな異方性ローブでも
        同じ値を返すので加工目が消える。ブラシ目が見えるのは、目が環境の明暗を
        目方向に引き伸ばすからである。

    加工目は**斜めから見ないと出ない**(真上から見た平面は反射方向が全画素で天頂に
    集中し、環境の勾配を掃かない)。``optical_camera(tilt_deg=50〜70)`` 程度が目安。
    """
    d = _safe_unit(_arr(directions, "directions", 3))
    up = np.clip(d[..., 2], -1.0, 1.0)
    az = np.arctan2(d[..., 0], d[..., 1])
    el = np.arcsin(up)
    t = np.clip((float(width) - np.abs(el - float(elevation))) / max(float(width) * 0.6, 1e-9),
                0.0, 1.0)
    t = t * t * (3.0 - 2.0 * t)
    a = np.clip((float(azimuth_width) - np.abs(az)) / max(float(azimuth_width), 1e-9), 0.0, 1.0)
    return float(base) + float(key) * t * (0.3 + 0.7 * a) + float(floor) * np.clip(-up, 0.0, 1.0)


def _lowdiscrepancy_gauss(n, seed=7):
    """低食い違い列 -> 標準正規。全画素で同じ位置を使うので粒状ノイズが出ない。"""
    i = np.arange(n) + 0.5
    rev = np.array([int(format(k, "022b")[::-1], 2) for k in range(n)]) / 2.0 ** 22
    u2 = (rev + np.random.default_rng(seed).random()) % 1.0
    r = np.sqrt(-2.0 * np.log(np.clip(i / n, 1e-12, 1.0)))
    return r * np.cos(2 * np.pi * u2), r * np.sin(2 * np.pi * u2)


def _studio(scene, o, d, depth, samples, env):
    hit = trace_rays(scene, o, d)
    col = np.repeat(np.asarray(env(d), float)[..., None], 3, -1)
    for k, obj in enumerate(scene):
        m = hit["index"] == k
        if not m.any():
            continue
        p, n, di = hit["point"][m], hit["normal"][m], d[m]
        mat = obj["material"]
        dmod, dtilt, _lab = _defect_sample(obj, p)
        if np.any(dtilt):
            n = _safe_unit(n + dtilt)
        if mat["kind"] == "conductor":
            col[m] = _studio_metal(scene, p, n, di, mat, depth, samples, env)
        elif mat["kind"] == "dielectric":
            col[m] = _studio_glass(scene, obj, p, n, di, mat, depth, samples, env)
        else:
            col[m] = _studio_lambert(scene, p, n, mat, dmod, samples, env)
    return col


def _studio_lambert(scene, p, n, mat, dmod, samples, env):
    """余弦重みで環境を積分し、遮蔽を数える(= 環境遮蔽つきの拡散)。"""
    t, b = _tangent(n, "random")
    gx, gy = _lowdiscrepancy_gauss(max(int(samples), 4), seed=11)
    acc = np.zeros(p.shape[:1])
    for a, bb in zip(gx, gy):
        w = _safe_unit(n + 0.75 * (a * t + bb * b))            # 半球のおおよそ余弦分布
        blocked = np.zeros(p.shape[:1], bool)
        for obj in scene:
            blocked |= np.isfinite(_hit(obj, p + 1e-4 * w, w))
        acc += np.where(blocked, 0.0, np.asarray(env(w), float))
    acc /= len(gx)
    return acc[..., None] * mat["albedo"] * np.clip(1.0 + dmod, 0.0, 1.0)[..., None]


def _studio_metal(scene, p, n, d, mat, depth, samples, env):
    """異方性ローブで環境とシーンを映す。色は metal_mirror_rgb(= Fresnel(n,k))だけ。"""
    t, b = _tangent(n, mat["finish"])
    refl = reflect_rays(d, n)
    ns = max(int(samples), 1) if depth >= 2 else 1
    gx, gy = _lowdiscrepancy_gauss(ns, seed=7)
    acc = np.zeros(p.shape[:1] + (3,))
    for a, bb in zip(gx, gy):
        rd = _safe_unit(refl + (mat["alpha_x"] * a) * t + (mat["alpha_y"] * bb) * b)
        acc += (np.repeat(np.asarray(env(rd), float)[..., None], 3, -1) if depth <= 1
                else _studio(scene, p + 1e-4 * n, rd, depth - 1, max(int(samples) // 4, 1), env))
    acc /= ns
    cos_v = np.clip(-(d * n).sum(-1), 0.0, 1.0)
    return acc * _gm.metal_mirror_rgb(mat["metal"], cos_v)


def _studio_glass(scene, obj, p, n, d, mat, depth, samples, env):
    """入射 Fresnel + 屈折 2 回 + Beer-Lambert。RGB それぞれの屈折率で解く(縁に分散)。"""
    cos_i = np.clip(-(d * n).sum(-1), 0.0, 1.0)
    rd = reflect_rays(d, n)
    refl = (np.repeat(np.asarray(env(rd), float)[..., None], 3, -1) if depth <= 1
            else _studio(scene, p + 1e-4 * n, rd, depth - 1, max(int(samples) // 4, 1), env))
    out = np.zeros(p.shape[:1] + (3,))
    for ch in range(3):
        nk = float(mat["n_rgb"][ch])
        R = np.asarray(_gm.fresnel_dielectric(cos_i, 1.0, nk), float)
        din, tir = _gm.refract_rays(d, n, 1.0, nk)
        din = _safe_unit(np.where(tir[..., None], rd, din))
        t_exit = _hit(obj, p + 1e-4 * din, din, inside=True)
        t_exit = np.where(np.isfinite(t_exit), t_exit, 0.0)
        q = p + (t_exit + 1e-4)[..., None] * din
        nq = -_normal(obj, q)
        absorb = np.asarray(_gm.beer_lambert_transmittance(t_exit, mat["sigma_per_mm"]), float)
        dout, tir2 = _gm.refract_rays(din, nq, nk, 1.0)
        dout = _safe_unit(np.where(tir2[..., None], reflect_rays(din, nq), dout))
        beyond = (np.asarray(env(dout), float) if depth <= 1
                  else _studio(scene, q + 1e-4 * dout, dout, depth - 1,
                               max(int(samples) // 4, 1), env)[:, ch])
        out[:, ch] = R * refl[:, ch] + (1.0 - R) * absorb * beyond
    return out


def render_studio(scene, camera, depth: int = 3, samples: int = 16,
                  environment=None, supersample: int = 1) -> np.ndarray:
    """**見せる絵**を描く: 環境光・多重反射・屈折と分散つき(測光の真値は無い)。

    検査データが要るなら :func:`render_optscene` ―― **作り方が違う別の op**。
    返り値は (H, W, 3) の線形 RGB。

    検査用の :func:`render_optscene` と目的が違う。あちらは実在の照明器具を物理単位で
    置いて直接光を数え、真値を返す(測光の根拠が要る)。こちらは環境全体から光が来る
    前提で、金属は環境を映し、ガラスは環境を屈折させ、互いも映り込む(見た目が要る)。

    ``depth`` は反射・屈折の再帰段数、``samples`` は粗さローブの標本数(増やすほど
    滑らか・遅い)。``environment`` に自前の関数((...,3) 方向 -> (...,) 明るさ)を
    渡せば別の環境にできる。表示するにはガンマを自分で掛ける。
    """
    scene = _check_scene(scene)
    if int(depth) < 1:
        raise ValueError(f"depth must be >= 1, got {depth!r}")
    if int(samples) < 1:
        raise ValueError(f"samples must be >= 1, got {samples!r}")
    ss = int(supersample)
    if ss < 1:
        raise ValueError(f"supersample must be >= 1, got {supersample!r}")
    if ss > 1:                                     # 画素は面積を積分する(縁が階段にならない)
        fine = render_studio(scene, _supersampled(camera, ss), depth=depth,
                             samples=samples, environment=environment, supersample=1)
        return _box_average(fine, ss)
    env = env_studio if environment is None else environment
    o, d = camera_rays(camera)
    col = _studio(scene, o, d, int(depth), int(samples), env)
    return col.reshape(camera["height"], camera["width"], 3)


def defocus_blur(image, depth_mm, camera, f_number: float = 5.6,
                   focus_mm: float = None, layers: int = 7) -> np.ndarray:
    """深度の真値から**被写界深度のぼけ**を掛ける(理想ピンホール像 -> 実レンズの像)。

    名前が optics.depth_of_field と紛らわしいので分けてある: あちらは被写界深度の
    **数値**を返し、こちらは**画像にぼけを掛ける**(2026-09-05 に台帳で同名衝突を
    起こして発覚。同名 op は後勝ちで静かに上書きされるので、名前で区別する)。

    錯乱円の直径は幾何光学の閉じた式
    ``c = (f² / (N (z_f − f))) · |z − z_f| / z``(f = 焦点距離, N = F 値, z_f = 合焦距離)。
    画素数に直して、深度でまとめた層ごとにガウスぼかしを掛け、手前の層から合成する。

    これが無いと「視野には入っているのに実機では合焦しない」構成を見逃す ――
    仮想化の目的は絵を作ることではなく、**その光学構成で検査が成立するか**を
    先に知ることなので、被写界深度は省けない。

    ``focus_mm`` を省くと ``camera`` の作動距離に合わせる。返り値は入力と同じ形。
    """
    img = np.asarray(image, dtype=np.float64)
    z = np.asarray(depth_mm, dtype=np.float64)
    if img.shape[:2] != z.shape:
        raise ValueError(f"image {img.shape[:2]} and depth_mm {z.shape} must have the "
                         "same height and width")
    N = _pos(f_number, "f_number")
    f = float(camera["focal_mm"])
    zf = float(camera["working_distance_mm"] if focus_mm is None else focus_mm)
    if zf <= f:
        raise ValueError(f"focus distance {zf} mm must exceed the focal length {f} mm")
    nl = int(layers)
    if nl < 1:
        raise ValueError(f"layers must be >= 1, got {layers!r}")
    finite = np.isfinite(z)
    if not finite.any():
        return img.copy()
    zz = np.where(finite, z, zf)
    coc_mm = (f * f / (N * (zf - f))) * np.abs(zz - zf) / np.maximum(zz, 1e-9)
    coc_px = coc_mm / camera["pixel_mm"]                  # 錯乱円の直径 [px]

    flat = img if img.ndim == 3 else img[..., None]
    edges = np.linspace(zz.min(), zz.max(), nl + 1)
    out = np.zeros_like(flat)
    wsum = np.zeros(flat.shape[:2] + (1,))
    for i in range(nl):
        sel = (zz >= edges[i]) & (zz <= edges[i + 1])
        if not sel.any():
            continue
        sigma = float(np.median(coc_px[sel])) / 2.0       # 直径 -> 標準偏差の目安
        layer = flat * sel[..., None]
        w = sel.astype(np.float64)[..., None]
        if sigma > 0.3:
            layer = _gauss_blur(layer, sigma)
            w = _gauss_blur(w, sigma)
        out += layer
        wsum += w
    return (out / np.maximum(wsum, 1e-12)).reshape(img.shape)


def _gauss_blur(a, sigma):
    """分離可能ガウスぼかし(依存を増やさないので自前。端は反射で埋める)。"""
    r = max(int(3.0 * sigma), 1)
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= k.sum()
    out = a
    for axis in (0, 1):
        pad = [(0, 0)] * a.ndim
        pad[axis] = (r, r)
        p = np.pad(out, pad, mode="reflect")
        acc = np.zeros_like(out)
        for j, w in enumerate(k):
            sl = [slice(None)] * a.ndim
            sl[axis] = slice(j, j + out.shape[axis])
            acc += w * p[tuple(sl)]
        out = acc
    return out


def airy_radius_um(f_number: float = 5.6, wavelength_nm: float = 550.0) -> float:
    """エアリーディスクの第 1 暗環までの半径 [µm] = 1.22 · λ · N(閉じた式)。

    微細な欠陥が「写るか」を決めるのは画素数ではなく、この回折の広がりと画素ピッチの
    どちらが大きいか。F5.6・550 nm なら 3.76 µm で、3.45 µm 画素とほぼ同じ ――
    つまりそこから先は絞っても分解能は上がらない。
    """
    N = _pos(f_number, "f_number")
    lam = _pos(wavelength_nm, "wavelength_nm") * 1e-3            # nm -> µm
    return 1.22 * lam * N


def diffraction_blur(image, camera, f_number: float = 5.6,
                     wavelength_nm: float = 550.0) -> np.ndarray:
    """開口で決まる**回折ぼけ**を掛ける(エアリーディスクをガウスで近似)。

    幾何光学だけで作った像は、実機より細部が出すぎる。絞るほど被写界深度は深くなるが
    回折で細部は潰れる ―― この綱引きを見ずに絞りを決めると、シミュレーション上は
    見えていた欠陥が実機で消える。

    エアリーパターンを、第 1 暗環の半径 1.22λN に合わせた等価ガウス
    (σ ≈ 0.42 · 1.22λN)で近似する。厳密な PSF が要るなら
    ``lensimage.psf_from_opd``(実収差瞳の回折 PSF)を使う。
    """
    img = np.asarray(image, dtype=np.float64)
    r_um = airy_radius_um(f_number, wavelength_nm)
    sigma_px = 0.42 * r_um * 1e-3 / camera["pixel_mm"]
    if sigma_px < 0.3:                                   # 画素より十分小さければ何もしない
        return img.copy()
    flat = img if img.ndim == 3 else img[..., None]
    return _gauss_blur(flat, sigma_px).reshape(img.shape)


def optscene_instances(scene, camera, min_area_px: int = 1) -> list:
    """欠陥を**個体ごと**に返す(クラス・画素マスク・bounding box・面積)。

    1 枚の合成マスクだけでは個体を分けられず、検出や計数の学習には使えない。
    連結成分で分け、``min_area_px`` 未満は落とす(1 画素の粒までは数えない)。

    返り値は 1 個体あたり dict: ``kind``(クラス)/ ``mask``(H, W の bool)/
    ``bbox``(x0, y0, x1, y1 の画素座標、右下は含む)/ ``area_px`` / ``source``
    (surface = 面に貼った欠陥 / object = 置かれた異物)。
    """
    scene = _check_scene(scene)
    o, d = camera_rays(camera)
    hit = trace_rays(scene, o, d)
    H, W = camera["height"], camera["width"]
    idx = hit["index"].reshape(H, W)
    out = []
    for k, obj in enumerate(scene):
        m = idx == k
        if not m.any():
            continue
        if obj.get("is_defect"):                          # 異物は物体まるごとが 1 個体
            out.extend(_components(m, obj.get("defect_kind", "foreign"), "object",
                                   int(min_area_px)))
        elif obj.get("defect") is not None:
            flat = np.zeros(H * W, bool)
            sel = hit["index"] == k
            _mod, _tilt, lab = _defect_sample(obj, hit["point"][sel])
            flat[np.nonzero(sel)[0]] = lab
            out.extend(_components(flat.reshape(H, W), "surface_defect", "surface",
                                   int(min_area_px)))
    return out


def _components(mask, kind, source, min_area):
    """4 近傍の連結成分。scipy を要求しないので自前(生成側で依存を増やさない)。"""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    cur = 0
    ys, xs = np.nonzero(mask)
    out = []
    for y0, x0 in zip(ys, xs):
        if lab[y0, x0]:
            continue
        cur += 1
        stack = [(y0, x0)]
        lab[y0, x0] = cur
        pix = []
        while stack:
            y, x = stack.pop()
            pix.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = cur
                    stack.append((ny, nx))
        if len(pix) < min_area:
            continue
        p = np.array(pix)
        m = np.zeros((h, w), bool)
        m[p[:, 0], p[:, 1]] = True
        out.append({"kind": kind, "source": source, "mask": m, "area_px": len(pix),
                    "bbox": (int(p[:, 1].min()), int(p[:, 0].min()),
                             int(p[:, 1].max()), int(p[:, 0].max()))})
    return out


# --------------------------------------------------------------------------- #
# 観察光学系の 4 オブジェクト(sensor / lens / light / layout)
# --------------------------------------------------------------------------- #
#: 洗い出しの台帳は docs/ops/optics/guides/virtual_machine_vision.md。
#: パラメータは「センサー・レンズ・光源・レイアウト」の 4 つに自然に分かれ、
#: レイアウトが残り 3 つを束ねて**導出量を閉じた式で**返す。
_SHUTTERS = ("global", "rolling")
_SOURCE_KINDS = ("led", "halogen", "laser")


#: 実在の産業用センサ(現行品中心)。**公開ページに載る値だけ**を持つ ――
#: 解像度・画素ピッチ・シャッタ・最大フレームレート・世代。飽和容量/読み出し雑音/QE は
#: データシートか EMVA1288 レポートにしかないので、ここには入れず既定の典型値を使う
#: (「特定型番の実測」だと誤解させないため)。台帳は
#: .claude/skills/corpus/machine_vision_optics_corpus/products/image_sensors.md(raptor)。
_SENSOR_CATALOG = {
    # 型番: (幅, 高さ, 画素µm, シャッタ, 世代, 状態,
    #        QE%, ダークノイズ e-, 飽和容量 ke-, DR dB, 最大SNR dB)
    # -- Pregius 1st: 画素が大きく飽和容量が 3 倍。ダイナミックレンジで選ぶなら今も強い
    "IMX174": (1920, 1200, 5.86, "global", "Pregius 1st", "legacy", 70, 7, 31.8, 74, 45),
    "IMX249": (1920, 1200, 5.86, "global", "Pregius 1st", "legacy", 70, 7, 31.9, 74, 45),
    # -- Pregius 2nd: 3.45 µm。解像度を稼ぐ代わりに 1 画素の容量が 1/3 になった
    "IMX252": (2048, 1536, 3.45, "global", "Pregius 2nd", "mature", 69, 2, 10.5, 73, 40),
    "IMX264": (2448, 2048, 3.45, "global", "Pregius 2nd", "mature", 68, 2, 10.4, 73, 40),
    "IMX265": (2048, 1536, 3.45, "global", "Pregius 2nd", "mature", 68, 2, 10.5, 73, 40),
    "IMX267": (4096, 2160, 3.45, "global", "Pregius 2nd", "mature", 69, 2, 10.2, 73, 40),
    "IMX273": (1440, 1080, 3.45, "global", "Pregius 2nd", "mature", 63, 3, 10.5, 71, 40),
    "IMX287": (720, 540, 6.90, "global", "Pregius 2nd", "mature", 63, 7, 21.0, 74, 43),
    "IMX304": (4096, 3000, 3.45, "global", "Pregius 2nd", "mature", 69, 2, 10.2, 73, 40),
    "IMX392": (1920, 1200, 3.45, "global", "Pregius 2nd", "mature", 62, 3, 10.5, 72, 40),
    # -- Pregius S 4th: 2.74 µm 裏面照射。**新規設計はここ**
    "IMX530": (5328, 4608, 2.74, "global", "Pregius S 4th", "current", 66, 2, 9.6, 71, 40),
    "IMX540": (5328, 4608, 2.74, "global", "Pregius S 4th", "current", 66, 2, 9.7, 71, 40),
    "IMX541": (4504, 4504, 2.74, "global", "Pregius S 4th", "current", 66, 2, 9.7, 71, 40),
    "IMX542": (5320, 3032, 2.74, "global", "Pregius S 4th", "current", 66, 2, 9.7, 71, 40),
    "IMX545": (4096, 3000, 2.74, "global", "Pregius S 4th", "current", 67, 3, 9.9, 70, 40),
    "IMX546": (2840, 2840, 2.74, "global", "Pregius S 4th", "current", 66, 2, 9.8, 70, 40),
    # -- ローリングシャッタ(低照度で QE が高い。動体が無いなら候補)
    "IMX178": (3088, 2064, 2.40, "rolling", "STARVIS", "mature", 81, 3, 14.3, 73, 42),
    "IMX183": (5472, 3648, 2.40, "rolling", "STARVIS", "mature", 75, 3, 13.8, 71, 41),
    "IMX226": (4024, 3036, 1.85, "rolling", "STARVIS", "mature", 83, 3, 11.0, 70, 40),
    # -- onsemi PYTHON(4.8 µm グローバル。小型・高速。ダークノイズは 11-12 e- と大きい)
    "PYTHON 300": (640, 480, 4.80, "global", "onsemi PYTHON", "mature", 52, 11, 7.1, 57, 39),
    "PYTHON 500": (800, 600, 4.80, "global", "onsemi PYTHON", "mature", 54, 11, 7.8, 57, 39),
    "PYTHON 1300": (1280, 1024, 4.80, "global", "onsemi PYTHON", "mature", 53, 11, 6.9, 56, 38),
    "PYTHON 2000": (1920, 1200, 4.80, "global", "onsemi PYTHON", "mature", 54, 11, 7.8, 57, 39),
    "PYTHON 5000": (2590, 2048, 4.80, "global", "onsemi PYTHON", "mature", 55, 12, 8.2, 57, 39),
    # -- onsemi XGS(3.2 µm グローバル。**大判**が本領。APS-C / 35 mm まである)
    "XGS 20000": (4500, 4500, 3.20, "global", "onsemi XGS", "current", 55, 4, 9.2, 66, 40),
    "XGS 32000": (6580, 4935, 3.20, "global", "onsemi XGS", "current", 57, 4, 9.3, 66, 40),
    "XGS 45000": (8192, 5460, 3.20, "global", "onsemi XGS", "current", 55, 5, 9.0, 65, 40),
    "MT9J003": (3840, 2748, 1.67, "rolling", "onsemi", "legacy", 46, 6, 2.8, 54, 34),
    # -- Gpixel GMAX(2.5 µm グローバル。**ダークノイズ 1 e- 級**が特徴。超高解像度も)
    "GMAX0505": (5120, 5120, 2.50, "global", "Gpixel GMAX", "current", 51, 4, 4.3, 60, 36),
    "GMAX2505": (2600, 2160, 2.50, "global", "Gpixel GMAX", "current", 53, 1, 4.8, 70, 37),
    "GMAX2509": (4200, 2160, 2.50, "global", "Gpixel GMAX", "current", 53, 1, 4.6, 69, 37),
    "GMAX2518": (4508, 4096, 2.50, "global", "Gpixel GMAX", "current", 56, 3, 6.7, 66, 38),
    "GMAX3265": (9344, 7000, 3.20, "global", "Gpixel GMAX", "current", 52, 8, 10.4, 61, 40),
    # -- ams(旧 CMOSIS)CMV(5.5 µm。飽和容量は大きいがダークノイズも 14 e- と大きい)
    "CMV2000": (2048, 1088, 5.50, "global", "ams CMV", "mature", 63, 14, 9.3, 57, 40),
    "CMV4000": (2048, 2048, 5.50, "global", "ams CMV", "mature", 62, 14, 11.9, 59, 41),
    "CMV12000": (4096, 3072, 5.50, "global", "ams CMV", "mature", 45, 14, 11.6, 59, 41),
    # -- Teledyne e2v(切替シャッタ。NIR 強化版がある)
    "EV76C570": (1602, 1202, 4.50, "switchable", "Teledyne e2v", "legacy", 47, 22, 6.8, 50, 38),
    "EV76C661": (1280, 1024, 5.30, "switchable", "Teledyne e2v NIR", "legacy", 59, 23, 7.4, 50, 39),
}


def sensor_catalog(status: str = None) -> dict:
    """実在センサの諸元表(Basler の EMVA1288 実測つき)。

    ``status`` に current / mature / legacy を渡すと絞れる。ディスコンで古すぎるものは
    載せていない。新規設計は ``status="current"``(Pregius S、2.74 µm 裏面照射)から選ぶ。

    **ここに載っているのは「カメラ側の値」**である。出典が Basler のカメラ実測表なので:
      * 解像度は**そのカメラが出す画素数**で、センサの全有効画素とは限らない
        (メーカーは端を切って少し低くすることがある)。
      * フレームレートは**接続インターフェース**(USB3 / GigE / 5GigE / CXP-12)で
        変わるので、センサの属性として持たない ―― だからこの表には入れていない。
      * QE / ダークノイズ / 飽和容量 / ダイナミックレンジ / 最大 SNR は
        **カメラの EMVA1288 実測**(ace / ace 2 / boost)。センサ単体の理論値では
        なく実装込みなので、別のカメラなら少し変わる。
      * 画素ピッチ・シャッタ方式・世代はセンサ由来なので、カメラが変わっても動かない。

    **自社でセンサを作っているカメラメーカーはここに載せられない**(Canon / Photron /
    Vision Research(Phantom) / Teledyne DALSA / Hamamatsu の一部)。型番から引けず、
    カメラのデータシートが唯一の出所だからである。画素ピッチが桁違いのものがあり
    (Phantom の高感度機は 28 µm、Pregius S は 2.74 µm)、回折律速に入る F 値も
    飽和容量も一桁変わるので、**実機の値を直接 sensor_spec に渡すこと**。

    世代で何が変わるかは飽和容量に出る: Pregius 1st は 31.8 ke- で、2nd(10.4 ke-)の
    **3 倍**。画素を 5.86 µm から 3.45 µm へ小さくした代償である。Pregius S(2.74 µm)は
    9.7 ke- で 2nd と同等を保っている(裏面照射)。

    Sony 以外(``maker`` で引ける)も同じ表から取ってあるので、**同じ測定法で横並び
    比較できる**:
      * **onsemi XGS**(3.2 µm)は APS-C / 35 mm の**大判**が本領。Sony にこの判は無い。
      * **onsemi PYTHON**(4.8 µm)は小型・高速だが、ダークノイズが 11-12 e- と
        Pregius の 5 倍。暗い場面では効いてくる。
      * **Gpixel GMAX**(2.5 µm)は**ダークノイズ 1 e- 級**が売り(GMAX2505/2509)。
        飽和容量は 4-5 ke- と小さいので、ダイナミックレンジは 70 dB でほぼ同等。
        GMAX3265 は 65 MP(9344x7000)で、超高解像度なら選択肢がここしかない。
      * **ams CMV**(5.5 µm)は飽和容量が大きい代わりにダークノイズも 14 e-。
    """
    if status is not None and status not in ("current", "mature", "legacy"):
        raise ValueError("status must be current / mature / legacy, got %r" % status)
    out = {}
    for name, v in _SENSOR_CATALOG.items():
        w, h, px, sh, gen, st, qe, dn, sat, dr, snr = v
        if status is not None and st != status:
            continue
        maker = ("Sony" if name.startswith("IMX")
                 else gen.split()[0] if gen else "unknown")
        out[name] = {"width": w, "height": h, "pixel_um": px, "shutter": sh,
                     "generation": gen, "status": st, "maker": maker,
                     "megapixels": round(w * h / 1e6, 2),
                     "quantum_efficiency": qe / 100.0, "read_noise_e": float(dn),
                     "full_well_e": sat * 1e3, "dynamic_range_db": float(dr),
                     "max_snr_db": float(snr), "source": "Basler EMVA1288 data overview"}
    return out


def sensor_spec(pixel_um: float = 3.45, resolution=(1024, 1024),
                quantum_efficiency: float = 0.6, full_well_e: float = 1.0e4,
                read_noise_e: float = 2.5, dark_e_per_s: float = 5.0,
                bit_depth: int = 8, gain_e_per_unit: float = 5.0e4,
                shutter: str = "global", model: str = None) -> dict:
    """イメージセンサの諸元。**電子の数**まで決める側の値だけを持つ。

    ``quantum_efficiency`` は光子 -> 電子の変換効率、``dark_e_per_s`` は暗電流
    (暗視野は露光が長いのでここが効く)、``shutter`` は global / rolling
    (コンベア上の部品では rolling の歪みが出る)。

    光学的な明るさ(何個の光子が来るか)はレンズとレイアウトで決まり、ここでは
    **それをどう記録するか**だけを持つ ―― 混ぜると「センサーを変えたのに視野も
    変わった」ような追跡不能な変更になる。

    ``model`` に実在の型番(``sensor_catalog()`` のキー、例 "IMX541")を渡すと、
    解像度・画素ピッチ・シャッタに加えて **QE・読み出し雑音・飽和容量も
    Basler の EMVA1288 実測**で埋まる(引数で明示した値はそちらを優先)。
    出所はカメラ実測なので、別のカメラなら少し変わる。
    """
    if model is not None:
        cat = sensor_catalog()
        if model not in cat:
            raise ValueError(f"unknown sensor model {model!r}; "
                             f"choose from {sorted(cat)} or pass the numbers directly")
        c = cat[model]
        pixel_um, resolution, shutter = c["pixel_um"], (c["width"], c["height"]), c["shutter"]
        # EMVA1288 の実測があるものはそちらを既定にする(引数で明示指定されていれば尊重)
        if quantum_efficiency == 0.6:
            quantum_efficiency = c["quantum_efficiency"]
        if full_well_e == 1.0e4:
            full_well_e = c["full_well_e"]
        if read_noise_e == 2.5:
            read_noise_e = c["read_noise_e"]
    px = _pos(pixel_um, "pixel_um")
    res = np.asarray(resolution, dtype=int)
    # 高さ 1 = ラインセンサ(竹中 TL 系や Vieworks VT の TDI がこれ)。撮像側はまだ
    # エリア前提だが、諸元と帯域の計算はラインでも成立するので入口では拒否しない
    if res.shape != (2,) or res[0] < 2 or res[1] < 1:
        raise ValueError(f"resolution must be (width >= 2, height >= 1), got {resolution!r}")
    qe = float(quantum_efficiency)
    if not (0.0 < qe <= 1.0):
        raise ValueError(f"quantum_efficiency must lie in (0, 1], got {quantum_efficiency!r}")
    if shutter not in _SHUTTERS:
        raise ValueError(f"shutter must be one of {_SHUTTERS}, got {shutter!r}")
    dk = float(dark_e_per_s)
    if not np.isfinite(dk) or dk < 0.0:
        raise ValueError(f"dark_e_per_s must be finite and >= 0, got {dark_e_per_s!r}")
    bits = int(bit_depth)
    if not (1 <= bits <= 16):
        raise ValueError(f"bit_depth must be in [1, 16], got {bit_depth!r}")
    return {"kind": "sensor", "pixel_um": px, "width": int(res[0]), "height": int(res[1]),
            "quantum_efficiency": qe, "full_well_e": _pos(full_well_e, "full_well_e"),
            "read_noise_e": float(read_noise_e), "dark_e_per_s": dk, "bit_depth": bits,
            "gain_e_per_unit": _pos(gain_e_per_unit, "gain_e_per_unit"), "shutter": shutter,
            "model": model,
            # 値の出所を残す(実測か典型値かを後から追跡できるように)
            "noise_values_are": "EMVA1288 (Basler camera)" if model else "user-supplied"}


def lens_spec(focal_mm: float = 25.0, f_number: float = None, na: float = None,
              working_distance_mm: float = 200.0, coc_um: float = None,
              telecentric: bool = False, transmission: float = 0.9) -> dict:
    """レンズの諸元。NA と F 値は**どちらで与えてもよい**(N = 1/(2·NA))。

    ``coc_um`` を省くと画素ピッチを許容錯乱円に使う(レイアウトが束ねるときに解決)。
    ``telecentric=True`` は倍率が距離で変わらない前提 ―― 寸法測定ではここが効く。
    """
    f = _pos(focal_mm, "focal_mm")
    wd = _pos(working_distance_mm, "working_distance_mm")
    if wd <= f:
        raise ValueError(f"working_distance_mm {wd} must exceed focal_mm {f}")
    if (f_number is None) == (na is None):
        raise ValueError("give exactly one of f_number or na (N = 1/(2·NA))")
    N = _pos(f_number, "f_number") if f_number is not None else 1.0 / (2.0 * _pos(na, "na"))
    tr = float(transmission)
    if not (0.0 < tr <= 1.0):
        raise ValueError(f"transmission must lie in (0, 1], got {transmission!r}")
    return {"kind": "lens", "focal_mm": f, "f_number": N,
            "numerical_aperture": 1.0 / (2.0 * N), "working_distance_mm": wd,
            "coc_um": None if coc_um is None else _pos(coc_um, "coc_um"),
            "telecentric": bool(telecentric), "transmission": tr}


def light_spec(kind: str = "coaxial", source: str = "led",
               wavelength_nm: float = 550.0, bandwidth_nm: float = 30.0,
               radius_mm: float = 40.0, height_mm: float = 110.0,
               size_mm: float = None, n: int = 196, intensity: float = 1.0,
               cos_exponent: float = 1.0, polarization: str = None) -> dict:
    """照明の諸元。**幾何は illumdesign.light_source に委ね、光の性質をここで足す**。

    ``kind`` は coaxial / ring / dome / bar / backlight(器具の形)。
    ``source`` は led / halogen / laser で、``wavelength_nm`` と ``bandwidth_nm``
    が意味を変える ―― LED は狭帯域(~30 nm)、ハロゲンは広帯域(~300 nm)、
    レーザーは単一波長(0 nm)でコヒーレント。粗さの鏡面割合
    exp(-(4πσcosθ/λ)²) が波長依存なので、**同じ面でも光源で見え方が変わる**。

    ``size_mm`` は器具の実体の差し渡し。鏡像として写るかどうか = 明視野/暗視野の
    本体なので、点近似のままだと暗視野が原理的に成立しない。省くと ``radius_mm``
    の半分を使う。
    """
    if source not in _SOURCE_KINDS:
        raise ValueError(f"source must be one of {_SOURCE_KINDS}, got {source!r}")
    bw = float(bandwidth_nm)
    if not np.isfinite(bw) or bw < 0.0:
        raise ValueError(f"bandwidth_nm must be finite and >= 0, got {bandwidth_nm!r}")
    if source == "laser" and bw > 0.0:
        bw = 0.0                                       # レーザーは単一波長として扱う
    import illumdesign as _id
    geo = _id.light_source(kind=kind, radius_mm=_pos(radius_mm, "radius_mm"),
                           height_mm=_pos(height_mm, "height_mm"), n=int(n),
                           intensity=float(intensity), cos_exponent=float(cos_exponent))
    geo["size_mm"] = float(size_mm) if size_mm is not None else float(radius_mm) * 0.5
    geo.update(source=source, wavelength_nm=float(wavelength_nm), bandwidth_nm=bw,
               coherent=source == "laser", polarization=polarization)
    return geo


def light_wavelengths(light: dict, samples: int = 5):
    """光源のスペクトルを、撮像に使う数本の波長と重みに落とす。

    レーザー = 1 本、LED = 狭帯域を数本、ハロゲン = 広帯域を数本。同じ面でも
    波長で鏡面/散乱の配分が変わるので、広帯域は**重ね合わせて**撮るのが正しい。
    """
    lam = float(light.get("wavelength_nm", 550.0))
    bw = float(light.get("bandwidth_nm", 0.0))
    k = max(int(samples), 1)
    if bw <= 0.0 or k == 1:
        return np.array([lam]), np.array([1.0])
    xs = np.linspace(-1.0, 1.0, k)
    w = np.exp(-0.5 * (xs * 2.0) ** 2)                 # ガウス型のスペクトル
    return lam + 0.5 * bw * xs, w / w.sum()


def vision_layout(sensor: dict, lens: dict, lights, scene=None,
                  tilt_deg: float = 0.0, azimuth_deg: float = 0.0,
                  look_at_mm=(0.0, 0.0, 0.0)) -> dict:
    """センサー・レンズ・照明・シーンを束ね、**導出量を閉じた式で**返す。

    返り値 dict: ``camera``(:func:`optical_camera` と同じ規約)/ ``sensor`` /
    ``lens`` / ``lights`` / ``scene`` / ``budget``(:func:`optical_budget`)。

    撮る前にここを見れば、視野に部品が収まるか・欠陥が分解できるか・被写界深度が
    足りるかが分かる ―― 「見えるか」ではなく「必要なコントラストで写るか」を
    先に判断するのが、光学デジタルツインを持つ理由。
    """
    for name, obj, want in (("sensor", sensor, "sensor"), ("lens", lens, "lens")):
        if not isinstance(obj, dict) or obj.get("kind") != want:
            raise ValueError(f"{name} must be a {want}_spec() result")
    lights = [lights] if isinstance(lights, dict) else list(lights)
    if not lights:
        raise ValueError("lights must contain at least one light_spec() result")
    lam = float(np.mean([float(l.get("wavelength_nm", 550.0)) for l in lights]))
    cam = optical_camera(focal_mm=lens["focal_mm"], pixel_um=sensor["pixel_um"],
                         resolution=(sensor["width"], sensor["height"]),
                         working_distance_mm=lens["working_distance_mm"],
                         look_at_mm=look_at_mm, tilt_deg=tilt_deg, azimuth_deg=azimuth_deg)
    budget = optical_budget(focal_mm=lens["focal_mm"],
                            working_distance_mm=lens["working_distance_mm"],
                            f_number=lens["f_number"], pixel_um=sensor["pixel_um"],
                            wavelength_nm=lam, coc_um=lens["coc_um"])
    return {"kind": "layout", "camera": cam, "sensor": sensor, "lens": lens,
            "lights": lights, "scene": None if scene is None else _check_scene(scene),
            "budget": budget}


def layout_capture(layout: dict, exposure_ms: float = 10.0, supersample: int = 2,
                   spectral_samples: int = 1, apply_diffraction: bool = True,
                   apply_defocus: bool = False, raw: bool = False) -> dict:
    """レイアウトのとおりに撮る(スペクトル -> 回折 -> 被写界深度 -> センサー)。

    ``spectral_samples`` > 1 で光源のスペクトルを重ね合わせる(ハロゲンのような
    広帯域はこれが要る。LED は 1-3 本、レーザーは 1 本で足りる)。
    ``raw=True`` なら量子化前の放射輝度も返す。

    返り値 dict: ``image``(量子化済み)/ ``radiance``(raw のとき)/ ``depth_mm`` /
    ``part_mask`` / ``defect_mask`` / ``budget``。
    """
    if not isinstance(layout, dict) or layout.get("kind") != "layout":
        raise ValueError("layout must be a vision_layout() result")
    if layout["scene"] is None:
        raise ValueError("layout has no scene; pass scene= to vision_layout()")
    scene, cam, sensor, lens = (layout["scene"], layout["camera"],
                                layout["sensor"], layout["lens"])
    acc = None
    for light in layout["lights"]:
        lams, ws = light_wavelengths(light, spectral_samples)
        for lam, w in zip(lams, ws):
            r = render_optscene(scene, cam, [light], depth=1, supersample=supersample,
                                wavelength_nm=float(lam))
            acc = w * r if acc is None else acc + w * r
    acc = acc * lens["transmission"] * sensor["quantum_efficiency"]
    depth = optscene_depth(scene, cam)
    if apply_diffraction:
        acc = diffraction_blur(acc, cam, f_number=layout["budget"]["f_number_working"],
                               wavelength_nm=layout["budget"]["wavelength_nm"])
    if apply_defocus:
        acc = defocus_blur(acc, depth, cam, f_number=lens["f_number"])
    img = sensor_capture(acc, exposure_ms=exposure_ms,
                         gain_e_per_unit=sensor["gain_e_per_unit"],
                         read_noise_e=np.hypot(sensor["read_noise_e"],
                                               np.sqrt(sensor["dark_e_per_s"]
                                                       * exposure_ms * 1e-3)),
                         full_well_e=sensor["full_well_e"], bit_depth=sensor["bit_depth"])
    out = {"image": img, "depth_mm": depth, "budget": layout["budget"],
           "part_mask": optscene_mask(scene, cam, 0),
           "defect_mask": optscene_defect_mask(scene, cam)}
    if raw:
        out["radiance"] = acc
    return out


#: 産業用カメラの伝送規格と 1 接続あたりの帯域 [Gbps]。フレームグラバーの台帳は
#: .claude/skills/corpus/machine_vision_optics_corpus/products/frame_grabbers.md(raptor)。
#: 光学が「必要なコントラストで写るか」を決めるのに対し、ここは「落とさずに運べるか」。
_INTERFACES = {
    "CXP-6": 6.25, "CXP-12": 12.5,           # CoaXPress(PoCXP で電源・制御・データを 1 本に)
    # Camera Link: 構成でビット幅が変わる(Base 24bit / Medium 48 / Full 64 / Deca 80、
    # いずれも最大 85 MHz)。2026-09-05 に Full を 6.8 と誤記していたのを修正
    # (6.8 は Deca の値。Full は 5.44)。
    "CameraLink-Base": 2.04, "CameraLink-Medium": 4.08,
    "CameraLink-Full": 5.44, "CameraLink-Deca": 6.80,
    "CameraLinkHS": 3.125,                    # 1 lane あたり
    # Opt-C:Link(アバールデータ独自の光 I/F)。ノイズに強く数百 m 延ばせる。
    # 1 ch 6.25 Gbps、2 ch 束ねて 12.5 Gbps。Camera Link カメラは変換ユニットで繋ぐ
    "Opt-C:Link": 6.25,
    "GigE": 1.0, "5GigE": 5.0, "10GigE": 10.0, "25GigE": 25.0,
    "USB3": 5.0,
}


def linescan_capture(scene, camera, lights, velocity_mm_s: float = 100.0,
                     line_rate_hz: float = 10000.0, lines: int = 512,
                     tdi_stages: int = 1, sync_error: float = 0.0,
                     scan_axis=(1.0, 0.0, 0.0), ambient: float = 0.0,
                     depth: int = 1, light_samples: int = None) -> dict:
    """**ラインスキャン / TDI** で撮る(搬送しながら 1 ラインずつ積む)。

    エリアセンサの模型では表せない領域。``camera`` は高さ 1 のラインセンサ
    (``sensor_spec(resolution=(N, 1))`` → :func:`vision_layout`)を想定するが、
    高さ h のカメラを渡した場合は**先頭ラインだけ**を使う。

    走査方向の画素実寸は **搬送速度 ÷ ラインレート** で決まる。横方向は光学倍率で
    決まるので、この 2 つが合っていないと**画像の縦横比が崩れる** ―― 光学をいくら
    詰めても直らない、ラインスキャン固有の故障モードである。

    ``tdi_stages`` を 2 以上にすると TDI(時間遅延積分)。M 段で信号が M 倍になるが、
    ``sync_error``(搬送とラインレートの相対誤差、0.01 = 1%)があると段ごとに位置が
    ずれて**M 段ぶんボケる**。感度と同期精度のトレードオフがそのまま出る。

    返り値 dict: ``image``(lines, width, 3 の放射輝度)/ ``depth_mm`` /
    ``part_mask`` / ``defect_mask`` / ``pixel_mm_scan``(走査方向の画素実寸)/
    ``pixel_mm_cross``(横方向)/ ``aspect``(縦横比。1.0 が正方画素)。
    """
    scene = _check_scene(scene)
    lights = [lights] if isinstance(lights, dict) else list(lights)
    if not lights:
        raise ValueError("lights must contain at least one illumdesign.light_source() result")
    v = _pos(velocity_mm_s, "velocity_mm_s")
    lr = _pos(line_rate_hz, "line_rate_hz")
    n_lines = int(lines)
    if n_lines < 1:
        raise ValueError(f"lines must be >= 1, got {lines!r}")
    m = int(tdi_stages)
    if m < 1:
        raise ValueError(f"tdi_stages must be >= 1, got {tdi_stages!r}")
    err = float(sync_error)
    if not np.isfinite(err):
        raise ValueError(f"sync_error must be finite, got {sync_error!r}")
    axis = _unit(_arr(scan_axis, "scan_axis", 3)[None])[0]

    step = v / lr                                        # 1 ライン進む距離 [mm]
    W = camera["width"]
    o0, d0 = camera_rays(camera)
    o0, d0 = o0[:W], d0[:W]                              # 先頭ラインだけ使う

    k = np.arange(n_lines, dtype=np.float64)[:, None]    # (L, 1)
    acc = None
    hit0 = None
    for stage in range(m):
        # TDI: 電荷が被写体と一緒に送られるので、**完全同期なら全段が同じ物点を見る**
        # (段が 1 つ進むあいだに被写体も 1 ライン進むので相殺する)。ずれるのは
        # 同期誤差のぶんだけ。2026-09-05 に (1 + err) と書いていて、誤差 0 でも
        # 段数ぶん スメアが出ていた ―― 明るくなるだけのはずが 64 段で鮮鋭度 0.38 に
        # 落ちており、TDI の利点が消えていた
        shift = (k + stage * err) * step
        org = (o0[None, :, :] + shift[..., None] * axis).reshape(-1, 3)
        dirs = np.broadcast_to(d0[None, :, :], (n_lines, W, 3)).reshape(-1, 3)
        hit = trace_rays(scene, org, dirs)
        fp = (np.where(np.isfinite(hit["t"]), hit["t"], 0.0)
              * camera["pixel_mm"] / camera["focal_mm"])
        col = _shade(scene, hit, dirs, lights, float(ambient), int(depth), True, fp,
                     light_samples)
        bg = float(ambient) + _light_background(lights, org, dirs)
        col = np.where((hit["index"] < 0)[..., None], bg[..., None], col)
        acc = col if acc is None else acc + col
        if stage == 0:
            hit0 = (hit, org, dirs)
    img = (acc / m).reshape(n_lines, W, 3)

    hit, org, dirs = hit0
    z = (hit["t"] * (dirs @ camera["forward"])).reshape(n_lines, W)
    idx = hit["index"].reshape(n_lines, W)
    defect = np.zeros((n_lines, W), bool)
    for j, obj in enumerate(scene):
        sel = hit["index"] == j
        if not sel.any():
            continue
        if obj.get("is_defect"):
            defect |= (idx == j)
        elif obj.get("defect") is not None:
            flat = np.zeros(n_lines * W, bool)
            _mod, _tilt, lab = _defect_sample(obj, hit["point"][sel])
            flat[np.nonzero(sel)[0]] = lab
            defect |= flat.reshape(n_lines, W)
    cross = camera["pixel_mm"] * camera["working_distance_mm"] / camera["focal_mm"]
    return {"image": img, "depth_mm": np.where(idx >= 0, z, np.nan),
            "part_mask": idx == 0, "defect_mask": defect,
            "pixel_mm_scan": step, "pixel_mm_cross": cross,
            "aspect": step / max(cross, 1e-12),
            "tdi_stages": m, "sync_error": err}


def interface_budget(sensor: dict, interface: str = "CXP-12", links: int = 4,
                     efficiency: float = 0.85, line_scan: bool = False) -> dict:
    """伝送帯域から**帯域律速の最大フレーム / ラインレート**を返す。

    高解像度・高速・ラインスキャンでは、律速がセンサではなく**伝送帯域**になることが
    普通にある。撮る前にどちらが律速かを知るための op(光学の :func:`optical_budget`
    と対になる)。

    ``efficiency`` は符号化・パケットの実効効率(CoaXPress で概ね 0.8-0.9)。
    ``line_scan=True`` なら 1 ライン(幅 x 1 画素)あたりで計算し、ラインレート [kHz]
    を返す。

    返り値 dict: ``gbps``(総帯域)/ ``bytes_per_frame`` / ``max_fps`` /
    ``max_line_rate_khz``(line_scan のとき)/ ``interface`` / ``links``。

    実測の目安: CXP-12 x4 = 50 Gbps = 5 GB/s は、8 bit・16k ラインセンサを 300 kHz で
    回せる帯域にちょうど一致する(Vieworks VT の TDI がこの前提)。一方エリアスキャンの
    IMX541(20.3 MP・8 bit)は 1 枚 20.3 MB なので理論 246 fps 出るが、センサ自体が
    18-42 fps なので**帯域は余る**。
    """
    if not isinstance(sensor, dict) or sensor.get("kind") != "sensor":
        raise ValueError("sensor must be a sensor_spec() result")
    if interface not in _INTERFACES:
        raise ValueError(f"interface must be one of {sorted(_INTERFACES)}, got {interface!r}")
    n = int(links)
    if n < 1:
        raise ValueError(f"links must be >= 1, got {links!r}")
    eff = float(efficiency)
    if not (0.0 < eff <= 1.0):
        raise ValueError(f"efficiency must lie in (0, 1], got {efficiency!r}")
    gbps = _INTERFACES[interface] * n * eff
    bytes_per_s = gbps * 1e9 / 8.0
    px = sensor["width"] * (1 if line_scan else sensor["height"])
    per_frame = px * sensor["bit_depth"] / 8.0
    rate = bytes_per_s / max(per_frame, 1e-12)
    out = {"interface": interface, "links": n, "gbps": gbps,
           "bytes_per_frame": per_frame, "max_fps": rate}
    if line_scan:
        out["max_line_rate_khz"] = rate / 1e3
    return out


def optical_budget(focal_mm: float = 25.0, working_distance_mm: float = 200.0,
                   f_number: float = None, na: float = None, pixel_um: float = 3.45,
                   wavelength_nm: float = 550.0, coc_um: float = None) -> dict:
    """観察光学系の**分解能バジェット**を閉じた式で出す(撮る前に成立するかを見る)。

    NA と F 値はどちらで与えてもよい(N = 1/(2·NA))。倍率は薄肉近似
    m = f / (WD − f)、実効(作動)F 値は N_w = (1 + |m|)·N。返す量:

      ``magnification`` 倍率 m / ``f_number_working`` N_w /
      ``airy_um`` エアリー半径 1.22·λ·N_w(像面)/ ``airy_object_um`` それを物体側に換算 /
      ``pixel_object_um`` 画素の物体側の実寸 / ``limit_um`` 実際の分解限界
      (回折と標本化の**大きい方**)/ ``limited_by`` どちらが律速か /
      ``dof_um`` 被写界深度(物体側、幾何 2·N_w·c/m² と波動 2·λ·N_w²/m² の和)/
      ``coc_um`` 許容錯乱円(既定は画素ピッチ)。

    「見えるか」ではなく「**必要なコントラストで写るか**」を決める前段の数字で、
    ここが足りていない構成でいくら画像を作っても、実機では検査が成立しない。
    """
    f = _pos(focal_mm, "focal_mm")
    wd = _pos(working_distance_mm, "working_distance_mm")
    if wd <= f:
        raise ValueError(f"working_distance_mm {wd} must exceed focal_mm {f}")
    if (f_number is None) == (na is None):
        raise ValueError("give exactly one of f_number or na (N = 1/(2·NA))")
    N = _pos(f_number, "f_number") if f_number is not None else 1.0 / (2.0 * _pos(na, "na"))
    px = _pos(pixel_um, "pixel_um")
    lam = _pos(wavelength_nm, "wavelength_nm") * 1e-3            # nm -> µm
    c = px if coc_um is None else _pos(coc_um, "coc_um")

    m = f / (wd - f)                                             # 薄肉近似の倍率
    nw = (1.0 + abs(m)) * N                                      # 作動 F 値
    airy = 1.22 * lam * nw                                       # 像面のエアリー半径
    airy_obj = airy / abs(m)
    px_obj = px / abs(m)
    limit = max(airy_obj, 2.0 * px_obj)                          # 回折 と 標本化(2画素)
    dof = (2.0 * nw * c + 2.0 * lam * nw * nw) / (m * m)         # 幾何 + 波動(物体側)
    return {"magnification": m, "f_number": N, "f_number_working": nw,
            "numerical_aperture": 1.0 / (2.0 * N), "airy_um": airy,
            "airy_object_um": airy_obj, "pixel_object_um": px_obj,
            "limit_um": limit,
            "limited_by": "diffraction" if airy_obj >= 2.0 * px_obj else "sampling",
            "dof_um": dof, "coc_um": c, "wavelength_nm": float(wavelength_nm)}


def observe_surface(material: str = "al", finish: str = "hairline",
                    pitch_um: float = 90.0, depth_um: float = 1.0,
                    roughness_um: float = 0.08, focal_mm: float = 25.0,
                    working_distance_mm: float = 200.0, f_number: float = None,
                    na: float = None, pixel_um: float = 3.45, resolution=(256, 256),
                    wavelength_nm: float = 550.0, illumination: str = "coaxial",
                    tilt_deg: float = 0.0, source_size_mm: float = 40.0,
                    supersample: int = 2, exposure: str = "auto",
                    defects: dict = None, seed: int = 0) -> dict:
    """**観察光学系を組んで、指定した素材の仕上げ面を撮る**(一行で使える入口)。

    ユーザー要望(2026-09-05)「基本的な観察用の光学系をレイアウトした場合を想定して、
    それらのパラメータを与えて、アルミなどの素材を指定した上で、ヘアライン画像を
    生成できるといいな。最初は同軸照明でも良い」。

    光学系は NA でも F 値でも指定できる。作動距離・焦点距離・画素ピッチ・波長から
    :func:`optical_budget` が倍率・エアリー半径・被写界深度・分解限界を出し、その
    まま撮像に効く(回折ぼけは :func:`diffraction_blur`、ぼけの深さ方向は
    :func:`depth_of_field`)。素材は ``glassmirror.METALS``、仕上げは
    ``surface_finish`` の種類。

    ``illumination`` は coaxial / ring / dome / bar / backlight。同軸は面が鏡なら
    器具が映って明るく(明視野)、低角のリングは映らないので暗い(暗視野)。

    返り値 dict: ``image``(線形 RGB)/ ``camera`` / ``scene`` / ``light`` /
    ``budget``(上の光学バジェット)/ ``defect_mask``(``defects`` を渡したとき)。
    """
    if material not in _gm.METALS:
        raise ValueError(f"material must be one of {tuple(_gm.METALS)}, got {material!r}")
    if f_number is None and na is None:
        f_number = 5.6                                           # よくある既定
    budget = optical_budget(focal_mm=focal_mm, working_distance_mm=working_distance_mm,
                            f_number=f_number, na=na, pixel_um=pixel_um,
                            wavelength_nm=wavelength_nm)
    lobe = {"hairline": "linear", "turned": "circular", "crosshatch": "crosshatch",
            "blasted": "random", "ground": "linear", "none": "random"}.get(finish, "random")
    plate = scene_box((0.0, 0.0, 2.5), (30.0, 30.0, 2.5),
                      scene_material("conductor", metal=material, finish=lobe,
                                     roughness_um=roughness_um))
    if finish != "none":
        plate = surface_finish(plate, kind=finish, pitch_um=pitch_um, depth_um=depth_um,
                               uv_size_mm=(64.0, 64.0), seed=int(seed))
    mask = None
    if defects:
        made = random_defects(plate, seed=int(seed) + 1, uv_size_mm=(64.0, 64.0), **defects)
        plate, extra, _labels = made["part"], made["objects"], made["labels"]
    else:
        extra = []
    scene = [plate] + extra
    cam = optical_camera(focal_mm=focal_mm, pixel_um=pixel_um, resolution=resolution,
                         working_distance_mm=working_distance_mm, tilt_deg=tilt_deg)
    import illumdesign as _id
    light = _id.light_source(kind=illumination, radius_mm=source_size_mm,
                             height_mm=working_distance_mm * 0.55, n=196)
    light["size_mm"] = float(source_size_mm)                     # 器具の実体の大きさ
    if defects:
        mask = optscene_defect_mask(scene, cam)
    img = render_optscene(scene, cam, [light], depth=1, supersample=int(supersample),
                          wavelength_nm=wavelength_nm)
    img = diffraction_blur(img, cam, f_number=budget["f_number_working"],
                           wavelength_nm=wavelength_nm)
    if exposure == "auto":                                       # 面の中央値を中間調に置く
        lvl = float(np.median(img[img > 0])) if np.any(img > 0) else 1.0
        img = img * (0.45 / max(lvl, 1e-30))
    return {"image": img, "camera": cam, "scene": scene, "light": light,
            "budget": budget, "defect_mask": mask}


def sensor_capture(radiance, exposure_ms: float = 10.0, gain_e_per_unit: float = 5.0e4,
                   read_noise_e: float = 2.5, full_well_e: float = 1.0e4,
                   bit_depth: int = 8, seed: int = 0) -> np.ndarray:
    """放射輝度 → 実センサの出力(ショット雑音・読み出し雑音・飽和・量子化)。

    光子数 = radiance · exposure_ms · gain_e_per_unit / 1000 を平均とする Poisson。
    そこへ読み出し雑音(正規)を足し、``full_well_e`` で**飽和**させ、``bit_depth``
    で量子化する。飽和は clip であって折り返さない(白飛びは白のまま)。

    返り値は 0..2^bit_depth−1 の整数配列。``seed`` を固定すれば決定的。
    """
    r = np.asarray(radiance, dtype=np.float64)
    if np.any(r < 0.0) or not np.all(np.isfinite(r)):
        raise ValueError("radiance must be finite and non-negative")
    exp = _pos(exposure_ms, "exposure_ms")
    g = _pos(gain_e_per_unit, "gain_e_per_unit")
    fw = _pos(full_well_e, "full_well_e")
    rn = float(read_noise_e)
    if rn < 0.0 or not np.isfinite(rn):
        raise ValueError(f"read_noise_e must be finite and >= 0, got {read_noise_e!r}")
    bits = int(bit_depth)
    if not (1 <= bits <= 16):
        raise ValueError(f"bit_depth must be in [1, 16], got {bit_depth!r}")
    rng = np.random.default_rng(int(seed))
    e = rng.poisson(np.minimum(r * exp * g / 1000.0, 1e12))
    e = e + (rng.normal(0.0, rn, e.shape) if rn > 0.0 else 0.0)
    levels = 2 ** bits - 1
    return np.clip(np.rint(np.clip(e, 0.0, fw) / fw * levels), 0, levels).astype(np.int32)
