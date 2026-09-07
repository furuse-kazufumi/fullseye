---
op: profile_camber
dim: profile
category: measure
in: pairs
out: pairs
examples: [profile_shape_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# profile_camber — PROFILE `measure` op

- **データ種**: `pairs` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.profile_camber(contour, n=101)` (実装を直接呼ぶなら `import profileops; profileops.profile_camber(contour, n=101)`、台帳から引くなら `opsprofile.get("profile_camber")`)

## 使い方

キャンバー線(上下面の中線)。返りは ``(n, 2)`` の ``(x, yc)``。

★**定義の差を承知で使うこと**。ここが返すのは「弦の各位置での上下面の中点」
で、NACA が翼型を**作るときに使う**キャンバー線(厚みを法線方向に載せる前の
中心線)とは厳密には別物です。加えて弦の取り方も違う —— 幾何的な弦は
「後縁の中点から最も遠い点」を前縁とするので、キャンバーのある翼では
生成座標の原点からわずかにずれ、弦が 0.1 度ほど傾きます。

実測(閉形式の最大キャンバー比 対 本 op の返り):

==========  ==========  ==========  ==========
翼型        閉形式      実測        比
==========  ==========  ==========  ==========
NACA 0012   0.0000      0.00001     ——
NACA 2412   0.0200      0.01882     0.94
NACA 4412   0.0400      0.03786     0.95
==========  ==========  ==========  ==========

**対称翼で 0 になること**は確認済み(0.00001)。有翼で 5-6 % 低く出るのは
上の定義差で、実装の誤りではありません。設計値と比べるときは、同じ定義で
測った基準形状(``profile_synth_naca4`` の出力)と比べること ——
:func:`profile_deviation` はまさにそれをします。

## 詳しい使い方ガイド

- [profile_metrology ファミリ ガイド](../guides/profile_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [profile_shape_inspection](../../../../examples/profile_shape_inspection.py) — `py -3.11 examples/profile_shape_inspection.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[profile_perturb](../synth/profile_perturb.md) · [profile_chord_frame](../frame/profile_chord_frame.md) · [profile_normalise](../frame/profile_normalise.md) · [profile_resample](../frame/profile_resample.md) · [profile_sides](profile_sides.md) · [profile_thickness](profile_thickness.md) · [profile_leading_edge_radius](profile_leading_edge_radius.md) · [profile_trailing_edge_gap](profile_trailing_edge_gap.md)

## 同カテゴリ(`measure`)

[profile_sides](profile_sides.md) · [profile_thickness](profile_thickness.md) · [profile_leading_edge_radius](profile_leading_edge_radius.md) · [profile_trailing_edge_gap](profile_trailing_edge_gap.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
