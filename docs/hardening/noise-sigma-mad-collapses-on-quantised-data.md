---
id: noise-sigma-mad-collapses-on-quantised-data
date: 2026-09-08
found_by: poc_thermal_radiometry
kind: silent-wrong
severity: high
where: [astrostack.py]
ops: [noise_sigma, star_detect]
gate: [test_mad_warns_when_quantisation_collapses_it_to_zero, test_star_detect_refuses_instead_of_silently_finding_nothing]
status: fixed
---

# 頑健な雑音推定が整数画像で 0 に潰れ、点目標検出が黙って何も返さなくなっていた

## 症状

`noise_sigma(method="mad")` は整数値の画像で **σ=0.5 相当のとき 0.0000** を返す。返せる値は **1.4826 の倍数だけ**で、σ=1.0 も σ=1.983 も**同じ 1.4826**。14 bit の生 DN はまさに整数なので、これは特殊な入力ではない。下流の影響を独立に確認: 200x200 の整数フレームに**点目標を 2 個植えて `star_detect` が 0 個**を返した(例外なし)。

## なぜ門が通したか

★`star_detect` には `sigma <= 0` の門が**在った**。しかしコメントは「**完全に平坦** = 雑音が測れない」と書いていて、**前提のほうが間違っていた** ——σ が 0 になる道はもう 1 本あり、そのとき画像は平坦ではない。しかも `_robust_background` のコード内コメントには「MAD が 0 に潰れる量子化された画像向け」と `clip` の存在が書かれていた —— **知識は在ったが、読む側(docstring と既定値)に無かった**。既定は `method="mad"` のままだった。

## 直し

道を分けた。値を返す入口の `noise_sigma` は拒否せず **`RuntimeWarning`**(呼び手が `method="clip"` を選べる)。答えを出す `star_detect` は、**平坦なら空(星が無いのは正当な答え)、平坦でないなら拒否**する —— 空を返すのは保守的な答えではなく誤った答えだから。実測: 同じフレームで `method="clip"` に替えると植えた 2 個がちゃんと出る(重心は量子化雑音に引かれて最大 0.7 px ずれる。丸めて「ぴったり」に見せない)。既存の 15 本の呼び手(PoC・ツアー)はすべて影響なしを実行で確認した。
