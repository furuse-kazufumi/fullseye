---
id: grating-interferometry
title: 格子干渉計(タルボ・ロー)で透過・微分位相・暗視野の 3 像を分ける
title_en: Grating interferometry (Talbot / Talbot-Lau): transmission, differential phase and dark field from one phase-stepping scan
category: 測る
ops: [talbot_grating_design, talbot_carpet, talbot_source_visibility, grating_stepping_simulate, grating_step_period_estimate, grating_three_image_retrieve, darkfield_scatter_relation, dpc_integrate]
examples: [poc_grating_interferometry]
version: 0.6.1
inputs: [images]
pipeline: [talbot_grating_design, talbot_source_visibility, grating_step_period_estimate, grating_three_image_retrieve, darkfield_scatter_relation, dpc_integrate]
alternatives: [talbot_carpet, grating_stepping_simulate, wrapped_phase, moire_talbot_gap, angular_spectrum_propagate]
limits: 位相ステップは 1 次の正弦だけを見る(格子の高次の調和・ステップの位置の揺れ・検出器の点広がりは模型に無い)。暗視野から散乱角へはガウス散乱の近似。単色の順モデルなので、多色の線源で吸収が平均のエネルギーを上げて可視度が落ちる効果は無い。折り返しは隣との跳びでしか見えない。
calibration: 1 周期のステップ数 P は空気(基準)の区画で grating_step_period_estimate から決める。基準と試料の露光の比は reference_exposure に渡す。屈折角・位相への換算は分析格子の周期 p2 と距離 d、波長で決まる(talbot_grating_design の値か実測)。
---

# 格子干渉計(タルボ・ロー)で透過・微分位相・暗視野の 3 像を分ける

## できること

X 線(や可視光)の透過像は「どれだけ吸われたか」しか写しません。周期数 µm の格子を 2 枚(線源が大きいなら 3 枚)入れ、どちらかを 1 周期ずらしながら数枚撮ると、各画素で縞の正弦が取れます。その**平均**が透過(吸収)、**位相のずれ**が微分位相(屈折角)、**振幅の落ち方**が暗視野(画素より小さい構造からの小角散乱)です。吸収がまわりとほとんど同じ繊維・粉・微小な割れ・気孔の群が、暗視野でははっきり出ます。

設計は閉形式です。`talbot_grating_design` が位相 π / π/2 / 吸収格子の分数タルボ距離(Weitkamp ら 2005)、円錐ビームで伸びる距離 d' = Ld/(L − d) と分析格子の周期、Lau の条件の線源格子の周期を返し、`talbot_carpet` が格子の後ろの強度 I(x, z)(タルボ絨毯)を回折次数の和で描きます。`talbot_source_visibility` は線源の幅・ガウスの焦点・線源格子で縞の可視度が何倍に落ちるかを出します(p1 = 4 µm・28 keV・L = 1.2 m で、焦点 2 mm なら 0.008、Lau の条件の線源格子で 2/π)。

処理は、`grating_step_period_estimate`(1 周期が何ステップかを残差の最小で推定)→ `grating_three_image_retrieve`(試料ありと基準の 2 組 → 3 像。P = N は `fringe.wrapped_phase` / `fringe.modulation`、P ≠ N は 3 項の最小二乗)→ `darkfield_scatter_relation`(暗視野 → 散乱角の広がり σ と線拡散係数)/ `dpc_integrate`(微分位相 → 波面の位相 → 投影の厚さ)。順モデル `grating_stepping_simulate` で、撮る前に雑音(Poisson)と可視度の予算を確かめられます。

PoC `poc_grating_interferometry` は、短繊維強化樹脂の板で幅 2 µm の割れを暗視野の CNR 13.5(吸収 1.34)で見つけ、4 方位の暗視野から繊維の向きを中央値 2.7° で戻します。公開の実データ(CC BY 4.0)では 1 周期のステップ数を推定してから 3 像に分けます。

## What it does

Eight ops in `gratinginterf` for grating-based phase-contrast and dark-field imaging: closed-form geometry (fractional Talbot distances for π, π/2 and absorption gratings, cone-beam distance and analyser period, the Lau source-grating period), the Talbot carpet behind a binary grating as a sum over diffraction orders, the visibility loss from source size and source gratings, a forward model of phase-stepping stacks with Poisson noise, estimation of the number of steps per period from the sine-fit residual, retrieval of transmission, differential phase and dark field from sample and reference stacks, conversion of dark field to a Gaussian scattering width, and integration of the differential phase into the wavefront phase and projected thickness (refusing wrapped input). The PoC finds a 2 µm crack in a short-fibre composite plate in the dark field (CNR 13.5 against 1.34 in absorption), recovers fibre orientation from four grating directions, and separates the three images of a public CC BY 4.0 Talbot-Lau dataset.

## 向くところ / 向かないところ

**向く**: 吸収のコントラストが弱いもの —— 樹脂・複合材の繊維の向きと分布、粉の詰まり具合、微小な割れ・剥離・気孔、食品や軽元素の異物 —— を、画素より細かい構造の散乱として見る用途。装置を組む前の格子の距離・周期・線源格子の見積り、撮る前の雑音の予算。

**向かない**: 強く吸収する金属の中(縞の平均が雑音に沈み、可視度の比が決まらない —— 基準の可視度が低い画素は NaN にして数を返す)。縞の位相が π を超える鋭い屈折(折り返し。隣と跳ぶ画素があれば `dpc_integrate` は拒否するが、平らな背景の隣の 1 画素だけが超える場合は見分けられない)。定量の散乱(σ)はガウス散乱の近似で、構造の大きさが自己相関長 ξ = λd/p2 と同じ程度になると σ では表せません。

## 推奨パイプライン

`talbot_grating_design` → `talbot_source_visibility` → `grating_step_period_estimate` → `grating_three_image_retrieve` → `darkfield_scatter_relation` → `dpc_integrate`

`talbot_grating_design` で格子の距離と周期(と線源格子の周期)を決める → `talbot_source_visibility` で焦点の大きさと線源格子から縞の可視度の予算を出す → 撮った基準の画像列の空気の区画で `grating_step_period_estimate` を回して 1 周期のステップ数 P を決める → `grating_three_image_retrieve`(試料・基準、P、露光の比)で 3 像 → 暗視野は `darkfield_scatter_relation` で散乱角の広がりへ、微分位相は `dpc_integrate`(baseline="both" で背景の位相の傾きを消す)で位相と厚さへ。

## 代替

縞の解析だけなら `wrapped_phase`(と関数 `fringe.modulation`、N 等分の位相シフト)。タルボ絨毯の 1 断面なら `angular_spectrum_propagate` で場を直接伝搬。近接ギャップのモアレの位置合わせでタルボ効果を扱うなら `moire_talbot_gap`。撮る前の順モデルは `grating_stepping_simulate`。

## 限界

- 位相ステップは 1 次の正弦だけを見る。格子の高次の調和、ステップの位置の揺れ(実データでは P を合わせても残差 0.4 % が残る)、検出器の点広がりは模型に無い。
- 暗視野 → σ はガウス散乱の近似(Strobl 2014 の積分の特別な場合)。一様な散乱では sinc になり、ガウスで直した σ は分布の標準偏差と 5 % 以上ずれる(門で固定)。
- 単色の順モデル。多色の線源で吸収が平均のエネルギーを上げると、散乱しない物体でも可視度が落ちる(実データの球の中央で −ln D ≈ 0.17)。
- 折り返しは「隣との跳び」でしか見えない。鋭い縁の 1 画素だけが π を超える場合は黙って通る(PoC で中央の厚さ −857 µm、真値 2000 µm を示す)。
- 線源格子は開口が一様に照らされた理想の矩形。ガウスの焦点と線源格子の組は拒否する。

## 実寸校正

1 周期のステップ数 P は装置の格子の送り量の較正で決まり、実データでは枚数 N と一致しないことがある(公開データで基準 22 枚・P = 20.80、試料 24 枚・P = 22.30)。空気か基準の区画で `grating_step_period_estimate` を回して決める。基準と試料の露光(1 枚あたりの光子数)が違えば `reference_exposure` に比を渡す(透過だけが比で化け、暗視野と微分位相は比と差なので影響しない)。屈折角・位相への換算は分析格子の周期 p2・格子間の距離 d・波長で決まる —— 設計値か、既知の屈折率の丸棒(`dpc_integrate` で厚さが既知の値に戻るか)で確かめる。

## 最初の 1 本

```python
import numpy as np
import gratinginterf as GI

g = GI.talbot_grating_design(4.0, energy_kev=14.4, grating="pi", order=1)
print(round(g["distance_mm"], 1), g["analyzer_period_um"])            # 23.2 2.0(Weitkamp ら 2005 の装置)

yy, xx = np.mgrid[:32, :48]
dfm = np.where(xx > 24, 0.55, 1.0)                                     # 右半分だけ散乱する
s = GI.grating_stepping_simulate(np.full((32, 48), 0.9), None, dfm, n_steps=8, flux=3000.0, seed=1)
r = GI.grating_stepping_simulate(None, n_steps=8, flux=3000.0, seed=2, shape=(32, 48))
o = GI.grating_three_image_retrieve(s, r)
print(round(float(np.mean(o["transmission"])), 2), round(float(np.mean(o["darkfield"][:, 30:])), 2))   # 0.9 0.55
```

走らせて見るなら `py -3.11 examples/poc_grating_interferometry.py`(図は `out/figures/poc_grating_interferometry/`)。
