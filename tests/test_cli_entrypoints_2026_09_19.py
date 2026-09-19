# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""CLI の入口の回帰(GenSpark 第 6 報、2026-09-19): help の CLI 名 / parity の argv 衝突 / samples の既定 /
coverage の同梱データ / 色 backend の名前検査が wheel で fail-open。

配布物では console_script ``fullseye`` が入口で ``imgevolve.py`` は checkout 専用の綴りなのに、help の実行例は
全部 ``py -3.11 imgevolve.py``。``fullseye parity`` はサブコマンド名が ``parity.main()`` の argparse に残って
「unrecognized arguments: parity」。``fullseye coverage`` は wheel に無い ``data/halcon_operators.json`` で
FileNotFoundError。``backends_color._real_ops`` は同じ JSON しか読まず、wheel では空集合 → 名前の門が全部通す。
"""
from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stdout

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import imgevolve  # noqa: E402


def _help_text(monkeypatch, argv0: str) -> str:
    monkeypatch.setattr(sys, "argv", [argv0, "--help"])
    buf = io.StringIO()
    with redirect_stdout(buf), pytest.raises(SystemExit) as ei:
        imgevolve.main()
    assert ei.value.code == 0
    return buf.getvalue()


def test_help_examples_use_the_installed_cli_name_when_run_as_fullseye(monkeypatch):
    text = _help_text(monkeypatch, "fullseye")
    assert "fullseye ops --search edge" in text
    assert "py -3.11 imgevolve.py ops" not in text
    assert "in a checkout" in text                        # 両方の呼び方を epilog で言う


def test_help_examples_keep_the_checkout_form_when_run_from_the_repo(monkeypatch):
    text = _help_text(monkeypatch, "imgevolve.py")
    assert "py -3.11 imgevolve.py ops --search edge" in text


def test_prog_name_follows_argv0(monkeypatch):
    monkeypatch.setattr(sys, "argv", [r"C:\Python\Scripts\fullseye.exe"])
    assert imgevolve._prog() == "fullseye"
    monkeypatch.setattr(sys, "argv", ["imgevolve.py"])
    assert imgevolve._prog() == "py -3.11 imgevolve.py"


def test_parity_subcommand_resets_argv_before_delegating(monkeypatch):
    import parity
    seen = {}

    def fake_main():
        seen["argv"] = list(sys.argv)
        return 0
    monkeypatch.setattr(parity, "main", fake_main)
    monkeypatch.setattr(sys, "argv", ["fullseye", "parity"])
    assert imgevolve.main() == 0
    assert seen["argv"] == ["parity.py"], seen           # "parity" が残っていれば unrecognized arguments


def test_samples_defaults_to_list(monkeypatch):
    import sample_data as sd
    called = {}
    monkeypatch.setattr(imgevolve, "cmd_samples", lambda a: called.setdefault("action", a.action) or 0)
    monkeypatch.setattr(sys, "argv", ["fullseye", "samples"])
    # set_defaults(fn=cmd_samples) は parser 構築時に束縛されるので main() を経由して action を見る
    ap_action = None
    import argparse
    orig = argparse.ArgumentParser.parse_args

    def spy(self, *a, **k):
        nonlocal ap_action
        ns = orig(self, *a, **k)
        if getattr(ns, "cmd", None) == "samples":
            ap_action = ns.action
            ns.fn = lambda a: 0
        return ns
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", spy)
    assert imgevolve.main() == 0
    assert ap_action == "list"
    assert hasattr(sd, "__name__")


def test_coverage_explains_the_missing_reference_data_instead_of_crashing(monkeypatch, tmp_path, capsys):
    import honest_summary
    monkeypatch.setattr(honest_summary, "HERE", str(tmp_path))     # wheel 相当: data/ が無い
    assert honest_summary.main() == 1
    out = capsys.readouterr().out
    assert "not shipped" in out and "HALCON_PARITY.md" in out and "halcon_names_data" in out


def test_registry_does_not_shrink_when_warnings_are_errors():
    """import 時の探針(backends_r3._gate)が pywt の警告を出し、`-W error` では 2 op が黙って消えていた。"""
    import subprocess
    code = "import ops; print(len(ops.REGISTRY))"
    env = dict(os.environ, PYTHONUTF8="1")
    normal = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, env=env)
    strict = subprocess.run([sys.executable, "-W", "error::UserWarning", "-W", "always::ResourceWarning", "-c", code],
                            cwd=ROOT, capture_output=True, text=True, env=env)
    assert normal.returncode == 0 and strict.returncode == 0, (normal.stderr[-500:], strict.stderr[-500:])
    assert normal.stdout.strip() == strict.stdout.strip(), (normal.stdout, strict.stdout)
    assert "Level value" not in strict.stderr and "unclosed file" not in strict.stderr


def test_studio_main_toolbar_has_an_object_name():
    # PySide6 が無い CI でも読める形で: ソースの QToolBar 生成の直後に setObjectName がある
    src = open(os.path.join(ROOT, "studio.py"), encoding="utf-8").read()
    i = src.index("tb = QtWidgets.QToolBar(); tb.setMovable(False)")
    assert 'tb.setObjectName("main_tools")' in src[i:i + 400]


def test_color_backend_name_check_is_fail_closed_without_the_json(monkeypatch, tmp_path):
    import backends_color as C
    from halcon_names_data import HALCON_NAMES
    monkeypatch.setattr(C, "HERE", str(tmp_path))                  # JSON 無し → 出荷名簿へ
    real = C._real_ops()
    assert real and real == set(HALCON_NAMES)
    assert all(d[0] in real for d in C._DEFS)                       # 色 op は全部実在名(門は通す)
