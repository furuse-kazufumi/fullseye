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

**★敵対検証が潰した「Python 不利」論(いずれも Python 固有ではなかった)**:

| よく聞く反論 | 検証の結論 |
|---|---|
| Cognex / Keyence CV-X / OMRON FH に Python の入口が無い | **C++ / C# にも無い**。これらは専用 GUI・独自マクロ・専用コントローラであり、真の分岐は「専用コントローラを買うか PC ベースで作るか」= **言語選択と直交** |
| CPython は 5 年 EOL で装置寿命とズレる | **比較先の .NET の方が短い**(現行 .NET は LTS 3 年 / STS 2 年)。同じ論法なら C# の方がズレは大きい |
| Euresys 公式が「性能が要る箇所は C++/C# で書き直す前提」と明記 | **一次情報の誤読**。原文は *"programming a specific functionality in more runtime efficient languages such as C++/C# is still possible"* = **選択肢の提示**であって前提ではない |
| PySide6 の `QImage(numpy_buffer)` は use-after-free になる | **Qt が全言語に課している API 契約**。Qt 公式は C++ の同一コンストラクタにも同じ寿命要件を明記しており、Python 固有のコストではない |
| 凍結配布が 345 MB で C# の単一 exe(数十 MB)より 10-50 倍重い | 成果物の中身が違う。**345.9 MB の 94.9% は OpenCV / Qt / OpenBLAS などのネイティブバイナリで、CPython 本体は 2.8%**。同機能を C# で作れば同じネイティブを積む |

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

**既存資産 `difftest.py` の実態(★自己訂正)**:
当初本書は「Python 実装を正解オラクルとし C 実装を差分テストで検証する機構が既にあるので、
**ネイティブ移行の検証ハーネスは新規開発不要**」と書いた。**これは寛容すぎた。**
敵対検証の指摘を受けて一次確認した結果:

| 主張 | 実態 |
|---|---|
| 「差分テストの機構が実在」 | **考え方としては実在**(141 行)。Python 側は毎回走る |
| 「規模だけが未証明」 | **C 側は一度も実行されたことがない**。記録 6 件すべて `status: skipped`(理由 = 「champion が C ランタミムに無い op を使う」or「C ツールチェーンが無い」)。この機械に gcc/clang も無い |
| 「op 単位で検証できる」 | **できない**。比較単位は **champion パイプライン全体**であって op 個別ではない |
| 「合否判定がある」 | 許容差は `c_max < 1e-3` の**ハードコード 1 本**。op ごとの契約になっていない |

→ **正しい言い方**: 「Python をオラクルにする」**発想**は既存だが、
  **本設計が必要とする per-op 差分ゲートは存在しない**。
  ただし **本セッションの `tests/test_fslib.py` で、それが実際に動くことは実証した**
  (gauss 3σ / connection / region_features / select_shape が numpy 実装と一致、宣言された許容差つき)。
  → **ハーネスは「拡張」ではなく「新規」だが、PoC で成立は確認済み**(§1.7)。

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

### 1.6b ★★最重要 — 650 op レジストリは fail-open である(敵対検証の指摘から発見)

外部の敵対検証が「片方の依存を外すと op は登録されたまま黙って benign 値を返す」と指摘したので、コードで確認した。**事実だった。**

`backends.py` の `_safe` は**全 op** をこう包んでいる:

```python
def w(v, a, b):
    try:
        out = fn(v, a, b)
    except Exception:
        out = None                 # ← あらゆる例外を飲む
    return sanitize(out, v, out_sort)
```

`sanitize(None, ...)` は `fallback()` を呼び、**「宣言された sort として妥当な無害値」**を返す。
実測で確認:

| out_sort | 例外時に返る値 | 検査における意味 |
|---|---|---|
| `region` | **全ゼロの region** | **「欠陥ゼロ」** |
| `feature` | `0.0` | 測定値ゼロ |
| `image` | 入力をクリップしたもの | 処理されなかった画像 |

→ **本番検査で op が何らかの理由で例外を投げると(依存欠落・退化入力・バグ)、
パイプラインは黙って「欠陥なし」を返し、全数が OK 判定になる。**
製造検査として最悪の失敗様式であり、**判定そのものが fail-open** になっている。

**★ただしこれは進化エンジンには正しい設計**である(失敗候補は低スコアで淘汰されるべきで、
探索全体を落としてはいけない)。**同じ挙動が Runtime では致命的**というだけ。

→ **これが「Studio と Runtime は意味論を分けねばならない」の最も具体的な証拠**であり、
  §4.2 の `industrial` = fail-closed 設計の**必然性**を示す。
  要件 R4 に「**Runtime プロファイルは op の例外を決して飲まない**」を明記する(下記)。
  対比は `tests/test_fslib.py::test_the_evolution_registry_is_fail_open_and_fslib_must_not_be` で固定。

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

### 1.8 産業プロファイル候補 44 op の native カバレッジ = 44/44

増分 2 の kill criteria(「頻出 op の半分以上にネイティブの道が無ければ設計を捨てる」)を先に検証した。
実検査で頻出する 44 op を列挙し、OpenCV に対応関数が存在するかを確認 → **不足 0**。

> gauss / box / median / bilateral / sobel / laplace / canny / threshold / otsu / adaptive_threshold /
> dilation / erosion / opening・closing / connection+features / contours / contour_features /
> min_area_rect / fit_circle / fit_line / fit_ellipse / convex_hull / moments / hu_moments /
> match_template / warp_affine / warp_perspective / resize / remap / calibrate / solve_pnp /
> hough_lines / hough_circles / distance_transform / watershed / histogram / equalize / inrange /
> cvt_color / subpixel_corner / optical_flow / barcode / qrcode / phase_correlate / ecc_align

→ **産業プロファイルの到達に Rust/C の新規実装は不要**。Path C(最初からネイティブコア)を採る理由がさらに薄れる。

**★「名前があること」から「実際に動くこと」へ格上げ済み**: 代表 16 op を **4 MP(2048x2048)の実 u8 フレームで実行**し、
16/16 成功。p50(ms):

| op | ms | op | ms | op | ms |
|---|---:|---|---:|---|---:|
| GaussianBlur | 2.09 | connCompWithStats | 8.77 | distanceTransform | 6.59 |
| medianBlur | 6.58 | findContours | 2.64 | HoughLinesP | 12.52 |
| Canny | 3.93 | minAreaRect / fitEllipse / moments | ~0.01 | solvePnP | 0.03 |
| adaptiveThreshold | 8.99 | warpAffine | 2.46 | cornerSubPix | 0.01 |
| morphologyEx(open) | 1.43 | **matchTemplate** | **46.74** | | |

**★ `matchTemplate` が突出して遅い(46.7 ms)** — しかもこれは**回転・スケール不変ですらない NCC**。
つまり **マッチングは機能面で最も弱く、同時に最も高価**。
→ §1.8 の「差別化 3 領域」のうち **shape-based matching が最優先**であることが、数字でも裏付けられた。

**★ただし正直に区別すべきこと** — 問題は「ネイティブカーネルが無い」ことではなく
**「OpenCV のアルゴリズム集合 ≠ HALCON のアルゴリズム集合」**である。HALCON が高価な理由そのものが OpenCV に無い:

| HALCON の中核ツール | OpenCV の対応 | 実態 |
|---|---|---|
| **shape-based matching**(回転・スケール不変、サブピクセル、遮蔽耐性) | `matchTemplate` | **NCC テンプレートマッチのみ**。回転・スケール不変ではない = **別物** |
| **XLD サブピクセル輪郭 + 計測** | `findContours` | **画素レベル**。サブピクセル輪郭の当てはめ・計測は無い |
| **1D measure object**(`measure_pairs` 等のエッジ対計測) | — | 相当機能なし |

→ **含意(戦略)**: cv2 で「速い産業プロファイル」は**すぐ届く**。
  一方 **HALCON 級の差別化はこの 3 つ**にあり、そこは自前実装が要る。
  そしてそこは **Fullseye の進化エンジンが新規性を出せる可能性がある唯一の領域**でもある
  (op を 650 個並べることではなく、この 3 領域で「設計された」アルゴリズムを出すこと)。
  ロードマップ上は **増分 2 = cv2 で産業成立 → 増分 5 = 差別化 3 領域を自前実装**、と位置づける。

---

## 2. 確定判断

### 判断 1 — Python で進める。ただし「L1 を numpy/scipy の唯一実装に固定しない」ことを条件とする

実測が示す優先順位は **型・意味論 → オブジェクトモデル → 画素カーネル → 言語の実行方式**。
言語の実行方式は**最も影響が小さい**。∴ 言語処理系・IDE・進化エンジンは Python のままで正しい。
**争点は L1 だけ**であり、その解は「言語を替える」ではなく「**L1 の契約をバックエンド差し替え可能に切る**」。

### 判断 2 — 実行モデルは VM 一本。codegen による配布はやらない

MVTec が本番でインタプリタを出荷している(§1.3)ことと、言語層のコストが検出できない実測(§1.4)から、
**二モード(VM + compile)は要件ではない**。同じ VM を Studio と Runtime の両方で使う。
codegen は将来の任意最適化であって、設計の柱にしない。→ 意味論の二重保守という最大の負債を回避。

**★反例を無視していないこと**: 市場には両方のモデルが実在する。
**Zebra Aurora Vision Studio(旧 Adaptive Vision)は Studio から C++ コード/プロジェクトを生成する構成を持つ**
(配布は Executor/Runtime または生成アプリ)。つまり codegen 配布は「誰もやっていない」わけではない。
**それでも HALCON 型を選ぶ理由**は 3 つ:
(1) 一人開発で 650 op の意味論を 2 系統維持できない(Codex 指摘・確信度高)、
(2) 実測上 codegen の**性能動機が無い**(言語層のコストが検出できない)、
(3) ウォッチ/step という本製品の差別化が**生きた変数環境**を要求し、VM 側に重心がある。
→ 顧客が「C#/C++ アプリに組み込みたい」と実際に言ってきた場合は、codegen ではなく
**C ABI の Runtime DLL + 薄い .NET ラッパ**で応える(§6 kill criteria)。

### 判断 3 — Path A / Path B の二者択一は誤った設問だった。**A の実装 + B の規律**を採る

- **Path A(Python-native IDE)を「製品の実行モデル」にしてはいけない**(Codex 指摘・確信度高):
  任意 Python を顧客の実行契約に入れた瞬間、決定性・静的検査・互換性・ライセンス調査・サポート範囲が爆発する。
- **Path B(独自 DSL)を「HALCON 忠実度のため」に採るのではない**。
  採る理由は **「実行契約を小さく閉じるため」** — 顧客資産が依存してよい意味論を、私が完全に列挙できる大きさに保つ。
- ∴ **独自 DSL(Path B の言語)+ Python 実装の VM(Path A の実装コスト)**。

**検討したが採らなかった第 3 の案(正直に記録)= 制限付き Python サブセット**:
ユーザーが書くのは Python だが、`ast` で構文木を検査し、許可したノード種別・名前・呼び出しだけを通す方式。
利点 = パーサ/VM を自作しない、既存エディタとデバッガが使える、進化エンジンが生成しやすい。
**採らない理由**: (1) サンドボックス境界が漏れやすいことが広く知られている(属性アクセス・dunder 経由の脱出)、
(2) 何より **Python の意味論がそのまま公開仕様になる** — これは Codex が「最も危険」と名指しした撤退不能パターンそのもの
(§2 判断 5)、(3) ユーザーが方向性として HDevEngine 風の専用言語を既に決定している。
ただし **(1)(2) は「実行契約を小さく閉じる」という同じ目的を別手段で満たそうとしたもの**なので、
もし独自 DSL の保守負担が想定を超えた場合の**代替案として記録**しておく。

### 判断 4 — Studio(設計時)と Runtime(配布)を別プロファイルにする

コールドスタート、フットプリント、決定論要件 — **3 つとも同時にこれで解ける**。
実測で裏付け済み: **起動 1663 ms → 160 ms(10.4x)**、フットプリント 5 GB → 375 MB
(`fslib.py` が 650 op レジストリを import しない設計にした直接の理由)。
160 ms なら**ウォッチドッグによる復旧再起動が 0.2 秒**で終わる = 実運用に耐える。
- **Fullseye Studio** = Python 全部入り。650 op、進化エンジン、ウォッチ IDE、torch/PySide6 可。
- **Fullseye Runtime** = 限定 op プロファイル + ネイティブカーネル + 決定論プロファイル。
  torch/PySide6/pip/REPL を**含まない**。常駐。顧客 PC に Python をインストールさせない閉じたイメージ。

### 判断 5 — 撤退不能点は実装言語ではなく「公開した意味論」。ゆえに**今固定すべきは契約だけ**

Codex の指摘(確信度高)を実測が裏書きした:
> 本当の撤退不能点は、顧客が保存したプロジェクトとプラグインが、あなたの実行意味論に依存し始めた時。
> 製造業では「移行ツールを出した」では済まず、**以前と同じ判定になる証明**を要求される。

§1.6 の欠陥 5 件は、まさに「Python の意味論がなし崩しに言語仕様になっている」状態。
**これを出荷する前に閉じることが、本プロジェクト最大の一手。**

### 判断 6 — 「それでは OpenCV の薄いラッパでは?」への答え

本確定案に対する**最も強い反論**を自分で立てておく:

> Python + OpenCV で十分速いと証明したのなら、Fullseye の産業プロファイルは cv2 の 44 op に過ぎない。
> 顧客は無料の OpenCV を直接使えばよいのでは?

**答え: 売っているのは op ではない。** これは HALCON にもそのまま当てはまる反論であり
(HALCON の中身の多くも古典的アルゴリズムである)、それでも HALCON が高価に売れている理由が答えになる。
Codex も同じ結論を出している —
「**購入判断に効くのは op 数より、再現性・デバッグ・レシピ・PLC 接続・ログ・復旧**」。

Fullseye が売るもの、優先順:

1. **ライブウォッチ IDE** — image / region / **domain(ROI)** / XLD / ObjectSet / handle を、実行を止めて
   その場で見られること。OpenCV には無い。ここが `FSCRIPT_LANGUAGE.md` §4 の主戦場である理由。
2. **配布と保証のパッケージ** — 決定論プロファイル、init/cycle 分離、deadline と `ERROR`/`TIMEOUT`、
   常駐 Runtime(起動 160 ms)、閉じた配布イメージ、SBOM、**golden image 回帰による「以前と同じ判定」の証明**。
   OpenCV を直接使う顧客は、これを**自分で作る**ことになる。
3. **アルゴリズムを設計する AI**(進化エンジン + 正直な holdout ゲート)— これは競合に無い。
   ただし §1.8 のとおり、**差別化が効くのは shape-based matching / XLD サブピクセル / 1D measure の 3 領域**であって、
   op を 650 個並べることではない。
4. **op の網羅**は 4 番目。**製品価値の順位を op 数トップに置かない**ことを、ここで明示的に決める。

**含意(ロードマップへの反映)**: 増分 3(ウォッチ)と増分 4(Runtime)は「後回しの仕上げ」ではなく
**製品価値そのもの**。増分 2 で速度が出た時点で満足しない。

---

## 3. 要件定義

### 3.1 いま固定する契約(= 撤退不能点を管理下に置く)

**R1. 型モデル(iconic / control を厳密に分離し、sort は「運ぶ」— 推測しない)**
- `FImage(pixels, dtype, value_range, domain: Region)` — **値域を型が持つ**(欠陥 2 の根治)。
  `domain` は HALCON 忠実(既定=全面、`reduce_domain`/`full_domain`/`get_domain`)。
- `Region` / `XLD` / `ObjectSet(label_image, ids, **feats**)` / `handle`(不透明)を**別クラス**として定義。
- ★**Region の内部表現は将来 run-length encoding(RLE)に変えられるよう、API を表現非依存に切る**。
  HALCON の Region は RLE で格納されており(公式に `runlength_features` が run 数/バイト数を返す)、
  領域演算が **O(run 数)** で済む。現 PoC は密 bool マスク = **O(画素数)**。
  小さな ROI を多数扱う検査(HALCON が得意な形)では**この差が支配的**になる。
  → 増分 1 では密マスクのままでよいが、**`Region` の公開 API に `.mask` を露出させない**
  (`area()` / `bbox()` / 集合演算だけを見せる)ことで、後から RLE へ差し替え可能に保つ。
  ★`ObjectSet` は**測定済み特徴量を id 索引で保持して運ぶ**(§1.7 の実測: これが無いと同じ連結成分パスを
  3 回走らせて 2.5 倍遅くなる)。`select` は id フィルタのみでラベル画像と特徴量表を共有する。
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
- **★最優先: Runtime は op の例外を決して飲まない(fail-closed)。**
  現行 650 op レジストリは `backends._safe` が全例外を飲んで「sort として妥当な無害値」を返す
  = region なら**空 region = 欠陥ゼロ = 全数 OK 判定**(§1.6b)。
  進化エンジンにはこの挙動が必要だが、**Runtime に持ち込んではならない**。
  Runtime では op の失敗は `ERROR` として PLC へ上がり、判定は行われない。
- **init フェーズと cycle フェーズを分離**。モデルロード・メモリ確保・式コンパイルは init で完了。
- cycle 中の **import / ファイル探索 / ネットワーク / 動的コード生成を禁止**(静的に検査する)。
- 画像バッファは pool 化して寿命を明示管理。
- **deadline を第一級**にし、PLC へは OK/NG に加えて **`ERROR` と `TIMEOUT` を返す**。
  「Python をハードリアルタイムにする」のではなく「**deadline を破った Python を設備が安全に扱える**」設計にする。
- Runtime は**常駐**(トリガ毎のプロセス起動を禁止。実測 1.8 s より)。
- Runtime プロファイルは **lazy import 規律**、torch/kornia/PySide6 を含まない。
- ★**Windows のタイマ分解能を明示的に上げる**(`winmm.timeBeginPeriod(1)` を Runtime の生存期間中保持)。
  外部検証の実測では、これを保持しない 10 ms ループは GC を完全に無効化し一切確保しなくても
  **2500 サイクル中 10 回が 1 ms を超え、max 8.9 ms** に達した。**GC より OS のタイマ分解能の方が支配的**。
- ★**AV スキャンを配布要件として扱う**。凍結配布の**初回起動**は、除外設定の無い実機で **6〜7 秒**
  かかりうる(数百ファイル・数百 MB のスキャン)。**遅延 import では 1 ms も削れない**。
  → 対策は (1) 更新の粒度を下げる/差分配布、(2) 導入手順に AV 除外パスの設定を含める、
  (3) コード署名。**「起動が速い」を lazy import だけで達成したと主張しない。**

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
| **N8** | **脆弱性対応義務(EU 市場)** | **EU Cyber Resilience Act(Regulation (EU) 2024/2847)**。2024-12-10 発効、**Art.14 の報告義務が 2026-09-11 から適用**。自社製品に含まれる脆弱性が実際に悪用されていると知った時点で **24 時間以内**の報告義務。→ **「装置をネットから隔離してパッチを当てない、と顧客と合意する」という緩和策は EU 市場向けには使えない**。SBOM と依存の追跡が契約ではなく**法令上の要件**になる。**要法務確認**(本書は法的助言ではない) |
| **N9** | **CI と C ビルド系が存在しない** | 自分で一次確認: `.github` なし(git 管理下に 0 ファイル)、`CMakeLists.txt` / `Makefile` / `setup.py` なし = **CI も C 拡張のビルド系も無い**。ただし `pyproject.toml`(setuptools)は在り、**wheel ビルド自体は実績がある**(STATUS の隔離 venv 検証)。N3(オフライン復元)と N4(SBOM)、および増分 5 のネイティブ化には **CI と C ビルド系の新設が前提**になる |

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
┌───────────────────────────────┐      ┌───────────────────────────────┐
│ Fullseye Studio (設計時)       │      │ Fullseye Runtime (配布)        │
│ ──────────────────            │      │ ──────────────────            │
│ L3 ウォッチ IDE (PySide6)      │      │ GUI なし・常駐・headless        │
│ L2 Fullseye Script VM   ←── 同一 VM ──→ L2 Fullseye Script VM          │
│ L1 native 優先 / numpy 補完     │      │ L1 native のみ (fail-closed)   │
│ + 650 op 進化エンジン + holdout │      │ + init/cycle 分離 + deadline   │
│ + torch / kornia (研究用)       │      │ + PLC state machine            │
│ 起動 1663 ms / 約 5 GB          │      │ 起動 160 ms / 約 375 MB         │
│                               │      │ Python を顧客に公開しない        │
└───────────────────────────────┘      └───────────────────────────────┘
              │                                       ▲
              └── 同じ .fsh スクリプト + 同じ IR version ┘
                  差分は「native が無い op を許すか」だけ
```

**★重要**: Studio 側も **native を優先**する(numpy は native が無い op の補完のみ)。
「設計者が見たものがそのまま出荷される」ため(§4.2)。**同じスクリプトが両方で走り、
結果が一致することを差分テストで保証する**(§4.5)。

### 4.2 3 層 + バックエンド選択(R2 の中核)

```
L3 Studio IDE      … エディタ / step / breakpoint / ★ウォッチ(型別レンダラ登録制)
L2 Fullseye Script … lexer→parser→typed AST→(将来 bytecode)→VM
                     ★ロジックを持たない。L1 を LanguageOperatorSpec 経由で呼ぶだけ
L1 Fullseye Lib    … 1 op = N backend。profile("studio"|"industrial"|"reference") で選択
                     numpy 実装 = 常に存在(= 差分テストの正解オラクル)
                     native 実装 = 任意(cv2 / C / Rust)。差分テストで等価性を証明したものだけ有効
```

**`profile` の意味**(3 つ。★ここは設計上の要点なので厳密に):

| profile | バックエンド優先順 | 用途 |
|---|---|---|
| `studio` | **native → numpy** | 設計者が使う。**ラインで走るのと同じ実装**を見せる |
| `industrial` | **native のみ(fail-closed)** | 配布。native が無い op は `FsBackendError`。静かに遅くならない |
| `reference` | numpy のみ | **差分テストのオラクル専用**。設計者向けの既定ではない |

**★「設計者が見たものが、そのまま出荷される」**を最優先の制約とする。
`studio` を numpy(オラクル)にすると、**設計者は numpy の挙動で閾値を調整し、ラインでは native の挙動が走る**。
差分テストが差を有界化しても、判定境界ぎりぎりのレシピは反転しうる。
製造業は「移行ツールを出した」では済まず **「以前と同じ判定になる証明」**を要求する(§2 判断 5)ので、
**設計時と実行時で実装を分けてはいけない**。
∴ numpy 実装の役割は**テスト時のオラクル**であって、設計者の既定ではない。
(PoC ではこれをテストで固定している: `studio` と `industrial` が同一バイト列を返すこと。)

`industrial` が fail-closed であることの意味: native 実装が無い op を使ったスクリプトは
**Runtime へ配布しようとした時点でエラー**になる。「配布したら遅かった」を構造的に防ぐ。

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

**★正直な現況**(§1.5 の自己訂正を反映): `difftest.py` はこの**発想**を実装しているが、
**C 側は一度も走ったことがなく**(記録 6/6 skipped)、比較単位も op ではなく champion パイプライン全体。
→ **per-op 差分ゲートは新規に作る**。ただし **`tests/test_fslib.py` で実際に動くことは実証済み**なので、
  設計リスクではなく実装作業である。
C ランタイムのカバレッジは 8/650 op(1.2%)、かつ region/blob 系ゼロ = **実測で 7.8〜21 倍差が出た側が未着手**。
→ **産業プロファイルの最初の目標は「op を増やす」ではなく「頻出 20〜40 op に native 実装 + 差分テストを付ける」**。
  (Codex も同結論: 「526 演算を先に全部移植するのでなく、装置案件頻出 20〜40 演算 + 取得 + 幾何 + 計測 + 通信で
   最初の産業 Runtime を成立させる方がよい。購入判断に効くのは op 数より再現性・デバッグ・レシピ・PLC 接続・ログ・復旧」)

**native の選択順**: ① **cv2 で足りるものは cv2**(実測済・即効)→
② 足りないもののみ C(既存 `imgops.c` を C ABI の後ろへ)→ ③ 本当に必要になったら Rust(単一コードで .dll/.so)。
**先回りして Rust コアを書き始めない**(市場検証前に数年を投じるのが Path C の致命傷)。

### 4.6 進化エンジン(650 op)と L1(言語の語彙)の関係 — op を 2 系統にしない

この 2 つは**重なるが同一ではない**。放置すると「op が 2 系統ある」状態になるので、役割を明示的に分ける:

| | `api.RT`(650 op レジストリ) | `fslib` L1(言語の語彙) |
|---|---|---|
| 引数 | **正規化ノブ** a/b ∈ [0,1] | **意味のある実引数**(sigma=1.5, 閾値=0.5) |
| 目的 | **進化の探索空間**(固定長ゲノム・holdout ゲート) | **人間が読み書きする語彙**(型・単位・エラー) |
| 実装 | numpy(研究用に多様性を最大化) | 1 op = N backend(native 必須の profile あり) |
| 数 | 多いほど良い(654 → 増やす) | **少ないほど良い**(契約が閉じる) |

**接続の規約(★これが「進化の北極星」を壊さないための要)**:

1. **進化は `api.RT` の上で回る**(現状のまま。654 op、正規化ノブ、locked holdout)。北極星は不変。
2. 進化が発見した champion は **既存の `champion_to_macro.py` で macro DNA op に凝縮**される(実装済みの機構)。
3. **macro op が言語の語彙になるには 2 つの関門を通る**:
   (a) `LanguageOperatorSpec` を与える(実引数・型・エラーを人間向けに定義)、
   (b) **industrial プロファイルに載せるなら native backend + 差分テスト合格**。
4. **つまり「進化が op を増やす」ことと「言語の契約が膨らむ」ことは切り離される。**
   650 op はいくら増えてもよい。言語の語彙と産業プロファイルは、通した分だけ増える。

これにより、**§3.1 R2 の「正規化ノブと実引数を別契約に保つ」が構造として実現される**。
`EvolvableBlock`(`FSCRIPT_LANGUAGE.md` §5)は、言語の中から (1) の探索を呼ぶための窓口として維持する。

### 4.7 設備との接続

- 能力制限 builtin のみ(`acquire` / `comm` / `device`)。任意 Python を公開しない。
- opaque handle + `on_error`/`finally` 自動 close、単調時計 deadline、simulation backend、
  動作範囲/速度/出力 pin の allowlist、Studio 初回 arm 確認。
- PLC 側インターフェースは **state machine + watchdog**。`READY` 成立条件を PLC から問い合わせ可能に。
- 画像 worker と device I/O worker を分離。VM は逐次意味論を保つ。

---

## 5. 増分計画

| 増分 | 内容 | 完了条件(falsifiable) |
|---|---|---|
| **0. 種(★完了)** | `fslib.py` = 型モデル(FImage/Region/ObjectSet)+ プロファイル + 1 op = N backend + 差分テスト。5 op で実証 | **済**: `tests/test_fslib.py` 18 passed、4 MP で 14.2x(§1.7) |
| **1. 型と意味論を閉じる** | `fscript` を `fslib` の上に載せ替え / `Tuple`(HALCON 準拠)/ `domain` の実効化 / **欠陥 2〜5 を修正**(xfail → pass)/ `for Obj in Objects` 実装 | `tests/test_fscript.py` の 5 xfail が全て pass。full suite 緑 |
| **2. 契約の一般化 + 産業プロファイル** | `LanguageOperatorSpec` 化 / 頻出 20〜40 op へ backend を拡張 / 既存 `difftest.py` と統合 / 配布時に不足 op を静的検出 | 4 MP 検査が **industrial プロファイルで p99.9 < 20 ms**、全 op が差分テスト合格 |
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
