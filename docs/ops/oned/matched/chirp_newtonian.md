---
op: chirp_newtonian
dim: oned
category: matched
in: 
out: signal
examples: [poc_gw_detector_pseudo_simulation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# chirp_newtonian — ONED `matched` op

- **データ種**: `なし` → `signal`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.chirp_newtonian(mass1_msun: 'float' = 36.0, mass2_msun: 'float' = 29.0, rate: 'float' = 4096.0, duration_s: 'float' = 1.0, *, f_low_hz: 'float' = 20.0, distance_mpc: 'float' = 410.0, phase_rad: 'float' = 0.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import gwsearch; gwsearch.chirp_newtonian(mass1_msun: 'float' = 36.0, mass2_msun: 'float' = 29.0, rate: 'float' = 4096.0, duration_s: 'float' = 1.0, *, f_low_hz: 'float' = 20.0, distance_mpc: 'float' = 410.0, phase_rad: 'float' = 0.0) -> 'np.ndarray'`、台帳から引くなら `ops1d.get("chirp_newtonian")`)

## 使い方

ニュートン近似(0PN)のインスパイラル波形 h₊(t) を ``signal`` で返す(合体が配列の末尾)。

Parameters
----------
mass1_msun, mass2_msun : float
    成分質量 [M☉] (検出器系)。
rate : float
    標本化周波数 [Hz]。
duration_s : float
    配列の長さ [s]。f_low からの時間がこれより長ければ ``f_low`` を押し上げる。
f_low_hz : float
    波形を始める重力波周波数 [Hz] (軌道周波数の 2 倍)。
distance_mpc : float
    光度距離 [Mpc] (振幅だけに効く)。
phase_rad : float
    合体時の位相。

Returns
-------
numpy.ndarray
    ``round(duration_s·rate)`` 点。``f_ISCO = c³/(6^{3/2}πG(m₁+m₂))`` で止め、以降は 0。
    合体時刻は最後の標本(``index n−1``)。

Notes
-----
``f(τ) = (1/π)(5/256τ)^{3/8}(GM_c/c³)^{−5/8}``、``A = (4/d)(GM_c/c²)^{5/3}(πf/c)^{2/3}``、
``Φ(τ) = −2(5GM_c/c³)^{−5/8}τ^{5/8} + φ₀``。合体・リングダウンは含まない(これが
GW150914 の SNR を数値相対論の波形より小さく見積もる理由 —— PoC が数で示す)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_gw_detector_pseudo_simulation](../../../../examples/poc_gw_detector_pseudo_simulation.py) — `py -3.11 examples/poc_gw_detector_pseudo_simulation.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](../function/create_funct_1d_array.md) · [create_funct_1d_pairs](../function/create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](../function/smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](../function/smooth_funct_1d_mean.md) · [derivate_funct_1d](../function/derivate_funct_1d.md) · [integrate_funct_1d](../function/integrate_funct_1d.md) · [zero_crossings_funct_1d](../function/zero_crossings_funct_1d.md) · [local_min_max_funct_1d](../function/local_min_max_funct_1d.md)

## 同カテゴリ(`matched`)

[psd_welch](psd_welch.md) · [whiten_by_psd](whiten_by_psd.md) · [chirp_mass_from_track](chirp_mass_from_track.md) · [matched_filter_snr](matched_filter_snr.md) · [optimal_snr](optimal_snr.md) · [coincidence_delay](coincidence_delay.md)

---
*Provenance: gwsearch.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
