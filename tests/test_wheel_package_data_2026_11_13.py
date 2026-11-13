# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""git で追跡している ``fullseye/`` の実行時データが wheel に入るか(2026-11-13、配布物の検証 S2)。

``fullseye/data/TUNING_CARDS.json`` は v1.1.0 から git で追跡されていたのに pyproject の package-data の列挙に無く、
1.1.0 / 1.1.1 の wheel では MCP の ``fullseye_find_ops`` / ``fullseye_plan`` が毎回 -32603 で落ちた。それまでの門は
**列挙した物だけ**を数えていた(目録・アイコン)ので、列挙から漏れた物には原理的に盲目だった。

ここで見るのは 3 つ:

1. checkout の側: git が追跡する ``fullseye/`` の .py 以外の全部が、package-data の ``"fullseye"`` のどれかに当たる
   (``tools/ci_wheel_check.py`` の ``NOT_SHIPPED`` に理由つきで挙げた物を除く)。wheel を組まずに速く落ちる。
2. checkout の側: package-data に**名前で**挙げた物(glob でない物)は checkout に在る。在りもしない名前は
   黙って空を通す(``data/OP_DEVICE.json`` など 3 つがそうだった)。
3. 門そのもの: ``tools/ci_wheel_check.py --package-data WHEEL`` が、追跡しているファイルの欠けた wheel・
   0 バイトのファイルを持つ wheel を NG(rc 1)にし、全部そろった wheel を OK(rc 0)にする。CI はこれを
   組んだ wheel に対して呼ぶ(``Wheel completeness`` の段)。
"""
from __future__ import annotations

import ast
import fnmatch
import os
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tools" / "ci_wheel_check.py"
#: git が追跡する fullseye/ の .py 以外の床(2026-11-13 の実数は 28)。読み方が壊れて 0 件で緑、を止める。
_FLOOR = 20


def _tracked() -> list:
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--", "fullseye"],
                             capture_output=True, check=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError) as e:
        pytest.skip("git ls-files が使えない(checkout ではない): %s" % e)
    names = [p for p in out.decode("utf-8").split("\0") if p]
    return sorted(p for p in names if not p.endswith((".py", ".pyc")) and "/__pycache__/" not in p)


def _not_shipped() -> dict:
    """``tools/ci_wheel_check.py`` の ``NOT_SHIPPED``(import すると chdir するので AST で読む)。"""
    tree = ast.parse(CHECK.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "NOT_SHIPPED" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("tools/ci_wheel_check.py に NOT_SHIPPED が無い")


def _package_data() -> dict:
    with open(ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["tool"]["setuptools"]["package-data"]


def _matches(rel: str, pattern: str) -> bool:
    """setuptools の package-data の glob と同じく、``*`` は ``/`` を跨がない(区切りごとに比べる)。"""
    a, b = rel.split("/"), pattern.split("/")
    return len(a) == len(b) and all(fnmatch.fnmatchcase(x, y) for x, y in zip(a, b))


def test_every_tracked_runtime_file_under_fullseye_is_declared_in_package_data():
    tracked = _tracked()
    assert len(tracked) >= _FLOOR, tracked
    globs = _package_data()["fullseye"]
    skip = _not_shipped()
    undeclared = [p for p in tracked if p not in skip
                  and not any(_matches(p[len("fullseye/"):], g) for g in globs)]
    assert not undeclared, ("git で追跡している fullseye/ の実行時データが package-data に無い(wheel に入らない): %s"
                            " —— pyproject の [tool.setuptools.package-data] の \"fullseye\" に足すか、"
                            "同梱しない理由を tools/ci_wheel_check.py の NOT_SHIPPED に書く" % undeclared)
    stale = sorted(p for p in skip if p not in tracked)
    assert not stale, "NOT_SHIPPED に挙げたのに git が追跡していない: %s" % stale


def test_tuning_cards_ship_and_the_unshipped_roster_is_not_read_by_the_package():
    """S2 の当事者を名指しで固定する(上の一般則が緩められても、この 2 つは見える)。"""
    globs = _package_data()["fullseye"]
    assert "data/TUNING_CARDS.json" in globs
    assert "fullseye/data/gpu_required.json" in _not_shipped()
    readers = [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "fullseye").rglob("*.py"))
               if "gpu_required" in p.read_text(encoding="utf-8")]
    assert not readers, "同梱しないはずの gpu_required.json を fullseye/ の .py が読んでいる: %s" % readers


def test_explicitly_named_package_data_entries_exist_in_the_checkout():
    entries = [(pkg, e) for pkg, globs in _package_data().items() for e in globs
               if not any(ch in e for ch in "*?[")]
    assert len(entries) >= _FLOOR, entries
    absent = ["%s/%s" % (pkg.replace(".", "/"), e) for pkg, e in entries
              if not (ROOT / pkg.replace(".", "/") / e).is_file()]
    assert not absent, "package-data に名前で挙げたのに checkout に無い(列挙は黙って空を通す): %s" % absent


def _wheel(tmp_path: Path, name: str, files: dict) -> Path:
    (tmp_path / name).mkdir()
    whl = tmp_path / name / "fullseye-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(whl, "w") as zf:
        zf.writestr("fullseye/__init__.py", "")
        for name, data in files.items():
            zf.writestr(name, data)
    return whl


def _gate(whl: Path):
    return subprocess.run([sys.executable, str(CHECK), "--package-data", str(whl)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=300, cwd=str(ROOT),
                          env=dict(os.environ, PYTHONUTF8="1"))


def test_the_wheel_gate_fails_on_a_missing_or_empty_file_and_passes_a_complete_wheel(tmp_path):
    tracked = _tracked()
    assert len(tracked) >= _FLOOR
    want = [p for p in tracked if p not in _not_shipped()]
    full = {p: b"{}" for p in want}
    target = "fullseye/data/TUNING_CARDS.json"
    assert target in full

    ok = _gate(_wheel(tmp_path, "ok", full))
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "OK:" in ok.stdout and "%d 件" % len(tracked) in ok.stdout

    miss = _gate(_wheel(tmp_path, "miss", {k: v for k, v in full.items() if k != target}))
    assert miss.returncode == 1 and target in miss.stdout and "NG:" in miss.stdout, miss.stdout + miss.stderr

    empty = _gate(_wheel(tmp_path, "empty", dict(full, **{target: b""})))
    assert empty.returncode == 1 and "0 バイト" in empty.stdout and target in empty.stdout, empty.stdout

    gone = _gate(tmp_path / "no_such.whl")
    assert gone.returncode == 1 and "NG:" in gone.stdout and "Traceback" not in gone.stderr, gone.stdout + gone.stderr
