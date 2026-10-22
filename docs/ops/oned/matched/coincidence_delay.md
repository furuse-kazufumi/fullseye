---
op: coincidence_delay
dim: oned
category: matched
in: signal × signal
out: table
examples: [poc_gw_detector_pseudo_simulation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# coincidence_delay — ONED `matched` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.coincidence_delay(snr_a, snr_b, rate: 'float' = 4096.0, *, max_delay_s: 'float' = 0.01) -> 'dict'` (実装を直接呼ぶなら `import gwsearch; gwsearch.coincidence_delay(snr_a, snr_b, rate: 'float' = 4096.0, *, max_delay_s: 'float' = 0.01) -> 'dict'`、台帳から引くなら `ops1d.get("coincidence_delay")`)

## 使い方

2 本の SNR 時系列の山の時刻差(b − a)を副標本精度で返す。

Parameters
----------
snr_a, snr_b : array_like
    ``matched_filter_snr`` の返り(同じ長さ・同じ標本化)。
rate : float
    標本化周波数 [Hz]。
max_delay_s : float
    a の山から b の山を探す窓(±)[s]。LIGO H1–L1 は光の走行時間 10 ms。

Returns
-------
dict
    ``delay_s``(副標本、放物線)、``delay_samples``(整数)、``peak_a`` / ``peak_b``(山の高さ)、
    ``index_a`` / ``index_b``、``network_snr`` = √(peak_a² + peak_b²)、``window_samples``
    (探した窓の片側の標本数 = round(max_delay_s·rate))。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_gw_detector_pseudo_simulation](../../../../examples/poc_gw_detector_pseudo_simulation.py) — `py -3.11 examples/poc_gw_detector_pseudo_simulation.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`matched`)

[psd_welch](psd_welch.md) · [whiten_by_psd](whiten_by_psd.md) · [chirp_newtonian](chirp_newtonian.md) · [chirp_mass_from_track](chirp_mass_from_track.md) · [matched_filter_snr](matched_filter_snr.md) · [optimal_snr](optimal_snr.md)

---
*Provenance: gwsearch.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
