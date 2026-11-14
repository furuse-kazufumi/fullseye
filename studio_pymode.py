# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_pymode — Studio の Program 欄の **Python のモード**(UI の層)。

設計書 ``docs/STUDIO_PROGRAM_LANGUAGE.md`` §13 の「UI への繋ぎ」の実装。実行系(``studio_program``)・
エディタ支援(``studio_pyedit_qt`` / ``studio_pyedit_vars_qt``)・プロジェクト(``studio_project``)を、
studio.py の Program 欄・段の欄・変数の欄・Problems に繋ぐ。studio.py への差し込みは薄く
(``win._pymode`` を見て振り分けるだけ)、中身はここに置く。

決まり(設計書 §1.1・§13):

* **モードは 2 つ**: パイプライン(段の列が正本、今までの Studio)と Python(文面が正本、段の列は実行の
  **記録** = 読み取り専用)。モードごとに文面を別々に持ち、切り替えで失わない。どちらにいるかは Program 欄の
  上の 1 か所(切り替えのボタン)に常に出す。
* **実行は作業スレッド**(``threading.Thread`` が ``studio_program.run_program`` を呼ぶ。run_program の中の
  見張りが止める)。GUI のスレッドは 30 ms ごとに終わったかを見るだけ(Qt の信号をスレッドを跨いで撃たない =
  2026-11-04 の QThread の解体の行き詰まりの型を作らない)。同時に走るのは 1 本だけ: 実行中に実行を押すと
  「先に止める」と言って何もしない。
* **Debug の続行と 1 行実行は「止まった所から続ける」**(§4)。ブレークポイント・1 行実行で止まった実行は、
  作業スレッドの中で待っている(``PauseGate``)。続行・1 行実行はそれを起こすだけで、上から走り直さない
  (print も乱数も 2 度走らない)。止まっている間に文面を直したら、止まっている実行を終えて上から走り直す
  (出力の欄にそう書く)。止まった所が関数の中なら、その枠の局所変数も変数の欄に出す。
* **実行時・検査の文は UI の言語で出す**(``studio_program_i18n.localize``。実行系の文は英語が正で、画面に出す
  所だけ直す)。例・新規の文面のコメントも UI の言語(手を付けていなければ言語の切り替えに従う)。
* **安全**: ファイル・プロジェクトから開いた Python は、初回の実行の前に確認(``TrustStore``、中身の SHA-256 で
  覚える。中身が変われば確認し直し)。確認した後にエディタで直した文面は利用者の物として扱う。パイプラインの
  ファイルから「Python に変換」した文面は、そのファイルの信頼を引き継ぐ(初回の実行の前に確認)。開いただけ・
  検査ではコードを走らせない(``compile`` と ``ast`` だけ)。補完・ホバー・変数の一覧は、**実行後の値のうち
  利用者のクラスの物については静的な情報だけ**を使う(``studio_pyedit_safe``: 型の MRO の ``__dict__``。
  ``__dir__`` / ``__getattr__`` / ``__class__`` のプロパティは呼ばない)。jedi には数・文字列・numpy の配列・
  ライブラリのモジュールだけを渡し、``allow_unsafe_interpreter_executions=False``・``auto_import_modules=[]``。
  ライブラリ(numpy・標準ライブラリ・site-packages)の型のメソッドは呼ぶ。変数の欄の利用者の ``__repr__`` は
  作業スレッドで時間の上限つき(``studio_pyedit_values``)。
* **行の基準は 1 か所**(:func:`to_block` / :func:`to_line`): 画面・Problems・実行系・ブレークポイントは
  1 始まりの行、Qt の文書のブロックと補完の供給元は 0 始まり。
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
import threading
import time
import types
from dataclasses import dataclass, field

from PySide6 import QtCore, QtGui, QtWidgets

import studio_program as sp
import studio_program_i18n as spi

MODE_PYTHON = "python"
MODE_PIPELINE = "pipeline"
MODES = (MODE_PIPELINE, MODE_PYTHON)
START_CHOICES = ("last", MODE_PYTHON, MODE_PIPELINE)
SETTINGS_PREFIX = "pymode/"
POLL_MS = 30
#: モードの札(Program 欄の左上)の色 ``{配色: {モード: (文字, 地)}}``。モードは**色・形(印)・語**の 3 つで言う
#: (色だけに頼らない)。赤・琥珀・緑は状態の色なので使わない。文字と地のコントラスト比は 4.5 以上(試験が測る)。
BADGE_PALETTES = {
    "dark": {MODE_PYTHON: ("#0b1020", "#8ab4ff"), MODE_PIPELINE: ("#0b1020", "#d0b0ff")},
    "light": {MODE_PYTHON: ("#ffffff", "#1f4fa3"), MODE_PIPELINE: ("#ffffff", "#5b3aa0")},
}
#: 札の印(形)。Python = 菱形、パイプライン = 段の列を表す横線。食い違いの時は前に警告の印を足す。
#: どれも Segoe UI / Arial / DejaVu Sans / Noto Sans にある字(U+2630 の三本線は無く、代わりの字の無い所では箱になった)。
BADGE_GLYPHS = {MODE_PYTHON: "\u25c6", MODE_PIPELINE: "\u2261"}
BADGE_WARNING = "\u26a0"
#: 食い違いの時の札の縁の色。警告は状態なので琥珀を使う(⚠ の印と並べる。色だけに頼らない)。
BADGE_WARN_BORDER = {"dark": "#f0b429", "light": "#b45309"}
_UNSENT = object()


def contrast_ratio(fg: str, bg: str) -> float:
    """2 つの色(``#rrggbb``)の WCAG のコントラスト比(1〜21)。"""
    def lum(c):
        c = c.lstrip("#")
        out = []
        for i in (0, 2, 4):
            v = int(c[i:i + 2], 16) / 255.0
            out.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
        return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]
    a, b = lum(fg), lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


_MIXED_LINES_RE = re.compile(r"line (\d+):.*?line (\d+):", re.S)


def _classify(text: str) -> tuple:
    """``(どちらに見えるか, 混ざっている行)``。前は ``"python"`` / ``"pipeline"`` / None(空・コメントだけ・
    混ざっている・決められない)。後は 2 つの書き方が混ざっている時だけ ``(パイプラインの書き方の行,
    Python の書き方の行)``(``detect_syntax`` の「混ざっている」の文から読む)。実行しない(字句と構文木だけ)。"""
    lines = [ln.strip() for ln in (text or "").splitlines()]
    code = [ln for ln in lines if ln and not ln.startswith(("#", "*"))]
    if not code:
        return None, None
    try:
        syn, errs = sp.detect_syntax(text)
    except Exception:                                         # noqa: BLE001 -- 判定の失敗で画面を止めない
        return None, None
    if errs:
        m = _MIXED_LINES_RE.search(str(errs[0]))
        return None, ((int(m.group(1)), int(m.group(2))) if m else (1, 1))
    return (MODE_PYTHON if syn == sp.SYNTAX_PYTHON else MODE_PIPELINE), None


def text_looks_like(text: str) -> str | None:
    """文面がどちらの書き方に見えるか: ``"python"`` / ``"pipeline"`` / None(空・コメントだけ・混ざっている・
    決められない)。実行しない(``studio_program.detect_syntax`` = 字句と構文木だけ)。"""
    return _classify(text)[0]


#: 出力の欄の上限: 行数(越えたら古い行から捨てる)と、1 回に書く文字数(越えたら末尾だけ)。
MAX_OUTPUT_LINES = 5000
MAX_OUTPUT_CHARS = 200_000
MAX_TOOLTIP_CHARS = 2000
#: 未保存の文面を設定へ書き出す間隔(落ちても次の起動で戻る)。
AUTOSAVE_MS = 5000
#: ファイルそのものへの自動保存(既定は切。退避 = 上の AUTOSAVE_MS とは別で、退避は設定に関係なく常に動く)。
#: "off" = しない / "idle" = 打つのを止めてから一定時間の後 / "focus" = Program 欄からフォーカスが外れた時。
AUTOSAVE_FILE_MODES = ("off", "idle", "focus")
DEFAULT_AUTOSAVE_IDLE_S = 2.0
AUTOSAVE_IDLE_RANGE_S = (0.5, 600.0)
DEFAULT_TIME_LIMIT_S = sp.DEFAULT_TIME_LIMIT_S
NEW_PROGRAM_COMMENT = "New program. F5 runs it; img is the image open in Studio."
NEW_PROGRAM_TEXT = ("# python\n"
                    "# " + NEW_PROGRAM_COMMENT + "\n"
                    "img = gaussian(img, 0.3)\n"
                    "show(img)\n")


# --------------------------------------------------------------------------- #
# Qt に依らない小さな部品(試験はここを直接呼ぶ)                                 #
# --------------------------------------------------------------------------- #
def to_block(line: int) -> int:
    """画面の行(1 始まり。Problems・実行系・ブレークポイント)→ Qt の文書のブロック番号(0 始まり)。"""
    return max(0, int(line) - 1)


def to_line(block: int) -> int:
    """Qt の文書のブロック番号・補完の供給元の行(0 始まり)→ 画面の行(1 始まり)。"""
    return int(block) + 1


def first_changed_line(old: str, new: str) -> int | None:
    """2 つの文面で最初に違う行(1 始まり)。同じなら None。"""
    a, b = (old or "").split("\n"), (new or "").split("\n")
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i + 1
    if len(a) != len(b):
        return min(len(a), len(b)) + 1
    return None


def per_line_ms(calls) -> dict:
    """記録 → {行: その行の op の時間の合計 ms}(ガターの時間の表示)。"""
    out: dict = {}
    for c in calls:
        out[c.line] = out.get(c.line, 0.0) + float(c.ms or 0.0)
    return out


def call_row_text(c, tr) -> str:
    """記録の 1 行(段の欄)。行番号・op・つまみ・出力の型と形・時間・再計算か使い回しか。"""
    shape = "×".join(str(s) for s in c.out_shape) if c.out_shape else ""
    knobs = "%.4g, %.4g" % (c.a, c.b)
    where = ""
    if c.pipeline:
        where = "  ·  %s #%s" % (c.pipeline, c.pipeline_step)
    mark = tr("↺ cache") if c.cached else tr("⟳ calc")
    return "L%d  %s(%s)  →  %s %s  ·  %.1f ms  ·  %s%s" % (c.line, c.op, knobs, c.out_sort or "?", shape,
                                                         float(c.ms or 0.0), mark, where)


def problem_rows(problems, tr=None) -> list:
    """``check_program`` の結果 → Problems の行 ``[(行, 文)]`` と、波線の ``{行: 文}``。*tr* を渡すと、文と
    直し方と「行 N」を UI の言語で出す(検査の文は英語が正。表に無い文・言語は英語のまま)。"""
    glyph = {"error": "✕", "warning": "⚠", "hint": "ℹ"}
    ident = tr if tr is not None else (lambda s: s)
    rows, per_line = [], {}
    for p in problems:
        message = spi.localize(p.message, ident)
        msg = "%s %s: %s [%s]" % (glyph.get(p.severity, "!"), spi.line_label(p.line, ident), message, p.code)
        if p.hint:
            msg += " — " + spi.localize(p.hint, ident)
        rows.append((int(p.line), msg))
        per_line[int(p.line)] = (per_line[int(p.line)] + "; " + message) if int(p.line) in per_line else message
    return rows, per_line


def error_line_of(text: str) -> int | None:
    """出力の 1 行から「行 N」の N(押すとその行へ飛ぶ。``line 3`` / ``3 行目`` / ``Zeile 3`` … どの言語の
    言い方でも)。無ければ None。"""
    return spi.line_number_of(text)


def trust_store_path(settings_file: str | None) -> str:
    """信頼の台帳(JSON)の置き場: 設定が ini ならその隣、そうでなければ利用者のデータの場所。"""
    if settings_file and settings_file.lower().endswith(".ini") and os.path.isdir(os.path.dirname(settings_file)):
        return os.path.join(os.path.dirname(settings_file), "studio_trust.json")
    base = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.AppDataLocation) or tempfile.gettempdir()
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "studio_trust.json")


@dataclass
class DebugSession:
    """Debug で止まっている実行(続行・1 行実行の起点)。*job* = 止まって待っている実行(作業スレッド)。"""
    text: str
    lines_run: int
    line: int
    reason: str
    job: "RunJob | None" = None

    @property
    def live(self) -> bool:
        """止まった実行がまだ待っているか(続行・1 行実行で、その場から続けられる)。"""
        return self.job is not None and not self.job.done


class PauseGate:
    """ブレークポイント・1 行実行で止まった実行(作業スレッド)と GUI の受け渡し。

    作業スレッドは :meth:`hook`(``run_program(pause_hook=)``)の中で待つ。GUI は :attr:`snapshot`(止まった時点の
    ``ProgramResult``)を取って画面に出し、:meth:`resume` で起こす。止める要求(*stop_event*)が立てば待ちを
    やめて "stop" を返す。Qt の物には触らない(スレッドを跨いで信号を撃たない)。"""

    def __init__(self, stop_event: threading.Event):
        self.stop_event = stop_event
        self.snapshot = None
        self._wake = threading.Event()
        self._command: object = "stop"

    def hook(self, snapshot):
        self._wake.clear()
        self.snapshot = snapshot
        while not self._wake.wait(0.02):
            if self.stop_event.is_set():
                return "stop"
        return self._command

    def resume(self, command, breakpoints=None, conditions=None) -> None:
        self._command = {"command": command, "breakpoints": breakpoints, "conditions": conditions}
        self._wake.set()


def run_plan(action: str, session: DebugSession | None, text: str, breakpoints, conditions) -> dict:
    """run / continue / step の、run_program に渡す引数(Qt なし。試験あり)。

    * run      : 上から。ブレークポイントと条件を渡す。
    * continue : 止まっている所から続ける。止まった実行が待っていれば(``session.live``)それを起こす
                 (``resume="continue"``。今のブレークポイントと条件を渡し直す)。待っている実行が無ければ
                 走り直しで、すでに通った行数 + 1 まではブレークポイントで止めない。
                 文面が止まった時から変わっていれば、上から(``restart=True``)。
    * step     : 1 行。待っている実行があれば起こして 1 行(``resume="step"``)。止まっていなければ最初の行で
                 止まる(``max_lines=0``)。

    ``resume`` が None でなければ新しい実行は起こさない(他の鍵は起こす実行へ渡す物)。"""
    bps = sorted(set(int(b) for b in breakpoints))
    conds = {int(k): v for k, v in (conditions or {}).items() if int(k) in bps}
    same = session is not None and session.text == text
    live = same and bool(getattr(session, "live", False))
    if action not in ("run", "continue", "step"):
        raise ValueError("action must be run / continue / step, got %r" % (action,))
    if live and action in ("continue", "step"):
        return {"breakpoints": bps, "conditions": conds, "resume_after_lines": 0, "max_lines": None,
                "restart": False, "resume": action}
    if action == "run" or (action == "continue" and not same):
        return {"breakpoints": bps, "conditions": conds, "resume_after_lines": 0, "max_lines": None,
                "restart": action == "continue", "resume": None}
    if action == "continue":
        return {"breakpoints": bps, "conditions": conds, "resume_after_lines": session.lines_run + 1,
                "max_lines": None, "restart": False, "resume": None}
    n = session.lines_run + 1 if same else 0
    return {"breakpoints": [], "conditions": {}, "resume_after_lines": 0, "max_lines": n, "restart": False,
            "resume": None}


def atomic_write_text(path: str, text: str) -> None:
    """同じ場所の一時ファイル → ``os.replace``(書きかけのファイルを残さない)。"""
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".~", suffix=".py", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _bytes_stamp(data: bytes) -> tuple:
    """バイト列の印 ``(大きさ, SHA-256)``。ファイルに書いた・ファイルから読んだ、そのバイト列から作る。"""
    import hashlib
    return len(data), hashlib.sha256(data).hexdigest()


#: 設定に残す「比べる元が無い(外で変わった・読めなかった)」の印。
_STAMP_CHANGED = "changed"


def _stamp_from_setting(value):
    """設定の ``file_stamp``(``"大きさ:SHA-256"`` か ``"changed"``)を印へ。空(前の版の設定)なら None。
    ``"changed"`` と読めない値は、どの印とも等しくない物(= 変わった)。"""
    s = str(value or "")
    if not s:
        return None
    size, _sep, digest = s.partition(":")
    if s == _STAMP_CHANGED or not size.isdigit() or len(digest) != 64:
        return (-1, _STAMP_CHANGED)
    return int(size), digest


def _file_stamp(path) -> tuple | None:
    """ファイルの今の中身の印 ``(大きさ, 生のバイトの SHA-256)``。**読めなければ None**(呼び出し側は「変わった」
    として扱う)。文字にしない(UTF-8 で解けない中身も、4 MB を越える中身も、そのまま比べられる)。"""
    import hashlib
    h = hashlib.sha256()
    n = 0
    try:
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(1 << 20)
                if not chunk:
                    break
                h.update(chunk)
                n += len(chunk)
    except (OSError, TypeError, ValueError):
        return None
    return n, h.hexdigest()


def _default_trust(parent, title, text):
    """信頼の確認の窓(「ファイルから来たプログラムを実行しますか」)。**既定のボタンも Esc もキャンセル**
    (2026-11-13 第 3 回レビュー S6: 既定を決めていなかったので、Qt が「Run it」にフォーカスを置き、F5 の直後に
    反射的に Enter を押すと確認していないコードが走った)。画面の無い実行(offscreen)では窓を出せないので、
    安全な側(実行しない)を返す。"""
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return False
    box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, title, text, QtWidgets.QMessageBox.NoButton, parent)
    run = box.addButton(_TR["fn"]("Run it"), QtWidgets.QMessageBox.AcceptRole)
    cancel = box.addButton(_TR["fn"]("Cancel"), QtWidgets.QMessageBox.RejectRole)
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    box.exec()
    return box.clickedButton() is run


def _default_save(parent, title, text):                      # pragma: no cover - GUI
    b = QtWidgets.QMessageBox.question(parent, title, text,
                                       QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard
                                       | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Save)
    return {QtWidgets.QMessageBox.Save: "save", QtWidgets.QMessageBox.Discard: "discard"}.get(b, "cancel")


def _default_condition(parent, title, label, text):          # pragma: no cover - GUI
    t, ok = QtWidgets.QInputDialog.getText(parent, title, label, QtWidgets.QLineEdit.Normal, text)
    return t if ok else None


def _default_open(parent, title, start):                     # pragma: no cover - GUI
    return QtWidgets.QFileDialog.getOpenFileName(parent, title, start or "", "Python (*.py)")[0] or None


def _default_save_as(parent, title, start):                  # pragma: no cover - GUI
    return QtWidgets.QFileDialog.getSaveFileName(parent, title, start or "", "Python (*.py)")[0] or None


#: 確認の窓(試験は差し替える)。TRUST_HOOK(parent, 題, 文) -> bool(True = 実行する)。
TRUST_HOOK = _default_trust
#: SAVE_HOOK(parent, 題, 文) -> "save" / "discard" / "cancel"(未保存のプログラムを閉じる前)。
SAVE_HOOK = _default_save
#: CONDITION_HOOK(parent, 題, 文, 今の式) -> 式 / None(条件つきブレークポイントの式)。
CONDITION_HOOK = _default_condition
#: OPEN_HOOK(parent, 題, 初めの場所) -> パス / None。SAVE_AS_HOOK も同じ形。
OPEN_HOOK = _default_open
SAVE_AS_HOOK = _default_save_as
_TR = {"fn": lambda s: s}


# --------------------------------------------------------------------------- #
# 作業スレッド                                                                  #
# --------------------------------------------------------------------------- #
class RunJob:
    """``fn()`` を作業スレッドで 1 回呼ぶ。終わったかは GUI のスレッドが :attr:`done` で見る。"""

    def __init__(self, kind: str, fn, stop_event: threading.Event, meta: dict, gate: "PauseGate | None" = None):
        self.kind = kind
        self.meta = meta
        self.stop_event = stop_event
        #: ブレークポイント・1 行実行で止まって待つための受け渡し(Debug の実行だけ)。
        self.gate = gate
        self.result = None
        self.exc: BaseException | None = None
        self.started = time.perf_counter()
        self._fn = fn
        self.thread = threading.Thread(target=self._body, name="studio-pymode-run", daemon=True)

    def _body(self):
        try:
            self.result = self._fn()
        except BaseException as e:                            # noqa: BLE001 -- 実行系の外の失敗も GUI で言う
            self.exc = e

    def start(self):
        self.thread.start()
        return self

    @property
    def done(self) -> bool:
        return not self.thread.is_alive()


class _OutputView(QtWidgets.QPlainTextEdit):
    """出力の欄。``line N`` を含む行を押すと、Program 欄のその行へ飛ぶ。"""

    def __init__(self, on_line, parent=None):
        super().__init__(parent)
        self._on_line = on_line
        self.setReadOnly(True)
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")

    def mouseReleaseEvent(self, ev):
        super().mouseReleaseEvent(ev)
        if ev.button() == QtCore.Qt.LeftButton and not self.textCursor().hasSelection():
            ln = error_line_of(self.cursorForPosition(ev.pos()).block().text())
            if ln is not None:
                self._on_line(ln)


# --------------------------------------------------------------------------- #
# モードの持ち主                                                                #
# --------------------------------------------------------------------------- #
class PyModeController(QtCore.QObject):
    """Program 欄の Python のモードの状態と、実行・ファイル・確認・表示の繋ぎ。``win._pymode``。"""

    def __init__(self, win, ctx: dict):
        super().__init__(win)
        self.win = win
        win._pymode = self                                    # 部品を作る間に撃たれる文書の変更の合図もここへ来る
        self.ctx = ctx
        self.tr = ctx["tr"]
        _TR["fn"] = self.tr
        self.edit = ctx["edit"]
        self.model = ctx["model"]
        self.state = ctx["state"]
        self.flash = ctx["flash"]
        self.settings = ctx["settings"]
        self.mode = MODE_PIPELINE
        self.config = "debug"
        #: 「新規」の文面(コメントは UI の言語)の SHA-256。手を付けていない無題の文面かどうかの判定に使う。
        self._new_digests: set = {sp.program_digest(NEW_PROGRAM_TEXT)}
        self._new_text()                                      # 今の言語の「新規」の文面も覚える
        self.py_text = self._starter()
        self.pipe_text: str | None = None
        self.pipe_dirty = False
        self.file: str | None = None
        self.origin = "typed"
        #: 開いたパイプラインのファイル(その文面から「Python に変換」した物は、このファイルの信頼を引き継ぐ)。
        self.pipe_source: str | None = None
        #: 確認の窓に出す「どこから来たか」(ファイルに結び付いていない文面のとき)。
        self.origin_path: str | None = None
        self._frame_local_names: set = set()
        self._autosaved_digest: str | None = None
        self.session_trusted = True
        #: 開いた(か最後に保存した)時の、ファイルの生のバイトの印 ``(大きさ, SHA-256)``。「Studio の外で書き換え
        #: られたか」はこれと今のディスクの印を比べて決める(:meth:`disk_changed`。2026-11-13 第 3 回レビュー S3)。
        self._disk_stamp: tuple | None = None
        #: ファイル・プロジェクトから来て、まだ確認していない文面 ``{中身の SHA-256: (由来, どこから来たか)}``。
        #: 信頼は**文面に結び付く**(2026-11-13 第 3 回レビュー S2): 「Python に変換」「Python のモードへ移す」は
        #: Python の文面を置き換えて「手で打った物」にするが、Ctrl+Z で前の文面(確認していないファイル)が戻る。
        #: 今の文面がこの表にある文面そのものになったら、由来と信頼をそのファイルの物に戻す(:meth:`_sync_trust`)。
        self._unconfirmed: dict = {}
        self.saved_digest: str | None = None
        self.breakpoints_py: set = set()
        self.breakpoints_pipe: set = set()
        self.conditions: dict = {}
        self.memo = sp.OpMemo()
        self.job: RunJob | None = None
        self.last: sp.ProgramResult | None = None
        self.last_text: str | None = None
        self.session: DebugSession | None = None
        self.namespace: dict | None = None
        self._prelude_keys = None
        self._legacy_ss = self.edit.styleSheet()
        self._suspend_text = False
        #: モードごとの文書。モードの切り替えは ``setDocument`` で差し替えるだけ = 文面も Undo の履歴も失わない
        #: (``setPlainText`` で入れ替えていた間は、切り替えのたびに履歴が消えた)。エディタが持ち主のままだと
        #: ``setDocument`` で前の文書が消されるので、持ち主をここ(QObject)へ移す。
        self.doc_pipe = self.edit.document()
        self.doc_pipe.setParent(self)
        self.doc_py: QtGui.QTextDocument | None = None
        self._cursor_pos = {MODE_PIPELINE: 0, MODE_PYTHON: 0}
        self.trust = sp.TrustStore(trust_store_path(self._settings_file()))
        self._poll = QtCore.QTimer(self)
        self._poll.setInterval(POLL_MS)
        self._poll.timeout.connect(self._poll_job)
        self._autosave = QtCore.QTimer(self)
        self._autosave.setInterval(AUTOSAVE_MS)
        self._autosave.timeout.connect(self.autosave_now)
        self._file_save_timer = QtCore.QTimer(self)           # ファイルへの自動保存(打つのを止めてから)
        self._file_save_timer.setSingleShot(True)
        self._file_save_timer.timeout.connect(lambda: self.autosave_file("idle"))
        self._conflict_told = None                            # 「外で変わったので自動保存しない」と言った時のディスクの印
        self._autosave_actions: dict = {}
        self.assist = None
        with self._quiet_text():
            self._build_assist()
        self._build_ui()
        self.edit.assist_hook = self._paint_marks
        self.edit._gutter.installEventFilter(self)
        self.edit.installEventFilter(self)                    # フォーカスが外れた時の自動保存

    @contextlib.contextmanager
    def _quiet_text(self):
        """文字は変わらないが文書の変更の合図が出る操作(色分けの付け外し)の間、「未適用の編集」の印を守る。"""
        dirty = self.state.get("code_dirty")
        old = self._suspend_text
        self._suspend_text = True
        try:
            yield
        finally:
            self._suspend_text = old
            self.state["code_dirty"] = dirty

    # ---- 設定 ----
    def _settings_file(self) -> str | None:
        try:
            return self.settings().fileName()
        except Exception:                                     # noqa: BLE001
            return None

    def _get(self, key, default=None):
        try:
            v = self.settings().value(SETTINGS_PREFIX + key)
        except Exception:                                     # noqa: BLE001
            return default
        return default if v is None else v

    def _set(self, key, value):
        try:
            self.settings().setValue(SETTINGS_PREFIX + key, value)
        except Exception as e:                                # noqa: BLE001
            self.state.setdefault("errors", []).append(("could not save the Python mode settings", str(e)))

    def time_limit_s(self) -> float:
        try:
            v = float(self._get("time_limit_s", DEFAULT_TIME_LIMIT_S))
            return v if v > 0 else DEFAULT_TIME_LIMIT_S
        except (TypeError, ValueError):
            return DEFAULT_TIME_LIMIT_S

    # ---- 状態 ----
    @property
    def active(self) -> bool:
        return self.mode == MODE_PYTHON

    @property
    def running(self) -> bool:
        return self.job is not None

    def unsaved(self) -> bool:
        """Python の文面に保存していない変更があるか(ファイルなら中身と比べる。無題なら例・新規の文面と比べる)。"""
        text = self.edit.toPlainText() if self.active else self.py_text
        if self.file:
            return self.saved_digest != sp.program_digest(text)
        return self._pristine_kind(text) is None and sp.program_digest(text) != self.saved_digest

    def _lang(self) -> str:
        return self.ctx.get("lang", lambda: "en")()

    def _starter(self) -> str:
        """例の文面(コメントは UI の言語。表に無い言語は英語)。"""
        return sp.starter_program(self._lang())

    def _new_text(self) -> str:
        """「新規」の文面(コメントは UI の言語)。"""
        text = NEW_PROGRAM_TEXT.replace(NEW_PROGRAM_COMMENT,
                                        self.tr("New program. F5 runs it; img is the image open in Studio."))
        self._new_digests.add(sp.program_digest(text))
        return text

    def _pristine_kind(self, text: str) -> str | None:
        """*text* が手を付けていない例("example")・新規("new")の文面か(どの言語の物でも)。違えば None。"""
        if text in sp.STARTER_PROGRAMS.values():
            return "example"
        if sp.program_digest(text) in self._new_digests:
            return "new"
        return None

    def _relocalize_untouched_text(self):
        """手を付けていない無題の例・新規の文面は、今の言語の物に入れ替える(コメントが UI の言語に従う)。
        行は全言語で同じなので、ブレークポイントと条件はそのまま。走っている・止まっている間は触らない。"""
        new_text = self._new_text()                           # 今の言語の「新規」の文面を覚える
        if self.file or self.running or self.session is not None:
            return
        text = self.edit.toPlainText() if self.active else self.py_text
        kind = self._pristine_kind(text)
        want = self._starter() if kind == "example" else new_text if kind == "new" else None
        if want is None or want == text:
            return
        if not self.active:
            self.py_text = want
            return
        bps, conds = set(self.edit.breakpoints), dict(self.conditions)
        self._load_text(want, None, "typed")
        self.edit.breakpoints, self.conditions = bps, conds
        self.edit._gutter.update()
        self.edit._highlight()

    def display_name(self) -> str:
        return os.path.basename(self.file) if self.file else self.tr("untitled.py")

    # ---- 部品 ----
    def _build_assist(self):
        try:
            import studio_pyedit_complete as comp
            import studio_pyedit_qt as pq
            _configure_jedi()
            self.catalog = comp.FullseyeOpCatalog()
            root = self.ctx.get("project_root", lambda: None)()
            files = comp.DirectoryProjectFiles(root) if root else None
            base = comp.default_provider(namespace=self._completion_namespace, catalog=self.catalog,
                                         project_files=files, tr=self._ptr)
            self.provider = _LockedProvider(base)
            self.assist = pq.PyEditAssist(self.edit, provider=self.provider, theme="dark", tr=self._ptr)
            self.assist.set_active(False)
        except Exception as e:                                # noqa: BLE001 -- 支援が無くても実行は動く
            self.assist = None
            self.state.setdefault("errors", []).append(("Python editor assistance unavailable", str(e)))

    def _ptr(self, s):
        """部品の文: Studio の i18n.json にあればそれ、無ければ部品の対訳(studio_pyedit_i18n.json)。"""
        t = self.tr(s)
        if t != s:
            return t
        try:
            import studio_pyedit_i18n as pi
            lang = self.ctx.get("lang", lambda: "en")()
            if lang in pi.LANGS:
                return pi.make_tr(lang)(s)
        except Exception:                                     # noqa: BLE001
            pass
        return s

    def _completion_namespace(self):
        ns = self.namespace
        return ns if isinstance(ns, dict) else None

    def warm_up(self):
        """最初の補完の待ち(実測 2.9 s: op の台帳と jedi の初回)を背景のスレッドで先に済ませる。"""
        prov = getattr(self, "provider", None)
        if prov is None or getattr(self, "_warming", False):
            return
        self._warming = True

        def body():
            with prov.lock:
                try:
                    self.catalog.warm_up()
                    prov.base.complete("import numpy as np\nnp.ar", 1, 5)
                except Exception:                             # noqa: BLE001
                    pass
        threading.Thread(target=body, name="studio-pymode-warmup", daemon=True).start()

    def _build_ui(self):
        tr = self.tr
        ctx = self.ctx
        lay = ctx["code_layout"]
        bar = QtWidgets.QHBoxLayout()
        bar.setSpacing(4)
        # モードの札: この欄の文面がパイプラインか Python かを、切り替えのボタンの状態に頼らずに常に見せる
        self.badge = QtWidgets.QToolButton()
        self.badge.setObjectName("program_mode_badge")
        self.badge.setAutoRaise(True)
        self.badge.setFocusPolicy(QtCore.Qt.NoFocus)
        self.badge.clicked.connect(lambda _=False: self._badge_clicked())
        self.badge_palette = "dark"
        self._mismatch: str | None = None
        self._mixed_at: int | None = None                     # 混ざっている時、直す側の行(札の「この行へ」)
        self._badge_key = None                                # (モード, 文書): これが変わった時だけ文面を読み直す
        self._badge_sent: dict = {}                           # 繋ぎ先へ最後に送った値(同じ値は送り直さない)
        self._checked = (None, None)                          # (文面, 検査の結果): 最後の check_now
        bar.addWidget(self.badge)
        self.btn_pipe = QtWidgets.QToolButton()
        self.btn_py = QtWidgets.QToolButton()
        for b, m in ((self.btn_pipe, MODE_PIPELINE), (self.btn_py, MODE_PYTHON)):
            b.setCheckable(True)
            b.setAutoRaise(False)
            b.clicked.connect(lambda _=False, mm=m: self.set_mode(mm))
            bar.addWidget(b)
        grp = QtWidgets.QButtonGroup(self)
        grp.setExclusive(True)
        grp.addButton(self.btn_pipe)
        grp.addButton(self.btn_py)
        self._mode_group = grp
        self.mode_note = QtWidgets.QLabel()
        self.mode_note.setProperty("hint", True)
        bar.addWidget(self.mode_note)
        bar.addStretch(1)
        self.autosave_note = QtWidgets.QLabel()               # 「自動保存した」を小さく出す(窓は出さない)
        self.autosave_note.setProperty("muted", True)
        bar.addWidget(self.autosave_note)
        self.file_label = QtWidgets.QLabel()
        bar.addWidget(self.file_label)
        self.config_box = QtWidgets.QComboBox()
        self.config_box.addItems([tr("Debug"), tr("Release")])
        self.config_box.currentIndexChanged.connect(lambda i: self.set_config(("debug", "release")[i]))
        bar.addWidget(self.config_box)
        # 文面の「元に戻す / やり直し」(どちらのモードでも。出来ない時は無効)
        self.btn_undo = QtWidgets.QToolButton()
        self.btn_redo = QtWidgets.QToolButton()
        for b, glyph, fn in ((self.btn_undo, "\u21b6", lambda: self.edit.undo()),
                             (self.btn_redo, "\u21b7", lambda: self.edit.redo())):
            b.setText(glyph)
            b.setFocusPolicy(QtCore.Qt.NoFocus)               # 押してもコード欄のフォーカスを奪わない
            b.setEnabled(False)
            b.clicked.connect(lambda _=False, f=fn: f())
            bar.addWidget(b)
        self.edit.undoAvailable.connect(self.btn_undo.setEnabled)
        self.edit.redoAvailable.connect(self.btn_redo.setEnabled)
        self.btn_run = QtWidgets.QToolButton()
        self.btn_step = QtWidgets.QToolButton()
        self.btn_stop = QtWidgets.QToolButton()
        for b, fn in ((self.btn_run, self.run), (self.btn_step, self.step), (self.btn_stop, self.stop)):
            b.clicked.connect(lambda _=False, f=fn: f())
            bar.addWidget(b)
        self.btn_run.setStyleSheet("QToolButton{font-weight:bold;}")
        lay.insertLayout(0, bar)
        self.bar = bar
        # 出力の欄(Python のモードだけ)
        self.output = _OutputView(self.goto_line)
        self.output.setMaximumBlockCount(MAX_OUTPUT_LINES)   # 古い行から捨てる(出力に上限)
        self.output.setMaximumHeight(96)                     # コードの欄を狭めない(実際の窓で 5 行しか見えなかった)
        self.output.setMinimumHeight(40)
        self.output_title = QtWidgets.QLabel()
        self.output_title.setProperty("muted", True)
        idx = lay.indexOf(ctx["status"])
        lay.insertWidget(idx if idx >= 0 else lay.count(), self.output_title)
        lay.insertWidget((idx + 1) if idx >= 0 else lay.count(), self.output)
        # 段の欄 = 実行の記録(Python のモード)
        sl = ctx["stage_list"]
        self.record = QtWidgets.QListWidget()
        self.record.setIconSize(QtCore.QSize(32, 32))
        self.record.itemClicked.connect(self._record_clicked)
        self.record.itemActivated.connect(self._record_clicked)
        self.record_title = QtWidgets.QLabel()
        self.record_title.setWordWrap(True)
        rec_w = QtWidgets.QWidget()
        rl = QtWidgets.QVBoxLayout(rec_w)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(2)
        rl.addWidget(self.record_title)
        rl.addWidget(self.record, 1)
        self.stage_stack = _wrap_in_stack(sl, rec_w)
        # 変数・ウォッチ(Python のモード)
        self.var_source = None
        self.vars = None
        self.var_stack = None
        self._built_lang = None
        self._build_vars()
        self.record.setToolTip(tr("Record of the last run: one row per op call (line, op, knobs, output, time, "
                                  "recalculated or from cache). Click a row to show its result"))
        self.retranslate()
        self._sync_mode_widgets()

    def _build_vars(self):
        """変数・ウォッチの欄(部品は作るときの言語で文を持つので、言語を切り替えたら作り直す。式は引き継ぐ)。"""
        dv = self.ctx.get("dock_vars")
        if dv is None:
            return
        try:
            import studio_pyedit_values as pv
            import studio_pyedit_vars_qt as vq
        except Exception as e:                                # noqa: BLE001
            self.state.setdefault("errors", []).append(("variables panel unavailable", str(e)))
            return
        watch = self.vars.watch.dumps() if self.vars is not None else None
        if self.var_source is None:
            self.var_source = _namespace_source(pv, self)
        new = vq.VarsWatchWidget(self.var_source, self._ptr, on_run=self.run, on_open_example=self.open_example)
        new.variables.imageRequested.connect(lambda _n, v: self._show_value(v))
        new.watch.changed.connect(lambda _l: self._set("watch", self.vars.watch.dumps()))
        new.watch.confirm_remove = lambda expr: self._confirm(
            self.tr("Remove the watch expression"),
            self.tr("The watch expression  %s  is removed from the list. It cannot be brought back (you can type it "
                    "again).") % expr, self.tr("Remove it"))
        new.watch.table.setToolTip(self.tr("Watch expressions and their values, evaluated again each time the "
                                           "program stops or finishes"))
        if watch:
            new.watch.loads(watch)
        if self.var_stack is None:
            old = dv.widget()
            stack = QtWidgets.QStackedWidget()
            stack.addWidget(old)
            stack.addWidget(new)
            dv.setWidget(stack)
            self.var_stack = stack
        else:
            prev = self.vars
            self.var_stack.insertWidget(1, new)
            self.var_stack.removeWidget(prev)
            try:                                              # すぐ消す(deleteLater は processEvents では消えず、古い言語の欄が残る)
                import shiboken6
                prev.setParent(None)
                shiboken6.delete(prev)
            except (ImportError, RuntimeError):
                prev.deleteLater()
        self.vars = new
        self._built_lang = self.ctx.get("lang", lambda: "en")()
        if self.var_source.ns:
            new.refresh()

    def retranslate(self):
        """今の言語で文を付け直す(言語の切り替え = studio の _relocalize_dynamic から呼ばれる)。"""
        tr = self.tr
        lang = self.ctx.get("lang", lambda: "en")()
        if self.vars is not None and lang != self._built_lang:
            self._build_vars()
        if self.assist is not None:
            self.assist.popup.list.setStatusTip(tr("Completions: Up / Down to choose, Enter or Tab to insert, "
                                                   "Esc to close"))
        self.record.setToolTip(tr("Record of the last run: one row per op call (line, op, knobs, output, time, "
                                  "recalculated or from cache). Click a row to show its result"))
        if self.vars is not None:
            self.vars.watch.table.setToolTip(tr("Watch expressions and their values, evaluated again each time the "
                                                "program stops or finishes"))
        for i, en in enumerate(("Debug", "Release")):
            self.config_box.setItemText(i, tr(en))
        for a, text_en, tip_en in getattr(self, "_action_texts", ()):
            a.setText(tr(text_en))
            if tip_en:
                a.setToolTip(tr(tip_en))
                a.setStatusTip(tr(tip_en))
        for m, title_en in getattr(self, "_menu_titles", ()):
            m.setTitle(tr(title_en))
        self.btn_undo.setToolTip(tr("Undo the last edit of the Program text (Ctrl+Z)"))
        self.btn_redo.setToolTip(tr("Redo the edit that was undone (Ctrl+Y or Ctrl+Shift+Z)"))
        self.btn_pipe.setText(tr("Pipeline mode"))
        self.btn_py.setText(tr("Python mode"))
        self.btn_pipe.setToolTip(tr("Pipeline mode: the stage list is the source; the Program shows it as code"))
        self.btn_py.setToolTip(tr("Python mode: the Program text is the source; the stage list records each run"))
        self.config_box.setToolTip(tr("Debug stops at breakpoints and steps line by line; Release runs faster "
                                      "without the line hook (breakpoints do not stop)"))
        self.btn_run.setText(tr("Run as Python"))
        self.btn_run.setToolTip(tr("Run the Program text as Python (F5). When stopped at a breakpoint: continue"))
        self.btn_step.setText(tr("Step"))
        self.btn_step.setToolTip(tr("Step: run one line and stop (F6, Debug only)"))
        self.btn_stop.setText(tr("Stop"))
        self.btn_stop.setToolTip(tr("Stop the running program (Ctrl+F2)"))
        self.output_title.setText(tr("Output (print, notes and errors; click a line with 'line N' to go there)"))
        self.output.setPlaceholderText(tr("Run the program (F5): print output, notes and errors appear here."))
        if getattr(self, "stage_stack", None) is not None:   # 部品を作っている途中(_build_ui)では入れ替えない
            self._relocalize_untouched_text()
        self._update_labels()

    # ---- 見た目の同期 ----
    def _sync_mode_widgets(self):
        py = self.active
        self.btn_py.setChecked(py)
        self.btn_pipe.setChecked(not py)
        for b in self.ctx.get("pipeline_buttons", ()):
            b.setVisible(not py)
        for w in (self.config_box, self.btn_run, self.btn_step, self.btn_stop, self.file_label, self.output,
                  self.output_title, self.autosave_note):
            w.setVisible(py)
        self.stage_stack.setCurrentIndex(1 if py else 0)
        if getattr(self, "var_stack", None) is not None:
            self.var_stack.setCurrentIndex(1 if py else 0)
        self.edit.comment_prefix = "#" if py else "*"
        self.edit.legacy_completion = not py
        try:                                                  # 起動時の案内(最初の 3 手)をモードに合わせる
            self.ctx.get("first_steps", lambda _py: None)(py)
        except Exception as e:                                # noqa: BLE001 -- 案内の失敗でモードの切り替えを止めない
            self.state.setdefault("errors", []).append(("could not update the first steps", str(e)))
        if self.assist is not None:
            with self._quiet_text():                         # 色分けの付け外しは文書の「変更」を撃つ: 未適用・未保存にしない
                self.assist.set_active(py)
            if not py:
                self.edit.setStyleSheet(self._legacy_ss)
        self._update_labels()
        self.edit._highlight()
        d = self.edit.document()                              # 文書を差し替えた: ボタンの有効・無効をその文書に合わせる
        self.btn_undo.setEnabled(d.isUndoAvailable())
        self.btn_redo.setEnabled(d.isRedoAvailable())
        try:
            self.ctx.get("sync_undo_actions", lambda: None)()
        except Exception:                                     # noqa: BLE001
            pass

    def _update_labels(self):
        tr = self.tr
        if self.active:
            self.mode_note.setText(tr("Python: the text is the source"))
            star = " ●" if self.unsaved() else ""
            self.file_label.setText(self.display_name() + star)
            self.file_label.setToolTip(self.file or tr("not saved to a file yet"))
        else:
            self.mode_note.setText(tr("Pipeline: the stage list is the source"))
        self.btn_stop.setEnabled(self.running or self.session is not None)
        self.btn_step.setEnabled(self.config == "debug")
        st = self.session is not None and not self.running
        self.btn_run.setText(tr("Continue") if st else tr("Run as Python"))
        self.update_badge(recheck=False)                      # 1 打ごとの道: 文面はモードか文書が変わった時だけ読む
        self._update_record_title()
        self._sync_actions()
        try:
            self.ctx.get("set_title", lambda: None)()
        except Exception:                                     # noqa: BLE001
            pass

    def _update_record_title(self):
        tr = self.tr
        if self.last is None:
            self.record_title.setText(tr("Record (read-only): run the program (F5) and each op call appears here"))
            return
        text = self.edit.toPlainText() if self.active else self.py_text
        ch = first_changed_line(self.last_text or "", text)
        n = len(self.last.calls)
        hits = sum(1 for c in self.last.calls if c.cached)
        head = tr("Record (read-only): %d op call(s), %d recalculated, %d from cache") % (n, n - hits, hits)
        if ch is not None:
            head += "  ·  " + tr("⚠ out of date: the text changed from line %d — run again") % ch
        self.record_title.setText(head)

    # ---- どちらの書き方か(札・パネルの題・状態の帯) ----
    def mode_name(self, mode: str | None = None) -> str:
        """モードの名前(今の言語)。"""
        return self.tr("Python") if (mode or self.mode) == MODE_PYTHON else self.tr("Pipeline")

    def mode_title(self) -> str:
        """パネルの題に出す文字列(今の言語。``Program (code) — Python``)。パネルの題の帯に状態を並べる側は、
        これを読む(英語の原文は :meth:`mode_title_en`)。"""
        return self.tr(self.mode_title_en())

    def mode_title_en(self) -> str:
        return "Program (code) \u2014 Python" if self.active else "Program (code) \u2014 Pipeline"

    def badge_text(self) -> str:
        """札の文字: 印(形)+ モードの名前。文面がモードと食い違っていれば、前に警告の印。"""
        t = "%s %s" % (BADGE_GLYPHS[self.mode], self.mode_name())
        return (BADGE_WARNING + " " + t) if self._mismatch else t

    def mode_mismatch(self, problems=None) -> str | None:
        """文面がモードと食い違っているか: ``"python_text_in_pipeline"`` / ``"pipeline_text_in_python"`` /
        ``"mixed"``(2 つの書き方が 1 つの文面に混ざっている。直す側の行は ``self._mixed_at``)/ None。
        *problems* は Python のモードの検査(``check_program``)の結果で、その ``mixed_syntax`` の行も拾う
        (渡されなければ、同じ文面で最後に検査した結果を使う)。実行しない。"""
        text = self.edit.toPlainText()
        looks, mixed = _classify(text)
        self._mixed_at = None
        if looks is not None and looks != self.mode:
            return "python_text_in_pipeline" if looks == MODE_PYTHON else "pipeline_text_in_python"
        if mixed is not None:                                 # 直す側 = 今のモードと違う書き方の行
            self._mixed_at = mixed[0] if self.active else mixed[1]
            return "mixed"
        if self.active:
            if problems is None and self._checked[0] == text:
                problems = self._checked[1]
            hits = sorted(int(p.line) for p in (problems or ()) if getattr(p, "code", None) == "mixed_syntax")
            if hits:
                self._mixed_at = hits[0]
                return "mixed"
        return None

    def set_badge_palette(self, name: str):
        """札の配色を選ぶ(``"dark"`` / ``"light"``。画面の配色に合わせて呼ぶ)。"""
        if name not in BADGE_PALETTES:
            raise ValueError("palette must be one of %s" % (sorted(BADGE_PALETTES),))
        self.badge_palette = name
        self.update_badge()

    def update_badge(self, recheck: bool = True, problems=None):
        """札・パネルの題・状態の帯・実行の入口の説明を、今のモードと文面に合わせる(モードの切り替え・ファイルを
        開く・変換・打っている最中の検査から呼ばれる。勝手にモードは変えない)。

        *recheck* が False の時(1 打ごとの ``_update_labels``)は、モードか文書が変わった時だけ文面を読み直す。
        打っている最中の読み直しは、間を置いた検査(``check_now`` / パイプラインの構文の検査)が recheck=True で
        呼ぶ(2,000 行の文面で 1 回 13 ms ほど。1 打ごとには払わない)。"""
        tr = self.tr
        key = (self.mode, id(self.edit.document()))
        if recheck or key != self._badge_key:
            self._badge_key = key
            self._mismatch = self.mode_mismatch(problems)
        fg, bg = BADGE_PALETTES[self.badge_palette][self.mode]
        border = ("2px solid %s" % BADGE_WARN_BORDER[self.badge_palette]) if self._mismatch else "0"
        self.badge.setText(self.badge_text())
        self.badge.setStyleSheet("QToolButton#program_mode_badge{color:%s;background:%s;border:%s;border-radius:3px;"
                                 "padding:2px 8px;font-weight:bold;}" % (fg, bg, border))
        if self._mismatch == "python_text_in_pipeline":
            tip = tr("The Program is in Pipeline mode, but this text looks like Python. Click for the choices "
                     "(nothing is switched by itself)")
        elif self._mismatch == "pipeline_text_in_python":
            tip = tr("The Program is in Python mode, but this text looks like a pipeline. Click for the choices "
                     "(nothing is switched by itself)")
        elif self._mismatch == "mixed":
            tip = tr("This text mixes the pipeline syntax and Python (line %d is in the other syntax). Click for the "
                     "choices (nothing is switched by itself)") % int(self._mixed_at or 1)
        elif self.active:
            tip = tr("This text is Python: F5 runs it as Python and the stage list records the run")
        else:
            tip = tr("This text is a pipeline: the stage list is the source and F5 runs the stages")
        self.badge.setToolTip(tip)
        self.badge.setAccessibleName(self.badge_text())
        self.badge.setAccessibleDescription(tip)
        # パネルの題・実行の入口の説明は言語の表に英語の原文を登録する側なので、値が変わった時(= モードが変わった時)
        # だけ送る。状態の帯は今の言語の文そのものなので毎回。
        for name, value, always in (("set_panel_title", self.mode_title_en(), False),
                                    ("status_mode", tr("Program: %s") % self.mode_name(), True),
                                    ("run_hints", self.active, False)):
            if not always and self._badge_sent.get(name, _UNSENT) == value:
                continue
            try:
                self.ctx.get(name, lambda _v: None)(value)
                self._badge_sent[name] = value
            except Exception as e:                            # noqa: BLE001 -- 表示の失敗でモードの処理を止めない
                self.state.setdefault("errors", []).append(("could not show the Program mode (%s)" % name, str(e)))

    def badge_menu(self) -> QtWidgets.QMenu:
        """札を押した時の選択肢(食い違いの時は直し方を先に。どれも利用者が選んだ時だけ動く)。"""
        tr = self.tr
        m = QtWidgets.QMenu(self.badge)
        if self._mismatch == "python_text_in_pipeline":
            m.addAction(tr("Move this text to Python mode"), self.move_text_to_python)
            m.addAction(tr("Switch to Python mode (this text stays in Pipeline mode)"),
                        lambda: self.set_mode(MODE_PYTHON))
        elif self._mismatch == "pipeline_text_in_python":
            m.addAction(tr("Convert this text to Python"), self.convert_text_in_place)
            m.addAction(tr("Switch to Pipeline mode (this text stays in Python mode)"),
                        lambda: self.set_mode(MODE_PIPELINE))
        elif self._mismatch == "mixed":
            ln = int(self._mixed_at or 1)
            m.addAction(tr("Go to line %d") % ln, lambda: self.goto_line(ln))
            if self.active:
                m.addAction(tr("Switch to Pipeline mode (this text stays in Python mode)"),
                            lambda: self.set_mode(MODE_PIPELINE))
            else:
                m.addAction(tr("Move this text to Python mode"), self.move_text_to_python)
                m.addAction(tr("Switch to Python mode (this text stays in Pipeline mode)"),
                            lambda: self.set_mode(MODE_PYTHON))
        else:
            m.addAction(tr("Switch to Pipeline mode") if self.active else tr("Switch to Python mode"), self.toggle_mode)
        self._badge_menu = m
        return m

    def _badge_clicked(self):                                # pragma: no cover - GUI (the menu is tested through badge_menu)
        m = self.badge_menu()
        m.popup(self.badge.mapToGlobal(QtCore.QPoint(0, self.badge.height())))

    def _replace_python_text(self, text: str):
        """Python のモードの文面を *text* に置き換える(1 つの編集 = Ctrl+Z の 1 回で前の文面に戻る)。"""
        cur = QtGui.QTextCursor(self.edit.document())
        cur.select(QtGui.QTextCursor.Document)
        cur.insertText(text)

    def move_text_to_python(self) -> bool:
        """パイプラインのモードにある Python らしい文面を、Python のモードへ移す(モードも切り替える)。
        開いたパイプラインのファイルから来た文面は、そのファイルの信頼を引き継ぐ(初回の実行の前に確認)。"""
        if self.active:
            return False
        text = self.edit.toPlainText()
        if self.file and self.unsaved() and not self._confirm_unsaved(self.tr("Move this text to Python mode")):
            return False
        self.set_mode(MODE_PYTHON, announce=False)
        if not self.active:
            return False
        self._note_python_text()                              # 前の文面が未確認なら覚える(Ctrl+Z で戻る)
        self._replace_python_text(text)
        self._after_text_adopted()
        self.flash(self.tr("Moved the text to Python mode (Ctrl+Z restores the previous Python text)"))
        return True

    def convert_text_in_place(self) -> bool:
        """Python のモードにあるパイプラインの書き方の文面を、その場で Python に変換する(Ctrl+Z の 1 回で戻る)。"""
        if not self.active:
            return False
        py, errs = sp.hdev_to_python(self.edit.toPlainText())
        if errs:
            self.flash(self.tr("Could not convert to Python: %s") % "; ".join(self._loc(e) for e in errs[:2]))
            return False
        self._replace_python_text(py)
        self._update_labels()
        self.update_badge()
        self.flash(self.tr("Converted the pipeline to Python (Ctrl+Z restores the previous Python text)"))
        return True

    def _after_text_adopted(self):
        """パイプラインの側から来た文面を Python の文面にした後の、由来と信頼の付け方(「Python に変換」と札の
        「Python のモードへ移す」の両方がここを通る)。置き換える**前**に :meth:`_note_python_text` を呼んでおくこと
        (前の文面が確認していないファイルの物なら、Ctrl+Z で戻った時にそう扱う)。"""
        if self.pipe_source:
            # 開いたパイプラインのファイルから作った文面: 「手で打った」扱いにしない。初回の実行の前に確認する
            # (ファイルはデータとして確認なしに開かれる。2026-11-13 レビュー H1)
            self.file, self.origin, self.session_trusted, self.saved_digest = None, "file", False, None
            self.origin_path = self.pipe_source
        else:
            self.file, self.origin, self.session_trusted, self.saved_digest = None, "typed", True, None
            self.origin_path = None
        self.last = None
        self._update_labels()
        self.update_badge()

    # ---- 信頼は文面に結び付く ----
    def _note_unconfirmed(self, text: str, origin: str, where: str | None) -> None:
        """ファイル・プロジェクトから来て、まだ確認していない文面 *text* を覚える(中身の SHA-256 で)。"""
        if origin == "typed" or self.trust.is_trusted(text, origin):
            return
        self._unconfirmed[sp.program_digest(text)] = (origin, where)

    def _note_python_text(self) -> None:
        """Python の文書の今の文面が確認していない物なら覚える(その文面を 1 回の編集で置き換える直前に呼ぶ)。"""
        if self.active and self.origin != "typed" and not self.session_trusted:
            self._note_unconfirmed(self.edit.toPlainText(), self.origin, self.file or self.origin_path)

    def _sync_trust(self, text: str) -> None:
        """今の文面 *text* が「確認していないファイルの文面」そのものなら、由来と信頼をそのファイルの物に戻す。
        文面が変わるたび(Undo / Redo も)と、実行の前に呼ぶ。戻した後に直した文面は、今までどおり確認するまで
        「ファイルから来た物」のまま(``origin`` が file / project で ``session_trusted`` が偽)。"""
        if not self._unconfirmed:
            return
        d = sp.program_digest(text)
        hit = self._unconfirmed.get(d)
        if hit is None:
            return
        origin, where = hit
        if self.trust.is_trusted(text, origin):               # 別の入口(従来のエディタなど)で確認済みになった
            del self._unconfirmed[d]
            return
        if self.origin == "typed" or self.session_trusted:
            self.origin, self.session_trusted = origin, False
            if not self.file:
                self.origin_path = where

    def _trust_confirmed(self, text: str) -> None:
        """文面 *text* を確認した(台帳にあった・確認の窓で「実行する」)。この文面と、同じ所から来た文面の覚えを
        消す(確認した後は、Undo / Redo で同じファイルの文面に戻っても聞き直さない)。"""
        self.session_trusted = True
        d, where = sp.program_digest(text), (self.file or self.origin_path)
        self._unconfirmed = {k: v for k, v in self._unconfirmed.items()
                             if k != d and (where is None or v[1] != where)}

    def title_segment(self) -> str | None:
        """窓の題の先頭(Python のモードのときだけ。プログラムの名前と未保存の印)。"""
        if not self.active:
            return None
        return self.display_name() + ("*" if self.unsaved() else "")

    # ---- モード ----
    def set_mode(self, mode: str, *, announce: bool = True):
        if mode not in MODES:
            raise ValueError("mode must be one of %s" % (MODES,))
        if mode == self.mode:
            self._sync_mode_widgets()
            return
        if self.running:
            self.flash(self.tr("A program is running: stop it first (Ctrl+F2)"))
            self._sync_mode_widgets()
            return
        self._suspend_text = True
        try:
            self._cursor_pos[self.mode] = self.edit.textCursor().position()
            if mode == MODE_PYTHON:
                self.pipe_text = self.edit.toPlainText()
                self.pipe_dirty = bool(self.state.get("code_dirty"))
                self.breakpoints_pipe = set(self.edit.breakpoints)
                self.mode = MODE_PYTHON
                self.state["code_dirty"] = False
                doc = self._python_document()
                self.edit.setDocument(doc)                    # 文書ごと差し替える: Undo の履歴はそのまま
                if doc.toPlainText() != self.py_text:         # 離れている間に入れ替わった(起動時の復元・言語の切り替え)
                    self.edit.setPlainText(self.py_text)
                self.edit.breakpoints = set(self.breakpoints_py)
                self.edit.clear_exec()
                self.warm_up()
            else:
                self.py_text = self.edit.toPlainText()
                self.breakpoints_py = set(self.edit.breakpoints)
                self._end_session()
                self.mode = MODE_PIPELINE
                self.edit.setDocument(self.doc_pipe)
                self.edit.breakpoints = set(self.breakpoints_pipe)
                self.edit.set_errors({})
                if self.pipe_dirty:
                    self.state["code_dirty"] = True           # 未適用の編集は文書に残っている
                else:
                    self.state["code_dirty"] = False
                    gen = self.ctx.get("generated_text", self.ctx["pipeline_text"])()
                    if self.edit.toPlainText().strip() != gen.strip():
                        self.ctx["sync_program"]()            # 段の列(正本)が変わっていた時だけ作り直す
            cur = self.edit.textCursor()
            cur.setPosition(max(0, min(self._cursor_pos.get(mode, 0), max(0, self.edit.document().characterCount() - 1))))
            self.edit.setTextCursor(cur)
        finally:
            self._suspend_text = False
        self._set("mode", self.mode)
        self._sync_mode_widgets()
        self.ctx.get("check", lambda: None)()
        try:
            self.ctx.get("refresh_problems", lambda: None)()
        except Exception:                                     # noqa: BLE001
            pass
        if announce:
            self.flash(self.tr("Python mode: the text is the source; the stage list records each run")
                       if self.active else self.tr("Pipeline mode: the stage list is the source"))

    def _python_document(self) -> QtGui.QTextDocument:
        """Python のモードの文書(初めて入る時に作る。持ち主はこの QObject)。"""
        if self.doc_py is None:
            d = QtGui.QTextDocument(self)
            d.setDocumentLayout(QtWidgets.QPlainTextDocumentLayout(d))
            d.setDefaultFont(self.doc_pipe.defaultFont())
            d.setPlainText(self.py_text)
            d.clearUndoRedoStacks()                           # 開いた直後は履歴が空
            d.setModified(False)
            try:
                self.ctx.get("on_text_document", lambda _d: None)(d)   # 打っている最中の検査などを、この文書にも繋ぐ
            except Exception as e:                            # noqa: BLE001
                self.state.setdefault("errors", []).append(("could not wire the Python document", str(e)))
            self.doc_py = d
        return self.doc_py

    def toggle_mode(self):
        self.set_mode(MODE_PIPELINE if self.active else MODE_PYTHON)

    def convert_to_python(self):
        """パイプラインの文面を Python にして Python のモードへ(行の位置は変えない。Undo で前の Python に戻る)。"""
        # 変換するのはパイプラインの文面(Python のモードにいるなら、正本の段の列から作り直した物)
        src = self.edit.toPlainText() if not self.active else self.ctx["pipeline_text"]()
        if self.file and self.unsaved() and not self._confirm_unsaved(self.tr("Convert to Python")):
            return False                                      # ファイルの未保存の変更は、置き換える前に聞く(文面は Ctrl+Z で戻るが、ファイルとの結び付きは切れる)
        py, errs = sp.hdev_to_python(src)
        if errs:
            self.flash(self.tr("Could not convert to Python: %s") % "; ".join(self._loc(e) for e in errs[:2]))
            return False
        self.set_mode(MODE_PYTHON, announce=False)
        if not self.active:
            return False
        self._note_python_text()                              # 前の文面が未確認なら覚える(Ctrl+Z で戻る)
        self._replace_python_text(py)                         # 1 回の Undo で前の Python の文面に戻る
        self._after_text_adopted()
        self.flash(self.tr("Converted the pipeline to Python (Ctrl+Z restores the previous Python text)"))
        return True

    def on_pipeline_opened(self, path: str | None = None):
        """パイプラインのファイルを開いた: パイプラインのモードで見せる(開いた物に合わせる)。開いたファイルを
        覚える(そこから「Python に変換」した文面は、初回の実行の前に確認する)。"""
        self.pipe_source = os.path.abspath(path) if path else "a pipeline file"
        # 開く前のパイプラインの文面への未適用の編集は、「捨てますか」に「捨てる」と答えた物: その状態を全部消す
        # (2026-11-13 第 3 回レビュー S5。残すと、モードを戻した所で捨てたはずの文面と「未適用」の印が戻った)
        self.pipe_dirty = False
        self.pipe_text = None
        self.breakpoints_pipe = set()
        self.state["code_dirty"] = False
        if self.active:
            self.set_mode(MODE_PIPELINE, announce=False)      # 未適用ではないので、段の列から文面を作り直す

    # ---- 文面の変化 ----
    def on_text_changed(self):
        if self._suspend_text:
            return
        if self.session is not None:                         # 止まった時の文面と違う: 続行は上から走り直しになる
            self.edit.set_exec_line(0)
        if self.edit.timings:                                # 前の実行の行ごとの時間は、行がずれると別の行に付く(実際の窓で見えた)
            self.edit.set_timings({})
        if self.active and self.file and self.autosave_file_mode() == "idle":
            self._file_save_timer.start(int(self.autosave_idle_s() * 1000))   # 打つたびに数え直す
        if self.active and self._unconfirmed:                 # Ctrl+Z で確認していないファイルの文面に戻ったか
            self._sync_trust(self.edit.toPlainText())
        self._update_labels()

    # ---- 検査(打っている最中) ----
    def check_now(self):
        text = self.edit.toPlainText()
        try:
            probs = sp.check_program(text, syntax=sp.SYNTAX_PYTHON, lang=self.ctx.get("lang", lambda: "en")())
        except Exception as e:                                # noqa: BLE001 -- 検査が入力を止めない
            probs = []
            self.state.setdefault("errors", []).append(("program check failed", str(e)))
        self._checked = (text, probs)
        self.update_badge(problems=probs)                     # 文面がモードと食い違っていないか(札の警告の印。混ざった行も)
        rows, per_line = problem_rows(probs, self._ptr)
        if self.last is not None and self.last_text == text and self.last.error_line and self.last.errors:
            ln = int(self.last.error_line)
            err = self._loc(self.last.errors[0])
            rows.append((ln, "✕ " + self.tr("run") + ": " + err))
            per_line[ln] = (per_line.get(ln, "") + "; " if ln in per_line else "") + err
        if rows == self.state.get("program_syntax_errors", []) and per_line == self.edit.errors():
            return
        self.state["program_syntax_errors"] = rows
        self.edit.set_errors(per_line)
        try:
            self.ctx.get("refresh_problems", lambda: None)()
        except Exception:                                     # noqa: BLE001
            pass

    # ---- 印(ブレークポイント・実行中の行・誤り)を PyEditAssist で描く ----
    def _paint_marks(self) -> bool:
        if not self.active or self.assist is None:
            return False
        a = self.assist
        a.marks.breakpoints = set(self.edit.breakpoints)
        a.marks.executing = self.edit._exec_line if self.edit._exec_line > 0 else None
        a.marks.errors = dict(self.edit.errors())
        a.refresh_decorations()
        return True

    # ---- ブレークポイント ----
    def toggle_breakpoint(self, line: int | None = None):
        ln = line if line is not None else to_line(self.edit.textCursor().blockNumber())
        self.edit.breakpoints.symmetric_difference_update({int(ln)})
        if int(ln) not in self.edit.breakpoints:
            self.conditions.pop(int(ln), None)
        self.edit._gutter.update()
        self.edit._highlight()
        return int(ln) in self.edit.breakpoints

    def set_condition(self, line: int, expr: str | None = None):
        """行 *line* に条件つきブレークポイント(*expr* が None なら聞く)。空の式で条件を外す。"""
        if expr is None:
            expr = CONDITION_HOOK(self.win, self.tr("Breakpoint condition"),
                                  self.tr("Stop at line %d only when this Python expression is true:") % line,
                                  self.conditions.get(int(line), ""))
            if expr is None:
                return None
        expr = expr.strip()
        if expr:
            try:
                compile(expr, "<condition>", "eval")
            except SyntaxError as e:
                self.flash(self.tr("Not a Python expression: %s") % (e.msg,))
                return None
            self.conditions[int(line)] = expr
            self.edit.breakpoints.add(int(line))
        else:
            self.conditions.pop(int(line), None)
        self.edit._gutter.update()
        self.edit._highlight()
        return expr

    def eventFilter(self, obj, ev):
        if obj is self.edit and ev.type() == QtCore.QEvent.FocusOut:
            # 補完の窓・メニューが一時的にフォーカスを取る時は「外れた」に数えない
            if ev.reason() not in (QtCore.Qt.PopupFocusReason, QtCore.Qt.MenuBarFocusReason) \
                    and self.autosave_file_mode() == "focus":
                self.autosave_file("focus")
            return False
        if (self.active and obj is self.edit._gutter and ev.type() == QtCore.QEvent.MouseButtonPress
                and ev.button() == QtCore.Qt.RightButton):
            y = ev.position().y() if hasattr(ev, "position") else ev.y()
            ln = to_line(self.edit.cursorForPosition(QtCore.QPoint(1, int(y))).blockNumber())
            m = QtWidgets.QMenu(self.edit)
            m.addAction(self.tr("Toggle breakpoint (F9)"), lambda: self.toggle_breakpoint(ln))
            m.addAction(self.tr("Breakpoint condition…"), lambda: self.set_condition(ln))
            if ln in self.conditions:
                m.addAction(self.tr("Remove the condition"), lambda: self.set_condition(ln, ""))
            self._gutter_menu = m
            m.popup(ev.globalPosition().toPoint() if hasattr(ev, "globalPosition") else ev.globalPos())
            return True
        return False

    # ---- 実行 ----
    def _input_image(self):
        img = getattr(self.model, "image", None)
        if img is None:
            img = self.ctx["demo_image"]()
        return img

    def _check_trust(self, text: str) -> bool:
        self._sync_trust(text)                                # 文面そのものが未確認のファイルの物なら、由来に関わらず確認する
        if self.origin == "typed" or self.session_trusted:
            return True
        if self.trust.is_trusted(text, self.origin):
            self._trust_confirmed(text)
            return True
        where = self.file or (self.origin_path if self.origin_path and os.path.isabs(self.origin_path)
                              else None)
        if not self.confirm_file_program(text, where):
            self._out(self.tr("Not run: this program came from a file and was not confirmed."))
            return False
        self._trust_confirmed(text)
        return True

    def confirm_file_program(self, text: str, where: str | None = None) -> bool:
        """ファイルから来た Python の文面 *text* を走らせてよいか。確認済み(中身の SHA-256 が台帳にある)なら True、
        そうでなければ確認の窓を出し、「実行する」なら台帳に足して True。Python のモードと、従来の Python
        エディタ(ドラッグ&ドロップ・開くで開いた .py)が同じ台帳と同じ窓を使う。"""
        if self.trust.is_trusted(text, "file"):
            return True
        ok = TRUST_HOOK(self.win, self.tr("Run this Python program?"),
                        self.tr("This program came from %s.\n\nPython runs on this PC with your permissions: "
                                "it can read and change files. Run it only if you trust it.\n\n"
                                "Studio remembers your answer for this exact text; if the file changes, "
                                "it asks again.") % (where or self.tr("a file")))
        if not ok:
            self.flash(self.tr("Not run: the program was not confirmed"))
            return False
        self.trust.trust(text)
        return True

    def run(self):
        """F5: 止まっていれば続行、そうでなければ上から実行。"""
        if self.session is not None and self.config == "debug":
            return self._start("continue")
        return self._start("run")

    def step(self):
        if self.config != "debug":
            self.flash(self.tr("Release cannot step line by line: switch to Debug"))
            return False
        return self._start("step")

    def _start(self, action: str):
        if self.running:
            self.flash(self.tr("A program is already running: press Stop (Ctrl+F2) first"))
            return False
        if not self.active:
            # パイプラインのモードの文面(段の列の表示 + ファイルから来た指示の行)を Python として走らせない。
            # 指示の行は Python としても読めるので、ここを通すと確認なしに走る(2026-11-13 レビュー H1 の別の入口)
            self.flash(self.tr("Not run: the Program is in Pipeline mode (switch to Python mode to run Python)"))
            return False
        if self._blocked_by_abandoned_run():
            return False
        text = self.edit.toPlainText()
        syn, errs = sp.detect_syntax(text)
        if not self._check_trust(text):
            return False
        plan = run_plan(action, self.session, text, self.edit.breakpoints, self.conditions)
        if plan["resume"]:
            return self._resume(plan)
        if plan["restart"]:
            self._out(self.tr("The program changed since it stopped: running again from the top"))
        if self.session is not None:
            self._end_session()                               # 止まって待っている実行を終えてから、上から走る
        stop = threading.Event()
        gate = PauseGate(stop) if self.config == "debug" else None
        root = self.ctx.get("project_root", lambda: None)()
        stages = [tuple(s[:3]) for s in getattr(self.model, "stages", []) if not (len(s) > 3 and s[3])]
        kw = dict(trusted=True, syntax=sp.SYNTAX_PYTHON, memo=self.memo, time_limit_s=self.time_limit_s(),
                  breakpoints=plan["breakpoints"], conditions=plan["conditions"],
                  resume_after_lines=plan["resume_after_lines"], max_lines=plan["max_lines"], stop_event=stop,
                  current_stages=stages, config=self.config, project_dir=root,
                  program_dir=os.path.dirname(self.file) if self.file else None, filename=self.file,
                  pause_hook=gate.hook if gate is not None else None)
        image = self._input_image()
        self.job = RunJob("program", lambda: sp.run_program(text, image, **kw), stop,
                          {"text": text, "action": action, "config": self.config, "stdout_n": 0, "notes_n": 0},
                          gate=gate).start()
        self.state["pymode_runs"] = self.state.get("pymode_runs", 0) + 1
        self._out_header(action)
        left = sp.program_threads()
        if left:                                              # 前の実行が起こしたスレッドがまだ動いている: 知らせてから走る
            self._out("⚠ " + self.tr("Threads started by an earlier run are still running (%s): they can change "
                                     "files, the environment and the working folder while this program runs")
                      % ", ".join(left[:5]))
        self._status(self.tr("running…"))
        self._update_labels()
        self._poll.start()
        return True

    def _blocked_by_abandoned_run(self) -> bool:
        """止められずに残した実行がまだ動いていれば、次の実行を始めずにそう言う(残った実行は環境変数や作業
        フォルダを書き換え続けるので、重ねて走らせない。2026-11-13 レビュー H3)。"""
        left = sp.abandoned_runs()
        if not left:
            # 変数・ウォッチの欄が利用者のコード(__repr__・式)のために起こして、止まらずに残っているスレッド。
            # 止めの例外が保留のまま残ると Debug の実行が約 300 倍遅くなり、何もしないプログラムが時間切れになる
            # (2026-11-13 第 2 回レビュー R5)。残っている間は始めずに、そう言う
            stray = self._stray_value_threads()
            if not stray:
                return False
            msg = self.tr("Not run: a value in the Variables or Watch panel is still running its own code in the "
                          "background (%d) — wait until it ends or restart Studio") % stray
            self._out("✕ " + msg)
            self._status("✕ " + msg)
            self.flash(msg)
            return True
        msg = self._loc(sp.ABANDONED_BLOCKS_RUN % len(left))
        self._out("✕ " + msg)
        self._status("✕ " + msg)
        self.flash(msg)
        return True

    @staticmethod
    def _stray_value_threads() -> int:
        try:
            import studio_pyedit_values as pv
            return len(pv.stray_threads())
        except Exception:                                     # noqa: BLE001
            return 0

    def _resume(self, plan: dict) -> bool:
        """止まって待っている実行を起こす(続行・1 行実行)。**止まった所から続く**: 上から走り直さない。"""
        sess, self.session = self.session, None
        job = sess.job
        job.meta["action"] = plan["resume"]
        self.job = job
        self.edit.set_exec_line(0)
        job.gate.resume(plan["resume"], plan["breakpoints"], plan["conditions"])
        self._out_header(plan["resume"])
        self._status(self.tr("running…"))
        self._update_labels()
        self._poll.start()
        return True

    def stop(self):
        """Ctrl+F2: 走っていれば止める。止まっている(ブレークポイント)なら Debug の区切りを終える。"""
        if self.job is not None:
            self.job.stop_event.set()
            self._status(self.tr("stop requested…"))
            self.flash(self.tr("Stop requested"))
            return True
        if self.session is not None:
            self._end_session()
            self.flash(self.tr("Debugging ended"))
            return True
        return False

    def reset(self):
        self._end_session()
        self.edit.clear_exec()
        self._show_value(self._input_image())

    def _end_session(self):
        """Debug の区切りを終える。止まって待っている実行があれば止めて、終わるのを待つ(待っているだけなので
        すぐ終わる。実行の前後で戻す物 = sys.path・作業フォルダが、次の実行と重ならないように待つ)。"""
        sess, self.session = self.session, None
        job = getattr(sess, "job", None)
        if job is not None and not job.done:
            job.stop_event.set()
            job.thread.join(2.0)
        self.edit.clear_exec()
        self._update_labels()

    def run_selection(self):
        """選んだ行(選びが無ければカーソルの行)だけを、直前の実行の名前空間で実行する。"""
        if self.running:
            self.flash(self.tr("A program is already running: press Stop (Ctrl+F2) first"))
            return False
        if not self.active:
            self.flash(self.tr("Not run: the Program is in Pipeline mode (switch to Python mode to run Python)"))
            return False
        cur = self.edit.textCursor()
        doc = self.edit.document()
        b1 = doc.findBlock(cur.selectionStart())
        b2 = doc.findBlock(cur.selectionEnd())
        if cur.hasSelection() and b2.blockNumber() > b1.blockNumber() and cur.selectionEnd() == b2.position():
            b2 = b2.previous()
        lines = []
        b = b1
        while b.isValid() and b.blockNumber() <= b2.blockNumber():
            lines.append(b.text())
            b = b.next()
        import textwrap
        src = textwrap.dedent("\n".join(lines)).strip("\n")
        if not src.strip():
            self.flash(self.tr("No code in the selected lines"))
            return False
        if self._blocked_by_abandoned_run():
            return False
        if not self._check_trust(self.edit.toPlainText()):
            return False
        ns = self.namespace
        if ns is None:
            ns = self._fresh_namespace()
            self.namespace = ns
        stop = threading.Event()
        lim = self.time_limit_s()
        self.job = RunJob("selection", lambda: sp.evaluate(src, ns, time_limit_s=lim, stop_event=stop), stop,
                          {"lines": (to_line(b1.blockNumber()), to_line(b2.blockNumber())), "src": src}).start()
        self._out(self.tr("▶ run lines %d–%d (in the last run's names)") % self.job.meta["lines"])
        self._update_labels()
        self._poll.start()
        return True

    def _fresh_namespace(self) -> dict:
        import builtins
        ns = dict(sp.prelude_namespace())
        rec = sp.Recorder(memo=self.memo)
        inp = rec.set_input(self._input_image())
        ns.update(__name__="__studio_program__", __builtins__=builtins, img=inp, image=inp, __studio_recorder__=rec)
        return ns

    def _user_values(self, ns: dict) -> dict:
        if self._prelude_keys is None:
            self._prelude_keys = set(sp.prelude_namespace(include_heavy=False)) | {"fs"}
        out = {}
        for k, v in ns.items():
            if type(k) is not str or k.startswith("_") or issubclass(type(v), types.ModuleType):
                continue                                      # 型だけで決める(メタクラスの __name__ を読まない)
            rec = ns.get("__studio_recorder__")
            if k == "print" or (k == "image" and (v is ns.get("img") or (rec is not None and v is rec.input))):
                continue                                      # 取り込みの print と img の別名は変数の一覧に出さない
            if k in self._prelude_keys and k not in ("img", "image") and callable(v):
                continue
            out[k] = v
        return out

    def _poll_job(self):
        job = self.job
        if job is None:
            self._poll.stop()
            return
        if not job.done:
            gate = job.gate
            snap = gate.snapshot if gate is not None else None
            if snap is not None:                              # ブレークポイント・1 行実行で止まって待っている
                gate.snapshot = None
                self.job = None
                self._poll.stop()
                try:
                    self._program_done(job, snap)
                finally:
                    self._update_labels()
            return
        self.job = None
        self._poll.stop()
        try:
            if job.exc is not None:
                self._out("✕ " + self.tr("internal error: %s") % job.exc)
                self._status(self.tr("internal error: %s") % job.exc)
            elif job.kind == "selection":
                self._selection_done(job)
            else:
                self._program_done(job)
        finally:
            self._update_labels()

    def _selection_done(self, job):
        r = job.result or {}
        if r.get("stdout"):
            self._out(r["stdout"].rstrip("\n"))
        for n in r.get("notes") or ():                        # F5 と同じ知らせ(戻した状態・plt.show()・残ったスレッド)
            self._out("ℹ " + self._loc(n))
        shown = r.get("shown")
        not_shown = None
        if shown is not None:                                 # 選んだ行の show() / plt.show() は、F5 と同じく画像の欄へ
            not_shown = self._show_value(shown)
        if r.get("error"):
            l1 = job.meta["lines"][0]
            err = r["error"]
            m = re.match(r"line (\d+):", err)
            if m:
                err = "line %d:%s" % (l1 + int(m.group(1)) - 1, err[m.end():])
            err = self._loc(err)
            self._out("✕ " + err)
            self._status("✕ " + err)
        else:
            v = r.get("value")
            if v is not None:
                kind, shape, summ = sp.describe_value(v)
                self._out("= " + summ)
                if shown is None and _is_image(v):
                    self._show_value(v)
            self._status(self.tr("ran lines %d–%d") % job.meta["lines"])
        self._refresh_variables(self.namespace)
        self.flash(not_shown or self.tr("ran lines %d–%d") % job.meta["lines"])

    def _loc(self, text: str) -> str:
        """実行系・検査の英語の文を UI の言語へ(型に当たらない文 = Python 自身の例外の文などはそのまま)。"""
        return spi.localize(text, self._ptr)

    def _program_done(self, job, res=None):
        """実行が終わった(*res* なし)か、ブレークポイント・1 行実行で止まって待っている(*res* = その時点の結果)。"""
        waiting = res is not None
        res = res if waiting else job.result
        tr = self.tr
        text = job.meta["text"]
        self.last, self.last_text = res, text
        if res.namespace is not None:
            self.namespace = res.namespace
        total = int(getattr(res, "stdout_total", 0) or len(res.stdout))
        fresh = total - job.meta.get("stdout_n", 0)           # 止まるたびに、前に出した分は出し直さない
        new_out = "" if fresh <= 0 else res.stdout if fresh >= len(res.stdout) else res.stdout[-fresh:]
        job.meta["stdout_n"] = total
        if new_out:
            head, sep, rest = new_out.partition("\n")         # 先頭の「前の出力は捨てた」の 1 行は UI の言語で
            self._out((self._loc(head) + sep + rest).rstrip("\n"))
        for n in res.notes[job.meta.get("notes_n", 0):]:
            self._out("ℹ " + self._loc(n))
        job.meta["notes_n"] = len(res.notes)
        for e in res.errors:
            self._out("✕ " + self._loc(e))
        # 記録・絵・変数
        self._fill_record(res)
        not_shown = None
        if res.ran and res.output is not None and not res.not_run_reason:
            not_shown = self._show_value(res.output)
        paused = res.stopped in ("breakpoint", "step")
        self._refresh_variables(res.namespace, res.locals if paused else None)
        self.edit.set_timings(per_line_ms(res.calls))
        if paused:
            self.session = DebugSession(text, res.lines_run, int(res.stopped_line or 0), res.stopped,
                                        job=job if waiting else None)
            self.edit.set_exec_line(int(res.stopped_line or 0))
            self.edit.goto_line(int(res.stopped_line or 1), focus=False)
            cond = self.conditions.get(int(res.stopped_line or 0))
            msg = (tr("stopped at line %d (breakpoint)") % res.stopped_line if res.stopped == "breakpoint"
                   else tr("stopped at line %d (step)") % res.stopped_line)
            func = res.stack[0][0] if res.stack else ""
            if func and not func.startswith("<"):
                msg += "  ·  " + tr("in %s(): its local variables are listed too") % func
            if cond and res.stopped == "breakpoint":
                msg += "  ·  " + tr("condition: %s") % cond
            msg += "  ·  " + tr("F5 continue, F6 step, Ctrl+F2 stop")
        else:
            self.session = None
            self.edit.clear_exec()
            self.edit.set_timings(per_line_ms(res.calls))
            if res.errors:
                msg = "✕ " + self._loc(res.errors[0])
            else:
                hits = sum(1 for c in res.calls if c.cached)
                msg = tr("ran in %.0f ms (%s)  ·  %d op call(s), %d from cache") % (
                    res.elapsed_s * 1000.0, tr("Debug") if res.config == "debug" else tr("Release"),
                    len(res.calls), hits)
        if not (res.errors and not paused):                   # 誤りの文は上で出力の欄へ書いた(2 度書かない)
            self._out(msg)
        self._status(msg)
        for n in res.notes:
            if n.startswith("Release does not stop"):
                self.flash(tr("Release does not stop at breakpoints: switch to Debug to use them"))
                break
        else:
            self.flash(msg)
        if not_shown:                                         # 「画像ではないので出していない」は状態の帯にも出す
            self.flash(not_shown)
        self.check_now()                                      # 実行時の誤りの行を Problems・波線へ

    def _fill_record(self, res):
        self.record.clear()
        try:
            import studio_pyedit_vars_qt as vq
        except Exception:                                     # noqa: BLE001
            vq = None
        for c in res.calls:
            it = QtWidgets.QListWidgetItem(call_row_text(c, self.tr))
            it.setData(QtCore.Qt.UserRole, c.index)
            it.setToolTip(self.tr("line %d: click to show this result and go to the line") % c.line)
            if vq is not None and c.value is not None and _is_image(c.value):
                pm = vq.pixmap_for(c.value, 32)
                if pm is not None:
                    it.setIcon(QtGui.QIcon(pm))
            if c.cached:
                it.setForeground(QtGui.QColor("#8b91a0"))
            self.record.addItem(it)
        if not res.calls:
            hint = QtWidgets.QListWidgetItem(self.tr("— no op calls in this run —"))
            hint.setFlags(QtCore.Qt.NoItemFlags)
            self.record.addItem(hint)
        self._update_record_title()

    def _record_clicked(self, item):
        idx = item.data(QtCore.Qt.UserRole)
        if self.last is None or idx is None:
            return
        calls = [c for c in self.last.calls if c.index == idx]
        if not calls:
            return
        c = calls[0]
        if c.value is not None:
            self._show_value(c.value)
        self.goto_line(c.line)

    def _refresh_variables(self, ns, frame_locals=None):
        """変数の欄を作り直す。*frame_locals* = 止まった所が関数の中のときの、その枠の局所変数(同じ名前の
        モジュールの変数より優先 = その行から見える値)。"""
        if self.vars is None or self.var_source is None:
            return
        vals = self._user_values(ns) if isinstance(ns, dict) else {}
        shown_locals = {k: v for k, v in (frame_locals or {}).items() if not k.startswith("__")}
        vals.update(shown_locals)
        self._frame_local_names = set(shown_locals)
        self.var_source.ns = vals
        try:
            self.vars.refresh()
        except Exception as e:                                # noqa: BLE001
            self.state.setdefault("errors", []).append(("variables refresh failed", str(e)))
        if not self.state.get("pymode_vars_shown"):
            self.state["pymode_vars_shown"] = True
            self.ctx.get("show_panel", lambda _n: None)("variables")

    def _show_value(self, v) -> str | None:
        """値を画像の欄へ出す。出さなかった時は、その理由の 1 行(出力の欄に書いた文)を返す(呼び出し側が状態の帯にも
        出す)。出した時・値が None の時は None。"""
        import numpy as np
        if type(v) is not np.ndarray or v.dtype.kind not in _DISPLAYABLE_KINDS:
            # 画面の側(GUI のスレッド)は**数の素の配列**だけを受け取る。
            # * 利用者のクラスの物・派生した配列を表示の処理へ渡すと、その ``__class__`` / ``__array__`` などが GUI の
            #   スレッドで走る(第 2 回レビュー R1)。
            # * 数でない配列(object・文字列・日付・構造体)は、表示の処理が ``np.isfinite`` などで落ち、毎回
            #   「Display error」のモーダルの窓が出た(第 3 回レビュー S8)。窓は出さず、1 行で言う。
            if v is None:
                return None
            note = self.tr("The shown value is not an image (%s): nothing is displayed") % sp.describe_value(v)[2]
            self._out("ℹ " + note)
            return note
        try:
            self.ctx["show_value"](v)
        except Exception as e:                                # noqa: BLE001 -- 表示の失敗で実行の結果を失わない
            self._out("⚠ " + self.tr("could not display the result: %s") % e)
        return None

    def goto_line(self, ln: int):
        self.edit.goto_line(int(ln))

    # ---- 出力の欄 ----
    def _status(self, msg: str, limit: int = 110):
        """Program 欄の状態行(1 行。長い文は切り、全文はツールチップへ)。長い文のままだと欄の最小幅が広がり、
        上の帯の右側(実行・止める)が窓の外へ押し出された(実際の窓で見えた)。"""
        lab = self.ctx["status"]
        one = " ".join(str(msg).split())
        lab.setText(one if len(one) <= limit else one[:limit - 1] + "\u2026")
        tip = str(msg)                                        # ツールチップにも上限(20 MB の文で画面が数秒止まった)
        lab.setToolTip(tip if len(tip) <= MAX_TOOLTIP_CHARS else tip[:MAX_TOOLTIP_CHARS] + "\u2026")

    def _out(self, text: str):
        if len(text) > MAX_OUTPUT_CHARS:                      # 1 回の書き込みが大きすぎる: 末尾だけ(画面を固めない)
            cut = len(text) - MAX_OUTPUT_CHARS
            text = self.tr("… (%d earlier characters not shown)") % cut + "\n" + text[-MAX_OUTPUT_CHARS:]
        self.output.appendPlainText(text)
        sb = self.output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _out_header(self, action):
        name = {"run": self.tr("Run"), "continue": self.tr("Continue"), "step": self.tr("Step")}[action]
        # どの書き方として走った結果かを見出しに残す(この欄は Python のモードの実行だけが書く)
        self._out("── %s  %s  (%s · %s)  %s" % (name, self.display_name(), self.tr("Python"),
                                                    self.tr("Debug") if self.config == "debug" else self.tr("Release"),
                                                    time.strftime("%H:%M:%S")))

    def clear_output(self):
        self.output.clear()

    def clear_output_asked(self):
        """「出力を消す」の入口: 消した出力は戻らないので、空でなければ先に聞く。"""
        n = self.output.document().blockCount() if self.output.toPlainText() else 0
        if n and not self._confirm(self.tr("Clear output"),
                                   self.tr("The Output pane has %d line(s) of print output, notes and errors from the "
                                           "runs so far. Clearing erases them; they cannot be brought back.") % n,
                                   self.tr("Clear the output")):
            return False
        self.clear_output()
        return True

    def set_config(self, config: str):
        if config not in sp.CONFIGS:
            raise ValueError(config)
        self.config = config
        self.config_box.blockSignals(True)
        self.config_box.setCurrentIndex(sp.CONFIGS.index(config))
        self.config_box.blockSignals(False)
        if config == "release":
            self._end_session()
            if self.edit.breakpoints and self.active:
                self.flash(self.tr("Release does not stop at breakpoints: switch to Debug to use them"))
        self._set("config", config)
        self._update_labels()

    # ---- ファイル ----
    def _confirm(self, title: str, text: str, action: str) -> bool:
        """やり直しの効かない操作の前に聞く(studio.confirm_action。繋がっていなければ実行しない側)。"""
        return bool(self.ctx.get("confirm_action", lambda *_a: False)(title, text, action))

    def _confirm_unsaved(self, title) -> bool:
        if not self.unsaved():
            return True
        ans = SAVE_HOOK(self.win, title, self.tr("The Python program %s has unsaved changes. Save them?")
                        % self.display_name())
        if ans == "save":
            return self.save()
        return ans == "discard"

    def new_program(self):
        if not self._confirm_unsaved(self.tr("New program")):
            return False
        self._load_text(self._new_text(), None, "typed")
        return True

    def open_example(self):
        if not self._confirm_unsaved(self.tr("Open the example")):
            return False
        self._load_text(self._starter(), None, "typed")
        return True

    def open_program(self, path: str | None = None, origin: str | None = None):
        """``.py`` を Program 欄に開く(Python のモードへ)。**開いただけでは実行しない**。"""
        if path is None:
            start = self.ctx.get("proj_path", lambda k, d="": d)("python")
            path = OPEN_HOOK(self.win, self.tr("Open Python program"), start)
            if not path:
                return False
        if not self._confirm_unsaved(self.tr("Open Python program")):
            return False
        try:
            with open(path, "rb") as fh:
                raw = fh.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise OSError("the file is larger than 4 MB")
            text = raw.decode("utf-8-sig")
        except (OSError, UnicodeDecodeError) as e:
            self.ctx.get("report_error", lambda t, x: self.flash(str(x)))(self.tr("Could not open file"),
                                                                           "%s\n\n%s" % (path, e))
            return False
        if origin is None:
            root = self.ctx.get("project_root", lambda: None)()
            inside = root and os.path.normcase(os.path.abspath(path)).startswith(os.path.normcase(os.path.abspath(root)) + os.sep)
            origin = "project" if inside else "file"
        self._load_text(text.replace("\r\n", "\n"), os.path.abspath(path), origin, stamp=_bytes_stamp(raw))
        self.flash(self.tr("opened %s (not run: F5 runs it after you confirm it once)") % os.path.basename(path))
        return True

    def _load_text(self, text, path, origin, stamp=None):
        """文面を Program 欄に入れる。*stamp* = *path* から読んだ生のバイトの印(:func:`_bytes_stamp`)。"""
        if not self.active:
            self.set_mode(MODE_PYTHON, announce=False)
        self._end_session()
        self._suspend_text = True
        try:
            self.edit.setPlainText(text)
        finally:
            self._suspend_text = False
        self.py_text = text
        self.file = path
        self._disk_stamp = stamp if path else None
        self._file_save_timer.stop()
        self._conflict_told = None
        self.autosave_note.setText("")
        self.autosave_note.setToolTip("")
        self.origin_path = None
        self.origin = origin
        self.session_trusted = origin == "typed"
        self._note_unconfirmed(text, origin, path)            # 確認するまで、この文面そのものは「ファイルから来た物」
        self.saved_digest = sp.program_digest(text) if path else None
        self.edit.breakpoints = set()
        self.conditions = {}
        self.last = None
        self.record.clear()
        self.edit.clear_exec()
        self._set("file", path or "")
        self._update_labels()
        self.ctx.get("check", lambda: None)()

    def save(self) -> bool:
        if not self.file:
            return self.save_as()
        if self.disk_changed() and not self._confirm(
                self.tr("Save Python program"),
                self.tr("%s was changed on disk by another program after Studio read it. Saving replaces that "
                        "version with the text in the Program; it cannot be brought back.")
                % os.path.basename(self.file), self.tr("Overwrite the file")):
            return False
        return self._write(self.file)

    def save_as(self) -> bool:
        start = self.file or self.ctx.get("proj_path", lambda k, d="": d)("python", "program.py")
        path = SAVE_AS_HOOK(self.win, self.tr("Save Python program as"), start)
        if not path:
            return False
        if not path.lower().endswith(".py"):
            path += ".py"
            # 保存の窓は打った名前で「上書きしますか」を確かめた。拡張子を足した後の名前は確かめていない
            if os.path.exists(path) and not self._confirm(
                    self.tr("Save Python program as"),
                    self.tr("%s already exists. Saving replaces it; the old file cannot be brought back.")
                    % os.path.basename(path), self.tr("Overwrite the file")):
                return False
        return self._write(path)

    def _write(self, path) -> bool:
        text = self.edit.toPlainText() if self.active else self.py_text
        try:
            atomic_write_text(path, text)
        except OSError as e:
            self.ctx.get("report_error", lambda t, x: self.flash(str(x)))(self.tr("Could not save"),
                                                                           "%s\n\n%s" % (path, e))
            return False
        self.file = os.path.abspath(path)
        self.saved_digest = sp.program_digest(text)
        self._disk_stamp = _bytes_stamp(text.encode("utf-8"))   # 今ディスクに在るのは、自分で書いたこのバイト列
        if self.session_trusted:
            self.trust.trust(text)                            # 自分で保存した中身は、次に開いても確認しない
        self._set("file", self.file)
        self._update_labels()
        self.flash(self.tr("saved %s") % os.path.basename(path))
        return True

    # ---- 入口(メニュー・パレット・キー。ボタンは Program 欄の上) ----
    def install_actions(self):
        """入口を足す(UX 規則 §1): メニュー(File / Program / Run)・コマンドパレット(別名つき)・キー。
        F5 / F6 / Shift+F5 は既存の「Run all / Step / Reset」が Python のモードの間こちらへ回す(同じキーを
        2 つの動作に割り当てると Qt はどちらも撃たない)。"""
        ctx, tr, win = self.ctx, self.tr, self.win
        act, menus, actions = ctx["act"], ctx["menus"], ctx["actions"]
        words = ctx.get("palette_words", {})
        self.actions = {}
        self._action_texts = []
        self._menu_titles = []

        def mk(key, text, keys, tip, fn, menu, alias="", checkable=False, py_only=False):
            a = act(text, None, tip)
            if keys:
                a.setShortcuts([QtGui.QKeySequence(k) for k in keys])
                a.setShortcutContext(QtCore.Qt.WindowShortcut)
                win.addAction(a)
            a.setCheckable(checkable)
            a.triggered.connect(lambda _=False, f=fn: f())
            if menu is not None:
                menu.addAction(a)
            actions[key] = a
            self.actions[key] = (a, py_only)
            self._action_texts.append((a, text, tip))
            if alias:
                words[key] = alias
            return a

        run_menu = menus.get("run")
        pm = QtWidgets.QMenu(tr("Program mode"), run_menu if run_menu is not None else win)
        if run_menu is not None:
            run_menu.insertMenu(run_menu.actions()[0] if run_menu.actions() else None, pm)
            run_menu.insertSeparator(run_menu.actions()[1] if len(run_menu.actions()) > 1 else None)
        else:
            win.menuBar().addMenu(pm)
        menus["program"] = pm
        self._menu_titles.append((pm, "Program mode"))
        mode_alias = "python パイソン スクリプト script 変数 variable 分岐 ループ loop if while for モード mode"
        self.act_py = mk("pymode_python", "Python mode", None,
                         "The Program text is the source; F5 runs it as Python and the stage list records the run",
                         lambda: self.set_mode(MODE_PYTHON), pm, mode_alias, checkable=True)
        self.act_pipe = mk("pymode_pipeline", "Pipeline mode", None,
                           "The stage list is the source; the Program shows it as code (HDevelop style)",
                           lambda: self.set_mode(MODE_PIPELINE), pm, "パイプライン pipeline 段 stage hdevelop モード mode",
                           checkable=True)
        g = QtGui.QActionGroup(win)
        g.setExclusive(True)
        g.addAction(self.act_py)
        g.addAction(self.act_pipe)
        self._mode_actions = g
        mk("pymode_toggle", "Switch Python / Pipeline mode", ["Ctrl+Alt+M"],
           "Switch the Program between Python mode and Pipeline mode (each keeps its own text)",
           self.toggle_mode, pm, mode_alias + " 切り替え switch")
        mk("pymode_convert", "Convert to Python", None,
           "Turn the pipeline into an equivalent Python program (same line numbers) and switch to Python mode",
           self.convert_to_python, pm, "変換 python にする convert パイソン スクリプト")
        pm.addSeparator()
        self.act_debug = mk("pymode_debug", "Debug", None, "Run with the line hook: breakpoints and steps work",
                            lambda: self.set_config("debug"), pm, "デバッグ debug ブレークポイント breakpoint",
                            checkable=True, py_only=True)
        self.act_release = mk("pymode_release", "Release", None,
                              "Run without the line hook (faster); breakpoints do not stop",
                              lambda: self.set_config("release"), pm, "リリース release 速い fast",
                              checkable=True, py_only=True)
        g2 = QtGui.QActionGroup(win)
        g2.setExclusive(True)
        g2.addAction(self.act_debug)
        g2.addAction(self.act_release)
        self._config_actions = g2
        mk("pymode_config_toggle", "Switch Debug / Release", ["Ctrl+Alt+D"],
           "Switch the Python run between Debug and Release",
           lambda: self.set_config("release" if self.config == "debug" else "debug"), pm,
           "デバッグ リリース debug release 切り替え", py_only=True)
        pm.addSeparator()
        start = QtWidgets.QMenu(tr("Start Studio in"), pm)
        pm.addMenu(start)
        self._start_menu = start
        self._menu_titles.append((start, "Start Studio in"))
        g3 = QtGui.QActionGroup(win)
        g3.setExclusive(True)
        cur = str(self._get("start", "last"))
        for val, label in (("last", "The last mode"), (MODE_PYTHON, "Python mode"), (MODE_PIPELINE, "Pipeline mode")):
            a = QtGui.QAction(tr(label), win)
            a.setCheckable(True)
            a.setChecked(val == cur)
            a.setToolTip(tr("Which mode the Program is in when Studio starts"))
            self._action_texts.append((a, label, "Which mode the Program is in when Studio starts"))
            a.triggered.connect(lambda _=False, v=val: self._set("start", v))
            g3.addAction(a)
            start.addAction(a)
        self._start_group = g3
        auto = QtWidgets.QMenu(tr("Autosave to the file"), pm)
        pm.addMenu(auto)
        self._menu_titles.append((auto, "Autosave to the file"))
        g4 = QtGui.QActionGroup(win)
        g4.setExclusive(True)
        tip = ("Save the Python file by itself while you type. Off by default. A program that has no file yet is "
               "only kept in the crash-recovery backup; a file changed by another program is never overwritten")
        for key, mode, label in (("pymode_autosave_off", "off", "Autosave: off"),
                                 ("pymode_autosave_idle", "idle", "Autosave: after a pause in typing"),
                                 ("pymode_autosave_focus", "focus", "Autosave: when the Program loses the focus")):
            a = mk(key, label, None, tip, lambda m=mode: self.set_autosave_file(m), auto,
                   "自動保存 autosave auto save 保存 ファイル file", checkable=True)
            g4.addAction(a)
            self._autosave_actions[mode] = a
        self._autosave_group = g4
        self._sync_autosave_actions()
        mk("pymode_example", "Open the Python example", None,
           "Put the example program (a sample image, four ops, a variable and an if) into the Program",
           self.open_example, pm, "例 example sample サンプル python")
        mk("pymode_clear_output", "Clear output", None, "Clear the Output pane under the Program",
           self.clear_output_asked, pm, "出力 output 消す clear", py_only=True)
        # File
        fm = menus.get("file")
        sep_before = fm.actions()[0] if fm is not None and fm.actions() else None
        new_a = mk("pymode_new", "New Python program", ["Ctrl+N"], "Start a new Python program in the Program",
                   self.new_program, None, "新規 new python プログラム program")
        open_a = mk("pymode_open", "Open Python program…", ["Ctrl+Alt+O"],
                    "Open a .py file in the Program (Python mode). It does not run until you confirm it once",
                    lambda: self.open_program(), None, "開く open python .py プログラム program")
        save_a = mk("pymode_save", "Save Python program", ["Ctrl+Alt+S"], "Save the Python program (.py)",
                    self.save, None, "保存 save python .py プログラム program", py_only=True)
        saveas_a = mk("pymode_save_as", "Save Python program as…", ["Ctrl+Alt+Shift+S"],
                      "Save the Python program under a new name (.py)",
                      self.save_as, None, "名前を付けて保存 save as python .py", py_only=True)
        if fm is not None:
            for a in (new_a, open_a, save_a, saveas_a):
                fm.insertAction(sep_before, a)
            fm.insertSeparator(sep_before)
        # Run
        if run_menu is not None:
            run_menu.addSeparator()
        mk("pymode_run", "Run Python program", None, "Run the Python program (also F5; continue when stopped)",
           self.run, run_menu, "実行 run python プログラム program F5", py_only=True)
        mk("pymode_step", "Step one line", None, "Step: run one line and stop (also F6; Debug only)",
           self.step, run_menu, "1 行 step ステップ デバッグ", py_only=True)
        mk("pymode_stop", "Stop the program", ["Ctrl+F2"], "Stop the running Python program",
           self.stop, run_menu, "止める stop 停止 中断 無限ループ", py_only=True)
        mk("pymode_breakpoint", "Toggle breakpoint", ["F9"], "Set or clear a breakpoint on the cursor line",
           lambda: self.toggle_breakpoint(), run_menu, "ブレークポイント breakpoint 止める所")
        mk("pymode_condition", "Breakpoint condition…", None,
           "Stop at the cursor line only when a Python expression is true",
           lambda: self.set_condition(to_line(self.edit.textCursor().blockNumber())), run_menu,
           "条件 condition ブレークポイント breakpoint", py_only=True)
        self._sync_actions()

    def _sync_actions(self):
        acts = getattr(self, "actions", None)
        if not acts:
            return
        self.act_py.setChecked(self.active)
        self.act_pipe.setChecked(not self.active)
        self.act_debug.setChecked(self.config == "debug")
        self.act_release.setChecked(self.config == "release")
        for a, py_only in acts.values():
            if py_only:
                a.setEnabled(self.active)
        run = acts.get("pymode_run")
        if run is not None:      # Python のモードでは Run メニューの「Python として実行」(= Run all。F5 / Ctrl+Return)と
            run[0].setVisible(not self.active)                # 同じ動作: 同じ物を 2 つ並べない(コマンドパレットには残る)

    # ---- 起動・終了 ----
    def restore(self, start_mode: str):
        """起動時: 設定からモード・ファイル・文面・カーソル・ブレークポイント・ウォッチを戻す。"""
        if start_mode == MODE_PIPELINE:
            return
        choice = str(self._get("start", "last"))
        mode = str(self._get("mode", MODE_PYTHON)) if choice == "last" else choice
        if start_mode == MODE_PYTHON:
            mode = MODE_PYTHON
        cfg = str(self._get("config", "debug"))
        if cfg in sp.CONFIGS:
            self.set_config(cfg)
        path = str(self._get("file", "") or "")
        buf = self._get("buffer", None)
        origin = str(self._get("origin", "typed"))
        trusted = str(self._get("session_trusted", "true")).lower() in ("true", "1")
        text = None
        kept = buf if isinstance(buf, str) and buf else None
        if path and os.path.isfile(path):
            try:
                with open(path, "rb") as fh:
                    raw = fh.read()
                disk = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
            except (OSError, UnicodeDecodeError):
                raw = disk = None
            name = os.path.basename(path)
            if disk is not None:
                self.file = os.path.abspath(path)
                self.saved_digest = sp.program_digest(disk)
                stamp = _bytes_stamp(raw)                     # 文面と同じ 1 回の読みから作る
                known = _stamp_from_setting(self._get("file_stamp", ""))
                if known is None:                             # 前の版の設定(生のバイトの印が無い): 文面で比べる
                    unchanged = sp.program_digest(disk) == str(self._get("file_digest", ""))
                else:
                    unchanged = known == stamp                # "changed" の印は、どの印とも等しくない
                text = kept or disk
                if not unchanged:
                    trusted = False                           # ファイルが外で変わった: 確認し直す
                # 退避した文面を出すのに、ファイルが外で変わっていた: 比べる元は無い(= 変わった。自動保存は書かず、
                # Ctrl+S は聞く。2026-11-15 第 4 回の確かめ: 前は変わった中身を比べる元にして、聞かずに上書きした)
                self._disk_stamp = stamp if (unchanged or not kept) else None
                if kept and not unchanged:
                    note = self.tr("%s was changed by another program while Studio was closed: the Program shows "
                                   "your unsaved text; saving asks before it replaces the file") % name
                    self._status(note)
                    self.flash(note)
                origin = origin if origin in ("file", "project") else "file"
            elif kept:
                # 読めない(cp932 に書き換わった・ロック中): 退避した文面を捨てない。ファイルは付けるが比べる元は無し
                # (= 変わった: 自動保存は書かず、Ctrl+S は聞く)。確認はやり直す(2026-11-15 第 4 回の確かめ)
                self.file = os.path.abspath(path)
                self.saved_digest = None
                self._disk_stamp = None
                text, trusted = kept, False
                origin = origin if origin in ("file", "project") else "file"
                note = self.tr("Could not read %s: the Program shows the unsaved text kept from the last session; "
                               "saving asks before it replaces the file") % name
                self._status(note)
                self.flash(note)
        elif isinstance(buf, str) and buf and buf not in sp.STARTER_PROGRAMS.values():
            text = buf                                        # 手を付けていない例は残さず、今の言語の例を出す
        if text is not None:
            self.py_text = text
            self.origin = origin
            self.session_trusted = trusted or origin == "typed"
            if not self.session_trusted:
                self._note_unconfirmed(text, origin, self.file)
        try:
            self.breakpoints_py = set(int(x) for x in json.loads(str(self._get("breakpoints", "[]"))))
            self.conditions = {int(k): str(v) for k, v in json.loads(str(self._get("conditions", "{}"))).items()}
        except (TypeError, ValueError):
            self.breakpoints_py, self.conditions = set(), {}
        w = self._get("watch", None)
        if w and self.vars is not None:
            try:
                self.vars.watch.loads(str(w))
            except Exception:                                 # noqa: BLE001 -- 壊れた保存はウォッチなしで起動
                pass
        if mode == MODE_PYTHON:
            self.set_mode(MODE_PYTHON, announce=False)
            try:
                pos = int(self._get("cursor", 0))
                c = self.edit.textCursor()
                c.setPosition(max(0, min(pos, len(self.edit.toPlainText()))))
                self.edit.setTextCursor(c)
            except (TypeError, ValueError):
                pass
        self._update_labels()

    def save_state(self):
        text = self.edit.toPlainText() if self.active else self.py_text
        bps = self.edit.breakpoints if self.active else self.breakpoints_py
        self._set("mode", self.mode)
        self._set("config", self.config)
        self._set("file", self.file or "")
        self._set("file_digest", self.saved_digest or "")
        # 生のバイトの印(次の起動で「外で変わったか」を比べる元)。比べる元が無い(外で変わった・読めなかった)
        # 事も残す: 残さないと、次の起動で今のディスクが比べる元になり、聞かずに上書きする
        self._set("file_stamp", "" if not self.file else (
            "%d:%s" % self._disk_stamp if self._disk_stamp else _STAMP_CHANGED))
        self._set("buffer", text if (self.unsaved() or not self.file) else "")
        self._set("origin", self.origin)
        self._set("session_trusted", "true" if self.session_trusted else "false")
        self._set("cursor", self.edit.textCursor().position() if self.active else 0)
        self._set("breakpoints", json.dumps(sorted(int(b) for b in bps)))
        self._set("conditions", json.dumps({str(k): v for k, v in self.conditions.items()}))
        if self.vars is not None:
            self._set("watch", self.vars.watch.dumps())
        try:
            self.settings().sync()
        except Exception:                                     # noqa: BLE001
            pass

    # ---- ファイルへの自動保存(設定で入れる。既定は切) ----
    def autosave_file_mode(self) -> str:
        m = str(self._get("autosave_file", "off"))
        return m if m in AUTOSAVE_FILE_MODES else "off"

    def autosave_idle_s(self) -> float:
        try:
            v = float(self._get("autosave_idle_s", DEFAULT_AUTOSAVE_IDLE_S))
        except (TypeError, ValueError):
            v = DEFAULT_AUTOSAVE_IDLE_S
        lo, hi = AUTOSAVE_IDLE_RANGE_S
        return min(hi, max(lo, v))

    def set_autosave_file(self, mode: str, idle_s: float | None = None):
        """ファイルへの自動保存の設定(メニューと設定の画面から)。"""
        if mode not in AUTOSAVE_FILE_MODES:
            raise ValueError("autosave mode must be one of %s" % (AUTOSAVE_FILE_MODES,))
        self._set("autosave_file", mode)
        if idle_s is not None:
            lo, hi = AUTOSAVE_IDLE_RANGE_S
            self._set("autosave_idle_s", min(hi, max(lo, float(idle_s))))
        if mode != "idle":
            self._file_save_timer.stop()
        self._sync_autosave_actions()
        self.flash({"off": self.tr("Autosave to the file: off"),
                    "idle": self.tr("Autosave to the file: %.1f s after you stop typing") % self.autosave_idle_s(),
                    "focus": self.tr("Autosave to the file: when the Program loses the focus")}[mode])

    def _sync_autosave_actions(self):
        mode = self.autosave_file_mode()
        for m, a in self._autosave_actions.items():
            a.setChecked(m == mode)

    def _disk_now(self) -> tuple | None:
        """ディスクのファイルの今の印 ``(大きさ, SHA-256)``。読めなければ None。大きさが覚えている物と違えば、
        中身は読まない(巨大なファイルに書き換えられていても待たせない)。"""
        try:
            size = os.path.getsize(self.file)
        except (OSError, TypeError):
            return None
        known = self._disk_stamp
        if known is not None and size != known[0]:
            return size, ""
        return _file_stamp(self.file)

    def disk_changed(self) -> bool:
        """開いた(か最後に保存した)後で、ファイルが Studio の外で書き換えられたか。**生のバイト**の大きさと
        SHA-256 で比べる(文字にしない)。読めない時・比べる元の印が無い時は「変わった」(上書きしない側。
        2026-11-13 第 3 回レビュー S3: 前は UTF-8 で解けない中身 = cp932 など・4 MB を越えた中身を
        「変わっていない」として、自動保存が聞かずに上書きした)。外で消されたファイルは「変わっていない」
        (保存は作り直すだけで、上書きする相手が無い)。"""
        if not self.file or not os.path.isfile(self.file):
            return False
        now = self._disk_now()
        return now is None or self._disk_stamp is None or now != self._disk_stamp

    def autosave_file(self, why: str = "idle") -> bool:
        """設定が入っていれば、Python のファイルへ今の文面を保存する(窓は出さない。状態の欄に小さく出す)。

        * 保存先の無い文面(無題)には効かない(退避だけ)。変わっていなければ書かない。
        * **外でファイルが変わっていたら上書きしない**(1 回だけ知らせる。手で保存すれば上書きの確認が出る)。
        * 構文が壊れている途中でも保存する。実行はしない。信頼の状態(台帳・``session_trusted``)は変えない。
        * 書き方は ``atomic_write_text``(書きかけのファイルを残さない)。"""
        if self.autosave_file_mode() == "off" or not self.file:
            return False
        text = self.edit.toPlainText() if self.active else self.py_text
        digest = sp.program_digest(text)
        if digest == self.saved_digest:
            return False
        if self.disk_changed():
            disk = self._disk_now() or "unreadable"
            if self._conflict_told != disk:
                self._conflict_told = disk
                msg = self.tr("Not autosaved: %s was changed on disk by another program — Save (Ctrl+Alt+S) asks "
                              "before it overwrites that; open the file again to read it") % os.path.basename(self.file)
                self.autosave_note.setText("\u26a0 " + self.tr("not autosaved"))
                self.autosave_note.setToolTip(msg)
                self.flash(msg)
            return False
        try:
            atomic_write_text(self.file, text)
        except OSError as e:
            self.autosave_note.setText("\u26a0 " + self.tr("not autosaved"))
            self.autosave_note.setToolTip(self.tr("Could not autosave %s: %s") % (os.path.basename(self.file), e))
            return False
        self.saved_digest = digest
        self._disk_stamp = _bytes_stamp(text.encode("utf-8"))
        self._conflict_told = None
        self.autosave_note.setText(self.tr("autosaved %s") % time.strftime("%H:%M:%S"))
        self.autosave_note.setToolTip(self.tr("Saved to %s automatically (%s)") % (
            self.file, self.tr("after a pause in typing") if why == "idle" else self.tr("the Program lost the focus")))
        self.state["pymode_autosaves"] = self.state.get("pymode_autosaves", 0) + 1
        self._update_labels()
        return True

    def autosave_now(self) -> bool:
        """文面が前に書き出した時から変わっていれば、状態(未保存の文面・カーソル・ブレークポイント)を設定へ
        書き出す。Studio が落ちても、次の起動で文面が戻る(プログラムが ``os._exit`` を呼んだ時など)。"""
        text = self.edit.toPlainText() if self.active else self.py_text
        d = sp.program_digest(text)
        if d == self._autosaved_digest:
            return False
        self._autosaved_digest = d
        self.save_state()
        return True

    def confirm_close(self) -> bool:
        """終了の前: 未保存の Python のプログラムを聞く(無題の文面は設定に残すので聞かない)。"""
        if self.running or (self.session is not None and self.session.live):
            if not self._confirm(self.tr("Quit Fullseye Studio"),
                                 self.tr("A Python program is still running (or stopped at a breakpoint). Closing "
                                         "Studio stops it: what it has computed so far is lost."),
                                 self.tr("Stop it and quit")):
                return False
        if self.file and self.unsaved():
            return self._confirm_unsaved(self.tr("Quit Fullseye Studio"))
        return True

    def shutdown(self, timeout_s: float = 3.0):
        """閉じる前: 走っている実行を止めて待つ(見張りが諦めるまで最大 上限 + 1 s)。状態を保存する。"""
        job = self.job
        if job is not None:
            job.stop_event.set()
            job.thread.join(timeout_s)
            self.job = None
        if self.session is not None:                          # ブレークポイントで待っている実行を残さない
            self._end_session()
        self._poll.stop()
        self._autosave.stop()
        if self._file_save_timer.isActive():                  # 待っていた自動保存は、閉じる前に済ませる
            self._file_save_timer.stop()
            self.autosave_file("idle")
        self.detach_highlighter()
        if self.vars is not None:
            try:
                self.vars.watch.wait_idle(1.0)
            except Exception:                                 # noqa: BLE001
                pass
        self.save_state()

    def detach_highlighter(self):
        """エディタ支援を編集欄から外す(閉じる前・プロセスの終わり)。event filter を付けたままプロセスが終わると、
        終了の途中で Python へ呼び戻して落ちる(実測: Windows で exit 139。studio_pyedit_qt.PyEditAssist.detach)。"""
        a = self.assist
        if a is None:
            return
        try:
            a.detach()
        except RuntimeError:
            pass

    def wait_idle(self, timeout_s: float = 30.0) -> bool:
        """実行が終わり、結果が画面に入るまでイベントを回して待つ(試験・e2e 用)。"""
        end = time.monotonic() + timeout_s
        app = QtWidgets.QApplication.instance()
        while self.job is not None and time.monotonic() < end:
            app.processEvents()
            time.sleep(0.01)
        app.processEvents()
        return self.job is None


# --------------------------------------------------------------------------- #
# 小物                                                                          #
# --------------------------------------------------------------------------- #
#: 画像の欄へ渡してよい配列の dtype の種類(bool・整数・実数・複素数)。object・文字列・日付・構造体の配列は渡さない
#: (表示の処理が落ちてモーダルの窓が出た。object の配列は要素ごとに利用者のコードを呼びうる)。
_DISPLAYABLE_KINDS = "biufc"


def _is_image(v) -> bool:
    import numpy as np
    if type(v) is not np.ndarray:                             # 型だけで決める(v.__class__ を読まない。派生した型は画像として扱わない)
        return False
    if v.dtype.kind not in _DISPLAYABLE_KINDS:                # 数でない配列は絵にしない
        return False
    return v.ndim in (2, 3) and v.shape[0] > 1 and v.shape[1] > 1 and (v.ndim == 2 or v.shape[2] in (1, 3, 4))


def _namespace_source(pv, pm):
    """変数の欄の供給元。欄に見せるのは名前空間の**写し**(前置きの名前などを除いた物)なので、欄での編集を
    実行の名前空間(``pm.namespace``)にも書く(書かないと、欄の値だけ変わって次の実行・選んだ行の実行には
    効かない = 見かけだけの編集。2026-11-13 レビュー M4)。関数の局所変数は外から書き換えられないので断る。"""

    class NamespaceSource(pv.DictSource):
        def set_value(self, path, value):
            if path and path[0][0] == "name" and len(path) == 1:
                name = path[0][1]
                if name in pm._frame_local_names:
                    raise pv.EditError(pm.tr("A local variable of a function cannot be changed here"))
                real = pm.namespace
                if type(real) is not dict or name not in real:
                    raise pv.EditError(pm.tr("This name is not a variable of the program any more: run it again"))
                real[name] = value
            super().set_value(path, value)

    return NamespaceSource({})


def _configure_jedi():
    """jedi が補完のために値を評価しない設定(入っていれば)。これだけでは実行後の値の ``__dir__`` /
    ``__getattr__`` は呼ばれる(jedi 0.20 で確かめた)ので、jedi に渡す値は ``studio_pyedit_complete`` が
    数・文字列・numpy の配列・ライブラリのモジュールに絞る。"""
    try:
        import jedi
    except Exception:                                         # noqa: BLE001
        return False
    try:
        jedi.settings.allow_unsafe_interpreter_executions = False   # 実行後の値の property は評価しない
        jedi.settings.auto_import_modules = []                       # 解析のために import するモジュールを無くす
    except Exception:                                         # noqa: BLE001
        return False
    return True


class _LockedProvider:
    """補完の供給元を 1 本の鍵で守る(背景の温め中は待たずに空を返す。jedi は同時に呼べない)。"""

    def __init__(self, base, wait_s: float = 0.05):
        self.base = base
        self.lock = threading.Lock()
        self.wait_s = wait_s
        self.fallback = getattr(base, "fallback", base)

    def _call(self, name, *args, empty=None):
        if not self.lock.acquire(timeout=self.wait_s):
            return empty
        try:
            return getattr(self.base, name)(*args)
        finally:
            self.lock.release()

    def complete(self, text, line, col):
        return self._call("complete", text, line, col, empty=[])

    def signature(self, text, line, col):
        return self._call("signature", text, line, col)

    def hover(self, text, line, col):
        return self._call("hover", text, line, col)


def _find_layout(widget):
    """*widget* を直接持つ layout(入れ子も探す)。"""
    parent = widget.parentWidget()
    if parent is None or parent.layout() is None:
        return None
    todo = [parent.layout()]
    while todo:
        lay = todo.pop()
        for i in range(lay.count()):
            it = lay.itemAt(i)
            if it.widget() is widget:
                return lay
            if it.layout() is not None:
                todo.append(it.layout())
    return None


def _wrap_in_stack(widget, other):
    """*widget* を置き場ごと QStackedWidget([widget, other]) に入れ替える。"""
    stack = QtWidgets.QStackedWidget()
    lay = _find_layout(widget)
    if lay is not None:
        lay.replaceWidget(widget, stack)
    stack.addWidget(widget)
    stack.addWidget(other)
    return stack


def install(win, ctx: dict, start_mode: str = MODE_PIPELINE) -> PyModeController:
    """窓に Python のモードを付ける。*start_mode*: ``"pipeline"``(build_window の既定 = 今までの試験の前提)・
    ``"python"``・``"auto"``(設定 = 既定は前回のまま、初回は Python。main() の起動)。"""
    pm = PyModeController(win, ctx)
    win._pymode = pm
    import atexit
    import weakref
    ref = weakref.ref(pm)
    atexit.register(lambda: ref() is not None and ref().detach_highlighter())
    pm.install_actions()
    pm.restore(start_mode)
    pm._autosaved_digest = sp.program_digest(pm.edit.toPlainText() if pm.active else pm.py_text)
    pm._autosave.start()
    return pm
