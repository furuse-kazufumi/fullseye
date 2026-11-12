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
* 台帳は書き換えられる JSON なので、中身を**許可制**で検証する(消してよい名前と置き場だけ。``shortcuts.check_ledger_item``)。
  許可外・別の Python 環境が作った物は消さずに「消さなかったもの」として表示する。壊れた台帳は警告して「台帳なし」に倒す。
* pip の段は、この Python に pip があり、入っている fullseye が動いている物と同じ場所のときだけ出す。
* **終了コード**: 0 = やると決めた物を全部消した(pip の段も、出す必要がある場合は起動した)/ ``--dry-run``・非端末で何もしていない /
  pip の段が要らない(この Python に fullseye が pip で入っていない、または別の場所のもの)。
  1 = 消せなかった項目がある、または台帳に許可外の項目があった(書き換えられた台帳)。
  3 = 登録は消したが、pip の段を出せず(pip の無い uv の venv など)、または pip の段を起動できず、fullseye 本体がこの Python に残っている
  (案内したコマンドを手で実行)。
* ``python -I fullseye/uninstall.py`` でパッケージ本体(__init__ = numpy / scipy を読む)を通さずに単独実行できる
  (setup フォルダの fullseye-uninstall.cmd がこれを呼ぶ)。
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

if __name__ == "__main__" and "fullseye" not in sys.modules:
    # 単独実行(python -I .../fullseye/uninstall.py): パッケージ本体の __init__(numpy / scipy などを読む)を通さない。
    # scipy が壊れた環境でも後始末できるよう、中身の無い "fullseye" パッケージを先に据えて、サブモジュールだけ読む。
    _HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path[:] = [_p for _p in sys.path if os.path.abspath(_p or os.getcwd()) != _HERE]   # fullseye/mcp 等が標準名を隠さない
    import types as _types
    _stub = _types.ModuleType("fullseye")
    _stub.__path__ = [_HERE]
    sys.modules["fullseye"] = _stub

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
        "badledger": "警告: 台帳を読めませんでした(%s)。台帳なしとして、既知の場所のショートカットだけを検出します。",
        "refused": "[台帳にあるが消さなかったもの]",
        "pip_nopip": "この Python には pip がありません(uv の venv など)。pip uninstall の段は飛ばします(fullseye 本体はまだ入っています)。"
                     "手で実行してください: %s",
        "pip_other": "pip uninstall の段は出しません: この Python に入っている fullseye は、いま動いている物と別の場所です(%s)。",
        "err": "エラー: %s",
        "pip_none": "pip uninstall の段は出しません: この Python に fullseye は pip で入っていません(%s)。",
        "later": "[この画面が閉じた直後に、後始末スクリプトが消すもの]",
        "q_skill": "Claude Code の skill(%s)も消しますか?",
        "skill_edited": "注意: %s の SKILL.md は同梱の原本から手で編集されています。既定では残します(消すと編集は戻せません)。",
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
        "badledger": "warning: the ledger could not be read (%s). Treating it as absent: only shortcuts in the well-known places are detected.",
        "refused": "[In the ledger but NOT removed]",
        "pip_nopip": "This Python has no pip (a uv venv, for example), so the pip uninstall step is skipped (fullseye itself is still "
                     "installed). Run by hand: %s",
        "pip_other": "Not offering pip uninstall: the fullseye installed in this Python is in a different place from the one "
                     "running now (%s).",
        "err": "error: %s",
        "pip_none": "Not offering pip uninstall: fullseye is not pip-installed in this Python (%s).",
        "later": "[Removed by the cleanup script right after this window closes]",
        "q_skill": "Also remove the Claude Code skill (%s)?",
        "skill_edited": "note: the SKILL.md in %s has been edited by hand relative to the shipped original. Kept by default (removing it cannot be undone).",
        "r_file": "file", "r_dir": "empty folder", "r_reg": "registry ('Apps & features')", "r_skill": "Claude Code skill",
        "r_ini": "settings file", "r_regtree": "settings (registry)", "r_cache": "cache",
    },
}
_LABEL = {"file": "r_file", "dir_if_empty": "r_dir", "regkey": "r_reg", "claude_skill": "r_skill",
          "settings_ini": "r_ini", "settings_regtree": "r_regtree", "cache": "r_cache"}
_ORDER = ["file", "settings_ini", "claude_skill", "regkey", "settings_regtree", "cache", "dir_if_empty"]
SETTINGS_REGTREE = r"Software\Fullseye\Studio"
CACHE_PATTERNS = ("op_help-*", "backend_probe.json*", "studio_crash.log")
_SETTINGS_SUFFIXES = (".ini", ".conf")       # FULLSEYE_STUDIO_SETTINGS が別の種類のファイルを指していても消さない


# --------------------------------------------------------------------------- 何を消すかの一覧
def cache_base(env: Optional[Dict[str, str]] = None) -> Path:
    """helpstore と同じ決め方(FULLSEYE_CACHE_DIR → %LOCALAPPDATA%/fullseye → ~/.cache/fullseye)。"""
    e = os.environ if env is None else env
    if e.get("FULLSEYE_CACHE_DIR"):
        return Path(e["FULLSEYE_CACHE_DIR"])
    if e.get("LOCALAPPDATA"):
        return Path(e["LOCALAPPDATA"]) / "fullseye"
    return Path.home() / ".cache" / "fullseye"


def _legacy_places(plat: str, dirs: Optional[Dict[str, Path]], registry: bool = True,
                   allow_keys: Iterable[str] = ()) -> List[Dict[str, str]]:
    """台帳が無い / 壊れているときの既知の場所(**固定の名前だけ**): ショートカット、setup フォルダのアイコンと後始末スクリプト、
    Uninstall\\Fullseye キー(完全一致。``allow_keys`` に挙がった試験用キーも在れば)。"""
    out: List[Dict[str, str]] = []
    keys: List[str] = []
    if plat == "win":
        d = dict(sc.windows_dirs())
        d.update(dirs or {})
        prog = d["start_menu"].parent                      # .../Programs
        cands = [d["start_menu"] / (sc.APP_NAME + ".lnk"), prog / (sc.APP_NAME + ".lnk"),
                 d["desktop"] / (sc.APP_NAME + ".lnk"), d["icon_dir"] / "fullseye.ico", d["icon_dir"] / sc.CMD_NAME]
        keys = [k for k in (([sc.UNINSTALL_KEY] if registry else []) + list(allow_keys)) if sc.regkey_exists(k)]
    elif plat == "linux":
        d = sc._linux_dirs(dirs)
        cands = [d["apps"] / "fullseye-studio.desktop", d["desktop"] / "fullseye-studio.desktop",
                 d["icon_dir"] / "fullseye-studio.png"]
    else:
        return out
    for p in cands:
        if p.is_file():
            out.append({"kind": "file", "path": str(p)})
    for k in dict.fromkeys(keys):
        out.append({"kind": "regkey", "path": k})
    return out


def collect(*, ledger: Optional[Path] = None, dirs: Optional[Dict[str, Path]] = None,
            env: Optional[Dict[str, str]] = None, plat: Optional[str] = None,
            registry: bool = True, allow_keys: Iterable[str] = (),
            regtree: str = SETTINGS_REGTREE) -> Dict[str, object]:
    """{"made": [...], "data": [...], "refused": [...], "legacy": bool, "ledger": Path, "warning": str|None}。
    何も変更しない。台帳の項目は検証し、許可外・別環境の物は ``refused`` へ(理由つき)。"""
    plat = plat or sc._platform()
    lp = ledger or sc.ledger_path()
    ents, warning = sc.ledger_load_safe(lp)
    legacy = ents is None
    refused: List[Dict[str, object]] = []
    made = []
    if legacy:
        for e in _legacy_places(plat, dirs, registry, tuple(allow_keys)):
            why = sc.verify_fullseye_item(e["kind"], e["path"], plat=plat)       # 名前だけで消さない: Fullseye の物と中身で確かめる
            if why:
                refused.append({"kind": e["kind"], "path": e["path"], "reason": why, "foreign": True})   # 利用者の物の可能性 = 異常ではない
            else:
                made.append(e)
    else:
        for e in ents:
            why = sc.check_ledger_item(e["kind"], e["path"], plat=plat, dirs=dirs, allow_keys=allow_keys)
            foreign = sc.entry_foreign(e) if why is None else None
            if foreign:
                why = "created by another Python environment (%s); left alone" % foreign
            if why is None:
                why = sc.verify_fullseye_item(e["kind"], e["path"], plat=plat)
            if why:
                refused.append({"kind": e["kind"], "path": e["path"], "reason": why, "foreign": bool(foreign)})
            else:
                made.append(dict(e))
    # 設定とキャッシュ(Studio / helpstore が作る物。setup は作らないので台帳には載らない = 既定で残す)
    data: List[Dict[str, str]] = []
    e = os.environ if env is None else env
    ini = e.get("FULLSEYE_STUDIO_SETTINGS", "")
    if ini and Path(ini).is_file() and Path(ini).suffix.lower() in _SETTINGS_SUFFIXES:
        data.append({"kind": "settings_ini", "path": ini})
    if registry and plat == "win" and sc.regkey_exists(regtree):
        data.append({"kind": "settings_regtree", "path": regtree})
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
        if made:
            for folder in (sm["start_menu"], sm["icon_dir"]):
                if folder.is_dir():
                    made.append({"kind": "dir_if_empty", "path": str(folder)})
    made.sort(key=lambda x: _ORDER.index(x["kind"]))
    return {"made": made, "data": data, "refused": refused, "legacy": legacy, "ledger": lp, "warning": warning}


# --------------------------------------------------------------------------- 削除の実行
def _reg_delete_tree(key: str, allow_keys: Iterable[str] = ()) -> bool:
    """HKCU の設定の木を消す。許すのは Studio の設定(SETTINGS_REGTREE)と、引数で明示された物だけ。"""
    import winreg
    k_norm = key.replace("/", "\\").strip("\\").lower()
    if k_norm != SETTINGS_REGTREE.lower() and k_norm not in {a.replace("/", "\\").strip("\\").lower() for a in allow_keys}:
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
    parent = key.replace("/", "\\").strip("\\").rpartition("\\")[0]
    if parent.lower().startswith("software\\fullseye"):          # 親(既定は HKCU\Software\Fullseye)は空になったときだけ
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, parent)
        except OSError:
            pass
    return ok


def remove_item(it: Dict[str, str], *, dirs: Optional[Dict[str, Path]] = None,
                allow_keys: Iterable[str] = ()) -> bool:
    """1 項目を消す。消した(または既に無い)なら True。残った(空でない dir_if_empty)なら False。失敗(許可外を含む)は例外。

    台帳由来の種類(file / dir_if_empty / regkey / claude_skill)は、ここでもう一度許可制で検証する(多重防御)。"""
    kind, path = it["kind"], it["path"]
    if kind in ("file", "dir_if_empty", "regkey", "claude_skill"):
        why = sc.check_ledger_item(kind, path, dirs=dirs, allow_keys=allow_keys) or sc.verify_fullseye_item(kind, path)
        if why:
            raise sc.ShortcutError(why)
    if kind == "file":
        p = Path(path)
        if p.is_file():
            p.unlink()
        return True
    if kind == "settings_ini":
        p = Path(path)
        if p.suffix.lower() not in _SETTINGS_SUFFIXES:
            raise sc.ShortcutError("%s is not a .ini / .conf settings file; left alone" % p)
        if p.is_file():
            p.unlink()
        return True
    if kind == "dir_if_empty":
        try:
            Path(path).rmdir()
        except OSError:
            pass
        return not Path(path).exists()          # 空でなくて畳めなかったときは False(「消した」と言わない)
    if kind == "regkey":
        sc.unregister_uninstall_entry(path, allow_keys)
        return True
    if kind == "settings_regtree":
        _reg_delete_tree(path, allow_keys)
        return True
    if kind == "claude_skill":
        from fullseye import rag_setup
        p = Path(path)
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


def _find_dist():
    """fullseye の配布物を探す。``-I`` の単独実行は利用者の site-packages(``pip install --user``)を外すので、そこも探す。"""
    try:
        return importlib.metadata.distribution("fullseye")
    except importlib.metadata.PackageNotFoundError:
        pass
    try:
        import site
        for d in importlib.metadata.distributions(name="fullseye", path=[site.getusersitepackages()]):
            return d
    except Exception:       # noqa: BLE001 — 探せなければ「無い」として扱う
        pass
    return None


def dist_location_matches(pkg_dir: Optional[Path] = None) -> Tuple[Optional[bool], str]:
    """この Python に入っている fullseye(配布物)が、いま動いているパッケージと同じ場所か。

    違えば pip uninstall は**別の** fullseye を消してしまう(checkout から ``imgevolve.py setup --uninstall`` を
    走らせたとき、その Python に別の fullseye が入っている場合)。editable は direct_url.json の場所で見る。
    戻り値は (True 一致 / False 別の場所 / None 配布物が見つからない, 説明)。"""
    pkg = Path(pkg_dir or Path(__file__).resolve().parent).resolve()
    dist = _find_dist()
    if dist is None:
        return None, "no fullseye distribution is installed in this Python"
    try:
        loc = Path(dist.locate_file("fullseye")).resolve()
    except (OSError, ValueError):
        loc = None
    if loc is not None and loc == pkg:
        return True, str(loc)
    try:
        du = json.loads(dist.read_text("direct_url.json") or "null")
        url = du.get("url", "") if isinstance(du, dict) else ""
        if isinstance(du, dict) and (du.get("dir_info") or {}).get("editable") and url.startswith("file:"):
            from urllib.parse import urlparse
            from urllib.request import url2pathname
            if Path(url2pathname(urlparse(url).path)).resolve() == pkg.parent:
                return True, str(pkg.parent)
    except (OSError, ValueError, AttributeError):
        pass
    return False, "installed: %s / running: %s" % (loc, pkg)


def pip_status(python: Optional[str] = None, pkg_dir: Optional[Path] = None) -> Tuple[str, str]:
    """pip の段を出してよいか: ("ok", "") / ("no_pip", "") / ("none", 説明: pip で入っていない) / ("other", 説明: 別の場所)。

    pip の無い環境(uv の venv)では、登録を消した後に別プロセスの pip uninstall が黙って失敗し、ログが %TEMP% に
    残るだけになる。先に ``-m pip --version`` で確かめて、無ければ段ごと飛ばす。"""
    py = python or sys.executable
    try:
        r = subprocess.run([py, "-I", "-m", "pip", "--version"], capture_output=True, text=True, timeout=60,
                           stdin=subprocess.DEVNULL, cwd=tempfile.gettempdir())
        has_pip = r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        has_pip = False
    if not has_pip:
        return "no_pip", ""
    ok, where = dist_location_matches(pkg_dir)
    if ok is None:
        return "none", where
    return ("ok", "") if ok else ("other", where)


def uv_uninstall_hint() -> str:
    return 'uv pip uninstall --python "%s" fullseye' % sys.executable


def spawn_pip_uninstall() -> str:
    """このプロセスの終了を待ってから pip uninstall を走らせる別プロセスを起こし、ログのパスを返す。"""
    log = os.path.join(tempfile.gettempdir(), "fullseye_uninstall.log")
    try:
        os.unlink(log)
    except OSError:
        pass
    argv = [sys.executable, "-I", "-c", _HELPER, str(os.getpid()), log, *pip_uninstall_command()]
    kw: Dict[str, object] = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 cwd=tempfile.gettempdir())
    if sys.platform == "win32":
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP。CREATE_NO_WINDOW は DETACHED_PROCESS と併用すると無視されるので付けない。
        # CREATE_BREAKAWAY_FROM_JOB: 端末を閉じたとき Job ごと止められないため。Job が許さないと OSError なので外して再試行。
        base = 0x00000008 | 0x00000200
        try:
            subprocess.Popen(argv, creationflags=base | 0x01000000, **kw)
        except OSError:
            subprocess.Popen(argv, creationflags=base, **kw)
    else:
        subprocess.Popen(argv, start_new_session=True, **kw)
    return log


# --------------------------------------------------------------------------- 本体
def main(argv: Optional[Sequence[str]] = None, *, input_fn: Optional[Callable[[str], str]] = None,
         pip_fn: Optional[Callable[[], str]] = None, is_tty: Optional[bool] = None, out=None,
         ledger: Optional[Path] = None, dirs: Optional[Dict[str, Path]] = None,
         env: Optional[Dict[str, str]] = None, registry: bool = True, allow_keys: Iterable[str] = (),
         regtree: str = SETTINGS_REGTREE,
         pip_check_fn: Optional[Callable[[], Tuple[str, str]]] = None) -> int:
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
    allow_keys = tuple(allow_keys)
    input_fn = input_fn or input
    pip_fn = pip_fn or spawn_pip_uninstall
    pip_check_fn = pip_check_fn or pip_status
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

    try:
        plan = collect(ledger=ledger, dirs=dirs, env=env, registry=registry, allow_keys=allow_keys, regtree=regtree)
    except sc.ShortcutError as e:
        say(m["err"] % e)
        return 1
    made, data, refused = plan["made"], plan["data"], plan["refused"]
    say(m["hdr"])
    say()
    if plan["warning"]:
        say(m["badledger"] % plan["warning"])
        say()
    say(m["legacy"] if plan["legacy"] else m["made"])
    if made:
        show(made)
    else:
        say(m["noledger"] % plan["ledger"] if plan["legacy"] else m["none"])
    if refused:
        say()
        say(m["refused"])
        for r in refused:
            say("  - %-26s %s" % (m[_LABEL[r["kind"]]], r["path"]))
            say("      %s" % r["reason"])
    say()
    say(m["data"])
    show(data) if data else say(m["none"])
    say()
    cmd = pip_uninstall_command()
    cmd_txt = " ".join('"%s"' % c if " " in c else c for c in cmd)
    pstate, pdetail = pip_check_fn()
    if pstate == "ok":
        say(m["cmd"] + "  " + cmd_txt)
    elif pstate == "no_pip":
        say(m["pip_nopip"] % uv_uninstall_hint())
    else:
        say((m["pip_none"] if pstate == "none" else m["pip_other"]) % pdetail)
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

    skills = [x for x in made if x["kind"] == "claude_skill"]
    others = [x for x in made if x["kind"] != "claude_skill"]
    do = {"made": bool(others) and yn(m["q_made"], True)}
    do["skill"] = False
    for s in skills:                        # skill は手編集を含みうるので別の問い(編集済みなら既定は残す)
        edited = False
        try:
            from fullseye import rag_setup
            edited = rag_setup.skill_edited(Path(s["path"]))
        except Exception:       # noqa: BLE001 — 判定できなければ「編集済みでない」とせず、確認に倒す
            edited = True
        if edited:
            say(m["skill_edited"] % s["path"])
        s["_ok"] = yn(m["q_skill"] % s["path"], not edited)
        do["skill"] = do["skill"] or bool(s["_ok"])
    do["settings"] = any(x["kind"] != "cache" for x in data) and yn(m["q_settings"], False)
    do["cache"] = any(x["kind"] == "cache" for x in data) and yn(m["q_cache"], False)
    do["pip"] = pstate == "ok" and yn(m["q_pip"], True)

    removed: List[Dict[str, str]] = []
    failed: List[str] = []
    todo = (others if do["made"] else []) + [x for x in skills if x.get("_ok")] + [x for x in data if (x["kind"] == "cache" and do["cache"])
                                          or (x["kind"] != "cache" and do["settings"])]
    todo.sort(key=lambda x: _ORDER.index(x["kind"]))
    deferred: List[Dict[str, str]] = []
    later: List[Dict[str, str]] = []
    if os.environ.get(sc.UNINSTALL_FROM_CMD_ENV) == "1":
        # 後始末スクリプト(.cmd)から呼ばれた: 走行中の .cmd はここで消さない(消えると cmd がエラーを出す)。
        # 台帳から外すだけにして、消すのは Python が終わった後の .cmd 自身。
        deferred = [x for x in todo if x["kind"] == "file"
                    and os.path.normcase(Path(x["path"]).name) == os.path.normcase(sc.CMD_NAME)]
        todo = [x for x in todo if x not in deferred]
    deferred_dirs = {os.path.normcase(os.path.normpath(str(Path(x["path"]).parent))) for x in deferred}
    for it in todo:
        try:
            if remove_item(it, dirs=dirs, allow_keys=allow_keys + (regtree,)) is False:
                if it["kind"] == "dir_if_empty" and os.path.normcase(os.path.normpath(it["path"])) in deferred_dirs:
                    later.append(it)        # 走行中の後始末スクリプトが入っている: スクリプトが終わってから消える
                continue                    # 消えなかった = 「残したもの」(下の kept に出る)
            removed.append(it)
        except Exception as e:      # noqa: BLE001 — 1 項目の失敗で全体を止めない
            failed.append("%s: %s" % (it["path"], e))
    for it in deferred:
        sc.ledger_forget("file", it["path"], plan["ledger"])
        later.insert(0, it)
    if do["made"] or do["skill"]:   # 台帳に載っていた物を消し終えたら台帳も畳む(残っている物があれば台帳は残る)
        sc.ledger_gc(plan["ledger"])
    if do["cache"]:
        try:
            cache_base(env).rmdir()         # setup/ を畳んだ後なので、空になっていれば消える
        except OSError:
            pass
    kept = [x for x in made + data if x not in removed and x not in later]
    say(m["done"])
    show(removed) if removed else say(m["none"])
    if later:
        say()
        say(m["later"])
        show(later)
    if failed:
        say()
        say(m["fail"])
        for f in failed:
            say("  - " + f)
    if kept:
        say()
        say(m["kept"])
        show(kept)
    if refused:
        say()
        say(m["refused"])
        for r in refused:
            say("  - %-26s %s" % (m[_LABEL[r["kind"]]], r["path"]))
            say("      %s" % r["reason"])
    say()
    pip_start_failed = False
    if do["pip"]:
        try:
            log = pip_fn()
            say(m["pip_later"] % log)
        except Exception as e:      # noqa: BLE001
            say(m["pip_fail"] % (e, cmd_txt))
            pip_start_failed = True         # pip の段を起こせなかった = fullseye 本体が残る(表の 3)
    elif pstate == "ok":
        say(m["pip_no"] % cmd_txt)
    elif pstate == "no_pip":
        say(m["pip_nopip"] % uv_uninstall_hint())
    else:
        say((m["pip_none"] if pstate == "none" else m["pip_other"]) % pdetail)
    if args.pause and is_tty:
        try:
            input_fn(m["pause"])
        except EOFError:
            pass
    if failed or any(not r["foreign"] for r in refused):       # 許可外の項目(書き換えられた台帳)は失敗扱い。別環境の物は正常
        return 1
    return 3 if (pstate == "no_pip" or pip_start_failed) else 0


if __name__ == "__main__":
    sys.exit(main())
