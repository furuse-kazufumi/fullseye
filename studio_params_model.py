# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_params_model — パラメータの束を並べて見る・直す窓のモデル(Qt なし)。

窓(``studio_params_qt``)の中身は全部ここにある。行 = キー(ドット区切りの階層)、列 = 束(ファイル 1 つ)。

* **読む**: JSON / TOML / YAML は ``fullseye.parambundle.load_params`` をそのまま通す(門を緩めない)。XML は
  ``safe_xml.safe_xml_parse``(DOCTYPE・大きさ・要素数・深さの門)で読み、下の小さな文法だけを受けて、同じ
  ``ParamBundle`` の門(数の欄の文字列・キーの衝突・非有限)を通す。断られた理由は読み手の文をそのまま返す。
* **比べる**: ``parambundle.params_compare``(``"0.55 um"`` と ``"550 nm"`` は同じ、書き方の違いは別の印)。
* **直す**: 値の型を保つ。数の欄に文字、単位つきの欄に次元の違う単位、文字の欄に単位つきの数 … は断って理由を
  返す。``eval`` は使わない(列は ``json.loads`` → ``ast.literal_eval``)。編集・写しは Undo / Redo できる。
* **書く**: 元の形式(JSON / YAML / XML)のまま、同じフォルダの一時ファイルに書き、**読み直して値と型が同じ
  ことを確かめてから** ``os.replace``(原子的)。途中で落ちても元のファイルは残る。コメント・include・参照・
  アンカーのように書き戻すと失われる物は、書く前に :class:`Outcome` で返す(``accept_losses=True`` で進む)。
  TOML は読むだけ(標準の ``tomllib`` に書き手が無い)なので、別の形式へ「名前を付けて保存」する。
* **外での変更**: 読んだ時の更新時刻・大きさ・SHA-256 を持ち、:meth:`ParamsModel.check_external` で比べる。

XML の文法(この窓が書く形。``type`` を省いた手書きは true / false・整数・小数・それ以外は文字列と読む)::

    <?xml version="1.0" encoding="UTF-8"?>
    <params fullseye_kind="params" version="1">
      <section name="camera">
        <param name="fx" type="float">800.5</param>
        <param name="wavelength" type="quantity">550 nm</param>
        <param name="size" type="list"><item type="int">640</item><item type="int">480</item></param>
      </section>
    </params>

画面の文は英語が正(:data:`MESSAGES`)。訳は ``studio_assets/studio_params_i18n.json``(:func:`make_tr`)。
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import safe_xml
from fullseye import parambundle
from fullseye.parambundle import ParamBundle, ParamError, ParamFileError, Quantity

__all__ = [
    "ParamsModel", "Outcome", "Column", "Row", "Node", "FileStamp", "EditRefused",
    "FORMATS", "WRITABLE_FORMATS", "WRITE_EXTS", "MESSAGES", "LANGS",
    "read_bundle", "write_bundle_atomic", "bundle_text", "kind_of", "format_value", "parse_edit", "same_value",
    "example_bundles", "load_i18n_table", "make_tr",
]

#: 拡張子 → 形式。
FORMATS: dict[str, str] = {".json": "json", ".toml": "toml", ".yaml": "yaml", ".yml": "yaml", ".xml": "xml"}
#: この窓が書ける形式(TOML は読むだけ)と、その拡張子。
WRITABLE_FORMATS: tuple[str, ...] = ("json", "yaml", "xml")
WRITE_EXTS: dict[str, str] = {".json": "json", ".yaml": "yaml", ".yml": "yaml", ".xml": "xml"}
#: 対訳を持つ言語(en は原文)。
LANGS: tuple[str, ...] = ("en", "ja", "zh", "tw", "ko", "de")

_XML_ROOT = "params"
_XML_KIND = "params"
_XML_VERSION = 1
_NUM_RE = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
_INT_RE = re.compile(r"[+-]?\d+")
_COMMENT_LINE = re.compile(r"(?:^|\s)#")
_YAML_PLAIN_OK = re.compile(r"[A-Za-z_][A-Za-z0-9_\-]*")
_YAML_WORDS = frozenset("y n yes no on off true false null none nan inf".split())

#: 画面に出す文の型(英語が正。``%`` の並びは訳でも変えない)。鍵は :class:`Outcome` の ``code``。
MESSAGES: dict[str, str] = {
    # 読む
    "load.refused": "Could not open %s (%s)",            # 読み手・OS の英語の理由は括弧で後ろに(D112)
    "load.duplicate": "%s is already open in this window",
    # 直す
    "edit.readonly": "%s is read-only here (TOML is read but not written); use Save As to make a JSON, YAML or XML copy",
    "edit.no_column": "there is no such column",
    "edit.no_key": "%s: this bundle has no such key (copy a value from another column to add it)",
    "edit.bool": "%s: this field is true / false; %r is neither",
    "edit.number": "%s: this field holds a number; %r is not a number",
    "edit.number_unit": "%s: this field holds a plain number; %r has a unit, which would change its type",
    "edit.quantity": "%s: this field holds a number with a unit (such as 550 nm); %r is not one",
    "edit.dimension": "%s: the unit must stay a %s unit; %r is a %s unit",
    "edit.str_quantity": "%s: this field holds text; %r would be read back as a number with a unit",
    "edit.list": "%s: this field holds a list such as [1, 2, 3]; %r is not a list of plain values",
    "edit.list_kind": "%s: this list holds %s values; %r would add %s",
    "edit.gate": "%s",
    "edit.same": "%s: the value is unchanged",
    "copy.missing": "%s: %s has no value to copy",
    "copy.same": "%s: both columns already hold the same value",
    "copy.nothing": "there is nothing to copy: the columns do not differ",
    "note.type_changed": "%s: the type changed from %s to %s",
    "note.key_added": "%s: the key was added to %s",
    # Undo / Redo
    "undo.empty": "nothing to undo",
    "redo.empty": "nothing to redo",
    "label.edit": "edit %s",
    "label.copy": "copy %s",
    "label.copy_column": "copy %d value(s) to %s",
    # 書く
    "save.no_path": "%s has no file yet; use Save As",
    "save.format": "%s: cannot write %s here (writable: .json, .yaml / .yml, .xml)",
    "save.external": "%s changed on disk after it was read; reload it, or save again to overwrite",
    "save.gone": "%s no longer exists on disk; saving will create it again",
    "save.confirm": "saving %s drops some things from the file",
    "save.failed": "could not save %s; the file on disk is unchanged (%s)",
    "save.verify": "could not save %s: the written file does not read back the same at %s (the file on disk is unchanged)",
    "save.done": "saved %s",
    "save.clean": "%s has no unsaved changes",
    "loss.include": "values from the included file(s) %s are written into this file and the include line is dropped",
    "loss.refs": "%d reference(s) to another key are written as plain values",
    "loss.comments": "comments are not kept (%d line(s))",
    "loss.anchors": "YAML anchors and aliases are expanded (%d)",
    "loss.layout": "layout is normalised (indentation, quoting, number spelling such as 1.50 -> 1.5)",
    "loss.convert": "the file is written as %s (it was read as %s)",
    # 外での変更
    "external.changed": "%s changed on disk",
    "external.missing": "%s was removed from disk",
    "reload.done": "reloaded %s",
    # 実行との連動
    "used.none": "the last run read no key of the open bundles",
    "used.count": "the last run read %d key(s)",
}


# ----------------------------------------------------------------------------------------------
# 対訳(Qt なし)
# ----------------------------------------------------------------------------------------------
_I18N_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "studio_assets", "studio_params_i18n.json")
_I18N_CACHE: dict[str, dict] = {}


def load_i18n_table(path: str | None = None) -> dict:
    """対訳の表 ``{英語の文: {言語: 訳}}``。読めない・壊れていれば ``ValueError``(黙って空にしない)。"""
    p = path or _I18N_PATH
    if p in _I18N_CACHE:
        return _I18N_CACHE[p]
    try:
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ValueError("cannot read the translation table: %s (%s)" % (p, exc)) from exc
    strings = data.get("strings") if isinstance(data, dict) else None
    if not isinstance(strings, dict):
        raise ValueError("the translation table has no 'strings': %s" % p)
    _I18N_CACHE[p] = strings
    return strings


def make_tr(lang: str = "en", table: dict | None = None) -> Callable[[str], str]:
    """言語 ``lang`` の ``tr``(英語の文 → その言語の文)。表に無い文は英語のまま。知らない言語は ``ValueError``。"""
    if lang not in LANGS:
        raise ValueError("language must be one of %s (got %r)" % (" / ".join(LANGS), lang))
    tab = load_i18n_table() if table is None else table

    def tr(text: str) -> str:
        if lang == "en" or not text:
            return text
        return tab.get(text, {}).get(lang, text)

    tr.lang = lang  # type: ignore[attr-defined]
    return tr


def _identity(text: str) -> str:
    return text


# ----------------------------------------------------------------------------------------------
# 結果(断った理由・注意・確認が要るか)
# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Outcome:
    """操作 1 回の結果。``ok`` が偽なら ``code`` / ``args`` が理由。``notes`` は起きた事(型が変わった、失われる物)。"""

    ok: bool
    code: str = ""
    args: tuple = ()
    notes: tuple[tuple[str, tuple], ...] = ()
    needs_confirm: bool = False      #: 失われる物・外での変更があり、承知の上でもう一度呼べば進む
    column: int | None = None
    path: str | None = None
    count: int = 0                   #: 変えたセルの数など

    def text(self, tr: Callable[[str], str] | None = None) -> str:
        """理由(または済んだ事)の文。``tr`` を渡すとその言語で。"""
        return _render(self.code, self.args, tr) if self.code else ""

    @property
    def reason(self) -> str:
        """英語の文(ログ・試験用)。"""
        return self.text()

    def note_texts(self, tr: Callable[[str], str] | None = None) -> list[str]:
        """注意の文の並び。"""
        return [_render(c, a, tr) for c, a in self.notes]


def _render(code: str, args: tuple, tr: Callable[[str], str] | None = None) -> str:
    tpl = MESSAGES[code]
    if tr is not None:
        tpl = tr(tpl)
    try:
        return tpl % args if args else tpl % ()
    except (TypeError, ValueError):                 # 訳の % が壊れていたら原文(壊れた訳より原文)
        return MESSAGES[code] % args


class EditRefused(ValueError):
    """編集を断った。``code`` / ``args`` は :data:`MESSAGES` の鍵と値。"""

    def __init__(self, code: str, args: tuple) -> None:
        super().__init__(MESSAGES[code] % args)
        self.code = code
        self.args_ = args


# ----------------------------------------------------------------------------------------------
# 値の型・文字への変換・編集の解釈
# ----------------------------------------------------------------------------------------------
def kind_of(value: Any) -> str:
    """値の型の名前: ``bool`` / ``int`` / ``float`` / ``quantity`` / ``str`` / ``list``。"""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, Quantity):
        return "quantity"
    if isinstance(value, str):
        return "str"
    if isinstance(value, (tuple, list)):
        return "list"
    raise TypeError("not a bundle value: %s" % type(value).__name__)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Quantity):
        return str(value)
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    return value


def format_value(value: Any) -> str:
    """セルに出す文字(編集の初期値も同じ)。float は最短の repr、真偽は true / false、列は JSON の書き方。"""
    k = kind_of(value)
    if k == "bool":
        return "true" if value else "false"
    if k == "int":
        return str(value)
    if k == "float":
        return repr(value)
    if k == "quantity":
        return str(value)
    if k == "str":
        return value
    return json.dumps(_jsonable(value), ensure_ascii=False, allow_nan=False)


def same_value(a: Any, b: Any) -> bool:
    """**値も型も**同じか(``1`` と ``1.0`` と ``True`` は別。未保存の判定と書いた後の検算に使う)。"""
    if isinstance(a, (tuple, list)) or isinstance(b, (tuple, list)):
        return (isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)) and len(a) == len(b)
                and all(same_value(x, y) for x, y in zip(a, b)))
    if isinstance(a, Quantity) or isinstance(b, Quantity):
        return (isinstance(a, Quantity) and isinstance(b, Quantity) and a.unit == b.unit and a.text == b.text
                and type(a.value) is type(b.value) and a.value == b.value)
    return type(a) is type(b) and a == b


def _number(text: str) -> int | float | None:
    s = text.strip()
    if not _NUM_RE.fullmatch(s):
        return None
    try:
        v: int | float = int(s) if _INT_RE.fullmatch(s) else float(s)
    except ValueError:                               # 桁が多すぎる整数
        return None
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def _quantity(text: str) -> Quantity | None:
    try:
        return parambundle.parse_quantity(text)
    except ParamError:
        return None


def _flat_kinds(value: Any) -> set[str]:
    out: set[str] = set()
    for v in value:
        if isinstance(v, (tuple, list)):
            out |= _flat_kinds(v)
        else:
            k = kind_of(v)
            out.add("number" if k in ("int", "float") else k)
    return out


def _plain_list(obj: Any) -> bool:
    if not isinstance(obj, (list, tuple)):
        return False
    for v in obj:
        if isinstance(v, (list, tuple)):
            if not _plain_list(v):
                return False
        elif isinstance(v, float):
            if not math.isfinite(v):
                return False
        elif not isinstance(v, (bool, int, str)):
            return False
    return True


def _refuse_constant(name: str) -> Any:
    raise ValueError(name)


def _parse_list(text: str) -> list | tuple | None:
    """``[1, 2, 3]`` / ``(1, 2)`` を読む。JSON → Python のリテラルの順(式は評価しない)。"""
    try:
        obj = json.loads(text, parse_constant=_refuse_constant)
    except (ValueError, RecursionError):
        try:
            obj = ast.literal_eval(text.strip())
        except (ValueError, SyntaxError, MemoryError, RecursionError, TypeError):
            return None
    return obj if _plain_list(obj) else None


def parse_edit(key: str, current: Any, text: str) -> Any:
    """``current`` の型を保って ``text`` を値にする。保てなければ :class:`EditRefused`(理由つき)。

    * 真偽: ``true`` / ``false`` だけ。
    * 数: 数のリテラルだけ。今が小数なら ``800`` も小数のまま持つ。今が整数で ``800.5`` なら小数になる(同じ「数」)。
    * 単位つき: ``数 + 単位``。単位の次元は変えられない(nm → um は可、nm → ms は不可)。
    * 文字: そのまま。ただし ``"550 nm"`` のように読み直すと単位つきの数になる文は断る。
    * 列: ``[1, 2, 3]``。中身の種類(数・文字・真偽)を増やさない。
    """
    kind = kind_of(current)
    s = text.strip()
    if kind == "bool":
        low = s.lower()
        if low not in ("true", "false"):
            raise EditRefused("edit.bool", (key, text))
        return low == "true"
    if kind in ("int", "float"):
        v = _number(s)
        if v is None:
            code = "edit.number_unit" if _quantity(s) is not None else "edit.number"
            raise EditRefused(code, (key, text))
        return float(v) if kind == "float" else v
    if kind == "quantity":
        q = _quantity(s)
        if q is None:
            raise EditRefused("edit.quantity", (key, text))
        if q.dimension != current.dimension:
            raise EditRefused("edit.dimension", (key, current.dimension, text, q.dimension))
        return q
    if kind == "str":
        if _quantity(text) is not None:
            raise EditRefused("edit.str_quantity", (key, text))
        return text
    obj = _parse_list(text)
    if obj is None:
        raise EditRefused("edit.list", (key, text))
    have = _flat_kinds(current)
    new = _flat_kinds(_normalise(key, obj))
    extra = sorted(new - have)
    if have and extra:
        raise EditRefused("edit.list_kind", (key, " / ".join(sorted(have)), text, " / ".join(extra)))
    return obj


def _normalise(key: str, value: Any) -> Any:
    """束の門(``ParamBundle`` の正規化と検査)を 1 つの値に通す。断られたら :class:`EditRefused`。"""
    try:
        return ParamBundle({key: value})[key]
    except ParamError as e:
        raise EditRefused("edit.gate", (str(e),)) from e


# ----------------------------------------------------------------------------------------------
# 読む
# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class FileStamp:
    """読んだ時のファイルの姿(外での変更の検出に使う)。"""

    mtime_ns: int
    size: int
    sha256: str


def _stamp(path: str) -> FileStamp:
    st = os.stat(path)
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return FileStamp(st.st_mtime_ns, st.st_size, digest)


def _xml_fail(where: str, msg: str) -> ParamFileError:
    return ParamFileError("%s: %s" % (where, msg))


def _xml_name(el: ET.Element, where: str, prefix: str, seen: set[str]) -> str:
    name = el.get("name")
    if name is None:
        raise _xml_fail(where, "<%s> under %s needs a name attribute" % (el.tag, prefix or "<params>"))
    if not name or name != name.strip() or "." in name or "\x00" in name:
        raise _xml_fail(where, "invalid key %r (empty / padded / contains '.'; nest with <section> instead)" % name)
    if name in seen:
        raise _xml_fail(where, "duplicate key %r under %s" % (name, prefix or "<params>"))
    seen.add(name)
    return name


def _xml_attrs(el: ET.Element, allowed: tuple[str, ...], where: str) -> None:
    extra = sorted(set(el.attrib) - set(allowed))
    if extra:
        raise _xml_fail(where, "<%s> has an unknown attribute %r (known: %s)" % (el.tag, extra[0], ", ".join(allowed)))


def _xml_scalar(text: str, typ: str | None, key: str, where: str) -> Any:
    s = text.strip()
    if typ is None:
        if s in ("true", "false"):
            return s == "true"
        v = _number(s)
        return v if v is not None else s
    if typ == "bool":
        if s not in ("true", "false"):
            raise _xml_fail(where, "%s: type bool needs true or false, got %r" % (key, text))
        return s == "true"
    if typ in ("int", "float"):
        v = _number(s)
        if v is None or (typ == "int" and not isinstance(v, int)):
            raise _xml_fail(where, "%s: type %s needs a %s, got %r"
                            % (key, typ, "whole number" if typ == "int" else "finite number", text))
        return float(v) if typ == "float" else v
    if typ == "quantity":
        if _quantity(s) is None:
            raise _xml_fail(where, "%s: type quantity needs a number and a known unit such as \"550 nm\", got %r" % (key, text))
        return s
    if typ == "str":
        if _quantity(text) is not None:
            raise _xml_fail(where, "%s: type str holds %r, which is a number with a unit (use type=\"quantity\")" % (key, text))
        return text
    raise _xml_fail(where, "%s: unknown type %r (known: bool, int, float, quantity, str, list)" % (key, typ))


def _xml_value(el: ET.Element, key: str, where: str) -> Any:
    typ = el.get("type")
    if typ == "list" or (typ is None and len(el)):
        if (el.text or "").strip():
            raise _xml_fail(where, "%s: text %r beside the <item> elements of a list" % (key, (el.text or "").strip()))
        out = []
        for i, ch in enumerate(el):
            if ch.tag != "item":
                raise _xml_fail(where, "%s: a list holds <item> elements, found <%s>" % (key, ch.tag))
            _xml_attrs(ch, ("type",), where)
            out.append(_xml_value(ch, "%s[%d]" % (key, i), where))
        return out
    if len(el):
        raise _xml_fail(where, "%s: <%s> inside a value of type %s (only type=\"list\" has children)" % (key, el[0].tag, typ))
    return _xml_scalar(el.text or "", typ, key, where)


def _xml_section(el: ET.Element, prefix: str, where: str) -> dict[str, Any]:
    if (el.text or "").strip():
        raise _xml_fail(where, "text %r directly inside %s (values go in <param>)"
                        % ((el.text or "").strip()[:40], "<section %s>" % prefix if prefix else "<params>"))
    out: dict[str, Any] = {}
    seen: set[str] = set()
    for ch in el:
        if ch.tag == "section":
            _xml_attrs(ch, ("name",), where)
            name = _xml_name(ch, where, prefix, seen)
            out[name] = _xml_section(ch, prefix + "." + name if prefix else name, where)
        elif ch.tag == "param":
            _xml_attrs(ch, ("name", "type"), where)
            name = _xml_name(ch, where, prefix, seen)
            out[name] = _xml_value(ch, prefix + "." + name if prefix else name, where)
        else:
            raise _xml_fail(where, "unknown element <%s> under %s (known: <section>, <param>)"
                            % (ch.tag, prefix or "<params>"))
    return out


def _read_xml(path: str, max_bytes: int) -> ParamBundle:
    try:
        size = os.path.getsize(path)
    except OSError as e:
        raise ParamFileError("cannot read %s: %s" % (path, e)) from e
    if size > max_bytes:
        raise ParamFileError("%s is %d bytes; limit is %d" % (path, size, max_bytes))
    try:
        with open(path, "rb") as fh:
            raw = fh.read(max_bytes + 1)
    except OSError as e:
        raise ParamFileError("cannot read %s: %s" % (path, e)) from e
    if len(raw) > max_bytes:
        raise ParamFileError("%s is larger than %d bytes" % (path, max_bytes))
    try:
        root = safe_xml.safe_xml_parse(raw, max_bytes=max_bytes, op="params")
    except safe_xml.UnsafeXMLError as e:
        raise ParamFileError("%s: %s" % (path, e)) from e
    except ET.ParseError as e:
        raise ParamFileError("%s: invalid XML: %s" % (path, e)) from e
    if root.tag != _XML_ROOT:
        raise _xml_fail(path, "the root element is <%s>, not <%s> (this is not a parameter bundle)" % (root.tag, _XML_ROOT))
    _xml_attrs(root, ("fullseye_kind", "version"), path)
    kind = root.get("fullseye_kind")
    if kind is not None and kind != _XML_KIND:
        raise _xml_fail(path, "this is a %r file, not %r" % (kind, _XML_KIND))
    ver = root.get("version")
    if ver is not None:
        if not _INT_RE.fullmatch(ver) or int(ver) < 1:
            raise _xml_fail(path, "'version' must be a positive integer, got %r" % ver)
        if int(ver) > _XML_VERSION:
            raise _xml_fail(path, "params version %s was written by a newer Fullseye (this one reads up to %d)"
                            % (ver, _XML_VERSION))
    tree = _xml_section(root, "", path)
    try:
        return ParamBundle(tree, name=os.path.basename(path))
    except ParamError as e:
        raise type(e)("%s: %s" % (path, e)) from e


def read_bundle(path: str | os.PathLike, *, max_bytes: int = parambundle.MAX_FILE_BYTES) -> ParamBundle:
    """ファイルを束にする。JSON / TOML / YAML は ``load_params``、XML は ``safe_xml`` + 上の文法。

    断る物は全部 :class:`fullseye.parambundle.ParamError`(読み手の文のまま)。
    """
    p = os.fspath(path)
    if FORMATS.get(os.path.splitext(p)[1].lower()) == "xml":
        if not os.path.isfile(p):
            raise ParamFileError("not a file: %s" % p)
        return _read_xml(p, max_bytes)
    return parambundle.load_params(p, max_bytes=max_bytes)


def _scan_raw(fmt: str, text: str) -> tuple[int, int]:
    """(コメントのある行の数, YAML のアンカー / エイリアスの数)。書き戻すと失われる物の見積もり。"""
    comments = anchors = 0
    if fmt in ("yaml", "toml"):
        comments = sum(1 for line in text.splitlines() if _COMMENT_LINE.search(line))
    elif fmt == "xml":
        comments = text.count("<!--")
    if fmt == "yaml":
        try:
            import yaml
            anchors = sum(1 for t in yaml.scan(text) if isinstance(t, (yaml.AnchorToken, yaml.AliasToken)))
        except Exception:                            # noqa: BLE001 -- 見積もりだけ。読めたファイルなので通常は起きない
            anchors = 0
    return comments, anchors


# ----------------------------------------------------------------------------------------------
# 書く
# ----------------------------------------------------------------------------------------------
def _nested(leaves: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in leaves.items():
        cur = out
        parts = k.split(".")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = _jsonable(v)
    return out


def _yaml_text(leaves: Mapping[str, Any]) -> str:
    try:
        import yaml
    except ImportError as e:                         # pragma: no cover - 環境による
        raise ParamFileError("writing YAML needs PyYAML: pip install \"fullseye[yaml]\"") from e

    class _Dumper(yaml.SafeDumper):
        """文字列は読み手で別の型に化けない物だけ素のまま、列は 1 行、節は段。"""

    def _str(d: Any, s: str) -> Any:
        plain = bool(_YAML_PLAIN_OK.fullmatch(s)) and s.lower() not in _YAML_WORDS
        return d.represent_scalar("tag:yaml.org,2002:str", s, style=None if plain else '"')

    def _seq(d: Any, seq: list) -> Any:
        return d.represent_sequence("tag:yaml.org,2002:seq", seq, flow_style=True)

    _Dumper.add_representer(str, _str)
    _Dumper.add_representer(list, _seq)
    tree = _nested(leaves)
    if not tree:
        return "{}\n"
    return yaml.dump(tree, Dumper=_Dumper, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)


def _xml_put(parent: ET.Element, tag: str, name: str | None, value: Any) -> None:
    kind = kind_of(value)
    attrs = {} if name is None else {"name": name}
    attrs["type"] = kind
    el = ET.SubElement(parent, tag, attrs)
    if kind == "list":
        for v in value:
            _xml_put(el, "item", None, v)
    else:
        el.text = format_value(value)


def _xml_text(leaves: Mapping[str, Any]) -> str:
    root = ET.Element(_XML_ROOT, {"fullseye_kind": _XML_KIND, "version": str(_XML_VERSION)})
    nodes: dict[str, ET.Element] = {}
    for key, v in leaves.items():
        parts = key.split(".")
        parent, path = root, ""
        for part in parts[:-1]:
            path = part if not path else path + "." + part
            if path not in nodes:
                nodes[path] = ET.SubElement(parent, "section", {"name": part})
            parent = nodes[path]
        _xml_put(parent, "param", parts[-1], v)
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def bundle_text(leaves: Mapping[str, Any], fmt: str) -> str:
    """葉の表を ``fmt``(json / yaml / xml)の本文にする(書く前の姿。ファイルには触らない)。"""
    if fmt == "json":
        return json.dumps(_nested(leaves), allow_nan=False, ensure_ascii=False, indent=2) + "\n"
    if fmt == "yaml":
        return _yaml_text(leaves)
    if fmt == "xml":
        return _xml_text(leaves)
    raise ParamError("cannot write format %r (writable: %s)" % (fmt, ", ".join(WRITABLE_FORMATS)))


class _VerifyError(ParamError):
    """書いた物を読み直したら違った(``key`` がその場所)。"""

    def __init__(self, key: str) -> None:
        super().__init__("written file does not read back the same at %s" % key)
        self.key = key


def write_bundle_atomic(leaves: Mapping[str, Any], path: str | os.PathLike) -> str:
    """葉の表を ``path`` の拡張子の形式で**原子的に**書く。書いたパスを返す。

    同じフォルダの一時ファイルへ書く → 読み手(:func:`read_bundle`)で読み直し、**値も型も**同じことを確かめる →
    ``os.replace``。どこで落ちても元のファイルは変わらず、一時ファイルは残さない。JSON は既存の
    ``parambundle.save_params`` が書く。
    """
    p = os.fspath(path)
    ext = os.path.splitext(p)[1].lower()
    fmt = WRITE_EXTS.get(ext)
    if fmt is None:
        raise ParamError("cannot write %r here (writable: .json, .yaml / .yml, .xml)" % ext)
    folder = os.path.dirname(os.path.abspath(p))
    if not os.path.isdir(folder):
        raise ParamError("folder does not exist: %s" % folder)
    want = dict(leaves)
    bundle = ParamBundle(want, name=os.path.basename(p))        # 束の門(型・キーの衝突)を書く前にも通す
    fd, tmp = tempfile.mkstemp(prefix=".params-", suffix=ext, dir=folder)
    try:
        if fmt == "json":
            os.close(fd)
            parambundle.save_params(bundle, tmp)
        else:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(bundle_text(want, fmt))
                fh.flush()
                os.fsync(fh.fileno())
        back = read_bundle(tmp)
        got = {k: back[k] for k in back}
        for k in want:
            if k not in got or not same_value(bundle[k], got[k]):
                raise _VerifyError(k)
        for k in got:
            if k not in want:
                raise _VerifyError(k)
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return p


# ----------------------------------------------------------------------------------------------
# 表のモデル
# ----------------------------------------------------------------------------------------------
class _Missing:
    """その束にキーが無い、の印(履歴の中だけで使う)。"""

    def __repr__(self) -> str:
        return "<missing>"


_MISSING = _Missing()


@dataclass
class Column:
    """1 つの束(列)。``leaves`` が今の値、``saved`` がファイルにある値。"""

    cid: int
    name: str                                  #: 列の見出し(窓の中で一意)
    path: str | None                           #: ファイル(コードから足した束は None)
    fmt: str | None                            #: json / toml / yaml / xml
    leaves: dict[str, Any]
    saved: dict[str, Any]
    bundle_name: str = ""                      #: 読み手が付けた名前(ファイル名)。ParamReport.bundle と照らす
    stamp: FileStamp | None = None
    includes: tuple[str, ...] = ()             #: include で読んだ別ファイル
    refs: int = 0                              #: 参照で入った値の数
    comments: int = 0
    anchors: int = 0
    used: dict[str, tuple[str, ...]] = field(default_factory=dict)   #: 直前の実行が読んだキー → (op.引数, …)
    _bundle: ParamBundle | None = None

    @property
    def writable(self) -> bool:
        """編集できるか(TOML は読むだけ)。"""
        return self.fmt != "toml"

    def bundle(self) -> ParamBundle:
        """今の値の :class:`ParamBundle`(変えるたびに作り直す)。"""
        if self._bundle is None:
            self._bundle = ParamBundle(dict(self.leaves), name=self.name)
        return self._bundle

    def dirty(self) -> bool:
        """未保存の変更があるか(値も型も比べる)。"""
        if len(self.leaves) != len(self.saved):
            return True
        return any(k not in self.saved or not same_value(v, self.saved[k]) for k, v in self.leaves.items())

    def cell_dirty(self, key: str) -> bool:
        """このセルが保存済みの値と違うか。"""
        a, b = self.leaves.get(key, _MISSING), self.saved.get(key, _MISSING)
        if a is _MISSING or b is _MISSING:
            return a is not b
        return not same_value(a, b)


@dataclass(frozen=True)
class Row:
    """1 キーの行。``values`` は列の順(無ければ None)。"""

    key: str
    values: tuple[Any, ...]
    status: str                  #: same / differ / partial(parambundle.CompareRow と同じ語)
    notation_differs: bool = False
    used: bool = False           #: 直前の実行が読んだ


@dataclass
class Node:
    """木の節点。節(``row`` が None)か葉。"""

    key: str
    label: str
    row: Row | None = None
    children: list["Node"] = field(default_factory=list)
    differ: int = 0              #: 配下の「違う」行の数(葉は自分)
    partial: int = 0


@dataclass(frozen=True)
class _Change:
    code: str
    args: tuple
    cells: tuple[tuple[int, str, Any, Any], ...]      # (cid, key, old, new)


class ParamsModel:
    """複数の束を列に並べた表。読む・比べる・絞る・写す・直す・戻す・書く・外での変更を見る。"""

    def __init__(self, *, max_bytes: int = parambundle.MAX_FILE_BYTES) -> None:
        self.columns: list[Column] = []
        self._max_bytes = max_bytes
        self._next_cid = 1
        self._undo: list[_Change] = []
        self._redo: list[_Change] = []
        self._rows: tuple[Row, ...] | None = None

    # -- 列 -------------------------------------------------------------------------------------
    def _unique_name(self, path: str | None, base: str) -> str:
        names = {c.name for c in self.columns}
        if base not in names:
            return base
        if path:
            parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
            cand = "%s/%s" % (parent, base) if parent else base
            if cand not in names:
                return cand
        i = 2
        while "%s #%d" % (base, i) in names:
            i += 1
        return "%s #%d" % (base, i)

    def _read_column(self, path: str, cid: int, name: str | None) -> Column:
        ext = os.path.splitext(path)[1].lower()
        bundle = read_bundle(path, max_bytes=self._max_bytes)
        fmt = FORMATS[ext]
        leaves = {k: bundle[k] for k in bundle}
        base = os.path.basename(path)
        includes: dict[str, None] = {}
        refs = 0
        for k in leaves:
            o = bundle.origin(k)
            if o.source != base:
                includes.setdefault(o.source, None)
            if o.ref:
                refs += 1
        stamp = _stamp(path)
        try:
            with open(path, "rb") as fh:
                text = fh.read().decode("utf-8-sig", "replace")
        except OSError:
            text = ""
        comments, anchors = _scan_raw(fmt, text)
        return Column(cid=cid, name=name or self._unique_name(path, base), path=os.path.abspath(path), fmt=fmt,
                      leaves=leaves, saved=dict(leaves), bundle_name=bundle.name, stamp=stamp,
                      includes=tuple(includes), refs=refs, comments=comments, anchors=anchors)

    def add_file(self, path: str | os.PathLike) -> Outcome:
        """ファイルを列として足す。読めなければ読み手の理由をそのまま返す(列は増えない)。"""
        p = os.fspath(path)
        ext = os.path.splitext(p)[1].lower()
        if ext not in FORMATS and ext not in (".jsonc", ".json5"):
            return Outcome(False, "load.refused", (os.path.basename(p) or p, "%s: unknown extension %r (use .json, .toml, .yaml / .yml or .xml)" % (p, ext)), path=p)
        ap = os.path.normcase(os.path.abspath(p))
        for c in self.columns:
            if c.path and os.path.normcase(c.path) == ap:
                return Outcome(False, "load.duplicate", (c.name,), column=self.columns.index(c), path=p)
        try:
            col = self._read_column(p, self._next_cid, None)
        except (ParamError, OSError) as e:
            return Outcome(False, "load.refused", (os.path.basename(p) or p, str(e)), path=p)
        self._next_cid += 1
        self.columns.append(col)
        self._rows = None
        return Outcome(True, column=len(self.columns) - 1, path=col.path)

    def add_bundle(self, bundle: ParamBundle | Mapping[str, Any], name: str = "bundle") -> Outcome:
        """コードから作った束を列として足す(ファイルは無い。保存は「名前を付けて保存」)。"""
        b = bundle if isinstance(bundle, ParamBundle) else ParamBundle(bundle, name=name)
        leaves = {k: b[k] for k in b}
        col = Column(cid=self._next_cid, name=self._unique_name(None, name), path=None, fmt=None,
                     leaves=leaves, saved=dict(leaves), bundle_name=b.name)
        self._next_cid += 1
        self.columns.append(col)
        self._rows = None
        return Outcome(True, column=len(self.columns) - 1)

    def remove_column(self, index: int) -> Outcome:
        """列を外す(ファイルには触らない)。その列に掛かる履歴も消える。"""
        if not 0 <= index < len(self.columns):
            return Outcome(False, "edit.no_column")
        cid = self.columns.pop(index).cid
        self._undo = [c for c in self._undo if all(cell[0] != cid for cell in c.cells)]
        self._redo = [c for c in self._redo if all(cell[0] != cid for cell in c.cells)]
        self._rows = None
        return Outcome(True)

    def _col(self, index: int) -> Column | None:
        return self.columns[index] if 0 <= index < len(self.columns) else None

    def _by_cid(self, cid: int) -> Column | None:
        for c in self.columns:
            if c.cid == cid:
                return c
        return None

    # -- 行 -------------------------------------------------------------------------------------
    def _compute_rows(self) -> tuple[Row, ...]:
        cols = self.columns
        if not cols:
            return ()
        used: set[str] = set()
        for c in cols:
            used |= set(c.used)
        if len(cols) == 1:
            return tuple(Row(k, (v,), "same", False, k in used) for k, v in cols[0].leaves.items())
        cmp = parambundle.params_compare([c.bundle() for c in cols], [c.name for c in cols])
        return tuple(Row(r.key, r.values, r.status, r.notation_differs, r.key in used) for r in cmp)

    def rows(self, *, diff_only: bool = False, query: str = "") -> list[Row]:
        """行の並び。``diff_only`` = 違う行と片方に無い行だけ、``query`` = キーの部分一致(大文字小文字を問わない)。"""
        if self._rows is None:
            self._rows = self._compute_rows()
        q = query.strip().casefold()
        return [r for r in self._rows
                if (not diff_only or r.status != "same") and (not q or q in r.key.casefold())]

    def row(self, key: str) -> Row | None:
        """キーの行(無ければ None)。"""
        for r in self.rows():
            if r.key == key:
                return r
        return None

    def tree(self, *, diff_only: bool = False, query: str = "") -> list[Node]:
        """行をキーの階層の木にする(節は ``camera``、葉は ``camera.fx``)。"""
        top: list[Node] = []
        index: dict[str, Node] = {}
        for r in self.rows(diff_only=diff_only, query=query):
            parts = r.key.split(".")
            siblings, path = top, ""
            chain: list[Node] = []
            for part in parts[:-1]:
                path = part if not path else path + "." + part
                node = index.get(path)
                if node is None:
                    node = index[path] = Node(path, part)
                    siblings.append(node)
                chain.append(node)
                siblings = node.children
            leaf = Node(r.key, parts[-1], r, differ=int(r.status == "differ"), partial=int(r.status == "partial"))
            siblings.append(leaf)
            for node in chain:
                node.differ += leaf.differ
                node.partial += leaf.partial
        return top

    def counts(self) -> dict[str, int]:
        """状態の 1 行の材料: 列・行・違う行・片方に無い行・未保存の列の数。"""
        rows = self.rows()
        return {"columns": len(self.columns), "rows": len(rows),
                "differ": sum(1 for r in rows if r.status == "differ"),
                "partial": sum(1 for r in rows if r.status == "partial"),
                "dirty": sum(1 for c in self.columns if c.dirty())}

    def value(self, index: int, key: str) -> Any:
        """セルの値(無ければ None)。"""
        c = self._col(index)
        return None if c is None else c.leaves.get(key)

    def is_dirty(self, index: int | None = None) -> bool:
        """未保存の変更があるか(``index`` を省くと全部の列)。"""
        if index is None:
            return any(c.dirty() for c in self.columns)
        c = self._col(index)
        return bool(c and c.dirty())

    # -- 直す・写す -------------------------------------------------------------------------------
    def _apply(self, cells: Iterable[tuple[int, str, Any, Any]], forward: bool) -> None:
        for cid, key, old, new in cells:
            col = self._by_cid(cid)
            if col is None:
                continue
            v = new if forward else old
            if v is _MISSING:
                col.leaves.pop(key, None)
            else:
                col.leaves[key] = v
            col._bundle = None
        self._rows = None

    def _commit(self, change: _Change) -> Outcome | None:
        """変更を当てる。束の門(キーの衝突など)に落ちたら戻して理由を返す。"""
        self._apply(change.cells, True)
        try:
            for cid in {c[0] for c in change.cells}:
                col = self._by_cid(cid)
                if col is not None:
                    col.bundle()
        except ParamError as e:
            self._apply(change.cells, False)
            return Outcome(False, "edit.gate", (str(e),))
        self._undo.append(change)
        self._redo.clear()
        return None

    def _editable(self, index: int) -> tuple[Column | None, Outcome | None]:
        col = self._col(index)
        if col is None:
            return None, Outcome(False, "edit.no_column")
        if not col.writable:
            return None, Outcome(False, "edit.readonly", (col.name,), column=index)
        return col, None

    def set_value(self, index: int, key: str, text: str) -> Outcome:
        """セルを文字から直す(型を保つ。保てなければ断って理由を返す)。"""
        col, bad = self._editable(index)
        if col is None:
            return bad  # type: ignore[return-value]
        if key not in col.leaves:
            return Outcome(False, "edit.no_key", (key,), column=index)
        old = col.leaves[key]
        try:
            new = _normalise(key, parse_edit(key, old, text))
        except EditRefused as e:
            return Outcome(False, e.code, e.args_, column=index)
        return self._set(index, col, key, old, new, "label.edit")

    def set_raw(self, index: int, key: str, value: Any) -> Outcome:
        """セルを値から直す(真偽のチェックなど)。型が変わる値は断る。"""
        col, bad = self._editable(index)
        if col is None:
            return bad  # type: ignore[return-value]
        if key not in col.leaves:
            return Outcome(False, "edit.no_key", (key,), column=index)
        old = col.leaves[key]
        try:
            ko, kn = kind_of(old), kind_of(value)
        except TypeError as e:
            return Outcome(False, "edit.gate", ("%s: %s" % (key, e),), column=index)
        if ko != kn and not {ko, kn} <= {"int", "float"}:
            return Outcome(False, "edit.gate", ("%s: the type would change from %s to %s" % (key, ko, kn),), column=index)
        try:
            new = _normalise(key, value)
        except EditRefused as e:
            return Outcome(False, e.code, e.args_, column=index)
        return self._set(index, col, key, old, new, "label.edit")

    def _set(self, index: int, col: Column, key: str, old: Any, new: Any, label: str) -> Outcome:
        if same_value(old, new):
            return Outcome(False, "edit.same", (key,), column=index)
        bad = self._commit(_Change(label, (key,), ((col.cid, key, old, new),)))
        if bad is not None:
            return bad
        notes: tuple = ()
        if kind_of(old) != kind_of(new):
            notes = (("note.type_changed", (key, kind_of(old), kind_of(new))),)
        return Outcome(True, notes=notes, column=index, count=1)

    def copy_value(self, key: str, src: int, dst: int) -> Outcome:
        """``src`` の列の値を ``dst`` の列へ写す(無いキーは足す)。型が変わったら注意に書く。"""
        s = self._col(src)
        d, bad = self._editable(dst)
        if s is None or d is None:
            return bad or Outcome(False, "edit.no_column")
        if key not in s.leaves:
            return Outcome(False, "copy.missing", (key, s.name), column=dst)
        new = s.leaves[key]
        old = d.leaves.get(key, _MISSING)
        if old is not _MISSING and same_value(old, new):
            return Outcome(False, "copy.same", (key,), column=dst)
        bad = self._commit(_Change("label.copy", (key,), ((d.cid, key, old, new),)))
        if bad is not None:
            return bad
        notes: list[tuple[str, tuple]] = []
        if old is _MISSING:
            notes.append(("note.key_added", (key, d.name)))
        elif kind_of(old) != kind_of(new):
            notes.append(("note.type_changed", (key, kind_of(old), kind_of(new))))
        return Outcome(True, notes=tuple(notes), column=dst, count=1)

    def copy_column(self, src: int, dst: int, keys: Sequence[str] | None = None) -> Outcome:
        """``src`` の列の値を ``dst`` へまとめて写す(``keys`` を省くと、値が違う行と ``dst`` に無い行の全部)。1 回の Undo で戻る。"""
        s = self._col(src)
        d, bad = self._editable(dst)
        if s is None or d is None:
            return bad or Outcome(False, "edit.no_column")
        cells = []
        for key in (keys if keys is not None else list(s.leaves)):
            if key not in s.leaves:
                continue
            new = s.leaves[key]
            old = d.leaves.get(key, _MISSING)
            if old is _MISSING or not same_value(old, new):
                cells.append((d.cid, key, old, new))
        if not cells:
            return Outcome(False, "copy.nothing", column=dst)
        bad = self._commit(_Change("label.copy_column", (len(cells), d.name), tuple(cells)))
        if bad is not None:
            return bad
        return Outcome(True, column=dst, count=len(cells))

    # -- Undo / Redo ----------------------------------------------------------------------------
    def can_undo(self) -> bool:
        """戻せる変更があるか。"""
        return bool(self._undo)

    def can_redo(self) -> bool:
        """やり直せる変更があるか。"""
        return bool(self._redo)

    def undo(self) -> Outcome:
        """直前の変更を戻す。``code`` / ``args`` は戻した変更の名前。"""
        if not self._undo:
            return Outcome(False, "undo.empty")
        ch = self._undo.pop()
        self._apply(ch.cells, False)
        self._redo.append(ch)
        return Outcome(True, ch.code, ch.args, count=len(ch.cells))

    def redo(self) -> Outcome:
        """戻した変更をやり直す。"""
        if not self._redo:
            return Outcome(False, "redo.empty")
        ch = self._redo.pop()
        self._apply(ch.cells, True)
        self._undo.append(ch)
        return Outcome(True, ch.code, ch.args, count=len(ch.cells))

    # -- 書く -------------------------------------------------------------------------------------
    def save_losses(self, index: int, target_fmt: str | None = None) -> list[tuple[str, tuple, bool]]:
        """書き戻すと失われる物 ``[(code, args, 確認が要るか)]``。空なら何も失われない(入れ物のまま)。"""
        col = self._col(index)
        if col is None:
            return []
        out: list[tuple[str, tuple, bool]] = []
        if col.includes:
            out.append(("loss.include", (", ".join(col.includes),), True))
        if col.refs:
            out.append(("loss.refs", (col.refs,), True))
        if col.comments:
            out.append(("loss.comments", (col.comments,), True))
        if col.anchors:
            out.append(("loss.anchors", (col.anchors,), True))
        if target_fmt and col.fmt and target_fmt != col.fmt:
            out.append(("loss.convert", (target_fmt.upper(), col.fmt.upper()), False))
        if col.path is not None:
            out.append(("loss.layout", (), False))
        return out

    def save(self, index: int, *, accept_losses: bool = False, force: bool = False) -> Outcome:
        """列を元のファイルへ元の形式で書く(原子的)。

        失われる物(コメント・include・参照・アンカー)があれば ``needs_confirm`` で止まり、``accept_losses=True``
        で進む。外でファイルが変わっていれば同じく止まり、``force=True`` で上書きする。
        """
        col = self._col(index)
        if col is None:
            return Outcome(False, "edit.no_column")
        if col.path is None:
            return Outcome(False, "save.no_path", (col.name,), column=index)
        return self._save_to(index, col, col.path, accept_losses, force, same_file=True)

    def save_as(self, index: int, path: str | os.PathLike, *, accept_losses: bool = False) -> Outcome:
        """列を別のファイル(形式は拡張子: .json / .yaml / .yml / .xml)へ書き、以後その列はそのファイルを指す。"""
        col = self._col(index)
        if col is None:
            return Outcome(False, "edit.no_column")
        return self._save_to(index, col, os.fspath(path), accept_losses, True, same_file=False)

    def _save_to(self, index: int, col: Column, path: str, accept: bool, force: bool, same_file: bool) -> Outcome:
        ext = os.path.splitext(path)[1].lower()
        fmt = FORMATS.get(ext)
        if fmt not in WRITABLE_FORMATS:
            return Outcome(False, "save.format", (os.path.basename(path), ext or "''"), column=index, path=path)
        losses = self.save_losses(index, fmt)
        notes = tuple((c, a) for c, a, _ in losses)
        if same_file and not force:
            state = self._external_state(col)
            if state:
                return Outcome(False, "save.external" if state == "changed" else "save.gone", (col.name,),
                               notes=notes, needs_confirm=True, column=index, path=path)
        if any(block for _, _, block in losses) and not accept:
            return Outcome(False, "save.confirm", (col.name,), notes=notes, needs_confirm=True, column=index, path=path)
        try:
            write_bundle_atomic(col.leaves, path)
        except _VerifyError as e:
            return Outcome(False, "save.verify", (os.path.basename(path), e.key), column=index, path=path)
        except (ParamError, OSError) as e:
            return Outcome(False, "save.failed", (os.path.basename(path), str(e)), column=index, path=path)
        col.path = os.path.abspath(path)
        col.fmt = fmt
        col.bundle_name = os.path.basename(path)
        col.saved = dict(col.leaves)
        col.includes, col.refs, col.comments, col.anchors = (), 0, 0, 0
        col.stamp = _stamp(col.path)
        if not same_file:
            old = col.name
            col.name = ""
            col.name = self._unique_name(col.path, os.path.basename(path))
            if col.name != old:
                col._bundle = None
                self._rows = None
        return Outcome(True, "save.done", (col.name,), notes=notes, column=index, path=col.path)

    # -- 外での変更 -------------------------------------------------------------------------------
    def _external_state(self, col: Column) -> str:
        """"" = 変わっていない / "changed" / "missing"。更新時刻だけ変わって中身が同じなら、変わっていない。"""
        if col.path is None or col.stamp is None:
            return ""
        try:
            st = os.stat(col.path)
        except OSError:
            return "missing"
        if st.st_mtime_ns == col.stamp.mtime_ns and st.st_size == col.stamp.size:
            return ""
        try:
            now = _stamp(col.path)
        except OSError:
            return "missing"
        if now.sha256 == col.stamp.sha256:
            col.stamp = now
            return ""
        return "changed"

    def check_external(self) -> list[tuple[int, str]]:
        """外で変わった列 ``[(列の番号, "changed" | "missing")]``。"""
        out = []
        for i, c in enumerate(self.columns):
            state = self._external_state(c)
            if state:
                out.append((i, state))
        return out

    def reload(self, index: int) -> Outcome:
        """列をファイルから読み直す(未保存の変更は捨てる。その列に掛かる履歴も消える)。読めなければ列はそのまま。"""
        col = self._col(index)
        if col is None:
            return Outcome(False, "edit.no_column")
        if col.path is None:
            return Outcome(False, "save.no_path", (col.name,), column=index)
        try:
            new = self._read_column(col.path, col.cid, col.name)
        except (ParamError, OSError) as e:
            return Outcome(False, "load.refused", (col.name, str(e)), column=index, path=col.path)
        new.used = col.used
        self.columns[index] = new
        self._undo = [c for c in self._undo if all(cell[0] != col.cid for cell in c.cells)]
        self._redo = [c for c in self._redo if all(cell[0] != col.cid for cell in c.cells)]
        self._rows = None
        return Outcome(True, "reload.done", (new.name,), column=index, path=new.path)

    def revert(self, index: int) -> Outcome:
        """列の未保存の変更を捨てて、保存済みの値に戻す(ファイルは読まない。その列に掛かる履歴も消える)。"""
        col = self._col(index)
        if col is None:
            return Outcome(False, "edit.no_column")
        if not col.dirty():
            return Outcome(False, "save.clean", (col.name,), column=index)
        col.leaves = dict(col.saved)
        col._bundle = None
        self._undo = [c for c in self._undo if all(cell[0] != col.cid for cell in c.cells)]
        self._redo = [c for c in self._redo if all(cell[0] != col.cid for cell in c.cells)]
        self._rows = None
        return Outcome(True, column=index)

    # -- 実行との連動 -----------------------------------------------------------------------------
    def set_used(self, reports: Any, index: int | None = None) -> Outcome:
        """直前の実行が読んだキーに印を付ける。

        ``reports`` は ``ParamReport``(``p.for_op(name, report=True)`` の記録)かその並び、またはキーの並び。
        記録は束の名前(ファイル名)が合う列に付く。``index`` を渡すとその列だけ。前の印は消える。
        """
        for c in self.columns:
            c.used = {}
        items = [reports] if hasattr(reports, "entries") or isinstance(reports, str) else list(reports or ())
        total = 0
        for item in items:
            if hasattr(item, "entries"):
                pairs = [(k, "%s.%s" % (item.op, e.arg)) for e in item.entries for k in e.keys]
                name = getattr(item, "bundle", "")
            else:
                pairs, name = [(str(item), "")], ""
            for i, c in enumerate(self.columns):
                if index is not None and i != index:
                    continue
                if index is None and name and name not in (c.bundle_name, c.name):
                    continue
                for key, who in pairs:
                    if key in c.leaves:
                        had = c.used.get(key, ())
                        if key not in c.used:
                            total += 1
                        c.used[key] = had + ((who,) if who and who not in had else ())
        self._rows = None
        return Outcome(True, "used.count" if total else "used.none", (total,) if total else (), count=total)

    def clear_used(self) -> None:
        """実行の印を消す。"""
        for c in self.columns:
            c.used = {}
        self._rows = None


def example_bundles() -> list[tuple[str, dict[str, Any]]]:
    """空の窓の「例を開く」が出す 2 つの束(同じ装置の昼と夜。違う行・書き方だけ違う行・片方に無い行が 1 つずつある)。"""
    day = {"camera": {"fx": 812.5, "fy": 812.5, "cx": 320, "cy": 240, "size": [640, 480]},
           "optics": {"wavelength": "550 nm", "f_number": 2.8, "pixel_pitch": "3.45 um"},
           "exposure": {"time": "8 ms", "auto": True, "mode": "global"}}
    night = {"camera": {"fx": 812.5, "fy": 812.5, "cx": 320, "cy": 240, "size": [640, 480]},
             "optics": {"wavelength": "0.55 um", "f_number": 1.4, "pixel_pitch": "3.45 um"},
             "exposure": {"time": "40 ms", "auto": False, "mode": "global", "gain_db": 12}}
    return [("rig_day", day), ("rig_night", night)]
