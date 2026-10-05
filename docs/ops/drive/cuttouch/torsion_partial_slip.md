---
op: torsion_partial_slip
dim: drive
category: cuttouch
in: scalar × scalar × table
out: table
examples: [poc_knife_tactile_toughness]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# torsion_partial_slip — DRIVE `cuttouch` op

- **データ種**: `scalar × scalar × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.torsion_partial_slip(M: 'float', P: 'float', pad: 'dict', ctx=None, field: 'bool' = False, na: 'int' = 64, from_no_slip_read: 'bool' = False) -> 'dict'` (実装を直接呼ぶなら `import cuttouch; cuttouch.torsion_partial_slip(M: 'float', P: 'float', pad: 'dict', ctx=None, field: 'bool' = False, na: 'int' = 64, from_no_slip_read: 'bool' = False) -> 'dict'`、台帳から引くなら `opsdrive.get("torsion_partial_slip")`)

## 使い方

球面パッド(Hertz、法線力 ``P``)に法線まわりのねじり ``M`` [N·m] を掛けたときの部分滑り: 固着半径 c、ねじれ角 β、全滑りまでの比。

数値解はモジュール冒頭(環 ``na`` 本の影響行列、無次元の 1 本の曲線を一度だけ)。返り: ``ratio`` = |M| / ((3π/16)μPa)、``c_over_a``、
``beta``(部分滑りのねじれ角 [rad])、``beta_no_slip`` = 3M/(16Ga³)(Reissner–Sagoci)、``read_bias`` = β/β_no_slip(無滑りの関係で
読んだときの M の過大の倍率)、``a``・``p0``・``M_full``、``slipping``(比 ≥ 1 = 全滑り。例外にせず印 —— 滑りは起きる状態で入力の
誤りではない。β は定まらないので nan)、``readable``(固着円が読みの核 r < 0.6a を含む)。``field=True`` なら ``ctx``
(:func:`pegtactile.pad_context`)の格子で周方向トラクションを Cerruti 核で畳んだ表面変位 ``ux``・``uy`` [m] と、マーカーの基準位置での
``u_markers`` (N, 2) [m] も返す(合成用。全滑りでは作らない)。``from_no_slip_read=True`` なら ``M`` を **無滑りの関係で読んだ値**
(Reissner–Sagoci、:func:`pegtactile.pad_tactile_read` の ``torsion_model="no_slip"``)と見て、部分滑りの M に直してから同じ表を返す
(``M`` = 直した値、``M_read`` = 渡した読み。読みが全滑りの像を超えていれば ``M`` = 全滑りのトルクで ``slipping``)。
``ratio_table_max`` は表の最後の行の比(これ以上は固着円が環 1 本より小さく、場を作らない)。
**Raises** ValueError: P ≤ 0・非有限、M が非有限、pad が :func:`pegtactile.pad_params` の表でない、na < 24。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_knife_tactile_toughness](../../../../examples/poc_knife_tactile_toughness.py) — `py -3.11 examples/poc_knife_tactile_toughness.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`cuttouch`)

[knife_load_from_pads](knife_load_from_pads.md) · [toughness_from_pads](toughness_from_pads.md)

---
*Provenance: cuttouch.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
