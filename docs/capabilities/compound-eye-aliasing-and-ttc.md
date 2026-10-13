---
id: compound-eye-aliasing-and-ttc
title: 周期パターンが標本化格子で折り返す距離と、縞の上で狂う衝突時間を閉形式で測る(複眼・検査カメラ)
title_en: The distance at which a periodic pattern aliases on a sampling lattice, and the time-to-contact that stripes corrupt — in closed form (compound eyes and inspection cameras)
category: 測る
ops: [sampling_alias_distance, fly_view_plane_texture, fly_expansion_readout, fly_vogel_lattice, lattice_moire_peak, traj_tau_dot, fly_t4t5_field, fly_tau_from_expansion]
examples: [poc_zebra_stripes_fly_eye]
version: 0.6.1
---

# 周期パターンが標本化格子で折り返す距離と、縞の上で狂う衝突時間を閉形式で測る(複眼・検査カメラ)

## できること

周期 P の縞を間隔 Δφ の格子で標本化すると、距離 d > P cos²θ/(√3 Δφ)(六角、正方は 2Δφ)で縞は折り返してモアレになります。`sampling_alias_distance` はこの距離と、ナイキストに残るコントラスト(MTF)を閉形式で返します —— Δφ を画素の瞬時視野、P を検査対象(ディスプレイ・メッシュ・織物・網点)のピッチと読めば、**検査カメラの作動距離の設計規則**です。`fly_view_plane_texture` は正面の周期面を六角個眼格子 + ガウス受容角の下で**解析的に**積分し(画像を再標本化しない)、`fly_t4t5_field(model="hr")` に渡すと相関型運動検出器(Hassenstein–Reichardt)の符号反転 sin(2πΔφ/λ) がどの個眼で起きるかを数えられます。`fly_expansion_readout` は眼全体の流れから衝突時間 τ を読み、縦縞のアパーチャ効果が放射当てはめ・発散とも**厳密に 2τ** を返すことを示します。`traj_tau_dot` は実測の 3-D 軌跡から距離・接近速度・τ・τ̇(Lee 1976)を出します。

フィボナッチの複眼 `fly_vogel_lattice`(Vogel 螺旋、同じ個眼数・同じ平均間隔)と `lattice_moire_peak`(非一様 DFT のピーク/背景中央値 = モアレの尖り)で、**格子の並びだけ**を変えたときに何が変わるかを比べられます: 六角は鋭いモアレ(尖り > 100)、螺旋は拡散(1/10 未満)、ナイキスト直下の解像は六角が最良、偽フローは格子でなく**対の間隔**で決まる。

## What it does

`sampling_alias_distance` gives the closed-form distance beyond which a period P aliases on a lattice of pitch Δφ (P cos²θ/(√3 Δφ) for hexagonal, 2Δφ for square) and the contrast left at Nyquist — the working-distance rule of an inspection camera once Δφ is read as the pixel IFOV. `fly_view_plane_texture` integrates a periodic frontal surface analytically under the hexagonal ommatidial lattice and a Gaussian acceptance function (no resampling); fed to the HR correlator it shows where the sign flips. `fly_expansion_readout` reads τ from the flow over the whole eye and shows the aperture effect of vertical stripes returns exactly 2τ. `traj_tau_dot` gives distance, closing speed, τ and τ̇ along a measured 3-D trajectory. `fly_vogel_lattice` and `lattice_moire_peak` compare a Fibonacci (Vogel-spiral) eye with the hexagonal one at the same count and mean spacing: sharp moire versus diffuse noise, best sub-Nyquist resolution for the hexagon, and false flow set by pair spacing rather than by lattice regularity.

## 向くところ / 向かないところ

**向く**: 周期構造(ディスプレイ・メッシュ・織物・網点・レール)を見る検査カメラの作動距離と画素ピッチの設計、周期構造の上を光流で着地・走行する機体(AGV・ドローン)の故障モードの見積もり、複眼・非一様標本化(Vogel 螺旋・ジッタ)の比較、実測軌跡の τ 解析。

**向かない**: ★正面の平面と等速接近の幾何だけです(`poc_zebra_stripes_fly_eye`)。縁を眼の中で見つける段、曲面・斜め接近、ハエの個体ごとの光学定数(アブの受容角は未発表値)は入っていません。★「縞で距離感が狂う」は閉形式の範囲では**縦縞のアパーチャ効果(2τ)と HR の符号反転**として出ますが、市松でも虫が避ける実測(How ら 2020)は説明しません —— 機構の説は査読文献でも未決着で、このノートはその数を出すだけです。★`fly_vogel_lattice` の眼は六角の近傍を要る op(`fly_hex_resample` など)には渡せません(拒否します)。

## 最初の 1 本

```python
import flyvision as L

# 7 cm 周期の縞を個眼間角 1.1° の六角格子で見る: 正面と 60° で折り返す距離、ナイキストに残るコントラスト
t = L.sampling_alias_distance(0.07, 1.1, acceptance_deg=1.0)
print("正面 %.3f m、MTF@Nyq(Δρ=1.0°) %.3f" % (t["distance_m"], t["mtf_at_nyquist"]))
print("60° %.3f m" % L.sampling_alias_distance(0.07, 1.1, view_angle_deg=60.0)["distance_m"])

# 同じ 721 個眼・同じ平均間隔のフィボナッチの眼
eye_hex = L.fly_hex_lattice(radius=15, dphi_deg=1.1)
eye_vog = L.fly_vogel_lattice(radius=15, dphi_deg=1.1)
print(len(eye_hex["az_rad"]), len(eye_vog["az_rad"]))
```
