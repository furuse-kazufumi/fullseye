---
op: add_noise_distribution
dim: 2d
category: noise
in: image
out: image
halcon: add_noise_distribution
examples: [gallery2d_smoothing_rank]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# add_noise_distribution — 2D `noise` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "add_noise_distribution", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `add_noise_distribution`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

画像に加法性ノイズを加える。実装はガウス（正規分布）ノイズのみで、``add_noise_white`` と同じ ``_sh_noise`` の ``gaussian`` 分岐を共有する。乱数は a から決まる固定シード（``int(a*997)+7``）で発生させるため同じ a なら毎回同じノイズになる（決定的）。b がノイズの標準偏差を 0.02〜0.22 に振る。

HALCON の ``add_noise_distribution``（任意の確率分布（ヒストグラム指定）に従うノイズを加える演算）とは異なり、この実装は常にガウス分布のノイズしか生成できない近似 —— 分布形状の指定は反映されない。

## 詳しい使い方ガイド

- [gallery2d_smoothing_rank ファミリ ガイド](../guides/gallery2d_smoothing_rank.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [mv_image_sensors](../../optics/guides/mv_image_sensors.md) — 産業用イメージセンサ（現行品中心）

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_smoothing_rank](../../../../examples/gallery2d_smoothing_rank.py) — `py -3.11 examples/gallery2d_smoothing_rank.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`noise`)

[add_noise_white](add_noise_white.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
