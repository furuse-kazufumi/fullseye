---
op: sphere_spacing_error
dim: acceptance
category: evaluate
in: points × points
out: table
gpu: なし
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# sphere_spacing_error — ACCEPTANCE `evaluate` op

- **データ種**: `points × points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sphere_spacing_error(points_a, points_b, calibrated_distance, exclude_fraction=0.003, fixed_diameter=None)` (実装を直接呼ぶなら `import acceptance3d; acceptance3d.sphere_spacing_error(points_a, points_b, calibrated_distance, exclude_fraction=0.003, fixed_diameter=None)`、台帳から引くなら `opsacceptance.get("sphere_spacing_error")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

ダンベル(2 球)の点群から球間距離の誤差 SD を計算する(``table``)。

Sphere-spacing error SD of a ball bar: distance of the two fitted sphere centres minus the
calibrated distance (signed: positive when measured too long).

各球は :func:`sphere_probing_error` と同じ当てはめ(半径自由、最大偏差の点を除いて当て直し)。
``fixed_diameter`` を与えると半径をその値に固定して中心だけを当てる(文献によっては固定半径で評価する;
既定は自由)。定義は Carfagni et al. 2019 / Eiríksson et al. 2016 の記述による。規格本文の写しではない。
Each sphere is fitted as in :func:`sphere_probing_error`; ``fixed_diameter`` fixes the radius.

返す ``dict``: ``sd``、``distance``、``calibrated_distance``、``center_a``、``center_b``、
``diameter_a``、``diameter_b``、``pf_a``、``pf_b``、``n_used_a``、``n_used_b``。
限界: 尺度の誤差は SD に ``(s−1)·L`` で出る(L が長いほど見える)ので、L は測定体積の対角に近いほどよい。

**Raises** ``ValueError``: どちらかの点群が不正(:func:`sphere_probing_error` と同じ条件)、
``calibrated_distance`` が正でない、``fixed_diameter`` が正でない、2 つの中心が重なる。

## 詳しい使い方ガイド

- [optical_3d_acceptance ファミリ ガイド](../guides/optical_3d_acceptance.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[acceptance_verdict](acceptance_verdict.md) · [acceptance_scan](../simulate/acceptance_scan.md) · [virtual_acceptance_test](../simulate/virtual_acceptance_test.md) · [acceptance_error_budget](../budget/acceptance_error_budget.md)

## 同カテゴリ(`evaluate`)

[sphere_probing_error](sphere_probing_error.md) · [plane_flatness_error](plane_flatness_error.md) · [acceptance_verdict](acceptance_verdict.md)

---
*Provenance: acceptance3d.py — ACCEPTANCE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
