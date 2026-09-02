---
op: evidence_quantile
dim: imgforensics
category: calibration
in: measurement × table
out: table
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# evidence_quantile — IMGFORENSICS `calibration` op

- **データ種**: `measurement × table` → `table`
- **呼び出し**: `import imgforensics; imgforensics.evidence_quantile(measurement, null, higher_is_stronger=True)` (または `opsimgforensics.get("evidence_quantile")`)

## 使い方

証拠量が、清浄な分布の**どのあたりに座るか**を返す。判定は返さない。

``null_distribution`` の出力を消費する側。返すのは「清浄な組の何 % より
外側か」であって、「改竄されている」ではない ―― 外側に座ることは、
その条件で**珍しい**ことしか意味しない(珍しい清浄画像は存在する)。

Parameters
----------
measurement : float
    測った証拠量(``hash_distance`` の返り値など)。
null : dict
    :func:`null_distribution` の返り値。
higher_is_stronger : bool
    PCE や相関のように**大きいほど強い証拠**なら ``True``。
    ハミング距離のように**小さいほど強い証拠**なら ``False``。
    **既定に頼らず必ず考えること** —— ここを間違えると、いちばん証拠の
    強い組が「まったく珍しくない」と出る(例外は出ない)。

Returns
-------
dict
    ``beyond_fraction``(清浄分布のうち、この値より内側にある割合)/
    ``z``(標準偏差の何倍か。ばらつき 0 なら ``None``)/ ``caveats``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`calibration`)

[null_distribution](null_distribution.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
