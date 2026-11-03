# レシピの GPU 経路(生成物)

`tools/gen_gpu_routes.py` が `fullseye.explain_pipeline(stages, (2048, 2048), device="auto", assume_cuda=True)` を既存のレシピ全部(`fullseye/data/RECIPE_INDEX.json`)に当てた表。手で直さない。
**前** = 領域の解析の族(`accel_label.ADOPTED`、34 op)を経路から外した場合、**後** = 今の経路。
`assume_cuda=True` は CUDA・CuPy・空き VRAM のある機械として経路表だけで決める(GPU の無い CI でも同じ表)。

| 2 段以上のレシピ 220 本・578 段 | GPU の段 | 全段 GPU | 切り替わり | 往復の見込み |
|---|---:|---:|---:|---:|
| 前 | 162 | 8 | 135 | 126 |
| 後 | 199 | 33 | 102 | 126 |

| レシピ | 前: 切替 / 往復 | 後: 切替 / 往復 | 後の段(CPU の段は理由つき) |
|---|---:|---:|---|
| Denoise — bilateral + unsharp | 0 / 1 | 0 / 1 | bilateral[GPU] → unsharp[GPU] |
| Denoise — total variation | 0 / 1 | 0 / 1 | sk_tv[GPU] |
| Denoise — median | 0 / 1 | 0 / 1 | median[GPU] |
| Edge — Sobel + Otsu | 0 / 1 | 0 / 1 | gaussian[GPU] → sobel_amp[GPU] → otsu[GPU] |
| Edge — Canny | 0 / 1 | 0 / 1 | gaussian[GPU] → canny[GPU] |
| Segment — blob / coin | 1 / 1 | 0 / 1 | gaussian[GPU] → otsu[GPU] → fill_up[GPU] → remove_small[GPU] |
| Count — blobs | 1 / 1 | 0 / 1 | gaussian[GPU] → otsu[GPU] → fill_up[GPU] → count_obj[GPU] |
| Binarize — document (adaptive) | 0 / 1 | 0 / 1 | adaptive_gauss_thresh[GPU] |
| Enhance — CLAHE contrast | 0 / 1 | 0 / 1 | clahe[GPU] |
| Enhance — histogram equalize | 0 / 1 | 0 / 1 | equalize[GPU] |
| Enhance — gamma | 0 / 1 | 0 / 1 | gamma[GPU] |
| Sharpen — unsharp mask | 0 / 1 | 0 / 1 | unsharp[GPU] |
| Sharpen — highpass | 0 / 1 | 0 / 1 | highpass[GPU] |
| Texture — Gabor | 0 / 1 | 0 / 1 | gabor[GPU] |
| Texture — local std | 0 / 1 | 0 / 1 | std_filter[GPU] |
| Keypoints — Harris corners | 0 / 0 | 0 / 0 | sk_corner_harris[CPU:not_listed] |
| Blobs — Difference of Gaussians | 0 / 0 | 0 / 0 | sk_dog[CPU:not_listed] |
| Morphology — gradient | 0 / 1 | 0 / 1 | morph_grad[GPU] |
| Shape — distance transform | 1 / 2 | 1 / 2 | gaussian[GPU] → otsu[GPU] → distance_transform[GPU] |
| Spots — local maxima | 0 / 1 | 0 / 1 | gaussian[GPU] → local_max[GPU] |
| FA — scratch on hairline metal | 1 / 1 | 0 / 1 | gaussian[GPU] → sk_rolling_ball[GPU] → threshold[GPU] → select_shape[GPU] |
| FA — dent and foreign fibre on resin | 3 / 3 | 2 / 3 | gaussian[GPU] → hx_plane_deviation[GPU] → threshold[GPU] → select_shape[GPU] |
| FA — engraved lot code (binarize for OCR) | 1 / 1 | 0 / 1 | gaussian[GPU] → otsu[GPU] → select_shape[GPU] |
| FA — count holes in a back-lit plate | 1 / 1 | 0 / 1 | otsu[GPU] → sk_clear_border[GPU] → count_obj[GPU] |
| FA — weld porosity (X-ray) | 1 / 1 | 0 / 1 | gaussian[GPU] → local_threshold[GPU] → select_shape[GPU] |
| Measure — diameter of a bright round part | 1 / 1 | 1 / 1 | gaussian[GPU] → otsu[GPU] → fill_up[GPU] → diameter_region[CPU:not_listed] |
| Inspect — roundness of a punched disk (circularity) | 1 / 1 | 0 / 1 | otsu[GPU] → fill_up[GPU] → circularity[GPU] |
| Preprocess — remove salt-and-pepper impulses before measuring part area | 1 / 1 | 0 / 1 | median[GPU] → otsu[GPU] → area_center[GPU] |
| Preprocess — denoise a flat field and verify the residual noise level | 1 / 1 | 1 / 1 | median[GPU] → estimate_noise[CPU:not_listed] |
| Inspect — count parts under strongly uneven illumination (local threshold) | 1 / 1 | 0 / 1 | local_threshold[GPU] → opening_circle[GPU] → count_obj[GPU] |
| Preprocess — flatten an illumination gradient with a plane fit, then count parts | 2 / 2 | 1 / 2 | hx_plane_deviation[GPU] → otsu[GPU] → count_obj[GPU] |
| Inspect — split touching round parts and count them (distance-transform peaks) | 2 / 2 | 2 / 2 | otsu[GPU] → dist_transform[GPU] → xsk2_h_maxima[CPU:not_listed] → count_obj[CPU:chain_only] |
| Measure — part area with a k-means intensity segmentation | 1 / 1 | 1 / 1 | sg_kmeans_intensity[GPU] → area_center[CPU:chain_only] |
| Measure — part area with hysteresis thresholding | 1 / 1 | 1 / 1 | gaussian[GPU] → hysteresis_threshold[CPU:not_listed] → area_center[CPU:chain_only] |
| Measure — hole area fraction of a washer | 1 / 1 | 0 / 1 | otsu[GPU] → area_holes[GPU] |
| Inspect — count punched holes in a plate (Euler number) | 1 / 1 | 1 / 1 | otsu[GPU] → euler_number[CPU:not_listed] |
| Measure — orientation angle of an elongated part | 1 / 1 | 0 / 1 | otsu[GPU] → orientation_region[GPU] |
| Measure — equivalent-ellipse semi-axes of an oval part | 1 / 1 | 0 / 1 | otsu[GPU] → elliptic_axis[GPU] |
| Measure — equivalent-ellipse angle Phi of a turned bar (elliptic_axis) | 1 / 1 | 0 / 1 | otsu[GPU] → elliptic_axis[GPU] |
| Measure — anisometry (aspect ratio) of an oval part | 1 / 1 | 0 / 1 | gaussian[GPU] → otsu[GPU] → eccentricity[GPU] |
| Measure — area and position of the largest part in a cluttered scene | 1 / 1 | 0 / 1 | otsu[GPU] → select_largest[GPU] → area_center[GPU] |
| Measure — convex-hull area of a C-shaped part | 1 / 1 | 1 / 1 | otsu[GPU] → get_region_convex[CPU:not_listed] → area_center[CPU:chain_only] |
| Inspect — convexity of a C-shaped clip (gap detection) | 1 / 1 | 1 / 1 | otsu[GPU] → convexity[CPU:not_listed] |
| Measure — length of a thin wire or scratch | 1 / 1 | 1 / 1 | otsu[GPU] → diameter_region[CPU:not_listed] |
| Measure — wall thickness of a bar-shaped part | 1 / 1 | 1 / 1 | otsu[GPU] → get_region_thickness[CPU:not_listed] |
| Inspect — count the arms of a branched part (skeleton end points) | 1 / 1 | 1 / 1 | otsu[GPU] → opening_circle[GPU] → skeleton[CPU:not_listed] → r2_endpoints_skeleton[CPU:not_listed] → count_obj[CPU:chain_only] |
| Preprocess — remove dust specks, then count the real parts | 1 / 1 | 0 / 1 | otsu[GPU] → remove_small[GPU] → count_obj[GPU] |
| Inspect — dark pits on a bright surface (black top-hat) | 1 / 1 | 0 / 1 | bothat[GPU] → threshold[GPU] → count_obj[GPU] |
| Inspect — bright spots on a vignetted background (white top-hat) | 1 / 1 | 0 / 1 | gray_tophat[GPU] → otsu[GPU] → count_obj[GPU] |
| Inspect — count bright round blobs (Laplacian-of-Gaussian detector) | 1 / 1 | 1 / 1 | gaussian[GPU] → xsk_blob_log[CPU:not_listed] |
| Inspect — count circular holes with the Hough circle transform | 1 / 1 | 1 / 1 | gaussian[GPU] → cv_hough_circles[CPU:not_listed] |
| Inspect — count corners of rectangular parts | 1 / 1 | 1 / 1 | gaussian[GPU] → cv_good_features[CPU:not_listed] |
| Measure — edge column from the gradient projection profile | 1 / 2 | 1 / 2 | gaussian[GPU] → sobel_amp[GPU] → img_to_projection_profile[GPU] |
| Measure — edge position on a 1-D grey profile (derivative peak) | 1 / 1 | 1 / 1 | img_to_signal[CPU:not_listed] → tb_smooth_funct_1d_gauss[GPU] → tb_derivate_funct_1d[GPU] |
| Measure — sub-pixel edge position along a caliper line | 1 / 1 | 1 / 1 | gaussian[GPU] → m1_measure_pos[CPU:not_listed] |
| Inspect — count bright bars crossed by a caliper (edge pairs) | 1 / 1 | 1 / 1 | gaussian[GPU] → m1_measure_pairs[CPU:not_listed] |
| Measure — count all edges along a caliper line | 0 / 0 | 0 / 0 | m1_measure_pos[CPU:not_listed] → count_contours[CPU:not_listed] |
| Measure — sub-pixel area of a round part from its iso-contour | 0 / 0 | 0 / 0 | threshold_sub_pix[CPU:not_listed] → area_center_xld[CPU:not_listed] |
| Measure — maximal diameter of a part from its sub-pixel contour | 0 / 0 | 0 / 0 | threshold_sub_pix[CPU:not_listed] → diameter_xld[CPU:not_listed] |
| Measure — radius of a round part by an ellipse fit to its sub-pixel edge | 0 / 0 | 0 / 0 | threshold_sub_pix[CPU:not_listed] → elliptic_axis_xld[CPU:not_listed] |
| Measure — angle of a straight edge by a sub-pixel line fit | 2 / 2 | 2 / 2 | gaussian[GPU] → edges_sub_pix[GPU] → fit_line_contours[CPU:not_listed] → xg_orientation[CPU:not_listed] |
| Measure — orientation of a bar from its sub-pixel outline | 0 / 0 | 0 / 0 | threshold_sub_pix[CPU:not_listed] → xg_orientation[CPU:not_listed] |
| Measure — orientation of a bar from its sub-pixel outline (orientation_xld) | 0 / 0 | 0 / 0 | threshold_sub_pix[CPU:not_listed] → orientation_xld[CPU:not_listed] |
| Measure — equivalent-ellipse angle Phi of a bar from its sub-pixel outline (elliptic_axis_xld) | 0 / 0 | 0 / 0 | threshold_sub_pix[CPU:not_listed] → elliptic_axis_xld[CPU:not_listed] |
| Measure — perimeter of a round part from sub-pixel edges | 2 / 2 | 2 / 2 | gaussian[GPU] → edges_sub_pix[GPU] → length_xld[CPU:not_listed] |
| Inspect — length of a scratch from its centre line (lines_gauss) | 0 / 0 | 0 / 0 | lines_gauss[CPU:not_listed] → length_xld[CPU:not_listed] |
| Measure — sub-pixel centre of a laser spot / fiducial dot | 1 / 1 | 1 / 1 | xsp_savgol[GPU] → sp_local_max_sub_pix[CPU:not_listed] |
| Locate — find a fiducial mark by normalized cross-correlation | 0 / 1 | 0 / 1 | gaussian[GPU] → ncc_locate[GPU] |
| Locate — find a rotated part and its angle (shape-based matching) | 1 / 1 | 1 / 1 | gaussian[GPU] → shape_locate[CPU:not_listed] |
| Inspect — segment a coloured part by saturation (HSV) | 2 / 1 | 1 / 1 | trans_from_rgb[CPU:not_listed] → access_channel[CPU:not_listed] → threshold[GPU] → area_center[GPU] |
| Inspect — pick a blue part by its colour channel | 2 / 1 | 1 / 1 | access_channel[CPU:not_listed] → threshold[GPU] → area_center[GPU] |
| Preprocess — rotate an image by a known angle and check the part angle | 1 / 1 | 0 / 1 | rotate_img[GPU] → otsu[GPU] → orientation_region[GPU] |
| Preprocess — zoom about the centre and verify the area scale | 1 / 1 | 0 / 1 | zoom_image_factor[GPU] → otsu[GPU] → area_center[GPU] |
| Preprocess — mirror an image upside down (row flip) | 2 / 1 | 1 / 1 | mirror_image[CPU:not_listed] → otsu[GPU] → area_center[GPU] |
| Measure — ring radius by polar unwrapping | 1 / 1 | 1 / 1 | polar_trans_image[CPU:not_listed] → img_to_projection_profile[GPU] |
| Preprocess — inpaint scratch lines before measuring part area | 2 / 1 | 1 / 1 | xcv_inpaint[CPU:not_listed] → otsu[GPU] → area_center[GPU] |
| Preprocess — Richardson-Lucy deblur of a defocused part, then measure | 2 / 2 | 1 / 2 | iv_richardson_lucy[GPU] → otsu[GPU] → area_center[GPU] |
| Preprocess — suppress periodic interference stripes with an FFT low-pass | 1 / 1 | 0 / 1 | lowpass[GPU] → otsu[GPU] → area_center[GPU] |
| Measure — period of a stripe texture by zero crossings | 1 / 1 | 1 / 1 | img_to_projection_profile[GPU] → tb_stat_zscore[GPU] → tb_zero_crossings_funct_1d[CPU:not_listed] → tb_num_points_funct_1d[CPU:not_listed] |
| Measure — direction of a grating or brushed texture (structure tensor) | 1 / 2 | 1 / 2 | gaussian[GPU] → structure_tensor_orientation[GPU] |
| Inspect — length of a dark scratch on brushed metal | 1 / 1 | 1 / 1 | bothat[GPU] → threshold[GPU] → select_largest[GPU] → diameter_region[CPU:not_listed] |
| Inspect — dark contamination spots on a woven fabric | 1 / 1 | 0 / 1 | lowpass[GPU] → bothat[GPU] → threshold[GPU] → count_obj[GPU] |
| Identify — count the bars of a 1-D barcode | 1 / 1 | 1 / 1 | bilateral[GPU] → decode_barcode[CPU:not_listed] |
| Preprocess — segment dark characters on shaded paper for OCR | 0 / 0 | 0 / 0 | hx_char_threshold[CPU:not_listed] → count_obj[CPU:chain_only] |
| Inspect — defects by golden-template difference against a good part | 2 / 1 | 1 / 1 | abs_diff_image[CPU:chain_only] → threshold[GPU] → opening_circle[GPU] → count_obj[GPU] |
| Preprocess — flat-field correction by dividing by a white reference | 2 / 1 | 1 / 1 | div_image[CPU:chain_only] → otsu[GPU] → area_center[GPU] |
| Preprocess — subtract a background frame, then measure the part area | 2 / 1 | 1 / 1 | sub_image[CPU:chain_only] → threshold[GPU] → area_center[GPU] |
| Inspect — missing material against the nominal shape (region difference) | 1 / 1 | 1 / 1 | otsu[GPU] → difference[CPU:not_listed] → area_center[CPU:chain_only] |
| Inspect — count bright particles and their total area | 1 / 1 | 1 / 1 | otsu[GPU] → blob_label[CPU:below_measured_size] → blob_features[CPU:not_listed] |
| Inspect — split touching particles with distance-transform seeds | 3 / 2 | 3 / 2 | otsu[GPU] → blob_label[CPU:below_measured_size] → blob_distance[GPU] → blob_seeds[CPU:not_listed] → blob_split[CPU:not_listed] |
| Inspect — particle count with an honest lower/upper interval | 1 / 1 | 1 / 1 | otsu[GPU] → blob_count_interval[CPU:not_listed] |
| Inspect — score a segmentation against the ground-truth mask (Dice / Jaccard) | 1 / 1 | 1 / 1 | otsu[GPU] → blob_label[CPU:below_measured_size] → seg_dice_jaccard[CPU:not_listed] |
| Inspect — separate touching parts with marker-controlled watershed | 3 / 3 | 3 / 3 | otsu[GPU] → blob_distance[GPU] → invert[GPU] → blob_seeds[CPU:not_listed] → watersheds_marker[CPU:not_listed] |
| Preprocess — automatic gray threshold between two intensity classes (ISODATA) | 1 / 1 | 1 / 1 | gaussian[GPU] → threshold_isodata[CPU:not_listed] |
| Measure — subpixel edge position along a caliper line | 0 / 0 | 0 / 0 | gen_measure_rectangle2[CPU:not_listed] → measure_pos[CPU:not_listed] |
| Measure — width of a bright bar in millimetres (edge pair + scale) | 0 / 0 | 0 / 0 | gen_measure_rectangle2[CPU:not_listed] → measure_pairs[CPU:not_listed] → table_px_to_mm[CPU:not_listed] |
| Measure — hole radius and centre by circle metrology | 0 / 0 | 0 / 0 | create_metrology_model[CPU:not_listed] → add_metrology_object_circle_measure[CPU:not_listed] → apply_metrology_model[CPU:not_listed] → table_px_to_mm[CPU:not_listed] |
| Preprocess — OpenVX affine warp, then gauge where the edge moved | 1 / 1 | 1 / 1 | vx_warp_affine[GPU] → gen_measure_rectangle2[CPU:not_listed] → measure_pos[CPU:not_listed] |
| Preprocess — OpenVX look-up table, then 16-bin histogram | 1 / 1 | 1 / 1 | vx_table_lookup[CPU:not_listed] → vx_histogram[GPU] |
| Preprocess — raw Bayer ISP: black level, demosaic, gray-world white balance | 2 / 1 | 2 / 1 | raw_black_level[CPU:not_listed] → raw_demosaic_bilinear[GPU] → awb_gains[CPU:below_measured_size] |
| Preprocess — lens-shading (vignetting) correction from a flat-field frame | 0 / 0 | 0 / 0 | lens_shading_gain[CPU:below_measured_size] → lens_shading_correct[CPU:not_listed] |
| Simulate — rule-90 cellular automaton (Sierpinski) stepped and rendered | 0 / 0 | 0 / 0 | perpetual_state[CPU:not_listed] → perpetual_step[CPU:not_listed] → perpetual_render[CPU:not_listed] |
| Simulate — SEM secondary-electron image of a sloped facet | 0 / 1 | 0 / 1 | sem_render[GPU] |
| Simulate — photoluminescence carrier-diffusion PSF | 0 / 0 | 0 / 0 | pl_diffusion_psf[CPU:not_listed] |
| Visualize — plot a measured series on data axes (data -> pixel mapping) | 0 / 0 | 0 / 0 | axes_transform[CPU:not_listed] → data_to_pixel[CPU:below_measured_size] → plot_series[CPU:not_listed] |
| Visualize — draw a filled ellipse marker and verify its pixel area | 2 / 1 | 2 / 1 | ellipse[CPU:not_listed] → otsu[GPU] → blob_label[CPU:below_measured_size] → blob_features[CPU:not_listed] |
| Inspect — image fidelity report of a noisy capture (PSNR / RMSE with conditions) | 0 / 0 | 0 / 0 | compare_images[CPU:not_listed] → metrics_table[CPU:not_listed] |
| Inspect — perceptual colour difference ΔE*ab against a reference colour | 0 / 0 | 0 / 0 | rgb_to_lab[CPU:not_listed] → rgb_to_lab[CPU:not_listed] → delta_e_76[CPU:not_listed] |
| Inspect — mutual information of a multimodal pair (inverted contrast) | 1 / 1 | 1 / 1 | invert[GPU] → mutual_information[CPU:not_listed] |
| Inspect — embed and blindly recover an integrity watermark | 0 / 0 | 0 / 0 | watermark_embed[CPU:not_listed] → watermark_extract[CPU:not_listed] |
| Inspect — detect a copy-move forgery and its displacement | 1 / 1 | 1 / 1 | gaussian[GPU] → copy_move_regions[CPU:not_listed] |
| Inspect — locate a spliced patch with different sensor noise | 2 / 1 | 2 / 1 | noise_inconsistency_map[CPU:below_measured_size] → otsu[GPU] → blob_label[CPU:below_measured_size] → blob_features[CPU:not_listed] |
| Preprocess — colour transfer of a product photo to a reference look | 0 / 0 | 0 / 0 | color_transfer[CPU:not_listed] |
| Measure — 1-D optimal transport plan between two sample sets | 0 / 0 | 0 / 0 | transport_plan_1d[CPU:not_listed] → apply_transport[CPU:not_listed] |
| Measure — radius of a round part from its contour (elliptic Fourier) | 0 / 0 | 0 / 0 | fourier_smooth[CPU:not_listed] → elliptic_fourier[CPU:not_listed] → invariants[CPU:not_listed] |
| Preprocess — thin-plate-spline warp from control points, check the part moved | 2 / 2 | 2 / 2 | warp_tps_image[GPU] → otsu[GPU] → blob_label[CPU:below_measured_size] → blob_features[CPU:not_listed] |
| Analyze — statistical shape model: variance explained by the first mode | 0 / 0 | 0 / 0 | shape_synth_family[CPU:not_listed] → shape_pca[CPU:not_listed] → shape_explained_variance[CPU:not_listed] |
| Inspect — form error after best-fit similarity alignment of landmarks | 0 / 0 | 0 / 0 | procrustes_align[CPU:not_listed] → procrustes_distance[CPU:not_listed] |
| Inspect — airfoil blade profile deviation from the nominal NACA section | 0 / 0 | 0 / 0 | profile_synth_naca4[CPU:not_listed] → profile_perturb[CPU:not_listed] → profile_deviation[CPU:not_listed] |
| Measure — airfoil leading-edge radius | 0 / 0 | 0 / 0 | profile_synth_naca4[CPU:not_listed] → profile_normalise[CPU:not_listed] → profile_leading_edge_radius[CPU:not_listed] |
| Measure — profile roughness Ra / Rq after a robust Gaussian filter (scratched, curved part) | 0 / 0 | 0 / 0 | robust_gaussian_profile[CPU:not_listed] → profile_params[CPU:not_listed] |
| Measure — profile roughness Ra / Rq after a robust spline filter | 0 / 0 | 0 / 0 | robust_spline_profile[CPU:not_listed] → profile_params[CPU:not_listed] |
| Measure — areal roughness Sq: form removal, Gaussian L-filter, ISO 25178 parameters | 0 / 0 | 0 / 0 | surface_form_remove[CPU:below_measured_size] → surface_filter[CPU:below_measured_size] → surface_params[CPU:not_listed] |
| Measure — Sq of a synthetic self-affine surface (PSD synthesis + form removal) | 0 / 0 | 0 / 0 | surface_synth_psd[CPU:not_listed] → surface_form_remove[CPU:below_measured_size] → surface_params[CPU:not_listed] |
| Preprocess — rotate colours about the grey axis (quaternion colour rotation) | 0 / 0 | 0 / 0 | rgb_to_quaternion[CPU:not_listed] → quat_color_rotate[CPU:not_listed] → quaternion_to_rgb[CPU:below_measured_size] |
| Measure — local orientation of a grating with the monogenic signal | 0 / 0 | 0 / 0 | monogenic_signal[CPU:not_listed] → monogenic_orientation[CPU:not_listed] |
| Inspect — locate a part template under an illumination change (orientation codes) | 1 / 1 | 1 / 1 | gaussian[GPU] → ocm_match[CPU:not_listed] |
| Measure — large displacement from multi-wavelength phases (CRT unwrapping) | 0 / 0 | 0 / 0 | crt_displacement[CPU:not_listed] |
| Inspect — flat-field correct, then register the frame to the golden image | 0 / 0 | 0 / 0 | flat_field_correct[CPU:not_listed] → register_image[CPU:not_listed] |
| Inspect — stroke width of printed characters (SWT) | 0 / 0 | 0 / 0 | swt_map[CPU:not_listed] |
| Inspect — character candidates from a stroke-width field | 0 / 0 | 0 / 0 | text_candidates[CPU:not_listed] |
| Inspect — group character candidates into text lines | 0 / 0 | 0 / 0 | text_candidates[CPU:not_listed] → text_lines[CPU:not_listed] |
| 3D — radius of a ball from a noisy scan with stray points | 0 / 0 | 0 / 0 | voxel_grid_downsample[CPU:not_listed] → ransac_sphere[CPU:not_listed] |
| 3D — ball radius by least squares after statistical outlier removal | 0 / 0 | 0 / 0 | statistical_outlier_removal[CPU:not_listed] → fit_sphere_3d[CPU:not_listed] |
| 3D — tilt of a flat face (RANSAC plane) despite clutter | 0 / 0 | 0 / 0 | ransac_plane[CPU:not_listed] |
| 3D — pipe radius from a cylinder scan (normals + RANSAC cylinder) | 0 / 0 | 0 / 0 | estimate_point_normals[CPU:not_listed] → ransac_cylinder[CPU:not_listed] |
| 3D — mean curvature of a ball surface as a summary table | 0 / 0 | 0 / 0 | principal_curvatures[CPU:not_listed] → curvature_to_table[CPU:not_listed] |
| 3D — centre of a scanned part (centroid position) | 0 / 0 | 0 / 0 | voxel_grid_downsample[CPU:not_listed] → points_to_position[CPU:not_listed] |
| 3D — enclosed volume of a scanned ball (convex hull mesh) | 0 / 0 | 0 / 0 | convex_hull[CPU:not_listed] → mesh_volume[CPU:not_listed] |
| 3D — surface area of a scanned ball (convex hull mesh) | 0 / 0 | 0 / 0 | convex_hull[CPU:not_listed] → mesh_area[CPU:not_listed] |
| 3D — align a scan to its reference (ICP rigid transform) | 0 / 0 | 0 / 0 | voxel_grid_downsample[CPU:not_listed] → icp_point2point_3d[CPU:not_listed] |
| 3D — align a scan to its reference with point-to-plane ICP | 0 / 0 | 0 / 0 | estimate_point_normals[CPU:not_listed] → icp_point2plane[CPU:not_listed] |
| 3D — register two scans with generalized ICP (plane-to-plane) | 0 / 0 | 0 / 0 | voxel_grid_downsample[CPU:not_listed] → gicp[CPU:not_listed] |
| 3D — object pose from known 3-D points and their image (PnP) | 0 / 0 | 0 / 0 | dlt_pose[CPU:not_listed] |
| 3D — how far a part sits from its nominal pose (point-to-plane ICP -> pose error) | 0 / 0 | 0 / 0 | estimate_point_normals[CPU:not_listed] → icp_point2plane[CPU:not_listed] → pose_error[CPU:not_listed] |
| 3D — camera pose deviation from its nominal mounting (PnP -> RRE / RTE) | 0 / 0 | 0 / 0 | dlt_pose[CPU:not_listed] → rotation_translation_error[CPU:not_listed] |
| 3D — plane tilt from a depth camera image | 0 / 0 | 0 / 0 | depth_to_points[CPU:not_listed] → ransac_plane[CPU:not_listed] |
| 3D — height of a bump by phase-shift structured light | 0 / 0 | 0 / 0 | synthesize_fringes[CPU:below_measured_size] → decode_fringe[CPU:not_listed] |
| 3D — fuse a depth image into a TSDF volume and read occupancy | 1 / 1 | 1 / 1 | tsdf_from_depth[GPU] → sdf_to_occupancy[CPU:not_listed] |
| 3D — depth of a surface from a calibrated stereo pair (plane sweep) | 0 / 0 | 0 / 0 | plane_sweep_depth[CPU:not_listed] |
| 3D — voxel count of an inclusion after removing speckle | 0 / 0 | 0 / 0 | filter_by_volume[CPU:not_listed] → region_props[CPU:not_listed] |
| 3D — volume of a CT inclusion from its marching-cubes surface | 0 / 0 | 0 / 0 | voxel_to_mesh[CPU:not_listed] → mesh_volume[CPU:not_listed] |
| 3D — surface area of a CT inclusion (marching cubes + Taubin smoothing) | 0 / 0 | 0 / 0 | voxel_to_mesh[CPU:not_listed] → taubin_smooth[CPU:not_listed] → mesh_area[CPU:not_listed] |
| 3D — label the objects in a CT volume and read their voxel counts | 0 / 0 | 0 / 0 | vol_label[CPU:below_measured_size] → vol_region_props[CPU:not_listed] |
| Inspect — diameter of a dense inclusion along a probe line (CT volume) | 0 / 0 | 0 / 0 | vol_window_level[CPU:below_measured_size] → vol_wall_thickness[CPU:not_listed] |
| DEM — slope of a hillside after filling sinks | 1 / 1 | 1 / 1 | dem_fill_sinks[CPU:not_listed] → dem_slope[GPU] |
| DEM — hillshade of a tilted terrain | 0 / 1 | 0 / 1 | dem_hillshade[GPU] |
| CT — reconstruct a disk phantom and measure its area | 2 / 2 | 2 / 2 | radon_transform[CPU:not_listed] → filtered_backprojection[GPU] → otsu[GPU] |
| CT — find the rotation-axis offset of a scanner | 0 / 0 | 0 / 0 | sinogram_center_of_rotation[CPU:not_listed] |
| CT — correct an off-centre axis, reconstruct and measure | 2 / 2 | 2 / 2 | sinogram_center_shift[CPU:not_listed] → filtered_backprojection[GPU] → otsu[GPU] |
| CT — suppress ring artefacts from a bad detector, then measure | 2 / 2 | 2 / 2 | ring_artifact_apply[CPU:not_listed] → ring_artifact_remove[CPU:not_listed] → filtered_backprojection[GPU] → otsu[GPU] |
| Calibrate — camera focal length from views of a planar target | 0 / 0 | 0 / 0 | caltab_points[CPU:not_listed] → camera_calibration[CPU:not_listed] |
| Measure — circle on a plane in millimetres from pixels (homography) | 0 / 0 | 0 / 0 | image_to_world_plane[CPU:not_listed] → fit_circle_geometric[CPU:not_listed] |
| Measure — image radius of a 3-D ring seen by a camera | 0 / 0 | 0 / 0 | project_3d_point[CPU:not_listed] → fit_circle_geometric[CPU:not_listed] |
| Measure — sub-pixel shift between two images (phase correlation) | 0 / 0 | 0 / 0 | phase_correlation_shift[CPU:not_listed] |
| 3D — save a scan as XYZ text, reload it and re-measure the ball | 0 / 0 | 0 / 0 | points_write_xyz[CPU:not_listed] → points_read_xyz[CPU:not_listed] → ransac_sphere[CPU:not_listed] |
| 3D — export a part mesh as OBJ, re-import it and check its volume | 0 / 0 | 0 / 0 | convex_hull[CPU:not_listed] → mesh_write_obj[CPU:not_listed] → mesh_read_obj[CPU:not_listed] → mesh_volume[CPU:not_listed] |
| Print — filament volume for the equator layer of a scanned ball | 0 / 0 | 0 / 0 | convex_hull[CPU:not_listed] → mesh_slice_contours[CPU:not_listed] → contours_to_gcode[CPU:not_listed] → gcode_extrusion_volume[CPU:not_listed] |
| Inspect — map a camera pixel onto the CAD surface (depth of the hit) | 0 / 0 | 0 / 0 | convex_hull[CPU:not_listed] → cad_pixel_to_surface[CPU:not_listed] |
| Sense — horizon line a camera sees from a DEM | 0 / 0 | 0 / 0 | dem_skyline[CPU:not_listed] → render_skyline_view[CPU:not_listed] → skyline_extract[CPU:not_listed] |
| 3D — per-object volume table of a labelled scan | 0 / 0 | 0 / 0 | vol_label_shape_stats[CPU:not_listed] |
| 3D — volume table of the objects found in a grey scan | 0 / 0 | 0 / 0 | vol_label[CPU:below_measured_size] → vol_label_shape_stats[CPU:not_listed] |
| 3D — colour a labelled volume and cut an RGB slice | 0 / 0 | 0 / 0 | vol_colorize_labels[CPU:not_listed] → vol_label_slice_rgb[CPU:below_measured_size] |
| Sense — slit-scan (x-t) image of a moving spot | 0 / 0 | 0 / 0 | video_cube_cut[CPU:not_listed] |
| Sense — beating shell: maximum-intensity projection video | 0 / 0 | 0 / 0 | volseq_synth_beating[CPU:not_listed] → volseq_mip_video[CPU:not_listed] |
| Sense — sun elevation at a site over a day | 0 / 0 | 0 / 0 | sun_position[CPU:not_listed] |
| Optics — focal length of a biconvex singlet lens (paraxial EFL / BFL) | 0 / 0 | 0 / 0 | lens_system[CPU:not_listed] → paraxial_trace[CPU:not_listed] |
| Optics — optimize a singlet to a target focal length (merit function, damped least squares) | 0 / 0 | 0 / 0 | lens_system[CPU:not_listed] → merit_default[CPU:not_listed] → optimize_lens_operands[CPU:not_listed] |
| Optics — tolerance sensitivity of a singlet (which radius drives the RMS spot) | 0 / 0 | 0 / 0 | lens_system[CPU:not_listed] → tolerance_table[CPU:not_listed] → tolerance_criteria[CPU:not_listed] → tolerance_sensitivity[CPU:not_listed] |
| Optics — diffraction-limited MTF50 of an f-number (Airy PSF to MTF) | 2 / 1 | 2 / 1 | airy_pattern[CPU:not_listed] → psf_to_mtf[GPU] → mtf50[CPU:not_listed] |
| Sense — indirect ToF depth with dual-frequency phase unwrapping | 0 / 0 | 0 / 0 | itof_capture[CPU:not_listed] → itof_phase_amplitude[CPU:not_listed] → itof_unwrap_multifreq[CPU:not_listed] |
| Measure — coating thickness by spectral-domain OCT | 0 / 0 | 0 / 0 | oct_interferogram[CPU:not_listed] → oct_ascan[CPU:not_listed] → oct_layer_thickness[CPU:not_listed] |
| Optics — Malus's law through a linear polarizer (Mueller calculus) | 0 / 0 | 0 / 0 | mueller_element[CPU:not_listed] → mueller_apply[CPU:not_listed] → stokes_analyze[CPU:not_listed] |
| 3D — shape from polarization of a glossy dome (curvature from polarization images) | 0 / 0 | 0 / 0 | sfp_render[CPU:not_listed] → sfp_normals[CPU:not_listed] → sfp_disambiguate[CPU:not_listed] → slope_to_curvature[CPU:not_listed] |
| Optics — object-side telecentric lens: magnification and telecentricity error | 0 / 0 | 0 / 0 | telecentric_lens[CPU:not_listed] → telecentricity_error[CPU:not_listed] |
| Optics — irradiance and uniformity of a point LED over the field (illumination design) | 0 / 0 | 0 / 0 | light_source[CPU:not_listed] → irradiance_map[CPU:not_listed] → illumination_uniformity[CPU:not_listed] |
| Optics — peak wavelength of a blackbody source (Wien's law, spectral radiometry) | 0 / 0 | 0 / 0 | blackbody_spectrum[CPU:not_listed] → spectral_stats[CPU:not_listed] |
| Measure — overlay alignment from a moire mark (nm-scale shift) | 0 / 0 | 0 / 0 | moire_overlay_image[CPU:not_listed] → moire_mark_read[CPU:not_listed] |
| Measure — photoelastic retardance and principal-stress direction (polarization camera) | 0 / 0 | 0 / 0 | photoelastic_polarization_images[CPU:not_listed] → photoelastic_phase_estimate[CPU:not_listed] |
| Measure — height with a chromatic confocal probe (designed lens, calibration table) | 0 / 0 | 0 / 0 | chromatic_confocal_probe[CPU:not_listed] → chromatic_confocal_spectrum[CPU:not_listed] → chromatic_confocal_peaks[CPU:not_listed] → chromatic_confocal_readout[CPU:not_listed] |
| Sense — FMCW radar range and velocity of a target (range-Doppler map) | 0 / 0 | 0 / 0 | fmcw_beat_simulate[CPU:not_listed] → fmcw_window_apply[CPU:not_listed] → range_doppler_map[CPU:not_listed] → range_doppler_peaks[CPU:not_listed] |
| Sense — radar direction of arrival with a uniform linear array (beamforming) | 0 / 0 | 0 / 0 | fmcw_beat_simulate[CPU:not_listed] → beamform_doa[CPU:not_listed] |
| Sense — direct ToF distance from a TCSPC histogram (SPAD lidar pixel) | 0 / 0 | 0 / 0 | tcspc_simulate[CPU:not_listed] → tcspc_background_subtract[CPU:not_listed] → dtof_depth[CPU:not_listed] |
| 3D — flash lidar depth map from a SPAD histogram cube | 0 / 0 | 0 / 0 | dtof_cube_simulate[CPU:not_listed] → dtof_cube_depth[CPU:not_listed] |
| Preprocess — variance-stabilize a photon-limited image (Anscombe transform) | 0 / 0 | 0 / 0 | photon_sample[CPU:not_listed] → anscombe_transform[CPU:below_measured_size] |
| Measure — surface height at a pixel by white-light interferometry (CSI peak) | 0 / 0 | 0 / 0 | csi_signal_simulate[CPU:not_listed] → csi_peak_position[CPU:not_listed] |
| Measure — tilt of a flat measured by a coherence-scanning interferometer | 1 / 1 | 1 / 1 | csi_stack_simulate[CPU:not_listed] → csi_height_map[CPU:not_listed] → dem_slope[GPU] |
| Measure — distance by chromatic confocal sensor (spectral peak to height) | 0 / 0 | 0 / 0 | chromatic_confocal_simulate[CPU:not_listed] → chromatic_confocal_height[CPU:not_listed] |
| Sense — detect and photometer stars in a frame (aperture photometry) | 0 / 0 | 0 / 0 | synth_starfield[CPU:not_listed] → star_detect[CPU:not_listed] → aperture_photometry[CPU:not_listed] |
| Measure — seeing / PSF FWHM of point sources (Gaussian PSF fit) | 0 / 0 | 0 / 0 | synth_starfield[CPU:not_listed] → star_detect[CPU:not_listed] → psf_fit[CPU:not_listed] |
| Preprocess — stack N frames with sigma clipping (noise drops as 1/sqrt N) | 1 / 1 | 1 / 1 | sigma_clip_stack[GPU] → noise_sigma[CPU:not_listed] |
| Preprocess — reveal faint stars: cosmic-ray reject, register and stack dithered frames | 4 / 2 | 4 / 2 | synth_frame_series[CPU:not_listed] → cosmic_ray_reject_stack[GPU] → align_frames[CPU:not_listed] → sigma_clip_stack[GPU] → star_detect[CPU:not_listed] |
| 3D — depth of a plane from a plenoptic camera raw image (refocus stack, depth from focus) | 0 / 0 | 0 / 0 | lf_from_mla[CPU:not_listed] → lf_focal_stack[CPU:not_listed] → depth_from_focus[CPU:not_listed] |
| 3D — metric depth from a light field (refocus depth from focus, camera-array model) | 1 / 1 | 1 / 1 | lf_synthesize[CPU:not_listed] → lf_depth_from_focus[CPU:not_listed] → lf_disparity_to_depth[GPU] |
| 3D — metric depth from a light field (EPI structure-tensor slope, camera-array model) | 1 / 1 | 1 / 1 | lf_synthesize[CPU:not_listed] → lf_epi_slope[GPU] → lf_disparity_to_depth[GPU] |
| Measure — flow velocity from a PIV image pair (multipass cross-correlation) | 0 / 0 | 0 / 0 | piv_multipass[CPU:not_listed] → piv_to_velocity[CPU:not_listed] → piv_flow_magnitude[CPU:not_listed] |
| Measure — mean flow from a PIV image sequence (ensemble correlation) | 0 / 0 | 0 / 0 | piv_synth_sequence[CPU:not_listed] → piv_ensemble_correlate[CPU:not_listed] → piv_flow_magnitude[CPU:not_listed] |
| Measure — vorticity of a PIV vector field after outlier replacement | 0 / 0 | 0 / 0 | piv_outlier_mask[CPU:not_listed] → piv_replace_outliers[CPU:not_listed] → piv_vorticity[CPU:not_listed] |
| Measure — flow speed in m/s from PIV displacement (pixel size, frame interval) | 0 / 0 | 0 / 0 | piv_to_velocity[CPU:not_listed] → piv_flow_magnitude[CPU:not_listed] |
| Inspect — bearing outer-race defect frequency by envelope spectrum | 0 / 0 | 0 / 0 | synthesize_bearing_signal[CPU:not_listed] → envelope_spectrum[CPU:not_listed] |
| Measure — frequency response (gain) of a device from input / output noise (H1) | 0 / 0 | 0 / 0 | transfer_function[CPU:not_listed] |
| Sense — time difference of arrival between two microphones (GCC-PHAT) | 0 / 0 | 0 / 0 | gcc_delay[CPU:not_listed] |
| Measure — A-weighted equivalent sound level of a tone | 1 / 1 | 1 / 1 | apply_weighting[GPU] → equivalent_level[CPU:not_listed] |
| Sense — self-rotation of a compound eye from optic flow (fly motion vision) | 0 / 0 | 0 / 0 | fly_lamina_filter[CPU:not_listed] → fly_t4t5_field[CPU:not_listed] → fly_flow_from_directions[CPU:not_listed] → fly_egomotion_from_flow[CPU:not_listed] |
| Sense — motion direction from two photoreceptors (Reichardt correlator) | 0 / 0 | 0 / 0 | fly_emd_response[CPU:not_listed] |
| Sense — time to collision from the looming angle (tau) | 0 / 1 | 0 / 1 | fly_tau_from_expansion[GPU] |
| Inspect — specular highlight strength of a glossy part (dichromatic model) | 0 / 0 | 0 / 0 | dichromatic_render[CPU:not_listed] → specular_coefficient_map[CPU:below_measured_size] |
| Sense — degree of linear polarization of specular reflection (Fresnel) | 0 / 0 | 0 / 0 | sfp_render[CPU:not_listed] → polarization_dolp_map[CPU:not_listed] |
| 3D — curvature of a matte part by robust photometric stereo | 0 / 0 | 0 / 0 | photometric_stereo_robust[CPU:not_listed] → slope_to_curvature[CPU:not_listed] |
| Inspect — remove specular glare to read the body colour (dichromatic separation) | 0 / 0 | 0 / 0 | dichromatic_render[CPU:not_listed] → specular_diffuse_split[CPU:not_listed] |
| Measure — sub-pixel vibration amplitude from video (phase-based) | 1 / 1 | 1 / 1 | synthesize_translation[CPU:not_listed] → displacement_series[GPU] |
| Inspect — magnify a small vibration in video (motion magnification) | 0 / 1 | 0 / 1 | motion_magnify[GPU] |
| Measure — vibration SNR in a frequency band of a video | 0 / 0 | 0 / 0 | band_snr[CPU:not_listed] |
| Sense — time to collision with a wall from depth and ego motion | 1 / 1 | 1 / 1 | relative_motion[CPU:not_listed] → ttc_truth[GPU] |
| Sense — focus of expansion of the ego motion (heading point in the image) | 0 / 0 | 0 / 0 | relative_motion[CPU:not_listed] → foe_from_motion[CPU:not_listed] |
| Measure — RSS minimum safe following distance (responsibility-sensitive safety) | 0 / 0 | 0 / 0 | rss_params[CPU:not_listed] → rss_longitudinal_check[CPU:not_listed] |
| Measure — RSS minimum safe gap behind a braking lead car (rss_params -> rss_longitudinal_same) | 0 / 0 | 0 / 0 | rss_params[CPU:not_listed] → rss_longitudinal_same[CPU:not_listed] |
| Analyze — driver lateral wobble (Ornstein-Uhlenbeck mean reversion and noise) | 0 / 0 | 0 / 0 | lateral_wobble[CPU:not_listed] → ou_estimate[CPU:not_listed] |
| Inspect — peg-in-hole clearance ratio and jamming-free tilt (robot assembly) | 0 / 0 | 0 / 0 | peg_params[CPU:not_listed] → whitney_clearance[CPU:not_listed] |
| Sense — direction of arrival of two sources with an antenna array (MUSIC) | 0 / 0 | 0 / 0 | ula_snapshots[CPU:not_listed] → music_doa[CPU:not_listed] |
| Analyze — count polynomial roots inside a circle (argument principle) | 2 / 1 | 2 / 1 | cplx_contour_circle[CPU:not_listed] → cplx_poly_eval[GPU] → cplx_argument_principle[CPU:not_listed] |
| Measure — condition number of a measured covariance (anisotropy / ill-conditioning) | 0 / 0 | 0 / 0 | stat_covariance[CPU:not_listed] → mat_cond[CPU:not_listed] |
| Measure — principal axes of a scatter (covariance eigen-decomposition) | 0 / 0 | 0 / 0 | stat_covariance[CPU:not_listed] → mat_eigh[CPU:not_listed] |
| Sense — dominant vibration frequency after band-pass filtering | 0 / 0 | 0 / 0 | bandpass[CPU:not_listed] → signal_features[CPU:not_listed] |
| Measure — count zero crossings of a smoothed profile (1-D function) | 0 / 0 | 0 / 0 | smooth_funct_1d_gauss[CPU:below_measured_size] → zero_crossings_funct_1d[CPU:not_listed] |
| Measure — amplitude of a vibration via its Hilbert envelope | 1 / 1 | 1 / 1 | envelope[GPU] → rms[CPU:not_listed] |
| Inspect — process capability Cp / Cpk against spec limits | 0 / 0 | 0 / 0 | spc_capability[CPU:not_listed] |
| Inspect — X-bar / R control chart of subgrouped parts | 0 / 0 | 0 / 0 | spc_xbar_r[CPU:not_listed] |
| Inspect — variation-model defect detection against good samples | 1 / 1 | 1 / 1 | varmodel_fit[GPU] → varmodel_score[CPU:not_listed] |
| Inspect — probability of detection a50 of an NDT method (â vs a) | 0 / 0 | 0 / 0 | pod_ahat_fit[CPU:not_listed] → pod_from_ahat[CPU:not_listed] |
| Analyze — algebraic connectivity of a neuron ring (Laplacian spectrum) | 0 / 0 | 0 / 0 | graph_from_synapses[CPU:not_listed] → graph_laplacian_spectrum[CPU:not_listed] |
| Analyze — clusters of a connectome after pruning weak synapses | 0 / 0 | 0 / 0 | graph_from_synapses[CPU:not_listed] → graph_binarize[CPU:not_listed] → graph_components[CPU:not_listed] |
| Measure — shortest route on a weighted network (slime-mould transport) | 0 / 0 | 0 / 0 | graph_physarum_path[CPU:not_listed] |
| Analyze — count directed feedback triangles in a network | 0 / 0 | 0 / 0 | graph_cycle3[CPU:not_listed] |
| Analyze — response-surface optimum of a central composite experiment | 0 / 0 | 0 / 0 | doe_central_composite[CPU:not_listed] → rsm_fit[CPU:not_listed] |
| Analyze — global sensitivity (Sobol' indices) of a model | 0 / 0 | 0 / 0 | doe_saltelli[CPU:not_listed] → sens_sobol[CPU:not_listed] |
| Analyze — principal components and explained variance of multivariate data | 0 / 0 | 0 / 0 | mv_pca[CPU:not_listed] |
| Inspect — score a segmentation split error (variation of information) | 0 / 0 | 0 / 0 | seg_inject_split[CPU:not_listed] → seg_variation_of_information[CPU:not_listed] |
| Inspect — detect a scene cut in a noisy video stream | 1 / 1 | 1 / 1 | temporal_bilateral[GPU] → scene_cut_detection[CPU:below_measured_size] |
| Inspect — moving object mask in a flickering video (deflicker + background model) | 0 / 0 | 0 / 0 | deflicker[CPU:below_measured_size] → running_gaussian_foreground[CPU:not_listed] |
| Calibrate — camera gain from a captured test chart (simulation calibration) | 0 / 0 | 0 / 0 | simcal_model[CPU:not_listed] → simcal_observe[CPU:not_listed] → simcal_fit[CPU:not_listed] → simcal_report[CPU:not_listed] |
| Analyze — attention as a key-value lookup (RMSNorm → scores → softmax → mix) | 0 / 0 | 0 / 0 | rms_norm[CPU:not_listed] → attention_scores[CPU:not_listed] → attention_weights[CPU:not_listed] → attention_apply[CPU:not_listed] |
| Measure — observed order of convergence of a grid study (GCI) | 0 / 0 | 0 / 0 | conv_observed_order[CPU:not_listed] |
| Measure — fixed point of an iteration with convergence proof (Anderson) | 0 / 0 | 0 / 0 | iterate_fixed_point[CPU:not_listed] |
| Measure — bore centre and radius from a sub-pixel contour (circle fit per XLD contour) | 0 / 0 | 0 / 0 | threshold_sub_pix[CPU:not_listed] → fit_circle_xld[CPU:not_listed] |
| Inspect — count touching parts as watershed basins (one label per object) | 3 / 3 | 3 / 3 | threshold[GPU] → distance_transform[GPU] → invert_image[GPU] → hierarchical_watershed[CPU:not_listed] |
| Segment — marker-controlled watershed inside a mask (two touching parts, background kept out) | 3 / 2 | 3 / 2 | threshold[GPU] → blob_label[CPU:below_measured_size] → sobel_amp[GPU] → invert_image[GPU] → blob_split[CPU:not_listed] |
| Measure — unwrap an off-centre ring about its centre and read its radius | 1 / 1 | 1 / 1 | polar_unwrap[CPU:not_listed] → img_to_projection_profile[GPU] |
| Inspect — count bright and dim inclusions in a grey volume (threshold, then count) | 1 / 1 | 1 / 1 | vol_threshold[GPU] → vol_count[CPU:not_listed] |
| Sense — bearing of a sound source from a microphone pair (time difference of arrival) | 0 / 0 | 0 / 0 | tdoa_bearing[CPU:not_listed] |
| Measure — feed-mark wavelength of a machined surface from its areal PSD peak | 1 / 1 | 1 / 1 | surface_psd[GPU] → spectral_stats[CPU:not_listed] |
| Measure — period and direction of a stripe / grating texture (strongest 2-D FFT peak) | 0 / 0 | 0 / 0 | wave_dominant_frequency[CPU:not_listed] |
| 3D — find a known part's 6-DoF pose in a scene cloud (PPF surface matching) | 0 / 0 | 0 / 0 | find_surface_pose[CPU:not_listed] |
| Accept — probing error of a 3-D sensor on a calibrated sphere (VDI/VDE 2634-2 idea: PF and PS) | 0 / 0 | 0 / 0 | sphere_probing_error[CPU:not_listed] |
| Register — sub-pixel shift between two images by ECC (enhanced correlation coefficient) | 0 / 0 | 0 / 0 | register_ecc[CPU:not_listed] |
| Read — an EAN-13 (JAN) barcode label, including a tilted and noisy one | 0 / 0 | 0 / 0 | read_barcode1d[CPU:not_listed] |
| Sense — degree of linear polarization map from four analyzer angles (0/45/90/135) | 0 / 0 | 0 / 0 | polarization_dolp_map[CPU:not_listed] |
| Inspect — glossy (specular) area from polarization: DoLP map, threshold, area fraction | 2 / 1 | 1 / 1 | polarization_dolp_map[CPU:not_listed] → threshold[GPU] → area_frac[GPU] |
| Measure — wrapped phase from 4-step phase-shifted fringes | 0 / 1 | 0 / 1 | wrapped_phase[GPU] |
| 3D — height map from 4-step phase-shift fringes (decode, unwrap, scale) | 0 / 0 | 0 / 0 | decode_fringe[CPU:not_listed] |

理由の語: `not_listed` = GPU 経路が無い / `chain_only` = 鎖の枠だけの経路で隣が GPU でない / `crossover` = 損益分岐。往復 = GPU の区間ごとに送り 1 回・戻し 1 回。
