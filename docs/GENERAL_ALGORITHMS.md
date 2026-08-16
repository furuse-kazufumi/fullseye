# 汎用アルゴリズムを実装可能にする — algo-c 対応ロードマップ

> ユーザー要望(2026-08-16): <https://github.com/okumuralab/algo-c>(奥村晴彦
> 『[改訂新版] C言語による標準アルゴリズム事典』全ソース)にあるような**汎用アルゴリズム**も
> Fullseye で実装できるようにしたい。
>
> **正直な現状認識**: Fullseye は現在 **画像アルゴリズム設計 AI**(op レジストリ = image/region/
> feature/contour/volume の sort、進化 + holdout gate + Python→C codegen)。汎用アルゴリズム
> (ソート/探索/グラフ/数論/暗号/圧縮)は画像 sort に載らないため、**言語・型・codegen の拡張**が要る。
> これは複数セッションの作業。本 doc はその**確定計画**(次セッションが full context で実行する正本)。

## algo-c のカテゴリ(書籍 TOC・実装対象マップ)
※ 厳密な網羅は repo の `/src` を正本とする。

| 分野 | 代表アルゴリズム | Fullseye での受け皿 |
|---|---|---|
| 数値計算 | 方程式(二分法/Newton)、数値積分(Simpson/Romberg)、連立一次(Gauss/LU)、補間(spline)、FFT | 既存 `dsp`(FFT)+ 新 `numeric` op 族 |
| 乱数・統計 | Mersenne Twister、分布、統計量 | 新 `rng`/`stat` op(決定的 seed) |
| ソート | quick/heap/merge/shell/radix | 新 `array` sort + `seq` 型 |
| 探索 | 二分探索、ハッシュ、BST/AVL/B-tree | 新 `array`/`map` op |
| 文字列 | KMP/BM/Rabin-Karp、編集距離、正規表現 | 新 `text` 型 + op |
| グラフ | DFS/BFS、Dijkstra、Warshall-Floyd、MST、最大流 | 新 `graph` 型 + op |
| 幾何 | 凸包、線分交差、ボロノイ | 既存 `pcseg`/幾何 + 新 `geom2d` |
| 数論・暗号 | 素数、GCD、RSA、MD5/SHA、AES | 新 `numtheory`/`crypto`(教育用・honest 開示) |
| データ圧縮 | Huffman、LZ/LZW、算術符号化 | 新 `compress` op |
| DP/探索 | 8-queens、ナップサック、DP | fscript の制御フロー + `array` |

## 実装アーキテクチャ(確定方針)
Fullseye の既存資産を汎用へ拡張する。**画像 AI の焦点は薄めない**(汎用 op は別 tier / opt-in)。

1. **型システム拡張**: 現在 6+1 sort(image/region/feature/contour/match/any/volume)に
   **`seq`(1-D 配列)/`text`(文字列)/`graph`/`scalar`** を追加(`ops.py` の sort・`fslib` 型)。
2. **fscript の汎用言語化**: 既に if/for/while・代入・タプルがある。**配列/文字列リテラル、
   インデックス、procedure(関数)** を段階追加(現在は言語スコープを絞る決定だったので、
   汎用 tier は別プロファイルで解禁)。正本 = `docs/FSCRIPT_DECISION.md` の A/B 分岐を再検討。
3. **op レジストリ拡張**: algo-c の各アルゴリズムを **op**(name/in-out sort/params/**c_stmt**)として
   登録。既存の Python→C codegen(`engine.to_python`/`to_c`)+ **difftest**(honest gate: Python が
   oracle、C を差分検証)をそのまま流用 → **「C で実装できる」を実測で保証**。
4. **honest gate**: algo-c の C を参照実装として `difftest` に食わせ、Fullseye codegen の C と
   数値/ビット一致を検証(既存 gate の拡張)。**元コードのライセンス**(algo-c = 書籍付属、
   利用条件を要確認)を尊重し、**丸写しでなく仕様から再実装**(公開開示ポリシー)。

## 段階計画(次セッション以降)
- **P1**: `seq`/`scalar` 型 + ソート 3 種(quick/heap/merge)を op 化 + C codegen + difftest。
  = 「Fullseye は汎用アルゴリズムも C 生成できる」最小実証。
- **P2**: 数値計算(二分法/Newton/Simpson/Gauss)op 族。
- **P3**: 文字列(KMP/BM/編集距離)+ `text` 型。
- **P4**: グラフ(Dijkstra/BFS/MST)+ `graph` 型。
- **P5**: 圧縮/数論/暗号(教育用・honest 開示、丸写し禁止)。
- 各 P で: 進化 gate は非対象(汎用 op は決定的・holdout 進化しない)、**difftest で C 一致を honest 実測**、
  Studio の op ブラウザに新 tier を出す。

## honest な限界と規律
- **丸写ししない**: algo-c の C を参照しつつ**仕様から再実装**(`feedback_provenance_research_method`)。
  ライセンス確認前にコードを取り込まない。
- **画像 AI の焦点を薄めない**: 汎用 op は opt-in tier。北極星(HALCON 級画像 op 網羅 + honest
  holdout)は不変。

---

## P1 完了記録(2026-08-16, Opus5[1m]/ultracode)
**最小実証「Fullseye は汎用アルゴリズムも C 生成でき、C 一致を honest 実測できる」を達成。**

- **新 tier(画像 REGISTRY と完全分離・opt-in)** = `algo.py`。`seq`(1-D 数列)/`scalar`(単一実数)型を新設。
  画像 `ops.REGISTRY` には一切触れないため、進化探索・Wave-0 champion pin は無影響(テストで実証)。
- **op(5)**: ソート 3 種 `quicksort`(Hoare/median-of-three/Lomuto/明示スタック)・`heapsort`(Williams
  1964 binary max-heap)・`mergesort`(von Neumann 1945 top-down stable)= `seq→seq`。加えて `scalar`
  型に役割を与える reduction `seq_max`/`seq_min`(`seq→scalar`、順序非依存で exact)。**全て仕様から
  再実装**(algo-c ソースは丸写しせず・各 op に `provenance` を明記)。
- **単一 source of truth**: 各 op は Python 本体と C 本体を**文字列で保持**し、in-process 参照は
  `algo.py_fn` が同じ文字列を compile、`algo_codegen` は同じ文字列を standalone `.py`/`.c` に emit。
  → テストした oracle と出荷物が drift しない(テスト `test_emitted_python_*` で実証)。
- **codegen** = `algo_codegen.py`(`emit_python`/`emit_c`。C は関数 + バイナリ I/O driver = 完全に
  compile 可能な単体プログラム)。
- **honest gate** = `algo_difftest.py`(2 つの実測、deferred skip でない):
  (1) Python 参照 **== numpy oracle**(`np.sort`/`np.max`/`np.min`)、(2) codegen **C == Python を
  bit 一致**(holdout=edge cases 10 + random 40)。これらの op は既存 double を移動/選択するのみゆえ
  正しい実装は bit 完全一致(tol=0.0)。
- **★実測(2026-08-16, `zig cc` = `python -m ziglang cc`, ziglang 0.16.0 を pip 導入)**:
  全 5 op で **python diff 0.00e+00 / C-vs-Python diff 0.00e+00 / passed=True**(実 compile→実 run→bit
  比較)。= 「C 一致を honest 実測」を **deferred skip でなく本当の測定**として達成。
- **fail-closed**: toolchain 無し → C 半分は honest skip(Python 半分は走る)。compile/run 失敗 →
  gate FAIL(neutral skip にしない。テスト `test_difftest_compile_error_fails_closed` で実証)。
- **facade**: `fullseye.algo_ops()/run_algo()/algo_to_c()/algo_to_python()/algo_difftest()`
  (+ `api.py`)。**skill** = `~/.claude/skills/image-processing/SKILL.md` に「General algorithms
  (algo-c tier)」節を追記(サブエージェントから使用可)。
- **テスト**: `tests/test_algo.py`(42 件=registry 整合・Python==sorted/oracle・安定性・単一 source
  of truth・C bit 一致[toolchain 有時]・compile-error fail-closed・画像 registry 非汚染・facade)。
- **honest な限界**: ①NaN を含む数列は比較ソートの規約が Python/C/numpy で分かれるため holdout から
  除外(開示)。②浮動小数の和など**累積で順序依存になる op は P1 に含めない**(seq_max/min は exact)。
  ③CLI サブコマンド統合(`imgevolve.py algo ...`)と Studio op ブラウザ tier 表示は次段(P1.5)。
  ④fscript の配列/procedure 言語化(設計 doc アーキ項 2)は P1 スコープ外(別 track)。

## P1 敵対レビュー後の強化(2026-08-16, [[feedback_no_solo_ai_judgment]])
本セッションの自作コードへ独立敵対レビュー(Workflow 4 レンズ=算法正しさ / codegen・C 安全 /
gate 健全性 / 統合・焦点安全、22 findings)を実施。全件を私が一次コード検証(v11 規律)し、
真の欠陥を修正:
- **[HIGH] gate の fail-open(NaN/符号付きゼロ)**: `_max_diff_*` が `max(0.0, nan)=0.0` で NaN 差分を
  握り潰し「bit 一致」と偽証していた(実測再現)→ **(1)Python×oracle=値比較だが非有限で fail-closed
  (inf、tol で通さない)、(2)C×Python=真の bit 比較(IEEE float64 生バイト=符号付きゼロ/NaN ペイロード
  も検出)** に分離。`c_verified` フィールドで「実 compile 検証済 pass」と「toolchain 無し unverified
  pass」を区別。
- **[HIGH] quicksort が重複多数入力で O(n²)**(Lomuto `<=` で全等値が片側に。二値=binary mask flatten
  が現実的入力・実測 quadratic)→ **3-way(Dutch national flag)partition + median-of-three** に Python/C
  とも書換(全等値 O(n))。性能ガードテスト(20000 全等値 <2s)追加。
- **[HIGH] emitted C `heapsort` が BSD `<stdlib.h>` の `heapsort()` と衝突**(macOS/BSD で compile 不能。
  `zig cc -target x86_64-macos` で実測)→ C シンボルを **`heapsort_asc`** に改名(`mergesort_asc` と統一)。
  **全 op の macOS cross-compile テスト**を追加(回帰ガード)。
- **[LOW] C の fail-open/UB 3 件**: mergesort の malloc 失敗=無ソート出力→**in-place 挿入ソート
  fallback(fail-closed・stable 維持)**/ heapsort の `2*root+1` int overflow→**long long** 化 /
  driver の len が 32-bit で size_t wrap→**`SIZE_MAX/sizeof(double)` 上限チェック + `<stdint.h>`**。
- **[MED] test_mergesort_is_stable が空虚**(値比較=どのソートも通る)→ **符号付きゼロの順序保存**で
  安定性を実観測(`<`=不安定への退行を検出)に書換。**no-mutation テスト**(`run(a)` が呼び手の
  list を破壊しない)も追加。
- **[MED] holdout が小・重複希薄**→ 大 all-equal(300)/ 二値(300)/ few-distinct(300)+ 重複多め
  ランダムを追加(C gate が重複・サイズ regime を実検査)。
- **[MED/honesty] NaN 規約未文書化**→ module docstring と各 op docstring に「NaN-free 前提・非有限は
  gate で fail-closed」を明記。seq_max/min の「order-independent」→「NaN-free 入力で order-independent」。
- **隣接の既存 ship-bug**: `sample_images`(studio が runtime import)が `pyproject.toml` py-modules
  欠落=非 editable wheel で消える → 追加(wheel 実ビルドで確認)。
- テスト **43→58 件**(bit-check・fail-closed・macOS cross-compile・重複性能・no-mutation・c_verified・
  安定性観測を追加)。全 op の difftest 再走 = python/C とも diff 0.0・bit 一致・passed=True。
- **未修正(ユーザー判断・P1 範囲外の既存問題)**: (a)`pyproject.toml` の `[tool.setuptools.package-data]`
  `"*"` glob が root-level flat の `studio_assets/`・`data/` を wheel に載せられない(studio i18n/op-help/
  sample 画像が installed wheel で欠落=既存・要 MANIFEST.in か package 化の設計変更)/ (b)`fullseye.__all__`
  が api の pcseg 系 18 名を欠く(star-import で欠落=既存)。**algo tier は無関係(algo* は py-modules で
  確実に同梱・facade は整合)**。

## 次(P2 以降)
- **P1.5a(済, 2026-08-16)**: `imgevolve.py algo <list|run|emit-c|emit-py|difftest>` サブコマンドを追加
  (統一 CLI 入口。`algo run quicksort --seq 3,1,2` / `algo emit-c mergesort` / `algo difftest all`)。
  CLI 回帰テスト 2 件 + skill の CLI 例を更新。
- **P1.5b(完了 2026-08-17)**: Studio の op ブラウザに general(algo)tier を **read-only 表示**(下記記録)。
- **P2(完了 2026-08-16)**: 数値計算 op を seq/scalar 型基盤の上に。**simpson / bisection / newton**
  (多項式・サンプルを入力 seq に内包する seq→scalar・既存 reduce ドライバに載る)+ **gauss_solve**
  (連立一次 Gauss 消去・部分ピボット=下記 P2 完遂記録)。honest gate = **C-vs-Python は bit 一致**
  (同一アルゴリズム + `-ffp-contract=off` で FMA 抑止)/ **Python-vs-oracle は数値許容差**(`AlgoOp.tol`)で
  独立 oracle(simpson=scipy / 求根=残差 |p(root)| / gauss=`np.linalg.solve`)照合。fail-soft を honest 文書化。
- **P3(完了 2026-08-17)**: 文字列 op(下記 P3 完遂記録)。`text` 型は「コードポイント列を float64 で運ぶ」
  規約(`text_to_seq`/`seq_to_text`)で既存 float64 harness に載せ、新 wire 型を足さずに実現。
- **P4(完了 2026-08-17)**: グラフ op(components/mst_weight/dijkstra、下記 P4 完遂記録)。`graph` は
  `[n, m, (u,v,w)*m]` パックで既存 harness に載せた(新 wire 型不要)。
- P5 圧縮・数論・暗号(教育用・honest 開示)。

## P3 完遂記録 — 文字列 op(2026-08-17, Opus5[1m]/ultracode, `graph-loop-engineering`)
**文字列アルゴリズム 3 種を algo tier に追加。** 「文字列 = コードポイント列を float64 で運ぶ」(Unicode スカラーは
< 2^53 ゆえ厳密)で **既存の float64 バイナリ harness に無改造で載る**(新 wire 型不要)。値は等値比較のみ(整数コードで
厳密)・位置/距離は厳密整数 → **C-vs-Python bit 一致 かつ Python-vs-oracle は EXACT(tol 0)**。

- **op(3)**: `strfind`(Knuth-Morris-Pratt=失敗関数プレフィックスオートマトン。入力 `[m, pattern(m), text]` → 全出現
  開始位置の昇順リスト・重複出現含む=**可変長 KIND_MAP**、gauss で作った可変長 wire を再利用) / `edit_distance`
  (Wagner-Fischer/Levenshtein 2 行 DP=**KIND_REDUCE**・厳密整数) / `lcs_length`(最長共通部分列長 2 行 DP=
  KIND_REDUCE)。全て仕様から再実装(provenance 明記)。fail-soft=空パターン/切詰/パターン>テキストは `[]`、
  na<0/切詰は `0.0`。
- **単一 source of truth + text 型ヘルパ**: `text_to_seq(s)`/`seq_to_text(seq)`(コードポイント↔float64)を追加。
- **honest gate 実測(3 op とも passed=True・c_verified=true)**: Python==**独立 oracle**(strfind=素朴 all-occurrences
  スキャン[KMP と独立]/ edit・lcs=**top-down memo 再帰**[bottom-up 2 行 DP と別コード経路])で **diff 0.0(exact)** /
  codegen **C==Python bit 一致**(ziglang cc)。
- **work-graph op 波(候補 d の実演)**: 新 op ごとに `algo_gate` ゲートノードを積む=**1 op=1 ノード**。3 op を
  `raptor-worklog add --capability tool` → `run-once --available tool:command` で **無人 done**(gate_ok.json 生成)。
- **回帰**: `tests/test_algo.py` に strfind/edit_distance/lcs_length のテスト群(既知解・random×独立 oracle・fail-soft・
  可変長出力・no-mutation・python exact・C bit 一致)。全スイート **4669 passed / 0 failed**(P2 後 4649 から +20)・
  ruff clean・mypy 回帰 0。commit + push はこのセッションで実施(ユーザー承認 2026-08-16 就寝時=push ゲート開放)。

### P3 文字列 敵対レビュー後の強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
独立敵対レビュー Workflow(4 レンズ・各 finding を検証エージェントが実コード/実 compile で確認)= **3 findings 全
CONFIRMED**(うち 2 件は同一根本原因を別レンズが報告)。一次検証の上で全修正:
- **[MED] Python が `int(a[0])` を範囲チェックの前に実行 → C と非一致**: edit_distance/lcs_length の Python は
  `na = int(a[0])` を先に評価(truncation)、C は raw double を先にガード。**`a[0]` ∈ (-1.0, 0.0)**(例 -0.5)で
  Python は na=0(有効な空文字列)で続行し実距離を返す一方、C は raw guard で拒否し 0.0 → **bit 一致契約違反**
  (ziglang cc で実測: `[-0.5,65,66]` = Python 2.0 vs C 0.0)。holdout は非負整数 na のみゆえゲートが未検出。
- **[LOW] NaN header で Python がクラッシュ**(C は fail-soft): `int(nan)` が ValueError を送出し、op docstring の
  fail-soft 約束に反する(C は NaN-false ガードで 0.0/`[]`)。※NaN は「NaN-free 前提」で契約外だが同じガード順序の欠陥。
- **修正(1 つで両方)**: 3 op すべての Python を **raw-value ガードを `int()` の前**に移動(`not (x >= lo and x <= hi)`=
  NaN-false)=**C を厳密に鏡写し**。gauss は元から raw guard で正しかった(同型に統一)。
- **境界の被覆**: oracle 検証域外(oracle は truncation で別値を出す=まさにこのバグ)ゆえ、小数負/NaN/超過ヘッダの
  **C-vs-Python parity を専用テストで直接固定**(`test_string_c_python_parity_on_bad_headers`)+ Python fail-soft
  no-crash テスト。algorithm-correctness/c-safety の中核指摘は 0(KMP/DP/メモリ安全はクリーン)。
- レビュー後: 3 op とも difftest = python exact / C bit 一致 / c_verified=true、全スイート緑(下記)・ruff/mypy 回帰 0。

## P2 完遂記録 — gauss_solve(2026-08-16, Opus5[1m]/ultracode, `graph-loop-engineering`)
**連立一次方程式 Gauss 消去(部分ピボット)を追加し、P2 数値計算を完遂。** ユーザー指示どおり
`graph-loop-engineering` スキルで raptor work-graph にノード化し、tool driver に無人実行させた(二層方針=
breadth は work-graph の difftest ゲート、敵対 findings 採否・push はセッションの human checkpoint)。

- **新 kind `KIND_MAP`(`map_varlen`)= 可変長 seq→seq**: 既存 op は sort(入力長=出力長)/ reduce(→1 値)
  のみで、連立解(入力 `[n, 拡大係数行列 n×(n+1) row-major]` → 解ベクトル長 n)は入力長≠出力長。C 境界=
  `int f(const double* a, int n, double* out)` が out に out_len(≤ n)個書き out_len を返す(fail-soft=0)。
- **`algo_codegen` ドライバに可変長出力モード**: KIND_MAP 分岐が `{int32 out_len, out_len*float64}` を書く
  (sort と同じ wire だが out_len≠入力長)。out バッファは入力長で確保(契約 out_len≤n が上界を保証)+
  `out_len ∈ [0,len]` に **fail-closed clamp**(暴走 op が読み手を over-read させない)。
- **gauss_solve(`algo.py`)**: Python 参照(stdlib のみ・index-by-index で C を鏡写し)と C 参照を単一 source。
  前進消去(部分ピボット=最大 |要素| 行を選択)+ 後退代入。特異(ピボット 0 残存)/ malformed は **[] / 0** で
  fail-soft(例外なし)。**Python/C の FP 演算順を厳密一致**(同一除算・subtract-then-multiply・被消去要素を
  exact `0.0` 代入・abs は inline 符号反転で `math.h`/`-lm` 非依存)ゆえ bit 一致。int overflow は `n≤46340` +
  `long long need` で防止。
- **honest gate 二段(実測)**: (1)Python **== `np.linalg.solve`**(独立 oracle・良条件 holdout 34 ケース=対角
  優位 + 行置換 + **ピボット必須ケース**[exact-zero(0,0)・微小(0,0)・3×3 ゼロ対角])→ **max abs diff 3.55e-15**
  (tol 1e-9)。(2)codegen **C == Python bit 一致**(`ziglang cc`・`-ffp-contract=off`)→ **diff 0.0 / c_verified=true**。
  特異/malformed の **C fail-soft は Python と完全一致**を別テストで直接検証(oracle 非対応領域ゆえ holdout でなく
  C-vs-Python 直接比較)。
- **`tools/algo_gate.py`(再利用可能な gated-stage runner)**: work-graph の `CommandWorker` は produces 生成 or
  exit0 で done 判定するため、difftest が FAIL 時も JSON を書く現状では **fail-open**(失敗ゲートが done)になる。
  これを塞ぐ = **pass 時のみマーカー `gate_ok.json` を書き、exit code=判定**。ノードの produces をマーカーに
  向けると失敗ゲートが **fail-closed** でノード失敗になる。P3 以降の op 波(1 op=1 ノード)にそのまま使える。
- **work-graph ノード化**: `raptor-worklog add --capability tool --project imgevolve --priority 0`(spec=
  `tools/algo_gate.py --op gauss_solve --out <OUT>`、produces=`<OUT>/gate_ok.json`)→ `run-once --available
  tool:command` で **無人実行 → status=done**(exit0・c_verified=true・bit 一致マーカー生成)。
- **回帰**: `tests/test_algo.py` に gauss + algo_gate + C fail-soft + require_c テスト群を追加(算法テスト
  **93 passed**)、全スイート **4649 passed / 0 failed**(レビュー前 4637 から +12)。私の全ファイル **ruff clean**・
  mypy 回帰 0(既存 baseline=scipy/ziglang stub 欠如と difftest 署名の既存 quirk のみ、私の追加行由来 0)。全
  local commit・**未 push=human-gate**。

### P2 gauss 敵対レビュー後の強化(2026-08-16, [[feedback_no_solo_ai_judgment]])
自作 gauss コードへ独立敵対レビュー Workflow(4 レンズ=numeric 正しさ / C 安全 / gate 健全性 / 統合・被覆、
各 finding を検証エージェントが**実行再現**)。5 findings 中 **4 CONFIRMED** を一次コード検証の上で全修正:
- **[HIGH] algo_gate の fail-open(未知 op)**: `find_algo` の `SystemExit` が `marker.unlink()` より**前**に
  あり、旧 pass の `gate_ok.json` が残存 → CommandWorker が produces 存在で **done 誤判定**(op 改名/typo の
  再実行で顕在)。→ **mkdir + stale-marker unlink を registry チェックの前**へ移動(どの早期 exit でも旧 pass を
  引き継がない)。回帰テスト追加。
- **[MED] gate が部分ピボットを反証できない**: holdout が対角優位のみ(exact-zero ピボット無)→ ピボット探索を
  削除した mutant でも `np.linalg.solve` と 2.2e-14 で一致し **PASS**(pytest は捕捉するが work-graph が走らせる
  algo_gate は difftest holdout ゆえ捕捉しない)。→ **ピボット必須ケース**(exact-zero(0,0)=`[[0,1],[1,0]]`・
  微小(0,0)=`[[1e-14,1],[1,1]]`・3×3 ゼロ対角)を holdout に追加=no-pivot mutant を**構造不一致→inf→FAIL** で
  falsify(自前実測確認済)。誤解を招くコメントも訂正。
- **[MED] C skip でも pass マーカー**: toolchain 不在で C 半分が skip(honest だが**未検証**)でも
  `res["passed"]` だけでマーカーを書き、graph はマーカー存在のみ読む → **未 compile の C を certify**。→
  `require_c`(既定 True)を追加=未検証 pass は `gate_ok.json` を書かず(`gate_unverified.json` に diagnostic)
  **fail-closed**。`--allow-unverified-c` で明示 opt-out、`--no-c` は Python-only の意図的弱ゲート。
- **[REFUTED] 「out_len==0 の wire が未テスト」**: 私が先回りで追加した `test_gauss_c_fail_soft_matches_python`
  が実 C を compile/run して被覆済 → 検証エージェントが mutation で健全性を確認し **棄却**。残る macOS
  cross-compile guard の軽微 nit(`_ALL`→`_ALL_OPS` で numeric/gauss も被覆)のみ採用。
レビュー後も gauss difftest = python 3.55e-15 / C bit 一致 / c_verified=true・work-graph ノード(hardened)= done。

## P1.5b 完遂記録 — Studio に general tier を read-only 表示(2026-08-17, Opus5[1m]/ultracode)
**op ブラウザに general(algo)tier を表示。** 画像フォーカスを薄めない設計 = general op は seq/scalar の別
計算モデルゆえ **read-only**(画像パイプラインに入れない)。
- `api.list_ops(include_algo=False)` に opt-in パラメータ + `api.algo_rows()`(backend="general"・category "algo:*"・
  tier "z_algo" で末尾ソート・halcon None・provenance 付き)。**既定は不変**(既存 caller は画像 op のみ=焦点維持)。
- studio: `all_ops = list_ops(include_algo=True)` で browser に表示 / `_op_row` が algo フォールバック /
  `op_signature_detail`・`op_tooltip` が general 分岐(「seq/scalar op・not an image op・run via CLI」+ provenance)/
  `on_op_selected` が general 選択時に Insert・Run once・Help・a/b ノブを無効化 / `add_op`・`run_op_once`・
  palette が general を flash 拒否。多重防御 = **`PipelineModel.add_stage` が画像 REGISTRY で KeyError fail-closed**。
- **敵対レビュー(2 レンズ・実行検証)= 3 CONFIRMED(2 は同一根本原因)を全修正**:
  - **[HIGH/MED] Program(HDevelop コード)エディタ「Apply → pipeline」が未ガード**: `op_names` を
    `list_ops(include_algo=True)` から導出していたため general 名がコードパーサ/補完/Help ピッカーに伝播 →
    `apply_program` が `model.stages=` 直書きで **add_stage backstop を迂回** → general op がパイプライン侵入。
    → **`op_names` を画像限定に**(`backend != "general"` で除外。browser 表示 `all_ops` は general 保持)+
    `apply_program` に general stage 拒否ガード(多重防御)。
  - **[MED] Help ダイアログのピッカーが general を虚偽表示**(「Two knobs a,b tune this operator」)→ 同じ
    `op_names` 画像限定化で Help ピッカーからも除外(root fix が両方を解消)。
- 回帰テスト: `_op_row`/signature/tooltip の general 分岐、offscreen で browser が general を表示しつつ Insert 等が
  無効・`win._op_names` が general 除外・コードパーサが general 行を拒否。全スイート緑・ruff net-new 0(新規テストは
  clean、studio.py の flash は file の `%`-format idiom に一貫)・mypy 回帰 0。**候補 (d) op 波**も実演=全 12 algo op を
  work-graph に 1 op=1 ノードで載せ `run-once` で無人 done。

## P4 完遂記録 — グラフ op(2026-08-17, Opus5[1m]/ultracode, bonus)
**グラフアルゴリズム 3 種を algo tier に追加**(候補外だがユーザー「全部進めて」+7-8h 自律に沿うボーナス)。グラフを
入力 seq にパック(`[n, m, (u,v,w)*m]`、無向; dijkstra は src 前置 `[n, m, src, ...]`)し既存 float64 harness に載せる。
- **op(3)**: `graph_components`(union-find・連結成分数=KIND_REDUCE 厳密整数)/ `graph_mst_weight`(Kruskal・最小
  全域森の総重み=KIND_REDUCE)/ `graph_dijkstra`(単一始点最短距離=**KIND_MAP**・-1.0=到達不可)。決定的 union 則 +
  (weight,index) ソート + 最小距離·最小 index の settle 順で **C==Python bit 一致**。
- **★KIND_MAP driver を 2 段化(size-probe)**: dijkstra は出力長 n が入力長 3+3m を**超え得る**(疎グラフ)。旧 driver
  は out を入力長で確保していたため heap OOB になる欠陥 → driver が `f(a,n,NULL)` で out_len 上界を問い、その分だけ確保
  してから実書き込みする 2 段プロトコルに変更(gauss/strfind/dijkstra に `if(!out) return <bound>`)。
- **honest gate**: Python == 独立 oracle **scipy.sparse.csgraph**(connected_components/minimum_spanning_tree/dijkstra)。
  整数重み holdout で **components 厳密(tol 0)/ mst・dijkstra tol 1e-9(実測 0)**。C==Python bit 一致(ziglang cc)。
  MST/Dijkstra holdout は単純グラフ(csr の重複加算回避)、components は多重辺可(連結性のみ)。
- **敵対レビュー(3 レンズ・実行検証)= 2 CONFIRMED(共に HIGH・dijkstra メモリ安全)を全修正**:
  (#2)out バッファが入力長サイズ → n>3+3m で OOB書込 → **2 段化 driver**で解消(発見前に先回り修正済)。
  (#1)src ガードが生 `sd < nd` → 小数 nd で src==n が通り out[n] OOB → **整数 n で束縛**(`sd < n`)。1 REFUTED
  (到達不可ノード未検証←known-answer/sparse テストで被覆)。numeric/oracle 各レンズの他指摘なし。
- **op 波**: 3 グラフ op も work-graph ゲート化(全 algo op = 15 が 1 op=1 ノードで無人 done)。全スイート緑・ruff clean
  ・mypy 回帰 0。push はセッション(ユーザー承認)。
