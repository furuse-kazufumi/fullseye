# Changelog — fullseye

All notable changes to the PyPI package `fullseye`. Dates are release dates (JST).
Versions follow the git tags; a tag push publishes to PyPI (`.github/workflows/release.yml`).

## 0.1.5 — unreleased (main since 2026-08-31)

**Summary (en)**: the largest release so far — 63 feature/fix commits, 2,600 files, +219k lines.
Registry now measures **870 distinct 2-D ops + 344 3-D ops + 417 ledger ops** (math 26, optics 47,
light field 17, photon counting 17, specular 13, motion magnification 9, quaternion 19, FMCW 8,
acoustics 19, interferometry 9, tomography 17, volume colour 11, representation 42, CAD 4,
annotate 46, gfx2d 32, image metrics 24, colour transport 11, forensics 16, astro stacking 14,
video streaming 16).
Full suite: **10,550 passed / 153 skipped / 3 xfailed / 0 failed**. Four things a user notices:
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
- **動画ストリーム(`videostream` / `opsvideostream` 8 op)** — `FrameRing`(直近 N 枚をフレームの dtype のまま: uint8 1080p×5 = 10 MB、float64 一括 1 秒は 475 MB)、状態つき op(`TemporalMedianWindow` / `MovingAverageWindow` / `BackgroundSubtractionWindow` / `FrameDifference` / `ExponentialBackground` / `RunningStats` / `OpticalFlowStream`)、`VideoPipeline`(台帳 op・状態つき op・callable を混ぜ、失敗時は状態リセット+台帳 `source="stream"`)。台帳の一括 op は同クラスの再生なので **ストリームと一括がフレーム単位で一致**。`iter_frames(dtype="uint8")` で整数素通し(1080p 読み込み 18→約 180 fps)。videops と同名にしない(因果窓は別名)。
- **CPU 高速 twin(`fast`、41 op、既定 OFF)** — `FULLSEYE_FAST=1` または `apply(..., fast=True)` で cv2/IPP の twin を使う。accel と同型の parity ゲート(5 (a,b)×6 画像、内部 <5e-3、二値 op は不一致率 0)を **通ったものだけ**登録: gaussian 8.6×、median k=5 29×、gerode 14.6×、gopen 7.6×(2048²、熱定常でない同 run 相対)。clahe(0.135)/ bilateral(0.121)/ 回転・拡縮(スプライン次数)/ equalize / otsu(二値で 0.004)は**速いが違うので載せない**(`fast.NOT_LISTED`)。uint8 整数カーネル `fast.apply_uint8`(median k=5 185×、box 27×、gopen 50×; gaussian は 1.17/255 ずれるので除外)。
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
