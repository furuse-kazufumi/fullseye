"""fullseye — evolvable HALCON-parity image-operator library + pipeline designer.

Public package facade. Import this from any project::

    import fullseye
    out = fullseye.apply(frame, "gauss_filter")        # numpy in, numpy out
    seg = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])

The engine modules (``ops``, ``backends*``, ``evolve``, ``scale`` ...) live one
directory up as flat modules for historical reasons; this facade puts that
directory on ``sys.path`` and re-exports the stable API defined in ``api.py``.
Everything here works on numpy arrays with no file I/O (see :func:`apply`).
"""
from __future__ import annotations

import os
import sys
import warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# The extended backends run a wavelet transform at build() time which emits a
# benign pywt boundary UserWarning; keep the consumer's import clean.
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from api import (  # noqa: E402,F401
        apply, run_pipeline, find_op, list_ops, op_names, categories,
        read_image, write_image, RT, REGISTRY, __version__, version,
        stereo, disparity_map, disparity_subpixel, lr_consistency,
        depth_from_disparity, reproject_to_points,
        census_transform, disparity_census, disparity_sgm,
        speckle_filter, fill_disparity, disparity_confidence,
        terrain, elevation_map, traversability, foothold_score, fill_gaps,
        ground_surface, ground_plane, detect_obstacles,
        fuse_elevation, slope_map, roughness_map, surface_normals,
        step_edges, foothold_candidates,
        locomotion, contact_points, com_from_silhouette, support_polygon,
        com_support_margin, gait_phase,
        imgio, to_float01, to_uint8, apply_cmap, colorize_depth,
        colorize_disparity, colorize_labels, colorize_height, colorize_flow,
        shaded_relief, overlay_mask, save, load, save_ply, COLORMAPS,
        detect, segment_objects, object_descriptor, nearest_prototype, draw_objects,
        registration, kabsch, icp, point_to_plane_icp, apply_transform,
        pca_align, register, feature_register,
        ppf, ppf_model, surface_match, find_surface_pose,
        pointcloud, estimate_normals, voxel_downsample,
        remove_statistical_outliers, remove_radius_outliers, fpfh,
        pcseg, fit_plane, fit_plane_ransac, fit_sphere_ransac, fit_cylinder_ransac,
        plane_distance, height_above_plane, remove_ground,
        euclidean_clusters, region_growing, aabb, obb, crop_box, crop_sphere,
        farthest_point_sampling, curvature, centroid, principal_axes,
        mesh, read_mesh, read_points, write_mesh, write_points, sample_surface,
        mesh_to_points, voxelize, bounds, recenter, normalize_scale,
        meshio_opt, read_gltf, read_gltf_merged, read_las, read_pcd, formats_available,
        volio, read_volume, write_volume, list_dicom_series, VolumeMeta,
        raster, read_raster, to01, read_depth, read_pfm, write_pfm, save16,
        render3d, render_mesh, look_at, intrinsics_from_fov, auto_view,
        mesh_to_sdf, voxelize_solid, marching_cubes,
        camera, intrinsic_matrix, decompose_intrinsics, projection_matrix,
        project_points, backproject, depth_to_points, normals_from_depth,
        triangulate, reprojection_error, solve_pnp, rodrigues, rotation_log,
        fundamental_matrix, essential_matrix, essential_from_fundamental,
        decompose_essential, recover_pose, epipolar_lines,
        distort_points, undistort_points, stereo_rectify,
        odometry, rgbd_odometry, pnp_odometry, integrate_trajectory,
        umeyama_align, trajectory_error,
        grasp, Grasp, sample_antipodal_grasps, grasps_from_mesh, force_closure,
        ferrari_canny_quality, approach_vector_from_normals, rank_grasps,
        grasp_pose, collision_free,
        meshrepair, is_watertight, is_edge_manifold, boundary_edges, weld_vertices,
        remove_degenerate_faces, orient_consistent, fill_holes, smooth_taubin,
        decimate_qem, convex_hull, inertia_tensor, components,
        volops, vol_frangi, vol_sato, vol_hessian_blobness, vol_distance_transform,
        vol_label, vol_region_props, vol_gradient_magnitude, vol_local_maxima, vol_watershed,
        complexops, cx_fft, cx_ifft, cx_magnitude, cx_phase, cx_real, cx_imag,
        cx_log_magnitude, cx_from_mag_phase, phase_unwrap, cx_wiener_deconvolve,
        cx_apply_transfer_function, cx_bandpass,
        specops, BandMeta, read_envi, write_envi, spec_band, spec_rgb_composite,
        spec_nearest_band, spec_band_ratio, spec_index, spec_angle_mapper, spec_pca,
        spec_mnf, spec_unmix, spec_endmembers_ppi, spec_continuum_removal,
        videops, temporal_mean, temporal_median, temporal_std, temporal_max,
        temporal_min, frame_difference, background_subtraction, temporal_gradient,
        motion_energy, moving_average, spatiotemporal_gaussian, spatiotemporal_sobel,
        per_frame, flicker_reduce, optical_flow_sequence,
        pose, pose_descriptor, skeleton_nodes, principal_axis,
        flow, optical_flow_lk, optical_flow_hs, warp_by_flow,
        flow_magnitude, flow_angle, track_points,
        motion, frame_motion_energy, dominant_motion, flow_from_model,
        residual_motion, motion_segments, motion_energy_series, detect_events,
        sceneflow, flow_divergence, flow_curl, focus_of_expansion, time_to_contact,
        looming, ego_translation_from_flow, scene_flow,
        video, read_frames, iter_frames, frame_pairs, write_video, probe,
        recipes, recipe, measure, line_profile, distance, angle,
        fit_line, fit_circle, fit_ellipse, fit_rectangle2,
    )
    from engine import FullseyeEngine, diagnose_stages  # noqa: E402,F401  (pipeline runtime)
    from acquire import (  # noqa: E402,F401  (image acquisition: cameras / framegrabbers)
        Camera, list_cameras, open_framegrabber, grab_image, close_framegrabber,
    )
    from comm import (  # noqa: E402,F401  (communication transports / industrial protocols)
        open_channel, protocols, Channel,
        TcpChannel, UdpChannel, HttpChannel, ModbusTcpChannel, ModbusTcpServer,
    )
    from device import DigitalIO, pulse, signal_result, wait_input  # noqa: E402,F401  (device control)
    from dsp import (  # noqa: E402,F401  (1-D signal / acoustic / vibration — beyond images)
        read_wav, write_wav, read_audio, spectrum, spectrogram,
        lowpass, highpass, bandpass, envelope, rms, find_peaks, signal_features,
    )


def capabilities() -> dict:
    """What this install can connect to and drive, across all three connectivity
    families: ``{"comm": [...], "acquire": [...], "device": [...]}``. Each entry
    reports ``kind`` (native / optional / scaffold), whether it is ``available``
    here, and the ``pip`` package that unlocks it. The comprehensive, honest menu
    of protocols (23), image sources (9) and device drivers (12)."""
    import comm
    import acquire
    import device
    return {"comm": comm.capabilities(),
            "acquire": acquire.capabilities(),
            "device": device.capabilities()}

__all__ = [
    "apply", "run_pipeline", "find_op", "list_ops", "op_names", "categories",
    "read_image", "write_image", "RT", "REGISTRY", "__version__", "version",
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
    "imgio", "to_float01", "to_uint8", "apply_cmap", "colorize_depth",
    "colorize_disparity", "colorize_labels", "colorize_height", "colorize_flow",
    "shaded_relief", "overlay_mask", "save", "load", "save_ply", "COLORMAPS",
    "detect", "segment_objects", "object_descriptor", "nearest_prototype", "draw_objects",
    "registration", "kabsch", "icp", "point_to_plane_icp", "apply_transform",
    "pca_align", "register", "feature_register",
    "ppf", "ppf_model", "surface_match", "find_surface_pose",
    "pointcloud", "estimate_normals", "voxel_downsample",
    "remove_statistical_outliers", "remove_radius_outliers", "fpfh",
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
    "grasp", "Grasp", "sample_antipodal_grasps", "grasps_from_mesh", "force_closure",
    "ferrari_canny_quality", "approach_vector_from_normals", "rank_grasps",
    "grasp_pose", "collision_free",
    "meshrepair", "is_watertight", "is_edge_manifold", "boundary_edges", "weld_vertices",
    "remove_degenerate_faces", "orient_consistent", "fill_holes", "smooth_taubin",
    "decimate_qem", "convex_hull", "inertia_tensor", "components",
    "volops", "vol_frangi", "vol_sato", "vol_hessian_blobness", "vol_distance_transform",
    "vol_label", "vol_region_props", "vol_gradient_magnitude", "vol_local_maxima", "vol_watershed",
    "complexops", "cx_fft", "cx_ifft", "cx_magnitude", "cx_phase", "cx_real", "cx_imag",
    "cx_log_magnitude", "cx_from_mag_phase", "phase_unwrap", "cx_wiener_deconvolve",
    "cx_apply_transfer_function", "cx_bandpass",
    "specops", "BandMeta", "read_envi", "write_envi", "spec_band", "spec_rgb_composite",
    "spec_nearest_band", "spec_band_ratio", "spec_index", "spec_angle_mapper", "spec_pca",
    "spec_mnf", "spec_unmix", "spec_endmembers_ppi", "spec_continuum_removal",
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
    "video", "read_frames", "iter_frames", "frame_pairs", "write_video", "probe",
    "recipes", "recipe", "measure", "line_profile", "distance", "angle",
    "fit_line", "fit_circle", "fit_ellipse", "fit_rectangle2",
    "FullseyeEngine", "diagnose_stages",
    "Camera", "list_cameras", "open_framegrabber", "grab_image", "close_framegrabber",
    "open_channel", "protocols", "capabilities", "Channel",
    "TcpChannel", "UdpChannel", "HttpChannel", "ModbusTcpChannel", "ModbusTcpServer",
    "DigitalIO", "pulse", "signal_result", "wait_input",
    "read_wav", "write_wav", "read_audio", "spectrum", "spectrogram",
    "lowpass", "highpass", "bandpass", "envelope", "rms", "find_peaks", "signal_features",
    "capabilities",
]
