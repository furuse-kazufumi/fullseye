---
op: watershed_vol
dim: segmentation
category: watershed3d
in: voxel
out: labels
examples: [watershed3d_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# watershed_vol — SEGMENTATION `watershed3d` op

- **データ種**: `voxel` → `labels`
- **呼び出し**: `import fullseye as fs; fs.ledger.watershed_vol(binary, markers: 'Optional[np.ndarray]' = None, min_distance: 'float' = 1.0, method: 'str' = 'auto') -> 'np.ndarray'` (実装を直接呼ぶなら `import watershed3d; watershed3d.watershed_vol(binary, markers: 'Optional[np.ndarray]' = None, min_distance: 'float' = 1.0, method: 'str' = 'auto') -> 'np.ndarray'`、台帳から引くなら `opssegmentation.get("watershed_vol")`)

## 使い方

距離変換シードの分水嶺で 3D 前景を物体ごとのラベルに分割する(公開 op の薄い合成)。

連結成分では 1 個に融合する**接触/僅かな重なり**を割るのが目的。EDT は
:func:`volops.vol_distance_transform`、skimage 分水嶺は :func:`volops.vol_watershed` に
委譲し、本モジュールは (A) skimage 不在時の純 scipy フォールバックと、シード自動生成の
グルーだけを足す。``markers`` を省略すると距離変換の局所極大(``min_distance`` NMS)を
自動シードにする。

Parameters
----------
binary : array_like
    bool または 0/1 の 3D 前景ボリューム。
markers : ndarray or None
    シードを外部指定する場合の int ラベル配列(binary と同形状、0=無し, 1..n=シード)。
    None なら距離変換の極大から自動生成する。
min_distance : float
    ``markers=None`` のときのシード最小間隔(voxel)。
method : {"auto", "skimage", "scipy"}
    バックエンド選択。"skimage" 指定で不在なら fail-closed(ImportError)。

Returns
-------
labels : ndarray(int32)
    binary と同形状。背景 0、各物体に 1..k のラベル(前景を過不足なく被覆)。

Raises
------
ValueError
    形状不正・退化入力・不正 method のとき(fail-closed)。

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

[distance_peaks](distance_peaks.md) · [separate_touching](separate_touching.md)

---
*Provenance: watershed3d.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
