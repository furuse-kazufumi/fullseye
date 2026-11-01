---
op: polyhedron_gravity
dim: drive
category: polygrav
in: any × points
out: table
gpu: なし
examples: [itokawa_gravity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# polyhedron_gravity — DRIVE `polygrav` op

- **データ種**: `any × points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.polyhedron_gravity(mesh, points, density: 'float' = 1.0, G: 'float' = 6.6743e-11, omega: 'float' = 0.0, spin_axis=(0.0, 0.0, 1.0), spin_center=None, normals=None) -> 'dict'` (実装を直接呼ぶなら `import polygrav; polygrav.polyhedron_gravity(mesh, points, density: 'float' = 1.0, G: 'float' = 6.6743e-11, omega: 'float' = 0.0, spin_axis=(0.0, 0.0, 1.0), spin_center=None, normals=None) -> 'dict'`、台帳から引くなら `opsdrive.get("polyhedron_gravity")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

一様密度の閉じた多面体が観測点に作る重力(Werner & Scheeres 1997 の厳密な式)。

Parameters
----------
mesh : (vertices (N,3), faces (M,3))
    閉じた三角形メッシュ。面は外向き(右手系)に巻く。長さの単位は m として扱う(km のデータは 1000 倍)。
points : (K,3)
    観測点 [m]。外・中・表面の上(頂点・辺の上も)のどこでもよい。
density : float
    密度 [kg/m³] (正)。
G : float
    重力定数(既定 6.67430e-11、CODATA 2018)。
omega : float
    自転の角速度 [rad/s] (0 以上)。正なら回る座標の実効ポテンシャルと実効重力も返す。
spin_axis : (3,)
    自転軸の向き(正規化する)。既定は +z。
spin_center : (3,), optional
    自転軸が通る点。既定は立体の重心(自由に回る天体は重心のまわりに回る)。
normals : (K,3), optional
    観測点での外向きの法線。渡すと斜面の角 ``slope_deg`` を返す(実効重力と −法線 のなす角、
    omega = 0 なら重力そのもの)。

Returns
-------
dict
    ``potential`` (K,) Φ [J/kg] (負。無限遠で 0)、``acceleration`` (K,3) g = −∇Φ [m/s²] (天体へ向く)、
    ``div_g`` (K,) ∇·g [1/s²] (中で −4πGρ、外で 0、面の上で −2πGρ —— ガウスの法則)、
    ``solid_angle`` (K,) Σ ω_f(中で 4π、外で 0)、``mass`` [kg]、``volume`` [m³]、``center_of_mass`` (3,)。
    omega > 0 のとき ``effective_potential`` (K,) = Φ − ½ω²ρ⊥²、``effective_acceleration`` (K,3) = g + ω²ρ⊥
    (ρ⊥ は自転軸からの垂直な距離のベクトル)、``spin_center`` (3,)。normals があれば ``slope_deg`` (K,)。

Notes
-----
辺の上・頂点の上の点では、その辺の対数 L_e が発散するが掛かる係数 n_fe·r_i が 0 なので、その項を 0 とする
(極限値)。メッシュが閉じていない(有向辺が逆向きの辺と打ち消さない)、体積が正でない(内向きの巻き)、
非有限、範囲外の索引は ``ValueError``。空の入力(``points`` が 0 要素)は ValueError で拒否する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_gravity_tour](../../../../examples/itokawa_gravity_tour.py) — `py -3.11 examples/itokawa_gravity_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`polygrav`)

[polyhedron_clip_halfspace](polyhedron_clip_halfspace.md)

---
*Provenance: polygrav.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
