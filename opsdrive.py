# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsdrive — 自動運転の教習所ワールドの台帳: 規格寸法のコース(2-D)/ 3-D の世界 / 回転式 LiDAR / カメラ /
τ 理論の衝突までの時間(drivettc)/ RSS の安全距離(rsssafety)/ 閉形式の地形と路面の材質・手続きの物体(driveterrain)。

型語彙は既存のものだけを使う(新語なし):
  * ``table``   — コース(drivecourse の dict: polygon / centerline / entry / exit / params …)、世界(driveworld の dict:
                  V / F / face_label / face_color / objects)、LiDAR の一掃(lidarsim の dict: points / ranges / labels …)、
                  カメラの像(color / label / depth)。**dict のまま運ぶ**のは、面のラベルと色を落とすと真値が消えるから
                  (mesh sort の (V, F) には載らない)。
  * ``image2d`` — 占有格子(bool、row = y、col = x)。
  * ``matrix``  — 4×4 の姿勢(world ← sensor)や 3×3 の内部パラメータ。
  * ``mesh``    — (V, F)。`lidar_scan` は世界 dict でなく (V, F) + 面ラベルを受ける(世界以外のメッシュにも撃てるように)。

Usage:
    import opsdrive
    opsdrive.list_ops("course")
    opsdrive.get("course_crank")()
"""
import drivecourse
import driveterrain
import drivettc
import driveworld
import lidarsim
import rsssafety

_MOD = {"drivecourse": drivecourse, "driveworld": driveworld, "lidarsim": lidarsim, "drivettc": drivettc,
        "rsssafety": rsssafety, "driveterrain": driveterrain}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 規格寸法のコース(道路交通法施行規則 別表第三、普通免許の値が既定)。引数なしで dict を返し、
    # course_layout が (x, y, yaw) で並べる。真値 = 多角形(靴紐の面積が閉形式と一致する門)。
    "course": [
        ("course_crank", "drivecourse", [], "table"),
        ("course_s_curve", "drivecourse", [], "table"),
        ("course_turnaround", "drivecourse", [], "table"),
        ("course_slope", "drivecourse", [], "table"),
        ("course_intersection", "drivecourse", [], "table"),
        ("course_parallel_parking", "drivecourse", [], "table"),
        ("course_crossing", "drivecourse", [], "table"),
        ("course_road", "drivecourse", [], "table"),
        ("course_loop_bend", "drivecourse", [], "table"),
        ("course_loop", "drivecourse", [], "table"),
        ("course_layout", "drivecourse", ["table", "table"], "table"),
        ("course_occupancy", "drivecourse", ["table"], "image2d"),
        ("course_contains", "drivecourse", ["table", "points"], "signal"),
    ],
    # 3-D の世界: コース → メッシュ(面ラベル・面色つき)+ CC0 の車・信号機・標識。カメラは render3d の三角形 id から
    # 色・ラベル・深度の像を引く(真値は世界の側にある)。
    "world": [
        ("world_build", "driveworld", ["table"], "table"),
        ("world_camera", "driveworld", ["table", "matrix", "matrix"], "table"),
        ("load_asset", "driveworld", [], "table"),
        ("world_move", "driveworld", ["table"], "any"),
    ],
    # 回転式 LiDAR: メッシュにレイを撃つ(Möller–Trumbore、方位・仰角のビンで加速)。平面・箱の閉形式が第 2 実装。
    "lidar": [
        ("lidar_spec", "lidarsim", [], "table"),
        ("lidar_scan", "lidarsim", ["mesh", "table", "matrix"], "table"),
        ("ray_plane_range", "lidarsim", ["points", "points"], "signal"),
        ("ray_box_ranges", "lidarsim", ["points", "points"], "signal"),
    ],
    # τ 理論(Lee 1976)の衝突までの時間: 深度像 + 剛体運動の閉形式が真値、光学流と見かけの大きさが推定(15 巡目)。
    # 恒等式 = 真の流れを time_to_contact に入れると 1 コマ後の τ(1 コマ足すと真の τ₀ と 1e-9 で一致)。
    "ttc": [
        ("relative_motion", "drivettc", ["matrix", "matrix"], "matrix"),
        ("foe_from_motion", "drivettc", ["matrix", "matrix"], "signal"),
        ("flow_from_depth_motion", "drivettc", ["image2d", "matrix", "matrix"], "table"),
        ("ttc_truth", "drivettc", ["image2d", "matrix", "matrix"], "table"),
        ("ttc_from_flow", "drivettc", ["image2d", "image2d"], "table"),
        ("ttc_from_scale", "drivettc", [], "scalar"),
        ("ttc_from_range", "drivettc", [], "scalar"),
        ("label_extent", "drivettc", ["labels2d"], "table"),
        ("foe_from_flow", "drivettc", ["image2d", "image2d"], "table"),
    ],
    # RSS(Shalev-Shwartz 2017)の安全距離: 閉形式(Lemma)と最悪ケースの時間積分(第 2 実装)、公表値は ad-rss-lib の表と試験。
    "rss": [
        ("rss_params", "rsssafety", [], "table"),
        ("rss_stopping_distance", "rsssafety", [], "scalar"),
        ("rss_longitudinal_same", "rsssafety", ["table"], "scalar"),
        ("rss_longitudinal_opposite", "rsssafety", ["table"], "scalar"),
        ("rss_lateral", "rsssafety", ["table"], "scalar"),
        ("rss_longitudinal_check", "rsssafety", ["table"], "table"),
        ("rss_lateral_check", "rsssafety", ["table"], "table"),
        ("rss_worst_case_gap", "rsssafety", ["table"], "table"),
        ("rss_worst_case_gap_opposite", "rsssafety", ["table"], "table"),
        ("rss_worst_case_gap_lateral", "rsssafety", ["table"], "table"),
    ],
    # 世界を広げる(16 巡目): 閉形式の地形(fBm のスペクトル合成 β = 2H + 2、Perlin の勾配雑音)、コースへの距離場(eikonal)、
    # 世界座標で評価する路面の材質(真値 = ラベル・摩耗率・水溜り・染み)、手続きの木・歩行者・横断歩道(体積・面積の閉形式)。
    "terrain": [
        ("perlin2", "driveterrain", ["image2d", "image2d"], "table"),
        ("fbm_params", "driveterrain", [], "table"),
        ("fbm_height", "driveterrain", ["image2d", "image2d", "table"], "image2d"),
        ("fbm_gradient", "driveterrain", ["image2d", "image2d", "table"], "any"),
        ("radial_periodogram", "driveterrain", ["image2d"], "table"),
        ("spectral_slope", "driveterrain", ["image2d"], "table"),
        ("course_distance", "driveterrain", ["table", "points"], "table"),
        ("terrain_params", "driveterrain", [], "table"),
        ("terrain_height", "driveterrain", ["image2d", "image2d", "table"], "image2d"),
        ("terrain_gradient", "driveterrain", ["image2d", "image2d", "table"], "any"),
        ("terrain_mesh", "driveterrain", ["table", "table"], "table"),
        ("world_apply_terrain", "driveterrain", ["table", "table"], "table"),
        ("material_params", "driveterrain", [], "table"),
        ("world_materials", "driveterrain", ["table", "table", "matrix", "matrix", "table"], "table"),
        ("tree_mesh", "driveterrain", [], "table"),
        ("pedestrian_mesh", "driveterrain", [], "table"),
        ("crosswalk_mesh", "driveterrain", [], "table"),
        ("add_mesh_object", "driveterrain", ["table", "table"], "scalar"),
        ("scatter_offroad", "driveterrain", ["table"], "points"),
        ("mesh_signed_volume", "driveterrain", ["points", "matrix"], "scalar"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = fn.__doc__.strip().splitlines()[0] if fn is not None and fn.__doc__ else ""
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "func": fn, "doc": doc}
    return reg


OPSDRIVE = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSDRIVE.items() if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(typed_catalog が集める)。course_occupancy は (occ, extent) を返すので格子だけを渡す。
RESULT_ADAPTERS = {"course_occupancy": lambda r: r[0]}
ADAPTERS = RESULT_ADAPTERS


def get(name):
    """op 名から関数を引く(無ければ KeyError)。"""
    return OPSDRIVE[name]["func"]


def info(name):
    """op の登録情報(category / in / out / doc)。"""
    m = OPSDRIVE[name]
    return {k: m[k] for k in ("category", "module", "in", "out", "doc")}


def call(name, *args, **kwargs):
    """登録名で呼ぶ。"""
    return get(name)(*args, **kwargs)


def missing():
    """台帳に在るが実体が無い op(ゼロであることを試験が確かめる)。"""
    return [n for n, m in OPSDRIVE.items() if m["func"] is None]


if __name__ == "__main__":
    for c in categories():
        print(c)
        for n in list_ops(c):
            print("  ", n, "-", OPSDRIVE[n]["doc"][:70])
