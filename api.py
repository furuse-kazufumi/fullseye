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
import handpose  # noqa: E402  (hand 21-keypoint pose + finger flexions; detection needs optional mediapipe)
import complexops  # noqa: E402  (complex/FFT-domain ops + 2-D phase unwrap [HALCON has none])
import specops  # noqa: E402  (multispectral/hyperspectral cube: ENVI + SAM + unmix + band math)
import videops  # noqa: E402  (video / temporal (T,H,W): temporal denoise, bg-subtract, motion, spatiotemporal filters)
import algo  # noqa: E402  (general-algorithm tier: seq/scalar sorts+reductions with Python+C references)
import algo_codegen  # noqa: E402  (standalone Python/C emission for the general tier)
import algo_difftest as _algo_difftest  # noqa: E402  (honest gate: Python==oracle, C==Python bit-for-bit)
import synth  # noqa: E402  (learn an image's features -> synthesise a similar image; classical texture synthesis)
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
    vol_boundary, vol_boundary_points,
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
