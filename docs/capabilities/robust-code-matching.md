---
id: robust-code-matching
title: 照明むら・ハイライト・遮蔽に強いテンプレート照合(明るさの変化の向きを符号にして比べ、決まらないテンプレートは拒否する)
title_en: Template matching that survives uneven light, highlights and occlusion (compare the direction of brightness change as codes, and refuse templates that cannot fix a position)
category: 見つける
ops: [ocm_match, isc_match, scc_match, orientation_code, increment_sign, radial_reach_filter]
examples: [poc_code_matching_breakdown]
version: 0.6.1
inputs: [image2d]
pipeline: [isc_match, ocm_match]
alternatives: [scc_match, ncc_locate, radial_reach_filter]
limits: 回転には弱い(4 種とも 7〜9° で当たりが半分を割る。回転を探す方向符号ヒストグラムの系統は無い)。スケール変化も探さない。平坦な所の多いテンプレートは拒否されるか、SCC では採点できる位置が減る。SCC は「符号の合った画素だけを選ぶ」ので無関係な位置でも相関が高めに出る(選択の偏り)。既定の床でそれを抑えても OCM・ISC には届かない。RRF は背景が平坦な画素を判定しない(空・無地の壁)。
calibration: 座標は画素(テンプレート中心、find_ncc_model と同じ規約)。閾値 grad_thresh・flat_thresh・t_p は [0, 1] の明るさで書く(8 ビットなら 255 で割る)。
---

# 照明むら・ハイライト・遮蔽に強いテンプレート照合

## できること

明るさの**値**ではなく**変化の向き**を符号にして比べる照合の族(`codematch`、6 op)。学習した特徴を使わず、式と閾値だけで、
どこまで残りどこで壊れるかを自分で言えます。

- `ocm_match`: 方向符号照合(勾配の向きを 16 段に。巡回差の平均。Ullah・Kaneko・Igarashi 2001)。
- `isc_match`: 増分符号相関(隣の画素との増分の符号の一致率。Kaneko・Murase・Igarashi 2002)。狭義単調な明るさの変換で点数地図が 1 ビットも変わらない。
- `scc_match`: 選択的相関係数(符号の一致した画素の組だけで正規化相関、拡張マスクつき。Kaneko・Satoh・Igarashi 2003)。
- `orientation_code` / `increment_sign`: 符号だけを取り出す口。
- `radial_reach_filter`: 背景との比較(8 方向の reach の符号。Satoh・Kaneko・Niwa・Yamamoto 2004)。照明が全体に変わっても、影の内側でも前景にしない。

平坦なテンプレート(符号が雑音で決まる)には値を返さず `ValueError`。NCC は同じテンプレートでも高い相関でどこかを返します
(PoC: 空を切った 11 枚で NCC は 10 枚を外し、相関の中央値は 0.82。符号系 3 種の誤答は 0)。

## What it does

Six ops (`codematch`) match on the direction of brightness change instead of its value: orientation code matching (OCM), increment
sign correlation (ISC, exactly invariant to any strictly monotone brightness map), the selective correlation coefficient (SCC, with
the extended mask) and the Radial Reach Filter for background comparison. Templates whose codes cannot fix a position are refused
with ValueError, where NCC still returns a confident wrong answer. On real CC0 photographs with 40 templates per level, NCC drops
below half its hits at 10 % occlusion and 6 % saturated highlight; OCM and ISC hold until 63-67 % occlusion and 44-53 % highlight.
None of the four is rotation invariant (half the hits are lost at 7-9 degrees).

## 向くところ / 向かないところ

- 向く: テンプレートの一部に光沢が飛ぶ・手前の物が隠す・照明が片側だけ暗いなど、明るさの値が局所的に崩れる検査・位置決め。
- 向く: 明るさのガンマや露出が撮るたびに変わる場面(ISC は単調な変換で値が変わらない)。
- 向かない: 回転・拡大縮小を探す用途(`shape_locate` / 形状モデル)。質感の乏しいテンプレート(拒否される)。

## 推奨パイプライン

`isc_match` → `ocm_match`

まず `isc_match` で探し(単調な明るさの変化に厳密に不変、最も速い)、`margin`(次点との差)が小さい場面は `ocm_match` で
確かめる。背景画像があるなら、物の有無の判定は `radial_reach_filter` で照明の変化と影を切り離す。

## 代替

`scc_match`(値の相関を残したいとき。OCM・ISC よりは遮蔽に弱い)、`ncc_locate`(照明が一様なら最も素直)、
`radial_reach_filter`(テンプレートではなく背景と比べる)。

## 限界

回転は探しません(PoC で 4 種とも 7〜9° で当たりが半分を割る)。SCC は符号の合った画素だけを選ぶので、無関係な位置でも相関が
高めに出ます(選択の偏り)。既定では無相関の位置で期待される使用率(基本 1/2、拡張 5/16)+ 4 標準偏差より使用率の低い位置を
採点しません —— これは文献の式には無い、こちらで足した拒否です。平坦な所の多いテンプレートでは正解の位置でも使用率がこの床を
割ることがあります。RRF は背景が平坦な画素(空など)を判定しません(PoC の camera で判定できたのは 65 %)。

## 実寸校正

座標は画素。閾値は [0, 1] の明るさで書きます(8 ビットの画像なら 255 で割った値)。

## 最初の 1 本

```python
import numpy as np
from scipy import ndimage
import fullseye as fs

rng = np.random.default_rng(0)
scene = ndimage.gaussian_filter(rng.random((96, 96)), 1.5)
scene = (scene - scene.min()) / (scene.max() - scene.min())
tpl = scene[30:62, 40:72].copy()
lit = scene ** 0.4                       # 露出が変わった
lit[30:46, 40:56] = 1.0                  # テンプレートの 1/4 が飽和
r = fs.ledger.isc_match(lit, tpl)
print(r["row"], r["col"])                # 46 56(テンプレート中心)
```

## 裏づけ

- op: `ocm_match` / `isc_match` / `scc_match` / `orientation_code` / `increment_sign` / `radial_reach_filter`
- 例: [`poc_code_matching_breakdown`](../../examples/poc_code_matching_breakdown.py) —— 公開の実写 5 枚(CC0)から切った 40 テンプレートに
  遮蔽・ハイライト・減光・回転を段階的に掛けた破綻点の曲線、照明を振る GIF、平坦なテンプレートの拒否、背景との比較。
- 門: 画素ごとの総当たり(OCM / ISC は整数で一致、SCC は 1e-12)、マスクが全部立つとき SCC = 既存の NCC(1e-9)、単調変換での
  不変性(ISC・RRF)、rot90 との可換性(巡回差を絶対差にした探針で崩れる)、正解位置の ISC とマスク率の閉形式(z が ±4.5 以内)。
- 一次資料: Ullah, Kaneko, Igarashi, IEICE Trans. Inf. & Syst. E84-D(8), 2001 / Kaneko, Murase, Igarashi, Pattern Recognition 35(10), 2002 /
  Kaneko, Satoh, Igarashi, Pattern Recognition 36(5), 2003 / Satoh, Kaneko, Niwa, Yamamoto, Systems and Computers in Japan 35(10), 2004。
  式の確認に和文の再掲(精密工学会誌 66(2) 2000・75(2) 2009、電気学会論文誌 C 121(4) 2001・129(10) 2009、いずれも J-STAGE 公開)。
  著者が再現を承認したものではありません。
