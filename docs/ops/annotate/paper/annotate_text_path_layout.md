---
op: annotate_text_path_layout
dim: annotate
category: paper
in: text
out: table
examples: [annotate_paper_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# annotate_text_path_layout — ANNOTATE `paper` op

- **データ種**: `text` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.annotate_text_path_layout(text, path, font_size=13, font_path=None, spacing=1.0, start=0.0, anchor='start', offset=0.0, upright=False, line_spacing=1.15)` (実装を直接呼ぶなら `import annotate; annotate.annotate_text_path_layout(text, path, font_size=13, font_path=None, spacing=1.0, start=0.0, anchor='start', offset=0.0, upright=False, line_spacing=1.15)`、台帳から引くなら `opsannotate.get("annotate_text_path_layout")`)

## 使い方

table(dict)を返す: 折れ線に沿って 1 文字ずつ置く位置と傾き(弧長で決める)。

文字 i の中心は弧長 ``s_i = s0 + Σ_{j<i} a_j*spacing + a_i/2``、傾きは
その位置の線分の接線角(画面座標、度)。経路より長い文字列は ValueError。

**位置の決め方**(2026-09-08 に追加。既定はそれまでの動作と同じ):

* ``anchor`` —— 経路に沿ったそろえ方。``"start"``(既定・従来どおり)/
  ``"center"``(経路の中央にそろえる)/ ``"end"``(終端にそろえる)。
  ``start`` はアンカーで決めた位置から**さらにずらす**量として効く。
* ``offset`` —— 経路に**垂直**なずらし [px]。正が**進行方向の右**
  (画面座標。y が下向きなので、左→右に進む文字なら「下」)。
  線に触れさせずに脇へ置く用途。
* ``\n`` で**改行**。2 行目以降は ``line_spacing`` を掛けた行高だけ
  ``offset`` と同じ向き(進行方向の右)へずれる。★この 1 つの規則で、
  横書きは「下へ」、縦書きは「左へ」と**どちらも組版どおり**になる
  (縦書きは進行方向が下なので、その右は画面の左)。
* ``upright`` —— 字を接線角に回さず**正立**させる。経路が主に縦向き
  (始点→終点の |dy| > |dx|)なら送りを字幅でなく**字高**にするので、
  これが**縦書き**になる。``VERTICAL_ROTATED_CHARS`` の字だけは 90 度回す。

★**縦書きで実装していないこと**(黙って近似しない): 句読点の右上寄せ、
小書き仮名の位置補正、縦中横。短い注記のための機能で、本文組版ではない。

Returns
-------
dict
    ``{"chars": [{"char","s","xy","angle_deg","width","advance","line"}],
    "length": 経路長, "used": 最も長い行の**送りの合計**(従来どおり
    ``Σ advance*spacing``), "span": 最も長い行が**実際に占める**弧長
    (最後の字の後ろの送りを含まない —— アンカーはこちらで揃える),
    "lines": 行数, "line_height": 行送り [px], "vertical": 縦書きか}``。

Raises
------
ValueError
    文字が空、経路が 2 点未満か長さゼロ、非有限、行が経路より長い、
    アンカーと ``start`` の組み合わせで行が経路から外れる場合。

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [dataset_conventions](../guides/dataset_conventions.md) — 学習データセット規約の知識 — COCO / YOLO / VOC と外観検査での落とし穴

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate_paper_tour](../../../../examples/annotate_paper_tour.py) — `py -3.11 examples/annotate_paper_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`paper`)

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
