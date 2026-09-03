# Changelog — fullseye

All notable changes to the PyPI package `fullseye`. Dates are release dates (JST).
Versions follow the git tags; a tag push publishes to PyPI (`.github/workflows/release.yml`).

## 0.1.6 — unreleased

- **実解剖骨メッシュから手骨格を組み立てる例 `examples_3d/anatomical_hand.py`(ユーザー指摘「手骨も
  今となっては粗い」)**: 記事の手骨 hero は手続きカプセル SDF で実物と並べると粗かった。「正確な骨格」
  は画像生成 AI のもっともらしさでなく**実データの幾何**で担保する方針で、MyoSuite `myo_sim`
  (Apache-2.0、同梱せず `MYO_SIM_DIR`)の OpenSim 由来骨メッシュ 27 個(手根骨 8・中手骨 5・指骨 14、
  実寸 m)を MJCF(include 構成、`<worldbody>` 複数)から **stdlib だけ**で辿って配置(body 木の
  pos/euler 累積、MuJoCo 既定 eulerseq xyz)。`mujoco` があれば forward kinematics と突き合わせ
  (重心 6e-11 m・最近傍頂点 2e-9 m で一致)、無ければスキップを明示。解剖サニティ=指長 中指 123 >
  示指 117.5 > 薬指 112 > 小指 99.5 mm。手背を手首側から見下ろす構図(掌側の豆状骨で背側を判定、
  中指末節骨で指方向を判定)、`render_beauty` 1280px。データ未取得は SKIP(exit 0)。テスト 4 件
  (27 骨・FK 一致・指長順・euler/quat 規約)。記事 ja/en の手骨 hero を差し替え(手続き版は
  ターンテーブル節に残置)。
- **hero レンダの品質修正(Qiita 記事の 1 枚目)+ `render_beauty(vertex_normals=)`**: 記事の
  SDF 彫刻 hero は 640px・marching cubes res=48・**フラット法線**で、ファセット模様と四角い
  スペキュラが見えていた(ユーザー指摘)。`smooth_normals=True` にしても、面から作る頂点法線は
  ボクセル格子の階段を引き継いで**等高線状のバンディング**が残る(1280px で拡大確認)。等値面の
  法線は定義から ∇f/|∇f| なので、`examples_3d/render_beauty.py` に `sdf_vertex_normals`(SDF 勾配
  `np.gradient` を頂点で三線形サンプル)を追加し、`render_beauty` / `render_regolith` に
  `vertex_normals=(n_mesh,3)` の注入口を追加(メッシュ行のみ上書き、地面は既定、単位正規化、
  形状/非有限は ValueError)。hero は res=128・1280px・ss=2・AO 64・shadow_res 1024 で再生成
  (AO/影が支配的で所要時間は 640px と同じ ~80 s)。記事の画像 URL は `?v=2` で imgix キャッシュを
  バスト。テスト 3 件(既定法線の明示渡しは float 丸めまで一致/解析法線は陰影だけ変えシルエット不変/
  不正入力拒否)。
- **精度ユニオン型ストレージ(`precision_union.py`、公開: `fullseye.PrecisionUnion`)** —
  配列をタイルに切り、**各タイルを局所エントロピーに応じた最小ビット深さ**(`{0,1,2,4,8,16}`
  bit/要素の union。定数=0bit、2値=1bit、平滑=4bit、繁雑=8/16bit)で保持する。
  タイルごとにアフィン(`値=offset+code*scale`)と unit-scale 整数の 2 候補を計算し
  少ビットな方を採用、sub-byte はビットパックするので 2bit タイルは実際に 1/4 バイト
  で収まる。整数(および整数値 float)は**無損失**、float は指定 `atol` 内。呼び出し側は
  タイルのビット深さで分岐せず `to_dense/threshold/mean/map_pointwise` を一元的に使える
  (定数タイルは復号せず offset だけで処理する fast path つき)。numpy+stdlib のみ。
  実測(512×512): セグメンテーションラベル **17.0x**、64 枚ラベルボリューム 17.0x、
  深度 float32(atol=0.02)**4.0x**、平滑勾配 1.3x。自然画像 uint8 は 0.98x で
  **わずかに損**(高局所エントロピーで 8bit を割れず、per-tile メタデータが overhead)—
  勝ち筋はラベル/領域マップ・平滑深度・CAD/合成・3D ボリューム(fullseye のマシンビジョン
  データ)であることを honest に記録。既知技術(ブロック適応量子化+ビットパック)の
  組合せで、新規性は「異種精度ストア上の型付き一元処理層」にある。速度化は Python
  タイルループの overhead が定数タイル近道を食っており、ベクトル化が前提(現状は
  メモリ削減が主効果)。**遅延アフィン `scale_shift(a,b)`** を追加: `値=offset+code*scale`
  の代数から `offset'=a*offset+b, scale'=a*scale` でパックコードを一切触らず O(タイル数)
  で `a*x+b` を返す(コードバッファは元と共有=コピーなし)。明るさ/コントラスト/正規化の
  連鎖はメタデータ1パス+最後に1回だけ decode に畳める。遅延代数のみなら dense の `a*x+b`
  連鎖比 ~100x、materialize 込みでも数 op 連鎖で明確に速い(実測)。`threshold` は逆に
  dense(完全ベクトル化・帯域律速)に Python ループでは勝てない旨を docstring に honest に明記。
  **昇格(PoC→機能): N-D 対応 + ディスク永続化**。タイリングを任意次元に一般化(共有
  `_blocks()` ジェネレータ、per-axis タイルサイズ可)し、**3D ボリューム・スタック・動画**を
  扱えるように(最大の勝ち筋)。実測: ラベルボリューム `(64,128,128)` uint8 で **15.9x**
  (無損失)、深度ボリューム float32(atol=0.02)**3.9x**、自然画像 uint8 は 0.98x で不変
  (honest)。`save`/`load`(`.npz`、`allow_pickle=False`、ヘッダを並列配列化+パック本体を
  連結)でメモリ勝ちがそのままファイル勝ちに(構造的ラベルボリュームで **on-disk 378x**、
  npz の gzip も乗る)。1D/2D の既存 API・挙動は不変。例 `examples/precision_union_volume.py`
  (PASS 終端、2 regime + 遅延アフィン + honest な非勝ちを実演)。
  **op パイプライン統合(遅延実行)**: `fullseye.apply` / `run_pipeline` が `PrecisionUnion`
  を入力に受ける。`precision_union.LAZY_OPS`(`identity`/`invert`/`scale_clip`)にある op は
  **materialize せずヘッダ代数+タイル単位 clip で実行しユニオンのまま返す**(O(タイル数))。
  表に無い最初の op で 1 回だけ materialize して通常経路(coerce/契約変換/台帳)へ。整数・bool
  ユニオンは `/255` 契約変換と台帳記録が通常経路の責務なので遅延せず materialize(parity 固定)。
  GPU 経路(`device!="cpu"`)は dense を要するので materialize。新 `clip(lo,hi)`: ヘッダから
  各タイルの値域を O(1) で判定し、**窓内=不変(コード共有)/窓外=定数化/跨ぎだけ decode→
  再量子化**。**精度契約**: ユニオンは `from_array` で受け入れた `atol` を保持し、`scale_shift`
  は |gain| 倍で伝播、`clip` の跨ぎ再量子化はその atol で行う(無損失ユニオン=整数ラベルの
  clip は無損失、float は符号化 atol を超えない)。この契約は開発中に「タイル自身のステップ/2」
  という誤った契約(4bit で厳密だったタイルに 0.067 の誤差を許した)をテストで摘発して修正した
  もの。**drift 防止**: `LAZY_OPS` の (a,b)→gain/offset 写像は ops.py と二重管理なので、
  `apply(pu,op).to_dense() == apply(dense,op)` の parity テストで実 op に固定(乖離は CI 失敗)。
  **整数ユニオンも遅延**: uint8/uint16(文書化されたセンサ dtype)と bool のユニオンは `/255`
  等の契約変換を `scale_shift(1/s,0)`(純 gain、無損失のまま)で遅延実行し、dense 経路の
  `_contract_dtype` と**同じ台帳記録**(`dtype_converted`, source="input")と `on_error="raise"`
  の拒否を鏡写し(`api._pu_contract`)。int64 等はデータ依存の除数(`_dtype_scale`)なので
  materialize。→ 最大の勝ち筋(uint8 ラベルボリューム)が点 op 連鎖を通じて一度も materialize
  されない。**clip の厳密化**: `_Tile.cmax`(実際に存在する最大コード)でタイル値域を厳密に
  (従来の保守的過大評価が「範囲内タイルを偽の跨ぎ」にし 16bit 再量子化で 7.5e-6 の誤差を
  出していた — テストで摘発)。跨ぎタイルの処理は 3 段階: (a) 境界がコードグリッド上なら
  **コード空間で clip**(同ビット、値の decode 不要、厳密)(b) 無損失ユニオン(atol=0)なら
  **raw float64 タイル(bits=64)**で厳密保持(精度契約を守りメモリが払う。planner は選ばない)
  (c) それ以外は atol で再量子化。※(2^b−1) 等分グリッドの性質上 k/4 のような値は厳密表現
  不可(4 は 2^b−1 でない)— 遅延アフィンは実数では厳密だが float64 の結合順で dense と ulp
  差(~1e-16)が出る。parity は atol=1e-12(16bit 半ステップ 7.6e-6 とは 6 桁差)。テスト計 60 件。
  **lazy `threshold`(`threshold_lazy` / `LAZY_OPS["threshold"]`)**: `(v > a)` を 0/1 の float64
  ユニオンとして返す。定数タイルと**片側タイル(ヘッダ値域で判定)は O(1) で定数化**、跨ぎだけ
  decode→1bit。厳密(atol=0)、≤1 bit/要素、dense op と完全一致。ラベル/深度データで最頻の op を
  通じて**メモリ勝ちが伝播**する: ラベルボリューム (64,128,128) uint8 で union 14.8x → threshold
  後 **616.8x**(238 タイル定数 + 18 タイル 1bit)。速度も **1.74 ms vs dense op 6.63 ms(3.8x)**
  — dense は /255 変換+比較を 100 万ボクセルに払うが lazy は大半をヘッダで決める(これは
  Python ループで dense に勝てなかった dense-出力 `threshold()` とは別物: 出力もユニオンなので
  decode/scatter が無い)。テスト計 64 件。
  **ユニオンで閉じる op を拡充(勝ち筋=閉包性)**: `apply` の n-ary 枝と feature 枝が
  `PrecisionUnion` を受ける。**2 入力(`LAZY_NARY`、同形・同タイリングの 2 ユニオン)**:
  `union2`/`intersection`/`difference`/`symm_difference`(`mask_binop`: 0/1 化は dense と同じ
  `> 0.5`、定数タイル代数 `x|1=1, x|0=x(コード共有), x&0=0, x&1=x, 1&~x=NOT x(ヘッダ反転)`
  で大半を O(1) 決定、両方非定数のタイルだけ decode)、`max_image`/`min_image`(`extremum_with`:
  片方定数なら他方を定数で片側 clip=ヘッダ判定、両方非定数だけ decode、atol は max で伝播)。
  タイリング不一致は materialize。**feature(`LAZY_FEATURES`、ユニオン→スカラ)**: `area_frac`
  (定数 O(1)+1bit は popcount)、`min_max_gray`(=clip 後の max、**ヘッダのみ O(タイル数)**)、
  `intensity`(=clip 後の mean、`clipped_mean` で再量子化なしに厳密)。`threshold_lazy` は
  1bit タイルを**ヘッダ書換だけ**で処理(コード共有)。実測(ラベルボリューム (64,128,128)):
  集合演算 **lazy 0.6–0.7 ms vs dense 8.3 ms(~12x)、結果 400–1300x・≤1bit**、`max_image`
  **47x**、`min_max_gray` **82x**、`area_frac` **34x**。parity テストで全 op を dense に固定。
  テスト計 88 件(test_precision_union 75)。
- `fullseye.__version__` はパッケージメタデータ(= pyproject の version)を単一
  真実源として解決するようになった。従来はハードコードで、0.1.5 でも `"0.1.0"` を
  返していた。ソース/sdist では `api.py` 隣の `pyproject.toml`、インストール時は
  `importlib.metadata` から引く。
- **exact geometric predicates(`predicates.py`、公開: `fullseye.orient2d/orient3d/incircle/insphere`)** — 向き・内接円・内接球の判定を返す。float64 の行列式は near-collinear/coplanar/cocircular で**符号を誤る**(線上補間点のスイープで naive は約 19% 誤符号)。Shewchuk 流の 2 段適応(float 高速フィルタ→`fractions.Fraction` の厳密フォールバック。float64→Fraction は lossless)で**常に正しい符号**を返す。stdlib+numpy のみ(bignum/C 拡張なし)。凸包(`_convex_hull_xy`)の turn 判定をこれに載せ替えて堅牢化。
- **robust geometry queries(`geompred.py`、公開: `fullseye.point_in_polygon/point_in_convex_polygon/is_convex_polygon/point_in_tetrahedron/point_in_convex_polytope/is_delaunay_2d/mesh_orientation_consistent`)** — 上の exact predicates を、naive float で符号が反転する**組合せ判定**に使う消費層。内外判定は 3 値(`+1` 厳密内 / `0` 境界上 / `-1` 厳密外)で境界を明示。`point_in_polygon` は winding のエッジ交差を `orient2d` の厳密符号で決めるので、辺・頂点に厳密に乗る点を境界として正しく返す(整数座標の実測: 全エッジ点を境界検出)。near-edge スイープでは**naive float winding が robust と 8.64% 食い違う**(=naive が誤る)。`is_delaunay_2d` は各三角形の外接円が空かを `incircle` で検査し違反 `(三角形, 点)` を返す(cocircular は非厳密なので誤検出しない)。`mesh_orientation_consistent` は隣接面が共有エッジを逆向きに辿るか(非多様体/向き反転)を報告。stdlib+numpy のみ。
- `scale.scale_class` のタイル可否がカテゴリ推測から**実測**に。カテゴリだけの
  分類は 141 個の非局所 op(region の skeleton/distance/形状、gray のヒストグラム、
  edges の勾配強度/コーナー/DoG、多スケール texture、TV/拡散/変換系 smoother)を
  `tile_safe=True` と偽っていた。これらを `_NOT_TILE_SAFE` に列挙し、正規化で
  スケールだけずれるものは新クラス `global_reduce`、残りは `global`/`compute_bound`
  として理由つきで返す。3 プローブ×2 パラメータのライブ計測テストが、tile_safe と
  分類した op が実際にタイルで壊れないこと(完全性)と一覧が陳腐化していないこと
  (非陳腐化)をロックする。`process_tiled` の消費者は実行時に居らず助言専用なので
  実行時挙動は不変。
- 進化ブリッジ(`backends_typed`)に per-op tunable override を追加し、
  `running_gaussian_foreground` は検出感度を支配する `var_init` を振れるように
  なった(既定ヒューリスティックは効きの薄い `alpha` を選んでいた)。公開 op の
  既定値は不変。

## 0.1.5 — 2026-09-03 (main since 2026-08-31)

**Summary (en)**: the largest release so far — 63 feature/fix commits, 2,600 files, +219k lines.
Registry now measures **870 distinct 2-D ops + 344 3-D ops + 417 ledger ops** (math 26, optics 47,
light field 17, photon counting 17, specular 13, motion magnification 9, quaternion 19, FMCW 8,
acoustics 19, interferometry 9, tomography 17, volume colour 11, representation 42, CAD 4,
annotate 46, gfx2d 32, image metrics 24, colour transport 11, forensics 16, astro stacking 14,
video streaming 16).
Full suite: **10,854 passed / 171 skipped / 3 xfailed / 0 failed**. Four things a user notices:
(1) `apply()` now warns once per op when it silently fell back, and `fullseye.fallbacks()` shows
the ledger; (2) 32 measured behaviour changes from the adversarial review (listed below, several
are corrections of wrong answers); (3) a lens-design / illumination-design / image-formation layer
(`raytrace`, `lensopt`, `illumdesign`, `lensimage`, 47 ops); (4) 39 new worked examples, every op
has one, and the op docs (`docs/ops/**`) are generated from the registry with drift CI.

### 新しい op 族(すべて numpy(+scipy)で動作、重い依存は optional)

- **光学設計・照明・結像(47 op、`opsoptics`)** — `optics`(近軸/波動/偏光 18)、`raytrace`(実光線追跡・OPD→Zernike・Seidel・公差 MC、**実硝材 Sellmeier 20 種**(refractiveindex.info ミラーで定数照合)、**非球面 `asph=(A4,A6,…)`**、`chromatic_shift`、実絞りへの主光線エイミング `chief_ray`)、`lensopt`(**減衰最小二乗の最適化** `optimize_lens` / `merit_function` / `bend_singlet` — Coddington・Descartes・A4=kc³/8 の閉形式で検証)、`illumdesign`(**照明設計** `light_source` / `irradiance_map` / `illumination_uniformity` / `defect_contrast` / `lighting_sweep` / `illumination_design` — cos⁴ 則、鏡面での最良仰角 = 90°−2×斜面、候補族の順位表)、`lensimage`(**設計レンズで撮る** `psf_from_opd` / `distortion_map` / `render_through_lens` / `defect_dataset` / **校正閉ループ** `calibration_views`)。
- **ビジョン設計・仮想 MV 環境** — `visiondesign`(要求分解能から焦点距離・F 値・被写界深度・検出限界を紙の上で)、`visionlab`(設計→限界→仮想部品→撮像→検査の一気通貫)、`defectgen`(傷/孔食/割れ/しみの合成)。
- **センサ物理** — `lightfield`(17)、`photoncount`(17、時間分解・光子計数)、`specularity`(13、鏡面/拡散分離・GGX・偏光分離・ロバスト光度ステレオ)、`motionmag`(9)、`quatimage`(19、四元数画像)、`rangedoppler`(8、FMCW)、`acoustics`(19)、`interferometry`(9、コヒーレンス走査)、`tomography`(17)。
- **表現・描画・計測・来歴** — `reprconv`(42、表現変換)、`gfx2d`(32)+`drawlist`/`drawstyle`、`annotate`(25)、`palette`(役割で配色、赤緑の対を既定から外す)、`imgmetrics`(24、差を測る op — 外部基準で 5 op 検証)、`colortransport`(11)、`imgforensics`(16)、`astrostack`(14)、`cadmap`(4)、`volcolor`(11)、`mathops`/`opsmath`(26)、`ops1d`。
- **3D 体積** — `volregion` / `volgray` / `volxform` / `volprobe` / `volfreq` / `volrestore`(体積の領域・濃度・変形・探針・周波数・復元)、3D domain/boundary 6 op、`render_regolith` / `brdf_hapke` / `brdf_lommel_seeliger` / `shadow_raycast`(太陽 0.53° の本影・半影)/ `mesh_displace_fbm` / `mesh_scatter_boulders` / `terrain_region_mask`(イトカワの光と影を実画像 AMICA と 4 指標で照合)。
- **Studio** — `param_specs`(op パラメータの型適合ウィジェット 81+66)、右クリックの全ビュー、Feature Inspection 2D/3D、対話 3D ビューア、タブエディタ / watch / 実行制御。

### 2026-09-03 追加: 解像度管理・図注・動画ストリーム・高速化(実測で着手)

- **解像度管理(`meshres`、ops3d `resolution` 15 op)** — 「点群の粗い部分と密な部分の使い分け」を測って直す。`mesh_edge_stats`(辺長 p95/p5、UV 球 5.4・イトカワ実測 2.7)、`mesh_detail_map`(粗さ・実データの細部・合成起伏の重み)、粗い所だけ細分 `mesh_split_long_edges`(頂点不変)、等方リメッシュ `mesh_isotropic_remesh`(5.4→1.7、面積誤差 <1 %、閉多様体)、`mesh_sample_points`(Poisson 表面標本)。**学術用途では間引きを安易に行わない**規律を op に焼き込む: `mesh_lod_chain` / `mesh_select_lod` は各段の幾何誤差と画面誤差 px を返し、`mesh_decimate_preserving` は細部の頂点を厳密固定(誤差 1e-16)で `max_error` 超は**拒否**、`mesh_reduction_report` / `pc_thinning_report` は失ったものを数える(孤立点の除去数、`pc_poisson_disk` は 0)。`pc_density` / `pc_fill_sparse` / `pc_density_equalize` / `pc_lod_chain`。`meshrepair.decimate_qem(protect=)` 追加。
- **図注(annotate `paper` 21 op + ops3d `annotate3d` 7 op)** — 学術図の作法を op に: 肘つき引き出し線(衝突回避)、番号マーカー+凡例、寸法線、角度、1/2/5×10^k スケールバー、方位、インセット拡大、マスク輪郭、経路文字、カラーバー、パネル記号、複数パネル組版(`*_layout` 8 op は幾何だけを table で返す)。3-D は `pose`/`K` で射影した矢印・ラベル・スケールバー(短縮を正直に)・座標軸・箱・距離、`depth=` で隠れたアンカーは破線+白抜き。族ガイド `docs/ops/annotate/guides/figure_annotation.md`。
- **動画ストリーム(`videostream` / `opsvideostream` 16 op、2 波)** — `FrameRing`(直近 N 枚をフレームの dtype のまま: uint8 1080p×5 = 10 MB、float64 一括 1 秒は 475 MB)、状態つき op。第 1 波(8): `TemporalMedianWindow` / `MovingAverageWindow` / `BackgroundSubtractionWindow` / `FrameDifference` / `ExponentialBackground` / `RunningStats` / `OpticalFlowStream`。第 2 波(8): `MotionHistoryImage` / `MotionEnergyImage`(Bobick–Davis 動き履歴/エネルギー)、`ThreeFrameDifference`(Collins・二連続差分の AND でゴースト除去)、`RunningGaussianForeground` / `RunningGaussianBackground`(Wren *Pfinder*・画素ごと単一ガウス、k-σ 前景 — 固定閾値の `ExponentialBackground` の上位)、`TemporalBilateral`(時間バイラテラル・動きをゴーストにせず静止部を雑音除去)、`Deflicker`(輝度脈動を打ち消す)、`SceneCutDetection`(ヒストグラム χ² でショット境界)。`VideoPipeline`(台帳 op・状態つき op・callable を混ぜ、失敗時は状態リセット+台帳 `source="stream"`)。台帳の一括 op は同クラスの再生なので **ストリームと一括がフレーム単位で一致**。`iter_frames(dtype="uint8")` で整数素通し(1080p 読み込み 18→約 180 fps)。videops と同名にしない(因果窓は別名)。**per-frame スループット計測 `tools/bench_ops.py --set video`**(ring メモリのみ、fps 予算判定: 720p float64 で deflicker 152 fps・frame_diff 101 fps 〜 per-画素中央値/窓の temporal_median・background_subtraction・temporal_bilateral は 10〜15 fps)。
- **CPU 高速 twin(`fast`、41 op、既定 OFF)** — `FULLSEYE_FAST=1` または `apply(..., fast=True)` で cv2/IPP の twin を使う。accel と同型の parity ゲート(5 (a,b)×6 画像、内部 <5e-3、二値 op は不一致率 0)を **通ったものだけ**登録: gaussian 8.6×、median k=5 29×、gerode 14.6×、gopen 7.6×(2048²、熱定常でない同 run 相対)。clahe(0.135)/ bilateral(0.121)/ 回転・拡縮(スプライン次数)/ equalize / otsu(二値で 0.004)は**速いが違うので載せない**(`fast.NOT_LISTED`)。uint8 整数カーネル `fast.apply_uint8`(median k=5 185×、box 27×、gopen 50×; gaussian は 1.17/255 ずれるので除外)。
- **`FULLSEYE_FAST` 既定は OFF を維持(計測で判断)** — `tools/bench_ops.py --set core --sizes 1080p` を FAST=0/1 で比較: テーブルの 10 op が 1.3〜10×(gerode 10×、gaussian 5.3〜5.8×、mean_box 4×、sobel_mag/canny/std_filter 1.5〜1.8×)、dtype 変化ゼロ、テーブル外の op は経路同一で不変。速度は大きいが cv2 twin は内部差 5e-3 を持ち込み、本ライブラリの**再現性(SHA-256 ピン留め)を全ユーザーに対し暗黙に破る**ため既定 ON にしない。速度が要る動画/リアルタイム時に `FULLSEYE_FAST=1` で明示 opt-in する設計。
- **uint8 の fail-closed** — 従来 `apply()` は uint8 を拒否せず、gaussian が uint8 を返し threshold が全 1 を返していた(`docs/design/PERF_MEMORY_VIDEO_SURVEY.md` §1.3)。`on_error="raise"` は `ValueError`、既定は `/255`(uint16 `/65535`)に変換し台帳に `source="input"` で記録。float64 入力の結果は 1 ビットも変わらない(SHA-256 で固定)。`_coerce_input` の `np.unique` を O(N) に(region op 2 倍速)、ACCEL 逆引きをキャッシュ。
- **ベンチ台(`tools/bench_ops.py` + `bench/bench_ops_baseline.json`)** — op×サイズ×dtype の ms / Mpx/s / メモリ倍率 / 出力 dtype / fallback / 入力破壊を同 run 相対で記録、`--baseline` で ±30 % 退行を検出。ノイズ画像必須(median は内容で 10 倍変わる)。初回で `cv_dist` が float32 を返していた契約違反を発見→修正。
- 調査報告 `docs/design/PERF_MEMORY_VIDEO_SURVEY.md`(65 op 実測: 遅さの正体は scipy.ndimage 単スレッド float64、1080p 30 fps に届くコア op は 56 中 25、GPU 常駐 5-op 連鎖 2.1 ms/フレーム)。

### 利用者が気づく挙動変更(要注意)

- **`apply()` / `run_pipeline()` に `on_error="fallback"|"warn"|"raise"`**(環境変数 `FULLSEYE_ON_ERROR`)。既定でも op ごとに 1 回 `FullseyeFallbackWarning` が出る(`warnings.filterwarnings("ignore", category=fullseye.FullseyeFallbackWarning)` で消せる)。`fullseye.fallbacks()` / `fallback_counts()` が台帳(直近 256 件、出所 op/gpu/input/import)。GPU は初回失敗で Circuit Breaker が開く(`fullseye.reset_gpu()`)。
- **`fscript`**: `mean_gray/min_gray/max_gray` は 0..1 の比率 / 署名済みレシピは digest 変更で再署名が必要 / `read_image` は `base_dir` 内に限定 / タプル演算・添字・数値字句が厳格化。
- **`measuring1d`**: `amplitude` = 濃度差(旧 勾配ピーク ≈0.32×)、`threshold` も濃度差基準、`row/col/dist` 追加 / `metrology` は実形状で再フィット(楕円/矩形が円扱いだった)。
- **`calib.camera_calibration` は (row, col) 入力**(fx↔fy, cx↔cy が入れ替わっていた)/ `caltab.find_marks_and_pose` は失敗で例外(旧 identity)。
- **`algo`**: 番兵 0.0→−1.0(`is_prime` / `segments_intersect` / `edit_distance` / `point_in_polygon` / `lcs_length`)、2^53 超の整数は `ValueError`、graph n ≤ 5e6。
- **`imgio.save` は uint8 を彩色しない** / 切れた JPEG は `ValueError`(旧 黙って部分画像)/ 偶数線幅が 1px 細く / `to_float01(int16)` はアフィン / RGBA 保存の ABGR 入替を修正。
- **`pnp3d`**: 完全平面入力は平面経路で解く / `bundle3d` は `scale_anchor` で尺度固定(×0.7〜213 に発散していた)/ `register(init="auto")` / PPF 投票の角度符号を修正。
- **`raytrace`**: 数値引数に bool / 文字列を渡すと `ValueError`(旧 `"50"` → 50.0)、`stop` は整数のみ、`mirror` は bool のみ、零長の方向ベクトルは拒否、屈折率公差は硝材のみ(空気層には掛けない)、`n < 1` になる摂動は `ValueError`。`optimize_lens` は `status`(converged / stalled / iterations)を返し、bounds は初期値にも適用。
- **`vol_resize`** が定数体積の隅を 0.42 にしていたのを修正 / `convol_image` は畳み込み(相関だった)/ `radon` の既定角 135°。
- 進化エンジン: NaN fitness が champion になれない / RPCA の入力縮小で欠陥が消えない / pyramid の 1px ずれ修正。

### 構造・品質

- **fail-soft 3 層の沈黙を解消**: 全 backends(31 本 + macro/typed)の `_safe` を `backend_safe.guard()` に一元化(記録・strict・sanitize)。設計根拠は `docs/design/TRIZ_DESIGN_PATTERN_MATRIX.md`。
- **CI 常設**: `tests/test_op_probe_ledger.py` + `docs/OP_PROBE_ALLOWLIST.json`(退化 op は理由付き許容、新規は fail)、typed ブリッジの sort 跨ぎ恒等/定数検査、OP_CATALOG / SENSOR_PLAYBOOK / 記事展示 / op docs / Studio help の drift 検査、`examples2d` 両方向検査、**op→example 100 %**(3D 317 / 2D 860)。
- 徹底敵対レビュー 7 領域 72 件 + 前回残 8 件 + 死んだ op 12 件 + 同名 4 組 + ブートストラップ 34 本を修正(`docs/KNOWN_ISSUES.md` に再現手順)。Codex 読取レビュー 3 巡(13 + 10 件)を実コード検証のうえ反映。
- **op ドキュメント体系**: `docs/ops/**`(per-op ノート 1,500+、24 ファミリガイド、全 snippet 実行検証)を `tools/opdocs.py` が生成し Studio help に変換、`docs/OP_CATALOG.md` は登録簿から生成。

### 記事・その他

- Qiita 総合紹介記事 ja/en を 860 / 317 / HALCON 981(42.4 %)へ更新、展示 141 点、イトカワの新静止画(Hapke + レイキャスト影)を追加。`tools/qiita_patch_overview.py`(GET 退避 → 画像 HEAD 全数 → 縮小ガード → PATCH → 検証)。
- サンプルデータは非同梱(`fullseye samples list/open/download`、fail-closed)。

## 0.1.4 — 2026-08-31

`em_skeleton`(EM93 で検証)、骨格グラフ 2D/3D、3D morphology の scipy 経路 + ball SE + open/close。733 + 271 op、6,301 テスト。

## 0.1.3 — 2026-08-30

バグ一掃リリース: KNOWN_ISSUES 5 件(`count_obj` 8 連結 / `sk_frangi` ノブ配線 / XLD トレース順 / CLAHE 双線形補間 / DStretch RGB 受理)。Studio に Feature Inspection 2D/3D・対話 3D ビューア・`disp` 系ディレクティブ。`pyproject.toml` の BOM/cp932 化け(PowerShell 書込み事故)を復元。

## 0.1.2 — 2026-08

セキュリティと i18n: GitHub Actions を commit SHA に固定、`fullseye-rag` の英語ヘルプ。

## 0.1.1 — 2026-08

bare-install 修正: 3D レジストリ(`ops3d`)が numpy + scipy のみでも import できる。

## 0.1.0 — 2026-08-01

初回公開: 約 1,000 の型付き画像処理 / 幾何ビジョン op(numpy ネイティブ、HALCON 語彙)、進化エンジン、Studio、C/Python codegen。
