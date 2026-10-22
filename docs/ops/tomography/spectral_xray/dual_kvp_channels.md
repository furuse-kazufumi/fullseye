---
op: dual_kvp_channels
dim: tomography
category: spectral_xray
in: pairs × pairs
out: table
examples: [poc_dual_energy_xray]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# dual_kvp_channels — TOMOGRAPHY `spectral_xray` op

- **データ種**: `pairs × pairs` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dual_kvp_channels(spectrum_low, spectrum_high, detector: 'str' = 'CSI', detector_mm: 'float' = 0.6) -> 'dict'` (実装を直接呼ぶなら `import dualxray; dualxray.dual_kvp_channels(spectrum_low, spectrum_high, detector: 'str' = 'CSI', detector_mm: 'float' = 0.6) -> 'dict'`、台帳から引くなら `opstomography.get("dual_kvp_channels")`)

## 使い方

2 つの管電圧で撮るエネルギー積分型(シンチレータ)の 2 チャネル。

信号は吸収した光子のエネルギーの和(gain = E)。分散は Σ φ E² e^{−μt}(複合 Poisson、
Swank の雑音の増えは入れない)。2 つのスペクトルは同じエネルギーの格子に載せる(線形補間、
範囲の外は 0)。返り値の形は :func:`photon_counting_channels` と同じ(mode = "integrating")。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dual_energy_xray](../../../../examples/poc_dual_energy_xray.py) — `py -3.11 examples/poc_dual_energy_xray.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_attenuation](material_xray_attenuation.md) · [material_xray_constants](material_xray_constants.md) · [material_effective_z](material_effective_z.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [xray_channel_projection](xray_channel_projection.md)

---
*Provenance: dualxray.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
