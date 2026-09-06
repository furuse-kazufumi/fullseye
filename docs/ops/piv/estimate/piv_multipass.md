---
op: piv_multipass
dim: piv
category: estimate
in: image2d × image2d
out: flow2d
examples: [piv_flow_from_particles, poc_strain_history]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# piv_multipass — PIV `estimate` op

- **データ種**: `image2d × image2d` → `flow2d`
- **呼び出し**: `import pivops; pivops.piv_multipass(a, b, windows=(64, 32), overlap=0.5, peak='gauss3', window_func='hann', outlier_threshold=2.0, normalize='overlap', search_limit=0.25)` (または `opspiv.get("piv_multipass")`)

## 使い方

粗い窓から細かい窓へ段を下げる多段 PIV。返りは ``(flow, info)``。

各段の結果を**次の段の予測変位**として使う(整数量だけ 2 枚目の窓をずらす)。
段の間で外れ値を除いて埋めるのは意図的 —— 外れたベクトルをそのまま予測に
使うと、その窓は次の段でも外れたまま固定される。

Args:
    a, b: 画像対。
    windows: 大きい順の窓列。各段は前段の**倍数関係でなくてよい**が、
        格子が変わるので予測は最近傍で載せ替える。
    overlap / peak / window_func: :func:`piv_cross_correlate` と同じ。
    outlier_threshold: 段間の正規化中央値検定の閾値。``None`` で無効。
Returns:
    最終段の ``(flow, info)``。``info["passes"]`` に各段の窓の大きさ。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_flow_from_particles](../../../../examples/piv_flow_from_particles.py) — `py -3.11 examples/piv_flow_from_particles.py`
- [poc_strain_history](../../../../examples/poc_strain_history.py) — `py -3.11 examples/poc_strain_history.py`

## 型が繋がる次の op(`flow2d` を入力に取れる)

[piv_deform_pass](piv_deform_pass.md) · [piv_outlier_mask](../validate/piv_outlier_mask.md) · [piv_replace_outliers](../validate/piv_replace_outliers.md) · [piv_vorticity](../field/piv_vorticity.md) · [piv_divergence](../field/piv_divergence.md) · [piv_flow_magnitude](../field/piv_flow_magnitude.md) · [piv_to_velocity](../field/piv_to_velocity.md) · [piv_velocity_gradient](../field/piv_velocity_gradient.md)

## 同カテゴリ(`estimate`)

[piv_cross_correlate](piv_cross_correlate.md) · [piv_deform_pass](piv_deform_pass.md) · [piv_ensemble_correlate](piv_ensemble_correlate.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
