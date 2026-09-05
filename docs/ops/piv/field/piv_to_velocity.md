---
op: piv_to_velocity
dim: piv
category: field
in: flow2d
out: flow2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# piv_to_velocity — PIV `field` op

- **データ種**: `flow2d` → `flow2d`
- **呼び出し**: `import pivops; pivops.piv_to_velocity(flow, pixel_size_m, dt_s)` (または `opspiv.get("piv_to_velocity")`)

## 使い方

画素/フレーム → m/s。**両方とも必須引数**(既定値を置かない)。

単位の取り違えは例外を出さずに桁を変えるので、既定値を置くと事故が既定に
なる —— ``demops`` の ``cell_size`` と同じ判断。

Returns:
    ``(2, h, w)`` [m/s]。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`flow2d` を入力に取れる)

[piv_outlier_mask](../validate/piv_outlier_mask.md) · [piv_replace_outliers](../validate/piv_replace_outliers.md) · [piv_vorticity](piv_vorticity.md) · [piv_divergence](piv_divergence.md) · [piv_flow_magnitude](piv_flow_magnitude.md) · [piv_sample_at_windows](../assess/piv_sample_at_windows.md) · [piv_error_stats](../assess/piv_error_stats.md) · [piv_peak_locking](../assess/piv_peak_locking.md)

## 同カテゴリ(`field`)

[piv_vorticity](piv_vorticity.md) · [piv_divergence](piv_divergence.md) · [piv_flow_magnitude](piv_flow_magnitude.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
