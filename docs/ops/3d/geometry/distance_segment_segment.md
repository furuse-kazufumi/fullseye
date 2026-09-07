---
op: distance_segment_segment
dim: 3d
category: geometry
in: primitive
out: measurement
examples: [geometry_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# distance_segment_segment — 3D `geometry` op

- **データ種**: `primitive` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.distance_segment_segment(p0, p1, q0, q1)` (実装を直接呼ぶなら `import match3d; match3d.distance_segment_segment(p0, p1, q0, q1)`、台帳から引くなら `ops3d.get("distance_segment_segment")`)
- **台帳経由の戻り値**: `fullseye.ledger.distance_segment_segment(...)` は**宣言 out 型 `measurement` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.distance_segment_segment.raw(...)`、または `match3d.distance_segment_segment` を直接呼ぶ。

## 使い方

**有限線分**どうしの最短距離と、その最近接点の対。→ ``(distance, cp, cq)``。

``distance_line_line`` は**無限直線**の距離なので、離れた 2 線分に 0 を返すことが
ある(実測: (0,0,0)-(1,0,0) と (5,0,0)-(6,0,0) に対し 0.0、真値は 4.0)。手足・
ロボットのリンク・配管・工具はどれも**有限**なので、安全距離や干渉判定に
無限直線版を使うと**危険を過小評価する**(`poc_safety_clearance` の実測では
同じ 2 本に対し 87.6 % の過小評価)。

Args:
    p0, p1: 線分 1 の端点 ``(3,)``。``p0 == p1`` なら点として扱う。
    q0, q1: 線分 2 の端点 ``(3,)``。

Returns:
    ``(distance, cp, cq)``: 最短距離 float と、線分 1 側・線分 2 側の最近接点
    ``(3,)``。``distance == 0`` は 2 線分が交差(または接触)しているとき。

    ★台帳経由(``fullseye.ledger.distance_segment_segment``)は宣言 out 型の
    ``distance`` だけを返す。最近接点も要るときは
    ``fullseye.ledger.distance_segment_segment.raw(...)``。

Raises:
    ValueError: 端点が ``(3,)`` に直せない、または非有限のとき。

平行・退化(点に潰れた線分)も分岐で正しく扱う(Ericson, *Real-Time Collision
Detection*, §5.1.9 の clamped closest-point 法)。**カプセル**(芯線 + 半径)
どうしの距離は ``distance - r1 - r2``、干渉は それが負になること。

Reference (public): C. Ericson, *Real-Time Collision Detection*, Morgan Kaufmann
2005, §5.1.9 "Closest Points of Two Line Segments".

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geometry_metrology](../../../../examples_3d/geometry_metrology.py) — `py -3.11 examples_3d/geometry_metrology.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`geometry`)

[line_from_2points](line_from_2points.md) · [plane_from_3points](plane_from_3points.md) · [angle_3points](angle_3points.md) · [angle_between_lines](angle_between_lines.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
