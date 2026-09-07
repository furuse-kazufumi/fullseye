---
op: fit_zernike
dim: 3d
category: curvilinear
in: image2d
out: table
gpu: true
examples: [curvilinear_proj]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fit_zernike — 3D `curvilinear` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_zernike(disk_image, n_max=6, device='cpu', nr=48, nt=72)` (実装を直接呼ぶなら `import match3d; match3d.fit_zernike(disk_image, n_max=6, device='cpu', nr=48, nt=72)`、台帳から引くなら `ops3d.get("fit_zernike")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

円板画像 → Zernike 係数(光学/波面計測の**極座標曲面近似**)。返り値 {(n,m): coef}。

直交多項式で円板上の曲面(波面収差、レンズ形状)を少数係数に。tilt/defocus/astigmatism/
coma/spherical 等が特定の (n,m) に対応し、回転で m が混ざる(帯域=回転不変)。

honest 開示(2026-08-30 レビュー実測): 離散サンプリング(既定 nr=48, nt=72)では
理論上直交のモード間に**最大 ~10% のクロストーク**が残る(例: 純 (2,0) defocus 入力で
係数回収 0.95、リーク先は (4,0))。支配モードの特定には十分だが、係数の定量比較が
要るときは nr/nt を上げる(誤差は解像度に対し単調減少)。

Raises ValueError: 入力が 2-D でない・2x2 未満・NaN/Inf/float32 桁あふれ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [curvilinear_proj](../../../../examples_3d/curvilinear_proj.py) — `py -3.11 examples_3d/curvilinear_proj.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`curvilinear`)

[polar_unwrap](polar_unwrap.md) · [cylinder_unwrap](cylinder_unwrap.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
