---
op: tac_surface_normal
dim: 2d
category: tactile
in: image
out: image
examples: [sim2real_and_alife]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# tac_surface_normal — 2D `tactile` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "tac_surface_normal", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Surface-normal z-component (slope map) from the shading gradients, using
Horn's shape-from-shading normal parameterisation
``n = (-p, -q, 1)/sqrt(1+p^2+q^2)`` so that ``nz = 1/sqrt(1+p^2+q^2)`` with
``p = gain*gx``, ``q = gain*gy``. Flat (uncontacted) gel gives nz = 1, steep
indentation walls tend to 0, so the map is already a valid [0,1] encoding.
``a`` = gradient gain (1..21x -- how steep the shading is taken to be),
``b`` = pre-smoothing sigma of the image (0..3) to tame sensor noise.
Constant input -> all-ones (perfectly flat gel).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sim2real_and_alife](../../../../examples/sim2real_and_alife.py) — `py -3.11 examples/sim2real_and_alife.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`tactile`)

[tac_contact_mask](tac_contact_mask.md) · [tac_height_from_shading](tac_height_from_shading.md) · [tac_pressure_proxy](tac_pressure_proxy.md) · [tac_shear_field](tac_shear_field.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
