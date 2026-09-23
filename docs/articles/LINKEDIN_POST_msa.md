# LinkedIn 投稿キット(測る側を測る —— 規格の公表値が 5 件を出した話)

投稿するのは**人間**です。ここにあるのは下書きと、添える画像の指定と、出す前に
確かめることの一覧。**確かめずに貼らないこと** —— 数字は全部「その時点の実測」です。

- 最終更新: 2026-09-23
- リンク先: 英語版(一般公開)<!-- 投稿後に URL を入れる --> /
  日本語版(限定共有)<!-- 投稿後に URL を入れる -->
- 画像: `docs/articles/assets/poc/poc_measurement_system_analysis/01_scene.png`
  (ゲージ R&R の古典的な見せ方 —— 部品ごとに測定値を縦に並べたもの。
  塊の離れ方と太さの比だけで「その測定器は使えるか」が読める)。
  対案 = `07_coverage_staircase.png`(規格の切り捨てが階段になる図。
  「手順の順序が答えを動かす」を 1 枚で言える)。
  ※ **LinkedIn は GIF を動画に変換することがあり 1 枚目で止まって見える**ので、
  `12_breakdown_movie.gif` を使うなら投稿後に自分のフィードで再生を確認する。

## 切り口

**作ったものを先に、新しい結果を次に、教訓は記事側で読ませる。** この話の芯は
「私の実装にバグがあった」ではなく、**「合成の検査には原理的に映らない層がある」**
というほうです。自虐から入ると何を作ったのか伝わりません。

数字は 1 つだけ選ぶこと。いちばん効くのは**乱数を使わない真値**です ——
停留点での 95 % 点が `2u²ln20 = 149.79×10⁻⁶` という閉形式で出て、規格の公表値 150 と
合う。モンテカルロの結果を「だいたい合った」と言うのとは別の強さがあります。

「52 件が緑のまま 5 件落ちた」は見出しとして強いので、本文の 2 行目までに置く。

## 本文(English)

```text
I added nine operators for gauge R&R and measurement uncertainty (GUM) to my
image-metrology library, and graded them the way this repo always does: a test
is only allowed to use a theorem, or a separate existing implementation, as its
ground truth. Never the formula being tested.

52 tests built that way. All green.

Then I ran the worked examples printed in the standards. Five failed.

All five were the same shape of defect — missing specification:
• no path to pool a non-significant interaction (repeatability off by 7.3 %)
• reading the t-table without truncating the effective dof first (k 2.1132 vs 2.12)
• a docstring claim that was simply false: dropping correlation "underestimates"
  uncertainty. On one real example it overestimated resistance by 2.8x while
  underestimating reactance. Same data, opposite directions.

A synthetic test can only check that code does what I specified. What sits
outside my specification is invisible to it in principle. A published worked
example is the one answer written independently of my derivation.

The sharpest tool turned out to be an exact solution. Where the law of
propagation collapses (a stationary point, where every sensitivity coefficient
is zero), the true 95 % point is a closed form: 2u^2 ln20 = 149.79e-6, matching
the standard's published 150 with no random numbers anywhere. That let me prove
two identical-looking validation failures had opposite causes — one was estimator
jitter, the other was error of the method itself.

So the tool returns u = 0 there, because that is the correct law-of-propagation
answer. It just refuses to do it silently: guf_valid=False travels with the
result, because a warning gets swallowed and a caller reads u = 0 as "the
measurement was perfect".

Write-up, figures and code in the comments.
```

## 出す前に確かめること

- [ ] 記事 2 本(en 一般公開 / ja 限定共有)が投稿済みで、URL が上に入っている
- [ ] 添える画像が master に載っていて、raw URL が HTTP 200 を返す
- [ ] 数字の再確認: EV 0.199933(公表一致)/ k 2.1132 → 2.12 / 相関 2.8 倍 /
      `2u²ln20 = 149.79e-6`(公表 150)/ 合成の門 52 件・最終 55 件
- [ ] 規格名・版を本文に書かない(リンク先の「出典」に正式名がある)
- [ ] 1 本目のコメントに記事リンク、2 本目に GitHub の PoC へのリンク
