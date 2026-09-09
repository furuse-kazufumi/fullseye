---
op: orient_normals
dim: 3d
category: normals_orient
in: points × normals
out: normals
examples: [oriented_normals]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# orient_normals — 3D `normals_orient` op

- **データ種**: `points × normals` → `normals`
- **呼び出し**: `import fullseye as fs; fs.ledger.orient_normals(points, normals, k: 'int' = 20, seed_dir=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import normals_orient; normals_orient.orient_normals(points, normals, k: 'int' = 20, seed_dir=None) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("orient_normals")`)

## 使い方

Hoppe 法で法線を**大域一貫**に向き付け(MST 伝播)。→ (N,3)。

kNN グラフ上に重み ``1 - |n_i·n_j|``(接平面が揃うほど安い)の最小全域木を張り、
種から木を BFS しながら親と符号が逆の子を反転させて成分を内部一貫にする。種は
``seed_dir`` 指定時はその向きに最も突き出た点、未指定時は**最外点**(重心から最遠)。
グラフが分断されていれば連結成分ごとに独立に種を取り伝播する(成分間の相対向きは未保証)。

``seed_dir`` を渡した場合、伝播で内部一貫化した後に**成分全点の射影を集約**して大域符号を
``seed_dir`` に整合する(単一 seed の ``|cos|`` に依存しないので、seed 点の法線が
``seed_dir`` と近直交でも符号は確実に決まる — finding [5])。``seed_dir`` が成分の
全法線と(ほぼ)直交して符号を決められない真の退化は fail-closed(``ValueError``)。
閉曲面(球など)で ``seed_dir`` が平均的に法線と直交する場合は大域符号が一意でないため、
最突出点(=外向き)基準の向き付けを保持する。``seed_dir`` 未指定時は重心から外向き。

Args:
    points: (N,3) の点群。
    normals: (N,3) の向き未定法線(内部で単位化)。
    k: kNN グラフの近傍数。
    seed_dir: 大域基準向き (3,)。None なら重心から外向きを基準にする。
Returns:
    符号を大域一貫にそろえた (N,3) 単位法線。
Raises:
    ValueError: ``seed_dir`` がゼロ、または(ある連結成分で)全法線と直交して
        大域符号を制御できないとき(fail-closed)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [oriented_normals](../../../../examples_3d/oriented_normals.py) — `py -3.11 examples_3d/oriented_normals.py`

## 型が繋がる次の op(`normals` を入力に取れる)

[icp_point2plane](../refine/icp_point2plane.md) · [compute_fpfh](../feature_register/compute_fpfh.md) · [shot_descriptor](../feature_register/shot_descriptor.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [reflect](../optics/reflect.md) · [refract](../optics/refract.md) · [normal_consistency](../metrics/normal_consistency.md) · [ransac_cylinder](../robust_fit/ransac_cylinder.md)

## 同カテゴリ(`normals_orient`)

[estimate_oriented_normals](estimate_oriented_normals.md)

---
*Provenance: normals_orient.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
