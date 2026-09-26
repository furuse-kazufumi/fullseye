---
id: dimensional-features-were-normalised
date: 2026-09-26
found_by: shape_factors_closed_form
kind: silent-wrong
severity: high
where: [backends_auto.py, data/auto_specs/regions.json]
ops: [area_center, area_center_xld, contlength, get_region_thickness, diameter_region, diameter_xld, elliptic_axis, elliptic_axis_xld]
gate: [test_area_center_is_pixels_not_a_fraction, test_contlength_is_the_perimeter_in_pixels, test_get_region_thickness_is_pixels_and_no_longer_saturates, test_diameter_region_is_the_max_chord_in_pixels, test_the_two_diameter_ops_agree, test_elliptic_axis_returns_ra_rb_phi_in_pixels, test_the_two_elliptic_axis_ops_use_the_same_angle_convention, test_a_bigger_image_does_not_change_a_pixel_measurement]
status: fixed
---

# 寸法を持つ特徴が画像サイズで正規化されていて、HALCON の数と合わなかった

## 症状

30x70 の矩形(画像 200x200)で、HALCON の画素値との倍率:

| op | 直す前 | HALCON(画素) | 倍率 |
|---|---|---|---|
| `diameter_region` | 0.2585 | 74.85 | 290x |
| `get_region_thickness` | 0.1500 | 30.00 | 200x |
| `contlength` | 0.2450 | 196.00 | 800x |
| `area_center` の面積 | 0.0525 | 2100.00 | **40,000x** |

倍率は**画像の大きさで変わる**。つまり同じ物体でも、画像を広げるだけで数が変わって
いた —— 「解像度に依らない」という当初の意図とは逆の性質である。

★**量そのものが違うものも 2 本あった**。`diameter_region` は等面積円の直径を返して
おり、HALCON の Diameter(輪郭 2 点間の最大距離)ではない。輪郭版 `diameter_xld` は
最大弦を返していたので、**双子どうしで 5.6 倍食い違っていた**。
`elliptic_axis` は ``Ra/Rb``(= **別の演算子 `eccentricity` の出力**である Anisometry)
を 10 で割った 1 スカラーで、HALCON の (Ra, Rb, Phi) のどれでもなかった。

## なぜ門が通したか

★**正規化は「規約」として明文化されていた** —— `area_center` の註に「3 成分とも
解像度に依らないよう [0,1] 正規化する」と書いてある。門は規約どおりかを見ており、
**規約そのものが HALCON と食い違っていることは誰も見ていなかった**。

開示されていた分、`height_width_ratio` の飽和と同じ型である —— **書いてあるが、
書いてあるまま残っていた**。

## 直し(2026-09-26 適用、ユーザー判断)

「特徴は解像度に依らないよう正規化する」をやめ、**同名は同じ数**を取る。正規化が
要るなら利用者が画像サイズで割れるが、**割った値から画素数は復元できない** ——
情報を捨てない側に倒した。

* `area_center` → (面積[画素], 重心行, 重心列)
* `area_center_xld` → 同上(HALCON の PointOrder は返していない)
* `contlength` / `get_region_thickness` → 画素
* `diameter_region` / `diameter_xld` → **輪郭 2 点間の最大距離**(画素)
* `elliptic_axis` / `elliptic_axis_xld` → **(Ra, Rb, Phi)** を `match` ソートで

★``cv2.fitEllipse`` の角は**最初に返る軸**(短軸のことが多い)の向きなので、長軸で
なければ 90 度回す。忘れると領域版と 90 度ずれる(実測: region 0 度 / xld -89.9 度)。

## 門

`tests/test_pixel_units_2026_09_26.py`。**閉形式で採点する** —— 30x70 の矩形なら
面積 2100、厚み 30、輪郭長 196。加えて「**画像を広げても数が変わらない**」ことを
門にした(正規化に戻ると落ちる)。
