---
id: pixel-shift-imaging
title: ピクセルシフト撮像(1 画素シフトで全色、半画素シフトで折り返しを消す、壊れる条件まで)
title_en: Pixel-shift imaging (full colour from 1-pixel shifts, no aliasing from half-pixel shifts, and where it breaks)
category: 光と色
ops: [pixel_shift_pattern, pixel_shift_capture, pixel_shift_merge, pixel_shift_motion_mask, false_color_metric, pixel_shift_resolution_budget]
examples: [poc_pixel_shift]
version: 0.6.1
inputs: [rgbimage]
pipeline: [pixel_shift_resolution_budget, pixel_shift_pattern, pixel_shift_capture, pixel_shift_motion_mask, pixel_shift_merge, false_color_metric]
alternatives: [drizzle_resample, align_frames, raw_demosaic_bilinear]
limits: 合わせる側は公称のシフトが 1/scale 画素の格子に乗る場合専用。傾いたエッジの MTF50 は 1 枚でもシフトしても同じで(開口の sinc は動かない)、レンズが先に落ちていれば何も戻らない(PoC)。撮る側は理想の撮像素子で、雑音は呼び手が足す。
calibration: 実寸は 1 枚撮りと同じ画素ピッチ ÷ 倍率。半画素シフトで合わせた 2 倍の格子では 1 画素がその半分になる。シフトそのものは公称で合わせるので、圧電の誤差は `pixel_shift_pattern(error_px=…)` で見積もる。
---

# ピクセルシフト撮像(1 画素シフトで全色、半画素シフトで折り返しを消す、壊れる条件まで)

## できること

撮像素子を圧電アクチュエータで 1 画素 / 半画素ずつ動かして複数枚撮り、格子へ合わせる撮り方を、撮る側と合わせる側の両方で再現します。`pixelshift` の 6 本は `opsoptics` の族 `pixelshift` です。

`pixel_shift_pattern` は公称のシフト列(1 画素 4 枚・半画素 4 枚・16 枚)にアクチュエータの誤差を足し、`pixel_shift_capture` は細かく描いたシーンをシフトした画素の開口(箱、開口率つき)で厳密に積分して Bayer か白黒の生の画像を返します(枚ごとに違うシーン = 動く被写体も撮れる)。`pixel_shift_merge` は**公称の**シフトで格子へ振り分けて平均するだけで補間しません(1 画素 4 枚 = 各画素に R・G・B、半画素 = 2 倍の格子)。格子を埋められないシフト列は拒否します。動く被写体には `pixel_shift_motion_mask`(同じ点に入った 2 つの G の食い違い)で動いた所を見つけ、そこだけ 1 枚のデモザイク(`gfx2d.raw_demosaic_bilinear`)に差し戻せます。測る側は `false_color_metric`(Cb・Cr の大きさ)と `pixel_shift_resolution_budget`(画素の開口の sinc × 回折の MTF、ナイキスト、Q = λN/p、レンズ律速か画素律速か)です。

PoC `poc_pixel_shift` は、基板の配線・織物・網点・解像チャートで偽色が消えること、半画素シフトで縞の山が折り返し 1 − f₀ から本当の f₀ へ戻ること、★傾いたエッジの MTF50 は 1 枚でもシフトしても同じ(開口の sinc は動かない)こと、レンズが先に落ちていれば何も戻らないこと、シフトの誤差・動く被写体・枚数を重ねたときの雑音と破綻を、閉形式と既存の op(drizzle・edgesfr・optics の Airy)で採点します。

## What it does

Six ops in `pixelshift` (category `pixelshift` of `opsoptics`): nominal shift sequences with actuator error, an exact box-aperture capture of a finely drawn scene through a shifted Bayer or monochrome sensor (optionally a different scene per frame for moving objects), a grid merge with the nominal shifts that refuses sequences that cannot fill the grid, a motion mask from disagreeing green samples with fallback to a single-frame demosaic, a false-colour metric, and the closed-form resolution budget (pixel-aperture sinc times diffraction MTF, Nyquist, Q = λN/p). The PoC shows false colour vanishing with 1-pixel shifts, aliasing vanishing with half-pixel shifts while the slanted-edge MTF50 stays put, the lens-limited regime where nothing is gained, and the failure modes: shift error, moving parts and stacking more frames.

## 向くところ / 向かないところ

**向く**: 色の正しさが要る検査(基板・印刷・織物・塗装の色むら)でピクセルシフト機能を使うかの判断、レンズの F 値と画素の組み合わせでシフトに意味があるか(Q = λN/p)の見積り、シフト誤差の許容(圧電の精度)と搬送速度の上限の見積り、実機の連写を合わせるときの合成器。

**向かない**: ★合わせる側は公称のシフトが 1/scale 画素の格子に乗る場合専用です(任意のずれは `astrostack.drizzle_resample`、手持ちの揺れのように位置合わせが要る場合は `astrostack.align_frames` が先)。drizzle の `shifts` は「フレームの中身のずれ」なのでセンサのシフトとは**符号が逆**です(PoC の門で確認)。撮る側は理想の撮像素子(箱の開口・画素間のクロストークなし・3 色が完全に分かれる色フィルタ)で、雑音は呼び手が足します。動き検出の差し戻し先は 1 枚の双線形デモザイクなので、ゆっくりした動き(PoC では 0.25 px/枚)では差し戻すほうが誤差が大きくなります。

## 推奨パイプライン

`pixel_shift_resolution_budget` → `pixel_shift_pattern` → `pixel_shift_capture` → `pixel_shift_motion_mask` → `pixel_shift_merge` → `false_color_metric`

`pixel_shift_resolution_budget` で画素ピッチと F 値から Q = λN/p とレンズ律速か画素律速かを見て(画素律速でなければシフトの意味は薄い)→ `pixel_shift_pattern` で公称のシフト列(1 画素 4 枚・半画素 4 枚・16 枚)→ 実機ではその連写、試すなら `pixel_shift_capture` で細かく描いたシーン(`rgbimage`)を撮る → `pixel_shift_motion_mask` で動いた所を見つけ → `pixel_shift_merge` で公称のシフトで格子へ振り分け → `false_color_metric` で偽色を測る。

## 代替

任意のずれ(格子に乗らない)は `drizzle_resample`、手持ちの揺れのように位置合わせが要る場合は `align_frames` が先(drizzle の `shifts` はフレームの中身のずれなので、センサのシフトとは符号が逆 —— PoC の門で確認)。動いた所の差し戻し先は 1 枚の `raw_demosaic_bilinear`。

## 限界

- MTF は上がらない: 傾いたエッジの MTF50 は 1 枚とシフトで同じ(開口の sinc は動かない)、レンズが先に落ちていれば何も戻らない(PoC の門)。
- 撮る側は理想の撮像素子(箱の開口・画素間のクロストークなし・3 色が完全に分かれる色フィルタ)で、雑音は呼び手が足す。
- 動き検出の差し戻し先は 1 枚の双線形デモザイクなので、ゆっくりした動き(PoC では 0.25 px/枚)では差し戻すほうが誤差が大きくなる。

## 実寸校正

ピクセルシフトは尺度を変えない —— 1 画素 4 枚の合成は 1 枚撮りと同じ格子(画素ピッチ ÷ 倍率)、半画素の合成は 2 倍の格子なので 1 画素がその半分の長さになる。合わせる側はシフトを公称の値で扱い、実測しない。圧電の誤差の影響は `pixel_shift_pattern` の `error_px` で見積もる(最初の 1 本の例は 0.1 px)。

## 最初の 1 本

```python
import numpy as np
import pixelshift as P

F = 8                                                        # 1 センサ画素 = 8 × 8 標本
scene = np.random.default_rng(0).random((40 * F, 40 * F, 3))
nom = P.pixel_shift_pattern("4shot")                         # (0,0) (0,1) (1,1) (1,0)
raw = P.pixel_shift_capture(scene, F, P.pixel_shift_pattern("4shot", error_px=0.1), "RGGB")
rgb = P.pixel_shift_merge(raw, nom, "RGGB")                  # 各画素に R・G・B(合わせるのは公称のシフトで)
print(P.pixel_shift_resolution_budget(3.45, 2.8)["regime"])  # pixel_limited(Q = 0.45)
```

走らせて見るなら `py -3.11 examples/poc_pixel_shift.py`(図は既定で `out/figures/poc_pixel_shift/`)。
