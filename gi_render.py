# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gi_render — 大域照明つきのレンダリング(optional backend: Mitsuba 3、BSD-3)。

**なぜ要るか(実測)**: Fullseye 内蔵の :mod:`render_beauty` は z バッファのラスタライザ
で、直接光しか運ばない。ところが検査で最もありふれた配置 —— 照明ボックスの中に部品を
置く —— は**凹んだ場**であり、相互反射が支配的になる。

2026-09-05 に同一レンダラ・同一サンプラで光路長だけを変えて測った(コーネルボックス、
128x128、spp=128):

===============================================  =========
測ったもの                                        値
===============================================  =========
平均輝度 直接光のみ(max_depth=2)                  0.2634
平均輝度 大域照明あり(max_depth=8)                0.4289
場全体の明るさの増加                              +62.8 %
画素ごとの相対差 中央値                           49.4 %
赤い壁の近くの床 直接光のみ                       (0.142, 0.142, 0.142)
赤い壁の近くの床 大域照明あり                     (0.458, 0.322, 0.270)
===============================================  =========

つまり内蔵ラスタライザの陰影は、囲まれた場では**画素値が 5 割ずれ、色にじみが
まったく出ない**。合成データを作る用途では、この差は無視できない。

**なぜ Mitsuba か(2026-09-05 の一次情報調査)**: Blender の Cycles は Apache-2.0 で
ライセンスは白だが、公式が standalone を「production 用ではない」「ビルド済み
バイナリは無い」と明記しており、Python バインディングも無い。決定的なのは
standalone の CLI が**深度・法線・ID の正解パスを一切出せない**こと —— 合成データ
生成では、その正解パスこそが目的物である。Mitsuba 3 は BSD-3、公式 wheel があり
ビルド不要、``aov`` 積分器で正解パスが取れる。

**この層が担当しないこと(正直に)**: レンズとセンサは渡さない。Mitsuba のカメラは
薄レンズ近似で、面ごとの硝材という概念が無い。実光線・実硝材・収差・MTF は
Fullseye 側(:mod:`raytrace` / :mod:`lensimage`)のほうが上なので、
**放射輝度は Mitsuba、結像とセンサは Fullseye** という分担にする。

    import gi_render
    out = gi_render.render_gi(V, F)          # image / radiance / depth / normals / silhouette

Mitsuba が入っていなければ :func:`available` が ``False`` を返し、
:func:`render_gi` は ``ImportError`` を投げる(黙って劣化した絵を返さない)。
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

import numpy as np

__all__ = ["available", "render_gi", "MITSUBA_VARIANT"]

#: 使う variant。``scalar_rgb`` は LLVM/CUDA を要求しないので、どの機械でも動く。
#: 分光が要るようになったら ``scalar_spectral``(同じ wheel に入っている)。
MITSUBA_VARIANT = "scalar_rgb"

_ENCLOSURES = ("box", "ground", "none")


def available() -> bool:
    """Mitsuba 3 が使えるか。**副作用なし**(import も variant 設定もしない)。"""
    import importlib.util
    try:
        return importlib.util.find_spec("mitsuba") is not None
    except (ImportError, ValueError):                            # pragma: no cover
        return False


def _mi():
    try:
        import mitsuba as mi
    except Exception as exc:                                     # noqa: BLE001
        raise ImportError(
            "gi_render needs the optional 'mitsuba' backend — install with: "
            "pip install \"fullseye[gi]\"  (Mitsuba 3, BSD-3-Clause)") from exc
    if mi.variant() != MITSUBA_VARIANT:
        mi.set_variant(MITSUBA_VARIANT)
    return mi


def _mesh_arrays(V, F):
    """(V, F) を検証して float32/uint32 の連続配列にする。fail-closed。"""
    v = np.ascontiguousarray(np.asarray(V, dtype=np.float64))
    f = np.asarray(F)
    if v.ndim != 2 or v.shape[1] != 3 or v.shape[0] < 3:
        raise ValueError(f"V must be (N,3) with N >= 3 (got: {v.shape})")
    if not np.isfinite(v).all():
        raise ValueError("V contains non-finite values")
    if f.ndim != 2 or f.shape[1] != 3 or f.shape[0] < 1:
        raise ValueError(f"F must be (M,3) with M >= 1 (got: {f.shape})")
    if not np.issubdtype(f.dtype, np.integer):
        if not np.all(np.asarray(f, np.float64) == np.floor(np.asarray(f, np.float64))):
            raise ValueError("F must contain integer vertex indices")
        f = f.astype(np.int64)
    if f.min() < 0 or f.max() >= v.shape[0]:
        raise ValueError(
            f"F indexes vertices outside V: range [{int(f.min())}, {int(f.max())}] "
            f"but V has {v.shape[0]} vertices")
    return v, f.astype(np.int64)


def _camera(mi, pose, K, size):
    """Fullseye の ``(pose, K)`` を Mitsuba のセンサ辞書へ写す。

    ★向きは 2026-09-05 に**実測で決めた**(推測していない)。非対称メッシュで
    ラスタライザ :func:`render3d.render_mesh` と画素ごとに突き合わせ、
    IoU 0.951 / z 深度差の中央値 0.0036(差は輪郭の部分被覆のみ)になる組み合わせ:

    * 視線 = ``origin - c2w[:, 2]``(Fullseye の pose は -Z が視線 = OpenGL 流)
    * up   = ``c2w[:, 1]``(OpenCV の「下」。Mitsuba のフィルム v 軸と行順の差を相殺する)

    逆向きの組み合わせは IoU 0.375 になるので、この検査は反転を見逃さない。
    """
    P = np.asarray(pose, dtype=np.float64)
    if P.shape != (4, 4) or not np.isfinite(P).all():
        raise ValueError(f"pose must be a finite (4,4) matrix (got: {P.shape})")
    Km = np.asarray(K, dtype=np.float64)
    if Km.shape != (3, 3) or not np.isfinite(Km).all():
        raise ValueError(f"intrinsics must be a finite (3,3) matrix (got: {Km.shape})")
    c2w = np.linalg.inv(P)
    origin = c2w[:3, 3]
    fy = float(Km[1, 1])
    if not (fy > 0.0):
        raise ValueError(f"intrinsics fy must be positive (got: {fy})")
    fov_y = math.degrees(2.0 * math.atan(size / (2.0 * fy)))
    to_world = mi.ScalarTransform4f().look_at(
        origin=origin.tolist(),
        target=(origin - c2w[:3, 2]).tolist(),
        up=c2w[:3, 1].tolist())
    return P, {
        "type": "perspective", "fov": fov_y, "fov_axis": "y", "to_world": to_world,
        "film": {"type": "hdrfilm", "width": int(size), "height": int(size),
                 "rfilter": {"type": "box"}, "pixel_format": "rgb"},
        "sampler": {"type": "independent", "sample_count": 4},
    }


def _shape(mi, v, f, albedo):
    """メッシュを**メモリ上で**組む(中間ファイルを作らない)。

    反射率は :class:`mitsuba.Properties` 経由で BSDF ごと渡す。既定の BSDF は
    グレースケール(``UniformSpectrum``)なので、後から ``traverse`` で色を差すと
    ``bad cast`` になる —— 2026-09-05 に踏んだ。色が要るなら**作るときに**渡す。
    """
    props = mi.Properties()
    props["bsdf"] = mi.load_dict({
        "type": "diffuse",
        "reflectance": {"type": "rgb", "value": [float(x) for x in albedo]}})
    mesh = mi.Mesh("mesh", int(v.shape[0]), int(f.shape[0]), props, False, False)
    params = mi.traverse(mesh)
    params["vertex_positions"] = np.ravel(v.astype(np.float32))
    params["faces"] = np.ravel(f.astype(np.uint32))
    params.update()
    return mesh


def _enclosure(mi, kind, centre, radius, albedo, light_power):
    """相互反射が起きる**場**を作る。これが無いと大域照明を測る意味が無い。"""
    T = mi.ScalarTransform4f
    r = float(radius)
    cx, cy, cz = (float(x) for x in centre)

    def face(shift, rot_axis, deg, refl):
        t = T().translate(shift)
        if deg:
            t = t.rotate(rot_axis, deg)
        return {"type": "rectangle", "to_world": t.scale(2.0 * r),
                "bsdf": {"type": "diffuse",
                         "reflectance": {"type": "rgb", "value": list(refl)}}}

    out = {}
    if kind in ("box", "ground"):
        out["gi_floor"] = face([cx, cy - 2 * r, cz], [1, 0, 0], -90, albedo)
    if kind == "box":
        out["gi_back"] = face([cx, cy, cz - 2 * r], None, 0, albedo)
        out["gi_left"] = face([cx - 2 * r, cy, cz], [0, 1, 0], 90, albedo)
        out["gi_right"] = face([cx + 2 * r, cy, cz], [0, 1, 0], -90, albedo)
        out["gi_top"] = face([cx, cy + 2 * r, cz], [1, 0, 0], 90, albedo)
    out["gi_light"] = {
        "type": "rectangle",
        "to_world": T().translate([cx, cy + 1.97 * r, cz]).rotate([1, 0, 0], 90).scale(0.6 * r),
        "emitter": {"type": "area",
                    "radiance": {"type": "rgb", "value": [float(light_power)] * 3}},
    }
    return out


def render_gi(V, F, *, pose=None, intrinsics=None, size: int = 256, spp: int = 64,
              max_depth: int = 8, albedo: Sequence[float] = (0.8, 0.8, 0.85),
              enclosure: str = "box", wall_albedo: Sequence[float] = (0.75, 0.75, 0.75),
              light_power: float = 18.0, seed: int = 0,
              pose_intrinsics: Optional[tuple] = None) -> dict:
    """三角メッシュを**大域照明つき**でレンダリングし、正解パスも一緒に返す。

    Args:
        V: 頂点 ``(N,3)``。
        F: 三角形の頂点番号 ``(M,3)``。
        pose: 世界→カメラの ``(4,4)``。``None`` なら :func:`render3d.auto_view`。
        intrinsics: ピンホールの ``(3,3)``。``None`` なら同上。
        size: 出力の一辺(正方)。
        spp: 画素あたりのサンプル数。**上げるほど雑音が減り、時間は線形に増える**。
        max_depth: 光路の最大長。``2`` = 直接光のみ(内蔵ラスタライザ相当)、
            ``8`` = 相互反射あり。**この 2 つを比べると大域照明の寄与が測れる**。
        albedo: 対象メッシュの拡散反射率。
        enclosure: ``"box"`` = 囲む(相互反射が出る) / ``"ground"`` = 床だけ /
            ``"none"`` = 何も置かない(光源のみ)。
        wall_albedo: 囲いの反射率。
        light_power: 面光源の放射輝度。
        seed: 乱数の種。**同じ種なら同じ絵**(サンプラを固定して再現性を持たせる)。

    Returns:
        dict:
            * ``image`` ``(size,size,3)`` [0,1] に収めた表示用(Reinhard)
            * ``radiance`` ``(size,size,3)`` 線形の放射輝度(トーンマップ前)
            * ``depth`` ``(size,size)`` **カメラ空間の z**(光線距離ではない)。
              当たっていない画素は ``0``
            * ``normals`` ``(size,size,3)`` 世界座標の面法線
            * ``silhouette`` ``(size,size)`` bool

    Raises:
        ImportError: Mitsuba が入っていない(**黙って劣化した絵を返さない**)。
        ValueError: 形・非有限・引数の範囲。
    """
    mi = _mi()
    v, f = _mesh_arrays(V, F)
    size = int(size)
    spp = int(spp)
    max_depth = int(max_depth)
    if size < 8:
        raise ValueError(f"size must be >= 8 (got: {size})")
    if spp < 1:
        raise ValueError(f"spp must be >= 1 (got: {spp})")
    if max_depth < 1:
        raise ValueError(f"max_depth must be >= 1 (got: {max_depth})")
    if enclosure not in _ENCLOSURES:
        raise ValueError(f"enclosure must be one of {_ENCLOSURES} (got: {enclosure!r})")
    alb = np.asarray(albedo, dtype=np.float64)
    wall = np.asarray(wall_albedo, dtype=np.float64)
    for name, arr in (("albedo", alb), ("wall_albedo", wall)):
        if arr.shape != (3,) or not np.isfinite(arr).all() or arr.min() < 0.0 or arr.max() > 1.0:
            raise ValueError(f"{name} must be 3 finite values in 0..1 (got: {arr})")
    if not (math.isfinite(float(light_power)) and float(light_power) > 0.0):
        raise ValueError(f"light_power must be positive and finite (got: {light_power})")

    if pose is None or intrinsics is None:
        import render3d
        auto_pose, auto_K = render3d.auto_view(v, width=size, height=size)
        pose = auto_pose if pose is None else pose
        intrinsics = auto_K if intrinsics is None else intrinsics
    P, sensor = _camera(mi, pose, intrinsics, size)
    sensor["sampler"] = {"type": "independent", "sample_count": spp, "seed": int(seed)}

    centre = v.mean(axis=0)
    radius = float(np.linalg.norm(v - centre, axis=1).max()) or 1.0
    shape = _shape(mi, v, f, alb)

    scene = {"type": "scene", "sensor": sensor, "gi_mesh": shape}
    scene.update(_enclosure(mi, enclosure, centre, radius, wall, light_power))


    beauty_scene = mi.load_dict(
        dict(scene, integrator={"type": "path", "max_depth": max_depth}))
    radiance = np.asarray(mi.render(beauty_scene, spp=spp, seed=int(seed)),
                          dtype=np.float64)[..., :3]

    aov_scene = mi.load_dict(dict(
        scene, integrator={"type": "aov", "aovs": "pp:position,nn:sh_normal"}))
    aov = np.asarray(mi.render(aov_scene, spp=max(4, min(spp, 16)), seed=int(seed)),
                     dtype=np.float64)
    world = aov[..., :3]
    normals = aov[..., 3:6]
    hit = np.abs(world).sum(axis=-1) > 1e-9
    cam = (P[:3, :3] @ world.reshape(-1, 3).T).T + P[:3, 3]
    depth = np.abs(cam[:, 2]).reshape(size, size)
    depth[~hit] = 0.0

    import render_tonemap
    image = np.clip(render_tonemap.tonemap_reinhard(radiance), 0.0, 1.0)
    return {"image": image, "radiance": radiance, "depth": depth,
            "normals": normals, "silhouette": hit}
