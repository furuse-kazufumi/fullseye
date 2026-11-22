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


# Round 2: a path saved in a pipeline must not be touched before explicit consent.


def test_r2_shared_lexical_helpers_refuse_windows_aliases_and_devices():
    import studio_result

    bad = [
        "", "points.xyz:hidden", "dir. /points.xyz", "points.xyz ", "nul.xyz",
        "COM1", "com1.txt", "LPT¹.log", "CONIN$", "D:foo.xyz", "../x.xyz",
        "a//b.xyz", "a\x01b.xyz", 'bad<name>.xyz',
    ]
    for path in bad:
        assert studio_result._plain_relative_path_problem(path), path
    assert studio_result._plain_relative_path_problem("./safe/points.xyz") is None
    assert studio_result._plain_name(r"D:old\foo.png") == "foo.png"
    assert studio_result._plain_name("image.png:hidden") == ""


@pytest.mark.parametrize(
    "path",
    ["points.xyz:hidden", "dir. /points.xyz", "points.xyz ", "nul.xyz", "COM1", "D:foo.xyz"],
)
def test_r2_1b_validate_directives_refuses_windows_unsafe_names(path):
    import studio

    with pytest.raises(ValueError, match=r"directive 1:"):
        studio.validate_directives({"directives": ["disp_points3d (%r)" % path]})


def test_r2_1a_unc_pipeline_apply_never_touches_unc(qapp, monkeypatch):
    import mesh
    import studio

    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    calls = []

    def refuse(name, result=None):
        def watched(path, *args, **kwargs):
            value = os.fspath(path)
            calls.append((name, value))
            assert not value.startswith((r"\\", "//")), (name, value)
            return result
        return watched

    monkeypatch.setattr(studio.os.path, "realpath", refuse("realpath", "local"))
    monkeypatch.setattr(studio.os.path, "exists", refuse("exists", False))
    monkeypatch.setattr(studio.os, "lstat", refuse("lstat"))
    monkeypatch.setattr(mesh, "read_points", lambda path, **_k: calls.append(("reader", os.fspath(path))))
    try:
        win._state["pipe_path"] = r"\\server\share\pipe.json"
        win._state["disp_log"] = []
        win._apply_dev_directives("disp_points3d ('points.xyz')")
        assert win._state["disp_log"][-1]["ok"] is False
        assert "pipeline folder" in win._state["disp_log"][-1]["error"].lower()
        assert not any(name == "reader" for name, _path in calls)
    finally:
        _close_window(win)


def test_r2_1a_linked_3d_folder_stops_lstat_walk_at_link(qapp, tmp_path, monkeypatch):
    import mesh
    import studio

    base = tmp_path / "project"
    outside = tmp_path / "outside"
    base.mkdir(); outside.mkdir()
    (outside / "points.xyz").write_text("0 0 0\n", encoding="utf-8")
    link = base / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip("symlink/junction could not be created: %s" % exc)
    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    lstat_calls = []
    real_lstat = os.lstat
    monkeypatch.setattr(studio.os, "lstat", lambda path: lstat_calls.append(os.fspath(path)) or real_lstat(path))
    monkeypatch.setattr(studio.os.path, "realpath", lambda *_a, **_k: pytest.fail("realpath must not be called"))
    reader_calls = []
    monkeypatch.setattr(mesh, "read_points", lambda path, **_k: reader_calls.append(os.fspath(path)))
    try:
        win._state["pipe_path"] = str(base / "pipe.json")
        win._state["disp_log"] = []
        win._apply_dev_directives("disp_points3d ('link/points.xyz')")
        assert reader_calls == []
        assert lstat_calls[-1] == str(link)
        assert str(link / "points.xyz") not in lstat_calls
        assert "link" in win._state["disp_log"][-1]["error"].lower()
    finally:
        _close_window(win)


def test_r2_2a_outward_link_needs_confirmation_without_following_it(tmp_path, monkeypatch):
    import studio_result

    base = tmp_path / "project"
    outside = tmp_path / "outside"
    base.mkdir(); outside.mkdir()
    (outside / "image.png").write_bytes(b"outside")
    link = base / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip("symlink/junction could not be created: %s" % exc)
    calls = []
    real_lstat = os.lstat
    monkeypatch.setattr(studio_result.os, "lstat", lambda path: calls.append(os.fspath(path)) or real_lstat(path))
    monkeypatch.setattr(studio_result.os.path, "realpath", lambda *_a, **_k: pytest.fail("realpath must not be called"))
    result = studio_result.resolve_input_ref(
        {"path": "link/image.png", "sha256": "unused"}, str(base))
    assert result["status"] == "needs_confirmation"
    assert result["path"] is None and result["given"] == "link/image.png"
    assert calls[-1] == str(link)
    assert str(link / "image.png") not in calls


def test_r2_2a_drive_relative_relinks_only_by_plain_name(tmp_path, monkeypatch):
    import studio_result

    base = tmp_path / "project"
    base.mkdir()
    local = base / "foo.png"
    local.write_bytes(b"same")
    digest = hashlib.sha256(b"same").hexdigest()
    calls = []
    real_isfile = os.path.isfile
    real_lstat = os.lstat

    def safe_arg(name, func):
        def watched(path, *args, **kwargs):
            value = os.fspath(path)
            calls.append((name, value))
            assert not value.upper().startswith("D:"), (name, value)
            return func(path, *args, **kwargs)
        return watched

    monkeypatch.setattr(studio_result.os.path, "realpath", safe_arg("realpath", os.path.realpath))
    monkeypatch.setattr(studio_result.os.path, "isfile", safe_arg("isfile", real_isfile))
    monkeypatch.setattr(studio_result.os, "lstat", safe_arg("lstat", real_lstat))
    result = studio_result.resolve_input_ref({"path": r"D:foo.png", "sha256": digest}, str(base))
    assert result["status"] == "relinked" and result["path"] == str(local)
    assert any(value == str(local) for _name, value in calls)


def test_r2_2a_unc_base_needs_confirmation_with_zero_unc_fs_calls(monkeypatch):
    import studio_result

    calls = []

    def watched(name, result=None):
        def inner(path, *args, **kwargs):
            value = os.fspath(path)
            calls.append((name, value))
            assert "server" not in value.lower(), (name, value)
            return result
        return inner

    monkeypatch.setattr(studio_result.os.path, "realpath", watched("realpath", "x"))
    monkeypatch.setattr(studio_result.os.path, "exists", watched("exists", False))
    monkeypatch.setattr(studio_result.os.path, "isfile", watched("isfile", False))
    monkeypatch.setattr(studio_result.os, "stat", watched("stat"))
    monkeypatch.setattr(studio_result.os, "lstat", watched("lstat"))
    result = studio_result.resolve_input_ref(
        {"path": "image.png", "sha256": "x"}, r"\\server\share\project")
    assert result["status"] == "needs_confirmation"
    assert "pipeline folder" in result["reason"]
    assert calls == []


def test_r2_2b_ads_input_never_reaches_filesystem(tmp_path, monkeypatch):
    import studio_result

    calls = []

    def reject(name, result=None):
        def watched(path, *args, **kwargs):
            value = os.fspath(path)
            calls.append((name, value))
            assert "image.png:hidden" not in value, (name, value)
            return result
        return watched

    monkeypatch.setattr(studio_result.os.path, "realpath", reject("realpath", "x"))
    monkeypatch.setattr(studio_result.os.path, "isfile", reject("isfile", False))
    monkeypatch.setattr(studio_result.os, "lstat", reject("lstat"))
    monkeypatch.setattr(studio_result, "file_sha256", reject("sha256", "x"))
    result = studio_result.resolve_input_ref(
        {"path": "image.png:hidden", "sha256": "x"}, str(tmp_path))
    assert result["status"] == "needs_confirmation"
    assert result["path"] is None and result["given"] == "image.png:hidden"
    assert calls == []


def _r2_write_saved_pipeline(image_path, pipe_path, image):
    import imgio
    import studio_result

    imgio.save(str(image_path), image)
    ref = studio_result.input_reference(str(image_path), image)
    pipe_path.write_text(json.dumps({
        "fullseye_pipeline": 1,
        "stages": [["gaussian", 0.3, 0.5]],
        "input": ref,
    }), encoding="utf-8")
    return ref


def test_r2_ux_pending_banner_has_three_visible_actions_and_read_uses_saved_bytes(
        qapp, tmp_path, monkeypatch):
    import numpy as np
    from PySide6 import QtWidgets
    import studio

    folder_a = tmp_path / "a"; folder_b = tmp_path / "b"
    folder_a.mkdir(); folder_b.mkdir()
    image_path = folder_a / "source.png"
    pipe_path = folder_b / "pipeline.json"
    original = np.arange(64, dtype=np.float64).reshape(8, 8) / 63.0
    _r2_write_saved_pipeline(image_path, pipe_path, original)
    real_open = builtins.open
    saved_reads = []

    def watched_open(path, *args, **kwargs):
        if os.path.normcase(os.fspath(path)) == os.path.normcase(str(image_path)):
            saved_reads.append(os.fspath(path))
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", watched_open)
    touched = []                                   # any FS call that names folder A before a choice

    def _watch(owner, attr):
        real = getattr(owner, attr)

        def spy(path, *args, **kwargs):
            if str(folder_a).lower() in os.fspath(path).lower():
                touched.append((attr, os.fspath(path)))
            return real(path, *args, **kwargs)
        monkeypatch.setattr(owner, attr, spy)

    for owner, attr in ((os.path, "realpath"), (os.path, "exists"), (os.path, "isfile"),
                        (os, "stat"), (os, "lstat")):
        _watch(owner, attr)
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    try:
        win.show(); qapp.processEvents()
        win._open_pipe_path(str(pipe_path)); qapp.processEvents()
        assert saved_reads == []
        assert touched == []
        assert win._state["input_pending"]["given"] == str(image_path)
        for name in ("input_confirm_read", "input_confirm_choose", "input_confirm_keep"):
            button = win.findChild(QtWidgets.QPushButton, name)
            assert button is not None and button.isVisible()
        assert "not loaded" in win._current_view().notice_text().lower()
        win._input_confirm["read"](); qapp.processEvents()
        assert len(saved_reads) == 1
        assert np.allclose(model.image, original, atol=1.0 / 255.0)
        assert win._state.get("input_pending") is None
    finally:
        _close_window(win)


def test_r2_ux_read_changed_requires_held_bytes_adoption(qapp, tmp_path, monkeypatch):
    import numpy as np
    from PySide6 import QtWidgets
    import imgio
    import studio

    image_path = tmp_path / "elsewhere" / "source.png"
    image_path.parent.mkdir()
    pipe_path = tmp_path / "pipeline.json"
    _r2_write_saved_pipeline(image_path, pipe_path, np.zeros((6, 6), np.float64))
    changed = np.ones((6, 6), np.float64)
    imgio.save(str(image_path), changed)
    real_open = builtins.open
    image_reads = []

    def watched_open(path, *args, **kwargs):
        if os.path.normcase(os.fspath(path)) == os.path.normcase(str(image_path)):
            image_reads.append(os.fspath(path))
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", watched_open)
    current = studio.demo_image(16)
    win, model = studio.build_window(studio.PipelineModel(current.copy()))
    try:
        win.show(); qapp.processEvents()
        win._open_pipe_path(str(pipe_path))
        assert win._state.get("input_pending")          # the button, not an automatic relink, reads it
        assert win._input_confirm["read"]() is False
        qapp.processEvents()
        assert len(image_reads) == 1
        assert np.array_equal(model.image, current)
        pending = win._state.get("input_pending")
        assert pending and pending["held"]["path"] == str(image_path)
        assert pending["held"]["sha256"] == hashlib.sha256(pending["held"]["data"]).hexdigest()
        differs = "differs from the one saved with the pipeline"
        banner = win.findChild(QtWidgets.QFrame, "input_confirm_bar")
        assert differs in " ".join(label.text() for label in banner.findChildren(QtWidgets.QLabel))
        assert differs in win._current_view().notice_text()
        assert any(differs in note for note in win._state["input_notes"])
        adopt = win.findChild(QtWidgets.QPushButton, "input_confirm_adopt")
        assert adopt is not None and adopt.isVisible()

        assert win._input_confirm["adopt"]() is True
        assert len(image_reads) == 1                       # 初回保持バイトを復号。Decode first-action bytes.
        assert np.allclose(model.image, changed)
        assert win._state.get("input_pending") is None
        assert any(differs in note for note in win._state["input_notes"])
    finally:
        _close_window(win)


def test_r3_ux_keep_current_after_mismatch_drops_held_bytes(qapp, tmp_path):
    import numpy as np
    import imgio
    import studio

    image_path = tmp_path / "elsewhere" / "source.png"
    image_path.parent.mkdir()
    pipe_path = tmp_path / "pipeline.json"
    ref = _r2_write_saved_pipeline(image_path, pipe_path, np.zeros((6, 6), np.float64))
    imgio.save(str(image_path), np.ones((6, 6), np.float64))
    current = studio.demo_image(16)
    win, model = studio.build_window(studio.PipelineModel(current.copy()))
    try:
        win._open_pipe_path(str(pipe_path))
        assert win._input_confirm["read"]() is False
        assert win._state["input_pending"]["held"]["data"]
        assert win._input_confirm["keep"]() is True
        assert np.array_equal(model.image, current)
        assert win._state.get("input_pending") is None
        assert model.kept_input_ref == ref
    finally:
        _close_window(win)


def test_r2_ux_keep_current_clears_pending_but_keeps_visible_note(qapp, tmp_path):
    import numpy as np
    import studio

    image_path = tmp_path / "elsewhere" / "source.png"
    image_path.parent.mkdir()
    pipe_path = tmp_path / "pipeline.json"
    _r2_write_saved_pipeline(image_path, pipe_path, np.zeros((6, 6), np.float64))
    current = np.full((7, 7), 0.25, np.float64)
    win, model = studio.build_window(studio.PipelineModel(current.copy()))
    try:
        win._open_pipe_path(str(pipe_path))
        win._input_confirm["keep"]()
        assert np.array_equal(model.image, current)
        assert win._state.get("input_pending") is None
        assert any("current image" in note.lower() for note in win._state["input_notes"])
        assert "current image" in win._current_view().notice_text().lower()
    finally:
        _close_window(win)


def test_r2_ux_choose_another_image_clears_pending(qapp, tmp_path, monkeypatch):
    import numpy as np
    from PySide6 import QtWidgets
    import studio

    saved = tmp_path / "saved" / "source.png"
    saved.parent.mkdir()
    chosen = tmp_path / "chosen.png"
    pipe_path = tmp_path / "pipeline.json"
    _r2_write_saved_pipeline(saved, pipe_path, np.zeros((6, 6), np.float64))
    wanted = np.full((6, 6), 0.75, np.float64)
    import imgio
    imgio.save(str(chosen), wanted)
    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName",
                        lambda *_a, **_k: (str(chosen), "Images"))
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    try:
        win._open_pipe_path(str(pipe_path))
        win._input_confirm["choose"]()
        assert win._state.get("input_pending") is None
        assert np.allclose(model.image, wanted, atol=1.0 / 255.0)
    finally:
        _close_window(win)


def _r3_save_pipeline(win, path, monkeypatch):
    from PySide6 import QtWidgets

    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *_a, **_k: (str(path), "JSON")))
    win._actions["save_pipeline"].trigger()
    return json.loads(path.read_text(encoding="utf-8"))


def test_r3_keep_demo_preserves_saved_input_reference_on_save(qapp, tmp_path, monkeypatch):
    import numpy as np
    import studio

    saved = tmp_path / "saved" / "source.png"
    saved.parent.mkdir()
    pipe_path = tmp_path / "pipeline.json"
    out = tmp_path / "kept-demo.json"
    ref = _r2_write_saved_pipeline(saved, pipe_path, np.zeros((6, 6), np.float64))
    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    try:
        win._actions["demo"].trigger()
        win._open_pipe_path(str(pipe_path))
        assert win._state["dirty"] is False
        assert win._input_confirm["keep"]() is True
        assert win._state["dirty"] is False
        assert _r3_save_pipeline(win, out, monkeypatch)["input"] == ref
    finally:
        _close_window(win)


def test_r3_keep_current_file_preserves_saved_input_reference_on_save(qapp, tmp_path, monkeypatch):
    import numpy as np
    import imgio
    import studio

    current_path = tmp_path / "current-a.png"
    saved = tmp_path / "saved" / "source-b.png"
    saved.parent.mkdir()
    pipe_path = tmp_path / "pipeline.json"
    out = tmp_path / "kept-file.json"
    imgio.save(str(current_path), np.ones((7, 7), np.float64))
    ref = _r2_write_saved_pipeline(saved, pipe_path, np.zeros((6, 6), np.float64))
    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    try:
        assert win._load_image_path(str(current_path)) is True
        win._open_pipe_path(str(pipe_path))
        assert win._input_confirm["keep"]() is True
        assert _r3_save_pipeline(win, out, monkeypatch)["input"] == ref
    finally:
        _close_window(win)


def test_r3_explicit_image_choice_after_keep_replaces_saved_reference(qapp, tmp_path, monkeypatch):
    import numpy as np
    from PySide6 import QtWidgets
    import imgio
    import studio

    saved = tmp_path / "saved" / "source-b.png"
    saved.parent.mkdir()
    chosen = tmp_path / "chosen.png"
    pipe_path = tmp_path / "pipeline.json"
    out = tmp_path / "chosen-pipeline.json"
    ref = _r2_write_saved_pipeline(saved, pipe_path, np.zeros((6, 6), np.float64))
    imgio.save(str(chosen), np.full((6, 6), 0.75, np.float64))
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    try:
        win._open_pipe_path(str(pipe_path))
        assert win._input_confirm["keep"]() is True
        assert model.kept_input_ref == ref
        monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName",
                            staticmethod(lambda *_a, **_k: (str(chosen), "Images")))
        assert win._input_confirm["choose"]() is True
        saved_data = _r3_save_pipeline(win, out, monkeypatch)
        assert saved_data["input"]["path"] == str(chosen)
        assert saved_data["input"] != ref
        assert model.kept_input_ref is None
    finally:
        _close_window(win)


def test_r2_ux_read_falls_back_to_the_path_loader_and_rehashes(qapp, tmp_path, monkeypatch):
    """バイト列から復号できない形式(16 bit・浮動小数の TIFF など)も「この画像を読む」で読める。"""
    import numpy as np
    import imgio
    import studio

    image_path = tmp_path / "elsewhere" / "source.png"
    image_path.parent.mkdir()
    pipe_path = tmp_path / "pipeline.json"
    original = np.arange(36, dtype=np.float64).reshape(6, 6) / 35.0
    _r2_write_saved_pipeline(image_path, pipe_path, original)

    def cannot_decode(*_a, **_k):
        raise ValueError("format not decodable from bytes")

    monkeypatch.setattr(imgio, "_load_bytes", cannot_decode)
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    try:
        win._open_pipe_path(str(pipe_path))
        assert win._input_confirm["read"]() is True
        assert np.allclose(model.image, original, atol=1.0 / 255.0)
        assert win._state.get("input_pending") is None
    finally:
        _close_window(win)


def test_r2_ux_read_refuses_a_file_swapped_while_loading(qapp, tmp_path, monkeypatch):
    """予備の読み手で読む間にファイルが差し替わったら読まず、確認待ちのまま理由を出す。"""
    import numpy as np
    import imgio
    import studio

    image_path = tmp_path / "elsewhere" / "source.png"
    image_path.parent.mkdir()
    pipe_path = tmp_path / "pipeline.json"
    _r2_write_saved_pipeline(image_path, pipe_path, np.zeros((6, 6), np.float64))
    real_load = imgio.load

    def cannot_decode(*_a, **_k):
        raise ValueError("format not decodable from bytes")

    def swapping_load(path, *a, **k):
        arr = real_load(path, *a, **k)
        imgio.save(str(image_path), np.ones((6, 6), np.float64))      # replaced after the user's check
        return arr

    monkeypatch.setattr(imgio, "_load_bytes", cannot_decode)
    monkeypatch.setattr(imgio, "load", swapping_load)
    keep = studio.demo_image(16)
    win, model = studio.build_window(studio.PipelineModel(keep.copy()))
    try:
        win._open_pipe_path(str(pipe_path))
        assert win._input_confirm["read"]() is False
        assert win._state.get("input_pending")
        assert any("changed while it was being read" in n for n in win._state["input_notes"])
        assert np.array_equal(model.image, keep)
    finally:
        _close_window(win)

