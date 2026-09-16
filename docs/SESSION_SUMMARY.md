# Session Summary (auto-generated)

> 自動生成: `libexec/raptor-auto-summary` (Stop hook)
> 次回 ccr 起動時に CLAUDE.md SESSION START で自動的に読み取られる。

- **最終更新**: 2026-09-16 13:45:08
- **プロジェクト**: `C:/dev/projects/imgevolve`
- **ブランチ**: `master`

## 直近の git log

```
d97049633 空フレームが全面誤検出に化ける不具合を 4 クラス直した(丸め屑が正規化で構造になる)
1a03dfcae 548 op すべてに第 2 実装を当て終えた —— 二重実装が相関故障を下げる実証つき
ad4360b3c triage が「壊れた第 2 実装」を「正規化の穴」と誤分類していた(偽の仕様穴 5 件)
d1e2ad7bb 無人実行が 1 本の不良 C で死んでいた —— 15 分間「走っている」と思い込んでいた
216162db0 CI を赤にしていた 3 件を直した —— 的を絞ったテストだけ見ていて 10 コミット気づかなかった
0a561655a 失敗した op の記録が消えていた —— 「失敗が不可視」は「発見ゼロ」と同じ形の事故
fb5fd5303 連結性の測定器: 陽性対照は通したが、**収穫はほぼゼロ**だった(負の結果として残す)
99041d89f 訳 5 言語にも同じ誤りが載っていた(「外周だけ」)—— 指紋の門が拾った
842585418 文書の誤りを 1 件訂正: 「外周だけを残す」は嘘だった(穴の輪郭も返る)
f5865b6fe triage が「もう塞がっている穴」を畳むようにした
```

## 現在の git status

```
M backends_auto.py
 M backends_halcon_ext.py
 M docs/DESIGN_NOTES.de.md
 M docs/DESIGN_NOTES.en.md
 M docs/DESIGN_NOTES.ko.md
 M docs/DESIGN_NOTES.md
 M docs/DESIGN_NOTES.tw.md
 M docs/DESIGN_NOTES.zh.md
 M docs/op_blank_frame.json
 M docs/ops/2d/artificial_life/alife_reaction_bz.md
 M docs/ops/2d/artistic/xcv_stylization.md
 M docs/ops/2d/augmentation/aug_cutout.md
 M docs/ops/2d/augmentation/aug_vignette.md
 M docs/ops/2d/domain/it_crop_domain.md
 M docs/ops/2d/edges/cv_laplacian.md
 M docs/ops/2d/edges/cv_min_eigen.md
 M docs/ops/2d/edges/cv_precorner.md
 M docs/ops/2d/edges/cv_scharr.md
 M docs/ops/2d/edges/derivate_gauss.md
 M docs/ops/2d/edges/diff_of_gauss.md
 M docs/ops/2d/edges/dog.md
 M docs/ops/2d/edges/f2_topographic.md
 M docs/ops/2d/edges/frei_amp.md
 M docs/ops/2d/edges/kirsch_amp.md
 M docs/ops/2d/edges/kirsch_dir.md
 M docs/ops/2d/edges/laplace.md
 M docs/ops/2d/edges/log.md
 M docs/ops/2d/edges/points_foerstner.md
 M docs/ops/2d/edges/prewitt_amp.md
 M docs/ops/2d/edges/prewitt_mag.md
 M docs/ops/2d/edges/roberts.md
 M docs/ops/2d/edges/roberts_mag.md
 M docs/ops/2d/edges/robinson_amp.md
 M docs/ops/2d/edges/robinson_dir.md
 M docs/ops/2d/edges/sk_dog.md
 M docs/ops/2d/edges/sk_farid.md
 M docs/ops/2d/edges/sk_scharr.md
 M docs/ops/2d/edges/sobel_amp.md
 M docs/ops/2d/edges/sobel_mag.md
 M docs/ops/2d/edges/tf_phase_congruency.md
 M docs/ops/2d/edges/xkor_dog.md
 M docs/ops/2d/edges/xkor_gftt.md
 M docs/ops/2d/edges/xkor_hessian.md
 M docs/ops/2d/edges/xkor_laplacian.md
 M docs/ops/2d/edges/xpil_contour.md
 M docs/ops/2d/edges/xpil_find_edges.md
 M docs/ops/2d/edges/xsk2_inv_gauss_grad.md
 M docs/ops/2d/edges/xsk3_corner_fast.md
 M docs/ops/2d/edges/xsk3_corner_moravec.md
 M docs/ops/2d/edges/xsk_hessian_eig.md
 M docs/ops/2d/edges/xsp_gauss_grad_mag.md
 M docs/ops/2d/edges/xwt_hf_reconstruct.md
 M docs/ops/2d/extra/xsitk_connected_threshold.md
 M docs/ops/2d/extra/xsitk_maxentropy_thresh.md
 M docs/ops/2d/extra/xsitk_moments_thresh.md
 M docs/ops/2d/features/hough_circle_trans.md
 M docs/ops/2d/features/hough_line_trans.md
 M docs/ops/2d/filtering/tf_gradient_domain_reintegrate.md
 M docs/ops/2d/frequency/fft_generic.md
 M docs/ops/2d/frequency/fft_image.md
 M docs/ops/2d/frequency/power_byte.md
 M docs/ops/2d/frequency/power_ln.md
 M docs/ops/2d/frequency/power_real.md
 M docs/ops/2d/frequency/rft_generic.md
 M docs/ops/2d/frequency/sk_butterworth.md
 M docs/ops/2d/frequency/xsk2_radon.md
 M docs/ops/2d/frequency/xsp_dct.md
 M docs/ops/2d/frequency/xwt_mra_component.md
 M docs/ops/2d/frequency/xwt_subband_tile.md
 M docs/ops/2d/geometry/polar_trans_image.md
 M docs/ops/2d/geometry/polar_trans_image_ext.md
 M docs/ops/2d/geometry/polar_trans_image_inv.md
 M docs/ops/2d/gray/monotony.md
 M docs/ops/2d/gray/sk_adapthist.md
 M docs/ops/2d/gray/sk_autolevel.md
 M docs/ops/2d/gray/xsk3_integral_image.md
 M docs/ops/2d/gray/xsk3_rank_equalize.md
 M docs/ops/2d/halcon_ext/hx_close_edges.md
 M docs/ops/2d/halcon_ext/hx_close_edges_length.md
 M docs/ops/2d/halcon_ext/hx_detect_edge_segments.md
 M docs/ops/2d/halcon_ext/hx_disparity_to_xyz.md
 M docs/ops/2d/halcon_ext/hx_fit_surface1.md
 M docs/ops/2d/halcon_ext/hx_fit_surface2.md
 M docs/ops/2d/halcon_ext/hx_full_domain.md
 M docs/ops/2d/halcon_ext/hx_gabor.md
 M docs/ops/2d/halcon_ext/hx_gen_empty_region.md
 M docs/ops/2d/halcon_ext/hx_get_domain.md
 M docs/ops/2d/halcon_ext/hx_nonmax_dir.md
 M docs/ops/2d/halcon_ext/hx_plane_deviation.md
 M docs/ops/2d/halcon_ext/hx_shade_height_field.md
 M docs/ops/2d/macro/macro_edge.md
 M docs/ops/2d/morphology/bothat.md
 M docs/ops/2d/morphology/cv_blackhat.md
 M docs/ops/2d/morphology/cv_gradient.md
 M docs/ops/2d/morphology/cv_tophat.md
 M docs/ops/2d/morphology/f2_gray_skeleton.md
 M docs/ops/2d/morphology/gray_bothat.md
 M docs/ops/2d/morphology/gray_tophat.md
 M docs/ops/2d/morphology/morph_grad.md
 M docs/ops/2d/morphology/tophat.md
 M docs/ops/2d/morphology_markers/xmh_regmin.md
 M docs/ops/2d/rank/gray_range_rect.md
 M docs/ops/2d/rank/xkor_median.md
 M docs/ops/2d/restoration/xsk_richardson_lucy.md
 M docs/ops/2d/segment/sg_felzenszwalb.md
 M docs/ops/2d/segment/sg_gmm_segment.md
 M docs/ops/2d/segment/sg_kmeans_intensity.md
 M docs/ops/2d/segment/sg_region_growing_seeded.md
 M docs/ops/2d/segment/sg_watershed_gradient.md
 M docs/ops/2d/segmentation/adaptive_gauss_thresh.md
 M docs/ops/2d/segmentation/auto_threshold.md
 M docs/ops/2d/segmentation/bin_threshold.md
 M docs/ops/2d/segmentation/binary_threshold.md
 M docs/ops/2d/segmentation/canny.md
 M docs/ops/2d/segmentation/cv_adaptive_gauss.md
 M docs/ops/2d/segmentation/cv_adaptive_mean.md
 M docs/ops/2d/segmentation/cv_canny.md
 M docs/ops/2d/segmentation/dyn_threshold.md
 M docs/ops/2d/segmentation/edges_image.md
 M docs/ops/2d/segmentation/local_threshold.md
 M docs/ops/2d/segmentation/pouring.md
 M docs/ops/2d/segmentation/segment_image_mser.md
 M docs/ops/2d/segmentation/sk_canny.md
 M docs/ops/2d/segmentation/sk_felzenszwalb.md
 M docs/ops/2d/segmentation/sk_li.md
 M docs/ops/2d/segmentation/sk_local_maxima.md
 M docs/ops/2d/segmentation/sk_niblack.md
 M docs/ops/2d/segmentation/sk_otsu.md
 M docs/ops/2d/segmentation/sk_yen.md
 M docs/ops/2d/segmentation/watersheds.md
 M docs/ops/2d/segmentation/watersheds_threshold.md
 M docs/ops/2d/segmentation/xcv_grabcut.md
 M docs/ops/2d/segmentation/xkor_canny.md
 M docs/ops/2d/segmentation/xmh_bernsen.md
 M docs/ops/2d/segmentation/xsk2_h_maxima.md
 M docs/ops/2d/segmentation/xsk3_h_minima.md
 M docs/ops/2d/segmentation/xsk3_peak_local_max.md
 M docs/ops/2d/segmentation/xsk3_threshold_local_median.md
 M docs/ops/2d/segmentation/xsk_flood.md
 M docs/ops/2d/segmentation/xsk_random_walker.md
 M docs/ops/2d/segmentation/zero_crossing.md
 M docs/ops/2d/self_similarity/xmh_selfmatch.md
 M docs/ops/2d/smoothing/sk_rolling_ball.md
 M docs/ops/2d/smoothing/xkor_motion_blur.md
 M docs/ops/2d/smoothing/xsp_wiener.md
 M docs/ops/2d/tactile/tac_contact_mask.md
 M docs/ops/2d/tactile/tac_height_from_shading.md
 M docs/ops/2d/tactile/tac_pressure_proxy.md
 M docs/ops/2d/tactile/tac_shear_field.md
 M docs/ops/2d/tactile/tac_surface_normal.md
 M docs/ops/2d/texture/deviation_image.md
 M docs/ops/2d/texture/entropy_image.md
 M docs/ops/2d/texture/f2_symmetry.md
 M docs/ops/2d/texture/gabor.md
 M docs/ops/2d/texture/gen_gabor.md
 M docs/ops/2d/texture/sk_entropy.md
 M docs/ops/2d/texture/sk_frangi.md
 M docs/ops/2d/texture/sk_hessian.md
 M docs/ops/2d/texture/sk_lbp.md
 M docs/ops/2d/texture/sk_meijering.md
 M docs/ops/2d/texture/std_filter.md
 M docs/ops/2d/texture/texture_laws.md
 M docs/ops/2d/texture/tf_census_transform.md
 M docs/ops/2d/texture/tf_rank_transform.md
 M docs/ops/2d/texture/xsk2_hog.md
 M docs/ops/2d/texture/xsk_meijering.md
 M docs/ops/2d/texture/xsk_sato.md
 M docs/ops/2d/texture/xsk_struct_coherence.md
 M docs/ops/2d/tomography/tm_backproject_unfiltered.md
 M docs/ops/2d/tomography/tm_fbp_reconstruct.md
 M docs/ops/2d/tomography/tm_radon_forward.md
 M docs/ops/2d/tomography/tm_sart_reconstruct.md
 M docs/ops/2d/transform/tf_radon_sinogram.md
 M docs/ops/2d/transform/xmh_daubechies.md
 M docs/ops/2d/transform/xmh_haar.md
 M ops.py
 M tests/test_blank_frame_is_stable.py
 M tools/impl2/blank_probe.py
 M tools/impl2/triage.py
 M tools/opdocs.py
?? tests/test_op_blank_frame_documented.py
```

## 直近 2 時間に変更されたファイル

```
13:44 .hypothesis/constants/001b4b7aa3c0a547
13:44 .hypothesis/constants/64f0422ef5a2cd8d
13:44 .hypothesis/constants/cb00786e17a13171
13:44 .hypothesis/constants/ff410dcf11915af1
13:44 .pytest_cache/v/cache/nodeids
13:44 docs/ops/dem/visibility/dem_viewshed.md
13:44 docs/ops/dem/visibility/dem_sky_view_factor.md
13:44 docs/ops/dem/visibility/dem_horizon_angle.md
13:44 docs/ops/dem/geodesy/dem_geodetic_slope.md
13:44 docs/ops/dem/geodesy/dem_geodetic_to_ecef.md
13:44 docs/ops/dem/geodesy/dem_geocentric_grid.md
13:44 docs/ops/dem/geodesy/dem_ecef_to_geodetic.md
13:44 docs/ops/dem/geodesy/dem_earth_curvature_drop.md
13:44 docs/ops/dem/geodesy/dem_cell_size_webmercator.md
13:44 docs/ops/dem/shading/dem_hillshade.md
```

---

> このファイルは毎ターン自動上書きされます。**手動で書いた内容は失われます。**
> 永続化したいメモは `docs/PROGRESS.md`、`docs/next_plan.md`、または `docs/NOTES.md` を使ってください。
