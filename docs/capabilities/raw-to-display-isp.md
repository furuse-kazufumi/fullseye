---
id: raw-to-display-isp
title: Bayer の生フレームを、段ごとに説明できる式で表示画像にする
title_en: Turn a Bayer raw frame into a display image, one explainable stage at a time
category: 光と色
ops: [raw_black_level, raw_dead_pixel_mask, raw_dead_pixel_correct, lens_shading_gain, lens_shading_correct, awb_gains, raw_apply_gains, rgb_apply_gains, raw_demosaic_bilinear, color_correction_matrix, hue_saturation, brightness_contrast, cfa_to_rgb, gamma]
examples: [raw_to_display_isp]
version: 0.2.1
---

# Bayer の生フレームを、段ごとに説明できる式で表示画像にする

## できること

カメラの ISP(Image Signal Processor)が RAW から RGB を作るまでの典型段を、**全部閉じた式**で持っています(gfx2d 台帳の `isp`)。黒レベル `raw_black_level`(台座を引いて白を 1 に)→ 欠陥画素 `raw_dead_pixel_mask` / `raw_dead_pixel_correct`(同色 8 近傍の全部から同じ向きに閾値以上ずれた画素を中央値で置く)→ 周辺減光 `lens_shading_gain` / `lens_shading_correct`(白い板を撮った flat から色ごとの利得地図)→ ホワイトバランス `awb_gains`(gray-world / white-patch)を `raw_apply_gains`(モザイク側)か `rgb_apply_gains` で → デモザイク `raw_demosaic_bilinear`(NumPy だけの双線形。OpenCV があれば `cfa_to_rgb` も)→ 色補正行列 `color_correction_matrix`(行和 1 に正規化して白を白のまま)→ `hue_saturation`(BT.601 の色差を回す・伸ばす)→ `brightness_contrast`(中灰を軸に)。`gamma` は既存 op。

段ごとに「何をしたか」を言えるのが要点で、検査用途では学習 ISP の綺麗さより**説明可能性と再現性**が要ります。Bayer 配列は `RGGB / BGGR / GRBG / GBRG` を `pattern` で渡します。

## What it does

The classic ISP stages, each a closed form you can state: black level, dead-pixel detection/correction (a pixel that departs from all eight same-colour neighbours in the same direction), lens-shading gain from a flat field (per colour channel), white-balance gains (gray-world / white-patch) applied on the mosaic or on RGB, a NumPy-only bilinear demosaic (exact on affine fields, phase-preserving mirrored border), a row-normalised colour-correction matrix (white stays white), hue/saturation in BT.601 YCbCr, and brightness/contrast about mid-grey. For inspection work, explainability and repeatability matter more than the polish of a learned ISP.

## 向くところ / 向かないところ

**向く**: 検査カメラの RAW を自前で現像したい場面、段ごとの影響を切り分けたい場面(減光は LSC が、かぶりは AWB が消したと言える)、合成データで RAW の劣化を植えて検査アルゴリズムの頑健性を測る場面。

**向かない**: ★デモザイクは**双線形だけ**です。色の段差でジッパーが出ます(例で最大 6e-2 を隠さず印字)。★`awb_gains` は仮定(場面の平均が灰 / 最も明るい面が白)が外れた場面では**真の照明の逆にならない**(例で数字を並べて示す)。白い板を撮るか、灰の基準を使ってください。★雑音除去・エッジ強調・偽色抑制・トーンマップは**ここには無い**(既存の `bilateral` / `sk_nlm` / `unsharp` / `tonemap_*` を使う)。★カラー偏光センサ、非 Bayer(X-Trans 等)は未対応。★CCM の推定(カラーチャートからの最小二乗)は含みません —— 行列は与える。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

raw = np.load("frame_rggb.npy")                        # (H, W) in [0, 1]
flat = np.load("flat_rggb.npy")                        # 白い板を同じレンズで
x = fs.raw_black_level(raw, 0.04, white=0.92, pattern="RGGB")
x = fs.raw_dead_pixel_correct(x, 0.15)
x = fs.lens_shading_correct(x, fs.lens_shading_gain(fs.raw_black_level(flat, 0.04, white=0.92), pattern="RGGB"))
gains = fs.awb_gains(fs.raw_demosaic_bilinear(x, "RGGB"), "white_patch")   # or "gray_world"
rgb = fs.raw_demosaic_bilinear(fs.raw_apply_gains(x, gains, "RGGB"), "RGGB")
rgb = fs.color_correction_matrix(rgb, np.array([[1.5, -0.35, -0.15], [-0.2, 1.4, -0.2], [0.05, -0.45, 1.4]]))
rgb = fs.brightness_contrast(fs.hue_saturation(rgb, 0.0, 1.1), 0.0, 1.05)
print(rgb.shape, rgb.min(), rgb.max())                 # (H, W, 3) 0.0 1.0
```

## 裏づけ

- op: gfx2d `isp` 12 本(2026-09-18)+ 既存 `cfa_to_rgb`(OpenCV 橋)/ `gamma`
- 例: [`raw_to_display_isp`](../../examples/raw_to_display_isp.py)(植えた台座・減光・かぶり・欠陥 12 画素を順に外し、デモザイク後の 95 % 点誤差 5e-4、欠陥 12/12、AWB の仮定外れを数字で)
- 試験: `tests/test_gfx2d.py`(黒レベルの厳密写像 / 欠陥の検出と縁は欠陥でない / flat の平坦化 / gray-world と white-patch の統計一致 / CCM の恒等と白 / 色相往復と彩度 0 = 輝度 / 中灰不変 / 4 配列の双線形が 1 次平面で厳密 / 端から端)
- 出典: 段の顔ぶれと DPC の規則は openISP(cruxopen、MIT)を一次情報で確認して定義から再実装。gray-world は Buchsbaum (1980)、YCbCr は ITU-R BT.601。`docs/REFERENCES.md`
