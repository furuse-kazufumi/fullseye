---
op: awb_gains
dim: gfx2d
category: isp
in: rgb
out: vector
examples: [raw_to_display_isp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# awb_gains — GFX2D `isp` op

- **データ種**: `rgb` → `vector`
- **呼び出し**: `import fullseye as fs; fs.ledger.awb_gains(rgb, method='gray_world', percentile=99.0)` (実装を直接呼ぶなら `import gfx2d; gfx2d.awb_gains(rgb, method='gray_world', percentile=99.0)`、台帳から引くなら `opsgfx2d.get("awb_gains")`)

## 使い方

Estimate white-balance gains ``(g_R, g_G, g_B)`` with ``g_G = 1``.

``method="gray_world"``: the scene averages to grey, so ``g_c = mean_G /
mean_c`` (Buchsbaum, 1980). ``method="white_patch"``: the brightest
surfaces are white, so ``g_c = P_G / P_c`` with ``P`` the *percentile*
(default 99, i.e. not the single hottest pixel) of each channel. Both are
closed forms; neither is right for every scene (a red wall breaks
gray-world, a coloured light breaks white-patch) and the docstring says so
rather than picking one silently. Apply with :func:`rgb_apply_gains` or,
on the mosaic, :func:`raw_apply_gains`.

Ground truth: after applying gray-world gains the three channel means are
equal to 1e-12; after white-patch gains the three percentiles are equal.
**Raises** ``ValueError``: unknown *method*, a channel whose statistic is 0
(no gain can be defined), or a *percentile* outside ``(0, 100]``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [raw_to_display_isp](../../../../examples/raw_to_display_isp.py) — `py -3.11 examples/raw_to_display_isp.py`

## 型が繋がる次の op(`vector` を入力に取れる)

[rgb_apply_gains](rgb_apply_gains.md) · [raw_apply_gains](raw_apply_gains.md)

## 同カテゴリ(`isp`)

[raw_black_level](raw_black_level.md) · [raw_dead_pixel_mask](raw_dead_pixel_mask.md) · [raw_dead_pixel_correct](raw_dead_pixel_correct.md) · [lens_shading_gain](lens_shading_gain.md) · [lens_shading_correct](lens_shading_correct.md) · [rgb_apply_gains](rgb_apply_gains.md) · [raw_apply_gains](raw_apply_gains.md) · [raw_demosaic_bilinear](raw_demosaic_bilinear.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
