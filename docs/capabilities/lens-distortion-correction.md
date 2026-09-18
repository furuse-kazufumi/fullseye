---
id: lens-distortion-correction
title: レンズの歪みを画像ごと補正する(たる型・糸巻き型・接線)
title_en: Correct lens distortion over a whole image (barrel, pincushion, tangential)
category: 形にする
ops: [undistort_image, distort_image, distort_points, undistort_points]
examples: [lens_undistort]
version: 0.2.1
---

# レンズの歪みを画像ごと補正する(たる型・糸巻き型・接線)

## できること

広角・魚眼寄りのレンズは直線を曲げます(たる型・糸巻き型)。`undistort_image(image, K, dist)` は Brown–Conrady モデル(`dist = [k1, k2, p1, p2(, k3)]`、OpenCV と同じ並び)で**画像を丸ごと補正**し、曲がった直線をまっすぐに戻します。`distort_image` はその逆で、理想画像から歪んだ画像を作ります(合成テストデータ・レンズの見えの確認)。

要は**後方マッピング**です。補正後(理想)の各画素について、その理想の光線が歪んだ入力のどこに落ちたか(`distort_points`)を求め、そこを双線形で拾う —— だから穴が開きません(Wolberg 1990)。`K` は 3x3 の内部行列で、その主点が歪みの中心。灰色 `(H, W)` でもカラー `(H, W, 3)` でも通り、端はクランプします。点だけを変換したいときは `distort_points` / `undistort_points`(既存)。

## What it does

Whole-image Brown–Conrady undistortion and its inverse, built as a backward map over this repo's own point model plus a bilinear, edge-clamped remap — so a corrected image is hole-free and a synthetic distorted image is exact to the resampling. `dist` is `[k1, k2, p1, p2(, k3)]` (OpenCV order); `K`'s principal point is the distortion centre. Grey or colour, in `[0, 1]`. On a smooth scene the round trip `distort_image` → `undistort_image` recovers the interior to a few times 1e-4 (only the double bilinear blur remains); the remap field equals `distort_points` to machine precision.

## 向くところ / 向かないところ

**向く**: 係数が分かっているレンズの歪み補正(計測・キャリブ後の絵作り)、直線性を要する検査画像の前処理、歪みを付けた合成データ作り、点補正では足りず画像全体を必要とする場面。

**向かない**: ★歪み係数の**推定**はしません(格子や直線パターンから `k1, k2 …` を求めるのは Discorpy 流の別 op。ここは係数が与えられている前提)。★魚眼の等距離射影(`r = fθ`)は Brown–Conrady では表せない —— 別モデルが要る。★縁の外側は外挿(クランプ)なので、大きな補正では枠が伸びる。★二重にリサンプルすると細い線はボケる(補正は 1 回で。合成→補正の往復はテスト用)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

img = fs.read_image("wide_angle.png")          # 曲がった直線を含む写真
h, w = img.shape[:2]
K = fs.intrinsic_matrix(0.9 * w, 0.9 * w, (w - 1) / 2, (h - 1) / 2)
dist = [-0.28, 0.09, 0.0, 0.0, 0.0]            # たる型(k1<0)を戻す係数
straight = fs.undistort_image(img, K, dist)    # 直線がまっすぐに
```

## 裏づけ

- 実装: `camera.py`(`undistort_image` / `distort_image`、点モデル `distort_points` と `deformreg.warp_by_field` の合成)
- 例: [`lens_undistort`](../../examples/lens_undistort.py)
- 試験: `tests/test_camera.py`(滑らか像で往復が内部一致 / remap 場が `distort_points` と厳密一致 / カラー / 歪みゼロは恒等)
- 来歴: Brown 1971(Brown–Conrady)/ Wolberg 1990(穴の開かない後方マップ)/ Discorpy(画像ドメイン補正)—— `docs/REFERENCES.md`
