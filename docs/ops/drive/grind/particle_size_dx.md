---
op: particle_size_dx
dim: drive
category: grind
in: table × scalar
out: scalar
examples: [poc_powder_grinding_ae]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# particle_size_dx — DRIVE `grind` op

- **データ種**: `table × scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.particle_size_dx(psd: 'dict', q: 'float' = 50.0, convention: 'str' = 'log_edges') -> 'float'` (実装を直接呼ぶなら `import grind; grind.particle_size_dx(psd: 'dict', q: 'float' = 50.0, convention: 'str' = 'log_edges') -> 'float'`、台帳から引くなら `opsdrive.get("particle_size_dx")`)

## 使い方

体積累積 ``q`` % の径 Dq [µm] (D10 / D50 / D90 は ``q`` = 10 / 50 / 90)。

``convention``:

- ``"log_edges"``(既定、装置のヘッダの ``Dx (50)`` と一致): 端 i の累積に対して log(径) を線形補間。
- ``"linear_edges"``: 端の累積に対して径そのものを線形補間(区間内の体積が径について一様、の仮定)。
- ``"lower_cumsum"``: 公開の解析コードの学習の段の定義 ``np.interp(q/100, cumsum(v), edges)``(累積を区間の下の端に置く)。
  1 区間分小さく出る(この装置で −11.9 %)。比較のために再現しているだけで、推奨しない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_grinding_ae](../../../../examples/poc_powder_grinding_ae.py) — `py -3.11 examples/poc_powder_grinding_ae.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`grind`)

[particle_size_read](particle_size_read.md) · [particle_size_oversize](particle_size_oversize.md) · [particle_size_synth](particle_size_synth.md) · [comminution_energy](comminution_energy.md) · [comminution_law_fit](comminution_law_fit.md) · [breakage_first_order_fit](breakage_first_order_fit.md) · [replicate_compare](replicate_compare.md) · [ae_read_csv](ae_read_csv.md)

---
*Provenance: grind.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
