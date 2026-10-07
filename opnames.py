# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Canonical op names, phase 1 of the naming cleanup (2026-10-07).

Fullseye exposes ops through four doors: the evolvable 2-D registry
(``fullseye.op.<name>`` / ``fullseye.apply``), the typed ledgers
(``fullseye.ledger.<name>`` / ``fullseye.op_run``), the one-line facade
(``fullseye.<name>``) and the HALCON-chapter vision namespaces
(``fullseye.vision.<chapter>.<name>``). 27 bare names meant *different functions*
behind different doors (``fs.lowpass`` is a 1-D Butterworth filter,
``fs.op.lowpass`` a 2-D FFT filter; ``fill_holes`` is a mesh, a depth-map or a
region operation depending on the door). Mixing them does not raise - it
returns a plausible wrong answer.

Phase 1 only ADDS names. Every old name keeps working, unchanged, forever in
phase 1. Each table below maps a new canonical name to the callable an old name
already reaches, in exactly one door:

* ``REGISTRY_ALIASES`` - resolved by ``api.find_op`` (so ``fullseye.apply``,
  ``fullseye.op.<canonical>``, ``run_pipeline``) and by the CLI's ``_find_op``.
  The registry itself is never touched: evolution genomes decode ops by
  ``ops.REGISTRY`` index order, so a canonical name is a lookup alias, not a new Op.
* ``LEDGER_ALIASES`` - resolved by ``fullseye.ledger`` and ``opassist``
  (``op_run`` / ``op_assist`` / ``op_presets`` ...). The value pins the ledger
  module, so a name hidden by ledger order (``gaussians_to_voxel`` of
  ``opsreprconv``) becomes reachable by its canonical name.
* ``FACADE_ALIASES`` - ``fullseye/__init__.py`` binds each canonical name to the
  same object as the old facade name and lists it in ``fullseye.__all__``.
* ``VISION_ALIASES_PENDING`` - decided but not exposed yet (phase 2: the vision
  namespaces have no alias mechanism yet).

HALCON operator names are frozen: where one side of an ambiguous name is the
HALCON-faithful operator (``fullseye.vision.*.bit_not`` and friends) it keeps the
name and only the other side gets a canonical alias.

Naming guideline for new names (enforced for new names by
``tests/test_op_names_phase1.py`` as a ratchet over today's names):

1. HALCON names are frozen; a ``<lib>_`` prefix only for alternative backends.
2. New typed-ledger ops: ``<family>_<object>_<action>``; no one-word names.
3. Disambiguate by dimension / object prefix: ``signal_`` ``image_`` ``region_``
   ``mesh_`` ``points_`` ``depth_`` ``vol_``.
4. American spelling (``normalize``, ``color``, ``center``, ``neighbor``).
5. Conversions read ``<a>_to_<b>``; 3-D variants end in ``_3d``.

This module holds data only (no functions), so it adds no public callable that
the reachability gate would have to account for.
"""
from __future__ import annotations

#: canonical name -> registry op name (``ops.REGISTRY``).
REGISTRY_ALIASES: dict[str, str] = {
    'glcm_energy': 'cooc_feature_matrix',
    'image_companding_mu_law': 'companding_mu_law',
    'image_fft_highpass': 'highpass',
    'image_fft_lowpass': 'lowpass',
    'image_invert_unit_range': 'bit_not',
    'image_local_entropy': 'entropy_image',
    'image_local_std': 'local_std',
    'region_fill_holes': 'fill_holes',
}

#: canonical name -> (ledger module, ledger op name). The module is part of the
#: key because the same ledger op name can exist in two ledgers.
LEDGER_ALIASES: dict[str, tuple[str, str]] = {
    'annotate_overlay_mask': ('opsannotate', 'overlay_mask'),
    'ball_bounce': ('opsdrive', 'bounce'),
    'bundle_project_points': ('ops3d', 'project'),
    'cplx_domain_color': ('opsmath', 'cplx_domain_colour'),
    'depth_fill_holes': ('ops3d', 'fill_holes'),
    'depth_to_points_strided': ('ops3d', 'depth_to_points'),
    'efd_invariants': ('opsshape2d', 'invariants'),
    'efd_normalize': ('opsshape2d', 'normalize'),
    'efd_reconstruct': ('opsshape2d', 'reconstruct'),
    'estimate_normals_outward': ('ops3d', 'estimate_normals'),
    'gaussian_arrays_to_voxel': ('ops3d', 'gaussians_to_voxel'),
    'gaussian_set_to_voxel': ('opsreprconv', 'gaussians_to_voxel'),
    'geodesic_farthest_point_sampling': ('ops3d', 'farthest_point_sampling'),
    'glass_from_abbe': ('opsoptics', 'glass'),
    'heightfield_normals': ('ops3d', 'surface_normals'),
    'histogram_match_transport': ('opscolortransport', 'histogram_match'),
    'hole_center_from_rgbd': ('opsdrive', 'hole_centre_from_rgbd'),
    'image_cross_dissolve': ('opsshape2d', 'blend'),
    'image_global_entropy': ('opsimgmetrics', 'image_entropy'),
    'image_morph_by_points': ('opsshape2d', 'morph'),
    'lidar_scan_mesh': ('opsdrive', 'lidar_scan'),
    'mesh_taubin_smooth': ('ops3d', 'taubin_smooth'),
    'mesh_to_surface_points': ('ops3d', 'mesh_to_points'),
    'neighbor_index_gaps': ('opsmath', 'neighbour_index_gaps'),
    'occupancy_inflate': ('ops3d', 'inflate'),
    'perlin_noise_2d': ('opsdrive', 'perlin2'),
    'photometric_stereo_masked': ('ops3d', 'photometric_stereo'),
    'point_to_line_distance': ('ops3d', 'distance_point_line'),
    'points_cutout': ('ops3d', 'cutout'),
    'points_euclidean_cluster_labels': ('ops3d', 'euclidean_cluster'),
    'points_global_shape_descriptor': ('ops3d', 'describe'),
    'points_inertia_tensor': ('ops3d', 'inertia_tensor'),
    'points_jitter': ('ops3d', 'jitter'),
    'points_project_to_image': ('ops3d', 'project_points'),
    'points_region_growing_normal_angle': ('ops3d', 'region_growing'),
    'profile_normalize': ('opsprofile', 'profile_normalise'),
    'range_image_normals': ('ops3d', 'normals_from_depth'),
    'recover_pose_from_points': ('ops3d', 'recover_pose'),
    'reflect_direction': ('ops3d', 'reflect'),
    'refract_direction': ('ops3d', 'refract'),
    'reprojection_rms_error': ('ops3d', 'reprojection_error'),
    'scene_flow_magnitude': ('opsreprconv', 'flow_magnitude'),
    'scene_trace_rays': ('opsoptics', 'trace_rays'),
    'signal_bandpass': ('ops1d', 'bandpass'),
    'signal_companding_mu_law': ('ops1d', 'companding_mu_law'),
    'signal_highpass': ('ops1d', 'highpass'),
    'signal_local_std': ('ops1d', 'local_std'),
    'signal_lowpass': ('ops1d', 'lowpass'),
    'signal_quantize': ('ops1d', 'quantize'),
    'ssaa_downsample': ('ops3d', 'antialias'),
    'superquadric_sample_surface': ('ops3d', 'sample_surface'),
    'tsdf_fuse_depths': ('ops3d', 'fuse'),
    'tsdf_integrate_depth': ('ops3d', 'integrate'),
    'twoview_triangulate': ('ops3d', 'triangulate'),
    'visual_hull_carve': ('ops3d', 'carve'),
    'vol_distance_watershed': ('opssegmentation', 'watershed_vol'),
    'vol_marker_watershed': ('ops3d', 'vol_watershed'),
    'wet_surface_color': ('opsoptics', 'wetness'),
    'world_points_to_pixels': ('opsdrive', 'reproject'),
}

#: canonical name -> existing facade name; ``fullseye.<canonical> is fullseye.<old>``.
FACADE_ALIASES: dict[str, str] = {
    'camera_depth_to_points': 'depth_to_points',
    'camera_normals_from_depth': 'normals_from_depth',
    'camera_project_points': 'project_points',
    'camera_triangulate': 'triangulate',
    'cplx_domain_color': 'cplx_domain_colour',
    'estimate_normals_pca': 'estimate_normals',
    'euclidean_farthest_point_sampling': 'farthest_point_sampling',
    'glass_from_abbe': 'glass',
    'glyph_normalize': 'glyph_normalise',
    'histogram_match_nearest_rank': 'match_histogram',
    'histogram_match_transport': 'histogram_match',
    'image_global_entropy': 'image_entropy',
    'image_paint_mask': 'overlay_mask',
    'lens_trace_rays': 'trace_rays',
    'mesh_fill_holes': 'fill_holes',
    'mesh_mass_properties': 'inertia_tensor',
    'mesh_sample_surface': 'sample_surface',
    'mesh_vertices_taubin_smooth': 'smooth_taubin',
    'neighbor_index_gaps': 'neighbour_index_gaps',
    'optical_flow_magnitude': 'flow_magnitude',
    'points_euclidean_cluster_indices': 'euclidean_clusters',
    'points_region_growing_smoothness': 'region_growing',
    'recover_pose_from_essential': 'recover_pose',
    'reprojection_error_per_point': 'reprojection_error',
    'signal_bandpass': 'bandpass',
    'signal_highpass': 'highpass',
    'signal_lowpass': 'lowpass',
    'terrain_surface_normals': 'surface_normals',
    'vol_marker_watershed': 'vol_watershed',
    'wet_surface_color': 'wetness',
}

#: canonical name -> (vision namespace, vision op name). Not exposed in phase 1.
VISION_ALIASES_PENDING: dict[str, tuple[str, str]] = {
    'lidar_scan_demo': ('gsplat', 'lidar_scan'),
}

#: old name -> {door: canonical}. Door keys: ``registry``, ``ledger:<module>``,
#: ``facade``, ``vision``. Derived from the tables above (the test checks that).
RENAMED: dict[str, dict[str, str]] = {
    'antialias': {'ledger:ops3d': 'ssaa_downsample'},
    'bandpass': {'facade': 'signal_bandpass', 'ledger:ops1d': 'signal_bandpass'},
    'bit_not': {'registry': 'image_invert_unit_range'},
    'blend': {'ledger:opsshape2d': 'image_cross_dissolve'},
    'bounce': {'ledger:opsdrive': 'ball_bounce'},
    'carve': {'ledger:ops3d': 'visual_hull_carve'},
    'companding_mu_law': {'ledger:ops1d': 'signal_companding_mu_law', 'registry': 'image_companding_mu_law'},
    'cooc_feature_matrix': {'registry': 'glcm_energy'},
    'cplx_domain_colour': {'facade': 'cplx_domain_color', 'ledger:opsmath': 'cplx_domain_color'},
    'cutout': {'ledger:ops3d': 'points_cutout'},
    'depth_to_points': {'facade': 'camera_depth_to_points', 'ledger:ops3d': 'depth_to_points_strided'},
    'describe': {'ledger:ops3d': 'points_global_shape_descriptor'},
    'distance_point_line': {'ledger:ops3d': 'point_to_line_distance'},
    'entropy_image': {'registry': 'image_local_entropy'},
    'estimate_normals': {'facade': 'estimate_normals_pca', 'ledger:ops3d': 'estimate_normals_outward'},
    'euclidean_cluster': {'ledger:ops3d': 'points_euclidean_cluster_labels'},
    'euclidean_clusters': {'facade': 'points_euclidean_cluster_indices'},
    'farthest_point_sampling': {'facade': 'euclidean_farthest_point_sampling', 'ledger:ops3d': 'geodesic_farthest_point_sampling'},
    'fill_holes': {'facade': 'mesh_fill_holes', 'ledger:ops3d': 'depth_fill_holes', 'registry': 'region_fill_holes'},
    'flow_magnitude': {'facade': 'optical_flow_magnitude', 'ledger:opsreprconv': 'scene_flow_magnitude'},
    'fuse': {'ledger:ops3d': 'tsdf_fuse_depths'},
    'gaussians_to_voxel': {'ledger:ops3d': 'gaussian_arrays_to_voxel', 'ledger:opsreprconv': 'gaussian_set_to_voxel'},
    'glass': {'facade': 'glass_from_abbe', 'ledger:opsoptics': 'glass_from_abbe'},
    'glyph_normalise': {'facade': 'glyph_normalize'},
    'highpass': {'facade': 'signal_highpass', 'ledger:ops1d': 'signal_highpass', 'registry': 'image_fft_highpass'},
    'histogram_match': {'facade': 'histogram_match_transport', 'ledger:opscolortransport': 'histogram_match_transport'},
    'hole_centre_from_rgbd': {'ledger:opsdrive': 'hole_center_from_rgbd'},
    'image_entropy': {'facade': 'image_global_entropy', 'ledger:opsimgmetrics': 'image_global_entropy'},
    'inertia_tensor': {'facade': 'mesh_mass_properties', 'ledger:ops3d': 'points_inertia_tensor'},
    'inflate': {'ledger:ops3d': 'occupancy_inflate'},
    'integrate': {'ledger:ops3d': 'tsdf_integrate_depth'},
    'invariants': {'ledger:opsshape2d': 'efd_invariants'},
    'jitter': {'ledger:ops3d': 'points_jitter'},
    'lidar_scan': {'ledger:opsdrive': 'lidar_scan_mesh', 'vision': 'lidar_scan_demo'},
    'local_std': {'ledger:ops1d': 'signal_local_std', 'registry': 'image_local_std'},
    'lowpass': {'facade': 'signal_lowpass', 'ledger:ops1d': 'signal_lowpass', 'registry': 'image_fft_lowpass'},
    'match_histogram': {'facade': 'histogram_match_nearest_rank'},
    'mesh_to_points': {'facade': 'mesh_sample_surface', 'ledger:ops3d': 'mesh_to_surface_points'},
    'morph': {'ledger:opsshape2d': 'image_morph_by_points'},
    'neighbour_index_gaps': {'facade': 'neighbor_index_gaps', 'ledger:opsmath': 'neighbor_index_gaps'},
    'normalize': {'ledger:opsshape2d': 'efd_normalize'},
    'normals_from_depth': {'facade': 'camera_normals_from_depth', 'ledger:ops3d': 'range_image_normals'},
    'overlay_mask': {'facade': 'image_paint_mask', 'ledger:opsannotate': 'annotate_overlay_mask'},
    'perlin2': {'ledger:opsdrive': 'perlin_noise_2d'},
    'photometric_stereo': {'ledger:ops3d': 'photometric_stereo_masked'},
    'profile_normalise': {'ledger:opsprofile': 'profile_normalize'},
    'project': {'ledger:ops3d': 'bundle_project_points'},
    'project_points': {'facade': 'camera_project_points', 'ledger:ops3d': 'points_project_to_image'},
    'quantize': {'ledger:ops1d': 'signal_quantize'},
    'reconstruct': {'ledger:opsshape2d': 'efd_reconstruct'},
    'recover_pose': {'facade': 'recover_pose_from_essential', 'ledger:ops3d': 'recover_pose_from_points'},
    'reflect': {'ledger:ops3d': 'reflect_direction'},
    'refract': {'ledger:ops3d': 'refract_direction'},
    'region_growing': {'facade': 'points_region_growing_smoothness', 'ledger:ops3d': 'points_region_growing_normal_angle'},
    'reproject': {'ledger:opsdrive': 'world_points_to_pixels'},
    'reprojection_error': {'facade': 'reprojection_error_per_point', 'ledger:ops3d': 'reprojection_rms_error'},
    'sample_surface': {'facade': 'mesh_sample_surface', 'ledger:ops3d': 'superquadric_sample_surface'},
    'smooth_taubin': {'facade': 'mesh_vertices_taubin_smooth'},
    'surface_normals': {'facade': 'terrain_surface_normals', 'ledger:ops3d': 'heightfield_normals'},
    'taubin_smooth': {'ledger:ops3d': 'mesh_taubin_smooth'},
    'trace_rays': {'facade': 'lens_trace_rays', 'ledger:opsoptics': 'scene_trace_rays'},
    'triangulate': {'facade': 'camera_triangulate', 'ledger:ops3d': 'twoview_triangulate'},
    'vol_watershed': {'facade': 'vol_marker_watershed', 'ledger:ops3d': 'vol_marker_watershed'},
    'watershed_vol': {'ledger:opssegmentation': 'vol_distance_watershed'},
    'wetness': {'facade': 'wet_surface_color', 'ledger:opsoptics': 'wet_surface_color'},
}

#: Old names that mean different functions behind different doors (group a).
#: ``fullseye.ledger.<name>`` warns (FutureWarning) for these only when the
#: environment variable ``FULLSEYE_WARN_AMBIGUOUS_NAMES`` is set to a non-empty
#: value other than ``0`` - off by default in phase 1.
AMBIGUOUS_NAMES: frozenset[str] = frozenset({
    'bit_not',
    'companding_mu_law',
    'cooc_feature_matrix',
    'depth_to_points',
    'distance_point_line',
    'estimate_normals',
    'farthest_point_sampling',
    'fill_holes',
    'flow_magnitude',
    'gaussians_to_voxel',
    'highpass',
    'inertia_tensor',
    'lidar_scan',
    'local_std',
    'lowpass',
    'mesh_to_points',
    'normals_from_depth',
    'overlay_mask',
    'photometric_stereo',
    'project_points',
    'recover_pose',
    'region_growing',
    'reprojection_error',
    'sample_surface',
    'surface_normals',
    'trace_rays',
    'triangulate',
})
