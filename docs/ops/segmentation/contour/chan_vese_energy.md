---
op: chan_vese_energy
dim: segmentation
category: contour
in: image2d × mask
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# chan_vese_energy — SEGMENTATION `contour` op

- **データ種**: `image2d × mask` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.chan_vese_energy(image, phi, *, mu: 'float' = 0.1, nu: 'float' = 0.0, lambda1: 'float' = 1.0, lambda2: 'float' = 1.0, eps: 'float' = 1.0, eta: 'float' = 0.1) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import segcontour; segcontour.chan_vese_energy(image, phi, *, mu: 'float' = 0.1, nu: 'float' = 0.0, lambda1: 'float' = 1.0, lambda2: 'float' = 1.0, eps: 'float' = 1.0, eta: 'float' = 0.1) -> 'Dict[str, float]'`、台帳から引くなら `opssegmentation.get("chan_vese_energy")`)

## 使い方

Chan–Vese 2001 のエネルギー F = μ Length + ν Area(inside) + λ1 ∫_in |I − c1|² + λ2 ∫_out |I − c2|²(2 相)。

``phi`` は φ(内側 φ < 0)か bool のマスク(符号付き距離に直す)。正則化: 内側の重み H_ε(−φ)(論文の arctan 版)、
長さ = Σ δ_ε(φ) |Dφ|_η(前進差分、|Dφ|_η = √(D_x² + D_y² + η²))。c1 / c2 = 内 / 外の H_ε で重みづけた平均(式 (6)(7))。
同じマスクの「鋭い」版(``energy_sharp``)も返す: 長さ = 4 近傍で内外が変わる辺の数、内外は φ < 0 で 0/1。
返り値: ``energy``、``length``、``area``、``fit_inside`` / ``fit_outside``、``c1`` / ``c2``(H_ε で重みづけた平均 ——
ε = 1 の arctan は裾が長いので 2 値の画像でも 0/1 から離れる)、``energy_sharp``、``perimeter_sharp``、
``c1_sharp`` / ``c2_sharp``(φ < 0 の内外の平均)。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [active_contours_and_level_sets](../guides/active_contours_and_level_sets.md) — 変分・動的輪郭とレベルセット — どの輪郭がどこで止まり、何を保証するか

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`contour`)

[snake_evolve](snake_evolve.md) · [gvf_field](gvf_field.md) · [chan_vese_evolve](chan_vese_evolve.md) · [morph_chan_vese](morph_chan_vese.md) · [morph_geodesic_ac](morph_geodesic_ac.md) · [edge_stop_g](edge_stop_g.md) · [level_set_reinit](level_set_reinit.md) · [drle_evolve](drle_evolve.md)

---
*Provenance: segcontour.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
