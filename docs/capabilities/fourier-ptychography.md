---
id: fourier-ptychography
title: フーリエ・タイコグラフィ(LED の斜め照明の像の組 → 位相回復で高 NA の振幅と位相、収束しなければ拒否)
title_en: Fourier ptychography (oblique LED illumination, phase retrieval to a high-NA amplitude and phase, refused unless it converges)
category: 測る
ops: [fp_design, fp_usaf_target, fp_capture, fp_stack_from_images, fp_reconstruct, fp_element_contrast]
examples: [poc_fourier_ptychography]
version: 0.8.1
inputs: [volume, signal, image2d]
pipeline: [fp_design, fp_stack_from_images, fp_reconstruct, fp_element_contrast]
alternatives: [fp_capture, fp_usaf_target, coherent_image]
limits: 薄い試料・スカラ回折・単色・平面波の照明(LED の大きさと帯域は無い)。照明の k は格子に丸める。隣り合う瞳の重なりが 35 % を割ると拒否されやすく、明視野と暗視野の境に乗る LED は失敗の元。散乱の弱い物体や LED の位置を補正した復元では、重なりが十分でも 2 本の初期値の位相が一致せず拒否されることがある。
calibration: 照明の方向余弦(LED の位置・距離・スライドガラスの屈折)と、カメラの画素の物体側の大きさ(倍率)。符号の規約は USAF チャートで確かめる(k の符号を反転すると位相の符号だけが反転した像になり、強度だけでは区別できない)。
---

# フーリエ・タイコグラフィ(LED の斜め照明の像の組 → 位相回復で高 NA の振幅と位相、収束しなければ拒否)

## できること

低倍率の対物は視野が広いが分解能が低く、高倍率は逆になります。フーリエ・タイコグラフィ(FP)は LED アレイで照明の角度を変えながら低倍率で何枚も撮り、周波数空間で各像の受け持つ円(瞳)をつなぎ合わせて、**視野は低倍率のまま、分解能は合成 NA = NA_obj + NA_ill まで**上げます。強度しか撮らないのに位相も戻ります。戻すのは反復の位相回復(収束型の演算)なので、`fp_reconstruct` は収束の履歴・止めた理由・合成 NA を返し、収束しなければ拒否します。

`fp_design` は撮る前の閉形式です: 合成 NA、コヒーレントの遮断周期 λ/NA_syn、隣り合う瞳の重なり率(2 円の交わりの面積 / 円の面積、公表の下限 35 %)、必要な LED の数、カメラの画素の標本化(Δx ≤ λ/(2 NA_obj))、明視野と暗視野の境に乗る LED の数。`fp_capture` は複素物体を傾いた平面波で照らして瞳に通し、LED の明るさの落ち・暗視野の露光・雑音・瞳の収差・LED アレイのずれまで入れた像の組を作ります。装置や公開データの像は `fp_stack_from_images` で入ります。`fp_usaf_target` と `fp_element_contrast` は、USAF 1951 チャートの真値と、要素ごとの 3 本の棒の変調の読み取りです。

収束の判定は 2 つです。(1) 振幅の残差の改善が 10 回で 1 % 未満になったこと(停留)。(2) 初期値の違う 2 本(明視野の像の拡大 / 一様)が同じ像に着いたこと(一意性)。残差だけでは重なりの不足を見抜けません —— 重なり 18 % の残差は 64 % より小さい(拘束が少ない分、雑音まで合わせ込む)。

## What it does

Six ops in `fourierptycho` for Fourier ptychographic microscopy: closed-form design numbers before measuring (synthetic NA, coherent cut-off period, overlap ratio of neighbouring pupils against the published 35 % minimum, LED count, camera sampling Δx ≤ λ/(2 NA_obj) and LEDs sitting on the bright-/dark-field boundary), a simulator of the image set under oblique LED illumination (LED fall-off, dark-field exposure, shot and read noise, pupil aberrations, LED array misalignment, reflective height to round-trip phase), an entry point for measured image sets, a sequential phase retrieval with joint pupil recovery (EPRY form, projected on low-order polynomials by default) and LED position correction, and a USAF 1951 target with an element-by-element read-out. The reconstruction returns its convergence history, the reason it stopped and the synthetic NA, and refuses (raises a MetricContractError carrying the record) unless the residual has stalled and two different starting points agree.

## 向くところ / 向かないところ

**向く**: 広い視野のまま細かい構造を見たい明視野の検査(ウェハ・微細パターン・細胞の透明な試料)。位相の物体(透明な膜・段差)の定量。撮る前の構成の見積り(LED の距離と枚数、重なり、境の LED、カメラの画素)。

**向かない**: 厚い試料(多重散乱・3 次元の構造)、蛍光(インコヒーレント)、動く物体(撮る枚数が多い)。LED の大きさ・帯域による部分コヒーレンスは模型に入っていません。散乱の弱い物体の高い周波数は、k を格子に丸めた模型の誤差に埋もれます。

## 推奨パイプライン

`fp_design` → `fp_stack_from_images` → `fp_reconstruct` → `fp_element_contrast`

`fp_design` で重なり ≥ 35 %・R_cam ≥ 1・境の LED 0 枚・欲しい合成 NA を満たす構成を先に決める → 撮った像の組と照明の方向余弦を `fp_stack_from_images` で表にする(暗視野の露光の比は `exposure`)→ `fp_reconstruct`(実データでは `intensity_correction=True`、瞳は `pupil_degree=None` で画素ごとに自由に推定)→ USAF チャートで `fp_element_contrast` を読み、合成 NA の閉形式と突き合わせる。

## 代替

真値のある合成なら `fp_usaf_target` → `fp_capture`。1 枚のコヒーレント像なら `coherent_image`。2 枚の像の平行移動は `phase_correlation_fft`(復元の 2 本の比較もこれを使う)。

## 限界

- 照明の k は格子に丸める。真の物体でも残差は雑音の床まで下がらない(有限の視野・瞳の縁の離散化・k の丸め)。
- 逐次型は雑音のある像では厳密な不動点を持たない(1 周ごとの物体の変化が 0.1〜0.4 % で止まらない)。停止は「残差の改善が 10 回で 1 % 未満」。
- 画素ごとに自由な瞳(原論文の EPRY)は合成では雑音を吸って停留しない。既定は 2〜4 次の多項式へ射影。実データでは自由な瞳が要った(射影すると残差 2.3 倍)。
- 一意性の門(2 本の初期値の差 ≤ 0.08)は物体に依存する。重なりの境(32〜43 %)はこの PoC のチャートと雑音での実測。
- 収差を推定しない復元も、2 本が同じ誤った像に着けば「収束」する —— 収束の門は収差の取り違えを見抜かない。
- 照明装置と瞳の同時推定には特許がある。式は汎用に書き、装置の構成は模倣しない。

## 実寸校正

合成 NA は照明の方向余弦の最大で決まる —— LED の位置・距離(スライドガラスの屈折も)を測っておく。高解像の画素は低解像の画素 / 上げ倍率。軸に沿った棒の分解は x・y の方向余弦の最大(`na_synthetic_axis`)で決まり、対角の LED は効かない。

## 最初の 1 本

```python
import fourierptycho as FP

d = FP.fp_design(na_obj=0.1, wavelength_um=0.532, led_pitch_mm=4.0, led_distance_mm=70.0, n_side=13,
                 magnification=4.0, camera_pixel_um=5.2)
print(round(d["na_synthetic"], 3), round(d["overlap_ratio_centre"], 3))       # 0.424 0.642

t = FP.fp_usaf_target(groups=(8, 9), elements=(1, 2, 3), shape=(128, 128))
st = FP.fp_capture(t["amplitude"], 0.5 * t["coverage"], n_side=5)
rec = FP.fp_reconstruct(st)                                                     # 収束しなければ FPNotConvergedError
print(rec["converged"], rec["reason"].split(":")[0], round(rec["na_synthetic_axis"], 3))  # True stalled 0.214
```

走らせて見るなら `py -3.11 examples/poc_fourier_ptychography.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
