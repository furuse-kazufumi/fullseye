# Fullseye Script — 言語 / ランタイム / ウォッチ IDE 設計仕様(北極星)

> 目的 = Fullseye Studio の Program を「線形 (op,a,b) パイプラインにスクリプトの皮を被せたもの」から、
> **HALCON HDevelop 級の本物のプログラミング環境**へ進化させる。ユーザー確定の方向性(2026-08-15 対話):
> 1. **専用言語**(HDevEngine 構文が第一希望、C/C++ 風でも可)で、名前付き変数 + 実 if/for/while(**測定値で分岐**)+ per-object 反復 + I/O。
> 2. **Fullseye = 画像処理ライブラリ**、言語は**それを呼ぶ**層(ロジックを言語に内蔵しない)。
> 3. **コンパイラ方式が望ましい**(インタプリタより)。
> 4. **厳密なウォッチ**: 変数ウォッチに加え **画像ウォッチ / Region ウォッチ / 画像の特定ドメイン(ROI)ウォッチ**。
> 5. 最終的には **Fullseye を DLL 化**するのが一番自然。
> 6. ロボット制御プログラムまで書けること(知覚→判断→動作のループ)。

外部 AI(Codex read-only)設計コンサルト済(20 項目、本書に反映)。**規律=鵜呑み禁止、コードで裏取り**。

---

## 0. 正直な現実(honest reality)と段階戦略

- **imgevolve は現在 純 Python + numpy/scipy**(CLAUDE.md: core=numpy+scipy)。**DLL 化=ビジョン核をネイティブ(C/C++/Rust)へ書き換え + C ABI 公開**であり、大工事。
- ただし imgevolve には **S2 codegen(IR→Python+**C**)** の種がある(champion を C に codegen 済)。→ **DSL→C→ネイティブ**の経路は空想でなく既存資産の延長。
- imgevolve の差別化は **進化エンジン + 正直な holdout ゲート + op レジストリ**(ほぼ Python)。**これを壊さないことが最優先**(Codex #17)。
- **de-risk 方針**: いきなり DLL を書かない。**最も難しい設計(言語意味論・ウォッチモデル・ライブラリ API)を先に Python の bytecode VM で厳密に検証**し、正しさとデバッグ体験を固めてから、ホットパスを C codegen / ネイティブ DLL へ落とす。
  - 理由: 言語/ウォッチ設計の誤りをネイティブで直すのは高コスト。VM なら反復が速く、ステップ/ウォッチ/例外/ソース対応が自然。重い画素処理は元々 numpy/C 側で走るので、制御 VM の Python オーバーヘッドは通常小さい(要ベンチ、Codex #10)。

**結論(Codex #1)**: **言語を主**、線形パイプラインは「分岐・副作用の無い直列部分集合(LinearSubset)」として残し、進化・高速化・旧 UI に再利用。

### ★インタプリタ vs コンパイラの解決(ユーザー指摘: ウォッチは構造的に難しい / PyBind11 / DLL 現実性)
- **リッチなライブウォッチ(画像 / Region / domain / object / 変数)は「生きた変数環境」を要する** → **VM / インタプリタが自然に提供**する。**ネイティブコンパイル済コードは変数がレジスタ/スタックに散り、DWARF + デバッガ(gdb 型)が必要 = 構造的に困難**(ユーザー指摘の通り)。→ **ウォッチ要件が VM を事実上必須にする。**
- ∴ **HALCON と同じ二モード運用が正解**:
  - **IDE = VM 実行**(解釈): 各 statement 境界で生きた環境をウォッチ/step/breakpoint。← ここが本設計の主戦場。
  - **配布 / 高速 = compile**: DSL→C→ネイティブ DLL(既存 C codegen 資産)。デバッグ情報無しの最適化実行。
  - これは **HDevelop(対話=解釈)+ HDevEngine(配布=エンジン)** そのもの。
- **PyBind11 / 呼出し規約**: IDE を **全 Python(VM + L1 ライブラリ)で統一すれば PyBind11 不要**。PyBind11 / CPython 埋込が要るのは「**ネイティブコンパイル済プログラムが Python の Fullseye を呼ぶ**」混在時のみ → **配布時に L1 を DLL 化**して回避(native 言語ランタイム→native Fullseye DLL の直呼び)。**混在(native 言語 + Python ライブラリ)を避ける**のが工夫の要点。
- **DLL 化の難易度(正直)**: 「Python をそのまま綺麗な DLL 化」は不可(Cython/Nuitka は CPython+numpy 同梱の "Python in a box"、クリーンな C ABI にならない)。**本物の DLL = op を native 再実装 + C ABI = 大工事**。ただし **純アルゴリズム系 op は既存 C codegen で C→DLL 化可能**(cv2/skimage/scipy ラップ系は対象外)。→ **段階的にホット op のみ native 化**。**言語 / ウォッチ / ライブラリ API の設計検証に DLL は不要**なので、そこは Python で先に固める(de-risk)。L1 の API 契約を今固定 → 後で L2 を変えず L1 を DLL 差し替え。

---

## 1. 3 層アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│ L3  Studio IDE  … エディタ / 実行(debug|run|profile) /       │
│                   ★ウォッチパネル(§4) / ブレークポイント /     │
│                   実行カーソル / Variable & Object 窓          │
├─────────────────────────────────────────────────────────────┤
│ L2  Fullseye Script 言語 … lexer→parser→typed AST→           │
│     bytecode compiler→VM(=コンパイラ)。ソース位置を第一級。   │
│     制御フロー・変数環境・per-object 反復・例外・キャンセル。   │
│     ★ロジックは持たない。L1 を呼ぶだけ(LanguageOperatorSpec)。│
├─────────────────────────────────────────────────────────────┤
│ L1  Fullseye ライブラリ … 実パラメータのビジョン/計測/幾何/     │
│     デバイス関数(read_image/gauss/threshold/connection/        │
│     area_center/…/comm/device/acquire)。numpy/scipy 実装。    │
│     ★将来: ホットパスを C codegen → ネイティブ DLL(C ABI)。  │
│     進化エンジンの正規化ノブ registry とは契約を分離(§3)。    │
└─────────────────────────────────────────────────────────────┘
```

- **L1 = 「Fullseye ライブラリ」**(ユーザー方針 2)。今は Python モジュール `fslib.py`(+ `fullseye` パッケージから再 export)。**将来 DLL**: 同じ関数群を C ABI(`fullseye_threshold(img, lo, hi, out)` 等)で公開し、Python 側は cffi/PyO3 で薄くバインド。**API 契約(型・単位・出力)を今から DLL 化を見据えて固定**しておく(移行時に言語 L2 を変えずに差し替え可能に)。
- **L2 = 言語(コンパイラ)**。Codex #5 に従い **bytecode VM**(`LOAD_VAR/CALL_OP/STORE_VAR/JUMP_IF_FALSE/ITER_OBJECTS/CALL_DEVICE`)。AST 直接評価は増分 1 の踏み台(意味論検証)で、早期に bytecode へ移行。
- **L3 = IDE**。VM が statement 境界で `ExecutionEvent(span, changed_vars, removed_vars, pc, state)` を発火 → ウォッチ/変数窓を差分更新(Codex #12)。

---

## 2. 言語仕様(HDevEngine 風、Codex #2–4)

- **呼出し**: HDevelop 4 区画 `operator (InIconic : OutIconic : InControl : OutControl)`。区画は省略可だがコロン位置は維持。
  ```
  read_image (: Image : 'samples://images/parts_01.png' :)
  threshold (Image : Region : 0.42, 1.0 :)
  connection (Region : Objects : :)
  area_center (Object : : : Area, Row, Column)
  ```
  ★互換のため増分 1 では **assignment 形 `Out := op(In, ctrl…)`**(C/C++ 風・universal)も許可し、4 区画は op signature 整備と共に段階導入。
- **型**(Codex #3): **iconic**=`Image/Region/XLD` + **ObjectSet**(反復可能な iconic 集合)/ **control**=number/string/bool/tuple/handle。iconic↔control の暗黙混同は禁止(代入で sort 記録)。numpy 配列を tuple 扱いしない。
- **★Image = ピクセル + domain(HALCON 忠実、ユーザー指摘 2026-08-15)**: HALCON では **Image オブジェクトは domain(=処理対象領域を表す Region、既定=全面)を内包**する。Fullseye L1 も **`Image = FImage(matrix, domain: Region)`** とする。
  - ops は **domain 内のみ処理**(domain 外ピクセルは不変/未定義)。`reduce_domain(Image, Region : ImageReduced : :)` で domain を制限、`full_domain(Image)` で全面化、`get_domain(Image : Region : :)` で domain を Region として取り出す。
  - `threshold`/`connection` 等の出力 Region は入力 Image の domain と交差。これで「ROI に限定した検査」が第一級表現になり、§4 の **domain ウォッチ**(image の domain を見る)がネイティブに成立。
  - 実装(増分): 既定は domain=全面の軽量ラッパ(matrix そのまま + `domain=None`=full)。`reduce_domain` 時のみ Region を保持。DLL 化時も `FImage` の C ABI(pixels ptr + domain run-length)で表現。
- **式**: `:=`(代入)/ `=`(比較)/ `# != <= >= < >` / `and or not` / `+ - * / mod` / tuple `[..]`・`t[i]`・`|t|`・連結 / 括弧。**未実装構文は黙って解釈せず構文エラー**。
- **★control = HALCON タプルモデル(ユーザー指摘 2026-08-15)**: HALCON では **control 変数は全て Tuple**(スカラ=長さ1のタプル)で、**1 つのタプル内に整数/実数/文字列が混在**できる(例 `['part', 5, 3.14, 'ok']`)。→ Fullseye も control 値を **異種混在 Tuple**(要素 = int / real / string、bool は int)としてモデル化。
  - `Tuple` は不変値。要素型は保持(整数 5 と実数 5.0 を区別)。`t[i]`(0-based)・`|t|`(長さ)・`t1 + t2`(連結)・`subset/remove/insert/tuple_gen_const`。算術/比較は**要素ごとにブロードキャスト**(HALCON 準拠、長さ 1↔N・N↔N)。
  - 演算子 `+` は **数値タプル同士=要素和、文字列を含む=連結** の HALCON 曖昧規則を踏襲(仕様書に明記、`.` を文字列連結専用にするかは要検討)。空タプル `[]`、混在時の型昇格規則(int→real)を定義。
  - iconic(Image/Region/XLD/ObjectSet)は Tuple ではない別クラス(§3、混同禁止)。
  - ★実装注意: 現 PoC(`fscript.py`)は control を素の float/int/str/list で扱う。**増分1の型システムを HALCON Tuple に置換**(`Tuple` クラス + 要素型保持 + broadcast 演算)する必要がある。
- **★Vector 型(HDevelop 13+、ユーザー指摘 2026-08-15)**: HALCON には Tuple とは別に **Vector**(タプル or iconic を格納する**型付き・多次元コンテナ**)がある。`vector(dim)`、`Vec.at(i)`、`|Vec|`、代入 `Vec[i] := ...`、`for` で反復。Tuple(平坦・混在スカラ)と Vector(入れ子・object も格納可)を**別型として**用意する。
  - 用途: object/tuple の配列(例 各 blob の輪郭 Vector、行ごとの計測 Vector of Tuple)。ObjectSet(§3)は「iconic の 1 次元集合」の特化で、Vector はより一般(多次元・control も格納)。
  - 実装(段階): 増分1では Python list で近似、増分2以降で **`FVector`(要素型 + 次元を保持)** に厳密化。ウォッチは §4 の型別レンダラで Vector(要素を展開表示)対応。
- **制御**: `if/elseif/else/endif`・`for V := a to b [by s]/endfor`・`for Obj in Objects/endfor`・`while (c)/endwhile`・`repeat/until (c)`・`break/continue`。停止性: VM に**命令予算 + wall-clock deadline + キャンセルフラグ**、`while/repeat` は定期 UI ポンプ。
- **測定 multi-output**(Codex #8): `area_center(Region : : : Area, Row, Column)` の複数 control 出力を正式サポート(現 `api.apply` は先頭要素のみ float 化=情報欠落)。空領域/NaN/長さ不一致は定義済み例外か空 tuple、条件式で暗黙真偽化しない。

---

## 3. L1 ライブラリ = 言語演算子仕様(Codex #6–9)

- **526 op を直接 `RT[name](v,a,b)` で公開しない**。`LanguageOperatorSpec(name, in_iconic, out_iconic, in_control=[Param(name,type)], out_control, invoke)` を別レイヤに置く。
- **正規化ノブ(a/b∈[0,1], 進化専用)と言語の実引数(sigma=1.5 等)を分離**(Codex #7)。逆写像が不正確な op は native 実装を用意。`normalized_knobs` と `semantic_parameters` を別契約に。
- **ObjectSet**(Codex #9): 現 region は二値マスクで個別 identity 無し。`ObjectSet` = **ラベル画像 + object ID 列 + 遅延 view**(mask はコピーせず必要時 materialize、copy-on-write)。`connection` が生成、`select_obj/concat_obj/count_obj/for Obj in Objects`。
- **未整備 op** は `legacy_apply(Image : Result : A, B :)` に警告付き隔離(一括で HDevelop 互換と称さない)。
- **増分 1 の L1 最小語彙**(実装済み種= `fslib.py`): read_image/to_gray/gauss/mean_smooth/invert/threshold/binary_threshold/dilation/erosion/connection/count_obj/select_obj/area_center/area/select_shape/union_object/mean_gray/max_gray/min_gray/region_to_image。

---

## 4. ★ウォッチモデル(ユーザー最重要・厳密設計)

ユーザー要件 = 変数ウォッチだけでなく **画像ウォッチ / Region ウォッチ / 画像の特定ドメイン(ROI)ウォッチ**。デバッガの中核。

- **観測対象(Watch)は型付き式**: `Watch(expr, kind, options)`。**ウォッチは型ごとに拡張可能なレンダラ登録制**(`WatchRenderer` レジストリ)= 新しい iconic/handle 型を足したら renderer を 1 つ登録すれば IDE が対応。ユーザー指摘「HALCON には Region 以外のオブジェクトもある、それも全てウォッチ必須」に対応。
  - `kind=control` … 数値/文字列/tuple の値(履歴リング + 変化グラフ)。
  - `kind=image` … 画像(+ domain)。表示=サムネイル + ピクセル統計(min/max/mean/hist) + **ズーム可能ビュー** + **domain 境界 overlay**。オプション: colormap、値レンジ。
  - `kind=region` … Region(マスク)。表示=元画像上に色 overlay(margin/fill) + 面積/重心/bbox。
  - `kind=xld` … **XLD(サブピクセル輪郭/ポリゴン)**。表示=元画像上に輪郭 polyline overlay + 制御点数/長さ/曲率。HALCON の XLD_cont/XLD_poly に相当(imgevolve は contour(XLD) sort を既に持つ)。
  - `kind=domain(ROI)` … **画像の特定ドメインをウォッチ**: `Watch(Image, domain=Rect(r1,c1,r2,c2))` または `Watch(Image, domain=Region)`。表示=その ROI に**限定**した crop + 統計(ROI 内 mean/hist/欠陥率)。**HALCON の Image が内包する domain(§3)そのもの**を非破壊観測。
  - `kind=objectset` … ObjectSet(**任意 iconic 型の集合**、Region に限らない)。表示=object 数 + 各 object を型別 renderer でサムネイル + 特徴表。
  - `kind=handle` … **不透明ハンドル(matching model / measure / classifier / calibration / OCR 等)**。表示=ハンドル型名 + 主要パラメータ + 生成元(内部生データは出さない)。HALCON の handle 群に対応。
  - **拡張性**: `register_watch_renderer(type, renderer)` で新型を追加(volume/point-cloud/mesh 等 imgevolve 固有の iconic も同機構でウォッチ可能に)。
- **評価タイミング**: VM の各 statement 境界で、生存しているウォッチ式を**その時点の変数環境で再評価**(step 中は現在 pc の環境)。ループ内は iteration index + call depth を付す(同一行の区別、Codex #13)。
- **性能/メモリ**: 巨大配列を signal でコピーせず **value ID + generation** を渡し、thumbnail worker が世代確認後に非同期描画。履歴は既定「直近 N 世代 + サムネイル」、明示 watch のみ完全値 pin(Codex #12/#13)。ROI ウォッチは crop だけ materialize。
- **ウォッチ式の言語内表現**: `watch Image`, `watch Region as overlay`, `watch Image[Rect(10,10,50,50)]`, `watch |Objects|` を Studio UI(右クリック→Watch / Watch パネルに式追加)で管理。式は L2 のサブセット(副作用なし)に限定。
- **step 連動**: 実行カーソル移動 → 全ウォッチ + Variable/Object 窓が現在の生存変数状態へ差分更新(Codex #12)。未到達変数は「未定義」、ObjectSet は lazy。

---

## 5. 進化の北極星との共存(Codex #16, #17)

- **round-trip は一方向**: `stage list → script` は常に可能。`script → stage list` は **LinearSubset**(単一 iconic in/out・直列・定数 control・分岐/ループ/I-O/複数出力なし)のみ。変換不能は行番号付きで提示、勝手にフラット化/分岐選択しない。
- **進化は `EvolvableBlock` のみ生成**(6 slot×(op,a,b) 固定長を維持)。外側の言語が取得/分岐/測定/動作、block 内だけ既存ゲノム + train 選択 + holdout/locked-holdout。
  ```
  evolve_block Denoiser (Input : Output)
    gauss_filter (Input : T1 : 0.63 :)
    threshold (T1 : Output : 0.47, 1.0 :)
  endblock
  ```

## 6. ロボット制御(Codex #20)

- 任意 Python 公開でなく**能力制限 builtin**: `open_camera/grab_image/close_camera`(acquire.py)、Modbus `read/write`(comm.py)、DigitalIO `set/get/pulse/wait_input`(device.py)を LanguageOperatorSpec 登録。
- opaque handle + `on_error/finally` 自動 close、単調時計 deadline、`wait_input(...,timeout)`、キャンセル可能 `delay`、simulation backend、動作範囲/速度/出力 pin の allowlist、Studio 初回 arm 確認。画像 worker と device I/O worker を分離、VM は逐次意味論を保ち future 完了待ち。→「取得→測定→条件分岐→動作→センサ確認→timeout」ループを安全記述。

---

## 7. サンプル配置(Codex #14–15)

```
samples/
  scripts/     01_threshold_and_measure.fsh …            # サンプルコード(専用フォルダ)
  images/      parts_01.png defects_scratches.png …       # 合成画像(手続き生成)
  generators/  make_inspection_samples.py                 # 生成器(seed/条件)
  manifests/   samples.json                               # 生成条件・期待結果・ライセンス
```
- **画像生成 AI は本環境から呼べない**(text-to-image ツール無し)。マシンビジョン用は**手続き的合成が最適**(決定的・ライセンスクリーン・正解ラベル付与=holdout 直結)。有用: 照明勾配付き部品/面積違い blob/接触・重なり部品/欠け・傷/低コントラスト異物/座標既知の校正 grid。
- `read_image` 解決規則(決定的・安全): `samples://images/x.png`=install 済 sample root、相対=呼出しスクリプトの親、絶対=許可 workspace 内。cwd 依存禁止、path traversal 検査、拡張子制限(Codex #15)。

---

## 8. 段階的ロードマップ(Codex #18 を imgevolve 現実へ調整)

- **増分 1(言語 PoC・実装中)**: AST インタプリタ `fscript.py`(意味論検証)+ L1 `fslib.py`(実装済み種)+ 実 if/elseif/else・数値 for・object for・代入・式・per-object 反復。**「blob 検出→per-object 面積→閾値除外→重心」実アルゴリズムが走ることをテストで実証**。samples 生成器 + 2 スクリプト。
- **増分 2(コンパイラ化 + ウォッチ)**: bytecode VM 化、ソース span 第一級、ExecutionEvent、Studio に **ウォッチパネル(§4: image/region/domain/objectset)** + ブレークポイント + step-in/over/out + 実行カーソル。`while/repeat`、診断。
- **増分 3(ライブラリ拡充 + 整合)**: LanguageOperatorSpec で legacy op adapter、測定 multi-output、ObjectSet(ラベル共有)、LinearSubset 抽出 → stage list 双方向、EvolvableBlock。
- **増分 4(デバイス/ロボット)**: acquire/comm/device の能力制限 builtin、安全ポリシー、simulation。
- **増分 5(ネイティブ化)**: ホット path を **C codegen(既存資産)→ ネイティブ Fullseye DLL(C ABI)**、cffi/PyO3 バインド。ベンチで妥当性確認後に選択適用。**L2 言語を変えずに L1 を DLL 差し替え**。

各段階で parser golden tests / 型エラー / 空 object / キャンセル / 同一 seed 画像 / 旧 pipeline parity を回帰化。

---

## 9. 現状のプロトタイプ

- `fscript.py`(増分 1・AST インタプリタ): lexer/parser/AST/evaluator + 変数環境 + 実 if/for/while/repeat + object 反復 + 例外 + step 予算。**意味論の検証用**(interpreter→bytecode VM→compiler は自然な進化で、まず意味論を固めるのが定石)。
- `fslib.py`(増分 1・L1 種): 実パラメータのビジョン関数群。
- 次: この 2 つで実アルゴリズムをテスト実証 → 増分 2 の bytecode VM + ウォッチへ。
