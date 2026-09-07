---
op: tb_capsule_sdf
dim: 2d
category: typed
in: points
out: volume
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# tb_capsule_sdf — 2D `typed` op

- **データ種**: `points` → `volume`
- **呼び出し**: `fullseye.apply(img, "tb_capsule_sdf", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

線分 ``a``–``b`` を半径 ``radius`` で太らせたカプセルの**厳密**な符号付き距離場。

    ``sdf(p) = ‖p - (a + clamp(((p-a)·(b-a))/‖b-a‖², 0, 1)·(b-a))‖ - radius``。
    線分への最短距離そのものなので**全空間で勾配ノルム 1**(円柱と違い端が丸いぶん、
    角が無く厳密)。リブ・配管・骨・ワイヤ・工具の掃引体積の近似に向く。

    引数と検証(``ValueError``):
    - ``grid``: 最終軸が 3 の float 配列 ``(..., 3)``。
    - ``a`` / ``b``: 芯線の端点(要素数 3)。``a == b`` なら球(``sphere_sdf`` と一致)。
    - ``radius``: 太さ(負は拒否)。

    返り値: ``grid.shape[:-1]`` の float64。

    使いどころ: 工具の到達性を「工具の掃引体積が部品と交わらないか」で見るとき、工具を
    カプセルで置いて ``sdf_intersect`` の最小値が正かを見る。骨梁・血管・繊維の合成にも。

2-D 進化レジストリへ橋渡しした 3d の op ``capsule_sdf``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。この op に調整点は無く、``a`` も ``b`` も使われない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `capsule_sdf` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [procedural_hand](../../../../examples_3d/procedural_hand.py) — `py -3.11 examples_3d/procedural_hand.py`
- [sdf_csg](../../../../examples_3d/sdf_csg.py) — `py -3.11 examples_3d/sdf_csg.py`

## 型が繋がる次の op(`volume` を入力に取れる)

[identity](../misc/identity.md) · [vol_gaussian](../3d/vol_gaussian.md) · [vol_median](../3d/vol_median.md) · [vol_erode](../3d/vol_erode.md) · [vol_dilate](../3d/vol_dilate.md) · [vol_threshold](../3d/vol_threshold.md) · [vol_reg_dilate](../3d/vol_reg_dilate.md) · [vol_reg_erode](../3d/vol_reg_erode.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
