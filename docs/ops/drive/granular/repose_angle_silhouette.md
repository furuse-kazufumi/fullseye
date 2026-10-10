---
op: repose_angle_silhouette
dim: drive
category: granular
in: image2d
out: table
examples: [poc_granular_heap_repose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# repose_angle_silhouette — DRIVE `granular` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.repose_angle_silhouette(side, *, threshold: 'float' = 0.5, toe_frac: 'float' = 0.15, apex_frac: 'float' = 0.15, min_points: 'int' = 8, correct_ground: 'bool' = False, method: 'str' = 'edge') -> 'dict'` (実装を直接呼ぶなら `import granular; granular.repose_angle_silhouette(side, *, threshold: 'float' = 0.5, toe_frac: 'float' = 0.15, apex_frac: 'float' = 0.15, min_points: 'int' = 8, correct_ground: 'bool' = False, method: 'str' = 'edge') -> 'dict'`、台帳から引くなら `opsdrive.get("repose_angle_silhouette")`)

## 使い方

側面像(粉の被覆率)から安息角 φ を読む —— 左右の斜面に別々に直線を当て、裾と頂を除く。

手順(Sunday ほか 2020 §5.3 の作法を規則化): ①列ごとの粉面の高さ = 被覆率が ``threshold`` を切る縁の画素の
位置 + その被覆率(副画素; ``method="edge"``、既定)②地面 = 各列の最下の交差(同じ補間)→ ``measure.fit_line`` で
地面の傾き β。``method="column_sum"`` は被覆率の列和(縁が反エイリアスなら厳密な副画素だが、粉の画素値が
1 からずれると **その比で tan φ がずれる**: 一様雑音 ±0.1 を [0, 1] に切っただけで 0.62 度低く出た、実測)
③頂 = 高さの最大列 ④地面からの高さが ``toe_frac·H`` 以上・``(1 − apex_frac)·H`` 以下の点だけを
左右別々に ``fit_line``(全最小二乗)⑤φ = 左右の平均。

- ``correct_ground``: 基準面の傾き β を **tan の引き算**で外す(``tan φ' = tan θ ∓ tan β``; せん断型
  datum の傾きに対して厳密)。カメラのロールなら角の引き算が正しく、両者は β = 5 度で 1 度以上違う
  ので既定は外さない。左右の差 ``asymmetry_deg`` が大きいときだけ基準面を疑う。
- 返り: ``phi_deg``, ``phi_left_deg``, ``phi_right_deg``, ``asymmetry_deg``, ``ground_deg``,
  ``height_px``, ``base_px``, ``apex_col``, ``left_cols`` / ``right_cols``(当てた列の範囲)、
  ``rms_left`` / ``rms_right``(直線からの残差 [px])、``n_left`` / ``n_right``。
- **Raises** ``ValueError``: 画像でない / 被覆率が [0, 1] の外 / 粉が写っていない / 山が画像の
  上・左・右の縁に触れている(切れている)/ 当てる点が ``min_points`` 未満(山が小さすぎる)/
  ``toe_frac + apex_frac ≥ 1`` / ``method`` の綴り違い。
分解能の目安(被覆率に一様雑音 ±0.1、4 角度 × 6 seed の実測): 山の幅 400 px で 0.007 度、50 px で 0.2 度、25 px で 0.6 度。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [beverloo_fit](beverloo_fit.md) · [discharge_synth](discharge_synth.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [hopper_discharge_rate](hopper_discharge_rate.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
