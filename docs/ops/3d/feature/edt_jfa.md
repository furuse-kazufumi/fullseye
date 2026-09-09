---
op: edt_jfa
dim: 3d
category: feature
in: voxel
out: sdf
gpu: true
examples: [diff_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# edt_jfa — 3D `feature` op

- **データ種**: `voxel` → `sdf`
- **呼び出し**: `import fullseye as fs; fs.ledger.edt_jfa(seed_bool, device='cpu')` (実装を直接呼ぶなら `import match3d; match3d.edt_jfa(seed_bool, device='cpu')`、台帳から引くなら `ops3d.get("edt_jfa")`)
- **台帳経由の戻り値**: `fullseye.ledger.edt_jfa(...)` は**宣言 out 型 `sdf` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.edt_jfa.raw(...)`、または `match3d.edt_jfa` を直接呼ぶ。
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

3D ユークリッド距離変換 = Jump Flooding Algorithm(GPU)。各 voxel → 最近 seed 距離。

実測で scipy EDT と厳密一致(max|err|=0、N≤160・JFA+2)。scipy(C 実装)は小さい N では
速いが、GPU-JFA は N≥96 で追い抜く(RTX5090 実測 96→2.6× / 128→4.7×)。全 voxel 並列で
GPU 常駐でき、chamfer を CPU 往復なしの全 GPU パイプラインにするのが本質。末尾の step=1 を
2 パス(JFA+2)にして大 N の近似誤差も消す。返り値 距離場 (D,H,W) の torch tensor。

引数 ``seed_bool`` は ``(D,H,W)`` の bool(True=seed、距離 0)。返り値は **torch float32
tensor** ``(D,H,W)``(``device`` 上、numpy ではない。台帳経由 ``fs.ledger.edt_jfa`` では
numpy に変換される)。距離は voxel 中心間のユークリッド距離(voxel 単位)。
seed が 1 つも無いと全 voxel が 1e6 に飽和する(例外は出ない)。26 方向 × log2(max(D,H,W))
段のジャンプなので、メモリは ``(3,D,H,W)`` float32 が数枚分。
用途: ``signed_distance_field``(両側)、``match_chamfer_3d(edt="jfa")``。CPU 版は
``scipy.ndimage.distance_transform_edt(~seed)`` と同じ値。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [diff_features](../../../../examples_3d/diff_features.py) — `py -3.11 examples_3d/diff_features.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](../sdf_csg/sdf_union.md) · [sdf_intersect](../sdf_csg/sdf_intersect.md) · [sdf_subtract](../sdf_csg/sdf_subtract.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [vol_frangi](vol_frangi.md) · [vol_sato](vol_sato.md) · [vol_hessian_blobness](vol_hessian_blobness.md) · [vol_gradient_magnitude](vol_gradient_magnitude.md) · [vol_local_maxima](vol_local_maxima.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
