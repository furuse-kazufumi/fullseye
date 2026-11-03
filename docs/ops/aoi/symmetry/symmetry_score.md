---
op: symmetry_score
dim: aoi
category: symmetry
in: image2d × table
out: measurement
examples: [poc_symmetry_self_reference_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# symmetry_score — AOI `symmetry` op

- **データ種**: `image2d × table` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.symmetry_score(image, symmetry, exclusion_mask=None, detrend=True)` (実装を直接呼ぶなら `import symmetry2d; symmetry2d.symmetry_score(image, symmetry, exclusion_mask=None, detrend=True)`、台帳から引くなら `opsaoi.get("symmetry_score")`)

## 使い方

自己参照差分をダイナミックレンジで正規化した対称からの距離を返す。

Parameters
----------
image : array-like, shape (H, W)
    検査するグレー画像。
symmetry : dict
    反射軸または回転中心の table。
exclusion_mask : array-like or None, default None
    設計上の非対称を除外する mask。形は image と同じ。
detrend : bool, default True
    線形照明差を除くなら True。

Returns
-------
float
    有効画素の平均絶対差 / 画像ダイナミックレンジ。0 が完全対称で、大きいほど
    対称から遠い連続値。

Notes
-----
定数・一様入力は相対床で ``ValueError``。この値は同じ画像、同じモデル、同じ mask
の乱れを比較する量で、異なる補間床や画角の画像を一律の合否しきい値で比べない。
軸・中心を乱れた画像自身から毎回再推定すると、推定器が欠陥へ寄って単調性を弱める。

## 詳しい使い方ガイド

- [aoi_frontend ファミリ ガイド](../guides/aoi_frontend.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symmetry_self_reference_inspection](../../../../examples/poc_symmetry_self_reference_inspection.py) — `py -3.11 examples/poc_symmetry_self_reference_inspection.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`symmetry`)

[center_from_symmetric_edges](center_from_symmetric_edges.md) · [reflection_axis](reflection_axis.md) · [rotational_symmetry](rotational_symmetry.md) · [symmetry_difference_map](symmetry_difference_map.md)

---
*Provenance: symmetry2d.py — AOI operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
