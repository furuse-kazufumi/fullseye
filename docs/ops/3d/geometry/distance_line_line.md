---
op: distance_line_line
dim: 3d
category: geometry
in: primitive
out: measurement
examples: [geometry_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# distance_line_line — 3D `geometry` op

- **データ種**: `primitive` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.distance_line_line(p1, d1, p2, d2)` (実装を直接呼ぶなら `import match3d; match3d.distance_line_line(p1, d1, p2, d2)`、台帳から引くなら `ops3d.get("distance_line_line")`)

## 使い方

2 直線間距離(ねじれの位置=skew も可)。平行なら点-線距離に退避。

★これは**無限直線**の距離。手足・ロボットのリンク・配管のような**有限線分**に
使うと、離れているのに 0 が返ることがある(実測: (0,0,0)-(1,0,0) と
(5,0,0)-(6,0,0) で 0.0、真値 4.0)。線分どうしは
:func:`distance_segment_segment` を使うこと —— 安全距離の判定でここを取り違えると
**危険を過小評価する**側に外れる。

``n = d̂1 × d̂2`` を取り、``|n| < 1e-9``(平行)なら ``distance_point_line(p2, p1, d1)``、それ
以外は ``|(p2 − p1)·n̂|``(共通垂線の長さ)を float で返す。交わる直線では 0。
``p1, d1, p2, d2`` は数値の 2 または 3 ベクトル、次元の混在は ValueError。
2-D の非平行な直線は交わるので距離 0 のはずだが、``np.cross`` がスカラーになるため ``@`` が
失敗する(2-D は平行な場合しか通らない)。3-D で使うこと。単位は入力座標の単位。
用途: 2 本の軸(``fit_line_3d``)の同軸度、穴ピッチ。

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
