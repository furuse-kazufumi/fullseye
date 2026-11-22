"""2026-11-22 の Studio adversarial review で確認された finding の回帰試験。"""
from __future__ import annotations

import builtins
import hashlib
import io
import json
import os

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6 import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _close_window(win):
    win._knob_timer.stop()
    if getattr(win, "_pyedit", None):
        tabs = win._pyedit["tabs"]
        for i in range(tabs.count()):
            tabs.widget(i)._dirty = False
        win._pyedit["dlg"].close()
    win.close_guard = None
    win.close()


def test_f1_open_keeps_directives_as_data_until_explicit_apply(qapp, tmp_path, monkeypatch):
    import cv2
    import mesh
    import studio

    pipe = tmp_path / "directives.json"
    pipe.write_text(json.dumps({
        "fullseye_pipeline": 1,
        "stages": [["gaussian", 0.3, 0.5]],
        "directives": ["set_system ('thread_num', 4)", "disp_points3d ('pts.xyz')"],
    }), encoding="utf-8")
    (tmp_path / "pts.xyz").write_text("0 0 0\n1 0 0\n0 1 0\n", encoding="utf-8")

    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    thread_calls = []
    point_calls = []
    settings_writes = []

    class FakeSettings:
        def __init__(self):
            self.groups = []

        def beginGroup(self, name):
            self.groups.append(str(name))

        def endGroup(self):
            self.groups.pop()

        def value(self, _key, default=None):
            return default

        def setValue(self, key, value):
            settings_writes.append(("/".join(self.groups + [str(key)]), value))

        def sync(self):
            return None

        def status(self):
            from PySide6 import QtCore
            return QtCore.QSettings.NoError

        def fileName(self):
            return str(tmp_path / "fake.ini")

    fake_settings = FakeSettings()
    monkeypatch.setattr(studio, "_settings", lambda: fake_settings)
    monkeypatch.setattr(cv2, "setNumThreads", lambda n: thread_calls.append(n))
    monkeypatch.setattr(
        mesh,
        "read_points",
        lambda path, with_colors=True: (
            point_calls.append(path) or __import__("numpy").zeros((3, 3)), None,
        ),
    )
    try:
        win._state["disp_log"] = []
        win._open_pipe_path(str(pipe))
        assert model.directives == ["set_system ('thread_num', 4)", "disp_points3d ('pts.xyz')"]
        assert win._state["dev_lines"] == model.directives
        assert thread_calls == []
        assert point_calls == []
        assert not any(key.startswith("system/") for key, _value in settings_writes)
        assert win._state["disp_log"] == []
        assert win._state["directives_pending"] == 2
        assert "not applied" in win._program["status"]().text().lower()

        win._program["apply"]()
        qapp.processEvents()
        assert thread_calls == [4]
        assert len(point_calls) == 1
        assert any(key == "system/threads" for key, _value in settings_writes)
        assert win._state["disp_log"]
        assert not win._state.get("directives_pending")
    finally:
        _close_window(win)


@pytest.mark.parametrize("line", ["dev_evil_x (1)", "disp_anything (1)", "set_systemx (1)"])
def test_f1_directive_validation_uses_the_exact_allowlist(line):
    import studio

    with pytest.raises(ValueError, match="directive 1"):
        studio.validate_directives({"directives": [line]})


@pytest.mark.parametrize("path", [r"\\server\share\p.xyz", "//server/share/p.xyz", "C:/x/p.xyz", "../p.xyz"])
def test_f1_file_directive_lexically_refuses_unsafe_paths(path):
    import studio

    with pytest.raises(ValueError, match="directive 1"):
        studio.validate_directives({"directives": ["disp_points3d (%r)" % path]})


def test_f1_unc_at_apply_never_touches_the_filesystem_or_reader(qapp, monkeypatch):
    import mesh
    import studio

    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    exists_calls = []
    reader_calls = []
    monkeypatch.setattr(studio.os.path, "exists", lambda path: exists_calls.append(path) or False)
    monkeypatch.setattr(mesh, "read_points", lambda *a, **k: reader_calls.append((a, k)))
    try:
        win._state["disp_log"] = []
        win._apply_dev_directives(r"disp_points3d ('\\server\share\p.xyz')")
        assert exists_calls == []
        assert reader_calls == []
        assert win._state["disp_log"][-1]["ok"] is False
        assert "network" in win._state["disp_log"][-1]["error"].lower() or "unc" in win._state["disp_log"][-1]["error"].lower()
    finally:
        _close_window(win)


@pytest.mark.parametrize("kind", ["absolute", "unc", "parent"])
def test_f2_unsafe_input_refs_need_confirmation_without_touching_given_path(kind, tmp_path, monkeypatch):
    import studio_result

    base = tmp_path / "project"
    base.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")
    given = {"absolute": str(outside), "unc": r"\\server\share\outside.png", "parent": "../outside.png"}[kind]
    forbidden = str(outside) if kind != "unc" else given
    isfile_calls = []
    hash_calls = []
    real_isfile = os.path.isfile

    def watched_isfile(path):
        isfile_calls.append(os.fspath(path))
        assert os.path.normcase(os.fspath(path)) != os.path.normcase(forbidden)
        return real_isfile(path)

    monkeypatch.setattr(studio_result.os.path, "isfile", watched_isfile)
    monkeypatch.setattr(studio_result, "file_sha256", lambda path: hash_calls.append(os.fspath(path)) or "x")
    result = studio_result.resolve_input_ref({"path": given, "sha256": "x"}, str(base))
    assert result["status"] == "needs_confirmation"
    assert result["path"] is None and given in result["message"]
    assert forbidden not in isfile_calls
    assert forbidden not in hash_calls


def test_f2_outward_symlink_is_not_opened(tmp_path, monkeypatch):
    import studio_result

    base = tmp_path / "project"
    base.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")
    link = base / "linked.png"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip("symlink/junction could not be created: %s" % exc)
    hash_calls = []
    monkeypatch.setattr(studio_result, "file_sha256", lambda path: hash_calls.append(os.fspath(path)) or "x")
    result = studio_result.resolve_input_ref({"path": "linked.png", "sha256": "x"}, str(base))
    assert result["status"] == "needs_confirmation"
    assert result["path"] is None and result["message"]
    assert hash_calls == []


def test_f2_inside_relative_is_ok_but_absolute_relinks_by_basename(tmp_path):
    import studio_result

    base = tmp_path / "project"
    base.mkdir()
    inside = base / "in.png"
    inside.write_bytes(b"inside")
    digest = hashlib.sha256(inside.read_bytes()).hexdigest()
    assert studio_result.resolve_input_ref({"path": "in.png", "sha256": digest}, str(base))["status"] == "ok"
    old = tmp_path / "old" / "in.png"
    old.parent.mkdir()
    old.write_bytes(inside.read_bytes())
    result = studio_result.resolve_input_ref({"path": str(old), "sha256": digest}, str(base))
    assert result["status"] == "relinked" and result["path"] == str(inside)


def test_f4_strict_json_boundaries_constants_duplicates_and_deep_input():
    from json_safety import MAX_JSON_DEPTH
    from json_strict import DEFAULT_MAX_JSON_BYTES, UntrustedJSONError, loads_untrusted

    exact = b'"' + b"a" * (DEFAULT_MAX_JSON_BYTES - 2) + b'"'
    assert len(loads_untrusted(exact, max_bytes=DEFAULT_MAX_JSON_BYTES)) == DEFAULT_MAX_JSON_BYTES - 2
    with pytest.raises(UntrustedJSONError, match="bytes"):
        loads_untrusted(exact + b" ", max_bytes=DEFAULT_MAX_JSON_BYTES)

    at_depth = "[" * MAX_JSON_DEPTH + "0" + "]" * MAX_JSON_DEPTH
    assert loads_untrusted(at_depth) is not None
    with pytest.raises(UntrustedJSONError, match="depth|nesting"):
        loads_untrusted("[" * (MAX_JSON_DEPTH + 1) + "0" + "]" * (MAX_JSON_DEPTH + 1))
    with pytest.raises(UntrustedJSONError, match="depth|nesting"):
        loads_untrusted("[" * 100_000)
    for constant in ("NaN", "Infinity", "-Infinity"):
        with pytest.raises(UntrustedJSONError, match=constant):
            loads_untrusted(constant)
    with pytest.raises(UntrustedJSONError, match="duplicate.*x"):
        loads_untrusted('{"x": 1, "x": 2}')


def test_f4_read_untrusted_reads_only_limit_plus_one(monkeypatch):
    from json_strict import UntrustedJSONError, read_untrusted

    seen = []

    class WatchedBytes(io.BytesIO):
        def read(self, size=-1):
            seen.append(size)
            return super().read(size)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    monkeypatch.setattr(builtins, "open", lambda *_a, **_k: WatchedBytes(b" " * 18))
    with pytest.raises(UntrustedJSONError, match="bytes"):
        read_untrusted("huge.json", max_bytes=16)
    assert seen == [17]


@pytest.mark.parametrize("body, reason", [('{"x": 1, "x": 2}', "duplicate"), ("NaN", "NaN")])
def test_f4_defs_io_maps_strict_refusals_to_definition_error(tmp_path, body, reason):
    import defs_io

    path = tmp_path / "bad.json"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(defs_io.DefinitionError, match=reason):
        defs_io.read_json(str(path))
    with pytest.raises(defs_io.DefinitionError, match=reason):
        defs_io.read_def(str(path))


@pytest.mark.parametrize("bad", ["nan", "duplicate", "depth"])
def test_f4_studio_refuses_strict_json_without_changing_current_pipeline(qapp, tmp_path, monkeypatch, bad):
    import studio
    from json_safety import MAX_JSON_DEPTH

    if bad == "nan":
        body = '{"fullseye_pipeline": 1, "stages": [["otsu", 0.5, 0.5]], "extra": NaN}'
    elif bad == "duplicate":
        body = ('{"fullseye_pipeline": 1, "stages": [["gaussian", 0.5, 0.5]], '
                '"stages": [["otsu", 0.5, 0.5]]}')
    else:
        nested = "[" * (MAX_JSON_DEPTH + 1) + "0" + "]" * (MAX_JSON_DEPTH + 1)
        body = '{"fullseye_pipeline": 1, "stages": [["otsu", 0.5, 0.5]], "extra": %s}' % nested
    path = tmp_path / (bad + ".json")
    path.write_text(body, encoding="utf-8")
    errors = []
    monkeypatch.setattr(studio, "ERROR_HOOK", lambda *args: errors.append(args))
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    model.stages = [["gaussian", 0.2, 0.3]]
    before = [list(s) for s in model.stages]
    try:
        win._open_pipe_path(str(path))
        assert [list(s) for s in model.stages] == before
        assert errors and any("Could not open pipeline" in str(arg) for arg in errors[-1])
    finally:
        _close_window(win)


@pytest.mark.parametrize("ext", ["json", "toml"])
def test_f5_parambundle_accepts_depth_64_and_refuses_65(tmp_path, ext):
    from json_safety import MAX_JSON_DEPTH
    from fullseye.parambundle import ParamFileError, load_params

    def body(depth):
        if ext == "json":
            return '{"a":' * depth + "1" + "}" * depth
        # TOML は解析木の暗黙 root table も 1 level。合計を *depth* にそろえる。
        return "[" + ".".join("a%d" % i for i in range(depth - 1)) + "]\nvalue = 1\n"

    ok = tmp_path / ("ok." + ext)
    bad = tmp_path / ("bad." + ext)
    ok.write_text(body(MAX_JSON_DEPTH), encoding="utf-8")
    bad.write_text(body(MAX_JSON_DEPTH + 1), encoding="utf-8")
    assert load_params(ok)
    with pytest.raises(ParamFileError, match="64|depth|nesting"):
        load_params(bad)


def test_f5_very_deep_parambundle_never_leaks_recursionerror(tmp_path):
    from fullseye.parambundle import ParamFileError, load_params

    path = tmp_path / "deep.json"
    path.write_text('{"a":' * 20_000 + "1" + "}" * 20_000, encoding="utf-8")
    with pytest.raises(ParamFileError, match="depth|nesting|deep"):
        load_params(path)


def test_f5_params_model_add_file_returns_reasoned_depth_refusal(tmp_path):
    from json_safety import MAX_JSON_DEPTH
    import studio_params_model

    path = tmp_path / "deep.json"
    path.write_text('{"a":' * (MAX_JSON_DEPTH + 1) + "1" + "}" * (MAX_JSON_DEPTH + 1), encoding="utf-8")
    result = studio_params_model.ParamsModel().add_file(str(path))
    assert not result.ok and result.code == "load.refused"
    assert "depth" in result.reason.lower() or "nesting" in result.reason.lower()


def test_f6_write_settings_reports_status_and_success(tmp_path):
    from PySide6 import QtCore
    from studio_settings import set_failure_reporter, write_settings

    class FakeSettings:
        def __init__(self, status):
            self._status = status
            self.values = {}
            self.removed = []

        def setValue(self, key, value):
            self.values[key] = value

        def remove(self, key):
            self.removed.append(key)

        def sync(self):
            return None

        def status(self):
            return self._status

        def fileName(self):
            return str(tmp_path / "settings.ini")

    reports = []
    set_failure_reporter(reports.append)
    good = FakeSettings(QtCore.QSettings.NoError)
    assert write_settings({"a": 1}, remove=["b"], settings=good) is None
    assert good.values == {"a": 1} and good.removed == ["b"] and reports == []
    bad = FakeSettings(QtCore.QSettings.AccessError)
    reason = write_settings({"a": 2}, settings=bad, what="preferences")
    assert reason and "could not be saved" in reason and str(tmp_path / "settings.ini") in reason
    assert reports == [reason]
    set_failure_reporter(None)                      # 他の試験へ偽の報告先を残さない


def test_f6_write_settings_removes_before_setting_so_a_rewritten_group_survives(tmp_path):
    """レイアウトの型の保存は「群を消してから書き直す」。消す前に書くと、書いた値まで消える。"""
    from PySide6 import QtCore
    from studio_settings import write_settings

    s = QtCore.QSettings(str(tmp_path / "presets.ini"), QtCore.QSettings.IniFormat)
    s.setValue("layout_presets/old/geometry", "g0")
    s.sync()
    reason = write_settings({"layout_presets/new/geometry": "g1", "layout_presets/new/state": "s1"},
                            remove=["layout_presets"], settings=s, what="layout presets")
    assert reason is None
    again = QtCore.QSettings(str(tmp_path / "presets.ini"), QtCore.QSettings.IniFormat)
    assert again.value("layout_presets/new/geometry") == "g1"
    assert again.value("layout_presets/new/state") == "s1"
    assert again.value("layout_presets/old/geometry") is None


def test_f6_params_and_pymode_save_state_surface_settings_failure(qapp, tmp_path):
    from PySide6 import QtCore
    import studio
    import studio_params_qt

    class FakeSettings:
        def __init__(self):
            self.values = {}

        def value(self, key, default=None):
            return self.values.get(key, default)

        def setValue(self, key, value):
            self.values[key] = value

        def remove(self, key):
            self.values.pop(key, None)

        def sync(self):
            return None

        def status(self):
            return QtCore.QSettings.AccessError

        def fileName(self):
            return str(tmp_path / "denied.ini")

    fake = FakeSettings()
    params = studio_params_qt.ParamsWindow(settings=lambda: fake)
    try:
        reason = params.save_state()
        assert reason and "could not be saved" in reason
        assert "could not be saved" in params.panel.message_label.full_text().lower()
    finally:
        params.close()

    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    try:
        pm = win._pymode
        pm.settings = lambda: fake
        reason = pm.save_state()
        assert reason and "could not be saved" in reason
        assert "could not be saved" in (pm.autosave_note.text() + pm.autosave_note.toolTip()).lower()
    finally:
        _close_window(win)


def test_f7_old_python_editor_save_is_atomic_and_marks_only_after_success(qapp, tmp_path, monkeypatch):
    import studio

    monkeypatch.setattr(studio, "ERROR_HOOK", lambda *_args: None)
    path = tmp_path / "script.py"
    original = b"print('old')\n"
    path.write_bytes(original)
    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    try:
        win._act_pyedit.trigger()
        qapp.processEvents()
        editor = win._pyedit["open_tab"]("print('old')\n", path=path)
        editor.setPlainText("print('new')\n")
        assert editor._dirty
        with monkeypatch.context() as patch:
            patch.setattr(studio.os, "replace", lambda *_a: (_ for _ in ()).throw(OSError("disk full")))
            assert win._pyedit["save_to"](str(path)) is False
        assert path.read_bytes() == original
        assert editor._dirty is True and editor._disk_text == "print('old')\n"

        assert win._pyedit["save_to"](str(path)) is True
        assert path.read_text(encoding="utf-8") == "print('new')\n"
        assert editor._dirty is False and editor._disk_text == "print('new')\n"
    finally:
        _close_window(win)
