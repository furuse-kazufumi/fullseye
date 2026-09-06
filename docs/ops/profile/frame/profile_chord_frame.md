---
op: profile_chord_frame
dim: profile
category: frame
in: pairs
out: table
examples: [profile_frame_tour, profile_shape_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# profile_chord_frame — PROFILE `frame` op

- **データ種**: `pairs` → `table`
- **呼び出し**: `import profileops; profileops.profile_chord_frame(contour)` (または `opsprofile.get("profile_chord_frame")`)

## 使い方

弦(最も離れた 2 点)を見つける。返りは dict。

翼型の慣行どおり、**最も離れた 2 点**を前縁・後縁とみなす。どちらが前縁かは
**その点の近傍の曲率が大きいほう**で決める(前縁は丸く、後縁は尖る)。

Returns:
    dict: ``le`` / ``te``(座標)、``le_index`` / ``te_index``、
    ``chord``(長さ)、``angle_deg``(弦の向き)。

## 詳しい使い方ガイド

- [profile_metrology ファミリ ガイド](../guides/profile_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [profile_frame_tour](../../../../examples/profile_frame_tour.py) — `py -3.11 examples/profile_frame_tour.py`
- [profile_shape_inspection](../../../../examples/profile_shape_inspection.py) — `py -3.11 examples/profile_shape_inspection.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`frame`)

[profile_normalise](profile_normalise.md) · [profile_resample](profile_resample.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
