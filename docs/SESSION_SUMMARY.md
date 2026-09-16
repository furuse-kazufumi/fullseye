# Session Summary (auto-generated)

> 自動生成: `libexec/raptor-auto-summary` (Stop hook)
> 次回 ccr 起動時に CLAUDE.md SESSION START で自動的に読み取られる。

- **最終更新**: 2026-09-16 22:39:23
- **プロジェクト**: `C:/dev/projects/imgevolve`
- **ブランチ**: `master`

## 直近の git log

```
57dbcc5e4 実測した事実の差し込みを 6 言語で出す —— docstring に連結していたのが設計の誤りだった
acc21258e CI だけが赤だった原因 —— 門が次元をまたぐ同名ノートを、環境ごとに違う側から掴んでいた
d04d2ddf3 空フレームの掃きが image->region を落としていた —— 直したら「欠陥 100%」になる op が 20 本出た
d97049633 空フレームが全面誤検出に化ける不具合を 4 クラス直した(丸め屑が正規化で構造になる)
1a03dfcae 548 op すべてに第 2 実装を当て終えた —— 二重実装が相関故障を下げる実証つき
ad4360b3c triage が「壊れた第 2 実装」を「正規化の穴」と誤分類していた(偽の仕様穴 5 件)
d1e2ad7bb 無人実行が 1 本の不良 C で死んでいた —— 15 分間「走っている」と思い込んでいた
216162db0 CI を赤にしていた 3 件を直した —— 的を絞ったテストだけ見ていて 10 コミット気づかなかった
0a561655a 失敗した op の記録が消えていた —— 「失敗が不可視」は「発見ゼロ」と同じ形の事故
fb5fd5303 連結性の測定器: 陽性対照は通したが、**収穫はほぼゼロ**だった(負の結果として残す)
```

## 現在の git status

```
M docs/AI_RAG_GUIDE.de.md
 M docs/AI_RAG_GUIDE.en.md
 M docs/AI_RAG_GUIDE.ko.md
 M docs/AI_RAG_GUIDE.md
 M docs/AI_RAG_GUIDE.tw.md
 M docs/AI_RAG_GUIDE.zh.md
 M docs/DESIGN_NOTES.de.md
 M docs/DESIGN_NOTES.en.md
 M docs/DESIGN_NOTES.ko.md
 M docs/DESIGN_NOTES.md
 M docs/DESIGN_NOTES.tw.md
 M docs/DESIGN_NOTES.zh.md
 M docs/OP_CATALOG.md
 M docs/OP_INDEX.json
 M docs/README.de.md
 M docs/README.en.md
 M docs/README.ko.md
 M docs/README.md
 M docs/README.tw.md
 M docs/README.zh.md
 M docs/SESSION_SUMMARY.md
 M docs/design_notes.json
 M docs/ops/2d/INDEX.md
 M docs/ops/2d/texture/cooc_feature_matrix.md
 M docs/ops/2d/texture/deviation_image.md
 M docs/ops/2d/texture/entropy_image.md
 M docs/ops/2d/texture/f2_symmetry.md
 M docs/ops/2d/texture/gabor.md
 M docs/ops/2d/texture/gen_gabor.md
 M docs/ops/2d/texture/sk_entropy.md
 M docs/ops/2d/texture/sk_frangi.md
 M docs/ops/2d/texture/sk_gabor.md
 M docs/ops/2d/texture/sk_hessian.md
 M docs/ops/2d/texture/sk_lbp.md
 M docs/ops/2d/texture/sk_meijering.md
 M docs/ops/2d/texture/sk_shape_index.md
 M docs/ops/2d/texture/std_filter.md
 M docs/ops/2d/texture/texture_laws.md
 M docs/ops/2d/texture/tf_census_transform.md
 M docs/ops/2d/texture/tf_rank_transform.md
 M docs/ops/2d/texture/xsk2_hog.md
 M docs/ops/2d/texture/xsk_meijering.md
 M docs/ops/2d/texture/xsk_sato.md
 M docs/ops/2d/texture/xsk_struct_coherence.md
 M docs/ops/2d/texture/xsp_hilbert_env.md
 M docs/ops/INDEX.de.md
 M docs/ops/INDEX.en.md
 M docs/ops/INDEX.ko.md
 M docs/ops/INDEX.md
 M docs/ops/INDEX.tw.md
 M docs/ops/INDEX.zh.md
 M docs/ops/SAMPLES.md
 M docs/ops/_fig/adaptive_gauss_thresh.a.jpg
 M docs/ops/_fig/adaptive_gauss_thresh.b.jpg
 M docs/ops/_fig/adaptive_gauss_thresh.inputs.jpg
 M docs/ops/_fig/adaptive_gauss_thresh.png
 M docs/ops/_fig/deviation_image.a.jpg
 M docs/ops/_fig/deviation_image.inputs.jpg
 M docs/ops/_fig/deviation_image.png
 M docs/ops/_fig/dots_image.a.jpg
 M docs/ops/_fig/dots_image.inputs.jpg
 M docs/ops/_fig/dots_image.png
 M docs/ops/_fig/dyn_threshold.a.jpg
 M docs/ops/_fig/dyn_threshold.b.jpg
 M docs/ops/_fig/dyn_threshold.inputs.jpg
 M docs/ops/_fig/dyn_threshold.png
 M docs/ops/_fig/figures.json
 M docs/ops/_fig/frei_dir.inputs.jpg
 M docs/ops/_fig/frei_dir.png
 M docs/ops/_fig/kirsch_dir.inputs.jpg
 M docs/ops/_fig/kirsch_dir.png
 M docs/ops/_fig/laplace_of_gauss.a.jpg
 M docs/ops/_fig/laplace_of_gauss.inputs.jpg
 M docs/ops/_fig/laplace_of_gauss.png
 M docs/ops/_fig/local_threshold.a.jpg
 M docs/ops/_fig/local_threshold.b.jpg
 M docs/ops/_fig/local_threshold.inputs.jpg
 M docs/ops/_fig/local_threshold.png
 M docs/ops/_fig/log.a.jpg
 M docs/ops/_fig/log.inputs.jpg
 M docs/ops/_fig/log.png
 M docs/ops/_fig/robinson_dir.inputs.jpg
 M docs/ops/_fig/robinson_dir.png
 M docs/ops/_fig/tb_project.chain.jpg
 M docs/ops/_fig/tb_project.inputs.jpg
 M docs/ops/_fig/tb_project.png
 M docs/ops/_fig/zero_crossing.a.jpg
 M docs/ops/_fig/zero_crossing.inputs.jpg
 M docs/ops/_fig/zero_crossing.png
 M docs/ops/_fig/zero_crossing_sub_pix.a.jpg
 M docs/ops/_fig/zero_crossing_sub_pix.inputs.jpg
 M docs/ops/_fig/zero_crossing_sub_pix.png
 M examples/gallery2d_texture_freq.py
 M fullseye/OP_CATALOG.md
 M fullseye/data/OP_INDEX.json
 M fullseye/data/OP_NOTES.json
 M fullseye/skill_template/SKILL.md
 M ops.py
 M skills/fullseye-ops/SKILL.md
 M studio_assets/op_help/cooc_feature_matrix.de.html
 M studio_assets/op_help/cooc_feature_matrix.en.html
 M studio_assets/op_help/cooc_feature_matrix.html
 M studio_assets/op_help/cooc_feature_matrix.ko.html
 M studio_assets/op_help/cooc_feature_matrix.tw.html
 M studio_assets/op_help/cooc_feature_matrix.zh.html
 M studio_assets/op_help/deviation_image.de.html
 M studio_assets/op_help/deviation_image.en.html
 M studio_assets/op_help/deviation_image.html
 M studio_assets/op_help/deviation_image.ko.html
 M studio_assets/op_help/deviation_image.tw.html
 M studio_assets/op_help/deviation_image.zh.html
 M studio_assets/op_help/entropy_image.de.html
 M studio_assets/op_help/entropy_image.en.html
 M studio_assets/op_help/entropy_image.html
 M studio_assets/op_help/entropy_image.ko.html
 M studio_assets/op_help/entropy_image.tw.html
 M studio_assets/op_help/entropy_image.zh.html
 M studio_assets/op_help/f2_symmetry.de.html
 M studio_assets/op_help/f2_symmetry.en.html
 M studio_assets/op_help/f2_symmetry.html
 M studio_assets/op_help/f2_symmetry.ja.html
 M studio_assets/op_help/f2_symmetry.ko.html
 M studio_assets/op_help/f2_symmetry.tw.html
 M studio_assets/op_help/f2_symmetry.zh.html
 M studio_assets/op_help/fig/adaptive_gauss_thresh.png
 M studio_assets/op_help/fig/deviation_image.png
 M studio_assets/op_help/fig/dots_image.png
 M studio_assets/op_help/fig/dyn_threshold.png
 M studio_assets/op_help/fig/frei_dir.png
 M studio_assets/op_help/fig/kirsch_dir.png
 M studio_assets/op_help/fig/laplace_of_gauss.png
 M studio_assets/op_help/fig/local_threshold.png
 M studio_assets/op_help/fig/log.png
 M studio_assets/op_help/fig/robinson_dir.png
 M studio_assets/op_help/fig/tb_project.png
 M studio_assets/op_help/fig/zero_crossing.png
 M studio_assets/op_help/fig/zero_crossing_sub_pix.png
 M studio_assets/op_help/gabor.de.html
 M studio_assets/op_help/gabor.en.html
 M studio_assets/op_help/gabor.html
 M studio_assets/op_help/gabor.ja.html
 M studio_assets/op_help/gabor.ko.html
 M studio_assets/op_help/gabor.tw.html
 M studio_assets/op_help/gabor.zh.html
 M studio_assets/op_help/gen_gabor.de.html
 M studio_assets/op_help/gen_gabor.en.html
 M studio_assets/op_help/gen_gabor.html
 M studio_assets/op_help/gen_gabor.ko.html
 M studio_assets/op_help/gen_gabor.tw.html
 M studio_assets/op_help/gen_gabor.zh.html
 M studio_assets/op_help/sk_entropy.de.html
 M studio_assets/op_help/sk_entropy.en.html
 M studio_assets/op_help/sk_entropy.html
 M studio_assets/op_help/sk_entropy.ko.html
 M studio_assets/op_help/sk_entropy.tw.html
 M studio_assets/op_help/sk_entropy.zh.html
 M studio_assets/op_help/sk_frangi.de.html
 M studio_assets/op_help/sk_frangi.en.html
 M studio_assets/op_help/sk_frangi.html
 M studio_assets/op_help/sk_frangi.ko.html
 M studio_assets/op_help/sk_frangi.tw.html
 M studio_assets/op_help/sk_frangi.zh.html
 M studio_assets/op_help/sk_gabor.de.html
 M studio_assets/op_help/sk_gabor.en.html
 M studio_assets/op_help/sk_gabor.html
 M studio_assets/op_help/sk_gabor.ko.html
 M studio_assets/op_help/sk_gabor.tw.html
 M studio_assets/op_help/sk_gabor.zh.html
 M studio_assets/op_help/sk_hessian.de.html
 M studio_assets/op_help/sk_hessian.en.html
 M studio_assets/op_help/sk_hessian.html
 M studio_assets/op_help/sk_hessian.ko.html
 M studio_assets/op_help/sk_hessian.tw.html
 M studio_assets/op_help/sk_hessian.zh.html
 M studio_assets/op_help/sk_lbp.de.html
 M studio_assets/op_help/sk_lbp.en.html
 M studio_assets/op_help/sk_lbp.html
 M studio_assets/op_help/sk_lbp.ko.html
 M studio_assets/op_help/sk_lbp.tw.html
 M studio_assets/op_help/sk_lbp.zh.html
 M studio_assets/op_help/sk_meijering.de.html
 M studio_assets/op_help/sk_meijering.en.html
 M studio_assets/op_help/sk_meijering.html
 M studio_assets/op_help/sk_meijering.ko.html
 M studio_assets/op_help/sk_meijering.tw.html
 M studio_assets/op_help/sk_meijering.zh.html
 M studio_assets/op_help/sk_shape_index.de.html
 M studio_assets/op_help/sk_shape_index.en.html
 M studio_assets/op_help/sk_shape_index.html
 M studio_assets/op_help/sk_shape_index.ko.html
 M studio_assets/op_help/sk_shape_index.tw.html
 M studio_assets/op_help/sk_shape_index.zh.html
 M studio_assets/op_help/std_filter.de.html
 M studio_assets/op_help/std_filter.en.html
 M studio_assets/op_help/std_filter.html
 M studio_assets/op_help/std_filter.ko.html
 M studio_assets/op_help/std_filter.tw.html
 M studio_assets/op_help/std_filter.zh.html
 M studio_assets/op_help/texture_laws.de.html
 M studio_assets/op_help/texture_laws.en.html
 M studio_assets/op_help/texture_laws.html
 M studio_assets/op_help/texture_laws.ko.html
 M studio_assets/op_help/texture_laws.tw.html
 M studio_assets/op_help/texture_laws.zh.html
 M studio_assets/op_help/tf_census_transform.de.html
 M studio_assets/op_help/tf_census_transform.en.html
 M studio_assets/op_help/tf_census_transform.html
 M studio_assets/op_help/tf_census_transform.ja.html
 M studio_assets/op_help/tf_census_transform.ko.html
 M studio_assets/op_help/tf_census_transform.tw.html
 M studio_assets/op_help/tf_census_transform.zh.html
 M studio_assets/op_help/tf_rank_transform.de.html
 M studio_assets/op_help/tf_rank_transform.en.html
 M studio_assets/op_help/tf_rank_transform.html
 M studio_assets/op_help/tf_rank_transform.ja.html
 M studio_assets/op_help/tf_rank_transform.ko.html
 M studio_assets/op_help/tf_rank_transform.tw.html
 M studio_assets/op_help/tf_rank_transform.zh.html
 M studio_assets/op_help/xsk2_hog.de.html
 M studio_assets/op_help/xsk2_hog.en.html
 M studio_assets/op_help/xsk2_hog.html
 M studio_assets/op_help/xsk2_hog.ko.html
 M studio_assets/op_help/xsk2_hog.tw.html
 M studio_assets/op_help/xsk2_hog.zh.html
 M studio_assets/op_help/xsk_meijering.de.html
 M studio_assets/op_help/xsk_meijering.en.html
 M studio_assets/op_help/xsk_meijering.html
 M studio_assets/op_help/xsk_meijering.ko.html
 M studio_assets/op_help/xsk_meijering.tw.html
 M studio_assets/op_help/xsk_meijering.zh.html
 M studio_assets/op_help/xsk_sato.de.html
 M studio_assets/op_help/xsk_sato.en.html
 M studio_assets/op_help/xsk_sato.html
 M studio_assets/op_help/xsk_sato.ko.html
 M studio_assets/op_help/xsk_sato.tw.html
 M studio_assets/op_help/xsk_sato.zh.html
 M studio_assets/op_help/xsk_struct_coherence.de.html
 M studio_assets/op_help/xsk_struct_coherence.en.html
 M studio_assets/op_help/xsk_struct_coherence.html
 M studio_assets/op_help/xsk_struct_coherence.ko.html
 M studio_assets/op_help/xsk_struct_coherence.tw.html
 M studio_assets/op_help/xsk_struct_coherence.zh.html
 M studio_assets/op_help/xsp_hilbert_env.de.html
 M studio_assets/op_help/xsp_hilbert_env.en.html
 M studio_assets/op_help/xsp_hilbert_env.html
 M studio_assets/op_help/xsp_hilbert_env.ko.html
 M studio_assets/op_help/xsp_hilbert_env.tw.html
 M studio_assets/op_help/xsp_hilbert_env.zh.html
 M tests/test_docs_index_reachable.py
 M tests/test_sample_data.py
 M tools/opdocs.py
?? docs/ops/2d/texture/local_std.md
?? docs/ops/_fig/local_std.a.jpg
?? docs/ops/_fig/local_std.b.jpg
?? docs/ops/_fig/local_std.inputs.jpg
?? docs/ops/_fig/local_std.png
?? studio_assets/op_help/fig/local_std.png
?? studio_assets/op_help/local_std.de.html
?? studio_assets/op_help/local_std.en.html
?? studio_assets/op_help/local_std.html
?? studio_assets/op_help/local_std.ko.html
?? studio_assets/op_help/local_std.tw.html
?? studio_assets/op_help/local_std.zh.html
```

## 直近 2 時間に変更されたファイル

```
22:39 docs/README.md
22:38 examples/README.md
22:38 docs/maturity.json
22:38 docs/MATURITY.md
22:38 docs/HARDENING.md
22:38 docs/HARDENING.en.md
22:38 docs/CAPABILITIES.md
22:38 docs/CAPABILITIES.en.md
22:38 fullseye/OP_CATALOG.md
22:38 docs/OP_CATALOG.md
22:38 studio_assets/op_help/fig/zoom_region.png
22:38 studio_assets/op_help/fig/zoom_image_size.png
22:38 studio_assets/op_help/fig/zoom_image_factor.png
22:38 studio_assets/op_help/fig/zero_crossing_sub_pix.png
22:38 studio_assets/op_help/fig/zero_crossing.png
```

---

> このファイルは毎ターン自動上書きされます。**手動で書いた内容は失われます。**
> 永続化したいメモは `docs/PROGRESS.md`、`docs/next_plan.md`、または `docs/NOTES.md` を使ってください。
