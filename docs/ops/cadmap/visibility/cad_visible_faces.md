---
op: cad_visible_faces
dim: cadmap
category: visibility
in: mesh
out: indices
examples: [defect_to_cad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# cad_visible_faces — CADMAP `visibility` op

- **データ種**: `mesh` → `indices`
- **呼び出し**: `import cadmap; cadmap.cad_visible_faces(mesh, K=None, R=None, t=None, width=64, height=64, cull_backfaces=True, strict=True)` (または `opscadmap.get("cad_visible_faces")`)

## 使い方

このカメラから**実際に見えている**面の ID(昇順、``indices`` sort)。

画像格子(``width`` x ``height``、画素中心は整数座標)へ光線を撃ち、最も
手前に来た面を集める。裏面(法線がカメラを向いていない)と、手前の面に
完全に隠れた面は入らない。検査カバレッジ — 「この視点で CAD のどの面を
見たことになるか」— をそのまま返す量で、``mesh_area`` と組み合わせれば
「未検査の面積」が出る。

格子の分解能より小さく写る面は取りこぼす(標本化なので当然)。**取りこぼし
を「隠れている」と言い換えない**ために、返るのは「見えた面」であって
「見えない面の補集合」ではない。

★ここだけ ``strict`` の既定が ``True``(他の 3 つは ``False``)。返りが素の
添字配列なので、**巻きを直したという事実を載せる先が無い**からで、
「黙って直す」を避けるにはここは拒否するしかない。``cull_backfaces=True``
のまま内向きの閉メッシュを渡すと ``ValueError`` になる。自動修正が欲しい
ときは ``strict=False`` を**呼び出し側で明示**すること — そのときは利用者が
修正を要求したのだから、返り値に載らなくても黙ってはいない。
``cull_backfaces=False`` なら巻き方向は結果に効かないので検査もしない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [defect_to_cad](../../../../examples/defect_to_cad.py) — `py -3.11 examples/defect_to_cad.py`

## 型が繋がる次の op(`indices` を入力に取れる)

—

## 同カテゴリ(`visibility`)

—

---
*Provenance: cadmap.py — CADMAP operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
