---
id: tdi-linescan-and-lens
title: TDI ラインスキャンとラインスキャン用レンズ(段数と SNR → 同期ずれの MTF → 像高ごとの照度と MTF)
title_en: TDI line-scan cameras and line-scan lenses (stages and SNR, synchronisation MTF, illumination and MTF across the image height)
category: 光と色
ops: [tdi_snr, tdi_sync_mtf, linescan_acquire, lens_field_profile, linescan_lens_columns, linescan_lens_example]
examples: [poc_tdi_linescan]
version: 0.6.1
---

# TDI ラインスキャンとラインスキャン用レンズ(段数と SNR → 同期ずれの MTF → 像高ごとの照度と MTF)

## できること

フィルム・鋼板・ガラス・印刷物・ウェハのように流れてくるものはラインセンサで撮ります。暗いラインでは TDI(時間遅延積分)で N 段ぶん露光を積み、その代わりに搬送とラインレートの同期が画質を決めます。長いラインセンサ(8k × 7 µm = 57 mm など)は普通の C マウントレンズの像円に収まらないので、ラインスキャン用のレンズを使います。`linescan` の 6 本はこの 3 つを数で扱います。

`tdi_snr` は EMVA 1288 の線形雑音模型(式 21、`sensorchar.emva_snr_curve`)を段数倍した SNR で、電荷で足す方式(読み出しは 1 回)とデジタルで足す方式(読み出しと量子化も N 回)を分けます。`tdi_sync_mtf` は同期ずれ ε とヨー θ の閉形式で、N 段の間の掃引 N·|ε| 画素(流れ方向)と N·sin θ 画素(幅方向)の |sinc|。`linescan_acquire` は反射率の地図を搬送して撮る撮像で、速度誤差(一定でもライン周期ごとでも)、ヨー、蛇行、エンコーダ同期、レンズの列ごとの照度とぼけ、EMVA 1288 の雑音を入れます。`lens_field_profile` は `raytrace` の処方を有限距離の物体で光線追跡し、像高ごとの相対照度を cos⁴ × 瞳 × 歪曲の 3 因子に厳密に分け、幾何 MTF(サジタル / タンジェンシャル)と回折 MTF を返します。`linescan_lens_columns` はそれを画素列ごとの照度とぼけにし、`linescan_lens_example` は同じ形の三枚玉を 57 mm の像円用(f 90)と 2/3 型用(f 35、C マウントの流用)に最適化した 2 つの模型を返します。

PoC `poc_tdi_linescan` は、像から測った SNR が式 21 と 1.2 % 以内、同期ずれとヨーの MTF が |sinc| と 0.004 以内、エンコーダ同期で速度のうねりが消えること、C マウントの流用では像高 19.7 mm から光が届かず、フラットフィールド補正で照度は揃っても MTF と欠陥の CNR は戻らないことを採点します。

## What it does

Six ops in `linescan`: the SNR of an N-stage TDI sensor from the EMVA 1288 linear model (charge-domain and digital-domain summation), the closed-form MTF of a synchronisation error and of a yawed web, an acquisition that transports a reflectance map past a TDI line sensor (speed error, yaw, weave, encoder sync, per-column lens illumination and blur, EMVA 1288 noise), and a ray-traced profile of a finite-conjugate lens across the image height whose relative illumination splits exactly into cos⁴ × pupil × distortion, with sagittal and tangential MTF. Two example lenses (the same triplet optimised for a 57 mm line and for a 2/3-inch format) show why a C-mount lens on a long line sensor goes dark and soft at the ends, and that flat-field correction restores the brightness but not the MTF.

## 向くところ / 向かないところ

**向く**: TDI の段数と照明の見積り(何段あれば欠陥の CNR が足りるか)、エンコーダ同期の要否と許せる速度誤差、ヨーと蛇行の許容値、ラインセンサに付けるレンズの像円と像高ごとの照度・MTF の確認、シェーディング補正で直るものと直らないものの切り分け。

**向かない**: ★レンズの模型は実在の型番の処方ではありません(メーカーの処方は公開されていない)。数字を特定のレンズの性能として引用しないでください —— 処方があれば `raytrace.lens_system` で組んで `lens_field_profile` に渡します。ぼけは列ごとのガウス近似(MTF を 1 つの周波数で合わせる)で、コマのような非対称な PSF は対称になります。同期の模型は一定の ε とライン周期ごとの ε までで、電荷の送りの離散さ(全条件に共通の 1 画素の掃引)、CMOS TDI の画素内の時間ずれ、ベルトの滑りの統計は入れていません。無限遠の物体の照度は `optics.relative_illumination` / `lensimage` を使ってください(`lens_field_profile` は拒否します)。

## 最初の 1 本

```python
import linescan as L

# 1 段 20 光子、64 段(η 0.6、読み出し 12 e⁻、K 0.25 DN/e⁻): 電荷加算とデジタル加算の SNR
print(L.tdi_snr(20.0, [1, 64], 0.6, 12.0, 0.25)["snr"].round(2))                            # [ 0.96 25.41]
print(L.tdi_snr(20.0, [1, 64], 0.6, 12.0, 0.25, architecture="digital")["snr"].round(2))   # [0.96 7.65]

# 速度誤差 2 % で 64 段: 流れ方向の掃引と 0.25 c/px の MTF
m = L.tdi_sync_mtf([0.25], 64, 0.02)
print(round(m["smear_scan_px"], 2), round(float(m["mtf_scan"][0]), 3))     # 1.28 0.84

# ラインスキャン用レンズの模型: センサの端(28.7 mm)の照度
p = L.lens_field_profile(L.linescan_lens_example("linescan"), [0.0, 28.672])
print(round(float(p["relative_illumination"][1]), 3))                      # 0.976
```

走らせて見るなら `py -3.11 examples/poc_tdi_linescan.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
