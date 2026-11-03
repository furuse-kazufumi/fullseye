# 機械的 GPU 化の掃引 (2026-11-02)

GPU 向き op(`gpu_tier` = required / suitable)2127 件を、1 件ずつ手書きせず既存の numpy/scipy 実装のまま CuPy 配列で走らせて採点した結果。

`tools/gpu_auto_sweep.py` の実測から `tools/gpu_auto_sweep.py report` が生成する。手で直さない。

## 方式

CuPy 13.6.0 + PyTorch 2.11.0+cu128 を同じプロセスで使い(DLPack の往復を確認)、`gpu_shadow.py` がプロジェクトのソースを別の名前空間でもう一度実行し、その中の `numpy` / `scipy` だけを CuPy へ向ける。大域の差し替えはしないので既定の CPU 経路は変わらない。CuPy に無い関数は CPU へ転送して実行し、回数を数える(速さの判定で落ちる)。乱数は numpy のものを使い、CPU と同じ系列を GPU へ転送する。比較の詳細は `docs/perf/gpu_auto_method_compare_2026-11-02.json`。

## 判定

- 一致: 同じ入力・同じ種で CPU と GPU を実行し、内部の最大差が出力の振れ幅の 5e-03 未満。端(4 画素以上)は比べない。NaN の位置も一致を要求する。
- 入力は構造のある合成画像(`op_probe` の円・矩形・斜めエッジ、チャープ信号など)を先頭に置く。出力が定数の op は一致と数えない(判定不能)。
- 倍率: 実寸(画像 2048²、体積 256³、信号 2²⁰、行列 1024²)で 1 回あたりの時間の比。GPU 側は転送 → 計算 → 転送(`.get()` が同期)を含み、CuPy のカーネルコンパイルは準備運転で除く。CPU 2 回、GPU 最大 3 回の最小値。バッチの融合は無い(1 枚ずつ)ので、N 枚の倍率も同じ値になる。CPU の基準線は他の作業と同時に測ったので、倍率 3 以上の op は1 本ずつ測り直し、速い方の時間を使った(倍率が低く出る向き)。GPU の時間も他の作業と同時に測ることがある。実寸の比較は出力を間引いた標本で行う。
- 採用: 一致かつ 5.0 倍以上、かつ Python 行数が入力に比例しない。
- CPU の基準線はこのリポジトリの実装そのもので、多くは 1 スレッドで走る。`FULLSEYE_FAST` の cv2 版やタイル分割の並列は使っていないので、最速の CPU 実装との比ではない。
- Python ループ律速: 入力を 2 倍にしたときの増分が 0.05 行/要素 以上(2048² で 20 万行)。固定形の入力は 1000 要素以上に限り 1 回の 行数/要素数 ≥ 0.5。

## 全件の分類

| 分類 | 件数 |
|---|---:|
| 採用(一致 + 転送込み 5 倍以上) | 507 |
| 常駐前提で採用(単独 1 回は 5 倍未満、GPU に載せたままの連続処理で 5 倍以上) | 120 |
| パイプライン常駐可(単独は 5 倍未満、GPU に載せたままの連続処理で 1 倍以上 5 倍未満。単独では採用しない) | 37 |
| 一致したが遅い(5 倍未満) | 331 |
| 一致したが実寸の入力を作れない(固定形の入力) | 444 |
| 不一致 | 48 |
| 判定不能(出力が定数) | 145 |
| 例外(CuPy 側の不足・型の混在) | 48 |
| 包み(cv2 / skimage / PIL が本体) | 184 |
| Python ループが律速 | 67 |
| 測れなかった | 196 |
| **合計** | **2127** |

例外と未計測の理由の内訳:

| 分類 | 理由 | 件数 |
|---|---|---:|
| exception | value_error | 13 |
| exception | type_error | 10 |
| exception | implicit_numpy | 9 |
| exception | gpu_timeout | 7 |
| exception | numpy_cupy_mix | 5 |
| exception | unhashable_array | 4 |
| mismatch | rel | 37 |
| mismatch | at_real_size | 9 |
| mismatch | value at .pairs[2] | 1 |
| mismatch | at_full_resolution | 1 |
| unmeasured | cpu_exception | 102 |
| unmeasured | no_backend | 47 |
| unmeasured | no_probe | 35 |
| unmeasured | cpu_over_limit_at_real_size | 10 |
| unmeasured | timeout | 2 |
| wrapper | skimage | 108 |
| wrapper | cv2 | 60 |
| wrapper | PIL | 16 |

## 採用 op の実測倍率

| op | 族 | 入力 | CPU | GPU(転送込み) | 倍率 | 内部差(比) | CPU 退避 |
|---|---|---|---:|---:|---:|---:|---:|
| `phase_congruency_pc` | perceptual | 2048×2048 | 21.83 s | 71 ms | 308.8 | 1.5e-13 | 0 |
| `ph_reaction_diffusion` | physics | 2048×2048 | 14.16 s | 52 ms | 271.6 | 0.0e+00 | 0 |
| `dolp_to_zenith` | shape_from_polarization | 2048×2048 | 50.29 s | 200 ms | 251.0 | 3.6e-16 | 0 |
| `ph_mean_curvature_motion` | physics | 2048×2048 | 28.19 s | 113 ms | 250.6 | 0.0e+00 | 0 |
| `bump_normals_fbm` | terrain | 2048×2048×3 | 36.30 s | 147 ms | 246.4 | 0.0e+00 | 1 |
| `curvature_flow` | contour | 2048×2048 | 20.93 s | 89 ms | 234.6 | 3.6e-12 | 0 |
| `alife_curvature_flow` | artificial-life | 2048×2048 | 13.94 s | 60 ms | 233.0 | 0.0e+00 | 0 |
| `ph_coherence_enhancing_diffusion` | physics | 2048×2048 | 26.24 s | 113 ms | 232.7 | 0.0e+00 | 0 |
| `dc_structure_texture` | decomposition | 2048×2048 | 29.37 s | 128 ms | 229.7 | 0.0e+00 | 0 |
| `dc_texture_residual` | decomposition | 2048×2048 | 23.50 s | 107 ms | 219.5 | 0.0e+00 | 0 |
| `alife_gray_scott` | artificial-life | 2048×2048 | 8.10 s | 37 ms | 218.0 | 0.0e+00 | 0 |
| `riesz_displacement_series` | motion | 8×512×512 | 3.17 s | 15 ms | 204.8 | 1.9e-13 | 0 |
| `alife_turing` | artificial-life | 2048×2048 | 6.87 s | 38 ms | 179.4 | 0.0e+00 | 0 |
| `esdf` | occupancy | 256×256×256 | 10.98 s | 61 ms | 179.3 | 0.0e+00 | 0 |
| `vol_frangi` | feature | 256×256×256 | 33.92 s | 191 ms | 177.6 | 8.0e-15 | 0 |
| `ridge_readout` | reservoir | 1024×1024 | 2.84 s | 16 ms | 173.3 | 9.0e-16 | 0 |
| `level_set_reinit` | contour | 2048×2048 | 18.30 s | 113 ms | 161.5 | 2.3e-17 | 0 |
| `displacement_series` | measure | 8×512×512 | 7.19 s | 45 ms | 159.6 | 4.8e-14 | 0 |
| `iv_backproject_superres` | restoration | 2048×2048 | 4.18 s | 27 ms | 154.0 | 2.9e-16 | 0 |
| `medial_axis_points` | medial | 256×256×256 | 2.74 s | 18 ms | 153.3 | 0.0e+00 | 0 |
| `ph_total_variation_flow` | physics | 2048×2048 | 9.30 s | 65 ms | 143.6 | 0.0e+00 | 0 |
| `backproject_sinogram` | reconstruct | 2048×2048 | 185.86 s | 1.32 s | 141.0 | 1.8e-16 | 1 |
| `filtered_backprojection` | reconstruct | 2048×2048 | 216.59 s | 1.55 s | 139.4 | 3.0e-15 | 1 |
| `vol_distance_transform` | medial | 256×256×256 | 6.85 s | 50 ms | 136.7 | 0.0e+00 | 0 |
| `coherence_enhancing_diff` | smoothing | 2048×2048 | 3.87 s | 29 ms | 133.2 | 5.7e-17 | 0 |
| `ph_heat_flow` | physics | 2048×2048 | 3.42 s | 27 ms | 128.0 | 0.0e+00 | 0 |
| `alife_life_step` | artificial-life | 2048×2048 | 3.30 s | 27 ms | 123.8 | 0.0e+00 | 0 |
| `mean_sp` | rank | 2048×2048 | 2.03 s | 17 ms | 119.4 | 0.0e+00 | 0 |
| `macro_edge` | macro | 2048×2048 | 4.88 s | 41 ms | 119.0 | 0.0e+00 | 0 |
| `tf_phase_congruency` | edges | 2048×2048 | 3.42 s | 29 ms | 117.6 | 6.0e-14 | 0 |
| `alife_cyclic_ca` | artificial-life | 2048×2048 | 4.97 s | 44 ms | 111.7 | 0.0e+00 | 0 |
| `sigma_clip_stack` | stack | 2048×2048 | 7.22 s | 65 ms | 111.0 | 2.6e-16 | 0 |
| `render_volume_projection` | render | 256×256×256 | 2.04 s | 19 ms | 106.1 | 0.0e+00 | 0 |
| `alife_sandpile` | artificial-life | 2048×2048 | 4.23 s | 41 ms | 104.2 | 0.0e+00 | 0 |
| `rank_image` | rank | 2048×2048 | 1.38 s | 13 ms | 102.6 | 0.0e+00 | 0 |
| `expand_gray` | grow | 2048×2048 | 47.52 s | 471 ms | 100.9 | 0.0e+00 | 0 |
| `vol_sato` | feature | 256×256×256 | 17.50 s | 174 ms | 100.8 | 5.1e-14 | 0 |
| `trimmed_mean` | rank | 2048×2048 | 1.92 s | 19 ms | 100.7 | 0.0e+00 | 0 |
| `eliminate_min_max` | rank | 2048×2048 | 1.40 s | 14 ms | 99.2 | 0.0e+00 | 0 |
| `ph_perona_malik` | physics | 2048×2048 | 5.40 s | 54 ms | 99.2 | 0.0e+00 | 0 |
| `deflectometry_render` | deflectometry | 2048×2048 | 10.39 s | 105 ms | 99.1 | 2.3e-14 | 0 |
| `alife_perona_malik` | artificial-life | 2048×2048 | 4.24 s | 43 ms | 98.1 | 0.0e+00 | 0 |
| `macro_denoise` | macro | 2048×2048 | 7.19 s | 75 ms | 96.3 | 2.3e-16 | 0 |
| `motion_magnify` | magnify | 8×512×512 | 6.01 s | 63 ms | 94.7 | 4.5e-12 | 0 |
| `percentile` | rank | 2048×2048 | 1.98 s | 21 ms | 93.9 | 0.0e+00 | 0 |
| `retardation_unwrap_multiwavelength` | photoelastic | 2048×2048 | 14.21 s | 163 ms | 87.4 | 1.3e-16 | 0 |
| `vol_local_maxima` | feature | 256×256×256 | 1.23 s | 14 ms | 87.3 | 0.0e+00 | 0 |
| `sensor_fingerprint` | sensor | 2048×2048 | 3.01 s | 35 ms | 85.2 | 5.3e-13 | 0 |
| `fp_capture` | fpm | 2048×2048 | 148.86 s | 1.76 s | 84.5 | 1.6e-16 | 338 |
| `phase_displacement` | measure | 8×512×512 | 3.87 s | 46 ms | 83.3 | 3.9e-10 | 0 |
| `tac_height_from_shading` | tactile | 2048×2048 | 1.59 s | 20 ms | 81.3 | 2.4e-15 | 0 |
| `macro_binarize` | macro | 2048×2048 | 5.06 s | 63 ms | 80.7 | 9.2e-16 | 0 |
| `patch_features` | anomaly_patch | 2048×2048 | 7.65 s | 95 ms | 80.7 | 3.6e-13 | 0 |
| `riesz_displacement` | motion | 8×512×512 | 2.09 s | 26 ms | 79.8 | 2.0e-11 | 0 |
| `median_weighted` | rank | 2048×2048 | 1.36 s | 17 ms | 79.6 | 0.0e+00 | 0 |
| `vx_warp_affine` | geometry | 2048×2048 | 767 ms | 10 ms | 79.5 | 0.0e+00 | 0 |
| `median_separate` | rank | 2048×2048 | 1.43 s | 18 ms | 79.1 | 0.0e+00 | 0 |
| `surface_psd` | measure | 2048×2048 | 467 ms | 6 ms | 78.7 | 1.3e-15 | 0 |
| `median_rect` | rank | 2048×2048 | 1.20 s | 15 ms | 78.5 | 0.0e+00 | 0 |
| `median` | rank | 2048×2048 | 1.32 s | 17 ms | 77.9 | 0.0e+00 | 0 |
| `punch_pressure` | tactorque | 1024×1024 | 568 ms | 7 ms | 77.9 | 0.0e+00 | 0 |
| `riesz_motion_magnify` | motion | 8×512×512 | 1.63 s | 21 ms | 77.3 | 1.3e-12 | 0 |
| `fbm_height` | terrain | 2048×2048 | 3.22 s | 43 ms | 75.3 | 3.1e-16 | 0 |
| `dc_retinex` | decomposition | 2048×2048 | 7.21 s | 97 ms | 74.2 | 1.3e-15 | 0 |
| `bootstrap_std_error` | texture | 2048×2048 | 80.33 s | 1.09 s | 73.6 | 3.5e-16 | 2 |
| `rank_rect` | rank | 2048×2048 | 1.25 s | 18 ms | 69.2 | 0.0e+00 | 0 |
| `bandpass_image` | frequency | 2048×2048 | 1.01 s | 15 ms | 68.0 | 2.8e-14 | 0 |
| `dc_homomorphic` | decomposition | 2048×2048 | 1.05 s | 16 ms | 66.5 | 4.7e-15 | 0 |
| `orientation_code` | code | 2048×2048 | 443 ms | 7 ms | 66.3 | 0.0e+00 | 0 |
| `deform_ffd` | deformation | 2048×2048 | 1.83 s | 28 ms | 66.1 | 1.4e-16 | 0 |
| `median_image` | rank | 2048×2048 | 1.47 s | 22 ms | 66.0 | 0.0e+00 | 0 |
| `tac_pressure_proxy` | tactile | 2048×2048 | 4.79 s | 74 ms | 64.8 | 5.6e-15 | 0 |
| `scale_select_std` | texture | 2048×2048 | 1.22 s | 19 ms | 64.7 | 7.0e-07 | 0 |
| `sg_gmm_segment` | segment | 2048×2048 | 27.22 s | 421 ms | 64.6 | 0.0e+00 | 0 |
| `anisotropic_diffusion` | smoothing | 2048×2048 | 2.19 s | 34 ms | 64.3 | 5.7e-17 | 0 |
| `alife_lenia` | artificial-life | 2048×2048 | 2.81 s | 44 ms | 63.5 | 4.3e-15 | 0 |
| `bilateral` | smoothing | 2048×2048 | 2.32 s | 37 ms | 63.0 | 0.0e+00 | 0 |
| `dual_rank` | rank | 2048×2048 | 1.54 s | 25 ms | 62.3 | 0.0e+00 | 0 |
| `tf_gradient_domain_reintegrate` | filtering | 2048×2048 | 840 ms | 14 ms | 59.4 | 6.5e-14 | 0 |
| `hatch_field` | npr | 2048×2048 | 1.40 s | 24 ms | 59.0 | 8.4e-11 | 0 |
| `filled_polygon` | shape | 2048×2048 | 1.42 s | 24 ms | 58.3 | 0.0e+00 | 0 |
| `vol_hessian_blobness` | feature | 256×256×256 | 6.08 s | 106 ms | 57.5 | 8.8e-14 | 0 |
| `cplx_poly_eval` | complex | 1048576 | 1.17 s | 21 ms | 55.2 | 1.5e-14 | 0 |
| `dem_flow_direction` | hydrology | 2048×2048 | 482 ms | 9 ms | 52.4 | 0.0e+00 | 0 |
| `psf_to_mtf` | imaging | 2048×2048 | 437 ms | 8 ms | 51.8 | 5.2e-06 | 0 |
| `winkler_polish_run` | polish | 2048×2048 | 8.62 s | 171 ms | 50.3 | 7.2e-16 | 0 |
| `xsp_wiener` | smoothing | 2048×2048 | 624 ms | 13 ms | 48.3 | 3.5e-15 | 0 |
| `strain_from_displacement` | solid | 2048×2048 | 1.54 s | 32 ms | 48.2 | 1.1e-10 | 0 |
| `azimuthal_integrate` | pxrd | 2048×2048 | 3.28 s | 74 ms | 44.3 | 2.5e-15 | 0 |
| `tac_contact_mask` | tactile | 2048×2048 | 6.16 s | 140 ms | 44.0 | 0.0e+00 | 2 |
| `banding_map` | gray | 2048×2048 | 558 ms | 13 ms | 43.2 | 0.0e+00 | 0 |
| `alife_dla` | artificial-life | 2048×2048 | 989 ms | 23 ms | 42.4 | 0.0e+00 | 0 |
| `rotate_image` | geometry | 2048×2048 | 552 ms | 13 ms | 41.6 | 2.3e-16 | 0 |
| `iv_motion_deblur` | restoration | 2048×2048 | 874 ms | 21 ms | 41.2 | 1.1e-15 | 0 |
| `mtf_tangential_sagittal` | imaging | 2048×2048 | 209 ms | 5 ms | 40.8 | 2.5e-20 | 0 |
| `dist_transform` | region | 2048×2048 | 461 ms | 11 ms | 40.7 | 0.0e+00 | 0 |
| `zero_crossing` | segmentation | 2048×2048 | 531 ms | 13 ms | 39.9 | 0.0e+00 | 0 |
| `joint_bilateral` | depth_denoise | 2048×2048 | 27.46 s | 703 ms | 39.1 | 4.3e-16 | 0 |
| `coherent_image` | coherent | 2048×2048 | 954 ms | 25 ms | 38.7 | 1.0e-15 | 0 |
| `sg_kmeans_intensity` | segment | 2048×2048 | 3.99 s | 105 ms | 38.1 | 0.0e+00 | 0 |
| `fft_image_inv` | frequency | 2048×2048 | 492 ms | 13 ms | 37.6 | 3.6e-11 | 0 |
| `robinson_dir` | edges | 2048×2048 | 589 ms | 16 ms | 36.8 | 0.0e+00 | 0 |
| `dem_slope` | surface | 2048×2048 | 456 ms | 12 ms | 36.8 | 1.1e-16 | 0 |
| `kirsch_amp` | edges | 2048×2048 | 585 ms | 16 ms | 36.7 | 5.1e-15 | 0 |
| `annotate_dimension` | paper | 2048×2048 | 1.95 s | 53 ms | 36.6 | 0.0e+00 | 0 |
| `correlation_score` | score | 256×256×256 | 3.40 s | 93 ms | 36.4 | 5.8e-16 | 0 |
| `vol_median` | 3d | 256×256×256 | 1.65 s | 46 ms | 36.0 | 0.0e+00 | 0 |
| `photometric_residual` | photometric | 2048×2048 | 1.20 s | 34 ms | 35.7 | 1.9e-16 | 0 |
| `video_interpolate_flow` | time | 8×512×512 | 6.85 s | 196 ms | 35.0 | 0.0e+00 | 0 |
| `temporal_bilateral` | denoise | 8×512×512 | 404 ms | 12 ms | 34.7 | 0.0e+00 | 0 |
| `annotate_invert_path` | overlay | 2048×2048 | 984 ms | 28 ms | 34.5 | 0.0e+00 | 1 |
| `weighting_response` | level | 1048576 | 152 ms | 4 ms | 34.5 | 9.9e-16 | 0 |
| `highpass_image` | frequency | 2048×2048 | 532 ms | 16 ms | 34.3 | 1.0e-13 | 0 |
| `corner_response` | edges | 2048×2048 | 513 ms | 15 ms | 34.2 | 1.5e-15 | 0 |
| `kuwahara` | smoothing | 2048×2048 | 510 ms | 15 ms | 34.2 | 1.4e-14 | 0 |
| `radial_reach_filter` | change | 2048×2048 | 11.33 s | 332 ms | 34.2 | 0.0e+00 | 0 |
| `radial_periodogram` | terrain | 2048×2048 | 302 ms | 9 ms | 33.2 | 2.6e-08 | 0 |
| `hankel_image` | transform | 2048×2048 | 279 ms | 8 ms | 33.1 | 4.4e-15 | 0 |
| `quat_correlate` | match | 2048×2048×4 | 3.18 s | 96 ms | 33.0 | 1.9e-15 | 0 |
| `vx_phase` | gradient | 2048×2048 | 111 ms | 3 ms | 32.9 | 0.0e+00 | 0 |
| `perlin2` | terrain | 2048×2048 | 1.58 s | 48 ms | 32.8 | 0.0e+00 | 1 |
| `edge_transition_width` | edges | 2048×2048 | 494 ms | 15 ms | 32.8 | 2.7e-16 | 0 |
| `iv_wiener_deconv_spatial` | restoration | 2048×2048 | 548 ms | 17 ms | 32.8 | 5.5e-16 | 0 |
| `tac_shear_field` | tactile | 2048×2048 | 671 ms | 21 ms | 32.5 | 2.9e-16 | 0 |
| `dem_aspect` | surface | 2048×2048 | 406 ms | 13 ms | 32.3 | 1.2e-16 | 0 |
| `pupil_psf` | wave | 2048×2048 | 5.41 s | 167 ms | 32.3 | 5.5e-16 | 0 |
| `rounded_rect` | shape | 2048×2048 | 583 ms | 18 ms | 31.8 | 0.0e+00 | 0 |
| `envelope` | signal | 1048576 | 112 ms | 4 ms | 31.3 | 8.9e-16 | 0 |
| `tf_rank_transform` | texture | 2048×2048 | 496 ms | 16 ms | 31.0 | 0.0e+00 | 0 |
| `halftone_screen` | npr | 2048×2048 | 405 ms | 13 ms | 30.1 | 4.4e-16 | 0 |
| `blob_distance` | split | 2048×2048 | 334 ms | 11 ms | 29.8 | 0.0e+00 | 0 |
| `bilateral_filter_depth` | depth_denoise | 2048×2048 | 20.57 s | 694 ms | 29.6 | 2.3e-16 | 0 |
| `gen_gabor` | texture | 2048×2048 | 539 ms | 18 ms | 29.4 | 1.7e-14 | 0 |
| `affine_trans_image_size` | geometry | 2048×2048 | 455 ms | 16 ms | 29.4 | 2.3e-16 | 0 |
| `vx_magnitude` | gradient | 2048×2048 | 123 ms | 4 ms | 29.3 | 0.0e+00 | 0 |
| `gmsd_map` | perceptual | 2048×2048 | 340 ms | 12 ms | 29.0 | 3.7e-15 | 0 |
| `fbm_gradient` | terrain | 2048×2048 | 2.91 s | 101 ms | 28.9 | 2.3e-16 | 0 |
| `psd_welch` | matched | 1048576 | 43 ms | 2 ms | 28.9 | 0.0e+00 | 0 |
| `dem_curvature` | surface | 2048×2048 | 330 ms | 12 ms | 28.2 | 0.0e+00 | 0 |
| `local_thickness` | morphology | 2048×2048 | 892 ms | 32 ms | 28.0 | 0.0e+00 | 0 |
| `slab_transmittance` | glassbody | 1048576 | 221 ms | 8 ms | 27.7 | 3.0e-16 | 0 |
| `xsp_hilbert_env` | texture | 2048×2048 | 357 ms | 13 ms | 27.4 | 5.2e-16 | 0 |
| `grating_three_image_retrieve` | grating_interf | 256×256×256 | 1.36 s | 50 ms | 27.4 | 1.5e-14 | 0 |
| `monotony` | gray | 2048×2048 | 299 ms | 11 ms | 27.4 | 0.0e+00 | 0 |
| `log_zero_crossings` | edges | 256×256×256 | 2.43 s | 90 ms | 26.9 | 0.0e+00 | 0 |
| `affine_warp` | geometry | 2048×2048 | 366 ms | 14 ms | 26.9 | 2.3e-16 | 0 |
| `f2_expand_domain` | gray | 2048×2048 | 422 ms | 16 ms | 26.4 | 0.0e+00 | 0 |
| `tem_power_spectrum` | tem | 2048×2048 | 763 ms | 29 ms | 26.4 | 1.2e-09 | 0 |
| `cosmic_ray_reject` | cosmic | 2048×2048 | 1.68 s | 64 ms | 26.1 | 0.0e+00 | 0 |
| `deviation_image` | texture | 2048×2048 | 321 ms | 12 ms | 26.0 | 4.0e-07 | 0 |
| `structure_tensor_orientation` | texture | 2048×2048 | 536 ms | 21 ms | 26.0 | 1.5e-14 | 0 |
| `dem_hillshade` | shading | 2048×2048 | 372 ms | 15 ms | 25.6 | 2.8e-15 | 0 |
| `speckle_statistics` | coherent | 2048×2048 | 202 ms | 8 ms | 25.3 | 8.2e-15 | 2 |
| `dwt_transform` | transform | 2048×2048 | 518 ms | 20 ms | 25.3 | 2.7e-12 | 2 |
| `vx_sobel3x3` | gradient | 2048×2048 | 189 ms | 7 ms | 25.2 | 0.0e+00 | 0 |
| `warp_tps_image` | morph | 2048×2048 | 3.03 s | 120 ms | 25.2 | 4.9e-10 | 0 |
| `flow_from_depth_motion` | ttc | 2048×2048 | 799 ms | 32 ms | 25.1 | 0.0e+00 | 0 |
| `feat_image_vector` | features | 2048×2048 | 770 ms | 31 ms | 24.7 | 3.1e-16 | 0 |
| `cie_xyz_from_wavelength` | appearance | 1048576 | 194 ms | 8 ms | 24.1 | 1.4e-64 | 0 |
| `render_transport` | light_transport | 24 | 547 ms | 23 ms | 24.0 | 2.4e-15 | 0 |
| `seg_membrane_response` | response | 2048×2048 | 353 ms | 15 ms | 23.3 | 4.8e-15 | 0 |
| `iv_richardson_lucy` | restoration | 2048×2048 | 1.41 s | 61 ms | 23.2 | 5.2e-16 | 0 |
| `tb_temporal_bilateral` | typed | 8×512×512 | 287 ms | 12 ms | 23.1 | 0.0e+00 | 0 |
| `fraunhofer_pattern` | wave | 2048×2048 | 390 ms | 17 ms | 23.0 | 3.9e-20 | 0 |
| `arrow` | pointer | 2048×2048 | 359 ms | 16 ms | 22.9 | 0.0e+00 | 0 |
| `rotate_img` | geometry | 2048×2048 | 394 ms | 17 ms | 22.9 | 2.3e-16 | 0 |
| `normals_from_depth` | range_image | 2048×2048 | 961 ms | 42 ms | 22.9 | 0.0e+00 | 0 |
| `distance_ridge` | medial | 256×256×256 | 2.36 s | 103 ms | 22.9 | 0.0e+00 | 0 |
| `deflectometry_phase_to_slope` | deflectometry | 2048×2048 | 1.28 s | 57 ms | 22.6 | 3.2e-16 | 0 |
| `tem_multislice` | tem | 2048×2048 | 1.22 s | 55 ms | 22.3 | 2.7e-09 | 0 |
| `sem_render` | sem | 2048×2048 | 363 ms | 17 ms | 21.6 | 1.5e-12 | 0 |
| `fresnel_conductor` | interface | 1048576 | 130 ms | 6 ms | 21.2 | 5.5e-15 | 0 |
| `dem_roughness` | surface | 2048×2048 | 313 ms | 15 ms | 21.0 | 2.4e-16 | 0 |
| `fft_image` | frequency | 2048×2048 | 254 ms | 12 ms | 21.0 | 1.0e-13 | 0 |
| `annotate_invert` | overlay | 2048×2048 | 362 ms | 17 ms | 21.0 | 0.0e+00 | 1 |
| `rough_transmission` | surface | 1048576 | 181 ms | 9 ms | 20.9 | 4.0e-16 | 0 |
| `illuminate` | gray | 2048×2048 | 318 ms | 15 ms | 20.8 | 2.8e-16 | 0 |
| `power_byte` | frequency | 2048×2048 | 279 ms | 13 ms | 20.8 | 1.0e-13 | 0 |
| `lab_to_rgb` | colorspace | 2048×2048×3 | 938 ms | 45 ms | 20.6 | 8.5e-16 | 0 |
| `xdog` | edges | 2048×2048 | 344 ms | 17 ms | 20.5 | 1.6e-14 | 0 |
| `mean_curvature_flow` | smoothing | 2048×2048 | 233 ms | 11 ms | 20.5 | 4.0e-16 | 0 |
| `dyn_threshold` | segmentation | 2048×2048 | 299 ms | 15 ms | 20.3 | 0.0e+00 | 0 |
| `dc_local_contrast_norm` | decomposition | 2048×2048 | 349 ms | 17 ms | 20.2 | 8.3e-13 | 0 |
| `iv_unsharp_deblur` | restoration | 2048×2048 | 319 ms | 16 ms | 19.8 | 9.2e-16 | 0 |
| `affine_trans_image` | geometry | 2048×2048 | 291 ms | 15 ms | 19.7 | 2.3e-16 | 0 |
| `tb_iqft2` | typed | 2048×2048×4 | 1.09 s | 55 ms | 19.7 | 1.8e-12 | 0 |
| `distance_transform` | region | 2048×2048 | 296 ms | 15 ms | 19.6 | 0.0e+00 | 0 |
| `annotate3d_bbox` | annotate3d | 2048×2048 | 897 ms | 46 ms | 19.6 | 0.0e+00 | 0 |
| `sobel_amp` | edges | 2048×2048 | 265 ms | 14 ms | 19.4 | 1.8e-15 | 0 |
| `morph_grad` | morphology | 2048×2048 | 278 ms | 15 ms | 19.0 | 0.0e+00 | 0 |
| `keypoints_from_image2d` | keypoint | 2048×2048 | 159 ms | 9 ms | 18.6 | 2.8e-13 | 0 |
| `aug_rolling_shutter` | augmentation | 2048×2048 | 270 ms | 14 ms | 18.6 | 5.6e-17 | 0 |
| `bloom` | post | 2048×2048×3 | 729 ms | 39 ms | 18.5 | 9.7e-17 | 0 |
| `cylinder_unwrap` | curvilinear | 256×256×256 | 277 ms | 15 ms | 18.5 | 0.0e+00 | 0 |
| `peg_measure_overlay` | pegsim | 2048×2048×3 | 242 ms | 13 ms | 18.3 | 0.0e+00 | 0 |
| `f2_gauss_pyramid` | smoothing | 2048×2048 | 318 ms | 17 ms | 18.2 | 2.3e-16 | 0 |
| `tophat` | morphology | 2048×2048 | 243 ms | 14 ms | 18.0 | 0.0e+00 | 0 |
| `hx_gen_circle_sector` | halcon_ext | 2048×2048 | 281 ms | 16 ms | 17.9 | 0.0e+00 | 0 |
| `annotate3d_label` | annotate3d | 2048×2048 | 646 ms | 37 ms | 17.7 | 0.0e+00 | 0 |
| `tf_steerable_filter` | edges | 2048×2048 | 258 ms | 15 ms | 17.6 | 2.9e-16 | 0 |
| `triangulate_column` | structured_light | 2048×2048 | 283 ms | 16 ms | 17.6 | 0.0e+00 | 0 |
| `tb_weighting_response` | typed | 1048576 | 76 ms | 4 ms | 17.5 | 1.0e-15 | 0 |
| `vol_local_std` | feature | 256×256×256 | 1.56 s | 89 ms | 17.5 | 8.1e-12 | 0 |
| `engrave_lines` | npr | 2048×2048 | 240 ms | 14 ms | 17.4 | 2.2e-16 | 0 |
| `it_bit_lshift` | gray | 2048×2048 | 222 ms | 13 ms | 17.4 | 0.0e+00 | 0 |
| `vol_gradient_magnitude` | feature | 256×256×256 | 1.46 s | 84 ms | 17.2 | 8.2e-16 | 0 |
| `edges_color_sub_pix` | contour | 2048×2048×3 | 789 ms | 46 ms | 17.2 | 0.0e+00 | 0 |
| `eliminate_sp` | rank | 2048×2048 | 224 ms | 13 ms | 17.1 | 6.9e-15 | 0 |
| `emva_general_relative_qe` | sensorgeneral | 1048576 | 1.12 s | 66 ms | 17.1 | 1.4e-14 | 0 |
| `hx_shade_height_field` | halcon_ext | 2048×2048 | 282 ms | 17 ms | 17.1 | 0.0e+00 | 0 |
| `gabor` | texture | 2048×2048 | 544 ms | 32 ms | 17.1 | 1.7e-14 | 0 |
| `it_crop_part` | geometry | 2048×2048 | 231 ms | 14 ms | 17.1 | 1.2e-16 | 0 |
| `emva_bspline_regression` | sensorchar | 1048576 | 979 ms | 58 ms | 17.0 | 8.7e-15 | 0 |
| `warp_by_plane` | plane_sweep_stereo | 2048×2048 | 224 ms | 13 ms | 16.9 | 5.9e-17 | 0 |
| `varmodel_alignment` | variation | 8×512×512 | 2.26 s | 134 ms | 16.9 | 1.0e-06 | 126 |
| `hx_gen_ellipse_sector` | halcon_ext | 2048×2048 | 246 ms | 15 ms | 16.9 | 0.0e+00 | 0 |
| `vol_fft_lowpass` | frequency | 256×256×256 | 801 ms | 48 ms | 16.8 | 2.3e-16 | 0 |
| `tf_log_polar` | geometry | 2048×2048 | 252 ms | 15 ms | 16.8 | 2.3e-15 | 0 |
| `sigma_image` | smoothing | 2048×2048 | 241 ms | 14 ms | 16.8 | 6.9e-15 | 0 |
| `temporal_median_window` | window | 8×512×512 | 213 ms | 13 ms | 16.6 | 0.0e+00 | 0 |
| `equirect_rotate` | omni360 | 2048×2048×3 | 1.04 s | 63 ms | 16.4 | 2.4e-16 | 0 |
| `gray_opening_rect` | morphology | 2048×2048 | 214 ms | 13 ms | 16.4 | 0.0e+00 | 0 |
| `rft_generic` | frequency | 2048×2048 | 205 ms | 13 ms | 16.4 | 9.1e-18 | 0 |
| `contact_patch_radius` | tacdome | 2048×2048 | 134 ms | 8 ms | 16.3 | 4.4e-16 | 0 |
| `grid_lines` | plot | 2048×2048 | 449 ms | 28 ms | 16.2 | 0.0e+00 | 0 |
| `varmodel_fit` | variation | 8×512×512 | 2.14 s | 133 ms | 16.2 | 4.1e-07 | 123 |
| `tsdf_from_depth` | transform | 2048×2048 | 341 ms | 21 ms | 16.2 | 0.0e+00 | 0 |
| `gray_opening` | morphology | 2048×2048 | 214 ms | 13 ms | 16.1 | 0.0e+00 | 0 |
| `hx_gen_rectangle2` | halcon_ext | 2048×2048 | 186 ms | 12 ms | 16.1 | 0.0e+00 | 0 |
| `carla_depth_decode` | carla | 2048×2048×3 | 178 ms | 11 ms | 16.1 | 0.0e+00 | 0 |
| `phase_rad` | frequency | 2048×2048 | 220 ms | 14 ms | 16.0 | 2.3e-12 | 0 |
| `sobel_mag` | edges | 2048×2048 | 211 ms | 13 ms | 16.0 | 1.8e-15 | 0 |
| `sk_li` | segmentation | 2048×2048 | 457 ms | 29 ms | 16.0 | 0.0e+00 | 0 |
| `f2_symmetry` | texture | 2048×2048 | 266 ms | 17 ms | 15.9 | 0.0e+00 | 0 |
| `emva_general_sensitivity` | sensorgeneral | 1048576 | 1.91 s | 121 ms | 15.8 | 3.6e-09 | 0 |
| `photometric_stereo` | photometric | 2048×2048 | 479 ms | 30 ms | 15.8 | 0.0e+00 | 0 |
| `aug_chromatic` | augmentation | 2048×2048 | 223 ms | 14 ms | 15.8 | 1.7e-16 | 0 |
| `img_to_beatcube` | bridge | 2048×2048 | 169 ms | 11 ms | 15.6 | 1.1e-16 | 2 |
| `ttc_truth` | ttc | 2048×2048 | 749 ms | 48 ms | 15.6 | 0.0e+00 | 0 |
| `video_summary_keyframes` | summary | 8×512×512 | 92 ms | 6 ms | 15.5 | 0.0e+00 | 0 |
| `canny` | segmentation | 2048×2048 | 225 ms | 14 ms | 15.5 | 0.0e+00 | 0 |
| `percentile_level` | level | 1048576 | 82 ms | 5 ms | 15.4 | 5.2e-10 | 0 |
| `polarization_demosaic_color` | polarization | 2048×2048 | 1.76 s | 114 ms | 15.4 | 0.0e+00 | 0 |
| `fft_generic` | frequency | 2048×2048 | 223 ms | 15 ms | 15.3 | 1.0e-13 | 0 |
| `histogram_match` | matching | 2048×2048 | 1.02 s | 66 ms | 15.3 | 0.0e+00 | 0 |
| `edges_sub_pix` | contour | 2048×2048 | 240 ms | 16 ms | 15.3 | 1.3e-12 | 0 |
| `local_std` | texture | 2048×2048 | 194 ms | 13 ms | 15.3 | 4.0e-07 | 0 |
| `class_ndim_norm` | classify | 2048×2048 | 249 ms | 16 ms | 15.3 | 0.0e+00 | 0 |
| `removal_depth_from_heights` | polish | 2048×2048 | 499 ms | 33 ms | 15.2 | 1.4e-12 | 0 |
| `emva_ptc_linearity_check` | sensorchar | 1048576 | 917 ms | 61 ms | 15.0 | 5.8e-11 | 0 |
| `annotate3d_axes` | annotate3d | 2048×2048 | 853 ms | 57 ms | 14.9 | 0.0e+00 | 0 |
| `tb_companding_mu_law` | typed | 1048576 | 69 ms | 5 ms | 14.9 | 1.2e-16 | 0 |
| `tb_drag_coefficient_sphere` | typed | 1048576 | 69 ms | 5 ms | 14.9 | 9.9e-17 | 0 |
| `xyz_to_lab` | colorspace | 2048×2048×3 | 487 ms | 33 ms | 14.8 | 2.5e-16 | 0 |
| `ttc_from_flow` | ttc | 2048×2048 | 293 ms | 20 ms | 14.8 | 0.0e+00 | 0 |
| `dog` | edges | 2048×2048 | 183 ms | 12 ms | 14.8 | 2.1e-14 | 0 |
| `four_f_filter` | wave | 2048×2048 | 690 ms | 47 ms | 14.8 | 4.6e-16 | 0 |
| `xsp_morph_laplace` | edges | 2048×2048 | 212 ms | 14 ms | 14.7 | 0.0e+00 | 0 |
| `resample` | signal | 1048576 | 38 ms | 3 ms | 14.7 | 6.1e-16 | 0 |
| `mandelbrot_interior` | complex | 2048×2048 | 133 ms | 9 ms | 14.6 | 0.0e+00 | 0 |
| `tb_lf_epi_slope` | typed | 3×3×256×256 | 39 ms | 3 ms | 14.5 | 6.0e-15 | 1 |
| `robinson_amp` | edges | 2048×2048 | 450 ms | 31 ms | 14.5 | 0.0e+00 | 0 |
| `cplx_domain_colour` | complex | 2048×2048 | 737 ms | 51 ms | 14.4 | 1.3e-15 | 0 |
| `closest_point_transform` | region | 2048×2048 | 283 ms | 20 ms | 14.4 | 0.0e+00 | 0 |
| `local_bimodality` | texture | 2048×2048 | 652 ms | 45 ms | 14.4 | 4.1e-12 | 0 |
| `img_to_keypoints` | bridge | 2048×2048 | 108 ms | 8 ms | 14.3 | 0.0e+00 | 0 |
| `lowpass` | frequency | 2048×2048 | 508 ms | 36 ms | 14.2 | 4.0e-16 | 0 |
| `annotate3d_arrow` | annotate3d | 2048×2048 | 383 ms | 27 ms | 14.2 | 0.0e+00 | 0 |
| `img_to_monogenic` | bridge | 2048×2048 | 909 ms | 64 ms | 14.2 | 1.3e-14 | 0 |
| `annotate_leader` | paper | 2048×2048 | 780 ms | 56 ms | 14.0 | 0.0e+00 | 0 |
| `perceptual_hash` | hash | 2048×2048 | 64 ms | 5 ms | 13.9 | 0.0e+00 | 1 |
| `tb_temporal_median_window` | typed | 8×512×512 | 188 ms | 14 ms | 13.9 | 0.0e+00 | 0 |
| `derivate_gauss` | edges | 2048×2048 | 204 ms | 15 ms | 13.8 | 2.3e-15 | 0 |
| `dem_geodetic_slope` | geodesy | 2048×2048 | 208 ms | 15 ms | 13.8 | 1.5e-16 | 0 |
| `f2_bit_slice` | gray | 2048×2048 | 208 ms | 15 ms | 13.8 | 0.0e+00 | 0 |
| `tonemap_aces` | render | 2048×2048 | 169 ms | 12 ms | 13.8 | 0.0e+00 | 0 |
| `annotate_orientation` | paper | 2048×2048 | 778 ms | 57 ms | 13.7 | 0.0e+00 | 0 |
| `lucky_select` | quality | 2048×2048 | 1.50 s | 109 ms | 13.7 | 0.0e+00 | 0 |
| `it_add_image_border` | geometry | 2048×2048 | 164 ms | 12 ms | 13.6 | 1.2e-16 | 0 |
| `class_2dim_unsup` | classify | 2048×2048 | 2.62 s | 193 ms | 13.5 | 0.0e+00 | 1 |
| `membrane_recover` | tacsim | 2048×2048×3 | 1.45 s | 107 ms | 13.5 | 2.3e-13 | 0 |
| `edges_color` | edges | 2048×2048×3 | 723 ms | 54 ms | 13.5 | 2.2e-14 | 0 |
| `clahe` | gray | 2048×2048 | 350 ms | 26 ms | 13.4 | 7.8e-17 | 0 |
| `gray_range_rect` | rank | 2048×2048 | 190 ms | 14 ms | 13.3 | 0.0e+00 | 0 |
| `xsp_detrend_flatten` | gray | 2048×2048 | 263 ms | 20 ms | 13.2 | 2.0e-15 | 0 |
| `mindlin_traction` | tacslip | 1024×1024 | 61 ms | 5 ms | 13.1 | 1.1e-16 | 0 |
| `xsp_gauss_grad_mag` | edges | 2048×2048 | 170 ms | 13 ms | 13.1 | 2.2e-15 | 0 |
| `power_ln` | frequency | 2048×2048 | 221 ms | 17 ms | 13.1 | 1.0e-13 | 0 |
| `tm_sinogram_denoise` | tomography | 2048×2048 | 177 ms | 14 ms | 12.9 | 2.3e-16 | 0 |
| `annotate3d_measure` | annotate3d | 2048×2048 | 585 ms | 46 ms | 12.8 | 0.0e+00 | 0 |
| `power_real` | frequency | 2048×2048 | 190 ms | 15 ms | 12.8 | 9.1e-18 | 0 |
| `gray_tophat` | morphology | 2048×2048 | 167 ms | 13 ms | 12.7 | 0.0e+00 | 0 |
| `peg_tip_from_rgbd` | pegsim | 2048×2048×3 | 4.73 s | 373 ms | 12.7 | 1.2e-09 | 0 |
| `diff_of_gauss` | edges | 2048×2048 | 213 ms | 17 ms | 12.7 | 2.1e-14 | 0 |
| `gray_bothat` | morphology | 2048×2048 | 167 ms | 13 ms | 12.6 | 0.0e+00 | 0 |
| `linear_to_srgb` | colorspace | 2048×2048×3 | 541 ms | 43 ms | 12.5 | 1.9e-16 | 0 |
| `bothat` | morphology | 2048×2048 | 147 ms | 12 ms | 12.4 | 0.0e+00 | 0 |
| `apply_weighting` | level | 1048576 | 55 ms | 4 ms | 12.3 | 5.3e-15 | 0 |
| `micro_phase_decode` | light_transport | 2048×2048 | 807 ms | 66 ms | 12.3 | 5.4e-16 | 1 |
| `fresnel_dielectric` | interface | 1048576 | 73 ms | 6 ms | 12.3 | 1.4e-16 | 0 |
| `lf_epi_slope` | depth | 3×3×256×256 | 41 ms | 3 ms | 12.3 | 6.0e-15 | 1 |
| `overlay_labels` | overlay | 2048×2048 | 213 ms | 17 ms | 12.2 | 0.0e+00 | 0 |
| `temporal_band_power` | temporal | 8×512×512 | 40 ms | 3 ms | 12.2 | 2.9e-16 | 0 |
| `joint_histogram` | information | 2048×2048 | 125 ms | 10 ms | 12.1 | 0.0e+00 | 0 |
| `cosmic_ray_reject_stack` | cosmic | 2048×2048 | 944 ms | 78 ms | 12.1 | 0.0e+00 | 0 |
| `revolution_volume_side` | scoop | 2048×2048 | 163 ms | 14 ms | 12.1 | 3.6e-08 | 0 |
| `gray_closing_shape` | morphology | 2048×2048 | 157 ms | 13 ms | 12.0 | 0.0e+00 | 0 |
| `deform_tps` | deformation | 2048×2048 | 3.96 s | 329 ms | 12.0 | 9.9e-14 | 0 |
| `binomial_filter` | smoothing | 2048×2048 | 132 ms | 11 ms | 12.0 | 1.1e-16 | 0 |
| `running_mean_std` | recursive | 8×512×512 | 53 ms | 4 ms | 11.9 | 0.0e+00 | 0 |
| `it_crop_rectangle1` | geometry | 2048×2048 | 157 ms | 13 ms | 11.9 | 1.3e-16 | 0 |
| `aug_cutout` | augmentation | 2048×2048 | 156 ms | 13 ms | 11.7 | 0.0e+00 | 2 |
| `vol_label_mpr_rgb` | slice | 256×256×256×3 | 586 ms | 50 ms | 11.6 | 0.0e+00 | 0 |
| `f2_topographic` | edges | 2048×2048 | 741 ms | 64 ms | 11.6 | 0.0e+00 | 0 |
| `annotate_angle` | paper | 2048×2048 | 570 ms | 49 ms | 11.5 | 0.0e+00 | 0 |
| `tb_angular_spectrum_propagate` | typed | 2048×2048 | 843 ms | 74 ms | 11.4 | 3.4e-16 | 1 |
| `chromatic_aberration` | post | 2048×2048×3 | 444 ms | 39 ms | 11.3 | 1.9e-16 | 0 |
| `texture_laws` | texture | 2048×2048 | 171 ms | 15 ms | 11.3 | 2.6e-13 | 0 |
| `prewitt_amp` | edges | 2048×2048 | 172 ms | 15 ms | 11.3 | 2.4e-15 | 0 |
| `sg_region_growing_seeded` | segment | 2048×2048 | 205 ms | 18 ms | 11.3 | 0.0e+00 | 0 |
| `polariscope_intensity` | photoelastic | 2048×2048 | 155 ms | 14 ms | 11.3 | 1.8e-16 | 0 |
| `hx_gen_ellipse` | halcon_ext | 2048×2048 | 182 ms | 16 ms | 11.3 | 0.0e+00 | 0 |
| `vx_warp_perspective` | geometry | 2048×2048 | 385 ms | 34 ms | 11.2 | 0.0e+00 | 0 |
| `vol_gaussian` | 3d | 256×256×256 | 759 ms | 68 ms | 11.2 | 2.3e-16 | 0 |
| `it_bit_mask` | gray | 2048×2048 | 131 ms | 12 ms | 11.2 | 0.0e+00 | 0 |
| `color_grade` | post | 2048×2048×3 | 557 ms | 50 ms | 11.2 | 3.1e-16 | 0 |
| `thin_film_reflectance` | appearance | 1048576 | 643 ms | 58 ms | 11.1 | 1.0e-12 | 0 |
| `lines_color` | contour | 2048×2048×3 | 492 ms | 44 ms | 11.1 | 0.0e+00 | 0 |
| `tan_image` | arithmetic | 2048×2048 | 155 ms | 14 ms | 11.0 | 6.9e-17 | 0 |
| `prewitt_mag` | edges | 2048×2048 | 164 ms | 15 ms | 11.0 | 2.4e-15 | 0 |
| `f2_lut_trans` | gray | 2048×2048 | 138 ms | 13 ms | 11.0 | 8.4e-17 | 0 |
| `terrain_gradient` | terrain | 2048×2048 | 7.38 s | 671 ms | 11.0 | 4.2e-16 | 0 |
| `sfp_dolp_model` | shape_from_polarization | 2048×2048 | 187 ms | 17 ms | 11.0 | 7.6e-16 | 0 |
| `quat_image_multiply` | algebra | 2048×2048×4 | 673 ms | 62 ms | 10.9 | 0.0e+00 | 0 |
| `hx_close_edges_length` | halcon_ext | 2048×2048 | 143 ms | 13 ms | 10.9 | 0.0e+00 | 0 |
| `whiten_by_psd` | matched | 1048576 | 47 ms | 4 ms | 10.9 | 6.0e-16 | 0 |
| `annotate_legend` | paper | 2048×2048 | 562 ms | 52 ms | 10.8 | 0.0e+00 | 0 |
| `tem_image_weak_phase` | tem | 2048×2048 | 684 ms | 63 ms | 10.8 | 4.5e-13 | 1 |
| `hertz_surface_ur` | tacslip | 1024×1024 | 48 ms | 4 ms | 10.8 | 5.1e-16 | 0 |
| `surface_normals` | photometric | 2048×2048 | 281 ms | 26 ms | 10.7 | 0.0e+00 | 0 |
| `vx_histogram` | pixel | 2048×2048 | 65 ms | 6 ms | 10.7 | 0.0e+00 | 0 |
| `overlay_mask` | overlay | 2048×2048 | 130 ms | 12 ms | 10.7 | 0.0e+00 | 0 |
| `laplace` | edges | 2048×2048 | 127 ms | 12 ms | 10.5 | 3.1e-14 | 0 |
| `create_funct_1d_pairs` | function | 1048576 | 24 ms | 2 ms | 10.5 | 0.0e+00 | 0 |
| `unsharp` | smoothing | 2048×2048 | 110 ms | 11 ms | 10.4 | 1.7e-16 | 0 |
| `superpixel_color_texture_features` | plant | 2048×2048×3 | 1.23 s | 118 ms | 10.4 | 7.2e-15 | 0 |
| `sdf_smooth_union` | sdf_csg | 256×256×256 | 637 ms | 61 ms | 10.4 | 0.0e+00 | 0 |
| `angular_spectrum_propagate` | wave | 2048×2048 | 696 ms | 67 ms | 10.3 | 3.3e-16 | 1 |
| `dem_tpi` | surface | 2048×2048 | 262 ms | 26 ms | 10.2 | 4.4e-14 | 0 |
| `specular_coefficient_map` | dichromatic | 2048×2048×3 | 648 ms | 63 ms | 10.2 | 4.9e-16 | 0 |
| `tb_specular_coefficient_map` | typed | 2048×2048×3 | 648 ms | 65 ms | 10.0 | 4.9e-16 | 0 |
| `hertz_surface_uz` | tacsim | 1024×1024 | 41 ms | 4 ms | 10.0 | 3.7e-16 | 0 |
| `iqft2` | fourier | 2048×2048×4 | 673 ms | 68 ms | 9.9 | 1.8e-12 | 0 |
| `frei_dir` | edges | 2048×2048 | 157 ms | 16 ms | 9.9 | 2.7e-14 | 0 |
| `arc` | shape | 2048×2048 | 323 ms | 33 ms | 9.8 | 0.0e+00 | 0 |
| `adaptive_gauss_thresh` | segmentation | 2048×2048 | 145 ms | 15 ms | 9.8 | 0.0e+00 | 0 |
| `tb_envelope` | typed | 1048576 | 54 ms | 6 ms | 9.7 | 8.7e-16 | 0 |
| `dots_image` | edges | 2048×2048 | 223 ms | 23 ms | 9.5 | 3.6e-15 | 0 |
| `marker_detect` | tacslip | 2048×2048 | 510 ms | 54 ms | 9.5 | 3.5e-06 | 1 |
| `it_change_format` | geometry | 2048×2048 | 111 ms | 12 ms | 9.5 | 0.0e+00 | 0 |
| `sk_otsu` | segmentation | 2048×2048 | 122 ms | 13 ms | 9.5 | 0.0e+00 | 0 |
| `it_region_to_bin` | segmentation | 2048×2048 | 139 ms | 15 ms | 9.4 | 0.0e+00 | 0 |
| `tb_temporal_band_power` | typed | 8×512×512 | 45 ms | 5 ms | 9.4 | 2.4e-16 | 0 |
| `tb_monogenic_orientation` | typed | 2048×2048×4 | 257 ms | 27 ms | 9.4 | 1.2e-16 | 0 |
| `label_points` | pointer | 2048×2048 | 678 ms | 73 ms | 9.3 | 0.0e+00 | 0 |
| `dem_geocentric_grid` | geodesy | 2048×2048 | 397 ms | 43 ms | 9.3 | 2.4e-13 | 0 |
| `frei_amp` | edges | 2048×2048 | 125 ms | 13 ms | 9.2 | 2.2e-15 | 0 |
| `nonmax_suppression_amp` | segmentation | 2048×2048 | 125 ms | 14 ms | 9.2 | 0.0e+00 | 0 |
| `hilbert_analytic` | spectral | 1048576 | 127 ms | 14 ms | 9.2 | 6.5e-15 | 0 |
| `quantization_error` | gray | 2048×2048 | 117 ms | 13 ms | 9.2 | 0.0e+00 | 0 |
| `blast_normals` | finish | 2048×2048×3 | 479 ms | 52 ms | 9.1 | 0.0e+00 | 1 |
| `terrain_height` | terrain | 2048×2048 | 6.24 s | 685 ms | 9.1 | 2.8e-16 | 0 |
| `tb_cx_ifft` | typed | 2048×2048 | 164 ms | 18 ms | 9.1 | 1.3e-13 | 0 |
| `raw_dead_pixel_correct` | isp | 2048×2048 | 275 ms | 30 ms | 9.1 | 0.0e+00 | 0 |
| `annotate_colorbar` | paper | 2048×2048 | 641 ms | 71 ms | 9.1 | 2.7e-16 | 0 |
| `raw_demosaic_bilinear` | isp | 2048×2048 | 253 ms | 28 ms | 9.0 | 0.0e+00 | 0 |
| `tb_monogenic_amplitude` | typed | 2048×2048×4 | 210 ms | 23 ms | 8.9 | 1.6e-16 | 0 |
| `blob_overlay` | extract | 2048×2048 | 426 ms | 48 ms | 8.9 | 0.0e+00 | 1 |
| `local_threshold` | segmentation | 2048×2048 | 113 ms | 13 ms | 8.9 | 0.0e+00 | 0 |
| `tb_qft2` | typed | 2048×2048×4 | 631 ms | 71 ms | 8.9 | 7.8e-15 | 0 |
| `classify_image_class_lut` | classify | 2048×2048 | 64 ms | 7 ms | 8.9 | 0.0e+00 | 0 |
| `vol_dilate` | 3d | 256×256×256 | 417 ms | 47 ms | 8.9 | 0.0e+00 | 0 |
| `plant_color_index` | plant | 2048×2048×3 | 295 ms | 33 ms | 8.8 | 0.0e+00 | 0 |
| `annotate_text_path` | paper | 2048×2048 | 176 ms | 20 ms | 8.8 | 0.0e+00 | 6 |
| `hx_gen_circle` | halcon_ext | 2048×2048 | 194 ms | 22 ms | 8.8 | 0.0e+00 | 0 |
| `xsp_savgol` | smoothing | 2048×2048 | 230 ms | 26 ms | 8.7 | 1.3e-15 | 0 |
| `hx_fit_surface1` | halcon_ext | 2048×2048 | 452 ms | 52 ms | 8.7 | 8.6e-05 | 0 |
| `zoom_image_factor` | geometry | 2048×2048 | 302 ms | 35 ms | 8.7 | 2.3e-16 | 0 |
| `gray_erosion` | morphology | 2048×2048 | 117 ms | 13 ms | 8.7 | 0.0e+00 | 0 |
| `xsk3_integral_image` | gray | 2048×2048 | 127 ms | 15 ms | 8.6 | 1.2e-15 | 0 |
| `cepstrum` | bearing | 1048576 | 57 ms | 7 ms | 8.6 | 6.7e-16 | 0 |
| `gopen` | morphology | 2048×2048 | 139 ms | 16 ms | 8.6 | 0.0e+00 | 0 |
| `gray_closing` | morphology | 2048×2048 | 138 ms | 16 ms | 8.5 | 0.0e+00 | 0 |
| `tb_running_gaussian_background` | typed | 8×512×512 | 84 ms | 10 ms | 8.5 | 0.0e+00 | 0 |
| `min_filter` | rank | 2048×2048 | 116 ms | 14 ms | 8.4 | 0.0e+00 | 0 |
| `tb_fly_tau_from_expansion` | typed | 1048576 | 38 ms | 5 ms | 8.4 | 4.9e-18 | 0 |
| `local_max` | segmentation | 2048×2048 | 125 ms | 15 ms | 8.4 | 0.0e+00 | 0 |
| `wrapped_phase` | structured_light | 2048×2048 | 174 ms | 21 ms | 8.4 | 4.6e-17 | 0 |
| `annotate_markers` | paper | 2048×2048 | 702 ms | 85 ms | 8.3 | 0.0e+00 | 0 |
| `highpass` | frequency | 2048×2048 | 344 ms | 42 ms | 8.3 | 1.0e-13 | 0 |
| `ensquared_energy` | imaging | 2048×2048 | 55 ms | 7 ms | 8.3 | 1.8e-19 | 0 |
| `vol_boundary_points` | boundary | 256×256×256 | 133 ms | 16 ms | 8.1 | 0.0e+00 | 0 |
| `ellipse_pressure_shifted` | tactorque | 1024×1024 | 31 ms | 4 ms | 8.1 | 5.4e-16 | 0 |
| `tb_resample` | typed | 1048576 | 24 ms | 3 ms | 8.1 | 7.1e-16 | 0 |
| `potential_flow_cylinder` | swarmflow | 1048576 | 1.43 s | 179 ms | 8.0 | 3.5e-16 | 0 |
| `aug_barrel` | augmentation | 2048×2048 | 326 ms | 41 ms | 8.0 | 1.2e-16 | 0 |
| `vignette` | post | 2048×2048×3 | 279 ms | 35 ms | 7.9 | 1.9e-16 | 0 |
| `sk_adjust_log` | gray | 2048×2048 | 106 ms | 13 ms | 7.9 | 1.2e-16 | 0 |
| `wipe_coverage` | polish | 2048×2048 | 355 ms | 45 ms | 7.9 | 0.0e+00 | 0 |
| `quantize_lloyd_max` | gray | 2048×2048 | 616 ms | 78 ms | 7.9 | 2.0e-15 | 0 |
| `separate_direct_global` | light_transport | 2048×2048 | 556 ms | 72 ms | 7.7 | 0.0e+00 | 0 |
| `sph_kernel` | swarmflow | 1048576 | 27 ms | 4 ms | 7.7 | 2.4e-16 | 0 |
| `color_bar` | furniture | 2048×2048 | 427 ms | 56 ms | 7.6 | 0.0e+00 | 0 |
| `bit_and` | nary | 2048×2048 | 114 ms | 15 ms | 7.6 | 0.0e+00 | 0 |
| `palette_quantize` | post | 2048×2048×3 | 951 ms | 125 ms | 7.6 | 0.0e+00 | 0 |
| `tem_ctf_correct` | tem | 2048×2048 | 532 ms | 70 ms | 7.6 | 3.4e-16 | 1 |
| `running_gaussian_background` | background | 8×512×512 | 70 ms | 9 ms | 7.6 | 0.0e+00 | 0 |
| `anscombe_inverse` | transform | 2048×2048 | 96 ms | 13 ms | 7.6 | 1.1e-16 | 0 |
| `smooth_image` | smoothing | 2048×2048 | 119 ms | 16 ms | 7.5 | 1.7e-16 | 0 |
| `aug_fixed_pattern` | augmentation | 2048×2048 | 95 ms | 13 ms | 7.5 | 0.0e+00 | 2 |
| `crossing_gate_state` | crossing | 1048576 | 57 ms | 8 ms | 7.5 | 7.1e-17 | 0 |
| `img_to_lightfield` | bridge | 2048×2048 | 2.79 s | 374 ms | 7.5 | 0.0e+00 | 0 |
| `isotropic_diffusion` | smoothing | 2048×2048 | 97 ms | 13 ms | 7.4 | 2.3e-16 | 0 |
| `spectrum` | signal | 1048576 | 24 ms | 3 ms | 7.4 | 3.0e-18 | 0 |
| `aug_motion_blur` | augmentation | 2048×2048 | 146 ms | 20 ms | 7.4 | 2.9e-16 | 0 |
| `vol_fft_highpass` | frequency | 256×256×256 | 772 ms | 105 ms | 7.4 | 1.4e-14 | 0 |
| `tb_monogenic_phase` | typed | 2048×2048×4 | 147 ms | 20 ms | 7.4 | 1.1e-16 | 0 |
| `surface_form_error` | surface_fit | 2048×2048 | 457 ms | 62 ms | 7.3 | 6.3e-08 | 0 |
| `coverage_edge_points` | pegsim | 2048×2048 | 111 ms | 15 ms | 7.3 | 0.0e+00 | 0 |
| `img_to_projection_profile` | bridge | 2048×2048 | 33 ms | 5 ms | 7.2 | 2.6e-16 | 0 |
| `fly_tau_from_expansion` | looming | 1048576 | 31 ms | 4 ms | 7.2 | 1.1e-16 | 0 |
| `anomaly_pro` | anomaly_eval | 4×512×512 | 63 ms | 9 ms | 7.1 | 2.3e-13 | 1 |
| `unproject_spherical` | lidar_projection | 2048×2048 | 250 ms | 36 ms | 7.0 | 5.5e-17 | 0 |
| `carla_label_unmap` | carla | 2048×2048 | 39 ms | 6 ms | 7.0 | 0.0e+00 | 0 |
| `gray_closing_rect` | morphology | 2048×2048 | 136 ms | 19 ms | 7.0 | 0.0e+00 | 0 |
| `ods_depth_to_disparity` | omni360 | 2048×2048 | 104 ms | 15 ms | 7.0 | 1.1e-16 | 0 |
| `crosshair` | pointer | 2048×2048 | 104 ms | 15 ms | 7.0 | 0.0e+00 | 0 |
| `fly_hex_quantize` | sample | 1048576 | 22 ms | 3 ms | 7.0 | 0.0e+00 | 0 |
| `vx_nonlinear_filter` | filter | 2048×2048 | 63 ms | 9 ms | 6.9 | 0.0e+00 | 0 |
| `aug_vignette` | augmentation | 2048×2048 | 215 ms | 32 ms | 6.8 | 1.1e-16 | 0 |
| `it_convert_image_type` | gray | 2048×2048 | 79 ms | 12 ms | 6.8 | 0.0e+00 | 0 |
| `gclose` | morphology | 2048×2048 | 137 ms | 20 ms | 6.8 | 0.0e+00 | 0 |
| `log` | edges | 2048×2048 | 193 ms | 29 ms | 6.8 | 5.0e-15 | 0 |
| `mean_box_wh` | smoothing | 2048×2048 | 110 ms | 16 ms | 6.8 | 7.4e-15 | 0 |
| `temporal_bandpass` | temporal | 8×512×512 | 57 ms | 8 ms | 6.7 | 5.4e-17 | 0 |
| `it_crop_domain` | domain | 2048×2048 | 100 ms | 15 ms | 6.7 | 0.0e+00 | 0 |
| `tb_specular_diffuse_split` | typed | 2048×2048×3 | 682 ms | 104 ms | 6.6 | 1.7e-15 | 0 |
| `it_bit_rshift` | gray | 2048×2048 | 91 ms | 14 ms | 6.5 | 0.0e+00 | 0 |
| `sprite_blit` | sprite | 2048×2048×4 | 1.29 s | 198 ms | 6.5 | 0.0e+00 | 1 |
| `tb_temporal_bandpass` | typed | 8×512×512 | 46 ms | 7 ms | 6.5 | 6.0e-17 | 0 |
| `bearing_angle_image` | range_image | 2048×2048 | 59 ms | 9 ms | 6.5 | 0.0e+00 | 0 |
| `compare_frame` | compose | 2048×2048 | 135 ms | 21 ms | 6.5 | 0.0e+00 | 0 |
| `sg_normalized_cut_2` | segment | 2048×2048 | 343 ms | 53 ms | 6.5 | 0.0e+00 | 1 |
| `binary_threshold` | segmentation | 2048×2048 | 85 ms | 13 ms | 6.5 | 0.0e+00 | 0 |
| `structure_tensor_coherence` | texture | 2048×2048 | 512 ms | 80 ms | 6.4 | 6.7e-14 | 0 |
| `zoom_inset` | compose | 2048×2048 | 133 ms | 21 ms | 6.4 | 0.0e+00 | 0 |
| `invert_funct_1d` | function | 1048576 | 37 ms | 6 ms | 6.4 | 0.0e+00 | 0 |
| `roberts` | edges | 2048×2048 | 137 ms | 22 ms | 6.3 | 1.4e-16 | 0 |
| `gray_dilation` | morphology | 2048×2048 | 78 ms | 12 ms | 6.3 | 0.0e+00 | 0 |
| `tb_apply_weighting` | typed | 1048576 | 56 ms | 9 ms | 6.3 | 4.4e-15 | 0 |
| `eval_poly_surface` | surface_fit | 6 | 265 ms | 42 ms | 6.3 | 1.1e-16 | 0 |
| `qft2` | fourier | 2048×2048×4 | 697 ms | 112 ms | 6.2 | 7.8e-15 | 0 |
| `mat_pinv` | linalg | 1024×1024 | 1.99 s | 320 ms | 6.2 | 2.5e-15 | 0 |
| `wetness` | material | 2048×2048×3 | 267 ms | 43 ms | 6.2 | 0.0e+00 | 0 |
| `srgb_to_linear` | colorspace | 2048×2048×3 | 468 ms | 76 ms | 6.2 | 6.8e-17 | 0 |
| `hx_region_to_mean` | halcon_ext | 2048×2048 | 106 ms | 17 ms | 6.2 | 8.4e-15 | 0 |
| `normal_error_map` | tacscalib | 2048×2048×3 | 294 ms | 48 ms | 6.1 | 1.0e-16 | 0 |
| `check_difference` | compare | 2048×2048 | 45 ms | 7 ms | 6.1 | 0.0e+00 | 0 |
| `normal_map_decode` | light | 2048×2048×3 | 251 ms | 42 ms | 6.0 | 0.0e+00 | 0 |
| `nine_slice` | sprite | 2048×2048×4 | 72 ms | 12 ms | 6.0 | 0.0e+00 | 0 |
| `hx_gen_derivative_filter` | halcon_ext | 2048×2048 | 111 ms | 19 ms | 5.9 | 1.4e-16 | 0 |
| `vol_gamma` | gray | 256×256×256 | 324 ms | 55 ms | 5.9 | 5.7e-17 | 0 |
| `hertz_pressure_shifted` | tactorque | 1024×1024 | 21 ms | 4 ms | 5.9 | 1.3e-15 | 0 |
| `beam_hardening_apply` | artifact | 2048×2048 | 75 ms | 13 ms | 5.9 | 7.4e-19 | 0 |
| `monogenic_phase` | riesz | 2048×2048×4 | 177 ms | 31 ms | 5.8 | 8.3e-17 | 0 |
| `tb_wetness` | typed | 2048×2048×3 | 390 ms | 68 ms | 5.8 | 0.0e+00 | 0 |
| `morph` | morph | 2048×2048 | 1.78 s | 310 ms | 5.7 | 1.3e-15 | 4 |
| `tb_fly_lgmd_eta` | typed | 1048576 | 16 ms | 3 ms | 5.7 | 1.0e-16 | 0 |
| `dither` | post | 2048×2048 | 76 ms | 13 ms | 5.7 | 0.0e+00 | 2 |
| `img_to_cimage` | bridge | 2048×2048 | 112 ms | 20 ms | 5.7 | 5.5e-17 | 0 |
| `annotate3d_scale_bar` | annotate3d | 2048×2048 | 230 ms | 41 ms | 5.7 | 0.0e+00 | 0 |
| `alpha_composite` | composite | 2048×2048×4 | 1.13 s | 201 ms | 5.6 | 0.0e+00 | 1 |
| `gray_opening_shape` | morphology | 2048×2048 | 81 ms | 14 ms | 5.6 | 0.0e+00 | 0 |
| `particle_image_d50` | grind | 2048×2048 | 118 ms | 21 ms | 5.6 | 6.4e-15 | 3 |
| `hx_plane_deviation` | halcon_ext | 2048×2048 | 303 ms | 54 ms | 5.6 | 1.9e-04 | 0 |
| `simulate_defocus` | smoothing | 2048×2048 | 105 ms | 19 ms | 5.5 | 6.8e-15 | 0 |
| `vol_opening_ball` | 3d | 256×256×256 | 331 ms | 61 ms | 5.5 | 0.0e+00 | 0 |
| `scale_bar` | furniture | 2048×2048 | 237 ms | 44 ms | 5.4 | 0.0e+00 | 0 |
| `sk_yen` | segmentation | 2048×2048 | 75 ms | 14 ms | 5.4 | 0.0e+00 | 0 |
| `macro_vol_denoise` | macro | 256×256×256 | 637 ms | 119 ms | 5.4 | 1.1e-16 | 0 |
| `annotate_figure_grid` | paper | 2048×2048 | 2.29 s | 429 ms | 5.3 | 0.0e+00 | 0 |
| `hx_gen_disc_se` | halcon_ext | 2048×2048 | 115 ms | 22 ms | 5.3 | 0.0e+00 | 0 |
| `gray_erosion_rect` | rank | 2048×2048 | 71 ms | 13 ms | 5.3 | 0.0e+00 | 0 |
| `ods_disparity_to_depth` | omni360 | 2048×2048 | 69 ms | 13 ms | 5.3 | 0.0e+00 | 0 |
| `carla_depth_encode` | carla | 2048×2048 | 108 ms | 20 ms | 5.3 | 0.0e+00 | 0 |
| `punch_surface_uz` | tactorque | 1024×1024 | 21 ms | 4 ms | 5.3 | 1.2e-16 | 0 |
| `max_filter` | rank | 2048×2048 | 67 ms | 13 ms | 5.3 | 0.0e+00 | 0 |
| `hx_gen_lowpass` | halcon_ext | 2048×2048 | 58 ms | 11 ms | 5.3 | 0.0e+00 | 0 |
| `lf_disparity_to_depth` | depth | 2048×2048 | 96 ms | 18 ms | 5.2 | 0.0e+00 | 0 |
| `hue_saturation` | isp | 2048×2048×3 | 261 ms | 50 ms | 5.2 | 3.6e-16 | 0 |
| `graycode_decode` | structured_light | 2048×2048 | 191 ms | 37 ms | 5.2 | 0.0e+00 | 0 |
| `gradient3d` | edges | 256×256×256 | 1.03 s | 199 ms | 5.2 | 2.3e-15 | 0 |
| `emva_spectrogram` | sensorchar | 2048×2048 | 189 ms | 37 ms | 5.2 | 1.4e-15 | 0 |
| `sigmoid` | gray | 2048×2048 | 63 ms | 12 ms | 5.1 | 2.8e-17 | 0 |
| `gauss_filter` | smoothing | 2048×2048 | 73 ms | 14 ms | 5.1 | 2.3e-16 | 0 |
| `runlength_smear` | morphology | 2048×2048 | 66 ms | 13 ms | 5.1 | 0.0e+00 | 0 |
| `blend_mode` | composite | 2048×2048×3 | 224 ms | 44 ms | 5.1 | 0.0e+00 | 0 |

倍率の中央値 14.8、最小 5.1、最大 308.8。

採用 507 件のうち 53 件は手書きの GPU 経路(`accel` 系)も持つ。新しく GPU で走るようになったのは 454 件。

### GPU 対応率への数え方(分母 2127 件 = required + suitable)

| 経路 | 件数 |
|---|---:|
| 手書き経路(`accel` / `accel_vol` / `accel_match`) | 85 |
| 許可リスト経由(機械的 GPU 化。`fullseye/data/gpu_auto_allow.json`) | 507 |
| うち手書きと重複 | 53 |
| 合算(重複を 1 回と数える) | 539 |

注記: 許可リスト経由の 507 件は**既定では有効でない**。明示の GPU 指定か許可リストを使ったときだけ GPU で走る。手書き経路とは数字を混ぜず、必ず上の内訳で示す。採用の門(内部差 < 5e-03・転送込み 5.0 倍以上・出力定数は不採用)は変えていない。

実寸の比較は間引いた標本で行ったので、倍率の上位と無作為標本の 659 件は全画素で比べ直した(`tools/gpu_auto_verify.py`)。一致 658 件。

## 一致したが遅い op(倍率の高い順に上位 30)

| op | 族 | 入力 | CPU | GPU | 倍率 |
|---|---|---|---:|---:|---:|
| `alife_reaction_bz` | artificial-life | 2048×2048 | 3.66 s | 35 ms | 105.52 |
| `speckle_quality` | solid | 2048×2048 | 927 ms | 10 ms | 94.67 |
| `canny3d` | edges | 256×256×256 | 3.24 s | 42 ms | 77.27 |
| `sp_saddle_points_sub_pix` | subpix | 2048×2048 | 497 ms | 8 ms | 60.29 |
| `annotate_invert_visibility` | overlay | 2048×2048 | 407 ms | 7 ms | 56.40 |
| `hx_estimate_tilt_zc` | halcon_ext | 2048×2048 | 175 ms | 3 ms | 52.81 |
| `surface_params` | measure | 2048×2048 | 2.79 s | 55 ms | 50.28 |
| `frame_quality` | quality | 2048×2048 | 489 ms | 10 ms | 48.30 |
| `tf_census_transform` | texture | 2048×2048 | 631 ms | 14 ms | 44.34 |
| `occlusion_edges` | range_image | 2048×2048 | 189 ms | 5 ms | 37.80 |
| `itof_flying_pixel_mask` | itof | 2048×2048 | 733 ms | 20 ms | 35.85 |
| `tb_equivalent_level` | typed | 1048576 | 82 ms | 3 ms | 31.67 |
| `phase_correlation_shift` | registration | 2048×2048 | 1.22 s | 39 ms | 31.51 |
| `hx_estimate_tilt_lr` | halcon_ext | 2048×2048 | 138 ms | 4 ms | 31.03 |
| `cplx_cr_residual` | complex | 2048×2048 | 244 ms | 8 ms | 30.73 |
| `optimal_snr` | matched | 1048576 | 77 ms | 3 ms | 26.26 |
| `equivalent_level` | level | 1048576 | 65 ms | 3 ms | 25.82 |
| `edge_alias_energy` | render | 2048×2048 | 121 ms | 5 ms | 25.50 |
| `riesz_transform` | riesz | 2048×2048 | 1.08 s | 44 ms | 24.46 |
| `vx_nonmax_suppression` | suppress | 2048×2048 | 59 ms | 3 ms | 23.68 |
| `tb_cplx_cr_residual` | typed | 2048×2048 | 212 ms | 9 ms | 23.00 |
| `vx_remap` | geometry | 2048×2048 | 166 ms | 7 ms | 22.88 |
| `vx_table_lookup` | pixel | 2048×2048 | 44 ms | 2 ms | 22.78 |
| `profile_params` | measure | 1048576 | 50 ms | 2 ms | 22.40 |
| `topology_signature` | medial | 256×256×256 | 366 ms | 17 ms | 21.37 |
| `band_snr` | temporal | 8×512×512 | 77 ms | 4 ms | 19.62 |
| `hx_cooc_feature` | halcon_ext | 2048×2048 | 142 ms | 7 ms | 19.46 |
| `sk_sauvola` | segmentation | 2048×2048 | 290 ms | 16 ms | 18.48 |
| `matcap_shade` | render | 2048×2048×3 | 601 ms | 34 ms | 17.74 |
| `m1_measure_projection` | measure1d | 2048×2048 | 123 ms | 7 ms | 17.69 |

## 追加掃引: 前 → 後

修正層(`gpu_shadow.py`、道 1)と常駐の連続処理(道 2)を足す前後の件数。分母 2127 件は変えていない。

| 分類 | 前 | 後 | 差 |
|---|---:|---:|---:|
| 採用(一致 + 転送込み 5 倍以上) | 502 | 507 | +5 |
| 常駐前提で採用(単独 1 回は 5 倍未満、GPU に載せたままの連続処理で 5 倍以上) | 0 | 120 | +120 |
| パイプライン常駐可(単独は 5 倍未満、GPU に載せたままの連続処理で 1 倍以上 5 倍未満。単独では採用しない) | 0 | 37 | +37 |
| 一致したが遅い(5 倍未満) | 486 | 331 | -155 |
| 一致したが実寸の入力を作れない(固定形の入力) | 438 | 444 | +6 |
| 不一致 | 48 | 48 | +0 |
| 判定不能(出力が定数) | 145 | 145 | +0 |
| 例外(CuPy 側の不足・型の混在) | 62 | 48 | -14 |
| 包み(cv2 / skimage / PIL が本体) | 184 | 184 | +0 |
| Python ループが律速 | 67 | 67 | +0 |
| 測れなかった | 195 | 196 | +1 |

採用の増分は道 1 が 5 件(単独 1 回呼び)、道 2 が 120 件(常駐前提・別枠)。常駐前提の採用は単独 1 回呼びの採用と混ぜて数えない。

### 道 1: 原因別の結果

| 原因 | 前の件数 | 直した(一致になった) | うち実寸で採用 | 直せない | 直せない理由 |
|---|---:|---:|---:|---:|---|
| wrapper_skimage | 108 | 0 | 0 | 108 | 本体が skimage(ネイティブ)。CuPy 配列を受け付けない。CPU へ渡して戻すだけの差し替えは GPU 化ではない |
| wrapper_cv2 | 60 | 0 | 0 | 60 | 本体が OpenCV(ネイティブ)。同上 |
| wrapper_PIL | 16 | 0 | 0 | 16 | 本体が PIL(ネイティブ)。同上 |
| value_error | 14 | 1 | 1 | 13 | 疎グラフ(csgraph)・疎行列の解法・縮退入力・自作クラスの型比較。CuPy 側に同等が無いか、入力の問題 |
| numpy_cupy_mix | 13 | 8 | 3 | 5 | CuPy が受け付けない型の混在(「直した」以外の残り) |
| type_error | 13 | 3 | 1 | 10 | 0 次元 CuPy 配列を Python の添字・辞書キー・スライスに使う箇所、SuperLU の LU.solve(CPU 専用)など。対応には op 側の書換えが要る |
| implicit_numpy | 9 | 0 | 0 | 9 | 疎行列・グラフ・skimage 経由で本物の numpy が CuPy 配列を受け取る。疎行列/グラフ(CPU アルゴリズム)は GPU に載せても転送が増えるだけ |
| gpu_timeout | 7 | 2 | 0 | 5 | 90 秒で終わらない(小さなカーネルを大量に発行する Python ループ律速) |
| unhashable_array | 4 | 0 | 0 | 4 | 配列を set / dict のキーに使う Python ループ(GPU 化の対象でない) |
| gpu_crash | 2 | 0 | 0 | 2 | プロセスが落ちる |

直した op と実寸の倍率:

| op | 原因 | 結果 | 倍率(単独) |
|---|---|---|---:|
| `car_hybrid_astar` | numpy_cupy_mix | match_slow | — |
| `fit_spin` | gpu_timeout | match_fixed | — |
| `micro_phase_decode` | value_error | adopted | 12.32 |
| `peg_measure_overlay` | numpy_cupy_mix | adopted | 18.30 |
| `perpetual_render` | numpy_cupy_mix | match_fixed | — |
| `plenoptic_mla_calibrate` | numpy_cupy_mix | match_fixed | — |
| `register_fpfh` | gpu_timeout | match_fixed | — |
| `sem_image` | type_error | unmeasured | — |
| `sign_image` | numpy_cupy_mix | match_fixed | — |
| `speckle_statistics` | type_error | adopted | 25.29 |
| `stat_ks_test` | type_error | match_slow | 0.95 |
| `synth_frame_series` | numpy_cupy_mix | match_fixed | — |
| `varmodel_alignment` | numpy_cupy_mix | adopted | 16.92 |
| `varmodel_fit` | numpy_cupy_mix | adopted | 16.16 |

直した修正(`gpu_shadow.py`。numpy / scipy を呼ぶ側のソースは書き換えない):

- `a[i] = (x, y)` のようにタプル・リストを CuPy 配列へ代入する形を、読み込み時の AST 書換えで配列に包む(CuPy は右辺のタプルを受け付けない)。
- `x.max(initial=v)` / `min` / `sum` の `initial` を `maximum` / `minimum` / 加算に置く。
- `np.repeat` の `repeats` が CuPy 配列のとき CPU の整数列にして渡す。
- `np.full(shape, ndarray)` を broadcast に置く。
- object dtype を CuPy が拒否した呼び出しは CPU に退避して数える。
- `scipy.stats.kstest` の結果のようにキーワード専用の追加項目を持つ namedtuple を、同名の namedtuple で組み直す。

### 道 2: 常駐前提の連続処理

単独 1 回呼びで 3.5〜5 倍だった op を、入力を GPU に先に 8 個ぶん置き、計算を続け、出力を 1 回だけ戻して測り直した。1 回あたりの時間 = (往路の転送 + 計算の総和 + 復路の転送) / 8。計算は 1 回ごとに `Stream.synchronize()` の後に時計を読む。CPU に退避した呼び出しがある op は常駐前提にならないので採用から除く。

測った 193 件のうち、常駐前提で採用 120 件、CPU 退避ありで除外 7 件、5 倍未満 62 件、不一致 0 件。

「単独(再)」は常駐の測定と同じ場で単独 1 回呼びも測り直した倍率。先の測定より高い op が多く、先の単独の値は他の負荷で遅く出ていた可能性がある。採用の判定は先の測定のまま動かしていない(測り直しの値で採用に格上げしない)。

| op | 族 | 単独 | 単独(再) | 常駐 | 計算のみ | CPU 退避 | 判定 |
|---|---|---:|---:|---:|---:|---:|---|
| `tac_surface_normal` | tactile | 4.85 | 27.34 | 55.7 | 103.3 | 0 | adopted_resident |
| `laplace_of_gauss` | edges | 4.31 | 16.12 | 40.2 | 114.3 | 0 | adopted_resident |
| `rescale_img` | geometry | 1.92 | 19.39 | 34.3 | 57.4 | 0 | adopted_resident |
| `synthesize_fringes` | structured_light | 4.73 | 8.10 | 34.1 | 103.5 | 0 | adopted_resident |
| `phase_deg` | frequency | 2.47 | 18.53 | 31.3 | 80.0 | 0 | adopted_resident |
| `img_to_video` | bridge | 3.45 | 6.45 | 29.2 | 74.4 | 0 | adopted_resident |
| `mean_box` | smoothing | 1.32 | 10.30 | 27.6 | 99.8 | 0 | adopted_resident |
| `hx_gen_checker_region` | halcon_ext | 2.04 | 9.75 | 25.4 | 83.0 | 0 | adopted_resident |
| `grating_stepping_simulate` | grating_interf | 4.75 | 6.42 | 23.9 | 48.3 | 0 | adopted_resident |
| `roberts_mag` | edges | 4.21 | 9.36 | 23.9 | 73.5 | 0 | adopted_resident |
| `alpha_composite_premul` | composite | 2.47 | 10.84 | 22.6 | 87.8 | 0 | adopted_resident |
| `vol_rotate` | geom_transform | 1.80 | 8.01 | 22.6 | 91.1 | 0 | adopted_resident |
| `aolp_to_azimuth` | shape_from_polarization | 4.49 | 6.42 | 21.9 | 75.2 | 0 | adopted_resident |
| `zoom_image_size` | geometry | 1.00 | 10.10 | 21.7 | 87.6 | 0 | adopted_resident |
| `rgb3_to_gray` | color | 1.85 | 11.45 | 21.6 | 110.4 | 0 | adopted_resident |
| `polarization_render` | polarization | 4.80 | 6.20 | 21.0 | 62.6 | 0 | adopted_resident |
| `anaglyph_crosstalk` | omni360 | 3.40 | 9.06 | 20.9 | 45.7 | 0 | adopted_resident |
| `surface_filter` | prepare | 4.71 | 5.95 | 20.9 | 74.9 | 0 | adopted_resident |
| `dither_ordered` | gray | 4.62 | 9.55 | 18.5 | 61.8 | 16 | match_slow |
| `vol_dilation_ball` | 3d | 2.00 | 7.72 | 17.9 | 107.0 | 0 | adopted_resident |
| `anscombe_transform` | transform | 4.26 | 6.54 | 17.4 | 65.4 | 0 | adopted_resident |
| `pow_image` | gray | 4.44 | 6.92 | 17.2 | 51.4 | 0 | adopted_resident |
| `vol_fft_bandpass` | frequency | 3.05 | 19.46 | 16.7 | 32.0 | 0 | adopted_resident |
| `hx_close_edges` | halcon_ext | 4.72 | 6.21 | 16.2 | 52.4 | 0 | adopted_resident |
| `hx_gen_bandfilter` | halcon_ext | 3.32 | 6.03 | 15.9 | 57.9 | 0 | adopted_resident |
| `sin_image` | arithmetic | 4.82 | 5.69 | 15.9 | 64.9 | 0 | adopted_resident |
| `cos_image` | arithmetic | 1.47 | 5.78 | 15.8 | 61.3 | 0 | adopted_resident |
| `ritter_dam_break` | swarmflow | 3.41 | 4.88 | 15.0 | 38.2 | 0 | adopted_resident |
| `edge_points` | edges | 3.69 | 3.89 | 14.6 | 45.5 | 0 | adopted_resident |
| `gray_dilation_shape` | morphology | 2.85 | 4.49 | 14.5 | 51.8 | 0 | adopted_resident |
| `auto_threshold` | segmentation | 3.81 | 6.04 | 14.5 | 33.6 | 0 | adopted_resident |
| `gamma` | gray | 3.45 | 5.42 | 14.3 | 48.1 | 0 | adopted_resident |
| `gerode` | morphology | 4.99 | 7.67 | 14.2 | 86.2 | 0 | adopted_resident |
| `quantize_uniform` | gray | 4.01 | 5.01 | 13.5 | 59.0 | 0 | adopted_resident |
| `sub_image` | nary | 2.83 | 6.10 | 13.1 | 74.8 | 0 | adopted_resident |
| `exp_image` | arithmetic | 4.33 | 4.98 | 13.1 | 58.0 | 0 | adopted_resident |
| `vol_erode` | 3d | 4.73 | 8.42 | 12.9 | 92.2 | 0 | adopted_resident |
| `hx_disparity_to_xyz` | halcon_ext | 4.53 | 5.59 | 12.8 | 44.7 | 0 | adopted_resident |
| `equalize` | gray | 1.33 | 5.54 | 12.8 | 30.1 | 0 | adopted_resident |
| `caustic_floor_segmentation` | watervision | 3.14 | 15.91 | 12.7 | 16.7 | 0 | adopted_resident |
| `acos_image` | arithmetic | 1.88 | 4.47 | 12.7 | 54.0 | 0 | adopted_resident |
| `linear_trans_color` | color | 3.68 | 4.59 | 12.5 | 38.5 | 0 | adopted_resident |
| `tb_cx_apply_transfer_function` | typed | 1.06 | 5.55 | 12.4 | 53.2 | 0 | adopted_resident |
| `premultiply` | composite | 3.86 | 4.54 | 12.4 | 48.9 | 0 | adopted_resident |
| `scale_image` | gray | 3.29 | 4.81 | 12.2 | 59.5 | 0 | adopted_resident |
| `bit_or` | nary | 2.62 | 5.53 | 12.2 | 84.5 | 0 | adopted_resident |
| `noise_inconsistency_map` | noise | 3.02 | 5.66 | 12.0 | 22.3 | 0 | adopted_resident |
| `img_to_volume` | bridge | 2.39 | 2.56 | 12.0 | 26.7 | 0 | adopted_resident |
| `hx_fill_interlace` | halcon_ext | 4.00 | 4.37 | 11.8 | 46.4 | 0 | adopted_resident |
| `retardation_from_birefringence` | photoelastic | 2.19 | 2.76 | 11.6 | 43.4 | 0 | adopted_resident |
| `light_mask` | light | 3.54 | 5.18 | 11.4 | 67.6 | 0 | adopted_resident |
| `transform_funct_1d` | function | 2.87 | 3.87 | 11.4 | 29.0 | 0 | adopted_resident |
| `rgb_apply_gains` | isp | 3.04 | 4.07 | 11.4 | 44.0 | 0 | adopted_resident |
| `monogenic_amplitude` | riesz | 3.08 | 8.82 | 11.3 | 58.4 | 0 | adopted_resident |
| `scale_image_max` | gray | 2.18 | 4.15 | 11.3 | 41.2 | 0 | adopted_resident |
| `fast_threshold` | segmentation | 2.26 | 4.19 | 11.3 | 46.1 | 0 | adopted_resident |
| `tb_quaternion_to_rgb` | typed | 2.93 | 4.28 | 11.2 | 53.7 | 0 | adopted_resident |
| `vol_equalize` | gray | 3.81 | 5.21 | 11.1 | 35.2 | 0 | adopted_resident |
| `tb_cx_phase` | typed | 3.26 | 5.20 | 11.1 | 58.4 | 0 | adopted_resident |
| `equ_histo_image` | gray | 4.85 | 5.34 | 10.9 | 33.6 | 0 | adopted_resident |
| `surface_form_remove` | prepare | 3.05 | 4.37 | 10.8 | 27.5 | 0 | adopted_resident |
| `depth_to_organized_points` | range_image | 1.85 | 2.86 | 10.8 | 32.1 | 0 | adopted_resident |
| `img_to_rgb` | bridge | 4.35 | 8.91 | 10.4 | 16.1 | 0 | adopted_resident |
| `mult_image` | nary | 2.76 | 4.57 | 10.3 | 72.6 | 0 | adopted_resident |
| `tb_exponential_background` | typed | 3.95 | 5.67 | 10.2 | 18.9 | 0 | adopted_resident |
| `hertzian_tangential_inner` | tacslip | 3.87 | 3.84 | 10.2 | 47.7 | 0 | adopted_resident |
| `annotate_scale_bar` | paper | 2.20 | 8.11 | 10.2 | 11.7 | 0 | adopted_resident |
| `otsu` | segmentation | 4.10 | 4.57 | 10.1 | 23.7 | 0 | adopted_resident |
| `stereo360_sbs` | omni360 | 1.43 | 3.27 | 10.1 | 74.8 | 0 | adopted_resident |
| `hx_mean_shape` | halcon_ext | 1.92 | 4.02 | 10.0 | 28.4 | 0 | adopted_resident |
| `vol_threshold` | 3d | 1.63 | 3.25 | 10.0 | 65.2 | 0 | adopted_resident |
| `asin_image` | arithmetic | 3.80 | 3.60 | 9.8 | 38.4 | 0 | adopted_resident |
| `photon_uncertainty` | counting | 3.65 | 4.00 | 9.8 | 30.5 | 0 | adopted_resident |
| `atan_image` | arithmetic | 4.88 | 5.73 | 9.6 | 64.0 | 0 | adopted_resident |
| `vol_erosion_ball` | 3d | 3.24 | 3.15 | 9.5 | 51.0 | 0 | adopted_resident |
| `log_image` | arithmetic | 4.45 | 3.34 | 9.5 | 38.7 | 0 | adopted_resident |
| `abs_diff_image` | nary | 1.91 | 4.15 | 9.4 | 71.2 | 0 | adopted_resident |
| `legend_box` | furniture | 4.17 | 8.50 | 9.3 | 10.0 | 0 | adopted_resident |
| `panel_grid` | compose | 1.37 | 3.07 | 9.0 | 35.3 | 0 | adopted_resident |
| `hx_histo_to_thresh` | halcon_ext | 3.33 | 4.11 | 8.9 | 17.8 | 0 | adopted_resident |
| `it_full_domain` | domain | 1.75 | 4.05 | 8.8 | 37.9 | 0 | adopted_resident |
| `gray_erosion_shape` | morphology | 2.36 | 3.99 | 8.7 | 37.3 | 0 | adopted_resident |
| `vol_tiled_map` | domain | 1.20 | 3.26 | 8.7 | 32.1 | 0 | adopted_resident |
| `tb_quantize` | typed | 3.94 | 4.94 | 8.6 | 19.1 | 0 | adopted_resident |
| `equ_histo_image_rect` | gray | 4.88 | 4.88 | 8.4 | 12.6 | 0 | adopted_resident |
| `smooth_funct_1d_gauss` | function | 1.91 | 3.57 | 8.4 | 22.3 | 0 | adopted_resident |
| `vol_boundary` | boundary | 1.32 | 2.72 | 8.3 | 48.5 | 0 | adopted_resident |
| `flow_magnitude` | flow | 3.60 | 6.50 | 8.3 | 87.0 | 0 | adopted_resident |
| `gray_dilation_rect` | rank | 1.78 | 4.47 | 8.2 | 26.6 | 0 | adopted_resident |
| `div_image` | nary | 2.70 | 4.27 | 8.2 | 69.7 | 0 | adopted_resident |
| `text_box` | text | 2.53 | 6.30 | 8.2 | 9.5 | 0 | adopted_resident |
| `retardation_convert` | photoelastic | 3.25 | 2.77 | 8.1 | 37.7 | 0 | adopted_resident |
| `underwater_image` | watermedia | 3.78 | 3.59 | 7.9 | 14.3 | 48 | match_slow |
| `min_image` | nary | 3.62 | 3.58 | 7.9 | 60.1 | 0 | adopted_resident |
| `hx_region_to_label` | halcon_ext | 3.13 | 3.43 | 7.8 | 18.0 | 0 | adopted_resident |
| `threshold` | segmentation | 3.09 | 2.86 | 7.8 | 29.3 | 0 | adopted_resident |
| `morph_sequence` | morph | 4.36 | 7.66 | 7.8 | 7.8 | 224 | match_slow |
| `tb_smooth_funct_1d_gauss` | typed | 3.26 | 3.33 | 7.7 | 18.2 | 0 | adopted_resident |
| `tb_integrate_funct_1d` | typed | 2.79 | 5.16 | 7.6 | 14.4 | 0 | adopted_resident |
| `sdf_offset` | sdf_csg | 2.39 | 2.47 | 7.4 | 43.4 | 0 | adopted_resident |
| `hx_rectangle1_domain` | halcon_ext | 1.95 | 2.60 | 7.4 | 31.4 | 0 | adopted_resident |
| `membrane_predict_rgb` | tacscalib | 1.17 | 2.53 | 7.2 | 32.2 | 0 | adopted_resident |
| `tb_magnus_lift_coefficient` | typed | 4.61 | 5.11 | 7.1 | 11.9 | 0 | adopted_resident |
| `vol_label_slice_rgb` | slice | 1.65 | 14.59 | 7.0 | 334.5 | 0 | adopted_resident |
| `quaternion_to_rgb` | convert | 1.61 | 3.47 | 7.0 | 40.2 | 0 | adopted_resident |
| `dct_transform` | transform | 4.64 | 6.11 | 6.7 | 7.2 | 8 | match_slow |
| `invert_image` | gray | 1.79 | 2.32 | 6.6 | 28.8 | 0 | adopted_resident |
| `carla_label_map` | carla | 1.91 | 1.96 | 6.6 | 14.9 | 0 | adopted_resident |
| `tb_cx_log_magnitude` | typed | 4.49 | 5.80 | 6.6 | 58.6 | 0 | adopted_resident |
| `stat_zscore` | stats | 4.56 | 4.86 | 6.5 | 15.8 | 0 | adopted_resident |
| `volume_downsample` | preprocess | 3.77 | 4.47 | 6.4 | 71.5 | 0 | adopted_resident |
| `coat_thickness_from_image` | polish | 5.00 | 3.37 | 6.4 | 16.9 | 0 | adopted_resident |
| `hx_gen_highpass` | halcon_ext | 3.57 | 3.46 | 6.3 | 20.0 | 0 | adopted_resident |
| `lights_fit_from_sphere` | tacscalib | 1.35 | 6.72 | 6.1 | 12.3 | 0 | adopted_resident |
| `vol_window_level` | gray | 3.23 | 6.53 | 6.0 | 13.6 | 0 | adopted_resident |
| `raw_apply_gains` | isp | 2.42 | 3.52 | 6.0 | 17.6 | 0 | adopted_resident |
| `deflicker` | restore | 2.87 | 3.96 | 5.8 | 9.5 | 0 | adopted_resident |
| `curvature_maps` | feature | 4.72 | 6.08 | 5.8 | 5.9 | 0 | adopted_resident |
| `tb_scale_y_funct_1d` | typed | 2.03 | 2.60 | 5.8 | 13.6 | 0 | adopted_resident |
| `tb_stat_zscore` | typed | 2.91 | 3.15 | 5.6 | 9.3 | 0 | adopted_resident |
| `tb_smooth_funct_1d_mean` | typed | 3.01 | 2.59 | 5.4 | 16.4 | 0 | adopted_resident |
| `compose_funct_1d` | function | 4.40 | 2.98 | 5.4 | 26.4 | 0 | adopted_resident |
| `cubic_photoelastic_birefringence` | photoelastic | 3.02 | 4.87 | 5.2 | 5.4 | 24 | match_slow |
| `marker_image` | tacslip | 1.94 | 4.10 | 5.2 | 8.6 | 0 | adopted_resident |
| `linescan_acquire` | linescan | 1.61 | 4.84 | 5.2 | 5.3 | 16 | match_slow |
| `film_grain` | post | 2.97 | 3.67 | 5.0 | 6.9 | 8 | match_slow |
| `specular_free_transform` | dichromatic | 3.40 | 4.14 | 5.0 | 58.5 | 0 | adopted_resident |
| `absolute_phase` | structured_light | 1.61 | 6.39 | 4.9 | 10.1 | 0 | pipeline |
| `cvar_cost_map` | roverslip | 2.23 | 3.65 | 4.7 | 5.0 | 56992 | match_slow |
| `tb_negate_funct_1d` | typed | 1.44 | 1.93 | 4.5 | 11.5 | 0 | pipeline |
| `ring_artifact_apply` | artifact | 1.10 | 1.54 | 4.4 | 19.3 | 8 | match_slow |
| `principal_stress` | photoelastic | 2.05 | 3.12 | 4.4 | 5.0 | 8 | match_slow |
| `beer_lambert_transmittance` | glassbody | 1.97 | 2.79 | 4.1 | 6.5 | 0 | pipeline |
| `gdilate` | morphology | 4.98 | 4.55 | 4.1 | 13.0 | 0 | pipeline |
| `annotate_panel_label` | paper | 3.33 | 6.77 | 4.1 | 5.5 | 0 | pipeline |
| `add_noise_white` | noise | 2.81 | 3.48 | 4.1 | 4.5 | 8 | match_slow |
| `regiongrowing_mean` | segmentation | 1.74 | 2.92 | 4.0 | 4.7 | 8 | match_slow |
| `unpremultiply` | composite | 3.36 | 3.23 | 3.9 | 4.3 | 8 | match_slow |
| `dl_aniso_diffusion` | smoothing | 2.68 | 3.72 | 3.7 | 4.0 | 0 | pipeline |
| `vol_reg_erode` | 3d | 1.98 | 2.49 | 3.6 | 4.5 | 8 | match_slow |
| `lens_shading_gain` | isp | 1.77 | 2.08 | 3.6 | 11.4 | 0 | pipeline |
| `blob_label` | connect | 1.98 | 1.87 | 3.5 | 5.7 | 0 | pipeline |
| `invert` | gray | 1.35 | 2.05 | 3.5 | 24.7 | 0 | pipeline |
| `vol_label` | regionprops | 3.26 | 4.40 | 3.5 | 50.9 | 0 | pipeline |
| `dem_height_frame_residual` | geodesy | 4.37 | 5.17 | 3.4 | 4.5 | 0 | pipeline |
| `alife_langton_ant` | artificial-life | 1.09 | 2.70 | 3.4 | 4.1 | 0 | pipeline |
| `bit_not` | gray | 2.32 | 1.83 | 3.4 | 12.5 | 0 | pipeline |
| `integrate_funct_1d` | function | 2.45 | 4.24 | 3.3 | 5.1 | 0 | pipeline |
| `axes_frame` | plot | 1.87 | 2.14 | 3.3 | 6.3 | 0 | pipeline |
| `tb_specular_free_transform` | typed | 1.56 | 4.54 | 3.3 | 15.4 | 0 | pipeline |
| `graph_activation_latency` | activity | 3.88 | 4.59 | 3.2 | 6.2 | 0 | pipeline |
| `coat_image` | polish | 1.33 | 2.64 | 3.1 | 3.3 | 8 | match_slow |
| `aug_jpeg_blocks` | augmentation | 1.58 | 2.82 | 3.0 | 3.1 | 16 | match_slow |
| `membrane_render_rgb` | tacsim | 1.12 | 2.57 | 3.0 | 3.2 | 8 | match_slow |
| `itof_capture` | itof | 2.07 | 2.53 | 2.9 | 3.0 | 8 | match_slow |
| `tb_local_std` | typed | 1.98 | 2.69 | 2.8 | 2.9 | 8 | match_slow |
| `aug_read_noise` | augmentation | 1.84 | 2.39 | 2.8 | 3.0 | 16 | match_slow |
| `tb_abs_funct_1d` | typed | 2.26 | 1.70 | 2.7 | 7.0 | 0 | pipeline |
| `awb_gains` | isp | 1.72 | 5.89 | 2.6 | 5.2 | 0 | pipeline |
| `anomaly_region_overlap` | anomaly_eval | 1.74 | 2.78 | 2.5 | 2.7 | 0 | pipeline |
| `morph_gradient3d` | morphology | 2.28 | 2.36 | 2.4 | 2.4 | 0 | pipeline |
| `brightness_contrast` | isp | 3.63 | 2.47 | 2.4 | 6.1 | 0 | pipeline |
| `regiongrowing` | segmentation | 1.12 | 1.82 | 2.3 | 3.2 | 8 | match_slow |
| `sdf_subtract` | sdf_csg | 1.01 | 1.83 | 2.3 | 39.4 | 0 | pipeline |
| `scene_cut_detection` | analysis | 1.69 | 2.16 | 2.3 | 3.6 | 0 | pipeline |
| `abs_funct_1d` | function | 1.08 | 1.49 | 2.3 | 4.9 | 0 | pipeline |
| `xsp_dct_lowpass` | frequency | 1.73 | 2.17 | 2.2 | 2.2 | 16 | match_slow |
| `aug_shot_noise` | augmentation | 1.07 | 2.08 | 2.2 | 2.2 | 8 | match_slow |
| `morph_erode3d` | morphology | 2.13 | 2.01 | 2.1 | 2.1 | 0 | pipeline |
| `xsp_chamfer_dist` | region | 1.08 | 1.66 | 2.0 | 2.4 | 8 | match_slow |
| `abs_image` | arithmetic | 1.78 | 3.20 | 2.0 | 6.2 | 0 | pipeline |
| `sensor_capture` | scene | 1.73 | 1.91 | 2.0 | 2.0 | 16 | match_slow |
| `tb_derivate_funct_1d` | typed | 2.64 | 1.42 | 1.9 | 6.1 | 0 | pipeline |
| `hx_fit_surface2` | halcon_ext | 1.72 | 2.01 | 1.9 | 1.9 | 0 | pipeline |
| `morph_open3d` | morphology | 1.87 | 1.84 | 1.9 | 1.9 | 0 | pipeline |
| `xsp_dct_denoise` | smoothing | 3.74 | 1.77 | 1.9 | 1.9 | 16 | match_slow |
| `tb_sensor_capture` | typed | 1.35 | 1.77 | 1.8 | 1.8 | 16 | match_slow |
| `derivate_funct_1d` | function | 1.42 | 2.18 | 1.8 | 2.5 | 0 | pipeline |
| `bessel` | numerics | 1.51 | 1.76 | 1.8 | 1.8 | 8 | match_slow |
| `sqrt_image` | arithmetic | 1.71 | 1.02 | 1.6 | 5.3 | 0 | pipeline |
| `mosaic_tiles_render` | npr | 1.50 | 1.48 | 1.5 | 1.6 | 16 | match_slow |
| `sobel3d` | feature | 1.22 | 1.42 | 1.5 | 1.6 | 0 | pipeline |
| `harris3d_keypoints` | feature_register | 1.10 | 1.41 | 1.4 | 1.4 | 0 | pipeline |
| `add_noise_distribution` | noise | 1.50 | 1.33 | 1.4 | 1.7 | 8 | match_slow |
| `chebyshev_coeffs_nd` | numerics | 1.07 | 1.23 | 1.2 | 1.3 | 16 | match_slow |
| `background_flatten` | surface_fit | 1.02 | 1.20 | 1.2 | 1.2 | 0 | pipeline |
| `lf_epi` | views | 1.05 | 1.02 | 1.1 | 3.3 | 0 | pipeline |
| `wrist_deflection_from_rgbd` | pegtactile | 1.04 | 1.09 | 1.1 | 1.1 | 0 | pipeline |
| `interp_cubic` | interp_poly | 3.07 | 1.00 | 1.0 | 1.0 | 16 | match_slow |


## 族別

| 族 | 全 | 採用 | 遅い | 固定形 | 不一致 | 判定不能 | 例外 | 包み | Pyループ | 未計測 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| typed | 123 | 24 | 38 | 35 | 6 | 1 | 3 | 0 | 0 | 0 |
| edges | 64 | 27 | 2 | 0 | 6 | 0 | 0 | 19 | 0 | 7 |
| segmentation | 54 | 12 | 8 | 0 | 0 | 0 | 0 | 28 | 0 | 2 |
| gray | 52 | 18 | 5 | 0 | 0 | 0 | 0 | 14 | 1 | 1 |
| smoothing | 50 | 16 | 6 | 0 | 0 | 0 | 1 | 17 | 0 | 8 |
| halcon_ext | 43 | 13 | 16 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| morphology | 43 | 17 | 2 | 0 | 0 | 0 | 2 | 14 | 1 | 0 |
| features | 33 | 1 | 7 | 0 | 0 | 2 | 0 | 20 | 0 | 3 |
| geometry | 32 | 13 | 5 | 1 | 0 | 0 | 1 | 8 | 0 | 2 |
| transform | 32 | 4 | 7 | 6 | 0 | 0 | 0 | 1 | 4 | 9 |
| texture | 28 | 13 | 2 | 0 | 0 | 0 | 0 | 13 | 0 | 0 |
| render | 24 | 2 | 4 | 10 | 1 | 4 | 2 | 0 | 0 | 1 |
| function | 23 | 2 | 11 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| rank | 23 | 17 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 1 |
| frequency | 22 | 14 | 2 | 0 | 0 | 0 | 0 | 2 | 0 | 2 |
| omni360 | 22 | 3 | 8 | 5 | 0 | 2 | 0 | 0 | 1 | 1 |
| bridge | 18 | 6 | 4 | 2 | 1 | 0 | 0 | 0 | 2 | 0 |
| contour | 18 | 5 | 0 | 5 | 0 | 1 | 1 | 5 | 1 | 0 |
| sensorchar | 17 | 3 | 2 | 3 | 0 | 2 | 0 | 0 | 0 | 7 |
| polarization | 16 | 1 | 1 | 11 | 0 | 0 | 0 | 0 | 0 | 2 |
| tactorque | 16 | 4 | 2 | 9 | 0 | 1 | 0 | 0 | 0 | 0 |
| carla | 15 | 3 | 0 | 9 | 0 | 2 | 0 | 0 | 0 | 0 |
| feature | 15 | 6 | 3 | 3 | 0 | 0 | 0 | 1 | 0 | 0 |
| paper | 15 | 9 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 1 |
| ball | 14 | 0 | 0 | 12 | 0 | 2 | 0 | 0 | 0 | 0 |
| extra | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14 |
| restoration | 14 | 5 | 1 | 1 | 0 | 0 | 0 | 6 | 1 | 0 |
| medial | 13 | 3 | 1 | 0 | 1 | 0 | 0 | 6 | 0 | 2 |
| nary | 13 | 1 | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| puck | 13 | 0 | 0 | 11 | 0 | 2 | 0 | 0 | 0 | 0 |
| surface | 13 | 6 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 |
| tacslip | 13 | 3 | 1 | 3 | 2 | 2 | 0 | 0 | 0 | 0 |
| 3d | 12 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| artificial-life | 12 | 9 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| estimation | 12 | 0 | 1 | 2 | 0 | 3 | 0 | 0 | 0 | 6 |
| flow | 12 | 0 | 2 | 5 | 0 | 2 | 2 | 0 | 0 | 0 |
| illusion | 12 | 0 | 0 | 12 | 0 | 0 | 0 | 0 | 0 | 0 |
| isp | 12 | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| sdf_csg | 12 | 1 | 2 | 7 | 0 | 0 | 0 | 0 | 0 | 0 |
| wave | 12 | 4 | 1 | 5 | 0 | 0 | 1 | 0 | 0 | 1 |
| granular | 11 | 0 | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 8 |
| graph | 11 | 0 | 0 | 2 | 0 | 0 | 2 | 0 | 7 | 0 |
| perpetual | 11 | 0 | 0 | 7 | 0 | 0 | 4 | 0 | 0 | 0 |
| scene | 11 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 8 |
| signal | 11 | 3 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| terrain | 11 | 7 | 0 | 3 | 0 | 1 | 0 | 0 | 0 | 0 |
| arithmetic | 10 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| augmentation | 10 | 7 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| color | 10 | 0 | 4 | 0 | 1 | 0 | 0 | 3 | 0 | 0 |
| diabolo | 10 | 0 | 0 | 7 | 0 | 3 | 0 | 0 | 0 | 0 |
| linalg | 10 | 1 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 1 |
| polish | 10 | 3 | 1 | 3 | 0 | 1 | 0 | 0 | 1 | 0 |
| complex | 9 | 3 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| numerics | 9 | 0 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| pegsym | 9 | 0 | 1 | 3 | 0 | 3 | 0 | 2 | 0 | 0 |
| photoelastic | 9 | 2 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| roverslip | 9 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 1 |
| structured_light | 9 | 3 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 |
| tacsim | 9 | 2 | 2 | 2 | 1 | 2 | 0 | 0 | 0 | 0 |
| algebra | 8 | 1 | 2 | 3 | 0 | 2 | 0 | 0 | 0 | 0 |
| cutting | 8 | 0 | 1 | 4 | 0 | 3 | 0 | 0 | 0 | 0 |
| field | 8 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| motion | 8 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| segment | 8 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| shape_from_polarization | 8 | 2 | 0 | 3 | 0 | 1 | 0 | 0 | 1 | 0 |
| synth | 8 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 1 |
| tem | 8 | 4 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| anomaly_eval | 7 | 1 | 0 | 0 | 0 | 4 | 0 | 0 | 1 | 0 |
| braidpath | 7 | 0 | 0 | 1 | 0 | 3 | 1 | 0 | 2 | 0 |
| decomposition | 7 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| domain | 7 | 1 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| imaging | 7 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| lockin | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |
| pegsim | 7 | 3 | 0 | 1 | 0 | 1 | 2 | 0 | 0 | 0 |
| pegtactile | 7 | 0 | 0 | 3 | 0 | 3 | 0 | 0 | 0 | 0 |
| perceptual | 7 | 2 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| photometric | 7 | 3 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 |
| post | 7 | 6 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| spectral | 7 | 1 | 0 | 1 | 3 | 0 | 1 | 0 | 0 | 1 |
| stats | 7 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| tacdome | 7 | 1 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| tacscalib | 7 | 1 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| annotate3d | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| appearance | 6 | 2 | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 1 |
| classify | 6 | 3 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| colorspace | 6 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| composite | 6 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| compression | 6 | 0 | 1 | 0 | 0 | 1 | 0 | 2 | 0 | 2 |
| curvature | 6 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 3 |
| descriptor | 6 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 2 |
| fidelity | 6 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 1 |
| grind | 6 | 1 | 1 | 2 | 0 | 2 | 0 | 0 | 0 | 0 |
| light_transport | 6 | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| matched | 6 | 2 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| physics | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| pxrd | 6 | 1 | 0 | 2 | 1 | 0 | 1 | 0 | 1 | 0 |
| region | 6 | 3 | 2 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| regionprops | 6 | 0 | 3 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| subpix | 6 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| ttc | 6 | 3 | 0 | 2 | 0 | 1 | 0 | 0 | 0 | 0 |
| agv | 5 | 0 | 0 | 1 | 0 | 4 | 0 | 0 | 0 | 0 |
| anomaly_patch | 5 | 1 | 0 | 2 | 0 | 0 | 1 | 0 | 1 | 0 |
| artifact | 5 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| balltrack | 5 | 0 | 0 | 3 | 0 | 2 | 0 | 0 | 0 | 0 |
| geodesy | 5 | 2 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| illumination | 5 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 3 |
| information | 5 | 1 | 3 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| interp_poly | 5 | 0 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| level | 5 | 3 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| light | 5 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| match_localize | 5 | 0 | 0 | 0 | 0 | 1 | 4 | 0 | 0 | 0 |
| matching | 5 | 1 | 0 | 1 | 0 | 2 | 0 | 0 | 0 | 1 |
| material | 5 | 1 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 1 |
| measure | 5 | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| measure1d | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| morph | 5 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| npr | 5 | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| overlay | 5 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| pixelshift | 5 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 3 |
| plot | 5 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 1 |
| prepare | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| refine | 5 | 0 | 2 | 2 | 0 | 1 | 0 | 0 | 0 | 0 |
| riesz | 5 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| scoop | 5 | 1 | 0 | 1 | 0 | 3 | 0 | 0 | 0 | 0 |
| score | 5 | 1 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| sem | 5 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 1 | 1 |
| sprite | 5 | 2 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| swarmflow | 5 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| tactile | 5 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| tomography | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| transport | 5 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 3 |
| two_view | 5 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 1 |
| visualise | 5 | 0 | 0 | 3 | 0 | 0 | 2 | 0 | 0 | 0 |
| watervision | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| assess | 4 | 0 | 0 | 2 | 0 | 1 | 0 | 0 | 1 | 0 |
| coherent | 4 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| deflectometry | 4 | 2 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| depth | 4 | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| dichromatic | 4 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| estimate | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| finish | 4 | 1 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| fit | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| gsplat | 4 | 0 | 0 | 3 | 0 | 1 | 0 | 0 | 0 | 0 |
| hydrology | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| macro | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| match | 4 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 1 | 0 |
| occupancy | 4 | 1 | 0 | 2 | 0 | 1 | 0 | 0 | 0 | 0 |
| ozaki | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| pointer | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| process | 4 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| range_image | 4 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| recursive | 4 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| refocus | 4 | 0 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| reservoir | 4 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| shape | 4 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| simulate | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| spectral_xray | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| stroke | 4 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| surface_fit | 4 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| threshold | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| views | 4 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| activity | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| analysis | 3 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| artistic | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| bearing | 3 | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| caliper | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| change | 3 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| colordiff | 3 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 1 |
| compose | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| convert | 3 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| counting | 3 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| curvilinear | 3 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| decide | 3 | 0 | 0 | 0 | 0 | 2 | 1 | 0 | 0 | 0 |
| decode | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| deform | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| deformation | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| detect | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dimension | 3 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 2 |
| direction | 3 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 2 |
| dual | 3 | 0 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| extract | 3 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| forward | 3 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 1 |
| fpm | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| freeform | 3 | 0 | 0 | 1 | 0 | 0 | 2 | 0 | 0 | 0 |
| furniture | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| geom_transform | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| geometric | 3 | 0 | 0 | 1 | 0 | 2 | 0 | 0 | 0 | 0 |
| glassbody | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| gradient | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| grating_interf | 3 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| io | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| lidar_projection | 3 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| looming | 3 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| model | 3 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 1 |
| moire_align | 3 | 0 | 0 | 1 | 0 | 2 | 0 | 0 | 0 | 0 |
| mt | 3 | 0 | 0 | 2 | 0 | 1 | 0 | 0 | 0 | 0 |
| noise | 3 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| oct | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 |
| path | 3 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| photometry | 3 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 1 |
| plant | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| plenoptic | 3 | 0 | 0 | 1 | 0 | 2 | 0 | 0 | 0 | 0 |
| probe | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| quality | 3 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| reconstruct | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| reflectance | 3 | 0 | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| rle_region | 3 | 0 | 0 | 0 | 0 | 2 | 1 | 0 | 0 | 0 |
| sensor | 3 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| sensorgeneral | 3 | 2 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| skyline | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| slice | 3 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| solid | 3 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| space_carving | 3 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 2 |
| split | 3 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| sun | 3 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| symmetry | 3 | 0 | 0 | 2 | 0 | 1 | 0 | 0 | 0 | 0 |
| synthesis | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| temporal | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| time | 3 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| traffic | 3 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 |
| tsdf_fusion | 3 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 |
| variation | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| visibility | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| watermark | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| watershed3d | 3 | 0 | 0 | 0 | 1 | 0 | 0 | 2 | 0 | 0 |
| window | 3 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| align | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| background | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| beamform | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| boundary | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| calibrate | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| code | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| coding | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| colorize | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| core | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| cosmic | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| course | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| crossing | 2 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| cube | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| decompose | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| depth_denoise | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| describe | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |
| dtof | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| dynsys | 2 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| feature_register | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| fourier | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gaussians | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| geodesic | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |
| grow | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| identifiability | 2 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| image | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| imaging_sim | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| interface | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| itof | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| keypoint | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| lamina | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| lidar | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| loop | 2 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 |
| match_pose | 2 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| mesh_process | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| metrics | 2 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| order | 2 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| pairs | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| pixel | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| pl | 2 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| plan_use | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| plane_sweep_stereo | 2 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| preprocess | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| radiosity | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| report | 2 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| roadjp | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| robust | 2 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| sample | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| selfmotion | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| series | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| stack | 2 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| stimulus | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| target | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| tile | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| validate | 2 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| volume | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| aggregate | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| alias | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| ballworld | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| barcode | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| blend | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| calibration | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| camera | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| capability | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| chart | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| chromatic | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| circuit | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| compare | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| connect | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| construct | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| copy_move | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| curve | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| degree | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| denoise | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| design | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| deviation | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| diagnose | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| doseunif | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| drawing | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| envelope | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| evaluate | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| export | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| film | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| filter | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| filtering | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| fusion | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| gcode | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| gicp | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| hash | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| inspect | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| integrate | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| intensity-transform | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| kendama | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| lateral | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| layout | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| linescan | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| locate | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| magnify | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mirror | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| moment_invariant | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| morphology/markers | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| motif | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| motion_io | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| multivariate | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| noncoaxial | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| null | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| orientation | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| palette | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| particle | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| pass | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| pegfail | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| pod | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| population | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| procrustes | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| project | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| registration | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| response | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| restore | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| self-similarity | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| shading | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stopping | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| stream | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| summary | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| superquadric | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| suppress | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| text | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| texture-feature | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| texture/shape-feature | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| theorem | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| tuning | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| view | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| watermedia | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| watershed | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |

## 手書きに回す族の順位

数式が numpy で書けているのに機械的に載らなかった op(例外・不一致)と、一致したのに5 倍に届かなかった op の数で並べた。包みは本体ライブラリの置き換えが要り、Python ループは先にベクトル化が要るので、列を分けた。

| 順位 | 族 | 例外+不一致+遅い | 包み | Pyループ |
|---:|---|---:|---:|---:|
| 1 | typed | 47 | 0 | 0 |
| 2 | halcon_ext | 19 | 0 | 0 |
| 3 | function | 11 | 0 | 0 |
| 4 | edges | 8 | 19 | 0 |
| 5 | omni360 | 8 | 0 | 1 |
| 6 | signal | 8 | 0 | 0 |
| 7 | segmentation | 8 | 28 | 0 |
| 8 | features | 7 | 20 | 0 |
| 9 | transform | 7 | 1 | 4 |
| 10 | render | 7 | 0 | 0 |
| 11 | smoothing | 7 | 17 | 0 |
| 12 | geometry | 6 | 8 | 0 |
| 13 | color | 5 | 3 | 0 |
| 14 | numerics | 5 | 0 | 0 |
| 15 | gray | 5 | 14 | 1 |

例外が集中する場所(同じ行で落ちる op の数、上位 15):

| 位置 | 件数 |
|---|---:|
| `bspline_surf.py:229` | 2 |
| `materials.py:239` | 2 |
| `geodesic3d.py:97` | 2 |
| `physarum_search.py:308` | 2 |
| `measure.py:228` | 2 |
| `accel_match.py:127` | 2 |
| `match3d.py:1209` | 2 |
| `render_shadow.py:418` | 2 |
| `seggraph.py:727` | 1 |
| `pxrd.py:1207` | 1 |
| `reconstruction.py:220` | 1 |
| `drivedecide.py:969` | 1 |
| `astrostack.py:1535` | 1 |
| `match3d.py:3282` | 1 |
| `mathgeometry.py:256` | 1 |
