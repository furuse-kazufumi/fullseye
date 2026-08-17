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
  honest-gate 状態を機械可読で持つ(Studio と эージェントが同じメタを使う)。
- **F4 OSS アダプタ契約**: OSS(PCL/OpenCV/grid_map 等)を裏に持つ op も、F1〜F3 を満たす同一 I/F で見える。
  OSS 不在時は明示エラー or 自作フォールバック(optional extras 方針)。
- **F5 合成**: op をパイプライン化して繋げられる(画像チェーン / 知覚の段組み)。
- **F6 Studio 露出**: 同一メタ(F3)から Studio が op を自動列挙・パラメータ UI 生成・実行できる。
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
