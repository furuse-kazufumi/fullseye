---
op: scoop_count
dim: drive
category: scoop
in: scalar × scalar × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# scoop_count — DRIVE `scoop` op

- **データ種**: `scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.scoop_count(volume: 'float', radius: 'float', packing: 'float', *, density: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.scoop_count(volume: 'float', radius: 'float', packing: 'float', *, density: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("scoop_count")`)

## 使い方

体積と充填率から粒の数 ``N = V ν / ((4/3) π r³)``(``density`` を与えれば質量 ``N m_p`` とかさ密度 ``ν ρ_p``)。

``packing`` ν は **較正値**(同じ粒・同じ測り方で、数の分かった 1 回から ``N v_p / V_img`` を取る): 側面の輪郭は
粒の外側の包絡なので、ν は充填そのものより小さく出る(包絡の分の体積を含む)。
**Raises** ``ValueError``: 体積 < 0、半径 ≤ 0、ν が (0, 1] の外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`scoop`)

[spoon_bowl_volume](spoon_bowl_volume.md) · [scoop_synth_side](scoop_synth_side.md) · [revolution_volume_side](revolution_volume_side.md) · [two_view_volume](two_view_volume.md) · [scoop_volume_read](scoop_volume_read.md) · [scoop_image_limit](scoop_image_limit.md) · [tilt_wedge_retained](tilt_wedge_retained.md) · [tilt_pour_rate](tilt_pour_rate.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
