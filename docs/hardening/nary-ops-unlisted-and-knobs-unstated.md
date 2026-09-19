---
id: nary-ops-unlisted-and-knobs-unstated
date: 2026-09-20
found_by: genspark_external_review
kind: discoverability
severity: low
where: [api.py, imgevolve.py, tools/gen_mcp_data.py, pyproject.toml]
ops: []
gate: [test_op_names_include_nary_adds_exactly_the_nary_tier, test_every_list_ops_row_carries_a_knobs_summary, test_the_shipped_knob_table_equals_the_docs_copy, test_cli_apply_input2_runs_an_nary_op, test_cli_index_prints_the_four_tiers]
status: fixed
---

# n-ary op は呼べるのに一覧に無く、つまみ a / b が効くかは文でしか分からず、CLI からは 2 入力の op を呼べなかった

## 症状

GenSpark 第 18〜20 報の統合チケット(N60 + I1)。

- `fullseye.op_names()` に `add_image` / `sub_image` … の 17 本が無い。`list_ops()` には `tier == "nary"` で載り、`apply([x0, x1], "add_image")` で呼べる —— 「一覧に無いのに呼べる」を第三者は N2 として報告し、第 1 陣で **docstring とエラー文に呼び方を書く**ところまで直していたが、**一覧そのものは引けない**ままだった。
- `a` / `b` のつまみが何を振るか(振っても出力が変わらない op か)は、op ノートの文と `docs/op_knob.json`(実測 461 op)にしか無く、**公開 API に機械可読な形が無い**。利用者は 931 op の a / b を「全部効くかもしれない」と扱うしかない。
- CLI `apply` は `op inp out` の 1 入力で、2 入力の op を呼ぶ手段が無い(`fullseye apply add_image a.png out.png` は「unknown op」)。
- `fullseye index` の内訳は dict の repr(`{'color': 12, 'ledger': 1048, …}`)で、段の名前と順が読みにくい。

## なぜ門が通したか

- `op_names()` は「**1 入力**の識別子の一覧」で、README・索引の門(931)はその定義で数える。第 1 陣ではその定義を守るため **既定を変えない**判断をし(正しい)、代わりに**引数で両方を出す**口を用意しなかった。
- つまみの実測(`tools/impl2/knob_probe.py` → `docs/op_knob.json`)は **ノートの文を検証する門**(`tools/opdocs.py` の `_fact_knob`)としてだけ使われていて、配布物に載らず、`list_ops` の行にも無かった。「測った」と「利用者が読める」は別の場所にある。
- CLI の `apply` は registry(`ops.REGISTRY`)だけを引く。n-ary は別モジュール(`imgops_nary`)で、`api._nary_by_name()` は CLI から呼ばれていなかった。

## 直し

1. **`op_names(include_nary=False)`** —— 既定は従来どおり 1 入力の一覧(定義と門を守る)。`True` で両方の段を 1 つの整列した一覧で返す。
2. **`list_ops()` の各行に `knobs`** = `knob_summary(name)`: `{"a": "continuous" | "discrete" | "unused", "b": bool, "breakpoints": [...]}`。正本 `docs/op_knob.json` を **`fullseye/data/op_knob.json` として wheel に同梱**(`tools/gen_mcp_data.py` が複製、`pyproject.toml` の package-data、`tools/regen_all.py --check` が drift を見る)。**未計測の op は `None`** —— 実測は 461 / 931 で、測っていない op を「効かない」と言わない。
3. **CLI `apply --input2 PATH`** —— n-ary op は `api.apply([A, B], name, a, b, on_error="raise")` で走る。`--input2` 無しの n-ary は「2 inputs: pass --input2」、1 入力 op に `--input2` は「takes one input」で止める(黙って捨てない)。3 入力以上は CLI の対象外と言う(現状の n-ary は全部 2 入力)。
4. **`fullseye index`** の内訳を `registry 919 / nary 17 / ledger 1048 / color 12` の順で名前つきに。

**同じチケットで採らなかったもの(設計)**:

| 提案 | 判断 | 理由 |
|---|---|---|
| `op_names()` の既定に nary を混ぜる | 採らない | 「1 入力の識別子一覧」という定義を変えると、README・索引の門(931)と pipeline / 進化の語彙が変わる。引数で出す |
| `apply2(x0, x1, name)` の新設 | 採らない | `apply([x0, x1], name)` の糖衣で、facade を 1 本増やすと help・example・門が要る。エラー文が呼び方を言う |
| `run --input2` | 採らない | pipeline の段は 1 入力(前段の出力を受ける)。2 入力を段に持たせるのは engine の型の変更で、別の設計判断 |
| `op_run` / `op_assist` に registry op を教える | 採らない | 型付き台帳(opassist)専用の道具。registry 側は `op_find` が両方の段を探す |
