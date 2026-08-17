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
- **P5(完了 2026-08-17)**: 数論・圧縮・教育用ハッシュ(gcd_seq / sieve_primes / pow_mod / crc32 /
  rle_encode、下記 P5 完遂記録)。整数を float64 で運ぶ(exact <2^53)ため新 wire 型不要。全 op が
  **exact**(C bit 一致 かつ Python==独立 oracle tol 0)。**暗号は primitive のみ**(modular
  exponentiation / CRC)= フル RSA/AES/SHA は bignum/大状態で float64 seq harness に載らないため範囲外
  と honest 開示。

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

## P5 完遂記録 — 数論・圧縮・教育用ハッシュ(2026-08-17, Opus5[1m]/ultracode, `graph-loop-engineering`)
**汎用アルゴリズム 5 種を algo tier に追加し、algo-c ロードマップ(P1→P5)を完遂。** 整数を float64 で運ぶ
(exact < 2^53)ため新 wire 型不要。ビット/整数演算は C 側で `unsigned long long`/`unsigned int` に cast して行い、
double へ戻す(結果は < 2^53 で exact)。**全 5 op が exact**(C==Python bit 一致 かつ Python==独立 oracle tol 0)。
- **op(5)**:
  - `gcd_seq`(KIND_REDUCE): 非負整数列の GCD(Euclid・列に fold)。oracle=`math.gcd`。
  - `sieve_primes`(**KIND_MAP**): エラトステネスの篩。入力 `[n]`(長さ 1)→ n 以下の素数昇順=**出力が入力長を
    大きく超える**代表例。size-probe 上界 `π(n) ≤ n/2 + 1`(2 と奇数の数、log 不要=`math.h` 非依存)。oracle=試し割り(独立経路)。
  - `pow_mod`(KIND_REDUCE): モジュラー冪 base^exp mod m(square-and-multiply=RSA/DH の primitive・教育用)。oracle=builtin `pow`。
  - `crc32`(KIND_REDUCE): CRC-32(IEEE 802.3・reflected・poly 0xEDB88320)。**c_func は `crc32_ieee`**(zlib/BSD の
    `crc32` シンボル衝突を防御的に回避、cf. heapsort_asc)。oracle=`zlib.crc32`(zlib C ライブラリ=完全独立)。
  - `rle_encode`(**KIND_MAP**): 連長圧縮 →`[value, count, ...]`(**出力最大 2×入力**、全異なると 2n)。可逆・oracle=`itertools.groupby`。
- **★honest 域の開示(pow_mod)**: uint64 の中間積が溢れないよう **mod ≤ 2^32−1**(積 < mod² < 2^64)、base/exp ≤ 2^53。
  結果 < mod < 2^53 で float64 exact。域外は fail-soft 0.0(raw guard を int() の前・NaN 安全)。
- **★暗号は primitive のみ(honest scope)**: フル RSA/AES/SHA は bignum・大状態で float64 seq harness に載らないため
  範囲外と明記。載る primitive(modular exponentiation / CRC checksum)を**アルゴリズム開示**で提供(cipher ではない)。
- **★整数性ガード(新規・honest 改善)**: gcd_seq/pow_mod/crc32 は**データ値**ゆえ非整数は malformed → fail-soft。
  `x == float(int(x))` / `x == (double)(long long)x` を**range チェックの後に short-circuit**(NaN/超過値では cast に到達せず
  `int(nan)` クラッシュ・C の `(long long)nan` UB を回避)。header 系(sieve の n)は既存 gauss/dijkstra と同じ切り捨て規約。
- **★KIND_MAP 2 段 size-probe を新 2 op で活用**: sieve(出力≫入力)・rle(出力≤2×入力)とも `if(!out) return <上界>` で
  driver が上界を問い→確保→実書き込み。専用テストで **C 出力が入力長を超えても heap OOB しない**ことを実 compile/run で固定。
- **honest gate 実測(5 op とも passed=True・c_verified=true・ziglang cc)**: Python==独立 oracle **diff 0.0(exact)** /
  codegen **C==Python bit 一致 diff 0.0**。crc32 は `zlib.crc32` と全バイト値・"Hello"・全 256 バイトで一致確認。
- **work-graph op 波**: 5 P5 op を `algo_gate` ゲートノード化(`1 op=1 ノード`・priority 0・tool capability)→
  `run-once --available tool:command` で **5 ノード無人 done**(各 `gate_ok.json`=c_verified/bit 一致マーカー生成)。
  = **全 algo op 20 が work-graph ゲート化**(15→20)。
- **回帰**: `tests/test_algo.py` に P5 テスト群(既知解・独立 oracle 照合 over-random・fail-soft・整数性・
  2 段 probe の出力超過・bad-input C-vs-Python parity・no-mutation・python exact・C bit 一致)。全スイート
  **4700 → 4736 passed / 0 failed**(+36)・私の新規ファイル ruff clean・mypy 新規エラー 0(既存 baseline のみ)。

### P5 敵対レビュー後の強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
自作 P5 コードへ独立敵対レビュー Workflow(4 レンズ=algorithm-correctness / C-safety-codegen / gate-honesty /
integration-focus、各 finding を検証エージェントが**実 compile/実行で再現**、18 agents)。**14 raw → 9 CONFIRMED / 5
REFUTED**。全 CONFIRMED を私が一次再現(自分で ziglang compile・実行)した上で修正。**特筆すべきは「gate が自作の
guard を falsify できるか」への深い突き**:
- **[MED] pow_mod の honest 域(base/exp ≤ 2^53)が holdout で未計測** → exp を uint32 に切り詰める C 変異が gate を
  通過(base/exp 最大 1e6/1e5 で上位 ~33bit 未計測)。**修正**=holdout に 2^53 境界ケース([2,2^53,7]・[2^53,2^53,2^32-1]
  等)追加 + random を [0,2^53] 全域に拡大。**再現確認**: 修正後は exp→uint32 変異が `passed=False`。
- **[LOW] gcd(2^53 guard)/sieve(5,000,000 cap)も同種の未計測境界** → gcd 境界を holdout に追加(変異 falsify 確認)、
  sieve at-cap は Python 参照が遅い(~7.7s)ため**専用 C-only テスト**で n=5,000,000 受理(π=348513・独立 numpy sieve で検算)
  ・n=5,000,001 棄却を計測。
- **[MED] -ffast-math / -ffinite-math-only が NaN ガードを消去** → shipped C artifact を fast-math で compile すると
  `x >= 0.0` の NaN 棄却が省かれ `(long long)NaN` UB が実行(**自己再現**: `gcd_seq([NaN,6])` が `-ffinite-math-only` で 2.0、
  gate 既定 `-ffp-contract=off` では 0.0)。**修正**=`algo_codegen.emit_c` に `#if __FAST_MATH__ || __FINITE_MATH_ONLY__ →
  #error` を注入(artifact が silent miscompile せず**ビルド拒否**=fail-closed)+ C コメントの「UB 到達不可」を IEEE 前提と
  honest 訂正 + fast-math ビルド拒否テスト追加。
- **[MED] C の短小入力ガード(pow_mod `n<3` / sieve `n_in<1`)が falsify 不能** → 全 holdout が固定長ゆえガード削除で
  OOB heap read を admit しても全テスト緑。**修正**=holdout / parity テストに空・短小配列を追加し境界パスを exercise。
  **honest 開示**: black-box 値比較は safety-guard 削除を**決定的には**捕捉できない(OOB 読み取り値が非決定的)。本来は
  ASan が正攻法だが **ziglang の ASan は本 Windows 環境でリンク不能**(`__asan_shadow_memory_dynamic_address` 未定義)。
  Python 側ガードは決定的に falsify 可能・C 側は境界 exercise + サニタイザで捕捉可(環境制約で自動化は保留)。
- **[MED] pow_mod の `1 % mod` 特殊分岐が falsify 不能**(exp==0 かつ mod==1 の同時ケースがどこにも無い)→ holdout に
  [7,0,1]・[0,0,1] 追加 + 既知解 assert(**再現確認**: `1%mod→1` 変異が `passed=False`)。
- **[MED] P5 oracle が域外入力でクラッシュ**(zlib.crc32 / pow() / int(nan) が raise)→ holdout に域外ケースを足すと
  difftest が例外送出=gate が guard 規約を**構造的に被覆できない**(1 unit test のみが捕捉)。**修正**=各 P5 oracle を
  **ドメイン認識化**(`_int_in` で op の宣言域を鏡写し→域外は op の fail-soft 値 0.0/[] を返す=クラッシュ回避)。これで
  gate 自体が guard 発散を falsify 可能に(**再現確認**: crc integrality 削除・gcd guard 縮小の各変異が `passed=False`)。
- **[LOW] Studio の Operator-help カードが general op に「Two knobs a,b」と虚偽表示**(P1.5b で picker は塞いだが
  browser 選択の `op_help_html` フォールスルーは未ガード・全 20 algo op に波及)→ `op_help_html` に general 分岐追加
  (provenance + packed-input 契約 + CLI 実行を表示)+ `_op_row`/`api.algo_rows` に `desc`(op.doc)追加 + 回帰テスト。
- **[LOW] image-processing skill の YAML frontmatter description(auto-trigger 面)が P1 のみ広告**(body は 20 op 更新済)→
  description の algo 節を P2–P5 全スコープ + トリガ語(primes/modular exponentiation/CRC-32/RLE/shortest path)に拡張。
- **REFUTED 5 件**(検証で棄却): いずれも現行コードは正しく、finding が実挙動を誤認(検証エージェントが実行で反証)。
- レビュー後: 5 P5 op とも difftest = python exact / C bit 一致 / c_verified=true、全スイート **4742 passed / 0 failed**
  (レビュー修正テスト +6)・私の新規ファイル ruff clean・mypy 新規 0。work-graph 5 ノードも post-fix で再ゲート(done)。

## P6 完遂記録 — 計算幾何(2026-08-17, Opus5[1m]/ultracode, 12h 自律・`graph-loop-engineering`)
**幾何アルゴリズム 3 種を algo tier に追加**(algo-c ロードマップ P1→P5 完遂後の拡張=P6。当初 TOC の「幾何=凸包/
線分交差」に対応)。**画像 tier の輪郭/領域処理への橋渡し**でもある。2-D 点を入力 seq にパックし、**整数座標**
(各 [-100000, 100000])で全ての向き判定/靴紐和を**厳密な整数**にする(浮動小数除算を一切使わない)=C bit 一致 かつ
Python==独立 oracle tol 0。
- **op(3)**:
  - `polygon_area2`(KIND_REDUCE): 靴紐公式で多角形の **2×符号付き面積**(符号=巻き方向)。oracle=numpy ベクトル化靴紐
    (`dot`+`roll`=別コード経路)。**honest 域**: 座標 ≤1e5・n ≤1e5 で和は最大 2e15 < 2^53(box 周回スパイラルで実測=exact)。
  - `point_in_polygon`(KIND_REDUCE): 交差数(レイキャスティング)で内外判定。整数の外積で交差を決める(除算なし)。
    oracle=**巻き数アルゴリズム**(交差数とは別手法・両者は単純多角形の厳密内外で一致)。凹多角形も正しい(notch=outside を検証)。
    **境界(辺上)の点は実装依存**と開示し holdout から除外(交差 vs 巻き数が境界で分岐しうるため)。
  - `convex_hull`(**KIND_MAP**): Andrew の monotone chain で凸包。出力=**lex-min 頂点から CCW 順**の頂点列(共線点は除外
    =strict hull・scipy と一致)。oracle=`scipy.spatial.ConvexHull` の**頂点集合**比較(順序は C-vs-Python bit 一致で別途担保)。
    退化(3 未満の distinct / 全共線)は両者 [] で fail-soft。**2000 ランダム点集合で scipy と mismatch 0**を事前実測。
- **KIND_MAP**: convex_hull は出力 ≤ 入力長(頂点 ≤ n)だが 2 段 size-probe(上界 2n)を踏襲。
- **honest gate 実測(3 op とも passed=True・c_verified=true・ziglang cc)**: Python==独立 oracle diff 0.0 / C==Python bit 一致 diff 0.0。
- **work-graph op 波**: 3 幾何 op も `algo_gate` ノード化(`1 op=1 ノード`)→ `run-once` で無人 done(全 algo op 23 が gate 化)。
- **回帰**: `tests/test_algo.py` に幾何テスト群(既知解・scipy/numpy/matplotlib/巻き数の複数独立 oracle 照合・凸性/CCW/点内包の
  構造検証・fail-soft・退化・no-mutation・python exact・C bit 一致)。全スイート **4742 → 4765 passed / 0 failed**(+23)・ruff clean・mypy 新規 0。

### P6 敵対レビュー(2026-08-17, [[feedback_no_solo_ai_judgment]])
2 本の独立敵対レビュー Workflow(各 finding を検証エージェントが実 compile/実行/ストレスで再現)を並行実施:
- **P6a(polygon_area2 / point_in_polygon、4 レンズ・102 tool uses)= findings 0**。geometry-correctness / C-safety /
  gate-honesty / integration-focus すべてゼロ(整数厳密・境界開示・2^53 域を事前実測済み)。私も最悪ケース(box 周回スパイラル
  n=1e5)で 2×面積=2.0e15 < 2^53 を実測し op==numpy==C 一致を確認済み。
- **P6b(convex_hull、3 レンズ・85 tool uses)= 1 raw → 0 CONFIRMED**(1 REFUTED)。唯一の指摘「dedup 削除変異が difftest を
  通過」は**非欠陥**と検証で棄却: dedup は strict `<=0` monotone-chain pop + `hv<3` 後置チェックで既に保証される**防御的冗長**
  (両 backend で削除しても等価=200,000 重複多点集合で divergence 0)。検証エージェントが独立に確認=**2n size-probe はタイト
  非超過上界**(放物線入力で out_len=2n)/ **ASan+UBSan が 1104 hostile cases でクリーン**(out[] 書込 OOB なし・long long 外積
  overflow なし)/ C==Python bit 一致・Python==scipy 頂点集合 全一致 / CCW-from-lex-min 順序も test で担保 / qsort 不安定性は
  (x,y) 全順序比較子 + 隣接 dedup で無影響(=`sorted(set())`)。→ dedup が防御的冗長である旨の説明コメントのみ追記(挙動不変)。
- **結論**: P6 幾何 3 op に shipped bug なし。commit + push はこのセッション(`24bc8ad`)。

## P7 完遂記録 — 線分交差(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**幾何ツールキットを 1 op 拡張**: `segments_intersect`(KIND_REDUCE)= 2 閉線分 `[x1,y1,x2,y2,x3,y3,x4,y4]` が交差するか
(1.0/0.0)。**画像の直線/輪郭解析への橋渡し**。CLRS 33.1 の整数 orientation 法(proper crossing = 端点が相手の線を厳密に
またぐ + 4 つの共線 on-segment 特殊ケース)。整数座標 [-100000,100000] で外積は厳密(|cross| ≤ 8e10 が long long に収まる)=
C bit 一致。**oracle = `sympy.geometry` の Segment 交差**(記号計算=orientation とは全く別手法)。実測: 固定 8 ケース正解 +
**sympy と 2970 ランダム整数線分ペアで mismatch 0**(共線重複/T 字/端点共有/near-miss を含む)。退化(点)線分は sympy が
Segment を作れないため holdout から除外(op は一般 orientation ロジックで動くが未 gate=開示)。difftest passed(python exact /
C bit 一致 / c_verified)、work-graph ノード無人 done(全 algo op 24 が gate 化)。

### P7 敵対レビュー後の強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
3 レンズ敵対レビュー(検証エージェントが実 compile/実行で再現)= **1 raw → 1 CONFIRMED**(MED・gate-honesty)。**op 自体は
正しい**(sympy と全一致)が、**difftest holdout が d1/d3/d4 の on-segment 特殊ケース(端点が相手線分の内部に乗る=共有端点なし)
を単独理由の 1.0 判定として一度も駆動せず**、その分岐を落とした wrong op を gate が通す(50 holdout の判定が 1 つも変わらない)。
自己再現で確定(d3+d4 drop 変異が passed=True・`[0,0,10,0,3,0,3,5]`→0.0 誤り)。**修正**=各 on_seg 分岐(d1/d2/d3/d4)を単独理由と
する固定 holdout ケース(端点が相手内部・軸並行 4 + 対角 2)を追加 → **各分岐を落とすと difftest が FAIL**(d1/d2/d3/d4 すべて
passed=False)を自前確認。既知解テストにも端点-内部 4 ケースを追加。全スイート **4765 → 4772 passed / 0 failed**(+7)・ruff clean・
mypy 新規 0。

## P8 完遂記録 — 探索/選択(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**探索/選択アルゴリズム 2 種を algo tier に追加**(幾何から別ドメインへ移り tier を均等化)。比較ベースで任意の
(NaN-free)double を扱う=結果は index or 既存要素ゆえ exact(tol 0)・C bit 一致。
- **op(2)**: `binary_search`(KIND_REDUCE): sorted 列 `[target, v0..v_{n-1}]` の target の**最左 index**(lower bound)、無ければ
  -1.0。oracle=`bisect_left` + 存在確認(独立)。 / `kth_smallest`(KIND_REDUCE): `[k, v0..]` の k 番目に小さい値(0-indexed order
  statistic)を **quickselect**(median-of-three pivot・Lomuto)。**k 番目の値は順序非依存**ゆえ pivot 順が違っても C==Python bit
  一致。oracle=`sorted()[k]`(Timsort=別アルゴリズム)。median-of-three で sorted 入力も O(n)(n=40001 が <2s)。
- **honest gate 実測**: 両 op とも passed=True・python exact / C bit 一致 / c_verified。**各 5000 ランダムケースで oracle と
  mismatch 0**を事前実測。fail-soft=binary_search は空/無→-1.0、kth_smallest は k 域外/非整数/空→0.0。
- **work-graph**: 2 op も `algo_gate` ノード無人 done(全 algo op 26 が gate 化)。回帰=`tests/test_algo.py` に P8 群(既知解・
  bisect/sorted 照合・O(n²)ガード・fail-soft・no-mutation・python exact・C bit 一致)。ruff clean・mypy 新規 0。

### P8 敵対レビュー後の強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
2 レンズ敵対レビュー(実 compile/実行検証)= **1 raw → 1 CONFIRMED**(LOW・correctness)。**正しさ不変だが性能欠陥**:
kth_smallest の quickselect が単一 pivot Lomuto ゆえ **all-equal/低カーディナリティ大入力で O(n²)**(median-of-three は重複を
保護しない・n=40000 all-equal で 7.44s、sorted/reverse は高速)。テストは holdout n≤30・計時テストが sorted のみで未捕捉。
姉妹 quicksort は既に 3-way(Dutch flag)partition を使用。**修正**=kth_smallest を **3-way(Dutch national flag)partition** に
書換(equal-band で重複を畳む→all-equal を O(n) に・比較のみ+順序非依存で **C==Python==sorted()[k] parity 維持**)。自己再現で
確認=**all-equal n=40000 が 7.44s → 0.0019s**(O(n) 化)・correctness 5000 cases mism 0・difftest bit 一致。計時テストを
sorted/reverse/**all_equal/few_distinct** に拡張(退行を実際にガード)。

## P9 完遂記録 — 統計/集計(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**統計 op 2 種を algo tier に追加**: `count_distinct`(distinct 値数=整数 count)/ `mode_value`(最頻値・小さい方が tie 勝ち)。
比較ベース(任意 NaN-free double)・結果は count or 既存要素ゆえ exact(tol 0)。両 op とも copy を sort → run 走査(結果は
順序非依存で C の qsort と Python の sorted が違っても bit 一致)。oracle=`len(set())` / `collections.Counter`(独立機構)。
**★proactive 堅牢化**: mode_value のゼロ mode で ±0.0 混在時、C の unstable qsort と Python の stable sort で返り値の符号が食い違い
bit 不一致になりうる → **`+ 0.0` で −0.0→+0.0 正準化**(他値は不変)で C==Python を堅牢に(rle_encode の signed-zero 開示と同系)。
実測: 各 5000 ランダムケースで oracle mismatch 0・difftest passed(python exact / C bit 一致 / c_verified)。全 algo op 28 が gate 化。
ruff clean・mypy 新規 0。

### P9 敵対レビュー後の強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
2 レンズ敵対レビュー(実 compile/実行/変異検証)= **1 raw → 1 CONFIRMED**(MED・gate-safety)。**正しさ不変だが gate coverage gap**:
mode_value の `+0.0` 正準化を落とす変異を holdout が falsify できない(唯一の signed-zero ケース `[0.0,-0.0,0.0]` が両 backend で
+0.0-last にソート → 正準化削除でも bit 一致)。コメントが担保と主張する bit-check が正準化を一度も実際に駆動しない。**修正**=
`-0.0` が run 末尾に来ない `[0.0,-0.0]`・`[-0.0,0.0]` を holdout に追加(両順序=qsort tie 順に依らず片方は必ず発散)。自己再現で
確認=**正準化削除変異が difftest FAIL**・現行(正準化済)コードは追加ケースで bit 一致 pass。全スイート **4787 → 4796 passed / 0 failed**。

## P10 完遂記録 — 数論(第2部)(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**数論 op 2 種を追加**(P5 の整数機構の上に・category numtheory を共有)。整数を float64 で運ぶ(exact <2^53)・honest 域で全
モジュラー積が uint64/long long に収まる=C bit 一致 かつ Python==独立 oracle tol 0。
- **op(2)**: `is_prime`(KIND_REDUCE): **決定的 Miller-Rabin**(witness {2..37})。honest 域 0≤n≤2^32−1(a·a mod n が uint64 に
  収まり witness set が決定的=n<3.3e24 まで primality 証明)。oracle=`sympy.isprime`。★Carmichael 数(561/1105/1729/2465…)を
  正しく合成判定。 / `modular_inverse`(KIND_REDUCE): **拡張ユークリッド**で a^−1 mod m(gcd≠1 は −1.0)。域 a≤2^53・m≤2^53(Bezout
  係数は不変量 |q·s|=|old_s−new_s|≤2m で long long に収まる)・m=1→0。C の truncated mod を [0,m−1] に正規化(+m)して Python の
  floor mod と一致。oracle=builtin `pow(a,−1,m)`。
- **honest gate 実測**: 両 op passed=True・python exact / C bit 一致 / c_verified。**is_prime を sympy と 8000 random + 2000
  exhaustive(561 Carmichael 含む)で mism 0 / modular_inverse を pow と 8000 で mism 0** を事前実測。全 algo op 30 が gate 化。
  ruff clean・mypy 新規 0。

### P10 敵対レビュー後の強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
2 レンズ敵対レビュー(実 compile/実行/変異検証)= **1 raw → 1 CONFIRMED**(MED・c-safety-gate)。**op 自体は正しく overflow-safe**
(353 敵対ケースで検証)だが、**modular_inverse の holdout が宣言域 2^53 を駆動せず**(in-domain m が ~1e9 止まり)、C の
`long long→int` 幅縮小変異(2^53 域を壊す)が gate を bit 一致で通過。姉妹 pow_mod(base=exp=2^53 をピン)/ gcd_seq(2^53 ガード端)/
is_prime(near-2^32)は同種変異を捕捉するのに modular_inverse だけ未対応。**修正**=2^53 端ケース(`[2, 2^53−1]` coprime→inverse・
large coprime near 2^53・`[2^52, 2^53]` both even→−1)を holdout に追加(Bezout 演算が |q·s|~2m~2^54 を駆動)。自己再現で確認=
**`long long→int` 変異が difftest FAIL**・baseline は bit 一致 pass。oracle(pow)は既に対応済ゆえ holdout のみ追加。全スイート緑。

## P11 完遂記録 — ビット操作(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**ビット操作 op 2 種を追加**: `xor_reduce`(全要素の bitwise XOR)/ `popcount_total`(全要素の 1 ビット総数=Kernighan)。
非負整数を float64 で運び、域 [0, 2^53−1] で全値を 53 ビットに収める(XOR 結果も < 2^53=exact・popcount は小さい整数)=
C bit 一致 かつ Python==独立 oracle(`functools.reduce(operator.xor)` / builtin `int.bit_count()`=Kernighan とは別機構)tol 0。
両 op passed=True・python exact / C bit 一致 / c_verified。各 3000 ランダムケースで oracle mism 0 を事前実測。fail-soft=負/非整数/≥2^53→0.0。
全 algo op 32 が gate 化。ruff clean(FURB161 で `bin().count('1')`→`.bit_count()` 化)・mypy 新規 0。

### P11 敵対レビュー結果(2026-08-17, [[feedback_no_solo_ai_judgment]])
2 レンズ敵対レビュー Workflow(correctness + gate-safety、`wf_7d130631-c0f`)= **findings 0(欠陥なし)**。レビュアー1 は
`{findings:[]}`、レビュアー2 は「ゲート mutation testing(実装を壊してゲートが捕まえるか)」の最中に window 圧縮で中断
(結果未産出)。**規律に従い、死んだ background を蘇生せず、私が同じ mutation test を一次検証で完遂**: xor_reduce/popcount_total
の代表 7 変異(空初期化 acc=1 / OR 誤用 / 2^53 域境界 off-by-one / 負ガード除去 / Kernighan→shift[popcount≠bitlength] /
+2 誤り / 2^53 admit)を holdout に対し実行 → **全 7 変異を独立 oracle が捕捉**(oracle_err > 0)。**結論=P11 ゲートは
falsifying・確定欠陥なし**(`fed093a` は正当・follow-up commit 不要)。

## P12 完遂記録 — 拡張ユークリッド互除法(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**数論 op 1 種を追加**(P5 の整数機構 + P10 の Bezout 不変量の上に・category numtheory を共有=P5+P10+P12)。
`extended_gcd`(**KIND_MAP**): 入力 `[a, b]`(非負整数 ≤ 2^53)→ 出力 `[g, x, y]`(**厳密 3 値**、`a·x + b·y = g = gcd(a,b)`)、
域外は `[]` fail-soft。反復版 two-variable sweep で係数を計算。**係数は厳密**(不変量 `|q·s| = |old_s − new_s| ≤ 2·max(a,b) ≤ 2^54`
が C の long long に収まる)ゆえ C == Python bit 一致。domain は **[0, 2^53] inclusive**(2^53 は exact・係数 |x|,|y| ≲ 2^52 も
float64 で exact)。
- **★oracle 独立性の要点(P10 の教訓)**: Bezout (x,y) は非一意ゆえ「`a·x+b·y==g`」の**恒等式検証では符号/正準形の食い違いを
  gate が falsify できない**。→ oracle は**独立な再帰版拡張ユークリッド `_ext_gcd_rec`(別コード経路)で (g,x,y) を計算し要素一致**。
  反復版と再帰版は同一 canonical 係数を返す(再帰を展開すると反復になる=数学的に一致、`[0,b]`/`[a,0]`/`[0,0]`/等値の全端も一致確認)。
- **honest gate 実測(passed=True・c_verified=true・ziglang cc・70 cases)**: python==独立再帰 oracle **diff 0.0(exact)** /
  codegen **C==Python bit 一致 diff 0.0**。事前実測=**200,000 ランダム(2^53 域端含む)で 反復 op == 再帰 oracle mism 0 かつ
  `a·x+b·y==g==math.gcd(a,b)` 恒等式(bignum で独立検算)失敗 0**。fail-soft=短小/非整数/負/NaN/>2^53 → `[]`。
- **★ゲート mutation test(自己検証)**: swap x,y / negate x / drop old_s update / widen guard(>2^53 admit)/ wrong-length
  の 5 終端変異を**全て捕捉**(要素不一致 or 構造不一致 inf)。誤商 q+1 は op 自身が無限ループ(difftest harness の timeout が
  failure 検出)=終端する誤実装は全て falsify。
- **holdout(域端と全分岐を単独理由で駆動)**: 既知 `[35,15]→(5,1,-2)` 等 + coprime/非 coprime + 等値 `[7,7]` + 片方 0
  (`[0,5]`/`[5,0]`/`[0,0]`)+ a=1 + **2^53 域端**(`[2, 2^53−1]` coprime・large coprime near 2^53・`[2^52, 2^53]` gcd 2^52・
  `[2^53, 6]` inclusive 上端)+ 域外 fail-soft(短小/`>2^53`=`[2^53+2,3]`/非整数/負/NaN)+ random 48。
- **work-graph op 波**: extended_gcd を `algo_difftest --op` ゲートノード化(`1 op=1 ノード`・priority 0・tool capability・
  produces=gate JSON)→ `run-once --available tool:command` で **無人 done**(passed:true・c_verified・bit 一致マーカー生成)。
  = **全 algo op 33 が work-graph ゲート化**(32→33)。
- **回帰**: `tests/test_algo.py` に P12 群(既知値・Bezout 恒等式 random×5000・独立再帰 oracle 一致 random×5000・fail-soft・
  category grouping[numtheory=P5+P10+P12]・difftest python exact・C bit 一致)。全スイート **4827 passed / 0 failed**(test_algo.py
  単体 260)・私の全変更 ruff clean・mypy 新規 0(origin/master=15 と同数=net-new 0)。

### P12 敵対レビュー後の強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
3 レンズ敵対レビュー Workflow(correctness / c-safety+gate-honesty / integration、各 finding を検証エージェントが**実 compile/
実行の mutation で再現**、5 agents・125 tool uses)= **2 raw(同一根本原因)→ 1 CONFIRMED**(MED・gate-cannot-falsify)。**op 自体は
正しい**(200k + 全端で検証・再帰 oracle と非発散・in-domain で long long overflow なし)が、**difftest holdout の域外ケースが全て
operand `a` 側**(`[2^53+2,3]`/`[2.5,7]`/`[-1,7]`)で、唯一の bad-`b` ケース `[7,NaN]` は NaN が `bd>=0.0` で短絡し b の 3 ガード節を
一つも単独駆動しない → **`b` 側ガードの片側退行(a/b はコピペ対称ゆえ plausible)が両ゲート半分を通過**(P5/P7/P9/P10 と同じ gate-coverage
教訓)。**自己再現で確定**: `bd>=0` / `bd<=2^53` / `bd==int` を _PY/_C 両方から削除 → **全て `passed=True`(MISSED)**、対称な `a` 側削除は
全て `passed=False`(CAUGHT・a の域端が holdout にあるから)。**修正**=`[valid_a, finite_bad_b]` ケース(`[3, 2^53+2]`・`[7,-1]`・`[7,2.5]`)
を holdout と fail-soft テストに追加 → 再実測で **b 側 3 削除が全て CAUGHT(passed=False, pydiff=inf)**・baseline は 70 cases で bit 一致
pass。★**検証エージェントの honest 訂正を採用**(finding の過剰主張を却下): 「`bd<=2^53` 削除は b=2^62 で C long long overflow UB」は
**不正確** — b=2^62 で C(long long)と Python(bignum)は bit 一致(overflow なし)。真の誤りは**出力の精度損失**(Bezout 係数が > 2^53 で
float64 に厳密表現できず `a·x+b·y==g` が破れる)であり、`b<=2^53` 上限はこの精度を守る。機構は誤りだが欠陥と remedy は成立=採用。
