---
op: separate_touching
dim: segmentation
category: watershed3d
in: voxel
out: labels
examples: [watershed3d_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# separate_touching — SEGMENTATION `watershed3d` op

- **データ種**: `voxel` → `labels`
- **呼び出し**: `import fullseye as fs; fs.ledger.separate_touching(binary, min_distance: 'float' = 5.0, method: 'str' = 'auto') -> 'np.ndarray'` (実装を直接呼ぶなら `import watershed3d; watershed3d.separate_touching(binary, min_distance: 'float' = 5.0, method: 'str' = 'auto') -> 'np.ndarray'`、台帳から引くなら `opssegmentation.get("separate_touching")`)

## 使い方

genuinely-new (B): 接触物体を 1 呼び出しで自動分離する常用ラッパ。

「複数物体が接触して 1 連結成分に融合している」典型ケースを、距離変換→極大 NMS シード化→
分水嶺という定型パイプラインを畳んで 1 コールで割る(公開 API では 3 op を手で繋ぐ必要が
あるところを常用ケース向けに 1 関数化)。中身は ``watershed_vol(..., markers=None)``。

Parameters
----------
binary : array_like
    bool または 0/1 の 3D 前景ボリューム。
min_distance : float
    分離シードの最小間隔(voxel)。想定物体半径程度が目安。
method : {"auto", "skimage", "scipy"}
    バックエンド選択。

Returns
-------
labels : ndarray(int32)
    binary と同形状。背景 0、分離された各物体に 1..k のラベル。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [watershed3d_tour](../../../../examples/watershed3d_tour.py) — `py -3.11 examples/watershed3d_tour.py`

## 型が繋がる次の op(`labels` を入力に取れる)

—

## 同カテゴリ(`watershed3d`)

[distance_peaks](distance_peaks.md) · [watershed_vol](watershed_vol.md)

---
*Provenance: watershed3d.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
