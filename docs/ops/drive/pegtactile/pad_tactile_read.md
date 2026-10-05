---
op: pad_tactile_read
dim: drive
category: pegtactile
in: table × table
out: table
examples: [poc_knife_tactile_toughness, poc_peg_insertion_tactile]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# pad_tactile_read — DRIVE `pegtactile` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pad_tactile_read(frame: 'dict', pad: 'dict', ctx=None, track=None, pixelwise: 'bool' = True) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.pad_tactile_read(frame: 'dict', pad: 'dict', ctx=None, track=None, pixelwise: 'bool' = True) -> 'dict'`、台帳から引くなら `opsdrive.get("pad_tactile_read")`)

## 使い方

パッド 1 枚の像 → (P̂, q̂, ねじり)。

P̂ = 陰影 → photometric の法線(:func:`tacsim.membrane_recover`)→ 接触半径(中心は既知 = パッド中央;``pixelwise`` なら
:func:`tacsim.contact_radius_fit_pixelwise`、偽ならビン版 :func:`tacsim.contact_radius_fit` = 罠の対照)→ :func:`tacsim.hertz_force`。
q̂ = マーカー追跡(:func:`tacslip.marker_track`、``track`` で渡せば省く)→ 法線荷重の ūr(P̂ から閉形式)を引く → 2 成分の Mindlin
当てはめ(:func:`tacslip.mindlin_fit_vector`)。ねじり = 当てはめたせん断場を引いた残りに、固着核(r < 0.6 â)で剛体回転
(:func:`tactorque.rigid_rotation_fit`)→ M = (16Gâ³/3)ω(Reissner–Sagoci)。第 2 実装 ``Q_stick`` = 固着核の一様変位 δ̂ を
Mindlin の δx 式で逆に解いた値(μ は較正値)。返り ``P``・``a``・``q``(2,)・``Q``・``phi``・``torsion``・``c_over_a``・``Q_stick``・
``matched``・``rms_px``(当てはめの残差)・``track``。**Raises** ValueError: frame に ``rgb``・``shading`` が無い、追跡できたマーカーが 3 未満。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_knife_tactile_toughness](../../../../examples/poc_knife_tactile_toughness.py) — `py -3.11 examples/poc_knife_tactile_toughness.py`
- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegtactile`)

[pad_params](pad_params.md) · [pad_context](pad_context.md) · [peg_wrench_to_pad_loads](peg_wrench_to_pad_loads.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_shear_asymmetry](pad_shear_asymmetry.md) · [pad_marker_displacement](pad_marker_displacement.md) · [pad_tactile_frame](pad_tactile_frame.md) · [contact_candidates](contact_candidates.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
