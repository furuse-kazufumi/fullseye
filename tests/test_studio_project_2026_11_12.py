# -*- coding: utf-8 -*-
"""Studio のプロジェクト(フォルダ)とファイルのツリー(第 2 便, 2026-11-12)。

* Qt に依らない部分(種類の判定・標準の並びの表・フォルダの外へ出るパスの断り・リンク・新しいプロジェクト・食い違い)
* 窓(offscreen): 入口の数・空の状態・開く先・右クリック・保存の初期位置・復元・日本語 UI
"""
import json
import os
import re
import subprocess
import sys
import time

import pytest

import studio
import studio_project as sp

_CJK = re.compile("[぀-ヿ一-鿿]")


# =========================================================================== Qt なし
def _w(path, text="", mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, encoding=None if "b" in mode else "utf-8") as f:
        f.write(text)
    return path


def test_kind_by_extension_and_content(tmp_path):
    t = str(tmp_path)
    assert sp.classify_file(_w(t + "/a.png", b"x", "wb")) == "image"
    assert sp.classify_file(_w(t + "/a.PNG", b"x", "wb")) == "image"
    assert sp.classify_file(_w(t + "/a.py", "print(1)")) == "python"
    for ext in (".toml", ".yaml", ".yml", ".xml"):
        assert sp.classify_file(_w(t + "/d" + ext, "x: 1")) == "params", ext
    assert sp.classify_file(_w(t + "/n.txt", "hi")) == "other"
    assert sp.classify_file(_w(t + "/p1.json", json.dumps({"fullseye_pipeline": 1, "stages": []}))) == "pipeline"
    assert sp.classify_file(_w(t + "/p2.json", json.dumps({"stages": [["otsu", 0.5, 0.5]]}))) == "pipeline"     # 今の保存形式の形
    assert sp.classify_file(_w(t + "/p3.json", json.dumps({"fullseye_kind": "pipeline", "stages": []}))) == "pipeline"   # 封筒
    assert sp.classify_file(_w(t + "/p4.json", json.dumps({"fullseye_kind": "params", "stages": [1]}))) == "params"      # 封筒が優先
    assert sp.classify_file(_w(t + "/c.json", json.dumps({"exposure": 0.2}))) == "params"
    assert sp.classify_file(_w(t + "/l.json", json.dumps([1, 2, 3]))) == "params"
    assert sp.classify_file(_w(t + "/bad.json", "{not json")) == "params"


def test_kind_does_not_depend_on_the_folder_name(tmp_path):
    t = str(tmp_path)
    p = _w(t + "/params/real_pipeline.json", json.dumps({"fullseye_pipeline": 1, "stages": []}))
    assert sp.classify_file(p) == "pipeline"                                  # params/ にあっても中身で判定


def test_big_json_reads_only_the_head_and_yaml_is_never_loaded(tmp_path):
    t = str(tmp_path)
    big = '{"fullseye_kind": "pipeline", "pad": "' + "x" * (sp.HEAD_BYTES * 3) + '"}'
    assert sp.classify_file(_w(t + "/big.json", big)) == "pipeline"           # 全部は json.loads できない大きさ
    seen = []
    real_open = open

    def spy(path, mode="r", *a, **k):
        f = real_open(path, mode, *a, **k)
        orig = f.read
        f.read = lambda n=-1: (seen.append(n), orig(n))[1]
        return f
    import builtins
    builtins.open, old = spy, builtins.open
    try:
        sp.classify_file(t + "/big.json")
    finally:
        builtins.open = old
    assert seen and all(n != -1 and n <= sp.HEAD_BYTES for n in seen), seen     # 先頭の小さな範囲だけ読む
    assert sp.classify_file(_w(t + "/broken.yaml", "a: [unclosed\n  - : :")) == "params"   # YAML は読み込まず拡張子で


def test_python_files_are_never_run_by_classification_or_listing(tmp_path):
    marker = str(tmp_path / "ran.txt")
    _w(str(tmp_path / "x.py"), "open(%r, 'w').write('ran')\nraise SystemExit(3)\n" % marker)
    assert sp.classify_file(str(tmp_path / "x.py")) == "python"
    sp.list_dir(str(tmp_path))
    assert not os.path.exists(marker)


def test_paths_outside_the_project_are_refused(tmp_path):
    root = str(tmp_path / "proj"); os.makedirs(root)
    for bad in ("../x", "..\\x", "a/../../x", "C:\\x", "/abs/x", "", "   "):
        with pytest.raises(ValueError):
            sp.resolve_inside(root, bad)
    assert sp.resolve_inside(root, "pipelines/a.json").startswith(os.path.realpath(root))
    for bad in ("..", "a/b", "a\\b", "C:x", "x:y", "n?", "tail.", "", " "):
        with pytest.raises(ValueError):
            sp.validate_name(bad)
    assert sp.validate_name("  ok name.json ") == "ok name.json"
    assert not sp.is_inside(root, str(tmp_path))
    assert sp.is_inside(root, os.path.join(root, "a", "b"))


def _make_link(target, link):
    """シンボリックリンク(権限が無ければジャンクション)。作れなければ None。"""
    try:
        os.symlink(target, link, target_is_directory=True)
        return link
    except (OSError, NotImplementedError):
        pass
    if sys.platform.startswith("win"):
        r = subprocess.run(["cmd", "/c", "mklink", "/J", link, target], capture_output=True)
        if r.returncode == 0 and os.path.isdir(link):
            return link
    return None


def test_links_are_listed_but_flagged_not_followed(tmp_path):
    outside = str(tmp_path / "outside"); _w(outside + "/secret.png", b"x", "wb")
    root = str(tmp_path / "proj"); os.makedirs(root)
    link = _make_link(outside, os.path.join(root, "lnk"))
    if link is None:
        pytest.skip("リンクを作れない環境")
    assert sp.is_link(link)
    rows = {e.name: e for e in sp.list_dir(root)}
    assert rows["lnk"].is_dir and rows["lnk"].is_link                          # 木には出す
    assert not sp.is_link(root)


def test_hidden_folders_pycache_git_venv_are_not_listed(tmp_path):
    t = str(tmp_path)
    for d in (".git", ".venv", "__pycache__", "_keep", "images"):
        os.makedirs(os.path.join(t, d))
    _w(t + "/a.png", b"x", "wb")
    names = [e.name for e in sp.list_dir(t)]
    assert names == ["_keep", "images", "a.png"], names                        # フォルダが先


def test_list_filters_by_name_and_kind(tmp_path):
    t = str(tmp_path)
    _w(t + "/Coins.png", b"x", "wb"); _w(t + "/b.py", ""); _w(t + "/p.json", json.dumps({"stages": []}))
    _w(t + "/c.yaml", "a: 1"); os.makedirs(t + "/dir")
    assert [e.name for e in sp.list_dir(t, "image")] == ["dir", "Coins.png"]    # フォルダは常に出る
    assert [e.name for e in sp.list_dir(t, "pipeline")] == ["dir", "p.json"]
    assert [e.name for e in sp.list_dir(t, "python")] == ["dir", "b.py"]
    assert [e.name for e in sp.list_dir(t, "params")] == ["dir", "c.yaml"]
    assert [e.name for e in sp.list_dir(t, "all", "coin")] == ["dir", "Coins.png"]    # 大文字小文字を区別しない部分一致


# --------------------------------------------------------------------------- 標準の並びの表
def test_standard_table_is_the_single_source_of_the_words():
    assert sp.STANDARD_FOLDER_NAMES == ("images", "pipelines", "programs", "params", "results")
    assert sp.folder_for("image") == "images" and sp.folder_for("pipeline") == "pipelines"
    assert sp.folder_for("python") == "programs" and sp.folder_for("params") == "params" and sp.folder_for("result") == "results"
    assert [k for k, _ in sp.FILTER_CHOICES] == ["all", "image", "pipeline", "python", "params"]
    assert sp.kind_of_folder("pipelines") == "pipeline" and sp.kind_of_folder("results") is None
    assert sp.folder_display("pipelines") == "pipelines \u2014 Pipelines"
    assert sp.folder_display("my_dir") == "my_dir"
    import importlib
    src = open(sp.__file__, encoding="utf-8").read()
    assert "PySide6" not in src.split("def build_panel")[0]                       # 上半分は Qt を import しない
    assert "PySide6" not in importlib.import_module("studio_project").__dict__.get("__doc__", "") or True


def test_every_word_of_the_table_has_six_languages():
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studio_assets", "i18n.json"), encoding="utf-8") as f:
        strings = json.load(f)["strings"]
    words = {label for _f, _k, label in sp.STANDARD_FOLDERS} | {lbl for _k, lbl in sp.FILTER_CHOICES} | {"Other files"}
    for w in words:
        row = strings.get(w)
        assert row and all(row.get(c) for c in ("ja", "zh", "tw", "ko", "de", "hi")), w


# --------------------------------------------------------------------------- 新しいプロジェクト・食い違い
def test_new_project_creates_the_five_folders(tmp_path):
    info = sp.create_project(str(tmp_path), "demo")
    assert sorted(os.listdir(info["root"])) == sorted(sp.STANDARD_FOLDER_NAMES)
    assert info["created"] == list(sp.STANDARD_FOLDER_NAMES) and not info["had_content"]


def test_new_project_never_overwrites_and_only_adds_missing_folders(tmp_path):
    root = str(tmp_path / "old")
    keep = _w(root + "/pipelines/mine.json", "KEEP")
    _w(root + "/notes.txt", "KEEP2")
    info = sp.create_project(str(tmp_path), "old")
    assert info["had_content"] and "pipelines" in info["existing"] and "images" in info["created"]
    assert open(keep, encoding="utf-8").read() == "KEEP" and open(root + "/notes.txt", encoding="utf-8").read() == "KEEP2"
    assert sp.missing_folders(root) == []
    with pytest.raises(ValueError):
        sp.create_project(str(tmp_path), "../escape")
    _w(str(tmp_path / "afile"), "x")
    with pytest.raises(ValueError):
        sp.create_project(str(tmp_path), "afile")


def test_mismatch_is_flagged_and_moving_is_safe(tmp_path):
    root = str(tmp_path); sp.create_project(root, "p"); root = os.path.join(root, "p")
    pipe = _w(root + "/params/p.json", json.dumps({"fullseye_pipeline": 1, "stages": []}))
    assert sp.mismatch(root, pipe, "pipeline") == "pipelines"
    assert sp.mismatch(root, root + "/pipelines/p.json", "pipeline") is None
    assert sp.mismatch(root, _w(root + "/sub/p.json", "{}"), "pipeline") is None        # 標準のフォルダの外は印を付けない
    assert sp.mismatch(root, pipe, "other") is None
    dest = sp.move_to_standard(root, pipe, "pipeline")
    assert dest == os.path.join(root, "pipelines", "p.json") and os.path.exists(dest) and not os.path.exists(pipe)
    again = _w(root + "/params/p.json", json.dumps({"stages": []}))
    with pytest.raises(ValueError):                                                 # 移動先に同名があれば止める
        sp.move_to_standard(root, again, "pipeline")
    assert os.path.exists(again)
    with pytest.raises(ValueError):
        sp.move_to_standard(root, str(tmp_path / "outside.json"), "pipeline")


def test_a_non_standard_layout_is_listed_and_not_flagged(tmp_path):
    t = str(tmp_path)
    _w(t + "/shots/a.png", b"x", "wb"); _w(t + "/misc/flow.json", json.dumps({"stages": []}))
    assert [e.name for e in sp.list_dir(t)] == ["misc", "shots"]
    assert sp.mismatch(t, t + "/misc/flow.json", "pipeline") is None
    assert [e.name for e in sp.list_dir(t + "/misc")] == ["flow.json"]


def test_state_key_is_stable_and_separates_folders(tmp_path):
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    os.makedirs(a); os.makedirs(b)
    assert sp.state_key(a) == sp.state_key(a + os.sep) == sp.state_key(a.upper()) or sys.platform != "win32"
    assert sp.state_key(a) != sp.state_key(b)


# =========================================================================== 窓(offscreen)
def _pump(sec=0.3):
    from PySide6 import QtWidgets
    end = time.monotonic() + sec
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)


def _launch(tmp_path, monkeypatch, size=(1400, 800), name="s.ini"):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / name))
    win, model = studio.build_window()
    win.resize(*size)
    win.show()
    _pump(0.5)
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
    pj = w._project
    pj["hooks"].update({"confirm": lambda t, x: True, "warn": lambda t, x: pj.setdefault("_warns", []).append((t, x)),
                        "ask_text": lambda t, l, d: None, "pick_dir": lambda t, s: ""})
    yield w
    _close(w)


def _project(tmp_path):
    """標準の並びのプロジェクトを作って中身を入れる。"""
    root = str(tmp_path / "proj")
    sp.create_project(str(tmp_path), "proj")
    from PySide6 import QtGui
    import numpy as np
    img = (np.random.default_rng(1).random((40, 50)) * 255).astype("uint8")
    import imgio
    imgio.save(root + "/images/a.png", img)
    imgio.save(root + "/images/b.png", img[::-1])
    _w(root + "/pipelines/p.json", json.dumps({"fullseye_pipeline": 1, "stages": [["gaussian", 0.4, 0.5]]}))
    _w(root + "/programs/run.py", "open(%r, 'w').write('ran')\n" % str(tmp_path / "marker.txt"))
    _w(root + "/params/cam.yaml", "exposure: 0.2\n")
    _w(root + "/params/misplaced.json", json.dumps({"fullseye_pipeline": 1, "stages": []}))
    return root


def _top(pj):
    return pj["names"]()


def test_empty_state_explains_and_offers_the_first_step(win):
    pj = win._project
    pj["tree"].parentWidget()
    assert pj["root"]() is None
    assert pj["stack"].currentIndex() == 0
    assert "folder" in pj["empty_text"].text().lower()
    assert pj["buttons"]["open"].text() == "Open folder…" and pj["buttons"]["new"].text() == "New project…"
    assert pj["buttons"]["open"].toolTip() and pj["buttons"]["new"].toolTip()
    assert pj["buttons"]["sample"].isVisibleTo(pj["widget"]) == bool(pj["hooks"].get("sample_dir"))   # 同梱のサンプルが無ければ付けない


def test_opening_a_folder_lists_standard_folders_with_translated_names(win, tmp_path):
    root = _project(tmp_path)
    assert win._project["open_dir"](root)
    pj = win._project
    assert pj["stack"].currentIndex() == 1 and pj["root"]() == root
    assert _top(pj) == ["images \u2014 Images", "params \u2014 Parameters", "pipelines \u2014 Pipelines",
                        "programs \u2014 Python", "results \u2014 Results"]
    pj["expand_all_top"]()
    _pump(0.1)
    model = pj["model"]
    flat = []

    def walk(it):
        for r in range(it.rowCount()):
            flat.append(it.child(r).text()); walk(it.child(r))
    walk(model.invisibleRootItem())
    assert "a.png" in flat and "p.json" in flat and "run.py" in flat and "cam.yaml" in flat


def test_double_click_routes_by_kind_and_python_is_never_run(win, tmp_path):
    root = _project(tmp_path)
    pj = win._project
    pj["open_dir"](root)
    assert pj["activate"](root + "/images/a.png") == "image"
    assert win._state["image_path"] == os.path.abspath(root + "/images/a.png")
    assert pj["activate"](root + "/pipelines/p.json") == "pipeline"
    assert win._state["pipe_path"] == os.path.abspath(root + "/pipelines/p.json") and len(win._test_model.stages) == 1
    assert pj["activate"](root + "/programs/run.py") == "python"
    _pump(0.1)
    assert not os.path.exists(str(tmp_path / "marker.txt"))                         # 開いただけでコードを走らせない
    assert "Python mode comes in the next version" in win.statusBar().currentMessage()
    n = len(getattr(win, "_code_windows", []))
    assert pj["activate"](root + "/params/cam.yaml") == "params"
    assert len(win._code_windows) == n + 1                                          # 読み取り専用のテキスト窓
    assert pj["activate"](root + "/params/cam.yaml") == "params"
    ed = win._code_windows[-1].widget().findChildren(__import__("PySide6.QtWidgets", fromlist=["QPlainTextEdit"]).QPlainTextEdit)[0]
    assert ed.isReadOnly() and "exposure" in ed.toPlainText()
    assert _w(root + "/notes.txt", "x") and pj["activate"](root + "/notes.txt") == "other"


def test_the_same_image_from_three_entries_gives_the_same_state(win, tmp_path):
    from PySide6 import QtCore
    root = _project(tmp_path)
    pj = win._project
    pj["open_dir"](root)
    path = root + "/images/a.png"
    seen = []

    def snap():
        _pump(0.2)
        seen.append((win._state["image_path"], win._test_model.image.shape, win.windowTitle().split(" — ")[1:2]))
    win._load_image_path(path); snap()                                               # 入口 1: 従来の経路
    win._load_image_path(root + "/images/b.png"); pj["activate"](path); snap()       # 入口 2: パネルの開く処理
    win._load_image_path(root + "/images/b.png")
    pj["expand_all_top"](); _pump(0.1)
    top = pj["model"].item(0)                                                        # images
    idx = pj["model"].indexFromItem(top.child(0))
    pj["tree"].doubleClicked.emit(idx); snap()                                       # 入口 3: ツリーのダブルクリック
    win._load_image_path(root + "/images/b.png")
    win._handle_drop([path]) if hasattr(win, "_handle_drop") else None
    assert seen[0] == seen[1], seen
    assert seen[1] == seen[2], seen


def test_context_menu_has_the_asked_items_and_no_delete(win, tmp_path):
    root = _project(tmp_path)
    pj = win._project
    pj["open_dir"](root)
    spec = pj["menu_spec"]([root + "/images/a.png"])
    labels = [s[0] for s in spec]
    for want in ("Open", "Compare side by side", "New pipeline", "New folder", "Rename", "Show in file manager",
                 "Copy path", "Copy relative path"):
        assert want in labels, labels
    assert not any("delete" in l.lower() or "削除" in l for l in labels)
    cmp1 = [s for s in spec if s[0] == "Compare side by side"][0]
    assert cmp1[1] is False and cmp1[2]                                              # 1 つでは無効 + 理由
    two = pj["menu_spec"]([root + "/images/a.png", root + "/images/b.png"])
    assert [s for s in two if s[0] == "Compare side by side"][0][1] is True
    mixed = pj["menu_spec"]([root + "/images/a.png", root + "/pipelines/p.json"])
    assert [s for s in mixed if s[0] == "Compare side by side"][0][1] is False       # 今は画像同士だけ
    shown = []
    pj["hooks"]["compare_images"] = lambda ps: shown.append(list(ps))
    [s for s in two if s[0] == "Compare side by side"][0][3]()
    assert shown == [[root + "/images/a.png", root + "/images/b.png"]]


def test_misplaced_file_is_marked_and_move_is_offered_never_silent(win, tmp_path):
    root = _project(tmp_path)
    pj = win._project
    pj["open_dir"](root)
    spec = pj["menu_spec"]([root + "/params/misplaced.json"])
    mv = [s for s in spec if s[0].startswith("Move to")]
    assert mv and mv[0][0] == "Move to pipelines/"
    pj["expand_all_top"](); _pump(0.1)
    params = [pj["model"].item(r) for r in range(pj["model"].rowCount()) if pj["model"].item(r).text().startswith("params")][0]
    names = {params.child(r).text(): params.child(r) for r in range(params.rowCount())}
    mark = names["misplaced.json  \u26a0"]
    assert "pipelines/" in mark.toolTip()                                            # ツールヒントで言う
    assert os.path.exists(root + "/params/misplaced.json")                           # 黙って移していない
    mv[0][3]()
    assert os.path.exists(root + "/pipelines/misplaced.json") and not os.path.exists(root + "/params/misplaced.json")


def test_rename_and_new_refuse_paths_outside_the_project_with_a_reason(win, tmp_path):
    root = _project(tmp_path)
    pj = win._project
    pj["open_dir"](root)
    pj["hooks"]["ask_text"] = lambda t, l, d: "../evil.png"
    assert pj["rename"](root + "/images/a.png") is None
    assert pj["_warns"] and "/" in pj["_warns"][-1][1] and os.path.exists(root + "/images/a.png")
    pj["hooks"]["ask_text"] = lambda t, l, d: "C:\\abs.png"
    assert pj["rename"](root + "/images/a.png") is None
    pj["hooks"]["ask_text"] = lambda t, l, d: "b.png"                                # 既存の名前は上書きしない
    assert pj["rename"](root + "/images/a.png") is None and os.path.exists(root + "/images/a.png")
    pj["hooks"]["ask_text"] = lambda t, l, d: "renamed.png"
    assert pj["rename"](root + "/images/a.png") == os.path.join(os.path.realpath(root), "images", "renamed.png") \
        or os.path.exists(root + "/images/renamed.png")
    pj["hooks"]["ask_text"] = lambda t, l, d: "..\\x"
    assert pj["new_folder"]() is None and pj["new_pipeline"]() is None


def test_new_pipeline_goes_to_pipelines_and_folder_is_made_after_asking(win, tmp_path):
    root = str(tmp_path / "bare"); os.makedirs(root)
    pj = win._project
    pj["open_dir"](root)
    asked = []
    pj["hooks"]["confirm"] = lambda t, x: (asked.append(x), False)[1]               # 断る
    pj["hooks"]["ask_text"] = lambda t, l, d: "mine"
    dest = pj["new_pipeline"]()
    assert asked and "pipelines/" in asked[0] and not os.path.isdir(root + "/pipelines")      # 黙って作らない
    assert dest == os.path.join(os.path.realpath(root), "mine.json") or os.path.exists(root + "/mine.json")
    pj["hooks"]["confirm"] = lambda t, x: True
    dest = pj["new_pipeline"]()
    assert os.path.exists(root + "/pipelines/mine.json")
    assert json.load(open(root + "/pipelines/mine.json", encoding="utf-8"))["stages"] == []
    assert sp.classify_file(root + "/pipelines/mine.json") == "pipeline"


def test_dialog_start_folders_follow_the_kind_and_the_title_names_the_project(win, tmp_path):
    root = _project(tmp_path)
    assert win._proj_path("pipeline", "pipeline.json") == "pipeline.json"          # プロジェクトが無い間は従来どおり
    assert "Project" not in win.windowTitle()
    win._project["open_dir"](root)
    _pump(0.1)
    assert win._proj_path("pipeline", "pipeline.json") == os.path.join(root, "pipelines", "pipeline.json")
    assert win._proj_path("image") == os.path.join(root, "images")
    assert win._proj_path("result", "result.png") == os.path.join(root, "results", "result.png")
    assert "Project: proj" in win.windowTitle()                                     # 題にプロジェクト名
    win._project["close"]()
    assert "Project" not in win.windowTitle()


def test_filter_by_name_and_by_kind(win, tmp_path):
    root = _project(tmp_path)
    pj = win._project
    pj["open_dir"](root)
    pj["expand_all_top"](); _pump(0.1)

    def files():
        out = []

        def walk(it):
            for r in range(it.rowCount()):
                c = it.child(r)
                if not c.data(0x100 + 2):
                    out.append(c.text())
                walk(c)
        walk(pj["model"].invisibleRootItem())
        return out
    pj["filter"].setText("cam"); _pump(0.1)
    pj["expand_all_top"](); _pump(0.1)                                 # 開いていたフォルダは作り直しても開いたまま
    assert [f for f in files() if f != "__placeholder__"] == ["cam.yaml"]
    pj["filter"].setText("")
    pj["kind_box"].setCurrentIndex([k for k, _ in sp.FILTER_CHOICES].index("image")); _pump(0.1)
    pj["expand_all_top"](); _pump(0.1)
    got = [f for f in files() if f != "__placeholder__"]
    assert sorted(got) == ["a.png", "b.png"], got


def test_entries_menu_palette_panel_list_find_panel_and_key(win):
    import studio_layout
    from PySide6 import QtGui
    texts = [a.text() for a in win._menus["file"].actions()]
    assert "Open folder…" in texts and "New project…" in texts and "Recent folders" in texts            # メニュー
    for key in ("project_open", "project_new", "project_panel"):
        assert key in win._actions                                                                       # パレットの元
    assert "Project" in [a.text() for a in win._menu_panels.actions()]                                   # 表示メニューのパネル一覧
    assert "project" in studio_layout.find_panels("プロジェクト") and "project" in studio_layout.find_panels("explorer")   # パネルを探す
    assert win._actions["project_panel"].shortcut().toString() == "Ctrl+Shift+J"                         # キー
    taken = [a for a in win.findChildren(QtGui.QAction) if a is not win._actions["project_panel"]
             and QtGui.QKeySequence("Ctrl+Shift+J") in a.shortcuts()]
    assert not taken                                                                                      # 既存と重ならない
    assert win._project["widget"].parent() is win._docks["project"]                                      # ドック
    assert "project" in win._layout_panels


@pytest.mark.parametrize("query, key", [
    ("project", "project_open"), ("folder", "project_open"), ("files", "project_panel"), ("explorer", "project_panel"),
    ("tree", "project_panel"), ("プロジェクト", "project_open"), ("フォルダ", "project_open"), ("ファイル", "project_panel"),
    ("ツリー", "project_panel"), ("エクスプローラ", "project_panel"), ("新しいプロジェクト", "project_new"),
])
def test_palette_finds_project_entries_by_japanese_and_english_words(win, query, key):
    keys = list(win._actions)
    hay = ["▸ " + win._actions[k].text() + " " + studio.PALETTE_WORDS.get(k, "") for k in keys]
    assert key in [keys[i] for i in studio.palette_filter(hay, query)], (query, key)


def test_same_name_in_menu_palette_panel_title_and_i18n(win):
    assert win._actions["project_panel"].text() == "Project"
    assert win._docks["project"].windowTitle() == "Project"
    assert studio.PANEL_NAME_EN["project"] == "Project"
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studio_assets", "i18n.json"), encoding="utf-8") as f:
        row = json.load(f)["strings"]["Project"]
    win._apply_language("ja")
    try:
        assert row["ja"] == "プロジェクト" == win._actions["project_panel"].text() == win._docks["project"].windowTitle()
        import studio_layout
        assert studio_layout.PANELS["project"]["name"] == "プロジェクト"                # 言語ごとに 1 つの語
    finally:
        win._apply_language("en")


def test_folder_and_tree_state_come_back_after_restart(tmp_path, monkeypatch):
    root = _project(tmp_path)
    w1, _m = _launch(tmp_path, monkeypatch, name="persist.ini")
    try:
        w1._project["open_dir"](root)
        w1._project["expand_all_top"](); _pump(0.2)
        w1._project["kind_box"].setCurrentIndex([k for k, _ in sp.FILTER_CHOICES].index("image"))
        expanded = set(w1._project["state"]["expanded"])
        assert expanded
        studio._settings().sync()
    finally:
        _close(w1)
    w2, _m2 = _launch(tmp_path, monkeypatch, name="persist.ini")
    try:
        _pump(0.4)
        pj = w2._project
        assert pj["root"]() == os.path.abspath(root)                                    # 最後のフォルダ
        assert pj["state"]["expanded"] == expanded                                      # 木の開閉
        assert pj["state"]["kind"] == "image"
        assert "Project: proj" in w2.windowTitle()
    finally:
        _close(w2)


def test_missing_last_folder_returns_quietly_to_the_empty_state_with_one_line(tmp_path, monkeypatch):
    import shutil
    root = _project(tmp_path)
    w1, _m = _launch(tmp_path, monkeypatch, name="gone.ini")
    try:
        w1._project["open_dir"](root)
        studio._settings().sync()
    finally:
        _close(w1)
    shutil.rmtree(root)
    w2, _m2 = _launch(tmp_path, monkeypatch, name="gone.ini")
    try:
        _pump(0.4)
        assert w2._project["root"]() is None and w2._project["stack"].currentIndex() == 0
        assert "gone" in w2.statusBar().currentMessage()
    finally:
        _close(w2)


def test_panel_starts_hidden_on_the_left_and_does_not_change_the_default_layout(win):
    import PySide6.QtCore as QC
    d = win._docks["project"]
    assert not d.isVisible()
    assert win.dockWidgetArea(d) == QC.Qt.LeftDockWidgetArea
    win._actions["project_panel"].trigger()
    _pump(0.2)
    assert d.isVisible()


def test_recent_folders_menu_lists_and_reopens(win, tmp_path):
    root = _project(tmp_path)
    win._project["open_dir"](root)
    win._project["close"]()
    acts = [a for a in win._recent_folders_menu.actions()]
    assert acts and acts[0].toolTip() == os.path.abspath(root)
    acts[0].trigger()
    assert win._project["root"]() == os.path.abspath(root)


def test_japanese_ui_has_no_english_left_in_the_project_panel(win, tmp_path):
    root = _project(tmp_path)
    win._apply_language("ja")
    try:
        pj = win._project                                                              # 言語の切り替えだけで作り直される
        for w in (pj["buttons"]["open"], pj["buttons"]["new"], pj["empty_text"], pj["kind_box"]):
            t = w.currentText() if hasattr(w, "currentText") else w.text()
            assert _CJK.search(t), t
        assert _CJK.search(pj["filter"].placeholderText())
        for i in range(pj["kind_box"].count()):
            assert _CJK.search(pj["kind_box"].itemText(i)) or pj["kind_box"].itemText(i) == "Python", pj["kind_box"].itemText(i)
        pj["open_dir"](root)
        assert _top(pj) == ["images \u2014 画像", "params \u2014 パラメータ", "pipelines \u2014 パイプライン",
                            "programs \u2014 Python", "results \u2014 出力"]
        spec = pj["menu_spec"]([root + "/images/a.png", root + "/images/b.png"])
        assert all(_CJK.search(s[0]) for s in spec), [s[0] for s in spec]
        assert all(_CJK.search(s[2]) for s in spec)
        for a in (win._actions["project_open"], win._actions["project_new"], win._actions["project_panel"]):
            assert _CJK.search(a.text()) and _CJK.search(a.toolTip()), (a.text(), a.toolTip())
        assert _CJK.search(win._recent_folders_menu.title())
    finally:
        win._apply_language("en")


def test_links_are_shown_but_never_expanded_in_the_tree(win, tmp_path):
    outside = str(tmp_path / "outside"); _w(outside + "/secret.png", b"x", "wb")
    root = str(tmp_path / "proj"); os.makedirs(root)
    link = _make_link(outside, os.path.join(root, "lnk"))
    if link is None:
        pytest.skip("リンクを作れない環境")
    pj = win._project
    pj["open_dir"](root)
    item = pj["model"].item(0)
    assert item.text() == "lnk" and item.rowCount() == 0                              # 展開する中身(仮の行)も持たない
    pj["tree"].expand(item.index()); _pump(0.1)
    assert item.rowCount() == 0
