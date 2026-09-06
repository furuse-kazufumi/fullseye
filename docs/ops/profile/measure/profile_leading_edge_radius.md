---
op: profile_leading_edge_radius
dim: profile
category: measure
in: pairs
out: measurement
examples: [profile_shape_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# profile_leading_edge_radius — PROFILE `measure` op

- **データ種**: `pairs` → `measurement`
- **呼び出し**: `import profileops; profileops.profile_leading_edge_radius(contour, frac=0.001, n_fit=24)` (または `opsprofile.get("profile_leading_edge_radius")`)

## 使い方

前縁半径(翼弦比)。前縁近傍の点に円を当てはめる。

``frac`` は前縁から弦方向にどこまでを「前縁付近」とみなすか。**この値で
答えが変わる**。鼻先は円だが、少し離れると円ではないので、窓を広げると
系統的に**過大**になる。NACA 4 桁の閉形式 ``1.1019 * t^2`` と突き合わせた
実測(点数 4001 で生成):

==========  ==========  ==========  ==========  ==========
frac        NACA 0012   NACA 2412   NACA 0021   NACA 0008
==========  ==========  ==========  ==========  ==========
閉形式      0.01587     0.01587     0.04859     0.00705
0.001       0.01590     0.01594     0.04780     0.00730
0.005       0.01708     0.01716     0.04801     0.00870
0.01        0.01872     0.01880     0.04897     0.01042
0.03        0.02517     0.02526     0.05412     0.01688
==========  ==========  ==========  ==========  ==========

★ 既定は **0.001**。最初 0.03 を既定にしていて、閉形式の **1.6 倍**の値を
返していた(「1 % 以内」と docstring に書いたのは確かめる前の推測だった)。
厚い翼(0021)ほど鈍いので窓の影響が小さく、薄い翼(0008)ほど敏感。

実データのように点が疎な輪郭では、この窓に点が 5 つ入らないことがある ——
そのときは自動で等弧長に取り直してから当てはめる。

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

[profile_sides](profile_sides.md) · [profile_thickness](profile_thickness.md) · [profile_camber](profile_camber.md) · [profile_trailing_edge_gap](profile_trailing_edge_gap.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
