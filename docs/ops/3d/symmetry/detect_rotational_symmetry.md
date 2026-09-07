---
op: detect_rotational_symmetry
dim: 3d
category: symmetry
in: points
out: primitive
examples: [rotational_symmetry_fold, symmetry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# detect_rotational_symmetry — 3D `symmetry` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.detect_rotational_symmetry(points, orders=(2, 3, 4, 6, 8))` (実装を直接呼ぶなら `import symmetry3d; symmetry3d.detect_rotational_symmetry(points, orders=(2, 3, 4, 6, 8))`、台帳から引くなら `ops3d.get("detect_rotational_symmetry")`)

## 使い方

PCA 主軸を候補軸として最良の回転対称(軸 × order)を選ぶ。

→ dict{axis_point, axis_dir, order, score, table, margin}。
score が小さいほど対称。

★ ``margin``(2 位との差)を必ず併読すること。理由は
:func:`detect_reflection_symmetry` と同じ —— 候補が団子なら選択はくじ引きで、
そのとき先に潰れるのは score ではなく margin である。回転対称は候補が
3 軸 x order なので**同じ軸の別 order が 2 位に来る**ことも多く、その場合の
margin の小ささは「order が決まらない」を意味する(軸は決まっている)。
``table`` に全候補が入っているので、軸だけ固定して order を見直せる。

★ 候補は PCA の 3 軸だけ。真の対称軸が主軸のどれとも一致しない形では
見つからず、しかも黙って最良を返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [rotational_symmetry_fold](../../../../examples_3d/rotational_symmetry_fold.py) — `py -3.11 examples_3d/rotational_symmetry_fold.py`
- [symmetry](../../../../examples_3d/symmetry.py) — `py -3.11 examples_3d/symmetry.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [intersect_line_plane](../geometry/intersect_line_plane.md)

## 同カテゴリ(`symmetry`)

[detect_reflection_symmetry](detect_reflection_symmetry.md) · [reflect_points](reflect_points.md) · [reflection_symmetry_score](reflection_symmetry_score.md)

---
*Provenance: symmetry3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
