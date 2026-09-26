---
id: functional-gate-did-not-know-the-match-sort
date: 2026-09-26
found_by: shape_factors_closed_form
kind: gate-gap
severity: medium
where: [verify_auto.py]
ops: [area_center, eccentricity, eccentricity_xld]
gate: [test_the_functional_gate_accepts_a_match_sort_vector, test_the_functional_gate_still_rejects_a_wrong_shape, test_the_headline_equals_the_union_of_its_parts]
status: fixed
---

# 機能ゲートが `match` ソートを知らず、正しい op を「実装されていない」と数えていた

## 症状

HALCON 対応の見出しが **979 から 977 に減った**。減らしたのは
`eccentricity` / `eccentricity_xld` を HALCON の 3 値に直した変更 —— 正しくしたのに
**対応数が減った**。

調べると、機能ゲート(`verify_auto._check_sort`)は `feature` と `contour` だけを
特別扱いし、**残りを「image / region = 2 次元配列」として検査していた**。`match`
(1 次元ベクトル。1 スカラーでは表せない組を運ぶ sort)はその枝に落ちて
``ndim=1`` で弾かれる。

★**`area_center` はずっと落ち続けていた。** この op は 2026 年の早い時期から
`match` を返しており、HALCON 対応数から静かに 1 本引かれていた。**数が減って初めて、
前から減っていたことが分かった** —— 同じ sort の op が 2 本増えて、初めて目に見える
大きさになったのである。

## なぜ門が通したか

★**門の検査に「知らない sort」の枝が無かった。** `if feature: ... if contour: ...`
の後が**無条件に**「image / region」の検査になっていて、`match` はそこへ黙って
流れ込む。知らないものを「知らない」と言わずに、既定の枝で処理していた ——
`else: raise` が在れば、`match` を足した日に気づけた。

もう一つ: **この門の出力は合否の数しか見ていなかった。** 「223 PASS / 4 FAIL」の
4 本の中身(`area_center ndim=1`)は毎回印字されていたのに、誰も読んでいない。
数だけを台帳に持つと、内訳が腐っても気づけない
([[feedback_a_verdict_without_the_detail_costs_another_run]])。

## 直し(2026-09-26 適用)

`_check_sort` に `match` の枝を足した —— 有限値の 1 次元ベクトルであること。

## 効き目

| | 対応数 |
|---|---|
| 直す前(`eccentricity` は誤った量、`area_center` は脱落) | 979 |
| `eccentricity` を 3 値にした直後(門が理解できず脱落) | 977 |
| 門を直したあと | **980** |

★**増えた 1 本は `area_center`**。`eccentricity` 2 本は元から数えられていた
(スカラーを返していたので `feature` として通っていた)ので差し引きゼロである。
**数字が上がったときこそ内訳を言う** —— 上がった理由は「実装が増えた」ではなく
「門が正しく数えられるようになった」だから
([[feedback_benchmark_honest_disclosure]])。
