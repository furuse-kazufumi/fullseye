---
op: refine_peak_newton
dim: 3d
category: refine
in: score × position
out: position
gpu: true
examples: [refinement]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# refine_peak_newton — 3D `refine` op

- **データ種**: `score × position` → `position`
- **呼び出し**: `import match3d; match3d.refine_peak_newton(score, idx, device='cpu', max_iter=12, tol=0.0001)` (または `ops3d.get("refine_peak_newton")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

スコア/相関 volume の整数ピークを 3D Newton でサブボクセル精緻化する(反復最適化)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [refinement](../../../../examples_3d/refinement.py) — `py -3.11 examples_3d/refinement.py`

## 型が繋がる次の op(`position` を入力に取れる)

[refine_translation_lk](refine_translation_lk.md) · [refine_lm](refine_lm.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`refine`)

[refine_translation_lk](refine_translation_lk.md) · [refine_lm](refine_lm.md) · [refine_rotation_z](refine_rotation_z.md) · [icp_point2point_3d](icp_point2point_3d.md) · [icp_point2plane](icp_point2plane.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
