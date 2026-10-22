# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""RAD コーパス(raptor の corpus2skill 階層)から **op に繋がる文献層** ``docs/literature/`` を生成する。

Fullseye の RAG は op ノート(``docs/ops``)が本体で、その役目は **op を有効に使うための土台**であること
(ユーザー 2026-09-21「fullseye の RAG は op を有効に使うための土台になってないといけない」)。製造技術へ広げるときも
同じで、「設計 → 工程 → 検査」の周辺知識は**どの op を使うかに落ちて**初めて土台になる。この生成器は手元の RAD
コーパス(``<rad-root>/<name>_corpus_v2/``: ``INDEX.md`` + ``cluster_*/SKILL.md`` + 葉の ``docs/*.md``)を歩き、クラスタごとに

1. **使う op** —— 知識のテーマ(クラスタ名・葉の名前の語)から ``THEME_OPS`` の対応表で引いた**実在の op**と、その op を
   なぜ使うか(一行)。対応表は手で書いたもので、**op 名は生成時に出荷ノートの一覧(``fullseye/data/OP_NOTES.json``)と
   突き合わせ、無い名前があれば止まる**(改名・削除した op を指したまま公開しない)。テーマに当たらないクラスタは
   「op に落ちていない」と書き、INDEX でその数を数える(Fullseye に無い領域を隠さない)。
   ★語の一致(BM25)で op を引く案は試して捨てた(2026-09-21): 「design」「structure」のような一般語で 2 語一致した無関係の
   op(反応拡散・Sellmeier 係数…)が並び、土台どころか誤導になった。対応は人が書き、機械は実在だけを守る。
2. 要約(corpus2skill が LLM で書いた Overview と Key Knowledge —— 自前の生成文なので出荷できる)
3. 代表論文の **メタデータだけ**(題名・著者・年・DOI / URL・OpenAlex id。OpenAlex のメタデータは CC0。**抄録は写さない**
   (出版社の権利)、手元の絶対パスも書かない)

を 1 本の Markdown に落とし、末尾に **op → クラスタの逆引き**(その op がどの知識の文脈で出るか)を付ける。コーパス本体は
repo に無い(数千本・外部)ので **CHAIN には入れない**(``regen_all --list`` の「入れないもの」側)。生成物は commit し、
``tests/test_literature_notes.py`` が形(op リンクの実在・抄録なし・手元パスなし・件数の整合)を守る。

**厳選の層**(2026-10-13、``--curated``): 階層化(``*_corpus_v2``)していない生のコーパス(``<rad-root>/<corpus>/`` の
``papers/*.md`` + ``READING_ORDER.json``)からは、クラスタの要約が無い。そこで repo に **手で書いた目録**
(``docs/literature/curated/<name>.json``)を置き、軸ごとに (a) 抄録を読んで自分の言葉で書いた概観、(b) 使う op と
その理由、(c) 厳選した論文(古典 + 2020 年以降の有用なもの、DOI か OpenAlex id で指す)を持つ。生成器は目録の
論文をコーパスの本体(棄却側ではなく主題側)から引いてメタデータだけを写し、軸の件数はコーパスの
``READING_ORDER.json`` から数える。fail-closed: 目録の op が出荷ノートに無い / 論文がコーパスの主題側に無い・
その軸に当たっていない / 目録の手書き文にコーパスの抄録と 8 語以上一致する英語の並びがある(抄録の写し)/
目録に手元の絶対パスがある、のどれでも exit 1。``pending_ops`` は別の作業で実装中の op を足す口(出荷したら
名前を入れる。入れた名前も実在を検証する)。

使い方::

    py -3.11 tools/gen_literature_notes.py --rad-root C:/path/to/docs        # 既定 = 環境変数 FULLSEYE_RAD_DIR
    py -3.11 tools/gen_literature_notes.py --rad-root ... --corpus mech_design --max-papers 6
    py -3.11 tools/gen_literature_notes.py --rad-root ... --curated optical_metrology   # 厳選の層だけ
    py -3.11 tools/gen_literature_notes.py --restate-counts                              # 件数だけ打ち直す(コーパス不要)

**件数の古び(2026-10-18)**: INDEX の「op ノート N 本」は生成した日の数で、op を足すと古びる(3,307 のまま実際は 3,322 だった)。
本体の再生成にはコーパスが要るが件数は要らないので、``--restate-counts`` が docs/ops の実ファイルを数えて件数だけ直し、
``tools/gen_literature_counts.py`` が regen_all の鎖からそれを呼ぶ。``stated_count_problems()`` が実数との差を返し、
``tests/test_literature_notes.py`` が門にする。

fail-closed: rad-root が無い / コーパスが無い / クラスタが 1 つも読めない / op ノートが読めない / 対応表の op が実在しない
ときは exit 1(空の文献層・嘘の op リンクを黙って出さない)。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from collections import defaultdict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: 出荷するコーパスと、その説明(日本語は手で書く —— 生成器が自分を説明しない、の原則は要約の側だけ)
CORPORA = {
    "mech_design": {
        "title": "メカ設計(機械設計)",
        "what": "CAD 表現(パラメトリック・B-rep・CSG・SDF)、generative design・トポロジー最適化、DfAM・格子、公差解析・GD&T、"
                "機構合成・コンプライアント機構、歯車・軸受・ボルト、疲労・強度・FEA、材料選定、射出成形・板金の設計ルール、"
                "DFA/DFM、ロボット機構、逆設計(点群 → CAD)、スライス・工具経路。",
        "why": "設計 → スライス → 印刷 → 検査 → 再設計 の閉ループ(`printpath` と SDF/CSG の族、進化エンジン)の設計側の知識。",
    },
    "mechatronics_parts": {
        "title": "メカトロ部品(アクチュエータ・センサ・電気部品)",
        "what": "アクチュエータ各種(BLDC / ステッパ / サーボ / ハーモニック / サイクロイド / SEA / QDD / 油空圧 / ソフト / SMA / 圧電 / "
                "誘電エラストマ / ボイスコイル / リニア)、モータ制御(FOC・ドライバ・電流検出・エンコーダ)、センサ各種と校正・融合、"
                "電源 / BMS / パワエレ / DC-DC / ゲートドライバ / EMI / PCB、CAN / EtherCAT / RS-485 / I2C / SPI、組込み RTOS、FMEA、データシートの読み方。",
        "why": "Fullseye が受け取る信号・画像の**上流にある部品**の原理と選定。センサの族(`lightfield` / `photon` / `rangedoppler`)と"
               "`SENSOR_PLAYBOOK.md` の背景知識。制御・電気そのものは Fullseye の外で、**動きを画像で測る**側だけが op に落ちる。",
    },
    "manufacturing_processes": {
        "title": "製造工程(あらゆる製造技術の開発に)",
        "what": "切削・びびり・工具摩耗・面粗さ、研削・放電・レーザ、溶接ビード・欠陥、鋳造・鍛造・圧延・押出、射出成形・板金・粉末冶金、"
                "付加製造のメルトプール・in-situ 検出、複合材・熱処理・表面処理、はんだ・SMT・AOI、半導体・ウェハ・リソ・CMP、組立・CAPP、"
                "SPC・Cpk、デジタルツイン・予知保全。",
        "why": "工程ごとの「何を測れば品質が分かるか」。検査ワークフロー層・`spc` 族・3D 計測・`roughness` 族・振動の PoC の当て先。",
    },
    # ★2026-10-03: 運転の系列の集大成と「開かれた運転基盤」のために足した 2 分野。テーマ表は製造の表と分ける
    #   (共通の 1 枚に足すと、運転の「digital twin」が製造の予知保全の op に、製造の「reconstruction」が 3DGS に当たる)。
    "driving_simulation": {
        "title": "運転のシミュレーションと評価",
        "what": "シミュレータ(CARLA・MetaDrive・AWSIM・SUMO 連成・デジタルツイン)、シナリオに基づく試験(OpenSCENARIO・危険度指標・"
                "コーナーケース・危険シナリオ生成)、稀な事象の加速評価(重要度サンプリング)、閉ループ評価(nuPlan・NAVSIM・Bench2Drive)、"
                "ニューラル再構成(NeRF・3DGS)、sim-to-real(ドメインギャップ・悪天候・合成データの真値)。",
        "why": "運転 PoC の系列(`opsdrive` の 22 カテゴリ)を**評価の作法**につなぐ。どの量を真値で採点できるか、閉じた商用スタックが"
               "何を握っているか、自前の世界と CARLA を同じ場面で比べるときに何を測るか。",
        "themes": "drive",
    },
    "sensor_simulation": {
        "title": "センサーの模擬(カメラ・LiDAR・レーダー)",
        "what": "カメラの雑音(EMVA 1288)・ISP・HDR・LED のちらつき・レンズのフレアと周辺減光・ローリングシャッター・モーションブラー、"
                "LiDAR の強度と入射角・霧と降雪の減衰、レーダーの伝搬とドップラー、センサー模擬の検証。",
        "why": "自前の世界の描画を**物理で根拠づける**ための知識。各効果は閉形式の門が立つ(cos⁴ 減光・PTC の傾き・Koschmieder・"
               "LiDAR 方程式)ので、CARLA の写実と比べる前に Fullseye 側の正しさを固められる。",
        "themes": "drive",
    },
}

#: 厳選の層: 名前 → repo 内の目録(手で書いた JSON)。生のコーパス(v2 の階層なし)から論文を人が選ぶ。
CURATED = {
    "convergent_numerics_light_transport": "docs/literature/curated/convergent_numerics_light_transport.json",
    "electron_microscopy": "docs/literature/curated/electron_microscopy.json",
    "industrial_optical_sensing": "docs/literature/curated/industrial_optical_sensing.json",
    "optical_metrology": "docs/literature/curated/optical_metrology.json",
    "sensitivity_uq_calibration": "docs/literature/curated/sensitivity_uq_calibration.json",
}

#: 知識のテーマ(クラスタ名・葉の名前に出る語)→ 使う op と、その理由。**op 名は生成時に実在を検証**する。
#: 当たらない語は当てない(何でも紐づけると嘘になる)。docs 参照だけのテーマ(op 無し)は ops を空にし、doc に入口を書く。
#: 運転・センサーの分野のテーマ表(2026-10-03)。照合はクラスタ名と葉の名前の語。op 名は生成時に実在を検証する。
#: 当たる op が無い領域(無線光通信・言語モデルの運転)は ops を空にして「Fullseye の外」と正直に出す。
DRIVE_THEMES: list[dict] = [
    {"keys": ("rare", "importance", "sampling", "accelerated", "failure", "monte", "carlo", "markov", "event", "events", "mixture", "piecewise"),
     "theme": "稀な事象の加速評価(重要度サンプリング)",
     "ops": [("importance_risk_estimate", "発生率を上げて走らせ、重みで本来の事故率に戻す(不偏)"), ("poisson_events", "稀な事象を頻度つきで置く"),
             ("poisson_events_xt", "場所と時刻で変わる発生率 λ(x, t)"), ("bus_stop_rate", "停車中のバスの前後で上がる飛び出しの率")]},
    {"keys": ("scenario", "scenarios", "criticality", "critical", "testing", "test", "collision", "corner", "cases", "ads", "safety"),
     "theme": "シナリオ試験と危険度の指標",
     "ops": [("ttc_truth", "衝突までの時間の真値"), ("ttc_from_range", "距離の列からの TTC"), ("rss_longitudinal_check", "RSS の縦の安全距離"),
             ("rss_lateral_check", "RSS の横の安全距離"), ("dilemma_zone", "黄信号のジレンマゾーン(閉形式)"), ("occlusion_safe_speed", "死角から止まれる速さ"),
             ("turn_maneuver_check", "右左折の採点"), ("skill_test_score", "技能試験の減点")]},
    {"keys": ("traffic", "sumo", "cav", "cavs", "merging", "micro", "vehicular", "codrive", "management", "distributed"),
     "theme": "交通流と他車の振る舞い",
     "ops": [("idm_platoon_simulate", "IDM の車列"), ("idm_equilibrium_gap", "IDM の定常車間(閉形式)"), ("driver_style", "運転の癖を個体ごとに"),
             ("lateral_wobble", "車線内のふらつき"), ("lane_change_permitted", "進路変更の可否"), ("passing_decision", "すれ違いの判断"),
             ("social_force_step", "歩行者の Social Force")]},
    {"keys": ("simulator", "simulators", "simulation", "simulations", "autoware", "carla", "virtual", "digital", "twin", "twins", "sim2real", "interaction", "automation"),
     "theme": "自前の世界(真値つきの描画とセンサー)",
     "ops": [("world_build", "コースから 3-D の世界"), ("world_camera", "色・ラベル・深度・面番号を一度に"), ("world_move", "物体を動かす"),
             ("lidar_scan", "同じ世界の LiDAR"), ("env_render", "太陽・霧・雨・夜"), ("tile_stream", "終わらない地図"), ("gs_from_world", "世界 → 3DGS"),
             ("carla_scene_world", "CARLA の場面を自前の世界に(同じ場面を両方で)"), ("carla_depth_decode", "CARLA の深度画像(RGB 符号)を m に"),
             ("carla_transform_matrix", "CARLA の座標系(左手・度)↔ 自前の行列"), ("cr_read", "CommonRoad のシナリオ XML を読む"),
             ("cr_drive", "CommonRoad のシナリオを運転して採点"), ("osm_road_graph", "OSM の道路網から地図")]},
    {"keys": ("weather", "adverse", "fog", "rain", "snow", "snowfall", "precipitation", "ice", "icing", "cloud", "clouds", "conditions", "wind", "drop", "realweather"),
     "theme": "天候と視程(閉形式で根拠づける)",
     "ops": [("koschmieder", "視程と消散係数(Koschmieder)"), ("beta_from_mor", "気象光学距離 → 消散係数"), ("fog_beta_from_profile", "画像の明るさの縦断から霧の濃さ"),
             ("veiling_luminance", "まぶしさの光幕輝度"), ("sight_stop_speed", "見える距離で止まれる速さ"), ("env_params", "天候の母数")]},
    {"keys": ("lidar", "lidars", "laser", "intensity", "incidence", "angle", "point", "hsl", "railway"),
     "theme": "LiDAR(距離・強度・幾何)",
     "ops": [("lidar_spec", "走査の仕様"), ("lidar_scan", "世界を走査"), ("ray_plane_range", "平面までの距離(閉形式)"), ("ray_box_ranges", "箱までの距離(閉形式)"),
             ("project_spherical", "球面投影"), ("tof_multipath_phase", "凹みの多重反射で ToF の位相がずれる量(閉形式)"),
             ("tof_transport_depth", "輸送行列で多重反射を入れた ToF の深度")]},
    {"keys": ("radar", "fmcw", "doppler", "propagation", "ray"),
     "theme": "レーダー・ドップラー・音の到来方向",
     "ops": [("fmcw_range_profile", "FMCW の距離"), ("range_doppler_map", "距離・速度の地図"), ("doppler_shift", "ドップラーの閉形式"),
             ("doppler_track", "サイレンの周波数の追跡"), ("tdoa_bearing", "到着時間差から方向")]},
    {"keys": ("synthetic", "domain", "adaptation", "real", "realistic", "detection", "translation"),
     "theme": "sim-to-real の比較(同じ場面を対で測る)",
     "ops": [("psnr", "画素の差"), ("ssim", "構造の類似"), ("ms_ssim", "多段の構造類似"), ("ssim_map", "どこが違うかの地図"),
             ("fsim", "位相一致と勾配の知覚的類似(FSIM)"), ("gmsd", "勾配の類似の偏差(GMSD)"), ("vifp", "情報忠実度(VIFp)"),
             ("tid2013_evaluate", "指標を人の評価(TID2013)と順位相関で採点"), ("world_camera", "真値つきの対の描画")]},
    {"keys": ("nerf", "radiance", "neural", "gaussian", "splatting", "reconstruction", "reconstruct", "view", "views", "synthesis", "rendering", "occlusions", "fields"),
     "theme": "ニューラル再構成と 3DGS",
     "ops": [("gs_from_world", "メッシュの世界 → ガウス"), ("gs_render", "ガウスの描画"), ("gs_update", "ガウスの更新"), ("gs_read_file", "3DGS の読み込み"),
             ("humanoid_impostors", "向き × 位相の事前描画(安い代替)")]},
    {"keys": ("planning", "trajectory", "loop", "closed", "policy", "end", "reinforcement", "imitation", "expert", "motion", "navigation", "racing"),
     "theme": "計画と制御(ルールベースの側)",
     "ops": [("curvature_speed_plan", "曲率から速度の計画"), ("pure_pursuit_curvature", "pure pursuit"), ("stanley_steer", "Stanley"),
             ("stop_line_plan", "停止線までの計画"), ("long_simulate", "縦の運動"), ("bicycle_model_step", "自転車モデル")]},
    {"keys": ("shutter", "rolling", "blur", "deblurring", "stripes", "imu", "star"),
     "theme": "ローリングシャッターとブラー(閉形式)",
     "ops": [("aug_rolling_shutter", "ローリングシャッター(斜線の傾き = v·t_line)"), ("aug_motion_blur", "モーションブラー(スペクトルの零点)"),
             ("xkor_motion_blur", "第 2 実装のブラー")]},
    {"keys": ("isp", "signal", "noise", "camera", "sensors", "imaging", "cis", "scmos", "microscopy", "fluorescence", "measurement", "image", "images"),
     "theme": "カメラの雑音と ISP(EMVA 1288)",
     "ops": [("aug_shot_noise", "光子の雑音"), ("aug_read_noise", "読み出し雑音"), ("emva_snr_curve", "EMVA 1288 の SNR 曲線"),
             ("emva_photon_transfer", "光子伝達曲線(PTC)から利得と読み出し雑音"), ("emva_dark_current", "暗電流(露光時間の傾き)"),
             ("emva_spatial_nonuniformity", "DSNU / PRNU(固定パターン雑音)"), ("emva_dynamic_range", "ダイナミックレンジ"),
             ("raw_demosaic_bilinear", "デモザイク"), ("tone_map", "階調"), ("estimate_noise", "雑音の推定"), ("noise_sigma", "雑音の標準偏差")]},
    {"keys": ("hdr", "exposure", "flicker", "p2020", "lighting"),
     "theme": "HDR と LED のちらつき",
     "ops": [("tone_map", "HDR の階調圧縮"), ("deflicker", "ちらつきの除去"), ("flash_frequency", "点滅の周波数"), ("aliased_frequency", "フレームレートとのエイリアシング")]},
    {"keys": ("flare", "lens", "vignetting", "correction", "calibration", "optical", "oblique", "surfaces"),
     "theme": "レンズ(周辺減光・歪み・フレア・MTF)",
     "ops": [("aug_vignette", "cos⁴ の周辺減光"), ("vignette", "周辺減光"), ("distortion_map", "歪みの地図"), ("psf_to_mtf", "PSF → MTF"),
             ("sfr_from_edge", "斜めエッジから SFR(ISO 12233)"), ("mtf50", "解像の指標"), ("veiling_glare_index", "ベールグレアの指数")]},
    {"keys": ("communication", "wireless", "vlc", "positioning", "v2x", "nlos", "ultraviolet"),
     "theme": "通信(V2X・可視光通信)", "ops": []},
    {"keys": ("language", "video", "diffusion", "videos", "action", "future", "avatar", "continual", "intelligence", "learning"),
     "theme": "学習・生成の運転モデル(採点する側は上の門)", "ops": []},
]

THEME_OPS: list[dict] = [
    {"keys": ("point", "cloud", "clouds", "scan", "scanning", "registration", "reverse"), "theme": "点群 → 当てはめ → CAD(逆設計)",
     "ops": [("voxel_grid_downsample", "スキャン点群を等間隔に間引く"), ("statistical_outlier_removal", "外れ点を落とす"),
             ("estimate_normals", "法線(面の向き)"), ("icp_point2plane", "設計形状との位置合わせ"), ("register_fpfh", "初期姿勢の無い位置合わせ"),
             ("ransac_plane", "平面プリミティブの当てはめ"), ("ransac_cylinder", "円筒の当てはめ(穴・軸)"), ("fit_cone", "円錐"),
             ("poisson_lite", "点群 → メッシュ"), ("chamfer_distance", "設計との形状差"), ("hausdorff_distance", "最悪の形状差")]},
    {"keys": ("mesh", "meshes", "surface", "surfaces", "geometry", "geometric", "shape", "shapes"), "theme": "メッシュ・形状の計測と変換",
     "ops": [("mesh_area", "表面積"), ("mesh_volume", "体積"), ("vertex_curvature", "曲率(角・フィレット)"), ("decimate_qem", "間引き"),
             ("mesh_isotropic_remesh", "等方リメッシュ"), ("mesh_to_voxel", "メッシュ → 体積"), ("mesh_sample_points", "メッシュ → 点群"),
             ("shape_index", "局所形状の型"), ("d2_distribution", "形状の記述子(検索・比較)"),
             ("procrustes_distance", "位置・向き・大きさを除いた形の差"), ("shape_pca", "同種部品の形のばらつき(統計形状モデル)")]},
    {"keys": ("cad", "parametric", "csg", "sdf", "brep", "b-rep", "feature", "features", "sketch", "constraint", "constraints", "signed", "constructive", "solid", "implicit", "modeling"),
     "theme": "パラメトリック形状(SDF / CSG)",
     "ops": [("box_sdf", "直方体の SDF"), ("cylinder_sdf", "円筒の SDF"), ("capsule_sdf", "カプセル"), ("plane_sdf", "平面(切り欠き)"),
             ("sdf_union", "和"), ("sdf_subtract", "差(穴)"), ("sdf_intersect", "積"), ("sdf_smooth_union", "フィレットつきの和"),
             ("sdf_offset", "肉厚のオフセット"), ("sdf_to_occupancy", "SDF → 占有(スライスへ)"), ("grid_coords", "評価格子"),
             ("fit_superquadric", "スーパー二次曲面の当てはめ(逆設計)"), ("fit_bspline_surface", "自由曲面の当てはめ")]},
    {"keys": ("topology", "optimization", "generative", "surrogate", "evolutionary", "lattice", "structures", "structural", "porous", "cellular", "lightweight"),
     "theme": "トポロジー最適化・格子構造の評価",
     "doc": "進化エンジン(`docs/ENGINE.md`、`docs/EVOLUTION_ENVIRONMENT.md`)は設計パラメータを適応度で回す側",
     "ops": [("vol_euler_number", "連結性(閉じた空隙の数)"), ("vol_wall_thickness", "最小肉厚"), ("edt_jfa", "距離変換(肉厚・隙間)"),
             ("vol_granulometry", "空隙の大きさ分布"), ("mesh_volume", "体積(材料量)"), ("inertia_tensor", "慣性テンソル"),
             ("principal_moments", "主慣性モーメント")]},
    {"keys": ("additive", "printing", "printed", "slicing", "toolpath", "fused", "deposition", "overhang", "extrusion-based", "fdm", "slm"),
     "theme": "付加製造(スライス・G-code・層検査)",
     "ops": [("mesh_slice_contours", "メッシュを層の輪郭に"), ("mesh_slice_stack", "層マスクの積み"), ("contours_to_gcode", "輪郭 → G-code"),
             ("gcode_read", "G-code を線分の表に"), ("gcode_write", "表 → G-code"), ("gcode_layer_image", "層の期待画像"),
             ("gcode_extrusion_volume", "押し出し量"), ("gcode_time_estimate", "所要時間"), ("print_layer_defect_map", "層画像の欠け・はみ出し"),
             ("read_3mf", "3MF 読み"), ("write_3mf", "3MF 書き"), ("vol_wall_thickness", "造形物 CT の肉厚")]},
    {"keys": ("melt", "pool", "in-situ", "situ", "monitoring", "powder", "spatter", "bed"), "theme": "in-situ 監視(メルトプール・高速動画)",
     "ops": [("temporal_bandpass", "動画の時間帯域(揺らぎ)"), ("motion_magnify", "微小な動きの拡大"), ("video_spacetime_cube", "時空間の立方体"),
             ("video_summary_keyframes", "要約コマ"), ("blob_count", "スパッタ・粒の数"), ("area_center", "溶融池の面積と重心"),
             ("volseq_magnify_motion", "3D+t の拍動の拡大"), ("focus_sweep_height_video", "焦点掃引 → 高さの時系列")]},
    {"keys": ("tolerance", "tolerances", "gdt", "metrology", "dimensional", "measurement", "measurements", "inspection", "gauge", "accuracy", "precision"),
     "theme": "寸法・幾何公差の計測",
     "doc": "検査ワークフロー層(計測 → 仕様 → 根拠つき Verdict)",
     "ops": [("m1_measure_pos", "エッジ位置(1-D 計測)"), ("m1_measure_pairs", "対のエッジ = 幅"), ("edges_sub_pix", "サブピクセル輪郭"),
             ("fit_poly_surface", "面の当てはめ"), ("surface_form_error", "平面度・形状誤差"), ("ransac_plane", "基準面"),
             ("distance_point_plane", "点と面の距離(高さ)"), ("angle_between_planes", "面の角度"), ("annotate3d_measure", "3D の寸法の注記"),
             ("profile_params", "断面の粗さパラメータ"), ("surface_params", "面の粗さパラメータ"),
             ("measure_pos", "測定線上のエッジ位置(サブピクセル、HALCON measure_pos)"), ("measure_pairs", "エッジの対 = 構造の幅"),
             ("profile_deviation", "断面の設計形状からの法線方向のずれ"), ("profile_thickness", "断面の厚み分布")]},
    {"keys": ("injection", "molding", "moulding", "warpage", "shrinkage", "sink", "fault", "faults", "defect", "defects", "flaw", "anomaly", "anomalies"),
     "theme": "外観欠陥の検出(成形・表面)",
     "ops": [("dc_local_contrast_norm", "照明むらを除いた局所コントラスト"), ("dc_rpca_sparse", "背景から外れる疎な欠陥"), ("defect_contrast", "照明条件での欠陥コントラスト"),
             ("illumination_design", "欠陥が出る照明の設計"), ("lighting_sweep", "照明を振って最良を探す"), ("auto_threshold", "二値化"),
             ("blob_count", "欠陥の数"), ("circularity", "形の記述"), ("sfp_normals", "黒光沢・透明部品の法線を偏光から"),
             ("check_difference", "良品(基準)画像との差が許容を超える画素"), ("blob_features", "欠陥ごとの形の特徴量"),
             ("separate_touching", "接した粒・欠陥を分ける(watershed)"),
             ("pod_hitmiss_fit", "欠陥の大きさごとの検出確率(POD)"),
             ("varmodel_fit", "良品を並べて画素ごとの許容帯を作る(HALCON の variation model、誤検出率を宣言)"),
             ("varmodel_score", "許容帯の外の画素を、何 σ 外れたかと領域ごとに説明する"),
             ("anomaly_pro", "欠陥図の方法を、欠陥 1 つずつの重なり(PRO / AUPRO)で比べる"),
             ("solid_angle_sweep", "照射立体角を振って打痕・傷のコントラストの山を探す(V-ISA 型照明の立体角の設定)"),
             ("solid_angle_render", "照射立体角を絞る・広げる・ずらして、鏡面の打痕・ヘアラインの傷・梨地のムラを撮る")]},
    {"keys": ("sheet", "bending", "springback", "forming", "drawing", "stamping", "friction", "rolling"), "theme": "板金・成形(曲げ角・ひずみ)",
     "ops": [("strain_from_displacement", "DIC の変位 → ひずみ"), ("piv_deform_pass", "変形を追う相関"), ("correlation_quality", "相関の信頼度"),
             ("speckle_quality", "スペックルの良さ"), ("angle_between_planes", "曲げ角"), ("ransac_plane", "フランジ面"),
             ("fit_spline_curve", "曲げ線の当てはめ"), ("curvature_torsion", "曲線の曲率")]},
    {"keys": ("fatigue", "strength", "fea", "finite", "stress", "stresses", "crack", "cracks", "bolted", "joints", "joint", "fracture", "damage", "load", "loading"),
     "theme": "き裂・ひずみ・損傷の画像計測",
     "ops": [("strain_from_displacement", "全視野ひずみ"), ("piv_multipass", "多段の変位推定"), ("motion_magnify", "微小変形の拡大"),
             ("displacement_series", "変位の時系列"), ("vol_frangi", "CT 中の管状き裂の強調"), ("canny", "き裂のエッジ"),
             ("hessian3d", "3D の線状構造"), ("distance_ridge", "き裂の中心線")]},
    {"keys": ("weld", "welding", "welds", "bead", "penetration", "arc"), "theme": "溶接(ビード形状・溶け込み)",
     "ops": [("decode_fringe", "構造化光の縞を復号"), ("unwrap_phase_2d", "位相のアンラップ"), ("triangulate_column", "三角測量 → ビードの高さ"),
             ("fit_poly_surface", "母材面"), ("surface_form_error", "ビードの形状誤差"), ("specular_free_transform", "アークの映り込みを除く"),
             ("predict_fringe_phase_error", "溝の相互反射で縞の位相が外れる量を事前に"), ("triangulation_speckle_limit", "レーザ光切断の高さの床(スペックル)"),
             ("vol_wall_thickness", "CT の溶け込み深さ"), ("beam_hardening_correct", "金属 CT のアーチファクト")]},
    {"keys": ("casting", "cast", "solidification", "forging", "extrusion", "porosity", "void", "voids", "sintering", "metallurgy"), "theme": "鋳造・塑性加工・焼結(内部欠陥の CT)",
     "ops": [("filtered_backprojection", "CT 再構成"), ("sart_reconstruct", "少数投影の再構成"), ("beam_hardening_correct", "カッピングの補正"),
             ("ring_artifact_remove", "リングアーチファクト"), ("vol_label", "空隙のラベル"), ("vol_region_props", "空隙の性質"),
             ("filter_by_volume", "大きさで選別"), ("vol_granulometry", "空隙の大きさ分布")]},
    {"keys": ("machining", "milling", "turning", "chatter", "wear", "cnc", "grinding", "roughness", "finish", "tribology", "tool", "cutting"),
     "theme": "切削・研削(工具・面粗さ・びびり)",
     "ops": [("surface_filter", "粗さのフィルタ(うねりと分ける)"), ("surface_form_remove", "形状の除去"), ("profile_params", "Ra / Rz など"),
             ("surface_params", "Sa / Sq など"), ("surface_psd", "面のパワースペクトル"), ("stft", "びびりの時間周波数"),
             ("spectral_kurtosis", "衝撃性(工具欠損)"), ("order_spectrum", "回転次数のスペクトル"), ("angular_resample", "回転同期の再標本化"),
             ("cut_force_fit", "切断力の模型(Atkins)を力の列に当てはめる"), ("cut_surface_roughness", "切り口の粗さ"),
             ("gcode_read", "CNC の G-code も同じ語彙で読む")]},
    {"keys": ("laser", "discharge", "edm", "beam", "ablation", "plasma"), "theme": "レーザ・放電加工(光学)",
     "ops": [("gaussian_beam", "ビームの伝搬"), ("airy_pattern", "集光スポット"), ("depth_of_field", "焦点深度"),
             ("beer_lambert_transmittance", "透過率"), ("fresnel_dielectric", "反射率"), ("irradiance_map", "照度分布"),
             ("material_optical_constants", "加工材の n, k(材料表)"), ("speckle_statistics", "レーザ照明のスペックルの統計")]},
    {"keys": ("solder", "soldering", "reflow", "pcb", "smt", "aoi", "circuit", "board", "boards", "electronic"), "theme": "PCB / SMT の検査",
     "ops": [("ncc_locate", "部品の位置決め"), ("shape_locate", "形状マッチング"), ("edges_sub_pix", "はんだフィレットの輪郭"),
             ("illumination_design", "多方向照明の設計"), ("defect_contrast", "欠陥コントラスト"), ("dc_rpca_sparse", "異物・欠け"),
             ("fbp_volume", "X 線 CT(BGA のボイド)"), ("vol_granulometry", "ボイドの大きさ分布")]},
    {"keys": ("wafer", "wafers", "lithography", "semiconductor", "cmp", "polishing", "etch", "etching", "planarization", "die", "film", "films"),
     "theme": "半導体工程(ウェハ・薄膜)",
     "ops": [("csi_height_map", "白色干渉の高さ"), ("csi_envelope", "干渉包絡"), ("chromatic_confocal_height", "クロマティック共焦点"),
             ("surface_psd", "研磨面のスペクトル"), ("thin_film_reflectance", "薄膜の反射率"), ("dc_rpca_sparse", "パターン欠陥"),
             ("ncc_locate", "ダイの位置"), ("mtf_diffraction", "光学系の解像限界"), ("wavefront_stats", "波面収差"),
             ("preston_removal_map", "CMP・研磨の除去深さ(Preston の式)"), ("silicon_free_carrier_absorption", "ドープした Si の近赤外の吸収"),
             ("pl_image_simulate", "ウェハの PL 像(キャリア拡散で欠陥がどう見えるか)"), ("sem_render", "SEM 像の縁効果(Dice は高いのに面積が太る)"),
             ("sam_cscan", "接合のボイドを超音波(SAM)の位相で")]},
    {"keys": ("spc", "statistical", "capability", "cpk", "quality", "chart", "charts", "variability", "taguchi"), "theme": "SPC(管理図・工程能力)",
     "ops": [("spc_xbar_r", "X̄-R 管理図"), ("spc_cusum", "小さなずれの累積検出"), ("spc_ewma", "指数平滑の管理図"),
             ("spc_capability", "Cp / Cpk"), ("spc_hotelling_t2", "多変量の管理"), ("null_distribution", "帰無分布"), ("evidence_quantile", "証拠量の位置")]},
    # ★2026-10-15: 実験計画・応答曲面・品質工学・感度解析(opsmultivar)。鍵は製造のクラスタ名に実際に出る語
    #   (射出成形の「optimization」、加工の「optimization」「prediction」)—— 工程条件の最適化と予測は、文献では
    #   直交表・応答曲面・感度解析で回す領域。
    {"keys": ("optimization", "optimisation", "prediction", "doe", "experiments", "experimental", "taguchi", "sensitivity"),
     "theme": "実験計画法・応答曲面・品質工学・感度解析(工程条件の決め方)",
     "ops": [("doe_orthogonal_array", "直交表(L4〜L27、公表された表)で条件を少ない回数で振る"),
             ("doe_fractional_factorial", "一部実施要因計画(分解能と交絡表つき)"),
             ("doe_central_composite", "応答曲面のための中心複合計画"), ("doe_box_behnken", "角を踏まない応答曲面の計画"),
             ("doe_lhs", "シミュレーションの入力をラテン超方格で埋める"),
             ("doe_encode", "条件の記録を符号化(−1..+1)へ"), ("doe_decode", "計画を装置の設定値へ戻す"),
             ("doe_main_effects", "主効果の応答表(SN 比は参考、判断は平均と散らばり)"),
             ("rsm_fit", "応答曲面・分散分析・停留点(支えない次数は拒否)"),
             ("mv_pls", "条件 ⇔ 画像の特徴量の部分最小二乗(Q² と VIP)"),
             ("mv_pca", "特徴量の主成分と独立な次元の数"), ("feat_image_vector", "画像を名前と単位つきの特徴量の表に"),
             ("doe_morris", "効くつまみを少ない回数でふるう(Morris)"), ("sens_morris", "要素効果の μ* と σ"),
             ("doe_saltelli", "Sobol' 指数のための標本行列"), ("sens_sobol", "Sobol' の S1・ST(交互作用の分も)と信頼区間"),
             ("mv_confounding", "データから決まるパラメータの組(共線性指数)"),
             ("mv_residual_pca", "残差に残った構造 = モデルに足りないもの")]},
    # ★2026-10-15: sim-to-real 較正(opssimcal)。鍵はクラスタ名に実際に出る語(慣性センサ・力覚の「calibration」、
    #   鍛造・交通・レーダの「simulation」「modeling」)—— シミュレーションを実物に合わせる・センサを較正する領域。
    {"keys": ("calibration", "simulation", "simulations", "simulator", "modeling"),
     "theme": "sim-to-real 較正(実物の画像から物理モデルの係数を合わせ、決まらない係数には数を出さない)",
     "ops": [("simcal_model", "順方向の物理モデルとつまみ(単位・範囲・カメラの雑音モデル)を組む"),
             ("simcal_simulate", "つまみの値で模型を走らせて画像を作る"),
             ("simcal_observe", "実物の画像を位置合わせ・関心領域・露出の正規化をして模型に付ける"),
             ("simcal_screen", "どのつまみが雑音を越えて画像を動かすか・交絡しているか"),
             ("simcal_fit", "重みつき最小二乗で合わせ、決まらないつまみは数を出さずに拒否する"),
             ("simcal_identifiability", "Cramér-Rao 下界とプロファイル尤度で、決まるつまみか・上限しか言えないかを判定する"),
             ("simcal_uncertainty", "決まったつまみの区間(Laplace かブートストラップ)"),
             ("simcal_validate", "取り置いた画像で過適合の門(LOCKED は 1 回だけ)"),
             ("simcal_discrepancy", "残差 PCA でモデルの食い違いを見つけ、不確かさが楽観側だと注記する"),
             ("simcal_report", "較正の表 1 枚(走らせなかった検査は not run と書く)")]},
    # ★2026-10-15: 収束型の演算(opsconverge)。鍵はクラスタ名・葉の名前に実際に出る語(有限要素の「finite」= 格子の収束の検証、
    #   霧・散乱・光線の輸送の「fog」「scattering」「transport」= 多重散乱のモンテカルロ、描画の「rendering」= 相互反射を収束まで)。
    {"keys": ("finite", "fog", "scattering", "transport", "rendering"),
     "theme": "収束型の演算(多重反射・多重散乱・反復を収束まで回し、収束した証拠と残りの誤差を返す。収束しなければ値を出さない)",
     "ops": [("iterate_fixed_point", "相互反射や自己無撞着の式を不動点反復で解き(Anderson 加速)、収束しなければ拒否する"),
             ("conv_observed_order", "格子・反射回数・標本数を 3 段振った解から観測収束次数を出す"),
             ("conv_gci", "最も細かい解の離散化誤差を GCI で見積もる(シミュレーションの検証)"),
             ("mc_sequential_mean", "信頼区間が許容幅に入るまで標本を足し、使った標本数を返す"),
             ("mc_photon_slab", "濁った多層媒質の光子輸送(拡散反射・透過・吸収)を信頼区間つきで"),
             ("iv_richardson_lucy_until", "逆畳み込みを食い違い原理で止め、雑音の増幅を防ぐ")]},
    {"keys": ("twin", "predictive", "maintenance", "prognostic", "prognostics", "bearing", "bearings", "vibration", "vibrations", "condition", "health", "diagnosis", "fault diagnosis"),
     "theme": "予知保全(振動・軸受)",
     "ops": [("bearing_defect_frequencies", "軸受の欠陥周波数"), ("envelope_spectrum", "包絡スペクトル"), ("spectral_kurtosis", "衝撃の帯域"),
             ("ae_band_power", "アコースティック・エミッションの帯域パワー"),
             ("cepstrum", "ケプストラム"), ("order_spectrum", "次数スペクトル"), ("stft", "時間周波数"), ("spc_ewma", "劣化の監視"),
             ("motion_magnify", "動画からの振動"), ("phase_displacement", "位相ベースの変位")]},
    {"keys": ("sensor", "sensors", "sensing", "imu", "lidar", "tof", "time-of-flight", "camera", "cameras", "encoder", "calibration", "fusion", "inertial", "navigation", "localization", "slam", "odometry"),
     "theme": "センサ(校正・深度・融合)",
     "doc": "`docs/SENSOR_PLAYBOOK.md`",
     "ops": [("calibration_views", "校正板の合成ビュー"), ("distortion_map", "歪みの地図"), ("pnp_ransac", "外部パラメータ"), ("bundle_adjust", "多視点の同時最適化"),
             ("project_spherical", "LiDAR の球面投影"), ("depth_to_points", "深度 → 点群"), ("normals_from_depth", "深度 → 法線"),
             ("dtof_depth", "dToF の距離"), ("fmcw_range_profile", "FMCW レーダの距離"), ("range_doppler_map", "距離・速度の地図"),
             ("lf_depth_from_focus", "ライトフィールドの深度"), ("photon_uncertainty", "光子計数の誤差棒"), ("spad_deadtime_correct", "SPAD の不感時間補正"),
             ("emva_photon_transfer", "カメラの利得と雑音(EMVA 1288 の光子伝達)"), ("emva_quantum_efficiency", "量子効率"),
             ("silicon_photodiode_qe", "Si フォトダイオードの分光感度"), ("spectral_integral", "光源 × 対象 × センサの波長積分"),
             ("kalman_smooth", "観測の欠けた軌跡を前後から(Kalman 平滑化)")]},
    {"keys": ("tactile", "haptic", "haptics", "soft", "skin", "grasp", "grasping"), "theme": "触覚センサ(接触・圧力・ずれ)",
     "ops": [("tac_contact_mask", "接触域"), ("tac_pressure_proxy", "圧力の代理量"), ("tac_shear_field", "ずれ場"),
             ("tac_surface_normal", "接触面の法線"), ("tac_height_from_shading", "陰影からの高さ"),
             ("hertz_force", "Hertz 接触の力と押し込み(閉形式)"), ("contact_radius_fit", "接触半径から押し込み力"),
             ("mindlin_partial_slip", "部分すべり(Mindlin)の固着域"), ("marker_track", "膜のマーカーを追う"),
             ("membrane_shear_field", "マーカーの変位 → ずれ場"), ("torque_decompose", "ねじりと傾きのトルクを分ける"),
             ("gradient_lut_invert", "GelSight 型の色 → 法線の表引き"), ("large_deformation_inverse", "大変形の接触の逆問題")]},
    {"keys": ("motor", "motors", "actuator", "actuators", "actuation", "servo", "stepper", "brushless", "foc", "drive", "drives", "hydraulic", "pneumatic", "piezoelectric", "piezo", "electric", "control", "controller"),
     "theme": "アクチュエータ(制御は外、動きを画像で測る側)",
     "ops": [("displacement_series", "変位の時系列"), ("phase_displacement", "位相ベースの微小変位"), ("riesz_displacement_series", "Riesz 変換の変位"),
             ("temporal_band_power", "帯域ごとの動きの量"), ("band_snr", "動きの SN"), ("order_spectrum", "回転次数"), ("angular_resample", "回転同期"),
             ("piv_multipass", "流体(油空圧)の流れ場")]},
    {"keys": ("battery", "batteries", "bms", "power", "converter", "converters", "gate", "mosfet", "emi", "thermal", "cooling", "storage", "electrode", "electrodes", "charging"),
     "theme": "電源・電池(内部構造の CT)",
     "ops": [("fbp_volume", "電池 CT の再構成"), ("vol_wall_thickness", "電極・セパレータの厚み"), ("vol_label", "層のラベル"),
             ("vol_region_props", "層の性質"), ("metal_trace_interpolate", "金属アーチファクト"), ("beam_hardening_correct", "カッピング")]},
    {"keys": ("robot", "robotic", "robotics", "robots", "manipulator", "manipulators", "kinematics", "gripper", "grippers", "humanoid", "rehabilitation", "exoskeleton", "locomotion", "prosthetic"),
     "theme": "ロボット(姿勢・位置合わせ・動き)",
     "doc": "`docs/PERCEPTION_PHYSICAL_AI.md`",
     "ops": [("pnp_ransac", "カメラから物体の姿勢"), ("dlt_pose", "姿勢の直接解"), ("reprojection_error", "姿勢の検証"), ("optimize_pose_graph", "軌跡の整合"),
             ("relative_pose", "相対姿勢"), ("register_cpd_rigid", "剛体の位置合わせ"), ("icp_point2plane", "ICP"), ("estimate_flow", "3D の流れ"),
             ("segment_rigid_motions", "動く部品の分離"), ("fit_rigid", "剛体運動の当てはめ"),
             ("peg_offset_from_rgbd", "peg-in-hole: 手首カメラの RGB-D からずれ"), ("hole_centre_from_rgbd", "穴の中心"),
             ("jamming_diagram", "かじり(jamming)の図(Whitney)"), ("insertion_failure_classify", "挿入の失敗の分類"),
             ("spiral_search_points", "穴探しのらせん探索"), ("slip_predict", "不整地の車輪の滑りの予測"),
             ("dem_slope", "地形の高さ地図から傾斜")]},
    {"keys": ("material", "materials", "coating", "coatings", "treatment", "microstructure", "composite", "composites", "polymer", "polymers", "alloy", "alloys", "ceramic", "ceramics", "steel", "corrosion"),
     "theme": "材料(見え方・組織・表面)",
     "ops": [("spectrum_to_srgb", "分光 → 色"), ("thin_film_reflectance", "薄膜の干渉色"), ("material_catalog", "材質の外観表"), ("oren_nayar", "粗い面の反射"),
             ("brdf_microfacet", "微小面の反射"), ("metallic_flake_normals", "メタリック塗装"), ("corrosion_mask", "腐食域"),
             ("cooc_feature_matrix", "組織のテクスチャ"), ("gabor", "方向性のテクスチャ"), ("vol_granulometry", "CT の空隙分布"), ("entropy_image", "組織の乱れ"),
             ("material_table", "材料の光学物性表(83 種、光学系と観察対象が同じ表を引く)"), ("material_optical_constants", "波長ごとの n, k"),
             ("material_transmittance", "厚さ d の透過率"), ("thermo_optic_coefficient", "温度で変わる屈折率"),
             ("phase_fractions", "粉末 X 線回折から相の割合"), ("scherrer_size", "回折線の幅から結晶子の大きさ(Scherrer)")]},
    {"keys": ("event", "events", "time", "timing", "network", "networks", "wireless", "iot", "synchronization"), "theme": "時間・イベント(高速・非同期)",
     "ops": [("video_spacetime_cube", "時空間の立方体"), ("photon_sample", "光子到達の標本化"), ("tcspc_stats", "時間相関の統計"),
             ("temporal_bandpass", "時間帯域")]},
    {"keys": ("can", "ethercat", "fieldbus", "protocol", "protocols", "embedded", "rtos", "firmware", "bus", "communication"), "theme": "通信・組込み(Fullseye の外)",
     "doc": "`docs/CONNECTIVITY.md`(産業プロトコルの対応表)", "ops": []},
    {"keys": ("fmea", "reliability", "failure", "failures", "risk", "safety", "hazard"), "theme": "信頼性・FMEA(判定の根拠)",
     "doc": "`docs/HARDENING.md`(PoC が上げた堅牢性)・検査ワークフロー層の Verdict",
     "ops": [("null_distribution", "帰無分布(誤報率)"), ("evidence_quantile", "証拠量の位置"), ("spc_capability", "工程能力"),
             ("pod_ahat_fit", "検出確率(POD)の â–a 回帰と a90/95"), ("pod_decision_tradeoff", "見逃しと誤検出の取引")]},
    # ★2026-10-15: 10 月に足した op の系列(研磨・粉体・粉末 X 線)は、既存のテーマの語に当たらず文献層から 1 本も
    #   指されていなかった。語はクラスタ名に実際に出るものだけを置く(当たらない語は当てない)。
    {"keys": ("polishing", "polish", "lapping", "abrasive", "wiping", "deburring", "grinding", "finishing"), "theme": "研磨・拭き取り(除去量の地図)",
     "ops": [("preston_pressure_kernel", "工具の下の圧力分布"), ("preston_removal_map", "軌跡と力から除去深さの地図(Preston の式)"),
             ("preston_track_profile", "1 本の軌跡の除去の断面"), ("preston_coefficient_fit", "測った除去から Preston 係数 k_p"),
             ("removal_depth_from_heights", "前後の高さから除去深さ"), ("wipe_coverage", "拭けた面積の割合"),
             ("coat_thickness_from_image", "残った膜の厚さを画像から(Beer–Lambert)"), ("surface_params", "仕上げ面の Sa / Sq")]},
    {"keys": ("powder", "powders", "particle", "particles", "granular", "comminution", "flowability", "hopper", "bulk"),
     "theme": "粉体(粒度・流動性・粉砕)",
     "ops": [("particle_size_dx", "粒度分布の Dx(D10 / D50 / D90)"), ("particle_image_d50", "粒の画像から D50"),
             ("comminution_law_fit", "粉砕のエネルギー則(Bond ほか)の当てはめ"), ("powder_flowability_class", "安息角から流動性の区分"),
             ("repose_angle_heightmap", "高さ地図から安息角"), ("hopper_discharge_rate", "ホッパの排出流量(Beverloo)"),
             ("blob_count", "粒の数"), ("vol_granulometry", "CT の粒・空隙の大きさ分布")]},
    {"keys": ("diffraction", "xrd", "crystalline", "crystallite", "crystallography", "metallurgy", "microstructure", "alloy", "alloys", "residual"),
     "theme": "回折と結晶(粉末 X 線回折)",
     "ops": [("debye_ring_image", "検出器の Debye 環"), ("detector_calibrate", "検出器の幾何の較正"), ("azimuthal_integrate", "環を 2θ の 1-D に"),
             ("diffraction_peaks", "回折ピーク"), ("phase_fractions", "相の割合"), ("scherrer_size", "結晶子の大きさ(Scherrer)"),
             ("cif_read", "CIF の結晶構造を読む")]},
    {"keys": ("gear", "gears", "screw", "screws", "bolt", "bolts", "spring", "springs", "cam", "linkage", "linkages", "mechanism", "mechanisms", "compliant", "transmission", "reducer"),
     "theme": "機械要素(歯車・ねじ・機構)",
     "ops": [("polar_unwrap", "歯車の極座標展開(歯形)"), ("cylinder_unwrap", "円筒面の展開(ねじ山)"), ("m1_measure_pairs", "歯厚・ピッチ"),
             ("edges_sub_pix", "歯形の輪郭"), ("envelope_spectrum", "歯車の噛み合い振動"), ("order_spectrum", "次数スペクトル"),
             ("segment_rigid_motions", "機構の動く部品の分離"), ("displacement_series", "変位の時系列")]},
    {"keys": ("scattering", "sar", "radar", "antenna", "antennas", "electromagnetic", "microwave", "acoustic", "acoustics", "ultrasonic", "ultrasound", "wave", "waves"),
     "theme": "波(レーダ・音・超音波)",
     "ops": [("fmcw_range_profile", "FMCW の距離"), ("beamform_delay_sum", "ビームフォーミング"), ("range_doppler_map", "距離・速度"),
             ("angular_spectrum_propagate", "波の伝搬"), ("stft", "時間周波数"), ("gcc_delay", "到達時間差"),
             ("pulse_echo_ascan", "超音波のパルスエコー(A スキャン)"), ("acoustic_layer_stack", "積層の反射と透過(音響インピーダンス)"),
             ("echo_phase_polarity", "エコーの位相の反転でボイドを見分ける"), ("matched_filter_snr", "既知の波形の整合フィルタ"),
             ("music_doa", "アンテナ・マイク列での到来方向(MUSIC、ビーム幅より細かく)")]},
    {"keys": ("optical", "optics", "imaging", "lens", "lenses", "photonic", "photonics", "vision", "illumination", "lighting", "spectral", "spectroscopy"),
     "theme": "光学・照明・撮像系",
     "ops": [("lens_system", "レンズ系の定義"), ("paraxial_trace", "近軸追跡"), ("mtf_diffraction", "MTF"), ("depth_of_field", "焦点深度"),
             ("illumination_design", "照明設計"), ("illumination_uniformity", "照明の均一性"), ("render_through_lens", "設計レンズ越しの像"),
             ("spectrum_to_srgb", "分光 → 色"), ("material_dispersion", "ガラスの分散(材料表)"), ("abbe_number", "アッベ数"),
             ("fiber_lp_modes", "光ファイバの伝搬モード"), ("fiber_bundle_coupling", "ライトガイドの照明効率"),
             ("separate_direct_global", "直接光と大域光を分ける(高周波照明)"),
             ("solid_angle_light", "照射立体角を制御する照明(V-ISA 型照明・照射立体角制御照明)を真似る光源: 照明の円錐の半角と向き"),
             ("solid_angle_boundaries", "照射立体角と観察立体角(レンズの NA)から、明暗が切り替わる面の傾きの境界"),
             ("solid_angle_brightness", "鏡面の傾きと明るさ(照射立体角と観察立体角の重なり、明視野と暗視野の境目)")]},
    {"keys": ("education", "students", "courses", "journal", "publishes", "review", "reviews", "abstract", "survey", "curriculum", "teaching", "learning"),
     "theme": "文献のメタ議論(教育・レビュー)", "ops": []},
]

_INDEX_LINE = re.compile(r"^- \[`(?P<dir>[^`]+)/`\]\([^)]*\) — \*\*(?P<name>[^*]+)\*\* \((?P<n>\d+) docs\)")
_NAV_LINE = re.compile(r"^- `(?P<dir>[^`/]+)/SKILL\.md` — (?P<name>.+)$")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _section(md: str, head: str) -> str:
    """``## head`` の本文(次の ## まで)。無ければ空。"""
    m = re.search(r"^## " + re.escape(head) + r"[^\n]*\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    return m.group(1).strip() if m else ""


def _first_sentences(text: str, n: int = 2) -> str:
    text = " ".join(text.split())
    parts = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(parts[:n]).strip()


# --------------------------------------------------------------------------- #
# op の実在(出荷ノートの一覧)                                                     #
# --------------------------------------------------------------------------- #
class OpIndex:
    """出荷ノートの一覧(OP_NOTES.json)。名前 → (dim, category, in, out, ノートの相対パス)。対応表の op を検証する。"""

    def __init__(self, repo: str):
        notes_json = os.path.join(repo, "fullseye", "data", "OP_NOTES.json")
        if not os.path.isfile(notes_json):
            raise SystemExit("op notes list not found: %s — run tools/regen_all.py first (fail-closed)" % notes_json)
        meta = json.load(open(notes_json, encoding="utf-8"))
        notes = meta["notes"]
        flat = [n for v in (notes.values() if isinstance(notes, dict) else notes) for n in (v if isinstance(v, list) else [v])]
        self.ops: dict[str, dict] = {}
        for n in flat:
            rel = n["path"].replace("\\", "/")
            if os.path.isabs(rel) or not rel.startswith("docs/ops/") or ".." in rel.split("/"):
                raise SystemExit("op note path must be repo-relative under docs/ops/, got %r (fail-closed)" % rel)
            if not os.path.isfile(os.path.join(repo, rel)):
                raise SystemExit("op note listed in OP_NOTES.json is missing on disk: %s (fail-closed)" % rel)
            self.ops.setdefault(n["op"], {"op": n["op"], "dim": n["dim"], "category": n.get("category", ""), "in": n.get("in", ""),
                                          "out": n.get("out", ""), "rel": rel.split("docs/ops/", 1)[-1]})
        if not self.ops:
            raise SystemExit("no op notes listed (fail-closed)")
        #: 出荷ノートの枚数。名前の数(``len(self.ops)``)とは違う —— 同じ名前が 2 つの族に在る op がある。
        self.n_notes = len(flat)
        missing = sorted({op for table in THEME_TABLES.values() for th in table for op, _why in th["ops"]
                          if op not in self.ops})
        if missing:
            raise SystemExit("THEME_OPS names ops that are not in the shipped notes (renamed or removed?): %s — fix the table (fail-closed)"
                             % ", ".join(missing))


def _themes_for(text: str, table: list[dict] | None = None) -> list[dict]:
    """テーマの語を、ハイフンを残した形(time-of-flight)と空白に開いた形(point-cloud → point cloud)の両方で照合する。

    ``table`` は分野のテーマ表(``CORPORA[name]["themes"]`` → :data:`THEME_TABLES`)。省くと製造の表。
    """
    low = text.lower()
    forms = [" " + re.sub(r"[^a-z0-9\-]+", " ", low) + " ", " " + re.sub(r"[^a-z0-9]+", " ", low) + " "]
    hits = []
    for th in (THEME_OPS if table is None else table):
        if any((" " + k + " ") in w for k in th["keys"] for w in forms):
            hits.append(th)
    return hits


#: 分野ごとのテーマ表。CORPORA の "themes" で選ぶ(既定 = 製造の THEME_OPS)
THEME_TABLES = {"default": THEME_OPS, "drive": DRIVE_THEMES}


def _slug(name: str) -> str:
    """GitHub の見出し ID: 小文字、英数・空白・ハイフン以外を落とし、空白をハイフンに(連続ハイフンは潰さない)。"""
    return re.sub(r"[^\w\- ]", "", name.lower()).replace(" ", "-")


def _fmt_op(idx: OpIndex, op: str, why: str) -> str:
    o = idx.ops[op]
    sig = ("%s → %s" % (o["in"] or "入力なし", o["out"])) if (o["in"] or o["out"]) else o["dim"]
    return "[`%s`](../ops/%s)(%s%s%s)" % (op, o["rel"], why, "、" if why else "", sig)


# --------------------------------------------------------------------------- #
# コーパス側                                                                    #
# --------------------------------------------------------------------------- #
def _paper(path: str) -> dict | None:
    """葉の doc からメタデータだけ(抄録・手元パスは読まない)。"""
    md = _read(path)
    title = ""
    for line in md.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    if not title:
        raise SystemExit("paper without a title line: %s (fail-closed)" % os.path.basename(path))

    def field(name: str) -> str:
        m = re.search(r"^\*\*" + re.escape(name) + r":\*\*[ \t]*(.*)$", md, re.M)   # [ \t]: 空欄で次の行を拾わない
        return m.group(1).strip() if m else ""

    authors = field("Authors")
    # ★2026-10-03: corpus2skill は葉へ写すときに Authors / Date / URL の行を落とす(元の papers/*.md には在る)。
    #   その結果、出荷した文献層の代表論文がすべて「— (n.d.)」になり、「新しい順」も日付なしで並んでいた。
    #   葉の **Source:** が指す元ファイルから、欠けた欄だけを補う(元のパスは読むだけで、出力には書かない)。
    src = field("Source")
    extra = {}
    if src and not (authors and field("Date")) and os.path.isfile(src):
        orig = _read(src)
        for key in ("Authors", "Date", "URL"):
            m2 = re.search(r"^\*\*" + key + r":\*\*[ \t]*(.*)$", orig, re.M)
            extra[key] = m2.group(1).strip() if m2 else ""
        authors = authors or extra["Authors"]
    if authors:
        names = [a.strip() for a in authors.replace(" et al.", "").split(",") if a.strip()]
        authors = names[0] + (" et al." if len(names) > 1 else "") if names else ""
    date = field("Date") or extra.get("Date", "")
    doi = field("DOI/ID") or field("arXiv")
    url = field("URL") or extra.get("URL", "")
    oa = field("OpenAlex")
    if not (doi or url or oa):
        raise SystemExit("paper without DOI / URL / OpenAlex id: %s (fail-closed — the corpus writer always records one)" % os.path.basename(path))
    return {"title": title, "authors": authors, "year": date[:4] if date else "", "doi": doi, "url": url, "openalex": oa, "date": date}


def _leaf_papers(leaf_dir: str, k: int) -> list[dict]:
    ddir = os.path.join(leaf_dir, "docs")
    docs = sorted(os.listdir(ddir)) if os.path.isdir(ddir) else []
    papers = [p for p in (_paper(os.path.join(ddir, d)) for d in docs if d.endswith(".md")) if p]
    papers.sort(key=lambda p: p["date"], reverse=True)
    if len(papers) <= k:
        return papers
    return papers[: k - 1] + [papers[-1]]                                   # 新しい順 k−1 本 + いちばん古い 1 本(古典を落とさない)


def _fmt_paper(p: dict) -> str:
    ref = p["doi"] or p["openalex"]
    link = p["url"] or (("https://doi.org/" + p["doi"]) if p["doi"] and not p["doi"].startswith("W") else "")
    year = p["year"] or "n.d."
    cite = "%s (%s). %s." % (p["authors"] or "—", year, p["title"].rstrip("."))
    return "  - %s %s" % (cite, ("[%s](%s)" % (ref, link)) if link else "`%s`" % ref)


def build_corpus(rad_root: str, name: str, idx: OpIndex, max_papers: int) -> tuple[str, dict]:
    cdir = os.path.join(rad_root, name + "_corpus_v2")
    table = THEME_TABLES[CORPORA[name].get("themes", "default")]
    if not os.path.isfile(os.path.join(cdir, "INDEX.md")):
        raise SystemExit("corpus not found: %s (INDEX.md missing) — refusing to write an empty literature note" % cdir)
    meta = json.load(open(os.path.join(cdir, "metadata.json"), encoding="utf-8")) if os.path.isfile(os.path.join(cdir, "metadata.json")) else {}
    stats = meta.get("stats", {})
    built = (meta.get("built_at") or "")[:10]
    info = CORPORA[name]
    index_lines = [ln for ln in _read(os.path.join(cdir, "INDEX.md")).splitlines() if ln.startswith("- [`cluster_")]
    tops = [m.groupdict() for m in (_INDEX_LINE.match(ln) for ln in index_lines) if m]
    if not tops or len(tops) != len(index_lines):
        raise SystemExit("INDEX.md of %s: %d cluster lines but %d parsed — the line format changed (fail-closed)"
                         % (cdir, len(index_lines), len(tops)))
    reverse: dict[str, list[str]] = defaultdict(list)
    out = []
    out.append("# 文献層: %s\n" % info["title"])
    out.append("<!-- generated by tools/gen_literature_notes.py from the RAD corpus %s_corpus_v2 (built %s); do not edit by hand -->\n" % (name, built))
    out.append("**何のコーパスか**: %s\n" % info["what"])
    out.append("**Fullseye でなぜ要るか**: %s\n" % info["why"])
    out.append("**来歴**: OpenAlex から取得した論文メタデータ **%s 本**(2012 年以降、`fetch_openalex_topical.py`)を TF-IDF + k-means で "
               "**%s クラスタ**に階層化し(raptor の `corpus2skill`、%s)、各クラスタの要約を LLM(claude-haiku-4-5)が書いた。"
               "ここに載せるのは**その要約と、代表論文の題名・著者・年・DOI だけ**(メタデータは CC0。抄録は出版社の権利なので写さない)。"
               "要約は生成時の英語のまま。**正直な限界**: 文献は原理・選定・校正の研究が中心で、型番やデータシートの数値(製品知識)は薄い。\n"
               % (f"{stats.get('documents', 0):,}", stats.get("clusters", 0), built))
    out.append("**使い方(op に落とす)**: 各クラスタの「**使う op**」は、知識のテーマ → op の対応表(`tools/gen_literature_notes.py` の `THEME_OPS`、"
               "人が書いたもの)で引いた**実在の op**(生成時に出荷ノート %s 本の一覧と突き合わせ、無ければ止まる)。op の後ろはなぜ使うかと型。"
               "テーマに当たらないクラスタは「op に落ちていない」と書く(Fullseye に無い領域を隠さない)。読む順: 工程・部品の話題 → クラスタ → 使う op → "
               "op ノート(型の契約・実行できる例)→ 実装。末尾の「op → クラスタ」で逆に引ける。\n" % f"{len(idx.ops):,}")
    out.append("## 目次\n")
    for t in tops:
        out.append("- [%s](#%s)(%s 本)" % (t["name"], _slug(t["name"]), t["n"]))
    out.append("")
    n_leaf = n_paper = n_oplink = n_uncovered = 0
    themes_hit: set[str] = set()
    for t in tops:
        tdir = os.path.join(cdir, t["dir"])
        md = _read(os.path.join(tdir, "SKILL.md"))
        kk = [ln for ln in _section(md, "Key Knowledge").splitlines() if ln.startswith("- ")]
        navs = [m.groupdict() for m in (_NAV_LINE.match(ln) for ln in _section(md, "Navigation").splitlines()) if m]
        # Navigation は長い名前(cluster_01_02_cad_parametric_modeling)で書かれ、実際のディレクトリは短縮名(c_02_cad_para)——
        # 2 つ目の番号で対応づける(名前の一致に頼らない)
        subdirs = sorted(d for d in os.listdir(tdir) if os.path.isdir(os.path.join(tdir, d)))
        for nv in navs:
            m = re.match(r"cluster_\d+_(\d+)_", nv["dir"])
            cand = [d for d in subdirs if m and d.startswith("c_%02d_" % int(m.group(1)))]
            if len(cand) != 1:
                raise SystemExit("%s/%s: Navigation entry %r matches %d sub-directories (expected 1) — the layout changed (fail-closed)"
                                 % (name, t["dir"], nv["dir"], len(cand)))
            nv["dir"] = cand[0]
        if not navs:
            navs = [{"dir": "", "name": t["name"]}]
        # クラスタ自身の名前で当たったテーマを先に、葉の名前だけで当たったテーマを後に(溶接のクラスタで「板金」が先頭に来ない)
        themes_name = _themes_for(t["name"], table)
        themes = themes_name + [th for th in _themes_for(" ".join(nv["name"] for nv in navs), table)
                                if th not in themes_name]
        out.append("## %s\n" % t["name"])
        out.append("**%s 本**\n" % t["n"])
        ov = _first_sentences(_section(md, "Overview"), 2)
        if ov:
            out.append(ov + "\n")
        if kk:
            out.append("\n".join(kk[:5]) + "\n")
        out.append("**使う op**(テーマ → op の対応表から。ノートで型と例を確かめてから使う):\n")
        seen: set[str] = set()
        any_ops = False
        for th in themes:
            items = [(op, why) for op, why in th["ops"] if op not in seen]
            if th.get("doc"):
                out.append("- %s —— 入口: %s" % (th["theme"], th["doc"]))
            if not items:
                if not th.get("doc"):
                    out.append("- %s —— op なし(Fullseye の外)" % th["theme"])
                continue
            any_ops = True
            # ★2026-10-15: ここはテーマごとに先頭 8 本で**黙って切っていた**。表の後ろに足した op(10 月の研磨・材料表・
            #   ファイバ・触覚・peg-in-hole …)は対応表に在るのに文献層のどこにも出ず、表に書いたことが嘘になっていた
            #   (2026-10-15 時点の表 251 op のうち 21 本。うち 3 本は SPC のテーマの鍵がどのクラスタ名にも当たらなかった分)。
            #   テーマは多くても 17 本なので全部出し、当たらないテーマは INDEX に名指しする(dead_themes)。
            themes_hit.add(th["theme"])
            out.append("- %s: " % th["theme"] + "、".join(_fmt_op(idx, op, why) for op, why in items))
            for op, _why in items:
                seen.add(op)
                reverse[op].append(t["name"])
                n_oplink += 1
        for th in themes:
            themes_hit.add(th["theme"])
        if not any_ops:
            n_uncovered += 1
            out.append("- **op に落ちていない**(テーマの対応表に無い —— Fullseye の外か、未整備)")
        out.append("")
        for nv in navs:
            ldir = os.path.join(tdir, nv["dir"]) if nv["dir"] else tdir
            lmd = _read(os.path.join(ldir, "SKILL.md")) if os.path.isfile(os.path.join(ldir, "SKILL.md")) else ""
            papers = _leaf_papers(ldir, max_papers)
            if not papers and nv["dir"]:
                continue
            n_leaf += 1
            n_paper += len(papers)
            out.append("### %s\n" % nv["name"])
            lov = _first_sentences(_section(lmd, "Overview"), 1)
            if lov:
                out.append(lov + "\n")
            lops: list[tuple[str, str]] = []
            for th in _themes_for(nv["name"], table):
                for op, why in th["ops"]:
                    if all(op != o for o, _w in lops):
                        lops.append((op, why))
            rest = lops[6:]
            lops = lops[:6]
            if lops:
                out.append("- 使う op: " + "、".join(_fmt_op(idx, op, why) for op, why in lops)
                           + (("、ほか %d 個: " % len(rest)) + "、".join("`%s`" % op for op, _w in rest) if rest else ""))
                for op, _why in lops:
                    tag = t["name"] + " › " + nv["name"]
                    if t["name"] not in reverse[op] and tag not in reverse[op]:
                        reverse[op].append(tag)
                n_oplink += len(lops)
            out.append("- 代表論文(新しい順 + いちばん古い 1 本):")
            out.extend(_fmt_paper(p) for p in papers)
            out.append("")
    out.append("## op → クラスタ(逆引き)\n")
    out.append("この文献層で「使う op」に挙がった op と、それが出たクラスタ(上位 › 葉)。op から「どの知識の文脈で使うか」を引く。\n")
    out.append("| op | 出たクラスタ |")
    out.append("|---|---|")
    for op in sorted(reverse):
        out.append("| [`%s`](../ops/%s) | %s |" % (op, idx.ops[op]["rel"], "; ".join(reverse[op][:6]) + (" …" if len(reverse[op]) > 6 else "")))
    out.append("")
    row = {"documents": stats.get("documents", 0), "clusters": stats.get("clusters", 0), "tops": len(tops), "leaves": n_leaf,
           "papers": n_paper, "oplinks": n_oplink, "ops": len(reverse), "uncovered": n_uncovered, "built": built,
           "themes_hit": sorted(themes_hit), "table": CORPORA[name].get("themes", "default")}
    return "\n".join(out) + "\n", row


# --------------------------------------------------------------------------- #
# 厳選の層(生のコーパス + 手で書いた目録)                                          #
# --------------------------------------------------------------------------- #
_LOCAL_PATH = re.compile(r"(?<![A-Za-z])[A-Z]:[\\/]|(?<![\w/])/c/|(?<![\w:/.])/(?:home|Users|tmp|mnt)/")
_SHINGLE = 8                                                               # 抄録の写しとみなす連続英単語の数


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _shingles(text: str, n: int = _SHINGLE) -> set[tuple[str, ...]]:
    w = _words(text)
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def _abstract(md: str) -> str:
    m = re.search(r"^## Abstract\s*\n(.*)", md, re.S | re.M)
    return m.group(1).strip() if m else ""


def _manifest_texts(man: dict) -> list[tuple[str, str]]:
    """目録の手書きの文(場所, 文)。抄録の写し・手元パスの検査の対象。題名・DOI は書誌なので含まない。"""
    out = [("what", man.get("what", "")), ("why", man.get("why", ""))]
    for ax in man["axes"]:
        out += [(ax["id"] + ".overview", p) for p in ax["overview"]]
        out += [(ax["id"] + ".op " + op, why) for op, why in ax["ops"]]
        out += [(ax["id"] + "." + k, ax.get(k, "")) for k in ("gaps", "pending_note")]
        out += [(ax["id"] + ".paper " + (p.get("doi") or p.get("openalex", "")), p.get("note", "")) for p in ax["papers"]]
    return [(where, t) for where, t in out if t]


def load_manifest(repo: str, name: str) -> dict:
    path = os.path.join(repo, CURATED[name])
    if not os.path.isfile(path):
        raise SystemExit("curated manifest not found: %s (fail-closed)" % CURATED[name])
    man = json.load(open(path, encoding="utf-8"))
    for key in ("name", "corpus", "title", "what", "why", "selection_rule", "axes"):
        if key not in man:
            raise SystemExit("%s: manifest key %r missing (fail-closed)" % (CURATED[name], key))
    if man["name"] != name:
        raise SystemExit("%s: name %r does not match the registry key %r (fail-closed)" % (CURATED[name], man["name"], name))
    ids = [ax.get("id") for ax in man["axes"]]
    if len(ids) < 4 or len(set(ids)) != len(ids):
        raise SystemExit("%s: need >= 4 axes with distinct ids, got %r (fail-closed)" % (CURATED[name], ids))
    for ax in man["axes"]:
        for key in ("id", "name", "overview", "ops", "papers"):
            if not ax.get(key):
                raise SystemExit("%s: axis %s has no %r (fail-closed)" % (CURATED[name], ax.get("id"), key))
        for p in ax["papers"]:
            if bool(p.get("doi")) == bool(p.get("openalex")) or not p.get("note"):
                raise SystemExit("%s: axis %s paper needs exactly one of doi / openalex, and a note: %r (fail-closed)"
                                 % (CURATED[name], ax["id"], p))
    bad = [where for where, t in _manifest_texts(man) if _LOCAL_PATH.search(t)]
    if bad:
        raise SystemExit("%s: local absolute path in %s (fail-closed)" % (CURATED[name], ", ".join(bad)))
    return man


def build_curated(rad_root: str, name: str, idx: OpIndex, repo: str) -> tuple[str, dict]:
    """厳選の層を 1 本組む。論文のメタデータはコーパスの本体から、件数は READING_ORDER.json から数える。"""
    man = load_manifest(repo, name)
    cdir = os.path.join(rad_root, man["corpus"])
    order_path = os.path.join(cdir, "READING_ORDER.json")
    if not os.path.isfile(order_path) or not os.path.isdir(os.path.join(cdir, "papers")):
        raise SystemExit("corpus not found or not a raw corpus (READING_ORDER.json + papers/): %s (fail-closed)" % cdir)
    order = json.load(open(order_path, encoding="utf-8"))
    if not order:
        raise SystemExit("%s: READING_ORDER.json is empty (fail-closed)" % man["corpus"])
    by_key = {}
    for r in order:                                                       # DOI が無い文献は OpenAlex id(w…)が doi 欄に入っている
        if r.get("doi"):
            by_key[r["doi"].lower()] = r
    # 目録の op の実在(テーマ表と同じ規律: 改名・削除した op を指したまま公開しない)
    named = {op for ax in man["axes"] for op, _w in ax["ops"]} | {op for ax in man["axes"] for op in ax.get("pending_ops", [])}
    missing = sorted(named - set(idx.ops))
    if missing:
        raise SystemExit("%s names ops that are not in the shipped notes: %s — fix the manifest (fail-closed)"
                         % (CURATED[name], ", ".join(missing)))
    # 抄録の写しの門: 目録の手書き文 × コーパスの全抄録(主題側)を 8 語の並びで突き合わせる
    abstract_sh: set = set()
    for r in order:
        abstract_sh |= _shingles(_abstract(_read(os.path.join(cdir, "papers", r["file"]))))
    copied = [(where, " ".join(sh)) for where, t in _manifest_texts(man) for sh in sorted(_shingles(t) & abstract_sh)]
    if copied:
        raise SystemExit("%s: hand-written text shares %d-word runs with corpus abstracts (copying is not allowed): %s (fail-closed)"
                         % (CURATED[name], _SHINGLE, copied[:3]))
    axis_count = {ax["id"]: sum(1 for r in order if ax["id"] in r.get("topics_hit", [])) for ax in man["axes"]}
    readme = os.path.join(cdir, "README.md")
    m = re.search(r"\((\d{4}-\d{2}-\d{2}) 作成\)", _read(readme)) if os.path.isfile(readme) else None
    built = m.group(1) if m else ""
    n_axes = len(man["axes"])
    out = ["# 文献層: %s\n" % man["title"],
           "<!-- generated by tools/gen_literature_notes.py from the RAD corpus %s (raw corpus, papers chosen by hand in %s; built %s); "
           "do not edit by hand -->\n" % (man["corpus"], CURATED[name], built),
           "**何のコーパスか**: %s\n" % man["what"],
           "**Fullseye でなぜ要るか**: %s\n" % man["why"],
           "**来歴**: OpenAlex から取得した論文メタデータの主題側 **%s 本**(分野違い・重複を落とした後)を、取得クエリの軸 **%d クラスタ**で持つ"
           "生のコーパス(LLM による階層化・要約はしていない、%s)。この層は**人が厳選した層**で、軸ごとの概観は人が抄録を読んで自分の言葉で書いたもの、"
           "論文は古典と 2020 年以降の有用なものを手で選んだもの(目録 `%s`)。載せるのは題名・著者・年・DOI だけ"
           "(メタデータは CC0。抄録は出版社の権利なので写さない —— 目録の手書き文はコーパスの全抄録と %d 語の並びで突き合わせ、一致があれば生成を止める)。"
           "軸の本数は語彙で当たった本数で、2 軸以上に当たる文献は両方で数える。\n"
           % (f"{len(order):,}", n_axes, built, CURATED[name], _SHINGLE),
           "**使い方(op に落とす)**: 各軸の「**使う op**」は目録に人が書いた対応で、op 名は生成時に出荷ノート %s 本の一覧と突き合わせる"
           "(無ければ止まる)。op の後ろはなぜ使うかと型。「Fullseye に無いもの」は op に落ちていない部分を正直に書いたもの。"
           "読む順: 話題 → 軸の概観 → 使う op → op ノート(型の契約・実行できる例)→ 厳選した文献。末尾の「op → クラスタ」で逆に引ける。\n"
           % f"{len(idx.ops):,}",
           "## 目次\n"]
    for ax in man["axes"]:
        head = "%s %s" % (ax["id"], ax["name"])
        out.append("- [%s](#%s)(%s 本)" % (head, _slug(head), f"{axis_count[ax['id']]:,}"))
    out.append("")
    reverse: dict[str, list[str]] = defaultdict(list)
    n_paper = n_oplink = 0
    for ax in man["axes"]:
        head = "%s %s" % (ax["id"], ax["name"])
        out.append("## %s\n" % head)
        out.append("**%s 本**(この軸の語彙で当たった本数)\n" % f"{axis_count[ax['id']]:,}")
        out.extend(p + "\n" for p in ax["overview"])
        out.append("**使う op**(目録の対応。ノートで型と例を確かめてから使う):\n")
        for op, why in ax["ops"]:
            out.append("- " + _fmt_op(idx, op, why))
            if ax["id"] not in reverse[op]:
                reverse[op].append(ax["id"])
            n_oplink += 1
        for op in ax.get("pending_ops", []):
            out.append("- " + _fmt_op(idx, op, "準備中の族から"))
            if ax["id"] not in reverse[op]:
                reverse[op].append(ax["id"])
            n_oplink += 1
        if ax.get("pending_note"):
            out.append("- **準備中**: " + ax["pending_note"])
        if ax.get("gaps"):
            out.append("- **Fullseye に無いもの**: " + ax["gaps"])
        out.append("")
        papers = []
        for p in ax["papers"]:
            key = (p.get("doi") or p.get("openalex")).lower()
            r = by_key.get(key)
            if r is None:
                raise SystemExit("%s: axis %s cites %s, which is not in the topical side of %s (rejected, duplicate or absent) (fail-closed)"
                                 % (CURATED[name], ax["id"], key, man["corpus"]))
            if ax["id"] not in r.get("topics_hit", []):
                raise SystemExit("%s: axis %s cites %s, but the corpus files it under %s, not %s (fail-closed)"
                                 % (CURATED[name], ax["id"], key, r.get("topics_hit"), ax["id"]))
            meta = _paper(os.path.join(cdir, "papers", r["file"]))
            papers.append((meta, p["note"]))
        papers.sort(key=lambda mp: (mp[0]["date"], mp[0]["title"]))
        out.append("### 厳選した文献(%d 本、古い順)\n" % len(papers))
        out.append("- 題名・著者・年・DOI と、読む理由:")
        out.extend(_fmt_paper(meta) + " —— " + note for meta, note in papers)
        out.append("")
        n_paper += len(papers)
    out.append("## op → クラスタ(逆引き)\n")
    out.append("この層で「使う op」に挙がった op と、それが出た軸。op から「どの知識の文脈で使うか」を引く。\n")
    out.append("| op | 出た軸 |")
    out.append("|---|---|")
    names = {ax["id"]: "%s %s" % (ax["id"], ax["name"]) for ax in man["axes"]}
    for op in sorted(reverse):
        out.append("| [`%s`](../ops/%s) | %s |" % (op, idx.ops[op]["rel"], "; ".join(names[a] for a in reverse[op])))
    out.append("")
    row = {"documents": len(order), "clusters": n_axes, "tops": n_axes, "leaves": n_axes, "papers": n_paper,
           "oplinks": n_oplink, "ops": len(reverse), "uncovered": 0, "built": built}
    return "\n".join(out) + "\n", row


def _title(repo: str, name: str) -> str:
    if name in CORPORA:
        return CORPORA[name]["title"]
    return load_manifest(repo, name)["title"]


def dead_themes(rows: dict[str, dict]) -> list[tuple[str, str]] | None:
    """どのコーパスのクラスタ名・葉の名前にも当たらなかったテーマ ``[(表, テーマ)]``。

    当たらないテーマの op は、表に書いてあっても文献層のどこからも指されない。全部のコーパスを組んだ回でしか
    数えられない(一部だけ組んだ回は ``None``)。
    """
    if not all(n in rows and "themes_hit" in rows[n] for n in CORPORA):
        return None
    hit: dict[str, set[str]] = defaultdict(set)
    for n in CORPORA:
        hit[rows[n]["table"]].update(rows[n]["themes_hit"])
    return [(tname, th["theme"]) for tname, table in THEME_TABLES.items() for th in table if th["theme"] not in hit[tname]]


def build_index(rows: dict[str, dict], n_notes: int, titles: dict[str, str] | None = None,
                dead: list[tuple[str, str]] | None = None) -> str:
    out = ["# 文献層 —— RAD コーパスからの、op に繋がる来歴つき要約\n",
           "<!-- generated by tools/gen_literature_notes.py; do not edit by hand -->\n",
           "Fullseye の RAG(`docs/ops` の op ノート %s 本)は **op を有効に使うための土台**。この層は周辺分野の知識 —— 製造"
           "(設計 → 工程 → 検査)、運転(シミュレーション・評価・センサーの模擬)、光学計測と外観検査の信頼性(POD・スペックル・偏光・大域光輸送・受入試験・合成データ)"
           "—— を、外部の文献コーパス(raptor の RAD、OpenAlex メタデータ)のクラスタごとに要約し、"
           "**その知識で使う op**(人が書いたテーマ → op の対応表、op 名は生成時に出荷ノートと突き合わせる)と、代表論文の題名・年・DOI を"
           "来歴として付けたもの。抄録は写さない。op ノートと違い**コーパス本体は repo に無い**ので `tools/regen_all.py` の鎖には入れず、"
           "`tools/gen_literature_notes.py --rad-root <RAD>` で作り直す(`tests/test_literature_notes.py` が形を守る)。"
           "題名に「(厳選)」とある層は階層化していない生のコーパスから人が論文を選び、軸の概観を人が書いたもの(目録 `docs/literature/curated/`)で、"
           "その行の「クラスタ」「上位」「葉」は軸の数。\n" % f"{n_notes:,}",
           "| 文献層 | 論文 | クラスタ | 上位 | 葉 | 載せた代表論文 | op リンク | 挙がった op | op に落ちていない上位クラスタ | 構築日 |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in rows.items():
        out.append("| [%s](%s.md) | %s | %d | %d | %d | %d | %d | %d | %d / %d | %s |" % (
            (titles or {}).get(name) or CORPORA[name]["title"], name, f"{r['documents']:,}", r["clusters"], r["tops"], r["leaves"], r["papers"], r["oplinks"], r["ops"],
            r["uncovered"], r["tops"], r["built"]))
    out.append("\n**読み方**: 工程・部品・運転の評価の話題 → 該当する文献層のクラスタ → 「使う op」→ op ノート(型の契約・実行できる例)→ 実装。"
               "逆に op から引くときは各ファイル末尾の「op → クラスタ」。\n")
    out.append("**正直な限界**: 文献は原理・選定・校正・評価の研究が中心で、製品カタログ(型番・定格)や規格の本文は含まない。op の対応は人が書いた表で、"
               "当たらないクラスタは「op に落ちていない」と数える(上の列)—— そこが Fullseye に無い領域か、表の未整備。"
               "テーマ表は分野ごとに分けてある(運転の「digital twin」が製造の予知保全に当たらないように)。"
               "語の一致(BM25)で op を引く案は、一般語で無関係の op が並んだので捨てた。\n")
    if dead is not None:
        out.append("**どのクラスタにも当たらなかったテーマ**(表に書いた op でも、ここに挙がるテーマのものは文献層から指されない。"
                   "コーパスの語に合わせて鍵を直すか、分野のコーパスを足す): "
                   + ("、".join("%s(%s)" % (th, tn) for tn, th in dead) if dead else "なし") + "\n")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# 件数の打ち直し(コーパス不要)                                                      #
# --------------------------------------------------------------------------- #
#: INDEX.md の「`docs/ops` の op ノート N 本」(ノートの**枚数**)
_INDEX_COUNT_RE = re.compile(r"(`docs/ops` の op ノート )([\d,]+)( 本)")
#: 各文献層の「出荷ノート N 本」(ノートの**名前の数**。同じ名前が 2 つの族に在る op は 1 と数える)
_LAYER_COUNT_RE = re.compile(r"(出荷ノート )([\d,]+)( 本)")
_OP_NOTE_HEAD_RE = re.compile(r"\A---\r?\nop: *([^\r\n]+)")


def count_op_notes(repo: str) -> tuple[int, int]:
    """``docs/ops`` の実ファイルから ``(ノートの枚数, 名前の数)`` を数える(コーパスも OP_NOTES.json も要らない)。

    op ノートは先頭が ``---`` / ``op: <名前>`` の front matter。索引(INDEX*.md)・SAMPLES・族の案内(guides)は
    この形ではないので数えない。台帳(OP_NOTES.json)から数えると「台帳が古いのに数も古い」で気づけないので、
    ファイルを開いて数える。
    """
    root = os.path.join(repo, "docs", "ops")
    if not os.path.isdir(root):
        raise SystemExit("docs/ops not found under %s (fail-closed)" % repo)
    n_files, names = 0, set()
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            with open(os.path.join(dirpath, fn), encoding="utf-8") as f:
                m = _OP_NOTE_HEAD_RE.match(f.read(400))
            if m:
                n_files += 1
                names.add(m.group(1).strip())
    if not n_files:
        raise SystemExit("no op notes found under docs/ops (fail-closed)")
    return n_files, len(names)


def _literature_files(lit_dir: str) -> tuple[str, list[str]]:
    """``(INDEX.md のパス, 生成器が書いた文献層ファイルのパス)``。登録表(CORPORA / CURATED)の名前で引くので、
    OSS の地図など別の生成器のファイルは読まない(regen_all の読み書きの宣言を増やさない)。"""
    index = os.path.join(lit_dir, "INDEX.md")
    layers = [p for p in (os.path.join(lit_dir, n + ".md") for n in sorted(set(CORPORA) | set(CURATED))) if os.path.isfile(p)]
    return index, layers


def stated_count_problems(repo: str = _ROOT) -> list[str]:
    """文献層が書いている「op ノート N 本」が、``docs/ops`` の実ファイルの数と合っているか。ずれの一覧(空なら合っている)。"""
    n_files, n_names = count_op_notes(repo)
    index, layers = _literature_files(os.path.join(repo, "docs", "literature"))
    probs = []
    ms = _INDEX_COUNT_RE.findall(_read(index))
    if len(ms) != 1:
        probs.append("INDEX.md: 「op ノート N 本」が %d 箇所(1 箇所のはず)" % len(ms))
    elif int(ms[0][1].replace(",", "")) != n_files:
        probs.append("INDEX.md: op ノート %s 本と書いてあるが、docs/ops の実ファイルは %s 本" % (ms[0][1], f"{n_files:,}"))
    for p in layers:
        ms = _LAYER_COUNT_RE.findall(_read(p))
        if len(ms) != 1:
            probs.append("%s: 「出荷ノート N 本」が %d 箇所(1 箇所のはず)" % (os.path.basename(p), len(ms)))
        elif int(ms[0][1].replace(",", "")) != n_names:
            probs.append("%s: 出荷ノート %s 本と書いてあるが、実際の名前の数は %s" % (os.path.basename(p), ms[0][1], f"{n_names:,}"))
    return probs


def restate_counts(repo: str = _ROOT) -> list[str]:
    """INDEX.md と各文献層の件数だけを、実ファイルの数に打ち直す。書き換えたファイルのパスを返す。

    文献層の本体はコーパスから作るので ``--rad-root`` が要るが、**件数は docs/ops を数えれば分かる**。件数だけ古びて
    (op を足すたびに 1 つずつ)他は変わらない、という古び方を、コーパス無しで直す。置換は 1 箇所ずつ数えて確かめる。
    """
    n_files, n_names = count_op_notes(repo)
    index, layers = _literature_files(os.path.join(repo, "docs", "literature"))
    changed = []
    for path, rx, n in [(index, _INDEX_COUNT_RE, n_files)] + [(p, _LAYER_COUNT_RE, n_names) for p in layers]:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
        new, k = rx.subn(lambda m: m.group(1) + f"{n:,}" + m.group(3), text)
        if k != 1:
            raise SystemExit("%s: expected exactly one count to restate, found %d (fail-closed)" % (path, k))
        if new != text:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new)
            changed.append(path)
    return changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rad-root", default=os.environ.get("FULLSEYE_RAD_DIR", ""), help="RAD コーパスの親ディレクトリ(既定 = 環境変数 FULLSEYE_RAD_DIR)")
    ap.add_argument("--corpus", action="append", choices=sorted(CORPORA), help="出す v2 コーパス(--corpus も --curated も無ければ全部)")
    ap.add_argument("--curated", action="append", choices=sorted(CURATED), help="出す厳選の層(目録 docs/literature/curated/<name>.json)")
    ap.add_argument("--repo", default=_ROOT, help="Fullseye の checkout(op ノートの在処。既定 = この生成器の 2 つ上)")
    ap.add_argument("--out", default=None, help="出力先(既定 = <repo>/docs/literature)")
    ap.add_argument("--max-papers", type=int, default=6, help="葉クラスタごとに載せる代表論文の上限")
    ap.add_argument("--restate-counts", action="store_true",
                    help="件数(op ノートの枚数)だけを docs/ops の実ファイルから打ち直す。コーパス不要(regen_all の鎖から呼ばれる)")
    a = ap.parse_args(argv)
    if a.restate_counts:
        for p in restate_counts(a.repo):
            print("literature count restated: %s" % os.path.relpath(p, a.repo))
        return 0
    if not a.rad_root or not os.path.isdir(a.rad_root):
        raise SystemExit("--rad-root (or FULLSEYE_RAD_DIR) must point at the RAD corpus directory; got %r" % a.rad_root)
    out_dir = a.out or os.path.join(a.repo, "docs", "literature")
    idx = OpIndex(a.repo)
    if a.corpus or a.curated:
        names, curated = a.corpus or [], a.curated or []
    else:
        names, curated = sorted(CORPORA), sorted(CURATED)
    os.makedirs(out_dir, exist_ok=True)
    rows = {}
    texts = {}
    for name in names:                                                     # まず全部を組む(途中で止まればファイルは 1 つも触らない)
        texts[name], rows[name] = build_corpus(a.rad_root, name, idx, a.max_papers)
    for name in curated:
        texts[name], rows[name] = build_curated(a.rad_root, name, idx, a.repo)
    names = names + curated
    for name in names:
        with open(os.path.join(out_dir, name + ".md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(texts[name])
        row = rows[name]
        print("literature %-24s %6s papers / %3d clusters / %3d leaves / %4d cited / %4d op links (%3d ops), uncovered top clusters %d/%d -> %s.md"
              % (name, f"{row['documents']:,}", row["clusters"], row["leaves"], row["papers"], row["oplinks"], row["ops"],
                 row["uncovered"], row["tops"], name))
    # INDEX は在るファイル全部で組む(今回出さなかったコーパスの行を消さない)
    existing = {}
    for name in sorted(set(CORPORA) | set(CURATED)):
        p = os.path.join(out_dir, name + ".md")
        if name in rows:
            existing[name] = rows[name]
        elif os.path.isfile(p):
            md = _read(p)
            m = re.search(r"built (\d{4}-\d{2}-\d{2})", md)
            tops = [ln for ln in md.splitlines() if ln.startswith("## ") and ln not in ("## 目次", "## op → クラスタ(逆引き)")]
            existing[name] = {"documents": int(re.search(r"\*\*([\d,]+) 本\*\*", md).group(1).replace(",", "")),
                              "clusters": int(re.search(r"\*\*(\d+) クラスタ\*\*", md).group(1)), "tops": len(tops),
                              "leaves": md.count("\n### "), "papers": len(re.findall(r"^  - .+\((?:\d{4}|n\.d\.)\)\. ", md, re.M)),
                              "oplinks": len(re.findall(r"\]\(\.\./ops/", md.split("## op → クラスタ")[0])), "ops": md.count("\n| [`"),
                              "uncovered": md.count("**op に落ちていない**"), "built": m.group(1) if m else ""}
    with open(os.path.join(out_dir, "INDEX.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(build_index(existing, idx.n_notes, {n: _title(a.repo, n) for n in existing}, dead_themes(rows)))
    _dead = dead_themes(rows)
    if _dead:
        print("literature: %d theme(s) matched no cluster: %s" % (len(_dead), "; ".join(th for _t, th in _dead)))
    print("literature INDEX: %d corpora (%s)" % (len(existing), _dt.date.today().isoformat()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
