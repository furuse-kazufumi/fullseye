---
op: profile_trailing_edge_gap
dim: profile
category: measure
in: pairs
out: measurement
examples: [profile_shape_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# profile_trailing_edge_gap — PROFILE `measure` op

- **データ種**: `pairs` → `measurement`
- **呼び出し**: `import profileops; profileops.profile_trailing_edge_gap(contour, n=201)` (または `opsprofile.get("profile_trailing_edge_gap")`)

## 使い方

後縁の開き(翼弦比)。上面と下面の後縁端の距離。

NACA 4 桁の既定係数(-0.1015)は後縁を**わずかに開く**ので、0 にならないのが
正しい。閉じる係数(-0.1036)なら 0 に近づく。

## 詳しい使い方ガイド

- [profile_metrology ファミリ ガイド](../guides/profile_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [profile_shape_inspection](../../../../examples/profile_shape_inspection.py) — `py -3.11 examples/profile_shape_inspection.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`measure`)

[profile_sides](profile_sides.md) · [profile_thickness](profile_thickness.md) · [profile_camber](profile_camber.md) · [profile_leading_edge_radius](profile_leading_edge_radius.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
