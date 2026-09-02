---
op: align_frames
dim: astrostack
category: align
in: images
out: images
examples: [astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# align_frames — ASTROSTACK `align` op

- **データ種**: `images` → `images`
- **呼び出し**: `import astrostack; astrostack.align_frames(frames, reference=0, order=3, **align_kw)` (または `opsastrostack.get("align_frames")`)

## 使い方

フレーム列を 1 枚の基準へ重ね合わせる。

各フレームについて :func:`frame_align` で変換を推定し、
:func:`scipy.ndimage.affine_transform` で逆写像・再標本化する。

**正直な注意**: 補間は像を保存しない。ノイズ無しの 64x64 / 12 星を
``(0.5, 0.5)`` px だけずらして戻した実測::

    order=1 (双一次)   総フラックス -0.016 %   星のピーク -11.437 %
    order=3 (スプライン) 総フラックス -0.016 %   星のピーク  -0.312 %

総フラックスはどちらでもほぼ保たれるのに、**星のピークは双一次だと 1 割
以上落ちる** —— 0.5 px ずらしは双一次にとって最悪の位相で、隣り合う
4 画素の単純平均になるからである。既定を ``order=3`` にしてあるのはこの
実測による(``order=3`` は星の周りに極小の負の縁を作るが、上の測定では
最小値 -0.0000 で目に見える量ではなかった)。

**フラックスもピークも厳密に保ちたいなら補間せず** :func:`drizzle_resample`
へ渡すこと —— 補間しないことが drizzle の存在理由そのもの。ただし
**推定シフトをそのまま渡してはいけない**: ここで返す ``matrices`` の並進は
「基準へ戻す」向きで、drizzle が要る向きとは符号が逆。
:func:`drizzle_shifts` を通すこと::

    aligned, mats = align_frames(frames)
    sci, wht = drizzle_resample(frames, drizzle_shifts(mats), scale=2.0)

Returns ``(aligned, matrices)``:

* ``aligned`` —— 長さ ``N`` の list、各 ``(H, W)`` float64(``images`` 語彙)。
  基準フレームは**変換を通さずそのまま**返す(恒等変換でも補間は像を鈍らせる
  ので、通す理由が無い)。
* ``matrices`` —— 長さ ``N`` の list、各 ``(3, 3)``。基準は単位行列。

**Raises** ``ValueError``: *frames* が list / tuple でない / 枚数が 2 未満 /
*reference* が範囲外 / *order* が 0〜5 の外 / :func:`frame_align` が
どれか 1 枚で失敗した場合(**失敗を黙って恒等変換に落とさない**)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`images` を入力に取れる)

[lucky_select](../quality/lucky_select.md) · [sigma_clip_stack](../stack/sigma_clip_stack.md) · [drizzle_resample](../stack/drizzle_resample.md) · [cosmic_ray_reject_stack](../cosmic/cosmic_ray_reject_stack.md)

## 同カテゴリ(`align`)

[frame_align](frame_align.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
