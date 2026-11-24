# BOP 第1段の公式評価検証

`bop.evaluate_bop19_pose` は、利用者が指定したローカルの BOP toolkit を使い、
ITODD の `val` だけを公式 BOP19 driver で評価します。`test` の評価は、非公開の
正解を探索しないよう subprocess の起動前に拒否します。

## 完全検証の経路

完全検証は GitHub Actions の `pinned official BOP19 golden fixture` job で行います。
この job は Ubuntu 上で EGL ライブラリを導入し、BOP toolkit を clone して
commit `cea62d651c7e395b2e1962b9749e4e89693c6ac4` に固定します。さらに公式
`scripts/eval_bop19_pose.py` の SHA-256 を照合してから、合成 fixture に対して
VSD・MSSD・MSPD の subprocess を含む公式 driver 全体を実行します。ITODD の画像、
深度、点群、CAD、派生可視化は fixture に含めません。

Windows の手元環境では EGL renderer を用意できず、公式 driver を最後まで通す
完全評価は未確認です。Windows で通る単体試験だけを完全評価の証拠にはしません。
非文書変更では、上記 Ubuntu/EGL CI job の成功を完全検証の門とします。

## ローカルで公式 golden 試験を実行する

BOP toolkit の固定 commit をチェックアウトしたディレクトリを
`BOP_TOOLKIT_ROOT` に指定し、EGL が使える Python 3.11 環境で次を実行します。

```powershell
$env:BOP_TOOLKIT_ROOT = (Resolve-Path '.\bop_toolkit').Path
$env:VISPY_USE_APP = 'egl'
py -3.11 -m pytest -q tests/test_bop_official_golden_2026_11_23.py
```

## 検証の範囲

この検査は、手元の BOP toolkit が固定した公式版から意図せずずれていないことを確かめ、
公表するローカル数値が公式評価器から得られたことを示すためのものです。固定 commit
オブジェクトの実在、HEAD がその commit を指すこと、固定 commit からの追跡ファイルの
一致、未追跡ファイルが一つもないこと（`.gitignore` と `.git/info/exclude` により無視
されたものを含む）を保証します。Git の検証コマンドは置換参照を無効にし、継承した
`GIT_DIR`、`GIT_WORK_TREE`、`GIT_INDEX_FILE` などの Git 環境変数を使いません。

この検査は、利用者が Python 環境または依存ライブラリ自体を意図して改変した場合や、
OS 側を改変した場合の耐性を保証しません。公式提出の数値は BOP サーバーが採点するため、
提出値の正本は BOP サーバーの結果です。

いずれかを確認できない場合は評価を開始しません。

## English summary

The complete official-driver verification is performed by the
`pinned official BOP19 golden fixture` Ubuntu/EGL CI job. The local Windows run
has not completed the EGL-based official evaluation, so Windows unit tests are
not evidence of the complete path. The adapter rejects a missing pinned commit,
tracked changes, and every untracked file, including ignored files, before
starting the evaluator. Its Git checks disable replacement refs and discard
inherited Git environment variables. This guards against accidental toolkit
drift; it does not make a deliberately modified local Python environment,
dependencies, or operating system trustworthy. Submitted results are
authoritative only when scored by the BOP server.
