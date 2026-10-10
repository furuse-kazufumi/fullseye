---
op: knife_load_from_pads
dim: drive
category: cuttouch
in: table × table × table × scalar
out: table
examples: [poc_knife_tactile_toughness]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# knife_load_from_pads — DRIVE `cuttouch` op

- **データ種**: `table × table × table × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.knife_load_from_pads(read_R: 'dict', read_L: 'dict', pad: 'dict', Lz: 'float', edge_slope: 'float' = 0.0, torsion_model: 'str' = 'partial_slip', tare=None, v_min: 'float' = 0.05, na: 'int' = 64) -> 'dict'` (実装を直接呼ぶなら `import cuttouch; cuttouch.knife_load_from_pads(read_R: 'dict', read_L: 'dict', pad: 'dict', Lz: 'float', edge_slope: 'float' = 0.0, torsion_model: 'str' = 'partial_slip', tare=None, v_min: 'float' = 0.05, na: 'int' = 64) -> 'dict'`、台帳から引くなら `opsdrive.get("knife_load_from_pads")`)

## 使い方

2 枚のパッドの読み(:func:`pegtactile.pad_tactile_read`)→ 刃が食材から受ける押し V・引き H・モーメント M_x と、刃の当たり位置 Ly。

``Lz`` [m]: 把持点から刃先までの高さ(刃が傾いていれば把持点の真下での値 Lz₀、``edge_slope`` = 刃先の傾きの正接で
``Ly = (M_x + Lz₀ H)/(V + s H)``)。``torsion_model``: ``"partial_slip"``(既定 —— 無滑りの関係で読まれたねじりを部分滑りの数値解で
直す、モジュール冒頭)/ ``"no_slip"``(無滑りの読みのまま = :mod:`pegtactile` 0.4.0 の約束、比べるため)。読みが
:func:`pegtactile.pad_tactile_read` の既定(既に部分滑りに直した ``torsion`` と無滑りの ``torsion_no_slip``)でも、ここは無滑りの値から
始めるので二重には直さない。``tare``: 空中の 1 コマの 2 枚の読み
``(read_R, read_L)``(または前の返り・``{"F": (3,), "M": (3,)}`` のパッドのレンチ)—— 包丁の重さを差し引く(空中のコマそのものは
V = 0 で Ly が定まらないので、この op に単独では渡せない)。
返り: ``V``・``H``・``Mx``(食材 → 刃、グリッパ系)、``Ly``・``xi``(= H/V)、パッドごとの ``torsion``(直した値)・``torsion_read``・
``torsion_ratio``・``slip_ratio``(せん断 |q|/μP)・``c_over_a``、``combined_margin`` = 1 − max(せん断の比 + ねじりの比)(十分条件)、
``readable``(両方のパッドで固着円が読みの核を含む)、``Ly_range_full_slip``・``Ly_range_readable``(いまの V・H・把持力のまま当たり位置が
動いたとき、全滑り / 読めなくなるまでの Ly の範囲 = 持てる柄の長さの限界)、``pad_wrench``(パッド → 刃、tare 前)、``torsion_model``。
**Raises** ValueError: 読みが壊れている、V ≤ ``v_min``(刃が食材を押していない = Ly が定まらない)、綴り違い、Lz が非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_knife_tactile_toughness](../../../../examples/poc_knife_tactile_toughness.py) — `py -3.11 examples/poc_knife_tactile_toughness.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`cuttouch`)

[torsion_partial_slip](torsion_partial_slip.md) · [toughness_from_pads](toughness_from_pads.md)

---
*Provenance: cuttouch.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
