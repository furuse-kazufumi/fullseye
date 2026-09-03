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
import warnings
import sys
from typing import Iterable, Sequence

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import ops as _ops  # noqa: E402  (the engine registry; imports its backends on load)
import backend_safe as _bs  # noqa: E402  (fallback ledger / strict mode — the one mediator)
from backend_safe import FullseyeFallbackWarning  # noqa: E402,F401  (re-exported)
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
import raytrace  # noqa: E402  (lens design: real ray tracing / OPD wavefront / Seidel sums / tolerances)
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
# Exact geometric predicates (robust orientation / in-circle / in-sphere): the
# correct SIGN even when float64 rounds a near-degenerate determinant to the wrong
# side. Used by the convex hull; exposed for robust user-side geometry.
from predicates import (orient2d, orient3d, incircle, insphere,  # noqa: E402,F401
                        orient2d_exact, orient3d_exact, incircle_exact, insphere_exact)
# Precision-union storage: a tiled array whose bit-depth varies per tile (a union
# over {0,1,2,4,8,16} bits), chosen per tile from its local entropy. Cuts memory
# on low-entropy machine-vision data (label/region maps, smooth depth, 3-D
# volumes) while presenting one uniform op surface (to_dense/threshold/mean/map).
from precision_union import PrecisionUnion  # noqa: E402,F401
# Robust geometry queries built on the exact predicates above: point-in-polygon /
# tetrahedron / convex-polytope (3-valued in/on/out), convexity, Delaunay validity,
# and mesh orientation consistency — the combinatorial decisions that flip under a
# naive float determinant but not under the exact-sign predicates.
from geompred import (point_in_polygon, point_in_convex_polygon, is_convex_polygon,  # noqa: E402,F401
                      point_in_tetrahedron, point_in_convex_polytope,
                      is_delaunay_2d, mesh_orientation_consistent)
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
except ImportError:       # keep the facade importable on a numpy-only install
    ops3d = None
    pipeline3d = None
except Exception as _e:   # noqa: BLE001 - installed but BROKEN is not the same as absent
    ops3d = None
    pipeline3d = None
    _bs.record("ops3d", _e, None, source="import")
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
    compressed_size, ncd, compare_images, data_range_of, measure_with, metrics_table,
    D65_WHITE, MS_SSIM_WEIGHTS, CIEDE2000_TEST_PAIRS,
)
# 分布を運ぶ層。imgmetrics が「どれだけ違うかを測る」側なら、こちらは「相手に
# 合わせる」側で、測る op と直す op が対になる。ここも検算できるのが特徴 ―
# 1 次元の最適輸送は総当たりの割当解と差 0.00e+00、Poisson 合成は「内部の
# ラプラシアンが元と一致(1.78e-15)・マスク外は貼り先と厳密一致」という
# 構成上の不変量を出力だけから確かめられる。
import colortransport  # noqa: E402  (optimal transport / colour transfer / Poisson blending)
import opscolortransport  # noqa: E402  (the colour-transport op ledger)
from colortransport import (  # noqa: E402,F401
    wasserstein_1d, transport_plan_1d, histogram_match, color_transfer,
    sinkhorn, sinkhorn_distance, sinkhorn_divergence, transport_cost,
    apply_transport, gaussian_transport_map, poisson_blend,
    COLOR_TRANSFER_METHODS,
)
# 画像フォレンジック層。カタログ全文の実測(2026-09-02)で prnu / ela / copy_move /
# jpeg_ghost / phash / watermark が **一件も無かった**。この族は「改竄側を自分で
# 作れるので正解が手元にある」のが強み(defectgen と自前合成)。どの op も
# 「加工されている」と**断定しない** ― 証拠量と、その証拠が何を意味しないかを返す。
import imgforensics  # noqa: E402  (perceptual hashing, PRNU, ELA, copy-move, watermarking)
import opsimgforensics  # noqa: E402  (the forensics op ledger)
from imgforensics import (  # noqa: E402,F401
    perceptual_hash, hash_distance, sensor_fingerprint, fingerprint_correlate,
    fingerprint_strength_map, error_level_map, jpeg_quality_estimate,
    jpeg_ghost_map, jpeg_ghost_quality, noise_inconsistency_map,
    copy_move_regions, watermark_embed, watermark_extract, watermark_capacity,
    null_distribution, evidence_quantile,
)
# 天体写真スタッキング層。カタログ全文の実測(2026-09-02)で lucky / drizzle /
# sigma_clip / cosmic_ray / astrometr が **一件も無かった**。photoncount(ショット
# ノイズ)・optics(PSF/MTF)・mosaic(RANSAC)・fit_transform(当てはめ)を
# import して合成し、Poisson 標本化も RANSAC も Umeyama も再実装していない。
# この族は検算できるのが取り柄 —— drizzle の総フラックス保存は倍精度の丸め
# (最大 6.3e-15)、開口測光は半径 8σ で誤差 0.0000 %、そして κ-σ 合成は
# **ちょうど 50 % の汚染で壊れる**(理論どおり。壊れる側もテストに残してある)。
import astrostack  # noqa: E402  (lucky imaging, sigma-clip stacking, drizzle, photometry)
import opsastrostack  # noqa: E402  (the astro-stacking op ledger)
from astrostack import (  # noqa: E402,F401
    synth_starfield, synth_frame_series, frame_quality, lucky_select, noise_sigma,
    sigma_clip_stack, drizzle_resample, cosmic_ray_reject, cosmic_ray_reject_stack,
    star_detect, psf_fit, aperture_photometry, frame_align, align_frames,
    STACK_MODES, PSF_MODELS, ALIGN_MODELS, NOISE_METHODS,
)
# 契約層 —— 人が呼ぶ経路(fail-closed)と自動で回す経路(Attempt)を分ける。
# システムパラメータは contextvars 実装で、**厳しくする方向にしか動かせない**。
import metriccontract  # noqa: E402  (strict vs tolerant measurement contracts)
import fssystem  # noqa: E402  (set_system / get_system, contextvar-scoped)
from metriccontract import (  # noqa: E402,F401
    MetricContractError, Attempt, attempt, attempt_all,
    DIRECTIONS, worst_case, value_or_worst, best_of, rank_attempts,
)
from fssystem import (  # noqa: E402,F401
    set_system, get_system, query_system, system, reset_system, system_snapshot,
)
import annotate  # noqa: E402  (text plates, arrows, legends, colour bars, axes)
import opsannotate  # noqa: E402  (the annotate op ledger)
from annotate import (  # noqa: E402,F401
    measure_text, text_box, arrow, leader_line, label_points, crosshair,
    legend_box, color_bar, scale_bar,
    axes_transform, data_to_pixel, nice_ticks, axes_frame, grid_lines, ticks,
    plot_series, overlay_labels, zoom_inset, compare_frame, panel_grid,
    rounded_rect, filled_polygon, arc, ellipse,
    # 学術図の作法(2026-09-03): 引き出し線・番号/凡例・寸法・角度・スケールバー・
    # 方位・隅の拡大・輪郭・経路文字・色分け・パネル文字・図の組版(+ *_layout)
    annotate_leader_layout, annotate_leader, annotate_markers, annotate_legend,
    annotate_dimension_layout, annotate_dimension, annotate_angle_layout,
    annotate_angle, annotate_scale_bar_layout, annotate_scale_bar,
    annotate_orientation, annotate_inset_layout, annotate_inset,
    annotate_outline_layout, annotate_outline, annotate_text_path_layout,
    annotate_text_path, annotate_colorbar, annotate_panel_label,
    annotate_figure_grid_layout, annotate_figure_grid,
)
import meshres  # noqa: E402  (resolution management: measure coarse/dense, remesh, audited reductions)
from meshres import (  # noqa: E402,F401
    mesh_edge_stats, mesh_detail_map, mesh_split_long_edges, mesh_isotropic_remesh,
    mesh_sample_points, mesh_lod_chain, mesh_select_lod, mesh_reduction_report,
    mesh_decimate_preserving, pc_density, pc_poisson_disk, pc_fill_sparse,
    pc_density_equalize, pc_lod_chain, pc_thinning_report,
)
import videostream  # noqa: E402  (frame-by-frame video: ring buffer, stateful ops, VideoPipeline)
import opsvideostream  # noqa: E402  (the streaming-video op ledger)
from videostream import (  # noqa: E402,F401
    FrameRing, StatefulOp, TemporalMedianWindow, MovingAverageWindow,
    BackgroundSubtractionWindow, FrameDifference, ExponentialBackground, RunningStats,
    OpticalFlowStream, VideoPipeline, stream_replay,
    MotionHistoryImage, ThreeFrameDifference, RunningGaussianForeground,
    TemporalBilateral, Deflicker, SceneCutDetection,
    temporal_median_window, moving_average_window, background_subtraction_window,
    frame_difference_causal, exponential_background, exponential_foreground,
    running_mean_std, optical_flow_magnitude_stream,
    motion_history_image, motion_energy_image, three_frame_difference,
    running_gaussian_foreground, running_gaussian_background,
    temporal_bilateral, deflicker, scene_cut_detection,
)
import annotate3d  # noqa: E402  (3-D anchors -> projected arrows / labels / scale bars)
from annotate3d import (  # noqa: E402,F401
    annotate3d_project, annotate3d_arrow, annotate3d_label, annotate3d_scale_bar,
    annotate3d_axes, annotate3d_bbox, annotate3d_measure, project_anchors,
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
from raytrace import (  # noqa: E402,F401  (lens design: real rays beyond the paraxial optics module)
    lens_system, thick_lens, glass, refractive_index, example_system,
    paraxial_trace, trace_rays, ray_bundle, spot_diagram, spot_stats, ray_fan,
    opd_map, opd_samples, wavefront_from_opd, seidel_coefficients,
    tolerance_analysis, glass_catalog, sellmeier, chromatic_shift, chief_ray,
    with_wavelength,
)
import lensopt  # noqa: E402  (damped-least-squares lens optimisation)
from lensopt import optimize_lens, merit_function, bend_singlet  # noqa: E402,F401
import illumdesign  # noqa: E402  (machine-vision illumination design)
from illumdesign import (  # noqa: E402,F401
    light_source, irradiance_map, illumination_uniformity, defect_contrast,
    lighting_sweep, illumination_design,
)
import lensimage  # noqa: E402  (image formation through a designed lens + synthetic defect datasets)
from lensimage import (  # noqa: E402,F401
    psf_from_opd, psf_field_grid, distortion_map, render_through_lens, defect_dataset,
    calibration_views,
)

__all__ = [
    "orient2d", "orient3d", "incircle", "insphere",
    "orient2d_exact", "orient3d_exact", "incircle_exact", "insphere_exact",
    "point_in_polygon", "point_in_convex_polygon", "is_convex_polygon",
    "point_in_tetrahedron", "point_in_convex_polytope",
    "is_delaunay_2d", "mesh_orientation_consistent",
    "PrecisionUnion",
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
    "measure_with", "metrics_table",
    "D65_WHITE", "MS_SSIM_WEIGHTS", "CIEDE2000_TEST_PAIRS",
    # 分布を運ぶ層(測る imgmetrics と対)
    "colortransport", "opscolortransport",
    "wasserstein_1d", "transport_plan_1d", "histogram_match", "color_transfer",
    "sinkhorn", "sinkhorn_distance", "sinkhorn_divergence", "transport_cost",
    "apply_transport", "gaussian_transport_map", "poisson_blend",
    "COLOR_TRANSFER_METHODS",
    # 画像フォレンジック層(断定せず証拠量を返す)
    "imgforensics", "opsimgforensics",
    "perceptual_hash", "hash_distance", "sensor_fingerprint", "fingerprint_correlate",
    "fingerprint_strength_map", "error_level_map", "jpeg_quality_estimate",
    "jpeg_ghost_map", "jpeg_ghost_quality", "noise_inconsistency_map",
    "copy_move_regions", "watermark_embed", "watermark_extract", "watermark_capacity",
    "null_distribution", "evidence_quantile",
    "astrostack", "opsastrostack",
    "synth_starfield", "synth_frame_series", "frame_quality", "lucky_select",
    "noise_sigma", "sigma_clip_stack", "drizzle_resample", "cosmic_ray_reject",
    "cosmic_ray_reject_stack", "star_detect", "psf_fit", "aperture_photometry",
    "frame_align", "align_frames",
    "STACK_MODES", "PSF_MODELS", "ALIGN_MODELS", "NOISE_METHODS",
    # 契約層(人が呼ぶ経路 / 自動で回す経路)とシステムパラメータ
    "metriccontract", "MetricContractError", "Attempt", "attempt", "attempt_all",
    "DIRECTIONS", "worst_case", "value_or_worst", "best_of", "rank_attempts",
    "fssystem", "set_system", "get_system", "query_system", "system",
    "reset_system", "system_snapshot",
    "annotate", "opsannotate", "measure_text", "text_box", "arrow", "leader_line",
    "label_points", "crosshair", "legend_box", "color_bar", "scale_bar",
    "axes_transform", "data_to_pixel", "nice_ticks", "axes_frame", "grid_lines",
    "ticks", "plot_series", "overlay_labels", "zoom_inset", "compare_frame",
    "panel_grid", "rounded_rect", "filled_polygon", "arc", "ellipse",
    "annotate_leader_layout", "annotate_leader", "annotate_markers", "annotate_legend",
    "annotate_dimension_layout", "annotate_dimension", "annotate_angle_layout",
    "annotate_angle", "annotate_scale_bar_layout", "annotate_scale_bar",
    "annotate_orientation", "annotate_inset_layout", "annotate_inset",
    "annotate_outline_layout", "annotate_outline", "annotate_text_path_layout",
    "annotate_text_path", "annotate_colorbar", "annotate_panel_label",
    "annotate_figure_grid_layout", "annotate_figure_grid",
    "meshres",
    "mesh_edge_stats", "mesh_detail_map", "mesh_split_long_edges", "mesh_isotropic_remesh",
    "mesh_sample_points", "mesh_lod_chain", "mesh_select_lod", "mesh_reduction_report",
    "mesh_decimate_preserving", "pc_density", "pc_poisson_disk", "pc_fill_sparse",
    "pc_density_equalize", "pc_lod_chain", "pc_thinning_report",
    "videostream", "opsvideostream",
    "FrameRing", "StatefulOp", "TemporalMedianWindow", "MovingAverageWindow",
    "BackgroundSubtractionWindow", "FrameDifference", "ExponentialBackground", "RunningStats",
    "OpticalFlowStream", "VideoPipeline", "stream_replay",
    "MotionHistoryImage", "ThreeFrameDifference", "RunningGaussianForeground",
    "TemporalBilateral", "Deflicker", "SceneCutDetection",
    "temporal_median_window", "moving_average_window", "background_subtraction_window",
    "frame_difference_causal", "exponential_background", "exponential_foreground",
    "running_mean_std", "optical_flow_magnitude_stream",
    "motion_history_image", "motion_energy_image", "three_frame_difference",
    "running_gaussian_foreground", "running_gaussian_background",
    "temporal_bilateral", "deflicker", "scene_cut_detection",
    "annotate3d",
    "annotate3d_project", "annotate3d_arrow", "annotate3d_label",
    "annotate3d_scale_bar", "annotate3d_axes", "annotate3d_bbox", "annotate3d_measure",
    "project_anchors",
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
    "raytrace", "lens_system", "thick_lens", "glass", "refractive_index",
    "example_system", "paraxial_trace", "trace_rays", "ray_bundle",
    "spot_diagram", "spot_stats", "ray_fan", "opd_map", "opd_samples",
    "wavefront_from_opd", "seidel_coefficients", "tolerance_analysis",
    "glass_catalog", "sellmeier", "chromatic_shift", "chief_ray", "with_wavelength",
    "lensopt", "optimize_lens", "merit_function", "bend_singlet",
    "illumdesign", "light_source", "irradiance_map", "illumination_uniformity",
    "defect_contrast", "lighting_sweep", "illumination_design",
    "lensimage", "psf_from_opd", "psf_field_grid", "distortion_map",
    "render_through_lens", "defect_dataset", "calibration_views",
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

def _resolve_version() -> str:
    """version の単一真実源 = pyproject。ハードコードは陳腐化する(0.1.5 でも
    "0.1.0" を返していた)。

    順に試す: (1) この api.py の隣にある ``pyproject.toml`` —— ソース/sdist の
    チェックアウトではこれが正本(wheel では隣に無いので None)。(2) インストール
    済みなら ``importlib.metadata`` の版。(1) を先に見るのは、開発ツリーに古い版が
    pip 済みだと metadata がソースとずれる(0.1.5 のソースで 0.1.4 が返る)ため。
    どちらも駄目なら最後の既知版。
    """
    import os as _os                                      # noqa: PLC0415
    try:
        import tomllib as _toml                           # noqa: PLC0415
        _pp = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "pyproject.toml")
        if _os.path.exists(_pp):
            with open(_pp, "rb") as _f:
                return _toml.load(_f)["project"]["version"]
    except Exception:                                     # noqa: BLE001
        pass
    try:
        from importlib.metadata import version as _v, PackageNotFoundError  # noqa: PLC0415
        try:
            return _v("fullseye")
        except PackageNotFoundError:
            pass
    except Exception:                                     # noqa: BLE001
        pass
    return "0.1.5"


__version__ = _resolve_version()


def version() -> str:
    return __version__


# ---- resolution ------------------------------------------------------------ #
# HALCON aliases that several ops share while NO op carries the alias as its own
# name. `find_op` used to fall back to "first registered", so which implementation
# `fullseye.apply(x, "emphasize")` ran depended on backend registration order — a
# silent behaviour change whenever a backend was added. The winner is now a TABLE
# (one row per alias; tests/test_api.py pins that every such alias has a row), so
# a new ambiguous alias fails CI instead of resolving by accident.
_ALIAS_CANONICAL = {
    "emphasize": "unsharp",              # cv_sharpen is the cv2 port of the same idea
    "points_harris": "corner_response",  # sk_/cv_corner_harris, cv_min_eigen are library ports
}


def find_op(name: str):
    """Return the :class:`ops.Op` for *name*, or ``None``.

    Exact op name wins; only then the HALCON alias, preferring the canonical op
    (``name == halcon``) when several ops share an alias, then the explicit
    ``_ALIAS_CANONICAL`` row, and only as a last resort the first registered hit.
    Identical rule to the CLI's ``_find_op`` so programmatic and command-line
    resolution agree.
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
    pick = _ALIAS_CANONICAL.get(name)
    if pick is not None:
        for o in hits:
            if o.name == pick:
                return o
    return hits[0]


def ambiguous_aliases() -> dict:
    """``{alias: [op names]}`` for HALCON aliases shared by >1 op with NO canonical op.

    Each key must have a row in ``_ALIAS_CANONICAL`` naming one of its ops — otherwise
    :func:`find_op` would resolve it by registration order (pinned by tests).
    """
    by_alias: dict = {}
    for o in _ops.REGISTRY:
        if o.halcon:
            by_alias.setdefault(o.halcon, []).append(o.name)
    return {k: v for k, v in by_alias.items() if len(v) > 1 and k not in v}


_NARY_CACHE = None


def _nary_by_name() -> dict:
    """``{name_or_halcon: NaryOp}`` for the n-ary tier (image arithmetic / region set ops)."""
    global _NARY_CACHE
    if _NARY_CACHE is None:
        table = {}
        try:
            import imgops_nary as _na
            for o in _na.build_nary():
                table[o.name] = o
                table.setdefault(o.halcon, o)
        except ImportError:
            pass
        except Exception as e:           # noqa: BLE001 - installed but broken: leave a trace
            _bs.record("imgops_nary", e, None, source="import")
        _NARY_CACHE = table
    return _NARY_CACHE


def _resolve(name: str):
    op = find_op(name)
    if op is None:
        nop = _nary_by_name().get(name)
        if nop is not None:
            # Listed by list_ops() (tier "nary") but not a single-input registry op: say
            # so instead of the old bare KeyError — the fix is to pass a list of inputs.
            raise TypeError(
                "%r is an n-ary operator (arity %d, inputs %s): call "
                "fullseye.apply([%s], %r, a, b) with a list of inputs"
                % (name, nop.arity, list(nop.in_sorts),
                   ", ".join("x%d" % i for i in range(nop.arity)), name))
        raise KeyError(
            "unknown operator %r — try op name or HALCON alias; "
            "list with fullseye.op_names() or `imgevolve.py has %s`" % (name, name)
        )
    return op


# Region ops that read the gray VALUES of their input as labels rather than as a
# mask. The registry carries no per-op flag for this, so the set is explicit; add
# an op here when it distinguishes label values instead of foreground/background.
_LABEL_READING_OPS = frozenset({"r3_label_to_region"})


def _needs_binarise(a) -> bool:
    """True when *a* has more than two distinct levels, or any value outside [0,1].

    This is the verdict ``np.unique(a)`` used to give, computed in **O(N)** instead
    of ``O(N log N)``: ``np.unique`` sorts the whole array, which made every region
    op twice as slow through the facade (2048² region: 17.6 ms of a 35.0 ms call —
    ``docs/design/PERF_MEMORY_VIDEO_SURVEY.md`` §1.7 / §5.3 item 3).

    Same verdict, not merely a similar one: an array with min ``mn`` and max ``mx``
    has at most two distinct levels **iff** every element equals ``mn`` or ``mx``.
    NaN is the one case where min/max stop being informative (``nan < 0`` is False,
    so the old code fell through to "leave it alone" for a two-element unique), so a
    NaN-bearing array takes the original ``np.unique`` path verbatim.
    """
    if a.size == 0:
        return False                                  # np.unique -> size 0: neither test fires
    mn = a.min()
    mx = a.max()
    if a.dtype.kind == "f" and (np.isnan(mn) or np.isnan(mx)):   # replay the exact old test
        vals = np.unique(a)
        return bool(vals.size > 2 or vals.min() < 0.0 or vals.max() > 1.0)
    if mn < 0.0 or mx > 1.0:
        return True
    return bool(mn != mx and not np.all((a == mn) | (a == mx)))


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

    Label-reading ops are exempted outright (``_LABEL_READING_OPS``): a real label
    image has more than two levels by definition, so the two-level carve-out above
    never reaches it — binarising at 0.5 would merge every label into one blob and
    the op could only ever return the whole foreground.
    """
    a = np.asarray(v)
    if op.in_sort != "region":
        return v
    if op.name in _LABEL_READING_OPS:
        return v
    if a.dtype.kind == "b":
        return a.astype(np.float64)                  # mask already; only the dtype is off
    if a.dtype.kind in "fiu":
        if _needs_binarise(a):
            return (a.astype(np.float64) > 0.5).astype(np.float64)
        if a.dtype.kind in "iu":
            return a.astype(np.float64)              # int/uint {0,1} mask -> float64 (same values)
    return v


# ---- run ------------------------------------------------------------------- #
# Error policy. The facade used to be fail-soft with no escape hatch: a broken op, a
# failed GPU kernel or an input of the wrong sort all became a plausible-looking
# array with no trace (2026-09-02 audit: 6 of 7 confirmed bugs were of the
# "no exception, wrong answer" kind). The contradiction — never crash a user's
# pipeline vs. never hide a failure — is resolved by letting the CALLER choose:
#
#   on_error="fallback"  (default) keep the sort-valid fallback; every degradation is
#                        recorded in the ledger (fullseye.fallbacks()) and each op
#                        warns ONCE (FullseyeFallbackWarning);
#   on_error="warn"      as above, but warn on EVERY fallback of this call;
#   on_error="raise"     fail-closed: the op's real exception propagates, a wrong-sort
#                        input raises ValueError, a failed GPU kernel raises.
#
# The default can be set process-wide with FULLSEYE_ON_ERROR=raise (CI / verifiers).
_ON_ERROR_CHOICES = ("fallback", "warn", "raise")
_NDIM_OK = {"image": (2, 3), "region": (2, 3), "color": (3,), "volume": (3, 4)}
_NOACCEL = object()
# GPU circuit breaker (TRIZ #9 preliminary anti-action / #23 feedback): once an op's
# accelerated path has FAILED it is not retried on every call — a broken kernel
# would otherwise cost a GPU attempt + a recorded fallback per invocation. The
# breaker is per op name, opens on the first failure, and `reset_gpu()` closes it
# (half-open: the next call tries the GPU again).
_GPU_OPEN: set = set()


def reset_gpu() -> list:
    """Close the GPU circuit breaker for every op; returns the names that were open."""
    was = sorted(_GPU_OPEN)
    _GPU_OPEN.clear()
    return was


def gpu_open_ops() -> list:
    """Op names whose accelerated path is currently disabled by the breaker."""
    return sorted(_GPU_OPEN)


# Same breaker for the CPU fast-twin path (``fast.py``): a twin that raises once is
# not retried on every call.
_FAST_OPEN: set = set()


def reset_fast() -> list:
    """Close the fast-twin circuit breaker for every op; returns the names that were open."""
    was = sorted(_FAST_OPEN)
    _FAST_OPEN.clear()
    return was


def fast_open_ops() -> list:
    """Op names whose CPU fast twin is currently disabled by the breaker."""
    return sorted(_FAST_OPEN)


def _fast_on(flag) -> bool:
    """Is the CPU fast-twin path enabled for this call?

    ``fast=True/False`` wins; ``None`` reads ``FULLSEYE_FAST`` (``1``/``true``/``yes``).
    **Default OFF** — the twins are parity-gated (``fast.parity``) but the switch is
    opt-in until a bench run on the target machine says the default should flip.
    """
    if flag is not None:
        return bool(flag)
    return os.environ.get("FULLSEYE_FAST", "").strip().lower() in ("1", "true", "yes", "on")


def _policy(on_error):
    p = on_error if on_error is not None else os.environ.get("FULLSEYE_ON_ERROR", "fallback")
    if p not in _ON_ERROR_CHOICES:
        raise ValueError("on_error must be one of %s, got %r" % (_ON_ERROR_CHOICES, p))
    return p


def _check_input_sort(v, op):
    """Exception describing a clearly wrong input for *op*, or None (light, ndim-level check)."""
    ok = _NDIM_OK.get(op.in_sort)
    if ok is None:
        return None
    try:
        arr = v if isinstance(v, np.ndarray) else np.asarray(v)
    except Exception as e:               # noqa: BLE001
        return TypeError("op %r expects a %s array, got %r (%s)" % (op.name, op.in_sort, type(v).__name__, e))
    if arr.dtype.kind not in "biufc":
        return TypeError("op %r expects a numeric %s array, got dtype %s" % (op.name, op.in_sort, arr.dtype))
    if arr.ndim not in ok:
        return ValueError("op %r expects a %s (%s-D array), got shape %s"
                          % (op.name, op.in_sort, "/".join(map(str, ok)), arr.shape))
    return None


def _guard_input(v, op, policy):
    err = _check_input_sort(v, op)
    if err is None:
        return
    if policy == "raise":
        raise err
    _bs.record(op.name, err, op.out_sort, source="input")


# ---- integer input: fail-closed instead of silently wrong -------------------- #
# The public contract is "image = H*W float64 in [0,1]" (module docstring), but the
# facade used to accept an integer array and hand it straight to the op. The core
# ops call ``ndimage.*`` with no dtype argument, so a uint8 image was filtered AS
# uint8 and came back uint8 (gaussian / mean_box / gerode / rotate_img), float16
# (sobel_mag) or all-ones (threshold: ``v > 0.5`` on 0..255). No exception, a
# plausible-looking array, a different answer — the third state between "accept"
# and "reject" (survey §1.3 / §2.1 / §5.3 item 1).
#
# The policy is the ``on_error`` policy, like every other degradation:
#   "raise"              -> ValueError naming the dtype and the contract (fail-closed)
#   "fallback" / "warn"  -> convert explicitly and RECORD it (source="input")
#
# ``region`` inputs are deliberately NOT touched: an int {0,1} mask is a legitimate
# region and ``_coerce_input`` already re-types it without rescaling.
_DTYPE_CONTRACT_SORTS = frozenset({"image", "color", "volume"})
_DTYPE_FULL_SCALE = {"uint8": 255.0, "uint16": 65535.0}


def _dtype_scale(a):
    """Divisor mapping *a*'s integer dtype onto the float64 [0,1] contract.

    uint8 / uint16 are the documented sensor dtypes and get their full scale. Any
    other integer dtype has no agreed full scale, so an array that is already inside
    [0,1] (an int mask) is only re-typed, and anything wider is divided by the
    dtype's maximum. Whichever branch runs, the conversion is recorded.
    """
    s = _DTYPE_FULL_SCALE.get(a.dtype.name)
    if s is not None:
        return s
    if a.size == 0:
        return 1.0
    if float(a.min()) >= 0.0 and float(a.max()) <= 1.0:
        return 1.0                                   # already contract-valued; only the dtype is off
    try:
        return float(np.iinfo(a.dtype).max)
    except ValueError:                               # not an integer dtype after all
        return 1.0


def _contract_dtype(v, op, policy):
    """Bring an integer/bool image onto the float64 [0,1] contract, or refuse it.

    Returns the value to run the op on. Independent of ``coerce`` (which is about
    the *sort*, not the dtype): a dtype outside the contract is wrong for every
    caller, and staying silent is what produced the wrong answers above.
    """
    if op.in_sort not in _DTYPE_CONTRACT_SORTS:
        return v
    a = v if isinstance(v, np.ndarray) else None
    if a is None or a.dtype.kind not in "bui":
        return v                                     # float / complex / non-array: unchanged
    if policy == "raise":
        raise ValueError(
            "op %r expects a %s of float64 in [0,1] (the fullseye contract), got dtype %s. "
            "Convert explicitly, e.g. img.astype(np.float64) / 255.0 for uint8 — the core "
            "operators run scipy.ndimage with no dtype argument, so an integer image is "
            "filtered as an integer and the result is a different image, not a slower one."
            % (op.name, op.in_sort, a.dtype))
    if a.dtype.kind == "b":
        out = a.astype(np.float64)
        how = "bool -> float64 {0,1}"
    else:
        s = _dtype_scale(a)
        out = a.astype(np.float64) if s == 1.0 else a.astype(np.float64) / s
        how = "%s -> float64 (/%g)" % (a.dtype, s)
    _bs.record(op.name,
               ValueError("dtype_converted: %s; the contract is float64 in [0,1]" % how),
               op.out_sort, source="input")
    return out


def _run_guarded(name, fn, policy, out_sort=None, v=None):
    """Run ``fn()`` under the error policy, attributing any fallback to *name*.

    The facade is the OUTER boundary: a core op (ops.py) carries no guard of its own,
    so its exception is caught here — recorded (source ``"op"``) and turned into the
    declared-sort fallback under ``"fallback"``/``"warn"``, propagated under ``"raise"``.
    Inner guards (backends) already record; ``"warn"`` silences their once-per-op
    warning and emits one warning per CALL instead (no duplicate on first failure).
    """
    m = _bs.mark()
    with _bs.current_op(name):
        if policy == "raise":
            with _bs.strict_mode(True):
                return fn()
        try:
            if policy == "warn":
                with _bs.quiet_warnings():
                    out = fn()
            else:
                out = fn()
        except Exception as e:           # noqa: BLE001 - recorded, sort-valid fallback
            if policy == "warn":
                with _bs.quiet_warnings():
                    _bs.record(name, e, out_sort, source="op")
            else:
                _bs.record(name, e, out_sort, source="op")
            out = _bs.fallback(v, out_sort)
    if policy == "warn":
        evs = _bs.events_since(m)
        if evs:
            warnings.warn("fullseye: %r degraded to a fallback (%s)"
                          % (name, "; ".join(e["error"] for e in evs)),
                          FullseyeFallbackWarning, stacklevel=4)
    return out


# core op name -> accel key, built ONCE. The comprehension used to run on every
# single ``apply`` (90+ entries per call — survey §1.7 / §5.3 item 4). Keyed on the
# identity+size of the table so a test that swaps ``accel.ACCEL`` still gets the
# right answer instead of a stale cache.
_ACCEL_REV: tuple = (None, None)


def _accel_reverse(accel) -> dict:
    """Cached ``{core_op_name: accel_key}`` reverse index of ``accel.ACCEL``.

    Same value the per-call dict comprehension produced (later keys win, exactly as
    before), just not rebuilt 90 entries at a time on every call.
    """
    global _ACCEL_REV
    tag = (id(accel.ACCEL), len(accel.ACCEL))
    if _ACCEL_REV[0] != tag:
        _ACCEL_REV = (tag, {c: k for k, (_f, c, _h) in accel.ACCEL.items()})
    return _ACCEL_REV[1]


def _try_fast(op, v, a, b):
    """CPU fast-twin path (``fast.py``, cv2/IPP). ``_NOACCEL`` when there is no twin.

    Same shape as :func:`_try_accel`: OpenCV/``fast`` ABSENT is silent (``ImportError``),
    an input the twin cannot serve faithfully is silent too (``FastUnsupported`` — that
    is an absence, not a failure), and anything else is recorded with ``source="fast"``
    and re-raised under ``on_error="raise"``.
    """
    try:
        import fast as _fast
    except ImportError:
        return _NOACCEL
    if op.name not in _fast.FAST or (op.name in _FAST_OPEN and not _bs.is_strict()):
        return _NOACCEL                  # breaker open; strict mode retries so "raise" can raise
    try:
        return _fast.apply_fast(op.name, v, a, b)
    except _fast.FastUnsupported:
        return _NOACCEL                  # no faithful twin for THIS input: core, no ledger noise
    except Exception as e:               # noqa: BLE001
        if _bs.is_strict():
            raise
        _FAST_OPEN.add(op.name)          # breaker opens: no more twin attempts until reset_fast()
        _bs.record(op.name, e, op.out_sort, source="fast")
        return _NOACCEL


def _try_accel(op, v, a, b, device):
    """GPU single-op path. Returns ``_NOACCEL`` when there is nothing to accelerate.

    torch/accel ABSENT is the documented silent case (``ImportError``). Anything else
    — a broken kernel, a CUDA error — used to be swallowed by ``except Exception: pass``
    and became a silent CPU result; it is now recorded (source ``"gpu"``) and re-raised
    under ``on_error="raise"``.
    """
    try:
        import accel
    except ImportError:
        return _NOACCEL
    try:
        accel_name = _accel_reverse(accel).get(op.name)
    except Exception as e:               # noqa: BLE001 - malformed table is a bug, not an absence
        if _bs.is_strict():
            raise
        _bs.record(op.name, e, op.out_sort, source="gpu")
        return _NOACCEL
    if accel_name is None or (op.name in _GPU_OPEN and not _bs.is_strict()):
        return _NOACCEL                  # breaker open; strict mode retries so "raise" can raise
    try:
        return accel.run_batch(accel_name, [v], a, b, device)[0]
    except Exception as e:               # noqa: BLE001
        if _bs.is_strict():
            raise
        _GPU_OPEN.add(op.name)           # breaker opens: no more GPU attempts until reset_gpu()
        _bs.record(op.name, e, op.out_sort, source="gpu")
        return _NOACCEL


def apply(image, name: str, a: float = 0.5, b: float = 0.5, coerce: bool = True,
          device: str = "cpu", on_error: str | None = None, template=None,
          fast: bool | None = None):
    """Apply one operator to *image* and return its raw output.

    image  -> image/region  : returns a float64 ndarray
    region -> feature        : returns a Python float (the scalar measurement)
    *      -> contour        : returns the XLD dict {"shape", "cs"}
    [x1, x2] -> nary op      : *image* may be a LIST of inputs for the n-ary tier
                               (``add_image``, ``union2`` … — see ``list_ops(tier)``)

    With ``coerce=True`` (default) a grayscale array handed to a ``region`` op is
    binarised at 0.5 and a bool mask is re-typed to float64, matching the CLI —
    see :func:`_coerce_input` for the exact rule (an in-range two-level array is
    left to the op's own 0.5 binarisation). Pass ``coerce=False`` to feed the
    array through untouched.

    An integer or bool *image* is **not** the contract (float64 in [0,1]): it is
    converted (``/255`` for uint8, ``/65535`` for uint16, re-typed for bool) and the
    conversion is recorded in the ledger, or refused outright under
    ``on_error="raise"``. It used to be handed to the op unchanged, which produced a
    uint8/float16/all-ones result with no exception — see :func:`_contract_dtype`.

    ``device`` (default ``"cpu"``): ``"cuda"`` runs accel-enabled ops on the GPU.
    torch/accel *absent* falls back to CPU silently (documented); a kernel that
    FAILS is recorded in the fallback ledger and raises under ``on_error="raise"``.

    ``fast`` (default ``None`` = read ``FULLSEYE_FAST``, i.e. **off**): on the CPU,
    run the op's parity-gated cv2 twin from ``fast.py`` when it has one (gaussian,
    box, median, gray morphology, sobel/laplace/prewitt, dog, unsharp, std, canny —
    ``fast.FAST``). Same answer (``fast.parity``), several times faster; a twin that
    fails is recorded with ``source="fast"`` and the core op runs instead.

    ``on_error``: ``"fallback"`` (default; sort-valid fallback, recorded, warns once
    per op), ``"warn"`` (warn on every fallback of this call) or ``"raise"``
    (fail-closed). ``None`` reads ``FULLSEYE_ON_ERROR``. See :func:`fallbacks`.

    ``template``: for the matching ops (``ncc_locate`` / ``shape_locate``) the
    template image to locate; it is set for this call only (thread-local) and the
    previous template is restored afterwards. Without one those ops return the
    no-match vector ``[0, 0, 0]`` — see :func:`set_match_template`.
    """
    policy = _policy(on_error)
    if template is None:
        return _apply_impl(image, name, a, b, coerce, device, policy, fast)
    prev = _ops._MATCH_CTX.get("template")
    _ops.set_match_template(template)
    try:
        return _apply_impl(image, name, a, b, coerce, device, policy, fast)
    finally:
        _ops.set_match_template(prev)


def _coerce_sort(v, sort: str):
    """The n-ary tier's version of :func:`_coerce_input`: only ``region`` inputs are touched."""
    a = np.asarray(v)
    if sort != "region":
        return a
    if a.dtype.kind == "b":
        return a.astype(np.float64)
    if a.dtype.kind in "fiu" and a.size:
        if _needs_binarise(a):                       # O(N) min/max test, same verdict as np.unique
            return (a.astype(np.float64) > 0.5).astype(np.float64)
        if a.dtype.kind in "iu":
            return a.astype(np.float64)
    return a


def _apply_impl(image, name, a, b, coerce, device, policy, fast=None):
    nop = _nary_by_name().get(name) if find_op(name) is None else None
    if nop is not None:                                  # n-ary tier: needs a LIST of inputs
        if isinstance(image, np.ndarray) or not isinstance(image, (list, tuple)):
            raise TypeError(
                "%r is an n-ary operator (arity %d, inputs %s): call "
                "fullseye.apply([%s], %r, a, b) with a list of inputs"
                % (name, nop.arity, list(nop.in_sorts),
                   ", ".join("x%d" % i for i in range(nop.arity)), name))
        if len(image) != nop.arity:
            raise TypeError("%r takes %d inputs %s, got %d"
                            % (name, nop.arity, list(nop.in_sorts), len(image)))
        inputs = [(_coerce_sort(x, srt) if coerce else np.asarray(x))
                  for x, srt in zip(image, nop.in_sorts)]
        # the n-ary functions carry no guard of their own: give them the same recorded,
        # sanitised fail-soft as every backend op (strict mode re-raises inside guard)
        w = _bs.guard(lambda v0, aa, bb: nop.fn(inputs, aa, bb), nop.out_sort, name=name)
        out = _run_guarded(name, lambda: w(inputs[0], a, b), policy, nop.out_sort, inputs[0])
        if nop.out_sort == "feature":
            return float(np.asarray(out).reshape(-1)[0])
        return out
    if isinstance(image, (list, tuple)):                 # legacy: a nested list IS an image
        image = np.asarray(image)

    op = _resolve(name)
    v = _coerce_input(image, op) if coerce else image
    v = _contract_dtype(v, op, policy)
    _guard_input(v, op, policy)
    use_fast = _fast_on(fast)

    def _call():
        if device != "cpu":
            res = _try_accel(op, v, a, b, device)
            if res is not _NOACCEL:
                return res
        elif use_fast:
            res = _try_fast(op, v, a, b)
            if res is not _NOACCEL:
                return res
        return _ops.RT[op.name](v, a, b)

    out = _run_guarded(op.name, _call, policy, op.out_sort, v)
    if op.out_sort == "feature":
        return float(np.asarray(out).reshape(-1)[0])
    return out


def run_pipeline(image, stages: Iterable, a: float = 0.5, b: float = 0.5,
                 coerce: bool = True, device: str = "cpu", on_error: str | None = None,
                 fast: bool | None = None):
    """Apply a sequence of operators, threading the array through each.

    *stages* is either a list of names (one shared ``a``/``b`` for the whole
    chain, like the CLI) **or** a list of ``(name, a, b)`` tuples for per-stage
    knobs — the latter is what you want when different stages need different
    tuning (the CLI cannot do this in a single call).

    ``coerce`` applies to the entry array only: every later value is an op output
    that already carries its declared sort, and region ops binarise at 0.5
    themselves, so re-coercing mid-chain would only strip gray levels a stage may
    still want (see :func:`_coerce_input`).

    ``device`` (default ``"cpu"``): ``"cuda"`` (or any non-cpu) runs the chain on the
    ``accel_bridge`` resident pipeline (unsupported ops fall back to CPU inside the
    bridge; consecutive accel ops share one transfer). torch/GPU *absent* silently
    uses the CPU path; a bridge that FAILS is recorded (source ``"gpu"``) and raises
    under ``on_error="raise"``. The GPU path uses ``ops.run_stages`` clip semantics
    (same as evolution champions) and only faithful ops go to the GPU, so task
    metrics are preserved (tests/test_accel_bridge.py).

    ``fast`` (default ``None`` = ``FULLSEYE_FAST``, i.e. off): as in :func:`apply`,
    but for the whole CPU chain — each stage that has a parity-gated cv2 twin in
    ``fast.py`` runs it. Ignored on the GPU path (the bridge is already the fast one).

    ``on_error``: as in :func:`apply`; fallbacks are attributed per stage.
    """
    policy = _policy(on_error)
    norm = []
    for st in stages:
        if isinstance(st, (tuple, list)):
            name, sa, sb = (list(st) + [a, b])[:3]
        else:
            name, sa, sb = st, a, b
        norm.append((name, float(sa), float(sb)))

    if device != "cpu" and norm:                          # GPU 経路(accel_bridge 常駐)
        try:
            import accel_bridge as _bridge
        except ImportError:
            _bridge = None
        if _bridge is not None:
            first_op = _resolve(norm[0][0])
            v0 = _coerce_input(image, first_op) if coerce else image
            v0 = _contract_dtype(v0, first_op, policy)
            _guard_input(v0, first_op, policy)
            try:
                with _bs.current_op("run_pipeline[gpu]"):
                    if policy == "raise":
                        with _bs.strict_mode(True):
                            return _bridge.run(norm, [v0], device=device)[0]
                    return _bridge.run(norm, [v0], device=device)[0]
            except Exception as e:       # noqa: BLE001 - bridge failed: recorded, then the CPU path runs
                if policy == "raise":
                    raise
                if policy == "warn":
                    with _bs.quiet_warnings():
                        _bs.record("run_pipeline[gpu]", e, None, source="gpu")
                    warnings.warn("fullseye: GPU pipeline failed, running on CPU (%s)" % _bs._fmt_exc(e),
                                  FullseyeFallbackWarning, stacklevel=2)
                else:
                    _bs.record("run_pipeline[gpu]", e, None, source="gpu")

    v = image
    first = True
    use_fast = _fast_on(fast)
    for name, sa, sb in norm:
        op = _resolve(name)
        if first:
            v = _coerce_input(v, op) if coerce else v
            v = _contract_dtype(v, op, policy)
            _guard_input(v, op, policy)
            first = False

        def _stage(_op=op, _v=v, _a=sa, _b=sb):
            if use_fast:
                res = _try_fast(_op, _v, _a, _b)
                if res is not _NOACCEL:
                    return res
            return _ops.RT[_op.name](_v, _a, _b)

        v = _run_guarded(op.name, _stage, policy, op.out_sort, v)
    return v


# ---- fallback ledger (re-exported from backend_safe) ------------------------ #
fallbacks = _bs.fallbacks
fallback_counts = _bs.fallback_counts
clear_fallbacks = _bs.clear_fallbacks
strict_mode = _bs.strict_mode
set_match_template = _ops.set_match_template
FAILED_BACKENDS = _ops.FAILED_BACKENDS


# ---- discovery ------------------------------------------------------------- #
def _rows():
    rows = [{"name": o.name, "halcon": o.halcon, "in_sort": o.in_sort,
             "out_sort": o.out_sort, "category": o.category, "tier": "registry"}
            for o in _ops.REGISTRY]
    rows += [{"name": o.name, "halcon": o.halcon, "in_sort": o.in_sorts[0],
              "out_sort": o.out_sort, "category": "nary", "tier": "nary",
              "arity": o.arity, "in_sorts": list(o.in_sorts)}
             for o in {id(o): o for o in _nary_by_name().values()}.values()]
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
