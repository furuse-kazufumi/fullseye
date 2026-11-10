#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""CI の失敗の実績を数える: テストのファイルごとに「直近の失敗した run のうち、落ちた run の数」。

``tools/ci_select_tests.py --early-list`` は、先頭のジョブ(``gates``)で先に回すテストを
**この実績の順**に選ぶ。その入力 ``tools/ci_failure_history.json`` を作り直すのがこの道具。

    python tools/ci_failure_history.py --runs 60            # 数え直して JSON を書き直す
    python tools/ci_failure_history.py --runs 60 --check    # 書かずに、いまの JSON との差を出す(差があれば exit 1)

* **GitHub は読むだけ**(``gh run list`` / ``gh run view --log-failed``)。何も書かない。
* **手元で回す道具**(CI からは回さない)。1 回に run の数だけログを取りに行くので、毎回の run を
  GitHub API の調子に依存させない。数え直す目安は月に 1 回か、落ち方の傾向が変わったとき。
  古くても壊れはしない(先に回す順番が古い実績のままになるだけ。片の側は何も減らない)。
* 数えるのは**止める力のあるジョブ**(``full suite`` / ``selected tests``)の ``FAILED tests/...`` /
  ``ERROR tests/...`` の行だけ。落ちても通す ``python 3.15 preview``、``order shuffle`` は数えない。
* ``--log-failed`` は**落ちた step のログ**しか返さない。落ちた片が途中で打ち切られた run
  (timeout・cancel)は、要約の行が無いので 0 件に見える(``runs_with_test_failures`` で分かる)。
* 書くのは件数だけ(ブランチ名・commit・ログの本文は書かない)。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tools" / "ci_failure_history.json"
WORKFLOW = "CI"
#: 数えるジョブ(名前の先頭)。ここに無いジョブの失敗は、PR を止めないか、テストの失敗ではない。
BLOCKING_JOB_PREFIXES = ("full suite", "selected tests")
#: ``regen_all --check`` が食い違いを見つけたときの文言(``tools/regen_all.py``)。
REGEN_DRIFT_MARKS = ("生成物がコミット済みと食い違っていた",)

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_FAILED = re.compile(r"^\S+ (?:FAILED|ERROR) (tests/[^\s:]+\.py)(?:::|\s|$)")


def _gh(args: list[str], repo: str | None) -> bytes:
    cmd = ["gh"] + args + (["-R", repo] if repo else [])
    return subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True).stdout


def list_failed_runs(n: int, repo: str | None) -> list[dict]:
    """直近の失敗した run を新しい順に *n* 本まで。"""
    raw = _gh(["run", "list", "--workflow", WORKFLOW, "--status", "failure", "--limit", str(n),
               "--json", "databaseId,createdAt,headBranch,event"], repo)
    runs = json.loads(raw.decode("utf-8"))
    return sorted(runs, key=lambda r: r["createdAt"], reverse=True)[:n]


def fetch_log(run_id: int, cache: Path, repo: str | None) -> str:
    """run の落ちた step のログ。*cache* にあればそれを読む(同じ run のログは変わらない)。"""
    path = cache / ("%d.log" % run_id)
    if not (path.exists() and path.stat().st_size > 0):
        path.write_bytes(_gh(["run", "view", str(run_id), "--log-failed"], repo))
    return path.read_text(encoding="utf-8", errors="replace")


def parse_log(text: str) -> tuple[set[str], bool]:
    """``gh run view --log-failed`` の出力 -> (落ちたテストのファイル, regen_all --check が食い違ったか)。

    行は ``ジョブ名 <TAB> step 名 <TAB> 時刻 本文``。
    """
    files: set[str] = set()
    drift = False
    for line in text.splitlines():
        parts = line.split("\t", 2)
        if len(parts) < 3:
            continue
        job, _step, body = parts
        body = _ANSI.sub("", body)
        if any(mark in body for mark in REGEN_DRIFT_MARKS):
            drift = True
        if not job.startswith(BLOCKING_JOB_PREFIXES):
            continue
        m = _FAILED.match(body)
        if m:
            files.add(m.group(1))
    return files, drift


def aggregate(runs: list[dict], logs: dict[int, str]) -> dict:
    """run ごとのログから、ファイルごとの件数の表を作る(決定的: 同じ入力なら同じ出力)。"""
    file_runs: dict[str, set[int]] = {}
    file_branches: dict[str, set[str]] = {}
    with_failures = 0
    drift_runs = 0
    for r in runs:
        files, drift = parse_log(logs[r["databaseId"]])
        with_failures += bool(files)
        drift_runs += drift
        for f in files:
            file_runs.setdefault(f, set()).add(r["databaseId"])
            file_branches.setdefault(f, set()).add(r["headBranch"])
    table = {f: {"failed_runs": len(file_runs[f]), "branches": len(file_branches[f])}
             for f in sorted(file_runs, key=lambda f: (-len(file_runs[f]), f))}
    stamps = sorted(r["createdAt"] for r in runs)
    return {
        "schema": 1,
        "source": "gh run list --workflow %s --status failure / gh run view <id> --log-failed "
                  "(tools/ci_failure_history.py)" % WORKFLOW,
        "counted_jobs": list(BLOCKING_JOB_PREFIXES),
        "runs_read": len(runs),
        "runs_with_test_failures": with_failures,
        "runs_with_regen_drift": drift_runs,
        "window": [stamps[0], stamps[-1]] if stamps else [],
        "files": table,
    }


def dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", type=int, default=60, help="数える失敗した run の本数(新しい順)")
    ap.add_argument("--repo", help="owner/name(省略時は gh がこの checkout の remote から決める)")
    ap.add_argument("--cache", type=Path, help="ログを置くディレクトリ(省略時は一時ディレクトリ)")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--check", action="store_true", help="書かずに、いまのファイルと比べる")
    args = ap.parse_args(argv)
    if args.runs < 1:
        ap.error("--runs must be >= 1")
    try:
        runs = list_failed_runs(args.runs, args.repo)
    except (OSError, subprocess.CalledProcessError, ValueError) as e:
        print("gh run list failed: %s" % e, file=sys.stderr)
        return 2
    if not runs:
        print("no failed run found (nothing to count; the file is left as it is)", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        cache = args.cache or Path(tmp)
        cache.mkdir(parents=True, exist_ok=True)
        try:
            with ThreadPoolExecutor(4) as ex:
                texts = list(ex.map(lambda r: fetch_log(r["databaseId"], cache, args.repo), runs))
        except (OSError, subprocess.CalledProcessError) as e:
            print("gh run view --log-failed failed: %s" % e, file=sys.stderr)
            return 2
    data = aggregate(runs, {r["databaseId"]: t for r, t in zip(runs, texts)})
    if not data["files"]:
        print("no failed test found in %d run(s); the file is left as it is" % len(runs), file=sys.stderr)
        return 2
    text = dumps(data)
    print("runs read %d (asked %d), with test failures %d, regen drift %d, window %s .. %s, files %d"
          % (data["runs_read"], args.runs, data["runs_with_test_failures"], data["runs_with_regen_drift"],
             data["window"][0], data["window"][1], len(data["files"])))
    for f, row in list(data["files"].items())[:15]:
        print("  %3d runs / %2d branches  %s" % (row["failed_runs"], row["branches"], f))
    if args.check:
        same = args.out.exists() and args.out.read_text(encoding="utf-8") == text
        print("same as %s" % args.out.name if same else "differs from %s" % args.out.name)
        return 0 if same else 1
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s" % args.out.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
