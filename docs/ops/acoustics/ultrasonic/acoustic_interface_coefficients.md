---
op: acoustic_interface_coefficients
dim: acoustics
category: ultrasonic
in: table
out: table
examples: [poc_sam_hybrid_bonding_voids]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# acoustic_interface_coefficients — ACOUSTICS `ultrasonic` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.acoustic_interface_coefficients(stack)` (実装を直接呼ぶなら `import ultrasound; ultrasound.acoustic_interface_coefficients(stack)`、台帳から引くなら `opsacoustics.get("acoustic_interface_coefficients")`)

## 使い方

Pressure reflection/transmission at every interface of a stack, energy check R^2 + (Z1/Z2) T^2 = 1, and the phase-inversion flag Z2 < Z1 (``table``).

``R = (Z2 − Z1)/(Z2 + Z1)``(圧力)、``T = 2 Z2/(Z1 + Z2)``。``R < 0`` ⇔ ``Z2 < Z1``
(エコーの反転)。半無限どうしの界面の値で、薄い層の多重反射は入らない
(それは :func:`pulse_echo_ascan`)。返り: ``names`` ``z1`` ``z2`` ``R`` ``T`` ``energy``
``inverted`` ``t_interfaces`` ``depth``。
Raises ValueError: 印(kind='acoustic_stack')の無い table。

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_sam_hybrid_bonding_voids](../../../../examples/poc_sam_hybrid_bonding_voids.py) — `py -3.11 examples/poc_sam_hybrid_bonding_voids.py`

## 型が繋がる次の op(`table` を入力に取れる)

[istft](../transform/istft.md) · [pulse_echo_ascan](pulse_echo_ascan.md) · [sam_cscan](sam_cscan.md) · [echo_phase_polarity](echo_phase_polarity.md) · [sam_frequency_tradeoff](sam_frequency_tradeoff.md)

## 同カテゴリ(`ultrasonic`)

[acoustic_material_table](acoustic_material_table.md) · [acoustic_layer_stack](acoustic_layer_stack.md) · [pulse_echo_ascan](pulse_echo_ascan.md) · [sam_cscan](sam_cscan.md) · [echo_phase_polarity](echo_phase_polarity.md) · [sam_frequency_tradeoff](sam_frequency_tradeoff.md)

---
*Provenance: ultrasound.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
