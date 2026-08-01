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
1. **オペレータ知識グラフ**(node=2313 op {章, in/out sort, 型シグネチャ, backend-analog 候補}、
   edge=型合成 + ライブラリ analog)を構築 → 進化の探索空間 + 自動 codegen の土台。
2. グラフの analog edge から **アルゴリズム系 808 の backend-wrapped registry エントリを自動生成**
   (HALCON op → cv2/skimage/scipy 呼出 + 型シグネチャ)→ 被覆を段階的に引上げ。
3. 各families を sweep で seed/世代積み各タスクの勝ちを確定。C runtime を median/bilateral/morph/fft へ拡張。

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
