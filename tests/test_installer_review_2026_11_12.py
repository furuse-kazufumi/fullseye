# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""インストーラ(fullseye.shortcuts / uninstall / setup_cmd / rag_setup)の独立レビュー(2026-11-12)指摘の回帰テスト。

番号は指摘の番号。危ない操作(消す・レジストリ)は必ず tmp と試験用キー ``Software\\FullseyeTest\\...`` で行い、
利用者の本物のファイル・本物の Uninstall キー・本物の台帳には触れない。
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fullseye import rag_setup, setup_cmd, shortcuts, uninstall  # noqa: E402

WIN = sys.platform == "win32"
winonly = pytest.mark.skipif(not WIN, reason="Windows-only")
KEY = r"Software\FullseyeTest\rev_"        # 試験用キーの接頭辞(本番コードは Software\FullseyeTest を許さない。引数で渡す)


# --------------------------------------------------------------------------- 共通
def _dirs(tmp_path):
    if WIN:
        return {"start_menu": tmp_path / "Programs" / "Fullseye", "desktop": tmp_path / "Desktop",
                "icon_dir": tmp_path / "local" / "Fullseye" / "setup"}
    return {"apps": tmp_path / "apps", "icon_dir": tmp_path / "icons", "desktop": tmp_path / "Desktop"}


def _plat():
    return "win" if WIN else "linux"


def _register(tmp_path, ledger, key, desktop=True):
    dirs = _dirs(tmp_path)
    if WIN:
        shortcuts.install(desktop=desktop, dirs=dirs, ledger=ledger, reg_key=key)
    else:
        shortcuts.install(platform="linux", python=sys.executable, dirs=dirs, ledger=ledger, desktop=desktop)
    return dirs


def _un(tmp_path, ledger, dirs, argv, allow=(), answers=(), tty=False, pip_state=("ok", ""), pip=None, regtree=None,
        registry=False):
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
    kw = {} if regtree is None else {"regtree": regtree}
    rc = uninstall.main(["--uninstall", "--lang", "en", *argv], input_fn=input_fn,
                        pip_fn=lambda: (calls.append(1), "LOGPATH")[1], is_tty=tty, out=buf, ledger=ledger, dirs=dirs,
                        env=env, registry=registry, allow_keys=tuple(allow), pip_check_fn=lambda: pip_state, **kw)
    return rc, buf.getvalue(), calls


def _assert_inside(root, key, path, what):
    root_r = os.path.normcase(os.path.realpath(str(root)))
    p = os.path.normcase(os.path.realpath(str(path)))
    if not (p == root_r or p.startswith(root_r + os.sep)):
        pytest.fail("SAFETY: %s %s is outside the test's tmp folder %s; refusing to run a test that could delete a real file"
                    % (what, path, root))


def guard_plan(root, key, *, ledger, dirs, env):
    """消す予定の一覧(``uninstall.collect``)を先に取り、一時フォルダの外のパス・自分の試験用キー以外のキーが 1 つでも
    入っていたら試験を失敗させる(何も消さない)。collect は何も変更しない。"""
    plan = uninstall.collect(ledger=ledger, dirs=dirs, env=env, registry=False, allow_keys=(key,))
    for it in list(plan["made"]) + list(plan["data"]):
        if it["kind"] in ("regkey", "settings_regtree"):
            if it["path"] != key:
                pytest.fail("SAFETY: registry key %s is not this test's key %s" % (it["path"], key))
        else:
            _assert_inside(root, key, it["path"], it["kind"])


def guard_script(script, root, key):
    """後始末 .cmd が消す対象(``del`` / ``rmdir`` / ``reg delete``)が、一時フォルダの中と自分の試験用キーだけであること。"""
    import re
    text = Path(script).read_text(encoding="utf-8")
    for line in text.splitlines():
        m = re.match(r'(?:del|rmdir)\s+"([^"]+)"', line)
        if m and not m.group(1).startswith("%"):
            _assert_inside(root, key, m.group(1).replace("%%", "%"), "script target")
        r = re.match(r'reg delete "HKCU\\([^"]+)"', line)
        if r and r.group(1) != key:
            pytest.fail("SAFETY: the script would delete registry key %s, not this test's key %s" % (r.group(1), key))
    assert 'del "%~f0"' in text


def _real_shortcut(path):
    """Fullseye Studio を起動する本物のショートカット(Windows は .lnk、Linux は .desktop)を作る。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    if WIN:
        shortcuts.write_lnk(path, Path(sys.executable), "-P -m studio", ROOT / "assets" / "fullseye.ico", path.parent)
    else:
        path.write_text(shortcuts.linux_desktop_text(sys.executable, Path("/i/x.png")), encoding="utf-8")


def _write_ledger(path, entries):
    path.write_text(json.dumps({"version": 1, "entries": entries}), encoding="utf-8")


# --------------------------------------------------------------------------- 1: 台帳の "file" は許可制
def test_1_tampered_ledger_cannot_delete_foreign_files_or_dirs(tmp_path):
    ledger = tmp_path / "ledger.json"
    dirs = _register(tmp_path, ledger, KEY + "1")
    docs = tmp_path / "Documents"
    docs.mkdir()
    victim = docs / "thesis.docx"                          # 名前が許可外
    victim.write_text("precious", encoding="utf-8")
    ico = docs / "fullseye.ico"                            # 名前は許可内でも置き場が許可外
    ico.write_bytes(b"x")
    emptydir = docs / "emptydir"                           # 空でも、setup が作ったフォルダではない
    emptydir.mkdir()
    ents = json.loads(ledger.read_text(encoding="utf-8"))["entries"]
    ents += [{"kind": "file", "path": str(victim)}, {"kind": "file", "path": str(ico)},
             {"kind": "file", "path": str(docs / ".." / "Documents" / "thesis.docx")},
             {"kind": "dir_if_empty", "path": str(emptydir)},
             {"kind": "regkey", "path": r"Software\Microsoft\Windows\CurrentVersion\Run"}]
    _write_ledger(ledger, ents)
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"], allow=(KEY + "1",))
    assert victim.read_text(encoding="utf-8") == "precious" and ico.exists() and emptydir.is_dir()
    assert rc == 1 and "NOT removed" in out and "thesis.docx" in out and "left alone" in out
    # 正当な項目は同じ実行で消えている(許可制が正当な削除まで止めていない)
    legit = [Path(e["path"]) for e in ents if e["kind"] == "file" and Path(e["path"]).parent != docs
             and Path(e["path"]).name != "thesis.docx"]
    assert legit and not any(p.exists() for p in legit)
    if WIN:
        shortcuts.regkey_exists(KEY + "1") and shortcuts.unregister_uninstall_entry(KEY + "1", (KEY + "1",))


def test_1_env_ledger_swap_is_also_checked(tmp_path, monkeypatch):
    """環境変数 FULLSEYE_LEDGER で別の台帳に差し替えても、同じ検証が掛かる(ledger 引数なしの既定経路)。"""
    victim = tmp_path / "Documents" / "thesis.docx"
    victim.parent.mkdir()
    victim.write_text("precious", encoding="utf-8")
    led = tmp_path / "swapped.json"
    _write_ledger(led, [{"kind": "file", "path": str(victim)}])
    monkeypatch.setenv("FULLSEYE_LEDGER", str(led))
    rc, out, _ = _un(tmp_path, None, None, ["--yes"])
    assert victim.exists() and rc == 1 and "NOT removed" in out


def test_1_remove_shortcuts_also_checks_the_ledger(tmp_path):
    ledger = tmp_path / "ledger.json"
    victim = tmp_path / "Documents" / "thesis.docx"
    victim.parent.mkdir()
    victim.write_text("precious", encoding="utf-8")
    _write_ledger(ledger, [{"kind": "file", "path": str(victim)}])
    skipped = []
    gone = shortcuts.remove(platform=_plat(), dirs=_dirs(tmp_path), ledger=ledger, skipped=skipped)
    assert gone == [] and victim.exists() and skipped and "left alone" in skipped[0][1]


# --------------------------------------------------------------------------- 2: claude_skill は置き場か目印が要る
def test_2_foreign_fullseye_ops_dir_is_left_alone_unless_marked_or_default(tmp_path, monkeypatch):
    mine = tmp_path / "Projects" / "mywork" / "fullseye-ops"
    (mine / "sub").mkdir(parents=True)
    (mine / "sub" / "notes.md").write_text("my dev work", encoding="utf-8")
    ledger = tmp_path / "ledger.json"
    _write_ledger(ledger, [{"kind": "claude_skill", "path": str(mine)}])
    dirs = {"start_menu": tmp_path / "s", "desktop": tmp_path / "d", "icon_dir": tmp_path / "i", "apps": tmp_path / "a"}
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"])
    assert (mine / "sub" / "notes.md").is_file() and rc == 1 and "left alone" in out and "marker" in out
    # fullseye-rag が置く目印があり、原本どおりなら消える
    pristine = rag_setup.install(tmp_path / "Projects2", repo=None, _auto_repo=False)
    _write_ledger(ledger, [{"kind": "claude_skill", "path": str(pristine)}])
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"])
    assert not pristine.exists() and rc == 0
    # 利用者が自分のファイルを足していたら、目印があっても --yes では残す(3 回目の指摘)
    mine2 = rag_setup.install(tmp_path / "Projects3", repo=None, _auto_repo=False)
    (mine2 / "my_notes.md").write_text("mine", encoding="utf-8")
    _write_ledger(ledger, [{"kind": "claude_skill", "path": str(mine2)}])
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"])
    assert (mine2 / "my_notes.md").is_file() and "edited by hand" in out and rc == 0
    # 既定の置き場(default_target)の直下なら、目印が無くても消える
    skills = tmp_path / "home" / ".claude" / "skills"
    other = rag_setup.install(skills, repo=None, _auto_repo=False)
    (other / rag_setup.MARKER_NAME).unlink()
    monkeypatch.setattr(rag_setup, "default_target", lambda: skills)
    _write_ledger(ledger, [{"kind": "claude_skill", "path": str(other)}])
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"])
    assert not other.exists() and rc == 0


def test_2_rag_install_writes_the_marker_and_uninstall_unlinks_a_junction_only(tmp_path):
    dest = rag_setup.install(tmp_path / "skills", repo=None, _auto_repo=False)
    assert (dest / rag_setup.MARKER_NAME).is_file()
    real = tmp_path / "real_data"
    real.mkdir()
    (real / "keep.txt").write_text("keep", encoding="utf-8")
    link_parent = tmp_path / "links"
    link_parent.mkdir()
    link = link_parent / rag_setup.SKILL_NAME
    try:
        os.symlink(real, link, target_is_directory=True)
    except OSError:
        pytest.skip("cannot create a symlink here")
    assert rag_setup.uninstall(link_parent) is True
    assert (real / "keep.txt").is_file() and not link.exists()


# --------------------------------------------------------------------------- 3: PowerShell は絶対パス
@winonly
def test_3_powershell_is_an_absolute_system_path_and_a_decoy_in_cwd_does_not_run(tmp_path, monkeypatch):
    ps = shortcuts.powershell_path()
    assert ps.is_absolute() and ps.name.lower() == "powershell.exe" and "system32" in str(ps).lower() and ps.is_file()
    with pytest.raises(shortcuts.ShortcutError, match="PowerShell not found"):
        shortcuts.powershell_path({"SystemRoot": str(tmp_path)})
    # Python 3.11 の shutil.which は作業フォルダを先に引く。置かれた powershell.bat が走ってはいけない
    work = tmp_path / "work"
    work.mkdir()
    marker = tmp_path / "DECOY_RAN"
    (work / "powershell.bat").write_text('@echo off\r\necho x> "%s"\r\n' % marker, encoding="ascii")
    (work / "powershell.cmd").write_text('@echo off\r\necho x> "%s"\r\n' % marker, encoding="ascii")
    monkeypatch.chdir(work)
    lnk = tmp_path / "t.lnk"
    shortcuts._write_lnk_via_powershell(lnk, Path(sys.executable), "-P -m studio", ROOT / "assets" / "fullseye.ico", tmp_path,
                                        "d")                                      # 退避の経路(PowerShell)だけが PowerShell を呼ぶ
    assert lnk.is_file() and shortcuts._read_lnk_via_powershell(lnk)["Arguments"] == "-P -m studio"
    assert not marker.exists(), "a powershell.bat in the working directory was executed"


def test_3_no_bare_which_lookups_remain_in_the_installer():
    for name in ("shortcuts", "uninstall", "setup_cmd", "rag_setup"):
        src = (ROOT / "fullseye" / (name + ".py")).read_text(encoding="utf-8")
        assert "shutil.which(" not in src and "which(" not in src.replace("`", ""), "%s.py resolves an executable through PATH + cwd" % name


# --------------------------------------------------------------------------- 4: -P -m studio / 作業フォルダ
def test_4_python_minus_P_ignores_a_decoy_module_in_cwd(tmp_path):
    work = tmp_path / "home"
    work.mkdir()
    (work / "decoy_mod_zz.py").write_text("print('DECOY')\n", encoding="utf-8")
    env = dict(os.environ, PYTHONUTF8="1")
    env.pop("PYTHONPATH", None)
    plain = subprocess.run([sys.executable, "-m", "decoy_mod_zz"], cwd=work, capture_output=True, text=True, env=env)
    assert "DECOY" in plain.stdout                          # -P なしだと cwd の物が先に読まれる(これが指摘の原因)
    safe = subprocess.run([sys.executable, "-P", "-m", "decoy_mod_zz"], cwd=work, capture_output=True, text=True, env=env)
    assert safe.returncode != 0 and "DECOY" not in safe.stdout and "No module named" in safe.stderr


def test_4_requires_python_allows_minus_P():
    import tomllib
    spec = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["requires-python"]
    assert spec.replace(" ", "").startswith(">=3.") and int(spec.replace(" ", "").split(".")[1].split(",")[0]) >= 11, spec
    assert shortcuts.STUDIO_ARGS == "-P -m studio"


@winonly
def test_4_lnk_reads_back_with_minus_P_and_setup_folder_as_workdir(tmp_path):
    dirs = _dirs(tmp_path)
    made = shortcuts.install(desktop=True, dirs=dirs, ledger=tmp_path / "l.json", reg_key=KEY + "4")
    assert len(made) == 2                                              # Start メニューとデスクトップ(空なら for は何も検査しない)
    try:
        for m in made:
            back = shortcuts.read_lnk(m)
            assert back["Arguments"] == "-P -m studio"
            assert Path(back["WorkingDir"]) == dirs["icon_dir"] and Path(back["WorkingDir"]) != Path.home()
    finally:
        shortcuts.remove(dirs=dirs, ledger=tmp_path / "l.json", allow_keys=(KEY + "4",))


def test_4_default_launch_uses_minus_P_and_the_setup_folder(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(setup_cmd.subprocess, "Popen", lambda args, **kw: seen.update(args=args, kw=kw))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    setup_cmd._default_launch()
    assert seen["args"][1:] == ["-P", "-m", "studio"]
    if WIN:
        assert Path(seen["kw"]["cwd"]) == tmp_path / "Local" / "Fullseye" / "setup"


# --------------------------------------------------------------------------- 5 / 14: pip の段
def test_5_pip_status_no_pip_in_a_venv_without_pip(tmp_path):
    v = tmp_path / "v"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(v)], check=True, capture_output=True)
    py = v / ("Scripts" if WIN else "bin") / ("python.exe" if WIN else "python")
    assert uninstall.pip_status(python=str(py)) == ("no_pip", "")


def test_5_no_pip_skips_the_pip_step_tells_uv_and_exits_3(tmp_path):
    ledger = tmp_path / "ledger.json"
    dirs = _register(tmp_path, ledger, KEY + "5")
    pip = []
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"], allow=(KEY + "5",), pip_state=("no_pip", ""), pip=pip)
    assert pip == [] and rc == 3
    assert "no pip" in out and "uv pip uninstall" in out and "fullseye" in out
    assert "Command to run:" not in out and "pip uninstall runs in a separate process" not in out
    made = [Path(e["path"]) for e in json.loads(ledger.read_text(encoding="utf-8"))["entries"]] if ledger.exists() else []
    assert not any(p.is_file() for p in made)               # 登録のほうは消えている(終了コードは pip の段だけを指す)


def test_5_dry_run_with_no_pip_exits_zero_and_still_explains(tmp_path):
    rc, out, _ = _un(tmp_path, tmp_path / "none.json", _dirs(tmp_path), ["--dry-run"], pip_state=("no_pip", ""))
    assert rc == 0 and "uv pip uninstall" in out


def _fake_dist(monkeypatch, location=None, direct_url=None, missing=False):
    class D:
        def locate_file(self, p):
            return Path(location) / p

        def read_text(self, name):
            return direct_url if name == "direct_url.json" else None

    def distribution(name):
        if missing:
            raise uninstall.importlib.metadata.PackageNotFoundError(name)
        return D()
    monkeypatch.setattr(uninstall.importlib.metadata, "distribution", distribution)


def test_14_pip_step_only_when_the_installed_fullseye_is_the_running_one(tmp_path, monkeypatch):
    pkg = tmp_path / "site" / "fullseye"
    pkg.mkdir(parents=True)
    _fake_dist(monkeypatch, location=tmp_path / "site")
    assert uninstall.dist_location_matches(pkg)[0] is True                         # 同じ場所
    _fake_dist(monkeypatch, location=tmp_path / "elsewhere")
    ok, why = uninstall.dist_location_matches(pkg)
    assert ok is False and "elsewhere" in why                                      # 別の fullseye が入っている
    _fake_dist(monkeypatch, missing=True)
    assert uninstall.dist_location_matches(pkg)[0] is None                         # 入っていない(checkout 直読み)
    editable = json.dumps({"url": (tmp_path / "site").as_uri(), "dir_info": {"editable": True}})
    _fake_dist(monkeypatch, location=tmp_path / "other", direct_url=editable)
    assert uninstall.dist_location_matches(pkg)[0] is True                         # editable は checkout の場所で比べる
    _fake_dist(monkeypatch, location=tmp_path / "other", direct_url=json.dumps({"url": tmp_path.as_uri()}))
    assert uninstall.dist_location_matches(pkg)[0] is False                        # editable でなければ一致しない
    _fake_dist(monkeypatch, location=tmp_path / "elsewhere")
    state, detail = uninstall.pip_status(pkg_dir=pkg)                              # この Python には pip がある
    if state == "no_pip":
        pytest.skip("this interpreter has no pip")
    assert state == "other" and "elsewhere" in detail


def test_14_main_does_not_offer_pip_when_the_distribution_is_elsewhere(tmp_path):
    ledger = tmp_path / "ledger.json"
    dirs = _register(tmp_path, ledger, KEY + "14")
    pip = []
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"], allow=(KEY + "14",), pip_state=("other", "installed: X / running: Y"),
                     pip=pip)
    assert pip == [] and rc == 0 and "different place" in out and "installed: X / running: Y" in out


# --------------------------------------------------------------------------- 6: 壊れた台帳
@pytest.mark.parametrize("content", ["{not json", '{"entries":{"a":1}}', "[1,2]", '"just a string"', "\x00\x01"])
def test_6_corrupt_ledger_dry_run_warns_and_falls_back_to_known_places(tmp_path, content):
    ledger = tmp_path / "ledger.json"
    ledger.write_text(content, encoding="utf-8")
    rc, out, _ = _un(tmp_path, ledger, _dirs(tmp_path), ["--dry-run"])
    assert rc == 0 and "could not be read" in out and "No ledger found" in out and "nothing was deleted" in out
    assert ledger.read_text(encoding="utf-8") == content                           # 壊れた台帳には触らない


def test_6_corrupt_ledger_yes_still_removes_known_places_only(tmp_path):
    dirs = _dirs(tmp_path)
    known = (dirs["start_menu"] / "Fullseye Studio.lnk") if WIN else (dirs["apps"] / "fullseye-studio.desktop")
    known.parent.mkdir(parents=True)
    _real_shortcut(known)
    stray = known.parent / "other.lnk"
    stray.write_bytes(b"x")
    ledger = tmp_path / "ledger.json"
    ledger.write_text("{not json", encoding="utf-8")
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"])
    assert rc == 0 and not known.exists() and stray.exists() and ledger.read_text(encoding="utf-8") == "{not json"
    # shortcuts 側の入口(remove / forget / gc)も壊れた台帳で落ちない
    assert shortcuts.remove(platform=_plat(), dirs=dirs, ledger=ledger) == []
    shortcuts.ledger_forget("file", known, ledger)
    shortcuts.ledger_gc(ledger)
    with pytest.raises(shortcuts.ShortcutError):               # 登録(書く側)は黙って上書きしない
        shortcuts.ledger_record("file", known, ledger)


def test_6_entries_with_wrong_types_are_dropped_not_crashed_on(tmp_path):
    ledger = tmp_path / "ledger.json"
    _write_ledger(ledger, [1, "x", {"kind": "file", "path": 5}, {"kind": "file"}, {"kind": "nope", "path": "a"}, None])
    assert shortcuts.ledger_load(ledger) == []
    rc, out, _ = _un(tmp_path, ledger, _dirs(tmp_path), ["--dry-run"])
    assert rc == 0


# --------------------------------------------------------------------------- 7: デスクトップ
@winonly
def test_7_desktop_is_the_real_known_folder_not_userprofile_guess():
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as k:
        shell_desktop = Path(winreg.QueryValueEx(k, "Desktop")[0])
    got = shortcuts.windows_dirs()["desktop"]
    assert got == shell_desktop and got.is_absolute()
    # テスト用の env 渡しは従来どおり USERPROFILE\Desktop(実機の場所に依存しない)
    d = shortcuts.windows_dirs({"APPDATA": r"C:\a", "LOCALAPPDATA": r"C:\l", "USERPROFILE": r"C:\u"})
    assert d["desktop"] == Path(r"C:\u") / "Desktop"


def test_15_relative_appdata_is_refused(tmp_path):
    with pytest.raises(shortcuts.ShortcutError, match="relative path"):
        shortcuts.windows_dirs({"APPDATA": "Roaming", "LOCALAPPDATA": str(tmp_path)})
    with pytest.raises(shortcuts.ShortcutError, match="relative path"):
        shortcuts.windows_dirs({"APPDATA": str(tmp_path), "LOCALAPPDATA": "..\\Local"})


# --------------------------------------------------------------------------- 8 / 10: テストが本物の台帳・レジストリを汚さない
def test_8_session_ledger_is_isolated_and_fullseye_rag_does_not_write_the_real_one(tmp_path):
    local = os.environ.get("LOCALAPPDATA")
    real = (Path(local) / "Fullseye" / "setup" / "install_ledger.json") if WIN and local else \
        (shortcuts._xdg_data() / "fullseye" / "install_ledger.json")
    before = real.read_bytes() if real.is_file() else None
    assert shortcuts.ledger_path() != real, "tests must run with FULLSEYE_LEDGER pointing at a temp file (conftest)"
    assert rag_setup.main(["--target", str(tmp_path / "skills")]) == 0           # fullseye-rag は台帳に書く
    assert (tmp_path / "skills" / "fullseye-ops" / rag_setup.MARKER_NAME).is_file()
    assert shortcuts.ledger_load(shortcuts.ledger_path())                         # 書いた先は一時の台帳
    assert rag_setup.main(["--target", str(tmp_path / "skills"), "--uninstall"]) == 0
    after = real.read_bytes() if real.is_file() else None
    assert before == after, "the real user ledger was modified by the test run"


@winonly
def test_10_test_registry_parent_key_is_removed_by_the_helper():
    import winreg
    from conftest import drop_fullseye_test_regkey
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Software\FullseyeTest\leftover\deep", 0, winreg.KEY_SET_VALUE):
        pass
    assert shortcuts.regkey_exists(r"Software\FullseyeTest")
    drop_fullseye_test_regkey()
    assert not shortcuts.regkey_exists(r"Software\FullseyeTest")


# --------------------------------------------------------------------------- 9: Uninstall キーは完全一致
def test_9_uninstall_key_guard_is_exact():
    bad = [r"Software\Microsoft\Windows\CurrentVersion\Uninstall\FullseyeOtherVendorApp",
           r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Fullseye Viewer 2",
           r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Fullseye\sub",
           r"Software\FullseyeTest\x", r"Software\Microsoft\Windows\CurrentVersion\Run"]
    for k in bad:
        assert shortcuts.check_ledger_item("regkey", k) is not None, k
    assert shortcuts.check_ledger_item("regkey", shortcuts.UNINSTALL_KEY) is None
    assert shortcuts.check_ledger_item("regkey", shortcuts.UNINSTALL_KEY.lower().replace("\\", "/")) is None
    assert shortcuts.check_ledger_item("regkey", r"Software\FullseyeTest\x", allow_keys=[r"Software\FullseyeTest\x"]) is None
    assert "fullseyetest" not in (ROOT / "fullseye" / "shortcuts.py").read_text(encoding="utf-8").lower(), \
        "the test-only key must not live in production code"


@winonly
def test_9_unregister_refuses_before_touching_the_registry():
    with pytest.raises(shortcuts.ShortcutError, match="refusing"):
        shortcuts.unregister_uninstall_entry(
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall\FullseyeOtherVendorApp")
    with pytest.raises(shortcuts.ShortcutError, match="refusing"):
        shortcuts.unregister_uninstall_entry(r"Software\FullseyeTest\no_permission")


# --------------------------------------------------------------------------- 11: 別の環境が作った物は残す
def test_11_second_environment_takes_ownership_and_first_cannot_remove_its_shortcuts(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.json"
    monkeypatch.setattr(shortcuts, "env_owner", lambda: str(tmp_path / "venvA"))
    dirs = _register(tmp_path, ledger, KEY + "11")
    monkeypatch.setattr(shortcuts, "env_owner", lambda: str(tmp_path / "venvB"))
    _register(tmp_path, ledger, KEY + "11")                                        # B が登録し直す
    owners = {e["owner"] for e in json.loads(ledger.read_text(encoding="utf-8"))["entries"]}
    assert owners == {str(tmp_path / "venvB")}
    files = [Path(e["path"]) for e in shortcuts.ledger_load(ledger) if e["kind"] == "file"]
    assert files and all(p.is_file() for p in files)
    # A から uninstall: B の物は --yes でも残る。画面で理由が分かる。pip の段(A 自身の fullseye)は出る
    monkeypatch.setattr(shortcuts, "env_owner", lambda: str(tmp_path / "venvA"))
    pip = []
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"], allow=(KEY + "11",), pip=pip)
    assert rc == 0 and all(p.is_file() for p in files) and "another Python environment" in out and "NOT removed" in out
    assert pip == [1]
    skipped = []
    assert shortcuts.remove(platform=_plat(), dirs=dirs, ledger=ledger, allow_keys=(KEY + "11",), skipped=skipped) == []
    assert skipped and all(p.is_file() for p in files)
    # B から uninstall: 消える
    monkeypatch.setattr(shortcuts, "env_owner", lambda: str(tmp_path / "venvB"))
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"], allow=(KEY + "11",))
    assert rc == 0 and not any(p.exists() for p in files)


def test_11_owner_of_python_is_the_venv_root_or_the_interpreter_folder(tmp_path):
    assert shortcuts.owner_of_python(None) == shortcuts.env_owner() == shortcuts.owner_of_python(sys.executable)
    venv = tmp_path / "venv"
    (venv / "Scripts").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = x", encoding="utf-8")
    assert shortcuts.owner_of_python(str(venv / "Scripts" / "python.exe")) == str(venv)
    assert shortcuts.owner_of_python(str(tmp_path / "py" / "python.exe")) == str(tmp_path / "py")


def test_11_foreign_entries_make_no_exit_code_error_and_unowned_legacy_entries_are_allowed(tmp_path):
    e = {"kind": "file", "path": "x"}
    assert shortcuts.entry_foreign(e) is None                                      # 持ち主不明は従来どおり
    assert shortcuts.entry_foreign(dict(e, owner=shortcuts.env_owner())) is None
    assert shortcuts.entry_foreign(dict(e, owner=str(tmp_path / "other"))) == str(tmp_path / "other")


# --------------------------------------------------------------------------- 12 / 13: Python に頼らない後始末スクリプト
def _stub_uninstaller(tmp_path, key, *, delete_key):
    """uninstall.py の代役: 呼ばれた引数と環境変数を記録し、delete_key なら Uninstall キーを消して終了コード 3 で終わる。"""
    p = tmp_path / "stub_uninstaller.py"
    p.write_text(
        "import os, sys, winreg\n"
        "open(os.path.join(os.path.dirname(__file__), 'stub_ran.txt'), 'w').write(repr((sys.argv[1:], os.environ.get('%s'))))\n"
        "if %r:\n"
        "    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, %r)\n"
        "sys.exit(3)\n" % (shortcuts.UNINSTALL_FROM_CMD_ENV, delete_key, key), encoding="utf-8")
    return p


@winonly
@pytest.mark.parametrize("delete_key", [True, False])
def test_12_script_runs_python_then_deletes_itself_only_when_the_uninstall_completed(tmp_path, delete_key):
    import winreg
    key = KEY + "12s"
    setup = tmp_path / "setup"
    setup.mkdir()
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE):
        pass
    script = setup / shortcuts.CMD_NAME
    stub = _stub_uninstaller(tmp_path, key, delete_key=delete_key)
    script.write_text(shortcuts.uninstall_cmd_text(python=Path(sys.executable), uninstaller=stub, lnks=[], regkey=key),
                      encoding="utf-8", newline="")
    guard_script(script, tmp_path, key)
    try:
        r = subprocess.run('"%s" --dry-run --lang en' % script, shell=True, capture_output=True, cwd=tmp_path)
        assert r.returncode == 3, r.stdout + r.stderr                       # Python の終了コードがそのまま返る
        args, env_flag = eval((tmp_path / "stub_ran.txt").read_text())
        assert args == ["--uninstall", "--pause", "--dry-run", "--lang", "en"] and env_flag == "1"
        assert b"cannot be found" not in r.stderr and b"\x83" not in r.stderr and r.stderr == b""     # バッチが消えたエラーは出ない
        if delete_key:                                                       # 完了 = キーが消えた: .cmd 自身と空の setup フォルダも消える
            assert not script.exists() and not setup.exists()
        else:                                                                # 未完了(--dry-run など): .cmd は残る
            assert script.is_file()
    finally:
        if shortcuts.regkey_exists(key):
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)


def test_12_python_side_does_not_delete_the_running_script(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.json"
    dirs = _register(tmp_path, ledger, KEY + "12p")
    script = dirs["icon_dir"] / shortcuts.CMD_NAME
    if not WIN:                                    # Linux には .cmd は無い。台帳に載せて同じ経路を通す(中身は後始末スクリプトの印つき)
        script.write_text("rem Fullseye uninstall helper\n", encoding="utf-8")
        shortcuts.ledger_record("file", script, ledger)
    assert script.is_file()
    monkeypatch.setenv(shortcuts.UNINSTALL_FROM_CMD_ENV, "1")
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"], allow=(KEY + "12p",))
    assert script.is_file() and rc == 0                                        # 走行中の .cmd は残す(.cmd 自身が後で消す)
    assert not any(e["path"] == str(script) for e in (shortcuts.ledger_load(ledger) or []))
    monkeypatch.delenv(shortcuts.UNINSTALL_FROM_CMD_ENV)
    if WIN:
        script.unlink()
        dirs["icon_dir"].rmdir() if not any(dirs["icon_dir"].iterdir()) else None


def _e2e_setup(tmp_path, root_name, key):
    venv = tmp_path / "v"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True, capture_output=True)
    vpy = venv / "Scripts" / "python.exe"
    root = tmp_path / root_name
    appdata, local = root / "Roaming", root / "Local"
    dirs = {"start_menu": appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Fullseye",
            "icon_dir": local / "Fullseye" / "setup", "desktop": root / "Desktop"}
    ledger = dirs["icon_dir"] / "install_ledger.json"
    shortcuts.install(desktop=True, python=str(vpy), dirs=dirs, ledger=ledger, reg_key=key)
    env = dict(os.environ, PYTHONUTF8="1", FS_NOPAUSE="1", APPDATA=str(appdata), LOCALAPPDATA=str(local),
               USERPROFILE=str(root), FULLSEYE_LEDGER=str(ledger), FULLSEYE_CACHE_DIR=str(root / "cache"),
               FULLSEYE_STUDIO_SETTINGS=str(root / "studio.ini"))
    guard_script(dirs["icon_dir"] / shortcuts.CMD_NAME, tmp_path, key)           # 本物の場所・本物のキーに触れないことを先に確かめる
    return venv, dirs, ledger, env, dirs["icon_dir"] / shortcuts.CMD_NAME


@winonly
@pytest.mark.parametrize("root_name", ["plain", "ユーザー 名's $env.X `y & ^ ! (1)", "ไทย עברית 한글 `$x & ^ ! (1)"])
def test_12_13_uninstall_script_works_with_python_then_without_it(tmp_path, root_name):
    import winreg
    key = KEY + "12"
    venv, dirs, ledger, env, script = _e2e_setup(tmp_path, root_name, key)
    assert script.is_file()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
        assert winreg.QueryValueEx(k, "UninstallString")[0] == '"%s"' % script          # 「アプリと機能」はこの .cmd を呼ぶ
    lnks = [dirs["start_menu"] / "Fullseye Studio.lnk", dirs["desktop"] / "Fullseye Studio.lnk"]
    mine = dirs["start_menu"] / "mine.txt"
    mine.write_text("not ours", encoding="utf-8")
    try:
        # (a) venv が在る: venv の python が uninstall.py を単独実行する(numpy / scipy の無い venv で動く = 13)
        r = subprocess.run('"%s" --dry-run --lang en' % script, shell=True, capture_output=True, env=env, cwd=tmp_path)
        out = r.stdout.decode("utf-8", "replace")
        assert r.returncode == 0 and "== Fullseye uninstall ==" in out and "Fullseye Studio.lnk" in out, out + r.stderr.decode("utf-8", "replace")
        assert all(p.is_file() for p in lnks)
        # (b) venv を消した(直接 pip uninstall / venv 削除と同じ): Python に頼らず、固定の名前だけを消す
        shutil.rmtree(venv)
        r = subprocess.run('"%s"' % script, shell=True, capture_output=True, env=env, cwd=tmp_path)
        out = r.stdout.decode("utf-8", "replace")
        assert r.returncode == 0, out + r.stderr.decode("utf-8", "replace")
        assert not any(p.exists() for p in lnks)
        assert not (dirs["icon_dir"] / "fullseye.ico").exists() and not ledger.exists()
        assert not shortcuts.regkey_exists(key), "the Apps & features entry survived"
        assert not script.exists(), "the script did not remove itself"
        assert r.stderr == b""
        assert mine.read_text(encoding="utf-8") == "not ours" and dirs["start_menu"].is_dir()    # 利用者の物は無傷
        assert not dirs["icon_dir"].exists()                                                   # 空になった setup フォルダは畳む
    finally:
        if shortcuts.regkey_exists(key):
            shortcuts.unregister_uninstall_entry(key, (key,))


@winonly
def test_12_fallback_dry_run_changes_nothing(tmp_path):
    key = KEY + "12d"
    venv, dirs, ledger, env, script = _e2e_setup(tmp_path, "dry", key)
    shutil.rmtree(venv)
    try:
        r = subprocess.run('"%s" --dry-run' % script, shell=True, capture_output=True, env=env, cwd=tmp_path)
        assert r.returncode == 0 and b"Nothing was changed" in r.stdout
        assert script.is_file() and shortcuts.regkey_exists(key) and ledger.is_file()
    finally:
        shortcuts.unregister_uninstall_entry(key, (key,))


def test_13_uninstall_runs_standalone_without_importing_the_package_or_numpy(tmp_path):
    code = ("import sys, runpy\n"
            "sys.argv = ['u', '--uninstall', '--dry-run', '--lang', 'en']\n"
            "try:\n    runpy.run_path(r'%s', run_name='__main__')\nexcept SystemExit:\n    pass\n"
            "print('HEAVY', [m for m in ('numpy', 'scipy', 'api', 'ops') if m in sys.modules])\n"
            % (ROOT / "fullseye" / "uninstall.py"))
    env = dict(os.environ, PYTHONUTF8="1", FULLSEYE_LEDGER=str(tmp_path / "none.json"),
               FULLSEYE_CACHE_DIR=str(tmp_path / "c"), FULLSEYE_STUDIO_SETTINGS=str(tmp_path / "s.ini"))
    r = subprocess.run([sys.executable, "-X", "utf8", "-I", "-c", code], capture_output=True, text=True,
                       encoding="utf-8", env=env, cwd=tmp_path)
    assert "== Fullseye uninstall ==" in r.stdout and "HEAVY []" in r.stdout, r.stdout + r.stderr


def test_12_uninstall_script_text_is_fixed_names_only_and_escapes_percent():
    s = shortcuts.uninstall_cmd_text(python=Path(r"C:\Py 3\a%b\python.exe"), uninstaller=Path(r"C:\x\uninstall.py"),
                                     lnks=[Path(r"C:\sm\Fullseye\Fullseye Studio.lnk")], regkey=shortcuts.UNINSTALL_KEY)
    assert 'set "FS_PY=C:\\Py 3\\a%%b\\python.exe"' in s and "\r\n" in s
    assert s.count("del ") == 5 and 'del "C:\\sm\\Fullseye\\Fullseye Studio.lnk"' in s       # lnk / ico / ledger / 自分自身(Python 経路と fallback 経路の 2 か所)
    assert "rmdir" in s and "rmdir /s" not in s and "rd /s" not in s and "rmdir /q" not in s        # 再帰削除はしない
    with pytest.raises(shortcuts.ShortcutError):
        shortcuts.uninstall_cmd_text(python=Path('C:\\a"b\\python.exe'), uninstaller=Path("u"), lnks=[], regkey="k")


# --------------------------------------------------------------------------- 15: 小さい物
def test_15_remove_does_not_delete_an_unledgered_desktop_shortcut(tmp_path):
    ledger = tmp_path / "ledger.json"
    dirs = _register(tmp_path, ledger, KEY + "15", desktop=False)
    name = "Fullseye Studio.lnk" if WIN else "fullseye-studio.desktop"
    stray = dirs["desktop"] / name                                   # 台帳に無い(利用者が自分で置いた)同名
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_bytes(b"mine")
    gone = shortcuts.remove(platform=_plat(), dirs=dirs, ledger=ledger, allow_keys=(KEY + "15",))
    assert gone and stray.read_bytes() == b"mine"


def test_15_registry_only_removal_is_not_reported_as_nothing_to_remove(monkeypatch):
    def fake_remove(**kw):
        kw["removed_keys"].append("Software\\X")
        return []
    monkeypatch.setattr(shortcuts, "remove", fake_remove)
    monkeypatch.setattr(shortcuts, "_platform", lambda p=None: "win" if WIN else "linux")
    buf = io.StringIO()
    assert shortcuts.run_cli(False, out=buf) == 0
    assert "removed registry entry" in buf.getvalue() and "nothing to remove" not in buf.getvalue()
    monkeypatch.setattr(shortcuts, "remove", lambda **kw: kw["skipped"].append(("p", "p is foreign; left alone")) or [])
    buf = io.StringIO()
    shortcuts.run_cli(False, out=buf)
    assert "kept: p is foreign" in buf.getvalue() and "nothing to remove" not in buf.getvalue()


@winonly
def test_15_a_failed_install_still_records_the_icon_it_copied(tmp_path, monkeypatch):
    (tmp_path / "py").mkdir()
    (tmp_path / "py" / "python.exe").write_bytes(b"")                  # pythonw.exe が無い → install は途中で失敗する
    ledger = tmp_path / "ledger.json"
    with pytest.raises(shortcuts.ShortcutError, match="pythonw.exe not found"):
        shortcuts.install(python=str(tmp_path / "py" / "python.exe"), dirs=_dirs(tmp_path), ledger=ledger,
                          reg_key=KEY + "15b")
    ents = shortcuts.ledger_load(ledger)
    assert len(ents) >= 1, ents
    assert any(e["kind"] == "file" and e["path"].endswith("fullseye.ico") for e in ents)
    assert not shortcuts.regkey_exists(KEY + "15b")
    monkeypatch.setattr(shortcuts, "env_owner", lambda: shortcuts.owner_of_python(str(tmp_path / "py" / "python.exe")))
    gone = shortcuts.remove(dirs=_dirs(tmp_path), ledger=ledger)
    assert [p.name for p in gone] == ["fullseye.ico"]


def test_15_desktop_entry_exec_is_escaped_per_the_spec():
    icon = Path("/i/x.png")
    text = shortcuts.linux_desktop_text('/o/p"q$r%s/py', icon)
    assert r'Exec="/o/p\\"q\\$r%%s/py" -P -m studio' in text
    assert "Exec=/usr/bin/python3 -P -m studio\n" in shortcuts.linux_desktop_text("/usr/bin/python3", icon)
    assert 'Exec="/opt/py 3/bin/python" -P -m studio' in shortcuts.linux_desktop_text("/opt/py 3/bin/python", icon)
    assert "Exec=/a%%b/python" in shortcuts.linux_desktop_text("/a%b/python", icon)
    with pytest.raises(shortcuts.ShortcutError):
        shortcuts.linux_desktop_text("/a\nb/python", icon)


def test_15_spawn_flags_do_not_combine_detached_with_no_window_and_fall_back_without_breakaway(monkeypatch):
    calls = []

    def fake(args, **kw):
        calls.append(kw.get("creationflags"))
        if len(calls) == 1 and kw.get("creationflags", 0) & 0x01000000:
            raise PermissionError("job does not allow breakaway")
        return None
    monkeypatch.setattr(uninstall.subprocess, "Popen", fake)
    monkeypatch.setattr(uninstall.sys, "platform", "win32")
    uninstall.spawn_pip_uninstall()
    assert len(calls) == 2 and calls[0] & 0x01000000 and not calls[1] & 0x01000000
    assert all(not (f & 0x00000008 and f & 0x08000000) for f in calls)             # DETACHED と NO_WINDOW を併用しない
    assert all(f & 0x00000008 and f & 0x00000200 for f in calls)
    calls.clear()
    monkeypatch.setattr(uninstall.subprocess, "Popen", lambda a, **kw: calls.append(kw.get("creationflags")))
    uninstall.spawn_pip_uninstall()
    assert len(calls) == 1 and calls[0] & 0x01000000


# --------------------------------------------------------------------------- 16: テストの盲点
@winonly
def test_16_settings_registry_tree_is_deleted_through_the_real_reg_delete_tree(tmp_path):
    import winreg
    tree = r"Software\FullseyeTest\tree\Studio"
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, tree + r"\sub", 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "v", 0, winreg.REG_SZ, "1")
    with pytest.raises(shortcuts.ShortcutError, match="refusing"):                     # 許可なしでは消さない
        uninstall._reg_delete_tree(tree)
    assert shortcuts.regkey_exists(tree)
    plan = uninstall.collect(ledger=tmp_path / "none.json", dirs=_dirs(tmp_path), env={"FULLSEYE_CACHE_DIR": str(tmp_path / "cache")},
                             registry=True, regtree=tree)
    assert len(plan["data"]) >= 1                            # 計画が空でない(設定のキーが見えている)ことの確認
    for it in plan["made"]:                                  # 安全弁: 本物の Uninstall キーは計画に入っていない(conftest が差し替える)
        assert it["kind"] != "regkey" or it["path"].startswith("Software\\FullseyeTest\\"), it
    rc, out, _ = _un(tmp_path, tmp_path / "none.json", _dirs(tmp_path), [], answers=["y", "n"], tty=True,
                     regtree=tree, registry=True)
    assert rc == 0 and "settings (registry)" in out and "Software\\FullseyeTest\\tree\\Studio" in out
    assert not shortcuts.regkey_exists(tree) and not shortcuts.regkey_exists(r"Software\FullseyeTest\tree")


@winonly
def test_16_uninstall_deletes_the_apps_and_features_key_for_real(tmp_path):
    ledger = tmp_path / "ledger.json"
    key = KEY + "16"
    dirs = _register(tmp_path, ledger, key)
    assert shortcuts.regkey_exists(key)
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"], allow=(key,))
    assert rc == 0 and not shortcuts.regkey_exists(key) and "Apps & features" in out


def _wheel_check(*args):
    return subprocess.run([sys.executable, str(ROOT / "tools" / "ci_wheel_check.py"), *args], capture_output=True,
                          text=True, encoding="utf-8", timeout=600, env=dict(os.environ, PYTHONUTF8="1"))


def test_16_wheel_check_fails_when_the_icons_are_missing_from_the_wheel(tmp_path):
    ops = ["tb_%d" % i for i in range(100)] + ["hx_%d" % i for i in range(50)]
    base = {"root_modules": [], "ops": ops, "failed_backends": [], "catalogs_missing": [], "unshipped_present": [],
            "py_modules_declared": []}
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(base), encoding="utf-8")
    b.write_text(json.dumps(dict(base, icons_missing=[])), encoding="utf-8")
    r = _wheel_check("--compare", str(a), str(b))
    assert r.returncode == 0, r.stdout + r.stderr
    b.write_text(json.dumps(dict(base, icons_missing=["studio_assets/fullseye.ico"])), encoding="utf-8")
    r = _wheel_check("--compare", str(a), str(b))
    assert r.returncode == 1 and "fullseye.ico" in r.stdout and "アイコン" in r.stdout


def test_16_wheel_check_dump_reports_icons_it_could_not_find(tmp_path):
    """--dump が icons_missing を出す(中身は、その Python が import する studio_assets に依る = wheel 環境で意味を持つ)。"""
    out = tmp_path / "d.json"
    r = _wheel_check("--dump", str(out))
    assert r.returncode == 0, r.stdout + r.stderr
    miss = json.loads(out.read_text(encoding="utf-8"))["icons_missing"]
    assert isinstance(miss, list) and set(miss) <= {"studio_assets/fullseye.ico", "studio_assets/fullseye_256.png"}


# =========================================================================== 2 回目の独立レビュー(2026-11-12)
# 番号は 2 回目の指摘の番号(R1〜R11)。
def _make_venv(tmp_path):
    venv = tmp_path / "v"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True, capture_output=True)
    return venv, venv / "Scripts" / "python.exe"


def _e2e_dirs(root):
    appdata, local = root / "Roaming", root / "Local"
    return {"start_menu": appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Fullseye",
            "icon_dir": local / "Fullseye" / "setup", "desktop": root / "Desktop"}


def _run_script(script, args, tmp_path, root):
    env = dict(os.environ, PYTHONUTF8="1", FS_NOPAUSE="1", FULLSEYE_LEDGER=str(root / "Local" / "Fullseye" / "setup" /
               "install_ledger.json"), FULLSEYE_CACHE_DIR=str(root / "cache"), FULLSEYE_STUDIO_SETTINGS=str(root / "s.ini"),
               APPDATA=str(root / "Roaming"), LOCALAPPDATA=str(root / "Local"), USERPROFILE=str(root))
    return subprocess.run('"%s" %s' % (script, args), shell=True, capture_output=True, env=env, cwd=tmp_path,
                          stdin=subprocess.DEVNULL)


@winonly
def test_R1_script_falls_back_when_the_venv_python_exists_but_cannot_start(tmp_path):
    """venv の元の Python を消した(pyvenv.cfg の home が無い)と、python.exe は在るが rc=103 で起動しない。"""
    key = KEY + "R1"
    venv, vpy = _make_venv(tmp_path)
    root = tmp_path / "root"
    dirs = _e2e_dirs(root)
    ledger = dirs["icon_dir"] / "install_ledger.json"
    made = shortcuts.install(desktop=True, python=str(vpy), dirs=dirs, ledger=ledger, reg_key=key)
    cfg = venv / "pyvenv.cfg"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace("home = ", "home = C:\\nope_"), encoding="utf-8")
    assert subprocess.run([str(vpy), "-c", "print(1)"], capture_output=True).returncode != 0   # 前提: 起動しない
    script = dirs["icon_dir"] / shortcuts.CMD_NAME
    guard_script(script, tmp_path, key)
    try:
        r = _run_script(script, "", tmp_path, root)
        assert r.returncode == 0, r.stdout + r.stderr
        assert not any(p.exists() for p in made) and not ledger.exists() and not script.exists()
        assert not shortcuts.regkey_exists(key), "the Apps & features entry survived a broken venv"
        assert not dirs["icon_dir"].exists() and r.stderr == b""
    finally:
        if shortcuts.regkey_exists(key):
            shortcuts.unregister_uninstall_entry(key, (key,))


def _wrapper_source(root, key, dirs, env_for_plan, plan_path):
    """別プロセスで uninstall を呼ぶ包み。**自分で collect を取って JSON に書き**、一時フォルダの外・自分以外のキーが 1 件でも
    あれば何も消さず 99 で終わる。``--wrap-plan-only`` では書くだけで消さない(試験が先に中身を確かめる段)。"""
    return ("import sys, types, json, os\nfrom pathlib import Path\n"
            "st = types.ModuleType('fullseye'); st.__path__ = [%r]; sys.modules['fullseye'] = st\n"
            "from fullseye import uninstall as u\n"
            "ROOT = %r; KEY = %r; PLAN = Path(%r)\n"
            "dirs = {k: Path(v) for k, v in %r.items()}\nenv = %r\n"
            "plan_only = '--wrap-plan-only' in sys.argv\n"
            "sys.argv = [a for a in sys.argv if a != '--wrap-plan-only']\n"
            "plan = u.collect(dirs=dirs, env=env, registry=False, allow_keys=[KEY])\n"
            "items = [{'kind': i['kind'], 'path': i['path']} for i in plan['made'] + plan['data']]\n"
            "root = os.path.normcase(os.path.realpath(ROOT)) + os.sep\n"
            "def inside(p): return (os.path.normcase(os.path.realpath(p)) + os.sep).startswith(root)\n"
            "outside = [i for i in items if (i['path'] != KEY if i['kind'] in ('regkey', 'settings_regtree') else not inside(i['path']))]\n"
            "PLAN.write_text(json.dumps({'items': items, 'outside': outside}), encoding='utf-8')\n"
            "if outside: sys.exit(99)\n"
            "if plan_only: sys.exit(0)\n"
            "sys.exit(u.main(dirs=dirs, env=env, registry=False, allow_keys=[KEY]))\n"
            % (str(ROOT / "fullseye"), str(root), key, str(plan_path), {k: str(v) for k, v in dirs.items()}, env_for_plan))


def verify_plan_file(plan_path, root, key, expect_names=()):
    """包み(別プロセス)が実際に取った「消す予定の一覧」を読んで確かめる。無い・外のパスがある・他のキーがある・期待する物が無い、は失敗。"""
    p = Path(plan_path)
    if not p.is_file():
        pytest.fail("SAFETY: the wrapper wrote no plan file %s (does it still call collect with isolated arguments?)" % p)
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("outside"):
        pytest.fail("SAFETY: the wrapper's own plan lists items outside the test folder: %s" % data["outside"])
    for it in data["items"]:
        if it["kind"] in ("regkey", "settings_regtree"):
            if it["path"] != key:
                pytest.fail("SAFETY: the wrapper's plan names registry key %s, not this test's key" % it["path"])
        else:
            _assert_inside(root, key, it["path"], it["kind"])
    missing = set(expect_names) - {Path(i["path"]).name for i in data["items"]}
    if missing:
        pytest.fail("SAFETY: the wrapper's plan does not contain the test's own items %s (isolation arguments dropped?)" % sorted(missing))


def test_R2_plan_verifier_rejects_a_missing_an_outside_and_a_foreign_plan(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    good = {"items": [{"kind": "file", "path": str(root / "a.lnk")}, {"kind": "regkey", "path": KEY + "v"}], "outside": []}
    p = tmp_path / "plan.json"
    with pytest.raises(pytest.fail.Exception):                         # 包みが一覧を書かなかった(昔の u.main だけの包みへ戻した変異)
        verify_plan_file(p, root, KEY + "v")
    p.write_text(json.dumps(good), encoding="utf-8")
    verify_plan_file(p, root, KEY + "v", expect_names={"a.lnk"})
    for bad in (dict(good, outside=[{"kind": "file", "path": "x"}]),
                dict(good, items=good["items"] + [{"kind": "file", "path": str(tmp_path / "real" / "Fullseye Studio.lnk")}]),
                dict(good, items=good["items"] + [{"kind": "regkey", "path": r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Fullseye"}])):
        p.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(pytest.fail.Exception):
            verify_plan_file(p, root, KEY + "v")
    p.write_text(json.dumps(good), encoding="utf-8")
    with pytest.raises(pytest.fail.Exception):                         # 期待する自分の物が無い(隔離の引数が落ちた)
        verify_plan_file(p, root, KEY + "v", expect_names={"fullseye.ico"})


@winonly
def test_R2_corrupt_ledger_legacy_removes_the_key_icon_and_script_and_the_cmd_finishes(tmp_path):
    key = KEY + "R2"
    venv, vpy = _make_venv(tmp_path)
    root = tmp_path / "root"
    dirs = _e2e_dirs(root)
    ledger = dirs["icon_dir"] / "install_ledger.json"
    made = shortcuts.install(desktop=False, python=str(vpy), dirs=dirs, ledger=ledger, reg_key=key)
    ledger.write_text("{not json", encoding="utf-8")                       # 台帳が壊れた → 「台帳なし」の既知の場所
    # ★3 回目・4 回目のレビュー: 包みが dirs / env / registry を渡さないと、本物のデスクトップ・Uninstall\Fullseye が計画に入る。
    #   試験と同じプロセスで作った一覧を見るだけでは、別プロセスの包みの呼び出しを見ていない。包みが**自分で**取った一覧を JSON で
    #   受け取り、試験が確かめてから消す段(2 段目)へ進む。
    env_for_plan = {"FULLSEYE_CACHE_DIR": str(root / "cache"), "LOCALAPPDATA": str(root / "Local"),
                    "FULLSEYE_STUDIO_SETTINGS": str(root / "studio.ini")}
    plan_path = tmp_path / "wrapper_plan.json"
    wrapper = tmp_path / "wrap.py"
    wrapper.write_text(_wrapper_source(root, key, dirs, env_for_plan, plan_path), encoding="utf-8")
    script = dirs["icon_dir"] / shortcuts.CMD_NAME
    script.write_text(shortcuts.uninstall_cmd_text(python=vpy, uninstaller=wrapper, lnks=made, regkey=key),
                      encoding="utf-8", newline="")
    guard_script(script, tmp_path, key)
    try:
        r1 = _run_script(script, "--wrap-plan-only --yes --lang en", tmp_path, root)           # 1 段目: 一覧だけ(何も消さない)
        assert r1.returncode == 0 and all(p.exists() for p in made) and shortcuts.regkey_exists(key), r1.stdout + r1.stderr
        verify_plan_file(plan_path, root, key, expect_names={"Fullseye Studio.lnk", "fullseye.ico", shortcuts.CMD_NAME})
        r = _run_script(script, "--yes --lang en", tmp_path, root)                             # 2 段目: 本当に消す
        out = r.stdout.decode("utf-8", "replace")
        assert r.returncode in (0, 3), out + r.stderr.decode("utf-8", "replace")       # 3 = pip の無い venv(本体が残る)
        assert "could not be read" in out
        assert not any(p.exists() for p in made) and not (dirs["icon_dir"] / "fullseye.ico").exists()
        assert not shortcuts.regkey_exists(key), "legacy detection did not include the Apps & features key"
        assert not script.exists(), "the .cmd was left behind"
        assert [p.name for p in dirs["icon_dir"].iterdir()] == ["install_ledger.json"]    # 壊れた台帳だけが残る(触らない方針。手で消す)
        assert ledger.read_text(encoding="utf-8") == "{not json"
    finally:
        if shortcuts.regkey_exists(key):
            shortcuts.unregister_uninstall_entry(key, (key,))


def test_R2_legacy_places_lists_only_fixed_names(tmp_path):
    dirs = _dirs(tmp_path)
    if WIN:
        for p in (dirs["icon_dir"] / "fullseye.ico", dirs["icon_dir"] / shortcuts.CMD_NAME,
                  dirs["icon_dir"] / "other.txt", dirs["start_menu"] / "Fullseye Studio.lnk"):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x", encoding="utf-8")
        got = {Path(i["path"]).name for i in uninstall._legacy_places("win", dirs, registry=False)}
        assert got == {"fullseye.ico", shortcuts.CMD_NAME, "Fullseye Studio.lnk"}


def _junction(tmp_path, name="fullseye-ops"):
    real = tmp_path / "repo" / "skills" / "fullseye-ops"
    real.mkdir(parents=True)
    (real / "SKILL.md").write_text("dev source", encoding="utf-8")
    (real / rag_setup.MARKER_NAME).write_text("x", encoding="utf-8")
    home = tmp_path / "linkhome"
    home.mkdir()
    j = home / name
    subprocess.run(["cmd", "/c", "mklink", "/J", str(j), str(real)], check=True, capture_output=True)
    return real, home, j


@winonly
def test_R3_junction_skill_is_unlinked_not_rmtreed_and_rag_uninstall_does_not_crash(tmp_path):
    real, home, j = _junction(tmp_path)
    assert not j.is_symlink() and rag_setup.is_link(j)                       # 3.11 の is_symlink は False(これが指摘の原因)
    ledger = tmp_path / "ledger.json"
    _write_ledger(ledger, [{"kind": "claude_skill", "path": str(j)}])
    rc, out, _ = _un(tmp_path, ledger, _dirs(tmp_path), ["--yes"])
    assert rc == 0 and not os.path.lexists(j) and (real / "SKILL.md").read_text(encoding="utf-8") == "dev source"
    real2, home2, j2 = _junction(tmp_path / "second")
    assert rag_setup.main(["--target", str(home2), "--uninstall"]) == 0         # 例外で落ちない
    assert not os.path.lexists(j2) and (real2 / "SKILL.md").exists()


def test_R4_non_empty_folder_is_reported_as_kept_not_removed(tmp_path):
    dirs = _dirs(tmp_path)
    folder = dirs["start_menu"] if WIN else dirs["icon_dir"]
    folder.mkdir(parents=True)
    (folder / "mine.txt").write_text("user file", encoding="utf-8")
    ledger = tmp_path / "ledger.json"
    _write_ledger(ledger, [{"kind": "dir_if_empty", "path": str(folder)}])
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"])
    assert folder.is_dir() and (folder / "mine.txt").is_file()
    if not WIN:        # Linux は畳むフォルダを作らないので、台帳のそういう行は許可外 = 消さずに理由つきで出す(終了コード 1)
        assert rc == 1 and "NOT removed" in out and "not a folder fullseye setup created" in out
        return
    removed_part = out.split("[Removed]")[1].split("[")[0]
    assert rc == 0 and "empty folder" not in removed_part and "[Kept]" in out and str(folder) in out.split("[Kept]")[1]


def test_R4_the_running_script_is_listed_apart_as_removed_after_this_window(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.json"
    dirs = _register(tmp_path, ledger, KEY + "R4")
    script = dirs["icon_dir"] / shortcuts.CMD_NAME
    if not WIN:
        script.write_text("rem Fullseye uninstall helper\n", encoding="utf-8")
        shortcuts.ledger_record("file", script, ledger)
    monkeypatch.setenv(shortcuts.UNINSTALL_FROM_CMD_ENV, "1")
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"], allow=(KEY + "R4",))
    assert rc == 0 and script.is_file()
    removed_part = out.split("[Removed]")[1].split("[Removed by the cleanup script")[0]
    assert shortcuts.CMD_NAME not in removed_part
    later = out.split("[Removed by the cleanup script right after this window closes]")[1]
    assert shortcuts.CMD_NAME in later
    assert str(dirs["icon_dir"]) in later or not WIN          # スクリプトが入っている setup フォルダ(畳むフォルダの記録は Windows だけ)
    assert "[Kept]" not in out or str(dirs["icon_dir"]) not in out.split("[Kept]")[1]
    monkeypatch.delenv(shortcuts.UNINSTALL_FROM_CMD_ENV)
    if WIN:
        script.unlink()


def test_R5_hand_edited_skill_is_kept_by_default_and_asked_separately(tmp_path):
    dest = rag_setup.install(tmp_path / "skills", repo=None, _auto_repo=False)
    assert rag_setup.skill_edited(dest) is False                                    # 原本どおり(FULLSEYE_REPO の行は見ない)
    md = dest / "SKILL.md"
    md.write_text(md.read_text(encoding="utf-8") + "\nMY NOTES\n", encoding="utf-8")
    assert rag_setup.skill_edited(dest) is True
    ledger = tmp_path / "ledger.json"
    _write_ledger(ledger, [{"kind": "claude_skill", "path": str(dest)}])
    dirs = {"start_menu": tmp_path / "s", "desktop": tmp_path / "d", "icon_dir": tmp_path / "i", "apps": tmp_path / "a"}
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"])
    assert "edited by hand" in out and "MY NOTES" in md.read_text(encoding="utf-8") and "[Kept]" in out and rc == 0
    # 対話で y と答えれば消せる(別の問い)
    rc, out, _ = _un(tmp_path, ledger, dirs, [], answers=["y", "n"], tty=True)
    assert not dest.exists()


def test_R6_user_site_install_is_found_and_not_installed_is_a_separate_message(tmp_path, monkeypatch):
    pkg = tmp_path / "usersite" / "fullseye"
    pkg.mkdir(parents=True)
    info = tmp_path / "usersite" / "fullseye-1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: fullseye\nVersion: 1.0\n", encoding="utf-8")
    _fake_dist(monkeypatch, missing=True)                                           # -I はユーザー site を外すので、通常の検索では見えない
    import site
    monkeypatch.setattr(site, "getusersitepackages", lambda: str(tmp_path / "usersite"))
    assert uninstall.dist_location_matches(pkg)[0] is True                          # ユーザー site も探す
    monkeypatch.setattr(site, "getusersitepackages", lambda: str(tmp_path / "empty"))
    ok, why = uninstall.dist_location_matches(pkg)
    assert ok is None and "no fullseye distribution" in why
    state, detail = uninstall.pip_status(pkg_dir=pkg)
    if state != "no_pip":
        assert state == "none"
    rc, out, _ = _un(tmp_path, tmp_path / "x.json", _dirs(tmp_path), ["--yes"], pip_state=("none", "no fullseye distribution"))
    assert "not pip-installed" in out and "different place" not in out


def test_R7_percent_var_in_the_setup_folder_is_refused_at_registration(tmp_path, monkeypatch):
    monkeypatch.setenv("FSTESTVAR_ZZ", "x")
    with pytest.raises(shortcuts.ShortcutError, match="FSTESTVAR_ZZ"):
        shortcuts.reject_expandable_percent(tmp_path / "a%FSTESTVAR_ZZ%b")
    with pytest.raises(shortcuts.ShortcutError, match="(?i)cd"):
        shortcuts.reject_expandable_percent(tmp_path / "%cd%")
    shortcuts.reject_expandable_percent(tmp_path / "100%" / "a%UNDEFINED_VAR_ZZ9%b")     # 未定義の形・単独の % は展開されない
    if WIN:
        d = _dirs(tmp_path)
        d["icon_dir"] = tmp_path / "x%FSTESTVAR_ZZ%y" / "setup"
        with pytest.raises(shortcuts.ShortcutError, match="expand"):
            shortcuts.install(dirs=d, ledger=tmp_path / "l.json", reg_key=KEY + "R7")
        assert not d["icon_dir"].exists() and not shortcuts.regkey_exists(KEY + "R7")      # 何も作らずに止まる


def test_R8_exit_codes_follow_the_table(tmp_path):
    for state, want in ((("ok", ""), 0), (("none", "x"), 0), (("other", "x"), 0), (("no_pip", ""), 3)):
        ledger = tmp_path / ("l_%s.json" % state[0])
        dirs = _register(tmp_path / state[0], ledger, KEY + "R8")
        rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"], allow=(KEY + "R8",), pip_state=state)
        assert rc == want, (state, rc, out)
    assert "終了コード" in (ROOT / "fullseye" / "uninstall.py").read_text(encoding="utf-8")


def test_R8_setup_exits_nonzero_when_a_step_failed():
    from test_studio_shortcuts_2026_11_12 import Fakes, _run
    f = Fakes(pip_rc=1)
    rc, out = _run(["--yes", "--lang", "en"], f, tty=False)
    assert rc == 1 and "dependency install failed" in out
    f2 = Fakes()
    k = f2.kw(tty=False)

    def boom(desktop):
        raise OSError("no start menu")
    k["shortcuts_fn"] = boom
    assert setup_cmd.main(["--yes", "--lang", "en"], **k) == 1
    f3 = Fakes()
    assert _run(["--yes", "--lang", "en"], f3, tty=False)[0] == 0


def test_R9_ci_has_a_windows_job_that_runs_the_windows_only_installer_tests():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    job = text.split("\n  windows-installer:\n", 1)[1].split("\n  # ", 1)[0].split("\n  lint:", 1)[0]
    assert "runs-on: windows-latest" in job and "needs: changes" in job
    assert "tests/test_installer_review_2026_11_12.py" in job and "tests/test_studio_shortcuts_2026_11_12.py" in job
    assert "actions/checkout@" in job and "actions/setup-python@" in job and "pip>=26.2.2" in job
    try:
        import yaml
    except ImportError:
        return
    doc = yaml.safe_load(text)
    j = doc["jobs"]["windows-installer"]
    assert j["runs-on"] == "windows-latest" and all("uses" in s or "run" in s for s in j["steps"])


def test_R11_mcp_choice_goes_through_display_to_knob_and_values_do_not_change():
    from fullseye.mcp import server
    from param_specs import display_to_knob, knob_to_display
    spec = {"kind": "choice", "choices": [1, 2, 4, 8], "unit": ""}
    for i, v in enumerate(spec["choices"]):
        got = server._physical_value_to_knob("op", "p", v, spec)
        assert got == (i + 0.5) / 4 == display_to_knob(spec, i)                  # 等幅の choice では従来と同じ値
        assert knob_to_display(spec, got) == i
    src = (ROOT / "fullseye" / "mcp" / "server.py").read_text(encoding="utf-8")
    assert "(allowed.index(shown) + 0.5) / len(allowed)" not in src


# =========================================================================== 3 回目の独立レビュー(2026-11-12)
def test_S0_the_watcher_detects_a_changed_real_registration_and_is_otherwise_stable(monkeypatch, tmp_path):
    from conftest import real_install_snapshot, snapshot_diff
    a, b = real_install_snapshot(), real_install_snapshot()
    assert snapshot_diff(a, b) == []                                                  # 何も触らなければ前後で同じ
    assert snapshot_diff({"desktop": [("x", 1, 2)]}, {"desktop": []}) and snapshot_diff({}, {}) == []
    if WIN:                                                                           # 偽のデスクトップに置くと一覧に出る
        fake = tmp_path / "Desktop"
        fake.mkdir()
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        before = real_install_snapshot()
        (fake / "Fullseye Studio.lnk").write_bytes(b"x")
        diff = snapshot_diff(before, real_install_snapshot())
        assert diff and "Fullseye Studio.lnk" in diff[0]


def test_S0_the_installer_tests_cannot_name_the_real_uninstall_key():
    assert shortcuts.UNINSTALL_KEY.startswith("Software\\FullseyeTest\\")           # conftest が差し替えている(別プロセスは対象外)


def test_S0_guards_refuse_paths_outside_tmp(tmp_path):
    with pytest.raises(pytest.fail.Exception):
        _assert_inside(tmp_path / "a", KEY, tmp_path / "b" / "x", "file")
    _assert_inside(tmp_path, KEY, tmp_path / "a" / "b", "file")
    ledger = tmp_path / "l.json"
    _write_ledger(ledger, [{"kind": "file", "path": str(tmp_path.parent / "Fullseye Studio.lnk")}])


@winonly
def test_S1_legacy_and_ledger_items_are_deleted_only_when_the_content_says_they_are_fullseyes(tmp_path):
    import winreg
    dirs = _dirs(tmp_path)
    # 台帳なし(legacy): 名前は同じでも、起動するのが Fullseye でない .lnk は消さない。install.ps1 形式(studio.py)は Fullseye の物
    other = dirs["desktop"] / "Fullseye Studio.lnk"
    other.parent.mkdir(parents=True)
    shortcuts.write_lnk(other, Path(sys.executable), "-c print(1)", ROOT / "assets" / "fullseye.ico", tmp_path)
    ps1 = dirs["start_menu"] / "Fullseye Studio.lnk"
    shortcuts.write_lnk(ps1, Path(sys.executable), '"C:\\repo\\studio.py"', ROOT / "assets" / "fullseye.ico", tmp_path)
    assert shortcuts.verify_fullseye_item("file", str(other)) is not None
    assert shortcuts.verify_fullseye_item("file", str(ps1)) is None
    (dirs["icon_dir"]).mkdir(parents=True)
    (dirs["icon_dir"] / "fullseye.ico").write_bytes(b"not an icon")
    (dirs["icon_dir"] / shortcuts.CMD_NAME).write_text("@echo hello\r\n", encoding="utf-8")
    key = KEY + "S1"
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, "Somebody Else's App")
        winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ, "C:\\other\\unins000.exe")
    try:
        plan = uninstall.collect(ledger=tmp_path / "none.json", dirs=dirs, env={"FULLSEYE_CACHE_DIR": str(tmp_path / "c")},
                                 registry=False, allow_keys=(key,))
        made = {Path(i["path"]).name for i in plan["made"] if i["kind"] == "file"}
        refused = {Path(str(r["path"])).name: r["reason"] for r in plan["refused"]}
        assert made == {"Fullseye Studio.lnk"} and str(ps1) in [i["path"] for i in plan["made"]]       # 起動が Fullseye の物だけ
        assert "fullseye.ico" in refused and shortcuts.CMD_NAME in refused and key.rsplit("\\", 1)[-1] in refused
        assert len(plan["refused"]) >= 3, plan["refused"]                                            # ico・cmd・キー・他人の lnk
        assert all(r["foreign"] for r in plan["refused"])                                             # 利用者の物の可能性 = 異常ではない
        assert not any(i["kind"] == "regkey" for i in plan["made"])
        rc, out, _ = _un(tmp_path, tmp_path / "none.json", dirs, ["--yes"], allow=(key,))
        assert rc == 0 and other.exists() and (dirs["icon_dir"] / "fullseye.ico").exists() and shortcuts.regkey_exists(key)
        assert not ps1.exists() and "NOT removed" in out and "does not start Fullseye Studio" in out
    finally:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
    # Fullseye が書いたキー(DisplayName / UninstallString)は確かめを通る
    shortcuts.register_uninstall_entry(Path("x.ico"), key, tmp_path / shortcuts.CMD_NAME)
    try:
        assert shortcuts.verify_fullseye_item("regkey", key) is None
    finally:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
    assert shortcuts.verify_fullseye_item("regkey", key) is None                                      # 無い物は問題なし(消す物が無い)


@winonly
def test_S1_remove_shortcuts_also_verifies_the_content(tmp_path):
    ledger = tmp_path / "ledger.json"
    dirs = _register(tmp_path, ledger, KEY + "S1r", desktop=True)
    lnk = dirs["desktop"] / "Fullseye Studio.lnk"
    lnk.unlink()
    shortcuts.write_lnk(lnk, Path(sys.executable), "-c print(1)", ROOT / "assets" / "fullseye.ico", tmp_path)   # 利用者が差し替えた
    skipped = []
    gone = shortcuts.remove(dirs=dirs, ledger=ledger, allow_keys=(KEY + "S1r",), skipped=skipped)
    assert lnk.exists() and lnk not in gone and any("does not start Fullseye Studio" in w for _p, w in skipped)
    assert not shortcuts.regkey_exists(KEY + "S1r")


@winonly
def test_S2_cmd_falls_back_on_a_negative_exit_code_such_as_a_missing_dll(tmp_path):
    """DLL が無い python は 0xC0000135(= -1073741515)で落ちる。`if errorlevel 1` はこれを見逃す。"""
    import winreg
    key = KEY + "S2"
    fake = tmp_path / "fakepy"
    fake.mkdir()
    base_py = Path(sys.base_prefix) / "python.exe"
    shutil.copyfile(base_py, fake / "python.exe")                          # python311.dll が隣に無い → DLL が見つからない
    sysroot = Path(os.environ["SystemRoot"])
    env = dict(os.environ, PATH=str(sysroot / "System32"), PYTHONUTF8="1", FS_NOPAUSE="1")
    probe = subprocess.run([str(fake / "python.exe"), "-I", "-c", "0"], capture_output=True, env=env)
    assert probe.returncode not in (0, 1), probe.returncode                # 前提: 0 でも 1 でもない(負の NTSTATUS)
    setup = tmp_path / "setup"
    setup.mkdir()
    lnk = tmp_path / "sm" / "Fullseye" / "Fullseye Studio.lnk"
    lnk.parent.mkdir(parents=True)
    lnk.write_bytes(b"x")
    uninst = tmp_path / "uninstall.py"
    uninst.write_text("print('SHOULD NOT RUN')\n", encoding="utf-8")
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE):
        pass
    script = setup / shortcuts.CMD_NAME
    text = shortcuts.uninstall_cmd_text(python=fake / "python.exe", uninstaller=uninst, lnks=[lnk], regkey=key)
    assert "if errorlevel" not in text and "if not errorlevel" not in text           # 終了コードの大小で分岐しない(0 かどうかだけ)
    script.write_text(text, encoding="utf-8", newline="")
    guard_script(script, tmp_path, key)
    try:
        r = subprocess.run('"%s"' % script, shell=True, capture_output=True, env=env, cwd=tmp_path)
        out = r.stdout.decode("utf-8", "replace")
        assert r.returncode == 0 and "SHOULD NOT RUN" not in out and "no longer there" in out, out + r.stderr.decode("utf-8", "replace")
        assert not lnk.exists() and not script.exists() and not shortcuts.regkey_exists(key)
    finally:
        if shortcuts.regkey_exists(key):
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)


def test_S3_skill_edited_fails_closed_and_sees_extra_files(tmp_path):
    mp = pytest.MonkeyPatch()          # 共有の monkeypatch を undo すると conftest の差し替えまで戻るので、専用の物を使う
    dest = rag_setup.install(tmp_path / "skills", backup=False)
    assert rag_setup.skill_edited(dest) is False
    (dest / "my_notes.md").write_text("mine", encoding="utf-8")                      # SKILL.md は無傷でも、足したファイルがあれば編集済み
    assert rag_setup.skill_edited(dest) is True
    (dest / "my_notes.md").unlink()
    (dest / "sub").mkdir()
    (dest / "sub" / "x.txt").write_text("x", encoding="utf-8")
    assert rag_setup.skill_edited(dest) is True
    shutil.rmtree(dest / "sub")
    assert rag_setup.skill_edited(dest) is False
    mp.setattr(rag_setup, "_skill_source", lambda repo: (_ for _ in ()).throw(SystemExit("template missing")))
    assert rag_setup.skill_edited(dest) is True                                      # 原本が見つからない = 判定できない → 編集済み扱い
    (dest / "SKILL.md").unlink()
    assert rag_setup.skill_edited(dest) is True                                      # SKILL.md が無い = 判定できない
    mp.undo()
    ledger = tmp_path / "ledger.json"
    dest2 = rag_setup.install(tmp_path / "skills2", backup=False)
    md = dest2 / "SKILL.md"
    md.write_text(md.read_text(encoding="utf-8") + "\nMY HAND NOTES\n", encoding="utf-8")
    mp.setattr(rag_setup, "_skill_source", lambda repo: (_ for _ in ()).throw(SystemExit("template missing")))
    _write_ledger(ledger, [{"kind": "claude_skill", "path": str(dest2)}])
    dirs = {"start_menu": tmp_path / "s", "desktop": tmp_path / "d", "icon_dir": tmp_path / "i", "apps": tmp_path / "a"}
    rc, out, _ = _un(tmp_path, ledger, dirs, ["--yes"])
    assert "MY HAND NOTES" in md.read_text(encoding="utf-8") and rc == 0                # 原本が無くても --yes で消えない
    mp.undo()


def test_S4_pip_start_failure_exits_3_and_ci_job_has_a_timeout(tmp_path):
    ledger = tmp_path / "ledger.json"
    dirs = _register(tmp_path, ledger, KEY + "S4")
    buf = io.StringIO()

    def boom():
        raise OSError("cannot start")
    rc = uninstall.main(["--uninstall", "--yes", "--lang", "en"], is_tty=False, out=buf, ledger=ledger, dirs=dirs,
                        env={"FULLSEYE_CACHE_DIR": str(tmp_path / "c")}, registry=False, allow_keys=(KEY + "S4",),
                        pip_fn=boom, pip_check_fn=lambda: ("ok", ""))
    assert rc == 3 and "Could not start pip uninstall" in buf.getvalue()
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    job = text.split("\n  windows-installer:\n", 1)[1].split("\n  # ", 1)[0].split("\n  lint:", 1)[0]
    assert "timeout-minutes: 15" in job


def test_S5_exit_code_table_lists_every_code():
    doc = uninstall.__doc__
    assert "終了コード" in doc and "0 =" in doc and "1 =" in doc and "3 =" in doc and "起動できず" in doc


# =========================================================================== 4 回目: コードページに無い文字のパス
UNICODE_NAMES = ["ユーザー 名's $env.X `y & ^ ! (1)", "ไทยภาษา", "עברית", "한글 Ж ü", "emoji \U0001F600"]


@winonly
@pytest.mark.parametrize("name", UNICODE_NAMES)
def test_E1_lnk_roundtrips_paths_outside_the_system_code_page(tmp_path, name):
    """英語の Windows の日本語のユーザー名(その逆も)でショートカットが作れなかった(WScript.Shell が ANSI で持つため ``????`` に化けた)。
    IShellLinkW(Unicode)で読み書きする。引用符・$・バッククォート・&・^・! を含むパスも式として解釈されない。"""
    d = tmp_path / name
    lnk = d / "Fullseye Studio.lnk"
    icon = d / "setup" / "fullseye.ico"
    shortcuts.write_lnk(lnk, Path(sys.executable), '-P -m studio "%s"' % name, icon, d)
    back = shortcuts.read_lnk(lnk)
    assert Path(back["Target"]) == Path(sys.executable)
    assert back["Arguments"] == '-P -m studio "%s"' % name
    assert back["WorkingDir"] == str(d) and back["Icon"].split(",")[0] == str(icon) and "?" not in back["WorkingDir"]
    assert d.is_dir() and lnk.is_file()


@winonly
def test_E1_the_powershell_fallback_still_works_for_ascii_paths(tmp_path):
    lnk = tmp_path / "f.lnk"
    shortcuts._write_lnk_via_powershell(lnk, Path(sys.executable), "-P -m studio", ROOT / "assets" / "fullseye.ico", tmp_path, "d")
    assert shortcuts._read_lnk_via_powershell(lnk)["Arguments"] == "-P -m studio"
    assert shortcuts.read_lnk(lnk)["Arguments"] == "-P -m studio"                  # COM の経路で、PowerShell が書いた物も読める


@winonly
def test_E1_the_old_wscript_path_really_was_broken_for_such_paths(tmp_path):
    """前提の確認(この試験が空を通していない): 従来の経路は、システムのコードページに無い文字のパスで壊れる。"""
    import locale
    name = "ไทยภาษา"
    try:
        name.encode(locale.getencoding())          # PYTHONUTF8 に左右されない、システムの ANSI コードページ
        pytest.skip("this machine's ANSI code page can represent the test characters")
    except UnicodeEncodeError:
        pass
    with pytest.raises(shortcuts.ShortcutError):
        shortcuts._write_lnk_via_powershell(tmp_path / name / "x.lnk", Path(sys.executable), "a", ROOT / "assets" / "fullseye.ico",
                                            tmp_path, "d")


@winonly
@pytest.mark.parametrize("name", UNICODE_NAMES[:3])
def test_E1_install_and_remove_work_with_such_a_setup_folder(tmp_path, name):
    root = tmp_path / name
    dirs = {"start_menu": root / "Programs" / "Fullseye", "desktop": root / "Desktop", "icon_dir": root / "local" / "setup"}
    ledger = root / "ledger.json"
    key = KEY + "E1"
    made = shortcuts.install(desktop=True, dirs=dirs, ledger=ledger, reg_key=key)
    assert len(made) == 2
    try:
        assert all(shortcuts.read_lnk(m)["WorkingDir"] == str(dirs["icon_dir"]) for m in made)
        gone = shortcuts.remove(dirs=dirs, ledger=ledger, allow_keys=(key,))
        assert len(gone) == 4 and not shortcuts.regkey_exists(key)
    finally:
        if shortcuts.regkey_exists(key):
            shortcuts.unregister_uninstall_entry(key, (key,))


# =========================================================================== どの OS でも通る部分(Windows だけの試験の Linux 側の受け皿)
def test_X1_content_verification_works_for_every_non_lnk_kind_on_any_os(tmp_path):
    """``.lnk`` / レジストリ以外(.ico / .png / .cmd / .desktop)の中身の確かめは OS に依らない。"""
    good = {"fullseye.ico": b"\x00\x00\x01\x00rest", "fullseye-studio.png": b"\x89PNG\r\n\x1a\nrest",
            shortcuts.CMD_NAME: b"@echo off\r\nrem Fullseye uninstall helper\r\n",
            "fullseye-studio.desktop": b"[Desktop Entry]\nName=Fullseye Studio\nExec=py -P -m studio\n"}
    assert len(good) == 4
    for name, data in good.items():
        (tmp_path / name).write_bytes(data)
        assert shortcuts.verify_fullseye_item("file", str(tmp_path / name)) is None, name
    for name in good:
        (tmp_path / name).write_bytes(b"something else entirely")
        why = shortcuts.verify_fullseye_item("file", str(tmp_path / name))
        assert why and "left alone" in why, (name, why)
    assert shortcuts.verify_fullseye_item("file", str(tmp_path / "absent.ico")) is None          # 無い物は消す物が無い
    notes = tmp_path / "notes.txt"
    notes.write_text("x", encoding="utf-8")
    assert "not a kind of file" in shortcuts.verify_fullseye_item("file", str(notes))


def test_X2_a_registry_row_in_a_ledger_does_not_crash_on_a_system_without_a_registry(tmp_path):
    """Linux で台帳に regkey の行があっても、uninstall も台帳の掃除も落ちない(winreg を import しない)。"""
    ledger = tmp_path / "ledger.json"
    _write_ledger(ledger, [{"kind": "regkey", "path": r"Software\Microsoft\Windows\CurrentVersion\Run"}])
    rc, out, _ = _un(tmp_path, ledger, _dirs(tmp_path), ["--yes"])
    assert rc == 1 and "NOT removed" in out
    assert shortcuts.regkey_exists(r"Software\Nope\x") is False
    shortcuts.ledger_gc(ledger)
    if not WIN:
        assert shortcuts.verify_fullseye_item("regkey", r"Software\Anything") is None
        with pytest.raises(shortcuts.ShortcutError):
            shortcuts.unregister_uninstall_entry(shortcuts.UNINSTALL_KEY)


def test_X3_unicode_paths_roundtrip_through_the_desktop_entry_on_any_os(tmp_path):
    """Linux 側: ``.desktop`` は UTF-8。コードページに依らない(Windows の .lnk の対になる確認)。"""
    for i, name in enumerate(("ユーザー 名 x", "ไทยภาษา", "עברית")):
        dirs = {"apps": tmp_path / name / "apps", "icon_dir": tmp_path / name / "icons", "desktop": tmp_path / name / "Desktop"}
        led = tmp_path / ("l%d.json" % i)
        made = shortcuts.install(platform="linux", python=sys.executable, dirs=dirs, ledger=led)
        assert len(made) == 1
        text = made[0].read_text(encoding="utf-8")
        icon_line = [l for l in text.splitlines() if l.startswith("Icon=")][0]
        assert name in icon_line and "?" not in icon_line
        assert shortcuts.verify_fullseye_item("file", str(made[0]), plat="linux") is None
        assert len(shortcuts.remove(platform="linux", dirs=dirs, ledger=led)) == 2


# =========================================================================== 5 回目のレビュー(2026-11-13)
def test_V1_remove_item_verifies_the_content_itself(tmp_path):
    """collect を通らずに remove_item が直接呼ばれても、名前と置き場が許可内でも中身が Fullseye の物でなければ消さない(二重の確かめ)。"""
    dirs = _dirs(tmp_path)
    folder = dirs["icon_dir"]
    folder.mkdir(parents=True)
    ico = folder / ("fullseye.ico" if WIN else "fullseye-studio.png")
    ico.write_bytes(b"not an image at all")
    with pytest.raises(shortcuts.ShortcutError, match="does not look like"):
        uninstall.remove_item({"kind": "file", "path": str(ico)}, dirs=dirs)
    assert ico.is_file()
    ico.write_bytes(b"\x00\x00\x01\x00ok" if WIN else b"\x89PNG\r\n\x1a\nok")
    assert uninstall.remove_item({"kind": "file", "path": str(ico)}, dirs=dirs) is True and not ico.exists()


@winonly
def test_V1_remove_item_refuses_a_registry_key_that_is_not_fullseyes(tmp_path):
    import winreg
    key = KEY + "V1"
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, "Somebody Else")
        winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ, "C:\\o\\u.exe")
    try:
        with pytest.raises(shortcuts.ShortcutError, match="not Fullseye"):
            uninstall.remove_item({"kind": "regkey", "path": key}, allow_keys=(key,))
        assert shortcuts.regkey_exists(key)
    finally:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)


@winonly
def test_V2_snapshot_tells_an_absent_setup_folder_from_an_empty_one(tmp_path, monkeypatch):
    from conftest import real_install_snapshot, snapshot_diff
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    before = real_install_snapshot()
    assert before["setup_folder"] is None
    (tmp_path / "Fullseye" / "setup").mkdir(parents=True)                 # 空で新しく作られた
    after = real_install_snapshot()
    assert after["setup_folder"] == [] and snapshot_diff(before, after) and "absent -> present" in snapshot_diff(before, after)[0]
    assert snapshot_diff(after, real_install_snapshot()) == []


@winonly
def test_V3_com_init_is_balanced_and_a_failed_enter_releases_the_shell_link(tmp_path, monkeypatch):
    import threading
    ole32 = __import__("ctypes").OleDLL("ole32")
    res = {}

    def work():
        ole32.CoInitializeEx(None, 2)                    # 呼び出し元が先に初期化している(count 1)
        shortcuts.write_lnk(tmp_path / "a.lnk", Path(sys.executable), "x", ROOT / "assets" / "fullseye.ico", tmp_path)
        __import__("ctypes").WinDLL("ole32").CoUninitialize()          # 呼び出し元の分だけ戻す
        try:                                             # 対が取れていれば、このスレッドは未初期化に戻っているので別の方式で初期化できる
            ole32.CoInitializeEx(None, 0)                # COINIT_MULTITHREADED
            res["balanced"] = True
            __import__("ctypes").WinDLL("ole32").CoUninitialize()
        except OSError:
            res["balanced"] = False
    th = threading.Thread(target=work)
    th.start()
    th.join()
    assert res["balanced"] is True
    releases = []
    orig = shortcuts._vt

    def counting(obj, index, *a, **kw):
        if index == 2:
            releases.append(1)
        return orig(obj, index, *a, **kw)
    monkeypatch.setattr(shortcuts, "_vt", counting)
    monkeypatch.setattr(shortcuts, "_IID_IPERSISTFILE", "{00000000-0000-0000-C000-000000000099}")      # QueryInterface が失敗する IID
    with pytest.raises(OSError):
        with shortcuts._ComLink():
            pass
    assert releases == [1]                               # ShellLink を 1 回 Release した(漏らさない)
