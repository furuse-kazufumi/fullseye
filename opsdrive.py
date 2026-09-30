# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsdrive — 自動運転の教習所ワールドの台帳: 規格寸法のコース(2-D)/ 3-D の世界 / 回転式 LiDAR / カメラ /
τ 理論の衝突までの時間(drivettc)/ RSS の安全距離(rsssafety)/ 閉形式の地形と路面の材質・手続きの物体(driveterrain)/
卓球の球の力学・追跡・真値つきの台・ラケット(ballistics / balltrack / ballworld / racket)/
日本の信号灯器と道路標識(roadjp、公表寸法をそのまま頂点に持つ)/
けん玉の定理と閉ループの捕球・真値つきのけんの世界(kendama / kendamaworld)。
世界を 3D Gaussian Splatting にして描く(gsplatnp: 面に貼ったガウシアン + EWA 描画、密度と誤差のつまみ)。
車の縦の運動と坂(drivelong: 空走 + 制動の停止距離の閉形式、坂の保持と発進のずり下がり、技能試験の減点)。

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
import drivelong
import drivettc
import gsplatnp
import driveworld
import kendama
import kendamaworld
import lidarsim
import racket
import roadjp
import rsssafety

_MOD = {"drivecourse": drivecourse, "driveworld": driveworld, "lidarsim": lidarsim, "drivettc": drivettc,
        "rsssafety": rsssafety, "driveterrain": driveterrain,
        "ballistics": ballistics, "balltrack": balltrack, "ballworld": ballworld, "racket": racket,
        "roadjp": roadjp,
        "kendama": kendama, "kendamaworld": kendamaworld, "gsplatnp": gsplatnp, "drivelong": drivelong}

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
    # けん玉の大皿(18 巡目): 大振幅振り子の周期 4√(L/g)K(k)(K は AGM)、張力 m(v²/L + g cos θ) と弛む角 cos θ_s = (2/3)cos θ₀、
    # 振り上げ(bang-bang / 台形)と頂点の閉形式、皿の縁に乗る幾何、2 段のシミュレーション(張っている間は射影法、弛んだら自由落下)、
    # 放物線の閉形式で皿を運ぶ閉ループの計画、知覚雑音つきの成功率。
    "kendama": [
        ("kendama_params", "kendama", [], "table"),
        ("elliptic_k_agm", "kendama", [], "scalar"),
        ("pendulum_period_exact", "kendama", [], "scalar"),
        ("pendulum_launch_speed", "kendama", [], "scalar"),
        ("pendulum_rod_simulate", "kendama", [], "table"),
        ("tether_tension_fixed", "kendama", [], "scalar"),
        ("tether_slack_angle", "kendama", [], "any"),
        ("swing_up_plan", "kendama", ["table"], "any"),
        ("swing_up_apex", "kendama", ["table"], "table"),
        ("kendama_catch_check", "kendama", ["table"], "table"),
        ("kendama_simulate", "kendama", ["table"], "table"),
        ("catch_plan_ballistic", "kendama", ["table"], "any"),
        ("noisy_perceiver", "kendama", [], "any"),
        ("catch_success_rate", "kendama", ["table"], "table"),
        # 作り直し: 段階を明示した捕球(hold → carry → absorb)、頂点を決める持ち上げ量の閉形式、g 既知の放物線の当てはめ、玉の穴の検出
        ("catch_plan_staged", "kendama", ["table"], "any"),
        ("swing_up_lift", "kendama", ["table"], "scalar"),
        ("parabola_fit_g", "kendama", [], "table"),
        ("hole_detect", "kendama", ["image2d"], "table"),
        ("kendama_combo_simulate", "kendama", ["table"], "table"),   # 連続技(もしかめ・3 皿)
    ],
    # けんの世界(18 巡目、作り直し): けん(けん先・握り・中皿の回転体)+ 皿胴(両端が大皿・小皿に開く回転体)、ラベル 27 けん /
    # 28 大皿 / 30 小皿 / 31 中皿 / 32 玉の穴(ballworld の 20〜26 と重ならない)、糸の角柱(29)、床 + けん + 穴のある玉 + 糸の世界、
    # 振り上げの空間を見るカメラの組、受ける皿の中心の投影の真値。ballworld の上に載る層。
    "kendamaworld": [
        ("ken_mesh", "kendamaworld", ["table"], "table"),
        ("add_ken", "kendamaworld", ["table", "table"], "scalar"),
        ("ken_set_pose", "kendamaworld", ["table", "matrix"], "any"),
        ("string_mesh", "kendamaworld", [], "any"),
        ("add_string", "kendamaworld", ["table"], "scalar"),
        ("string_set", "kendamaworld", ["table"], "any"),
        ("kendama_world", "kendamaworld", ["table"], "table"),
        ("kendama_rig", "kendamaworld", ["table"], "table"),
        ("ken_truth", "kendamaworld", ["table", "table"], "table"),
        # 作り直し: 技の姿勢で世界を置く、玉とけん玉の隙間(回転体の子午面の厳密な距離)、画像だけから (p̂, v̂) を出す知覚
        ("kendama_pose", "kendamaworld", ["table"], "table"),
        ("kendama_clearance", "kendamaworld", ["table"], "table"),
        ("camera_perceiver", "kendamaworld", ["table"], "any"),
    ],
    # 世界(三角形の束)→ 3DGS: 面に貼ったガウシアン(面の番号 + 重心座標 + 局所の誤差を固定で持ち、頂点が動けば付いて動く)、
    # EWA 投影 Σ' = J W Σ Wᵀ Jᵀ + 0.3 I と手前からの α 合成で描く。真値 = 2 次モーメントの閉形式・合成の式・剛体の同変性。
    "gsplat": [
        ("gs_from_world", "gsplatnp", ["table"], "table"),
        ("gs_update", "gsplatnp", ["table", "table"], "table"),
        ("gs_render", "gsplatnp", ["table", "matrix"], "table"),
        ("gs_render_fn", "gsplatnp", ["table"], "any"),
    ],
    # 車の縦の運動: m dv/dt = 駆動 − 制動 − m g sin θ − c_rr m g cos θ − ½ρC_dA v|v|(止まっている間はブレーキの保持の範囲で動かない)。
    # 真値 = 停止距離の閉形式 vρ + (1/2k)ln(1 + k v²/A)(A = b ± g sin θ + c_rr g cos θ)、rsssafety との一致、坂道発進のずり下がりの閉形式、
    # エネルギー収支。採点 = 警察庁 丙運発第 12 号(令和 4 年)の減点細目。
    "long": [
        ("long_params", "drivelong", [], "table"),
        ("road_profile", "drivelong", ["table"], "table"),
        ("road_eval", "drivelong", ["table", "scalar"], "any"),
        ("long_simulate", "drivelong", ["scalar", "scalar", "any"], "table"),
        ("long_energy_residual", "drivelong", ["table"], "any"),
        ("stopping_distance_grade", "drivelong", ["scalar", "scalar", "scalar"], "scalar"),
        ("stop_line_plan", "drivelong", ["scalar", "scalar"], "table"),
        ("plan_command", "drivelong", ["table"], "any"),
        ("hill_hold_brake_min", "drivelong", ["scalar"], "scalar"),
        ("hill_start_rollback", "drivelong", ["scalar", "scalar", "scalar"], "table"),
        ("hill_start_command", "drivelong", ["scalar", "scalar", "scalar", "scalar"], "any"),
        ("skill_test_thresholds", "drivelong", [], "table"),
        ("skill_test_score", "drivelong", ["table"], "table"),
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
