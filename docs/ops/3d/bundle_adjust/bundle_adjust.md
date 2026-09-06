---
op: bundle_adjust
dim: 3d
category: bundle_adjust
in: pose × points
out: table
examples: [bundle_adjust]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# bundle_adjust — 3D `bundle_adjust` op

- **データ種**: `pose × points` → `table`
- **呼び出し**: `import bundle3d; bundle3d.bundle_adjust(cameras, points, obs_cam, obs_pt, obs_uv, K, fix_first=True, max_iter=200)` (または `ops3d.get("bundle_adjust")`)

## 使い方

再投影誤差最小でカメラ姿勢と 3D 点を同時最適化。→ dict{cameras, points, rmse, cost}。

cameras (nc,6)=[rvec(3)|t(3)] の初期値、points (m,3) の初期値、観測 obs_cam/obs_pt/obs_uv。
fix_first=True で先頭カメラを [I|0] 相当(初期値のまま)に固定し gauge を除く。

**scale gauge**: 再投影誤差は「カメラ 0 の中心を基準にシーン全体を相似拡大」しても
厳密に変わらないので、それだけでは解の scale が定まらず LM が任意の倍率へ滑る
(実測 ×0.7〜×213、rmse≈0 のまま)。本関数は **構造のカメラ 0 中心からの RMS 距離
(``scale_anchor``)を初期値に保つ残差** ``w·(rms/rms0 − 1)`` を 1 本足して固定する。
再投影コストは scale 方向に勾配ゼロなので、この残差は最適解で厳密に 0 になり、
返る scale は初期構造のそれと一致する(基線長 ``‖t₁‖`` で固定するより、点数で
平均される分だけ初期摂動の影響が小さい)。初期構造が退化(全点がカメラ 0 中心に
一致)していれば拘束は掛けない。返り dict の ``scale_anchor`` に採用した RMS 距離を載せる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bundle_adjust](../../../../examples_3d/bundle_adjust.py) — `py -3.11 examples_3d/bundle_adjust.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`bundle_adjust`)

[mean_reprojection_error](mean_reprojection_error.md) · [project](project.md)

---
*Provenance: bundle3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
