---
id: dem-viewshed-self-occlusion
date: 2026-09-08
found_by: poc_stockpile_volume
kind: implementation-bug
severity: high
where: [demops.py]
ops: [dem_viewshed]
gate: [test_a_hill_taller_than_the_eye_is_visible_from_the_open, test_the_wall_itself_is_visible_even_though_its_far_side_is_not, test_a_hill_is_hidden_only_when_the_sight_line_passes_below_the_wall]
status: fixed
---

# 可視領域が、目線より高いセルを軒並み「見えない」と返していた

## 症状

平地に置いた円錐の**頂点**が、60 m 先・目線 2.0 m の開けた平地から可視 0.0。目線より高い 1541 セルの可視は **0 個**、底面の遮蔽率 0.8863(閉形式 0.5710)。独立に最小再現: 平地に高さ 10 m の柱を立てると可視 0.0、目線より低い 1 m の柱は 可視 1.0。**凸な立体の最高点は外から必ず見える**ので、幾何として誤り。

## なぜ門が通したか

可視領域の試験は 3 本あった —— 平地は全部見える / 壁の**向こう側**は見えない / 観測点は常に見える。**どれも目線より高いセルの可視を一度も見ていない**。平地には目線より高いものが無く、壁の試験は「向こう側が 0 か」だけを見ていた。壁**そのもの**が見えるかを確かめる 1 行があれば、その日に鳴っていた。

## 直し

視線を `ceil(hypot(H,W))` 等分した最後の標本が `np.rint` で**目標セル自身**に丸まり、`(z-eye)/(dist*t) > (z-eye)/dist`(t<1)が z > eye なら必ず真になっていた。**標本が目標セルに乗った回は数えない**よう修正。直後の実測: 頂点 1.0、遮蔽率 0.5900(PoC 自前 0.5539 / 閉形式 0.5710 —— **閉形式を挟んで両側**。別々の離散化なので一致は求めない)。壁越しの遮蔽は幾何どおり残っている。
