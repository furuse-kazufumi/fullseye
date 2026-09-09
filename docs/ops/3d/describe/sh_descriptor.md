---
op: sh_descriptor
dim: 3d
category: describe
in: voxel
out: descriptor
gpu: true
examples: [sh_descriptor_retrieval, shape_descriptor]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# sh_descriptor — 3D `describe` op

- **データ種**: `voxel` → `descriptor`
- **呼び出し**: `import fullseye as fs; fs.ledger.sh_descriptor(vol, L=8, nradii=12, ntheta=32, nphi=64, device='cpu')` (実装を直接呼ぶなら `import match3d; match3d.sh_descriptor(vol, L=8, nradii=12, ntheta=32, nphi=64, device='cpu')`、台帳から引くなら `ops3d.get("sh_descriptor")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

球面調和記述子。同心球 shell の SH 帯域エネルギー ‖f_l(r)‖ を (半径 × 周波数) で返す。

2D 閉輪郭を 1D Fourier 記述子で表す **線→面リフト**: 3D 閉曲面は SH で表し、帯域エネルギーは
回転で m を帯域内に混ぜるだけ=**回転不変**(Kazhdan 2003)。全 shell を grid_sample で取り、
固定 SH 基底との内積 → 帯域二乗和。retrieval/verification 用の大域シグネチャ。返り値 (nradii,L+1)。

honest 開示(2026-08-30 レビュー実測): 球面求積は一様 θ×φ グリッド和(Gauss-Legendre
でない)ため、値は**厳密な SH 帯域エネルギーの近似**(既定 32×64 で l=4 自己内積が
理論値の ~0.62 倍、解像度↑で 1 に収束)。match_sh_descriptor は L2 正規化+コサイン
類似度なので**同一 ntheta/nphi 同士の比較には影響しない**が、絶対値を物理量として
使う・異なる解像度設定間で比較するのは不可。

引数: ``vol`` は **立方体**(N,N,N)前提。中心 ``c = (N−1)/2`` と座標の正規化に軸 0 の長さ N
だけを使うので、非立方体だと軸 1,2 のサンプル位置が歪む(検証は無い)。shell 半径は
``0.2·rmax`` 〜 ``rmax = N/2 − 1`` を ``nradii`` 等分(voxel 単位)、各 shell を
``ntheta × nphi`` の (θ,φ) 格子で trilinear サンプルする。``L`` は最大次数。
返り値 ``(nradii, L+1)`` float32 numpy、``[i, l]`` が i 番目の shell の次数 l のエネルギー
(非負)。物体は volume の中心に置く(中心がずれると回転不変性が崩れる。``moment_axes`` の
重心で先に中心合わせを)。scipy の ``sph_harm_y``/``sph_harm`` を呼び出し時 import。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sh_descriptor_retrieval](../../../../examples_3d/sh_descriptor_retrieval.py) — `py -3.11 examples_3d/sh_descriptor_retrieval.py`
- [shape_descriptor](../../../../examples_3d/shape_descriptor.py) — `py -3.11 examples_3d/shape_descriptor.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`describe`)

[match_sh_descriptor](match_sh_descriptor.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
