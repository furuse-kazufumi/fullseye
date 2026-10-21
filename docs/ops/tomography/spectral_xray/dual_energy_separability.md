---
op: dual_energy_separability
dim: tomography
category: spectral_xray
in: 
out: table
examples: [poc_dual_energy_xray]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# dual_energy_separability — TOMOGRAPHY `spectral_xray` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.dual_energy_separability(material_a='POLYETHYLENE', thickness_a_cm: 'float' = 1.0, material_b='AL', thickness_b_cm=None, channels=None, photons_per_pixel: 'float' = 100000.0, background=None, n_pixels: 'int' = 1) -> 'dict'` (実装を直接呼ぶなら `import dualxray; dualxray.dual_energy_separability(material_a='POLYETHYLENE', thickness_a_cm: 'float' = 1.0, material_b='AL', thickness_b_cm=None, channels=None, photons_per_pixel: 'float' = 100000.0, background=None, n_pixels: 'int' = 1) -> 'dict'`、台帳から引くなら `opstomography.get("dual_energy_separability")`)

## 使い方

2 つの材料(厚み)が、チャネルの対数減衰でどれだけ分けられるか(d′ と誤り率の閉形式)。

``thickness_b_cm=None`` は**交絡の組**: b の厚みを、最後(最も高いエネルギー)のチャネルで a と
同じ L になるように決める(単一エネルギーの像では区別できない組)。``background`` =
(材料, 厚さ cm) は両方に重なる共通の母材(肉の中の異物)。``n_pixels`` 個の画素を平均した
領域で判定する(d′ は √n 倍)。

各材料の L ベクトル(チャネルごと)は平均 μ_a, μ_b、共分散は Poisson の差分近似
Σ = diag(var_c/mean_c²)/n。判別は等事前確率の線形判別(LDA)で、d′² = Δᵀ Σ̄⁻¹ Δ、
誤り率 = Φ(−d′/2)。比べのため、1 チャネルだけで判定したときの d′ も返す(交絡の組では最後の
チャネルの d′ は 0)。

返り値: dict(thickness_b_cm, L_a, L_b, R_a, R_b, d_prime, error_rate, d_prime_single (C,),
error_rate_single (C,), sigma_L (C,), n_pixels)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dual_energy_xray](../../../../examples/poc_dual_energy_xray.py) — `py -3.11 examples/poc_dual_energy_xray.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_attenuation](material_xray_attenuation.md) · [material_xray_constants](material_xray_constants.md) · [material_effective_z](material_effective_z.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md)

---
*Provenance: dualxray.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
