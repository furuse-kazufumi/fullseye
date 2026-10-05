---
op: diabolo_render
dim: drive
category: diabolo
in: table × table
out: rgb
examples: [poc_diabolo_model_and_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# diabolo_render — DRIVE `diabolo` op

- **データ種**: `table × table` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.diabolo_render(cam: 'dict', params: 'dict', *, center=None, axis=None, phase: 'float' = 0.0, omega: 'float' = 0.0, exposure: 'float' = 0.0, n_sub: 'int' = 8, sticks=None, ss: 'int' = 4, noise: 'float' = 0.0, blur_sigma: 'float' = 0.0, seed: 'int' = 0, background=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import diabolo; diabolo.diabolo_render(cam: 'dict', params: 'dict', *, center=None, axis=None, phase: 'float' = 0.0, omega: 'float' = 0.0, exposure: 'float' = 0.0, n_sub: 'int' = 8, sticks=None, ss: 'int' = 4, noise: 'float' = 0.0, blur_sigma: 'float' = 0.0, seed: 'int' = 0, background=None) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("diabolo_render")`)

## 使い方

ディアボロの 1 コマを光線追跡で描く(RGB float (H, W, 3)、[0, 1])。

形 = 2 つのカップ(円錐殻、外面 赤・内面 黄)+ 底の板(暗い灰)+ 軸。マーカーは手前のカップの内面に ``n_slots`` か所(反射 = 白、
ダミー = 灰)。``center`` の既定はカメラの注視点、``axis`` の既定はカメラへ向く向き。``phase`` = 体の系 e1 から測った回転角、
``omega`` [rad/s] と ``exposure`` [s] でマーカーの回転ぶれ(露光の中心 = コマの時刻、``n_sub`` 点で平均)。``sticks`` = (2, 3) を
渡すと棒と糸(軸へ伸びる 2 本)と棒の先の青い印も描く。``ss`` × ``ss`` の超標本化はディアボロの外接矩形だけ(縁の被覆率が
正しく出る)。``noise`` = 画素ごとのガウス雑音の σ(``seed`` で再現)、``blur_sigma`` = 光学ぼけ [px]。

**Raises** ``ValueError``: cam / params の形、軸がゼロ、ss / n_sub < 1、負の雑音・ぼけ・露光。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_diabolo_model_and_vision](../../../../examples/poc_diabolo_model_and_vision.py) — `py -3.11 examples/poc_diabolo_model_and_vision.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_depth_decode](../carla/carla_depth_decode.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md)

## 同カテゴリ(`diabolo`)

[diabolo_params](diabolo_params.md) · [diabolo_spheroid](diabolo_spheroid.md) · [spheroid_closest](spheroid_closest.md) · [diabolo_dynamics_step](diabolo_dynamics_step.md) · [diabolo_simulate](diabolo_simulate.md) · [diabolo_state_sequence](diabolo_state_sequence.md) · [diabolo_throw_catch_truth](diabolo_throw_catch_truth.md) · [string_tension_static](string_tension_static.md)

---
*Provenance: diabolo.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
