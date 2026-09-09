---
op: apply_metrology_model
dim: measure1d
category: apply
in: metrologymodel × image2d
out: table
examples: [poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# apply_metrology_model — MEASURE1D `apply` op

- **データ種**: `metrologymodel × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.apply_metrology_model(model, image, measure_length=6.0, sigma=1.0, threshold=0.05) -> 'list'` (実装を直接呼ぶなら `import metrology; metrology.apply_metrology_model(model, image, measure_length=6.0, sigma=1.0, threshold=0.05) -> 'list'`、台帳から引くなら `opsmeasure1d.get("apply_metrology_model")`)

## 使い方

各計測オブジェクトの参照形状の法線に沿ってサブピクセルエッジを測り、形状を
再フィットして結果を返す(apply_metrology_model)。

``measure_length`` = 法線方向の探索半幅 [px]、``sigma`` = プロファイル平滑化、
``threshold`` = 採用するエッジの最小グレー差(画像のグレー単位)。
各結果 dict: ``type`` / ``edge_points`` (M,2) / ``amplitudes`` (M,) 符号つきグレー差 /
``score`` = 平均 |振幅| / ``centroid`` / ``params``(再フィット形状; 直線は
row1,col1,row2,col2,angle_deg / 円は row,col,radius / 楕円は row,col,phi,ra>=rb /
矩形は row,col,phi,l1>=l2)/ ``rms`` = フィット残差 [px]。エッジ点が足りず
フィットできない場合は ``params=None``, ``rms=inf``, ``error`` に理由を入れる
(他オブジェクトの計測は続行)。楕円・矩形の ``phi`` は長軸(ra / l1)の向き。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`apply`)

[align_metrology_model](align_metrology_model.md)

---
*Provenance: metrology.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
