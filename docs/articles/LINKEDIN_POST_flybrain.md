# LinkedIn 投稿キット(ハエの視覚モデルを体に載せた話)

投稿するのは**人間**です。ここにあるのは下書きと、添える画像の指定と、出す前に
確かめることの一覧。**確かめずに貼らないこと** —— 数字は全部「その時点の実測」です。

- 最終更新: 2026-09-14
- リンク先: 英語版 Qiita <https://qiita.com/furuse-kazufumi/items/638f0b0aa7865e17c67c> /
  日本語版 <https://qiita.com/furuse-kazufumi/items/331af639c2b9a1493576>
- 画像: `docs/articles/assets/fly/task_setup.png`(課題の全体像)または
  `docs/articles/assets/fly/dof_vs_generalisation.png`(自由度と般化)。
  ※ **LinkedIn は GIF を動画に変換することがあり、1 枚目で止まって見える**ので、
  歩行 GIF や 3D GIF を使うなら投稿後に自分のフィードで再生を確認する。事故が少ないのは静止画。

---

## なぜこの切り口にしたか(先に読む)

記事には結果が 10 個ありますが、**フィードで指が止まるのは「自分もやっているかもしれない失敗」**
だけです。そこで軸は 1 つ ——

> **自分で書いた検査に全部通ったモデルが、動き出した瞬間に全滅した。**

学習済みモデルを自分の系に載せる人なら誰でも身に覚えがある形です。コネクトームも進化も
ゲノム的ボトルネックも、この投稿では**出しません**(記事で読んでもらう)。規模の数字
(「20 実験」「721 列」)も見出しに置きません —— 書き手の都合であって読み手の道具ではないからです。

---

## 本文(English / 主)—— 約 140 語

```text
The model passed every test I wrote. Then it started walking.

A connectome-constrained model of the fly visual system, mounted on a
simulated fly body. I calibrated it by spinning the fly in place:
monotonic, symmetric, 0.11 s latency. Every check passed.

Walking, the same readout scored 0.06-0.51. Total failure.

The model was fine. The world wasn't. With the eyes 1.2 mm above the
floor, the ground streams past at 330-1000 deg/s, outside the motion
detectors' passband. Read only above the horizon: correlation 0.98.

Then the part that stung. Feeding that 0.98 sensor into steering changed
arrivals from 7/12 to 6/12. Nothing.

A test built under different motion than your deployment guarantees
nothing. Neither does sensor fidelity.

Every number here comes from a measured run:
https://qiita.com/furuse-kazufumi/items/638f0b0aa7865e17c67c
```

**ハッシュタグ(3 個。多いと逆に届かない)**

```text
#ComputerVision #Neuroscience #Robotics
```

**1 コメント目**(本文のリンクは 1 本に絞ったので、残りはここへ)

```text
Japanese version: https://qiita.com/furuse-kazufumi/items/331af639c2b9a1493576

Two more results in the write-up. Textbook 1956 motion detection plus a
high-pass stage reaches 0.84 on held-out scenes; the connectome-constrained
model reaches 0.98 - so the measured wiring is worth 0.14-0.20, not an order
of magnitude. And evolving 734 free parameters on 2 scenes overfits to -0.25
on held-out scenes, while folding the same search into 260 per-cell-type
modulations gives +0.71. Fewer degrees of freedom, better generalisation.
```

---

## 本文(日本語 / 従)

```text
自分で書いた検査に全部通ったモデルが、歩き出した瞬間に全滅しました。

コネクトームで配線を固定したハエの視覚モデルを、シミュレータのハエの体に
載せた話です。その場で回して較正したところ、単調・左右対称・遅れ 0.11 秒。
検査は全部合格でした。

歩かせると、同じ読み出しが相関 0.06〜0.51。全滅です。

悪かったのはモデルではなく世界でした。目が床から 1.2 mm の高さにあると、
足元の床は 330〜1000 度/秒で流れ、運動検出器の帯域を超えます。地平線より
上だけを読むと 0.98。

こたえたのはその次です。相関 0.98 のセンサを操舵に足しても、到達は
12 本中 7 → 6 本。変わりません。

本番と違う運動条件で作った検査は、通っても何も保証しない。センサの忠実度も
同じです。数字はすべて実測から:
https://qiita.com/furuse-kazufumi/items/331af639c2b9a1493576
```

---

## 出す前のチェックリスト

- [ ] **数字が記事と一致している。** 0.11 秒 / 0.06〜0.51 / 1.2 mm / 330〜1000 度/秒 /
      0.98 / 7 本 → 6 本(12 本中)。出典は `flyvis_loop2_*.json` と実験台帳。
      合わなければ**文章のほうを直す**(丸めて合わせない)。
- [ ] **1 コメント目の数字も一致している。** EMD + 高域通過 0.84(保留 C)/ flyvis 0.98 /
      配線の取り分 0.14〜0.20 / フリー 734 次元 2 景色 −0.25 / ボトルネック 260 次元 +0.71。
- [ ] **リンクが生きている。** 英語版・日本語版とも公開状態で 200。限定共有の
      `/private/` URL を貼らない(他人から開けない)。
- [ ] **リンクの向こうが英語で読める。** 本文のリンクは英語版 1 本にしてある。
- [ ] **ローカルパス・社内情報・私的なメモの ID が 1 つも入っていない。**
- [ ] 画像を添付した。GIF を使ったなら**投稿後に自分のフィードで再生されるか**を見る。
- [ ] **誇張していない。** 「ハエの脳を再現した」と書かない —— 実測のコネクトームで
      配線が決まっているのは**視葉だけ**で、目の幾何・読み出し・行動・歩行は全部手書き。
      「世界初」「最速」も書かない。

## 出したあと

- 最初の 60 分の反応で伸びが決まるので、コメントには**その日のうちに**返す。
- 「どこまでが本物か」を聞かれたら、記事の「何が実物で、どこからが手書きか」の表と
  経路図(`flybrain_model_map.png`)を出す。青い箱 1 つだけが実測、と一目で分かる。
- 「ハエ以外でも同じか」を聞かれたら、**主張しているのは手続きのほう**だと答える ——
  検査は本番と同じ運動条件で作る、センサと行動を別々に測る、自由度は構造の単位で削る。
- 反応が薄かったときに**投稿を消さない**。何が刺さらなかったかは次の材料。
