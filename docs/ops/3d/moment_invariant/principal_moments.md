---
op: principal_moments
dim: 3d
category: moment_invariant
in: points
out: descriptor
examples: [shape_desc_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# principal_moments — 3D `moment_invariant` op

- **データ種**: `points` → `descriptor`
- **呼び出し**: `import fullseye as fs; fs.ledger.principal_moments(points) -> 'np.ndarray'` (実装を直接呼ぶなら `import moments3d; moments3d.principal_moments(points) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("principal_moments")`)

## 使い方

慣性テンソルの固有値(主慣性モーメント、降順ソート、回転不変)。

慣性テンソルは対称なので固有値は実。点群を回転 R で回すと I → R I Rᵀ と
相似変換され、固有値は不変(厳密)。返り値は降順にそろえるので座標系や
回転に依らず一致する。

Returns
-------
np.ndarray, shape (3,)
    降順の主慣性モーメント λ1 >= λ2 >= λ3 >= 0。

補足:
- ``inertia_tensor`` の固有値で、共分散の固有値 c_i とは ``λ_i = (c_1 + c_2 + c_3) - c_i`` の関係。細長い棒では最小固有値(棒の軸まわり)が 0 に近づき、球では 3 つが等しい。
- 単位は長さ²。並進と回転には不変だが **スケールには不変でない**(s 倍で s² 倍)。スケール不変が要るなら ``moment_invariants``。
- 入力は (N,3)、N >= 1(1 点なら全て 0)。形状不正・非有限は ``ValueError``。
- 主軸ベクトル(固有ベクトル)が要るなら ``moment_axes``。決定論的。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape_desc_pose](../../../../examples_3d/shape_desc_pose.py) — `py -3.11 examples_3d/shape_desc_pose.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`moment_invariant`)

[moment_invariants](moment_invariants.md) · [central_moments](central_moments.md) · [inertia_tensor](inertia_tensor.md)

---
*Provenance: moments3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
