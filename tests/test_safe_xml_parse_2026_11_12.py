# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""XML の読み口の安全の門(``safe_xml``)と、それを通す全部の読み手(2026-11-12)。

定義ファイルの読み書きの棚卸し(DEFS_IO_SURVEY §4-I)で、外部のファイルを読む XML の入口 9 か所のうち DOCTYPE を断るのが SVG
だけだと分かった。門の関数だけでなく **各読み手の入口から** 攻撃入力を渡して断られることを確かめる(門を作っても読み手が通して
いなければ穴は残る)。さらに配布するモジュールに、門を通さない XML 解析の呼び出しが残っていないことを走査する。
"""
from __future__ import annotations

import importlib.util
import io
import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import xml.etree.ElementTree as ET  # noqa: E402

import safe_xml as SX  # noqa: E402
from safe_xml import UnsafeXMLError  # noqa: E402

BIG = SX.DEFAULT_MAX_BYTES + 1024


# --------------------------------------------------------------------------- 攻撃入力(ルート要素ごとに包む)
def _laughs(levels: int = 8, fan: int = 10) -> str:
    ents = '<!ENTITY l0 "ha">' + "".join(
        '<!ENTITY l%d "%s">' % (i, ("&l%d;" % (i - 1)) * fan) for i in range(1, levels + 1))
    return "<!DOCTYPE r [%s]>" % ents


_DTDS = {
    "billion_laughs": _laughs(),
    "quadratic": '<!DOCTYPE r [<!ENTITY a "%s">]>' % ("x" * 5000),
    "external_entity": '<!DOCTYPE r [<!ENTITY x SYSTEM "file:///nonexistent/secret.txt">]>',
    "internal_entity": '<!DOCTYPE r [<!ENTITY x "hello">]>',
    "doctype_only": "<!DOCTYPE r>",
    "doctype_system": '<!DOCTYPE r SYSTEM "http://example.invalid/r.dtd">',
}


def _doc(dtd: str, root: str) -> str:
    return '<?xml version="1.0"?>%s%s' % (dtd, root)


#: 読み手ごとの(最小の正しい)ルート。
_ROOTS = {
    "cr_read": '<commonRoad commonRoadVersion="2020a" timeStepSize="0.1" benchmarkID="X" date="2020-01-01" author="a"/>',
    "osm_parse": '<osm version="0.6"><node id="1" lat="35.0" lon="139.0"/></osm>',
    "plateau_parse": "<CityModel/>",
    "plateau_lod2_mesh": "<CityModel/>",
    "svg_entities": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>',
    "ome_written_axes": '<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06"/>',
    "ome_xml_meta": '<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06"/>',
    "pegtactile_cutaway_xml": "<mujoco/>",
    "pegfail_scene_mjcf": "<mujoco/>",
    "read_3mf": '<model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"/>',
    "anatomical_hand": "<mujoco/>",
}


# --------------------------------------------------------------------------- 読み手の入口(payload は bytes か str)
def _hand_module():
    p = ROOT / "examples_3d" / "anatomical_hand.py"
    spec = importlib.util.spec_from_file_location("anatomical_hand_for_safe_xml", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _call_cr_read(payload, tmp_path, mp):
    import drivecommonroad as CR
    return CR.cr_read(payload)


def _call_osm_parse(payload, tmp_path, mp):
    import drivejapan as DJ
    return DJ.osm_parse(payload)


def _call_plateau_parse(payload, tmp_path, mp):
    import driveplateau as DP
    return DP.plateau_parse(payload)


def _call_plateau_lod2_mesh(payload, tmp_path, mp):
    import driveplateau as DP
    return DP.plateau_lod2_mesh(payload)


def _call_svg(payload, tmp_path, mp):
    import optdraw as OD
    return OD.svg_entities(payload)


def _as_str(payload):
    """str で受ける読み手(OME・pegtactile・pegfail)へは、エンコード済みの試料を BOM / 先頭バイトから復号して渡す。"""
    if isinstance(payload, str):
        return payload
    if payload[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return payload.decode("utf-16")
    if payload[:1] == b"\x00":
        return payload.decode("utf-16-be")
    if payload[1:2] == b"\x00":
        return payload.decode("utf-16-le")
    if payload[:3] == b"\xef\xbb\xbf":
        return payload.decode("utf-8")  # BOM は U+FEFF として残る
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload.decode("latin-1")


def _call_ome_written_axes(payload, tmp_path, mp):
    import fileio
    return fileio._ome_written_axes(_as_str(payload), "ome_tiff_read")


def _call_ome_xml_meta(payload, tmp_path, mp):
    import fileio
    return fileio._ome_xml_meta(_as_str(payload), (1, 1, 1, 2, 2), "TCZYX", "uint8", "ome_tiff_read")


def _call_pegtactile(payload, tmp_path, mp):
    import pegtactile as PT
    return PT.pegtactile_cutaway_xml(_as_str(payload))


def _call_pegfail(payload, tmp_path, mp):
    # pegfail は pegsim が作った自前の MJCF を読む。入口の手前(生成元)を差し替えて、門が通っていることを見る。
    import pegfail as PF
    mp.setattr(PF.P, "peg_scene_mjcf", lambda *a, **k: _as_str(payload))
    return PF.pegfail_scene_mjcf()


def _call_3mf(payload, tmp_path, mp):
    import printpath as P
    path = tmp_path / "x.3mf"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("3D/3dmodel.model", payload if isinstance(payload, bytes) else payload.encode("utf-8"))
    return P.read_3mf(str(path))


def _call_hand(payload, tmp_path, mp):
    path = tmp_path / "hand.xml"
    path.write_bytes(payload if isinstance(payload, bytes) else payload.encode("utf-8"))
    return _hand_module().load_mjcf_bone_meshes(path)


_READERS = {
    "cr_read": _call_cr_read, "osm_parse": _call_osm_parse, "plateau_parse": _call_plateau_parse,
    "plateau_lod2_mesh": _call_plateau_lod2_mesh, "svg_entities": _call_svg,
    "ome_written_axes": _call_ome_written_axes, "ome_xml_meta": _call_ome_xml_meta,
    "pegtactile_cutaway_xml": _call_pegtactile, "pegfail_scene_mjcf": _call_pegfail,
    "read_3mf": _call_3mf, "anatomical_hand": _call_hand,
}
assert set(_READERS) == set(_ROOTS)
#: 大きさの上限を持たない読み手(ストリーム読み。メモリは elem.clear() で抑える設計)。
_NO_SIZE_LIMIT = {"plateau_parse", "plateau_lod2_mesh"}


# --------------------------------------------------------------------------- 1. 読み手ごとに DTD 系を断る
@pytest.mark.parametrize("reader", sorted(_READERS))
@pytest.mark.parametrize("attack", sorted(_DTDS))
def test_every_reader_refuses_dtd_attacks(reader, attack, tmp_path, monkeypatch):
    payload = _doc(_DTDS[attack], _ROOTS[reader]).encode("utf-8")
    with pytest.raises(UnsafeXMLError, match="DOCTYPE"):
        _READERS[reader](payload, tmp_path, monkeypatch)


# --------------------------------------------------------------------------- 2. エンコードを替えても断る(UTF-8 / UTF-16 BOM つき・なし / 宣言つき別エンコード)
def _encoded(kind: str, reader: str) -> bytes:
    body = _ROOTS[reader]
    dtd = _DTDS["internal_entity"]
    if kind == "utf8_bom":
        return b"\xef\xbb\xbf" + _doc(dtd, body).encode("utf-8")
    if kind == "utf16_bom":
        return _doc(dtd, body).encode("utf-16")  # BOM つき(エンディアンは実行環境)
    if kind == "utf16le_declared":
        return ('<?xml version="1.0" encoding="utf-16"?>' + dtd + body).encode("utf-16-le")
    if kind == "utf16be_nobom":
        return (dtd + body).encode("utf-16-be")
    if kind == "latin1_declared":
        return ('<?xml version="1.0" encoding="iso-8859-1"?>' + dtd + body).encode("latin-1")
    raise AssertionError(kind)


_ENCODINGS = ["utf8_bom", "utf16_bom", "utf16le_declared", "utf16be_nobom", "latin1_declared"]


@pytest.mark.parametrize("reader", sorted(_READERS))
@pytest.mark.parametrize("kind", _ENCODINGS)
def test_every_reader_refuses_dtd_in_other_encodings(reader, kind, tmp_path, monkeypatch):
    payload = _encoded(kind, reader)
    # 入口の手前で UTF-8 を要求する読み手(cr_read・svg・ome の str 受け)は UnicodeDecodeError(ValueError)で断る。
    # どの経路でも「受理されて実体が展開される」ことだけは無い。
    with pytest.raises(ValueError):
        _READERS[reader](payload, tmp_path, monkeypatch)


@pytest.mark.parametrize("kind", ["utf8_bom", "utf16_bom", "utf16le_declared", "utf16be_nobom", "latin1_declared"])
def test_gate_refuses_dtd_in_other_encodings_by_the_gate_itself(kind):
    with pytest.raises(UnsafeXMLError, match="DOCTYPE"):
        SX.safe_xml_parse(_encoded(kind, "svg_entities"), kind="data")


# --------------------------------------------------------------------------- 3. 巨大な入力(読み手ごと)
# read_3mf は zip の展開後の大きさとして下の test_3mf_zip_bomb_is_refused_before_inflating で試す。
@pytest.mark.parametrize("reader", sorted(set(_READERS) - _NO_SIZE_LIMIT - {"read_3mf"}))
def test_every_reader_refuses_oversize_input(reader, tmp_path, monkeypatch):
    if reader == "anatomical_hand":
        path = tmp_path / "big.xml"
        path.write_bytes(b"<mujoco>" + b"x" * BIG + b"</mujoco>")
        with pytest.raises(UnsafeXMLError, match="exceeds"):
            _hand_module().load_mjcf_bone_meshes(path)
        return
    # ルートの中身を水増しして、構文は正しいまま上限を超える。
    root = _ROOTS[reader]
    tag = re.match(r"<(\w+)", root).group(1)
    pad = "x" * BIG
    if root.endswith("/>"):
        big = root[:-2] + ">" + "<!--" + pad + "-->" + "</%s>" % tag
    else:
        big = root + "<!--" + pad + "-->"
    # svg_entities は入口(_check_text)の上限が先に断る(ValueError)。ほかは門の UnsafeXMLError。
    exc = ValueError if reader == "svg_entities" else UnsafeXMLError
    with pytest.raises(exc, match="exceeds"):
        _READERS[reader](big.encode("utf-8"), tmp_path, monkeypatch)


def test_plateau_stream_has_no_size_limit_by_design():
    """plateau(CityGML)はストリーム読みで上限を持たない設計。DTD は断る(上で試験済み)・大きな正常入力は通る。"""
    import driveplateau as DP
    pad = b"<!--" + b"x" * (SX.DEFAULT_MAX_BYTES // 8) + b"-->"
    with pytest.raises(ValueError, match="source|CityGML|Building|建物"):
        DP.plateau_parse(b"<CityModel>" + pad + b"</CityModel>")  # 建物なし = 空の旨で断る(上限では断らない)


# --------------------------------------------------------------------------- 4. zip の中(3MF)
def test_3mf_zip_bomb_is_refused_before_inflating(tmp_path):
    import printpath as P
    path = tmp_path / "bomb.3mf"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("3D/3dmodel.model", b"<model>" + b"\0" * (SX.DEFAULT_MAX_BYTES + 4096) + b"</model>")
    assert path.stat().st_size < 1_000_000  # 圧縮後は小さい(爆弾)
    with pytest.raises(UnsafeXMLError, match="exceeds"):
        P.read_3mf(str(path))


class _FakeInfo:
    def __init__(self, file_size):
        self.file_size = file_size


class _FakeZip:
    """zipfile.ZipFile の代わり。open が呼ばれたか・何バイト要求されたかを記録する。"""

    def __init__(self, declared, payload):
        self.info = _FakeInfo(declared)
        self.payload = payload
        self.opened = 0
        self.requested = []

    def getinfo(self, name):
        return self.info

    def open(self, info):
        self.opened += 1
        outer = self

        class _S(io.BytesIO):
            def read(self, n=-1):
                outer.requested.append(n)
                return super().read(n)

        return _S(self.payload)


def test_zip_member_declared_size_over_the_limit_is_refused_without_opening():
    """守り 1: 宣言された展開後の大きさが上限を超えるなら、展開(open)せずに断る。"""
    zf = _FakeZip(declared=10_000, payload=b"<a/>")
    with pytest.raises(UnsafeXMLError, match="exceeds"):
        SX.safe_xml_parse_zip_member(zf, "m.xml", max_bytes=100)
    assert zf.opened == 0


def test_zip_member_with_a_lying_small_header_is_cut_at_limit_plus_one():
    """守り 2: 宣言が嘘で小さくても、読むのは max_bytes + 1 バイトまで(それを超えたら断る)。宣言の検査とは独立に効く。"""
    zf = _FakeZip(declared=10, payload=b"<a>" + b"y" * 5000 + b"</a>")
    with pytest.raises(UnsafeXMLError, match="exceeds"):
        SX.safe_xml_parse_zip_member(zf, "m.xml", max_bytes=100)
    assert zf.opened == 1 and zf.requested == [101]


def test_zip_member_within_limits_parses():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("m.xml", b"<a><b/></a>")
    zf = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
    assert SX.safe_xml_parse_zip_member(zf, "m.xml", max_bytes=100).tag == "a"
    with pytest.raises(UnsafeXMLError, match="DOCTYPE"):
        buf2 = io.BytesIO()
        with zipfile.ZipFile(buf2, "w") as z2:
            z2.writestr("m.xml", b"<!DOCTYPE a><a/>")
        SX.safe_xml_parse_zip_member(zipfile.ZipFile(io.BytesIO(buf2.getvalue())), "m.xml")


# --------------------------------------------------------------------------- 5. 正常な入力の読み結果が変わらない
def test_normal_inputs_parse_the_same_as_plain_elementtree():
    docs = [b"<a x='1'><b>t</b><!-- c --><c/></a>", '<a>日本語</a>', b'\xef\xbb\xbf<a/>',
            '<?xml version="1.0" encoding="utf-16"?><a/>'.encode("utf-16"),
            '<?xml version="1.0" encoding="iso-8859-1"?><a>\xe9</a>'.encode("latin-1"),
            '<r xmlns="urn:x"><k a="1 2"/></r>']
    for d in docs:
        a = SX.safe_xml_parse(d, kind="data")
        b = ET.fromstring(d)
        assert ET.tostring(a) == ET.tostring(b)


def test_cdata_and_comment_with_doctype_text_still_parse():
    """DOCTYPE という文字列がコメント・CDATA の中にあるだけの正常な文書は、バイト列の正規表現と違って断らない。"""
    assert SX.safe_xml_parse(b"<a><![CDATA[<!DOCTYPE x>]]></a>", kind="data").tag == "a"
    assert SX.safe_xml_parse(b"<!-- <!DOCTYPE x> --><a/>", kind="data").tag == "a"


def test_path_input_and_kinds(tmp_path):
    p = tmp_path / "a.xml"
    p.write_bytes(b"<a/>")
    assert SX.safe_xml_parse(p).tag == "a"                       # PathLike は常にパス
    assert SX.safe_xml_parse(str(p), kind="path").tag == "a"     # str をパスとして開くのは kind="path" を明示したときだけ
    assert SX.safe_xml_parse("  <a/>").tag == "a"
    assert SX.safe_xml_parse("\ufeff<a/>").tag == "a"
    with pytest.raises(ValueError, match="file not found"):
        SX.safe_xml_parse(tmp_path / "none.xml")
    p.write_bytes(b"<!DOCTYPE a><a/>")
    with pytest.raises(UnsafeXMLError, match="DOCTYPE"):
        SX.safe_xml_parse(p)
    with pytest.raises(UnsafeXMLError, match="exceeds"):
        SX.safe_xml_parse(p, max_bytes=5)


_PATH_LIKE_TEXTS = ["\\\\evil-host\\share\\a.xml", "//evil-host/share/a.xml", "\\\\?\\C:\\a.xml", "\\\\.\\pipe\\x", "http://evil-host/a.xml",
                    "file:///C:/a.xml", "C:\\a.xml", "NUL", "CON", "a.xml", "../a.xml"]


@pytest.mark.parametrize("text", _PATH_LIKE_TEXTS)
def test_a_str_is_never_opened_as_a_path_by_default(text, monkeypatch):
    """既定(auto)で str / bytes は本文。UNC(``\\\\host\\share``)などをパスとして開く(= SMB で認証情報が外へ出る)ことは無く、
    ファイルの有無も例外の違いで分からない(どれも同じ ParseError)。open / stat が 1 回も呼ばれないことを見る。"""
    import builtins
    import pathlib

    def boom(*a, **k):
        raise AssertionError("a str was opened as a path")

    monkeypatch.setattr(builtins, "open", boom)
    monkeypatch.setattr(pathlib.Path, "is_file", boom)
    monkeypatch.setattr(pathlib.Path, "stat", boom)
    monkeypatch.setattr(pathlib.Path, "open", boom)
    with pytest.raises(ET.ParseError):
        SX.safe_xml_parse(text)
    with pytest.raises(ET.ParseError):
        SX.safe_xml_parse(text.encode("utf-8"))


def test_malformed_xml_stays_a_parse_error_and_bad_arguments_are_refused():
    with pytest.raises(ET.ParseError):
        SX.safe_xml_parse(b"<a>", kind="data")
    with pytest.raises(ValueError, match="max_bytes"):
        SX.safe_xml_parse(b"<a/>", max_bytes=0, kind="data")
    with pytest.raises(ValueError, match="kind"):
        SX.safe_xml_parse(b"<a/>", kind="nope")
    with pytest.raises(ValueError, match="expected"):
        SX.safe_xml_parse(123, kind="data")  # type: ignore[arg-type]
    assert SX.safe_xml_parse(b"<!DOCTYPE a><a/>", forbid_dtd=False, kind="data").tag == "a"


def test_iterparse_matches_elementtree_and_refuses_dtd():
    doc = b"<r>" + b"".join(b"<b i='%d'><c/></b>" % i for i in range(5000)) + b"</r>"
    mine = [(e.tag, e.get("i")) for _, e in SX.safe_xml_iterparse(io.BytesIO(doc))]
    ref = [(e.tag, e.get("i")) for _, e in ET.iterparse(io.BytesIO(doc), events=("end",))]
    assert mine == ref and len(mine) == 10001
    with pytest.raises(UnsafeXMLError, match="DOCTYPE"):
        list(SX.safe_xml_iterparse(io.BytesIO(b'<!DOCTYPE r [<!ENTITY a "b">]><r/>')))
    with pytest.raises(ET.ParseError):
        list(SX.safe_xml_iterparse(io.BytesIO(b"<r><b></r>")))


# --------------------------------------------------------------------------- 6. 配布するモジュールに、門を通さない解析が残っていないこと(ast)
# 対象 = pyproject の py-modules と packages(= wheel に入る全部。examples/・examples_3d/ を含む)。tests/・tools/ は wheel に入らない
# 開発用なので対象外。除外は門のモジュール自身(safe_xml.py)だけ。正規表現でなく ast で import の別名を追う。
_ET_MODULES = ("xml.etree.ElementTree", "xml.etree.cElementTree")
_PARSE_ATTRS = ("fromstring", "fromstringlist", "parse", "iterparse", "XML", "XMLID", "XMLParser", "XMLPullParser")
_BANNED_PARSE = {m + "." + a for m in _ET_MODULES for a in _PARSE_ATTRS}
_BANNED_FAMILIES = ("xml.dom", "xml.sax", "xml.parsers", "pyexpat", "lxml", "plistlib", "xmlrpc", "xmltodict", "defusedxml")


def _in_family(name: str) -> bool:
    return any(name == f or name.startswith(f + ".") for f in _BANNED_FAMILIES)


def _scan_source(src: str) -> list:
    """門を通らない XML 解析の形を全部返す: 別名つき import・``X.fromstring``・``fromstring as fs``・dom/sax/expat/lxml/plistlib 系の import。"""
    import ast
    tree = ast.parse(src)
    alias: dict = {}
    hits: list = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                alias[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
                if _in_family(a.name):
                    hits.append((node.lineno, "import " + a.name))
        elif isinstance(node, ast.ImportFrom) and not node.level:
            mod = node.module or ""
            for a in node.names:
                full = mod + "." + a.name
                alias[a.asname or a.name] = full
                if _in_family(mod) or _in_family(full) or full in _BANNED_PARSE:
                    hits.append((node.lineno, "from %s import %s" % (mod, a.name)))

    def resolve(n):
        if isinstance(n, ast.Name):
            return alias.get(n.id, n.id)
        if isinstance(n, ast.Attribute):
            base = resolve(n.value)
            return base + "." + n.attr if base else None
        return None

    for node in ast.walk(tree):
        if isinstance(node, (ast.Name, ast.Attribute)) and isinstance(getattr(node, "ctx", None), ast.Load):
            r = resolve(node)
            if r in _BANNED_PARSE:
                hits.append((node.lineno, r))
        if isinstance(node, ast.Call):
            r = resolve(node.func)
            if r in {m + ".ElementTree" for m in _ET_MODULES} and (len(node.args) >= 2 or any(k.arg == "file" for k in node.keywords)):
                hits.append((node.lineno, "ElementTree(file=...)"))
            if isinstance(node.func, ast.Attribute) and node.func.attr == "parse" and isinstance(node.func.value, ast.Call) \
                    and (resolve(node.func.value.func) or "") in {m + ".ElementTree" for m in _ET_MODULES}:
                hits.append((node.lineno, "ElementTree().parse"))
            if r in ("__import__", "importlib.import_module") and node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str) and (_in_family(node.args[0].value) or node.args[0].value in _ET_MODULES):
                hits.append((node.lineno, "dynamic import " + node.args[0].value))
    return sorted(set(hits))


def _shipped_py():
    import tomllib
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["setuptools"]
    files = [ROOT / (m + ".py") for m in cfg["py-modules"]]
    for pkg in cfg["packages"]:
        files += sorted((ROOT / pkg.replace(".", "/")).glob("*.py"))
    return [f for f in dict.fromkeys(files) if f.is_file()]


def test_no_ungated_xml_parse_remains_in_shipped_modules():
    files = _shipped_py()
    assert len(files) >= 900, "走査の対象が縮んでいる(%d 本)" % len(files)  # 空を通す門にしない(examples/ を含めて 1,000 本超)
    assert any(f.parent.name == "examples" for f in files) and any(f.parent.name == "examples_3d" for f in files)
    offenders, gate_users = [], 0
    for f in files:
        src = f.read_text(encoding="utf-8")
        if f.name == "safe_xml.py" and f.parent == ROOT:
            continue
        for lineno, what in _scan_source(src):
            offenders.append("%s:%d %s" % (f.relative_to(ROOT), lineno, what))
        if "safe_xml" in src:
            gate_users += 1
    assert not offenders, "門(safe_xml)を通さない XML 解析が残っている:\n" + "\n".join(offenders)
    assert gate_users >= 16, gate_users  # 本体 9 本 + examples 7 本


_SCAN_BAD = [
    "import xml.etree.ElementTree as ET\nET.fromstring(x)",
    "import xml.etree.ElementTree as X\nX.fromstring(x)",
    "from xml.etree.ElementTree import fromstring as fs\nfs(x)",
    "from xml.etree import ElementTree as E\nE.fromstringlist(x)",
    "import xml.etree.ElementTree as ET\nET.XMLID(x)",
    "import xml.etree.ElementTree as ET\nET.XMLParser()",
    "import xml.etree.ElementTree\nxml.etree.ElementTree.parse(p)",
    "from xml import etree\netree.ElementTree.iterparse(f)",
    "import xml.etree.ElementTree as ET\nET.ElementTree(file=p)",
    "import xml.etree.ElementTree as ET\nET.ElementTree().parse(p)",
    "import xml.etree.cElementTree as C\nC.fromstring(x)",
    "import pyexpat",
    "from xml.parsers import expat",
    "import xml.dom.minidom",
    "from xml.dom import pulldom",
    "import xml.sax",
    "import plistlib",
    "import lxml.etree",
    "import xmlrpc.client",
    "importlib.import_module('xml.dom.minidom')",
]
_SCAN_OK = [
    "import xml.etree.ElementTree as ET\nET.Element('a'); ET.SubElement(r, 'b'); ET.tostring(r); ET.ParseError",
    "import xml.etree.ElementTree as ET\nET.ElementTree(root).write(p)",
    "from safe_xml import safe_xml_parse\nsafe_xml_parse(x)",
    "def fromstring(x): pass\nfromstring(1)",
]


@pytest.mark.parametrize("src", _SCAN_BAD)
def test_scanner_detects_each_bypass_form(src):
    assert _scan_source(src), src


@pytest.mark.parametrize("src", _SCAN_OK)
def test_scanner_does_not_flag_legitimate_uses(src):
    assert not _scan_source(src), src


# --------------------------------------------------------------------------- 7. 要素数と入れ子の深さの上限
def _inject(root: str, inner: str) -> str:
    if root.endswith("/>"):
        tag = re.match(r"<(\w+)", root).group(1)
        return root[:-2] + ">" + inner + "</%s>" % tag
    i = root.rindex("</")
    return root[:i] + inner + root[i:]


def _deep(n: int) -> str:
    return "<z>" * n + "</z>" * n


@pytest.mark.parametrize("reader", sorted(_READERS))
def test_every_reader_refuses_deep_nesting(reader, tmp_path, monkeypatch):
    payload = _inject(_ROOTS[reader], _deep(300)).encode("utf-8")
    with pytest.raises(UnsafeXMLError, match="nesting"):
        _READERS[reader](payload, tmp_path, monkeypatch)


@pytest.mark.parametrize("reader", sorted(set(_READERS) - _NO_SIZE_LIMIT))
def test_every_reader_refuses_a_flat_element_flood(reader, tmp_path, monkeypatch):
    """要素の数の上限(既定 100 万、osm_parse は 200 万): 200 万 + 1 個の平らな ``<z/>``(8 MB)は入力の大きさの上限(50 MiB)では止まらない。"""
    payload = _inject(_ROOTS[reader], "<z/>" * 2_000_001).encode("utf-8")
    assert len(payload) < SX.DEFAULT_MAX_BYTES
    with pytest.raises(UnsafeXMLError, match="elements"):
        _READERS[reader](payload, tmp_path, monkeypatch)


def test_pegtactile_cutaway_does_not_leak_a_recursion_error_on_200k_levels():
    import pegtactile as PT
    with pytest.raises(UnsafeXMLError, match="nesting"):
        PT.pegtactile_cutaway_xml("<mujoco>" + _deep(200_000) + "</mujoco>")


def test_limits_are_inclusive_and_configurable_and_disableable():
    d256 = "<r>" + _deep(255) + "</r>"          # r + 255 = 256 段
    assert SX.safe_xml_parse(d256).tag == "r"
    import copy
    copy.deepcopy(SX.safe_xml_parse(d256))     # 上限の深さでも後段の deepcopy は再帰上限に当たらない
    with pytest.raises(UnsafeXMLError, match="nesting"):
        SX.safe_xml_parse("<r>" + _deep(256) + "</r>")
    with pytest.raises(UnsafeXMLError, match="nesting"):
        SX.safe_xml_parse("<r><a><b/></a></r>", max_depth=2)
    assert SX.safe_xml_parse("<r><a><b/></a></r>", max_depth=3).tag == "r"
    with pytest.raises(UnsafeXMLError, match="elements"):
        SX.safe_xml_parse("<r><a/><a/><a/></r>", max_elements=3)
    assert SX.safe_xml_parse("<r><a/><a/></r>", max_elements=3).tag == "r"
    assert SX.safe_xml_parse("<r>" + _deep(2000) + "</r>", max_depth=None).tag == "r"
    with pytest.raises(ValueError, match="max_depth"):
        SX.safe_xml_parse("<r/>", max_depth=0)
    with pytest.raises(ValueError, match="max_elements"):
        SX.safe_xml_parse("<r/>", max_elements=-1)


def test_element_cap_bounds_memory_for_a_flat_flood():
    """8.4 MB の平らな ``<a/>`` は上限なしだと約 185 MB(22 倍)になる。要素数の上限でその前に止まる。"""
    import tracemalloc
    data = b"<r>" + b"<a/>" * 2_100_000 + b"</r>"
    tracemalloc.start()
    try:
        with pytest.raises(UnsafeXMLError, match="elements"):
            SX.safe_xml_parse(data)
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert peak < 130 * 1024 * 1024, peak


def test_zip_member_applies_element_and_depth_limits():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("m.xml", "<r>" + _deep(300) + "</r>")
    zf = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
    with pytest.raises(UnsafeXMLError, match="nesting"):
        SX.safe_xml_parse_zip_member(zf, "m.xml")
    assert SX.safe_xml_parse_zip_member(zf, "m.xml", max_depth=None).tag == "r"


# --------------------------------------------------------------------------- 8. iterparse の門
def test_iterparse_depth_and_element_limits():
    with pytest.raises(UnsafeXMLError, match="nesting"):
        list(SX.safe_xml_iterparse(io.BytesIO(("<r>" + _deep(300) + "</r>").encode())))
    assert len(list(SX.safe_xml_iterparse(io.BytesIO(("<r>" + _deep(300) + "</r>").encode()), max_depth=None))) == 301
    with pytest.raises(UnsafeXMLError, match="elements"):
        list(SX.safe_xml_iterparse(io.BytesIO(b"<r><a/><a/><a/></r>"), max_elements=3))
    # 既定は総数の上限なし(巨大な街区ファイルを elem.clear() しながら読む設計。実ファイルは 226 万要素)
    n = sum(1 for _ in SX.safe_xml_iterparse(io.BytesIO(b"<r>" + b"<a/>" * 1_200_000 + b"</r>")))
    assert n == 1_200_001


def test_iterparse_refuses_a_dtd_hidden_behind_a_long_prolog():
    """DOCTYPE の前に 64 KiB を超えるコメントがあっても(先頭の chunk だけを見る実装を許さない)断る。"""
    doc = b"<!--" + b"x" * 200_000 + b'--><!DOCTYPE r [<!ENTITY a "b">]><r/>'
    with pytest.raises(UnsafeXMLError, match="DOCTYPE"):
        list(SX.safe_xml_iterparse(io.BytesIO(doc)))
    # コメントの中の DOCTYPE という文字列は断らない
    assert [e.tag for _, e in SX.safe_xml_iterparse(io.BytesIO(b"<!--" + b"x" * 200_000 + b"<!DOCTYPE a>--><r/>"))] == ["r"]


@pytest.mark.parametrize("kind", _ENCODINGS)
def test_iterparse_refuses_dtd_in_other_encodings(kind):
    with pytest.raises(UnsafeXMLError, match="DOCTYPE"):
        list(SX.safe_xml_iterparse(io.BytesIO(_encoded(kind, "svg_entities"))))


def test_iterparse_keeps_the_stream_intact_after_the_prolog_peek():
    """前置きの先読みが入力を欠かさない: 小さな chunk で返すストリームでも標準の iterparse と同じ要素列。"""
    doc = b"<?xml version='1.0'?><!-- c --><r>" + b"".join(b"<b i='%d'>t%d</b>" % (i, i) for i in range(3000)) + b"</r>"

    class Dribble(io.BytesIO):
        def read(self, n=-1):
            return super().read(7 if n is None or n < 0 or n > 7 else n)

    mine = [(e.tag, e.get("i"), e.text) for _, e in SX.safe_xml_iterparse(Dribble(doc))]
    ref = [(e.tag, e.get("i"), e.text) for _, e in ET.iterparse(io.BytesIO(doc), events=("end",))]
    assert mine == ref


def test_iterparse_needs_a_binary_stream():
    with pytest.raises(ValueError, match="binary"):
        list(SX.safe_xml_iterparse(io.StringIO("<r/>")))


def test_hand_include_expansion_still_works_through_the_gate(tmp_path):
    """正常な MJCF の ``<include>`` 展開は門を通しても変わらない(myo_sim が無い環境でも走る小さな実物)。"""
    (tmp_path / "sub.xml").write_text("<mujoco><asset><mesh name='m' file='m.stl'/></asset></mujoco>", encoding="utf-8")
    (tmp_path / "main.xml").write_text("<mujoco><include file='sub.xml'/><worldbody/></mujoco>", encoding="utf-8")
    root = _hand_module()._expand_includes(tmp_path / "main.xml")
    assert [c.tag for c in root] == ["asset", "worldbody"]
    assert root.find("asset/mesh").get("name") == "m"
