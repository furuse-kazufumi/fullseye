# -*- coding: utf-8 -*-
"""Studio の操作動画の試し撮り(2026-11-12)で見つかった使い勝手の問題の回帰テスト。

1. 画像が画像欄に収まらず下が切れた(画像の表示矩形 ⊂ 画像欄の矩形を数値で)
2. 初回(保存済みレイアウト無し)の画像欄の比率(縦の 55〜65%)。保存済みの配置は尊重する
3. ``+`` の直後に段の欄が「未計算」と言い続ける / 状態バーが古い世代を言い続ける
4. op を選ぶ・つまみを動かすと右パネルの幅が変わる(画像が横にずれる)
5. 日本語モードに残る英語(固定文言・併記・つまみの説明・コード欄の初期コメント)

起動は既存の Studio テストと同じ(offscreen・空の設定ファイル)。
"""
import json
import os
import re
import time

import pytest

import studio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CJK = re.compile("[぀-ヿ一-鿿]")
_ASCII_WORD = re.compile("[A-Za-z]{3,}")


def _pump(sec=0.3):
    from PySide6 import QtWidgets
    end = time.monotonic() + sec
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)


def _app():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _launch(tmp_path, monkeypatch, size=(1280, 673), name="s.ini", platform=None):
    """空の設定ファイルで Studio を起動する(普段の設定には触らない)。"""
    _app()
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / name))
    if platform is not None:
        monkeypatch.setenv("QT_QPA_PLATFORM", platform)       # 保存済みレイアウトの復元経路を通すため(offscreen では復元しない)
    win, model = studio.build_window()
    win.resize(*size)
    win.show()
    _pump(0.6)
    return win, model


def _close(win):
    studio._UI_LANG["code"] = "en"
    win.close_guard = lambda: True
    win.quiesce()
    win.close()
    _pump(0.1)


@pytest.fixture
def win(tmp_path, monkeypatch):
    w, m = _launch(tmp_path, monkeypatch)
    w._test_model = m
    yield w
    _close(w)


def _fit_report(win):
    """画像の表示矩形・画像欄(view の viewport)・欄(MDI の作業領域)を、MDI の座標でそろえて返す。"""
    from PySide6 import QtCore
    v = win._current_view()
    mdi_vp = win.centralWidget().viewport()
    pane = mdi_vp.rect()
    view_rect = QtCore.QRect(v.mapTo(mdi_vp, QtCore.QPoint(0, 0)), v.size())
    vp = v.viewport()
    img_in_vp = v.mapFromScene(v.scene().sceneRect()).boundingRect()
    img = img_in_vp.translated(vp.mapTo(mdi_vp, QtCore.QPoint(0, 0)))
    return {"pane": pane, "view": view_rect, "image": img, "viewport": vp.rect(), "image_in_viewport": img_in_vp}


def _contained(inner, outer, tol=2):
    return (inner.left() >= outer.left() - tol and inner.top() >= outer.top() - tol
            and inner.right() <= outer.right() + tol and inner.bottom() <= outer.bottom() + tol)


# --------------------------------------------------------------------------- #
# 1. 画像が画像欄に収まる                                                         #
# --------------------------------------------------------------------------- #
# offscreen の既定フォントは幅が広く、窓の最小幅が約 910px。それより狭い窓は作れない
@pytest.mark.parametrize("size", [(1280, 673), (1120, 700), (1600, 900)])
def test_sample_image_is_fully_inside_the_image_pane_right_after_opening(tmp_path, monkeypatch, size):
    win, _m = _launch(tmp_path, monkeypatch, size)
    try:
        r = _fit_report(win)
        assert r["image"].width() > 20 and r["image"].height() > 20, "画像が描かれていない: %s" % r["image"]
        assert _contained(r["view"], r["pane"]), "画像欄が欄からはみ出す: %s ⊄ %s" % (r["view"], r["pane"])
        assert _contained(r["image"], r["pane"]), "起動直後に画像が欄からはみ出す(デモ画像): %s ⊄ %s" % (r["image"], r["pane"])
        win._load_sample_image("coins"); _pump(0.5)
        r = _fit_report(win)
        assert r["image"].width() > 20, r
        assert _contained(r["image"], r["pane"]), "coins を開いた直後に下が切れる: %s ⊄ %s" % (r["image"], r["pane"])
    finally:
        _close(win)


def test_fit_to_window_fits_after_the_window_is_resized(win):
    win._load_sample_image("coins"); _pump(0.4)
    for size in ((1100, 700), (1500, 880), (1250, 760)):
        win.resize(*size); _pump(0.4)
        win._actions["fit"].trigger(); _pump(0.2)
        r = _fit_report(win)
        assert _contained(r["view"], r["pane"]), (size, r["view"], r["pane"])
        assert _contained(r["image"], r["pane"]), (size, "窓に合わせても収まらない", r["image"], r["pane"])
        # 欄いっぱいに使う(小さく縮んだままではない)
        assert r["image"].width() >= r["viewport"].width() - 4 or r["image"].height() >= r["viewport"].height() - 4, (size, r)


def test_a_fitted_view_follows_the_pane_but_a_zoomed_view_does_not(win):
    """合わせた状態のまま窓を変えれば画像も追従する。利用者が拡大した後は勝手に戻さない。"""
    win._load_sample_image("coins"); _pump(0.4)
    win.resize(1500, 880); _pump(0.4)
    assert _contained(_fit_report(win)["image"], _fit_report(win)["pane"])
    v = win._current_view()
    v.zoom(2.0); _pump(0.1)
    scale = v.transform().m11()
    win.resize(1200, 720); _pump(0.4)
    assert abs(v.transform().m11() - scale) < 1e-9, "拡大した倍率が窓の変更で勝手に変わった"


def test_image_view_minimum_is_smaller_than_the_first_run_pane(win):
    """原因: 画像欄の最小 380x380 が初回の欄(約 290px)より大きく、中身が欄からはみ出して下が切れた。"""
    v = win._current_view()
    assert v.minimumHeight() <= 200 and v.minimumWidth() <= 300
    pane = win.centralWidget().viewport().rect()
    assert v.minimumHeight() < pane.height()


# --------------------------------------------------------------------------- #
# 2. 初回レイアウトの比率                                                          #
# --------------------------------------------------------------------------- #
def _image_ratio(win):
    h_img = win.centralWidget().height()
    h_code = win._docks["program"].height()
    return h_img / float(h_img + h_code)


@pytest.mark.parametrize("size", [(1280, 673), (1600, 900)])
def test_first_run_gives_the_image_pane_55_to_65_percent_of_the_height(tmp_path, monkeypatch, size):
    win, _m = _launch(tmp_path, monkeypatch, size)
    try:
        assert 0.55 <= _image_ratio(win) <= 0.65, _image_ratio(win)
    finally:
        _close(win)


def test_the_first_run_ratio_is_applied_once_and_a_users_resize_is_kept(win):
    dock = win._docks["program"]
    win.resizeDocks([dock], [220], __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.Vertical); _pump(0.3)
    assert abs(dock.height() - 220) < 12, dock.height()
    win.hide(); _pump(0.1); win.show(); _pump(0.4)               # 再表示で比率を取り直さない
    assert abs(dock.height() - 220) < 12, dock.height()


def test_a_saved_dock_layout_is_respected(tmp_path, monkeypatch):
    """保存済みの配置がある起動では、初回の比率に上書きしない(P-01 の復元を壊さない)。

    offscreen は保存配置を復元しない経路なので、環境変数だけ offscreen でない値にして復元経路を通す。"""
    from PySide6 import QtCore
    first, _m = _launch(tmp_path, monkeypatch, platform="offscreen-saved-layout-test")
    try:
        assert 0.55 <= _image_ratio(first) <= 0.65, _image_ratio(first)       # 1 回目は初回: 比率が当たる
        first.resizeDocks([first._docks["program"]], [130], QtCore.Qt.Vertical); _pump(0.3)
        saved_h = first._docks["program"].height()
    finally:
        _close(first)
    second, _m2 = _launch(tmp_path, monkeypatch, platform="offscreen-saved-layout-test")
    try:
        assert second.first_layout_pending is False, "保存済みの配置があるのに、初回の比率が当たる印が立った"
        assert abs(second._docks["program"].height() - saved_h) < 25, (second._docks["program"].height(), saved_h)
        assert _image_ratio(second) > 0.65, "保存した小さいコード欄が、初回の比率(約 40%)に戻された"
    finally:
        _close(second)


# --------------------------------------------------------------------------- #
# 3. 画像と表示が食い違わない                                                      #
# --------------------------------------------------------------------------- #
def _pick(win, name):
    from PySide6 import QtCore
    lst = win._op_list
    for i in range(lst.count()):
        if lst.item(i).data(QtCore.Qt.UserRole) == name:
            lst.setCurrentRow(i); _pump(0.05)
            return
    raise AssertionError("op が一覧に無い: %s" % name)


def _rows(win):
    return [win._stage_list.item(i).text() for i in range(win._stage_list.count())]


def test_row_does_not_say_not_computed_right_after_plus(win):
    win._load_sample_image("coins"); _pump(0.3)
    _pick(win, "gaussian")
    win._op_buttons["insert"].click(); _pump(0.2)
    rows = _rows(win)
    assert len(rows) == 1 and rows[0].startswith("1. gaussian")
    assert "not computed" not in rows[0] and "未計算" not in rows[0], rows[0]
    assert "mean=" in rows[0] and " ms" in rows[0], rows[0]           # 画像と同じ結果の要約が出ている
    assert win._stage_list.currentRow() == 0
    # 2 つ目も
    _pick(win, "sobel_mag")
    win._op_buttons["insert"].click(); _pump(0.2)
    assert all("not computed" not in r and "未計算" not in r for r in _rows(win)[:2]), _rows(win)


def test_row_follows_the_knob_while_it_is_dragged(win):
    win._load_sample_image("coins"); _pump(0.3)
    _pick(win, "gaussian")
    win._op_buttons["insert"].click(); _pump(0.3)
    ka = win._knob_rows[0]
    before = _rows(win)[0]
    ka.slider.setValue(int(ka.slider.maximum() * 0.9))               # ドラッグの 1 目盛り(つまみを離す前)
    _pump(0.02)
    during = _rows(win)[0]
    assert win._knob_drag_base is not None, "ドラッグ中の状態になっていない"
    assert during != before, "つまみを動かしても段の欄の文字が古いまま: %s" % during
    assert "not computed" not in during and "未計算" not in during, during


def test_status_bar_does_not_name_an_old_generation_for_a_live_picture(win):
    """worker で走らせた後に設定を変えると、画像は「いまの設定の結果」になる。状態バーは古い世代を言わない。"""
    win._load_sample_image("coins"); _pump(0.3)
    _pick(win, "gaussian")
    win._op_buttons["insert"].click(); _pump(0.3)
    gen = win._start_run_async()
    end = time.monotonic() + 10
    while win._run_controller.running and time.monotonic() < end:
        _pump(0.05)
    _pump(0.3)
    attr = win._run_ui["attribution"]
    assert str(gen) in attr.text(), "走らせた直後は世代を言う: %r" % attr.text()       # 前提: 世代の結果を見せている
    # 設定を変える(つまみ)→ 画像はいまの設定の結果になる
    ka = win._knob_rows[0]
    ka.slider.setValue(int(ka.slider.maximum() * 0.8)); _pump(0.3)
    assert attr.text() == "", "画像はもう世代 %d の結果ではないのに状態バーが言い続ける: %r" % (gen, attr.text())
    # 前の結果へ行く導線(帯と「その結果を見る」)は残る: 詳しくは test_the_previous_completed_result_stays_reachable...
    assert not win._run_ui["banner"].isHidden() and not win._run_ui["show_result"].isHidden()
    # op を足しても同じ
    _pick(win, "sobel_mag")
    win._op_buttons["insert"].click(); _pump(0.3)
    assert attr.text() == ""
    # もう一度走らせると、世代が戻る
    gen2 = win._start_run_async()
    end = time.monotonic() + 10
    while win._run_controller.running and time.monotonic() < end:
        _pump(0.05)
    _pump(0.3)
    assert str(gen2) in attr.text(), attr.text()


# --------------------------------------------------------------------------- #
# 4. 右パネルの幅が中身で変わらない                                                  #
# --------------------------------------------------------------------------- #
_OPS_WIDE = ("sobel_mag", "median", "gaussian", "mean_box", "gamma", "scale_clip", "threshold", "unsharp",
             "bilateral", "clahe", "otsu", "invert", "min_filter")


def test_right_panel_width_does_not_change_when_an_op_is_selected(tmp_path, monkeypatch):
    # 窓を狭くして、右パネルが「中身の最小幅」で決まる状態にする(広いと余裕で変化が見えない)
    win, _m = _launch(tmp_path, monkeypatch, (900, 640))
    try:
        ops = win._docks["operators"]
        _pick(win, "sobel_mag"); _pump(0.3)
        base_w, base_min = ops.width(), ops.widget().minimumSizeHint().width()
        widths, mins = {base_w}, {base_min}
        for name in _OPS_WIDE:
            _pick(win, name); _pump(0.15)
            widths.add(ops.width()); mins.add(ops.widget().minimumSizeHint().width())
        assert len(widths) == 1, "op を選ぶと右パネルの幅が変わる: %s" % sorted(widths)
        assert len(mins) == 1, "op を選ぶと右パネルの最小幅が変わる: %s" % sorted(mins)
    finally:
        _close(win)


def test_right_panel_width_does_not_change_when_a_knob_is_dragged(tmp_path, monkeypatch):
    win, _m = _launch(tmp_path, monkeypatch, (900, 640))
    try:
        win._load_sample_image("coins"); _pump(0.3)
        ops, pipe = win._docks["operators"], win._docks["pipeline"]
        for name in ("gaussian", "median", "sobel_mag", "clahe"):
            _pick(win, name)
            win._op_buttons["insert"].click(); _pump(0.15)
        pipe.show(); pipe.raise_(); _pump(0.3)
        w_ops, w_pipe = {ops.width()}, {pipe.width()}
        mins = {pipe.widget().minimumSizeHint().width()}
        code_w = {win._docks["program"].width()}
        for k in range(4):
            win._stage_list.setCurrentRow(k); _pump(0.15)
            w_ops.add(ops.width()); w_pipe.add(pipe.width()); mins.add(pipe.widget().minimumSizeHint().width())
            code_w.add(win._docks["program"].width())
            for row in win._knob_rows:
                if row.slider is not None and row.slider.isEnabled():
                    for frac in (0.2, 0.55, 0.95):
                        row.slider.setValue(int(row.slider.maximum() * frac)); _pump(0.03)
                        w_ops.add(ops.width()); w_pipe.add(pipe.width()); code_w.add(win._docks["program"].width())
        _pump(0.4)
        w_ops.add(ops.width()); w_pipe.add(pipe.width()); code_w.add(win._docks["program"].width())
        assert len(w_ops) == 1 and len(w_pipe) == 1, "つまみを動かすと右パネルの幅が変わる: %s %s" % (sorted(w_ops), sorted(w_pipe))
        assert len(mins) == 1, sorted(mins)
        assert len(code_w) == 1, "つまみを動かすとコード欄の幅が変わる: %s" % sorted(code_w)
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# 5. 日本語モードに残る英語                                                         #
# --------------------------------------------------------------------------- #
def test_japanese_mode_translates_the_texts_found_in_the_trial(win):
    win._load_sample_image("coins"); _pump(0.3)
    win._apply_language("ja"); _pump(0.3)
    try:
        assert not win._samples.itemText(0).startswith("— load"), win._samples.itemText(0)
        assert _CJK.search(win._samples.itemText(0)) and _CJK.search(win._category_combo.itemText(0))
        assert [win._problems_list.item(i).text() for i in range(win._problems_list.count())] == ["問題はありません"]
        # コード欄の初期コメント
        code = win._program["edit"].toPlainText()
        assert "empty pipeline" not in code and "空のパイプライン" in code, code
        assert "control flow" not in code and "制御構文" in code, code
        # つまみの名前・説明
        _pick(win, "gaussian"); _pump(0.2)
        a_lbl, b_lbl = win._op_arg_labels
        assert a_lbl.text() == "a · ぼかしの量", a_lbl.text()
        assert b_lbl.text() == "b · 端の扱い"                     # ★2026-11-12: gaussian の b は端の扱い(未使用ではない)
        detail = studio.op_signature_detail(studio._op_row("gaussian"))
        assert "knob a" not in detail and "knob b" not in detail and "つまみ a" in detail and "端の扱い" in detail, detail
        unused = studio.op_signature_detail(studio._op_row("sobel_mag"))
        assert "(未使用)" in unused and "unused" not in unused, unused        # 本当に未使用の op の表記
        win._op_buttons["insert"].click(); _pump(0.3)
        ka, kb = win._knob_rows
        assert "つまみ" in ka.label.text() and "ぼかし" in ka.label.text(), ka.label.text()
        assert "端の扱い" in kb.label.text() and "reflect" in kb.label.text(), kb.label.text()
        # 本当に未使用のつまみの表記(日本語)
        _pick(win, "sobel_mag"); _pump(0.2)
        win._op_buttons["insert"].click(); _pump(0.3)
        win._refresh_stage_list(select=len(win._model_stages()) - 1) if hasattr(win, "_model_stages") else None
        ka, kb = win._knob_rows
        assert "unused by this op" not in kb.label.text() and "この op では使いません" in kb.label.text(), kb.label.text()
        # 段の欄の併記(英語のまま残る「not computed」)
        assert _rows(win), "段が無い"
    finally:
        win._apply_language("en"); _pump(0.2)


def test_not_computed_is_japanese_only_in_japanese_and_unchanged_in_english(win):
    assert studio._pair("未計算", "not computed") == "未計算 / not computed"        # 英語モードの文言は従来のまま
    win._apply_language("ja")
    try:
        assert studio._pair("未計算", "not computed") == "未計算"
    finally:
        win._apply_language("en")
    win._apply_language("de")
    try:
        assert studio._pair("未計算", "not computed") == "not computed"        # 日本語を見せない
    finally:
        win._apply_language("en")


def test_stage_row_says_not_computed_in_japanese_only_for_a_stage_that_was_never_computed(win):
    """段が未計算の状態(1 つ目の段の後ろ)の文言が、日本語モードで日本語だけになる。"""
    win._load_sample_image("coins"); _pump(0.3)
    for name in ("gaussian", "sobel_mag"):
        _pick(win, name)
        win._op_buttons["insert"].click(); _pump(0.2)
    win._test_model.add_stage("otsu")                                # モデルにだけ足す: この段はまだ計算されていない
    win._refresh_stage_list(select=1); _pump(0.2)
    assert "not computed" in _rows(win)[2] or "未計算" in _rows(win)[2], _rows(win)
    win._apply_language("ja"); _pump(0.3)
    try:
        rows = _rows(win)
        assert any("未計算" in r or "再計算が必要" in r for r in rows), rows
        assert not any("not computed" in r or "recompute needed" in r for r in rows), rows
    finally:
        win._apply_language("en"); _pump(0.2)
    rows = _rows(win)
    assert any("未計算 / not computed" in r or "再計算が必要 / recompute needed" in r for r in rows), rows


def test_english_mode_texts_are_unchanged(win):
    win._apply_language("en"); _pump(0.2)
    assert win._samples.itemText(0) == "— load a sample —"
    assert win._category_combo.itemText(0) == "all categories"
    assert [win._problems_list.item(i).text() for i in range(win._problems_list.count())] == ["no problems"]
    assert win._program["edit"].toPlainText().startswith("* empty pipeline — type ops here (HDevelop syntax), e.g.:")
    detail = studio.op_signature_detail(studio._op_row("gaussian"))
    assert "knob a — blur amount — Gaussian σ = 0.3 + 2.7·a" in detail and "knob b — border handling" in detail
    assert "knob b — (unused)" in studio.op_signature_detail(studio._op_row("sobel_mag"))
    _pick(win, "gaussian")
    assert win._op_arg_labels[0].text() == "a · blur amount"


def test_a_comment_the_user_wrote_is_not_taken_for_the_empty_pipeline_note(win):
    assert studio._is_empty_program_text(studio._empty_program_text())
    assert studio._is_empty_program_text("* empty pipeline — type ops here (HDevelop syntax), e.g.:\n* x")
    assert not studio._is_empty_program_text("* my own note about this program\ngaussian (0.4, 0.5)")
    assert not studio._is_empty_program_text("")


def test_new_translation_rows_are_japanese_only_pending_rows():
    with open(os.path.join(ROOT, "studio_assets", "i18n.json"), encoding="utf-8") as f:
        d = json.load(f)
    pending = d["pending_translation"]
    for key in ("— load a sample —", "all categories", "no problems", "unused by this op", "knob a — %s",
                "knob b — %s", "(unused)", "see impl", studio._EMPTY_PROGRAM_FIRST, studio._EMPTY_PROGRAM_LAST,
                "blur amount — Gaussian σ = 0.3 + 2.7·a", "blur amount", "blur σ", "kernel", "iterations"):
        assert key in pending and _CJK.search(pending[key]["ja"]), key
        assert key not in d["strings"], "同じ行が strings と pending の両方にある: %s" % key
    # 「%s」を持つ行は、訳も同じ数の「%s」を持つ(書式が壊れない)
    for key, row in pending.items():
        if key != "_note" and "ja" in row:
            assert key.count("%s") == row["ja"].count("%s") and key.count("%d") == row["ja"].count("%d"), key


# --------------------------------------------------------------------------- #
# 追加(2026-11-12 の 2 回目): op の一覧の行数・説明欄の折り返し・直前の結果への導線・最初の 3 手の帯              #
# --------------------------------------------------------------------------- #
def _visible_rows(lst):
    vp = lst.viewport().rect()
    n = 0
    for i in range(lst.count()):
        r = lst.visualItemRect(lst.item(i))
        if r.height() > 0 and vp.contains(r.topLeft()) and r.bottom() <= vp.bottom() + 1:
            n += 1
    return n


def test_operator_list_shows_six_or_more_rows_at_1280x673(win):
    lst = win._op_list
    assert _visible_rows(lst) >= 6, "op の一覧が %d 行しか見えない(高さ %d)" % (_visible_rows(lst), lst.height())
    # op を選んだ状態でも(署名欄が伸びても一覧は 6 行を保つ)
    _pick(win, "gaussian"); _pump(0.3)
    assert _visible_rows(lst) >= 6, (_visible_rows(lst), lst.height())
    # 一覧の下に使われない空きが無い: 一覧の下端と署名欄の上端が接している
    sig = [w for w in win._docks["operators"].findChildren(__import__("PySide6.QtWidgets", fromlist=["QLabel"]).QLabel)
           if "gaussian" in w.text() and "→" in w.text()][0]
    gap = sig.mapTo(win._docks["operators"], __import__("PySide6.QtCore", fromlist=["QPoint"]).QPoint(0, 0)).y() - \
        (lst.mapTo(win._docks["operators"], __import__("PySide6.QtCore", fromlist=["QPoint"]).QPoint(0, 0)).y() + lst.height())
    assert 0 <= gap <= 12, "一覧と署名欄のあいだに空きがある: %d px" % gap


def test_operator_list_uses_all_the_free_height_in_a_tall_window(tmp_path, monkeypatch):
    small, _m = _launch(tmp_path, monkeypatch, (1280, 673), name="a.ini")
    h_small = small._op_list.height()
    _close(small)
    big, _m2 = _launch(tmp_path, monkeypatch, (1920, 1080), name="b.ini")
    try:
        assert big._op_list.height() >= h_small + 300, (h_small, big._op_list.height())
        assert _visible_rows(big._op_list) >= 12, _visible_rows(big._op_list)
    finally:
        _close(big)


def test_operator_list_still_has_rows_after_a_search(win):
    se = win._search_ui["edit"]
    se.setText("blur"); win._search_ui["search_now"]("blur"); _pump(0.4)
    lst = win._op_list
    assert lst.count() >= 1
    assert lst.height() >= 150, lst.height()                     # 検索結果は 1 件が高い行(ボタン付き)。一覧の高さは保たれる
    assert _visible_rows(lst) >= 1


def test_stage_description_is_not_cut_off_and_impl_is_translated(win):
    win._load_sample_image("coins"); _pump(0.3)
    _pick(win, "gaussian")
    win._op_buttons["insert"].click(); _pump(0.3)
    win._docks["pipeline"].show(); win._docks["pipeline"].raise_(); _pump(0.4)
    d = win._stage_detail
    assert d.wordWrap() and "impl:" in d.text()
    assert d.height() >= d.heightForWidth(d.width()), "説明欄が文の高さに足りず、下の行が切れる: %d < %d" % (d.height(), d.heightForWidth(d.width()))
    # 幅を変えても追従する
    win.resize(1500, 800); _pump(0.4)
    assert d.height() >= d.heightForWidth(d.width())
    win._apply_language("ja"); _pump(0.4)
    try:
        assert "実装: " in d.text() and "impl:" not in d.text(), d.text()
        assert d.height() >= d.heightForWidth(d.width())
    finally:
        win._apply_language("en"); _pump(0.2)


def test_operator_signature_panel_keeps_the_implementation_in_its_tooltip(win):
    _pick(win, "gaussian"); _pump(0.3)
    from PySide6 import QtWidgets
    sig = [w for w in win._docks["operators"].findChildren(QtWidgets.QLabel) if "gaussian" in w.text() and "→" in w.text()][0]
    assert "impl:" not in sig.text() and "impl:" in sig.toolTip()
    assert "knob a" in sig.text()


def test_the_previous_completed_result_stays_reachable_after_a_setting_changes(win):
    import numpy as np
    win._load_sample_image("coins"); _pump(0.3)
    _pick(win, "gaussian")
    win._op_buttons["insert"].click(); _pump(0.3)
    gen = win._start_run_async()
    end = time.monotonic() + 10
    while win._run_controller.running and time.monotonic() < end:
        _pump(0.05)
    _pump(0.3)
    ui = win._run_ui
    assert ui["banner"].isHidden(), "設定を変える前は帯を出さない"
    done_result = np.array(win._test_model.displayed_result, copy=True)
    ka = win._knob_rows[0]
    ka.slider.setValue(int(ka.slider.maximum() * 0.9)); _pump(0.4)
    # 画像は今の設定の結果。状態バーは世代を言わず、前の結果へ行く導線が出る
    assert ui["attribution"].text() == ""
    assert not ui["banner"].isHidden() and not ui["show_result"].isHidden() and not ui["run_current"].isHidden()
    live = np.array(win._current_view()._data, copy=True)
    assert not np.array_equal(live, done_result), "つまみを動かしたのに画像が変わっていない"
    # 「その結果を見る」で完了した結果へ戻れる(画像も状態バーも世代 N)
    ui["show_result"].click(); _pump(0.4)
    assert np.array_equal(np.array(win._current_view()._data), done_result)
    assert str(gen) in ui["attribution"].text()


def test_first_steps_band_is_one_line_about_40px(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    for lang in ("en", "ja"):
        win, _m = _launch(tmp_path, monkeypatch, (1280, 673), name="band_%s.ini" % lang)
        try:
            win._apply_language(lang); _pump(0.4)
            band = win._first_steps
            assert band.isVisible()
            assert band.height() <= 44, "%s: 帯の高さ %d" % (lang, band.height())
            for lab in band.findChildren(QtWidgets.QLabel):
                assert not lab.wordWrap(), lab.text()
            ys = {lab.geometry().y() for lab in band.findChildren(QtWidgets.QLabel)}
            assert max(ys) - min(ys) <= 6, "3 つの手が 1 行に並んでいない: %s" % sorted(ys)
            # 閉じるボタンと既読の保存は今のまま
            win._first_steps_close.click(); _pump(0.2)
            assert band.isHidden()
        finally:
            _close(win)
