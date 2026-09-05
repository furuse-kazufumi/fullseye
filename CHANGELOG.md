# Changelog — fullseye

All notable changes to the PyPI package `fullseye`. Dates are release dates (JST).
Versions follow the git tags; a tag push publishes to PyPI (`.github/workflows/release.yml`).
What makes a release 0.1.x vs 0.2.0 is written down in `CONTRIBUTING.md`
("Versioning") — the minor slot is our breaking signal.

## 0.1.7 — 2026-09-05

### 分母を増やした —— 全 1,722 op が「何をする op か」を自分で言えるようになった

前の版まで、**登録済み 1,722 op のうち 787 本(46%)に説明が一文も無かった**。
ヘルプを開いても名前と型しか出ない op がそれだけあった、ということ。
その 787 本を 0 にした。「要約 935 本を 6 言語」と言っていたときの **935 は
「説明がある op」の数**で、全体の 54% にすぎなかった —— 分母の方を直した。

内訳を測ったら、**787 本のうち 225 本は説明が既に書いてあった**。
op を包むラッパが ``__doc__`` を転記しておらず、包んだ瞬間に消えていた:

| 握り潰していた場所 | 本数 |
|---|---:|
| `backend_safe.guard` | 82 |
| `backends_typed` の橋(カタログ側の説明を捨てていた) | 143 |
| `backends_regions3` / `segment2` / `subpix` / `measure1d` の自前ラッパ | 28(※) |

※ 28 本は下の手書き 562 本にも含まれる(手で書いた日本語の方を採る)。

ここが今回いちばんの教訓で、**「仕組みがある」は「全経路が通る」ではない**。
`guard` を直した時点では直したつもりだったが、同型のラッパ族は全部で 6 つあり、
そのうち 4 つが同じ穴を持っていた。だから個別の回帰テストに加えて、
**ラッパ族をレジストリから機械的に数える検査**を置いた
(`test_no_wrapper_family_swallows_the_description`)—— 新しい族が増えたら、
登録した瞬間にそこへ現れる。

- **562 本を手で書いた**。名前からの推測ではなく、**実装を読んでから**
  「何を計算するか」「``a``/``b`` が何を振るか」「いつ使うか」「罠」を書いた。
  近似は近似と書く(HALCON の代役 op は「同じ結果を返すとは限らない」と明記)。
- **lambda にも説明を持たせられるようにした**。backend の op 表は lambda で
  書かれている行が多く、docstring を置く場所が無い。`ops.Op` に `doc` を足し、
  backend が module-level の `DOCS`(op 名 → 説明)を出すと登録時に積む。
  `backends_auto` の op は generic な shape から組むので spec 側に `doc` を置いた。
- **`Op.doc` が docstring より強い**。`backends_r3` の 56 op は汎用ファクトリが返す
  **同一の関数オブジェクト**を共有していて、その docstring を説明に使うと
  56 本が同じ文言になる。op 名で引く明示の指定が勝つのが正しい。
- **2-D の docstring に `cleandoc` を通した**。関数 docstring の 2 行目以降には
  定義位置ぶんの字下げが付いていて、そのまま出すと Markdown が**コードブロックと
  読む**。3-D / ledger 側は最初からこれを通していた(2-D だけ抜けていた)。
- **填め物を弾く検査**も置いた。要約が 20 字未満、あるいは op 名の言い換えだけ、
  は落ちる —— 「説明を書いた」を「文字列を入れた」で満たせると、数字だけが
  100% になって読者には何も渡らない。

**挙動は 1 ビットも変わっていない**(説明を足しただけ)。0.1.6 の木と現在で、
レジストリ 881 本・登録順の指紋 `371c7143…`・全 op を同じ入力で回した出力の指紋
`e5f25752…`・`DROPPED_DUPLICATES` の 4 件、すべて一致することを実測で確認した。

### 説明を書く作業が検出器になった(0.1.8 で直す)

実装を読んだら、**名前や HALCON 対応が約束していることをしていない** op が
15 件出てきた —— `_edges_color_sub_pix` にサブピクセル補間が無い、
`min_max_gray` が最大値しか返さない、`vol_erode` の `a` が実質 2 値スイッチ、
kornia 系や `polar_trans_*` でノブが死んでいる、別名なのに実装が同一 …。
説明の側は実装に合わせて正直に書いてあるのでヘルプは嘘をつかないが、
**コードはまだ直していない**。挙動が変わる修正で、公開済みの生成画像の再現性に
触れるため、`sk_frangi`(0.1.3)と同じく「既定値でビット一致」を保証したうえで
0.1.8 に入れる。一覧は `docs/KNOWN_ISSUES.md` の #12〜#26。

### ヘルプの多言語化(ja / en / zh / tw / ko / de)

対象言語は半導体サプライチェーンの主要国を見て選んだ 6 つ —— 日本・米英・中国・
台湾・韓国・ドイツ。台湾向け繁体字のコードは、ファイル名を 2 文字にそろえるため
`tw` にしてある(標準タグ BCP 47 では `zh-TW` / `zh-Hant`、しかも `tw` は本来
ISO 639-1 で Twi 語の記号なので、外から来るロケールは `opdocs.normalize_lang()` の
対応表を必ず通す)。

- **op ヘルプの枠を 6 言語に**。見出し・ラベル・fail-closed 入力契約など 40 件を
  `docs/i18n/opdocs.json` に括り出した。**キーは原文(日本語)そのもの**で、
  studio.py の `tr()` と同じ規約 —— 翻訳者はキーを発明せずに済み、原文を書き換えれば
  その行は自動的に未訳へ落ちる(古い訳が黙って残らない)。**言語追加は各行に 1 列
  足すだけ**で生成器のコードは触らない。`tools/opdocs.py html` が
  `<op>.<lang>.html` を 5 言語 × 1,722 op ぶん書く。
  括り出しは AST で機械的に行い、**日本語の生成物が 1 バイトも変わらないこと**を
  再生成 + diff で確認した(写し違いを人手に頼らない)。
- **訳したふりをしない**。散文(op の docstring)は原文のままなので、頁自身が
  どこまで訳されているかを言う: 要約が訳されていれば「以下の詳細説明は原文の
  ままです —— 要約と見出しは訳出済み」、まだ無ければ「まだ訳がありません」。
  判定は**表を引けたか**ではなく**読み手の言語で書かれているか**で行う ——
  2-D の要約 94 本のうち 30 本ほどは**もともと英語**で、それを英語の読者に
  「未訳です」と断るのは嘘になる。ガイド(人が書いた散文)は日本語 1 枚だけを
  出し、各言語版には日本語のみである旨を冠する。
- **要約の切り出しを先頭「行」から先頭「段落」へ**。折り返した docstring では
  935 本のうち **35 本が文の途中で切れていた**(``…enclosed by a contour, from``)
  —— 断片は訳しようがない。段落で切っても総量はほぼ変わらない(51,975 → 52,577 字)。
- ★**日本語も翻訳先だった**。「原文だから ja は常に読める」と数えていたのが誤りで、
  **原文が英語の要約が 521 本**あり、日本語のヘルプを開いても英語のままだった
  (分母を 1,722 に増やしたあとの実測。増やす前は 935 本中 349 本)。
  その 521 本すべてに日本語訳を入れ、**ja は 1,722 / 1,722**。
  `docs/ops/**` のノートは docstring の写し(単一真実源)なので触らず、
  `<op>.ja.html` を兄弟ページとして生やす形にした —— 他の 5 言語とまったく同じ
  仕組みで、参照順も既にそうなっていた。
- **到達率(実測、分母は全 1,722 op)**:
  **ja 1,722 / en 1,107 / zh・tw・ko・de 各 935**。
  日本語は全 op で読める。他の 5 言語は「分母を増やす前の 935 本」までで、
  **今回増えた 787 本ぶんはまだ日本語のまま**(頁自身が「まだ訳がありません」と
  断る)。数字を 100% に見せるために分母を小さいまま据え置く、はやらない。
- **要約が読めるかを op 名で数える検査**を足した。「要約が日本語で読めない op」を
  件数ではなく**名指しで**落とすので、赤い出力がそのまま作業リストになる。
  訳したことにして原文を貼る取り違え(指紋は一致するので永久に気づけない)も、
  「日本語訳のはずが日本語を含まない」で弾く。
- **手書きヘルプを訳で覆わない**。`gaussian` / `otsu` / `sobel_mag` の 3 枚は英語で
  書かれていて `sample:` で実行可能なパイプラインまで載せている。生成訳を横に置くと
  言語を選んだ瞬間に**中身の薄いほうへ差し替わる**ので、この 3 つには言語版を作らない。
- **ヘルプ内の言語導線**。頁の冒頭に、**その頁に実在する言語だけ**を並べた切替
  リンク(現在地は太字、押せないリンクは作らない)。UI の言語を切り替えると
  ヘルプもそれに追従する。
- **op 要約の対訳表を用意**(`docs/i18n/op_summary.json`)。キーは `<dim>/<op>`、
  原文の指紋つきで、**指紋が合わない訳は出さない**(古い訳を出すより日本語へ戻す)。
  指紋だけ更新して訳を据え置く、という抜け道は塞いである(それは訳の更新ではない)。
- **Studio UI を 6 言語に**。`strings` 44 件は **`ja` しか入っておらず、中文を
  選んでもメニューは英語のまま**だった。ツールチップ 36 件とクイックガイドも
  含めて zh / tw / ko / de を埋めた。

### 直した不具合

- **`apply_language` の固定許可リスト**。`i18n.json` の `languages` に足せば
  言語が増える、という約束をコード側が破っていた —— メニューには出るのに、
  選ぶと `("en","ja","zh")` 以外は黙って英語へ戻っていた。
- **台帳ヘルプが wheel に 1 枚も入っていなかった**。`package-data` が
  `op_help/3d/*.html` しか挙げておらず、生成してコミット済みの台帳 21 族・
  494 枚は `pip install fullseye` に含まれていなかった。`op_help/*/*.html` に
  してワイルドカード化(族が増えても落ちない。翻訳頁も同じ glob に入る)。
- **台帳ヘルプ上のリンクが全部死んでいた**。台帳の頁は兄弟 op / 次の op / 族
  ガイドへのリンクを `op<dim>:` / `guide<dim>:` で持つのに、Studio 側は
  `op3d:` と `guide2d:` しか捌いていなかった。接頭辞から次元を切り出して一般化。
- **入力を取らない op 82 個のデータ種の行が壊れていた**。`thin_lens` のように
  引数だけで決まる op は入力ソートが空で、`` `` → `table` `` という中身の無い
  コードスパンになっていた(「型が抜けている」のか「入力が無い」のか読み手に
  区別できない)。`` `なし` → `table`(引数だけで決まる op)`` と名指しする。

### 測って分かったこと(まだ直していない)

- **2-D の 881 op のうち 787 op(89%)に docstring が無い**。ヘルプには型契約の
  1 行しか出ない(`型契約は image → image。挙動の言語説明は下記のガイドと実行可能
  サンプルを参照`)。1,722 op 全体で見ても **787 op = 46% に説明文が無い**。
  翻訳より前に埋めるべき穴で、要約が 935 本しかないのはこれが理由(`math` 26 /
  `imgmetrics` 24 が少ないのは単に族が小さいだけ)。

### wheel を 72 MB → 30 MB に

wheel を実際に組んで中身を数えたところ、**圧縮後 42.1 MB(全体 72.0 MB の 58%)が
`studio_assets/sample_sources_ai/` の AI 生成素材 26 枚**だった。出荷コードからは
1 箇所も読まれない(参照は `tools/fops_article/` = 記事生成の開発ツールと docs/ の
仕様書だけ)。同梱から外した —— **読まないものを配らない**。リポジトリには残るので
記事の再生成には支障しない。翻訳ヘルプ 8,595 枚(圧縮後 15.5 MB)を足しても、
wheel は 0.1.6 の 54 MB より小さい 30 MB になる。

「studio_assets の全ファイルが package-data の glob に載ること」という既存の不変条件は、
そのままだと**読まない 42 MB を配り続ける理由**になってしまうので、意図的に同梱しない
ディレクトリの明示リストを設け、「出荷コードが読まないこと」を別の検査で示す形にした。

### wheel から 321 op が黙って消えていた(0.1.6 まで)

`pip install fullseye` で入る wheel には、**HALCON facade 600 op のうち 321 op(54%)が
入っていなかった**。リポジトリを clone した環境では全部動くので、テストも手元の確認も
通ってしまう。

原因は 2 つが重なっていた:

1. facade の実体モジュールは **文字列でしか import されない** ——
   `unified._load_facade` が `data/halcon_facade_map.json` の `"<module>.<func>"` を
   解決する。だから `import X` を探す `test_every_runtime_root_module_is_in_py_modules`
   には映らず、`matrix` / `shapematch` / `geometry2d` / `image_channels` /
   `contours_xld2` / `final_genuine` / `filters_freq` / `regions_setops` … 計 25 の
   ルートモジュールが `py-modules` から抜け落ちたままだった。
2. `_load_facade` は解決できない参照を `except Exception: continue` で握る。層ごと
   落とさないための設計として正しいが、そのぶん **op が黙って減るだけ**になる ——
   例外も警告も出ないので、誰も気づけない。

修正: 25 モジュールを `py-modules` に追加し、`tests/test_unified.py` に
**facade map の全参照が実際に解決すること**と**参照先のルートモジュールが
`py-modules` に載っていること**を検査する 2 本を足した。数の閾値(`facade >= 590`)
では 1 件ずつ削れていく欠落を捕まえられないので、**参照そのもの**を見る。

★この欠落は、`color_pca.py` を「死んだモジュール」と判断して削除したときに露見した
(facade が 600 → 589 に静かに減った)。`ops.REGISTRY` に 1 つも登録されていない
ことを根拠にしたが、**別の registry(facade 層)が使っていた**。削除は取り消し、
`py-modules` に追加した —— `create_color_trans_lut` / `inpainting_ced` /
`inpainting_mcf` / `inpainting_texture` / `exhaustive_match_mg` /
`gen_principal_comp_trans` / `gen_canonical_variates_trans` ほか 11 op の実体である。
**「1 つの登録簿で使われていない」は「使われていない」ではない。**

### 直したついで

- `tests/test_colorimetry.py` を `imgmetrics` を直接見る形に付け替え、**CIE の Lab と
  op 台帳の Lab が別の尺度であること**を固定するテストを足した(一致しないのが正しい
  状態 —— 揃えようとしないための杭)。

## 0.1.6 — 2026-09-05

- **ドキュメントに「知識ガイド」層を足し、ガイドを二種に体系化**。op の使い方を書く
  **族ガイド**(ファイル名が族名と一致し、その族の全 op ノートから自動リンクされる)に加えて、
  op の**手前にある物理と規約**を書く**背景知識ガイド**を導入した。後者は frontmatter の
  `applies_to: <dim>` / `<dim>/<category>` で該当する op ノートへ配線される
  (`applies_to: none` は「繋ぐ先が無い」の明示宣言で、書き忘れと区別できる)。
  この配線が無かったあいだ、知識ガイドは dim の INDEX にしか出ず
  **op ノートから辿る経路が一本も無かった**。書き忘れ・綴り違いは生成時に報告し、
  `tests/test_opdocs.py` が不変条件として固定する。
  投入したガイド: `3d/depth_sensors`(測距 5 原理の誤差の距離依存・実機の公表値・欠測の出方) /
  `annotate/dataset_conventions`(COCO/YOLO/VOC の bbox 換算・列優先 RLE・小箱で IoU が崩れる) /
  `2d/colorimetry`(色は分光 × 光源 × 観測者・メタメリズム・カメラは観測者でない) /
  `math/measurement_uncertainty`(VIM の条番号つき定義・GUM・校正は 2 段階) /
  `optics/mv_illumination_practice`(波長選択・偏光・オーバードライブ・IEC 62471) /
  `imgmetrics/image_difference_metrics`(`data_range` の 48.13 dB・SSIM の実装差・
  リサイズ実装だけで FID が動くこと・LPIPS の入力レンジ)。
  いずれも一次情報の出典と「症状 → まず疑う → 確かめ方」の診断表を持つ。
- **測色の実装を 1 か所に統一**。`color_pca.trans_from_rgb` は `"lab"` / `"xyz"` で
  `ValueError` を投げていたが、CIE の定義どおりの実装は `imgmetrics` に既にあった
  (白色点を選べ、CIEDE2000 は Sharma らの 34 組の検証対で固定されている)。もう一組
  書かずに**委譲**へ寄せた。回帰テスト `tests/test_colorimetry.py`。
  **honest**: この `color_pca` は**どこからも import されず wheel にも入っていない
  死んだモジュール**だったので、利用者への影響はゼロだった(0.1.7 で削除)。実際に
  効くのは残る 2 経路の違いのほうで、op 台帳経由の同名 op(OpenCV 実装)は uint8 に
  量子化した 8-bit スケールを返す —— **同じ名前でも数値の尺度が違う**。ガイドに表で
  明記した。
- **3-D のガイドが Studio ヘルプに 1 枚も出ていなかったのを修正**。HTML 生成の
  次元ループから `3d` が抜けていた。全ガイドにヘルプページがあることをテストで固定。
- **ドキュメント生成が 30 分級 → 8 秒**。`tools/op_example_index.py` が
  **(op 名 × example ファイル) の全組合せ**でソースを `ast.parse` + `tokenize` し直しており、
  実測で約 14 万回に達していた。散文落としは op 名に依存しないのでソースごとに 1 回だけ行い、
  正規表現の前に部分文字列の素通し判定を置いた。**出力は 1722 枚とも byte 一致**
  (生成前スナップショットとの差分 0 行で確認)。`md` 10 分 → 3.6 秒。
- **optics の worked-example カバレッジを 100% に戻した**。光学第 2 波で入った 29 op に
  例が無かった。`examples/vision_layout_from_catalog.py`(型番から組んで「覆えるか・
  分解できるか・運べるか・写るか」を撮る前に数字で決める)と
  `examples/studio_raytrace_scene.py`(光線の量で答え合わせをする)を追加。
  検証はすべて閉じた式 —— センサー対角 `p·√(w²+h²)`、Airy `1.22λN`、実効 F 値 `N(1+m)`、
  視野 `N·p·WD/f`、伝送帯域 `規格 × links × 効率`、回折ボケの総和保存、
  反射の法則 `|d·n + r·n| < 1e-14`、ライン走査の走査画素 `速度 / ライン周波数`
  (**既定では正方画素にならない**。周波数を `速度 / 直交画素` に合わせるとアスペクトが厳密に 1)。
- `optscene` の docstring 2 か所が偶然 Markdown リンク `[x](y)` になり、
  生成ドキュメントに壊れた相対リンクを作っていたのを修正。
- **`optscene` が非 editable な wheel から丸ごと欠落していた(出荷バグ)**。root モジュール
  なのに `pyproject.toml` の `py-modules` に無く、同梱の worked example が
  `import optscene` しているのに `pip install fullseye` 後の環境では ImportError に
  なる状態だった(0.1.5 以前が該当)。`py-modules` へ追加。
- **PyPI の `classifiers` が 0 件だった**のを 13 件追加(分類・検索の導線が無かった)。
- **版の付け方がどこにも書かれていなかった**のを `CONTRIBUTING.md` に明文化。
  0.x では SemVer 上「いつ何を変えてもよい」が、PyPI から入れる人がいる以上
  **minor の桁を破壊的変更の合図として使う**と約束する(op の削除・改名、既存 op の
  型/単位/尺度の変更、`apply()` の意味論、**既定の数値が変わる変更**、型付き
  レジストリの契約、Python 下限、fail-soft → fail-closed の反転 = 0.2.0)。
  値が bit 一致のままの高速化・op 追加・ドキュメント・翻訳は 0.1.x のまま。
- **総合紹介記事(en 39 万字 / ja 24 万字)がリポジトリにありながら、どこからも
  辿れなかった**のを修正。README の冒頭とドキュメント地図から絶対 URL で辿れるように
  し(この README は PyPI の long description を兼ねるため、相対パスは使えない)、
  `docs/articles/README.md` の一覧を実態に合わせた(**英語版が載っていなかった**)。
  各記事の冒頭に言語スイッチャの 1 行を置いた。
- **`docs/I18N.md` に多言語の方針を追記**: ④ 散文ドキュメントは**兄弟ファイル**
  (`<name>.en.md` / `<name>.zh.md`)、③ **コメント・docstring の併記は ja+en まで**
  (三言語を 1 つの docstring に詰めるとコードの可読性が先に壊れる。中国語以降は ④ へ)。
  導線の表と、v1.0.0 までの計画(実測した分量つき)も記載。

- **外観 op 族の敵対的検証(ユーザー「敵対的検証をしてください。特に未実施のものを重点に」)
  —— 実バグ 4 件を摘発して修正**。`tests/test_appearance_adversarial.py`(17 件)は
  「自分が期待した振る舞い」ではなく**まだ一度も掛けていない不変量**を突く:
  相反性 / 極限での一致 / エネルギー保存 / 線形性 / 敵対入力 / 決定性 / 補助層の正直さ /
  導線の実行可能性。
  摘発した実バグ:
  1. `matappear._normal_map` が **NaN/Inf を素通し**していた。外観 op の共通入口なので
     `ward_anisotropic`/`grating_rgb`/`oren_nayar`/`finish_shade` など**全部が例外を出さずに
     NaN 画像を返す**。下流のトーンマップが NaN を黒へ丸めるので「暗いだけの絵」になり
     原因が消える → 入口で fail-closed に。
  2. `cie_xyz_from_wavelength` の宣言 `pairs`((N,2))が嘘。実返りは (…,3) の XYZ →
     `points` へ直し、スカラ波長の (3,) は adapter で (1,3) に揃える。
  3. `prism_min_deviation_deg` が**台帳規約(先頭 N 個が宣言 in 型のデータ)に違反**して
     `apex_deg` を先頭に置いていた。波長配列が頂角に入り **素の TypeError**。波長を
     第 1 引数へ(規約に揃えるのが正しい直し方)+ 頂角に配列が来たら ValueError。
  4. `spectrum_to_srgb` が 0 次元入力で **素の IndexError**(`r.shape[-1]`)→ 番人を追加。
  併せて `opassist.sample_input` が単位を無視して波長に 0..1 を渡し「サンプルが動かない op」
  を作っていたのを修正(単位から可視域 400–700 nm を選ぶ)。
  通った不変量: 相反性(Ward / Oren–Nayar とも相対 <1e-9)/ 金属 Fresnel は **k→0 で誘電体
  Fresnel と 1e-9 一致**(独立に書いた 2 式が同じ物理へ収束)/ 薄膜は膜厚 0 で界面式と斜入射まで
  一致 / 透過係数から作った T で **R+T=1**(1e-12)/ 金属は全角度・全波長で R≤1 /
  分光→sRGB はスケールと和に対して厳密に線形 / 敵対入力 5 種 × 外観 op 9 種で素の例外漏れ 0・
  NaN 出力 0 / 乱数 op 5 件が seed 固定で bit 一致 / `accepted_sorts` の "works" が
  空の成功を隠していない / `op_path` の連鎖が台帳の型で本当に繋がる。
  最終監査: 新 op 33 件すべて型整合・素の例外漏れ 0(実行 30 / 契約拒否 3 / 問題 0)。
- **op 別の入力補助 `opassist` + Studio の op help に接続**(ユーザー「Studio の周りとか、
  入力補助機能とかもっと op 別にあったらいい」): `param_specs` は 2-D の a,b ノブ 2 本の
  見せ方を説明する層で、**実引数を取る台帳 op**(3-D / optics / tomography …)には効かない。
  そこを埋める。(1) `param_spec` 引数の型・単位・既定・選択肢・説明を署名と docstring から
  (選択肢は `METALS` / `FINISHES` など**モジュール定数から引く**ので実体とずれない)
  (2) `presets` CD/DVD/BD・実硝材・仕上げ・素材などの名前つき設定(テストで「実際に呼べる」
  ことを固定)(3) `producers`/`consumers` 「この入力はどう作る/次にどこへ繋ぐ」
  (4) `sample_input` すぐ動かせる引数一式 (5) `preflight` 実行前の注意
  (回折を溝と同じ向きから照らしている / 全反射を疎→密で呼んでいる等 —— **実際に踏んだ
  失敗**から起こした。例外にはせず実行は妨げない)。テスト +18。台帳 op は増やしていない。
  ★**コンテナ型の統一**(ユーザー「色々なコンテナ型は扱えるほうが良いけど、統一感も大事」):
  最初は `kind` に "seq"/"matrix" を混ぜていた = **値の型と容器の形が 1 つの欄で競合**
  していた(「int の 3 ベクトル」が表現できず、行列だけ構造の置き場が違う)。`kind` は
  値型(number/int/bool/choice/text/data)だけにし、容器は常に `container`
  (form: scalar/vector/matrix/list/nested/data、shape は必ず tuple、elem/role/labels)へ。
  スカラも例外にしない(shape=())ので UI の分岐が 1 本で済む。
  ★ tuple は既定値からだけでは分からない: `center=None`(省略可の (row,col))、必須の
  `trans`(3 ベクトル)、`k_cam`(3x3 行列)は**既定値が tuple ではない**ため、名前から
  構造を補う(名前と実際の長さが食い違うときは**形を優先** — 名前は当てにならない)。
  ★**op の多態性を実測で出す** `accepted_sorts`(ユーザー「op は複数の型に対応してると
  いいね」): 台帳は 1 op に 1 入力型しか書けないが、実体は要素ごとの演算が多く、
  `signal` 宣言の op が image2d / voxel / rgbimage / images も通す。宣言を広げると
  台帳と champion に波及するので、まず**測って見せる**層として置いた
  (`declared` / `works` / `rejected` / `error` の 4 値)。実測: `fresnel_dielectric` は
  宣言 signal に対し image2d・voxel・rgbimage・normalmap・images が通り、
  **素の例外漏れ(error)は 0 件** = 断るときは必ず ValueError で断れている。
  数えられていない多態性は「無い」のと同じで、UI も利用者も使えないままになる。
  ★**使いやすさの入口 3 つ**(ユーザー「使いやすさを考慮して、実装しましょう」):
  `op_find("虹")` でやりたいことの言葉(日本語可)から op を引き、`op_run(op)` は
  **引数ゼロでも動く**(プリセット解決 → 前提チェック → 台帳の宣言 out 型で返すので
  素のタプルを呼び手が剥がさなくてよい。`strict=True` で警告を例外に)、
  `op_path("normalmap","rgbimage")` で**型 A から B へ繋ぐ op の列**が出る
  (型で繋ぐライブラリなので、手順を知らなくても辿れる導線)。`fullseye.op_*` で公開。
  ★ `sample_input` の必須引数を**容器の形から**埋めるよう修正: 値型だけで決めると
  `corrosion_mask(shape, ...)` の `shape` に 1.0 が入り
  「'float' object is not iterable」で落ちた(実際に踏んだ)。
  ★ 単位の suffix 照合を最長一致に修正(`sigma_per_mm` が `_mm` に当たって "mm" と
  表示されていた。単位の取り違えは UI の数字を黙って別物にする)。
- **金属・ガラス以外の素材と表面処理 `surfacelib`(新 op 11 件)**(ユーザー「他にもいろんな
  素材や表面を再現できるなら対応してほしい」): 紙・石膏・コンクリート・プラスチック・塗装・
  陶器・布・ベルベット・木・皮革・ゴム・濡れた面・錆びた面・すりガラス ―― これらの大半は
  **(1) 粗い拡散 (2) 透明な上塗り (3) 微細構造 (4) むら** の 4 つで説明できる、という整理で
  op 化した。`oren_nayar`(σ=0 で **Lambert に厳密一致 1.1e-16**、σ=30° で端が 1.35 倍明るい
  = 満月が円盤に見える効果)/ `clearcoat_shade`(上塗りで反射した分だけ下地を (1−F_in)(1−F_out)
  で減衰 ―― 掛けないと足すほど明るくなる)/ `metallic_flake_normals` / `sheen_shade`
  (**鏡面と逆に縁で最大** — Phong では出せない布の見え方)/ `weave_normals`(FFT に 2 本の
  ピーク)/ `wood_grain`(年輪の変調 + 繊維方向)/ `wetness`(濡れは拡散を暗くする:
  0.50 → 0.357)/ `corrosion_mask`(面積率が指定値に一致: 0.30 → 0.2995)/
  `subsurface_approx` / `rough_transmission`(**直進 + 拡散 = 平板の透過率**でエネルギー保存)/
  `material_catalog`(素材 11 種の既定パラメータ)。テスト +14。
  optics 台帳 47 → **80 op**(appearance 7 / interface 4 / mirror 2 / glassbody 4 /
  finish 5 / material 6 / surface 5)。
- **ガラス・鏡面の光学 `glassmirror`(新 op 10 件)**(ユーザー「光学的にガラスや鏡面を
  扱う op が沢山あると良いね」): 誘電体/金属の Fresnel(s・p・無偏光)、Brewster 角、
  臨界角、金属の複素屈折率 n+ik(Ag/Au/Al/Cu/Cr)、金属鏡の**色**(n,k → 分光 → 等色関数)、
  Beer–Lambert 吸収、平行平板の多重反射、per-ray TIR つきベクトル屈折、プリズムの最小偏角
  (実硝材の分散)。検算: 垂直入射 = ((n1−n2)/(n1+n2))²(rel 1e-12)/ Brewster で Rp = 0
  (< 1e-15)/ 臨界角超 = 1.0 厳密 / 平板 T = 2n/(n²+1) 厳密 / 金 rgb (1.00, 0.67, 0.38)・
  銅 (0.98, 0.73, 0.53)・銀はほぼ中性 / プリズム d 線 38.65°、短波長ほど大きく曲がる。
  テスト +15。★ `match3d.refract` は「1 本でも TIR ならバッチ全体が None」なので画像
  サイズでは使えない —— `refract_rays` は per-ray マスクを返す。
  ★教訓: 「銅は金より赤い」と思って書いた assert が落ちた。公開値でも Au の R(450nm)
  ≈ 0.40 < Cu ≈ 0.56 で、**青は銅の方が多い**(金の方が飽和した黄色)。データが正しかった。
- **加工された金属表面 `metalfinish`(新 op 5 件 + ヘルパ 1)**(ユーザー「いろいろ加工された
  いろんな素材の金属表面を再現できると良いね」): 仕上げ 5 種(ヘアライン / 旋盤の同心目 /
  放射ブラシ / ローレット交差目 / ビーズブラスト)の**接線場**と**異方性粗さ場**、加工痕を
  法線へ刻む `micro_normals`、無方向凹凸の `blast_normals`、材質 × 仕上げの `finish_shade`
  (金属色は `glassmirror.metal_mirror_rgb`、微小面は Ward)。テスト +9。
  ★ これに合わせて `matappear.ward_anisotropic` / `grating_rgb` の接線を**場 (H,W,3)**
  でも受けられるようにした ―― 定ベクトルのままでは同心目・交差目・無方向が原理的に作れない。
  optics 台帳 47 → **69 op**(appearance 7 / interface 4 / mirror 2 / glassbody 4 / finish 5)。
- **溜まっていた実バグの一掃**:
  - `tools/op_example_index`: docstring の散文「<op名> (」を op 呼び出しと誤判定して
    **偽リンク**を生んでいた → 走査前に docstring とコメントを除去。実装中に
    **`ast.col_offset` が UTF-8 バイト基準**である二次バグも摘発(日本語コメント混じりだと
    docstring の代わりに実コードを消し、`match_sh_descriptor` が偽の未到達になった)。
  - `photometric.photometric_stereo(lit_only=True)`: 付着影(max(N·L,0) の非線形)で
    最小二乗が偏る既知欠陥を修正。実測 **6.499° → 0.003°**。既定は従来挙動のまま。
  - **TYPEMISS 既知 3 件を全解消**: `pose_error` は宣言 `measurement` に対し実返りが
    (回転誤差, 並進誤差) の 2 つ → 宣言を `table` にし adapter で名前つき dict へ
    (**並進誤差を捨てない**)。`sphere_sdf` / `box_sdf` は座標場を取るのに `points` 宣言
    だった → `grid_coords` を台帳に登録し新語彙 `coordgrid` を入口に。保留理由だった
    「champion を黙って書き換える」は `TYPE_TO_SORT["coordgrid"] = "points"` で解消
    (2-D 橋の tb_ 版は INPUT_ADAPTER が点群から座標場を作っているので、あちらの
    `points` 宣言は嘘ではない)。`test_wave0` green = champion 不変を実測で確認。
- **構造色・異方性の材質族 `matappear`(新 op 7 件)+ `render_beauty(surface=)`**
  (ユーザー: 「鏡面やガラスは?」「CD の虹は?」「ヘアラインは?」): 光線追跡を要さない 3 つ
  ―― 回折(CD)・薄膜干渉(シャボン/陽極酸化)・異方性微小面(ヘアライン)――
  を**波長から**作る。`cie_xyz_from_wavelength`(Wyman 2013 の多ローブ Gauss 近似)/
  `spectrum_to_srgb`(D65 白色順応つき、平坦反射率 1 → sRGB 白 (1,1,1))/
  `thin_film_reflectance`(Airy)/ `grating_wavelengths`(d(sinθo−sinθi)=mλ)/
  `grating_rgb` / `thin_film_rgb` / `ward_anisotropic`。optics 台帳 47 → **54**、
  新カテゴリ `appearance`。`render_beauty(surface="brushed"|"grating"|"thinfilm",
  surface_params=...)` で物体画素の鏡面項を置き換える。テスト +17。
  検算: 膜厚 0 = 基板単体のフレネル(n=1.5 で 0.040000、rel 1e-12)/ λ/4 = 解析値 0.077113 /
  λ/2 = absentee layer / CD 1.6 µm・Δsin 0.35 の 1 次 = 560 nm / 異方性ローブの伸び比 9:1:0.11。
  ★教訓 3 件: (a) 分散は**溝に直交する向き**にしか起きない ―― 溝と同じ向きに光源を振ると
  λ が ±100 nm(不可視)にしかならず「色が出ない」。(b) 実際の格子は**両側**に回折するのに
  +m しか計算せず、解が全部負 → 正の λ だけ残すフィルタが全部落として真っ黒だった
  (本命は m=−2 の 440 nm)。(c) 手組みの球メッシュの**巻き順が逆**だと法線が内を向き、
  render_beauty は例外を出さずに真っ黒を返す。
- **記事を「画像処理の分類別」に再構成(ja/en)**(ユーザー要望): 冒頭の実演を時系列の
  積み増しから、① 合成と計測チャンネル ② 受動計測 ③ 能動計測 ④ 断層 ⑤ 材質の見え方
  ⑥ 作り込みの過程、の 6 分類に並べ直し、分類マップの表(各項目に実測値)を先頭に置いた。
- **静物の X 線 CT(記事図)**: `tools/gen_hero_ct.py` — hero の静物を SDF から**中身の詰まった
  減衰係数ボリューム**(Al 0.46 / Ti 1.20 / PMMA 0.17 [1/cm]、横幅 30 mm・体素 0.210 mm)に
  戻し、74 スライス × 180 ビューを `radon_transform` → 光子ポアソンノイズ →
  `filtered_backprojection` で再構成 → 真値と照合。**Dice 0.882(適合率 0.79 / 再現率 1.00)**、
  μ 誤差 Ti 4.3% / PMMA 6.3% / Al 16.6%(格子球の殻は局所肉厚 2.0 体素 = 部分体積効果)。
  零点は単純逆投影 0.492(その手法に最も有利なしきい値)・24 ビュー FBP 0.452 で 1.8〜2.0 倍差。
  ★教訓: 初回は μ を「/画素」で置いて線積分 p=30 に達し、exp(-p) が光子 1 個を割って
  **対数が飽和**(photon starvation)。復元 μ が 50〜84% 低く、**零点の方が Dice で勝った**
  (0.63 対 0.43)。零点が勝ったらまず自分の物理を疑う。材質別の数字は Dice ではなく
  **再現率**(ラベル内しか見ないので Dice と名乗ると必ず 1.0 に寄る)と明記した。
- **構造化光スキャナを閉ループで組めるようにした(新 op 2 件)**: `fringe.absolute_phase`
  (巻き込み位相 + 粗い絶対推定 → 画素ごとに 2π 次数を確定。空間アンラップと違い島に分かれた
  場面でも絶対、要件は「粗推定の誤差 < π」)と `fringe.triangulate_column`(投影機コラム番号 →
  カメラ視線 × コラム平面の交点 → 深度、閉形式。既知面で 1e-8 一致)。3D 台帳 344 → **346**。
  事例 `examples_3d/structured_light_scan.py`: 球+段差箱+床を描画し、相補 Gray 18 枚 + 位相
  シフト 4 枚の撮影を合成 → 復号 → 三角測量 → **レンダラの真値深度**と mm で照合。
  奥行き 287 mm を **RMSE 0.233 mm(0.081%)**、Gray 復号は 16,521 画素で誤り 0。零点は
  Gray 整数のみ 0.548 mm(2.4 倍)・位相のみ 209.8 mm(901 倍)を判別的に上回る。
  記事図 `tools/gen_hero_structured_light.py`(静物へ 24 枚投影 → RMSE 0.036 mm / 中央値
  0.017 mm / 奥行き 102 mm)。テスト +8(`tests/test_fringe.py`)。
  ★教訓: 最初の実行は **RMSE 78 mm** で、しかも零点(Gray のみ 79 mm)と見分けがつかなかった。
  原因は `look_at` の gluLookAt 規約(-Z 前方)と `render_mesh`/K の CV 規約(+Z 前方、(x,-y,-z))の
  取り違えで、深度は「もっともらしい大きさのまま全部間違う」。零点を同時に測っていなければ
  通していた。相補 Gray(Inokuchi 1984)に替えるまでは固定しきい値が暗い画素だけ誤読していた
  (RMSE 5.3 mm の外れ値の正体)。
- **hero の被写体刷新 + `render_beauty(vertex_albedo=)` + 差別化パネル**(ユーザー: 「ジャガイモにしか見えない」
  「この絵は DirectX で昔からできる、差別化を見せろ」「図で訴求」): 被写体を 4 球 smooth union から
  **SDF/CSG の静物**(ジャイロイド格子球=鋼/三葉結び目=金/歯車=黒鉄、`examples_3d/render_beauty.still_life`)へ。
  物体別の色は新設 `vertex_albedo=(n_mesh,3)`(重心補間、金属は鏡面色も追従、範囲/形状検査)。
  記事には (a) **同シーンの計測チャンネル**(depth/法線/AO/影/`sobel_mag(depth)` 境界 21x、
  `tools/gen_hero_channels.py`)(b) **フォトメトリックステレオ閉ループ**(6 灯 `render_beauty(lambert,linear)`
  → `photometric_stereo`/`_robust` → 真値法線と角度誤差、`tools/gen_hero_photometric_stereo.py`。素朴 LS は
  付着影で 9° 偏り、点灯光源のみ/RANSAC で 0.00x°)(c) **改善の過程モンタージュ**(`tools/gen_hero_making_of.py`、
  素材 `tools/_making_of/`)(d) ターンテーブル(`tools/gen_still_life_turntable.py`)(e) 「2026-09-04 の拡張」章
  (op 数 2D 877/3D 344、新層の表)を追加。テスト +3(vertex_albedo)。
  (f) **復元法線からの再照明 GIF**(`tools/gen_hero_relight.py`): 6 灯撮影 → `photometric_stereo_robust`
  で法線+アルベド復元 → `render_lambertian` で光を一周(左=復元のみ / 右=真値法線)。有限画素の
  中央値角度誤差 **0.000°**、RANSAC が inlier 不足で未定にした 3763/21461 画素は `(0,0,1)` を明示的に
  詰める(嘘の形を作らない)。`integrate_normals` で高さ場も確認。

- **実解剖骨メッシュから手骨格を組み立てる例 `examples_3d/anatomical_hand.py`(ユーザー指摘「手骨も
  今となっては粗い」)**: 記事の手骨 hero は手続きカプセル SDF で実物と並べると粗かった。「正確な骨格」
  は画像生成 AI のもっともらしさでなく**実データの幾何**で担保する方針で、MyoSuite `myo_sim`
  (Apache-2.0、同梱せず `MYO_SIM_DIR`)の OpenSim 由来骨メッシュ 27 個(手根骨 8・中手骨 5・指骨 14、
  実寸 m)を MJCF(include 構成、`<worldbody>` 複数)から **stdlib だけ**で辿って配置(body 木の
  pos/euler 累積、MuJoCo 既定 eulerseq xyz)。`mujoco` があれば forward kinematics と突き合わせ
  (重心 6e-11 m・最近傍頂点 2e-9 m で一致)、無ければスキップを明示。解剖サニティ=指長 中指 123 >
  示指 117.5 > 薬指 112 > 小指 99.5 mm。手背を手首側から見下ろす構図(掌側の豆状骨で背側を判定、
  中指末節骨で指方向を判定)、`render_beauty` 1280px。データ未取得は SKIP(exit 0)。テスト 4 件
  (27 骨・FK 一致・指長順・euler/quat 規約)。記事 ja/en の手骨 hero を差し替え(手続き版は
  ターンテーブル節に残置)。
- **hero レンダの品質修正(Qiita 記事の 1 枚目)+ `render_beauty(vertex_normals=)`**: 記事の
  SDF 彫刻 hero は 640px・marching cubes res=48・**フラット法線**で、ファセット模様と四角い
  スペキュラが見えていた(ユーザー指摘)。`smooth_normals=True` にしても、面から作る頂点法線は
  ボクセル格子の階段を引き継いで**等高線状のバンディング**が残る(1280px で拡大確認)。等値面の
  法線は定義から ∇f/|∇f| なので、`examples_3d/render_beauty.py` に `sdf_vertex_normals`(SDF 勾配
  `np.gradient` を頂点で三線形サンプル)を追加し、`render_beauty` / `render_regolith` に
  `vertex_normals=(n_mesh,3)` の注入口を追加(メッシュ行のみ上書き、地面は既定、単位正規化、
  形状/非有限は ValueError)。hero は res=128・1280px・ss=2・AO 64・shadow_res 1024 で再生成
  (AO/影が支配的で所要時間は 640px と同じ ~80 s)。記事の画像 URL は `?v=2` で imgix キャッシュを
  バスト。テスト 3 件(既定法線の明示渡しは float 丸めまで一致/解析法線は陰影だけ変えシルエット不変/
  不正入力拒否)。
- **精度ユニオン型ストレージ(`precision_union.py`、公開: `fullseye.PrecisionUnion`)** —
  配列をタイルに切り、**各タイルを局所エントロピーに応じた最小ビット深さ**(`{0,1,2,4,8,16}`
  bit/要素の union。定数=0bit、2値=1bit、平滑=4bit、繁雑=8/16bit)で保持する。
  タイルごとにアフィン(`値=offset+code*scale`)と unit-scale 整数の 2 候補を計算し
  少ビットな方を採用、sub-byte はビットパックするので 2bit タイルは実際に 1/4 バイト
  で収まる。整数(および整数値 float)は**無損失**、float は指定 `atol` 内。呼び出し側は
  タイルのビット深さで分岐せず `to_dense/threshold/mean/map_pointwise` を一元的に使える
  (定数タイルは復号せず offset だけで処理する fast path つき)。numpy+stdlib のみ。
  実測(512×512): セグメンテーションラベル **17.0x**、64 枚ラベルボリューム 17.0x、
  深度 float32(atol=0.02)**4.0x**、平滑勾配 1.3x。自然画像 uint8 は 0.98x で
  **わずかに損**(高局所エントロピーで 8bit を割れず、per-tile メタデータが overhead)—
  勝ち筋はラベル/領域マップ・平滑深度・CAD/合成・3D ボリューム(fullseye のマシンビジョン
  データ)であることを honest に記録。既知技術(ブロック適応量子化+ビットパック)の
  組合せで、新規性は「異種精度ストア上の型付き一元処理層」にある。速度化は Python
  タイルループの overhead が定数タイル近道を食っており、ベクトル化が前提(現状は
  メモリ削減が主効果)。**遅延アフィン `scale_shift(a,b)`** を追加: `値=offset+code*scale`
  の代数から `offset'=a*offset+b, scale'=a*scale` でパックコードを一切触らず O(タイル数)
  で `a*x+b` を返す(コードバッファは元と共有=コピーなし)。明るさ/コントラスト/正規化の
  連鎖はメタデータ1パス+最後に1回だけ decode に畳める。遅延代数のみなら dense の `a*x+b`
  連鎖比 ~100x、materialize 込みでも数 op 連鎖で明確に速い(実測)。`threshold` は逆に
  dense(完全ベクトル化・帯域律速)に Python ループでは勝てない旨を docstring に honest に明記。
  **昇格(PoC→機能): N-D 対応 + ディスク永続化**。タイリングを任意次元に一般化(共有
  `_blocks()` ジェネレータ、per-axis タイルサイズ可)し、**3D ボリューム・スタック・動画**を
  扱えるように(最大の勝ち筋)。実測: ラベルボリューム `(64,128,128)` uint8 で **15.9x**
  (無損失)、深度ボリューム float32(atol=0.02)**3.9x**、自然画像 uint8 は 0.98x で不変
  (honest)。`save`/`load`(`.npz`、`allow_pickle=False`、ヘッダを並列配列化+パック本体を
  連結)でメモリ勝ちがそのままファイル勝ちに(構造的ラベルボリュームで **on-disk 378x**、
  npz の gzip も乗る)。1D/2D の既存 API・挙動は不変。例 `examples/precision_union_volume.py`
  (PASS 終端、2 regime + 遅延アフィン + honest な非勝ちを実演)。
  **op パイプライン統合(遅延実行)**: `fullseye.apply` / `run_pipeline` が `PrecisionUnion`
  を入力に受ける。`precision_union.LAZY_OPS`(`identity`/`invert`/`scale_clip`)にある op は
  **materialize せずヘッダ代数+タイル単位 clip で実行しユニオンのまま返す**(O(タイル数))。
  表に無い最初の op で 1 回だけ materialize して通常経路(coerce/契約変換/台帳)へ。整数・bool
  ユニオンは `/255` 契約変換と台帳記録が通常経路の責務なので遅延せず materialize(parity 固定)。
  GPU 経路(`device!="cpu"`)は dense を要するので materialize。新 `clip(lo,hi)`: ヘッダから
  各タイルの値域を O(1) で判定し、**窓内=不変(コード共有)/窓外=定数化/跨ぎだけ decode→
  再量子化**。**精度契約**: ユニオンは `from_array` で受け入れた `atol` を保持し、`scale_shift`
  は |gain| 倍で伝播、`clip` の跨ぎ再量子化はその atol で行う(無損失ユニオン=整数ラベルの
  clip は無損失、float は符号化 atol を超えない)。この契約は開発中に「タイル自身のステップ/2」
  という誤った契約(4bit で厳密だったタイルに 0.067 の誤差を許した)をテストで摘発して修正した
  もの。**drift 防止**: `LAZY_OPS` の (a,b)→gain/offset 写像は ops.py と二重管理なので、
  `apply(pu,op).to_dense() == apply(dense,op)` の parity テストで実 op に固定(乖離は CI 失敗)。
  **整数ユニオンも遅延**: uint8/uint16(文書化されたセンサ dtype)と bool のユニオンは `/255`
  等の契約変換を `scale_shift(1/s,0)`(純 gain、無損失のまま)で遅延実行し、dense 経路の
  `_contract_dtype` と**同じ台帳記録**(`dtype_converted`, source="input")と `on_error="raise"`
  の拒否を鏡写し(`api._pu_contract`)。int64 等はデータ依存の除数(`_dtype_scale`)なので
  materialize。→ 最大の勝ち筋(uint8 ラベルボリューム)が点 op 連鎖を通じて一度も materialize
  されない。**clip の厳密化**: `_Tile.cmax`(実際に存在する最大コード)でタイル値域を厳密に
  (従来の保守的過大評価が「範囲内タイルを偽の跨ぎ」にし 16bit 再量子化で 7.5e-6 の誤差を
  出していた — テストで摘発)。跨ぎタイルの処理は 3 段階: (a) 境界がコードグリッド上なら
  **コード空間で clip**(同ビット、値の decode 不要、厳密)(b) 無損失ユニオン(atol=0)なら
  **raw float64 タイル(bits=64)**で厳密保持(精度契約を守りメモリが払う。planner は選ばない)
  (c) それ以外は atol で再量子化。※(2^b−1) 等分グリッドの性質上 k/4 のような値は厳密表現
  不可(4 は 2^b−1 でない)— 遅延アフィンは実数では厳密だが float64 の結合順で dense と ulp
  差(~1e-16)が出る。parity は atol=1e-12(16bit 半ステップ 7.6e-6 とは 6 桁差)。テスト計 60 件。
  **lazy `threshold`(`threshold_lazy` / `LAZY_OPS["threshold"]`)**: `(v > a)` を 0/1 の float64
  ユニオンとして返す。定数タイルと**片側タイル(ヘッダ値域で判定)は O(1) で定数化**、跨ぎだけ
  decode→1bit。厳密(atol=0)、≤1 bit/要素、dense op と完全一致。ラベル/深度データで最頻の op を
  通じて**メモリ勝ちが伝播**する: ラベルボリューム (64,128,128) uint8 で union 14.8x → threshold
  後 **616.8x**(238 タイル定数 + 18 タイル 1bit)。速度も **1.74 ms vs dense op 6.63 ms(3.8x)**
  — dense は /255 変換+比較を 100 万ボクセルに払うが lazy は大半をヘッダで決める(これは
  Python ループで dense に勝てなかった dense-出力 `threshold()` とは別物: 出力もユニオンなので
  decode/scatter が無い)。テスト計 64 件。
  **ユニオンで閉じる op を拡充(勝ち筋=閉包性)**: `apply` の n-ary 枝と feature 枝が
  `PrecisionUnion` を受ける。**2 入力(`LAZY_NARY`、同形・同タイリングの 2 ユニオン)**:
  `union2`/`intersection`/`difference`/`symm_difference`(`mask_binop`: 0/1 化は dense と同じ
  `> 0.5`、定数タイル代数 `x|1=1, x|0=x(コード共有), x&0=0, x&1=x, 1&~x=NOT x(ヘッダ反転)`
  で大半を O(1) 決定、両方非定数のタイルだけ decode)、`max_image`/`min_image`(`extremum_with`:
  片方定数なら他方を定数で片側 clip=ヘッダ判定、両方非定数だけ decode、atol は max で伝播)。
  タイリング不一致は materialize。**feature(`LAZY_FEATURES`、ユニオン→スカラ)**: `area_frac`
  (定数 O(1)+1bit は popcount)、`min_max_gray`(=clip 後の max、**ヘッダのみ O(タイル数)**)、
  `intensity`(=clip 後の mean、`clipped_mean` で再量子化なしに厳密)。`threshold_lazy` は
  1bit タイルを**ヘッダ書換だけ**で処理(コード共有)。実測(ラベルボリューム (64,128,128)):
  集合演算 **lazy 0.6–0.7 ms vs dense 8.3 ms(~12x)、結果 400–1300x・≤1bit**、`max_image`
  **47x**、`min_max_gray` **82x**、`area_frac` **34x**。parity テストで全 op を dense に固定。
  テスト計 88 件(test_precision_union 75)。
- `fullseye.__version__` はパッケージメタデータ(= pyproject の version)を単一
  真実源として解決するようになった。従来はハードコードで、0.1.5 でも `"0.1.0"` を
  返していた。ソース/sdist では `api.py` 隣の `pyproject.toml`、インストール時は
  `importlib.metadata` から引く。
- **exact geometric predicates(`predicates.py`、公開: `fullseye.orient2d/orient3d/incircle/insphere`)** — 向き・内接円・内接球の判定を返す。float64 の行列式は near-collinear/coplanar/cocircular で**符号を誤る**(線上補間点のスイープで naive は約 19% 誤符号)。Shewchuk 流の 2 段適応(float 高速フィルタ→`fractions.Fraction` の厳密フォールバック。float64→Fraction は lossless)で**常に正しい符号**を返す。stdlib+numpy のみ(bignum/C 拡張なし)。凸包(`_convex_hull_xy`)の turn 判定をこれに載せ替えて堅牢化。
- **robust geometry queries(`geompred.py`、公開: `fullseye.point_in_polygon/point_in_convex_polygon/is_convex_polygon/point_in_tetrahedron/point_in_convex_polytope/is_delaunay_2d/mesh_orientation_consistent`)** — 上の exact predicates を、naive float で符号が反転する**組合せ判定**に使う消費層。内外判定は 3 値(`+1` 厳密内 / `0` 境界上 / `-1` 厳密外)で境界を明示。`point_in_polygon` は winding のエッジ交差を `orient2d` の厳密符号で決めるので、辺・頂点に厳密に乗る点を境界として正しく返す(整数座標の実測: 全エッジ点を境界検出)。near-edge スイープでは**naive float winding が robust と 8.64% 食い違う**(=naive が誤る)。`is_delaunay_2d` は各三角形の外接円が空かを `incircle` で検査し違反 `(三角形, 点)` を返す(cocircular は非厳密なので誤検出しない)。`mesh_orientation_consistent` は隣接面が共有エッジを逆向きに辿るか(非多様体/向き反転)を報告。stdlib+numpy のみ。
- `scale.scale_class` のタイル可否がカテゴリ推測から**実測**に。カテゴリだけの
  分類は 141 個の非局所 op(region の skeleton/distance/形状、gray のヒストグラム、
  edges の勾配強度/コーナー/DoG、多スケール texture、TV/拡散/変換系 smoother)を
  `tile_safe=True` と偽っていた。これらを `_NOT_TILE_SAFE` に列挙し、正規化で
  スケールだけずれるものは新クラス `global_reduce`、残りは `global`/`compute_bound`
  として理由つきで返す。3 プローブ×2 パラメータのライブ計測テストが、tile_safe と
  分類した op が実際にタイルで壊れないこと(完全性)と一覧が陳腐化していないこと
  (非陳腐化)をロックする。`process_tiled` の消費者は実行時に居らず助言専用なので
  実行時挙動は不変。
- 進化ブリッジ(`backends_typed`)に per-op tunable override を追加し、
  `running_gaussian_foreground` は検出感度を支配する `var_init` を振れるように
  なった(既定ヒューリスティックは効きの薄い `alpha` を選んでいた)。公開 op の
  既定値は不変。

## 0.1.5 — 2026-09-03 (main since 2026-08-31)

**Summary (en)**: the largest release so far — 63 feature/fix commits, 2,600 files, +219k lines.
Registry now measures **870 distinct 2-D ops + 344 3-D ops + 417 ledger ops** (math 26, optics 47,
light field 17, photon counting 17, specular 13, motion magnification 9, quaternion 19, FMCW 8,
acoustics 19, interferometry 9, tomography 17, volume colour 11, representation 42, CAD 4,
annotate 46, gfx2d 32, image metrics 24, colour transport 11, forensics 16, astro stacking 14,
video streaming 16).
Full suite: **10,854 passed / 171 skipped / 3 xfailed / 0 failed**. Four things a user notices:
(1) `apply()` now warns once per op when it silently fell back, and `fullseye.fallbacks()` shows
the ledger; (2) 32 measured behaviour changes from the adversarial review (listed below, several
are corrections of wrong answers); (3) a lens-design / illumination-design / image-formation layer
(`raytrace`, `lensopt`, `illumdesign`, `lensimage`, 47 ops); (4) 39 new worked examples, every op
has one, and the op docs (`docs/ops/**`) are generated from the registry with drift CI.

### 新しい op 族(すべて numpy(+scipy)で動作、重い依存は optional)

- **光学設計・照明・結像(47 op、`opsoptics`)** — `optics`(近軸/波動/偏光 18)、`raytrace`(実光線追跡・OPD→Zernike・Seidel・公差 MC、**実硝材 Sellmeier 20 種**(refractiveindex.info ミラーで定数照合)、**非球面 `asph=(A4,A6,…)`**、`chromatic_shift`、実絞りへの主光線エイミング `chief_ray`)、`lensopt`(**減衰最小二乗の最適化** `optimize_lens` / `merit_function` / `bend_singlet` — Coddington・Descartes・A4=kc³/8 の閉形式で検証)、`illumdesign`(**照明設計** `light_source` / `irradiance_map` / `illumination_uniformity` / `defect_contrast` / `lighting_sweep` / `illumination_design` — cos⁴ 則、鏡面での最良仰角 = 90°−2×斜面、候補族の順位表)、`lensimage`(**設計レンズで撮る** `psf_from_opd` / `distortion_map` / `render_through_lens` / `defect_dataset` / **校正閉ループ** `calibration_views`)。
- **ビジョン設計・仮想 MV 環境** — `visiondesign`(要求分解能から焦点距離・F 値・被写界深度・検出限界を紙の上で)、`visionlab`(設計→限界→仮想部品→撮像→検査の一気通貫)、`defectgen`(傷/孔食/割れ/しみの合成)。
- **センサ物理** — `lightfield`(17)、`photoncount`(17、時間分解・光子計数)、`specularity`(13、鏡面/拡散分離・GGX・偏光分離・ロバスト光度ステレオ)、`motionmag`(9)、`quatimage`(19、四元数画像)、`rangedoppler`(8、FMCW)、`acoustics`(19)、`interferometry`(9、コヒーレンス走査)、`tomography`(17)。
- **表現・描画・計測・来歴** — `reprconv`(42、表現変換)、`gfx2d`(32)+`drawlist`/`drawstyle`、`annotate`(25)、`palette`(役割で配色、赤緑の対を既定から外す)、`imgmetrics`(24、差を測る op — 外部基準で 5 op 検証)、`colortransport`(11)、`imgforensics`(16)、`astrostack`(14)、`cadmap`(4)、`volcolor`(11)、`mathops`/`opsmath`(26)、`ops1d`。
- **3D 体積** — `volregion` / `volgray` / `volxform` / `volprobe` / `volfreq` / `volrestore`(体積の領域・濃度・変形・探針・周波数・復元)、3D domain/boundary 6 op、`render_regolith` / `brdf_hapke` / `brdf_lommel_seeliger` / `shadow_raycast`(太陽 0.53° の本影・半影)/ `mesh_displace_fbm` / `mesh_scatter_boulders` / `terrain_region_mask`(イトカワの光と影を実画像 AMICA と 4 指標で照合)。
- **Studio** — `param_specs`(op パラメータの型適合ウィジェット 81+66)、右クリックの全ビュー、Feature Inspection 2D/3D、対話 3D ビューア、タブエディタ / watch / 実行制御。

### 2026-09-03 追加: 解像度管理・図注・動画ストリーム・高速化(実測で着手)

- **解像度管理(`meshres`、ops3d `resolution` 15 op)** — 「点群の粗い部分と密な部分の使い分け」を測って直す。`mesh_edge_stats`(辺長 p95/p5、UV 球 5.4・イトカワ実測 2.7)、`mesh_detail_map`(粗さ・実データの細部・合成起伏の重み)、粗い所だけ細分 `mesh_split_long_edges`(頂点不変)、等方リメッシュ `mesh_isotropic_remesh`(5.4→1.7、面積誤差 <1 %、閉多様体)、`mesh_sample_points`(Poisson 表面標本)。**学術用途では間引きを安易に行わない**規律を op に焼き込む: `mesh_lod_chain` / `mesh_select_lod` は各段の幾何誤差と画面誤差 px を返し、`mesh_decimate_preserving` は細部の頂点を厳密固定(誤差 1e-16)で `max_error` 超は**拒否**、`mesh_reduction_report` / `pc_thinning_report` は失ったものを数える(孤立点の除去数、`pc_poisson_disk` は 0)。`pc_density` / `pc_fill_sparse` / `pc_density_equalize` / `pc_lod_chain`。`meshrepair.decimate_qem(protect=)` 追加。
- **図注(annotate `paper` 21 op + ops3d `annotate3d` 7 op)** — 学術図の作法を op に: 肘つき引き出し線(衝突回避)、番号マーカー+凡例、寸法線、角度、1/2/5×10^k スケールバー、方位、インセット拡大、マスク輪郭、経路文字、カラーバー、パネル記号、複数パネル組版(`*_layout` 8 op は幾何だけを table で返す)。3-D は `pose`/`K` で射影した矢印・ラベル・スケールバー(短縮を正直に)・座標軸・箱・距離、`depth=` で隠れたアンカーは破線+白抜き。族ガイド `docs/ops/annotate/guides/figure_annotation.md`。
- **動画ストリーム(`videostream` / `opsvideostream` 16 op、2 波)** — `FrameRing`(直近 N 枚をフレームの dtype のまま: uint8 1080p×5 = 10 MB、float64 一括 1 秒は 475 MB)、状態つき op。第 1 波(8): `TemporalMedianWindow` / `MovingAverageWindow` / `BackgroundSubtractionWindow` / `FrameDifference` / `ExponentialBackground` / `RunningStats` / `OpticalFlowStream`。第 2 波(8): `MotionHistoryImage` / `MotionEnergyImage`(Bobick–Davis 動き履歴/エネルギー)、`ThreeFrameDifference`(Collins・二連続差分の AND でゴースト除去)、`RunningGaussianForeground` / `RunningGaussianBackground`(Wren *Pfinder*・画素ごと単一ガウス、k-σ 前景 — 固定閾値の `ExponentialBackground` の上位)、`TemporalBilateral`(時間バイラテラル・動きをゴーストにせず静止部を雑音除去)、`Deflicker`(輝度脈動を打ち消す)、`SceneCutDetection`(ヒストグラム χ² でショット境界)。`VideoPipeline`(台帳 op・状態つき op・callable を混ぜ、失敗時は状態リセット+台帳 `source="stream"`)。台帳の一括 op は同クラスの再生なので **ストリームと一括がフレーム単位で一致**。`iter_frames(dtype="uint8")` で整数素通し(1080p 読み込み 18→約 180 fps)。videops と同名にしない(因果窓は別名)。**per-frame スループット計測 `tools/bench_ops.py --set video`**(ring メモリのみ、fps 予算判定: 720p float64 で deflicker 152 fps・frame_diff 101 fps 〜 per-画素中央値/窓の temporal_median・background_subtraction・temporal_bilateral は 10〜15 fps)。
- **CPU 高速 twin(`fast`、41 op、既定 OFF)** — `FULLSEYE_FAST=1` または `apply(..., fast=True)` で cv2/IPP の twin を使う。accel と同型の parity ゲート(5 (a,b)×6 画像、内部 <5e-3、二値 op は不一致率 0)を **通ったものだけ**登録: gaussian 8.6×、median k=5 29×、gerode 14.6×、gopen 7.6×(2048²、熱定常でない同 run 相対)。clahe(0.135)/ bilateral(0.121)/ 回転・拡縮(スプライン次数)/ equalize / otsu(二値で 0.004)は**速いが違うので載せない**(`fast.NOT_LISTED`)。uint8 整数カーネル `fast.apply_uint8`(median k=5 185×、box 27×、gopen 50×; gaussian は 1.17/255 ずれるので除外)。
- **`FULLSEYE_FAST` 既定は OFF を維持(計測で判断)** — `tools/bench_ops.py --set core --sizes 1080p` を FAST=0/1 で比較: テーブルの 10 op が 1.3〜10×(gerode 10×、gaussian 5.3〜5.8×、mean_box 4×、sobel_mag/canny/std_filter 1.5〜1.8×)、dtype 変化ゼロ、テーブル外の op は経路同一で不変。速度は大きいが cv2 twin は内部差 5e-3 を持ち込み、本ライブラリの**再現性(SHA-256 ピン留め)を全ユーザーに対し暗黙に破る**ため既定 ON にしない。速度が要る動画/リアルタイム時に `FULLSEYE_FAST=1` で明示 opt-in する設計。
- **uint8 の fail-closed** — 従来 `apply()` は uint8 を拒否せず、gaussian が uint8 を返し threshold が全 1 を返していた(`docs/design/PERF_MEMORY_VIDEO_SURVEY.md` §1.3)。`on_error="raise"` は `ValueError`、既定は `/255`(uint16 `/65535`)に変換し台帳に `source="input"` で記録。float64 入力の結果は 1 ビットも変わらない(SHA-256 で固定)。`_coerce_input` の `np.unique` を O(N) に(region op 2 倍速)、ACCEL 逆引きをキャッシュ。
- **ベンチ台(`tools/bench_ops.py` + `bench/bench_ops_baseline.json`)** — op×サイズ×dtype の ms / Mpx/s / メモリ倍率 / 出力 dtype / fallback / 入力破壊を同 run 相対で記録、`--baseline` で ±30 % 退行を検出。ノイズ画像必須(median は内容で 10 倍変わる)。初回で `cv_dist` が float32 を返していた契約違反を発見→修正。
- 調査報告 `docs/design/PERF_MEMORY_VIDEO_SURVEY.md`(65 op 実測: 遅さの正体は scipy.ndimage 単スレッド float64、1080p 30 fps に届くコア op は 56 中 25、GPU 常駐 5-op 連鎖 2.1 ms/フレーム)。

### 利用者が気づく挙動変更(要注意)

- **`apply()` / `run_pipeline()` に `on_error="fallback"|"warn"|"raise"`**(環境変数 `FULLSEYE_ON_ERROR`)。既定でも op ごとに 1 回 `FullseyeFallbackWarning` が出る(`warnings.filterwarnings("ignore", category=fullseye.FullseyeFallbackWarning)` で消せる)。`fullseye.fallbacks()` / `fallback_counts()` が台帳(直近 256 件、出所 op/gpu/input/import)。GPU は初回失敗で Circuit Breaker が開く(`fullseye.reset_gpu()`)。
- **`fscript`**: `mean_gray/min_gray/max_gray` は 0..1 の比率 / 署名済みレシピは digest 変更で再署名が必要 / `read_image` は `base_dir` 内に限定 / タプル演算・添字・数値字句が厳格化。
- **`measuring1d`**: `amplitude` = 濃度差(旧 勾配ピーク ≈0.32×)、`threshold` も濃度差基準、`row/col/dist` 追加 / `metrology` は実形状で再フィット(楕円/矩形が円扱いだった)。
- **`calib.camera_calibration` は (row, col) 入力**(fx↔fy, cx↔cy が入れ替わっていた)/ `caltab.find_marks_and_pose` は失敗で例外(旧 identity)。
- **`algo`**: 番兵 0.0→−1.0(`is_prime` / `segments_intersect` / `edit_distance` / `point_in_polygon` / `lcs_length`)、2^53 超の整数は `ValueError`、graph n ≤ 5e6。
- **`imgio.save` は uint8 を彩色しない** / 切れた JPEG は `ValueError`(旧 黙って部分画像)/ 偶数線幅が 1px 細く / `to_float01(int16)` はアフィン / RGBA 保存の ABGR 入替を修正。
- **`pnp3d`**: 完全平面入力は平面経路で解く / `bundle3d` は `scale_anchor` で尺度固定(×0.7〜213 に発散していた)/ `register(init="auto")` / PPF 投票の角度符号を修正。
- **`raytrace`**: 数値引数に bool / 文字列を渡すと `ValueError`(旧 `"50"` → 50.0)、`stop` は整数のみ、`mirror` は bool のみ、零長の方向ベクトルは拒否、屈折率公差は硝材のみ(空気層には掛けない)、`n < 1` になる摂動は `ValueError`。`optimize_lens` は `status`(converged / stalled / iterations)を返し、bounds は初期値にも適用。
- **`vol_resize`** が定数体積の隅を 0.42 にしていたのを修正 / `convol_image` は畳み込み(相関だった)/ `radon` の既定角 135°。
- 進化エンジン: NaN fitness が champion になれない / RPCA の入力縮小で欠陥が消えない / pyramid の 1px ずれ修正。

### 構造・品質

- **fail-soft 3 層の沈黙を解消**: 全 backends(31 本 + macro/typed)の `_safe` を `backend_safe.guard()` に一元化(記録・strict・sanitize)。設計根拠は `docs/design/TRIZ_DESIGN_PATTERN_MATRIX.md`。
- **CI 常設**: `tests/test_op_probe_ledger.py` + `docs/OP_PROBE_ALLOWLIST.json`(退化 op は理由付き許容、新規は fail)、typed ブリッジの sort 跨ぎ恒等/定数検査、OP_CATALOG / SENSOR_PLAYBOOK / 記事展示 / op docs / Studio help の drift 検査、`examples2d` 両方向検査、**op→example 100 %**(3D 317 / 2D 860)。
- 徹底敵対レビュー 7 領域 72 件 + 前回残 8 件 + 死んだ op 12 件 + 同名 4 組 + ブートストラップ 34 本を修正(`docs/KNOWN_ISSUES.md` に再現手順)。Codex 読取レビュー 3 巡(13 + 10 件)を実コード検証のうえ反映。
- **op ドキュメント体系**: `docs/ops/**`(per-op ノート 1,500+、24 ファミリガイド、全 snippet 実行検証)を `tools/opdocs.py` が生成し Studio help に変換、`docs/OP_CATALOG.md` は登録簿から生成。

### 記事・その他

- Qiita 総合紹介記事 ja/en を 860 / 317 / HALCON 981(42.4 %)へ更新、展示 141 点、イトカワの新静止画(Hapke + レイキャスト影)を追加。`tools/qiita_patch_overview.py`(GET 退避 → 画像 HEAD 全数 → 縮小ガード → PATCH → 検証)。
- サンプルデータは非同梱(`fullseye samples list/open/download`、fail-closed)。

## 0.1.4 — 2026-08-31

`em_skeleton`(EM93 で検証)、骨格グラフ 2D/3D、3D morphology の scipy 経路 + ball SE + open/close。733 + 271 op、6,301 テスト。

## 0.1.3 — 2026-08-30

バグ一掃リリース: KNOWN_ISSUES 5 件(`count_obj` 8 連結 / `sk_frangi` ノブ配線 / XLD トレース順 / CLAHE 双線形補間 / DStretch RGB 受理)。Studio に Feature Inspection 2D/3D・対話 3D ビューア・`disp` 系ディレクティブ。`pyproject.toml` の BOM/cp932 化け(PowerShell 書込み事故)を復元。

## 0.1.2 — 2026-08

セキュリティと i18n: GitHub Actions を commit SHA に固定、`fullseye-rag` の英語ヘルプ。

## 0.1.1 — 2026-08

bare-install 修正: 3D レジストリ(`ops3d`)が numpy + scipy のみでも import できる。

## 0.1.0 — 2026-08-01

初回公開: 約 1,000 の型付き画像処理 / 幾何ビジョン op(numpy ネイティブ、HALCON 語彙)、進化エンジン、Studio、C/Python codegen。
