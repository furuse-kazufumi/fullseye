# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsdrive — 自動運転の教習所ワールドの台帳: 規格寸法のコース(2-D)/ 3-D の世界 / 回転式 LiDAR / カメラ /
τ 理論の衝突までの時間(drivettc)/ RSS の安全距離(rsssafety)/ 閉形式の地形と路面の材質・手続きの物体(driveterrain)/
卓球の球の力学・追跡・真値つきの台・ラケット(ballistics / balltrack / ballworld / racket)/
日本の信号灯器と道路標識(roadjp、公表寸法をそのまま頂点に持つ)。

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
import ballistics
import balltrack
import ballworld
import drivecourse
import driveterrain
import drivettc
import driveworld
import lidarsim
import racket
import roadjp
import rsssafety

_MOD = {"drivecourse": drivecourse, "driveworld": driveworld, "lidarsim": lidarsim, "drivettc": drivettc,
        "rsssafety": rsssafety, "driveterrain": driveterrain,
        "ballistics": ballistics, "balltrack": balltrack, "ballworld": ballworld, "racket": racket,
        "roadjp": roadjp}

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
    # 卓球の球の力学(17 巡目): 真空の放物線(閉形式)と抗力 + マグヌスの RK4、跳ね(Cross 2002 / Garwin 1969、接触点まわりの
    # 角運動量が保存)、頂点の等比 e^{2k}h₀、軌跡からの初期状態・空力係数の同定、摩擦(停止距離・滑り角)、けん玉のひもと皿。
    "ball": [
        ("ball_params", "ballistics", [], "table"),
        ("impact_params", "ballistics", [], "table"),
        ("flight_vacuum", "ballistics", ["signal"], "points"),
        ("flight_ode", "ballistics", ["table"], "table"),
        ("flight_simulate", "ballistics", ["table", "table"], "table"),
        ("flight_state_at", "ballistics", ["table"], "table"),
        ("magnus_lift_coefficient", "ballistics", ["signal"], "signal"),
        ("drag_coefficient_sphere", "ballistics", ["signal"], "signal"),
        ("bounce", "ballistics", ["table", "table"], "table"),
        ("contact_angular_momentum", "ballistics", ["table"], "signal"),
        ("apex_sequence", "ballistics", [], "signal"),
        ("bounce_total_time", "ballistics", [], "scalar"),
        ("restitution_from_apexes", "ballistics", ["signal"], "table"),
        ("restitution_from_intervals", "ballistics", ["signal"], "table"),
        ("fit_parabola", "ballistics", ["signal", "points"], "table"),
        ("flight_fit", "ballistics", ["signal", "points", "table"], "table"),
        ("fit_aero", "ballistics", ["signal", "points", "table"], "table"),
        ("fit_bounce", "ballistics", ["table"], "table"),
        ("slide_stop_distance", "ballistics", [], "scalar"),
        ("incline_slip_angle", "ballistics", [], "scalar"),
        ("mu_from_stop_distance", "ballistics", [], "scalar"),
        ("roll_slide_state", "ballistics", ["table"], "table"),
        ("tether_simulate", "ballistics", [], "table"),
        ("pendulum_period", "ballistics", [], "scalar"),
        ("cup_catch_check", "ballistics", [], "table"),
    ],
    # 球の追跡(17 巡目): しきい値 → 連結成分のサブピクセル重心、等速予測の追跡、等加速度 Kalman(放物線に厳密)、DLT の三角測量、
    # 高さの局所最小の跳ね検出、模様の向きの Kabsch で角速度。
    "balltrack": [
        ("ball_detect", "balltrack", ["image2d"], "table"),
        ("ball_track", "balltrack", ["table"], "table"),
        ("kalman_ca", "balltrack", ["points"], "table"),
        ("triangulate_dlt", "balltrack", ["matrix", "any", "any"], "table"),
        ("track_triangulate", "balltrack", ["table", "any", "any"], "table"),
        ("bounce_detect", "balltrack", ["signal", "signal"], "table"),
        ("marker_direction", "balltrack", [], "signal"),
        ("spin_from_markers", "balltrack", ["points", "points"], "table"),
        ("reproject", "balltrack", ["points", "matrix", "matrix"], "matrix"),
    ],
    # 真値つきの台の世界(17 巡目): ITTF 寸法の台 + ネット + 床、正 20 面体の球と模様(ラベル 23 / 24)、台を囲むカメラ、
    # 球の中心・像の半径・模様の投影の真値(裏側の模様は NaN)。
    "ballworld": [
        ("table_params", "ballworld", [], "table"),
        ("table_world", "ballworld", ["table"], "table"),
        ("ball_mesh", "ballworld", [], "table"),
        ("add_ball", "ballworld", ["table", "table"], "scalar"),
        ("ball_set_pose", "ballworld", ["table", "matrix"], "any"),
        ("rotation_from_omega", "ballworld", [], "matrix"),
        ("camera_rig", "ballworld", ["table"], "table"),
        ("ball_truth", "ballworld", ["table", "table"], "table"),
        ("icosphere", "ballworld", [], "any"),
    ],
    # ラケット(17 巡目): 動く板との衝突(ラケット系で bounce)、板の枠の当たり判定、目標へ届く初速(真空の閉形式 → 反復)、
    # 望む v_out を出す法線と速度、上限つきの動き、2 本のラケットの打ち合いと打球の合法性の先読み。
    "racket": [
        ("racket_params", "racket", [], "table"),
        ("racket_impact", "racket", ["table", "table"], "table"),
        ("racket_hit_check", "racket", ["table"], "table"),
        ("aim_velocity", "racket", ["table"], "table"),
        ("racket_plan", "racket", ["table", "table"], "table"),
        ("racket_move", "racket", ["table"], "any"),
        ("strategy_attacker", "racket", ["table"], "table"),
        ("strategy_feeder", "racket", ["table"], "table"),
        ("shot_is_legal", "racket", ["table", "table", "table"], "table"),
        ("rally_simulate", "racket", ["table", "table", "table"], "table"),
    ],
    # 日本の信号灯器と道路標識(18 巡目): 公表寸法をそのまま頂点に持つメッシュ(標識 円 600 mm・逆三角 600 mm・菱形 450 mm、
    # 板の下端 1.8 m / 灯器 レンズ 300 mm・下端 4.5 m 以上・アーム 2.0 m)。絵は RGBA(既存の rgba sort)、板・灯器は
    # driveworld と同じ dict(V / F / color / label)、世界へ足す op は object 索引(scalar)を返す。
    "roadjp": [
        ("sign_params", "roadjp", [], "table"),
        ("sign_image", "roadjp", [], "rgba"),
        ("plate_mesh_from_image", "roadjp", ["rgba"], "table"),
        ("sign_mesh", "roadjp", [], "table"),
        ("add_sign", "roadjp", ["table"], "scalar"),
        ("signal_jp_mesh", "roadjp", [], "table"),
        ("add_signal_jp", "roadjp", ["table"], "scalar"),
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
