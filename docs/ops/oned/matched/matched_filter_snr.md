---
op: matched_filter_snr
dim: oned
category: matched
in: signal × signal × pairs
out: signal
examples: [poc_gw_detector_pseudo_simulation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# matched_filter_snr — ONED `matched` op

- **データ種**: `signal × signal × pairs` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.matched_filter_snr(data, template, psd, rate: 'float' = 4096.0, *, f_low_hz: 'float | None' = 20.0, f_high_hz: 'float | None' = None, template_ref_index: 'int | None' = None, taper_s: 'float' = 0.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import gwsearch; gwsearch.matched_filter_snr(data, template, psd, rate: 'float' = 4096.0, *, f_low_hz: 'float | None' = 20.0, f_high_hz: 'float | None' = None, template_ref_index: 'int | None' = None, taper_s: 'float' = 0.0) -> 'np.ndarray'`、台帳から引くなら `ops1d.get("matched_filter_snr")`)

## 使い方

整合フィルタの SNR 時系列 |ρ(t)|(位相で最大化)を ``signal`` で返す。

Parameters
----------
data : array_like
    観測時系列(1-D)。
template : array_like
    テンプレート(data 以下の長さ。末尾を 0 で埋めて同じ長さにする)。
psd : array_like
    雑音の片側 PSD の ``pairs``(``psd_welch``)。
rate : float
    標本化周波数 [Hz]。
f_low_hz, f_high_hz : float or None
    内積の帯域。
template_ref_index : int or None
    テンプレート内の「事象の時刻」の標本番号(None なら ``argmax |h|``)。返り値はこの分だけ
    回してあり、**|ρ| の山の標本番号 = data 内の事象の時刻**になる。
taper_s : float
    data の両端を余弦で 0 へ落とす長さ [s] (Tukey 窓の端)。実データの端の不連続が
    FFT の循環で全体に漏れるのを抑える(GWOSC の例題は 32 s に対し 2 s)。

Returns
-------
numpy.ndarray
    data と同じ長さの非負配列。``ρ(t) = ⟨d|h_t⟩/σ``、``⟨a|b⟩ = 4Re∫ÃB̃*/S df``、
    ``σ = optimal_snr``。位相は解析信号で最大化する(``|z|``)。テンプレートが data の外へ
    はみ出す時刻(先頭の ``ref`` 標本と末尾の ``len(template) − ref`` 標本)は循環の折り返し
    なので **0** にしてある(山の探索に混じらない)。

Notes
-----
白色ガウス雑音だけなら |ρ| の典型値は ~1.25(レイリー)、閾値 8 が重力波探索の慣例。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_gw_detector_pseudo_simulation](../../../../examples/poc_gw_detector_pseudo_simulation.py) — `py -3.11 examples/poc_gw_detector_pseudo_simulation.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](../function/create_funct_1d_array.md) · [create_funct_1d_pairs](../function/create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](../function/smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](../function/smooth_funct_1d_mean.md) · [derivate_funct_1d](../function/derivate_funct_1d.md) · [integrate_funct_1d](../function/integrate_funct_1d.md) · [zero_crossings_funct_1d](../function/zero_crossings_funct_1d.md) · [local_min_max_funct_1d](../function/local_min_max_funct_1d.md)

## 同カテゴリ(`matched`)

[psd_welch](psd_welch.md) · [whiten_by_psd](whiten_by_psd.md) · [chirp_newtonian](chirp_newtonian.md) · [chirp_mass_from_track](chirp_mass_from_track.md) · [optimal_snr](optimal_snr.md) · [coincidence_delay](coincidence_delay.md)

---
*Provenance: gwsearch.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
