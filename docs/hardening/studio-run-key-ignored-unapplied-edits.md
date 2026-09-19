---
id: studio-run-key-ignored-unapplied-edits
date: 2026-09-19
found_by: genspark_external_review
kind: implementation-bug
severity: medium
where: [studio.py]
ops: [gaussian, otsu]
gate: [test_run_all_applies_unapplied_program_edits_first, test_run_all_does_not_run_the_old_pipeline_when_the_edit_does_not_parse, test_ctrl_r_is_an_alias_of_the_run_key]
status: fixed
---

# Studio の実行キーが、Program に書いたばかりの編集を無視して古いパイプラインを走らせていた

## 症状

GenSpark 第 8 報。Xvfb 上で Studio を起動し xdotool で操作、前後のスクリーンショットを画像解析で比べた実測: Program エディタに `gaussian (0.4, 0.5)` を打つとステータスが「● unapplied edits — Apply to run, or Reset to discard」に変わる(s8)。そこで実行キーを押しても **画面は 1 bit も変わらず**、ステータスもそのまま(s9 = s8)。報告では Ctrl+R を押していたが、Studio の実行キーは HDevelop 流の **F5 / Ctrl+Return** で、Ctrl+R は未割り当てだった —— ただし F5 を押しても同じ結果になる(下)。

## なぜ門が通したか

`_do_run_all` は `step_to(len(model.stages) - 1)` の 1 行で、**`model.stages`(= 適用済みのパイプライン)だけ**を見る。Program の未適用編集は `state["code_dirty"]` と、エディタの文字列にしか無い。「Apply ボタン → 実行」の 2 段を前提に作ってあり、実行キーが「書いてあるものを走らせる」という利用者の期待(HDevelop の F5 もそう)と食い違っていた。Studio のテストは `model.add_stage` → `_do_run_all` の経路だけで、**エディタに打ってから実行キー**の経路を踏んでいなかった。

## 直し

1. **`_do_run_all`** —— `state["code_dirty"]` なら先に `win._program["apply"]()`(Apply ボタンと同じ関数)。Apply が通らなければ(構文エラー・未知の op は Program の状態表示に理由が出る)**古いパイプラインは走らせない**。
2. **Ctrl+R を F5 の別名に**(`act_dbg_run.setShortcuts([F5, Ctrl+R])`)。メニューの表示も「Run all (F5 / Ctrl+R)」。
3. **Run once の fallback を画面に出す**(第 10 報 N16)—— グレー画像に `edges_color`(color 入力)を Run once すると、ライブラリは台帳に記録して sort の既定値を返すが、GUI は「ran … once」としか言わず、新しい窓には**既定値**が映っていた。`api._bs.mark()` / `events_since()` で前後の台帳を比べ、落ちていれば窓の題名に「— FALLBACK」、ステータスに「⚠ … FELL BACK (理由)」を出す。
4. **ブラウザ検索の順位**(第 10 報 N17)—— 「canny」で先頭が `edges_color`(説明文に canny を含む)になり、Enter で挿入する op を取り違えやすかった。名前の完全一致 → 前方一致 → 名前に含む → HALCON 名 → 説明文だけ、の順に並べる(同順位は登録順)。

**同じ報告で設計 / 環境側として残したもの**: 検索欄の入力文字が描画されていないように見える(N14)—— 一覧は `canny` に絞られているので入力は届いている。Xvfb のフォント環境の問題か Studio の描画かはスクリーンショットだけでは切り分けられず、未確認のまま。サンプルパイプラインのプルダウンが無反応(N15)は座標の外れ(報告側も断定していない)。
