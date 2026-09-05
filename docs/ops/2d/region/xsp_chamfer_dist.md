---
op: xsp_chamfer_dist
dim: 2d
category: region
in: region
out: image
examples: [gallery2d_region]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# xsp_chamfer_dist — 2D `region` op

- **データ種**: `region` → `image`
- **呼び出し**: `fullseye.apply(img, "xsp_chamfer_dist", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

City-block (chamfer) distance to the nearest background pixel, normalised to [0,1].

★2026-09-02: 縮退入力での **符号つきセンチネル** を潰す。
``scipy.ndimage.distance_transform_cdt`` は「背景画素が 1 つも無い」入力に対して
距離ではなく **-1 を全画素に**書く(実測: ``np.ones((8,8), bool)`` -> min=max=-1)。
旧実装はそれをそのまま ``_norm`` に通していたので、**塗り潰された領域の距離マップが
一様 -1 の「画像」**になっていた —— 例外も警告も出ないまま値域 [0,1] の image 契約を
破り、保存・表示では全面が黒に潰れる。

背景が無い = どの画素も「無限に遠い」ので、正規化後の正直な答えは **一様 1.0**。
前景が無いときは距離 0 の一様 0.0。どちらも符号つきの値を返さない。

## 詳しい使い方ガイド

- [gallery2d_region ファミリ ガイド](../guides/gallery2d_region.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_region](../../../../examples/gallery2d_region.py) — `py -3.11 examples/gallery2d_region.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`region`)

[reg_erode](reg_erode.md) · [reg_dilate](reg_dilate.md) · [reg_open](reg_open.md) · [reg_close](reg_close.md) · [fill_holes](fill_holes.md) · [select_largest](select_largest.md) · [remove_small](remove_small.md) · [invert_region](invert_region.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
