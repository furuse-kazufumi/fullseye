---
op: add_signal_jp
dim: drive
category: roadjp
in: table
out: scalar
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# add_signal_jp — DRIVE `roadjp` op

- **データ種**: `table` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.add_signal_jp(world: 'dict', x: 'float', y: 'float', yaw: 'float', *, state: 'str' = 'red', arm: 'float' = 2.0, lamp_bottom: 'float' = 5.0, pole_radius: 'float' = 0.08, arm_side: 'str' = 'left', lens: 'float' = 0.3, hood: 'bool' = True) -> 'int'` (実装を直接呼ぶなら `import roadjp; roadjp.add_signal_jp(world: 'dict', x: 'float', y: 'float', yaw: 'float', *, state: 'str' = 'red', arm: 'float' = 2.0, lamp_bottom: 'float' = 5.0, pole_radius: 'float' = 0.08, arm_side: 'str' = 'left', lens: 'float' = 0.3, hood: 'bool' = True) -> 'int'`、台帳から引くなら `opsdrive.get("add_signal_jp")`)

## 使い方

日本式の信号機を立てる: 柱 + 水平アーム + 灯器(横型 3 灯、yaw の向きへ進んで来る車に表示面が向く)。

配置(信号機設置の指針の解説: 一般の車両用灯器は交差点の向こう側 = 出口側): 柱を (x, y) に立て
(高さ lamp_bottom + 0.7)、アームを進入車の運転者から見て **右**(車線の上。yaw 0 で −y)へ水平に ``arm`` だけ出し
(標準 2.0 m、最大 3.5 m 超は ValueError)、灯器の中心をアームの先に吊る(灯器の底 = ``lamp_bottom``、
既定 5.0 m、4.5 m 未満は ValueError — 交通信号機工事仕様書、一次資料で要確認)。``arm_side="right"`` なら柱が
運転者の右側にあり、アームは左へ出る。表示面の法線 = (−cos yaw, −sin yaw)、レンズは運転者から見て左から青・黄・赤。

objects: 柱 + アーム(ラベル 3、name "signal_pole")と灯器(ラベル 3、name "traffic_light"、
``extra = {"state", "lamp_faces"(世界の面索引), "arm", "lamp_bottom", "kind": "jp"}``)。返り値 = 灯器の索引
(:func:`driveworld.set_signal_state` はこれに対して使う)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`roadjp`)

[sign_params](sign_params.md) · [sign_image](sign_image.md) · [plate_mesh_from_image](plate_mesh_from_image.md) · [sign_mesh](sign_mesh.md) · [add_sign](add_sign.md) · [signal_jp_mesh](signal_jp_mesh.md)

---
*Provenance: roadjp.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
