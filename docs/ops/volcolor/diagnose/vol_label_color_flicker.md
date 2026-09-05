---
op: vol_label_color_flicker
dim: volcolor
category: diagnose
in: voxel
out: table
examples: [voxel_labels_color]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# vol_label_color_flicker — VOLCOLOR `diagnose` op

- **データ種**: `voxel` → `table`
- **呼び出し**: `import volcolor; volcolor.vol_label_color_flicker(vol_binary, axis='z', seed: 'int' = 0, connectivity: 'int' = 26, connectivity_2d: 'int' = 8)` (または `opsvolcolor.get("vol_label_color_flicker")`)

## 使い方

「切ってから色を付ける」と「色を付けてから切る」の差を**数える**。

同じ 2 値ボリュームに対して 2 通りの手順を踏む:

  A. **スライスごと** ―― 各断面を 2-D で連結成分ラベリングし、
     :func:`imgio.colorize_labels` と同じパレットで色を付ける。
     断面ごとに番号が振り直されるので、同じ部品でも層が変われば色が変わりうる。
  B. **ボリュームで** ―― :func:`volops.vol_label` でラベリングしてから
     :func:`vol_colorize_labels` で色を付け、あとで切る。

返りは dict:

  ``n_components`` 3-D 成分数 · ``n_slices`` 断面の数 ·
  ``slices_with_change`` **A で 1 つ以上の成分の色が変わった断面の本数** ·
  ``changed_pairs`` A で色が変わった (成分, 断面) の組の数 ·
  ``changed_components`` A で一度でも色が変わった成分の数 ·
  ``volume_slices_with_change`` / ``volume_changed_pairs`` /
  ``volume_changed_components`` B の同じ量(**構造上 0**) ·
  ``pairs_checked`` 比較した (成分, 断面) の総数 ·
  ``flicker_rate`` ``changed_pairs / pairs_checked``。

比較の定義:各 3-D 成分 ``c`` について、``c`` が現れる最初の断面での色を
基準とし、以降の断面で ``c`` の画素の**最頻色**が基準と違えば 1 件と数える
(1 つの 3-D 成分が 1 断面で複数の 2-D 片に割れることがあるため、代表は
最頻色。同数の場合は RGB の辞書順で小さい方 = 決定的)。

実測(``(24, 48, 48)``・16 球の参照ファントム、seed=0、axis="z"、
``connectivity=26`` / ``connectivity_2d=8``):``pairs_checked=108``、
``slices_with_change=20 / 24``、``changed_pairs=62``(57.4 %)、
``changed_components=16 / 16``。B 側は 3 つとも 0 ―― **構造上 0 であって、
たまたま 0 なのではない**(ラベル番号がボリューム全体で一意だから)。

Raises ``ValueError`` for a bad volume, an unknown *axis*, or a *connectivity*
that is not 6 / 18 / 26 (2-D: 4 / 8).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [voxel_labels_color](../../../../examples/voxel_labels_color.py) — `py -3.11 examples/voxel_labels_color.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`diagnose`)

—

---
*Provenance: volcolor.py — VOLCOLOR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
