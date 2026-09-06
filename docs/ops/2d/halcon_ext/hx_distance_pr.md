---
op: hx_distance_pr
dim: 2d
category: halcon_ext
in: region
out: feature
halcon: distance_pr
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# hx_distance_pr — 2D `halcon_ext` op

- **データ種**: `region` → `feature`
- **呼び出し**: `fullseye.apply(img, "hx_distance_pr", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `distance_pr`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_distance_pr: input → output](../../_fig/hx_distance_pr.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![hx_distance_pr: knob a sweep](../../_fig/hx_distance_pr.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![hx_distance_pr: knob b sweep](../../_fig/hx_distance_pr.b.jpg)

**段階**(前置きの op → この op。左から順):

![hx_distance_pr: stages](../../_fig/hx_distance_pr.chain.jpg)

## 使い方

クエリ点(正規化 a,b)から region までの最小距離(feature)。距離変換で。

``v > 0.5`` の region の補集合にユークリッド距離変換(``distance_transform_edt``)を掛け、正規化座標 ``(a, b)``
の画素での値(その画素から最も近い region 画素までの距離)を ``max(H, W)`` で割って 1 で頭打ちした
``np.float64`` で返す。

- ``a`` → 行 ``min(int(a*H), H-1)``。
- ``b`` → 列 ``min(int(b*W), W-1)``。
- region が空なら 1.0(「最大距離」の意味。``hx_distance_pc`` の空=0 とは逆なので注意)。

クエリ点が region の内側なら 0。距離変換は画像全体に対して計算するので 1 点の問い合わせとしては重いが、
値は厳密な画素間距離(``hx_distance_pc`` のような頂点近似ではない)。含むかどうかだけなら
``hx_test_region_point``。

## 詳しい使い方ガイド

- [gallery2d_halcon_ext ファミリ ガイド](../guides/gallery2d_halcon_ext.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
threshold 0.50 0.50
hx_distance_pr 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_halcon_ext](../../../../examples/gallery2d_halcon_ext.py) — `py -3.11 examples/gallery2d_halcon_ext.py`

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md)

## 同カテゴリ(`halcon_ext`)

[hx_gen_circle](hx_gen_circle.md) · [hx_gen_ellipse](hx_gen_ellipse.md) · [hx_gen_rectangle2](hx_gen_rectangle2.md) · [hx_gen_checker_region](hx_gen_checker_region.md) · [hx_gen_grid_region](hx_gen_grid_region.md) · [hx_gabor](hx_gabor.md) · [hx_fit_surface1](hx_fit_surface1.md) · [hx_fit_surface2](hx_fit_surface2.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
