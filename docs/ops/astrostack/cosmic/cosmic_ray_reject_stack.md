---
op: cosmic_ray_reject_stack
dim: astrostack
category: cosmic
in: images
out: images
examples: [astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# cosmic_ray_reject_stack — ASTROSTACK `cosmic` op

- **データ種**: `images` → `images`
- **呼び出し**: `import astrostack; astrostack.cosmic_ray_reject_stack(frames, kappa=5.0, min_frames=3, read_sigma=None, gain=1.0)` (または `opsastrostack.get("cosmic_ray_reject_stack")`)

## 使い方

フレーム間比較による宇宙線除去 —— **同じ場所に二度は当たらない**。

宇宙線が単一フレームの検出で難しいのは「星も尖っている」からだが、
位置合わせ済みのフレームが何枚もあれば話は簡単になる: 星は**毎回同じ画素**
に居て、宇宙線は**一度しか来ない**。そこで画素ごとにフレーム方向の中央値と
MAD を取り、``value > median + kappa * sigma`` のフレームだけを落として
中央値で埋める(下側は落とさない —— 宇宙線は必ず**足す**方向の外れ値で、
下側を落とすと欠損画素まで消してしまう)。

``min_frames`` 枚未満では中央値も MAD も意味を成さないので拒否する
(3 枚が最低限: 2 枚だとどちらが外れ値か決まらない)。**フレームは位置合わせ
済みであること** —— ずれたまま渡すと星が「一度しか来ない」ことになり、
星の方が消える。

**枚数が少ないと MAD 自体が当てにならない、という実測。** 8 枚の背景で
MAD 推定は真の σ 9.22 に対し 7.89(-14.5 %)、しかも画素ごとに大きく散る
ので、``kappa=5`` のつもりが実質 4.3 になり、偽陽性が真陽性の 2.4 倍
(546 対 227 画素)出た。しかも**偽陽性は星の上ではなく背景に居た**
(偽陽性画素の真値の中央値が 60 = sky そのもの)ので、「星が尖っているから」
では説明がつかない —— 少数標本の MAD が画素ごとに大きく散ることが原因。
対策は 2 つ重ねてある:

1. :func:`_mad_correction`(Croux & Rousseeuw 1992)の小標本補正を掛ける。
2. *read_sigma* を渡すと、**このモジュールが持つ唯一のノイズモデル**
   ``sigma = sqrt(median/gain + read_sigma^2)`` を尺度の**床**にする。
   これは :func:`synth_starfield` が使っているのと同じ
   「Poisson(信号) + Gauss(読み出し)」で、二つ目の理論ではない。
   床を入れると、標本のゆらぎで MAD がたまたま小さく出た画素が
   宇宙線に化けることが無くなる。

効き方の実測(128x128 / 25 星 / 1 枚あたり 10 宇宙線 / 8 枚、真の宇宙線
227 画素、``kappa=5``)::

    read_sigma=None  ->  594 画素検出、偽陽性 367、適合率 0.382
    read_sigma=5.0   ->  228 画素検出、偽陽性   1、適合率 0.996

再現率はどちらも **1.000**(1 画素も取りこぼさない)。床は宇宙線を
見逃す方向には効かない —— 宇宙線は雑音の何十倍もあるので、床が数 e-
上がっても越えてくる。

Returns ``(cleaned, masks)``:

* ``cleaned`` —— 長さ ``N`` の list、各 ``(H, W)`` float64(``images`` 語彙)。
* ``masks`` —— ``(N, H, W)`` bool、``True`` = 宇宙線と判定した画素。

**Raises** ``ValueError``: *frames* が list / tuple でない / 枚数が
*min_frames* 未満 / 形が揃っていない / *kappa* が非正 / *gain* が非正 /
*read_sigma* が負の場合。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`images` を入力に取れる)

[lucky_select](../quality/lucky_select.md) · [sigma_clip_stack](../stack/sigma_clip_stack.md) · [drizzle_resample](../stack/drizzle_resample.md) · [align_frames](../align/align_frames.md)

## 同カテゴリ(`cosmic`)

[cosmic_ray_reject](cosmic_ray_reject.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
