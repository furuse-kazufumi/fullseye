# Studio の Program 欄: 従来のモードと Python のモード

2026-11-12 第 1 段(設計 + Qt に依らない実行系 + 試験)。実装は `studio_program.py`(実行系)・
`fullseye/studio_prelude.py`(前置き)・`defs_io.py`(定義ファイルの層)・`engine.py` の末尾
(`PipelineFile` / `load_pipeline`)。試験は `tests/test_studio_program_2026_11_12.py`。

## 0. 最初の例: 従来のモードで組んで保存 → Python のモードで読み、判定と繰り返しだけ Python で書く

従来のモード(段の列とつまみ)で検査の前処理を組み、File ▸ Save で `inspect.json` に保存する。
Python のモードでは、その段の列をそのまま読み、判定と繰り返しだけを書く:

```python
# python
prep = load_pipeline("inspect.json")      # 従来のモードで保存した物(段は記録に「inspect の 2 段目」と載る)
mask = prep(img)
n = blob_count(mask)
if n > 20:                                # 粒が多すぎる = 汚れ。強くぼかしてから数え直す
    img = median(img, 0.8)
    mask = prep(img)
k = 0
while blob_count(mask) > 5 and k < 4:     # 小さな粒が消えるまで開く
    mask = opening(mask, 0.3)
    k += 1
show(mask)
```

同じ文面は、Studio の外の普通の Python でも動く(§11 の書き出し)。パイプラインのファイルは
Python からも `fs.load_pipeline("inspect.json")` で読める(§9)。

## 1. 位置づけ

- **併用が前提**。従来のモード(段の列が正本、HDevelop 風の Program、つまみ・「+」・並べ比べ)は
  恒久的に残す。Python のモードは置き換えではなく横に足す。従来のモードを廃止することは計画に入れない。
- **起動時の既定のモードは Python**(ユーザーの決定、2026-11-12 夜。`STUDIO_AS_PYTHON_IDE.md` の「決定」)。
  Python のモードが画面に繋がった版から。ただし、パイプラインのファイルを開いたとき・前回パイプラインで
  終えたプロジェクトはパイプラインで開く。設定で「Python / パイプライン / 前回のまま」を選べる。
  画面の既定の切り替えは main が UI を繋ぐときに行う(この段では実行系だけ)。
- **起動時の例**: `studio_program.STARTER_PROGRAM`(13 行。同梱の `coins` の画像を読み、op 4 つ・変数・if 1 つ。
  実行すると絵と段の列が出る)。Studio の画像があればそれを使う。試験が `run_program` で通ることを確かめる。
- Python のモードは**本物の Python**として実行する(ユーザーの判断、2026-11-12「Python を直接使っても
  良いくらいだ」)。部分集合の評価器は作らない。構文の制限も付けない(import・関数定義・numpy も使える)。
  そのかわり、ファイル・プロジェクト・MCP から来たプログラムは確認するまで実行しない(§5)。
- HALCON の「入力と出力を引数で渡す」形へ言語全体を変えることはしない。op の関数は**値を返す**
  (`img = gaussian(img, 0.4)`)。入力を省くと「今の流れ」に掛ける(§3)ので、Fullseye の
  「1 本の流れ + つまみ」もそのまま書ける。
- 参照した一次情報: Python `ast`(https://docs.python.org/3.11/library/ast.html)、
  `sys.settrace`(https://docs.python.org/3.11/library/sys.html#sys.settrace)、
  `compile` / `exec`(https://docs.python.org/3.11/library/functions.html#compile)。
  HDevelop の制御構文と代入(`:=`、タプル)は MVTec の HDevelop User's Guide の「HDevelop Language」の章
  (入口 https://www.mvtec.com/products/halcon/documentation)が正本だが、記法を Python に決めたので
  この段では読み比べていない(従来のモードの記法は今の解析器が正本で、変えない)。

### 1.1 混乱しない作り(`STUDIO_UX_RULES.md` §9 への答え)

- **語を 1 つの意味に固定する**(正本は別の担当の `studio_project.py` の種類の表。入ったらそこから引く):

  | 語 | 意味 | ファイル |
  |---|---|---|
  | パイプライン | op の段の列(`[op, a, b]` の並び)。従来のモードで組む物 | `pipelines/*.json`(`fullseye_kind: pipeline`) |
  | プログラム | Program 欄の文面。記法は「パイプラインの記法」(従来、HDevelop 風)か「Python」 | `programs/`(この段では保存の形を決めない) |
  | パラメータ | op のつまみ `a` / `b`(と、将来の名前つきの束 `params`) | `params/`(別の便) |
  | レシピ | **同梱のパイプライン**(種類は pipeline。別の概念にしない) | recipes.py |

  「設定」「定義」「構成」はこの 4 語の代わりに使わない。`definition`(定義ファイル)は JSON の封筒の層の
  名前(§9)で、画面の語にはしない。
- **どちらのモードにいるかは 1 か所に常に出す**: Program 欄の上の切り替え(「パイプライン / Python」)。
  文面の 1 行目の印(`# python`)と同期し、切り替えたときに何が変わるか(「段の列が正本 ⇄ 文面が正本」)を
  1 行で言う(§13)。
- **正本はどちらか**:
  - パイプラインのモード: **段の列が正本**、Program 欄はその写し(今の Studio のまま。未適用の編集は
    「● unapplied edits」で知らせる)。
  - Python のモード: **文面が正本**、段の列は**実行の記録**(読み取り専用。段の欄の題に「記録」と出す)。
  - ずれたら言う: 文面を直したが走っていない → 段の欄に「記録は古い(行 N 以降が変わった)」。
    Python のプログラムが `current_pipeline()` を使っていて、パイプラインの段を直した → 同じ印。
    黙ってどちらかを採らない。

## 2. 記法の見分け(`detect_syntax`)

1. 最初の空でない行が `# python` / `# hdevelop`(`# fullseye: python` も可)なら、それに従う。
2. 行ごとに印を探す。HDevelop だけの印: `*` のコメント(`*a, b = x` の展開は除く)、`endif` /
   `endfor` / `endwhile`、`:=`、`:` の無い `if` / `elseif` / `while` / `for`、`:` の無い `else`、
   既知の op 名に空白と引数が続く短い呼び方(`gaussian 0.4 0.5`)。Python だけの印: `:` で終わる
   `if` / `elif` / `while` / `for` / `def` / `class` / `with` / `try`、`else:`、`x = …` の代入、`import`。
   HDevelop の印が付いた行は Python の印に数えない。
3. 両方あれば**誤り**(混在は不可): 「line 4: HDevelop-style 'end…' keyword and line 1: Python-style
   'x = …' assignment are mixed」。HDevelop の印だけなら従来のモード。
4. 印が無ければ `ast.parse`。通って、文が全部「op 名(定数…)」か「op 名」だけなら従来のモード
   (`gaussian (0.4, 0.5)` はどちらで読んでも同じ段の列)。それ以外で通れば Python。通らなければ、
   Python の印があれば Python(構文の誤りを行番号つきで出す)、無ければ従来のモード。

`* note` や素の `endif` は Python としても構文が通ってしまう(前者は `*note` の式、後者は名前の文)。
これは既存の試験の文面を集めた突き合わせ(§12)で見つかり、行の印を先に見る形にした。

## 3. 前置き(prelude)と op の呼び方

`from fullseye.studio_prelude import *` で次が入る(Studio の中でも同じ名前):

| 名前 | 意味 |
|---|---|
| op 名の関数(964 本) | `gaussian(x, a, b)`。入力 → つまみの順。`a=` / `b=` の名前でも可。省いたつまみは 0.5 |
| `op("名前", x, a, b)` | 名前で呼ぶ逃げ道(組み込み名・予約語と衝突する op、名前を変数で持つとき) |
| `img` / `image` | 入力の画像(書き出したスクリプトでは `studio_input()` が入れる)。読み取り専用 |
| `show(x)` | x を最後に画面へ出す値にする(最後の `show` が勝つ) |
| `pipeline` / `current_pipeline` / `load_pipeline` | 段の列をひとまとまりで扱う(§8) |
| `np` / `fs` | numpy と fullseye |
| `dev_*` / `disp_*` / `set_system` | 表示の指示。Python のモードでは記録するだけ(`ProgramResult.directives`) |

- **入力と「今の流れ」**: 位置引数の先頭から、数でない物が入力、最初の数からがつまみ(数の後に数でない物が
  来たら誤り)。入力を 1 つも渡さないと「今の流れ」に掛ける。今の流れ = **最後に画像・領域などを返した
  op の結果**(代入したかどうかに依らない。最初は入力)。2 入力の op(`sub_image(a, b)` など n-ary 17 本)は
  入力を省けない。
- **測るだけの op**: 出力の sort が `feature` / `match` の op は流れを変えず、値だけを返す
  (`n = blob_count(mask)` は float)。それ以外(image / region / contour / points …)は流れを進める。
- **最後に見せる値**: `show()` を呼んだら最後の `show` の値。呼ばなければ、最後に流れを進めた op の結果。
  op を 1 つも呼ばなければ入力。どれかは `ProgramResult.output_source`(`"show line 9"` /
  `"last op line 6"` / `"input"`)に出る。
- **つまみ**: 有限の数(bool は不可)。0..1 の外は丸めて、従来と同じ文で行番号つきで知らせる
  (`line 2: gaussian a=9 → 1`)。NaN / inf は行番号つきの誤り。
- **op の出力は読み取り専用**(メモ化の安全のため、§6)。書き換えたいときは `x = np.array(y)` で写す。
  558 本の画像 op に読み取り専用の入力を渡して壊れる op は 0 本だった(実測)。万一 op が入力へ書けば、
  書ける写しで計算し直す。
- **名前の衝突**(`prelude_collisions`): Python の予約語・ソフト予約語(`match` など)、組み込み名
  (`min` `max` `abs` `round` …)、前置きの予約名(`img` `show` …)、識別子にならない名前、表示指示と
  同じ名前の op は関数として出さず、`op("名前", …)` で呼ぶ。**2026-11-12 の全数: 964 本で衝突 0**
  (`min_image` などは衝突しない)。試験が全数を数え、衝突する名前が `__all__` に無いことを確かめる。

## 4. 実行(`run_program`)

- 文面を `compile(text, "<studio-program>", "exec")` し、前置きの名前空間で `exec` する。
  `print` はプログラムの名前空間の中で取り込んで `ProgramResult.stdout` に返す(§15)。
- **`sys.settrace`**: `<studio-program>` の枠の `line` だけを見る(他のモジュールの枠には局所トレースを
  付けないので遅くならない)。行ごとに:
  - 停止の要求(`stop_event`)・時間の上限(`time_limit_s`、**既定 30 秒**)→ 止める。
  - ブレークポイント(`breakpoints`)→ その行を**実行する前**に止める。`skip_hits` 回までは通過。
  - 1 行実行(`max_lines`)→ その数の行を実行したら止める。
  - 止めるのは `ProgramStopped`(`BaseException`)を投げて行う。`except Exception` では捕まらず、
    `except BaseException` で捕まえても次の行でまた投げる(一度止めたら止まり続ける)。
- **続行**は 2 通り。`pause_hook=` を渡すと(Studio の Python のモードはこれ)、ブレークポイント・1 行実行で
  実行を**終えずに作業スレッドの中で待ち**、フックが返す指示("continue" / "step" / "stop")で**止まった所から
  続ける**(上から走り直さない = print・乱数・ファイルへの書き込みが 2 度走らない)。待っている時間は時間の上限に
  数えない。待っている間に `stop_event` が立てば見張りが止める。`pause_hook` を渡さない呼び方(API・試験)は
  今までどおり、止まった所で実行を終え、続きは「上から走り直し、ブレークポイントを `skip_hits` 回通過」
  (メモ化 §6 で上流の op は計算し直さない)。
- **止まった所の変数**: モジュールの階層は名前空間そのもの。関数の中で止まったら、その枠の局所変数を
  `ProgramResult.locals`、呼び出しの積み重ねを `stack`(`[(関数名, 行)]`、内側が先)に入れる。
- **例外**: トレースバックの中で `<studio-program>` の最も深い枠の行番号を取り、
  `line 2: ZeroDivisionError: division by zero` の形で返す。構文の誤りは `SyntaxError` の行。
  `exit()` も行番号つきの誤りにする(Studio は落ちない)。
- **結果**(`ProgramResult`): 記録した段の列 `calls`(`CallRecord` = op 名・a・b・行番号・入力の型と形・
  出力の sort と形・時間 ms・`cached`・device・測るだけか・入力を省いたか・パイプラインの名前と何段目か・
  結果の参照)、最後に見せる値、変数の表 `variables`(名前・型・形・要約。画像は
  `image 512×512 float64`、16 要素以下の配列と小さい値は中身)、標準出力、行番号つきの誤り、止まった理由と行、
  丸めたつまみ、表示の指示。
- **止められない物(正直に)**: C の中で回っている重い op や `time.sleep` の途中(見張りが 1 秒で諦めて
  呼び出し側へ戻り、そのスレッドは残す。§4.0)、プログラムが作ったスレッド(`settrace` も見張りも
  そのスレッドに付かない)。握りつぶすループは撃ち直しで止まる(試験あり)。**メモリの上限は付けない**
  (本物の Python なので)。
- **外部 tracer の下での限界**: デバッガーや coverage など別の tracer が動いている間は、Stop ボタンと
  時間の上限による停止を保証しない。Stop を要求した時と、時間切れ・停止不能を報告する時に Studio が検出できれば、
  出力の欄でこの制限を知らせる。

### 4.0 必ず止める(見張り)

- プログラムは**作業スレッド**(daemon、スタック 64 MB)で回し、呼び出し側のスレッドは待つだけ
  (呼び出し側が既に作業スレッドでも同じ形)。見張りは呼び出し側にいて、時間の上限か `stop_event` で
  `PyThreadState_SetAsyncExc` を撃つ(止めの例外は `ProgramStopped` = `BaseException` の子)。素の Python の
  ループは Release でも遅れなく止まる(試験: `while True: pass` が上限 0.5 秒で止まる)。
- `except BaseException` で握りつぶすループには、0.05 秒ごとに撃ち直す(上限 60 回)。Debug では行フックも
  一度止めたら次の行でまた止める。
- **撃ち始めて 1.0 秒で戻らなければ諦めて呼び出し側へ戻る**(`stopped = "unstoppable"`、errors に「could not stop
  the program … it goes on running in the background and its results are ignored」)。残したスレッドは
  `abandoned_runs()` の一覧に持つ。止められないのは C の中の長い呼び出し(`time.sleep(60)`、大きな SVD など)で、
  そこから Python へ戻った所で例外が届いて終わる(戻らなければプロセスが終わるまで残る)。
- 試験(子プロセスで回し外側に時間切れ): Debug / Release × (`while True: pass`・握りつぶすループ・
  `time.sleep(60)`・numpy の重い 1 回の呼び出し)の 8 通りで、呼び出し側が「上限 + 2 秒」以内に必ず戻る。
- Debug の見張りは行フックより 0.25 秒遅らせる(行フックの方が行番号つきの文で止める)。見張りは保険。
- Qt を直接 import するプログラム(`needs_gui_thread`)を main スレッドから回すときは、呼び出し側(GUI)の
  スレッドで回し、見張りが別のスレッドから撃つ。この形だけは C の中で止まった物を諦めて戻ることができない。

### 4.2 実行の後に戻す物・戻さない物(プロセス全体の状態)

本物の Python を Studio のプロセスの中で回すので、プログラムがプロセス全体の状態を変えうる。

| 物 | 扱い | 理由 |
|---|---|---|
| `sys.path` | **戻す**(実行前の列へ) | 次の実行・Studio の import が変わる |
| `os.environ` | **戻す**(足した鍵を消し、変えた値を戻す) | 別プロセスで走らせる普通の IDE と同じ見え方 |
| 作業フォルダ(`os.chdir`) | **戻す** | Studio の相対パスが狂う |
| `builtins` の名前 | **戻す**(足した名前を消し、差し替えを戻す) | 他の実行・Studio 本体に漏れる |
| `warnings` の絞り | **戻す** | Studio の警告が消える |
| `sys.stdout` / `sys.stderr` / `sys.stdin` | **戻す** | 差し替えられると Studio 本体の出力が飲み込まれる |
| `sys.excepthook` / `sys.displayhook` / `sys.unraisablehook` / `threading.excepthook` | **戻す** | クラッシュの記録(studio_crash.log)が書かれなくなる |
| 再帰の上限(`sys.setrecursionlimit`) | **戻す** | 次の実行と Studio 本体に効く |
| `sys.modules` | 利用者のフォルダ(実行したファイルの場所・`programs/`)から読んだ物だけ外す。他は残す | numpy などを毎回読み直すと遅い。外すと直した中身が読まれる |
| numpy の乱数の状態・`np.seterr`・logging の設定・signal・開いたファイル・作ったスレッド | 戻さない | 戻す一般の方法が無い。必要なら別プロセスの実行(§14) |

戻した物は `notes` に「restored after the run: sys.path, os.environ, cwd, builtins」と出す。戻す物の一覧は
`studio_program.RESTORED_STATE`(試験は一覧の全部を 1 つずつ壊して、戻る事と名前が出る事を見る)。
2 本の実行を同時に回すと互いの変更を戻し合うので、同時実行は UI 側で 1 本に絞る前提。
**止められずに残した実行(§4.0)が生きている間は、次の実行を始めない**(`run_program` / `evaluate` が
「not run: an earlier run could not be stopped and is still running in the background …」を返し、画面にも出す)。
残った実行は諦めて戻した後にも環境変数や作業フォルダを書き換えるので、終わった所で**もう一度戻す**。
**取り込む標準出力は末尾 100 万文字まで**(`MAX_STDOUT_CHARS`。越えた分は古い方から捨て、捨てた文字数を先頭に書く。
`ProgramResult.stdout_total` が書かれた総数)。
**実行の後の変数の表(`describe_value`)は利用者のコードを呼ばない**(`__repr__` / `__len__` / `__class__` の
プロパティ)。数・文字列・numpy・完全一致の list / tuple / dict / set だけ中身を書き、利用者のクラスの物は型の名前。
見張りの外で動く所なので、戻らない `__repr__` があると実行が終わらなくなるため。
`trusted=False` のときは実行せず、errors に「not run: … confirm it first」を入れる(黙って何もしない、にしない)。

### 4.1 Debug と Release(実行の構成。画面では 1 か所に常に表示)

| | Debug(既定) | Release |
|---|---|---|
| 行フック(settrace) | あり | なし |
| ブレークポイント・1 行実行 | 効く | **効かない**。渡されていれば結果の `notes` に「Release does not stop at breakpoints (lines 2) — switch to Debug to use them」 |
| 止める場所 | 行の境目(停止の要求・時間の上限)+ 見張り(§4.0) | 見張り(§4.0)と op の呼び出しの境目(`Recorder.check_stop`)。素の Python のループも止まる |
| 段の列(記録)・メモ化・結果 | 同じ | 同じ(試験: 3 種のプログラムを両方で走らせ、段の列・行番号・出力が一致) |

- `run_program(config="debug" | "release")`。
- 速さ(2026-11-12 の試作の実測を引用。報告は repo の外に置いた作業用の資料): 行フックを外すだけで画素の 2 重ループ
  5.4 倍・手書き 3x3 畳み込み 3.2 倍・スカラーの反復 10^6 回 7.9 倍。numpy / op の呼び出しが主役のコードは
  変わらない(269 ms → settrace ありで 252 ms)。**Release の第 1 段はこれだけ**(依存なし)。
- **関数をコンパイルする枠(未実装・方式は実測の結果に沿って次の段)**:
  - 既定の方式は numba(任意の依存。wheel だけで入る。REPORT の実測で 22〜1800 倍、入れた後 numba 29 MB +
    llvmlite 122 MB)。Cython は C コンパイラ(Build Tools 3.4 GB + SDK 3.8 GB)と型注釈を利用者に求めるので
    今は作らない。
  - 印の名前の案: `@fast`(前置きが出す。中身は `numba.njit(nogil=True)` を包む)。入っていない・型が通らない
    (例 `np.pad(mode="edge")` は TypingError)ときは**理由を見せて素の Python で動かす**。最初の 1 回は
    素の Python と結果を突き合わせ、一致と倍率(「@fast smooth: 1126x, same result」)を見せる。
  - 条件(入れる前に確かめる): numba は**配列の範囲外を既定で検査しない**(読むとゴミ、書くとメモリを壊す。
    `NUMBA_BOUNDSCHECK=1` は未試験 → 有効にできなければ最初の 1 回の突き合わせを必須にする)。0 割りは
    例外になるが行番号が出ない。`exec` した文字列の関数はキャッシュできない(`cannot cache function: no
    locator available` → 毎回 0.1〜3 s のコンパイル。プログラムを一時ファイルに書いて import する案)。
    コンパイル済みの中は settrace が見えず、**止めるには `nogil=True` + 共有の旗配列**が要る。何もしないと
    止まらず、GIL を離さないので **UI スレッドも固まる**。
  - 依存なしで効く勧め: 「numpy で書き直すと 44〜124 倍」(REPORT)をサンプルと助言で出す。

### 4.3 結果を文字にする段・GUI の部品・残ったスレッド(2026-11-13 第 2 回レビュー)

考え方: 確認を経たコードは利用者自身のコードなので、悪意への完全な封じ込めは目標にしない。目標は
(a) 確認していないコードが走らない事、(b) 普通に書いたコードのうっかり(重い `__str__`、`plt.show()`、スレッド)で
Studio が固まったり戻らなくなったりしない事。

- **結果を文字にする処理は、全部が作業スレッドの中・見張りの内側**。プログラムが終わった後、例外の文
  (`str(e)`)・終了コード・変数の表・出力の種類を、プログラムと同じ作業スレッドで作る(上限 2 秒。越えたら
  止めの例外を撃ち、文は `<the text of this X is not available: its __str__ did not return in time>` になる)。
  呼び出し側(GUI)は出来上がった str と表だけを受け取り、例外や値そのものには触らない。型の判定は同一性
  (`t is int`)と `type` 自身の記述子(`type.__dict__["__name__"].__get__(t)`)で行い、`isinstance` / `==` /
  `x.__class__` / `t.__name__` を生の値に使わない(メタクラスの `__eq__`・`__name__`・`__mro__` のプロパティ、
  `__class__` のプロパティが利用者のコードを呼ぶため)。利用者のコードを呼びうるのは例外の `__str__` の 1 か所だけ。
- **例外の文は 2000 字まで**(`MAX_ERROR_CHARS`)。状態の欄のツールチップも 2000 字まで。
- **GUI の部品は作業スレッドから import できない**。実行の間だけ、プログラムの作業スレッドからの
  `PySide6` / `PyQt*` / `tkinter` / matplotlib の窓を出す backend(`backend_qtagg` など)の import を
  `ImportError`(「Studio does not let a running program import …」)で断る。`import` 文・`__import__`・
  `importlib.import_module`・`exec` した文字列・ライブラリの中からの import を拾う。Studio 自身のスレッドの
  import は通す。
- **matplotlib は Agg で動く**(実行の間だけ `MPLBACKEND=Agg`。Studio は PySide6 を読み込み済みなので、何もしないと
  matplotlib は QtAgg を選び、`plt.show()` の 1 行が作業スレッドで Qt の窓を作って Studio 全体が固まった)。
  `plt.show()` は窓を開かず、今の図を画像の欄へ出す(`show(fig)` も同じ。`notes` に 1 行)。
- **変数・ウォッチの欄の利用者のコード**(`__repr__`、ウォッチの式)は別のスレッドで時間の上限つきで呼ぶ。
  時間切れの後も止まらずに残ったスレッドが 1 本でもある間は、新しいスレッドを起こさず「表示していません」と出し、
  **次の実行も始めない**(`STRAY_BLOCKS_RUN`。止めの例外が保留のまま残ると、CPython 3.11 では `sys.settrace` の下の
  実行が約 300 倍遅くなり、何もしないプログラムが時間切れに見えた)。`__repr__` が変えた環境変数と作業フォルダは
  戻す。補完・ホバー・要約の「ライブラリの型か」は、名前でなく実体で決める(C の静的な型か、`__module__` の
  モジュールから `__qualname__` を辿って同じ型に着く時だけ)。
- **プログラムが起こして残したスレッド**は、実行の後に `notes` で知らせ(`program_threads()`)、次の実行の前にも
  出力の欄に出す。止めはしない。

既知の制約(正直に):

- **`sys.modules` から直接引く道は塞いでいない**(`sys.modules["PySide6.QtWidgets"].QLabel("x")`)。プログラムが
  起こした別のスレッドからの import も見ていない。わざと書かない限り通らない道として残す。
- **プログラムが起こしたスレッドが変えた環境変数・作業フォルダ・ファイルは戻さない**(知らせるだけ)。
  ThreadPoolExecutor と asyncio の作業用のスレッドは数えない(ライブラリが持ち続ける物と区別できない)。
- **止められずに残した実行が終わった所で「もう一度戻す」時、その間に Studio 自身がした変更も実行前の値へ戻る**
  (環境変数・`sys.path`・warnings の絞り・`sys.stderr`。区別していない)。残した実行は、**戻し終えるまで**を
  「残っている」に数える(スレッドが終わった瞬間に次の実行を通すと、その実行の途中で状態と import の見張りが
  戻されるため。試験あり)。
- **戻さないプロセスの状態**(`RESTORED_STATE` の外): `sys.meta_path` / `sys.path_hooks` に足した import の仕掛け、
  `gc` の有効・無効、`locale`、乱数の状態、`sys.modules` の中の標準ライブラリの差し替え、`sys.setswitchinterval`、
  `sys.set_int_max_str_digits`、`threading.setprofile` / `settrace`、`sys.addaudithook`(外す方法が無い)。
  どれも確認を経た利用者のコードがわざと行う操作で、Studio を起動し直せば消える。
- **許す型の一覧にある物については、ライブラリのコードを呼ぶ**(numpy・標準ライブラリ・site-packages を信用する。
  §4.4)。利用者が site-packages に入れたパッケージは「ライブラリ」として扱われる。ライブラリのモジュールへ自分の
  型を代入した物(`json.X = X`)は、クラスそのものは「ライブラリ」として扱われる(そのインスタンスは、一覧に
  無いので静的な名前だけを使う)。
- **従来の Python エディタ**(別の窓)は別プロセスで走らせる。走らせるのは常に画面の文面(一時の写し)で、
  `__file__` は写しの場所を指す(元のファイルの場所は `PYTHONPATH` に足すので、隣の .py は import できる)。

### 4.4 入口は 1 つ・import の見張りの範囲・画像の欄に出す物(2026-11-13 第 3 回レビュー)

- **利用者のコードを回す入口は 1 つ**(`studio_program._guarded_user_call`)。F5・続行・1 行実行(`run_program`)も、
  選んだ行の実行(`evaluate`)も、ここを通る。中に入っている物: 断り(止められずに残した実行・変数の欄の
  `__repr__` 用のスレッドが残っている間、作業スレッドからの Qt)、GUI の部品の import の見張り、matplotlib を Agg に
  する事、プロセスの状態の写しと戻し(§4.2)、残した実行が終わった所でのもう一度の戻し、プログラムが残した
  スレッドの知らせ。見張りつきで利用者のコードを回す所(`_run_with_watchdog`)は、この関数の中の 1 か所だけ
  (試験が源を読んで数える)。この先に足す入口(対話の窓など)も、ここを通す。
  前は「選んだ行を実行」だけが守りを 1 つも通らず、選んだ行が作業スレッドで QLabel や QtAgg の図を作り、
  `plt.close('all')` で Studio 全体が固まった(外から殺すしかなかった)。
- **選んだ行の実行も、変えたプロセスの状態を戻す**(`sys.stdout`・環境変数・作業フォルダ …。出力の欄に
  「restored after the run: …」と出る)。選んだ行の `os.chdir(...)` は、その実行の中だけで効く。止まっている
  (ブレークポイント)間の選んだ行は、止まっている実行の状態へ戻る。選んだ行の `show()` / `plt.show()` は、F5 と
  同じく画像の欄へ出る。時間の上限と停止の要求は、選んだ行の物を使う(前は、Release の実行が記録に残した上限が、
  その後の選んだ行の op の呼び出しを「時間切れ」で止めていた)。
- **matplotlib は、図が残っていても Agg にする**。前は「図が 1 つでもあれば backend を変えない」だったので、
  窓を出す backend(QtAgg など)の図が 1 つ残っているだけで、次の実行の `plt.figure()` が作業スレッドで Qt の窓を
  作った。窓を出す backend で作られた図は、作業スレッドからは使えず、閉じる事もできない(持ち主でないスレッドから
  Qt の窓を消すと固まる)ので、pyplot の一覧から外し(窓は消さない)、`notes` に 1 行入れる。図そのものが
  名前空間に残っていれば、`show(fig)` で画像の欄へ出せる。
- **import の見張りは、相対 import と `importlib.__import__` も見る**。相対 import は、import 文と同じ決まり
  (`__package__` → `__spec__.parent` → `__name__`)で絶対の名前にしてから調べる(前は `__package__ = "PySide6"` と
  `from . import QtWidgets` で抜けた)。利用者のパッケージの中の相対 import は今までどおり通る。
  `sys.modules` から直接引く道と、プログラムが起こした別のスレッドからの import は、今までどおり既知の制約。
- **画像の欄へ出すのは、数の素の配列だけ**(bool・整数・実数・複素数)。object・文字列・日付・構造体の配列を
  `show()` しても窓は出さず、出力の欄と状態の帯に「画像ではない(型と形)」と出す(前は、表示の処理が落ちて
  毎回モーダルの窓が出た)。
- **補完・ホバー・シグネチャが調べてよい物は、許す型の一覧で決める**(`studio_pyedit_safe.is_inert`): 数・文字列・
  素の入れ物・numpy の C の型の物・ライブラリのモジュール・ライブラリのクラスそのもの・C の関数と記述子・
  ライブラリのコードから作られた関数(`__code__` の置き場で決める)。包みの型は中身まで見る(束縛メソッド・
  `staticmethod` / `classmethod` / `property`・`functools.partial` / `partialmethod` とその引数・`__wrapped__`)。
  `weakref.proxy` は常に偽。一覧に無い物(利用者の物、**一覧に無いライブラリのクラスのインスタンス**)は、静的な
  名前(型の MRO とインスタンスの `__dict__`)だけを使う。前は「ライブラリの型のインスタンスなら何でも調べる」で、
  `weakref.proxy`・`functools.partial`・ライブラリのモジュールへ差し込んだクラスを通して、利用者の
  `__getattribute__` / `__getattr__` / `__dir__` が GUI のスレッドで走った(ホバーで 24 秒)。
- **変数の欄の要約は、利用者の関数の既定値を文字にしない**(`f(a, b=…)`。ライブラリの関数は今までどおり
  `inspect.signature`)。前は `def f(x, cfg=Config()):` の `Config.__repr__` が GUI のスレッドで走った。クラスの
  名前は `type` 自身の記述子、モジュールの名前はモジュールの `__dict__` から読む。

既知の制約(この回で残した物):

- **補完・ホバー・シグネチャを作業スレッドで回して約 100 ms で打ち切る形は入れていない**(第 1 回からの案)。
  今は GUI のスレッドで呼び、上の一覧で「利用者のコードを呼ばない」ようにしている。一覧にある物については
  ライブラリのコード(jedi を含む)を待つ。
- 一覧に無いライブラリのクラスのインスタンスは、`__dir__` が足す動的な名前(pandas の表の列の名前など)が補完に出ない。
- ウォッチの式(`studio_pyedit_values`)は別の入口(時間の上限つきの別のスレッド)で、上の 1 つの入口は通らない。
  式の中で GUI の部品を import する事は断っていない。

### 4.5 第 3 回レビューの直しの確かめ(2026-11-15)

確かめの担当 2 人が、§4.4 の直しの後に見つけた物と、その直し:

- **入口は入れ子にしない**(重大。§4.4 の直しで入った退行)。ブレークポイントで止まって待っている Debug の実行の
  間の「選んだ行」は、止まっている実行の import の見張りの下で回す(作業スレッドを外側の見張りに足すだけ。見張りも
  遅れた戻しも重ねない)。外側の実行が終わる時に、まだ終わっていない・止められずに残した選んだ行があれば、外側が
  それを待ってから外側の前の状態へ戻し、見張りを外す(その間は次の実行を断る)。前は選んだ行の遅れた戻しが
  「止まっていた時の写し」と外した見張りを戻し、Studio の中の import が全部 `TypeError` になり、プログラムが
  変えた環境変数と作業フォルダも戻ってきた。走っている(止まっていない)実行とは重ねて始めない。外した見張りが
  鉤の列に残っても、何も断らずに元の物へ素通しする。
- 選んだ行は、名前空間の `print` を終わったら戻す(続行したプログラムの print が出力に出なかった)。名前空間の
  `__studio_recorder__` は `Recorder` そのものの時だけ使う(入口の外で利用者のコードを呼ばない)。
- import の見張りは、`importlib.import_module` の相対の名前(`'.QtWidgets', 'PySide6'`)、dict の派生を globals に
  した相対の `__import__`(決められないので断る)、str の派生の名前・`__package__` も見る。
- 補完・ホバー・シグネチャ・変数の欄: 呼べない物は `inspect.signature` に渡さない(誤りの文で要素の `__repr__` が
  走った)。object の要素を持つ配列は調べない。C の関数・method-wrapper は束縛した相手まで見る。静的な属性の
  引き方は型の記述子だけで行う(`inspect.getattr_static` は 3.11 でメタクラスの `__getattribute__` を呼ぶ)。
  源の木では配布するモジュール(`pyproject.toml` の `py-modules`)だけをライブラリとして扱う。プログラムの中の
  関数・束縛メソッドのシグネチャは `__code__` から作る(既定値は `=…`。§4.4 の直しで出なくなっていた)。
- 起動し直した時: 退避した未保存の文面を出すのにファイルが外で変わっていたら、比べる元は無し(自動保存は書かず、
  Ctrl+S は聞く。設定に生のバイトの印を残して比べる)。ファイルが読めなくても退避した文面を捨てない。
- Undo / Redo で戻った文面の由来と信頼は、その文面が変換・移すで置き換えられた時の物(手で打った文面を「ファイル
  から来た」と言わない)。確認していないファイルの文面は、今までどおり確認するまで走らない。

## 5. 安全: 本物の Python を実行するので

- **自分で打ったプログラムはそのまま走る**。
- **ファイルやプロジェクトから読み込んだ Python のプログラム、MCP や自動操作から来たプログラムは、
  最初の実行の前に 1 回確認を出す**(「このプロジェクトには、この PC 上で実行される Python のコードが
  含まれます」。VS Code の Workspace Trust と同じ考え)。実行系の入口 `run_program(..., trusted=False)`
  は実行せずに理由を返す(`not_run_reason`)。確認の状態は文面の SHA-256(改行を揃えて)で覚える
  (`TrustStore`、1 文字でも変われば確認し直し)。由来 `typed` だけが既定で信頼、`file` / `project` /
  `mcp` / 自動操作は確認が要る。
- 従来のモード(HDevelop 風)は任意のコードを含まないので確認は要らない。**パイプラインのファイルはデータ**として
  確認なしに開くので、そこから Python へ渡る道を塞ぐ:
  - `hdev_to_python` は、表示の指示(`dev_*` / `disp_*` / `set_system`)の引数を**定数(数・引用符つきの文字列)と
    素の語だけ**に限り、それ以外(呼び出し・属性・添字・演算・キーワード引数 …)は変換の誤りにする
    (fail-closed)。出す行は構文木から作り直し、元の文字列は写さない。
  - 開いたパイプラインのファイルから「Python に変換」した文面は、**そのファイルの信頼を引き継ぐ**
    (由来 `file`・未確認。最初の実行の前に確認)。
  - Python の実行の入口(`studio_pymode` の実行・1 行・選んだ行)は、パイプラインのモードでは走らない
    (指示の行は Python としても読めるため)。
- **信頼は文面に結び付く**(2026-11-13 第 3 回レビュー S2)。「Python に変換」と札の「Python のモードへ移す」は、
  Python の文面を 1 回の編集で置き換えて「手で打った物」にするが、Ctrl+Z で前の文面が戻る。ファイル・プロジェクト
  から来て確認していない文面は、中身の SHA-256 で覚えておき(開いた時・起動時の復元・置き換える直前)、今の文面が
  その文面そのものになったら(Undo / Redo で戻った時も、実行の前にも見る)、由来と信頼をそのファイルの物に戻す。
  戻した後に直した文面も、確認するまで「ファイルから来た物」。確認すれば、その文面と同じ所から来た文面の覚えは
  消える(Undo / Redo で同じ文面に戻っても聞き直さない)。前は
  「X.py を開く(未確認)→ パイプラインのモードで 1 行打つ → Python に変換 → Ctrl+Z → F5」で、確認の窓が出ずに
  X.py が走った。
- **確認の窓の既定のボタンはキャンセル**(Enter でも Esc でも実行しない)。画面の無い実行(offscreen)では窓を
  出さず、実行しない側を返す。
- 従来の Python エディタ(別の窓)にファイルから開いた `.py`(ドラッグ&ドロップ・開く)も、同じ台帳と同じ確認の窓を通る。
  **確認した文面 = 走らせる文面**(常に画面の文面を一時の写しから走らせる。開いた後でディスクのファイルが変わっても、
  変わった中身は走らない。変わった事は出力に書く)。プロジェクトのパラメータのファイルなどを読み取り専用の窓から
  「Open in editor」で送った文面も、ファイルから来た物として初回に確認する。
- 確認の UI は次の段(§13)。

## 6. 最適化

### 6.1 op の呼び出しのメモ化(この段で実装)

- 鍵 = (op 名, a, b, 入力ごとの指紋, device)。プログラムを 1 行直して走り直すと、変わっていない上流の op は
  計算し直さない。ループの中で引数が変わらない呼び出しも 1 回で済む。
- **指紋は中身から取る**(配列の id ではない)。ただし毎回全画素を読まないように:
  - 記録層が作った読み取り専用の配列は「由来の指紋」= 作った呼び出しの鍵の SHA-256(画素を読まない)。
  - 入力の画像は実行ごとに 1 回、中身の SHA-256(`engine._input_hash` と同じ全バイト。
    **1024×1024 float64 で 1.80 ms**、同じ画像の gaussian 1 回は約 13 ms)。
  - 利用者が numpy で作った書き換えできる配列は、呼ぶたびに中身の SHA-256(書き換えられても古い結果を
    出さない)。数・文字列・list / tuple / dict は中身を辿る。数えられない物(object 配列など)はメモ化しない。
- **メモ化しない op**: 名前で乱数・副作用と分かる物(noise / random / sample / aug_ / ransac / write / save …)、
  実装の本体(`_safe` などの包みを外した関数)のソースに乱数・時刻・ファイル書き込みの語がある物、
  ソースが読めない物、n-ary。呼んだ先の補助関数までは読まないので確実ではない ——
  試験で、メモ化してよいとした op の標本(画像 → 何か の 1/8)を同じ入力で 2 回呼んで同じ答えを確かめる。
  分からなければメモ化しない側に倒す。
- **上限と捨て方**: 値の置き場は `studio_result.StageCache`(PipelineModel の段のキャッシュと同じ LRU・
  同じ上限 `CACHE_BUDGET_BYTES` = 256 MiB)を使い回す。
- 命中は記録の `cached` に残る(段の列に「cache」と出せる)。**命中した結果が計算し直した結果と画素単位で
  同じ**ことを試験にしている。
- 実測(1024×1024、gaussian・median・otsu・blob_count・ループの gaussian 2 回・分岐の 1 回、計 7 呼び出し):

  | 実行 | 時間 | 命中 |
  |---|---|---|
  | 1 回目 | 422 ms | 0 / 7 |
  | 2 回目(同じ文面) | 6.8 ms | 7 / 7 |
  | ループの中の 1 行を直した後 | 74 ms | 4 / 7(上流 4 つ) |
  | 上流の 1 行(median)を直した後 | 509 ms | 1 / 7 |

### 6.2 構文木を見る助言(この段で実装、`advise_program`)

書き換えは黙ってしない。行番号つきの提案で、実行結果は変えない。誤った助言を出さないことを優先する。

| 種類 | 出す条件 | 例 | 直した文面 |
|---|---|---|---|
| `unused_result` | 測るだけの op の結果を、どこからも読まない変数に入れている | `n = blob_count(otsu(a))`(n を誰も読まない) | トップレベルの 1 行の文なら、その行を消した文面 |
| `loop_invariant` | ループの中の op の引数が定数か、ループの中で代入されない変数だけ。入力を省いていない。メモ化できる op | `for i in range(3): g = gaussian(img, 0.4)` | 無し(メモ化がすでに 1 回にしている、と添える) |
| `duplicate` | 同じブロックに同じ op の呼び出しが 2 回、間で引数の変数が代入されない | `a = gaussian(img, 0.4)` / `b = gaussian(img, 0.4)` | 無し |
| `type_mismatch` | 1 回しか代入されない変数の sort が、受ける op の入力の sort と合わない(`engine._compatible`) | `m = otsu(img)` / `gaussian(m, 0.4)` | 無し |

出さない条件(全部試験に紛らわしい例がある): `globals` / `locals` / `vars` / `eval` / `exec` / `getattr` …
を使う、`global` / `del` / `import` を使う、関数の中、op の名前を上書きした、ループの中に属性の呼び出しや
添字への代入や op 以外の関数の呼び出しがある(書き換えかもしれない)、入力を省いた(流れに依る)、
乱数の op、画像の op の結果が使われない(流れと最後の表示を変えるので消せない)、2 回以上代入される変数の型。

### 6.3 等価な書き換えの候補(この段では実装しない)

続けて掛けるガウシアンを 1 回に(σ を合成)、閾値の後の同じ構造要素の開閉の重複、など。厳密には等しく
ないことが多い(端の扱い・離散化)。枠組みだけ決める: 候補ごとに「前後の時間」と「最大の画素差・差のある
画素の数」を**実測して並べ**、利用者が選んでから文面を書き換える(黙って置き換えない)。記録(§4)に
入力と時間があるので、同じ入力で前後を走らせるのは安い。

### 6.4 実行の計画(GPU・並列)

既存の `device="auto"`(`gpu_route` / `explain_pipeline`)に任せる。この段では記録に device と時間を
残すだけ(`run_program(device=...)` を各呼び出しへ渡す)。

## 7. 2 入力の op と測るだけの op の例

```python
d = sub_image(img, gaussian(img, 0.9))   # 背景の差。入力を 2 つ明示する
n = blob_count(otsu(d))                  # 測るだけ: 流れは d のまま
if n > 5:
    show(d)
```

## 8. Python の中からパイプラインを使う

- 組み立ては **段の組の列だけ**にする: `p = pipeline([("gaussian", 0.4), ("otsu",)], name="edge")`
  (`(op, a, b)`、`a`・`b` は省略可。op 名の文字列でも可)。`pipeline(gaussian(0.4), otsu())` の形は
  採らない: `gaussian(0.4)` は「今の流れに掛けて実行する」呼び方なので、段の部品にもすると
  「入力つきで呼ぶと実行、入力なしで呼ぶと段」になって紛らわしい。
- `p(x)` / `p.run(x, upto=k)`(0..k 段目)/ `p.run_stepwise(x)`(段ごとの結果)/ `p.save(path)` /
  `p.stages`。`x` を省くと今の流れ。`p(x)` は **`fullseye.run_pipeline(x, p.stages)` と同じ意味・同じ
  結果**(段ごとに `api.run_pipeline(v, [段], coerce=第 1 段だけ)` = Studio の `_run_stage` と同じ。
  先に `api._check_chain_sorts` で型の繋ぎを検査)。試験: recipes.py の全レシピで画素単位に一致、
  `run_stepwise` は `FullseyeEngine.run_stepwise` と一致。
- 中の各段は記録に載る(`CallRecord.pipeline` = 名前、`pipeline_step` = 何段目)。メモ化も効く。
- `current_pipeline()` = Studio の画面で組んだ今のパイプライン(従来のモードの段の列。切った段は除く)。
  `run_program(current_stages=...)` で渡す。書き出したスクリプトには `studio_set_current_pipeline([...])`
  の 1 行で埋め込む。
- `load_pipeline("名前")` = レシピ名か、Studio が保存した `.json`(§9)。同じ物が `fs.load_pipeline` で
  Studio の外から読める(前置きの物は記録つきの包み `studio_program.Pipeline` で、`source` に
  `engine.PipelineFile` を持つ)。

## 9. 定義ファイル(パイプラインのファイル)

全数調査 `DEFS_IO_SURVEY.md`(2026-11-12)の §3 表 E・§4 D・§5.2〜5.3 に従う。

- **形式は新しく作らない**。Studio が今保存している JSON(`PipelineModel.to_dict`、拡張子 `.json`、
  `{"fullseye_pipeline": 1, "stages": [[op, a, b(, true)], ...], "directives"?, "input"?, "pinned"?}`)を
  そのまま正本にする。
- **印**: 書くときに `"fullseye_kind": "pipeline"`・`"version": 1`・`"created_by": "fullseye <版>"` を
  先頭に足す(他の鍵と段の位置は変えない。Studio の読み込みは知らない鍵を無視するので、書いたファイルは
  今の Studio でも開ける — 試験あり)。鍵の綴りは調査の §5.2(`fullseye_sort` / `fullseye_pipeline` /
  `fullseye_graph` に揃えた `fullseye_kind`)。
- **印の無い今までのファイル**は「版 0 のパイプライン」として読む: `fullseye_pipeline` が整数 1 か、
  鍵が無く `stages` の列だけがあるファイル。`fullseye_pipeline` が 99・`"banana"` なら断る(調査 §4 D の
  穴を、この入口では塞いだ)。`fullseye_graph` / `fullseye_sort` の印を持つ物は行き先を言って断る。
- **断る**(ファイル名と理由つき、`fullseye.DefinitionError` = ValueError): 壊れた JSON(行と列)、
  未知の `fullseye_kind`、新しすぎる `version`、整数でない `version`、未知の op、つまみが範囲外
  (0..1。Studio と同じ。Engine は今まで 1.5 を受理していた)、段の形が読めない、`params` を持つ段
  (版 1 には無い)。見つからないファイルは、探した場所を全部書いた `FileNotFoundError`。
- **段の形の正本** = `[op, a, b]`(切った段は `[op, a, b, true]`)。読むときに寄せる表
  (`engine.STAGE_FORMS`):

  | 読む形 | どこの形 | 扱い |
  |---|---|---|
  | `[op, a, b]` / `[op, a, b, bypass]` | Studio の保存 | 正本 |
  | `{"op": op, "a": a, "b": b}` / `{"name": op, …}`(`"bypass": true` も可) | Engine・MCP の a/b | 正本へ |
  | `"op"` | Engine | a = b = 0.5 の正本へ |
  | `[op, {"a": a, "b": b}]` | Engine | 正本へ |
  | `{"op": op, "params": {…}}` | MCP(名前つきの物理量) | **版 1 では断る**(版 2 で正本の拡張形にする案) |

  書くときは必ず正本の形。読み方の本体は `api._normalise_stage`(Engine と同じ 1 本)で、範囲の検査だけ
  Studio に揃えて足した。
- **入口の名前**: `fs.read_def(path, kind=None)` / `fs.write_def(obj, path, kind=None)`(印を見て振り分ける。
  `fs.load` / `fs.save` は画像用なので使わない)、種類別の薄い別名 `fs.load_pipeline(path)`
  (= `read_def(path, kind="pipeline")` + レシピ名)。戻り値の `PipelineFile` は `FullseyeEngine` の
  子で、`p(img)` / `p.run(img, upto=k)` / `p.run_stepwise(img)` / `p.stages` / `p.save(path)`。
  `save` は読んだ辞書の他の鍵(directives・input・pinned)と切った段を残し、**保存 → 読み込み → 保存で
  中身が変わらない**(試験あり)。版の検査の正本は `defs_io.check_marker(d, where, expect_kind)` の 1 本、
  パイプラインの中身の検査は `engine.pipeline_from_dict(d, where)`。
- **相対パス**は「プロジェクトのフォルダが分かればその `pipelines/` → 実行中のプログラムのファイルの場所 →
  作業フォルダ」の順(`studio_program.pipeline_search_dirs`。Studio は `run_program(project_dir=,
  program_dir=)` で渡す)。`pipelines` の綴りは差し込み口 `PROJECT_SUBDIR_RESOLVER` で、別の担当の
  `studio_project.py`(標準の並び images / pipelines / programs / params / results)から引けるようにしてある。
  Studio の外(`fs.load_pipeline`)では「走っているスクリプトの場所 → 今の作業場所」、または `search_dirs=`。
- **読み込みはデータだけ**: `json.load` で読み、op 名は台帳に在る物だけを受ける。pickle を使わない、
  ファイルの中の文字列を eval しない、読み手は種類の表に登録した関数だけ。書き出すコード
  (`FullseyeEngine.to_python`)は既存の名前の検査(在る op 名だけ)を通る。
- **書き込みは原子的**(同じ場所の一時ファイル → `os.replace`)。NaN / inf は書かない。
- jsonio との関係: 型つき値の封筒(`fullseye_sort`、MCP の `import_json` / `export_json` が依存)は
  作り替えない。定義の封筒は `defs_io.py` に**兄弟として**置いた(調査 §5.1 は「jsonio を拡張」。
  中身の流儀 = 自己記述・fail-closed は揃え、MCP が使う jsonio のファイルには手を入れなかった。
  まとめるなら `fullseye/jsonio.py` に `read_def` を移すだけで済む形にしてある)。
- **Studio の保存そのもの**(File ▸ Save)はこの段では変えない(今のファイルとバイト一致を保つ)。
  Studio の保存を印つきにするのは UI の段で、`PipelineModel.to_dict` に鍵を 3 つ足すだけ。

### 9.1 ほかの定義へ広げるときの決まり(カメラ・光学系・フィジカル AI の場面 …)

1. **種類を表に足す**: `defs_io.register_kind(DefKind(kind="camera", version=1, reader="mod:fn",
   writer="mod:fn", legacy="mod:fn"|None, migrations={0: "mod:fn"}, python_type="mod:Class"))`。
   読み手・書き手は文字列で持ち、使うときに import する(層が種類に依存しない)。kind の語彙は調査 §5.2
   (`camera` `stereo` `lens` `light` `sensor` `pipeline` `graph` `shape_model` `scene` `robot_scene` …)。
2. **印**: `fullseye_kind` と整数の `version` を必ず書く。`created_by` はログ用で判定に使わない。
   新しすぎる版・未知の kind は断る。**印の無い物を推測で読まない**(嗅ぎ分けは、既存のファイルが
   その種類に限って持つ鍵がある時だけ。カメラの dict は推測しない)。
3. **版を上げるとき**: 旧版 → 新版の移行関数を `migrations` に足す(読むときに今の版まで順に当てる)。
   旧版の読み手が黙って落とさず断るよう、意味が変わる追加(例: 段の `params`)は版を上げる。
4. **単位**: 中身に書く(`"units": {"length": "mm", "angle": "deg", "pixel": "px", "wavelength": "um"}`)。
   欠けていたら断る。鍵名の接尾辞(`_mm` `_um`)だけに頼らない。単位の変換は使うときに 1 回
   (調査 §1: `nm→um` を `v*1e-3` でやると 1 ULP ずれる値が出る)。
5. **JSON に入らない値**: NaN / inf は種類ごとに表現を決める(レンズの平面は `curv: 0` など)。
   書くときは `allow_nan=False`。tuple・ndarray を読み戻す型は種類ごとの読み手が復元する。
6. **大きな配列**は同じ場所の `.npy`(`allow_pickle=False`)を `{"$array": "name.npy", "sha256": "…"}` で
   参照する(インラインは 4096 要素まで)。読むときは `resolve_sidecar` が、定義ファイルの場所の内側か
   (`..`・絶対パス・外へ出るリンクは断る)・SHA-256 が合うかを確かめる。
7. **op にするか**: 読み書きは関数を正本にし、MCP にファイルパスを受ける道具は足さない(信頼境界を越える
   読みは封筒を引数で渡す既存の `import_json` 経由)。

## 10. 従来 ↔ Python の変換

- **従来 → Python**(`hdev_to_python`、「Python にする」の中身): 行の数と位置を変えない(行 N の段は
  変換後も行 N。ブレークポイントがそのまま使える)。

  | 従来 | Python |
  |---|---|
  | `gaussian (0.4, 0.5)` / `gaussian 0.4 0.5` | `img = gaussian(img, 0.4, 0.5)` |
  | `for 3` … `endfor` | `for _ in range(3):` … `# endfor` |
  | `if 1 = 2` … `else` … `endif` | `if 1 == 2:` … `else:` … `# endif`(`#` → `!=`) |
  | `if foo`(数の比較でない) | `if True:  # was: if foo`(従来と同じ真偽) |
  | `* コメント` | `# コメント` |
  | 中身の無いブロック | 開く行に `: pass`(行を足さない) |
  | `dev_set_lut (gray)` | `dev_set_lut('gray')`(素の語は文字列) |
  | `# bypassed: op (…)` | そのまま(Python のモードに「切った段」は無い) |

  既存の試験の文面のうち従来のモードで誤りの無い 69 本を変換し、走る段・行番号が全部一致、画像つきで
  走った 39 本は最後の `img` が画素単位で一致(試験)。途中に測るだけの op がある物は対象外: 従来の
  モードでは次の段がその数を受け取るが、Python では `img = blob_count(img)` で img が数になり意味が違う。
- **Python → 従来**(`python_to_hdev`): 分岐・ループの無い物だけ。戻せる文は `img = op(img, 数…)`
  (毎行同じ変数)・入力を省いた `op(数…)`・表示の指示・コメント・最後の `show(img)`。測るだけの op は
  最後の文でだけ許す。戻せない文は行番号つきの理由(「line 2: only op calls can go back to the stage list
  (If)」など)。

## 11. 書き出し

- Python のモードの書き出し(`export_python_script`)は「前置きの import + Program の文面そのまま +
  入出力の数行」:

  ```python
  # Fullseye Studio Program (Python) — exported.
  from fullseye.studio_prelude import *
  img = image = studio_input()          # sys.argv[1](.npy はそのまま読む)
  # ---- Program ----
  ...(Program 欄の文面)...
  # ---- end of Program ----
  studio_output()                       # sys.argv[2] か pipeline_result.png(.npy は値のまま)
  ```

  `py -3.11 file.py 入力画像 [出力]` で、Studio の実行系と**画素単位で同じ**結果になる(前置きは同じ
  記録層・同じ op の呼び方を使う)。試験は 6 種(分岐・for・while・関数定義・numpy・パイプライン)を
  別プロセスで走らせ、dtype と全画素を比べる。
- **逆向き**: 書き出したスクリプトを Program 欄へ貼ってもそのまま動く(`from fullseye.studio_prelude import *`
  は Studio の記録へ、`studio_input()` は Studio の画像を返し、`studio_output()` は何もしない)。試験あり。
  前置きの名前だけで書かれた普通の Python なら貼って動く。前置きに無い物(`cv2` を直接呼ぶ等)も動くが、
  記録(段の列)には載らない。
- 従来のモードの書き出し(`PipelineModel.export_standalone`)は変えない。

## 12. 後方互換の門

既存の Studio の試験 8 ファイルの文字列定数から Program の文面を集める(docstring と書式の型紙を除く。
2026-11-12 の実測 83 本、うち複数行 38 本、下限つき)。全部について:
- `detect_syntax` が従来のモードと判定する(0 本の取りこぼしを要求)。
- `run_program(text, None)` の段の列・行番号・切った段の印・誤りが `studio.parse_hdev_program_lines` と
  1 つ残らず一致(誤りの無い 72 本)。
- 画像つきで走らせた値が、Studio の `_run_stage` と同じ呼び方(段ごとの `api.run_pipeline`、coerce は
  第 1 段だけ)で走らせた値と一致(42 本。残りは op が入力の型で断る物で、両方が誤りを出すことを確かめる)。

## 13. UI への繋ぎ(この段では入れない。設計と見積もり)

入れなかった理由:
1. `apply_program` は文面を平らな段の列にして `model.stages` へ入れ、`refresh_stage_list` → `sync_program`
   が**エディタの文面を段の列から作り直す**。Python のプログラムはこの往復で消える。Python のモードには
   「文面が正本で、段の列は実行の記録」という逆向きの持ち方が要る。
2. 段の列(PipelineModel)は「1 本の流れ」を前提に段 i の結果を i-1 から作る(キャッシュもそう)。Python の
   記録は 2 入力・測るだけ・分岐で飛ぶ段を持つので、段の欄の再計算(つまみを動かしたら段 i から作り直す)は
   「文面を走り直す + メモ化」に置き換える必要がある。
3. Studio に入口を足すには `STUDIO_UX_RULES.md` の決まり(入口 4 つ以上を同じ名前で・空の状態の案内・
   6 言語の `tr()`・offscreen の試験・スクリーンショット)を満たす必要があり、エディタの部品
   (`ProgramEditor`)は別の担当が別の木で触っている。

設計(次の段):
- **モードの切り替え**: Program 欄の上に「従来 / Python」の切り替え(文面の 1 行目の印 `# python` と同期)。
  入口(UX 規則 §1): メニュー「プログラム ▸ Python のモード」/ コマンドパレット(「Python」「パイソン」
  「スクリプト」「変数」「分岐」「ループ」「if」「while」で当たる)/ Program 欄の上の切り替え / 文脈
  (従来のモードで `if 式` に変数を書いて誤りになったとき、誤りの文から「Python にする」)。キーは既存の
  割り当てを調べてから決める(この段では決めない)。
- **「Python にする」**: `hdev_to_python` の結果を新しいタブ(または同じ欄を置き換え、Undo で戻る)。
  戻せる物は「従来に戻す」(`python_to_hdev`)。戻せない時は行番号つきの理由を出す。
- **`apply_program` / `run_program` の切り替え**: `detect_syntax` が python のときだけ新しい実行系
  (`studio_program.run_program(text, model.image, memo=窓ごとの OpMemo, current_stages=今の段の列,
  program_dir=, project_dir=, breakpoints=エディタのブレークポイント, trusted=由来と TrustStore)`)を
  ワーカーで呼ぶ。従来の経路はそのまま。Python のときは `sync_program` で文面を作り直さない
  (`state["program_mode"] == "python"` の間は段の欄から文面を作らない)。
- **段の欄**: 記録 `calls` を読み取り専用の段として並べる(行番号・cache の印・パイプラインの名前と何段目・
  時間)。サムネイルは `CallRecord.value`。つまみを動かしたら、その呼び出しの行の数字を書き換えて走り直す
  (メモ化で上流は計算しない)。
- **変数の表**: 既存の「Variables & Objects」ドック(`dock_variables`、studio.py 7800 行付近。Watch の
  表もある)に `ProgramResult.variables`(名前・型・形・要約)を出す。画像は選ぶと表示に出す。
- **助言**: Problems の欄に `advise_program` の結果(行へ飛べる、「適用」は `fixed_text` がある物だけ)。
- **確認の UI**: ファイル・プロジェクトから開いた Python のプログラムは最初の実行の前に 1 回だけ確認
  (`TrustStore` を QSettings の隣の JSON に)。
- **見積もり**: モードの切り替えと実行の繋ぎ 1.5 日、段の欄と変数の表 1.5 日、確認の UI と信頼の台帳
  0.5 日、入口 4 種・6 言語・offscreen 試験・スクリーンショット 1.5 日、計 約 5 日(ProgramEditor の
  別担当の作業が入った後)。

### 13.1 繋いだ(2026-11-13、integrate/studio-1-2-0-2026-11-13)

実装は `studio_pymode.py`(Qt。モードの状態・実行の橋・出力の欄・記録の欄・信頼の確認・ファイルの開閉・入口)。
studio.py の差し込みは `win._pymode` を見て振り分けるだけ(F5 / F6 / Shift+F5・`sync_program`・文面の変化・
`apply_program`・選んだ行の実行・打っている最中の検査・Problems・パイプラインを開いた時・Project の `.py`・
窓の題・閉じる前の確認・言語の切り替え・`ProgramEditor` の装飾とコメントの記号と旧い補完の止め方)。
試験 `tests/test_studio_python_mode_2026_11_13.py`、本物の窓の筋書き(repo の外に置いた作業用の `e2e.py`、14 段)。

§13 の設計どおりの所: 文面が正本で段の欄は実行の記録(行・op・つまみ・出力・時間・「↺ 使い回し / ⟳ 計算」・
サムネイル。文面を直すと「記録は古い(行 N から)」)、モードごとに文面を別に持つ、Python のときは
`sync_program` が文面を作り直さない、`OpMemo` は窓ごとに 1 つ、変数とウォッチは既存の Variables の欄の
入れ物へ(`VarsWatchWidget`、パイプラインのモードでは今までの欄)、確認は `TrustStore`(設定が ini ならその隣、
それ以外は利用者のデータの場所の `studio_trust.json`)。

違えた所と理由:

1. **`build_window()` の既定はパイプラインのまま**(`start_mode="pipeline"`)。`fullseye-studio`(`main()`)は
   `start_mode="auto"` = 設定の「起動時のモード」(既定は前回のまま、初回は Python)。既存の Studio の試験
   (42 ファイル、1171 件)は全部 `build_window()` を呼び、起動直後の Program 欄がパイプラインの記法である前提で
   書かれているため。利用者の起動は決定どおり Python から始まる。
2. **続行・1 行実行は上から走り直す**(§4 のまま)。`run_program(resume_after_lines=前の lines_run + 1)` で
   止まった所までのブレークポイントを素通りし、1 行実行は `max_lines=前の lines_run + 1`。止まった後に文面を
   直していれば、続行は上からの実行になる(出力の欄にそう書く)。乱数や外の状態に依るプログラムは、走り直しで
   止まる前と違う値になりうる(正直な限界)。
3. **条件つきブレークポイントは実行系で評価**(止まる行の枠の globals / locals)。ウォッチの評価器
   (`WatchPanel.condition_evaluator`)は実行後の名前空間しか見えないので使わない。評価できない条件では
   止めて理由を `notes` に出す(素通りさせない)。
4. **入口**: メニューは新しい最上位を足さず、Run ▸ Program mode(Python のモード / パイプラインのモード /
   切り替え Ctrl+Alt+M / Python にする / Debug・Release Ctrl+Alt+D / 起動時のモード / 例 / 出力を消す)、
   File に新規 Ctrl+N・開く Ctrl+Alt+O・保存 Ctrl+Alt+S・名前を付けて保存 Ctrl+Alt+Shift+S、Run に実行・1 行・
   止める Ctrl+F2・ブレークポイント F9・条件。F5 / F6 / Shift+F5 は既存の動作が Python のモードの間こちらへ回す
   (同じキーを 2 つに割り当てると Qt はどちらも撃たない)。最上位のメニューを増やさないのは、見た目の担当が
   メニューの帯を触っているため。
5. **確認の後の編集**: ファイル・プロジェクトから開いた文面は初回の実行の前に確認する。確認した後にエディタで
   直した文面は、利用者が打った物として扱う(1 文字ごとに聞き直さない)。ファイルを開き直して中身が違えば
   聞き直す。自分で保存した中身は確認済みとして覚える。
6. **出力の欄**は Program の欄の中(エディタの下)。下の帯のタブ(Problems / 出力 / 対話)は見た目の担当の枝。
7. **補完**は `studio_pyedit_complete.default_provider`(0 始まりの行)を直接使い、`studio_program.complete`
   (1 始まり)は使わない。行の変換は `studio_pymode.to_block` / `to_line` の 1 か所(試験あり)。jedi は
   `allow_unsafe_interpreter_executions=False`・`auto_import_modules=[]` にした(実行後の値の property などを
   補完のために呼ばない)。ただし jedi は C 拡張のモジュールを調べるとき別プロセスで import する
   (利用者の .py は静的に読むだけ)。最初の補完の待ち(実測 2.9 s)は Python のモードに入った時に背景で温める。
8. **終了時の落ち方を直した**: `PyEditAssist` の event filter を付けたままプロセスが終わると Windows で
   access violation(exit 139)。`atexit` で外し、窓を閉じるときにも外す(`PyEditAssist.detach`)。
9. **言語**: 新しい文は i18n.json の strings に 6 言語。エディタ支援の部品の文(studio_pyedit_i18n.json)は
   i18n.json へ移さず、Studio の表に無ければ部品の表を引く(部品の表に hi は無いので、hi では部品の文は英語)。

まだ入れていない物(次の便): つまみ ↔ コードの値の往復(記録の行のつまみを動かして文面の数字を書き換える)、
助言(`advise_program`)と検査の直し(`apply_fix`)の「適用」、GUI スレッドの橋(`GUI_BRIDGE`、§15 の案 A。
**橋が無い間、Qt を直接 import するプログラムは Program 欄からは走らせず、分かる文で断る**)、中へ / 外へ・
呼び出しの積み重ねの表示(`ProgramResult.stack` は返す)、定義へ飛ぶ、引数(sys.argv)と時間の上限の画面からの設定、
Python → パイプライン(`python_to_hdev`)の入口。

2026-11-13 の 2 便目(同じ枝)で変えた物:

- 上の 2.(続行・1 行実行)は**止まった所から続ける**に変えた(§4 の `pause_hook`、`studio_pymode.PauseGate`)。
  止まっている間に文面を直したら、止まっている実行を終えて上から走り直す(出力の欄にそう書く)。
  関数の中で止まったら、その枠の局所変数も変数の欄に出す(書き換えはできない: 断る)。
- 実行時・検査・助言の文は UI の言語で出す(`studio_program_i18n`: 源の書式文字列を型にして値を取り出し、
  訳に埋め直す。訳は `studio_pyedit_i18n.json` の 5 言語、hi は英語)。例のプログラムと「新規」のコメント、
  起動時の案内(最初の 3 手)も UI の言語とモードに従う。
- 変数の欄での編集は実行の名前空間に届く。出力の欄は 5000 行まで(古い行から捨てる)。未保存の文面は 5 秒ごとに
  設定へ書き出す(落ちても次の起動で戻る)。
- 補完・ホバー・変数の一覧は、実行後の値のうち利用者のクラスの物については静的な情報だけを使う
  (`studio_pyedit_safe`)。jedi には数・文字列・numpy の配列・ライブラリのモジュールだけを渡す。

### 13.2 やり直しの効かない操作の確認・Undo / Redo・ファイルへの自動保存(2026-11-13、利用者の要件)

**確認の窓の線引き**: 利用者が自分で元に戻せる操作(段の操作の Undo、文面の Ctrl+Z、保存の窓そのものの
「置き換えますか」、ディスクに残っているファイルの開き直し)には窓を出さない。利用者が作った物を壊し、何も
それを戻さない操作だけ、入口(ボタン・メニュー)で 1 回聞く。文には何が失われるかを書き、既定のボタンは
キャンセル、「次から聞かない」は付けない(`studio.confirm_action` / `CONFIRM_ACTION_HOOK`。画面の無い実行では
実行しない側)。スクリプトから関数を直接呼ぶ道には窓を出さない。

| 操作(入口) | 失われる物 | 守り |
|---|---|---|
| 段を消す・動かす・切る・複製・つまみ・op を足す・Program を適用・全部消す・サンプルを読む(コンボ・ギャラリー) | 段の列 | Undo(Ctrl+Z)。全部消す・読み込みは未保存があれば確認も出る |
| パイプラインを開く・終了・dev_* のデモ・ヘルプの「sample:」 | 未保存の段・未適用の文面 | 確認(`confirm_discard`。Python のモードに居る間に退避した未適用の文面も数える)。デモとヘルプは Python の文面を置き換えず、パイプラインのモードへ切り替える |
| Program の「Reset」 | 未適用の編集 | **確認**(未適用の編集がある時だけ) |
| Program の「Sync」 | 文面のコメント・空行・for / if | **確認**(作り直すと消える物がある時だけ)。段の列を変えた時の自動の作り直しは聞かない(段の列が正本) |
| 固定: 3 つ目を固定(一番古い固定が押し出される)・「今の結果を採る」 | 固定した結果とそのパイプライン | **確認** |
| パネルの配置のリセット・保存したレイアウトの上書き・削除 | 今の配置・保存した配置 | **確認** |
| 最近使ったファイルの一覧を消す | 一覧 | **確認** |
| フォルダに適用(一括処理) | 既にある出力の画像(「上書き」の時)・summary.csv | **確認**(上書きされるファイルがある時だけ。件数を言う) |
| Python: 新規・開く・例を開く・「Python にする」(ファイルに未保存の変更がある時) | 未保存の文面 | 確認(保存する / 捨てる / やめる) |
| Python: 「Python にする」(無題の文面) | 前の文面 | Ctrl+Z の 1 回 |
| Python: 保存(外でファイルが変わっていた)・名前を付けて保存(拡張子を足した名前が既にある) | ディスクの版 | **確認**。それ以外の上書きは保存の窓が聞く |
| Python: 出力を消す | 出力の欄の文 | **確認**(空でない時) |
| Python: 実行中・ブレークポイントで待っている間に終了 | 実行の途中の結果 | **確認** |
| ウォッチの式を消す(「−」) | 式 | **確認** |
| 従来の Python エディタ: タブを閉じる(未保存)・保存(外でファイルが変わっていた) | 文面・ディスクの版 | 確認 |
| モードの切り替え | (何も失わない) | モードごとに文書を持つ。文面も Undo の履歴も残る |
| 画像を開く・フレーム B・デモ画像 | 今の入力の画像(作った物ではない) | 窓なし(開き直せる) |
| 止める・リセット(実行) | 実行の途中 | 窓なし(安全のための操作。走り直せる) |
| ブレークポイントの付け外し・最初の 3 手を閉じる・言語の切り替え | (すぐ元に戻せる) | 窓なし |
| プロジェクトの名前の変更・移動・新規 | (既存の物は上書きしない) | 上書きを断る。削除の操作は無い |

**Undo / Redo(コーディング中)**: Program 欄は打つ → Ctrl+Z → Ctrl+Y / Ctrl+Shift+Z が効く。モードごとに
`QTextDocument` を持ち、切り替えは `setDocument` で差し替えるだけなので、往復しても文面と履歴が残る。プログラムが
文面を書き換える操作(「Python にする」)は 1 つの編集で、Undo 1 回で戻る。ファイルを開いた・新規・例の直後は履歴が空。
Edit ▸ Undo / Redo は**フォーカスのある方**に効く(Program 欄 = 文面、それ以外 = 段の操作)。出来ない時は無効。
Program 欄の上にも「元に戻す / やり直し」のボタンがある。パイプラインのモードの文面は、段の列を変えるたびに段の列から
作り直すので(段の列が正本)、その時点で文面の履歴は消える(段の操作の Undo が履歴)。

**ファイルへの自動保存**: 既定は切。Run ▸ Program mode ▸ Autosave to the file か、設定の画面(Editor)で、
「打つのを止めてから N 秒後」(既定 2 秒、0.5〜600 秒)か「Program 欄からフォーカスが外れた時」を選ぶ。保存先の無い
文面(無題)には効かない。外でファイルが変わっていたら上書きせずに知らせる。構文が壊れている途中でも保存する。
実行はしない。信頼の台帳は変えない。書き方は原子的。保存した時は Program 欄の上に小さく出す(窓は出さない)。
5 秒ごとの退避(落ちた時の復元用)は、この設定に関係なく常に動く。

**第 3 回レビュー(2026-11-13)の直し**:

- **「外で変わったか」は生のバイトで決める**。開いた時・保存した時(自動保存も)に、ファイルの生のバイトの印
  (大きさと SHA-256)を持ち、今のディスクの印と比べる(文字にしない)。読めない時・比べる元が無い時は
  「変わった」(上書きしない側)。同じ中身の書き直しは「変わっていない」。外で消されたファイルは作り直す。
  前は UTF-8 の文字として先頭 4 MB を読んで比べ、読めない・解けない時は「変わっていない」としたので、外で
  cp932 / Latin-1 / UTF-16 で書き換えられたファイルや 4 MB を越えたファイルを、自動保存が聞かずに上書きし、
  保存も聞かなかった。従来の Python エディタの保存も同じ印で比べる。
- **パイプラインのファイルを開いたら、未適用の編集の状態を全部消す**(「捨てますか」に「捨てる」と答えた後)。
  編集欄にフォーカスがあっても、開いた段の列から Program の文面を作り直す(Undo の履歴も空になる)。Python の
  モードの側で持っていた「未適用」の印・パイプラインの文面のブレークポイントも消す。前は、捨てたはずの文面が
  Program に残り、Apply すると開いたパイプラインがその文面で置き換わった。Python のモードの間に開いても、
  Python の文面のブレークポイントは消さない。
- **既定のボタン**: 信頼の確認(「ファイルから来たプログラムを実行しますか」)と、従来の Python エディタのタブを
  閉じる窓も、既定のボタンと Esc がキャンセル側(前は Enter で「Run it」/「Yes(捨てる)」だった)。タブを閉じる
  窓は、終了の時と同じ確認(Discard / Cancel)を通す。試験は、既定の窓そのものを出して Enter / Esc を押す。
- **Undo と信頼**: 「Python にする」「Python のモードへ移す」を Ctrl+Z で戻した文面が、確認していないファイルの物
  なら、由来と信頼もそのファイルの物に戻る(§5)。

### 13.3 Program 欄がどちらの書き方かを常に見せる(2026-11-13、利用者の要件)

切り替えのボタンの押された状態に頼らず、4 か所で言う。

| 場所 | 出る物 | 出所 |
|---|---|---|
| Program 欄の左上の札 | 印(Python = ◆、パイプライン = ≡)+ モードの名前 + 色(色だけに頼らない) | `PyModeController.badge` / `badge_text()` |
| パネルの題 | `Program (code) — Python` / `Program (code) — Pipeline`(今の言語) | `mode_title()`(英語の原文は `mode_title_en()`) |
| 窓の下の状態の帯 | `Program: Python` | `win._mode_status` |
| 実行のボタン・ツールヒント・出力の見出し | 「Python として実行」、見出しに `(Python · Debug)` | `btn_run` / `_out_header` |
| F5 の入口(Run メニューの Run all・F5 / Ctrl+R の動作・Ctrl+Return のボタン) | Python のモードの間は「Python として実行」と、その説明 | `build_window` の `_pm_run_hints`(ctx の `run_hints`) |

- 札の色は `studio_pymode.BADGE_PALETTES`(`dark` / `light`)。文字と地のコントラスト比は 4.5 以上で、試験が測る
  (`contrast_ratio`)。配色を切り替える側は `set_badge_palette(name)` を呼ぶ。この版の Studio の配色は暗い側の
  1 つだけなので、`light` は用意と試験まで(明るい配色が入った時に繋ぐ)。
- **パネルの題の帯に状態を並べる側への覚え書き**: 題に出す文字列は `win._pymode.mode_title()` が返す。今は
  `build_window` の `_pm_panel_title`(ctx の `set_panel_title`)が、ドックの題そのものを書き換えている。題の帯に
  状態の欄が出来たら、`_pm_panel_title` の中身をその欄への書き込みに差し替える(呼ばれる時機はそのまま使える:
  モードの切り替え・ファイルを開く・変換・言語の切り替え)。
- **食い違い**: パイプラインのモードなのに Python らしい文面、またはその逆(`text_looks_like` =
  `studio_program.detect_syntax`。実行しない)の時は、札の前に ⚠ が付き、札の縁が琥珀になる。札を押すと選択肢が
  出る(「この文面を Python のモードへ移す」/「Python のモードへ切り替える」、逆は「この文面を Python に変換する」/
  「パイプラインのモードへ切り替える」)。勝手には切り替えない。移す・変換するは Ctrl+Z の 1 回で戻る。
  開いたパイプラインのファイルから来た文面を移した時は、そのファイルの信頼を引き継ぐ(初回の実行の前に確認)。
- **混ざっている**: 1 つの文面に 2 つの書き方が混ざっている時(`detect_syntax` の「混ざっている」、Python のモード
  では検査の `mixed_syntax` も)も ⚠ と琥珀の縁。ツールヒントが直す側の行(今のモードと違う書き方の行)を言い、
  札を押すと「N 行目へ移る」が先頭に出る(ほかはモードの切り替え、パイプラインのモードでは Python のモードへ移す)。
- **読み直す時機**: 札のために文面を読む(`detect_syntax`)のは、間を置いた検査(Python のモードの `check_now`、
  パイプラインのモードの構文の検査)・モードの切り替え・文書の差し替え・ファイルを開く・変換・移す、の時だけ。
  1 打ごと(`_update_labels`)には読まない(2,000 行の文面で 1 回 13 ms ほどかかるため)。パネルの題と F5 の入口の
  説明は、値が変わった時だけ送る(言語の表への登録し直しを 1 打ごとにしない)。
- Python のモードでは、Run メニューの「Python として実行」(= Run all。F5 / Ctrl+Return)と同じ動作の
  「Python のプログラムを実行」をメニューから隠す(同じ物を 2 つ並べない。コマンドパレットには残る)。
- パイプラインの印は U+2261(≡)。最初に使った U+2630(☰)は Segoe UI / Arial / DejaVu Sans / Noto Sans に無く、
  代わりの字を探さない環境(画面を持たない描画)では箱になった。
- コード欄の地の色や左端の帯をモードで変える案は入れていない(札・題・状態の帯で足りており、構文の色と競るため)。

## 14. 既存の「Python Editor」との関係

studio.py には既にスクリプトを走らせる欄がある(Python Editor、`Run (F5) executes the CURRENT tab with the
repo on PYTHONPATH`、インタプリタは設定の Execution ページ `interp`、空 = Studio の Python)。役割が違う:

| | Python Editor | Program 欄の Python のモード |
|---|---|---|
| 何を走らせるか | 任意のスクリプト(別プロセス) | パイプラインのプログラム(Studio のプロセスの中) |
| 結果 | 標準出力 | 記録した段の列・最後の画像・変数の表 |
| 画像 | 自分で読む | Studio の画像が `img` に入る |
| 止める | プロセスを止める | settrace の行の境目 |

将来は 1 つにまとめられる: Python Editor の「Run」に「Studio の中で記録つきで走らせる」を足し、書き出した
スクリプト(§11)を開いたら同じ実行系に渡す。別プロセスの実行は、重い・止められない op を確実に止めたい
ときの逃げ道として残す。

## 15. Qt を使う Python も呼べる(import と窓とスレッド)

1. **import は制限しない**。Studio と同じプロセス・同じ環境に入っている物は全部使える。入っていない物は
   `ModuleNotFoundError` をそのまま見せ、入れ方を 1 行で添える(`line 2: ModuleNotFoundError: No module
   named 'x' — install it into Studio's Python: "<sys.executable>" -m pip install x`、試験あり)。
2. **Qt の決まり**: Studio の `QApplication` が既にあるので、プログラムは `QApplication.instance()` を使い、
   新しく作らない・`app.exec()` を呼ばない。呼ばれたときに Studio が止まらないよう、Studio 側の層は
   Qt を直接使うプログラムの実行の間だけ `QApplication.exec` / `QCoreApplication.exit` / `quit` を
   「何もせず 0 を返し、助言に『Studio の中では exec() は要らない』と出す」物に差し替え、終わったら戻す
   (クラスの属性を一時的に替える。この段では実装しない)。
3. **どのスレッドで回すか**(実測、PySide6 offscreen、1024×1024、`measure_qt_threads.py`):

   | 案 | やり方 | 窓を出す例(20 枚) | 重い op のループ(median 0.9 + gaussian × 6) |
   |---|---|---|---|
   | A | 作業スレッドで回す。窓は前置きの `ui(fn, *args)`(GUI スレッドで実行して結果を返す)・`show_window(make_widget)` で出す | 1 枚あたり中央値 0.07 ms・最大 1.8 ms(BlockingQueued の往復) | GUI のタイマーの最長の間隔 **11 ms**(固まらない) |
   | B | GUI スレッドで回し、行フックで `processEvents` | 直接作れる | 行の間の最長 **817 ms 固まる**(median 1 回の C の呼び出しの間)。時間も 4.4 → 5.7 s |
   | C | 構文木で Qt の import を見つけたら GUI スレッド(B)、無ければ A | — | — |

   **既定は A**、Qt を直接 import するプログラムだけ C の規則で B に切り替える(`needs_gui_thread`)。
   A では止めるボタンも GUI も常に効く。B に落ちたプログラムには「`show_window` / `ui` を使えば
   作業スレッドで回せて固まらない」と助言する。
4. **PyQt5 / PyQt6 / PySide2** を同じプロセスで PySide6 と混ぜると落ちることがあるので、import を
   見つけたら助言 `qt_binding_mix`(行番号つき)で知らせる。止めはしない。
5. **窓を取り残さない**: `show_window` で開いた窓は記録(`ProgramResult.windows`)に残り、
   `close_program_windows(result)` で閉じる。Studio は実行の終わり(次の実行の前)・停止・Studio の終了で
   呼ぶ(UI の段)。プログラムが `show_window` を通さず直接作った窓は追えない(B のときは
   `QApplication.topLevelWidgets()` の実行前後の差で拾う案、未実装)。
6. **`studio_program.py` 本体は Qt を import しない**。GUI スレッドへの橋は差し込み口 `GUI_BRIDGE`
   (`call(fn, *args)` を持つ物。Studio 側の薄い層が `Signal` + `BlockingQueuedConnection` で作る。
   実測の版は `measure_qt_threads.py` の `Bridge`)。Studio の外では、`QApplication` が無ければ
   「ui(): no Qt application is running — …」で断り、main スレッドでなければ断る(試験あり)。
   `run_program` はどのスレッドから呼ばれても動く: 記録の先は contextvar(スレッドごと)、`settrace` も
   呼んだスレッドだけ、`print` は `sys.stdout` を差し替えずプログラムの名前空間の中だけで取り込む
   (作業スレッドで回している間に Studio 本体の出力を取り込まない。試験あり)。

## 16. 書いている最中の指摘・補完・ホバー(実行しない)

入口(Qt なし。別の枝のエディタの波線・Problems の欄が呼ぶので形を固定する):

- `check_program(text, *, known_ops=None, lang="en", syntax=None) -> list[Problem]`。
  `Problem(line, col, end_line, end_col, severity, code, message, hint, fix, params)`。行は 1 始まり、列は
  0 始まり(ast と同じ、文字単位)。`severity` は error / warning / hint。`code` は安定した短い識別子で訳の鍵、
  `message` / `hint` は英語が正(Studio が `tr()` を通す)、`params` は文に埋めた値。`fix` は機械で直せる
  ときだけ `{"line", "col", "end_line", "end_col", "text"}`(`apply_fix(text, fix)` が同じ置き換え)。
  `syntax` はエディタが知っているモード(Python のモードで `if x` と書けば「':' が無い」)。
- `checker_backends()` = 使える道具と、無い物で何が使えていないかの 1 行。
- `complete(text, line, col)` / `hover(text, line, col)`。
- **コードは実行しない**(`compile` と `ast` と字句の走査だけ、プログラムの import もしない)。
  500 行で 45 ms(試験の実測、2 回目以降。初回は op の表を作る)。

**層**(一般的な Python の検査は自作せず既存のパッケージ、Fullseye 固有の所だけ自作):

| 道具 | 使う所 | 無いとき | ライセンス | Python | 大きさ(この機械の実測) | import |
|---|---|---|---|---|---|---|
| 標準 `compile` / `ast` / `tokenize` / `difflib` | 最初の構文の誤り、Fullseye 固有の検査、緩い未定義の名前 | (常にある) | PSF | — | — | — |
| parso 0.8.7 | 2 件目以降の構文の誤り(壊れたコードでも読める) | 構文の誤りは 1 件だけ | MIT | 3.6+ | 0.8 MB | 74 ms |
| pyflakes 4.1.0 | 順序まで見る未定義の名前、使われない import・変数、再定義 | 未定義は「どこかで代入されていれば良し」の緩い判定、使われない import は出ない | MIT | 3.9+ | 0.9 MB | 4 ms |
| jedi 0.20.0 | 補完・ホバー・シグネチャ(numpy や入っているパッケージも) | 前置き・組み込み・文面の中の名前の前方一致だけ | MIT | 3.8+ | 26 MB(typeshed 込み) | 68 ms |
| pycodestyle 2.15.0 | (採らない) 書式の流儀の指摘。Studio の小さなプログラムには煩い | — | MIT | — | 0.1 MB | — |
| ruff 0.16.0 | (採らない) 速いが Rust の実行ファイルを別プロセスで呼ぶ形。31 MB、1 回の起動で 35 ms。pyflakes と jedi で足りる | — | MIT | — | 31 MB | — |

(大きさは site-packages の実測。Python の対応版は各パッケージの宣言の記憶で、この段では確かめていない。)

- **前置きの名前を教える橋**: pyflakes は `Checker(tree, builtins=前置きの名前)` で教える(行をずらさない =
  誤検出・行のずれが無い)。jedi は前置きを実行時に作るので静的に読めない → op ごとの `def` を並べた
  stub(`_fullseye_studio_prelude_stub.py`、一時の場所に一度だけ書く)を `added_sys_path` に置き、先頭に
  見えない `from … import *` を 1 行足して行を 1 つずらして戻す。
- **extras**: pyproject の `gui = ["PySide6>=6.5"]` が Studio 用の extra。案: `studio = ["PySide6>=6.5",
  "parso>=0.8", "pyflakes>=3.0", "jedi>=0.19"]`(必須の依存には足さない。この段では pyproject の extras を
  変えていない)。
- **試験**: 間違った例 29 件 → 期待する code・行・列、正しい例 30 件 → 指摘ゼロ(内包表記・lambda・with・try・
  global・nonlocal・del・walrus・型注釈・f 文字列・デコレータ・match・async・展開・前置きの全 964 op 名)、
  fix を当てたら compile が通る。parso / pyflakes / jedi を塞いだときに土台に落ちることと、ある時の動き
  (pyflakes は repo の外の venv で確認)。

**拾う物**(code):

| 種類 | code | 例 |
|---|---|---|
| 構文 | `missing_colon` `unclosed_bracket`(開いた行を指す) `unmatched_bracket` `unclosed_string` `indentation` `tabs_spaces` `missing_comma` `assign_in_condition`(`if x = 1`) `brace_block` `syntax_error`(Python の文のまま) | |
| 他言語の書き方 | `else_if` `c_operator`(`&&` `\|\|` `!`) `js_literal`(`true` `false` `null`) `semicolon`(hint) | fix つき |
| 全角 | `fullwidth_char`(括弧・カンマ・コロン・引用符・空白 …。文字列とコメントの中は対象外) | fix つき |
| 書き方の混入 | `mixed_syntax`(`endfor`・`* コメント`・`:=`・`op a b`)/ パイプラインのモードの文面は `pipeline_syntax`(今の解析器の誤り) | 「Convert to Python」へ案内 |
| 名前 | `undefined_name`(もしかして: difflib、fix つき)・`maybe_undefined`(分岐の片側でしか代入されない、warning)・pyflakes の `unused_import` `unused_variable` `redefined_unused`、それ以外は `pyflakes_<名前>` で元の文 | |
| op の呼び出し | `unknown_op`(`op("gausian")`) `missing_inputs` `too_many_args` `unknown_keyword` `knob_out_of_range`(warning、パイプラインの丸めと同じ文) `result_discarded`(測るだけの op、入力を明示した画像の op を文として書いた) | |
| 助言 | `unused_result` `loop_invariant` `duplicate` `type_mismatch` `qt_binding_mix`(`advise_program` と同じ物を hint で) | |

連鎖させない: 構文の誤りがあるときは構文の誤り(と全角の記号)だけ。最初の誤りの行と次の行の parso の誤り、
字下げの誤りは足さない(最大 5 件)。同じ行の同じ code は 1 件、`mixed_syntax` の行の他の指摘は出さない。

**指摘しないと決めた物**: 書式の流儀(行の長さ・空白。pycodestyle を採らない)、型の推論(mypy 相当)、
変数をつまみに渡したときの範囲(実行しないと分からない)、変数が入力かつまみか(`gaussian(img, s)` の `s`)、
他のモジュールの `*` import がある時の未定義の名前(中身が分からない)、`global` を使うプログラムの
「片側でしか代入されない」、ループの中で代入される名前のループ後の使用(0 回かもしれないが普通の書き方)。

## 17. 「Python の IDE」の受け入れ表との対応(`STUDIO_AS_PYTHON_IDE.md`)

実行系は「Program 欄 1 つ」を前提にしない: 実行の対象はファイル(`run_file(path, image)` /
`run_program(text, image, filename=path)`)、名前空間は実行ごとに作って結果に残す(`ProgramResult.namespace`)、
実行の間だけ実行するファイルの場所とプロジェクトの `programs/` を `sys.path` の先頭に足して終わったら戻す
(その間に読んだ利用者のモジュールは `sys.modules` から外す = 直して走り直すと読み直す。試験あり)、
例外は (ファイル, 行)(`error_file` / `error_line`。import した自分のモジュールの中の誤りはそのファイルの行を
`notes` に足す)。`sys.path` の差し替えはプロセス全体に効くので、2 つのプログラムを同時に別スレッドで
走らせると互いの道が見える(同時実行は UI 側で 1 本に絞る前提)。

### A4 補完・ホバー・シグネチャ・定義へ飛ぶ — 差し込み口だけ
`complete(text, line, col)` / `hover(text, line, col)` を入れた(jedi があれば jedi + 前置きの stub、無ければ
前置きと組み込みの名前)。シグネチャは hover の `signature`。**定義へ飛ぶ・エディタへの繋ぎは未着手**(別の枝)。

### A5 間違いの指摘 — 今回入れた(Qt なしの層)
`check_program` / `checker_backends` / `apply_fix`(§16)。波線と Problems の欄は別の枝(ide)。

### B1 実行 — 今回入れた(実行系)
ファイルを実行・止める(`stop_event`)・時間の上限(既定 30 秒)・作業フォルダ(`program_dir` / `project_dir`)。
**選んだ行だけ実行**は `evaluate(source, namespace)` を使える形(UI は別の枝)。**引数(sys.argv)は未着手**。

### B2 Debug — 一部
ブレークポイント(条件つき `conditions`)・1 行実行・続行(`pause_hook`: 止まった所から続く)、止まった所の変数
(`variables` と、関数の中なら `locals`)、呼び出しの積み重ね(`stack`。画面には関数の名前だけ)。
**中へ / 外へ・積み重ねの一覧の表示・import した別ファイルの中のブレークポイントは未着手**(tracer は実行した
ファイルだけを見る。1 行実行は関数の中へ入る)。

### B3 Release — 今回入れた(行フックなしまで)
`config="release"`(§4.1)。**関数単位のコンパイル(numba)は未着手・方式は実測済み**。Debug と結果が一致する
試験はある。

### B5 対話の窓 — 差し込み口だけ
`evaluate(source, namespace)`: 実行後の名前空間で式か文を評価(値・標準出力・誤り・足された op の記録)。
**窓・履歴・補完の繋ぎは未着手**。qtconsole を使うかは未決(ユーザーに聞く項目)。

### D1 画像の IDE ならでは — 今回入れた(実行系)
op の呼び出し → 記録(段・行・入出力の型と形・時間・cache の印・device)、メモ化で差分実行(§6)。
**サムネイルの欄・つまみ ↔ コードの値の往復の UI は未着手**(§13 に設計と見積もり)。

### D2 パイプラインとの往復 — 今回入れた(実行系)
`hdev_to_python` / `python_to_hdev`、`pipeline()` / `current_pipeline()` / `load_pipeline()`、
`fs.load_pipeline` / `fs.read_def` / `fs.write_def`(§8〜§10)。**「Python にする」ボタンは未着手**。

### D4 Qt を使う Python — 差し込み口だけ(Studio の中では未配線)
`ui()` / `show_window()` / `close_program_windows()` / `needs_gui_thread()` と橋の差し込み口 `GUI_BRIDGE`。
**Studio 側の橋・exec() の差し替えは未着手**(実測の試作のみ)。橋が無い間、Qt を直接 import するプログラムを
作業スレッドから走らせようとすると(Studio の Program 欄は常にこれ)、`run_program` は実行せずに
「line N: not run: this program imports Qt directly …」を返す(作業スレッドで QWidget を作るのは未定義の動作)。
main スレッドから直接呼ぶ使い方(Studio の外)は今までどおり動く。

## 18. やらないこと

- 従来のモードを廃止する。
- 部分集合の評価器(許可リストの自前の実行系)。構文の制限。
- メモリの上限(本物の Python なので)。
- 等価な書き換えの自動適用(§6.3)。助言の黙った適用。
- HDevelop の制御構文(`:=` や `while … endwhile`)を従来のモードに足すこと(変数と分岐は Python のモードで)。
- 新しいファイル形式・YAML・JSONC。MCP にファイルパスを受ける読み道具を足すこと。
- `fs.load` / `fs.save`(画像用)の意味を広げること。

## 19. 確かめられなかったこと

- HDevelop の公式文書の制御構文の頁を読み比べていない(§1)。
- メモ化してよいと判定した op が、呼んだ先の補助関数で乱数を使っていないことの全数(標本で確認)。
- 見張りが諦めて残したスレッドが、後で戻した大域の状態(sys.path など)に触れる場合: 残っている間は次の
  実行を断り、終わった所でもう一度戻す(2026-11-13)。残っている間に Studio 本体が変えた環境変数・作業フォルダも
  その時に実行前の値へ戻る(区別できない)。終わらない実行(C の中の無限ループ)は、Studio を起動し直すまで残る。
- 実際の Studio の窓での見え方(UI は入れていない)。
- 第 3 回レビューの直し(§4.4・§13.2)は、画面の無い実行(offscreen)と子プロセスで確かめた。実画面での既定の
  ボタンの見え方、Linux / macOS、matplotlib 3.10 以外の版(図が残っている時の backend の切り替え方が版で違う)は
  確かめていない。
- 案 A の橋を Studio の本物の窓で動かすこと(実測は offscreen の小さな試作。exec() の差し替えは未実装)。
