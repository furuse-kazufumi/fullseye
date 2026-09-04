---
op: drizzle_resample
dim: astrostack
category: stack
in: images
out: image2d
examples: [astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# drizzle_resample — ASTROSTACK `stack` op

- **データ種**: `images` → `image2d`
- **呼び出し**: `import astrostack; astrostack.drizzle_resample(frames, shifts=None, scale=2.0, pixfrac=1.0)` (または `opsastrostack.get("drizzle_resample")`)

## 使い方

Drizzle —— 副画素でずれた複数フレームから細かい格子を作る(面積保存)。

Fruchter & Hook, *Drizzle: A Method for the Linear Reconstruction of
Undersampled Images*, PASP 114, 144 (2002)。入力画素を一回り縮めた
「しずく(drop、辺 ``pixfrac``)」とみなし、出力格子の画素との**重なり面積**
に比例してフラックスを撒く。補間しないので、

* **総フラックスが保存される。** しずくが出力格子の内側に収まっている限り
  ``sci.sum()`` は入力フレームの総和の平均と厳密に一致する
  (実測: ``shifts=0``、``scale=2``、``pixfrac=0.7`` で相対誤差 0.0)。
  これが**返り値だけで検算できる**形にしてある理由。
* ``pixfrac`` を小さくするほど、しずくが出力画素の内側に入る割合が増えて
  **解像度は上がるが、覆われない出力画素が出る**(``wht`` がそこで小さく
  なる)。この綱引きが drizzle の唯一の調整点。

**効くのは標本化が足りていないときだけ**、というのが実測の結論。48x48 に
10 星、ディザ 1.5 px、16 枚での測定(値は入力画素に換算した FWHM)::

    真の FWHM  単フレーム  そのまま平均  drizzle x2 (pixfrac=0.5)
      1.0        1.773       2.249         1.312
      1.3        1.929       2.876         1.572
      1.8        2.262       2.648         3.086
      2.5        4.057       4.295         3.586

FWHM が 2 画素を割る(ナイキストを破る)ところでだけ drizzle が勝つ。
ディザしたフレームを**そのまま平均すると像は逆に鈍る**(1.773 → 2.249)
—— ずれを平均してしまうからで、drizzle はその同じずれを解像度に変える。
1.8 px 以上では既に十分標本化されているので、drizzle は得をせず
しずくの畳み込みぶんだけ損をする。

二つの星が分かれるかどうかで見ると分かりやすい。σ=0.55 px の星を 2 つ、
間隔を変えて 16 枚ディザ撮影し、平均合成と drizzle x3 (pixfrac=0.4) で
:func:`star_detect` した実測: **間隔 1.6 入力画素で、平均合成は 1 個、
drizzle は 2 個**を見つけた(2.0 px 以上ではどちらも 2 個)。

*shifts* は ``(N, 2)`` の ``(dr, dc)`` で、フレーム ``i`` が基準からどれだけ
ずれているか(:func:`synth_frame_series` の ``truth["shifts"]`` がこの向き)。
``None`` なら全部 0。

★ **符号に注意** —— :func:`frame_align` / :func:`align_frames` が返す行列の
並進は「フレームを基準へ**戻す**」向き、つまりここで要る ``(dr, dc)`` の
**符号が逆**である。推定値をそのまま渡すとずれが打ち消されず**倍**になり、
例外も出さずに二重像になる(実測: 6 枚 96x96 で ``est + truth ≈ 0``、
そのまま渡すと残差が 2 倍)。行列から正しい向きの shifts を作るには
:func:`drizzle_shifts` を使うこと。
**回転は受けない** —— 回転が入ると軸が分離せず重なり面積が閉形式で書けなく
なるので、先に :func:`align_frames` で戻すこと(そこで補間の誤差を払う、
という取引が見えている方が正直)。

Returns ``(sci, wht)``:

* ``sci`` —— ``(round(H*scale), round(W*scale))`` float64、**総フラックス
  単位**(入力と同じ電子)。格子の外へ出たしずくの分だけ総和が減るので、
  ``sci.sum()`` と入力総和の差は「縁で失った量」そのもの。
* ``wht`` —— 同じ形の重みマップ。出力画素が何枚ぶんのしずくに覆われたか
  (出力画素面積を 1 とする)。``pixfrac=1`` かつ ``shifts=0`` なら内部は
  厳密に 1.0。

★ **見る / 測る ときは ``sci / wht`` を使うこと。** ``sci`` は総フラックスを
保存するために「撒かれた量」をそのまま持っており、**被覆の不均一が像に
残っている**。``pixfrac`` を小さくすると被覆は格子状にむらを持つので、
生の ``sci`` に検出をかけるとその格子が星に化ける —— 実測(``scale=3``、
``pixfrac=0.4``、二重星 1 組の 24 枚)で :func:`star_detect` は生の ``sci``
に対して **200 個**(上限に張り付いた)を返し、``sci / wht`` に対しては
正しく **2 個**を返した。保存則(``sci``)と見た目(``sci / wht``)は
別の量であり、片方をもう片方の代わりに使うと**例外なく間違う**。

**Raises** ``ValueError``: *frames* が list / tuple でない / 形が揃って
いない / *scale* が 1 未満 / *pixfrac* が (0, 1] の外 / *shifts* の形が
``(N, 2)`` でない / 出力が :data:`MAX_OUTPUT_ELEMENTS` を超える場合。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[frame_quality](../quality/frame_quality.md) · [noise_sigma](../quality/noise_sigma.md) · [cosmic_ray_reject](../cosmic/cosmic_ray_reject.md) · [star_detect](../photometry/star_detect.md) · [psf_fit](../photometry/psf_fit.md) · [aperture_photometry](../photometry/aperture_photometry.md) · [frame_align](../align/frame_align.md)

## 同カテゴリ(`stack`)

[sigma_clip_stack](sigma_clip_stack.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
