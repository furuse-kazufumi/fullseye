---
op: psd_welch
dim: oned
category: matched
in: signal
out: pairs
examples: [poc_gw_detector_pseudo_simulation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# psd_welch — ONED `matched` op

- **データ種**: `signal` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.psd_welch(x, rate: 'float' = 4096.0, segment_s: 'float | None' = None, *, overlap: 'float' = 0.5, window: 'str' = 'hann', average: 'str' = 'mean') -> 'np.ndarray'` (実装を直接呼ぶなら `import gwsearch; gwsearch.psd_welch(x, rate: 'float' = 4096.0, segment_s: 'float | None' = None, *, overlap: 'float' = 0.5, window: 'str' = 'hann', average: 'str' = 'mean') -> 'np.ndarray'`、台帳から引くなら `ops1d.get("psd_welch")`)

## 使い方

Welch 法の片側 PSD を ``pairs``(周波数 [Hz], S [1/Hz])で返す。

Parameters
----------
x : array_like
    時系列(1-D)。
rate : float
    標本化周波数 fs [Hz]。
segment_s : float or None
    1 区間の長さ [s] (周波数分解能 = 1/segment_s)。``None`` なら **4 s と信号長の 1/8 の短い方**
    (重力波の慣例 4 s、短い信号でも 8 区間は取る)。信号より長ければ信号全長に切り詰める。
overlap : float
    区間の重なり(0 ≤ overlap < 1)。
window : str
    窓("hann" / "hamming" / "blackman" / "boxcar"、scipy の名前)。
average : str
    区間の平均 "mean" か "median"(グリッチに強い。scipy は median の偏り補正つき)。

Returns
-------
numpy.ndarray
    ``(n_freq, 2)``。白色ガウス雑音(分散 σ²)で ``S = 2σ²/fs``(片側)。

Notes
-----
重力波の標準手順(GWOSC の例題)と同じ ``scaling="density"``。分解能 1/segment_s より
細い線(60 Hz の電源線など)は幅がこの分解能に広がる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_gw_detector_pseudo_simulation](../../../../examples/poc_gw_detector_pseudo_simulation.py) — `py -3.11 examples/poc_gw_detector_pseudo_simulation.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[whiten_by_psd](whiten_by_psd.md) · [chirp_mass_from_track](chirp_mass_from_track.md) · [matched_filter_snr](matched_filter_snr.md) · [optimal_snr](optimal_snr.md)

## 同カテゴリ(`matched`)

[whiten_by_psd](whiten_by_psd.md) · [chirp_newtonian](chirp_newtonian.md) · [chirp_mass_from_track](chirp_mass_from_track.md) · [matched_filter_snr](matched_filter_snr.md) · [optimal_snr](optimal_snr.md) · [coincidence_delay](coincidence_delay.md)

---
*Provenance: gwsearch.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
