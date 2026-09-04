---
op: lucky_select
dim: astrostack
category: quality
in: images
out: indices
examples: [astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# lucky_select — ASTROSTACK `quality` op

- **データ種**: `images` → `indices`
- **呼び出し**: `import astrostack; astrostack.lucky_select(frames, keep_fraction=0.3, min_keep=1, **quality_kw)` (または `opsastrostack.get("lucky_select")`)

## 使い方

品質点の上位 ``keep_fraction`` だけを採る —— lucky imaging の選別。

採用枚数は ``max(min_keep, ceil(keep_fraction * N))``。**必ず 1 枚は残す**
ので、``keep_fraction`` をいくら小さくしても空にはならない(空の合成を
後段へ渡す方が事故が大きい)。並べ替えは点の降順で、同点は元の順序を保つ
安定ソート —— 同じ入力なら同じ並びが返る。

Returns ``(indices, scores)``:

* ``indices`` —— ``(K,)`` int64、**採用フレームの添字を良い順に**
  (``indices`` 語彙)。``[frames[i] for i in indices]`` がそのまま
  :func:`sigma_clip_stack` へ渡せる。
* ``scores`` —— ``(N,)`` float64、**全フレームの点**(捨てた側も含む)。
  捨てた理由を図にできるように、選別の結果ではなく素材を返す。

Ground truth it reproduces(``tests/test_astrostack.py``): 同じ星野を
FWHM だけ変えて撮ったフレーム列では、点は FWHM とともに**下がる**。
96x96 に 20 星、FWHM を 3.462〜6.080 px で振った 12 枚の実測で
``corr(fwhm, score) = -0.925``。上位 25 %(3 枚)を採って平均合成すると、
12 枚全部を平均した場合に比べて合成後の FWHM が 4.403 → 3.672 px、
**16.6 % 改善**する —— 枚数を 1/4 に減らしたのに像は鋭くなる、というのが
lucky imaging の主張そのもの(その代わり雑音は sqrt(4) = 2 倍になる)。

**Raises** ``ValueError``: *frames* が list / tuple でない(3-D 配列は
明示的に拒否)/ 枚数が 1 未満 / ``keep_fraction`` が (0, 1] の外 /
*min_keep* が枚数を超える場合。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`indices` を入力に取れる)

—

## 同カテゴリ(`quality`)

[frame_quality](frame_quality.md) · [noise_sigma](noise_sigma.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
