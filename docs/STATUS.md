# imgevolve — status / plan (plan_ref)

**作業名 imgevolve**(公開名は衝突実測後に確定)。画像処理アルゴリズムを **設計する** AI。
**スケーラブルなオペレータ・レジストリ**を進化させ、holdout で正直にゲートし、多言語
(Python/C)コードに codegen する。目標は **HALCON 級のオペレータ網羅**。raptor work-graph 上で自走。

設計の正本: `C:/dev/tools/raptor/docs/design/imgevolve_s0s1_workgraph.md`

## 差別化(先行研究で確定, 2026-08-01)
AlphaEvolve(生ソース進化・Gemini・汎用)/ TransCoder(翻訳)/ Halide(schedule 探索・
アルゴリズムは人が書く)いずれも「アルゴリズム発見 × 型付き画像IR × 検証済み多言語codegen ×
オンデバイス × honest holdout」を全部は満たさない。Halide は C/GPU codegen の下敷きに流用可。

## 現在地(v7=optional cv2/skimage backends + 論文provenance, commit 系列 e6587af→c4f2078→d6b5456→v4・local・未push=human-gate)
- **スケーラブル・レジストリ**(`ops.py` の `REGISTRY`)。**op を1つ足すだけで進化も codegen も catalog も自動追従**。
- **多ソート型システム(6 ソート)**: `image / region / feature / contour(XLD) / match / any`。**型整合のある進化**で
  HALCON 中核パターン **image →(segment)→ region →(morph/select)→ feature** と
  **image →(edges_sub_pix)→ contour →(select/smooth/fit_line)→ contour →(to_region/length)→ region/feature** と
  **image →(ncc_locate)→ match** を表現。
- **107 op**(pure core 67 + backend 40=skimage25/cv2 15、cv2/skimage 導入時に自動登録・IMGEVOLVE_NO_BACKENDS=1 で core のみ)。**16+ カテゴリ**: image(smoothing/rank/morphology/edges/gray/frequency/texture)+ segmentation(threshold/
  otsu/dyn_threshold/canny/local_max)+ region(reg_morph/fill_holes/select_largest/remove_small/dist_transform/
  boundary/convex)+ features(blob_count/area_frac/count_contours/total_length)+ contour(edges_sub_pix/select/
  smooth/fit_line/to_region)+ matching(ncc_locate)。
- **8タスク**: denoise/edge/binarize/count/locate/**locate_rot**(回転不変shape matching)/**classify**(OCR/決定基盤)/**barcode**(1D bar計数)。
- **cross-library catalog**(`catalog.py`→`docs/OPERATORS.md`): 各 op を HALCON/OpenCV/scikit-image/MATLAB の
  API にマップ。直接アナログ被覆 = opencv 56/67・skimage 59/67・matlab 57/67。
- S2 codegen(IR→Python+C)+ difftest(honest gate)。多ソートでも Python 照合 PASS(edge diff 0.0/count 4e-7)。
- **honest 結果**(多ソート seed0/25gen): count 大勝(0.938 vs hand 0.688)、binarize 勝ち(fill_holes 使用)、
  denoise 僅差勝ち、edge は 25gen で hand に負け(空間が広い=要 seed/世代)。乱択は大空間で劣化。

## HALCON/多ライブラリ級への道(ロードマップ)
- **済(v1-v6)**: image/region/feature/contour(XLD)/match の 6 ソート + 67 op(filter/rank/morphology/edge/gray/
  threshold/frequency/texture/region/features/contour/matching/geometry/classification/barcode)。cross-library catalog。
  8 タスク(denoise/edge/binarize/count/locate/locate_rot/classify/barcode)。多言語 codegen+difftest。
- **次**: shape-model の**スケール不変**化 + **実 OCR**(文字テンプレ集/学習)+ **calibration 解**(対応点→変換の最小二乗/solvePnP 相当)+
  **3D/stereo** ソート。これで HALCON ~2100 に接近。
- **多ライブラリ被覆拡大**: OpenCV ~2500 / skimage ~300。ファミリ単位で registry を拡張、analogs は catalog が自動追跡。
- **C ランタイム拡張**: 現状 image op 8 種。median/bilateral/morph/region/fft を足し、gcc 到着で compile+差分検証を自動充足。

## 研究provenance / backend
- `backends.py`: cv2/skimage を optional で wrap(sk_/cv_、例外安全)。**実装はエコシステム、差別化層(型IR進化+honest gate+多言語codegen)は自前**=数千オペレータへの現実解。
- `references.py`→`docs/REFERENCES.md`: 各 op を seminal paper(Otsu/Canny/ROF/Tomasi-Manduchi/Frangi/Steger…83/107)+ RAD image corpus を新op源に。
- cross-lib catalog: opencv 71/skimage 84/matlab 57 of 107。

## 自走のしかた(work-graph)
```powershell
cd C:\dev\projects\imgevolve
py -3.11 sweep.py --round N            # imgevolve-rN-* を投入(seed 変えて別軌道)
cd C:\dev\tools\raptor
py -3.11 libexec/raptor-worklog serve --workers 1 --poll 5   # 自律実行(review だけ human-gated)
```
成果物 = `C:/dev/tools/raptor/out/worklog/imgevolve/`。進捗は read-only(実行中に run-once/reclaim 禁止)。

## honest 限界
- OCR/barcode/matching は self-contained な最小実装(barcode=バー計数、classify=円形度、OCR は実文字認識未搭載)。実運用級は次段。
- C は image op のみ emit(この環境に gcc 無し)。compile 差分検証は toolchain 到着後に自動で埋まる。
- 進化の優位はタスク依存(誇張しない)。op 空間が広いほど乱択は劣化し進化が相対的に勝つ(要 seed/世代)。locate系/classify/barcode は perfect。
