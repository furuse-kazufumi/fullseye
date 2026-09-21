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

使い方::

    py -3.11 tools/gen_literature_notes.py --rad-root C:/path/to/docs        # 既定 = 環境変数 FULLSEYE_RAD_DIR
    py -3.11 tools/gen_literature_notes.py --rad-root ... --corpus mech_design --max-papers 6

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
}

#: 知識のテーマ(クラスタ名・葉の名前に出る語)→ 使う op と、その理由。**op 名は生成時に実在を検証**する。
#: 当たらない語は当てない(何でも紐づけると嘘になる)。docs 参照だけのテーマ(op 無し)は ops を空にし、doc に入口を書く。
THEME_OPS: list[dict] = [
    {"keys": ("point", "cloud", "clouds", "scan", "scanning", "registration", "reverse"), "theme": "点群 → 当てはめ → CAD(逆設計)",
     "ops": [("voxel_grid_downsample", "スキャン点群を等間隔に間引く"), ("statistical_outlier_removal", "外れ点を落とす"),
             ("estimate_normals", "法線(面の向き)"), ("icp_point2plane", "設計形状との位置合わせ"), ("register_fpfh", "初期姿勢の無い位置合わせ"),
             ("ransac_plane", "平面プリミティブの当てはめ"), ("ransac_cylinder", "円筒の当てはめ(穴・軸)"), ("fit_cone", "円錐"),
             ("poisson_lite", "点群 → メッシュ"), ("chamfer_distance", "設計との形状差"), ("hausdorff_distance", "最悪の形状差")]},
    {"keys": ("mesh", "meshes", "surface", "surfaces", "geometry", "geometric", "shape", "shapes"), "theme": "メッシュ・形状の計測と変換",
     "ops": [("mesh_area", "表面積"), ("mesh_volume", "体積"), ("vertex_curvature", "曲率(角・フィレット)"), ("decimate_qem", "間引き"),
             ("mesh_isotropic_remesh", "等方リメッシュ"), ("mesh_to_voxel", "メッシュ → 体積"), ("mesh_sample_points", "メッシュ → 点群"),
             ("shape_index", "局所形状の型"), ("d2_distribution", "形状の記述子(検索・比較)")]},
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
             ("profile_params", "断面の粗さパラメータ"), ("surface_params", "面の粗さパラメータ")]},
    {"keys": ("injection", "molding", "moulding", "warpage", "shrinkage", "sink", "fault", "faults", "defect", "defects", "flaw", "anomaly", "anomalies"),
     "theme": "外観欠陥の検出(成形・表面)",
     "ops": [("dc_local_contrast_norm", "照明むらを除いた局所コントラスト"), ("dc_rpca_sparse", "背景から外れる疎な欠陥"), ("defect_contrast", "照明条件での欠陥コントラスト"),
             ("illumination_design", "欠陥が出る照明の設計"), ("lighting_sweep", "照明を振って最良を探す"), ("auto_threshold", "二値化"),
             ("blob_count", "欠陥の数"), ("circularity", "形の記述")]},
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
             ("gcode_read", "CNC の G-code も同じ語彙で読む")]},
    {"keys": ("laser", "discharge", "edm", "beam", "ablation", "plasma"), "theme": "レーザ・放電加工(光学)",
     "ops": [("gaussian_beam", "ビームの伝搬"), ("airy_pattern", "集光スポット"), ("depth_of_field", "焦点深度"),
             ("beer_lambert_transmittance", "透過率"), ("fresnel_dielectric", "反射率"), ("irradiance_map", "照度分布")]},
    {"keys": ("solder", "soldering", "reflow", "pcb", "smt", "aoi", "circuit", "board", "boards", "electronic"), "theme": "PCB / SMT の検査",
     "ops": [("ncc_locate", "部品の位置決め"), ("shape_locate", "形状マッチング"), ("edges_sub_pix", "はんだフィレットの輪郭"),
             ("illumination_design", "多方向照明の設計"), ("defect_contrast", "欠陥コントラスト"), ("dc_rpca_sparse", "異物・欠け"),
             ("fbp_volume", "X 線 CT(BGA のボイド)"), ("vol_granulometry", "ボイドの大きさ分布")]},
    {"keys": ("wafer", "wafers", "lithography", "semiconductor", "cmp", "polishing", "etch", "etching", "planarization", "die", "film", "films"),
     "theme": "半導体工程(ウェハ・薄膜)",
     "ops": [("csi_height_map", "白色干渉の高さ"), ("csi_envelope", "干渉包絡"), ("chromatic_confocal_height", "クロマティック共焦点"),
             ("surface_psd", "研磨面のスペクトル"), ("thin_film_reflectance", "薄膜の反射率"), ("dc_rpca_sparse", "パターン欠陥"),
             ("ncc_locate", "ダイの位置"), ("mtf_diffraction", "光学系の解像限界"), ("wavefront_stats", "波面収差")]},
    {"keys": ("spc", "statistical", "capability", "cpk", "quality", "chart", "charts"), "theme": "SPC(管理図・工程能力)",
     "ops": [("spc_xbar_r", "X̄-R 管理図"), ("spc_cusum", "小さなずれの累積検出"), ("spc_ewma", "指数平滑の管理図"),
             ("spc_capability", "Cp / Cpk"), ("spc_hotelling_t2", "多変量の管理"), ("null_distribution", "帰無分布"), ("evidence_quantile", "証拠量の位置")]},
    {"keys": ("twin", "predictive", "maintenance", "prognostic", "prognostics", "bearing", "bearings", "vibration", "vibrations", "condition", "health", "diagnosis", "fault diagnosis"),
     "theme": "予知保全(振動・軸受)",
     "ops": [("bearing_defect_frequencies", "軸受の欠陥周波数"), ("envelope_spectrum", "包絡スペクトル"), ("spectral_kurtosis", "衝撃の帯域"),
             ("cepstrum", "ケプストラム"), ("order_spectrum", "次数スペクトル"), ("stft", "時間周波数"), ("spc_ewma", "劣化の監視"),
             ("motion_magnify", "動画からの振動"), ("phase_displacement", "位相ベースの変位")]},
    {"keys": ("sensor", "sensors", "sensing", "imu", "lidar", "tof", "time-of-flight", "camera", "cameras", "encoder", "calibration", "fusion", "inertial", "navigation", "localization", "slam", "odometry"),
     "theme": "センサ(校正・深度・融合)",
     "doc": "`docs/SENSOR_PLAYBOOK.md`",
     "ops": [("calibration_views", "校正板の合成ビュー"), ("distortion_map", "歪みの地図"), ("pnp_ransac", "外部パラメータ"), ("bundle_adjust", "多視点の同時最適化"),
             ("project_spherical", "LiDAR の球面投影"), ("depth_to_points", "深度 → 点群"), ("normals_from_depth", "深度 → 法線"),
             ("dtof_depth", "dToF の距離"), ("fmcw_range_profile", "FMCW レーダの距離"), ("range_doppler_map", "距離・速度の地図"),
             ("lf_depth_from_focus", "ライトフィールドの深度"), ("photon_uncertainty", "光子計数の誤差棒"), ("spad_deadtime_correct", "SPAD の不感時間補正")]},
    {"keys": ("tactile", "haptic", "haptics", "soft", "skin", "grasp", "grasping"), "theme": "触覚センサ(接触・圧力・ずれ)",
     "ops": [("tac_contact_mask", "接触域"), ("tac_pressure_proxy", "圧力の代理量"), ("tac_shear_field", "ずれ場"),
             ("tac_surface_normal", "接触面の法線"), ("tac_height_from_shading", "陰影からの高さ")]},
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
             ("segment_rigid_motions", "動く部品の分離"), ("fit_rigid", "剛体運動の当てはめ")]},
    {"keys": ("material", "materials", "coating", "coatings", "treatment", "microstructure", "composite", "composites", "polymer", "polymers", "alloy", "alloys", "ceramic", "ceramics", "steel", "corrosion"),
     "theme": "材料(見え方・組織・表面)",
     "ops": [("spectrum_to_srgb", "分光 → 色"), ("thin_film_reflectance", "薄膜の干渉色"), ("material_catalog", "材質の外観表"), ("oren_nayar", "粗い面の反射"),
             ("brdf_microfacet", "微小面の反射"), ("metallic_flake_normals", "メタリック塗装"), ("corrosion_mask", "腐食域"),
             ("cooc_feature_matrix", "組織のテクスチャ"), ("gabor", "方向性のテクスチャ"), ("vol_granulometry", "CT の空隙分布"), ("entropy_image", "組織の乱れ")]},
    {"keys": ("event", "events", "time", "timing", "network", "networks", "wireless", "iot", "synchronization"), "theme": "時間・イベント(高速・非同期)",
     "ops": [("video_spacetime_cube", "時空間の立方体"), ("photon_sample", "光子到達の標本化"), ("tcspc_stats", "時間相関の統計"),
             ("temporal_bandpass", "時間帯域")]},
    {"keys": ("can", "ethercat", "fieldbus", "protocol", "protocols", "embedded", "rtos", "firmware", "bus", "communication"), "theme": "通信・組込み(Fullseye の外)",
     "doc": "`docs/CONNECTIVITY.md`(産業プロトコルの対応表)", "ops": []},
    {"keys": ("fmea", "reliability", "failure", "failures", "risk", "safety", "hazard"), "theme": "信頼性・FMEA(判定の根拠)",
     "doc": "`docs/HARDENING.md`(PoC が上げた堅牢性)・検査ワークフロー層の Verdict",
     "ops": [("null_distribution", "帰無分布(誤報率)"), ("evidence_quantile", "証拠量の位置"), ("spc_capability", "工程能力")]},
    {"keys": ("gear", "gears", "screw", "screws", "bolt", "bolts", "spring", "springs", "cam", "linkage", "linkages", "mechanism", "mechanisms", "compliant", "transmission", "reducer"),
     "theme": "機械要素(歯車・ねじ・機構)",
     "ops": [("polar_unwrap", "歯車の極座標展開(歯形)"), ("cylinder_unwrap", "円筒面の展開(ねじ山)"), ("m1_measure_pairs", "歯厚・ピッチ"),
             ("edges_sub_pix", "歯形の輪郭"), ("envelope_spectrum", "歯車の噛み合い振動"), ("order_spectrum", "次数スペクトル"),
             ("segment_rigid_motions", "機構の動く部品の分離"), ("displacement_series", "変位の時系列")]},
    {"keys": ("scattering", "sar", "radar", "antenna", "antennas", "electromagnetic", "microwave", "acoustic", "acoustics", "ultrasonic", "ultrasound", "wave", "waves"),
     "theme": "波(レーダ・音・超音波)",
     "ops": [("fmcw_range_profile", "FMCW の距離"), ("beamform_delay_sum", "ビームフォーミング"), ("range_doppler_map", "距離・速度"),
             ("angular_spectrum_propagate", "波の伝搬"), ("stft", "時間周波数"), ("gcc_delay", "到達時間差")]},
    {"keys": ("optical", "optics", "imaging", "lens", "lenses", "photonic", "photonics", "vision", "illumination", "lighting", "spectral", "spectroscopy"),
     "theme": "光学・照明・撮像系",
     "ops": [("lens_system", "レンズ系の定義"), ("paraxial_trace", "近軸追跡"), ("mtf_diffraction", "MTF"), ("depth_of_field", "焦点深度"),
             ("illumination_design", "照明設計"), ("illumination_uniformity", "照明の均一性"), ("render_through_lens", "設計レンズ越しの像"),
             ("spectrum_to_srgb", "分光 → 色")]},
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
        missing = sorted({op for th in THEME_OPS for op, _why in th["ops"] if op not in self.ops})
        if missing:
            raise SystemExit("THEME_OPS names ops that are not in the shipped notes (renamed or removed?): %s — fix the table (fail-closed)"
                             % ", ".join(missing))


def _themes_for(text: str) -> list[dict]:
    """テーマの語を、ハイフンを残した形(time-of-flight)と空白に開いた形(point-cloud → point cloud)の両方で照合する。"""
    low = text.lower()
    forms = [" " + re.sub(r"[^a-z0-9\-]+", " ", low) + " ", " " + re.sub(r"[^a-z0-9]+", " ", low) + " "]
    hits = []
    for th in THEME_OPS:
        if any((" " + k + " ") in w for k in th["keys"] for w in forms):
            hits.append(th)
    return hits


def _slug(name: str) -> str:
    """GitHub の見出し ID: 小文字、英数・空白・ハイフン以外を落とし、空白をハイフンに(連続ハイフンは潰さない)。"""
    return re.sub(r"[^\w\- ]", "", name.lower()).replace(" ", "-")


def _fmt_op(idx: OpIndex, op: str, why: str) -> str:
    o = idx.ops[op]
    sig = ("%s → %s" % (o["in"], o["out"])) if (o["in"] or o["out"]) else o["dim"]
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
        m = re.search(r"^\*\*" + re.escape(name) + r":\*\*\s*(.*)$", md, re.M)
        return m.group(1).strip() if m else ""

    authors = field("Authors")
    if authors:
        names = [a.strip() for a in authors.replace(" et al.", "").split(",") if a.strip()]
        authors = names[0] + (" et al." if len(names) > 1 else "") if names else ""
    date = field("Date")
    doi = field("DOI/ID") or field("arXiv")
    url = field("URL")
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
        themes_name = _themes_for(t["name"])
        themes = themes_name + [th for th in _themes_for(" ".join(nv["name"] for nv in navs)) if th not in themes_name]
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
            out.append("- %s: " % th["theme"] + "、".join(_fmt_op(idx, op, why) for op, why in items[:8]))
            for op, _why in items[:8]:
                seen.add(op)
                reverse[op].append(t["name"])
                n_oplink += 1
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
            for th in _themes_for(nv["name"]):
                for op, why in th["ops"]:
                    if all(op != o for o, _w in lops):
                        lops.append((op, why))
            lops = lops[:6]
            if lops:
                out.append("- 使う op: " + "、".join(_fmt_op(idx, op, why) for op, why in lops))
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
           "papers": n_paper, "oplinks": n_oplink, "ops": len(reverse), "uncovered": n_uncovered, "built": built}
    return "\n".join(out) + "\n", row


def build_index(rows: dict[str, dict], n_notes: int) -> str:
    out = ["# 文献層 —— RAD コーパスからの、op に繋がる来歴つき要約\n",
           "<!-- generated by tools/gen_literature_notes.py; do not edit by hand -->\n",
           "Fullseye の RAG(`docs/ops` の op ノート %s 本)は **op を有効に使うための土台**。この層は製造技術の周辺知識"
           "(設計 → 工程 → 検査)を、外部の文献コーパス(raptor の RAD、OpenAlex メタデータ)のクラスタごとに要約し、"
           "**その知識で使う op**(人が書いたテーマ → op の対応表、op 名は生成時に出荷ノートと突き合わせる)と、代表論文の題名・年・DOI を"
           "来歴として付けたもの。抄録は写さない。op ノートと違い**コーパス本体は repo に無い**ので `tools/regen_all.py` の鎖には入れず、"
           "`tools/gen_literature_notes.py --rad-root <RAD>` で作り直す(`tests/test_literature_notes.py` が形を守る)。\n" % f"{n_notes:,}",
           "| 文献層 | 論文 | クラスタ | 上位 | 葉 | 載せた代表論文 | op リンク | 挙がった op | op に落ちていない上位クラスタ | 構築日 |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in rows.items():
        out.append("| [%s](%s.md) | %s | %d | %d | %d | %d | %d | %d | %d / %d | %s |" % (
            CORPORA[name]["title"], name, f"{r['documents']:,}", r["clusters"], r["tops"], r["leaves"], r["papers"], r["oplinks"], r["ops"],
            r["uncovered"], r["tops"], r["built"]))
    out.append("\n**読み方**: 工程・部品の話題 → 該当する文献層のクラスタ → 「使う op」→ op ノート(型の契約・実行できる例)→ 実装。"
               "逆に op から引くときは各ファイル末尾の「op → クラスタ」。\n")
    out.append("**正直な限界**: 文献は原理・選定・校正の研究が中心で、製品カタログ(型番・定格)は含まない。op の対応は人が書いた表で、"
               "当たらないクラスタは「op に落ちていない」と数える(上の列)—— そこが Fullseye に無い領域か、表の未整備。"
               "語の一致(BM25)で op を引く案は、一般語で無関係の op が並んだので捨てた。\n")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rad-root", default=os.environ.get("FULLSEYE_RAD_DIR", ""), help="RAD コーパスの親ディレクトリ(既定 = 環境変数 FULLSEYE_RAD_DIR)")
    ap.add_argument("--corpus", action="append", choices=sorted(CORPORA), help="出すコーパス(既定 = 全部)")
    ap.add_argument("--repo", default=_ROOT, help="Fullseye の checkout(op ノートの在処。既定 = この生成器の 2 つ上)")
    ap.add_argument("--out", default=None, help="出力先(既定 = <repo>/docs/literature)")
    ap.add_argument("--max-papers", type=int, default=6, help="葉クラスタごとに載せる代表論文の上限")
    a = ap.parse_args(argv)
    if not a.rad_root or not os.path.isdir(a.rad_root):
        raise SystemExit("--rad-root (or FULLSEYE_RAD_DIR) must point at the RAD corpus directory; got %r" % a.rad_root)
    out_dir = a.out or os.path.join(a.repo, "docs", "literature")
    idx = OpIndex(a.repo)
    names = a.corpus or sorted(CORPORA)
    os.makedirs(out_dir, exist_ok=True)
    rows = {}
    texts = {}
    for name in names:                                                     # まず全部を組む(途中で止まればファイルは 1 つも触らない)
        texts[name], rows[name] = build_corpus(a.rad_root, name, idx, a.max_papers)
    for name in names:
        with open(os.path.join(out_dir, name + ".md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(texts[name])
        row = rows[name]
        print("literature %-24s %6s papers / %3d clusters / %3d leaves / %4d cited / %4d op links (%3d ops), uncovered top clusters %d/%d -> %s.md"
              % (name, f"{row['documents']:,}", row["clusters"], row["leaves"], row["papers"], row["oplinks"], row["ops"],
                 row["uncovered"], row["tops"], name))
    # INDEX は在るファイル全部で組む(今回出さなかったコーパスの行を消さない)
    existing = {}
    for name in sorted(CORPORA):
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
        f.write(build_index(existing, len(idx.ops)))
    print("literature INDEX: %d corpora (%s)" % (len(existing), _dt.date.today().isoformat()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
