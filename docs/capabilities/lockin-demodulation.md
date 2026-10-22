---
id: lockin-demodulation
title: 画素ごとの直交復調(ロックイン・時間相関イメージセンサ → 振幅・位相・直流、リング照明の法線・符号化照明の分離・熱波)
title_en: Per-pixel lock-in demodulation (time-correlation imaging: amplitude, phase and DC; ring-light normals, coded-light separation, thermal waves)
category: 測る
ops: [lockin_demodulate, lockin_amplitude, lockin_phase, lockin_noise_floor, lockin_walsh_codes, lockin_separate, lockin_ring_synthesize, lockin_ring_normals, lockin_thermal_wave]
examples: [poc_lockin_imaging]
version: 0.7.0
inputs: [image2d]
pipeline: [lockin_ring_synthesize, lockin_demodulate, lockin_ring_normals]
alternatives: [lockin_amplitude, lockin_phase, lockin_separate, lockin_walsh_codes, lockin_noise_floor, lockin_thermal_wave]
limits: 法線の復元は朗伯面で、輪の光源のどれも影にならない画素(傾き < 90° − 天頂角)だけ有効(他は NaN と valid = False)。光沢・相互反射では式が崩れる。熱波は定常状態の 1 次元モデル(横拡散と立ち上がりの過渡は無し)で、位相は L/μ = 1.963 で最大になるのでそれより深い欠陥は位相から一意に読めない。矩形窓は周期が整数のときだけ(そうでなければ拒否)。
calibration: 位相は参照の周波数と標本化の時刻(fps)だけで決まり、画素の大きさや照度の絶対値は要らない。振幅は照明・反射率・放射率の掛け算を含むので、反射率を消したいときは A / 直流(法線)か位相(熱波)を使う。参照の周波数が 10 % ずれると振幅が落ちる(sinc)ので、参照は実測の周波数に合わせる。
---

# 画素ごとの直交復調(ロックイン・時間相関イメージセンサ → 振幅・位相・直流、リング照明の法線・符号化照明の分離・熱波)

## できること

変調した光や熱で場面を照らし、画素ごとに参照信号と相関を取ると、画像でなく「参照に追従する成分の振幅と位相」と直流が出ます。`lockin` の 9 本は、画像列 (T, H, W) に対するその直交復調と 3 つの使い方です。`lockin_demodulate` は振幅・位相・直流・同相・直交と窓の漏れを返し(`lockin_amplitude` / `lockin_phase` は 2 次元の画像だけ)、窓は宣言します: 矩形窓は参照の周期が整数のときだけ厳密で、そうでなければ拒否し、hann なら漏れの大きさを表で返します。`lockin_noise_floor` は白色雑音の下の振幅・位相の雑音を SN 比から閉形式(位相は Rice の分布)で与えます。

(a) 多重極変調リング: `lockin_ring_synthesize` は輪の光源の位相を方位角と一緒に 1 周させた(双極子)ランバート面の像列を作り、`lockin_ring_normals` は復調した基本波の応答 (n_x − j n_y) と直流から反射率を消して法線と勾配を返します。(b) 符号化間歇照明: `lockin_walsh_codes` の直交な符号で断続する灯を、`lockin_separate` が昼間の光と分けて 1 灯ずつの像にします(ゆっくりした増加は列を足して吸収、ちらつきは残差に出る)。(c) ロックイン・サーモグラフィ: `lockin_thermal_wave` は周期加熱した板(欠陥は底の深さを変えた層)の表面温度の厳密解 coth(σL) を返し、位相から欠陥の深さを読めます(加熱ムラは位相に入らない)。

## What it does

Nine ops in `lockin` (category `lockin` of `opsoptics`): per-pixel quadrature demodulation of an image sequence against a sinusoidal reference, returning amplitude, phase, DC, in-phase, quadrature and the window leakage; the window is declared (rectangular only for a whole number of periods, otherwise refused; hann reports its leakage). Closed-form amplitude and phase noise from the SNR (Rice phase distribution), a multipole-modulated ring of sources on a Lambertian relief and the normals recovered from its first-harmonic response with the albedo cancelled, Walsh codes and a least-squares separation of coded lights from daylight, and the exact surface temperature of a periodically heated plate for lock-in thermography.

## 向くところ / 向かないところ

**向く**: 時間相関イメージセンサ・ロックインカメラ・ロックイン・サーモグラフィの試作と性能の見積り(雑音の下の位相の精度、参照のずれの許容、窓の選び方)、反射率の模様に邪魔されずに凹凸・傷・へこみを調べる照明の設計、昼間の光の下で符号化した灯だけを取り出す設計の下準備、熱波の位相から欠陥の深さを読む範囲の確認。

**向かない**: 法線の復元は朗伯面に限り、光沢面・相互反射・影のある急な傾きでは式が崩れる(影になる画素は無効にして法線を作らない)。サーモグラフィは定常状態の 1 次元モデルで、横方向の熱拡散と最初の数周期の過渡は入っていない。位相は L/μ = 1.963 で最大になり、それより深い欠陥は位相から一意に読めない。実機のセンサの変調帯域・画素ごとの参照信号の位相ずれ・飽和は模型に無い。

## 推奨パイプライン

`lockin_ring_synthesize` → `lockin_demodulate` → `lockin_ring_normals`

高さの図から輪の光源の像列を作り(実機なら撮った像列)→ `lockin_demodulate` で参照の周波数(1 周期あたりの枚数で決まる)に復調し → `lockin_ring_normals` に表と天頂角を渡して法線・勾配・有効画素を得る。

## 代替

振幅か位相の 2 次元の画像だけが要るなら `lockin_amplitude` / `lockin_phase`。昼間の光の下の灯の分離は `lockin_walsh_codes` → `lockin_separate`。雑音の下の精度の見積りは `lockin_noise_floor`。熱波は `lockin_thermal_wave` の像列を `lockin_demodulate` に渡して位相から深さを読む。

## 限界

- 法線の復元は朗伯面で、輪の光源のどれも影にならない画素だけ有効(A / 直流 < 1/2)。他は NaN と valid = False。
- サーモグラフィは定常状態の 1 次元モデル。位相の最大(L/μ = 1.963)より深い欠陥は一意に読めない。
- 矩形窓は参照の周期が整数のときだけ。周期が整数でない長さは拒否し、hann は漏れを表で返す(3.75 周期で振幅誤差 0.0156)。
- Walsh 符号はゆっくりした増加や参照と周波数の近いちらつきに直交でなく、その分は誤差になる(残差の画像で分かる。増加は列を足して吸収できる)。

## 実寸校正

位相は参照の周波数と標本化の時刻(fps)だけで決まり、画素の大きさや照度の絶対値は要りません。振幅は照明・反射率・放射率の掛け算を含むので、反射率を消したいときは A / 直流(法線)か位相(熱波)を使います。参照の周波数が実際の変調と 10 % ずれると振幅は sinc で落ちる(PoC で 0.90)ので、参照は実測の周波数に合わせます。

## 最初の 1 本

```python
import numpy as np
import lockin as LK

# 反射率に縞のある面に、へこみ。8 灯の輪(天頂角 25°)の光を 16 枚/周期 x 4 周期で撮った像列から法線を取る
yy, xx = np.mgrid[0:64, 0:64].astype(float)
height = -3.0 * np.exp(-((yy - 32) ** 2 + (xx - 32) ** 2) / 50.0)
albedo = 0.35 + 0.55 * (np.floor(xx / 6.0) % 2)
video = LK.lockin_ring_synthesize(height, 25.0, 8, 1, 16, 4, albedo=albedo)
demod = LK.lockin_demodulate(video, 1.0, 16.0)          # 参照 1 周期 = 16 枚
nrm = LK.lockin_ring_normals(demod, 25.0)
gy, gx = np.gradient(height)
print(round(float(np.abs(nrm["height_gradient_x"] - gx)[1:-1, 1:-1].max()), 12))   # 0.0(反射率の縞に依らず勾配が閉形式で出る)
```

走らせて見るなら `py -3.11 examples/poc_lockin_imaging.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
