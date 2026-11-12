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


def test_zip_member_with_a_lying_header_is_still_bounded():
    """宣言(file_size)が小さくても、読むのは max_bytes + 1 まで。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("m.xml", b"<a>" + b"y" * 5000 + b"</a>")
    zf = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
    info = zf.getinfo("m.xml")
    info.file_size = 10  # 嘘の宣言
    # zipfile 自身が宣言の長さで読みを打ち切り(CRC 不一致 = BadZipFile)、門の上限でも断る。どちらでも無制限には読まない。
    with pytest.raises((UnsafeXMLError, zipfile.BadZipFile)):
        SX.safe_xml_parse_zip_member(zf, info, max_bytes=100)


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


def test_path_input_and_auto_kind(tmp_path):
    p = tmp_path / "a.xml"
    p.write_bytes(b"<a/>")
    assert SX.safe_xml_parse(p).tag == "a"
    assert SX.safe_xml_parse(str(p)).tag == "a"
    assert SX.safe_xml_parse("  <a/>").tag == "a"
    assert SX.safe_xml_parse("﻿<a/>").tag == "a"
    with pytest.raises(ValueError, match="file not found"):
        SX.safe_xml_parse(tmp_path / "none.xml")
    with pytest.raises(UnsafeXMLError, match="DOCTYPE"):
        p.write_bytes(b"<!DOCTYPE a><a/>")
        SX.safe_xml_parse(p)
    with pytest.raises(UnsafeXMLError, match="exceeds"):
        SX.safe_xml_parse(p, max_bytes=5)


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


# --------------------------------------------------------------------------- 6. 配布するモジュールに、門を通さない解析の呼び出しが残っていないこと
#: tests/ と tools/(CI の JUnit など内部の生成物を読む開発用の道具)・build/・examples/(PoC の台本。自前で生成した MJCF を
#: 読むだけ)は対象外。それ以外の .py(ルートのモジュール・fullseye/・examples_3d/・studio_*)は全部走査する。
_EXCLUDED_DIRS = {"tests", "tools", "build", "examples", "spikes", "bench", "impl2", ".git", "docs", "install", "rust"}
_UNGATED = re.compile(
    r"\b(?:_?ET|ElementTree|etree)\.(?:fromstring|parse|iterparse|XML|XMLParser|XMLPullParser)\s*\("
    r"|\bminidom\b|\bxml\.sax\b|\bpulldom\b|\blxml\b|\bxml\.parsers\.expat\b|\bxml\.dom\b|\bparseString\s*\(")


def _shipped_py():
    out = []
    for p in ROOT.rglob("*.py"):
        rel = p.relative_to(ROOT)
        if rel.parts[0] in _EXCLUDED_DIRS or any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
            continue
        out.append(p)
    return out


def _strip_comments_and_docstrings(src: str) -> str:
    """コメントと docstring(説明文に ET.fromstring と書いてあるだけの行)を落として、実コードだけを見る。"""
    import ast
    tree = ast.parse(src)
    lines = src.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                    and isinstance(body[0].value.value, str):
                for i in range(body[0].lineno - 1, body[0].end_lineno):
                    lines[i] = ""
    return "\n".join(re.sub(r"#.*$", "", ln) for ln in lines)


def test_no_ungated_xml_parse_call_remains_in_shipped_modules():
    files = _shipped_py()
    assert len(files) >= 500, "走査の対象が縮んでいる(%d 本)" % len(files)  # 空を通す門にしない
    gate_users = []
    offenders = []
    for p in files:
        src = p.read_text(encoding="utf-8", errors="replace")
        if "ElementTree" not in src and "minidom" not in src and "lxml" not in src and "xml." not in src:
            continue
        code = _strip_comments_and_docstrings(src)
        if p.name != "safe_xml.py":
            for m in _UNGATED.finditer(code):
                offenders.append("%s: %s" % (p.relative_to(ROOT), m.group(0)))
        if "safe_xml" in code and p.name != "safe_xml.py":
            gate_users.append(p.name)
    assert not offenders, "門(safe_xml)を通さない XML 解析が残っている:\n" + "\n".join(offenders)
    # 下限: 門を通している読み手が 9 本のファイルにある(drivecommonroad・drivejapan・driveplateau・fileio・optdraw・pegfail・pegtactile・printpath・anatomical_hand)。
    assert len(gate_users) >= 9, gate_users


def test_scan_actually_detects_an_ungated_call():
    """走査が空を通していないことの確認: 門を通さない呼び出しを含む行は検出される。"""
    for bad in ("root = ET.fromstring(x)", "ET.parse(p)", "_ET.fromstring(x)", "for e in ET.iterparse(s):",
                "from xml.dom import minidom", "ElementTree.XMLParser()"):
        assert _UNGATED.search(bad), bad
    assert not _UNGATED.search("root = safe_xml_parse(x)")


def test_hand_include_expansion_still_works_through_the_gate(tmp_path):
    """正常な MJCF の ``<include>`` 展開は門を通しても変わらない(myo_sim が無い環境でも走る小さな実物)。"""
    (tmp_path / "sub.xml").write_text("<mujoco><asset><mesh name='m' file='m.stl'/></asset></mujoco>", encoding="utf-8")
    (tmp_path / "main.xml").write_text("<mujoco><include file='sub.xml'/><worldbody/></mujoco>", encoding="utf-8")
    root = _hand_module()._expand_includes(tmp_path / "main.xml")
    assert [c.tag for c in root] == ["asset", "worldbody"]
    assert root.find("asset/mesh").get("name") == "m"
