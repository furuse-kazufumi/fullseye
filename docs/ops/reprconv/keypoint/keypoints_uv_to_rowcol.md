---
op: keypoints_uv_to_rowcol
dim: reprconv
category: keypoint
in: keypoints
out: keypoints
gpu: なし
examples: [poc_bga_ball_type_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# keypoints_uv_to_rowcol — REPRCONV `keypoint` op

- **データ種**: `keypoints` → `keypoints`
- **呼び出し**: `import fullseye as fs; fs.ledger.keypoints_uv_to_rowcol(keypoints)` (実装を直接呼ぶなら `import reprconv; reprconv.keypoints_uv_to_rowcol(keypoints)`、台帳から引くなら `opsreprconv.get("keypoints_uv_to_rowcol")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

像面の点 ``(u, v) = (col, row)`` → ``(row, col)``。:func:`keypoints_rowcol_to_uv` の逆向き。

Args:
    keypoints: (N, 2) の (u, v)。
Returns:
    (N, 2) float64 の (row, col)。
Raises:
    ValueError: (N, 2) でない / 非有限 / 空。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_bga_ball_type_roundtrip](../../../../examples/poc_bga_ball_type_roundtrip.py) — `py -3.11 examples/poc_bga_ball_type_roundtrip.py`

## 型が繋がる次の op(`keypoints` を入力に取れる)

[keypoints_uv_to_points](keypoints_uv_to_points.md) · [keypoints_to_image2d](keypoints_to_image2d.md) · [keypoints_rowcol_to_uv](keypoints_rowcol_to_uv.md)

## 同カテゴリ(`keypoint`)

[keypoints_uv_to_points](keypoints_uv_to_points.md) · [points_zyx_to_keypoints_uv](points_zyx_to_keypoints_uv.md) · [keypoints_to_image2d](keypoints_to_image2d.md) · [keypoints_from_image2d](keypoints_from_image2d.md) · [position_to_points](position_to_points.md) · [points_to_position](points_to_position.md) · [keypoints_rowcol_to_uv](keypoints_rowcol_to_uv.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
