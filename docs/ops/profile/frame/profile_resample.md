---
op: profile_resample
dim: profile
category: frame
in: pairs
out: pairs
examples: [profile_frame_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# profile_resample — PROFILE `frame` op

- **データ種**: `pairs` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.profile_resample(contour, n=200, kind='arclength')` (実装を直接呼ぶなら `import profileops; profileops.profile_resample(contour, n=200, kind='arclength')`、台帳から引くなら `opsprofile.get("profile_resample")`)

## 使い方

輪郭を等間隔に取り直す。``kind`` は ``"arclength"`` のみ(現状)。

点の密度が場所で違うと、厚みやキャンバーの当てはめが密なところに引きずられる。
比較する 2 本は**同じ取り方**で取り直してから比べること。

## 詳しい使い方ガイド

- [profile_metrology ファミリ ガイド](../guides/profile_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [profile_frame_tour](../../../../examples/profile_frame_tour.py) — `py -3.11 examples/profile_frame_tour.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[profile_perturb](../synth/profile_perturb.md) · [profile_chord_frame](profile_chord_frame.md) · [profile_normalise](profile_normalise.md) · [profile_sides](../measure/profile_sides.md) · [profile_thickness](../measure/profile_thickness.md) · [profile_camber](../measure/profile_camber.md) · [profile_leading_edge_radius](../measure/profile_leading_edge_radius.md) · [profile_trailing_edge_gap](../measure/profile_trailing_edge_gap.md)

## 同カテゴリ(`frame`)

[profile_chord_frame](profile_chord_frame.md) · [profile_normalise](profile_normalise.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
