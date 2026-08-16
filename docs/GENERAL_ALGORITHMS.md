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

## 次(P2 以降)
- **P1.5(小)**: `imgevolve.py` に `algo`/`algo-c`/`algo-difftest` サブコマンド、Studio の op ブラウザに
  general tier を出す(design 段階計画「Studio の op ブラウザに新 tier を出す」)。
- **P2**: 数値計算(二分法/Newton/Simpson/Gauss)op 族。scalar/seq に加え `numeric` 系。
  累積順序に注意し tol の扱いを honest に(bit 一致でなく数値許容差を明示)。
- P3 文字列(+`text` 型)/ P4 グラフ(+`graph` 型)/ P5 圧縮・数論・暗号(教育用・honest 開示)。
