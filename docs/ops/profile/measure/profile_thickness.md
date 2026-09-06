---
op: profile_thickness
dim: profile
category: measure
in: pairs
out: pairs
examples: [profile_shape_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# profile_thickness — PROFILE `measure` op

- **データ種**: `pairs` → `pairs`
- **呼び出し**: `import profileops; profileops.profile_thickness(contour, n=101)` (または `opsprofile.get("profile_thickness")`)

## 使い方

厚み分布 ``t(x)``。返りは ``(n, 2)`` の ``(x, t)``。

``pairs`` として返すので、``pairs_to_signal`` や ``plot_series`` へそのまま
渡せる。最大厚みとその位置は :func:`profile_thickness_stats` ではなく
返り値から取る(``t`` の最大 = 最大厚み比)。

## 詳しい使い方ガイド

- [profile_metrology ファミリ ガイド](../guides/profile_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [profile_shape_inspection](../../../../examples/profile_shape_inspection.py) — `py -3.11 examples/profile_shape_inspection.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[profile_perturb](../synth/profile_perturb.md) · [profile_chord_frame](../frame/profile_chord_frame.md) · [profile_normalise](../frame/profile_normalise.md) · [profile_resample](../frame/profile_resample.md) · [profile_sides](profile_sides.md) · [profile_camber](profile_camber.md) · [profile_leading_edge_radius](profile_leading_edge_radius.md) · [profile_trailing_edge_gap](profile_trailing_edge_gap.md)

## 同カテゴリ(`measure`)

[profile_sides](profile_sides.md) · [profile_camber](profile_camber.md) · [profile_leading_edge_radius](profile_leading_edge_radius.md) · [profile_trailing_edge_gap](profile_trailing_edge_gap.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
