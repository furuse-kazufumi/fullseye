---
op: pulse_echo_ascan
dim: acoustics
category: ultrasonic
in: table
out: table
examples: [poc_sam_hybrid_bonding_voids]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# pulse_echo_ascan — ACOUSTICS `ultrasonic` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pulse_echo_ascan(stack, f0=100000000.0, bandwidth=0.6, water_path=0.002, rate=None, duration=None, n_reverb=40)` (実装を直接呼ぶなら `import ultrasound; ultrasound.pulse_echo_ascan(stack, f0=100000000.0, bandwidth=0.6, water_path=0.002, rate=None, duration=None, n_reverb=40)`、台帳から引くなら `opsacoustics.get("pulse_echo_ascan")`)

## 使い方

RF A-scan of a layered stack for a broadband pulse at normal incidence: transfer-matrix stack response, water path and power-law attenuation (``table``).

パルスはガウス型スペクトル(中心 ``f0`` [Hz]、−6 dB の比帯域 ``bandwidth``)。
応答 ``S(f) = w(f) · exp(−2ik_w z_w) · R_stack(f)``、``k = 2πf/c − iα(f)``。
振幅の単位は「焦点の完全反射体・水の損失なし」の包絡線の山 = 1。
時間窓は表面エコーの手前から始まり、``n_reverb`` 回分の積層の往復(残響)を含む。
FFT の周期で窓の外の残響が先頭へ折り返すので、長い残響の積層は ``duration`` を伸ばす。

返り: ``t`` [s] ``rf`` ``analytic``(複素)``envelope`` ``rate`` ``f0`` ``bandwidth``
``sigma_t``(包絡線の標準偏差)``water_path`` ``t_front``(表面エコーの時刻)
``t_interfaces``(各界面のエコーの時刻 = 表面 + 層の往復)``freqs`` ``weights``
``response``(各周波数の水の経路込みの複素応答)``names``。
Raises ValueError: 印の無い table、f0 ≤ 0 / 10 GHz 超、比帯域 0.02–1.5 の外、水の経路 ≤ 0、
サンプリングが帯域の 2 倍未満、サンプル数が上限超え。

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_sam_hybrid_bonding_voids](../../../../examples/poc_sam_hybrid_bonding_voids.py) — `py -3.11 examples/poc_sam_hybrid_bonding_voids.py`

## 型が繋がる次の op(`table` を入力に取れる)

[istft](../transform/istft.md) · [acoustic_interface_coefficients](acoustic_interface_coefficients.md) · [sam_cscan](sam_cscan.md) · [echo_phase_polarity](echo_phase_polarity.md) · [sam_frequency_tradeoff](sam_frequency_tradeoff.md)

## 同カテゴリ(`ultrasonic`)

[acoustic_material_table](acoustic_material_table.md) · [acoustic_layer_stack](acoustic_layer_stack.md) · [acoustic_interface_coefficients](acoustic_interface_coefficients.md) · [sam_cscan](sam_cscan.md) · [echo_phase_polarity](echo_phase_polarity.md) · [sam_frequency_tradeoff](sam_frequency_tradeoff.md)

---
*Provenance: ultrasound.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
