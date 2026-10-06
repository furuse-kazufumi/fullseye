---
op: rss_stopping_distance
dim: drive
category: rss
in: 
out: scalar
examples: [poc_driving_longitudinal]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# rss_stopping_distance — DRIVE `rss` op

- **データ種**: `なし` → `scalar`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.rss_stopping_distance(v: 'float', rho: 'float', accel: 'float', brake: 'float', v_max: 'Optional[float]' = None, direction: 'float' = 1.0) -> 'float'` (実装を直接呼ぶなら `import rsssafety; rsssafety.rss_stopping_distance(v: 'float', rho: 'float', accel: 'float', brake: 'float', v_max: 'Optional[float]' = None, direction: 'float' = 1.0) -> 'float'`、台帳から引くなら `opsdrive.get("rss_stopping_distance")`)

## 使い方

ad-rss-lib の stated braking pattern による **符号つき位置オフセット**(縦・横共通の 1 つの式)。

ρ の間 ``accel`` で加速(``v_max`` で頭打ち)し、ρ 後の速度 v_ρ が **相手へ向いている**
(``direction · v_ρ > 0``)ときだけ停止距離 ``direction · v_ρ² / (2 brake)`` を足す。
離れる向きなら足さない(lib ``calculateLongitudinalDistanceOffsetAfterStatedBrakingPattern`` /
``calculateLateralDistanceOffsetAfterStatedBrakingPattern`` の ``signbit`` 判定)。

符号規約
--------
* ``direction`` = 相手へ向かう向き(+1 か −1)。縦方向は +1(進行方向 = +x)。横方向は左の車が +1、右の車が −1。
* ``v`` は符号つき速度(direction 側が正なら相手へ向かっている)。縦方向は v ≥ 0 で呼ぶ。
* ``accel`` は符号つきで **direction 側に向ける**(``direction · accel ≥ 0`` でないと ValueError)。
  縦方向は ``+a_accel_max``、横方向は左 ``+a_lat``、右 ``−a_lat``。
* ``brake`` は正の大きさ。常に「相手へ向かう速度を 0 にする向き」(= ``−direction`` 側)にかかる。
* ``v_max`` は direction 側の到達速度の上限(None = 制限なし)。既に |v| がそれ以上なら加速しない。

縦方向(v ≥ 0, accel ≥ 0)では ``v ρ + ½ a ρ² + (v + a ρ)²/(2 b)`` になり論文 Lemma 2 の後続車の走行距離と一致する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`rss`)

[rss_params](rss_params.md) · [rss_longitudinal_same](rss_longitudinal_same.md) · [rss_longitudinal_opposite](rss_longitudinal_opposite.md) · [rss_lateral](rss_lateral.md) · [rss_longitudinal_check](rss_longitudinal_check.md) · [rss_lateral_check](rss_lateral_check.md) · [rss_worst_case_gap](rss_worst_case_gap.md) · [rss_worst_case_gap_opposite](rss_worst_case_gap_opposite.md)

---
*Provenance: rsssafety.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
