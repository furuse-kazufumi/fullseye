---
op: xray_channel_projection
dim: tomography
category: spectral_xray
in: images
out: images
examples: [poc_dual_energy_xray]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# xray_channel_projection — TOMOGRAPHY `spectral_xray` op

- **データ種**: `images` → `images`
- **呼び出し**: `import fullseye as fs; fs.ledger.xray_channel_projection(thickness, materials_list=('MUSCLE_ICRU44',), channels=None, photons_per_pixel: 'float' = 100000.0, noise: 'bool' = True, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import dualxray; dualxray.xray_channel_projection(thickness, materials_list=('MUSCLE_ICRU44',), channels=None, photons_per_pixel: 'float' = 100000.0, noise: 'bool' = True, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opstomography.get("xray_channel_projection")`)
- **台帳経由の戻り値**: `fullseye.ledger.xray_channel_projection(...)` は**宣言 out 型 `images` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.xray_channel_projection.raw(...)`、または `dualxray.xray_channel_projection` を直接呼ぶ。

## 使い方

材料ごとの厚み図 → チャネルごとの信号の像 (C, H, W)。

``thickness``: (M, H, W)、単位 cm(``materials_list`` の材料ごとに 1 枚、重なりは足し算 = 細いビームの
Beer–Lambert)。``photons_per_pixel``: 1 画素に入射する光子の数(全エネルギー、検出器の前)。
計数(counting)のチャネルは平均 n₀ Σ W e^{−μt} の Poisson 標本(``photoncount.photon_sample``、
チャネルごとに seed から決まる別の乱数列)。積分型(integrating)は平均と分散 Σ W E² e^{−μt}
のガウス(複合 Poisson の近似)。``noise=False`` は平均そのもの。
空き(厚み 0)の平均は ``channels`` から決まるので、分解の op は同じ ``channels`` と
``photons_per_pixel`` を受けて自分で計算する(白の撮影を別に渡すこともできる)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dual_energy_xray](../../../../examples/poc_dual_energy_xray.py) — `py -3.11 examples/poc_dual_energy_xray.py`

## 型が繋がる次の op(`images` を入力に取れる)

[basis_material_decompose](basis_material_decompose.md) · [r_value_map](r_value_map.md) · [effective_z_map](effective_z_map.md)

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_attenuation](material_xray_attenuation.md) · [material_xray_constants](material_xray_constants.md) · [material_effective_z](material_effective_z.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md)

---
*Provenance: dualxray.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
