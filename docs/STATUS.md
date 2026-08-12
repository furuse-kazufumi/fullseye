# imgevolve — status / plan (plan_ref)

**公開名 = fullseye**(2026-08-01確定 = full[FullSense]+bullseye[的を射る=正しいアルゴリズムを当てる]・PyPI/GitHub完全クリーン)/ **作業名 imgevolve**。物理リネーム(dir/repo/PyPI)は公開時=llcore統合可否確定後まで保留。画像処理アルゴリズムを **設計する** AI。
**スケーラブルなオペレータ・レジストリ**を進化させ、holdout で正直にゲートし、多言語
(Python/C)コードに codegen する。目標は **HALCON 級のオペレータ網羅**。

設計の正本: `C:/dev/tools/raptor/docs/design/imgevolve_s0s1_workgraph.md`

## 差別化(先行研究で確定, 2026-08-01)
AlphaEvolve(生ソース進化)/ TransCoder(翻訳)/ Halide(schedule 探索)いずれも
「アルゴリズム発見 × 型付き画像IR × 検証済み多言語codegen × オンデバイス × honest holdout」を
全部は満たさない。

## 現在地(v10 = 実 HALCON 被覆計測, 2026-08-01)
- **スケーラブル・レジストリ**(`ops.py` の `REGISTRY`, **153 op**)。op を1つ足すだけで進化も
  codegen も catalog も自動追従。core 67 + backend 86(skimage/opencv/torch を optional wrap)。
- **多ソート型システム(6+1 ソート)**: image / region / feature / contour(XLD) / match / any / volume(3D)。
- **10 タスク**: denoise/edge/binarize/count/locate/locate_rot/classify/barcode/vol_denoise/vol_count。
- S2 codegen(IR→Python+C)+ difftest(honest gate)。

### ★実 HALCON 被覆(memory 由来の推測を廃し、公式リファレンスを実スクレイプ)
- `halcon_scrape.py`: MVTec 公式 Operator Reference を実スクレイプ → **実 2313 op(HALCON 26.05,
  最新)/ 30 top-level 章 / 説明文 100%**。`--version` 引数化・`--op-sets` で複数版スナップショット。
- `halcon_coverage.py`: レジストリの `Op.halcon` を実リファレンスに突合。
  **被覆 = 79 / 2313(3.4%, 最新版)/ dangling = 0**(全 `.halcon` が実 HALCON 名 or 正直に空)。
- **バージョン横断(op 集合は版で増減する)**: v12=2147 / v13=2176 / v2311=2381 / v2411=2387 /
  v2505=2411 / **v2605=2313(最新, Legacy 209→110 に削減)**。union=2466。
  `.halcon` 名を **stable(全版)=77 / version-drift=2(`bilateral_filter`・`guided_filter`=v13 追加)/
  never(捏造)=0** に分類 = honest disclosure。
- **`mvtec-halcon` PyPI バインディング(版一致 26050.0.0=26.05)から型付き Python シグネチャ**を
  抽出 → typed stub(`data/halcon_stubs.json`, 2235/2313 に実シグネチャ)。3ソース(HTML scrape /
  binding / 被覆)が「dangling は本物の誤り」で一致=三重確定。
- 成果物: `docs/HALCON_COVERAGE.md`(版認識+gap ランキング)。scrape データは再生成可能な
  ローカルキャッシュ(`data/` は gitignore, MVTec docs/EULA 配慮で vendor しない)。

## ★現在地(v11 = HALCON-parity 自動生成 + 機能ゲート, 2026-08-12)
**目標の再確認(ユーザー)= 「HALCON と同じことができる」= 名前だけの被覆でなく各 op が
実際に同じ処理を行える**。これを honest に達成する土台を構築:

- **operator 知識グラフ**(`graph.py` → `data/halcon_graph.json`): 2313 op を
  {章 / desc / 型シグネチャ / arity(HObject入力数) / 推定sort / algorithm判定 / covered}
  でノード化。**unary algorithm = 535(honest な対象規模)/ n-ary = 210**。fan-out と
  自動生成の土台(正本 = STATUS.md の plan step 1)。
- **固定 shape 語彙 + データ駆動生成**(`backends_auto.py`): 17 の検証済み factory shape
  (pointwise/lut/linfilter/rank/graymorph/edge/freq/diffusion/texture/geom/threshold/
  segment/binmorph/region_trans/region_feat/img_feat/xld)を **手書きで正しく実装**。
  `SPECS`(halcon名→shape+params の**データのみ**)を語彙にマップ。**halcon 名は実
  reference で実在検証し、偽名は fail-closed でドロップ(捏造で被覆を水増ししない)**。
- **章別 fan-out**(`specs/fanout_workgraph.js`, 8 agent workflow): 各 algorithm 章の
  未被覆 unary op を固定語彙にマップした verified specs(`data/auto_specs/*.json`)を生成。
  **agent は genuine analog のみ採用し、noise生成/色多チャネル/射影変換/逆FFT/コーナー検出/
  ドメインROI/学習モデル等は honest に skip**(捏造せず)。生成後、私が全マッピングを
  **一次スポットチェック**し、非 genuine を除去(monotony/frei_dir/robinson_dir は誤マップを
  genuine 実装に差し替えて救済、equ_histo_image_rect/region_features/polar_trans_region/
  morph_skiz/gen_contours_skeleton_xld は同一性なしで削除)。
- **機能ゲート**(`verify_auto.py`): 各 op を canonical 画像/領域/輪郭で実行し、**例外なく
  宣言 sort を返すもののみ被覆にカウント**(「同じことができる」の実証)。
- **n-ary capability tier**(`imgops_nary.py`): 単一画像スレッドに載らない多入力 HALCON op
  (add/sub/mult/div/abs_diff/max/min_image、union2/intersection/difference/symm_difference、
  reduce_domain/overpaint_region/convol_image 等)を **17 op 本物実装**(全機能ゲート通過)。

**★honest 被覆(実測, `honest_summary.py` → `docs/HALCON_PARITY.md`)**:
- **269 / 2313 distinct real HALCON op を genuine 実装(11.6%)** = 進化 registry 252(color 12 含む)+ n-ary 17(disjoint)。
- registry ops 392(core 67 + backend 86 + **auto 227 + color 12**)。auto/color/n-ary は **全て機能ゲート通過**。
- v11f 増分 = Hough 変換(hough_line_trans/hough_circle_trans=accumulator図)+ subpixel crossings→contour
  (threshold_sub_pix/zero_crossing_sub_pix)+ closest_point_transform(補集合 EDT)+ junctions_skeleton +
  get_region_thickness。79→269 = **3.4倍**。
- **★map-to-shape 方式は実質出し切り**(v11→v11f 6ラウンド + fan-out 2回)。残 ~330 未被覆は
  (a) 専有/学習モデル(分類器・DL・OCR・Calibration・pose)(b) 多入力/n-ary(primitive間 distance・intersection・
  mosaic・union contours・compose)(c) 座標/tuple plumbing(getter/test/query)(d) ごく特殊な shape 要 =
  **新 capability か本質的 scope 外**。更なる breadth より **codegen/difftest による parity 実証(depth)** が本筋。

**★全 op 対応 = disposition map(`dispositions.py` → `docs/OP_DISPOSITION.json`)**: 偽実装で数を埋めず
(feedback_no_false_reporting)、**全 2313 op に truthful な disposition を付与(100% 対応、捏造 0)**。
`imgevolve.py has <任意の op>` が全 op に定義済み応答を返す(implemented=呼び方 / 未実装=status+理由)。内訳:
**implemented 269(11.6%)/ needs_new_capability 176(honest backlog)/ nary_multiinput 119 / out_of_scope_model 635(専有)/ out_of_scope_plumbing 1114(HDevelop言語・IO・getter=非アルゴリズム)**。
→ honest な分母(実装しうる algorithm 系 ≈ implemented+needs_new_capability = 445)に対し **269/445 ≈ 60% を genuine 実装**。
- **dangling(偽名)= 0**(fail-closed)。回帰スモーク 600〜800/同(image起点 decode+run クラッシュ0、color 到達も全 OK)。
- 開始(v10)79 → **245(registry)/ 262(総capability)= 3.3倍**。数値は memory 推測でなく実測。
- v11e 増分 = fan-out 第2ラウンド(拡張語彙で残精査、genuine 5: add_noise_distribution/polar_trans_region_inv/
  contour_point_num_xld/affine_trans_polygon_xld)+ corner 強度図(points_foerstner/points_harris_binomial)+
  XLD 楕円/モーメント特徴(eccentricity/orientation/elliptic_axis/diameter/rectangularity/moments_xld・shape_trans_xld)+
  zero_crossing・local_min・pruning。★fan-out 第2は total 5 のみ=**「shape へマップ」方式の genuine 天井が近い**シグナル
  (残未被覆は Hough/楕円フィット/subpixel点座標/多入力 distance・intersection/mosaic/pose/分類器モデル/run-length 等 =
  新 sort・新 capability か本質的 scope 外)。
- v11d 増分(XLD 輪郭群が主): 輪郭特徴 area_center_xld/circularity_xld/compactness_xld/convexity_xld・
  輪郭変換 close_contours_xld/affine_trans_contour_xld/projective_trans_contour_xld/polar_trans_contour_xld・
  region モーメント(moments_region_3rd/_central/_central_invar/_2nd_rel_invar/_3rd_invar)・
  dual_threshold・segment_image_mser(MSER)・regiongrowing_mean・estimate_noise。
- **★multichannel `color` sort 導入(v11c, ユーザー選択)**: `backends_color.py` に H×W×3 RGB の first-class sort。
  `cfa_to_rgb`(image→color, 実 Bayer demosaic)を bridge に進化から到達、`rgb1_to_gray`/`access_channel`/
  `edges_color` 等で gray へ復帰。**sort スレッドで型分離 → gray op に color は渡らず進化は無傷**。genuine 色op 12
  (trans_from/to_rgb・linear_trans_color・principal_comp・rgb1/3_to_gray・access_channel・edges_color(+_sub_pix)・
  lines_color・count_channels)。
- v11b 増分(shape 拡張で救済): region 計測(contlength/area_holes/height_width_ratio/moments_region_2nd/_2nd_invar)・
  cooc_feature_matrix(Haralick)・equ_histo_image_rect(局所equalize)・simulate_motion(方向ブラー)・
  projective_trans_image/_size/_region・polar_trans_image_inv・fft_image_inv・add_noise_white。
- **★将来利用インターフェース(`imgevolve.py` CLI)**: `has`/`ops`/`apply`/`pipeline`/`coverage`/`index`。
  `docs/OP_INDEX.json` = 全 369 op の機械可読索引。使い方 = README + memory `reference_imgevolve_usage`。
- **★GitHub push 済(2026-08-12 ユーザー許可)= github.com/furuse-kazufumi/imgevolve(private)**。公開(public 化)・
  PyPI・fullseye 物理リネームは別途 human-gate(公開時)。

## HALCON ~2313 の実装可能性(章別内訳, honest)
- **アルゴリズム系 808**(Filters/Morphology/Regions/Segmentation/XLD/Image/Transformations/
  Metrology/Inspection…)= imgevolve の対象。cv2/skimage/scipy backend wrap で大規模実装可。
- **インフラ系 776**(Graphics/Tuple/System/File/Control/Develop/Matrix/Legacy)= HDevelop 言語・
  システム関数 = **アルゴリズム設計エンジンの対象外**(stub は自明だが実装は無意味)。
- **モデル/専有 622**(Deep Learning/OCR/Classification/Calibration/3D)= 学習済モデル・HALCON 専有 =
  部分的(汎用版は可、parity 不可)。
- → 「全 stub scaffold」= 生成可能。「全実装」= 不要。現実解 = **アルゴリズム系 808 を graph 駆動で
  backend wrap**(被覆 79→数百)。

## 次(graph エンジニアリングでスケール)
1. ~~オペレータ知識グラフを構築~~ **DONE**(`graph.py` → `data/halcon_graph.json`, 2313ノード)。
2. ~~analog edge から backend-wrapped registry を自動生成~~ **DONE**(`backends_auto.py` 固定 shape
   語彙 + fail-closed 生成 + 8-agent fan-out + 機能ゲート = auto 173 op / 被覆 79→186)。
3. **残る未被覆 unary algorithm = 366**(graph の `unary_uncovered_by_chapter`)。次の増分候補:
   - **語彙の拡張**で救える families(現状 skip されたが genuine 実装可能): motion/defocus 方向ブラー
     (linear blur kernel)、gray_skeleton(gray 版 thinning)、shock_filter(PDE 先鋭化)、
     projective_trans(射影変換 shape)、inverse FFT(fft_image_inv/polar_inv)、corner→point sort
     (Foerstner/Harris の点出力に新 sort)、cooc/Haralick テクスチャ特徴、moment features
     (region moments)。**shape を1つ足すと該当 op 群が一気に被覆に入る**設計。
   - **n-ary tier の拡張**(現17→): 画像演算の残り(min/max_image は済、`gen_*`除く算術)、
     region 集合の union1/複数入力、channel 合成(多チャネル対応が要件)。
4. 各 families を sweep で seed/世代積み各タスクの勝ちを確定。C runtime を median/bilateral/morph/fft へ拡張。
5. **honest 規律**: 新規 op は必ず (a) halcon 名を実 reference で実在検証(fail-closed)、
   (b) 機能ゲート通過(例外なく宣言 sort)、(c) shape が HALCON op の記述と materially 同一 —
   でなければ skip。被覆数は `honest_summary.py` の実測のみを正本とする(推測で語らない)。

## 自走のしかた(work-graph)
```powershell
cd C:\dev\projects\imgevolve
py -3.11 halcon_scrape.py --version 2605                 # 実リファレンス取得(最新)
py -3.11 halcon_scrape.py --op-sets --versions 12,13,2311,2411,2505,2605   # 版横断スナップショット
py -3.11 halcon_coverage.py                              # 被覆計測 → docs/HALCON_COVERAGE.md
py -3.11 sweep.py --round N                              # 進化を投入(seed 変えて別軌道)
```

## honest 限界
- 被覆 3.4% は正直な現在地(memory 推測でなく実測)。インフラ系 776 は意図的に非対象。
- OCR/DL/3D/matching は重い依存 or 専有アルゴリズムで parity 困難(汎用近似のみ)。
- 型シグネチャは `mvtec-halcon` バインディング由来(ライセンスは MVTec、ローカル参照のみ・非 vendor)。
- C は image op のみ emit(gcc 未導入環境)。compile 差分検証は toolchain 到着で自動充足。
