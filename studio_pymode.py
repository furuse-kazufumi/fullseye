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
* **Debug の続行と 1 行実行は「上から走り直し」**(§4)。メモ化(``OpMemo``)で上流の op は計算し直さない。
* **安全**: ファイル・プロジェクトから開いた Python は、初回の実行の前に確認(``TrustStore``、中身の SHA-256 で
  覚える。中身が変われば確認し直し)。確認した後にエディタで直した文面は利用者の物として扱う。開いただけ・
  補完・検査・ホバーではコードを走らせない(jedi は ``allow_unsafe_interpreter_executions=False``、
  ``auto_import_modules=[]``)。
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
from dataclasses import dataclass, field

from PySide6 import QtCore, QtGui, QtWidgets

import studio_program as sp

MODE_PYTHON = "python"
MODE_PIPELINE = "pipeline"
MODES = (MODE_PIPELINE, MODE_PYTHON)
START_CHOICES = ("last", MODE_PYTHON, MODE_PIPELINE)
SETTINGS_PREFIX = "pymode/"
POLL_MS = 30
DEFAULT_TIME_LIMIT_S = sp.DEFAULT_TIME_LIMIT_S
NEW_PROGRAM_TEXT = ("# python\n"
                    "# New program. F5 runs it; img is the image open in Studio.\n"
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


def problem_rows(problems) -> list:
    """``check_program`` の結果 → Problems の行 ``[(行, 文)]`` と、波線の ``{行: 文}``。"""
    glyph = {"error": "✕", "warning": "⚠", "hint": "ℹ"}
    rows, per_line = [], {}
    for p in problems:
        msg = "%s line %d: %s [%s]" % (glyph.get(p.severity, "!"), p.line, p.message, p.code)
        if p.hint:
            msg += " — " + p.hint
        rows.append((int(p.line), msg))
        per_line[int(p.line)] = (per_line[int(p.line)] + "; " + p.message) if int(p.line) in per_line else p.message
    return rows, per_line


def error_line_of(text: str) -> int | None:
    """出力の 1 行から ``line N`` の N(押すとその行へ飛ぶ)。無ければ None。"""
    m = re.search(r"\bline (\d+)\b", text or "")
    return int(m.group(1)) if m else None


def trust_store_path(settings_file: str | None) -> str:
    """信頼の台帳(JSON)の置き場: 設定が ini ならその隣、そうでなければ利用者のデータの場所。"""
    if settings_file and settings_file.lower().endswith(".ini") and os.path.isdir(os.path.dirname(settings_file)):
        return os.path.join(os.path.dirname(settings_file), "studio_trust.json")
    base = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.AppDataLocation) or tempfile.gettempdir()
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "studio_trust.json")


@dataclass
class DebugSession:
    """Debug で止まっている実行(続行・1 行実行の起点)。"""
    text: str
    lines_run: int
    line: int
    reason: str


def run_plan(action: str, session: DebugSession | None, text: str, breakpoints, conditions) -> dict:
    """run / continue / step の、run_program に渡す引数(Qt なし。試験あり)。

    * run      : 上から。ブレークポイントと条件を渡す。
    * continue : 止まっている所から。走り直しで、すでに通った行数 + 1 まではブレークポイントで止めない。
                 文面が止まった時から変わっていれば、上から(``restart=True``)。
    * step     : 1 行。止まっていなければ最初の行で止まる(``max_lines=0``)。"""
    bps = sorted(set(int(b) for b in breakpoints))
    conds = {int(k): v for k, v in (conditions or {}).items() if int(k) in bps}
    same = session is not None and session.text == text
    if action == "run" or (action == "continue" and not same):
        return {"breakpoints": bps, "conditions": conds, "resume_after_lines": 0, "max_lines": None,
                "restart": action == "continue"}
    if action == "continue":
        return {"breakpoints": bps, "conditions": conds, "resume_after_lines": session.lines_run + 1,
                "max_lines": None, "restart": False}
    if action == "step":
        n = session.lines_run + 1 if same else 0
        return {"breakpoints": [], "conditions": {}, "resume_after_lines": 0, "max_lines": n, "restart": False}
    raise ValueError("action must be run / continue / step, got %r" % (action,))


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


def _default_trust(parent, title, text):                     # pragma: no cover - GUI
    box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, title, text, QtWidgets.QMessageBox.NoButton, parent)
    run = box.addButton(_TR["fn"]("Run it"), QtWidgets.QMessageBox.AcceptRole)
    box.addButton(_TR["fn"]("Cancel"), QtWidgets.QMessageBox.RejectRole)
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

    def __init__(self, kind: str, fn, stop_event: threading.Event, meta: dict):
        self.kind = kind
        self.meta = meta
        self.stop_event = stop_event
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
        self.py_text = sp.STARTER_PROGRAM
        self.pipe_text: str | None = None
        self.pipe_dirty = False
        self.file: str | None = None
        self.origin = "typed"
        self.session_trusted = True
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
        self.trust = sp.TrustStore(trust_store_path(self._settings_file()))
        self._poll = QtCore.QTimer(self)
        self._poll.setInterval(POLL_MS)
        self._poll.timeout.connect(self._poll_job)
        self.assist = None
        with self._quiet_text():
            self._build_assist()
        self._build_ui()
        self.edit.assist_hook = self._paint_marks
        self.edit._gutter.installEventFilter(self)

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
        """Python の文面に保存していない変更があるか(ファイルなら中身と比べる。無題なら例の文面と比べる)。"""
        text = self.edit.toPlainText() if self.active else self.py_text
        if self.file:
            return self.saved_digest != sp.program_digest(text)
        return sp.program_digest(text) not in (sp.program_digest(sp.STARTER_PROGRAM),
                                               sp.program_digest(NEW_PROGRAM_TEXT), self.saved_digest)

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
        self.file_label = QtWidgets.QLabel()
        bar.addWidget(self.file_label)
        self.config_box = QtWidgets.QComboBox()
        self.config_box.addItems([tr("Debug"), tr("Release")])
        self.config_box.currentIndexChanged.connect(lambda i: self.set_config(("debug", "release")[i]))
        bar.addWidget(self.config_box)
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
        self.output.setMaximumHeight(150)
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
            self.var_source = pv.DictSource({})
        new = vq.VarsWatchWidget(self.var_source, self._ptr, on_run=self.run, on_open_example=self.open_example)
        new.variables.imageRequested.connect(lambda _n, v: self._show_value(v))
        new.watch.changed.connect(lambda _l: self._set("watch", self.vars.watch.dumps()))
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
        self.btn_pipe.setText(tr("Pipeline mode"))
        self.btn_py.setText(tr("Python mode"))
        self.btn_pipe.setToolTip(tr("Pipeline mode: the stage list is the source; the Program shows it as code"))
        self.btn_py.setToolTip(tr("Python mode: the Program text is the source; the stage list records each run"))
        self.config_box.setToolTip(tr("Debug stops at breakpoints and steps line by line; Release runs faster "
                                      "without the line hook (breakpoints do not stop)"))
        self.btn_run.setText(tr("Run"))
        self.btn_run.setToolTip(tr("Run the Python program (F5). When stopped at a breakpoint: continue"))
        self.btn_step.setText(tr("Step"))
        self.btn_step.setToolTip(tr("Step: run one line and stop (F6, Debug only)"))
        self.btn_stop.setText(tr("Stop"))
        self.btn_stop.setToolTip(tr("Stop the running program (Ctrl+F2)"))
        self.output_title.setText(tr("Output (print, notes and errors; click a line with 'line N' to go there)"))
        self.output.setPlaceholderText(tr("Run the program (F5): print output, notes and errors appear here."))
        self._update_labels()

    # ---- 見た目の同期 ----
    def _sync_mode_widgets(self):
        py = self.active
        self.btn_py.setChecked(py)
        self.btn_pipe.setChecked(not py)
        for b in self.ctx.get("pipeline_buttons", ()):
            b.setVisible(not py)
        for w in (self.config_box, self.btn_run, self.btn_step, self.btn_stop, self.file_label, self.output,
                  self.output_title):
            w.setVisible(py)
        self.stage_stack.setCurrentIndex(1 if py else 0)
        if getattr(self, "var_stack", None) is not None:
            self.var_stack.setCurrentIndex(1 if py else 0)
        self.edit.comment_prefix = "#" if py else "*"
        self.edit.legacy_completion = not py
        if self.assist is not None:
            with self._quiet_text():                         # 色分けの付け外しは文書の「変更」を撃つ: 未適用・未保存にしない
                self.assist.set_active(py)
            if not py:
                self.edit.setStyleSheet(self._legacy_ss)
        self._update_labels()
        self.edit._highlight()

    def _update_labels(self):
        tr = self.tr
        if self.active:
            self.mode_note.setText(tr("Python: the text is the source"))
            star = " ●" if self.unsaved() else ""
            self.file_label.setText(self.display_name() + star)
            self.file_label.setToolTip(self.file or tr("not saved to a file yet"))
        else:
            self.mode_note.setText(tr("Pipeline: the stage list is the source"))
        self.btn_stop.setEnabled(self.running)
        self.btn_step.setEnabled(self.config == "debug")
        st = self.session is not None and not self.running
        self.btn_run.setText(tr("Continue") if st else tr("Run"))
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
            if mode == MODE_PYTHON:
                self.pipe_text = self.edit.toPlainText()
                self.pipe_dirty = bool(self.state.get("code_dirty"))
                self.breakpoints_pipe = set(self.edit.breakpoints)
                self.mode = MODE_PYTHON
                self.state["code_dirty"] = False
                self.edit.setPlainText(self.py_text)
                self.edit.breakpoints = set(self.breakpoints_py)
                self.edit.clear_exec()
                self.warm_up()
            else:
                self.py_text = self.edit.toPlainText()
                self.breakpoints_py = set(self.edit.breakpoints)
                self._end_session()
                self.mode = MODE_PIPELINE
                self.edit.breakpoints = set(self.breakpoints_pipe)
                self.edit.set_errors({})
                if self.pipe_text is not None and self.pipe_dirty:
                    self.edit.setPlainText(self.pipe_text)
                    self.state["code_dirty"] = True
                else:
                    self.state["code_dirty"] = False
                    self.ctx["sync_program"]()                # 段の列(正本)から文面を作り直す
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

    def toggle_mode(self):
        self.set_mode(MODE_PIPELINE if self.active else MODE_PYTHON)

    def convert_to_python(self):
        """パイプラインの文面を Python にして Python のモードへ(行の位置は変えない。Undo で前の Python に戻る)。"""
        # 変換するのはパイプラインの文面(Python のモードにいるなら、正本の段の列から作り直した物)
        src = self.edit.toPlainText() if not self.active else self.ctx["pipeline_text"]()
        py, errs = sp.hdev_to_python(src)
        if errs:
            self.flash(self.tr("Could not convert to Python: %s") % "; ".join(errs[:2]))
            return False
        self.set_mode(MODE_PYTHON, announce=False)
        cur = QtGui.QTextCursor(self.edit.document())
        cur.select(QtGui.QTextCursor.Document)
        cur.insertText(py)                                    # 1 回の Undo で前の Python の文面に戻る
        self.file, self.origin, self.session_trusted, self.saved_digest = None, "typed", True, None
        self.last = None
        self._update_labels()
        self.flash(self.tr("Converted the pipeline to Python (Ctrl+Z restores the previous Python text)"))
        return True

    def on_pipeline_opened(self):
        """パイプラインのファイルを開いた: パイプラインのモードで見せる(開いた物に合わせる)。"""
        if self.active:
            self.set_mode(MODE_PIPELINE, announce=False)

    # ---- 文面の変化 ----
    def on_text_changed(self):
        if self._suspend_text:
            return
        if self.session is not None:                         # 止まった時の文面と違う: 続行は上から走り直しになる
            self.edit.set_exec_line(0)
        self._update_labels()

    # ---- 検査(打っている最中) ----
    def check_now(self):
        text = self.edit.toPlainText()
        try:
            probs = sp.check_program(text, syntax=sp.SYNTAX_PYTHON, lang=self.ctx.get("lang", lambda: "en")())
        except Exception as e:                                # noqa: BLE001 -- 検査が入力を止めない
            probs = []
            self.state.setdefault("errors", []).append(("program check failed", str(e)))
        rows, per_line = problem_rows(probs)
        if self.last is not None and self.last_text == text and self.last.error_line and self.last.errors:
            ln = int(self.last.error_line)
            rows.append((ln, "✕ " + self.tr("run") + ": " + self.last.errors[0]))
            per_line[ln] = (per_line.get(ln, "") + "; " if ln in per_line else "") + self.last.errors[0]
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
        if self.origin == "typed" or self.session_trusted:
            return True
        if self.trust.is_trusted(text, self.origin):
            self.session_trusted = True
            return True
        where = self.file or self.tr("a file")
        ok = TRUST_HOOK(self.win, self.tr("Run this Python program?"),
                        self.tr("This program came from %s.\n\nPython runs on this PC with your permissions: "
                                "it can read and change files. Run it only if you trust it.\n\n"
                                "Studio remembers your answer for this exact text; if the file changes, "
                                "it asks again.") % where)
        if not ok:
            self.flash(self.tr("Not run: the program was not confirmed"))
            self._out(self.tr("Not run: this program came from a file and was not confirmed."))
            return False
        self.trust.trust(text)
        self.session_trusted = True
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
        text = self.edit.toPlainText()
        syn, errs = sp.detect_syntax(text)
        if not self._check_trust(text):
            return False
        plan = run_plan(action, self.session, text, self.edit.breakpoints, self.conditions)
        if plan["restart"]:
            self._out(self.tr("The program changed since it stopped: running again from the top"))
        stop = threading.Event()
        root = self.ctx.get("project_root", lambda: None)()
        stages = [tuple(s[:3]) for s in getattr(self.model, "stages", []) if not (len(s) > 3 and s[3])]
        kw = dict(trusted=True, syntax=sp.SYNTAX_PYTHON, memo=self.memo, time_limit_s=self.time_limit_s(),
                  breakpoints=plan["breakpoints"], conditions=plan["conditions"],
                  resume_after_lines=plan["resume_after_lines"], max_lines=plan["max_lines"], stop_event=stop,
                  current_stages=stages, config=self.config, project_dir=root,
                  program_dir=os.path.dirname(self.file) if self.file else None, filename=self.file)
        image = self._input_image()
        self.job = RunJob("program", lambda: sp.run_program(text, image, **kw), stop,
                          {"text": text, "action": action, "config": self.config}).start()
        self.state["pymode_runs"] = self.state.get("pymode_runs", 0) + 1
        self._out_header(action)
        self.ctx["status"].setText(self.tr("running…"))
        self._update_labels()
        self._poll.start()
        return True

    def stop(self):
        """Ctrl+F2: 走っていれば止める。止まっている(ブレークポイント)なら Debug の区切りを終える。"""
        if self.job is not None:
            self.job.stop_event.set()
            self.ctx["status"].setText(self.tr("stop requested…"))
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
        self.session = None
        self.edit.clear_exec()
        self._update_labels()

    def run_selection(self):
        """選んだ行(選びが無ければカーソルの行)だけを、直前の実行の名前空間で実行する。"""
        if self.running:
            self.flash(self.tr("A program is already running: press Stop (Ctrl+F2) first"))
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
            if not isinstance(k, str) or k.startswith("_") or type(v).__name__ == "module":
                continue
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
            return
        self.job = None
        self._poll.stop()
        try:
            if job.exc is not None:
                self._out("✕ " + self.tr("internal error: %s") % job.exc)
                self.ctx["status"].setText(self.tr("internal error: %s") % job.exc)
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
        if r.get("error"):
            l1 = job.meta["lines"][0]
            err = r["error"]
            m = re.match(r"line (\d+):", err)
            if m:
                err = "line %d:%s" % (l1 + int(m.group(1)) - 1, err[m.end():])
            self._out("✕ " + err)
            self.ctx["status"].setText("✕ " + err)
        else:
            v = r.get("value")
            if v is not None:
                kind, shape, summ = sp.describe_value(v)
                self._out("= " + summ)
                if _is_image(v):
                    self._show_value(v)
            self.ctx["status"].setText(self.tr("ran lines %d–%d") % job.meta["lines"])
        self._refresh_variables(self.namespace)
        self.flash(self.tr("ran lines %d–%d") % job.meta["lines"])

    def _program_done(self, job):
        res: sp.ProgramResult = job.result
        tr = self.tr
        text = job.meta["text"]
        self.last, self.last_text = res, text
        if res.namespace is not None:
            self.namespace = res.namespace
        if res.stdout:
            self._out(res.stdout.rstrip("\n"))
        for n in res.notes:
            self._out("ℹ " + n)
        for e in res.errors:
            self._out("✕ " + e)
        # 記録・絵・変数
        self._fill_record(res)
        if res.ran and res.output is not None and not res.not_run_reason:
            self._show_value(res.output)
        self._refresh_variables(res.namespace)
        self.edit.set_timings(per_line_ms(res.calls))
        paused = res.stopped in ("breakpoint", "step")
        if paused:
            self.session = DebugSession(text, res.lines_run, int(res.stopped_line or 0), res.stopped)
            self.edit.set_exec_line(int(res.stopped_line or 0))
            self.edit.goto_line(int(res.stopped_line or 1), focus=False)
            cond = self.conditions.get(int(res.stopped_line or 0))
            msg = (tr("stopped at line %d (breakpoint)") % res.stopped_line if res.stopped == "breakpoint"
                   else tr("stopped at line %d (step)") % res.stopped_line)
            if cond and res.stopped == "breakpoint":
                msg += "  ·  " + tr("condition: %s") % cond
            msg += "  ·  " + tr("F5 continue, F6 step, Ctrl+F2 stop")
        else:
            self.session = None
            self.edit.clear_exec()
            self.edit.set_timings(per_line_ms(res.calls))
            if res.errors:
                msg = "✕ " + res.errors[0]
            else:
                hits = sum(1 for c in res.calls if c.cached)
                msg = tr("ran in %.0f ms (%s)  ·  %d op call(s), %d from cache") % (
                    res.elapsed_s * 1000.0, "Debug" if res.config == "debug" else "Release", len(res.calls), hits)
        self._out(msg)
        self.ctx["status"].setText(msg)
        for n in res.notes:
            if n.startswith("Release does not stop"):
                self.flash(tr("Release does not stop at breakpoints: switch to Debug to use them"))
                break
        else:
            self.flash(msg)
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

    def _refresh_variables(self, ns):
        if self.vars is None or self.var_source is None:
            return
        vals = self._user_values(ns) if isinstance(ns, dict) else {}
        self.var_source.ns = vals
        try:
            self.vars.refresh()
        except Exception as e:                                # noqa: BLE001
            self.state.setdefault("errors", []).append(("variables refresh failed", str(e)))
        if not self.state.get("pymode_vars_shown"):
            self.state["pymode_vars_shown"] = True
            self.ctx.get("show_panel", lambda _n: None)("variables")

    def _show_value(self, v):
        try:
            self.ctx["show_value"](v)
        except Exception as e:                                # noqa: BLE001 -- 表示の失敗で実行の結果を失わない
            self._out("⚠ " + self.tr("could not display the result: %s") % e)

    def goto_line(self, ln: int):
        self.edit.goto_line(int(ln))

    # ---- 出力の欄 ----
    def _out(self, text: str):
        self.output.appendPlainText(text)
        sb = self.output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _out_header(self, action):
        name = {"run": self.tr("Run"), "continue": self.tr("Continue"), "step": self.tr("Step")}[action]
        self._out("── %s  %s  (%s)  %s" % (name, self.display_name(), "Debug" if self.config == "debug"
                                                      else "Release", time.strftime("%H:%M:%S")))

    def clear_output(self):
        self.output.clear()

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
        self._load_text(NEW_PROGRAM_TEXT, None, "typed")
        return True

    def open_example(self):
        if not self._confirm_unsaved(self.tr("Open the example")):
            return False
        self._load_text(sp.STARTER_PROGRAM, None, "typed")
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
        self._load_text(text.replace("\r\n", "\n"), os.path.abspath(path), origin)
        self.flash(self.tr("opened %s (not run: F5 runs it after you confirm it once)") % os.path.basename(path))
        return True

    def _load_text(self, text, path, origin):
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
        self.origin = origin
        self.session_trusted = origin == "typed"
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
        return self._write(self.file)

    def save_as(self) -> bool:
        start = self.file or self.ctx.get("proj_path", lambda k, d="": d)("python", "program.py")
        path = SAVE_AS_HOOK(self.win, self.tr("Save Python program as"), start)
        if not path:
            return False
        if not path.lower().endswith(".py"):
            path += ".py"
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
        mk("pymode_example", "Open the Python example", None,
           "Put the example program (a sample image, four ops, a variable and an if) into the Program",
           self.open_example, pm, "例 example sample サンプル python")
        mk("pymode_clear_output", "Clear output", None, "Clear the Output pane under the Program",
           self.clear_output, pm, "出力 output 消す clear", py_only=True)
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
        if path and os.path.isfile(path):
            try:
                with open(path, encoding="utf-8-sig") as fh:
                    disk = fh.read().replace("\r\n", "\n")
            except (OSError, UnicodeDecodeError):
                disk = None
            if disk is not None:
                self.file = os.path.abspath(path)
                self.saved_digest = sp.program_digest(disk)
                text = buf if isinstance(buf, str) and buf else disk
                if sp.program_digest(disk) != str(self._get("file_digest", "")):
                    trusted = False                           # ファイルが外で変わった: 確認し直す
                origin = origin if origin in ("file", "project") else "file"
        elif isinstance(buf, str) and buf:
            text = buf
        if text is not None:
            self.py_text = text
            self.origin = origin
            self.session_trusted = trusted or origin == "typed"
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

    def confirm_close(self) -> bool:
        """終了の前: 未保存の Python のプログラムを聞く(無題の文面は設定に残すので聞かない)。"""
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
        self._poll.stop()
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
def _is_image(v) -> bool:
    import numpy as np
    return isinstance(v, np.ndarray) and v.ndim in (2, 3) and v.shape[0] > 1 and v.shape[1] > 1 \
        and (v.ndim == 2 or v.shape[2] in (1, 3, 4))


def _configure_jedi():
    """補完・ホバーでコードを実行しない設定(jedi が入っていれば)。"""
    try:
        import jedi
    except Exception:                                         # noqa: BLE001
        return False
    try:
        jedi.settings.allow_unsafe_interpreter_executions = False   # 実行後の値の属性を読むとき property 等を呼ばない
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
    return pm
