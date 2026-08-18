# HALCON operator coverage (measured vs the real reference)

Source: `https://www.mvtec.com/doc/halcon/2605/en/` (version 2605).
Ground truth: **2313 operators across 30 top-level chapters** (218 TOC pages), mined by `halcon_scrape.py`.

**imgevolve maps to 709 / 2313 HALCON operators (30.7%)** via `Op.halcon`, from 735 registry ops.

One imgevolve op claims one nearest HALCON operator, so coverage counts
distinct real operators with an analogue. This number is grounded in the
scraped reference, not memory; grow it by adding operator families to the
registry (each new `Op.halcon` that names a real operator lifts coverage).

## Per-chapter coverage (ranked by gap)

| chapter | covered | total | gap |
|---|---|---|---|
| Graphics | 3 | 174 | 171 |
| Tuple | 0 | 165 | 165 |
| System | 0 | 141 | 141 |
| Classification | 0 | 99 | 99 |
| OCR | 0 | 96 | 96 |
| Legacy | 16 | 110 | 94 |
| Matching | 8 | 96 | 88 |
| Deep Learning | 3 | 88 | 85 |
| Calibration | 11 | 68 | 57 |
| 3D Matching | 3 | 59 | 56 |
| Tools | 54 | 108 | 54 |
| File | 0 | 53 | 53 |
| Inspection | 5 | 55 | 50 |
| 3D Reconstruction | 31 | 76 | 45 |
| XLD | 53 | 97 | 44 |
| Image | 72 | 110 | 38 |
| Develop | 0 | 37 | 37 |
| Filters | 161 | 196 | 35 |
| Control | 0 | 34 | 34 |
| Transformations | 89 | 118 | 29 |
| Identification | 1 | 27 | 26 |
| 3D Object Model | 26 | 51 | 25 |
| Image Source | 0 | 25 | 25 |
| Regions | 84 | 106 | 22 |
| 2D Metrology | 10 | 32 | 22 |
| Segmentation | 35 | 53 | 18 |
| Object | 1 | 16 | 15 |
| 1D Measuring | 6 | 20 | 14 |
| Matrix | 46 | 57 | 11 |
| Morphology | 37 | 44 | 7 |

## Build targets — biggest gaps first (sample uncovered operators)

- **Graphics** (3/174): add_scene_3d_camera, add_scene_3d_instance, add_scene_3d_label, add_scene_3d_light, attach_background_to_window, attach_drawing_object_to_window, clear_drawing_object, clear_scene_3d, clear_window, close_window, convert_coordinates_image_to_window, convert_coordinates_window_to_image
- **Tuple** (0/165): clear_handle, copy_dict, create_dict, dict_to_json, get_dict_object, get_dict_param, get_dict_tuple, get_handle_object, get_handle_param, get_handle_tuple, handle_to_integer, integer_to_handle
- **System** (0/141): activate_compute_device, broadcast_condition, clear_barrier, clear_condition, clear_event, clear_message, clear_message_queue, clear_mutex, clear_serial, clear_serialized_item, close_io_channel, close_io_device
- **Classification** (0/99): add_class_train_data_gmm, add_class_train_data_knn, add_class_train_data_mlp, add_class_train_data_svm, add_sample_class_gmm, add_sample_class_knn, add_sample_class_mlp, add_sample_class_svm, add_sample_class_train_data, classify_class_gmm, classify_class_knn, classify_class_mlp
- **OCR** (0/96): append_ocr_trainf, apply_deep_ocr, clear_lexicon, clear_ocr_class_cnn, clear_ocr_class_knn, clear_ocr_class_mlp, clear_ocr_class_svm, clear_text_model, clear_text_result, concat_ocr_trainf, create_deep_ocr, create_lexicon
- **Legacy** (16/110): approx_chain, approx_chain_simple, clear_component_model, clear_rectangle, clear_training_components, close_ocr, cluster_model_components, copy_metrology_object, create_component_model, create_ocr_class_box, create_text_model, create_trained_component_model
- **Matching** (8/96): adapt_shape_model_high_noise, apply_deep_counting_model, clear_deformable_model, clear_descriptor_model, clear_ncc_model, clear_shape_model, create_aniso_shape_model_xld, create_calib_descriptor_model, create_deep_counting_model, create_local_deformable_model, create_local_deformable_model_xld, create_planar_calib_deformable_model
- **Deep Learning** (3/88): add_dl_pruning_batch, apply_dl_model, clear_dl_model, create_dl_layer_activation, create_dl_layer_affine_grid, create_dl_layer_anchors, create_dl_layer_batch_normalization, create_dl_layer_box_proposals, create_dl_layer_box_targets, create_dl_layer_class_id_conversion, create_dl_layer_concat, create_dl_layer_convolution
- **Calibration** (11/68): binocular_calibration, calibrate_cameras, calibrate_hand_eye, caltab_points, camera_calibration, clear_calib_data, clear_camera_setup_model, contour_to_world_plane_xld, create_calib_data, create_caltab, create_camera_setup_model, deserialize_calib_data
- **3D Matching** (3/59): add_deformable_surface_model_reference_point, add_deformable_surface_model_sample, apply_deep_matching_3d, apply_dl_model, clear_deformable_surface_matching_result, clear_deformable_surface_model, clear_shape_model_3d, clear_surface_matching_result, clear_surface_model, create_cam_pose_look_at_point, create_deep_matching_3d, create_deformable_surface_model
- **Tools** (54/108): adjust_mosaic_images, apply_distance_transform_xld, bundle_adjust_mosaic, clear_distance_transform_xld, clear_scattered_data_interpolator, close_bg_esti, connect_grid_points, create_bg_esti, create_distance_transform_xld, create_funct_1d_array, create_funct_1d_pairs, create_rectification_grid
- **File** (0/53): close_file, copy_file, delete_file, deserialize_handle, deserialize_image, deserialize_object, deserialize_region, deserialize_tuple, deserialize_xld, file_exists, fnew_line, fread_bytes

## Version awareness (HALCON's op set changes between releases)
Operator counts per scraped release: v12=2147, v13=2176, v2311=2381, v2411=2387, v2505=2411, v2605=2313 (union 2466). Coverage above is vs the primary scrape; the classification below is honest about which claimed `Op.halcon` names are stable vs release-specific.

- **673** claimed names exist in **all** scraped releases (stable).
- **36 version-drift** (real, but only some releases): `add_image_border` (in 2311/2411/2505/2605); `area_intersection_rectangle2` (in 2311/2411/2505/2605); `bilateral_filter` (in 13/2311/2411/2505/2605); `create_generic_shape_model` (in 2311/2411/2505/2605); `crop_rectangle2` (in 2311/2411/2505/2605); `decode_structured_light_pattern` (in 2311/2411/2505/2605); `distance_cc_min_points` (in 2311/2411/2505/2605); `distance_point_line` (in 2311/2411/2505/2605); `distance_point_pluecker_line` (in 2311/2411/2505/2605); `dual_quat_compose` (in 13/2311/2411/2505/2605); `dual_quat_conjugate` (in 13/2311/2411/2505/2605); `dual_quat_interpolate` (in 13/2311/2411/2505/2605); `dual_quat_normalize` (in 13/2311/2411/2505/2605); `dual_quat_to_hom_mat3d` (in 13/2311/2411/2505/2605); `dual_quat_to_pose` (in 13/2311/2411/2505/2605); `dual_quat_to_screw` (in 13/2311/2411/2505/2605); `dual_quat_trans_point_3d` (in 2311/2411/2505/2605); `edges_object_model_3d` (in 13/2311/2411/2505/2605); `equ_histo_image_rect` (in 2311/2411/2505/2605); `gen_savitzky_golay_filter` (in 2605); `gen_structured_light_pattern` (in 2311/2411/2505/2605); `guided_filter` (in 13/2311/2411/2505/2605); `height_width_ratio` (in 2311/2411/2505/2605); `height_width_ratio_xld` (in 2311/2411/2505/2605); `interleave_channels` (in 13/2311/2411/2505/2605); `mean_image_shape` (in 2311/2411/2505/2605); `pluecker_line_to_point_direction` (in 2311/2411/2505/2605); `pluecker_line_to_points` (in 2311/2411/2505/2605); `point_direction_to_pluecker_line` (in 2311/2411/2505/2605); `points_to_pluecker_line` (in 2311/2411/2505/2605); `pose_to_dual_quat` (in 13/2311/2411/2505/2605); `rectangularity_xld` (in 2311/2411/2505/2605); `screw_to_dual_quat` (in 13/2311/2411/2505/2605); `segment_image_mser` (in 13/2311/2411/2505/2605); `test_region_points` (in 2411/2505/2605); `uncalibrated_photometric_stereo` (in 2311/2411/2505/2605)
- **0** claimed names exist in **no** scraped release — genuine bad names / library-specific / voxel-3D, not version drift.

## Honest reading
- HALCON's ~2313 operators include large non-algorithmic chapters (Graphics / Tuple / System / File / Develop / Control) an algorithm-design engine does not target; real algorithmic headroom is smaller than the raw gap.
- Many operators are parametric variants of one family (collapse to fewer).
- Coverage counts a *nearest analogue*, not signature-level parity; per-operator typed stubs (`data/halcon_stubs.json`, with real Python signatures from the `mvtec-halcon` binding when available) track what is named vs implemented.
