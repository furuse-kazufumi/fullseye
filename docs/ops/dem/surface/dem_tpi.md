---
op: dem_tpi
dim: dem
category: surface
in: depth
out: image2d
examples: [dem_terrain_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_tpi — DEM `surface` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import demops; demops.dem_tpi(dem, cell_size=1.0)` (または `opsdem.get("dem_tpi")`)

## 使い方

地形位置指数 TPI —— 自セルと 8 近傍平均の差 [m]。正が尾根、負が谷。

式: ``tpi = z - mean(8 近傍の z)``(Weiss の TPI を 3x3 の最小近傍で取ったもの)。
縁は端の値を複製して埋める。近傍が 1 セル固定なので、**スケールは
``cell_size`` 1 つぶんに固定**で、より広い尾根/谷を見たいときは先に
``dem`` を粗くする(この op に半径の引数は無い)。

- ``dem``: ``(H, W)`` [m]、3x3 以上、実数、``inf`` 不可。欠測は ``nan``(番兵値
  ``<= -9000`` が ``nan`` 無しで入っていれば拒否)。``nan`` は 3x3 に伝播する。
- ``cell_size``: 結果には影響しない(差分に距離は入らない)が、単位が [m] である
  ことを呼び出し側に意識させるため受け取り、正の有限値かを検査する。
- 返り値: ``(H, W)`` float64 [m]。0 付近が斜面の途中、正が凸(尾根・頂)、
  負が凹(谷・窪地)。
- 失敗: ``ValueError``(形、番兵値、``cell_size``)。

``dem_roughness``(同じ近傍の RMS)と組み合わせると地形分類の特徴になる。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dem_terrain_analysis_tour](../../../../examples/dem_terrain_analysis_tour.py) — `py -3.11 examples/dem_terrain_analysis_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

—

## 同カテゴリ(`surface`)

[dem_slope](dem_slope.md) · [dem_aspect](dem_aspect.md) · [dem_curvature](dem_curvature.md) · [dem_roughness](dem_roughness.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
