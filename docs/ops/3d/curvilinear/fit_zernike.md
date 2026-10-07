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
version: 0.5.0  # fullseye lib version this note was generated for
---

# fit_zernike — 3D `curvilinear` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_zernike(disk_image, n_max=6, device='cpu', nr=48, nt=72, center=None, radius=None)` (実装を直接呼ぶなら `import match3d; match3d.fit_zernike(disk_image, n_max=6, device='cpu', nr=48, nt=72, center=None, radius=None)`、台帳から引くなら `ops3d.get("fit_zernike")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

円板画像 → Zernike 係数(光学/波面計測の**極座標曲面近似**)。返り値 {(n,m): coef}。

直交多項式で円板上の曲面(波面収差、レンズ形状)を少数係数に。tilt/defocus/astigmatism/
coma/spherical 等が特定の (n,m) に対応し、回転で m が混ざる(帯域=回転不変)。

瞳(単位円板 ρ=1)は既定で画像中心 ``((H-1)/2, (W-1)/2)``、半径 ``min(H, W)/2 - 1`` 画素に
置かれる。画像の瞳がこれと違うなら ``center=(row, col)`` と ``radius``(画素)で渡す —— 渡さないと
半径の食い違いがそのまま低次モードへの漏れになる(129×129 で瞳半径 (H-1)/2 の純 defocus を
既定で読むと (2,0)=0.984 / (0,0)=−0.015、``radius=(H-1)/2`` を渡せば 0.999999)。瞳の円が画像から
はみ出す ``center`` / ``radius`` は ValueError。

honest 開示(2026-10-07 訂正): 以前ここには「離散サンプリング(nr=48, nt=72)由来の最大 ~10% の
クロストーク、nr/nt を上げれば減る」と書いていたが、原因は解像度ではなかった。瞳の半径・中心が
合っていて瞳の外にも値が続く画像なら既定の nr/nt で係数はほぼ 1(129×129 で 0.999999)に戻る。漏れの実際の原因は
(1) 上記の瞳半径・中心の食い違い(nr/nt を上げても 1 桁も減らない)と、(2) 瞳の外が 0 の画像で
いちばん外のリング(ρ=1)が縁に乗り、双一次補間が外側の 0 を吸い込むこと
(examples/poc_zernike_aberrations.py の実測)。

Raises ValueError: 入力が 2-D でない・2x2 未満・NaN/Inf/float32 桁あふれ・瞳が画像からはみ出す。

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
