---
op: ae_read_csv
dim: drive
category: grind
in: any
out: signal
examples: [poc_powder_grinding_ae]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# ae_read_csv — DRIVE `grind` op

- **データ種**: `any` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.ae_read_csv(path, header_lines: 'int' = 12, offset: 'float' = 32768.0, full_scale: 'float' = 32768.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import grind; grind.ae_read_csv(path, header_lines: 'int' = 12, offset: 'float' = 32768.0, full_scale: 'float' = 32768.0) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("ae_read_csv")`)

## 使い方

AE の生の CSV(ヘッダ ``header_lines`` 行 + 1 行 1 標本の ADC 値)を電圧 [V] の信号にする。

公開データの ADC は 16 bit・±1 V・ストレートオフセットバイナリ(0 → −1 V、32768 → 0 V、65535 → +1 V)なので
``(raw − offset) / full_scale``(解析コードの変換と同じ)。パスは返り値に残さない。数値でない行・空 → ``ValueError``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_grinding_ae](../../../../examples/poc_powder_grinding_ae.py) — `py -3.11 examples/poc_powder_grinding_ae.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`grind`)

[particle_size_read](particle_size_read.md) · [particle_size_dx](particle_size_dx.md) · [particle_size_oversize](particle_size_oversize.md) · [particle_size_synth](particle_size_synth.md) · [comminution_energy](comminution_energy.md) · [comminution_law_fit](comminution_law_fit.md) · [breakage_first_order_fit](breakage_first_order_fit.md) · [replicate_compare](replicate_compare.md)

---
*Provenance: grind.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
