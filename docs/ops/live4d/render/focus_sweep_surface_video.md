---
op: focus_sweep_surface_video
dim: live4d
category: render
in: volseq
out: rgbvideo
examples: [poc_live4d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# focus_sweep_surface_video — LIVE4D `render` op

- **データ種**: `volseq` → `rgbvideo`
- **呼び出し**: `import fullseye as fs; fs.ledger.focus_sweep_surface_video(volseq, window: 'int' = 5, zscale: 'float' = 1.0, light=(0.4, 0.4, 0.8), ambient: 'float' = 0.25) -> 'np.ndarray'` (実装を直接呼ぶなら `import live4d; live4d.focus_sweep_surface_video(volseq, window: 'int' = 5, zscale: 'float' = 1.0, light=(0.4, 0.4, 0.8), ambient: 'float' = 0.25) -> 'np.ndarray'`、台帳から引くなら `opslive4d.get("focus_sweep_surface_video")`)

## 使い方

焦点掃引(各フレームが z の合焦スタック)の時系列から**陰影つきの高さ場の動画** ``(T, Y, X, 3)`` を
起こす(``rgbvideo``)。

高さは ``focus_sweep_height_video`` と同じ(合焦度の最大を放物線で副ボクセルに)。高さ場の勾配から
法線を作り(``zscale`` は z 1 枚の実長 / 画素の実長)、``light`` 方向のランバート陰影(``ambient`` を
下駄に)を**高さの色**(青 = 低い → 赤 = 高い)に掛ける。掃引の途中で対象が動くと層の整合が崩れて
高さが跳ぶ(その時刻だけ疑う)。

## 詳しい使い方ガイド

- [live4d ファミリ ガイド](../guides/live4d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_live4d](../../../../examples/poc_live4d.py) — `py -3.11 examples/poc_live4d.py`

## 型が繋がる次の op(`rgbvideo` を入力に取れる)

—

## 同カテゴリ(`render`)

[volseq_render_orbit](volseq_render_orbit.md) · [focus_sweep_height_video](focus_sweep_height_video.md)

---
*Provenance: live4d.py — LIVE4D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
