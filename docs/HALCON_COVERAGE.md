# HALCON operator coverage (measured vs the real reference)

Source: `https://www.mvtec.com/doc/halcon/2605/en/` (version 2605).
Ground truth: **2313 operators across 30 top-level chapters** (218 TOC pages), mined by `halcon_scrape.py`.

**imgevolve maps to 403 / 2313 HALCON operators (17.4%)** via `Op.halcon`, from 733 registry ops.

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
| Tools | 7 | 108 | 101 |
| Transformations | 18 | 118 | 100 |
| Classification | 0 | 99 | 99 |
| Legacy | 13 | 110 | 97 |
| OCR | 0 | 96 | 96 |
| Matching | 2 | 96 | 94 |
| Deep Learning | 2 | 88 | 86 |
| Image | 29 | 110 | 81 |
| Filters | 129 | 196 | 67 |
| Calibration | 2 | 68 | 66 |
| 3D Reconstruction | 13 | 76 | 63 |
| 3D Matching | 2 | 59 | 57 |
| Matrix | 0 | 57 | 57 |
| Inspection | 0 | 55 | 55 |
| File | 0 | 53 | 53 |
| XLD | 53 | 97 | 44 |
| 3D Object Model | 7 | 51 | 44 |
| Develop | 0 | 37 | 37 |
| Control | 0 | 34 | 34 |
| 2D Metrology | 2 | 32 | 30 |
| Regions | 77 | 106 | 29 |
| Identification | 1 | 27 | 26 |
| Image Source | 0 | 25 | 25 |
| Segmentation | 34 | 53 | 19 |
| Object | 1 | 16 | 15 |
| 1D Measuring | 6 | 20 | 14 |
| Morphology | 34 | 44 | 10 |

## Build targets — biggest gaps first (sample uncovered operators)

- **Graphics** (3/174): add_scene_3d_camera, add_scene_3d_instance, add_scene_3d_label, add_scene_3d_light, attach_background_to_window, attach_drawing_object_to_window, clear_drawing_object, clear_scene_3d, clear_window, close_window, convert_coordinates_image_to_window, convert_coordinates_window_to_image
- **Tuple** (0/165): clear_handle, copy_dict, create_dict, dict_to_json, get_dict_object, get_dict_param, get_dict_tuple, get_handle_object, get_handle_param, get_handle_tuple, handle_to_integer, integer_to_handle
- **System** (0/141): activate_compute_device, broadcast_condition, clear_barrier, clear_condition, clear_event, clear_message, clear_message_queue, clear_mutex, clear_serial, clear_serialized_item, close_io_channel, close_io_device
- **Tools** (7/108): abs_funct_1d, adjust_mosaic_images, angle_ll, angle_lx, apply_distance_transform_xld, area_intersection_rectangle2, bundle_adjust_mosaic, clear_distance_transform_xld, clear_scattered_data_interpolator, close_bg_esti, compose_funct_1d, connect_grid_points
- **Transformations** (18/118): affine_trans_pixel, affine_trans_point_2d, affine_trans_point_3d, angle_ll, angle_lx, axis_angle_to_quat, convert_point_3d_cart_to_spher, convert_point_3d_spher_to_cart, convert_pose_type, create_generic_shape_model, create_pose, deserialize_dual_quat
- **Classification** (0/99): add_class_train_data_gmm, add_class_train_data_knn, add_class_train_data_mlp, add_class_train_data_svm, add_sample_class_gmm, add_sample_class_knn, add_sample_class_mlp, add_sample_class_svm, add_sample_class_train_data, classify_class_gmm, classify_class_knn, classify_class_mlp
- **Legacy** (13/110): approx_chain, approx_chain_simple, bottom_hat, clear_component_model, clear_rectangle, clear_training_components, close_ocr, cluster_model_components, copy_metrology_object, create_component_model, create_ocr_class_box, create_text_model
- **OCR** (0/96): append_ocr_trainf, apply_deep_ocr, clear_lexicon, clear_ocr_class_cnn, clear_ocr_class_knn, clear_ocr_class_mlp, clear_ocr_class_svm, clear_text_model, clear_text_result, concat_ocr_trainf, create_deep_ocr, create_lexicon
- **Matching** (2/96): adapt_shape_model_high_noise, apply_deep_counting_model, clear_deformable_model, clear_descriptor_model, clear_ncc_model, clear_shape_model, create_aniso_shape_model, create_aniso_shape_model_xld, create_calib_descriptor_model, create_deep_counting_model, create_generic_shape_model, create_local_deformable_model
- **Deep Learning** (2/88): add_dl_pruning_batch, apply_dl_model, clear_dl_model, create_dl_layer_activation, create_dl_layer_affine_grid, create_dl_layer_anchors, create_dl_layer_batch_normalization, create_dl_layer_box_proposals, create_dl_layer_box_targets, create_dl_layer_class_id_conversion, create_dl_layer_concat, create_dl_layer_convolution
- **Image** (29/110): add_channels, append_channel, area_center_gray, change_domain, channels_to_image, close_framegrabber, complex_to_real, compose2, compose3, compose4, compose5, compose6
- **Filters** (129/196): abs_diff_image, add_image, apply_color_trans_lut, atan2_image, bit_and, bit_or, bit_xor, clear_color_trans_lut, convert_map_type, convol_channels, convol_fft, convol_image

## Version awareness (HALCON's op set changes between releases)
Operator counts per scraped release: v12=2147, v13=2176, v2311=2381, v2411=2387, v2505=2411, v2605=2313 (union 2466). Coverage above is vs the primary scrape; the classification below is honest about which claimed `Op.halcon` names are stable vs release-specific.

- **394** claimed names exist in **all** scraped releases (stable).
- **9 version-drift** (real, but only some releases): `add_image_border` (in 2311/2411/2505/2605); `bilateral_filter` (in 13/2311/2411/2505/2605); `equ_histo_image_rect` (in 2311/2411/2505/2605); `guided_filter` (in 13/2311/2411/2505/2605); `height_width_ratio` (in 2311/2411/2505/2605); `height_width_ratio_xld` (in 2311/2411/2505/2605); `mean_image_shape` (in 2311/2411/2505/2605); `rectangularity_xld` (in 2311/2411/2505/2605); `segment_image_mser` (in 13/2311/2411/2505/2605)
- **0** claimed names exist in **no** scraped release — genuine bad names / library-specific / voxel-3D, not version drift.

## Honest reading
- HALCON's ~2313 operators include large non-algorithmic chapters (Graphics / Tuple / System / File / Develop / Control) an algorithm-design engine does not target; real algorithmic headroom is smaller than the raw gap.
- Many operators are parametric variants of one family (collapse to fewer).
- Coverage counts a *nearest analogue*, not signature-level parity; per-operator typed stubs (`data/halcon_stubs.json`, with real Python signatures from the `mvtec-halcon` binding when available) track what is named vs implemented.
