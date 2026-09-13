# LinkedIn 投稿キット(ハエの視覚モデルを体に載せた話)

投稿するのは**人間**です。ここにあるのは下書きと、添える画像の指定と、出す前に
確かめることの一覧。**確かめずに貼らないこと** —— 数字は全部「その時点の実測」です。

- 最終更新: 2026-09-14
- リンク先: 英語版 <https://qiita.com/furuse-kazufumi/items/638f0b0aa7865e17c67c> /
  日本語版 <https://qiita.com/furuse-kazufumi/items/331af639c2b9a1493576>
- 画像: `docs/articles/assets/fly/task_setup.png`(課題の全体像)または
  `dof_vs_generalisation.png`(自由度と般化)。
  ※ **LinkedIn は GIF を動画に変換することがあり 1 枚目で止まって見える**ので、
  歩行 GIF・3D GIF を使うなら投稿後に自分のフィードで再生を確認する。

## 切り口(2026-09-14 にユーザー指摘で修正)

最初の版は「検査に通ったのに歩いたら全滅した」という**失敗談だけ**で、何を作ったのかも
何が新しいのかも無かった —— 「何のアピールにもなっていない」。**作ったものを先に、
新しい結果を次に、失敗の教訓は記事側で読ませる**。長さは数行。

## 本文(English)

```text
I wired a connectome-constrained model of the fly visual system (65 cell types,
fixed wiring) into a physics-simulated fruit fly: compound eye → optic lobe →
steering → path integration, closed loop.

Two results worth the trouble:
• The measured connectome is worth 0.14-0.20 over a 1956 textbook motion
  detector on the same task — real, but not an order of magnitude.
• Evolving its 734 free parameters overfits on scarce data (-0.25 on held-out
  scenes). Compressing the same search into 260 per-cell-type modulations
  gives +0.71 — and matches the free version once data is plentiful.
  Fewer degrees of freedom, better generalisation.

https://qiita.com/furuse-kazufumi/items/638f0b0aa7865e17c67c
```

```text
#ComputerVision #Neuroscience #Robotics
```

## 本文(日本語)

```text
コネクトームで配線を固定したハエの視覚モデル(65 細胞型)を、物理シミュレータのハエに
載せました。複眼 → 視葉 → 操舵 → 経路積分まで閉ループで動きます。

やって良かった結果が 2 つ:
・同じ課題で 1956 年の教科書的な運動検出器と比べると、実測の配線の取り分は 0.14〜0.20。
  ゼロではないが桁違いでもない、と数字で言えた。
・自由パラメータ 734 個をそのまま進化させると少データで過適合(保留 −0.25)。同じ探索を
  細胞型ごとの 260 次元に圧縮すると +0.71 に般化し、データが増えれば 734 個版と同等。
  自由度を減らしたほうが般化する。

https://qiita.com/furuse-kazufumi/items/331af639c2b9a1493576
```

```text
#コンピュータビジョン #神経科学 #ロボティクス
```

## 出す前のチェックリスト

- [ ] **数字が記事と一致している。** 配線の取り分 0.14〜0.20(EMD+高域通過 0.84 対 flyvis 0.98、
      保留 C)/ フリー 734 次元・2 景色 −0.25 / ボトルネック 260 次元 +0.71 / 10 景色で 0.92 対 0.91。
      出典は `flyvis_vs_emd_*.json`、`evo_r1_summary.json`、`evo_bn_007.json`。
      合わなければ**文章のほうを直す**(丸めて合わせない)。
- [ ] **リンクが公開状態で 200。** 限定共有の `/private/` URL を貼らない。
- [ ] **ローカルパス・社内情報・私的なメモの ID が入っていない。**
- [ ] **誇張していない。** 「ハエの脳を再現した」と書かない —— 実測のコネクトームで配線が
      決まっているのは**視葉だけ**で、目の幾何・読み出し・行動・歩行は全部手書き。

## 出したあと

- 最初の 60 分の反応で伸びが決まるので、コメントには**その日のうちに**返す。
- 「どこまでが本物か」を聞かれたら、記事の経路図(`flybrain_model_map.png`)を出す。
  青い箱 1 つだけが実測、と一目で分かる。
- 反応が薄かったときに**投稿を消さない**。何が刺さらなかったかは次の材料。
