# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Tools ▸ Run a ledger op —— 台帳の op を型に合った入力欄で走らせる窓(2026-10-03)。

発端: Studio が走らせられたのは 2-D の進化 op だけで、台帳の ~1,700 op はヘルプの表を
読めても押して試す手段が無かった。見るのは: 入力欄が型どおりに出る / 見本で走る /
「直前の結果」で op を繋げる / 同じことをする 1 行の Python が出る / 失敗は窓に文字で出る。
"""
import os

import numpy as np
import pytest

import studio


def test_parse_param_follows_the_declared_kind():
    num = {"name": "s", "kind": "number", "default": 1.5, "container": {"form": "scalar"}}
    assert studio.parse_ledger_param(num, "") == 1.5            # 空欄 = 既定値
    assert studio.parse_ledger_param(num, "2.25") == 2.25
    assert studio.parse_ledger_param(num, "None") is None
    with pytest.raises(ValueError, match="expected number"):
        studio.parse_ledger_param(num, "abc")                    # 黙って既定値に戻さない
    seq = {"name": "c", "kind": "number", "default": (0.0, 0.0), "container": {"form": "vector"}}
    assert studio.parse_ledger_param(seq, "1, 2.5") == (1.0, 2.5)
    assert studio.parse_ledger_param({"name": "k", "kind": "int", "default": 3,
                                      "container": {"form": "scalar"}}, "7") == 7


def test_call_code_is_one_runnable_line():
    code = studio.ledger_call_code("piv_quiver", ["flow"], {"spacing": 4})
    assert code.splitlines()[-1] == "result = fs.ledger.piv_quiver(flow, spacing=4)"
    # 書いたコードがそのまま走る
    import fullseye as fs
    ns = {"fs": fs, "flow": np.stack([np.zeros((8, 8)), np.ones((8, 8))])}
    exec(code, ns)
    assert ns["result"].shape == (64, 64, 3)


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    return QtWidgets, QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_the_runner_builds_typed_fields_runs_a_sample_and_chains_results():
    QtWidgets, app = _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    assert "Run a ledger op" in win._act_ledger_run.text()
    dlg = win._open_ledger_runner("ode_vector_field_grid")
    st = dlg._state
    assert st["op"] == "ode_vector_field_grid"
    # 型どおりの入力欄: 文字の既定値は行入力、整数・実数・真偽はそれぞれの部品
    kinds = {type(w).__name__ for w in st["widgets"].values()}
    assert "QLineEdit" in kinds
    flow = dlg._run()
    assert flow is not None and flow.shape[0] == 2 and flow.ndim == 3, st["error"]
    assert "fs.ledger.ode_vector_field_grid(" in dlg._code.toPlainText()
    assert "flow2d" in dlg._info.toPlainText()
    assert dlg._pic.pixmap() is not None and not dlg._pic.pixmap().isNull()

    # 直前の結果(flow2d)を矢印図へ繋ぐ
    assert dlg._select("piv_quiver")
    src = dlg._state["sources"]["flow"]
    src.setCurrentIndex(studio.LEDGER_SOURCES.index("last result"))
    sp = dlg._state["widgets"]["spacing"]
    sp.setText("4")
    img = dlg._run()
    assert img is not None and img.ndim == 3 and img.shape[2] == 3, dlg._state["error"]
    assert dlg._code.toPlainText().splitlines()[-1] == \
        "result = fs.ledger.piv_quiver(result, spacing=4.0)"  # 台帳の宣言は実数


def test_a_bad_value_is_reported_in_the_window_not_raised():
    QtWidgets, app = _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    dlg = win._open_ledger_runner("piv_quiver")
    dlg._state["widgets"]["spacing"].setText("many")
    assert dlg._run() is None
    assert "spacing" in dlg._info.toPlainText() and "expected" in dlg._info.toPlainText()
    # 「直前の結果」をまだ持っていない新しい窓でそれを選ぶと、理由を言う
    dlg2 = win._open_ledger_runner("piv_flow_magnitude")
    dlg2._state["result"] = None
    dlg2._state["sources"]["flow"].setCurrentIndex(studio.LEDGER_SOURCES.index("last result"))
    assert dlg2._run() is None and "run once" in dlg2._info.toPlainText()


def test_the_current_image_feeds_image_ops():
    QtWidgets, app = _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    win._stage_list.setCurrentRow(-1)
    app.processEvents()
    assert isinstance(win._state.get("raw"), np.ndarray)
    dlg = win._open_ledger_runner("piv_flow_to_rgbimage")
    # flow2d の入力に「いまの画像」は渡せない(型が違う)→ 名指しで断る
    dlg._state["sources"]["flow"].setCurrentIndex(studio.LEDGER_SOURCES.index("current image"))
    assert dlg._run() is None and "flow2d" in dlg._info.toPlainText()


def test_search_falls_back_to_words_and_the_ui_is_translated():
    QtWidgets, app = _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    dlg = win._open_ledger_runner()
    dlg._search.setText("quiver")
    names = [dlg._op_list.item(i).text() for i in range(dlg._op_list.count())]
    assert names == ["piv_quiver"]
    studio._UI_LANG["code"] = "ja"
    try:
        dja = win._open_ledger_runner("piv_quiver")
        assert dja.windowTitle().startswith("台帳の op を実行")
        assert dja._auto.text() == "値を変えたら自動で再実行"
    finally:
        studio._UI_LANG["code"] = "en"


def test_the_window_runs_exactly_what_a_direct_call_runs():
    """窓で走るかどうかが、見本を**直接** op に渡したときと一致すること。

    窓が成績を悪くしていないかの門(2026-10-03: 3x3 の K を文字にして読み戻せず、
    直接なら通る形の引数を窓だけが落としていた)。見本そのものの質(opassist.sample_input)
    は別の話で、成功率は印字だけする(実測 60 本中 27 本。flow2d の見本を足す前は 26 本)。
    """
    import fullseye as fs
    import opassist
    QtWidgets, app = _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    names = studio.ledger_op_names()
    assert len(names) > 1500
    pick = names[:: max(1, len(names) // 60)][:60]
    dlg = win._open_ledger_runner()
    ok, differ = 0, []
    for n in pick:
        assert dlg._select(n), n
        out = dlg._run()
        try:
            data, kw = opassist.sample_input(n)
            getattr(fs.ledger, n)(*data, **kw)
            direct = True
        except Exception:                               # noqa: BLE001
            direct = False
        if (out is not None) != direct:
            differ.append((n, dlg._info.toPlainText()[:120]))
        if out is not None:
            ok += 1
        else:
            assert dlg._info.toPlainText(), n           # 失敗は理由が窓に出る
    print("ledger runner: %d / %d ops ran on their synthetic sample" % (ok, len(pick)))
    assert ok >= 20
    assert not differ, differ


def test_no_two_window_actions_share_a_shortcut():
    """★2026-10-03: Ctrl+Shift+O が Open pipeline と Image Viewer の両方に付いていた。
    Qt はあいまいなショートカットを**どちらも発火しない**ので、両方が黙って効かなくなる。"""
    QtWidgets, app = _app()
    from PySide6 import QtCore, QtGui
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    seen = {}
    dup = []
    acts = win.findChildren(QtGui.QAction)
    assert len(acts) > 50
    for a in acts:
        for ks in a.shortcuts():
            key = ks.toString()
            if not key or a.shortcutContext() == QtCore.Qt.WidgetShortcut:
                continue
            if key in seen and seen[key] is not a:
                dup.append((key, seen[key].text(), a.text()))
            seen.setdefault(key, a)
    assert not dup, dup
    assert seen.get("Ctrl+Shift+L") is win._act_ledger_run


# =========================================================================
# 見たもの・試したものを、少ない手数でコードへ(2026-10-03)
# =========================================================================

def test_the_window_script_runs_as_is_and_imports_merge_once():
    import fullseye as fs                               # noqa: F401
    t = studio.ledger_script("piv_quiver", [("flow", "sample")], {"spacing": 4.0})
    ns = {}
    exec(t, ns)                                         # 見本の作り直しまで含めて、そのまま走る
    assert ns["result"].ndim == 3
    doc, _ = studio.merge_script_into("import numpy as np\n", 19,
                                      studio.ledger_script("ode_vector_field_grid", [], {}))
    doc, pos = studio.merge_script_into(doc, len(doc),
                                        studio.ledger_script("piv_flow_magnitude", [("flow", "result")], {}))
    assert doc.count("import fullseye as fs") == 1 and doc.startswith("import fullseye as fs\n")
    ns = {}
    exec(doc, ns)
    assert ns["result"].ndim == 2                       # 場 → 速さ と繋がった
    assert pos == len(doc)


def test_call_templates_and_completions_save_keystrokes():
    text, pos = studio.ledger_call_template("dem_slope")
    assert text == "dem_slope(dem, cell_size=)" and text[pos - 1] == "="   # 最初の空欄へ
    text, pos = studio.ledger_call_template("ode_vector_field_grid")
    assert text == "ode_vector_field_grid()" and text[pos] == ")"           # 括弧の中
    word, cands, kind = studio.editor_completions("y = fs.ledger.piv_qu")
    assert (word, kind) == ("piv_qu", "ledger") and cands[0] == "piv_quiver"
    word, cands, kind = studio.editor_completions("img = fs.read_im")
    assert kind == "facade" and cands[0] == "read_image"
    assert studio.editor_completions("x = np.zer")[2] is None              # fs の外では出さない


def test_runner_to_editor_and_back_in_a_few_clicks():
    QtWidgets, app = _app()
    from PySide6 import QtCore, QtTest
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    dlg = win._open_ledger_runner("ode_vector_field_grid")
    assert dlg._run() is not None
    ed = dlg._insert()                                  # 1 クリック: エディタが開き、走るコードが入る
    assert "result = fs.ledger.ode_vector_field_grid()" in ed.toPlainText()
    dlg._select("piv_quiver")
    dlg._state["sources"]["flow"].setCurrentIndex(studio.LEDGER_SOURCES.index("last result"))
    assert dlg._run() is not None
    ed = dlg._insert()                                  # 2 回目は同じタブのカーソル位置へ、import は増えない
    txt = ed.toPlainText()
    assert txt.count("import fullseye as fs") == 1
    assert txt.index("ode_vector_field_grid") < txt.index("piv_quiver(result")
    ns = {}
    exec(dlg._session_script(), ns)                     # 履歴 = 繋いだ 2 手がそのまま走る
    assert ns["result"].ndim == 3 and ns["result"].shape[2] == 3

    # エディタで補完: fs.ledger.piv_qu → piv_quiver(flow)、カーソルは括弧の中の引数の後
    ed.selectAll(); ed.insertPlainText("")
    QtTest.QTest.keyClicks(ed, "fs.ledger.piv_qu")
    assert ed._completer.popup().isVisible() or ed._cmodel.stringList()[:1] == ["piv_quiver"]
    ed._insert_completion("piv_quiver")
    assert ed.toPlainText() == "fs.ledger.piv_quiver(flow)"
    # エディタ → 実行窓: カーソル下の op 名で開く
    cur = ed.textCursor(); cur.setPosition(14); ed.setTextCursor(cur)
    assert ed.word_under_cursor() == "piv_quiver"
    ed.on_open_ledger_op(ed.word_under_cursor())
    assert win._last_ledger_runner._state["op"] == "piv_quiver"


def test_the_command_palette_reaches_every_ledger_op():
    """Ctrl+P → 名前 → Enter の 3 手で、台帳のどの op の実行窓も開く。"""
    QtWidgets, app = _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    from PySide6 import QtCore
    assert win._actions["ledger_run"] is win._act_ledger_run

    def type_and_enter():
        win._palette["edit"].setText("ledger: piv_quiver")
        win._palette["run"]()
    QtCore.QTimer.singleShot(0, type_and_enter)        # パレットは exec() で開く → 開いた直後に打つ
    win._actions["palette"].trigger()
    assert win._last_ledger_runner._state["op"] == "piv_quiver"
    assert any(lbl.startswith("ledger: ") for lbl in win._palette["labels"])
