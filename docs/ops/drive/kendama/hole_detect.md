---
op: hole_detect
dim: drive
category: kendama
in: image2d
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# hole_detect — DRIVE `kendama` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.hole_detect(img, ball_center, ball_radius, *, dark_ratio: 'float' = 0.45, min_sat: 'float' = 0.35, min_chroma: 'float' = 0.1, min_area: 'int' = 3) -> 'dict'` (実装を直接呼ぶなら `import kendama; kendama.hole_detect(img, ball_center, ball_radius, *, dark_ratio: 'float' = 0.45, min_sat: 'float' = 0.35, min_chroma: 'float' = 0.1, min_area: 'int' = 3) -> 'dict'`、台帳から引くなら `opsdrive.get("hole_detect")`)

## 使い方

玉の像の中の暗い円盤(けん先の穴)を探す: 玉の中心 ``ball_center`` (col, row)・像の半径 ``ball_radius`` [px] の円の内側で、
明るさ(RGB の平均)が玉の明るさの中央値の ``dark_ratio`` 倍未満、彩度 (max − min)/max ≥ ``min_sat``(灰色の糸を除く)、
かつ色度(RGB / |RGB|)が玉の色度の中央値から ``min_chroma`` 以上離れた(陰になった玉の面は明るさだけが落ちて色度は同じ
—— 明るさだけで拾うと影を穴と取り違えた、測って退けた)画素の連結成分のうち最大のもの。返り値 ``{"found", "col", "row", "angle" (玉の中心 → 穴の重心の像の角度 [rad]、
atan2(Δrow, Δcol)), "offset" (距離 / ball_radius: 0 = 正面、→ 1 = 縁), "ellipticity" (短軸 / 長軸、2 次モーメントから:
1 = 正面の円、→ 0 = 真横), "area" [px]}``。見つからなければ found False(他は NaN)。
正面から見た穴の中心は玉の中心と重なり、横へ回るほど縁へ寄って潰れる(offset ≈ sin φ、ellipticity ≈ cos φ、φ = 穴の軸と視線の角)。
img (H, W, 3)、ball_radius > 0 でなければ ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`kendama`)

[kendama_params](kendama_params.md) · [elliptic_k_agm](elliptic_k_agm.md) · [pendulum_period_exact](pendulum_period_exact.md) · [pendulum_launch_speed](pendulum_launch_speed.md) · [pendulum_rod_simulate](pendulum_rod_simulate.md) · [tether_tension_fixed](tether_tension_fixed.md) · [tether_slack_angle](tether_slack_angle.md) · [swing_up_plan](swing_up_plan.md)

---
*Provenance: kendama.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
