---
op: echo_phase_polarity
dim: acoustics
category: ultrasonic
in: table
out: table
gpu: なし
examples: [poc_sam_hybrid_bonding_voids]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# echo_phase_polarity — ACOUSTICS `ultrasonic` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.echo_phase_polarity(echo, interface=1, half_width=None, reference_interface=0, tol_deg=45.0)` (実装を直接呼ぶなら `import ultrasound; ultrasound.echo_phase_polarity(echo, interface=1, half_width=None, reference_interface=0, tol_deg=45.0)`、台帳から引くなら `opsacoustics.get("echo_phase_polarity")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Classify an interface echo by its phase relative to the front-surface echo: in phase (Z rises), inverted (Z drops) or quadrature (thin-layer, sign not meaningful) (``table``).

``echo`` は :func:`pulse_echo_ascan` の A スキャン(``kind='ascan'``)か :func:`sam_cscan` の
C スキャン(``kind='cscan'``、既に位相を持つので分類だけする)。
A スキャンでは界面のエコーの**期待時刻** ``t_interfaces[interface]`` での解析信号の偏角から、
基準エコー(``reference_interface``、既定 = 表面)の期待時刻での偏角を引く(解析信号は
スペクトルから任意の時刻で厳密に足す)。振幅は ``±half_width``(既定 2σ_t)のゲートの中の
包絡線の山。★包絡線の山の時刻で位相を読まないのは、山は平らで雑音が時刻を動かし、位相が
``2π f0 δt`` だけ回るから(1 ns で 200 MHz なら 72°)。代わりに、積層の厚さの誤差 δd は
位相を ``4π f0 δd / c`` 回す(Si・200 MHz で 1 µm あたり 17°)。
分類: ``|位相| ≤ tol`` → 同相 (+1)、``|位相| ≥ 180° − tol`` → 反転 (−1)、それ以外 → 直交 (0)。
★基準は**表面エコー**。表面そのものが Z の下がる界面(水より柔らかい最上層)なら表面
エコーが反転しているので、Z の上がる深い界面が「反転」と読まれる —— 分類は「表面に対して
同じ向きか逆向きか」であって、絶対の Z の上下ではない(``tests/test_ultrasound.py`` の門)。
★``signed_peak``(ゲート内で |RF| が最大のサンプルの、参照エコーに対する相対符号)も返す —— 現場で言う
「極性」はこれだが、直交のエコー(薄い層の微分形)では帯域と標本化でどちらにも
転ぶ。``signed_peak_agrees`` が False の行はそれ。
返り(A スキャン): ``phase`` [rad] ``phase_deg`` ``amplitude`` ``t_peak`` ``polarity``
(+1/−1/0)``label`` ``signed_peak`` ``signed_peak_agrees``。
返り(C スキャン): ``polarity`` の地図と各分類の画素数。
Raises ValueError: A/C スキャンの印の無い入力、界面の番号が範囲外、tol_deg が (0, 90) の外、
ゲートの中の標本が 3 未満。

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_sam_hybrid_bonding_voids](../../../../examples/poc_sam_hybrid_bonding_voids.py) — `py -3.11 examples/poc_sam_hybrid_bonding_voids.py`

## 型が繋がる次の op(`table` を入力に取れる)

[istft](../transform/istft.md) · [acoustic_interface_coefficients](acoustic_interface_coefficients.md) · [pulse_echo_ascan](pulse_echo_ascan.md) · [sam_cscan](sam_cscan.md) · [sam_frequency_tradeoff](sam_frequency_tradeoff.md)

## 同カテゴリ(`ultrasonic`)

[acoustic_material_table](acoustic_material_table.md) · [acoustic_layer_stack](acoustic_layer_stack.md) · [acoustic_interface_coefficients](acoustic_interface_coefficients.md) · [pulse_echo_ascan](pulse_echo_ascan.md) · [sam_cscan](sam_cscan.md) · [sam_frequency_tradeoff](sam_frequency_tradeoff.md)

---
*Provenance: ultrasound.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
