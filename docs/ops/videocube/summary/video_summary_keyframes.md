---
op: video_summary_keyframes
dim: videocube
category: summary
in: video
out: indices
examples: [poc_video_cube]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# video_summary_keyframes — VIDEOCUBE `summary` op

- **データ種**: `video` → `indices`
- **呼び出し**: `import fullseye as fs; fs.ledger.video_summary_keyframes(video, k: 'int' = 5, min_gap: 'int | None' = None, bins: 'int' = 32) -> 'np.ndarray'` (実装を直接呼ぶなら `import videocube; videocube.video_summary_keyframes(video, k: 'int' = 5, min_gap: 'int | None' = None, bins: 'int' = 32) -> 'np.ndarray'`、台帳から引くなら `opsvideocube.get("video_summary_keyframes")`)

## 使い方

代表フレームの添字 ``(k,)`` int64、昇順(``indices``)。

フレームごとの得点 = 動きの量(|I_t − I_{t−1}| の平均、[0, 1] に正規化)+ 場面の変化(ヒストグラムの
χ² 距離、正規化)。得点の高い順に、既に選んだフレームから ``min_gap``(既定 T // (2k))以上離れたものを
貪欲に ``k`` 枚選ぶ。T < k なら全フレーム。学習なしの「何かが起きたフレーム」であって、意味の要約ではない。

>>> idx = video_summary_keyframes(clip, k=4)
>>> thumbnails = clip[idx]

## 詳しい使い方ガイド

- [videocube ファミリ ガイド](../guides/videocube.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_video_cube](../../../../examples/poc_video_cube.py) — `py -3.11 examples/poc_video_cube.py`

## 型が繋がる次の op(`indices` を入力に取れる)

—

## 同カテゴリ(`summary`)

—

---
*Provenance: videocube.py — VIDEOCUBE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
