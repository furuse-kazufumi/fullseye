# 型変換の行列 ―― 穴と不具合の点検

`py -3.11 tools/conversion_matrix.py --md docs/CONVERSION_MATRIX.md` の生成物。
手で編集しない。

```
型 95 / 変換ペア 387 / 変換を行う op のべ 2172
生成器のある型 68 / 出力型に述語のある型 94

■ 袋小路 (4) ― 産めるのに、そこから他の型へ出られない
   frame            ← 1 型から来る
   gradient         ← 1 型から来る
   graph            ← 1 型から来る
   hessian          ← 1 型から来る

■ 孤児 (0) ― 生成器も無く、どの op も産まない

■ 構造的に到達不能 (0) ― 不動点で閉じても届かない

■ 専用ビルダで到達している op (341) ― 型プールだけでは届かない
   acoustic_interface_coefficients
   adg_build
   adg_execute
   aim_velocity
   axes_frame
   azimuthal_integrate
   ball_track
   ball_truth
   bekker_pressure
   bekker_wheel_sinkage
   beta_from_mor
   beverloo_rate
   bounce
   boussinesq_surface_displacement
   bus_departure_yield_check
   camera_rig
   carla_label_map
   carla_label_unmap
   carla_scene_check
   carla_scene_render
   carla_scene_world
   catch_success_rate
   cerruti_surface_displacement
   chamfer_capture
   check_sequence_score
   class_2dim_sup
   coat_image
   coat_thickness_from_image
   coherent_image
   color_bar
   combined_modulus
   compare_frame
   cone_profile_px
   contact_candidates
   contact_state_from_wrench
   contact_state_predict
   course_distance
   course_layout
   cr_collision
   cr_drive
   cr_drive_sweep
   cr_feasible
   cr_route
   crossing_stop_check
   crosswalk_overtake_check
   crosswalk_stopped_vehicle_check
   cut_depth_from_side
   datum_tilt_check
   debye_ring_image
   decimate_qem
   detector_calibrate
   detector_two_theta
   diabolo_axis_from_image
   diabolo_dynamics_step
   diabolo_marker_phase
   diabolo_simulate
   diabolo_throw_catch_truth
   diabolo_track
   displace_markers
   drag_coefficient_sphere
   echo_phase_polarity
   ellipse_pressure_shifted
   emva_exposure_for_snr
   emva_photon_exposure
   env_render
   expand_gray
   fbm_height
   fem_vs_halfspace
   fit_aero
   fit_bounce
   fit_spin
   fivebar_reach_interval
   fivebar_workspace
   flight_fit
   flight_ode
   flight_simulate
   flight_state_at
   fly_emd_response
   fly_expansion_readout
   fly_lgmd_eta
   fly_tau_from_expansion
   food_cut_width
   force_from_wrist_displacement
   gmsd_map
   graph_core_persistence
   graph_edge_consensus
   grid_distances
   grid_lines
   gs_from_world
   gs_render
   gs_update
   gum_expanded
   gum_monte_carlo
   gum_propagate
   gum_standard_uncertainty
   gum_validate
   heap_mass
   heap_volume_heightmap
   hertz_force
   hertz_pressure
   hertz_pressure_shifted
   hertz_surface_ur
   hertz_surface_uz
   hill_hold_brake_min
   humanoid_clip_mesh
   humanoid_impostors
   insertion_episode_summary
   insertion_failure_classify
   insertion_failure_presets
   insertion_failure_validate
   insertion_grid_summary
   insertion_signature
   integrate
   interp_cubic
   interp_linear
   intersect_planes
   intrinsics_to_carla
   intrinsics_to_fullseye
   jamming_diagram
   jamming_force_check
   jamming_parallelogram_planar
   japan_stats
   japan_world
   jones_apply
   ken_mesh
   ken_truth
   kendama_catch_check
   kendama_clearance
   kendama_combo_simulate
   kendama_pose
   kendama_rig
   kendama_simulate
   kendama_world
   knife_load_from_pads
   label_points
   lane_change_permitted
   large_deformation_contact
   large_deformation_inverse
   largedef_c1_coefficient
   largedef_correction
   largedef_radius_ratio
   largedef_universal_correction
   lattice_moire_peak
   leader_line
   legend_box
   lidar_scan
   magnus_lift_coefficient
   mat_solve
   matmul_ozaki
   matmul_reproducible
   mdr_spring_bed
   membrane_delta_from_normals
   membrane_indent_sphere
   membrane_render_markers
   membrane_shear_field
   mesh_displace_fbm
   mesh_displace_spectrum
   mesh_isotropic_remesh
   mesh_scatter_boulders
   mesh_split_long_edges
   mesh_subdivide
   mindlin_fit
   mindlin_fit_vector
   mindlin_model
   mindlin_partial_slip
   mindlin_traction
   mor_from_beta
   msa_anova_table
   msa_attribute_agreement
   msa_bias_linearity
   msa_gauge_rr
   mueller_apply
   naive_execute
   no_overtaking_zones
   no_stopping_zones
   obstacle_fit_doublet
   osm_road_graph
   osm_road_loops
   osm_road_mask
   osm_route
   overlay_labels
   overtake_permitted
   overtaken_conduct_check
   ozaki_error_bound
   pad_context
   pad_loads_to_peg_wrench
   pad_marker_displacement
   pad_tactile_frame
   pad_tactile_read
   panel_grid
   particle_size_dx
   particle_size_oversize
   particle_step
   path_slip_risk
   peg_measure_overlay
   peg_synthetic_rgbd
   peg_wrench_to_pad_loads
   perpetual_step
   phase_congruency_pc
   phase_fractions
   phase_peel
   plan_conflicts
   plane_topview
   plot_series
   pod_ahat_fit
   pod_decision_tradeoff
   pod_from_ahat
   pod_hitmiss_fit
   powder_reflections
   predict_amber_onset
   predict_fringe_phase_error
   preston_track_profile
   priority_rule
   puck_camera
   puck_mirror_path
   puck_pinhole_camera
   puck_pixel_to_world
   puck_restitution_from_wall
   puck_slide_predict
   puck_state_at
   puck_stop_distance
   puck_synth_frames
   puck_track
   puck_velocity_estimate
   puck_world_to_pixel
   pulse_echo_ascan
   punch_pressure
   punch_surface_uz
   racket_hit_check
   racket_impact
   racket_plan
   rally_simulate
   relative_motion
   removal_depth_from_heights
   render_through_lens
   render_transport
   reproject
   risk_aware_path
   road_profile
   roll_slide_state
   roundabout_entry_check
   rounded_rect
   rss_lateral_check
   rss_longitudinal_check
   rss_worst_case_gap
   rss_worst_case_gap_lateral
   rss_worst_case_gap_opposite
   sam_cscan
   sam_frequency_tradeoff
   scale_bar
   scene_pair_table
   scherrer_size
   seg_synapse_nri
   seg_synapse_partners
   seg_wiring_exposure
   seg_wiring_variation
   sfp_dolp_model
   shot_is_legal
   sight_stop_speed
   simcal_observe
   simcal_uncertainty
   skill_test_score
   slice_push_from_track
   slice_push_ratio
   slip_cvar
   slip_predict
   slope_slip_curve
   sph_kernel
   spheroid_closest
   spoon_tilt_critical
   stagnation_from_centerline
   stall_verdict
   stopping_distance_grade
   strategy_attacker
   strategy_feeder
   stream_areal_density
   striker_plan
   string_tension_static
   surface_divergence_closed_form
   swing_up_apex
   symmetry_fold
   table_world
   terrain_height
   terrain_mesh
   text_box
   text_lines
   ticks
   tid2013_by_distortion
   tile_mesh
   tile_roads
   tile_stream
   tilt_shear_field
   tip_force_ratios
   to_points
   tof_transport_depth
   torsion_partial_slip
   torsion_stick_field
   town_checks
   town_crossing_state
   town_run
   town_stop_lines
   town_world
   track_triangulate
   transport_matrix_radiosity
   tree_morphometry
   tree_run_length
   tree_sholl
   turn_maneuver_check
   two_point_forces
   unexplained_peaks
   vda5050_check
   vda5050_order
   veil_chroma_limit
   velocity_deficit_map
   vision_boundary_flip
   vx_magnitude
   vx_nonlinear_filter
   vx_nonmax_suppression
   vx_phase
   vx_remap
   vx_table_lookup
   vx_warp_affine
   vx_warp_perspective
   watermark_embed
   watersheds_marker
   wavefront_stats
   wedging_check
   wedging_risk
   wheel_forces
   wheel_sinkage
   wheel_traction_curve
   whitney_clearance
   whitney_wrench
   world_apply_terrain
   world_build
   world_camera
   world_camera_impostors
   world_materials
   wrist_load_from_deflection
   yield_maneuver_check
   zoom_inset

■ 誰も食べない型 (4) ― 出力専用。終端なら正しい
   frame, gradient, graph, hessian

■ 出力型に述語が無い変換 op (0) ― 何を返しても TYPEMISS にならない
   対象の型: 

■ 片道の変換 (199) ― A→B はあるが B→A が無い(戻せないのが正しい場合も多い)
   any              → pose              register_cross, register_cross
   any              → rgb               cutting_edge_render
   any              → voxel             fuse_to_voxel
   axes             → image2d           axes_frame, grid_lines, ticks
   axes             → pairs             data_to_pixel
   beatcube         → image2d           range_doppler_map
   beatcube         → signal            fmcw_range_profile, beamform_delay_sum
   beatcube         → table             beamform_doa
   bspline_surface  → measurement       surface_residual
   calresult        → table             simcal_report
   cimage           → jones             jones_apply
   cimage           → mask              mandelbrot_interior
   cimage           → measurement       cplx_cr_residual
   cimage           → rgbimage          cplx_domain_colour
   conn_graph       → image2d           graph_adjacency_image
   conn_graph       → matrix            reservoir_states, reservoir_encode, graph_layer_propagate
   conn_graph       → measurement       graph_clustering_coefficient, graph_spectral_radius, graph_modularity
   conn_graph       → points            graph_layout_spectral
   conn_graph       → signal            graph_betweenness, graph_laplacian_spectrum
   conn_graph       → table             graph_degree_table, graph_edges_as_lines
   coordgrid        → sdf               sphere_sdf, box_sdf, plane_sdf
   counts           → measurement       dtof_depth
   counts           → table             tcspc_stats, lifetime_fit, lifetime_phasor
   cpoints          → cscalar           cplx_contour_integral, cplx_contour_integral, cplx_cauchy_value
   cpoints          → measurement       cplx_winding_number, cplx_argument_principle, cplx_argument_principle
   cpoints          → table             cplx_laurent_coeffs, cplx_laurent_coeffs
   curvature        → table             curvature_to_table
   depth            → labels            dem_flow_direction
   depth            → normalmap         normals_from_depth
   depth            → pairs             surface_psd
   depth            → pointmap          depth_to_organized_points, dem_geocentric_grid
   depth            → sdf               tsdf_from_depth, fuse, integrate
   depth            → signal            dem_geoid_height
   depth            → table             itof_capture, surface_params, dem_skyline
   descriptor       → measurement       shape_distance, shape_distance
   descriptor       → table             descriptor_to_table
   design           → table             rsm_fit, doe_main_effects, sens_morris
   efdmodel         → matrix            normalize
   efdmodel         → measurement       descriptor_distance, descriptor_distance
   entries          → image2d           legend_box
   fingerprint      → image2d           fingerprint_strength_map
   fingerprint      → table             fingerprint_correlate
   flow2d           → rgb               piv_flow_to_rgbimage, piv_quiver, piv_streamline_image
   flow2d           → table             piv_velocity_gradient, piv_streamlines, piv_error_stats
   flow_dense       → rgbimage          flow_to_rgbimage
   flow_scattered   → signal            flow_speed
   gaussians        → voxel             gaussians_to_voxel
   image2d          → labels2d          blob_seeds, blob_split, class_2dim_unsup
   image2d          → measurement       surface_form_error, edge_alias_energy, surface_residual
   image2d          → metrics           compare_images, compare_images, measure_with
   image2d          → pose              recover_pose, recover_pose
   image2d          → rgbvolume         polarization_demosaic_color
   images           → depth             decode_fringe
   images           → fingerprint       sensor_fingerprint
   images           → flow2d            piv_ensemble_correlate
   images           → indices           lucky_select
   images           → labels2d          regiongrowing_n
   images           → mask              class_ndim_norm
   images           → normalmap         photometric_stereo, photometric_stereo_robust
   jones            → stokes            stokes_from_jones
   keypoints        → measurement       reprojection_error
   keypoints        → pose              dlt_pose, pnp_ransac
   keypoints        → table             cad_pixel_to_surface, psf_fit, aperture_photometry
   lab              → image2d           delta_e_2000, delta_e_2000, delta_e_76
   labels           → image2d           overlay_labels
   labels           → measurement       graph_modularity
   labels           → rgbimage          vol_label_volume_render
   labels           → rgbvolume         vol_colorize_labels, vol_label_overlay
   labels           → table             vol_region_props, cad_defect_to_cad, vol_label_shape_stats
   labels           → vector            illuminant_from_dichromatic_planes
   labels2d         → rgb               blob_overlay
   labels2d         → table             sam_cscan, label_extent, blob_features
   lightfield       → images            lf_views, lf_focal_stack
   lightfield       → table             lf_stats
   lut              → image2d           color_bar
   lut              → rgb               color_grade
   matrix           → mask              wave_nodal_lines
   matrix           → measurement       mat_cond, fly_hs_readout, states_participation_ratio
   matrix           → rgb               peg_measure_overlay, peg_measure_overlay, membrane_render_rgb
   matrix           → rgbimage          pixel_shift_merge
   matrix           → rgbvideo          points_activity_video
   matrix           → stokes            mueller_apply
   matrix           → transport_plan    sinkhorn
   matrix           → video             pixel_shift_capture
   measurehandle    → table             measure_pos, measure_pairs, fuzzy_measure_pairing
   mesh             → curvature         vertex_curvature
   mesh             → image2d           ambient_occlusion, cast_shadow, supersample_mesh
   mesh             → indices           boundary_vertices, cad_visible_faces
   mesh             → matrix            displacement_band_weights
   mesh             → measurement       mesh_area, mesh_volume
   mesh             → normals           face_normals, vertex_normals
   mesh             → rgbimage          render_beauty, render_regolith
   mesh             → signal            terrain_region_mask, mesh_edge_lengths, geodesic_mesh
   mesh             → table             mesh_edge_stats, mesh_detail_map, mesh_lod_chain
   metrics          → table             metrics_table
   metrologymodel   → scalar            add_metrology_object_line_measure, add_metrology_object_circle_measure, add_metrology_object_rectangle2_measure
   metrologymodel   → table             apply_metrology_model
   normalmap        → polsweep          sfp_render
   normalmap        → rgbimage          grating_rgb, thin_film_rgb, finish_shade
   normalmap        → scalar            membrane_delta_from_normals
   normals          → descriptor        compute_fpfh, shot_descriptor
   normals          → image2d           normals_to_egi
   normals          → measurement       normal_consistency
   normals          → pose              icp_point2plane
   normals          → primitive         ransac_cylinder
   pairs            → images            morph_sequence, morph_sequence
   pairs            → measurement       optimal_snr, mtf50, spectral_integral
   phash            → measurement       hash_distance, hash_distance
   phash            → table             watermark_capacity
   pointmap         → normalmap         bump_normals_fbm
   points           → any               social_force_step, social_force_step, social_force_step
   points           → axes              moment_axes
   points           → curvature         principal_curvatures
   points           → descriptor        compute_fpfh, shot_descriptor, d2_distribution
   points           → frame             frenet_frame
   points           → graph             knn_graph
   points           → labels            region_growing, euclidean_cluster, plane_segmentation
   points           → matrix            inertia_tensor, reproject, cross_covariance_reproducible
   points           → measurement       angle_3points, distance_point_plane, distance_point_line
   points           → normals           estimate_point_normals, estimate_normals, estimate_oriented_normals
   points           → pairs             curvature_torsion
   points           → pose              match_pca, match_pca, icp_point2point_3d
   points           → primitive         line_from_2points, plane_from_3points, fit_line_3d
   points           → rgbvideo          points_activity_video
   points           → scalar            mesh_signed_volume
   polsweep         → stokes            polarization_stokes
   polsweep         → table             sfp_normals
   pose             → measurement       mean_reprojection_error, mean_edge_error, rotation_translation_error
   pose             → table             pose_error, pose_error, bundle_adjust
   position         → table             refine_lm
   positions        → table             point_spectrum
   primitive        → measurement       angle_between_lines, angle_between_planes, angle_line_plane
   primitive        → position          intersect_line_plane
   rgb              → lab               xyz_to_lab
   rgbimage         → rgb               rgb_to_xyz
   rgbimage         → scalar            fsimc, fsimc
   rgbimage         → vector            illuminant_from_dichromatic_planes
   rgbvideo         → table             perpetual_loop_seam
   rgbvideo         → text              video_write_gif
   rgbvolume        → rgbimage          vol_label_slice_rgb, vol_label_mpr_rgb
   rle_region       → measurement       vol_rle_volume
   rle_region       → position          vol_rle_centroid
   rle_region       → primitive         vol_rle_bbox
   roots            → cimage            cplx_rational_field, cplx_rational_field
   scalar           → rgb               membrane_render_markers, membrane_render_markers, spheres_render_shaded
   score            → image2d           score_to_image2d
   score            → position          refine_peak_newton, score_to_position
   sdf              → points            extract_surface_points
   sdf              → signal            query_distance
   shapemodel       → measurement       shape_mahalanobis
   shapemodel       → points            shape_reconstruct, shape_synthesize
   shapemodel       → signal            shape_project, shape_explained_variance
   shapeset         → points            shape_mean
   shapeset         → shapemodel        shape_pca
   signal           → cpoints           cplx_poly_eval
   signal           → labels2d          cplx_newton_basins, classify_image_class_lut
   signal           → measurement       distance_funct_1d, distance_funct_1d, num_points_funct_1d
   signal           → roots             poly_roots
   signal           → vector            spectrum_to_srgb
   simmodel         → calresult         simcal_fit, simcal_validate
   simmodel         → table             simcal_screen
   sinogram         → measurement       sinogram_center_of_rotation
   stokes           → table             stokes_analyze
   sweep            → measurement       csi_peak_position, chromatic_confocal_height
   sweep            → signal            csi_envelope
   synapse_table    → conn_graph        graph_from_synapses
   text             → image2d           annotate3d_label, symmetric_peg_shape, text_box
   transport_plan   → scalar            transport_cost
   vector           → image2d           cast_shadow, shadow_raycast, raw_apply_gains
   vector           → normals           reflect, refract
   vector           → points            sample_surface
   vector           → pose              carve_look_at
   video            → image2d           pixel_shift_motion_mask, temporal_band_power, video_cube_cut
   video            → indices           video_summary_keyframes
   video            → pairs             displacement_series, riesz_displacement_series
   video            → rgbvideo          video_cube_orbit
   video            → table             band_snr, motion_magnify, phase_displacement
   video            → voxel             video_spacetime_cube
   volseq           → rgb               volseq_pathline_render
   volseq           → rgbvideo          volseq_pathline_orbit, volseq_render_orbit, focus_sweep_surface_video
   volseq           → video             volseq_mip_video, volseq_cut_video, focus_sweep_height_video
   volume           → table             emva_spatial_nonuniformity, emva_spatial_nonuniformity, emva_general_nonuniformity
   voxel            → angle             refine_rotation_z, refine_rotation_z
   voxel            → curvature         curvature_maps
   voxel            → descriptor        sh_descriptor
   voxel            → gradient          sobel3d, gradient3d
   voxel            → hessian           hessian3d
   voxel            → keypoints         harris3d_keypoints
   voxel            → labels            label_components, vol_label, vol_watershed
   voxel            → pairs             vol_profile_line
   voxel            → position          match_shape_3d, match_shape_3d, match_chamfer_3d
   voxel            → primitive         vol_bounding_box, hough_plane_3d, hough_sphere_3d
   voxel            → rgb               vol_render_transfer
   voxel            → rgbvolume         vol_label_overlay
   voxel            → rot_scale         match_logpolar_z, match_logpolar_z
   voxel            → score             correlation_score, correlation_score
   voxel            → shift             match_phase_3d, match_phase_3d
   voxel            → signal            vol_wall_thickness
   zscan            → image2d           csi_contrast_map

■ 行列(セル = その変換を行う op の数)
| from \ to | angle | any | attnmap | axes | beatcube | bspline_curve | bspline_surface | calresult | cimage | conn_graph | coordgrid | countrate | counts | cpoints | cscalar | curvature | deformation | depth | descriptor | design | efdmodel | entries | fingerprint | flow2d | flow_dense | flow_scattered | frame | gaussians | gradient | graph | hessian | histcube | image2d | images | indices | jones | keypoints | lab | labels | labels2d | lightfield | lut | mask | matrix | measurehandle | measurement | mesh | metrics | metrologymodel | normalmap | normals | pairs | phash | pointmap | points | polsweep | poly_surface | pose | position | positions | primitive | qimage | rgb | rgba | rgba_premul | rgbimage | rgbvideo | rgbvolume | rle_region | roots | rot_scale | scalar | score | sdf | shapemodel | shapeset | shift | signal | simmodel | sinogram | sinostack | sprites | stokes | sweep | synapse_table | table | text | tokens | transport_plan | vector | video | volseq | volume | voxel | zscan |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **angle** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **any** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  | 1 |  |  |  |  |  |  |  |  | 9 |  |  |  |  |  | 5 |  |  |  |  |  |  |  | 84 |  |  |  |  |  |  |  | 1 |  |
| **attnmap** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |
| **axes** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **beatcube** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **bspline_curve** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **bspline_surface** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **calresult** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **cimage** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 6 |  |  | 1 |  |  |  |  |  |  | 1 |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **conn_graph** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  | 1 |  |  |  |  | 4 |  | 5 |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |
| **coordgrid** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 6 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **countrate** |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **counts** |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  |  |  |  |
| **cpoints** |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |
| **cscalar** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **curvature** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **deformation** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **depth** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 | 15 |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  | 1 |  | 1 |  | 2 | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  | 1 |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  |  |  | 1 |
| **descriptor** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **design** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 4 |  |  |  |  |  |  |  |  |  |
| **efdmodel** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  | 2 |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **entries** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **fingerprint** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **flow2d** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 8 |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 5 |  |  |  |  |  |  |  |  |  |
| **flow_dense** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |
| **flow_scattered** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **frame** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **gaussians** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |
| **gradient** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **graph** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **hessian** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **histcube** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **image2d** |  | 5 |  |  |  |  | 3 |  | 3 |  |  |  |  |  |  |  |  | 5 |  |  |  |  |  | 6 |  |  |  |  |  |  |  |  |  | 5 |  |  | 3 |  |  | 6 | 1 |  | 5 | 9 |  | 8 |  | 4 |  | 5 |  | 4 | 2 |  | 3 | 3 | 3 | 2 |  |  |  | 2 | 3 |  |  | 1 |  | 1 |  |  |  | 28 |  |  |  |  |  | 4 |  | 1 |  |  |  |  |  | 134 |  |  |  |  |  |  |  | 1 |  |
| **images** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  | 1 | 1 |  |  |  |  |  |  |  |  | 7 |  | 1 |  |  |  |  | 1 |  |  | 1 |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  | 5 |  |  |  |  |  |  |  | 2 |  |
| **indices** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **jones** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |
| **keypoints** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  | 1 |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 5 |  |  |  |  |  |  |  |  |  |
| **lab** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **labels** |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  | 1 |  |  |  |  |  |  |  |  | 1 |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 7 |  |  |  | 1 |  |  |  |  |  |
| **labels2d** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 37 |  |  |  |  |  |  |  |  |  |
| **lightfield** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 9 | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **lut** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **mask** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  | 5 |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 9 |  |  |  |  |  |  |  |  |  |
| **matrix** | 1 | 7 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 | 1 |  |  |  |  |  |  |  |  |  |  |  |  | 13 |  |  |  |  |  | 1 |  |  |  | 1 |  |  | 3 |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  | 6 |  |  | 1 | 1 |  |  |  | 1 | 6 |  |  |  |  |  | 6 |  |  |  |  | 1 |  |  | 135 |  |  | 1 |  | 1 |  |  |  |  |
| **measurehandle** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  |  |  |  |
| **measurement** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  | 1 |  |
| **mesh** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 4 |  | 2 |  |  |  |  |  |  |  |  | 1 |  | 2 |  |  |  |  | 2 |  |  |  | 3 |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  | 4 |  |  |  |  |  |  |  | 14 | 1 |  |  |  |  |  |  | 2 |  |
| **metrics** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **metrologymodel** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 5 |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **normalmap** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 18 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  | 3 |  |  | 5 |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  |  |  |  |
| **normals** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  | 1 |  |  |  |  |  | 1 |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **pairs** |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 | 1 |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  | 11 | 2 |  |  |  |  |  |  |  |  |  | 1 |  | 7 |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 4 |  |  |  |  |  |  |  | 14 |  |  |  |  |  |  |  |  |  |
| **phash** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **pointmap** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **points** |  | 3 |  | 1 |  | 1 |  |  |  |  |  |  |  |  |  | 1 | 2 | 1 | 10 |  |  |  |  |  |  | 6 | 1 | 1 |  | 1 |  |  | 3 |  | 3 |  | 3 |  | 5 |  |  |  |  | 9 |  | 28 | 4 |  |  |  | 4 | 1 |  |  |  |  |  | 22 | 3 |  | 27 |  |  |  |  |  | 1 |  |  |  |  | 1 |  |  |  |  |  | 19 |  |  |  |  |  |  |  | 28 |  |  |  |  |  |  |  | 3 |  |
| **polsweep** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **poly_surface** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **pose** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 4 |  |  |  |  |  |  |  |  |  |
| **position** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **positions** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **primitive** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 7 |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **qimage** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **rgb** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 12 |  |  |  | 1 |  |  |  |  |  |
| **rgba** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **rgba_premul** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **rgbimage** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 | 1 |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  | 1 | 1 |  |  |  |  |
| **rgbvideo** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 | 1 |  |  |  |  |  |  |  |  |
| **rgbvolume** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **rle_region** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |
| **roots** |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **rot_scale** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **scalar** |  | 15 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 19 |  |  |  |  |  |  |  |  |  |  | 25 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 12 |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 12 |  |  |  |  |  |  |  | 268 |  |  |  |  |  |  |  |  |  |
| **score** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **sdf** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |
| **shapemodel** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **shapeset** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **shift** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |
| **signal** |  | 2 |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 6 |  | 2 |  |  |  |  | 2 |  |  |  | 7 |  | 12 |  |  |  |  |  | 13 |  |  | 3 |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  | 9 |  |  |  |  |  |  |  |  |  |  |  |  |  | 225 |  |  | 4 | 1 |  |  |  |  |  |
| **simmodel** |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **sinogram** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **sinostack** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |
| **sprites** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **stokes** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |
| **sweep** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **synapse_table** |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **table** |  | 34 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 20 | 1 |  |  |  |  |  |  |  |  | 1 | 10 |  | 4 |  |  |  | 3 |  | 10 |  |  | 2 |  |  |  |  |  |  |  | 6 | 2 |  | 8 |  |  |  |  |  | 21 |  |  |  |  |  | 12 |  |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  | 1 |  |
| **text** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 6 |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 14 |  |  |  |  |  |  |  |  |  |
| **tokens** |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **transport_plan** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **vector** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  | 1 |  |  | 1 |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **video** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 7 |  |  |  |  |  |  |  | 1 |  |
| **volseq** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  | 3 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 3 |  |  |  |  |
| **volume** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 4 |  |  |  |  |  |  |  |  |  |
| **voxel** | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  | 1 |  |  |  |  |  | 6 |  |  |  | 2 |  | 1 |  | 1 | 1 |  |  | 1 |  | 6 |  |  |  |  |  |  | 8 | 1 |  |  |  |  | 1 |  |  | 5 |  |  |  | 12 |  | 4 |  | 1 |  |  |  |  | 1 | 2 |  | 2 |  | 2 | 3 |  |  | 2 | 1 |  |  | 1 |  |  |  |  | 7 |  |  |  |  |  |  |  |  |  |
| **zscan** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
```
