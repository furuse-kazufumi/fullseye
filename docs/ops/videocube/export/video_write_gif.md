---
op: video_write_gif
dim: videocube
category: export
in: rgbvideo
out: text
examples: [poc_video_cube]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# video_write_gif — VIDEOCUBE `export` op

- **データ種**: `rgbvideo` → `text`
- **呼び出し**: `import fullseye as fs; fs.ledger.video_write_gif(frames, path: 'str', fps: 'float' = 10.0) -> 'str'` (実装を直接呼ぶなら `import videocube; videocube.video_write_gif(frames, path: 'str', fps: 'float' = 10.0) -> 'str'`、台帳から引くなら `opsvideocube.get("video_write_gif")`)

## 使い方

フレーム列をアニメーション GIF に書く(``text`` = 書いたパス)。使い回しの出口。

``frames`` は灰の ``video`` (T, H, W) か色の ``rgbvideo`` (F, H, W, 3)。float は [0, 1] を 0..255 に、
整数はそのまま uint8 に(範囲外は切る)。**全フレームを保存する**(Pillow は前と同じ絵を 1 コマに
畳んで数を減らすので、``video.write_video`` の全コマ保存経路を使い、書いた後に枚数を読み戻して確かめる)。
Pillow が無ければ ImportError(optional 依存)。``path`` は ``.gif`` で終わること。

>>> video_write_gif(video_cube_orbit(clip, n_frames=24), "out/cube.gif", fps=12)
'out/cube.gif'

## 詳しい使い方ガイド

- [videocube ファミリ ガイド](../guides/videocube.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_video_cube](../../../../examples/poc_video_cube.py) — `py -3.11 examples/poc_video_cube.py`

## 型が繋がる次の op(`text` を入力に取れる)

—

## 同カテゴリ(`export`)

—

---
*Provenance: videocube.py — VIDEOCUBE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
