---
op: profile_deviation
dim: profile
category: compare
in: pairs × pairs
out: table
examples: [profile_shape_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# profile_deviation — PROFILE `compare` op

- **データ種**: `pairs × pairs` → `table`
- **呼び出し**: `import profileops; profileops.profile_deviation(measured, reference, n=200, align='chord', oversample=8)` (または `opsprofile.get("profile_deviation")`)

## 使い方

設計形状からの**符号つき法線方向のずれ**。返りは dict。

正が「太い側(外向き)」、負が「痩せた側」。設計輪郭の外向き法線を基準にする。

Args:
    measured / reference: ``(N, 2)`` の閉輪郭。
    n: 比較に使う等弧長の点数(両方を取り直す)。
    align: :data:`ALIGN_MODES`。
    oversample: 相手側を基準の何倍の密度で取り直すか(既定 8)。
        折れ線が弧を切る分だけ偏差に床ができるので、**相手側は細かく**取る。
Returns:
    dict: ``points``(基準側の点、``(n, 2)``)、``deviation``(``(n,)``)、
    ``max`` / ``min`` / ``rms`` / ``mean``、``align``。

## 詳しい使い方ガイド

- [profile_metrology ファミリ ガイド](../guides/profile_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [profile_shape_inspection](../../../../examples/profile_shape_inspection.py) — `py -3.11 examples/profile_shape_inspection.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`compare`)

[profile_align](profile_align.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
