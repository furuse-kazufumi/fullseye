# 3D operator help — 279 ops in 55 categories

自動生成(`tools/opdocs.py toc`)。フォルダ階層 `docs/ops/3d/<category>/<op>.md` を走査。

## カテゴリ

### augment (6)

[cutout](augment/cutout.md) · [elastic_deform](augment/elastic_deform.md) · [jitter](augment/jitter.md) · [random_dropout](augment/random_dropout.md) · [random_rotation](augment/random_rotation.md) · [random_scale](augment/random_scale.md)

### bounds (4)

[aabb](bounds/aabb.md) · [convex_hull](bounds/convex_hull.md) · [min_enclosing_sphere](bounds/min_enclosing_sphere.md) · [obb](bounds/obb.md)

### bundle_adjust (3)

[bundle_adjust](bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](bundle_adjust/mean_reprojection_error.md) · [project](bundle_adjust/project.md)

### curvature (5)

[estimate_normals](curvature/estimate_normals.md) · [gaussian_curvature](curvature/gaussian_curvature.md) · [mean_curvature](curvature/mean_curvature.md) · [principal_curvatures](curvature/principal_curvatures.md) · [shape_index](curvature/shape_index.md)

### curve (5)

[arc_length](curve/arc_length.md) · [curvature_torsion](curve/curvature_torsion.md) · [fit_spline_curve](curve/fit_spline_curve.md) · [frenet_frame](curve/frenet_frame.md) · [resample_uniform](curve/resample_uniform.md)

### curvilinear (3)

[cylinder_unwrap](curvilinear/cylinder_unwrap.md) · [fit_zernike](curvilinear/fit_zernike.md) · [polar_unwrap](curvilinear/polar_unwrap.md)

### deform (4)

[register_cpd_rigid](deform/register_cpd_rigid.md) · [register_nonrigid](deform/register_nonrigid.md) · [tps_fit](deform/tps_fit.md) · [tps_warp](deform/tps_warp.md)

### depth_denoise (3)

[bilateral_filter_depth](depth_denoise/bilateral_filter_depth.md) · [fill_holes](depth_denoise/fill_holes.md) · [joint_bilateral](depth_denoise/joint_bilateral.md)

### describe (2)

[match_sh_descriptor](describe/match_sh_descriptor.md) · [sh_descriptor](describe/sh_descriptor.md)

### detect (2)

[hough_plane_3d](detect/hough_plane_3d.md) · [hough_sphere_3d](detect/hough_sphere_3d.md)

### edges (5)

[canny3d](edges/canny3d.md) · [edge_points](edges/edge_points.md) · [gradient3d](edges/gradient3d.md) · [link_edges](edges/link_edges.md) · [log_zero_crossings](edges/log_zero_crossings.md)

### feature (9)

[curvature_maps](feature/curvature_maps.md) · [edt_jfa](feature/edt_jfa.md) · [hessian3d](feature/hessian3d.md) · [sobel3d](feature/sobel3d.md) · [vol_frangi](feature/vol_frangi.md) · [vol_gradient_magnitude](feature/vol_gradient_magnitude.md) · [vol_hessian_blobness](feature/vol_hessian_blobness.md) · [vol_local_maxima](feature/vol_local_maxima.md) · [vol_sato](feature/vol_sato.md)

### feature_register (7)

[compute_fpfh](feature_register/compute_fpfh.md) · [harris3d_keypoints](feature_register/harris3d_keypoints.md) · [iss_keypoints](feature_register/iss_keypoints.md) · [register_fpfh](feature_register/register_fpfh.md) · [register_shot](feature_register/register_shot.md) · [register_spin](feature_register/register_spin.md) · [shot_descriptor](feature_register/shot_descriptor.md)

### freeform (5)

[eval_bspline_curve](freeform/eval_bspline_curve.md) · [eval_bspline_surface](freeform/eval_bspline_surface.md) · [fit_bspline_curve](freeform/fit_bspline_curve.md) · [fit_bspline_surface](freeform/fit_bspline_surface.md) · [surface_residual](freeform/surface_residual.md)

### fusion (2)

[fuse_to_voxel](fusion/fuse_to_voxel.md) · [register_cross](fusion/register_cross.md)

### geodesic (4)

[farthest_point_sampling](geodesic/farthest_point_sampling.md) · [geodesic_distances](geodesic/geodesic_distances.md) · [geodesic_mesh](geodesic/geodesic_mesh.md) · [knn_graph](geodesic/knn_graph.md)

### geometry (23)

[angle_3points](geometry/angle_3points.md) · [angle_between_lines](geometry/angle_between_lines.md) · [angle_between_planes](geometry/angle_between_planes.md) · [angle_line_plane](geometry/angle_line_plane.md) · [distance_line_line](geometry/distance_line_line.md) · [distance_point_line](geometry/distance_point_line.md) · [distance_point_plane](geometry/distance_point_plane.md) · [fit_box3](geometry/fit_box3.md) · [fit_circle3](geometry/fit_circle3.md) · [fit_circle_3d](geometry/fit_circle_3d.md) · [fit_line3](geometry/fit_line3.md) · [fit_line_3d](geometry/fit_line_3d.md) · [fit_plane3](geometry/fit_plane3.md) · [fit_plane_3d](geometry/fit_plane_3d.md) · [fit_sphere3](geometry/fit_sphere3.md) · [fit_sphere_3d](geometry/fit_sphere_3d.md) · [intersect_line_plane](geometry/intersect_line_plane.md) · [intersect_planes](geometry/intersect_planes.md) · [line_from_2points](geometry/line_from_2points.md) · [plane_from_3points](geometry/plane_from_3points.md) · [smallest_box3](geometry/smallest_box3.md) · [smallest_box3_axis](geometry/smallest_box3_axis.md) · [smallest_sphere3](geometry/smallest_sphere3.md)

### gicp (2)

[estimate_covariances](gicp/estimate_covariances.md) · [gicp](gicp/gicp.md)

### lidar_projection (3)

[project_cylindrical](lidar_projection/project_cylindrical.md) · [project_spherical](lidar_projection/project_spherical.md) · [unproject_spherical](lidar_projection/unproject_spherical.md)

### match_localize (6)

[match_chamfer_3d](match_localize/match_chamfer_3d.md) · [match_curvature_3d](match_localize/match_curvature_3d.md) · [match_hough_3d](match_localize/match_hough_3d.md) · [match_mip_2d](match_localize/match_mip_2d.md) · [match_points_ncc](match_localize/match_points_ncc.md) · [match_shape_3d](match_localize/match_shape_3d.md)

### match_pose (4)

[match_logpolar_z](match_pose/match_logpolar_z.md) · [match_pca](match_pose/match_pca.md) · [match_phase_3d](match_pose/match_phase_3d.md) · [moment_axes](match_pose/moment_axes.md)

### medial (10)

[distance_ridge](medial/distance_ridge.md) · [medial_axis_points](medial/medial_axis_points.md) · [medial_match](medial/medial_match.md) · [skeleton_branches3d](medial/skeleton_branches3d.md) · [skeleton_endpoints3d](medial/skeleton_endpoints3d.md) · [skeleton_junctions3d](medial/skeleton_junctions3d.md) · [skeleton_prune3d](medial/skeleton_prune3d.md) · [skeletonize_vol](medial/skeletonize_vol.md) · [topology_signature](medial/topology_signature.md) · [vol_distance_transform](medial/vol_distance_transform.md)

### mesh_process (7)

[decimate_qem](mesh_process/decimate_qem.md) · [face_normals](mesh_process/face_normals.md) · [laplacian_smooth](mesh_process/laplacian_smooth.md) · [mesh_area](mesh_process/mesh_area.md) · [taubin_smooth](mesh_process/taubin_smooth.md) · [vertex_curvature](mesh_process/vertex_curvature.md) · [vertex_normals](mesh_process/vertex_normals.md)

### metrics (7)

[chamfer_distance](metrics/chamfer_distance.md) · [fscore](metrics/fscore.md) · [hausdorff_distance](metrics/hausdorff_distance.md) · [normal_consistency](metrics/normal_consistency.md) · [pose_error](metrics/pose_error.md) · [rmse_correspondence](metrics/rmse_correspondence.md) · [voxel_iou](metrics/voxel_iou.md)

### moment_invariant (4)

[central_moments](moment_invariant/central_moments.md) · [inertia_tensor](moment_invariant/inertia_tensor.md) · [moment_invariants](moment_invariant/moment_invariants.md) · [principal_moments](moment_invariant/principal_moments.md)

### morphology (7)

[morph_blackhat3d](morphology/morph_blackhat3d.md) · [morph_close3d](morphology/morph_close3d.md) · [morph_dilate3d](morphology/morph_dilate3d.md) · [morph_erode3d](morphology/morph_erode3d.md) · [morph_gradient3d](morphology/morph_gradient3d.md) · [morph_open3d](morphology/morph_open3d.md) · [morph_tophat3d](morphology/morph_tophat3d.md)

### motion (1)

[scene_flow_lk](motion/scene_flow_lk.md)

### motion_segment (3)

[estimate_flow](motion_segment/estimate_flow.md) · [fit_rigid](motion_segment/fit_rigid.md) · [segment_rigid_motions](motion_segment/segment_rigid_motions.md)

### normals_orient (2)

[estimate_oriented_normals](normals_orient/estimate_oriented_normals.md) · [orient_normals](normals_orient/orient_normals.md)

### occupancy (4)

[esdf](occupancy/esdf.md) · [inflate](occupancy/inflate.md) · [occupancy_grid](occupancy/occupancy_grid.md) · [query_distance](occupancy/query_distance.md)

### optics (5)

[fresnel_reflectance](optics/fresnel_reflectance.md) · [normal_from_reflection](optics/normal_from_reflection.md) · [reflect](optics/reflect.md) · [refract](optics/refract.md) · [snell_angle](optics/snell_angle.md)

### photometric (4)

[integrate_normals](photometric/integrate_normals.md) · [photometric_stereo](photometric/photometric_stereo.md) · [render_lambertian](photometric/render_lambertian.md) · [surface_normals](photometric/surface_normals.md)

### plane_sweep_stereo (2)

[plane_sweep_depth](plane_sweep_stereo/plane_sweep_depth.md) · [warp_by_plane](plane_sweep_stereo/warp_by_plane.md)

### pose_estimation (3)

[dlt_pose](pose_estimation/dlt_pose.md) · [pnp_ransac](pose_estimation/pnp_ransac.md) · [reprojection_error](pose_estimation/reprojection_error.md)

### pose_graph (3)

[mean_edge_error](pose_graph/mean_edge_error.md) · [optimize_pose_graph](pose_graph/optimize_pose_graph.md) · [relative_pose](pose_graph/relative_pose.md)

### preprocess (5)

[mls_smooth](preprocess/mls_smooth.md) · [radius_outlier_removal](preprocess/radius_outlier_removal.md) · [statistical_outlier_removal](preprocess/statistical_outlier_removal.md) · [volume_downsample](preprocess/volume_downsample.md) · [voxel_grid_downsample](preprocess/voxel_grid_downsample.md)

### range_image (4)

[bearing_angle_image](range_image/bearing_angle_image.md) · [depth_to_organized_points](range_image/depth_to_organized_points.md) · [normals_from_depth](range_image/normals_from_depth.md) · [occlusion_edges](range_image/occlusion_edges.md)

### reconstruct (4)

[alpha_shape_boundary](reconstruct/alpha_shape_boundary.md) · [alpha_shape_mesh](reconstruct/alpha_shape_mesh.md) · [estimate_alpha](reconstruct/estimate_alpha.md) · [poisson_lite](reconstruct/poisson_lite.md)

### refine (6)

[icp_point2plane](refine/icp_point2plane.md) · [icp_point2point_3d](refine/icp_point2point_3d.md) · [refine_lm](refine/refine_lm.md) · [refine_peak_newton](refine/refine_peak_newton.md) · [refine_rotation_z](refine/refine_rotation_z.md) · [refine_translation_lk](refine/refine_translation_lk.md)

### regionprops (7)

[filter_by_volume](regionprops/filter_by_volume.md) · [inner_box3](regionprops/inner_box3.md) · [label_components](regionprops/label_components.md) · [largest_component](regionprops/largest_component.md) · [region_props](regionprops/region_props.md) · [vol_label](regionprops/vol_label.md) · [vol_region_props](regionprops/vol_region_props.md)

### registration_metrics (4)

[inlier_ratio](registration_metrics/inlier_ratio.md) · [registration_recall](registration_metrics/registration_recall.md) · [rmse_inliers](registration_metrics/rmse_inliers.md) · [rotation_translation_error](registration_metrics/rotation_translation_error.md)

### render (14)

[ambient_occlusion](render/ambient_occlusion.md) · [antialias](render/antialias.md) · [cast_shadow](render/cast_shadow.md) · [edge_alias_energy](render/edge_alias_energy.md) · [matcap_shade](render/matcap_shade.md) · [phong_shade](render/phong_shade.md) · [project_points](render/project_points.md) · [render_beauty](render/render_beauty.md) · [render_point_depth](render/render_point_depth.md) · [render_shaded](render/render_shaded.md) · [render_volume_projection](render/render_volume_projection.md) · [supersample_mesh](render/supersample_mesh.md) · [tonemap_aces](render/tonemap_aces.md) · [tonemap_reinhard](render/tonemap_reinhard.md)

### robust_fit (7)

[fit_cone](robust_fit/fit_cone.md) · [fit_ellipsoid](robust_fit/fit_ellipsoid.md) · [fit_torus](robust_fit/fit_torus.md) · [ransac_cylinder](robust_fit/ransac_cylinder.md) · [ransac_line](robust_fit/ransac_line.md) · [ransac_plane](robust_fit/ransac_plane.md) · [ransac_sphere](robust_fit/ransac_sphere.md)

### scene_flow3d (3)

[nearest_neighbor_flow](scene_flow3d/nearest_neighbor_flow.md) · [rigid_flow](scene_flow3d/rigid_flow.md) · [smooth_flow](scene_flow3d/smooth_flow.md)

### sdf_csg (7)

[box_sdf](sdf_csg/box_sdf.md) · [sdf_intersect](sdf_csg/sdf_intersect.md) · [sdf_offset](sdf_csg/sdf_offset.md) · [sdf_smooth_union](sdf_csg/sdf_smooth_union.md) · [sdf_subtract](sdf_csg/sdf_subtract.md) · [sdf_union](sdf_csg/sdf_union.md) · [sphere_sdf](sdf_csg/sphere_sdf.md)

### segment (4)

[euclidean_cluster](segment/euclidean_cluster.md) · [plane_segmentation](segment/plane_segmentation.md) · [region_growing](segment/region_growing.md) · [vol_watershed](segment/vol_watershed.md)

### shape_descriptor (5)

[a3_distribution](shape_descriptor/a3_distribution.md) · [d2_distribution](shape_descriptor/d2_distribution.md) · [describe](shape_descriptor/describe.md) · [extent_signature](shape_descriptor/extent_signature.md) · [shape_distance](shape_descriptor/shape_distance.md)

### space_carving (3)

[carve](space_carving/carve.md) · [synthesize_silhouette](space_carving/synthesize_silhouette.md) · [visual_hull](space_carving/visual_hull.md)

### structured_light (5)

[decode_fringe](structured_light/decode_fringe.md) · [graycode_decode](structured_light/graycode_decode.md) · [synthesize_fringes](structured_light/synthesize_fringes.md) · [unwrap_phase_2d](structured_light/unwrap_phase_2d.md) · [wrapped_phase](structured_light/wrapped_phase.md)

### superquadric (4)

[fit_superquadric](superquadric/fit_superquadric.md) · [inside_outside](superquadric/inside_outside.md) · [sample_surface](superquadric/sample_surface.md) · [superquadric_residual](superquadric/superquadric_residual.md)

### surface_fit (4)

[background_flatten](surface_fit/background_flatten.md) · [eval_poly_surface](surface_fit/eval_poly_surface.md) · [fit_poly_surface](surface_fit/fit_poly_surface.md) · [surface_form_error](surface_fit/surface_form_error.md)

### symmetry (4)

[detect_reflection_symmetry](symmetry/detect_reflection_symmetry.md) · [detect_rotational_symmetry](symmetry/detect_rotational_symmetry.md) · [reflect_points](symmetry/reflect_points.md) · [reflection_symmetry_score](symmetry/reflection_symmetry_score.md)

### transform (12)

[depth_to_points](transform/depth_to_points.md) · [estimate_point_normals](transform/estimate_point_normals.md) · [gaussians_to_voxel](transform/gaussians_to_voxel.md) · [mesh_to_points](transform/mesh_to_points.md) · [mesh_to_voxel](transform/mesh_to_voxel.md) · [points_to_voxel](transform/points_to_voxel.md) · [sdf_to_occupancy](transform/sdf_to_occupancy.md) · [signed_distance_field](transform/signed_distance_field.md) · [to_points](transform/to_points.md) · [tsdf_from_depth](transform/tsdf_from_depth.md) · [voxel_to_mesh](transform/voxel_to_mesh.md) · [voxel_to_mips](transform/voxel_to_mips.md)

### tsdf_fusion (3)

[extract_surface_points](tsdf_fusion/extract_surface_points.md) · [fuse](tsdf_fusion/fuse.md) · [integrate](tsdf_fusion/integrate.md)

### two_view (5)

[essential_8point](two_view/essential_8point.md) · [fundamental_8point](two_view/fundamental_8point.md) · [recover_pose](two_view/recover_pose.md) · [sampson_distance](two_view/sampson_distance.md) · [triangulate](two_view/triangulate.md)

---
© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
