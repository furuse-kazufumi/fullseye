---
op: match_sh_descriptor
dim: 3d
category: describe
in: voxel × voxel
out: measurement
gpu: true
examples: [sh_descriptor_retrieval, shape_descriptor]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# match_sh_descriptor — 3D `describe` op

- **データ種**: `voxel × voxel` → `measurement`
- **呼び出し**: `import match3d; match3d.match_sh_descriptor(a, b, L=8, nradii=12, device='cpu')` (または `ops3d.get("match_sh_descriptor")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

SH 記述子同士のコサイン類似度(回転不変な形状照合)。1 に近いほど同形状。voxel × SH 列。

``sh_descriptor(a, L, nradii)`` と ``sh_descriptor(b, L, nradii)`` を平坦化して L2 正規化し、
内積を float で返す。帯域エネルギーは非負なので値は **[0, 1]**(負にならない)。どちらかの
記述子が全 0(空 volume)なら 0。
- ``a``, ``b`` は立方体 volume(``sh_descriptor`` の前提)。形が違ってもよいが、shell 半径が
各 N で決まるので **スケールが違う物体は別物**として低く出る(スケール不変ではない)。
中心ずれにも弱い(重心で中心合わせしてから)。
- 回転には不変(帯域エネルギー)。ただし鏡像も同じ値になる。
- ``ntheta``/``nphi`` は既定(32×64)固定。同じ設定同士の比較にだけ意味がある。
- 位置は返さない。「どこにあるか」は ``match_shape_3d`` 等、「同じ形か」は本 op。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sh_descriptor_retrieval](../../../../examples_3d/sh_descriptor_retrieval.py) — `py -3.11 examples_3d/sh_descriptor_retrieval.py`
- [shape_descriptor](../../../../examples_3d/shape_descriptor.py) — `py -3.11 examples_3d/shape_descriptor.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`describe`)

[sh_descriptor](sh_descriptor.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
