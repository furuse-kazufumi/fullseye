---
op: distance_peaks
dim: segmentation
category: watershed3d
in: voxel
out: labels
examples: [watershed3d_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# distance_peaks — SEGMENTATION `watershed3d` op

- **データ種**: `voxel` → `labels`
- **呼び出し**: `import fullseye as fs; fs.ledger.distance_peaks(binary, min_distance: 'float' = 1.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import watershed3d; watershed3d.distance_peaks(binary, min_distance: 'float' = 1.0) -> 'np.ndarray'`、台帳から引くなら `opssegmentation.get("distance_peaks")`)

## 使い方

前景距離変換の局所極大を ``min_distance`` NMS で間引いた int マーカ配列を返す。

:func:`volops.vol_distance_transform` + :func:`volops.vol_local_maxima` の薄い合成に、
「極大座標→ラベル配列(1 物体 1 シード)」の後処理を足したもの(``watershed_vol`` が
内部で使うシード生成を単体で公開=可視化・検証用)。

Parameters
----------
binary : array_like
    bool または 0/1 の 3D 前景ボリューム。
min_distance : float
    採用シード間の最小ユークリッド距離(voxel)。物体間隔より小さく、物体内ノイズ極大の
    間隔より大きく取る。

Returns
-------
markers : ndarray(int32)
    binary と同形状。0=シード無し、1..k=各シードラベル。

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

[watershed_vol](watershed_vol.md) · [separate_touching](separate_touching.md)

---
*Provenance: watershed3d.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
