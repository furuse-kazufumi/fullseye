---
id: frame-align-inlier-ratio-is-not-confidence
date: 2026-09-08
found_by: poc_print_registration
kind: silent-wrong
severity: high
where: [astrostack.py]
ops: [frame_align]
gate: [test_inlier_ratio_is_not_a_probability_that_the_answer_is_right, test_a_tie_in_the_smoothed_vote_no_longer_picks_an_empty_bin]
status: fixed
---

# 位置合わせが、賛成率 1.00 のまま 80.85 px 外していた

## 症状

網点のような**繰り返し構造**では、`frame_align` の `inlier_ratio` が **1.00 のまま 80.85 px 外す**。独立に再現した((0, 1.30) の真値に対し (54.24, 30.12) を返す)。例外は出ず、賛成率という「自信ありげな数字」だけが残る。

## なぜ門が通したか

賛成率は「同じ答えに賛成した点の割合」であって、**「答えが正しい確率」ではない**。格子状の構造では、間違った格子点にも同じだけ賛成が集まる —— **多数決が満場一致でも、投票所が間違っている**。試験は賛成率が高いことしか見ておらず、賛成率と正しさの相関を一度も測っていなかった。

## 直し

投票の**2 番手の山 / 1 番手**を `vote_margin` として返すようにした(網点 0.857〜1.000 / 星野 0.143 —— 繰り返し構造では 2 番手が肉薄する)。docstring に測った数字つきで警告を書いた。返り値の追加のみで既存の値は変えていない。
