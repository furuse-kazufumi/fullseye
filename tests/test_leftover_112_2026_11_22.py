# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Fullseye 1.1.2 に回した配布物・定義読み込みの積み残しを固定する門。"""
from __future__ import annotations

import gc
import importlib
import json
import os
import re
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

import engine
import helpstore
import opassist
import safe_xml
from fullseye import abi_bridge
from fullseye.mcp import server


ROOT = Path(__file__).resolve().parents[1]
README_LINK = re.compile(r"\]\(([^)]+)\)")


def _nested_lists(levels: int) -> str:
    return "[" * levels + "0" + "]" * levels


@pytest.mark.parametrize("levels, accepted", [
    (server.MAX_JSON_DEPTH - 1, True),
    (server.MAX_JSON_DEPTH, False),
    (100_000, False),
])
def test_pipeline_definition_json_has_the_shared_depth_limit(tmp_path, levels, accepted):
    """ルート辞書を含め 64 段は通し、65 段と 10 万段は ``ValueError`` で断る。"""
    path = tmp_path / "pipeline.json"
    path.write_text('{"fullseye_pipeline":1,"stages":[],"metadata":' + _nested_lists(levels) + "}",
                    encoding="utf-8")
    if accepted:
        assert engine.FullseyeEngine.load(path).stages == []
    else:
        with pytest.raises(ValueError, match="nesting|depth|deep"):
            engine.FullseyeEngine.load(path)


@pytest.mark.parametrize("levels, accepted", [
    (server.MAX_JSON_DEPTH - 1, True),
    (server.MAX_JSON_DEPTH, False),
    (100_000, False),
])
def test_parameter_json_has_the_shared_depth_limit(levels, accepted):
    """C ABI のパラメータ束も pipeline / MCP と同じ数え方・上限で読む。"""
    text = '{"value":' + _nested_lists(levels) + "}"
    if accepted:
        assert abi_bridge.parse_params(text)["value"] is not None
    else:
        with pytest.raises(Exception, match="nesting|depth|deep|入れ子") as exc:
            abi_bridge.parse_params(text)
        assert not isinstance(exc.value, RecursionError)


def test_general_xml_default_depth_remains_256():
    """定義専用ではない XML 全体の既定値を JSON の上限へ巻き込まない。"""
    assert safe_xml.DEFAULT_MAX_DEPTH == 256


@pytest.mark.parametrize("module_name,data_rel", [
    ("examples.poc_real_file_formats", "data/fileio_real"),
    ("examples.poc_real_tum_rgbd_slam", "data/tum_rgbd_fr1_xyz"),
])
def test_checkout_only_data_examples_stop_with_a_clear_message(tmp_path, monkeypatch, module_name, data_rel):
    """wheel に同梱しない大きな実データの見本は traceback でなく利用条件を伝える。"""
    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, "DATA", tmp_path / "missing")
    with pytest.raises(SystemExit, match=r"needs %s.*source checkout" % re.escape(data_rel)):
        module.main()


def test_wheel_op_find_uses_the_packaged_summary_without_extracting(monkeypatch):
    """docs/ops が無い wheel でも、op_find の説明 1 行のために HTML 全書庫を展開しない。"""
    monkeypatch.setattr(opassist, "_NOTE_LINES", None)
    real_glob = __import__("glob").glob

    def no_checkout_notes(pattern, *args, **kwargs):
        if "docs" + os.sep + "ops" in pattern:
            return []
        return real_glob(pattern, *args, **kwargs)

    monkeypatch.setattr(__import__("glob"), "glob", no_checkout_notes)
    monkeypatch.setattr(opassist, "_help_html_root",
                        lambda _here: (_ for _ in ()).throw(AssertionError("help archive was extracted")))
    assert opassist._note_first_line("gaussian")


def test_help_html_reader_closes_every_file(tmp_path):
    """書庫 fallback の読取りを ResourceWarning=error でも通す。"""
    for i in range(20):
        (tmp_path / ("op%d.en.html" % i)).write_text("<p>help %d</p>" % i, encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("error", ResourceWarning)
        assert len(opassist._help_html_lines(str(tmp_path))) == 20
        gc.collect()


def test_checkout_op_find_closes_every_note(monkeypatch):
    """checkout の Markdown を全走査する初回も、開いたファイルをその場で閉じる。"""
    opened = []
    real_open = opassist.io.open

    def tracked_open(*args, **kwargs):
        fh = real_open(*args, **kwargs)
        opened.append(fh)
        return fh

    monkeypatch.setattr(opassist.io, "open", tracked_open)
    monkeypatch.setattr(opassist, "_NOTE_LINES", None)
    assert opassist._note_first_line("gaussian")
    assert len(opened) > 1_000
    assert all(fh.closed for fh in opened)


def test_help_cache_removes_only_stale_versions_and_touches_current(tmp_path, monkeypatch, capsys):
    """期限切れだけを掃除し、新しい別版と現在版・無関係な名前は残す。"""
    stale_days = 31
    fresh_days = 29
    seconds_per_day = 24 * 60 * 60
    archive = tmp_path / "help.tar.xz"
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.html").write_text("<p>a</p>", encoding="utf-8")
    helpstore.pack_archive(str(source), str(archive))
    monkeypatch.setenv("FULLSEYE_CACHE_DIR", str(tmp_path / "cache"))
    cache = tmp_path / "cache"
    current = Path(helpstore._extract(str(archive)))
    current_marker = current / ".complete"
    before_touch = current_marker.stat().st_mtime
    stale = cache / ("op_help-" + "0" * helpstore.CACHE_DIGEST_HEX_CHARS)
    fresh = cache / ("op_help-" + "1" * helpstore.CACHE_DIGEST_HEX_CHARS)
    unrelated = cache / "op_help-not-a-hash"
    other = cache / "keep-me"
    for path in (stale, fresh, unrelated, other):
        path.mkdir(parents=True)
        (path / ".complete").write_text("", encoding="utf-8")
    now = __import__("time").time()
    os.utime(stale / ".complete", (now - stale_days * seconds_per_day,) * 2)
    os.utime(fresh / ".complete", (now - fresh_days * seconds_per_day,) * 2)
    os.utime(current_marker, (now - stale_days * seconds_per_day,) * 2)

    assert Path(helpstore._extract(str(archive))) == current
    assert not stale.exists()
    assert fresh.is_dir()
    assert current.is_dir() and current_marker.stat().st_mtime > before_touch
    assert unrelated.is_dir() and other.is_dir()
    err = capsys.readouterr().err
    assert stale.name in err and fresh.name not in err and current.name not in err


def _stop_lock_holder(process):
    """試験用ロック保持子プロセスを必ず止める。/ Always stop the test lock-holder process."""
    if process.poll() is not None:
        return
    try:
        process.stdin.write("\n")
        process.stdin.flush()
        process.stdin.close()
        process.wait(timeout=10)
    except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
        process.kill()
        process.wait(timeout=10)


def test_help_cache_keeps_a_stale_version_locked_by_another_process(tmp_path, monkeypatch, capsys):
    """別プロセスが利用中の期限切れ版は残し、終了後の掃除でだけ消す。"""
    stale_days = 31
    seconds_per_day = 24 * 60 * 60
    archive = tmp_path / "help.tar.xz"
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.html").write_text("<p>a</p>", encoding="utf-8")
    helpstore.pack_archive(str(source), str(archive))
    cache = tmp_path / "cache"
    stale = cache / ("op_help-" + "2" * helpstore.CACHE_DIGEST_HEX_CHARS)
    stale.mkdir(parents=True)
    complete = stale / ".complete"
    complete.write_text("", encoding="utf-8")
    (stale / "old.html").write_text("old", encoding="utf-8")
    now = __import__("time").time()
    os.utime(complete, (now - stale_days * seconds_per_day,) * 2)
    inuse = stale / (".inuse-%d-test" % os.getpid())
    holder_code = (
        "import os,sys\n"
        "f=open(sys.argv[1], 'w+b')\n"
        "f.write(b'0'); f.flush(); f.seek(0)\n"
        "if os.name == 'nt':\n"
        " import msvcrt; msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)\n"
        "else:\n"
        " import fcntl; fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
        "print('ready', flush=True)\n"
        "sys.stdin.read(1)\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", holder_code, str(inuse)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        assert process.stdout.readline().strip() == "ready"
        monkeypatch.setenv("FULLSEYE_CACHE_DIR", str(cache))
        helpstore._extract(str(archive))
        assert stale.is_dir() and complete.is_file() and (stale / "old.html").is_file()
        assert stale.name not in capsys.readouterr().err
    finally:
        _stop_lock_holder(process)

    helpstore._extract(str(archive))
    assert not stale.exists()


def test_help_cache_removes_an_unlocked_crashed_process_marker(tmp_path, monkeypatch):
    """落ちたプロセスが残したロックされていない印だけなら期限切れ版を消す。"""
    stale_days = 31
    seconds_per_day = 24 * 60 * 60
    archive = tmp_path / "help.tar.xz"
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.html").write_text("<p>a</p>", encoding="utf-8")
    helpstore.pack_archive(str(source), str(archive))
    cache = tmp_path / "cache"
    stale = cache / ("op_help-" + "3" * helpstore.CACHE_DIGEST_HEX_CHARS)
    stale.mkdir(parents=True)
    complete = stale / ".complete"
    complete.write_text("", encoding="utf-8")
    (stale / ".inuse-dead-process").write_bytes(b"0")
    now = __import__("time").time()
    os.utime(complete, (now - stale_days * seconds_per_day,) * 2)

    monkeypatch.setenv("FULLSEYE_CACHE_DIR", str(cache))
    helpstore._extract(str(archive))
    assert not stale.exists()


def _fake_demo(monkeypatch, *, failing_tool=None, final_refused=True):
    class Stream:
        def close(self):
            pass

    class Process:
        def __init__(self):
            self.stdin = Stream()
            self.stdout = Stream()
            self.requests = []

        def wait(self, timeout):
            assert timeout == 120
            return 0

    process = Process()
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: process)

    def write_message(stream, body, **_kwargs):
        assert stream is process.stdin
        process.requests.append(body)

    def read_message(stream):
        assert stream is process.stdout
        request = process.requests[-1]
        method = request["method"]
        if method == "initialize":
            result = {"serverInfo": {"name": "fake", "version": "0"},
                      "protocolVersion": server.PROTOCOL_VERSION}
        elif method == "tools/list":
            result = {"tools": []}
        else:
            name = request["params"]["name"]
            is_error = name == failing_tool or (name == "fullseye_apply" and final_refused)
            result = {"content": [{"type": "text", "text": name}], "isError": is_error,
                      "structuredContent": {"handle": "fake-handle"}}
        return {"jsonrpc": "2.0", "id": request["id"], "result": result}

    monkeypatch.setattr(server, "write_message", write_message)
    monkeypatch.setattr(server, "read_message", read_message)
    return server.demo()


def test_mcp_demo_returns_nonzero_when_an_intermediate_tool_fails(monkeypatch):
    assert _fake_demo(monkeypatch, failing_tool="fullseye_search_ops") != 0


def test_mcp_demo_returns_zero_only_when_the_expected_last_refusal_occurs(monkeypatch):
    assert _fake_demo(monkeypatch, final_refused=True) == 0
    assert _fake_demo(monkeypatch, final_refused=False) != 0


def test_pypi_readme_has_no_relative_links_and_repo_urls_exist():
    """PyPI の long_description から辿れない相対リンクを作らない。"""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    relative = []
    repo_urls = []
    prefix = "https://github.com/furuse-kazufumi/fullseye/"
    raw_prefix = "https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/"
    for match in README_LINK.finditer(text):
        target = match.group(1).split()[0].strip("<>")
        if not re.match(r"(?i)^(https?://|mailto:|#)", target):
            relative.append(target)
        if target.startswith(raw_prefix):
            repo_urls.append(target[len(raw_prefix):])
        elif target.startswith(prefix + "blob/master/"):
            repo_urls.append(target[len(prefix + "blob/master/"):])
        elif target.startswith(prefix + "tree/master/"):
            repo_urls.append(target[len(prefix + "tree/master/"):])
    assert not relative, relative
    missing = [path for path in repo_urls if not (ROOT / path).exists()]
    assert not missing, missing


def test_mcp_help_exits_without_starting_the_stdio_server():
    run = subprocess.run([sys.executable, "-m", "fullseye.mcp", "--help"], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8", timeout=20,
                         env=dict(os.environ, PYTHONUTF8="1", PYTHONPATH=str(ROOT)))
    assert run.returncode == 0 and "usage:" in run.stdout and "--demo" in run.stdout
