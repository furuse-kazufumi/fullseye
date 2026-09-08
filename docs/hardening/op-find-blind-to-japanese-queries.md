---
id: op-find-blind-to-japanese-queries
date: 2026-09-08
found_by: poc_search_sweep_width
kind: discoverability
severity: high
where: [opassist.py, astrostack.py]
ops: [star_detect]
gate: [test_op_find_answers_japanese_queries]
status: fixed
---

# op_find が和文の複数語クエリに構造的に盲目だった

## 症状

副画素重心つきで点状目標の座標を返す 2-D op は `star_detect` だけなのに、`op_find("小さい目標 検出")` / `("スポット 検出")` / `("漂流 捜索")` は**いずれも 0 件**。英語の "point target detection" でようやく 20 件中 14 番目。名前が天文に閉じているせいだと思って docstring に説明語を足したが、**それでも 0 件のままだった**。

## なぜ門が通したか

原因は 2 つとも**探す側**にあった。(1) 語の切り出しが `_WORD_RE = re.compile(r"[a-z0-9]+")` の **ASCII 限定**で、`_WORD_RE.findall("点 検出") == []`。語幹の段は空回りし、部分一致は**空白ごと含む文字列**を探すので当たらない。(2) 採点に使う `doc` は台帳の**1 行目だけ**(`star_detect` で 30 文字)。本文にどれだけ説明語を書いても検索には届かない。**docstring の大半が日本語で、6 言語を配っている製品**でこれが立っていた。

## 直し

CJK の連なりを語として取り、丸ごと当たらなければ**文字 2-gram で按分**する段を足した。ただし **既存の点が 0 のときだけ**参照する追加の段なので、これまでの並び順は変わらない(語幹の段と同じ方針)。採点対象を docstring 全文へ広げ、**要約(名前 + 1 行 doc)への一致を重く**した。`star_detect` の docstring にも「名前は天体だが中身は分野中立」と、点状目標 / 輝点 / スポット / 微小欠陥 / 粒子 の語を書いた。実測: 「小さい目標 検出」1 位 / 「スポット 検出」2 位 / 「漂流 捜索」1 位。★**「点 検出」は今も出ない** —— 「点」1 文字は `cv_canny` や `frei_amp` の説明にも必ず出るので同点に押し出される。限界は PoC の assert に書いて隠していない。
