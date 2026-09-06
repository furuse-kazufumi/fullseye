# LinkedIn 投稿キット(Fullseye)

投稿するのは**人間**です。ここにあるのは下書きと、添える画像の指定と、
出す前に確かめることの一覧。**確かめずに貼らないこと** —— 数字は全部
「その時点の実測」なので、日が経つと合わなくなります。

- 最終更新: 2026-09-06
- リンク先: <https://furuse.work/>(ドキュメント索引)/
  <https://github.com/furuse-kazufumi/fullseye> / `pip install fullseye`
- 画像: `docs/articles/assets/fullseye_mosaic.png`(1200x1200、フィード向け)
  ※ 動く扉絵 `fullseye_hero.gif` もあるが、**LinkedIn は GIF を動画に
  変換することがあり、1 枚目で止まって見える場合がある**。静止画のほうが
  事故が少ないので既定は mosaic。GIF を試すなら投稿後に自分の目で再生を確認する。

---

## なぜこの切り口にしたか(先に読む)

**規模の数字を見出しにしない。** 「1,500 オペレータ」「45 本の PoC」は
書き手の都合であって、読み手が明日使えるものではありません。フィードで
指が止まるのは**「自分もそれをやっているかもしれない」と思える失敗**です。

そこで軸は 1 つだけ ——
**「向きの逆な 2 つの失敗は打ち消し合う。まとめた 1 つの数字はそのとき
いちばん良く見える」**。粒度分布でも細胞計数でも寸法検査でも同じ形で出る、
測る仕事なら誰にでも刺さる話です。ツールの紹介はその**あと**に置きます。

---

## 本文(English / 主)

> Last week I measured the same thing two ways and got the "best" answer from
> the worst setup.
>
> I was sizing particles from images — the standard chain: threshold, connected
> components, report D10/D50/D90. I swept the area fraction from 2 % to 28 % and
> watched the D50 error go from −4.9 % to +4.5 %.
>
> Somewhere in the middle it crossed zero. At 13.8 % area fraction the D50 error
> was +0.55 %. If I had reported that single number, this would have been my
> "optimal" operating point.
>
> It wasn't optimal. It was two failures cancelling.
>
> Touching particles merge into one blob, which pulls the size distribution up.
> Particles clipped by the frame edge get measured short, which pulls it down.
> At 13.8 % there were 28 merged blobs and 19 clipped ones out of 140. The two
> errors happened to be the same size. The summary number had no idea.
>
> The thinnest condition I tested — 1.9 % area fraction, almost nothing touching —
> reported a *larger* error (−4.9 %). By D50 alone, the crowded slide beats the
> clean one.
>
> Two things I now do differently:
>
> 1. Count the failure modes separately, not just the error. Merged blobs and
>    clipped blobs are different defects with different fixes; a single RMSE or
>    bias number folds them together and hides both.
> 2. Be suspicious of a metric that crosses zero. Monotone error is a bias you
>    can correct. Error that crosses zero is usually two things fighting.
>
> The obvious fix — detect merged blobs by their low solidity and drop them —
> made it worse, by the way. It moved D50 from +6.5 % to −11.3 %, because merged
> blobs also contain the genuinely large particles. Overcorrection is a failure
> mode too.
>
> This is one of 45 worked examples in Fullseye, an Apache-2.0 image-processing
> and 3-D measurement toolkit I build in the open. Every example ships with a
> closed-form or synthetic ground truth and a null model, because "our method
> scored 0.9" means nothing until you know what doing nothing scores.
>
> Docs (now in Japanese, English, 简体中文, 繁體中文, 한국어 and Deutsch):
> furuse.work · `pip install fullseye`
>
> What is the metric in your field that everyone quotes and nobody decomposes?

**ハッシュタグ(3〜5 個まで。多いと逆に届かない)**

```
#ComputerVision #MachineVision #Metrology #OpenSource
```

**1 コメント目に置くもの**(LinkedIn は本文の外部リンクを抑制する傾向があるので、
リンクは本文に 1 つだけ残し、詳細は最初のコメントへ):

> Source and the 45 worked examples:
> https://github.com/furuse-kazufumi/fullseye
> The particle-sizing one is `examples/poc_particle_sizing.py` — it prints every
> number in the post, so you can disagree with me by running it.

---

## 本文(日本語 / 従)

> 同じものを 2 通りで測って、いちばん悪い条件から「いちばん良い答え」が出ました。
>
> 画像から粒度分布(D10/D50/D90)を出す、という定番の仕事です。しきい値 → 連結成分
> → 物体ごとに測る。面積率を 2 % から 28 % まで振ると、D50 の誤差は −4.9 % から
> +4.5 % へ動きました。
>
> 途中で 0 を横切ります。面積率 13.8 % のとき D50 の誤差は +0.55 %。この 1 つの
> 数字を報告していたら、ここが「最適な条件」として通っていました。
>
> 最適ではありません。**向きの逆な 2 つの失敗が釣り合っていただけ**です。
>
> 触れ合った粒子は 1 個の塊に融合して分布を大きい側へ引き、視野の縁で切れた粒子は
> 小さく測られて逆へ引く。13.8 % のとき、塊 140 個のうち融合 28 件・縁切れ 19 件。
> たまたま同じ大きさだった、というだけです。要約した数字はそれを知りません。
>
> いちばん薄い条件(面積率 1.9 %、ほとんど触れていない)のほうが誤差は**大きい**
> (−4.9 %)。D50 だけを見れば、混んだ標本が空いた標本に勝ちます。
>
> それ以来こうしています。
>
> 1. **誤差ではなく、壊れ方を別々に数える。** 融合と縁切れは原因も直し方も違うのに、
>    RMSE や偏りに畳むと両方とも見えなくなります。
> 2. **0 を横切る指標を疑う。** 単調な誤差は補正できる偏りですが、0 をまたぐ誤差は
>    たいてい 2 つのものが押し合っています。
>
> ちなみに、当たり前の対策 —— 充填率(solidity)が低い塊を融合とみなして捨てる ——
> は**悪化させました**。D50 は +6.5 % から −11.3 % へ。融合した塊には本当に大きい
> 粒子も混ざっているからです。**過剰補正もまた失敗の型**でした。
>
> これは Fullseye(Apache-2.0 の画像処理・3-D 計測ツールキット)に入っている
> 45 本の実例のうちの 1 本です。どの例も**真値を閉形式か合成で厳密に持ち、
> ゼロ点(何もしない場合)を必ず併記**します。「うちの手法は 0.9 出ました」は、
> 何もしなかったときの点数を知るまで意味を持たないので。
>
> ドキュメント(日本語・English・简体中文・繁體中文・한국어・Deutsch):
> furuse.work / `pip install fullseye`
>
> あなたの分野で、みんなが引用するのに誰も内訳を見ない指標は何ですか?

---

## 出す前のチェックリスト

- [ ] **数字を測り直した。** `py -3.11 examples/poc_particle_sizing.py` を走らせ、
      −4.9 % / +4.5 % / 13.8 % / +0.55 % / 28 件 / 19 件 / 140 個 / +6.5 % /
      −11.3 % が**いま出る値と一致**することを確認する。合わなければ**文章の
      ほうを直す**(数字を丸めて合わせない)。
- [ ] **45 本という本数が合っている。** `ls examples/poc_*.py | wc -l`。
- [ ] **多言語の行が本当か。** `docs/README.en.md` `.zh.md` `.tw.md` `.ko.md`
      `.de.md` が **push 済み**で、furuse.work から切り替えられることを実際に
      ブラウザで確認する。**まだなら多言語の 1 行を消してから投稿する。**
- [ ] **リンクが生きている。** furuse.work が 200 で開き、PyPI の
      `pip install fullseye` が現行版であること。
- [ ] **ローカルパス・社内情報・私的なメモの ID が 1 つも入っていない。**
- [ ] 画像を添付した(`fullseye_mosaic.png`)。GIF を使うなら**投稿後に自分の
      フィードで再生されるか**を見る。
- [ ] 誇張していない。「世界初」「最速」「HALCON を超えた」は書かない ——
      この repo の HALCON 実装カバレッジは 269/2313 で、それが事実。

## 出したあと

- 最初の 60 分の反応で伸びが決まるので、コメントには**その日のうちに**返す。
- 「どの op を使ったのか」を聞かれたら、`fs.ledger.blob_label` →
  `blob_features` → `blob_select` の 3 つと、ガイド
  <https://furuse.work/ops/blob/guides/blob_analysis.html> を出す。
- 反応が薄かったときに**投稿を消さない**。何が刺さらなかったかは次の材料。
