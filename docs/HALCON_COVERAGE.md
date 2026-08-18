# HALCON operator coverage (measured vs the real reference)

Source: `https://www.mvtec.com/doc/halcon/2605/en/` (version 2605).
Ground truth: **2313 operators across 30 top-level chapters** (218 TOC pages), mined by `halcon_scrape.py`.

**imgevolve maps to 973 / 2313 HALCON operators (42.1%)** via `Op.halcon`, from 735 registry ops.

One imgevolve op claims one nearest HALCON operator, so coverage counts
distinct real operators with an analogue. This number is grounded in the
scraped reference, not memory; grow it by adding operator families to the
registry (each new `Op.halcon` that names a real operator lifts coverage).

## Per-chapter coverage (ranked by gap)

| chapter | covered | total | gap |
|---|---|---|---|
| Graphics | 9 | 174 | 165 |
| Tuple | 0 | 165 | 165 |
| System | 0 | 141 | 141 |
| Classification | 0 | 99 | 99 |
| OCR | 0 | 96 | 96 |
| Legacy | 16 | 110 | 94 |
| Deep Learning | 4 | 88 | 84 |
| Matching | 36 | 96 | 60 |
| File | 0 | 53 | 53 |
| 3D Matching | 15 | 59 | 44 |
| Inspection | 12 | 55 | 43 |
| Develop | 0 | 37 | 37 |
| Calibration | 32 | 68 | 36 |
| Control | 0 | 34 | 34 |
| 3D Reconstruction | 50 | 76 | 26 |
| Identification | 1 | 27 | 26 |
| Image Source | 0 | 25 | 25 |
| Image | 88 | 110 | 22 |
| 2D Metrology | 10 | 32 | 22 |
| Tools | 90 | 108 | 18 |
| Object | 1 | 16 | 15 |
| Transformations | 104 | 118 | 14 |
| 3D Object Model | 39 | 51 | 12 |
| Filters | 185 | 196 | 11 |
| Matrix | 46 | 57 | 11 |
| XLD | 88 | 97 | 9 |
| 1D Measuring | 11 | 20 | 9 |
| Segmentation | 47 | 53 | 6 |
| Morphology | 42 | 44 | 2 |
| Regions | 105 | 106 | 1 |

## Build targets — biggest gaps first (sample uncovered operators)

- **Graphics** (9/174): add_scene_3d_camera, add_scene_3d_instance, add_scene_3d_label, add_scene_3d_light, attach_background_to_window, attach_drawing_object_to_window, clear_drawing_object, clear_scene_3d, clear_window, close_window, convert_coordinates_image_to_window, convert_coordinates_window_to_image
- **Tuple** (0/165): clear_handle, copy_dict, create_dict, dict_to_json, get_dict_object, get_dict_param, get_dict_tuple, get_handle_object, get_handle_param, get_handle_tuple, handle_to_integer, integer_to_handle
- **System** (0/141): activate_compute_device, broadcast_condition, clear_barrier, clear_condition, clear_event, clear_message, clear_message_queue, clear_mutex, clear_serial, clear_serialized_item, close_io_channel, close_io_device
- **Classification** (0/99): add_class_train_data_gmm, add_class_train_data_knn, add_class_train_data_mlp, add_class_train_data_svm, add_sample_class_gmm, add_sample_class_knn, add_sample_class_mlp, add_sample_class_svm, add_sample_class_train_data, classify_class_gmm, classify_class_knn, classify_class_mlp
- **OCR** (0/96): append_ocr_trainf, apply_deep_ocr, clear_lexicon, clear_ocr_class_cnn, clear_ocr_class_knn, clear_ocr_class_mlp, clear_ocr_class_svm, clear_text_model, clear_text_result, concat_ocr_trainf, create_deep_ocr, create_lexicon
- **Legacy** (16/110): approx_chain, approx_chain_simple, clear_component_model, clear_rectangle, clear_training_components, close_ocr, cluster_model_components, copy_metrology_object, create_component_model, create_ocr_class_box, create_text_model, create_trained_component_model
- **Deep Learning** (4/88): add_dl_pruning_batch, apply_dl_model, clear_dl_model, create_dl_layer_activation, create_dl_layer_affine_grid, create_dl_layer_anchors, create_dl_layer_batch_normalization, create_dl_layer_box_proposals, create_dl_layer_box_targets, create_dl_layer_class_id_conversion, create_dl_layer_concat, create_dl_layer_convolution
- **Matching** (36/96): apply_deep_counting_model, clear_deformable_model, clear_descriptor_model, clear_ncc_model, clear_shape_model, create_deep_counting_model, create_planar_calib_deformable_model_xld, create_planar_uncalib_deformable_model_xld, deserialize_deformable_model, deserialize_descriptor_model, deserialize_ncc_model, deserialize_shape_model
- **File** (0/53): close_file, copy_file, delete_file, deserialize_handle, deserialize_image, deserialize_object, deserialize_region, deserialize_tuple, deserialize_xld, file_exists, fnew_line, fread_bytes
- **3D Matching** (15/59): add_deformable_surface_model_reference_point, add_deformable_surface_model_sample, apply_deep_matching_3d, apply_dl_model, clear_deformable_surface_matching_result, clear_deformable_surface_model, clear_shape_model_3d, clear_surface_matching_result, clear_surface_model, create_deep_matching_3d, deserialize_deformable_surface_model, deserialize_shape_model_3d
- **Inspection** (12/55): add_texture_inspection_model_image, clear_bead_inspection_model, clear_structured_light_model, clear_texture_inspection_model, clear_texture_inspection_result, clear_train_data_variation_model, clear_variation_model, close_ocv, deserialize_ocv, deserialize_structured_light_model, deserialize_texture_inspection_model, deserialize_variation_model
- **Develop** (0/37): dev_clear_obj, dev_clear_window, dev_close_inspect_ctrl, dev_close_tool, dev_close_window, dev_disp_text, dev_display, dev_error_var, dev_get_exception_data, dev_get_preferences, dev_get_system, dev_get_window

## Version awareness (HALCON's op set changes between releases)
Operator counts per scraped release: v12=2147, v13=2176, v2311=2381, v2411=2387, v2505=2411, v2605=2313 (union 2466). Coverage above is vs the primary scrape; the classification below is honest about which claimed `Op.halcon` names are stable vs release-specific.

- **919** claimed names exist in **all** scraped releases (stable).
- **54 version-drift** (real, but only some releases): `adapt_shape_model_high_noise` (in 2311/2411/2505/2605); `add_image_border` (in 2311/2411/2505/2605); `apply_texture_inspection_model` (in 13/2311/2411/2505/2605); `area_intersection_rectangle2` (in 2311/2411/2505/2605); `bilateral_filter` (in 13/2311/2411/2505/2605); `convol_channels` (in 2605); `create_generic_shape_model` (in 2311/2411/2505/2605); `create_structured_light_model` (in 2311/2411/2505/2605); `create_texture_inspection_model` (in 13/2311/2411/2505/2605); `crop_rectangle2` (in 2311/2411/2505/2605); `decode_structured_light_pattern` (in 2311/2411/2505/2605); `distance_cc_min_points` (in 2311/2411/2505/2605); `distance_point_line` (in 2311/2411/2505/2605); `distance_point_pluecker_line` (in 2311/2411/2505/2605); `dual_quat_compose` (in 13/2311/2411/2505/2605); `dual_quat_conjugate` (in 13/2311/2411/2505/2605); `dual_quat_interpolate` (in 13/2311/2411/2505/2605); `dual_quat_normalize` (in 13/2311/2411/2505/2605); `dual_quat_to_hom_mat3d` (in 13/2311/2411/2505/2605); `dual_quat_to_pose` (in 13/2311/2411/2505/2605); `dual_quat_to_screw` (in 13/2311/2411/2505/2605); `dual_quat_trans_line_3d` (in 13/2311/2411/2505/2605); `dual_quat_trans_point_3d` (in 2311/2411/2505/2605); `edges_object_model_3d` (in 13/2311/2411/2505/2605); `equ_histo_image_rect` (in 2311/2411/2505/2605); `find_box_3d` (in 2311/2411/2505/2605); `find_generic_shape_model` (in 2311/2411/2505/2605); `find_ncc_models` (in 13/2311/2411/2505/2605); `find_surface_model_image` (in 13/2311/2411/2505/2605); `fuse_object_model_3d` (in 2311/2411/2505/2605); `gen_canonical_variates_trans` (in 2605); `gen_image_warp_map` (in 2505/2605); `gen_savitzky_golay_filter` (in 2605); `gen_structured_light_pattern` (in 2311/2411/2505/2605); `guided_filter` (in 13/2311/2411/2505/2605); `height_width_ratio` (in 2311/2411/2505/2605); `height_width_ratio_xld` (in 2311/2411/2505/2605); `interleave_channels` (in 13/2311/2411/2505/2605); `intersection_region_contour_xld` (in 2411/2505/2605); `mean_image_shape` (in 2311/2411/2505/2605); `pluecker_line_to_point_direction` (in 2311/2411/2505/2605); `pluecker_line_to_points` (in 2311/2411/2505/2605); `point_direction_to_pluecker_line` (in 2311/2411/2505/2605); `point_pluecker_line_to_hom_mat3d` (in 2311/2411/2505/2605); `points_to_pluecker_line` (in 2311/2411/2505/2605); `pose_to_dual_quat` (in 13/2311/2411/2505/2605); `reconstruct_surface_structured_light` (in 2311/2411/2505/2605); `rectangularity_xld` (in 2311/2411/2505/2605); `refine_surface_model_pose_image` (in 13/2311/2411/2505/2605); `screw_to_dual_quat` (in 13/2311/2411/2505/2605); `segment_image_mser` (in 13/2311/2411/2505/2605); `test_region_points` (in 2411/2505/2605); `uncalibrated_photometric_stereo` (in 2311/2411/2505/2605); `watersheds_marker` (in 2311/2411/2505/2605)
- **0** claimed names exist in **no** scraped release — genuine bad names / library-specific / voxel-3D, not version drift.

## Honest reading
- HALCON's ~2313 operators include large non-algorithmic chapters (Graphics / Tuple / System / File / Develop / Control) an algorithm-design engine does not target; real algorithmic headroom is smaller than the raw gap.
- Many operators are parametric variants of one family (collapse to fewer).
- Coverage counts a *nearest analogue*, not signature-level parity; per-operator typed stubs (`data/halcon_stubs.json`, with real Python signatures from the `mvtec-halcon` binding when available) track what is named vs implemented.
