---
op: dc_rpca_sparse
dim: 2d
category: decomposition
in: image
out: image
examples: [gallery2d_texture_freq]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# dc_rpca_sparse — 2D `decomposition` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "dc_rpca_sparse", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![dc_rpca_sparse: input → output](../../_fig/dc_rpca_sparse.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![dc_rpca_sparse: knob a sweep](../../_fig/dc_rpca_sparse.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![dc_rpca_sparse: other inputs](../../_fig/dc_rpca_sparse.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

Robust-PCA sparse (defect / anomaly) residual = input - low-rank, at 0.5.

``dc_rpca_lowrank`` と同じ inexact ALM の PCP 分解 ``M = L + S`` を行い、
スパース項 ``S`` を 0.5 を中心に置いて返す(``clip(S + 0.5, 0, 1)``)。背景と
同じ画素は 0.5、背景より明るい孤立点は 0.5 より上、暗い点は下に出る符号つき
残差で、飽和しない範囲で ``dc_rpca_lowrank + (この出力 - 0.5) == 入力``。
``a`` はスパース重み ``λ = (0.5 + 1.5*a)/sqrt(max(m, n))`` で、大きいほど
``S`` が疎(小さな残差は 0 に丸められ、はっきりした欠陥だけ残る)、``a=0``
ではほぼ全画素に残差が出る。``b`` は未使用。

長辺 64 超の画像は縮小して ``L`` を解き、``S`` は元解像度で
``S = soft(M0 - L_up, λ/μ_final)`` として作り直す(縮小した ``S`` を拡大
すると 1 画素欠陥がにじんで振幅を失うため)。入力は [0,1] の 2 次元に揃え、
返り値は同形 float64、[0,1]。全零画像では ``S = 0`` で一様 0.5。例外時は
fail-soft で入力のクリップ版が返り、台帳に記録される。

後段では ``|出力 - 0.5|`` が欠陥の強さなので、``threshold`` 系の op で 0.5 から
離れた画素を拾う(明側・暗側のどちらを拾うかはしきい値の向きで決まる)。周期
背景(織物・格子・ディスプレイ)上の点欠陥・傷の検出向けで、非周期背景では
残差に背景の凹凸がそのまま混ざる。

## 詳しい使い方ガイド

- [gallery2d_texture_freq ファミリ ガイド](../guides/gallery2d_texture_freq.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
dc_rpca_sparse 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_texture_freq](../../../../examples/gallery2d_texture_freq.py) — `py -3.11 examples/gallery2d_texture_freq.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`decomposition`)

[dc_structure_texture](dc_structure_texture.md) · [dc_texture_residual](dc_texture_residual.md) · [dc_rpca_lowrank](dc_rpca_lowrank.md) · [dc_retinex](dc_retinex.md) · [dc_local_contrast_norm](dc_local_contrast_norm.md) · [dc_homomorphic](dc_homomorphic.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
