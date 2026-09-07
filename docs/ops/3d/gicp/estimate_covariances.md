---
op: estimate_covariances
dim: 3d
category: gicp
in: points
out: descriptor
examples: [gicp_register]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# estimate_covariances — 3D `gicp` op

- **データ種**: `points` → `descriptor`
- **呼び出し**: `import fullseye as fs; fs.ledger.estimate_covariances(points, k: 'int' = 20, epsilon: 'float' = 0.001) -> 'np.ndarray'` (実装を直接呼ぶなら `import gicp; gicp.estimate_covariances(points, k: 'int' = 20, epsilon: 'float' = 0.001) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("estimate_covariances")`)

## 使い方

各点の局所共分散を固有値 (ε,1,1) に置換した plane-to-plane 共分散 (N,3,3)。

k 近傍(自身を含む)の標本共分散を固有分解し、固有値を **接平面内は 1・
表面法線方向(最小固有値方向)は ε** に置き換えて再構成する。共分散の
大きさは近傍の広がりに依らず一定(ε,1,1)で、スケール不変な「面的な
確からしさ」モデルになる(GICP の中核)。

引数:
    points (N,3): 点群。
    k: 近傍数(自身を含む)。共分散推定は k≥4 程度が安定。
    epsilon: 法線方向に割り当てる小分散(0<ε<1)。小さいほど接平面へ
             強く拘束する。スケール不変(次元なし比)。

返り値:
    (N,3,3) 対称正定値共分散の束。各共分散の固有値は {ε,1,1}、ε に
    対応する固有ベクトルが局所表面法線方向。

例外:
    ValueError: points が (N,3) でない / N<3(法線が定まらず縮退)/
                epsilon が (0,1) 外(fail-closed)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gicp_register](../../../../examples_3d/gicp_register.py) — `py -3.11 examples_3d/gicp_register.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`gicp`)

[gicp](gicp.md)

---
*Provenance: gicp.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
