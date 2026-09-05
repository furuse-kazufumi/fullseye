---
op: macro_denoise
dim: 2d
category: macro
in: image
out: image
examples: [gallery2d_physics_alife_3d, sim2real_and_alife]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# macro_denoise — 2D `macro` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "macro_denoise", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

進化探索（``evolve.py`` / ``robust.py``）が発見した固定パイプライン: ``bilateral(a=0.10,b=0.76)`` → ``bilateral(a=0.12,b=0.27)`` → ``bilateral(a=0.73,b=0.11)``（既存 op のバイラテラルフィルタを、強さの違うパラメータで 3 段連ねたもの）。

``a``, ``b`` は凍結済みで未使用 —— このパイプライン自体が進化で選ばれた1 つの固定構成である。denoise 課題（PSNR）でロック済みホールドアウト26.28dB、手作りベースライン 22.83dB を上回る（train/holdout/locked_holdoutのどれで測っても手作りベースラインに勝っている）。HALCON に対応する単一オペレータは無い（``halcon=""``）。

## 詳しい使い方ガイド

- [gallery2d_physics_alife_3d ファミリ ガイド](../guides/gallery2d_physics_alife_3d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_physics_alife_3d](../../../../examples/gallery2d_physics_alife_3d.py) — `py -3.11 examples/gallery2d_physics_alife_3d.py`
- [sim2real_and_alife](../../../../examples/sim2real_and_alife.py) — `py -3.11 examples/sim2real_and_alife.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`macro`)

[macro_edge](macro_edge.md) · [macro_binarize](macro_binarize.md) · [macro_vol_denoise](macro_vol_denoise.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
