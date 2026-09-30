---
op: add_sign
dim: drive
category: roadjp
in: table
out: scalar
examples: [poc_driving_school, poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# add_sign — DRIVE `roadjp` op

- **データ種**: `table` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.add_sign(world: 'dict', kind: 'str', x: 'float', y: 'float', yaw: 'float', *, value=None, mount_height: 'float | None' = None, pole_radius: 'float' = 0.03, cell: 'int' = 4, size_px: 'int' = 128, font_path=None, side: 'float | None' = None) -> 'int'` (実装を直接呼ぶなら `import roadjp; roadjp.add_sign(world: 'dict', kind: 'str', x: 'float', y: 'float', yaw: 'float', *, value=None, mount_height: 'float | None' = None, pole_radius: 'float' = 0.03, cell: 'int' = 4, size_px: 'int' = 128, font_path=None, side: 'float | None' = None) -> 'int'`、台帳から引くなら `opsdrive.get("add_sign")`)

## 使い方

路側式の標識を立てる: 柱(円柱、灰、ラベル 6)+ 板(下端 = ``mount_height``、既定 1.8 m、ラベル 4)。

規約: **yaw の向きへ進んで来る車に板の面が向く**(法線 = (−cos yaw, −sin yaw))。実装は :func:`sign_mesh`(法線 −x)を
:func:`driveworld.place_mesh` で回すだけ。板は柱の手前(車の側)に ``pole_radius + 1 cm`` 離して付ける。
返り値 = 板の object 索引(``extra = {"kind", "value", "width", "height", "mount_height"}``)。柱は直前の別 object。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`
- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[road_eval](../long/road_eval.md) · [long_simulate](../long/long_simulate.md) · [stopping_distance_grade](../long/stopping_distance_grade.md) · [stop_line_plan](../long/stop_line_plan.md) · [hill_hold_brake_min](../long/hill_hold_brake_min.md) · [hill_start_rollback](../long/hill_start_rollback.md) · [hill_start_command](../long/hill_start_command.md) · [julian_day](../env/julian_day.md)

## 同カテゴリ(`roadjp`)

[sign_params](sign_params.md) · [sign_image](sign_image.md) · [plate_mesh_from_image](plate_mesh_from_image.md) · [sign_mesh](sign_mesh.md) · [signal_jp_mesh](signal_jp_mesh.md) · [add_signal_jp](add_signal_jp.md)

---
*Provenance: roadjp.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
