---
id: compactness-saturated-at-one
date: 2026-09-26
found_by: shape_factors_closed_form
kind: silent-wrong
severity: medium
where: [backends_auto.py]
ops: [compactness]
gate: [test_compactness_does_not_saturate_on_long_scratches, test_compactness_matches_the_closed_form_shape, test_the_old_squash_is_what_the_gate_catches]
status: fixed
---

# `compactness` が 1.0 で頭打ちし、長い傷を区別しなくなっていた

## 症状

幅 2 px の傷の長さを変えても、**長さ 80 以上は全部 `1.0`**。

| 傷の長さ | 直す前 | 直した後 |
|---|---|---|
| 10 | 0.159 | 1.592 |
| 40 | 0.637 | 6.366 |
| 80 | **1.000** | 12.732 |
| 110 | **1.000** | 17.507 |
| 140 | **1.000** | 22.282 |

傷・割れは検査の主役である。**いちばん見たい領域で、形が違うのに同じ数**が返っていた。

## 原因

```python
return np.float64(min(1.0, (per * per) / (4 * np.pi * max(pr.area, 1)) / 10))
```

`C = 周囲長²/(4π·面積)` を 10 で割って `[0,1]` に収めていた。`/10` が便宜的で
あることは説明文に書いてあったが、**`min(1.0, ...)` で潰していることは書いて
いなかった** —— 開示されていたのはスケールだけで、答えを失う方ではない。

★**値域 `[0,1]` は feature の契約ではなかった。** 同じ `region -> feature` の
`elliptic_axis` は 6.35、`r2_runlength_features` は 110、`r3_region_features` は
18.1 を返す。潰す理由がそもそも無かった。

★**同じ量を素のまま返す兄弟が既に在った。** `r3_region_features` は
`周囲長²/(4π·面積)` をそのまま返し、`tests/test_regions3.py` が正方形で
`16/(4π)` を門にしている —— 同じ問いに 2 つの入口があり、片方だけが潰していた
([[feedback_a_fix_leaves_the_twin_surface_open]])。

## なぜ門が通したか

★**「範囲に収まっていること」を確かめる門は、潰れていることを見ない。** この op に
掛かっていた検査は値域([0,1])と有限性だけで、**頭打ちはその両方を満たす** ——
むしろ「きれいに収まっている」ように見える。潰れを見つけるには「**入力を変えたら
出力も変わるか**」を問う必要があり、そのためには形を 1 つでなく**列**で渡さねば
ならない。1 枚の探針では原理的に出ない型である
([[feedback_one_probe_input_is_not_coverage]])。

説明文にも半分しか書かれていなかった: `/10` が便宜的であることは書いてあったが、
`min(1.0, ...)` のことは書いていない。**開示は、痛い方こそ書く。**

## 直し(2026-09-26 適用)

`/10` と `min(1.0, ...)` を外し、`周囲長²/(4π·面積)` をそのまま返す(HALCON の
`compactness` と同じ量)。HALCON は `max(1, C)` と**下で**切るが、ここでは切らない
—— 1 を下回る値は「領域が小さすぎて画素近似が効いていない」という情報そのもので、
必要なら呼ぶ側で切れる。この差は説明文に書いた。

## 門

`tests/test_shape_factors_closed_form_2026_09_26.py`。長さを伸ばすと数が伸び続ける
こと、矩形の閉形式と形が合うこと、そして**旧式(`/10` + 頭打ち)に戻すと落ちる**
ことを固定した。

## 残っているもの(直していない)

この直しで `compactness` の**絶対値**は周囲長の推定に載る。その推定には解像度を
上げても消えないバイアスが在り、2 つある推定量が逆の形で外す ——
`docs/KNOWN_ISSUES.md` §50 に測定つきで記録した。`circularity` が HALCON と
**別の量**を計算している件も同じ節にある。どちらも規約の選択なので、記録だけ。
