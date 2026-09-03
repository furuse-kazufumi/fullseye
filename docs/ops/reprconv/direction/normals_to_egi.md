---
op: normals_to_egi
dim: reprconv
category: direction
in: normals
out: image2d
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# normals_to_egi — REPRCONV `direction` op

- **データ種**: `normals` → `image2d`
- **呼び出し**: `import reprconv; reprconv.normals_to_egi(normals, n_az=36, n_el=18)` (または `opsreprconv.get("normals_to_egi")`)

## 使い方

法線 ``(N,3)`` → 拡張ガウス像 ``(n_el, n_az)`` の ``image2d``。

方向の 2-D ヒストグラム(Horn, *Extended Gaussian Images*, Proc. IEEE 72(12)
1984)。「どの向きの面がどれだけあるか」の地図で、平面が支配的な物体では
1 つの bin に山が立つ。**不可逆** —— bin 幅ぶんの方向解像度を捨てる。
捨てた量は測れる: 最頻 bin の中心方向と入力の平均方向の角度差が量子化誤差で、
既定 (36, 18) では bin 幅 10 度に対し実測 3.7 度(``selftest`` が出す)。

仰角の bin は ``sin(el)`` で等分する(等立体角)。度で等分すると極が過剰に
細かくなり、「北極に面が集中している」という嘘の山が立つ。

Args:
    normals: (N, 3)。
    n_az: 方位の bin 数(既定 36 = 10 度刻み)。
    n_el: 仰角の bin 数(既定 18)。
Returns:
    (n_el, n_az) float64 の計数マップ(行 = 仰角、列 = 方位)。
Raises:
    ValueError: bin 数が 1 未満 / 上限超 / 入力不正。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[keypoints_from_image2d](../keypoint/keypoints_from_image2d.md)

## 同カテゴリ(`direction`)

[normals_to_angles](normals_to_angles.md) · [angles_to_normals](angles_to_normals.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
