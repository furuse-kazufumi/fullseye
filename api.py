"""fullseye / imgevolve — stable programmatic API for other projects.

This is the surface another project imports. It works on **numpy arrays**
(no file I/O required), so a robotics/vision pipeline can hand imgevolve a frame
and get a measured result back::

    import fullseye                       # or: import api
    import numpy as np
    frame = np.random.rand(480, 640)      # float64 gray in [0, 1]
    edges = fullseye.apply(frame, "sobel_amp")          # HALCON name or op name
    seg   = fullseye.apply(frame, "otsu")               # image -> region (binary)
    n     = fullseye.apply(seg,   "count_obj")          # region -> feature (scalar)
    out   = fullseye.run_pipeline(frame, ["gauss_filter", "sobel_amp", "otsu"])

Operators are resolved by their op **name** first, then by HALCON alias (the same
rule the CLI uses), so both ``"gauss_filter"`` (HALCON) and ``"gaussian"`` (op
name) work. ``a`` and ``b`` are the two knobs, each in ``[0, 1]``.

Sorts (an op's declared input/output type):
  image  H*W float64 in [0, 1]      region  H*W in {0, 1}
  color  H*W*3 RGB float64          feature scalar float (returned as a Python float)
  contour XLD dict {"shape", "cs"}  volume  D*H*W stack

Discover ops with :func:`list_ops` / :func:`op_names`, or the CLI
(``py -3.11 imgevolve.py ops --search edge``).
"""
from __future__ import annotations

import os
import sys
from typing import Iterable, Sequence

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import ops as _ops  # noqa: E402  (the engine registry; imports its backends on load)
import stereo  # noqa: E402  (numpy+scipy depth building blocks)
import terrain  # noqa: E402  (elevation map / traversability)
import imgio  # noqa: E402  (coercion / colormap visualisation / export)
import detect  # noqa: E402  (object segmentation / description / identification)
import registration  # noqa: E402  (rigid point-cloud registration: Kabsch + ICP)
import deformreg  # noqa: E402  (deformable image registration: Thirion's demons + field warp)
import ppf  # noqa: E402  (6-DoF surface matching by Point Pair Features -> object pose for grasping)
import pointcloud  # noqa: E402  (point-cloud geometry: normals, voxel downsample)
import pcseg  # noqa: E402  (point-cloud segmentation/fitting: RANSAC plane/sphere/cylinder, clusters, OBB)
import mesh  # noqa: E402  (3-D object import: OBJ/STL/PLY/OFF -> vertices, points, voxels)
import meshio_opt  # noqa: E402  (optional heavier object formats: glTF/GLB, LAS/LAZ, PCD-binary)
import pose  # noqa: E402  (silhouette posture descriptors)
import locomotion  # noqa: E402  (balance/gait perception: contacts, support polygon, stability margin, gait phase)
import occupancy  # noqa: E402  (2-D occupancy / free-space navigation grids: inflate, clearance, line-of-sight)
import flow  # noqa: E402  (dense optical flow: two-frame motion)
import motion  # noqa: E402  (flow analysis: energy / dominant / segmentation)
import sceneflow  # noqa: E402  (scene flow / ego-motion: FoE, time-to-contact, looming, 3D scene flow)
import features  # noqa: E402  (sparse keypoints/descriptors/matching: Harris/FAST + patch match)
import events  # noqa: E402  (neuromorphic / event-camera vision from frames: DVS events, time surface, contrast max)
import video  # noqa: E402  (read/write video & GIF clips as numpy frames)
import recipes  # noqa: E402  (curated sample pipelines)
import measure  # noqa: E402  (line profiles / distance / angle)
import volio  # noqa: E402  (volumetric/medical import: DICOM/NIfTI/NRRD/MetaImage/TIFF -> volume)
import raster  # noqa: E402  (bit-depth-preserving raster + metric depth: 16-bit/float/PFM)
import render3d  # noqa: E402  (mesh -> depth/silhouette/normals render + SDF + solid voxelization)
import camera  # noqa: E402  (pinhole geometry: project/triangulate/PnP/essential/rectify -- 2D<->3D backbone)
import odometry  # noqa: E402  (visual/RGB-D odometry: frame-to-frame camera motion + trajectory)
import grasp  # noqa: E402  (antipodal grasp synthesis: force-closure + Ferrari-Canny quality)
import meshrepair  # noqa: E402  (watertight/repair/decimate + exact inertia -> sim-ready body)
import volops  # noqa: E402  (3-D volume analysis: Frangi/Sato/label/distance/region props)
import volregion  # noqa: E402  (RLE 3-D regions: run-length masks + direct-on-runs queries)
import handpose  # noqa: E402  (hand 21-keypoint pose + finger flexions; detection needs optional mediapipe)
import complexops  # noqa: E402  (complex/FFT-domain ops + 2-D phase unwrap [HALCON has none])
import specops  # noqa: E402  (multispectral/hyperspectral cube: ENVI + SAM + unmix + band math)
import videops  # noqa: E402  (video / temporal (T,H,W): temporal denoise, bg-subtract, motion, spatiotemporal filters)
import algo  # noqa: E402  (general-algorithm tier: seq/scalar sorts+reductions with Python+C references)
import algo_codegen  # noqa: E402  (standalone Python/C emission for the general tier)
import algo_difftest as _algo_difftest  # noqa: E402  (honest gate: Python==oracle, C==Python bit-for-bit)
import synth  # noqa: E402  (learn an image's features -> synthesise a similar image; classical texture synthesis)
import funct1d  # noqa: E402  (HALCON funct_1d family: 1-D function/profile analysis on the index grid)
import mathops  # noqa: E402  (math for visual metrology: linalg / stats / interp / poly)
import optics  # noqa: E402  (optics for imaging systems: geometric / wave / imaging / polarisation)
from videops import (  # noqa: E402,F401
    temporal_mean, temporal_median, temporal_std, temporal_max, temporal_min,
    frame_difference, background_subtraction, temporal_gradient, motion_energy,
    moving_average, spatiotemporal_gaussian, spatiotemporal_sobel, per_frame,
    flicker_reduce, optical_flow_sequence,
)
from stereo import (  # noqa: E402,F401
    disparity_map, disparity_subpixel, lr_consistency,
    depth_from_disparity, reproject_to_points,
    census_transform, disparity_census, disparity_sgm,
    speckle_filter, fill_disparity, disparity_confidence,
)
from measure import (line_profile, distance, angle,  # noqa: E402,F401
                     fit_line, fit_circle, fit_ellipse, fit_rectangle2)
# 3-D metrology fits — the (depth, row, col) analogue of the 2-D fits above.
# numpy-only (no torch), so always available; the torch-backed op registry below is guarded.
from measure3d import (  # noqa: E402,F401
    fit_line3, fit_plane3, fit_sphere3, fit_circle3,
    smallest_box3, smallest_box3_axis, fit_box3, smallest_sphere3)
from regionprops3d import inner_box3  # noqa: E402,F401  (3-D inner_rectangle1)
import measure3d          # noqa: E402,F401
import regionprops3d      # noqa: E402,F401
try:                      # full typed 3-D op registry + composite pipelines
    import ops3d          # noqa: E402,F401  (needs the `threed` extra — torch)
    import pipeline3d     # noqa: E402,F401
except Exception:         # keep the facade importable on a numpy-only install
    ops3d = None
    pipeline3d = None
from registration import (  # noqa: E402,F401
    kabsch, icp, point_to_plane_icp, apply_transform, pca_align, register, feature_register,
)
from ppf import ppf_model, surface_match, find_surface_pose  # noqa: E402,F401
from pointcloud import (  # noqa: E402,F401
    estimate_normals, voxel_downsample,
    remove_statistical_outliers, remove_radius_outliers, fpfh,
)
from pcseg import (  # noqa: E402,F401
    fit_plane, fit_plane_ransac, fit_sphere_ransac, fit_cylinder_ransac,
    plane_distance, height_above_plane, remove_ground,
    euclidean_clusters, region_growing, aabb, obb, crop_box, crop_sphere,
    farthest_point_sampling, curvature, centroid, principal_axes,
)
from mesh import (  # noqa: E402,F401
    read_mesh, read_points, write_mesh, write_points, sample_surface, mesh_to_points,
    voxelize, bounds, recenter, normalize_scale,
)
from meshio_opt import (  # noqa: E402,F401
    read_gltf, read_gltf_merged, read_las, read_pcd, formats_available,
)
from volio import read_volume, write_volume, list_dicom_series, VolumeMeta  # noqa: E402,F401
from raster import read_raster, to01, read_depth, read_pfm, write_pfm, save16  # noqa: E402,F401
from render3d import (  # noqa: E402,F401
    render_mesh, look_at, intrinsics_from_fov, auto_view, mesh_to_sdf,
    voxelize_solid, marching_cubes,
)
from camera import (  # noqa: E402,F401
    intrinsic_matrix, decompose_intrinsics, projection_matrix,
    project_points, backproject, depth_to_points, normals_from_depth,
    triangulate, reprojection_error, solve_pnp, rodrigues, rotation_log,
    fundamental_matrix, essential_matrix, essential_from_fundamental,
    decompose_essential, recover_pose, epipolar_lines,
    distort_points, undistort_points, stereo_rectify,
)
from odometry import (  # noqa: E402,F401
    rgbd_odometry, pnp_odometry, integrate_trajectory,
    umeyama_align, trajectory_error,
)
from grasp import (  # noqa: E402,F401
    Grasp, sample_antipodal_grasps, grasps_from_mesh, force_closure,
    ferrari_canny_quality, approach_vector_from_normals, rank_grasps,
    grasp_pose, collision_free,
)
from meshrepair import (  # noqa: E402,F401
    is_watertight, is_edge_manifold, boundary_edges, weld_vertices,
    remove_degenerate_faces, orient_consistent, fill_holes, smooth_taubin,
    decimate_qem, convex_hull, inertia_tensor, components,
)
from volops import (  # noqa: E402,F401
    vol_frangi, vol_sato, vol_hessian_blobness, vol_distance_transform,
    vol_label, vol_region_props, vol_gradient_magnitude, vol_local_maxima,
    vol_watershed,
    vol_reduce_domain, vol_bounding_box, vol_crop_domain, vol_uncrop,
    vol_boundary, vol_boundary_points, vol_tiled_map,
)
from volregion import (  # noqa: E402,F401
    VolRLE, vol_rle_encode, vol_rle_decode, vol_rle_volume, vol_rle_bbox,
    vol_rle_centroid, vol_rle_union, vol_rle_intersect, vol_rle_difference,
    vol_rle_components,
)
import volgray  # noqa: E402  (3-D intensity transforms: CT windowing / equalize / gamma / stretch)
import volxform  # noqa: E402  (3-D geometric transforms: resize / rotate / affine)
import volprobe  # noqa: E402  (3-D virtual probe: profile line / edge probe / wall thickness)
import volfreq  # noqa: E402  (3-D FFT filtering: low/high/band-pass)
import volrestore  # noqa: E402  (3-D restoration: Richardson-Lucy deconvolution)
from volgray import (  # noqa: E402,F401
    vol_window_level, vol_equalize, vol_gamma, vol_stretch,
)
from volxform import (  # noqa: E402,F401
    vol_resize, vol_rotate, vol_affine,
)
from volprobe import (  # noqa: E402,F401
    vol_profile_line, vol_edge_probe, vol_wall_thickness,
)
from volfreq import (  # noqa: E402,F401
    vol_fft_lowpass, vol_fft_highpass, vol_fft_bandpass,
)
from volrestore import (  # noqa: E402,F401
    vol_gaussian_psf, vol_richardson_lucy,
)
from handpose import (  # noqa: E402,F401
    hand_landmarks, finger_flexions, hand_skeleton_edges, draw_hand_landmarks,
)
from complexops import (  # noqa: E402,F401
    cx_fft, cx_ifft, cx_magnitude, cx_phase, cx_real, cx_imag, cx_log_magnitude,
    cx_from_mag_phase, phase_unwrap, cx_wiener_deconvolve, cx_apply_transfer_function,
    cx_bandpass,
)
from specops import (  # noqa: E402,F401
    BandMeta, read_envi, write_envi, spec_band, spec_rgb_composite, spec_nearest_band,
    spec_band_ratio, spec_index, spec_angle_mapper, spec_pca, spec_mnf, spec_unmix,
    spec_endmembers_ppi, spec_continuum_removal,
    spec_pansharpen, spec_decorrelation_stretch, spec_fuse,
)
from deformreg import (  # noqa: E402,F401
    warp_by_field, demons_register, field_magnitude, residual_ssd,
)
from pose import pose_descriptor, skeleton_nodes, principal_axis  # noqa: E402,F401
from flow import (  # noqa: E402,F401
    optical_flow_lk, optical_flow_hs, warp_by_flow, flow_magnitude, flow_angle,
    track_points,
)
from motion import (  # noqa: E402,F401
    frame_motion_energy, dominant_motion, flow_from_model, residual_motion,
    motion_segments, motion_energy_series, detect_events,
)
from sceneflow import (  # noqa: E402,F401
    flow_divergence, flow_curl, focus_of_expansion, time_to_contact,
    looming, ego_translation_from_flow, scene_flow,
)
from features import (  # noqa: E402,F401
    harris_corners, fast_corners, describe_patches, match_descriptors, match_keypoints,
)
from events import (  # noqa: E402,F401
    simulate_events, event_count, event_image, event_rate, event_rate_map,
    time_surface, warp_frame, contrast_maximization,
)
from video import (  # noqa: E402,F401
    read_frames, iter_frames, frame_pairs, write_video, probe,
)
from terrain import (  # noqa: E402,F401
    elevation_map, traversability, foothold_score, fill_gaps,
    ground_surface, ground_plane, detect_obstacles,
    fuse_elevation, slope_map, roughness_map, surface_normals,
    step_edges, foothold_candidates,
)
from locomotion import (  # noqa: E402,F401
    contact_points, com_from_silhouette, support_polygon,
    com_support_margin, gait_phase,
)
from occupancy import (  # noqa: E402,F401
    occupancy_grid_2d, inflate_obstacles, clearance_map, line_of_sight, frontier_cells,
)
from imgio import (  # noqa: E402,F401
    to_float01, to_uint8, apply_cmap, colorize_depth, colorize_disparity,
    colorize_labels, colorize_height, colorize_flow, shaded_relief, overlay_mask,
    save, load, save_ply, COLORMAPS,
)
from detect import segment_objects, object_descriptor, nearest_prototype, draw_objects  # noqa: E402,F401
from synth import (  # noqa: E402,F401
    learn_features, synthesize_like, match_histogram, radial_power_spectrum,
    feature_distance, patch_novelty, pyramid_stat_distance,
)
from funct1d import (  # noqa: E402,F401
    smooth_funct_1d_gauss, smooth_funct_1d_mean,
    derivate_funct_1d, integrate_funct_1d,
    zero_crossings_funct_1d, local_min_max_funct_1d,
    funct_1d_to_pairs, abs_funct_1d, negate_funct_1d, scale_y_funct_1d,
    compose_funct_1d, num_points_funct_1d, distance_funct_1d,
    sample_funct_1d, get_pair_funct_1d, invert_funct_1d,
    transform_funct_1d, x_range_funct_1d, y_range_funct_1d,
    get_y_value_funct_1d, create_funct_1d_array, create_funct_1d_pairs,
    match_funct_1d_trans,
)
from mathops import (  # noqa: E402,F401
    mat_solve, mat_lstsq, mat_svd, mat_eigh, mat_pinv, mat_cond,
    stat_describe, stat_histogram, stat_covariance, stat_correlation,
    stat_zscore,
    interp_linear, interp_cubic, poly_fit, poly_eval, poly_roots,    cplx_contour_circle, cplx_poly_eval, cplx_contour_integral,
    cplx_winding_number, cplx_cauchy_value, cplx_argument_principle,
    cplx_laurent_coeffs, cplx_joukowski, cplx_mobius, cplx_cr_residual,
)
# 仮想マシンビジョン環境: 部品を買う前に「その構成で狙う欠陥が見つかるか」を
# 閉形式の光学 + 数式で作った欠陥 + 撮像連鎖で先に確かめる層。
import defectgen  # noqa: E402  (mathematical defect models with pixel-perfect masks)
import visiondesign  # noqa: E402  (closed-form feasibility: resolution / DOF / falloff)
import visionlab  # noqa: E402  (the whole loop: design -> part -> capture -> inspect)
from defectgen import (  # noqa: E402,F401
    defect_scratch, defect_pits, defect_crack, defect_blob,
    surface_texture, composite_defect, defect_stats,
)
from visiondesign import (  # noqa: E402,F401
    system_geometry, resolving_power, system_feasibility, image_formation,
    detectability_limit,
)
from visionlab import (  # noqa: E402,F401
    VisionSystem, render_part, inspection_sweep, detection_report,
)
# ライトフィールド(plenoptic): 4-D (V,U,H,W) を扱う族。1 回の露光から視点・
# リフォーカス・深度を出す経路で、既存の stereo / focus_stack とは入力が違う。
import lightfield  # noqa: E402  (4-D light field: views / refocus / depth)
from lightfield import (  # noqa: E402,F401
    lf_synthesize, lf_from_mla, lf_to_mla, lf_stats,
    lf_subaperture, lf_center_view, lf_views, lf_epi,
    lf_refocus, lf_focal_stack, lf_aperture_mask, lf_synthetic_aperture,
    lf_depth_from_focus, lf_epi_slope, lf_disparity_to_depth, lf_all_in_focus,
    lf_plenoptic_design,
)
# 光子計数・時間分解: 光が「連続した明るさ」でなく**数えられる粒**になる領域。
# 加法ガウス雑音を足す aug_* とは雑音モデルが違い(乗法的なショット雑音)、
# 到達時刻ヒストグラムから距離・寿命を出す経路をまとめて持つ。
import photoncount  # noqa: E402  (photon counting / SPAD / TCSPC / dToF / lifetime)
from photoncount import (  # noqa: E402,F401
    photon_sample, photon_statistics, photon_uncertainty,
    anscombe_transform, anscombe_inverse,
    spad_deadtime_apply, spad_deadtime_correct, tcspc_coates_correct,
    tcspc_simulate, tcspc_irf_convolve, tcspc_background_subtract, tcspc_stats,
    dtof_depth, dtof_cube_simulate, dtof_cube_depth,
    lifetime_fit, lifetime_phasor,
)
# 鏡面反射の分離と反射モデル: 光沢面・鏡面部品の検査で Lambertian 前提が
# 破れる領域。二色性反射モデル(色の方向で分ける)・BRDF・影に強い
# フォトメトリックステレオ・偏光による分離。
import specularity  # noqa: E402  (dichromatic split / BRDF / robust photometric stereo)
# 位相ベースのモーション増幅: 目に見えない微小振動を可視化・定量化する層。
# 既存の optical_flow_* は「どこがどれだけ動いたか」を返すが、こちらは
# サブピクセルの周期運動を帯域で選んで増幅する(別の問題を解いている)。
# 四元数・双対四元数による 3-D 姿勢代数。**実装は前からあったが、どちらの
# facade からも 1 つも引けなかった**(module-only)。3-D 姿勢の合成・逆・補間は
# 回転行列より数値的に素直で、ねじ運動(screw)表現も持つ。
import pose_quat  # noqa: E402  (quaternion / dual-quaternion 3-D pose algebra)
from pose_quat import (  # noqa: E402,F401
    axis_angle_to_quat, convert_point_3d_cart_to_spher,
    convert_point_3d_spher_to_cart, convert_pose_type, create_pose,
    dual_quat_compose, dual_quat_conjugate, dual_quat_interpolate,
    dual_quat_normalize, dual_quat_to_pose, dual_quat_to_screw,
    dual_quat_trans_point_3d, get_pose_type, hom_mat3d_to_pose_local,
    pose_average, pose_compose, pose_invert, pose_to_dual_quat,
    pose_to_hom_mat3d_local, pose_to_quat, quat_compose, quat_conjugate,
    quat_interpolate, quat_normalize, quat_rotate_point_3d,
    quat_to_hom_mat3d, quat_to_pose, screw_to_dual_quat,
)
# 四元数画像: 画素が 4 成分になる層。複素画像 (cimage) の回転軸は 1 本だが、
# 四元数の純虚部 (0,R,G,B) は 3 次元ベクトルで、q·x·q* が**色空間の 3 次元
# 回転**になる — チャンネルごとの複素演算では構造的に書けない操作。加えて
# Riesz 変換 / モノジェニック信号(解析信号の 2 次元一般化)を持つ。
# 1-D 信号 / 音響 / 振動。**画像の外**の入力を同じ op 体系で扱う層で、
# 音声 I/O とスペクトログラム・帯域通過・包絡線・実効値まで持つ。
# 振動を「映像から測る」経路は motionmag、「音から測る」経路がこちら。
# **api にだけ無く fullseye にはある**という食い違いがあったので揃えた
# (2026-09-01 実測: api.__all__ に bandpass が無く fullseye にはあった)。
import dsp  # noqa: E402  (1-D signal / acoustic / vibration)
from dsp import (  # noqa: E402,F401
    read_wav, write_wav, read_audio, spectrum, spectrogram, lowpass,
    highpass, bandpass, envelope, rms, find_peaks, signal_features,
    resample, zero_crossing_rate,
)
# FMCW レンジ-ドップラー: 既存の lidar_* が幾何(レイキャスト)だけで信号処理層が
# 空だったところを埋める層。距離と**速度を同時に**出し、遅延和ビームフォーミングで
# 到来角も出す。photoncount(dToF)とは原理が逆で、型も分けてある。
# 音響・振動診断: 「1-D が扱えるなら音響も扱える」を道具にした層。反転可能な
# 短時間フーリエ変換、軸受欠陥の包絡線スペクトル、次数比分析、オクターブ帯域と
# 周波数重み付け。motionmag が「映像から測る振動」、こちらが「音から測る振動」。
# コヒーレンス走査干渉 / クロマティック共焦点: 既存の fringe(位相シフト法)が
# 2π 不定性に負ける段差を、包絡線のピークで解く経路。実測で fringe は
# 段差 λ/4 = 0.15 µm ちょうどから λ/2 の整数倍ずれた答えを**無言で**返す。
import interferometry  # noqa: E402  (coherence-scanning interferometry / chromatic confocal)
from interferometry import (  # noqa: E402,F401
    chromatic_confocal_height, chromatic_confocal_simulate,
    csi_contrast_map, csi_design, csi_envelope, csi_height_map,
    csi_peak_position, csi_signal_simulate, csi_stack_simulate,
)
# 画像 → CAD 面の**逆写像**: 既存の align_cad_to_scan / ICP / ppf は「姿勢は出す」
# が、2-D 画像上で見つけた欠陥が CAD 面のどの座標かに落とす経路が空だった。
# 姿勢は**既知として受け取る**側で、一度も推定しない(推定は pipeline3d /
# registration / ppf の仕事)。render3d.render_mesh がラスタライザ(全画素の
# depth 画像)なのに対し、こちらは**任意の画素だけを問い合わせる**逆向きで、
# face_id と重心座標を返す。
import cadmap  # noqa: E402  (defect pixel -> CAD surface inverse mapping)
from cadmap import (  # noqa: E402,F401
    cad_pixel_to_surface, cad_surface_to_pixel, cad_defect_to_cad,
    cad_visible_faces,
)
# 断層撮影。CT ボリュームを**扱う** op は多数あったのに、**投影から作る**側が
# 完全に空だった(radon / サイノグラム / FBP / 反復再構成がゼロ)。閉形式の真値
# (円板の弦長 2√(r²−s²)、楕円の解析 Radon 変換)で検証してある。
# 図の配色を「役割」で決める層。図ごとに作者が色を選ぶと同じ意味に違う色が付く
# (実際この repo でも「赤=誤り/緑=正しい」と青-黒-橙が同居していた)。既定の
# Okabe-Ito は**赤と緑を対にしない** ― 赤緑の対は色覚特性によっては情報量ゼロ。
import palette  # noqa: E402  (semantic colour roles for figures)
from palette import (  # noqa: E402,F401
    semantic_palette, role_color, role_rgb8, diverging_lut,
    assert_not_red_green_pair, ROLES, ROLE_MARKERS, SCHEMES,
)
# 図注(figure annotation)の層。描画は imagedraw の 5 op(線・円・マーカー)
# しか無く、**図に意味を載せる側**が空だった ― その穴を、図の生成器 6 本が各自の
# 私的ヘルパーで埋めていた(実測の重複: _font 16 / _text 7 / _fill 5 / _legend 2)。
# 文字は必ず幅を測ってから描き、収まらなければ黙って切らずに例外にする。
# 2 枚の絵の差を測る層。op カタログ全文の実測(2026-09-02)で ssim / psnr /
# mutual_information / delta_e が **一件も無かった** ― 変換する op は数百あるのに、
# その出力が入力とどれだけ違うかを言う op が無く、進化の目的関数も図注も
# その場限りの平均二乗誤差を毎回書き直していた。この族は **答え合わせが外から
# できる**のが特徴(CIEDE2000 は公開検証表 34 組と一致、SSIM は独立実装と差 0.0)。
# ``data_range`` を推測しないのが中心的な設計判断 ― [0,1] を 255 と取り違えると
# PSNR が 48.13 dB ずれるが例外は出ない。
# sRGB の伝達関数は gfx2d が実体なので、ここでは再輸出しない(重複を作らない)。
import imgmetrics  # noqa: E402  (SSIM / PSNR / CIEDE2000 / mutual information / NCD)
import opsimgmetrics  # noqa: E402  (the image-metrics op ledger)
from imgmetrics import (  # noqa: E402,F401
    rgb_to_lab, lab_to_rgb, rgb_to_xyz, xyz_to_lab,
    delta_e_2000, delta_e_76, delta_e_map,
    mse, rmse, psnr, ssim, ssim_map, ms_ssim,
    joint_histogram, image_entropy, joint_entropy,
    mutual_information, normalized_mutual_information,
    compressed_size, ncd, compare_images, data_range_of,
    D65_WHITE, MS_SSIM_WEIGHTS, CIEDE2000_TEST_PAIRS,
)
import annotate  # noqa: E402  (text plates, arrows, legends, colour bars, axes)
import opsannotate  # noqa: E402  (the annotate op ledger)
from annotate import (  # noqa: E402,F401
    measure_text, text_box, arrow, leader_line, label_points, crosshair,
    legend_box, color_bar, scale_bar,
    axes_transform, data_to_pixel, nice_ticks, axes_frame, grid_lines, ticks,
    plot_series, overlay_labels, zoom_inset, compare_frame, panel_grid,
    rounded_rect, filled_polygon, arc, ellipse,
)
# ★ ``annotate.overlay_mask`` は **意図的にトップレベルへ出していない**。同名の
# ``imgio.overlay_mask`` が既に ``fs.overlay_mask`` として公開されており、引数も
# 意味も違う(imgio = 生 RGB・mask>0.5・fill/margin / annotate = 役割名の色・
# 重み [0,1] も可・形の不一致を拒否)。同じ名前に別の約束を載せると、呼び手は
# 例外ではなく**もっともらしく違う絵**を受け取る。公開 API の破壊的変更は
# 独断でしないので、役割つきの方は ``fs.annotate.overlay_mask`` で引く。

# 描画を **ためてから一度に流す** 層。即時描画は呼んだ瞬間に絵になるので、そこから先は
# 検査できない ― 文字がはみ出したかどうかは、ラスタ化後の画素からは判定できない。
# コマンドの列で持てば、描く前に箱を測れて、列は JSON になるので図の差分が
# 「3 番目の text_box の文字列が変わった」まで言え、同じ列を別解像度へも流せる。
import drawlist  # noqa: E402  (deferred draw-command list: inspect / diff / rescale)
from drawlist import (  # noqa: E402,F401
    DrawList, DrawListError, diff_command_lists, format_diff, flush_buffer,
    default_text_metrics, measured_text_metrics, COMMAND_SPECS, TEXT_ADVANCE_RATIO,
)
# 描画状態(色・線幅・線種・塗り)と、ラスタ描画。HALCON は装置に状態を持たせる
# (set_color / set_draw / set_line_width / set_line_style)が、ここは**不変値**の
# DrawStyle を正典にした ― 展示画像は再生成で SHA-256 が一致することが要件で、
# 可変グローバルがあると「前に描いた図の設定」が混ざり、例外にならずに図だけが
# 変わる。HALCON 名は相互運用の別名として残し、値を返す関数にしてある。
import drawstyle  # noqa: E402  (immutable draw state: colour / width / line style / fill)
from drawstyle import (  # noqa: E402,F401
    DrawStyle, draw_style, current_style, set_color, set_line_width,
    set_line_style, set_draw, resolve_pattern, resolve_color,
    LINE_STYLES, DRAW_MODES,
)
import imagedraw  # noqa: E402  (raster annotation: lines / markers / circles / contours)
from imagedraw import (  # noqa: E402,F401
    draw_line, draw_polyline, draw_circle, draw_markers, draw_contour, new_canvas,
)
import tomography  # noqa: E402  (radon / FBP / SART / artifacts / CT-to-voxel)
from tomography import (  # noqa: E402,F401
    projection_angles, sinogram_design, ellipse_phantom, ellipse_sinogram,
    radon_transform, backproject_sinogram, filtered_backprojection,
    sart_reconstruct, beam_hardening_apply, beam_hardening_correct,
    ring_artifact_apply, ring_artifact_remove, metal_trace_interpolate,
    sinogram_center_of_rotation, sinogram_center_shift,
    radon_volume, fbp_volume,
)
# 3-D ラベルの色分け。2-D の colorize_labels しか無かったので、ボリュームを
# 断面ごとに着色すると**同じ部品の色が断面ごとに変わる**(断面ごとにラベル番号が
# 振り直されるため。実測: 13 成分中 11 が 32 か所で色が変わる)。ボリュームで
# 着色してから切れば 0 ―― 色は「見た目」ではなく部品の同一性を運ぶので分けた。
import volcolor  # noqa: E402  (3-D label colouring, selection, legend)
from volcolor import (  # noqa: E402,F401
    vol_colorize_labels, vol_label_color_flicker, vol_label_legend,
    vol_label_mpr_rgb, vol_label_overlay, vol_label_palette,
    vol_label_shape_stats, vol_label_slice_rgb, vol_label_volume_render,
    vol_labels_to_meshes, vol_select_labels,
)
import acoustics  # noqa: E402  (STFT / bearing envelope / order tracking / sound level)
from acoustics import (  # noqa: E402,F401
    angular_resample, apply_weighting, bearing_defect_frequencies,
    cepstrum, coherence, envelope_spectrum, equivalent_level, istft,
    octave_bands, octave_spectrum, order_spectrum, percentile_level,
    spectral_kurtosis, stft, stft_cola_check, synthesize_bearing_signal,
    synthesize_speed_ramp, transfer_function, weighting_response,
)
import rangedoppler  # noqa: E402  (FMCW range-Doppler / delay-and-sum beamforming)
from rangedoppler import (  # noqa: E402,F401
    beamform_delay_sum, beamform_doa, fmcw_beat_simulate, fmcw_design,
    fmcw_range_profile, fmcw_window_apply, range_doppler_map,
    range_doppler_peaks,
)
import quatimage  # noqa: E402  (quaternion images / Riesz + monogenic signal)
from quatimage import (  # noqa: E402,F401
    iqft2, monogenic_amplitude, monogenic_orientation, monogenic_phase,
    monogenic_signal, qft2, quat_color_filter, quat_color_rotate,
    quat_conjugate_image, quat_correlate, quat_image_multiply, quat_norm,
    quat_normalize_image, quaternion_to_rgb, rgb_to_quaternion,
    riesz_displacement, riesz_displacement_series, riesz_motion_magnify,
    riesz_transform,
)
import motionmag  # noqa: E402  (phase-based motion magnification / vibration measurement)
from motionmag import (  # noqa: E402,F401
    band_snr, complex_steerable_decompose, complex_steerable_reconstruct,
    displacement_series, motion_magnify, phase_displacement,
    synthesize_translation, temporal_band_power, temporal_bandpass,
)
import gfx2d  # noqa: E402  (real-time 2-D graphics: compositing / sprites / tiles / particles / lighting / post)
from gfx2d import (  # noqa: E402,F401
    alpha_composite, alpha_composite_premul, blend_mode, bloom,
    chromatic_aberration, color_grade, color_lut, dither, film_grain,
    layer_stack, light_mask, linear_to_srgb, nine_slice, normal_map_decode,
    normal_map_shade, palette_quantize, parallax_layers, particle_emit,
    particle_render, particle_step, premultiply, radial_light, shadow_cast_2d,
    sprite_blit, sprite_sheet_slice, sprite_synthesize, sprite_transform,
    srgb_to_linear, tilemap_render, unpremultiply, vignette, viewport,
    BLEND_MODES,
)
from specularity import (  # noqa: E402,F401
    specular_diffuse_split, specular_free_transform,
    specular_coefficient_map, illuminant_from_dichromatic_planes,
    brdf_blinn_phong, brdf_microfacet, dichromatic_render,
    photometric_stereo_robust, photometric_residual, polarization_render,
    polarization_separate, polarization_dolp_map, polarization_stokes,
)
from optics import (  # noqa: E402,F401
    thin_lens, abcd_matrix, abcd_trace, depth_of_field, relative_illumination,
    airy_pattern, angular_spectrum_propagate, fraunhofer_pattern, gaussian_beam,
    psf_to_mtf, mtf_diffraction, wavefront_stats,
    jones_element, jones_apply, stokes_from_jones,
    mueller_element, mueller_apply, stokes_analyze,
)

__all__ = [
    "apply", "run_pipeline", "find_op", "list_ops", "op_names",
    "categories", "read_image", "write_image", "RT", "REGISTRY", "version",
    "stereo", "disparity_map", "disparity_subpixel", "lr_consistency",
    "depth_from_disparity", "reproject_to_points",
    "census_transform", "disparity_census", "disparity_sgm",
    "speckle_filter", "fill_disparity", "disparity_confidence",
    "terrain", "elevation_map", "traversability", "foothold_score", "fill_gaps",
    "ground_surface", "ground_plane", "detect_obstacles",
    "fuse_elevation", "slope_map", "roughness_map", "surface_normals",
    "step_edges", "foothold_candidates",
    "locomotion", "contact_points", "com_from_silhouette", "support_polygon",
    "com_support_margin", "gait_phase",
    "occupancy", "occupancy_grid_2d", "inflate_obstacles", "clearance_map",
    "line_of_sight", "frontier_cells",
    "imgio", "to_float01", "to_uint8", "apply_cmap", "colorize_depth",
    "colorize_disparity", "colorize_labels", "colorize_height", "colorize_flow",
    "shaded_relief", "overlay_mask", "save", "load", "save_ply", "COLORMAPS",
    "detect", "segment_objects", "object_descriptor", "nearest_prototype", "draw_objects",
    "registration", "kabsch", "icp", "point_to_plane_icp", "apply_transform",
    "pca_align", "register", "feature_register",
    "ppf", "ppf_model", "surface_match", "find_surface_pose",
    "pointcloud", "estimate_normals", "voxel_downsample",
    "remove_statistical_outliers", "remove_radius_outliers", "fpfh",
    "pcseg", "fit_plane", "fit_plane_ransac", "fit_sphere_ransac", "fit_cylinder_ransac",
    "plane_distance", "height_above_plane", "remove_ground",
    "euclidean_clusters", "region_growing", "aabb", "obb", "crop_box", "crop_sphere",
    "farthest_point_sampling", "curvature", "centroid", "principal_axes",
    "mesh", "read_mesh", "read_points", "write_mesh", "write_points", "sample_surface",
    "mesh_to_points", "voxelize", "bounds", "recenter", "normalize_scale",
    "meshio_opt", "read_gltf", "read_gltf_merged", "read_las", "read_pcd", "formats_available",
    "volio", "read_volume", "write_volume", "list_dicom_series", "VolumeMeta",
    "raster", "read_raster", "to01", "read_depth", "read_pfm", "write_pfm", "save16",
    "render3d", "render_mesh", "look_at", "intrinsics_from_fov", "auto_view",
    "mesh_to_sdf", "voxelize_solid", "marching_cubes",
    "camera", "intrinsic_matrix", "decompose_intrinsics", "projection_matrix",
    "project_points", "backproject", "depth_to_points", "normals_from_depth",
    "triangulate", "reprojection_error", "solve_pnp", "rodrigues", "rotation_log",
    "fundamental_matrix", "essential_matrix", "essential_from_fundamental",
    "decompose_essential", "recover_pose", "epipolar_lines",
    "distort_points", "undistort_points", "stereo_rectify",
    "odometry", "rgbd_odometry", "pnp_odometry", "integrate_trajectory",
    "umeyama_align", "trajectory_error",
    "grasp", "Grasp", "sample_antipodal_grasps", "grasps_from_mesh", "force_closure",
    "ferrari_canny_quality", "approach_vector_from_normals", "rank_grasps",
    "grasp_pose", "collision_free",
    "meshrepair", "is_watertight", "is_edge_manifold", "boundary_edges", "weld_vertices",
    "remove_degenerate_faces", "orient_consistent", "fill_holes", "smooth_taubin",
    "decimate_qem", "convex_hull", "inertia_tensor", "components",
    "volops", "vol_frangi", "vol_sato", "vol_hessian_blobness", "vol_distance_transform",
    "vol_label", "vol_region_props", "vol_gradient_magnitude", "vol_local_maxima", "vol_watershed",
    "vol_reduce_domain", "vol_bounding_box", "vol_crop_domain", "vol_uncrop",
    "vol_boundary", "vol_boundary_points", "vol_tiled_map",
    "volregion", "VolRLE", "vol_rle_encode", "vol_rle_decode", "vol_rle_volume",
    "vol_rle_bbox", "vol_rle_centroid", "vol_rle_union", "vol_rle_intersect",
    "vol_rle_difference", "vol_rle_components",
    "volgray", "vol_window_level", "vol_equalize", "vol_gamma", "vol_stretch",
    "volxform", "vol_resize", "vol_rotate", "vol_affine",
    "volprobe", "vol_profile_line", "vol_edge_probe", "vol_wall_thickness",
    "volfreq", "vol_fft_lowpass", "vol_fft_highpass", "vol_fft_bandpass",
    "volrestore", "vol_gaussian_psf", "vol_richardson_lucy",
    "handpose", "hand_landmarks", "finger_flexions", "hand_skeleton_edges", "draw_hand_landmarks",
    "complexops", "cx_fft", "cx_ifft", "cx_magnitude", "cx_phase", "cx_real", "cx_imag",
    "cx_log_magnitude", "cx_from_mag_phase", "phase_unwrap", "cx_wiener_deconvolve",
    "cx_apply_transfer_function", "cx_bandpass",
    "specops", "BandMeta", "read_envi", "write_envi", "spec_band", "spec_rgb_composite",
    "spec_nearest_band", "spec_band_ratio", "spec_index", "spec_angle_mapper", "spec_pca",
    "spec_mnf", "spec_unmix", "spec_endmembers_ppi", "spec_continuum_removal",
    "spec_pansharpen", "spec_decorrelation_stretch", "spec_fuse",
    "deformreg", "warp_by_field", "demons_register", "field_magnitude", "residual_ssd",
    "videops", "temporal_mean", "temporal_median", "temporal_std", "temporal_max",
    "temporal_min", "frame_difference", "background_subtraction", "temporal_gradient",
    "motion_energy", "moving_average", "spatiotemporal_gaussian", "spatiotemporal_sobel",
    "per_frame", "flicker_reduce", "optical_flow_sequence",
    "pose", "pose_descriptor", "skeleton_nodes", "principal_axis",
    "flow", "optical_flow_lk", "optical_flow_hs", "warp_by_flow",
    "flow_magnitude", "flow_angle", "track_points",
    "motion", "frame_motion_energy", "dominant_motion", "flow_from_model",
    "residual_motion", "motion_segments", "motion_energy_series", "detect_events",
    "sceneflow", "flow_divergence", "flow_curl", "focus_of_expansion", "time_to_contact",
    "looming", "ego_translation_from_flow", "scene_flow",
    "features", "harris_corners", "fast_corners", "describe_patches",
    "match_descriptors", "match_keypoints",
    "video", "read_frames", "iter_frames", "frame_pairs", "write_video", "probe",
    "recipes", "recipe", "measure", "line_profile", "distance", "angle",
    "fit_line", "fit_circle", "fit_ellipse", "fit_rectangle2",
    "fit_line3", "fit_plane3", "fit_sphere3", "fit_circle3",
    "smallest_box3", "smallest_box3_axis", "fit_box3", "smallest_sphere3", "inner_box3",
    "measure3d", "regionprops3d", "ops3d", "pipeline3d",
    "algo", "algo_ops", "algo_categories", "find_algo", "run_algo",
    "algo_to_python", "algo_to_c", "algo_difftest",
    "synth", "learn_features", "synthesize_like", "match_histogram",
    "radial_power_spectrum", "feature_distance", "patch_novelty", "pyramid_stat_distance",
    "funct1d", "smooth_funct_1d_gauss", "smooth_funct_1d_mean",
    "derivate_funct_1d", "integrate_funct_1d",
    "zero_crossings_funct_1d", "local_min_max_funct_1d",
    "funct_1d_to_pairs", "abs_funct_1d", "negate_funct_1d", "scale_y_funct_1d",
    "compose_funct_1d", "num_points_funct_1d", "distance_funct_1d",
    "sample_funct_1d", "get_pair_funct_1d", "invert_funct_1d",
    "transform_funct_1d", "x_range_funct_1d", "y_range_funct_1d",
    "get_y_value_funct_1d", "create_funct_1d_array", "create_funct_1d_pairs",
    "match_funct_1d_trans",
    "mathops", "mat_solve", "mat_lstsq", "mat_svd", "mat_eigh", "mat_pinv", "mat_cond",
    "stat_describe", "stat_histogram", "stat_covariance", "stat_correlation",
    "stat_zscore",
    "interp_linear", "interp_cubic", "poly_fit", "poly_eval", "poly_roots",
    "cplx_contour_circle", "cplx_poly_eval", "cplx_contour_integral",
    "cplx_winding_number", "cplx_cauchy_value", "cplx_argument_principle",
    "cplx_laurent_coeffs", "cplx_joukowski", "cplx_mobius", "cplx_cr_residual",
    "visiondesign", "system_geometry", "resolving_power", "system_feasibility",
    "image_formation", "detectability_limit",
    "defectgen", "defect_scratch", "defect_pits", "defect_crack", "defect_blob",
    "surface_texture", "composite_defect", "defect_stats",
    "visionlab", "VisionSystem", "render_part", "inspection_sweep",
    "detection_report",
    "lightfield", "lf_synthesize", "lf_from_mla", "lf_to_mla", "lf_stats",
    "lf_subaperture", "lf_center_view", "lf_views", "lf_epi",
    "lf_refocus", "lf_focal_stack", "lf_aperture_mask", "lf_synthetic_aperture",
    "lf_depth_from_focus", "lf_epi_slope", "lf_disparity_to_depth",
    "lf_all_in_focus", "lf_plenoptic_design",
    "photoncount", "photon_sample", "photon_statistics", "photon_uncertainty",
    "anscombe_transform", "anscombe_inverse",
    "spad_deadtime_apply", "spad_deadtime_correct", "tcspc_coates_correct",
    "tcspc_simulate", "tcspc_irf_convolve", "tcspc_background_subtract",
    "tcspc_stats", "dtof_depth", "dtof_cube_simulate", "dtof_cube_depth",
    "lifetime_fit", "lifetime_phasor",
    "dsp",
    "read_wav", "write_wav", "read_audio", "spectrum", "spectrogram",
    "lowpass", "highpass", "bandpass", "envelope", "rms", "find_peaks",
    "signal_features", "resample", "zero_crossing_rate",
    "specularity", "motionmag", "pose_quat", "quatimage", "rangedoppler",
    "acoustics", "interferometry",
    "gfx2d", "alpha_composite", "alpha_composite_premul", "blend_mode", "bloom",
    "chromatic_aberration", "color_grade", "color_lut", "dither", "film_grain",
    "layer_stack", "light_mask", "linear_to_srgb", "nine_slice",
    "normal_map_decode", "normal_map_shade", "palette_quantize",
    "parallax_layers", "particle_emit", "particle_render", "particle_step",
    "premultiply", "radial_light", "shadow_cast_2d", "sprite_blit",
    "sprite_sheet_slice", "sprite_synthesize", "sprite_transform",
    "srgb_to_linear", "tilemap_render", "unpremultiply", "vignette",
    "viewport", "BLEND_MODES",
    "cadmap", "cad_pixel_to_surface", "cad_surface_to_pixel",
    "cad_defect_to_cad", "cad_visible_faces",
    "palette", "semantic_palette", "role_color", "role_rgb8", "diverging_lut", "assert_not_red_green_pair", "ROLES", "ROLE_MARKERS", "SCHEMES",
    # 差を測る層(srgb_to_linear / linear_to_srgb は gfx2d が実体なので再輸出しない)
    "imgmetrics", "opsimgmetrics",
    "rgb_to_lab", "lab_to_rgb", "rgb_to_xyz", "xyz_to_lab",
    "delta_e_2000", "delta_e_76", "delta_e_map",
    "mse", "rmse", "psnr", "ssim", "ssim_map", "ms_ssim",
    "joint_histogram", "image_entropy", "joint_entropy",
    "mutual_information", "normalized_mutual_information",
    "compressed_size", "ncd", "compare_images", "data_range_of",
    "D65_WHITE", "MS_SSIM_WEIGHTS", "CIEDE2000_TEST_PAIRS",
    "annotate", "opsannotate", "measure_text", "text_box", "arrow", "leader_line",
    "label_points", "crosshair", "legend_box", "color_bar", "scale_bar",
    "axes_transform", "data_to_pixel", "nice_ticks", "axes_frame", "grid_lines",
    "ticks", "plot_series", "overlay_labels", "zoom_inset", "compare_frame",
    "panel_grid", "rounded_rect", "filled_polygon", "arc", "ellipse",
    "drawlist", "DrawList", "DrawListError", "diff_command_lists", "format_diff", "flush_buffer", "default_text_metrics", "measured_text_metrics", "COMMAND_SPECS", "TEXT_ADVANCE_RATIO",
    "drawstyle", "DrawStyle", "draw_style", "current_style", "set_color", "set_line_width", "set_line_style", "set_draw", "resolve_pattern", "resolve_color", "LINE_STYLES", "DRAW_MODES",
    "imagedraw", "draw_line", "draw_polyline", "draw_circle", "draw_markers", "draw_contour", "new_canvas",
    "tomography", "projection_angles", "sinogram_design", "ellipse_phantom",
    "ellipse_sinogram", "radon_transform", "backproject_sinogram",
    "filtered_backprojection", "sart_reconstruct", "beam_hardening_apply",
    "beam_hardening_correct", "ring_artifact_apply", "ring_artifact_remove",
    "metal_trace_interpolate", "sinogram_center_of_rotation",
    "sinogram_center_shift", "radon_volume", "fbp_volume",
    "volcolor", "vol_colorize_labels", "vol_label_color_flicker",
    "vol_label_legend", "vol_label_mpr_rgb", "vol_label_overlay",
    "vol_label_palette", "vol_label_shape_stats", "vol_label_slice_rgb",
    "vol_label_volume_render", "vol_labels_to_meshes", "vol_select_labels",
    "chromatic_confocal_height", "chromatic_confocal_simulate",
    "csi_contrast_map", "csi_design", "csi_envelope", "csi_height_map",
    "csi_peak_position", "csi_signal_simulate", "csi_stack_simulate",
    "angular_resample", "apply_weighting", "bearing_defect_frequencies",
    "cepstrum", "coherence", "envelope_spectrum", "equivalent_level",
    "istft", "octave_bands", "octave_spectrum", "order_spectrum",
    "percentile_level", "spectral_kurtosis", "stft", "stft_cola_check",
    "synthesize_bearing_signal", "synthesize_speed_ramp",
    "transfer_function", "weighting_response",
    "beamform_delay_sum", "beamform_doa", "fmcw_beat_simulate",
    "fmcw_design", "fmcw_range_profile", "fmcw_window_apply",
    "range_doppler_map", "range_doppler_peaks",
    "iqft2", "monogenic_amplitude", "monogenic_orientation",
    "monogenic_phase", "monogenic_signal", "qft2", "quat_color_filter",
    "quat_color_rotate", "quat_conjugate_image", "quat_correlate",
    "quat_image_multiply", "quat_norm", "quat_normalize_image",
    "quaternion_to_rgb", "rgb_to_quaternion", "riesz_displacement",
    "riesz_displacement_series", "riesz_motion_magnify",
    "riesz_transform",
    "axis_angle_to_quat", "convert_point_3d_cart_to_spher",
    "convert_point_3d_spher_to_cart", "convert_pose_type", "create_pose",
    "dual_quat_compose", "dual_quat_conjugate", "dual_quat_interpolate",
    "dual_quat_normalize", "dual_quat_to_pose", "dual_quat_to_screw",
    "dual_quat_trans_point_3d", "get_pose_type",
    "hom_mat3d_to_pose_local", "pose_average", "pose_compose",
    "pose_invert", "pose_to_dual_quat", "pose_to_hom_mat3d_local",
    "pose_to_quat", "quat_compose", "quat_conjugate", "quat_interpolate",
    "quat_normalize", "quat_rotate_point_3d", "quat_to_hom_mat3d",
    "quat_to_pose", "screw_to_dual_quat",
    "band_snr", "complex_steerable_decompose",
    "complex_steerable_reconstruct", "displacement_series",
    "motion_magnify", "phase_displacement", "synthesize_translation",
    "temporal_band_power", "temporal_bandpass",
    "specular_diffuse_split", "specular_free_transform",
    "specular_coefficient_map", "illuminant_from_dichromatic_planes",
    "brdf_blinn_phong", "brdf_microfacet", "dichromatic_render",
    "photometric_stereo_robust", "photometric_residual",
    "polarization_render", "polarization_separate",
    "polarization_dolp_map", "polarization_stokes",
    "optics", "thin_lens", "abcd_matrix", "abcd_trace", "depth_of_field",
    "relative_illumination",
    "airy_pattern", "angular_spectrum_propagate", "fraunhofer_pattern",
    "gaussian_beam",
    "psf_to_mtf", "mtf_diffraction", "wavefront_stats",
    "jones_element", "jones_apply", "stokes_from_jones",
    "mueller_element", "mueller_apply", "stokes_analyze",
]


def recipe(name):
    """Look up a curated sample pipeline by name (see ``fullseye.recipes``)."""
    return recipes.get(name)


# ---- general-algorithm tier (algo-c parity; opt-in, image-focus-safe) ------- #
# A separate registry from the image REGISTRY: sorts/reductions over 1-D
# sequences, each shipping a Python reference AND a C reference, verified by
# algo_difftest (Python==numpy oracle, C==Python bit-for-bit). Does not touch the
# evolution registry — see ``algo.py`` and ``docs/GENERAL_ALGORITHMS.md``.
def algo_ops() -> list[str]:
    """Names of the general-algorithm ops (sorts/reductions), e.g. ``quicksort``."""
    return algo.algo_names()


def algo_categories() -> dict:
    """General-algorithm ops grouped by category (``sort`` / ``reduce``)."""
    return algo.algo_categories()


def find_algo(name: str):
    """The :class:`algo.AlgoOp` for *name*, or ``None``."""
    return algo.find_algo(name)


def run_algo(name: str, seq):
    """Run general algorithm *name* on *seq* (a sort returns a list; a reduction a float)."""
    return algo.run_algo(name, seq)


def algo_to_python(name: str) -> str:
    """The standalone Python source for general algorithm *name* (defines ``run(a)``)."""
    return algo_codegen.emit_python(algo.ALGO_BY_NAME[name])


def algo_to_c(name: str) -> str:
    """The standalone C source for general algorithm *name* (function + I/O driver)."""
    return algo_codegen.emit_c(algo.ALGO_BY_NAME[name])


def algo_difftest(name: str, workdir="out/algo", **kw) -> dict:
    """Run the honest gate for general algorithm *name* (Python==oracle, C==Python)."""
    return _algo_difftest.difftest(name, workdir, **kw)

__version__ = "0.1.0"


def version() -> str:
    return __version__


# ---- resolution ------------------------------------------------------------ #
def find_op(name: str):
    """Return the :class:`ops.Op` for *name*, or ``None``.

    Exact op name wins; only then the HALCON alias, preferring the canonical op
    (``name == halcon``) when several ops share an alias. Identical rule to the
    CLI's ``_find_op`` so programmatic and command-line resolution agree.
    """
    for o in _ops.REGISTRY:
        if o.name == name:
            return o
    hits = [o for o in _ops.REGISTRY if o.halcon == name]
    if not hits:
        return None
    for o in hits:
        if o.name == o.halcon:
            return o
    return hits[0]


def _resolve(name: str):
    op = find_op(name)
    if op is None:
        raise KeyError(
            "unknown operator %r — try op name or HALCON alias; "
            "list with fullseye.op_names() or `imgevolve.py has %s`" % (name, name)
        )
    return op


def _coerce_input(v, op):
    """Gently match the array to the op's declared input sort (opt-in).

    Only a ``region`` input is touched. It is re-typed to a float64 {0,1} mask —
    never re-valued — when it is not already one:
      * a bool array is re-typed (``-``/``sum`` on bool either raises or silently
        changes meaning);
      * an int/uint array that is already a {0,1} mask is re-typed to float64 so
        the declared "returns float64" contract holds for it too;
      * any array with more than two levels or values outside [0,1] is binarised
        at the same 0.5 threshold every region op uses internally (``ops._bin``).

    A float one- or two-level in-range array such as {0.3, 0.7} is deliberately
    left alone: ``_bin`` already reads it as an unambiguous mask, so binarising
    here would change nothing for mask ops while destroying the gray levels that
    the few label-reading region ops (``r3_label_to_region``) legitimately consume.
    """
    a = np.asarray(v)
    if op.in_sort != "region":
        return v
    if a.dtype.kind == "b":
        return a.astype(np.float64)                  # mask already; only the dtype is off
    if a.dtype.kind in "fiu":
        vals = np.unique(a)
        if vals.size > 2 or (vals.size and (vals.min() < 0.0 or vals.max() > 1.0)):
            return (a.astype(np.float64) > 0.5).astype(np.float64)
        if a.dtype.kind in "iu":
            return a.astype(np.float64)              # int/uint {0,1} mask -> float64 (same values)
    return v


# ---- run ------------------------------------------------------------------- #
def apply(image, name: str, a: float = 0.5, b: float = 0.5, coerce: bool = True,
          device: str = "cpu"):
    """Apply one operator to *image* and return its raw output.

    image  -> image/region  : returns a float64 ndarray
    region -> feature        : returns a Python float (the scalar measurement)
    *      -> contour        : returns the XLD dict {"shape", "cs"}

    With ``coerce=True`` (default) a grayscale array handed to a ``region`` op is
    binarised at 0.5 and a bool mask is re-typed to float64, matching the CLI —
    see :func:`_coerce_input` for the exact rule (an in-range two-level array is
    left to the op's own 0.5 binarisation). Pass ``coerce=False`` to feed the
    array through untouched.

    ``device`` (default ``"cpu"``): ``"cuda"`` で accel が GPU 化した op を GPU 実行(未対応 op や
    torch/GPU 不在時は静かに CPU)。単発 op は転送律速なので効果は薄い(連鎖は run_pipeline を推奨)。
    """
    op = _resolve(name)
    v = _coerce_input(image, op) if coerce else image
    if device != "cpu":
        try:
            import accel
            accel_name = {c: k for k, (_f, c, _h) in accel.ACCEL.items()}.get(op.name)
            if accel_name is not None:
                return accel.run_batch(accel_name, [v], a, b, device)[0]
        except Exception:
            pass
    out = _ops.RT[op.name](v, a, b)
    if op.out_sort == "feature":
        return float(np.asarray(out).reshape(-1)[0])
    return out


def run_pipeline(image, stages: Iterable, a: float = 0.5, b: float = 0.5,
                 coerce: bool = True, device: str = "cpu"):
    """Apply a sequence of operators, threading the array through each.

    *stages* is either a list of names (one shared ``a``/``b`` for the whole
    chain, like the CLI) **or** a list of ``(name, a, b)`` tuples for per-stage
    knobs — the latter is what you want when different stages need different
    tuning (the CLI cannot do this in a single call).

    ``coerce`` applies to the entry array only: every later value is an op output
    that already carries its declared sort, and region ops binarise at 0.5
    themselves, so re-coercing mid-chain would only strip gray levels a stage may
    still want (see :func:`_coerce_input`).

    ``device`` (default ``"cpu"``): ``"cuda"`` (or any non-cpu) で GPU に載る op を
    ``accel_bridge`` の **常駐パイプライン**で実行(未対応 op は CPU に自動フォールバック、
    連続 accel op は転送 1 回に償却)。GPU/torch 不在時は静かに CPU 経路へ。既定の CPU 経路は
    従来どおり core を鎖状適用する(挙動不変)。GPU 経路は ``ops.run_stages`` と同じ clip 付き
    意味論(進化 champion と同じ)で、faithful op のみ GPU に載せるため **タスク指標は保存**
    される(検証: tests/test_accel_bridge.py ほか)。
    """
    norm = []
    for st in stages:
        if isinstance(st, (tuple, list)):
            name, sa, sb = (list(st) + [a, b])[:3]
        else:
            name, sa, sb = st, a, b
        norm.append((name, float(sa), float(sb)))

    if device != "cpu":                                   # GPU 経路(accel_bridge 常駐)
        try:
            import accel_bridge as _bridge
            v = _coerce_input(image, _resolve(norm[0][0])) if (coerce and norm) else image
            return _bridge.run(norm, [v], device=device)[0]
        except Exception:
            pass                                          # GPU/torch 不在等は CPU にフォールバック

    v = image
    first = True
    for name, sa, sb in norm:
        op = _resolve(name)
        if first:
            v = _coerce_input(v, op) if coerce else v
            first = False
        v = _ops.RT[op.name](v, sa, sb)
    return v


# ---- discovery ------------------------------------------------------------- #
def _rows():
    rows = [{"name": o.name, "halcon": o.halcon, "in_sort": o.in_sort,
             "out_sort": o.out_sort, "category": o.category, "tier": "registry"}
            for o in _ops.REGISTRY]
    try:
        import imgops_nary as _na
        rows += [{"name": o.name, "halcon": o.halcon, "in_sort": o.in_sorts[0],
                  "out_sort": o.out_sort, "category": "nary", "tier": "nary",
                  "arity": o.arity, "in_sorts": list(o.in_sorts)}
                 for o in _na.build_nary()]
    except Exception:
        pass
    return rows


def algo_rows() -> list[dict]:
    """Rows for the opt-in general-algorithm tier (``algo.py``), shaped like ``_rows()``.

    ``tier`` = ``"z_algo"`` so they sort AFTER the image / nary ops; ``category`` is
    prefixed ``algo:`` so the op-browser category filter separates them cleanly; and
    ``backend == "general"`` marks them as a DIFFERENT computational model (seq/scalar,
    not an image raster) so the UI can show them read-only rather than let them be
    dropped into an image pipeline. Empty if the algo tier fails to import.
    """
    try:
        import algo
    except Exception:  # noqa: BLE001 - the general tier is optional; never break the image UI
        return []
    return [{"name": op.name, "halcon": None, "in_sort": op.in_sort,
             "out_sort": op.out_sort, "category": "algo:" + op.category,
             "tier": "z_algo", "backend": "general", "provenance": op.provenance,
             "desc": op.doc}          # packed-input contract (surfaced read-only in the UI help card)
            for op in algo.ALGO_REGISTRY]


def list_ops(sort: str | None = None, search: str | None = None,
             include_algo: bool = False) -> list[dict]:
    """Every operator as a uniform dict. Filter by input *sort* and/or *search*
    (substring over name/halcon/category). *include_algo* (default False, so the image
    focus is unchanged for every existing caller) appends the general-algorithm tier."""
    kw = (search or "").lower()
    rows = _rows() + (algo_rows() if include_algo else [])
    out = []
    for r in rows:
        if sort and r["in_sort"] != sort:
            continue
        hay = (r["name"] + " " + (r["halcon"] or "") + " " + r["category"]).lower()
        if kw and kw not in hay:
            continue
        out.append(r)
    return sorted(out, key=lambda r: (r["tier"], r["in_sort"], r["name"]))


def op_names() -> list[str]:
    """Sorted list of every registry op name (the identifiers :func:`apply` takes)."""
    return sorted(o.name for o in _ops.REGISTRY)


def categories() -> list[str]:
    return sorted({o.category for o in _ops.REGISTRY})


# ---- optional file helpers (cv2) ------------------------------------------- #
def read_image(path: str, sort: str = "image"):
    """Load *path* as a float64 array matching *sort* (needs opencv-python)."""
    import cv2
    if sort == "color":
        im = cv2.imread(path, cv2.IMREAD_COLOR)
        if im is None:
            raise FileNotFoundError(path)
        return im[:, :, ::-1].astype(np.float64) / 255.0
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if im is None:
        raise FileNotFoundError(path)
    g = im.astype(np.float64) / 255.0
    return (g > 0.5).astype(np.float64) if sort == "region" else g


def write_image(path: str, v) -> None:
    """Save a float64 image/region array to *path* (needs opencv-python)."""
    import cv2
    v = np.asarray(v)
    if v.ndim == 3 and v.shape[-1] == 3:
        out = np.clip(v * 255, 0, 255).astype(np.uint8)[:, :, ::-1]
    else:
        out = np.clip(np.asarray(v, np.float64) * 255, 0, 255).astype(np.uint8)
    cv2.imwrite(path, out)


# convenience re-exports
RT = _ops.RT
REGISTRY = _ops.REGISTRY
