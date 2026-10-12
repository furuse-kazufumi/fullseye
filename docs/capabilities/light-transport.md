---
id: light-transport
title: 凹みの相互反射で縞投影と ToF が外れる量を、撮る前に予測する(大域光輸送・直接と大域の分離・マイクロ位相シフト)
title_en: Predict how far interreflection in concave parts throws fringe projection and ToF off, before measuring (global light transport, direct/global separation, micro phase shifting)
category: 測る
ops: [groove_profile, form_factors_2d, transport_matrix_radiosity, high_frequency_patterns, render_transport, separate_direct_global, fringe_multipath_phase_error, predict_fringe_phase_error, micro_phase_decode, tof_multipath_phase, tof_transport_depth]
examples: [poc_interreflection_fringe_error]
version: 0.6.1
---

# 凹みの相互反射で縞投影と ToF が外れる量を、撮る前に予測する(大域光輸送・直接と大域の分離・マイクロ位相シフト)

## できること

縞投影(位相シフト)も ToF も、「画素に届く光は 1 つの経路から来た」と仮定して位相を距離に変えます。V 溝・加工ポケットの内角・はんだフィレット・部屋の隅のような凹んだ形では、片方の面で反射した光が向かいの面を照らし、画素には**別の場所の位相を持った光**が混ざります(相互反射 = 大域成分)。光沢も金属も要らず、**白い Lambert 面でも凹んでいれば起きます**。このページの op は、その光の行き来を輸送行列として明示的に解き、誤差を閉形式で予測します。

- ★**輸送行列**。凹んだ断面(押し出し形状)をパッチに分け、Hottel の crossed-strings 則で形態係数を閉形式で求め、Lambert のラジオシティ `T = (I − diag(ρ)F)^-1 diag(ρ)` を解きます。V 溝の板どうしの形態係数は閉形式 `1 − sin(θ/2)` と 5e-15、核 `cosθi cosθj / (2r)` の数値積分と 1.2e-14 で一致します。反射回数を打ち切った Neumann 和も出せます(反射 0 回 = 直接光だけの真値)。
- ★★**直接光と大域光の分離**(Nayar ら 2006)。溝に平行な 2 値の縞をずらして撮り、画素ごとの最大 `L_max` と最小 `L_min` から `L_d = L_max − L_min`、`L_g = 2 L_min`(点灯率 1/2)。点灯率 α・消灯の明るさ b・補のパターンの一般形もあります。白い 90° の V 溝で、周期を 128 → 8 px と細かくすると直接光の誤差は 12 % → 1.4 % に単調に減り、画素の足跡より細い 4 px では 53 % に崩れます(大域光が縞より滑らか、という前提の限界)。
- ★★**縞の位相の誤差の予測**。各画素の位相は「直接のフェーザ + 大域のフェーザ」の偏角で、誤差は `atan2(r sin Δ, 1 + r cos Δ)`、最悪 `asin(r)`(r = 大域 / 直接の振幅比)。輸送行列から画素ごとに予測した誤差は、描いた縞を `fringe.wrapped_phase` で復号した誤差と 1e-15 rad で一致します。幅 1 mm・深さ 0.5 mm の白い 90° の V 溝を視野 4 mm の縞 1 本で測ると、高さ誤差は RMS 282 µm。
- ★★**マイクロ位相シフト**(Gupta & Nayar 2012)。周期の近い高周波の縞の組(16 / 16.2 / 15.8 px)だけで測り、2 周波のうなりで次数を決めます。どの縞も細かいので相互反射は縞の位相を平均してしまい、同じ溝で RMS 0.76 µm(溝 3 本で 386 µm → 1.2 µm)。
- ★**ToF の多経路**。経路ごとのフェーザの和(閉形式)と、反射ごとの経路の遅れを入れた複素ラジオシティ。白い壁の部屋の隅(2-D のモデル、20 MHz)は、相互反射で隅が丸く・最大 24 cm 遠く見えます。

## What it does

Global light transport for concave Lambertian parts and its effect on active 3-D: an explicit light-transport matrix for an extruded concave cross-section (Hottel's crossed-strings form factors, checked against the V-groove closed form 1 − sin(θ/2) and against quadrature of the 2-D kernel to 1e-14; radiosity T = (I − diag(ρ)F)^-1 diag(ρ), or its Neumann partial sum by bounce count); shifted high-frequency patterns and the Nayar et al. (2006) L_max / L_min separation into direct and global images (general fill α, black level b, pattern-plus-complement); the fringe phase as the argument of the direct-plus-global phasor sum, predicted per pixel from the transport matrix and matching the phase decoded from rendered fringes by `fringe.wrapped_phase` to 1e-15 rad; a micro phase-shifting decoder (Gupta & Nayar 2012) that orders narrow-band high-frequency fringes by their beat; and AMCW time-of-flight multipath, both as a phasor sum and as complex radiosity with per-bounce path delay. On a white 1 mm, 0.5 mm deep 90° V-groove, one fringe across a 4 mm field misreads height by 282 µm RMS; the micro set brings it to 0.76 µm.

## 向くところ / 向かないところ

- **Lambert(完全拡散)と、溝の軸方向に無限に長い形(2-D)だけ**です。縞は溝に平行(市松のパターンは 2-D の問題にならないので `render_transport` が拒みます)。実物のはんだや金属の溝では**鏡面の相互反射**が支配的で、誤差はもっと大きく形も違います —— その真値には Mitsuba 3 の `gi_render.render_gi`(optional)が要り、ここでは扱っていません。
- 断面は z(x) の関数で下に凸(凹み)であること。凸の部分があると遮蔽が起きるので拒みます。プロジェクタから影になる面(三角測量の角が壁の傾きより大きい)も拒みます。
- 断面の両端の外は黒(反射しない)とみなします。V 溝の頂点のすぐ隣のパッチどうしは縞の位相が近く、どれだけ細かい縞でも平均されないので、マイクロ位相シフトでも頂点の数画素に誤差が残ります(この例では最大 19 µm)。
- マイクロ位相シフトは論文の F + 2 枚の同時解法と Gushov–Solodkin の位相接続ではなく、周波数ごとに N 枚で復号して 2 周波のうなりで次数を決めます。うなりの位相は雑音を 周期 / (周期の差) 倍に増やすので、雑音のある実機では周波数の組を選び直す必要があります。
- ToF の複素ラジオシティは 2-D(壁は上下に無限、光源はカメラ位置の線光源)のモデルで、遅延はパッチ中心間の距離で近似します(パッチが変調波長より十分小さいこと)。

## 最初の 1 本

```python
import numpy as np
import fringe
import fullseye as fs

groove = fs.ledger.groove_profile("vgroove", 120, angle_deg=90.0)         # 幅 1、深さ 0.5 の内角
T = fs.ledger.transport_matrix_radiosity(groove, 0.85)                   # 白い Lambert(反射率 0.85)
D = fs.ledger.transport_matrix_radiosity(groove, 0.85, n_bounces=0)      # 直接光だけ(真値)

stripes = fs.ledger.high_frequency_patterns((1, 240), 8)                 # 点灯率 1/2 の縞を 8 回ずらす
sep = fs.ledger.separate_direct_global(fs.ledger.render_transport(T, stripes))
truth = fs.ledger.render_transport(D, [np.ones((1, 240))])[0]
print("分離した直接光の誤差 %.1f %%" % (100 * np.abs(sep["direct"] - truth).mean() / truth.mean()))

fr = fs.ledger.high_frequency_patterns((1, 240), 240.0, kind="sinusoid")  # 視野に縞 1 本
d = fringe.wrapped_phase(fs.ledger.render_transport(T, fr)) - fringe.wrapped_phase(fs.ledger.render_transport(D, fr))
meas = np.angle(np.exp(1j * d))                                           # (-π, π] に戻す
pred = fs.ledger.predict_fringe_phase_error(T, 240.0, projector_width=240)
print("位相の誤差 最大 %.3f rad、予測との差 %.1e" % (np.abs(pred["bias"]).max(), np.abs(pred["bias"] - meas[0]).max()))
```

## 裏づけ

- op: `groove_profile` / `form_factors_2d` / `transport_matrix_radiosity` / `high_frequency_patterns` / `render_transport` / `separate_direct_global` / `fringe_multipath_phase_error` / `predict_fringe_phase_error` / `micro_phase_decode` / `tof_multipath_phase` / `tof_transport_depth`
- 例: [`poc_interreflection_fringe_error`](../../examples/poc_interreflection_fringe_error.py) —— 幅 1 mm の溝 3 本(90° の内角・60° の V 溝・R つきのポケット)を持つ白い部品: 分離した大域光は凹みの中だけが光り、内角の底では直接光の 1.28 倍。縞 1 本の高さ誤差 RMS 282 / 579 / 183 µm を予測と実測で重ね(差 1e-15 rad)、2 段の位相接続は 329 / 480 画素で次数を取り違えて救えず、マイクロ位相シフトで 0.76 / 1.97 / 0.02 µm。部屋の隅の ToF は最大 24 cm 遠く見える。
- 既存 op と組む: `fringe.wrapped_phase`(N ステップの復号、そのまま再利用)・`fringe.synthesize_fringes`(直接光だけの縞)・`photoncount`(dToF、単一経路)・`gi_render.render_gi`(鏡面の相互反射の外部真値、Mitsuba 3 が optional)
- 先行: S. K. Nayar, G. Krishnan, M. D. Grossberg, R. Raskar, *ACM Trans. Graphics* 25(3), 2006(§3.3 の式 (7)–(9) と §4 を本文で確認); M. Gupta, S. K. Nayar, "Micro Phase Shifting", CVPR 2012(式 (5)–(12) と §3 を本文で確認); 形態係数の crossed-strings 則(H. C. Hottel、教科書の標準形を閉形式と数値積分で照合)。
