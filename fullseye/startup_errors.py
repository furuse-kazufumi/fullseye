# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""入口の起動例外を、元の詳細を残したまま案内へ変える。 / Explain startup errors without swallowing their details."""
from __future__ import annotations

import sys
import traceback
from typing import Optional


def _detect_lang(override: Optional[str] = None) -> str:
    """setup / doctor と同じ規則で言語を選ぶ。 / Select the language by the same rule as setup and doctor."""
    from fullseye.setup_cmd import detect_lang
    return detect_lang(override=override)


def explain(exc: BaseException, entrypoint: str, *, lang: Optional[str] = None) -> str:
    """よくある Windows 起動例外に原因候補と直し方を付ける。 / Add causes and repairs to common startup exceptions.

    The return value deliberately includes the raw exception text.  Callers also print
    the traceback, so a friendly explanation never removes information needed to debug.
    """
    language = _detect_lang(lang)
    raw = "%s: %s" % (type(exc).__name__, str(exc) or "(no message)")
    low = raw.lower()
    if isinstance(exc, UnicodeError) or "unicodeencodeerror" in low:
        cause = ("コンソールが cp932 のような古い文字エンコーディングを使っています。" if language == "ja"
                 else "The console is using a legacy encoding such as cp932.")
        repair = "chcp 65001; $env:PYTHONUTF8='1'"
    elif isinstance(exc, PermissionError) or "access is denied" in low or "permission denied" in low:
        cause = ("Windows がファイルまたは保護されたフォルダーへのアクセスを拒否しました。" if language == "ja"
                 else "Windows denied access to a file or protected directory.")
        repair = r"py -3.11 -m venv $HOME\venvs\fullseye"
    elif isinstance(exc, FileNotFoundError):
        cause = ("必要なファイルまたは実行ファイルが見つかりません。OneDrive や引用していないパスで移動した場合もあります。" if language == "ja"
                 else "A required file or executable was not found; OneDrive or an unquoted path can also move it.")
        repair = "py -3.11 -m fullseye doctor"
    elif "dll load failed" in low or "winerror 126" in low or "winerror 193" in low or "qt platform plugin" in low:
        cause = ("ネイティブ DLL または Qt platform plugin を読み込めませんでした。" if language == "ja"
                 else "A native DLL or Qt platform plugin could not be loaded.")
        repair = "py -3.11 -m pip install --upgrade fullseye[gui]"
    elif isinstance(exc, ImportError) or "no module named" in low:
        cause = ("Python パッケージが不足しているか、pip が別の Python へ導入しました。" if language == "ja"
                 else "A Python package is missing, or pip installed it into a different Python.")
        repair = "py -3.11 -m pip install --upgrade fullseye"
    elif isinstance(exc, OSError) and ("path" in low or "filename" in low):
        cause = ("Windows がパスを拒否しました。長すぎる、リダイレクトされた、または native helper で引用していない場合があります。" if language == "ja"
                 else "Windows rejected the path (too long, redirected, or not quoted by a native helper).")
        repair = "py -3.11 -m fullseye doctor"
    else:
        cause = "プログラムが起動中に停止しました。" if language == "ja" else "The program stopped while it was starting."
        repair = "py -3.11 -m fullseye doctor --json"
    if language == "ja":
        return "\n".join([
            "Fullseye %s を起動できませんでした。" % entrypoint,
            "何が起きたか: %s" % raw,
            "考えられる理由: %s" % cause,
            "対処: %s" % repair,
            "確認: py -3.11 -m fullseye doctor",
            "元の例外: %s" % raw,
        ])
    return "\n".join([
        "Fullseye %s could not start." % entrypoint,
        "What happened: %s" % raw,
        "Likely cause: %s" % cause,
        "Repair: %s" % repair,
        "Check: py -3.11 -m fullseye doctor",
        "Original exception: %s" % raw,
    ])


def report(exc: BaseException, entrypoint: str, *, out=None, lang: Optional[str] = None) -> str:
    """説明と元の traceback を標準エラーへ書く。 / Report friendly text plus the original traceback."""
    stream = out if out is not None else sys.stderr
    message = explain(exc, entrypoint, lang=lang)
    if stream is not None:
        try:
            print(message, file=stream)
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=stream)
        except (OSError, UnicodeError):
            pass
    return message


def show_windows_message(message: str, title: str = "Fullseye") -> bool:
    """コンソールなし Windows で同じ説明を表示する。 / Show the same explanation without a console."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
        return True
    except (AttributeError, OSError):
        return False


def is_consoleless_windows() -> bool:
    """pythonw 等で標準エラーが無いかを判定する。 / Detect a Windows GUI launch without stderr."""
    return sys.platform == "win32" and getattr(sys, "stderr", None) is None
