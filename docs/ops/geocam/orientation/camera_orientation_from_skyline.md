---
op: camera_orientation_from_skyline
dim: geocam
category: orientation
in: signal × table
out: table
examples: [poc_public_camera_heading]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# camera_orientation_from_skyline — GEOCAM `orientation` op

- **データ種**: `signal × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.camera_orientation_from_skyline(skyline_rows, K, sky_table, yaw_step_deg=1.0, pitch_range=(-15.0, 15.0), roll_range=(-10.0, 10.0), coarse_step_deg=2.5)` (実装を直接呼ぶなら `import geocam; geocam.camera_orientation_from_skyline(skyline_rows, K, sky_table, yaw_step_deg=1.0, pitch_range=(-15.0, 15.0), roll_range=(-10.0, 10.0), coarse_step_deg=2.5)`、台帳から引くなら `opsgeocam.get("camera_orientation_from_skyline")`)

## 使い方

写真のスカイライン(列ごとの行)と DEM のスカイラインから (yaw, pitch, roll) を決める → table。

写真の境界画素 (u, v) をカメラ光線にし、仮の姿勢で世界へ回すと、各列は (方位, 仰角) の点になる。
その仰角と、DEM のスカイラインをその方位で引いた仰角の差の RMS が姿勢のコスト。yaw を
``yaw_step_deg`` 刻みで一周、pitch・roll を ``coarse_step_deg`` 刻みで格子探索し、最小の点から
Nelder–Mead で連続値に詰める(scipy)。Baatz ら 2012 のスカイライン照合を、位置既知・
1 台のカメラに絞った形。

**曖昧さを返す**: yaw ごとの最良コストの曲線(``yaw_profile_deg`` / ``yaw_profile_residual_deg``)
と、最良と 2 番目の谷の差 ``margin_deg``(2 番目の谷 = 最良から 20° 以上離れた最小)。平地・
対称な尾根・半円しか写らない写真では谷が複数あり、margin が小さい。**margin が
``coarse`` の残差程度なら向きは決まっていない**と読む(黙って 1 つを返さない: ``ambiguous``)。

Args:
    skyline_rows: (W,) ``skyline_extract`` の出力(列ごとの行)。
    K: (fx, fy, cx, cy)。
    sky_table: ``dem_skyline`` の出力。
    yaw_step_deg / coarse_step_deg: 粗い格子の刻み。pitch_range / roll_range: 探索範囲 [度]。
Returns:
    table: ``yaw_deg`` / ``pitch_deg`` / ``roll_deg`` / ``residual_deg``(仰角残差 RMS)/
    ``margin_deg`` / ``runner_up_yaw_deg`` / ``ambiguous``(bool)/ ``yaw_profile_deg`` (M,) /
    ``yaw_profile_residual_deg`` (M,) / ``n_columns``。

## 詳しい使い方ガイド

- [geocam ファミリ ガイド](../guides/geocam.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_public_camera_heading](../../../../examples/poc_public_camera_heading.py) — `py -3.11 examples/poc_public_camera_heading.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_skyline_view](../skyline/render_skyline_view.md)

## 同カテゴリ(`orientation`)

—

---
*Provenance: geocam.py — GEOCAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
