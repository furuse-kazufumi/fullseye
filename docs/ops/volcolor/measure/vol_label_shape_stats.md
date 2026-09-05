---
op: vol_label_shape_stats
dim: volcolor
category: measure
in: labels
out: table
examples: [voxel_labels_color]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# vol_label_shape_stats — VOLCOLOR `measure` op

- **データ種**: `labels` → `table`
- **呼び出し**: `import volcolor; volcolor.vol_label_shape_stats(labels, spacing=None, shape: 'bool' = True)` (または `opsvolcolor.get("vol_label_shape_stats")`)

## 使い方

成分ごとの**線形時間で出せる**定量値(体積・重心・箱・主成分形状指標)。

:func:`volops.vol_region_props` の姉妹だが、**目的が違う**:

  * あちらは ``surface_area`` と Wadell ``sphericity`` を出す。そのために
    成分ごとに marching cubes を回すので、**成分数に比例して Python ループが
    回る**(1 ボクセル 1 ラベルの病的入力で急速に重くなる)。
  * こちらは ``np.bincount`` の重み付き総和だけで済む量に限る。ラベル配列 1 本
    あたり 9 回の ``bincount`` = **O(N + n)**。実測(``connectivity=26``、
    **1 ボクセル 1 ラベル**の市松模様 = 病的入力):
    16**3 = 4096 ボクセル / 512 成分 = 0.0037 s、32**3 = 32768 / 4096 =
    0.0350 s、64**3 = 262144 / 32768 = 0.2556 s、128**3 = 2097152 / 262144 =
    2.3122 s。**ボクセル 8 倍ごとに 9.5 / 7.3 / 9.0 倍**(二次なら 64 倍)で、
    全域で約 1.1 マイクロ秒/ボクセル。同じ 128**3 の色付けは 0.0357 s。
    (参考: ``volops.vol_region_props(surface="faces")`` は同じ 16**3 で
    0.0121 s ―― 成分ごとの Python ループがあるぶん 3.5 倍。marching cubes を
    使う既定の ``surface="auto"`` はさらに重い。)

``label`` ``voxel_count`` ``volume`` ``centroid`` ``bbox`` の 5 つは
:func:`volops.vol_region_props` と**同一の定義・同一の値**である
(``tests/test_volcolor.py::test_stats_agree_with_vol_region_props_exactly`` が
厳密一致で固定)。``bbox`` は ``(z0, z1, y0, y1, x0, x1)`` で上限は排他的。

加えて返すもの:

  ``centroid_mm`` ``(z, y, x)`` 物理座標(spacing 無しなら voxel と同値)·
  ``extent`` bbox の物理寸法 ``(dz, dy, dx)`` · ``equivalent_diameter``
  ``(6V/pi)**(1/3)`` · ``touches_border`` bbox がボリューム端に接するか ·
  ``principal_extent`` 共分散固有値の平方根 ``(s1 >= s2 >= s3)``(物理単位) ·
  ``linearity`` ``(l1-l2)/l1`` · ``planarity`` ``(l2-l3)/l1`` · ``isotropy``
  ``l3/l1`` · ``elongation`` ``sqrt(l1/l2)``。

**``elongation`` は無限になりうる**(契約):``l1 > 0`` かつ ``l2 == 0``、
すなわち厚み 1 ボクセルの完全な直線の成分では ``inf`` を返す。0 で割った事故
ではなく「第 2 軸方向に広がりが無い」という事実であり、丸めると細長さの順位が
黙って入れ替わる。単一ボクセル(``l1 == 0``)は等方な点なので ``1.0``。

**spacing を渡し忘れると数字も結論も変わる**。実測 ―― 半径 6 mm の球を
``spacing = (3.0, 1.0, 1.0)`` mm の異方格子(z だけ 3 倍粗い)で標本化すると
293 ボクセルになる。閉形式の真値は ``4/3 pi 6**3 = 904.78 mm**3``:

  * ``spacing`` あり = 879.0 mm**3(誤差 **-2.85 %**)、
    ``isotropy`` = 0.7349(ほぼ等方 = 正しい)。
  * ``spacing`` なし = 293.0(voxel 単位。mm**3 と読むと誤差 **-67.62 %**)、
    ``isotropy`` = 0.0817 ―― **球が「板」に見える**。異方性を無視すると
    形状指標は破綻し、しかも有限で妥当そうな値として返る。
  * 等価直径も 11.8849 mm 対 8.2406 と 1.44 倍ずれる。

数値上の注意:2 次モーメントは ``E[x**2] - E[x]**2`` で求めるので、座標が
大きく広がりが小さい成分では桁落ちが起きうる。上限 :data:`MAX_COLOR_VOXELS`
(1 辺 ~2000 まで)では ``E[x**2] ~ 4e6`` に対し float64 の相対精度 1e-16 =
絶対 1e-10 で、ボクセル単位の分散に対して 10 桁の余裕がある。それより大きい
ボリュームは ROI を切ってから渡すこと(上限があるのはこのためでもある)。

*shape* を ``False`` にすると共分散(9 本のうち 6 本の bincount)を省き、
``principal_extent`` 以下の 5 項目を返さない ―― 体積フィルタしか要らない
ときに O(N) の一時配列を 1 本に減らせる。

Returns ``list[dict]`` in ascending label order (**実在するラベルのみ** ――
番号に欠番があっても、``labels.max()`` ぶんの空 dict は返さない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [voxel_labels_color](../../../../examples/voxel_labels_color.py) — `py -3.11 examples/voxel_labels_color.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`measure`)

[vol_label_legend](vol_label_legend.md)

---
*Provenance: volcolor.py — VOLCOLOR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
