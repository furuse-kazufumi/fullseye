# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsgeocam — fullseye fixed-camera geo-orientation op registry.

Motivation (2026-09-21): public fixed cameras (road, weather, tourism) publish their
*position* but not their *orientation* — or only a coarse one (road direction code, an
id hash, a manual gizmo). Without the orientation a frame cannot be placed on a map, a
DEM or a 3-D city. This registry (geocam.py, 7 ops / 3 categories) recovers yaw / pitch /
roll of a camera at a known position from the picture itself, with no learning:

  * sun: the sun's apparent position is a closed form of time and place (NOAA solar
    calculator, Meeus 1998); two time-stamped sun pixels fix the rotation exactly
    (Wahba's problem, Kabsch 1976 SVD). Lalonde, Narasimhan & Efros, IJCV 2010 fitted
    the same cue to webcam sequences (3 deg on 22 low-quality webcams); Jacobs et al.,
    WACV 2008 is the ancestor.
  * skyline: the ridge silhouette rendered from a DEM at the camera position, matched
    against the sky/terrain boundary extracted by dynamic programming (Lie, Lin & Hsu
    2005) — Baatz, Saurer, Köser & Pollefeys, ECCV 2012 restricted to one camera whose
    position is known. The ambiguity (several valleys in the yaw profile) is returned,
    not hidden.

Both routes give the same (yaw, pitch, roll) and can check each other on the same camera
(the prior work uses one or the other). Provenance = public papers and NOAA formulas only.

Coexistence with existing assets (compose, do not re-implement):
  * DEM handling is the dem family (`dem_horizon_angle` = every cell x one azimuth;
    `dem_skyline` here = one point x every azimuth). Geodetic conversion stays in dem.
  * intrinsics are (fx, fy, cx, cy) as in `project_points` / `pnp_ransac` (3d family).
  * sky/sun photometry (skydome, atmospheric models) is the optics family; geocam only
    uses the sun's *direction* and the skyline's *shape*.

Usage:
    import opsgeocam
    opsgeocam.list_ops("skyline")
    opsgeocam.get("dem_skyline")(dem, 30.0, (150, 150))
"""
import inspect
import sys
from functools import wraps

import numpy as np

import geocam


# ★2026-11-03(レシピの e2e が見つけた宣言の嘘): 台帳は ``sun_position`` の入力を ``signal``(UNIX 秒の 1-D 列)
#   と宣言しているのに、素の関数は ``(lat_deg, lon_deg, unix_times)`` の並びで、宣言どおり時刻の列を第 1 引数に
#   渡すと緯度に入り ``TypeError: only 0-dimensional arrays can be converted to Python scalars`` で落ちた。
#   同じ族の消費側 ``camera_orientation_from_sun(sun_pixels, unix_times, lat, lon, K)`` も時刻を「場所より前」に
#   置いている。素の関数(``geocam.sun_position`` と facade ``fs.sun_position``)の並びは公開の約束なので変えず、
#   **台帳の入口だけ**を宣言の並び ``(unix_times, lat_deg, lon_deg)`` にする(``__wrapped__`` で同じ op の
#   identity を保ち、``__signature__`` で OP_GRAPH の引数表も宣言どおりになる)。
#   旧い並び ``(lat, lon, unix_times)`` で台帳を呼んでいた呼び手のために、**経度の位置に配列が来た**ときだけ
#   旧い並びと読む(経度は必ずスカラなので取り違えは起きない)。3 つともスカラなら宣言の並びと読む ——
#   旧い並びのスカラ呼び出しは時刻が経度に入り ``geocam._check_latlon`` が範囲外として拒む(fail-closed、
#   黙って違う太陽を返さない)。
@wraps(geocam.sun_position)
def sun_position(unix_times, lat_deg, lon_deg):
    if np.ndim(lon_deg) > 0 and np.ndim(unix_times) == 0 and np.ndim(lat_deg) == 0:
        # 旧い並び (lat_deg, lon_deg, unix_times) —— 引数名ではなく位置で来た値をそのまま素の関数へ。
        return geocam.sun_position(unix_times, lat_deg, lon_deg)
    if np.ndim(lat_deg) > 0 or np.ndim(lon_deg) > 0:
        raise ValueError("sun_position: lat_deg and lon_deg must be scalars (the site); got shapes %r, %r"
                         % (np.shape(lat_deg), np.shape(lon_deg)))
    return geocam.sun_position(lat_deg, lon_deg, unix_times)


sun_position.__signature__ = inspect.Signature([
    inspect.Parameter(n, inspect.Parameter.POSITIONAL_OR_KEYWORD) for n in ("unix_times", "lat_deg", "lon_deg")])
sun_position.__module__ = __name__
sun_position.__qualname__ = "sun_position"

_MOD = {"geocam": geocam, "opsgeocam": sys.modules[__name__]}

# --------------------------------------------------------------------------
# Type vocabulary: no new word is coined (it all fits the existing pool).
# --------------------------------------------------------------------------
#   * signal    — UNIX times (1-D) into `sun_position` / `camera_orientation_from_sun`,
#                 and the extracted skyline (one row per image column) out of
#                 `skyline_extract` and into `camera_orientation_from_skyline`.
#   * depth     — the DEM (H, W) in metres, the same sort the dem family eats.
#   * image2d   — the photograph (grey) and the rendered sky mask.
#   * keypoints — sun pixels (N, 2) as (u, v), the image-plane sort.
#   * table     — every estimate is a dict (angles, residuals, profiles).
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    "sun": [
        # 入口は opsgeocam.sun_position(時刻の列が先 = 宣言どおり。上の注記)。計算は geocam.sun_position。
        ("sun_position", "opsgeocam", ["signal"], "table"),
        ("sun_pixel_position", "geocam", ["image2d"], "keypoints"),
        ("camera_orientation_from_sun", "geocam", ["keypoints", "signal"], "table"),
            # 2026-09-21 実データ(Fintraffic)で足した 2 本: 切れたブルームの円当て / 候補列から動きで太陽を選ぶ
            ("sun_bloom_fit", "geocam", ["image2d"], "table"),
            ("camera_orientation_from_sun_candidates", "geocam", ["keypoints", "signal", "signal"], "table"),
    ],
    "skyline": [
        ("dem_skyline", "geocam", ["depth"], "table"),
        ("skyline_extract", "geocam", ["image2d"], "signal"),
        ("render_skyline_view", "geocam", ["table"], "image2d"),
    ],
    "orientation": [
        ("camera_orientation_from_skyline", "geocam", ["signal", "table"], "table"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = ""
            if fn is not None and fn.__doc__:
                doc = fn.__doc__.strip().splitlines()[0]
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "func": fn, "doc": doc}
    return reg


OPSGEOCAM = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSGEOCAM.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**空 — 意図的に**。7 op はすべて宣言型どおり
#: (dict = table / (W,) = signal / (N,2) = keypoints / (H,W) = image2d)を素で返す。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSGEOCAM[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSGEOCAM[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSGEOCAM[name]


def missing():
    """レジストリに載っているが実体が見つからない op。"""
    return [n for n, m in OPSGEOCAM.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsgeocam: {len(OPSGEOCAM)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
