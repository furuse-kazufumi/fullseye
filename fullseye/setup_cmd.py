# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``fullseye setup`` — 対話的な初期設定(環境を調べ、1 問ずつ聞いて、やったことと次の一手を出す)。

``pip install fullseye`` の後に「何をすれば使えるのか」が分からない、という声への答え。標準ライブラリだけで動く
(``input()`` と ``subprocess``)。

* まず環境を調べて表示する(doctor): Python / fullseye / Qt / 任意依存 / Claude Code の RAG skill と MCP。
* 次に 1 問ずつ聞く(Enter で既定): 用途 → Studio の登録 → 足りない依存 → AI 連携 → (最後に)Studio を開くか。
  pip は**実行するコマンドを見せてから**走らせる。黙って入れない。
* ``--yes`` は全部既定で無人実行(窓は開かない)、``--dry-run`` は何も変えず予定だけ表示。
  標準入力が端末でなく ``--yes`` / ``--dry-run`` も無いときは、質問せず案内だけ出して終了コード 0
  (CI やパイプで止まらない)。
* 表示は日本語 / 英語(ロケールで選び、``--lang`` か環境変数 ``FULLSEYE_LANG`` で上書き)。
"""
from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

# (extra 名, import 名, pip の配布名, 説明 ja, 説明 en) — pyproject の extras と対応。
PROBES = [
    ("gui", "PySide6", "PySide6", "Studio の画面", "Studio GUI"),
    ("opencv", "cv2", "opencv-python", "OpenCV 系の op / 画像 I/O", "OpenCV ops / image I/O"),
    ("skimage", "skimage", "scikit-image", "scikit-image 系の op", "scikit-image ops"),
    ("pil", "PIL", "Pillow", "Pillow(画像の読み書き)", "Pillow (image read/write)"),
    ("wavelets", "pywt", "PyWavelets", "ウェーブレット", "wavelets"),
    ("gpu", "torch", "torch", "GPU / torch 系", "GPU / torch ops"),
    ("video", "imageio", "imageio", "動画入出力", "video I/O"),
    ("volume", "SimpleITK", "SimpleITK", "医用ボリューム入力", "volumetric import"),
    ("xlsx", "openpyxl", "openpyxl", "Excel レポート", "Excel reports"),
]
# importlib.metadata で取れないとき(checkout 直読みなど)の代替。
_FALLBACK_REQ = {"gui": ["PySide6>=6.5"], "opencv": ["opencv-python>=4.8.1.78"], "skimage": ["scikit-image>=0.20"],
                 "pil": ["Pillow>=13.0"]}
# 用途ごとの「入れておくと良い」軽い extras(torch / GPU は重いので勧めない。報告だけする)。
RECOMMENDED = {"studio": ["gui"], "python": ["opencv", "skimage", "pil"], "ai": []}

M = {
    "ja": {
        "hdr": "== Fullseye セットアップ ==",
        "env": "[環境]",
        "py": "Python",
        "fs": "fullseye",
        "qt": "Studio(Qt)",
        "qt_ok": "開けます(PySide6 %s)",
        "qt_no_dep": "開けません: PySide6 が未導入(下の質問で入れられます)",
        "qt_no_display": "PySide6 は有りますが、画面(DISPLAY)がありません",
        "opt": "[任意の依存]",
        "have": "あり",
        "miss": "なし",
        "ai": "[AI 連携]",
        "skill_yes": "Claude Code の RAG skill: 登録済み",
        "skill_no": "Claude Code の RAG skill: 未登録",
        "mcp_yes": "MCP: 登録済み(Claude の設定に fullseye あり)",
        "mcp_no": "MCP: 未登録",
        "sc": "[ショートカット]",
        "sc_yes": "Studio: 登録済み",
        "sc_no": "Studio: 未登録",
        "sc_na": "このOSはメニュー登録に対応していません",
        "q_use": "何に使いますか? 1=Studio で触る  2=Python から使う  3=AI から使う (複数可、例 1,3)",
        "q_sc": "Studio をスタートメニュー(アプリ一覧)に登録しますか?",
        "q_desktop": "デスクトップにも置きますか?",
        "q_dep": "足りない依存を入れますか? (%s)",
        "q_rag": "Claude Code に fullseye の RAG skill を登録しますか? (~/.claude/skills)",
        "q_open": "いま Studio を開きますか?",
        "cmd": "実行するコマンド:",
        "plan": "[予定]",
        "dry": "(--dry-run: 何も変更していません)",
        "done_hdr": "[やったこと]",
        "next_hdr": "[次の一手]",
        "nothing": "(変更なし)",
        "p_dep": "依存を入れる: %s",
        "p_sc": "Studio をメニューに登録する(%s)",
        "p_rag": "RAG skill を登録する(%s)",
        "did_dep": "依存を入れた: %s",
        "fail_dep": "依存の導入に失敗(終了コード %s)。上のコマンドを手で実行してください",
        "did_sc": "Studio を登録: %s",
        "fail_sc": "Studio の登録に失敗: %s",
        "did_rag": "RAG skill を登録: %s",
        "fail_rag": "RAG skill の登録に失敗: %s",
        "did_open": "Studio を起動した",
        "fail_open": "Studio の起動に失敗: %s",
        "skip_yes_open": "(--yes では窓を開きません。開くには fullseye-studio)",
        "mcp_ex": "MCP の設定例(Claude Code):",
        "next_studio": "Studio を開く: スタートメニューの Fullseye Studio、または  fullseye-studio",
        "next_py": "Python から: import fullseye; fullseye.apply(img, \"sobel_amp\")   (README の Quickstart)",
        "next_ai": "AI から: Claude Code を開いて画像処理の質問をする / fullseye-rag search \"ノイズ除去\"",
        "next_help": "コマンド一覧: fullseye --help    もう一度: fullseye setup",
        "noninter": "標準入力が端末でないため質問しません(案内だけ表示)。対話するには端末で fullseye setup、"
                    "無人なら fullseye setup --yes。",
        "bad": "もう一度入力してください(Enter で既定)",
        "gpu_note": "GPU(torch)は重いので勧めていません。必要なら  pip install \"fullseye[gpu]\"",
        "g_head": "Fullseye へようこそ。 初めてなら:  fullseye setup   (環境を調べて、1 問ずつ案内します)",
        "g_title": "使い方の入口(次の 3 手):",
        "g_1": "1. Studio を開く(画面で触る)",
        "g_1b": "   スタートメニューに登録",
        "g_2": "2. Python から 3 行で使う",
        "g_3": "3. AI から使う(Claude Code など)",
        "g_tail": "コマンド一覧: fullseye --help    演算子を探す: fullseye ops --search edge    (English: FULLSEYE_LANG=en)",
    },
    "en": {
        "hdr": "== Fullseye setup ==",
        "env": "[Environment]",
        "py": "Python",
        "fs": "fullseye",
        "qt": "Studio (Qt)",
        "qt_ok": "can open (PySide6 %s)",
        "qt_no_dep": "cannot open: PySide6 is not installed (the questions below can install it)",
        "qt_no_display": "PySide6 is installed but there is no display (DISPLAY)",
        "opt": "[Optional dependencies]",
        "have": "yes",
        "miss": "no",
        "ai": "[AI integration]",
        "skill_yes": "Claude Code RAG skill: registered",
        "skill_no": "Claude Code RAG skill: not registered",
        "mcp_yes": "MCP: registered (fullseye is in the Claude settings)",
        "mcp_no": "MCP: not registered",
        "sc": "[Shortcuts]",
        "sc_yes": "Studio: registered",
        "sc_no": "Studio: not registered",
        "sc_na": "menu shortcuts are not supported on this OS",
        "q_use": "What will you use it for? 1=Studio (GUI)  2=from Python  3=from an AI (several ok, e.g. 1,3)",
        "q_sc": "Add Studio to the Start menu / application menu?",
        "q_desktop": "Also put it on the desktop?",
        "q_dep": "Install the missing dependencies? (%s)",
        "q_rag": "Register the fullseye RAG skill with Claude Code? (~/.claude/skills)",
        "q_open": "Open Studio now?",
        "cmd": "Command to run:",
        "plan": "[Plan]",
        "dry": "(--dry-run: nothing was changed)",
        "done_hdr": "[What was done]",
        "next_hdr": "[Next steps]",
        "nothing": "(no changes)",
        "p_dep": "install dependencies: %s",
        "p_sc": "register Studio in the menu (%s)",
        "p_rag": "register the RAG skill (%s)",
        "did_dep": "installed dependencies: %s",
        "fail_dep": "dependency install failed (exit code %s). Run the command above by hand",
        "did_sc": "registered Studio: %s",
        "fail_sc": "could not register Studio: %s",
        "did_rag": "registered the RAG skill: %s",
        "fail_rag": "could not register the RAG skill: %s",
        "did_open": "started Studio",
        "fail_open": "could not start Studio: %s",
        "skip_yes_open": "(--yes never opens a window; run fullseye-studio to open it)",
        "mcp_ex": "MCP setup example (Claude Code):",
        "next_studio": "Open Studio: 'Fullseye Studio' in the Start menu, or  fullseye-studio",
        "next_py": "From Python: import fullseye; fullseye.apply(img, \"sobel_amp\")   (README Quickstart)",
        "next_ai": "From an AI: open Claude Code and ask an image-processing question / fullseye-rag search \"remove noise\"",
        "next_help": "All commands: fullseye --help    Run again: fullseye setup",
        "noninter": "stdin is not a terminal, so no questions are asked (guidance only). For the interactive flow run "
                    "fullseye setup in a terminal; for unattended use fullseye setup --yes.",
        "bad": "Please try again (Enter for the default)",
        "gpu_note": "GPU (torch) is heavy and not recommended here. If needed:  pip install \"fullseye[gpu]\"",
        "g_head": "Welcome to Fullseye. First time?  run:  fullseye setup   (checks your environment and guides you, one question at a time)",
        "g_title": "Where to start (next 3 steps):",
        "g_1": "1. Open Studio (the GUI)",
        "g_1b": "   Add it to the Start menu",
        "g_2": "2. Use it from Python in 3 lines",
        "g_3": "3. Use it from an AI (Claude Code etc.)",
        "g_tail": "All commands: fullseye --help    Find an operator: fullseye ops --search edge    (Japanese: FULLSEYE_LANG=ja)",
    },
}


# --------------------------------------------------------------------------- 言語
def detect_lang(env: Optional[Dict[str, str]] = None, override: Optional[str] = None) -> str:
    """ja / en。引数 > FULLSEYE_LANG > OS の表示言語 > LANG 系の環境変数。"""
    e = os.environ if env is None else env
    for v in (override, e.get("FULLSEYE_LANG")):
        if v and v.lower()[:2] in ("ja", "en"):
            return v.lower()[:2]
    if sys.platform == "win32" and env is None:
        try:
            import ctypes
            if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0xFF == 0x11:     # LANG_JAPANESE
                return "ja"
            return "en"
        except Exception:
            pass
    for k in ("LC_ALL", "LC_MESSAGES", "LANG"):
        if (e.get(k) or "").lower().startswith("ja"):
            return "ja"
    return "en"


def guidance(lang: str) -> str:
    """引数なしの ``fullseye`` と、非端末の ``fullseye setup`` が出す案内。"""
    m = M[lang]
    exe = sys.executable
    return "\n".join([
        m["g_head"], "", m["g_title"],
        "  " + m["g_1"], "      fullseye-studio",
        "  " + m["g_1b"], "      fullseye-studio --install-shortcuts   (+ --desktop)",
        "  " + m["g_2"], "      import fullseye, numpy as np",
        "      img = np.random.rand(64, 64)",
        "      print(fullseye.apply(img, \"sobel_amp\").shape)",
        "  " + m["g_3"], "      fullseye-rag     |     claude mcp add fullseye -- \"%s\" -m fullseye.mcp" % exe,
        "", m["g_tail"], ""])


# --------------------------------------------------------------------------- doctor
def _has(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except (ImportError, ValueError):
        return False


def _ver(dist: str) -> str:
    try:
        return importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        return ""


def _mcp_registered(home: Path) -> bool:
    """Claude Code の設定(~/.claude.json)の mcpServers に fullseye があるか(読めなければ False)。"""
    try:
        data = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False

    def has(d) -> bool:
        return isinstance(d, dict) and any("fullseye" in str(k).lower() for k in (d.get("mcpServers") or {}))
    if has(data):
        return True
    return any(has(v) for v in (data.get("projects") or {}).values())


def collect_env(home: Optional[Path] = None) -> Dict[str, object]:
    """環境の事実を集める(``fullseye doctor`` 相当。何も変更しない)。"""
    home = home or Path.home()
    info: Dict[str, object] = {"python": sys.version.split()[0], "executable": sys.executable,
                               "venv": sys.prefix != getattr(sys, "base_prefix", sys.prefix)}
    try:
        import fullseye
        info["fullseye"] = fullseye.version()
    except Exception as e:      # noqa: BLE001 — 版が取れないことは報告に回す
        info["fullseye"] = "?(%s)" % type(e).__name__
    probes = {}
    for extra, mod, dist, *_ in PROBES:
        probes[extra] = {"installed": _has(mod), "version": _ver(dist) if _has(mod) else ""}
    info["probes"] = probes
    qt = probes["gui"]["installed"]
    display = sys.platform in ("win32", "darwin") or bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
                                                          or os.environ.get("QT_QPA_PLATFORM"))
    info["qt"] = "ok" if qt and display else ("no_display" if qt else "no_dep")
    try:
        from fullseye import rag_setup
        info["skill"] = (rag_setup.default_target() / rag_setup.SKILL_NAME).exists()
    except Exception:           # noqa: BLE001
        info["skill"] = False
    info["mcp"] = _mcp_registered(home)
    try:
        from fullseye import shortcuts as sc
        plat = sc._platform()
        if plat == "win":
            info["shortcut"] = (sc.windows_dirs()["start_menu"] / (sc.APP_NAME + ".lnk")).is_file()
        elif plat == "linux":
            info["shortcut"] = (sc._xdg_data() / "applications" / "fullseye-studio.desktop").is_file()
        else:
            info["shortcut"] = None
    except Exception:           # noqa: BLE001
        info["shortcut"] = None
    return info


def format_report(info: Dict[str, object], lang: str) -> str:
    m = M[lang]
    L = [m["hdr"], "", m["env"],
         "  %-12s %s  (%s%s)" % (m["py"], info["python"], info["executable"], ", venv" if info["venv"] else ""),
         "  %-12s %s" % (m["fs"], info["fullseye"])]
    pr = info["probes"]
    if info["qt"] == "ok":
        L.append("  %-12s %s" % (m["qt"], m["qt_ok"] % (pr["gui"]["version"] or "?")))
    else:
        L.append("  %-12s %s" % (m["qt"], m["qt_no_display"] if info["qt"] == "no_display" else m["qt_no_dep"]))
    L += ["", m["opt"]]
    for extra, _mod, dist, ja, en in PROBES:
        p = pr[extra]
        L.append("  %-14s %-4s %s" % (dist, m["have"] if p["installed"] else m["miss"],
                                      (p["version"] + "  " if p["version"] else "") + (ja if lang == "ja" else en)))
    L += ["", m["ai"], "  " + (m["skill_yes"] if info["skill"] else m["skill_no"]),
          "  " + (m["mcp_yes"] if info["mcp"] else m["mcp_no"]), "", m["sc"]]
    sc = info["shortcut"]
    L.append("  " + (m["sc_na"] if sc is None else (m["sc_yes"] if sc else m["sc_no"])))
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- pip
def requirements_for(extras: Sequence[str]) -> List[str]:
    """extras に対応する要件(``PySide6>=6.5`` など)。fullseye 自身は入れ直さない(checkout を壊さない)。"""
    out: List[str] = []
    try:
        reqs = importlib.metadata.requires("fullseye") or []
    except importlib.metadata.PackageNotFoundError:
        reqs = []
    for x in extras:
        found = []
        for r in reqs:
            if ";" in r:
                spec, marker = r.split(";", 1)
                mk = re.fullmatch(r"\s*extra\s*==\s*['\"]%s['\"]\s*" % re.escape(x), marker)
                if mk:
                    found.append(spec.strip())
        for r in (found or _FALLBACK_REQ.get(x, [])):
            if r not in out:
                out.append(r)
    return out


def pip_command(reqs: Sequence[str]) -> List[str]:
    return [sys.executable, "-m", "pip", "install", *reqs]


def _default_run(cmd: List[str]) -> int:
    return subprocess.call(cmd)


def _default_launch() -> None:
    exe = sys.executable
    kw: Dict[str, object] = {}
    if sys.platform == "win32":
        w = Path(exe).with_name("pythonw.exe")
        exe = str(w) if w.is_file() else exe
        kw["creationflags"] = 0x00000008 | 0x00000200       # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([exe, "-m", "studio"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, cwd=str(Path.home()), **kw)


def _default_rag() -> str:
    from fullseye import rag_setup
    dest = rag_setup.install(rag_setup.default_target(), repo=rag_setup.find_repo(), _auto_repo=False)
    from fullseye import shortcuts
    shortcuts.ledger_record("claude_skill", dest)        # 消すときの台帳(推測で消さない)
    return str(dest)


def _default_shortcuts(desktop: bool) -> List[str]:
    from fullseye import shortcuts
    return [str(p) for p in shortcuts.install(desktop=desktop)]


def _stdin_is_terminal() -> bool:
    """標準入力が本物の端末か。Windows では NUL()も isatty() が True を返すので、
    GetConsoleMode で本当のコンソールかを確かめる(NUL を端末と誤認して質問・登録に進まないため)。"""
    if not (sys.stdin and sys.stdin.isatty()):
        return False
    if sys.platform == "win32":
        import ctypes
        import msvcrt
        h = msvcrt.get_osfhandle(sys.stdin.fileno())
        mode = ctypes.c_uint32()
        return bool(ctypes.windll.kernel32.GetConsoleMode(ctypes.c_void_p(h), ctypes.byref(mode)))
    return True


# --------------------------------------------------------------------------- 本体
def main(argv: Optional[Sequence[str]] = None, *, input_fn: Optional[Callable[[str], str]] = None,
         run_fn: Optional[Callable[[List[str]], int]] = None, launch_fn: Optional[Callable[[], None]] = None,
         rag_fn: Optional[Callable[[], str]] = None, shortcuts_fn: Optional[Callable[[bool], List[str]]] = None,
         is_tty: Optional[bool] = None, out=None, info: Optional[Dict[str, object]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--uninstall" in argv:           # 後始末は fullseye/uninstall.py(台帳に載った物だけを消す)
        from fullseye import uninstall
        return uninstall.main(argv)
    ap = argparse.ArgumentParser(prog="fullseye setup", description="Interactive first-time setup for Fullseye.")
    ap.add_argument("--uninstall", action="store_true",
                    help="remove what setup created (shortcuts, Claude skill, 'Apps & features' entry); asks about "
                         "settings/cache and pip uninstall. Combine with --yes / --dry-run")
    ap.add_argument("--lang", choices=["ja", "en"], default=None, help="ja / en (default: from the locale)")
    ap.add_argument("--yes", "-y", action="store_true", help="accept every default, unattended (never opens a window)")
    ap.add_argument("--dry-run", "-n", action="store_true", help="show the plan only; change nothing")
    args = ap.parse_args(argv)
    out = out or sys.stdout
    try:
        out.reconfigure(errors="replace")       # cp932 の端末でも落ちない
    except Exception:       # noqa: BLE001
        pass
    lang = detect_lang(override=args.lang)
    m = M[lang]
    input_fn = input_fn or input
    run_fn = run_fn or _default_run
    launch_fn = launch_fn or _default_launch
    rag_fn = rag_fn or _default_rag
    shortcuts_fn = shortcuts_fn or _default_shortcuts
    if is_tty is None:
        try:
            is_tty = _stdin_is_terminal()
        except Exception:       # noqa: BLE001
            is_tty = False

    def say(s: str = "") -> None:
        print(s, file=out)

    info = info or collect_env()
    say(format_report(info, lang))
    auto = args.yes or args.dry_run
    if not is_tty and not auto:
        say(m["noninter"])
        say()
        say(guidance(lang))
        return 0
    interactive = is_tty and not args.yes and not args.dry_run

    def ask(q: str, default: str) -> str:
        if not interactive:
            say("%s  -> %s" % (q, default))
            return default
        try:
            ans = input_fn("%s [%s] " % (q, default)).strip()
        except EOFError:
            return default
        return ans or default

    def yn(q: str, default: bool) -> bool:
        for _ in range(3):
            a = ask(q + (" (Y/n)" if default else " (y/N)"), "Y" if default else "N").lower()
            if a in ("y", "yes", "はい", "ｙ"):
                return True
            if a in ("n", "no", "いいえ", "ｎ"):
                return False
            say(m["bad"])
        return default

    # (1) 用途
    uses: List[str] = []
    for _ in range(3):
        raw = ask(m["q_use"], "1")
        picked = {"1": "studio", "2": "python", "3": "ai"}
        toks = [t for t in re.split(r"[,\s、]+", raw) if t]
        if toks and all(t in picked for t in toks):
            uses = [picked[t] for t in dict.fromkeys(toks)]
            break
        say(m["bad"])
    uses = uses or ["studio"]

    plat_ok = info["shortcut"] is not None
    do_sc = do_desktop = False
    if "studio" in uses and plat_ok:
        do_sc = yn(m["q_sc"], True)
        if do_sc:
            do_desktop = yn(m["q_desktop"], False)

    want: List[str] = []
    for u in uses:
        for x in RECOMMENDED[u]:
            if x not in want:
                want.append(x)
    if do_sc and "gui" not in want:
        want.insert(0, "gui")
    missing = [x for x in want if not info["probes"][x]["installed"]]
    do_pip = False
    reqs: List[str] = []
    if missing:
        reqs = requirements_for(missing)
        cmd = pip_command(reqs)
        say(m["cmd"] + "  " + " ".join('"%s"' % c if re.search(r"[<>= ]", c) else c for c in cmd))
        do_pip = bool(reqs) and yn(m["q_dep"] % ", ".join(missing), True)

    do_rag = False
    if "ai" in uses:
        do_rag = (not info["skill"]) and yn(m["q_rag"], True)

    plan = []
    if do_pip:
        plan.append(m["p_dep"] % ", ".join(reqs))
    if do_sc:
        plan.append(m["p_sc"] % ("menu + desktop" if do_desktop else "menu"))
    if do_rag:
        plan.append(m["p_rag"] % "~/.claude/skills")
    say()
    say(m["plan"])
    for p in plan or [m["nothing"]]:
        say("  - " + p)
    if args.dry_run:
        say(m["dry"])
        return 0

    done: List[str] = []
    if do_pip:
        rc = run_fn(pip_command(reqs))
        if rc == 0:
            done.append(m["did_dep"] % ", ".join(reqs))
        else:
            done.append(m["fail_dep"] % rc)
    if do_sc:
        try:
            made = shortcuts_fn(do_desktop)
            done.append(m["did_sc"] % ", ".join(made))
        except Exception as e:      # noqa: BLE001 — 理由を文にして続行
            done.append(m["fail_sc"] % e)
    if do_rag:
        try:
            done.append(m["did_rag"] % rag_fn())
        except Exception as e:      # noqa: BLE001
            done.append(m["fail_rag"] % e)

    if "ai" in uses:
        say()
        say(m["mcp_ex"])
        say('  claude mcp add fullseye -- "%s" -m fullseye.mcp' % sys.executable)
        say('  {"mcpServers": {"fullseye": {"command": %s, "args": ["-m", "fullseye.mcp"]}}}'
            % json.dumps(sys.executable))
    if info["probes"]["gpu"]["installed"] is False and "python" in uses:
        say()
        say(m["gpu_note"])

    if "studio" in uses:
        if args.yes:
            say()
            say(m["skip_yes_open"])
        elif yn(m["q_open"], True):
            try:
                launch_fn()
                done.append(m["did_open"])
            except Exception as e:      # noqa: BLE001
                done.append(m["fail_open"] % e)

    say()
    say(m["done_hdr"])
    for d in done or [m["nothing"]]:
        say("  - " + d)
    say()
    say(m["next_hdr"])
    if "studio" in uses:
        say("  - " + m["next_studio"])
    if "python" in uses:
        say("  - " + m["next_py"])
    if "ai" in uses:
        say("  - " + m["next_ai"])
    say("  - " + m["next_help"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
