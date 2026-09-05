---
op: alife_sandpile
dim: 2d
category: artificial-life
in: image
out: image
examples: [gallery2d_physics_alife_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# alife_sandpile — 2D `artificial-life` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "alife_sandpile", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Abelian sandpile / self-organised criticality (Bak-Tang-Wiesenfeld 1987).

The image is quantised to integer grain heights h = round(K * image) with
K = 4 + int(12a), then relaxed by the BTW toppling rule: a cell with 4 or
more grains gives one grain to each orthogonal neighbour and keeps the rest.
The boundary is dissipative (grains leaving the grid are lost), which is what
lets the pile settle into the self-organised critical state where every cell
holds at most 3 grains.

``a`` sets the initial grain scale K (how supercritical the pile starts);
``b`` sets the number of parallel relaxation sweeps 1 + int(50b). For
b >= 0.9 the pile relaxes *toward* stability with early termination, but the
sweep count is bounded by a total-work budget (``_SANDPILE_BUDGET`` grain-
updates) so the op stays fast on any image size: a small or varied pile
reaches the stable critical state (every cell <= 3), while a very large
maximally-supercritical pile is only partially relaxed (full BTW
stabilisation is O(L^2) sweeps). Returns h / max(h) in [0, 1]; a fully
relaxed pile (max 3) takes values in {0, 1/3, 2/3, 1} (or {0, 1/2, 1} when
the stable maximum is 2).

## 詳しい使い方ガイド

- [gallery2d_physics_alife_3d ファミリ ガイド](../guides/gallery2d_physics_alife_3d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_physics_alife_3d](../../../../examples/gallery2d_physics_alife_3d.py) — `py -3.11 examples/gallery2d_physics_alife_3d.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`artificial-life`)

[alife_gray_scott](alife_gray_scott.md) · [alife_turing](alife_turing.md) · [alife_life_step](alife_life_step.md) · [alife_cyclic_ca](alife_cyclic_ca.md) · [alife_perona_malik](alife_perona_malik.md) · [alife_curvature_flow](alife_curvature_flow.md) · [alife_dla](alife_dla.md) · [alife_reaction_bz](alife_reaction_bz.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
