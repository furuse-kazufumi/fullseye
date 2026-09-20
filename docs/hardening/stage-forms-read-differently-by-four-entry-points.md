---
id: stage-forms-read-differently-by-four-entry-points
date: 2026-09-20
found_by: genspark_external_review
kind: implementation-bug
severity: medium
where: [engine.py, unified.py]
ops: []
gate: [test_four_entry_points_read_the_same_stage_names, test_diagnose_stages_reports_a_broken_stage_instead_of_raising, test_engine_rejects_a_malformed_stage_with_the_shared_sentence, test_unified_pipeline_accepts_list_and_dict_stages]
status: fixed
---

# 同じ段を 4 つの入口が別々に読んでいた

## 症状

GenSpark 第 53 報(0.2.0 の clone 調査、2026-09-20)。0.2.1 でも再現。

- **N179**: `engine.diagnose_stages([{"op": "otsu"}])` が `unknown operator {'op': 'otsu'}`。Studio が保存する形の段を、検証器が
  **dict そのものを op 名として** registry に引いていた(`st[0] if tuple else st`)。同じ段は `run_pipeline` でも
  `FullseyeEngine` でも走る —— 検証器だけが「無い」と言う。
- **N181**: `fullseye.Pipeline([{"op": "median"}])` と JSON 由来の list 段 `[["median", {}]]` が `unhashable type: 'dict'` /
  `'list'`。`unified.Pipeline` は tuple しか見ず、それ以外を registry の鍵にしていた。

## なぜ門が通したか

段の書き方 5 形は `api._normalise_stages` の docstring に書かれ、`run_pipeline` の門(第 1 陣)で固定されていた。
しかし段を読む場所は 4 つ(`api._normalise_stages` / `FullseyeEngine.__init__` / `diagnose_stages` / `unified.Pipeline`)で、
門は最初の 2 つにしか無かった。GenSpark の設計パターン提案 ②「段の正規化を 1 本に」はこの数え方の指摘で、
[[feedback_count_wrapper_families_not_mechanisms]] と同じ —— **仕組みがあることと、全経路が通ることは別**。

## 直し

1. **`engine.stage_name(stage)`** を唯一の入口に: 文字列 / タプル・リスト / dict(`op` か `name`)から op 名だけを
   取り出し、外した形は「the op must be a non-empty name: a stage is …, got …」の TypeError。ノブの読み方
   (engine は a / b、unified は kwargs)は呼ぶ側に残す。
2. `diagnose_stages` は壊れた段を **raise せず error 行** に(検証器の答えは Problems 欄に出るべきもの)。
3. `FullseyeEngine.__init__` は名前の取り出しを `stage_name` に(ValueError の文は同じ 1 文)。
4. `unified.Pipeline` は list 段と dict 段 `{"op": name, **kwargs}` を受け、`(op, 3)` のような形は「(op, {kwargs})」と言う。
   `_resolve_op` は op 名・UnifiedOp・callable 以外を TypeError で止める(unhashable を利用者に見せない)。

**同じ報で分けたもの**: N182(`apply_cmap` の名前)= master で動く / N183 `blend_mode` のモード名検証順・N184 `attempt*` の
docstring・N187 `algo run` の `--seq` 必須 = 候補(低)/ N185 = 第 6 陣で済 / N186 = 非不具合。
