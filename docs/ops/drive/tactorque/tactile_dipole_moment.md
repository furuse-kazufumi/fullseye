---
op: tactile_dipole_moment
dim: drive
category: tactorque
in: matrix × matrix
out: table
examples: [poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# tactile_dipole_moment — DRIVE `tactorque` op

- **データ種**: `matrix × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tactile_dipole_moment(pts, u, form: 'str' = 'divergence', origin='midpoint', weight: 'str' = 'area', area: 'float | None' = None, window=None, rho=None, radius: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import tactorque; tactorque.tactile_dipole_moment(pts, u, form: 'str' = 'divergence', origin='midpoint', weight: 'str' = 'area', area: 'float | None' = None, window=None, rho=None, radius: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("tactile_dipole_moment")`)

## 使い方

触覚双極子モーメント D = Σ_i w ρ_i r_i(2 成分)。``form``:
  * ``"divergence"`` —— 論文(arXiv 2404.15626)式 4–8: ρ_i = (∇·u)_i(``rho`` を渡すか、``radius`` で :func:`marker_divergence`)。
  * ``"norm_cross"`` —— 論文の基線(式 10–11、Yamaguchi & Atkeson 流): ρ_i = |u_i|(ベクトルのノルムを法線力の代わりに)。
    l_i × f_i の傾き成分は (l_y|u|, −l_x|u|) で D を 90° 回したものなので、同じ「1 次モーメント」の枡で返す。零点後の対称な傾きでは
    |u| が M の偶関数なので恒等的に 0(符号を知らない、門)。
  * ``"radial"`` —— 本モジュールの変種: ρ_i = u_i · r̂_i(放射成分)。
``origin``: ``"midpoint"``(式 6–7、正負の重心の中点)/ ``"centre"``(pts の平均、基線の作法)/ (x0, y0)。
``weight``: ``"area"`` = 1 点あたり面積 ``area`` [m²] を掛ける(閉形式の係数 −(1−2ν)/(2G) と比べられる、単位 m³)/ ``"mean"`` = 1/N(論文)。
``window`` = (cx, cy, R) なら半径 R 内の点だけ使う(せん断の漏れを切る窓、根拠はモジュール docstring)。valid でない点(nan)は除く。
返り ``D`` (2,)、``tau_dir`` = (−D_y, D_x)(式 9 の向き、係数なし)、``origin``、``n``、``rho``、``form``、``keep``。
**Raises** ValueError: form/origin/weight が未知(綴り違いは fail-closed)、pts/u の形、area 無しの "area"、使える点が 3 未満。

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
