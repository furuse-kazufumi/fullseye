# LinkedIn 投稿キット(数学の絵を定理で採点する話)

投稿するのは**人間**です。ここにあるのは下書きと、添える画像の指定と、出す前に
確かめることの一覧。**確かめずに貼らないこと** —— 数字は全部「その時点の実測」です。

- 最終更新: 2026-09-23
- リンク先: 英語版(一般公開)<https://qiita.com/furuse-kazufumi/items/dc100e7ea90e9575c40b> /
  日本語版(限定共有)<https://qiita.com/furuse-kazufumi/private/fe04f6eef40119913894>
- 画像: `docs/articles/assets/poc/poc_beats_fringes_and_screens/01_membrane.png`(膜の固有モード 5 枚。
  符号つきなので節線がはっきり出る)または
  `poc_what_a_picture_cannot_check/09_minimal.png`(極小曲面 4 種)。
  ※ **LinkedIn は GIF を動画に変換することがあり 1 枚目で止まって見える**ので、
  回る円の GIF(`poc_one_stroke_epicycles/07_epicycles.gif`)を使うなら
  投稿後に自分のフィードで再生を確認する。

## 切り口

**作ったものを先に、新しい結果を次に、教訓は記事側で読ませる。** この話の芯は
「数学の絵はきれいなので誰も確かめない」ではなく、**「絵の外に真値を置く方法が
ちゃんとある」**というほうです。失敗談から入ると何を作ったのか伝わりません。

数字は 1 つだけ選ぶこと。全部並べると読まれません。いちばん効くのは
**対照群のある数字**(極小曲面の |H| 0.0001 に対し球 1.00004・円柱 0.50000)です ——
「門が素通しでない」ことまで 1 行で言えるのはこれだけ。

## 本文(English)

```text
Mathematical pictures never get checked, because they already look right. A
slightly wrong implementation still packs circles, still spirals, and a Lorenz
plot is the same butterfly whether the integrator is 1st or 4th order.

So I built 32 drawing operators under one rule: ship it only if a theorem can
act as the gate, or an existing independent implementation supplies the truth.
Checking a formula against itself is not allowed.

What that buys you:
• "This is a minimal surface" is scored by an op that does not know how it was
  built — median |H| of 1e-4, against controls of 1.00004 (unit sphere) and
  0.50000 (unit cylinder). The gate is provably not a pass-through.
• The sum of the Lyapunov exponents matches the trace identity to 2.6e-06,
  independently of the tangent-flow/QR procedure that produced them.
• A print moiré and a two-slit fringe are the same beat, so the period is
  predicted in closed form before anything is drawn, then measured back by FFT.

The gates found four real defects in my own work — including a hatching routine
whose docstring said "follows the edges" while the code crossed them. You cannot
see that in the picture.

https://qiita.com/furuse-kazufumi/items/dc100e7ea90e9575c40b
```

```text
#ComputerVision #ScientificComputing #Python
```

## 出す前に確かめること

- [ ] リンク先が **一般公開**(`/items/`)になっているか。`/private/` だと読者によっては開けない。
- [ ] 画像が LinkedIn のプレビューで切れていないか(横長の図は上下が切られる)。
- [ ] 数字が記事の数字と一致しているか —— `|H|` 中央値 0.00002〜0.00014 / 球 1.00004 /
      円柱 0.50000 / トレース恒等式の差 2.57e-06 / モアレの実測比 0.948〜0.986。
- [ ] 「32 op」が記事と合っているか(定理の図 9 + 波動 6 + 力学系 6 + 様式化 6 + 極小曲面 5)。
