---
id: features-saturated-at-one
date: 2026-09-26
found_by: shape_factors_closed_form
kind: silent-wrong
severity: high
where: [backends_auto.py]
ops: [height_width_ratio, moments_region_2nd, moments_region_2nd_invar, moments_region_2nd_rel_invar, moments_region_3rd, moments_region_3rd_invar, moments_region_central, moments_region_central_invar, moments_xld]
gate: [test_a_region_feature_responds_to_at_least_one_deformation, test_a_contour_feature_responds_to_at_least_one_deformation, test_height_width_ratio_reports_tall_objects_honestly, test_the_moment_features_keep_growing_on_long_shapes, test_the_probe_would_catch_a_squashed_feature, test_the_constant_ledger_names_ops_that_really_are_constant]
status: fixed
---

# 特徴が 1.0 で頭打ちし、形が違うのに同じ数を返していた(9 op)

## 症状

`compactness` の頭打ちを直したあと、**同じ型が他にも無いか**を機械的に探した。
「単調に形を変える列を渡して、出力が止まる op」を数える探針で 9 本出た。

| op | 実測 | 真値 |
|---|---|---|
| `height_width_ratio` | 60x20 -> **1.000** / 160x4 -> **1.000** | 3.0 / 40.0 |
| `moments_region_2nd` ほか 7 本 | 幅 4・長さ 80 以上 -> **1.000** | 伸び続ける |

`height_width_ratio` がいちばん重い。**横長は正しく出るのに、縦長は全部 1.0**
—— 対象の向きが変わった瞬間に情報が消える。検査で縦長の部品を測っている人は、
どれも同じ数を受け取っていたことになる。

## なぜ門が通したか

★**「範囲に収まっていること」を確かめる門は、潰れていることを見ない。** 頭打ちは
値域も有限性も決定性もすべて満たす —— むしろ「きれいに収まっている」ように見える。

★**1 枚の探針では原理的に出ない。** 潰れを見つけるには「入力を変えたら出力も
変わるか」を問う必要があり、そのためには形を 1 つでなく**列**で渡さねばならない
([[feedback_one_probe_input_is_not_coverage]])。

★**`height_width_ratio` は、飽和を「仕様」として説明文に書いていた** ——
「高さが幅を超える領域では 1.0 に飽和してしまう(実装の非対称性)」。開示は
されていたが、**開示されたまま直されずに残っていた**。値域 [0,1] はそもそも
feature の契約ではない(`elliptic_axis` は 6.35、`r2_runlength_features` は 110)。

## 直し(2026-09-26 適用)

`min(1.0, ...)` を 3 か所(`aspect` / moments の表 / `moment_xld`)で外した。
`height_width_ratio` はこれで HALCON の Ratio と同じ量になる。

## 門

`tests/test_features_do_not_saturate_2026_09_26.py`。**6 つの族**(横長・縦長・三角・
L 字・穴・個数)を渡し、**どれか 1 つの族で動けば合格**とする。

★最初は「全族で動くこと」を求めて 31 本落としたが、その大半は**探針が対称すぎた**
だけだった —— 対称な矩形では奇数次モーメントが厳密に 0 になるのは正しい。非対称な
族と穴・個数の族を足したら、免除は 5 本まで減った(いずれも 2 輪郭を要する op や
定義上いつも同じ op)。**免除で逃げる前に、探針を疑う。**
