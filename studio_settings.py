# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Studio の設定を開き、書込み完了まで検査する共通層。Checked Studio settings writes."""
from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Mapping

__all__ = ["open_settings", "set_failure_reporter", "write_settings"]

_failure_reporter: Callable[[str], object] | None = None


def open_settings():
    """Studio の QSettings を作る唯一の入口。Open the configured Studio QSettings store."""
    from PySide6 import QtCore  # noqa: PLC0415 — import 時に Qt を必要としない

    ini = os.environ.get("FULLSEYE_STUDIO_SETTINGS", "")
    if ini:
        return QtCore.QSettings(ini, QtCore.QSettings.IniFormat)
    return QtCore.QSettings("Fullseye", "Studio")


def set_failure_reporter(fn):
    """書込み失敗を画面へ出す関数を登録する。Register the active UI failure reporter."""
    global _failure_reporter
    _failure_reporter = fn


def _report(reason: str) -> str:
    """登録先の失敗で元の理由を隠さない。Report without letting a reporter exception escape."""
    if _failure_reporter is not None:
        try:
            _failure_reporter(reason)
        except Exception:  # noqa: BLE001 — 設定エラーの報告先が壊れても保存側は理由を返す
            pass
    return reason


def _file_name(settings) -> str:
    """設定の保存先。偽物・壊れた backend でも説明を作る。Best-effort settings location."""
    try:
        return str(settings.fileName() or "the settings store")
    except Exception:  # noqa: BLE001
        return "the settings store"


def write_settings(values: Mapping[str, object] = (), *, remove: Iterable[str] = (),
                   settings=None, what: str = "settings") -> str | None:
    """値の設定・削除を同期し、QSettings の状態を検査する。Return/report a human reason on failure."""
    from PySide6 import QtCore  # noqa: PLC0415 — Qt は呼ばれた時だけ

    target = settings if settings is not None else open_settings()
    location = _file_name(target)
    try:
        # 消してから書く: 「群を消して書き直す」保存(レイアウトの型)で、書いた値まで消さないため。
        # Remove first, then set, so a group that is cleared and rewritten keeps its new values.
        for key in remove:
            target.remove(key)
        for key, value in dict(values).items():
            target.setValue(key, value)
        target.sync()
        status = target.status()
    except Exception as exc:  # noqa: BLE001 — Qt / 偽 backend の例外も同じ失敗として画面へ出す
        return _report("%s could not be saved to %s: %s" % (what, location, exc))
    if status == QtCore.QSettings.NoError:
        return None
    if status == QtCore.QSettings.AccessError:
        detail = "access error"
    elif status == QtCore.QSettings.FormatError:
        detail = "format error"
    else:
        detail = "QSettings status %s" % status
    return _report("%s could not be saved to %s: %s" % (what, location, detail))
