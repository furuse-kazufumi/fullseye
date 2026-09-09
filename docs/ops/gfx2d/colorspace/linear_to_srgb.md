---
op: linear_to_srgb
dim: gfx2d
category: colorspace
in: rgb
out: rgb
examples: [gfx2d_scene, poc_leaf_disease_area, poc_pigment_unmixing, poc_white_balance]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# linear_to_srgb — GFX2D `colorspace` op

- **データ種**: `rgb` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.linear_to_srgb(img)` (実装を直接呼ぶなら `import gfx2d; gfx2d.linear_to_srgb(img)`、台帳から引くなら `opsgfx2d.get("linear_to_srgb")`)

## 使い方

Linear light back to sRGB encoding. Exact inverse of :func:`srgb_to_linear`.

式(IEC 61966-2-1): ``c <= 0.0031308`` なら ``12.92 c``、それ以外は
``1.055 c^(1/2.4) - 0.055``。チャネルごと・画素ごとに独立。

- ``img``: ``(H, W)`` / ``(H, W, 1)`` / ``(H, W, 3)`` / ``(H, W, 4)`` の float。
  値は ``[0, 1]``(許容 1e-9)でなければ ``ValueError`` ―― 線形光の HDR 値
  (1 超)は先に露光を掛けて収めること。整数配列は最大値が 1 以下のときだけ
  通る(0〜255 のバッファは拒否)。bool は 0/1 として通る。NaN/Inf、複素数、
  マスク配列は ``ValueError``。
- ``(H, W, 4)`` のアルファ(4 チャネル目)は**変換しない**(被覆率は元々線形)。
- 返り値: 同形の float64 の複製、``[0, 1]``。
- ``(3,)`` の 1 色や ``(N, 3)`` の色表はこの op では受けない(画像 API)。
  任意の形に掛けたいときは ``imgmetrics`` 側の同名関数がここへ委譲している。

``radial_light`` / ``light_mask`` / ``bloom`` など線形光で計算した結果を、
ファイルに書く・画面に出す直前に 1 回だけ掛ける。二度掛けると中間調が
浮く(例外は出ない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`
- [poc_leaf_disease_area](../../../../examples/poc_leaf_disease_area.py) — `py -3.11 examples/poc_leaf_disease_area.py`
- [poc_pigment_unmixing](../../../../examples/poc_pigment_unmixing.py) — `py -3.11 examples/poc_pigment_unmixing.py`
- [poc_white_balance](../../../../examples/poc_white_balance.py) — `py -3.11 examples/poc_white_balance.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[srgb_to_linear](srgb_to_linear.md) · [blend_mode](../composite/blend_mode.md) · [light_mask](../light/light_mask.md) · [normal_map_decode](../light/normal_map_decode.md) · [bloom](../post/bloom.md) · [vignette](../post/vignette.md) · [chromatic_aberration](../post/chromatic_aberration.md) · [film_grain](../post/film_grain.md)

## 同カテゴリ(`colorspace`)

[srgb_to_linear](srgb_to_linear.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
