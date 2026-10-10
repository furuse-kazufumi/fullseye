---
op: rotation_window
dim: drive
category: pegsym
in: scalar × scalar × scalar
out: table
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# rotation_window — DRIVE `pegsym` op

- **データ種**: `scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.rotation_window(n: 'int', apothem: 'float', clearance: 'float', chamfer: 'float' = 0.0, peg_vertices=None, hole_vertices=None, tol: 'float' = 1e-10, mu: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import pegsym; pegsym.rotation_window(n: 'int', apothem: 'float', clearance: 'float', chamfer: 'float' = 0.0, peg_vertices=None, hole_vertices=None, tol: 'float' = 1e-10, mu: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("rotation_window")`)

## 使い方

ペグが穴(面取りがあれば口)に入る回転の窓。正 n 角形の閉形式(導出): 中心を揃えた時、頂点は面の法線から π/n ∓ φ の向きにあり、
最も外へ出る頂点の法線方向の長さ a cos(π/n − |φ|) が A + δ(+ W)以下なら入る:
    φ = π/n − arccos(x)、x = (A + δ + W) cos(π/n)/A(x ≥ 1 なら窓は半周期 π/n いっぱい)。
arccos は 1 の近くで丸めの床があるので atan2(√(1 − x²), x) で書く。``peg_vertices``・``hole_vertices`` を渡すと、線形計画
(:func:`polygon_fit_check`、平行移動も自由)の二分法で正・負の向きの窓も測る(第 2 実装。キー付きはこちらだけ)。
返り ``phi_fit``(口でなく最狭部)・``phi_cap``(面取りの口)・``period`` = 2π/n、``M`` = ⌈period/(2 phi_cap)⌉、
``lp``(``plus``/``minus``: 頂点を渡した時、口に入る窓の両端 = 0 を含む連結な区間。走査は半周期を 360 刻み、端は二分法)。

``mu`` を渡すと**摩擦で止まる限界**も返す(導出、45° の面取り): 口に載った頂点(面の法線から β = π/n − φ の向き)が面取りを滑り下りる
には、ペグが回らなければならない(偶数の n では向かい合う頂点の横向きの力が打ち消し合い、並進しない)。軸まわりのばねが弱いと
接触力の軸まわりのモーメントが 0 で釣り合う: 面取りの法線の接線成分 sin β/√2 と、滑りの向き(面の上で下り + 回転)に逆らう摩擦
μ/√(1 + sin²β) が等しい所が境で、回るのは s√(1 + s²) > √2 μ(s = sin β)、すなわち s² > (√(1 + 8μ²) − 1)/2 の時。
``phi_friction`` = π/n − β*、``phi_eff`` = max(phi_fit, min(phi_cap, phi_friction))(面取りに頼らず入る分は摩擦に依らない)。
六角形(頂点が面の法線に近い)は摩擦で窓が狭まり、三角形・四角形は幾何で決まる —— MuJoCo の試作で確かめた(PoC の --full)。
**Raises** ValueError: n < 1、apothem ≤ 0、clearance < 0、chamfer < 0、mu < 0、頂点を片方だけ渡した。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_symmetry_search](../../../../examples/poc_peg_symmetry_search.py) — `py -3.11 examples/poc_peg_symmetry_search.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsym`)

[polygon_peg](polygon_peg.md) · [polygon_offset](polygon_offset.md) · [polygon_fit_check](polygon_fit_check.md) · [polygon_two_point_depth](polygon_two_point_depth.md) · [polygon_coverage_image](polygon_coverage_image.md) · [plane_topview](plane_topview.md) · [polygon_yaw_read](polygon_yaw_read.md) · [relative_yaw_from_images](relative_yaw_from_images.md)

---
*Provenance: pegsym.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
