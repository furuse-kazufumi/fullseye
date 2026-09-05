---
op: angle_to_matrix
dim: reprconv
category: algebra
in: angle
out: matrix
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# angle_to_matrix — REPRCONV `algebra` op

- **データ種**: `angle` → `matrix`
- **呼び出し**: `import reprconv; reprconv.angle_to_matrix(angle)` (または `opsreprconv.get("angle_to_matrix")`)

## 使い方

角度 **[度]** → z 軸まわりの回転行列 ``matrix (3,3)``。``angle`` の出口。

``angle_to_matrix(90)`` は軸1(y)を軸2(x)へ送り、軸2(x)を **−軸1**(−y)へ
送る(``R @ [0,1,0] = [0,0,1]``、``R @ [0,0,1] = [0,-1,0]``、実測)。
2-D の :func:`rot_scale_to_matrix` と同じ ``[[c,-s],[s,c]]`` の向き
(軸 0 → 軸 1)を軸 (1, 2) に置いたもので、:func:`matrix_to_angle` の
``atan2(R[2,1], R[1,1])`` もこの向きで往復する。**度**であることと
**どちらの軸へ回るか**が、この段落の全内容である。ラジアンを渡すと
例外は出ず、ただ 57.3 分の 1 だけ回った行列が返る。

Args:
    angle: 度。
Returns:
    (3, 3) float64、行列式 1 の直交行列。
Raises:
    ValueError: スカラでない / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[matrix_to_descriptor](../descriptor/matrix_to_descriptor.md) · [matrix_to_angle](matrix_to_angle.md) · [matrix_to_rot_scale](matrix_to_rot_scale.md)

## 同カテゴリ(`algebra`)

[matrix_to_angle](matrix_to_angle.md) · [rot_scale_to_matrix](rot_scale_to_matrix.md) · [matrix_to_rot_scale](matrix_to_rot_scale.md) · [shift_to_vector](shift_to_vector.md) · [vector_to_shift](vector_to_shift.md) · [cscalar_to_polar](cscalar_to_polar.md) · [polar_to_cscalar](polar_to_cscalar.md) · [countrate_to_counts](countrate_to_counts.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
