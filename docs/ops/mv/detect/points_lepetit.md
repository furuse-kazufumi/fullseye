---
op: points_lepetit
dim: mv
category: detect
in: image2d
out: keypoints
halcon: points_lepetit
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# points_lepetit — MV `detect` op

- **データ種**: `image2d` → `keypoints`
- **呼び出し**: `import fullseye as fs; fs.ledger.points_lepetit(image, radius=3, check_neighbor=1, min_check_neighbor_diff=0.06, min_score=0.2, subpix=True)` (実装を直接呼ぶなら `import mvimage; mvimage.points_lepetit(image, radius=3, check_neighbor=1, min_check_neighbor_diff=0.06, min_score=0.2, subpix=True)`、台帳から引くなら `opsmv.get("points_lepetit")`)
- **HALCON 相当**: `points_lepetit`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

円周上の向かい合う 2 点の比較で注目点を検出する(Lepetit と Fua の点検出)。

中心の灰色値に近い向かい合う 2 点が円周のどこかにあれば、そこを通る直線が伸びていると
見なして落とす。残った画素を、円周の 2 階差分の総和(離散ラプラシアンの近似)で採点し、
半径 ``radius`` の窓の極大だけを残す。``subpix`` が真なら応答の放物線で小数の位置へ寄せる。
灰色の範囲は ``[0, 1]`` を想定するので、``min_check_neighbor_diff`` と ``min_score`` は
その尺度で渡す。平らな画像は空の点列を返す。
空の入力(``image`` が 0 要素)は ValueError。

Args:
    image: (H, W) の画像。
    radius: 比較する円の半径(画素、>= 1)。
    check_neighbor: 円周で左右に何点まで一緒に比べるか(>= 0)。
    min_check_neighbor_diff: 「近い」と見なす灰色の差の上限。
    min_score: 応答(円周平均の 2 階差分の絶対値)の下限。
    subpix: 位置を小数へ寄せるか。

Returns:
    (N, 2) の ``(row, col)``。応答の強い順。

出典: V. Lepetit and P. Fua, IEEE Trans. PAMI 28(9), 1465-1479 (2006), doi:10.1109/TPAMI.2006.188。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`keypoints` を入力に取れる)

[get_grayval_contour_xld](../gray/get_grayval_contour_xld.md) · [get_circle_pose](../pose/get_circle_pose.md) · [gen_nurbs_interp](../curve/gen_nurbs_interp.md)

## 同カテゴリ(`detect`)

[create_ncc_model](create_ncc_model.md) · [find_ncc_models](find_ncc_models.md)

---
*Provenance: mvimage.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
