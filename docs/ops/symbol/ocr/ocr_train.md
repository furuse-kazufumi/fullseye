---
op: ocr_train
dim: symbol
category: ocr
in: 
out: table
gpu: なし
examples: [poc_symbol_lot_ocr]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# ocr_train — SYMBOL `ocr` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ocr_train(font='dot5x7', char_height_px=(16, 20, 26, 34), variants=None, seed=0, neighbour='random') -> 'dict'` (実装を直接呼ぶなら `import ocrclassic; ocrclassic.ocr_train(font='dot5x7', char_height_px=(16, 20, 26, 34), variants=None, seed=0, neighbour='random') -> 'dict'`、台帳から引くなら `opssymbol.get("ocr_train")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

書体を撹乱つきで描いてテンプレート(特徴量 + ラベル)と棄却の閾値を集める(``table``)。

Render every character under a small deterministic set of nuisance variations and collect
feature templates for k-NN.

各試料は「乱数(seed 固定)で選んだ隣字 + 字 + 隣字」の 3 字行として描き、撹乱(字高・にじみ・
ぼけ・小数ずれ)をかけてから、**読み取りと同じ規則**で中央の字を切る: 字間の中点(真値)に最も
近い列射影の極小を切れ目とし(読みの切れ目候補と同じ規則)、その間の字の画素(ink >= 0.5)の
外接箱から、重心中心・送り幅の窓で特徴量を取る。隣字を固定(例 ``"H"``)にすると、読みの場で
隣に来る字のにじみが学習に無く、ぼけ 0.1h で正解率が 2 割落ちた(実測)ので乱数にしている。
切れなかった試料(字の画素が無い)は真値の箱で代替し、件数を ``n_fallback`` に残す。

Each sample is a 3-glyph line (seeded random neighbours + glyph + neighbour); the middle glyph
is cut with the same rule as reading (profile minima nearest to the true gap midpoints) and
featurised with the centroid-centred pitch-wide window. A fixed neighbour lost ~20 % accuracy
at blur 0.1 h (measured), hence random neighbours.

Parameters
----------
font : 書体名か書体辞書。
char_height_px : 字高の組(各 8..256)。既定 (16, 20, 26, 34)。
variants : ``{"ink_gain": tuple, "blur": tuple (σ / 字高), "subpixel": bool, "noise": float}``。
    None で既定(にじみ 3 x ぼけ 8 [0..0.14h, 0.02h 刻み] x 字高 4 = 1 字 96 試料、
    40 字で 3840 試料)。
seed : 小数ずらし・隣字・雑音の乱数種(決定的)。
neighbour : ``"random"``(既定)か字種内の 1 字。

Returns
-------
dict
    ``features`` (n, 88), ``labels`` (n,) str, ``weights`` (88,) 対角マハラノビスの重み,
    ``blur`` (n,) 各試料のぼけ, ``blur_levels``, ``blur_step``, ``charset``, ``font``,
    ``font_kind``, ``k`` (=1), ``reject_distance``(全体の値、帯を指定しない照合用),
    ``reject_distance_by_class``(字ごと), ``min_margin_ratio``, ``reject_stats``
    (``within_nn_p99``, ``factor``, ``between_nn_min``, ``between_nn_p01``), ``n_fallback``,
    ``heights``。

棄却距離の導き方 / reject_distance derivation
    各試料について「同クラス・ぼけ帯内(±1 格子点)の最近傍の**他の**試料までの重みつき距離」を
    求め、**字ごとに**その 99 パーセンタイル x ``REJECT_FACTOR`` を棄却距離とする。
    学習分布だけで決まる(係数の選び方は ``REJECT_FACTOR`` の注記を参照)。
    Per class: REJECT_FACTOR x P99 of the within-class, within-band nearest-other-sample
    weighted distance. Derived from the training distribution only.

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_lot_ocr](../../../../examples/poc_symbol_lot_ocr.py) — `py -3.11 examples/poc_symbol_lot_ocr.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_symbol](../symbol_capture/render_symbol.md) · [symbol_read_trials](../read_pod/symbol_read_trials.md) · [symbol_read_pod](../read_pod/symbol_read_pod.md) · [ocr_classify](ocr_classify.md) · [ocr_read_line](ocr_read_line.md) · [ocr_read_trials](ocr_read_trials.md)

## 同カテゴリ(`ocr`)

[ocr_font](ocr_font.md) · [ocr_render_text](ocr_render_text.md) · [ocr_segment_line](ocr_segment_line.md) · [ocr_features](ocr_features.md) · [ocr_classify](ocr_classify.md) · [ocr_read_line](ocr_read_line.md) · [ocr_score](ocr_score.md) · [ocr_read_trials](ocr_read_trials.md)

---
*Provenance: ocrclassic.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
