---
op: sam_frequency_tradeoff
dim: acoustics
category: ultrasonic
in: table
out: table
examples: [poc_sam_hybrid_bonding_voids]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# sam_frequency_tradeoff — ACOUSTICS `ultrasonic` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sam_frequency_tradeoff(stack, void_diameter, water_path=0.001, f_number=3.0, interface=None, k_res=1.02, f_min=1000000.0, f_max=5000000000.0, n_grid=600, bandwidth=0.6, n_sigma_gate=5.0)` (実装を直接呼ぶなら `import ultrasound; ultrasound.sam_frequency_tradeoff(stack, void_diameter, water_path=0.001, f_number=3.0, interface=None, k_res=1.02, f_min=1000000.0, f_max=5000000000.0, n_grid=600, bandwidth=0.6, n_sigma_gate=5.0)`、台帳から引くなら `opsacoustics.get("sam_frequency_tradeoff")`)

## 使い方

Optimal SAM frequency for a void of given size at a buried interface: lateral fill (1 - 2^-(a/w)^2, w = k_res*lambda_w*F#) against two-way attenuation; closed form when all losses go as f^2 (``table``).

信号 ``S(f) = η(f) · exp(−L(f))``、``η = 1 − 2^{−(a/w)²}`` はボイド(直径 a)の中心に
ガウスの往復 PSF(半値全幅 ``w = k/f``、``k = k_res c_w F#``)が当たったときの充填率、
``L(f) = 2 α_w(f) z_w + 2 Σ_{j<interface} α_j(f) d_j``(水の経路と上の層の往復減衰 [Np])。
減衰がすべて ``f²``(``L = β f²``)なら ``dlnS/df = 0`` から
``f* = (k/a) · sqrt(log2(1 + a² ln2 / (β k²)))``(小さなボイドの極限で ``1/√β``)。
それ以外は対数格子で探して有界の 1-D 最適化で詰める。
返り: ``freqs`` ``fwhm`` ``fill`` ``loss_np`` ``loss_db`` ``signal`` ``f_opt``(数値)
``f_opt_closed``(閉形式が立つときだけ、そうでなければ None)``beta`` ``k``
``fwhm_at_opt`` ``f_number_min``(臨界角の上限)。
時間の分解能の下限も返す: 表面エコーと界面のエコーの間隔 ``t_sep``(積層の往復時間)が
パルスの包絡線の ``n_sigma_gate`` σ_t(ゲートの半幅 2σ_t + 裾 3σ_t)より短いと、表面エコーの
裾がゲートに入る。σ_t = FWHM_PER_SIGMA / (2π · bandwidth · f) なので
``f_min_time = n_sigma_gate · 2.3548 / (2π · bandwidth · t_sep)``、
``f_opt_usable = max(f_opt, f_min_time)``(表面の界面(interface=0)なら下限 0)。
★ボイドの反射 |R| は周波数によらず 1 とみなす(薄い空気の層では ~1)。
Raises ValueError: 印の無い積層、直径 ≤ 0、f_min ≥ f_max、F# が臨界角の上限より小さい、減衰が 0
(最適周波数が存在しない — 上へ行くほど良い)。

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_sam_hybrid_bonding_voids](../../../../examples/poc_sam_hybrid_bonding_voids.py) — `py -3.11 examples/poc_sam_hybrid_bonding_voids.py`

## 型が繋がる次の op(`table` を入力に取れる)

[istft](../transform/istft.md) · [acoustic_interface_coefficients](acoustic_interface_coefficients.md) · [pulse_echo_ascan](pulse_echo_ascan.md) · [sam_cscan](sam_cscan.md) · [echo_phase_polarity](echo_phase_polarity.md)

## 同カテゴリ(`ultrasonic`)

[acoustic_material_table](acoustic_material_table.md) · [acoustic_layer_stack](acoustic_layer_stack.md) · [acoustic_interface_coefficients](acoustic_interface_coefficients.md) · [pulse_echo_ascan](pulse_echo_ascan.md) · [sam_cscan](sam_cscan.md) · [echo_phase_polarity](echo_phase_polarity.md)

---
*Provenance: ultrasound.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
