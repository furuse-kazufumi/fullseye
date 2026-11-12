"""XML を読む入口を 1 つに寄せた「門」(``safe_xml_parse`` ほか)。

なぜ必要か: 外部のファイル(OME-TIFF の埋め込み XML・CommonRoad・OSM・3MF・CityGML・SVG)を標準の ``xml.etree`` に
そのまま渡すと、(i) DOCTYPE の内部実体(``<!ENTITY a "...">``)が展開されて受理される、(ii) 入力の大きさ・要素の数・入れ子の深さに
上限が無い、(iii) zip の中の XML は展開後の大きさに上限が無い、という穴があった。標準の expat(2.4.1 以降)は入力の増幅率を
制限し外部実体は読まないので、実体の爆発は今の環境では起きにくいが、それは **古い expat や別の環境では保証されない**。

- DOCTYPE: 解析器そのものの DOCTYPE 通知(``TreeBuilder.doctype``)で断る。バイト列の正規表現ではなく expat が読んだ後の通知なので、
  UTF-8 / UTF-16 の BOM つき・BOM なし、宣言つきの別エンコード(iso-8859-1 など)でも見落とさない
  (実測は tests/test_safe_xml_parse_2026_11_12.py)。
- 大きさ: 既定 50 MiB(SVG の既存の上限と同じ)。ただし **バイト数だけではメモリを抑えられない**(平らな ``<a/>`` を並べた 8.4 MB が
  約 185 MB になった。1 要素あたり約 88 バイトで入力の約 22 倍)ので、要素の数にも上限を置く。
- 要素の数: 既定 :data:`DEFAULT_MAX_ELEMENTS` = 100 万(約 97 MB で止まる)。決め方 = 手元の実ファイルの最大が OSM 3.2 MB の
  77,854 要素、CommonRoad 9,498、ginza.osm 13,789 なので、最大の実ファイルの約 13 倍(~35 MB の OSM まで通る)。
  ``drivejapan.osm_parse`` だけは街全体の OSM があり得るので 200 万。
- 入れ子の深さ: 既定 :data:`DEFAULT_MAX_DEPTH` = 256。実ファイルの最大は PLATEAU の 14。20 万段が受理されると、読んだ後の再帰
  (``copy.deepcopy`` など)が ``RecursionError`` やプロセスの異常終了になるので、Python の再帰上限(1000)の手前で断る。
- iterparse(CityGML など巨大なストリーム): 要素の総数の既定は **上限なし**。呼び出し側が ``elem.clear()`` して木を抱えない設計で、
  実ファイルは 1 本で 226 万要素(219 MB)あり、総数で切ると正常な街区ファイルが通らない。深さは同じ既定 256。
  ``clear()`` しない呼び出し側は ``max_elements`` を自分で付ける。
- zip の中の XML は展開後の大きさにも上限。

断る入力はすべて :class:`UnsafeXMLError`(``ValueError`` の子)。壊れた XML は標準どおり ``ET.ParseError`` のままで、
呼び出し側の既存の ``except ET.ParseError`` はそのまま効く。``defusedxml`` は依存に足さない(この門だけで同じ入力を断れる)。

公開: :func:`safe_xml_parse`(本文・bytes・パス)/ :func:`safe_xml_parse_zip_member`(zip の中の 1 メンバー)/
:func:`safe_xml_iterparse`(ストリーム読み)。
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
import xml.parsers.expat as _expat
from collections.abc import Iterator
from pathlib import Path
from typing import Any

__all__ = ["UnsafeXMLError", "DEFAULT_MAX_BYTES", "DEFAULT_MAX_ELEMENTS", "DEFAULT_MAX_DEPTH", "safe_xml_parse",
           "safe_xml_parse_zip_member", "safe_xml_iterparse"]

#: 既定の入力の上限(``optdraw._MAX_TEXT_BYTES`` の SVG と同じ 50 MiB)。
DEFAULT_MAX_BYTES = 50 * 1024 * 1024
#: 既定の要素数の上限(最大の実ファイル 77,854 要素の約 13 倍。約 97 MB で止まる)。
DEFAULT_MAX_ELEMENTS = 1_000_000
#: 既定の入れ子の深さの上限(実ファイルの最大 14、Python の再帰上限 1000 の手前)。
DEFAULT_MAX_DEPTH = 256
_CHUNK = 64 * 1024


class UnsafeXMLError(ValueError):
    """DOCTYPE / 実体宣言・大きさ / 要素数 / 深さの上限超えなど、安全の門が断った入力。``ValueError`` の子(既存の契約を保つ)。"""


class _GuardBuilder(ET.TreeBuilder):
    """DOCTYPE を見た瞬間に断り、要素の数と入れ子の深さを数える TreeBuilder(expat の通知で呼ばれる)。"""

    _op = "xml"
    _forbid = True
    _max_elements: int | None = None
    _max_depth: int | None = None

    def __init__(self) -> None:
        super().__init__()
        self._n = 0
        self._d = 0

    def doctype(self, name, pubid, system):  # noqa: D401 (ElementTree が呼ぶ名前)
        if self._forbid:
            raise _dtd_error(self._op, name)

    def start(self, tag, attrs):
        self._n += 1
        self._d += 1
        if self._max_depth is not None and self._d > self._max_depth:
            raise UnsafeXMLError("%s: XML nesting deeper than %d levels is refused" % (self._op, self._max_depth))
        if self._max_elements is not None and self._n > self._max_elements:
            raise UnsafeXMLError("%s: XML with more than %d elements is refused" % (self._op, self._max_elements))
        return super().start(tag, attrs)

    def end(self, tag):
        self._d -= 1
        return super().end(tag)


def _dtd_error(op: str, name: Any) -> UnsafeXMLError:
    return UnsafeXMLError(
        "%s: DOCTYPE / ENTITY declarations are refused (<!DOCTYPE %s> found; XML entity-expansion defense)" % (op, name))


def _check_limit(value: Any, what: str, op: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("%s: %s must be a positive int or None, got %r" % (op, what, value))
    return value


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


def _feed(payload: "str | bytes", forbid_dtd: bool, op: str, max_elements: int | None, max_depth: int | None):
    target = _GuardBuilder()
    target._op = op
    target._forbid = bool(forbid_dtd)
    target._max_elements = max_elements
    target._max_depth = max_depth
    parser = ET.XMLParser(target=target)
    parser.feed(payload)
    return parser.close()


def safe_xml_parse(data_or_path: "str | bytes | bytearray | os.PathLike[str]", *,
                   max_bytes: int | None = DEFAULT_MAX_BYTES, forbid_dtd: bool = True,
                   max_elements: int | None = DEFAULT_MAX_ELEMENTS, max_depth: int | None = DEFAULT_MAX_DEPTH,
                   kind: str = "auto", op: str = "xml") -> ET.Element:
    """XML(本文・bytes・パス)を DOCTYPE なし・大きさ / 要素数 / 深さの上限つきで読み、ルート要素を返す。

    ``kind="auto"``(既定): ``str`` と ``bytes`` は **常に XML の本文**、``os.PathLike``(``Path``)だけがパス。
    文字列をパスとして読むのは ``kind="path"`` を明示したときだけ(``\\\\host\\share\\x.xml`` のような UNC を本文の取り違えで
    開いて、ネットワーク越しに認証情報を送ってしまう経路を作らない)。``kind="data"`` は本文に固定。
    大きさは bytes はバイト数、``str`` は文字数で ``max_bytes`` と比べる。各上限は ``None`` で無効。
    ``forbid_dtd=True``(既定)なら DOCTYPE / ENTITY を含む入力を :class:`UnsafeXMLError` で断る。
    **Raises** :class:`UnsafeXMLError`(DTD・上限超え)/ ``ValueError``(型・パスが違う・上限の値が不正)/ ``ET.ParseError``。
    """
    limit = _check_limit(max_bytes, "max_bytes", op)
    max_elements = _check_limit(max_elements, "max_elements", op)
    max_depth = _check_limit(max_depth, "max_depth", op)
    if kind not in ("auto", "data", "path"):
        raise ValueError("%s: kind must be 'auto', 'data' or 'path', got %r" % (op, kind))
    if kind == "path" or (kind == "auto" and isinstance(data_or_path, os.PathLike)):
        if not isinstance(data_or_path, (str, os.PathLike)):
            raise ValueError("%s: a path must be str or PathLike, got %r" % (op, type(data_or_path).__name__))
        payload: "str | bytes" = _read_path(Path(data_or_path), limit, op)
    elif isinstance(data_or_path, (str, bytes, bytearray)):
        payload = data_or_path if isinstance(data_or_path, str) else bytes(data_or_path)
        if limit is not None and len(payload) > limit:
            raise _too_big(op, len(payload), limit, "characters" if isinstance(payload, str) else "bytes")
    else:
        raise ValueError("%s: expected an XML string, bytes or a path, got %r" % (op, type(data_or_path).__name__))
    return _feed(payload, forbid_dtd, op, max_elements, max_depth)


def safe_xml_parse_zip_member(zf: Any, name: "str | Any", *, max_bytes: int | None = DEFAULT_MAX_BYTES,
                              forbid_dtd: bool = True, max_elements: int | None = DEFAULT_MAX_ELEMENTS,
                              max_depth: int | None = DEFAULT_MAX_DEPTH, op: str = "xml") -> ET.Element:
    """zip の中の 1 メンバー(3MF の ``.model`` など)を読む。**展開後**の大きさにも ``max_bytes`` の上限(zip 爆弾の備え)。

    守りは 2 段: (1) 宣言された展開後の大きさ(``file_size``)が上限を超えるなら **展開せずに** 断る、(2) 宣言が嘘で小さくても
    ``max_bytes + 1`` バイトまでしか読まない。
    """
    limit = _check_limit(max_bytes, "max_bytes", op)
    info = zf.getinfo(name) if isinstance(name, str) else name
    if limit is not None and info.file_size > limit:
        raise _too_big(op, info.file_size, limit)
    with zf.open(info) as f:
        data = f.read() if limit is None else f.read(limit + 1)
    if limit is not None and len(data) > limit:
        raise _too_big(op, len(data), limit)
    return safe_xml_parse(data, max_bytes=None, forbid_dtd=forbid_dtd, max_elements=max_elements,
                          max_depth=max_depth, kind="data", op=op)


class _Replay:
    """先読みした bytes を先に返し、そのあとは元のストリームを読む(iterparse に渡す)。"""

    def __init__(self, head: bytes, stream: Any) -> None:
        self._head = head
        self._stream = stream

    def read(self, n: int = -1) -> bytes:
        if self._head:
            if n is None or n < 0:
                out, self._head = self._head + self._stream.read(), b""
                return out
            out, self._head = self._head[:n], self._head[n:]
            return out
        return self._stream.read(n)


class _RootSeen(Exception):
    pass


def _refuse_dtd_in_prolog(stream: Any, op: str) -> Any:
    """ルート要素の開始まで(= DOCTYPE があり得る所だけ)を expat の通知で調べ、DOCTYPE があれば断る。読んだ分は :class:`_Replay` で返す。"""
    parser = _expat.ParserCreate()

    def _dt(name, *rest):
        raise _dtd_error(op, name)

    def _root(name, attrs):
        raise _RootSeen

    parser.StartDoctypeDeclHandler = _dt
    parser.StartElementHandler = _root
    seen: list[bytes] = []
    while True:
        chunk = stream.read(_CHUNK)
        if not chunk:
            try:  # 入力の終わり: expat は末尾の token を次のデータが来るまで保留するので、確定させて通知を出し切る
                parser.Parse(b"", True)
            except (_RootSeen, _expat.ExpatError):
                pass
            break
        if not isinstance(chunk, (bytes, bytearray)):
            raise ValueError("%s: safe_xml_iterparse needs a binary stream (got %s chunks)" % (op, type(chunk).__name__))
        seen.append(bytes(chunk))
        try:
            parser.Parse(chunk, False)
        except _RootSeen:
            break
        except _expat.ExpatError:
            break  # 壊れた前置きは、このあと ET.iterparse が ParseError として報告する
    return _Replay(b"".join(seen), stream)


def safe_xml_iterparse(stream: Any, *, forbid_dtd: bool = True, max_elements: int | None = None,
                       max_depth: int | None = DEFAULT_MAX_DEPTH, op: str = "xml") -> Iterator[tuple[str, ET.Element]]:
    """``ET.iterparse(stream, events=("end",))`` の DOCTYPE なし・深さ上限つき版。``("end", 要素)`` を順に返す(読みながら ``elem.clear()`` してよい)。

    巨大なストリーム(CityGML など)を読むので、大きさと要素の総数の既定は **上限なし**(``max_elements=None``。理由は
    モジュールの説明)。``elem.clear()`` しない呼び出し側は ``max_elements`` を付ける。DOCTYPE はルート要素の前の部分を
    expat で調べて断る(以降の本体は標準の C の ``iterparse`` のまま走るので、遅さは深さの印の分だけ)。
    壊れた XML は ``ET.ParseError``。``stream`` は bytes を返す file-like。
    """
    max_elements = _check_limit(max_elements, "max_elements", op)
    max_depth = _check_limit(max_depth, "max_depth", op)
    if forbid_dtd:
        stream = _refuse_dtd_in_prolog(stream, op)
    depth = 0
    count = 0
    for event, elem in ET.iterparse(stream, events=("start", "end")):
        if event == "start":
            depth += 1
            count += 1
            if max_depth is not None and depth > max_depth:
                raise UnsafeXMLError("%s: XML nesting deeper than %d levels is refused" % (op, max_depth))
            if max_elements is not None and count > max_elements:
                raise UnsafeXMLError("%s: XML with more than %d elements is refused" % (op, max_elements))
            continue
        depth -= 1
        yield "end", elem
