---
op: synth_frame_series
dim: astrostack
category: synth
in: 
out: images
examples: [astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# synth_frame_series — ASTROSTACK `synth` op

- **データ種**: `なし` → `images`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import astrostack; astrostack.synth_frame_series(shape=(128, 128), n_frames=8, dither_px=1.5, fwhm_px=3.2, fwhm_jitter=0.0, n_cosmic=0, seed=0, **starfield_kw)` (または `opsastrostack.get("synth_frame_series")`)

## 使い方

同じ星野を ``n_frames`` 枚、**別々のノイズと別々のディザ**で撮り直す。

星の座標・フラックスは全フレームで同じ(``field_seed`` を固定して星の抽選を
再現し、観測ごとの ``seed`` と ``shift_row`` / ``shift_col`` だけを振る)ので、
位置合わせ・合成・drizzle の正解が 1 組で済む。*fwhm_jitter* を与えると FWHM がフレームごとに揺れる
—— これが lucky imaging の「シーイングが揺らぐ」条件で、0 のままだと
:func:`lucky_select` が選ぶ理由が無くなる。

ディザは ``dither_px`` を半径とする決定的な螺旋(``i`` 番目のフレームを
``dither_px * (i / (n-1))`` の半径・黄金角の方向へ置く)。乱数でないので
フレーム数を変えても並びが安定し、図が再現する。

Returns ``(frames, truth)``:

* ``frames`` —— 長さ ``n_frames`` の list、各要素は ``(H, W)`` float64。
  **``images`` 語彙そのもの**なので、合成 op へそのまま渡せる。
* ``truth`` —— :func:`synth_starfield` の truth に、``shifts`` ``(N, 2)``
  (各フレームの ``(dr, dc)``)と ``fwhms`` ``(N,)`` を足したもの。
  ``rows`` / ``cols`` は**ディザ前**(フレーム 0 の位置)。

**Raises** ``ValueError``: :func:`synth_starfield` の条件に加えて、
*n_frames* が 1 未満、*dither_px* が負、*fwhm_jitter* が負の場合。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`images` を入力に取れる)

[lucky_select](../quality/lucky_select.md) · [sigma_clip_stack](../stack/sigma_clip_stack.md) · [drizzle_resample](../stack/drizzle_resample.md) · [cosmic_ray_reject_stack](../cosmic/cosmic_ray_reject_stack.md) · [align_frames](../align/align_frames.md)

## 同カテゴリ(`synth`)

[synth_starfield](synth_starfield.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
