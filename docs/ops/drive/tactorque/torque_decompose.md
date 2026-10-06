---
op: torque_decompose
dim: drive
category: tactorque
in: matrix × matrix × scalar × scalar × scalar
out: table
examples: [poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# torque_decompose — DRIVE `tactorque` op

- **データ種**: `matrix × matrix × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.torque_decompose(pts, u, area: 'float', G: 'float', nu: 'float', a: 'float | None' = None, window=None, radius: 'float | None' = None, coef: 'float | None' = None, P: 'float | None' = None, mu: 'float | None' = None, torsion_model: 'str' = 'partial_slip') -> 'dict'` (実装を直接呼ぶなら `import tactorque; tactorque.torque_decompose(pts, u, area: 'float', G: 'float', nu: 'float', a: 'float | None' = None, window=None, radius: 'float | None' = None, coef: 'float | None' = None, P: 'float | None' = None, mu: 'float | None' = None, torsion_model: 'str' = 'partial_slip') -> 'dict'`、台帳から引くなら `opsdrive.get("torque_decompose")`)

## 使い方

マーカー場を 3 つの力学量に分ける: ``translation`` = 窓内の平均変位(せん断 Q、単向成分)、``omega`` = 剛体回転角
(:func:`rigid_rotation_fit`)→ ねじり ``Mz``(a が要る; ``omega_curl`` = 平均 curl/2 は参考)、
``D`` = 発散双極子(面積重み)→ 傾き ``M1`` = D / coef(coef 既定 = 半空間の閉形式 −(1−2ν)/(2G)、実機は較正値を渡す)、``tau`` = (−M1_y, M1_x)。
発散・curl は平均変位を引いても変わらない(定数の微分は 0)ので順序に依らない。窓 (cx, cy, R) は接触円に限る(半空間では純せん断が
窓全体に発散双極子を作るため、モジュール docstring 参照)。``radius`` = 発散の近傍半径(必須)。

ねじり: 無滑りの関係(Reissner–Sagoci)M = (16Ga³/3)ω を ``Mz_no_slip`` に残す。★``torsion_model="partial_slip"``(既定、2026-10-06 から)
では、Hertz 接触(法線力 ``P``、摩擦 ``mu``、接触半径 ``a``)の部分滑りの数値解(:func:`cuttouch.torsion_partial_slip` の
``contact`` と ``from_no_slip_read``)で直した値を ``Mz`` に返す —— Hertz 接触のねじりは縁から必ず滑るので、無滑りの関係のままだと
M を過大に読む(全滑りまでの比 0.5 で +33 %、0.8 で +85 %)。``Mz_ratio``(全滑りまでの比)、``Mz_c_over_a``(固着円の半径 / a)、
``Mz_readable``(全滑りでなく、固着円が当てはめの窓の半径を含む —— 偽なら数は返すが当てにならない。窓が無ければ偽)も返す。
a を渡して P か mu が無いと補正できないので ValueError(黙って無滑りの値を返さない)。``"no_slip"`` は 0.4.0 までの値
(``Mz`` = ``Mz_no_slip``)—— 平頭押し込み子(全滑りの 8/(3π) 倍まで無滑りが厳密)や接着した円盤の場合。
**Raises** ValueError: area, G ≤ 0、ν が [0, 0.5] の外、点の形、radius 無し、窓内の点が 3 未満、torsion_model の綴り違い、
partial_slip で a があるのに P・mu が正の有限でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tactorque`)

[punch_pressure](punch_pressure.md) · [punch_surface_uz](punch_surface_uz.md) · [hertz_pressure_shifted](hertz_pressure_shifted.md) · [ellipse_pressure_shifted](ellipse_pressure_shifted.md) · [pressure_first_moment](pressure_first_moment.md) · [boussinesq_kernel](boussinesq_kernel.md) · [boussinesq_surface_displacement](boussinesq_surface_displacement.md) · [surface_divergence_closed_form](surface_divergence_closed_form.md)

---
*Provenance: tactorque.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
