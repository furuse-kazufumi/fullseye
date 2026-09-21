---
op: volseq_magnify_motion
dim: live4d
category: time
in: volseq
out: volseq
examples: [poc_live4d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# volseq_magnify_motion — LIVE4D `time` op

- **データ種**: `volseq` → `volseq`
- **呼び出し**: `import fullseye as fs; fs.ledger.volseq_magnify_motion(volseq, alpha: 'float' = 10.0, f_lo: 'float' = 0.05, f_hi: 'float' = 0.4, fps: 'float' = 1.0, sigma: 'float' = 0.5) -> 'np.ndarray'` (実装を直接呼ぶなら `import live4d; live4d.volseq_magnify_motion(volseq, alpha: 'float' = 10.0, f_lo: 'float' = 0.05, f_hi: 'float' = 0.4, fps: 'float' = 1.0, sigma: 'float' = 0.5) -> 'np.ndarray'`、台帳から引くなら `opslive4d.get("volseq_magnify_motion")`)

## 使い方

体積時系列の**帯域内の微小な動きを alpha 倍**にする(``volseq``、Eulerian の線形拡大の 3 次元版)。

Wu et al.(SIGGRAPH 2012)の線形 Eulerian: 各体積を空間ガウス(``sigma``)で平滑化した層を、時間方向に
帯域通過(``[f_lo, f_hi]`` Hz、``fps`` は体積のフレームレート、FFT の理想帯域)して ``alpha − 1`` 倍を
元に足し戻す。並進 δ の像 ``I(x − δ(t))`` を 1 次で展開すると帯域内の時間変化は ``−δ · ∇I`` なので、
足し戻した結果の変位は ``alpha · δ``(``alpha`` は変位の倍率: 1 で恒等、0 で帯域内の動きを消す)。
成り立つのは **小さな動き**だけ —— 目安は ``alpha · δ < λ / 8``(λ は平滑化後の空間波長 ≈ 4·sigma)。
それを超えると像が壊れる(増幅でなく歪み)。雑音も同じ倍率で増幅される(SNR は良くならない)。

>>> s = volseq_synth_beating((16, 24, 24), n_frames=24, period=8.0, amplitude=0.1)
>>> volseq_magnify_motion(s, alpha=8.0, f_lo=0.08, f_hi=0.2, fps=1.0).shape
(24, 16, 24, 24)

## 詳しい使い方ガイド

- [live4d ファミリ ガイド](../guides/live4d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_live4d](../../../../examples/poc_live4d.py) — `py -3.11 examples/poc_live4d.py`

## 型が繋がる次の op(`volseq` を入力に取れる)

[volseq_mip_video](../series/volseq_mip_video.md) · [volseq_cut_video](../series/volseq_cut_video.md) · [volseq_speed](../flow/volseq_speed.md) · [volseq_pathline_render](../flow/volseq_pathline_render.md) · [volseq_pathline_orbit](../flow/volseq_pathline_orbit.md) · [volseq_interpolate_flow](volseq_interpolate_flow.md) · [volseq_render_orbit](../render/volseq_render_orbit.md) · [focus_sweep_height_video](../render/focus_sweep_height_video.md)

## 同カテゴリ(`time`)

[video_interpolate_flow](video_interpolate_flow.md) · [volseq_interpolate_flow](volseq_interpolate_flow.md)

---
*Provenance: live4d.py — LIVE4D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
