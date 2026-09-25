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


def test_version_flag_prints_the_version_and_exits_zero(monkeypatch, capsys):
    import api
    monkeypatch.setattr(sys, "argv", ["fullseye", "--version"])
    with pytest.raises(SystemExit) as ei:
        imgevolve.main()
    assert ei.value.code == 0
    assert api.__version__ in capsys.readouterr().out


def test_runtime_messages_name_the_installed_cli(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["fullseye", "algo", "run", "no_such_algo_xyz", "--seq", "1,2"])
    with pytest.raises(SystemExit) as ei:
        imgevolve.main()
    assert "fullseye algo list" in str(ei.value) and "imgevolve.py" not in str(ei.value)
    monkeypatch.setattr(sys, "argv", ["fullseye", "has", "nosuchop_xyz"])
    rc = imgevolve.main()
    out = capsys.readouterr().out
    assert rc == 1 and "neither an op name" in out and "op_find" in out


def test_empty_operator_name_is_unknown_not_lowpass():
    import numpy as np
    import api
    import fullseye as fs
    assert api.find_op("") is None and api.find_op("   ") is None and api.find_op(None) is None
    img = np.random.default_rng(2).random((8, 8))
    for bad in ("", " ", "\t"):
        with pytest.raises(KeyError, match="unknown operator"):
            fs.apply(img, bad)
        with pytest.raises(KeyError, match="unknown operator"):
            fs.run_pipeline(img, [bad])


def test_narrow_floats_are_upcast_to_the_float64_contract():
    import numpy as np
    import fullseye as fs
    img = np.random.default_rng(2).random((16, 16))
    fs.clear_fallbacks()
    o16 = fs.apply(img.astype(np.float16), "gaussian", on_error="raise")
    o32 = fs.apply(img.astype(np.float32), "gaussian", on_error="raise")
    o64 = fs.apply(img, "gaussian", on_error="raise")
    assert o16.dtype == o32.dtype == np.float64 and o64.dtype == np.float64
    assert np.allclose(o32, o64, atol=1e-6) and np.allclose(o16, o64, atol=2e-3)   # 昇格は無損失、差は入力の量子化だけ
    assert not fs.fallbacks()                                                      # 記録もしない


def test_on_error_message_names_the_default_none():
    import numpy as np
    import fullseye as fs
    with pytest.raises(ValueError, match="or None"):
        fs.apply(np.zeros((4, 4)), "gaussian", on_error="ignore")


def test_generated_python_declares_utf8_because_comments_carry_japanese_op_docs():
    import engine
    eng = engine.FullseyeEngine.from_ops("gaussian,otsu") if hasattr(engine.FullseyeEngine, "from_ops") \
        else engine.FullseyeEngine.from_dict({"name": "p", "stages": [["gaussian", 0.5, 0.5], ["otsu", 0.5, 0.5]]})
    for src in (eng.to_python(), eng.to_python_staged()):
        assert src.splitlines()[0] == "# -*- coding: utf-8 -*-", src.splitlines()[:2]
        compile(src, "<generated>", "exec")


def test_sample_photo_unknown_name_raises_instead_of_killing_the_process():
    import realdata
    import fullseye as fs
    with pytest.raises(realdata.RealDataError, match="未登録"):
        fs.sample_photo("no_such_photo_xyz")
    assert not issubclass(realdata.RealDataError, SystemExit)
    assert "sample_photo" in fs.__all__


def _ops_out(monkeypatch, capsys, *args) -> str:
    monkeypatch.setattr(sys, "argv", ["fullseye", "ops", *args])
    assert imgevolve.main() == 0
    return capsys.readouterr().out


def _assert_a_zero_is_not_a_silent_zero(out: str) -> None:
    """★「0 件」と「0 件に見えているだけ」を区別すること(門の本体)。

    2026-09-25 まで ``fullseye ops --search msa`` は ``0 ops match`` と言い切っていた ——
    台帳には 4 件在るのに。同じ欠陥は ``has`` では 2026-09-20 に、``api.list_ops`` では
    同日に塞がれており、**この一覧だけが 3 面目として残っていた**。
    """
    assert "0 ops match" in out, out[-200:]
    assert "台帳層にさらに" in out, (
        "当たりが台帳に在るのに、一覧が黙って 0 件と答えている: %s" % out[-200:])


def test_a_search_that_only_hits_the_ledger_says_so(monkeypatch, capsys):
    _assert_a_zero_is_not_a_silent_zero(_ops_out(monkeypatch, capsys, "--search", "msa"))


def test_the_silent_zero_gate_catches_a_listing_that_hides_the_ledger(monkeypatch, capsys):
    """★門を壊して確かめる —— 添え書きを消した出力は落ちること。"""
    out = _ops_out(monkeypatch, capsys, "--search", "msa")
    with pytest.raises(AssertionError):
        _assert_a_zero_is_not_a_silent_zero(out.replace("台帳層にさらに", "(消した)"))


def test_the_ledger_is_reachable_from_the_listing(monkeypatch, capsys):
    out = _ops_out(monkeypatch, capsys, "--search", "msa", "--include-ledger")
    assert "msa_gauge_rr" in out and "4 ops match" in out


def test_the_default_listing_keeps_the_image_vocabulary(monkeypatch, capsys):
    """既定は据え置き —— パイプラインと進化はこの語彙で回る。"""
    import api
    out = _ops_out(monkeypatch, capsys)
    assert "--- %d ops match ---" % len(api.list_ops()) in out


def test_the_listing_and_the_index_agree_when_the_ledger_is_included(monkeypatch, capsys):
    import api
    out = _ops_out(monkeypatch, capsys, "--include-ledger")
    assert "--- %d ops match ---" % len(api.list_ops(include_ledger=True)) in out
