---
id: estimate-lens-distortion
title: 本来まっすぐな線から歪み係数を推定する(plumb-line、チェッカー不要)
title_en: Estimate lens distortion coefficients from straight lines (plumb-line, no board)
category: 測る
ops: [estimate_distortion, undistort_image, distort_points, undistort_points]
examples: [estimate_lens_distortion]
version: 0.2.1
---

# 本来まっすぐな線から歪み係数を推定する(plumb-line、チェッカー不要)

## できること

`undistort_image(image, K, dist)` は歪み係数 `dist` が**与えられている**前提でした。`estimate_distortion(lines, K)` はその上流 —— 係数を**測る**側です。本来まっすぐな線(印刷された直線・建物のエッジ・定規)がレンズで曲がった点列だけから、Brown–Conrady 係数 `[k1, k2, p1, p2, k3]` を推定します。**対応点もチェッカーボードも既知の間隔も要りません** —— 各線がまっすぐだと分かっていればよい(Discorpy が使う線パターンの考え方を、このライブラリの `(x, y)` 規約で)。推定した `dist` は `undistort_image` にそのまま渡せます。

原理は plumb-line 法(Brown 1971、Devernay–Faugeras 2001)です。係数を仮に置いて各線を補正し、補正後の点が「本来の直線」からどれだけ広がるか(直線当てはめの残差=第 2 特異値)を全線で合計し、それを最小化する係数を探します。まっすぐであるべき線がまっすぐになる係数が答え。順・逆モデルは `undistort_points` そのものを呼びます(Brown–Conrady の実装はこのモジュールに 1 つだけ、別コピーを持ちません)。`K` の主点が歪み中心で、これは固定します(この方法は中心と接線 `p1, p2` を分離できない)。放射の次数は `radial=1/2/3`、接線は `tangential` で on/off。最適化は SciPy(このパッケージの他の校正リファイナと同じ)。

## What it does

The upstream of `undistort_image`: it *measures* the Brown–Conrady coefficients instead of taking them as given. From point lists sampled along features that are straight in the world (`lines`, each `(N_i, 2)` in `(x=col, y=row)`) plus the intrinsics `K`, `estimate_distortion` returns `dist = [k1, k2, p1, p2, k3]` ready for `undistort_image` / `undistort_points`. It is the plumb-line method (Brown 1971; Devernay–Faugeras 2001): minimize, over the coefficients, the summed perpendicular scatter of the *undistorted* lines, so lines that are straight in the world become straight once distortion is removed. No correspondences, no calibration board, no known spacing — only that each line is straight (the line-pattern idea Discorpy uses). The principal point of `K` is the distortion centre and is held fixed (the method cannot separate it from `p1, p2`). `radial` in `{1, 2, 3}` frees `k1`; `k1, k2`; or `k1, k2, k3`; `tangential` frees `p1, p2`. On clean synthetic lines the coefficients come back to machine precision; with pixel noise they degrade gracefully. Requires SciPy. fail-closed on fewer than two lines or a line with fewer than three points.

## 向くところ / 向かないところ

**向く**: チェッカーボードを撮れない/撮っていない現場で、画に写った直線だけから歪みを求める、既存の写真アーカイブの歪み推定、`undistort_image` に渡す係数を用意する、直線性が要る検査画像の前処理の係数決め。

**向かない**: ★**内部行列 `K` の推定はしません**(焦点距離・主点は与える前提。多視点の平面ターゲットから `K` を出すのは Zhang 法の別 op)。★**主点=歪み中心を推定しません**(固定。1 枚の線群では中心と接線が縮退する)。★魚眼の等距離射影は Brown–Conrady で表せない(別モデル)。★**線が 1 本では効きません**(1 本だと「曲がり」と「傾き」を区別できない —— 向きの違う 2 本以上を、できれば画面いっぱいに)。★雑音・少ない点・高次(`k2, k3`)は誤差が増える(過信せず、線を増やし広く張る)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

# 本来まっすぐな線ごとの点列(x=col, y=row)。実写ではエッジ検出+追跡で拾う。
K = fs.intrinsic_matrix(0.95 * 200, 0.95 * 200, 99.5, 99.5)
true = [-0.24, 0.06, 0.0, 0.0, 0.0]
lines = [fs.distort_points(np.column_stack([np.linspace(12, 188, 40),
                                            np.full(40, y)]), K, true)
         for y in (40, 100, 160)]                    # 水平線を歪ませた例
lines += [fs.distort_points(np.column_stack([np.full(40, x),
                                             np.linspace(12, 188, 40)]), K, true)
          for x in (40, 100, 160)]                    # 向きの違う垂直線も入れる
dist = fs.estimate_distortion(lines, K, radial=2, tangential=False)
straight = fs.undistort_image(img, K, dist)           # 測った係数でそのまま補正
```

## 裏づけ

- 実装: `camera.py`(`estimate_distortion`。plumb-line 直線性コストを `undistort_points` の上で `scipy.optimize.least_squares` で最小化)
- 例: [`estimate_lens_distortion`](../../examples/estimate_lens_distortion.py)(放射・接線の回収、直線性が桁で回復、推定係数での像の往復、雑音での劣化)
- 試験: `tests/test_camera.py`(たる型/糸巻き型の回収 / 接線の回収 / `undistort_image` への接続 / 雑音での素直な劣化 / fail-closed)
- 来歴: Brown 1971(plumb-line 歪み推定)/ Devernay–Faugeras 2001(直線からの歪み補正)/ Discorpy(線パターン・画像ドメイン)—— `docs/REFERENCES.md`
