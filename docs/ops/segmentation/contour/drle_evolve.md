---
op: drle_evolve
dim: segmentation
category: contour
in: image2d × mask
out: table
examples: [poc_active_contours]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# drle_evolve — SEGMENTATION `contour` op

- **データ種**: `image2d × mask` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.drle_evolve(image, init, *, mu: 'Optional[float]' = None, lambda_: 'float' = 5.0, alpha: 'float' = 1.5, epsilon: 'float' = 1.5, dt: 'float' = 1.0, sigma: 'float' = 1.5, k: 'float' = 0.00392156862745098, g=None, n_iter: 'int' = 300, c0: 'float' = 2.0, potential: 'str' = 'double_well', record_every: 'int' = 0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segcontour; segcontour.drle_evolve(image, init, *, mu: 'Optional[float]' = None, lambda_: 'float' = 5.0, alpha: 'float' = 1.5, epsilon: 'float' = 1.5, dt: 'float' = 1.0, sigma: 'float' = 1.5, k: 'float' = 0.00392156862745098, g=None, n_iter: 'int' = 300, c0: 'float' = 2.0, potential: 'str' = 'double_well', record_every: 'int' = 0) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("drle_evolve")`)

## 使い方

距離正則化レベルセット DRLSE(Li–Xu–Gui–Fox 2010)のエッジ版。再初期化しない。

φ_t = μ div(d_p(|∇φ|)∇φ) + λ δ_ε(φ) div(g ∇φ/|∇φ|) + α g δ_ε(φ)(φ < 0 が内側、α > 0 で縮む)。
d_p(s) = p'(s)/s。二重井戸 p2(s) = (1 − cos 2πs)/(2π)²(s ≤ 1)、(s − 1)²/2(s ≥ 1)、単井戸 p1(s) = (s − 1)²/2。
初期 = 2 値の段差(内側 −c0、外側 +c0、Li の例と同じ)。g = ``edge_stop_g(image, sigma, k)`` の g(``g`` で直接与えても
よい)。μ の既定は 0.2/dt、CFL 条件 μ dt < 1/4 を満たさなければ ValueError。境界は Li のコードの Neumann。
エネルギー ε(φ) = μ Σ p(|∇φ|) + λ Σ g δ_ε(φ)|∇φ| + α Σ g H_ε(−φ) も各反復で記録する(実測、門ではない)。
返り値: ``mask``(φ < 0)、``phi``、``grad``(|φ| ≤ ε の |∇φ| 分位点)、``grad_trace``(record_every ごとの中央値)、
``energy``、``n_increase``、``history``、``n_iter``。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [active_contours_and_level_sets](../guides/active_contours_and_level_sets.md) — 変分・動的輪郭とレベルセット — どの輪郭がどこで止まり、何を保証するか

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_active_contours](../../../../examples/poc_active_contours.py) — `py -3.11 examples/poc_active_contours.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`contour`)

[snake_evolve](snake_evolve.md) · [gvf_field](gvf_field.md) · [chan_vese_energy](chan_vese_energy.md) · [chan_vese_evolve](chan_vese_evolve.md) · [morph_chan_vese](morph_chan_vese.md) · [morph_geodesic_ac](morph_geodesic_ac.md) · [edge_stop_g](edge_stop_g.md) · [level_set_reinit](level_set_reinit.md)

---
*Provenance: segcontour.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
