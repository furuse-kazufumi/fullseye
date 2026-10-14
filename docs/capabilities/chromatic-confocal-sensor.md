---
id: chromatic-confocal-sensor
title: クロマティック共焦点変位センサ(硝材の分散 → 較正表 → 戻りスペクトル → 高さ・厚さ)
title_en: Chromatic confocal displacement sensor (glass dispersion, calibration table, return spectrum, height and thickness)
category: 光と色
ops: [chromatic_confocal_probe, confocal_axial_response, chromatic_confocal_spectrum, chromatic_confocal_peaks, chromatic_confocal_readout, chromatic_confocal_limits]
examples: [poc_chromatic_confocal]
version: 0.6.1
inputs: []
pipeline: [chromatic_confocal_probe, chromatic_confocal_spectrum, chromatic_confocal_peaks, chromatic_confocal_readout]
alternatives: [confocal_axial_response, chromatic_confocal_limits]
limits: 層のあいだの干渉は入れない(反射を強度で足す)ので数 µm の薄膜のチャネルドスペクトルは再現しない。縦球面収差は 3 次の 1 項だけ。NA の補正式・金や粗さや光源のむらによる偏りの大きさ・薄膜の限界は模型の値。
calibration: 較正表は合成データで鏡を動かして作る(ピーク波長 → 高さ)。滑らかな推定の偏りはこの較正で消え、ビンの刻みの振れは残る。実機では実測の較正表に差し替える。
---

# クロマティック共焦点変位センサ(硝材の分散 → 較正表 → 戻りスペクトル → 高さ・厚さ)

## できること

白色光を軸上色収差の大きい対物レンズで集光すると、波長ごとに焦点の高さが変わります。面で反射してピンホールを通って分光器へ戻るのは面にピントの合った色だけなので、戻りスペクトルのピーク波長が高さになります(Molesini 1984)。`chromconf` の 6 本は、このセンサを**対物レンズの処方(`raytrace`)と硝材の分散(`materials`)から**組み立てます。観察対象(透明板・金属・Si)の反射率と屈折率も同じ材料表から引きます。

`chromatic_confocal_probe` は処方から波長ごとの近軸焦点・像側 NA・縦球面収差を求め、鏡を置いて応答のピークを読む較正を数値で再現した較正表(虹のものさしの目盛)を返します。`confocal_axial_response` は共焦点の軸応答(鏡面 sinc²(u/2)、点 sinc⁴(u/4)、縦球面収差つき)。`chromatic_confocal_spectrum` は面の位置と層構成から戻りスペクトルを合成します(Fresnel の反射率、往復の透過、傾き、粗さ、光源・分光器、雑音)。`chromatic_confocal_peaks` がピーク波長を拾い(白色参照で光源のむらを補正)、`chromatic_confocal_readout` が高さと透明板の厚さ(見かけの厚さ × n(λ)、NA の補正つき)に戻し、`chromatic_confocal_limits` が測定範囲・分解能・傾きの上限・最小膜厚を閉形式で出します。

PoC `poc_chromatic_confocal` は、焦点位置が厚肉レンズの閉形式と、軸応答の幅が 0.443 λ/(1 − cos α) と一致すること、色球面収差が較正のピークをずらすこと、推定法の偏りのうち滑らかな部分は「鏡を動かす較正」で消え、ビンの刻みで振れる部分は消えないこと、透明板の厚さが 4 材料で 0.1 % 以内に戻ること、金の面の偏りを反射率の傾き / 応答の曲率の閉形式が予言することを門にしています。

## What it does

Six ops in `chromconf` (category `confocal`): the probe calibration from a lens prescription and the glass dispersion of the material table (paraxial focus, image-side NA and longitudinal spherical aberration per wavelength, and the mirror-peak calibration), the confocal axial response (mirror and point, with spherical aberration), the return spectrum of a surface and a layer stack (Fresnel reflectance from the material table, tilt, roughness, source, spectrometer, noise), peak picking with white-reference correction, readout of heights and transparent-plate thickness with an NA correction, and closed-form limits (range, resolution, tilt, minimum film). Gates: thick-lens focus, sinc² width ∝ λ/NA², pupil-overlap Monte Carlo for tilt, plate thickness to 0.1 %, and the gold bias predicted by the reflectance slope over the response curvature.

## 向くところ / 向かないところ

**向く**: 対物レンズの硝材と NA の選定(範囲と分解能の両立)、透明体の厚さ計測の誤差の見積り(近軸の補正・n_d の取り違え・NA)、色のついた対象や光源のむらが読みに与える偏りの見積り、推定法の選択(雑音なしの偏りと雑音での再現性は順位が入れ替わる)。

**出典と模型の区別**: 範囲の式・軸応答の幅・傾きの上限・推定法の系統誤差・透明板に n と NA の両方が要ることは一次文献(Hillenbrand 2012、Corle 1986、Chen 2018 / 2019、Choi 2020)で確かめてあります。NA の補正式、金・粗さ・光源のむらによる偏りの大きさ、薄膜の限界は模型の値です。対応表は `chromconf` の docstring にあります。

**向かない**: ★層のあいだの干渉は入れていません(反射を強度で足す)。数 µm の薄膜で実物に出る干渉縞(チャネルドスペクトル)は再現しません。縦球面収差は 3 次の 1 項で、傾いた面の応答の非対称・スペックル・ファイバ結合のモード・横方向の分解能も扱いません。較正は合成データで鏡を動かして作るもので、実機では実測の較正に差し替えてください。

## 最初の 1 本

```python
import chromconf as C

P = C.chromatic_confocal_probe()          # 重フリントの非球面単レンズ(f 16 mm、NA 0.16)、450〜700 nm
print(round(P["range_um"]))                # 1191 —— 焦点が並ぶ長さ(測定範囲)

# ホウケイ酸クラウン 500 µm の板: 表と裏の 2 ピーク → 見かけの厚さ × n(λ)、NA の補正つき
s = C.chromatic_confocal_spectrum(P, 300.0, stack=((C.GLASS_CROWN, 500.0),), substrate=1.0)
r = C.chromatic_confocal_readout(C.chromatic_confocal_peaks(s), P, C.GLASS_CROWN)
print(round(r["thickness_um"], 1))         # 500.0(近軸の補正だけなら 498.8)
```

走らせて見るなら `py -3.11 examples/poc_chromatic_confocal.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。

## 推奨パイプライン

`chromatic_confocal_probe` → `chromatic_confocal_spectrum` → `chromatic_confocal_peaks` → `chromatic_confocal_readout`

対物レンズの処方と硝材から較正表を作り(`chromatic_confocal_probe`)→ 面の位置と層構成から戻りスペクトルを合成するか実測のスペクトルを持ち込み(`chromatic_confocal_spectrum`)→ ピーク波長を拾い(`chromatic_confocal_peaks`、白色参照で光源のむらを補正)→ 高さと透明板の厚さに戻す(`chromatic_confocal_readout`)。

## 代替

軸応答の形だけを見るなら `confocal_axial_response`。設計の段階で測定範囲・分解能・傾きの上限・最小膜厚だけが要るなら `chromatic_confocal_limits`(閉形式)。

## 限界

層のあいだの干渉は入れていない(反射を強度で足す)ので、数 µm の薄膜で実物に出るチャネルドスペクトルは再現しない。縦球面収差は 3 次の 1 項で、傾いた面の応答の非対称・スペックル・ファイバ結合のモード・横方向の分解能は扱わない。NA の補正式、金・粗さ・光源のむらによる偏りの大きさ、薄膜の限界は模型の値。

## 実寸校正

較正表は合成データで鏡を動かして作る(ピーク波長 → 高さ)。推定法の偏りのうち滑らかな部分はこの較正で消え、ビンの刻みで振れる部分は残る。実機では実測の較正表に差し替える。透明板の厚さには n(λ) と NA の両方が要る(n_d だけでは偏る)。

## 裏づけ

- op: `chromatic_confocal_probe`、`confocal_axial_response`、`chromatic_confocal_spectrum`、`chromatic_confocal_peaks`、`chromatic_confocal_readout`、`chromatic_confocal_limits`
- 例: [`poc_chromatic_confocal`](../../examples/poc_chromatic_confocal.py)
- 文献: Molesini 1984、Hillenbrand 2012、Corle 1986、Chen 2018 / 2019、Choi 2020(対応表は `chromconf` の docstring)
