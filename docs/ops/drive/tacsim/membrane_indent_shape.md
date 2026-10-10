---
op: membrane_indent_shape
dim: drive
category: tacsim
in: text × scalar
out: table
examples: [poc_tacsim_elastic_membrane]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# membrane_indent_shape — DRIVE `tacsim` op

- **データ種**: `text × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.membrane_indent_shape(shape: 'str', depth: 'float', n: 'int' = 128, fov: 'float' = 0.006, R: 'float' = 0.003, edge_deg: 'float' = 30.0, tip_radius: 'float' = 0.0003, size: 'float' = 0.002) -> 'dict'` (実装を直接呼ぶなら `import tacsim; tacsim.membrane_indent_shape(shape: 'str', depth: 'float', n: 'int' = 128, fov: 'float' = 0.006, R: 'float' = 0.003, edge_deg: 'float' = 30.0, tip_radius: 'float' = 0.0003, size: 'float' = 0.002) -> 'dict'`、台帳から引くなら `opsdrive.get("membrane_indent_shape")`)

## 使い方

既知形状の剛体を深さ ``depth`` だけ押し込んだゲル膜の高さ場を**幾何学的な追従**で作る: h = −max(0, depth − z_ind(x, y))。

弾性の裾(Hertz の外側解)は入れない —— 球は :func:`membrane_indent_sphere` が Hertz で正確に作るので、こちらは
円柱・直線エッジ・スタンプのように閉形式の裾が無い形を**同じ流儀で**並べるための道具。``shape``:
``"sphere"``(半径 R の球冠 z = R − √(R² − r²))、``"cylinder"``(軸は y、z = R − √(R² − x²))、``"edge"``(直線エッジ:
先端半径 tip_radius で丸めた角 edge_deg のくさび z = (√(x² + ρ²) − ρ) tan α)、``"stamp"``(一辺 size の "F" 字の平らなスタンプ、
外側は距離 × tan 60° で立ち上がる)。法線は :func:`photometric.surface_normals`(h/pitch)で取る(第 2 実装)。
返り: ``h``・``normals``・``pitch``・``X``・``Y``・``contact``(z_ind < depth)・``z_ind``。
**Raises** ``ValueError``: 未知の shape、depth ≤ 0、球・円柱で depth ≥ R。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_elastic_membrane](../../../../examples/poc_tacsim_elastic_membrane.py) — `py -3.11 examples/poc_tacsim_elastic_membrane.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacsim`)

[combined_modulus](combined_modulus.md) · [hertz_sphere](hertz_sphere.md) · [hertz_force](hertz_force.md) · [hertz_cylinder](hertz_cylinder.md) · [hertz_surface_uz](hertz_surface_uz.md) · [hertz_pressure](hertz_pressure.md) · [membrane_indent_sphere](membrane_indent_sphere.md) · [membrane_lights](membrane_lights.md)

---
*Provenance: tacsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
