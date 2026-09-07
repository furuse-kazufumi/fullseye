---
op: blob_select
dim: blob
category: select
in: labels2d
out: labels2d
examples: [poc_particle_sizing, poc_weld_radiograph_porosity]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# blob_select — BLOB `select` op

- **データ種**: `labels2d` → `labels2d`
- **呼び出し**: `import blob2d; blob2d.blob_select(labels: 'Any', feature: 'str', vmin: 'Optional[float]' = None, vmax: 'Optional[float]' = None, spacing: 'float' = 1.0) -> 'np.ndarray'` (または `opsblob.get("blob_select")`)

## 使い方

特徴量が ``[vmin, vmax]`` に入る物体だけ残す(**番号は 1 から振り直す**)。

Parameters
----------
labels : array_like
    :func:`blob_label` の出力。
feature : str
    :data:`FEATURE_KEYS` のどれか。知らない鍵は**候補を並べて拒否する**。
vmin, vmax : float or None
    両端(含む)。``None`` は片側を開ける。両方 ``None`` は
    「何も選んでいない」ので拒否する —— 全部通す意図なら呼ばなければよい。
spacing : float
    :func:`blob_features` と同じ意味。``area`` や ``perimeter`` を
    物理単位で切るときに要る。

Returns
-------
numpy.ndarray
    ``int32`` のラベル画像。**残った物体は 1..k の連番**になる
    (元の番号は残さない)。元の番号が要るなら
    ``blob_features(labels)["label"]`` を先に取っておくこと。

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_particle_sizing](../../../../examples/poc_particle_sizing.py) — `py -3.11 examples/poc_particle_sizing.py`
- [poc_weld_radiograph_porosity](../../../../examples/poc_weld_radiograph_porosity.py) — `py -3.11 examples/poc_weld_radiograph_porosity.py`

## 型が繋がる次の op(`labels2d` を入力に取れる)

[blob_features](../measure/blob_features.md) · [blob_select_largest](blob_select_largest.md) · [blob_split](../split/blob_split.md) · [blob_region](../extract/blob_region.md) · [blob_boundaries](../extract/blob_boundaries.md) · [blob_overlay](../extract/blob_overlay.md)

## 同カテゴリ(`select`)

[blob_select_largest](blob_select_largest.md)

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
