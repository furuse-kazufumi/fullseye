# Changelog — fullseye

All notable changes to the PyPI package `fullseye`. Dates are release dates (JST).
Versions follow the git tags; a tag push publishes to PyPI (`.github/workflows/release.yml`).

## 0.1.5 — unreleased (main since 2026-08-31)

**Summary (en)**: the largest release so far — 63 feature/fix commits, 2,600 files, +219k lines.
Registry now measures **860 distinct 2-D ops + 317 3-D ops + 380 ledger ops** (math 26, optics 47,
light field 17, photon counting 17, specular 13, motion magnification 9, quaternion 19, FMCW 8,
acoustics 19, interferometry 9, tomography 17, volume colour 11, representation 42, CAD 4,
annotate 25, gfx2d 32, image metrics 24, colour transport 11, forensics 16, astro stacking 14).
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
