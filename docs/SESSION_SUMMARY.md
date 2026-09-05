# Session Summary (auto-generated)

> 自動生成: `libexec/raptor-auto-summary` (Stop hook)
> 次回 ccr 起動時に CLAUDE.md SESSION START で自動的に読み取られる。

- **最終更新**: 2026-09-06 05:19:15
- **プロジェクト**: `C:/dev/projects/imgevolve`
- **ブランチ**: `master`

## 直近の git log

```
385fad845 0.1.9 の CHANGELOG を実際にやったことに合わせる
89404e12f CI が実際に走らせて初めて見えた 2 件を直す(どちらも「保証できない厳密さ」の主張)
871794cb6 例の索引の誤検出を直し、遅い例に時間予算を宣言できるようにする
e2d5f3320 auto: op_example_index.py 編集前 (2026-09-05 21:46)
46d30c04c 劣化の記録から「どの op か」が分かるようにする(潰れたキー 122 件を 0 に)
5459a5e7d auto: ops.py 編集前 (2026-09-05 21:40)
cd2d680dd 環境で変わるレジストリに依存する検査を宣言つき skip にする + 収集中断を一掃
a922ce202 CI: 同じ枝の古い run を打ち切る(concurrency group)
4234c44e0 op 探針の入力を 1 枚から 2 枚に広げる(門は在ったが入力が 1 つで見逃していた)
39a6d353e auto: test_op_probe_ledger.py 編集前 (2026-09-05 21:19)
```

## 現在の git status

```
M CHANGELOG.md
 M api.py
 M backends_decomp.py
 M docs/KNOWN_ISSUES.md
 M docs/OP_CATALOG.md
 M docs/SESSION_SUMMARY.md
 M docs/ops/2d/decomposition/dc_homomorphic.md
 M docs/ops/2d/decomposition/dc_local_contrast_norm.md
 M docs/ops/2d/decomposition/dc_retinex.md
 M docs/ops/2d/decomposition/dc_rpca_lowrank.md
 M docs/ops/2d/decomposition/dc_rpca_sparse.md
 M docs/ops/2d/decomposition/dc_structure_texture.md
 M docs/ops/2d/decomposition/dc_texture_residual.md
 M docs/ops/2d/rank/median.md
 M docs/ops/3d/curvature/estimate_normals.md
 M docs/ops/3d/curvature/gaussian_curvature.md
 M docs/ops/3d/curvature/mean_curvature.md
 M docs/ops/3d/curvature/principal_curvatures.md
 M docs/ops/3d/curvature/shape_index.md
 M docs/ops/3d/feature_register/compute_fpfh.md
 M docs/ops/3d/feature_register/harris3d_keypoints.md
 M docs/ops/3d/feature_register/iss_keypoints.md
 M docs/ops/3d/feature_register/register_fpfh.md
 M docs/ops/3d/feature_register/register_shot.md
 M docs/ops/3d/feature_register/register_spin.md
 M docs/ops/3d/feature_register/shot_descriptor.md
 M docs/ops/3d/robust_fit/fit_cone.md
 M docs/ops/3d/robust_fit/fit_ellipsoid.md
 M docs/ops/3d/robust_fit/fit_torus.md
 M docs/ops/3d/robust_fit/ransac_cylinder.md
 M docs/ops/3d/robust_fit/ransac_line.md
 M docs/ops/3d/robust_fit/ransac_plane.md
 M docs/ops/3d/robust_fit/ransac_sphere.md
 M docs/ops/3d/surface_fit/background_flatten.md
 M docs/ops/3d/surface_fit/eval_poly_surface.md
 M docs/ops/3d/surface_fit/fit_poly_surface.md
 M docs/ops/3d/surface_fit/surface_form_error.md
 M docs/ops/math/INDEX.md
 M docs/ops/math/linalg/mat_cond.md
 M docs/ops/math/linalg/mat_eigh.md
 M docs/ops/math/linalg/mat_lstsq.md
 M docs/ops/math/linalg/mat_pinv.md
 M docs/ops/math/linalg/mat_solve.md
 M docs/ops/math/linalg/mat_svd.md
 M examples/g1_policy_staged.py
 M examples2d.py
 M fullseye/OP_CATALOG.md
 M fullseye/__init__.py
 M pyproject.toml
 M studio_assets/op_help/3d/background_flatten.de.html
 M studio_assets/op_help/3d/background_flatten.en.html
 M studio_assets/op_help/3d/background_flatten.html
 M studio_assets/op_help/3d/background_flatten.ko.html
 M studio_assets/op_help/3d/background_flatten.tw.html
 M studio_assets/op_help/3d/background_flatten.zh.html
 M studio_assets/op_help/3d/compute_fpfh.de.html
 M studio_assets/op_help/3d/compute_fpfh.en.html
 M studio_assets/op_help/3d/compute_fpfh.html
 M studio_assets/op_help/3d/compute_fpfh.ko.html
 M studio_assets/op_help/3d/compute_fpfh.tw.html
 M studio_assets/op_help/3d/compute_fpfh.zh.html
 M studio_assets/op_help/3d/estimate_normals.de.html
 M studio_assets/op_help/3d/estimate_normals.en.html
 M studio_assets/op_help/3d/estimate_normals.html
 M studio_assets/op_help/3d/estimate_normals.ko.html
 M studio_assets/op_help/3d/estimate_normals.tw.html
 M studio_assets/op_help/3d/estimate_normals.zh.html
 M studio_assets/op_help/3d/eval_poly_surface.de.html
 M studio_assets/op_help/3d/eval_poly_surface.en.html
 M studio_assets/op_help/3d/eval_poly_surface.html
 M studio_assets/op_help/3d/eval_poly_surface.ko.html
 M studio_assets/op_help/3d/eval_poly_surface.tw.html
 M studio_assets/op_help/3d/eval_poly_surface.zh.html
 M studio_assets/op_help/3d/fit_cone.de.html
 M studio_assets/op_help/3d/fit_cone.en.html
 M studio_assets/op_help/3d/fit_cone.html
 M studio_assets/op_help/3d/fit_cone.ko.html
 M studio_assets/op_help/3d/fit_cone.tw.html
 M studio_assets/op_help/3d/fit_cone.zh.html
 M studio_assets/op_help/3d/fit_ellipsoid.de.html
 M studio_assets/op_help/3d/fit_ellipsoid.en.html
 M studio_assets/op_help/3d/fit_ellipsoid.html
 M studio_assets/op_help/3d/fit_ellipsoid.ko.html
 M studio_assets/op_help/3d/fit_ellipsoid.tw.html
 M studio_assets/op_help/3d/fit_ellipsoid.zh.html
 M studio_assets/op_help/3d/fit_poly_surface.de.html
 M studio_assets/op_help/3d/fit_poly_surface.en.html
 M studio_assets/op_help/3d/fit_poly_surface.html
 M studio_assets/op_help/3d/fit_poly_surface.ko.html
 M studio_assets/op_help/3d/fit_poly_surface.tw.html
 M studio_assets/op_help/3d/fit_poly_surface.zh.html
 M studio_assets/op_help/3d/fit_torus.de.html
 M studio_assets/op_help/3d/fit_torus.en.html
 M studio_assets/op_help/3d/fit_torus.html
 M studio_assets/op_help/3d/fit_torus.ko.html
 M studio_assets/op_help/3d/fit_torus.tw.html
 M studio_assets/op_help/3d/fit_torus.zh.html
 M studio_assets/op_help/3d/gaussian_curvature.de.html
 M studio_assets/op_help/3d/gaussian_curvature.en.html
 M studio_assets/op_help/3d/gaussian_curvature.html
 M studio_assets/op_help/3d/gaussian_curvature.ko.html
 M studio_assets/op_help/3d/gaussian_curvature.tw.html
 M studio_assets/op_help/3d/gaussian_curvature.zh.html
 M studio_assets/op_help/3d/harris3d_keypoints.de.html
 M studio_assets/op_help/3d/harris3d_keypoints.en.html
 M studio_assets/op_help/3d/harris3d_keypoints.html
 M studio_assets/op_help/3d/harris3d_keypoints.ko.html
 M studio_assets/op_help/3d/harris3d_keypoints.tw.html
 M studio_assets/op_help/3d/harris3d_keypoints.zh.html
 M studio_assets/op_help/3d/iss_keypoints.de.html
 M studio_assets/op_help/3d/iss_keypoints.en.html
 M studio_assets/op_help/3d/iss_keypoints.html
 M studio_assets/op_help/3d/iss_keypoints.ko.html
 M studio_assets/op_help/3d/iss_keypoints.tw.html
 M studio_assets/op_help/3d/iss_keypoints.zh.html
 M studio_assets/op_help/3d/mean_curvature.de.html
 M studio_assets/op_help/3d/mean_curvature.en.html
 M studio_assets/op_help/3d/mean_curvature.html
 M studio_assets/op_help/3d/mean_curvature.ko.html
 M studio_assets/op_help/3d/mean_curvature.tw.html
 M studio_assets/op_help/3d/mean_curvature.zh.html
 M studio_assets/op_help/3d/principal_curvatures.de.html
 M studio_assets/op_help/3d/principal_curvatures.en.html
 M studio_assets/op_help/3d/principal_curvatures.html
 M studio_assets/op_help/3d/principal_curvatures.ko.html
 M studio_assets/op_help/3d/principal_curvatures.tw.html
 M studio_assets/op_help/3d/principal_curvatures.zh.html
 M studio_assets/op_help/3d/ransac_cylinder.de.html
 M studio_assets/op_help/3d/ransac_cylinder.en.html
 M studio_assets/op_help/3d/ransac_cylinder.html
 M studio_assets/op_help/3d/ransac_cylinder.ko.html
 M studio_assets/op_help/3d/ransac_cylinder.tw.html
 M studio_assets/op_help/3d/ransac_cylinder.zh.html
 M studio_assets/op_help/3d/ransac_line.de.html
 M studio_assets/op_help/3d/ransac_line.en.html
 M studio_assets/op_help/3d/ransac_line.html
 M studio_assets/op_help/3d/ransac_line.ko.html
 M studio_assets/op_help/3d/ransac_line.tw.html
 M studio_assets/op_help/3d/ransac_line.zh.html
 M studio_assets/op_help/3d/ransac_plane.de.html
 M studio_assets/op_help/3d/ransac_plane.en.html
 M studio_assets/op_help/3d/ransac_plane.html
 M studio_assets/op_help/3d/ransac_plane.ko.html
 M studio_assets/op_help/3d/ransac_plane.tw.html
 M studio_assets/op_help/3d/ransac_plane.zh.html
 M studio_assets/op_help/3d/ransac_sphere.de.html
 M studio_assets/op_help/3d/ransac_sphere.en.html
 M studio_assets/op_help/3d/ransac_sphere.html
 M studio_assets/op_help/3d/ransac_sphere.ko.html
 M studio_assets/op_help/3d/ransac_sphere.tw.html
 M studio_assets/op_help/3d/ransac_sphere.zh.html
 M studio_assets/op_help/3d/register_fpfh.de.html
 M studio_assets/op_help/3d/register_fpfh.en.html
 M studio_assets/op_help/3d/register_fpfh.html
 M studio_assets/op_help/3d/register_fpfh.ko.html
 M studio_assets/op_help/3d/register_fpfh.tw.html
 M studio_assets/op_help/3d/register_fpfh.zh.html
 M studio_assets/op_help/3d/register_shot.de.html
 M studio_assets/op_help/3d/register_shot.en.html
 M studio_assets/op_help/3d/register_shot.html
 M studio_assets/op_help/3d/register_shot.ko.html
 M studio_assets/op_help/3d/register_shot.tw.html
 M studio_assets/op_help/3d/register_shot.zh.html
 M studio_assets/op_help/3d/register_spin.de.html
 M studio_assets/op_help/3d/register_spin.en.html
 M studio_assets/op_help/3d/register_spin.html
 M studio_assets/op_help/3d/register_spin.ko.html
 M studio_assets/op_help/3d/register_spin.tw.html
 M studio_assets/op_help/3d/register_spin.zh.html
 M studio_assets/op_help/3d/shape_index.de.html
 M studio_assets/op_help/3d/shape_index.en.html
 M studio_assets/op_help/3d/shape_index.html
 M studio_assets/op_help/3d/shape_index.ko.html
 M studio_assets/op_help/3d/shape_index.tw.html
 M studio_assets/op_help/3d/shape_index.zh.html
 M studio_assets/op_help/3d/shot_descriptor.de.html
 M studio_assets/op_help/3d/shot_descriptor.en.html
 M studio_assets/op_help/3d/shot_descriptor.html
 M studio_assets/op_help/3d/shot_descriptor.ko.html
 M studio_assets/op_help/3d/shot_descriptor.tw.html
 M studio_assets/op_help/3d/shot_descriptor.zh.html
 M studio_assets/op_help/3d/surface_form_error.de.html
 M studio_assets/op_help/3d/surface_form_error.en.html
 M studio_assets/op_help/3d/surface_form_error.html
 M studio_assets/op_help/3d/surface_form_error.ko.html
 M studio_assets/op_help/3d/surface_form_error.tw.html
 M studio_assets/op_help/3d/surface_form_error.zh.html
 M studio_assets/op_help/dc_homomorphic.de.html
 M studio_assets/op_help/dc_homomorphic.en.html
 M studio_assets/op_help/dc_homomorphic.html
 M studio_assets/op_help/dc_homomorphic.ja.html
 M studio_assets/op_help/dc_homomorphic.ko.html
 M studio_assets/op_help/dc_homomorphic.tw.html
 M studio_assets/op_help/dc_homomorphic.zh.html
 M studio_assets/op_help/dc_local_contrast_norm.de.html
 M studio_assets/op_help/dc_local_contrast_norm.en.html
 M studio_assets/op_help/dc_local_contrast_norm.html
 M studio_assets/op_help/dc_local_contrast_norm.ja.html
 M studio_assets/op_help/dc_local_contrast_norm.ko.html
 M studio_assets/op_help/dc_local_contrast_norm.tw.html
 M studio_assets/op_help/dc_local_contrast_norm.zh.html
 M studio_assets/op_help/dc_retinex.de.html
 M studio_assets/op_help/dc_retinex.en.html
 M studio_assets/op_help/dc_retinex.html
 M studio_assets/op_help/dc_retinex.ja.html
 M studio_assets/op_help/dc_retinex.ko.html
 M studio_assets/op_help/dc_retinex.tw.html
 M studio_assets/op_help/dc_retinex.zh.html
 M studio_assets/op_help/dc_rpca_lowrank.de.html
 M studio_assets/op_help/dc_rpca_lowrank.en.html
 M studio_assets/op_help/dc_rpca_lowrank.html
 M studio_assets/op_help/dc_rpca_lowrank.ja.html
 M studio_assets/op_help/dc_rpca_lowrank.ko.html
 M studio_assets/op_help/dc_rpca_lowrank.tw.html
 M studio_assets/op_help/dc_rpca_lowrank.zh.html
 M studio_assets/op_help/dc_rpca_sparse.de.html
 M studio_assets/op_help/dc_rpca_sparse.en.html
 M studio_assets/op_help/dc_rpca_sparse.html
 M studio_assets/op_help/dc_rpca_sparse.ja.html
 M studio_assets/op_help/dc_rpca_sparse.ko.html
 M studio_assets/op_help/dc_rpca_sparse.tw.html
 M studio_assets/op_help/dc_rpca_sparse.zh.html
 M studio_assets/op_help/dc_structure_texture.de.html
 M studio_assets/op_help/dc_structure_texture.en.html
 M studio_assets/op_help/dc_structure_texture.html
 M studio_assets/op_help/dc_structure_texture.ja.html
 M studio_assets/op_help/dc_structure_texture.ko.html
 M studio_assets/op_help/dc_structure_texture.tw.html
 M studio_assets/op_help/dc_structure_texture.zh.html
 M studio_assets/op_help/dc_texture_residual.de.html
 M studio_assets/op_help/dc_texture_residual.en.html
 M studio_assets/op_help/dc_texture_residual.html
 M studio_assets/op_help/dc_texture_residual.ja.html
 M studio_assets/op_help/dc_texture_residual.ko.html
 M studio_assets/op_help/dc_texture_residual.tw.html
 M studio_assets/op_help/dc_texture_residual.zh.html
 M studio_assets/op_help/math/mat_cond.de.html
 M studio_assets/op_help/math/mat_cond.en.html
 M studio_assets/op_help/math/mat_cond.html
 M studio_assets/op_help/math/mat_cond.ja.html
 M studio_assets/op_help/math/mat_cond.ko.html
 M studio_assets/op_help/math/mat_cond.tw.html
 M studio_assets/op_help/math/mat_cond.zh.html
 M studio_assets/op_help/math/mat_eigh.de.html
 M studio_assets/op_help/math/mat_eigh.en.html
 M studio_assets/op_help/math/mat_eigh.html
 M studio_assets/op_help/math/mat_eigh.ja.html
 M studio_assets/op_help/math/mat_eigh.ko.html
 M studio_assets/op_help/math/mat_eigh.tw.html
 M studio_assets/op_help/math/mat_eigh.zh.html
 M studio_assets/op_help/math/mat_lstsq.de.html
 M studio_assets/op_help/math/mat_lstsq.en.html
 M studio_assets/op_help/math/mat_lstsq.html
 M studio_assets/op_help/math/mat_lstsq.ja.html
 M studio_assets/op_help/math/mat_lstsq.ko.html
 M studio_assets/op_help/math/mat_lstsq.tw.html
 M studio_assets/op_help/math/mat_lstsq.zh.html
 M studio_assets/op_help/math/mat_pinv.de.html
 M studio_assets/op_help/math/mat_pinv.en.html
 M studio_assets/op_help/math/mat_pinv.html
 M studio_assets/op_help/math/mat_pinv.ja.html
 M studio_assets/op_help/math/mat_pinv.ko.html
 M studio_assets/op_help/math/mat_pinv.tw.html
 M studio_assets/op_help/math/mat_pinv.zh.html
 M studio_assets/op_help/math/mat_solve.de.html
 M studio_assets/op_help/math/mat_solve.en.html
 M studio_assets/op_help/math/mat_solve.html
 M studio_assets/op_help/math/mat_solve.ja.html
 M studio_assets/op_help/math/mat_solve.ko.html
 M studio_assets/op_help/math/mat_solve.tw.html
 M studio_assets/op_help/math/mat_solve.zh.html
 M studio_assets/op_help/math/mat_svd.de.html
 M studio_assets/op_help/math/mat_svd.en.html
 M studio_assets/op_help/math/mat_svd.html
 M studio_assets/op_help/math/mat_svd.ja.html
 M studio_assets/op_help/math/mat_svd.ko.html
 M studio_assets/op_help/math/mat_svd.tw.html
 M studio_assets/op_help/math/mat_svd.zh.html
 M studio_assets/op_help/median.de.html
 M studio_assets/op_help/median.en.html
 M studio_assets/op_help/median.html
 M studio_assets/op_help/median.ko.html
 M studio_assets/op_help/median.tw.html
 M studio_assets/op_help/median.zh.html
 M tests/test_g1_policy.py
?? docs/ops/math/guides/blas_threads_and_memory.md
?? examples/blas_thread_budget.py
?? fsthreads.py
?? studio_assets/op_help/guide_blas_threads_and_memory.de.html
?? studio_assets/op_help/guide_blas_threads_and_memory.en.html
?? studio_assets/op_help/guide_blas_threads_and_memory.html
?? studio_assets/op_help/guide_blas_threads_and_memory.ko.html
?? studio_assets/op_help/guide_blas_threads_and_memory.tw.html
?? studio_assets/op_help/guide_blas_threads_and_memory.zh.html
?? tests/test_blas_thread_discipline.py
?? tests/test_fsthreads.py
```

## 直近 2 時間に変更されたファイル

```
05:17 docs/SESSION_SUMMARY.md
05:03 .hypothesis/constants/140283103ae3c6c1
05:03 .hypothesis/constants/3425a1dc61c633e7
05:03 .hypothesis/constants/e394cb09161cbe24
05:03 .hypothesis/constants/095b138a32bc81bb
05:03 .hypothesis/constants/2ca2c5ceb36316f2
05:03 .pytest_cache/v/cache/nodeids
05:03 .pytest_cache/v/cache/lastfailed
05:02 fullseye/OP_CATALOG.md
05:02 docs/OP_CATALOG.md
05:02 studio_assets/op_help/guide_video_streaming.tw.html
05:02 studio_assets/op_help/guide_video_streaming.ko.html
05:02 studio_assets/op_help/guide_video_streaming.de.html
05:02 studio_assets/op_help/guide_video_streaming.zh.html
05:02 studio_assets/op_help/guide_video_streaming.html
```

---

> このファイルは毎ターン自動上書きされます。**手動で書いた内容は失われます。**
> 永続化したいメモは `docs/PROGRESS.md`、`docs/next_plan.md`、または `docs/NOTES.md` を使ってください。
