---
op: hessian_determinant
dim: reprconv
category: derivative
in: hessian
out: voxel
gpu: なし
examples: [hessian_numpy_chain, type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# hessian_determinant — REPRCONV `derivative` op

- **データ種**: `hessian` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.hessian_determinant(hessian)` (実装を直接呼ぶなら `import reprconv; reprconv.hessian_determinant(hessian)`、台帳から引くなら `opsreprconv.get("hessian_determinant")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

3-D Hessian ``hessian`` → 行列式 ``det H`` の体積 ``voxel``(符号つき)。``hessian`` 型の出口。

``det H = λ1 λ2 λ3``(固有値の積)。球状の明るい塊の中心では 3 つとも負なので負、
暗い塊では正、管や板(固有値の 1 つ以上が 0 に近い)では 0 に近い ——
Determinant-of-Hessian の塊検出(Lindeberg 1998)の 3-D 版。単位は ``hessian3d``
と同じ 1/voxel² の 3 乗(正規化しない。**値の比較は同じ尺度の中だけ**で)。

固有値を経由せず成分から直接 ``zz(yy·xx − yx²) − zy(zy·xx − yx·zx) + zx(zy·yx − yy·zx)``
で計算する(固有値分解の丸めを入れないため)。

Args:
    hessian: ``hessian3d`` の 6 成分 (zz, yy, xx, zy, zx, yx)。torch でも numpy でもよい。
Returns:
    (D, H, W) float64。
Raises:
    ValueError: 6 成分でない / 形がそろわない / 非有限 / 空。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [hessian_numpy_chain](../../../../examples/hessian_numpy_chain.py) — `py -3.11 examples/hessian_numpy_chain.py`
- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[correlation_score](../score/correlation_score.md) · [voxel_to_hessian](voxel_to_hessian.md)

## 同カテゴリ(`derivative`)

[gradient_magnitude](gradient_magnitude.md) · [gradient_coherence](gradient_coherence.md) · [voxel_to_hessian](voxel_to_hessian.md) · [hessian_vesselness](hessian_vesselness.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
