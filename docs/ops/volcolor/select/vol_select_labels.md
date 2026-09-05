---
op: vol_select_labels
dim: volcolor
category: select
in: labels
out: labels
examples: [voxel_labels_color]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# vol_select_labels — VOLCOLOR `select` op

- **データ種**: `labels` → `labels`
- **呼び出し**: `import volcolor; volcolor.vol_select_labels(labels, props=None, spacing=None, relabel: 'bool' = False, exclude_border: 'bool' = False, keep=None, **criteria)` (または `opsvolcolor.get("vol_select_labels")`)

## 使い方

3-D の特徴で成分をふるいにかける(2-D のブロブ選別の 3-D 版)。

``(labels_out, kept_ids)`` を返す。落ちた成分のボクセルは 0(背景)になる。

*props* は :func:`vol_label_shape_stats` か :func:`volops.vol_region_props` の
返り値。``None`` なら :func:`vol_label_shape_stats` をその場で呼ぶ。

条件(すべて省略可・与えたものは AND):``min_volume`` ``max_volume``
``min_voxels`` ``max_voxels`` ``min_sphericity`` ``max_sphericity``
``min_elongation`` ``max_elongation`` ``min_isotropy`` ``max_isotropy``
``min_equivalent_diameter`` ``max_equivalent_diameter``。加えて
``exclude_border=True`` で**ボリューム端に接する成分を落とす**(CT の視野で
切れている粒子を計測から外す標準手順)、``keep=[...]`` で残す id を直接指定。

**必要なキーが props に無ければ ValueError**。たとえば ``min_sphericity`` を
:func:`vol_label_shape_stats` の結果に対して指定すると、``sphericity`` は
そちらが出さない量なので拒否する ―― 欠けたキーを既定値で埋めると「条件を
書いたのに一件も落ちない」フィルタが黙って出来上がる。

``relabel``:

  * ``False``(既定)―― **元の id をそのまま残す**。ゆえに
    :func:`vol_colorize_labels` を前後で呼んでも**残った成分の色は変わらない**。
    「ふるいにかけて色が残っていく」図が成立するのはこの既定のおかげである。
  * ``True`` ―― 残った成分を ``1..k`` へ振り直す。**色は総取り替えになる**
    (ラベル番号がパレットの行番号だから)。下流が連番を要求する場合だけ使う。
    この 1 引数がこの族の売りを壊せる唯一の場所なので、明示的にした。

Returns ``(labels_out int32 (D, H, W), kept_ids np.ndarray int64)``.
Raises ``ValueError`` for an unknown criterion, a criterion whose key is absent
from *props*, a *props* that does not cover the labels present, or a *keep*
containing a label that is not in the volume.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [voxel_labels_color](../../../../examples/voxel_labels_color.py) — `py -3.11 examples/voxel_labels_color.py`

## 型が繋がる次の op(`labels` を入力に取れる)

[vol_colorize_labels](../colorize/vol_colorize_labels.md) · [vol_label_overlay](../colorize/vol_label_overlay.md) · [vol_label_shape_stats](../measure/vol_label_shape_stats.md) · [vol_label_legend](../measure/vol_label_legend.md) · [vol_labels_to_meshes](../render/vol_labels_to_meshes.md) · [vol_label_volume_render](../render/vol_label_volume_render.md)

## 同カテゴリ(`select`)

—

---
*Provenance: volcolor.py — VOLCOLOR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
