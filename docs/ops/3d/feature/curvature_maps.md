---
op: curvature_maps
dim: 3d
category: feature
in: voxel
out: curvature
gpu: true
examples: [diff_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# curvature_maps — 3D `feature` op

- **データ種**: `voxel` → `curvature`
- **呼び出し**: `import fullseye as fs; fs.ledger.curvature_maps(vol, device='cpu', mc=0.000625)` (実装を直接呼ぶなら `import match3d; match3d.curvature_maps(vol, device='cpu', mc=0.000625)`、台帳から引くなら `ops3d.get("curvature_maps")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

level-set の主曲率 → shape index S(Koenderink)と curvedness。閉形式(Kindlmann 2003)。

2D 輪郭の曲率(スカラー 1 個)の **線→面リフト**: 曲面は主曲率 κ1,κ2 の 2 個を持つ。
mean = (κ1+κ2)/2 = (|g|²trH − gᵀHg)/|g|³、Gauss K = κ1κ2 = gᵀadj(H)g/|g|⁴(g=∇, H=Hessian)。
S=(2/π)atan2(κ1+κ2, κ1−κ2) ∈[-1,1] は **強度・回転に不変な局所曲面型**(cup−1/rut/saddle0/
ridge+.5/cap+1)。外向き法線規約で明凸 blob=cap(+1)。返り値 (S, curvedness, mask, |g|)、全 torch。

単位系: sobel3d の分離 conv 利得 32(deriv[-1,0,1]×平滑[1,2,1]²)をここで割り戻すので、
κ1,κ2/curvedness は **真の 1/voxel 単位**(半径 R の球殻で curvedness=1/R)、|g| と
mask 閾値 mc は **voxel あたりの真の勾配単位**。旧版(〜2026-08-29)は割り戻しを忘れ
curvedness が 1/32 倍・mc が生 sobel3d 単位だった(shape index S は比なので影響なし)。
旧 mc 値を使っていた場合は 1/32 して渡すこと(既定値 0.02→6.25e-4 も等価変換済み)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [diff_features](../../../../examples_3d/diff_features.py) — `py -3.11 examples_3d/diff_features.py`

## 型が繋がる次の op(`curvature` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [edt_jfa](edt_jfa.md) · [vol_frangi](vol_frangi.md) · [vol_sato](vol_sato.md) · [vol_hessian_blobness](vol_hessian_blobness.md) · [vol_gradient_magnitude](vol_gradient_magnitude.md) · [vol_local_maxima](vol_local_maxima.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
