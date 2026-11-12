# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Studio のスタートメニュー登録(fullseye.shortcuts)と対話的な初期設定(fullseye setup)の検査(2026-11-12)。

* .lnk / .desktop の作成先は tmp に向ける(実際のスタートメニューは触らない)。
* pip・ショートカット・RAG・Studio 起動はすべて差し替え(テストが本物を呼ばないこと自体も検査する)。
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fullseye import setup_cmd, shortcuts  # noqa: E402

WIN = sys.platform == "win32"


@pytest.fixture(autouse=True)
def _isolated_ledger(tmp_path, monkeypatch):
    """台帳は tmp へ。実際の利用者データ領域(と HKCU の Uninstall キー)は触らない。"""
    monkeypatch.setenv("FULLSEYE_LEDGER", str(tmp_path / "_default_ledger.json"))


# --------------------------------------------------------------------------- アイコン / 梱包
def test_icon_is_shipped_in_package_data_and_matches_assets():
    toml = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"fullseye.ico", "fullseye_256.png"' in toml, "icons must be declared as studio_assets package-data"
    for name in ("fullseye.ico", "fullseye_256.png"):
        assert (ROOT / "studio_assets" / name).read_bytes() == (ROOT / "assets" / name).read_bytes()
    assert shortcuts.icon_source("ico").is_file() and shortcuts.icon_source("png").is_file()


# --------------------------------------------------------------------------- Windows .lnk
@pytest.mark.skipif(not WIN, reason="the .lnk path is Windows-only")
def test_windows_lnk_create_idempotent_remove(tmp_path):
    dirs = {"start_menu": tmp_path / "Programs" / "Fullseye", "desktop": tmp_path / "Desktop",
            "icon_dir": tmp_path / "local" / "Fullseye" / "setup"}
    made = shortcuts.install(desktop=True, dirs=dirs, reg_key=r"Software\FullseyeTest\t1")
    assert [p.name for p in made] == ["Fullseye Studio.lnk"] * 2
    first = shortcuts.read_lnk(made[0])
    assert first["Target"].lower().endswith("pythonw.exe")          # no console window
    assert Path(first["Target"]).parent == Path(sys.executable).parent   # this environment's interpreter
    assert first["Arguments"] == "-m studio"
    assert Path(first["Icon"].split(",")[0]) == dirs["icon_dir"] / "fullseye.ico"
    assert (dirs["icon_dir"] / "fullseye.ico").read_bytes() == (ROOT / "assets" / "fullseye.ico").read_bytes()
    # twice -> same result, no error
    again = shortcuts.install(desktop=True, dirs=dirs, reg_key=r"Software\FullseyeTest\t1")
    assert again == made and shortcuts.read_lnk(again[0]) == first
    # remove: deletes lnks + icon, folders that became empty; second remove is a no-op
    gone = shortcuts.remove(dirs=dirs)
    assert not shortcuts.regkey_exists(r"Software\FullseyeTest\t1")
    assert len(gone) == 3 and not any(p.exists() for p in gone)
    assert not dirs["start_menu"].exists() and not dirs["icon_dir"].exists()
    assert shortcuts.remove(dirs=dirs) == []


@pytest.mark.skipif(not WIN, reason="the .lnk path is Windows-only")
def test_windows_start_menu_only_by_default_and_venv_python_is_used(tmp_path):
    fake = tmp_path / "venv" / "Scripts"
    fake.mkdir(parents=True)
    (fake / "python.exe").write_bytes(b"")
    (fake / "pythonw.exe").write_bytes(b"")
    dirs = {"start_menu": tmp_path / "sm", "desktop": tmp_path / "dt", "icon_dir": tmp_path / "ic"}
    made = shortcuts.install(python=str(fake / "python.exe"), dirs=dirs, reg_key=r"Software\FullseyeTest\t2")
    assert made == [dirs["start_menu"] / "Fullseye Studio.lnk"] and not dirs["desktop"].exists()
    assert Path(shortcuts.read_lnk(made[0])["Target"]) == fake / "pythonw.exe"
    shortcuts.remove(dirs=dirs)
    assert not shortcuts.regkey_exists(r"Software\FullseyeTest\t2")


@pytest.mark.skipif(not WIN, reason="Windows-only")
def test_windows_missing_pythonw_is_a_clear_error(tmp_path):
    (tmp_path / "python.exe").write_bytes(b"")
    with pytest.raises(shortcuts.ShortcutError, match="pythonw.exe not found"):
        shortcuts.install(python=str(tmp_path / "python.exe"),
                          dirs={"start_menu": tmp_path / "a", "desktop": tmp_path / "b", "icon_dir": tmp_path / "c"})


# --------------------------------------------------------------------------- Linux .desktop(どの OS でも書ける)
def test_linux_desktop_entry_idempotent_remove(tmp_path):
    dirs = {"apps": tmp_path / "apps", "icon_dir": tmp_path / "icons", "desktop": tmp_path / "Desktop"}
    made = shortcuts.install(platform="linux", python="/opt/py 3/bin/python", dirs=dirs)
    assert made == [dirs["apps"] / "fullseye-studio.desktop"]
    text = made[0].read_text(encoding="utf-8")
    assert 'Exec="/opt/py 3/bin/python" -m studio' in text and "Terminal=false" in text
    assert "Icon=%s" % (dirs["icon_dir"] / "fullseye-studio.png") in text
    assert (dirs["icon_dir"] / "fullseye-studio.png").is_file()
    assert shortcuts.install(platform="linux", python="/opt/py 3/bin/python", dirs=dirs) == made
    gone = shortcuts.remove(platform="linux", dirs=dirs)
    assert len(gone) == 2 and shortcuts.remove(platform="linux", dirs=dirs) == []


def test_unsupported_platform_is_not_an_error(monkeypatch):
    assert shortcuts.install(platform="darwin") == []
    monkeypatch.setattr(sys, "platform", "darwin")
    buf = io.StringIO()
    assert shortcuts.run_cli(True, out=buf) == 0
    assert "Windows and Linux" in buf.getvalue()


def test_studio_cli_flag_validation():
    pytest.importorskip("PySide6")
    import studio
    assert studio.main(["--desktop"]) == 2                                    # --desktop alone
    assert studio.main(["--install-shortcuts", "--remove-shortcuts"]) == 2    # contradictory
    assert studio.main(["--nonsense"]) == 2


# --------------------------------------------------------------------------- fullseye setup
def _info(gui=False, skill=False):
    probes = {e: {"installed": True, "version": "1.0"} for e, *_ in setup_cmd.PROBES}
    probes["gui"]["installed"] = gui
    return {"python": "3.11.0", "executable": sys.executable, "venv": False, "fullseye": "1.1.1", "probes": probes,
            "qt": "ok" if gui else "no_dep", "skill": skill, "mcp": False, "shortcut": False}


class Fakes:
    """pip / shortcuts / rag / launch を差し替える。本物が呼ばれたら落ちる(呼び出しを数える)。"""

    def __init__(self, pip_rc=0):
        self.pip, self.sc, self.rag, self.launch = [], [], [], []
        self.pip_rc = pip_rc

    def kw(self, answers=None, tty=True):
        it = iter(answers or [])

        def input_fn(prompt):
            try:
                return next(it)
            except StopIteration:
                raise EOFError
        return dict(input_fn=input_fn, run_fn=lambda c: (self.pip.append(c), self.pip_rc)[1],
                    shortcuts_fn=lambda d: (self.sc.append(d), ["X.lnk"])[1],
                    rag_fn=lambda: (self.rag.append(1), "SKILL")[1],
                    launch_fn=lambda: self.launch.append(1), is_tty=tty, out=io.StringIO(), info=_info())


def _run(argv, f, **kw):
    k = f.kw(**kw)
    rc = setup_cmd.main(argv, **k)
    return rc, k["out"].getvalue()


def test_dry_run_changes_nothing():
    f = Fakes()
    rc, out = _run(["--dry-run", "--lang", "en"], f)
    assert rc == 0 and "nothing was changed" in out
    assert not (f.pip or f.sc or f.rag or f.launch)


def test_dry_run_with_all_uses_via_interactive_answers_still_changes_nothing():
    f = Fakes()
    rc, out = _run(["--dry-run", "--lang", "en"], f, answers=["1,2,3"])     # dry-run never reads answers
    assert rc == 0 and not (f.pip or f.sc or f.rag or f.launch)


def test_non_terminal_stops_at_guidance_and_exits_zero():
    f = Fakes()
    k = f.kw(tty=False)
    k["input_fn"] = lambda p: pytest.fail("must not ask a question when stdin is not a terminal")
    rc = setup_cmd.main(["--lang", "en"], **k)
    out = k["out"].getvalue()
    assert rc == 0 and "fullseye setup" in out and "fullseye-studio --install-shortcuts" in out
    assert not (f.pip or f.sc or f.rag or f.launch)


def test_yes_runs_defaults_unattended_without_opening_a_window():
    f = Fakes()
    rc, out = _run(["--yes", "--lang", "en"], f, tty=False)
    assert rc == 0
    assert len(f.pip) == 1 and any(a.startswith("PySide6") for a in f.pip[0])   # missing gui -> pip (faked)
    assert f.pip[0][1:4] == ["-m", "pip", "install"]
    assert f.sc == [False] and not f.rag and not f.launch                      # default use = Studio only
    assert "never opens a window" in out and "[What was done]" in out


def test_interactive_answers_drive_every_step():
    f = Fakes()
    # uses=1,3 / start-menu y / desktop y / install deps y / rag y / open studio y
    rc, out = _run(["--lang", "en"], f, answers=["1,3", "y", "y", "y", "y", "y"])
    assert rc == 0
    assert len(f.pip) == 1 and f.sc == [True] and f.rag == [1] and f.launch == [1]
    assert "claude mcp add fullseye" in out and '"mcpServers"' in out
    assert "Command to run:" in out and out.index("Command to run:") < out.index("[What was done]")


def test_interactive_refusals_do_nothing_and_enter_takes_defaults():
    f = Fakes()
    rc, out = _run(["--lang", "en"], f, answers=["", "n", "n", "n"])     # use=default(1) / menu n / deps n / open n
    assert rc == 0 and not (f.pip or f.sc or f.rag or f.launch)
    assert "(no changes)" in out


def test_pip_failure_is_reported_and_setup_continues():
    f = Fakes(pip_rc=1)
    rc, out = _run(["--yes", "--lang", "en"], f, tty=False)
    assert rc == 0 and "dependency install failed (exit code 1)" in out and f.sc == [False]


def test_bad_answer_is_asked_again():
    f = Fakes()
    rc, out = _run(["--lang", "en"], f, answers=["x", "1", "n", "n", "n"])
    assert rc == 0 and out.count("Please try again") == 1


def test_requirements_come_from_pyproject_extras_not_the_package_itself():
    reqs = setup_cmd.requirements_for(["gui", "opencv"])
    assert any(r.lower().startswith("pyside6") for r in reqs) and any(r.lower().startswith("opencv") for r in reqs)
    assert not any(r.lower().startswith("fullseye") for r in reqs)
    assert setup_cmd.pip_command(["x"])[:4] == [sys.executable, "-m", "pip", "install"]


def test_detect_lang_override_and_env():
    assert setup_cmd.detect_lang(env={}, override="ja") == "ja"
    assert setup_cmd.detect_lang(env={"FULLSEYE_LANG": "en"}) == "en"
    assert setup_cmd.detect_lang(env={"LANG": "ja_JP.UTF-8"}) == "ja"
    assert setup_cmd.detect_lang(env={"LANG": "C"}) == "en"


# --------------------------------------------------------------------------- CLI 入口
def _cli(*args, env_extra=None, stdin=subprocess.DEVNULL):
    env = dict(os.environ, PYTHONUTF8="1", FULLSEYE_LANG="en")
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(ROOT / "imgevolve.py"), *args], capture_output=True, text=True,
                          encoding="utf-8", env=env, stdin=stdin, timeout=120)


def test_cli_no_args_prints_guidance_with_setup_first_and_exits_zero():
    r = _cli()
    assert r.returncode == 0
    assert r.stdout.lstrip().startswith("Welcome to Fullseye. First time?  run:  fullseye setup")
    assert "fullseye-studio --install-shortcuts" in r.stdout and "fullseye.apply(img" in r.stdout
    assert "fullseye-rag" in r.stdout and "fullseye.mcp" in r.stdout
    assert _cli(env_extra={"FULLSEYE_LANG": "ja"}).stdout.startswith("Fullseye へようこそ")


def test_cli_existing_behaviour_is_kept():
    r = _cli("--help")
    assert r.returncode == 0 and "setup" in r.stdout and "ops" in r.stdout
    assert _cli("--version").stdout.startswith("fullseye ")
    assert _cli("ops", "--search", "sobel").returncode == 0
    assert _cli("nonsense-cmd").returncode == 2


def test_cli_setup_with_devnull_stdin_does_not_hang_or_change_anything():
    r = _cli("setup", stdin=subprocess.DEVNULL)
    assert r.returncode == 0 and "fullseye setup" in r.stdout
    assert "not a terminal" in r.stdout


# --------------------------------------------------------------------------- 台帳 / アンインストール
from fullseye import uninstall  # noqa: E402


def _win_dirs(tmp_path):
    return {"start_menu": tmp_path / "Programs" / "Fullseye", "desktop": tmp_path / "Desktop",
            "icon_dir": tmp_path / "local" / "Fullseye" / "setup"}


def _linux_dirs(tmp_path):
    return {"apps": tmp_path / "apps", "icon_dir": tmp_path / "icons", "desktop": tmp_path / "Desktop"}


def _register(tmp_path, ledger, regkey):
    """この OS で登録して dirs を返す(Windows は .lnk + HKCU の試験用キー、Linux は .desktop)。"""
    if WIN:
        dirs = _win_dirs(tmp_path)
        shortcuts.install(desktop=True, dirs=dirs, ledger=ledger, reg_key=regkey)
    else:
        dirs = _linux_dirs(tmp_path)
        shortcuts.install(platform="linux", python=sys.executable, dirs=dirs, ledger=ledger)
    return dirs


def _plat():
    return "win" if WIN else "linux"


def _un(tmp_path, ledger, dirs, argv, answers=(), tty=True, pip=None):
    it = iter(answers)

    def input_fn(prompt):
        try:
            return next(it)
        except StopIteration:
            raise EOFError
    calls = pip if pip is not None else []
    buf = io.StringIO()
    env = {"FULLSEYE_CACHE_DIR": str(tmp_path / "cache"), "FULLSEYE_STUDIO_SETTINGS": str(tmp_path / "studio.ini"),
           "LOCALAPPDATA": str(tmp_path / "nolocal")}
    rc = uninstall.main(["--uninstall", "--lang", "en", *argv], input_fn=input_fn,
                        pip_fn=lambda: (calls.append(1), "LOGPATH")[1], is_tty=tty, out=buf, ledger=ledger, dirs=dirs,
                        env=env, registry=False)            # 実レジストリ(本物の Studio 設定)は見ない・消さない
    return rc, buf.getvalue(), calls


def test_ledger_records_what_install_created_and_is_idempotent(tmp_path):
    ledger = tmp_path / "ledger.json"
    dirs = _register(tmp_path, ledger, r"Software\FullseyeTest\a")
    _register(tmp_path, ledger, r"Software\FullseyeTest\a")                 # twice: no duplicates
    ents = shortcuts.ledger_load(ledger)
    keys = [(e["kind"], e["path"]) for e in ents]
    assert len(keys) == len(set(keys))
    assert any(k == "file" for k, _ in keys) and any(k == "dir_if_empty" for k, _ in keys)
    if WIN:
        assert ("regkey", r"Software\FullseyeTest\a") in keys
        assert shortcuts.regkey_exists(r"Software\FullseyeTest\a")
    shortcuts.remove(platform=_plat(), dirs=dirs, ledger=ledger)
    assert not ledger.exists()                                              # 全部消えたら台帳も畳む
    if WIN:
        assert not shortcuts.regkey_exists(r"Software\FullseyeTest\a")


def test_uninstall_removes_only_ledger_items_and_leaves_foreign_files(tmp_path):
    ledger = tmp_path / "ledger.json"
    dirs = _register(tmp_path, ledger, r"Software\FullseyeTest\b")
    folder = dirs["start_menu"] if WIN else dirs["apps"]
    foreign = folder / "my_own_note.txt"                                    # ユーザーが後から置いた物
    foreign.write_text("keep me", encoding="utf-8")
    rc, out, pip = _un(tmp_path, ledger, dirs, ["--yes"])
    assert rc == 0 and pip == [1]                                           # pip は別プロセスの関数に委ねた(1 回)
    assert foreign.read_text(encoding="utf-8") == "keep me"                 # 台帳外は無傷
    assert folder.is_dir()                                                  # 空でないので畳まない
    made = [e["path"] for e in (shortcuts.ledger_load(ledger) or [])]
    assert not any(Path(p).is_file() for p in made)
    if WIN:
        assert not shortcuts.regkey_exists(r"Software\FullseyeTest\b")
    # 2 回目: 落ちない
    rc2, out2, _ = _un(tmp_path, ledger, dirs, ["--yes"])
    assert rc2 == 0


def test_uninstall_dry_run_deletes_nothing(tmp_path):
    ledger = tmp_path / "ledger.json"
    dirs = _register(tmp_path, ledger, r"Software\FullseyeTest\c")
    before = ledger.read_text(encoding="utf-8")
    files = sorted(p for p in tmp_path.rglob("*") if p.is_file())
    rc, out, pip = _un(tmp_path, ledger, dirs, ["--dry-run"], tty=False)
    assert rc == 0 and "nothing was deleted" in out and pip == []
    assert sorted(p for p in tmp_path.rglob("*") if p.is_file()) == files
    assert ledger.read_text(encoding="utf-8") == before
    if WIN:
        assert shortcuts.regkey_exists(r"Software\FullseyeTest\c")
        shortcuts.remove(platform="win", dirs=dirs, ledger=ledger)           # 試験用キーの後始末


def test_uninstall_non_terminal_without_flags_deletes_nothing(tmp_path):
    ledger = tmp_path / "ledger.json"
    dirs = _register(tmp_path, ledger, r"Software\FullseyeTest\d")
    files = sorted(p for p in tmp_path.rglob("*") if p.is_file())
    rc, out, pip = _un(tmp_path, ledger, dirs, [], tty=False)
    assert rc == 0 and "not a terminal" in out and pip == []
    assert sorted(p for p in tmp_path.rglob("*") if p.is_file()) == files
    if WIN:
        shortcuts.remove(platform="win", dirs=dirs, ledger=ledger)


def test_uninstall_settings_and_cache_are_kept_unless_confirmed(tmp_path):
    ledger = tmp_path / "ledger.json"
    dirs = _register(tmp_path, ledger, r"Software\FullseyeTest\e")
    ini = tmp_path / "studio.ini"
    ini.write_text("[x]\na=1\n", encoding="utf-8")
    cache = tmp_path / "cache"
    (cache / "op_help-abc").mkdir(parents=True)
    (cache / "op_help-abc" / "f.html").write_text("x", encoding="utf-8")
    (cache / "backend_probe.json").write_text("{}", encoding="utf-8")
    (cache / "samples").mkdir()                                              # 利用者が取った試料は対象外
    (cache / "samples" / "mine.bin").write_bytes(b"1")
    # Enter x all: remove made(Y) / settings(N) / cache(N) / pip(Y)
    rc, out, pip = _un(tmp_path, ledger, dirs, [], answers=["", "", "", ""])
    assert rc == 0 and ini.exists() and (cache / "op_help-abc").exists() and "[Kept]" in out
    # now confirm both
    ledger2 = tmp_path / "ledger2.json"
    rc, out, pip = _un(tmp_path, ledger2, dirs, [], answers=["y", "y", "n"])
    assert not ini.exists() and not (cache / "op_help-abc").exists() and not (cache / "backend_probe.json").exists()
    assert (cache / "samples" / "mine.bin").exists() and pip == []         # 台帳外・パターン外は残る / pip は n


def test_uninstall_without_ledger_detects_known_shortcut_places_only(tmp_path):
    dirs = _win_dirs(tmp_path) if WIN else _linux_dirs(tmp_path)
    known = (dirs["start_menu"] / "Fullseye Studio.lnk") if WIN else (dirs["apps"] / "fullseye-studio.desktop")
    known.parent.mkdir(parents=True)
    known.write_bytes(b"old")
    stray = known.parent / "other.lnk"
    stray.write_bytes(b"not ours")
    rc, out, pip = _un(tmp_path, tmp_path / "no_such_ledger.json", dirs, ["--yes"])
    assert rc == 0 and not known.exists() and stray.exists()
    assert "No ledger found" in out


def test_uninstall_skill_is_removed_only_via_ledger(tmp_path):
    from fullseye import rag_setup
    target = tmp_path / "skills"
    dest = rag_setup.install(target, repo=None, _auto_repo=False)
    other = target / "someone-elses-skill"
    other.mkdir()
    ledger = tmp_path / "ledger.json"
    shortcuts.ledger_record("claude_skill", dest, ledger)
    rc, out, _ = _un(tmp_path, ledger, {"start_menu": tmp_path / "s", "desktop": tmp_path / "d",
                                        "icon_dir": tmp_path / "i", "apps": tmp_path / "a"}, ["--yes"])
    assert rc == 0 and not dest.exists() and other.is_dir()
    # a ledger entry pointing somewhere else is refused, not deleted
    victim = tmp_path / "precious"
    victim.mkdir()
    shortcuts.ledger_record("claude_skill", victim, ledger)
    rc, out, _ = _un(tmp_path, ledger, {"start_menu": tmp_path / "s", "desktop": tmp_path / "d",
                                        "icon_dir": tmp_path / "i", "apps": tmp_path / "a"}, ["--yes"])
    assert victim.is_dir() and "left alone" in out and rc == 1


def test_registry_helper_refuses_keys_outside_fullseye():
    if not WIN:
        pytest.skip("winreg is Windows-only")
    with pytest.raises(shortcuts.ShortcutError, match="refusing"):
        shortcuts.unregister_uninstall_entry(r"Software\Microsoft\Windows\CurrentVersion\Run")


def test_pip_uninstall_command_and_helper_are_wired():
    cmd = uninstall.pip_uninstall_command()
    assert cmd == [sys.executable, "-m", "pip", "uninstall", "-y", "fullseye"]
    assert "WaitForSingleObject" in uninstall._HELPER and "time.sleep(1.5)" in uninstall._HELPER


def test_cli_setup_uninstall_non_terminal_lists_and_exits_zero(tmp_path):
    env = {"FULLSEYE_LEDGER": str(tmp_path / "none.json"), "FULLSEYE_CACHE_DIR": str(tmp_path / "c")}
    r = _cli("setup", "--uninstall", env_extra=env)
    assert r.returncode == 0 and "Fullseye uninstall" in r.stdout and "pip" in r.stdout
    r = _cli("setup", "--uninstall", "--dry-run", env_extra=env)
    assert r.returncode == 0 and "nothing was deleted" in r.stdout


def test_crash_log_stays_out_of_site_packages(tmp_path, monkeypatch):
    """pip 版(site-packages の中)ではログをパッケージ内に書かない(pip uninstall の後に残骸になる)。"""
    pytest.importorskip("PySide6")
    import studio
    monkeypatch.setattr(studio, "__file__", str(tmp_path / "Lib" / "site-packages" / "studio.py"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    p = Path(studio._crash_log_path())
    assert "site-packages" not in p.parts and p.name == "studio_crash.log" and p.parent.is_dir()
    monkeypatch.setattr(studio, "__file__", str(tmp_path / "checkout" / "studio.py"))
    assert Path(studio._crash_log_path()) == tmp_path / "checkout" / "studio_crash.log"
