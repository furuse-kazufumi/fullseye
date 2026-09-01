# 型変換の行列 ―― 穴と不具合の点検

`py -3.11 tools/conversion_matrix.py --md docs/CONVERSION_MATRIX.md` の生成物。
手で編集しない。

```
型 59 / 変換ペア 164 / 変換を行う op のべ 441
生成器のある型 37 / 出力型に述語のある型 57

■ 袋小路 (17) ― 産めるのに、そこから他の型へ出られない
   angle            ← 1 型から来る
   axes             ← 1 型から来る
   countrate        ← 0 型から来る
   cscalar          ← 1 型から来る
   curvature        ← 3 型から来る
   flow_dense       ← 1 型から来る
   flow_scattered   ← 1 型から来る
   frame            ← 1 型から来る
   gradient         ← 1 型から来る
   graph            ← 1 型から来る
   hessian          ← 1 型から来る
   indices          ← 3 型から来る
   pairs            ← 5 型から来る
   pointmap         ← 1 型から来る
   roots            ← 1 型から来る
   rot_scale        ← 1 型から来る
   shift            ← 1 型から来る

■ 孤児 (1) ― 生成器も無く、どの op も産まない
   any

■ 構造的に到達不能 (1) ― 不動点で閉じても届かない
   any

■ 誰も食べない型 (15) ― 出力専用。終端なら正しい
   axes, cscalar, curvature, flow_dense, flow_scattered, frame, gradient, graph, hessian, indices, pairs, pointmap, roots, rot_scale, shift

■ 出力型に述語が無い変換 op (0) ― 何を返しても TYPEMISS にならない
   対象の型: 

■ 片道の変換 (110) ― A→B はあるが B→A が無い(戻せないのが正しい場合も多い)
   any              → pose              register_cross, register_cross
   any              → voxel             fuse_to_voxel
   beatcube         → image2d           range_doppler_map
   beatcube         → signal            fmcw_range_profile, beamform_delay_sum
   beatcube         → table             beamform_doa
   bspline_surface  → measurement       surface_residual
   cimage           → jones             jones_apply
   cimage           → measurement       cplx_cr_residual
   counts           → measurement       dtof_depth
   counts           → table             tcspc_stats, lifetime_fit, lifetime_phasor
   cpoints          → cscalar           cplx_contour_integral, cplx_contour_integral, cplx_cauchy_value
   cpoints          → measurement       cplx_winding_number, cplx_argument_principle, cplx_argument_principle
   cpoints          → table             cplx_laurent_coeffs, cplx_laurent_coeffs
   depth            → normalmap         normals_from_depth
   depth            → pointmap          depth_to_organized_points
   depth            → sdf               tsdf_from_depth, fuse, integrate
   descriptor       → measurement       shape_distance, shape_distance
   gaussians        → points            to_points
   image2d          → matrix            fundamental_8point, fundamental_8point, essential_8point
   image2d          → measurement       surface_form_error, edge_alias_energy, surface_residual
   image2d          → pairs             psf_to_mtf
   image2d          → pose              recover_pose, recover_pose
   images           → depth             decode_fringe
   images           → normalmap         photometric_stereo, photometric_stereo_robust
   jones            → stokes            stokes_from_jones
   keypoints        → measurement       reprojection_error
   keypoints        → pose              dlt_pose, pnp_ransac
   keypoints        → table             cad_pixel_to_surface
   labels           → table             vol_region_props, cad_defect_to_cad
   labels           → vector            illuminant_from_dichromatic_planes
   lightfield       → images            lf_views, lf_focal_stack
   lightfield       → table             lf_stats
   matrix           → measurement       mat_cond
   matrix           → signal            mat_solve
   matrix           → stokes            mueller_apply
   mesh             → curvature         vertex_curvature
   mesh             → image2d           ambient_occlusion, cast_shadow, supersample_mesh
   mesh             → indices           cad_visible_faces
   mesh             → measurement       mesh_area
   mesh             → normals           face_normals, vertex_normals
   mesh             → rgbimage          render_beauty
   mesh             → signal            geodesic_mesh
   mesh             → table             cad_pixel_to_surface, cad_surface_to_pixel, cad_defect_to_cad
   normalmap        → rgbimage          dichromatic_render
   normals          → descriptor        compute_fpfh, shot_descriptor
   normals          → measurement       normal_consistency
   normals          → pose              icp_point2plane
   normals          → primitive         ransac_cylinder
   points           → axes              moment_axes
   points           → curvature         principal_curvatures
   points           → descriptor        compute_fpfh, shot_descriptor, d2_distribution
   points           → flow_scattered    nearest_neighbor_flow, nearest_neighbor_flow, smooth_flow
   points           → frame             frenet_frame
   points           → graph             knn_graph
   points           → indices           iss_keypoints, alpha_shape_boundary, farthest_point_sampling
   points           → keypoints         project_points
   points           → labels            region_growing, euclidean_cluster, plane_segmentation
   points           → matrix            inertia_tensor
   points           → measurement       angle_3points, distance_point_plane, distance_point_line
   points           → normals           estimate_point_normals, estimate_normals, estimate_oriented_normals
   points           → pairs             curvature_torsion
   points           → pose              match_pca, match_pca, icp_point2point_3d
   points           → position          match_points_ncc, match_points_ncc
   points           → primitive         line_from_2points, plane_from_3points, fit_line_3d
   points           → signal            mean_curvature, gaussian_curvature, geodesic_distances
   points           → table             central_moments, cad_surface_to_pixel
   polsweep         → stokes            polarization_stokes
   pose             → measurement       pose_error, pose_error, mean_reprojection_error
   position         → table             refine_lm
   primitive        → measurement       angle_between_lines, angle_between_planes, angle_line_plane
   primitive        → position          intersect_line_plane
   rgbimage         → image2d           specular_coefficient_map
   rgbimage         → vector            illuminant_from_dichromatic_planes
   rle_region       → measurement       vol_rle_volume
   rle_region       → position          vol_rle_centroid
   rle_region       → primitive         vol_rle_bbox
   score            → position          refine_peak_newton
   sdf              → measurement       query_distance
   signal           → cpoints           cplx_poly_eval
   signal           → image2d           spectrogram
   signal           → indices           zero_crossings_funct_1d, find_peaks
   signal           → measurement       distance_funct_1d, distance_funct_1d, num_points_funct_1d
   signal           → pairs             invert_funct_1d, transform_funct_1d, x_range_funct_1d
   signal           → roots             poly_roots
   stokes           → table             stokes_analyze
   sweep            → measurement       csi_peak_position, chromatic_confocal_height
   sweep            → signal            csi_envelope
   vector           → image2d           cast_shadow
   vector           → normals           reflect, refract
   vector           → points            sample_surface
   video            → image2d           temporal_band_power
   video            → pairs             displacement_series, riesz_displacement_series
   video            → table             band_snr, motion_magnify, phase_displacement
   voxel            → angle             refine_rotation_z, refine_rotation_z
   voxel            → curvature         curvature_maps
   voxel            → descriptor        sh_descriptor
   voxel            → flow_dense        scene_flow_lk, scene_flow_lk
   voxel            → gradient          sobel3d, gradient3d
   voxel            → hessian           hessian3d
   voxel            → image2d           render_volume_projection
   voxel            → keypoints         harris3d_keypoints
   voxel            → labels            label_components, vol_label, vol_watershed
   voxel            → pairs             vol_profile_line
   voxel            → position          match_shape_3d, match_shape_3d, match_chamfer_3d
   voxel            → primitive         vol_bounding_box, hough_plane_3d, hough_sphere_3d
   voxel            → rot_scale         match_logpolar_z, match_logpolar_z
   voxel            → shift             match_phase_3d, match_phase_3d
   voxel            → signal            vol_wall_thickness
   voxel            → table             vol_edge_probe, refine_lm, refine_lm
   zscan            → image2d           csi_contrast_map

■ 行列(セル = その変換を行う op の数)
| from \ to | angle | any | axes | beatcube | bspline_curve | bspline_surface | cimage | counts | cpoints | cscalar | curvature | deformation | depth | descriptor | flow_dense | flow_scattered | frame | gaussians | gradient | graph | hessian | histcube | image2d | images | indices | jones | keypoints | labels | lightfield | matrix | measurement | mesh | normalmap | normals | pairs | pointmap | points | polsweep | poly_surface | pose | position | primitive | qimage | rgbimage | rle_region | roots | rot_scale | score | sdf | shift | signal | stokes | sweep | table | vector | video | voxel | zscan |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **angle** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **any** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |
| **axes** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **beatcube** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  | 1 |  |  |  |  |
| **bspline_curve** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **bspline_surface** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **cimage** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 6 |  |  | 1 |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **counts** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |
| **cpoints** |  |  |  |  |  |  |  |  |  | 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |
| **cscalar** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **curvature** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **deformation** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **depth** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 | 2 |  |  |  |  |  |  |  |  |  | 1 |  |  | 1 | 2 |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  |  |  | 1 |
| **descriptor** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **flow_dense** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **flow_scattered** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **frame** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **gaussians** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **gradient** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **graph** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **hessian** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **histcube** |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **image2d** |  |  |  |  |  | 3 | 3 |  |  |  |  |  | 4 |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  | 1 | 4 | 7 |  | 1 |  | 1 |  | 3 | 2 | 3 | 2 |  |  | 2 |  |  |  |  |  |  |  |  |  |  | 4 |  |  |  |  |
| **images** |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |
| **indices** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **jones** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |
| **keypoints** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |
| **labels** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 | 1 |  |  |  |
| **lightfield** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 9 | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |
| **matrix** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 | 1 |  | 4 |  |  |  |  |
| **measurement** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |
| **mesh** |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  | 3 |  | 1 |  |  |  |  |  | 1 |  |  | 2 |  |  | 2 |  |  |  |  |  |  | 1 |  |  |  |  |  |  | 1 |  |  | 3 |  |  | 1 |  |
| **normalmap** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 7 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **normals** |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  | 1 |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **pairs** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **pointmap** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **points** |  |  | 1 |  | 1 |  |  |  |  |  | 1 | 2 | 1 | 10 |  | 6 | 1 |  |  | 1 |  |  | 4 |  | 3 |  | 1 | 5 |  | 1 | 25 | 3 |  | 4 | 1 |  |  |  |  | 23 | 2 | 27 |  |  |  |  |  |  | 2 |  | 4 |  |  | 2 |  |  | 3 |  |
| **polsweep** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |
| **poly_surface** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **pose** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 6 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **position** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |
| **primitive** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 6 |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **qimage** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **rgbimage** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |
| **rle_region** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  | 1 | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |
| **roots** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **rot_scale** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **score** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **sdf** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |
| **shift** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **signal** |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  | 2 |  |  |  |  |  | 7 |  |  |  | 8 |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  | 20 |  |  |  |  |
| **stokes** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |
| **sweep** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |
| **table** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |
| **vector** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  | 2 |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **video** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 5 |  |  |  |  |
| **voxel** | 2 |  |  |  |  |  |  |  |  |  | 1 |  |  | 1 | 2 |  |  |  | 2 |  | 1 |  | 1 | 1 |  |  | 1 | 3 |  |  | 6 | 1 |  |  | 1 |  | 5 |  |  |  | 12 | 4 |  |  | 2 |  | 2 |  | 3 | 2 | 1 |  |  | 5 |  |  |  |  |
| **zscan** |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
```
