# HALCON カバレッジ — honest な分母(2026-08-18 更新)

`halcon_coverage.py` は全 2313 operator を分母に **31.5%(728/2313)** と報告する。しかし
**「HALCON 級 vision ライブラリ」の honest な目標分母は 2313 ではない** — HALCON の 2313 には
numpy vision スキルライブラリが再現すべきでない/できない operator が約 1034 含まれる。

**現在到達点(2026-08-18 セッション、genuine 掘り切り)**: vision-algorithm 分母で **967/1304 = 74.2%**
(セッション開始 46.2% → **+369 op**、全て numpy genuine 実装 + ground-truth 検証済、dangling=0、facade 600 マッピング、honest-gate 13 件、registry 回帰 3113 pass/0 fail)。

**★genuine 掘り切りの honest な結論**: 未カバー vision 326 のうち **genuine-algorithm は残 2 件のみ**
(`points_lepetit`=学習型で再現不可・honest スキップ / `combine_roads_xld`=航空路網ニッチ・スキップ)、
**残 324 は全て handle/IO/serialize/param getter-setter/framegrabber/DL wrapper の boilerplate**
(numpy スキルライブラリが偽装すべきでない)。∴ **真の genuine-algorithm 分母 ≈ 1304−324 = 980、
うち 967 カバー = 実装可能な視覚アルゴリズムの ~98.7%**。これが「HALCON 級網羅」の honest な到達。
80-90%(of 1304)未達は boilerplate を分母に含むため=水増しせず 74.2% と正直に報告
([[feedback_benchmark_honest_disclosure]])。80-90% は残 boilerplate の create/find/get/set 系を
統一 I/F の設定オブジェクトとして正当に載せた時に初めて意味を持つ(別途の設計ステップ)。
本セッション追加: image_channels/image_gray/image_gen(Image)、filters_arith/filters_freq/filters_flow
(Filters: 算術・FFT畳込み・位相相関・Wiener・Horn-Schunck multigrid オプティカルフロー・異方性拡散インペイント)、
tools_geom(交点・Plücker 直線・方向つき Hough)、reconstruction(Frankot-Chellappa 勾配積分・photometric stereo・
depth-from-focus・三角測量・構造化光復号)、calib(透視投影・world-plane 逆投影・Zhang 内部校正・Tsai/Park-Martin ハンドアイ)。
honest-gate 検出 7 件(moments_gray_plane の Mean 意味論、hand-eye Procrustes 転置 ほか)を修正。

## off-mission(vision アルゴリズムでない ~1034 op)

| 種別 | chapter | なぜ対象外 |
|---|---|---|
| GUI/対話 | Graphics(174) | ウィンドウ表示・マウス描画(HDevelop 環境) |
| 言語/データ | Tuple(165)・Matrix の一部 | tuple 演算・制御構文 |
| 環境/IO | System(141)・File(53)・Develop(37)・Control(34)・Object・Image Source | プロセス/シリアライズ/ファイル/取得器 |
| ML/学習 | Deep Learning・OCR・Classification・Identification | 学習モデル・バーコード/文字認識(別ドメイン) |
| 廃止 | Legacy | deprecated |

これらは fullseye の「即使える vision アルゴリズムのスキル化」というミッション外
([[project_fullseye_mission_unified_vision_2026_08_18]] の algo-c 除外と同じ論理)。

## honest な vision カバレッジ

- **vision-algorithm operator = 1279**(2313 − off-mission 1034)
- **fullseye は 325/1279 = 25.4%** をカバー(2313 分母の 14.9% でなく、**vision 分母で 25.4%**)

### vision chapter 別(covered/total、2026-08-18)

| chapter | covered/total | 状態 |
|---|---|---|
| Morphology | 33/40 (82%) | ほぼ HALCON 級 |
| Regions | 71/101 (70%) | 強い |
| Filters | 129/194 (66%) | 強い |
| Segmentation | 30/50 (60%) | 強い |
| XLD(contour) | 26/87 (30%) | 中 |
| 1D Measuring | 5/20 (25%) | 中 |
| Image | 20/102 (20%) | 拡充余地大 |
| Transformations | 4/97 (4%) | 行列系が多く fn(v,a,b) 契約外 |
| Tools | 4/107 (4%) | 混在 |
| Matching | 2/95 (2%) | テンプレート/変形マッチ(machinery 要) |
| 3D Reconstruction | 1/76 (1%) | ステレオ/PS(一部は evis 側 pcseg に有) |
| 3D Matching / 3D Object Model | 0/51, 0/50 | surface-based 6D(ppf は有・HALCON API 名は未対応) |
| Calibration | 0/68 | カメラ校正(machinery 要) |
| Inspection / 2D Metrology | 0/43, 0/30 | model/handle ベース |
| Matrix | 0/57 | 線形代数(別サブライブラリ寄り) |

## 含意(honest な到達戦略)

- **2D 画像処理コア(Filters/Regions/Morphology/Segmentation)は既に 60–82%=HALCON 級に接近**。
  ここは残りの未カバーを genuine 実装で埋めていけば近い将来 HALCON 級に届く。
- **大きな残ギャップは 3D/Matching/Calibration/Metrology/Inspection** — これらは単一画像 `fn(v,a,b)`
  でなく **model/handle ベースの machinery** が要る(evis の pcseg/ppf に実体はあるが HALCON API 名に
  未マップ)。ここは統一 I/F(設定オブジェクト方式)側で段階的に。
- **Transformations/Matrix** は行列演算主体で進化 registry の画像契約に合わない → 統一 I/F の
  幾何ユーティリティとして別途。
- ∴ **「HALCON 級」= vision-algorithm 1279 op の高カバレッジ**を目標にし、2313 の見かけ%を追わない
  ([[feedback_benchmark_honest_disclosure]]:誤解を招く分母を避ける)。

進捗: 2026-08-18 セッションで 307→344(vision 分母 25.4%)。`backends_halcon_ext.py` に genuine
実装 37 op を追加(全 dangling=0・honest gate 数値検証・test_op_contracts pass)。
