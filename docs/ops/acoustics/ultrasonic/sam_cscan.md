---
op: sam_cscan
dim: acoustics
category: ultrasonic
in: labels2d × table
out: table
examples: [poc_sam_hybrid_bonding_voids]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# sam_cscan — ACOUSTICS `ultrasonic` op

- **データ種**: `labels2d × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sam_cscan(bond_map, stacks, pixel_size=2e-06, f0=150000000.0, bandwidth=0.6, f_number=3.0, water_path=0.001, gate_interface=1, half_width=None, k_res=1.02, noise_rms=0.0, seed=0, n_reverb=40, psf_nodes=32)` (実装を直接呼ぶなら `import ultrasound; ultrasound.sam_cscan(bond_map, stacks, pixel_size=2e-06, f0=150000000.0, bandwidth=0.6, f_number=3.0, water_path=0.001, gate_interface=1, half_width=None, k_res=1.02, noise_rms=0.0, seed=0, n_reverb=40, psf_nodes=32)`、台帳から引くなら `opsacoustics.get("sam_cscan")`)

## 使い方

Focused-transducer C-scan of a 2-D bond map: per-frequency Gaussian lateral PSF, time gate at an interface, amplitude, phase, in-phase (signed) and signed-peak images (``table``).

``bond_map`` は整数ラベルの 2-D 配列、``stacks`` は ``{ラベル: acoustic_layer_stack}``
(例: 0 = 誘電体、1 = Cu パッド、2 = ボイド、3 = パッド上のボイド)。
各周波数 f で、ラベルごとの反射 ``R_c(f)`` を地図に置いてガウスの横 PSF
(半値全幅 ``k_res · (c_w/f) · F#``、往復の振幅 PSF、無限の平面で利得 1)で畳み込み、
水の経路と減衰を掛けて、ゲートの時刻での解析信号に和を取る。
ゲートは ``t_interfaces[gate_interface] ± half_width``(既定 2σ_t)。
出力の像:
  * ``amplitude`` — ゲート内の包絡線の山(振幅の C スキャン)
  * ``phase`` — 界面のエコーの**期待時刻**(表面エコーの時刻 + 積層の往復)での解析信号の
    偏角 − 表面エコーの期待時刻での偏角 [rad]
  * ``inphase`` — 期待時刻の解析信号の同相成分 ``|a| cos(phase)``(符号つき。反転したエコーは負)
  * ``signed_peak`` — ゲート内で |RF| が最大のサンプルの値(従来の極性の読み方)
  * ``tof`` — 包絡線の山の時刻 [s]
``plane_phasor`` は ``{ラベル: 複素数}`` —— そのラベルが一面に広がっていたときの期待時刻の
値(雑音なし、基準の偏角を引いた後)。地図の設計(どこがパッドか)が分かっていれば、
良品の基準として ``inphase`` / ``amplitude`` から引ける。
★位相を包絡線の山の時刻でなく期待時刻で読む理由は :func:`echo_phase_polarity` と同じ
(山の時刻の揺れが位相を ``2π f0 δt`` 回す。期待時刻なら位相の雑音は 雑音/振幅 だけ)。
代わりにダイの厚さの誤差 δd は位相を ``4π f0 δd / c`` 回す —— 厚さが場所で変わる部品では
``tof`` から期待時刻を画素ごとに直す必要がある(この op はしていない)。
``noise_rms`` は受信の加法雑音(RF の実部の RMS、探触子の帯域の形の色つき雑音)。
``psf_nodes`` は横 PSF を厳密に作る周波数の節点の数(その間は f の 1 次補間)。
★ボイドの中心でも節点を倍にして変わる量は 1e-3 未満(``tests/test_ultrasound.py``)。
Raises ValueError: 印の無い積層・地図のラベルに積層が無い・結合液が積層ごとに違う・
``F#`` が最初の固体層の縦波の臨界角を超える(横波に化ける光線はこのモデルの外)・
画素 ≤ 0・地図が大きすぎる・周波数の本数が上限超え。

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_sam_hybrid_bonding_voids](../../../../examples/poc_sam_hybrid_bonding_voids.py) — `py -3.11 examples/poc_sam_hybrid_bonding_voids.py`

## 型が繋がる次の op(`table` を入力に取れる)

[istft](../transform/istft.md) · [acoustic_interface_coefficients](acoustic_interface_coefficients.md) · [pulse_echo_ascan](pulse_echo_ascan.md) · [echo_phase_polarity](echo_phase_polarity.md) · [sam_frequency_tradeoff](sam_frequency_tradeoff.md)

## 同カテゴリ(`ultrasonic`)

[acoustic_material_table](acoustic_material_table.md) · [acoustic_layer_stack](acoustic_layer_stack.md) · [acoustic_interface_coefficients](acoustic_interface_coefficients.md) · [pulse_echo_ascan](pulse_echo_ascan.md) · [echo_phase_polarity](echo_phase_polarity.md) · [sam_frequency_tradeoff](sam_frequency_tradeoff.md)

---
*Provenance: ultrasound.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
