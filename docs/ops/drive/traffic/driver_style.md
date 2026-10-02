---
op: driver_style
dim: drive
category: traffic
in: 
out: table
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# driver_style — DRIVE `traffic` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.driver_style(kind: 'str', seed: 'Optional[int]' = None) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.driver_style(kind: 'str', seed: 'Optional[int]' = None) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("driver_style")`)

## 使い方

運転の癖 3 種("careful" / "normal" / "sloppy")の母数を返す。**値はすべて仮定**(出典なし)。

キー: IDM の ``v0, T, a, b, s0, delta``、``reaction_delay`` [s]、横ふらつき(OU 過程)の ``wobble_theta`` [1/s]
と ``wobble_sigma`` [m/√s] (定常の標準偏差は σ/sqrt(2θ) = 0.05 / 0.11 / 0.28 m)、``speed_noise``(希望速度の
相対むら)、``length`` 4.5 m(仮定)、``kind``。返り値はそのまま ``idm_platoon_simulate`` の 1 台分に渡せる。

``seed`` を与えると、主要な値に一様 ±10% の個人差を掛ける(``default_rng(seed)`` で決定的)。None なら名目値。
順序の性質(門): 名目値で careful の T・s0 が最大で反応遅れが最小、sloppy がその逆、ふらつきの定常 SD は
careful < normal < sloppy。

**Raises** ``ValueError``: 未知の kind。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`traffic`)

[idm_accel](idm_accel.md) · [idm_equilibrium_gap](idm_equilibrium_gap.md) · [idm_platoon_simulate](idm_platoon_simulate.md) · [lateral_wobble](lateral_wobble.md) · [ou_estimate](ou_estimate.md) · [social_force_step](social_force_step.md) · [pedestrian_crossing](pedestrian_crossing.md) · [occlusion_reveal_distance](occlusion_reveal_distance.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
