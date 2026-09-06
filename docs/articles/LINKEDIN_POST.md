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

## 本文(English / 主)—— 130 語

**★長さについて(2026-09-06 にユーザーから2 点の指摘 —— 「長い文だな、誰も
読まないだろ」「furuse.work のリンクも無い」)。** 最初の版は 350 語あり、
リンクも `furuse.work` と平文で書いていてクリックできなかった。フィードで
折りたたまれる前に見えるのは**冒頭 2 行だけ**なので、そこに結論を置き、
本文は 130 語に落とし、**リンクは `https://` 付きで 1 本だけ**にした。
多言語の話も落とした —— 主張と関係が無く、字数を食うだけだった。

```text
The best-looking number came from the worst setup.

Sizing particles from images — threshold, connected components, report D50.
I swept the density and the D50 error went from -4.9 % to +4.5 %.

It crosses zero at 13.8 %. That looked like the optimal operating point.
It wasn't: 28 merged blobs pulling the size up, 19 edge-clipped ones pulling
it down. Two failures cancelling.

The clean, sparse sample reported a *bigger* error.

The obvious fix - drop the low-solidity blobs - overcorrected to -11.3 %.
Worse than doing nothing.

So: count failure modes separately, and distrust a metric that crosses zero.
A monotone error is a bias you can correct. One that crosses zero is usually
two things fighting.

45 worked examples like this, each with a ground truth and a null model:
https://furuse.work
```

**ハッシュタグ(3 個。多いと逆に届かない)**

```
#ComputerVision #Metrology #OpenSource
```

**1 コメント目**(本文のリンクは 1 本に絞ったので、残りはここへ):

```text
Source: https://github.com/furuse-kazufumi/fullseye
This one is examples/poc_particle_sizing.py - it prints every number in the
post, so you can disagree with me by running it.
```

---

## 本文(日本語 / 従)

```text
いちばん良く見えた数字が、いちばん悪い条件から出ました。

画像から粒度分布を出す仕事です。しきい値 → 連結成分 → D50。密度を振ると
D50 の誤差は -4.9 % から +4.5 % へ動きます。

13.8 % で 0 を横切る。最適な条件に見えます。違いました。融合した塊 28 件が
大きい側へ、縁で切れた 19 件が小さい側へ引いて、打ち消し合っていただけです。

きれいに空いた標本のほうが、誤差は大きい。

当たり前の対策(充填率の低い塊を捨てる)は -11.3 % へ行き過ぎました。
何もしないより悪い。

だから、誤差ではなく壊れ方を別々に数える。そして 0 を横切る指標を疑う。
単調な誤差は補正できる偏りですが、0 をまたぐ誤差はたいてい 2 つのものが
押し合っています。

こういう実例が 45 本、どれも真値とゼロ点つきで置いてあります:
https://furuse.work
```

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
