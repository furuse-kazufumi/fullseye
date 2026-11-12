# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.parambundle — パラメータを束で持ち、ファイルから読んで op にまとめて渡す層(画面に依らない部分)。

    import fullseye as fs
    p = fs.load_params("rig.toml")                    # JSON / TOML / YAML(PyYAML があれば)
    out = fs.undistort_image(img, **p.for_op("undistort_image"))
    out = fs.run_params("undistort_image", img, params=p)    # 同じことの糖衣

なぜ要るか(調査 DEFS_IO_SURVEY.md §5.10): 台帳 2,879 op のうち引数 6 個以上が 873 本。カメラ K とレンズ系は
すでに束で渡しているが、波長・画素ピッチ・焦点などは 1 つずつ並べ、**同じ量が綴りと単位で割れている**
(画素ピッチ 3 綴り、波長 ``_um`` 50 / ``_nm`` 28)。単位は引数名の接尾辞にだけあり、値には付かない。

## 決め(調査の「推す側」)

* 中身は形式に依らない対応表(ドット区切りの葉のキー → 値)。JSON(標準)・TOML(標準 ``tomllib``、読むだけ)・
  YAML(optional extra、``safe_load`` だけ。読んだ後に門)。JSONC / JSON5 は受けない。
* 値は「数」「数 + 単位の文字列(``"550 nm"``)」「配列」「文字列」「真偽」。単位つきは値と単位を**そのまま**持つ。
* 単位の変換は**使うとき 1 回だけ**、10 の冪の単位は ``Decimal``(``nm→um`` を ``v*1e-3`` でやると 10 万個中
  23,496 個が 1 ULP ずれる)。deg / rad は不可避の丸めで、変換先の単位は op の引数名の接尾辞が決める。
* **黙って捨てない**: 未使用キー・不足する必須引数・単位違い・型違いは名前つきで断る。
* **任意コード・式は許さない**。派生値は ``K()`` のように固定の変換だけ。参照は型で区別する
  (``{"$param": "camera.fx"}`` / TOML の ``{ ref = "camera.fx" }``)。文字列 ``"camera.fx"`` は参照ではない。
* ``fs.apply`` の契約も既存 op の引数も変えない。``**p`` の丸ごと展開は基本にしない(op が受けないキーで
  TypeError になる)ので、``p.for_op(op)`` が**その op の引数だけ**を取り出す。
"""
from __future__ import annotations

import datetime as _dt
import difflib
import inspect
import itertools
import json
import math
import os
import re
import tempfile
import warnings
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, localcontext
from typing import Any, Callable, NamedTuple

import numpy as np

__all__ = [
    "ParamBundle", "ParamSection", "Quantity", "Origin", "ParamReport", "ReportEntry",
    "ParamComparison", "CompareRow", "ParamGrid",
    "load_params", "save_params", "params_compare", "param_grid", "param_zip", "sweep", "run_params",
    "ParamError", "ParamFileError", "MissingParam", "UnitMismatch", "ParamTypeError",
    "UnusedParams", "GridTooLarge", "AmbiguousParam", "ParamWarning",
    "SYNONYM_GROUPS", "UNITS",
]

#: ファイルの大きさの上限(バイト)。設定ファイルに MB 級は要らない(巨大な入力で止める)。
MAX_FILE_BYTES = 4_000_000
#: ``include`` の入れ子の深さと、参照の連鎖の深さの上限。
MAX_INCLUDE_DEPTH = 8
MAX_REF_DEPTH = 32
#: YAML のアンカー/エイリアスを展開したあとの節点数・深さの上限(billion laughs の備え)。
MAX_YAML_NODES = 100_000
MAX_YAML_DEPTH = 100
#: ``param_grid`` の既定の件数の上限。
DEFAULT_MAX_GRID_POINTS = 10_000


# ----------------------------------------------------------------------------------------------
# 例外
# ----------------------------------------------------------------------------------------------
class ParamError(ValueError):
    """束まわりの失敗の基底。黙って捨てず、名前つきで理由を言う。"""


class ParamFileError(ParamError):
    """ファイルが読めない・形式が不正・門(型・重複・上限)に落ちた。"""


class MissingParam(ParamError):
    """op の必須引数が束から作れない。必要な名前・束に在る名前・導出の手がかりを含む。"""


class UnitMismatch(ParamError):
    """単位違い(次元が違う・単位が無い)。"""


class ParamTypeError(ParamError, TypeError):
    """型違い(数の欄に文字列・真偽など)。"""


class UnusedParams(ParamError):
    """``strict=True`` で、どの引数にも当たらなかったキーがある。"""


class GridTooLarge(ParamError):
    """走査の直積が上限を超える。件数と見積もりを先に出して断る。"""


class AmbiguousParam(ParamError):
    """同じ名前の葉が複数の節にあり、どれか決められない。"""


class ParamWarning(UserWarning):
    """未使用キーなどの警告(``warnings`` 経由)。"""


# ----------------------------------------------------------------------------------------------
# 単位
# ----------------------------------------------------------------------------------------------
#: 単位 → (次元, 基準単位に対する倍率)。10 の冪は Decimal で厳密。角度は別扱い(丸めが不可避)。
UNITS: dict[str, tuple[str, Decimal]] = {
    "m": ("length", Decimal(1)), "cm": ("length", Decimal("1E-2")), "mm": ("length", Decimal("1E-3")),
    "um": ("length", Decimal("1E-6")), "nm": ("length", Decimal("1E-9")), "pm": ("length", Decimal("1E-12")),
    "s": ("time", Decimal(1)), "ms": ("time", Decimal("1E-3")), "us": ("time", Decimal("1E-6")),
    "ns": ("time", Decimal("1E-9")),
    "hz": ("frequency", Decimal(1)), "khz": ("frequency", Decimal("1E3")),
    "mhz": ("frequency", Decimal("1E6")), "ghz": ("frequency", Decimal("1E9")),
    "px": ("pixel", Decimal(1)),
    "deg": ("angle", Decimal(1)), "rad": ("angle", Decimal(1)),
}
#: 値の中に書ける綴り → 正規の単位(大文字小文字を区別する: ``Mm`` と ``mm`` を取り違えない)。
_UNIT_SPELLINGS: dict[str, str] = {
    **{u: u for u in UNITS},
    "µm": "um", "μm": "um", "µs": "us", "μs": "us",
    "Hz": "hz", "kHz": "khz", "MHz": "mhz", "GHz": "ghz",
    "°": "deg", "degree": "deg", "degrees": "deg", "pixel": "px", "pixels": "px",
}
_SUFFIX_RE = re.compile(r"^(?P<stem>.+)_(?P<unit>" + "|".join(sorted(UNITS, key=len, reverse=True)) + r")$")
_NUM = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
_NUM_FULL = re.compile(_NUM)
_QUANTITY_RE = re.compile(r"\s*(" + _NUM + r")\s*([^\s\d+\-.][^\s]*)\s*")
#: 引数名に単位が無くても暗黙に画素と決まっているもの(内部パラメータ)。
_IMPLICIT_UNIT: dict[str, str] = {"fx": "px", "fy": "px", "cx": "px", "cy": "px", "skew": "px"}


def split_suffix(name: str) -> tuple[str, str | None]:
    """``wavelength_um`` → (``wavelength``, ``um``)。接尾辞が単位でなければ (name, None)。"""
    m = _SUFFIX_RE.match(name)
    if m:
        return m.group("stem"), m.group("unit")
    return name, None


def _dec(value: int | float | str) -> Decimal:
    """数を 10 進の**書かれた値のまま**にする(float は最短の repr、つまり利用者が書いた桁)。"""
    return Decimal(repr(value) if isinstance(value, float) else str(value))


def convert_number(value: int | float | Decimal, unit_from: str, unit_to: str) -> float | int:
    """``value`` を ``unit_from`` から ``unit_to`` へ**1 回だけ**変換する。10 の冪の単位は Decimal で厳密。

    同じ単位なら値をそのまま返す(int は int のまま)。次元が違えば :class:`UnitMismatch`。
    deg ↔ rad は ``math`` の丸めが不可避で、往復では戻らない(だから結果を束へ書き戻さない)。
    """
    if unit_from == unit_to:
        return value if not isinstance(value, Decimal) else float(value)
    dim_f, fac_f = UNITS[unit_from]
    dim_t, fac_t = UNITS[unit_to]
    if dim_f != dim_t:
        raise UnitMismatch("cannot convert %s (%s) to %s (%s)" % (unit_from, dim_f, unit_to, dim_t))
    if dim_f == "angle":
        v = float(value)
        return math.radians(v) if unit_from == "deg" else math.degrees(v)
    x = value if isinstance(value, Decimal) else _dec(value)
    with localcontext() as ctx:
        ctx.prec = 80
        r = x * (fac_f / fac_t)
    return float(r)


@dataclass(frozen=True)
class Quantity:
    """数 + 単位。書かれた値と単位を**そのまま**持つ(変換して書き戻さない)。

    ``text`` は書かれた数の字面(``"550"``)。``Decimal(text)`` が厳密な値で、変換の基準になる。
    """

    value: int | float
    unit: str
    text: str

    @property
    def dimension(self) -> str:
        return UNITS[self.unit][0]

    @property
    def exact(self) -> Decimal:
        """書かれた値の 10 進表現(厳密)。"""
        return Decimal(self.text)

    def to(self, unit: str) -> float | int:
        """``unit`` に変換した数(10 の冪の単位は Decimal で 1 回だけ)。"""
        if unit not in UNITS:
            raise UnitMismatch("unknown unit %r" % unit)
        return convert_number(self.exact, self.unit, unit) if self.unit != unit else self.value

    def __str__(self) -> str:
        return "%s %s" % (self.text, self.unit)


def parse_quantity(text: str) -> Quantity | None:
    """``"550 nm"`` → :class:`Quantity`。数 + 既知の単位でなければ None(ただの文字列)。"""
    m = _QUANTITY_RE.fullmatch(text)
    if not m:
        return None
    unit = _UNIT_SPELLINGS.get(m.group(2))
    if unit is None:
        return None
    tok = m.group(1)
    try:
        val: int | float = float(tok) if re.search(r"[.eE]", tok) else int(tok)
    except ValueError:
        return None
    if isinstance(val, float) and not math.isfinite(val):
        raise ParamFileError("non-finite number in %r" % text)
    return Quantity(val, unit, tok.lstrip("+") if tok.startswith("+") else tok)


# ----------------------------------------------------------------------------------------------
# 同義の綴りの表(調査の表 P の割れを正本として 1 か所に持つ)
# ----------------------------------------------------------------------------------------------
#: 同じ量の綴りの群(単位の接尾辞を除いた幹)。op の引数の幹と束のキーの幹が同じ群なら同義とみなす。
#: 入れなかったもの: ``pitch``(``grating_wavelengths(pitch_um)`` は格子のピッチで画素ではない)、``f``(周波数と衝突)。
SYNONYM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("wavelength", "wl", "lambda"),
    ("pixel_pitch", "pixel", "pixel_size"),
    ("focal", "focal_length", "efl"),
    ("f_number", "fnumber", "fnum", "fno", "f_no"),
    ("na", "numerical_aperture"),
    ("exposure", "exposure_time", "t_exp"),
    ("qe", "quantum_efficiency"),
)
_STEM_GROUP: dict[str, tuple[str, ...]] = {s: g for g in SYNONYM_GROUPS for s in g}
#: 「数の欄」とみなす幹(文字列や真偽が来たら断る)。単位の接尾辞があるキーも数の欄。
_NUMERIC_STEMS = frozenset(_STEM_GROUP) | frozenset({"fx", "fy", "cx", "cy", "skew", "k1", "k2", "k3", "p1", "p2", "sigma"})
#: 配列を ndarray にして渡す引数名(op は ndarray 前提の物が多い)。
_ARRAY_ARGS = frozenset({"K", "dist", "R", "t", "cam_par"})
#: 呼び出し側が渡す「データ」とみなす引数名(束から探さない)。
_DATA_ARG_NAMES = frozenset(
    "image img x psf field aperture volume voxel vol points pts uv xy xyz mesh depth disparity signal "
    "data array table profile pointcloud cloud frame frames stack".split())


def _is_numeric_name(leaf: str) -> bool:
    stem, unit = split_suffix(leaf)
    return unit is not None or stem in _NUMERIC_STEMS


# ----------------------------------------------------------------------------------------------
# 値の正規化・出どころ
# ----------------------------------------------------------------------------------------------
class Origin(NamedTuple):
    """値の出どころ。``line`` は YAML だけ(TOML の ``tomllib`` と標準の ``json`` は行を返さない)。"""

    source: str
    key: str
    line: int | None = None
    ref: str | None = None      #: 参照で入った値なら、参照先のキー

    def __str__(self) -> str:
        s = "%s:%d" % (self.source, self.line) if self.line else "%s:%s" % (self.source, self.key)
        return s + (" (ref %s)" % self.ref if self.ref else "")


class _Ref(NamedTuple):
    """読む途中の参照の目印(解決したあとの束には残らない)。"""

    target: str


def _norm_scalar(value: Any, key: str) -> Any:
    """葉の値を「数 / Quantity / 文字列 / 真偽 / それらの配列(tuple)」に揃える。それ以外は断る。"""
    leaf = key.rsplit(".", 1)[-1]
    if isinstance(value, bool):
        if _is_numeric_name(leaf):
            raise ParamTypeError(
                "%s: boolean %s in a numeric field (YAML 1.1 reads no/yes/on/off as booleans; "
                "write a number, or quote a string)" % (key, value))
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ParamFileError("%s: non-finite number (%r); a bundle holds finite numbers only" % (key, value))
        return value
    if isinstance(value, Quantity):
        return value
    if isinstance(value, str):
        q = parse_quantity(value)
        if q is not None:
            return q
        if _is_numeric_name(leaf):
            raise ParamTypeError(
                "%s: string %r in a numeric field; write a number or a quantity such as \"550 nm\"" % (key, value))
        return value
    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        out = []
        for i, v in enumerate(value):
            if isinstance(v, Mapping):
                raise ParamFileError("%s[%d]: a table inside an array is not supported (use sections)" % (key, i))
            out.append(_norm_scalar(v, "%s[%d]" % (key, i)) if not isinstance(v, (list, tuple)) else _norm_scalar(v, key))
        return tuple(out)
    if value is None:
        raise ParamFileError("%s: null is not a value (omit the key)" % key)
    raise ParamFileError("%s: unsupported value type %s" % (key, type(value).__name__))


def _check_key(k: Any, where: str) -> str:
    if not isinstance(k, str):
        raise ParamFileError(
            "%s: key %r is a %s, not a string (YAML 1.1 reads NO/yes/on/off/1 as bool/int keys; quote it)"
            % (where or "<root>", k, type(k).__name__))
    if not k or k != k.strip() or "." in k or "\x00" in k:
        raise ParamFileError("%s: invalid key %r (empty / padded / contains '.'; nest with sections instead)" % (where or "<root>", k))
    return k


def _flatten(tree: Mapping, prefix: str, out: dict[str, Any], lines: Mapping[str, int] | None,
             source: str, origins: dict[str, Origin], fmt: str) -> None:
    """入れ子の表を葉(ドット区切りのキー)へ。参照の目印はそのまま ``_Ref`` で入れる。"""
    ref_key = "ref" if fmt == "toml" else None
    for k, v in tree.items():
        k = _check_key(k, prefix)
        full = prefix + "." + k if prefix else k
        if isinstance(v, Mapping):
            if len(v) == 1 and ("$param" in v or (ref_key and ref_key in v)):
                tk = "$param" if "$param" in v else ref_key
                tgt = v[tk]
                if not isinstance(tgt, str) or not tgt:
                    raise ParamFileError("%s: reference target must be a non-empty string" % full)
                out[full] = _Ref(tgt)
            else:
                _flatten(v, full, out, lines, source, origins, fmt)
                continue
        else:
            out[full] = _norm_scalar(v, full)
        origins[full] = Origin(source, full, (lines or {}).get(full))


def _check_layout(leaves: Mapping[str, Any]) -> None:
    """葉と節が同じ名前で衝突していないか(``a = 1`` と ``a.b = 2``)。"""
    prefixes: set[str] = set()
    for k in leaves:
        parts = k.split(".")
        for i in range(1, len(parts)):
            prefixes.add(".".join(parts[:i]))
    if "include" in leaves or "include" in prefixes:
        raise ParamFileError("the top-level key 'include' is reserved for file inclusion")
    clash = sorted(prefixes & set(leaves))
    if clash:
        raise ParamFileError("key %r is both a value and a section" % clash[0])


# ----------------------------------------------------------------------------------------------
# 形式ごとの読み
# ----------------------------------------------------------------------------------------------
def _reject_const(name: str) -> Any:
    raise ParamFileError("JSON constant %s is not allowed (a bundle holds finite numbers only)" % name)


def _json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    d: dict[str, Any] = {}
    for k, v in pairs:
        if k in d:
            raise ParamFileError("duplicate key %r in JSON object" % k)
        d[k] = v
    return d


def _parse_json(text: str) -> tuple[Mapping, None]:
    try:
        tree = json.loads(text, object_pairs_hook=_json_pairs, parse_constant=_reject_const)
    except json.JSONDecodeError as e:
        raise ParamFileError("invalid JSON (comments and trailing commas are not accepted): %s" % e) from e
    return tree, None


def _parse_toml(text: str) -> tuple[Mapping, None]:
    import tomllib
    try:
        return tomllib.loads(text), None
    except tomllib.TOMLDecodeError as e:
        raise ParamFileError("invalid TOML: %s" % e) from e


_YAML_HINT = ("YAML needs PyYAML: pip install \"fullseye[yaml]\"  (or: pip install pyyaml). "
              "TOML (standard library) and JSON work without it.")


def _yaml_walk(node: Any, path: str, lines: dict[str, int], budget: list[int], depth: int, active: set[int]) -> None:
    """節点グラフを歩いて、展開後の節点数・深さ・循環・キー重複を検査し、キーの行を集める。

    エイリアスは同じ節点を指すので、展開すると指数的に増える(billion laughs)。訪問のたびに数え、
    上限を超えた時点で止める(増幅の全体を歩かない)。
    """
    import yaml
    budget[0] += 1
    if budget[0] > MAX_YAML_NODES:
        raise ParamFileError("YAML expands to more than %d nodes (alias bomb?)" % MAX_YAML_NODES)
    if depth > MAX_YAML_DEPTH:
        raise ParamFileError("YAML nesting deeper than %d" % MAX_YAML_DEPTH)
    nid = id(node)
    if nid in active:
        raise ParamFileError("YAML recursive alias (an anchor that contains itself)")
    if isinstance(node, yaml.ScalarNode):
        return
    active.add(nid)
    try:
        if isinstance(node, yaml.MappingNode):
            seen: set[tuple[str, Any]] = set()
            for knode, vnode in node.value:
                sub = path
                if isinstance(knode, yaml.ScalarNode) and knode.tag != "tag:yaml.org,2002:merge":
                    ident = (knode.tag, knode.value)
                    if ident in seen:
                        raise ParamFileError("duplicate key %r in YAML mapping (line %d)"
                                             % (knode.value, knode.start_mark.line + 1))
                    seen.add(ident)
                    sub = path + "." + knode.value if path else knode.value
                    lines.setdefault(sub, knode.start_mark.line + 1)
                _yaml_walk(vnode, sub, lines, budget, depth + 1, active)
        elif isinstance(node, yaml.SequenceNode):
            for i, c in enumerate(node.value):
                _yaml_walk(c, "%s[%d]" % (path, i), lines, budget, depth + 1, active)
    finally:
        active.discard(nid)


def _parse_yaml(text: str) -> tuple[Mapping, dict[str, int]]:
    """``safe_load`` だけ(任意のコードは走らない)。重複キー・展開量・循環を断り、日付は文字列へ。"""
    try:
        import yaml
    except ImportError as e:                                  # pragma: no cover - 環境による
        raise ParamFileError(_YAML_HINT) from e

    class _Loader(yaml.SafeLoader):
        """SafeLoader の薄い派生: 日付・日時を文字列で返す(型を増やさない)。"""

    def _ts(loader: Any, node: Any) -> str:
        return loader.construct_scalar(node)

    _Loader.add_constructor("tag:yaml.org,2002:timestamp", _ts)
    loader = _Loader(text)
    try:
        try:
            node = loader.get_single_node()
        except yaml.YAMLError as e:
            raise ParamFileError("invalid YAML: %s" % e) from e
        if node is None:
            return {}, {}
        lines: dict[str, int] = {}
        _yaml_walk(node, "", lines, [0], 0, set())
        try:
            tree = loader.construct_document(node)
        except yaml.YAMLError as e:
            raise ParamFileError("invalid YAML: %s" % e) from e
    finally:
        loader.dispose()
    _gate_yaml(tree, "")
    return tree, lines


def _gate_yaml(obj: Any, path: str) -> None:
    """YAML 1.1 の罠の門: 文字列になった数(``1e-3``)・数や真偽になったキーを断る。"""
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            _check_key(k, path)
            _gate_yaml(v, path + "." + k if path else k)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _gate_yaml(v, "%s[%d]" % (path, i))
    elif isinstance(obj, str) and _NUM_FULL.fullmatch(obj.strip()):
        raise ParamTypeError(
            "%s: %r was read as a string, not a number (YAML 1.1 needs a decimal point: write 1.0e-3 instead of 1e-3; "
            "or use TOML/JSON)" % (path or "<root>", obj))


_PARSERS: dict[str, tuple[str, Callable[[str], tuple[Mapping, Any]]]] = {
    ".json": ("json", _parse_json), ".toml": ("toml", _parse_toml),
    ".yaml": ("yaml", _parse_yaml), ".yml": ("yaml", _parse_yaml),
}


# ----------------------------------------------------------------------------------------------
# include の安全
# ----------------------------------------------------------------------------------------------
def _safe_include(rel: Any, base_dir: str, root_dir: str) -> str:
    """``include`` のパスを検査して絶対パスを返す。外を指す物・絶対パス・シンボリックリンクは断る。"""
    if not isinstance(rel, str) or not rel.strip():
        raise ParamFileError("include entries must be non-empty strings, got %r" % (rel,))
    if "\x00" in rel:
        raise ParamFileError("include path contains NUL")
    norm = rel.replace("\\", "/")
    if os.path.isabs(rel) or norm.startswith("/") or re.match(r"^[A-Za-z]:", norm) or norm.startswith("~"):
        raise ParamFileError("include %r: absolute paths are refused (use a path under the including file's folder)" % rel)
    parts = [p for p in norm.split("/") if p not in ("", ".")]
    if ".." in parts:
        raise ParamFileError("include %r points outside the including folder ('..' is refused)" % rel)
    cur = base_dir
    for part in parts:
        cur = os.path.join(cur, part)
        if os.path.islink(cur):
            raise ParamFileError("include %r goes through a symbolic link (%s); refused" % (rel, part))
    full = os.path.abspath(cur)
    real = os.path.realpath(full)
    expected = os.path.join(os.path.realpath(base_dir), *parts)
    if os.path.normcase(real) != os.path.normcase(expected):
        raise ParamFileError("include %r resolves elsewhere (%s): link or junction; refused" % (rel, real))
    root_abs = os.path.normcase(os.path.realpath(root_dir))
    try:
        inside = os.path.commonpath([root_abs, os.path.normcase(real)]) == root_abs
    except ValueError:
        inside = False
    if not inside:
        raise ParamFileError("include %r is outside the bundle's folder" % rel)
    return full


def _read_text(path: str, max_bytes: int) -> str:
    try:
        size = os.path.getsize(path)
    except OSError as e:
        raise ParamFileError("cannot read %s: %s" % (path, e)) from e
    if size > max_bytes:
        raise ParamFileError("%s is %d bytes; limit is %d" % (path, size, max_bytes))
    try:
        with open(path, "rb") as f:
            raw = f.read(max_bytes + 1)
    except OSError as e:
        raise ParamFileError("cannot read %s: %s" % (path, e)) from e
    if len(raw) > max_bytes:
        raise ParamFileError("%s is larger than %d bytes" % (path, max_bytes))
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ParamFileError("%s is not valid UTF-8: %s" % (path, e)) from e


def _load_file(path: str, root_dir: str, stack: tuple[str, ...], display: str, max_bytes: int
               ) -> tuple[dict[str, Any], dict[str, Origin]]:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jsonc", ".json5"):
        raise ParamFileError("%s: JSONC / JSON5 are not accepted (one reader, one grammar). "
                             "Use TOML for hand-written files with comments." % path)
    if ext not in _PARSERS:
        raise ParamFileError("%s: unknown extension %r (use .json, .toml, .yaml / .yml)" % (path, ext))
    if len(stack) >= MAX_INCLUDE_DEPTH:
        raise ParamFileError("include nested deeper than %d" % MAX_INCLUDE_DEPTH)
    ap = os.path.abspath(path)
    if os.path.normcase(ap) in stack:
        raise ParamFileError("circular include: %s" % " -> ".join(list(stack) + [os.path.normcase(ap)]))
    fmt, parser = _PARSERS[ext]
    text = _read_text(path, max_bytes)
    tree, lines = parser(text)
    if not isinstance(tree, Mapping):
        raise ParamFileError("%s: top level must be an object / table" % path)
    tree = dict(tree)
    inc = tree.pop("include", None)
    leaves: dict[str, Any] = {}
    origins: dict[str, Origin] = {}
    if inc is not None:
        if isinstance(inc, str) or not isinstance(inc, (list, tuple)):
            raise ParamFileError("%s: include must be a list of file names" % path)
        for rel in inc:
            full = _safe_include(rel, os.path.dirname(ap), root_dir)
            sub_l, sub_o = _load_file(full, root_dir, stack + (os.path.normcase(ap),),
                                      os.path.relpath(full, root_dir).replace("\\", "/"), max_bytes)
            leaves.update(sub_l)
            origins.update(sub_o)
    own: dict[str, Any] = {}
    own_o: dict[str, Origin] = {}
    _flatten(tree, "", own, lines, display, own_o, fmt)
    leaves.update(own)
    origins.update(own_o)
    return leaves, origins


def _resolve_refs(leaves: dict[str, Any], origins: dict[str, Origin]) -> None:
    """参照を値に置き換える(読むとき 1 回)。循環と未解決は断る。"""
    for key in list(leaves):
        if not isinstance(leaves[key], _Ref):
            continue
        chain = [key]
        cur = leaves[key]
        depth = 0
        while isinstance(cur, _Ref):
            tgt = cur.target
            if tgt in chain:
                raise ParamError("circular reference: %s" % " -> ".join(chain + [tgt]))
            if tgt not in leaves:
                near = difflib.get_close_matches(tgt, [k for k in leaves if not isinstance(leaves[k], _Ref)], n=3)
                raise ParamError("%s: reference to %r does not resolve%s" % (
                    key, tgt, " (did you mean %s?)" % ", ".join(near) if near else ""))
            chain.append(tgt)
            cur = leaves[tgt]
            depth += 1
            if depth > MAX_REF_DEPTH:
                raise ParamError("reference chain deeper than %d at %s" % (MAX_REF_DEPTH, key))
        o = origins.get(key)
        leaves[key] = cur
        if o is not None:
            origins[key] = Origin(o.source, o.key, o.line, chain[1])


def load_params(path: str | os.PathLike, *, max_bytes: int = MAX_FILE_BYTES) -> "ParamBundle":
    """JSON / TOML / YAML のファイルを読んで :class:`ParamBundle` にする。

    * 拡張子で形式を決める(``.json`` ``.toml`` ``.yaml`` ``.yml``)。JSONC / JSON5 は断る。
    * 最上位の ``include = ["base.toml"]`` は**そのファイルと同じ階層以下だけ**(外・絶対パス・リンクは断る)。
    * ``{"$param": "camera.fx"}``(TOML は ``{ ref = "camera.fx" }``)は読むとき 1 回で解決、循環は断る。
    * 数の欄の文字列・真偽、キー重複、非有限の数、YAML のアンカーの展開上限は :class:`ParamError` で断る。
    """
    p = os.fspath(path)
    if not os.path.isfile(p):
        raise ParamFileError("not a file: %s" % p)
    root = os.path.dirname(os.path.abspath(p))
    leaves, origins = _load_file(p, root, (), os.path.basename(p), max_bytes)
    _check_layout(leaves)
    _resolve_refs(leaves, origins)
    return ParamBundle._make(leaves, origins, os.path.basename(p))


# ----------------------------------------------------------------------------------------------
# 比較用の値の同一性(単位違いで値が等しい物を同じと見分ける)
# ----------------------------------------------------------------------------------------------
def values_equal(a: Any, b: Any) -> bool:
    """意味として同じ値か。``"0.55 um"`` と ``"550 nm"`` は同じ。数と単位つきは別物。"""
    if isinstance(a, Quantity) or isinstance(b, Quantity):
        if not (isinstance(a, Quantity) and isinstance(b, Quantity)):
            return False
        da, fa = UNITS[a.unit]
        db, fb = UNITS[b.unit]
        if da != db:
            return False
        if da == "angle" and a.unit != b.unit:
            x, y = (a.to("rad"), b.to("rad"))
            return math.isclose(x, y, rel_tol=1e-12, abs_tol=1e-15)
        with localcontext() as ctx:
            ctx.prec = 80
            return a.exact * fa == b.exact * fb
    if isinstance(a, tuple) or isinstance(b, tuple):
        return (isinstance(a, tuple) and isinstance(b, tuple) and len(a) == len(b)
                and all(values_equal(x, y) for x, y in zip(a, b)))
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    return a == b


def _jsonable(v: Any) -> Any:
    if isinstance(v, Quantity):
        return str(v)
    if isinstance(v, tuple):
        return [_jsonable(x) for x in v]
    return v


# ----------------------------------------------------------------------------------------------
# op に渡す: 記録
# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ReportEntry:
    """``for_op`` が 1 つの引数を埋めた記録。"""

    arg: str
    keys: tuple[str, ...]          #: 使った束のキー
    how: str                       #: exact / section / synonym / derived
    source: str                    #: 束の値(文字列で)
    value: Any                     #: op に渡した値
    converted: bool = False        #: 単位を変換したか
    note: str = ""


@dataclass
class ParamReport:
    """``p.for_op(name, report=True)`` の記録: 写した・変換した・導出した事実と、使わなかったキー。"""

    op: str
    bundle: str
    entries: list[ReportEntry] = field(default_factory=list)
    unused: list[str] = field(default_factory=list)

    def _by(self, pred: Callable[[ReportEntry], bool]) -> list[ReportEntry]:
        return [e for e in self.entries if pred(e)]

    @property
    def copied(self) -> list[ReportEntry]:
        """そのまま写した(名前が完全一致、または節の指定)。"""
        return self._by(lambda e: e.how in ("exact", "section") and not e.converted)

    @property
    def converted(self) -> list[ReportEntry]:
        """単位を変換して渡した。"""
        return self._by(lambda e: e.converted)

    @property
    def synonyms(self) -> list[ReportEntry]:
        """同義の綴りの表で写した。"""
        return self._by(lambda e: e.how == "synonym")

    @property
    def derived(self) -> list[ReportEntry]:
        """固定の導出で作った(``K`` を fx, fy, cx, cy から)。"""
        return self._by(lambda e: e.how == "derived")

    def text(self) -> str:
        """人が読む 1 ブロック。"""
        rows = ["%s (%s)" % (self.op, self.bundle)]
        for e in self.entries:
            tail = " (%s -> %r)" % (e.source, e.value) if (e.converted or e.how == "synonym") else ""
            rows.append("  %s <- %s [%s]%s%s" % (e.arg, ", ".join(e.keys), e.how, tail, " " + e.note if e.note else ""))
        if self.unused:
            rows.append("  unused: " + ", ".join(self.unused))
        return "\n".join(rows)


# ----------------------------------------------------------------------------------------------
# op の探索
# ----------------------------------------------------------------------------------------------
def _find_callable(op_name: str) -> Callable[..., Any]:
    """台帳 → facade → 進化する 2-D op(``apply`` の a/b つまみ)の順で op を探す。"""
    import fullseye as fs
    if not isinstance(op_name, str) or not op_name:
        raise ParamError("op name must be a non-empty string")
    f = getattr(fs.ledger, op_name, None)
    if callable(f):
        return f
    try:
        f = getattr(fs, op_name)
    except AttributeError:
        f = None
    if callable(f) and not isinstance(f, type):
        return f
    try:
        known = fs.find_op(op_name)
    except Exception:                                        # noqa: BLE001 - 名前の不在はこの下で言う
        known = None
    if known is not None:
        def _registry_op(image: Any, a: float = 0.5, b: float = 0.5) -> Any:
            return fs.apply(image, op_name, a, b)
        _registry_op.__name__ = op_name
        return _registry_op
    near = difflib.get_close_matches(op_name, [n for n in dir(fs.ledger) if not n.startswith("_")], n=3)
    raise ParamError("unknown op %r%s" % (op_name, " (did you mean %s?)" % ", ".join(near) if near else ""))


def _auto_data_names(op_name: str, sig: inspect.Signature) -> set[str]:
    """呼び出し側が渡す「データ」の引数名。台帳の型づけ(kind == data)があればそれ、なければ名前で。"""
    names = {p for p in sig.parameters if p in _DATA_ARG_NAMES}
    try:
        import fullseye as fs
        info = fs.op_assist(op_name, measure=False)
        names |= {p["name"] for p in info.get("params", ()) if p.get("kind") == "data"}
    except Exception:                                        # noqa: BLE001 - 台帳の外の関数は名前だけで決める
        pass
    return names


# ----------------------------------------------------------------------------------------------
# 束
# ----------------------------------------------------------------------------------------------
class ParamBundle(Mapping):
    """読み取り専用のパラメータの束。キーはドット区切り(``camera.fx``)。

    ``p["camera.fx"]``・``p.camera.fx``・``p.fx``(その名の葉が 1 つだけのとき)・節 ``p["camera"]``・
    ``p.origin("fx")``(出どころ)。値は数(int / float)・:class:`Quantity`・文字列・真偽・それらの配列(tuple)。
    """

    __slots__ = ("_leaves", "_origins", "_name", "_by_leaf", "_sections")

    # -- 構築 ---------------------------------------------------------------------------------
    def __init__(self, data: Mapping[str, Any] | None = None, *, name: str = "<code>") -> None:
        """辞書から作る(入れ子でもドット区切りでもよい)。ファイルからは :func:`load_params`。"""
        leaves: dict[str, Any] = {}
        origins: dict[str, Origin] = {}
        if data:
            tmp: dict[str, Any] = {}
            _flatten_loose(data, tmp)
            for k, v in tmp.items():
                leaves[k] = v if isinstance(v, _Ref) else _norm_scalar(v, k)
                origins[k] = Origin(name, k)
            _check_layout(leaves)
            _resolve_refs(leaves, origins)
        self._init(leaves, origins, name)

    @classmethod
    def _make(cls, leaves: dict[str, Any], origins: dict[str, Origin], name: str) -> "ParamBundle":
        self = object.__new__(cls)
        self._init(leaves, origins, name)
        return self

    def _init(self, leaves: dict[str, Any], origins: dict[str, Origin], name: str) -> None:
        by_leaf: dict[str, list[str]] = {}
        sections: dict[str, None] = {}
        for k in leaves:
            parts = k.split(".")
            by_leaf.setdefault(parts[-1], []).append(k)
            for i in range(1, len(parts)):
                sections.setdefault(".".join(parts[:i]), None)
        object.__setattr__(self, "_leaves", leaves)
        object.__setattr__(self, "_origins", origins)
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_by_leaf", by_leaf)
        object.__setattr__(self, "_sections", tuple(sections))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("ParamBundle is read-only (use .with_(...) or .merged(...) to get a new bundle)")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("ParamBundle is read-only")

    # -- Mapping ------------------------------------------------------------------------------
    @property
    def name(self) -> str:
        """出どころの名前(ファイル名、コードから作ったなら ``<code>``)。"""
        return self._name

    def __iter__(self) -> Iterator[str]:
        return iter(self._leaves)

    def __len__(self) -> int:
        return len(self._leaves)

    def __contains__(self, key: object) -> bool:
        try:
            self._find(key)           # type: ignore[arg-type]
            return True
        except (KeyError, AmbiguousParam):
            return False

    def _find(self, key: str) -> tuple[str, str]:
        """キー → ("leaf" | "section", 完全なキー)。葉の名前が 1 つだけならその葉。"""
        if not isinstance(key, str):
            raise KeyError(key)
        if key in self._leaves:
            return "leaf", key
        if key in self._sections:
            return "section", key
        hits = self._by_leaf.get(key)
        if hits:
            if len(hits) == 1:
                return "leaf", hits[0]
            raise AmbiguousParam("%r is ambiguous in %s: %s (write the full key)" % (key, self._name, ", ".join(hits)))
        near = difflib.get_close_matches(key, list(self._leaves) + list(self._sections), n=3)
        raise KeyError("%r not in bundle %s%s" % (key, self._name, " (did you mean %s?)" % ", ".join(near) if near else ""))

    def __getitem__(self, key: str) -> Any:
        kind, full = self._find(key)
        if kind == "section":
            return ParamSection(self, full)
        return self._leaves[full]

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(str(e)) from None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ParamBundle):
            return NotImplemented
        return self._leaves == other._leaves

    __hash__ = None  # type: ignore[assignment]

    def __repr__(self) -> str:
        head = ", ".join(list(self._leaves)[:6])
        more = ", ..." if len(self._leaves) > 6 else ""
        return "ParamBundle(%s: %d keys [%s%s])" % (self._name, len(self._leaves), head, more)

    # -- 節・出どころ・書き出し ----------------------------------------------------------------
    def sections(self) -> list[str]:
        """最上位の節の名前。"""
        return list(dict.fromkeys(k.split(".")[0] for k in self._leaves if "." in k))

    def origin(self, key: str) -> Origin:
        """出どころ(ファイル名・キーの経路・YAML なら行・参照なら参照先)。"""
        kind, full = self._find(key)
        if kind != "leaf":
            raise KeyError("%r is a section; ask for a value key" % key)
        return self._origins[full]

    def to_dict(self, *, nested: bool = True) -> dict[str, Any]:
        """素の dict(JSON にそのまま書ける形: 単位つきは ``"550 nm"``、配列は list)。"""
        if not nested:
            return {k: _jsonable(v) for k, v in self._leaves.items()}
        out: dict[str, Any] = {}
        for k, v in self._leaves.items():
            cur = out
            parts = k.split(".")
            for part in parts[:-1]:
                cur = cur.setdefault(part, {})
            cur[parts[-1]] = _jsonable(v)
        return out

    # -- 重ね合わせ・差分 -----------------------------------------------------------------------
    def merged(self, other: "ParamBundle") -> "ParamBundle":
        """基本(self)+ 上書き(other)。上書きしたキーの出どころは other。元は不変。"""
        if not isinstance(other, ParamBundle):
            raise TypeError("merged() takes a ParamBundle, got %s" % type(other).__name__)
        leaves = dict(self._leaves)
        leaves.update(other._leaves)
        origins = dict(self._origins)
        origins.update(other._origins)
        _check_layout(leaves)
        return ParamBundle._make(leaves, origins, "%s+%s" % (self._name, other._name))

    def with_(self, **updates: Any) -> "ParamBundle":
        """値の差し替え(``p.with_(**{"camera.fx": 820})``)。元は不変、出どころは ``<code>``。"""
        add: dict[str, Any] = {}
        _flatten_loose(updates, add)
        leaves = dict(self._leaves)
        origins = dict(self._origins)
        for k, v in add.items():
            leaves[k] = _norm_scalar(v, k) if not isinstance(v, _Ref) else v
            origins[k] = Origin("<code>", k)
        _check_layout(leaves)
        _resolve_refs(leaves, origins)
        return ParamBundle._make(leaves, origins, self._name)

    def diff(self, other: "ParamBundle") -> dict[str, tuple[Any, Any]]:
        """意味として違うキーだけ ``{key: (self の値, other の値)}``。片方に無ければ None。"""
        out: dict[str, tuple[Any, Any]] = {}
        for k in itertools.chain(self._leaves, (k for k in other._leaves if k not in self._leaves)):
            a = self._leaves.get(k)
            b = other._leaves.get(k)
            if k not in self._leaves or k not in other._leaves or not values_equal(a, b):
                out[k] = (a, b)
        return out

    # -- 導出 ---------------------------------------------------------------------------------
    def K(self, section: str | None = None) -> np.ndarray:
        """``fx, fy, cx, cy``(と任意の ``skew``)から 3x3 の内部行列。固定の導出で、式は許さない。"""
        found = _derive_K(self._leaves, section)
        if found is None:
            raise MissingParam("K needs fx, fy, cx, cy in the bundle %s%s" % (
                self._name, " (section %s)" % section if section else ""))
        return found[0]

    # -- op へ ---------------------------------------------------------------------------------
    def for_op(self, op_name: str, *, report: bool = False, strict: bool = False,
               data: Iterable[str] | None = None, fn: Callable[..., Any] | None = None
               ) -> dict[str, Any] | tuple[dict[str, Any], ParamReport]:
        """``op_name`` が受ける引数だけの dict(``op(img, **p.for_op("op"))``)。

        引数名の**完全一致**(``[op_name]`` の節が最優先)→ 同義の綴りの表(:data:`SYNONYM_GROUPS`)→ 固定の導出
        (``K`` を fx, fy, cx, cy から)の順に探す。単位は引数名の接尾辞(``wavelength_um``)が決め、束の
        ``"550 nm"`` を 1 回だけ変換して渡す。

        ``data`` は呼び出し側が渡す引数名(束から探さない)。省略時は台帳の型づけと名前から決める。
        必須引数が作れなければ :class:`MissingParam`(必要な名前・束にある名前・導出の手がかり)、単位違いは
        :class:`UnitMismatch`、型違いは :class:`ParamTypeError`。``strict=True`` で、どの引数にも当たらなかった
        キーがあれば :class:`UnusedParams`。``report=True`` なら ``(kwargs, ParamReport)``。
        """
        func = fn or _find_callable(op_name)
        kwargs, rep = _for_op(self, op_name, func, None if data is None else set(data), strict)
        return (kwargs, rep) if report else kwargs

    def unused(self, ops: Iterable[str]) -> list[str]:
        """``ops`` のどれにも使われないキー(束を複数の op で使うときの確認)。足りない引数は数えず、使われた分だけ見る。"""
        used: set[str] = set()
        for op in ops:
            _, rep = _for_op(self, op, _find_callable(op), None, False, tolerate_missing=True)
            used |= {k for e in rep.entries for k in e.keys}
        return [k for k in self._leaves if k not in used]


def _flatten_loose(data: Mapping[str, Any], out: dict[str, Any], prefix: str = "") -> None:
    """コードから渡された dict(入れ子もドット区切りも可)を葉へ。参照は ``{"$param": key}`` のみ。"""
    for k, v in data.items():
        if not isinstance(k, str) or not k or k != k.strip():
            raise ParamError("invalid key %r" % (k,))
        full = prefix + "." + k if prefix else k
        if isinstance(v, Mapping):
            if len(v) == 1 and "$param" in v:
                tgt = v["$param"]
                if not isinstance(tgt, str) or not tgt:
                    raise ParamError("%s: reference target must be a non-empty string" % full)
                out[full] = _Ref(tgt)
            else:
                _flatten_loose(v, out, full)
        else:
            out[full] = v


class ParamSection(Mapping):
    """束の 1 つの節(``p.camera``)の読み取り専用の見え方。キーは節からの相対。"""

    __slots__ = ("_bundle", "_prefix")

    def __init__(self, bundle: ParamBundle, prefix: str) -> None:
        object.__setattr__(self, "_bundle", bundle)
        object.__setattr__(self, "_prefix", prefix)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("ParamSection is read-only")

    def _keys(self) -> list[str]:
        pre = self._prefix + "."
        return [k[len(pre):] for k in self._bundle._leaves if k.startswith(pre)]

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys())

    def __len__(self) -> int:
        return len(self._keys())

    def __getitem__(self, key: str) -> Any:
        full = self._prefix + "." + key
        b = self._bundle
        if full in b._leaves:
            return b._leaves[full]
        if full in b._sections:
            return ParamSection(b, full)
        raise KeyError("%r not in section %s of %s" % (key, self._prefix, b._name))

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(str(e)) from None

    def origin(self, key: str) -> Origin:
        return self._bundle.origin(self._prefix + "." + key)

    def K(self) -> np.ndarray:
        """この節の ``fx, fy, cx, cy`` から 3x3 の内部行列。"""
        return self._bundle.K(self._prefix)

    def __repr__(self) -> str:
        return "ParamSection(%s.%s: %s)" % (self._bundle._name, self._prefix, ", ".join(self._keys()))


def _derive_K(leaves: Mapping[str, Any], section: str | None = None) -> tuple[np.ndarray, tuple[str, ...]] | None:
    """``fx, fy, cx, cy``(+ 任意の ``skew``)が同じ節にそろっていれば 3x3 の K と使ったキー。"""
    prefixes = []
    for k in leaves:
        if k == "fx" or k.endswith(".fx"):
            pre = k[:-2]
            if section is not None and pre.rstrip(".") != section:
                continue
            if all((pre + n) in leaves for n in ("fy", "cx", "cy")):
                prefixes.append(pre)
    if not prefixes:
        return None
    if len(prefixes) > 1:
        raise AmbiguousParam("K could be built from more than one section (%s); pass section= / use p.<section>.K()"
                             % ", ".join(p.rstrip(".") or "<top>" for p in prefixes))
    pre = prefixes[0]
    names = ["fx", "fy", "cx", "cy"] + (["skew"] if (pre + "skew") in leaves else [])
    vals = {}
    for n in names:
        v = leaves[pre + n]
        if isinstance(v, Quantity):
            if v.unit != "px":
                raise UnitMismatch("%s%s is %s; K takes pixels (write a number or \"... px\")" % (pre, n, v))
            v = v.value
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ParamTypeError("%s%s must be a number (pixels), got %r" % (pre, n, v))
        vals[n] = float(v)
    K = np.array([[vals["fx"], vals.get("skew", 0.0), vals["cx"]], [0.0, vals["fy"], vals["cy"]], [0.0, 0.0, 1.0]])
    return K, tuple(pre + n for n in names)


# ----------------------------------------------------------------------------------------------
# for_op の中身
# ----------------------------------------------------------------------------------------------
def _numeric_param(param: inspect.Parameter) -> bool:
    d = param.default
    if isinstance(d, (int, float)) and not isinstance(d, bool):
        return True
    ann = param.annotation
    return isinstance(ann, str) and ann.replace(" ", "").split("|")[0] in ("float", "int")


def _coerce(value: Any, param: inspect.Parameter, key: str) -> Any:
    """op の既定値・注釈に合わせて型を整える(tuple / ndarray / int)。合わなければ断る。"""
    name, d = param.name, param.default
    if isinstance(value, tuple):
        if name in _ARRAY_ARGS:
            try:
                return np.asarray(value, dtype=float)
            except (TypeError, ValueError) as e:
                raise ParamTypeError("%s: %s expects a numeric array: %s" % (key, name, e)) from e
        if isinstance(d, tuple):
            return tuple(_unq(v) for v in value)
        return [_unq(v) for v in value]
    if isinstance(d, bool):
        if not isinstance(value, bool):
            raise ParamTypeError("%s: %s expects a boolean, got %r" % (key, name, value))
        return value
    if _numeric_param(param) or split_suffix(name)[1] is not None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ParamTypeError("%s: %s expects a number, got %s %r" % (key, name, type(value).__name__, value))
        if isinstance(d, int) and not isinstance(d, bool) and isinstance(value, float):
            if value != int(value):
                raise ParamTypeError("%s: %s expects an integer, got %r" % (key, name, value))
            return int(value)
        return value
    if isinstance(d, str) and not isinstance(value, str):
        raise ParamTypeError("%s: %s expects a string, got %r" % (key, name, value))
    return value


def _unq(v: Any) -> Any:
    """配列の要素の Quantity は値だけにする(単位つきの配列要素は単位を捨てない: 断る)。"""
    if isinstance(v, Quantity):
        raise UnitMismatch("a quantity (%s) inside an array cannot be passed to an op; write plain numbers" % v)
    if isinstance(v, tuple):
        return [_unq(x) for x in v]
    return v


def _to_arg_unit(value: Any, key: str, param: inspect.Parameter, key_unit: str | None) -> tuple[Any, bool, str]:
    """束の値を引数の単位へ。(渡す値, 変換したか, 注記)。"""
    name = param.name
    _, arg_unit = split_suffix(name)
    if isinstance(value, Quantity):
        if arg_unit is None:
            imp = _IMPLICIT_UNIT.get(name)
            if imp is not None and value.unit == imp:
                return value.value, False, ""
            raise UnitMismatch(
                "%s = %s has a unit, but %s takes a bare number (its name carries no unit); "
                "write a plain number in the file, or use an op argument with a unit suffix" % (key, value, name))
        if value.dimension != UNITS[arg_unit][0]:
            raise UnitMismatch("%s = %s is a %s but %s needs a %s (%s)" % (
                key, value, value.dimension, name, UNITS[arg_unit][0], arg_unit))
        out = value.to(arg_unit)
        return out, value.unit != arg_unit, ("" if value.unit == arg_unit else "%s -> %s" % (value.unit, arg_unit))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if arg_unit is None:
            return value, False, ""
        if key_unit is None:
            raise UnitMismatch(
                "%s = %r has no unit but %s is in %s; write \"%r %s\" (or name the key ...%s%s)"
                % (key, value, name, arg_unit, value, arg_unit, "_", arg_unit))
        if key_unit == arg_unit:
            return value, False, ""
        if UNITS[key_unit][0] != UNITS[arg_unit][0]:
            raise UnitMismatch("%s is in %s but %s needs %s" % (key, key_unit, name, arg_unit))
        return convert_number(_dec(value), key_unit, arg_unit), True, "%s -> %s" % (key_unit, arg_unit)
    return value, False, ""


def _candidates(bundle: ParamBundle, op_name: str, argname: str) -> tuple[str, list[str]]:
    """引数 1 つに当たる束のキー(how, keys)。完全一致 → 同義の表。見つからなければ ("", [])。"""
    leaves = bundle._leaves
    sec = op_name + "." + argname
    if sec in leaves:
        return "section", [sec]
    if argname in leaves:
        return "exact", [argname]
    hits = bundle._by_leaf.get(argname, [])
    if len(hits) == 1:
        return "exact", hits
    if len(hits) > 1:
        raise AmbiguousParam("%s: argument %r matches more than one key (%s); qualify with a [%s] section or "
                             "remove the duplicates" % (op_name, argname, ", ".join(hits), op_name))
    stem, _unit = split_suffix(argname)
    group = _STEM_GROUP.get(stem)
    if group:
        found: list[str] = []
        for leaf, fulls in bundle._by_leaf.items():
            lstem, _lu = split_suffix(leaf)
            if lstem in group and leaf != argname:
                found.extend(fulls)
        if found:
            return "synonym", found
    return "", []


def _for_op(bundle: ParamBundle, op_name: str, func: Callable[..., Any], data: set[str] | None, strict: bool,
            tolerate_missing: bool = False) -> tuple[dict[str, Any], ParamReport]:
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError) as e:
        raise ParamError("cannot inspect the signature of %s: %s" % (op_name, e)) from e
    data_names = _auto_data_names(op_name, sig) if data is None else data
    kwargs: dict[str, Any] = {}
    rep = ParamReport(op_name, bundle._name)
    consumed: set[str] = set()
    missing: list[str] = []
    needed: list[str] = []
    for param in sig.parameters.values():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD, param.POSITIONAL_ONLY):
            continue
        name = param.name
        if name in data_names:
            continue
        required = param.default is param.empty
        if required:
            needed.append(name)
        how, keys = _candidates(bundle, op_name, name)
        if not keys and name == "K":
            d = _derive_K(bundle._leaves)
            if d is not None:
                K, used = d
                kwargs[name] = K
                consumed.update(used)
                rep.entries.append(ReportEntry(name, used, "derived", "fx,fy,cx,cy", K, False, "built from fx, fy, cx, cy"))
                continue
        if not keys:
            if required:
                missing.append(name)
            continue
        # 同義の綴りが複数のキーに当たったとき: 意味が同じなら 1 つに、違えば断る。
        vals = [bundle._leaves[k] for k in keys]
        if len(keys) > 1:
            if not all(values_equal(vals[0], v) for v in vals[1:]):
                raise AmbiguousParam("%s: argument %r could take %s with different values; keep one" % (
                    op_name, name, ", ".join("%s = %s" % (k, _jsonable(bundle._leaves[k])) for k in keys)))
        key = keys[0]
        value = vals[0]
        key_unit = split_suffix(key.rsplit(".", 1)[-1])[1]
        if isinstance(value, tuple):
            out, conv, note = value, False, ""
        else:
            out, conv, note = _to_arg_unit(value, key, param, key_unit)
        out = _coerce(out, param, key)
        kwargs[name] = out
        consumed.update(keys)
        rep.entries.append(ReportEntry(name, tuple(keys), how, str(value) if isinstance(value, Quantity) else repr(_jsonable(value)),
                                       out, conv, note))
    rep.unused = [k for k in bundle._leaves if k not in consumed]
    if missing and not tolerate_missing:
        raise MissingParam(_missing_message(bundle, op_name, needed, missing))
    if strict and rep.unused:
        raise UnusedParams("%s: %d key(s) in bundle %s are not used by this op: %s"
                           % (op_name, len(rep.unused), bundle._name, ", ".join(rep.unused)))
    return kwargs, rep


def _missing_message(bundle: ParamBundle, op_name: str, needed: list[str], missing: list[str]) -> str:
    have = list(bundle._leaves)
    hints = []
    for m in missing:
        if m == "K":
            hints.append("K can be built from fx, fy, cx, cy with p.K() (put all four in one section)")
            continue
        close = difflib.get_close_matches(m, have + [h.rsplit(".", 1)[-1] for h in have], n=2)
        stem, unit = split_suffix(m)
        grp = _STEM_GROUP.get(stem)
        if grp:
            hints.append("%s may be written as %s (a bare number needs the unit in the name, or write \"value %s\")" % (
                m, " / ".join(g + ("_" + unit if unit else "") for g in grp if g != stem),
                unit or "unit"))
        elif close:
            hints.append("%s: close to %s" % (m, ", ".join(close)))
    return "%s needs %s; bundle %s has [%s] -- missing: %s%s" % (
        op_name, ", ".join(needed), bundle._name, ", ".join(have),
        ", ".join(missing), ("; hint: " + "; ".join(hints)) if hints else "")


# ----------------------------------------------------------------------------------------------
# 比べる(複数の束を並べる)
# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class CompareRow:
    """1 キーの行。``values`` は束の順(無ければ None)。"""

    key: str
    values: tuple[Any, ...]
    status: str                 #: "same"(全部在って同じ)/ "differ"(違う)/ "partial"(一部の束に無い)
    notation_differs: bool = False   #: 同じ値だが書き方が違う("0.55 um" と "550 nm")


@dataclass(frozen=True)
class ParamComparison:
    """束を列、キーを行にした比較表。Studio の段組表示の土台。"""

    names: tuple[str, ...]
    rows: tuple[CompareRow, ...]

    def __iter__(self) -> Iterator[CompareRow]:
        return iter(self.rows)

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, key: str) -> CompareRow:
        for r in self.rows:
            if r.key == key:
                return r
        raise KeyError(key)

    def counts(self) -> dict[str, int]:
        c = {"same": 0, "differ": 0, "partial": 0}
        for r in self.rows:
            c[r.status] += 1
        return c

    def table(self) -> list[list[str]]:
        """文字の表(1 行目が見出し)。段組表示・テキスト出力の共通の材料。"""
        mark = {"same": "=", "differ": "!=", "partial": "?"}
        out = [["key", *self.names, "status"]]
        for r in self.rows:
            cells = ["-" if v is None else str(_jsonable(v)) for v in r.values]
            out.append([r.key, *cells, mark[r.status] + ("~" if r.notation_differs else "")])
        return out

    def text(self) -> str:
        t = self.table()
        w = [max(len(row[i]) for row in t) for i in range(len(t[0]))]
        return "\n".join("  ".join(c.ljust(w[i]) for i, c in enumerate(row)).rstrip() for row in t)

    __str__ = text


def params_compare(bundles: Sequence[ParamBundle], names: Sequence[str] | None = None) -> ParamComparison:
    """複数の束を並べて比べる(キー = 行、束 = 列)。

    印: ``same`` = 全部の束に在って意味として同じ(``"0.55 um"`` と ``"550 nm"`` は同じ。書き方が違えば
    ``notation_differs``)、``differ`` = 違う、``partial`` = 一部の束に無い。
    """
    bs = list(bundles)
    if len(bs) < 2:
        raise ParamError("params_compare needs at least 2 bundles")
    if not all(isinstance(b, ParamBundle) for b in bs):
        raise TypeError("params_compare takes ParamBundle objects")
    if names is None:
        raw = [b.name for b in bs]
        names_out = [n if raw.count(n) == 1 else "%s#%d" % (n, i + 1) for i, n in enumerate(raw)]
    else:
        if len(names) != len(bs):
            raise ParamError("names must match the number of bundles")
        names_out = list(names)
    keys: dict[str, None] = {}
    for b in bs:
        for k in b._leaves:
            keys.setdefault(k, None)
    rows: list[CompareRow] = []
    for k in keys:
        vals = tuple(b._leaves.get(k) for b in bs)
        present = [v for v in vals if v is not None]
        if len(present) < len(bs):
            status, nd = "partial", False
        elif all(values_equal(present[0], v) for v in present[1:]):
            status = "same"
            nd = any(isinstance(v, Quantity) for v in present) and len({str(v) for v in present}) > 1
        else:
            status, nd = "differ", False
        rows.append(CompareRow(k, vals, status, nd))
    return ParamComparison(tuple(names_out), tuple(rows))


# ----------------------------------------------------------------------------------------------
# 走査
# ----------------------------------------------------------------------------------------------
class ParamGrid(Sequence):
    """束の列(直積または zip)。要素は :class:`ParamBundle`。遅延で作る(件数は先に分かる)。"""

    def __init__(self, base: ParamBundle, axes: Mapping[str, Sequence[Any]], mode: str, size: int) -> None:
        self.base = base
        self.axes: dict[str, tuple[Any, ...]] = {k: tuple(v) for k, v in axes.items()}
        self.mode = mode
        self._size = size

    def __len__(self) -> int:
        return self._size

    def point(self, i: int) -> dict[str, Any]:
        """i 番目の上書き(``{key: 値}``)。"""
        if not -self._size <= i < self._size:
            raise IndexError(i)
        i %= self._size
        if self.mode == "zip":
            return {k: v[i] for k, v in self.axes.items()}
        out: dict[str, Any] = {}
        for k, v in reversed(list(self.axes.items())):
            i, r = divmod(i, len(v))
            out[k] = v[r]
        return dict(reversed(list(out.items())))

    def __getitem__(self, i: Any) -> Any:
        if isinstance(i, slice):
            return [self[j] for j in range(*i.indices(self._size))]
        return self.base.with_(**self.point(i))

    def points(self) -> list[dict[str, Any]]:
        return [self.point(i) for i in range(self._size)]

    def __repr__(self) -> str:
        return "ParamGrid(%s, %d points over %s)" % (self.mode, self._size, ", ".join(self.axes))


def _check_axes(base: ParamBundle, axes: Mapping[str, Any]) -> dict[str, tuple[Any, ...]]:
    if not axes:
        raise ParamError("give at least one axis, e.g. param_grid(p, **{\"gaussian.sigma\": [0.5, 1, 2]})")
    out: dict[str, tuple[Any, ...]] = {}
    for k, v in axes.items():
        if isinstance(v, (str, bytes, Mapping)) or not isinstance(v, Iterable):
            raise ParamError("axis %r must be a list of values, got %s" % (k, type(v).__name__))
        vals = tuple(v)
        if not vals:
            raise ParamError("axis %r is empty" % k)
        for x in vals:
            _norm_scalar(x, k)          # 値の検査(非有限・型)を走査の前にする
        out[k] = vals
    return out


def param_grid(base: ParamBundle, *, max_points: int = DEFAULT_MAX_GRID_POINTS, **axes: Sequence[Any]) -> ParamGrid:
    """直積の走査: ``param_grid(p, **{"gaussian.sigma": [0.5, 1, 2], "otsu.thr": [0.3, 0.5]})`` → 6 束。

    件数が ``max_points`` を超えるなら、件数と見積もりを先に出して :class:`GridTooLarge` で断る。
    """
    ax = _check_axes(base, axes)
    n = 1
    for v in ax.values():
        n *= len(v)
    if n > max_points:
        est_bytes = n * max(len(base), 1) * 200
        raise GridTooLarge(
            "grid has %s points (%s); limit is %s. Estimate: ~%.1f MB if every bundle were kept, and %s runs of the op. "
            "Narrow an axis or pass max_points=" % (
                "{:,}".format(n), " x ".join(str(len(v)) for v in ax.values()), "{:,}".format(max_points),
                est_bytes / 1e6, "{:,}".format(n)))
    return ParamGrid(base, ax, "product", n)


def param_zip(base: ParamBundle, *, max_points: int = DEFAULT_MAX_GRID_POINTS, **axes: Sequence[Any]) -> ParamGrid:
    """同じ長さの軸を並べて 1 つずつ組にする(直積でなく zip)。長さが違えば断る。"""
    ax = _check_axes(base, axes)
    lens = {k: len(v) for k, v in ax.items()}
    if len(set(lens.values())) != 1:
        raise ParamError("param_zip needs axes of equal length, got %s" % lens)
    n = next(iter(lens.values()))
    if n > max_points:
        raise GridTooLarge("zip has %s points; limit is %s" % ("{:,}".format(n), "{:,}".format(max_points)))
    return ParamGrid(base, ax, "zip", n)


def sweep(op: str | Callable[[ParamBundle], Any], x: Any, grid: ParamGrid | Iterable[ParamBundle], *,
          metric: Callable[[Any], Any] | None = None, on_error: str = "raise", **fixed: Any) -> list[dict[str, Any]]:
    """走査を実行して行(dict)の列を返す。各行 = ``index`` + 上書きしたキーと値 + ``value``(metric の値)。

    ``op`` が名前なら ``run_params(op, x, params=束, **fixed)``(``x`` が None なら位置引数なし。データを取らない op 用)、callable なら ``op(束)`` を呼ぶ(``x`` は無視)。
    ``on_error="record"`` なら失敗を行の ``error`` に残して続ける(既定は raise)。
    パイプライン全体の実行(段の列)はここでは扱わない(``op`` に段を回す関数を渡す)。
    """
    if on_error not in ("raise", "record"):
        raise ParamError("on_error must be 'raise' or 'record'")
    rows: list[dict[str, Any]] = []
    for i, b in enumerate(grid):
        row: dict[str, Any] = {"index": i}
        if isinstance(grid, ParamGrid):
            row.update({k: _jsonable(v) for k, v in grid.point(i).items()})
        try:
            out = run_params(op, *(() if x is None else (x,)), params=b, warn_unused=False, **fixed) if isinstance(op, str) else op(b)
            row["value"] = metric(out) if metric is not None else None
            row["error"] = None
        except Exception as e:                               # noqa: BLE001 - on_error で扱いを選べる
            if on_error == "raise":
                raise
            row["value"] = None
            row["error"] = "%s: %s" % (type(e).__name__, e)
        rows.append(row)
    return rows


# ----------------------------------------------------------------------------------------------
# 糖衣 run_params / 書く側
# ----------------------------------------------------------------------------------------------
def run_params(op_name: str, *args: Any, params: ParamBundle | Mapping[str, Any] | str | os.PathLike | None = None,
        strict: bool = False, warn_unused: bool = True, **overrides: Any) -> Any:
    """``op_name`` を束から引数を取って実行する糖衣。``fs.apply`` の契約は変えない別の入口。

        fs.run_params("undistort_image", img, params=p)
        # = fs.undistort_image(img, **p.for_op("undistort_image"))

    位置引数はそのまま op に渡る(データ)。キーワードの ``overrides`` は束より優先。どの引数にも当たらなかった
    キーは実行後に :class:`ParamWarning` で一覧にし、``strict=True`` なら実行前に断る。進化する 2-D op
    (``fs.apply`` の a/b つまみ)は束の ``[op].a`` / ``[op].b`` を使う。
    """
    if params is None:
        bundle = ParamBundle()
    elif isinstance(params, ParamBundle):
        bundle = params
    elif isinstance(params, Mapping):
        bundle = ParamBundle(params)
    else:
        bundle = load_params(params)
    func = _find_callable(op_name)
    try:
        sig = inspect.signature(func)
        pos = [p.name for p in sig.parameters.values() if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    except (TypeError, ValueError):
        pos = []
    data = set(pos[:len(args)]) | set(overrides)
    kwargs, rep = _for_op(bundle, op_name, func, data, strict)
    kwargs.update(overrides)
    if rep.unused and warn_unused and not strict:
        warnings.warn("run_params(%s): %d key(s) of bundle %s were not used by this op: %s (strict=True refuses them)"
                      % (op_name, len(rep.unused), bundle.name, ", ".join(rep.unused)), ParamWarning, stacklevel=2)
    return func(*args, **kwargs)


def save_params(bundle: ParamBundle, path: str | os.PathLike) -> str:
    """束を JSON で書く(原子的: 同じフォルダの一時ファイル → ``os.replace``)。書いたパスを返す。

    JSON だけ。``allow_nan=False``(非有限は書かない)。単位つきは ``"550 nm"`` の文字列のまま、参照と
    ``include`` は展開済みの値で書く(出どころの情報は書かない)。TOML / YAML への書き出しや、コメントを
    保つ差分書き込みはしない。
    """
    p = os.fspath(path)
    if os.path.splitext(p)[1].lower() != ".json":
        raise ParamError("save_params writes JSON only (got %r); TOML / YAML are read-only here" % p)
    if not isinstance(bundle, ParamBundle):
        raise TypeError("save_params takes a ParamBundle")
    text = json.dumps(bundle.to_dict(), allow_nan=False, ensure_ascii=False, indent=2) + "\n"
    folder = os.path.dirname(os.path.abspath(p))
    if not os.path.isdir(folder):
        raise ParamError("folder does not exist: %s" % folder)
    fd, tmp = tempfile.mkstemp(prefix=".params-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return p
