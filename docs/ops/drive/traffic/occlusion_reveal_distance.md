---
op: occlusion_reveal_distance
dim: drive
category: traffic
in: any
out: scalar
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# occlusion_reveal_distance — DRIVE `traffic` op

- **データ種**: `any` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.occlusion_reveal_distance(ego_xy, ego_heading: 'float', parked_box, emerge_xy) -> 'float'` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.occlusion_reveal_distance(ego_xy, ego_heading: 'float', parked_box, emerge_xy) -> 'float'`、台帳から引くなら `opsdrive.get("occlusion_reveal_distance")`)

## 使い方

路肩駐車車両(向きつきの箱)の陰にある点 ``emerge_xy`` が、自車の目から **初めて見える** ときの縦距離。

自車の目は p(s) = ego_xy + s h(h = (cos ψ, sin ψ)、s ≥ 0 = 前進量)を動く。視線 = 線分 p(s) → e が箱の内部を
通らなければ見える。箱は凸なので「見えない s」は区間になり、その端は **視線が箱の角をかすめる** か、進路が箱の辺を
横切る所。各角 c について直線 e + λ(c − e) と進路の交点 s_c を 2×2 の連立で解き(閉形式)、候補 {0, s_c, 進路と辺の
交点} の小さい順に見えるかを調べ、最初に見える s* で d = h · (e − p(s*)) を返す。

軸平行の例(進路 y = 0、+x 向き、陰を作る角 c、e は箱の向こう): d = (e_x − c_x) · e_y / (e_y − c_y)。

``parked_box`` = (cx, cy, length, width, yaw)(中心・全長・全幅・向き)。最初から見えていれば s* = 0 の縦距離、
どこまで進んでも見えない(e が箱の内部)なら ``inf``。d が負(見えた時には既に e を通り過ぎている)もそのまま返す。
角をかすめる視線は「見える」(箱を 1e-9 相対だけ縮めて判定し、浮動小数の揺れで判定が割れないようにする)。

**Raises** ``ValueError``: 形・非有限・寸法 ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`traffic`)

[idm_accel](idm_accel.md) · [idm_equilibrium_gap](idm_equilibrium_gap.md) · [idm_platoon_simulate](idm_platoon_simulate.md) · [driver_style](driver_style.md) · [lateral_wobble](lateral_wobble.md) · [ou_estimate](ou_estimate.md) · [social_force_step](social_force_step.md) · [pedestrian_crossing](pedestrian_crossing.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
