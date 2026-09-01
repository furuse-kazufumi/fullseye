# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ops3d — fullseye 3D ビジョン op の統一レジストリ(全 op を一望・組み合わせ可能に)。

散らばった 3D op(match3d / feat_* / fuse3d)を 1 つのカタログに「対応」させ、カテゴリ・入出力の
種別・GPU 対応・一行説明を付ける。これにより **op × op の組み合わせ**(あるカテゴリの出力 = 別の
op の入力)を機械的に列挙・スコアリングでき、指数的な拡張候補を優先度づけできる(docs/OP_COMBINATION_MATRIX.md)。

使い方:
    import ops3d
    ops3d.list_ops("match_localize")        # カテゴリ内の op 名
    ops3d.get("match_shape_3d")(...)        # 実体を取得して呼ぶ
    ops3d.compatible("register_fpfh")       # 出力が別 op の入力になる後続候補
"""
import numpy as np

import match3d
import feat_harris
import feat_spin
import feat_shot
import feat_fpfh
import fuse3d
import photometric
import range_image
import pcl_filter
import fringe
import deform3d
import medial
import metrics3d
import ransac_fit
import edges3d
import recon3d
import curve3d
import descriptors3d
import bspline_surf
import pnp3d
import regionprops3d
import twoview
import curvature3d
import moments3d
import geodesic3d
import visualhull
import superquadric
import bundle3d
import tsdf_fusion
import pcl_augment
import gicp
import segment3d
import pose_graph
import normals_orient
import scene_flow3d
import occupancy
import symmetry3d
import spherical_proj
import motion_seg3d
import plane_sweep
import sdf_ops
import depth_bilateral
import registration_eval
# --- Wave A: mesh processing / bounds / extended primitive fits ---
# 新規 op(hull3d/mesh_smooth/mesh_props/fit_primitives_ext)に加え、実在するが
# レジストリ未登録だった正統 op(meshrepair/pcseg/volops)も surface して発見可能にする。
import hull3d
import mesh_smooth
import mesh_props
import fit_primitives_ext
import meshrepair
import pcseg
import volops
# --- Wave B: rendering quality ops(AO/shadow/matcap-Phong/SSAA/tonemap = 映える静止3D)---
import render_ao
import render_shadow
import render_shade
import render_ssaa
import render_tonemap
import render_beauty  # capstone: 全品質層を一発合成する hero レンダラ
# --- Wave C: 3-D metrology fits (measure.py の (depth,row,col) 版) ---
import measure3d
# --- Wave D: RLE 領域(効率レイヤ。2-D HALCON region の run-length を voxel 界へ)---
import volregion
# --- Wave E: 2D→3D ギャップ第2波(gray/幾何変換/probe/FFT/復元。NEXT_OPS_PLAN §D)---
import volgray
import volxform
import volprobe
import volfreq
import volrestore

_MOD = {"match3d": match3d, "feat_harris": feat_harris, "feat_spin": feat_spin,
        "feat_shot": feat_shot, "feat_fpfh": feat_fpfh, "fuse3d": fuse3d,
        "photometric": photometric, "range_image": range_image, "pcl_filter": pcl_filter,
        "fringe": fringe, "deform3d": deform3d, "medial": medial,
        "metrics3d": metrics3d, "ransac_fit": ransac_fit, "edges3d": edges3d, "recon3d": recon3d,
        "curve3d": curve3d, "descriptors3d": descriptors3d, "bspline_surf": bspline_surf,
        "pnp3d": pnp3d, "regionprops3d": regionprops3d,
        "twoview": twoview, "curvature3d": curvature3d,
        "moments3d": moments3d, "geodesic3d": geodesic3d,
        "visualhull": visualhull, "superquadric": superquadric,
        "bundle3d": bundle3d, "tsdf_fusion": tsdf_fusion, "pcl_augment": pcl_augment,
        "gicp": gicp, "segment3d": segment3d,
        "pose_graph": pose_graph, "normals_orient": normals_orient,
        "scene_flow3d": scene_flow3d, "occupancy": occupancy,
        "symmetry3d": symmetry3d, "spherical_proj": spherical_proj,
        "motion_seg3d": motion_seg3d,
        "plane_sweep": plane_sweep, "sdf_ops": sdf_ops,
        "depth_bilateral": depth_bilateral, "registration_eval": registration_eval,
        "hull3d": hull3d, "mesh_smooth": mesh_smooth, "mesh_props": mesh_props,
        "fit_primitives_ext": fit_primitives_ext, "meshrepair": meshrepair,
        "pcseg": pcseg, "volops": volops, "volregion": volregion,
        "volgray": volgray, "volxform": volxform, "volprobe": volprobe,
        "volfreq": volfreq, "volrestore": volrestore,
        "render_ao": render_ao, "render_shadow": render_shadow, "render_shade": render_shade,
        "render_ssaa": render_ssaa, "render_tonemap": render_tonemap,
        "render_beauty": render_beauty,
        "measure3d": measure3d}

# 入出力の「種別」語彙(op 連結の型検査に使う):
#   voxel / points(N,3) / mesh / depth / sdf / normals(N,3) / gaussians / image2d /
#   pose(R,t) / transform-params(angle,scale,shift) / position / primitive(plane/sphere/...) /
#   descriptor / keypoints((N,2) 等の画像平面上の点列) / flow /
#   measurement(scalar) / render(image2d) /
#   pointmap(H,W,3 organized 点群) / normalmap(H,W,3 organized 法線) / images(list) /
#   indices(元配列への index 列) / table(dict の列=多物体プロパティ) /
#   signal(1-D array=点ごと/サンプルごとの値列) / pairs((2,n)=x-y の対列) /
#   poly_surface / bspline_surface / bspline_curve(いずれも曲面/曲線モデル。
#     互換性が無いので別語彙 — 下の surface_fit / freeform のコメント参照)
#   ※ organized 系は (N,3) と別型(連鎖ファザー 2026-08-31 で申告と実返却の乖離
#     20 種を検出し、型語彙を実態に合わせて分離した)

# カテゴリ → [(op 名, module, [入力種別], 出力種別, gpu)]
_CATALOG = {
    "transform": [  # データ形式の変換(構造 → 別構造/共通表現)
        ("points_to_voxel", "match3d", ["points"], "voxel", True),
        # 第 1 引数は gaussians の入れ物ではなく **means (N,3)**(scales/opacities は
        # 別引数)。旧宣言 ["gaussians"] は dict を means の位置へ渡させていた
        ("gaussians_to_voxel", "match3d", ["points"], "voxel", True),
        ("mesh_to_voxel", "match3d", ["mesh"], "voxel", True),
        ("mesh_to_points", "match3d", ["mesh"], "points", False),
        ("depth_to_points", "match3d", ["depth"], "points", False),
        ("voxel_to_mips", "match3d", ["voxel"], "images", False),
        ("voxel_to_mesh", "match3d", ["voxel"], "mesh", False),
        ("tsdf_from_depth", "match3d", ["depth"], "sdf", False),
        ("signed_distance_field", "match3d", ["voxel"], "sdf", True),
        ("sdf_to_occupancy", "match3d", ["sdf"], "voxel", False),
        ("estimate_point_normals", "match3d", ["points"], "normals", False),
        ("to_points", "fuse3d", ["voxel", "points", "mesh", "depth", "gaussians"], "points", False),
    ],
    "feature": [  # 微分/曲率など局所特徴場
        ("sobel3d", "match3d", ["voxel"], "gradient", True),
        ("hessian3d", "match3d", ["voxel"], "hessian", True),
        ("curvature_maps", "match3d", ["voxel"], "curvature", True),
        ("edt_jfa", "match3d", ["voxel"], "sdf", True),
        # volops の Hessian 固有値ベース特徴(2026-08-31 登録。実装は既存・api 公開済み
        # だったが _CATALOG に無く発見不能だった)。医用 CT の血管/気道・産業 CT の欠陥
        ("vol_frangi", "volops", ["voxel"], "voxel", False),
        ("vol_sato", "volops", ["voxel"], "voxel", False),
        ("vol_hessian_blobness", "volops", ["voxel"], "voxel", False),
        ("vol_gradient_magnitude", "volops", ["voxel"], "voxel", False),
        ("vol_local_maxima", "volops", ["voxel"], "points", False),
    ],
    "domain": [  # 処理領域(HALCON domain 概念の voxel 版。crop がメモリ削減の要 —
        #          512^3 → ROI 128^3 で 64x。Hessian 系の MAX_EIGEN_VOXELS 突破の正攻法)
        ("vol_reduce_domain", "volops", ["voxel", "voxel"], "voxel", False),
        ("vol_bounding_box", "volops", ["voxel"], "primitive", False),
        ("vol_crop_domain", "volops", ["voxel"], "voxel", False),
        ("vol_uncrop", "volops", ["voxel"], "voxel", False),
        # z スラブ streaming(局所 op 限定・overlap >= 空間 footprint で厳密一致。
        # crop=どこを計算するか / RLE=何を保持するか / tiled=一度に RAM に載る量)
        ("vol_tiled_map", "volops", ["voxel"], "voxel", False),
    ],
    "boundary": [  # 境界抽出(2-D region_boundary の voxel 版 + voxel→points 橋渡し。
        #            中実領域は殻だけ残して 1-2% に落ちる = 省メモリ表現)
        ("vol_boundary", "volops", ["voxel"], "voxel", False),
        ("vol_boundary_points", "volops", ["voxel"], "points", False),
    ],
    "rle_region": [  # run-length 領域(HALCON region の効率の正体を voxel 界へ。
        #              実測: 384^3 部品マスクで dense bool の 1/145、volume/bbox は
        #              decode 不要の直接演算で ~300-1000x 速い。保管・多数領域向け)
        ("vol_rle_encode", "volregion", ["voxel"], "rle_region", False),
        ("vol_rle_decode", "volregion", ["rle_region"], "voxel", False),
        ("vol_rle_volume", "volregion", ["rle_region"], "measurement", False),
        ("vol_rle_bbox", "volregion", ["rle_region"], "primitive", False),
        ("vol_rle_centroid", "volregion", ["rle_region"], "position", False),
        # run のままの集合演算(HALCON region 演算の本体。voxel 数に一切触れない)
        ("vol_rle_union", "volregion", ["rle_region", "rle_region"], "rle_region", False),
        ("vol_rle_intersect", "volregion", ["rle_region", "rle_region"], "rle_region", False),
        ("vol_rle_difference", "volregion", ["rle_region", "rle_region"], "rle_region", False),
        # 成分分解(run 内はラベル一定、という構造事実で run 単位に振り分け)
        ("vol_rle_components", "volregion", ["voxel"], "rle_region", False),
    ],
    "gray": [  # 強度変換(2D gray 41op の voxel 版第一陣。CT windowing が旗艦)
        ("vol_window_level", "volgray", ["voxel"], "voxel", False),
        ("vol_equalize", "volgray", ["voxel"], "voxel", False),
        ("vol_gamma", "volgray", ["voxel"], "voxel", False),
        ("vol_stretch", "volgray", ["voxel"], "voxel", False),
    ],
    "geom_transform": [  # 幾何変換(resize/rotate/affine。位置合わせ後の再サンプリング)
        ("vol_resize", "volxform", ["voxel"], "voxel", False),
        ("vol_rotate", "volxform", ["voxel"], "voxel", False),
        ("vol_affine", "volxform", ["voxel"], "voxel", False),
    ],
    "probe": [  # virtual probe(measure1d の 3D 版 = 産業 CT 肉厚計測の核)
        ("vol_profile_line", "volprobe", ["voxel"], "pairs", False),
        ("vol_edge_probe", "volprobe", ["voxel"], "table", False),
        ("vol_wall_thickness", "volprobe", ["voxel"], "signal", False),
    ],
    "frequency": [  # 3D FFT フィルタ(2D frequency 19op の voxel 版第一陣)
        ("vol_fft_lowpass", "volfreq", ["voxel"], "voxel", False),
        ("vol_fft_highpass", "volfreq", ["voxel"], "voxel", False),
        ("vol_fft_bandpass", "volfreq", ["voxel"], "voxel", False),
    ],
    "restoration": [  # 復元(Richardson-Lucy 3D デコンボリューション=顕微鏡定番)
        ("vol_gaussian_psf", "volrestore", ["measurement"], "voxel", False),
        ("vol_richardson_lucy", "volrestore", ["voxel", "voxel"], "voxel", False),
    ],
    "morphology": [  # 3D モルフォロジー(前処理/特徴抽出。torch 不在時は scipy 経路)
        ("morph_dilate3d", "match3d", ["voxel"], "voxel", True),
        ("morph_erode3d", "match3d", ["voxel"], "voxel", True),
        ("morph_open3d", "match3d", ["voxel"], "voxel", True),
        ("morph_close3d", "match3d", ["voxel"], "voxel", True),
        ("morph_gradient3d", "match3d", ["voxel"], "voxel", True),
        ("morph_tophat3d", "match3d", ["voxel"], "voxel", True),
        ("morph_blackhat3d", "match3d", ["voxel"], "voxel", True),
    ],
    "match_localize": [  # scene 内でテンプレ位置を出す
        ("match_shape_3d", "match3d", ["voxel", "voxel"], "position", True),
        ("match_chamfer_3d", "match3d", ["voxel", "voxel"], "position", True),
        ("match_curvature_3d", "match3d", ["voxel", "voxel"], "position", True),
        ("match_hough_3d", "match3d", ["voxel", "voxel"], "position", True),
        ("match_mip_2d", "match3d", ["voxel", "voxel"], "position", True),
        ("match_points_ncc", "match3d", ["points", "points"], "position", True),
    ],
    "match_pose": [  # 変換パラメータを出す
        ("match_phase_3d", "match3d", ["voxel", "voxel"], "shift", True),
        ("match_pca", "match3d", ["points", "points"], "pose", False),
        ("moment_axes", "match3d", ["points"], "axes", False),
        ("match_logpolar_z", "match3d", ["voxel", "voxel"], "rot_scale", True),
    ],
    "detect": [  # テンプレ不要の原始形状検出
        ("hough_plane_3d", "match3d", ["voxel"], "primitive", True),
        ("hough_sphere_3d", "match3d", ["voxel"], "primitive", True),
    ],
    "describe": [  # 回転不変な大域記述子/照合
        ("sh_descriptor", "match3d", ["voxel"], "descriptor", True),
        ("match_sh_descriptor", "match3d", ["voxel", "voxel"], "measurement", True),
    ],
    "refine": [  # 粗推定 → 高精度収束
        ("refine_peak_newton", "match3d", ["score", "position"], "position", True),
        ("refine_translation_lk", "match3d", ["voxel", "voxel", "position"], "position", True),
        ("refine_lm", "match3d", ["voxel", "voxel", "position"], "pose", True),
        ("refine_rotation_z", "match3d", ["voxel", "voxel", "angle"], "angle", True),
        ("icp_point2point_3d", "match3d", ["points", "points"], "pose", False),
        ("icp_point2plane", "match3d", ["points", "points", "normals"], "pose", False),
    ],
    "motion": [
        ("scene_flow_lk", "match3d", ["voxel", "voxel"], "flow", True),
    ],
    "feature_register": [  # 疎特徴 keypoint + 記述子 + RANSAC(初期推定なし大回転)
        ("harris3d_keypoints", "feat_harris", ["voxel"], "keypoints", True),
        ("iss_keypoints", "feat_shot", ["points"], "indices", False),
        ("compute_fpfh", "feat_fpfh", ["points", "normals"], "descriptor", False),
        ("shot_descriptor", "feat_shot", ["points", "normals"], "descriptor", False),
        ("register_spin", "feat_spin", ["points", "points"], "pose", False),
        ("register_fpfh", "feat_fpfh", ["points", "points"], "pose", False),
        ("register_shot", "feat_shot", ["points", "points"], "pose", False),
    ],
    "fusion": [  # 全5構造を組み合わせる(TRIZ 統合)
        ("register_cross", "fuse3d", ["any", "any"], "pose", False),
        ("fuse_to_voxel", "fuse3d", ["any"], "voxel", True),
    ],
    "geometry": [  # 幾何メトロロジー(2点→線・3点→面/角度)
        ("line_from_2points", "match3d", ["points"], "primitive", False),
        ("plane_from_3points", "match3d", ["points"], "primitive", False),
        ("angle_3points", "match3d", ["points"], "measurement", False),
        ("angle_between_lines", "match3d", ["primitive"], "measurement", False),
        ("angle_between_planes", "match3d", ["primitive"], "measurement", False),
        ("angle_line_plane", "match3d", ["primitive"], "measurement", False),
        ("distance_point_plane", "match3d", ["points", "primitive"], "measurement", False),
        ("distance_point_line", "match3d", ["points", "primitive"], "measurement", False),
        ("distance_line_line", "match3d", ["primitive"], "measurement", False),
        ("intersect_line_plane", "match3d", ["primitive"], "position", False),
        ("intersect_planes", "match3d", ["primitive"], "primitive", False),
        ("fit_line_3d", "match3d", ["points"], "primitive", False),
        ("fit_plane_3d", "match3d", ["points"], "primitive", False),
        ("fit_sphere_3d", "match3d", ["points"], "primitive", False),
        ("fit_circle_3d", "match3d", ["points"], "primitive", False),
        # measure3d: (depth,row,col) 版 fit + box/sphere 境界。真のギャップ=
        # smallest_box3(最小体積 OBB=smallest_rectangle2 の 3-D 版)/ smallest_sphere3(最小包含球)。
        ("fit_line3", "measure3d", ["points"], "primitive", False),
        ("fit_plane3", "measure3d", ["points"], "primitive", False),
        ("fit_sphere3", "measure3d", ["points"], "primitive", False),
        ("fit_circle3", "measure3d", ["points"], "primitive", False),
        ("smallest_box3_axis", "measure3d", ["points"], "primitive", False),
        ("fit_box3", "measure3d", ["points"], "primitive", False),
        ("smallest_box3", "measure3d", ["points"], "primitive", False),
        ("smallest_sphere3", "measure3d", ["points"], "primitive", False),
    ],
    "surface_fit": [  # 曲面近似 z=f(x,y)
        # 曲面モデルの型は **多項式と B スプラインで分けてある**(旧: 両方 "surface")。
        # 理由(2026-09-01、連鎖ファザーが 7 回叩いた実測を受けて):
        #   * 中身が違う。fit_poly_surface は dict(coef/powers/degree/rms/pv)、
        #     bspline 側は FITPACK の tck(曲面 [tx,ty,c,kx,ky] / 曲線 (t,c,k) の list)。
        #     同じ "surface" と名乗ると eval_poly_surface(model["degree"])に list が
        #     流れ、生の TypeError("list indices must be integers ...")になっていた。
        #   * 「型を分けると誰も産まない死んだ語彙になる」実測もあるが、ここでは
        #     **3 語すべてに台帳内の産出 op と消費 op が揃っている**ので該当しない
        #     (poly_surface: fit_poly_surface → eval_poly_surface /
        #      bspline_surface: fit_bspline_surface → eval_bspline_surface,
        #      surface_residual / bspline_curve: fit_bspline_curve → eval_bspline_curve)。
        #   * 型を分けても素の :func:`get` 呼び出しは守れないので、実体側にも
        #     fail-closed の入口検証を入れてある(match3d.eval_poly_surface /
        #     bspline_surf.eval_bspline_*)。型は連鎖を、検証は直接呼びを守る。
        # なお fit/eval とも x, y(, z)が必須引数なので、in は座標場を明示的に
        # 並べる(旧宣言は 1 入力で、残る座標は外側のヒント表任せだった = 実質
        # 「宣言に無い必須入力」があり、長さが噛み合わず毎回 ValueError だった)。
        ("fit_poly_surface", "match3d", ["image2d", "image2d", "image2d"],
         "poly_surface", False),
        ("eval_poly_surface", "match3d", ["poly_surface", "image2d", "image2d"],
         "image2d", False),
        # (residual (H,W), rms, pv) → adapter で pv を剥がして measurement
        # (形状誤差 = 残差の peak-to-valley が計測の正典。wave-4 TYPEMISS 修正)
        ("surface_form_error", "match3d", ["image2d"], "measurement", False),
        ("background_flatten", "match3d", ["image2d"], "image2d", False),
    ],
    "curvilinear": [  # 曲座標系への展開
        ("polar_unwrap", "match3d", ["image2d"], "image2d", True),
        ("cylinder_unwrap", "match3d", ["voxel"], "voxel", True),
        ("fit_zernike", "match3d", ["image2d"], "descriptor", True),
    ],
    "optics": [  # 鏡面/透明体
        ("reflect", "match3d", ["vector", "normals"], "normals", False),
        ("refract", "match3d", ["vector", "normals"], "normals", False),
        ("fresnel_reflectance", "match3d", ["measurement"], "measurement", False),
        ("normal_from_reflection", "match3d", ["vector", "vector"], "vector", False),
        ("snell_angle", "match3d", ["measurement"], "measurement", False),
    ],
    "render": [  # 射影/レンダリング(3D → 2D 合成、ループを閉じる)
        # (uv (N,2), depth (N,)) を返す。画像は返していないので keypoints
        # (画像平面の点列)+ adapter で depth を剥がす。旧宣言 "image2d" は
        # 型の嘘で、pnp3d 側の "image2d" 宣言と噛み合って PnP を壊していた
        ("project_points", "match3d", ["points"], "keypoints", False),
        ("render_point_depth", "match3d", ["points"], "depth", False),
        ("render_volume_projection", "match3d", ["voxel"], "image2d", True),
        ("render_shaded", "match3d", ["normalmap"], "image2d", False),
        ("ambient_occlusion", "render_ao", ["mesh"], "image2d", False),
        ("cast_shadow", "render_shadow", ["mesh", "vector"], "image2d", False),
        ("phong_shade", "render_shade", ["normalmap"], "image2d", False),
        ("matcap_shade", "render_shade", ["normalmap", "image2d"], "image2d", False),
        ("supersample_mesh", "render_ssaa", ["mesh"], "image2d", False),
        ("antialias", "render_ssaa", ["image2d"], "image2d", False),
        ("edge_alias_energy", "render_ssaa", ["image2d"], "measurement", False),
        ("tonemap_reinhard", "render_tonemap", ["image2d"], "image2d", False),
        ("tonemap_aces", "render_tonemap", ["image2d"], "image2d", False),
        ("render_beauty", "render_beauty", ["mesh"], "image2d", False),
    ],
    "photometric": [  # フォトメトリックステレオ・法線積分(既知光源 → 法線 → 高さ)
        ("photometric_stereo", "photometric", ["images"], "normalmap", False),
        ("surface_normals", "photometric", ["image2d"], "normalmap", False),
        ("integrate_normals", "photometric", ["normalmap"], "image2d", False),
        ("render_lambertian", "photometric", ["normalmap"], "image2d", False),
    ],
    "range_image": [  # organized 深度画像(depth camera → 特徴の橋渡し)
        ("depth_to_organized_points", "range_image", ["depth"], "pointmap", False),
        ("normals_from_depth", "range_image", ["depth"], "normalmap", False),
        ("occlusion_edges", "range_image", ["depth"], "image2d", False),
        ("bearing_angle_image", "range_image", ["depth"], "image2d", False),
    ],
    "preprocess": [  # 点群前処理(pointcloud.py に正準版あり・mls_smooth が固有の新機能)
        ("statistical_outlier_removal", "pcl_filter", ["points"], "points", False),
        ("radius_outlier_removal", "pcl_filter", ["points"], "points", False),
        ("voxel_grid_downsample", "pcl_filter", ["points"], "points", False),
        ("mls_smooth", "pcl_filter", ["points"], "points", False),
        ("volume_downsample", "volops", ["voxel"], "voxel", False),
    ],
    "structured_light": [  # 構造化光・位相シフト profilometry(縞 → 位相 → 高さ)
        ("wrapped_phase", "fringe", ["images"], "image2d", False),
        ("unwrap_phase_2d", "fringe", ["image2d"], "image2d", False),
        ("graycode_decode", "fringe", ["images"], "image2d", False),
        ("decode_fringe", "fringe", ["images"], "depth", False),
        ("synthesize_fringes", "fringe", ["image2d"], "images", False),
    ],
    "deform": [  # 3D 非剛体・変形登録(TPS / non-rigid ICP / CPD)
        ("tps_fit", "deform3d", ["points", "points"], "deformation", False),
        ("tps_warp", "deform3d", ["deformation", "points"], "points", False),
        ("register_nonrigid", "deform3d", ["points", "points"], "points", False),
        ("register_cpd_rigid", "deform3d", ["points", "points"], "pose", False),
    ],
    "medial": [  # TRIZ 線→面: medial surface / 3D 骨格(位相不変照合)
        ("distance_ridge", "medial", ["voxel"], "voxel", False),
        ("skeletonize_vol", "medial", ["voxel"], "voxel", False),
        ("medial_axis_points", "medial", ["voxel"], "points", False),
        ("topology_signature", "medial", ["voxel"], "descriptor", False),
        ("medial_match", "medial", ["voxel", "voxel"], "measurement", False),
        # 骨格グラフ要素(2D の junctions/endpoints/pruning/split の 3D 版。
        # HALCON に voxel 骨格のグラフ op は無い = 差別化領域)
        ("skeleton_junctions3d", "medial", ["voxel"], "voxel", False),
        ("skeleton_endpoints3d", "medial", ["voxel"], "voxel", False),
        ("skeleton_prune3d", "medial", ["voxel"], "voxel", False),
        ("skeleton_branches3d", "medial", ["voxel"], "voxel", False),
        # spacing 対応の物理距離 EDT(edt_jfa は torch 必須の SDF、こちらは scipy 経路)
        ("vol_distance_transform", "volops", ["voxel"], "voxel", False),
    ],
    "metrics": [  # 評価メトリクス(進化探索の fitness 土台 = 一致度を数値化)
        ("chamfer_distance", "metrics3d", ["points", "points"], "measurement", False),
        ("hausdorff_distance", "metrics3d", ["points", "points"], "measurement", False),
        # (f, precision, recall) を返す → adapter で F 値を剥がして measurement
        ("fscore", "metrics3d", ["points", "points"], "measurement", False),
        ("rmse_correspondence", "metrics3d", ["points", "points"], "measurement", False),
        ("normal_consistency", "metrics3d", ["points", "normals"], "measurement", False),
        ("voxel_iou", "metrics3d", ["voxel", "voxel"], "measurement", False),
        ("pose_error", "metrics3d", ["pose", "pose"], "measurement", False),
    ],
    "robust_fit": [  # RANSAC 頑健プリミティブ適合(外れ値に強い、最小二乗の上位)
        ("ransac_plane", "ransac_fit", ["points"], "primitive", False),
        ("ransac_sphere", "ransac_fit", ["points"], "primitive", False),
        ("ransac_line", "ransac_fit", ["points"], "primitive", False),
        ("ransac_cylinder", "ransac_fit", ["points", "normals"], "primitive", False),
        ("fit_cone", "fit_primitives_ext", ["points"], "primitive", False),
        ("fit_torus", "fit_primitives_ext", ["points"], "primitive", False),
        ("fit_ellipsoid", "fit_primitives_ext", ["points"], "primitive", False),
    ],
    "edges": [  # 3D エッジ抽出(Canny/LoG の 3D 版・検出/照合の前処理)
        ("gradient3d", "edges3d", ["voxel"], "gradient", False),
        ("canny3d", "edges3d", ["voxel"], "voxel", False),
        ("log_zero_crossings", "edges3d", ["voxel"], "voxel", False),
        ("link_edges", "edges3d", ["voxel"], "voxel", False),
        ("edge_points", "edges3d", ["voxel"], "points", False),
    ],
    "reconstruct": [  # 点群 → 表面再構成(voxel を介さず直接メッシュ/境界)
        ("poisson_lite", "recon3d", ["points"], "mesh", False),
        ("alpha_shape_mesh", "recon3d", ["points"], "mesh", False),
        # 返るのは点ではなく **入力点への添字**(docstring どおり (K,) int64)。
        # points((N,3))と宣言していたのは型の嘘 — indices が正しい語彙
        ("alpha_shape_boundary", "recon3d", ["points"], "indices", False),
        ("estimate_alpha", "recon3d", ["points"], "measurement", False),
    ],
    "curve": [  # 空間曲線の微分幾何(曲率・捩率・Frenet・弧長・スプライン平滑)
        # (kappa (N,), tau (N,)) の同格対 → adapter で stack して (2,N) pairs
        # (vol_profile_line と同流儀。wave-4 TYPEMISS 修正)
        ("curvature_torsion", "curve3d", ["points"], "pairs", False),
        ("frenet_frame", "curve3d", ["points"], "frame", False),
        # (cumulative (N,), total float) → adapter で全長スカラを剥がして measurement
        ("arc_length", "curve3d", ["points"], "measurement", False),
        ("resample_uniform", "curve3d", ["points"], "points", False),
        ("fit_spline_curve", "curve3d", ["points"], "points", False),
    ],
    "shape_descriptor": [  # 統計ベース大域形状記述子(検索/分類、回転+スケール不変)
        ("d2_distribution", "descriptors3d", ["points"], "descriptor", False),
        ("a3_distribution", "descriptors3d", ["points"], "descriptor", False),
        ("extent_signature", "descriptors3d", ["points"], "descriptor", False),
        ("describe", "descriptors3d", ["points"], "descriptor", False),
        ("shape_distance", "descriptors3d", ["descriptor", "descriptor"], "measurement", False),
    ],
    "freeform": [  # B スプライン自由曲面/曲線(多項式より柔軟な自由形状計測)
        # 曲面(bisplrep の tck)と曲線(splprep の tck)も別語彙。どちらも list だが
        # 要素の意味が違い([tx,ty,c,kx,ky] vs (t,c,k))、取り違えると bisplev /
        # splev が生の例外で落ちる。surface_fit のコメントと同じ判断。
        ("fit_bspline_surface", "bspline_surf", ["image2d", "image2d", "image2d"],
         "bspline_surface", False),
        ("eval_bspline_surface", "bspline_surf",
         ["bspline_surface", "image2d", "image2d"], "image2d", False),
        # (rms, max, pv) の dict → adapter で pv を剥がして measurement
        # (surface_form_error と同じ「形状誤差 = 残差の peak-to-valley」の正典)
        ("surface_residual", "bspline_surf",
         ["image2d", "image2d", "image2d", "bspline_surface"], "measurement", False),
        ("fit_bspline_curve", "bspline_surf", ["points"], "bspline_curve", False),
        ("eval_bspline_curve", "bspline_surf", ["bspline_curve"], "points", False),
    ],
    "pose_estimation": [  # PnP: 3D-2D 対応 → カメラ姿勢(射影の逆問題)
        # 第 2 引数は **画像平面の (N,2) 点列**であって画像ではない。旧宣言の
        # "image2d" は型の嘘で、ファザーが宣言どおり 32x32 の画像を渡すと
        # 生の IndexError になっていた(2026-09-01 実測 22 回)。既存語彙の
        # keypoints((N,2) 等)が正しい — 産出元は project_points / harris3d_keypoints。
        ("dlt_pose", "pnp3d", ["points", "keypoints"], "pose", False),
        ("pnp_ransac", "pnp3d", ["points", "keypoints"], "pose", False),
        ("reprojection_error", "pnp3d", ["points", "keypoints"], "measurement", False),
    ],
    "regionprops": [  # 3D 連結成分の多物体計測(検査で複数部品を一括)
        # (labels, n) を返す。旧宣言 "voxel" は 2 重に嘘だった(タプルであること、
        # および中身が二値ボリュームでなくラベル場であること)。vol_label と
        # 同じ "labels" + adapter に揃える(同クラス一掃、2026-09-01)
        ("label_components", "regionprops3d", ["voxel"], "labels", False),
        ("region_props", "regionprops3d", ["voxel"], "table", False),
        ("largest_component", "regionprops3d", ["voxel"], "voxel", False),
        ("filter_by_volume", "regionprops3d", ["voxel"], "voxel", False),
        ("inner_box3", "regionprops3d", ["voxel"], "primitive", False),  # 最大内接ボックス(inner_rectangle1 の 3D 版)
        # volops 系(6/18/26 連結の明示指定と spacing 物理量が regionprops3d との差)。
        # vol_region_props の入力は vol_label の返すラベルボリューム(in="labels")。
        # 注: vol_label は (labels, n) のタプルを返すので、連鎖はタプルを外して
        # labels, n = vol_label(m); vol_region_props(labels) と書く(examples 参照)
        ("vol_label", "volops", ["voxel"], "labels", False),
        ("vol_region_props", "volops", ["labels"], "table", False),
    ],
    "two_view": [  # 2視点エピポーラ幾何(対応点 → 相対姿勢 + 構造、単眼 SfM/VO の核)
        ("fundamental_8point", "twoview", ["image2d", "image2d"], "matrix", False),
        ("essential_8point", "twoview", ["image2d", "image2d"], "matrix", False),
        ("recover_pose", "twoview", ["image2d", "image2d"], "pose", False),
        ("triangulate", "twoview", ["image2d", "image2d"], "points", False),
        ("sampson_distance", "twoview", ["image2d", "image2d"], "measurement", False),
    ],
    "curvature": [  # 点群の主曲率/shape index(把持アフォーダンス・凸凹鞍点分類)
        ("principal_curvatures", "curvature3d", ["points"], "curvature", False),
        # 点ごとの曲率列 (N,) — スカラでなく 1-D 配列なので signal 宣言
        # (vol_wall_thickness と同流儀。wave-4 TYPEMISS 修正)
        ("mean_curvature", "curvature3d", ["points"], "signal", False),
        ("gaussian_curvature", "curvature3d", ["points"], "signal", False),
        ("shape_index", "curvature3d", ["points"], "descriptor", False),
        ("estimate_normals", "curvature3d", ["points"], "normals", False),
    ],
    "moment_invariant": [  # 3D モーメント不変量(並進/回転/スケール不変な形状シグネチャ)
        # 注: shape_distance は descriptors3d に既存のため衝突回避で未登録(descriptor 距離はそちらを使う)
        ("moment_invariants", "moments3d", ["points"], "descriptor", False),
        ("principal_moments", "moments3d", ["points"], "descriptor", False),
        ("central_moments", "moments3d", ["points"], "descriptor", False),
        ("inertia_tensor", "moments3d", ["points"], "matrix", False),
    ],
    "geodesic": [  # 曲面上の測地距離(TRIZ 線→面: EDT の曲面版)
        # 返るのは点ごと/頂点ごとの距離列 (N,) であってスカラではない。
        # mean_curvature / vol_wall_thickness と同じ signal 語彙が正しい
        ("geodesic_distances", "geodesic3d", ["points"], "signal", False),
        ("geodesic_mesh", "geodesic3d", ["mesh"], "signal", False),
        ("farthest_point_sampling", "geodesic3d", ["points"], "indices", False),
        ("knn_graph", "geodesic3d", ["points"], "graph", False),
    ],
    "space_carving": [  # シルエットからの空間彫刻/visual hull(多視点 → voxel)
        ("carve", "visualhull", ["images"], "voxel", False),
        ("visual_hull", "visualhull", ["images"], "voxel", False),
        ("synthesize_silhouette", "visualhull", ["points"], "image2d", False),
    ],
    "superquadric": [  # スーパー2次曲面フィット(把持・物体モデリングの汎用形状族)
        ("fit_superquadric", "superquadric", ["points"], "primitive", False),
        # 第 1 引数は primitive(dict)ではなく半径 (a1,a2,a3) の 3-ベクトル。
        # eps・姿勢は別引数なので、既存語彙で正しいのは vector
        ("sample_surface", "superquadric", ["vector"], "points", False),
        ("inside_outside", "superquadric", ["points"], "measurement", False),
        ("superquadric_residual", "superquadric", ["points"], "measurement", False),
    ],
    "bundle_adjust": [  # N視点バンドル調整(全カメラ姿勢+3D構造を再投影誤差最小で同時最適化)
        ("bundle_adjust", "bundle3d", ["pose", "points"], "pose", False),
        ("mean_reprojection_error", "bundle3d", ["pose", "points"], "measurement", False),
        ("project", "bundle3d", ["points"], "image2d", False),
    ],
    "tsdf_fusion": [  # 多フレーム TSDF 体積融合(KinectFusion 核・複数深度→表面)
        ("fuse", "tsdf_fusion", ["depth"], "sdf", False),
        ("integrate", "tsdf_fusion", ["sdf", "depth"], "sdf", False),
        ("extract_surface_points", "tsdf_fusion", ["sdf"], "points", False),
    ],
    "augment": [  # 3D 点群データ拡張(Physical AI 学習支援)
        ("jitter", "pcl_augment", ["points"], "points", False),
        ("random_rotation", "pcl_augment", ["points"], "points", False),
        ("random_scale", "pcl_augment", ["points"], "points", False),
        ("random_dropout", "pcl_augment", ["points"], "points", False),
        ("elastic_deform", "pcl_augment", ["points"], "points", False),
        ("cutout", "pcl_augment", ["points"], "points", False),
    ],
    "gicp": [  # Generalized-ICP(plane-to-plane 共分散重み ICP、平面的点群で優位)
        ("gicp", "gicp", ["points", "points"], "pose", False),
        ("estimate_covariances", "gicp", ["points"], "descriptor", False),
    ],
    "segment": [  # 点群セグメンテーション(法線領域成長/Euclidean/平面抽出)
        ("region_growing", "segment3d", ["points"], "labels", False),
        ("euclidean_cluster", "segment3d", ["points"], "labels", False),
        ("plane_segmentation", "segment3d", ["points"], "labels", False),
        ("vol_watershed", "volops", ["voxel"], "labels", False),
    ],
    "pose_graph": [  # 姿勢グラフ最適化(SLAM back-end: 相対姿勢+ループ閉じ→大域姿勢)
        ("optimize_pose_graph", "pose_graph", ["pose"], "pose", False),
        ("relative_pose", "pose_graph", ["pose", "pose"], "pose", False),
        ("mean_edge_error", "pose_graph", ["pose"], "measurement", False),
    ],
    "normals_orient": [  # 一貫向き付き点群法線(MST伝播、curvature3d の凹/凸符号を正す)
        # 注: estimate_normals は curvature3d に既存名があるため衝突回避で未登録
        ("estimate_oriented_normals", "normals_orient", ["points"], "normals", False),
        ("orient_normals", "normals_orient", ["points", "normals"], "normals", False),
    ],
    "scene_flow3d": [  # 点群ベース3Dシーンフロー(剛体/非剛体分解、match3dのvoxel版と別)
        ("nearest_neighbor_flow", "scene_flow3d", ["points", "points"], "flow", False),
        ("rigid_flow", "scene_flow3d", ["points", "points"], "pose", False),
        ("smooth_flow", "scene_flow3d", ["points", "points"], "flow", False),
    ],
    "occupancy": [  # 占有グリッド + ESDF + 膨張(ロボット計画用、3D)
        ("occupancy_grid", "occupancy", ["points"], "voxel", False),
        ("esdf", "occupancy", ["voxel"], "sdf", False),
        ("inflate", "occupancy", ["voxel"], "voxel", False),
        ("query_distance", "occupancy", ["sdf", "points"], "measurement", False),
    ],
    "symmetry": [  # 対称性検出(反射面/回転軸、chamfer で採点=形状補完・正準姿勢・左右差検査)
        ("detect_reflection_symmetry", "symmetry3d", ["points"], "primitive", False),
        ("detect_rotational_symmetry", "symmetry3d", ["points"], "primitive", False),
        ("reflect_points", "symmetry3d", ["points"], "points", False),
        ("reflection_symmetry_score", "symmetry3d", ["points"], "measurement", False),
    ],
    "lidar_projection": [  # 回転式 LiDAR の球面/円柱レンジ画像(点群⇄レンジ画像)
        ("project_spherical", "spherical_proj", ["points"], "image2d", False),
        ("unproject_spherical", "spherical_proj", ["image2d"], "points", False),
        ("project_cylindrical", "spherical_proj", ["points"], "image2d", False),
    ],
    "motion_segment": [  # 剛体運動セグメンテーション(2点群→運動が一致する剛体ごとに分割、動的シーン)
        # dict{"labels","motions"} を返す(シグネチャ自身が -> dict)。motions は
        # この op の存在理由なので返りは削らず、adapter で labels を取り出す
        # (opslightfield の lf_depth_from_focus と同じ流儀)
        ("segment_rigid_motions", "motion_seg3d", ["points", "points"], "labels", False),
        ("estimate_flow", "motion_seg3d", ["points", "points"], "flow", False),
        ("fit_rigid", "motion_seg3d", ["points", "points"], "pose", False),
    ],
    "plane_sweep_stereo": [  # 平面掃引ステレオ(2視点 image + カメラ→密深度、多視点 MVS の基本)
        ("plane_sweep_depth", "plane_sweep", ["image2d", "image2d"], "depth", False),
        ("warp_by_plane", "plane_sweep", ["image2d"], "image2d", False),
    ],
    "sdf_csg": [  # 符号付き距離場の CSG 合成(陰関数ソリッドモデリング、marching cubes へ橋渡し)
        # プリミティブが取るのは **ボクセル中心の座標場 (nx,ny,nz,3)** であって
        # (N,3) の点群ではない。旧宣言 ["points"] → "sdf" は二重に嘘で、点群を
        # 渡すと返りは (N,) の 1-D になり、"sdf"(3-D 場)にならない。座標場を
        # 産む grid_coords は実在するのに未登録で、そのため嘘が露見しなかった
        ("grid_coords", "sdf_ops", [], "coordgrid", False),
        ("sphere_sdf", "sdf_ops", ["coordgrid"], "sdf", False),
        ("box_sdf", "sdf_ops", ["coordgrid"], "sdf", False),
        ("sdf_union", "sdf_ops", ["sdf", "sdf"], "sdf", False),
        ("sdf_intersect", "sdf_ops", ["sdf", "sdf"], "sdf", False),
        ("sdf_subtract", "sdf_ops", ["sdf", "sdf"], "sdf", False),
        ("sdf_smooth_union", "sdf_ops", ["sdf", "sdf"], "sdf", False),
        ("sdf_offset", "sdf_ops", ["sdf"], "sdf", False),
    ],
    "depth_denoise": [  # 深度画像のエッジ保存デノイズ/穴埋め(段差を跨がず平滑、joint は guide 誘導)
        ("bilateral_filter_depth", "depth_bilateral", ["depth"], "depth", False),
        ("joint_bilateral", "depth_bilateral", ["depth", "image2d"], "depth", False),
        ("fill_holes", "depth_bilateral", ["depth"], "depth", False),
    ],
    "registration_metrics": [  # 登録品質の定量評価(inlier/RMSE/recall/回転並進誤差、GT 比較)
        ("inlier_ratio", "registration_eval", ["points", "points"], "measurement", False),
        # (rmse, n_inliers) を返す → adapter で rmse を剥がして measurement
        ("rmse_inliers", "registration_eval", ["points", "points"], "measurement", False),
        ("registration_recall", "registration_eval", ["points", "points"], "measurement", False),
        ("rotation_translation_error", "registration_eval", ["pose", "pose"], "measurement", False),
    ],
    "bounds": [  # 凸包・バウンディングボリューム(位置/向き/大きさの基本メトロロジー)
        ("convex_hull", "meshrepair", ["points"], "mesh", False),
        ("aabb", "pcseg", ["points"], "primitive", False),
        ("obb", "pcseg", ["points"], "primitive", False),
        ("min_enclosing_sphere", "hull3d", ["points"], "primitive", False),
    ],
    "mesh_process": [  # 三角形メッシュの処理(平滑化/簡略化/法線・面積・曲率)
        ("laplacian_smooth", "mesh_smooth", ["mesh"], "mesh", False),
        ("taubin_smooth", "mesh_smooth", ["mesh"], "mesh", False),
        ("decimate_qem", "meshrepair", ["mesh"], "mesh", False),
        ("face_normals", "mesh_props", ["mesh"], "normals", False),
        ("vertex_normals", "mesh_props", ["mesh"], "normals", False),
        ("mesh_area", "mesh_props", ["mesh"], "measurement", False),
        ("vertex_curvature", "mesh_props", ["mesh"], "curvature", False),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out, gpu in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = ""
            if fn is not None and fn.__doc__:
                doc = fn.__doc__.strip().splitlines()[0]
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "gpu": gpu, "func": fn, "doc": doc}
    return reg


OPS3D = _build()

#: 「宣言した出力型の値」を実返却から取り出すアダプタ(型忠実呼び出しの要)。
#: 多くの op は本体値+補助情報のタプルを返す(例: vol_label → (labels, n))。
#: 目録の out 型で連鎖する消費者(Studio パイプライン/連鎖ファザー)は
#: :func:`call` を使えば常に宣言型の値を受け取れる。素の関数呼び出しの
#: 返り値仕様は互換のため不変(補助情報が要る呼び手はそのまま直接呼ぶ)。
#: 連鎖ファザー(tools/chain_fuzz.py、2026-08-31)が申告と実返却の乖離を
#: 20 種検出したのを受けて整備した。
RESULT_ADAPTERS = {
    "vol_label": lambda r: r[0],                    # (labels, n)
    "vol_crop_domain": lambda r: r[0],              # (part, offset)
    "distance_ridge": lambda r: r[0],               # (ridge, dist)
    "medial_axis_points": lambda r: r[0],           # (points, radii)
    "link_edges": lambda r: r[0],                   # (linked, n)
    "statistical_outlier_removal": lambda r: r[0],  # (kept, mask)
    "radius_outlier_removal": lambda r: r[0] if isinstance(r, tuple) else r,
    "harris3d_keypoints": lambda r: r[0],           # (keypoints, scores)
    "random_rotation": lambda r: r[0],              # (points, R)
    "random_scale": lambda r: r[0] if isinstance(r, tuple) else r,
    "register_nonrigid": lambda r: r[0],            # (warped, info, info)
    "fuse_to_voxel": lambda r: r[0],                # (voxel, bounds)
    "vol_resize": lambda r: r[0] if isinstance(r, tuple) else r,  # spacing 付き時
    "random_dropout": lambda r: r[0] if isinstance(r, tuple) else r,
    "cutout": lambda r: r[0] if isinstance(r, tuple) else r,
    "photometric_stereo": lambda r: r[0] if isinstance(r, tuple) else r,
    "synthesize_fringes": lambda r: [r[i] for i in range(r.shape[0])]
    if hasattr(r, "shape") and getattr(r, "ndim", 0) == 3 else r,
    # torch Tensor を返す GPU op → numpy(catalog は配列型を宣言している)
    "edt_jfa": lambda r: r.detach().cpu().numpy() if hasattr(r, "detach") else r,
    # probe: (t_mm, values) → (2, n) pairs / list[float] → 1-D signal
    "vol_profile_line": lambda r: np.stack(r) if isinstance(r, tuple) else r,
    "vol_wall_thickness": lambda r: np.asarray(r, np.float64),
    # curve/metrology(wave-4 TYPEMISS 修正): 同格対は stack、補助つきは本体を剥がす
    "curvature_torsion": lambda r: np.stack(r),     # (kappa, tau) → (2, N) pairs
    "arc_length": lambda r: r[1],                   # (cumulative, total) → 全長 float
    "surface_form_error": lambda r: r[2],           # (residual, rms, pv) → pv float
    # --- wave-5(2026-09-01): 「一度も実行されていなかったので見えなかった」乖離 ---
    # カメラ内部行列 K / 姿勢 R,t / RANSAC 閾値などの引数を束縛できるようにして
    # 初めて実行され、そこで露出した非 CONTRACT の署名。
    "project_points": lambda r: r[0],               # (uv (N,2), depth (N,)) → uv
    "segment_rigid_motions": lambda r: r["labels"],  # {"labels", "motions"} → labels
    "surface_residual": lambda r: r["pv"],          # {"rms","max","pv"} → pv float
    "label_components": lambda r: r[0],             # (labels, n) → labels
}


def call(name, *args, **kwargs):
    """op を呼び、**目録の out 型どおりの値**を返す(補助情報つきタプルは剥がす)。

    連鎖・パイプライン用の型忠実入口。素の :func:`get` は互換のため
    生の返り値のまま。"""
    result = OPS3D[name]["func"](*args, **kwargs)
    adapter = RESULT_ADAPTERS.get(name)
    return adapter(result) if adapter is not None else result


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPS3D.items() if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable)。"""
    return OPS3D[name]["func"]


def info(name):
    """op のメタ情報。"""
    return OPS3D[name]


def compatible(name):
    """name の出力種別を入力に取れる後続 op(op × op の連結候補)を列挙。"""
    out = OPS3D[name]["out"]
    return [n for n, m in OPS3D.items()
            if out in m["in"] or "any" in m["in"]]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPS3D.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"ops3d: {len(OPS3D)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for c in categories():
        print(f"  [{c}] {len(list_ops(c))} ops")
