# TRIZ 40 発明原理 × ソフトウェア設計パターン × コンテナ型 — 構造選択マトリクス(fullseye)

> 作成 2026-09-02 / 対象 = `C:\dev\projects\imgevolve`(fullseye: ~1000 op、進化探索、`fscript`、Studio、C codegen)。
> 目的 = **6 か月後の自分が、設計のジレンマに当たったとき 2 分で「どの構造を選ぶか」を決める**ための参照表。
> 一般的なパターン解説は書かない。**fullseye の実ファイルで検証できる事実**と、**4 軸の採点理由**だけを書く。
> 引用した行番号は 2026-09-02 時点。ファイル名は `grep` で実在確認済み(未確認のものは「未確認」と明記)。

関連正本: `docs/FSCRIPT_DECISION.md`(判断の書き方の手本)/ `out/robustness-audit-2026-09-02/LEDGER.md`(発端の矛盾)/ `docs/NEXT_SESSION.md` / raptor `.claude/skills/triz-ideation/SKILL.md`(40 原理・39 特性の原典表)。

---

## §0 2 分で読む

1. **ジレンマを 39 特性の 2 語で言う**(例: 「信頼性 #27 を上げると測定精度 #28 が下がる」)。§5 の対応表で原理候補が出る。
2. **§3a の当該原理の行**を読む。パターンごとに 4 軸(S 速度 / M メモリ / G 入出力汎用性 / D 検出性)の 1〜5 点と、**3 点以下の軸をどの原理・パターン・コンテナで埋めるか**(短所のカバー)が書いてある。
3. パターンを決めたら **§3b でコンテナ**を選ぶ(同じ 4 軸 + 古典的な落とし穴 + カバー)。コンテナが先に決まっている(ndarray を触るしかない等)なら **§3c で原理→コンテナ**を逆引きする。
4. **§4 は fullseye への具体適用**。fail-soft の矛盾を解いた実例(2026-09-02、`backend_safe.py` に実装済みの Mediator+台帳)と、順位づけした次の 9 手。
5. 採点は「fullseye にその組合せを適用したとき」の値。**汎用のパターン評価ではない**。理由を読んで納得できなければ点を信じないこと。

読み方の記号: `S/M/G/D = 5/4/5/5` = 速度 5・メモリ 4・汎用性 5・検出性 5。**3 以下の軸には必ずカバー方法が付く**(付いていなければ、その組合せをそのまま使うと弱点が残る)。マトリクスの `●` = 強い対応(採点あり)、`○` = 弱い対応(採点なし・理由 1 行)、空欄 = 対応なし(パディングしない)。

---

## §1 方法

### 1.1 原理 → パターンの写像規則

TRIZ 原理は「物質・場」の抽象操作、設計パターンは「責務・依存の配置」。両者を結ぶのは **何を分離・統合・仲介・記録するか**という構造動詞である。写像は次の 3 段で行った(§3a の「なぜ」列はこの 3 段の要約):

| 段 | 問い | 例(#24 仲介) |
|---|---|---|
| 1. 原理の構造動詞 | 原理が対象に何をするか | 「A と B の間に C を置く」 |
| 2. ソフトウェアの主語 | 対象は呼出し関係か・データか・時間か | 呼出し関係(21 の `_safe` ラッパと台帳) |
| 3. 一致するパターン | 同じ構造動詞を持つパターン | Mediator / Facade / Adapter / Proxy / Bridge |

一致度: **●** = 構造動詞が同じ(原理の定義がそのままパターンの定義になる)/ **○** = 比喩的に一致(役に立つが、別の原理の方が本命)/ 空欄 = 一致しない。#29 流体・#37 熱膨張・#38 酸化剤・#39 不活性雰囲気は物理原理のため ○ が多い。**無理に ● を立てていない**。

### 1.2 4 軸の 5 段階(具体基準)

採点は「**fullseye の facade `api.apply(v, name, a, b)` 経路にその構造を入れたとき**」を基準にする。hot path = 1 op 呼出し(4 MP 画像で数 ms〜数十 ms、`docs/FSCRIPT_MEASUREMENTS.md`)。

**S 速度(speed)** — 成功経路に加わる実行コスト

| 点 | 基準 |
|---|---|
| 5 | 成功経路に呼出しオーバーヘッドを足さない(失敗時のみ仕事をする / 定数の分岐 1 個) |
| 4 | 呼出しごとに O(1) の作業(dict lookup 1 回、小オブジェクト 1 個の生成) |
| 3 | 呼出しごとに O(1) だが同期・ロック・thread-local を伴う、または小さな O(k) 走査(k = op 数・stage 数) |
| 2 | データに対する追加パス 1 回(O(N)、N = 画素数) |
| 1 | データの追加パス複数回、または working set の複製・デバイス転送を伴う |

**M メモリ(memory)** — 追加確保

| 点 | 基準 |
|---|---|
| 5 | 追加確保なし |
| 4 | 上限つき定数(ring 256 件、`lru_cache(64)` 等) |
| 3 | O(op 数) or O(stage 数) のメタデータ(数百〜数千件の小オブジェクト) |
| 2 | 呼出しごとに O(N) の一時配列 1 本 |
| 1 | working set を複製する、または上限なしに成長する |

**G 入出力の汎用性(I/O generality)** — その構造が受け入れる入出力の形

| 点 | 基準 |
|---|---|
| 1 | 固定の単一配列シグネチャ `(v, a, b) -> array`(現 `ops.Op.fn`) |
| 2 | 単一入力 + 固定 kwargs(`coerce`, `device`) |
| 3 | sort タグつきの単一入力・単一出力(`in_sort`/`out_sort` を尊重) |
| 4 | 型つき多入力 or 多出力(`imgops_nary` の arity 2、`Attempt` の (ok, value, reason)) |
| 5 | 任意の型つき多入力・多出力(`graphengine.FullseyeGraph` の DAG、`fslib` の ObjectSet) |

**D 検出性/監査可能性(detectability of silent failure)** — 黙って壊れたときに気づけるか

| 点 | 基準 |
|---|---|
| 1 | 沈黙(例外を握りつぶし記録なし。2026-09-02 以前の 21 個の `backends_*._safe`) |
| 2 | 記録されるが表面化しない(問い合わせないと分からない。旧 `backends._ERRORS` ring) |
| 3 | 1 回だけ表面化する(warn once)or 環境変数でのみ strict 化 |
| 4 | 記録 + 表面化 + **呼出しごとに方針選択可**(`on_error=`) |
| 5 | 4 に加えて **分類(taxonomy)があり CI が空を断言できる**(`fallbacks()` を assert) |

### 1.3 「短所のカバー方法」列の規約

- 各行で **3 点以下の軸**について、(a) 何が弱いか (b) **どの原理 #N / パターン / コンテナ**がそれを埋めるか (c) fullseye で既にやっていればファイル名 — を書く。
- カバーは「別の行の組合せを重ねる」形で書く。これにより **§3a・§3b・§3c の行どうしがリンク**し、珍しい状況(例: メモリが極端に足りない + 検出性を落とせない)でも「行 A の弱点を行 B で埋める」経路が辿れる。
- 4〜5 点の軸にはカバーを書かない(書く必要がないので空欄)。

---

## §2 パターン語彙(fullseye での実在箇所つき)

「既存」列は `grep` で実在確認したファイル。**「(未使用)」は fullseye コアに該当構造が無いことを確認した**という意味(tests/ tools/ examples/ は除外して検索)。

### 2.1 GoF 23 + Null Object

| パターン | 何か(1 行) | fullseye 既存(検証済) | 適用余地 |
|---|---|---|---|
| Strategy | 同じ契約の実装を差替える | `fslib.py:379-423` `PROFILES` と `op(name, backend)` の `_REGISTRY[name][backend]`(numpy を oracle に native を選ぶ)/ `ops.Op.fn` | `ops.REGISTRY` 側は `gaussian` と `cv_gaussian` が**別 op**(`FSCRIPT_DECISION.md §1.5`)→ backend 次元の統合(§4 候補 8) |
| Decorator | 呼出しを包んで横断関心を足す | `backend_safe.guard()`(L184)/ `backends._safe`(L64-69)と 21 の `backends_*._safe`(例 `backends_scipy.py:16-`)が **すべて `backend_safe.guard` へ委譲**(2026-09-02) | — |
| Facade | 複雑系に単純な入口 | `fullseye/__init__.py`(`__all__` L307-)/ `api.apply(on_error=, template=)`(L1109)/ `api.run_pipeline(on_error=)`(L1184) | 多入力(§4 候補 2) |
| Mediator | 多対多の連絡を 1 点に集める | `backend_safe.record()`(L113)= 全ラッパが報告する 1 点(2026-09-02 新設、22 ラッパ配線済) | Studio・進化ループからの購読 |
| Observer | 変化を購読者に通知 | `studio.py` Qt signal `.connect(` 177 箇所 / `warnings.warn(FullseyeFallbackWarning)`(`backend_safe.py:137`) | Studio の台帳購読(fallback 発生をステータスバーへ) |
| Chain of Responsibility | 順に処理者へ渡す | `api.py:875-895` op 名 → HALCON alias の順に解決(「Exact op name wins」)/ `api._coerce_input`(L907)/ `_guard_input`(sort 検査 → policy) | alias 曖昧は `api.ambiguous_aliases` で公開済(`__init__.py:312`)|
| Template Method | 骨格固定・一部を子で実装 | `comm.Channel`(`comm.py:40-57`、未対応は `NotImplementedError`)/ 各 `backends_*.build(Op, IMAGE, ...)` の共通形 | — |
| Null Object(非 GoF) | 「何もしない」を正規の値で返す | `backend_safe.fallback(v, out_sort)`(L287: feature→0.0 / region→zeros / contour→空 cs / match→[0,0,0]) | **これが「壊れた op = 働く恒等」問題の正体**。単独では D=1、台帳と組で 4 以上 |
| Command | 操作をオブジェクト化 | (未使用: `QUndoStack`/`QUndoCommand` 0 件) | Studio の undo/redo・「パラメータ窓 → スクリプト行生成」(NEXT_SESSION B-4) |
| Memento | 状態の snapshot/復元 | `fsruntime.GoldenVector`(L60: inputs→expect の凍結証拠)/ `fsruntime.sign()`・`Recipe.digest()` / `fssystem.system_snapshot()`(L175) | — |
| Proxy | 代理が本体を遅延・制御 | `torch_lazy._LazyTorch`(L83、torch 800 ms import の遅延) | GPU 経路の Circuit Breaker(§4 候補 3) |
| Flyweight | 共有して確保を減らす | `annotate.py:276,296` `lru_cache` のフォント/ラスタ共有(弱い一致) / ndarray view(`tomography.py:1657 sliding_window_view`) | — |
| Visitor | 構造と操作を分離 | (未使用: `class *Visitor`/`visit_` 0 件。`codegen.py`・`algo_codegen.py` は emit 関数群) | fscript の eval/codegen 分離監査(§4 候補 7) |
| Interpreter | 文法をクラスで表し評価 | `fscript.py` `Parser`(L234)+ `Node` 群(L154-227)+ `Env`(L541) | — |
| Iterator | 順次アクセスを抽象化 | `fslib.ObjectSet.__iter__`(L298)/ `acquire.py:269` `yield self.grab()`(フレーム流) | — |
| Builder | 段階的に組み立て最後に固める | `fsruntime.compile_recipe(Recipe) -> ReadyRecipe`(L201) | — |
| Prototype | 複製で生成 | `evolve.py:23,98,102` genome `.copy()`(ndarray) | — |
| Adapter | 異なる I/F を合わせる | `oss_adapter.py`(`BlockMatching`/`SGBM`/... cv2 を fullseye 規約へ)/ `accel_bridge.core_to_accel()`(L35) | — |
| Bridge | 抽象と実装を別階層で独立変化 | `fslib` L1 契約(「One operator, several backends」L11)/ `accel_bridge.plan()`(L99: CPU/GPU 島分割) | `ops.REGISTRY` へ拡張(§4 候補 8) |
| Composite | 木構造を同一 I/F で | `graphengine.FullseyeGraph`(L24: nodes dict + `topological_order` + nary) | facade `apply` の多入力(§4 候補 2) |
| State | 状態で振舞いを変える | `fsruntime.FullseyeRuntime.start/inspect`(Recipe→ReadyRecipe→Runtime→Verdict)/ `backend_safe._STRICT` | GPU 経路の open/closed(§4 候補 3) |
| Singleton | 唯一のインスタンス | `fssystem.SYSTEM_PARAMS`(L68)/ `backend_safe` のモジュール状態(`_EVENTS`/`_COUNTS`/`_WARNED`) | — |
| Abstract Factory | 関連物の生成を族で | 各 `backends_*.build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm)` が `Op` 列を生成(`ops.py:969`) | — |
| Factory Method | 生成をサブクラス/関数に委ねる | `ops._c(name)`(L805: C 文生成器の解決)/ `Op(...)` 組立 | — |

### 2.2 アーキテクチャ/堅牢性パターン

| パターン | 何か | fullseye 既存(検証済) | 適用余地 |
|---|---|---|---|
| Pipeline / Pipes-and-Filters | 段の列でデータを流す | `api.run_pipeline`(L40 の docstring 側)/ `ops.Stage`(L1019)/ `ops.decode(genome)`(L1027) | — |
| Registry | 名前→実装の表 | `ops.REGISTRY`(L921 list)/ `RT`・`_BY_NAME`(L922-923 dict、**後勝ち**)/ `DROPPED_DUPLICATES`(L1003 付近、捨てた重複を残す) | param spec メタデータ(§4 候補 4) |
| Plugin | 実行時に発見・追加 | (静的: `ops.py:969` が backend モジュール列を明示 import して `build`。entry_points 0 件) | 外部 op パックの登録点(将来) |
| Result / Either | 成否と理由を値で持ち回る | `metriccontract.Attempt`(L170: ok/value/reason/metric、`__bool__`)/ `pyramid_gate.GateResult`(L47) | op 出力への拡張(§4 候補 2) |
| Circuit Breaker | 連続失敗で経路を遮断 | (未使用: `circuit`/`breaker` の hit は `algo.py` の short-circuit 注記のみ) | GPU 経路(§4 候補 3) |
| Bulkhead | 区画分離で波及を止める | (未使用) | 進化探索の per-op 予算(弱) |
| Retry / Backoff | 再試行 | (コア未使用。`learn_evis.py`・`tools/` のみ) | 通信 `comm.py` の再送(対象外) |
| Lazy / Memoize / Cache | 遅延・記憶 | `torch_lazy.py` / `annotate.py:276` `lru_cache(64)` / `volio.py:430` `np.load(mmap_mode="r")` | 台帳 ID→Op のキャッシュは既に dict |
| Object Pool | 生成物を使い回す | (未使用。`accel.py:275` 注記「GPU 常駐のまま」は意図のみ) | GPU バッファ(RTX5090 ゲート後) |
| Event Sourcing / Ledger | 事象を追記し状態を導出 | `backend_safe._EVENTS`(L60、ring 256)+ `_COUNTS` + `fallbacks()`/`events_since(mark())` / `ops.DROPPED_DUPLICATES` / `tests/test_backend_safe.py` | CI 常設 probe(§4 候補 1) |
| Saga | 多段の補償つき手続き | (未使用) | — |
| Health Check / Probe | 生存・退化を能動検査 | `tests/test_backends_typed_liveness.py` / `out/robustness-audit-2026-09-02/probe_runtime_degeneracy.py` / `fsruntime.GoldenVector` / `fullseye.capabilities()`(`__init__.py:294`) | `selfcheck()` + CI 常設(§4 候補 1) |
| Feature Flag / Policy Object | 挙動を設定で切替 | `fssystem.set_system/get_system/system()`(L123-160)/ `IMGEVOLVE_STRICT_BACKENDS`・`FULLSEYE_STRICT`・`FULLSEYE_QUIET_FALLBACK`(`backend_safe.py:75-76`)/ `apply(coerce=, device=, on_error=)` + `FULLSEYE_ON_ERROR`(`api._policy` L1028) | op 単位の既定 policy(§3a #3) |
| Sentinel / Tainted value | 特別値で状態を運ぶ | `api._LABEL_READING_OPS`(L904 frozenset)/ `api._NDIM_OK`(L1025)/ `np.ma.is_masked`(`mathops.py:139`)/ `fslib.FsNotReady` | sort 跨ぎ恒等の検出(§4 候補 1・6) |
| Tagged output / Provenance | 出力に来歴を付ける | `fsruntime.sign()`・`Recipe.digest()`(L105)/ `backend_safe.record()` の `source` タグ(op/gpu/import/input、`api.py:1058,1095,1104,1230`・`ops.py:979`) | run_pipeline の trace(§4 候補 6) |

---

## §3a マトリクス 1: TRIZ 40 原理 × 設計パターン

### 3a.1 強対応マトリクス(40 × 12)

列 = 数値 op ライブラリに最も効く 12 パターン。Str=Strategy/Registry, Dec=Decorator, Fac=Facade, Med=Mediator, Nul=Null Object, Res=Result/Either, Pip=Pipeline/Composite, Lzy=Proxy/Lazy/Cache, Led=Ledger/Event Sourcing, Pol=Policy/Feature Flag, Prb=Health Probe, Prv=Provenance/Tagged output。`●` 強 / `○` 弱 / 空欄 なし。

| # | 原理 | Str | Dec | Fac | Med | Nul | Res | Pip | Lzy | Led | Pol | Prb | Prv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 分割 | ○ | | | | | ● | ● | | | | | ○ |
| 2 | 引き出し | | ● | ● | ● | | | | | | | | |
| 3 | 局所的性質 | ● | | | | | | | | | ● | | ○ |
| 4 | 非対称化 | | | | | | ● | | | | ● | | |
| 5 | 統合 | ● | | ○ | ● | | | ● | | | | | |
| 6 | 多用途化 | | | ● | | | | | | | | | |
| 7 | 入れ子 | | ● | | | | | ● | | | | | |
| 8 | 釣り合い | | | | | ○ | | | ● | | | | |
| 9 | 先取り反作用 | | ○ | | | | | | | | | ● | |
| 10 | 先取り作用 | | | | | | | | ● | | | ○ | |
| 11 | 緩衝 | | | | | ● | | | | | | | |
| 12 | 等ポテンシャル | ● | | ● | | | ○ | | | | | | |
| 13 | 逆転 | | | | | | | | | ○ | ● | | |
| 14 | 球面化 | | | | | | | | | ○ | | | |
| 15 | 動性化 | ● | | | | | | | | | ● | | |
| 16 | 部分的に | | | | | | ○ | | | | | ● | |
| 17 | 多次元化 | | | | | | | ● | | | | | ● |
| 18 | 振動 | | | | | | | | | | | ○ | |
| 19 | 周期化 | | | | | | | | | ○ | | ● | |
| 20 | 有用作用継続 | | | | | | | ○ | ● | | | | |
| 21 | 高速化 | | ● | | | | | | ● | | | | |
| 22 | 災い転じて福 | | | | | | | | | ● | | ● | |
| 23 | フィードバック | | | | | | | | | ● | | ● | ○ |
| 24 | 仲介 | | ○ | ● | ● | | | | ○ | | | | |
| 25 | セルフサービス | ● | | | | ○ | | | | | | ● | |
| 26 | コピー | | | | | | | | ○ | | | ● | ● |
| 27 | 使い捨て | | | | | | ○ | | | | | | |
| 28 | 機械系の置換 | ● | | | | | | | | | | | |
| 29 | 流体 | | | | | | | ○ | | | | | |
| 30 | 柔らかい膜 | | ● | | | | | | | | | | |
| 31 | 多孔質 | | | | | | | | ○ | | | | |
| 32 | 色変化 | | | | | | | | | ○ | | | ● |
| 33 | 同質性 | ● | | | ● | | ● | | | | | | |
| 34 | 排除と再生 | | | | | | | | ● | ● | | | |
| 35 | パラメータ変化 | ○ | | | | | | | | | ● | | |
| 36 | 相変化 | | | | | | | | ○ | | ● | | |
| 37 | 熱膨張 | | | | | | | | ○ | | | | |
| 38 | 強い酸化剤 | | | | | | | | | | ● | ● | |
| 39 | 不活性雰囲気 | | | | | ● | | | | | | | |
| 40 | 複合材料 | ● | ● | | | | | | | ● | ● | | |

### 3a.2 原理ごとの対応パターンと 4 軸採点(fullseye 適用時)

各行: パターン | なぜ一致するか | S | M | G | D | 短所のカバー(3 点以下の軸のみ)。採点は §1.2 の基準。「既存」= 検証済ファイル。

#### #1 分割(Segmentation)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Result / 例外分類(taxonomy) | 「失敗」を backend-absent / op-failed / input-sort-mismatch に**分割**すると台帳が読める。既存: `backend_safe.record(source=op\|gpu\|import\|input)` | 5(失敗時のみ) | 4(ring 256) | 5(シグネチャ不変) | 5 | — |
| Pipeline / Pipes-and-Filters | op を独立 filter に分割。既存 `ops.Stage`・`api.run_pipeline` | 5 | 2(段ごとに O(N) 中間配列) | 3(単一 sort の鎖) | 2(段の失敗が次段の入力に化ける) | M: #34 排除と再生 × Object Pool(中間バッファ再利用、§3b Pipeline×ndarray)/ G: #17 多次元化 × Composite(`graphengine`)/ D: #23 × Ledger(段ごとに `current_op` で帰属、既存 `backend_safe.current_op`) |
| Bulkhead(○) | op ごとの予算区画。進化の 1 個体が全体を止めないため | 3(区画ごとの計時) | 4 | 5 | 3(超過は分かるが原因は分からない) | S: #21 高速化 × Lazy(計時を失敗時のみ)/ D: #23 × Ledger に timeout 種別を足す |

#### #2 引き出し(Extraction)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Decorator | 横断関心(例外握り・sanitize)を op 本体から**引き出す**。既存 `backend_safe.guard` | 5(try は成功時ゼロコスト) | 5 | 1(`(v,a,b)` 固定) | 4(guard 経由なら記録) | G: #17 × Composite(nary は `graphengine._eval` が別経路で吸収、§4 候補 2) |
| Facade | 内部 API 群から利用者向け面だけ引き出す。既存 `fullseye/__init__` | 4(名前解決 1 回) | 3(`__all__` 400 行 + alias dict) | 2(`coerce`,`device`,`on_error` 固定 kwargs) | 4(`on_error=` + 入力 sort 記録、2026-09-02) | G: #17 × Composite(§4 候補 2) |
| Mediator | 21 か所に散った握りつぶしを 1 点へ引き出す。既存 `backend_safe.record` | 5 | 4 | 5 | 5 | — |

#### #3 局所的性質(Local Quality)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Strategy / Registry メタデータ | op ごとに違う性質(sort、arity、param 型)を表に持つ。既存 `ops.Op(in_sort,out_sort)`、`api._LABEL_READING_OPS`(局所例外) | 4(dict lookup) | 3(O(op 数)) | 4(型つき param spec で kwargs 化可能) | 4(範囲外を検出可) | M: 許容(861 op × 数百 B = 数百 KB)。カバー不要だが、成長時は #26 コピー × Flyweight(共通 spec を共有) |
| Policy(op 単位の on_error)| 計測 op は fail-closed、描画 op は fail-soft — 局所で方針を変える。既存 `metriccontract`(計測だけ strict) | 5 | 3 | 5 | 5 | M: 上と同じ表に相乗り |

#### #4 非対称化(Asymmetry)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Result(ok/value/reason) | 成功と失敗を対称な「値」にせず、失敗側だけ理由を持つ**非対称**な型。既存 `metriccontract.Attempt` | 4(小オブジェクト 1 個/呼出し) | 4 | 4 | 5 | — |
| Policy(strict vs tolerant の二重契約) | 計測は fail-closed、画像は fail-soft の非対称。既存 `MetricContractError` + `attempt()`(契約違反だけ翻訳、他の例外は素通し `metriccontract.py:195-`) | 5 | 5 | 5 | 5 | — |

#### #5 統合(Merging)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Composite(多入力を 1 つの入力に統合) | `apply((img1,img2), 'add_image')`。既存 `graphengine.add(inputs)`、未: facade | 5 | 5 | 5 | 4(arity 不一致は明示エラーにできる) | — |
| Mediator(22 ラッパの統合) | 既存 `backends._safe` + 21 の `backends_*._safe` → `backend_safe.guard`(配線済) | 5 | 4 | 5 | 5 | — |
| Registry(op 宇宙の統合) | 進化 `ops.REGISTRY` と台帳 op(`backends_typed`)の統合。既存 `ops.py:969` `_extra += _b.build(...)` | 4 | 3 | 3 | 3(同名は**後勝ち**で黙って消えていた) | D: #23 × Ledger — 既存 `ops.DROPPED_DUPLICATES`(捨てた分を残す)+ `tests/test_op_contracts.py` で assert |

#### #6 多用途化(Universality)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Facade `apply` が全 sort・全 backend で 1 入口 | 1 つの関数が image/region/volume/points を受ける | 4 | 3 | 2(単入力・a,b 2 ノブ) | 4 | G: #17 × Composite(多入力、§4 候補 2)+ #3 × param spec(型つき kwargs、§4 候補 4) |
| Adapter(○) | cv2/skimage/torch を同じ `(v,a,b)` に合わせる。既存 `oss_adapter.py` | 4 | 2(dtype 変換で O(N) 複製、`_to_u8`) | 3 | 2(変換誤差は沈黙) | M: #26 × view(変換不要な dtype は素通し)/ D: #26 コピー × Probe(`difftest`/`parity.py` の cross-backend 比較、既存 `docs/PARITY_CROSSBACKEND.md`) |

#### #7 入れ子(Nested Doll)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Decorator の積層 | `coerce → guard → fn → sanitize → region01` の入れ子。既存 `backend_safe.guard` + `sanitize`(L331) | 4(層ごとに関数呼出し 1 回 ≈ 数百 ns) | 5 | 1 | 4 | G: 上記 #2 と同じ |
| Composite(graph in graph) | サブグラフを 1 ノードとして使う。既存 `FullseyeGraph.to_dict/from_dict` は平坦(入れ子未対応) | 4 | 3 | 5 | 3(内側の失敗が外に伝わらない) | D: #23 × Ledger の `current_op` を graph ノード ID で階層化(`"g1/n3"`) |

#### #8 釣り合い(Anti-Weight)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Lazy(import 重量を遅延で相殺) | torch 800 ms を必要時まで持ち上げない。既存 `torch_lazy._LazyTorch` | 5(初回のみ) | 5 | 5 | 3(遅延 import の失敗が初回呼出しで露見) | D: #9 先取り反作用 × Probe(`fullseye.capabilities()` で事前申告、既存) |
| Null Object(○) | 失敗を「無害な値」で釣り合わせる — **釣り合いは沈黙を生む** | 5 | 5 | 3 | **1** | D: #24 × Mediator + #23 × Ledger(**単独使用禁止**。§4 実例) |

#### #9 先取り反作用(Preliminary Anti-Action)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Probe(import 時 or 明示 `selfcheck()`) | 壊れた op を利用者が踏む**前に**検出。既存 `test_backends_typed_liveness.py`・`probe_runtime_degeneracy.py`(CI/手動のみ) | 5(hot path 外)/ import 時なら 1(861 op 実行) | 4 | 5 | 5 | S: **時間分離** — import 時ではなく CI と `fullseye.selfcheck()`(§4 候補 1) |
| Decorator(入力 sort 検証)(○) | 不正入力を op の前で止める。既存 `api._check_input_sort`(ndim/dtype)→ `_guard_input` が policy=raise なら例外、それ以外は `source="input"` で記録 | 4 | 5 | 3 | 4 | G: #35 × Policy(`coerce=False` + `on_error="raise"`)。sort 跨ぎ恒等は捕まえない → §4 候補 1 |

#### #10 先取り作用(Preliminary Action)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Builder / 事前コンパイル | 実行前に検証・固定。既存 `fsruntime.compile_recipe -> ReadyRecipe`(golden 照合込み) | 5(実行時ゼロ) | 3(ReadyRecipe の複製) | 4 | 5(golden 不一致は `FsNotReady`) | M: 許容(recipe は KB 単位) |
| Cache / Memoize | カーネル・フォントを先に作る。既存 `annotate.lru_cache(64)`。未: `accel._gauss_kernel` は毎回生成 | 5(hit 時) | 4 | 5 | 2(古いキャッシュは沈黙) | D: #26 × Provenance(キャッシュ鍵に version/fingerprint。既存 `docs/ops` の frontmatter fingerprint の流儀) |
| Probe(○) | 事前検査は #9 の方が本命 | — | — | — | — | — |

#### #11 緩衝(Cushioning)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Null Object(sort 妥当な fallback) | 失敗時に下流を壊さない値。既存 `backend_safe.fallback` | 5 | 5 | 3 | 1(単独) | D: #24 Mediator × #23 Ledger × #32 色変化(warn once)= 既存 `guard`+`record`+`FullseyeFallbackWarning`。**緩衝は必ず記録と組にする** |
| Circuit Breaker | 連続失敗する経路を遮断し再試行コストも緩衝。未使用 | 5(open 後は分岐 1 個) | 4(op ごとの状態 dict) | 5 | 4 | — |
| Retry(○) | 決定的な数値 op には無意味(同じ入力は同じ失敗)。通信のみ | — | — | — | — | 適用外 |

#### #12 等ポテンシャル(Equipotentiality)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| 一様シグネチャ(Strategy) | 全 op が `(v,a,b)`、持ち上げ不要で差替え可。既存 `ops.Op.fn` | 5 | 5 | **1** | 3 | G: #3 × param spec(型つき kwargs を `a,b` に写像する層、§4 候補 4)+ #17 × Composite(nary、§4 候補 2) |
| Facade(HALCON alias を同じ高さに) | `api.py:875` 名前 → alias | 4 | 3 | 2 | 3 | 上と同じ |
| Result 一様型(○) | 全 op の返りを `Attempt` 型に揃えると facade が破壊的変更 | 4 | 4 | 4 | 5 | G/破壊性: **条件分離** — 内層は Result、facade は値(§4 候補 7) |

#### #13 逆転(The Other Way Around)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Policy(既定の反転: fail-soft 既定 → strict 既定) | 「既定が握る」を逆にすると CI が真実を語る。既存 `IMGEVOLVE_STRICT_BACKENDS` は opt-in | 5 | 5 | 5 | 5(CI で strict、利用者は fallback) | — |
| Ledger 逆引き(○) | 「op → 失敗」でなく「失敗 → op」で読む(`fallback_counts()`) | 5 | 4 | 5 | 5 | — |

#### #14 球面化(Spheroidality)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Ledger の ring(○) | 「直線的に伸びる log」を「環状」にする。既存 `_EVENTS` + `del _EVENTS[:-256]` | 4(list 切詰めは O(1) 償却でない: 溢れるたび O(256)) | 4 | 5 | 3(**古い事象が消える**) | S: §3b Ledger×deque(maxlen)/ D: #23 × `_COUNTS`(件数は消えない、既存) |

#### #15 動性化(Dynamicity)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Strategy(実行時 backend 切替) | 既存 `fslib.PROFILES`(studio/reference/industrial) | 4 | 3 | 4 | 3(profile 間の差は parity test 頼み) | D: #26 × Probe(`difftest`/`parity.py` を profile ペアで) |
| Policy / State(実行時 strict 切替) | 既存 `backend_safe.strict_mode()` context manager | 5 | 5 | 5 | 4 | — |

#### #16 部分的に(Partial or Excessive Action)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Probe(標本抽出) | 全 861 op を毎回でなく構造データ 1 本で「多くも少なくもなく」検査 | 5(hot path 外) | 4 | 5 | 4(標本外は見ない) | D: #19 周期化 × CI 常設 + #26 × 乱数ではなく**構造データ**(memory `feedback_random_test_data_hides_structural_defects`) |
| Result(部分成功)(○) | 「一部の点だけ測れた」を値で返す。既存 `attempt_all` | 4 | 4 | 4 | 5 | — |

#### #17 多次元化(Another Dimension)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Composite / Graph(鎖 → DAG) | 1D の stage 列を 2D の DAG に。既存 `graphengine.FullseyeGraph` | 4(topo sort O(V+E) 1 回) | 3(ノード dict) | 5 | 3(`validate()` は構造のみ) | D: #23 × Ledger(ノード ID で帰属) |
| Provenance(出力に来歴の次元を足す) | 値 + (op, backend, fallback?) | 4 | 4 | 3(ndarray subclass は numpy 演算で剥がれる) | 5 | G: **空間分離** — 配列に付けず `run_pipeline` の trace(side channel dict)に付ける(§4 候補 6) |

#### #18 振動(Vibration)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Probe(ファジング = 入力を揺らす)(○) | 既存 `tools/chain_fuzz.py`。ただし `TYPE_CHECKS['labels']` が緩く自己参照(LEDGER #9) | 5(CI) | 4 | 5 | 3 | D: #38 強い酸化剤 × strict 述語(型契約テストを進化側の厳しい sort 契約に揃える) |

#### #19 周期化(Periodic Action)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Probe(CI 常設の周期実行) | 連続監視でなく commit ごと。既存 `tests/test_op_example_coverage.py` | 5 | 5 | 5 | 4 | — |
| Ledger の周期 flush(○) | 長時間バッチで ring が溢れる前に `events_since(mark())` で回収。既存 API | 5 | 4 | 5 | 4 | — |

#### #20 有用作用継続(Continuity of Useful Action)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Lazy / 常駐 Runtime | import 1.8 s を 1 回で済ませ、以後は休みなく処理。既存 `fsruntime.FullseyeRuntime.start` | 5 | 3(常駐分) | 4 | 4(`deadline_ms` 超過は Verdict) | M: 許容(設計要件 `FSCRIPT_DECISION.md §1.4`「Runtime 常駐が必須」) |
| Pipeline(○) | 段間で GPU 常駐(`accel.py:275` 注記) | 4 | 2 | 3 | 2 | M/D: #36 相変化 × Object Pool + Ledger の `source="gpu"` |

#### #21 高速化(Hurrying / Skipping)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Decorator の zero-cost 成功経路 | try/except は成功時にコスト無し。guard は失敗時だけ働く | 5 | 5 | 1 | 4 | G: #2 と同じ |
| Cache(hit で丸ごとスキップ) | 既存 `annotate.lru_cache` | 5 | 4 | 5 | 2 | D: #10 と同じ(鍵に fingerprint) |

#### #22 災い転じて福(Convert Harm into Benefit)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Ledger(失敗記録 = dead-op 監査) | 8 Agent の監査を `fallbacks()` 1 回に置き換える。既存(2026-09-02) | 5 | 4 | 5 | 5 | — |
| Probe(ファザーのクラッシュ = 回帰テスト) | 既存 `tests/test_fix_clahe_coverage.py` のような「発見 → テスト化」 | 5 | 5 | 5 | 4 | — |

#### #23 フィードバック(Feedback)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Ledger → CI assert | 出力(失敗)を入力(ゲート)に戻す。`assert fullseye.fallbacks() == []` | 5 | 4 | 5 | 5 | — |
| Observer(warn once / Studio 通知) | 既存 `FullseyeFallbackWarning`、Studio 未 | 5(初回のみ) | 4(`_WARNED` set) | 5 | 3(2 回目以降は沈黙 = 設計どおり) | D: `fallback_counts()` で件数は残る(既存)。**時間分離**の意図的トレードオフ |
| Provenance(○) | 台帳 event の `seq`/`source` が来歴 | — | — | — | — | Ledger に含む |

#### #24 仲介(Mediator)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Mediator × Ledger | 全ラッパ(22)が `record()` 1 点へ。**§4 実例の中核** | 5(失敗時 dict append 1 回 + lock) | 4(ring 256 + counts O(op 数)) | 5(シグネチャ不変) | 5 | — |
| Facade(利用者との仲介) | `on_error=` を決める外層 | 4 | 3 | 2 | 4 | G: #17 × Composite |
| Decorator / Proxy(○) | guard 自体が仲介の実体 | — | — | — | — | Mediator に含む |

#### #25 セルフサービス(Self-Service)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Registry の自己記述(param spec) | op が自分の引数型・範囲を申告し、Studio/fscript/docs が**自分で**ウィジェット・行・表を作る。既存: `studio._ARG_ROLES`(L1185、人間可読の文字列のみ、一部 op)。§4 候補 4 | 5 | 3 | 4 | 4 | M: 許容 |
| Probe(自己検査 `selfcheck()`) | ライブラリが自分の op を自分で検査 | 5(明示呼出し) | 4 | 5 | 5 | — |
| Null Object(○) | fallback が入力から自分で妥当値を導く(`fallback(v, out_sort)`) | — | — | — | — | #11 参照 |

#### #26 コピー(Copying)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Probe(Python 実装 = 安価なオラクル複製) | native/GPU を numpy の写しと比べる。既存 `fslib` L14「numpy implementation is the oracle」、`difftest.py`(ただし C 側は未実行 `FSCRIPT_DECISION §1.5`) | 5(CI) | 2(両実装の出力を保持) | 4 | 5 | M: #16 × 標本(全画素でなく構造データ数枚) |
| Provenance / Memento(golden vector) | 検証時の出力の写しを凍結し照合。既存 `fsruntime.GoldenVector` | 5 | 3 | 4 | 5 | — |
| Lazy(○ view = 複製の回避) | §3b Flyweight×view 参照 | — | — | — | — | — |

#### #27 使い捨て(Cheap Short-Living Objects)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Result(○ 呼出しごとの小オブジェクト) | `Attempt` を毎回作って捨てる。永続化しないので安い | 4 | 4 | 4 | 5 | — |
| 使い捨て context(`strict_mode()` with 文) | 既存 `backend_safe.strict_mode` | 5 | 5 | 5 | 4 | — |

#### #28 機械系の置換(Mechanics Substitution)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Strategy / Bridge(numpy → native/GPU) | 同じ契約で「動力源」を替える。既存 `fslib.op(name, backend)`、`accel_bridge.plan()` | 5(切替は plan 時) | 2(device 転送でコピー) | 4 | 3(GPU 失敗は `source="gpu"` で記録されるが**毎回再挑戦**) | M: #20 × 常駐(島単位で転送、既存 `plan`)/ D: #36 × Circuit Breaker(§4 候補 3) |

#### #29 流体(Pneumatics & Hydraulics)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Pipeline / generator(○ 「流す」の比喩) | フレームを流体のように流す。既存 `acquire.stream()` の `yield` | — | — | — | — | §3b Pipeline×generator を参照。原理としては #20 が本命 |

#### #30 柔らかい膜(Flexible Shells & Thin Films)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Decorator(薄い膜 = guard) | op 本体を変えず薄い膜で包む。既存 `guard`(w 関数 1 層) | 5 | 5 | 1 | 4 | G: #2 と同じ |
| Adapter(○ 膜としての変換層) | `oss_adapter` | #6 参照 | | | | |

#### #31 多孔質(Porous Materials)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Plugin / Hook(○ 拡張の穴) | 外部 op パックの登録点。既存は静的 import(`ops.py:969`) | 4 | 3 | 5 | 2(外部 op の失敗も同じ guard を通れば 4) | D: #24 × Mediator を登録点で強制(guard を通らない op を登録不可に) |

#### #32 色変化(Colour Change)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Provenance / Warning category(見えないものを色づけ) | fallback を `FullseyeFallbackWarning` という**専用カテゴリ**にする → `filterwarnings` で選別可。既存 | 5 | 5 | 5 | 4 | — |
| Ledger の `source` タグ(○) | op/gpu/import/input の 4 色 | Ledger に含む | | | | |

#### #33 同質性(Homogeneity)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Mediator(全 backend が同じ guard) | 21 個の私家版 `_safe` を `guard` へ委譲して同質化(済) | 5 | 4 | 5 | 5 | — |
| Result の同質型 | 全計測が `Attempt` を返す。既存 `metriccontract` | 4 | 4 | 4 | 5 | — |
| Strategy(同じ契約の backend 群) | `fslib` の「numpy = oracle」規約 | 5 | 3 | 4 | 3 | D: #26 × Probe |

#### #34 排除と再生(Discarding & Recovering)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Ledger の ring 排除 + counts 再生 | 事象は捨て、件数は残す。既存 `_EVENTS`/`_COUNTS` | 5 | 4 | 5 | 4 | — |
| Cache eviction / Object Pool | `lru_cache(64)` の LRU 排除。GPU バッファ再生は未 | 5 | 4 | 5 | 2 | D: #10 と同じ |

#### #35 パラメータ変化(Parameter Changes)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Policy(`on_error="fallback"\|"warn"\|"raise"`) | 構造を変えず**パラメータ**で挙動の相を変える。既存 `api.apply/run_pipeline(on_error=)` + `FULLSEYE_ON_ERROR` + `strict_mode()` | 5 | 5 | 5 | 4(呼出しごと選択) | — |
| Feature Flag(`set_system`) | 既存 `fssystem`(HALCON 流) | 5 | 5 | 5 | 3(設定の食い違いは沈黙) | D: `system_snapshot()` を Recipe の digest に含める(#26 × Provenance) |
| Strategy(○) | profile 切替は #15 | — | — | — | — | — |

#### #36 相変化(Phase Transitions)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| State / Circuit Breaker(closed → open → half-open) | GPU 経路の相転移。1 回目の失敗で記録+warn、以後は CPU 固定、明示リセットで再挑戦 | 5 | 4 | 5 | 4 | — |
| Builder の相(Recipe → ReadyRecipe) | 既存 `fsruntime`。「可変」→「凍結」の相転移 | 5 | 3 | 4 | 5 | — |
| Lazy(○ 未ロード → ロード済) | `torch_lazy` | #8 参照 | | | | |

#### #37 熱膨張(Thermal Expansion)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Backoff(○ 膨張する待ち) | 数値 op に再試行は無意味(#11)。通信のみ | — | — | — | — | 適用外 |
| 拡散→収縮(○) | 進化環境の「拡散(採掘)→収縮(進化)」(memory `project_fullseye_evolution_environment_2026_09_01`)は原理 #37 より #36 相変化 | — | — | — | — | — |

#### #38 強い酸化剤(Strong Oxidants)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Policy(strict = 反応を激しくして露見させる) | CI では `FULLSEYE_STRICT=1` で全 fallback を例外に | 5 | 5 | 5 | 5 | — |
| Probe(敵対検証・ファザー) | 既存 `out/.../adversarial/`、`tools/chain_fuzz.py` | 5 | 4 | 5 | 4 | — |

#### #39 不活性雰囲気(Inert Atmosphere)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Null Object(不活性な出力) | fallback 値は下流で「反応しない」(zeros / 0.0 / 空 contour) | 5 | 5 | 3 | 1 | D: #11 と同じ(**必ず Ledger と組**) |
| Bulkhead(○ 隔離) | 未使用 | — | — | — | — | — |

#### #40 複合材料(Composite Materials)

| パターン | なぜ | S | M | G | D | 短所のカバー |
|---|---|---|---|---|---|---|
| Decorator + Ledger + Policy + Warning(= `guard`) | 単独では D=1 の Null Object を、4 パターンの複合で D=5 に。**§4 実例そのもの** | 5 | 4 | 5 | 5 | — |
| Strategy + Probe(numpy oracle + native) | `fslib` の設計。複合の片方(native)を他方(numpy)で常時検証 | 5 | 2 | 4 | 5 | M: #16 × 標本 |

---

## §3b マトリクス 2: 設計パターン × コンテナ型

パターンを決めた後、「その責務をどのコンテナで持つか」が速度・メモリ・検出性を実際に決める(同じ Ledger でも list ring と deque(maxlen) では S が違う)。ここでは **fullseye で実在するコンテナ**を列にし、自然な組合せ(●)だけを採点する。

### 3b.1 コンテナ列の定義と fullseye での実在箇所(検証済)

| 記号 | コンテナ | fullseye 実在箇所 | 備考 |
|---|---|---|---|
| L | `list` | `ops.REGISTRY`(L921)/ `backend_safe._EVENTS`(ring: `del _EVENTS[:-256]`) | 順序あり・末尾 O(1)・先頭削除 O(n) |
| T | `tuple` | `ops.OPS`(L924 back-compat)/ `api.run_pipeline` の stage `(name,a,b)` | 不変・hashable |
| D | `dict` | `ops.RT`/`_BY_NAME`(L922-923、**後勝ち**)/ `fssystem.SYSTEM_PARAMS`(L68)/ `graphengine.nodes` / `fslib._REGISTRY[name][backend]` / `backend_safe._COUNTS` | 挿入順保持(3.7+) |
| S | `set`/`frozenset` | `backend_safe._WARNED`(warn once)/ `api._LABEL_READING_OPS`(L904)/ `ops._UNCLIPPED_SORTS`(L1058) | 所属判定 O(1) |
| Q | `collections.deque` | `segmentation.py:105`(flood fill BFS)/ `physarum_search.py:284` | 両端 O(1)・`maxlen` で ring |
| H | `heapq` | `mesh_decimate.py:262,283`(edge collapse 優先度、version stamp で stale 除外)/ `meshrepair.py:518` | 遅延削除が定石 |
| A | `array.array` | **未使用(0 件)** | ndarray が代替 |
| B | `bytes` | `comm.py:245`(Modbus frame)/ `dsp.py:62` `frombuffer` / `fslib.py:312` `Seq.__hash__` = `tobytes()` | 不変・境界越え |
| N | `ndarray`(密) | 全 op。`acoustics.py:329` `ascontiguousarray`。**`order="F"`/`asfortranarray` は 0 件**(全て C 順) | dtype/連続性が速度を決める |
| V | ndarray view / copy | `tomography.py:1657`・`imgforensics.py:1108` `sliding_window_view` / `evolve.py:23` genome `.copy()` / `fslib.Seq`(コピー + write-protect) | view = 0 コピーだが alias |
| R | 構造化/masked 配列 | `mathops.py:139,221,857` `np.ma.is_masked` / 構造化 dtype は**コア未使用** | mask = 値つき sentinel |
| P | `scipy.sparse` | `mesh_smooth.py:84`(COO→CSR Laplacian)/ `geodesic3d.py:20` csr / `colortransport.py` | 疎グラフ・疎行列 |
| M | `np.memmap` | `volio.py:430` `np.load(mmap_mode="r")` / `scale.py:147,162` `open_memmap`・`process_tiled_memmap` | working set > RAM |
| G | torch tensor(device) | `accel.py:42` `as_tensor(device=)` / `accel_bridge.plan/run` | 転送コストが支配 |
| C | `@dataclass` | `ops.Op`/`ops.Stage`/`fsruntime.Recipe`・`GoldenVector`/`metriccontract.Attempt`/`pyramid_gate.GateResult`(22 ファイル) | 自己記述・型ヒント |
| W | 台帳行(dict の list) | `backend_safe.record()` の `ev` dict / `ops.DROPPED_DUPLICATES` / `runtime_degeneracy.json` | 追記のみ |
| K | 木(nested dict / kd-tree) | `curvature3d.py:29` `cKDTree` / `fscript` AST(`Node` 群)/ **octree 未使用** | 空間索引・構文木 |
| E | グラフ(隣接 dict / CSR) | `graphengine.FullseyeGraph`(nodes dict + `topological_order`)/ `mesh_smooth` CSR 隣接 | DAG 実行・Laplacian |
| Z | `queue.Queue` / `threading.Lock` | `backend_safe._LEDGER_LOCK` / `video.py:246` / **`queue.Queue` 未使用** | スレッド境界 |
| I | generator / iterator | `acquire.py:269` `yield self.grab()` / `fslib.ObjectSet.__iter__`(L298) | 遅延・流し込み |
| U | `functools.lru_cache` | `annotate.py:276,296`(maxsize 64 / 8) | 鍵は hashable 必須 |

### 3b.2 適合マトリクス(パターン × コンテナ)

`●` 自然な組合せ(3b.3 で採点)/ `○` 可能だが本命でない / 空欄 = 使わない。

| パターン | L | T | D | S | Q | H | A | B | N | V | R | P | M | G | C | W | K | E | Z | I | U |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Registry / Strategy | ● | ○ | ● | ○ | | | | | | | | | | | ● | | | | | | |
| Decorator | | | | | | | | | | | | | | | | | | | | | ○ |
| Facade | | ○ | ● | ○ | | | | | ● | | | | | | | | | | | | |
| Mediator | | | ● | ● | | | | | | | | | | | | ● | | | ● | | |
| Observer | ● | | | ● | | | | | | | | | | | | | | | ○ | | |
| Chain of Responsibility | ● | ○ | | | ● | | | | | | | | | | | | | | | | |
| Template Method | | | | | | | | | | | | | | | ○ | | | | | | |
| Null Object | | | | | | | | | ● | | ○ | | | | | | | | | | |
| Command | ● | | | | ● | ● | | | | | | | | | ● | | | | | | |
| Memento | | ● | | | | | | ● | | ● | | | | | ● | | | | | | |
| Proxy / Lazy | | | | | | | | | | | | | ● | ○ | | | | | | ● | |
| Flyweight | | | ● | | | | | | | ● | | | | | | | | | | | ● |
| Visitor | | | ○ | | | | | | | | | | | | | | ● | ● | | | |
| Interpreter | | | ● | ○ | | | | | | | | | | | ● | | ● | | | | |
| Iterator | ● | | | | ● | | | | ○ | | | | | | | | | | | ● | |
| Builder | | ● | | | | | | | | | | | | | ● | | | | | | |
| Prototype | | | | | | | | | | ● | | | | | ○ | | | | | | |
| Adapter | | | | | | | | ● | ● | | | ● | | ● | | | | | | | |
| Bridge | | | ● | | | | | | | | | | | ● | | | | | | | |
| Composite | | | | | | | | | | | | | | | | | ● | ● | | | |
| State | | | ● | | | | | | | | | | | | ● | | | | | | |
| Singleton | | | ● | | | | | | | | | | | | | | | | ○ | | |
| Pipeline | ● | ● | | | | | | | ● | | | | ● | ● | | | | | | ● | |
| Plugin | | | ● | | | | | | | | | | | | | | | | | | |
| Result / Either | | ○ | | | | | | | | | ○ | | | | ● | | | | | | |
| Circuit Breaker | | | ● | | | | | | | | | | | | ○ | | | | | | |
| Bulkhead | | | | | | | | | | | | | | | | | | | ● | | |
| Retry / Backoff | | | | | ○ | | | | | | | | | | | | | | | | |
| Cache / Memoize | | | ● | | | | | | | | | | | | | | | | | | ● |
| Object Pool | ● | | | | ● | | | | | | | | | ● | | | | | | | |
| Ledger / Event Sourcing | ● | | ● | ● | ● | | | | | | | | | | | ● | | | ● | | |
| Saga | ● | | | | | | | | | | | | | | | | | | | | |
| Health Probe | | | | | | | | | ● | | | | | | | ● | | | | | |
| Policy / Feature Flag | | | ● | ● | | | | | | | | | | | | | | | | | |
| Sentinel / Tainted | | | | ● | | | | | | | ● | | | | | | | | | | |
| Provenance / Tagged | | | ● | | | | | | | | ● | | | | ● | ● | | | | | |

### 3b.3 採点(● セルのみ。列 = S/M/G/D + 古典的な落とし穴 + 短所のカバー)

| パターン × コンテナ | fullseye での形 | S | M | G | D | 落とし穴 | 短所のカバー(≤3 の軸) |
|---|---|---|---|---|---|---|---|
| Registry × D(dict) | `ops.RT[name]` | 5 | 3 | 3 | 3 | **後勝ち**で同名が黙って消える | D: Ledger × W — 既存 `DROPPED_DUPLICATES` + `tests/test_op_contracts.py` / G: Registry × C(param spec) |
| Registry × L(list) | `ops.REGISTRY` の登録順 | 4(線形探索は禁物) | 3 | 3 | 3 | 順序が「先勝ち/後勝ち」の意味を持ち、import 順で挙動が変わる | S/D: 常に D を索引にし、L は列挙専用に(既存 `_BY_NAME`) |
| Registry × C(dataclass) | `Op(name, category, halcon, in_sort, out_sort, fn, c_stmt)` | 5 | 3 | 4(`params` フィールドを足せば型つき kwargs) | 4(型ヒントで静的検査可) | フィールド追加で 861 op の生成側を全部触る | M: 許容 / #3 局所的性質 × 既定値(`params=()`)で段階導入 |
| Facade × D | HALCON alias → op 名 の dict(`api.py:875`) | 4 | 3 | 2 | 3 | alias 衝突を先勝ちで隠す(LEDGER「曖昧解決 2 件」) | D: Ledger × W — 既存 `api.ambiguous_aliases`(`__init__.py:312` で公開)/ G: #17 × Composite |
| Facade × N(ndarray) | `apply(image: ndarray)` | 5 | 5 | 1 | 4(`_check_input_sort` が ndim/dtype を見て `source="input"` 記録) | 1-D を 2-D op に渡しても以前は通った(LEDGER #3) | G: Composite × E(多入力は graph へ)|
| Mediator × D | `_COUNTS[name] += 1` | 5 | 3(O(op 数)) | 5 | 5 | なし(件数は消えない) | M: 許容 |
| Mediator × S(set) | `_WARNED`(warn once) | 5 | 3 | 5 | 3(2 回目以降は沈黙 = 意図) | `clear_fallbacks(reset_warnings=True)` を忘れると再警告しない | D: Ledger × D(件数)で補完(既存) |
| Mediator × W(台帳行) | `record()` の `ev = {name, source, out_sort, error, seq}` | 5 | 4 | 5 | 5 | 行が dict なのでスキーマ drift が沈黙 | (D は 5 だが)将来 Result × C(dataclass 化)で型を固める |
| Mediator × Z(Lock) | `_LEDGER_LOCK` | 3(失敗時のみ lock、成功経路はゼロ) | 5 | 5 | 5 | GIL 下でも `del _EVENTS[:-N]` と append の競合はあり得るので必要 | S: 失敗時のみなので実質 5。**成功経路に lock を置かない**(#21 高速化) |
| Observer × L | 購読者 list(Qt signal 内部) | 4 | 3 | 5 | 3(購読漏れは沈黙) | 例外を投げる購読者が他を止める | D: Decorator × try で購読者ごとに隔離(#39 不活性) |
| Observer × S | `_WARNED` = 「一度通知した」集合 | 5 | 3 | 5 | 3 | 上と同じ | 上と同じ |
| Chain × L | 処理者 list を順に(alias 解決) | 4 | 3 | 3 | 2(どの処理者が採ったか残らない) | 順序依存 | D: Provenance × W(採用した処理者名を記録) |
| Chain × Q(deque) | BFS(`segmentation.py:105`) | 5(両端 O(1)) | 2(フロンティア O(N) 最悪) | 3 | 4(終了しない = 明白) | list.pop(0) を使うと O(N²) | M: #16 × 部分(タイル、`scale.process_tiled`) |
| Null Object × N | `fallback` の `zeros`/`clip(v)` | 5 | 2(image sort は clip で O(N) 複製) | 3 | **1** | 恒等と区別不能 | D: Mediator × W(**既存 `guard` が必ず `record`**)/ M: `np.clip(v, 0, 1, out=...)` は入力を壊すので不可 — 許容 |
| Command × L / Q / H | undo スタック(未使用)/ 優先度キュー(`mesh_decimate`) | 5 / 5 / 4(log n) | 3 / 4(maxlen) / 3 | 5 | 3 | heapq は stale entry(既存は version stamp `int(vver[i])` で遅延削除 = 正解) | D: Command × C(コマンドに `applied: bool` を持たせる) |
| Memento × T / B / V / C | `GoldenVector`(C)/ `Seq.__hash__` の `tobytes()`(B)/ genome `.copy()`(V) | 5 / 4(O(N) hash) / 4(O(N) copy) / 5 | 5 / 4 / 2 / 3 | 4 | 5 | view を snapshot と誤認して後で書き換わる | M(V): `fslib.Seq` 方式 = コピー + `setflags(write=False)`(既存 L240) |
| Proxy/Lazy × M(memmap) | `volio.np.load(mmap_mode="r")`、`scale.process_tiled_memmap` | 4(ページフォルト) | 5 | 3 | 3(OS が握るので I/O エラーが遅れて出る) | 書込み memmap の flush 忘れ | D: Probe × W(タイル完了を台帳に)/ G: Pipeline × M 参照 |
| Proxy/Lazy × I(generator) | `acquire.stream()` | 5 | 5 | 4 | 2(途中で切れても呼び手は「終わった」と思う) | 1 回しか回せない | D: Result × C(終端理由を返す)+ `limit` 到達を明示 |
| Flyweight × D / V / U | 共有 kernel dict / view / `lru_cache(64)` | 5 | 4 | 5 | 2(共有物の変更が全員に波及) | view が alias、cache の鍵に version 無し | D: Sentinel × V(`setflags(write=False)`)+ Provenance × D(鍵に fingerprint) |
| Visitor × K / E | AST / graph の走査 | 4 | 5 | 5 | 4 | ノード型追加で Visitor 全部を直す | (fullseye 未使用。fscript は isinstance 分岐。§4 候補 7) |
| Interpreter × D / C / K | `fscript.Env`(D)・`Node` dataclass(C)・AST(K) | 4 | 3 | 4 | 4(`FScriptError` に行番号) | builtins が dict でなく if 連鎖だと分岐が増える | 既存で 4 以上。memory `feedback_nested_conditionals_use_a_table` |
| Iterator × L / Q / I | ObjectSet / BFS / stream | 5 | 5 | 4 | 3 | 反復中の変更 | D: Memento × T(反復前に tuple 化) |
| Builder × T / C | `Recipe` → `ReadyRecipe`(frozen dataclass) | 5 | 3 | 4 | 5 | 「Ready」なのに可変フィールドを持つ | 既存 `FsNotReady` で fail-closed |
| Prototype × V | genome `.copy()` | 4 | 2 | 3 | 4 | `copy()` 忘れで親子が alias | M: 許容(genome は小)/ 画像は #26 × view |
| Adapter × B / N / P / G | Modbus bytes / dtype 変換 / COO→CSR / `as_tensor` | 4 / 3(dtype 複製) / 3 / 1(転送) | 5 / 2 / 3 / 1 | 3 | 2(変換の丸めが沈黙) | S/M(G): #20 × Object Pool × G(常駐)/ D: Probe × N(`parity.py` の cross-backend 比較) |
| Bridge × D / G | `fslib._REGISTRY[name][backend]` / CPU-GPU 島 `accel_bridge.plan` | 5 | 3 | 4 | 3 | backend 間の意味論差 | D: #26 × Probe(numpy oracle)、既存 `difftest`/`parity` |
| Composite × K / E | `FullseyeGraph`(隣接 dict + topo sort) | 4 | 3 | 5 | 3(`validate()` は構造のみ) | 循環・未定義入力 | D: Ledger × W(ノード ID で `current_op`) |
| State × D / C | `_STRICT` / `FullseyeRuntime` | 5 | 5 | 5 | 4 | グローバル状態のテスト間漏れ | (既存 `strict_mode()` context で復元) |
| Singleton × D | `SYSTEM_PARAMS` / モジュール状態 | 5 | 5 | 5 | 3(設定の食い違いが沈黙) | テスト分離 | D: Memento × C(`system_snapshot()` を digest に) |
| Pipeline × L / T | stage 列 `[(name,a,b)]` | 5 | 3 | 3 | 3 | 段の失敗が次段入力に化ける | D: Mediator × W(既存 `current_op` 帰属)/ G: Composite × E |
| Pipeline × N | 段ごとの中間 ndarray | 5 | 2(段数 × O(N)) | 3 | 3 | 中間配列の dtype 昇格(float64 化)で 8 倍 | M: #34 × Object Pool × L(バッファ再利用、`out=`)/ #1 × M(タイル memmap、既存 `scale.py`) |
| Pipeline × M(memmap tiles) | `scale.process_tiled_memmap(tile=1024, halo=16)` | 3(halo 重複) | 5 | 3 | 3(タイル境界の継ぎ目誤差) | halo 不足 | S: 許容(RAM 超え専用)/ D: 既存 `scale.tiling_error`(L89)で継ぎ目を実測 |
| Pipeline × G(torch) | `accel_bridge.run(stages, device)` | 2(転送)〜5(島内) | 1(CPU/GPU 二重) | 3 | 4(`source="gpu"` 記録) | 転送律速(`api.apply` docstring「単発 op は転送律速」) | S/M: #20 有用作用継続 × 島分割(既存 `plan`)+ Object Pool × G |
| Pipeline × I(generator) | フレーム流に op を map | 5 | 5 | 4 | 2 | 途中終了が沈黙 | D: Proxy × I と同じ |
| Plugin × D | 外部 op パックの登録 dict | 4 | 3 | 5 | 2 | guard を通らない op が混入 | D: Mediator を登録関数で強制(登録時に `guard` で包む) |
| Result × C | `Attempt(ok, value, reason, metric)` | 4 | 4 | 4 | 5 | `if att.value:` で 0.0 を偽と誤認 | 既存 `__bool__` = ok(設計で回避) |
| Circuit Breaker × D | `{op_name: state}`(未使用) | 5 | 4 | 5 | 4 | half-open の再挑戦条件が無いと永久 open | Policy × S(明示 reset API) |
| Bulkhead × Z | per-op timeout / worker 区画(未使用) | 3 | 4 | 5 | 3 | Windows で signal ベースの timeout は使えない | S/D: 進化ループの外側(`robust.py`)で計時、hot path に置かない |
| Cache × D / U | kernel dict / `lru_cache(64)` | 5 | 4 | 5 | 2 | 鍵に version が無い | D: Provenance × D(鍵に fingerprint) |
| Object Pool × L / Q / G | バッファ再利用(未使用) | 5 | 4 | 3 | 2(古い内容が残る) | 「空」のつもりで前回の値 | D: Sentinel × N(`fill(nan)` して返却)|
| Ledger × L(ring) | `_EVENTS` + `del _EVENTS[:-256]` | 4(溢れるたび O(256)) | 4 | 5 | 4 | 古い事象が消える | S: **Ledger × Q(`deque(maxlen=256)`)に替えると append O(1)**(1 行変更・挙動同値) |
| Ledger × Q(deque maxlen) | 推奨形 | 5 | 4 | 5 | 4 | `events_since` は線形走査(256 件なので無視可) | — |
| Ledger × D(counts) | `_COUNTS` | 5 | 3 | 5 | 5 | なし | — |
| Ledger × S(warned) | `_WARNED` | 5 | 3 | 5 | 3 | 上述 | 上述 |
| Ledger × W | 行 = dict | 5 | 4 | 5 | 5 | スキーマ drift | Result × C |
| Ledger × Z | lock | (Mediator × Z と同じ) | | | | | |
| Saga × L | 補償手続き list(未使用) | 4 | 3 | 5 | 3 | 補償自体の失敗 | (fullseye では対象外) |
| Health Probe × N / W | 構造データ ndarray を全 op に流し、結果行を `runtime_degeneracy.json` | 5(CI) | 4 | 5 | 5 | 乱数データは構造欠陥を隠す | 既存: memory `feedback_random_test_data_hides_structural_defects` |
| Policy × D / S | `SYSTEM_PARAMS` / `_ON_ERROR_CHOICES` tuple + 検証 | 5 | 5 | 5 | 4(不正値は `ValueError`) | 文字列 typo | 既存 `_policy()` が検証(fail-closed) |
| Sentinel × S / R | `_LABEL_READING_OPS`(frozenset)/ masked array | 5 / 3(mask 伝播 O(N)) | 5 / 2 | 3 | 4 / 4 | masked が numpy 関数で剥がれる(`np.asarray` で mask 消失) | R: Provenance × W(side channel)に逃がす。R は `mathops` 内に閉じる(既存) |
| Provenance × D / R / C / W | trace dict / masked / dataclass / 台帳行 | 5 / 3 / 4 / 5 | 4 / 2 / 4 / 4 | 3 / 3 / 4 / 5 | 5 | ndarray subclass は演算で剥がれる | G: **空間分離** — 値と来歴を別コンテナに(`run_pipeline` の trace dict)|

---

## §3c マトリクス 3: TRIZ 40 原理 × コンテナ型

パターンを経由せず「原理 → コンテナ」を直接引く表。**コンテナが先に決まっている状況**(ndarray を返す契約は動かせない、GPU tensor しか触れない、等)で使う。列は §3b.1 と同じ記号。

### 3c.1 適合マトリクス(40 × 21)

| # | 原理 | L | T | D | S | Q | H | A | B | N | V | R | P | M | G | C | W | K | E | Z | I | U |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 分割 | ○ | | | | | | | | ● | | | ● | ● | | | | | | | | |
| 2 | 引き出し | | | | ○ | | | | | | | ● | ● | | | | | | | | | |
| 3 | 局所的性質 | | | ● | | | | | | | | ● | | | | ● | | | | | | |
| 4 | 非対称化 | | | | | | ● | | | | | | | | | ● | | | | | | |
| 5 | 統合 | | | | | | | | | ● | | | | | | | | | ● | | | |
| 6 | 多用途化 | | | ● | | | | | | | | | | | | | | | | | | |
| 7 | 入れ子 | | | ○ | | | | | | | | | | | | | | ● | ● | | | |
| 8 | 釣り合い | | | | | | | | | | | | | ● | | | | | | | ○ | |
| 9 | 先取り反作用 | | | | ● | | | | | | | | | | | | | | | | | |
| 10 | 先取り作用 | | | | | | | | | | | | | | | ● | | | | | | ● |
| 11 | 緩衝 | | | | | ● | | | | ● | | | | | | | | | | | | |
| 12 | 等ポテンシャル | | ● | | | | | | | ● | | | | | | | | | | | | |
| 13 | 逆転 | | | | | | | | | | | | ● | | | | | | | | ● | |
| 14 | 球面化 | | | | | ● | | | | | | | | | | | | | | | | ○ |
| 15 | 動性化 | | | ● | | | | | | | | | | | ● | | | | | | | |
| 16 | 部分的に | | | | | | | | | | ● | | | | | | | | | | ● | |
| 17 | 多次元化 | | | | | | | | | ● | | | | | | | | | ● | | | |
| 18 | 振動 | | | | | | | | | | | | | | | | | | | ○ | | |
| 19 | 周期化 | | | | | ● | ● | | | | | | | | | | | | | | | |
| 20 | 有用作用継続 | | | | | | | | | | | | | | ● | | | | | | ● | |
| 21 | 高速化 | | | | | | | | | ● | ● | | | | | | | | | | | |
| 22 | 災い転じて福 | | | | | | | | | | | | | | | | ● | | | | | |
| 23 | フィードバック | | | ● | | | | | | | | | | | | | ● | | | | | |
| 24 | 仲介 | | | | | | | | | | | | | | | ● | | | | ● | | |
| 25 | セルフサービス | | | | | | | | | | | | | | | ● | | | | | | |
| 26 | コピー | | | | | | | | ○ | | ● | | | | | ● | | | | | | |
| 27 | 使い捨て | | ● | | | | | | | | | | | | | ○ | | | | | | |
| 28 | 機械系の置換 | | | | | | | | | | | | ● | | ● | | | | | | | |
| 29 | 流体 | | | | | | | | | | | | | | | | | | | | ● | |
| 30 | 柔らかい膜 | | | | | | | | | | | ● | | | | | | | | | | |
| 31 | 多孔質 | | | | ○ | | | | | | | | ● | | | | | | | | | |
| 32 | 色変化 | | | | | | | | | | | ● | | | | ● | | | | | | |
| 33 | 同質性 | | | | | | | | | ● | | | | | | | | | | | | |
| 34 | 排除と再生 | | | | | ● | | | | | | | | | | | | | | | | ● |
| 35 | パラメータ変化 | | | | | | | | | ● | | | | | | | | | | | | |
| 36 | 相変化 | | | | | | | | | | | | ● | ● | | | | | | | | |
| 37 | 熱膨張 | ● | | | | | | | | | | | | | | | | | | | | |
| 38 | 強い酸化剤 | | | | ● | | | | | | | | | | | | | | | | | |
| 39 | 不活性雰囲気 | | ● | | | | | | | | ● | | | | | | | | | | | |
| 40 | 複合材料 | | | ● | | | | | | | | ● | | | | | | | | | | |

### 3c.2 採点(● セル。列 = 原理 × コンテナ | fullseye での形 | S/M/G/D | 落とし穴 | 短所のカバー)

| 原理 × コンテナ | fullseye での形 | S | M | G | D | 落とし穴 | 短所のカバー(≤3 の軸) |
|---|---|---|---|---|---|---|---|
| #1 分割 × N(タイル分割) | `scale.process_tiled(tile=1024, halo=16)` | 3(halo 重複 ~3%) | 5(タイル分だけ) | 3 | 3(継ぎ目) | halo 不足で境界アーティファクト | S: 許容 / D: 既存 `scale.tiling_error` で継ぎ目を数値化(#23 × W) |
| #1 × P(疎ブロック) | Laplacian を CSR で(`mesh_smooth.py:84`) | 5(nnz 比例) | 5 | 3 | 4(shape 不一致は例外) | COO のまま演算すると遅い | (#36 × P 参照: COO→CSR 相転移) |
| #1 × M(memmap タイル) | `scale.process_tiled_memmap` | 3 | 5 | 3 | 3 | flush 忘れ | D: #23 × W(タイル完了台帳)|
| #2 引き出し × R(mask で邪魔な要素を除外) | `np.ma`(`mathops`) | 3(mask 伝播) | 2(mask 配列 O(N)) | 3 | 4 | `np.asarray` で mask が消える | S/M: mask を bool ndarray として別持ち(#17 × N)/ D: 4 |
| #2 × P(非零だけ取り出す) | 疎行列化 | 5 | 5 | 3 | 4 | 密→疎の閾値 | — |
| #3 局所的性質 × D(op ごとの表) | `_LABEL_READING_OPS`、`fslib.PROFILES` | 5 | 3 | 4 | 4 | 表と実装の二重管理 | M: 許容 / memory `feedback_nested_conditionals_use_a_table`(表どうしの整合をテストで突き合わせる) |
| #3 × R(構造化 dtype = フィールドごとに型) | **未使用**。点群 (N,3)+属性を構造化配列で持つ案 | 4 | 5 | 4 | 3(フィールド名 typo は KeyError = 明白だが、dtype 順序依存が沈黙) | 演算のたびに view が必要 | D/G: #40 × R 参照(dataclass に ndarray を束ねる方が fullseye 流) |
| #3 × C(dataclass に局所の性質) | `Op.in_sort/out_sort`、将来 `params` | 5 | 3 | 4 | 4 | — | — |
| #4 非対称化 × H(優先度で非対称に処理) | `mesh_decimate` の edge collapse | 4 | 3 | 3 | 4 | stale entry | 既存 version stamp |
| #4 × C(ok/value/reason の非対称) | `Attempt` | 4 | 4 | 4 | 5 | — | — |
| #5 統合 × N(`stack`/`concatenate`) | 多チャネル化(`backend_safe.fallback` の `np.stack([vv]*3,-1)`) | 2(O(N) 複製) | 2 | 3 | 3 | 軸の取り違え(HWC vs CHW) | S/M: #26 × V(`broadcast_to` の view)/ D: shape assert |
| #5 × E(グラフ統合) | `FullseyeGraph.add(inputs=[...])` | 4 | 3 | 5 | 3 | — | D: #23 × W |
| #6 多用途化 × D(何でも入る dict) | `graphengine.nodes[id] = {op, inputs, a, b}` | 5 | 3 | 5 | 2(キー typo が沈黙) | スキーマ無し | D: #25 × C(dataclass 化で属性エラー = 明白) |
| #7 入れ子 × K / E | AST / サブグラフ | 4 | 3 | 5 | 3 | 深さの再帰限界 | D: #23 × W(階層 ID)|
| #8 釣り合い × M(RAM を disk で釣り合わせる) | `volio` mmap | 4 | 5 | 3 | 3 | 遅延 I/O エラー | D: #9 × S(事前に存在・サイズ検査)|
| #9 先取り反作用 × S(許可集合で先に弾く) | `_ON_ERROR_CHOICES`、`_NDIM_OK` | 5 | 5 | 5 | 5 | 集合の更新漏れ | (テストで表と実装を突き合わせる) |
| #10 先取り作用 × C(事前コンパイル) | `ReadyRecipe` | 5 | 3 | 4 | 5 | — | — |
| #10 × U(事前計算 cache) | `lru_cache` | 5 | 4 | 5 | 2 | 鍵に version 無し | D: #26 × D(fingerprint 鍵) |
| #11 緩衝 × Q(`deque(maxlen)` = 溢れても壊れない) | Ledger ring の推奨形 | 5 | 4 | 5 | 4 | 古い事象消失 | D: `_COUNTS`(既存)|
| #11 × N(sort 妥当な zeros) | `fallback` | 5 | 2 | 3 | 1 | 恒等と区別不能 | D: #24 × W(**必須**、既存 `guard`) / M: 許容 |
| #12 等ポテンシャル × T(一様 stage tuple) | `(name, a, b)` | 5 | 5 | 1 | 3 | 位置引数の意味が op ごとに違う(`a` = sigma か閾値か) | G: #3 × C(param spec)/ D: 同左(範囲検査) |
| #12 × N(全 op が float64 [0,1] ndarray) | `ops` の clip 規約(`_UNCLIPPED_SORTS` 例外) | 5 | 3(float64 固定 = uint8 の 8 倍) | 1 | 3(clip が符号情報を捨てる: `signed01` の注記) | 符号つき応答の半分が消える | M: #35 × N(dtype を op 契約に)/ D: 既存 `backend_safe.signed01` |
| #13 逆転 × P(COO ↔ CSR / 転置表現) | 行索引 ↔ 列索引 | 5 | 5 | 3 | 4 | 変換コスト | — |
| #13 × I(push → pull) | `acquire.stream()` の generator(呼び手が引く) | 5 | 5 | 4 | 2 | 途中終了が沈黙 | D: #32 × C(終端理由)|
| #14 球面化 × Q(環状バッファ) | ring | 5 | 4 | 5 | 4 | 上述 | 上述 |
| #15 動性化 × D(実行時に表を差替え) | `set_system`、`PROFILES` | 5 | 3 | 5 | 3 | グローバル状態 | D: #26 × C(`system_snapshot()`)|
| #15 × G(device 間を動的に移動) | `accel_bridge.plan` | 2(転送) | 1 | 3 | 4(`source="gpu"`) | 転送律速 | S/M: #20 × G(常駐・島)|
| #16 部分的に × V(sliding window view = 部分だけ見る) | `sliding_window_view`(`tomography`, `imgforensics`) | 5(0 コピー) | 5 | 3 | 3(view に書くと元が壊れる) | 巨大な仮想 shape を `copy()` すると爆発 | D/M: `setflags(write=False)` + **決して `.copy()` しない**規約 |
| #16 × I(必要な分だけ生成) | generator | 5 | 5 | 4 | 2 | 上述 | 上述 |
| #17 多次元化 × N(軸を足す: batch 次元) | `accel._to_batch` の (B,1,H,W) | 5 | 3 | 4 | 3 | 軸順の規約違い | D: shape 契約テスト(既存 `tests/test_chain_type_contracts.py`)|
| #17 × E(鎖 → DAG) | `FullseyeGraph` | 4 | 3 | 5 | 3 | — | D: #23 × W |
| #19 周期化 × Q / H(周期スケジュール) | 周期 probe / 優先度付き再検査(未使用) | 5 | 4 | 5 | 4 | — | — |
| #20 有用作用継続 × G(GPU 常駐) | 島単位で転送(`plan`) | 5(島内) | 1(二重保持) | 3 | 4 | メモリ二重 | M: #34 × Object Pool × G(バッファ再利用、RTX5090 ゲート後)|
| #20 × I(途切れないフレーム流) | `acquire.stream()` | 5 | 5 | 4 | 2 | 上述 | 上述 |
| #21 高速化 × N(ベクトル化 = Python ループを飛ばす) | 全 op の基本 | 5 | 2(一時配列) | 3 | 3 | 一時配列の連鎖で O(N) × 式の項数 | M: `out=` 引数・`np.multiply(a,b,out=a)`(#34 × N 再利用)|
| #21 × V(view で複製を飛ばす) | `sliding_window_view`、`[::2]` | 5 | 5 | 3 | 3 | alias | D: `write=False` |
| #22 災い転じて福 × W(失敗行 = 監査資産) | `fallbacks()` → dead-op 一覧 | 5 | 4 | 5 | 5 | — | — |
| #23 フィードバック × D / W(件数・事象を CI へ戻す) | `fallback_counts()` / `events_since(mark())` | 5 | 3〜4 | 5 | 5 | — | — |
| #24 仲介 × C(値と失敗を運ぶ型) | `Attempt` | 4 | 4 | 4 | 5 | — | — |
| #24 × Z(スレッド境界の仲介) | `_LEDGER_LOCK`(失敗時のみ) | 3→5 | 5 | 5 | 5 | 成功経路に lock を置くと 3 | S: 失敗時のみに限定(既存)|
| #25 セルフサービス × C(自己記述) | `Op` に `params` を足すと Studio/fscript/docs が自動生成 | 5 | 3 | 4 | 4 | 生成側 861 op | M: 許容 / 段階導入(既定値) |
| #26 コピー × V(view = 安価な写し) | genome/画像 | 5 | 5 | 3 | 3 | alias | D: `write=False` |
| #26 × C(golden の写し) | `GoldenVector` | 5 | 3 | 4 | 5 | — | — |
| #27 使い捨て × T(不変の一時 tuple) | stage tuple、`Attempt` 相当 | 5 | 5 | 3 | 3 | — | G: #12 と同じ |
| #28 機械系の置換 × P(密→疎) | Laplacian / OT の疎化 | 5 | 5 | 3 | 4 | 密度閾値 | — |
| #28 × G(CPU→GPU) | `accel` | 2〜5 | 1 | 3 | 4 | 転送 | #20 参照 |
| #29 流体 × I(流す) | generator pipeline | 5 | 5 | 4 | 2 | 上述 | 上述 |
| #30 柔らかい膜 × R(mask = 柔らかい境界) | masked | 3 | 2 | 3 | 4 | mask 消失 | S/M: #2 × R と同じ |
| #31 多孔質 × P(空隙 = 疎) | 疎行列 | 5 | 5 | 3 | 4 | — | — |
| #32 色変化 × R(mask で「疑わしい画素」に色をつける) | masked array を tainted として | 3 | 2 | 3 | 4 | 剥がれる | G: #17 × W(side channel)|
| #32 × C(`ok` フラグ) | `Attempt.ok`、`GateResult` | 4 | 4 | 4 | 5 | — | — |
| #33 同質性 × N(全 op が同 dtype) | float64 規約 | 5 | 3 | 1 | 3 | 上述 #12 × N | 同左 |
| #34 排除と再生 × Q / U(古い順に捨てて再利用) | `deque(maxlen)` / LRU | 5 | 4 | 5 | 3〜4 | 消えたものが必要だった | D: `_COUNTS`(件数は不滅)|
| #35 パラメータ変化 × N(dtype/連続性を変える) | `ascontiguousarray(float64)`(`acoustics.py:329`)、uint8 化(`_u8`) | 3(変換 O(N)) | 2 | 3 | 2(丸め・オーバーフローが沈黙) | uint8 で [0,1] を 255 倍する際の飽和 | D: #9 × S(dtype 許可集合、既存 `dtype.kind in "biufc"`)+ `parity` |
| #36 相変化 × P(COO → CSR) | `coo_matrix(...).tocsr()`(`mesh_smooth.py:84`) | 5 | 3(変換中は二重) | 3 | 4 | CSR に要素追加不可 | — |
| #36 × M(disk ↔ RAM) | memmap ↔ ndarray | 4 | 5 | 3 | 3 | 上述 | 上述 |
| #37 熱膨張 × L(償却成長) | list append の倍々成長 | 5(償却 O(1)) | 3(最大 2 倍の余白) | 5 | 4 | 上限なし成長 | M: #11 × Q(maxlen)|
| #38 強い酸化剤 × S(厳格な許可集合で反応を激化) | `FULLSEYE_ON_ERROR=raise` + 許可 dtype/ndim | 5 | 5 | 5 | 5 | 厳格すぎて正当入力を弾く | (既存 `_NDIM_OK` は「明らかに違う」だけ弾く軽い検査 = 意図的) |
| #39 不活性雰囲気 × T / V(不変 = 反応しない) | tuple stage / `write=False` 配列(`fslib.Seq`) | 5 | 5 | 3 | 4 | 不変を破る `np.asarray` 経路 | G: 許容(不変性は sort の契約) |
| #40 複合材料 × D / R(異種を束ねる) | `{"shape":..., "cs": [...]}` contour dict(`fallback`)、構造化配列(未使用) | 5 | 4 | 4 | 2(dict スキーマが沈黙) | — | D: #25 × C(dataclass 化) |

---

## §4 fullseye への適用

### 4.1 実例(解決済): fail-soft の矛盾 — 2026-09-02 に `backend_safe.py` / `api.py` で実装

**矛盾**(39 特性): 改善したい = **信頼性 #27・操作容易性 #33**(facade は利用者のパイプラインを落とさない)/ 悪化する = **測定精度 #28・制御の困難さ #37**(壊れた op が「働く恒等」と区別できない)。2026-09-02 の監査で確定バグ 7 件中 6 件が「例外なし・答えが違う」型(`LEDGER.md`)。原因は 3 層の fail-soft: facade `api.apply` / GPU 分岐 `except Exception` / 22 ファイルの私家版 `_safe`(記録するのは `backends.py` の 1 つだけ)。

**物理的矛盾**: 「握りつぶすべき」かつ「握りつぶすべきでない」。**側を選ばず分離で解く**:

| 分離 | TRIZ 原理 | パターン | 実装(検証済) |
|---|---|---|---|
| 空間(内層は記録・外層が決める) | **#24 仲介** | Mediator × Ledger | `backend_safe.record()`(L113)= 全ラッパが報告する 1 点。`backends._safe`(L64-69)と **21 の `backends_*._safe` すべて**が `backend_safe.guard` に委譲(`grep -l "_bs.guard\|backend_safe.guard\|import backend_safe" backends_*.py` = 21) |
| 分類 | **#1 分割** | Result / taxonomy | `record(source="op"\|"gpu"\|"import"\|"input")`。GPU: `api.py:1095,1104,1230` / import: `ops.py:979` / 入力 sort: `api._check_input_sort` + `_guard_input`(L1036-1058、`_NDIM_OK` で ndim/dtype の軽い検査) |
| 条件(呼び手が選ぶ) | **#35 パラメータ変化** | Policy | `api.apply(..., on_error="fallback"\|"warn"\|"raise")`(L1109)/ `run_pipeline`(L1184)/ 既定は env `FULLSEYE_ON_ERROR`。`_policy()` が不正値を `ValueError` で拒否(fail-closed)。`"raise"` は `strict_mode(True)` の with で内層を strict に切替(`_run_guarded` L1062) |
| 時間(1 回だけ見せる) | **#11 緩衝 + #32 色変化** | Observer × set | `FullseyeFallbackWarning`(専用カテゴリ = 色)を op 名ごとに 1 回(`_WARNED` set)。`FULLSEYE_QUIET_FALLBACK` で沈黙可 |
| フィードバック | **#23** | Ledger → CI | `fullseye.fallbacks()` / `fallback_counts()` / `mark()`+`events_since()`(facade `__init__.py:30,311` で公開)。CI は構造データ probe 後に `assert fallbacks() == []` |
| 害を益に | **#22** | Ledger = 監査 | 8 Agent を回した dead-op 監査が `fallback_counts()` 1 回に。`tests/test_backend_safe.py` が回帰 |

**4 軸(実測根拠つき)**: S **5**(成功経路は try のみ。lock/dict append は失敗時だけ。`_run_guarded` の `mark()`/`current_op` は呼出しごとに lock 1 回 + thread-local 代入 = 数百 ns、4 MP op の ms 級に対し無視可 — ただし厳密には 4.5)/ M **4**(ring 256 + counts O(op 数) + warned set)/ G **5**(`apply` のシグネチャは kwargs 追加のみ、既存呼出しは無変更)/ D **5**(記録 + 分類 + warn once + 呼出しごと policy + CI assert)。

**残っている弱点(正直に)**: (1) GPU 経路は記録されるが**毎回**再挑戦する(Circuit Breaker 無し → 候補 5)。(2) `_check_input_sort` は ndim/dtype の粗い検査で、sort 跨ぎ恒等(`tb_quaternion_to_rgb` 型)は捕まえない → 候補 1・6。(3) `_EVENTS` は list ring で溢れるたび O(256)(§3b Ledger × L)→ `deque(maxlen=256)` に替えるだけで S=5(挙動同値)。

### 4.2 次の候補 — マトリクスから選んだ「より理想的な構造」(順位つき)

順位 = (D の上がり幅 × 影響 op 数)÷ 実装難度。各行: 4 軸 / 矛盾(39 特性)/ 分離原理 / 難度。

| 順位 | 候補 | 原理 × パターン × コンテナ | S/M/G/D | 矛盾(改善 vs 悪化) | 分離 | 難度 | 根拠・既存資産 |
|---|---|---|---|---|---|---|---|
| **1** | **`fullseye.selfcheck()` + CI 常設 probe**: 構造データ 1 組を全 op に流し、(a) fallback 件数 (b) **sort 跨ぎ恒等**(入力≡出力)(c) 定数出力 を台帳行で返す。CI は「呼べた/毎回拒否/引数組めない」を分けて数える | #9 先取り反作用 + #22 × Health Probe × N/W | 5/4/5/**5** | 信頼性 #27 vs 時間の損失 #25 | **時間**(import 時でなく CI・明示呼出し) | ★☆☆ | `out/.../probe_runtime_degeneracy.py` と `triage_degenerate.py` が土台。`tests/test_backends_typed_liveness.py` は同 sort 恒等のみ(盲点) |
| **2** | **facade の多入力(nary)**: `apply((img1, img2), "add_image")` を Composite 入力で受け、`list_ops` に `arity` を出す。arity 不一致は `ArityError`(taxonomy に `source="input"`) | #17 多次元化 + #5 統合 × Composite × T/E | 5/5/**5**/4 | 適応性 #35 vs 操作容易性 #33 | 空間(単入力 facade の裏に graph 経路) | ★☆☆ | `graphengine._eval(RT, nary, ...)` が既に nary を扱う。LEDGER #4(17 op が KeyError) |
| **3** | **GPU 経路の Circuit Breaker**: op ごとに `{closed, open}`。初回失敗で記録+warn once、以後は CPU 直行(再挑戦コストゼロ)。`fullseye.reset_gpu()` で half-open。`device="cuda!"`(strict device)は raise | #36 相変化 + #11 緩衝 × Circuit Breaker × D | 5/4/5/4 | 速度 #9 vs 信頼性 #27 | 条件(strict device)+ 時間(open 後) | ★☆☆ | `api.py:1095,1104` に record 済。CI は CUDA 不在で GPU 実効カバレッジ 0%(`test_false_confidence.md`)— RTX5090 ゲートで実測 |
| **4** | **op param spec メタデータ**: `Op` に `params: tuple[ParamSpec]`(name/type/range/choices/default)。Studio の型適合ウィジェット・fscript 行生成・docs 表・範囲検査が**自動生成**される | #25 セルフサービス + #3 局所的性質 × Registry × C | 5/3/**4**/4 | 操作容易性 #33 vs 装置の複雑さ #36 | 空間(メタデータは registry、UI は購読) | ★★☆ | `studio._ARG_ROLES`(L1185、人間可読・一部 op)と `docs/ops/*.md` の frontmatter から初期値を生成できる。NEXT_SESSION B-1 の前提 |
| **5** | **Ledger の deque 化 + 台帳行の dataclass 化**: `_EVENTS = deque(maxlen=256)`、`FallbackEvent` dataclass(schema drift を型で止める) | #34 排除と再生 × Ledger × Q/C | **5**/4/5/5 | 速度 #9 vs 情報の損失 #24 | — | ★☆☆ | 1 ファイル数行。`fallbacks()` は `dict(e)` を返す契約を保てば互換 |
| **6** | **run_pipeline の provenance trace(side channel)**: 各段の (op, backend, device, fallback?, elapsed) を配列とは**別の**dict list で返す(`return_trace=True`)。sort 跨ぎ恒等を段単位で検出 | #17 多次元化 + #32 色変化 × Provenance × W | 4/4/3/**5** | 測定精度 #28 vs 物質の量 #26(メモリ) | **空間**(値と来歴を別コンテナ) | ★★☆ | ndarray subclass は演算で剥がれる(§3b Provenance × R)。`events_since(mark())` を段ごとに切るだけで作れる |
| **7** | **内層 Result 型(`OpResult`)+ facade は値**: backend/typed 層は `(ok, value, reason, kind)` を返し、facade が policy で値に畳む。`metriccontract.Attempt` を全 sort に一般化 | #4 非対称化 + #12 等ポテンシャル × Result × C | 4/4/4/5 | 測定精度 #28 vs 操作容易性 #33 | 条件(内層は型、外層は値) | ★★☆ | 現行の `guard` が例外→記録で同じ情報を得ているため**増分価値は限定的**。やるなら候補 6 と統合 |
| **8** | **backend 次元の統合(Strategy/Bridge を `ops.REGISTRY` へ)**: `gaussian`/`cv_gaussian`/GPU を 1 op × backends にし、profile で選ぶ。parity テストが op 単位で自動生成される | #28 機械系の置換 + #15 動性化 × Bridge × D | 5/3/4/4 | 適応性 #35 vs 装置の複雑さ #36 | 条件(profile) | ★★★ | `fslib` L1 に同設計が実在(`op(name, backend)`、`PROFILES`)。進化側の REGISTRY は名前が鍵なので後方互換に alias 層が要る |
| **9** | **fscript Interpreter 監査**: builtins dispatch を表に、AST ノード網羅テスト、`FScriptError` の kind 分類。Visitor 化は**しない**(VM 一本の決定 `FSCRIPT_DECISION` 判断 2 により codegen と意味論を共有する必要が無い) | #1 分割 + #33 同質性 × Interpreter × D/K | 4/5/4/4 | 制御の困難さ #37 vs 装置の複雑さ #36 | — | ★★☆ | `fscript.Parser`/`Node`/`Env`、`tests/test_fscript.py`。価値は限定的なので最下位 |

**上位 3 件は合計 ★☆☆ × 3 で、D を上げる幅が最大**(候補 1 は「壊れた op を利用者より先に見つける」、候補 2 は 17 op の KeyError を消す、候補 3 は GPU の沈黙再挑戦を止める)。候補 4 は Studio 4 本柱の前提なので UI 作業の直前に。

---

## §5 使い方(再利用チェックリスト)

### 5.1 ジレンマに当たったら

1. **2 語で言う**: 「改善したい特性 X(39 特性の番号)/ 悪化する特性 Y」。言えなければまだ問題が 1 つに潰れている(`FSCRIPT_DECISION.md §0` の「3 つの別々の問い」の型)。
2. **原理候補を引く**: raptor `triz-ideation` SKILL の矛盾マトリクス(または下の速引き)。
3. **§3a の当該原理の行を読む** → パターンと 4 軸。**制約と一致する軸プロファイル**を選ぶ:
   - hot path(op 本体・進化ループ内)→ S=5 必須。M は `out=`/view で稼ぐ。
   - facade / I/O 境界 → G=4 以上。S は 4 で妥協可(dict lookup 1 回)。
   - 検証・CI・監査 → D=5 必須。S は無視(時間分離で hot path 外へ)。
4. **3 点以下の軸の「短所のカバー」を辿る**(別行の組合せを重ねる)。カバーが辿れないなら、その構造は fullseye では使わない。
5. **§3b でコンテナを決める**。落とし穴列を読んでから書く。
6. 実装したら **`docs/design/` に判断を 1 節足す**(この文書の §4.2 に順位を入れ直す)。

### 5.2 コンテナが先か、パターンが先か

| 状況 | 先に決めるもの | 理由 |
|---|---|---|
| 既存の契約が動かせない(`(v,a,b) -> ndarray`、GPU tensor、memmap) | **コンテナが先** → §3c で原理→コンテナ、次に §3b を**逆引き**してパターン | パターンはコンテナに合わせて変えられるが、契約を破ると 861 op と進化が壊れる |
| 新しい責務(監査・方針・登録)を足す | **パターンが先** → §3a、次に §3b でコンテナ | 責務の置き場が決まらないとコンテナの寿命・所有者が決まらない |
| 速度が支配(ms 級 op、4 MP) | **コンテナが先**(N/V/G の S 列) | §1.2 の S は「データへの追加パス」で決まる = コンテナ選択そのもの |
| 検出性が支配(CI・監査) | **パターンが先**(Ledger/Probe/Policy) | D はパターンで決まり、コンテナは W/D/Q のどれでも 4 以上 |
| 迷ったら | **パターン → コンテナ** | コンテナの置換(list→deque)は 1 行、パターンの置換(Null Object→Result)は API 変更 |

### 5.3 39 特性 → 原理の速引き(fullseye で実際に出た矛盾のみ)

| 改善 vs 悪化 | 効いた原理(本書の実例) |
|---|---|
| 信頼性 #27 / 操作容易性 #33 vs 測定精度 #28 / 制御 #37 | #24 仲介・#1 分割・#35 パラメータ変化・#11 緩衝・#32 色変化・#23 フィードバック・#22(§4.1) |
| 速度 #9 vs 信頼性 #27(GPU) | #36 相変化・#11 緩衝(Circuit Breaker) |
| 適応性 #35 vs 操作容易性 #33(nary) | #17 多次元化・#5 統合(Composite) |
| 操作容易性 #33 vs 複雑さ #36(Studio ウィジェット) | #25 セルフサービス・#3 局所的性質(param spec) |
| 物質の量 #26(メモリ)vs 測定精度 #28(来歴) | #17 多次元化 + **空間分離**(side channel) |
| 時間の損失 #25 vs 信頼性 #27(検査コスト) | #9 先取り反作用 + **時間分離**(CI へ) |
| 適応性 #35 vs 複雑さ #36(backend 切替) | #28 機械系の置換・#15 動性化 + **条件分離**(profile) |

### 5.4 禁じ手(この文書から導かれる)

- **Null Object を Ledger なしで使わない**(§3a #8/#11/#39: 単独 D=1)。
- **成功経路に lock・O(N) 検査・小オブジェクト生成を置かない**(S は失敗時に払う)。
- **来歴を ndarray subclass に載せない**(numpy 演算で剥がれる → side channel)。
- **view を snapshot と呼ばない**(`setflags(write=False)` か `copy()` のどちらかを明示)。
- **表(dict)を増やしたら表どうしの整合テストを足す**(`_NDIM_OK` / `_ON_ERROR_CHOICES` / `PROFILES` / `_LABEL_READING_OPS`)。

---

## 付録 A. 検証済み事実と未検証事項

**検証済み(grep/sed で実在確認、2026-09-02〜03)**: `backend_safe.py`(`guard` L184 / `record` L113 / `FullseyeFallbackWarning` L50 / `_EVENTS` ring 256 / `_COUNTS` / `_WARNED` / `strict_mode` / `mark`・`events_since`)、`api.py`(`_policy` L1028 / `_check_input_sort` L1036 / `_guard_input` / `_run_guarded` L1062 / `apply(on_error=, template=)` L1109 / `run_pipeline(on_error=)` L1184 / GPU record L1095,1104,1230)、`ops.py`(`REGISTRY` L921 / `RT`・`_BY_NAME` L922-923 / `DROPPED_DUPLICATES` / import record L979)、21 の `backends_*.py` が `backend_safe.guard` へ委譲、`fullseye/__init__.py` の公開(`fallbacks` 等 L30,311)、`tests/test_backend_safe.py` / `test_ops3d_ledger.py` の存在、§2・§3b.1 の各ファイル・行。

**fullseye コアに存在しないことを確認**: Circuit Breaker / Retry(コア)/ Bulkhead / Saga / `QUndoStack` / Visitor クラス / entry_points plugin / `array.array` / octree / `queue.Queue` / 構造化 dtype / `order="F"`。

**未検証・注意**: (1) 本書の行番号は 2026-09-03 時点の作業ツリー。auto-commit で動く。(2) 採点は実測でなく §1.2 の基準による**見積り**(実測値があるのは `FSCRIPT_MEASUREMENTS.md` の言語層コストと `scale.tiling_error` のみ)。(3) タスク指示の「23 backend files」は本調査では **`_safe` を定義するファイル 22**(`backends.py` + 21)。`backend_safe.py` 自身のコメント(L28)は「23 backend files … 24 wrapper families」と書いており、`backends_typed` の `_fallback` を含めた数え方と思われる — 数え方の差で、事実は同じ(記録していたのは 1 つだけ)。
