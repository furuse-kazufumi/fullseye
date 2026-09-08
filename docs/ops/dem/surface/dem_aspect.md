---
op: dem_aspect
dim: dem
category: surface
in: depth
out: image2d
examples: [poc_dem_terrain, poc_geodetic_height_frames]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_aspect — DEM `surface` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_aspect(dem, cell_size, method='horn', flat_tol=1e-12)` (実装を直接呼ぶなら `import demops; demops.dem_aspect(dem, cell_size, method='horn', flat_tol=1e-12)`、台帳から引くなら `opsdem.get("dem_aspect")`)

## 使い方

斜面方位 [度]。**北 0 度・東回り**。平坦なセルは :data:`ASPECT_FLAT`。

平坦を 0 で返さないのは、0 が「北向き斜面」を意味してしまうため
—— 区別できない値を返すのは、例外を出さずに間違える典型。

手順: ``dem_slope`` と同じ 3x3 勾配 ``(dz/dx, dz/dy)`` を取り、**下り勾配**の
向き ``atan2(-dz/dx, -dz/dy)`` を度にして ``[0, 360)`` に折り返す。行 0 が北・
列が増える向きが東という前提で、北 0 / 東 90 / 南 180 / 西 270。
行 0 が南の格子(上下反転した配列)を渡すと南北が入れ替わり、**例外は出ない**。

- ``dem``, ``cell_size``, ``method``: ``dem_slope`` と同じ契約(3x3 以上、``nan``
  で欠測、番兵値は拒否、``cell_size`` は正の [m])。
- ``flat_tol``: 勾配の大きさ ``hypot(dz/dx, dz/dy)`` [m/m] がこれ以下なら平坦と
  みなし ``ASPECT_FLAT``(= -1.0)を返す。既定 1e-12 は「数値的に厳密に平坦」だけ。
  整数標高の平地でも微小勾配で方位が付くことがあるので、意味のある閾
  (例 1e-3)を明示するとよい。
- 返り値: ``(H, W)`` float64。``[0, 360)`` または ``-1.0``。``nan`` セルの周りは ``nan``。
- 方位のヒストグラムや平均を取るときは ``-1`` を先に除く(``out >= 0``)。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dem_terrain](../../../../examples/poc_dem_terrain.py) — `py -3.11 examples/poc_dem_terrain.py`
- [poc_geodetic_height_frames](../../../../examples/poc_geodetic_height_frames.py) — `py -3.11 examples/poc_geodetic_height_frames.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

—

## 同カテゴリ(`surface`)

[dem_slope](dem_slope.md) · [dem_curvature](dem_curvature.md) · [dem_roughness](dem_roughness.md) · [dem_tpi](dem_tpi.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
