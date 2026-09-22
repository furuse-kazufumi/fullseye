---
op: seg_membrane_chord_score
dim: emproof
category: suspect
in: labels2d × image2d
out: table
examples: [poc_em_second_opinion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# seg_membrane_chord_score — EMPROOF `suspect` op

- **データ種**: `labels2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_membrane_chord_score(labels, membrane, tau: 'float' = 0.2, band: 'int' = 4, min_area: 'int' = 1500, min_segment: 'int' = 20, normalize: 'bool' = True, ignore_zero: 'bool' = True, max_points: 'int' = 400, min_hole: 'int' = 4) -> 'dict'` (実装を直接呼ぶなら `import emproof; emproof.seg_membrane_chord_score(labels, membrane, tau: 'float' = 0.2, band: 'int' = 4, min_area: 'int' = 1500, min_segment: 'int' = 20, normalize: 'bool' = True, ignore_zero: 'bool' = True, max_points: 'int' = 400, min_hole: 'int' = 4) -> 'dict'`、台帳から引くなら `opsemproof.get("seg_membrane_chord_score")`)

## 使い方

**融合の疑い**: ラベルの内部を横切る膜の「弦」の長さ / ラベルの径。ラベル(連結成分)ごとに 1 行。

手順: 成分の内側(境界から ``band`` px より内)で膜応答 > ``tau`` の画素を 8 連結の成分にし、
``min_segment`` px 以上の膜成分ごとに、3 px 太らせて境界帯(``band`` < 距離 ≤ ``band`` + 3)に
触れる画素の**最遠 2 点間距離**を弦長とする。score = max 弦長 / sqrt(面積)。境界の 2 か所を結ぶ膜
(= 貼り付いた 2 細胞の境目)は score ≈ 1、境界に触れない断片は 0 か小さい。**穴を持つ膜成分**
(``min_hole`` px 以上の穴 = 閉じた輪 = ミトコンドリア・小胞)は弦の候補から外す ―― 境界の 2 点に
接する輪は弦と同じ「遠い 2 点」を持つので、穴の有無で先に分ける。輪が切れて弧になった膜は
外せない(実データで AUC が 1 にならない主因)。

CREMI sample A(512² 断面 12 枚、試作)で人工融合の成分 vs 他: AUC 0.83(tau 0.2)。
列: ``label`` / ``component`` / ``area`` / ``score`` / ``chord_px`` / ``n_segments`` / ``cy`` / ``cx``
(score 降順)。``min_area`` 未満の成分は数えない(小さな断片の弦は径と同程度で常に高く出る)。

>>> table = seg_membrane_chord_score(labels, seg_membrane_response(raw))
>>> table["label"][:5], table["score"][:5]          # 疑いの強い順

## 詳しい使い方ガイド

- [emproof ファミリ ガイド](../guides/emproof.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_em_second_opinion](../../../../examples/poc_em_second_opinion.py) — `py -3.11 examples/poc_em_second_opinion.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`suspect`)

[seg_boundary_membrane_gap](seg_boundary_membrane_gap.md)

---
*Provenance: emproof.py — EMPROOF operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
