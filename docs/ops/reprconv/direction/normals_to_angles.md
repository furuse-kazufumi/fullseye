---
op: normals_to_angles
dim: reprconv
category: direction
in: normals
out: pairs
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# normals_to_angles — REPRCONV `direction` op

- **データ種**: `normals` → `pairs`
- **呼び出し**: `import reprconv; reprconv.normals_to_angles(normals)` (または `opsreprconv.get("normals_to_angles")`)

## 使い方

法線 ``(N,3)`` → 方位・仰角の対 ``(N,2)`` **[度]**。``normals`` の出口。

``az = atan2(c1, c0)`` を軸0-軸1 平面内の方位、``el = asin(c2/|v|)`` を
軸2 からの仰角とする。**x/y/z でなく「軸0/1/2」で定義する**のは、この repo に
(z,y,x) 順の点群と (x,y,z) 順の点群が両方いるため —— 名前で書くと、渡された
配列がどちらの流儀かに依存して意味が変わってしまう。

可逆: :func:`angles_to_normals` と往復して **方向は厳密に戻る**(実測
max|Δ| = 6.1e-16、``selftest`` が毎回測る)。**戻らないのは長さだけ** ——
法線は向きなので、非単位ベクトルを渡すと往復で単位ベクトルになる。

Args:
    normals: (N, 3) 実配列。零ベクトルは拒否(方位が定義できない)。
Returns:
    (N, 2) float64。列 0 = 方位 (-180, 180]、列 1 = 仰角 [-90, 90]。
Raises:
    ValueError: 形状が (N,3) でない / 非有限 / 長さ 0 のベクトルを含む。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[angles_to_normals](angles_to_normals.md) · [shape_index_to_curvature](../curvature/shape_index_to_curvature.md) · [pairs_to_signal](../pairs/pairs_to_signal.md) · [pairs_to_image2d](../pairs/pairs_to_image2d.md) · [pairs_to_table](../pairs/pairs_to_table.md) · [polar_to_cscalar](../algebra/polar_to_cscalar.md)

## 同カテゴリ(`direction`)

[angles_to_normals](angles_to_normals.md) · [normals_to_egi](normals_to_egi.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
