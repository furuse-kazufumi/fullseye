---
op: sphere_probing_error
dim: acceptance
category: evaluate
in: points
out: table
gpu: なし
examples: [poc_3d_sensor_modalities]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# sphere_probing_error — ACCEPTANCE `evaluate` op

- **データ種**: `points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sphere_probing_error(points, calibrated_diameter, exclude_fraction=0.003)` (実装を直接呼ぶなら `import acceptance3d; acceptance3d.sphere_probing_error(points, calibrated_diameter, exclude_fraction=0.003)`、台帳から引くなら `opsacceptance.get("sphere_probing_error")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

球の点群から探針の誤差の形状 PF と寸法 PS を計算する(``table``)。

Probing error of form (PF) and of size (PS) from the point cloud of one calibrated sphere.

ガウスの最小二乗で半径自由の球を当て(代数解を初期値に Gauss-Newton)、半径方向の偏差が最大の点を
``floor(exclude_fraction · N)`` 個まで除いて当て直す。``pf = R_max − R_min``(除外後の点の、当てた中心から
の距離の範囲)、``ps = 2R − calibrated_diameter``(符号つき: 大きく測れば正)。
A free-radius least-squares sphere is fitted, at most ``floor(exclude_fraction*N)`` points with the
largest radial deviation are dropped and the sphere refitted; ``pf`` is the range of radial distances,
``ps`` the signed diameter error. Definitions as described in Carfagni et al. 2019 (doi:10.3390/s19030489)
for VDI/VDE 2634 Part 2 — the normative text is not reproduced; this is not a conformance claim.

返す ``dict``: ``pf``、``ps``、``diameter``、``radius``、``center`` (3,)、``residual_rms``、``n_points``、
``n_used``、``n_excluded``、``exclude_fraction``、``calibrated_diameter``。単位は入力の点の単位のまま。
限界: 球冠しか見えない点群(片側から撮った球)では半径と中心が相関し、PS は雑音に敏感になる
(見えている角度が小さいほど)。``residual_rms`` が雑音の目安。

**Raises** ``ValueError``: 点が (N, 3) でない・10 点未満・非有限、同一平面上(球が定まらない)、
``calibrated_diameter`` が正でない、``exclude_fraction`` が [0, 0.05] の外。

## 詳しい使い方ガイド

- [optical_3d_acceptance ファミリ ガイド](../guides/optical_3d_acceptance.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_3d_sensor_modalities](../../../../examples/poc_3d_sensor_modalities.py) — `py -3.11 examples/poc_3d_sensor_modalities.py`

## 型が繋がる次の op(`table` を入力に取れる)

[acceptance_verdict](acceptance_verdict.md) · [acceptance_scan](../simulate/acceptance_scan.md) · [virtual_acceptance_test](../simulate/virtual_acceptance_test.md) · [acceptance_error_budget](../budget/acceptance_error_budget.md)

## 同カテゴリ(`evaluate`)

[sphere_spacing_error](sphere_spacing_error.md) · [plane_flatness_error](plane_flatness_error.md) · [acceptance_verdict](acceptance_verdict.md)

---
*Provenance: acceptance3d.py — ACCEPTANCE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
