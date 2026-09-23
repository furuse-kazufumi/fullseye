---
id: pictures-that-carry-their-own-truth
title: 目が嘘をつく絵を作って、測る側を採点する(錯視・無限描画・循環動画)
title_en: Pictures that carry their own ground truth (illusions, endless drawing, seamless loops)
category: 描く
ops: [illusion_cafe_wall, illusion_muller_lyer, illusion_checker_shadow, illusion_kanizsa, illusion_fraser_spiral, illusion_ground_truth, perpetual_elementary_ca, perpetual_langtons_ant, perpetual_apollonian, perpetual_flow_field, perpetual_identities, perpetual_state, perpetual_step, perpetual_render, perpetual_loop, perpetual_loop_seam]
examples: [poc_illusions_and_perpetual_drawing]
version: 0.2.3
---

## できること

**真値が最初から付いている画像**を作ります。Fullseye のほとんどの op は与えられた
画像を測る側にいますが、この族だけが反対側にいます。

- **錯視 13 本** —— カフェウォールの目地は厳密に平行、ミュラー・リヤーの軸は厳密に
  等長、チェッカーシャドウの 2 マスは浮動小数として同じ値。**目が否定している
  不変量**を、生成器が数として返します(`illusion_ground_truth`)。
- **無限に描き続けるもの 12 本** —— 10 PRINT の迷路、基本セルオートマトン、
  ラングトンの蟻、アポロニウスの円詰め、カオスゲーム、流れ場、反応拡散。
  「いつ止めても途中」なので絵では採点できません。だから**絵とは独立に成り立つ
  恒等式**を持つものだけを入れ、`perpetual_identities` が 7 本まとめて実測を返します。
- **止めどきを決めない 3 本組** —— `perpetual_state` → `perpetual_step` →
  `perpetual_render`。1 万歩でも 1 億歩でも、途中で描いても構いません。
- **継ぎ目の無い循環動画** —— `perpetual_loop`。時間依存の量をすべて θ の関数に
  してあるので、継ぎ目は「消した」のではなく**最初から存在しません**。

新しい型語は 1 つも作っていません。返りは既存の `rgb` / `rgbvideo` / `table` だけで、
作った絵に既存の 2,000 以上の op がそのまま掛かります。

## What it does

Generates pictures that ship with their own ground truth: optical illusions whose
denied invariant is exact (parallel, equal-length, identical-valued), endless
generative systems whose correctness is an identity rather than an appearance, and
seamless loops where the seam is absent by construction rather than removed by
editing.

## 向くところ / 向かないところ

**向く**: 測る側の採点(錯視図には「正解」が付いてくる)、尽きない試験入力、周期
境界を持つ時間方向 op の素材、合成データの生成。

**向かない**: 作品としての完成度。この族には**主張が検算できる図**しか入れて
いません。美しいが検算できない図は、たとえ描けても入れていません。

## 最初の 1 本

```python
import fullseye as fs

# 目が「傾いている」と言う図で、目地の傾きを測る
img = fs.ledger.illusion_cafe_wall(size=40, rows=8, cols=10, shift=0.25)
gt = fs.ledger.illusion_ground_truth("cafe_wall")
print(gt["quantity"][0], "の真値は", gt["value"][0])     # mortar_slope の真値は 0.0

# 止めどきを決めない 3 本組
s = fs.ledger.perpetual_state("langtons_ant", size=301)
s = fs.ledger.perpetual_step(s, 12_000)
ant = fs.ledger.perpetual_render(s)

# 絵を見ずに採点する
ident = fs.ledger.perpetual_identities()
print(dict(zip(ident["system"], ident["residual"])))

# 継ぎ目の無い循環動画(比が 0 ではなく 1 に近いのが正解)
v = fs.ledger.perpetual_loop("plasma_orbit", frames=48, size=360)
print(float(fs.ledger.perpetual_loop_seam(v)["ratio"][0]))
```

## 裏づけ

恒等式 7 本の実測(`perpetual_identities`、`tests/test_generative.py` が門):

| 系 | 恒等式 | 残差 |
|---|---|---|
| 規則 90 | 第 n 行 = `C(n,k) mod 2`(リュカの定理) | `0.0e+00` |
| ラングトンの蟻 | 周期 104 で同じ斜め (2,2) を繰り返す | `0.0e+00` |
| ラングトンの蟻 | 高速道路は 104 歩で**正味ちょうど 12 マス**増やす | `0.0e+00` |
| アポロニウス | `(Σk)² = 2Σk²`(デカルトの円定理) | `1.2e-16` |
| 流れ場 | `div(curl ψ) = 0`(非圧縮) | `7.0e-17` |
| 反応拡散 | 餌も死も 0 なら総量保存 | `2.0e-16` |
| プラズマ | 4 隅は最後まで書き換えられない | `0.0e+00` |

錯視側は 12 枚すべてが「厳密に 0」の不変量を宣言し、実測も 0(カフェウォールの
目地の傾き、チェッカーシャドウ・同時対比の 2 パッチの差、カニッツァの錯覚輪郭上の
勾配)。循環動画の継ぎ目の比は 4 種で 0.997〜1.041。

**作る途中で 3 件の欠陥が出ました**(どれも絵を見ても気づけないもの): 二項係数を
`int64` で積んで `C(62,31)×31` で黙って溢れていた(リュカの定理に置き換え)、
チェッカーシャドウで対にするマスを間違えていた(差 0.31)、「104 歩で 52 マス」と
見当で書いた成長率が実測 0.114/歩 と合わず、測り直すと正味ちょうど 12 マスだった。
