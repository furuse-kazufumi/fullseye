---
op: volseq_cut_video
dim: live4d
category: series
in: volseq
out: video
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# volseq_cut_video — LIVE4D `series` op

- **データ種**: `volseq` → `video`
- **呼び出し**: `import fullseye as fs; fs.ledger.volseq_cut_video(volseq, plane: 'str' = 'xy', position: 'float' = 0.5) -> 'np.ndarray'` (実装を直接呼ぶなら `import live4d; live4d.volseq_cut_video(volseq, plane: 'str' = 'xy', position: 'float' = 0.5) -> 'np.ndarray'`、台帳から引くなら `opslive4d.get("volseq_cut_video")`)

## 使い方

体積時系列を 1 枚の断面で切った動画 ``(T, H, W)``(``video``)。

``plane`` は ``"xy"``(z を固定)/ ``"xz"``(y を固定)/ ``"yz"``(x を固定)、``position`` は固定する
軸に沿った相対位置 [0, 1]。断面は最大値投影と違って重なりを失わないが、断面から外れた動きは見えない。

## 詳しい使い方ガイド

- [live4d ファミリ ガイド](../guides/live4d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`video` を入力に取れる)

[video_interpolate_flow](../time/video_interpolate_flow.md)

## 同カテゴリ(`series`)

[volseq_mip_video](volseq_mip_video.md)

---
*Provenance: live4d.py — LIVE4D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
