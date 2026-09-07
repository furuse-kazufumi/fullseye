---
op: essential_8point
dim: 3d
category: two_view
in: image2d × image2d
out: matrix
examples: [sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# essential_8point — 3D `two_view` op

- **データ種**: `image2d × image2d` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.essential_8point(pts1, pts2, K1, K2=None)` (実装を直接呼ぶなら `import twoview; twoview.essential_8point(pts1, pts2, K1, K2=None)`、台帳から引くなら `ops3d.get("essential_8point")`)

## 使い方

対応点 + K から本質行列 E を直接。→ E (3,3)。

手順: ``fundamental_8point(pts1, pts2)`` で F を推定し、``E = K2ᵀ F K1`` を作ってから SVD で特異値を (1, 1, 0) に置き換える(本質行列の性質。結果の Frobenius ノルムは √2 に固定される)。

- ``K1`` (3,3) は画像 1 の内部行列、``K2`` を省略すると ``K1`` を両画像に使う(同一カメラの前提)。
- 対応点は画素座標 (N,2)。検証と例外は ``fundamental_8point`` と同じ(8 点未満・点数不一致・非有限・(N,2) でない入力は ``ValueError``)。
- E の符号は不定で、(R, t) は 4 候補に分かれる。分解と cheirality による一意化までまとめて行うのが ``recover_pose``。
- 外れ値に無防備。平面・純回転の退化も本 op では検出しない(``recover_pose`` が検出する)。決定論的。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`two_view`)

[fundamental_8point](fundamental_8point.md) · [recover_pose](recover_pose.md) · [triangulate](triangulate.md) · [sampson_distance](sampson_distance.md)

---
*Provenance: twoview.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
