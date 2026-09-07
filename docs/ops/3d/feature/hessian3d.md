---
op: hessian3d
dim: 3d
category: feature
in: voxel
out: hessian
gpu: true
examples: [diff_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# hessian3d — 3D `feature` op

- **データ種**: `voxel` → `hessian`
- **呼び出し**: `import fullseye as fs; fs.ledger.hessian3d(vol, device='cpu')` (実装を直接呼ぶなら `import match3d; match3d.hessian3d(vol, device='cpu')`、台帳から引くなら `ops3d.get("hessian3d")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

3D Hessian の 6 独立成分 (fzz,fyy,fxx,fzy,fzx,fyx)。分離 conv3d(2 階/1 階×平滑)。

カーネル: 2 階 [1,−2,1] (利得 1)、1 階 [−0.5,0,0.5] (利得 1)、残りの軸は [1,2,1]/4 の平滑
(利得 1)。対角成分は「その軸の 2 階 × 他 2 軸の平滑」、交差成分は「2 軸の 1 階 × 残り軸の
平滑」。**単位は 1/voxel² の真の値**(``sobel3d`` の 32 倍利得とは違う)。端は replicate。
返り値は **list の torch tensor 6 本**、各 ``(D,H,W)`` float32、``device`` 上、順は
(zz, yy, xx, zy, zx, yx)(軸 0=z, 1=y, 2=x)。numpy が要れば ``.cpu().numpy()``。入力は
numpy 相当(float32 に変換)。
用途: ``curvature_maps`` の主曲率(``sobel3d`` と組で使う)、blob/管状構造の検出。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [diff_features](../../../../examples_3d/diff_features.py) — `py -3.11 examples_3d/diff_features.py`

## 型が繋がる次の op(`hessian` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md) · [vol_frangi](vol_frangi.md) · [vol_sato](vol_sato.md) · [vol_hessian_blobness](vol_hessian_blobness.md) · [vol_gradient_magnitude](vol_gradient_magnitude.md) · [vol_local_maxima](vol_local_maxima.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
