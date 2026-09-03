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
2. **イトカワ hero 再描画(Agent)**: 幾何は減らさず、適応テッセレーション(辺長 1.5 m 目標、p95/p5 2.72→2.38、面積・体積誤差 0)、帯域制限つき起伏(`mesh_displace_spectrum` + Nyquist ゲート `displacement_band_weights`、短波長は `bump_normals_fbm` へ)、角ばった岩塊 2,909 個(D^−3.1、埋没 0.3〜0.6)、露出を lit 中央値 0.45 に。起伏コントラスト 0.034→0.081(AMICA 円盤尺度 0.090、AMICA 実測 0.037 は位相角 8.8° なので厳密比較不可)。`render_mesh` をベクトル化(bit-exact)、影/AO のグリッド自動。新 op 5 つ(terrain)。静止画 `docs/articles/assets/itokawa_regolith_hero.png` を差し替え、記事 ja/en の説明文も新描画に合わせて更新し PATCH 済(下記 1)。**回転 GIF も同パイプラインで作り直し**(`tools/gen_itokawa_turntable.py`: 間引きなし・カメラと太陽が一周・位相角 45° 固定・全フレーム同一露出、36 枚 480 px、2.56 MB、`media/itokawa.mp4` 同梱)。旧 `gen_showcase_gifs.py` の低ポリ版は `*_lowpoly` 名に退避。
3. **図注(Agent)**: annotate `paper` 21 op + ops3d `annotate3d` 7 op、テスト 36 件、例 2 本、族ガイド。
4. **調査 → 着手(ユーザー指示「調査した上で着手」)**: `PERF_MEMORY_VIDEO_SURVEY.md`(65 op × 3 サイズ × 2 dtype + GPU)。推奨 3 件を全部実装:
   - (h) ベンチ台 `tools/bench_ops.py` + `bench/bench_ops_baseline.json`(384 行)+ テスト 31 件。初回で `cv_dist` の float32 契約違反を発見→修正。
   - (a′) `fast.py` cv2 twin 41 op(parity ゲート 41/41、**既定 OFF** `FULLSEYE_FAST=1`)、`fast.apply_uint8` 21 op、uint8 fail-closed(`on_error="raise"` は拒否、既定は `/255` 変換+台帳 `source="input"`)、`_coerce_input` O(N) 化、ACCEL 逆引きキャッシュ。float64 の結果は 1 ビット不変(SHA-256 で固定)。
   - (d) `videostream.py` / `opsvideostream`(8 op): `FrameRing` / `StatefulOp` 7 種 / `VideoPipeline`、`iter_frames(dtype="uint8")`。テスト 21 件、ファザー 8/8 到達、一括 op = ストリーム版がフレーム単位で一致。
5. `CHANGELOG.md` 0.1.5 に「2026-09-03 追加」節、README/CHANGELOG の op 数を 870 / 344 / 409 に更新、docs/OP_CATALOG/Studio help 再生成。

## 2026-09-03(午後)追加: 動画像処理 第 2 波 + FAST 既定判断 + bench --set video
- **動画 op 第 2 波(videostream 8→16 op)**: `MotionHistoryImage`/`MotionEnergyImage`(Bobick–Davis)、`ThreeFrameDifference`(Collins・ゴースト除去)、`RunningGaussianForeground`/`RunningGaussianBackground`(Wren *Pfinder*・画素ごと k-σ)、`TemporalBilateral`(時間バイラテラル)、`Deflicker`、`SceneCutDetection`(χ² ヒストグラム)。カテゴリ motion/background/denoise/restore/analysis を追加。テスト +10(計 31)、fuzz cover-all 8/8 到達(uncovered 0/807)、例 `examples/video_streaming.py` に第 2 波 GT ブロック、ガイド更新、per-op 注記 8 本 + OP_CATALOG/Studio help 再生成(drift テスト green)。
- **`FULLSEYE_FAST` 既定は OFF 維持(計測で判断・完了)**: `--set core --sizes 1080p` を FAST=0/1 比較 → テーブル 10 op が 1.3〜10×(gerode 10×、gaussian 5.3〜5.8×)、dtype 変化ゼロ、テーブル外は経路同一で不変。cv2 twin の内部差 5e-3 が再現性(SHA-256 ピン)を暗黙に破るため既定 ON にしない。速度が要る場面で `FULLSEYE_FAST=1` opt-in。
- **bench `--set video`**: per-frame ストリーミング計測(ring メモリのみ、ms/frame・fps)。720p float64 で deflicker 152 fps・exp_bg 124 fps・frame_diff 101 fps 〜 per-画素中央値/窓(temporal_median 14.7・background_subtraction 13.2・temporal_bilateral 10.2 fps)。`tools/bench_ops.py --set video --sizes 720p`。

## 2026-09-03(さらに後半)追加: 検証キャンペーン + exact geometry predicates
- **検証キャンペーン A(契約監査)**: 公開 op(`ops.REGISTRY`)は test_op_contracts の4大契約で既に完全網羅と確認。唯一の穴 = tb_ ブリッジ 139 op の有限性/決定性契約(conftest に新 sort バンク無く「ゼロ反復で自明パス」= 未実行だった)を test_backends_typed_liveness にロック追加。実バグ 0、honest-inf 2 件(tb_mat_cond 特異=inf / tb_geodesic_distances 不達=inf)を allowlist。= 契約レベルでは fullseye は既に堅牢という発見。
- **exact geometry predicates(`predicates.py`)実装**: orient2d/orient3d/incircle/insphere を Shewchuk 流 2 段適応(float→Fraction 厳密)。naive は 19% 誤符号→adaptive は完全一致。凸包 robust 化、`fullseye.*` 露出、py-modules 登録。詳細 = memory [[project_fullseye_representation_future_backlog]]。次候補: Delaunay/point-in-polytope/mesh 向き検査へ横展開。
- **教訓**: `pytest | grep | tail` はパイプで exit code をマスクし drift/packaging 失敗を見逃す → 以後 `> log; echo $?` で実 exit を捕捉。

## 2026-09-04 追加: 精度ユニオン型 PoC(ユーザー発案)+ geompred(predicates 横展開)
- **精度ユニオン型 PoC = 一本化して公開(`precision_union.py`、`fullseye.PrecisionUnion`)**: ユーザー発案「ビット深さのユニオンに量子化要素を乗せ一元処理」。タイルごとに最小ビット幅 {0,1,2,4,8,16}(アフィン vs unit-scale 整数の2候補 min、実 sub-byte パック)。正直な実測: メモリはラベル/深度/3Dボリュームで 4〜17x 勝ち、自然画像 uint8 は 0.98x で微損(隠さず報告)。**遅延アフィン `scale_shift(a,b)` を追加**(私の PoC 由来): `offset'=a·off+b, scale'=a·scale` でコード不変・O(タイル数)、連鎖を1 decode に畳む(遅延代数のみ ~100x)。`threshold` は dense ベクトル化に Python ループでは勝てない旨を honest に明記。※並列 fork がコンテキスト継承で PoC を重複実装したため公開版に一本化(重複 `poc/bitunion.py` は削除)。
- **geompred(`geompred.py`)= exact predicates の横展開(本来の次候補)**: point_in_polygon / point_in_convex_polygon / is_convex_polygon / point_in_tetrahedron / point_in_convex_polytope(内外3値)/ is_delaunay_2d(incircle で外接円空を検査・違反返す)/ mesh_orientation_consistent。`fullseye.*` 露出 + py-modules 登録。near-edge スイープで **naive float winding が robust と 8.64% 食い違う**(価値の実証)。テスト 18 件。
- **教訓(fork の使い方)**: `subagent_type:"fork"` はコンテキスト+役割を継承するため、別タスクを頼んでも親の最優先タスク(PoC)を再実行し自分を orchestrator と誤認しうる。独立タスクの委任は fresh general-purpose の方が混乱しない。
- **昇格(ユーザー指示「昇格を目指しましょう」→「進めて下さい」)完了 3 段**: ①N-D 化(共有 `_blocks()`、ラベルボリューム 15.9x 無損失/深度 f32 3.9x)②`save`/`load`(.npz、on-disk 378x)③**op パイプライン統合** — `apply`/`run_pipeline` が `PrecisionUnion` を受け、`LAZY_OPS`(identity/invert/scale_clip)は materialize せず遅延、初の非遅延 op で 1 回 materialize。新 `clip(lo,hi)`(窓内不変/窓外定数化/跨ぎだけ再量子化)。**精度契約**=ユニオンが `from_array` の atol を保持し gain で伝播、clip はその atol で再量子化(無損失ユニオンの clip は無損失)。開発中に「ステップ/2」契約の誤りをテストで摘発→修正。parity テストで LAZY_OPS の写像を ops.py に固定。テスト 51 件。
- **次の昇格候補(未着手)**: (a) 整数ユニオンの遅延化 = `/255` 契約変換を `scale_shift(1/255,0)` で遅延しつつ台帳記録も行う(`_contract_dtype` と同じ record を呼ぶ)(b) LAZY_OPS の拡充 = `gamma` は非アフィンだが**定数タイルは O(1)**(map_pointwise の fast path 経由)、threshold 系 op は `threshold()` で bool 出力(c) `threshold`/`mean` のタイル群ベクトル化(同ビット幅タイルを SoA で一括)で Python ループ税を外す(d) Studio/CLI からの `.npz` ユニオン読み書き。

## 次にやること(優先順)
1. ~~v0.1.5 タグ(PyPI 公開)~~ **完了(2026-09-03)**: PyPI に 0.1.5 公開済(wheel+sdist、latest=0.1.5)。公開前に liveness テスト 1 件(tb_running_gaussian_foreground が video 生成器で定数)を修正 = bridge に per-op tunable override を足し (k, var_init) を振る(公開 op 既定は不変)。※v0.1.4 は 3 日前に PyPI 400 で失敗しており PyPI 上は 0.1.3→0.1.5(同 license 形式で今回は成功 = 一過性)。
2. ~~`FULLSEYE_FAST` 既定 ON の判断~~ **完了: OFF 維持**(上記)。
3. 高速化の次の梃子: **`scale.scale_class` の誤分類修正は完了(2026-09-03)** — カテゴリ推測が 141 個の非局所 op を tile_safe と偽っていたのを実測ベースの `_NOT_TILE_SAFE`(class `global_reduce`/`global`/`compute_bound`)に置換、ライブ計測テストで完全性・非陳腐化をロック。**残**: `ops._norm` の一元化 + `Op.global_reduction` フラグ(sobel_mag/canny の残り 2〜3× 高速化と、`global_reduce` op を「生フィルタをタイル→一度だけ正規化」で実際にタイル可能にする `process_tiled_norm` 配線 (c))、GPU 常駐リング(accel `Resident`)を `VideoPipeline(device="cuda")` に (g)、フレーム並列 executor (f)、bench に `--set vol`。
4. 動画の残: `optical_flow_magnitude_stream` は per-frame が重い(既定 video セット外)→ 高速化 or cv2 twin 検討。scene_cut のフリッカ耐性は deflicker を前段に置く導線を例示済み。
5. 解像度管理の残: 増分中央値(大きい窓)、`mesh_isotropic_remesh` をイトカワの表示用 LOD にだけ使う導線(解析データとは分離)。
6. 前回からの残: 光学候補(多重反射/異方性 BRDF/ゴースト/テレセン誤差予算/センサ RS・PRNU・HDR/多色 PSF)、`fullseye.selfcheck()`、typed `_EMPTY_OF`、0.0 番兵 4 件、ファザー拒否 35 件、TYPEMISS 既知 3 件(pose_error / sphere_sdf / box_sdf)、raptor upstream 同期。
