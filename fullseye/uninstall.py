# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``fullseye setup --uninstall`` — setup / ``--install-shortcuts`` が作った物を一式そろえて消す。

方針:

* **推測で消さない。** 消すのは台帳(``install_ledger.json``、``fullseye.shortcuts`` が登録時に書く)に載っている物だけ。
  台帳に無い物、ユーザーが後から置いた物には触らない。台帳が無い古い状態でも、既知の決まった場所のショートカット
  (Start Menu の Fullseye/Fullseye Studio.lnk、install.ps1 が作る Fullseye Studio.lnk、デスクトップの同名、Linux の
  .desktop)だけは検出して消せる。
* Studio の設定(QSettings / ``FULLSEYE_STUDIO_SETTINGS`` の ini)とキャッシュ(op_help-* / backend_probe.json*)は
  既定で**残す**。聞いて、y のときだけ消す。
* 最後に ``pip uninstall -y fullseye`` を実行するか聞く(実行するコマンドを先に見せる)。自分自身を消すので、Windows で
  実行中の exe がロックされて失敗しないよう、**このプロセスが終わるのを待つ別プロセス**で走らせ、結果をログに残す。
* ``--yes`` は設定・キャッシュを残して他は全部既定で実行、``--dry-run`` は並べるだけ、非端末は並べて終了コード 0。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from fullseye import shortcuts as sc
from fullseye.setup_cmd import detect_lang

M = {
    "ja": {
        "hdr": "== Fullseye アンインストール ==",
        "made": "[setup が作ったもの(台帳に記録済み)]",
        "legacy": "[台帳が無いので、既知の場所のショートカットだけ検出しました]",
        "data": "[Studio の設定とキャッシュ(既定は残す)]",
        "none": "  (見つかりません)",
        "noledger": "台帳(%s)が無く、既知の場所にも何もありません。",
        "q_made": "上の「作ったもの」を消しますか?",
        "q_settings": "Studio の設定を消しますか?(残すと次に入れ直したとき前回の状態が戻ります)",
        "q_cache": "キャッシュを消しますか?(再生成できます)",
        "q_pip": "最後に pip uninstall fullseye を実行しますか?",
        "cmd": "実行するコマンド:",
        "dry": "(--dry-run: 何も消していません)",
        "noninter": "標準入力が端末でないため何も消しません。消すには端末で fullseye setup --uninstall "
                    "(無人なら --yes)。",
        "bad": "もう一度入力してください(Enter で既定)",
        "done": "[消したもの]",
        "kept": "[残したもの]",
        "fail": "[消せなかったもの]",
        "pip_later": "pip uninstall は、この画面が閉じた直後に別プロセスで走ります(結果: %s)。",
        "pip_no": "pip uninstall は実行しません。後で: %s",
        "pip_fail": "pip uninstall を起動できませんでした: %s。手で実行してください: %s",
        "pause": "Enter で閉じます...",
        "r_file": "ファイル", "r_dir": "空フォルダ", "r_reg": "レジストリ(アプリと機能)", "r_skill": "Claude Code の skill",
        "r_ini": "設定ファイル", "r_regtree": "設定(レジストリ)", "r_cache": "キャッシュ",
    },
    "en": {
        "hdr": "== Fullseye uninstall ==",
        "made": "[What setup created (recorded in the ledger)]",
        "legacy": "[No ledger found, so only shortcuts in the well-known places were detected]",
        "data": "[Studio settings and cache (kept by default)]",
        "none": "  (nothing found)",
        "noledger": "There is no ledger (%s) and nothing in the well-known places.",
        "q_made": "Remove the items listed under 'created'?",
        "q_settings": "Delete the Studio settings? (if you keep them, a reinstall restores your last state)",
        "q_cache": "Delete the cache? (it is regenerated on demand)",
        "q_pip": "Finally run pip uninstall fullseye?",
        "cmd": "Command to run:",
        "dry": "(--dry-run: nothing was deleted)",
        "noninter": "stdin is not a terminal, so nothing is deleted. Run fullseye setup --uninstall in a terminal "
                    "(add --yes for unattended use).",
        "bad": "Please try again (Enter for the default)",
        "done": "[Removed]",
        "kept": "[Kept]",
        "fail": "[Could not remove]",
        "pip_later": "pip uninstall runs in a separate process right after this window closes (result: %s).",
        "pip_no": "Not running pip uninstall. Later: %s",
        "pip_fail": "Could not start pip uninstall: %s. Run it by hand: %s",
        "pause": "Press Enter to close...",
        "r_file": "file", "r_dir": "empty folder", "r_reg": "registry ('Apps & features')", "r_skill": "Claude Code skill",
        "r_ini": "settings file", "r_regtree": "settings (registry)", "r_cache": "cache",
    },
}
_LABEL = {"file": "r_file", "dir_if_empty": "r_dir", "regkey": "r_reg", "claude_skill": "r_skill",
          "settings_ini": "r_ini", "settings_regtree": "r_regtree", "cache": "r_cache"}
_ORDER = ["file", "settings_ini", "claude_skill", "regkey", "settings_regtree", "cache", "dir_if_empty"]
SETTINGS_REGTREE = r"Software\Fullseye\Studio"
CACHE_PATTERNS = ("op_help-*", "backend_probe.json*", "studio_crash.log")


# --------------------------------------------------------------------------- 何を消すかの一覧
def cache_base(env: Optional[Dict[str, str]] = None) -> Path:
    """helpstore と同じ決め方(FULLSEYE_CACHE_DIR → %LOCALAPPDATA%/fullseye → ~/.cache/fullseye)。"""
    e = os.environ if env is None else env
    if e.get("FULLSEYE_CACHE_DIR"):
        return Path(e["FULLSEYE_CACHE_DIR"])
    if e.get("LOCALAPPDATA"):
        return Path(e["LOCALAPPDATA"]) / "fullseye"
    return Path.home() / ".cache" / "fullseye"


def _legacy_places(plat: str, dirs: Optional[Dict[str, Path]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if plat == "win":
        d = dict(sc.windows_dirs())
        d.update(dirs or {})
        prog = d["start_menu"].parent                      # .../Programs
        cands = [d["start_menu"] / (sc.APP_NAME + ".lnk"), prog / (sc.APP_NAME + ".lnk"),
                 d["desktop"] / (sc.APP_NAME + ".lnk")]
    elif plat == "linux":
        d = sc._linux_dirs(dirs)
        cands = [d["apps"] / "fullseye-studio.desktop", d["desktop"] / "fullseye-studio.desktop",
                 d["icon_dir"] / "fullseye-studio.png"]
    else:
        return out
    for p in cands:
        if p.is_file():
            out.append({"kind": "file", "path": str(p)})
    return out


def collect(*, ledger: Optional[Path] = None, dirs: Optional[Dict[str, Path]] = None,
            env: Optional[Dict[str, str]] = None, plat: Optional[str] = None,
            registry: bool = True) -> Dict[str, object]:
    """{"made": [...], "data": [...], "legacy": bool, "ledger": Path}。何も変更しない。"""
    plat = plat or sc._platform()
    lp = ledger or sc.ledger_path()
    ents = sc.ledger_load(lp)
    legacy = ents is None
    made = list(_legacy_places(plat, dirs)) if legacy else [dict(e) for e in ents]
    # 設定とキャッシュ(Studio / helpstore が作る物。setup は作らないので台帳には載らない = 既定で残す)
    data: List[Dict[str, str]] = []
    e = os.environ if env is None else env
    ini = e.get("FULLSEYE_STUDIO_SETTINGS", "")
    if ini and Path(ini).is_file():
        data.append({"kind": "settings_ini", "path": ini})
    if registry and plat == "win" and sc.regkey_exists(SETTINGS_REGTREE):
        data.append({"kind": "settings_regtree", "path": SETTINGS_REGTREE})
    if plat == "linux":
        conf = Path(e.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "Fullseye" / "Studio.conf"
        if conf.is_file():
            data.append({"kind": "settings_ini", "path": str(conf)})
    cb = cache_base(env)
    if cb.is_dir() and any(True for pat in CACHE_PATTERNS for _ in cb.glob(pat)):
        data.append({"kind": "cache", "path": str(cb)})
    if legacy and plat == "win":
        sm = dict(sc.windows_dirs())
        sm.update(dirs or {})
        if made and sm["start_menu"].is_dir():
            made.append({"kind": "dir_if_empty", "path": str(sm["start_menu"])})
    made.sort(key=lambda x: _ORDER.index(x["kind"]))
    return {"made": made, "data": data, "legacy": legacy, "ledger": lp}


# --------------------------------------------------------------------------- 削除の実行
def _reg_delete_tree(key: str) -> bool:
    import winreg
    low = key.lower()
    if low != SETTINGS_REGTREE.lower():
        raise sc.ShortcutError("refusing to delete registry tree %s" % key)

    def rec(parent, name):
        try:
            k = winreg.OpenKey(parent, name, 0, winreg.KEY_ALL_ACCESS)
        except FileNotFoundError:
            return False
        with k:
            while True:
                try:
                    sub = winreg.EnumKey(k, 0)
                except OSError:
                    break
                rec(k, sub)
        winreg.DeleteKey(parent, name)
        return True
    ok = rec(winreg.HKEY_CURRENT_USER, key)
    try:                                       # 親 HKCU\Software\Fullseye は空になったときだけ
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Fullseye")
    except OSError:
        pass
    return ok


def remove_item(it: Dict[str, str]) -> bool:
    """1 項目を消す。消した(または既に無い)なら True。失敗は例外。"""
    kind, path = it["kind"], it["path"]
    if kind == "file":
        p = Path(path)
        if p.is_file():
            p.unlink()
        return True
    if kind == "settings_ini":
        p = Path(path)
        if p.is_file():
            p.unlink()
        return True
    if kind == "dir_if_empty":
        try:
            Path(path).rmdir()
        except OSError:
            pass
        return True
    if kind == "regkey":
        sc.unregister_uninstall_entry(path)
        return True
    if kind == "settings_regtree":
        _reg_delete_tree(path)
        return True
    if kind == "claude_skill":
        from fullseye import rag_setup
        p = Path(path)
        if p.name != rag_setup.SKILL_NAME:
            raise sc.ShortcutError("ledger skill path %s is not a %s directory; left alone" % (p, rag_setup.SKILL_NAME))
        rag_setup.uninstall(p.parent)
        return True
    if kind == "cache":
        base = Path(path)
        for pat in CACHE_PATTERNS:
            for child in base.glob(pat):
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                elif child.is_file():
                    child.unlink()
        try:
            base.rmdir()
        except OSError:
            pass
        return True
    raise sc.ShortcutError("unknown item kind %r" % kind)


# --------------------------------------------------------------------------- pip uninstall(別プロセス)
_HELPER = (
    "import os, sys, time, subprocess\n"
    "pid, log = int(sys.argv[1]), sys.argv[2]\n"
    "cmd = sys.argv[3:]\n"
    "def alive(p):\n"
    "    if sys.platform == 'win32':\n"
    "        import ctypes\n"
    "        h = ctypes.windll.kernel32.OpenProcess(0x00100000, False, p)\n"
    "        if not h:\n"
    "            return False\n"
    "        r = ctypes.windll.kernel32.WaitForSingleObject(h, 0)\n"
    "        ctypes.windll.kernel32.CloseHandle(h)\n"
    "        return r == 258\n"
    "    try:\n"
    "        os.kill(p, 0)\n"
    "        return True\n"
    "    except OSError:\n"
    "        return False\n"
    "for _ in range(120):\n"
    "    if not alive(pid):\n"
    "        break\n"
    "    time.sleep(0.25)\n"
    "time.sleep(1.5)\n"
    "out = ''\n"
    "for attempt in range(3):\n"
    "    r = subprocess.run(cmd, capture_output=True, text=True)\n"
    "    out += 'attempt %d exit=%d\\n%s%s\\n' % (attempt + 1, r.returncode, r.stdout, r.stderr)\n"
    "    if r.returncode == 0:\n"
    "        break\n"
    "    time.sleep(2)\n"
    "open(log, 'w', encoding='utf-8').write(out)\n"
)


def pip_uninstall_command() -> List[str]:
    return [sys.executable, "-m", "pip", "uninstall", "-y", "fullseye"]


def spawn_pip_uninstall() -> str:
    """このプロセスの終了を待ってから pip uninstall を走らせる別プロセスを起こし、ログのパスを返す。"""
    log = os.path.join(tempfile.gettempdir(), "fullseye_uninstall.log")
    try:
        os.unlink(log)
    except OSError:
        pass
    kw: Dict[str, object] = {}
    if sys.platform == "win32":
        kw["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000       # DETACHED | NEW_GROUP | NO_WINDOW
    else:
        kw["start_new_session"] = True
    subprocess.Popen([sys.executable, "-I", "-c", _HELPER, str(os.getpid()), log, *pip_uninstall_command()],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     cwd=tempfile.gettempdir(), **kw)
    return log


# --------------------------------------------------------------------------- 本体
def main(argv: Optional[Sequence[str]] = None, *, input_fn: Optional[Callable[[str], str]] = None,
         pip_fn: Optional[Callable[[], str]] = None, is_tty: Optional[bool] = None, out=None,
         ledger: Optional[Path] = None, dirs: Optional[Dict[str, Path]] = None,
         env: Optional[Dict[str, str]] = None, registry: bool = True) -> int:
    ap = argparse.ArgumentParser(prog="fullseye setup --uninstall", description="Uninstall what fullseye setup created.")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--lang", choices=["ja", "en"], default=None)
    ap.add_argument("--yes", "-y", action="store_true", help="remove everything created by setup, keep settings/cache, run pip uninstall")
    ap.add_argument("--dry-run", "-n", action="store_true", help="list only; delete nothing")
    ap.add_argument("--pause", action="store_true", help="wait for Enter before closing (used by 'Apps & features')")
    args = ap.parse_args(list(sys.argv[1:] if argv is None else argv))
    out = out or sys.stdout
    try:
        out.reconfigure(errors="replace")
    except Exception:       # noqa: BLE001
        pass
    lang = detect_lang(override=args.lang)
    m = M[lang]
    input_fn = input_fn or input
    pip_fn = pip_fn or spawn_pip_uninstall
    if is_tty is None:
        from fullseye.setup_cmd import _stdin_is_terminal
        try:
            is_tty = _stdin_is_terminal()
        except Exception:       # noqa: BLE001
            is_tty = False

    def say(s: str = "") -> None:
        print(s, file=out)

    def show(items: List[Dict[str, str]]) -> None:
        for it in items:
            say("  - %-26s %s" % (m[_LABEL[it["kind"]]], it["path"]))

    plan = collect(ledger=ledger, dirs=dirs, env=env, registry=registry)
    made, data = plan["made"], plan["data"]
    say(m["hdr"])
    say()
    say(m["legacy"] if plan["legacy"] else m["made"])
    if made:
        show(made)
    else:
        say(m["noledger"] % plan["ledger"] if plan["legacy"] else m["none"])
    say()
    say(m["data"])
    show(data) if data else say(m["none"])
    say()
    cmd = pip_uninstall_command()
    cmd_txt = " ".join('"%s"' % c if " " in c else c for c in cmd)
    say(m["cmd"] + "  " + cmd_txt)
    say()

    auto = args.yes or args.dry_run
    if args.dry_run:
        say(m["dry"])
        return 0
    if not is_tty and not auto:
        say(m["noninter"])
        return 0
    interactive = is_tty and not args.yes

    def yn(q: str, default: bool) -> bool:
        if not interactive:
            say("%s  -> %s" % (q, "Y" if default else "N"))
            return default
        for _ in range(3):
            try:
                a = input_fn("%s (%s) " % (q, "Y/n" if default else "y/N")).strip().lower()
            except EOFError:
                return default
            if not a:
                return default
            if a in ("y", "yes", "はい"):
                return True
            if a in ("n", "no", "いいえ"):
                return False
            say(m["bad"])
        return default

    do = {"made": bool(made) and yn(m["q_made"], True)}
    do["settings"] = any(x["kind"] != "cache" for x in data) and yn(m["q_settings"], False)
    do["cache"] = any(x["kind"] == "cache" for x in data) and yn(m["q_cache"], False)
    do["pip"] = yn(m["q_pip"], True)

    removed: List[Dict[str, str]] = []
    failed: List[str] = []
    todo = (made if do["made"] else []) + [x for x in data if (x["kind"] == "cache" and do["cache"])
                                          or (x["kind"] != "cache" and do["settings"])]
    todo.sort(key=lambda x: _ORDER.index(x["kind"]))
    for it in todo:
        try:
            remove_item(it)
            removed.append(it)
        except Exception as e:      # noqa: BLE001 — 1 項目の失敗で全体を止めない
            failed.append("%s: %s" % (it["path"], e))
    if do["made"]:                  # 台帳に載っていた物を消し終えたら台帳も畳む
        sc.ledger_gc(plan["ledger"])
        if plan["ledger"].is_file():
            remaining = sc.ledger_load(plan["ledger"]) or []
            if not remaining:
                plan["ledger"].unlink()
        try:
            plan["ledger"].parent.rmdir()
        except OSError:
            pass
    if do["cache"]:
        try:
            cache_base(env).rmdir()         # setup/ を畳んだ後なので、空になっていれば消える
        except OSError:
            pass
    kept = [x for x in made + data if x not in removed]
    say(m["done"])
    show(removed) if removed else say(m["none"])
    if failed:
        say()
        say(m["fail"])
        for f in failed:
            say("  - " + f)
    if kept:
        say()
        say(m["kept"])
        show(kept)
    say()
    if do["pip"]:
        try:
            log = pip_fn()
            say(m["pip_later"] % log)
        except Exception as e:      # noqa: BLE001
            say(m["pip_fail"] % (e, cmd_txt))
    else:
        say(m["pip_no"] % cmd_txt)
    if args.pause and is_tty:
        try:
            input_fn(m["pause"])
        except EOFError:
            pass
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
