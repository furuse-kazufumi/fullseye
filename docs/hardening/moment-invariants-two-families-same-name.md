---
id: moment-invariants-two-families-same-name
date: 2026-09-09
found_by: poc_rotation_invariance_audit
kind: discoverability
severity: low
where: [moments3d.py]
ops: [moment_invariants, moments_region_2nd_invar, moments_region_central_invar]
gate: [test_the_three_d_moment_op_points_at_the_two_d_region_family]
status: fixed
---

# 「モーメント不変量」が 2 つの族にあり、名前だけで選ぶと落ちる

## 症状

回転不変性を監査する PoC を書くとき、「回転不変なモーメント」を探して `moment_invariants` を見つけ、`(H,W)` の二値領域を渡した。返ってきたのは

```
ValueError: points must be a point cloud of shape (N,3): shape=(200, 200)
```

`moment_invariants`(:mod:`moments3d`)は **3-D 点群**の Sadjadi–Hall 流不変量で、2-D の**領域**から同じ趣旨の量が欲しいときは HALCON 流の `moments_region_2nd_invar` / `moments_region_central_invar` / `moments_region_3rd_invar`(Hu モーメント)のほうだった。

## なぜ門が通したか

どちらの op も**それ自体は正しく、docstring も正しい**。壊れていたのは「名前が同じ趣旨を指しているのに、互いを知らない」ところ ―― `refract` / `refract_rays` で踏んだのと同じ、**参照が片道ですらなく無い**型。しかも今回は片方が例外で止まるので実害は小さいが、探す側は「回転不変量は 3-D にしか無い」と誤って結論しうる(実際、この PoC を書いた時点でそう思いかけた)。

型検査は正しく働いた ―― `_check_points` が `(200, 200)` を拒んだ。**落ちること自体は良い設計**で、足りなかったのは「では何を使えばいいのか」を言う一行。

## 直し

`moment_invariants` の docstring 冒頭に、2-D 領域用の 3 op を名指しで書いた(踏んだ日付と、実際に出る例外文つき)。門はその相互参照が**実在し続けること**を見る ―― 名前を変えたり片方を消したりしたときに、説明だけが古びないように。

## 残っている限界(正直に)

2-D 側(`backends_auto.py` の Hu モーメント 3 本)から 3-D 側への逆参照はまだ張っていない。実際に人が落ちるのは「3-D の名前を見つけて画像を渡す」向きだけなので、そちらを先に塞いだ。
