---
op: force_from_wrist_displacement
dim: drive
category: cutting
in: signal × signal × scalar
out: signal
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# force_from_wrist_displacement — DRIVE `cutting` op

- **データ種**: `signal × signal × scalar` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.force_from_wrist_displacement(z_meas_mm, z_cmd_mm, k_n_per_mm: 'float')` (実装を直接呼ぶなら `import cutting; cutting.force_from_wrist_displacement(z_meas_mm, z_cmd_mm, k_n_per_mm: 'float')`、台帳から引くなら `opsdrive.get("force_from_wrist_displacement")`)

## 使い方

柔らかい手首(縦のばね k、N/mm)なら押し力 F = k (z_meas − z_cmd): 刃が指令より上に残った分が力(N の配列)。

準静的の近似: 手首の慣性と減衰は入らない。減衰 c の手首を速さ v で下げると、空中での風袋引きに c·v が入り、刃が食材に
止められている間だけそれが抜ける —— 誤差の上限は c·v(PoC の --full で MuJoCo の拘束力と比べる)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_food_cutting_measure](../../../../examples/poc_food_cutting_measure.py) — `py -3.11 examples/poc_food_cutting_measure.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`cutting`)

[cutting_scene](cutting_scene.md) · [cutting_face_render](cutting_face_render.md) · [cutting_edge_render](cutting_edge_render.md) · [cutting_episode_synth](cutting_episode_synth.md) · [cutting_wrist_mjcf](cutting_wrist_mjcf.md) · [knife_edge_track](knife_edge_track.md) · [cut_depth_from_side](cut_depth_from_side.md) · [slice_thickness_profile](slice_thickness_profile.md)

---
*Provenance: cutting.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
