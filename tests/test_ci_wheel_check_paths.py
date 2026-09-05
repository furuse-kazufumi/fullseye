# -*- coding: utf-8 -*-
"""wheel 門を **CI と同じ呼び方** で叩く回帰テスト。

2026-09-05 の事故: `tools/ci_wheel_check.py` は checkout の `tools/` を
`sys.path` から外すために起動直後 `chdir` する。`tools/preflight.py` は
集計ファイルを **絶対パス**で渡すので手元では通っていたが、`ci.yml` は
**相対パス**で渡すため、`--dump` の出力が一時ディレクトリへ書き捨てられ、
続く `--compare` が `FileNotFoundError` で落ちた。

つまり **門は本番の呼び出し経路では一度も比較を実行していなかった**。
「門は事故の起きる場所に立てる」の 3 度目。ここで検査するのは wheel の中身
ではなく、**門そのものが呼び出し規約に耐えるか**である。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "tools", "ci_wheel_check.py")

pytestmark = pytest.mark.skipif(
    not os.path.exists(CHECK), reason="tools/ci_wheel_check.py が無い(配布物側)"
)


def _run(args, cwd):
    return subprocess.run([sys.executable, CHECK, *args], cwd=str(cwd),
                          capture_output=True, text=True, timeout=900)


def test_dump_with_a_relative_path_lands_in_the_callers_directory(tmp_path):
    """`--dump ops.json` は **呼び出し元の cwd** に書く。

    スクリプトは内部で chdir するので、素直に書くと一時 dir へ消える。
    それが CI で起きた事故そのものなので、ここで固定する。
    """
    r = _run(["--dump", "ops_editable.json"], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    out = tmp_path / "ops_editable.json"
    assert out.exists(), (
        "相対パスで --dump したのに呼び出し元に出力が無い。"
        "chdir 前の cwd を基準に解決していない。stdout=%s" % r.stdout
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    for key in ("version", "ops", "failed_backends", "root_modules"):
        assert key in payload, "集計 JSON に %s が無い" % key
    assert payload["ops"], "op が 1 つも数えられていない"


def test_compare_accepts_the_relative_paths_ci_actually_passes(tmp_path):
    """`--compare a.json b.json`(相対 2 つ)が CI の呼び方。落ちてはいけない。

    ここでは同じ集計を 2 回渡すので**内容としては必ず一致**する。
    見ているのは判定結果ではなく、**引数の解決が壊れていないこと**。
    """
    assert _run(["--dump", "a.json"], tmp_path).returncode == 0
    assert _run(["--dump", "b.json"], tmp_path).returncode == 0
    r = _run(["--compare", "a.json", "b.json"], tmp_path)
    assert "FileNotFoundError" not in r.stderr, (
        "相対パスの --compare がファイルを見つけられていない: " + r.stderr[-400:]
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_a_missing_dump_is_reported_as_a_verdict_not_a_traceback(tmp_path):
    """集計ファイルが無いときは、traceback ではなく **NG の判定**として出す。

    門が traceback で死ぬと「門が壊れた」のか「検査に落ちた」のか
    ログから区別できない。区別できない門は運用で無視されるようになる。
    """
    r = _run(["--compare", "nope_a.json", "nope_b.json"], tmp_path)
    assert r.returncode == 1
    assert "Traceback" not in r.stderr, "判定ではなく例外で落ちている: " + r.stderr[-300:]
    assert "NG:" in r.stdout, r.stdout + r.stderr
