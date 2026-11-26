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
import sys

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


def test_every_message_is_translated_into_six_languages():
    """対訳の表: 画面の文の型は全部 6 言語(ja・zh・tw・ko・de・hi)に訳があり、% の並びが英語と同じ。使わない行は無い。
    理由だけを素通しにする型("%s")は無い(束の門の理由も UI の言語の文 + 括弧)。"""
    table = M.load_i18n_table()
    assert len(table) >= 128
    assert "Could not open %s (%s)" in table
    assert M.LANGS == ("en", "ja", "zh", "tw", "ko", "de", "hi")
    templates = list(M.MESSAGES.values())
    assert len(templates) == 45 and [t for t in templates if not re.search(r"[A-Za-z]{3}", t)] == []
    missing = [t for t in templates if t not in table]
    assert missing == []
    cells = 0
    for en, row in table.items():
        assert sorted(row) == sorted(M.LANGS[1:]), en
        for lang in M.LANGS[1:]:
            text = row.get(lang, "")
            assert text.strip(), (en, lang)
            assert _placeholders(text) == _placeholders(en), (en, lang, text)
            cells += 1
    assert cells == len(table) * 6
    # hi はデーヴァナーガリーで書いてある(英語の写しで埋めた行は無い)
    latin_only = [en for en, row in table.items() if not re.search("[\u0900-\u097f]", row["hi"])]
    assert latin_only == [], latin_only
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
    assert same == ["ja", "zh", "tw", "ko", "de", "hi"]


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

# 写し(確かめ用のコピー)で回す時の罠を止める: fullseye/__init__ は自分の木を sys.path の先頭に入れるので、写しの
# studio_params_model を読んだ後(それが fullseye を読む)の import は、作業木の studio_params_qt を黙って読む。そうなると
# 「直す前のコードで落ちる」を写しで確かめても、試験は作業木(直した後)のコードを回して緑になる(2026-11-15 の確かめで
# 実際に起きた: 3 failed / 12 passed、写しの ROOT を先頭へ戻すと 62 failed)。窓の 2 つのモジュールが、この試験と同じ木から
# 読まれていなければ、どの試験も回さずに止める(skip でなく収集の誤り)。
_WINDOW_TREES = {os.path.normcase(os.path.dirname(os.path.realpath(m.__file__))) for m in (M, Q)}
if _WINDOW_TREES != {os.path.normcase(os.path.realpath(ROOT))}:
    raise ImportError("the window modules were not read from this test's tree %s: studio_params_model=%s, "
                      "studio_params_qt=%s (another tree is earlier on sys.path)" % (ROOT, M.__file__, Q.__file__))

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
    assert p.message_level == "error"
    assert p.message_label.full_text() == "✕ camera.fx: this field holds a number; 'fast' is not a number — example: 820.0"
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


def _answer(app, label: str, log: list) -> dict:
    """次に出るモーダルの箱の ``label`` を押す。3 秒で箱を閉じて試験を失敗させる。

    Press ``label`` on the next modal box.  After three seconds, close every
    visible confirmation box and leave an explicit failure marker: a GUI test
    must never leave ``QMessageBox.exec()`` waiting without a bound.
    """
    state = {"tries": 0, "timed_out": False}

    def visible_boxes():
        return [widget for widget in app.topLevelWidgets()
                if isinstance(widget, QtWidgets.QMessageBox) and widget.isVisible()]

    def go():
        box = app.activeModalWidget()
        state["tries"] += 1
        if not isinstance(box, QtWidgets.QMessageBox):
            if state["tries"] < 300:
                QtCore.QTimer.singleShot(10, go)
            else:
                # 見つからない箱を待ち続けず、見えている確認を閉じて失敗を残す。
                # Never leave a nested event loop open when the expected box was not found.
                state["timed_out"] = True
                for visible in visible_boxes():
                    visible.reject()
            return
        hit = [b for b in box.buttons() if b.text() == label]
        log.append((box.text(), box.informativeText(), sorted(b.text() for b in box.buttons())))
        if hit:
            hit[0].click()
        else:
            box.reject()

    QtCore.QTimer.singleShot(0, go)
    return state


def test_the_three_question_boxes_ask_in_the_ui_language(qapp, ini, tmp_path):
    """聞く箱の既定(未保存・失われる物・外での変更): 押したボタンどおりの答えが返り、文とボタンは UI の言語。"""
    win = _window(qapp, [_write(tmp_path, "day.json", DAY)], lang="ja")
    p = win.panel
    tr = M.make_tr("ja")
    log: list = []
    answers = []
    guards = []
    for label, want in (("Save and close", "save"), ("Close without saving", "discard"), ("Cancel", "cancel")):
        guards.append(_answer(qapp, tr(label), log))
        answers.append(p._ask_unsaved_box(["day.json"]) == want)
    for label, want in (("Save anyway", True), ("Cancel", False)):
        guards.append(_answer(qapp, tr(label), log))
        answers.append(p._ask_losses_box("day.json", ["a", "b"]) is want)
    for label, want in (("Overwrite anyway", "overwrite"), ("Reload", "reload"), ("Cancel", "cancel")):
        guards.append(_answer(qapp, tr(label), log))
        answers.append(p._ask_overwrite_box("day.json", "changed") == want)
    assert not any(guard["timed_out"] for guard in guards), guards
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


@pytest.fixture(scope="module")
def fusion(qapp):
    """見た目と配置の門は Qt の様式を Fusion に固定して数える(設計書 P14-9)。

    module scope: ``setStyle`` は生きている全ウィジェットに様式を当て直す。試験ごとに往復させると、
    同じプロセスで先に走った試験のウィジェットの数だけ遅くなり、CI の shard が時間切れになった(2026-11-27)。
    すでに Fusion なら何もしない。"""
    before = qapp.style().name()
    changed = before.lower() != "fusion"
    if changed:
        qapp.setStyle("Fusion")
    yield qapp
    if changed:
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


def test_params_set_confirm_takes_the_parents_confirm_action(qapp, fusion, ini, tmp_path, monkeypatch):
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


def test_params_no_ctrl_d_binding(qapp, fusion, ini, tmp_path):
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


def _open_editor(qapp, p, col, key):
    idx = p.index_of(col, key)
    p.tree.setCurrentIndex(idx)
    p.tree.edit(idx)
    _pump(qapp)
    eds = [w for w in p.tree.viewport().findChildren(QtWidgets.QLineEdit) if w.isVisible()]
    assert len(eds) == 1, len(eds)
    return eds[0]


def test_params_rejected_cell_keeps_text_and_marks_invalid(qapp, fusion, ini, tmp_path):
    """D89 / G08: 表のセルで断った時は、打った文字を欄に残し(欄は開いたまま)、property "invalid" が真で赤枠、ツールヒントと
    状態の行に理由 + 例(今の値)。直して Enter で確定。Esc は取り消し。Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z が同じ行き来をする。"""
    win = _window(qapp, _three_files(tmp_path))
    p = win.panel
    win.activateWindow()
    cases = [(0, "camera.fx", "fast", "812.5"), (1, "optics.wavelength", "5 ms", "0.55 um"),
             (0, "camera.size", "640", "[640, 480]")]
    checked = 0
    for col, key, bad, now in cases:
        before = p.model.value(col, key)
        ed = _open_editor(qapp, p, col, key)
        ed.setText(bad)
        QTest.keyClick(ed, Qt.Key_Return)
        _pump(qapp)
        assert ed.isVisible() and ed.text() == bad and ed.property("invalid") is True, key
        assert "border" in ed.styleSheet() and p.model.value(col, key) == before, key
        assert p.message_level == "error" and ("example: " + now) in p.message_label.full_text(), key
        assert ed.toolTip() == p.message_label.full_text()[2:] and bad in ed.toolTip(), key
        QTest.keyClick(ed, Qt.Key_Escape)                               # 取り消し: 値はそのまま
        _pump(qapp)
        assert not ed.isVisible() and p.model.value(col, key) == before, key
        checked += 1
    assert checked == 3
    ed = _open_editor(qapp, p, 0, "camera.fx")
    ed.setText("fast")
    QTest.keyClick(ed, Qt.Key_Return)
    assert ed.property("invalid") is True
    ed.setText("820")                                                  # 直すと印が消え、Enter で確定する
    assert ed.property("invalid") is False and ed.styleSheet() == ""
    QTest.keyClick(ed, Qt.Key_Return)
    _pump(qapp)
    assert not ed.isVisible() and p.model.value(0, "camera.fx") == 820.0
    # 取り消し・やり直し: Ctrl+Z → 前、Ctrl+Y → 後、Ctrl+Z → 前、Ctrl+Shift+Z → 後
    p.tree.setFocus()
    seen = []
    for k, mod in ((Qt.Key_Z, Qt.ControlModifier), (Qt.Key_Y, Qt.ControlModifier), (Qt.Key_Z, Qt.ControlModifier),
                   (Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)):
        QTest.keyClick(p.tree, k, mod)
        _pump(qapp)
        seen.append(p.model.value(0, "camera.fx"))
    assert seen == [812.5, 820.0, 812.5, 820.0]
    redo = p.tool_actions["redo"]
    assert [k.toString() for k in redo.shortcuts()] == ["Ctrl+Y", "Ctrl+Shift+Z"]
    assert redo.toolTip().endswith("(Ctrl+Y)")                          # 表示は Ctrl+Y(設計書 P08-2)
    _close_quietly(win)


def _drop(p, mime) -> tuple[bool, bool]:
    """``mime`` を窓へ引き入れて落とす。(引き入れを受けたか, 落としを受けたか)。"""
    act = Qt.CopyAction
    enter = QtGui.QDragEnterEvent(QtCore.QPoint(10, 10), act, mime, Qt.LeftButton, Qt.NoModifier)
    enter.ignore()
    p.dragEnterEvent(enter)
    if not enter.isAccepted():
        return False, False
    drop = QtGui.QDropEvent(QtCore.QPointF(10, 10), act, mime, Qt.LeftButton, Qt.NoModifier)
    drop.ignore()
    p.dropEvent(drop)
    return True, drop.isAccepted()


def _mime(urls=(), text=None):
    m = QtCore.QMimeData()
    if urls:
        m.setUrls([u if isinstance(u, QtCore.QUrl) else QtCore.QUrl.fromLocalFile(u) for u in urls])
    if text is not None:
        m.setText(text)
    return m


def test_params_drop_reject_says_why(qapp, fusion, ini, tmp_path):
    """D91 / G12(c): 対象外の物(画像・フォルダ・ネットの URL・ただの文字)を落としても黙らず、下の行に理由(何が・開ける種類)。
    束のファイルと混ぜて落とせば、束は足し、対象外の物の理由を言う。どの言語でも訳がある。"""
    png = _raw(tmp_path, "photo.png", b"\x89PNG")
    folder = tmp_path / "rigs"
    folder.mkdir()
    day = _write(tmp_path, "day.json", DAY)
    win = _window(qapp, lang="ja")
    p = win.panel
    tr = M.make_tr("ja")
    kinds = tr("open .json, .toml, .yaml / .yml or .xml")
    cases = [
        ([png], None, [tr("not a parameter file: %s") % "photo.png"]),
        ([str(folder)], None, [tr("not a parameter file: %s") % "rigs"]),
        ([QtCore.QUrl("https://example.com/rig.json")], None, [tr("only files can be dropped here")]),
        ((), "camera.fx = 2", [tr("only files can be dropped here")]),
    ]
    seen = 0
    for urls, text, wants in cases:
        p.show_message("", "info")                                      # 前の場合の知らせを残さない(空で通さない)
        assert p.message_label.full_text() == "" and p.message_level == "info"
        assert _drop(p, _mime(urls, text)) == (True, True), (urls, text)
        msg = p.message_label.full_text()
        assert p.message_level == "warn" and msg.startswith("\u25b2 "), msg
        assert all(w in msg for w in wants) and kinds in msg, (msg, wants)
        assert p.model.columns == [], msg
        seen += 1
    assert seen == 4
    assert _drop(p, _mime([day, png])) == (True, True)                  # 混ぜて落とす: 束は足し、画像の理由を言う
    assert [c.name for c in p.model.columns] == ["day.json"]
    assert (tr("not a parameter file: %s") % "photo.png") in p.message_label.full_text()
    for en in ("not a parameter file: %s", "only files can be dropped here", "open .json, .toml, .yaml / .yml or .xml"):
        assert tr(en) != en
    _close_quietly(win)


def test_params_deferred_calls_do_not_outlive_the_window(qapp, fusion, ini, tmp_path):
    """直し(既存): 遅らせた呼び出し(列の幅の等分・表の作り直し・段と向きの組み替え・theme の読み直し)が、窓が消えた後に
    走らない。直す前は消えた表に触って RuntimeError か access violation(2 つ続けて窓を作る試験で数回に 1 回落ちた)。
    呼び出しを予約してから窓を消し、次の回で何も起きない事を、予約の種類ごとに数える。予約の書き方は構文木でも数える:
    QTimer.singleShot は全部「相手(self)つきの 3 引数」(相手が消えたら Qt が捨てる)。"""
    import shiboken6

    tree = ast.parse(io.open(os.path.join(ROOT, "studio_params_qt.py"), encoding="utf-8").read())
    shots = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "singleShot"]
    bare = [n.lineno for n in shots if not (len(n.args) == 3 and isinstance(n.args[1], ast.Name) and n.args[1].id == "self")]
    assert len(shots) >= 4 and bare == [], bare
    kinds = ("fit", "refresh", "replace", "theme")
    assert len(shots) == len(kinds)                                        # 予約が増えたら、下の種類も足す
    steps = 0
    for kind in kinds:
        d = tmp_path / kind
        d.mkdir()
        win = _window(qapp, _three_files(d))
        p = win.panel
        if kind == "fit":
            p._user_sized = False
            p._fit_pending = False
            vp = p.tree.viewport()
            p.eventFilter(vp, QtGui.QResizeEvent(vp.size(), vp.size()))     # 等分を次の回へ予約する
            assert p._fit_pending
        elif kind == "refresh":
            p._after_change(structure=True, deferred=True)                 # 作り直しを次の回へ予約する
        elif kind == "replace":
            p._replace_pending = False
            p._search_below = not p._search_below                          # 今の置き方が古い事にする
            p.resizeEvent(QtGui.QResizeEvent(p.size(), p.size()))          # 段の組み替えを次の回へ予約する
            assert p._replace_pending
        else:
            p._theme_pending = False
            p.changeEvent(QtCore.QEvent(QtCore.QEvent.StyleChange))        # theme の読み直しを次の回へ予約する
            assert p._theme_pending
        p.ask_unsaved = lambda names: "discard"
        win.hide()
        shiboken6.delete(win)                                              # 窓の C++ の側を今消す
        assert not shiboken6.isValid(p)
        _pump(qapp)                                                        # 予約した呼び出しは捨てられる(落ちない)
        steps += 1
    assert steps == 4


@pytest.mark.parametrize("lang", ["ja", "de", "en"])
def test_params_search_zero_hits_says_no_match(qapp, fusion, ini, tmp_path, lang):
    """D112 / G07(a): 330 px の窓でも検索の欄が切れない(置いた文字が全部見える幅・窓の内側)。合わない語では一覧の中に
    「該当なし: "語"」と次の一手(検索を消す)が出て、件数は「0 / 9 行」、前の知らせは消える。次の一手で元の 9 行に戻る。"""
    tr = M.make_tr(lang)
    win = _window(qapp, _three_files(tmp_path), lang=lang, size=(330, 300))
    p = win.panel
    _pump(qapp)
    s = p.search
    fm = s.fontMetrics()
    left = s.mapTo(p, QtCore.QPoint(0, 0)).x()
    assert s.isVisible() and left >= 0 and left + s.width() <= p.width() - 2, (lang, left, s.width(), p.width())
    assert s.width() >= fm.horizontalAdvance(s.placeholderText()) + 32, (lang, s.width())
    for k in BUTTONS:                                                   # 道具も切れない
        b = p.buttons[k]
        x = b.mapTo(p, QtCore.QPoint(0, 0)).x()
        assert b.isVisible() and 0 <= x and x + b.width() <= p.width() - 2, (lang, k)
    assert p.copy_column(0, 2).ok and p.message_label.full_text() != ""   # 古い知らせ
    s.setText("zzz")
    _pump(qapp)
    assert p.stack.currentWidget() is p.no_match and p.no_match.isVisible()
    assert p.no_match_label.text() == tr('No match: "%s"') % "zzz"
    assert p.no_match_button.text() == tr("Clear the search") and p.no_match_button.isVisible()
    assert p.counts_label.toolTip().startswith(tr("%d bundle(s)") % 3 + " · " + tr("%d of %d row(s)") % (0, 9))
    assert p.message_label.full_text() == ""                            # 古い知らせを残さない
    p.no_match_button.click()
    _pump(qapp)
    assert s.text() == "" and p.stack.currentWidget() is p.tree and len(_visible_keys(p)) == 9
    # 違う行だけで 0 行: 同じ場所に「束は違いません」と次の一手(全部の行を出す)。day と lab を同じにする。
    p.model.remove_column(1)
    p.refresh()
    assert [c.name for c in p.model.columns] == ["day.json", "lab.xml"]   # 上の写しで day と lab は同じ値
    p.set_diff_only(True)
    _pump(qapp)
    assert _visible_keys(p) == [] and p.stack.currentWidget() is p.no_match
    assert p.no_match_label.text() == tr("The bundles do not differ")
    assert p.no_match_button.text() == tr("Show every row")
    p.no_match_button.click()
    _pump(qapp)
    assert not p.tmodel.diff_only and p.stack.currentWidget() is p.tree and len(_visible_keys(p)) == 8
    _close_quietly(win)


def test_params_os_reason_goes_in_brackets_at_the_end(qapp, fusion, ini, tmp_path):
    """D112: 読み手・OS が返す英語の理由は、UI の言語の文の後ろに括弧で付ける(「x を開けません(<理由>)」)。"""
    win = _window(qapp, lang="ja")
    p = win.panel
    tr = M.make_tr("ja")
    outs = p.add_paths([str(tmp_path / "nope.json"), _raw(tmp_path, "bad.json", "{")])
    assert [o.ok for o in outs] == [False, False]
    msg = p.message_label.full_text()
    parts = [tr("Could not open %s (%s)") % (o.args[0], o.args[1]) for o in outs]
    assert msg == "\u2715 " + " | ".join(parts)
    assert parts[0].startswith("nope.json を開けません(") and parts[0].endswith(")")
    m = M.ParamsModel()
    assert M.MESSAGES["save.failed"].endswith("(%s)") and M.MESSAGES["load.refused"].endswith("(%s)")
    assert m.add_file(str(tmp_path / "nope.json")).text(tr).startswith("nope.json を開けません(")
    _close_quietly(win)
    # 束の門(値と節がぶつかる写し)が断った時も同じ形: UI の言語の文の後ろに、門の英語の理由を括弧で
    assert M.MESSAGES["edit.gate"].endswith("(%s)") and tr(M.MESSAGES["edit.gate"]) != M.MESSAGES["edit.gate"]
    win = _window(qapp, lang="ja")
    p = win.panel
    for name, data in (("flat", {"a": 1, "b": 2}), ("nested", {"a": {"x": 1}, "b": 2})):
        assert p.model.add_bundle(data, name).ok
    p.refresh()
    out = p.copy_cell("a", 0, 1)
    assert not out.ok and out.code == "edit.gate" and "both a value and a section" in out.reason
    msg = p.message_label.full_text()
    assert msg == "\u2715 " + tr(M.MESSAGES["edit.gate"]) % out.args and p.message_level == "error"
    assert msg.startswith("\u2715 束の決まりで") and msg.endswith(")") and "both a value and a section" in msg
    _close_quietly(win)


def test_params_compact_counts_keep_shown_of_all(qapp, fusion, ini, tmp_path):
    """D112 / G07(a): 狭い窓の短い数え方でも、絞っている時は「見えている行 / 全部の行」が出る(0 件なら 0 / 9)。"""
    win = _window(qapp, _three_files(tmp_path), size=(330, 300))
    p = win.panel
    assert p.counts_text(compact=True) == "3 bundle(s) · ≠ 4 · ◌ 1"
    p.search.setText("zzz")
    assert p.counts_text(compact=True) == "3 bundle(s) · 0 / 9 · ≠ 4 · ◌ 1"
    assert p.counts_label.text() in (p.counts_text(), p.counts_text(compact=True)) and "0" in p.counts_label.text()
    p.search.setText("EXPO")
    assert p.counts_text(compact=True).startswith("3 bundle(s) · 3 / 9 ·")
    _close_quietly(win)


def _window_texts(win) -> dict:
    """窓に出ている文を全部集める(題・道具の名前とツールヒント・読み上げの名前・検索・空の案内・見出し・数え方・知らせ・
    該当なし)。言語を切り替えた窓と、最初からその言語で作った窓を比べる。"""
    p = win.panel
    out = {"title": win.windowTitle(), "search.placeholder": p.search.placeholderText(),
           "search.tip": p.search.toolTip(), "search.name": p.search.accessibleName(),
           "empty": p.empty_label.text(), "empty.open": p.empty_open.text(), "empty.example": p.empty_example.text(),
           "empty.example.tip": p.empty_example.toolTip(), "counts": p.counts_label.text(),
           "counts.tip": p.counts_label.toolTip(), "message": p.message_label.full_text(),
           "no_match": p.no_match_label.text(), "no_match.button": p.no_match_button.text()}
    for k, a in p.tool_actions.items():
        out["action.%s.text" % k] = a.text()
        out["action.%s.tip" % k] = a.toolTip()
        out["button.%s.name" % k] = p.buttons[k].accessibleName()
    tm = p.tmodel
    for i in range(tm.columnCount()):
        out["header.%d" % i] = tm.headerData(i, Qt.Horizontal)
        out["header.%d.tip" % i] = tm.headerData(i, Qt.Horizontal, Qt.ToolTipRole)
    for key in ("camera.fx", "exposure.gain_db"):
        for c in range(3):
            out["cell.%s.%d.tip" % (key, c)] = p.index_of(c, key).data(Qt.ToolTipRole)
    out["every widget"] = _walk_texts(win)
    return out


def _walk_texts(win) -> list:
    """窓の木を全部歩いて集めた文(部品の文・ツールヒント・置いた文字・読み上げの名前・題・QAction の文とツールヒント)。
    手で並べた一覧に載っていない所(後から足した部品)も拾う。並びに頼らないよう「型.何=文」を整列した並びで返す。"""
    out = []
    for w in [win] + win.findChildren(QtWidgets.QWidget):
        for attr in ("text", "toolTip", "placeholderText", "accessibleName", "windowTitle", "statusTip", "whatsThis"):
            f = getattr(w, attr, None)
            if not callable(f):
                continue
            try:
                v = f()
            except TypeError:
                continue
            if isinstance(v, str) and v:
                out.append("%s.%s=%s" % (type(w).__name__, attr, v))
    for a in win.findChildren(QtGui.QAction):
        for attr in ("text", "toolTip", "statusTip", "whatsThis"):
            v = getattr(a, attr)()
            if v:
                out.append("QAction.%s=%s" % (attr, v))
    return sorted(out)


def _same_state(qapp, win, paths):
    p = win.panel
    assert p.copy_column(0, 2).ok                                         # 知らせ: 写した
    p.set_diff_only(True)
    p.search.setText("zzz")                                               # 該当なし
    _pump(qapp)
    assert p.stack.currentWidget() is p.no_match
    p.search.setText("")
    assert p.copy_column(1, 0).ok


def test_params_language_switch_rebuilds_every_text(qapp, fusion, ini, tmp_path):
    """D92 / G15: en で開いた窓を ja・de に切り替えると、窓の文が全部、最初からその言語で作った窓と同じになる(数えた文は
    50 以上)。知らせの行も作り直す。切り替えの前後で中身(列・絞り込み・未保存)は変わらない。"""
    paths = _three_files(tmp_path)
    win = _window(qapp, paths, lang="en")
    _same_state(qapp, win, paths)
    before_cols = [c.name for c in win.panel.model.columns]
    compared = 0
    for lang in ("ja", "de"):
        win.set_tr(M.make_tr(lang))
        _pump(qapp)
        got = _window_texts(win)
        fresh = _window(qapp, paths, lang=lang)
        _same_state(qapp, fresh, paths)
        want = _window_texts(fresh)
        assert len(want) >= 50 and sorted(got) == sorted(want)
        assert len(want["every widget"]) >= 70, len(want["every widget"])     # 窓の木を歩いて拾った文の数
        stale = sorted(set(got["every widget"]) ^ set(want["every widget"]))
        assert stale == [], (lang, stale)
        diff = {k: (got[k], want[k]) for k in want if got[k] != want[k]}
        assert diff == {}, (lang, diff)
        assert want["message"] and want["title"] != "Parameters — day.json, night.yaml *, lab.xml *"
        compared += len(want)
        _close_quietly(fresh)
    assert compared >= 100
    assert [c.name for c in win.panel.model.columns] == before_cols and win.panel.tmodel.diff_only
    assert win.panel.model.is_dirty()
    _close_quietly(win)


def test_params_colours_come_from_theme_roles(qapp, fusion, ini, tmp_path, monkeypatch):
    """D92 / P14-2: 状態の色(違うセルの地・注意・誤り・断った欄の枠)は studio_theme の役割(warn / err)から。theme が
    import できなければ今の色(琥珀 232,163,61・赤 217,83,79)。apply_theme() で読み直す。"""
    import sys
    import types

    fake = types.ModuleType("studio_theme")
    roles = {"warn": "#00c000", "err": "#0000f0"}
    fake.colour = lambda role: roles[role]
    seen = []
    for mod, warn, err in ((None, (232, 163, 61), (217, 83, 79)), (fake, (0, 192, 0), (0, 0, 240))):
        monkeypatch.setitem(sys.modules, "studio_theme", mod)
        assert Q._state_colour("warn").getRgb()[:3] == warn and Q._state_colour("err").getRgb()[:3] == err
        d = tmp_path / ("theme%d" % len(seen))
        d.mkdir()
        win = _window(qapp, _three_files(d))
        p = win.panel
        base = p.palette().color(QtGui.QPalette.Base)
        want = Q._mix(base, QtGui.QColor(*warn), 0.30)
        brush = p.index_of(0, "camera.fx").data(Qt.BackgroundRole)
        assert brush.color().getRgb()[:3] == want.getRgb()[:3]
        text = p.palette().color(QtGui.QPalette.WindowText)
        p.show_message("x", "error")
        tone = p.message_label.palette().color(QtGui.QPalette.WindowText)
        assert tone.getRgb()[:3] == Q._mix(text, QtGui.QColor(*err), 0.7).getRgb()[:3]
        p.show_message("x", "warn")                                     # ▲ の知らせ = warn の役割
        tone = p.message_label.palette().color(QtGui.QPalette.WindowText)
        assert tone.getRgb()[:3] == Q._mix(text, QtGui.QColor(*warn), 0.6).getRgb()[:3]
        assert "rgb(%d, %d, %d)" % tone.getRgb()[:3] in p.message_label.styleSheet()
        p.show_message("x", "info")                                     # 印なしは本文の色(状態の色を付けない)
        assert p.message_label.palette().color(QtGui.QPalette.WindowText).getRgb()[:3] == text.getRgb()[:3]
        assert p.message_label.styleSheet() == ""
        win.activateWindow()
        ed = _start_edit(qapp, p, "fast")                               # 断った欄の枠 = err の役割
        QTest.keyClick(ed, Qt.Key_Return)
        assert ed.property("invalid") is True and ("border: 1px solid rgb(%d, %d, %d)" % err) in ed.styleSheet()
        QTest.keyClick(ed, Qt.Key_Escape)
        seen.append(brush.color().getRgb()[:3])
        _close_quietly(win)
    assert len(seen) == 2 and seen[0] != seen[1]
    # 窓を作った後に theme が変わったら apply_theme で読み直す
    monkeypatch.setitem(sys.modules, "studio_theme", None)
    d = tmp_path / "late"
    d.mkdir()
    win = _window(qapp, _three_files(d))
    p = win.panel
    old = p.index_of(0, "camera.fx").data(Qt.BackgroundRole).color().getRgb()[:3]
    p.show_message("x", "warn")                                         # 出ている知らせの色も読み直される
    text = p.palette().color(QtGui.QPalette.WindowText)
    before = p.message_label.palette().color(QtGui.QPalette.WindowText).getRgb()[:3]
    assert before == Q._mix(text, QtGui.QColor(232, 163, 61), 0.6).getRgb()[:3]
    monkeypatch.setitem(sys.modules, "studio_theme", fake)
    p.apply_theme()
    new = p.index_of(0, "camera.fx").data(Qt.BackgroundRole).color().getRgb()[:3]
    assert old != new == Q._mix(p.palette().color(QtGui.QPalette.Base), QtGui.QColor(0, 192, 0), 0.30).getRgb()[:3]
    after = p.message_label.palette().color(QtGui.QPalette.WindowText).getRgb()[:3]
    assert before != after == Q._mix(text, QtGui.QColor(0, 192, 0), 0.6).getRgb()[:3]
    assert "rgb(%d, %d, %d)" % after in p.message_label.styleSheet()
    _close_quietly(win)


# ============================================================================================== #
# 確かめの担当 2 人の指摘(2026-11-15)の門: 本物の theme の下・フォーカス・狭い窓・窓の木の全部を歩く
# ============================================================================================== #
import sys  # noqa: E402
import types  # noqa: E402

#: 見た目の枝(B1 の studio_theme)の役割の色のうち、この窓が使う物(instrument = 暗い配色、panel = 明るい配色)。
_THEME_ROLES = {
    "instrument": {"bg0": "#1a1d22", "bg1": "#20242a", "bg2": "#272c33", "line": "#363c45", "text": "#e4e7eb",
                   "warn": "#e8b04a", "err": "#f0646a", "off": "#7d8590"},
    "panel": {"bg0": "#dfe2e6", "bg1": "#eceef1", "bg2": "#ffffff", "line": "#a9b0b9", "text": "#15191e",
              "warn": "#8a5a00", "err": "#b3261e", "off": "#646c76"},
}


def _theme_qss(name: str) -> str:
    """studio_theme.build_qss の決まりのうち、この窓に効く物の写し(QToolButton の余白と iconOnly、QLabel の色、無効の色)。"""
    return ("QWidget { background:%(bg0)s; color:%(text)s; }\n"
            "QLabel { color:%(text)s; background:transparent; }\n"
            "QToolButton { background:%(bg2)s; border:1px solid %(line)s; border-radius:3px; padding:2px 8px; "
            "color:%(text)s; }\n"
            'QToolButton[iconOnly="true"] { padding:3px; }\n'
            "QToolButton:disabled { background:%(bg1)s; border:1px solid %(line)s; color:%(off)s; }\n"
            "QPushButton { background:%(bg2)s; border:1px solid %(line)s; border-radius:3px; padding:3px 10px; "
            "color:%(text)s; }\n"
            "QLineEdit { background:%(bg2)s; border:1px solid %(line)s; border-radius:3px; padding:0px 6px; }\n"
            % _THEME_ROLES[name])


@pytest.fixture(params=["stand-in", "studio_theme"])
def themed(request, monkeypatch):
    """(配色を選んで QSS を返す関数, 配色 → 役割の色の表)。stand-in = 上の写し + 偽の studio_theme(どの木でも回る)、
    studio_theme = 本物の build_qss(見た目の枝が入った木だけ。この木には無いので理由つきで skip)。"""
    if request.param == "stand-in":
        state = {"name": "instrument"}
        fake = types.ModuleType("studio_theme")
        fake.colour = lambda role: _THEME_ROLES[state["name"]][role]
        monkeypatch.setitem(sys.modules, "studio_theme", fake)

        def choose(name):
            state["name"] = name
            return _theme_qss(name)

        return choose, (lambda name: _THEME_ROLES[name])
    st = pytest.importorskip("studio_theme", reason="the look branch (studio_theme) is not in this tree")
    before = st.current_name()
    request.addfinalizer(lambda: st.set_current(theme=before))

    def choose(name):
        st.set_current(theme=name)
        return st.build_qss(name, "en", None, 16)

    return choose, (lambda name: st.PALETTES[name])


def _rect_in(w, anc) -> QtCore.QRect:
    return QtCore.QRect(w.mapTo(anc, QtCore.QPoint(0, 0)), w.size())


def _lum(c) -> float:
    def lin(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(c.red()) + 0.7152 * lin(c.green()) + 0.0722 * lin(c.blue())


def _contrast(a, b) -> float:
    la, lb = _lum(QtGui.QColor(a)), _lum(QtGui.QColor(b))
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


#: 描かれた字の色の許容: 地 -> 役割の色の距離に対する割合。字の画素が完全に塗られない(縁のにじみ)ので
#: 一番遠い画素も少し地へ寄る。Linux(Noto、灰色の antialias)では 5.6 % 寄った(2026-11-23 実測、絶対の 24 を超えた)。
NOTICE_INK_TOLERANCE_FRACTION = 0.10
#: 上の割合で決まる許容の下限(従来の絶対の値)
NOTICE_INK_TOLERANCE_MIN = 24


def _far(a, b) -> int:
    a, b = QtGui.QColor(a), QtGui.QColor(b)
    return abs(a.red() - b.red()) + abs(a.green() - b.green()) + abs(a.blue() - b.blue())


def _ink(img, rect, margin: int = 2):
    """``rect`` の中で、地の色(いちばん多い色)から遠い画素の外接の (幅, 高さ, いちばん遠い色, 地の色)。描かれた物が無ければ幅 0。"""
    span = [(x, y) for x in range(rect.left() + margin, rect.right() - margin + 1)
            for y in range(rect.top() + margin, rect.bottom() - margin + 1)]
    count: dict[int, int] = {}
    for x, y in span:
        v = img.pixel(x, y)
        count[v] = count.get(v, 0) + 1
    ground = QtGui.QColor(max(count, key=lambda v: count[v]))
    xs, ys, far, best = [], [], -1, ground
    for x, y in span:
        c = QtGui.QColor(img.pixel(x, y))
        d = _far(c, ground)
        if d > 60:
            xs.append(x)
            ys.append(y)
        if d > far:
            far, best = d, c
    if not xs:
        return 0, 0, best, ground
    return max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, best, ground


_DIFF_KEYS = ("camera.fx", "optics.f_number", "exposure.mode")


def _theme_cells_and_icons(qapp, win, roles) -> int:
    """theme の下の窓を数える(数えた物の数を返す): 違うセルの地と字・道具の絵(押せる / 押せない)。書体に頼らない。"""
    p = win.panel
    text = QtGui.QColor(roles["text"])
    counted = 0
    # 違うセル: 地 = 表の地に warn を 3 割、字とのコントラスト 4.5 以上。描かれた地の画素も同じ色。
    base = p.tree.palette().color(QtGui.QPalette.Base)
    assert _far(base, roles["bg0"]) <= 3, (base.name(), roles["bg0"])
    want = Q._mix(base, QtGui.QColor(roles["warn"]), 0.30)
    img = win.grab().toImage()
    for key in _DIFF_KEYS:
        for col in range(3):
            idx = p.index_of(col, key)
            brush = idx.data(Qt.BackgroundRole).color()
            assert _far(brush, want) <= 3, (key, col, brush.name(), want.name())
            assert _contrast(text, brush) >= 4.5, (key, col, brush.name(), _contrast(text, brush))
            r = p.tree.visualRect(idx)
            at = p.tree.viewport().mapTo(win, QtCore.QPoint(r.right() - 1, r.bottom() - 1))
            assert _far(QtGui.QColor(img.pixel(at)), brush) <= 6, (key, col, QtGui.QColor(img.pixel(at)).name())
            counted += 1
    # 道具の絵: 押せる時は長い辺 10 px 以上で地から浮く。押せない時は off の色(押せる時より沈み、それでも見える)。
    seen = {}
    for state in (True, False):
        for k in BUTTONS:
            p.tool_actions[k].setEnabled(state)
        _pump(qapp)
        img = win.grab().toImage()
        for k in BUTTONS:
            b = p.buttons[k]
            assert b.property("iconOnly") is True and (b.width(), b.height()) == (24, 24), k
            w, h, ink, ground = _ink(img, _rect_in(b, win))
            assert max(w, h) >= 10 and min(w, h) >= 6, (k, state, w, h)
            seen[(k, state)] = _contrast(ink, ground)
            counted += 1
    for k in BUTTONS:
        on, off = seen[(k, True)], seen[(k, False)]
        assert on >= 4.5 and 2.0 <= off <= on / 1.5, (k, on, off)
    p._update_actions()
    return counted


def _theme_notice(qapp, win, roles) -> int:
    """知らせの字の**描かれた**色: ▲ / ✕ は役割の色を混ぜた色(本文の色のままではない)、印なしは本文の色。字の画素を読む。"""
    p = win.panel
    text = QtGui.QColor(roles["text"])
    counted = 0
    body = p.palette().color(QtGui.QPalette.WindowText)
    assert _far(body, text) <= 3
    for level, role, t in (("warn", "warn", 0.6), ("error", "err", 0.7), ("info", None, 0.0)):
        p.show_message("xxxxxxxx", level)
        _pump(qapp)
        tone = Q._mix(body, QtGui.QColor(roles[role]), t) if role else body
        ml = p.message_label
        assert ml.isVisible() and _far(ml.palette().color(QtGui.QPalette.WindowText), tone) <= 3, level
        w, _h, ink, ground = _ink(win.grab().toImage(), _rect_in(ml, win), 0)
        if w == 0:                                    # 字を描ける書体が無い環境(字の画素が無い)
            pytest.skip("no font draws text on this platform: the painted colour of the notice cannot be read")
        allowed = max(NOTICE_INK_TOLERANCE_MIN, int(NOTICE_INK_TOLERANCE_FRACTION * _far(ground, tone)))
        assert _far(ink, tone) <= allowed, (level, ink.name(), tone.name(), allowed)
        if role:
            assert _far(ink, body) >= 60, (level, ink.name(), body.name())
        counted += 1
    p.show_message("", "info")
    return counted


def _open_under_theme(qapp, tmp_path, qss: str):
    """theme の QSS を当てた親(Studio の代わり)から、Studio と同じ入口 show_params_window で開く。"""
    parent = QtWidgets.QMainWindow()
    parent.setStyleSheet(qss)
    parent.resize(900, 600)
    parent.show()
    _pump(qapp)
    win = Q.show_params_window(parent, _three_files(tmp_path), M.make_tr("en"))
    win.resize(720, 360)
    _pump(qapp)
    return parent, win


def test_params_opened_under_a_theme_is_readable(qapp, fusion, ini, tmp_path, themed):
    """確かめの指摘(high): theme の QSS を当てた親(Studio)から show_params_window で開いた**直後**に、違う行の値が読め
    (地と字のコントラスト 4.5 以上)、道具 10 個の絵が潰れず(長い辺 10 px 以上)、押せない絵は off の色で沈む。
    apply_theme() を外から呼ばない。親の QSS を別の配色に差し替えても(theme の切り替え)パネルが自分で読み直す。"""
    choose, roles = themed
    parent, win = _open_under_theme(qapp, tmp_path, choose("instrument"))
    counted = _theme_cells_and_icons(qapp, win, roles("instrument"))
    dark = win.panel.index_of(0, "camera.fx").data(Qt.BackgroundRole).color().name()
    parent.setStyleSheet(choose("panel"))                               # theme の切り替え(apply_theme は呼ばない)
    _pump(qapp)
    counted += _theme_cells_and_icons(qapp, win, roles("panel"))
    assert win.panel.index_of(0, "camera.fx").data(Qt.BackgroundRole).color().name() != dark
    assert counted == 2 * (9 + 20)
    _close_quietly(win)
    parent.close()
    parent.deleteLater()


def test_params_notice_is_painted_in_the_state_colour_under_a_theme(qapp, fusion, ini, tmp_path, themed):
    """確かめの指摘(medium): theme の QSS(QLabel { color })の下でも、▲ / ✕ の知らせの字が役割の色で**描かれる**
    (パレットに入れただけでは QSS に負けて本文の色になる)。字の画素を読むので、字を描ける書体が無い環境では skip。"""
    choose, roles = themed
    parent, win = _open_under_theme(qapp, tmp_path, choose("instrument"))
    counted = _theme_notice(qapp, win, roles("instrument"))
    parent.setStyleSheet(choose("panel"))
    _pump(qapp)
    counted += _theme_notice(qapp, win, roles("panel"))
    assert counted == 2 * 3
    _close_quietly(win)
    parent.close()
    parent.deleteLater()


def _start_edit(qapp, p, text: str, col: int = 0, key: str = "camera.fx"):
    """セルの編集を始めて、欄に ``text`` を入れる(まだ確定しない)。"""
    ed = _open_editor(qapp, p, col, key)
    ed.setFocus()
    ed.setText(text)
    return ed


def _held(p) -> list:
    """表の中で開いている編集の欄(閉じて消されるのを待っている物は数えない)。"""
    return [w for w in p.tree.viewport().findChildren(QtWidgets.QLineEdit) if not w.isHidden()]


@pytest.mark.parametrize("how", ["enter", "tab", "shift+tab", "click another cell", "focus to the search",
                                 "another window"])
def test_params_rejected_cell_stays_whatever_ends_the_edit(qapp, fusion, ini, tmp_path, how):
    """D89(確かめの指摘): 断った欄は、確定を試みる道がどれでも閉じない。Enter・Tab・Shift+Tab(確定キー)だけでなく、
    他のセルを押す・検索の欄へフォーカスを移す・別の窓へ移る(欄からフォーカスが外れる)でも、欄は開いたまま、打った文字と
    赤枠(property invalid)と理由 + 例が残り、値は変わらない。Esc で取り消せる。"""
    import shiboken6

    win = _window(qapp, _three_files(tmp_path))
    p = win.panel
    win.activateWindow()
    ed = _start_edit(qapp, p, "fast")
    other = None
    if how == "enter":
        QTest.keyClick(ed, Qt.Key_Return)
    elif how == "tab":
        QTest.keyClick(ed, Qt.Key_Tab)
    elif how == "shift+tab":
        QTest.keyClick(ed, Qt.Key_Backtab, Qt.ShiftModifier)
    elif how == "click another cell":
        at = p.tree.visualRect(p.index_of(1, "camera.fy")).center()
        QTest.mouseClick(p.tree.viewport(), Qt.LeftButton, Qt.NoModifier, at)
    elif how == "focus to the search":
        p.search.setFocus(Qt.MouseFocusReason)
    else:
        other = QtWidgets.QWidget()
        other.show()
        other.activateWindow()
        other.setFocus()
    _pump(qapp)
    assert shiboken6.isValid(ed) and _held(p) == [ed], how
    assert ed.isVisible() and ed.text() == "fast" and ed.property("invalid") is True, how
    assert "border" in ed.styleSheet() and p.model.value(0, "camera.fx") == 812.5, how
    assert p.message_level == "error" and ed.toolTip() == p.message_label.full_text()[2:], how
    assert "'fast'" in ed.toolTip() and "example: 812.5" in ed.toolTip(), how
    if how == "click another cell":
        assert p.current_cell() == (1, "camera.fy")                    # 選択は動く。欄は残る
    elif how == "focus to the search":
        assert qapp.focusWidget() is p.search
    ed.setFocus()
    QTest.keyClick(ed, Qt.Key_Escape)                                   # 取り消し: 欄は閉じ、値はそのまま
    _pump(qapp)
    assert _held(p) == [] and p.model.value(0, "camera.fx") == 812.5 and win.isVisible(), how
    if other is not None:
        other.close()
        other.deleteLater()
    _close_quietly(win)


def test_params_rejected_cell_survives_redraw_and_is_resolved_first(qapp, fusion, ini, tmp_path):
    """D89 の続き: 断って残った欄は、表の描き直し(チェックの切り替え・実行の印・theme の読み直し)で文字を失わない。
    残っている間に他のセルを編集しようとすると(編集の開始・ダブルクリック)、2 つ目の欄は開かず、断った欄へフォーカスが戻る。
    表にフォーカスがある時の Esc は、まず断った欄を取り消し(窓は閉じない)、次の Esc で窓が閉じる。直してフォーカスを
    外せば確定して閉じる。打っている途中の文字も描き直しで消えない。"""
    win = _window(qapp, _three_files(tmp_path))
    p = win.panel
    p.ask_unsaved = lambda names: "discard"
    win.activateWindow()
    ed = _start_edit(qapp, p, "fast")
    p.search.setFocus(Qt.MouseFocusReason)
    _pump(qapp)
    assert _held(p) == [ed] and ed.property("invalid") is True
    redraws = 0
    assert p.tmodel.setData(p.index_of(0, "exposure.auto"), Qt.Unchecked, Qt.CheckStateRole)   # 他のセルが変わる
    redraws += 1
    p.mark_used(["camera.fx"], 0)                                       # 実行の印
    redraws += 1
    p.apply_theme()                                                     # theme の読み直し
    redraws += 1
    _pump(qapp)
    assert redraws == 3 and p.model.value(0, "exposure.auto") is False
    assert _held(p) == [ed] and ed.text() == "fast" and ed.property("invalid") is True
    other = p.index_of(2, "camera.cx")
    tried = 0
    p.tree.setFocus()
    p.tree.setCurrentIndex(other)
    p.tree.edit(other)                                                  # 編集の開始(F2・打ち始めと同じ入口)
    _pump(qapp)
    assert _held(p) == [ed] and qapp.focusWidget() is ed and ed.text() == "fast"
    tried += 1
    p.tree.setFocus()
    QTest.mouseDClick(p.tree.viewport(), Qt.LeftButton, Qt.NoModifier, p.tree.visualRect(other).center())
    _pump(qapp)
    assert _held(p) == [ed] and qapp.focusWidget() is ed and ed.text() == "fast"
    tried += 1
    assert tried == 2
    p.tree.setFocus()
    QTest.keyClick(p.tree, Qt.Key_Escape)                               # Esc の 1 段目: 断った欄を取り消す
    _pump(qapp)
    assert win.isVisible() and _held(p) == [] and p.model.value(0, "camera.fx") == 812.5
    ed2 = _open_editor(qapp, p, 2, "camera.cx")                         # 取り消した後は他のセルを編集できる
    assert ed2.text() == "320"
    ed2.setText("32")                                                   # 打っている途中(まだ確定していない)
    p.apply_theme()
    _pump(qapp)
    assert ed2.text() == "32" and p.model.value(2, "camera.cx") == 320
    QTest.keyClick(ed2, Qt.Key_Escape)
    _pump(qapp)
    assert _held(p) == [] and p.model.value(2, "camera.cx") == 320
    ed = _start_edit(qapp, p, "fast")                                   # 直してフォーカスを外すと確定して閉じる
    p.search.setFocus(Qt.MouseFocusReason)
    _pump(qapp)
    assert _held(p) == [ed] and ed.property("invalid") is True
    ed.setFocus()
    ed.setText("820")
    assert ed.property("invalid") is False
    p.search.setFocus(Qt.MouseFocusReason)
    _pump(qapp)
    assert _held(p) == [] and p.model.value(0, "camera.fx") == 820.0
    p.tree.setFocus()
    QTest.keyClick(p.tree, Qt.Key_Escape)                               # 残っている欄が無ければ、Esc は窓を閉じる
    _pump(qapp)
    assert not win.isVisible()


#: Studio の i18n.json の strings が知っている、束の窓の文(9 行だけ。studio.tr はこの表しか引かない)。
_STUDIO_KNOWS = ("Parameters", "Open", "Save", "Cancel", "Close", "Open the example", "read-only", "saved %s",
                 "not saved to a file yet")


def _studio_like_tr(lang: str):
    """Studio の tr の代役: Studio の i18n.json の strings だけを引く(束の対訳の表は知らない)。"""
    with io.open(os.path.join(ROOT, "studio_assets", "i18n.json"), encoding="utf-8") as fh:
        strings = json.load(fh)["strings"]
    assert all(k in strings for k in _STUDIO_KNOWS)

    def tr(text):
        return text if lang == "en" or not text else strings.get(text, {}).get(lang, text)

    return tr


@pytest.mark.parametrize("lang", ["ja", "hi", "de"])
def test_params_studio_entry_speaks_the_ui_language(qapp, fusion, ini, tmp_path, lang):
    """D87 の引き継ぎ(確かめの指摘): Studio は言語コードを ``lang=`` で渡して開く。Studio の tr は束の文を 9 行しか
    知らないので、tr だけを渡した窓はほぼ英語になる(その事も数える)。``lang=`` で開いた窓は、その言語で作った窓と全部の文が
    同じで、英語の窓と違う文が 45 以上。言語の切り替えは set_lang、既にある窓は入口が切り替える。知らない言語でも落ちない。"""
    paths = _three_files(tmp_path)
    host = _studio_like_tr(lang)
    english = _window(qapp, paths, lang="en")
    _same_state(qapp, english, paths)
    en = _window_texts(english)
    _close_quietly(english)
    fresh = _window(qapp, paths, lang=lang)
    _same_state(qapp, fresh, paths)
    want = _window_texts(fresh)
    _close_quietly(fresh)
    translated = [k for k in want if want[k] != en[k]]
    assert len(want) >= 55 and len(translated) >= 45, (lang, len(want), len(translated))
    # 対照: Studio の tr だけを渡した窓(引き継ぎの前の文どおり)は、ほとんど英語のまま
    bare = Q.ParamsWindow(None, host)
    bare.resize(720, 420)
    bare.panel.add_paths(paths)
    bare.show()
    _pump(qapp)
    _same_state(qapp, bare, paths)
    got = _window_texts(bare)
    assert len([k for k in got if got[k] != en[k]]) <= len(translated) // 2
    _close_quietly(bare)
    # 入口: lang= で開く(tr は Studio の tr のまま渡してよい)
    parent = QtWidgets.QWidget()
    win = Q.show_params_window(parent, paths, host, lang=lang)
    win.resize(720, 420)
    _pump(qapp)
    _same_state(qapp, win, paths)
    got = _window_texts(win)
    assert {k: (got[k], want[k]) for k in want if got[k] != want[k]} == {} and sorted(got) == sorted(want)
    # 言語の切り替え: set_lang。en → 全部英語、もう一度その言語 → 全部戻る
    win.set_lang("en")
    _pump(qapp)
    back = _window_texts(win)
    assert {k: (back[k], en[k]) for k in en if back[k] != en[k]} == {}
    assert Q.show_params_window(parent, (), host, lang=lang) is win       # 既にある窓: 入口が言語を切り替える
    _pump(qapp)
    again = _window_texts(win)
    assert {k: (again[k], want[k]) for k in want if again[k] != want[k]} == {}
    _close_quietly(win)
    parent.deleteLater()
    # 束の表が持たない言語(Studio が後から足した言語): 落ちずに開き、束の文は英語。表にある言語へ切り替えれば訳される
    other = Q.ParamsWindow(None, _studio_like_tr("xx"), lang="xx")
    assert other.windowTitle() == "Parameters" and other.panel.search.placeholderText() == "Search keys"
    other.set_lang(lang)
    assert other.panel.search.placeholderText() == M.make_tr(lang)("Search keys") != "Search keys"
    _close_quietly(other)
    # 束の表に無い文は fallback(Studio の tr)へ。fallback が無い時、知らない言語は断る(前からの決まり)
    seen = []
    tr = M.make_tr(lang, fallback=lambda s: (seen.append(s), "<" + s + ">")[1])
    assert tr("Search keys") == M.make_tr(lang)("Search keys") != "Search keys" and seen == []
    assert tr("a text of Studio") == "<a text of Studio>" and seen == ["a text of Studio"] and tr("") == ""
    assert M.make_tr("xx", fallback=lambda s: s.upper())("Search keys") == "SEARCH KEYS"
    with pytest.raises(ValueError):
        M.make_tr("xx")


def _notice(p):
    """状態の行で今見えている知らせのラベル(折り返した行か、1 行のラベル)。"""
    return p.message_wrap if not p.message_wrap.isHidden() else p.message_label


@pytest.mark.parametrize("lang", ["ja", "en", "de"])
def test_params_refusal_reason_is_readable_in_a_narrow_window(qapp, fusion, ini, tmp_path, lang):
    """確かめの指摘(medium): 330 px の窓でも、断りの理由が下の行で全部読める。直す前は数え方が幅を取り、知らせは
    「▲ パラメータのフ…」(79 字のうち 9 字)だった。落とした物の断り(理由が出るのは下の行だけ)はファイル名と開ける種類、
    セルの断りは理由と例が、省略されずに見えている(折り返した行は切れず、窓の内側にあり、表も残る)。知らせが消えれば
    1 行へ戻る。印なしの知らせは 1 行のまま。広い窓では折り返さない。"""
    tr = M.make_tr(lang)
    png = _raw(tmp_path, "photo.png", b"\x89PNG")
    win = _window(qapp, _three_files(tmp_path), lang=lang, size=(330, 300))
    p = win.panel
    row = p.row_height()
    assert p.status.height() == row and p.message_wrap.isHidden()
    read = 0
    # 落とした物の断り
    assert _drop(p, _mime([png])) == (True, True)
    _pump(qapp)
    full = p.message_label.full_text()
    assert p.message_level == "warn" and full.startswith("\u25b2 ")
    for want in (full, "photo.png", tr("open .json, .toml, .yaml / .yml or .xml")):
        assert want in p.message_shown(), (lang, want, p.message_shown())
        read += 1
    lab = _notice(p)
    assert lab is p.message_wrap and lab.isVisible() and lab.text() == full and lab.toolTip() == full
    assert lab.height() >= lab.heightForWidth(lab.width()) > 0, (lang, lab.height(), lab.width())   # 折り返した行が切れていない
    assert lab.height() >= 2 * lab.fontMetrics().lineSpacing()                                      # 1 行には入らない長さ
    assert win.rect().contains(_rect_in(lab, win)) and win.rect().contains(_rect_in(p.counts_label, win))
    assert p.status.height() == row + lab.height() and p.height() - p.status.geometry().bottom() - 1 == 2
    assert p.stack.height() >= 4 * row and p.counts_label.isVisible()                               # 表も数え方も残る
    tall = p.status.height()
    # セルの断り(欄で断った時と同じ文: 理由 + 例)。前の知らせより短ければ、行の高さも戻る
    ed = _start_edit(qapp, p, "fast")
    QTest.keyClick(ed, Qt.Key_Return)
    _pump(qapp)
    full = p.message_label.full_text()
    assert p.message_level == "error" and full.startswith("\u2715 ") and (tr("example: %s") % "812.5") in full
    for want in (full, "'fast'", tr("example: %s") % "812.5"):
        assert want in p.message_shown(), (lang, want, p.message_shown())
        read += 1
    lab = _notice(p)
    assert lab.height() >= lab.heightForWidth(lab.width()) > 0 and win.rect().contains(_rect_in(lab, win))
    assert row < p.status.height() <= tall and p.status.height() == row + lab.height()
    QTest.keyClick(ed, Qt.Key_Escape)
    assert read == 6
    # 折り返しても 1 行で済む長さの知らせ: 前の知らせ(2 行以上)の高さを引きずらず、1 行分になる
    fm = p.message_wrap.fontMetrics()
    one = "x" * max(1, (p.status.width() - 4 - 30) // max(1, fm.horizontalAdvance("x")) - 2)
    p.show_message(one, "warn")
    _pump(qapp)
    lab = _notice(p)
    assert lab is p.message_wrap and lab.text() == "\u25b2 " + one
    assert lab.heightForWidth(lab.width()) <= lab.height() < 2 * fm.lineSpacing(), (lang, lab.height(), fm.lineSpacing())
    assert p.status.height() == row + lab.height() < tall
    # 知らせが消えると 1 行へ戻る(隠れたラベルに前の文を残さない)。印なしの知らせ(済んだ事)は 1 行のまま(省略 + ツールヒント)
    p.show_message("", "info")
    _pump(qapp)
    assert p.status.height() == row and p.message_wrap.isHidden() and p.message_shown() == ""
    assert p.message_wrap.text() == "" and p.message_wrap.toolTip() == ""
    p.show_message("saved " + "x" * 200, "info")
    _pump(qapp)
    assert p.status.height() == row and p.message_wrap.isHidden() and p.message_label.isVisible()
    assert p.message_shown().endswith("\u2026") and p.message_label.toolTip() == "saved " + "x" * 200
    # 知らせを出したまま窓を広げる(幅は書体から出す。窓の幅 = 状態の行の内側 + 8 px)
    assert _drop(p, _mime([png])) == (True, True)
    _pump(qapp)
    assert not p.message_wrap.isHidden() and p.status.height() > row
    fm = p.counts_label.fontMetrics()
    need = p.message_label.fontMetrics().horizontalAdvance(p.message_label.full_text()) + 4
    long_w, short_w = fm.horizontalAdvance(p.counts_text()), fm.horizontalAdvance(p.counts_text(compact=True))
    assert long_w - short_w > 8
    # 広い窓: 折り返さずに 1 行で全部(数え方は語つきのまま)
    win.resize(long_w + 8 + need + 8 + 2, 300)
    _pump(qapp)
    assert p.message_wrap.isHidden() and p.status.height() == row
    assert p.message_shown() == p.message_label.full_text() and p.counts_label.text() == p.counts_text()
    # 中くらいの幅: 数え方を短い形にすれば 1 行に入るなら、折り返さずにそうする
    win.resize(short_w + 8 + need + 8 + 2, 300)
    _pump(qapp)
    assert p.message_wrap.isHidden() and p.status.height() == row
    assert p.message_shown() == p.message_label.full_text() and p.counts_label.text() == p.counts_text(compact=True)
    # それより狭い: 折り返す
    win.resize(short_w + 8 + need + 8 - 6, 300)
    _pump(qapp)
    assert not p.message_wrap.isHidden() and p.message_shown() == p.message_label.full_text() and p.status.height() > row
    _close_quietly(win)


def _whole(w) -> bool:
    """部品が親に切られずに全部見えているか。"""
    if not w.isVisible():
        return False
    r = w.visibleRegion().boundingRect()
    return (r.width(), r.height()) == (w.width(), w.height())


def _button_rects(win) -> list:
    return [_rect_in(win.panel.buttons[k], win) for k in BUTTONS]


@pytest.mark.parametrize("size", [(1024, 240), (1024, 160), (1280, 280), (320, 160)])
def test_params_left_strip_never_squeezes_or_cuts_its_buttons(qapp, fusion, ini, tmp_path, size):
    """確かめの指摘(medium): 道具の列を左に縦にした窓を低くしても(横長・低い形 = 左に縦の規則が当たる形そのもの)、
    10 個のボタンが詰まらず・重ならず・切れない。直す前は 1024x240 で 6 個が前のボタンと重なり最後が切れ、1024x160 で 9 個が
    重なった。既定の列の部品は送りも折り返しも持たないので、縦に収まらない高さでは上の横 1 行へ戻る(頼まれた向きは left の
    まま覚えていて、高さが戻れば左の縦 1 列へ戻る)。"""
    win = _window(qapp, _three_files(tmp_path), size=(1024, 700))
    p = win.panel
    p.set_strip_side("left")
    _pump(qapp)
    assert len({r.x() for r in _button_rects(win)}) == 1                 # 高い窓では左に縦 1 列
    win.resize(*size)
    _pump(qapp)
    _pump(qapp)
    assert (win.width(), win.height()) == size
    rects = _button_rects(win)
    status = _rect_in(p.status, win)
    checked = 0
    for k, r in zip(BUTTONS, rects):
        assert _whole(p.buttons[k]) and win.rect().contains(r) and (r.width(), r.height()) == (24, 24), (size, k, r)
        assert not r.intersects(status), (size, k)
        checked += 1
    assert checked == 10
    assert [(i, j) for i in range(10) for j in range(i + 1, 10) if rects[i].intersects(rects[j])] == [], size
    assert p.strip_side() == "left" and p.strip_side_shown() == "top"
    assert len({r.y() for r in rects}) == 1                              # 上の横 1 行(間は決まりどおり)
    assert [rects[i + 1].left() - rects[i].right() - 1 for i in range(9)] == [4, 4, 8, 4, 4, 8, 4, 4, 8]
    assert _whole(p.search) and win.rect().contains(_rect_in(p.search, win))
    win.resize(1024, 700)                                                # 高さが戻れば左へ戻る
    _pump(qapp)
    _pump(qapp)
    rects = _button_rects(win)
    assert p.strip_side_shown() == "left" and len({r.x() for r in rects}) == 1 and len({r.y() for r in rects}) == 10
    _close_quietly(win)


def test_params_strip_draws_a_line_between_groups(qapp, fusion, ini, tmp_path):
    """設計書 P04-2: 群の間(8 px)に細い線が 1 本、隣り合うボタンの間(4 px)には何も無い。横の 1 行でも縦の 1 列でも。
    線は描かれた画素で数える(間の帯の中の、地と違う画素の外接: 幅 1 px・長さ 12 px 以上)。"""
    win = _window(qapp, _three_files(tmp_path), size=(720, 420))
    p = win.panel
    lines = plain = 0
    for side in ("top", "left"):
        p.set_strip_side(side)
        _pump(qapp)
        img = win.grab().toImage()
        rects = _button_rects(win)
        for i in range(9):
            a, b = rects[i], rects[i + 1]
            if side == "top":
                between = QtCore.QRect(a.right() + 1, a.top(), b.left() - a.right() - 1, a.height())
            else:
                between = QtCore.QRect(a.left(), a.bottom() + 1, a.width(), b.top() - a.bottom() - 1)
            w, h, _ink_colour, _ground = _ink(img, between, 0)
            if i in (2, 5, 8):                                           # 群の境
                assert min(w, h) == 1 and max(w, h) >= 12, (side, i, w, h)
                lines += 1
            else:
                assert (w, h) == (0, 0), (side, i, w, h)
                plain += 1
    assert (lines, plain) == (6, 12)
    _close_quietly(win)


class _FlowLike(QtWidgets.QWidget):
    """見た目の枝の studio_panels.FlowStrip と同じ口の代役(この木に studio_panels が無くても門が回るように)。
    ボタンの群を受け取り(set_groups)、向きは "h" / "v" の文字(それ以外は本物と同じく黙って "h")、objectName は "flow_strip"。
    収まらなければ両端に送りのボタン(b_back / b_on)が出て、1 回押すと 1 個送る。端では無効。
    restyle(tr) は送りのボタンのツールヒントを tr で作り直し(本物と同じく、作った時にも 1 回)、set_mode は収まらない時の形
    "scroll" / "wrap" を覚える(知らない形は本物と同じく "scroll"。この代役は折り返しまでは描かない)。"""

    def __init__(self):
        super().__init__()
        self.setObjectName("flow_strip")
        self.orientation = "h"
        self.groups: list = []
        self.first = self.end_first = 0
        self.b_back, self.b_on = QtWidgets.QToolButton(self), QtWidgets.QToolButton(self)
        self.b_back.clicked.connect(lambda: self.scroll_by(-1))
        self.b_on.clicked.connect(lambda: self.scroll_by(1))
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.tr = lambda s: s
        self.mode = "scroll"
        self.restyle()

    def restyle(self, tr=None):
        if tr is not None:
            self.tr = tr
        for b, text in zip((self.b_back, self.b_on), _SCROLL_TIPS):
            b.setToolTip(self.tr(text))

    def set_mode(self, mode):
        mode = mode if mode in ("scroll", "wrap") else "scroll"
        if mode != self.mode:
            self.mode = mode
            self.first = 0
            self.updateGeometry()
            self.relayout()

    def set_groups(self, groups):
        self.groups = [list(g) for g in groups if g]
        for w in self.items():
            w.setParent(self)
            w.show()
        self.first = 0
        self.updateGeometry()
        self.relayout()

    def items(self):
        return [w for g in self.groups for w in g]

    def set_orientation(self, orientation):
        self.orientation = "v" if orientation == "v" else "h"
        pol = QtWidgets.QSizePolicy
        if self.orientation == "h":
            self.setSizePolicy(pol.Preferred, pol.Fixed)
        else:
            self.setSizePolicy(pol.Fixed, pol.Preferred)
        self.first = 0
        self.updateGeometry()
        self.relayout()

    def _need(self) -> int:
        n = len(self.items())
        return n * 24 + max(0, n - 1) * 4

    def sizeHint(self):
        return QtCore.QSize(self._need(), 24) if self.orientation == "h" else QtCore.QSize(24, self._need())

    def minimumSizeHint(self):
        return QtCore.QSize(48, 24) if self.orientation == "h" else QtCore.QSize(24, 48)

    def scroll_by(self, step):
        self.first = max(0, min(self.first + step, self.end_first))
        self.relayout()

    def relayout(self):
        h = self.orientation == "h"
        items = self.items()
        length = self.width() if h else self.height()
        fits = self._need() <= length
        arrow = 0 if fits else 12
        per = max(1, (length - 2 * arrow + 4) // 28)
        self.end_first = 0 if fits else max(0, len(items) - per)
        self.first = min(self.first, self.end_first)
        pos = arrow
        for i, w in enumerate(items):
            if fits or self.first <= i < self.first + per:
                w.setGeometry(pos, 0, 24, 24) if h else w.setGeometry(0, pos, 24, 24)
                pos += 28
            else:
                w.setGeometry(-30000, -30000, 24, 24)       # 送られて見えない所で待つ
        for b, at in ((self.b_back, 0), (self.b_on, length - 12)):
            b.setVisible(not fits)
            b.setGeometry(at, 0, 12, 24) if h else b.setGeometry(0, at, 24, 12)
        self.b_back.setEnabled(self.first > 0)
        self.b_on.setEnabled(self.first < self.end_first)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.relayout()


#: 見た目の枝の FlowStrip の送りのボタンのツールヒント(studio_panels.S_SCROLL_BACK / S_SCROLL_ON と同じ英語の元の文)。
_SCROLL_TIPS = ("Scroll back \u2014 show the ones before (or turn the mouse wheel)",
                "Scroll on \u2014 show the ones after (or turn the mouse wheel)")


def _another_flow_strip(fs):
    """``fs`` と同じ種類の FlowStrip をもう 1 つ(代役なら代役、本物なら本物)。"""
    return _FlowLike() if isinstance(fs, _FlowLike) else type(fs)("tools", "params")


@pytest.fixture(params=["stand-in", "studio_panels"])
def flow_strip(request):
    """FlowStrip の形の部品。stand-in = 上の代役(どの木でも回る)、studio_panels = 見た目の枝の本物(入っている木だけ)。"""
    if request.param == "stand-in":
        return _FlowLike()
    sp = pytest.importorskip("studio_panels", reason="the look branch (studio_panels) is not in this tree")
    return sp.flow_classes()["FlowStrip"]("tools", "params")


def _reach_by_arrows(qapp, p, strip) -> tuple[set, int]:
    """送りのボタンを**押して**届いたボタンの鍵の集まりと、押した回数(先頭まで戻してから、端で無効になるまで進む)。"""
    for _ in range(40):
        if not (strip.b_back.isVisible() and strip.b_back.isEnabled()):
            break
        strip.b_back.click()
        _pump(qapp)
    seen, presses = set(), 0
    for _ in range(40):
        seen |= {k for k in BUTTONS if _whole(p.buttons[k])}
        if not (strip.b_on.isVisible() and strip.b_on.isEnabled()):
            break
        strip.b_on.click()
        presses += 1
        _pump(qapp)
    return seen, presses


def test_params_strip_takes_the_flow_strip_of_the_look_branch(qapp, fusion, ini, tmp_path, flow_strip):
    """確かめの指摘(medium / low): 差し替えの口 set_strip_widget は、見た目の枝の本物の部品 FlowStrip の形(set_groups・
    向きは "h" / "v"・objectName "flow_strip")をそのまま受ける。直す前は TypeError(set_actions が無い)で、試験の代役でしか
    確かめていなかった。差し込んだ列は、高い窓では左に縦 1 列で全部見え、低い窓(1024x240・1024x160)では左のまま送りのボタンが
    出て、**押して** 10 個全部に届き、端で無効になり、広げると消える。同じ QAction 10 個が 3・3・3・1 の群で入り、有効・押した
    状態が通る。名前は付け替えない。"""
    win = _window(qapp, _three_files(tmp_path), size=(1024, 700))
    p = win.panel
    old = p.strip_widget()
    fs = flow_strip
    p.set_strip_widget(fs)
    _pump(qapp)
    assert p.strip_widget() is fs and p.isAncestorOf(fs) and fs.objectName() == "flow_strip"
    assert old.parent() is None and not old.isVisible() and _strips(p) == []
    acts = [a for a in p.strip_actions() if a is not None]
    inside = [b for g in fs.groups for b in g]
    assert [len(g) for g in fs.groups] == [3, 3, 3, 1] and [b.defaultAction() for b in inside] == acts
    assert [p.buttons[k] for k in BUTTONS] == inside and all(b.parent() is fs for b in inside)
    steps = 0
    for side, size, orient, scrolls in (("left", (1024, 700), "v", False), ("left", (1024, 240), "v", True),
                                        ("left", (1024, 160), "v", True), ("left", (1024, 700), "v", False),
                                        ("top", (1024, 700), "h", False)):
        p.set_strip_side(side)
        win.resize(*size)
        _pump(qapp)
        _pump(qapp)
        assert fs.orientation == orient and p.strip_side_shown() == side, (side, size)   # 送る部品は低い窓でも左のまま
        assert (fs.b_back.isVisible(), fs.b_on.isVisible()) == (scrolls, scrolls), (side, size)
        assert win.rect().contains(_rect_in(fs, win)) and not _rect_in(fs, win).intersects(_rect_in(p.status, win))
        seen, presses = _reach_by_arrows(qapp, p, fs)
        assert seen == set(BUTTONS), (side, size, sorted(set(BUTTONS) - seen))
        if scrolls:
            assert presses >= 3 and not fs.b_on.isEnabled() and fs.b_back.isEnabled()    # 端まで送った
            assert len([k for k in BUTTONS if _whole(p.buttons[k])]) < 10                # 一度には見えていない
        else:
            assert presses == 0
        steps += 1
    assert steps == 5
    assert not p.buttons["redo"].isEnabled() and not p.buttons["diff"].isChecked()
    assert p.edit_cell(0, "camera.fx", "900").ok
    p.undo()
    assert p.buttons["redo"].isEnabled()
    p.buttons["diff"].click()
    assert p.tmodel.diff_only and p.buttons["diff"].isChecked()
    with pytest.raises(TypeError):
        p.set_strip_widget(QtWidgets.QLabel("no"))
    assert p.strip_widget() is fs
    _close_quietly(win)


def test_params_strip_follows_the_side_rule(qapp, fusion, ini, tmp_path):
    """確かめの指摘(medium): 「横長なら道具の列を左へ縦に」の規則(全部のパネルで 1 つ = studio_panels.strip_side)を
    set_strip_rule で受け取り、パネルの大きさが変わるたびに聞いて向きを変える。規則は幅 / 高さ 2.2 以上で左・1.6 以下で上・
    間は今のまま(同じ式を写した)。既定の部品が縦に収まらない高さでは、頼まれた向きは left のまま、置くのは上。"""
    asked = []

    def rule(w, h, now):
        asked.append((w, h, now))
        ratio = w / h
        return "left" if ratio >= 2.2 else ("top" if ratio <= 1.6 else now)

    win = _window(qapp, _three_files(tmp_path), size=(720, 420))
    p = win.panel
    p.set_strip_rule(rule)
    assert (p.strip_side(), p.strip_side_shown()) == ("top", "top") and asked == [(720, 420, "top")]   # 1.71 = 間
    turns = 0
    for size, want, shown in (((1280, 500), "left", "left"), ((1024, 560), "left", "left"), ((600, 600), "top", "top"),
                              ((1024, 560), "top", "top"), ((1280, 280), "left", "top"), ((1280, 500), "left", "left")):
        win.resize(*size)
        _pump(qapp)
        _pump(qapp)
        assert (p.strip_side(), p.strip_side_shown()) == (want, shown), size
        rects = _button_rects(win)
        assert (len({r.x() for r in rects}) == 1) == (shown == "left") and all(_whole(p.buttons[k]) for k in BUTTONS), size
        turns += 1
    assert turns == 6 and len(asked) >= 7 and {now for _w, _h, now in asked} == {"top", "left"}
    p.set_strip_rule(lambda w, h, now: "bottom")                         # 知らない答えは聞かなかった事にする
    win.resize(600, 600)
    _pump(qapp)
    assert p.strip_side() == "left"
    p.set_strip_rule(None)                                               # 外す: 向きは今のまま、大きさを変えても変わらない
    n = len(asked)
    win.resize(700, 600)
    _pump(qapp)
    assert p.strip_side() == "left" and len(asked) == n
    _close_quietly(win)


#: 見た目の枝の studio_theme.DENSITY の写し(この窓が使う鍵と、使わない鍵 1 つ)。
_DENSITY = {
    "compact": {"row_pad": 4, "icon_btn": 24, "icon": 16, "click_gap": 4, "group_gap": 8, "title_band": 22},
    "standard": {"row_pad": 8, "icon_btn": 28, "icon": 18, "click_gap": 4, "group_gap": 10, "title_band": 28},
}


def _sizes(p) -> dict:
    """窓の密度の数を実物から測る: 行・ボタン・絵・間・検索の欄・状態の行・見出し。"""
    fm = p.tree.fontMetrics()
    keys = _visible_keys(p)
    btns = [p.buttons[k] for k in BUTTONS]
    assert len(keys) == 9 and len(btns) == 10
    return {"row_pad": {p.tree.visualRect(p.index_of(0, k)).height() - fm.height() for k in keys},
            "button": {(b.width(), b.height()) for b in btns}, "icon": {b.iconSize().width() for b in btns},
            "gaps": [btns[i + 1].geometry().left() - btns[i].geometry().right() - 1 for i in range(9)],
            "search": p.search.height(), "status": p.status.height() - p.fontMetrics().height(),
            "header": p.tree.header().height() - p.fontMetrics().height()}


def test_params_sizes_come_from_the_theme_density(qapp, fusion, ini, tmp_path, monkeypatch):
    """確かめの指摘(low): px は直書きでなく studio_theme の密度の表から(設計書 P14-1・B0)。密度を「標準」にした
    Studio で開くと、行 = 文字 + 8・絵だけのボタン 28 px(絵 18)・群の間 10 px。直す前は窓だけ詰めたまま(20・24・8)だった。
    密度を変えて theme を読み直すと(apply_theme。様式が変わった時はパネルが自分で呼ぶ)その場で変わり、戻すと戻る。
    theme の無い木では窓の定数(詰めると同じ値)。"""
    compact = {"row_pad": {4}, "button": {(24, 24)}, "icon": {16}, "gaps": [4, 4, 8, 4, 4, 8, 4, 4, 8], "search": 24,
               "status": 4, "header": 6}
    standard = {"row_pad": {8}, "button": {(28, 28)}, "icon": {18}, "gaps": [4, 4, 10, 4, 4, 10, 4, 4, 10], "search": 28,
                "status": 8, "header": 10}
    state = {"density": "standard"}
    fake = types.ModuleType("studio_theme")
    fake.colour = lambda role: _THEME_ROLES["instrument"][role]
    fake.density = lambda: dict(_DENSITY[state["density"]])
    monkeypatch.setitem(sys.modules, "studio_theme", fake)
    assert Q._density() == {k: v for k, v in _DENSITY["standard"].items() if k != "title_band"}
    win = _window(qapp, _three_files(tmp_path))
    p = win.panel
    assert _sizes(p) == standard and p.row_height() == p.fontMetrics().height() + 8
    switched = 0
    for name, want in (("compact", compact), ("standard", standard), ("compact", compact)):
        state["density"] = name
        p.apply_theme()
        _pump(qapp)
        assert _sizes(p) == want, name
        assert all(_whole(p.buttons[k]) for k in BUTTONS) and _whole(p.search), name
        switched += 1
    assert switched == 3
    p.set_strip_side("left")                                             # 縦の 1 列でも同じ数
    state["density"] = "standard"
    p.apply_theme()
    _pump(qapp)
    rects = _button_rects(win)
    assert len({r.x() for r in rects}) == 1 and {(r.width(), r.height()) for r in rects} == {(28, 28)}
    assert [rects[i + 1].top() - rects[i].bottom() - 1 for i in range(9)] == [4, 4, 10, 4, 4, 10, 4, 4, 10]
    _close_quietly(win)
    # 壊れた表(鍵が無い・正の整数でない)は、その数だけ窓の定数に倒す
    fake.density = lambda: {"row_pad": "8", "icon_btn": 0, "icon": True, "group_gap": 12}
    assert Q._density() == {"row_pad": 4, "icon_btn": 24, "icon": 16, "click_gap": 4, "group_gap": 12}
    # theme の無い木: 窓の定数(詰めると同じ値)
    monkeypatch.setitem(sys.modules, "studio_theme", None)
    assert Q._density() == {k: v for k, v in _DENSITY["compact"].items() if k != "title_band"}
    plain = tmp_path / "plain"
    plain.mkdir()
    win = _window(qapp, _three_files(plain))
    assert _sizes(win.panel) == compact
    _close_quietly(win)


@pytest.mark.parametrize("files", [True, False], ids=["with bundles", "empty"])
def test_params_opens_with_focus_off_the_buttons_and_no_default_button(qapp, fusion, ini, tmp_path, files):
    """確かめの指摘(low)/ 設計書 P02-4・P02-5・G02(f)(g): 開いた直後のフォーカスはボタンに無い(束があれば表、無ければ
    パネルそのもの。直す前は「開く」のボタン)。窓の中の QPushButton は全部 autoDefault も default も偽(直す前は 3 個とも
    autoDefault で、「ファイルを開く」は既定の青い枠)。どこにフォーカスがあっても Enter でボタンは押されない。空の案内から
    例を開くと表へ、全部の列を外すとパネルへフォーカスが移る(隣のボタンへ流れない)。Studio の入口から開いても同じ。"""
    paths = _three_files(tmp_path) if files else []
    win = _window(qapp, paths)
    win.activateWindow()
    _pump(qapp)
    p = win.panel
    p.pick_open = lambda: []                                            # 本物のファイルの窓を出さない
    fw = win.focusWidget()
    assert fw is not None and not isinstance(fw, QtWidgets.QAbstractButton), fw
    assert fw is (p.tree if files else p)
    pushes = win.findChildren(QtWidgets.QPushButton)
    assert len(pushes) == 3 and {p.empty_open, p.empty_example, p.no_match_button} == set(pushes)
    assert [b.text() for b in pushes if b.autoDefault() or b.isDefault()] == []
    fired = []
    for b in win.findChildren(QtWidgets.QAbstractButton):
        b.clicked.connect(lambda _c=False, b=b: fired.append(b))
    pressed = 0
    for w in (p, p.tree, p.search, win):
        if not (w.isEnabled() and w.isVisible()):
            continue
        w.setFocus()
        for key in (Qt.Key_Return, Qt.Key_Enter):
            QTest.keyClick(w, key)
            pressed += 1
    _pump(qapp)
    assert pressed >= 4 and fired == [] and win.isVisible()
    if not files:
        p.empty_example.setFocus()                                      # 押したボタンは、頁が替わると隠れる
        p.empty_example.click()
        _pump(qapp)
        assert p.stack.currentWidget() is p.tree and win.focusWidget() is p.tree
        while p.model.columns:
            p.model.remove_column(0)
        p.refresh()
        _pump(qapp)
        assert p.stack.currentWidget() is p.empty and win.focusWidget() is p
    _close_quietly(win)
    parent = QtWidgets.QWidget()
    w2 = Q.show_params_window(parent, paths, M.make_tr("en"))
    _pump(qapp)
    fw = w2.focusWidget()
    assert fw is (w2.panel.tree if files else w2.panel) and not isinstance(fw, QtWidgets.QAbstractButton)
    _close_quietly(w2)
    parent.deleteLater()


_TIP_FORM = re.compile(r"^[^\u2014]+ \u2014 .+$")


@pytest.mark.parametrize("lang", ["en", "ja"])
def test_params_every_button_has_a_tooltip_and_disabled_ones_say_why(qapp, fusion, ini, tmp_path, lang):
    """確かめの指摘(low)/ 設計書 P04-4・P04-5: 窓の木の中の絵だけのボタン(QToolButton)は全部ツールヒントと読み上げの名前を
    持つ(直す前は検索の欄の中の虫眼鏡と × が空)。虫眼鏡は Ctrl+F と同じ(欄へ行く)、× は「検索を消す」。押せない道具は
    ツールヒントに理由を言い(直す前は押せる時と同じ文)、押せるようになれば理由は消える。形は「名前 — 何が起きるか (キー)」のまま。"""
    tr = M.make_tr(lang)
    lead = tr("not available now: %s").split("%s")[0]
    assert lead.strip() and (lang == "en" or lead != "not available now: ")
    win = _window(qapp, lang=lang)
    p = win.panel
    tools = win.findChildren(QtWidgets.QToolButton)
    assert len(tools) == 12                                             # 道具 10 + 検索の欄の中の 2
    assert [b for b in tools if not b.toolTip().strip()] == []
    assert [b for b in tools if not (b.accessibleName().strip() or b.text().strip())] == []

    def reasons() -> dict:
        out = {}
        for k in BUTTONS:
            b = p.buttons[k]
            tip = b.toolTip()
            assert _TIP_FORM.match(tip) and "\n" not in tip, (k, tip)
            keys = p.tool_actions[k].shortcut().toString(QtGui.QKeySequence.NativeText)
            assert not keys or tip.endswith(" (%s)" % keys), (k, tip)              # キーは末尾のまま
            assert (lead in tip) == (not b.isEnabled()), (k, tip, b.isEnabled())   # 押せない時だけ理由
            if lead in tip:
                out[k] = tip.split(lead, 1)[1].split(" (")[0]
        return out

    first = tr("open a file first")
    assert reasons() == {"remove": first, "save": first, "saveas": first, "reload": first, "copy": tr("open two or more bundles first"),
                         "diff": first, "undo": tr("nothing to undo"), "redo": tr("nothing to redo")}
    assert not p.search.isEnabled() and (lead + first) in p.search.toolTip() and p.search.toolTip().endswith("(Ctrl+F)")
    assert p.add_paths(_three_files(tmp_path)) and p.search.isEnabled() and lead not in p.search.toolTip()
    column = tr("select a column first")
    assert reasons() == {"remove": column, "saveas": column, "reload": column, "save": tr("nothing has changed"),
                         "undo": tr("nothing to undo"), "redo": tr("nothing to redo")}
    assert p.select_cell(0, "camera.fx") and p.edit_cell(0, "camera.fx", "900").ok
    assert reasons() == {"redo": tr("nothing to redo")}
    p.undo()
    assert reasons() == {"save": tr("nothing has changed"), "undo": tr("nothing to undo")}
    assert p.model.add_bundle({"a": 1}, "memo").ok                     # ファイルの無い束
    p.refresh()
    assert p.select_cell(3, "a") and reasons()["reload"] == tr("the selected bundle has no file yet")
    # 検索の欄の中の 2 つ: 虫眼鏡 = 欄へ行く(Ctrl+F と同じ)、× = 検索を消す
    inner = p.search.findChildren(QtWidgets.QToolButton)
    assert len(inner) == 2
    clear = [b for b in inner if b.defaultAction().objectName() == "_q_qlineeditclearaction"]
    glass = [b for b in inner if b not in clear]
    assert len(clear) == 1 and clear[0].toolTip() == tr("Clear the search")
    assert len(glass) == 1 and glass[0].toolTip() == p.search.toolTip() and _TIP_FORM.match(glass[0].toolTip())
    p.search.setText("fx")
    p.tree.setFocus()
    glass[0].defaultAction().trigger()
    assert win.focusWidget() is p.search and p.search.selectedText() == "fx"
    p.ask_unsaved = lambda names: "discard"
    _close_quietly(win)


@pytest.mark.parametrize("lang", M.LANGS)
def test_params_empty_guide_is_not_cut_at_the_smallest_window(qapp, fusion, ini, lang):
    """確かめの指摘(low): 窓の最小の大きさ(320x160)でも、空の案内の文が切れない(直す前は 48 px 要る所が 38 px で 3 行目が
    半分切れた)。収まらない分は頁が縦に送れる(横には送らない)。広い窓では送りは出ない。"""
    win = _window(qapp, lang=lang, size=(320, 160))
    p = win.panel
    assert (win.width(), win.height()) == (320, 160) and p.stack.currentWidget() is p.empty
    lab = p.empty_label
    assert lab.text() == M.make_tr(lang)(Q.ParamsPanel.EMPTY_TEXT)
    assert lab.height() >= lab.heightForWidth(lab.width()) > 0, (lang, lab.height(), lab.heightForWidth(lab.width()))
    body = p.empty.widget()
    for w in (lab, p.empty_open, p.empty_example):                      # 頁の中身は全部、頁の内側にある(送れば届く)
        assert body.rect().contains(QtCore.QRect(w.mapTo(body, QtCore.QPoint(0, 0)), w.size())), (lang, w)
    over = body.height() - p.empty.viewport().height()                 # 収まらない分(0 なら全部見えている)
    assert over >= 0 and p.empty.verticalScrollBar().maximum() == over, (lang, over)
    assert p.empty.horizontalScrollBar().maximum() == 0 and body.width() <= p.empty.viewport().width()
    win.resize(720, 420)
    _pump(qapp)
    assert p.empty.verticalScrollBar().maximum() == 0 and not p.empty.verticalScrollBar().isVisible()
    assert lab.height() >= lab.heightForWidth(lab.width()) > 0
    _close_quietly(win)


def test_params_narrow_headers_show_an_ellipsis(qapp, fusion, ini, tmp_path):
    """確かめの指摘(low): 列が細くて入らない見出し(330 px・道具の列が左)は、黙って切らずに末尾を … にする。全部の名前と
    場所は見出しのツールヒントにある。"""
    paths = _three_files(tmp_path)
    win = _window(qapp, paths, size=(330, 700))
    p = win.panel
    p.set_strip_side("left")
    _pump(qapp)
    hdr = p.tree.header()
    assert hdr.textElideMode() == Qt.ElideRight
    tips = [p.tmodel.headerData(2 + i, Qt.Horizontal, Qt.ToolTipRole) for i in range(3)]
    assert [os.path.normcase(t.split("\n")[0]) for t in tips] == [os.path.normcase(x) for x in paths]
    _close_quietly(win)


@pytest.mark.parametrize("lang", ["de", "en", "ja"])
def test_params_search_field_is_wide_enough_at_every_width(qapp, fusion, ini, tmp_path, lang):
    """D112 の門を広げる(確かめの指摘): 検索の欄は、窓の幅 320〜760 px のどこでも、置いた文字が全部見える幅より狭く
    ならず、窓の内側にある(収まらない幅では次の段へ送られる)。前の門は 330 px の 1 点だけで、最小幅を直す前の 60 に戻しても
    緑だった(330 px では 60 でも次の段へ送られる。切れるのは段が変わる境の手前の幅)。道具 10 個も切れない。広げ直すと
    道具の行へ戻る。"""
    win = _window(qapp, _three_files(tmp_path), lang=lang, size=(760, 300))
    p = win.panel
    s = p.search
    need = s.fontMetrics().horizontalAdvance(s.placeholderText()) + 32
    widths = list(range(760, 319, -8))
    below = set()
    for w in widths + [760]:
        win.resize(w, 300)
        _pump(qapp)
        _pump(qapp)
        assert win.width() == w
        left = s.mapTo(p, QtCore.QPoint(0, 0)).x()
        assert s.isVisible() and left >= 0 and left + s.width() <= p.width() - 2, (lang, w, left, s.width())
        assert s.width() >= need, (lang, w, s.width(), need)
        for k in BUTTONS:
            b = p.buttons[k]
            x = b.mapTo(p, QtCore.QPoint(0, 0)).x()
            assert _whole(b) and 0 <= x and x + b.width() <= p.width() - 2, (lang, w, k)
        below.add(p._search_below)
    assert len(widths) == 56 and below == {True, False}                 # 段が変わる境をまたいでいる
    assert not p._search_below                                          # 広げ直すと道具の行へ戻る
    _close_quietly(win)


def test_params_filter_change_clears_the_old_notice(qapp, fusion, ini, tmp_path):
    """D112(確かめの指摘): 絞り込みを変えたら、前の表についての知らせを消す。検索の語を変えた時だけでなく、
    「違う行だけ」を入れた時も切った時も(前の門は検索だけを見ていた)。"""
    win = _window(qapp, _three_files(tmp_path))
    p = win.panel
    cleared = 0
    for change in (lambda: p.set_diff_only(True), lambda: p.set_diff_only(False), lambda: p.buttons["diff"].click(),
                   lambda: p.search.setText("fx"), lambda: p.search.setText("")):
        assert p.copy_column(0, 2).ok or p.copy_column(1, 2).ok
        assert p.message_label.full_text() != ""                        # 古い知らせ(写した)
        change()
        _pump(qapp)
        assert p.message_label.full_text() == "" and p.message_level == "info"
        cleared += 1
    assert cleared == 5
    _close_quietly(win)


def test_params_every_pressable_thing_is_declared(qapp, fusion, ini, tmp_path):
    """道具の列の門を広げる(確かめの指摘): 窓の木の中の押せる物(QAbstractButton)を全部拾い、どれも「道具の列の中の
    QAction を押すボタン」「検索の欄の中の 2 つ」「一覧の場所の文字のボタン 3 つ」のどれかである(列の外に、宣言していない
    道具のボタンが無い)。前の門は決まった 10 個の QAction だけを数え、列の外にボタンを 1 個足しても緑だった。"""
    win = _window(qapp, _three_files(tmp_path))
    p = win.panel
    strip = p.strip_widget()
    acts = [a for a in p.strip_actions() if a is not None]
    every = win.findChildren(QtWidgets.QAbstractButton)
    in_strip = [b for b in every if strip.isAncestorOf(b)]
    in_search = [b for b in every if p.search.isAncestorOf(b)]
    pushes = [b for b in every if isinstance(b, QtWidgets.QPushButton)]
    assert len(every) == 15 and (len(in_strip), len(in_search), len(pushes)) == (10, 2, 3)
    stray = [b for b in every if b not in in_strip and b not in in_search and b not in pushes]
    assert stray == [], [(type(b).__name__, b.toolTip()) for b in stray]
    assert sorted(id(b.defaultAction()) for b in in_strip) == sorted(id(a) for a in acts)
    assert set(pushes) == {p.empty_open, p.empty_example, p.no_match_button}
    for side in ("left", "top"):                                        # 向きを変えても同じ
        p.set_strip_side(side)
        _pump(qapp)
        every = win.findChildren(QtWidgets.QAbstractButton)
        live = [b for b in every if p.strip_widget().isAncestorOf(b)]
        assert len(every) == 15 and len(live) == 10, (side, len(every), len(live))
        assert sorted(id(b.defaultAction()) for b in live) == sorted(id(a) for a in acts), side
    _close_quietly(win)


def test_params_ctrl_d_does_nothing_wherever_the_focus_is(qapp, fusion, ini, tmp_path):
    """D90 の門を広げる(確かめの指摘): 窓の木の中でフォーカスを取れる部品を全部回り、どこで Ctrl+D を押しても絞り込みが
    変わらない(QAction / QShortcut の一覧と、表への 1 回の打鍵だけを見る門は、検索の欄のイベントフィルタで Ctrl+D を戻しても
    緑だった)。届く事の対照: 同じ回り方で Ctrl+F は検索の欄へ行く。"""
    win = _window(qapp, _three_files(tmp_path))
    p = win.panel
    assert p.select_cell(0, "camera.fx") and p.edit_cell(0, "camera.fx", "900").ok   # 押せる道具を増やす(やり直し以外の 9 個)
    win.activateWindow()
    _pump(qapp)
    visited, toggled = [], []
    for w in [win] + win.findChildren(QtWidgets.QWidget):
        if not w.isVisible() or not w.isEnabled() or w.focusPolicy() == Qt.NoFocus:
            continue
        w.setFocus()
        _pump(qapp)
        before = p.tmodel.diff_only
        QTest.keyClick(w, Qt.Key_D, Qt.ControlModifier)
        _pump(qapp)
        visited.append(type(w).__name__)
        if p.tmodel.diff_only != before:
            toggled.append(type(w).__name__ + ":" + w.objectName())
            p.set_diff_only(before)
    assert len(visited) >= 11 and visited.count("_StripButton") == 9, visited
    assert {"_Tree", "QLineEdit", "_StripButton"} <= set(visited), visited
    assert toggled == [] and not p.tool_actions["diff"].isChecked()
    p.tree.setFocus()                                                   # 対照: キーは届いている
    QTest.keyClick(p.tree, Qt.Key_F, Qt.ControlModifier)
    assert win.focusWidget() is p.search
    _close_quietly(win)


def test_params_panel_in_a_host_window_does_not_take_the_focus(qapp, fusion, ini, tmp_path):
    """パネルを別の窓の中に入れた時(Studio の dock に入れる形)、ファイルを足して一覧の場所の頁が替わっても、窓のフォーカスが
    よその部品にある時・まだ無い時は奪わない。フォーカスがパネルの中にあった時だけ置き直す。"""
    host = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(host)
    editor = QtWidgets.QPlainTextEdit(host)                             # 主役(コードの欄の代わり)
    panel = Q.ParamsPanel(M.make_tr("en"), host)
    lay.addWidget(editor)
    lay.addWidget(panel)
    host.resize(800, 600)
    kept = 0
    assert host.focusWidget() is None
    panel.open_example()                                                # まだフォーカスの先が無い窓: 取らない
    assert panel.stack.currentWidget() is panel.tree and host.focusWidget() is None
    kept += 1
    host.show()
    editor.setFocus()
    _pump(qapp)
    assert host.focusWidget() is editor
    while panel.model.columns:
        panel.model.remove_column(0)
    panel.refresh()                                                     # 表 → 空の案内: フォーカスは主役のまま
    assert panel.stack.currentWidget() is panel.empty and host.focusWidget() is editor
    kept += 1
    assert [o.ok for o in panel.add_paths(_three_files(tmp_path))] == [True] * 3
    assert panel.stack.currentWidget() is panel.tree and host.focusWidget() is editor
    kept += 1
    panel.tree.setFocus()                                               # パネルの中にある時は置き直す
    while panel.model.columns:
        panel.model.remove_column(0)
    panel.refresh()
    assert panel.stack.currentWidget() is panel.empty and host.focusWidget() is panel
    assert kept == 3
    host.close()
    host.deleteLater()


def _scroll_tips(fs) -> tuple[str, str]:
    """``fs`` の送りのボタンのツールヒントの英語の元の文(本物なら studio_panels の定数、代役なら _SCROLL_TIPS)。"""
    sp = sys.modules.get(type(fs).__module__)
    return getattr(sp, "S_SCROLL_BACK", _SCROLL_TIPS[0]), getattr(sp, "S_SCROLL_ON", _SCROLL_TIPS[1])


def test_params_flow_strip_hears_the_language_theme_and_overflow(qapp, fusion, ini, tmp_path, flow_strip):
    """確かめの指摘(medium): 差し込んだ FlowStrip に、Studio の言語・theme・「収まらない時: 送る / 折り返す」が届く。
    見た目の枝は言語と theme を restyle(tr)、送る / 折り返すを set_mode で当てるが、台帳(st["strips"])に載った列にしか
    当てず、この窓は台帳に載らない。直す前は ja の窓でも送りのボタンのツールヒントが英語のまま(set_lang の後も)で、
    パネルに送る / 折り返すを渡す口(set_overflow)が無かった。

    Studio の tr の代役は「今の UI の言語」で引く関数(Studio の tr と同じく、言語は外の状態)。束の表に無い送りの文は、
    窓の tr(make_tr(lang, fallback=Studio の tr))から Studio の tr へ流れて訳される。"""
    fs = flow_strip
    tips = _scroll_tips(fs)
    ui = {"lang": "en"}

    def host(text):
        return text if ui["lang"] == "en" or not text else "[%s] %s" % (ui["lang"], text)

    def shown(strip) -> tuple[str, str]:
        return strip.b_back.toolTip(), strip.b_on.toolTip()

    win = Q.ParamsWindow(None, host, lang="en")
    win.resize(1024, 240)
    p = win.panel
    p.add_paths(_three_files(tmp_path))
    win.show()
    _pump(qapp)
    p.set_strip_widget(fs)
    _pump(qapp)
    assert shown(fs) == tips                                            # en: 元の文のまま
    open_en = p.tool_actions["open"].toolTip()
    checked = 0
    for lang in ("ja", "de", "en", "hi"):                               # Studio の言語の切り替え = set_lang
        ui["lang"] = lang
        win.set_lang(lang)
        _pump(qapp)
        want = tips if lang == "en" else tuple("[%s] %s" % (lang, t) for t in tips)
        assert shown(fs) == want, (lang, shown(fs))
        assert (p.tool_actions["open"].toolTip() == open_en) == (lang == "en"), lang    # 対照: 道具の文も変わる
        checked += 1
    assert checked == 4
    ui["lang"] = "ja"                                                   # ja の窓に後から差し込んだ列も、差した時に ja
    win.set_lang("ja")
    second = _another_flow_strip(fs)
    p.set_strip_widget(second)
    _pump(qapp)
    assert shown(second) == tuple("[ja] " + t for t in tips), shown(second)
    # theme: 親の QSS の差し替え(Studio の theme の切り替え)で、列にも restyle が届く
    calls = []
    real = second.restyle
    second.restyle = lambda tr=None: (calls.append(tr), real(tr))[1]
    win.setStyleSheet("QLabel { color: #203040; }")
    _pump(qapp)
    _pump(qapp)
    assert len(calls) >= 1 and calls[-1] is p.tr_, calls
    n = len(calls)
    p.apply_theme()
    assert len(calls) == n + 1
    # 送る / 折り返す: set_overflow で渡し、後から差し込んだ列にも当てる。知らない形は断り、今の形のまま
    assert p.overflow() is None and second.mode == "scroll"
    assert p.set_overflow("wrap") == "wrap" and second.mode == "wrap" and p.overflow() == "wrap"
    assert p.set_overflow("scroll") == "scroll" and second.mode == "scroll"
    with pytest.raises(ValueError):
        p.set_overflow("fold")
    assert p.overflow() == "scroll" and second.mode == "scroll"
    p.set_overflow("wrap")
    third = _another_flow_strip(fs)
    assert third.mode == "scroll"
    p.set_strip_widget(third)
    assert third.mode == "wrap" and shown(third) == tuple("[ja] " + t for t in tips)
    _close_quietly(win)
    # 既定の部品(送りも折り返しも持たない)の窓でも、形は覚えるだけで落ちない
    plain = _window(qapp)
    assert plain.panel.set_overflow("wrap") == "wrap" and plain.panel.overflow() == "wrap"
    assert plain.panel.strip_widget().objectName() == "panelStrip"
    _close_quietly(plain)


def test_params_studio_entry_takes_the_strip_rule_and_overflow(qapp, fusion, ini, tmp_path, flow_strip):
    """確かめの指摘(medium): Studio の入口(show_params_window)から、道具の列の部品・向きの規則・収まらない時の形を渡せる。
    D87 の引き継ぎの繋ぎ方 show_params_window(win, paths, tr, lang=, confirm=) で開いた窓は、規則も送る部品も持たず、
    横長の窓(1280x280)でも道具の列が上のままだった(直す前は strip= / strip_rule= / overflow= が無く TypeError)。
    渡して開いた窓は 1280x280 で左に縦 1 列、送りのボタンを押して 10 個全部に届く。同じ親から入口をもう一度通っても、
    部品は作り直さない(1 つのまま)。知らない形は窓に触る前に断る。"""
    paths = _three_files(tmp_path)
    parent = QtWidgets.QWidget()
    made = []

    def make():
        made.append(flow_strip if not made else _another_flow_strip(flow_strip))
        return made[-1]

    asked = []

    def rule(w, h, now):                                                # studio_panels.strip_side(w, h, now, "auto") と同じ式
        asked.append((w, h, now))
        ratio = w / h
        return "left" if ratio >= 2.2 else ("top" if ratio <= 1.6 else now)

    win = Q.show_params_window(parent, paths, M.make_tr("en"), lang="ja", strip=make, strip_rule=rule,
                               overflow="scroll")
    p = win.panel
    assert parent._params_window is win and made == [flow_strip] and p.strip_widget() is flow_strip
    assert p.overflow() == "scroll" and flow_strip.mode == "scroll" and len(asked) >= 1
    win.resize(1280, 280)
    _pump(qapp)
    _pump(qapp)
    assert (p.strip_side(), p.strip_side_shown(), flow_strip.orientation) == ("left", "left", "v")
    assert flow_strip.b_on.isVisible()                                  # 縦に入りきらない: 送る
    seen, presses = _reach_by_arrows(qapp, p, flow_strip)
    assert seen == set(BUTTONS) and len(seen) == 10 and presses >= 1, (sorted(set(BUTTONS) - seen), presses)
    assert win.rect().contains(_rect_in(flow_strip, win)) and not _rect_in(flow_strip, win).intersects(_rect_in(p.status, win))
    # 2 回目: 部品は作らない・形は変えられる
    again = Q.show_params_window(parent, (), M.make_tr("en"), lang="ja", strip=make, overflow="wrap")
    assert again is win and len(made) == 1 and p.strip_widget() is flow_strip and flow_strip.mode == "wrap"
    with pytest.raises(ValueError):                                     # 知らない形: 窓に触る前に断る
        Q.show_params_window(parent, (), M.make_tr("en"), lang="ja", overflow="fold")
    assert p.overflow() == "wrap" and flow_strip.mode == "wrap"
    _close_quietly(win)
    parent.deleteLater()
    # 対照: 部品も規則も渡さない入口(元の引き継ぎの形)は、既定の部品・規則なしで 1280x280 でも上の 1 行
    other = QtWidgets.QWidget()
    plain = Q.show_params_window(other, paths, M.make_tr("en"), lang="ja")
    plain.resize(1280, 280)
    _pump(qapp)
    _pump(qapp)
    assert plain.panel.strip_widget().objectName() == "panelStrip" and plain.panel.strip_side_shown() == "top"
    _close_quietly(plain)
    other.deleteLater()


#: 確認の箱で使わない物: QMessageBox の静的な箱(決まったボタン・既定のボタンを持つ)と標準ボタン(設計書 P09・B0)。
_MB_STATIC = ("question", "warning", "information", "critical", "about", "aboutQt")
_MB_STANDARD = ("Ok", "Save", "SaveAll", "Open", "Yes", "YesToAll", "No", "NoToAll", "Abort", "Retry", "Ignore", "Close",
                "Cancel", "Discard", "Help", "Apply", "Reset", "RestoreDefaults", "StandardButton", "StandardButtons",
                "setStandardButtons", "standardButton")


def _tail(node) -> str | None:
    """``a.b.C`` / ``C`` の最後の名前(それ以外は None)。"""
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def _nodes_in_functions(tree) -> list:
    """(節, それを含む一番内側の関数の名前)の並び。モジュールの直下は "<module>"。"""
    out = []

    def go(node, fn):
        for ch in ast.iter_child_nodes(node):
            out.append((ch, fn))
            go(ch, ch.name if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn)

    go(tree, "<module>")
    return out


def test_params_confirm_boxes_are_built_in_one_place():
    """確かめの指摘(low): G09(a) を構文木で数える。D88 の門は決まった 6 つの入口を動かして本物の箱を数えるので、試験が
    動かさない道に QMessageBox.question のような箱(既定のボタンが「はい」)を足しても緑のままだった。
    窓のモジュールで QMessageBox を作るのは _build_confirm_box の 1 か所だけ・静的な箱と標準ボタンと別名は 0。作る関数と
    見せる関数を呼ぶのは聞く所 _confirm だけで、_confirm を呼ぶのは 4 つの聞く関数(6 つの入口は全部ここを通る)。
    束のモデルは Qt を持たない。"""
    with io.open(os.path.join(os.path.dirname(os.path.abspath(Q.__file__)), "studio_params_qt.py"), encoding="utf-8") as fh:
        nodes = _nodes_in_functions(ast.parse(fh.read()))
    calls = [(n, fn) for n, fn in nodes if isinstance(n, ast.Call)]
    assert len(nodes) >= 10000 and len(calls) >= 1000, (len(nodes), len(calls))       # 木を全部歩いた
    assert [fn for n, fn in calls if _tail(n.func) == "QMessageBox"] == ["_build_confirm_box"]
    on_box = [(n.attr, fn) for n, fn in nodes if isinstance(n, ast.Attribute) and _tail(n.value) == "QMessageBox"]
    assert len(on_box) >= 12, on_box                                    # 役割の表・アイコン・NoButton を数えている
    banned = [(a, fn) for a, fn in on_box if a in _MB_STATIC or a in _MB_STANDARD]
    banned += [(n.attr, fn) for n, fn in nodes if isinstance(n, ast.Attribute) and n.attr in _MB_STANDARD[-2:]]
    assert banned == [], banned
    aliases = [fn for n, fn in nodes if isinstance(n, (ast.Assign, ast.AnnAssign, ast.NamedExpr))
               and isinstance(n.value, (ast.Name, ast.Attribute)) and _tail(n.value) == "QMessageBox"]
    assert aliases == [], aliases
    for name in ("_build_confirm_box", "_exec_confirm_box"):
        assert [fn for n, fn in calls if _tail(n.func) == name] == ["_confirm"], name
    asking = sorted(fn for n, fn in calls if _tail(n.func) == "_confirm")
    assert asking == ["_ask_losses_box", "_ask_overwrite_box", "_ask_unsaved_box", "_ask_unsaved_box"], asking
    assert len(_BOX_SHAPES) >= 6                                        # D88 の門が本物の箱で動かす入口
    assert {k for _title, buttons in _BOX_SHAPES.values() for k, _s in buttons} == set(Q._CONFIRM_ROLES)
    with io.open(os.path.join(os.path.dirname(os.path.abspath(M.__file__)), "studio_params_model.py"), encoding="utf-8") as fh:
        model = fh.read()
    assert len(model) > 10000 and "QMessageBox" not in model and "PySide6" not in model


def test_params_window_modules_come_from_this_tree():
    """確かめの指摘(low): 写しで試すと fullseye/__init__ が作業木を sys.path の先頭に入れ、写しの試験が作業木の
    studio_params_qt を黙って読んだ。この試験のファイルは読み込みの時に、窓の 2 つのモジュールがこの試験と同じ木から
    読まれた事を確かめて、違えば収集の誤りで止める(上の _WINDOW_TREES)。ここでは止め金そのものが効いている事を数える。"""
    here = os.path.normcase(os.path.realpath(ROOT))
    assert _WINDOW_TREES == {here} and len({M.__file__, Q.__file__}) == 2
    for m in (M, Q):
        assert os.path.normcase(os.path.dirname(os.path.realpath(m.__file__))) == here, m.__file__


#: 依頼文 B6 の門の試験(5 本)。
_BRIEF_GATES = ("test_params_boxes_default_and_escape_cancel_real_box", "test_params_rejected_cell_keeps_text_and_marks_invalid",
                "test_params_no_ctrl_d_binding", "test_params_drop_reject_says_why", "test_params_search_zero_hits_says_no_match")


def test_params_qt_tests_fix_the_style_to_fusion():
    """確かめの指摘(low): B0「試験の書き方: Qt の様式は Fusion に固定」。1.2.0 の節(fusion の fixture から後ろ)で qapp を
    受ける試験は、どれも fusion も受ける。依頼文 B6 の門 5 本は全部その中にある。直す前は D90・D91 の門を含む 10 本に
    無かった(中身が様式に左右されない試験でも、決まりに揃える)。"""
    with io.open(os.path.abspath(__file__), encoding="utf-8") as fh:
        body = ast.parse(fh.read()).body
    start = [i for i, n in enumerate(body) if isinstance(n, ast.FunctionDef) and n.name == "fusion"]
    assert len(start) == 1
    tests = {}
    for n in body[start[0]:]:
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"):
            args = [a.arg for a in n.args.args]
            if "qapp" in args:
                tests[n.name] = args
    assert len(tests) >= 35 and set(_BRIEF_GATES) <= set(tests), (len(tests), sorted(set(_BRIEF_GATES) - set(tests)))
    assert sorted(k for k, v in tests.items() if "fusion" not in v) == []
