---
op: jpeg_ghost_quality
dim: imgforensics
category: compression
in: images
out: image2d
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# jpeg_ghost_quality — IMGFORENSICS `compression` op

- **データ種**: `images` → `image2d`
- **呼び出し**: `import imgforensics; imgforensics.jpeg_ghost_quality(ghosts, qualities=None) -> 'np.ndarray'` (または `opsimgforensics.get("jpeg_ghost_quality")`)

## 使い方

ゴースト地図の列 → 画素ごとに **残差が最小になる品質** の地図。``image2d``。

``qualities`` を省くと :func:`jpeg_ghost_map` の既定(40..95 step 5)を仮定する
—— **枚数が合わなければ :class:`ValueError`**(添字と品質がずれた地図を返さない)。

返りは品質そのものを画素値に持つ ``(H, W)`` なので、値域は [0, 1] ではない。
表示するときは正規化すること(この op は数値を返すのであって絵を返さない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[perceptual_hash](../hash/perceptual_hash.md) · [fingerprint_correlate](../sensor/fingerprint_correlate.md) · [error_level_map](error_level_map.md) · [jpeg_quality_estimate](jpeg_quality_estimate.md) · [jpeg_ghost_map](jpeg_ghost_map.md) · [noise_inconsistency_map](../noise/noise_inconsistency_map.md) · [copy_move_regions](../copy_move/copy_move_regions.md) · [watermark_embed](../watermark/watermark_embed.md)

## 同カテゴリ(`compression`)

[error_level_map](error_level_map.md) · [jpeg_quality_estimate](jpeg_quality_estimate.md) · [jpeg_ghost_map](jpeg_ghost_map.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
