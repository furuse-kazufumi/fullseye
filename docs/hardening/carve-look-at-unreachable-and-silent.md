---
id: carve-look-at-unreachable-and-silent
date: 2026-09-08
found_by: poc_livestock_body_volume
kind: discoverability
severity: high
where: [visualhull.py, ops3d.py, render3d.py]
ops: [carve_look_at, synthesize_silhouette, carve]
gate: [test_carve_look_at_is_reachable_from_the_public_tiers, test_the_public_look_at_is_the_other_convention_and_says_so]
status: fixed
---

# 空間彫刻の姿勢ヘルパが引けず、同名の別規約を掴むと例外なく空の hull が返った

## 症状

`carve` / `synthesize_silhouette` が要求する姿勢は OpenCV 規約(`X_cam = R X + t`、**+Z 前方**)。それを作る `visualhull.look_at` は `fs.` / `fs.op.` / `fs.ledger.` の**どこからも引けず**、`op_find("look")` も **0 件**。一方、公開層で `look_at` の名を持つのは `render3d` の gluLookAt 版(4x4・**−Z 前方**)。その `M[:3,:3], M[:3,3]` を渡すと全点がカメラ後方に落ち、**例外を出さずに空のシルエット → 空の hull** が返る。独立に再現(立方体 8000 点で 正しい姿勢なら前景 2240 px、gluLookAt 由来で 0 px)。

## なぜ門が通したか

**カメラ 0 台は `ValueError` で fail-closed** なのに、**規約違いは無言**だった。門は「入力が足りない」ほうには立っていて、「入力の意味が逆」のほうには立っていなかった。同じ名前で規約が逆という、いちばん静かに間違える組み合わせ。

## 直し

① `carve_look_at` を台帳(`ops3d` / space_carving、型 `pose`)に載せて `fs.ledger` と `op_find("look")` から引けるようにした —— **名前は譲らない**(同名にすると今度は逆向きに静かに壊れる)。② 点が 1 つ残らずカメラ後方なら `RuntimeWarning`。③ `render3d.look_at` の docstring に「彫刻には渡すな」と書いた。④ 既存の「後方の点を棄却する」試験も `pytest.warns` で固定し、警告をノイズにしない。⑤ 正典の例 `examples_3d/space_carving.py` を新しい名前へ付け替えた。
