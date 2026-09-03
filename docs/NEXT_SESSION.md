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
- **(a) 整数ユニオンの遅延化 = 完了**(`api._pu_contract`: uint8/uint16/bool を `scale_shift(1/s,0)` で遅延+同じ台帳記録+raise 拒否、int64 は materialize)。**clip 厳密化も完了**(`_Tile.cmax` で値域厳密/跨ぎ=コード空間 clip→raw float64(atol=0)→atol 再量子化の 3 段)。教訓 2 件: ①保守的な範囲過大評価が偽跨ぎ→不要な再量子化を招いた ②(2^b−1) 等分グリッドは k/4 を表せない・遅延アフィンは dense と ulp 差。テスト 60 件。
- **(c) タイル群 SoA ベクトル化 = 試して負け(null 結果、撤回)**: 同ビット幅タイルを連結して 1 回 unpack + gather/repeat で decode したが、ラベルボリューム(64,128,128) tile=16 で **8.3→15.6 ms(遅くなる)**、4bit 6クラスで 25 ms、tile=8 でも 13.2→12.7 の誤差範囲。4096 要素/タイルでは per-tile の numpy 呼び出しは既に償却済みで、追加した全配列パス(fancy gather ~5 ms/1M、repeat×2、astype)が Python 税を上回る。**実測コスト表(1 MB u8 ラベルボリューム, tile=16)**: encode 14 ms / to_dense 8.3 ms / threshold 3.1 / mean 2.3 / scale_shift **0.04**(dense アフィン 4.58 ms → 100x)/ np.copy 0.27。→ materialize は ~8 ms/MB(128 MB で ~1 s)= 許容だが速くはない。速くするなら Python ではなく **unpack カーネル自体**(np.unpackbits ベースの 1 パス化、または numba/C 拡張 optional)が対象で、regroup では効かない。
- **(b) lazy `threshold` = 完了(勝ち筋に絞った成果)**: `threshold_lazy` / `LAZY_OPS["threshold"]`。ラベルボリューム union 14.8x → threshold 後 **616.8x**、**1.74 ms vs dense op 6.63 ms(3.8x)**。「dense に勝てない」のは dense 出力の `threshold()`(decode+scatter を払う)で、**出力もユニオンなら勝つ** — ユニオン→ユニオンの閉じた演算が勝ち筋という結論。
- **フルスイート赤 4 件(全て自分起因)と手順ミス**: ①新 example の examples2d 未登録 ②③`tools/op_example_index._called` が docstring 散文 "boundary (printed)" を `boundary\s*\(` で op 呼び出しと誤検出→偽リンク+drift(言い換えで回避。**生成器の潜在バグ種**: 散文中の「<op名> (」が全 example で誤リンクしうる。修正案=コメント/docstring を剥いでからスキャン)④`test_videostream` の台帳 `before+1` 期待はリング上限 256 で満杯だと不成立(clear してから delta を見るよう修正)。**手順ミス**: background 通知の「exit code 0」はラッパーシェルの終了で、ログ末尾の `FULL_EXIT=1` を読む前に push してしまった(4 失敗込みが origin に載った→即修正 push)。**規律: push 前に必ずログの `FULL_EXIT=` 行を読む。通知の exit は pytest の exit ではない。**
- **ゴール「勝ち筋に沿って op を増やす」= 閉包性で拡充(完了)**: n-ary `union2/intersection/difference/symm_difference`(定数タイル代数、コード共有)+ `max_image/min_image`(片側 clip)、feature `area_frac/min_max_gray/intensity`(ヘッダ厳密)。実測: 集合演算 ~12x・結果 400–1300x、max_image 47x、min_max_gray 82x、area_frac 34x。設計則: **閉じる=ヘッダ(定数/値域)で決まる部分が大半で、decode は跨ぎ/両非定数だけ**。
- **次の候補(未着手)**: 残る閉じる候補は `abs_diff_image`/`add_image`/`sub_image`(片方定数→scale_shift+clip、両非定数は decode — 勝ちは集合演算より薄い)、`reduce_domain`(image×region: region 定数 0 タイル→定数化)、region の `select_shape`/CC 系は**閉じない**(materialize が正しい)。Studio/CLI `.npz` I/O は製品面の露出として別枠。(`gamma` は定数タイル O(1)・非定数は decode+再量子化=勝ちが薄い)。他: Studio/CLI の `.npz` ユニオン I/O(勝ちを製品面に出す)/unpack カーネル自体の高速化(optional numba)。 = `gamma` は非アフィンだが**定数タイルは O(1)**(map_pointwise の fast path 経由)、threshold 系 op は `threshold()` で bool 出力(c) `threshold`/`mean` のタイル群ベクトル化(同ビット幅タイルを SoA で一括)で Python ループ税を外す(d) Studio/CLI からの `.npz` ユニオン読み書き。

## 2026-09-04 追加: Qiita hero 画像の品質修正(ユーザー指摘)
- 原因 = 640px・res48・フラット法線。`smooth_normals` だけでは格子由来のバンディングが残る → **SDF 勾配法線**(`sdf_vertex_normals`)+ `render_beauty(vertex_normals=)` 注入口。1280px で再生成、`?v=2` でキャッシュバスト、`tools/qiita_patch_overview.py --lang ja --lang en` で PATCH。教訓: **marching cubes メッシュの法線は場から取る**(面法線の平均は格子を引き継ぐ)。他の SDF 由来 hero(itokawa は実測メッシュなので対象外)にも同じ手が効く。

## 2026-09-04 追加: 画像の総点検(ユーザー「他にも粗い物やお粗末な画像があれば改善」)
- 232 アセットの寸法表で候補抽出 → 実画像を見て判断。**手骨 hero(512px 手続きカプセル)→ 実解剖メッシュ 27 骨に差し替え**(`examples_3d/anatomical_hand.py`、myo_sim Apache-2.0、MuJoCo FK と 6e-11 m 一致、指長順 OK)。イトカワ hero は 640→1280(`FULLSEYE_HERO_SIZE=1280`)。gear_hero(512)は記事未参照(バナーのみ)で後回し。
- 小さいが「実態」の画像(後回し、改善=パイプライン再実行の重作業): evis 筋活性 480×360(動画フレーム)、bin-pick 680×480(MuJoCo フレーム)、evis stereo 960×268(SGM 出力のブロック状=アルゴリズム出力そのもの)、dragon anaglyph 640、turntable GIF 480(容量)。
- 方針: **「正確」は実データの幾何で担保、レンダは SDF 勾配/頂点法線+1280px+SSAA。** 手続き形状の hero は差し替え候補(evis 700 筋モデルの骨格も同じ手で実骨格化できる)。

## 次にやること(優先順)
1. ~~v0.1.5 タグ(PyPI 公開)~~ **完了(2026-09-03)**: PyPI に 0.1.5 公開済(wheel+sdist、latest=0.1.5)。公開前に liveness テスト 1 件(tb_running_gaussian_foreground が video 生成器で定数)を修正 = bridge に per-op tunable override を足し (k, var_init) を振る(公開 op 既定は不変)。※v0.1.4 は 3 日前に PyPI 400 で失敗しており PyPI 上は 0.1.3→0.1.5(同 license 形式で今回は成功 = 一過性)。
2. ~~`FULLSEYE_FAST` 既定 ON の判断~~ **完了: OFF 維持**(上記)。
3. 高速化の次の梃子: **`scale.scale_class` の誤分類修正は完了(2026-09-03)** — カテゴリ推測が 141 個の非局所 op を tile_safe と偽っていたのを実測ベースの `_NOT_TILE_SAFE`(class `global_reduce`/`global`/`compute_bound`)に置換、ライブ計測テストで完全性・非陳腐化をロック。**残**: `ops._norm` の一元化 + `Op.global_reduction` フラグ(sobel_mag/canny の残り 2〜3× 高速化と、`global_reduce` op を「生フィルタをタイル→一度だけ正規化」で実際にタイル可能にする `process_tiled_norm` 配線 (c))、GPU 常駐リング(accel `Resident`)を `VideoPipeline(device="cuda")` に (g)、フレーム並列 executor (f)、bench に `--set vol`。
4. 動画の残: `optical_flow_magnitude_stream` は per-frame が重い(既定 video セット外)→ 高速化 or cv2 twin 検討。scene_cut のフリッカ耐性は deflicker を前段に置く導線を例示済み。
5. 解像度管理の残: 増分中央値(大きい窓)、`mesh_isotropic_remesh` をイトカワの表示用 LOD にだけ使う導線(解析データとは分離)。
6. 前回からの残: 光学候補(多重反射/異方性 BRDF/ゴースト/テレセン誤差予算/センサ RS・PRNU・HDR/多色 PSF)、`fullseye.selfcheck()`、typed `_EMPTY_OF`、0.0 番兵 4 件、ファザー拒否 35 件、TYPEMISS 既知 3 件(pose_error / sphere_sdf / box_sdf)、raptor upstream 同期。
