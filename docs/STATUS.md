# imgevolve — status / plan (plan_ref)

**公開名 = fullseye**(2026-08-01確定 = full[FullSense]+bullseye[的を射る=正しいアルゴリズムを当てる]・PyPI/GitHub完全クリーン)/ **作業名 imgevolve**。物理リネーム(dir/repo/PyPI)は公開時=llcore統合可否確定後まで保留。画像処理アルゴリズムを **設計する** AI。
**スケーラブルなオペレータ・レジストリ**を進化させ、holdout で正直にゲートし、多言語
(Python/C)コードに codegen する。目標は **HALCON 級のオペレータ網羅**。

設計の正本: `C:/dev/tools/raptor/docs/design/imgevolve_s0s1_workgraph.md`

> **★★I-2「意味論を閉じる」完了(2026-08-15 その3, Opus5[1m]/ultracode)。** 正本 = `docs/FSCRIPT_DECISION.md`(§1.6 に完了記録)/ `docs/FSCRIPT_MEASUREMENTS.md`(実測)。**やったこと** = `fscript` を `fslib` の型モデルへ載せ替え、`tests/test_fscript.py` の strict xfail 5 件(欠陥2-5)を pass に。iconic 値を `FImage`/`Region`/`ObjectSet`(sort を型が運ぶ・内容から推測しない・真偽値なし)へ、制御タプルの `+` を HALCON 準拠の要素ごと演算に(連結は `[t1, t2]` flatten)、画素 op は `fslib` へ委譲(実装二重化なし)。value_kind も型ベースに。ベンチ2本(bench_realtime/bench_objectset_memory)を新型へ追従(実行確認済・ObjectSet 8.9x/10.2x 省メモリを再現)。**全スイート 4372→4377 passed / 0 xfailed(回帰なし)**、e2e で5欠陥の実挙動を目視確認。**★確定の背景**(不変) = Python で進める / 実行モデルは VM 一本 / **A(普通の Python)か B(独自 DSL)かは未決**(顧客の Q1/Q2 待ち・共通核フェーズ I は Path 非依存で先行可)。I-1 完了(commit 16955d0)= `fullseye_abi.h` 仕様先行 + `fslib.py` 適合 + `test_abi_conformance.py` 19 tests。
> **★fail-open 是正の self-check プリミティブ実装済(2026-08-15 その3 続き, commit f1a7379)**: fslib に `unmet_ops`/`readiness_report`/`require_ready`(レシピが使う全 op の動作バックエンドを起動前に検証、1 つでも欠ければ `FsBackendError` で起動拒否・degrade しない、§1.6b/R4)。`industrial` は numpy fallback なし=numpy-only op は起動拒否、`studio` は degrade。test 5 件・cv2 非依存。全スイート 4377→**4382 passed**。**残り配線** = 実 Runtime ローダー(レシピ/マニフェスト読込)から `require_ready` を呼ぶ(ローダーは golden/マニフェスト検証と同じ後段)。
> **★N1b 初期診断(2026-08-15 その3 続き, commit 78bb97e)**: `tools/bench_soak.py` に `timeBeginPeriod(1)` レバー(`--timer-resolution`、既定 ON)を追加し実検査で A/B。**★正直な結果=タイマ分解能は裾に効かなかった**(4MP で max off 18.81ms / on 18.67ms=誤差域。R4 の 26x は合成空ループの数字で OpenCV 主体の実検査に非転移→主因候補から**降格**)。かつ 82s の短 soak では 118.7ms を再現できず(cold p50 17ms=熱定常前・稀事象)。記録=`docs/FSCRIPT_MEASUREMENTS.md §9`。
> **★Runtime ローダー実装済(2026-08-16, commit 9b74fd3)= `fsruntime.py`**: レシピは判定前に fail-closed で (1)ABI major 一致 (2)source SHA-256 が manifest 署名と一致(改ざん検出) (3)全 op が industrial で動作バックエンドを持つ(`require_ready` 配線=§1.6b) (4)golden vector で「以前と同じ判定」を再現(R5) を証明せねば READY にならない=`FsNotReady`(degrade しない)。golden 実行が backend self-check と判定証明を兼ねる。`Recipe`/`GoldenVector`/`ReadyRecipe`/`sign`/`compile_recipe`、test 10 件。**golden vector 形式も確定**(GoldenVector=inputs→expect+tol)。
> **★N1b 裾は外部 CPU 競合に強く依存(示唆的・要追加測定 2026-08-16, `FSCRIPT_MEASUREMENTS.md §9.1`)**。★当初「原因特定/唯一の確実策/DEFINITIVE」と書いたが**自分の敵対検証で overclaim を摘発し格下げ**([[feedback_benchmark_honest_disclosure]]/[[feedback_no_false_reporting]])。所見(各 N=1): クリーンなアイドル機は 54,000 cycle で max **21.0ms(1.24x)= タイト**(計装なしでも ~18.9ms)、全コア飽和で **~73ms** へ膨張(cv2 系膨れ numpy threshold 不変)。★**ただし正本 118.7ms は一度も再現できておらず**、当時の測定が開発機上の並列エージェント汚染だった可能性を排除できない=「環境要因と確定」とは言えない。対策候補=コア確保(24 コア機 1 例・4-8 コア産線 PC 未検証・逆効果の恐れ)/ cv2 スレッド抑制(弱い)/ 優先度(未適用=未検証)。**受入前に必須**: 4-8 コア機の裾 / ≥3 反復+p99.9 / per-cycle fault / pool 版飽和 A/B / 118.7ms 再現 or 汚染源特定。
> **★常駐 Runtime 実装済(2026-08-16)= `fsruntime.FullseyeRuntime`**: `start()` が load ゲート(compile_recipe)を通してから READY、`inspect(images, judge)` が **PLC 語彙の Verdict(OK/NG/ERROR/TIMEOUT)** を返す(op 失敗=ERROR で fail-open を産線に出さない、deadline 超過=late result 付き TIMEOUT で判定は PLC に委ねる=R4)。裾対策 knob(cv2_threads/high_priority)も装備し実適用可否を正直に返す。test 16 件(loader 9 + runtime 7)。
> **★次 = フェーズ I の残り**(優先順): (1)PLC プロトコル結線(`comm.py`/`device.py` の Modbus/TCP へ Verdict を橋渡し)+ **OS レベルのコア確保配布手順**(裾の唯一の確実策)+ 二プロファイル配布イメージ(§4.1)。(2)任意: バッファ pool 化で p50 削減(~14,000 ページフォールト/cycle=毎 cycle 新規 4MP 確保。裾でなくバルク軸)。言語スコープは絞ったまま(Vector/STLコンテナ/例外/procedure/regexp は入れない)。**A/B の分岐は Q1/Q2 の答え待ち**。fscript/fslib/fsruntime/fullseye_abi.h の commit は local(auto-commit hook)・push 判断は human-gate。
>
> **v18.8 (2026-08-15, Opus5[1m]/ultracode) = 自律 UI 操作デバッグ・ハーネス + クラッシュ級バグ 3 件修正 + step 実行のショートカット化.** ユーザー指示「UIと操作系の修正・デバッグを自律で / 操作方法は外部AIと審議」。
> - **★自律 UI ハーネス** `tools/studio_ui_harness.py` = offscreen subprocess で Studio を起動し **実マウス/キーイベント**を全ボタン/アクション/**dock ドラッグ**/変数/右クリックへ注入(187 ステップ)。crash 帰属(step-log 前置 + faulthandler)+ hang 回避(modal/popup watchdog)+ slot 例外捕捉。**実イベントでしか出ない 3 クラッシュを自動検出→修正**(regression 付き studio 69→**74**):(1)3D surface ボタンで **Q3DSurface() の GL 不在 segfault** → `_opengl_available()` プローブで degrade(Remote Desktop/ソフトGLでも安全)、(2)`update_actions` が削除済みボタンで **RuntimeError** → `_enable` で削除耐性化、(3)**プライマリ Graphics 窓を閉じると常駐 view+グローバル操作ボタンが破棄** → close 拒否 event filter + detach 拒否で**常駐窓化**(=Codex #2)。dock ドラッグは全 25 パターン crash せず。
> - **★step 実行等をショートカット化**(ユーザー指示)= debugger 風ファンクションキー **F5=Run all / F6=Step / Shift+F5=Reset** を **window-scoped**(Ctrl+Arrow はパイプラインリスト scoped=タイプ中誤発火回避のため)で追加。QTest 実キー注入で Program エディタフォーカスからも発火を検証。Run メニュー + Keyboard shortcuts help に自動掲載。
> - **★操作仕様を外部 AI(Codex read-only)と審議**(「用途を考えて批判」)= 12 件の code-backed 指摘を一次検証し、**ユーザー選択で残項目を全実装**: カレント Graphics 窓モデル(#1–5=ハンドル番号/カレント窓ポインタ/変数ダブルクリック・Run once をカレント窓へ)、op 別引数 UI(#6)、step 変数フロンティア(#8)、Program 未適用編集の保護(#9)、Undo/Redo(#10, Ctrl+Z/Ctrl+Shift+Z)、削除後選択維持(#11)、**holdout 検証経路(#12=run_holdout + 「Validate on holdout…」Ctrl+H)**。未実装は #1 の `_render`→current 窓のみ(意味変更大)。
> - **★step 実行等をショートカット化**(ユーザー指示)= F5/F6/Shift+F5(window-scoped)。**★既定レイアウトを画像優先へ**(ユーザー指針=画像最大/コード2番目/op・変数は縮小 on-demand、layout_version 2→3)。
> - 詳細 = `docs/HDEVELOP_FIDELITY.md`『v18.8 実装記録 + 操作仕様・審議 + 追記群』。full suite **4297→4310 passed**(studio 69→82、回帰なし)、ハーネス 192 steps・fail0・slot0。全 local(auto-commit hook)。
>
> **v18.7 (2026-08-15, Opus5[1m]/ultracode) = Studio を HDevelop 忠実な IDE へ / P1 メニュー再構成.** ユーザー指摘「メニュー構成がおかしい・一般 IDE でない」+ 原則「IDE の画面はシンプルかつ多機能」([[feedback_ide_design_simple_multifunctional]])を受け、**HDevelop 仕様を Perplexity で確認**(iconic 変数モデル / Operator 窓 = コンボ選択+引数行 / 制御フロー if-else-for-while / メニュー構成)した上でメニューを標準 IDE 構成へ再編:
> - **Window 過積載を解消** = Panels / Graphics windows / Layout の3 submenu へ階層化(v18.6 で平坦に積んだ float/detach/layout を整理)。"Windows"→"Window"(単数・HIG 準拠)。
> - **View に Display mode(色マップ)を新設** = 右パネル combo のみだった 18 色マップを View から辿れるようにし双方向同期。
> - **Command palette を Run→Tools、Language を Help→Tools** へ(意味論の是正)。File を 画像入力 / pipeline 文書 / 結果 / Quit の群に整理。
> - **★submenu 実バグ修正** = `QMenu.addMenu(str)` の返す submenu の C++ 実体が shiboken に回収され**メニューが空になり得た**問題を、明示親付き `QMenu(title, parent)` 構築 + win 保持で解消(テストで実証・全 submenu に適用)。
> **★HDevelop 忠実化ロードマップ**(ユーザー要望を統合、正本 = `docs/HDEVELOP_FIDELITY.md`):
> - **P1 メニュー再構成 — 済**(Window submenu 化 / View Display mode / Tools / 単数 Window / submenu バグ修正)。
> - **P2a 引数の可視化 — 済**: `op_signature_detail`=knob a/b 役割(curated)+実装式を高密度表示(「引数が判断できない」解消)。
> - **P2b Operator 窓(引数入力+単発実行)— 済**: a/b の spinbox 引数入力、Insert はその値で挿入、**Run once ▷**=単発実行(`api.apply`)→結果を Graphics 窓表示・pipeline 不変、**op 名オートコンプリート**(QCompleter・contains)。
> - **P3 サンプル読込導線 — 済**: SAMPLE PIPELINES にヒント+「Browse with code…」でギャラリーをパネルから到達可能に。
> - **P4 iconic 変数モデル + パネル刷新 — 済(a/b/c/d)**: (a)Variable 窓の iconic 変数に **shape サムネイル**+iconic/control ラベル、ダブルクリック→Graphics 表示(既存)。(b)**Region 色 overlay**(`apply_display` の "region overlay"=binary region を source に amber 合成、View/combo に追加)。(c)**step 連動**(step_to で該当出力変数を var 窓でハイライト)。(d)**右クリック・コンテキストメニュー**(op/stage/var 各リスト)。残(P4e)=各パネル自己完結化・アイコンツールバー・変数編集。
> - **P5 HDevelop script 構文・制御フロー — 済**: Program 窓のパーサを HDevelop-style へ(module-level `parse_hdev_program`)。`op (a, b)`(括弧)+ `op a b`、`*`/`#` コメント、**`for N … endfor`(loop unrolling)**、**`if <定数条件> … else … endif`(静的分岐、< > <= >= = # 比較)**。while/elseif は runtime 変数要のため honest な unsupported エラー。生成も `op (a, b)` 形式。実行カーソル・breakpoint は既存(run_program)。残(P4e)= 各パネル自己完結・アイコンツールバー・変数編集。
> テスト = studio 53→**69 passed**、full suite 4285→**4297 passed / 0 fail**(各段で回帰なし)。全 local commit・push は都度。**★HDevelop 同等機能仕様の中核(P1 メニュー / P2 Operator 窓=引数入力+単発実行+補完 / P3 サンプル / P4 iconic 変数=サムネイル+overlay+step連動+右クリック / P5 script 構文+制御フロー)を一通り実装完了。** 正本 = 本 STATUS『v18.7』+ `docs/HDEVELOP_FIDELITY.md`。
>
> **v18.6 (2026-08-15, Opus5[1m]/ultracode) = Fullseye Studio 窓レイアウト自由度の拡張(ユーザー指示「窓/レイアウト配置の自由度をさらに上げる」).** v18.5 の Studio v2(ドック+MDI+Float-all)を「不十分」との評価→ `studio.py` に4方向追加(全て offscreen headless テスト付き):
> **(1) 名前付きレイアウトプリセット**=現在の geometry+dock/toolbar 配置(`saveState`/`saveGeometry`)を任意名で保存→適用→削除(QSettings 永続・offscreen は in-memory)。組込3種 `Balanced (default)` / `Graphics focus`(操作/表示/コード/変数 dock を隠しグラフィクス最大化)/ `Code focus`(Program dock 前面)。Windows▸Layouts を動的再構築=**フラット action 設計**(PySide6 `addMenu(str)` の submenu が Python 参照喪失で shiboken 削除される既知落とし穴を回避、テストで実証・修正済)。
> **(2) グラフィクス窓の MDI 外 detach/reattach**=アクティブ graphics サブ窓を独立トップレベル窓へ pop out(`Ctrl+Shift+D`)/復帰。image view は描画継続。
> **(3) パネル個別 float**=`Float panel` submenu で1パネルずつ float/re-dock(従来の all-or-nothing より細粒度・マルチモニタ向け)。
> **(4) ドックのネスト自由度**=既存 `AllowNestedDocks` を活用(据え置き)。
> テスト=studio 53→**57 passed**(preset round-trip / built-in 配置 / detach-reattach bookkeeping / 個別 float を新規)、**full suite 4281→4285 passed / 0 fail**(回帰なし)、F系(pyflakes)clean・既存 house-style(BLE001/E702)踏襲。公開ハンドル=`win._{save,apply,delete}_layout_preset` `_builtin_layouts` `_{detach,reattach}_graphics` `_float_panel` `_layouts_menu`。全 local auto-commit(未 push=human-gate)。正本=本 STATUS『v18.6』。
>
> **v18.5 (2026-08-15, Opus5[1m]/ultracode) = 未着手候補 (a)-(e) 完遂 + Fullseye Studio を HDevelop/VS 級 IDE へ全面刷新.** ユーザー指示「次セッションでは未着手候補すべてやる」→ 4068→**4281 passed / 0 fail**、N_OPS 646→**654**、**wheel 隔離 venv で end-to-end 検証済**(WHEEL N_OPS 654 == source、新 op・macro・auto_specs 全て同梱)。全 local auto-commit(未 push=human-gate)。
> **(b) op 波 +7(全 halcon=""=新 capability・numpy/scipy・決定的)**: `backends_alife2.py`(CA/人工生命: `alife_wolfram1d`[初期行→elementary rule 時空図、rule90=Sierpinski ground-truth] / `alife_langton_ant`[Langton の蟻・独立再シミュ照合] / `alife_lenia`[連続 CA Chan2019・ring kernel+Gaussian growth] / `alife_sandpile`[BTW 自己組織化臨界]) + `backends_deform.py`(制御点変形: `deform_tps`[Bookstein1989 薄板スプライン] / `deform_ffd`[Rueckert1999 B-spline FFD・injectivity 境界] / `deform_mls`[Schaefer2006 移動最小二乗・affine 再現])。honest 重複回避=swirl/barrel は既存ゆえ除外。**facade 追加** `deformreg.py`(Thirion demons 変形レジストレーション)+ specops 拡張(`spec_pansharpen`[Brovey/IHS/PCA] / `spec_decorrelation_stretch`[Gillespie1986] / `spec_fuse`[PCA/average/multi-focus])= NDVI/band_ratio/PCA は specops 既存ゆえ**融合系のみ追加**(honest 非重複)。
> **(c) DNA op を新 sort へ一般化**: 進化(robust.py core-only seeds8/gens80)→ `champion_to_macro`。**`macro_vol_denoise`**(vol_threshold→vol_gaussian、**volume→volume**、locked **25.74 dB > hand 20.94 dB = +4.80 dB**、`beats_hand=True`)= **4 番目の DNA op で自己拡張 registry を image→image / image→region に加え volume→volume へ拡張**。★honest negative(水増し回避)= count(locked 0.679 < hand 0.875 負け)/ locate・locate_rot(ncc/shape_locate primitive が locked 1.0 で saturated=引分)は **`beats_hand` を通らないため追加せず**。教訓=DNA registry の信頼性ガードは genuine 勝利のみ許可。
> **(d) FBP トモ→XCT**: `xct/examples/fullseye_baseline.py` を run 検証(exit0、sparse22 vs dense180 の FBP/SART/BP、sparse penalty **8.74 dB** を honest 提示)。
> **(e) auto_specs data-as-code(wheel 完全化)**: `backends_auto` が runtime で読む `data/auto_specs/*.json`(53 spec)が flat-layout ゆえ wheel 非同梱=非 editable install で欠落していた既存 finding を、`gen_auto_specs_data.py`→`auto_specs_data.py`(生成 py-module、常に wheel 同梱)+ load_specs の fallback で解消(macro DNA store と同手法)。**wheel 実測=backends_auto 174→227(source 一致)= 53 auto op 復活を実証**。
> **★敵対検証(honest DoD)**: 4 新モジュールを ultracode workflow(8 agents=実装+敵対検証)で並列 authoring→検証。全 finding を私が一次コード確認(v11 規律)。**real 修正**: alife_sandpile の HIGH(`b>=0.9` の run-to-stable が大画像で 76-140s・未安定化)を**総作業量 bound**(`_SANDPILE_BUDGET` grain-updates で sweep 数を制御 → size 非依存 ~tens-of-ms、L=320 が **140s→107ms**)+ docstring 正直化 / spec_fuse(pca)の近似反相関で非有界重み→相対閾値 guard / deform_ffd injectivity テストの vacuous 化→振幅依存の非 vacuous 化 / lenia の R=1 box 退化→R≥2 / decorrelation「全相関完全除去」は full-rank 限定と honest 化 / deformreg の +inf 扱い・residual_ssd clip を docstring 明記 / deform「exact identity」→resampling 誤差まで。0 reproduced defect(統合後)。
> **★Fullseye Studio v2(ユーザー主導・HDevelop 7.1/VS 級 IDE 化、`studio.py`)**: (1)高密度 VS スタイル QSS(padding/角丸圧縮) (2)全パネル `QDockWidget` 化(ドラッグ/フロート/タブ)+ 中央 `QMdiArea` グラフィクス窓 (3)**HDevelop 4 大窓**=Graphics(複数生成可)/Program(コード)/Variables&Objects/Operators (4)**Program 窓**=op 名 IntelliSense 補完・ブレークポイント(gutter)・Step 実行・**各行処理時間**・コード⇔pipeline 双方向 (5)**Variables 窓**=各ステージ出力を型付き列挙・任意変数をグラフィクス窓表示 (6)全機能を **Windows メニュー**から/複数グラフィクス窓/**マルチモニタ用 Float all panels** (7)**QSettings 永続化**(位置・レイアウト・言語) (8)**多言語 i18n を専用ファイル外部化** `studio_assets/i18n.json`(en/ja/zh、`languages` 駆動で拡張可・コード変更不要) (9)**op ヘルプ HTML** `studio_assets/op_help/*.html`(引数/使い方/**サンプルコード読込リンク**/関連 op リンク、`<op>.<lang>.html` フォールバック)+ **専用ヘルプダイアログ**(非モーダル・`op:`/`sample:`/`run:` アンカー)。studio テスト 49→**53 passed**(dockable/program/variables/i18n/help を新規テスト)、既存配線を全保持。honest 限界=op ヘルプ HTML は 3 例執筆(他は生成カード)・ツールチップ翻訳は主要 36 コントロール(未訳は英語 graceful)。
> **★次候補(未着手)**: (i)op ヘルプ HTML を主要 op へ拡張 + ja/zh 版 (ii)残 LOW finding(deform ffd 枠外サンプリング/_safe 非画像/brovey 負平均符号反転/spec detail_size 検証 等の edge-case docstring) (iii)更なる op 波(soft-body TPS の逆問題/追加 CA) (iv)more macro DNA(headroom ある問題で genuine 勝利のみ)。正本=本 STATUS『v18.5』。
>
> **v18.4 (2026-08-15) = 自己拡張 registry(進化の DNA op)+ Physical-AI/進化 op 波(+23 op).** ユーザー目標「差別化を進める。特に Physical AI や進化にかかわる、今後10年で使われる技術を op として揃える」。
> **① 自己拡張 registry(進化の閉ループ)**: 進化コアが発見した champion pipeline を **1 つの再利用可能 op に凝縮** = `backends_macro.py`(data 駆動 `data/macro_champions.json`)+ `champion_to_macro.py`(champion JSON→DNA 登録・honest provenance=full-registry train/holdout/locked 再計算 + trivial/hand/reference baseline + `beats_hand_on_locked_holdout` 判定)。マクロ op は凍結 name-pin stages を `decode_by_names`+`run_stages` で実行 → champion pipeline と **bit 一致**(`tests/test_macro_ops.py`)、a,b 凍結、halcon=""。初 DNA op = **`macro_denoise`**(bilateral×3、holdout 26.05 / **locked 26.28 dB** = gaussian→median reference を locked で **+2.56 dB** 上回る・honest 検証)。進化が自らの発見を次世代のプリミティブに選択可能(op 数はライブラリ wrap だけでなく発見の凝縮でも増える=記事/特許級差別化)。**★機構の汎化を実証**: registry は 3 DNA op にまたがる = `macro_denoise`(image→image) / **`macro_edge`**(image→**region**、gamma→bilateral→sobel_mag→scale_clip→otsu、holdout 0.948 / locked 0.906 F1、hand[sobel→threshold] locked 0.772 を超え) / **`macro_binarize`**(image→image、bilateral→unsharp→bilateral→lowpass→gopen→unsharp、holdout 0.953 / locked 0.750 IoU、hand[gauss→otsu] locked 0.619 を超え)。**いずれも locked holdout で hand baseline を上回る genuine な発見**で、機構が problem type 非依存(image→image / image→region)であることを示す。commit `8f75879`。★**不具合修正**: `.gitignore data/*` が DNA データを除外 → fresh clone で機能消失・CI で `test_macro_ops` 失敗する ship ブロッカーを `!data/macro_champions.json` 例外で修正。commit `8e3f7d6`。
> **② Physical-AI/進化 op 波(+23 op、全 halcon=""=HALCON 非対応の新 capability、classical numpy/scipy、RAD で 4 families の prior art 確認済)**: `aug_`(10)=sim2real センサー劣化(Poisson shot / Gaussian read / fixed-pattern PRNU / motion-PSF[angle] / rolling-shutter / vignette / JPEG 8x8 DCT / barrel-pincushion / cutout)= **進化/RL 方策の学習・stress-test 基盤**(RNG は knob seed で決定的)。`alife_`(8)=人工生命/セル・オートマトン(Conway 系 CA / cyclic CA[spiral] / Gray-Scott・Gierer-Meinhardt reaction-diffusion / Greenberg-Hastings 励起媒質[BZ] / DLA)。honest: 連続 PDE 3 members は既存 `ph_` と重複するが **toroidal-lattice / evolver-parameterised の真の variant**(max|diff| 0.27–0.93=非同一・既存の multi-variant 規範と整合)。`tac_`(5)=触覚/contact-from-shading(GelSight 系: contact mask[region] / Poisson height-from-shading / surface normal / pressure / shear)= **器用マニピュレーション**。REGISTRY 621→**644**、coverage **307/2313 不変**(honest: op 数増でも被覆主張ゼロ・dangling 0)、Wave-0 北極星不変(dtrain +0.0)、full suite 3862→**4033 passed / 0 fail**。**検証(honest DoD)** = 各実装 self-test + 全 registry 契約 sweep + module ground-truth + **3-agent 敵対レビュー(find→verify、0 reproduced defect)** + 自己 spot-check(非正方形/1x1/degenerate refit・finite・region 契約・variant 差分)。example=`examples/sim2real_and_alife.py`。commit `ff7d0da`。
> **③ event-camera facade + wheel-packaging 修正**: `events.py`=neuromorphic/event-camera 視覚(frame→event の v2e 系・plain numpy=次世代低遅延ロボ感覚)。`simulate_events`/`event_count`(log 強度変化で ON/OFF 極性)・`event_image`(IWE)・`event_rate`/`event_rate_map`・`time_surface`(SAE, T×H×W stack)・`warp_frame`・**`contrast_maximization`**(Gallego 2018=warp 済 event 像を最鋭化する定常大域フローを復元、既知 per-frame 速度を ground-truth 復元)。facade 配線(api.py+fullseye)、14 ground-truth テスト。★**不具合修正(wheel 実ビルド検証で発見)**: (a)`events`+`backends_aug/alife/tactile/macro` が pyproject `py-modules` 欠落=**非 editable `pip install` で 23 wave op・macro_denoise・events facade が全消失**(v18.3 と同クラス)→追加。(b)flat-layout の `data/*.json` は wheel に**載らない**(backends_auto も同一の既存制限)ため `data/macro_champions.json` 単独では installed package で macro_denoise が登録されない→ **`macro_champions_data.py`(生成 py-module の DNA store=常に wheel に載る)**を導入、backends_macro は .py store 優先で JSON fallback、champion_to_macro が両方書く。**isolated venv での wheel install 検証=macro_denoise 登録・wave 23/23・events facade 全 OK**。★既存 finding(範囲外・未修正)= backends_auto が runtime で読む `data/auto_specs/*.json` も wheel 非同梱ゆえ非 editable install で ~227 auto op 欠落(editable/source 経路は無影響)。macro DNA は data-as-code で回避。
>
> **v18.3 (2026-08-15) = Physical-AI 知覚パイプラインを徹底拡充(ユーザー指示「Physical AI に繋がる op を徹底的に増やす」+「skill として実用レベルに」).**
> **視覚 → 深度 → 点群 → 物体6DoF姿勢 → 把持** と **深度 → 地形 → 足場 → 歩容安定** を end-to-end で完備。
> 全 numpy/scipy native・古典手法(H&Z / Drost / Hirschmüller / Fusiello、**学習モデル不使用**)・ground-truth テスト付き。
> これらは進化 REGISTRY でなく **facade モジュール**ゆえ Wave-0 recapture 不要([A]自律安全)。full suite 3728→**3794 pass**(+66)。
> - **`camera.py`**(2D↔3D バックボーン, 22 テスト): `intrinsic_matrix`/`project_points`/`backproject`/`depth_to_points`/`normals_from_depth`/`triangulate`(DLT)/`solve_pnp`(DLT+LM=物体6DoF)/`fundamental_matrix`/`essential_matrix`/`recover_pose`(cheirality)/`undistort_points`(Brown-Conrady)/`stereo_rectify`(Fusiello)/`rodrigues`。
> - **`pcseg.py`**(点群セグメント/フィット, 15 テスト): `fit_plane/sphere/cylinder_ransac`/`remove_ground`/`euclidean_clusters`/`region_growing`/`obb`/`aabb`/`crop_box/sphere`/`farthest_point_sampling`/`curvature`/`height_above_plane`/`principal_axes`。
> - **`stereo.py` 深化**(6 テスト): `census_transform`+`disparity_census`(照明不変)/`disparity_sgm`(4-path SGM)/`speckle_filter`/`fill_disparity`/`disparity_confidence`(PKRN)。
> - **`terrain.py` 拡張 + `locomotion.py`**(12 テスト): `fuse_elevation`/`slope_map`/`roughness_map`/`surface_normals`/`step_edges`/`foothold_candidates`; `contact_points`/`support_polygon`/`com_support_margin`(静的安定余裕 McGhee-Frank)/`com_from_silhouette`/`gait_phase`(Alexander duty factor)。
> - **`sceneflow.py`**(7 テスト): `flow_divergence`/`flow_curl`/`focus_of_expansion`/`time_to_contact`(tau Lee1976)/`looming`/`ego_translation_from_flow`/`scene_flow`(Vedula1999)。
> - **`ppf.py`**(4 テスト): Point Pair Features 6-DoF 表面マッチング(Drost2010)= `ppf_model`/`surface_match`/`find_surface_pose`。既知姿勢を <0.2°/<1mm で回復(統合 example 実測)。
> - **`odometry.py`(新, P7, 6 テスト)= 視覚/RGB-D オドメトリ(自己位置推定)**: `rgbd_odometry`(depth ペア+flow→RANSAC-Kabsch でフレーム間カメラ運動)/`pnp_odometry`(3D-2D)/`integrate_trajectory`(相対運動→絶対4x4姿勢積算)/`umeyama_align`(Umeyama1991 相似アライメント)/`trajectory_error`(ATE)。既知の並進+光軸ロールを回復。camera+stereo+flow を束ねる navigation 層。
> - **`occupancy.py`(新, P8, 6 テスト)= 2D 占有格子/自由空間(経路計画層)**: `occupancy_grid_2d`(点群→トップダウン占有・z-slab フィルタ)/`inflate_obstacles`(C-space 円盤膨張 Lozano-Pérez1979)/`clearance_map`(障害物距離コスト場 EDT)/`line_of_sight`(Bresenham セル間衝突判定)/`frontier_cells`(free↔unknown 境界=探索 Yamauchi1997)。terrain の steppability への「どこを歩けて・どう行くか」補完。full suite→3818。
> - **`features.py`(新, P9, 6 テスト, push 45c6278)= 疎特徴マッチング(SLAM/再局在化フロントエンド)**: `harris_corners`/`fast_corners`(キーポイント)/`describe_patches`(zero-mean unit-norm パッチ記述子)/`match_descriptors`(NN+Lowe ratio+mutual)/`match_keypoints`(検出→記述→マッチで (x,y) 対応点→camera.recover_pose/solve_pnp)。密フローの疎な相補。honest: 照明不変だが回転/スケール非不変(ORB/SIFT は optional cv2)。full suite→3835。
> - **★S1 = out-of-core / memmap / マルチスレッド(`scale.py` 拡張, HALCON XL, 5 テスト, push d9d5682)**: `process_tiled_mt`(ThreadPoolExecutor でタイル並列・numpy/scipy が C カーネルで GIL 解放→計算重い tile-safe op が実効高速化・結果 bit 一致)/`open_memmap`(on-disk .npy 配列=RAM 非常駐)/`process_tiled_memmap`(memmap in→out でタイル逐次処理=任意サイズを bounded RAM、100k² も数 MB)。ユーザー既述の希望。full suite→3823。
> - **★第3敵対レビュー(features/P9 + scale/S1、4 agents)→ 3 real 修正(full suite→3837、push 69a91ec)**: describe_patches 偶数 patch クラッシュ(window side 一元化)/ process_tiled_mt・process_tiled が (H,W,C) でクラッシュ(out=src.shape)/ scale docstring に all-finite 前提明記。**これで P1-P9+S1 全モジュールが独立敵対レビュー通過(計3・40 real 修正)=honest DoD 完全クローズ**。
> - **★P7/P8 敵対レビュー(集中・4 agents・repro 検証)→ 7 real 修正 + 回帰 +6(full suite→3829、push 78f80ff)**: odometry rgbd_odometry がカメラ運動を返すよう修正(旧=シーン運動を integrate がカメラ軌跡として合成し**符号反転**)/ trajectory_error に with_scale(既定 rigid=メトリックのスケールドリフトを隠さない)/ _ransac_kabsch fallback の inlier 全True 偽装 / occupancy line_of_sight の対角壁トンネル(corner-cut 拒否)/ clearance・inflate の無障害物グリッド幻影 / occupancy_grid_2d の境界外点クランプ幻影。**★私の self-probe が all-free clearance を甘く見た点を独立レビューが摘発**=honest DoD の価値実証([[feedback_no_solo_ai_judgment]])。
> - **wheel パッケージング修正**: v18 波の 13 backends_* + videops が `py-modules` 欠落=pip wheel で import 不能だった(v14-review 系バグ)→ 全 runtime モジュールを監査補完。
> - **実用化 = skill + example**: `examples/physical_ai_perception.py`(manipulation/locomotion/ego-motion の3経路、実行検証済)+ グローバル skill `~/.claude/skills/image-processing/` に全 API + 2 worked pipeline を追記(subagent 実用レベル)。
> - **敵対レビュー(honest DoD)**: 6モジュールを ultracode workflow で並列レビュー(12 agents・repro 検証)→ 31 confirmed。私が全件一次コード確認(v11 規律)→ **real 30 件修正 + 回帰テスト +21(suite 3794→3806)**。camera solve_pnp が coplanar/checkerboard で誤姿勢(DLT 退化→homography init)/ normals_from_depth が斜面で法線を逆向き(n·X 判定へ)/ step_edges の対角ステップ符号消失・2x 過少 / foothold が未観測 NaN セルを提案 / gait/looming の NaN fail-open / scene_flow の無効視差ブレンド 等。**ppf の符号指摘(:186)は FALSE POSITIVE と検証**(α=α_s−α_m は Drost 準拠・全テスト+example が正しく回復・反転は破壊)=agent 指摘の鵜呑み禁止を実践。全 push 済(eae7d5c)。
> - 消費先: onocollo(物理動画→motion/TTC)・evis(ステレオ→`disparity_sgm`→`depth_to_points`→物体姿勢)・hillco(heightmap→`slope`/`foothold_candidates`+`com_support_margin` 歩容安定)。全 push 済 origin/master。
> - **★公開開示ポリシー厳守**([[project_imgevolve_goal_knowledge_layer_2026_08_13]]): provenance=公開論文/OSS からの再実装。記事で商用製品名を出さない。

> **v13 (2026-08-13) = 実用化 + 知覚スタック + Studio.** 詳細 = `docs/V13.md`
> (`api.py`/`fullseye` パッケージ・`pip install -e`・stereo/terrain/detect/registration/pose/imgio・
> HDevelop 風 `studio.py`・leg2 codegen/difftest/accuracy_bench)。
>
> **v14 (2026-08-13) = 知覚スタック完成(モーション + 堅牢化).** 詳細 = `docs/V14.md` / 使い方一枚 = `docs/PERCEPTION.md`。
> 時間軸 = `flow.py`(pyramidal Lucas-Kanade + Horn-Schunck + warp + `imgio.colorize_flow`)。
> 深度精緻化 = stereo `disparity_subpixel` + `lr_consistency`。歩行 = terrain `ground_plane` /
> `ground_surface` / `detect_obstacles`。把持 = registration `pca_align` + Trimmed ICP + `register`。
> 全 `fullseye` 公開・ground-truth テスト付き・**全スイート 2497 passed**。commits `a8fe121`/`e2feaf8`。
>
> **v12 (2026-08-12) = production hardening.** 全 521 op をテスト皆無 → 本番品質へ。
> 監査 = `docs/AUDIT_2026_08_12.md`(execution-verified 81 findings の disposition)+
> `docs/audit_findings_2026_08_12.json`(生 repro)。テスト = `tests/`(**2255 passing**、
> `py -3.11 -m pytest tests/ -q`)。**15 バグ修正済**(決定性 polar/sk_medial・NaN・型契約
> sort-aware `backend_safe`・reg_close border・evolve pop・robust.py champion 永続・閾値逆転)。
> 進化の北極星は無傷、被覆不変(269/2313)。deferred(意味論変更で champion が変わる=要判断)=
> 符号付き応答 16op ほか、詳細は AUDIT_2026_08_12.md。利用 skill = `~/.claude/skills/image-processing/`。

## 差別化(先行研究で確定, 2026-08-01)
AlphaEvolve(生ソース進化)/ TransCoder(翻訳)/ Halide(schedule 探索)いずれも
「アルゴリズム発見 × 型付き画像IR × 検証済み多言語codegen × オンデバイス × honest holdout」を
全部は満たさない。

## 現在地(v10 = 実 HALCON 被覆計測, 2026-08-01)
- **スケーラブル・レジストリ**(`ops.py` の `REGISTRY`, **153 op**)。op を1つ足すだけで進化も
  codegen も catalog も自動追従。core 67 + backend 86(skimage/opencv/torch を optional wrap)。
- **多ソート型システム(6+1 ソート)**: image / region / feature / contour(XLD) / match / any / volume(3D)。
- **10 タスク**: denoise/edge/binarize/count/locate/locate_rot/classify/barcode/vol_denoise/vol_count。
- S2 codegen(IR→Python+C)+ difftest(honest gate)。

### ★実 HALCON 被覆(memory 由来の推測を廃し、公式リファレンスを実スクレイプ)
- `halcon_scrape.py`: MVTec 公式 Operator Reference を実スクレイプ → **実 2313 op(HALCON 26.05,
  最新)/ 30 top-level 章 / 説明文 100%**。`--version` 引数化・`--op-sets` で複数版スナップショット。
- `halcon_coverage.py`: レジストリの `Op.halcon` を実リファレンスに突合。
  **被覆 = 79 / 2313(3.4%, 最新版)/ dangling = 0**(全 `.halcon` が実 HALCON 名 or 正直に空)。
- **バージョン横断(op 集合は版で増減する)**: v12=2147 / v13=2176 / v2311=2381 / v2411=2387 /
  v2505=2411 / **v2605=2313(最新, Legacy 209→110 に削減)**。union=2466。
  `.halcon` 名を **stable(全版)=77 / version-drift=2(`bilateral_filter`・`guided_filter`=v13 追加)/
  never(捏造)=0** に分類 = honest disclosure。
- **`mvtec-halcon` PyPI バインディング(版一致 26050.0.0=26.05)から型付き Python シグネチャ**を
  抽出 → typed stub(`data/halcon_stubs.json`, 2235/2313 に実シグネチャ)。3ソース(HTML scrape /
  binding / 被覆)が「dangling は本物の誤り」で一致=三重確定。
- 成果物: `docs/HALCON_COVERAGE.md`(版認識+gap ランキング)。scrape データは再生成可能な
  ローカルキャッシュ(`data/` は gitignore, MVTec docs/EULA 配慮で vendor しない)。

## ★現在地(v11 = HALCON-parity 自動生成 + 機能ゲート, 2026-08-12)
**目標の再確認(ユーザー)= 「HALCON と同じことができる」= 名前だけの被覆でなく各 op が
実際に同じ処理を行える**。これを honest に達成する土台を構築:

- **operator 知識グラフ**(`graph.py` → `data/halcon_graph.json`): 2313 op を
  {章 / desc / 型シグネチャ / arity(HObject入力数) / 推定sort / algorithm判定 / covered}
  でノード化。**unary algorithm = 535(honest な対象規模)/ n-ary = 210**。fan-out と
  自動生成の土台(正本 = STATUS.md の plan step 1)。
- **固定 shape 語彙 + データ駆動生成**(`backends_auto.py`): 17 の検証済み factory shape
  (pointwise/lut/linfilter/rank/graymorph/edge/freq/diffusion/texture/geom/threshold/
  segment/binmorph/region_trans/region_feat/img_feat/xld)を **手書きで正しく実装**。
  `SPECS`(halcon名→shape+params の**データのみ**)を語彙にマップ。**halcon 名は実
  reference で実在検証し、偽名は fail-closed でドロップ(捏造で被覆を水増ししない)**。
- **章別 fan-out**(`specs/fanout_workgraph.js`, 8 agent workflow): 各 algorithm 章の
  未被覆 unary op を固定語彙にマップした verified specs(`data/auto_specs/*.json`)を生成。
  **agent は genuine analog のみ採用し、noise生成/色多チャネル/射影変換/逆FFT/コーナー検出/
  ドメインROI/学習モデル等は honest に skip**(捏造せず)。生成後、私が全マッピングを
  **一次スポットチェック**し、非 genuine を除去(monotony/frei_dir/robinson_dir は誤マップを
  genuine 実装に差し替えて救済、equ_histo_image_rect/region_features/polar_trans_region/
  morph_skiz/gen_contours_skeleton_xld は同一性なしで削除)。
- **機能ゲート**(`verify_auto.py`): 各 op を canonical 画像/領域/輪郭で実行し、**例外なく
  宣言 sort を返すもののみ被覆にカウント**(「同じことができる」の実証)。
- **n-ary capability tier**(`imgops_nary.py`): 単一画像スレッドに載らない多入力 HALCON op
  (add/sub/mult/div/abs_diff/max/min_image、union2/intersection/difference/symm_difference、
  reduce_domain/overpaint_region/convol_image 等)を **17 op 本物実装**(全機能ゲート通過)。

**★honest 被覆(実測, `honest_summary.py` → `docs/HALCON_PARITY.md`)**:
- **269 / 2313 distinct real HALCON op を genuine 実装(11.6%)** = 進化 registry 252(color 12 含む)+ n-ary 17(disjoint)。
- registry ops 392(core 67 + backend 86 + **auto 227 + color 12**)。auto/color/n-ary は **全て機能ゲート通過**。
- v11f 増分 = Hough 変換(hough_line_trans/hough_circle_trans=accumulator図)+ subpixel crossings→contour
  (threshold_sub_pix/zero_crossing_sub_pix)+ closest_point_transform(補集合 EDT)+ junctions_skeleton +
  get_region_thickness。79→269 = **3.4倍**。
- **★map-to-shape 方式は実質出し切り**(v11→v11f 6ラウンド + fan-out 2回)。残 ~330 未被覆は
  (a) 専有/学習モデル(分類器・DL・OCR・Calibration・pose)(b) 多入力/n-ary(primitive間 distance・intersection・
  mosaic・union contours・compose)(c) 座標/tuple plumbing(getter/test/query)(d) ごく特殊な shape 要 =
  **新 capability か本質的 scope 外**。更なる breadth より **codegen/difftest による parity 実証(depth)** が本筋。

**★他ライブラリ機能の取り込み(`backends_extra.py`/`lib_coverage.py`, ユーザー指示「他の画像処理ライブラリの機能取り込み」)**:
imgevolve は HALCON 中心だが、**PIL/Pillow・scipy.signal/fft・cv2(484)・skimage(316)を introspect**(実インストール
=ground truth)して多ライブラリ軸で計測。**HALCON が重視しない distinctive op を 61 追加**(`xsk_`/`xcv_`/`xpil_`/
`xsp_`/`xsk2_`/`xcv2_`):
- **1st batch(21)**: inpaint・blob(LoG/DoG/DoH)・ORB・random_walker/flood/grabCut/marker-watershed・structure/Hessian tensor・NPR(stylization/pencil/edge_preserving/detail)・meijering/sato。
- **2nd batch(per-library fan-out 4-agent workflow で発掘→私が correctness 担保して実装, 40)**: PIL(emboss/contour/mode/posterize/solarize/autocontrast/offset[トロイダル]/contrast[平均中心])・scipy(wiener/savgol/hilbert/DCT spectrum/lowpass/denoise/cspline/detrend/morph_laplace/chamfer/gauss_grad_mag)・skimage(multiotsu/geomean-rank/reconstruction/h_maxima/diameter_opening/isotropic_close/HOG/Kitchen-Rosenfeld corner/Radon/inverse_gaussian_gradient/Wiener-deconv)・cv2(log-polar/mean-shift/hit-or-miss/Laplacian-variance焦点測度/FAST count)。
- **3rd batch(per-library fan-out で mahotas/PyWavelets/SimpleITK を新規 pip 導入 + 発掘, 56)**: `backends_r3.py`
  = agent が実走検証した one-line recipe を埋め込み、名前空間(np+各lib)で compile・exception-safe・**build 時に機能ゲートで
  再検証(fail-closed)**。mahotas(Zernike/pftas/bernsen/majority/Haar/Daubechies/soft-threshold/bwperim/regmin/self-match)・
  pywt(subband-tile/VisuShrink/firm-denoise/detail-energy/HF・LF-reconstruct/directional-detail/packet-entropy/MRA)・
  SimpleITK(curvature-flow/minmax-curv/curv-aniso-diff/laplacian-sharpen/grayscale-fillhole・grindpeak/opening・closing-by-recon/
  signed-Maurer-dist/connected・confidence-threshold/maxentropy・moments・huang-threshold)・skimage r3(rank otsu/majority/
  subtract-mean/equalize/mean-bilateral・h-minima・area・diameter-closing・Moravec・FAST corner・integral・local-median-threshold・
  is-low-contrast・estimate-sigma・peak-local-max)・cv2 r3(TVL1-denoise/NS-inpaint/pyr-laplacian/Hu/SIFT・BRISK・AGAST・LSD count)。
全 exception-safe・回帰 800/800・56/56 機能ゲート通過。**多ライブラリ**(`docs/LIB_COVERAGE.md`): HALCON+OpenCV+scikit-image+
PIL+scipy+mahotas+PyWavelets+SimpleITK+torch(GPU)= **9 ライブラリ横断**。全 `.halcon=""`(HALCON 軸不変=269)。**registry 481 / 総 op 509**。

**★処理効率 = GPU-ready バッチバックエンド(`accel.py`/`bench.py`, ユーザー指摘「GPUで効率化も重要」)**:
計算重い vectorizable op(gauss/mean/sobel/laplace/gamma/scale/invert/threshold/erosion/dilation/range_rect)を
**torch でバッチ一括処理**する高速経路。`--device cuda` で GPU 実行(device 非依存)。**忠実性**=accel が CPU
registry を内部で exact 再現(`imgevolve.py accel` で 10/11 interior<5e-3、境界のみ reflect/pool 規約差)。
**honest ベンチ(CPU 実測, `feedback_benchmark_honest_disclosure`)**: バッチは計算重い op を 1.6〜2.2x 加速
(range_rect 2.15x/dilation 1.75x/sobel 1.66x/gamma 1.60x)する一方、**自明 pointwise は tensor 変換で損**
(threshold 0.15x/scale 0.22x/invert 0.25x)、集計 1.31x。真の効き所は GPU(変換コストを大規模並列で償却)=
本環境 torch-CPU のみゆえ GPU 数値は RTX 5090 で実測。CLI = `imgevolve.py accel|bench [--device cuda]`。

**★codegen/difftest parity 実証(`parity.py` → `docs/PARITY_CROSSBACKEND.md`, ユーザー選択 depth)**:
HALCON/コンパイラ非依存で今実証できる parity = **クロスバックエンド一致**。独立実装(scipy/cv2/skimage)を
≥2 持つ 65 op を holdout 照合: **agree 27**(独立/冗長実装が 0.02 以内一致 = 強い parity 証拠。うち
scipy↔skimage の真クロスライブラリ一致 + core↔auto の codegen 忠実性)/ close 5 / **differ 33**
(共有 HALCON 名の裏でアルゴリズム実差 = Otsu≠Li≠Yen、scipy≠cv2 構造要素、Canny 実装差 等を**隠さず開示**、
`feedback_benchmark_honest_disclosure`)。C 経路(imgops.c 独立実装との言語横断 parity)は gcc 不在で本環境 skip
(toolchain 到着で自動充足)。CLI = `imgevolve.py parity`。

**★全 op 対応 = disposition map(`dispositions.py` → `docs/OP_DISPOSITION.json`)**: 偽実装で数を埋めず
(feedback_no_false_reporting)、**全 2313 op に truthful な disposition を付与(100% 対応、捏造 0)**。
`imgevolve.py has <任意の op>` が全 op に定義済み応答を返す(implemented=呼び方 / 未実装=status+理由)。内訳
(**2026-08-14 op 拡張 wave 1+2 後**): **implemented 324(14.0%)/ needs_new_capability 128(honest backlog)/
nary_multiinput 125 / out_of_scope_model 586(learned 442 + geometric 144)/ out_of_scope_plumbing 1150**。
→ honest な分母(実装しうる algorithm 系 ≈ implemented+needs_new_capability = 452)に対し **324/452 ≈ 72% を genuine 実装**。

**★op 拡張 wave 2(2026-08-14, ultracode workflow)= registry +39 op / coverage 282→307**: 5 新 backend
モジュール — `backends_regions3`(background_seg/clip_region/eliminate_runs/rank_region/region_features/
polar_trans_region 等 10)・`backends_imgtools`(add_image_border/crop_part/bit_lshift/rshift/mask/
convert_image_type 等 11)・`backends_measure1d`(1D caliper=measure_projection/pos/thresh/pairs/fuzzy 5)・
`backends_physics`(**物理演算 PDE**=perona-malik/coherence/reaction-diffusion/heat/mean-curvature/TV flow 6)・
`backends_decomp`(**分解**=structure-texture/texture-residual/RPCA low-rank/sparse/retinex/local-contrast/
homomorphic 7、産業検査差別化)。**25 が genuine 新 HALCON 被覆、14 は halcon=""**(physics 4=anisotropic/
isotropic/coherence/mean_curvature は backends_auto と重複ゆえ被覆主張せず[より忠実な実装]・decomp 7=新 capability・
full_domain=恒等 no-op)。★検証 agent が physics の重複被覆主張を摘発→私が一次確認して halcon クリア(v11 規律)。
REGISTRY 556→595。**固定参照パイプライン北極星は +39 op 後もスコア不変(dtrain +0.0)= gate 設計を実証**。

**★op 拡張 wave 3(2026-08-14, ultracode workflow)= registry +25 op(全て新 capability・halcon="")**: 4 新
モジュール — `backends_inverse`(逆問題=Richardson-Lucy/spatial Wiener/unsharp-deblur/motion-deblur/
back-projection 超解像/harmonic inpainting 6)・`backends_transform2`(領域変換=log-polar/Radon sinogram/
steerable/phase-congruency/gradient-domain/census/rank 7)・`backends_segment2`(適応セグメント=SLIC/
felzenszwalb/GMM/k-means/region-growing/normalized-cut/watershed 7)・**`backends_tomo`(トモグラフィ=
radon forward/FBP/SART/unfiltered-BP/sinogram-denoise 5、★XCT プロジェクト直結)**。**HALCON に無い新
capability ゆえ全て halcon=""**(被覆主張ゼロ=honest、coverage 307 不変・dangling=0)。4 クラスタ全て敵対検証
pass・suspect ゼロ。REGISTRY 595→620。**参照北極星は +25 op 後もスコア不変(dtrain +0.0)= gate を3度実証**。

**★op 拡張 wave(2026-08-14, ultracode workflow)= registry +35 op / coverage 252→282(dangling=0)**: 4 新 backend
モジュール(`backends_filters2` shock/gray_skeleton/topographic/lut/symmetry 等 9・`backends_regions2`
inner_circle/smallest_circle/smallest_rectangle2/runlength 等 10・`backends_subpix` サブピクセル極値点 6・
`backends_xldgeom` 輪郭モーメント/DP 簡略化 等 10)を並列実装→敵対検証。**30 が genuine 新 HALCON 被覆、5 は
honest に halcon="" **(重複2=smallest_rectangle1/local_max_sub_pix・再解釈3=clip/crop/regress は HALCON 意味論と
不一致ゆえ被覆主張せず)。加えて **video/時空間モジュール `videops`**(T×H×W を一級化=temporal 中央値/背景差分/
motion_energy/時空間 Gauss・Sobel/temporal MIP/flicker 除去/per-frame 等 15 関数、facade 公開)を追加。REGISTRY
521→556。**op 追加で Wave-0 fingerprint が trip → `recapture_wave0_pins.py --write` で gate 再祝福**(champion 無回帰を確認)。

**★被覆修正(2026-08-14, dispositions.py)= honest-disclosure バグ修正**: 旧 `MODEL_KW` は素の部分文字列マッチで、
`"pose"` が transpose/compose/decompose・pose タプル/四元数/同次行列の**代数 op を 47 件**、`"bundle"` が古典
bundle-adjust を「要・学習モデル」と**誤ラベル**していた(feedback_no_false_reporting 違反)。修正: (1)`pose`/`bundle`
を除去し、bare キーワードを**アンダースコア・トークン境界マッチ**化(部分文字列 FP を根絶、正当な model ヒットは不変を実測検証)
→ **49 op が out_of_scope_model から離脱**(plumbing 36 / needs_new_capability 7 / nary 6)、`implemented` は 269 で不変
(inflate ゼロ)。(2)model 章を **learned**(Classification/OCR/Deep Learning/3D Matching/Identification=真の学習モデル)と
**geometric**(3D Reconstruction/Calibration=古典幾何。学習不要、要キャリブ/多視点)に区別し reason を正確化。
回帰テスト = `tests/test_dispositions.py`(8 tests)。**未対応(要ユーザー判断の follow-up)**: 3D Matching 章の
純幾何ヘルパー(例 `create_cam_pose_look_at_point`)や 3D/Calibration の一部を out_of_scope_model → needs_new_capability
へ再分類するかは章単位判定の判断領域。今回は status を動かさず reason のみ正直化(backlog を私の判断で inflate しない)。
- **dangling(偽名)= 0**(fail-closed)。回帰スモーク 600〜800/同(image起点 decode+run クラッシュ0、color 到達も全 OK)。
- 開始(v10)79 → **245(registry)/ 262(総capability)= 3.3倍**。数値は memory 推測でなく実測。
- v11e 増分 = fan-out 第2ラウンド(拡張語彙で残精査、genuine 5: add_noise_distribution/polar_trans_region_inv/
  contour_point_num_xld/affine_trans_polygon_xld)+ corner 強度図(points_foerstner/points_harris_binomial)+
  XLD 楕円/モーメント特徴(eccentricity/orientation/elliptic_axis/diameter/rectangularity/moments_xld・shape_trans_xld)+
  zero_crossing・local_min・pruning。★fan-out 第2は total 5 のみ=**「shape へマップ」方式の genuine 天井が近い**シグナル
  (残未被覆は Hough/楕円フィット/subpixel点座標/多入力 distance・intersection/mosaic/pose/分類器モデル/run-length 等 =
  新 sort・新 capability か本質的 scope 外)。
- v11d 増分(XLD 輪郭群が主): 輪郭特徴 area_center_xld/circularity_xld/compactness_xld/convexity_xld・
  輪郭変換 close_contours_xld/affine_trans_contour_xld/projective_trans_contour_xld/polar_trans_contour_xld・
  region モーメント(moments_region_3rd/_central/_central_invar/_2nd_rel_invar/_3rd_invar)・
  dual_threshold・segment_image_mser(MSER)・regiongrowing_mean・estimate_noise。
- **★multichannel `color` sort 導入(v11c, ユーザー選択)**: `backends_color.py` に H×W×3 RGB の first-class sort。
  `cfa_to_rgb`(image→color, 実 Bayer demosaic)を bridge に進化から到達、`rgb1_to_gray`/`access_channel`/
  `edges_color` 等で gray へ復帰。**sort スレッドで型分離 → gray op に color は渡らず進化は無傷**。genuine 色op 12
  (trans_from/to_rgb・linear_trans_color・principal_comp・rgb1/3_to_gray・access_channel・edges_color(+_sub_pix)・
  lines_color・count_channels)。
- v11b 増分(shape 拡張で救済): region 計測(contlength/area_holes/height_width_ratio/moments_region_2nd/_2nd_invar)・
  cooc_feature_matrix(Haralick)・equ_histo_image_rect(局所equalize)・simulate_motion(方向ブラー)・
  projective_trans_image/_size/_region・polar_trans_image_inv・fft_image_inv・add_noise_white。
- **★将来利用インターフェース(`imgevolve.py` CLI)**: `has`/`ops`/`apply`/`pipeline`/`coverage`/`index`。
  `docs/OP_INDEX.json` = 全 369 op の機械可読索引。使い方 = README + memory `reference_imgevolve_usage`。
- **★GitHub push 済(2026-08-12 ユーザー許可)= github.com/furuse-kazufumi/imgevolve(private)**。公開(public 化)・
  PyPI・fullseye 物理リネームは別途 human-gate(公開時)。

**★進化ループでの他ライブラリ op 実使用 検証(2026-08-12, 全 521-op registry・短予算15-18世代)**:
- **denoise(★多 seed で honest 訂正, baseline 手作り 22.72 dB)**: seed0=24.12・seed1=24.14(**+1.4 dB で超え**)、
  seed3=22.22(僅差下)、**seed2=13.99(崩壊=trivial 14.998 未満)**。→ **2/4 seed が baseline 超え・分散大・1 seed 崩壊 =
  勝ちは seed 依存で robust でない**(`feedback_beat_the_null`/`honest_disclosure`: 単一 seed の勝ちを過大主張しない)。
  超えた champion は `xsitk_curv_aniso_diff`(SimpleITK)等の他ライブラリ op を選択 = 取り込みが**改善に寄与しうる**
  (robust 化には長予算・多 seed 選抜・崩壊対策が要)。
- edge: 0.830 F1(手作り 0.897 に僅差未達・random 0.311 超)、champion=`xcv2_meanshift`・`xcv_detail_enhance`・`sk_enhance_contrast`。
- binarize: 0.826 IoU(手作り 0.878 未達・random 0.407 超)、champion=`xsp_cspline_smooth`・`xkor_unsharp`(kornia)・`xsitk_minmax_curv_flow`。
honest: 他ライブラリ op は dead weight でなく全 3 タスクで champion に genuine 選択される。denoise は手作りを超え、
edge/binarize は短予算で僅差未達(長予算で縮む見込み)。拡張 registry は進化で使え、価値がある。

## HALCON ~2313 の実装可能性(章別内訳, honest)
- **アルゴリズム系 808**(Filters/Morphology/Regions/Segmentation/XLD/Image/Transformations/
  Metrology/Inspection…)= imgevolve の対象。cv2/skimage/scipy backend wrap で大規模実装可。
- **インフラ系 776**(Graphics/Tuple/System/File/Control/Develop/Matrix/Legacy)= HDevelop 言語・
  システム関数 = **アルゴリズム設計エンジンの対象外**(stub は自明だが実装は無意味)。
- **モデル/専有 622**(Deep Learning/OCR/Classification/Calibration/3D)= 学習済モデル・HALCON 専有 =
  部分的(汎用版は可、parity 不可)。
- → 「全 stub scaffold」= 生成可能。「全実装」= 不要。現実解 = **アルゴリズム系 808 を graph 駆動で
  backend wrap**(被覆 79→数百)。

## 次(graph エンジニアリングでスケール)
1. ~~オペレータ知識グラフを構築~~ **DONE**(`graph.py` → `data/halcon_graph.json`, 2313ノード)。
2. ~~analog edge から backend-wrapped registry を自動生成~~ **DONE**(`backends_auto.py` 固定 shape
   語彙 + fail-closed 生成 + 8-agent fan-out + 機能ゲート = auto 173 op / 被覆 79→186)。
3. **残る未被覆 unary algorithm = 366**(graph の `unary_uncovered_by_chapter`)。次の増分候補:
   - **語彙の拡張**で救える families(現状 skip されたが genuine 実装可能): motion/defocus 方向ブラー
     (linear blur kernel)、gray_skeleton(gray 版 thinning)、shock_filter(PDE 先鋭化)、
     projective_trans(射影変換 shape)、inverse FFT(fft_image_inv/polar_inv)、corner→point sort
     (Foerstner/Harris の点出力に新 sort)、cooc/Haralick テクスチャ特徴、moment features
     (region moments)。**shape を1つ足すと該当 op 群が一気に被覆に入る**設計。
   - **n-ary tier の拡張**(現17→): 画像演算の残り(min/max_image は済、`gen_*`除く算術)、
     region 集合の union1/複数入力、channel 合成(多チャネル対応が要件)。
4. 各 families を sweep で seed/世代積み各タスクの勝ちを確定。C runtime を median/bilateral/morph/fft へ拡張。
5. **honest 規律**: 新規 op は必ず (a) halcon 名を実 reference で実在検証(fail-closed)、
   (b) 機能ゲート通過(例外なく宣言 sort)、(c) shape が HALCON op の記述と materially 同一 —
   でなければ skip。被覆数は `honest_summary.py` の実測のみを正本とする(推測で語らない)。

## 自走のしかた(work-graph)
```powershell
cd C:\dev\projects\imgevolve
py -3.11 halcon_scrape.py --version 2605                 # 実リファレンス取得(最新)
py -3.11 halcon_scrape.py --op-sets --versions 12,13,2311,2411,2505,2605   # 版横断スナップショット
py -3.11 halcon_coverage.py                              # 被覆計測 → docs/HALCON_COVERAGE.md
py -3.11 sweep.py --round N                              # 進化を投入(seed 変えて別軌道)
```

## honest 限界
- 被覆 3.4% は正直な現在地(memory 推測でなく実測)。インフラ系 776 は意図的に非対象。
- OCR/DL/3D/matching は重い依存 or 専有アルゴリズムで parity 困難(汎用近似のみ)。
- 型シグネチャは `mvtec-halcon` バインディング由来(ライセンスは MVTec、ローカル参照のみ・非 vendor)。
- C は image op のみ emit(gcc 未導入環境)。compile 差分検証は toolchain 到着で自動充足。
