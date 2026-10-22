---
op: whiten_by_psd
dim: oned
category: matched
in: signal × pairs
out: signal
examples: [poc_gw_detector_pseudo_simulation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# whiten_by_psd — ONED `matched` op

- **データ種**: `signal × pairs` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.whiten_by_psd(x, psd, rate: 'float' = 4096.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import gwsearch; gwsearch.whiten_by_psd(x, psd, rate: 'float' = 4096.0) -> 'np.ndarray'`、台帳から引くなら `ops1d.get("whiten_by_psd")`)

## 使い方

雑音の PSD で割って白色化する(``x_w = irfft(rfft(x)·√(2Δt/S(f)))``)。

Parameters
----------
x : array_like
    時系列(1-D)。
psd : array_like
    片側 PSD の ``pairs``(``psd_welch`` の返り)。rfft の格子へ log 補間する。
rate : float
    標本化周波数 [Hz]。

Returns
-------
numpy.ndarray
    白色化した時系列(x と同じ長さ)。雑音がこの PSD に従うガウス過程なら**分散 1**。

Notes
-----
端の数区間は FFT の循環のため乱れる(重力波の実データでは Tukey 窓で落とすのが慣例)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_gw_detector_pseudo_simulation](../../../../examples/poc_gw_detector_pseudo_simulation.py) — `py -3.11 examples/poc_gw_detector_pseudo_simulation.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](../function/create_funct_1d_array.md) · [create_funct_1d_pairs](../function/create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](../function/smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](../function/smooth_funct_1d_mean.md) · [derivate_funct_1d](../function/derivate_funct_1d.md) · [integrate_funct_1d](../function/integrate_funct_1d.md) · [zero_crossings_funct_1d](../function/zero_crossings_funct_1d.md) · [local_min_max_funct_1d](../function/local_min_max_funct_1d.md)

## 同カテゴリ(`matched`)

[psd_welch](psd_welch.md) · [chirp_newtonian](chirp_newtonian.md) · [chirp_mass_from_track](chirp_mass_from_track.md) · [matched_filter_snr](matched_filter_snr.md) · [optimal_snr](optimal_snr.md) · [coincidence_delay](coincidence_delay.md)

---
*Provenance: gwsearch.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
