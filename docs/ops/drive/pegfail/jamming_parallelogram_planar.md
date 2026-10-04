---
op: jamming_parallelogram_planar
dim: drive
category: pegfail
in: table × scalar
out: table
examples: [poc_peg_failure_recovery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# jamming_parallelogram_planar — DRIVE `pegfail` op

- **データ種**: `table × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.jamming_parallelogram_planar(kp, depth: 'float') -> 'dict'` (実装を直接呼ぶなら `import pegfail; pegfail.jamming_parallelogram_planar(kp, depth: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("jamming_parallelogram_planar")`)

## 使い方

かじりの平行四辺形を **二点接触の平面静力学から導く**(pegsim.jamming_diagram の頂点 = OCW p.34 の値と突き合わせる第 2 経路)。

平面(x 右、z 上)で、先端の縁が −x 側の壁に深さ l で触れ(法線力 f₁ ≥ 0、+x 向き)、+x 側の口の縁が胴に触れる(f₂ ≥ 0、−x 向き)。
両点が下へ滑る Coulomb 摩擦(上向き μf)で、先端に加える (F_x, F_z 下向き正, M 反時計回り正) の釣り合いは
    F_x = f₂ − f₁、F_z = μ(f₁ + f₂)、M = μ r f₁ − (μ r + l) f₂
→ M/(rF_z) = −λ − μ(λ + 1)·(F_x/F_z)、λ = l/(2rμ)。鏡像の配置(先端が +x の壁)は +λ − μ(λ+1)x。f₁ = 0 / f₂ = 0 が
|F_x/F_z| = 1/μ の縦の辺(一点接触の摩擦限界)。4 頂点 = 2 本の斜辺 × 2 本の縦辺の交点 = (−1/μ, 2λ+1), (1/μ, −1), (1/μ, −(2λ+1)),
(−1/μ, 1)(OCW の順)。返り: ``lambda``、``slope`` = −μ(λ+1)、``vertices``(4, 2)、``line_minus``・``line_plus``(切片)。
**Raises** ``ValueError``: l < 0、μ ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_failure_recovery](../../../../examples/poc_peg_failure_recovery.py) — `py -3.11 examples/poc_peg_failure_recovery.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegfail`)

[insertion_failure_table](insertion_failure_table.md) · [insertion_failure_validate](insertion_failure_validate.md) · [insertion_signature](insertion_signature.md) · [insertion_failure_classify](insertion_failure_classify.md) · [insertion_recovery_primitive](insertion_recovery_primitive.md) · [jamming_force_check](jamming_force_check.md) · [wedging_risk](wedging_risk.md) · [insertion_stall_detect](insertion_stall_detect.md)

---
*Provenance: pegfail.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
