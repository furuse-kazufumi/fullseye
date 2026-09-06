---
op: sobel3d
dim: 3d
category: feature
in: voxel
out: gradient
gpu: true
examples: [diff_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# sobel3d — 3D `feature` op

- **データ種**: `voxel` → `gradient`
- **呼び出し**: `import match3d; match3d.sobel3d(vol, device='cpu')` (または `ops3d.get("sobel3d")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

3D 勾配 (gz,gy,gx)。導関数[-1,0,1]×平滑[1,2,1] の分離 conv3d。

vol は numpy でも torch tensor(GPU 上でも可)でも受ける(scene_flow 等の device 常駐用)。

返り値は **torch tensor 3 本**(numpy ではない)、各 ``(1,1,D,H,W)`` float32、``device`` 上。
``gz`` は軸 0 方向、``gy`` は軸 1、``gx`` は軸 2 の微分(入力が (D,H,W) なら (depth,row,col)
順)。numpy に戻すなら ``g[0, 0].cpu().numpy()``。
利得: 微分 [-1,0,1] (傾き 1 で 2)× 他 2 軸の平滑 [1,2,1] (各 4)で **真の勾配の 32 倍**が出る
(正規化しない)。真の値が要るなら 32 で割る(``curvature_maps`` / ``scene_flow_lk`` は内部で
割っている。``hessian3d`` は利得 1 なので混ぜるときに注意)。
端は replicate padding(境界で偽のエッジを作らない)。tensor 入力が 3-D なら batch 次元を
足し、5-D ならそのまま使う。dtype は float32 に落とす。
後段: ``curvature_maps`` / ``match_shape_3d`` の単位勾配、``hough_plane_3d`` の法線。
方向の要らないエッジ強度なら ``morph_gradient3d`` も代替。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [diff_features](../../../../examples_3d/diff_features.py) — `py -3.11 examples_3d/diff_features.py`

## 型が繋がる次の op(`gradient` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`feature`)

[hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md) · [vol_frangi](vol_frangi.md) · [vol_sato](vol_sato.md) · [vol_hessian_blobness](vol_hessian_blobness.md) · [vol_gradient_magnitude](vol_gradient_magnitude.md) · [vol_local_maxima](vol_local_maxima.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
