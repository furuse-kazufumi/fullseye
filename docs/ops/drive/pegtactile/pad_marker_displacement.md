---
op: pad_marker_displacement
dim: drive
category: pegtactile
in: scalar × signal × table
out: table
examples: [poc_knife_tactile_toughness]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# pad_marker_displacement — DRIVE `pegtactile` op

- **データ種**: `scalar × signal × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pad_marker_displacement(P: 'float', q_uv, pad: 'dict', ctx=None, pts=None, torsion: 'float' = 0.0, torsion_model: 'str' = 'partial_slip') -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.pad_marker_displacement(P: 'float', q_uv, pad: 'dict', ctx=None, pts=None, torsion: 'float' = 0.0, torsion_model: 'str' = 'partial_slip') -> 'dict'`、台帳から引くなら `opsdrive.get("pad_marker_displacement")`)

## 使い方

膜の表面変位をマーカー位置で(閉形式 + Cerruti 畳み込み): 向き φ のせん断 |q| は x 向きの Mindlin 場を φ だけ回したもの
u(p) = R(φ) u_x(R(−φ)p)(核は等方な半空間なので回転で閉じる)、法線荷重の半径変位 ūr(Johnson 式 3.41b)とねじりの場を足す。
ねじりの場は ``torsion_model="partial_slip"``(既定、2026-10-06 から)なら部分滑り(:func:`cuttouch.torsion_partial_slip` の数値解、
縁の環から滑る)、``"no_slip"`` なら 0.4.0 までの無滑りの場(:func:`tactorque.torsion_stick_field`)。ねじりが全滑りを超えるときは、
膜はそれ以上のねじりを運べないので表の最後の行(固着円が環 1 本)の場で描き、``torsion_slipping`` の印を立てる。``pts`` はマーカー中心
(px、省略時は ``ctx`` の基準位置)。返り ``u_m``(N, 2)[m]、``hz``・``mp``(Hertz と Mindlin の表)、``phi``・``Q``・``torsion``・
``torsion_model``・``torsion_ratio``・``torsion_slipping``。全滑り(|q| ≥ μP)は ``mp['slipping']`` の印(場は c = 0)。
**Raises** ValueError: P ≤ 0(パッドが離れている)、q が有限の 2 成分でない、torsion_model の綴り違い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_knife_tactile_toughness](../../../../examples/poc_knife_tactile_toughness.py) — `py -3.11 examples/poc_knife_tactile_toughness.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegtactile`)

[pad_params](pad_params.md) · [pad_context](pad_context.md) · [peg_wrench_to_pad_loads](peg_wrench_to_pad_loads.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_shear_asymmetry](pad_shear_asymmetry.md) · [pad_tactile_frame](pad_tactile_frame.md) · [pad_tactile_read](pad_tactile_read.md) · [contact_candidates](contact_candidates.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
