"""XML を読む入口を 1 つに寄せた「門」(``safe_xml_parse`` ほか)。

なぜ必要か: 外部のファイル(OME-TIFF の埋め込み XML・CommonRoad・OSM・3MF・CityGML・SVG)を標準の ``xml.etree`` に
そのまま渡すと、(i) DOCTYPE の内部実体(``<!ENTITY a "...">``)が展開されて受理される、(ii) 入力の大きさに上限が無い
(8 MB の入力が約 170 MB のメモリになる実測)、(iii) zip の中の XML は展開後の大きさに上限が無い、という穴があった。
標準の expat(2.4.1 以降)は入力の増幅率を制限し外部実体は読まないので、実体の爆発は今の環境では起きにくいが、
それは **古い expat や別の環境では保証されない**。ここでは解析器そのものの DOCTYPE 通知(``TreeBuilder.doctype``)で
DOCTYPE を断る。バイト列の正規表現ではなく expat が読んだ後の通知なので、UTF-8 / UTF-16 の BOM つき・BOM なし、宣言つきの別
エンコード(iso-8859-1 など)でも見落とさない(実測は tests/test_safe_xml_parse_2026_11_12.py)。

断る入力はすべて :class:`UnsafeXMLError`(``ValueError`` の子)。壊れた XML は標準どおり ``ET.ParseError`` のままで、
呼び出し側の既存の ``except ET.ParseError`` はそのまま効く。``defusedxml`` は依存に足さない(この門だけで同じ入力を断れる)。

公開: :func:`safe_xml_parse`(文字列・bytes・パス)/ :func:`safe_xml_parse_zip_member`(zip の中の 1 メンバー)/
:func:`safe_xml_iterparse`(ストリーム読み。大きさの上限は呼び出し側が持つ)。
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from collections import deque
from collections.abc import Iterator
from pathlib import Path
from typing import Any

__all__ = ["UnsafeXMLError", "DEFAULT_MAX_BYTES", "safe_xml_parse", "safe_xml_parse_zip_member", "safe_xml_iterparse"]

#: 既定の入力の上限(``optdraw._MAX_TEXT_BYTES`` の SVG と同じ 50 MiB)。
DEFAULT_MAX_BYTES = 50 * 1024 * 1024
_CHUNK = 64 * 1024


class UnsafeXMLError(ValueError):
    """DOCTYPE / 実体宣言・大きさの上限超えなど、安全の門が断った入力。``ValueError`` の子(既存の呼び出し側の契約を保つ)。"""


class _NoDTDBuilder(ET.TreeBuilder):
    """DOCTYPE を見た瞬間に断る TreeBuilder。expat の StartDoctypeDecl で呼ばれるので、内部実体の宣言より前に止まる。"""

    _op = "xml"
    _forbid = True

    def doctype(self, name, pubid, system):  # noqa: D401 (ElementTree が呼ぶ名前)
        if not self._forbid:
            return
        raise UnsafeXMLError(
            "%s: DOCTYPE / ENTITY declarations are refused (<!DOCTYPE %s> found; XML entity-expansion defense)"
            % (self._op, name))


class _EventBuilder(_NoDTDBuilder):
    """``end`` の要素を溜める版(iterparse の代わり。C の iterparse は TreeBuilder の厳密な型しか受けない)。"""

    def __init__(self) -> None:
        super().__init__()
        self.ended: deque = deque()

    def end(self, tag):
        elem = super().end(tag)
        self.ended.append(elem)
        return elem


def _make_parser(forbid_dtd: bool, op: str, builder: type | None = None):
    target = (builder or _NoDTDBuilder)()
    target._op = op
    target._forbid = bool(forbid_dtd)
    return ET.XMLParser(target=target)


def _check_limit(max_bytes: Any, op: str) -> int | None:
    if max_bytes is None:
        return None
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("%s: max_bytes must be a positive int or None, got %r" % (op, max_bytes))
    return max_bytes


def _too_big(op: str, size: int, limit: int, unit: str = "bytes") -> UnsafeXMLError:
    return UnsafeXMLError("%s: XML input of %d %s exceeds the limit %d" % (op, size, unit, limit))


def _read_path(path: Path, limit: int | None, op: str) -> bytes:
    if not path.is_file():
        raise ValueError("%s: file not found: %s" % (op, path))
    if limit is not None and path.stat().st_size > limit:
        raise _too_big(op, path.stat().st_size, limit)
    with open(path, "rb") as f:
        data = f.read() if limit is None else f.read(limit + 1)
    if limit is not None and len(data) > limit:
        raise _too_big(op, len(data), limit)
    return data


def safe_xml_parse(data_or_path: "str | bytes | bytearray | os.PathLike[str]", *,
                   max_bytes: int | None = DEFAULT_MAX_BYTES, forbid_dtd: bool = True,
                   kind: str = "auto", op: str = "xml") -> ET.Element:
    """XML(文字列・bytes・パス)を DOCTYPE なし・大きさ上限つきで読み、ルート要素を返す。

    ``kind="auto"``(既定): ``str`` は先頭の空白・BOM を除いて ``<`` で始まれば XML の本文、そうでなければパス。``Path`` は
    常にパス。呼び出し側で本文かパスか決めてある場合は ``kind="data"`` / ``"path"`` で固定する(本文が ``<`` で始まらない壊れた
    入力をパスと取り違えて「ファイルが無い」と言わないため)。大きさは bytes はバイト数、``str`` は文字数で ``max_bytes`` と比べる(``None`` で上限なし)。
    ``forbid_dtd=True``(既定)なら DOCTYPE / ENTITY を含む入力を :class:`UnsafeXMLError` で断る。
    **Raises** :class:`UnsafeXMLError`(DTD・上限超え)/ ``ValueError``(型・パスが違う・``max_bytes`` が不正)/ ``ET.ParseError``。
    """
    limit = _check_limit(max_bytes, op)
    if kind not in ("auto", "data", "path"):
        raise ValueError("%s: kind must be 'auto', 'data' or 'path', got %r" % (op, kind))
    if kind == "path" or (kind == "auto" and (isinstance(data_or_path, os.PathLike) or (
            isinstance(data_or_path, str) and not data_or_path.lstrip("\ufeff \t\r\n").startswith("<")))):
        payload: "str | bytes" = _read_path(Path(data_or_path), limit, op)
    elif isinstance(data_or_path, (str, bytes, bytearray)):
        payload = data_or_path if isinstance(data_or_path, str) else bytes(data_or_path)
        if limit is not None and len(payload) > limit:
            raise _too_big(op, len(payload), limit, "characters" if isinstance(payload, str) else "bytes")
    else:
        raise ValueError("%s: expected an XML string, bytes or a path, got %r" % (op, type(data_or_path).__name__))
    parser = _make_parser(forbid_dtd, op)
    parser.feed(payload)
    return parser.close()


def safe_xml_parse_zip_member(zf: Any, name: "str | Any", *, max_bytes: int | None = DEFAULT_MAX_BYTES,
                              forbid_dtd: bool = True, op: str = "xml") -> ET.Element:
    """zip の中の 1 メンバー(3MF の ``.model`` など)を読む。**展開後**の大きさにも ``max_bytes`` の上限(zip 爆弾の備え)。

    宣言された展開後の大きさ(``file_size``)が上限を超えるなら展開せずに断り、宣言が嘘でも ``max_bytes + 1`` バイトまでしか読まない。
    """
    limit = _check_limit(max_bytes, op)
    info = zf.getinfo(name) if isinstance(name, str) else name
    if limit is not None and info.file_size > limit:
        raise _too_big(op, info.file_size, limit)
    with zf.open(info) as f:
        data = f.read() if limit is None else f.read(limit + 1)
    if limit is not None and len(data) > limit:
        raise _too_big(op, len(data), limit)
    return safe_xml_parse(data, max_bytes=None, forbid_dtd=forbid_dtd, op=op)


def safe_xml_iterparse(stream: Any, *, forbid_dtd: bool = True, op: str = "xml") -> Iterator[tuple[str, ET.Element]]:
    """``ET.iterparse(stream, events=("end",))`` の DOCTYPE なし版。``("end", 要素)`` を順に返す(読みながら ``elem.clear()`` してよい)。

    巨大なストリーム(CityGML など)を読むので大きさの上限は持たない(呼び出し側がメモリを ``clear()`` で抑える)。
    DOCTYPE は最初の chunk で断る。壊れた XML は ``ET.ParseError``。
    """
    parser = _make_parser(forbid_dtd, op, _EventBuilder)
    builder = parser.target
    while True:
        chunk = stream.read(_CHUNK)
        if not chunk:
            break
        parser.feed(chunk)
        while builder.ended:
            yield "end", builder.ended.popleft()
    parser.close()
    while builder.ended:
        yield "end", builder.ended.popleft()
