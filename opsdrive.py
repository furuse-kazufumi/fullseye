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
柔らかい手首のペグ挿入(pegsim: Whitney の準静的幾何 —— 二点接触の深さ・くさび・かじり・面取りの許容 —— を門に、手首 RGB-D 1 枚から穴中心とペグ先端を 3-D で読む計測、真値つきの合成 RGB-D、MJCF。mujoco が要る場面・描画・接触・挿入は facade だけ)。
視触覚センサ(tacsim: Hertz 接触の閉形式 —— 接触半径・押し込み・圧力・半空間の表面変位 —— を真値に、弾性膜を 3 色照明で撮った像を合成し、フォトメトリックステレオで法線 → 接触半径と力を逆算。スロープ分布への Hertz 模型の当てはめ・模型なしのリング・δ の 1D 積分の 3 経路)。
マーカー配列のせん断(tacslip: Cattaneo–Mindlin の部分滑りを真値に、固着円・滑り環・接線力をマーカー追跡から逆算。接触円の外側は Cerruti 核の FFT 畳み込み、逆算は相似則で畳み込み 1 回。有限要素の節点変位で半空間が外れる半径を数に。マーカー中心の (N, 2) は matrix で運ぶ)。
触覚双極子 → 把持内トルク(tactorque: マーカー変位場の発散を電荷と見た双極子(arXiv 2404.15626 の再実装)で傾きトルク、剛体回転でねじり、平均で並進に分ける。真値 = Johnson 1985 の閉形式: 平頭押し込み子の圧 + 傾きモーメントの反対称項、Boussinesq 核、Gauss の恒等式 ∇·ū = −(1−2ν)p/2G(双極子 = 圧力の 1 次モーメント、形状不変)、Reissner–Sagoci のねじり。純せん断の漏れ (1−ν)/(1−2ν)·Q·R を窓で切る。有限要素では有限厚が膨らんで符号が逆)。
エアホッケーのパック追跡・予測・打ち返し(puck: 学習なし、全部ルール。真値 = Coulomb の等減速と壁の 2 つの反発係数の閉形式(区間ごとに繋ぐ、鏡映法と一致)、5 節リンクの FK/IK(円と円の交点)、第 2 実装 = 外部シムの台の MJCF(粘性減衰 c/m = 0.5 /s で Coulomb ではない、e・kₜ は測って出る)。合成の真上カメラ(被覆率の反エイリアス、モーションブラー = v·τ/2)、検出は balltrack の facade、速度は向き固定の最小二乗、打点計画は一定角速度の規則。リンク寸法・サーボ速度・打具半径・守備線は仮定)。
ペグ挿入の失敗検出と回復(pegfail: VLM の代わりに規則の分類表 12 行 × 接触計測。観測(接触の種別・深さの帯・停滞・くさびの境目・かじりの図の内外・穴中心からのずれ)を 6 欄の署名にし、当たる行は高々 1 つ、無ければ unknown(fail-closed)。真値 = Whitney 1982 のくさび θ > c/μ とかじりの平行四辺形(平面静力学から導き直して pegsim の頂点と一致)+ MuJoCo の接触と手首の力センサ。手首ばねのたわみから荷重を読む。失敗はわざと注入(ずれ・傾き・横目標・栓・囮)。回復は脚本のプリミティブ。mujoco が要る 3 本は facade)。
粉体の山を画像で測る(granular: 安息角・体積・質量・流動性・排出率を規則だけで。真値 = 円錐の閉形式、Beverloo 1961 の排出則、USP <1174> の流動性の表(Carr 1965)、1 mm ガラス球の公表値 25.2 ± 0.8 度(arXiv 2009.10448)、第 2 実装 = MuJoCo の剛体球の山。側面像は縁の画素の被覆率を副画素の位置に読む(列和法は粉の画素値のずれで tan φ が縮む罠)、高さ図は勾配ヒストグラムの最頻、傾いた基準面は左右差 ≈ 2β の警報。mujoco が要る 2 本は facade)。
視触覚センサの照明を実機の較正球で較正する(tacscalib: 既知球の法線の閉形式と手当ての接触円を真値に、線形 12 パラメタの照明模型(逆算は photometric_stereo = 被験者)と example-based の勾配 LUT(位置の 2 次式つき、行の少ないビンは近いビンの位置の項を借りて傾き 0〜15° の不感帯を消す、粗 → 細の逆引き)を 2 つの独立な経路にする。外部の位置 2 次 LUT の書式を読むアダプタつき。全部 numpy)。
ペグ挿入を 2 本指の膜で読む(pegtactile: 指先の弾性膜のせん断の像から、ペグが穴から受ける接触レンチ・Whitney の接触状態(一点 / 二点、止まった時のくさび / かじり)・壁の摩擦・手首剛性を学習なしの規則で。真値 = Whitney 1982 の二点接触の深さ l₂(θ) とくさびの境目 c/μ、Hertz・Cattaneo–Mindlin・Cerruti・無滑りねじりの閉形式、群の作用(同変性)、MuJoCo の接触と手首の力・トルクセンサ。膜は MuJoCo に無いのでパッド荷重は静力学の写像(把持の左右分配は対称の仮定)。くさびの境目ではレンチだけの規則が二点を口の一点と読む死角があり幾何の検査で解く。mujoco が要る 4 本は facade)。
食材の切断を画像で測る(cutting: 刃の追跡・切り込み深さ・切片の厚み・切断面の粗さ・柔らかい手首のたわみからの切断力を規則だけで。真値 = Atkins 2016 の摩擦なし slice/push の閉形式(H = ξV、H/Rw は ξ = 1 で最大 0.5、ξ = tan i)と Williams & Patel 2016 のくさび + 摩擦(μ = 0.2 で θo = 79°・最小 1.24)、合成の被覆率描画、MuJoCo の正射影カメラと手首の拘束力。厚みは画素を背景・食材・刃の 3 色に線形分解し、2 つの段の窓をぼけの推定で広げる。摩擦と刃角を含む slice/push の式は未読なので組み合わせは ValueError。合成の力も当てはめも同じ模型 = 配管の検査(自己申告)。mujoco が要る 1 本は facade)。
ディアボロの解析模型と視覚(diabolo: ロボット学習用の解析模型(arXiv:2011.09068)を LaTeX 原文から写し、原文どおりでは成り立たない所(式 1b の次元・状態遷移の帯の重なり・回転則の刻み依存)を直す。真値 = 閉形式(焦点の恒等式・振り子の周期・静止張力・放物線)、厳密な糸の模型(片側拘束の RATTLE)、第 2 実装 = MuJoCo の空間テンドン。視覚は学習なし: 光線追跡の合成映像から縁と底の板の 2 円の透視モーメントで軸、マーカーの位相と回転ぶれの弧で回転数、V 字で張力。棒の組は matrix (2, 3)、棒の時系列 (N, 2, 3) と棒の動きの指定(名前 / dict / 呼べる物)は any。mujoco が要る 1 本は facade)。

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
import pegsim
import tacsim
import tacscalib
import tacslip
import tactorque
import puck
import pegfail
import pegtactile
import granular
import cutting
import diabolo
import racket
import roadjp
import rsssafety

_MOD = {"drivecourse": drivecourse, "driveworld": driveworld, "lidarsim": lidarsim, "drivettc": drivettc,
        "rsssafety": rsssafety, "driveterrain": driveterrain,
        "ballistics": ballistics, "balltrack": balltrack, "ballworld": ballworld, "racket": racket,
        "roadjp": roadjp,
        "kendama": kendama, "kendamaworld": kendamaworld, "gsplatnp": gsplatnp, "motionio": motionio, "drivehumanoid": drivehumanoid, "agvfleet": agvfleet, "carlabridge": carlabridge, "drivetown": drivetown, "drivejapan": drivejapan, "driveplateau": driveplateau, "drivecommonroad": drivecommonroad, "drivelong": drivelong, "driveenv": driveenv, "driveinf": driveinf, "drivetraffic": drivetraffic, "drivedecide": drivedecide, "drivelateral": drivelateral, "drivecrossing": drivecrossing, "drivepass": drivepass, "pegsim": pegsim, "tacsim": tacsim, "tacslip": tacslip, "tactorque": tactorque, "puck": puck, "pegfail": pegfail, "granular": granular, "tacscalib": tacscalib, "pegtactile": pegtactile, "cutting": cutting, "diabolo": diabolo}

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
    # 柔らかい手首のペグ挿入(2026-10-04、物理シミュ × Fullseye 系列の第 1 弾): 真値 = Whitney 1982 の準静的幾何(著者本人の OCW 2.875
    # Class 3 スライドの式、原著は未読)+ MuJoCo の接触。二点接触の深さは 3-D の円柱で厳密に l tan θ = 2R − r(cos θ + sec θ)(導出)、
    # 真の姿勢から接触点数を幾何だけで予測する第 2 実装、既知半径の円・円柱、反エイリアスの被覆率から副画素の縁、手首 RGB-D 1 枚から
    # 穴中心・ペグ先端・相対ずれ、真値つきの合成 RGB-D(解析的レイキャスト)、MJCF 文字列。mujoco が要る関数(場面・描画・接触・
    # 挿入・格子)は facade(fullseye.peg_*)だけで台帳には載せない(humanoid_walk_clip と同じ)。
    "pegsim": [
        ("peg_params", "pegsim", [], "table"),
        ("whitney_clearance", "pegsim", ["table"], "table"),
        ("two_point_depth", "pegsim", ["table"], "scalar"),
        ("wedging_check", "pegsim", ["table"], "table"),
        ("jamming_diagram", "pegsim", ["table"], "table"),
        ("chamfer_capture", "pegsim", ["table"], "table"),
        ("contact_state_predict", "pegsim", ["table"], "table"),
        ("circle_fit_known_radius", "pegsim", ["matrix"], "table"),
        ("cylinder_fit_known_radius", "pegsim", ["points"], "table"),
        ("coverage_edge_points", "pegsim", ["image2d", "image2d", "image2d"], "matrix"),
        ("hole_centre_from_rgbd", "pegsim", ["rgb", "image2d", "matrix"], "table"),
        ("peg_tip_from_rgbd", "pegsim", ["rgb", "image2d", "matrix"], "table"),
        ("peg_offset_from_rgbd", "pegsim", ["rgb", "image2d", "matrix", "matrix"], "table"),
        ("peg_measure_overlay", "pegsim", ["rgb", "matrix", "matrix"], "rgb"),
        ("camera_world_to_cv", "pegsim", ["matrix"], "table"),
        ("peg_synthetic_rgbd", "pegsim", ["table"], "table"),
        ("insertion_grid_summary", "pegsim", ["table"], "table"),
        ("peg_scene_mjcf", "pegsim", ["table"], "any"),
    ],
    # 視触覚センサ = 弾性膜 + カメラ(2026-10-04、物理シミュ × Fullseye 系列の第 2 弾): 真値 = Hertz 接触の閉形式(Johnson 1985: a³ = 3FR/4E*、
    # δ = a²/R、p0√(1−r²/a²)、半空間の表面変位の内外解)+ Woodham 1980 のフォトメトリックステレオ + Frankot-Chellappa 1988 の積分。
    # 導出したのは外側のスロープ閉形式 (2/πR)[r arcsin(a/r) − a√(1−a²/r²)] と、それを法線場のスロープ分布に 1 パラメータ a で当てる逆算
    # (高さの積分を通らない)、δ の 1D 積分に Boussinesq の遠方場の裾を足す窓打ち切りの補正。合成は 3 色方向照明の Lambertian(各色 = 1 光源、
    # Johnson & Adelson CVPR 2009 の原理)。被験者は photometric 系 4 op と measure.fit_circle(第 2 実装)。全部 numpy、facade 不要。
    "tacsim": [
        ("combined_modulus", "tacsim", ["scalar", "scalar"], "scalar"),
        ("hertz_sphere", "tacsim", ["scalar", "scalar", "scalar"], "table"),
        ("hertz_force", "tacsim", ["scalar", "scalar"], "scalar"),
        ("hertz_cylinder", "tacsim", ["scalar", "scalar", "scalar"], "table"),
        ("hertz_surface_uz", "tacsim", ["matrix", "scalar", "scalar", "scalar"], "matrix"),
        ("hertz_pressure", "tacsim", ["matrix", "scalar", "scalar"], "matrix"),
        ("membrane_indent_sphere", "tacsim", ["table"], "table"),
        ("membrane_indent_shape", "tacsim", ["text", "scalar"], "table"),
        ("membrane_lights", "tacsim", ["scalar"], "matrix"),
        ("membrane_render_rgb", "tacsim", ["normalmap", "matrix"], "rgb"),
        ("membrane_recover", "tacsim", ["rgb", "matrix", "scalar"], "table"),
        ("contact_radius_ring", "tacsim", ["image2d", "scalar"], "table"),
        ("contact_radius_fit", "tacsim", ["normalmap", "matrix", "matrix", "scalar", "scalar"], "table"),
        ("contact_radius_fit_pixelwise", "tacsim", ["normalmap", "matrix", "matrix", "scalar", "scalar"], "table"),
        ("membrane_delta_from_normals", "tacsim", ["normalmap", "matrix", "matrix", "scalar"], "scalar"),
    ],
    # 視触覚のマーカー配列 → せん断場・固着/滑り(2026-10-04、物理シミュ × Fullseye 系列 第 2 弾の第 2 本): 真値 = Cattaneo–Mindlin の部分滑り
    # (Johnson 1985 §7.2: c/a = (1 − Q/μP)^{1/3}、q = q′ − q″、δx = 3μP(2−ν)/(16Ga)[1 − (1−Q/μP)^{2/3}]、kt = 8Ga/(2−ν))+ Hertz 形接線トラクションの
    # 円内解(式 3.91)+ 法線荷重の半径変位(式 3.41b)+ Cerruti の点荷重解(式 3.22)、第 2 真値 = 有限要素の節点変位(有限厚ドーム、形だけ)。
    # 自分で作ったのは接触円の外側の接線変位(閉形式なし)を画素平均の Cerruti 核で FFT 畳み込みすること、任意の固着半径の場を相似則
    # g(x) − (c/a)²g(x·a/c) で出す逆算模型(畳み込み 1 回)、変位で中心を移してから描くマーカー像、縁から連続性で伸ばす対応(規則格子の
    # エイリアス対策)、反復ガウス重みの重心(pixel-locking 対策)。被験者は blob2d / pivops / backends_subpix / tac_shear_field。全部 numpy + scipy。
    "tacslip": [
        ("mindlin_partial_slip", "tacslip", ["scalar", "table", "scalar", "scalar", "scalar"], "table"),
        ("mindlin_traction", "tacslip", ["matrix", "table"], "matrix"),
        ("hertz_surface_ur", "tacslip", ["matrix", "scalar", "scalar", "scalar", "scalar"], "matrix"),
        ("hertzian_tangential_inner", "tacslip", ["matrix", "matrix", "scalar", "scalar", "scalar", "scalar"], "table"),
        ("cerruti_kernel", "tacslip", ["scalar", "scalar", "scalar", "scalar"], "table"),
        ("cerruti_surface_displacement", "tacslip", ["matrix", "table"], "table"),
        ("membrane_shear_field", "tacslip", ["table", "table", "matrix", "matrix", "table"], "table"),
        ("membrane_markers", "tacslip", ["scalar", "scalar"], "matrix"),
        ("displace_markers", "tacslip", ["matrix", "matrix", "matrix", "scalar"], "matrix"),
        ("membrane_render_markers", "tacslip", ["rgb", "matrix", "scalar", "scalar"], "rgb"),
        ("marker_image", "tacslip", ["rgb", "rgb"], "image2d"),
        ("marker_detect", "tacslip", ["image2d", "scalar", "scalar"], "table"),
        ("marker_match_grow", "tacslip", ["matrix", "matrix", "scalar"], "table"),
        ("marker_track", "tacslip", ["image2d", "image2d", "scalar", "scalar", "scalar"], "table"),
        ("mindlin_model", "tacslip", ["table", "matrix", "matrix", "table", "scalar", "scalar"], "table"),
        ("mindlin_fit", "tacslip", ["table", "matrix", "matrix"], "table"),
        ("mindlin_fit_vector", "tacslip", ["table", "matrix", "matrix"], "table"),
        ("stick_radius_modelfree", "tacslip", ["matrix", "matrix"], "table"),
        ("slip_entropy", "tacslip", ["signal"], "scalar"),
        ("fem_nodes_load", "tacslip", ["text", "text"], "table"),
        ("fem_vs_halfspace", "tacslip", ["table", "table"], "table"),
    ],
    # 触覚双極子 → 把持内トルク(2026-10-04、物理シミュ × Fullseye 系列 第 2 弾の第 3 本): 論文(Fuchioka & Hamaya, ICRA 2024, arXiv 2404.15626)の
    # 式 4–11 を再実装(学習なし・光学模型なし。著者のコードは無ライセンスなので読まず、本文の式だけから)。真値 = Johnson 1985 の閉形式: 平頭押し込み子の
    # 圧 p = P/(2πa√(a²−r²))(式 3.34)+ 傾きモーメントの反対称項 3Mx/(2πa³√(a²−r²))(∫x p dA = M、導出)、Boussinesq の点荷重解(§3.2)、Hertz 圧の表面変位
    # (3.41b・3.42a)、楕円 Hertz 圧(4.24)、無滑りねじり(Reissner–Sagoci)q_θ = 3M_z r/(4πa³√(a²−r²))・β = 3M_z/(16Ga³)。自分で導いたのは Gauss の法則が
    # 半空間で恒等式になること ∇·ū = −(1−2ν)p/(2G)(双極子 = 圧力の 1 次モーメント × 係数、押し込み子の形に依らない)、Cerruti 点荷重の場の発散 −(1−ν)Qx/(2πGr³)
    # (純せん断が窓全体に偽の傾き (1−ν)/(1−2ν)·Q·R を作る → 窓を固着円に限る)、基線形式(|u| を電荷に)が対称な傾きで恒等的に 0 になること。
    # 第 2 真値 = 有限要素の節点変位(有限厚ドーム、tacslip.fem_nodes_load): 有限厚は膨らんで符号が逆、斜め荷重の双極子はせん断漏れの符号。全部 numpy + scipy。
    "tactorque": [
        ("punch_pressure", "tactorque", ["matrix", "matrix", "scalar", "scalar"], "matrix"),
        ("punch_surface_uz", "tactorque", ["matrix", "scalar", "scalar", "scalar", "scalar"], "matrix"),
        ("hertz_pressure_shifted", "tactorque", ["matrix", "matrix", "table"], "matrix"),
        ("ellipse_pressure_shifted", "tactorque", ["matrix", "matrix", "scalar", "scalar", "scalar"], "matrix"),
        ("pressure_first_moment", "tactorque", ["matrix", "matrix", "matrix", "scalar"], "table"),
        ("boussinesq_kernel", "tactorque", ["scalar", "scalar", "scalar", "scalar"], "table"),
        ("boussinesq_surface_displacement", "tactorque", ["matrix", "table"], "table"),
        ("surface_divergence_closed_form", "tactorque", ["matrix", "scalar", "scalar"], "matrix"),
        ("tilt_shear_field", "tactorque", ["matrix", "matrix", "table"], "table"),
        ("torsion_stick_field", "tactorque", ["matrix", "matrix", "scalar", "scalar", "table", "scalar"], "table"),
        ("marker_divergence", "tactorque", ["matrix", "matrix", "scalar"], "table"),
        ("rigid_rotation_fit", "tactorque", ["matrix", "matrix"], "table"),
        ("tactile_dipole_moment", "tactorque", ["matrix", "matrix"], "table"),
        ("dipole_to_torque_fit", "tactorque", ["signal", "signal"], "table"),
        ("torque_decompose", "tactorque", ["matrix", "matrix", "scalar", "scalar", "scalar"], "table"),
        ("dipole_torque_resolution", "tactorque", ["matrix", "matrix", "scalar", "scalar", "scalar", "scalar", "scalar"], "table"),
        ("grasp_torque_frame", "tactorque", ["image2d", "image2d", "scalar", "scalar", "scalar", "scalar", "scalar", "scalar"], "table"),
    ],
    # エアホッケーのパック追跡・予測・打ち返し(2026-10-04、物理シミュ × Fullseye 系列 第 3 弾): 低価格のエアホッケーロボット(Shinjo ほか、IROS 2024、
    # doi 10.1109/iros58592.2024.10801458)の鎖 カメラ → 検出 → 速度 → 予測 → 5 節リンクの計画 を学習なしで。真値 = 閉形式(Coulomb の等減速 a = μg、壁は
    # 法線 −e・接線 kₜ: 記法は Cross 2022 doi 10.1088/1361-6404/ac4b47、Spong 2001 の衝突模型は未読で未検証)、5 節リンクの FK∘IK 恒等、第 2 実装 = Robot Air
    # Hockey Challenge の台の MJCF(Liu ほか arXiv 2411.05718、MIT、repo に同梱せず FULLSEYE_AIRHOCKEY_DATA の下)—— 読んで分かったのは減速が粘性減衰
    # c/m = 0.5 /s(Coulomb ではない)で、壁の e・kₜ は軟接触から測って出ること。自前の Coulomb 版 MJCF(文字列、mujoco 不要)も持つ。2-vector(p, v, q, E)は
    # signal、(N,2) は matrix、コマは image2d、コマ列は any。mujoco が要る 2 本(puck_challenge_mjcf / puck_mujoco_run)は facade だけで台帳には載せない。
    "puck": [
        ("puck_table", "puck", [], "table"),
        ("puck_wall_bounce", "puck", ["signal", "signal", "scalar", "scalar"], "table"),
        ("puck_slide_predict", "puck", ["signal", "signal", "table", "scalar"], "table"),
        ("puck_state_at", "puck", ["table", "signal"], "table"),
        ("puck_crossing_point", "puck", ["table", "scalar"], "any"),
        ("puck_mirror_path", "puck", ["signal", "signal", "table", "scalar"], "signal"),
        ("puck_stop_distance", "puck", ["scalar", "table"], "scalar"),
        ("puck_camera", "puck", ["table"], "table"),
        ("puck_pinhole_camera", "puck", ["table", "scalar", "scalar", "signal"], "table"),
        ("puck_world_to_pixel", "puck", ["table", "matrix"], "matrix"),
        ("puck_pixel_to_world", "puck", ["table", "matrix"], "matrix"),
        ("puck_render_frame", "puck", ["table", "signal"], "image2d"),
        ("puck_synth_frames", "puck", ["table", "table", "signal", "signal"], "table"),
        ("puck_detect", "puck", ["image2d", "table"], "any"),
        ("puck_track", "puck", ["any", "table"], "table"),
        ("puck_velocity_estimate", "puck", ["signal", "matrix", "table"], "table"),
        ("puck_mu_from_decel", "puck", ["signal", "matrix"], "table"),
        ("puck_restitution_from_wall", "puck", ["signal", "matrix", "table"], "table"),
        ("fivebar_link", "puck", [], "table"),
        ("fivebar_fk", "puck", ["signal", "table"], "any"),
        ("fivebar_ik", "puck", ["signal", "table"], "any"),
        ("fivebar_workspace", "puck", ["table"], "table"),
        ("fivebar_reach_interval", "puck", ["table", "scalar"], "table"),
        ("striker_plan", "puck", ["any", "signal", "table"], "table"),
        ("fivebar_trajectory", "puck", ["signal", "table", "signal"], "matrix"),
        ("puck_scene_mjcf", "puck", ["table"], "any"),
    ],
    # ペグ挿入の失敗検出と回復(2026-10-04、物理シミュ × Fullseye 系列、pegsim の集大成): 先行研究(arXiv:2509.17666、ICRA 2026 予定)の VLM による
    # 失敗判定を規則の分類表に置き換える。観測 → 6 欄の署名 → 表引き(当たる行は高々 1 つ、無ければ unknown)→ 回復プリミティブ。真値 = Whitney 1982
    # (OCW 2.875 Class 3 スライド、原著未読: くさび θ > c/μ、かじりの平行四辺形 λ = l/(2rμ) を二点接触の平面静力学から導き直し pegsim と 1e-9)+
    # MuJoCo の接触・手首の力センサ(--full)。表・署名・走行の記録・要約は table(dict / list)、深さの列は signal、3-vector は signal、MJCF は文字列(any)。
    # mujoco が要る 3 本(pegfail_scene_build / pegfail_episode_run / pegfail_failure_grid)は facade だけで台帳には載せない。
    "pegfail": [
        ("insertion_failure_table", "pegfail", [], "table"),
        ("insertion_failure_validate", "pegfail", ["table"], "table"),
        ("insertion_signature", "pegfail", ["table", "table"], "table"),
        ("insertion_failure_classify", "pegfail", ["table"], "table"),
        ("insertion_recovery_primitive", "pegfail", ["any"], "table"),
        ("jamming_parallelogram_planar", "pegfail", ["table", "scalar"], "table"),
        ("jamming_force_check", "pegfail", ["table", "scalar", "scalar", "scalar"], "table"),
        ("wedging_risk", "pegfail", ["table", "scalar"], "table"),
        ("insertion_stall_detect", "pegfail", ["signal"], "table"),
        ("wrist_load_from_deflection", "pegfail", ["table", "signal", "signal", "signal", "signal", "signal"], "table"),
        ("tip_force_ratios", "pegfail", ["table", "signal", "signal", "signal"], "table"),
        ("insertion_episode_summary", "pegfail", ["table"], "table"),
        ("failure_confusion", "pegfail", ["any", "any"], "table"),
        ("vision_boundary_flip", "pegfail", ["table", "signal", "scalar"], "table"),
        ("insertion_failure_presets", "pegfail", ["table"], "table"),
        ("pegfail_scene_mjcf", "pegfail", ["table"], "any"),
    ],
    # 粉体の山を画像で測る(2026-10-05、物理シミュ × Fullseye 系列): 安息角・体積・質量・流動性・排出率を規則だけで。真値 = 円錐の閉形式、
    # Beverloo 1961 の排出則、USP <1174> Table 1(Carr 1965)、1 mm ガラス球の公表値 25.2 ± 0.8 度(Sunday ほか 2020、arXiv 2009.10448)、
    # 第 2 実装 = MuJoCo の剛体球の山。側面像(被覆率)と高さ図は image2d、合成の世界・計測の結果・MJCF の dict は table、
    # 球の中心 (n, 3) は matrix(点群の op に流すと意味が違う —— 山の選別と描画の入口だけが受ける)、陰影つきの絵は rgb、
    # 動画の高さ図の列はコマのリスト(any、型が違えば ValueError)。mujoco が要る 2 本(heap_mujoco_pour / heap_mujoco_discharge)は
    # facade だけで台帳には載せない。
    "granular": [
        ("heap_volume_cone", "granular", ["scalar", "scalar"], "table"),
        ("heap_mass", "granular", ["scalar", "scalar"], "scalar"),
        ("heap_volume_heightmap", "granular", ["image2d", "scalar"], "scalar"),
        ("beverloo_rate", "granular", ["scalar", "scalar", "scalar"], "scalar"),
        ("beverloo_fit", "granular", ["signal", "signal", "scalar", "scalar"], "table"),
        ("discharge_synth", "granular", ["scalar", "scalar", "scalar", "scalar", "scalar", "scalar"], "table"),
        ("dispense_mass_from_video", "granular", ["any", "scalar", "scalar", "signal"], "table"),
        ("hopper_discharge_rate", "granular", ["signal", "signal", "scalar"], "table"),
        ("spoon_tilt_critical", "granular", ["scalar", "scalar", "scalar"], "scalar"),
        ("spoon_tilt_dispense", "granular", ["scalar", "scalar", "scalar", "scalar"], "table"),
        ("powder_flowability_class", "granular", ["scalar"], "table"),
        ("heap_synth_cone", "granular", ["scalar", "scalar"], "table"),
        ("cone_profile_px", "granular", ["signal", "scalar", "scalar"], "signal"),
        ("repose_angle_silhouette", "granular", ["image2d"], "table"),
        ("repose_angle_heightmap", "granular", ["image2d", "scalar"], "table"),
        ("datum_tilt_check", "granular", ["table"], "table"),
        ("container_synth", "granular", ["scalar"], "table"),
        ("container_fill_level", "granular", ["image2d"], "table"),
        ("heap_spheres_select", "granular", ["matrix", "scalar", "scalar", "scalar"], "table"),
        ("spheres_to_heightmap", "granular", ["matrix", "scalar", "scalar", "scalar"], "image2d"),
        ("spheres_to_silhouette", "granular", ["matrix", "scalar", "scalar", "scalar", "scalar"], "image2d"),
        ("spheres_render_shaded", "granular", ["matrix", "scalar", "scalar", "scalar", "scalar"], "rgb"),
        ("heap_scene_mjcf", "granular", ["scalar", "scalar"], "table"),
    ],
    # 視触覚センサの照明を実機の較正球で較正する(2026-10-05、物理シミュ × Fullseye 系列、tacsim の続き): 真値 = 既知球の半径(接触円の内側で
    # 膜が球面にならう → 法線は閉形式、R は較正と評価の両辺に入る)+ 手当ての接触円(弱い真値)、データ = arXiv:2109.04027 の作者が MIT で
    # 公開した較正パック(FULLSEYE_TAXIM_DATA)。線形 12 パラメタの照明(order=2 で位置つき 72)と、example-based の勾配 LUT(θ・φ を
    # 125 × 125、位置の 2 次式つき)を独立な 2 経路に。自分で作ったのは「行の少ないビンが角度で最も近い多項式ビンの位置の項を借り定数項だけ
    # 自分の平均に合わせる」(試作の不感帯 0〜15° を消す)、距離を特徴の内積 1 回にする書き換え(|k|² = AᵀQA)、粗 → 細の逆引き
    # (総当たりと 9 割同じビン・角誤差の中央値の差 0.1° 以内を門に)、外部の位置 2 次 LUT の書式を同じ逆引きに通すアダプタ。
    # 較正パックの path は text、形・中心の組は any(型が違えば ValueError)、マスクは image2d、行の列 (P, 3) は matrix。全部 numpy。
    "tacscalib": [
        ("calib_pack_load", "tacscalib", ["text", "scalar", "scalar"], "table"),
        ("sphere_normals_known", "tacscalib", ["any", "any", "scalar", "scalar"], "table"),
        ("lights_fit_from_sphere", "tacscalib", ["rgb", "normalmap", "image2d"], "table"),
        ("membrane_predict_rgb", "tacscalib", ["normalmap", "table"], "rgb"),
        ("gradient_lut_build", "tacscalib", ["matrix", "matrix"], "table"),
        ("gradient_lut_invert", "tacscalib", ["rgb", "table", "image2d"], "normalmap"),
        ("normal_error_map", "tacscalib", ["normalmap", "normalmap"], "image2d"),
        ("sphere_cap_height", "tacscalib", ["any", "any", "scalar", "scalar", "scalar"], "table"),
        ("field_position_sweep", "tacscalib", ["matrix", "signal", "any"], "table"),
        ("poly_lut_invert", "tacscalib", ["rgb", "table", "image2d"], "normalmap"),
    ],
    # ペグ挿入を 2 本指の膜で読む(2026-10-05、物理シミュ × Fullseye 系列と視触覚 3 本の集大成): 膜の像 2 枚 → 接触レンチ → Whitney の
    # 接触状態・壁の μ・止まった時のくさび / かじり、手首カメラ × 触覚で手首剛性、形と装置の同変性。真値 = Whitney 1982(OCW 2.875 Class 3、
    # 原著未読)の l₂(θ) と c/μ、Johnson 1985 の閉形式(Hertz / Cattaneo–Mindlin / Cerruti / Reissner–Sagoci)、群の作用 + MuJoCo(--full)。
    # パッドの表・荷重・読み・状態・当てはめはどれも table(dict)、力とモーメントの 3-vector と q の 2-vector は signal、輪郭 (N, 2) は matrix、
    # 状態名・形の名は text、None を取りうる入力(接触点・μ̂)と呼べる物(render / op)は any(型が違えば ValueError)。
    # mujoco が要る 4 本(pegtactile_episode_run / pegtactile_prefetch / pegtactile_process_episode / pegtactile_cutaway_xml)は facade だけ。
    "pegtactile": [
        ("pad_params", "pegtactile", [], "table"),
        ("pad_context", "pegtactile", ["table"], "table"),
        ("peg_wrench_to_pad_loads", "pegtactile", ["signal", "signal", "table"], "table"),
        ("pad_loads_to_peg_wrench", "pegtactile", ["scalar", "signal", "scalar", "signal", "table"], "table"),
        ("pad_shear_asymmetry", "pegtactile", ["signal", "signal"], "table"),
        ("pad_marker_displacement", "pegtactile", ["scalar", "signal", "table"], "table"),
        ("pad_tactile_frame", "pegtactile", ["scalar", "signal", "table"], "table"),
        ("pad_tactile_read", "pegtactile", ["table", "table"], "table"),
        ("contact_candidates", "pegtactile", ["table", "signal", "signal"], "table"),
        ("contact_state_from_wrench", "pegtactile", ["table", "signal", "signal", "signal", "signal", "signal"], "table"),
        ("two_point_forces", "pegtactile", ["table", "signal", "signal", "signal", "signal", "signal"], "table"),
        ("whitney_wrench", "pegtactile", ["table", "text", "scalar", "scalar", "scalar", "scalar"], "table"),
        ("friction_from_single_contact", "pegtactile", ["signal", "text", "any", "signal"], "table"),
        ("stall_verdict", "pegtactile", ["table", "scalar", "any"], "table"),
        ("wrist_stiffness_fit", "pegtactile", ["signal", "signal"], "table"),
        ("wrist_deflection_from_rgbd", "pegtactile", ["rgb", "image2d", "matrix", "matrix", "signal", "signal", "scalar"], "table"),
        ("symmetric_peg_shape", "pegtactile", ["text"], "image2d"),
        ("symmetry_order_contour", "pegtactile", ["matrix"], "table"),
        ("equivariance_check", "pegtactile", ["any", "any", "signal", "scalar", "signal"], "table"),
    ],
    # 食材の切断を画像で測る(2026-10-05、物理シミュ × Fullseye 系列、題材は arXiv:2404.02569): 刃の追跡・切り込み深さ・切片の厚み・
    # 切断面の粗さ・手首のたわみ → 力 → 靱性。真値 = Atkins 2016(式 1.1〜1.4)と Williams & Patel 2016(式 2.6)の閉形式と本文の数、
    # 合成の被覆率描画、MuJoCo の描画と手首の拘束力(--full)。正面像・刃先方向の像は rgb、場面・追跡・厚み・粗さ・力の結果は table、
    # 位置と力の列は signal、z_band は 2 要素の signal、端面の指定(数 / dict / (N, 2))と CSV のパス・ライセンスは any、MJCF は文字列(any)。
    # mujoco が要る 1 本(cutting_mujoco_wrist)は facade だけで台帳には載せない。
    "cutting": [
        ("cutting_scene", "cutting", ["any"], "table"),
        ("cutting_face_render", "cutting", ["table", "scalar", "scalar", "scalar"], "rgb"),
        ("cutting_edge_render", "cutting", ["table", "any", "scalar", "scalar", "scalar"], "rgb"),
        ("cutting_episode_synth", "cutting", [], "table"),
        ("cutting_wrist_mjcf", "cutting", ["table", "scalar"], "any"),
        ("knife_edge_track", "cutting", ["rgb"], "table"),
        ("cut_depth_from_side", "cutting", ["rgb", "table", "scalar", "scalar"], "table"),
        ("slice_thickness_profile", "cutting", ["rgb", "scalar", "scalar"], "table"),
        ("cut_surface_roughness", "cutting", ["rgb", "scalar", "scalar", "signal"], "table"),
        ("force_from_wrist_displacement", "cutting", ["signal", "signal", "scalar"], "signal"),
        ("cut_force_atkins", "cutting", ["scalar", "scalar"], "table"),
        ("slice_push_ratio", "cutting", ["scalar", "scalar", "scalar"], "scalar"),
        ("slice_push_from_track", "cutting", ["scalar", "signal", "signal"], "scalar"),
        ("food_cut_width", "cutting", ["scalar", "scalar", "scalar", "scalar"], "scalar"),
        ("cut_force_fit", "cutting", ["signal", "signal", "scalar"], "table"),
        ("cut_force_csv_load", "cutting", ["any", "any"], "table"),
    ],
    # ディアボロの解析模型と視覚(2026-10-05、物理シミュ × Fullseye 系列): 解析模型(arXiv:2011.09068、ICRA 2021)を原文から写して直し、
    # 閉形式・厳密な糸(RATTLE)・MuJoCo の空間テンドン(--full)で確かめる。合成映像から軸・回転・張力を読む(学習なし)。寸法・楕円体・状態・
    # 結果は table(dict)、点と速度は signal(3-vector)、棒の組は matrix (2, 3)、軌跡は matrix (N, 3)、棒の時系列と棒の動きの指定とコマの列は any、
    # 画像は rgb(float [0, 1])、MJCF は文字列(any)。mujoco が要る diabolo_mujoco_simulate は facade だけで台帳には載せない。
    "diabolo": [
        ("diabolo_params", "diabolo", [], "table"),
        ("diabolo_spheroid", "diabolo", ["signal", "signal", "scalar"], "table"),
        ("spheroid_closest", "diabolo", ["signal", "table"], "table"),
        ("diabolo_dynamics_step", "diabolo", ["table", "matrix", "matrix", "scalar", "table"], "table"),
        ("diabolo_simulate", "diabolo", ["signal", "signal", "any", "scalar", "scalar", "table"], "table"),
        ("diabolo_state_sequence", "diabolo", ["matrix", "any", "table"], "signal"),
        ("diabolo_throw_catch_truth", "diabolo", ["signal", "signal", "matrix", "table"], "table"),
        ("string_tension_static", "diabolo", ["scalar", "table"], "table"),
        ("string_tension_from_sag", "diabolo", ["signal", "signal", "signal", "scalar"], "table"),
        ("diabolo_camera", "diabolo", [], "table"),
        ("diabolo_render", "diabolo", ["table", "table"], "rgb"),
        ("diabolo_axis_from_image", "diabolo", ["rgb", "table", "table"], "table"),
        ("diabolo_marker_phase", "diabolo", ["rgb", "table", "table", "table"], "table"),
        ("diabolo_spin_from_markers", "diabolo", ["signal", "signal", "scalar", "scalar"], "table"),
        ("diabolo_track", "diabolo", ["any", "table", "table"], "table"),
        ("diabolo_scene_mjcf", "diabolo", ["table"], "any"),
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
