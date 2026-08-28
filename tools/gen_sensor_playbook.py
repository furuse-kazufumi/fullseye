# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_sensor_playbook — センサー種別ごとの推奨 op パイプラインを markdown 台帳に出力。

    py -3.11 tools/gen_sensor_playbook.py [--out docs/SENSOR_PLAYBOOK.md]

目的: 「手元のセンサーは何か」から入って、そのセンサーの生データを扱うのに
**どの op をどの順で組めばよいか**を AI/人が引ける一枚を作る(OP_CATALOG.md が
op 一覧なのに対し、こちらは **sensor → pipeline** のビュー)。

honest 設計(gen_op_catalog.py と同方針): パイプラインで参照する op 名は実際の
``ops3d`` レジストリに問い合わせて in→out/説明を埋める。**存在しない op 名は
"(未登録)" と明示**し、決して捏造しない。curate したマッピング(sensor→ops)は
人が保守し、生成器が実在性を保証する。
"""
from __future__ import annotations

import argparse
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


# --------------------------------------------------------------------------- #
# curate: センサー → パイプライン(各 step の ops は実在名。生成器が検証する)     #
# --------------------------------------------------------------------------- #
SENSORS = [
    {
        "id": "lidar", "name": "LiDAR(3D 点群)",
        "data": "無秩序3D点群(LAS/LAZ=laspy, PCD=pypcd4 で取り込み)。屋外・広域・疎。",
        "pipeline": [
            {"step": "整形・ノイズ除去", "ops": ["voxel_grid_downsample", "statistical_outlier_removal", "radius_outlier_removal"],
             "why": "密度を揃え外れ点を落として後段を安定化"},
            {"step": "距離画像化(任意)", "ops": ["project_spherical", "unproject_spherical", "project_cylindrical"],
             "why": "回転式LiDARを2D距離画像に畳んで高速処理→戻す"},
            {"step": "法線推定", "ops": ["estimate_oriented_normals", "orient_normals"],
             "why": "一貫向きの法線(平面/物体判定・登録の土台)"},
            {"step": "地面除去・クラスタリング", "ops": ["plane_segmentation", "euclidean_cluster", "region_growing"],
             "why": "地面を剥がし残りを物体クラスタへ"},
            {"step": "特徴・キーポイント", "ops": ["iss_keypoints", "harris3d_keypoints", "compute_fpfh"],
             "why": "疎な対応付け・登録のための記述子"},
            {"step": "位置合わせ(粗→精)", "ops": ["register_fpfh", "gicp", "icp_point2plane", "inlier_ratio", "registration_recall"],
             "why": "FPFHで粗合わせ→GICP/点対面ICPで精合わせ、品質を定量評価"},
            {"step": "バウンディング/計測", "ops": ["aabb", "obb", "min_enclosing_sphere", "convex_hull"],
             "why": "物体の位置・向き・大きさを掴む"},
            {"step": "占有地図・クリアランス", "ops": ["occupancy_grid", "esdf", "inflate", "query_distance"],
             "why": "経路計画用の占有格子と連続距離場"},
            {"step": "動体(2時刻)", "ops": ["nearest_neighbor_flow", "rigid_flow", "smooth_flow", "segment_rigid_motions"],
             "why": "シーンフローと剛体運動の分割"},
        ],
    },
    {
        "id": "depth_camera", "name": "深度カメラ / ToF / RGB-D(整列深度)",
        "data": "格子状(organized)の深度画像+任意RGB。屋内・近接・密。",
        "pipeline": [
            {"step": "点群化・法線", "ops": ["depth_to_organized_points", "depth_to_points", "normals_from_depth"],
             "why": "深度→3D点、格子を活かした高速法線"},
            {"step": "デノイズ・穴埋め", "ops": ["bilateral_filter_depth", "joint_bilateral", "fill_holes"],
             "why": "段差を跨がず平滑化、欠測を補間"},
            {"step": "遮蔽エッジ", "ops": ["occlusion_edges", "bearing_angle_image"],
             "why": "手前/奥の段差を検出(物体境界)"},
            {"step": "平面・物体分離", "ops": ["plane_segmentation", "euclidean_cluster"],
             "why": "台面除去とビンピッキングの物体分離"},
            {"step": "多視点融合・表面", "ops": ["tsdf_from_depth", "fuse", "integrate", "extract_surface_points", "voxel_to_mesh"],
             "why": "複数深度をTSDFへ融合し表面メッシュを抽出"},
            {"step": "メッシュ後処理", "ops": ["taubin_smooth", "decimate_qem", "vertex_normals", "mesh_area"],
             "why": "非収縮平滑化・軽量化・法線/面積計測"},
        ],
    },
    {
        "id": "stereo", "name": "ステレオカメラ(2枚→深度)",
        "data": "既知/未知基線の2画像。対応点から深度・姿勢。",
        "pipeline": [
            {"step": "相対姿勢", "ops": ["fundamental_8point", "essential_8point", "recover_pose", "sampson_distance"],
             "why": "対応点から基礎/基本行列→相対R,t"},
            {"step": "深度(平面掃引)", "ops": ["plane_sweep_depth", "warp_by_plane"],
             "why": "深度平面を掃引しphoto-consistency最小で深度"},
            {"step": "三角測量", "ops": ["triangulate"],
             "why": "対応点+姿勢から3D点を復元"},
            {"step": "姿勢・精緻化", "ops": ["pnp_ransac", "dlt_pose", "reprojection_error", "bundle_adjust"],
             "why": "PnPで姿勢→再投影誤差最小でバンドル調整"},
        ],
    },
    {
        "id": "structured_light", "name": "構造化光(縞投影)",
        "data": "位相シフト/グレイコード縞を投影した複数画像。高精度形状。",
        "pipeline": [
            {"step": "縞合成(検証/生成)", "ops": ["synthesize_fringes"],
             "why": "既知形状から縞画像を合成しGT検証"},
            {"step": "位相復元", "ops": ["wrapped_phase", "unwrap_phase_2d", "graycode_decode", "decode_fringe"],
             "why": "包み位相→アンラップ→絶対位相→高さ"},
            {"step": "3D化", "ops": ["depth_to_points", "voxel_to_mesh", "poisson_lite"],
             "why": "高さ→点群→メッシュ"},
        ],
    },
    {
        "id": "photometric", "name": "フォトメトリックステレオ(多光源)",
        "data": "同一視点・複数の既知光源方向で撮った輝度画像群。微細凹凸。",
        "pipeline": [
            {"step": "法線復元", "ops": ["photometric_stereo", "surface_normals"],
             "why": "陰影群から画素ごとの法線"},
            {"step": "高さ積分", "ops": ["integrate_normals"],
             "why": "法線場を積分して高さ場へ"},
            {"step": "順方向モデル(検証)", "ops": ["render_lambertian"],
             "why": "法線+光源→輝度の順レンダで逆問題を検証"},
        ],
    },
    {
        "id": "ct_volume", "name": "CT / ボリューム(医用・産業X線)",
        "data": "3Dスカラーボリューム(DICOM/NIfTI/NRRD/TIFF=SimpleITK/tifffile)。断層積層。",
        "pipeline": [
            {"step": "前処理(モルフォロジ)", "ops": ["morph_dilate3d", "morph_erode3d", "morph_gradient3d", "morph_tophat3d"],
             "why": "空洞埋め・トゲ除去・境界殻抽出"},
            {"step": "セグメント・計数", "ops": ["label_components", "region_props", "filter_by_volume", "largest_component", "vol_watershed"],
             "why": "連結成分で分離・計測、接触物体はwatershedで割る"},
            {"step": "エッジ・骨格・距離", "ops": ["canny3d", "log_zero_crossings", "edge_points", "signed_distance_field", "skeletonize_vol", "medial_axis_points"],
             "why": "境界抽出・距離場・中軸骨格"},
            {"step": "表面抽出・後処理", "ops": ["voxel_to_mesh", "decimate_qem", "taubin_smooth", "vertex_curvature", "mesh_area"],
             "why": "marching cubesで表面化→軽量化・平滑化・曲率/面積計測"},
            {"step": "形状計測", "ops": ["moment_invariants", "principal_moments", "inertia_tensor", "fit_cone", "fit_torus", "fit_ellipsoid"],
             "why": "不変量・慣性・プリミティブ当てはめで寸法照合"},
        ],
    },
    {
        "id": "monocular_sfm", "name": "単眼カメラ / SfM(複数視点→3D)",
        "data": "1台のカメラで動かし撮った画像列。対応点から構造と運動。",
        "pipeline": [
            {"step": "2視点初期化", "ops": ["fundamental_8point", "essential_8point", "recover_pose", "triangulate"],
             "why": "最初の2枚で姿勢と初期点群"},
            {"step": "姿勢追加(PnP)", "ops": ["pnp_ransac", "reprojection_error"],
             "why": "既知3D点に新規画像を PnP で結合"},
            {"step": "大域最適化", "ops": ["bundle_adjust", "optimize_pose_graph", "relative_pose"],
             "why": "全姿勢+構造をバンドル調整、ループはポーズグラフで"},
            {"step": "2D特徴(対応点の素)", "ops2d": ["features(71)", "edges(57)", "matching(2)"],
             "why": "コーナー/記述子など2D特徴で対応点を作る(詳細=OP_CATALOG.md)"},
        ],
    },
    {
        "id": "multiview_silhouette", "name": "マルチビュー / シルエット(visual hull・3DGS)",
        "data": "複数の既知視点画像/シルエット、または3D Gaussian。",
        "pipeline": [
            {"step": "シルエット彫刻", "ops": ["synthesize_silhouette", "carve", "visual_hull"],
             "why": "多視点シルエットからvisual hullを彫る"},
            {"step": "平面掃引深度", "ops": ["plane_sweep_depth"],
             "why": "既知視点群からの密深度"},
            {"step": "Gaussian→体積", "ops": ["gaussians_to_voxel", "voxel_to_mesh"],
             "why": "3DGSを占有体積化→メッシュ(gsplat 訓練/描画は gsplat_* モジュール)"},
        ],
    },
    {
        "id": "area_camera_2d", "name": "エリアカメラ(2D 産業検査)→ 必要なら3D連携",
        "data": "GigE/CoaXPress/Camera Link のエリアスキャン画像(2D)。外観検査の主戦場。",
        "pipeline": [
            {"step": "2D 前処理・強調", "ops2d": ["smoothing(48)", "filtering", "restoration(12)", "gray(41)", "frequency(19)", "color(8)"],
             "why": "平滑化・復元・階調/周波数/色変換(詳細=OP_CATALOG.md)"},
            {"step": "検出・領域・輪郭", "ops2d": ["edges(57)", "segmentation(56)", "region(76)", "contour(26)", "morphology(33)"],
             "why": "エッジ/領域/輪郭/形態で欠陥・部品を抽出"},
            {"step": "特徴・計測・照合", "ops2d": ["features(71)", "measure1d(5)", "texture(22)", "matching(2)", "subpix(6)"],
             "why": "特徴量・寸法・テクスチャ・テンプレート照合(サブピクセル)"},
            {"step": "3D幾何連携", "ops": ["fit_line_3d", "fit_plane_3d", "fit_circle_3d", "fit_sphere_3d"],
             "why": "校正済みなら2D計測を3D幾何当てはめへ橋渡し"},
        ],
    },
    {
        "id": "sim_render", "name": "センサーシミュレーション / レンダリング(学習データ・デジタルツイン)",
        "data": "CAD/SDF/メッシュから合成センサー出力・映える静止画・学習用データを生成。",
        "pipeline": [
            {"step": "ジオメトリ生成", "ops": ["sphere_sdf", "box_sdf", "sdf_smooth_union", "sdf_subtract", "voxel_to_mesh"],
             "why": "SDFのCSGで形を作りmarching cubesでメッシュ化"},
            {"step": "合成センサー出力", "ops": ["render_point_depth", "render_volume_projection", "project_points"],
             "why": "深度/MIP/投影で疑似センサー画像"},
            {"step": "映える静止3D(hero)", "ops": ["render_beauty", "ambient_occlusion", "cast_shadow", "phong_shade", "matcap_shade", "supersample_mesh", "tonemap_reinhard", "tonemap_aces"],
             "why": "全品質層を合成した hero 画像(render_beauty 一発、または層を個別に)"},
            {"step": "学習データ拡張", "ops": ["jitter", "random_rotation", "random_scale", "random_dropout", "elastic_deform", "cutout"],
             "why": "点群/ボリュームの拡張で頑健性を上げる"},
        ],
    },
]

# 実在する「センサーシミュレーション・デモ」スクリプト(op ではなく走る例)。
_SIM_DEMOS = [
    ("bin_pick.py", "ビンピッキング(乱雑箱→把持)"),
    ("stereo_sim.py", "ステレオ撮像シミュレーション"),
    ("focus_stack.py", "焦点合成(被写界深度合成)"),
    ("polar_cam.py", "偏光カメラ"),
    ("event_camera.py", "イベントカメラ(DVS)"),
    ("pick_render.py", "ピッキング動作レンダ"),
]


def _resolve(name: str):
    """op 名を ops3d で解決 → (io_str, doc) or None(未登録)。"""
    try:
        import ops3d
        info = ops3d.info(name)
        io = f"{', '.join(info.get('in', []))} → {info.get('out', '')}"
        return io, (info.get("doc", "") or "")
    except Exception:
        return None


def _preamble() -> list[str]:
    return [
        "# Fullseye Sensor Playbook — センサー種別ごとの推奨 op パイプライン",
        "",
        "「手元のセンサーは何か」から入って、その生データを扱うのに **どの op をどの順で** "
        "組めばよいかを引く台帳です(op の全一覧は `OP_CATALOG.md`)。",
        "",
        "## この台帳の使い方(assistant 向け)",
        "",
        "1. ユーザーの**センサー種別**(下の見出し)を特定する。",
        "2. そのセクションの**パイプライン段**を上から下へ辿る。各段の op はその順で "
        "`in → out` のデータ種が繋がるように並んでいる。",
        "3. 3D の各 op は実在レジストリ(`ops3d`)から `in → out`/説明を引いており、"
        "`ops3d.get(name)(...)` で呼べる。2D 経路は `OP_CATALOG.md` の該当カテゴリを参照。",
        "4. 各 op の前提・退化条件は fail-closed(捏造せず例外)。GT 例は `examples_3d/` にある。",
        "5. パイプラインは出発点であり、案件に応じて段を足し引きしてよい。",
        "",
    ]


def build() -> str:
    lines = _preamble()
    unresolved: list[str] = []
    for s in SENSORS:
        lines.append(f"## {s['name']}")
        lines.append("")
        lines.append(f"- **データ**: {s['data']}")
        lines.append("")
        for st in s["pipeline"]:
            lines.append(f"### {st['step']}")
            lines.append(f"_{st['why']}_")
            lines.append("")
            for name in st.get("ops", []):
                r = _resolve(name)
                if r is None:
                    unresolved.append(f"{s['id']}:{name}")
                    lines.append(f"- `{name}` (未登録: ops3d に無い — 要確認)")
                else:
                    io, doc = r
                    lines.append(f"- `{name}` (`{io}`) — {doc}")
            for cat in st.get("ops2d", []):
                lines.append(f"- 2D: **{cat}** カテゴリ(詳細は OP_CATALOG.md)")
            lines.append("")
    # sensor-sim demos(実在ファイルのみ)
    lines.append("## センサーシミュレーション・デモ(走る例スクリプト)")
    lines.append("")
    for fn, desc in _SIM_DEMOS:
        exists = os.path.exists(os.path.join(_REPO, fn))
        mark = "" if exists else " (未確認)"
        lines.append(f"- `{fn}`{mark} — {desc}")
    lines.append("")
    if unresolved:
        lines.append("## 生成時の未解決 op(捏造せず明示)")
        lines.append("")
        lines += [f"- {u}" for u in unresolved]
        lines.append("")
    return "\n".join(lines) + "\n", unresolved


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(_REPO, "docs", "SENSOR_PLAYBOOK.md"))
    args = ap.parse_args()
    md, unresolved = build()
    targets = [args.out]
    shipped = os.path.join(_REPO, "fullseye", "SENSOR_PLAYBOOK.md")
    if os.path.isdir(os.path.dirname(shipped)) and os.path.abspath(shipped) != os.path.abspath(args.out):
        targets.append(shipped)
    for path in targets:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"wrote {path} ({len(md):,} bytes, {md.count(chr(10))} lines)")
    if unresolved:
        print(f"WARNING: {len(unresolved)} unresolved op refs: {unresolved}")
        return 1
    print("all op references resolved against ops3d registry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
