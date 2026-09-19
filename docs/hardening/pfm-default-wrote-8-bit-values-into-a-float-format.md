---
id: pfm-default-wrote-8-bit-values-into-a-float-format
date: 2026-09-20
found_by: genspark_external_review
kind: silent-wrong
severity: medium
where: [imgio.py, engine.py, api.py, accel.py, imgevolve.py, README.md]
ops: [gaussian]
gate: [test_pfm_default_write_is_float_and_round_trips, test_from_dict_refuses_none_and_scalar_stages_but_keeps_the_documented_forms, test_device_cuda_without_a_gpu_is_explained_and_recorded, test_apply_with_a_ledger_op_name_points_to_op_run, test_accel_parity_label_carries_its_threshold, test_readme_intro_counts_match_the_shipped_index, test_has_knows_the_ledger_and_algorithm_tiers, test_ops_search_folds_case_and_accents, test_pipeline_with_an_empty_ops_string_is_refused_with_a_sentence]
status: fixed
---

# PFM の既定が 8 bit 値を float 形式に書き、壊れた pipeline 設定が「成功」し、無い GPU が生の torch 文で報告されていた

## 症状

GenSpark 第 28〜35 報(0.2.1 の仕上げに回した分)。

- **N120(第 34 報)**: `imgio.save("x.pfm", float_image)` の往復が max|Δ| 0.98。ファイルの生バイトを読むと float32 に 226.0 … 254.0 —— **8 bit 経路の 0..255 を float 形式に書いていた**([[image-io-dropped-write-failures-and-crushed-16-bit]] で `depth="float"` を足したが、既定は直していなかった)。上下順は cv2 が書き読み両方で扱っており崩れていない。
- **N107(第 30 報)**: `FullseyeEngine.from_dict({"stages": None})` が 0 段のエンジンになり、`run` が入力をそのまま返す。`{}` は拒否するのに None は通る非対称。
- **N117(第 33 報)**: CUDA の無い環境で `apply(x, op, device="cuda")` —— master では台帳に記録して CPU で続けるが、その文が torch の生文「Torch not compiled with CUDA enabled」で、`on_error="raise"` ではそれがそのまま例外。
- **N124(第 35 報)**: 台帳 op の名前(`color_lut`)を `apply` に渡すと「unknown operator … list with fullseye.op_names()」—— op_names にも無いので、利用者は「存在しない」と読む。同梱索引は tier=ledger を知っている。
- **N116(第 32・33 報)**: `fullseye accel` の表が interior 差 0.0002 に "exact" と出す(閾値 5e-3 のラベル)。
- **N103(第 29 報)**: README.md 冒頭の「1,942 = 918 + 1,049」が手書きで、索引(1,996 = 931 + 17 + 1,048)とずれていた。生成器の対象外で門も無かった。

## なぜ門が通したか

- PFM の往復テストは `depth="float"` の口だけを見て、既定経路を見ていなかった(直した口を試験し、直していない口を試験しない —— [[feedback_one_probe_input_is_not_coverage]])。
- `from_dict` は「`stages` キーの有無」しか見ず、値の型を見ていなかった。
- GPU の失敗は「記録して続ける」までは第 1 陣で決めたが、記録する文を作る側(torch)の言葉をそのまま載せていた。
- README.md 冒頭は生成ブロックの外にあり、`test_docs_index_numbers` は docs/README*.md だけを数えていた。

## 直し

1. **`imgio.save`**: `.pfm` の既定 depth を `"float"` に(float32、往復 ~1e-7)。`ensure_gray` に「チャネルだけ、値域は `to_float01` / `normalize`」の契約を docstring で。
2. **`from_dict`**: `stages` が None / 数値なら ValueError(「list of stages (or an ops string)」)。`[]` は文書どおり恒等のまま。
3. **`_try_accel`**: GPU 経路が失敗したとき、`device` が cpu 以外で `torch.cuda.is_available()` が偽なら「device='cuda' requested but CUDA is not available here (torch x.y: …) — <元の例外> — the op ran on the CPU」に翻訳して台帳に(strict では例外)。元の例外文を残すのは、故障を注入する既存テストと診断のため。
3b. **`from_dict`** の `stages` が文字列のとき、1 文字ずつ段にしていた(`{"stages": "x"}` が op `'x'`)—— `from_ops` と同じ ops 文字列として分割。
4. **`_resolve`**: 同梱索引の tier が ledger の名前は「typed-ledger operator … run it with fullseye.op_run(name, <inputs>)」。
5. **`accel.parity_flag`**: `match(<0.005)` / `close(<0.05)` / `differ(>=0.05)`。照合相手の無い行は `-`。
6. **CLI `has`**(第 37 報 N131): 台帳 op と汎用アルゴリズムを「unknown」と答えていた(発見面 = 索引、判定面 = registry + nary が別)—— 同梱索引の台帳行と algo 層を引き、`op_run` / `algo run` を案内。`ops --search` はアクセントも畳む(N132)。
6b. **CLI `pipeline --ops \"\"`**(第 42 報 N146): 生の IndexError → 1 文の SystemExit。
7. **README.md** 冒頭の件数を索引の実数に(1,996 = 931 single-input + 17 n-ary + 1,048 typed-ledger)、門 `test_readme_intro_counts_match_the_shipped_index` で固定。

**同じ報で設計・次回として分けたもの**:

| 指摘 | 判断 | 理由 |
|---|---|---|
| N109 OP_NOTES の `dim` に族名 31 種(第 31 報) | 文書化(分離は 0.2.2) | `dim` は docs/ops の族ディレクトリ名で、opdocs・テスト・2,002 ノートがその意味で使う。次元は `in` / `out` から読める。`catalog.NOTE_KEYS` に注記。分離は opdocs の鍵の変更と全ノート再生成を伴う |
| N110 `n_notes` ≠ 実件数(第 31 報) | 設計 | `n_ops` は op 数(キー)、`n_notes` はノート枚数(6 op が 2 枚) |
| N113 / N118 bench・`fast=True` が遅い(第 32・33 報) | 設計(測り方) | 定常状態では `fast=True` が速い(0.07 ms vs 0.13 ms)。初回の 0.8 ms は cv2 の warm-up。バッチ経路の損益分岐は op と大きさで違い、`bench --size` はそれを測る道具 |
| N114 stubs 982 vs graph 252(第 32 報) | 定義違い | graph は registry の `Op.halcon` 完全一致、stubs は honest coverage(facade 別名・台帳を含む)。JSON への definition 併記は 0.2.2 |
| N115 CLI `index` 1,940 vs 同梱 1,942(第 32 報) | 設計 | CLI はその環境の生きた registry を数え、同梱複製はビルド環境の値 |
| N111 / N112 coverage・parity(第 32 報) | 0.2.0 のみ | 第 3 陣で直し済み(データ不在は 1 文で rc 1、parity は argv 衝突を解消) |
| N119 `op_find` の `doc` 空・`exact` / `total`(第 33 報) | 次回候補 | 索引側の note で補完する案 |
| N121 `ensure_gray` が正規化しない(第 34 報) | 文書化(上の 1) | チャネル処理と値域処理は別の契約 |
| N122 引数不足の生 TypeError(第 34 報) | 次回候補(低) | Python 標準の文。台帳の他 op と流儀を揃えるなら opassist 側で翻訳 |
| N123 `lines_color` の dict(第 35 報) | 非不具合 | N74 と同じ: out_sort は contour(dict)。`float(dict)` した側 |
| N125 int32 0..99 が全黒(第 35 報) | 設計維持 | 第 1 陣の判断どおり dtype 最大値で割り、台帳に記録・1 回警告、`raise` 方針で止まる。符号付き整数を方針に依らず拒否する案は 0.2.2 で検討(int の 0..255 を渡す利用者の互換) |
| N126 出力が [0,1] を外れる 40 op(第 35 報) | 設計 | feature / count / signed の out_sort。「[0,1]」は image 入力の契約 |
| accel 双子が apply から呼ばれない(第 28・29 報) | 実測で反証 | `apply(fast=True)` は `fast.py` の CPU 双子、`device="cuda"` は `accel` の GPU 双子に届く(`_try_fast` / `_try_accel`)。定常で速い |
| `accel.run_pipeline(steps, imgs)` の引数順(第 28 報) | 設計 | 台帳の `run` と同じく「何を」が先。docstring に `steps = [(op, a, b), ...]` |
| N99 `from_ops(list)`(第 27・28 報) | 0.2.0 のみ | 第 6 陣で直し済み |
| N141 MCP カタログの facade ソースに facade 表に無い名前 474 件(Python クラス名を含む)、表の鍵 515 件が欠落(第 41 報) | **0.2.2 の最優先候補** | master でも再現(entries 2,497 中 facade のみ 501)。facade ソースを `halcon_facade_map.json` の鍵に限定し、差集合 0 を門にする。検索面(`fullseye_search_ops`)を汚すので早く直す |
| N142 `synth` が rc 2(第 41 報) | 非不具合 | `inp out` の位置引数が必須で、argparse の usage エラーが正しい |
| N144 `run --upto 1` が全段と同じ(第 41 報) | 非不具合 | `threshold → otsu` は二値画像に恒等なので 2 段と 3 段が一致する。`upto` は効いている(第 6 陣の門) |
| N143 日本語の op_help が 199 件(第 39・41 報) | 非不具合 | 既定の `.html`(966 件)が日本語。`.ja.html` は一部の別名 |
| N127 HARDENING の「直した」が 0.2.0 に無い(第 36 報) | 0.2.1 で解消 | この CHANGELOG 0.2.1 が直した項目を列挙。ノートに `fixed_in` を持たせる案と wheel 実走の CI 門は 0.2.2 |
| N128 / N129 / N130 C ヘッダ・`fullseye mcp`・CHANGELOG の同梱(第 36 報) | 設計 / 候補 | ヘッダは Rust クレート側、`fullseye mcp` は新入口として候補、CHANGELOG は repo |
| N133 / N136 `call_tool(name, args, cat)`・`Catalog(entries, sorts)`(第 38・39 報) | 設計(0.2.2 候補) | 入口は stdio / `dispatch` / `main`。ファクトリと `cat=None` は候補 |
| N135 / N139 / N140 MCP の「2390 names」(第 38〜40 報) | 文言(上の起動ログ) | op 名 + HALCON 別名。ledger +3 は registry と同名の台帳 op を索引が registry 側に寄せる差 |
| N137 部分 NaN の無言サニタイズ(第 39 報) | 0.2.0 のみ | 第 3 陣で台帳 + 1 回警告 + raise で停止 |
| N100 / N101 / N104 z_algo(第 28・29 報) | 設計 | `include_algo` は別の計算モデル(`z_algo` は末尾に並ぶための鍵)、`apply` の対象外と docstring に明記済み |
