---
op: strain_from_displacement
dim: piv
category: solid
in: image2d × image2d
out: image2d
examples: [poc_dic_strain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# strain_from_displacement — PIV `solid` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.strain_from_displacement(u: 'Any', v: 'Any', window: 'int', method: 'str', spacing: 'float' = 1.0) -> 'tuple[np.ndarray, np.ndarray, np.ndarray]'` (実装を直接呼ぶなら `import dic; dic.strain_from_displacement(u: 'Any', v: 'Any', window: 'int', method: 'str', spacing: 'float' = 1.0) -> 'tuple[np.ndarray, np.ndarray, np.ndarray]'`、台帳から引くなら `opspiv.get("strain_from_displacement")`)
- **台帳経由の戻り値**: `fullseye.ledger.strain_from_displacement(...)` は**宣言 out 型 `image2d` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.strain_from_displacement.raw(...)`、または `dic.strain_from_displacement` を直接呼ぶ。

## 使い方

変位場からひずみ場を出す。``(exx, eyy, exy)`` を返す。

引数(``window`` と ``method`` に**既定値は無い**。理由は下記)
  u        x 方向(列)の変位場 [px]。2 次元。
  v        y 方向(行)の変位場 [px]。``u`` と同じ形。
  window   局所最小二乗の窓の一辺。**単位は格子の節点数**(画素ではない)。
           **奇数**。
  method   ``"infinitesimal"`` または ``"green"``。他は例外。
  spacing  節点の間隔 [px]。全画素の密な場なら 1.0(既定)。
           `piv_cross_correlate` の格子なら ``info["step"]``。

★ `pivops` から渡すとき —— **成分の順を間違えると静かに壊れる**
  ``flow2d`` は ``(dy, dx)`` の順。正しくは::

      flow, info = piv_cross_correlate(a, b, window=32, overlap=0.75)
      exx, eyy, exy = strain_from_displacement(
          flow[1], flow[0], 9, "green", spacing=info["step"])

  ``flow[0]`` を ``u`` に渡すと x と y が入れ替わり、例外にならずに
  もっともらしい別の答えが返る。3 次元配列をそのまま渡した場合だけは
  直し方つきで拒否できるので、そこは検査してある。

定義
  ``ux = ∂u/∂x`` などを ``window x window`` の平面当てはめで出し、

  * ``"infinitesimal"``(微小ひずみ、工学ひずみ)
    ``exx = ux``, ``eyy = vy``, ``exy = ½(uy + vx)``
  * ``"green"``(Green-Lagrange)
    ``exx = ux + ½(ux² + vx²)``, ``eyy = vy + ½(uy² + vy²)``,
    ``exy = ½(uy + vx + ux·uy + vx·vy)``

★★ なぜ ``method`` に既定値を置かないのか —— 剛体回転が作る嘘
  試験片が θ だけ回っただけで、**材料は 1 ミクロンも伸びていない**とする。
  真のひずみは 0。厳密な剛体回転の変位場
  ``u = (cosθ-1)x - sinθ·y``, ``v = sinθ·x + (cosθ-1)y`` を**画像を通さず
  直接**入れた実測(単位 µε = 1e-6):

      θ [度]   cosθ-1     infinitesimal   piv_velocity_gradient   green
        0.5     -38.1        -38.1              -38.1           5.3e-14
        1.0    -152.3       -152.3             -152.3           9.3e-14
        2.0    -609.2       -609.2             -609.2           2.0e-13
        5.0   -3805.3      -3805.3            -3805.3           6.5e-13

  **2 度で -609 µε。鋼の降伏ひずみ(約 2000 µε)の 3 割。** Green-Lagrange
  は ``exx = (cosθ-1) + ½((cosθ-1)² + sin²θ) = 0`` が**代数的に厳密**なので
  1e-13 に落ちる。既存の `piv_velocity_gradient` は微小ひずみと同じ値を
  返す(= 同じ嘘を持つ)し、`piv_strain_rate` は 2 度で **+1218 µε**
  (``2|cosθ-1|``)を返す —— 流体の線形化した回転 ``u=-ωy, v=ωx`` なら 0 に
  なる量だが、**有限回転では 0 にならない**。

  逆に、材料試験の報告書・規格・ひずみゲージとの突き合わせでは
  微小ひずみが標準で、Green-Lagrange を黙って返すと数字が合わない。
  **どちらが正しいかは場面で反転する。だから選ばせる。**

★ ただし「green にすれば安全」ではない —— 推定の誤差はそのまま通る
  Green の補正項 ``½(ux²+vx²)`` は**推定した勾配**から作るので、勾配の
  推定が悪ければ補正も悪い。実測(解析スペックル 256²、剛体回転、
  MARGIN 40 の内側の平均 ± 散らばり、単位 µε):

      θ [度]  cosθ-1  |  piv+LS w=9 微小     green     | lk+LS w=31 微小     green
        2.0   -609.2  |   -42.9 ±  428    564.7 ±  429 |  -698.8 ± 2122   -84.4 ± 2132
        5.0  -3805.3  |   364.9 ± 9532   3843.4 ± 9638 | -1372.9 ±22909  2759.6 ±25685

  ``lk`` の 2 度は教科書どおり(-699 ≒ -609 の嘘 → green で -84 に減る)。
  だが ``piv`` の 2 度は微小ひずみですら -42.9 しか返さない —— 回転する
  サブセットが相関を鈍らせて**勾配の推定自体が ±500 µε 揺れている**ため
  で、そこへ +609 µε の Green 補正を足すと逆に +565 µε になる。
  **5 度以上ではどちらの推定器も散らばりが 1e4 µε を超え、平均に意味が無い。**
  定義の議論が効くのは、まず勾配がその精度で測れているときだけ。

★ ``window`` は空間分解能そのもの
  同じ piv 変位場から一様ひずみを読み戻した実測(µε):

      真値      piv_velocity_gradient        w=3            w=5            w=9
       100       100.4 ±   21.8      100.4 ±   16.0  100.3 ±   6.4  100.3 ±   1.7
       500       501.8 ±  107.2      502.0 ±   78.9  501.4 ±  31.3  501.2 ±   8.6
      2000      1996.3 ±  342.0     1996.6 ±  259.5 1994.8 ±  99.3 1995.6 ±  25.9
     20000     19768.8 ± 2909.9    19768.9 ± 2210.5 19742.7 ± 790.9 19754.1 ± 209.6

  平均は全部同じ。**散らばりだけが w とともに 13.9 倍まで縮む。**
  その代わり ``w=9`` は 9 節点(step=8 なら 72 px)を平らとみなすので、
  切欠き先端のような**曲率のあるひずみ場では尖頭を過小に読む**。
  対称窓の最小二乗は 1 次のひずみ場なら厳密に返すが、曲がった場は鈍る。
  既定を置くと、選んだ覚えのないトレードオフの上で数字が出る。

★ NaN の扱い —— 0 で埋めない
  ``u`` か ``v`` に NaN があると、その点を含む ``window x window`` の
  当てはめは定義できない。**NaN を含む窓の出力をすべて NaN** にする
  (``u``/``v`` 両方の欠測を合わせた 1 つのマスクを 3 成分に適用)。
  NaN を 0 と見なすと、測れなかった点が「変位 0 の点」として当てはめに
  効き、**周囲に本物に見える偽のひずみ勾配**を作る。

fail-closed
  * ``u`` / ``v`` が 2 次元でない、形が違う、4x4 未満。
  * ``u`` に ``(2, h, w)`` の ``flow2d`` を丸ごと渡した(直し方つきで拒否)。
  * ``window`` が偶数・3 未満・場より大きい。
  * ``spacing`` が非正・非有限。
  * ``method`` が ``"infinitesimal"`` / ``"green"`` 以外。
  * ``window`` と ``method`` を省いた呼び出しは ``TypeError``
    (既定値を置いていないので Python の引数機構でそのまま落ちる)。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dic_strain](../../../../examples/poc_dic_strain.py) — `py -3.11 examples/poc_dic_strain.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[piv_cross_correlate](../estimate/piv_cross_correlate.md) · [piv_multipass](../estimate/piv_multipass.md) · [piv_deform_pass](../estimate/piv_deform_pass.md) · [correlation_quality](correlation_quality.md) · [speckle_quality](speckle_quality.md)

## 同カテゴリ(`solid`)

[correlation_quality](correlation_quality.md) · [speckle_quality](speckle_quality.md)

---
*Provenance: dic.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
