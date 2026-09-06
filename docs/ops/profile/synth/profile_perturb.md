---
op: profile_perturb
dim: profile
category: synth
in: pairs
out: pairs
examples: [profile_shape_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# profile_perturb — PROFILE `synth` op

- **データ種**: `pairs` → `pairs`
- **呼び出し**: `import profileops; profileops.profile_perturb(contour, kind='thicken', amount=0.001, extent=0.1, cycles=6.0)` (または `opsprofile.get("profile_perturb")`)

## 使い方

既知の量の欠陥を入れた輪郭を返す。:data:`PERTURB_KINDS`。

**これが無い形状検査は、静かに合格を出す**。0.001 翼弦の厚み増を入れて、
検出器がそれを 0.001 として返すかを確かめるために使う。

Args:
    contour: 元の輪郭。
    kind: 欠陥の種類。
    amount: 大きさ(翼弦比)。``"twist"`` だけは度。
    extent: ``"le_erosion"`` が及ぶ弦方向の範囲。
    cycles: ``"waviness"`` の波数。

## 詳しい使い方ガイド

- [profile_metrology ファミリ ガイド](../guides/profile_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [profile_shape_inspection](../../../../examples/profile_shape_inspection.py) — `py -3.11 examples/profile_shape_inspection.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[profile_chord_frame](../frame/profile_chord_frame.md) · [profile_normalise](../frame/profile_normalise.md) · [profile_resample](../frame/profile_resample.md) · [profile_sides](../measure/profile_sides.md) · [profile_thickness](../measure/profile_thickness.md) · [profile_camber](../measure/profile_camber.md) · [profile_leading_edge_radius](../measure/profile_leading_edge_radius.md) · [profile_trailing_edge_gap](../measure/profile_trailing_edge_gap.md)

## 同カテゴリ(`synth`)

[profile_synth_naca4](profile_synth_naca4.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
