---
op: angles_to_normals
dim: reprconv
category: direction
in: pairs
out: normals
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# angles_to_normals — REPRCONV `direction` op

- **データ種**: `pairs` → `normals`
- **呼び出し**: `import reprconv; reprconv.angles_to_normals(pairs)` (または `opsreprconv.get("angles_to_normals")`)

## 使い方

方位・仰角の対 ``(N,2)`` **[度]** → 単位法線 ``(N,3)``。``pairs`` の出口。

:func:`normals_to_angles` の厳密な逆(単位長に正規化した意味で)。
仰角は [-90, 90] の外を拒否する —— 100 度の仰角は「反対側の 80 度」に
折り返して**もっともらしく間違う**ので、黙って受けない。

Args:
    pairs: (N, 2) [方位度, 仰角度]、または 2 本の等長 1-D のタプル。
Returns:
    (N, 3) float64、行ごとに単位長。
Raises:
    ValueError: 形状不正 / 非有限 / 仰角が [-90, 90] 外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`normals` を入力に取れる)

[normals_to_angles](normals_to_angles.md) · [normals_to_egi](normals_to_egi.md)

## 同カテゴリ(`direction`)

[normals_to_angles](normals_to_angles.md) · [normals_to_egi](normals_to_egi.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
