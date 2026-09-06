---
op: match_hough_3d
dim: 3d
category: match_localize
in: voxel × voxel
out: position
gpu: true
examples: [matching_localize]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# match_hough_3d — 3D `match_localize` op

- **データ種**: `voxel × voxel` → `position`
- **呼び出し**: `import match3d; match3d.match_hough_3d(scene, template, device='cpu', ndir=26, mc=0.05, topk=1, nms=3, subvoxel=True)` (または `ops3d.get("match_hough_3d")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

generalized Hough 3D(Ballard R-table 投票)。voxel × Hough 列。

GHT を **向きビンごとの相関の総和** として GPU ネイティブに定式化:
accumulator A(t) = Σ_bin ( scene_bin ⋆ template_bin )。各エッジが勾配方向に応じて投票し、
欠けたエッジはピークを下げるだけ(**遮蔽・クラッタに頑健**)。shape-based(連続内積の単一解)
と違い **投票 accumulator を返し、NMS で複数ピーク = 複数インスタンス** を取れるのが差別化。
返り値 (topk,4) の [votes, d, h, w] (votes 降順)。

手順: 両 volume の単位勾配(``mc`` は ``sobel3d`` の生出力への閾値)を ``ndir`` 本の参照方向の
うち最も近いものに量子化し、方向ビンごとに「scene のそのビンの 2 値場 ⋆ テンプレのそのビンの
2 値場」を conv3d で足し合わせる。テンプレの有効エッジ数で割るので votes は **[0, 1]**、1 で
全エッジが一致。
- ``ndir``: 26 以下は 26 近傍方向のリストの先頭 ``ndir`` 本(26 未満は方向が偏る)、27 以上は
fibonacci 球で一様。方向が粗いほど回転に寛容だが偽ピークも増える。
- 返り値 ``(topk, 4)`` の各行 ``[votes, z, y, x]``、votes 降順。座標は **テンプレ中心 (T//2)**
の scene 座標、``subvoxel=True`` なら ±2 近傍重心。
- ``nms``: ピークを取るたびに ``±nms`` voxel の立方体を −1 で潰してから次を探す。近接する
複数インスタンスは ``nms`` を小さく。
- テンプレにエッジが無ければ全 0 の ``(topk,4)``。テンプレが完全に収まらない位置は 0。
後段: 各ピークを ``refine_translation_lk`` / ``refine_peak_newton`` で精緻化。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [matching_localize](../../../../examples_3d/matching_localize.py) — `py -3.11 examples_3d/matching_localize.py`

## 型が繋がる次の op(`position` を入力に取れる)

[refine_peak_newton](../refine/refine_peak_newton.md) · [refine_translation_lk](../refine/refine_translation_lk.md) · [refine_lm](../refine/refine_lm.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`match_localize`)

[match_shape_3d](match_shape_3d.md) · [match_chamfer_3d](match_chamfer_3d.md) · [match_curvature_3d](match_curvature_3d.md) · [match_mip_2d](match_mip_2d.md) · [match_points_ncc](match_points_ncc.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
