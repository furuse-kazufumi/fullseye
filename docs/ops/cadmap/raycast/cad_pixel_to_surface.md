---
op: cad_pixel_to_surface
dim: cadmap
category: raycast
in: mesh × keypoints
out: table
examples: [defect_to_cad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# cad_pixel_to_surface — CADMAP `raycast` op

- **データ種**: `mesh × keypoints` → `table`
- **呼び出し**: `import cadmap; cadmap.cad_pixel_to_surface(mesh, pixels, K=None, R=None, t=None, cull_backfaces=True, image_size=None, strict=False)` (または `opscadmap.get("cad_pixel_to_surface")`)

## 使い方

画素 (N,2) → CAD 面上の ``(face_id, 重心座標, 3-D 点)``(閉形式)。

画素ごとに視線を作り(``camera.py`` 規約: 中心は整数座標、``u`` = 列、
``v`` = 行)、Möller-Trumbore で全三角形と交差させ、**最も手前の当たり**を
採る。当たらない画素には ``face_id = -1`` を返し、**最寄りの面へは絶対に
丸めない**(検査で「欠陥が背景に載っていた」を「面 17 の欠陥」に化けさせない
ため)。``cull_backfaces=True``(既定)では法線がカメラを向いていない面は
当たりにしない。

返りは dict:

  * ``face_id``  (N,) int64 — 当たった三角形の行番号。miss は ``-1``。
  * ``bary``     (N,3) — 重心座標 ``(w0, w1, w2)``、``F[face_id]`` の 3 頂点の
    順。``point = w0*V[i0] + w1*V[i1] + w2*V[i2]`` が厳密に成り立つ。
    miss は ``NaN``。辺・頂点上では 1 成分が ``0``(許容 ``1e-9``)。
  * ``point``    (N,3) — 世界座標の交点。miss は ``NaN``。
  * ``depth``    (N,) — カメラ座標の Z(視線距離ではない)。miss は ``NaN``。
  * ``normal``   (N,3) — 当たった面の単位法線(世界座標、巻き方どおり)。
    miss は ``NaN``(``bary``/``point``/``depth`` と同じ規約)。
  * ``hit``      (N,) bool。
  * ``camera``   実際に使われた ``K``/``R``/``t``/``width``/``height``。
    既定に落ちた場合もここを見れば分かる。
  * ``winding_fixed`` bool — 内向きに巻かれた閉メッシュを検出して**この
    呼び出しの中で巻きを直した**かどうか。常に入る(``False`` でも入る)。

``cull_backfaces=True``(既定)で mesh が閉じていて符号つき体積が負なら、
既定では巻きを直して ``winding_fixed=True`` を返す。``strict=True`` にすると
直さず ``ValueError`` で拒否する。``cull_backfaces=False`` のときは裏面判定を
しないので巻き方向は結果に効かず、検査もせず ``winding_fixed`` は常に
``False``(``normal`` は入力の巻きどおりの符号で返る)。詳細は
:func:`_orient_for_culling`。

``K``/``R``/``t`` を省くと mesh を画像に収める既定カメラを作る
(``R = I``、カメラは重心の -Z 側)。``image_size`` を省くと**与えた画素の
外接箱**から画像サイズを決める — 既定カメラが画素のある場所を見るように
するためで、``K`` を明示したときは ``in_image`` 判定にしか効かない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [defect_to_cad](../../../../examples/defect_to_cad.py) — `py -3.11 examples/defect_to_cad.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`raycast`)

—

---
*Provenance: cadmap.py — CADMAP operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
