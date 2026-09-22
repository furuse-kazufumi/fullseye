---
id: geodetic-frames
title: 地球規模の座標に載せる(ECEF・高さの基準・局所 ENU)
title_en: Put measurements on the Earth (ECEF, height frames, local ENU)
category: 測る
ops: [dem_geodetic_to_ecef, dem_ecef_to_geodetic, dem_geoid_height, dem_height_frame_convert, dem_height_frame_residual, dem_datum_shift_3param, dem_enu_from_geodetic, dem_geodetic_from_enu]
examples: [poc_geodetic_height_frames, poc_geodetic_benchmarks_real, dem_geodesy_tour]
version: 0.2.3
---

# 地球規模の座標に載せる(ECEF・高さの基準・局所 ENU)

## できること

緯度・経度・高さを、地球中心直交座標(ECEF)・局所 ENU・別の測地成果(datum)へ移します。**高さは 2 つある**(GNSS が返す楕円体高 h と、地図・設計図が使う標高 H)ので、どちらの基準の量なのかを op に書かせ、`h − H − N` の残差で取り違えを検出します。

実データでの確かめ(NOAA/NGS が公開する測量成果 523 点、コロラド州フロントレンジ。1 点につき h・H・ジオイド高 N・地心直交座標が全部公開されている):

- `dem_geodetic_to_ecef` は公開されている地心直交座標と **rms 0.5 mm・最大 0.8 mm** で一致。
- 0.25 度の GEOID18 格子を `dem_geoid_height` で補間した値と、同じ点の公開値の差は **rms 11.1 cm・最大 44.5 cm**(山地の縁なので勾配が大きい)。格子の外に落ちた 15 点は**端で埋めず拒否**します(外挿した undulation は測量値ではない)。
- 楕円体高をそのまま標高として使うと、残差は中央値 **16.75 m** ずれました。
- その残差は測量の等級を**言われないまま並べ替えます**: 水準測量 1.6 cm < 網調整 1.9 cm < GPS 観測 3.8 cm < VERTCON3(モデル換算)8.3 cm・最大 1.02 m。

往復の誤差の床(合成の 4000 点、緯度 ±85 度・高さ -500〜9000 m の最大値): ECEF が緯度 6.4e-12 度・高さ 8.5e-07 m、局所 ENU が緯経 1e-11 度・高さ 1e-06 m。

## What it does

Convert geodetic coordinates to Earth-centred Cartesian (ECEF), to a local ENU frame, and between datums; convert between the two kinds of height (ellipsoidal h from GNSS and orthometric H used by maps) through a published geoid grid, and measure the residual `h - H - N` that exposes a height-frame mix-up. Checked against 523 published NGS survey marks: ECEF agrees with the published Cartesian coordinates to 0.5 mm rms, bilinear interpolation of a 0.25-degree GEOID18 grid lands within 11.1 cm rms of the published point values, and using h as if it were H shifts the answer by 16.75 m (median) in that region.

## 向くところ / 向かないところ

**向く**: 測量成果・GNSS・広域の点群を 1 つの枠に載せる前処理。GNSS の楕円体高と地図の標高が混ざった表の**健全性検査**(残差を数えるだけで由来の悪い点が浮く)。

**向かない**: **epoch の移動(プレート運動)と 7 パラメータのヘルマート変換はまだありません**(`dem_datum_shift_3param` は平行移動 3 つだけで、回転と縮尺は扱いません —— 旧日本測地系のような大きなずれには足りますが、ITRF の実現どうしの cm 級には足りません)。ジオイドモデルそのものも計算しません(公開格子を**引く**だけです)。

## 最初の 1 本

```python
import fullseye as fs

h = [1651.543]                      # GNSS の楕円体高[m]
H = [1668.547]                      # 地図の標高[m]
N = [-17.024]                       # ジオイド高[m](公開格子から)

# 基準どおりなら残差はほぼ 0 —— 実在の測量点(NGS の KK1420)で 0.020 m
print(fs.ledger.dem_height_frame_residual(h, H, N)['rms_m'])

# 楕円体高をそのまま標高として使うと、残差が -N に張り付く(17 m の静かなずれ)
print(fs.ledger.dem_height_frame_residual(h, h, N)['median_m'])
```

## 裏づけ

- op: `dem_geodetic_to_ecef` / `dem_ecef_to_geodetic` / `dem_geoid_height` / `dem_height_frame_convert` / `dem_height_frame_residual` / `dem_datum_shift_3param` / `dem_enu_from_geodetic` / `dem_geodetic_from_enu`
- 例: [`poc_geodetic_height_frames`](../../examples/poc_geodetic_height_frames.py)(合成で伝播を量ごとに分ける)、[`poc_geodetic_benchmarks_real`](../../examples/poc_geodetic_benchmarks_real.py)(公開測量成果 523 点で答え合わせ)、[`dem_geodesy_tour`](../../examples/dem_geodesy_tour.py)
- 出所: NOAA/NGS datasheet API と GEOID18 の点照会(集計のみ同梱、生データは同梱しません)
