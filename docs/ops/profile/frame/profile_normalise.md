---
op: profile_normalise
dim: profile
category: frame
in: pairs
out: pairs
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# profile_normalise — PROFILE `frame` op

- **データ種**: `pairs` → `pairs`
- **呼び出し**: `import profileops; profileops.profile_normalise(contour)` (または `opsprofile.get("profile_normalise")`)

## 使い方

弦長 1・前縁が原点・弦が +x になるよう回転と並進で正規化する。

**スケールは弦長でしか変えない**(形を歪めない)。返りは正規化した輪郭。

## 詳しい使い方ガイド

- [profile_metrology ファミリ ガイド](../guides/profile_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`pairs` を入力に取れる)

[profile_perturb](../synth/profile_perturb.md) · [profile_chord_frame](profile_chord_frame.md) · [profile_resample](profile_resample.md) · [profile_sides](../measure/profile_sides.md) · [profile_thickness](../measure/profile_thickness.md) · [profile_camber](../measure/profile_camber.md) · [profile_leading_edge_radius](../measure/profile_leading_edge_radius.md) · [profile_trailing_edge_gap](../measure/profile_trailing_edge_gap.md)

## 同カテゴリ(`frame`)

[profile_chord_frame](profile_chord_frame.md) · [profile_resample](profile_resample.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
