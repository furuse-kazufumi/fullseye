---
op: surface_form_remove
dim: roughness
category: prepare
in: depth
out: depth
examples: [poc_surface_roughness]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# surface_form_remove — ROUGHNESS `prepare` op

- **データ種**: `depth` → `depth`
- **呼び出し**: `import roughness; roughness.surface_form_remove(z, dx, order=1, method='ls', thresh=None, dy=None, iters=200, seed=0)` (または `opsroughness.get("surface_form_remove")`)

## 使い方

格子のまま平面 / 二次曲面を除く。``(residual, coeffs)`` を返す。

引数
  z       高さ場。
  dx, dy  標本間隔。``dy=None`` は正方画素。
  order   1 = 平面、2 = 二次曲面。
  method  ``"ls"``(最小二乗)または ``"ransac"``(ロバスト)。
  thresh  RANSAC の内点しきい値(高さの単位)。``None`` なら最小二乗残差の
          ロバストな散らばり ``2.5 x 1.4826 x MAD`` を使う。
  iters   RANSAC の試行回数。``seed`` で決定的。

``coeffs`` は **場の中心を原点とする物理座標の単項式係数**。
``order=1`` なら ``[c0, gx, gy]`` で ``gx``/``gy`` がそのまま勾配、
``order=2`` なら ``[c0, gx, gy, cxx, cxy, cyy]``(``x^2, xy, y^2`` の順)。

★ なぜ格子のまま受けるのか
  既存の `fit_plane` / `fit_plane_ransac` は (N,3) 点群しか受けない。
  512² の高さ場を渡すには毎回 ``column_stack`` で 262144x3 = **6.3 MB** に
  展開する必要がある(実測)。ここは格子を格子のまま受け、基底も
  1 次元ベクトルの外積で作るので展開が要らない。

★ 費用(実測、1024x1024、``iters=200``)
  ``method="ls"`` 47 ms に対し ``method="ransac"`` は **1.8 秒**(38 倍)。
  RANSAC は毎回 1024² 点の残差を数え直すので、``iters`` に線形に効く。
  粗さだけを見るなら「LS + λc ハイパス」で同じ答えが 40 分の 1 で出る
  (下の実測を参照)—— **RANSAC を既定にしない理由がこれ。**

★ 落とし穴 —— ロバストが要るのは「深い傷」ではなく「**広い**外れ値」。
  ただし外れ値が多数派になると RANSAC も同時に壊れる。
  深さ 3 µm の傷 4 本を片側に寄せた 512x512 の面で、傷の**幅だけ**を
  変えた実測(傾き 0.050/-0.025 を仕込んで除く。真値は傷を含む面そのもの):

      傷の半値半幅   面積比    LS の Sq 誤差   RANSAC の Sq 誤差   改善
         4 µm         5.6 %      -1.94 %          -0.39 %        5.0 倍
        12 µm        16.3 %      -6.47 %          -3.03 %        2.1 倍
        24 µm        31.0 %     -13.79 %         -11.53 %        1.2 倍
        40 µm        46.0 %     -23.80 %         -23.56 %        1.0 倍

  3 つ読める:
    * 効くのは深さではなく**面積比**。「深い傷 = ロバスト必須」は早合点で、
      正しくは「**広い**外れ値 = ロバスト必須」。
    * 誤差は必ず**過小側**に出る —— 最小二乗が「傷が片側に寄っている
      ことによる本物の非対称」まで平面として吸い上げるから。
      **合否判定では危険な向きに壊れる。**
    * **面積比 46 % では RANSAC も助けにならない**(改善 1.0 倍)。
      外れ値が半分近くを占めると、RANSAC の多数決そのものが傷を選ぶ。
      ロバスト当てはめは「外れ値が少数派である」という前提の道具で、
      その前提が切れる所は表で示すしかない。

★ 落とし穴 —— λc を後段に置くと LS と RANSAC の差は消える
  同じ面(半値半幅 4 µm)に λc=80 µm のハイパスを後から掛けると、
  Sq 誤差は **LS +0.00 % / RANSAC -0.00 %**(上の表では 5.0 倍差)。
  余計に除いた平面は純粋な長波長なので、ハイパスが同じものをもう一度
  捨てるだけ。**当てはめのロバスト性が効くのは λc を掛けない運用
  (平面度・形状偏差)のとき。** 粗さだけを見るなら順序で救える。
  なお平面そのものの回復は LS でも良く、上の面で仕込んだ勾配
  0.050 / -0.025 に対し 0.050006 / -0.025127 が返る(実測)。

fail-closed
  * ``order`` が 1 か 2 以外 / ``method`` が ``"ls"``・``"ransac"`` 以外。
  * ``thresh`` が非正・非有限。
  * RANSAC が内点を規定数集められない(退化した面)。

## 詳しい使い方ガイド

- [surface_roughness ファミリ ガイド](../guides/surface_roughness.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_surface_roughness](../../../../examples/poc_surface_roughness.py) — `py -3.11 examples/poc_surface_roughness.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[surface_filter](surface_filter.md) · [surface_params](../measure/surface_params.md) · [surface_psd](../measure/surface_psd.md)

## 同カテゴリ(`prepare`)

[surface_filter](surface_filter.md)

---
*Provenance: roughness.py — ROUGHNESS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
