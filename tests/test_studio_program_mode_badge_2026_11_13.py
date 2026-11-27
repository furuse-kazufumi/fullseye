# -*- coding: utf-8 -*-
"""Studio: Program 欄がパイプラインか Python かを、常に・一目で分かるようにする(2026-11-13、利用者の要件)。

- 札(Program 欄の左上): 印(形)+ モードの名前 + 色。切り替えのボタンの押された状態に頼らない。
- パネルの題(``Program (code) — Python``)と、窓の下の状態の帯にも出る。
- 起動直後・切り替え後・ファイルを開いた後(Python のファイルもパイプラインのファイルも)・変換後に、札が追従する。
- 文面とモードが食い違っている時(書き方が逆・2 つが混ざっている)は札に警告の印と琥珀の縁。押すと選択肢が出る。
  勝手には切り替えない。
- 実行のボタン・ツールヒント・F5 の入口(Run all / F5 の動作 / Ctrl+Return のボタン)・出力の見出しが「Python として」と言う。
- 札の文字と地のコントラスト比は、2 つの配色とも 4.5 以上。
- 打っている最中(1 打ごと)は文面を読み直さない(間を置いた検査が読み直す)。
"""
import json
import os
import time

import pytest

import studio
import studio_program as sp
import studio_pymode as pm_mod

LANGS = ("ja", "zh", "tw", "ko", "de", "hi")
PY_TEXT = "# python\nimport numpy as np\nx = np.zeros(3)\nfor i in range(3):\n    x[i] = i\nshow(img)\n"
PIPE_TEXT = "gaussian (0.4, 0.5)\nsobel_mag (0.5, 0.5)\n"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _table():
    with open(os.path.join(HERE, "studio_assets", "i18n.json"), encoding="utf-8") as fh:
        return json.load(fh)["strings"]


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


def _launch(tmp_path, monkeypatch, start_mode="pipeline"):
    _app()
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "s.ini"))
    win, model = studio.build_window(start_mode=start_mode)
    win.resize(1400, 860)
    win.show()
    _pump(0.3)
    return win, model


def _close(win):
    studio._UI_LANG["code"] = "en"
    win.close_guard = lambda: True
    win.quiesce()
    win.close()
    _pump(0.1)


def _says(win, mode_word):
    """札・パネルの題・状態の帯・題のための文字列が、4 つとも *mode_word* を言っているか(言っていない所の一覧)。"""
    pm = win._pymode
    places = {"badge": pm.badge.text(), "title_string": pm.mode_title(),
              "dock_title": win._docks["program"].windowTitle(), "status": win._mode_status.text()}
    return [k for k, v in places.items() if mode_word not in v]


def test_the_badge_the_title_and_the_status_bar_name_the_mode_at_launch_and_after_a_switch(tmp_path, monkeypatch):
    win, _ = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        assert pm.mode == pm_mod.MODE_PIPELINE
        assert _says(win, "Pipeline") == [] and "Python" not in pm.badge.text()
        assert pm.badge.text().startswith(pm_mod.BADGE_GLYPHS[pm_mod.MODE_PIPELINE])   # 形でも言う(色だけに頼らない)
        assert pm.mode_title_en() == "Program (code) — Pipeline"
        assert pm.badge.isVisible() and pm.badge.toolTip()
        pm.set_mode(pm_mod.MODE_PYTHON)
        assert _says(win, "Python") == [] and "Pipeline" not in pm.badge.text()
        assert pm.badge.text().startswith(pm_mod.BADGE_GLYPHS[pm_mod.MODE_PYTHON])
        assert pm.mode_title_en() == "Program (code) — Python"
        pm.set_mode(pm_mod.MODE_PIPELINE)
        assert _says(win, "Pipeline") == []
    finally:
        _close(win)


def test_a_first_launch_in_python_mode_says_python(tmp_path, monkeypatch):
    win, _ = _launch(tmp_path, monkeypatch, start_mode="auto")
    try:
        assert win._pymode.active and _says(win, "Python") == []
    finally:
        _close(win)


def test_the_badge_follows_opening_a_file_and_converting(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    old = pm_mod.TRUST_HOOK
    pm_mod.TRUST_HOOK = lambda *_a: True
    try:
        pm = win._pymode
        p = tmp_path / "a.py"
        p.write_text(PY_TEXT, encoding="utf-8")
        assert _says(win, "Pipeline") == []
        pm.open_program(str(p))                                # ファイルを開く → Python
        assert pm.active and _says(win, "Python") == [] and pm.mode_mismatch() is None
        pm.set_mode(pm_mod.MODE_PIPELINE)
        assert _says(win, "Pipeline") == []
        model.add_stage("gaussian")
        _pump(0.2)
        assert pm.convert_to_python() is not False             # 変換 → Python
        assert pm.active and _says(win, "Python") == []
    finally:
        pm_mod.TRUST_HOOK = old
        _close(win)


def test_opening_a_pipeline_file_from_python_mode_turns_the_badge_to_pipeline(tmp_path, monkeypatch):
    win, _ = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        other = studio.PipelineModel(studio.demo_image(48))   # 開くファイルは別の model で作る(今の窓を汚さない)
        other.add_stage("gaussian")
        other.add_stage("sobel_mag")
        p = tmp_path / "pipe.json"
        p.write_text(json.dumps(other.to_dict()), encoding="utf-8")
        pm.set_mode(pm_mod.MODE_PYTHON)
        assert _says(win, "Python") == []
        win._open_pipe_path(str(p))
        _pump(0.2)
        assert pm.mode == pm_mod.MODE_PIPELINE and _says(win, "Pipeline") == []
        assert "gaussian" in win._program["edit"].toPlainText() and pm.mode_mismatch() is None
        assert pm_mod.BADGE_WARNING not in pm.badge.text()
    finally:
        _close(win)


def test_python_text_in_pipeline_mode_gets_a_warning_mark_and_choices_but_no_automatic_switch(tmp_path, monkeypatch):
    win, _ = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        assert pm.mode_mismatch() is None and pm_mod.BADGE_WARNING not in pm.badge.text()
        assert "border:0" in pm.badge.styleSheet()
        ed.setPlainText(PY_TEXT)
        pm.update_badge()
        assert pm.mode_mismatch() == "python_text_in_pipeline"
        assert pm.badge.text().startswith(pm_mod.BADGE_WARNING) and "Pipeline" in pm.badge.text()
        assert "border:2px solid %s" % pm_mod.BADGE_WARN_BORDER["dark"] in pm.badge.styleSheet()   # 縁も警告の色
        assert "looks like Python" in pm.badge.toolTip()
        assert pm.mode == pm_mod.MODE_PIPELINE                 # 勝手には切り替えない
        labels = [a.text() for a in pm.badge_menu().actions()]
        assert len(labels) == 2 and "Move this text to Python mode" in labels
        assert pm.mode == pm_mod.MODE_PIPELINE and ed.toPlainText() == PY_TEXT   # 選択肢を出しただけでは何も変わらない
        assert pm.move_text_to_python() is True                # 選んだ時だけ動く
        assert pm.active and ed.toPlainText() == PY_TEXT and pm.mode_mismatch() is None
        assert pm_mod.BADGE_WARNING not in pm.badge.text() and _says(win, "Python") == []
        assert "border:0" in pm.badge.styleSheet()
        assert ed.document().isUndoAvailable()
        ed.undo()                                              # 1 回で前の Python の文面に戻る
        assert ed.toPlainText() != PY_TEXT
    finally:
        _close(win)


def test_moving_text_that_came_with_an_opened_pipeline_file_asks_before_the_first_run(tmp_path, monkeypatch):
    """札の「この文面を Python のモードへ移す」: 開いたパイプラインのファイルから来た文面は、そのファイルの信頼を
    引き継ぐ(手で打った物にしない。初回の実行の前に確認する。第 1 回レビュー H1 の変換と同じ約束)。"""
    asked = []
    monkeypatch.setattr(pm_mod, "TRUST_HOOK", lambda *a: asked.append(a) or False)
    win, _ = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        other = studio.PipelineModel(studio.demo_image(48))
        other.add_stage("gaussian")
        p = tmp_path / "from_disk.json"
        p.write_text(json.dumps(other.to_dict()), encoding="utf-8")
        win._open_pipe_path(str(p))
        _pump(0.2)
        assert pm.pipe_source == os.path.abspath(str(p))
        win._program["edit"].setPlainText("# python\nk = 1\n")
        pm.update_badge()
        assert pm.mode_mismatch() == "python_text_in_pipeline"
        assert pm.move_text_to_python() is True and pm.active
        assert pm.origin == "file" and pm.session_trusted is False         # 「手で打った」扱いにしない
        runs0 = pm.state.get("pymode_runs", 0)
        pm.run()
        _pump(0.3)
        assert len(asked) == 1 and pm.state.get("pymode_runs", 0) == runs0  # 断った: 走っていない
        assert os.path.basename(str(p)) in asked[0][2]                       # どのファイルから来たかを言う
    finally:
        _close(win)


def test_pipeline_text_in_python_mode_gets_a_warning_mark_and_converts_only_when_chosen(tmp_path, monkeypatch):
    win, _ = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        pm.set_mode(pm_mod.MODE_PYTHON)
        ed.setPlainText(PIPE_TEXT)
        pm.check_now()                                         # 打っている最中の検査と同じ道
        assert pm.mode_mismatch() == "pipeline_text_in_python"
        assert pm.badge.text().startswith(pm_mod.BADGE_WARNING) and "Python" in pm.badge.text()
        assert "looks like a pipeline" in pm.badge.toolTip()
        labels = [a.text() for a in pm.badge_menu().actions()]
        assert len(labels) == 2 and "Convert this text to Python" in labels
        assert pm.active and ed.toPlainText() == PIPE_TEXT     # 勝手には変換しない
        assert pm.convert_text_in_place() is True
        after = ed.toPlainText()
        assert after != PIPE_TEXT and "gaussian" in after and pm.mode_mismatch() is None
        assert pm_mod.BADGE_WARNING not in pm.badge.text()     # 変換した時に読み直す(次の検査を待たない)
        ed.undo()
        assert ed.toPlainText() == PIPE_TEXT                   # Ctrl+Z の 1 回で戻る
    finally:
        _close(win)


def test_mixed_text_in_python_mode_gets_a_warning_and_a_go_to_line_choice(tmp_path, monkeypatch):
    win, _ = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        pm.set_mode(pm_mod.MODE_PYTHON)
        text = "# python\nimg = gaussian(img, 0.4)\nendfor\nshow(img)\n"     # 3 行目だけパイプラインの書き方
        ed.setPlainText(text)
        pm.check_now()                                         # 検査の mixed_syntax を札も使う
        assert pm.mode_mismatch() == "mixed" and pm._mixed_at == 3
        assert pm.badge.text().startswith(pm_mod.BADGE_WARNING) and "Python" in pm.badge.text()
        assert "line 3" in pm.badge.toolTip() and "mixes" in pm.badge.toolTip()
        acts = pm.badge_menu().actions()
        labels = [a.text() for a in acts]
        assert len(labels) == 2 and labels[0] == "Go to line 3"
        assert pm.active and ed.toPlainText() == text          # 選択肢を出しただけでは何も変わらない
        acts[0].trigger()
        assert ed.textCursor().blockNumber() + 1 == 3 and pm.active and ed.toPlainText() == text
        ed.setPlainText("# python\nimg = gaussian(img, 0.4)\nshow(img)\n")     # 直すと印が消える
        pm.check_now()
        assert pm.mode_mismatch() is None and pm_mod.BADGE_WARNING not in pm.badge.text()
    finally:
        _close(win)


def test_mixed_text_in_pipeline_mode_points_at_the_python_line(tmp_path, monkeypatch):
    win, _ = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        text = "gaussian (0.4, 0.5)\nx = np.zeros(3)\nfor 3\nsobel_mag (0.5, 0.5)\nendfor\n"   # 2 行目だけ Python
        ed.setPlainText(text)
        pm.update_badge()                                      # パイプラインのモードの構文の検査と同じ道
        assert pm.mode_mismatch() == "mixed" and pm._mixed_at == 2
        assert pm.badge.text().startswith(pm_mod.BADGE_WARNING) and "line 2" in pm.badge.toolTip()
        labels = [a.text() for a in pm.badge_menu().actions()]
        assert labels == ["Go to line 2", "Move this text to Python mode",
                          "Switch to Python mode (this text stays in Pipeline mode)"]
        assert pm.mode == pm_mod.MODE_PIPELINE and ed.toPlainText() == text
    finally:
        _close(win)


@pytest.mark.parametrize("text", ["", "# a comment only\n", "* a pipeline comment\n"])
def test_text_without_code_is_never_a_mismatch(text):
    assert pm_mod.text_looks_like(text) is None


def test_text_looks_like_reads_without_running():
    marker = []
    src = "import os\nmarker.append(1)\nraise SystemExit\n"
    assert pm_mod.text_looks_like(src) == pm_mod.MODE_PYTHON and marker == []
    assert pm_mod.text_looks_like(PIPE_TEXT) == pm_mod.MODE_PIPELINE
    assert pm_mod.text_looks_like(PY_TEXT) == pm_mod.MODE_PYTHON


def test_no_op_line_written_by_the_pipeline_looks_like_python():
    """パイプラインのモードの文面(段 1 つ = ``op (a, b)`` の 1 行)が、どの op でも Python に見えない
    (パイプラインのモードで札が根拠なく ⚠ を出さない)。"""
    names = sorted(sp.op_table())
    assert len(names) > 500
    lines = ["%s (%r, %r)" % (n, 0.5, 0.5) for n in names]
    wrong = [ln for ln in lines if pm_mod.text_looks_like(ln + "\n") != pm_mod.MODE_PIPELINE]
    assert wrong == []
    assert pm_mod.text_looks_like("\n".join(lines) + "\n") == pm_mod.MODE_PIPELINE
    bypassed = "\n".join("# bypassed: " + ln for ln in lines[:50]) + "\ngaussian (0.4, 0.5)\n"
    assert pm_mod.text_looks_like(bypassed) == pm_mod.MODE_PIPELINE


def test_typing_does_not_re_read_the_text_for_the_badge_until_the_check(tmp_path, monkeypatch):
    from PySide6 import QtGui
    win, _ = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        pm.set_mode(pm_mod.MODE_PYTHON)
        calls = []
        real = pm_mod._classify
        monkeypatch.setattr(pm_mod, "_classify", lambda t: (calls.append(len(t)), real(t))[1])
        cur = QtGui.QTextCursor(pm.edit.document())
        cur.movePosition(QtGui.QTextCursor.End)
        for ch in "x = 1  # typed\n":                        # 1 文字ずつ(1 打ごとの道 = on_text_changed)
            cur.insertText(ch)
        assert calls == []                                     # 間を置いた検査の前は読み直さない
        pm.check_now()                                         # 間を置いた検査
        assert len(calls) == 1
        pm.set_mode(pm_mod.MODE_PIPELINE)                      # モード(文書)が変われば読み直す
        assert len(calls) >= 2
    finally:
        _close(win)


def test_the_f5_entries_say_python_in_python_mode_and_come_back_in_pipeline_mode(tmp_path, monkeypatch):
    win, _ = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        run_all, dbg_run, btn = win._actions["run_all"], win._actions["dbg_run"], win._buttons["run_all"]

        def now():
            return (run_all.text(), run_all.toolTip(), dbg_run.text(), dbg_run.toolTip(), btn.toolTip())
        before = now()
        assert before[0] == "Run all" and "F5" in before[1] and "Python" not in " ".join(before)
        pm.set_mode(pm_mod.MODE_PYTHON)
        assert run_all.text() == "Run as Python" and "as Python" in run_all.toolTip() and "F5" in run_all.toolTip()
        assert dbg_run.text() == "Run as Python (F5 / Ctrl+R)" and "as Python" in dbg_run.toolTip()
        assert "as Python" in btn.toolTip()
        # WIRING 2.7 / 4 章 D123: 帯の tooltip は「名前 — 効果 (キー)」、statusTip は効果だけのまま。
        assert run_all.toolTip().startswith("Run as Python — ") and run_all.toolTip().endswith(" (Ctrl+Return)")
        assert run_all.statusTip() == "Run the Program text as Python. Also F5 or Ctrl+R from any panel"
        table = _table()
        win._apply_language("ja")
        _pump(0.1)
        assert run_all.text() == table["Run as Python"]["ja"]
        assert dbg_run.text() == table["Run as Python (F5 / Ctrl+R)"]["ja"]
        assert btn.toolTip() == table["Run the Program text as Python (Ctrl+Enter)"]["ja"]
        win._apply_language("en")
        _pump(0.1)
        pm.set_mode(pm_mod.MODE_PIPELINE)
        assert now() == before                                 # パイプラインのモードでは元の文に戻る
    finally:
        _close(win)


def test_the_run_button_its_hint_and_the_output_header_say_python(tmp_path, monkeypatch):
    win, _ = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        pm.set_mode(pm_mod.MODE_PYTHON)
        assert pm.btn_run.text() == "Run as Python" and "as Python" in pm.btn_run.toolTip()
        win._program["edit"].setPlainText("# python\nk = 1\n")
        pm.run()
        end = time.monotonic() + 20
        while pm.running and time.monotonic() < end:
            _pump(0.05)
        _pump(0.2)
        head = [ln for ln in pm.output.toPlainText().splitlines() if ln.startswith("──")]
        assert len(head) == 1 and "Python" in head[0] and "Run" in head[0]
    finally:
        _close(win)


def test_the_badge_colours_have_a_contrast_of_at_least_4_5_in_both_palettes(tmp_path, monkeypatch):
    assert sorted(pm_mod.BADGE_PALETTES) == ["dark", "light"]
    assert sorted(pm_mod.BADGE_WARN_BORDER) == ["dark", "light"]
    seen = []
    for name, modes in pm_mod.BADGE_PALETTES.items():
        assert sorted(modes) == sorted([pm_mod.MODE_PIPELINE, pm_mod.MODE_PYTHON])
        for mode, (fg, bg) in modes.items():
            seen.append((name, mode, pm_mod.contrast_ratio(fg, bg)))
        assert modes[pm_mod.MODE_PYTHON][1] != modes[pm_mod.MODE_PIPELINE][1]      # モードで色が違う
    assert len(seen) == 4 and [s for s in seen if s[2] < 4.5] == []
    assert abs(pm_mod.contrast_ratio("#000000", "#ffffff") - 21.0) < 1e-6           # 物差しそのものの検算
    assert abs(pm_mod.contrast_ratio("#777777", "#777777") - 1.0) < 1e-9
    win, _ = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        for name in ("dark", "light"):                        # 実際に札へ掛かる色がその表の色
            pm.set_badge_palette(name)
            for mode in (pm_mod.MODE_PIPELINE, pm_mod.MODE_PYTHON):
                pm.set_mode(mode)
                fg, bg = pm_mod.BADGE_PALETTES[name][mode]
                css = pm.badge.styleSheet()
                assert "color:%s" % fg in css and "background:%s" % bg in css
        with pytest.raises(ValueError):
            pm.set_badge_palette("sepia")
    finally:
        _close(win)


def test_the_mode_words_exist_in_six_languages_and_the_badge_uses_them(tmp_path, monkeypatch):
    table = _table()
    keys = ["Pipeline", "Python", "Program (code) — Python", "Program (code) — Pipeline", "Program: %s",
            "Run as Python", "Move this text to Python mode", "Convert this text to Python",
            "Switch to Pipeline mode", "Switch to Python mode",
            "This text is Python: F5 runs it as Python and the stage list records the run",
            "This text is a pipeline: the stage list is the source and F5 runs the stages",
            "Run as Python (F5 / Ctrl+R)", "Run the Program text as Python. Also F5 or Ctrl+R from any panel",
            "Run the Program text as Python (debugger Run); when stopped at a breakpoint: continue",
            "Run the Program text as Python (Ctrl+Enter)", "Go to line %d",
            "This text mixes the pipeline syntax and Python (line %d is in the other syntax). Click for the "
            "choices (nothing is switched by itself)"]
    missing = [(k, lang) for k in keys for lang in LANGS if not str(table.get(k, {}).get(lang, "")).strip()]
    assert len(keys) == 18 and missing == []
    fmt = [(k, lang) for k in keys if "%d" in k or "%s" in k for lang in LANGS
           if table[k][lang].count("%") != k.count("%")]
    assert fmt == []                                           # 書式の穴の数が原文と同じ
    win, _ = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        win._apply_language("ja")
        _pump(0.1)
        assert pm.badge.text().endswith(table["Pipeline"]["ja"])
        assert win._docks["program"].windowTitle() == table["Program (code) — Pipeline"]["ja"]
        pm.set_mode(pm_mod.MODE_PYTHON)
        assert win._docks["program"].windowTitle() == table["Program (code) — Python"]["ja"]
        assert pm.btn_run.text() == table["Run as Python"]["ja"]
        assert table["Python"]["ja"] in win._mode_status.text()
    finally:
        _close(win)
