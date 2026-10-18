---
op: basis_material_decompose
dim: tomography
category: spectral_xray
in: images
out: images
examples: [poc_dual_energy_xray]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# basis_material_decompose — TOMOGRAPHY `spectral_xray` op

- **データ種**: `images` → `images`
- **呼び出し**: `import fullseye as fs; fs.ledger.basis_material_decompose(signal, channels=None, basis=('WATER', 'AL'), photons_per_pixel: 'float' = 100000.0, flat=None) -> 'dict'` (実装を直接呼ぶなら `import dualxray; dualxray.basis_material_decompose(signal, channels=None, basis=('WATER', 'AL'), photons_per_pixel: 'float' = 100000.0, flat=None) -> 'dict'`、台帳から引くなら `opstomography.get("basis_material_decompose")`)
- **台帳経由の戻り値**: `fullseye.ledger.basis_material_decompose(...)` は**宣言 out 型 `images` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.basis_material_decompose.raw(...)`、または `dualxray.basis_material_decompose` を直接呼ぶ。

## 使い方

チャネルの信号 → 基底物質の厚み図(Alvarez–Macovski / Lehmann の基底分解)。

各画素で、多色の順方向模型 L_c(b) = −ln(Σ_k W_ck g_k e^{−Σ_j μ_j(E_k) b_j} / Σ_k W_ck g_k)
を測った L_c に合わせる b(基底ごとの厚み [cm])を、分散 var(L_c) ≈ var_c/mean_c² で重みをつけた
Gauss–Newton で解く(チャネル数 = 基底の数なら連立方程式の厳密解、多ければ重みつき最小二乗
= 高計数での最尤)。初期値は空きのスペクトルの実効 μ の線形解。
基底の厚みは負になりうる(水と Al の基底でポリエチレンは Al が負)—— 物理の厚みではなく
「同じ減衰を作る基底の組合せ」。

**拒否(fail-closed)**: 信号が 0 以下・非有限の画素、:data:`DECOMP_MAX_ITER` 回で :data:`DECOMP_TOL_CM` に
収束しない画素、|b| > :data:`DECOMP_MAX_THICKNESS_CM` に飛ぶ画素は NaN にして ``rejected`` に数える
(黙って値を返さない)。反復の上限・収束の幅・厚さの上限は引数にしない —— Gauss–Newton は 3〜6 回で
1e-6 cm に収束し、どの値にしても解ける画素の答えは変わらない(効かないノブは置かない、2026-10-18)。
チャネル数 < 基底の数は ValueError(解が決まらない)。

返り値: dict(thickness (B, H, W) [cm], basis, rejected (H, W) bool, n_rejected, iterations,
residual (H, W) = 重みつき残差の二乗和)。``opstomography.call`` は thickness だけを返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dual_energy_xray](../../../../examples/poc_dual_energy_xray.py) — `py -3.11 examples/poc_dual_energy_xray.py`

## 型が繋がる次の op(`images` を入力に取れる)

[xray_channel_projection](xray_channel_projection.md) · [r_value_map](r_value_map.md) · [effective_z_map](effective_z_map.md)

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_attenuation](material_xray_attenuation.md) · [material_xray_constants](material_xray_constants.md) · [material_effective_z](material_effective_z.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md)

---
*Provenance: dualxray.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
