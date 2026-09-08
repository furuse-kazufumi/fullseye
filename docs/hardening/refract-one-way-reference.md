---
id: refract-one-way-reference
date: 2026-09-08
found_by: poc_multibeam_bathymetry
kind: doc-hole
severity: medium
where: [match3d.py]
ops: [refract, refract_rays, snell_angle]
gate: [test_refract_points_at_the_per_ray_version_it_used_to_hide]
status: fixed
---

# ベクトル版 refract が、per-ray 版 refract_rays の存在に触れていなかった

## 症状

`refract` の docstring は「(N,3) バッチも通るが **1 本でも TIR ならバッチ全体が `None`**。バッチで使うなら呼び出し側で **1 本ずつ回すこと**」とだけ書いていた。ところが**光線ごとに TIR を判定して (方向, マスク) を返す `refract_rays` が既にある**(`refract_rays` 側からの参照は在った)。

## なぜ門が通したか

参照が**片道**だと、名前の見つけやすい側から入った人だけが遠回りする。「無い」と言う前に 4 層を引く規律は読み手にも要求できない —— **説明の側が両方向に張られていないと、正しい道具が在っても届かない**。

## 直し

両方の docstring に相互参照を書き、音響で使うときの読み替え(`eta = 1/c`。屈折率ではなく速度で考えるので逆数を渡す)も `snell_angle` の説明に添えた。
