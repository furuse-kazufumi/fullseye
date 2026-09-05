---
op: vol_labels_to_meshes
dim: volcolor
category: render
in: labels
out: table
examples: [voxel_labels_color]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# vol_labels_to_meshes — VOLCOLOR `render` op

- **データ種**: `labels` → `table`
- **呼び出し**: `import volcolor; volcolor.vol_labels_to_meshes(labels, ids=None, spacing=None, seed: 'int' = 0, level: 'float' = 0.5, axes: 'str' = 'xyz')` (または `opsvolcolor.get("vol_labels_to_meshes")`)

## 使い方

成分ごとに marching cubes をかけ、**色付きメッシュの集合**にする。

返りは ``list[dict]``、各要素が ``{"label", "vertices" (nv, 3) float64,
"faces" (nf, 3) int64, "color" (r, g, b)}``。色は
:func:`vol_colorize_labels` と同じパレットなので、**断面図と 3-D 表示で同じ
部品が同じ色**になる。

成分ごとに **bbox を 1 ボクセル分パディングした部分体**だけを切り出して
marching cubes を回す(全ボリュームを成分数だけ舐めない)。パディングは
ボリューム端に接する成分の面を閉じるためで、これをしないと端の成分だけ
穴の開いたメッシュになる。

``axes``:

  * ``"xyz"``(既定)―― 頂点を ``(x, y, z)`` で返す。:mod:`render3d` /
    :mod:`mesh` の頂点順がこれで、``render3d.render_mesh`` へ直接渡せる。
  * ``"zyx"`` ―― ボリュームの添字順のまま返す。:func:`vol_label_shape_stats`
    の ``centroid`` と同じ並びになる。

  **黙って取り違えると例外は出ない** ―― 出るのは上下と前後が入れ替わった、
  それらしい絵である。``tests/test_volcolor.py::test_mesh_axes_order_is_explicit`` が
  両方の重心を stats の重心と突き合わせて固定している。

*spacing* を渡すと頂点は物理座標(mm)になる。*ids* で成分を絞れる
(``None`` なら実在する全ラベル、ただし :data:`MAX_MESHES` 件まで)。

Raises ``ImportError`` (with the ``pip install scikit-image`` message) when
marching cubes is unavailable, and ``ValueError`` for a bad *axes*, a *level*
outside ``(0, 1)``, an *ids* naming an absent label, or more than
:data:`MAX_MESHES` components.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [voxel_labels_color](../../../../examples/voxel_labels_color.py) — `py -3.11 examples/voxel_labels_color.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`render`)

[vol_label_volume_render](vol_label_volume_render.md)

---
*Provenance: volcolor.py — VOLCOLOR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
