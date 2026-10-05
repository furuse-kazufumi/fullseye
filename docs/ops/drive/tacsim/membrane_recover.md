---
op: membrane_recover
dim: drive
category: tacsim
in: rgb × matrix × scalar
out: table
examples: [poc_peg_insertion_tactile, poc_tacsim_elastic_membrane]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# membrane_recover — DRIVE `tacsim` op

- **データ種**: `rgb × matrix × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.membrane_recover(rgb, lights, pitch: 'float', ambient: 'float' = 0.0, albedo: 'float' = 1.0) -> 'dict'` (実装を直接呼ぶなら `import tacsim; tacsim.membrane_recover(rgb, lights, pitch: 'float', ambient: 'float' = 0.0, albedo: 'float' = 1.0) -> 'dict'`、台帳から引くなら `opsdrive.get("membrane_recover")`)

## 使い方

視触覚 RGB (H, W, 3) → 3 チャネルを 3 光源の像として :func:`photometric.photometric_stereo`(lit_only)で法線 →
:func:`photometric.integrate_normals`(Frankot-Chellappa)で高さ(画素単位 × pitch = m)。

``ambient``・``albedo`` は較正値: 像から albedo·ambient を引いてから解く(合成 albedo·(N·L + ambient) の ambient 項を
Woodham の線形模型は持たないので、引かないと法線が z 側へ寄り、傾きが ambient/sin(仰角) ≈ 3.7 %(0.03/0.82)系統的に
小さく出る —— 実機の参照フレーム較正に当たる。試作で δ が 3.5 % 低かった原因)。
返り: ``normals``(H, W, 3)、``albedo``(H, W)、``height``(H, W)[m、平均 0 の相対値]、``pitch``。
**Raises** ``ValueError``: rgb が (H, W, 3) でない、pitch ≤ 0、ambient < 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`
- [poc_tacsim_elastic_membrane](../../../../examples/poc_tacsim_elastic_membrane.py) — `py -3.11 examples/poc_tacsim_elastic_membrane.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacsim`)

[combined_modulus](combined_modulus.md) · [hertz_sphere](hertz_sphere.md) · [hertz_force](hertz_force.md) · [hertz_cylinder](hertz_cylinder.md) · [hertz_surface_uz](hertz_surface_uz.md) · [hertz_pressure](hertz_pressure.md) · [membrane_indent_sphere](membrane_indent_sphere.md) · [membrane_indent_shape](membrane_indent_shape.md)

---
*Provenance: tacsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
