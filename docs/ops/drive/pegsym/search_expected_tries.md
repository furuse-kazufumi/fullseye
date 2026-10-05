---
op: search_expected_tries
dim: drive
category: pegsym
in: scalar × scalar
out: table
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# search_expected_tries — DRIVE `pegsym` op

- **データ種**: `scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.search_expected_tries(n_sym: 'int', phi_cap: 'float', order: 'str' = 'alternate', estimate_sigma: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import pegsym; pegsym.search_expected_tries(n_sym: 'int', phi_cap: 'float', order: 'str' = 'alternate', estimate_sigma: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("search_expected_tries")`)

## 使い方

回転の探索の期待試行回数(未知の向きの誤差 e が 1 周期に一様のとき、厳密)。候補 c_k(:func:`rotation_search_plan`)で k 回目に
入るのは e が [c_k − φ, c_k + φ] (周期 P)に初めて入った時なので E = Σ_k (1 − |∪_{i<k} I_i|/P)。計算は区間の端で円周を割り、
小区間ごとに最初に覆う候補の番号を数える(同じ値、O(M²) のベクトル演算)。刻みが
ちょうど 2φ なら E = (M + 1)/2(``closed``)。対称を知らない探索(周期 2π、M₁ = ⌈π/φ⌉)との比 ``ratio_vs_blind`` → 1/n。
``estimate_sigma`` [rad] を渡すと、e が推定値のまわりに標準偏差 σ の正規(周期に巻いたもの)で、"alternate" の順の期待回数も返す
(``expected_with_estimate``、数値積分 4,096 点)。返り ``expected``・``closed``・``M``・``blind_expected``・``ratio_vs_blind``。
**Raises** ValueError: n_sym < 1、phi_cap ≤ 0、sigma ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_symmetry_search](../../../../examples/poc_peg_symmetry_search.py) — `py -3.11 examples/poc_peg_symmetry_search.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsym`)

[polygon_peg](polygon_peg.md) · [polygon_offset](polygon_offset.md) · [polygon_fit_check](polygon_fit_check.md) · [rotation_window](rotation_window.md) · [polygon_two_point_depth](polygon_two_point_depth.md) · [polygon_coverage_image](polygon_coverage_image.md) · [plane_topview](plane_topview.md) · [polygon_yaw_read](polygon_yaw_read.md)

---
*Provenance: pegsym.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
