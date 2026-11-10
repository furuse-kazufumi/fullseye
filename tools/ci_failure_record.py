"""master と毎日の全数で落ちたテストを、その run の commit 範囲と一緒に 1 つの JSON に残す。

なぜ要るか(2026-11-10)
----------------------
PR の CI は変更に関係するテストだけを回す(``tools/ci_select_tests.py``)。選ばれなかった
テストの失敗は、master への push か毎日の schedule の全数で初めて出る。そのとき
「どの commit が持ち込んだか」を追えるよう、各片の JUnit から落ちたテストを集め、
この run が見た commit の範囲(push なら ``before..sha``)と並べて残す。

使い方(CI の failure-record ジョブ)::

    python3 tools/ci_failure_record.py junit --sha "$GITHUB_SHA" --before "$BEFORE" \\
        --event push --run-id "$RUN_ID" --test-result failure -o ci_result.json \\
        --summary "$GITHUB_STEP_SUMMARY"

原因の commit を絞るには: 落ちたテストが前の緑の run(``gh run list --workflow CI --branch master``)
の後に初めて出たなら、要約に並ぶ範囲の commit が候補。範囲が広ければ
``git bisect run python -m pytest <落ちたテスト>`` で 1 本に絞る(CONTRIBUTING.md の「CI: which tests run where」)。

標準ライブラリだけで動く(CI では setup-python なしの python3 で呼ぶ)。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

_ZERO = "0" * 40


def failed_tests(junit_dir: Path) -> tuple[list[dict], int, list[str]]:
    """(落ちたテスト, 走った件数, 読めなかったファイル)。

    落ちた = ``<failure>`` か ``<error>`` を持つ testcase。名前は pytest のノード id に近い形
    (``tests/test_x.py::test_y[param]``)に戻す(classname の ``tests.test_x`` を path にする)。
    """
    failed: list[dict] = []
    n = 0
    bad: list[str] = []
    for f in sorted(junit_dir.rglob("*.xml")) if junit_dir.exists() else []:
        try:
            root = ET.parse(f).getroot()
        except (ET.ParseError, OSError) as e:
            bad.append("%s: %s" % (f.name, e))
            continue
        for case in root.iter("testcase"):
            n += 1
            bad_child = case.find("failure")
            if bad_child is None:
                bad_child = case.find("error")
            if bad_child is None:
                continue
            cls = case.get("classname", "")
            parts = cls.split(".")
            # tests.test_x(.Class) -> tests/test_x.py(::Class)
            path_parts, rest = [], []
            for i, p in enumerate(parts):
                path_parts.append(p)
                if p.startswith("test_"):
                    rest = parts[i + 1:]
                    break
            node = "/".join(path_parts) + ".py" + "".join("::" + r for r in rest)
            failed.append({"nodeid": node + "::" + case.get("name", ""),
                           "kind": bad_child.tag,
                           "message": (bad_child.get("message") or "")[:300],
                           "junit": f.name})
    return failed, n, bad


def commit_range(sha: str, before: str | None) -> list[str]:
    """この run が新しく見た commit(push の ``before..sha``)。分からなければ直近 20 本。"""
    if before and before != _ZERO:
        rng = ["%s..%s" % (before, sha)]
    else:
        rng = ["-20", sha]
    try:
        out = subprocess.run(["git", "log", "--first-parent", "--format=%h %ad %s",
                              "--date=format:%Y-%m-%d %H:%M", *rng],
                             check=True, capture_output=True, text=True).stdout
        return [ln for ln in out.splitlines() if ln.strip()]
    except (subprocess.CalledProcessError, OSError) as e:
        return ["(git log failed: %s)" % e]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("junit_dir")
    ap.add_argument("--sha", required=True)
    ap.add_argument("--before", default="")
    ap.add_argument("--event", default="")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--test-result", default="", help="needs.test.result(success / failure)")
    ap.add_argument("-o", "--output", default="ci_result.json")
    ap.add_argument("--summary", help="GITHUB_STEP_SUMMARY のパス")
    args = ap.parse_args(argv)
    failed, n, bad = failed_tests(Path(args.junit_dir))
    rec = {
        "sha": args.sha, "before": args.before or None, "event": args.event,
        "run_id": args.run_id, "test_result": args.test_result,
        "tests_reported": n, "failed": failed, "unreadable_junit": bad,
        "commits": commit_range(args.sha, args.before),
    }
    Path(args.output).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as fh:
            fh.write("## Full-suite result for `%s` (%s): %d tests reported, %d failed\n\n"
                     % (args.sha[:10], args.event, n, len(failed)))
            if failed:
                for x in failed[:50]:
                    fh.write("- `%s` (%s)\n" % (x["nodeid"], x["kind"]))
                fh.write("\n### Commits this run brought in (candidates for the cause)\n\n")
                for c in rec["commits"][:50]:
                    fh.write("- %s\n" % c)
            if args.test_result not in ("", "success") and not failed:
                fh.write("\nThe test job did not succeed but no failing test case was found in the "
                         "JUnit files (a shard may have died before writing it).\n")
            if bad:
                fh.write("\nUnreadable JUnit: %s\n" % ", ".join(bad))
    print("tests=%d failed=%d" % (n, len(failed)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
