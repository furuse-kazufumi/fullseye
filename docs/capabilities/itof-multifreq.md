---
id: itof-multifreq
title: 間接 ToF(位相方式)の多周波アンラップと壊れ方(折り返し・多重反射・縁の混合・高調波・背景光)
title_en: Indirect time-of-flight (phase-based): multi-frequency unwrapping and how it breaks (wrapping, multipath, flying pixels, harmonics, ambient light)
category: 測る
ops: [itof_capture, itof_phase_amplitude, itof_noise_budget, itof_unwrap_multifreq, itof_unwrap_error_rate, itof_multipath_separate, itof_flying_pixel_mask, itof_wiggling_correct]
examples: [poc_itof_multifreq]
version: 0.6.1
inputs: [depth]
pipeline: [itof_noise_budget, itof_capture, itof_phase_amplitude, itof_unwrap_multifreq]
alternatives: [dtof_cube_simulate, dtof_cube_depth, tof_transport_depth, residue_crt]
limits: 場面の強さは Lambert と逆二乗だけ(鏡面・迷光・画素間のクロストークなし)。行列ペンシルは等間隔の周波数専用で、帯域の分解能 c/(2FΔf) より近い 2 経路は雑音があると分けられない。雑音の閉形式は SNR ≥ 3 の近似(PoC)。
calibration: 距離は周期 c/(2f) の剰余から出るので尺度は光速と周波数で決まる。実機では段の位相の符号と原点・系の遅延(距離のオフセット)・周波数の正確な値を較正する(オフセットは itof_wiggling_correct の較正の定数項)。
---

# 間接 ToF(位相方式)の多周波アンラップと壊れ方(折り返し・多重反射・縁の混合・高調波・背景光)

## できること

光を周波数 f で強度変調し、戻り光との相関を 4 段(K 段)の位相で測る間接 ToF を、生信号から距離まで通し、壊れるところまで再現します。`itof` の 8 本は `opsoptics` の族 `itof` です。

`itof_capture` は距離の図(と反射率・背景光・余分な経路)から周波数ごと K 段のバケットを作ります(ショット雑音・読み出し雑音、正弦か矩形の変調、画素の開口での平均 = フライングピクセル)。`itof_phase_amplitude` は K 段から位相・振幅・オフセットと画素ごとの距離の雑音の見積もりを出し(段の位相が等間隔でなくても既知なら最小二乗)、`itof_noise_budget` は σ_d = c/(4πf)·√((B+σ_r²)/2)/A の閉形式です。`itof_unwrap_multifreq` は複数周波数の剰余を、次数の仮説を全部試す最尤の復号・`residue.residue_crt`・2 周波のうなりで距離にし、`itof_unwrap_error_rate` は次数を誤る確率の上界を出します。壊れ方の側は `itof_multipath_separate`(等間隔の多周波の行列ペンシルで 2 経路を分ける)、`itof_flying_pixel_mask`、`itof_wiggling_correct`(矩形波の周期誤差を模型の逆引きか較正の当てはめで補正)です。

PoC `poc_itof_multifreq` は、雑音の閉形式、倉庫の通路の 3 周波のアンラップと遠くで次数を誤る割合、80/100/120 MHz の組で 7.5 m より奥が折り返して映ること、包装フィルムと箱の 2 経路、部屋の隅の距離の伸び(`lighttransport` の輸送行列と一致)、箱の縁のフライングピクセル、矩形波の周期誤差、太陽光を、閉形式と既存の op で採点し、同じ場面を直接 ToF(`photoncount`)で撮って壊れ方を比べます。公開の実機の生データ(3 周波 × 3 段、CC BY 4.0)が手元にあれば、それを通して真値と突き合わせる章も走ります。

## What it does

Eight ops in `itof` (category `itof` of `opsoptics`) take continuous-wave indirect time of flight from raw phase-step buckets to depth and into its failure modes: a capture model with shot and read noise, sine or square modulation, extra light paths and pixel-aperture mixing; K-step phase, amplitude and offset with a per-pixel noise estimate; the closed-form depth noise; multi-frequency unwrapping by exhaustive maximum-likelihood hypotheses, by `residue.residue_crt` or by the two-frequency beat, plus an upper bound on the wrong-order probability; two-path separation from equally spaced frequencies (matrix pencil); a flying-pixel mask; and correction of the square-wave cyclic error. The PoC scores noise, unwrapping, aliasing beyond the unambiguous range, a translucent film over a box, a room corner (matching `lighttransport`), flying pixels, the cyclic error and sunlight against closed forms and existing ops, compares the same scene with direct ToF from `photoncount`, and, when the public raw multi-frequency data (CC BY 4.0) is present, checks the unwrapping against its ground truth.

## 向くところ / 向かないところ

**向く**: 位相方式の 3 次元カメラの周波数の組を決める前の見積もり(非曖昧距離 c/(2·gcd f)、距離の雑音、遠くで次数を誤る割合)、背景光の下での使える距離の見積もり、実機の生のバケットからの距離の復元と次数の信頼度(margin)による画素の選別、半透明物・凹んだ部品・段差の縁で距離がどうずれるかの説明。

**向かない**: 3 次元の場面の相互反射の描画(部屋の隅は 2 次元の断面だけ、`lighttransport`)。鏡面の多重反射。拡散した(連続した)多重反射の除去 —— `itof_multipath_separate` は経路が少数(既定 2 本)のときの分離で、隅のような連続した遅れには模型が合わない。直接 ToF の光子の数え方は `photoncount`。

## 推奨パイプライン

`itof_noise_budget` → `itof_capture` → `itof_phase_amplitude` → `itof_unwrap_multifreq`

`itof_noise_budget` で信号・背景光・読み出し雑音から周波数ごとの σ_d と非曖昧距離を見て周波数の組を選び(`itof_unwrap_error_rate` で次数を誤る確率も)→ 実機ではその生のバケット、試すなら `itof_capture` で距離の図(`depth`)を撮る → `itof_phase_amplitude` で位相と振幅 → `itof_unwrap_multifreq` で距離(margin の小さい画素は捨てる)。その後に `itof_flying_pixel_mask` で縁の浮いた画素を落とし、矩形に近い変調なら `itof_wiggling_correct` で周期誤差を補正する。

## 代替

直接 ToF(光子の到達時刻のヒストグラム)は `dtof_cube_simulate` → `dtof_cube_depth`(2 つの面の山を別々に見るので、縁が宙に浮かずフィルムの奥もずれない —— PoC で比較)。凹んだ形の相互反射による距離の偏りは `tof_transport_depth`。剰余の組み合わせそのものは `residue_crt`(★Wang–Xia の錨の選び方 —— 雑音の分散が最小の帯、同分散なら円上の最小二乗に最も近い剰余 —— で錨を選ぶので、位相雑音が帯ごとに同じ iToF でも最尤の復号と同等: 合成 0.1161 対 0.1160、実データ 0.131 対 0.131。以前の、常に最も長い周期を錨にする実装は 0.556 / 0.293 と大きく誤っていた。保証の外の画素では ResidueBoundWarning を出す)。

## 限界

- 場面の強さは Lambert(cos)と逆二乗だけで、鏡面反射・レンズの迷光・画素間のクロストークは入れていない。
- 雑音の閉形式は小さい雑音の近似で、SNR = A/√(B+σ_r²) が 3 を切ると実測が大きくなる(PoC で SNR 2.3 のとき 8 %)。
- `itof_multipath_separate` は等間隔の周波数専用で、帯域の分解能 c/(2FΔf) より近い 2 経路は雑音があると分けられない(PoC: 20〜160 MHz の 8 周波で、間隔 0.2 m 以下は 3 % 以下)。
- `itof_flying_pixel_mask` は両側が平らな台地の段差の縁を拾う判定で、幅 1〜2 画素の細い物は拾えない。雑音の大きい所は `depth_sigma` を渡さないと斜面と取り違える。

## 実寸校正

距離は周期 c/(2f) の剰余から出るので、尺度は光速と変調周波数で決まり、画素の大きさや倍率は関わらない。実機で要るのは、段の位相の符号と原点(間違えると c/(2f) − d に裏返る)、系の遅延による距離のオフセット(`itof_wiggling_correct` の較正の定数項)、周波数の正確な値(非曖昧距離と次数は周波数の比で決まる)。距離の図を点群にするなら、視線の方向(カメラの内部パラメータ)で距離を z に直す —— iToF が測るのは視線に沿った距離。

## 最初の 1 本

```python
import numpy as np
import itof

d = np.random.default_rng(0).uniform(0.5, 18.0, (64, 64))          # 真の距離 [m]
raw = itof.itof_capture(d, frequencies_hz=(16e6, 80e6, 120e6), signal_electrons=4000.0, read_noise_e=5.0)
pa = itof.itof_phase_amplitude(raw)                                 # 位相・振幅・距離の雑音の見積もり
un = itof.itof_unwrap_multifreq(pa)                                 # 最尤の復号(18.7 m まで一意)
print(un["unambiguous_range"], np.mean(np.abs(un["depth"] - d) > 0.3))
print(itof.itof_noise_budget(120e6, 4000.0)["depth_sigma"])         # 120 MHz 単独の σ_d [m]
```

走らせて見るなら `py -3.11 examples/poc_itof_multifreq.py`(図は既定で `out/figures/poc_itof_multifreq/`)。
