# imgevolve — status / plan (plan_ref)

**作業名 imgevolve**(公開名は衝突実測後に確定)。画像処理アルゴリズムを **設計する** AI。
**スケーラブルなオペレータ・レジストリ**を進化させ、holdout で正直にゲートし、多言語
(Python/C)コードに codegen する。目標は **HALCON 級のオペレータ網羅**。raptor work-graph 上で自走。

設計の正本: `C:/dev/tools/raptor/docs/design/imgevolve_s0s1_workgraph.md`

## 差別化(先行研究で確定, 2026-08-01)
AlphaEvolve(生ソース進化・Gemini・汎用)/ TransCoder(翻訳)/ Halide(schedule 探索・
アルゴリズムは人が書く)いずれも「アルゴリズム発見 × 型付き画像IR × 検証済み多言語codegen ×
オンデバイス × honest holdout」を全部は満たさない。Halide は C/GPU codegen の下敷きに流用可。

## 現在地(v3, commit 未記入・local・未push=human-gate)
- **スケーラブル・レジストリ**(`ops.py` の `REGISTRY`)。**op を1つ足すだけで進化も codegen も自動追従**(driver 変更不要)。
- **32 op / 9 カテゴリ**: smoothing(gaussian/mean/bilateral/unsharp) rank(median/min/max/percentile)
  morphology(erode/dilate/open/close/tophat/bothat/grad) edges(sobel/laplace/prewitt/roberts/dog)
  gray(gamma/invert/scale/equalize/sigmoid) segmentation(threshold/otsu/dyn_threshold)
  frequency(lowpass/highpass) texture(std)。各 op に HALCON アナログ名を付与。
- 3タスク: denoise(PSNR)/edge(F1)/binarize(IoU)。S2 codegen(IR→Python+C)+ difftest(honest gate)。
- **honest 結果**(op 拡張後): op 空間が広がると**乱択は劣化・進化は決定的勝利**。
  denoise 進化24.41 vs 乱択19.5(**+4.9dB**)/ edge 0.901 vs 0.72 / binarize 0.931 vs 0.72(**v2の負け→勝ちに反転**)。
  edge codegen の Python 照合は **diff 0.0(ビット一致)**。C は gcc 待ち(正直 skip)。

## HALCON 級への道(ロードマップ)
- **済**: filter/rank/morphology/edge/gray/threshold/frequency/texture ファミリの代表 32 op(全て Image→Image)。
- **次の型システム拡張(本命)**: HALCON は Image だけでなく **Region(領域)/ XLD(輪郭)/ Tuple(特徴)/ Model** を扱う。
  多ソート型付き DSL(Image/Region/Feature)へ広げると blob 解析・connection・select_shape・
  measure・matching(template/shape/correlation)・OCR/calibration まで射程に入る。genome は型整合の
  ある列/DAG に。**これが 2000 級オペレータへスケールする鍵**(現状は単一ソート=Image→Image)。
- **C ランタイム拡張**: 現状 8 op(gaussian/box/gamma/invert/scale/threshold/unsharp/sobel)。
  bilateral/median/morph/fft を足せば denoise/binarize も C 化。gcc 到着で compile+差分検証が自動で埋まる。

## 自走のしかた(work-graph)
```powershell
cd C:\dev\projects\imgevolve
py -3.11 sweep.py --round N            # imgevolve-rN-* を投入(seed 変えて別軌道)
cd C:\dev\tools\raptor
py -3.11 libexec/raptor-worklog serve --workers 1 --poll 5   # 自律実行(review だけ human-gated)
```
成果物 = `C:/dev/tools/raptor/out/worklog/imgevolve/`。進捗は read-only(実行中に run-once/reclaim 禁止)。

## honest 限界
- まだ Image→Image 単一ソート。regions/contours/matching/OCR は型システム拡張が前提(未着手)。
- C は emit のみ(この環境に gcc 無し)。compile 検証は toolchain 到着後に自動で埋まる。
- 進化の優位はタスク依存(誇張しない)。op を足すほど乱択が落ち進化が相対的に勝つ、という構造は確認済み。
