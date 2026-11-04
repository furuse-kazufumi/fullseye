---
op: get_circle_pose
dim: mv
category: pose
in: keypoints
out: table
halcon: get_circle_pose
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# get_circle_pose — MV `pose` op

- **データ種**: `keypoints` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.get_circle_pose(contour, radius, cam_par)` (実装を直接呼ぶなら `import mvstereo; mvstereo.get_circle_pose(contour, radius, cam_par)`、台帳から引くなら `opsmv.get("get_circle_pose")`)
- **HALCON 相当**: `get_circle_pose`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

既知の半径の円の像(楕円の点列)から、円の中心と法線をカメラ座標で求める。

点列に円錐曲線を当てはめ、視線の錐の固有分解から 3-D の円を閉形式で求める。解は鏡像の
2 つで、1 枚の像からは区別できないので両方を、再投影の誤差つきで返す。正面視では 2 解が
重なる。歪みは扱わない(歪みのある点列は先に戻す)。
空の入力(``contour`` が 0 要素)は ValueError。

Args:
    contour: (N, 2) の ``(row, col)``(N >= 5)。
    radius: 円の半径(> 0)。返す中心の単位がこの単位になる。
    cam_par: ``fx`` / ``fy`` / ``cx`` / ``cy`` の dict。

Returns:
    ``center`` (2, 3)、``normal`` (2, 3)(カメラへ向く単位ベクトル)、``rms_px`` (2,) の dict。

出典: Y. C. Shiu and S. Ahmad, IEEE Trans. Robot. Autom. 5(1), 16-29 (1989);
Q. Chen, H. Wu, T. Wada, Proc. ECCV 2004, LNCS 3021, 302-315。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [find_ncc_models](../detect/find_ncc_models.md) · [run_bg_esti](../tracking/run_bg_esti.md) · [give_bg_esti](../tracking/give_bg_esti.md) · [update_bg_esti](../tracking/update_bg_esti.md) · [classify_class_gmm](../classify/classify_class_gmm.md)

## 同カテゴリ(`pose`)

—

---
*Provenance: mvstereo.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
