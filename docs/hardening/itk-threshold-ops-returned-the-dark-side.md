---
id: itk-threshold-ops-returned-the-dark-side
date: 2026-09-26
found_by: threshold_family_agreement
kind: silent-wrong
severity: high
where: [backends_r3.py]
ops: [xsitk_huang_thresh, xsitk_maxentropy_thresh, xsitk_moments_thresh]
gate: [test_the_region_is_the_bright_side, test_a_global_automatic_threshold_gets_the_box_exactly, test_they_all_agree_with_each_other, test_the_complement_is_what_the_gate_catches, test_the_itk_convention_is_the_one_we_had_wrong]
status: fixed
---

# SimpleITK 由来の 3 つのしきい値 op が、兄弟 op の**補集合**を返していた

## 症状

明部ちょうど 400 px の板で:

| op | 前景 px |
|---|---|
| `otsu` / `sk_otsu` / `cv_otsu` / `sk_yen` / `sk_li` | **400** |
| `xsitk_huang_thresh` | **3,696** |
| `xsitk_maxentropy_thresh` | **3,696** |
| `xsitk_moments_thresh` | **3,696** |

3,696 = 4096 - 400 —— ちょうど補集合。例外も警告も出ない。`area_frac` に渡すと
面積が **9.2 倍**になるが、返るのは「もっともらしい数」である。

## 原因

ITK の ``insideValue`` は**しきい値以下**の側(暗い方)に付く。recipe が

```python
sitk.HuangThreshold(img, 1, 0, bins)      # 1 = insideValue = 暗い側
```

と書いていたので、暗い側が 1 になっていた。SimpleITK 自身の ``OtsuThreshold`` を
``insideValue=1`` で呼んでも同じ 3,696 が出る(2026-09-26 に一次情報で確認)ので、
**SimpleITK の不具合ではなくこちらの呼び方**の誤り。直しは ``0, 1`` に入れ替える
だけで、しきい値そのものは 1 つも動かない。

## なぜ門が通したか

★**両方向を通す門は、向きを守らない。** この 3 本のうち 1 本には
`examples/gallery2d_color_artistic.py` に ground-truth の確認が在った ——
しかし見ていたのは「出力が二値であること」と「全 0 / 全 1 でないこと」だけで、
**どちらの向きでも通る**。「自明解でないこと」は確かに要る性質だが、それだけでは
**逆さまの答え**が素通りする。

図も 3 枚とも反転したまま配られていた(明部の円が黒、背景が白)。つまり
**見れば分かる形で出ていたのに、見て確かめる門が無かった**。

## 直し(2026-09-26 適用)

`backends_r3.py` の 3 つの recipe で ``1, 0`` を ``0, 1`` に入れ替え、図を描き直した。

## 門

`tests/test_threshold_polarity_2026_09_26.py`。**op 名から族を拾う**ので、新しい
しきい値の方法を足しても自動で門に入る(免除は理由つきで名指しし、「本当にまだ
暗い側なのか」を別の試験が確かめる)。守るのは 3 つ:

1. どの方法でも region になるのは明るい側(局所適応は被覆率で見る)
2. 大域の自動しきい値は板でちょうど箱を返し、**互いに一致する**
3. ITK の規約そのものを 1 本の試験に固定する —— 規約が変われば、直す場所が
   recipe だとその試験が教える

展示 = `examples/threshold_family_agreement.py`(この欠陥を見つけた形そのもの)。
