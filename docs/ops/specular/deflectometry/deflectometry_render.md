---
op: deflectometry_render
dim: specular
category: deflectometry
in: image2d
out: images
examples: [poc_phase_measuring_deflectometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# deflectometry_render — SPECULAR `deflectometry` op

- **データ種**: `image2d` → `images`
- **呼び出し**: `import fullseye as fs; fs.ledger.deflectometry_render(height, rig=None, period_mm=10.0, n_steps=4, direction='x', kind='fringe', slope_x=None, slope_y=None, diffuse_fraction=0.0, scatter_rad=0.0, back_thickness_mm=None, refractive_index=1.52, focus='surface', aperture_samples=None, noise_sigma=0.0, bits=None, seed=0)` (実装を直接呼ぶなら `import deflectometry; deflectometry.deflectometry_render(height, rig=None, period_mm=10.0, n_steps=4, direction='x', kind='fringe', slope_x=None, slope_y=None, diffuse_fraction=0.0, scatter_rad=0.0, back_thickness_mm=None, refractive_index=1.52, focus='surface', aperture_samples=None, noise_sigma=0.0, bits=None, seed=0)`、台帳から引くなら `opsspecular.get("deflectometry_render")`)

## 使い方

高さ場 → カメラが撮る「画面の鏡像」(順方向のシミュレーション)。→ 画像のリスト(各 (H, W)、[0, 1])。

``height`` (H, W) [mm] は ``rig`` の視野(一辺 ``field_mm``、格子間隔 field / (W − 1))に張った面の高さ。
カメラの画像も (H, W) で、視野の四隅が収まる焦点距離を選ぶ(画素と面の格子は斜めから見るので
1 対 1 ではない —— `deflectometry_phase_to_slope` が投影して読み直す)。各画素の視線を面に当て
(z = h の交点を反復で)、法線で鏡面反射して(`match3d.reflect`)画面に当て、画面の輝度
(`deflectometry_screen_pattern` と同じ式)を読む。``kind="fringe"`` なら ``n_steps`` 枚、
それ以外は 1 枚。

傾きは ``slope_x`` = ∂h/∂x、``slope_y`` = ∂h/∂y を渡せば解析値を使い(真値を厳密にするため)、
省略すると ``height`` の中心差分。

物理の効果(どれも既定は「理想の鏡」):
  * ``diffuse_fraction`` = k_d ∈ [0, 1): 面の拡散成分。I = (1 − k_d)·鏡面 + k_d·画面の平均輝度。
    縞の振幅が (1 − k_d) 倍に落ち、位相の雑音は 1 / (1 − k_d) 倍になる(ざらついた塗装)。
  * ``scatter_rad``: 鏡面ローブの広がり(面の法線の標準偏差 [rad])。反射光は 2 倍広がり、画面上で
    σ = 2·scatter·(面から画面の距離)のガウスで縞がぼける → 振幅 exp(−2π²σ²/周期²)。
  * ``back_thickness_mm`` / ``refractive_index``: 透明板(カバーガラス)の裏面反射(屈折率は数か材料表の名前 ——
    名前なら d 線 587.56 nm の n)。表で屈折
    (`glassmirror.refract_rays`)→ 平らな裏面で反射 → 表から出る光が、ずれた画面の点を映す。
    重みは Fresnel(`glassmirror.fresnel_dielectric`)。カメラの露出は表と裏の和で正規化する。
  * ``focus``: ``"surface"``(面にピント)/ ``"screen"``(画面の虚像 = 主光線に沿って L + d にピント)/
    0〜1 の数(その間の比 D_f = L + α d)。開口 ``rig["aperture_mm"]`` = A の薄レンズで、距離 D の物体の
    錯乱円の直径は A·|D − D_f| / D_f。面にピント(α = 0)で開口積分を指定しないときは、面の 1 点から出た
    光が画面上で直径 A·d/L の円板に広がるだけなので、縞に一様円板の MTF 2 J1(πc/p) / (πc/p) を掛ける
    (閉形式、負なら位相が反転)。それ以外は**開口積分**: 開口上の ``aperture_samples`` 点(既定 16、
    Vogel の螺旋)から、主光線上のピントの点へ向かう光線を 1 本ずつ面に当てて反射させ、画面の輝度を
    平均する —— 画面側のぼけ(縞の振幅)と面側のぼけ(面の傾きの平均 = 凹みがぼける)が同時に出る。
    ★2026-10-15: 初版は面側のぼけを「画像を円板で畳み込む」近似にしていて、画面にピントを合わせても
    縞の振幅が 0.59 倍に落ちた(縞そのものまでぼかしていた)。画面に合っていれば縞はくっきりで、ぼける
    のは縞を曲げる面の傾きのほう —— 開口積分に直した。
  * ``noise_sigma``(画素の加法ガウス雑音、[0, 1] の単位)と ``bits``(量子化、例 8)。``seed`` で再現。

画面の外に当たる画素は 0(黒)。``fringe.modulation`` で低い変調の画素を除くこと。

Raises: ``ValueError`` —— ``height`` が 2-D の有限な配列でない(2 × 2 未満も)、傾きの形が違う・
有限でない、周期が正でない、N < 3、方向・kind・focus が不正、k_d が [0, 1) の外、散乱が負、
板厚が正でない、屈折率が 1 以下、雑音が負、bits が 1〜16 の整数でない、aperture_samples が
1〜256 の整数でも None でもない、rig が不正。

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_phase_measuring_deflectometry](../../../../examples/poc_phase_measuring_deflectometry.py) — `py -3.11 examples/poc_phase_measuring_deflectometry.py`

## 型が繋がる次の op(`images` を入力に取れる)

[photometric_stereo_robust](../photometric/photometric_stereo_robust.md) · [photometric_residual](../photometric/photometric_residual.md)

## 同カテゴリ(`deflectometry`)

[deflectometry_rig](deflectometry_rig.md) · [deflectometry_screen_pattern](deflectometry_screen_pattern.md) · [deflectometry_phase_to_slope](deflectometry_phase_to_slope.md) · [slope_to_curvature](slope_to_curvature.md) · [deflectometry_sensitivity](deflectometry_sensitivity.md)

---
*Provenance: deflectometry.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
