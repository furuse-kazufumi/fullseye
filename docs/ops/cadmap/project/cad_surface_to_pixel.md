---
op: cad_surface_to_pixel
dim: cadmap
category: project
in: mesh × points
out: table
examples: [defect_to_cad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# cad_surface_to_pixel — CADMAP `project` op

- **データ種**: `mesh × points` → `table`
- **呼び出し**: `import cadmap; cadmap.cad_surface_to_pixel(mesh, points, K=None, R=None, t=None, image_size=None, cull_backfaces=True, depth_tol=1e-06, strict=False)` (または `opscadmap.get("cad_surface_to_pixel")`)

## 使い方

3-D 点 (N,3) → 画素 + **可視性**(遮蔽・背面・画枠外を区別して返す)。

``camera.project_points`` で投影したうえで、**同じ画素へ光線を撃ち直して**
手前に別の面が無いかを確かめる。これをやらないと、隠れている点の画素座標を
「そこに見えている」かのように返してしまう。返りは dict:

  * ``uv``            (N,2) — 画素 ``(u=列, v=行)``。``depth <= 0`` の点でも
    投影値は返るが ``in_front = False`` が立つ。
  * ``depth``         (N,) — カメラ座標 Z。
  * ``in_front``      (N,) bool — ``depth > 0``。
  * ``in_image``      (N,) bool — 画枠内(``0 <= u <= width-1`` かつ
    ``0 <= v <= height-1``)。
  * ``occluded``      (N,) bool — 同じ視線上で、その点より手前に面がある。
  * ``occluder_face`` (N,) int64 — 遮っている面。無ければ ``-1``。
  * ``visible``       (N,) bool — ``in_front & in_image & ~occluded``。
  * ``camera``        実際に使われたカメラ。
  * ``winding_fixed`` bool — 内向きに巻かれた閉メッシュを検出して直したか。

``depth_tol`` は「自分自身の面に遮られた」と誤判定しないための相対許容で、
遮蔽と判定するのは ``z_hit < depth * (1 - depth_tol) - depth_tol`` のとき。
閉じた mesh の**裏側**にある点は、手前の壁に遮られて ``occluded = True`` に
なる — これは仕様であって取りこぼしではない。

**遮蔽判定は巻き方向に依存する**(手前の壁が裏面としてカリングされると、
裏側の点まで ``visible`` になる)。そのため ``cull_backfaces=True`` では
内向きに巻かれた閉メッシュを検出し、既定では巻きを直して
``winding_fixed=True`` を返す。``strict=True`` で ``ValueError``、
``cull_backfaces=False`` では検査そのものをしない
(詳細は :func:`_orient_for_culling`)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [defect_to_cad](../../../../examples/defect_to_cad.py) — `py -3.11 examples/defect_to_cad.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`project`)

—

---
*Provenance: cadmap.py — CADMAP operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
