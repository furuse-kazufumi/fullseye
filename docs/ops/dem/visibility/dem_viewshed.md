---
op: dem_viewshed
dim: dem
category: visibility
in: depth
out: image2d
examples: [dem_terrain_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_viewshed — DEM `visibility` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_viewshed(dem, cell_size, observer_rc, observer_height_m=1.7, target_height_m=0.0, max_distance_m=None)` (実装を直接呼ぶなら `import demops; demops.dem_viewshed(dem, cell_size, observer_rc, observer_height_m=1.7, target_height_m=0.0, max_distance_m=None)`、台帳から引くなら `opsdem.get("dem_viewshed")`)

## 使い方

1 点からの可視領域(1 = 見える)。視線が地形に遮られるかを判定する。

``observer_rc`` は ``(row, col)``。観測点自身は常に可視。

手順: 目の高さ ``eye = z[observer] + observer_height_m``。各セルへの視線を
``ceil(hypot(H, W))`` 等分し、途中の地形の仰角 ``(z_mid - eye) / d_mid`` が
目標の仰角 ``(z + target_height_m - eye) / d`` を上回るセルがあれば遮蔽(0)。
途中の点は最近傍セルに丸めるので、斜めの視線は格子誤差を含む。
**地球の曲率と大気屈折は入れない**(数 km 超では別途補正する)。

- ``dem``: ``(H, W)`` [m]、3x3 以上、番兵値は拒否(``dem_slope`` と同じ契約)。
  ``nan`` セルは比較が偽になるため**遮蔽にも被遮蔽にもならず 1 のまま**残る。
- ``cell_size``: [m]、正。距離判定に使う。
- ``observer_rc``: 格子内の ``(row, col)`` 整数。外や pair でないものは ``ValueError``。
- ``observer_height_m`` / ``target_height_m``: 地面からの高さ [m]。既定は目の高さ
  1.7 m と地表 0 m。鉄塔からの可視域なら ``observer_height_m`` を上げる。
- ``max_distance_m``: これより遠いセルは 0(省略時は無制限)。
- 返り値: ``(H, W)`` float64 の 1 / 0。観測点は常に 1。
- 計算量: 格子全体 × ``ceil(hypot(H, W))`` 回のベクトル演算。

``dem_horizon_angle`` / ``dem_sky_view_factor`` は逆に「各セルから空がどれだけ
見えるか」を出す。

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

## 同カテゴリ(`visibility`)

[dem_horizon_angle](dem_horizon_angle.md) · [dem_sky_view_factor](dem_sky_view_factor.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
