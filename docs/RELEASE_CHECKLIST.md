# リリース手順書 — 同じ間違いを繰り返さないための門

この文書は「気をつける」ためのものではない。**気をつけなくても止まる**ように、
過去に実際にやった間違いを 1 つずつ門に変えた記録である。

実行部は `tools/preflight.py`。読んで思い出す項目は最小限にしてある ——
忙しい日に飛ばされるのは、いつも「読んで思い出す」方だから。

```powershell
py -3.11 tools/preflight.py            # 既定(約 5〜10 分)
py -3.11 tools/preflight.py --full     # 全数テストも(+20 分)
```

**FAIL が 1 つでもあれば出さない。SKIP は「通った」ではない。**

---

## 1. なぜこの手順書があるか — 2026-09-05 に起きたこと

0.1.8 を「全数テスト 11,342 件が緑」で出した。その直後に PyPI から落として
Linux に入れたら、**その場で 5 件見つかった**。

| 起きたこと | なぜ気づけなかったか |
|---|---|
| `pip install` した wheel から **224 op(26%)が消えていた** | `py-modules` の漏れ。**editable install は source dir を `sys.path` に足すので、開発機では原理的に再現しない** |
| Linux で 3 op が退化入力に **SIGSEGV**(Windows では 1 件も再現せず) | 開発機でしか動かしていなかった |
| 無音入力で `peak_prominence` が `inf`(0/0 を「無限に卓越」と報告) | 旧い scipy ではフィルタの残差で `med > 0` になり、**版が上がって初めて露出した** |
| 「誤った内部パラメータを検出できる」という安全確認が空振り | Windows の最適化が悪い解に留まっていた**偶然**を、テストが仕様として固定していた |
| CI が 0.1.6 から**ずっと赤**のまま 3 回リリースしていた | release ワークフローが CI に依存していなかった(**門がそもそも無かった**) |

いちばん痛かったのは次の事実である。

> **224 op が消えたことは `FAILED_BACKENDS` に理由つきで記録されていた。
> それを検査するテストも存在した。門が、事故の起きない場所にだけ立っていた。**

だからこの手順書の主題は「検査を増やす」ではなく **「門を正しい場所に立てる」**。

---

## 2. 過去の失敗 → いまそれを止める門

| 失敗の型 | 門 | どこで走るか |
|---|---|---|
| wheel から op が消える(0.1.6 で 321、0.1.8 で 224) | `tools/ci_wheel_check.py`(editable と wheel の op 集合を比較 + wheel 側の `FAILED_BACKENDS` が空) | CI `core-minimal` / preflight `wheel` |
| 動的読み込みのモジュールが `py-modules` から漏れる | `test_every_module_the_registry_actually_loads_is_shipped`(子プロセスでレジストリを組み、`sys.modules` を数える) | 全数テスト / preflight `ledgers` |
| 退化入力でプロセスが死ぬ | `ops.NATIVE_CRASHES_ON_DEGENERATE` + 登録時の関門 + 退化スイープ | preflight `degenerate` |
| **Linux でだけ落ちる** | preflight `linux`(WSL で同じスイープ) | preflight のみ(CI にネイティブ差は出ない) |
| 非有限が外へ漏れる | `backend_safe.guard` の一律適用 + `_clip01_finite` + `test_no_op_returns_a_non_finite_value_for_a_non_finite_input` | 全数テスト |
| 台帳に直った項目が残る | 各台帳の陳腐化検査(`stale = set(台帳) - 実在`) | preflight `ledgers` |
| 赤い CI でリリースする | release.yml の `Guard - CI is green for this commit` | タグ push 時 |
| CI が壊れているのに気づかない | preflight `ci`(HEAD の CI 結論を見る) | preflight |
| テストの import 失敗が全体を中断させる | `pytest.importorskip` + CI の install に依存を明記 | CI |
| 版がずれたままタグを打つ | preflight `version` | preflight |
| 台帳から本物を消しても落ちない(消えた op は検査対象からも消える) | テスト側の**対照**集合との等価(`EXPECTED_NATIVE_CRASH_LEDGER` / `test_the_two_nonfinite_ledgers_agree`) | 全数テスト |
| 台帳に偽の op 名が残る(改名・タイポ) | `test_every_ledger_entry_names_a_live_bridge_op` ほか各台帳の陳腐化検査 | 全数テスト |
| 別 repo の agent が実ツリーを直接書き換える(worktree 隔離は cwd の repo のみ) | 規律: 書き換える agent には自分で worktree を切って渡す。レビューは読み取り専用 | 人 |
| 出荷コードが**非同梱の開発道具**に依存し、失敗を `return []` で握る(tb_* 143 op が一度も配布されていなかった) | `typed_catalog` を出荷側へ + `build()` は失敗を投げる + wheel 門の tb_/hx_ **床** | CI `core-minimal` / preflight `wheel` |
| 門のスクリプト自身の置き場所が `sys.path[0]` に載り、checkout の `tools/` が wheel 側から見える | `ci_wheel_check.py` は自分の dir と cwd を捨ててから数える | 同上 |
| `build/lib` の古い staging コピーが wheel に混入し、外したモジュールが入ったまま門が通る | preflight は建てる前に `build/lib` を捨てる(release.yml は clean checkout) | preflight `wheel` |
| wrapper 族が内側で例外を握り潰し、外側の guard が何も見ない(5 族目 `backends_r3._make`) | `tests/test_backends_r3_wrapper.py`(必ず失敗するレシピで strict / 台帳を確認) | 全数テスト |
| テストが**利用者の実レジストリ**に書く(隔離 fixture が効いていない) | Studio の設定入口を `_settings()` に集約 + `FULLSEYE_STUDIO_SETTINGS` で ini へ | 全数テスト(Studio) |


---

## 3. 機械に判定させられないもの(ここだけ人が守る)

**規律 1 — バグを 1 件直したら、同じ形を全ファイルで grep してから完了とする。**
2026-09-05 に `xsk2_reconstruction` / `xsk2_h_maxima` を塞いだその日に、
兄弟の `xsk3_h_minima` を見落として Linux で落とした。直した「箇所」ではなく
直した「形」で検索する。

**規律 2 — 「自分が思いついた入力で確かめた」は「確かめた」ではない。**
全 op を元実装と突き合わせて「変わったのは 1 本」と結論した翌日に、
`tb_mat_cond` の取りこぼしを既存テストに拾われた。理由は単純で、
**自分の probe が特異行列を作っていなかった**から。
入力の作り方を疑う。構造のあるデータを必ず 1 本混ぜる。

**規律 3 — 測り方が雑なうちに出てきた数字を、不具合の数として報告しない。**
ノブ監査の候補は、ハーネスの粗を落とすたびに **425 → 108 → 98 → 29 → 17** と
減った。コードは 1 行も変えていない。門の棚卸しでも、雑な正規表現が出した
「17」を一度そのまま口にした —— あれは**パターンが一致しなかった回数**であって、
門が無い台帳の数ではなかった。**数字を出す前に、その数字の作り方を 1 段疑う。**

**規律 4 — 台帳(既知の不良を許すリスト)を足したら、陳腐化検査も同時に足す。**
足すのは「新しい不良を見つける」方向と「直った項目が残っていないか」の
**両方向**。片方だけだと、直したものが「既知」のまま居座って次に壊れたときに
気づけない。

**規律 5 — 「発見ゼロ」を頑健さの証拠にしない。**
まず「その検査は本当に実行されたか」を疑う。母数(通した op 数など)を
必ず一緒に主張する。テストが**消える**形で壊れることがある。

---

## 4. WSL 検証用 venv の作り方(preflight `linux` が使う)

Windows で開発している限り、**Linux での動作は誰も見ていない**。
一度作れば以後は使い回せる。

```powershell
wsl -e bash -lc "python3 -m venv /tmp/fs018 && /tmp/fs018/bin/pip -q install numpy scipy"
wsl -e bash -lc "/tmp/fs018/bin/pip -q install opencv-python-headless scikit-image pillow PyWavelets"
# 動作確認(repo のソースを直接読ませる)
wsl -e bash -lc "PYTHONPATH=/mnt/c/dev/projects/imgevolve /tmp/fs018/bin/python -c 'import fullseye;print(fullseye.__version__)'"
```

`pip install` した**配布物**の側で確かめたいときは、`PYTHONPATH` を付けずに
`/tmp/fs018/bin/pip install fullseye==<版>` する。**この 2 つは別の検査**で、
0.1.8 の 224 op 欠落は後者でしか見つからない。

---

## 5. 出す

```powershell
# 1) 手元で全部見る(ci 以外)。ci は push 前には構造的に FAIL するので外す
py -3.11 tools/preflight.py --full --only version,ruff,ledgers,wheel,degenerate,linux,suite
git add -A ; git commit                    # CHANGELOG に節があること
git push origin master
# 2) CI が緑になるまで待つ(タグを打つのはそのあと)
gh run list --limit 3 --workflow=ci.yml
py -3.11 tools/preflight.py --only ci      # HEAD の CI 結論を機械で確認
# 3) タグ
git tag -a v0.1.9 -m "0.1.9 — <一行>"
git push origin v0.1.9
```

順序に理由がある: `ci` 項目は **push 済みの HEAD** の結論を見るので、push 前に
`--full` に含めると必ず FAIL する(2026-09-05 レビューで実測)。
`suite` は `--full` を付けたときだけ走る(`--only suite` 単独は 0 件で拒否される)。

**CI が赤でも出さざるを得ないとき**は、タグの注釈に理由を書く。
書いた場合だけ release ワークフローが通り、**迂回したことが警告として残る**。

```powershell
# msg.txt の末尾に:  RELEASE-OVERRIDE: 上流 CVE で pip-audit が落ちるだけ
git tag -a v0.1.9 -F msg.txt
```

理由を書かずに通す道は用意しない。**黙って迂回できる門は門ではない。**

---

## 6. 出したあと(ここまでがリリース)

```powershell
# 配布物を、まっさらな環境に入れて確かめる。ビルドできたことは動く証拠ではない。
py -3.11 -m venv $env:TEMP\relcheck
& $env:TEMP\relcheck\Scripts\pip.exe install "fullseye==0.1.9"
& $env:TEMP\relcheck\Scripts\python.exe -c "import fullseye as F, ops; print(len(F.op_names()), ops.FAILED_BACKENDS)"
```

`FAILED_BACKENDS` が空でないなら、**そのリリースには op が欠けている**。

Linux 側も同じことをする(`wsl` の venv に `pip install fullseye==<版>`)。

---

## 7. この手順書を更新するとき

新しい失敗をしたら、**§2 の表に 1 行足してから直す**。
「どの門が受け持つか」を書けない修正は、まだ再発を止められていない ——
その場合は §3 に規律として書く(機械にできないと判断した理由も一緒に)。

門を足したら、**その門を壊して落ちることを確かめる**(変異テスト)。
落ちない門は、無い門より悪い。あると思い込ませるぶんだけ。
