---
op: acoustic_material_table
dim: acoustics
category: ultrasonic
in: 
out: table
examples: [poc_sam_hybrid_bonding_voids]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# acoustic_material_table — ACOUSTICS `ultrasonic` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.acoustic_material_table()` (実装を直接呼ぶなら `import ultrasound; ultrasound.acoustic_material_table()`、台帳から引くなら `opsacoustics.get("acoustic_material_table")`)

## 使い方

Built-in acoustic material table: density, longitudinal speed, impedance Z = rho*c, attenuation alpha0*f^n, with a source and a verified flag per entry (``table``).

返り: ``{"kind": "acoustic_materials", "materials": {name: {rho, c, Z, alpha0, alpha_n,
verified, source, uncertainty}}}``。``verified`` が False の材料は代表値の置き場で、
:func:`acoustic_layer_stack` は ``allow_unverified=True`` が無い限り拒む。
単位: rho [kg/m³]、c [m/s]、Z [Rayl]、alpha0 [Np/m/Hz^n]。
Raises: 何も拒まない(引数が無い)。返す dict は毎回の複製で、書き換えても表は変わらない。

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_sam_hybrid_bonding_voids](../../../../examples/poc_sam_hybrid_bonding_voids.py) — `py -3.11 examples/poc_sam_hybrid_bonding_voids.py`

## 型が繋がる次の op(`table` を入力に取れる)

[istft](../transform/istft.md) · [acoustic_interface_coefficients](acoustic_interface_coefficients.md) · [pulse_echo_ascan](pulse_echo_ascan.md) · [sam_cscan](sam_cscan.md) · [echo_phase_polarity](echo_phase_polarity.md) · [sam_frequency_tradeoff](sam_frequency_tradeoff.md)

## 同カテゴリ(`ultrasonic`)

[acoustic_layer_stack](acoustic_layer_stack.md) · [acoustic_interface_coefficients](acoustic_interface_coefficients.md) · [pulse_echo_ascan](pulse_echo_ascan.md) · [sam_cscan](sam_cscan.md) · [echo_phase_polarity](echo_phase_polarity.md) · [sam_frequency_tradeoff](sam_frequency_tradeoff.md)

---
*Provenance: ultrasound.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
