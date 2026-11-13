# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""パラメータの束を並べて見る・直す窓(``studio_params_model`` / ``studio_params_qt``)の試験。

前半はモデル(Qt なし): 3 形式の読み書きの往復で値と型が変わらない・差の判定・絞り込み・写す・編集の型の検査・
Undo / Redo・原子的な保存(途中で落ちても元のファイルが残る)・外での変更の検出・壊れた入力の拒否(全種を数える)。
後半は窓(offscreen): 開く・編集・保存・未保存の確認・違う行だけ・検索・6 言語で文字が切れない・設定は一時の ini。
"""
from __future__ import annotations

import ast
import io
import json
import os
import re

import pytest

yaml = pytest.importorskip("yaml")

import studio_params_model as M  # noqa: E402
from fullseye import parambundle  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: 3 形式で同じ中身にする葉(読み手で型が化けやすい文字列を含める)。
TRICKY = {
    "camera.fx": 812.5, "camera.cx": 320, "camera.neg": -7, "camera.big": 12345678901234567890,
    "camera.size": (640, 480), "camera.grid": ((1, 2), (3, 4)), "camera.tags": ("left", "NO", "010"),
    "optics.wavelength": "550 nm", "optics.pixel_pitch": "3.45 um", "optics.f_number": 2.8,
    "optics.tiny": 1e-07, "optics.huge": 1e+20,
    "exposure.auto": True, "exposure.bracket": False, "exposure.mode": "global",
    "text.no": "NO", "text.octal": "010", "text.octal12": "0o10", "text.truthy": "true", "text.clock": "12:30:00",
    "text.padded": " padded ", "text.empty": "", "text.ja": "日本語の値", "text.colon": "a: b", "text.hash": "#hash",
    "text.lines": "a\nb", "text.number": "42", "text.amp": "a < b & c",
}
KINDS = {"camera.fx": "float", "camera.cx": "int", "camera.neg": "int", "camera.big": "int", "camera.size": "list",
         "camera.grid": "list", "camera.tags": "list", "optics.wavelength": "quantity", "optics.pixel_pitch": "quantity",
         "optics.f_number": "float", "optics.tiny": "float", "optics.huge": "float", "exposure.auto": "bool",
         "exposure.bracket": "bool", "exposure.mode": "str", "text.no": "str", "text.octal": "str", "text.octal12": "str",
         "text.truthy": "str", "text.clock": "str", "text.padded": "str", "text.empty": "str", "text.ja": "str",
         "text.colon": "str", "text.hash": "str", "text.lines": "str", "text.number": "str", "text.amp": "str"}
WRITABLE_EXTS = (".json", ".yaml", ".xml")


def _leaves(data: dict) -> dict:
    b = parambundle.ParamBundle(data)
    return {k: b[k] for k in b}


def _write(tmp_path, name: str, data: dict | None = None) -> str:
    """``data`` を ``name`` の拡張子の形式で書く(モデルの書き手ではなく本文を直接置く)。"""
    p = str(tmp_path / name)
    text = M.bundle_text(_leaves(TRICKY if data is None else data), M.FORMATS[os.path.splitext(name)[1]])
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return p


def _raw(tmp_path, name: str, text: str | bytes) -> str:
    p = str(tmp_path / name)
    with open(p, "wb") as fh:
        fh.write(text if isinstance(text, bytes) else text.encode("utf-8"))
    return p


DAY = {"camera": {"fx": 812.5, "fy": 812.5, "cx": 320, "size": [640, 480]},
       "optics": {"wavelength": "550 nm", "f_number": 2.8},
       "exposure": {"auto": True, "mode": "global"}}
NIGHT = {"camera": {"fx": 812.5, "fy": 812.5, "cx": 320, "size": [640, 480]},
         "optics": {"wavelength": "0.55 um", "f_number": 1.4},
         "exposure": {"auto": False, "mode": "global", "gain_db": 12}}
LAB = {"camera": {"fx": 815.0, "fy": 812.5, "cx": 320, "size": [640, 480]},
       "optics": {"wavelength": "550 nm", "f_number": 2.8},
       "exposure": {"auto": True, "mode": "rolling"}}


def _three(tmp_path) -> tuple[M.ParamsModel, list[str]]:
    paths = [_write(tmp_path, "day.json", DAY), _write(tmp_path, "night.yaml", NIGHT), _write(tmp_path, "lab.xml", LAB)]
    m = M.ParamsModel()
    outs = [m.add_file(p) for p in paths]
    assert [o.ok for o in outs] == [True, True, True], [o.reason for o in outs]
    return m, paths


# ============================================================================================== #
# モデル: 読む・書く
# ============================================================================================== #
def test_three_formats_read_the_same_values_and_types(tmp_path):
    """同じ中身の JSON / YAML / XML を読むと、28 個の葉が値も型も一致する(型は表のとおり)。"""
    m = M.ParamsModel()
    for ext in WRITABLE_EXTS:
        out = m.add_file(_write(tmp_path, "tricky" + ext))
        assert out.ok, out.reason
    assert len(m.columns) == 3
    want = _leaves(TRICKY)
    assert len(want) == 28 == len(KINDS)
    checked = 0
    for col in m.columns:
        assert list(col.leaves) == list(want), col.name
        for k, v in want.items():
            assert M.same_value(col.leaves[k], v), (col.name, k, col.leaves[k], v)
            assert M.kind_of(col.leaves[k]) == KINDS[k], (col.name, k)
            checked += 1
    assert checked == 84
    c = m.counts()
    assert (c["rows"], c["differ"], c["partial"], c["dirty"]) == (28, 0, 0, 0)


@pytest.mark.parametrize("ext", WRITABLE_EXTS)
def test_edit_save_reread_keeps_values_and_types(tmp_path, ext):
    """直して保存し、別のモデルで読み直す: 直した 1 個だけが変わり、残り 27 個は値も型もそのまま。形式も元のまま。"""
    p = _write(tmp_path, "tricky" + ext)
    m = M.ParamsModel()
    assert m.add_file(p).ok
    assert m.set_value(0, "camera.fx", "820.25").ok
    out = m.save(0)
    assert out.ok, out.reason
    assert out.code == "save.done" and out.path == os.path.abspath(p)
    assert not m.is_dirty()
    head = open(p, "rb").read(64)
    marker = {".json": b"{", ".yaml": b"camera:", ".xml": b"<?xml"}[ext]
    assert head.startswith(marker), head
    m2 = M.ParamsModel()
    assert m2.add_file(p).ok
    got, want = m2.columns[0].leaves, dict(_leaves(TRICKY))
    want["camera.fx"] = 820.25
    assert set(got) == set(want) and len(got) == 28
    same = [k for k in want if M.same_value(got[k], want[k]) and M.kind_of(got[k]) == KINDS[k]]
    assert len(same) == 28, sorted(set(want) - set(same))


@pytest.mark.parametrize("src,dst", [(".json", ".yaml"), (".json", ".xml"), (".yaml", ".xml"), (".xml", ".json"),
                                     (".xml", ".yaml"), (".yaml", ".json")])
def test_save_as_another_format_keeps_values_and_types(tmp_path, src, dst):
    """形式を変えて「名前を付けて保存」しても 28 個の葉の値と型は同じ。列は新しいファイルを指す。"""
    m = M.ParamsModel()
    assert m.add_file(_write(tmp_path, "a" + src)).ok
    target = str(tmp_path / ("b" + dst))
    out = m.save_as(0, target)
    assert out.ok, out.reason
    assert ("loss.convert", (M.FORMATS[dst].upper(), M.FORMATS[src].upper())) in out.notes
    assert m.columns[0].path == os.path.abspath(target) and m.columns[0].fmt == M.FORMATS[dst]
    back = M.read_bundle(target)
    want = _leaves(TRICKY)
    assert len(back) == 28
    same = [k for k in want if M.same_value(back[k], want[k])]
    assert len(same) == 28, sorted(set(want) - set(same))


def test_toml_is_read_but_not_written(tmp_path):
    """TOML は読める・比べられるが、編集と上書きは理由つきで断る。別の形式へは書ける。"""
    p = _raw(tmp_path, "rig.toml", '# comment\n[camera]\nfx = 812.5\ncx = 320\n\n[optics]\nwavelength = "550 nm"\n')
    m = M.ParamsModel()
    assert m.add_file(p).ok
    col = m.columns[0]
    assert col.fmt == "toml" and not col.writable and col.comments == 1
    assert M.same_value(col.leaves["camera.fx"], 812.5) and M.kind_of(col.leaves["optics.wavelength"]) == "quantity"
    out = m.set_value(0, "camera.fx", "820")
    assert not out.ok and out.code == "edit.readonly" and "Save As" in out.reason
    before = open(p, "rb").read()
    out = m.save(0)
    assert not out.ok and out.code == "save.format"
    assert open(p, "rb").read() == before
    target = str(tmp_path / "rig.json")
    out = m.save_as(0, target)
    assert not out.ok and out.needs_confirm and ("loss.comments", (1,)) in out.notes     # コメントが失われるので聞く
    assert not os.path.exists(target)
    out = m.save_as(0, target, accept_losses=True)
    assert out.ok and m.columns[0].writable
    assert json.load(open(target, encoding="utf-8")) == {"camera": {"fx": 812.5, "cx": 320}, "optics": {"wavelength": "550 nm"}}
    assert m.set_value(0, "camera.fx", "820").ok


def test_xml_grammar_typed_and_inferred(tmp_path):
    """XML: type つきはその型、type なしの手書きは true / false・整数・小数・それ以外は文字。封筒の印も読む。"""
    p = _raw(tmp_path, "hand.xml", """<?xml version="1.0" encoding="UTF-8"?>
<params fullseye_kind="params" version="1">
  <section name="camera">
    <param name="fx">812.5</param>
    <param name="cx">320</param>
    <param name="on">true</param>
    <param name="mode"> global </param>
    <param name="size"><item>640</item><item>480</item></param>
    <param name="wavelength">550 nm</param>
    <param name="label" type="str"> kept </param>
    <param name="ratio" type="float">2</param>
  </section>
</params>
""")
    b = M.read_bundle(p)
    got = {k: (M.kind_of(b[k]), M.format_value(b[k])) for k in b}
    assert got == {"camera.fx": ("float", "812.5"), "camera.cx": ("int", "320"), "camera.on": ("bool", "true"),
                   "camera.mode": ("str", "global"), "camera.size": ("list", "[640, 480]"),
                   "camera.wavelength": ("quantity", "550 nm"), "camera.label": ("str", " kept "),
                   "camera.ratio": ("float", "2.0")}


# ============================================================================================== #
# モデル: 比べる・絞る・木
# ============================================================================================== #
def test_compare_statuses_and_counts(tmp_path):
    """3 つの束: 違う行 4、片方に無い行 1、書き方だけ違う行 1、残りは同じ。"""
    m, _ = _three(tmp_path)
    rows = {r.key: r for r in m.rows()}
    assert len(rows) == 9
    status = {k: r.status for k, r in rows.items()}
    assert status == {"camera.fx": "differ", "camera.fy": "same", "camera.cx": "same", "camera.size": "same",
                      "optics.wavelength": "same", "optics.f_number": "differ", "exposure.auto": "differ",
                      "exposure.mode": "differ", "exposure.gain_db": "partial"}
    assert [k for k, r in rows.items() if r.notation_differs] == ["optics.wavelength"]
    assert rows["exposure.gain_db"].values == (None, 12, None)
    assert m.counts() == {"columns": 3, "rows": 9, "differ": 4, "partial": 1, "dirty": 0}


def test_diff_only_and_key_search(tmp_path):
    """「違う行だけ」は違う行と片方に無い行、検索はキーの部分一致(大文字小文字を問わない)。組み合わせられる。"""
    m, _ = _three(tmp_path)
    assert [r.key for r in m.rows(diff_only=True)] == ["camera.fx", "optics.f_number", "exposure.auto", "exposure.mode",
                                                       "exposure.gain_db"]
    assert [r.key for r in m.rows(query="CAMERA")] == ["camera.fx", "camera.fy", "camera.cx", "camera.size"]
    assert [r.key for r in m.rows(query="f")] == ["camera.fx", "camera.fy", "optics.f_number"]
    assert [r.key for r in m.rows(diff_only=True, query="exposure")] == ["exposure.auto", "exposure.mode", "exposure.gain_db"]
    assert m.rows(query="no-such-key") == []


def test_tree_follows_key_hierarchy(tmp_path):
    """木: 節 3 つ、その下に葉。節は配下の違う行・片方に無い行の数を持つ。深い階層も節になる。"""
    m, _ = _three(tmp_path)
    top = m.tree()
    assert [(n.label, n.row is None, len(n.children), n.differ, n.partial) for n in top] == [
        ("camera", True, 4, 1, 0), ("optics", True, 2, 1, 0), ("exposure", True, 3, 2, 1)]
    assert [c.key for c in top[2].children] == ["exposure.auto", "exposure.mode", "exposure.gain_db"]
    assert [n.label for n in m.tree(diff_only=True, query="optics")] == ["optics"]
    deep = M.ParamsModel()
    assert deep.add_bundle({"a": {"b": {"c": 1, "d": 2}}, "top": 3}, "deep").ok
    t = deep.tree()
    assert [(n.key, len(n.children)) for n in t] == [("a", 1), ("top", 0)]
    assert t[0].children[0].key == "a.b" and [x.key for x in t[0].children[0].children] == ["a.b.c", "a.b.d"]


# ============================================================================================== #
# モデル: 直す
# ============================================================================================== #
EDIT_CASES = [
    # (キー, 入れる文字, 通るか, 断る理由の code か None, 通った後の (型, 文字))
    ("camera.fx", "820", True, None, ("float", "820.0")),
    ("camera.fx", " 8.2e2 ", True, None, ("float", "820.0")),
    ("camera.fx", "fast", False, "edit.number", None),
    ("camera.fx", "", False, "edit.number", None),
    ("camera.fx", "5 mm", False, "edit.number_unit", None),
    ("camera.fx", "nan", False, "edit.number", None),
    ("camera.fx", "1e999", False, "edit.number", None),
    ("camera.fx", "__import__('os').system('echo x')", False, "edit.number", None),
    ("camera.fx", "1+1", False, "edit.number", None),
    ("camera.fx", "True", False, "edit.number", None),
    ("camera.cx", "321", True, None, ("int", "321")),
    ("camera.cx", "321.5", True, None, ("float", "321.5")),
    ("camera.cx", "0x10", False, "edit.number", None),
    ("optics.wavelength", "600 nm", True, None, ("quantity", "600 nm")),
    ("optics.wavelength", "0.6 um", True, None, ("quantity", "0.6 um")),
    ("optics.wavelength", "600", False, "edit.quantity", None),
    ("optics.wavelength", "5 ms", False, "edit.dimension", None),
    ("optics.wavelength", "red", False, "edit.quantity", None),
    ("exposure.mode", "rolling", True, None, ("str", "rolling")),
    ("exposure.mode", "42", True, None, ("str", "42")),
    ("exposure.mode", "550 nm", False, "edit.str_quantity", None),
    ("exposure.auto", "false", True, None, ("bool", "false")),
    ("exposure.auto", "FALSE", True, None, ("bool", "false")),
    ("exposure.auto", "maybe", False, "edit.bool", None),
    ("exposure.auto", "0", False, "edit.bool", None),
    ("camera.size", "[800, 600]", True, None, ("list", "[800, 600]")),
    ("camera.size", "(1024, 768, 3)", True, None, ("list", "[1024, 768, 3]")),
    ("camera.size", "[1, \"a\"]", False, "edit.list_kind", None),
    ("camera.size", "640", False, "edit.list", None),
    ("camera.size", "[1, {\"a\": 1}]", False, "edit.list", None),
    ("camera.size", "[1, null]", False, "edit.list", None),
    ("camera.size", "[1, NaN]", False, "edit.list", None),
    ("camera.size", "__import__('os').listdir('.')", False, "edit.list", None),
    ("camera.size", "[i for i in range(3)]", False, "edit.list", None),
    ("camera.nope", "1", False, "edit.no_key", None),
]


def test_edit_cases_are_all_distinct_and_counted():
    """編集の表は 35 件。断る理由は 9 種類を全部踏む。"""
    assert len(EDIT_CASES) == 35
    codes = {c[3] for c in EDIT_CASES if c[3]}
    assert codes == {"edit.number", "edit.number_unit", "edit.quantity", "edit.dimension", "edit.str_quantity",
                     "edit.bool", "edit.list", "edit.list_kind", "edit.no_key"}
    assert sum(1 for c in EDIT_CASES if c[2]) == 12


@pytest.mark.parametrize("key,text,ok,code,after", EDIT_CASES)
def test_edit_keeps_the_type_or_refuses_with_a_reason(tmp_path, key, text, ok, code, after):
    """型を保って直す。保てなければ断り、値・未保存の印・履歴は変わらない。理由の文に入れた文字が入る。"""
    m = M.ParamsModel()
    assert m.add_file(_write(tmp_path, "day.json", DAY)).ok
    before = dict(m.columns[0].leaves)
    out = m.set_value(0, key, text)
    assert out.ok is ok, out.reason
    if ok:
        v = m.value(0, key)
        assert (M.kind_of(v), M.format_value(v)) == after
        assert m.is_dirty() and m.can_undo()
    else:
        assert out.code == code
        assert key in out.reason and len(out.reason) > len(key) + 10
        assert m.columns[0].leaves == before and not m.is_dirty() and not m.can_undo()


def test_type_change_inside_numbers_is_noted(tmp_path):
    """整数の欄に小数を入れると小数になり、そのことを注意で返す(黙って変えない)。同じ値は「変わっていない」。"""
    m = M.ParamsModel()
    assert m.add_file(_write(tmp_path, "day.json", DAY)).ok
    out = m.set_value(0, "camera.cx", "320.5")
    assert out.ok and out.notes == (("note.type_changed", ("camera.cx", "int", "float")),)
    assert out.note_texts() == ["camera.cx: the type changed from int to float"]
    out = m.set_value(0, "camera.fx", "812.5")
    assert not out.ok and out.code == "edit.same"
    out = m.set_raw(0, "exposure.auto", "yes")
    assert not out.ok and "type would change from bool to str" in out.reason
    out = m.set_raw(0, "exposure.auto", False)
    assert out.ok and m.value(0, "exposure.auto") is False


def test_source_has_no_eval_exec_pickle_or_unsafe_yaml():
    """2 つのモジュールは eval / exec / pickle / 安全でない YAML の読み手を使わない(構文木で数える)。"""
    seen = 0
    for name in ("studio_params_model.py", "studio_params_qt.py"):
        src = io.open(os.path.join(ROOT, name), encoding="utf-8").read()
        tree = ast.parse(src)
        calls = [n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        yaml_calls = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                      and isinstance(n.func.value, ast.Name) and n.func.value.id == "yaml"}
        imports = [a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names]
        assert len(calls) > 20 and len(imports) > 3
        assert not {"eval", "exec", "compile", "__import__"} & set(calls), name
        assert yaml_calls <= {"scan", "dump"}, (name, yaml_calls)       # 読むのは parambundle の safe な読み手だけ
        assert not {"pickle", "marshal", "shelve"} & set(imports), name
        seen += 1
    assert seen == 2


# ============================================================================================== #
# モデル: 写す・Undo / Redo
# ============================================================================================== #
def test_copy_between_columns_and_undo(tmp_path):
    """値を列から列へ写す: 違う値は置き換え、無いキーは足し(注意つき)、無い値・同じ値は断る。Undo で戻る。"""
    m, _ = _three(tmp_path)
    out = m.copy_value("optics.f_number", 0, 1)
    assert out.ok and out.notes == () and m.value(1, "optics.f_number") == 2.8
    assert m.row("optics.f_number").status == "same" and m.counts()["differ"] == 3
    out = m.copy_value("exposure.gain_db", 1, 0)
    assert out.ok and out.notes == (("note.key_added", ("exposure.gain_db", "day.json")),)
    assert m.value(0, "exposure.gain_db") == 12 and m.row("exposure.gain_db").values == (12, 12, None)
    assert (m.copy_value("exposure.gain_db", 2, 0).code, m.copy_value("camera.fy", 0, 1).code) == ("copy.missing", "copy.same")
    assert m.undo().ok and m.value(0, "exposure.gain_db") is None and "exposure.gain_db" not in m.columns[0].leaves
    assert m.undo().ok and m.value(1, "optics.f_number") == 1.4
    assert not m.is_dirty() and not m.can_undo() and m.counts()["differ"] == 4
    out = m.undo()
    assert not out.ok and out.code == "undo.empty"


def test_copy_column_is_one_undo_step(tmp_path):
    """違う値を全部まとめて写す(4 個)。1 回の Undo で 4 個とも戻る。違いが無ければ断る。"""
    m, _ = _three(tmp_path)
    out = m.copy_column(1, 0)
    assert out.ok and out.count == 4, out.reason           # f_number, auto, gain_db(足す), wavelength(書き方)
    assert [r.key for r in m.rows(diff_only=True)] == ["camera.fx", "optics.f_number", "exposure.auto", "exposure.mode",
                                                       "exposure.gain_db"]
    assert M.format_value(m.value(0, "optics.wavelength")) == "0.55 um"
    assert m.copy_column(1, 0).code == "copy.nothing"
    out = m.undo()
    assert out.ok and out.count == 4 and out.reason == "copy 4 value(s) to day.json"
    assert not m.is_dirty() and M.format_value(m.value(0, "optics.wavelength")) == "550 nm"
    assert m.value(0, "exposure.gain_db") is None


def test_undo_redo_history(tmp_path):
    """編集 3 回 → Undo 2 回 → Redo 1 回 → 新しい編集で Redo の枝が消える。全部戻すと未保存の印も消える。"""
    m = M.ParamsModel()
    assert m.add_file(_write(tmp_path, "day.json", DAY)).ok
    for text in ("820", "830", "840"):
        assert m.set_value(0, "camera.fx", text).ok
    assert m.value(0, "camera.fx") == 840.0 and not m.can_redo()
    assert m.undo().reason == "edit camera.fx" and m.undo().ok
    assert m.value(0, "camera.fx") == 820.0 and m.can_redo()
    assert m.redo().ok and m.value(0, "camera.fx") == 830.0
    assert m.set_value(0, "camera.cx", "100").ok and not m.can_redo()
    assert m.redo().code == "redo.empty"
    steps = 0
    while m.can_undo():
        assert m.undo().ok
        steps += 1
    assert steps == 3 and not m.is_dirty()
    assert m.value(0, "camera.fx") == 812.5 and m.value(0, "camera.cx") == 320
    assert m.redo().ok and m.is_dirty() and m.columns[0].cell_dirty("camera.fx") and not m.columns[0].cell_dirty("camera.cx")


def test_a_copy_that_breaks_the_bundle_layout_is_refused(tmp_path):
    """片方では値、もう片方では節になっているキーを写すと、束の門(値と節の衝突)が断る。何も変わらない。"""
    m = M.ParamsModel()
    assert m.add_bundle({"a": 1, "b": 2}, "flat").ok and m.add_bundle({"a": {"x": 1}, "b": 2}, "nested").ok
    out = m.copy_value("a", 0, 1)
    assert not out.ok and out.code == "edit.gate" and "both a value and a section" in out.reason
    assert list(m.columns[1].leaves) == ["a.x", "b"] and not m.is_dirty() and not m.can_undo()


# ============================================================================================== #
# モデル: 原子的な保存・失われる物・外での変更
# ============================================================================================== #
def _no_temp_left(folder) -> bool:
    return not [n for n in os.listdir(folder) if n.startswith(".params-")]


@pytest.mark.parametrize("ext", WRITABLE_EXTS)
def test_save_is_atomic_when_the_last_step_fails(tmp_path, monkeypatch, ext):
    """最後の置き換えで落ちても、元のファイルは 1 バイトも変わらず、一時ファイルも残らない。列は未保存のまま。"""
    p = _write(tmp_path, "rig" + ext, DAY)
    m = M.ParamsModel()
    assert m.add_file(p).ok and m.set_value(0, "camera.fx", "999").ok
    before = open(p, "rb").read()
    real = os.replace
    hits = []

    def boom(src, dst, *a, **k):
        if os.path.normcase(os.path.abspath(dst)) == os.path.normcase(os.path.abspath(p)):
            hits.append(src)
            raise OSError("disk full (test)")
        return real(src, dst, *a, **k)

    monkeypatch.setattr(os, "replace", boom)
    out = m.save(0)
    assert len(hits) == 1
    assert not out.ok and out.code == "save.failed" and "disk full (test)" in out.reason and "unchanged" in out.reason
    assert open(p, "rb").read() == before
    assert _no_temp_left(tmp_path) and m.is_dirty(0)
    monkeypatch.setattr(os, "replace", real)
    assert m.save(0).ok and open(p, "rb").read() != before and not m.is_dirty(0) and _no_temp_left(tmp_path)


def test_save_verifies_by_reading_back(tmp_path):
    """書いた物を読み直して同じにならない値(XML が改行を畳む \\r)は、置き換える前に断る。元のファイルは残る。"""
    p = _write(tmp_path, "rig.xml", DAY)
    m = M.ParamsModel()
    assert m.add_file(p).ok
    before = open(p, "rb").read()
    assert m.set_raw(0, "exposure.mode", "a\rb").ok
    out = m.save(0)
    assert not out.ok and out.code == "save.verify" and out.args == ("rig.xml", "exposure.mode")
    assert open(p, "rb").read() == before and _no_temp_left(tmp_path) and m.is_dirty(0)
    assert m.set_raw(0, "exposure.mode", "a\x01b").ok           # XML に書けない制御文字
    out = m.save(0)
    assert not out.ok and out.code in ("save.failed", "save.verify")
    assert open(p, "rb").read() == before and _no_temp_left(tmp_path)
    target = str(tmp_path / "rig.json")                          # JSON なら書ける
    assert m.save_as(0, target).ok and M.read_bundle(target)["exposure.mode"] == "a\x01b"


def test_losses_are_told_before_saving(tmp_path):
    """コメント・アンカー・include・参照は、書く前に「失われる」と返して止まる。承知すれば書き、以後は失う物が無い。"""
    y = _raw(tmp_path, "rig.yaml", "# rig\nbase: &b 3\ncamera:\n  fx: 812.5  # px\n  copy: *b\n")
    _raw(tmp_path, "base.json", json.dumps({"camera": {"fy": 800.0}}))
    j = _raw(tmp_path, "main.json", json.dumps({"include": ["base.json"], "camera": {"fx": 812.5, "same": {"$param": "camera.fx"}}}))
    x = _raw(tmp_path, "rig.xml", "<params><!-- note --><param name=\"fx\" type=\"float\">812.5</param></params>")
    m = M.ParamsModel()
    assert [m.add_file(p).ok for p in (y, j, x)] == [True, True, True]
    want = [{"loss.comments": (2,), "loss.anchors": (2,), "loss.layout": ()},
            {"loss.include": ("base.json",), "loss.refs": (1,), "loss.layout": ()},
            {"loss.comments": (1,), "loss.layout": ()}]
    stopped = 0
    for i, p in enumerate((y, j, x)):
        assert {c: a for c, a, _ in m.save_losses(i)} == want[i], i
        before = open(p, "rb").read()
        out = m.save(i)
        assert not out.ok and out.needs_confirm and out.code == "save.confirm" and dict(out.notes) == want[i]
        assert open(p, "rb").read() == before
        stopped += 1
        out = m.save(i, accept_losses=True)
        assert out.ok, out.reason
        assert [c for c, _, _ in m.save_losses(i)] == ["loss.layout"]
        assert m.save(i).ok                                      # 2 回目からは聞かない
    assert stopped == 3
    assert b"#" not in open(y, "rb").read() and b"include" not in open(j, "rb").read() and b"<!--" not in open(x, "rb").read()
    assert M.read_bundle(j).to_dict() == {"camera": {"fy": 800.0, "fx": 812.5, "same": 812.5}}
    assert M.read_bundle(y).to_dict() == {"base": 3, "camera": {"fx": 812.5, "copy": 3}}


def test_external_change_is_detected_by_time_and_hash(tmp_path):
    """外での変更: 更新時刻だけ変わって中身が同じなら変更なし、中身が変われば changed、消えれば missing。保存は止まる。"""
    p = _write(tmp_path, "day.json", DAY)
    m = M.ParamsModel()
    assert m.add_file(p).ok
    assert m.check_external() == []
    st = os.stat(p)
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    assert os.stat(p).st_mtime_ns != st.st_mtime_ns
    assert m.check_external() == []                               # 触っただけ(ハッシュが同じ)
    other = json.dumps({"camera": {"fx": 1.0}})
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(other)
    assert m.check_external() == [(0, "changed")]
    assert m.set_value(0, "camera.cx", "1").ok
    out = m.save(0)
    assert not out.ok and out.needs_confirm and out.code == "save.external"
    assert open(p, encoding="utf-8").read() == other               # 黙って上書きしない
    out = m.reload(0)
    assert out.ok and out.code == "reload.done"
    assert list(m.columns[0].leaves) == ["camera.fx"] and not m.is_dirty() and not m.can_undo()
    assert m.check_external() == []
    os.remove(p)
    assert m.check_external() == [(0, "missing")]
    out = m.save(0)
    assert not out.ok and out.code == "save.gone" and out.needs_confirm and not os.path.exists(p)
    assert m.save(0, force=True).ok and json.load(open(p, encoding="utf-8")) == {"camera": {"fx": 1.0}}
    assert m.check_external() == []


def test_force_overwrites_an_external_change(tmp_path):
    """外で変わったファイルは force=True で上書きできる(窓が「上書き」を選ばれた時の道)。"""
    p = _write(tmp_path, "day.yaml", DAY)
    m = M.ParamsModel()
    assert m.add_file(p).ok and m.set_value(0, "camera.fx", "1.5").ok
    with open(p, "a", encoding="utf-8") as fh:
        fh.write("extra: 1\n")
    assert m.save(0).code == "save.external"
    assert m.save(0, force=True).ok
    back = M.read_bundle(p)
    assert back["camera.fx"] == 1.5 and "extra" not in back


def test_revert_drops_unsaved_changes_and_their_history(tmp_path):
    """捨てる: 保存済みの値に戻り、その列の履歴は消える(別の列の履歴は残る)。"""
    m, _ = _three(tmp_path)
    assert m.set_value(0, "camera.fx", "1").ok and m.set_value(1, "camera.fx", "2").ok
    assert m.revert(0).ok and m.value(0, "camera.fx") == 812.5 and not m.is_dirty(0) and m.is_dirty(1)
    assert m.revert(0).code == "save.clean"
    assert m.undo().ok and m.value(1, "camera.fx") == 812.5 and not m.can_undo()


# ============================================================================================== #
# モデル: 壊れた入力の拒否(読み手の拒否をそのまま返す)
# ============================================================================================== #
_BOMB_YAML = "a: &a [x, x, x, x, x, x, x, x, x, x]\n" + "".join(
    "%s: &%s [*%s, *%s, *%s, *%s, *%s, *%s, *%s, *%s, *%s, *%s]\n" % ((chr(98 + i), chr(98 + i)) + (chr(97 + i),) * 10)
    for i in range(8))
_DEEP_XML = "<params>" + "".join('<section name="s%d">' % i for i in range(300)) + "</section>" * 300 + "</params>"

#: (名前, ファイル名, 中身 か None(作らない) か "DIR", 理由に入るはずの語, 小さい上限で読むか)
BROKEN = [
    ("missing file", "nope.json", None, "not a file", False),
    ("a folder", "dir.json", "DIR", "not a file", False),
    ("unknown extension", "notes.txt", "a = 1", "unknown extension", False),
    ("jsonc", "rig.jsonc", "{}", "JSONC", False),
    ("json syntax", "bad.json", "{", "invalid JSON", False),
    ("json trailing comma", "comma.json", '{"a": 1,}', "invalid JSON", False),
    ("json duplicate key", "dup.json", '{"a": 1, "a": 2}', "duplicate key", False),
    ("json NaN", "nan.json", '{"a": NaN}', "NaN", False),
    ("json top-level list", "list.json", "[1, 2]", "top level", False),
    ("json null", "null.json", '{"a": null}', "null", False),
    ("json string in a numeric field", "str.json", '{"wavelength_um": "abc"}', "numeric field", False),
    ("json dotted key", "dot.json", '{"a.b": 1}', "invalid key", False),
    ("json table in array", "tab.json", '{"a": [{"b": 1}]}', "table inside an array", False),
    ("not utf-8", "latin.json", b'{"a": "\xff\xfe"}', "UTF-8", False),
    ("too large", "big.json", json.dumps({"k%d" % i: i for i in range(200)}), "limit", True),
    ("include outside", "inc.json", '{"include": ["../x.json"]}', "outside", False),
    ("include absolute", "abs.json", '{"include": ["/etc/passwd"]}', "absolute", False),
    ("circular reference", "ref.json", '{"a": {"$param": "b"}, "b": {"$param": "a"}}', "circular", False),
    ("dangling reference", "dang.json", '{"a": {"$param": "zz"}}', "does not resolve", False),
    ("yaml python object", "py.yaml", "a: !!python/object/apply:os.system ['echo x']\n", "invalid YAML", False),
    ("yaml alias bomb", "bomb.yaml", _BOMB_YAML, "nodes", False),
    ("yaml duplicate key", "dup.yaml", "a: 1\na: 2\n", "duplicate key", False),
    ("yaml 1.1 boolean", "no.yaml", "a: NO\n", "YAML 1.1", False),
    ("yaml octal", "oct.yaml", "a: 010\n", "octal", False),
    ("yaml number key", "key.yaml", "1: 2\n", "not a string", False),
    ("yaml syntax", "bad.yaml", "a: [1, 2\n", "invalid YAML", False),
    ("toml syntax", "bad.toml", "a = = 1\n", "invalid TOML", False),
    ("xml doctype", "dtd.xml", '<!DOCTYPE params [<!ENTITY a "b">]><params><param name="x">&a;</param></params>', "DOCTYPE", False),
    ("xml external entity", "xxe.xml", '<!DOCTYPE params SYSTEM "http://127.0.0.1/x.dtd"><params/>', "DOCTYPE", False),
    ("xml syntax", "bad.xml", "<params><param name='a'>1</params>", "invalid XML", False),
    ("xml wrong root", "root.xml", "<config><param name='a'>1</param></config>", "root element", False),
    ("xml unknown element", "elem.xml", "<params><value name='a'>1</value></params>", "unknown element", False),
    ("xml duplicate key", "dup.xml", "<params><param name='a'>1</param><param name='a'>2</param></params>", "duplicate key", False),
    ("xml missing name", "name.xml", "<params><param>1</param></params>", "name attribute", False),
    ("xml dotted name", "dot.xml", "<params><param name='a.b'>1</param></params>", "invalid key", False),
    ("xml bad int", "int.xml", "<params><param name='a' type='int'>1.5</param></params>", "whole number", False),
    ("xml bad bool", "bool.xml", "<params><param name='a' type='bool'>yes</param></params>", "true or false", False),
    ("xml unknown type", "type.xml", "<params><param name='a' type='date'>x</param></params>", "unknown type", False),
    ("xml str that is a quantity", "q.xml", "<params><param name='a' type='str'>5 mm</param></params>", "number with a unit", False),
    ("xml unknown attribute", "attr.xml", "<params><param name='a' unit='mm'>5</param></params>", "unknown attribute", False),
    ("xml stray text", "text.xml", "<params>hello<param name='a'>1</param></params>", "directly inside", False),
    ("xml other kind", "kind.xml", "<params fullseye_kind='pipeline'/>", "not 'params'", False),
    ("xml newer version", "ver.xml", "<params version='99'/>", "newer", False),
    ("xml string in a numeric field", "num.xml", "<params><param name='wavelength_um' type='str'>abc</param></params>", "numeric field", False),
    ("xml too deep", "deep.xml", _DEEP_XML, "depth", False),
    ("xml too large", "big.xml", "<params>" + "<param name='k%d'>1</param>" * 1 + " " * 400 + "</params>", "limit", True),
    ("xml not utf-8", "enc.xml", b"<params><param name='a'>\xff\xfe</param></params>", "invalid XML", False),
]


def test_broken_table_is_counted():
    """壊れた入力の表は 47 種。5 つの拡張子(json / yaml / toml / xml / それ以外)を全部含む。"""
    assert len(BROKEN) == 47 and len({b[0] for b in BROKEN}) == 47 and len({b[1] for b in BROKEN}) == 47
    exts = {os.path.splitext(b[1])[1] for b in BROKEN}
    assert exts == {".json", ".jsonc", ".yaml", ".toml", ".xml", ".txt"}
    assert sum(1 for b in BROKEN if b[1].endswith(".xml")) == 20


@pytest.mark.parametrize("label,name,body,needle,small", BROKEN, ids=[b[0] for b in BROKEN])
def test_broken_input_is_refused_with_the_readers_reason(tmp_path, label, name, body, needle, small):
    """読めない・壊れた・巨大な・安全でない入力は列にならず、読み手の理由がそのまま返る。良い列は影響を受けない。"""
    m = M.ParamsModel(max_bytes=256) if small else M.ParamsModel()
    good = _write(tmp_path, "good.json", {"a": 1})
    assert m.add_file(good).ok
    p = str(tmp_path / name)
    if body == "DIR":
        os.mkdir(p)
    elif body is not None:
        _raw(tmp_path, name, body)
    out = m.add_file(p)
    assert not out.ok and out.code == "load.refused", label
    assert needle in out.reason, (label, out.reason)
    assert os.path.basename(p) in out.reason
    assert len(m.columns) == 1 and m.columns[0].name == "good.json" and m.value(0, "a") == 1
    assert out.text(M.make_tr("ja")) != out.reason                 # 枠の文は訳され、読み手の理由はそのまま入る
    assert needle in out.text(M.make_tr("ja"))


def test_opening_the_same_file_twice_is_refused(tmp_path):
    """同じファイルを 2 度開くと 2 列目は作らない(どちらが正本か分からなくなる)。同名の別ファイルは親の名前で区別。"""
    p = _write(tmp_path, "rig.json", DAY)
    os.mkdir(tmp_path / "night")
    q = _write(tmp_path / "night", "rig.json", NIGHT)
    m = M.ParamsModel()
    assert m.add_file(p).ok
    out = m.add_file(p)
    assert not out.ok and out.code == "load.duplicate" and len(m.columns) == 1
    assert m.add_file(q).ok and [c.name for c in m.columns] == ["rig.json", "night/rig.json"]


# ============================================================================================== #
# モデル: 実行との連動・対訳
# ============================================================================================== #
def test_keys_read_by_the_last_run_are_marked(tmp_path):
    """``for_op(report=True)`` の記録を渡すと、op が使ったキーの行に印が付く。束の名前が合う列だけ。"""
    m, paths = _three(tmp_path)

    def fake_op(image, fx, f_number=1.0, wavelength_um=0.5, gamma=1.0):
        return image

    bundle = parambundle.load_params(paths[0])
    kwargs, rep = bundle.for_op("fake_op", report=True, fn=fake_op)
    assert kwargs == {"fx": 812.5, "f_number": 2.8, "wavelength_um": 0.55}
    out = m.set_used(rep)
    assert out.ok and out.code == "used.count" and out.count == 3
    assert [r.key for r in m.rows() if r.used] == ["camera.fx", "optics.wavelength", "optics.f_number"]
    assert m.columns[0].used == {"camera.fx": ("fake_op.fx",), "optics.f_number": ("fake_op.f_number",),
                                 "optics.wavelength": ("fake_op.wavelength_um",)}
    assert m.columns[1].used == {} and m.columns[2].used == {}
    out = m.set_used(["camera.cx", "no.such.key"], 2)             # キーの並び + 列の指定
    assert out.count == 1 and [r.key for r in m.rows() if r.used] == ["camera.cx"] and m.columns[0].used == {}
    rep.bundle = "other.json"
    out = m.set_used([rep])
    assert out.code == "used.none" and out.count == 0 and [r for r in m.rows() if r.used] == []


def _placeholders(text: str) -> list[str]:
    return re.findall(r"%[sdr]", text)


def test_every_message_is_translated_into_five_languages():
    """対訳の表: 画面の文の型は全部 5 言語(ja・zh・tw・ko・de)に訳があり、% の並びが英語と同じ。使わない行は無い。"""
    table = M.load_i18n_table()
    assert len(table) >= 110 and "Could not open %s: %s" in table
    templates = [t for t in M.MESSAGES.values() if t != "%s"]
    assert len(templates) == len(M.MESSAGES) - 1 == 44
    missing = [t for t in templates if t not in table]
    assert missing == []
    cells = 0
    for en, row in table.items():
        for lang in M.LANGS[1:]:
            text = row.get(lang, "")
            assert text.strip(), (en, lang)
            assert _placeholders(text) == _placeholders(en), (en, lang, text)
            cells += 1
    assert cells == len(table) * 5
    literals: set[str] = set()
    for name in ("studio_params_model.py", "studio_params_qt.py"):
        tree = ast.parse(io.open(os.path.join(ROOT, name), encoding="utf-8").read())
        literals |= {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert len(literals) > 200
    dead = sorted(k for k in table if k not in literals)
    assert dead == []
    tr = M.make_tr("ja")
    assert tr("Parameters") == "パラメータ" and tr("no such text") == "no such text" and M.make_tr("en")("Save") == "Save"
    with pytest.raises(ValueError):
        M.make_tr("xx")


def test_the_name_is_the_same_as_the_project_panel():
    """名前は 1 つ: 窓の題「Parameters」は、プロジェクトの種類の表(studio_project.KINDS)と Studio の i18n.json の訳と同じ。"""
    import studio_project
    assert studio_project.KINDS["params"][1] == "Parameters"
    with io.open(os.path.join(ROOT, "studio_assets", "i18n.json"), encoding="utf-8") as fh:
        studio = json.load(fh)["strings"]["Parameters"]
    mine = M.load_i18n_table()["Parameters"]
    same = [lang for lang in M.LANGS[1:] if mine[lang] == studio[lang]]
    assert same == ["ja", "zh", "tw", "ko", "de"]


def test_example_bundles_show_every_kind_of_row():
    """「例を開く」の 2 つの束は、違う行・書き方だけ違う行・片方に無い行・同じ行を全部含む(初めての人が印を全部見られる)。"""
    m = M.ParamsModel()
    for name, data in M.example_bundles():
        assert m.add_bundle(data, name).ok
    assert [c.name for c in m.columns] == ["rig_day", "rig_night"]
    c = m.counts()
    assert (c["rows"], c["differ"], c["partial"]) == (12, 3, 1)
    assert [r.key for r in m.rows() if r.notation_differs] == ["optics.wavelength"]
    out = m.save(0)
    assert not out.ok and out.code == "save.no_path"


# ============================================================================================== #
# 窓(offscreen)
# ============================================================================================== #
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from PySide6 import QtCore, QtGui  # noqa: E402

import studio_params_qt as Q  # noqa: E402

Qt = QtCore.Qt
BUTTONS = ("open", "add", "remove", "save", "saveas", "reload", "undo", "redo", "copy", "diff")


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


@pytest.fixture
def ini(tmp_path, monkeypatch):
    """設定は一時の ini(利用者の本物の設定に触らない)。"""
    p = str(tmp_path / "studio_settings.ini")
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", p)
    return p


def _pump(app) -> None:
    for _ in range(5):
        app.processEvents()


def _window(app, paths=(), lang="en", size=(720, 420)):
    win = Q.ParamsWindow(None, M.make_tr(lang))
    win.resize(*size)
    if paths:
        outs = win.panel.add_paths(list(paths))
        assert [o.ok for o in outs] == [True] * len(paths), [o.reason for o in outs]
    win.show()
    _pump(app)
    return win


def _three_files(tmp_path) -> list[str]:
    return [_write(tmp_path, "day.json", DAY), _write(tmp_path, "night.yaml", NIGHT), _write(tmp_path, "lab.xml", LAB)]


def _visible_keys(panel) -> list[str]:
    out: list[str] = []

    def walk(parent):
        for i in range(panel.tmodel.rowCount(parent)):
            idx = panel.tmodel.index(i, 0, parent)
            n = idx.internalPointer()
            if n.row is not None:
                out.append(n.key)
            walk(idx)

    walk(QtCore.QModelIndex())
    return out


def _close_quietly(win) -> None:
    win.panel.ask_unsaved = lambda names: "discard"
    win.close()


def test_window_settings_go_to_the_temporary_ini(qapp, ini, tmp_path):
    """設定の置き場は FULLSEYE_STUDIO_SETTINGS の ini。閉じると位置・絞り込み・開いていたファイルが書かれ、次の窓で戻る。"""
    s = Q._default_settings()
    assert s.format() == QtCore.QSettings.IniFormat and os.path.normcase(s.fileName()) == os.path.normcase(ini)
    paths = _three_files(tmp_path)
    win = _window(qapp, paths, size=(640, 360))
    win.panel.set_diff_only(True)
    assert win.close() and not win.isVisible()
    assert os.path.isfile(ini)
    text = io.open(ini, encoding="utf-8").read()
    assert "[params_window]" in text and "geometry=" in text and "diff_only=true" in text
    again = Q.ParamsWindow(None, M.make_tr("en"))
    assert (again.width(), again.height()) == (640, 360)
    assert again.panel.tmodel.diff_only and again.panel.buttons["diff"].isChecked()
    outs = again.restore_session()
    assert [o.ok for o in outs] == [True, True, True]
    assert [c.name for c in again.panel.model.columns] == ["day.json", "night.yaml", "lab.xml"]
    _close_quietly(again)


def test_empty_window_guides_the_first_step(qapp, ini):
    """空の状態: 何をする場所かの 1 行と、最初の一手のボタン 2 つ(開く / 例を開く)。例を開くと表になる。"""
    win = _window(qapp)
    p = win.panel
    assert p.stack.currentWidget() is p.empty and p.empty_label.isVisible()
    assert "rows are keys" in p.empty_label.text() and p.empty_open.isVisible() and p.empty_example.isVisible()
    assert win.windowTitle() == "Parameters" and p.counts_text() == "0 bundle(s)"
    enabled = {k: p.buttons[k].isEnabled() for k in BUTTONS}
    assert enabled == {"open": True, "add": True, "remove": False, "save": False, "saveas": False, "reload": False,
                       "undo": False, "redo": False, "copy": False, "diff": False}
    p.empty_example.click()
    _pump(qapp)
    assert p.stack.currentWidget() is p.tree and len(p.model.columns) == 2 and len(_visible_keys(p)) == 12
    assert win.windowTitle() == "Parameters — rig_day, rig_night"
    _close_quietly(win)


def test_open_three_bundles_shows_columns_marks_and_title(qapp, ini, tmp_path):
    """3 つ開く: 見出し = キー・印・束 3 つ、行 = 9、題に束の名前。印は色だけでなく文字・斜線・セルの印でも出る。"""
    win = _window(qapp, _three_files(tmp_path))
    p, tm = win.panel, win.panel.tmodel
    heads = [tm.headerData(i, Qt.Horizontal) for i in range(tm.columnCount())]
    assert heads == ["Key", Q.MARK_DIFFER, "day.json", "night.yaml", "lab.xml"]
    assert _visible_keys(p) == ["camera.fx", "camera.fy", "camera.cx", "camera.size", "optics.wavelength",
                                "optics.f_number", "exposure.auto", "exposure.mode", "exposure.gain_db"]
    assert win.windowTitle() == "Parameters — day.json, night.yaml, lab.xml"
    assert p.counts_text() == "3 bundle(s) · 9 row(s) · ≠ 4 differ · ◌ 1 not in every bundle"
    marks = {k: p.index_of(0, k).siblingAtColumn(1).data() for k in _visible_keys(p)}
    assert marks == {"camera.fx": "≠", "camera.fy": "", "camera.cx": "", "camera.size": "",
                     "optics.wavelength": "≈", "optics.f_number": "≠", "exposure.auto": "≠",
                     "exposure.mode": "≠", "exposure.gain_db": "◌"}
    exposure = tm.index(2, 1)
    assert exposure.data() == "≠◌" and "2" in exposure.data(Qt.ToolTipRole)
    # 違う行: 全部のセルに色、基準(最初の束)と違うセルにだけ小さな印。
    fx = [p.index_of(c, "camera.fx") for c in range(3)]
    assert [i.data() for i in fx] == ["812.5", "812.5", "815.0"]
    assert [i.data(Qt.BackgroundRole) is not None for i in fx] == [True, True, True]
    assert [i.data(Qt.DecorationRole) is not None for i in fx] == [False, False, True]
    assert p.index_of(0, "camera.fy").data(Qt.BackgroundRole) is None
    # 片方に無いセル: 空欄 + 斜線(色ではなく模様)。
    gain = [p.index_of(c, "exposure.gain_db") for c in range(3)]
    assert [i.data() for i in gain] == ["", "12", ""]
    assert gain[0].data(Qt.BackgroundRole).style() == Qt.BDiagPattern and gain[1].data(Qt.BackgroundRole) is None
    assert "not in day.json" in gain[0].data(Qt.ToolTipRole)
    assert "whole number" in gain[1].data(Qt.ToolTipRole)
    legend = tm.headerData(1, Qt.Horizontal, Qt.ToolTipRole)
    assert [m in legend for m in (Q.MARK_DIFFER, Q.MARK_PARTIAL, Q.MARK_NOTATION, Q.MARK_USED)] == [True] * 4
    _close_quietly(win)


def test_cells_are_edited_in_place_with_type_checks(qapp, ini, tmp_path):
    """その場の編集: 数は文字の欄 + 検査(スピンではない)、真偽はチェック。断られたら値はそのままで理由が状態の行に出る。"""
    win = _window(qapp, _three_files(tmp_path))
    p, tm = win.panel, win.panel.tmodel
    fx = p.index_of(0, "camera.fx")
    auto = p.index_of(0, "exposure.auto")
    gain_missing = p.index_of(0, "exposure.gain_db")
    assert bool(tm.flags(fx) & Qt.ItemIsEditable) and not bool(tm.flags(fx) & Qt.ItemIsUserCheckable)
    assert bool(tm.flags(auto) & Qt.ItemIsUserCheckable) and not bool(tm.flags(auto) & Qt.ItemIsEditable)
    assert not bool(tm.flags(gain_missing) & (Qt.ItemIsEditable | Qt.ItemIsUserCheckable))
    assert auto.data(Qt.CheckStateRole) == Qt.Checked
    # 本物の編集の欄を通す
    p.tree.setCurrentIndex(fx)
    p.tree.edit(fx)
    _pump(qapp)
    editors = [w for w in p.tree.viewport().findChildren(QtWidgets.QLineEdit) if w.isVisible()]
    assert len(editors) == 1 and editors[0].text() == "812.5"
    assert not p.tree.viewport().findChildren(QtWidgets.QAbstractSpinBox)
    editors[0].setText("820")
    p.tree.itemDelegate().commitData.emit(editors[0])
    p.tree.itemDelegate().closeEditor.emit(editors[0], QtWidgets.QAbstractItemDelegate.NoHint)
    _pump(qapp)
    assert p.model.value(0, "camera.fx") == 820.0 and isinstance(p.model.value(0, "camera.fx"), float)
    fx = p.index_of(0, "camera.fx")
    assert fx.data() == "820.0" and fx.data(Qt.FontRole).bold() and "saved value: 812.5" in fx.data(Qt.ToolTipRole)
    assert tm.headerData(2, Qt.Horizontal) == "day.json *" and win.windowTitle().startswith("Parameters — day.json *,")
    assert p.counts_text().endswith("* 1 unsaved") and p.buttons["save"].isEnabled() and p.buttons["undo"].isEnabled()
    # 断られる編集
    assert tm.setData(fx, "fast", Qt.EditRole) is False
    assert p.model.value(0, "camera.fx") == 820.0
    assert p.message_level == "error" and p.message_label.full_text() == "✕ camera.fx: this field holds a number; 'fast' is not a number"
    # 真偽はチェックで
    assert tm.setData(p.index_of(0, "exposure.auto"), Qt.Unchecked, Qt.CheckStateRole) is True
    assert p.model.value(0, "exposure.auto") is False
    assert p.index_of(0, "exposure.auto").data(Qt.CheckStateRole) == Qt.Unchecked
    # 触っただけ(同じ文字)は変更にしない
    n = len(p.model._undo)
    assert tm.setData(p.index_of(0, "camera.cx"), "320", Qt.EditRole) is False and len(p.model._undo) == n == 2
    _close_quietly(win)


def test_toolbar_undo_redo_copy_and_marks_follow(qapp, ini, tmp_path):
    """道具の帯: 元に戻す・やり直し・列へ写す。写すメニューは「選んだ値を他の 2 列へ」+「違う値を全部 他の 2 列へ」。"""
    win = _window(qapp, _three_files(tmp_path))
    p = win.panel
    assert p.select_cell(0, "optics.f_number") and p.current_cell() == (0, "optics.f_number")
    p._fill_copy_menu()
    texts = [a.text() for a in p.copy_menu.actions() if not a.isSeparator()]
    assert texts == ["Copy optics.f_number to night.yaml", "Copy optics.f_number to lab.xml",
                     "Copy every differing value from day.json to night.yaml",
                     "Copy every differing value from day.json to lab.xml"]
    p.copy_menu.actions()[0].trigger()
    _pump(qapp)
    assert p.model.value(1, "optics.f_number") == 2.8
    assert p.index_of(0, "optics.f_number").siblingAtColumn(1).data() == ""          # 行の印が消える
    assert p.counts_text() == "3 bundle(s) · 9 row(s) · ≠ 3 differ · ◌ 1 not in every bundle · * 1 unsaved"
    p.buttons["undo"].click()
    assert p.model.value(1, "optics.f_number") == 1.4 and not p.model.is_dirty()
    assert p.message_label.full_text() == "undone: copy optics.f_number" and p.buttons["redo"].isEnabled()
    p.buttons["redo"].click()
    assert p.model.value(1, "optics.f_number") == 2.8 and not p.buttons["redo"].isEnabled()
    out = p.copy_column(0, 2)
    assert out.ok and out.count == 2 and p.message_label.full_text() == "copied 2 value(s) to lab.xml"
    assert p.current_cell() == (0, "optics.f_number")                                # 選んでいたセルは保たれる
    _close_quietly(win)


def test_save_writes_files_and_clears_the_unsaved_marks(qapp, ini, tmp_path):
    """保存: 変えた列だけを元の形式で書く。失われる物があれば聞く(ここでは YAML のコメント)。印が消える。"""
    paths = _three_files(tmp_path)
    with open(paths[1], "a", encoding="utf-8") as fh:
        fh.write("# hand-written note\n")
    win = _window(qapp, paths)
    p = win.panel
    asked = []
    p.ask_losses = lambda name, lines: (asked.append((name, lines)) or True)
    assert p.edit_cell(0, "camera.fx", "900").ok and p.edit_cell(1, "camera.fx", "901").ok
    lab_before = open(paths[2], "rb").read()
    p.buttons["save"].click()
    _pump(qapp)
    assert asked == [("night.yaml", ["comments are not kept (1 line(s))",
                                     "layout is normalised (indentation, quoting, number spelling such as 1.50 -> 1.5)"])]
    assert json.load(open(paths[0], encoding="utf-8"))["camera"]["fx"] == 900.0
    assert yaml.safe_load(open(paths[1], encoding="utf-8"))["camera"]["fx"] == 901.0
    assert open(paths[2], "rb").read() == lab_before
    assert not p.model.is_dirty() and not p.buttons["save"].isEnabled()
    assert win.windowTitle() == "Parameters — day.json, night.yaml, lab.xml"
    assert p.message_label.full_text().startswith("saved night.yaml")
    # 聞かれて断ると書かない
    with open(paths[1], "a", encoding="utf-8") as fh:
        fh.write("# another note\n")
    assert p.reload_column(1) and p.edit_cell(1, "camera.fx", "902").ok
    p.ask_losses = lambda name, lines: False
    before = open(paths[1], "rb").read()
    assert p.save_all() is False and open(paths[1], "rb").read() == before and p.model.is_dirty(1)
    assert p.message_level == "warn" and p.message_label.full_text() == "▲ not saved: night.yaml"
    _close_quietly(win)


def test_closing_with_unsaved_changes_asks(qapp, ini, tmp_path):
    """未保存で閉じる: やめる → 開いたまま / 捨てる → 閉じて値は保存済みに戻る / 保存 → 書いて閉じる。Esc も同じ道。"""
    paths = _three_files(tmp_path)
    win = _window(qapp, paths)
    p = win.panel
    calls = []
    assert p.edit_cell(0, "camera.fx", "900").ok
    p.ask_unsaved = lambda names: (calls.append(list(names)) or "cancel")
    win.close()
    assert win.isVisible() and calls == [["day.json"]] and p.model.is_dirty()
    QtCore.QCoreApplication.sendEvent(win, QtGui.QKeyEvent(QtCore.QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
    assert win.isVisible() and len(calls) == 2
    p.ask_unsaved = lambda names: (calls.append(list(names)) or "discard")
    win.close()
    assert not win.isVisible() and len(calls) == 3
    assert p.model.value(0, "camera.fx") == 812.5 and not p.model.is_dirty()
    assert json.load(open(paths[0], encoding="utf-8"))["camera"]["fx"] == 812.5
    win.show()
    assert p.edit_cell(2, "camera.fx", "777").ok
    p.ask_unsaved = lambda names: (calls.append(list(names)) or "save")
    win.close()
    assert not win.isVisible() and calls[-1] == ["lab.xml"] and len(calls) == 4
    assert M.read_bundle(paths[2])["camera.fx"] == 777.0
    # 未保存が無ければ聞かない
    win.show()
    win.close()
    assert not win.isVisible() and len(calls) == 4


def test_diff_only_and_search_filter_the_tree(qapp, ini, tmp_path):
    """違う行だけ・検索: 木の行が絞られ、状態の行に「何行のうち何行」が出る。Esc は先に検索を消す。"""
    win = _window(qapp, _three_files(tmp_path))
    p = win.panel
    p.buttons["diff"].click()
    assert p.tmodel.diff_only and _visible_keys(p) == ["camera.fx", "optics.f_number", "exposure.auto", "exposure.mode",
                                                       "exposure.gain_db"]
    assert p.counts_text().startswith("3 bundle(s) · 5 of 9 row(s)")
    p.search.setText("EXPO")
    assert _visible_keys(p) == ["exposure.auto", "exposure.mode", "exposure.gain_db"]
    assert p.counts_text().startswith("3 bundle(s) · 3 of 9 row(s)")
    # 違う行だけの時に差を無くすと、その行は消える
    assert p.copy_cell("exposure.mode", 0, 2).ok
    assert _visible_keys(p) == ["exposure.auto", "exposure.gain_db"]
    p.buttons["diff"].click()
    assert not p.tmodel.diff_only and _visible_keys(p) == ["exposure.auto", "exposure.mode", "exposure.gain_db"]
    p.search.setText("zzz")
    assert _visible_keys(p) == [] and p.counts_text().startswith("3 bundle(s) · 0 of 9 row(s)")
    esc = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    QtCore.QCoreApplication.sendEvent(win, esc)
    assert win.isVisible() and p.search.text() == "" and len(_visible_keys(p)) == 9
    p.ask_unsaved = lambda names: "discard"
    QtCore.QCoreApplication.sendEvent(win, esc)
    assert not win.isVisible()


def test_rows_are_dense_and_gaps_follow_the_rules(qapp, ini, tmp_path):
    """密度: 行の高さ = 文字 + 4 px、ボタンは 24 px の正方形で間は 4 px(群の間 8 px)、枠の内側 2 px。"""
    win = _window(qapp, _three_files(tmp_path))
    p = win.panel
    fm = p.tree.fontMetrics()
    keys = _visible_keys(p)
    heights = [p.tree.visualRect(p.index_of(0, k)).height() for k in keys]
    assert len(heights) == 9 and set(heights) == {fm.height() + 4}
    r1, r2 = p.tree.visualRect(p.index_of(0, "camera.fx")), p.tree.visualRect(p.index_of(0, "camera.fy"))
    assert r2.top() - r1.top() == fm.height() + 4                              # 行の間に余分な隙間が無い
    btns = [p.buttons[k] for k in BUTTONS]
    assert [(b.width(), b.height()) for b in btns] == [(24, 24)] * 10
    gaps = [btns[i + 1].geometry().left() - btns[i].geometry().right() - 1 for i in range(9)]
    assert gaps == [4, 4, 8, 4, 4, 8, 4, 4, 8]
    assert (p.bar.geometry().left(), p.bar.geometry().top()) == (2, 2)
    assert p.stack.geometry().top() - p.bar.geometry().bottom() - 1 == 2
    assert p.status.geometry().top() - p.stack.geometry().bottom() - 1 == 2
    assert p.status.height() == fm.height() + 4 and p.height() - p.status.geometry().bottom() - 1 == 2
    assert p.tree.indentation() == 12 and p.tree.header().height() == fm.height() + 6
    _close_quietly(win)


@pytest.mark.parametrize("lang", M.LANGS)
def test_six_languages_fit_without_clipping(qapp, ini, tmp_path, lang):
    """6 言語: 道具の帯のボタン 10 個と検索の欄が 720 px でも 400 px でも帯の内側に収まり、見出し・状態の行・
    空の状態の文が欄の幅を超えない(文字の幅を測る)。en 以外はツールヒントが訳されている。"""
    en = M.make_tr("en")
    tr = M.make_tr(lang)
    measured = 0
    for size in ((720, 420), (400, 300)):
        win = _window(qapp, _three_files(tmp_path), lang=lang, size=size)
        p = win.panel
        fm = p.fontMetrics()
        assert p.bar.width() <= size[0]
        for k in BUTTONS:
            b = p.buttons[k]
            assert b.isVisible() and b.geometry().right() < p.bar.width() and b.geometry().left() >= 0, (lang, size, k)
            assert b.toolTip().strip() and b.accessibleName().strip(), (lang, k)
            measured += 1
        assert p.search.isVisible() and p.search.width() >= 60 and p.search.geometry().right() < p.bar.width()
        assert p.search.placeholderText() == tr("Search keys")
        if size[0] == 720:
            hdr = p.tree.header()
            tm = p.tmodel
            for i in range(tm.columnCount()):
                text = tm.headerData(i, Qt.Horizontal)
                assert fm.horizontalAdvance(text) + 8 <= hdr.sectionSize(i), (lang, i, text, hdr.sectionSize(i))
                measured += 1
            assert hdr.length() <= p.tree.viewport().width()                    # 横スクロールが出ない
        else:
            assert p.tree.header().length() <= p.tree.viewport().width(), (lang, "narrow")
        # 状態の行: 語つきの形か、収まらなければ印 + 数の形。どちらでも欄の幅を超えない(全文はツールヒント)。
        text = p.counts_label.text()
        assert text in (p.counts_text(), p.counts_text(compact=True)) and text.startswith(tr("%d bundle(s)") % 3)
        assert fm.horizontalAdvance(text) <= p.counts_label.width() <= p.status.width(), (lang, size, text)
        assert p.counts_label.toolTip().startswith(p.counts_text())
        measured += 1
        _close_quietly(win)
    assert measured == 10 + 5 + 1 + 10 + 1
    # 空の状態の文とボタン
    win = _window(qapp, lang=lang, size=(400, 300))
    p = win.panel
    lab = p.empty_label
    assert lab.text() == tr(Q.ParamsPanel.EMPTY_TEXT) and lab.height() >= lab.heightForWidth(lab.width()) > 0
    for b, src in ((p.empty_open, "Open files"), (p.empty_example, "Open the example")):
        assert b.text() == tr(src) and b.width() >= b.fontMetrics().horizontalAdvance(b.text()) + 8
        assert b.geometry().right() < p.empty.width() and b.geometry().left() >= 0
    if lang != "en":
        same = [k for k in BUTTONS if p.buttons[k].toolTip() == _window_tooltip(en, k)]
        assert same == [], (lang, same)
        assert lab.text() != en(Q.ParamsPanel.EMPTY_TEXT) and win.windowTitle() == tr("Parameters") != ""
    _close_quietly(win)


def _window_tooltip(tr, key: str) -> str:
    """英語のツールヒント(比べる相手)。"""
    win = Q.ParamsWindow(None, tr)
    try:
        return win.panel.buttons[key].toolTip()
    finally:
        win.deleteLater()


def test_every_text_on_screen_goes_through_tr(qapp, ini, tmp_path):
    """画面の文は全部 tr を通り、対訳の表にある: 記録する tr で窓を一通り動かし、通った文が全部表にあることを数える。"""
    table = M.load_i18n_table()
    seen: list[str] = []

    def rec(text):
        seen.append(text)
        return text

    paths = _three_files(tmp_path)
    paths.append(_raw(tmp_path, "rig.toml", "# c\n[camera]\nfx = 1.0\n"))
    win = Q.ParamsWindow(None, rec)
    p = win.panel
    p.add_paths(paths + [str(tmp_path / "nope.json")])
    win.show()
    _pump(qapp)
    tm = p.tmodel
    for i in range(tm.columnCount()):
        tm.headerData(i, Qt.Horizontal)
        tm.headerData(i, Qt.Horizontal, Qt.ToolTipRole)
    for k in _visible_keys(p):
        for c in range(-2, 4):
            idx = p.index_of(max(c, 0), k).siblingAtColumn(c + 2)
            idx.data(Qt.ToolTipRole)
    for i in range(tm.rowCount()):
        tm.index(i, 1).data(Qt.ToolTipRole)
    p.select_cell(0, "camera.fx")
    p._fill_copy_menu()
    p.edit_cell(0, "camera.fx", "x")
    p.edit_cell(0, "camera.cx", "1.5")
    p.edit_cell(3, "camera.fx", "2")
    p.copy_cell("exposure.gain_db", 1, 0)
    p.copy_column(1, 2)
    p.undo()
    p.redo()
    p.mark_used(["camera.fx"], 0)
    p.ask_losses = lambda name, lines: False
    p.save_all()
    with open(paths[0], "a", encoding="utf-8") as fh:
        fh.write(" ")
    p.check_external()
    p.set_diff_only(True)
    p.counts_text()
    p.title()
    _pump(qapp)
    asked = sorted(set(s for s in seen if s and s != "%s"))
    assert len(asked) >= 60, len(asked)
    unknown = [s for s in asked if s not in table]
    assert unknown == []
    _close_quietly(win)


def test_run_marks_and_external_changes_show_in_the_window(qapp, ini, tmp_path):
    """実行との連動: 読んだキーの行に ▸ が付く。外での変更: 前に来た時に調べ、状態の行に注意(▲)として出る。"""
    paths = _three_files(tmp_path)
    win = _window(qapp, paths)
    p = win.panel
    out = p.mark_used(["camera.fx", "optics.wavelength"], 0)
    assert out.count == 2 and p.message_label.full_text() == "the last run read 2 key(s)"
    assert p.index_of(0, "camera.fx").siblingAtColumn(1).data() == "≠▸"
    assert p.index_of(0, "optics.wavelength").siblingAtColumn(1).data() == "≈▸"
    assert p.tmodel.index(0, 1).data() == "≠▸"                              # 節にも上がる
    assert "read by the last run" in p.index_of(0, "camera.fx").data(Qt.ToolTipRole)
    assert "read by the last run" not in p.index_of(1, "camera.fx").data(Qt.ToolTipRole)
    with open(paths[1], "a", encoding="utf-8") as fh:
        fh.write("extra: 5\n")
    assert p.check_external() == [(1, "changed")]
    assert p.message_level == "warn" and p.message_label.full_text().startswith("▲ night.yaml changed on disk")
    # 外で変わった物を保存しようとすると聞く(上書き / 読み直す / やめる)
    assert p.edit_cell(1, "camera.fx", "5").ok
    asked = []
    p.ask_overwrite = lambda name, text: (asked.append(name) or "reload")
    assert p.save_all() is False and asked == ["night.yaml"]
    assert p.model.value(1, "extra") == 5 and p.model.value(1, "camera.fx") == 812.5 and not p.model.is_dirty()
    _close_quietly(win)


def test_toml_column_is_marked_read_only_and_not_editable(qapp, ini, tmp_path):
    """TOML の列: 見出しに読み取り専用の印、セルは編集できない、保存は「名前を付けて保存」へ回る。"""
    t = _raw(tmp_path, "rig.toml", "[camera]\nfx = 812.5\non = true\n")
    win = _window(qapp, [t, _write(tmp_path, "day.json", DAY)])
    p, tm = win.panel, win.panel.tmodel
    assert tm.headerData(2, Qt.Horizontal) == "rig.toml (read-only)"
    assert "read-only here" in tm.headerData(2, Qt.Horizontal, Qt.ToolTipRole)
    for key in ("camera.fx", "camera.on"):
        f = tm.flags(p.index_of(0, key))
        assert not bool(f & (Qt.ItemIsEditable | Qt.ItemIsUserCheckable)), key
    assert bool(tm.flags(p.index_of(1, "camera.fx")) & Qt.ItemIsEditable)
    picked = []
    target = str(tmp_path / "rig_copy.xml")
    p.pick_save = lambda i: (picked.append(i) or target)
    assert p.save_column(0) is True and picked == [0]
    assert tm.headerData(2, Qt.Horizontal) == "rig_copy.xml" and M.read_bundle(target)["camera.on"] is True
    assert bool(tm.flags(p.index_of(0, "camera.fx")) & Qt.ItemIsEditable)
    _close_quietly(win)


def test_show_params_window_reuses_the_window_of_a_parent(qapp, ini, tmp_path):
    """Studio の入口: 同じ親なら 2 枚目を作らず、既にある窓へ列を足す。モードレスで、親の上の独立した窓。"""
    parent = QtWidgets.QWidget()
    paths = _three_files(tmp_path)
    a = Q.show_params_window(parent, [paths[0]], M.make_tr("en"))
    b = Q.show_params_window(parent, [paths[1]])
    assert a is b and [c.name for c in a.panel.model.columns] == ["day.json", "night.yaml"]
    assert not a.isModal() and a.isWindow() and a.parent() is parent and a.isVisible()
    c = Q.show_params_window(parent, [paths[1]])                                      # 同じファイルは 2 列にならない
    assert c is a and len(a.panel.model.columns) == 2
    assert a.panel.message_level == "error" and "already open" in a.panel.message_label.full_text()
    _close_quietly(a)
    parent.deleteLater()


def _answer(app, label: str, log: list) -> None:
    """次に出るモーダルの箱の、``label`` のボタンを押す(出なければ 3 秒で諦めて箱を閉じる = 試験は落ちる)。"""
    state = {"tries": 0}

    def go():
        box = app.activeModalWidget()
        state["tries"] += 1
        if not isinstance(box, QtWidgets.QMessageBox):
            if state["tries"] < 300:
                QtCore.QTimer.singleShot(10, go)
            return
        hit = [b for b in box.buttons() if b.text() == label]
        log.append((box.text(), box.informativeText(), sorted(b.text() for b in box.buttons())))
        if hit:
            hit[0].click()
        else:
            box.reject()

    QtCore.QTimer.singleShot(0, go)


def test_the_three_question_boxes_ask_in_the_ui_language(qapp, ini, tmp_path):
    """聞く箱の既定(未保存・失われる物・外での変更): 押したボタンどおりの答えが返り、文とボタンは UI の言語。"""
    win = _window(qapp, [_write(tmp_path, "day.json", DAY)], lang="ja")
    p = win.panel
    tr = M.make_tr("ja")
    log: list = []
    answers = []
    for label, want in (("Save and close", "save"), ("Close without saving", "discard"), ("Cancel", "cancel")):
        _answer(qapp, tr(label), log)
        answers.append(p._ask_unsaved_box(["day.json"]) == want)
    for label, want in (("Save anyway", True), ("Cancel", False)):
        _answer(qapp, tr(label), log)
        answers.append(p._ask_losses_box("day.json", ["a", "b"]) is want)
    for label, want in (("Overwrite anyway", "overwrite"), ("Reload", "reload"), ("Cancel", "cancel")):
        _answer(qapp, tr(label), log)
        answers.append(p._ask_overwrite_box("day.json", "changed") == want)
    assert answers == [True] * 8 and len(log) == 8
    assert log[0][0] == tr("%d bundle(s) have unsaved changes: %s") % (1, "day.json")
    want = sorted([tr("Save and close"), tr("Close without saving"), tr("Cancel")])
    assert log[0][2] == want and want != sorted(["Save and close", "Close without saving", "Cancel"])
    assert log[3][0] == tr("Saving %s rewrites the whole file. These are not kept:") % "day.json"
    assert log[3][1] == "\u2022 a\n\u2022 b" and log[3][2] == sorted([tr("Save anyway"), tr("Cancel")])
    assert log[5][2] == sorted([tr("Overwrite anyway"), tr("Reload"), tr("Cancel")])
    _close_quietly(win)


def test_main_refuses_a_dangling_lang_option(capsys):
    """``--lang`` に値が無ければ窓を出さずに 2 を返す。"""
    assert Q.main(["--lang"]) == 2
    assert "ja" in capsys.readouterr().err


# ============================================================================================== #
# 1.2.0 の操作感(B6 [束]、設計書 STUDIO_INTERACTION_RULES の P07〜P09・P12〜P15)
# ============================================================================================== #
from PySide6.QtTest import QTest  # noqa: E402


@pytest.fixture
def fusion(qapp):
    """見た目と配置の門は Qt の様式を Fusion に固定して数える(設計書 P14-9)。"""
    before = qapp.style().name()
    qapp.setStyle("Fusion")
    yield qapp
    qapp.setStyle(before)


def _collect_real_boxes(monkeypatch, key):
    """確認の箱を「見せる関数」だけ差し替え、作る関数が作った本物の箱を見せてから ``key`` を送る。

    箱の中身(題・文・ボタンの文・役割・既定・Esc・標準ボタン)と、押されたボタンの役割を記録して返す。"""
    seen = []

    def show(box):
        box.show()
        QTest.keyClick(box, key)
        hit = box.clickedButton()
        seen.append({
            "title": box.windowTitle(), "text": box.text(), "informative": box.informativeText(),
            "buttons": [(b.text(), b.property("fsRole"), box.buttonRole(b)) for b in box.buttons()],
            "default": box.defaultButton().property("fsRole") if box.defaultButton() is not None else None,
            "escape": box.escapeButton().property("fsRole") if box.escapeButton() is not None else None,
            "default_role": box.buttonRole(box.defaultButton()) if box.defaultButton() is not None else None,
            "standard": box.standardButtons(), "hit": hit.property("fsRole") if hit is not None else None,
            "modal_visible": box.isVisible()})
        return seen[-1]["hit"] or "cancel"

    monkeypatch.setattr(Q, "_exec_confirm_box", show)
    return seen


#: 入口ごとの箱の形(英語の元の文): 題・ボタン(役割の鍵, 文)。
_BOX_SHAPES = {
    "close": ("Close", [("save", "Save and close"), ("discard", "Close without saving"), ("cancel", "Cancel")]),
    "open": ("Open", [("save", "Save and open"), ("discard", "Open without saving"), ("cancel", "Cancel")]),
    "remove": ("Remove column", [("save", "Save and remove"), ("discard", "Remove without saving"),
                                 ("cancel", "Cancel")]),
    "reload": ("Reload", [("run", "Reload"), ("cancel", "Cancel")]),
    "losses": ("Save", [("run", "Save anyway"), ("cancel", "Cancel")]),
    "changed": ("Save", [("reload", "Reload"), ("overwrite", "Overwrite anyway"), ("cancel", "Cancel")]),
}


def _drive_every_box_entry(qapp, p, win, paths) -> list[str]:
    """6 つの入口を順に通す(どれも箱で「キャンセル」になる前提)。通った入口の名前を返し、状態が変わらない事を確かめる。"""
    done = []
    assert p.edit_cell(0, "camera.fx", "900").ok and p.model.is_dirty(0)
    win.close()                                                           # 閉じる → 未保存の箱
    assert win.isVisible() and p.model.is_dirty(0)
    done.append("close")
    p.pick_open = lambda: [paths[0]]
    p.open_files()                                                        # 開き直す → 未保存の箱(開く)
    assert [c.name for c in p.model.columns] == ["day.json", "night.yaml", "lab.xml"] and p.model.is_dirty(0)
    done.append("open")
    assert p.select_cell(0, "camera.fx")
    p.remove_current()                                                    # 列を外す → 未保存の箱(外す)
    assert len(p.model.columns) == 3
    done.append("remove")
    p.reload_current()                                                    # 読み直す → 実行の箱(読み直す)
    assert p.model.value(0, "camera.fx") == 900.0
    done.append("reload")
    with open(paths[1], "a", encoding="utf-8") as fh:                     # YAML のコメントは保存で失われる
        fh.write("# hand-written note\n")
    assert p.reload_column(1) and p.edit_cell(1, "camera.fx", "901").ok
    before = open(paths[1], "rb").read()
    assert p.save_column(1) is False and open(paths[1], "rb").read() == before
    done.append("losses")
    assert p.edit_cell(2, "camera.fx", "902").ok
    with open(paths[2], "a", encoding="utf-8") as fh:                     # 外で変わった XML
        fh.write("\n")
    with open(paths[2], "rb") as fh:
        lab_before = fh.read()
    assert p.save_column(2) is False and open(paths[2], "rb").read() == lab_before
    assert p.model.value(2, "camera.fx") == 902.0                         # 読み直してもいない
    done.append("changed")
    return done


@pytest.mark.parametrize("key", [Qt.Key_Escape, Qt.Key_Return])
def test_params_boxes_default_and_escape_cancel_real_box(qapp, fusion, ini, tmp_path, monkeypatch, key):
    """D88 / G09(b'): 6 つの入口(閉じる・開く・列を外す・読み直す・失われる保存・外で変わった)から本物の箱を作らせ、
    Esc でも Enter でもキャンセルになり何も変わらない。標準ボタン 0・既定 = Esc = キャンセル(RejectRole)・ボタンは動詞で
    UI の言語(ja の訳が表にあり、英語と違う)。"""
    table = M.load_i18n_table()
    tr = M.make_tr("ja")
    seen = _collect_real_boxes(monkeypatch, key)
    paths = _three_files(tmp_path)
    win = _window(qapp, paths, lang="ja")
    p = win.panel
    done = _drive_every_box_entry(qapp, p, win, paths)
    assert done == list(_BOX_SHAPES) and len(seen) == len(done) == 6
    checked = 0
    for name, box in zip(done, seen):
        title, buttons = _BOX_SHAPES[name]
        assert box["standard"] == QtWidgets.QMessageBox.NoButton, name
        assert box["default"] == box["escape"] == "cancel" == box["hit"], (name, box)
        assert box["default_role"] == QtWidgets.QMessageBox.RejectRole, name
        assert sorted((b[1], b[0]) for b in box["buttons"]) == sorted((k, tr(s)) for k, s in buttons), name
        assert box["title"] == tr(title) != title, name
        for text, _role_key, _role in box["buttons"]:
            en = [s for _k, s in buttons if tr(s) == text]
            assert len(en) == 1 and en[0] in table and text != en[0], (name, text)
            checked += 1
        assert not box["modal_visible"], name                             # 答えたら箱は閉じる
    assert checked == 3 + 3 + 3 + 2 + 2 + 3
    assert seen[0]["text"] == tr("%d bundle(s) have unsaved changes: %s") % (1, "day.json")
    assert seen[4]["informative"].count("\u2022") == 2                    # 失われる物の並び
    _close_quietly(win)


def test_params_set_confirm_takes_the_parents_confirm_action(qapp, ini, tmp_path, monkeypatch):
    """D88: 親(Studio)の confirm_action を set_confirm で受け取る。新しい形(kind・buttons)は役割の鍵・役割・真偽のどれで
    答えてもよく、知らない答えはキャンセル(fail-closed)。古い形(4 つの引数 → 真偽)は 2 択だけを任せ、3 択は自前の箱で聞く。"""
    own = _collect_real_boxes(monkeypatch, Qt.Key_Escape)
    paths = _three_files(tmp_path)
    calls = []

    def new_style(parent, title, text, action, *, kind="run", buttons=None):
        calls.append((title, text, action, kind, [k for k, _s in buttons]))
        return answers.pop(0)

    win = Q.ParamsWindow(None, M.make_tr("en"), confirm=new_style)
    p = win.panel
    p.add_paths(paths)
    win.show()
    _pump(qapp)
    assert p.edit_cell(0, "camera.fx", "900").ok
    answers = ["cancel", "nonsense", QtWidgets.QMessageBox.RejectRole, False]
    for _ in range(4):
        win.close()
        assert win.isVisible() and p.model.is_dirty(0)
    assert len(calls) == 4 and calls[0] == ("Close", "1 bundle(s) have unsaved changes: day.json", "Close", "unsaved",
                                            ["save", "discard", "cancel"])
    answers = [QtWidgets.QMessageBox.DestructiveRole]                         # 役割で答える = 保存せずに閉じる
    win.close()
    assert not win.isVisible() and not p.model.is_dirty(0) and len(calls) == 5
    win.show()
    assert p.edit_cell(0, "camera.fx", "901").ok
    answers = ["save"]
    win.close()
    assert not win.isVisible() and M.read_bundle(paths[0])["camera.fx"] == 901.0
    assert own == []                                                          # 新しい形なら自前の箱は出ない
    # 古い形の confirm_action(parent, title, text, action) -> bool
    legacy = []
    p.set_confirm(lambda parent, title, text, action: (legacy.append((title, action)) or True))
    win.show()
    with open(paths[1], "a", encoding="utf-8") as fh:
        fh.write("# note\n")
    assert p.reload_column(1) and p.edit_cell(1, "camera.fx", "5").ok
    assert p.save_column(1) is True and legacy == [("Save", "Save anyway")]   # 2 択は親へ
    assert p.edit_cell(0, "camera.fx", "6").ok
    win.close()                                                               # 3 択は自前の箱(Esc でキャンセル)
    assert win.isVisible() and len(own) == 1 and own[0]["hit"] == "cancel" and len(legacy) == 1
    p.set_confirm(None)
    _close_quietly(win)
    # Studio の入口からも渡せる
    parent = QtWidgets.QWidget()
    w2 = Q.show_params_window(parent, [paths[2]], M.make_tr("en"), confirm=new_style)
    assert w2.panel.confirm_function() is new_style
    _close_quietly(w2)
    parent.deleteLater()


def _strips(p) -> list:
    return [w for w in p.findChildren(QtWidgets.QWidget, "panelStrip")]


def test_params_strip_is_one_part_of_actions_and_turns(qapp, fusion, ini, tmp_path):
    """A2 の備え: 道具の列は 1 つの部品(objectName "panelStrip")で、道具 10 個は QAction(パネルにも載り、≡ から届く)。
    set_strip_side("left") で縦の 1 列(x が全部同じ・y が増える)が表の左に、"top" で横の 1 行(y が同じ・x が増える)が表の上に。"""
    win = _window(qapp, _three_files(tmp_path), size=(720, 420))
    p = win.panel
    assert _strips(p) == [p.strip_widget()] and p.strip_side() == "top"
    items = p.strip_actions()
    acts = [a for a in items if a is not None]
    assert len(acts) == len(BUTTONS) == 10 and items.count(None) == 3
    assert [p.tool_actions[k] for k in BUTTONS] == acts
    assert set(acts) <= set(p.actions())                                  # パネルに載る(キーと ≡ の一覧の元)
    for k in BUTTONS:
        a, b = p.tool_actions[k], p.buttons[k]
        assert a.text().strip() and a.toolTip().startswith(a.text()) and b.defaultAction() is a, k
        assert b.parent() is p.strip_widget() and b.accessibleName() == a.text(), k
    for side, want in (("left", "column"), ("top", "row"), ("left", "column")):
        assert p.set_strip_side(side) == side == p.strip_side()
        _pump(qapp)
        strip = p.strip_widget()
        pos = [p.buttons[k].mapTo(p, QtCore.QPoint(0, 0)) for k in BUTTONS]
        assert len(pos) == 10
        if want == "column":
            assert len({q.x() for q in pos}) == 1 and [q.y() for q in pos] == sorted(q.y() for q in pos)
            assert len({q.y() for q in pos}) == 10
            assert strip.mapTo(p, QtCore.QPoint(strip.width(), 0)).x() <= p.stack.geometry().left()
            assert strip.mapTo(p, QtCore.QPoint(0, 0)).y() <= p.stack.geometry().top()
        else:
            assert len({q.y() for q in pos}) == 1 and [q.x() for q in pos] == sorted(q.x() for q in pos)
            assert len({q.x() for q in pos}) == 10
            assert strip.mapTo(p, QtCore.QPoint(0, strip.height())).y() <= p.stack.geometry().top()
        assert p.search.isVisible() and p.search.mapTo(p, QtCore.QPoint(0, p.search.height())).y() <= p.stack.geometry().top()
        assert _strips(p) == [strip]
    with pytest.raises(ValueError):
        p.set_strip_side("right")
    assert p.strip_side() == "left"
    _close_quietly(win)


class _WrapStrip(QtWidgets.QWidget):
    """折り返す型の代役: 3 個ごとに次の段(横)/ 次の列(縦)。全部が見える。"""

    PER_LINE = 3

    def __init__(self):
        super().__init__()
        self.grid = QtWidgets.QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.orientation = Qt.Horizontal
        self.items: list = []
        self.made: dict = {}

    def set_actions(self, items):
        self.items = list(items)
        self._lay()

    def set_orientation(self, o):
        self.orientation = o
        self._lay()

    def _lay(self):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.made = {}
        for n, a in enumerate(x for x in self.items if x is not None):
            b = QtWidgets.QToolButton(self)
            b.setDefaultAction(a)
            line, at = divmod(n, self.PER_LINE)
            if self.orientation == Qt.Horizontal:
                self.grid.addWidget(b, line, at)
            else:
                self.grid.addWidget(b, at, line)
            self.made[a] = b

    def button_for(self, a):
        return self.made.get(a)


class _ScrollStrip(QtWidgets.QScrollArea):
    """送る型の代役: 既定の列を、ボタン 2 個分の長さのスクロールの窓に入れる(隠れた物は送って届く)。"""

    def __init__(self):
        super().__init__()
        self.inner = Q._ToolStrip()
        self.setWidget(self.inner)
        self.setWidgetResizable(False)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)       # 送りはボタンとホイールの役(棒は出さない)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.orientation = Qt.Horizontal

    def set_actions(self, items):
        self.inner.set_actions(items)
        self.inner.adjustSize()

    def set_orientation(self, o):
        self.orientation = o
        self.inner.set_orientation(o)
        self.inner.adjustSize()
        two = 2 * Q.BUTTON_PX + Q.GAP_PX
        if o == Qt.Horizontal:
            self.setFixedSize(two, Q.BUTTON_PX + 2)
        else:
            self.setFixedSize(Q.BUTTON_PX + 2, two)

    def button_for(self, a):
        return self.inner.button_for(a)


def _reached(strip, actions) -> int:
    """列の部品の中で、送り(スクロール)を使ってでも目に見える位置に出せたボタンの数。"""
    n = 0
    for a in actions:
        b = strip.button_for(a)
        if b is None:
            continue
        if isinstance(strip, QtWidgets.QScrollArea):
            strip.ensureWidgetVisible(b, 0, 0)
            QtWidgets.QApplication.processEvents()
            r = QtCore.QRect(b.mapTo(strip.viewport(), QtCore.QPoint(0, 0)), b.size())
            if strip.viewport().rect().contains(r):
                n += 1
        elif b.isVisible() and strip.rect().contains(QtCore.QRect(b.mapTo(strip, QtCore.QPoint(0, 0)), b.size())):
            n += 1
    return n


@pytest.mark.parametrize("kind", ["scroll", "wrap"])
def test_params_strip_can_be_replaced_by_scroll_or_wrap(qapp, fusion, ini, tmp_path, kind):
    """A2・A3 の備え: 列の部品を外の部品(送る型・折り返す型)に差し替えられる。差し替えた部品は同じ QAction 10 個を受け、
    objectName は "panelStrip"・パネルの中に 1 つだけ、横 / 縦のどちらでも 10 個全部に届く(数で)。状態(有効・押した)は
    QAction を通して差し替えた部品のボタンにも出る。約束を満たさない物は TypeError(黙って受けない)。"""
    win = _window(qapp, _three_files(tmp_path), size=(720, 420))
    p = win.panel
    old = p.strip_widget()
    strip = _ScrollStrip() if kind == "scroll" else _WrapStrip()
    p.set_strip_widget(strip)
    _pump(qapp)
    assert p.strip_widget() is strip and strip.objectName() == "panelStrip" and _strips(p) == [strip]
    assert old.parent() is None and not old.isVisible()
    acts = [a for a in p.strip_actions() if a is not None]
    assert len(acts) == 10 and [p.buttons[k] for k in BUTTONS] == [strip.button_for(a) for a in acts]
    for side, orient in (("top", Qt.Horizontal), ("left", Qt.Vertical), ("top", Qt.Horizontal)):
        p.set_strip_side(side)
        _pump(qapp)
        assert strip.orientation == orient
        assert _reached(strip, acts) == 10, (kind, side)
    assert not p.buttons["redo"].isEnabled() and not p.buttons["diff"].isChecked()
    assert p.edit_cell(0, "camera.fx", "900").ok
    p.undo()
    assert p.buttons["redo"].isEnabled()
    p.buttons["diff"].click()
    assert p.tmodel.diff_only and p.buttons["diff"].isChecked()
    with pytest.raises(TypeError):
        p.set_strip_widget(QtWidgets.QLabel("no"))
    assert p.strip_widget() is strip
    _close_quietly(win)


def _window_keys(win) -> list[str]:
    """窓の中の全部の QAction と QShortcut のキー(空でない物)。"""
    keys = []
    for a in win.findChildren(QtGui.QAction):
        keys += [k.toString() for k in a.shortcuts() if not k.isEmpty()]
    for sc in win.findChildren(QtGui.QShortcut):
        keys += [k.toString() for k in sc.keys() if not k.isEmpty()]
    return keys


def test_params_no_ctrl_d_binding(qapp, ini, tmp_path):
    """D90 / G13: 「違う行だけ」は帯のトグルだけ(Ctrl+D は Studio では「複製」。キーは [キー] の登録簿で決める)。
    窓の全部の QAction と QShortcut のキーを数え(7 個以上)、Ctrl+D が 0。キーが表に届く事を Ctrl+Z で確かめてから、
    Ctrl+D を押しても絞り込みが変わらない事を見る。トグルは押せば効く。"""
    win = _window(qapp, _three_files(tmp_path))
    p = win.panel
    win.activateWindow()
    keys = _window_keys(win)
    assert len(keys) >= 7 and {"Ctrl+O", "Ctrl+S", "Ctrl+Z", "Ctrl+Y", "Ctrl+F"} <= set(keys)
    assert [k for k in keys if k == "Ctrl+D"] == []
    diff = p.tool_actions["diff"]
    assert diff.shortcut().isEmpty() and "Ctrl+D" not in diff.toolTip() and diff.toolTip().startswith("Differences only")
    assert p.edit_cell(0, "camera.fx", "900").ok
    p.tree.setFocus()
    _pump(qapp)
    QTest.keyClick(p.tree, Qt.Key_Z, Qt.ControlModifier)                 # 届く事の対照
    assert p.model.value(0, "camera.fx") == 812.5 and p.message_label.full_text().startswith("undone:")
    QTest.keyClick(p.tree, Qt.Key_D, Qt.ControlModifier)
    _pump(qapp)
    assert not p.tmodel.diff_only and not diff.isChecked()
    p.buttons["diff"].click()
    assert p.tmodel.diff_only and diff.isChecked()
    _close_quietly(win)
