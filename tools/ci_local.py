# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""push の前に、手元の Linux(Windows なら WSL2)で GitHub CI に相当する検査を回す。

## なぜ要るか(2026-11-10)

2026-11-09〜10 に「CI で落ちる → 直して push → また落ちる」の往復が 4 回あった(1 回 1.5 時間)。
落ちた原因は 空の表明・所要時間の記録・記録値のずれ・Linux のファイル権限と lock の違いで、
Linux で全数を回せば手元で見える型の失敗だった。この道具は**その型を push の前に減らす**ためのもので、
GitHub の CI の代わりではない(確かめないものは下の一覧と、要約の末尾に毎回書く)。

## 使い方

    py -3.11 tools/ci_local.py                 # Windows: HEAD を WSL2 で全段(初回は環境を作る)
    py -3.11 tools/ci_local.py --ref origin/master -n 12
    python3 tools/ci_local.py                  # Linux: 同じ(WSL を介さない)
    py -3.11 tools/ci_local.py --only core     # 1 段だけ(要約は「部分実行(全数ではない)」になる)
    py -3.11 tools/ci_local.py --accept-skips "skip 付きのテストを 60 件足した"   # skip の基準を受け入れる

結果は要約 ``summary.md`` と JUnit・ログを ``--out`` に書く(既定は一時ディレクトリの
``fullseye-ci-local/<時刻>-<commit>``。前回の成果物が残っていれば消してから始める)。
終了コード: 0 = 走った段が全部 ok / 1 = 失敗 / 2 = 引数の誤り(1 段も走らない組み合わせを含む)/
3 = 状態ディレクトリを別の ci_local が使っている / 130 = Ctrl-C で中断した。
0 の意味は「走った段が ok」で、「全数が GitHub と同じ条件で通った」ではない。部分実行(``--only`` など)と、
GitHub と違う条件の run(``--no-merge``・``--no-fetch``・``--allow-other-python``)も 0 を返す。どちらも
呼び出した側が引数で選んだ範囲・条件で、選んだ範囲の中の失敗だけを終了コードにする(条件の違いを非 0 に
すると、オフラインの ``--no-fetch`` や 1 段だけの ``--only`` が「落ちた」と区別できなくなる)。緑との区別は
要約の題と結論、``result.json`` の ``verdict`` でする(``full_ok`` だけが「全段・同じ条件で ok」。ほかは
``ok_missing_tools``・``partial_ok``・``deviating_ok``・``failed``・``busy``)。端末の最後の行にも
``verdict: <値> — <一言>`` を出す(``ci_local && git push`` のように終了コードだけを見ると、0 の 4 つの意味を
区別できない。push に繋ぐなら result.json の ``verdict`` が ``full_ok`` かを見る)。外側が内側を走らせずに
止まったとき(引数の誤り・``wsl.exe`` が無い・Ctrl-C・例外)も最後の行は ``verdict: usage — …`` か
``verdict: failed — …`` にする(この 2 つは最後の行だけの語で、``result.json`` は書かない)。

## 何を検査するか

* **対象の commit と、fetch し直した ``origin/master`` の merge** を検査する(既定)。GitHub の PR の CI が
  検査するのは枝の先端ではなく base との merge commit で、op の数・索引・台帳・``.test_durations`` のように
  両方が触る生成物は「先端では揃っていて merge 結果では揃わない」ことがある。merge は Linux 側の clone の
  中で作る(利用者の作業木には何も書かない。外側がするのは ``git fetch`` だけ)。衝突したら失敗
  (master を取り込んでからやり直す)。``origin/master`` が対象の祖先なら merge しても同じ木なので先端を、
  対象が ``origin/master`` の祖先(または master そのもの)なら対象の先端をそのまま検査する。
  ``--no-merge`` は先端だけを検査する。どの場合も、何と何を検査したか(両方の sha)を要約に書く。
* 作業木の未 commit の変更は検査しない(要約に件数を書く)。検査する木は Linux 側の別の clone
  (``--state-dir``、既定 ``~/fullseye-ci-local`` の ``repo/``)で、段ごとに ``git checkout --detach`` +
  ``git clean -fdx`` する。Windows の作業木を ``/mnt/c`` 越しに読まない理由は 2 つ: 遅い(9P 越し)ことと、
  ``core.autocrlf=true`` の作業木は CRLF で権限ビットも無く、Linux の CI と同じ木にならないこと。
* 状態ディレクトリは**排他**(flock)。別の ci_local が使っていれば、持ち主(pid・開始時刻・commit)を出して
  すぐ終了コード 3 で終わる。目印のファイル(``.fullseye-ci-local``)の無い既存のディレクトリでは
  何も消さずに失敗する。例外は 1 つ: 目印を置く前の版が作った置き場(venv の stamp がある)は、``repo/`` が
  「origin が検査する repo で、``pyproject.toml`` の name が fullseye の clone」のときだけ引き継ぐ
  (``repo/`` が別物なら、目印も置かず何も消さずに失敗する)。
  段の終わりごとに clone の HEAD が検査対象のままかを確かめる。
* 段は**落ちやすくて軽いものから順に、直列で** 5 つ回す:
  1. lint —— ci.yml の ``lint`` ジョブ: ``ruff check .``(ruff は毎回 ``ruff>=0.4`` の最新に上げる)と
     ``tools/pip_audit_gate.py``(利用者に入る依存の既知脆弱性。ネットワークが要る。``--no-pip-audit`` で外す)。
  2. regen —— ``tools/regen_all.py --check``(ci.yml の shard 1 の最後の段)。
  3. gates —— ``tools/ci_always_run.txt``(検査する木にあればそれ、無ければ内蔵の写し ``BUILTIN_GATES``。
     どちらを使ったかは要約に書く。一覧にあって実在しないファイルは失敗)。
  4. core —— ci.yml の ``core-minimal`` ジョブと同じ順(毎回作り直す venv に ``pip install -e .`` →
     smoke → editable の op → ここで初めて ``build`` → sdist から wheel → 配布物の op → 大きさ →
     ここで初めて ``pytest`` → packaging → wheel からの MCP / fs_apply)。
  5. tests —— ci.yml の ``test`` ジョブ(py3.11、optional backend 全部入り)と同じ依存と環境変数で、
     pytest-xdist で並列に回す。門も外さない(範囲を減らさない)。追加の pytest 引数が無いときは、
     実行件数が ``.test_durations`` の行数の 95 % を下回ったら失敗(``SUITE_FLOOR_RATIO``)。skip の件数は
     状態ディレクトリに記録し、基準(これまでの記録の最小)から大きく増えたら要約の先頭と端末の最後の行で
     知らせる(失敗にはしない)。比べるのは全体の件数で、手元に無い道具(cargo・node・Chrome)の組が基準と
     今回で違うときだけ、有無の違う道具の skip(理由の文面からの推定)を、その道具が無かった側から引く
     (道具の有無が run ごとに入れ替わっても基準がずれない。組が同じなら何も引かない)。記録を書くのは verdict が ``full_ok`` か ``ok_missing_tools`` の run だけ(失敗・部分実行・
     違う条件の run の件数は比べる相手にしない)。基準は下がる向きにしか動かないので、線以内の増加を
     繰り返しても基準は上がらず、累積で線を超えたところで知らせる。正当な増加は ``--accept-skips "<理由>"``
     で、その run の件数を基準に受け入れる(記録に前の基準・理由・sha・日時を残す)。記録が読めない
     (壊れた・型の違う・版の違う)ときは比べず、上書きもしない(段は落とさない)。
  前の段が落ちたらそこで止めて要約を書く(``--keep-going`` で最後まで回す)。
  ``--only``・``--skip``・``--no-pip-audit``・追加の pytest 引数のどれかがあれば、要約の題と結論は
  「部分実行(全数ではない)」になり、走らなかった段は表に「未実行」と残る。
  ``--no-merge``・``--no-fetch``(と、fetch できない形の ``--base``)・``--allow-other-python`` は、走る段は
  同じでも GitHub と違う木・違う Python を検査する。題と結論は「GitHub の CI とは違う条件」になり、
  「全段 ok」とは書かない。
* 環境変数は**継承しない**(``env -i`` 相当)。手元の ``FULLSEYE_*_DATA`` や ``~/.cache/fullseye`` の
  実データが見えると CI と違う分岐を通るので、HOME も run ごとの空のディレクトリにする。
  入れるのは GitHub の runner と ci.yml が与えるもの: ``CI=true`` ``GITHUB_ACTIONS=true``
  ``PYTHONUTF8=1`` ``QT_QPA_PLATFORM=offscreen`` ``LANG=C.UTF-8`` ``TZ=UTC`` と、門・全数だけ
  ``FULLSEYE_REQUIRE_OPTIONAL=1`` ``FULLSEYE_FIGURES=off``。PYTHONPATH は無し、pytest は
  ``python -m pytest`` でなく ``pytest`` で起動する(cwd が sys.path に入らない = CI と同じ)。
  例外は道具の置き場だけ: cargo・node・Chrome は手元の PATH と ``~/.cargo/bin`` で探し、見つけた実行ファイルの
  ディレクトリをテストの PATH に足す(rustup の ``CARGO_HOME``・``RUSTUP_HOME`` も渡す)。同じディレクトリに
  ある他の実行ファイルもテストから見える。
  ★``CI=true`` は設計判断: GitHub の runner が実際に与える値が ``true`` で、``os.environ.get("CI") == "1"``
  で分岐する PoC が 2 本ある(examples/poc_omni360_inspection.py・poc_plenoptic_camera.py)。``CI=1`` に
  すると手元だけ「CI 用の小さい設定」を通り、GitHub と違う分岐を検査することになる。

## 確かめないもの(要約の末尾にも毎回書く)

* Python 3.12 / 3.14(master で GitHub が回す)、3.13(週次)、3.15 の preview。手元は 3.11 だけ。
* 片ごとの見え方。GitHub は全数を 6 片に分け、片ごとの session で回す。``test_test_durations_is_fresh``
  のように session の構成で答えが変わる門は、全件 1 session の手元と片で結論が違いうる。
* 直列の順序。CI の片の中は直列、手元は xdist の並列。順序依存は夜間の order-shuffle が見る。
  逆に、並列でだけ時々落ちる手元だけの赤もある。
* runner にある道具(cargo・node・Chrome)が手元に無いと、それに依るテストは skip する。開始時に有無を
  調べて要約の先頭に書き、skip の理由を JUnit から集計して「GitHub でしか確かめられない件数」を出す。
  道具が 1 つでも無い run は、全段 ok でも ``full_ok`` にしない(verdict = ``ok_missing_tools``、結論は
  「全段 ok —— ただし手元に無い道具のため N 件は GitHub でしか確かめられない」)。``--require-tools`` は、
  その場合を開始時の失敗(終了コード 1、verdict = ``failed``)に変える —— 「``full_ok`` か失敗か」の
  どちらかが欲しいときに付ける。道具がシステムに何かを入れることはしない
  (apt パッケージも ``--install-apt`` で頼まれたときだけ)。
* lint ジョブの 2 つ目の pip-audit(CI の道具そのものの監査。CI でも警告のみ)、coverage の結合
  (``--cov`` で計測だけは付く)、docs-only ジョブ(文書だけの PR で全数の代わりに回る部分集合)。
* 依存の版は venv を揃えた時点のもの。CI は毎回その日の最新を入れるので、``--refresh-hours``(既定 24)
  より古い full venv は ``pip install -U --upgrade-strategy eager`` で揃え直す。
* この道具の中の依存の定義(``FULL_EXTRAS`` など)は ci.yml の手写し。ci.yml に同じ文字列があることは
  tests/test_ci_local_tool_2026_11_10.py が見るが、ci.yml に**足された**行は見つけない。
* fetch したあとに master が進めば、GitHub が作る merge commit は手元で検査したものと違う。
* BLAS のスレッド数は ``CPU 数 / 並列数`` に絞る(付けないと 12 並列 × 24 スレッドで詰まる)。絞ったせいで
  「BLAS が 4 スレッド以上要る」と skip したテストは、全数のあとで絞らずに直列で回し直す。回し直しても
  走らないテストが残れば失敗にする(回し直しの目的が「走らせること」なので)。
* 持ち主が殺されたあとに残る子プロセス。排他は内側の Python が持つ flock で、内側だけが ``kill -9`` されると
  ロックは外れるが、子(pytest など)は残りうる。その間に次の run が同じ clone を ``clean -fdx`` することは
  防いでいない(止めるときは内側だけでなくプロセスの木ごと止め、pytest が残っていないのを見てから次を回す)。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path

# ---- ci.yml と揃える(変えたら ci.yml の該当行も見る。同じ文字列が ci.yml にあることはテストが見る) ----
#: ci.yml `test` ジョブの extras と追加パッケージ。
FULL_EXTRAS = "opencv,skimage,pil,wavelets,gui,video,volume,gltf,lidar,pcd,xlsx,export-verify"
FULL_EXTRA_PKGS = ["pytest", "pytest-cov", "pytest-split", "matplotlib", "sympy", "ziglang",
                   "hypothesis", "pytest-timeout"]
#: 手元だけの追加(並列用)。ci.yml の `test` ジョブには無い。
LOCAL_ONLY_PKGS = ["pytest-xdist"]
#: ci.yml `test` ジョブの「Optional backends (py3.11 only)」。
TORCH_INDEX = "https://download.pytorch.org/whl/cpu"
TORCH_PKGS = ["torch>=2.13"]
OPTIONAL_PKGS = ["kornia>=0.9", "mahotas>=1.4"]
OPENCV_CONTRIB = "opencv-contrib-python>=4.8.1.78"
#: ci.yml の各ジョブ先頭の「pip と証明書を更新」。
PIP_BOOTSTRAP = ["pip>=26.2.2", "certifi>=2026.10.19"]
BUILD_PIN = "build==1.6.1"
#: CI の runner が入れる apt パッケージ(Qt offscreen と CJK フォント 2 本)。
APT_PKGS = ["libegl1", "libgl1", "libxkbcommon-x11-0", "libdbus-1-3",
            "fonts-noto-cjk", "fonts-ipafont-gothic"]
#: ci.yml `lint` ジョブ。
RUFF_PIN = "ruff>=0.4"
PIP_AUDIT_PIN = "pip-audit==2.10.1"
PIP_AUDIT_ARGS = ["--python-version", "3.11", "--manylinux-glibc", "2.39"]
#: ``tools/ci_always_run.txt`` が無い木で回す門(2026-11-10 の版の写し)。
BUILTIN_GATES = [
    "tests/test_vacuous_assertions.py", "tests/test_type_alias_ledger.py",
    "tests/test_test_durations_is_fresh.py", "tests/test_provenance_naming.py",
    "tests/test_no_invalid_escape_sequences.py", "tests/test_svd_full_matrices.py", "tests/test_fssystem.py",
    "tests/test_docs_liquid_safe.py", "tests/test_no_stray_root_images_2026_11_01.py",
    "tests/test_review_fixes_lib2_2026_10_07.py",
]
GATES_FILE = "tools/ci_always_run.txt"
#: 依存の定義を変えたら上げる(venv を作り直す合図)。
SPEC_VERSION = "1"
#: ci.yml の「Optional backends」の最後の確認と同じ。
VERIFY_FULL = ("import torch, kornia, mahotas, cv2; print(torch.__version__, cv2.__version__);"
               " assert hasattr(cv2, 'xfeatures2d')")

#: 段(引数の名前, 要約の名前)。この順に回す。
PHASES = (("lint", "lint (ruff + pip-audit)"), ("regen", "regen_all --check"), ("gates", "門"),
          ("core", "core (numpy+scipy)"), ("tests", "full suite"))
PHASE_KEYS = tuple(k for k, _ in PHASES)
PHASE_LABEL = dict(PHASES)
PHASE_ALIASES = {"ruff": "lint"}

#: 全数の段の件数の床 = ``.test_durations`` の行数 × この割合(追加の pytest 引数が無いときだけ)。
#: 根拠(2026-11-10 の全数 2 回、同じ commit): 実行 27,710 件 / ``.test_durations`` 27,699 行 = 1.0004。
#: 行は skip したテストにも付く(JUnit の skip 425 件のうち 418 件に行がある)ので、比が一番小さくなるのは
#: 行を全部取り直した直後で、そのとき 実行 27,710 / 収集 28,148 = 0.984。0.95 はそこから 3.4 %(約 970 件)
#: 下で、鮮度の門(行数が session の 95 % 以上)と対になる。0.90 のときは約 2,780 件が消えても通った
#: (2 回目のレビューの指摘)。床が止めるのは「大量に消えた・大量に skip した」で、それより小さい skip の
#: 増加は ``skip_jump`` が前回の記録と比べて要約で知らせる。
SUITE_FLOOR_RATIO = 0.95
#: ``.test_durations`` が読めない木での床(ci.yml の夜間 order-shuffle の ``--min-executed`` と同じ)。
SUITE_FLOOR_ABSOLUTE = 10_000

#: 調べる道具(GitHub の runner にはある)。値 = 実行ファイルの名前の候補。
RUNNER_TOOLS = {
    "cargo": ("cargo",),
    "node": ("node",),
    "Chrome": ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"),
}
#: skip の理由の文面から「その道具が無いための skip」を数えるための型。
#: 前後が ASCII の英字でないことで区切る(``\b`` は日本語の文字も語の一部に数えるので「cargoが無い」を取りこぼす。
#: 区切らないと robust・frustum が Rust に、monochrome が Chrome に当たる)。
TOOL_SKIP_PATTERNS = {
    "cargo": r"(?<![A-Za-z])(cargo|[Rr]ust|rustc)(?![A-Za-z])",
    "node": r"(?<![A-Za-z])(node|Node\.js|npm)(?![A-Za-z])",
    "Chrome": r"(?<![A-Za-z])(Chrome|Chromium|chrome|chromium)(?![A-Za-z])",
}
BLAS_SKIP_PATTERN = r"needs a BLAS with"

#: 全数の skip が基準の記録からこれを超えて増えたら要約で知らせる(基準の件数 × 割合と、件数の下限の大きい方)。
#: 件数は ``comparable_skips``(無い道具の組が同じなら全体。違えば有無の違う道具の skip を引いた件数)。
#: 2026-11-10 の実測は skip 427 件(うち道具が無いため 114 件)。同じ道具の組の run どうしなら線は +43 件
#: (ceaa600d39 と同じ判定)。基準だけ cargo が無かった(98 件)なら、比べる基準は 329 件で線は +33 件。
SKIP_JUMP_RATIO = 0.10
SKIP_JUMP_MIN = 20
#: skip の記録(状態ディレクトリの中)。書くのは verdict が ``SKIP_RECORD_VERDICTS`` の run だけ。
SKIP_BASELINE_FILE = "skip_baseline.json"
#: 記録を書いてよい verdict(全段 ok・追加引数なし・GitHub と同じ条件・BLAS の回し直しも ok)。
#: ``ok_missing_tools`` を入れるのは、手元に無い道具は run ごとに変わらず、入れないと作者の機械では
#: 記録が一度も書けないため(どの道具が無かったかは記録に残し、違えば要約で知らせる)。
SKIP_RECORD_VERDICTS = ("full_ok", "ok_missing_tools")
#: 記録の形の版。2 = ``{"format": 2, "base": <最小の記録>, "last": <最後に書いた run>}``。
#: 1(版の欄が無い ``{"skipped": ...}``)は 2026-11-10 の最初の版が書いたもので、失敗した run の件数の
#: ことがある。捨てると基準が緩む向きになりうるので、基準として読み、次に書くときに最小の規則で 2 へ移す。
SKIP_BASELINE_FORMAT = 2

MARKER = ".fullseye-ci-local"
LOCK_FILE = ".ci_local.lock"
OWNER_FILE = ".ci_local.owner.json"
DEFAULT_STATE_DIR = "~/fullseye-ci-local"
DEFAULT_DISTRO = os.environ.get("FULLSEYE_CI_LOCAL_DISTRO", "Ubuntu-24.04")
#: ``--out`` に前回のものが残っていたら消す成果物(この道具が書く名前だけ)。
OUT_PRODUCTS = ("summary.md", "result.json", "job.json", "meta.json", "junit-full.xml", "junit-gates.xml",
                "junit-core-packaging.xml", "junit-core-wheel.xml", "junit-blas.xml", "setup.log", "ruff.log",
                "pip-audit.log", "regen.log", "gates.log", "core.log", "full-suite.log", "blas.log")

EXIT_OK, EXIT_FAILED, EXIT_USAGE, EXIT_BUSY = 0, 1, 2, 3
#: Ctrl-C で外側が止まったとき(シェルの慣習 128 + SIGINT)。
EXIT_INTERRUPTED = 130


def _log(msg: str) -> None:
    print(f"[ci_local {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _fmt_dur(sec: float) -> str:
    sec = int(round(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


# =============================================================================================
# 純粋な部分(WSL を起動せずにテストできる)
# =============================================================================================

def normalize_phase(name: str) -> str:
    return PHASE_ALIASES.get(name, name)


def select_phases(only: str | None, skip: list[str]) -> list[str]:
    """回す段(順番どおり)。空なら 1 段も走らない = 呼び出し側が失敗にする。"""
    only = normalize_phase(only) if only else None
    skipped = {normalize_phase(s) for s in skip}
    return [k for k in PHASE_KEYS if (only is None or k == only) and k not in skipped]


def partial_reasons(job: dict) -> list[str]:
    """全数でない理由(空なら全段を既定のまま回す run)。"""
    out = []
    if job.get("only"):
        out.append(f"--only {job['only']}")
    if job.get("skip"):
        out.append("--skip " + ",".join(job["skip"]))
    if job.get("pytest_args"):
        out.append("pytest への追加引数 `" + " ".join(job["pytest_args"]) + "`")
    if job.get("pip_audit") is False:
        out.append("--no-pip-audit")
    return out


def deviation_reasons(job: dict, python_versions: dict | None = None) -> list[str]:
    """走る段は同じでも、検査の条件が GitHub の CI と違う理由(空なら同じ条件)。

    ``--no-merge``・``--no-fetch``・fetch できない形の ``--base``・``--allow-other-python``。どれも GitHub が
    検査する木・Python と違うものを検査するので、全部 ok でも結論を「全段 ok」にしない。
    """
    tree = job.get("tree") or {}
    out = []
    if tree.get("mode") == "tip":
        out.append("--no-merge(base との merge でなく、対象の先端だけ)")
    if tree.get("fetched") == "no_fetch":
        out.append("--no-fetch(base は手元の追跡 ref のまま。GitHub の master より古いかもしれない)")
    elif tree.get("fetched") == "not_remote":
        out.append(f"--base {tree.get('base_ref') or '?'} は `<remote>/<branch>` の形でないので fetch していない")
    if job.get("allow_other_python"):
        # 3.11 以外を許しただけで実際がすべて 3.11 なら、条件は同じ(3 回目のレビュー C6)。版を 1 つも読めて
        # いない run は、何で回したか分からないので違う条件に数える
        versions = [str(v) for v in (python_versions or {}).values()]
        other = sorted({v for v in versions if not v.startswith("3.11.")})
        if other:
            out.append(f"--allow-other-python(Python {'・'.join(other)}。CI のこの構成は 3.11)")
        elif not versions:
            out.append("--allow-other-python(venv の Python の版を読めていない。CI のこの構成は 3.11)")
    return out


def _is_count(value) -> bool:
    """0 以上の整数か(bool は int の部分型なので外す)。"""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def skip_record_problem(rec) -> str | None:
    """skip の記録 1 件(基準・旧形式の記録)の型の誤り。正しければ None。

    4 回目のレビュー D1: 型を検めないと、JSON としては読める手書きの記録(``tools_missing`` が数・
    ``skip_reasons`` の値が null・``skipped`` が true)で全数の段が TypeError で毎回落ちた。
    """
    if not isinstance(rec, dict):
        return f"記録が dict でない({type(rec).__name__})"
    if not _is_count(rec.get("skipped")):
        return f"`skipped` が 0 以上の整数でない({rec.get('skipped')!r:.40})"
    for key in ("tools_missing", "apt_missing"):
        if key in rec and not (isinstance(rec[key], list) and all(isinstance(t, str) for t in rec[key])):
            return f"`{key}` が文字列の list でない({rec[key]!r:.40})"
    if "skip_reasons" in rec:
        reasons = rec["skip_reasons"]
        if not (isinstance(reasons, dict) and all(isinstance(r, str) and _is_count(n) for r, n in reasons.items())):
            return "`skip_reasons` が「文字列 → 0 以上の整数」の dict でない"
    return None


def parse_skip_baseline(text: str) -> dict:
    """skip の記録ファイルの中身を読む。返り値 = ``{"state": "ok" | "unreadable", "base", "accepted", "reason"}``。

    ``base`` は基準(これまでの記録の最小)。旧形式(版の欄が無い)は ``legacy`` を付けて返す。``accepted`` は
    ``--accept-skips`` で受け入れた履歴の list。空・BOM 付き・JSON でない・版の違う・型の違う記録は、どれも
    ``unreadable`` で、理由を ``reason`` に入れる(「記録が無い」と取り違えると、次の run が黙って上書きする)。
    """
    def bad(reason: str) -> dict:
        return {"state": "unreadable", "base": None, "accepted": [], "reason": reason}

    if text.startswith("\ufeff"):
        return bad("BOM 付き(この道具は BOM なしの UTF-8 で書く)")
    if not text.strip():
        return bad("空のファイル")
    try:
        data = json.loads(text)
    except ValueError as exc:
        return bad(f"JSON でない({type(exc).__name__}: {str(exc)[:80]})")
    if not isinstance(data, dict):
        return bad(f"最上位が dict でない({type(data).__name__})")
    if "format" not in data:
        problem = skip_record_problem(data)
        if problem:
            return bad(f"旧形式の記録の型が違う: {problem}")
        return {"state": "ok", "base": dict(data, legacy=True), "accepted": [], "reason": None}
    fmt = data["format"]
    if not (type(fmt) is int and fmt == SKIP_BASELINE_FORMAT):
        return bad(f"版が違う(`format` = {fmt!r:.20}。この道具が読むのは {SKIP_BASELINE_FORMAT})")
    if "base" not in data:
        return bad("`base`(基準)が無い")
    problem = skip_record_problem(data["base"])
    if problem:
        return bad(f"基準の型が違う: {problem}")
    accepted = data.get("accepted", [])
    if not (isinstance(accepted, list) and all(isinstance(a, dict) for a in accepted)):
        return bad("`accepted`(受け入れた履歴)が dict の list でない")
    return {"state": "ok", "base": dict(data["base"]), "accepted": list(accepted), "reason": None}


def comparable_skips(prev: dict, now: dict) -> tuple[int, int, list[str]]:
    """基準と今回の、比べる件数 = (基準側, 今回側, 一言の list)。

    無い道具の組が同じなら、どちらも全体の件数(何も引かない = ceaa600d39 と同じ判定)。違うときだけ、
    基準でだけ無かった道具の skip を基準から、今回だけ無い道具の skip を今回から引く(理由の文面からの推定)。
    5 回目のレビュー E1: 両側から無い道具の skip を全部引くと、道具の名前を理由に含む skip(``node2vec`` が node に
    当たる・Rust 拡張)が何件増えても知らせなくなった。E7: 引くべき側に ``skip_reasons`` が無ければ引けないので
    全体で比べ、そう言う。apt に依る skip は理由の文面から数えられないので、どちらでも引かない。
    """
    was, got = set(prev.get("tools_missing") or []), set(now.get("tools_missing") or [])
    before, after = int(prev.get("skipped") or 0), int(now.get("skipped") or 0)
    notes: list[str] = []
    for side, rec, only in (("基準", prev, sorted(was - got)), ("今回", now, sorted(got - was))):
        if not only:
            continue
        if "skip_reasons" not in rec:
            notes.append(f"{side}の記録に skip の理由が無いので、{side}だけ無い道具({'、'.join(only)})の skip を"
                         "引けなかった(全体の件数で比べた)")
            continue
        n, _ = github_only_skips(rec.get("skip_reasons") or {}, only)
        if side == "基準":
            before = max(0, before - n)
        else:
            after = max(0, after - n)
    return before, after, notes


def skip_jump_allowed(before: int) -> int:
    """知らせる線(基準からの増加がこれを超えたら知らせる)。"""
    return max(SKIP_JUMP_MIN, math.ceil(before * SKIP_JUMP_RATIO))


def baseline_condition_notes(prev: dict, now: dict) -> list[str]:
    """基準と今回で、手元に無い道具・apt パッケージが違うときの一言(跳ねた行にも、跳ねない行にも付ける)。"""
    notes = []
    was, got = sorted(prev.get("tools_missing") or []), sorted(now.get("tools_missing") or [])
    if was != got:
        notes.append(f"**手元に無い道具が基準と違う**(基準 {'、'.join(was) or 'なし'} → 今回 {'、'.join(got) or 'なし'})"
                     "。有無の違う道具の skip だけを、その道具が無かった側の件数から引いてある(理由の文面からの推定)")
    got_apt = sorted(now.get("apt_missing") or [])
    if "apt_missing" in prev or got_apt:
        was_apt = sorted(prev.get("apt_missing") or [])
        if was_apt != got_apt:
            shown = ("記録なし" if "apt_missing" not in prev else "、".join(was_apt) or "なし")
            notes.append(f"**手元に無い apt パッケージが基準と違う**(基準 {shown} → 今回 {'、'.join(got_apt) or 'なし'})"
                         "。apt に依る skip は理由の文面から数えられないので、件数からは引いていない")
    return notes


def skip_jump(prev: dict | None, now: dict, where: str = SKIP_BASELINE_FILE) -> str | None:
    """全数の skip が基準の記録から大きく増えたときに要約へ出す 1 行(増えていなければ None)。失敗にはしない。

    ``prev`` は基準(これまでの記録の最小)。前回の run と比べると、線以内の増加を繰り返すたびに基準が
    上がり、一度も知らせずに数百件が基準に入る(3 回目のレビュー C2 のラチェット)。比べるのは
    ``comparable_skips``、線もその基準側の件数で決める。``where`` は記録ファイルの場所(要約に出す形)。

    件数の床(``SUITE_FLOOR_RATIO``)が止めるのは「大量に消えた」まで。その手前 —— full venv の optional 依存が
    1 つ壊れて数十〜数百件が skip に回る —— は床を割らないので、基準の記録と比べる。
    """
    if skip_record_problem(prev) or skip_record_problem(now):
        return None
    before, after, cant = comparable_skips(prev, now)
    allowed = skip_jump_allowed(before)
    if after - before <= allowed:
        return None
    old = prev.get("skip_reasons") or {}
    grew = sorted(((n - int(old.get(r, 0)), r) for r, n in (now.get("skip_reasons") or {}).items()
                   if n > int(old.get(r, 0))), key=lambda t: (-t[0], t[1]))
    top = ";".join(f"+{d:,} 件「{r.replace('|', '/')}」" for d, r in grew[:3])
    off_before, off_after = prev["skipped"] - before, now["skipped"] - after
    breakdown = ""
    if off_before or off_after:
        breakdown = (f"。有無の違う道具の skip を引いて比べた(全体 {prev['skipped']:,} → {now['skipped']:,} 件から、"
                     f"基準でだけ無かった道具の skip {off_before:,} 件・今回だけ無い道具の skip {off_after:,} 件を引いた)")
    notes = "".join("。" + n for n in cant + baseline_condition_notes(prev, now))
    return (f"**skip が基準の記録から大きく増えた**: {before:,} → {after:,} 件(+{after - before:,}。知らせる線は "
            f"+{allowed:,})" + breakdown
            + f"。基準 = {prev.get('when', '?')} の `{str(prev.get('sha', '?'))[:12]}`(これまでの最小)"
            + (f"。増えた理由の上位: {top}" if top else "") + notes
            + "。床を割っていなくても、依存が壊れて skip に回った可能性がある(失敗にはしていない。基準は動かして"
              "いない。正当な増加なら `--accept-skips \"<理由>\"` を付けて回し直すと、その run の件数を基準にする。"
              f"記録 `{where}`)")


def junit_counts(path: Path) -> dict:
    """JUnit を数える。無い・壊れている場合は ``broken`` に理由を入れる(例外にしない)。"""
    res = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "xfailed": 0, "executed": 0, "failed": [],
           "skip_reasons": {}, "skipped_cases": [], "broken": None}
    if not Path(path).exists():
        res["broken"] = "JUnit が無い"
        return res
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        res["broken"] = f"JUnit が壊れている({type(exc).__name__})"
        return res
    for case in root.iter("testcase"):
        res["tests"] += 1
        cls, nm = case.get("classname", ""), case.get("name", "")
        name = f"{cls}::{nm}"
        if case.find("failure") is not None:
            res["failures"] += 1
            res["failed"].append(name)
        elif case.find("error") is not None:
            res["errors"] += 1
            res["failed"].append(name + "(error)")
        elif case.find("skipped") is not None:
            sk = case.find("skipped")
            if sk.get("type") == "pytest.xfail":
                res["xfailed"] += 1
            else:
                res["skipped"] += 1
                reason = " ".join((sk.get("message") or "(理由なし)").split())[:140]
                res["skip_reasons"][reason] = res["skip_reasons"].get(reason, 0) + 1
                res["skipped_cases"].append([cls, nm, reason])
    res["executed"] = res["tests"] - res["skipped"] - res["xfailed"]
    return res


def suite_floor(n_durations: int | None) -> tuple[int, str]:
    """全数の段の実行件数の床と、その出どころ。"""
    if not n_durations:
        return SUITE_FLOOR_ABSOLUTE, f".test_durations が読めないので固定の {SUITE_FLOOR_ABSOLUTE:,} 件"
    floor = math.ceil(n_durations * SUITE_FLOOR_RATIO)
    return floor, f".test_durations {n_durations:,} 行 × {SUITE_FLOOR_RATIO:.2f}"


def junit_verdict(jc: dict, floor: int | None = None) -> str | None:
    """JUnit だけから言える失敗の理由(無ければ None)。壊れ・0 件・床未満は通さない。"""
    if jc.get("broken"):
        return jc["broken"]
    if jc["tests"] == 0:
        return "1 件も走っていない(JUnit が 0 件)"
    if floor is not None and jc.get("executed", 0) < floor:
        return f"実行件数 {jc.get('executed', 0):,} が床 {floor:,} を下回る"
    return None


def count_durations(path: Path) -> int | None:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return len(data) if isinstance(data, dict) else None


def parse_gate_list(text: str) -> list[str]:
    return [n for n in (ln.split("#", 1)[0].strip() for ln in text.splitlines()) if n]


def github_only_skips(skip_reasons: dict, missing_tools: list[str]) -> tuple[int, dict]:
    """手元に無い道具が理由の skip(理由の文面からの推定)。返り値 = (重複なしの合計, 道具ごと)。"""
    per = {t: 0 for t in missing_tools if t in TOOL_SKIP_PATTERNS}
    total = 0
    for reason, n in skip_reasons.items():
        hit = [t for t in per if re.search(TOOL_SKIP_PATTERNS[t], reason)]
        for t in hit:
            per[t] += n
        if hit:
            total += n
    return total, per


def missing_tools_of(st: dict) -> tuple[bool, str, int]:
    """道具の欠け: (欠けがある・調べていない, 無い道具の文, 道具が無いための skip の件数)。

    件数は全数の JUnit の skip の理由の文面からの推定(``github_only_skips``)。apt パッケージに依る skip は
    理由の文面から数えられないので件数に入らない(文の側に書く)。
    """
    if not st.get("tools_probed"):
        return True, "(道具の有無を調べていない)", 0
    missing = list(st.get("tools_missing") or [])
    apt = list(st.get("apt_missing") or [])
    total, _ = github_only_skips((st.get("junit_full") or {}).get("skip_reasons") or {}, missing)
    what = "、".join(missing + [f"apt:{p}" for p in apt])
    if apt:
        what += "。apt に依る skip は理由の文面から数えられないので件数に入っていない"
    return bool(missing or apt), what, total


def fill_not_run(results: dict, job: dict, stopped_at: str | None, crash: str | None, busy: bool = False) -> dict:
    """走らなかった段に「未実行」と理由を入れる(表から消さない)。"""
    selected = set(job.get("selected") or [])
    out = dict(results)
    for key in PHASE_KEYS:
        if key in out:
            continue
        if key not in selected:
            why = f"--only {job['only']}" if job.get("only") else "--skip"
        elif stopped_at:
            why = f"{stopped_at} が落ちて止めた。--keep-going で最後まで"
        elif busy:
            why = "状態ディレクトリが使用中"
        elif crash:
            why = "準備で止まった"
        else:
            why = "理由不明"
        out[key] = {"state": "not_run", "detail": f"未実行({why})", "sec": None}
    return out


def exit_code(st: dict) -> int:
    results = st["results"]
    ran = [k for k in PHASE_KEYS if results.get(k, {}).get("state") in ("ok", "failed")]
    if st.get("busy"):
        return EXIT_BUSY
    if st.get("crash") or st.get("stopped_at") or not ran:
        return EXIT_FAILED
    return EXIT_OK if all(results[k]["state"] == "ok" for k in ran) else EXIT_FAILED


def verdict(st: dict) -> str:
    """機械が読む結論(``result.json`` の ``verdict``)。終了コード 0 の中身を 4 つに分ける。

    ``full_ok`` だけが「5 段を既定のまま、GitHub と同じ条件(fetch した base との merge・Python 3.11・runner に
    ある道具が全部ある)で回して全部 ok」。``partial_ok`` = 走った段は ok だが全数ではない。``deviating_ok`` =
    5 段とも ok だが条件が違う。``ok_missing_tools`` = 5 段とも同じ条件で ok だが、手元に無い道具(cargo・node・
    Chrome・apt)のせいで GitHub では走るテストが手元では skip した(道具を調べていない run も含む)。
    """
    code = exit_code(st)
    if code == EXIT_BUSY:
        return "busy"
    if code != EXIT_OK:
        return "failed"
    job, results = st["job"], st["results"]
    ran = [k for k in PHASE_KEYS if results.get(k, {}).get("state") in ("ok", "failed")]
    if partial_reasons(job) or len(ran) < len(PHASE_KEYS):
        return "partial_ok"
    if deviation_reasons(job, st.get("python_versions")):
        return "deviating_ok"
    if missing_tools_of(st)[0]:
        return "ok_missing_tools"
    return "full_ok"


#: 端末の最後の行の一言(``verdict_line``)。``ok_missing_tools`` は件数を入れるので関数の中で作る。
VERDICT_WORDS = {
    "full_ok": "全段・GitHub と同じ条件で ok",
    "deviating_ok": "GitHub と違う条件。緑の証拠にしない",
    "partial_ok": "部分実行(全数ではない)。緑の証拠にしない",
    "failed": "失敗",
    "busy": "状態ディレクトリを別の ci_local が使っている。実行していない",
}


def verdict_line(result: dict | None) -> str:
    """端末の最後に出す 1 行(``result.json`` の中身から)。読めなければ「不明」と言い、緑にしない。"""
    v = result.get("verdict") if isinstance(result, dict) else None
    if v == "ok_missing_tools":
        tools = [str(t) for t in (result.get("tools_missing") or [])]
        tools += [f"apt:{p}" for p in (result.get("apt_missing") or [])]
        n = result.get("github_only_skips")
        word = (f"全段 ok。ただし手元に無い道具({'、'.join(tools) or '有無を調べていない'})のため "
                f"{n if isinstance(n, int) else '?'} 件は GitHub でしか確かめられない")
    elif v in VERDICT_WORDS:
        word = VERDICT_WORDS[v]
    else:
        return "verdict: 不明 — result.json が無いか読めない。緑の証拠にしない"
    return f"verdict: {v} — {word}" + "".join("。" + t for t in skip_baseline_tail(result.get("skip_baseline")))


def skip_baseline_tail(info) -> list[str]:
    """最後の行の末尾に足す skip の基準の短い通知(``result.json`` の ``skip_baseline`` から)。

    4 回目のレビュー D2: 跳ねの通知が要約の 4 行目にしか無く、最後の行だけを見る人には見えなかった。
    verdict の語と ``verdict: <語> — `` の形は変えない(機械が読む)。
    """
    if not isinstance(info, dict):
        return []
    out = []
    jump = info.get("jump")
    if _is_count(jump) and jump > 0:
        out.append(f"skip が基準より +{jump:,} 件(要約の先頭を見る)")
    if info.get("accepted") is True:
        out.append("skip の基準を受け入れた(--accept-skips)")
    if info.get("state") == "unreadable":
        out.append("skip の記録を読めない(比べていない)")
    return out


def host_stop_line(word: str, why: str) -> str:
    """外側が内側を走らせずに止まったときの最後の行(``result.json`` の verdict の種類は増やさない)。"""
    return f"verdict: {word} — {why}"


def junit_case_ids(path: Path) -> set | None:
    """JUnit にある (classname, name) の集合。読めなければ None。"""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None
    return {(c.get("classname", ""), c.get("name", "")) for c in root.iter("testcase")}


def blas_rerun_outcome(cases: list, rerun_ids: set | None, rerun_skipped: set) -> dict:
    """BLAS の回し直しで、最初に skip した各テストがどうなったか(走った / skip のまま / 回し直しに現れない)。"""
    ids = rerun_ids or set()
    absent = [c for c in cases if tuple(c) not in ids]
    still = [c for c in cases if tuple(c) in ids and tuple(c) in rerun_skipped]
    return {"first": len(cases), "recovered": len(cases) - len(absent) - len(still),
            "still_skipped": len(still), "absent": len(absent)}


def tree_line(tree: dict) -> str:
    """検査した木が何と何か(両方の sha を必ず書く)。"""
    sha, base, ref = tree.get("sha", "?")[:12], (tree.get("base_sha") or "?")[:12], tree.get("base_ref") or "?"
    fetched = {"yes": "fetch 済み", "no_fetch": "**fetch していない**(--no-fetch。手元の追跡 ref のまま)",
               "not_remote": "`<remote>/<branch>` の形でないので fetch していない"}.get(tree.get("fetched"), "fetch は不明")
    behind, ahead = tree.get("behind"), tree.get("ahead")
    mode = tree.get("mode")
    if mode == "merge" and not tree.get("tested"):
        return (f"- 検査した木: **無い** —— 対象 `{sha}` と `{ref}` `{base}`({fetched})の merge を作れなかった"
                f"(対象は {ref} から {behind} commit 遅れ・{ahead} commit 先)")
    if mode == "merge":
        tested = tree["tested"][:12]
        return (f"- 検査した木: `{tested}` = 対象 `{sha}` と `{ref}` `{base}`({fetched})の merge。"
                f"Linux 側の clone の中で作った(対象は {ref} から {behind} commit 遅れ・{ahead} commit 先)")
    if mode == "ahead":
        return (f"- 検査した木: 対象 `{sha}` の先端。`{ref}` `{base}`({fetched})は対象の祖先なので、"
                f"merge しても同じ木({ahead} commit 先)")
    if mode == "is_base":
        return f"- 検査した木: 対象 `{sha}` = `{ref}` `{base}`({fetched})そのもの。merge するものが無い"
    if mode == "behind":
        return (f"- 検査した木: 対象 `{sha}` の先端。対象は `{ref}` `{base}`({fetched})の祖先({behind} commit 遅れ)で、"
                "merge すると master そのものになるため")
    extra = f"`{ref}` `{base}`({fetched})から {behind} commit 遅れ・{ahead} commit 先" if tree.get("base_sha") \
        else "base は解決していない"
    return (f"- 検査した木: **対象 `{sha}` の先端だけ(--no-merge)**。GitHub の PR の CI は base との merge commit を"
            f"検査するので、同じ木ではない({extra})")


def render_summary(st: dict) -> str:
    """要約(Markdown)。状態の dict だけから作る(ファイルもプロセスも触らない)。"""
    job, results = st["job"], st["results"]
    partial = partial_reasons(job)
    deviating = deviation_reasons(job, st.get("python_versions"))
    ran = [k for k in PHASE_KEYS if results.get(k, {}).get("state") in ("ok", "failed")]
    failed = [k for k in ran if results[k]["state"] == "failed"]
    not_run = [k for k in PHASE_KEYS if k not in ran]
    tools_mark = ""
    if st.get("tools_probed") and (st.get("tools_missing") or st.get("apt_missing")):
        tools_mark = " — 手元に無い道具あり(GitHub でしか確かめられないテストがある)"
    elif not st.get("tools_probed") and ran:
        tools_mark = " — 道具の有無を調べていない"
    lines = ["### 手元の CI 相当の検査(Linux)— tools/ci_local.py"
             + (" — 部分実行(全数ではない)" if partial else "")
             + (" — GitHub の CI とは違う条件" if deviating else "") + tools_mark, ""]
    if st.get("busy"):
        concl = "**実行していない** —— 状態ディレクトリを別の ci_local が使っている"
    elif not ran:
        concl = "**失敗 —— 1 段も走っていない**"
    elif failed or st.get("crash") or st.get("stopped_at"):
        concl = "**失敗**" + (": " + "、".join(PHASE_LABEL[k] for k in failed) if failed else "")
    elif partial or not_run:
        concl = "**部分実行(全数ではない)** —— 走った段(" + "、".join(PHASE_LABEL[k] for k in ran) + ")は ok"
    elif deviating:
        concl = ("**GitHub の CI とは違う条件での検査** —— 走った段(" + "、".join(PHASE_LABEL[k] for k in ran)
                 + ")は ok")
    elif missing_tools_of(st)[0]:
        _, what, n_gh = missing_tools_of(st)
        concl = (f"**全段 ok —— ただし手元に無い道具のため {n_gh:,} 件は GitHub でしか確かめられない**"
                 f"({len(ran)} 段。無い道具: {what})")
    else:
        concl = f"**全段 ok**({len(ran)} 段)"
    if partial and ran:
        concl += "。絞った引数: " + " / ".join(partial) + "。**この結果を全数の証拠にしない**"
    if deviating and ran:
        concl += ("。GitHub と違う点: " + " / ".join(deviating)
                  + "。**この結果を GitHub の CI が通る証拠にしない**")
    if not_run and not st.get("busy"):
        concl += "。未実行: " + "、".join(PHASE_LABEL[k] for k in not_run)
    lines.append(f"- 結論: {concl}")
    missing = st.get("tools_missing") or []
    apt_missing = st.get("apt_missing") or []
    if st.get("tools_probed"):
        if missing or apt_missing:
            what = "、".join(missing + [f"apt:{p}" for p in apt_missing])
            lines.append(f"- **手元に無い道具(GitHub の runner にはある)**: {what} —— これに依るテストは手元では skip する"
                         "(GitHub でしか確かめられない。件数は下の skip の集計)")
        else:
            lines.append("- 手元に無い道具: なし(cargo・node・Chrome・apt の 6 個とも有る)")
    if st.get("skip_jump"):
        lines.append(f"- {st['skip_jump']}")
    for note in st.get("skip_notices") or []:
        lines.append(f"- {note}")
    lines.append(tree_line(st.get("tree") or {}))
    lines.append(f"- 対象: `{job.get('sha', '?')[:12]}` {job.get('subject', '')}({job.get('target', '?')})")
    n_dirty = job.get("dirty_count", 0)
    if n_dirty:
        lines.append(f"- **作業木に未 commit の変更 {n_dirty} 件 —— 検査していない**(commit だけを検査する)")
    elif job.get("dirty_applies"):
        lines.append("- 作業木: きれい(未 commit の変更なし)")
    else:
        lines.append("- 作業木: HEAD 以外の ref を検査したので作業木の状態は無関係")
    if st.get("env_line"):
        lines.append(f"- 環境: {st['env_line']}")
    if st.get("versions"):
        lines.append(f"- 版: {st['versions']}")
    if st.get("gates_source"):
        lines.append(f"- 門の一覧: {st['gates_source']}")
    for note in st.get("setup_notes") or []:
        lines.append(f"- {note}")
    for note in job.get("notes") or []:
        lines.append(f"- 注: {note}")
    if st.get("loadavg"):
        lines.append(f"- 終了時の load average: {st['loadavg']}")
    lines += ["", "| 段 | 結果 | 所要時間 |", "|---|---|---|"]
    for key in PHASE_KEYS:
        r = results.get(key) or {"state": "not_run", "detail": "未実行", "sec": None}
        dur = _fmt_dur(r["sec"]) if r.get("sec") is not None else "—"
        lines.append(f"| {PHASE_LABEL[key]} | {r['detail']} | {dur} |")
    lines.append(f"| 合計(準備を含む) | | {_fmt_dur(st.get('total', 0))} |")
    if st.get("stopped_at"):
        lines += ["", f"**{st['stopped_at']} が落ちたので止めた**(最後まで回すなら --keep-going)。"]
    if st.get("crash"):
        lines += ["", ("**実行していない**: " if st.get("busy") else "**途中で止まった**: ") + st["crash"]]
    for text in st.get("remarks") or []:
        lines += ["", text]
    gj = st.get("junit_gates") or {}
    if gj.get("failed"):
        lines += ["", f"落ちた門({len(gj['failed'])}):", ""] + [f"- `{n}`" for n in gj["failed"][:40]]
    jc = st.get("junit_full") or {}
    if jc.get("failed"):
        lines += ["", f"落ちたテスト({len(jc['failed'])}):", ""]
        lines += [f"- `{n}`" for n in jc["failed"][:80]]
        if len(jc["failed"]) > 80:
            lines.append(f"- ほか {len(jc['failed']) - 80} 件(junit-full.xml)")
    reasons = jc.get("skip_reasons") or {}
    if reasons:
        total_gh, per = github_only_skips(reasons, missing)
        blas = st.get("blas") or {}
        lines += ["", f"skip の理由(全数の JUnit、{jc.get('skipped', 0):,} 件・{len(reasons):,} 種)。"
                      f"**手元の道具が無いための skip = {total_gh:,} 件**(理由の文面からの推定。GitHub の runner では走る = "
                      "GitHub でしか確かめられない"
                      + ("。内訳: " + "、".join(f"{t} {n}" for t, n in per.items()) if per else "") + ")。"]
        if blas:
            stuck = blas.get("still_skipped", 0) + blas.get("absent", 0)
            lines.append(f"BLAS のスレッドを絞ったための skip {blas.get('first', 0)} 件は、絞らずに直列で回し直した: "
                         f"{blas.get('recovered', 0)} 件が走った"
                         + (f"、**{stuck} 件は走らないまま = 失敗**(skip のまま {blas.get('still_skipped', 0)} 件・"
                            f"回し直しに現れない {blas.get('absent', 0)} 件)" if stuck else "")
                         + f"({blas.get('detail', '')})。")
        lines += ["", "| 件数 | 理由 |", "|---|---|"]
        top = sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))
        lines += [f"| {n:,} | {r.replace('|', '/')} |" for r, n in top[:15]]
        if len(top) > 15:
            lines.append(f"| {sum(n for _, n in top[15:]):,} | ほか {len(top) - 15} 種(result.json の skip_reasons) |")
    lines += ["", "確かめていないもの(この道具の範囲外。GitHub の CI が見る): Python 3.12 / 3.14 / 3.13(週次)/ 3.15 preview、"
              "片ごとの session の見え方(`test_test_durations_is_fresh` など)、直列の順序と夜間の order-shuffle、"
              "CI の道具の pip-audit(警告のみ)、docs-only ジョブ、"
              + ("" if job.get("cov") else "coverage(--cov なし)、")
              + "fetch のあとに進んだ master、その日の最新の依存(venv を揃えた時点の版)。"
              "手元は xdist の並列(CI の片の中は直列)なので、並列でだけ落ちる手元だけの赤もありうる。"]
    text = "\n".join(lines) + "\n"
    for old, new in st.get("scrub") or []:
        if old:
            text = text.replace(old, new)
    return text


# =============================================================================================
# 外側(Windows / Linux の作業木): 何を検査するかを決め、内側を起動する
# =============================================================================================

class UsageError(Exception):
    """引数・起動場所の誤り(終了コード 2)。"""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


def _git_ok(repo: Path, *args: str) -> str | None:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip() if r.returncode == 0 else None


def _to_wsl(path: Path, distro: str) -> str:
    """Windows の絶対パスを WSL のパスに(``wslpath -u``)。"""
    out = subprocess.run(["wsl.exe", "-d", distro, "--exec", "wslpath", "-u", str(path).replace("\\", "/")],
                         check=True, capture_output=True)
    return out.stdout.decode("utf-8", "replace").strip()


def is_fullseye_pyproject(text: str) -> bool:
    return re.search(r'(?m)^name\s*=\s*"fullseye"\s*$', text) is not None


def check_state_dir_arg(value: str, on_windows: bool) -> str:
    """状態ディレクトリは Linux 側のパス。Windows のパスに化けていたら断る。"""
    if on_windows and (re.match(r"^[A-Za-z]:[\\/]", value) or "\\" in value):
        raise UsageError(f"--state-dir は Linux(WSL)側のパスで渡す(`~/...` か `/home/...`)。受け取った値: {value}"
                         "(Git Bash は `/...` と `~/...` を Windows のパスに書き換える。引用符で囲んだ '~/...' か、"
                         "MSYS_NO_PATHCONV=1 を付けた `/home/...` で渡す)")
    if not (value.startswith("~/") or value == "~" or value.startswith("/")):
        raise UsageError(f"--state-dir は絶対パスか `~/...` で渡す。受け取った値: {value}")
    return value


def _fetch_ref(repo: Path, refname: str, remotes: list[str]) -> bool:
    """``<remote>/<branch>`` の形なら fetch し直す。fetch したら True。失敗は例外。"""
    remote, _, branch = refname.partition("/")
    if remote not in remotes or not branch:
        return False
    r = subprocess.run(["git", "-C", str(repo), "fetch", "-q", remote, branch], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise UsageError(f"`git fetch {remote} {branch}` が失敗した(オフラインなら --no-fetch。その場合、手元の追跡 ref の"
                         f"ままの {refname} を使い、要約にそう書く): {r.stderr.strip()[:300]}")
    return True


def build_job(args: argparse.Namespace, cwd: Path, environ: dict) -> tuple[dict, Path, Path]:
    """何を検査するかを決める。返り値 = (job, 出力先, git の common dir)。"""
    selected = select_phases(args.only, args.skip)
    if not selected:
        raise UsageError("この引数の組み合わせでは 1 段も走らない(--only と --skip を見直す)")
    accept = None
    if args.accept_skips is not None:
        accept = " ".join(str(args.accept_skips).split())[:200]  # 要約の 1 行に入る形(改行・表の区切りを潰す)
        if not accept:
            raise UsageError("--accept-skips には理由を渡す(空にできない。記録に残す): --accept-skips \"<理由>\"")
        accept = accept.replace("|", "/")
    top = _git_ok(cwd, "rev-parse", "--show-toplevel")
    if top is None:
        raise UsageError("git の作業木の中で起動する(cwd が repo でない)")
    repo = Path(top)
    remotes = _git(repo, "remote").split()
    fetched = "no_fetch"
    if not args.no_fetch:
        fetched = "yes" if _fetch_ref(repo, args.base, remotes) else "not_remote"
        if args.ref != args.base:
            _fetch_ref(repo, args.ref, remotes)
    sha = _git_ok(repo, "rev-parse", "--verify", "--quiet", f"{args.ref}^{{commit}}")
    if not sha:
        raise UsageError(f"--ref {args.ref} を commit に解決できない")
    pyproject = _git_ok(repo, "show", f"{sha}:pyproject.toml")
    if pyproject is None or not is_fullseye_pyproject(pyproject):
        raise UsageError("cwd の repo は Fullseye ではない(検査する commit の pyproject.toml の name が fullseye でない)。"
                         "Fullseye の作業木の中で起動する")
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    head = _git(repo, "rev-parse", "HEAD")
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    subject = _git(repo, "log", "-1", "--format=%s", sha)
    dirty_count = 0
    if sha == head:
        dirty_count = len([ln for ln in _git(repo, "status", "--porcelain", "--untracked-files=normal").splitlines()
                           if ln])
    base_sha = _git_ok(repo, "rev-parse", "--verify", "--quiet", f"{args.base}^{{commit}}")
    tree = {"sha": sha, "base_ref": args.base, "base_sha": base_sha, "fetched": fetched, "behind": None,
            "ahead": None}
    if base_sha:
        behind, ahead = _git(repo, "rev-list", "--left-right", "--count", f"{base_sha}...{sha}").split()
        tree["behind"], tree["ahead"] = int(behind), int(ahead)
    if args.no_merge:
        tree["mode"] = "tip"
    elif not base_sha:
        raise UsageError(f"--base {args.base} を解決できない(merge の相手が無い)。先端だけを検査するなら --no-merge")
    elif base_sha == sha:
        tree["mode"] = "is_base"
    elif tree["behind"] == 0:
        tree["mode"] = "ahead"
    elif tree["ahead"] == 0:
        tree["mode"] = "behind"
    else:
        tree["mode"] = "merge"

    on_windows = os.name == "nt"
    state_dir = check_state_dir_arg(args.state_dir or environ.get("FULLSEYE_CI_LOCAL_DIR") or DEFAULT_STATE_DIR,
                                    on_windows)
    workers = args.workers if args.workers is not None else int(environ.get("FULLSEYE_CI_LOCAL_WORKERS") or 12)
    if workers < 1:
        raise UsageError("-n は 1 以上")
    notes: list[str] = []
    lock = environ.get("FULLSEYE_GPU_LOCK")
    if lock and Path(lock).exists():
        notes.append("GPU ロックが取られている(GPU の重い処理が並走中の可能性。所要時間は目安)")
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = (Path(args.out).resolve() if args.out
           else Path(tempfile.gettempdir()) / "fullseye-ci-local" / f"{stamp}-{sha[:10]}")
    job = {
        "sha": sha, "ref": args.ref, "subject": subject, "branch": branch,
        "target": f"HEAD({branch})" if sha == head else args.ref,
        "dirty_count": dirty_count, "dirty_applies": sha == head, "host": platform.platform(), "notes": notes,
        "tree": tree, "selected": selected,
        "only": normalize_phase(args.only) if args.only else None,
        "skip": sorted({normalize_phase(s) for s in args.skip}),
        "pytest_args": list(args.pytest_args), "pip_audit": not args.no_pip_audit,
        "state_dir": state_dir, "workers": workers, "dist": args.dist, "cov": args.cov,
        "keep_going": args.keep_going, "rebuild": args.rebuild, "refresh_hours": args.refresh_hours,
        "python": args.python, "allow_other_python": args.allow_other_python,
        "require_tools": args.require_tools, "install_apt": args.install_apt, "accept_skips": accept,
    }
    return job, out, common


def prepare_out(out: Path) -> None:
    """出力先を作り、前回の成果物(この道具が書く名前だけ)を消す。"""
    out.mkdir(parents=True, exist_ok=True)
    for name in OUT_PRODUCTS:
        (out / name).unlink(missing_ok=True)


def _host_main(args: argparse.Namespace) -> int:
    """外側。止まり方が何であっても、端末の最後の行を ``verdict: …`` にする(4 回目のレビュー D5)。

    ``wsl.exe`` が無い・Ctrl-C・引数の誤りで、トレースバックか stderr の 1 行で終わっていた。最後の行を機械で
    読む用途のため、トレースバックを先に出してから最後の行を出す。終了コードは非 0 のまま。
    """
    try:
        return _host_run(args)
    except UsageError as exc:
        print(f"ci_local: {exc}", file=sys.stderr, flush=True)
        print(host_stop_line("usage", "引数か起動場所の誤り。実行していない"), flush=True)
        return EXIT_USAGE
    except KeyboardInterrupt:
        traceback.print_exc()
        sys.stderr.flush()
        print(host_stop_line("failed", "中断した(Ctrl-C)。緑の証拠にしない"), flush=True)
        return EXIT_INTERRUPTED
    except Exception as exc:  # noqa: BLE001 — 最後の行を出してから非 0 で終わる(トレースバックはその前に出す)
        traceback.print_exc()
        sys.stderr.flush()
        print(host_stop_line("failed", f"外側が止まった({type(exc).__name__})。緑の証拠にしない"), flush=True)
        return EXIT_FAILED


def _host_run(args: argparse.Namespace) -> int:
    job, out, common = build_job(args, Path.cwd(), dict(os.environ))
    prepare_out(out)
    me = Path(__file__).resolve()
    _log(f"検査する commit: {job['sha'][:10]} {job['subject'][:60]} ({job['target']})、木 = {job['tree']['mode']}")
    if job["dirty_count"]:
        _log(f"作業木に未 commit の変更 {job['dirty_count']} 件(検査しない。要約に件数を書く)")
    job_path = out / "job.json"
    if os.name == "nt":
        d = args.distro
        job["source"], job["out"] = _to_wsl(common, d), _to_wsl(out, d)
        cmd = ["wsl.exe", "-d", d, "--cd", "~", "--exec", "python3", _to_wsl(me, d), "--inside",
               job["out"].rstrip("/") + "/job.json"]
    else:
        job["source"], job["out"] = str(common), str(out)
        cmd = [sys.executable, str(me), "--inside", str(job_path)]
    # 状態ディレクトリと並列数は、環境変数ではなく引数で内側へ渡す(Windows の環境変数は WSLENV 無しでは WSL に届かない)
    cmd += ["--state-dir", job["state_dir"], "-n", str(job["workers"])]
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding="utf-8")
    rc = subprocess.call(cmd)
    summary = out / "summary.md"
    if summary.exists():  # 前回のものは prepare_out で消してあるので、あればこの run のもの
        print()
        print(summary.read_text(encoding="utf-8"))
        _log(f"要約: {summary}")
    else:
        _log("要約が書かれなかった(内側が要約の前に落ちた)")
        rc = rc or EXIT_FAILED
    try:
        result = json.loads((out / "result.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        result = None
    # 最後の行に verdict(終了コード 0 には 4 つの意味がある。終了コードの意味は変えない —— 変えると
    # --only や --no-fetch の 0 が「落ちた」と区別できなくなる。区別はこの行と result.json でする)
    print(verdict_line(result), flush=True)
    return rc


# =============================================================================================
# 内側(Linux): 排他を取り、検査する木を揃え、5 段を回し、要約を書く
# =============================================================================================

class Busy(Exception):
    """状態ディレクトリを別の ci_local が使っている。"""


class Inner:
    def __init__(self, job: dict) -> None:
        self.job = job
        self.state = Path(os.path.expanduser(job["state_dir"]))
        self.repo = self.state / "repo"
        self.venv_full = self.state / "venv-full"
        self.venv_core = self.state / "venv-core"
        self.venv_lint = self.state / "venv-lint"
        self.out = Path(job["out"])
        self.out.mkdir(parents=True, exist_ok=True)
        self.ncpu = os.cpu_count() or 1
        self.workers = int(job["workers"])
        self.threads = max(1, self.ncpu // max(1, self.workers))
        self.results: dict[str, dict] = {}
        self.setup_notes: list[str] = []
        self.remarks: list[str] = []
        self.tree = dict(job["tree"])
        self.tested: str | None = None
        self.extra_path: list[str] = []
        self.extra_env: dict[str, str] = {}
        self.st: dict = {"job": job, "results": self.results, "tree": self.tree, "setup_notes": self.setup_notes,
                         "remarks": self.remarks, "tools_probed": False, "skip_notices": [],
                         "scrub": [(str(self.state), "<state-dir>"), (str(Path.home()), "~")]}
        self._full_ready = False
        self._py311: str | None = None
        self._lock_fh = None
        self.skip_now: dict | None = None  # 全数の skip(記録を書くかは finish が verdict で決める)
        self._skip_undo: list[tuple[str, object]] = []  # この run が記録にしたこと(要約が作れなければ戻す)

    # ---- 共通 ------------------------------------------------------------------------------
    def run(self, cmd: list[str], *, env: dict | None = None, cwd: Path | None = None, log: str | None = None,
            check: bool = True) -> int:
        shown = " ".join(shlex.quote(c) for c in cmd)
        _log(f"$ {shown[:200]}")
        if log:
            with open(self.out / log, "a", encoding="utf-8") as fh:
                fh.write(f"\n$ {shown}\n")
                fh.flush()
                rc = subprocess.call(cmd, env=env, cwd=cwd, stdout=fh, stderr=subprocess.STDOUT)
        else:
            rc = subprocess.call(cmd, env=env, cwd=cwd)
        if check and rc != 0:
            raise RuntimeError(f"exit {rc}: {shown[:300]}" + (f"(ログ {log})" if log else ""))
        return rc

    def git(self, *args: str, check: bool = True) -> int:
        return self.run(["git", "-C", str(self.repo), *args], log="setup.log", check=check)

    def capture(self, cmd: list[str], *, env: dict | None = None) -> str:
        """出力を読むだけの呼び出し(失敗は空文字)。"""
        return subprocess.run(cmd, capture_output=True, text=True, env=env).stdout.strip()

    def git_out(self, *args: str) -> str:
        return self.capture(["git", "-C", str(self.repo), *args])

    def base_env(self, venv: Path, home: Path) -> dict:
        """CI の runner が与える環境だけ(手元の環境変数は継承しない)。"""
        tmp = home / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        path = [f"{venv}/bin", "/usr/local/bin", "/usr/bin", "/bin", *self.extra_path]
        env = {
            "PATH": ":".join(path),
            "HOME": str(home), "TMPDIR": str(tmp), "LANG": "C.UTF-8", "TZ": "UTC",
            "CI": "true", "GITHUB_ACTIONS": "true",  # ★CI=true は設計判断(docstring)
            "PYTHONUTF8": "1", "QT_QPA_PLATFORM": "offscreen",
            "VIRTUAL_ENV": str(venv),
        }
        env.update(self.extra_env)
        return env

    def setup_env(self, env: dict) -> dict:
        """pip を呼ぶときだけ使う(HOME が毎回空なので、pip のキャッシュを状態ディレクトリに置く)。"""
        return dict(env, PIP_CACHE_DIR=str(self.state / "pip-cache"))

    def fresh_home(self, name: str) -> Path:
        home = self.state / "homes" / name
        shutil.rmtree(home, ignore_errors=True)
        home.mkdir(parents=True)
        return home

    # ---- 状態ディレクトリ: 目印と排他 ------------------------------------------------------
    def claim_state_dir(self) -> None:
        """目印の無い既存のディレクトリでは何も消さない。排他が取れなければ Busy。"""
        self.check_marker()
        self.take_lock()

    def foreign_repo_reason(self) -> str | None:
        """目印の無い置き場の ``repo/`` が、この道具の作った Fullseye の clone でない理由(clone なら None)。

        2 回目のレビューの実行: stamp だけある置き場の ``repo/`` が別の git repo で、引き継いだあとの
        ``checkout -f``・``clean -fdx`` が未追跡ファイルを消した。stamp は venv の出どころしか言わない。
        """
        if not self.repo.exists():
            return None  # 掃除する相手が無い(clone し直すだけ)
        if not (self.repo / ".git").exists():
            return "`repo/` が git の clone でない"
        origin = self.git_out("config", "--get", "remote.origin.url")
        want = str(self.job.get("source") or "")

        def norm(p: str) -> str:
            return os.path.normcase(os.path.realpath(p)).rstrip("/\\") if p else ""

        if not origin or norm(origin) != norm(want):
            return "`repo/` の origin が、検査する repo と違う"
        if not is_fullseye_pyproject(self.git_out("show", "HEAD:pyproject.toml")):
            return "`repo/` の HEAD の pyproject.toml の name が fullseye でない"
        return None

    def check_marker(self) -> None:
        """目印を確かめる(無ければ、空の置き場か、旧版の置き場と確かめられたときだけ置く)。"""
        marker = self.state / MARKER
        if not self.state.exists():
            self.state.mkdir(parents=True)
            marker.write_text("tools/ci_local.py の状態ディレクトリ(消してよい。中身は作り直せる)\n", encoding="utf-8")
        elif not marker.exists():
            if not any(self.state.iterdir()):
                marker.write_text("tools/ci_local.py の状態ディレクトリ(消してよい。中身は作り直せる)\n", encoding="utf-8")
            elif any((self.state / v / ".ci_local_stamp.json").exists() for v in ("venv-full", "venv-core")):
                # 目印を置く前の版(2026-11-10 の最初の版)が作った置き場: venv の stamp はこの道具しか書かない。
                # ただし stamp が言うのは venv のことだけなので、掃除する相手の repo/ は別に確かめる
                foreign = self.foreign_repo_reason()
                if foreign:
                    raise RuntimeError(
                        f"状態ディレクトリに目印 {MARKER} が無く、venv の stamp はあるが {foreign}。この道具の clone と"
                        "確かめられないので、目印を置かず、checkout -f・clean -fdx を走らせずに止めた"
                        "(--state-dir で空か新しい場所を渡す)")
                marker.write_text("tools/ci_local.py の状態ディレクトリ(旧版から引き継いだ)\n", encoding="utf-8")
                self.setup_notes.append("状態ディレクトリ: 目印の無い旧版の置き場を引き継いだ(venv の stamp と、"
                                        "repo/ の origin・pyproject.toml で確認)")
            else:
                raise RuntimeError(
                    f"状態ディレクトリに目印 {MARKER} が無い。既存の別のディレクトリかもしれないので、checkout -f・"
                    "clean -fdx・rmtree を走らせずに止めた(--state-dir で空か新しい場所を渡す)")

    def take_lock(self) -> None:
        """状態ディレクトリの排他(flock)。取れなければ持ち主を書いて Busy。"""
        import fcntl  # Linux の内側だけ
        self._lock_fh = open(self.state / LOCK_FILE, "a+", encoding="utf-8")
        try:
            fcntl.flock(self._lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            try:
                owner = json.loads((self.state / OWNER_FILE).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                owner = {}
            raise Busy("状態ディレクトリを別の ci_local が使っている(持ち主: pid {pid}、開始 {started}、commit {sha}、"
                       "段 {phases})。終わるのを待つか、--state-dir で別の置き場を渡す".format(
                           pid=owner.get("pid", "?"), started=owner.get("started", "?"),
                           sha=str(owner.get("sha", "?"))[:12], phases=",".join(owner.get("selected", [])) or "?"
                       )) from None
        (self.state / OWNER_FILE).write_text(json.dumps({
            "pid": os.getpid(), "started": time.strftime("%Y-%m-%d %H:%M:%S %z"), "sha": self.job["sha"],
            "selected": self.job["selected"]}), encoding="utf-8")

    # ---- 道具の有無 ------------------------------------------------------------------------
    def probe_tools(self) -> None:
        real_home = Path.home()
        search = os.pathsep.join([os.environ.get("PATH", ""), str(real_home / ".cargo/bin")])
        base = {"/usr/local/bin", "/usr/bin", "/bin"}
        missing = []
        for tool, names in RUNNER_TOOLS.items():
            found = next((p for p in (shutil.which(n, path=search) for n in names) if p), None)
            if not found:
                missing.append(tool)
                continue
            d = str(Path(found).parent)
            if d not in base and d not in self.extra_path:
                self.extra_path.append(d)  # 利用者が入れた場所(~/.cargo/bin・nvm)をテストの PATH に足す
        if (real_home / ".cargo/bin/cargo").exists():  # HOME を空にするので、rustup の置き場を教える
            for var, sub in (("CARGO_HOME", ".cargo"), ("RUSTUP_HOME", ".rustup")):
                if (real_home / sub).is_dir():
                    self.extra_env[var] = str(real_home / sub)
        apt_missing = [p for p in APT_PKGS
                       if subprocess.call(["dpkg", "-s", p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)]
        if apt_missing and self.job.get("install_apt"):
            _log(f"apt パッケージが足りない: {apt_missing} → --install-apt なので sudo -n apt-get install を試す")
            subprocess.call(["sudo", "-n", "apt-get", "install", "-y", "-q", *apt_missing],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            apt_missing = [p for p in apt_missing
                           if subprocess.call(["dpkg", "-s", p], stdout=subprocess.DEVNULL,
                                              stderr=subprocess.DEVNULL)]
        self.st.update(tools_missing=missing, apt_missing=apt_missing, tools_probed=True)
        if missing or apt_missing:
            _log(f"手元に無い道具: {missing + apt_missing}(これに依るテストは skip する)")
            if self.job.get("require_tools"):
                raise RuntimeError("必要な道具が無い(--require-tools): " + "、".join(missing + apt_missing)
                                   + "。入れるのは利用者(この道具はシステムに何も入れない。apt だけは --install-apt)")

    # ---- 検査する木 ------------------------------------------------------------------------
    def sync_repo(self) -> None:
        sha, src = self.job["sha"], self.job["source"]
        if not (self.repo / ".git").exists():
            self.run(["git", "clone", "-q", "--no-checkout", src, str(self.repo)], log="setup.log")
        # 改行と権限は Linux の CI と同じに(ここの設定で Windows の autocrlf が入らないようにする)
        self.git("config", "core.autocrlf", "false")
        self.git("config", "core.filemode", "true")
        want = [sha] + ([self.tree["base_sha"]] if self.tree["mode"] == "merge" else [])
        for commit in want:
            if subprocess.call(["git", "-C", str(self.repo), "cat-file", "-e", f"{commit}^{{commit}}"],
                               stderr=subprocess.DEVNULL) != 0:
                self.git("fetch", "-q", src, commit)
        if self.tree["mode"] == "merge":
            base = self.tree["base_sha"]
            # GitHub の PR と同じ向き(base に対象を merge)。作るのは Linux 側の clone の中だけ
            self.git("checkout", "-q", "-f", "--detach", base)
            self.git("clean", "-q", "-f", "-d", "-x")
            rc = self.git("-c", "user.name=ci_local", "-c", "user.email=ci_local@invalid", "-c",
                          "commit.gpgsign=false", "merge", "-q", "--no-ff", "--no-edit", "-m",
                          f"ci_local: Merge {sha} into {base}", sha, check=False)
            if rc != 0:
                conflicted = [ln for ln in self.git_out("diff", "--name-only", "--diff-filter=U").splitlines() if ln]
                self.git("merge", "--abort", check=False)
                shown = "、".join(f"`{c}`" for c in conflicted[:10]) + (" ほか" if len(conflicted) > 10 else "")
                raise RuntimeError(
                    f"{self.tree['base_ref']} `{base[:12]}` との merge が衝突した({len(conflicted)} ファイル: {shown})。"
                    "GitHub の PR も同じ衝突になる。**master を取り込んでから**やり直す(先端だけを見るなら --no-merge)")
            self.tested = self.git_out("rev-parse", "HEAD")
            if self.git_out("rev-parse", "HEAD^1") != base or self.git_out("rev-parse", "HEAD^2") != sha:
                raise RuntimeError("merge commit の親が期待と違う")
        else:
            self.tested = sha
        self.tree["tested"] = self.tested
        self.git("update-ref", "refs/ci-local/tested", self.tested)
        self.clean_tree()

    def clean_tree(self) -> None:
        """前の段の置き土産を消す(CI は段ごとに別の checkout)。editable の egg-info だけ残す。

        2026-11-10 実測: core の段の ``.wheelenv/`` が残ったまま全数を回し、repo を走査する門
        (tests/test_fssystem.py)が site-packages の写しを「読み手」に数えて落ちた。
        追跡ファイルも commit の中身に戻す(regen_all --check が落ちたとき、書き換えた生成物が残る)。
        """
        self.git("checkout", "-q", "-f", "--detach", self.tested)
        self.git("clean", "-q", "-f", "-d", "-x", "-e", "*.egg-info")
        self.verify_tree("準備")

    def verify_tree(self, when: str) -> None:
        got = self.git_out("rev-parse", "HEAD")
        if got != self.tested:
            raise RuntimeError(f"{when} の時点で clone の HEAD が `{got[:12]}`(検査対象は `{str(self.tested)[:12]}`)。"
                               "検査中に木が差し替わった")

    # ---- venv ------------------------------------------------------------------------------
    def find_python311(self) -> str:
        if self._py311:
            return self._py311
        if self.job.get("python"):
            self._py311 = self.job["python"]
            return self._py311
        p = shutil.which("python3.11")
        if not p:
            uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
            if Path(uv).exists():
                r = subprocess.run([uv, "python", "find", "3.11"], capture_output=True, text=True)
                if r.returncode != 0 or not r.stdout.strip():
                    self.run([uv, "python", "install", "3.11"], log="setup.log")
                    r = subprocess.run([uv, "python", "find", "3.11"], capture_output=True, text=True)
                p = r.stdout.strip() if r.returncode == 0 else None
        if not p:
            raise RuntimeError("Python 3.11 が無い(--python で渡すか、uv を入れる)")
        self._py311 = p
        return p

    def check_python(self, venv: Path, which: str) -> str:
        """venv の Python の版を実際に調べる。3.11 でなければ失敗(--allow-other-python のときだけ許す)。"""
        r = subprocess.run([str(venv / "bin/python"), "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
                           capture_output=True, text=True)
        ver = r.stdout.strip() or "?"
        self.st.setdefault("python_versions", {})[which] = ver
        if not ver.startswith("3.11."):
            if not (self.job.get("allow_other_python") and self.job.get("python")):
                raise RuntimeError(f"{which} venv の Python が {ver}(3.11 でない)。CI のこの構成は 3.11。--rebuild で作り直すか、"
                                   "承知の上なら --python と --allow-other-python を両方渡す")
            note = f"**{which} venv の Python は {ver}(3.11 ではない。--allow-other-python)**"
            if note not in self.setup_notes:
                self.setup_notes.append(note)
        return ver

    def make_venv(self, venv: Path) -> None:
        shutil.rmtree(venv, ignore_errors=True)
        self.run([self.find_python311(), "-m", "venv", str(venv)], log="setup.log")

    def spec_hash(self, which: str) -> str:
        h = hashlib.sha256()
        h.update(f"{SPEC_VERSION}|{which}".encode())
        h.update((self.repo / "pyproject.toml").read_bytes())
        return h.hexdigest()[:16]

    def ensure_full_venv(self, env: dict) -> str:
        """full venv を用意する。返り値 = 何をしたか(要約用)。"""
        venv, senv = self.venv_full, self.setup_env(env)
        stamp = venv / ".ci_local_stamp.json"
        want = self.spec_hash("full")
        info = json.loads(stamp.read_text()) if stamp.exists() else {}
        age_h = (time.time() - info.get("refreshed", 0)) / 3600
        py = venv / "bin" / "python"
        pip = [str(py), "-m", "pip", "install", "-q"]
        if not py.exists() or self.job.get("rebuild"):
            self.make_venv(venv)
            action, upgrade = "作った", []
        elif info.get("spec") != want or age_h > float(self.job.get("refresh_hours", 24)):
            action, upgrade = f"揃え直した(前回 {age_h:.0f} 時間前)", ["-U", "--upgrade-strategy", "eager"]
        else:
            # 依存は据え置き。editable の写像だけは毎回作り直す(clean -fdx で egg-info が消えるため)
            self.run([*pip, "--no-deps", "-e", "."], env=senv, cwd=self.repo, log="setup.log")
            # ★再利用のたびに中身を確かめる。2026-11-10 実測: 揃え直しが途中で落ちた venv(cv2 が空)を
            #   stamp だけ見て再利用し、全数の 720 件が「backend が無い」で落ちた。
            if self.run([str(py), "-c", VERIFY_FULL], env=env, log="setup.log", check=False) == 0:
                self.check_python(venv, "full")
                return f"再利用({age_h:.0f} 時間前に揃えた)"
            action, upgrade = "壊れていたので揃え直した", ["-U", "--upgrade-strategy", "eager"]
        self.check_python(venv, "full")
        stamp.unlink(missing_ok=True)  # 途中で落ちたら次回は揃え直す
        self.run([*pip, "--upgrade", *PIP_BOOTSTRAP], env=senv, log="setup.log")
        self.run([*pip, *upgrade, "-e", f".[{FULL_EXTRAS}]", *FULL_EXTRA_PKGS, *LOCAL_ONLY_PKGS], env=senv,
                 cwd=self.repo, log="setup.log")
        self.run([*pip, *upgrade, "--index-url", TORCH_INDEX, *TORCH_PKGS], env=senv, log="setup.log")
        self.run([*pip, *upgrade, *OPTIONAL_PKGS], env=senv, log="setup.log")
        self.run([str(py), "-m", "pip", "uninstall", "-y", "-q", "opencv-python"], env=senv, log="setup.log",
                 check=False)
        # ★--force-reinstall: 揃え直しの道では上の `-e .[opencv]` が opencv-python を入れ直し、その uninstall が
        #   contrib と共有の cv2/ を消す。contrib は「最新なので何もしない」ため cv2 が空になった(2026-11-10 実測)。
        self.run([*pip, "--force-reinstall", "--no-deps", OPENCV_CONTRIB], env=senv, log="setup.log")
        self.run([str(py), "-c", VERIFY_FULL], env=env, log="setup.log")
        stamp.write_text(json.dumps({"spec": want, "refreshed": time.time()}))
        return action

    def versions(self, venv: Path, env: dict) -> str:
        code = ("import importlib.metadata as m\n"
                "out=[]\n"
                "for n in ['numpy','scipy','opencv-contrib-python','scikit-image','torch','pillow','pytest',"
                "'pytest-xdist','threadpoolctl']:\n"
                "    try: out.append(f'{n} {m.version(n)}')\n"
                "    except Exception: pass\n"
                "print(', '.join(out))")
        r = subprocess.run([str(venv / "bin/python"), "-c", code], env=env, capture_output=True, text=True)
        return r.stdout.strip()

    def full_env(self, name: str) -> dict:
        env = self.base_env(self.venv_full, self.fresh_home(name))
        if not self._full_ready:
            self.setup_notes.append("full venv: " + self.ensure_full_venv(env))
            self.st["versions"] = self.versions(self.venv_full, env)
            self._full_ready = True
        return env

    def test_env(self, env: dict, *, throttle: bool = True) -> dict:
        env = dict(env, FULLSEYE_REQUIRE_OPTIONAL="1", FULLSEYE_FIGURES="off")
        if throttle and self.workers > 1:
            for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
                env[k] = str(self.threads)
        return env

    def set_result(self, key: str, ok: bool, detail: str, t0: float) -> None:
        self.results[key] = {"state": "ok" if ok else "failed", "detail": ("ok" if ok else "失敗") + detail,
                             "sec": time.time() - t0}

    # ---- 段 --------------------------------------------------------------------------------
    def phase_lint(self) -> None:
        """ci.yml の lint ジョブ: ruff(毎回その日の最新)と、利用者に入る依存の pip-audit。"""
        t0 = time.time()
        venv = self.venv_lint
        env = self.base_env(venv, self.fresh_home("lint"))
        senv = self.setup_env(env)
        py = str(venv / "bin/python")
        if not Path(py).exists() or self.job.get("rebuild"):
            self.make_venv(venv)
        self.check_python(venv, "lint")
        pkgs = [RUFF_PIN] + ([PIP_AUDIT_PIN] if self.job.get("pip_audit", True) else [])
        fresh = (self.run([py, "-m", "pip", "install", "-q", "--upgrade", *PIP_BOOTSTRAP], env=senv, log="setup.log",
                          check=False) == 0
                 and self.run([py, "-m", "pip", "install", "-q", "-U", *pkgs], env=senv, log="setup.log",
                              check=False) == 0)
        ruff = venv / "bin/ruff"
        if not ruff.exists():
            self.set_result("lint", False, "(ruff を入れられなかった。setup.log)", t0)
            return
        ver = self.capture([str(ruff), "--version"], env=env)
        parts, ok = [], True
        rc = self.run([str(ruff), "check", "."], env=env, cwd=self.repo, log="ruff.log", check=False)
        ok = ok and rc == 0
        parts.append(f"{ver}" + ("" if fresh else "(**最新に上げられなかった**。CI は毎回 `ruff>=0.4` の最新)")
                     + (" ok" if rc == 0 else f" 失敗(exit {rc}、ruff.log)"))
        if self.job.get("pip_audit", True):
            gate = self.repo / "tools" / "pip_audit_gate.py"
            if not gate.exists():
                parts.append("pip-audit: tools/pip_audit_gate.py の無い木なので回していない")
            else:
                rc = self.run([py, "tools/pip_audit_gate.py", *PIP_AUDIT_ARGS], env=senv, cwd=self.repo,
                              log="pip-audit.log", check=False)
                ok = ok and rc == 0
                parts.append("pip-audit " + ("ok" if rc == 0 else f"失敗(exit {rc}、pip-audit.log。ネットワークが要る)"))
        else:
            parts.append("pip-audit **未実行**(--no-pip-audit)")
        self.set_result("lint", ok, " — " + " / ".join(parts), t0)

    def phase_regen(self) -> None:
        env = self.full_env("regen")
        t0 = time.time()
        rc = self.run([str(self.venv_full / "bin/python"), "tools/regen_all.py", "--check"], env=env,
                      cwd=self.repo, log="regen.log", check=False)
        self.set_result("regen", rc == 0, "" if rc == 0 else f"(exit {rc}、regen.log)", t0)

    def gate_files(self) -> tuple[list[str], list[str], str]:
        """門の一覧。返り値 = (実在するもの, 一覧にあって実在しないもの, 出どころ)。"""
        listed = self.repo / GATES_FILE
        if listed.exists():
            names = parse_gate_list(listed.read_text(encoding="utf-8"))
            src = f"`{GATES_FILE}`(検査した木のファイル)"
        else:
            names = list(BUILTIN_GATES)
            src = f"**内蔵の写し** `BUILTIN_GATES`(検査した木に `{GATES_FILE}` が無い)"
        files = [n for n in names if (self.repo / n.split("::", 1)[0]).exists()]
        gone = [n for n in names if n not in files]
        return files, gone, f"{src}、{len(names)} 本"

    def phase_gates(self) -> None:
        env = self.test_env(self.full_env("gates"))
        t0 = time.time()
        files, gone, src = self.gate_files()
        self.st["gates_source"] = src
        self.gate_files_run = files
        junit = self.out / "junit-gates.xml"
        if not files:
            self.set_result("gates", False, "(門が 1 本も実在しない)", t0)
            return
        cmd = [str(self.venv_full / "bin/pytest"), "-q", "-ra", f"--junitxml={junit}"]
        if self.workers > 1:
            cmd += ["-n", str(min(self.workers, len(files))), "--dist", "load"]
        rc = self.run(cmd + files, env=env, cwd=self.repo, log="gates.log", check=False)
        jc = junit_counts(junit)
        self.st["junit_gates"] = jc
        why = [f"exit {rc}、gates.log"] if rc != 0 else []
        bad = junit_verdict(jc)
        if bad:
            why.append(bad)
        if gone:
            why.append(f"一覧にあって実在しない門 {len(gone)} 本: " + "、".join(f"`{g}`" for g in gone[:5]))
        self.set_result("gates", not why, ("(" + ";".join(why) + ")" if why else "") + f" — {jc['tests']:,} 件", t0)

    def phase_core(self) -> None:
        """ci.yml の core-minimal ジョブと同じ順。venv は毎回作り直す(中身を CI の各段と同じにするため)。"""
        t0 = time.time()
        env = self.base_env(self.venv_core, self.fresh_home("core"))
        senv = self.setup_env(env)
        self.make_venv(self.venv_core)
        ver = self.check_python(self.venv_core, "core")
        self.setup_notes.append(f"core venv: 作り直した(毎回。Python {ver}。`pip install -e .` のあと smoke、"
                                "build と pytest はそれぞれ使う直前に入れる = ci.yml と同じ順)")
        py = str(self.venv_core / "bin/python")
        pip = [py, "-m", "pip", "install", "-q"]
        repo = self.repo
        smoke = (
            "import numpy as np, fullseye\n"
            "img = np.zeros((64, 64)); img[16:48, 16:48] = 1.0\n"
            "out = fullseye.run_pipeline(img, ['gaussian', 'sobel_amp', 'otsu'])\n"
            "assert set(np.unique(out)) <= {0.0, 1.0}\n"
            "print('bare-install pipeline smoke ok')\n")
        wenv = dict(env, FULLSEYE_WHEEL_GATE="1", FULLSEYE_WHEEL_PYTHON=".wheelenv/bin/python")
        pytest_bin = str(self.venv_core / "bin/pytest")
        steps = [
            ("pip と証明書", [*pip, "--upgrade", *PIP_BOOTSTRAP], senv),
            ("pip install -e .", [*pip, "-e", "."], senv),
            ("import", [py, "-c", "import fullseye, fsi18n; print('import ok')"], env),
            ("op 数", [py, "-c", "import fullseye; n=len(fullseye.op_names()); print(n, 'ops'); assert n > 500"], env),
            ("3-D op 数", [py, "-c", "import ops3d, pipeline3d, measure3d; assert len(ops3d.list_ops()) > 200"], env),
            ("pipeline smoke", [py, "-c", smoke], env),
            ("wheel: editable の op", [py, "tools/ci_wheel_check.py", "--dump", "ops_editable.json"], env),
            ("wheel: build を入れる", [*pip, BUILD_PIN], senv),
            ("wheel: sdist→wheel", [py, "-m", "build", "-o", "dist_check"], senv),
            ("wheel: venv", [py, "-m", "venv", ".wheelenv"], env),
            ("wheel: 入れる", ["bash", "-c", ".wheelenv/bin/pip install -q numpy scipy dist_check/*.whl"], senv),
            ("wheel: 配布物の op", [".wheelenv/bin/python", "tools/ci_wheel_check.py", "--dump", "ops_wheel.json"], env),
            ("wheel: 比べる", [py, "tools/ci_wheel_check.py", "--compare", "ops_editable.json", "ops_wheel.json"], env),
            ("wheel: 大きさ", [py, "-c", "import glob,os,sys; w=glob.glob('dist_check/*.whl')[0]; s=os.path.getsize(w);"
                                     " print('wheel %.1f MB' % (s/1e6)); sys.exit(1 if s > 70e6 else 0)"], env),
            ("packaging: pytest を入れる", [*pip, "pytest"], senv),
            ("packaging", [pytest_bin, "tests/test_unified_packaging.py", "tests/test_packaging_foundation.py", "-q",
                           f"--junitxml={self.out / 'junit-core-packaging.xml'}"], env),
            ("MCP + fs_apply from the wheel", [pytest_bin, "tests/test_mcp_wheel.py", "tests/test_abi_wheel.py", "-q",
                                               "-ra", f"--junitxml={self.out / 'junit-core-wheel.xml'}"], wenv),
        ]
        failed = None
        for name, cmd, step_env in steps:  # CI のジョブと同じく、落ちた段で止める
            if self.run(cmd, env=step_env, cwd=repo, log="core.log", check=False) != 0:
                failed = name
                break
        why = []
        if failed:
            why.append(f"{failed}(core.log)")
        else:
            for name in ("junit-core-packaging.xml", "junit-core-wheel.xml"):
                bad = junit_verdict(junit_counts(self.out / name))
                if bad:
                    why.append(f"{name}: {bad}")
        self.set_result("core", not why, (": " + ";".join(why)) if why else "", t0)

    def phase_tests(self) -> None:
        env = self.test_env(self.full_env("full"))
        n = self.workers
        junit = self.out / "junit-full.xml"
        extra = list(self.job.get("pytest_args") or [])
        cmd = [str(self.venv_full / "bin/pytest"), "-q", "-ra", f"--junitxml={junit}"]
        if n > 1:
            cmd += ["-n", str(n), "--dist", self.job["dist"]]
        if self.job.get("cov"):
            cmd += ["--cov"]
        cmd += extra
        t0 = time.time()
        rc = self.run(cmd, env=env, cwd=self.repo, log="full-suite.log", check=False)
        jc = junit_counts(junit)
        self.st["junit_full"] = jc
        floor = None
        if not extra:
            floor, basis = suite_floor(count_durations(self.repo / ".test_durations"))
            self.remarks.append(f"全数の件数の床: 実行 {jc.get('executed', 0):,} 件 / 床 {floor:,} 件({basis})。")
        why = [f"exit {rc}"] if rc != 0 else []
        bad = junit_verdict(jc, floor)
        if bad:
            why.append(bad)
        if not extra and not bad:  # 床を割った・壊れた JUnit は比べない(記録を書くかは finish が verdict で決める)
            self.compare_skip_baseline(jc)
        blas_note = self.rerun_blas(jc, env)
        if blas_note:
            why.append(blas_note)
        passed = jc["tests"] - jc["failures"] - jc["errors"] - jc["skipped"] - jc["xfailed"]
        counts = (f" — {passed:,} passed / {jc['failures']:,} failed / {jc['errors']:,} errors / "
                  f"{jc['skipped']:,} skipped / {jc['xfailed']:,} xfailed(計 {jc['tests']:,})")
        if extra:
            counts += "。**追加引数つき(全数ではない)**: `" + " ".join(extra) + "`"
        self.set_result("tests", not why, ("(" + ";".join(why) + ")" if why else "") + counts, t0)

    def skip_baseline_shown(self) -> str:
        """記録ファイルの場所(要約に出す形)。ホームの下なら ``~/...``(要約は手元の絶対パスを消すので)。"""
        given = str(self.job.get("state_dir") or DEFAULT_STATE_DIR)
        if not given.startswith("~"):
            try:
                given = "~/" + Path(given).resolve().relative_to(Path.home().resolve()).as_posix()
            except (ValueError, OSError):
                pass
        return given.rstrip("/\\") + "/" + SKIP_BASELINE_FILE

    def read_skip_baseline(self) -> dict:
        """skip の記録を読む。返り値の ``state`` = ``absent``(無い)/ ``ok``(読めた)/ ``unreadable``(理由つき)。"""
        path = self.state / SKIP_BASELINE_FILE
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            return {"state": "absent", "base": None, "accepted": [], "reason": None}
        except OSError as exc:
            return {"state": "unreadable", "base": None, "accepted": [], "reason": f"開けない({type(exc).__name__})"}
        try:
            return parse_skip_baseline(raw.decode("utf-8"))
        except UnicodeDecodeError:
            return {"state": "unreadable", "base": None, "accepted": [], "reason": "UTF-8 でない"}

    def compare_skip_baseline(self, jc: dict) -> None:
        """全数の skip を基準と比べ、大きく増えていたら要約に出す。記録はここでは書かない(``record_skip_baseline``)。

        記録を読めないときは比べず、要約の先頭で知らせる(段は落とさない。上書きもしない)。
        """
        rec = self.read_skip_baseline()
        where = self.skip_baseline_shown()
        now = {"skipped": jc["skipped"], "tests": jc["tests"], "sha": self.tested or self.job["sha"],
               "when": time.strftime("%Y-%m-%d %H:%M"), "tools_missing": list(self.st.get("tools_missing") or []),
               "apt_missing": list(self.st.get("apt_missing") or []), "skip_reasons": jc.get("skip_reasons") or {}}
        self.skip_now = now
        info = {"state": rec["state"], "reason": rec["reason"], "where": where, "jump": None, "accepted": False}
        self.st["skip_baseline"] = info
        if rec["state"] == "unreadable":
            self.st["skip_notices"].append(
                f"**skip の基準: 記録を読めない**({rec['reason']})。比べていない・上書きしていない。直すか、"
                f"`--accept-skips \"<理由>\"` で置き換える(記録 `{where}`)")
            return
        base = rec["base"]
        if base is None:
            self.remarks.append(f"skip の基準: 記録が無い(この run が全段 ok なら、今回の {jc['skipped']:,} 件を"
                                f"最初の記録にする。記録 `{where}`)。")
            return
        jump = skip_jump(base, now, where)
        before, after, cant = comparable_skips(base, now)
        if jump:
            self.st["skip_jump"] = jump
            info["jump"] = after - before
            return
        subtracted = before != base["skipped"] or after != now["skipped"]
        line = (f"skip の基準比: {before:,} → {after:,} 件("
                + ("有無の違う道具の skip を引いた件数。" if subtracted else "")
                + f"基準 = {base.get('when', '?')} の `{str(base.get('sha', '?'))[:12]}`。これまでの最小。知らせる線は"
                  f"基準 + {skip_jump_allowed(before):,} 件")
        if subtracted:
            line += f"。全体は {base['skipped']:,} → {now['skipped']:,} 件"
        line += ")"
        if base.get("legacy"):
            line += "。基準は最初の版の形の記録(失敗した run の件数のことがある)"
        line += "".join("。" + n for n in cant + baseline_condition_notes(base, now))
        self.remarks.append(line + "。")

    def write_skip_baseline(self, data: dict) -> str | None:
        """記録を書く(一時ファイルに書いてから ``os.replace``。途中で切れた記録を残さない)。返り値 = 書けなかった理由。"""
        path = self.state / SKIP_BASELINE_FILE
        tmp = self.state / f".{SKIP_BASELINE_FILE}.{os.getpid()}.tmp"
        try:
            prior = path.read_bytes() if path.is_file() else None
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, path)
            self._skip_undo.append(("write", prior))
        except OSError as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return type(exc).__name__
        return None

    def record_skip_baseline(self, v: str) -> None:
        """verdict が ``SKIP_RECORD_VERDICTS`` の run だけが記録を書く。基準は下がる向きにしか動かさない
        (``--accept-skips`` で受け入れたときだけ、この run の件数に置き換える)。読めない記録は上書きしない。"""
        now = self.skip_now
        accept = self.job.get("accept_skips")
        if now is None:
            if accept:
                self.st["skip_notices"].append(
                    "**skip の基準を受け入れていない**(--accept-skips): この run は全数の skip を基準と比べていない"
                    "(全数の段が走っていない・床を割った・JUnit が壊れた・追加の pytest 引数がある)。基準はそのまま")
            return
        if v not in SKIP_RECORD_VERDICTS:
            self.remarks.append(f"skip の記録: この run の verdict は `{v}`(全段 ok・GitHub と同じ条件ではない)"
                                "なので、記録を書かない(基準はそのまま)。")
            if accept:
                self.st["skip_notices"].append(
                    f"**skip の基準を受け入れていない**(--accept-skips): この run の verdict は `{v}`。受け入れるのは "
                    "verdict が full_ok か ok_missing_tools の run だけ(失敗・部分実行・違う条件の run の件数は"
                    "基準にしない)。基準はそのまま")
            return
        if accept:
            # 5 回目のレビュー E6: 受け入れるのは、跳ねたときと記録が読めないときだけ(跳ねていない run の
            # 受け入れで基準を上げると、--accept-skips を付けたままの alias で C2 のラチェットが戻る)
            if self.st.get("skip_jump") or (self.st.get("skip_baseline") or {}).get("state") == "unreadable":
                self.accept_skip_baseline(now, accept)
                return
            self.st["skip_notices"].append(
                "**skip の基準を受け入れていない**(--accept-skips): 基準より大きく増えていない(跳ねていない)ので、"
                "受け入れるものが無い。基準は通常の規則(下がる向きにしか動かさない)で扱った")
        if self.st.get("skip_jump"):
            return  # 基準は増える前のまま(次の run でも知らせる。文面は skip_jump の行)
        rec = self.read_skip_baseline()
        if rec["state"] == "unreadable":
            self.remarks.append("skip の記録: 記録を読めないので、記録を書かない(上書きしていない。要約の先頭を見る)。")
            return
        base = rec["base"]
        before, after = comparable_skips(base, now)[:2] if base is not None else (None, now["skipped"])
        if base is None or after < before:
            new_base, how = now, ("最初の記録にした" if base is None else
                                  f"基準を {before:,} → {after:,} 件に下げた(比べた件数)")
        else:
            new_base = {k: val for k, val in base.items() if k != "legacy"}
            if base.get("legacy"):
                new_base["from"] = "最初の版の形の記録から引き継いだ"
            how = f"基準 {before:,} 件は動かさない(下がる向きにしか動かさない。比べた件数)"
        data = {"format": SKIP_BASELINE_FORMAT, "base": new_base,
                "last": {k: now[k] for k in ("skipped", "tests", "sha", "when", "tools_missing", "apt_missing")},
                "accepted": rec["accepted"]}
        failed = self.write_skip_baseline(data)
        if failed:
            self.remarks.append(f"skip の記録を書けなかった({failed})。")
            return
        self.remarks.append(f"skip の記録: 今回 {now['skipped']:,} 件。{how}。")

    def accept_skip_baseline(self, now: dict, reason: str) -> None:
        """``--accept-skips``: この run の件数を新しい基準にし、受け入れた履歴を記録に残す(4 回目のレビュー D2)。

        それまで正当な増加を受け入れる手段は記録の削除だけで、最小の履歴も消え、壊れている最中に消すと壊れた
        件数が基準に入った。読めない記録は、置き換える前に別名で残す。
        """
        where = self.skip_baseline_shown()
        rec = self.read_skip_baseline()
        kept = None
        if rec["state"] == "unreadable":
            kept = f"{SKIP_BASELINE_FILE}.unreadable-{time.strftime('%Y%m%d-%H%M%S')}"
            try:
                os.replace(self.state / SKIP_BASELINE_FILE, self.state / kept)
                self._skip_undo.append(("move", kept))
            except OSError as exc:
                self.st["skip_notices"].append(
                    f"**skip の基準を受け入れられなかった**(--accept-skips): 読めない記録を別名で残せなかった"
                    f"({type(exc).__name__})。基準はそのまま(記録 `{where}`)")
                return
        prev = rec["base"]
        before, after = comparable_skips(prev, now)[:2] if prev is not None else (None, now["skipped"])
        entry = {"from": None if prev is None else prev["skipped"], "to": now["skipped"],
                 "compared": {"before": before, "after": after}, "reason": reason,
                 "sha": now["sha"], "when": now["when"], "replaced_unreadable": kept}
        data = {"format": SKIP_BASELINE_FORMAT, "base": dict(now, accepted=reason),
                "last": {k: now[k] for k in ("skipped", "tests", "sha", "when", "tools_missing", "apt_missing")},
                "accepted": [*rec["accepted"], entry]}
        failed = self.write_skip_baseline(data)
        if failed:
            self.st["skip_notices"].append(
                f"**skip の基準を受け入れられなかった**(--accept-skips): 記録を書けなかった({failed})。"
                f"基準はそのまま(記録 `{where}`)")
            self.remarks.append(f"skip の記録を書けなかった({failed})。")
            return
        (self.st.get("skip_baseline") or {})["accepted"] = True
        was = "記録なし" if prev is None else f"{prev['skipped']:,} 件"
        compared = "" if prev is None or (before, after) == (prev["skipped"], now["skipped"]) else (
            f"。有無の違う道具の skip を引いて比べた件数では {before:,} → {after:,} 件")
        self.st["skip_notices"].append(
            f"**skip の基準を受け入れた**(--accept-skips「{reason}」): skip の基準を {was} → {now['skipped']:,} 件にした"
            f"(記録に前の基準・理由・sha・日時を残した{compared}"
            + (f"。読めなかった記録は `{kept}` として同じ場所に残した" if kept else "")
            + f"。記録 `{where}`)")

    def undo_skip_record(self) -> bool:
        """この run が書き換えた skip の記録を元に戻す(要約の作成が例外になった run。5 回目のレビュー E2)。戻したら True。"""
        path = self.state / SKIP_BASELINE_FILE
        undone = bool(self._skip_undo)
        for kind, value in reversed(self._skip_undo):
            if kind == "write":
                if value is None:
                    path.unlink(missing_ok=True)
                else:
                    tmp = self.state / f".{SKIP_BASELINE_FILE}.{os.getpid()}.undo.tmp"
                    tmp.write_bytes(value)
                    os.replace(tmp, path)
            elif kind == "move":
                os.replace(self.state / value, path)
        self._skip_undo.clear()
        if isinstance(self.st.get("skip_baseline"), dict):
            self.st["skip_baseline"]["accepted"] = False
        return undone

    def rerun_blas(self, jc: dict, env: dict) -> str | None:
        """BLAS を絞ったせいで skip したテストを、絞らずに直列で回し直す。返り値 = 失敗の理由(無ければ None)。

        回し直しの目的は「走らせること」なので、回し直しても走らないテスト(skip のまま・回し直しに現れない)が
        1 件でも残れば失敗にする。
        """
        cases = [(c, nm) for c, nm, reason in jc.get("skipped_cases", []) if re.search(BLAS_SKIP_PATTERN, reason)]
        if not cases:
            return None
        files = set()
        for cls, _ in cases:
            parts = cls.split(".")
            for i in range(len(parts), 0, -1):
                cand = "/".join(parts[:i]) + ".py"
                if (self.repo / cand).exists():
                    files.add(cand)
                    break
        if not files:
            self.st["blas"] = {"first": len(cases), "recovered": 0, "still_skipped": 0, "absent": len(cases),
                               "detail": "テストのファイルを特定できなかった"}
            return f"BLAS を絞ったための skip {len(cases)} 件を回し直せなかった(テストのファイルを特定できない)"
        loose = {k: v for k, v in env.items() if not k.endswith("_NUM_THREADS")}
        junit = self.out / "junit-blas.xml"
        rc = self.run([str(self.venv_full / "bin/pytest"), "-q", "-ra", f"--junitxml={junit}", *sorted(files)],
                      env=loose, cwd=self.repo, log="blas.log", check=False)
        bj = junit_counts(junit)
        res = blas_rerun_outcome(cases, None if bj.get("broken") else junit_case_ids(junit),
                                 {(c, nm) for c, nm, _ in bj.get("skipped_cases", [])})
        self.st["blas"] = dict(res, detail=f"{len(files)} ファイルを絞らずに直列で、計 {bj['tests']} 件・失敗 "
                                           f"{bj['failures'] + bj['errors']} 件。junit-blas.xml")
        if rc != 0 or bj.get("broken"):
            return f"BLAS を絞らない回し直しが失敗(exit {rc}、blas.log)"
        stuck = res["still_skipped"] + res["absent"]
        if stuck:
            return (f"BLAS を絞らずに回し直しても {stuck} 件が走らない(skip のまま {res['still_skipped']} 件・"
                    f"回し直しに現れない {res['absent']} 件。junit-blas.xml)")
        return None

    # ---- 要約 ------------------------------------------------------------------------------
    def gate_time_in_full(self) -> float | None:
        """全数の JUnit のうち、門のファイルのテストに掛かった時間の和(二重に回る分)。"""
        files = getattr(self, "gate_files_run", None)
        junit = self.out / "junit-full.xml"
        if not files or not junit.exists():
            return None
        mods = {f.split("::", 1)[0][:-3].replace("/", ".") for f in files}
        total = 0.0
        try:
            for case in ET.parse(junit).getroot().iter("testcase"):
                cls = case.get("classname", "")
                if cls in mods or cls.rsplit(".", 1)[0] in mods:
                    total += float(case.get("time") or 0)
        except (ET.ParseError, OSError, ValueError):
            return None
        return total

    def finish(self, total: float) -> int:
        st = self.st
        st["total"] = total
        try:
            st["results"] = fill_not_run(self.results, self.job, st.get("stopped_at"), st.get("crash"),
                                         bool(st.get("busy")))
            st["github_only_skips"] = missing_tools_of(st)[2]
            self.record_skip_baseline(verdict(st))
            osname = platform.freedesktop_os_release().get("PRETTY_NAME", "Linux") if hasattr(
                platform, "freedesktop_os_release") else "Linux"
            wsl = " (WSL2)" if "microsoft" in platform.release().lower() else ""
            pyv = st.get("python_versions") or {}
            st["env_line"] = (f"{osname}{wsl}, {self.ncpu} CPU, Python "
                              + (" / ".join(f"{v}({k} venv)" for k, v in pyv.items()) or "(venv を使う段は未実行)")
                              + f", xdist `-n {self.workers} --dist {self.job['dist']}`, BLAS {self.threads} スレッド"
                              + (", --cov" if self.job.get("cov") else ""))
            try:
                st["loadavg"] = " ".join(Path("/proc/loadavg").read_text().split()[:3])
            except OSError:
                pass
            dup = self.gate_time_in_full()
            if dup is not None:
                self.remarks.append("門は全数でも回している(範囲を減らさないため)。全数の中で門のテストに掛かった時間の和 = "
                                    f"{_fmt_dur(dup)}(テストごとの和。壁時計の増分はおよそこれを並列数で割った量)。")
            text = render_summary(st)
            rc = exit_code(st)
        except Exception as exc:  # noqa: BLE001 — 要約が書けなくても、失敗として結果を残す
            text = ("### 手元の CI 相当の検査(Linux)— tools/ci_local.py\n\n"
                    f"- 結論: **失敗 —— 要約を作れなかった**({type(exc).__name__}: {exc})\n")
            rc = EXIT_FAILED
            # 失敗した run は skip の記録を書かない(5 回目のレビュー E2: 記録は要約の前に書くので、書いた分を戻す)
            try:
                if self.undo_skip_record():
                    text += "- skip の記録: この run が書き換えた分は元に戻した(失敗した run は記録を書かない)\n"
            except OSError as undo_exc:
                text += f"- **skip の記録を元に戻せなかった**({type(undo_exc).__name__})。記録を確かめる\n"
        (self.out / "summary.md").write_text(text, encoding="utf-8")
        slim = {k: v for k, v in st.items() if k not in ("scrub", "junit_full", "junit_gates")}
        for name in ("junit_full", "junit_gates"):
            if st.get(name):
                slim[name] = {k: v for k, v in st[name].items() if k != "skipped_cases"}
        slim["exit_code"] = rc
        try:
            slim["verdict"] = verdict(st) if rc != EXIT_FAILED else "failed"
            slim["partial"] = partial_reasons(self.job)
            slim["deviations"] = deviation_reasons(self.job, st.get("python_versions"))
        except Exception as exc:  # noqa: BLE001 — 要約が書けなかった run でも result.json は残す
            slim["verdict"] = "failed"
            _log(f"verdict を作れなかった: {type(exc).__name__}: {exc}")
        try:
            (self.out / "result.json").write_text(json.dumps(slim, ensure_ascii=False, indent=1, default=str),
                                                  encoding="utf-8")
        except (OSError, TypeError, ValueError) as exc:
            _log(f"result.json を書けなかった: {exc}")
        return rc

    def main(self) -> int:
        t0 = time.time()
        st = self.st
        runners = {"lint": self.phase_lint, "regen": self.phase_regen, "gates": self.phase_gates,
                   "core": self.phase_core, "tests": self.phase_tests}
        try:
            self.claim_state_dir()
            self.probe_tools()
            self.sync_repo()
            for key in self.job["selected"]:
                self.clean_tree()
                t_phase = time.time()
                try:
                    runners[key]()
                except Exception as exc:  # noqa: BLE001 — その段の失敗として残す(--keep-going なら次の段へ)
                    _log(f"{PHASE_LABEL[key]}: {type(exc).__name__}: {exc}")
                    self.results[key] = {"state": "failed", "sec": time.time() - t_phase,
                                         "detail": f"失敗(段が途中で止まった: {type(exc).__name__}: {exc})"}
                # 段の終わりにも、検査していた木が対象のままかを確かめる(違えば、その段の結果は信用しない)
                try:
                    self.verify_tree(f"{PHASE_LABEL[key]} の終わり")
                except RuntimeError as exc:
                    self.results[key] = {"state": "failed", "detail": f"失敗({exc})", "sec": time.time() - t_phase}
                if self.results[key]["state"] != "ok" and key != "tests" and not self.job.get("keep_going"):
                    st["stopped_at"] = PHASE_LABEL[key]
                    break
        except Busy as exc:
            st["busy"] = True
            st["crash"] = str(exc)
            _log(str(exc))
        except Exception as exc:  # noqa: BLE001 — 要約に残して非 0 で終わる
            st["crash"] = f"{type(exc).__name__}: {exc}"
            _log(st["crash"])
        return self.finish(time.time() - t0)


class _Parser(argparse.ArgumentParser):
    """引数の誤り(知らない引数・値の無い引数・選べない値)でも、最後の行を ``verdict: usage — …`` にする。

    5 回目のレビュー E5: argparse の ``error`` は usage と誤りを stderr に出して exit 2 で終わり、最後の行が
    ``verdict:`` にならなかった。終了コードは 2 のまま。
    """

    def error(self, message: str):  # type: ignore[override]
        self.print_usage(sys.stderr)
        sys.stderr.write(f"{self.prog}: error: {message}\n")
        sys.stderr.flush()
        print(host_stop_line("usage", "引数か起動場所の誤り。実行していない"), flush=True)
        sys.exit(EXIT_USAGE)


def build_parser() -> argparse.ArgumentParser:
    ap = _Parser(description=__doc__.split("\n\n")[0], allow_abbrev=False,
                 formatter_class=argparse.RawDescriptionHelpFormatter)
    names = [*PHASE_KEYS, *PHASE_ALIASES]
    ap.add_argument("--ref", default="HEAD", help="検査する commit(既定 HEAD。作業木の未 commit 変更は含まない)")
    ap.add_argument("--base", default="origin/master",
                    help="merge の相手(既定 origin/master。`<remote>/<branch>` の形なら先に fetch し直す)")
    ap.add_argument("--no-merge", action="store_true",
                    help="base との merge を作らず、対象の先端だけを検査する(要約は「GitHub の CI とは違う条件」になる)")
    ap.add_argument("--no-fetch", action="store_true",
                    help="fetch しない(手元の追跡 ref のまま。要約は「GitHub の CI とは違う条件」になる)")
    ap.add_argument("--out", help="要約・JUnit・ログの置き場(既定 = 一時ディレクトリ。前回の成果物は消してから始める)")
    ap.add_argument("--state-dir",
                    help=f"Linux 側の状態ディレクトリ(clone と venv。既定 {DEFAULT_STATE_DIR}。環境変数 "
                         "FULLSEYE_CI_LOCAL_DIR も読み、内側へは引数で渡す。排他つき)")
    ap.add_argument("--distro", default=DEFAULT_DISTRO, help="WSL のディストリ(Windows のとき)")
    ap.add_argument("-n", "--workers", type=int, default=None,
                    help="pytest-xdist の並列数(既定 12。環境変数 FULLSEYE_CI_LOCAL_WORKERS も読む。1 で直列)")
    ap.add_argument("--dist", default="worksteal", choices=["load", "loadfile", "loadscope", "worksteal"],
                    help="xdist の配り方(既定 worksteal。load は重いテストが 1 ワーカーに溜まる。2026-11-10 の実測で"
                         "全数の段が load 35m47s → worksteal 17m56s)")
    ap.add_argument("--only", choices=names, help="1 段だけ回す(要約は「部分実行」になる。ruff は lint の別名)")
    ap.add_argument("--skip", action="append", default=[], choices=names,
                    help="この段を飛ばす(何度でも。要約は「部分実行」になる)")
    ap.add_argument("--no-pip-audit", action="store_true",
                    help="lint の段の pip-audit を外す(ネットワークが無いとき。要約は「部分実行」になる)")
    ap.add_argument("--keep-going", action="store_true",
                    help="前の段(lint・regen・門・core)が落ちても最後まで回す(全数の結果が要るとき)")
    ap.add_argument("--cov", action="store_true", help="CI と同じく --cov を付ける(遅くなる)")
    ap.add_argument("--rebuild", action="store_true", help="venv を作り直す")
    ap.add_argument("--refresh-hours", type=float, default=24.0,
                    help="これより古い full venv は依存をその日の最新に揃え直す(CI は毎回最新を入れる)")
    ap.add_argument("--python", help="venv を作る Python(既定 = python3.11 か uv の 3.11)")
    ap.add_argument("--allow-other-python", action="store_true",
                    help="--python で渡した Python が 3.11 でなくても続ける(要約に版を書き、"
                         "「GitHub の CI とは違う条件」になる)")
    ap.add_argument("--require-tools", action="store_true",
                    help="runner にある道具(cargo・node・Chrome・apt の 6 個)が手元に無ければ失敗にする"
                         "(付けなければ、全段 ok でも verdict は full_ok でなく ok_missing_tools)")
    ap.add_argument("--accept-skips", metavar="REASON",
                    help="この run の skip の件数を新しい基準として受け入れる(理由は必須。記録に前の基準・理由・sha・"
                         "日時を残す)。受け入れるのは verdict が full_ok か ok_missing_tools の run だけ。verdict は変えない")
    ap.add_argument("--install-apt", action="store_true",
                    help="足りない apt パッケージを sudo -n apt-get install で入れる(頼まれたときだけ)")
    ap.add_argument("--inside", metavar="JOB", help=argparse.SUPPRESS)
    ap.add_argument("pytest_args", nargs="*", help="pytest に渡す追加の引数(`--` の後ろ。要約は「部分実行」になる)")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.inside:
        job = json.loads(Path(args.inside).read_text(encoding="utf-8"))
        if args.state_dir is None or args.workers is None:
            print("ci_local: 内側は --state-dir と -n を引数で受け取る(外側が必ず渡す)", file=sys.stderr)
            return EXIT_USAGE
        job["state_dir"], job["workers"] = args.state_dir, args.workers
        return Inner(job).main()
    return _host_main(args)


if __name__ == "__main__":
    sys.exit(main())
