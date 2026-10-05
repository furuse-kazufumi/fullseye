---
op: mindlin_model
dim: drive
category: tacslip
in: table × matrix × matrix × table × scalar × scalar
out: table
examples: [poc_tacsim_marker_shear]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# mindlin_model — DRIVE `tacslip` op

- **データ種**: `table × matrix × matrix × table × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mindlin_model(hz: 'dict', X, Y, kern: 'dict', G: 'float', nu: 'float') -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.mindlin_model(hz: 'dict', X, Y, kern: 'dict', G: 'float', nu: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("mindlin_model")`)

## 使い方

任意の c/a の Mindlin 変位場を**相似則**で出す逆算模型(畳み込みは 1 回だけ)。

Hertz 形の接線トラクション(半径 R、頂点 q0)の表面変位は u = q0·R·ĝ(x/R)(線形弾性 + 無次元化)。q′(半径 a、頂点 μp0)と
q″(半径 c、頂点 μp0·c/a)の差だから、g(x) = 頂点 1 Pa・半径 a の場として u(x; c) = μp0·[g(x) − (c/a)²·g(x·a/c)]。
g は Cerruti 核で格子上に作り、x·a/c が格子の外に出る点は点荷重の漸近形(総力 (2/3)πa²·1 Pa)で補う。順方向の畳み込みとの差は
核で 0.05 %、環で 0.13 %。返り ``gx``・``gy``(n, n)、``Qunit``、``n``・``pitch``・``c0``(格子中心 [px])、``hz``・``G``・``nu``。
c/a の格子を線形補間する模型は場が c に非線形なので c/a を 0.01 ずらした(捨てた)。**Raises** ValueError: 形の不一致、G ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
