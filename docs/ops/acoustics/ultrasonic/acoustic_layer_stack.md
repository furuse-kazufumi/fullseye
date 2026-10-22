---
op: acoustic_layer_stack
dim: acoustics
category: ultrasonic
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# acoustic_layer_stack — ACOUSTICS `ultrasonic` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.acoustic_layer_stack(layers=(('silicon', 0.0001), ('sio2', 2e-06)), substrate='silicon', couplant='water', allow_unverified=False)` (実装を直接呼ぶなら `import ultrasound; ultrasound.acoustic_layer_stack(layers=(('silicon', 0.0001), ('sio2', 2e-06)), substrate='silicon', couplant='water', allow_unverified=False)`、台帳から引くなら `opsacoustics.get("acoustic_layer_stack")`)

## 使い方

Layered stack for normal-incidence pulse-echo: couplant, layers (material, thickness in m) from the top, and a half-space substrate (``table``).

``layers`` は ``[(材料, 厚さ [m]), ...]``(上から)。材料は表の名前
(:func:`acoustic_material_table`)か ``{"rho", "c", "alpha0", "alpha_n", "name"}`` の dict。
層は 0 枚でもよい(結合液と基板の 1 界面)。返りの ``interfaces`` は上から
``couplant|layer0``, ``layer0|layer1``, …, ``layerN-1|substrate`` の名前、``t_interfaces`` は
最初の界面からの往復時間 [s] で ``2 Σ d_j / c_j``、``depth`` はその深さ [m]。

Raises ValueError: 厚さが 0 以下・1 m 超・非有限、未知の材料、確かめていない材料
(``allow_unverified`` 無し)、ρ・c が 0 以下、減衰が負、層が 256 枚超。

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[istft](../transform/istft.md) · [acoustic_interface_coefficients](acoustic_interface_coefficients.md) · [pulse_echo_ascan](pulse_echo_ascan.md) · [sam_cscan](sam_cscan.md) · [echo_phase_polarity](echo_phase_polarity.md) · [sam_frequency_tradeoff](sam_frequency_tradeoff.md)

## 同カテゴリ(`ultrasonic`)

[acoustic_material_table](acoustic_material_table.md) · [acoustic_interface_coefficients](acoustic_interface_coefficients.md) · [pulse_echo_ascan](pulse_echo_ascan.md) · [sam_cscan](sam_cscan.md) · [echo_phase_polarity](echo_phase_polarity.md) · [sam_frequency_tradeoff](sam_frequency_tradeoff.md)

---
*Provenance: ultrasound.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
