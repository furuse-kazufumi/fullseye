"""``tools/measure_mcp_context.py`` は ``--help`` で何も書かず、``--check`` は書かずに drift を見る。

2026-11-03 の完成度監査(A-10): この道具は引数を読まずに ``docs/mcp_context_benchmark.json`` を
書き直していた(``--help`` を渡しても上書き)。門として使えるよう ``--check`` も無かった。
"""
import importlib.util
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "measure_mcp_context.py")
OUT = os.path.join(ROOT, "docs", "mcp_context_benchmark.json")


def _env():
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    env["FULLSEYE_DEVICE"] = "cpu"
    return env


def _load():
    spec = importlib.util.spec_from_file_location("measure_mcp_context_under_test", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_help_writes_nothing_and_does_not_load_the_server():
    before = (os.stat(OUT).st_mtime_ns, open(OUT, "rb").read())
    code = ("import runpy, sys; sys.argv = [%r, '--help']\n"
            "try:\n    runpy.run_path(%r, run_name='__main__')\n"
            "except SystemExit as e:\n    print('EXIT', e.code)\n"
            "print('SERVER', 'fullseye.mcp.server' in sys.modules)\n") % (TOOL, TOOL)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8",
                       env=_env(), cwd=ROOT, timeout=120)
    assert "usage:" in r.stdout and "--check" in r.stdout, r.stdout + r.stderr
    assert "EXIT 0" in r.stdout and "SERVER False" in r.stdout, r.stdout + r.stderr
    after = (os.stat(OUT).st_mtime_ns, open(OUT, "rb").read())
    assert after == before, "--help が docs/mcp_context_benchmark.json に触れた"


def test_check_reports_drift_without_writing(tmp_path, monkeypatch):
    mod = _load()
    fake = tmp_path / "bench.json"
    fake.write_text('{"stale": true}\n', encoding="utf-8")
    monkeypatch.setattr(mod, "OUT", fake)
    monkeypatch.setattr(mod, "render", lambda: '{"fresh": true}\n')
    assert mod.main(["--check"]) == 1
    assert fake.read_text(encoding="utf-8") == '{"stale": true}\n'
    fake.write_text('{"fresh": true}\n', encoding="utf-8")
    assert mod.main(["--check"]) == 0
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(mod, "OUT", missing)
    assert mod.main(["--check"]) == 1 and not missing.exists()


def test_write_mode_writes_the_rendered_text(tmp_path, monkeypatch):
    mod = _load()
    target = tmp_path / "bench.json"
    monkeypatch.setattr(mod, "OUT", target)
    monkeypatch.setattr(mod, "render", lambda: '{"x": 1}\n')
    assert mod.main([]) == 0
    assert target.read_text(encoding="utf-8") == '{"x": 1}\n'
