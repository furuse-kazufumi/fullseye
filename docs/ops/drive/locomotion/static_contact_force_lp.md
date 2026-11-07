---
op: static_contact_force_lp
dim: drive
category: locomotion
in: points × normals × vector × scalar × scalar
out: table
gpu: なし
examples: [walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# static_contact_force_lp — DRIVE `locomotion` op

- **データ種**: `points × normals × vector × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.static_contact_force_lp(contacts, normals, com, mass, mu, gravity: 'float' = 9.81, n_facets: 'int' = 8) -> 'dict'` (実装を直接呼ぶなら `import locomotion; locomotion.static_contact_force_lp(contacts, normals, com, mass, mu, gravity: 'float' = 9.81, n_facets: 'int' = 8) -> 'dict'`、台帳から引くなら `opsdrive.get("static_contact_force_lp")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Static contact-force distribution under linearised friction cones (``scipy.optimize.linprog``).

静的な接触力の配分。各接触 i の力を、摩擦錐を ``n_facets`` 角の多角錐で内側から近似した
生成ベクトル ``g_ik = n_i + μ·t_ik``(t_ik は接平面の単位ベクトルを等角に回したもの)の
非負結合 ``f_i = Σ_k λ_ik g_ik`` で表し、静的な釣り合い

    Σ f_i + m·g = 0,   Σ (p_i − c) × f_i = 0      (g = (0, 0, −gravity))

を満たす λ ≥ 0 を線形計画で探す。目的は **法線力の最大値の最小化**(荷重を均す)に、
接線力の L1 和を 1e-3 の重みで足したもの(足どうしで押し合う内力 = 解の不定さを消す)。

* 多角錐は錐の内側(頂点が錐面の上)なので、ここで実行可能なら真の摩擦錐でも実行可能。
  逆は ``n_facets`` が小さいと成り立たない(縁の近くは保守的)。
* 平地(法線がすべて +z)では、μ > 0 なら「解がある ⇔ COM の地面への射影が支持多角形の
  内側」(接線力は z = 0 の点で水平な軸のまわりのモーメントを作れない)。
  :func:`com_support_margin` と突き合わせる門が tests にある。
* ``contacts`` (N, 3) [m]、``normals`` (N, 3)(正規化する。外向き = 地面から足へ)、
  ``com`` (3,) [m]、``mass`` [kg] > 0、``mu`` ≥ 0(0 なら摩擦なし = 法線だけ)。
* 返り値 ``{"feasible", "forces" (N, 3) [N] か None, "normal" (N,), "tangential" (N,),
  "max_normal", "residual"(釣り合いの残差 [N]、[N·m]), "status", "message"}``。
  解が無ければ ``feasible = False``、力は ``None``。

空の入力(``contacts`` が 0 要素)は ValueError で拒否する。

English: friction cones are replaced by inscribed ``n_facets``-sided pyramids, so a
feasible answer here is feasible for the true cone. The LP minimises the largest normal
force plus 1e-3 x the L1 tangential force. On flat ground with mu > 0, feasibility is
equivalent to the COM projection lying inside the support polygon.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`locomotion`)

[contact_points](contact_points.md) · [com_from_silhouette](com_from_silhouette.md) · [support_polygon](support_polygon.md) · [com_support_margin](com_support_margin.md) · [gait_phase](gait_phase.md) · [support_line_margin](support_line_margin.md) · [lipm_capture_point](lipm_capture_point.md) · [capture_margin](capture_margin.md)

---
*Provenance: locomotion.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
