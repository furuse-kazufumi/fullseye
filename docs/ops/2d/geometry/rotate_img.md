---
op: rotate_img
dim: 2d
category: geometry
in: image
out: image
halcon: rotate_image
examples: [gallery2d_geometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# rotate_img — 2D `geometry` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "rotate_img", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `rotate_image`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

Rotate about the image centre by ``-45° + 90°·a`` (a=0.5 → 0°). ``b`` unused.

    ★呼び出し規約(2026-09-02 に明文化。実装は変えていない):

    * **キャンバスを変えない** (``reshape=False``)。出力の shape は入力と同じで、
      回転で枠外へ出た画素は捨てられる。
    * **枠外は鏡映で埋める** (``mode="reflect"``)。つまり回すと **四隅に元画像が
      折り返して写り込む**(帳票を回すと隅に鏡文字が出る)。

    どちらが正典かは用途で割れる。**この op の正典は「連鎖しても常に同じ形・
    同じ値域の画像が出ること」** — 進化パイプラインは image を段間で無条件に
    繋ぐので、shape が変わる/枠外に定数が入ると後段の統計(平均・分散・
    ヒストグラム)が回転量に依存して動いてしまう。鏡映は「無から作った定数」で
    はなく画像自身の統計を保つので、この用途ではこちらを採る。

    **deskew(帳票の傾き補正)には向かない**: 折り返した鏡文字が OCR / 二値化に
    そのまま乗る。背景色で埋めたい場合はこの op を使わず、
    ``scipy.ndimage.rotate(v, ang, reshape=True, mode="constant", cval=bg)`` を
    直接呼ぶこと(``fullseye.apply`` の 2 つまみ界面では背景色を渡せない)。
    同じ規約が backends_auto の ``rotate_image`` (``_sh_geom`` kind="rotate")にも
    そのまま当てはまる。

## 詳しい使い方ガイド

- [gallery2d_geometry ファミリ ガイド](../guides/gallery2d_geometry.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_geometry](../../../../examples/gallery2d_geometry.py) — `py -3.11 examples/gallery2d_geometry.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`geometry`)

[rescale_img](rescale_img.md) · [affine_warp](affine_warp.md) · [sk_swirl](sk_swirl.md) · [mirror_image](mirror_image.md) · [transpose_region](transpose_region.md) · [rotate_image](rotate_image.md) · [zoom_image_factor](zoom_image_factor.md) · [zoom_image_size](zoom_image_size.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
