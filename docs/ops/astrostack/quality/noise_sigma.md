---
op: noise_sigma
dim: astrostack
category: quality
in: image2d
out: measurement
examples: [acoustic_condition_monitoring, astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# noise_sigma — ASTROSTACK `quality` op

- **データ種**: `image2d` → `measurement`
- **呼び出し**: `import astrostack; astrostack.noise_sigma(image, method='mad', kappa=3.0, iters=5)` (または `opsastrostack.get("noise_sigma")`)

## 使い方

背景の雑音 sigma を頑健に推定する(星に汚されない一つの実数)。

*method* ``"mad"`` は中央絶対偏差の ``1.4826`` 倍(正規分布のときに標準偏差と
一致する定数)。``"clip"`` は対称な κ-σ クリップを ``iters`` 回。星は上側だけの
外れ値なので、素の ``std`` を使うと**星が明るいほど「雑音」が大きく**なる
—— 128x128 に 40 星(フラックス 3e3〜4e4 e-)、真の背景 σ が
``sqrt(100 + 36) = 11.662`` のフレームでの実測: 素の ``np.std`` は
**175.43(真値の 15.0 倍)**、``method="mad"`` は 13.804(+18.4 %)、
``method="clip"`` は 12.349(+5.9 %)。MAD が 1 % で当たるのは星がまばらな
ときだけで、**混み合った視野では星の裾が背景に効く** —— そこまで要求する
なら ``"clip"`` を選ぶこと。桁が違うのは ``std`` だけで、そこが要点。

``sqrt(N)`` 則を絵にするとき図に載せる数値は、すべてこの op の返り。

Returns ``float``(*image* と同じ単位)。

**Raises** ``ValueError``: 2-D でない / 非有限を含む / *method* が
:data:`NOISE_METHODS` にない場合。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [acoustic_condition_monitoring](../../../../examples/acoustic_condition_monitoring.py) — `py -3.11 examples/acoustic_condition_monitoring.py`
- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`quality`)

[frame_quality](frame_quality.md) · [lucky_select](lucky_select.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
