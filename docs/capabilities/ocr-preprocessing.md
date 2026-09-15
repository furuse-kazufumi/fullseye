---
id: ocr-preprocessing
title: OCR の前処理(傾き補正・局所 2 値化・行の切り出し)
title_en: OCR pre-processing (deskew, local binarisation, line extraction)
category: 見つける
ops: [sk_sauvola, rotate_image, remove_small, dilation_rectangle1]
examples: [gallery2d_segmentation, poc_matrix_code_reading, gallery2d_region]
version: 0.2.0
inputs: [image]
pipeline: [median, rotate_image, sk_sauvola, invert_region, remove_small, select_shape, dilation_rectangle1]
alternatives: [sk_niblack, adaptive_gauss_thresh, otsu, gray_bothat, unsharp, zoom_image_factor, affine_trans_image]
limits: OCR 本体(文字認識)は無い —— ここは認識器に渡す 2 値画像を作る層。大域 `otsu` は照明むらで文字が欠ける(局所 `sk_sauvola` へ)。傾きは `rotate_image` の `a` で与える(角度の推定は輪郭 `fit_line_contours` か射影で別に取る)。細い字画は `remove_small` で消える。
calibration: 文字は px で扱い、実寸校正は不要。読み取り解像度の目安は x 高さ 20 px 以上(足りなければ `zoom_image_factor`)。
---

# OCR の前処理(傾き補正・局所 2 値化・行の切り出し)

## できること

認識器(外部の OCR / 1-D・2-D コードのデコーダ)に渡す前の、**傾き補正 → 局所 2 値化 → ゴミ取り → 行のまとめ**を 2-D レジストリ op だけで組みます。認識そのものはこのライブラリの持ち場ではありません。

## What it does

Everything before the recogniser: deskew, local (Sauvola) binarisation, speck removal and merging characters into lines, all from registry operators. Recognition itself is out of scope.

## 向くところ / 向かないところ

**向く**: 照明むらのある刻印・ラベル・帳票。背景に対して文字が暗い(または明るい)ことが分かっているとき。

**向かない**: ★文字認識そのもの。★透視で歪んだ面(`affine_trans_image` で戻せるのは平面のアフィンまで)。★x 高さが 10 px を切る小さな字(`zoom_image_factor` で拡大しても情報は増えない)。

## 推奨パイプライン

`median` → `rotate_image` → `sk_sauvola` → `invert_region` → `remove_small` → `select_shape` → `dilation_rectangle1`

`median` で塩胡椒雑音を落とし → `rotate_image` で傾きを戻し(角度は別に推定: 行の輪郭 `fit_line_contours` か射影の分散最大)→ `sk_sauvola` で局所 2 値化(窓は文字の 2〜3 倍)→ 文字が暗いなら `invert_region` で前景に → `remove_small` でごみ → `select_shape` で文字らしい大きさだけ → `dilation_rectangle1` を横長に掛けて字を行に繋ぐ(行の矩形が切り出し単位)。

## 代替

局所 2 値化は `sk_niblack` / `adaptive_gauss_thresh`、むらが小さければ大域 `otsu`。照明むらは `gray_bothat`(暗い字)で先に引ける。ぼけた字は `unsharp`。小さい字は `zoom_image_factor`。平面の歪みは `affine_trans_image`。

## 限界

- 大域しきい値は照明むらで文字が欠ける・背景が黒くなる(`gallery2d_segmentation` が Sauvola との差を見せる)。
- `remove_small` の面積下限は細い字画(「い」の点など)を消す —— 下限は最小の字画で決める。
- `rotate_image` は補間するので縁がなまる。2 値化の**前**に回す。
- 傾き角の推定 op はこの連鎖に無い(`fit_line_contours` の向き、または射影)。

## 実寸校正

不要。ただし**解像度**は要件で、x 高さ 20 px 以上を目安に光学系を選ぶ(1-D コードは `poc_barcode_1d`、2-D コードは `poc_matrix_code_reading` がモジュール当たりの画素数で崖を測っている)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

yy, xx = np.mgrid[0:64, 0:160].astype(float)
img = 0.55 + 0.25 * xx / 159                       # 左右で明るさが違う紙
img[20:44, 20:26] = 0.1; img[20:26, 20:60] = 0.1    # 「Γ」のような暗い字画
reg = fs.apply(fs.apply(img, "median", 0.2, 0.5), "sk_sauvola", 0.5, 0.5)
fg = fs.apply(reg, "invert_region", 0.5, 0.5)       # 暗い字を前景に
clean = fs.apply(fg, "remove_small", 0.05, 0.5)     # a=0.2 だと 6 px 幅の字画ごと消える(実測)
print("前景画素", int(np.asarray(clean).sum()))     # 344

```

## 裏づけ

- op: `sk_sauvola`(局所 2 値化)、`rotate_image`(傾き)、`remove_small` / `select_shape`(ごみ)、`dilation_rectangle1`(行)
- 例: [`gallery2d_segmentation`](../../examples/gallery2d_segmentation.py)、[`poc_matrix_code_reading`](../../examples/poc_matrix_code_reading.py)、[`gallery2d_region`](../../examples/gallery2d_region.py)
