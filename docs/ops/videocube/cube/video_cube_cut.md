---
op: video_cube_cut
dim: videocube
category: cube
in: video
out: image2d
examples: [poc_video_cube]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# video_cube_cut — VIDEOCUBE `cube` op

- **データ種**: `video` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.video_cube_cut(video, plane: 'str' = 'xt', position: 'float' = 0.5) -> 'np.ndarray'` (実装を直接呼ぶなら `import videocube; videocube.video_cube_cut(video, plane: 'str' = 'xt', position: 'float' = 0.5) -> 'np.ndarray'`、台帳から引くなら `opsvideocube.get("video_cube_cut")`)

## 使い方

立方体の断面 1 枚(``image2d``)。``"xt"`` = 行 ``position`` のスリットスキャン (T, W)、``"yt"`` = 列の (T, H)、
``"xy"`` = 時刻 ``position`` のフレーム (H, W)。``position`` は [0, 1] の割合(行・列・時刻の何割目か)。

x–t 断面では、右へ動く物体は右下がりの筋、止まっている物体は縦の帯になる —— **速度が傾きとして読める**。

>>> streak = video_cube_cut(clip, "xt", position=0.4)      # 4 割目の行を横切ったものの記録

## 詳しい使い方ガイド

- [videocube ファミリ ガイド](../guides/videocube.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_video_cube](../../../../examples/poc_video_cube.py) — `py -3.11 examples/poc_video_cube.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

—

## 同カテゴリ(`cube`)

[video_spacetime_cube](video_spacetime_cube.md)

---
*Provenance: videocube.py — VIDEOCUBE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
