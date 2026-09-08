---
id: ecef-to-geodetic-returned-latitude-180
date: 2026-09-08
found_by: poc_geodetic_height_frames
kind: silent-wrong
severity: medium
where: [demops.py]
ops: [dem_ecef_to_geodetic, dem_geodetic_to_ecef]
gate: [test_ecef_to_geodetic_refuses_the_region_where_latitude_is_not_unique, test_ecef_to_geodetic_never_returns_a_latitude_its_own_inverse_rejects]
status: fixed
---

# ECEF→測地座標が、自分の逆関数が拒否する緯度 180 度を黙って返していた

## 症状

地球の中心付近を渡すと **lat = 180.0000 度**が返る —— 緯度として存在しない値。しかも `dem_geodetic_to_ecef` 自身が「lat_deg must be within [-90, 90]」で**拒否する**値だった。**自分が産んだ値を自分の逆関数が受け取れない**。例外は出ないので、下流は「もっともらしい数字」を受け取る。

## なぜ門が通したか

往復(測地→ECEF→測地)の試験はあったが、**往復できる入力しか渡していなかった**。地球の内部という、実用では来ないが定義が壊れる入力に門が無かった。[[feedback_gate_must_stand_where_the_accident_happens]] の型。

## 直し

Bowring の式の分母 `r - e²a·cos³θ` が負に回るのが原因で、負になるのは楕円体の**縮閉線(evolute)の内側** —— そこでは楕円体面から立てた法線が 1 本に決まらず、**測地緯度がそもそも一意でない**。閉形式 `(a·r)^(2/3) + (b·|z|)^(2/3) < (a²-b²)^(2/3)` で判定して fail-closed にした。境界は赤道面で `e²a = 42697.7 m`、極軸上で `(a²-b²)/b = 42841.3 m`(実測でも 42600 m が 180 度、42700 m が 0 度でちょうど切り替わる)。★ついでに docstring の往復誤差も測り直した —— 「1e-12 度未満 / 1e-7 m 未満」は**中央値であって最大値ではなく**、緯度 ±85 度の 4000 点で既に 6.4e-12 度 / 8.5e-07 m を超えていた。標本の範囲つきで書き直した。
