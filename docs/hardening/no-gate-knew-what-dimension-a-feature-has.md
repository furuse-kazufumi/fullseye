---
id: no-gate-knew-what-dimension-a-feature-has
date: 2026-09-26
found_by: scale_law_of_features
kind: gate-gap
severity: high
where: [tests/]
ops: [area_center, contlength, diameter_region, get_region_thickness, elliptic_axis, moments_region_2nd, moments_region_3rd, moments_region_central]
gate: [test_the_feature_follows_its_declared_scale_law, test_every_region_feature_op_declares_a_scale_law, test_the_moment_ops_carry_halcons_dimension, test_the_law_would_catch_a_normalised_feature]
status: fixed
---

# どの門も「その特徴が何の次元を持つか」を知らなかった

## 症状

2026-09-26 に 8 op を HALCON の画素値へ直した。直し方は HALCON のリファレンスを
読み、閉形式と突き合わせることだった —— **外の一次情報が無ければ出なかった**。

ところが後から測ると、そのうち **5 本は HALCON の数値を一つも使わずに出ていた**。
「k 倍に拡大したら値は k^p 倍になる」という指数 p が、宣言と食い違うからである:

| op | 直す前の実測 p | その量の次元 |
|---|---|---|
| `area_center` の面積 | 0(画布で割っていた) | 面積 = 2 |
| `contlength` | 0 | 長さ = 1 |
| `get_region_thickness` | 0 | 長さ = 1 |
| `diameter_region` | 0 | 長さ = 1 |
| `elliptic_axis` | 0(Anisometry/10 を返していた) | 長さ = 1 |

そして同じ 1 枚が、まだ開いている `docs/KNOWN_ISSUES.md` §52 も指している ——
`moments_region_2nd` の実測は **p=0.001**、HALCON の同名演算子は正規化しない
中心モーメントなので **p=4** でなければならない。

## なぜ門が通したか

★**門は「値が妥当か」を見ていて、「その値が何の量か」を見ていなかった。** 値域・
有限性・決定性・再現性はすべて確かめられていたが、**次元**を確かめる門が 1 枚も
無かった。次元が違えば、値がどれだけきれいでも別の量である。

★**一律の変成関係では出ない。** 「平行移動で変わらない」を全 op に当てると 35 本中
30 本が違反し、そのほとんどは**違反して当然**だった(重心は動くのが正しく、個数は
尺度不変が正しい)。免除が 30 本になる門は門ではない。効くのは「その量が何の次元を
持つか」を **op ごとに宣言**させることで、それは指数 1 つで書ける。
文献側でもここが難所として研究されている(手元の調査コーパス `test_oracle_corpus_v2` では MR の同定・選択に 51 件)。

## 直し(2026-09-26 適用)

`tests/test_scale_law_2026_09_26.py`。領域を受けて数を返す **35 op すべて**に、
成分ごとの尺度指数を宣言させる表を置いた。

* 拡大は ``np.kron``(整数倍・補間なし)。二値マスクを任意角で回すと周囲長が
  3.8 倍荒れるが、整数倍の拡大は補間を伴わないので**期待値を厳密に書ける**。
* 2 倍と 3 倍の両方で測り、**同じ指数になること**も見る(冪則でない量を弾く)。
* 周囲長を経由する量だけ許容差を 0.08 に広げ、理由を名前で残した
  (ラスタ化の偏り、`docs/KNOWN_ISSUES.md` §50)。
* **完全性の門**: 表に載っていない op があれば落ちる。新しい op を足した人に
  「その量は長さか、面積か、無次元か」を宣言させる —— 一つずつ試験を書く運用だと、
  書かなければ何も見ない([[feedback_one_probe_input_is_not_coverage]] への構造的な手当て)。
* **§52 は免除にせず `strict xfail`** で開いたまま持つ。直った瞬間に「予期せぬ成功」
  で落ち、表の更新を要求する。免除台帳に畳み込むと**直ったことに誰も気づけない**。

## 門を壊して確かめた

`contlength` に「画布で割る」種を植え直して実行 —— 落ちたのは
`test_the_feature_follows_its_declared_scale_law[contlength]` **1 本だけ**で、
自己検算は通った(自己検算が被検 op を経由していると、op が壊れたとき**二重に
正規化**して紛らわしい落ち方をする。最初はそうなっていたので、周囲長を自前で
数える形に切り離した)。

## 展示

`examples/scale_law_of_features.py` —— 35 op の次元を表にし、そのうえで
「**同じ op でも画布で割った瞬間に別の量になる**」ことをその場で見せる
(画素なら p=1.015、割ると p=0.015)。名前は変わらないので、値域や有限性を見る門は
どちらも通す —— 次元を見る門だけが区別できる。

## 来歴

この手口には名前がある —— **metamorphic relation**。真値が手に入らないプログラムを
検算する古典的な道具で、`Pseudo-oracles for non-testable programs`(Weyuker 1981)、
`Metamorphic Testing and Its Applications`(Chen 2004)に遡る。
2026-09-26 に作った調査コーパス `test_oracle_corpus_v2`(1,598 件)から引いた。
