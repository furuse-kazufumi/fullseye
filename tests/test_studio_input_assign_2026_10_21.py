import csv
import os

import numpy as np
import pytest

import studio


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _write(path, headers=("piece", "person", "reading"), drop=None):
    rows = []
    for part in range(10):
        for operator in range(3):
            for repeat in range(3):
                rows.append(("P%d" % part, "O%d" % operator,
                             10.0 + part * 0.7 + operator * 0.1 + repeat * 0.02))
    if drop is not None:
        rows.pop(drop)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(headers); writer.writerows(rows)
    return rows


def _assign(dlg):
    for param, column in {"part": "piece", "operator": "person", "value": "reading"}.items():
        dlg._state["column_widgets"][param].setCurrentText(column)


def test_gauge_rr_csv_runs_like_the_direct_call(tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "settings.ini"))
    _app(); path = tmp_path / "measurements.csv"; _write(path)
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(24)))
    win._apply_language("en")
    dlg = win._open_ledger_runner("msa_gauge_rr")
    table = dlg._load_csv(str(path)); _assign(dlg)
    actual = dlg._run()
    import fullseye as fs
    expected = fs.ledger.msa_gauge_rr(table, part="piece", operator="person", value="reading")
    assert actual is not None, dlg._state["error"]
    for key in expected:
        np.testing.assert_equal(actual[key], expected[key])
    namespace = {}
    exec(dlg._code.toPlainText(), namespace)
    np.testing.assert_equal(namespace["result"]["sigma"], expected["sigma"])
    assert "90 rows" in dlg._state["data_check"].text()
    assert "3 repeats" in dlg._state["data_check"].text()


def test_unequal_repeats_are_refused_with_the_group_named(tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "settings.ini"))
    _app(); path = tmp_path / "unequal.csv"; _write(path, drop=0)
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(24)))
    win._apply_language("ja")
    dlg = win._open_ledger_runner("msa_gauge_rr"); dlg._load_csv(str(path)); _assign(dlg)
    assert dlg._run() is None
    message = dlg._info.toPlainText()
    assert "[gauge_rr:unequal_repeats]" in message
    assert "part=P0 / operator=O0 (2)" in message


def test_mapping_reuse_is_keyed_by_header_signature(tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "settings.ini"))
    _app(); first = tmp_path / "first.csv"; second = tmp_path / "second.csv"
    different = tmp_path / "different.csv"
    _write(first); _write(second); _write(different, headers=("item", "worker", "measurement"))
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(24)))
    dlg = win._open_ledger_runner("msa_gauge_rr"); dlg._load_csv(str(first)); _assign(dlg)
    assert dlg._run() is not None
    dlg2 = win._open_ledger_runner("msa_gauge_rr"); dlg2._load_csv(str(second))
    assert {p: w.currentText() for p, w in dlg2._state["column_widgets"].items()} == {
        "part": "piece", "operator": "person", "value": "reading"}
    dlg3 = win._open_ledger_runner("msa_gauge_rr"); dlg3._load_csv(str(different))
    assert [w.currentText() for w in dlg3._state["column_widgets"].values()] == [
        "item", "item", "item"]


@pytest.mark.parametrize("lang", studio.HELP_LANG_ORDER)
def test_assignment_form_and_data_check_use_selected_language(tmp_path, monkeypatch, lang):
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / (lang + ".ini")))
    _app(); path = tmp_path / (lang + ".csv"); _write(path)
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(24)))
    # ★UI 言語はプロセス全体の状態(studio._UI_LANG)。切り替えたまま返すと、同じ worker で後に走る
    #   test_studio_result_preview の note が hi / ko になって落ちる(CI shard 5、2026-10-25)。teardown で戻す。
    monkeypatch.setitem(studio._UI_LANG, "code", studio._UI_LANG["code"])
    win._apply_language(lang)
    dlg = win._open_ledger_runner("msa_gauge_rr")

    from PySide6 import QtWidgets
    labels = {label.text() for label in dlg.findChildren(QtWidgets.QLabel)}
    translated = lambda key: key if lang == "en" else studio.STRINGS_I18N[key][lang]
    assert translated("Input table") in labels
    assert translated("Data check") in labels
    assert dlg._state["csv_label"].text() == translated("No CSV selected")
    if lang != "en":
        for key in ("Open CSV table", "No CSV selected", "Input table", "Data check",
                    "CSV file…"):
            assert translated(key) != key
    for param, key in (("part", "part ID"), ("operator", "operator"),
                       ("value", "measured value")):
        assert "%s / %s" % (param, translated(key)) in labels
    dlg._load_csv(str(path)); _assign(dlg)
    source = dlg._state["sources"]["table"]
    assert source.currentText() == translated("CSV file…")
    expected = translated(
        "%d rows; part: %d distinct; operator: %d distinct; value: 0 missing; "
        "%d repeats per part x operator group") % (90, 10, 3, 3)
    assert dlg._state["data_check"].text() == expected
    if lang != "en":
        assert dlg._state["data_check"].text() != (
            "90 rows; part: 10 distinct; operator: 3 distinct; value: 0 missing; "
            "3 repeats per part x operator group")
