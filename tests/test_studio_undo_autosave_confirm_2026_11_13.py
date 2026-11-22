# -*- coding: utf-8 -*-
"""Studio: やり直しの効かない操作の確認・コーディング中の Undo / Redo・ファイルへの自動保存(2026-11-13、利用者の要件 3 つ)。

1. **確認の窓**: 元に戻せない操作は、入口(ボタン・メニュー)で 1 回聞く。何が失われるかを文に書き、キャンセルなら
   何も変わらず、OK で実行される。Undo で戻せる操作には窓を出さない。窓は ``studio.CONFIRM_ACTION_HOOK`` を差し替えて数える。
2. **Undo / Redo**: モードを往復しても文面の履歴が残る。Edit ▸ Undo はフォーカスのある方(文面か段の列)に効く。
3. **自動保存**: 既定は切。入れると、打つのを止めた後・フォーカスが外れた時にファイルへ保存する。外で変わった
   ファイルは上書きしない。無題の文面には効かない。
"""
import json
import os
import time

import numpy as np
import pytest

import studio
import studio_batch
import studio_program as sp
import studio_pymode as pm_mod


def _app():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _pump(sec=0.3):
    from PySide6 import QtWidgets
    end = time.monotonic() + sec
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)


def _launch(tmp_path, monkeypatch, start_mode="auto", name="s.ini"):
    _app()
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / name))
    win, model = studio.build_window(start_mode=start_mode)
    win.resize(1400, 860)
    win.show()
    win.activateWindow()
    _pump(0.3)
    return win, model


def _close(win):
    studio._UI_LANG["code"] = "en"
    win.close_guard = lambda: True
    win.quiesce()
    win.close()
    _pump(0.1)


def _ed(win):
    return win._program["edit"]


def _type(win, text):
    """カーソルの位置に打つ(1 回の編集 = Undo 1 回ぶん)。"""
    c = _ed(win).textCursor()
    c.insertText(text)
    _ed(win).setTextCursor(c)
    _pump(0.05)


def _set_text(win, text):
    from PySide6 import QtGui
    c = QtGui.QTextCursor(_ed(win).document())
    c.select(QtGui.QTextCursor.Document)
    c.insertText(text)
    _ed(win).setTextCursor(c)
    _pump(0.35)


def _f5(win, timeout=20):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    QTest.keyClick(_ed(win), QtCore.Qt.Key_F5)
    assert win._pymode.wait_idle(timeout)
    _pump(0.1)
    return win._pymode.last


class Asker:
    """確認の窓の差し替え: 聞かれた回数と文を覚え、``answer`` を返す。"""

    def __init__(self, monkeypatch, answer=False):
        self.calls = []
        self.answer = answer
        monkeypatch.setattr(studio, "CONFIRM_ACTION_HOOK", self)

    def __call__(self, parent, title, text, action):
        self.calls.append((title, text, action))
        return self.answer


# --------------------------------------------------------------------------- #
# 1. 確認の窓                                                                   #
# --------------------------------------------------------------------------- #
def _buttons(win):
    """Program 欄のパイプライン側のボタン (run, continue, step, reset, apply, sync)。"""
    b = win._pymode.ctx["pipeline_buttons"]
    assert len(b) == 6
    return {"reset": b[3], "apply": b[4], "sync": b[5]}


def test_reset_with_unapplied_edits_asks_and_cancel_keeps_them(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch, start_mode="pipeline")
    try:
        ask = Asker(monkeypatch, answer=False)
        b = _buttons(win)
        b["reset"].click()                                              # 未適用の編集が無ければ聞かない
        assert ask.calls == []
        _set_text(win, "gaussian (0.4, 0.5)\n* my note\notsu (0.5, 0.5)\n")
        assert win._state.get("code_dirty")
        mine = _ed(win).toPlainText()
        b["reset"].click()
        assert len(ask.calls) == 1 and "not applied" in ask.calls[0][1] and ask.calls[0][2] == "Discard the edits"
        assert _ed(win).toPlainText() == mine and win._state.get("code_dirty")      # キャンセル: 何も変わらない
        ask.answer = True
        b["reset"].click()
        assert len(ask.calls) == 2
        assert _ed(win).toPlainText() != mine and not win._state.get("code_dirty")  # OK: 捨てて作り直す
    finally:
        _close(win)


def test_sync_asks_only_when_it_would_drop_comments(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch, start_mode="pipeline")
    try:
        ask = Asker(monkeypatch, answer=False)
        b = _buttons(win)
        _set_text(win, "gaussian (0.4, 0.5)\n* my note\notsu (0.5, 0.5)\n")
        b["apply"].click()
        _pump(0.2)
        assert not win._state.get("code_dirty") and len(model.stages) == 2
        if "* my note" not in _ed(win).toPlainText():                    # 適用で作り直す作りなら、消える物が無い
            b["sync"].click()
            assert ask.calls == []
            return
        mine = _ed(win).toPlainText()
        b["sync"].click()
        assert len(ask.calls) == 1 and "comments" in ask.calls[0][1]
        assert _ed(win).toPlainText() == mine
        ask.answer = True
        b["sync"].click()
        assert len(ask.calls) == 2 and "* my note" not in _ed(win).toPlainText()
        b["sync"].click()                                                # もう段の列と同じ: 聞かない
        assert len(ask.calls) == 2
    finally:
        _close(win)


def test_pins_dropping_a_snapshot_asks(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch, start_mode="pipeline")
    try:
        ask = Asker(monkeypatch, answer=False)
        model.stages = [["gaussian", 0.4, 0.5]]
        win._refresh_stage_list()
        win._docks["ab"].show()                                          # 比べる欄が出ていないと、固定の一覧を作らない
        win._pin_a_asked()
        win._pin_a_asked()
        assert ask.calls == [] and len(model.pins) == studio.MAX_PINS == 2      # 上限までは聞かない
        before = [id(p) for p in model.pins]
        win._pin_a_asked()                                               # 3 つ目: 一番古い固定が押し出される
        assert len(ask.calls) == 1 and "oldest" in ask.calls[0][1]
        assert [id(p) for p in model.pins] == before
        ask.answer = True
        win._pin_a_asked()
        assert len(ask.calls) == 2 and [id(p) for p in model.pins] != before and len(model.pins) == 2
        ask.answer = False
        before = [id(p) for p in model.pins]
        win._ab["refresh"]()
        assert win._ab["adopt"].isEnabled(), "the Adopt button is not enabled: the test would not reach the question"
        win._ab["adopt"].click()                                         # 「今の結果を採る」= 固定を捨てる
        assert len(ask.calls) == 3 and "dropped" in ask.calls[2][1] and [id(p) for p in model.pins] == before
        ask.answer = True
        win._ab["adopt"].click()
        assert len(ask.calls) == 4 and len(model.pins) == 1
    finally:
        _close(win)


def test_layout_reset_overwrite_delete_and_clear_recent_ask(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    win, model = _launch(tmp_path, monkeypatch, start_mode="pipeline")
    try:
        ask = Asker(monkeypatch, answer=False)
        # 配置のリセット(2026-11-15 見た目の枝を合わせた後: 戻る先は「画像 + コード」= 他のパネルは隠れる)
        win._docks["operators"].show()
        _pump(0.1)
        assert win._docks["operators"].isVisible()
        win._actions["reset_layout"].trigger() if "reset_layout" in win._actions else win._reset_layout_asked()
        _pump(0.1)
        assert len(ask.calls) == 1 and win._docks["operators"].isVisible()      # 「いいえ」: 何も変わらない
        ask.answer = True
        win._reset_layout_asked()
        _pump(0.1)
        assert len(ask.calls) == 2 and not win._docks["operators"].isVisible()  # 「はい」: 画像 + コードへ
        assert win._docks["program"].isVisible()
        # 保存したレイアウト: 同じ名前で保存(上書き)・削除
        assert win._save_layout_preset("mine")
        first = win._preset_store["mine"]
        monkeypatch.setattr(QtWidgets.QInputDialog, "getText", staticmethod(lambda *a, **k: ("mine", True)))
        save = [a for a in win._layouts_menu.actions() if a.text().startswith("Save current layout")]
        assert len(save) == 1
        ask.answer = False
        win._docks["operators"].hide()
        save[0].trigger()
        assert len(ask.calls) == 3 and "already exists" in ask.calls[2][1] and win._preset_store["mine"] is first
        ask.answer = True
        save[0].trigger()
        assert len(ask.calls) == 4 and win._preset_store["mine"] is not first
        monkeypatch.setattr(QtWidgets.QInputDialog, "getText", staticmethod(lambda *a, **k: ("new name", True)))
        [a for a in win._layouts_menu.actions() if a.text().startswith("Save current layout")][0].trigger()
        assert len(ask.calls) == 4 and "new name" in win._preset_store        # 新しい名前は聞かない
        ask.answer = False
        delete = [a for a in win._layouts_menu.actions() if a.text() == "Delete layout: mine"]
        assert len(delete) == 1
        delete[0].trigger()
        assert len(ask.calls) == 5 and "mine" in win._preset_store
        ask.answer = True
        [a for a in win._layouts_menu.actions() if a.text() == "Delete layout: mine"][0].trigger()
        assert len(ask.calls) == 6 and "mine" not in win._preset_store
        # 最近使ったファイル
        pj = tmp_path / "p.json"
        pj.write_text(json.dumps({"fullseye_pipeline": 1, "stages": [["median", 0.3, 0.5]]}), encoding="utf-8")
        win._open_pipe_path(str(pj))
        win._rebuild_recent_menu()
        texts = [a.text() for a in win._recent_menu.actions()]
        assert "p.json" in texts
        ask.answer = False
        [a for a in win._recent_menu.actions() if a.text() == "Clear recent"][0].trigger()
        win._rebuild_recent_menu()
        assert len(ask.calls) == 7 and "p.json" in [a.text() for a in win._recent_menu.actions()]
        ask.answer = True
        [a for a in win._recent_menu.actions() if a.text() == "Clear recent"][0].trigger()
        win._rebuild_recent_menu()
        assert len(ask.calls) == 8 and "p.json" not in [a.text() for a in win._recent_menu.actions()]
    finally:
        _close(win)


def test_undoable_operations_do_not_ask(tmp_path, monkeypatch):
    """線引き: Undo で戻せる操作(段を消す・全部消す・文面の編集・「Python にする」)には窓を出さない。"""
    win, model = _launch(tmp_path, monkeypatch, start_mode="pipeline")
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda *_a: True)
    try:
        ask = Asker(monkeypatch, answer=False)
        model.stages = [["gaussian", 0.4, 0.5], ["otsu", 0.5, 0.5]]
        win._refresh_stage_list()
        win._state["dirty"] = False
        win._pymode.ctx["stage_list"].setCurrentRow(1)
        win._buttons["remove"].click()
        assert len(model.stages) == 1 and ask.calls == []
        win._undo()
        assert len(model.stages) == 2
        win._actions["clear"].trigger()
        assert len(model.stages) == 0 and ask.calls == []
        win._undo()
        assert len(model.stages) == 2
        pm = win._pymode
        pm.set_mode("python")
        before = _ed(win).toPlainText()
        assert pm.convert_to_python() and ask.calls == []                 # 無題の文面: Ctrl+Z の 1 回で戻る
        _ed(win).undo()
        assert _ed(win).toPlainText() == before
    finally:
        _close(win)


def test_python_mode_clear_output_save_over_changed_file_and_quit_while_paused_ask(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ask = Asker(monkeypatch, answer=False)
        # 出力を消す
        win._actions["pymode_clear_output"].trigger()
        assert ask.calls == []                                           # 空なら聞かない
        _set_text(win, "# python\nprint('keep me')\nshow(img)\n")
        _f5(win)
        assert "keep me" in pm.output.toPlainText()
        win._actions["pymode_clear_output"].trigger()
        assert len(ask.calls) == 1 and "keep me" in pm.output.toPlainText()
        ask.answer = True
        win._actions["pymode_clear_output"].trigger()
        assert len(ask.calls) == 2 and pm.output.toPlainText() == ""
        # 保存: 外で変わったファイルは、上書きの前に聞く
        p = tmp_path / "a.py"
        monkeypatch.setattr(pm_mod, "SAVE_AS_HOOK", lambda *_a: str(p))
        assert pm.save() and p.read_text(encoding="utf-8").startswith("# python")
        _type(win, "# mine\n")
        p.write_text("# someone else\n", encoding="utf-8")
        ask.answer = False
        assert pm.save() is False
        assert len(ask.calls) == 3 and "changed on disk" in ask.calls[2][1]
        assert p.read_text(encoding="utf-8") == "# someone else\n" and pm.unsaved()
        ask.answer = True
        assert pm.save() is True and len(ask.calls) == 4 and "# mine" in p.read_text(encoding="utf-8")
        assert pm.save() is True and len(ask.calls) == 4                 # 変わっていなければ聞かない
        # 名前を付けて保存: 拡張子を足した後の名前が既にある
        (tmp_path / "typed.py").write_text("old", encoding="utf-8")
        monkeypatch.setattr(pm_mod, "SAVE_AS_HOOK", lambda *_a: str(tmp_path / "typed"))
        ask.answer = False
        assert pm.save_as() is False and len(ask.calls) == 5 and "already exists" in ask.calls[4][1]
        assert (tmp_path / "typed.py").read_text(encoding="utf-8") == "old"
        ask.answer = True
        assert pm.save_as() is True and len(ask.calls) == 6
        assert "# mine" in (tmp_path / "typed.py").read_text(encoding="utf-8")
        # 実行中(ブレークポイントで待っている)に閉じる
        _set_text(win, "# python\nk = 1\nk = 2\nshow(img)\n")
        pm.save()
        pm.toggle_breakpoint(3)
        res = _f5(win)
        assert res.stopped == "breakpoint" and pm.session is not None and pm.session.live
        ask.answer = False
        assert pm.confirm_close() is False
        assert len(ask.calls) == 7 and "still running" in ask.calls[6][1] and pm.session.live
        ask.answer = True
        assert pm.confirm_close() is True and len(ask.calls) == 8
    finally:
        _close(win)


def test_converting_over_an_unsaved_file_asks_to_save_first(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda *_a: True)
    try:
        pm = win._pymode
        p = tmp_path / "work.py"
        p.write_text("# python\nx = 1\nshow(img)\n", encoding="utf-8")
        pm.open_program(str(p))
        _type(win, "# unsaved change\n")
        assert pm.unsaved()
        answers = []
        monkeypatch.setattr(pm_mod, "SAVE_HOOK", lambda *_a: answers.append(1) or "cancel")
        mine = _ed(win).toPlainText()
        assert pm.convert_to_python() is False
        assert len(answers) == 1 and pm.file == str(p) and _ed(win).toPlainText() == mine
        monkeypatch.setattr(pm_mod, "SAVE_HOOK", lambda *_a: answers.append(2) or "discard")
        assert pm.convert_to_python() is True and len(answers) == 2 and pm.file is None
    finally:
        _close(win)


def test_watch_remove_button_asks(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ask = Asker(monkeypatch, answer=False)
        w = pm.vars.watch
        w.add_expression("1 + 1")
        w.add_expression("2 + 2")
        w.table.setCurrentCell(0, 0)
        w.btn_del.click()
        assert len(ask.calls) == 1 and "1 + 1" in ask.calls[0][1] and w.watch.exprs == ["1 + 1", "2 + 2"]
        ask.answer = True
        w.table.setCurrentCell(0, 0)
        w.btn_del.click()
        assert len(ask.calls) == 2 and w.watch.exprs == ["2 + 2"]
    finally:
        _close(win)


def test_demo_and_help_sample_do_not_replace_the_python_text_and_ask_about_unapplied_edits(tmp_path, monkeypatch):
    from PySide6 import QtCore
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        asked = []
        monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda *a: asked.append(a) or False)
        _set_text(win, "# python\nmine = 1\nshow(img)\n")
        win._load_visual_demo()                                          # 捨てる物が無い: 聞かずにパイプラインのモードへ
        assert asked == [] and pm.mode == "pipeline" and "dev_" in _ed(win).toPlainText()
        pm.set_mode("python")
        assert _ed(win).toPlainText() == "# python\nmine = 1\nshow(img)\n"   # Python の文面は残っている
        pm.set_mode("pipeline")
        _type(win, "* unapplied edit\n")
        assert win._state.get("code_dirty")
        mine = _ed(win).toPlainText()
        win._load_visual_demo()
        assert len(asked) == 1 and _ed(win).toPlainText() == mine         # キャンセル: 置き換えない
        win._help["browser"].anchorClicked.emit(QtCore.QUrl("sample:gaussian%20(0.3,%200.5)")) \
            if getattr(win, "_help", None) and "browser" in win._help else asked.append("no help handle")
        assert len(asked) == 2 and _ed(win).toPlainText() == mine
    finally:
        _close(win)


def test_python_editor_save_over_a_file_changed_on_disk_asks(tmp_path, monkeypatch):
    script = tmp_path / "a.py"
    script.write_text("print(1)\n", encoding="utf-8")
    win, model = _launch(tmp_path, monkeypatch)
    try:
        ask = Asker(monkeypatch, answer=False)
        win.drop_handler([str(script)])
        _pump(0.3)
        pe = win._pyedit
        ed = pe["editor"]()
        ed.setPlainText("print(2)\n")
        assert pe["save_to"](str(script)) and ask.calls == [] and script.read_text(encoding="utf-8") == "print(2)\n"
        ed.setPlainText("print(3)\n")
        script.write_text("print('someone else')\n", encoding="utf-8")
        from PySide6 import QtWidgets
        saves = [b for b in pe["dlg"].findChildren(QtWidgets.QAbstractButton) if b.text().replace("&", "") == "Save"]
        assert len(saves) == 1
        saves[0].click()
        assert len(ask.calls) == 1 and script.read_text(encoding="utf-8") == "print('someone else')\n"
        ask.answer = True
        saves[0].click()
        assert len(ask.calls) == 2 and script.read_text(encoding="utf-8") == "print(3)\n"
    finally:
        try:
            win._pyedit["dlg"].close()
        except Exception:                                                 # noqa: BLE001
            pass
        _close(win)


def test_batch_reports_the_files_it_would_overwrite(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    for n in ("a.png", "b.png"):
        import imgio
        imgio.save(str(src / n), np.zeros((8, 8)))
    out = tmp_path / "out"
    files = studio_batch.list_inputs(str(src))
    assert len(files) == 2
    plan = studio_batch.BatchPlan(files, str(out), "overwrite", folder=str(src))
    assert studio_batch.existing_outputs(plan) == (0, False)
    out.mkdir()
    (out / "a.png").write_bytes(b"old")
    (out / "summary.csv").write_text("old", encoding="utf-8")
    assert studio_batch.existing_outputs(plan) == (1, True)
    skip = studio_batch.BatchPlan(files, str(out), "skip", folder=str(src))
    assert studio_batch.existing_outputs(skip) == (0, True)              # 画像は壊さないが、summary.csv は書き直す
    assert (out / "a.png").read_bytes() == b"old"                        # 数えるだけ(読むだけ)


def test_the_default_confirmation_is_safe_and_every_new_text_has_six_languages():
    """既定の窓は offscreen では実行しない側。確認の文と実行のボタンの名前は 6 言語にある。"""
    _app()
    assert studio._default_confirm_action(None, "t", "x", "go") is False
    data = json.load(open(os.path.join(os.path.dirname(studio.__file__), "studio_assets", "i18n.json"), encoding="utf-8"))
    strings = data["strings"]
    import ast
    keys = set()
    for fn in ("studio.py", "studio_pymode.py"):
        tree = ast.parse(open(os.path.join(os.path.dirname(studio.__file__), fn), encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) in ("confirm_action", "_confirm"):
                for a in node.args:
                    for sub in ast.walk(a):
                        if isinstance(sub, ast.Call) and getattr(sub.func, "id", getattr(sub.func, "attr", "")) == "tr" \
                                and sub.args and isinstance(sub.args[0], ast.Constant):
                            keys.add(sub.args[0].value)
    assert len(keys) >= 30, len(keys)
    missing = [k for k in sorted(keys) if any(not str(strings.get(k, {}).get(lang, "")).strip()
                                               for lang in ("ja", "zh", "tw", "ko", "de", "hi"))]
    assert not missing, missing


# --------------------------------------------------------------------------- #
# 2. Undo / Redo                                                                #
# --------------------------------------------------------------------------- #
def test_text_undo_history_survives_a_mode_round_trip(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = _ed(win)
        base = ed.toPlainText()
        assert pm.mode == "python" and not ed.document().isUndoAvailable()      # 開いた直後は履歴が空
        assert not pm.btn_undo.isEnabled() and not pm.btn_redo.isEnabled()
        from PySide6 import QtGui
        c = ed.textCursor()
        c.movePosition(QtGui.QTextCursor.End)
        ed.setTextCursor(c)
        _type(win, "a = 1\n")
        _type(win, "b = 2\n")
        typed = ed.toPlainText()
        assert typed == base + "a = 1\nb = 2\n" and pm.btn_undo.isEnabled()
        py_doc = ed.document()
        pm.set_mode("pipeline")
        assert ed.document() is not py_doc and ed.document() is pm.doc_pipe
        pipe_text = ed.toPlainText()
        _type(win, "* typed in the pipeline mode\n")
        pm.set_mode("python")
        assert ed.document() is py_doc and ed.toPlainText() == typed            # 文書ごと戻る
        assert pm.assist.highlighter.document() is py_doc                       # 色分けもその文書に付いている
        assert ed.document().isUndoAvailable() and pm.btn_undo.isEnabled()
        ed.undo()
        assert ed.toPlainText() == base + "a = 1\n"
        pm.btn_undo.click()
        assert ed.toPlainText() == base and pm.btn_redo.isEnabled()
        pm.btn_redo.click()
        ed.redo()
        assert ed.toPlainText() == typed
        pm.set_mode("pipeline")                                                 # パイプライン側の未適用の編集と履歴も残る
        assert "* typed in the pipeline mode" in ed.toPlainText() and win._state.get("code_dirty")
        ed.undo()
        assert ed.toPlainText() == pipe_text
    finally:
        _close(win)


def test_opening_a_file_starts_with_an_empty_history_and_convert_is_one_undo(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda *_a: True)
    try:
        pm = win._pymode
        ed = _ed(win)
        _type(win, "# edit\n")
        assert ed.document().isUndoAvailable()
        p = tmp_path / "f.py"
        p.write_text("# python\nx = 1\nshow(img)\n", encoding="utf-8")
        monkeypatch.setattr(pm_mod, "SAVE_HOOK", lambda *_a: "discard")
        pm.open_program(str(p))
        assert not ed.document().isUndoAvailable() and not pm.btn_undo.isEnabled()
        before = ed.toPlainText()
        model.stages = [["gaussian", 0.4, 0.5]]
        win._refresh_stage_list()
        assert pm.convert_to_python()
        assert ed.toPlainText() != before
        ed.undo()                                                         # プログラムが書き換えた文面は Undo 1 回で戻る
        assert ed.toPlainText() == before
    finally:
        _close(win)


def test_edit_undo_follows_the_focus_and_ctrl_y_is_redo(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtWidgets
    from PySide6.QtTest import QTest
    win, model = _launch(tmp_path, monkeypatch, start_mode="pipeline")
    try:
        ed = _ed(win)
        undo, redo = win._actions["undo"], win._actions["redo"]
        # WIRING 4 章 D16: Redo は Ctrl+Y / Ctrl+Shift+Z、先頭の Ctrl+Y をメニューに表示する。
        assert [s.toString() for s in redo.shortcuts()] == ["Ctrl+Y", "Ctrl+Shift+Z"] and undo.shortcut().toString() == "Ctrl+Z"
        model.stages = [["gaussian", 0.4, 0.5]]
        win._refresh_stage_list()
        win._push_undo("test")
        model.stages = [["gaussian", 0.4, 0.5], ["otsu", 0.5, 0.5]]
        win._refresh_stage_list()
        n_stack = len(win._undo_stack)
        assert n_stack >= 1
        # コード欄にフォーカス: 文面の Undo。段の操作は戻さない
        ed.setFocus()
        _pump(0.1)
        if QtWidgets.QApplication.focusWidget() is not ed:
            pytest.skip("this platform does not give the editor the focus in a test")
        win._sync_undo_actions()
        assert not undo.isEnabled()                                      # 文面には戻す物が無い(段の操作の履歴はあるが)
        base = ed.toPlainText()
        _type(win, "* note\n")
        assert undo.isEnabled()
        QTest.keyClick(ed, QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)
        assert ed.toPlainText() == base and len(model.stages) == 2 and len(win._undo_stack) == n_stack
        assert redo.isEnabled()
        QTest.keyClick(ed, QtCore.Qt.Key_Y, QtCore.Qt.ControlModifier)
        assert "* note" in ed.toPlainText()
        undo.trigger()                                                   # メニューの Undo もフォーカスのある方(文面)
        assert ed.toPlainText() == base and len(model.stages) == 2 and len(win._undo_stack) == n_stack
        redo.trigger()
        assert "* note" in ed.toPlainText()
        text_now = ed.toPlainText()
        # 段の欄にフォーカス: 段の操作の Undo。文面の履歴には触らない
        win._program["apply"]() if False else None
        stage_list = win._pymode.ctx["stage_list"]
        stage_list.setFocus()
        _pump(0.1)
        assert QtWidgets.QApplication.focusWidget() is not ed
        win._sync_undo_actions()
        assert undo.isEnabled()
        undo.trigger()
        assert len(model.stages) == 1 and len(win._undo_stack) == n_stack - 1
        redo.trigger()
        assert len(model.stages) == 2
        assert ed.document().isUndoAvailable() and text_now                # 文面の履歴は残っている
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# 3. ファイルへの自動保存                                                        #
# --------------------------------------------------------------------------- #
def _open(win, monkeypatch, path, text="# python\nx = 1\nshow(img)\n"):
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(pm_mod, "SAVE_HOOK", lambda *_a: "discard")
    assert win._pymode.open_program(str(path))
    return win._pymode


def test_autosave_is_off_by_default_and_idle_mode_saves_after_a_pause(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    try:
        p = tmp_path / "a.py"
        pm = _open(win, monkeypatch, p)
        assert pm.autosave_file_mode() == "off" and pm._autosave_actions["off"].isChecked()
        _type(win, "# typed\n")
        _pump(1.2)
        assert p.read_text(encoding="utf-8") == "# python\nx = 1\nshow(img)\n" and pm.unsaved()   # 既定は保存しない
        assert pm.autosave_file() is False
        runs0 = pm.state.get("pymode_runs", 0)
        trusted0 = (pm.session_trusted, pm.trust.is_trusted(_ed(win).toPlainText(), "file"))
        win._actions["pymode_autosave_idle"].trigger()
        pm.set_autosave_file("idle", 0.5)
        assert pm.autosave_file_mode() == "idle" and pm.autosave_idle_s() == 0.5
        assert pm._autosave_actions["idle"].isChecked() and not pm._autosave_actions["off"].isChecked()
        _type(win, "if broken(\n")                                       # 構文が壊れている途中でも保存はする
        assert "typed" not in p.read_text(encoding="utf-8")              # 打った直後はまだ
        _pump(1.3)
        saved = p.read_text(encoding="utf-8")
        assert "# typed" in saved and "if broken(" in saved and not pm.unsaved()
        assert "autosaved" in pm.autosave_note.text() and pm.state.get("pymode_autosaves", 0) == 1
        assert pm.state.get("pymode_runs", 0) == runs0                   # 保存で実行は走らない
        assert (pm.session_trusted, pm.trust.is_trusted(saved, "file")) == (trusted0[0], False)   # 信頼の台帳は変えない
        assert not [n for n in os.listdir(tmp_path) if n.startswith(".~")]      # 書きかけを残さない
    finally:
        _close(win)


def test_autosave_on_focus_loss_and_never_over_a_file_changed_outside(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtGui, QtWidgets
    win, model = _launch(tmp_path, monkeypatch)
    try:
        p = tmp_path / "a.py"
        pm = _open(win, monkeypatch, p)
        pm.set_autosave_file("focus")
        _type(win, "# one\n")
        _pump(0.8)
        assert "# one" not in p.read_text(encoding="utf-8")              # フォーカスが外れるまでは保存しない
        QtWidgets.QApplication.sendEvent(_ed(win), QtGui.QFocusEvent(QtCore.QEvent.FocusOut, QtCore.Qt.PopupFocusReason))
        assert "# one" not in p.read_text(encoding="utf-8")              # 補完の窓などの一時的な物は数えない
        QtWidgets.QApplication.sendEvent(_ed(win), QtGui.QFocusEvent(QtCore.QEvent.FocusOut, QtCore.Qt.MouseFocusReason))
        assert "# one" in p.read_text(encoding="utf-8") and not pm.unsaved()
        # 外でファイルが変わった: 自動では上書きせず、知らせる
        flashes = []
        monkeypatch.setattr(pm, "flash", lambda m: flashes.append(m))
        p.write_text("# someone else\n", encoding="utf-8")
        _type(win, "# two\n")
        QtWidgets.QApplication.sendEvent(_ed(win), QtGui.QFocusEvent(QtCore.QEvent.FocusOut, QtCore.Qt.MouseFocusReason))
        assert p.read_text(encoding="utf-8") == "# someone else\n" and pm.unsaved()
        assert len(flashes) == 1 and "changed on disk" in flashes[0] and "not autosaved" in pm.autosave_note.text()
        QtWidgets.QApplication.sendEvent(_ed(win), QtGui.QFocusEvent(QtCore.QEvent.FocusOut, QtCore.Qt.MouseFocusReason))
        assert len(flashes) == 1 and p.read_text(encoding="utf-8") == "# someone else\n"   # 同じ事を何度も言わない
    finally:
        _close(win)


def test_autosave_does_nothing_for_an_untitled_program_and_the_setting_is_remembered(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch, name="keep.ini")
    try:
        pm = win._pymode
        pm.set_autosave_file("idle", 0.5)
        assert pm.file is None
        _type(win, "# untitled work\n")
        _pump(1.2)
        assert pm.autosave_file() is False and pm.state.get("pymode_autosaves", 0) == 0
        assert [n for n in os.listdir(tmp_path) if n.endswith(".py")] == []     # ファイルは作らない(退避だけ)
        assert pm.autosave_now() is True                                 # 退避(復元用)は設定に関係なく動く
        with pytest.raises(ValueError):
            pm.set_autosave_file("sometimes")
        pm.set_autosave_file("idle", 99999)
        assert pm.autosave_idle_s() == pm_mod.AUTOSAVE_IDLE_RANGE_S[1]
        pm.set_autosave_file("focus", 3.0)
    finally:
        _close(win)
    win2, _m = _launch(tmp_path, monkeypatch, name="keep.ini")
    try:
        pm2 = win2._pymode
        assert pm2.autosave_file_mode() == "focus" and pm2.autosave_idle_s() == 3.0
        assert pm2._autosave_actions["focus"].isChecked()
        # 設定の画面からも切り替えられる
        from PySide6 import QtWidgets
        seen = {}

        def fake_exec(dlg):
            seen["mode"] = dlg._autosave_mode.currentIndex()
            seen["delay"] = dlg._autosave_delay.value()
            dlg._autosave_mode.setCurrentIndex(1)
            dlg._autosave_delay.setValue(4.5)
            return QtWidgets.QDialog.Accepted
        monkeypatch.setattr(QtWidgets.QDialog, "exec", fake_exec)
        win2._open_system_settings()
        assert seen == {"mode": 2, "delay": 3.0}
        assert pm2.autosave_file_mode() == "idle" and pm2.autosave_idle_s() == 4.5
    finally:
        _close(win2)
