# Fullseye Script / Runtime — 要件定義と基本設計(確定案)

> 発端 = ユーザーの問い(2026-08-15):
> 「**Python で進めて実用性としては問題ないか? 製造業ではまだ Python でシステムを組むというのは少ない傾向にあるよ。**」
>
> 本書はこの問いに、**憶測でなく一次情報と実測**で答え、要件定義と基本設計を確定する。
> 実測の生データ = `docs/FSCRIPT_MEASUREMENTS.md` / 言語仕様の正本 = `docs/FSCRIPT_LANGUAGE.md`。

---

## 0. 問いの再定義 — 「Python か否か」は問いとして誤りだった

調査の結果、この問いは **3 つの別々の問い**が 1 語に潰れていたことが分かった。分けると答えが変わる。

| 潰れていた問い | 答え | 根拠 |
|---|---|---|
| (a) 設計環境(IDE)を Python で作ってよいか | **問題なし** | 顧客の設備上で動くものではない。HALCON の HDevelop も重量級 GUI |
| (b) 検査ロジックを走らせる**言語処理系**が Python でよいか | **問題なし(コストがノイズに埋没して検出できない)** | 実測 §1.4 / HALCON 自身が本番にインタプリタを出荷(§1.3) |
| (c) **画像処理エンジンの実体**が Python/numpy でよいか | **ここだけが本当の争点。現状のままでは No** | 実測 §1.2(カーネルで 23 倍・オブジェクトモデルで 5.8 倍) |

**業界が受容しているのは (a)(b) であり、拒否されているのは言語ではなく「保証できないランタイム」。**
そして Fullseye が現在いるのは (c) — 前例が確認できない場所である。ここが結論のすべて。

---

## 1. 判断に使った証拠

### 1.1 商用プラットフォームは Python を第一級 API として本番提供している(一次情報)

外部 AI(Codex, web 検索つき read-only)に一次資料を当てさせ、公式ドキュメントで裏を取った結果:

| 製品 | 公式 Python API | 位置づけ |
|---|---|---|
| MVTec HALCON / HDevEngine | あり | **第一級**(試作専用ではない) |
| Euresys Open eVision | あり | **第一級** |
| Basler pylon (pypylon) | あり | 正式 API(ただしサポートは限定的と自ら明記) |
| Cognex VisionPro / In-Sight | 確認できず | .NET 中心 |
| MERLIC / NI VDM / Keyence CV-X / OMRON FH | 確認できず | 専用 GUI・専用コントローラ |

**★ただし決定的な但し書き**: これらの Python API は**すべて「Python → ネイティブライブラリのバインディング」**であり、
画像演算を Python バイトコードで実行する構成ではない。
→ **業界が認めているのは「Python がネイティブエンジンを駆動する」形**であって、
  「エンジン自体が Python」ではない。**この区別が本件の核心。**

### 1.2 「Python だから弾かれる」という一般条件は存在しない

Codex が一次資料で確認した結論(確信度: 高):
「Python 製だから採用可能/不可能」という製造業共通の基準や採用率は**確認できない**。
弾かれるのは以下の**個別要件違反**であり、**そのすべてが Python 非依存**である:

- 顧客仕様書で言語が C++/C#/PLC 等に限定され例外承認がない
- 要求サイクルタイム・最大ジッタ・連続トリガ数を**実機試験で満たさない**
- ハードリアルタイム/安全認証済み実行環境が必須なのに Windows+CPython しか出せない
- 安全機能(非常停止・ガード・STO)を担うのに PL/SIL の検証証拠を出せない
- 規制工程でバリデーション資料(要求仕様・リスク分析・版管理・監査証跡)を出せない
- 顧客のセキュリティ規程が Python 本体・pip・未承認 OSS を禁止している
- オフライン復元・SBOM・ソース引渡し・保守期間中の供給計画を出せない

**含意**: 障壁は言語ではなく**「保証・証拠・供給」**。これは Python でも C++ でも同じ量の仕事であり、
むしろ**一人ベンダーであることの方が本質的リスク**(Codex も同じ結論)。
なお「日本では SIer 文化ゆえ Python が拒否される」「装置保守年数は必ず 15 年」といった一般化は、
公的統計では**裏付けられなかった**(IPA 2012 年組込み調査で C 60.3% / C++・C# 21.0% という古いデータのみ)。

### 1.3 ★HALCON は本番にインタプリタを出荷している(MVTec 公式で確認)

> HDevEngine is "**an interpreter-based library that loads and executes HDevelop programs and procedures at runtime**"
> — 対応言語 C++, C#, **Python**, .NET。
> C++/C# への export は「**HDevEngine API 呼び出しのラッパ生成**」であり、HDevelop のロジックをネイティブへ変換しない。

**含意(設計を 1 段単純化する)**:
世界最大手が本番でインタプリタを走らせて成立している。速いのは**オペレータがネイティブ**だから。
→ **「IDE = VM / 配布 = compile」の二モードは不要**。
→ Codex が Path D の致命傷と指摘した「インタプリタと codegen の意味論を 650 op で二重保守」を、**そもそも背負わない**。

### 1.4 実測(この PC。詳細 = `docs/FSCRIPT_MEASUREMENTS.md`)

4 MP(2048x2048)・200 blob の検査 1 サイクル:

| | p50 | 対現状 |
|---|---:|---:|
| 現状(`fscript.py` L1 + AST インタプリタ) | 1448 ms | 1.0x |
| 言語層を外して L1 を直接呼ぶ | 1382 ms | 1.05x |
| ObjectSet(ラベル画像 + ID 列)へ置換 | 250 ms | 5.8x |
| **ネイティブカーネル(OpenCV)+ ObjectSet** | **10.8 ms** | **134x** |

- **言語 / VM 層のコストは検出できない**(ノイズに埋没。分離測定で 0.67 us/statement = 1 サイクル 1,500 statement まで 10 ms サイクルの 10% 未満)
- **5000 サイクル連続で p99.9 = 13.5 ms / max = 16.7 ms**(駆動は Python)
- **GC はこの負荷ではジッタ源ではなかった**(収集回数 0、gc 抑止で max はむしろ悪化)
- コールドスタート `import api` = **1.8 s**(うち torch 800 ms)→ **Runtime 常駐が必須要件**
- 配布フットプリント = numpy+scipy+cv2 で **326 MB** + stdlib 49 MB ≒ **375 MB**(torch/PySide6 を除けば商用同等)

**この 134 倍のどこにも「Python をやめる」は入っていない。**

### 1.5 コードの実態(実測で判明した、設計書との食い違い)

| 設計書の記述 | 実際 |
|---|---|
| 「実装済み種 = `fslib.py`」 | **`fslib.py` は存在しない**。builtin は `fscript.py` 内。**L1/L2 未分離** |
| 「`for Obj in Objects`」 | **未実装**(`_KEYWORDS` に `in` が無い) |
| 「smoke test 実証」 | **コミットされたテストは 0 件だった**(本セッションで新規作成: 22 passed / 5 xfail) |
| 「C codegen 資産の延長で DLL 化」 | `imgops.c` = **112 行・8 op**(650 中 **1.2%**)。しかも**全て image→image フィルタ系で region/blob 系はゼロ** = 実測で 21 倍差が出た側を 1 つもカバーしていない |
| — | **バックエンド選択機構が無い**。`gaussian` と `cv_gaussian` は**別の op** として登録 = 「同じスクリプトを別実装で走らせる」が表現できない |

**ただし 1 つ、極めて重要な既存資産がある**:
`difftest.py` は既に **「Python 実装を正解オラクルとし、C 実装を holdout 入力上の差分テストで検証、
全 op がカバーされない場合は正直に SKIP」** を実装している。
→ **ネイティブ移行の検証ハーネスは新規開発不要**。機構は実在し、規模だけが未証明(8/650)。

### 1.6 実測の過程で見つかった「黙って誤答する」欠陥 5 件

すべて根因は同じ = **言語が自前の型モデルを持たず、numpy/Python の意味論を継承している**。
**実装言語を変えても残る**。回帰テスト = `tests/test_fscript.py`。

| # | 欠陥 | 症状 | 状態 |
|---|---|---|---|
| 1 | `*` を行途中でもコメント扱い | `A := I * 2` が `A := I` に。**エラーも出ない** | **修正済** |
| 2 | `_norm01` が画像の最大値で正規化 | 隅の明るい画素 1 個で同じ部品の area が **256 → 1** | xfail 固定 |
| 3 | 数値 Tuple の `+` が連結 | HALCON は要素和 `[11,22,33]`、現状は連結 | xfail 固定 |
| 4 | iconic が条件式で暗黙に真偽化 | `if (Region)` が `.any()` で通る | xfail 固定 |
| 5 | 比較が配列を返し条件で潰れる | `if (Image = 0)` が「1 画素でも 0 なら真」 | xfail 固定 |

**欠陥 2 が最も重い**: 実ラインの正反射・ホットピクセルで**判定が黙って反転する**。
これは性能問題ではなく**信頼性問題**であり、ネイティブ化より優先度が高い。

### 1.7 ★確定案の要石を PoC で de-risk 済み(本セッションで実装・実測)

本確定案は「**1 op = N バックエンド + Python 実装をオラクルとする差分テスト**」に全体重を預けている。
成立しなければ増分 2 以降が崩れるので、**先に最小 PoC を作って確かめた**。

実装 = `fslib.py`(L1 の種)/ 契約テスト = `tests/test_fslib.py`(**18 passed**)。

**証明できたこと**:

| 主張 | 証拠 |
|---|---|
| 型が sort と値域を**運ぶ**(推測しない) | ホットピクセルを足しても測定部品の面積は 256 のまま。同じ入力を現 `fscript` に通すと変わる(テストで両方を実行して対比) |
| iconic は真偽値を持たない | `bool(FImage/Region/ObjectSet)` は `FsTypeError`。`if (Region)` が書けない |
| 誤った sort を渡すと型エラー | `connection(image)` / `gauss(region)` が `FsTypeError` |
| **1 op = N backend、プロファイルで選択** | `gauss` 1 つに numpy と cv2 の実装。`with profile("industrial")` で切替 |
| **産業プロファイルは黙って劣化しない** | ネイティブ実装が無い op は `FsBackendError`(**fail-closed**)。「配布したら遅かった」を構造的に防ぐ |
| **ネイティブはオラクルと一致することを証明してから採用** | 差分テスト: gauss(3 σ)/ connection / region_features / select_shape が numpy 実装と一致 |
| ObjectSet はマスクを作らない | ラベル画像 1 枚 + id 列。`select_shape` は id フィルタのみでラベル画像を共有(コピーなし) |

**性能(同じスクリプト・同じ結果・プロファイル切替のみ)**:

| | studio(numpy オラクル) | **industrial(native)** | 倍率 |
|---|---:|---:|---:|
| 1024x1024 / 50 blob | 58.6 ms | **5.42 ms** | 10.8x |
| 2048x2048 / 200 blob | 240.2 ms | **16.94 ms** | 14.2x |

**PoC 構築中に見つかった設計要件(実測駆動)**: 最初の版は 4 MP で 41.7 ms だった。
原因は **API 形状が連結成分パスを 3 回走らせていた**こと(`connection` で 1 回、`select_shape` の測定で 2 回目、
最終取得で 3 回目)。→ **`ObjectSet` は測定済み特徴量を保持して運ぶ**ことを要件化し(R1 に反映)、
41.7 → 16.9 ms。**「オブジェクトモデルは形だけでなく、測定結果の持ち回りまで含めて設計する」**という学び。

**正直な残差**: 手書き cv2 の 10.8 ms に対し PoC は 16.9 ms。差の原因は特定済み
(`threshold` が u8 上で numpy 比較 2 回 + AND、`connection` で uint8 への変換コピー)。
アーキテクチャの限界ではなく、実装の詰めしろ。

---

## 2. 確定判断

### 判断 1 — Python で進める。ただし「L1 を numpy/scipy の唯一実装に固定しない」ことを条件とする

実測が示す優先順位は **型・意味論 → オブジェクトモデル → 画素カーネル → 言語の実行方式**。
言語の実行方式は**最も影響が小さい**。∴ 言語処理系・IDE・進化エンジンは Python のままで正しい。
**争点は L1 だけ**であり、その解は「言語を替える」ではなく「**L1 の契約をバックエンド差し替え可能に切る**」。

### 判断 2 — 実行モデルは VM 一本。codegen による配布はやらない

MVTec が本番でインタプリタを出荷している(§1.3)ことと、言語層の税がゼロである実測(§1.4)から、
**二モード(VM + compile)は要件ではない**。同じ VM を Studio と Runtime の両方で使う。
codegen は将来の任意最適化であって、設計の柱にしない。→ 意味論の二重保守という最大の負債を回避。

### 判断 3 — Path A / Path B の二者択一は誤った設問だった。**A の実装 + B の規律**を採る

- **Path A(Python-native IDE)を「製品の実行モデル」にしてはいけない**(Codex 指摘・確信度高):
  任意 Python を顧客の実行契約に入れた瞬間、決定性・静的検査・互換性・ライセンス調査・サポート範囲が爆発する。
- **Path B(独自 DSL)を「HALCON 忠実度のため」に採るのではない**。
  採る理由は **「実行契約を小さく閉じるため」** — 顧客資産が依存してよい意味論を、私が完全に列挙できる大きさに保つ。
- ∴ **独自 DSL(Path B の言語)+ Python 実装の VM(Path A の実装コスト)**。

### 判断 4 — Studio(設計時)と Runtime(配布)を別プロファイルにする

コールドスタート 1.8 s、フットプリント 375 MB vs 5 GB、決定論要件 — **3 つとも同時にこれで解ける**。
- **Fullseye Studio** = Python 全部入り。650 op、進化エンジン、ウォッチ IDE、torch/PySide6 可。
- **Fullseye Runtime** = 限定 op プロファイル + ネイティブカーネル + 決定論プロファイル。
  torch/PySide6/pip/REPL を**含まない**。常駐。顧客 PC に Python をインストールさせない閉じたイメージ。

### 判断 5 — 撤退不能点は実装言語ではなく「公開した意味論」。ゆえに**今固定すべきは契約だけ**

Codex の指摘(確信度高)を実測が裏書きした:
> 本当の撤退不能点は、顧客が保存したプロジェクトとプラグインが、あなたの実行意味論に依存し始めた時。
> 製造業では「移行ツールを出した」では済まず、**以前と同じ判定になる証明**を要求される。

§1.6 の欠陥 5 件は、まさに「Python の意味論がなし崩しに言語仕様になっている」状態。
**これを出荷する前に閉じることが、本プロジェクト最大の一手。**

---

## 3. 要件定義

### 3.1 いま固定する契約(= 撤退不能点を管理下に置く)

**R1. 型モデル(iconic / control を厳密に分離し、sort は「運ぶ」— 推測しない)**
- `FImage(pixels, dtype, value_range, domain: Region)` — **値域を型が持つ**(欠陥 2 の根治)。
  `domain` は HALCON 忠実(既定=全面、`reduce_domain`/`full_domain`/`get_domain`)。
- `Region` / `XLD` / `ObjectSet(label_image, ids)` / `handle`(不透明)を**別クラス**として定義。
- `Tuple` = HALCON 準拠の異種混在タプル(int/real/string、スカラ=長さ 1、要素ごとブロードキャスト)。
  **`+` は数値タプル同士なら要素和**(欠陥 3 の根治)。連結は別構文 `[t1, t2]`。
- `Vector`(型付き多次元コンテナ)/ `FContainer` 群(list/map/set/stack/queue = **Fullseye 拡張と正直にラベル**)。

**R2. 演算子契約 `LanguageOperatorSpec`(C ABI に落とせる形だけを許す)**
- `(name, in_iconic, out_iconic, in_control[Param(name,type,unit)], out_control, errors, invoke)`。
- 表現できてよいのは **スカラ / 配列 / 不透明ハンドル / エラーコード** のみ。
  **Python 固有(任意 dict、任意 class、Python 例外、duck typing、ndarray view の alias 挙動)を公開仕様にしない。**
- **進化用の正規化ノブ(a/b ∈ [0,1])と言語の実引数(sigma=1.5)は別契約**に保つ。
- **★1 op = N バックエンド**。`gaussian` は 1 つの op であり、実装が numpy / cv2 / native と複数ある形にする
  (現状の `gaussian` と `cv_gaussian` が別 op という構造を解消)。

**R3. 意味論の禁止事項(「黙って誤答しない」の明文化)**
- iconic の**暗黙真偽化を禁止**(`if (Region)` は型エラー。`if (|Objects| > 0)` と書かせる)。
- iconic の要素比較を条件に使うことを**禁止**(明示的な reduction を要求)。
- 値域・sort を**内容から推測しない**。
- **未実装機能は必ず構文/型エラー**。「見た目だけ言語」を作らない。
- 測定の multi-output(`area_center → Area, Row, Column`)を正式サポート。空領域/NaN は定義済み例外か空 tuple。

**R4. 決定論と設備との協調(Runtime プロファイル)**
- **init フェーズと cycle フェーズを分離**。モデルロード・メモリ確保・式コンパイルは init で完了。
- cycle 中の **import / ファイル探索 / ネットワーク / 動的コード生成を禁止**(静的に検査する)。
- 画像バッファは pool 化して寿命を明示管理。
- **deadline を第一級**にし、PLC へは OK/NG に加えて **`ERROR` と `TIMEOUT` を返す**。
  「Python をハードリアルタイムにする」のではなく「**deadline を破った Python を設備が安全に扱える**」設計にする。
- Runtime は**常駐**(トリガ毎のプロセス起動を禁止。実測 1.8 s より)。
- Runtime プロファイルは **lazy import 規律**、torch/kornia/PySide6 を含まない。

**R5. 版管理と再現性**
- **IR version** / プロジェクト保存形式 / スキーマ version。migration は暗黙実行せず、変換後の再検証を要求。
- **golden image + 期待出力**の互換性テスト形式を今決める(= 顧客に「以前と同じ判定」を証明する手段)。
- Runtime build ID を判定結果とログに記録。Python patch version・wheel の hash まで固定。

### 3.2 まだ固定しないもの(意図的に自由を残す)

- VM が Python 実装か native 実装か
- 各 op の中身が numpy か C か Rust か(**R2 の契約さえ守れば差し替え可能**)
- codegen の有無
- Studio 内部のクラス構造 / PySide6 の画面構成
- Rust か C++ か(既存 `imgops.c` は捨てず C ABI の後ろに置く)

### 3.3 非機能要件(製造業。§1.2 の「弾かれる条件」を裏返したもの)

| # | 要件 | 受入基準 |
|---|---|---|
| N1 | サイクルタイム | 対象構成で **最悪値**(p99.9 と連続 N 回の max)を提示できること。平均は受入根拠にしない |
| N2 | 連続運転 | 長時間試験(メモリ増加・ハンドルリーク・カメラ再接続・復旧)の結果を出せること |
| N3 | オフライン復元 | インストーラ・wheel・ネイティブ DLL・ドライバ・ライセンス・モデルを完全保存 |
| N4 | SBOM / ライセンス | 第三者ライセンス一覧・GPL 混入なし・Qt/PySide の条件を明示(**要法務確認**)。★下記の cv2 実態を織り込むこと |
| N5 | サポート性 | 現地には安定エラーコード、詳細ログに元例外・op ID・入力 shape・プロジェクト hash。サポート bundle を 1 操作で採取 |
| N6 | 安全 | 安全機能は**担わない**(PLC/安全 PLC 側)。非安全系の検査判定に限定することを設計制約として明記 |
| N7 | 事業継続 | 一人ベンダーのリスクに対し、ソースエスクロー / 仕様書とテスト資産の整備で応える(技術で消せないと正直に認める) |

**★ N4 の実態(一次情報で確認、2026-08-15)** — 「cv2 = Apache-2.0 だから安全」は**誤り**:

| 構成要素 | ライセンス | 含意 |
|---|---|---|
| OpenCV 本体 | Apache 2.0 | 問題なし |
| `opencv-python` のパッケージングスクリプト | MIT | 問題なし |
| **全 wheel が同梱する FFmpeg** | **LGPLv2.1** | **再リンク可能性の提供義務が残る** |
| 非 headless の **Linux** wheel が同梱する Qt5 | LGPLv3 | Runtime では回避すべき |

→ **要件**: Runtime は `opencv-python-headless` を使う(Qt5 LGPLv3 を排除)。
  それでも **FFmpeg の LGPL は残る**ので、(i) 動的リンクのまま再リンク手段を提供するか、
  (ii) **FFmpeg 無しで OpenCV を自前ビルド**して完全に切るか、を増分 4 までに決める。
  Fullseye は動画 I/O を Runtime で必要としない見込みなので **(ii) が本命**。

---

## 4. 基本設計

### 4.1 二プロファイル

```
┌──────────────────────────────┐        ┌──────────────────────────────┐
│ Fullseye Studio (設計時)      │        │ Fullseye Runtime (配布)       │
│ ─────────────────            │        │ ─────────────────            │
│ L3 ウォッチ IDE (PySide6)     │        │ (GUI なし・常駐・headless)    │
│ L2 Fullseye Script VM  ←─── 同一 VM ───→ L2 Fullseye Script VM         │
│ L1 全 650 op / numpy 実装      │        │ L1 限定プロファイル / native   │
│ + 進化エンジン + holdout       │        │ + init/cycle 分離 + deadline  │
│ + torch / kornia (研究用)      │        │ + PLC state machine           │
│ ~5 GB                        │        │ **~375 MB / Python 非公開**    │
└──────────────────────────────┘        └──────────────────────────────┘
              │                                        ▲
              └── 同じ .fsh スクリプト + 同じ IR version ─┘
                  差分は「どのバックエンドが選ばれるか」だけ
```

**同じスクリプトが両方で走り、結果が一致することを差分テストで保証する**(§4.5)。

### 4.2 3 層 + バックエンド選択(R2 の中核)

```
L3 Studio IDE      … エディタ / step / breakpoint / ★ウォッチ(型別レンダラ登録制)
L2 Fullseye Script … lexer→parser→typed AST→(将来 bytecode)→VM
                     ★ロジックを持たない。L1 を LanguageOperatorSpec 経由で呼ぶだけ
L1 Fullseye Lib    … 1 op = N backend。profile("studio"|"industrial") で選択
                     numpy 実装 = 常に存在(= 正解オラクル)
                     native 実装 = 任意(cv2 / C / Rust)。差分テストで等価性を証明したものだけ有効
```

**`profile` の意味**: `industrial` プロファイルは「**native 実装が存在し、差分テストに合格した op のみ**」を公開する。
存在しない op を使ったスクリプトは **Runtime へ配布しようとした時点でエラー**(実行時に静かに遅くならない)。

### 4.3 実行モデル — VM 一本(判断 2)

- IDE も Runtime も**同じ VM**。statement 境界で `ExecutionEvent(span, changed_vars, ...)` を発火。
- Studio ではそれをウォッチ/変数窓が受ける。Runtime では**発火自体を無効化**(deadline 保護)。
- bytecode VM 化は**やる。ただし動機は速度ではなくデバッグ体験**(step/breakpoint/source span)。
  実測上サイクルタイムの動機は無い、と正直に記録する。

### 4.4 ウォッチモデル(§4 of FSCRIPT_LANGUAGE.md を継承)

型別レンダラ登録制(`register_watch_renderer`)。control / image(+domain) / region / xld /
domain(ROI) / objectset / handle / vector。**A/B どちらの Path でも再利用できる核**という当初の判断は正しく、維持する。

### 4.5 ネイティブ化の段階と、その検証(★既存資産の再利用)

**TRIZ 原理 #26(コピー)**: **Python 実装を「実行系」から「正解オラクル」へ格下げする。**

```
numpy 実装 (常に存在)  ──┐
                        ├─→ difftest.py: holdout 入力上で max|diff| < tol を要求
native 実装 (任意)    ──┘   不一致 or 未カバーなら industrial プロファイルに載せない(正直に SKIP)
```

`difftest.py` は既にこの構造を実装済み。**新規開発ではなく拡張**。
現状カバレッジは 8/650 op(1.2%)、かつ region/blob 系ゼロ = **実測で 21 倍差が出た側が未着手**。
→ **産業プロファイルの最初の目標は「op を増やす」ではなく「頻出 20〜40 op に native 実装 + 差分テストを付ける」**。
  (Codex も同結論: 「526 演算を先に全部移植するのでなく、装置案件頻出 20〜40 演算 + 取得 + 幾何 + 計測 + 通信で
   最初の産業 Runtime を成立させる方がよい。購入判断に効くのは op 数より再現性・デバッグ・レシピ・PLC 接続・ログ・復旧」)

**native の選択順**: ① **cv2 で足りるものは cv2**(実測済・即効)→
② 足りないもののみ C(既存 `imgops.c` を C ABI の後ろへ)→ ③ 本当に必要になったら Rust(単一コードで .dll/.so)。
**先回りして Rust コアを書き始めない**(市場検証前に数年を投じるのが Path C の致命傷)。

### 4.6 設備との接続

- 能力制限 builtin のみ(`acquire` / `comm` / `device`)。任意 Python を公開しない。
- opaque handle + `on_error`/`finally` 自動 close、単調時計 deadline、simulation backend、
  動作範囲/速度/出力 pin の allowlist、Studio 初回 arm 確認。
- PLC 側インターフェースは **state machine + watchdog**。`READY` 成立条件を PLC から問い合わせ可能に。
- 画像 worker と device I/O worker を分離。VM は逐次意味論を保つ。

---

## 5. 増分計画

| 増分 | 内容 | 完了条件(falsifiable) |
|---|---|---|
| **1. 型と意味論を閉じる** | `fslib.py` へ L1 分離 / `FImage`(値域+domain)/ `Tuple` / `Region` / `ObjectSet` をクラス化 / **欠陥 2〜5 を修正**(xfail → pass)/ `for Obj in Objects` 実装 | `tests/test_fscript.py` の 5 xfail が全て pass。full suite 緑 |
| **2. バックエンド契約 + 産業プロファイル** | `LanguageOperatorSpec` / 1 op = N backend / `profile("industrial")` / 頻出 20〜40 op に cv2 backend + `difftest` 拡張 | 4 MP 検査が **industrial プロファイルで p99.9 < 20 ms**、numpy 実装との差分テスト合格 |
| **3. bytecode VM + ウォッチ** | source span 第一級 / `ExecutionEvent` / Studio ウォッチパネル(型別レンダラ)/ breakpoint / step | 実スクリプトを step 実行しながら image/region/domain/objectset をウォッチできる |
| **4. Runtime プロファイル** | headless 常駐 / init-cycle 分離 / deadline + ERROR/TIMEOUT / PLC state machine / lazy import / 閉じた配布イメージ | Python 未インストール PC で起動し、連続 N 時間の試験レポートを出せる |
| **5. 必要になった op のみ native/Rust** | 実案件で計測されたホットパスのみ | 差分テスト合格 + ベンチで妥当性確認できたものだけ採用 |

**増分 1 と 2 の順序は入れ替えない。** 意味論が間違ったまま速くしても、間違いが速くなるだけ。

---

## 6. 撤退不能点と kill criteria

### 出荷した瞬間に撤退不能になるもの(= 増分 1〜2 で確定させ、以後は版管理下でしか変えない)
1. Fullseye Script の文法と意味論
2. FImage / Region / XLD / ObjectSet / Tuple / handle のデータモデルと**値域規約**
3. 演算子名・引数順・既定値・**エラー動作**
4. プロジェクト保存形式と IR version
5. ユーザープラグイン API
6. 数値結果の互換性保証(= golden image 回帰の形式)

### kill criteria(この設計を捨てるべき観測)
- 増分 2 で、頻出 20 op のうち **半分以上に native 実装の道が無い**(cv2 にも無く C 実装も現実的でない)と判明した場合
  → L1 を最初から native で書く判断(Path C)に切り替える
- 実案件で **industrial プロファイルの p99.9 が要求の 2 倍を超える**
  → プロセス分離(Path D)か、対象領域を「設計ツール」に絞る判断
- 顧客が実際に要求するのが「Fullseye で組んだものを **C#/C++ アプリに組み込む**」形だった場合
  → codegen ではなく **C ABI の Runtime DLL + 薄い .NET ラッパ**を優先(HALCON と同型)

---

## 7. 正直な限界

- **実測は開発機 1 台・短時間のみ**。長時間安定性 / 実カメラ同時実行 / OS 由来ジッタ / 産業 PC(低クロック)
  / マルチカメラ(GIL 下)は未測定。`docs/FSCRIPT_MEASUREMENTS.md` §6 に列挙。
- **ライセンスは法務確認が必要**(Qt/PySide の条件、GPL 混入、opencv の依存)。本書は法的助言ではない。
- **一人ベンダーの事業継続性リスクは技術で消せない**。ソースエスクロー・仕様書・テスト資産で応えるしかない。
- 本書の産業界事実は **Codex(web 一次資料つき)+ 私による MVTec 公式ページの再確認**に基づく。
  Cognex / Keyence / OMRON の内部実装言語は公開されておらず「不明」のまま。
