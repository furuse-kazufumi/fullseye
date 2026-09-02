---
op: cosmic_ray_reject
dim: astrostack
category: cosmic
in: image2d
out: image2d
examples: [astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# cosmic_ray_reject — ASTROSTACK `cosmic` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import astrostack; astrostack.cosmic_ray_reject(frame, sigma=5.0, f_lim=2.0, replace_box=5, iters=1)` (または `opsastrostack.get("cosmic_ray_reject")`)

## 使い方

単一フレームの宇宙線除去(ラプラシアン鋭度)。

van Dokkum, *Cosmic-Ray Rejection by Laplacian Edge Detection*,
PASP 113, 1420 (2001) の考え方 —— 宇宙線は**星より鋭い**。星は PSF で
ぼけているので必ず数画素にまたがるが、宇宙線は光学系を通っていないので
1〜数画素で立ち上がる。そこで

1. ラプラシアン ``L`` の正の成分を雑音で規格化した有意度
   ``S = L / (2 sigma_noise)`` を作り、
2. 微細構造像 ``F = median3 - median7(median3)`` と比べて ``L / F`` が
   ``f_lim`` を超えるものだけを宇宙線とする。

2 番目の条件が無いと**星の中心が必ず宇宙線に見える**(星も局所的には
尖っている)。``f_lim`` はその境目で、原論文の推奨は 2.0。

``iters`` を増やすと、除去 → 再測定を繰り返す(大きなヒットの裾が残るとき)。
置換は ``replace_box`` の窓での**非汚染画素の中央値**。

Returns ``(cleaned, mask)``:

* ``cleaned`` —— ``(H, W)`` float64、宇宙線画素を置換した像。
* ``mask`` —— ``(H, W)`` bool、``True`` = 宇宙線と判定した画素。

**Raises** ``ValueError``: 2-D でない / 非有限を含む / *sigma* が非正 /
*f_lim* が非正 / *replace_box* が 3 未満または偶数の場合。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[frame_quality](../quality/frame_quality.md) · [noise_sigma](../quality/noise_sigma.md) · [star_detect](../photometry/star_detect.md) · [psf_fit](../photometry/psf_fit.md) · [aperture_photometry](../photometry/aperture_photometry.md) · [frame_align](../align/frame_align.md)

## 同カテゴリ(`cosmic`)

[cosmic_ray_reject_stack](cosmic_ray_reject_stack.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
