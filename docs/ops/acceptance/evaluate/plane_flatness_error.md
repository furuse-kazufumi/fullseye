---
op: plane_flatness_error
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

# plane_flatness_error — ACCEPTANCE `evaluate` op

- **データ種**: `points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.plane_flatness_error(points, exclude_fraction=0.003)` (実装を直接呼ぶなら `import acceptance3d; acceptance3d.plane_flatness_error(points, exclude_fraction=0.003)`、台帳から引くなら `opsacceptance.get("plane_flatness_error")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

平面の点群から平面度の誤差 F(最小二乗平面からの符号つき距離の範囲)を計算する(``table``)。

Flatness measurement error F: range of signed distances from the least-squares (orthogonal-
regression) plane, after dropping at most ``floor(exclude_fraction*N)`` largest deviations and
refitting once. Definition as described in Carfagni et al. 2019 for VDI/VDE 2634 Part 2.

★最小二乗の平面(Gauss)であり、最小領域(Chebyshev)の平面ではない。最小領域の F は最小二乗の F 以下になる
(定義から)。正弦のうねり(振幅 A、周期の整数倍)を持つ平面では最小二乗の平面が公称の平面と一致し、F = 2A。

返す ``dict``: ``f``、``normal`` (3,)、``center`` (3,)、``residual_rms``、``n_points``、``n_used``、``n_excluded``。

**Raises** ``ValueError``: 点が (N, 3) でない・10 点未満・非有限、共線(法線が定まらない)、
``exclude_fraction`` が [0, 0.05] の外。

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

[sphere_probing_error](sphere_probing_error.md) · [sphere_spacing_error](sphere_spacing_error.md) · [acceptance_verdict](acceptance_verdict.md)

---
*Provenance: acceptance3d.py — ACCEPTANCE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
