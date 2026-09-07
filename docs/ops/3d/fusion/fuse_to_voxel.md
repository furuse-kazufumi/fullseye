---
op: fuse_to_voxel
dim: 3d
category: fusion
in: any
out: voxel
gpu: true
examples: [transforms_repr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fuse_to_voxel — 3D `fusion` op

- **データ種**: `any` → `voxel`
- **呼び出し**: `import fuse3d; fuse3d.fuse_to_voxel(items, size=64, bounds=None, device='cpu', smooth=0.8)` (または `ops3d.get("fuse_to_voxel")`)
- **台帳経由の戻り値**: `fullseye.ledger.fuse_to_voxel(...)` は**宣言 out 型 `voxel` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.fuse_to_voxel.raw(...)`、または `fuse3d.fuse_to_voxel` を直接呼ぶ。
  - 本体の返り: `(voxel, bounds)`
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

複数構造を共通密度 voxel へ融合(TRIZ 統合)。items=[(data,kind,params_dict), ...]。

mesh(topology)+ points(sample)+ depth(観測)等の相補的な構造を 1 表現に。返り値 (voxel, bounds)。

手順: 各 ``(data, kind, params)`` を ``to_points(data, kind, **params)`` で点群にして
縦に連結し、``match3d.points_to_voxel`` で ``size^3`` の密度 grid に splat する
(各点が落ちる cell を +1、``smooth > 0`` なら σ = ``smooth`` voxel の Gaussian で
平滑)。``bounds=None`` なら連結点群の ``(min, max)`` を格子範囲にする。

引数:
- ``items``: 空でない list/tuple で、各要素が長さ 3 の ``(data, kind, params_dict)``
  (``params_dict`` は ``dict`` 必須)。``to_points`` の ``samples`` を変えたければ
  ``params`` に ``samples=`` を入れる。
- ``size``: 1 軸の voxel 数(立方格子固定)。
- ``bounds``: ``(lo, hi)`` それぞれ長さ 3。複数の雲を同じ格子に載せるとき(比較・
  ``voxel_iou``)は必ず明示する。
- ``device``: torch デバイス(``"cpu"`` / ``"cuda"``)。``smooth``: Gaussian σ [voxel]。

返り値: ``(voxel, bounds)`` — ``voxel`` は ``(size, size, size)`` float64 の
**点数密度**(合計 ≈ 総点数、確率ではない)、``bounds`` は実際に使った ``(lo, hi)``。
格子 index は ``points_to_voxel`` の ``floor((p - lo) / span * (size - 1))`` で、
軸 0 が点の x 成分に対応する(voxel の軸順 = 点の成分順)。

検証(``ValueError``): ``items`` が list/tuple でない・空・要素が 3 組でない・
``params`` が dict でない(生データを直接渡す誤用を入口で止める)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`fusion`)

[register_cross](register_cross.md)

---
*Provenance: fuse3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
