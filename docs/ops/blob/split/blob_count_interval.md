---
op: blob_count_interval
dim: blob
category: split
in: mask
out: table
examples: [poc_dense_bubble_count]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# blob_count_interval — BLOB `split` op

- **データ種**: `mask` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.blob_count_interval(region: 'Any', rel_lo: 'float' = 0.05, rel_hi: 'float' = 0.15, min_prominence: 'float' = 1.0, round_tol: 'Optional[float]' = None, connectivity: 'int' = 8) -> 'dict'` (実装を直接呼ぶなら `import blob2d; blob2d.blob_count_interval(region: 'Any', rel_lo: 'float' = 0.05, rel_hi: 'float' = 0.15, min_prominence: 'float' = 1.0, round_tol: 'Optional[float]' = None, connectivity: 'int' = 8) -> 'dict'`、台帳から引くなら `opsblob.get("blob_count_interval")`)

## 使い方

重なった物体を数える。**決まらないときは個数ではなく区間を返す**(fail-closed)。

融合した塊の中の物体は、距離変換の山として現れる。2 つの円が重なると
くびれができ、くびれが浅くなるほど(山の**突出度**が小さいほど)「2 個か
1 個か」が決まらなくなる。``blob_seeds`` + ``blob_split`` は h を 1 つ選んで
**必ず 1 つの個数を返す** —— 重なりが深くて決まらない所でも、もっともらしい
数が出る。この op は山ごとに突出度を測り、閾値の帯に落ちた山を「あいまい」
として個数を ``lo`` 〜 ``hi`` の区間で返す。区間の幅が 0 のときだけ
``count`` を返す。

山の判定(突出度 p、高さ h、相対突出度 p/h。h は内接円の半径にあたる):

* ``p >= min_prominence`` かつ ``p/h >= rel_hi`` → 確かな山(数える)
* ``p >= min_prominence`` かつ ``rel_lo <= p/h < rel_hi`` → あいまい
  (lo には数えず hi には数える)
* それ以外 → 雑音(格子の量子化で出る山。楕円で実測 0.6 px 未満)

**相対突出度を使う理由**: 等しい半径 r の 2 円が重なり率 o(中心間
d = 2r(1 − o))で重なると、くびれの半幅は w = sqrt(r² − (d/2)²) で、
p/h = 1 − sqrt(1 − (1 − o)²) —— **半径によらない**。絶対値の h を選ぶと、
大きい泡と小さい泡が混ざった画像で片方にしか合わない(``poc_cell_counting``
が記録した穴と同じ形)。既定の帯 0.05〜0.15 は重なり率 0.69〜0.47 に当たる。

``round_tol`` を与えると、**山では説明できない面積**も拒否する。
重なり率が 0.7 を超えると、くびれが格子の量子化に埋もれて山が 1 つしか
残らない(2 個が 1 個に見える)。そこで成分の面積を、確かな山とあいまいな山の
内接円の面積の和 Σπh² と比べ、面積 > (1 + round_tol + 1/h_min) · Σπh² なら
上限を開く(``hi = None``)。1/h_min は格子の量子化の分(半径 8 px 以上の円板で
比 1.09 以下、2026-10-18 実測)。``round_tol`` は**許す縦横比 − 1** にあたる
(縦横比 a/b の楕円は面積比 a/b)。泡のように丸い物体なら 0.1、細胞のように
いびつなら 0.3 程度。``None`` は形を仮定しない(深い重なりは見逃す)。

**区間の上限は保証ではない**: ``hi`` は山として見えた物体の数で、山を残さずに
埋もれた物体(大きい泡に食い込んだ小さい泡など)は ``hi`` にも入らない。面積の
検査がそれを拾えたときだけ上限を開く。``determined`` が False のときは「数を
言えない」ことだけが確かで、区間は目安(実際の泡の形の半合成で、決まらないと
答えた塊の真値が ``hi`` を 1 個上回る例が出た。``poc_dense_bubble_count``)。

Parameters
----------
region : array_like
    2-D の前景(``> 0`` が前景)。
rel_lo, rel_hi : float
    相対突出度の帯。``0 < rel_lo <= rel_hi < 1``。
min_prominence : float
    突出度の絶対の床 [px]。``>= 0``。距離変換の量子化の山を落とす。
round_tol : float or None
    面積の検査の許し(上を参照)。``None`` で検査しない。
connectivity : {4, 8}
    成分と水位の連結の取り方。

Returns
-------
dict
    ``count``(区間の幅が 0 なら int、そうでなければ ``None``)、``lo``、
    ``hi``(上限が開いていれば ``None``)、``determined``、``reason``、
    ``labels``(確かな山だけを種にした分割、int32、内接円の冪図)、``labels_hi``
    (あいまいな山も種にした分割)、``components``(成分ごとの ``label`` / ``lo`` /
    ``hi``(開いていれば -1)/ ``status`` / ``area`` / ``area_ratio``)、
    ``peaks``(山ごとの ``component`` / ``row`` / ``col`` / ``height`` /
    ``prominence`` / ``rel_prominence`` / ``status``(0 雑音・1 あいまい・2 確か))、
    ``params``。

Examples
--------
>>> import numpy as np
>>> yy, xx = np.mgrid[0:80, 0:120]
>>> two = ((yy - 40) ** 2 + (xx - 40) ** 2 < 400) | ((yy - 40) ** 2 + (xx - 76) ** 2 < 400)
>>> blob_count_interval(two)["count"]              # 重なり率 0.1: 2 個に決まる
2
>>> deep = ((yy - 40) ** 2 + (xx - 50) ** 2 < 400) | ((yy - 40) ** 2 + (xx - 66) ** 2 < 400)
>>> r = blob_count_interval(deep, round_tol=0.1)   # 重なり率 0.6: 決まらない
>>> r["count"] is None, r["lo"]
(True, 1)

来歴(公開文献のみ): Edelsbrunner, Letscher & Zomorodian, *Discrete Comput.
Geom.* 28 (2002) 511 —— パーシステンス / Vincent & Soille, *IEEE TPAMI* 13
(1991) 583 —— 分水嶺 / Aurenhammer, *SIAM J. Comput.* 16 (1987) 78 —— 冪図(分割)。

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dense_bubble_count](../../../../examples/poc_dense_bubble_count.py) — `py -3.11 examples/poc_dense_bubble_count.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`split`)

[blob_distance](blob_distance.md) · [blob_seeds](blob_seeds.md) · [blob_split](blob_split.md)

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
