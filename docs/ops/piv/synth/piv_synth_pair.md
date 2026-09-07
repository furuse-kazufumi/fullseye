---
op: piv_synth_pair
dim: piv
category: synth
in: 
out: image2d
examples: [piv_field_analysis_tour, piv_flow_from_particles, poc_strain_history]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# piv_synth_pair — PIV `synth` op

- **データ種**: `なし` → `image2d`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import pivops; pivops.piv_synth_pair(shape, displacement, density=0.02, diameter_px=2.5, seed=0, noise_sigma=0.0, intensity=(0.6, 1.0), background=0.0)` (または `opspiv.get("piv_synth_pair")`)
- **台帳経由の戻り値**: `fullseye.ledger.piv_synth_pair(...)` は**宣言 out 型 `image2d` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.piv_synth_pair.raw(...)`、または `pivops.piv_synth_pair` を直接呼ぶ。
  - 本体の返り: `(a, b, truth) -> image2d`

## 使い方

既知の変位場を持つ画像対を作る。返りは ``(image_a, image_b, truth)``。

**粒子を動かしてから 2 枚目を描く**(1 枚目を補間で歪めるのではない)。
補間で作ると、補間の平滑化が「PIV が当てやすい絵」を作ってしまい、
自分の実装を自分に有利な入力で測ることになる。

Args:
    shape: ``(H, W)``。
    displacement: 変位の与え方。次のいずれか。

        * 長さ 2 の列 —— 一様並進 ``(dy, dx)`` [px]。
        * ``callable(rows, cols) -> (dy, dx)`` —— 位置に依存する場。
          引数は粒子の連続座標の配列。
    density / diameter_px / seed / intensity / background: :func:`piv_synth_particles` と同じ。
    noise_sigma: 2 枚それぞれに独立に足す加法ガウス雑音の標準偏差。
Returns:
    ``(a (H, W), b (H, W), truth (2, H, W))``。``truth`` は**画素ごと**の
    真の変位で、窓の格子に落とすには :func:`piv_sample_at_windows` を使う。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_field_analysis_tour](../../../../examples/piv_field_analysis_tour.py) — `py -3.11 examples/piv_field_analysis_tour.py`
- [piv_flow_from_particles](../../../../examples/piv_flow_from_particles.py) — `py -3.11 examples/piv_flow_from_particles.py`
- [poc_strain_history](../../../../examples/poc_strain_history.py) — `py -3.11 examples/poc_strain_history.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[piv_cross_correlate](../estimate/piv_cross_correlate.md) · [piv_multipass](../estimate/piv_multipass.md) · [piv_deform_pass](../estimate/piv_deform_pass.md) · [strain_from_displacement](../solid/strain_from_displacement.md) · [correlation_quality](../solid/correlation_quality.md) · [speckle_quality](../solid/speckle_quality.md)

## 同カテゴリ(`synth`)

[piv_synth_particles](piv_synth_particles.md) · [piv_synth_sequence](piv_synth_sequence.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
