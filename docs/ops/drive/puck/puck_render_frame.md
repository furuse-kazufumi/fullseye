---
op: puck_render_frame
dim: drive
category: puck
in: table × signal
out: image2d
examples: [poc_air_hockey_intercept]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# puck_render_frame — DRIVE `puck` op

- **データ種**: `table × signal` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.puck_render_frame(cam: 'dict', p, *, v=None, exposure: 'float' = 0.0, n_sub: 'int' = 16, noise: 'float' = 0.0, rng=None, puck_value: 'float' = 0.12, table_value: 'float' = 0.92, wall_value: 'float' = 0.55) -> 'np.ndarray'` (実装を直接呼ぶなら `import puck; puck.puck_render_frame(cam: 'dict', p, *, v=None, exposure: 'float' = 0.0, n_sub: 'int' = 16, noise: 'float' = 0.0, rng=None, puck_value: 'float' = 0.12, table_value: 'float' = 0.92, wall_value: 'float' = 0.55) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("puck_render_frame")`)

## 使い方

真上の 1 コマを合成(float (H,W)、0〜1): 白い台・灰色の壁・暗いパック(1 次の反エイリアス)。

``exposure`` > 0 なら露光の間 [t, t+exposure] にパックが v·exposure 動く分を n_sub 個の副露光の平均で入れる(モーションブラー)。
コマの時刻は **露光の始め**: ブラーした像の重心は v·exposure/2 だけ進む(閉形式、門)。``noise`` はガウス雑音の σ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_air_hockey_intercept](../../../../examples/poc_air_hockey_intercept.py) — `py -3.11 examples/poc_air_hockey_intercept.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`puck`)

[puck_table](puck_table.md) · [puck_wall_bounce](puck_wall_bounce.md) · [puck_slide_predict](puck_slide_predict.md) · [puck_state_at](puck_state_at.md) · [puck_crossing_point](puck_crossing_point.md) · [puck_mirror_path](puck_mirror_path.md) · [puck_stop_distance](puck_stop_distance.md) · [puck_camera](puck_camera.md)

---
*Provenance: puck.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
