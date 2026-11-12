# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""外部コマンドを PATH から探すとき、作業フォルダに置かれた同名のファイルを拾わない(2026-11-12)。

Python 3.11 の ``shutil.which`` は Windows で作業フォルダを PATH の先頭に足す。書庫を開くフォルダに
``7z.bat`` が置いてあると、``archive_*`` がそれを実行していた(``%ProgramFiles%\7-Zip`` に 7-Zip が無いとき)。
"""
from __future__ import annotations

import os
import shutil
import sys

import pytest

import backend_safe
import fileio


def _plant(folder, name):
    path = os.path.join(str(folder), name)
    with open(path, "w", encoding="ascii") as f:
        f.write("@echo planted\n" if os.name == "nt" else "#!/bin/sh\necho planted\n")
    if os.name != "nt":
        os.chmod(path, 0o755)
    return path


def test_planted_file_in_the_working_folder_is_not_found(tmp_path, monkeypatch):
    planted = _plant(tmp_path, "fullseye_probe_tool.bat" if os.name == "nt" else "fullseye_probe_tool")
    monkeypatch.chdir(tmp_path)
    assert backend_safe.which_outside_cwd("fullseye_probe_tool") is None
    if os.name == "nt" and sys.version_info[:2] == (3, 11):
        # 対照: 直す前の探し方は拾う(この試験が空を通していないことの確認)
        assert shutil.which("fullseye_probe_tool") is not None
    # 利用者が PATH に絶対パスで入れたフォルダは尊重する
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ.get("PATH", ""))
    found = backend_safe.which_outside_cwd("fullseye_probe_tool")
    assert found is not None and os.path.samefile(found, planted)


def test_relative_and_empty_path_entries_are_skipped_on_windows(tmp_path, monkeypatch):
    if os.name != "nt":
        pytest.skip("Windows の PATH の規則")
    _plant(tmp_path, "fullseye_probe_tool.cmd")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", os.pathsep.join(["", ".", "relative_dir", os.environ.get("PATH", "")]))
    assert backend_safe.which_outside_cwd("fullseye_probe_tool") is None


def test_real_tools_are_still_found_and_bad_names_return_none():
    known = "cmd" if os.name == "nt" else "sh"
    found = backend_safe.which_outside_cwd(known)
    assert found and os.path.isabs(found) and os.path.isfile(found)
    assert os.path.samefile(found, shutil.which(known))
    for bad in ("", "   ", None, 7, "fullseye_no_such_tool_zzz"):
        assert backend_safe.which_outside_cwd(bad) is None


def test_sevenzip_lookup_ignores_a_planted_7z(tmp_path, monkeypatch):
    """7-Zip が既定の場所に無く PATH にも無いとき、作業フォルダの 7z.bat を実行ファイルとして返さない。"""
    _plant(tmp_path, "7z.bat" if os.name == "nt" else "7z")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FULLSEYE_7Z", raising=False)
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "no_program_files"))
    system = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32") if os.name == "nt" else "/usr/bin"
    monkeypatch.setenv("PATH", system)
    exe = fileio._sevenzip_executable()
    assert exe is None or not os.path.samefile(os.path.dirname(exe), str(tmp_path)), exe
    # 環境変数で裸の名前を渡しても同じ
    monkeypatch.setenv("FULLSEYE_7Z", "7z")
    exe = fileio._sevenzip_executable()
    if os.name == "nt":
        # 相対の指定は作業フォルダから解決される(利用者の明示の指定)。ここでは「実行可能な別物を PATH から
        # 拾わない」ことだけを見る: 返るのは指定そのもの(.bat でなく拡張子なしの 7z は存在しない)か None
        assert exe is None or os.path.basename(exe).lower() != "7z.bat", exe


def test_no_bare_shutil_which_left_in_shipped_modules():
    """配布するモジュールに、作業フォルダを暗黙に探す ``shutil.which(`` が残っていない(tools/ と tests/ は対象外)。"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    offenders, scanned = [], 0
    for folder in (root, os.path.join(root, "fullseye")):
        for fn in sorted(os.listdir(folder)):
            if not fn.endswith(".py"):
                continue
            scanned += 1
            with open(os.path.join(folder, fn), encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    code = line.split("#", 1)[0]
                    if "shutil.which(" in code and fn != "backend_safe.py":
                        offenders.append("%s:%d" % (fn, lineno))
    assert scanned >= 300, scanned
    assert not offenders, offenders
