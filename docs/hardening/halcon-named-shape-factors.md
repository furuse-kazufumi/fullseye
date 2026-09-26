---
id: halcon-named-shape-factors
date: 2026-09-26
found_by: shape_factors_closed_form
kind: silent-wrong
severity: high
where: [backends_auto.py]
ops: [circularity, roundness, rectangularity, circularity_xld, compactness_xld, rectangularity_xld]
gate: [test_the_op_returns_the_halcon_quantity, test_rectangularity_is_one_for_rectangles_whatever_the_angle, test_rectangularity_is_one_for_a_square, test_the_old_isoperimetric_formula_is_what_the_gate_catches, test_the_old_axis_aligned_extent_is_what_the_gate_catches, test_the_contour_twin_answers_the_same_question, test_every_same_named_shape_factor_is_either_checked_or_named]
status: fixed
---

# HALCON と同じ名前の形状係数が、HALCON と**別の量**を返していた

## 症状

同名を名乗る 6 本のうち、HALCON の式と一致していたのは `convexity` だけだった。

| op | Fullseye が計算していた式 | HALCON の式 |
|---|---|---|
| `circularity` | `4π·面積/周囲長²`(等周比) | `min(1, F/(π·max²))`、max = 重心→輪郭画素の最大距離 |
| `roundness` | `4·面積/(π·長軸²)` | `1 - σ/μ`(重心→輪郭距離の平均と標準偏差) |
| `rectangularity` | 面積 / **軸平行**外接矩形 | 同じ 1 次・2 次モーメントを持つ矩形との差を正規化 |
| `circularity_xld` | 等周比 | region 版と同じ |
| `compactness_xld` | `L²/(4πF)/10` を 1 で頭打ち | `max(1, L²/(4πF))` |
| `rectangularity_xld` | 面積 / 最小外接回転矩形 | region 版と同じ |

数で見ると、**順序まで変わる**:

| 形 | `circularity` 旧 | HALCON | `rectangularity` 旧 | HALCON |
|---|---|---|---|---|
| 円 r=24 | 0.916 | 0.991 | 0.747 | 0.809 |
| 正方形 40 | **0.826** | **0.670** | 1.000 | 1.000 |
| 矩形 16x64 | 0.529 | 0.311 | 1.000 | 1.000 |
| **同じ矩形を 30 度回す** | 0.459 | 0.307 | **0.359** | **0.998** |
| 細長 4x80 | 0.150 | 0.065 | 1.000 | 1.000 |

`rectangularity` は**同じ長方形を回しただけで 1.000 から 0.359 に落ちていた**。
`circularity` は正方形を「かなり円い」(0.826)と言うので、HALCON のレシピを移して
きて `circularity > 0.8` と書いた人は、ここでは正方形を通してしまう。

## なぜ門が通したか

★**説明文は正直だった。** 各 op は自分の式(`4π・面積/周囲長²` 等)を書いていた。
嘘は式ではなく「**HALCON の `circularity` に相当**」という一行の方にあり、
**被覆率の表もそれを数えていた**。門は「op が在るか」「値域に収まるか」「決定的か」を
見ていて、**名前が約束している量かどうか**は誰も見ていなかった。

★もう一つ: 探針が 1 枚だと出ない。円だけで試すと旧 `circularity` は 0.916、HALCON は
0.991 で「まあ近い」に見える。**正方形と回転した矩形**を混ぜて初めて、順序が変わる
ことと回転で崩れることが出る([[feedback_one_probe_input_is_not_coverage]])。

## 直し(2026-09-26 適用)

6 本とも HALCON の式に置き換えた。寸法を持つ量(`diameter_region` / `contlength` /
`get_region_thickness`)は触っていない —— そちらはこの repo の「特徴は解像度に
依らないよう正規化する」という既存の規約に従っており、**スケールの規約**であって
**別の量を計算している**のとは違う。

★**2 次モーメントで向きが決まらない形の扱い。** 正方形や円は共分散が等方なので
固有ベクトルが任意に決まり、モーメント矩形が 45 度回った状態で当たると正方形が
**0.651** になる。HALCON は「矩形なら 1 を返す」と明記しているので、これは実装の
不足である。等方なときは「同じモーメントを持つ矩形」が向きの数だけ在って定義が
向きを決めないので、重なりが最大になる向きを選んだ(正方形 1.000、20 度回しても
0.982 —— HALCON が明記する「最大 10% 過小評価」の範囲に収まる)。

## 残っているもの

`eccentricity` / `eccentricity_xld` は HALCON では **3 値**(Anisometry / Bulkiness /
StructureFactor)を返す演算子で、スカラーの `feature` 型では表せない。`area_center`
と同じ `match` 型への変更が要るので別の巡で直す。門の `_NOT_YET_HALCON` に理由つきで
名指ししてあり、「本当にまだ違う」ことを試験が確かめている(直ったら台帳から外れる)。
