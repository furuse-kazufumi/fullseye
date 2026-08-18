# Fullseye 統一インターフェース — 要件定義書 (v0.1, 2026-08-18)

> 2026-08-17〜18 のディレクションを踏まえた要件定義。方針正本 = raptor memory
> `project_fullseye_mission_unified_vision_2026_08_18`、gap 分析 = `EVIS_VISION_OSS_GAP.md`。
> 本書は **何を・なぜ**(要件)を定める。**どう作るか**(実装)は本書合意後の設計/spike で。

## 1. 背景・目的

Fullseye = **あらゆる画像処理/視覚アルゴリズムを『スキル』として保持し、即使える包括的ライブラリ**
(=専用 HALCON)。目標は **HALCON 級網羅**(実測 307/2313 = 13.3%、`HALCON_COVERAGE.md` を伸ばす)。
現状、アルゴリズムは 3 つの別インターフェースに分裂しており、**使う側(人間・Studio・evis 視覚・エージェント)から
一貫して呼べない**。本件の目的は **使う際のインターフェースを統一**し、どのアルゴリズムも同じ自然な作法で
発見・呼び出し・introspection・Studio 露出できるようにすること。

## 2. 対象ユーザーと利用シーン

| ユーザー | シーン | 含意 |
|---|---|---|
| **本人(人間)** | REPL / スクリプトで手書き、仕事で使う | ★**サンプルコードが人間から見て自然**であること(最優先) |
| **Fullseye Studio** | GUI から op を把握・試験・パラメータ調整 | 同じ op を GUI からも一貫操作(introspection/メタが要る) |
| **evis 視覚パイプライン** | stereo→cloud→6D pose→(MoveIt2)→筋実現 | 知覚 op を統一 I/F で組める |
| **エージェント/自動化** | プログラム的に op を列挙・実行 | 発見可能(registry)・型/メタが機械可読 |

## 3. スコープ

**In**: 画像処理 op(現 registry 654)+ 視覚/知覚 op(現 facade 116)を統一 I/F に載せる。
自作 numpy 実装も OSS アダプタも同一 I/F。Studio 露出。introspection/メタ/honest gate の統一。
**Out**: 汎用 CS(algo-c: sort/CRC/Huffman/回文 = 39 op。画像/視覚の知見でない=対象外・凍結)。
OSS 内部の再実装(PCL/grid_map/OpenCV/MoveIt2 は薄いアダプタで裏に、再発明しない)。

## 4. 現状と課題(実測 2026-08-18)

3 層・3 規約に分裂:

| 層 | 数 | 現 呼び出し | 自然さ |
|---|---|---|---|
| 画像 registry | 654 | `apply(image, "gaussian", a=0.5, b=0.5)` = **文字列名 + 汎用 2 ノブ a/b** | ✗ 最も不自然(進化用エンコード) |
| algo(対象外) | 39 | `run_algo("name", seq)` = 文字列 dispatch | ✗(だが off-mission) |
| 知覚 facade | 116 | `fs.disparity_sgm(left, right, max_disp=16, ...)` = 名前付き引数 | △ 比較的自然だが registry/introspection 無し |

- **単一の op 発見/registry が層を跨いで無い**(画像だけ REGISTRY、知覚は素の関数)。
- **呼び出し規約が非対称**(進化用の a/b 2 ノブ vs 名前付き引数)。
- **メタ(in/out 型・doc・honest gate・provenance)の持ち方が層ごとに別 or 無し**。
- 既存 770 op(654+116)を**壊さず**移行する必要(後方互換)。

## 5. 機能要件

- **F1 統一呼び出し**: 全 op を同一の自然な作法で呼べる。画像 op は**意味のある名前付き引数**を持つ
  (進化用 a/b の生露出を使う側に見せない)。
- **F2 統一発見(registry)**: 層を跨いで op を列挙・検索・カテゴリ分類できる単一の索引。
- **F3 introspection/メタ**: 各 op が name / 入出力型 / パラメータ(名前・型・既定・範囲)/ doc / provenance /
  honest-gate 状態を機械可読で持つ(Studio と эージェントが同じメタを使う)。**+ 描画ヒント**(出力を
  Studio でどう可視化するか: `image` / `point_cloud` / `pose` / `grid_map_layer` / `scalar` 等)を持ち、
  Studio が RViz2 相当の 3D/2D 描画を自動選択できる。
- **F4 OSS/sim アダプタ契約**: OSS(PCL/OpenCV/grid_map 等)を裏に持つ op も、F1〜F3 を満たす同一 I/F で見える。
  OSS 不在時は明示エラー or 自作フォールバック(optional extras 方針)。**sim ソース**(`sim.MuJoCo`/`sim.Gazebo`/
  `sim.IsaacSim`)も同一契約で、共通の動詞(`.frames()`/`.depth()`/`.intrinsics()`/`.ground_truth()`)で視覚 op に
  入力を供給する(入力元を問わず op が組める。ground_truth は honest 評価の真値源)。
- **F5 合成**: op をパイプライン化して繋げられる(画像チェーン / 知覚の段組み)。
- **F6 Studio 露出**: 同一メタ(F3)から Studio が op を自動列挙・パラメータ UI 生成・実行できる。
  **Studio = HDevelop(2D 画像処理 IDE)+ RViz2(3D 知覚可視化)の融合**: 2D 画像パネルに加え、
  点群 / depth / 6D pose 軸 / TF 木 / grid_map layer を 3D 表示(F3 の描画ヒントで自動選択)。
  3D viewer は再実装せず既存(Open3D/RViz2 連携 or 薄い描画)を裏に。
  **★ドメインの棲み分け(ユーザー要望 2026-08-18)**: Studio は op/sample を 2 ドメインに**きれいに分けて**
  提示する ── **vision(視覚 op = fullseye が"計算する")** と **sim-source(物理が"供給する": RGB/depth/
  LiDAR/真値)**。この分業(fullseye は物理をやらない=F4/gap 分析と同一)を UI 上でも崩さない
  (タブ/カテゴリ分け)。**どちらのドメインも各エントリに実行可能なサンプルコードを添える**
  (人間が読んで自然な Qt 風。Studio で「見て・コードを読んで・その場で実行」できる)。
  種 = `spikes/studio_sample_catalog.py`(vision: image.chain / cloud.perceive、sim-source: sim.lidar /
  sim.to_vision。各 sample が name/domain/summary/**code**/run を持つ = F3 introspection のミニ版)。
- **F7 後方互換**: 既存 770 op と現 API(`apply`/facade 関数)を壊さない(統一 I/F は上に薄く載せる)。

## 6. 非機能要件

- **N1 人間可読性(最優先)**: サンプルコードが自然に読める。**Qt 風ツールキット設計**を参考(§7)。
- **N2 discoverable**: 名前空間・命名一貫・IDE 補完が効く。
- **N3 自己完結**: 基本は stdlib+numpy で動く。重量級(GPU SGM/deep pose)のみ optional extras。
- **N4 網羅性**: HALCON カバレッジ地図(`HALCON_COVERAGE.md`)/ ROS2 標準(PCL/grid_map/image_pipeline)を
  **抜けの地図**として使い、統一 I/F 上で網羅を伸ばせる構造。
- **N5 検証可能性**: honest gate(reference == 独立 oracle、C codegen 系は bit 一致)を統一 I/F でも保持。
- **N6 忠実性**: OSS/ROS2 の実用語彙・意味論に命名/挙動を合わせる(移行学習コスト低)。

## 7. API 設計方針(Qt 風・人間が書いて自然)

**悪例(現状)**: `apply(image, "gaussian", a=0.5, b=0.5)` / `run_algo("name", seq)` = 機械向け string-dispatch。

**目指す自然さ(案・§9 で要ユーザー判断)**:
```python
import fullseye as fs
# core オブジェクトのチェーン(画像 op):文のように読める
edges = fs.Image.load("scene.png").to_gray().gaussian(sigma=1.4).sobel()
# 名前空間モジュール + 設定オブジェクト + 動詞メソッド(知覚 op):Qt ウィジェット風
depth = fs.stereo.SGM(max_disp=128, window=5).compute(left, right)
cloud = fs.camera.Pinhole(K).backproject(depth)
plane = fs.pcseg.PlaneRANSAC(thresh=0.01).fit(cloud)
```
Qt から借りる: **名前空間モジュール**(`fs.stereo`/`fs.camera` = QtWidgets 風)・**設定オブジェクト+動詞メソッド**
(`.compute()`/`.fit()`/`.apply()`)・**core オブジェクトのチェーン**(`Image`)・**sensible defaults**・
**discoverable**。文字列名/生 registry/進化用 a/b は**裏に隠す**。

## 8. 制約・前提

- 既存 770 op と進化エンジン(op registry は進化の基盤)を壊さない → 統一 I/F は**上に載せる層**。
- OSS は再発明しない(薄いアダプタ)。汎用 CS(algo-c)は含めない。
- 分類/命名は HALCON/ROS2 の実用語彙に忠実(N6)。

## 9. 要ユーザー判断(実装前に確定したい)

1. **画像 op の作法**: `fs.Image(...).sobel()` の**チェーン**か、知覚と同じ**設定オブジェクト方式**に統一か。
2. **実行モデル**: **eager**(即計算・REPL/Studio 向き)か **lazy パイプライン**(`.run()` で確定)か。
3. **命名**: HALCON 語彙寄せ(`dyn_threshold` 等)か、一般語彙(`adaptive_threshold`)か。
4. **Studio 露出**: 最初の spike に含めるか、Python API 先行か。

## 10. 受け入れ基準(統一 I/F の "done")

- 画像 op と知覚 op を**同一の自然な作法**で呼べる(サンプルが Qt 風に自然)。
- 全 op が単一 registry で発見でき、F3 のメタを持つ(Studio と共有)。
- 既存 770 op / 現 API が壊れていない(回帰 0)。
- OSS アダプタが同一 I/F で 1 例以上動く(例: stereo か pcseg で PCL/OpenCV 裏)。
- honest gate が統一 I/F 上でも走る。

## 11. 段階計画(案)

1. **本要件定義の合意**(§9 の 4 判断)。
2. **設計 + 小 spike**: `Image` チェーン + 知覚 1 モジュール(例 `fs.stereo`)を既存実装の**薄いラッパ**で。additive・回帰 0。
3. **メタ/registry 統一**(F2/F3)→ 既存 op を段階的に載せる。
4. **Studio 露出**(F6)。
5. **OSS アダプタ契約**(F4)を 1 領域で実証(stereo=image_pipeline / pcseg=PCL)。
6. **網羅を伸ばす**(N4、HALCON/ROS2 地図の抜けを honest gate 付きで補完)。

## 12. 決定ログ

- **2026-08-18 要件定義に合意(ユーザー)**。§9 の 4 判断は既定を採用:
  ①**混成**(画像=`Image().gaussian()` チェーン / 視覚=`stereo.SGM().compute()` 設定オブジェクト)
  ②**eager** ③**一般語彙を主 + HALCON エイリアス** ④**Python API 先行**(Studio は次段)。
- **F1 実現方針 = approach B(単一実装)**: 自然 API は下層(scipy.ndimage 等)を**自然パラメータで直接**呼ぶ
  (gaussian は `ndimage.gaussian_filter(v, sigma)`= 進化 op と同じ下層ゆえ drift 無し)。進化 registry の
  汎用 a/b ノブ(探索用の正規化・有界エンコード、例 `sigma=0.3+2.7*a`)は**人間 API のパラメータ範囲に漏らさず**、
  `Image.op(name, a, b)` エスケープハッチにのみ残して 654 op の長い尾へアクセス。
- **spike 実証済**: `spikes/unified_api_spike.py`(画像チェーン + 視覚設定オブジェクト + 長い尾エスケープ)。
  既存 809 op 無変更・additive。pcseg RANSAC が合成平面 400/400 点をインライア検出=実委譲を確認。

- **2026-08-18 F1/F2/F3 実装完了(統一視覚 I/F 本体)= `unified.py`**:
  本セッションで実装した **600 の HALCON facade op**(genuine numpy、`data/halcon_facade_map.json`)を
  **単一 registry + introspection メタ + 章別名前空間**に載せた。additive・既存 op / 進化 registry /
  fullseye パッケージ facade を一切変更せず(F7)。
  - **F2 統一発見**: `Registry`(`ops`)が 600 op を層横断で索引。`ops.find(q)`(名前/doc/章の全文検索)/
    `ops.list(namespace=…)` / `ops.stats()`。
  - **F3 introspection**: 各 op が `UnifiedOp`(name/実装関数の**自然シグネチャ**(inspect)/主 chapter/
    namespace/doc/**render_hint**(image/region/contour/pose/point_cloud/matches/scalar/matrix)/provenance)。
    `ops.describe(name)` が機械可読 dict を返す(Studio/エージェント共有)。**描画ヒントは F6(Studio)の 2D/3D
    自動描画選択メタ**。
  - **F1 自然呼び出し**: **17 章別名前空間**(`contour`/`calib`/`recon3d`/`region`/`match`/`transform`/
    `filter`/`image`/`tools`/`object3d`/`match3d`/`segment`/`measure`/`metrology`/`morph`/`matrix`/`inspection`)。
    例 `u.calib.camera_calibration(obj, views)` が Zhang 校正で真値 K を復元。進化用 a/b は露出しない
    (各 op は自然な名前付き引数)。
  - **fullseye 統合**: `fullseye/__init__.py` に additive 露出 → `fs.vision.<ns>.<op>(...)` / `fs.vision_ops`。
    進化 REGISTRY(735)・知覚 facade(fs.stereo 等)と共存。
  - **検証**: 動くデモ `spikes/unified_vision_demo.py`(F1/F2/F3/F7 を実走表示)。テスト `tests/test_unified.py`
    9 件 pass。回帰 `test_op_contracts` 3113 pass 0 fail(F7 確認)。
- **2026-08-18 F6 Studio 露出 実装完了**: 統一 registry(`fs.vision_ops`)から Studio が **600 op を
  自動列挙・パラメータ UI 自動生成・実行・描画自動選択**する 2 プリミティブを `spikes/studio_ops_browser.py` に:
  - **`render_by_hint(result, hint, fig)`** = F3 の render_hint で **2D/3D 描画を自動選択**(image=imshow /
    region=マスク / contour=線 / point_cloud=3D 散布 / pose=RGB 軸 / matrix・scalar・matches=カード)。8 種全て検証。
  - **`synthesize_args(op)` / `scalar_param_specs(op)`** = F3 の**自然な param 名**から合成入力と
    スライダ spec を作る(param 名が意味を持つ=F1 の設計が効く)。**honest 自動実行カバレッジ = 364/600(60%)**
    が合成入力だけで即実行・描画。残りは create_* が生む model handle 等の専用入力要(209)+ synthesizer の
    形状ヒューリスティック外(27)で、いずれも **F3 introspection カード**(signature/doc/params/render_hint)を
    表示=600 全てが「発見+メタ把握」できる。
  - **GUI 統合** = `spikes/studio_app.py` のツリーに `vision-ops (600)` を**章別名前空間で自動展開**、
    op 選択で F3 カード + スライダ自動生成 + `render_op_into`(スライダ override→合成入力→render_hint 描画)。
    既存 9 サンプル(vision/sim-source 棲み分け)と共存。smoke = 9/9 サンプル OK + 代表 op 経路 + カバレッジ表示。
  - **検証** = テスト `tests/test_studio_ops_browser.py` 7 pass(render_hint 8 種・合成入力・カバレッジ>=300・
    override 反映)。ギャラリー `spikes/out_gallery/studio_f6_render_hints.png`(8 hint の描画一覧)。
- **2026-08-18 F2 全 op 1 索引 統合完了(3 層マージ)**: `unified.py` が **3 層を単一 registry に統合**:
  ①**facade 600**(本セッションの genuine HALCON 実装)②**進化 registry 729**(`fs.REGISTRY`, a/b ノブ、
  自然 caller `(image, a=0.5, b=0.5)` で長い尾へ、provenance=evolution)③**知覚 facade 240**(`fs.stereo`/
  `pcseg`/`camera`/`terrain`/… の公開関数、自然シグネチャ、provenance=perception)。**計 1569 op / 57 名前空間**。
  - **衝突処理**: facade を最初に登録=bare 名衝突は genuine facade 優先(既存挙動維持)。各 op に `provenance`。
  - **render_hint**: 進化 op は `out_sort`(image/region/contour/feature/match/volume/color)→ hint。知覚 op は
    モジュール既定 hint。→ Studio(F6)が 3 層すべてを render_hint で自動描画。**自動実行カバレッジ 1129/1569(72%)**。
  - **循環 import 解消**: fullseye が unified を、unified が fs.REGISTRY/知覚 facade を読むため、遅延構築
    (PEP 562 `__getattr__`)+ publish-before-load で re-entrancy 安全化。両 import 順で動作。
  - **検証**: `import fullseye`/`import unified` 双方で 1569 op、`fs.vision.smooth.<op>(img,a,b)`(進化)/
    `fs.vision.camera.intrinsic_matrix(...)`(知覚)/ `fs.vision.calib.camera_calibration(...)`(facade)が
    同じ作法で呼べる。テスト `tests/test_unified.py` 9 pass(3 層 provenance 検証)+ browser 7 pass、
    回帰 `test_op_contracts` 3113 pass 0 fail(F7)。
- **次**: F4 OSS アダプタ契約(stereo=image_pipeline / pcseg=PCL)/ synthesizer の per-op 入力ヒント拡充
  (自動実行 72%→上げる)/ Studio 3D viewer を Open3D/RViz2 連携へ(現状 matplotlib 3D)。
