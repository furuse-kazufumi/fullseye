---
op: pl_groove_visibility
dim: generative
category: pl
in: 
out: table
examples: [poc_si_wafer_pl_defect_visibility]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# pl_groove_visibility — GENERATIVE `pl` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.pl_groove_visibility(width_px: 'float' = 3.0, diffusion_length_px: 'float' = 8.0, *, sink_velocity: 'float' = 0.0, noise_rel: 'float' = 0.01, cnr_min: 'float' = 1.0) -> 'dict'` (実装を直接呼ぶなら `import pl; pl.pl_groove_visibility(width_px: 'float' = 3.0, diffusion_length_px: 'float' = 8.0, *, sink_velocity: 'float' = 0.0, noise_rel: 'float' = 0.01, cnr_min: 'float' = 1.0) -> 'dict'`、台帳から引くなら `opsgenerative.get("pl_groove_visibility")`)

## 使い方

溝の幅・拡散長・雑音から、影の溝と沈みの溝のコントラストと CNR を閉形式で返す(``table``)。

Parameters
----------
width_px : float
    溝の幅 w[px]。
diffusion_length_px : float
    拡散長 L[px]。
sink_velocity : float
    沈みの溝の再結合速度 ``s = S·px/D``(無次元、1 画素あたり)。0 なら沈みの項は 0。
noise_rel : float
    像の雑音 σ(地 1 に対する相対値)。CNR = コントラスト / σ。
cnr_min : float
    「見える」とする CNR の下限(既定 1 = 雑音と同じ深さ)。

Returns
-------
dict
    ``contrast_shadow``(連続 ``1 − e^{−w/2L}``)/ ``contrast_shadow_grid``(w が奇数の
    整数なら格子の厳密値、そうでなければ ``None``)/ ``contrast_sink``(``sL/(sL+2)``)/
    ``fwhm_shadow_px`` / ``fwhm_sink_px``(``2L·ln2``)/ ``cnr_shadow`` / ``cnr_sink`` /
    ``visible_shadow`` / ``visible_sink`` / ``L_star_shadow_px``(この L **より長いと**
    影は CNR < cnr_min で消える)/ ``L_star_sink_px``(この L **より短いと**沈みは
    消える。``sink_velocity = 0`` か ``cnr_min·noise_rel ≥ 1`` なら境界が無いので
    ``None`` = どの L でも見えない)/ ``deficit_shadow_px``(影の欠け量の積分 = w、
    L によらない)。

Notes
-----
影は ``w ≪ L`` で ``≈ w/2L`` と消え、沈みは L と共に深く広くなる。欠陥の種類で
向きが逆なので、「拡散長が長いほど欠陥が隠れる」は影にだけ当てはまる。

Examples
--------
>>> t = pl_groove_visibility(2.0, 20.0, sink_velocity=0.5, noise_rel=0.02)
>>> round(t["contrast_shadow"], 4)
0.0488
>>> round(t["contrast_sink"], 4)
0.8333
>>> t["visible_shadow"], t["visible_sink"]
(True, True)

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_si_wafer_pl_defect_visibility](../../../../examples/poc_si_wafer_pl_defect_visibility.py) — `py -3.11 examples/poc_si_wafer_pl_defect_visibility.py`

## 型が繋がる次の op(`table` を入力に取れる)

[perpetual_step](../stream/perpetual_step.md) · [perpetual_render](../stream/perpetual_render.md)

## 同カテゴリ(`pl`)

[pl_diffusion_psf](pl_diffusion_psf.md) · [pl_image_simulate](pl_image_simulate.md)

---
*Provenance: pl.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
