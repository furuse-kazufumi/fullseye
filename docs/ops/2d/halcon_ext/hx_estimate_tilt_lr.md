---
op: hx_estimate_tilt_lr
dim: 2d
category: halcon_ext
in: image
out: feature
halcon: estimate_tilt_lr
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# hx_estimate_tilt_lr — 2D `halcon_ext` op

- **データ種**: `image` → `feature`
- **呼び出し**: `fullseye.apply(img, "hx_estimate_tilt_lr", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `estimate_tilt_lr`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_estimate_tilt_lr: input → output](../../_fig/hx_estimate_tilt_lr.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

## 使い方

Lee-Rosenfeld: 光源方位角 tilt = atan2(<Ey>, <Ex>)(平均勾配方向)。[0,1] 正規化。

Sobel 勾配 ``Ex``(列方向)・``Ey``(行方向)を画像全体で平均し、``tilt = arctan2(<Ey>, <Ex>)`` を
``(tilt / 2π) mod 1`` で [0,1) に写した ``np.float64`` を返す。Lambertian 面で光源方位(tilt)が平均勾配の方向に
現れるという Lee-Rosenfeld の推定。

- ``a``, ``b`` は未使用。
- 0 が +列方向、0.25 が +行方向(画像では下)、以下その向きに回る。平均勾配がほぼ 0 だと ``arctan2(0, 0) = 0`` で
0 に落ちる。

勾配の生の平均を使うので、コントラストの強い部分の方向に引きずられる。表面の反射率や形状がランダムで、照明の
傾きだけが全体の勾配の偏りを作る、という前提が要る。局所コントラストの影響を抑えた版は ``hx_estimate_tilt_zc``。
角度値は周期量なので 0 と 1 付近は同じ方向(差を取るときは注意)。

## 詳しい使い方ガイド

- [gallery2d_halcon_ext ファミリ ガイド](../guides/gallery2d_halcon_ext.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
hx_estimate_tilt_lr 0.50 0.50
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
