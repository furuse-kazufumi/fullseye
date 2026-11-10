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

結果は要約 ``summary.md`` と JUnit・ログを ``--out`` に書く(既定は一時ディレクトリの
``fullseye-ci-local/<時刻>-<commit>``。前回の成果物が残っていれば消してから始める)。
終了コード: 0 = 走った段が全部 ok / 1 = 失敗 / 2 = 引数の誤り(1 段も走らない組み合わせを含む)/
3 = 状態ディレクトリを別の ci_local が使っている。

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
  何も消さずに失敗する。段の終わりごとに clone の HEAD が検査対象のままかを確かめる。
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
     実行件数が ``.test_durations`` の行数の 90 % を下回ったら失敗(``SUITE_FLOOR_RATIO``)。
  前の段が落ちたらそこで止めて要約を書く(``--keep-going`` で最後まで回す)。
  ``--only``・``--skip``・``--no-pip-audit``・追加の pytest 引数のどれかがあれば、要約の題と結論は
  「部分実行(全数ではない)」になり、走らなかった段は表に「未実行」と残る。
* 環境変数は**継承しない**(``env -i`` 相当)。手元の ``FULLSEYE_*_DATA`` や ``~/.cache/fullseye`` の
  実データが見えると CI と違う分岐を通るので、HOME も run ごとの空のディレクトリにする。
  入れるのは GitHub の runner と ci.yml が与えるもの: ``CI=true`` ``GITHUB_ACTIONS=true``
  ``PYTHONUTF8=1`` ``QT_QPA_PLATFORM=offscreen`` ``LANG=C.UTF-8`` ``TZ=UTC`` と、門・全数だけ
  ``FULLSEYE_REQUIRE_OPTIONAL=1`` ``FULLSEYE_FIGURES=off``。PYTHONPATH は無し、pytest は
  ``python -m pytest`` でなく ``pytest`` で起動する(cwd が sys.path に入らない = CI と同じ)。
  ★``CI=true`` は設計判断: GitHub の runner が実際に与える値が ``true`` で、``os.environ.get("CI") == "1"``
  で分岐する PoC が 2 本ある(examples/poc_omni360_inspection.py・poc_plenoptic_camera.py)。``CI=1`` に
  すると手元だけ「CI 用の小さい設定」を通り、GitHub と違う分岐を検査することになる。

## 確かめないもの(要約の末尾にも毎回書く)

* Python 3.12 / 3.14(master で GitHub が回す)、3.13(週次)、3.15 の preview。手元は 3.11 だけ。
* 片ごとの見え方。GitHub は全数を 6 片に分け、片ごとの session で回す。``test_test_durations_is_fresh``
  のように session の構成で答えが変わる門は、全件 1 session の手元と片で結論が違いうる
  (2026-11-09 の PR #294 の赤は片 6 だけの 94.8 %)。
* 直列の順序。CI の片の中は直列、手元は xdist の並列。順序依存は夜間の order-shuffle が見る。
  逆に、並列でだけ時々落ちる手元だけの赤もある。
* runner にある道具(cargo・node・Chrome)が手元に無いと、それに依るテストは skip する。開始時に有無を
  調べて要約の先頭に書き、skip の理由を JUnit から集計して「GitHub でしか確かめられない件数」を出す。
  ``--require-tools`` で、足りないことを失敗に変える。道具がシステムに何かを入れることはしない
  (apt パッケージも ``--install-apt`` で頼まれたときだけ)。
* lint ジョブの 2 つ目の pip-audit(CI の道具そのものの監査。CI でも警告のみ)、coverage の結合
  (``--cov`` で計測だけは付く)、docs-only ジョブ(文書だけの PR で全数の代わりに回る部分集合)。
* 依存の版は venv を揃えた時点のもの。CI は毎回その日の最新を入れるので、``--refresh-hours``(既定 24)
  より古い full venv は ``pip install -U --upgrade-strategy eager`` で揃え直す。
* この道具の中の依存の定義(``FULL_EXTRAS`` など)は ci.yml の手写し。ci.yml に同じ文字列があることは
  tests/test_ci_local_tool_2026_11_10.py が見るが、ci.yml に**足された**行は見つけない。
* fetch したあとに master が進めば、GitHub が作る merge commit は手元で検査したものと違う。
* BLAS のスレッド数は ``CPU 数 / 並列数`` に絞る(付けないと 12 並列 × 24 スレッドで詰まる)。絞ったせいで
  「BLAS が 4 スレッド以上要る」と skip したテストは、全数のあとで絞らずに直列で回し直す。
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
#: 根拠: 2026-11-10 の実測で全数の JUnit は 28,020 件(skip 426)、同じ commit の ``.test_durations`` は
#: 27,6xx 行 = 実行件数は行数のほぼ 1.0 倍。鮮度の門(行数が session の 95 % 以上)が逆向きを縛るので、
#: 比が 0.9 を割るのは「一部しか収集していない・大半が skip した」場合だけ。10 % の余裕は、消したテストの
#: 行が ``.test_durations`` に残っている分と skip の増減のため。
SUITE_FLOOR_RATIO = 0.90
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
    ran = [k for k in PHASE_KEYS if results.get(k, {}).get("state") in ("ok", "failed")]
    failed = [k for k in ran if results[k]["state"] == "failed"]
    not_run = [k for k in PHASE_KEYS if k not in ran]
    lines = ["### 手元の CI 相当の検査(Linux)— tools/ci_local.py"
             + (" — 部分実行(全数ではない)" if partial else ""), ""]
    if st.get("busy"):
        concl = "**実行していない** —— 状態ディレクトリを別の ci_local が使っている"
    elif not ran:
        concl = "**失敗 —— 1 段も走っていない**"
    elif failed or st.get("crash") or st.get("stopped_at"):
        concl = "**失敗**" + (": " + "、".join(PHASE_LABEL[k] for k in failed) if failed else "")
    elif partial or not_run:
        concl = "**部分実行(全数ではない)** —— 走った段(" + "、".join(PHASE_LABEL[k] for k in ran) + ")は ok"
    else:
        concl = f"**全段 ok**({len(ran)} 段)"
    if partial and ran:
        concl += "。絞った引数: " + " / ".join(partial) + "。**この結果を全数の証拠にしない**"
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
            lines.append(f"BLAS のスレッドを絞ったための skip {blas.get('first', 0)} 件は、絞らずに直列で回し直した: "
                         f"{blas.get('recovered', 0)} 件が走った({blas.get('detail', '')})。")
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
        "require_tools": args.require_tools, "install_apt": args.install_apt,
    }
    return job, out, common


def prepare_out(out: Path) -> None:
    """出力先を作り、前回の成果物(この道具が書く名前だけ)を消す。"""
    out.mkdir(parents=True, exist_ok=True)
    for name in OUT_PRODUCTS:
        (out / name).unlink(missing_ok=True)


def _host_main(args: argparse.Namespace) -> int:
    try:
        job, out, common = build_job(args, Path.cwd(), dict(os.environ))
    except UsageError as exc:
        print(f"ci_local: {exc}", file=sys.stderr)
        return EXIT_USAGE
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
                         "remarks": self.remarks, "tools_probed": False,
                         "scrub": [(str(self.state), "<state-dir>"), (str(Path.home()), "~")]}
        self._full_ready = False
        self._py311: str | None = None
        self._lock_fh = None

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

    def git_out(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True).stdout.strip()

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
        marker = self.state / MARKER
        if not self.state.exists():
            self.state.mkdir(parents=True)
            marker.write_text("tools/ci_local.py の状態ディレクトリ(消してよい。中身は作り直せる)\n", encoding="utf-8")
        elif not marker.exists():
            if not any(self.state.iterdir()):
                marker.write_text("tools/ci_local.py の状態ディレクトリ(消してよい。中身は作り直せる)\n", encoding="utf-8")
            elif any((self.state / v / ".ci_local_stamp.json").exists() for v in ("venv-full", "venv-core")):
                # 目印を置く前の版(2026-11-10 の最初の版)が作った置き場: venv の stamp はこの道具しか書かない
                marker.write_text("tools/ci_local.py の状態ディレクトリ(旧版から引き継いだ)\n", encoding="utf-8")
                self.setup_notes.append("状態ディレクトリ: 目印の無い旧版の置き場を引き継いだ(venv の stamp で確認)")
            else:
                raise RuntimeError(
                    f"状態ディレクトリに目印 {MARKER} が無い。既存の別のディレクトリかもしれないので、checkout -f・"
                    "clean -fdx・rmtree を走らせずに止めた(--state-dir で空か新しい場所を渡す)")
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
        ver = subprocess.run([str(ruff), "--version"], capture_output=True, text=True, env=env).stdout.strip()
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
        blas_note = self.rerun_blas(jc, env)
        if blas_note:
            why.append(blas_note)
        passed = jc["tests"] - jc["failures"] - jc["errors"] - jc["skipped"] - jc["xfailed"]
        counts = (f" — {passed:,} passed / {jc['failures']:,} failed / {jc['errors']:,} errors / "
                  f"{jc['skipped']:,} skipped / {jc['xfailed']:,} xfailed(計 {jc['tests']:,})")
        if extra:
            counts += "。**追加引数つき(全数ではない)**: `" + " ".join(extra) + "`"
        self.set_result("tests", not why, ("(" + ";".join(why) + ")" if why else "") + counts, t0)

    def rerun_blas(self, jc: dict, env: dict) -> str | None:
        """BLAS を絞ったせいで skip したテストを、絞らずに直列で回し直す。返り値 = 失敗の理由(無ければ None)。"""
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
            self.st["blas"] = {"first": len(cases), "recovered": 0, "detail": "ファイルを特定できなかった"}
            return None
        loose = {k: v for k, v in env.items() if not k.endswith("_NUM_THREADS")}
        junit = self.out / "junit-blas.xml"
        rc = self.run([str(self.venv_full / "bin/pytest"), "-q", "-ra", f"--junitxml={junit}", *sorted(files)],
                      env=loose, cwd=self.repo, log="blas.log", check=False)
        bj = junit_counts(junit)
        still = {(c, nm) for c, nm, _ in bj.get("skipped_cases", [])}
        recovered = len([c for c in cases if c not in still]) if not bj.get("broken") else 0
        self.st["blas"] = {"first": len(cases), "recovered": recovered,
                           "detail": f"{len(files)} ファイルを絞らずに直列で、計 {bj['tests']} 件・失敗 "
                                     f"{bj['failures'] + bj['errors']} 件。junit-blas.xml"}
        if rc != 0 or bj.get("broken"):
            return f"BLAS を絞らない回し直しが失敗(exit {rc}、blas.log)"
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
        (self.out / "summary.md").write_text(text, encoding="utf-8")
        slim = {k: v for k, v in st.items() if k not in ("scrub", "junit_full", "junit_gates")}
        for name in ("junit_full", "junit_gates"):
            if st.get(name):
                slim[name] = {k: v for k, v in st[name].items() if k != "skipped_cases"}
        slim["exit_code"] = rc
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


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], allow_abbrev=False,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    names = [*PHASE_KEYS, *PHASE_ALIASES]
    ap.add_argument("--ref", default="HEAD", help="検査する commit(既定 HEAD。作業木の未 commit 変更は含まない)")
    ap.add_argument("--base", default="origin/master",
                    help="merge の相手(既定 origin/master。`<remote>/<branch>` の形なら先に fetch し直す)")
    ap.add_argument("--no-merge", action="store_true",
                    help="base との merge を作らず、対象の先端だけを検査する(要約にそう書く)")
    ap.add_argument("--no-fetch", action="store_true", help="fetch しない(手元の追跡 ref のまま。要約にそう書く)")
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
                    help="--python で渡した Python が 3.11 でなくても続ける(要約に版を書く)")
    ap.add_argument("--require-tools", action="store_true",
                    help="runner にある道具(cargo・node・Chrome・apt の 6 個)が手元に無ければ失敗にする")
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
