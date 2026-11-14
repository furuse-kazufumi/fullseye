# Studio のキーボードのショートカット(キーを自分で決める)

Fullseye Studio のショートカットキーは、利用者が自分で決められます。Visual Studio や VS Code の
「キーボード」の設定と同じ形で、コマンドごとにキーを変え、外し、元に戻し、ファイルに書き出して別の機械へ
持って行けます。キーの割り当ての正本は `studio_keymap.COMMANDS` の 1 つの表(登録簿)で、メニューの右に出る
キー・キーの一覧(`Ctrl+F1`)・設定の窓・この文書の表は、どれもそこから引いています
(試験 `tests/test_studio_keymap_2026_11_13.py` が、この文書の表と登録簿が 1 字も違わない事を確かめます)。

コードエディタの編集の操作(矩形選択・行の操作)の説明は [STUDIO_EDITOR_KEYS.md](STUDIO_EDITOR_KEYS.md) にあります。
そこに書いてあるキーは「Visual Studio 風」の型の既定で、この設定の窓で変えられます。

## 1. 設定のしかた

**開く**: Tools ▸ キーボードのショートカットの設定…(既定のキーは `Ctrl+K, Ctrl+S`。`Ctrl+K` を押してから
`Ctrl+S`)。キーの一覧(`Ctrl+F1`。Help ▸ Keyboard shortcuts)も同じ窓を開きます。コマンドパレット(`Ctrl+P`)で
「キー」「ショートカット」と打っても出ます。本体を止めない窓なので、開いたまま Studio を使えます。開いた時の
フォーカスは検索の欄です。起動の時に使えなかった設定や、今の言語では効かないキーがあれば、窓の上に一覧が出ます。
この窓では `Enter` でボタンは押されません(検索の欄や表で `Enter` を押しても、記録したキーは消えません)。表の行で
`Enter` を押すかダブルクリックすると、記録の欄へ移ります。`Esc` は、検索に文字があれば 1 回目は文字だけを消し、
もう 1 回で窓を閉じます。

**探す**: 上の欄に、コマンドの名前(日本語でも英語でも)・ID・範囲の名前を打つと表が絞られます。
`ctrl+d` のようにキーとして読める語を打つと、**そのキーを持つ行だけ**が出ます(`Ctrl+K` なら `Ctrl+K, …` の
2 打鍵のキーも)。`Ctrl-D`・`^D`・`C-d`(Emacs の書き方)もキーとして読みます。当たる物が無ければ例を出します。

**変える**:

1. 表の行を選ぶ。下に「今のキー」と、そのコマンドが効く範囲が出ます。
2. 「新しいキー」の欄をクリックして、キーを押す。押したキーがそのまま記録されます(記録の間は Studio の
   ほかのキーは働きません)。窓全体の範囲では、続けてもう 1 つ押すと 2 打鍵のキー(`Ctrl+K, Ctrl+S` の形)に
   なります。やり直すのは「消す」。欄の中では VS Code と同じく、修飾なしの `Enter` = 割り当てる、`Esc` = 記録を
   やめる(空の時はもう 1 回で表へ戻る)、`Tab` / `Shift+Tab` = 次の欄へ。`Tab`・`Esc`・`Enter` そのものを割り当てたい
   時は「Tab / Esc / Enter を記録」を押してから 1 打だけ押します。
3. 押した時点で、当たりと注意が下に出ます。**決める前に**分かります。
   * 赤(当たり): そのキーでは割り当てられません。「割り当てる」は押せません。相手のコマンドの名前と範囲が
     出るので、先に相手のキーを変えてください。**相手のキーを勝手に外す事はしません。**
   * 黄(注意): 割り当てられますが、OS や入力方式、ほかの配列のキーボードで問題になる事があります。
   * 灰(知っておく事): 範囲が違うので当たりではない同じキー(例: 「Program 欄では、Program 欄の検索が
     Ctrl+F を先に受ける」)。
4. 「割り当てる」(今のキーと入れ替える。外れる今のキーは、押す前に状態の欄に出ます)か「別のキーとして足す」
   (今のキーに足す。1 つのコマンドに 4 つまで)。

ほかのボタン: 「キーを外す」(そのコマンドのキーを全部無しにする。外した事も覚えます。記録の欄に今のキーの 1 つを
押すと「<キー> を外す」になり、そのキーだけを外します)/「型の既定に戻す」(そのコマンドだけ。戻すと別のコマンドと
当たる時は戻さずに相手を出します)/「全部を戻す…」(変えた物を全部、型の既定に戻す。変えた物が無い時は押せません)/
「読み込む…」「書き出す…」(4 章)。表の右端の「●」が、型の既定から変えた行です。

**確認の窓**(全部を戻す・型の切り替え・読み込みの置き換え)は、既定のボタンが「キャンセル」です。`Enter` だけ・
`Esc` では何も変わりません(実行のボタンは「全部を戻す」「型を切り替える」「置き換える」)。

**組み込みの行**(灰色)は、部品の中に直接書いてあるキーで、この版では変えられません。当たりの検査には入るので、
同じキーを別のコマンドに割り当てようとすると知らせます。

**型(プリセット)**: 上の「型」で「Visual Studio 風(既定)」と「VS Code 風」を切り替えます。切り替えても、
自分で変えたキーは残ります。新しい型と当たる物だけは外れるので、確認の窓に**外れる物の一覧を先に出します**。
型の箱は、フォーカスが無い時のマウスのホイールでは変わりません。

変えたキーはすぐに効き、すぐに保存されます(Visual Studio の「OK」に当たる手順はありません)。

## 2. 範囲の考え方

同じキーでも、どこにフォーカスがあるかで働きが変わります。例えば `Ctrl+D` は、段の一覧では「段の複製」、
コードエディタでは「行の複製」です。この 2 つは同時に効く場所が無いので、当たりではありません。

範囲は次のとおりです。「効く所」は、そこにフォーカスがある時にその範囲のキーが効く場所です。

| 範囲 | 効く所 | 仕組み | 2 打鍵 |
|---|---|---|---|
| 窓全体(`window`) | 窓全体、テキスト欄、段の一覧、Program 欄、Program 欄の検索欄、画像の窓 | Qt の表(QAction / QShortcut) | 使える |
| 段の一覧(`pipeline_list`) | 段の一覧 | Qt の表(QAction / QShortcut) | 使える |
| グラフィクス窓(`graphics_subwindow`) | 画像の窓 | Qt の表(QAction / QShortcut) | 使える |
| Program 欄(`program_editor`) | Program 欄 | 部品が自分で先に受ける | — |
| コードエディタ(`editor`) | Program 欄、Python エディタ | 部品が自分で先に受ける | — |
| コードエディタ(矩形選択の間)(`editor_box`) | Program 欄、Python エディタ | 部品が自分で先に受ける | — |
| 自前のコメントのキーを持たないコードエディタ(`editor_no_comment`) | Python エディタ | 部品が自分で先に受ける | — |
| Program 欄の検索欄(`program_find`) | Program 欄の検索欄 | 部品が自分で先に受ける | — |
| Python エディタの窓(`python_editor_window`) | Python エディタ | Qt の表(QAction / QShortcut) | 使える |
| 画像ビューアの窓(`image_viewer_window`) | 画像ビューア | Qt の表(QAction / QShortcut) | 使える |
| 3-D 表示(`view3d`) | 3-D 表示 | 部品が自分で先に受ける | — |
| テキスト欄(`text`) | テキスト欄、Program 欄、Program 欄の検索欄、Python エディタ | テキスト欄が先に取る標準のキー | — |
| テキスト欄(窓のキーが勝つ)(`text_lost`) | テキスト欄、Program 欄、Program 欄の検索欄、Python エディタ | 窓のキーが勝つと欄の操作が消える標準のキー | — |
| メニューバー(`menu_bar`) | 窓全体、テキスト欄、段の一覧、Program 欄、Program 欄の検索欄、画像の窓 | 今の言語のメニューバーのニーモニック | — |
| 他の言語のメニューバー(`menu_bar_other`) | 窓全体、テキスト欄、段の一覧、Program 欄、Program 欄の検索欄、画像の窓 | 他の言語のメニューバーのニーモニック | — |

当たりの決まり(`studio_keymap.find_conflicts`):

* **Qt の表どうし**(窓全体・段の一覧・別窓)が、1 か所で同じキーを持つと **当たり**。Qt はどちらを撃つか
  決められず、**両方とも効かなくなります**(Studio では以前、`Ctrl+Shift+O` が開く操作 2 つに重なって、
  どちらも効かなくなった事があります)。窓全体と段の一覧は、段の一覧の中で両方が効くので当たりです。
* **部品が先に受ける範囲**(Program 欄・コードエディタ・検索欄・3-D 表示)は、窓全体の同じキーより先に取ります。
  これは当たりではなく、知らせるだけです(Program 欄の `Ctrl+F` は欄の検索、ほかでは op の検索欄へ)。
  ただし、どこへ行っても先に取られて**一度も届かない**キーは当たりにします。部品の側のキーを変えて相手が一度も
  届かなくなる時も、割り当てる前に断ります(「相手のキーを奪う」)。
* **Python エディタの窓**に矩形選択の部品を付けるかは配線で選べます(付けなくてもよい)。Qt なしの検査と読み込みの
  既定は「付いている」として厳しく数え、本物の窓では本当に付いている部品から数えます。
* **同じエディタの部品どうし**(Program 欄の操作と矩形選択の操作)が同じキーを持つと当たり。片方が黙って負けます。
  ただし「箱がある時だけ」「検索の帯が出ている時だけ」のように、働く場面が別々に決まっている物どうしは共用できます
  (`Esc`)。
* **2 打鍵のキー**は、Qt の表で動く範囲(窓全体・段の一覧・別窓)だけで使えます。エディタの部品はキーを 1 打ずつ
  見ているので、エディタの範囲では 1 打のキーだけです。`Ctrl+K` と `Ctrl+K, Ctrl+S` のように**始めが同じ**キーは、
  片方が押せなくなるので当たりです。
* **メニューバーのニーモニック**(`Alt+F` = File など)も当たりの相手に入ります。今の言語の物は当たり(メニューが
  取り、コマンドには届きません)、ほかの言語の物は注意(英語で `Alt+D` を付けると「ドイツ語では Datei のメニュー」と
  出ます)。言語を切り替えたら表全体を調べ直し、その言語で効かなくなったキーを状態行と設定の窓で知らせます
  (キーは外しません)。7 言語のどれでも、メニューバーの 7 つのニーモニックは重なりません(ドイツ語の Ausführen は
  `Alt+U`)。
* **テキスト欄の標準のキー**(`Ctrl+Z`、`Ctrl+A`、`Home` など)は 2 つに分かれます。欄が先に取る物(`Ctrl+A`・
  `Ctrl+C`・`Home` …)は、窓全体に同じキーを割り当てても欄の中では欄が勝つので、知らせるだけです。窓のキーが勝って
  **欄の操作が消える**物(`Ctrl+Backspace`・`Ctrl+Del`・`PgUp`/`PgDown`、1 行の欄の `Up`/`Down`/`Shift+Down` …)は
  注意を出します。どちらに入るかは、本物の欄(QPlainTextEdit と QLineEdit)にキーを送って確かめています。
  エディタの部品のコマンドが欄の標準のキー(コピー・貼り付け・元に戻す …)を取る時も注意です。
* **修飾なしの移動・削除・取り消しのキー**(矢印・`PgUp`/`PgDown`・`Home`/`End`・`Backspace`/`Del`/`Ins`/`Esc`)は、
  窓全体・段の一覧・図の窓・Python エディタの窓には割り当てられません(一覧と入力欄で効かなくなるため)。
  型の既定(段の一覧の `Home` = 最初へ・`Del` = 段を削除、画像だけを抜ける `Esc`)はそのままです。
* **修飾なしの文字キー**(`F`、`1`、Shift だけを付けた文字、`Space`、`Return`)は、文字を打たない窓
  (画像ビューア・3-D 表示)でしか割り当てられません。ほかでは文字の入力を奪うためです。

予約のキー(`studio_keymap.reserved`):

* 割り当てられない: `Alt+Tab`、`Alt+Esc`、`Ctrl+Esc`、`Ctrl+Alt+Del`、`Ctrl+Shift+Esc`、Windows キー(Meta)の付く物。
  OS が先に取り、Studio には届きません。
* 注意を出す: `Alt+F4`(窓が閉じる)、`Alt+Space`(窓のメニュー)、`F10`・`Shift+F10`(メニューバー・右クリック)、
  `Print`、`Ctrl+Alt+` 文字(AltGr のある配列 = ドイツ語・フランス語・ポーランド語などでは、AltGr が Ctrl+Alt として
  届き、文字の入力と取り合います。Studio の既定の `Ctrl+Alt+M` なども同じ注意が出ます)、`Ctrl+Alt+` 矢印
  (ドライバによっては画面が回る。Linux では作業領域の切り替え)、`Ctrl+Alt+F1`〜`F12`(Linux の文字のコンソール)、
  `Ctrl+Alt+T`(Linux の端末)、`Ctrl+Space`・`Shift+Space`・`Ctrl+.`・``Alt+` ``・`Ctrl+Shift+F`(入力方式 = IME の
  切り替え。中国語の IME は `Ctrl+Space` で入力方式を切り替えます)。

## 3. 2 つの型の全部のキー

**Visual Studio 風(既定)** は、Studio の今までのキーを元に、同じキーはどこでも同じ意味になるように少し直した物です
(2026-11-13: `F1` = ここのヘルプ、`Ctrl+F1` = キーの一覧、`Shift+F1` = op の一覧、コードの欄の `Ctrl+S` =
プログラム / パイプラインの保存、やり直しの表示は `Ctrl+Y`(`Ctrl+Shift+Z` も効く)、拡大は `Ctrl+=` と `Ctrl++`、
holdout の検証は `Ctrl+Alt+H`(`Ctrl+H` はコードの欄の置換だけ)、画像だけを抜ける `Esc` は画像だけの間だけ)。
Visual Studio と同じなのは、エディタの `Ctrl+D` = 行の複製、`Alt+Shift+.` = 次の一致を選択に足す、
`Alt+Shift+矢印` = 矩形選択、`Ctrl+]` = 対応する括弧、`F1` = ヘルプ、`F5` = 実行、`F9` = ブレークポイント、
`Ctrl+Y` = やり直し、`Ctrl+,` = 設定などです。Visual Studio と違う所もあります
(1 段進むは `F6`。Visual Studio の「ステップ オーバー」は `F10`)。名前は「Visual Studio の流儀に寄せた
Studio の既定」という意味で、Visual Studio のキーを全部写した物ではありません。

**VS Code 風** は、次の行だけを VS Code の既定に合わせた型です(ほかは Visual Studio 風と同じ)。VS Code では
`F1` がコマンドパレットなので、この型の「ここのヘルプ」は `Ctrl+F1` です。

| ID | 操作 | Visual Studio 風(既定) | VS Code 風 |
|---|---|---|---|
| `palette` | コマンドパレット… | `Ctrl+P` | `Ctrl+Shift+P` / `F1` |
| `find_panel` | パネルを探す… | `Ctrl+Shift+P` | `Ctrl+P` |
| `shortcuts` | キーボードショートカット | `Ctrl+F1` | `Ctrl+K, Ctrl+R` |
| `help_here` | ここのヘルプ | `F1` | `Ctrl+F1` |
| `dbg_step` | 1 段進む(どの欄からでも) | `F6` | `F10` |
| `editops_box_up` | 矩形選択を上へ広げる | `Alt+Shift+Up` / `Ctrl+Alt+Up` | `Ctrl+Alt+Shift+Up` / `Ctrl+Alt+Up` |
| `editops_box_down` | 矩形選択を下へ広げる | `Alt+Shift+Down` / `Ctrl+Alt+Down` | `Ctrl+Alt+Shift+Down` / `Ctrl+Alt+Down` |
| `editops_box_left` | 矩形選択を左へ広げる | `Alt+Shift+Left` | `Ctrl+Alt+Shift+Left` |
| `editops_box_right` | 矩形選択を右へ広げる | `Alt+Shift+Right` | `Ctrl+Alt+Shift+Right` |
| `editops_multi_add_next` | 次の一致を選択に足す | `Alt+Shift+.` | `Ctrl+D` |
| `editops_line_duplicate` | 行を複製 | `Ctrl+D` | `Alt+Shift+Down` |
| `editops_bracket_jump` | 対応する括弧へ移動 | `Ctrl+]` | `Ctrl+Shift+\` |

全部のコマンド(112 個。★ は 2 つの型で違う行。「—」はキー無し = 自分で割り当てられる):

| ID | 操作 | 範囲 | Visual Studio 風(既定) | VS Code 風 |
|---|---|---|---|---|
| `open_image` | 画像を開く… | 窓全体 | `Ctrl+O` | `Ctrl+O` |
| `image_viewer` | 画像ビューア… | 窓全体 | `Ctrl+Shift+I` | `Ctrl+Shift+I` |
| `demo` | 合成デモ | 窓全体 | — | — |
| `open_pipeline` | パイプラインを開く… | 窓全体 | `Ctrl+Shift+O` | `Ctrl+Shift+O` |
| `save_pipeline` | パイプラインを保存… | 窓全体 | `Ctrl+Shift+S` | `Ctrl+Shift+S` |
| `export` | 書き出し… | 窓全体 | `Ctrl+E` | `Ctrl+E` |
| `code_to_editor` | パイプラインをコードとしてエディタへ | 窓全体 | `Ctrl+Shift+E` | `Ctrl+Shift+E` |
| `project_open` | フォルダを開く… | 窓全体 | — | — |
| `project_new` | 新しいプロジェクト… | 窓全体 | — | — |
| `project_panel` | プロジェクト | 窓全体 | `Ctrl+Shift+J` | `Ctrl+Shift+J` |
| `samples` | サンプルとコード… | 窓全体 | — | — |
| `save_result` | 結果を保存… | 窓全体 | `Ctrl+S` | `Ctrl+S` |
| `save_view` | 表示のまま保存… | 窓全体 | — | — |
| `copy_result` | 結果画像をコピー | 窓全体 | — | — |
| `quit` | 終了 | 窓全体 | `Ctrl+Q` | `Ctrl+Q` |
| `pymode_new` | 新しい Python のプログラム | 窓全体 | `Ctrl+N` | `Ctrl+N` |
| `pymode_open` | Python のプログラムを開く… | 窓全体 | `Ctrl+Alt+O` | `Ctrl+Alt+O` |
| `pymode_save` | Python のプログラムを保存 | 窓全体 | `Ctrl+Alt+S` | `Ctrl+Alt+S` |
| `pymode_save_as` | 名前を付けて Python のプログラムを保存… | 窓全体 | `Ctrl+Alt+Shift+S` | `Ctrl+Alt+Shift+S` |
| `undo` | 元に戻す | 窓全体 | `Ctrl+Z` | `Ctrl+Z` |
| `redo` | やり直す | 窓全体 | `Ctrl+Y` / `Ctrl+Shift+Z` | `Ctrl+Y` / `Ctrl+Shift+Z` |
| `pin_a` | A として固定 | 窓全体 | `Ctrl+Shift+A` | `Ctrl+Shift+A` |
| `clear` | パイプラインを空にする | 窓全体 | `Ctrl+Shift+Backspace` | `Ctrl+Shift+Backspace` |
| `focus_search` | op 検索欄へ移動 | 窓全体 | `Ctrl+F` | `Ctrl+F` |
| `zoom_in` | 拡大 | 窓全体 | `Ctrl+=` / `Ctrl++` | `Ctrl+=` / `Ctrl++` |
| `zoom_out` | 縮小 | 窓全体 | `Ctrl+-` | `Ctrl+-` |
| `fit` | 窓に合わせる | 窓全体 | `Ctrl+0` | `Ctrl+0` |
| `actual_size` | 実寸 (1:1) | 窓全体 | `Ctrl+Alt+1` | `Ctrl+Alt+1` |
| `surface_3d` | 3D 曲面 | 窓全体 | `Ctrl+Alt+3` | `Ctrl+Alt+3` |
| `viewer_3d` | 3D ビューア… | 窓全体 | `Ctrl+Alt+4` | `Ctrl+Alt+4` |
| `run_all` | すべて実行 | 窓全体 | `Ctrl+Return` | `Ctrl+Return` |
| `run_selection` | 選んだ行だけ実行 | 窓全体 | `Ctrl+Alt+Return` | `Ctrl+Alt+Return` |
| `dbg_run` | 全部を実行(どの欄からでも) | 窓全体 | `F5` / `Ctrl+R` | `F5` / `Ctrl+R` |
| `dbg_step` | 1 段進む(どの欄からでも) ★ | 窓全体 | `F6` | `F10` |
| `dbg_reset` | 最初に戻す(どの欄からでも) | 窓全体 | `Shift+F5` | `Shift+F5` |
| `batch_apply` | この処理をフォルダに適用… | 窓全体 | — | — |
| `verify_exported` | 書き出した Python を検証… | 窓全体 | `Ctrl+Shift+R` | `Ctrl+Shift+R` |
| `holdout` | 検証用の画像で確かめる… | 窓全体 | `Ctrl+Alt+H` | `Ctrl+Alt+H` |
| `pymode_python` | Python のモード | 窓全体 | — | — |
| `pymode_pipeline` | パイプラインのモード | 窓全体 | — | — |
| `pymode_toggle` | Python / パイプラインのモードを切り替え | 窓全体 | `Ctrl+Alt+M` | `Ctrl+Alt+M` |
| `pymode_convert` | Python にする | 窓全体 | — | — |
| `pymode_debug` | Debug(デバッグ) | 窓全体 | — | — |
| `pymode_release` | Release(リリース) | 窓全体 | — | — |
| `pymode_config_toggle` | Debug / Release を切り替え | 窓全体 | `Ctrl+Alt+D` | `Ctrl+Alt+D` |
| `pymode_example` | Python の例を開く | 窓全体 | — | — |
| `pymode_clear_output` | 出力を消す | 窓全体 | — | — |
| `pymode_run` | Python のプログラムを実行 | 窓全体 | — | — |
| `pymode_step` | 1 行進む | 窓全体 | — | — |
| `pymode_stop` | プログラムを止める | 窓全体 | `Ctrl+F2` | `Ctrl+F2` |
| `pymode_breakpoint` | ブレークポイントを付ける / 外す | 窓全体 | `F9` | `F9` |
| `pymode_condition` | ブレークポイントの条件… | 窓全体 | — | — |
| `work_mode_build` | 処理を組む | 窓全体 | `Ctrl+1` | `Ctrl+1` |
| `work_mode_compare` | 結果を比べる | 窓全体 | `Ctrl+2` | `Ctrl+2` |
| `work_mode_inspect` | 数値を調べる | 窓全体 | `Ctrl+3` | `Ctrl+3` |
| `work_mode_code` | コードにする | 窓全体 | `Ctrl+4` | `Ctrl+4` |
| `image_focus` | 画像だけ大きく | 窓全体 | `F11` | `F11` |
| `leave_image_focus` | 画像だけ大きくを終了 | 窓全体 | `Esc` | `Esc` |
| `find_panel` | パネルを探す… ★ | 窓全体 | `Ctrl+Shift+P` | `Ctrl+P` |
| `new_graphics_window` | 新しいグラフィクスウィンドウ | 窓全体 | `Ctrl+G` | `Ctrl+G` |
| `detach_graphics` | グラフィクス窓を切り離す | 窓全体 | `Ctrl+Shift+D` | `Ctrl+Shift+D` |
| `reattach_graphics` | グラフィクス窓を戻す | 窓全体 | — | — |
| `palette` | コマンドパレット… ★ | 窓全体 | `Ctrl+P` | `Ctrl+Shift+P` / `F1` |
| `feature_inspection` | 特徴量の検査… | 窓全体 | `Ctrl+F5` | `Ctrl+F5` |
| `ledger_run` | 台帳の op を実行… | 窓全体 | `Ctrl+Shift+L` | `Ctrl+Shift+L` |
| `system_settings` | 環境設定… | 窓全体 | `Ctrl+,` | `Ctrl+,` |
| `keyboard_settings` | キーボードのショートカットの設定… | 窓全体 | `Ctrl+K, Ctrl+S` | `Ctrl+K, Ctrl+S` |
| `editops_howto` | 矩形選択の使い方… | 窓全体 | — | — |
| `help_here` | ここのヘルプ ★ | 窓全体 | `F1` | `Ctrl+F1` |
| `op_reference` | op リファレンス… | 窓全体 | `Shift+F1` | `Shift+F1` |
| `quick_guide` | クイックガイド (en/ja/zh) | 窓全体 | `Shift+F2` | `Shift+F2` |
| `shortcuts` | キーボードショートカット ★ | 窓全体 | `Ctrl+F1` | `Ctrl+K, Ctrl+R` |
| `about` | Fullseye Studio について | 窓全体 | — | — |
| `remove` | 段を削除 | 段の一覧 | `Del` | `Del` |
| `duplicate_stage` | 段を複製 | 段の一覧 | `Ctrl+D` | `Ctrl+D` |
| `bypass` | 段をバイパス(入/切) | 段の一覧 | `Ctrl+B` | `Ctrl+B` |
| `move_up` | 段を上へ | 段の一覧 | `Ctrl+Up` | `Ctrl+Up` |
| `move_down` | 段を下へ | 段の一覧 | `Ctrl+Down` | `Ctrl+Down` |
| `move_top` | 段を先頭へ | 段の一覧 | `Ctrl+Shift+Up` | `Ctrl+Shift+Up` |
| `move_bottom` | 段を末尾へ | 段の一覧 | `Ctrl+Shift+Down` | `Ctrl+Shift+Down` |
| `reset` | 最初に戻す | 段の一覧 | `Home` | `Home` |
| `step` | 1 段進める | 段の一覧 | `Ctrl+Right` | `Ctrl+Right` |
| `program_find` | Program 内を検索 | Program 欄 | `Ctrl+F` | `Ctrl+F` |
| `program_replace` | Program 内を置換 | Program 欄 | `Ctrl+H` | `Ctrl+H` |
| `program_find_next` | Program 内で次を検索 | Program 欄 | `F3` | `F3` |
| `program_find_prev` | Program 内で前を検索 | Program 欄 | `Shift+F3` | `Shift+F3` |
| `program_comment` | 行コメントの付け外し | Program 欄 | `Ctrl+/` | `Ctrl+/` |
| `program_font_bigger` | エディタの文字を大きく | Program 欄 | `Ctrl++` / `Ctrl+=` | `Ctrl++` / `Ctrl+=` |
| `program_font_smaller` | エディタの文字を小さく | Program 欄 | `Ctrl+-` | `Ctrl+-` |
| `program_save` | プログラムを保存(コードの欄) | Program 欄 | `Ctrl+S` | `Ctrl+S` |
| `editops_box_up` | 矩形選択を上へ広げる ★ | コードエディタ | `Alt+Shift+Up` / `Ctrl+Alt+Up` | `Ctrl+Alt+Shift+Up` / `Ctrl+Alt+Up` |
| `editops_box_down` | 矩形選択を下へ広げる ★ | コードエディタ | `Alt+Shift+Down` / `Ctrl+Alt+Down` | `Ctrl+Alt+Shift+Down` / `Ctrl+Alt+Down` |
| `editops_box_left` | 矩形選択を左へ広げる ★ | コードエディタ | `Alt+Shift+Left` | `Ctrl+Alt+Shift+Left` |
| `editops_box_right` | 矩形選択を右へ広げる ★ | コードエディタ | `Alt+Shift+Right` | `Ctrl+Alt+Shift+Right` |
| `editops_multi_add_next` | 次の一致を選択に足す ★ | コードエディタ | `Alt+Shift+.` | `Ctrl+D` |
| `editops_box_cancel` | 矩形選択をやめる | コードエディタ(矩形選択の間) | `Esc` | `Esc` |
| `editops_line_duplicate` | 行を複製 ★ | コードエディタ | `Ctrl+D` | `Alt+Shift+Down` |
| `editops_line_move_up` | 行を上へ移動 | コードエディタ | `Alt+Up` | `Alt+Up` |
| `editops_line_move_down` | 行を下へ移動 | コードエディタ | `Alt+Down` | `Alt+Down` |
| `editops_line_delete` | 行を削除 | コードエディタ | `Ctrl+Shift+K` | `Ctrl+Shift+K` |
| `editops_line_comment` | 行コメントの切り替え | 自前のコメントのキーを持たないコードエディタ | `Ctrl+/` | `Ctrl+/` |
| `editops_line_indent` | 字下げ | コードエディタ | `Tab` | `Tab` |
| `editops_line_outdent` | 字下げを戻す | コードエディタ | `Shift+Tab` | `Shift+Tab` |
| `editops_bracket_jump` | 対応する括弧へ移動 ★ | コードエディタ | `Ctrl+]` | `Ctrl+Shift+\` |
| `editops_edit_trim` | 行末の空白を削除 | コードエディタ | — | — |
| `python_editor_run` | 実行(Python エディタ) | Python エディタの窓 | `F5` | `F5` |
| `python_editor_save` | 保存(Python エディタ) | Python エディタの窓 | `Ctrl+S` | `Ctrl+S` |
| `python_editor_ledger_op` | カーソルの語の台帳 op(Python エディタ) | Python エディタの窓 | `Ctrl+Shift+L` | `Ctrl+Shift+L` |
| `image_viewer_fit` | 窓に合わせる(画像ビューア) | 画像ビューアの窓 | `F` | `F` |
| `image_viewer_actual_size` | 1:1(画像ビューア) | 画像ビューアの窓 | `1` | `1` |
| `image_viewer_next` | 次の画像(画像ビューア) | 画像ビューアの窓 | `Right` | `Right` |
| `image_viewer_previous` | 前の画像(画像ビューア) | 画像ビューアの窓 | `Left` | `Left` |

組み込み(13 個。この版では変えられない。当たりの検査と一覧のために載せている):

| ID | 操作 | 範囲 | キー |
|---|---|---|---|
| `fixed_program_run_selection` | 選んだ Program の行だけ実行(選びがある時) | Program 欄 | `Ctrl+Return` |
| `fixed_program_close_find` | 検索の帯を閉じる(出ている時) | Program 欄 | `Esc` |
| `fixed_complete` | 語を補完(Python) | コードエディタ | `Ctrl+Space` |
| `fixed_find_close` | 検索欄: 閉じる | Program 欄の検索欄 | `Esc` |
| `fixed_find_next` | 検索欄: 次の一致 | Program 欄の検索欄 | `F3` / `Return` |
| `fixed_find_prev` | 検索欄: 前の一致 | Program 欄の検索欄 | `Shift+F3` / `Shift+Return` |
| `fixed_find_switch` | 検索欄: 検索 / 置換 | Program 欄の検索欄 | `Ctrl+F` / `Ctrl+H` |
| `fixed_view3d_first_person` | 3-D 表示: 一人称 | 3-D 表示 | `F` |
| `fixed_view3d_move` | 3-D 表示: 移動(一人称) | 3-D 表示 | `W` / `A` / `S` / `D` / `E` / `Q` / `Space` |
| `fixed_view3d_fov` | 3-D 表示: 視野角 | 3-D 表示 | `+` / `=` / `]` / `-` / `[` |
| `fixed_view3d_reset` | 3-D 表示: 元に戻す | 3-D 表示 | `R` |
| `fixed_view3d_wireframe` | 3-D 表示: 線画 | 3-D 表示 | `W` |
| `fixed_mdi_close` | 画像の窓を閉じる(Qt) | グラフィクス窓 | `Ctrl+F4` / `Ctrl+W` |

## 4. 保存の場所と形式

* **場所**: Studio の設定の鍵 `keymap/user` の 1 つ。Windows はレジストリ
  `HKEY_CURRENT_USER\Software\Fullseye\Studio`(その下の `keymap` の `user`)、Linux は
  `~/.config/Fullseye/Studio.conf`。環境変数 `FULLSEYE_STUDIO_SETTINGS` に INI のパスがあればそのファイル
  (試験はこれで利用者の設定に触れない)。
* **保存するのは型との差分だけ**です。型の既定と同じキーに戻したコマンドは消え、何も変えていなければ鍵ごと消えます。
  キーを外した事は空の並び `[]` で覚えます。
* **形式**(書き出しのファイルも同じ。UTF-8、改行は LF):

```json
{
  "bindings": {
    "editops_line_duplicate": ["Ctrl+F9"],
    "keyboard_settings": ["Ctrl+K, Ctrl+K"],
    "quit": []
  },
  "format": "fullseye-studio-keymap",
  "preset": "vscode",
  "version": 1
}
```

  キーの書き方は 1 つで、Qt がメニューの右に出す書き方です(`Ctrl+Shift+K`・`Alt+Shift+Up`。修飾は Meta・Ctrl・Alt・
  Shift の順。2 打鍵は `, ` で区切る)。設定の窓・当たりの文・この文書の表・保存の形が同じ字です。読む時はどの順で
  書いてあっても読みます(`Shift+Alt+Up` と書いた古いファイルも)。
  言語や OS で変わる表示用の書き方(ドイツ語の `Strg` など)は保存に使いません(読む時は `Strg` も読めます)。
* **壊れていた時**: 起動は止めません(型の違う値・深すぎる入れ子・重なった鍵でも)。読めない設定は型の既定で
  起動し、読めない分(知らない ID・読めないキー・当たる物)だけを使わずに、状態行に 1 行で知らせます(数は使えな
  かった上書きの数。注意だけの物は当てていて、起動では言いません)。**起動では設定を書き直しません**。キーを
  変えて保存する時に、使えなかった元の文字列を `keymap/user.backup` に 1 つ残してから書きます。
* **新しい版の設定**(`version` が 1 より大きい = 新しい Studio が書いた物)は読まずにそのまま残し、型の既定で
  起動します(版を戻しても設定が消えません)。
* **読み込み**(`読み込む…`)は fail-closed です。次のどれか 1 つでもあれば、**何も当てずに**理由の一覧を出します:
  JSON でない / 入れ子が 32 段より深い / 同じ鍵が 2 回ある / `format` が違う / `version` が 1 でない / 知らない項目 /
  知らない型 / 知らないコマンドの ID / 組み込みのコマンド / キーが文字の並びでない / 読めないキー / 予約で割り当て
  られないキー / 当たり / 256 KB を超える / コマンドの数より多い行。注意(黄)だけの物は当てて、注意を出します。
  理由の文に出すファイルの中の文字は、制御文字・書字方向の文字を符号(`U+202E` なら `\u202e`)に直して 40 字で切ります。
* 今の表に変えた物がある時は、置き換える前に確認の窓(置き換える数・型の変化・ファイルに無くて既定に戻る物)を
  出し、置き換える前の表を `keymap/user.previous` に 1 世代残します。書き出しは一時ファイルに書いてから置き換え、
  書けなければ警告の窓で知らせます。

## 5. 文の中のキーと、既知の制約

* メニュー・ツールチップ・状態行の文に既定のキーが書いてある所があります(`Run all (F5 / Ctrl+R)` など)。
  メニューの項目(`QAction`)の文とツールチップは、キーを変えると今のキーへ書き換えます(言語を切り替えた後も)。
  ボタンの文(画像ビューアの `Fit (F)` など)・状態行の文・案内の文は、まだ既定のキーのままです
  (Studio 本体の文からキーを外し、表示する時に今のキーを付ける変更が要ります)。
* **帯のボタンのツールヒント**(上の帯の Open image・Run all・Export・Pin as A、作業モードの 4 つ、Image focus、
  Find panel など 12 個)は「名前 — 何が起きるか (キー)」の形です。キーは文に書いてあるのではなく登録簿の今のキーを
  付けているので、キーを変えると変わり、キーを外すと括弧ごと消えます(ドイツ語の文では `Strg+Umschalt+A` の書き方)。
* **Edit メニュー**は、同じ意味の項目を 1 つにしてあります。「複製」(`Ctrl+D`)は 1 項目で、最後にフォーカスがあったのが
  コードの欄なら行の複製、それ以外は段の複製です(右に出るキーとツールヒントは、メニューを開いた時の場面の物)。
  行コメントの付け外し(`Ctrl+/`)も 1 項目です。コードの欄の右クリックのメニューには、行の複製と行コメントの切り替えが
  今までどおり出ます。`Ctrl+F` の 2 項目(op の検索欄へ / Program 内を検索)を 1 項目にするのは次の版です。
* 矩形選択の部品が Edit メニューに足す 3 つのサブメニューと、コマンドパレットの入口・「矩形選択の使い方」の窓は、
  言語の切り替えとキーの変更に追従します(「使い方」の窓のボタンも今の言語)。
* キーの一覧(`Ctrl+F1`)は、この設定の窓を開きます(古いモーダルの表は出しません。全部のキー・範囲・組み込みの
  キーが出て、検索できます)。
* `F1` = ここのヘルプ: コードの欄ではカーソルの下の op、段の一覧にフォーカスがあれば選んだ段の op、ほかでは
  op の一覧で選んでいる op、何も選んでいなければキーの一覧。`Shift+F1` はどこでも op の一覧(コードの欄でも)。
* まだしていない事(1.3): 窓全体の `Ctrl+S` の意味(前にある文書を保存)、`Tab`・`Ctrl+Tab`・`Alt+F7`、
  Visual Studio 風の型の実行・デバッグのキーを本物の Visual Studio に合わせる事、同じメニューの `Ctrl+F`・`Ctrl+=`・
  `Ctrl+-` の 2 項目ずつを 1 項目にする事。
* 配列: `Alt+Shift+.` のような記号のキーは US 配列の位置で数えています。JIS 配列では `=` `+` `\` などの
  Shift の要否が違い、ドイツ語の配列では `/` が `Shift+7`、`]` が `AltGr+9` です。実機の配列での確認は
  まだしていません(試験は offscreen で、キーの番号を直接送っています)。
* 入力方式(IME): 記録の欄は IME を受けません(変換中の文字はキーとして記録しません)。IME がオンでテキスト欄に
  フォーカスがある時、修飾なしの文字キーは変換の入力になるので、そのようなキーは文字を打たない窓だけに限っています。
* 言語を切り替えても、キーはそのままです。メニューの右のキーは Qt の書き方(`Ctrl`)で出ます(Studio は Qt の
  訳を読み込んでいないため、ドイツ語でも `Strg` になりません)。設定の窓・この文書の表・保存したファイルも同じ字です
  (修飾は Meta・Ctrl・Alt・Shift の順 = `Alt+Shift+Up`。4 章)。

## 6. 開発者向け

本体への取り付け(`studio.py` の `build_window` の最後、`studio_pymode.install` と矩形選択の取り付けの後):

```python
import studio_keymap_qt as kq
win._keymap = kq.install(win, settings=_settings, tr=tr, lang=lambda: _UI_LANG.get("code", "en"),
                         palette_words=PALETTE_WORDS, model=model)
```

`model` は F1 で選んだ段の op を引くため(無ければ `win._pymode.model`)。Python エディタの窓にも矩形選択の部品を
付ける配線なら `python_editor_editops=True` を渡します(渡さなければ、開いている Python エディタを見て決めます)。

* コマンドを足したら、登録簿 `studio_keymap.COMMANDS` に 1 行足します。`win._actions` に載っているのに登録簿に
  無い action があると、試験(`test_install_finds_every_command_of_the_real_window`)が落ちて知らせます。
* `kq.apply_keymap(win, keymap)` が、登録簿のキーを本物の `QAction`(`setShortcuts`)・別窓の `QShortcut`
  (`setKeys`。窓が作られた時)・Program 欄の部品・矩形選択の部品(`studio_editops_qt.apply_bindings`)へ配ります。
  メニューの右のキーは Qt が `QAction.shortcut()` から出すので、表示と実際は常に同じです。
* Qt に依らない部分(登録簿・正規化・当たり・保存の形・読み込みの検査・文の書き換え)は `studio_keymap` にあり、
  単体で試験できます。
* 全部のコマンドに意味(`studio_keymap.family`: find・replace・zoom・help・save・run・escape …)があり、
  `studio_keymap.same_key_different_family` が、範囲の重なる所で同じキーに付いた 2 つの意味が違う組を数えます
  (既定の 2 つの型で 0)。
