---
id: halcon-named-shape-factors
date: 2026-09-26
found_by: shape_factors_closed_form
kind: silent-wrong
severity: high
where: [backends_auto.py]
ops: [circularity, roundness, rectangularity, circularity_xld, compactness_xld, rectangularity_xld, eccentricity, eccentricity_xld]
gate: [test_the_op_returns_the_halcon_quantity, test_rectangularity_is_one_for_rectangles_whatever_the_angle, test_rectangularity_is_one_for_a_square, test_the_old_isoperimetric_formula_is_what_the_gate_catches, test_the_old_axis_aligned_extent_is_what_the_gate_catches, test_the_contour_twin_answers_the_same_question, test_every_same_named_shape_factor_is_either_checked_or_named, test_eccentricity_returns_the_three_halcon_values, test_eccentricity_is_one_one_zero_for_a_circle, test_the_old_scalar_eccentricity_is_what_the_gate_catches, test_the_contour_eccentricity_uses_moments_not_a_point_fit]
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

## 追補(同じ日): `eccentricity` は 3 値のどれでもなかった

HALCON の `eccentricity` は**3 値**を返す演算子である:

    Anisometry      = Ra / Rb                 (円で 1、下限 1)
    Bulkiness       = π·Ra·Rb / A             (円で 1)
    StructureFactor = Anisometry·Bulkiness - 1 (円で 0)

この op が返していたのは skimage の離心率 `sqrt(1-(b/a)²)` —— **3 つのどれでもない**。
円で 0.0(HALCON は 1.0)、4x80 の棒で 0.999(HALCON の Anisometry は 20.65)。
1 スカラーでは 3 値を表せないので、`area_center` と同じ `match` ソートに変えた。
領域が空でも 3 成分を返す(成分数が入力で変わると受け取る側の形が壊れる)。

★**輪郭版はもう一段ずれていた。** `cv2.fitEllipse` は輪郭「点」への最小二乗当てはめ
で、HALCON の定義は**囲まれた面積の幾何モーメント**から導く方である。4x80 の棒で
Anisometry 39.1 対 20.65 —— 2 倍近い。モーメント由来に直して、領域版と 3% 以内で
一致するようになった。

★**`/10` の押し潰しは、これで 3 例目だった**(`compactness` / `compactness_xld` /
`elliptic_axis`)。`elliptic_axis` が返しているのは **Anisometry を 10 で割ったもの**
—— つまり**別の演算子の出力**を、勝手なスケールで縮めたもの。

## 残っているもの

`elliptic_axis`(HALCON は Ra, Rb, Phi)と `diameter_region`(HALCON は両端点と
Diameter = 輪郭 2 点間の最大距離)は、どちらも**画素の長さ**を含む。この repo は
寸法を持つ特徴を画像サイズで正規化する規約を持っており(`area_center` の註に明記)、
`diameter_region` / `get_region_thickness` / `contlength` がそれに従っている。

**どちらに合わせるかは 1 op の話ではなく規約の選択**である —— HALCON のレシピを
移す人にとっては、正規化も式の違いと同じだけ「数が合わない」原因になる。判断を
仰ぐため、門の `_NOT_YET_HALCON` に理由つきで名指しし、「本当にまだ HALCON の量では
ない」ことを試験が確かめている(直ったら台帳から外れる)。
