---
op: piv_ensemble_correlate
dim: piv
category: estimate
in: images
out: flow2d
examples: [piv_field_analysis_tour, poc_river_surface_velocity]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# piv_ensemble_correlate — PIV `estimate` op

- **データ種**: `images` → `flow2d`
- **呼び出し**: `import pivops; pivops.piv_ensemble_correlate(images, window=32, overlap=0.5, peak='gauss3', window_func='hann', normalize='overlap', search_limit=0.25)` (または `opspiv.get("piv_ensemble_correlate")`)

## 使い方

相関マップを**足してから**ピークを探す(アンサンブル相関)。

粒子が少ない・雑音が多い場合、1 対ずつ測って平均すると**外れたベクトルの
平均**になる。相関の段階で足すと、弱いピークが同じ場所に積み上がって
立ち上がる。定常流(全対で変位が同じ)が前提。

Args:
    images: 2 枚以上の画像の列。連続する対 ``(k, k+1)`` を使う。
    window / overlap / peak / window_func / normalize / search_limit:
        :func:`piv_cross_correlate` と同じ。
Returns:
    ``(flow (2, h, w), info)``。``info["pairs"]`` に使った対の数。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_field_analysis_tour](../../../../examples/piv_field_analysis_tour.py) — `py -3.11 examples/piv_field_analysis_tour.py`
- [poc_river_surface_velocity](../../../../examples/poc_river_surface_velocity.py) — `py -3.11 examples/poc_river_surface_velocity.py`

## 型が繋がる次の op(`flow2d` を入力に取れる)

[piv_deform_pass](piv_deform_pass.md) · [piv_outlier_mask](../validate/piv_outlier_mask.md) · [piv_replace_outliers](../validate/piv_replace_outliers.md) · [piv_vorticity](../field/piv_vorticity.md) · [piv_divergence](../field/piv_divergence.md) · [piv_flow_magnitude](../field/piv_flow_magnitude.md) · [piv_to_velocity](../field/piv_to_velocity.md) · [piv_velocity_gradient](../field/piv_velocity_gradient.md)

## 同カテゴリ(`estimate`)

[piv_cross_correlate](piv_cross_correlate.md) · [piv_multipass](piv_multipass.md) · [piv_deform_pass](piv_deform_pass.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
