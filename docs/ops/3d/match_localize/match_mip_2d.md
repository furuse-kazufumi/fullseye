---
op: match_mip_2d
dim: 3d
category: match_localize
in: voxel × voxel
out: position
gpu: true
examples: [matching_localize]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# match_mip_2d — 3D `match_localize` op

- **データ種**: `voxel × voxel` → `position`
- **呼び出し**: `import fullseye as fs; fs.ledger.match_mip_2d(scene_vol, model_vol, device='cpu')` (実装を直接呼ぶなら `import match3d; match3d.match_mip_2d(scene_vol, model_vol, device='cpu')`、台帳から引くなら `ops3d.get("match_mip_2d")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

MIP 投影 → 2D NCC(構造=voxel → 2D × 手法=NCC、変換=直交 MIP)。

3 直交方向の最大値投影で 3 枚の 2D 問題に落とし、既存の 2D NCC で定位 → 3 枚から 3D 座標を
冗長推定。全 3D NCC より安く coarse alignment に。回転が無い平行移動探索向き。

手順: ``voxel_to_mips`` で scene・model とも 3 枚の MIP を作り、各投影で model MIP の
``> 5%·max`` の bbox を切り出してテンプレにし、``accel_match.ncc_locate_batch``(2D NCC、
テンプレ中心規約)で位置を取る。軸 0 を潰した投影は (y,x)、軸 1 は (z,x)、軸 2 は (z,y) を
与えるので各座標は 2 枚から得られ、その平均を返す。
返り値 ``(3,)`` float64 の ``[z, y, x]``(整数 NCC 位置の平均なので .5 刻み)。score は返さない。
- 位置は **切り出した bbox テンプレの中心**が scene MIP のどこに載るか。model volume の
中心ではない。
- model MIP が全 0 の投影は飛ばし、ある座標が 1 枚からも得られなければ 0.0 になる(例外は
出ない)。
- MIP は重なりで奥行き情報を失うので、複数物体・クラッタには弱い。
後段: この粗位置を ``refine_translation_lk`` / ``refine_lm`` に渡す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [matching_localize](../../../../examples_3d/matching_localize.py) — `py -3.11 examples_3d/matching_localize.py`

## 型が繋がる次の op(`position` を入力に取れる)

[refine_peak_newton](../refine/refine_peak_newton.md) · [refine_translation_lk](../refine/refine_translation_lk.md) · [refine_lm](../refine/refine_lm.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`match_localize`)

[match_shape_3d](match_shape_3d.md) · [match_chamfer_3d](match_chamfer_3d.md) · [match_curvature_3d](match_curvature_3d.md) · [match_hough_3d](match_hough_3d.md) · [match_points_ncc](match_points_ncc.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
