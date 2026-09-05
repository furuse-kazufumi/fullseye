---
op: cad_defect_to_cad
dim: cadmap
category: defect
in: mesh × labels
out: table
examples: [defect_to_cad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# cad_defect_to_cad — CADMAP `defect` op

- **データ種**: `mesh × labels` → `table`
- **呼び出し**: `import cadmap; cadmap.cad_defect_to_cad(mesh, labels, K=None, R=None, t=None, cull_backfaces=True, min_pixels=1, background=0, strict=False)` (または `opscadmap.get("cad_defect_to_cad")`)

## 使い方

2-D の欠陥ラベル画像 → **CAD 面上の表**(面 ID / 面上の面積 / 3-D 重心)。

``labels`` は (H, W) の整数ラベル画像(``background`` は無視、bool マスクも
可)。ラベルごとに全画素の視線を撃ち、当たった面と、その画素が**面の上で
占める実面積**を積む。面積は画素数ではなく

    dA = Z^2 * cosα / (fx * fy * |cosθ|)

で、``cosα`` は光軸からの傾き、``cosθ`` は視線と面法線のなす角。**斜めから
見た面ほど 1 画素が広い面積を覆う**という透視投影のヤコビアンそのもので、
ここを ``Z^2/(fx*fy)`` のままにすると傾いた面の欠陥が小さく出る(60 度で
ちょうど半分になる)。

返りはラベルごとの dict の list(``table`` sort):

  * ``label``        ラベル値。
  * ``n_pixels``     そのラベルの画素数。
  * ``n_hit``        CAD に当たった画素数。``hit_fraction`` = その比。
  * ``area``         面上の実面積(mesh の長さ単位の 2 乗)。当たった画素分
    だけの和で、当たらなかった画素は**足さない**。
  * ``area_naive``   ``Z^2/(fx*fy)`` だけの和(= 傾きを無視した値)。両方
    返すのは、傾き補正が効いているかを利用者が自分で確かめられるようにする
    ため。
  * ``face_ids``     当たった面の昇順一意リスト(int64 配列)。
  * ``face_areas``   ``face_ids`` と同じ並びの面ごとの面積。
  * ``centroid``     面積重みの 3-D 重心(世界座標)。当たり 0 なら ``NaN``。
  * ``depth_mean``   当たった画素の平均 Z。当たり 0 なら ``NaN``。
  * ``winding_fixed`` bool — 内向きに巻かれた閉メッシュを検出して直したか。
    **全レコードに同じ値**が入る(mesh 単位の性質なので)。

``min_pixels`` 未満の領域は落とす。当たり 0 の領域は**消さずに** ``area =
0.0``, ``hit_fraction = 0.0`` で残す — 消すと「CAD の外にあった欠陥」が
表から静かに消えるため。

巻き方向の扱いは他の op と同じ(``cull_backfaces=True`` で閉じた内向き
メッシュを検出 → 既定は自動修正 + ``winding_fixed``、``strict=True`` で
``ValueError``)。**正直な限界**: 返るのがレコードの list なので、``labels``
が全部背景だったり全領域が ``min_pixels`` 未満だったりして **list が空**に
なると、修正の事実を載せる先が無い。その場合はそもそも 1 つも欠陥を写して
いない(誤った数を返しようがない)。載せる先が要るなら ``strict=True`` に
するか、同じ mesh で :func:`cad_pixel_to_surface` を 1 画素だけ引くこと。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [defect_to_cad](../../../../examples/defect_to_cad.py) — `py -3.11 examples/defect_to_cad.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`defect`)

—

---
*Provenance: cadmap.py — CADMAP operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
