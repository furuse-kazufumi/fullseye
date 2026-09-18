---
id: polarization-imaging
title: 偏光カメラの生フレームを Stokes・DoLP・Mueller に読む
title_en: Read a polarisation camera's raw frame into Stokes, DoLP and Mueller
category: 光と色
ops: [polarization_demosaic, polarization_stokes, polarization_dolp_map, polarization_separate, stokes_analyze, mueller_from_intensities, mueller_checks, mueller_element, mueller_apply]
examples: [polarization_camera_pipeline, poc_polarization_specular]
version: 0.2.1
---

# 偏光カメラの生フレームを Stokes・DoLP・Mueller に読む

## できること

偏光カメラ(Sony IMX250MZR 系: FLIR BFS-U3-51S5P、LUCID TRI050S-P など)は 2×2 の画素ブロックに 0/45/90/135 度の偏光子を並べた**モザイク**を 1 枚で出します。`polarization_demosaic` がそれを 4 枚(0/45/90/135)に戻し(双線形。1 次の場は厳密に戻り、縁はモザイクを鏡映して位相を保つ)、そのまま `polarization_stokes` / `polarization_dolp_map` / `polarization_separate` に渡せます(角度の既定が一致しているので引数無しで繋がる)。センサの配列が違えば `layout=((a00, a01), (a10, a11))` で渡します。

試料の **Mueller 行列**は、既知の生成器(PSG)と検光子(PSA)の列で撮った強度から `mueller_from_intensities` が最小二乗で取り戻します。強度は 16 成分に線形なので観測行列 `outer(a_i, g_i)` を積んで解くだけです。★設計が S3 を見られないとき(偏光板だけ、階数 9)は**階数を言って断り**、擬似逆行列のもっともらしい答えを返しません。画像ごと(N, H, W)に渡せば画素ごとに解けます。

取り戻した行列が**物理的**か(Cloude の coherency 行列が半正定値)、**純粋**か(脱偏光しない)、どれだけ脱偏光しているか(Gil–Bernabeu 指数)、**受動**か(透過率 ≤ 1)は `mueller_checks` が一度に返します。数値は固有値ごと載せるので、「どれだけ非物理か」まで見えます。

## What it does

Turn a polarisation camera's mosaic (a 2×2 block of 0/45/90/135° analysers, Sony IMX250MZR family) into four full-resolution images with `polarization_demosaic` (bilinear, exact on affine fields, phase-preserving mirrored border) that chain straight into `polarization_stokes` / `polarization_dolp_map`. Recover a sample's Mueller matrix from intensities measured through known generator/analyser states with `mueller_from_intensities` (linear least squares on `outer(a_i, g_i)`; refuses rank-deficient designs with the rank instead of returning a pseudo-inverse guess). Check any 4×4 matrix with `mueller_checks`: Cloude coherency eigenvalues (physical), purity, the Gil–Bernabeu depolarisation index and passivity.

## 向くところ / 向かないところ

**向く**: 偏光カメラの生フレームの前処理、鏡面反射と拡散の分離(`polarization_separate`)、偏光素子や試料の Mueller 行列の計測と健全性確認、光弾性・応力可視化の前段。

**向かない**: ★カラー偏光センサ(IMX250MYR、4×4 ブロック)は未対応です。★demosaic は**双線形**だけで、エッジ適応や勾配法はありません(輪郭では 1 画素幅のにじみが出ます)。★`mueller_from_intensities` は生成器・検光子が**正確に既知**である前提で、素子の誤差は結果にそのまま乗ります(較正は別の問題)。★`mueller_checks` の `tol` は測定雑音の水準で置いてください。雑音つきで回復した行列は最小固有値が僅かに負に出るのが普通で、tol を勘で小さくすると「非物理」に化けます(例で実演)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

raw = np.load("polarcam_frame.npy")                     # (H, W) のモザイク、値は [0, 1]
sweep = fs.polarization_demosaic(raw)                   # (4, H, W): I_0, I_45, I_90, I_135
dolp = fs.polarization_dolp_map(sweep)                  # 画素ごとの直線偏光度
print(fs.stokes_analyze(fs.polarization_stokes(sweep)))  # 場全体の Stokes → dop / azimuth

# Mueller: 既知の PSG / PSA(各 N 個の 4x4)で撮った N 個の強度から
M = fs.mueller_from_intensities(intensities, psg, psa)  # (4, 4)。階数 < 16 なら ValueError
print(fs.mueller_checks(M, tol=1e-3))                   # physical / pure / depolarization_index / passive
```

## 裏づけ

- op: `polarization_demosaic` / `mueller_from_intensities` / `mueller_checks`(2026-09-18、optics 台帳 `polarization`)、既存の `polarization_stokes` / `polarization_dolp_map` / `polarization_separate` / `stokes_analyze` / `mueller_element` / `mueller_apply`
- 例: [`polarization_camera_pipeline`](../../examples/polarization_camera_pipeline.py)(合成の Stokes 場 → モザイク → 4 枚 → DoLP、Mueller の回復と階数の拒否、物理性)、[`poc_polarization_specular`](../../examples/poc_polarization_specular.py)(偏光で鏡面反射を分ける)
- 試験: `tests/test_optics.py`(1 次の場で厳密、配列の読み替え、sweep op との接続、既知 M の回復 1e-10、階数 9 の拒否、全素子の物理性、非物理と利得の判定)
- 相互検証(2026-09-18、`tools/diff_polarization_external.py` / `tests/test_polarization_external_diff.py`、外部 3 本は任意依存で無ければ skip): 偏光板・リターダ・QWP/HWP の Mueller は pypolar / py-pol / polanalyser と **1e-16 で一致**、Mueller 最小二乗は polanalyser と 5e-16、DoLP 地図は 9e-16、demosaic の内側は 16 bit 量子化の範囲。差が出た所は全部**規約差**: 回転子は能動(+θ)で相手の受動 R(θ) = こちらの −θ / Jones は規約が library ごとに違うので Mueller に写して比較(fullseye の Stokes 写像経由で pypolar の Mueller 素子と 1e-15)/ 楕円率は偏光成分で正規化(pypolar は S0)/ demosaic の縁。不具合は見つからなかった。
- 出典: 配列の規約と「4 枚の Bayer 面」の読みは Polanalyser(前田、MIT)、観測行列は Chipman *Handbook of Optics* ch. 15、物理性は Cloude (1986) / Gil (2007)、脱偏光指数は Gil & Bernabeu (1986)、判定の顔ぶれは py-pol(MIT)。いずれも定義から再実装(`docs/REFERENCES.md`)
