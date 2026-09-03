# 次セッション引き継ぎ — 高速化・省メモリ・動画 + 解像度管理 + 図注(2026-09-03 午前〜)

## 正本
- 今回の記録: raptor memory `project_fullseye_perf_video_meshres_2026_09_03`(前回 = `project_fullseye_optics_wave2_2026_09_03`)
- 調査報告(実測、着手順の根拠): `docs/design/PERF_MEMORY_VIDEO_SURVEY.md`(§6 = ベンチ台の使い方)
- 高速 twin の設計と載せなかったもの: `docs/design/FAST_TWINS.md`
- ガイド: `docs/ops/videostream/guides/video_streaming.md` / `docs/ops/annotate/guides/figure_annotation.md`
- 例(すべて PASS 終端): `examples/video_streaming.py` / `examples/paper_figure.py` / `examples_3d/mesh_resolution_demo.py` / `examples_3d/annotate3d_figure.py` / `examples_3d/itokawa_regolith_hero.py`
- 規律: raptor memory `feedback_no_casual_decimation_academic`(学術用途では間引きを安易に行わない。減らす op は監査を返し、保護領域を壊すなら拒否)

## この回でやったこと
1. **解像度管理 `meshres.py`(ops3d `resolution` 15 op)**: 粗密を測る(`mesh_edge_stats` p95/p5、`mesh_detail_map`)、揃える(`mesh_split_long_edges` 頂点不変、`mesh_isotropic_remesh` 5.4→1.7)、監査つきで減らす(`mesh_lod_chain`/`mesh_select_lod`/`mesh_decimate_preserving` 細部固定+`max_error` 超は拒否/`mesh_reduction_report`)、点群(`pc_density`/`pc_poisson_disk` 孤立点を落とさない/`pc_fill_sparse`/`pc_density_equalize`/`pc_lod_chain`/`pc_thinning_report`)。`meshrepair.decimate_qem(protect=)`。テスト 29 件、ファザー 15/15 到達。
2. **イトカワ hero 再描画(Agent)**: 幾何は減らさず、適応テッセレーション(辺長 1.5 m 目標、p95/p5 2.72→2.38、面積・体積誤差 0)、帯域制限つき起伏(`mesh_displace_spectrum` + Nyquist ゲート `displacement_band_weights`、短波長は `bump_normals_fbm` へ)、角ばった岩塊 2,909 個(D^−3.1、埋没 0.3〜0.6)、露出を lit 中央値 0.45 に。起伏コントラスト 0.034→0.081(AMICA 円盤尺度 0.090、AMICA 実測 0.037 は位相角 8.8° なので厳密比較不可)。`render_mesh` をベクトル化(bit-exact)、影/AO のグリッド自動。新 op 5 つ(terrain)。記事本文は未変更、静止画 `docs/articles/assets/itokawa_regolith_hero.png` は差し替え済(**Qiita PATCH は未実施**)。
3. **図注(Agent)**: annotate `paper` 21 op + ops3d `annotate3d` 7 op、テスト 36 件、例 2 本、族ガイド。
4. **調査 → 着手(ユーザー指示「調査した上で着手」)**: `PERF_MEMORY_VIDEO_SURVEY.md`(65 op × 3 サイズ × 2 dtype + GPU)。推奨 3 件を全部実装:
   - (h) ベンチ台 `tools/bench_ops.py` + `bench/bench_ops_baseline.json`(384 行)+ テスト 31 件。初回で `cv_dist` の float32 契約違反を発見→修正。
   - (a′) `fast.py` cv2 twin 41 op(parity ゲート 41/41、**既定 OFF** `FULLSEYE_FAST=1`)、`fast.apply_uint8` 21 op、uint8 fail-closed(`on_error="raise"` は拒否、既定は `/255` 変換+台帳 `source="input"`)、`_coerce_input` O(N) 化、ACCEL 逆引きキャッシュ。float64 の結果は 1 ビット不変(SHA-256 で固定)。
   - (d) `videostream.py` / `opsvideostream`(8 op): `FrameRing` / `StatefulOp` 7 種 / `VideoPipeline`、`iter_frames(dtype="uint8")`。テスト 21 件、ファザー 8/8 到達、一括 op = ストリーム版がフレーム単位で一致。
5. `CHANGELOG.md` 0.1.5 に「2026-09-03 追加」節、README/CHANGELOG の op 数を 870 / 344 / 409 に更新、docs/OP_CATALOG/Studio help 再生成。

## 次にやること(優先順)
1. ~~フルスイート → commit → push → Qiita PATCH~~ **完了(2026-09-03 09:37)**: 10,800 passed / 163 skipped / 3 xfailed / 0 failed(17.5 分、`out/full_suite_2026_09_03c.log`)、push `e6d1ce02f..bb89e5e9a`、ja/en PATCH 200(イトカワ新静止画の説明を差し替え・`?v=2` でキャッシュ回避、op 数 870/344、テスト 10800)。
2. **v0.1.5 タグ**(= PyPI 公開)は **ユーザー判断待ち**。CHANGELOG は書けている。
3. `FULLSEYE_FAST` 既定 ON の判断: `tools/bench_ops.py --set core --sizes 2048,1080p --baseline bench/bench_ops_baseline.json` を FAST=0/1 で取り、退行ゼロなら既定 ON。
4. 高速化の次の梃子: `ops._norm` の一元化 + `Op.global_reduction` フラグ(sobel_mag/canny の残り 2〜3×、`scale.scale_class` の誤分類修正 → タイル配線 (c))、GPU 常駐リング(accel `Resident`)を `VideoPipeline(device="cuda")` に (g)、フレーム並列 executor (f)、bench に `--set vol` / `--set video`。
5. 解像度管理の残: 増分中央値(大きい窓)、`mesh_isotropic_remesh` をイトカワの表示用 LOD にだけ使う導線(解析データとは分離)。
6. 前回からの残: 光学候補(多重反射/異方性 BRDF/ゴースト/テレセン誤差予算/センサ RS・PRNU・HDR/多色 PSF)、`fullseye.selfcheck()`、typed `_EMPTY_OF`、0.0 番兵 4 件、ファザー拒否 35 件、TYPEMISS 既知 3 件(pose_error / sphere_sdf / box_sdf)、raptor upstream 同期。
