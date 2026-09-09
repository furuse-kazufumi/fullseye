---
op: region_growing
dim: 3d
category: segment
in: points
out: labels
examples: [sensor_seg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# region_growing — 3D `segment` op

- **データ種**: `points` → `labels`
- **呼び出し**: `import fullseye as fs; fs.ledger.region_growing(points, normals=None, angle_thresh_deg: 'float' = 15.0, k: 'int' = 20, min_region_size: 'int' = 3) -> 'np.ndarray'` (実装を直接呼ぶなら `import segment3d; segment3d.region_growing(points, normals=None, angle_thresh_deg: 'float' = 15.0, k: 'int' = 20, min_region_size: 'int' = 3) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("region_growing")`)

## 使い方

法線類似で領域成長し連結した平滑領域へ同ラベルを付す(曲率ゲート無し変種)。

各点を k 近傍グラフ上で BFS 成長させ、隣接点 q を「法線 n_p と n_q の成す角が
``angle_thresh_deg`` 未満」のときだけ同領域に加える。平面内の法線はほぼ平行なので
同一領域に連結し、向きの違う面の境界では角度が開いて連結が切れる → 面ごとに別領域。
法線は符号不定(PCA 由来)なので ``|n_p·n_q|`` で判定(表裏を同一視)。

Args:
    points: (N,3) 点群。
    normals: (N,3) 単位法線。None なら :func:`pointcloud.estimate_normals` で PCA 推定。
    angle_thresh_deg: 隣接法線角度の許容上限[度]。(0,180) の範囲。
    k: 近傍数(kNN グラフの次数)。

Returns:
    labels: (N,) int。連結平滑領域ごとに 0,1,2,... を付与。**min_region_size 未満の
    小領域(孤立点・向き不一致のゴミ)は -1(ノイズ/未割当)** = 統一契約(-1=ノイズ)に従う。
    空入力は shape (0,) を返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sensor_seg](../../../../examples_3d/sensor_seg.py) — `py -3.11 examples_3d/sensor_seg.py`

## 型が繋がる次の op(`labels` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [vol_region_props](../regionprops/vol_region_props.md)

## 同カテゴリ(`segment`)

[euclidean_cluster](euclidean_cluster.md) · [plane_segmentation](plane_segmentation.md) · [vol_watershed](vol_watershed.md)

---
*Provenance: segment3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
