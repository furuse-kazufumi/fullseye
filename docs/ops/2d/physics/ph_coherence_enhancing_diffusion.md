---
op: ph_coherence_enhancing_diffusion
dim: 2d
category: physics
in: image
out: image
examples: [gallery2d_physics_alife_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# ph_coherence_enhancing_diffusion — 2D `physics` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "ph_coherence_enhancing_diffusion", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Weickert coherence-enhancing diffusion (HALCON ``coherence_enhancing_diff``).

Builds the structure tensor J_rho = G_rho * (grad I_sigma . grad I_sigma^T),
eigendecomposes it, and diffuses with a tensor whose ALONG-structure eigenvalue
grows with local coherence (mu1-mu2)^2 while the ACROSS-structure eigenvalue
stays small — so noise is smoothed along coherent lines/flow without blurring
across them. Update  I <- I + dt * div(D grad I). ``a`` sets the step count,
``b`` the integration scale rho.

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

## 同カテゴリ(`physics`)

[ph_perona_malik](ph_perona_malik.md) · [ph_reaction_diffusion](ph_reaction_diffusion.md) · [ph_heat_flow](ph_heat_flow.md) · [ph_mean_curvature_motion](ph_mean_curvature_motion.md) · [ph_total_variation_flow](ph_total_variation_flow.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
