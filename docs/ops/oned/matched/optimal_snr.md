---
op: optimal_snr
dim: oned
category: matched
in: signal × pairs
out: measurement
examples: [poc_gw_detector_pseudo_simulation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# optimal_snr — ONED `matched` op

- **データ種**: `signal × pairs` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.optimal_snr(template, psd, rate: 'float' = 4096.0, *, f_low_hz: 'float | None' = 20.0, f_high_hz: 'float | None' = None) -> 'float'` (実装を直接呼ぶなら `import gwsearch; gwsearch.optimal_snr(template, psd, rate: 'float' = 4096.0, *, f_low_hz: 'float | None' = 20.0, f_high_hz: 'float | None' = None) -> 'float'`、台帳から引くなら `ops1d.get("optimal_snr")`)

## 使い方

テンプレートの最適 SNR ``σ = √(4∫|h̃|²/S df)``(``measurement``)。

Parameters
----------
template : array_like
    波形(1-D)。
psd : array_like
    片側 PSD の ``pairs``。
rate : float
    標本化周波数 [Hz]。
f_low_hz, f_high_hz : float or None
    内積を取る帯域(None は端まで)。

Returns
-------
float
    この PSD の雑音に対し、位相・時刻が既知のときに期待される SNR。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_gw_detector_pseudo_simulation](../../../../examples/poc_gw_detector_pseudo_simulation.py) — `py -3.11 examples/poc_gw_detector_pseudo_simulation.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`matched`)

[psd_welch](psd_welch.md) · [whiten_by_psd](whiten_by_psd.md) · [chirp_newtonian](chirp_newtonian.md) · [chirp_mass_from_track](chirp_mass_from_track.md) · [matched_filter_snr](matched_filter_snr.md) · [coincidence_delay](coincidence_delay.md)

---
*Provenance: gwsearch.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
