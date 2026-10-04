# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsdrive — 自動運転の教習所ワールドの台帳: 規格寸法のコース(2-D)/ 3-D の世界 / 回転式 LiDAR / カメラ /
τ 理論の衝突までの時間(drivettc)/ RSS の安全距離(rsssafety)/ 閉形式の地形と路面の材質・手続きの物体(driveterrain)/
卓球の球の力学・追跡・真値つきの台・ラケット(ballistics / balltrack / ballworld / racket)/
日本の信号灯器と道路標識(roadjp、公表寸法をそのまま頂点に持つ)/
けん玉の定理と閉ループの捕球・真値つきのけんの世界(kendama / kendamaworld)。
他人の場面で自分の運転手を走らせ他人の採点器に出す(drivecommonroad: CommonRoad 2020a の自前読み書き、KS 運動学の第 2 実装、IDM + pure-pursuit、TUM drivability-checker の合否 JSON)。
実在の日本の町(drivejapan / driveplateau: OSM の道路網をラスタ和集合と輪郭追跡で街区にし、PLATEAU の建物を柱で立て、一時停止・「止まれ」・踏切警標・日本式の横断歩道を規格の寸法で置き、最短路を左の車線で通して走る)。
町を 1 つに組む(drivetown: 教習所の要素を自動で継いで 1 本の道にし、縦だけの通し走行を停止線ごとに採点、教則 159 場面の台帳の集計)。
外部の高写実シミュレータ(CARLA 0.9.16)の撮影記録を自前の世界の規約に写す橋(carlabridge: 左手系の鏡映・カメラの向き・主点の 0.5 画素・24 bit の深度・29 タグ → 14 ラベル、往復の門つき、numpy だけ)。
世界を 3D Gaussian Splatting にして描く(gsplatnp: 面に貼ったガウシアン + EWA 描画、密度と誤差のつまみ)。
車の縦の運動と坂(drivelong: 空走 + 制動の停止距離の閉形式、坂の保持と発進のずり下がり、技能試験の減点)。
太陽と天気(driveenv: 太陽の位置 = 暦計算室、影・逆光の光幕・霧 Koschmieder・雨・夜の前照灯を物理の単位で描き、見えてから止まれる速さ)。
終わらない地図(driveinf: 区画の番号と種だけで決まる区画、辺のハッシュで継ぎ目がつながる道、整数格子の起伏、(区画, 区画の中) の座標)。
動く交通参加者と死角(drivetraffic: IDM の車列と運転の癖、OU の横ふらつき、Social Force の歩行者と横断の意図、路肩駐車の死角から止まれる速さ、対向車とのすれ違いの境目、場所と時刻で変わる飛び出しの率、重要度サンプリングの事故率)。
判断の場面(drivedecide: ミラーを鏡の向こうの仮想カメラで描く・凸面鏡の視野と死角、確認と合図の順序の採点、歩行者信号から車両の黄を予測・ジレンマゾーン、点滅の周波数と折り返し、サイレンのドップラーと到着時間差の方位、緊急車両への譲り(道交法 40 条)とバスの発進(31 条の 2)の採点)。
横の運動(drivelateral: 摩擦円とカーブの限界速度・道路構造令の最小半径、2 輪等価モデルのアンダーステア勾配と定常円旋回、アッカーマンと内輪差の閉形式・後車軸の軌跡、クロソイドとフレネル積分、pure pursuit と Stanley の制御則と定常の横ずれ、曲率からの速度計画、車線の横位置と TLC、左折・右折の寄り方の採点)。
踏切と交差点の優先(drivecrossing: 鉄道の解釈基準の警報の時間と遮断機の状態、警報灯の交互点滅を画素から読む、渡り切る時間と向こう側の余地(道交法 33 条・50 条 2 項)、一時停止と左右確認の採点、見通し距離の閉形式、優先道路・広い道路と左方優先(36 条)、交差車の到達時間と急な減速、横断歩道の手前の停止車両と 30 m 以内の追越し(38 条)、駐停車禁止の区間(44 条))。
追越しと見えない所(drivepass: 追越しに要る時間・道のりと対向車の境目の距離、ルームミラーに前車の全体が映って戻る車間、追越し禁止の区間と判定(28〜30 条)、追い越される側の義務(27 条)、進路変更先の後続車に要る減速度(26 条の 2)、環状交差点の優先と出口の 1 つ手前での合図(37 条の 2・53 条)、坂の頂上の視距(道路構造令の表を再現)と止まれる速さ、坂道の行き違い、カーブミラー(凸面鏡)の像の大きさ・距離と速さの見誤り・像の左右・道の上で映る範囲と死角)。

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
import driveenv
import driveinf
import drivetraffic
import drivedecide
import drivelateral
import drivecrossing
import drivepass
import drivelong
import drivettc
import gsplatnp
import motionio
import drivehumanoid
import agvfleet
import carlabridge
import drivetown
import drivejapan
import driveplateau
import drivecommonroad
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
        "kendama": kendama, "kendamaworld": kendamaworld, "gsplatnp": gsplatnp, "motionio": motionio, "drivehumanoid": drivehumanoid, "agvfleet": agvfleet, "carlabridge": carlabridge, "drivetown": drivetown, "drivejapan": drivejapan, "driveplateau": driveplateau, "drivecommonroad": drivecommonroad, "drivelong": drivelong, "driveenv": driveenv, "driveinf": driveinf, "drivetraffic": drivetraffic, "drivedecide": drivedecide, "drivelateral": drivelateral, "drivecrossing": drivecrossing, "drivepass": drivepass}

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
        ("fit_spin", "ballistics", ["signal", "points", "table"], "table"),
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
        ("spin_from_marker_sequence", "balltrack", ["any"], "table"),
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
        # 3DGS のファイル(.ply = INRIA 形式 / .splat)を読む入口(2026-10-03、Studio の D&D から)
        ("gs_read_file", "gsplatnp", [], "table"),
    ],
    # 動きのデータの入口(2026-10-03、Studio の D&D から): BVH のモーションキャプチャ(順運動学まで)と、イベントカメラの
    # (x, y, t, p)(列の順は見出しか中身で決める)→ 極性つきのコマ。真値 = 手で計算できる骨格・全極性の和の保存。
    "motion_io": [
        ("read_bvh", "motionio", [], "table"),
        ("read_events", "motionio", [], "table"),
        ("events_to_frames", "motionio", ["table"], "voxel"),
    ],
    # 運転の世界を歩くヒューマノイド(2026-10-03): 実在ロボットの MJCF から 1 周期の歩行を作り(humanoid_walk_clip、mujoco が
    # 要るので台帳の外・facade だけ)、再生は numpy。見た目 = 格子で間引いたメッシュ(LiDAR・深度)か、向き × 位相ごとの
    # マスク付きの事前描画(カメラ画像、1 体 数 ms)。当たり判定は外形の箱(車ほどの正確さは要らない)。
    # 真値 = 間引きのずれ ≤ √3·格子幅(定理)、事前描画と直接の描画のマスクの一致、手前の物に隠れること。
    "humanoid": [
        ("humanoid_clip_mesh", "drivehumanoid", ["table"], "table"),
        ("world_pose_humanoid", "drivehumanoid", ["table"], "any"),
        ("humanoid_impostors", "drivehumanoid", ["table"], "table"),
        ("world_camera_impostors", "drivehumanoid", ["table", "matrix", "matrix"], "table"),
    ],
    # 工場・倉庫の AGV の群れ(2026-10-03): 床の格子(bool の占有格子 = image2d、True = 走れる)の上の複数台の経路計画
    # (CBS = 最適 / 焦点探索 = 最適の w 倍以内 / 結合 A* = 第 2 実装 / 優先度付き = 不完全)と、遅れても詰まらない実行
    # (行動依存グラフ ADG)、計画を VDA 5050 の order にして仕様の規則で検査する。計画・結果・order は dict / list = table。
    # 真値 = CBS と結合 A* の総コストの一致、焦点探索 ≤ w·最適、ADG は遅れを入れても衝突 0・デッドロック 0(Hönig ら 2019)。
    "agv": [
        ("warehouse_grid", "agvfleet", [], "any"),
        ("grid_distances", "agvfleet", ["image2d"], "image2d"),
        ("mapf_cbs", "agvfleet", ["image2d"], "table"),
        ("mapf_ecbs", "agvfleet", ["image2d"], "table"),
        ("mapf_joint_astar", "agvfleet", ["image2d"], "table"),
        ("mapf_prioritized", "agvfleet", ["image2d"], "table"),
        ("plan_conflicts", "agvfleet", ["table"], "table"),
        ("plan_cost", "agvfleet", ["table"], "scalar"),
        ("adg_build", "agvfleet", ["table"], "table"),
        ("adg_execute", "agvfleet", ["table"], "table"),
        ("naive_execute", "agvfleet", ["table"], "table"),
        ("vda5050_order", "agvfleet", ["table"], "table"),
        ("vda5050_check", "agvfleet", ["table"], "table"),
    ],
    # 外部の高写実シミュレータ(CARLA 0.9.16)の撮影記録を自前の世界の規約に写す橋(2026-10-04、集大成の最初の部品)。numpy だけで動く —— CARLA の
    # パッケージもサーバも要らず、repo の外の撮影記録(npz = table)だけを読む。規約 = 左手系 → 右手系の鏡映(R_f = M R_c M)、CARLA のカメラ
    # (+x を見る)→ render3d のカメラ(−z を見る)、主点の 0.5 画素、24 bit の深度の復号式、29 タグ → 14 ラベル。真値 = CARLA の客体が返した
    # 回転行列(焼き込み)、look_at との一致、往復の恒等(深度は量子化 1 段以内)、自前の世界 → 記録 → 描き直しが画素単位で同じ、
    # 記録の姿勢から閉形式で出した後ろ面までの距離と深度の中央値の一致、車の画素数 ∝ 1/d²。
    "carla": [
        ("carla_labels", "carlabridge", [], "table"),
        ("carla_label_map", "carlabridge", ["image2d"], "image2d"),
        ("carla_label_unmap", "carlabridge", ["image2d"], "image2d"),
        ("carla_depth_decode", "carlabridge", ["rgb"], "image2d"),
        ("carla_depth_encode", "carlabridge", ["image2d"], "rgb"),
        ("carla_intrinsics", "carlabridge", [], "matrix"),
        ("intrinsics_to_fullseye", "carlabridge", ["matrix"], "matrix"),
        ("intrinsics_to_carla", "carlabridge", ["matrix"], "matrix"),
        ("carla_rotation_matrix", "carlabridge", [], "matrix"),
        ("carla_rotation_angles", "carlabridge", ["matrix"], "any"),
        ("carla_transform_matrix", "carlabridge", ["any"], "matrix"),
        ("carla_pose_to_world", "carlabridge", ["any"], "matrix"),
        ("world_pose_to_carla", "carlabridge", ["matrix"], "any"),
        ("carla_camera_pose", "carlabridge", ["any"], "matrix"),
        ("camera_pose_to_carla", "carlabridge", ["matrix"], "any"),
        ("carla_xy_yaw", "carlabridge", ["any"], "any"),
        ("carla_scene_check", "carlabridge", ["table"], "table"),
        ("carla_scene_load", "carlabridge", ["any"], "table"),
        ("carla_scene_save", "carlabridge", ["table"], "any"),
        ("carla_scene_synthetic", "carlabridge", [], "table"),
        ("carla_scene_world", "carlabridge", ["table"], "table"),
        ("carla_scene_render", "carlabridge", ["table"], "table"),
        ("lead_truth_depth", "carlabridge", ["table"], "scalar"),
        ("lead_from_depth", "carlabridge", ["image2d", "image2d", "matrix"], "table"),
        ("scene_pair_table", "carlabridge", ["table"], "table"),
    ],
    # 町を 1 つに組む(2026-10-04、集大成の土台): 教習所の要素を自動で継ぐ(要素 k+1 の entry を要素 k の exit に、配置 p = target ∘ entry⁻¹)、
    # 1 本の中心線、流入車線の停止線、縦だけの通し走行(先の停止線を止まっている先行車と見なす IDM)、通しの採点、教則 159 場面の台帳の集計、
    # 法規パック(JP = 左・踏切は常に停止 + 確認 / US・DE = 右・警報中だけ、JP 以外は一次確認なし = verified False)、踏切の設備(遮断機つき警報機・遮断かん・列車)を
    # drivecrossing の状態機械(警報 → 降下 → 遮断 → 上昇)で動かす。
    # 真値 = 継ぎ目の位置差 = overlap・向きの差 0(閉形式)、総延長 = Σ centerline_length − overlap × 継ぎ目数、台形則の ∫v dt = s、
    # 制動距離 ≥ v²/(2b)、drivecrossing.crossing_stop_check を実際に呼ぶ、同じ指令を drivelong.long_simulate(RK4)に渡した第 2 実装。
    "town": [
        ("town_chain", "drivetown", ["any"], "table"),
        ("town_layout", "drivetown", [], "table"),
        ("town_world", "drivetown", ["table"], "table"),
        ("town_centerline", "drivetown", ["table"], "any"),
        ("town_stop_lines", "drivetown", ["table"], "table"),
        ("town_rules", "drivetown", [], "table"),
        ("town_crossing_state", "drivetown", ["table"], "table"),
        ("town_run", "drivetown", ["table"], "table"),
        ("town_checks", "drivetown", ["table", "table"], "table"),
        ("kyosoku_summary", "drivetown", [], "table"),
    ],
    # 実在の日本の町(2026-10-04、「出来れば日本のマップで」): 道路網 = OpenStreetMap(ODbL)、建物 = 国交省 PLATEAU(CC BY 4.0)、道具立て = 道路標識令・
    # 交通規制基準の寸法(一時停止 330-A 一辺 80 cm、停止線 45 cm、「止まれ」240 × 80 cm × 3 字、横断歩道 45 cm の縞)。道路の形は幅つき線分の
    # ラスタ和集合を contours_xld の境界追跡でループにする(面積 = 画素数 × step² が厳密)。真値 = 等距円筒の閉形式、直線路の面積 L w + π(w/2)²、
    # 最短路の長さ・停止線の位置の閉形式、右側通行は鏡像、一方通行の遵守、PLATEAU の柱の体積 = 面積 × 高さ(発散定理)。
    "japan": [
        ("osm_synthetic", "drivejapan", [], "any"),
        ("osm_parse", "drivejapan", ["any"], "table"),
        ("osm_road_graph", "drivejapan", ["table"], "table"),
        ("osm_road_mask", "drivejapan", ["table"], "table"),
        ("osm_road_loops", "drivejapan", ["table"], "table"),
        ("osm_route", "drivejapan", ["table"], "table"),
        ("japan_world", "drivejapan", ["table"], "table"),
        ("japan_stats", "drivejapan", ["table"], "table"),
        ("latlon_to_local", "drivejapan", ["any", "any"], "any"),
        ("jp_sign_stop_mesh", "drivejapan", [], "any"),
        ("jp_crossbuck_mesh", "drivejapan", [], "any"),
        ("jp_pole_mesh", "drivejapan", [], "any"),
        ("jp_mirror_mesh", "drivejapan", [], "any"),
        ("jp_stop_marking_mesh", "drivejapan", [], "any"),
        ("jp_stop_marking_length", "drivejapan", [], "scalar"),
        ("citygml_synthetic", "driveplateau", [], "any"),
        ("plateau_parse", "driveplateau", ["any"], "table"),
        ("buildings_in_box", "driveplateau", ["table"], "any"),
        ("building_prisms", "driveplateau", ["any"], "any"),
        ("prism_mesh", "driveplateau", ["any"], "any"),
        ("triangulate_polygon", "driveplateau", ["any"], "any"),
        ("polygon_area", "driveplateau", ["any"], "scalar"),
    ],
    # 他人の場面 × 自分の運転手 × 他人の採点器(2026-10-04、「自作の罠を自分で解くのは限界」→ 真値・門・被験者の 1 つを外から): CommonRoad(TUM、BSD-3)の
    # 2020a シナリオを自前で読み、縦 IDM + pure-pursuit の運転手を KS 運動学(後軸、RK4、BMW_320i = parameters_vehicle2 の値)で走らせ、公式の solution XML を書き、
    # TUM drivability-checker(WSL、tools/check_solution_json.py)の合否 JSON を読む。真値 = KS の閉形式(直進・円 R = l_wb/tan δ)、採点器の第 2 実装(feasibility 2 cm・
    # SAT 衝突・道路境界)と公式の合否が正負の対照で一致。
    "commonroad": [
        ("cr_synthetic", "drivecommonroad", [], "any"),
        ("cr_read", "drivecommonroad", ["any"], "table"),
        ("cr_route", "drivecommonroad", ["table"], "table"),
        ("ks_step", "drivecommonroad", ["any", "any"], "any"),
        ("cr_drive", "drivecommonroad", ["table"], "table"),
        ("cr_drive_sweep", "drivecommonroad", ["table"], "table"),
        ("cr_feasible", "drivecommonroad", ["table"], "table"),
        ("cr_collision", "drivecommonroad", ["table", "table"], "table"),
        ("cr_solution_xml", "drivecommonroad", ["table", "table"], "any"),
        ("cr_checker_result", "drivecommonroad", ["any"], "table"),
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
    # 太陽と天気: 太陽の高度・方位(NOAA / Meeus、真値 = 国立天文台 暦計算室の公表値)、晴天の照度、Koschmieder の霧と視程(WMO の MOR)、
    # 路面の輝度の曲線から β を戻す(Hautière の考え方)、減能グレアの光幕(Stiles–Holladay / CIE)、灯火の色度が白に埋もれる閾値、
    # 見えてから止まれる速さ(drivelong の停止距離を v について解く)、物理の単位の描画(影 = 太陽のシャドウマップ、灯火は自発光、前照灯)。
    "env": [
        ("julian_day", "driveenv", ["any"], "scalar"),
        ("sun_at", "driveenv", ["any", "scalar", "scalar"], "table"),
        ("sun_events", "driveenv", ["scalar", "scalar", "scalar", "scalar", "scalar"], "table"),
        ("sun_vector", "driveenv", ["scalar", "scalar"], "any"),
        ("sun_illuminance", "driveenv", ["scalar"], "table"),
        ("koschmieder", "driveenv", ["any", "any", "scalar", "any"], "any"),
        ("mor_from_beta", "driveenv", ["scalar"], "scalar"),
        ("beta_from_mor", "driveenv", ["scalar"], "scalar"),
        ("road_row_distance", "driveenv", ["any", "scalar", "scalar", "scalar"], "any"),
        ("fog_beta_from_profile", "driveenv", ["any", "any", "scalar", "scalar", "scalar"], "table"),
        ("veiling_luminance", "driveenv", ["any", "any"], "any"),
        ("veil_chroma_limit", "driveenv", ["any", "scalar"], "scalar"),
        ("sight_stop_speed", "driveenv", ["scalar", "scalar", "scalar"], "scalar"),
        ("env_params", "driveenv", [], "table"),
        ("tone_map", "driveenv", ["any", "scalar"], "any"),
        ("env_render", "driveenv", ["table", "matrix", "matrix"], "table"),
    ],
    # 終わらない地図: 区画 (i, j) の中身は番号と世界の種だけで決まる(SplitMix64 のハッシュ)。道は辺の番号のハッシュで横切る位置を
    # 決めるので継ぎ目で必ずつながり、起伏は全体の整数格子の Perlin を区画の中の小数で補間(継ぎ目で連続・遠くでも桁が落ちない)。
    # 車の周り (2r+1)² 区画だけを持つ(tile_stream)。
    "inf": [
        ("tile_hash", "driveinf", [], "scalar"),
        ("tile_uniform", "driveinf", [], "scalar"),
        ("pose_normalize", "driveinf", [], "any"),
        ("tile_params", "driveinf", [], "table"),
        ("tile_edge_crossing", "driveinf", ["table"], "scalar"),
        ("tile_roads", "driveinf", ["table"], "table"),
        ("tile_road_distance", "driveinf", ["any", "any", "table"], "any"),
        ("tile_height", "driveinf", ["any", "any", "table"], "any"),
        ("tile_mesh", "driveinf", ["table"], "table"),
        ("tile_digest", "driveinf", ["table"], "any"),
        ("tile_stream", "driveinf", ["table", "table"], "table"),
        ("global_to_tile", "driveinf", [], "any"),
    ],
    # 動く交通参加者と死角: 追従は IDM(Treiber 2000、平衡車間の閉形式)、運転の癖は車ごとの母数と反応の遅れ、横ふらつきは OU 過程の
    # 厳密な離散化、歩行者は Social Force(Helbing & Molnar 1995)と横断の意図(真値)。死角から止まれる最大速度は停止距離の逆、
    # すれ違いは「はみ出す区間を抜ける時間」と対向車の到着の比較、飛び出しは非一様ポアソン(thinning)と重要度サンプリング。
    "traffic": [
        ("idm_accel", "drivetraffic", ["any"], "any"),
        ("idm_equilibrium_gap", "drivetraffic", ["any"], "any"),
        ("idm_platoon_simulate", "drivetraffic", ["any"], "table"),
        ("driver_style", "drivetraffic", [], "table"),
        ("lateral_wobble", "drivetraffic", [], "signal"),
        ("ou_estimate", "drivetraffic", ["signal"], "table"),
        ("social_force_step", "drivetraffic", ["points", "points", "points"], "any"),
        ("pedestrian_crossing", "drivetraffic", [], "table"),
        ("occlusion_reveal_distance", "drivetraffic", ["any"], "scalar"),
        ("occlusion_visible_intervals", "drivetraffic", ["any"], "any"),
        ("occlusion_safe_speed", "drivetraffic", ["any"], "any"),
        ("passing_gap_required", "drivetraffic", [], "table"),
        ("passing_decision", "drivetraffic", [], "any"),
        ("passing_simulate", "drivetraffic", [], "table"),
        ("bus_stop_rate", "drivetraffic", ["any"], "any"),
        ("poisson_events", "drivetraffic", ["any"], "signal"),
        ("poisson_events_xt", "drivetraffic", ["any"], "any"),
        ("importance_risk_estimate", "drivetraffic", ["any"], "table"),
    ],
    # 判断の場面: ミラーは鏡の向こうの仮想カメラ(反射 I − 2nnᵀ)、凸面鏡は鏡の縁で反射した光線で死角を囲む。確認の順序は
    # 教則の「ミラー → 合図(約 3 秒前 / 30 m 手前)→ 進路変更 → 合図をやめる」を丁運発第44号の点数で採点。信号は歩行者の青点滅から
    # 車両の黄を予測し、ジレンマゾーンは GHM(1960)と停止線の読みの両方。救急車はサイレンのドップラーと 2 本のマイクの到着時間差、
    # 赤色灯の点滅(カメラの fps で折り返す)、譲りは道交法 40 条、バスの発進は 31 条の 2 の「急に減速しないと譲れない」で採点。
    "decide": [
        ("mirror_reflection_matrix", "drivedecide", [], "any"),
        ("mirror_virtual_camera", "drivedecide", ["any"], "table"),
        ("mirror_aim_normal", "drivedecide", [], "any"),
        ("convex_mirror_fov", "drivedecide", [], "table"),
        ("mirror_blind_zone", "drivedecide", [], "table"),
        ("check_sequence_score", "drivedecide", ["table"], "table"),
        ("signal_phase_plan", "drivedecide", [], "table"),
        ("signal_state", "drivedecide", ["table"], "any"),
        ("predict_amber_onset", "drivedecide", ["table"], "table"),
        ("dilemma_zone", "drivedecide", ["any"], "table"),
        ("flash_frequency", "drivedecide", ["signal"], "table"),
        ("aliased_frequency", "drivedecide", ["any"], "any"),
        ("siren_signal", "drivedecide", [], "table"),
        ("doppler_shift", "drivedecide", ["any"], "any"),
        ("doppler_track", "drivedecide", ["signal"], "table"),
        ("tdoa_bearing", "drivedecide", ["signal", "signal"], "table"),
        ("yield_maneuver_check", "drivedecide", ["table"], "table"),
        ("bus_departure_yield_check", "drivedecide", ["table"], "table"),
    ],
    # 横の運動: 摩擦円(√(ax² + ay²) ≤ μg)とカーブの限界速度・道路構造令の設計式、2 輪等価モデル(定常円旋回の舵角 = L/R + K·ay)、
    # 低速の内輪差(後輪の軌跡の閉形式)、クロソイド A² = RL、pure pursuit(κ = 2 sin α / Ld)と Stanley、前後 2 パスの速度計画、
    # TLC の閉形式、教則の左折(左端に寄り側端に沿って徐行)・右折(中央に寄り中心のすぐ内側)の採点。
    "lateral": [
        ("friction_circle_usage", "drivelateral", ["any"], "any"),
        ("curve_speed_limit", "drivelateral", ["any"], "any"),
        ("design_min_radius", "drivelateral", ["any"], "any"),
        ("understeer_gradient", "drivelateral", [], "table"),
        ("steady_cornering", "drivelateral", [], "table"),
        ("bicycle_model_step", "drivelateral", ["any"], "any"),
        ("ackermann_steer_angles", "drivelateral", ["any"], "table"),
        ("offtracking_circle", "drivelateral", [], "table"),
        ("rear_axle_path", "drivelateral", ["any"], "table"),
        ("fresnel_integrals", "drivelateral", ["any"], "any"),
        ("clothoid_points", "drivelateral", [], "table"),
        ("clothoid_design", "drivelateral", [], "table"),
        ("pure_pursuit_curvature", "drivelateral", ["any"], "table"),
        ("pure_pursuit_circle_offset", "drivelateral", [], "table"),
        ("stanley_steer", "drivelateral", ["any"], "table"),
        ("stanley_straight_decay", "drivelateral", [], "signal"),
        ("curvature_speed_plan", "drivelateral", ["any"], "table"),
        ("lateral_offset", "drivelateral", ["any"], "table"),
        ("time_to_line_crossing", "drivelateral", [], "scalar"),
        ("turn_maneuver_check", "drivelateral", ["table"], "table"),
    ],
    # 踏切と交差点の優先: 鉄道の解釈基準(警報→到達 遮断機つき 35 s・警報機だけ 30 s)と遮断機の状態機械、警報灯の交互点滅
    # (画素の時間周波数・カメラの fps の折り返し)、渡り切る時間と向こう側の余地(33 条・50 条 2 項)、見通し距離の閉形式、
    # 優先道路・広い道路と左方優先(36 条)、横断歩道の手前の停止車両・30 m 以内の追越し(38 条)、駐停車禁止の区間(44 条)。
    "crossing": [
        ("crossing_timing_check", "drivecrossing", [], "table"),
        ("crossing_gate_state", "drivecrossing", ["signal"], "table"),
        ("crossing_lamp_signal", "drivecrossing", [], "any"),
        ("lamp_pair_phase", "drivecrossing", ["signal", "signal"], "table"),
        ("crossing_clear_time", "drivecrossing", [], "table"),
        ("exit_room_check", "drivecrossing", ["any"], "table"),
        ("crossing_stop_check", "drivecrossing", ["table"], "table"),
        ("track_sight_distance", "drivecrossing", ["any"], "any"),
        ("sight_triangle_distance", "drivecrossing", [], "scalar"),
        ("priority_rule", "drivecrossing", ["table"], "table"),
        ("conflict_zone_intervals", "drivecrossing", ["any"], "table"),
        ("obstruction_decel", "drivecrossing", ["any"], "table"),
        ("crosswalk_overtake_check", "drivecrossing", ["table"], "table"),
        ("crosswalk_stopped_vehicle_check", "drivecrossing", ["table"], "table"),
        ("no_stopping_zones", "drivecrossing", ["table"], "table"),
        ("legal_stop_intervals", "drivecrossing", ["any"], "any"),
        ("parking_position_check", "drivecrossing", [], "table"),
    ],
    # 追越しと見えない所: 追越しの時間と対向車の境目・ルームミラーで戻る距離(28〜30 条・27 条・教則 5-6-3)、後続車に要る減速度と
    # 進路変更(26 条の 2)、環状交差点の優先と出口の合図(35 条の 2・37 条の 2・53 条 2 項)、凸形縦断曲線の視距(構造令の表を再現)、
    # 凸面鏡の見誤り・像の左右・道の上で映る範囲。
    "pass": [
        ("overtake_requirement", "drivepass", [], "table"),
        ("overtake_return_gap", "drivepass", [], "table"),
        ("no_overtaking_zones", "drivepass", ["table"], "table"),
        ("overtake_permitted", "drivepass", ["table"], "table"),
        ("overtaken_conduct_check", "drivepass", ["table"], "table"),
        ("lane_change_follower_decel", "drivepass", ["any"], "table"),
        ("lane_change_permitted", "drivepass", ["table"], "table"),
        ("roundabout_entry_check", "drivepass", ["table"], "table"),
        ("roundabout_signal_point", "drivepass", ["any"], "table"),
        ("roundabout_signal_check", "drivepass", ["signal", "signal"], "table"),
        ("crest_sight_distance", "drivepass", [], "table"),
        ("crest_safe_speed", "drivepass", ["any"], "table"),
        ("hill_meeting_yield", "drivepass", [], "table"),
        ("convex_mirror_image", "drivepass", ["any"], "table"),
        ("convex_mirror_misjudge", "drivepass", ["any", "any"], "table"),
        ("mirror_image_side", "drivepass", ["points"], "table"),
        ("mirror_road_coverage", "drivepass", [], "table"),
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
