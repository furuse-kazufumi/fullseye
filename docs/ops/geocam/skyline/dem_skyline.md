---
op: dem_skyline
dim: geocam
category: skyline
in: depth
out: table
examples: [poc_public_camera_heading]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# dem_skyline — GEOCAM `skyline` op

- **データ種**: `depth` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_skyline(dem, cell_size, observer_rc, eye_height=1.5, az_step_deg=1.0, max_distance=None, earth_curvature=True)` (実装を直接呼ぶなら `import geocam; geocam.dem_skyline(dem, cell_size, observer_rc, eye_height=1.5, az_step_deg=1.0, max_distance=None, earth_curvature=True)`、台帳から引くなら `opsgeocam.get("dem_skyline")`)

## 使い方

DEM の 1 点から見た**全方位のスカイライン**(方位ごとの地平線仰角)→ table。

``dem_horizon_angle`` は「全セル × 1 方位」、これは「1 点 × 全方位」—— 固定カメラの向きを
決めるのに要るのは後者。各方位へ ``cell_size / 2`` 刻みで視線を進め(標高は双一次補間)、
``atan((z_j − z_0 − drop(d)) / d)`` の最大値をその方位の仰角にする。``drop(d) = d² / (2 R_eff)``
は地球の丸みと大気屈折(有効半径 R / (1 − 0.13))で遠くの山が沈む分。視線が DEM の外に
出たらそこで止める(``max_distance`` でも止まる)。**DEM の外側**は「DEM の最低標高の平面が
地平線まで続く」と仮定し、仰角の下限を地平線の沈み ``−sqrt(2 h / R_eff)``(h = 観測点の
最低標高からの高さ)にする —— 有限の DEM の端でたまたま低い点を見て、実際には地球の丸みで
見えない −7° のような「穴」を空にしないため(``horizon_dip_deg`` に返す)。

Args:
    dem: (H, W) 標高 [m]。行 0 が北端。
    cell_size: [m/セル]。
    observer_rc: 観測点 (row, col)。float 可(セルの中に立てる)。
    eye_height: 地面からのカメラ高さ [m]。
    az_step_deg: 方位の刻み [度]。
    max_distance: 視線の最大距離 [m] (None = DEM の端まで)。
    earth_curvature: False なら平らな地球。
Returns:
    table: ``azimuth_deg`` (M,) / ``elevation_deg`` (M,) / ``distance_m`` (M,)(仰角を決めた
    地点までの距離)/ ``observer_elevation_m`` / ``horizon_dip_deg`` / ``n``。方位は 0 以上
    360 未満、昇順。

## 詳しい使い方ガイド

- [geocam ファミリ ガイド](../guides/geocam.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_public_camera_heading](../../../../examples/poc_public_camera_heading.py) — `py -3.11 examples/poc_public_camera_heading.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_skyline_view](render_skyline_view.md) · [camera_orientation_from_skyline](../orientation/camera_orientation_from_skyline.md)

## 同カテゴリ(`skyline`)

[skyline_extract](skyline_extract.md) · [render_skyline_view](render_skyline_view.md)

---
*Provenance: geocam.py — GEOCAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
