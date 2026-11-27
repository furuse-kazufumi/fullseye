---
op: moments_region_2nd_invar
dim: 2d
category: features
in: region
out: feature
halcon: moments_region_2nd_invar
gpu: あり(lbl_moments_region_2nd_invar)
examples: [gallery2d_features, poc_rotation_invariance_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.2.0  # fullseye lib version this note was generated for
---

# moments_region_2nd_invar — 2D `features` op

- **データ種**: `region` → `feature`
- **呼び出し**: `fullseye.apply(img, "moments_region_2nd_invar", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `moments_region_2nd_invar`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: あり(`lbl_moments_region_2nd_invar`、`device="cuda"` で高速経路)

![moments_region_2nd_invar: input → output](../../_fig/moments_region_2nd_invar.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![moments_region_2nd_invar: stages](../../_fig/moments_region_2nd_invar.chain.jpg)

## 使い方

非推奨の互換別名。``moments_region_2nd`` をそのまま呼ぶので返り値は同一である。
``moments_region_2nd_invar`` は 2.0 で削除予定で、呼ぶたびに ``DeprecationWarning``
を出す。移行先は ``moments_region_2nd``。

HALCON では両名は別の複数値演算子だが、この repo の 1 スカラー化では量が潰れて
同一になった。docs/KNOWN_ISSUES.md §52。

``a``, ``b`` は未使用。

## 詳しい使い方ガイド

- [gallery2d_features ファミリ ガイド](../guides/gallery2d_features.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
threshold 0.50 0.50
moments_region_2nd_invar 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_features](../../../../examples/gallery2d_features.py) — `py -3.11 examples/gallery2d_features.py`
- [poc_rotation_invariance_audit](../../../../examples/poc_rotation_invariance_audit.py) — `py -3.11 examples/poc_rotation_invariance_audit.py`

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md) · [feature_to_img](../bridge/feature_to_img.md)

## 同カテゴリ(`features`)

[effective_bit_depth](effective_bit_depth.md) · [blob_count](blob_count.md) · [area_frac](area_frac.md) · [count_contours](count_contours.md) · [total_length](total_length.md) · [vol_count](vol_count.md) · [sk_euler](sk_euler.md) · [sk_entropy_feat](sk_entropy_feat.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
