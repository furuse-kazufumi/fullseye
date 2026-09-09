---
op: mean_reprojection_error
dim: 3d
category: bundle_adjust
in: pose × points
out: measurement
examples: [bundle_adjust]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# mean_reprojection_error — 3D `bundle_adjust` op

- **データ種**: `pose × points` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.mean_reprojection_error(cameras, points, obs_cam, obs_pt, obs_uv, K)` (実装を直接呼ぶなら `import bundle3d; bundle3d.mean_reprojection_error(cameras, points, obs_cam, obs_pt, obs_uv, K)`、台帳から引くなら `ops3d.get("mean_reprojection_error")`)

## 使い方

再投影 RMS 誤差(ピクセル)。

全観測 k について ``project(points[obs_pt[k]], cameras[obs_cam[k]])`` と ``obs_uv[k]`` の差
(du, dv) を取り、``sqrt(mean_k(du² + dv²))`` = 観測ごとの再投影距離の 2 乗平均平方根を float で
返す(実装は ``r.reshape(-1,2)**2 * 2`` の平均の平方根で、同じ量)。単位は ``obs_uv`` と K に
従うピクセル。

- ``cameras``: (nc,6) の ``[rvec(3) | t(3)]``(``X_cam = R X + t``)。
- ``points``: (m,3) の 3D 点。
- ``obs_cam`` / ``obs_pt``: 各観測のカメラ添字・点添字(int)。``obs_uv``: (K,2) の観測画素。
- ``K``: 全カメラ共通の (3,3) 内部行列。

``bundle_adjust`` の返り値 ``rmse`` と同じ計算で、最適化前後の比較に使う。観測が 0 件だと空の
平均で NaN になる(長さの検証は ``bundle_adjust`` 側にあり、この関数単体では行わない)。
カメラ後方の点も ``project`` がそのまま射影するので、可視性は呼び出し側で保証する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bundle_adjust](../../../../examples_3d/bundle_adjust.py) — `py -3.11 examples_3d/bundle_adjust.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`bundle_adjust`)

[bundle_adjust](bundle_adjust.md) · [project](project.md)

---
*Provenance: bundle3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
