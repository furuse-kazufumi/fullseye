# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""定義ファイル(JSON)の読み書きの、**種類に依らない小さな層**(``fullseye.read_def`` / ``write_def``)。

パイプライン・(将来の)カメラの設定・光学系のパラメータ・フィジカル AI の場面など、Fullseye が JSON で
持つ定義に共通する部分だけをここに置く。種類ごとの中身の検査は、種類の表(:data:`KINDS`)に登録した
読み手・書き手の関数が持つ。設計は ``docs/STUDIO_PROGRAM_LANGUAGE.md`` の「定義ファイル」の節と、
全数調査 ``DEFS_IO_SURVEY.md`` §5.2〜5.3(封筒の鍵 ``fullseye_kind``、入口 ``read_def`` / ``write_def``)。

型つき値の封筒(``fullseye_sort``、``fullseye.jsonio``)は**作り替えない**。こちらは「定義(kind)」の封筒で、
jsonio と同じ流儀(自己記述・fail-closed)で並べる兄弟。

* **印**: ``"fullseye_kind"``(例 ``"pipeline"``)・``"version"``(整数)・``"created_by"``(``"fullseye <版>"``、
  ログ用で判定には使わない)。種類の中身は、既存の形があればその場所のまま(パイプラインは ``stages`` が
  トップレベル。Studio の保存形は鍵を足すだけ)。
* **印の無い今までのファイル**: 種類ごとの嗅ぎ分け(``legacy``)で **版 0** と読み、今の版へ移行する。
  パイプラインは ``fullseye_pipeline: 1`` か ``stages`` だけのファイル。``fullseye_pipeline`` が整数 1 で
  なければ断る。
* **断る**(fail-closed、ファイル名と理由つき): 未知の ``fullseye_kind``、その種類の今の版より新しい
  ``version``、整数でない ``version``、移行の段が欠けている版、印も嗅ぎ分けも当たらない辞書
  (種類を推測しない)、別の族の印(``fullseye_graph`` / ``fullseye_sort``)。
* **JSON に入らない値**: NaN / inf は書かない(どの鍵かを書いて断る)。numpy の数は Python の数、
  タプルは列、小さい配列は列。大きな配列は別ファイル(``{"$array": "x.npy", "sha256": …}``)にし、
  :func:`resolve_sidecar` が「定義ファイルの場所の内側か」と「SHA-256 が合うか」を確かめる。
* **原子的な書き込み**: 同じ場所に一時ファイルを書いてから ``os.replace``。途中で落ちても元のファイルは残る。
* **データだけ**: ``json.load`` で読む。pickle も eval も使わず、読み手は表に登録された関数だけ。
"""
from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

KIND_KEY = "fullseye_kind"
VERSION_KEY = "version"
CREATED_BY_KEY = "created_by"
MARKER_KEYS = (KIND_KEY, VERSION_KEY, CREATED_BY_KEY)

#: 配列をそのまま JSON の列にしてよい要素数の上限。これより大きい配列は別ファイルにする。
MAX_INLINE_ARRAY = 4096

#: 別の族の印(この層の読み手ではない物)。見つけたら行き先を言って断る。
_OTHER_FAMILIES = {"fullseye_graph": "a FullseyeGraph file (fullseye.FullseyeGraph)",
                   "fullseye_sort": "a typed value (fullseye.load_json)"}


class DefinitionError(ValueError):
    """定義ファイルが読めない・書けない。メッセージは「どのファイルの、どこが、なぜ」。"""


@dataclass(frozen=True)
class DefKind:
    """1 つの種類の登録。関数は ``"module:function"`` の文字列で持ち、使うときに import する
    (層が種類のモジュールに依存しない = 循環しない・軽い)。"""
    kind: str
    version: int
    reader: str                       # (d: dict, where: str) -> object。d は今の版へ移行済み
    writer: str                       # (obj) -> dict(印は層が付ける)
    legacy: str | None = None         # (d) -> 版(int) か None: 印の無い辞書をこの種類の何版と見なすか
    migrations: dict = field(default_factory=dict)   # {from_version: "module:function"}(d -> 次の版の d)
    python_type: str | None = None    # write_def(obj) の振り分けに使う "module:Class"


#: 種類の表。後から ``register_kind(DefKind("camera", 1, ...))`` で足す。
KINDS: dict = {}


def register_kind(k: DefKind) -> None:
    """種類を表に足す(同じ kind を別の中身で二重登録するのは誤り)。"""
    if k.kind in KINDS and KINDS[k.kind] != k:
        raise ValueError("definition kind %r is already registered" % k.kind)
    KINDS[k.kind] = k


def _fn(spec: str) -> Callable:
    mod, _, name = spec.partition(":")
    return getattr(importlib.import_module(mod), name)


def created_by() -> str:
    """``"fullseye <版>"``(版が分からなければ ``"fullseye unknown"``)。"""
    try:
        from importlib.metadata import version
        return "fullseye %s" % version("fullseye")
    except Exception:                                # noqa: BLE001 -- 配布されていない作業木
        return "fullseye unknown"


def stamp(d: dict, kind: str) -> dict:
    """*d* に印(fullseye_kind / version / created_by)を付けた新しい辞書(印を先頭に置く)。"""
    k = KINDS[kind]
    out = {KIND_KEY: kind, VERSION_KEY: k.version, CREATED_BY_KEY: created_by()}
    for key, v in d.items():
        if key not in out:
            out[key] = v
    return out


def check_marker(d, where: str, expect_kind: str | None = None) -> tuple:
    """印を検査し、今の版へ移行した ``(kind, d)`` を返す。読めなければ :class:`DefinitionError`。

    版の検査の正本はこの関数 1 本(パイプラインの読み手 ``engine.pipeline_from_dict`` もここを通る)。"""
    if not isinstance(d, dict):
        raise DefinitionError("%s: not a definition file (expected a JSON object, got %s)"
                              % (where, type(d).__name__))
    kind = d.get(KIND_KEY)
    if kind is None:
        for key, what in _OTHER_FAMILIES.items():
            if key in d:
                raise DefinitionError("%s: this is %s, not a definition file%s"
                                      % (where, what, " of kind %r" % expect_kind if expect_kind else ""))
        hits = []
        for k in KINDS.values():
            if k.legacy is None or (expect_kind is not None and k.kind != expect_kind):
                continue
            try:
                v = _fn(k.legacy)(d)
            except DefinitionError as e:
                raise DefinitionError("%s: %s" % (where, e)) from None
            if v is not None:
                hits.append((k, v))
        if len(hits) != 1:
            raise DefinitionError("%s: no '%s' marker and the content is not recognisable as %s"
                                  % (where, KIND_KEY, repr(expect_kind) if expect_kind
                                     else "any known kind (%s)" % ", ".join(sorted(KINDS))))
        k, ver = hits[0]
        kind = k.kind
    else:
        if not isinstance(kind, str) or kind not in KINDS:
            raise DefinitionError("%s: unknown definition kind %r (this Fullseye reads: %s)"
                                  % (where, kind, ", ".join(sorted(KINDS))))
        ver = d.get(VERSION_KEY)
        if isinstance(ver, bool) or not isinstance(ver, int):
            raise DefinitionError("%s: 'version' must be an integer, got %r" % (where, ver))
    if expect_kind is not None and kind != expect_kind:
        raise DefinitionError("%s: this is a %r file, not %r" % (where, kind, expect_kind))
    k = KINDS[kind]
    if ver > k.version:
        raise DefinitionError("%s: %s version %d was written by a newer Fullseye (this one reads up to %d) "
                              "— update Fullseye to open it" % (where, kind, ver, k.version))
    if ver < 0:
        raise DefinitionError("%s: version %d is not valid" % (where, ver))
    d = dict(d)
    while ver < k.version:
        step = k.migrations.get(ver)
        if step is None:
            raise DefinitionError("%s: no migration from %s version %d" % (where, kind, ver))
        try:
            d = _fn(step)(d)
        except DefinitionError as e:
            raise DefinitionError("%s: %s" % (where, e)) from None
        ver += 1
    return kind, d


def to_jsonable(v, where: str = "$") -> Any:
    """JSON に書ける形へ: numpy の数 → Python の数、タプル → 列、小さい配列 → 列。
    NaN / inf・大きい配列・書けない型は :class:`DefinitionError`(*where* = 鍵の道筋)。"""
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        f = float(v)
        if not math.isfinite(f):
            raise DefinitionError("%s: %r cannot be written to JSON (NaN / inf are refused)" % (where, f))
        return f
    if isinstance(v, (str, type(None))):
        return v
    if isinstance(v, np.ndarray):
        if v.size > MAX_INLINE_ARRAY:
            raise DefinitionError("%s: array of %d elements is too large to inline (limit %d) — "
                                  "save it next to the file and reference it as {\"$array\": \"name.npy\", "
                                  "\"sha256\": …}" % (where, v.size, MAX_INLINE_ARRAY))
        return to_jsonable(v.tolist(), where)
    if isinstance(v, (list, tuple)):
        return [to_jsonable(x, "%s[%d]" % (where, i)) for i, x in enumerate(v)]
    if isinstance(v, dict):
        out = {}
        for k, x in v.items():
            if not isinstance(k, str):
                raise DefinitionError("%s: keys must be text, got %r" % (where, k))
            out[k] = to_jsonable(x, "%s.%s" % (where, k))
        return out
    raise DefinitionError("%s: a %s cannot be written to a definition file" % (where, type(v).__name__))


def write_json_atomic(path: str, d: dict) -> None:
    """*d* を JSON で原子的に書く(同じ場所の一時ファイル → ``os.replace``)。"""
    path = os.fspath(path)
    body = json.dumps(to_jsonable(d), indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_json(path: str) -> dict:
    """JSON を読む(データだけ)。壊れていれば行と列つきの :class:`DefinitionError`。"""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as e:
        raise DefinitionError("%s: not valid JSON (line %d, column %d: %s)" % (path, e.lineno, e.colno, e.msg)) from None
    except UnicodeDecodeError as e:
        raise DefinitionError("%s: not UTF-8 text (%s)" % (path, e.reason)) from None


def find_file(name: str, search_dirs) -> str:
    """相対の *name* を *search_dirs* の順に探す。見つからなければ探した場所を全部書いた FileNotFoundError。"""
    name = os.fspath(name)
    if os.path.isabs(name):
        cands = [name]
    else:
        cands = [os.path.join(os.fspath(d), name) for d in (search_dirs or []) if d]
    for c in cands:
        if os.path.isfile(c):
            return c
    raise FileNotFoundError("%r not found; looked in: %s" % (name, "; ".join(cands) or "(nowhere)"))


def resolve_sidecar(ref, base_dir: str, where: str = "$") -> np.ndarray:
    """``{"$array": "x.npy", "sha256": "…"}`` を読む。定義ファイルの場所の内側にあること・SHA-256 が
    合うことを確かめ(合わなければ DefinitionError)、``np.load(allow_pickle=False)`` で読む。"""
    if not (isinstance(ref, dict) and isinstance(ref.get("$array"), str) and isinstance(ref.get("sha256"), str)):
        raise DefinitionError("%s: an array reference needs {\"$array\": name, \"sha256\": hex}" % where)
    base = os.path.realpath(base_dir)
    p = os.path.realpath(os.path.join(base, ref["$array"]))
    if os.path.isabs(ref["$array"]) or os.path.commonpath([base, p]) != base:
        raise DefinitionError("%s: array reference %r points outside the definition's folder" % (where, ref["$array"]))
    if not os.path.isfile(p):
        raise DefinitionError("%s: array file %r is missing" % (where, ref["$array"]))
    with open(p, "rb") as fh:
        h = hashlib.sha256(fh.read()).hexdigest()
    if h != ref["sha256"].lower():
        raise DefinitionError("%s: array file %r does not match its sha256 (changed after the definition was saved)"
                              % (where, ref["$array"]))
    return np.load(p, allow_pickle=False)


def read_def(path: str, kind: str | None = None, search_dirs=None):
    """印を見て種類ごとの読み手へ振り分ける(``fullseye.read_def``)。*kind* を渡すとその種類だけを受ける。"""
    p = find_file(path, search_dirs if search_dirs is not None else [os.getcwd()])
    d = read_json(p)
    k, d = check_marker(d, p, kind)
    return _fn(KINDS[k].reader)(d, p)


def write_def(obj, path: str, kind: str | None = None) -> str:
    """種類ごとの書き手で辞書にし、印を付けて原子的に書く(``fullseye.write_def``)。書いた kind を返す。"""
    if kind is None:
        for k in KINDS.values():
            if k.python_type and isinstance(obj, _fn(k.python_type)):
                kind = k.kind
                break
        else:
            raise DefinitionError("write_def: no definition kind for a %s (kinds: %s)"
                                  % (type(obj).__name__, ", ".join(sorted(KINDS))))
    if kind not in KINDS:
        raise DefinitionError("write_def: unknown definition kind %r" % (kind,))
    d = _fn(KINDS[kind].writer)(obj)
    write_json_atomic(path, stamp(d, kind))
    return kind


# --------------------------------------------------------------------------- #
# 登録: パイプライン(中身の検査は engine.py)                                    #
# --------------------------------------------------------------------------- #
register_kind(DefKind(
    kind="pipeline", version=1,
    reader="engine:_pipeline_reader", writer="engine:_pipeline_writer",
    legacy="engine:_pipeline_legacy_version",
    migrations={0: "engine:_pipeline_v0_to_v1"},
    python_type="engine:FullseyeEngine",
))
