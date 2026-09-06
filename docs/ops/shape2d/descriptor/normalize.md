---
op: normalize
dim: shape2d
category: descriptor
in: efdmodel
out: matrix
examples: [piv_flow_from_particles]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# normalize — SHAPE2D `descriptor` op

- **データ種**: `efdmodel` → `matrix`
- **呼び出し**: `import fourierdesc; fourierdesc.normalize(model, size_invariant=True)` (または `opsshape2d.get("normalize")`)

## 使い方

EFD 係数を「正準ポーズ」の係数へ変換する(第1高調波を基準に整列)。

Kuhl–Giardina の正準化: (1) 第1高調波の位相で **始点** の任意性を除去、(2) 第1
楕円の長軸を基準軸へ回して **向き** を揃え、(3) 第1高調波の長軸長で割って **大きさ**
を揃える。複数形状を重ねる/平均する等の「正準ポーズ再構成」向け。

注意(honest): 第1高調波がほぼ **円形**(長軸≈短軸)の形状では位相 (theta/psi) が
悪条件で不安定になる。**不変マッチングには本関数でなく** :func:`invariants` /
:func:`descriptor_distance`(特異値ベース)を使うこと。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_flow_from_particles](../../../../examples/piv_flow_from_particles.py) — `py -3.11 examples/piv_flow_from_particles.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

—

## 同カテゴリ(`descriptor`)

[elliptic_fourier](elliptic_fourier.md) · [reconstruct](reconstruct.md) · [invariants](invariants.md) · [descriptor_distance](descriptor_distance.md) · [fourier_smooth](fourier_smooth.md) · [from_xld](from_xld.md)

---
*Provenance: fourierdesc.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
