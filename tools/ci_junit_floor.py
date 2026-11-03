"""CI の門: pytest の JUnit XML を読み、**実際に走ったテストの件数**が床を下回ったら exit 1。

なぜ要るか(2026-11-03):
nightly の ``order-shuffle`` ジョブは ``continue-on-error: true``(順序依存の失敗で本流を止めない)。
2026-11-02 から ``Install`` 段の ``run: >``(折り畳みスカラー)の中に書いたコメント行が
``pip install ...`` と 1 行に連結され、行全体がシェルのコメントになって何も入らず、
次の段が ``pytest: command not found``(exit 127)で終わっていた。continue-on-error のせいで
誰も気づかなかった。「テストが落ちた」と「テストが 1 件も走っていない」を区別し、
後者だけは赤にするのがこの道具の役目。

使い方::

    python tools/ci_junit_floor.py shuffle-serial.xml shuffle-parallel.xml --min-executed 10000

- 「走った」= ``tests - skipped``(failure / error は走った側に数える。落ちたのは調査の対象で、
  この門の対象ではない)。
- ファイルが無い・読めない・``<testsuite>`` が 1 つも無い、はどれも赤(fail-closed)。
- 標準ライブラリだけで動く(CI では setup-python なしの python3 で呼ぶ)。
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from typing import Dict, List


def count_junit(path: str) -> Dict[str, int]:
    """JUnit XML 1 本の件数を返す。``{"tests", "skipped", "failures", "errors", "executed", "suites"}``。

    Raises:
        FileNotFoundError: ファイルが無い。
        ET.ParseError: XML として読めない。
        ValueError: ``<testsuite>`` が 1 つも無い / 件数の属性が整数でない。
    """
    root = ET.parse(path).getroot()
    if root.tag == "testsuite":
        suites: List[ET.Element] = [root]
    else:
        suites = list(root.iter("testsuite"))
    if not suites:
        raise ValueError("%s: <testsuite> が 1 つも無い" % path)
    out = {"tests": 0, "skipped": 0, "failures": 0, "errors": 0, "suites": len(suites)}
    for s in suites:
        for key in ("tests", "skipped", "failures", "errors"):
            raw = s.get(key, "0")
            try:
                out[key] += int(raw)
            except ValueError as exc:
                raise ValueError("%s: %s=%r が整数でない" % (path, key, raw)) from exc
    out["executed"] = out["tests"] - out["skipped"]
    return out


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("junit", nargs="+", help="pytest --junitxml の出力(複数可、1 本ずつ床を見る)")
    ap.add_argument("--min-executed", type=int, required=True,
                    help="1 本あたり、走ったテスト(tests - skipped)の下限")
    args = ap.parse_args(argv)
    if args.min_executed < 1:
        ap.error("--min-executed は 1 以上(0 だと門が空を通す)")

    bad = 0
    for path in args.junit:
        try:
            c = count_junit(path)
        except (OSError, ET.ParseError, ValueError) as exc:
            print("RED %s: 読めない (%s: %s)" % (path, type(exc).__name__, exc))
            bad += 1
            continue
        verdict = "ok " if c["executed"] >= args.min_executed else "RED"
        print("%s %s: executed=%d (tests=%d skipped=%d failures=%d errors=%d suites=%d) floor=%d" % (
            verdict, path, c["executed"], c["tests"], c["skipped"], c["failures"], c["errors"],
            c["suites"], args.min_executed))
        if c["executed"] < args.min_executed:
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
