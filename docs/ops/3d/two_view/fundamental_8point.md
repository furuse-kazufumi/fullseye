---
op: fundamental_8point
dim: 3d
category: two_view
in: image2d × image2d
out: matrix
examples: [two_view_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# fundamental_8point — 3D `two_view` op

- **データ種**: `image2d × image2d` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.fundamental_8point(pts1, pts2)` (実装を直接呼ぶなら `import twoview; twoview.fundamental_8point(pts1, pts2)`、台帳から引くなら `ops3d.get("fundamental_8point")`)

## 使い方

正規化 8 点法で基礎行列 F を推定(rank-2 強制)。→ F (3,3)。8 点以上必要。

Raises ValueError: 点が (N,2) でない/非有限/8 点未満/対応数不一致。

手順: 両画像の点を Hartley 正規化(重心を原点、平均距離 √2)→ 9 列の係数行列の最小特異ベクトルを F とする → 特異値の 3 番目を 0 にして rank-2 に強制 → ``T2ᵀ F T1`` で逆正規化 → ``F[2,2]`` で割って正規化(それがほぼ 0 なら Frobenius ノルムで割る)。

- 対応点は画素座標 (x, y) の (N,2)。規約は ``x2ᵀ F x1 = 0``(x1 が pts1、x2 が pts2)。
- F はスケール不定(定数倍しても同じ幾何)で符号も一意ではない。
- 全点を等しく使う最小二乗で、外れ値には無防備。誤対応が混じる対応は本 op の前に除くか、``sampson_distance`` で残差を見て選別してから再フィットする。
- 平面シーンや純回転では対応点が 1 つのホモグラフィで説明でき F は一意に決まらない(それでも何かは返る)。この退化は ``recover_pose`` が入口で検出して拒否する。
- 決定論的。後段は ``essential_8point`` / ``recover_pose`` / ``sampson_distance``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [two_view_pose](../../../../examples_3d/two_view_pose.py) — `py -3.11 examples_3d/two_view_pose.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`two_view`)

[essential_8point](essential_8point.md) · [recover_pose](recover_pose.md) · [triangulate](triangulate.md) · [sampson_distance](sampson_distance.md)

---
*Provenance: twoview.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
