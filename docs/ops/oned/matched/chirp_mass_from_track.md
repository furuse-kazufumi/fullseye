---
op: chirp_mass_from_track
dim: oned
category: matched
in: pairs
out: table
gpu: なし
examples: [poc_gw_detector_pseudo_simulation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# chirp_mass_from_track — ONED `matched` op

- **データ種**: `pairs` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.chirp_mass_from_track(track) -> 'dict'` (実装を直接呼ぶなら `import gwsearch; gwsearch.chirp_mass_from_track(track) -> 'dict'`、台帳から引くなら `ops1d.get("chirp_mass_from_track")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

重力波周波数の軌跡 (t, f) からチャープ質量と合体時刻を最小二乗で返す。

Parameters
----------
track : array_like
    ``(N, 2)`` の ``pairs``: 列 0 = 時刻 [s]、列 1 = 重力波周波数 [Hz] (正)。N ≥ 3。

Returns
-------
dict
    ``chirp_mass_msun``、``coalescence_time_s``(t_c = a/b)、``slope``(b)、
    ``residual_rms``(``f^{−8/3}`` の当てはめ残差)、``n_points``、``rising``(周波数が
    時間とともに上がる軌跡か)。**上がらない軌跡はインスパイラルではない**ので
    ``rising = False`` とし、``chirp_mass_msun`` と ``coalescence_time_s`` は ``None``
    (例外にはしない —— 「鳴いていない」は正しい答え)。

Notes
-----
``f^{−8/3} = a − b·t``、``b = (8/3)(96/5)π^{8/3}(GM_c/c³)^{5/3}``。PRL 116, 061102 の
式 (1) の積分形。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_gw_detector_pseudo_simulation](../../../../examples/poc_gw_detector_pseudo_simulation.py) — `py -3.11 examples/poc_gw_detector_pseudo_simulation.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`matched`)

[psd_welch](psd_welch.md) · [whiten_by_psd](whiten_by_psd.md) · [chirp_newtonian](chirp_newtonian.md) · [matched_filter_snr](matched_filter_snr.md) · [optimal_snr](optimal_snr.md) · [coincidence_delay](coincidence_delay.md)

---
*Provenance: gwsearch.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
