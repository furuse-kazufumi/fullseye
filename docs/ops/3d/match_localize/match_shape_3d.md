---
op: match_shape_3d
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

# match_shape_3d — 3D `match_localize` op

- **データ種**: `voxel × voxel` → `position`
- **呼び出し**: `import match3d; match3d.match_shape_3d(vol, template, device='cpu', mc=0.05, subvoxel=True)` (または `ops3d.get("match_shape_3d")`)
- **台帳経由の戻り値**: `fullseye.ledger.match_shape_3d(...)` は**宣言 out 型 `position` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.match_shape_3d.raw(...)`、または `match3d.match_shape_3d` を直接呼ぶ。
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

3D 形状ベース(勾配方向)マッチング = 2D shapematch_gpu の voxel 版(「輪郭マッチング」)。

テンプレとシーンの **単位勾配ベクトルの内積和**(Steger 流)。強度/コントラストに不変で、
エッジ/形状で一致を測る。score(pos)=Σ<û_scene(pos+dt), û_model(dt)>/n を 3 成分の conv3d で。

手順: 両 volume に ``sobel3d`` → 大きさ ``mc`` 超の voxel だけ単位ベクトル化(以下は 0)。
テンプレの単位勾配 3 成分をカーネルに、シーンの単位勾配と成分ごとに conv3d して和を取り、
テンプレの有効 voxel 数 ``n`` で割る。score は **[−1, 1]**、1 で完全一致(勾配の向きが全て
揃う)、コントラスト反転で −1。
- ``mc``: ``sobel3d`` の **生出力(真の勾配の 32 倍)** に対する閾値。小さいほど平坦部の
ノイズ勾配が投票に入る。
- 位置: 返り値 ``[score, z, y, x]``(float64 配列)の座標は **テンプレ中心 voxel(index T//2)**
が scene のどこに載るか。テンプレが完全に収まる位置以外は 0 に落とすので、テンプレが scene
より大きいと全 0 のまま index (0,0,0) が返る(例外は出ない)。
- ``subvoxel=True`` で argmax の ±2 近傍の正スコア重心に精緻化(``accel_match._subvoxel_com``)。
後段: ``refine_translation_lk``(corner 規約なので T//2 を引く)/ ``refine_lm``。回転には
不変でない(``match_logpolar_z`` で先に回転を合わせる)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [matching_localize](../../../../examples_3d/matching_localize.py) — `py -3.11 examples_3d/matching_localize.py`

## 型が繋がる次の op(`position` を入力に取れる)

[refine_peak_newton](../refine/refine_peak_newton.md) · [refine_translation_lk](../refine/refine_translation_lk.md) · [refine_lm](../refine/refine_lm.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`match_localize`)

[match_chamfer_3d](match_chamfer_3d.md) · [match_curvature_3d](match_curvature_3d.md) · [match_hough_3d](match_hough_3d.md) · [match_mip_2d](match_mip_2d.md) · [match_points_ncc](match_points_ncc.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
