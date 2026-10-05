---
op: symmetry_order_contour
dim: drive
category: pegtactile
in: matrix
out: table
examples: [poc_peg_insertion_tactile]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# symmetry_order_contour — DRIVE `pegtactile` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.symmetry_order_contour(contour, K: 'int' = 24, rel: 'float' = 0.01) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.symmetry_order_contour(contour, K: 'int' = 24, rel: 'float' = 0.01) -> 'dict'`、台帳から引くなら `opsdrive.get("symmetry_order_contour")`)

## 使い方

閉輪郭 (N, 2) = (row, col) の複素フーリエ係数(:func:`fourierdesc.contour_fourier_complex`、弧長で打ち直し、±K 次)から n 回対称の
次数を読む: n 回対称なら非零の係数は k ≡ 1 (mod n) だけ。有意(|c_k| > rel·|c_1|、k ≠ 0, 1)な k の (k − 1) の最大公約数が n。
有意な k が無ければ円(``n`` = 0 = 連続)。向き α̂ = arg(c₁₋ₙ c₁ⁿ⁻¹)/n(始点の取り方に依らない不変量、mod 2π/n)。n = 1 は
c₂ c₁⁻² から α̂ = −arg(·) —— k = −1(振幅は 3 倍)は形ごとの定数位相が違い、枝(α / α + π)を参照なしに決められない(試作で
180° 取り違えた)。返り ``n``・``angle``(rad、n = 0 は nan)・``amps``(k → |c_k|/|c_1|)・``sig``・``centroid``(c₀ = (row, col))。
2 次モーメントの向きは n ≥ 3 で慣性が等方になり使えない(PoC の罠の門)。**Raises** ValueError: 輪郭が (N ≥ 8, 2) でない、K < 6。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegtactile`)

[pad_params](pad_params.md) · [pad_context](pad_context.md) · [peg_wrench_to_pad_loads](peg_wrench_to_pad_loads.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_shear_asymmetry](pad_shear_asymmetry.md) · [pad_marker_displacement](pad_marker_displacement.md) · [pad_tactile_frame](pad_tactile_frame.md) · [pad_tactile_read](pad_tactile_read.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
