# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_pyedit_complete — Python の入力補完・シグネチャ・ホバー(Qt なし)。

供給元(Protocol)
    ``CompletionSource.complete(text, line, col) -> list[Completion]``
    ``SignatureSource.signature(text, line, col) -> Signature | None``
    ``HoverSource.hover(text, line, col) -> Hover | None``
    ``line`` と ``col`` は**どちらも 0 始まり**(Qt の ``blockNumber()`` と ``positionInBlock()`` と同じ)。
    jedi は行が 1 始まりなので、``JediProvider`` の中でだけ ``+1`` する。別の供給元(``studio_program.complete``)を
    繋ぐときは行の基準を確かめて、``LineBase(source, base=1)`` で包む。

既定の供給元
    * ``FallbackProvider``: jedi が無くても動く。prelude の名前・op の一覧(``OpCatalog``)・組み込み・予約語・
      スニペット・本文の中の名前・import の補完・属性(``np.`` ``fs.`` ``fs.ledger.`` と、実行後の名前空間の値)・
      キーワード引数・文字列の中のファイル名。
    * ``JediProvider``: jedi(MIT、任意の依存)が入っていれば使う。``namespace`` があれば ``jedi.Interpreter`` で
      実行後の値を見て補完する。
    * ``default_provider()``: 上の 2 つを重ねる(op・prelude・スニペット・引数名は自前、一般の Python は jedi)。

安全
    * 補完のために利用者のコードは実行しない。import は ``sys.modules`` に既にある物だけを見る(未 import の
      モジュールを勝手に import しない)。属性は ``inspect.getattr_static`` と ``dir`` で見て、プロパティを呼ばない。
"""
from __future__ import annotations

import ast
import builtins
import inspect
import keyword
import os
import re
import sys
from dataclasses import dataclass, field, replace
from typing import Callable, Iterable, Mapping, Protocol, Sequence, runtime_checkable

import studio_pyedit_syntax as syn

#: 補完の種類(仕様の 7 種 + class / attribute / file)。
KINDS = ("op", "variable", "function", "class", "module", "keyword", "param", "snippet", "attribute", "file")
#: 候補の窓で種類を示す 1 文字の印。
KIND_MARK = {"op": "O", "variable": "v", "function": "f", "class": "C", "module": "M", "keyword": "k",
             "param": "p", "snippet": "S", "attribute": "a", "file": "F"}


@dataclass(frozen=True)
class Completion:
    """補完の 1 候補。"""
    name: str
    kind: str
    detail: str = ""                 # 1 行の説明(右に出す)
    insert: str = ""                 # 挿入する文字列(空なら name)
    score: float = 0.0               # 並び順の点(高いほど上)。供給元の基準の点で、ランクが足し引きする
    doc: str = ""                    # 選んだとき横に出す詳しい説明(docstring の先頭など)
    replace_len: int | None = None   # カーソルの前の何文字を置き換えるか(None = 打ちかけの識別子)
    cursor_offset: int | None = None  # 挿入後のカーソル位置(insert の先頭から。None = 末尾)
    doc_loader: Callable[[], str] | None = field(default=None, compare=False, repr=False)

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError("補完の kind は %s のどれか(来たのは %r)" % ("/".join(KINDS), self.kind))

    @property
    def text(self) -> str:
        return self.insert or self.name

    def full_doc(self) -> str:
        """詳しい説明(遅い取得は ``doc_loader`` に任せてある)。取得に失敗したら空。"""
        if self.doc:
            return self.doc
        if self.doc_loader is not None:
            try:
                return self.doc_loader() or ""
            except Exception:                                      # noqa: BLE001
                return ""
        return ""


@dataclass(frozen=True)
class ParamInfo:
    """シグネチャの 1 引数。"""
    name: str
    text: str                       # 表示の形 例 ``sigma=1.0`` / ``a``
    doc: str = ""                   # 引数の意味(op ならつまみの役割・範囲・単位)
    kind: str = "positional"        # positional / keyword / var_positional / var_keyword


@dataclass(frozen=True)
class Signature:
    name: str
    params: tuple
    summary: str = ""
    returns: str = ""

    def segments(self, active: int | None) -> list:
        """``[(文字列, 太字か)]``: ``name(`` ``p1`` ``, `` ``p2`` ... ``)``。今の引数を太字に。"""
        segs = [(self.name + "(", False)]
        for i, p in enumerate(self.params):
            if i:
                segs.append((", ", False))
            segs.append((p.text, active is not None and i == active))
        segs.append((")", False))
        if self.returns:
            segs.append((" -> " + self.returns, False))
        return segs

    def active_param(self, n_positional: int, kw: str | None, used=()) -> int | None:
        """今打っている引数の番号(キーワード引数なら名前で、位置なら数で)。位置の引数を使い切ったら、
        まだ渡していない最初のキーワード引数(op の a / b)を指す。"""
        names = [p.name for p in self.params]
        if kw is not None and kw in names:
            return names.index(kw)
        if kw is not None:
            for i, p in enumerate(self.params):
                if p.kind == "var_keyword":
                    return i
        pos_idx = [i for i, p in enumerate(self.params) if p.kind in ("positional", "var_positional")]
        if not pos_idx:
            for i, p in enumerate(self.params):
                if p.kind == "keyword" and p.name not in used:
                    return i
            return None
        if n_positional < len(pos_idx):
            return pos_idx[n_positional]
        last = pos_idx[-1]
        if self.params[last].kind == "var_positional":
            return last
        for i, p in enumerate(self.params):
            if p.kind == "keyword" and p.name not in used:
                return i
        return None


@dataclass(frozen=True)
class Hover:
    title: str
    body: str = ""


@runtime_checkable
class CompletionSource(Protocol):
    def complete(self, text: str, line: int, col: int) -> list: ...


@runtime_checkable
class SignatureSource(Protocol):
    def signature(self, text: str, line: int, col: int): ...


@runtime_checkable
class HoverSource(Protocol):
    def hover(self, text: str, line: int, col: int): ...


@runtime_checkable
class ProjectFiles(Protocol):
    """プロジェクトのフォルダ(studio_project.py)の窓口。``kind`` は image / pipeline / python / params。"""
    def files(self, kind: str) -> list: ...


#: 標準のサブフォルダ(正本は ``studio_project.KINDS``。部品を独立させるために写しを持つ)。
_STANDARD_FOLDERS = {"image": "images", "pipeline": "pipelines", "python": "programs", "params": "params"}
_KIND_EXTS = {"image": (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".pgm", ".ppm", ".gif", ".jp2", ".pfm"),
              "pipeline": (".json",), "python": (".py",),
              "params": (".json", ".toml", ".yaml", ".yml", ".xml")}


class DirectoryProjectFiles:
    """フォルダの下の標準のサブフォルダを見る ``ProjectFiles``。"""

    def __init__(self, root: str, folders: Mapping | None = None):
        self.root = root
        self.folders = dict(_STANDARD_FOLDERS if folders is None else folders)

    def files(self, kind: str) -> list:
        sub = self.folders.get(kind)
        if sub is None:
            return []
        base = os.path.join(self.root, sub)
        exts = _KIND_EXTS.get(kind)
        out = []
        try:
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]
                for fn in filenames:
                    if exts and os.path.splitext(fn)[1].lower() not in exts:
                        continue
                    out.append(os.path.relpath(os.path.join(dirpath, fn), base).replace(os.sep, "/"))
                if len(out) > 2000:
                    break
        except OSError:
            return []
        return sorted(out)


#: 呼び出した関数の名前 → 文字列の中でほしいファイルの種類。
FILE_ARG_FUNCS = {"load_pipeline": "pipeline", "load_params": "params", "studio_input": "image",
                  "load_image": "image", "read_image": "image", "imread": "image"}


# --------------------------------------------------------------------------- #
# op の台帳
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class OpInfo:
    name: str
    summary: str = ""
    in_sorts: tuple = ()
    out_sort: str = ""
    params: tuple = ()               # ParamInfo の列(データ引数を含む)
    layer: str = "2d"                # "2d" = つまみ a / b の画像 op、"ledger" = 実引数の台帳 op


@runtime_checkable
class OpCatalog(Protocol):
    def names(self) -> Iterable: ...
    def get(self, name: str): ...


class StaticOpCatalog:
    """``OpInfo`` の一覧から作る台帳(試験・単体のデモ用)。"""

    def __init__(self, infos: Iterable):
        self._infos = {i.name: i for i in infos}

    def names(self):
        return list(self._infos)

    def get(self, name: str):
        return self._infos.get(name)


def _first_sentence(doc: str | None, limit: int = 110) -> str:
    if not doc:
        return ""
    para = doc.strip().split("\n\n", 1)[0].replace("\n", " ").strip()
    m = re.search(r"[。.！!？?](?:\s|$)", para)
    if m and m.end() <= limit + 20:
        para = para[:m.end()].strip()
    return para if len(para) <= limit else para[:limit - 1].rstrip() + "…"


def _data_param_names(sorts: Sequence) -> list:
    names, seen = [], {}
    for s in sorts:
        base = "image" if s in ("image", "color", "cimage") else str(s)
        seen[base] = seen.get(base, 0) + 1
        names.append(base if seen[base] == 1 else "%s%d" % (base, seen[base]))
    return names


def _knob_text(spec: dict) -> str:
    """つまみ(a / b)の意味を 1 行で: ``blur σ · 0.3..3 px`` / ``border handling · reflect|nearest|…``。"""
    kind = spec.get("kind")
    if kind == "unused":
        return "(unused)"
    label = spec.get("label") or ""
    unit = spec.get("unit") or ""
    if kind == "choice" and spec.get("choices"):
        rng = "|".join(str(c) for c in spec["choices"][:5]) + ("|…" if len(spec["choices"]) > 5 else "")
    elif kind == "bool":
        rng = "on/off"
    elif kind in ("float", "int"):
        def f(x):
            return ("%g" % x) if isinstance(x, (int, float)) else str(x)
        rng = "%s..%s" % (f(spec.get("min", 0)), f(spec.get("max", 1)))
        if unit:
            rng += " " + unit
    else:
        rng = ""
    return " · ".join(x for x in (label, rng) if x)


class FullseyeOpCatalog:
    """Fullseye の公開 op の台帳。``api.list_ops()``(画像 op、つまみ a / b)と ``opassist``(台帳 op、実引数)から作る。

    作るのは最初に使ったとき(``import api`` は 1 秒近くかかるので、importはここでは遅延する)。"""

    def __init__(self):
        self._two_d: dict | None = None
        self._ledger: set | None = None
        self._cache: dict = {}
        self._ops_fn: dict | None = None

    def warm_up(self) -> None:
        """名前の一覧を先に作る(背景のスレッドから呼べる。最初の補完の待ちを無くす)。"""
        self._load()

    def _load(self):
        if self._two_d is not None:
            return
        two_d, ledger = {}, set()
        try:
            import api                                      # noqa: PLC0415
            for r in api.list_ops():
                two_d[r["name"]] = r
        except Exception:                                   # noqa: BLE001 — 台帳が無くても補完は動く
            pass
        try:
            import opassist                                 # noqa: PLC0415
            ledger = set(opassist.known_ops())
        except Exception:                                   # noqa: BLE001
            pass
        self._two_d, self._ledger = two_d, ledger

    def names(self):
        self._load()
        return sorted(set(self._two_d) | self._ledger)

    def get(self, name: str):
        self._load()
        if name in self._cache:
            return self._cache[name]
        info = None
        if name in self._two_d:
            info = self._build_two_d(self._two_d[name])
        elif name in self._ledger:
            info = self._build_ledger(name)
        self._cache[name] = info
        return info

    def _build_two_d(self, rec: dict) -> OpInfo:
        name = rec["name"]
        sorts = list(rec.get("in_sorts") or [rec.get("in_sort") or "image"])
        params = [ParamInfo(n, n, "input: %s" % s) for n, s in zip(_data_param_names(sorts), sorts)]
        try:
            import param_specs                              # noqa: PLC0415
            specs = param_specs.spec_for(name)
        except Exception:                                   # noqa: BLE001
            specs = {}
        for letter in ("a", "b"):
            sp = specs.get(letter)
            doc = _knob_text(sp) if sp else ""
            params.append(ParamInfo(letter, "%s=0.5" % letter if sp and sp.get("kind") != "unused" else letter,
                                    "%s · %s" % (letter, doc) if doc else letter, "keyword"))
        summary = ""
        try:
            import ops                                      # noqa: PLC0415
            if self._ops_fn is None:
                self._ops_fn = dict(ops.OPS)
            fn = self._ops_fn.get(name)
            summary = _first_sentence(inspect.getdoc(fn)) if fn is not None else ""
        except Exception:                                   # noqa: BLE001
            pass
        return OpInfo(name, summary, tuple(sorts), str(rec.get("out_sort") or ""), tuple(params), "2d")

    def _build_ledger(self, name: str) -> OpInfo:
        import opassist                                     # noqa: PLC0415
        specs = opassist.param_spec(name)
        params, sorts = [], []
        for s in specs:
            if s.get("kind") == "data":
                sorts.append(str(s.get("sort") or "data"))
                params.append(ParamInfo(s["name"], s["name"], "input: %s" % (s.get("sort") or "data")))
                continue
            text = s["name"] if s.get("required") else "%s=%s" % (s["name"], _short_default(s.get("default")))
            bits = []
            if s.get("doc"):
                bits.append(str(s["doc"]))
            if s.get("unit"):
                bits.append(str(s["unit"]))
            if s.get("choices"):
                bits.append("|".join(str(c) for c in list(s["choices"])[:6]))
            params.append(ParamInfo(s["name"], text, " · ".join(bits), "keyword" if not s.get("required") else "positional"))
        summary, out = "", ""
        try:
            ent = opassist._ledger_entry(name)[1]
            summary = _first_sentence(inspect.getdoc(ent.get("func")) or ent.get("doc"))
            out = str(ent.get("out") or "")
        except Exception:                                   # noqa: BLE001
            pass
        return OpInfo(name, summary, tuple(sorts), out, tuple(params), "ledger")


def _short_default(v) -> str:
    r = repr(v)
    return r if len(r) <= 14 else r[:12] + "…"


# --------------------------------------------------------------------------- #
# 並べ替え
# --------------------------------------------------------------------------- #
class UsageStats:
    """よく使う候補を上に出すための回数(確定した名前を数える)。``to_dict`` / ``from_dict`` で保存できる。"""

    def __init__(self, counts: Mapping | None = None):
        self.counts: dict = dict(counts or {})

    def bump(self, name: str) -> None:
        self.counts[name] = self.counts.get(name, 0) + 1
        if len(self.counts) > 2000:                         # 古い(少ない)ものから捨てる
            for k, _ in sorted(self.counts.items(), key=lambda kv: kv[1])[:500]:
                self.counts.pop(k, None)

    def get(self, name: str) -> int:
        return self.counts.get(name, 0)

    def to_dict(self) -> dict:
        return dict(self.counts)

    @classmethod
    def from_dict(cls, d) -> "UsageStats":
        return cls({str(k): int(v) for k, v in (d or {}).items() if isinstance(v, (int, float))})


def match_tier(name: str, prefix: str) -> int | None:
    """打ちかけ ``prefix`` との一致の度合い。0 完全 / 1 前方(大小一致)/ 2 前方 / 3 語頭 / 4 部分 / 5 あいまい。一致しなければ None。"""
    if not prefix:
        return 2
    if name == prefix:
        return 0
    if name.startswith(prefix):
        return 1
    nl, pl = name.lower(), prefix.lower()
    if nl == pl:
        return 0
    if nl.startswith(pl):
        return 2
    if "_" + pl in nl:
        return 3
    if pl in nl:
        return 4
    if len(pl) >= 2:
        it = iter(nl)
        if all(ch in it for ch in pl):
            return 5
    return None


def rank(cands: Iterable, prefix: str, usage: UsageStats | None = None, limit: int = 60) -> list:
    """前方一致 → 部分一致 → あいまい一致の順に、種類の基準点・使った回数・名前の短さで並べて ``limit`` 件。"""
    scored = []
    seen = set()
    for c in cands:
        t = match_tier(c.name, prefix)
        if t is None:
            continue
        key = (c.name, c.kind)
        if key in seen:
            continue
        seen.add(key)
        s = 1000.0 - t * 150.0 + c.score
        if usage is not None:
            s += min(usage.get(c.name), 20) * 4.0
        s -= len(c.name) * 0.1
        scored.append((s, c))
    scored.sort(key=lambda sc: (-sc[0], sc[1].name))
    return [c for _s, c in scored[:limit]]


# --------------------------------------------------------------------------- #
# 文脈の解析
# --------------------------------------------------------------------------- #
def split_lines(text: str) -> list:
    return text.split("\n")


_WORD_TAIL = re.compile(r"[^\W\d]\w*$|$")


def word_prefix(before: str) -> str:
    """カーソルの前の打ちかけの識別子。"""
    m = _WORD_TAIL.search(before)
    return m.group(0) if m else ""


@dataclass(frozen=True)
class CallContext:
    callee: str | None               # 例 ``gaussian`` / ``np.zeros`` / ``fs.ledger.dem_slope``
    n_positional: int                # 完成した位置引数の数
    used_kwargs: frozenset
    current_kw: str | None           # 今の引数が ``name=`` で始まっているときの name
    innermost: bool                  # カーソルがこの呼び出しの直下(入れ子の括弧の中ではない)か
    open_line: int
    open_col: int


_KW_SEG = re.compile(r"^\s*([A-Za-z_]\w*)\s*=(?!=)")
_NOT_CALLEE = frozenset(keyword.kwlist) - {"None", "True", "False"}
_CALLEE = re.compile(r"([A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)*)\s*$")


def call_context(lines: Sequence, line: int, col: int, window: int = 80) -> CallContext | None:
    """カーソルを囲む呼び出し ``f(`` の文脈。括弧の外なら ``None``。文字列とコメントの中の括弧・コンマは数えない。"""
    start = max(0, line - window)
    state = syn.triple_state_before(lines, start)
    frames: list = []                       # 開いている括弧: dict
    for ln in range(start, line + 1):
        raw = lines[ln] if ln < len(lines) else ""
        text = raw[:col] if ln == line else raw
        toks, state, _open = syn.scan_line_detail(text, state)
        skip = [(a, b) for a, b, cat in toks if cat in ("string", "comment")]
        if _open is not None and not skip:
            skip.append((_open[0], len(text)))
        si = 0
        i = 0
        n = len(text)
        while i < n:
            while si < len(skip) and skip[si][1] <= i:
                si += 1
            if si < len(skip) and skip[si][0] <= i < skip[si][1]:
                if frames:
                    frames[-1]["seg"].append(" ")
                i = skip[si][1]
                continue
            ch = text[i]
            if ch in "([{":
                callee = None
                if ch == "(":
                    m = _CALLEE.search(text[:i])
                    if m:
                        name = re.sub(r"\s+", "", m.group(1))
                        head = name.split(".")[0]
                        before_callee = text[:m.start()].rstrip()
                        if head not in _NOT_CALLEE and not before_callee.endswith(("def", "class")):
                            callee = name
                frames.append({"ch": ch, "callee": callee, "pos": 0, "kwargs": set(), "seg": [],
                               "ol": ln, "oc": i})
            elif ch in ")]}":
                if frames:
                    frames.pop()
                    if frames:
                        frames[-1]["seg"].append("_")
            elif ch == "," and frames:
                f = frames[-1]
                segtxt = "".join(f["seg"])
                m = _KW_SEG.match(segtxt)
                if m:
                    f["kwargs"].add(m.group(1))
                elif segtxt.strip():
                    f["pos"] += 1
                f["seg"] = []
            elif frames:
                frames[-1]["seg"].append(ch)
            i += 1
    if not frames:
        return None
    innermost = True
    for f in reversed(frames):
        if f["ch"] == "(" and f["callee"]:
            segtxt = "".join(f["seg"])
            m = _KW_SEG.match(segtxt)
            return CallContext(f["callee"], f["pos"], frozenset(f["kwargs"]), m.group(1) if m else None,
                               innermost, f["ol"], f["oc"])
        innermost = False
    return None


# --------------------------------------------------------------------------- #
# 本文の中の名前
# --------------------------------------------------------------------------- #
_DEF_RE = re.compile(r"^[ \t]*(?:async[ \t]+)?def[ \t]+([^\W\d]\w*)[ \t]*\(", re.M)
_CLASS_RE = re.compile(r"^[ \t]*class[ \t]+([^\W\d]\w*)", re.M)
_ASSIGN_RE = re.compile(r"^[ \t]*((?:[^\W\d]\w*|\([^\W\d][\w, ]*\))(?:[ \t]*,[ \t]*(?:[^\W\d]\w*|\*[^\W\d]\w*))*)[ \t]*(?::[^=\n]+)?(?:=|\+=|-=|\*=|/=)(?!=)", re.M)
_FOR_RE = re.compile(r"\bfor[ \t]+([^\W\d][\w, ()]*?)[ \t]+in\b")
_AS_RE = re.compile(r"\bas[ \t]+([^\W\d]\w*)")
_WALRUS_RE = re.compile(r"([^\W\d]\w*)[ \t]*:=")
_IMPORT_RE = re.compile(r"^[ \t]*import[ \t]+([^\n#]+)", re.M)
_FROM_RE = re.compile(r"^[ \t]*from[ \t]+([\w.]+)[ \t]+import[ \t]+\(?([^\n#]+)", re.M)
_ATTR_SEEN_RE = re.compile(r"\b([^\W\d]\w*)\.([^\W\d]\w*)")
_IDENT_LIST = re.compile(r"[^\W\d]\w*")


@dataclass
class TextIndex:
    """本文から拾った名前の索引。"""
    variables: dict = field(default_factory=dict)       # 名前 → 行(定義・代入のある行。0 始まり)
    functions: dict = field(default_factory=dict)       # 名前 → Signature
    classes: set = field(default_factory=set)
    modules: dict = field(default_factory=dict)         # 別名 → モジュールの名前
    imported: dict = field(default_factory=dict)        # 別名 → (モジュール, 名前)
    attrs: dict = field(default_factory=dict)           # 受け手の名前 → {属性名}


def _sig_from_def(text: str, start: int) -> Signature | None:
    """``def name(`` の ``(`` の位置から対応する ``)`` まで取り、ast で引数を読む。"""
    depth, i, n = 0, start, len(text)
    while i < n and i < start + 2000:
        c = text[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    else:
        return None
    header = "def _f" + text[start:i + 1] + ": pass"
    try:
        fn = ast.parse(header).body[0]
    except SyntaxError:
        return None
    params = []
    a = fn.args
    posonly = list(a.posonlyargs) + list(a.args)
    defaults = [None] * (len(posonly) - len(a.defaults)) + list(a.defaults)
    for arg, d in zip(posonly, defaults):
        t = arg.arg + (": " + ast.unparse(arg.annotation) if arg.annotation else "")
        if d is not None:
            t += " = " + ast.unparse(d)
        params.append(ParamInfo(arg.arg, t, "", "positional" if d is None else "positional"))
    if a.vararg:
        params.append(ParamInfo(a.vararg.arg, "*" + a.vararg.arg, "", "var_positional"))
    for arg, d in zip(a.kwonlyargs, a.kw_defaults):
        t = arg.arg + (" = " + ast.unparse(d) if d is not None else "")
        params.append(ParamInfo(arg.arg, t, "", "keyword"))
    if a.kwarg:
        params.append(ParamInfo(a.kwarg.arg, "**" + a.kwarg.arg, "", "var_keyword"))
    return Signature("", tuple(params))


def index_text(text: str) -> TextIndex:
    """本文の名前(def / class / 代入 / for / as / import / walrus)と、受け手ごとの属性(``self.x``)を拾う。"""
    idx = TextIndex()
    lines_start = None

    def lineno(pos: int) -> int:
        nonlocal lines_start
        if lines_start is None:
            lines_start = [m.start() for m in re.finditer(r"\n", text)]
        import bisect
        return bisect.bisect_left(lines_start, pos)

    for m in _DEF_RE.finditer(text):
        sig = _sig_from_def(text, m.end() - 1)
        name = m.group(1)
        idx.functions[name] = Signature(name, sig.params if sig else ()) if sig else Signature(name, ())
        idx.variables.setdefault(name, lineno(m.start()))
    for m in _CLASS_RE.finditer(text):
        idx.classes.add(m.group(1))
        idx.variables.setdefault(m.group(1), lineno(m.start()))
    for m in _ASSIGN_RE.finditer(text):
        for w in _IDENT_LIST.findall(m.group(1)):
            if w not in _NOT_CALLEE:
                idx.variables.setdefault(w, lineno(m.start()))
    for m in _FOR_RE.finditer(text):
        for w in _IDENT_LIST.findall(m.group(1)):
            idx.variables.setdefault(w, lineno(m.start()))
    for m in _AS_RE.finditer(text):
        idx.variables.setdefault(m.group(1), lineno(m.start()))
    for m in _WALRUS_RE.finditer(text):
        idx.variables.setdefault(m.group(1), lineno(m.start()))
    for m in _IMPORT_RE.finditer(text):
        for part in m.group(1).split(","):
            mm = re.match(r"\s*([\w.]+)(?:\s+as\s+(\w+))?\s*$", part)
            if mm:
                mod, alias = mm.group(1), mm.group(2)
                key = alias or mod.split(".")[0]
                idx.modules[key] = mod if alias else mod.split(".")[0]
                idx.variables.setdefault(key, lineno(m.start()))
    for m in _FROM_RE.finditer(text):
        for part in m.group(2).replace(")", "").split(","):
            mm = re.match(r"\s*(\w+)(?:\s+as\s+(\w+))?\s*$", part)
            if mm:
                key = mm.group(2) or mm.group(1)
                idx.imported[key] = (m.group(1), mm.group(1))
                idx.variables.setdefault(key, lineno(m.start()))
    if len(text) < 400_000:
        for m in _ATTR_SEEN_RE.finditer(text):
            idx.attrs.setdefault(m.group(1), set()).add(m.group(2))
    return idx


_INDEX_CACHE: dict = {"key": None, "idx": None}


def cached_index(text: str) -> TextIndex:
    key = (len(text), hash(text))
    if _INDEX_CACHE["key"] != key:
        _INDEX_CACHE["idx"] = index_text(text)
        _INDEX_CACHE["key"] = key
    return _INDEX_CACHE["idx"]


# --------------------------------------------------------------------------- #
# スニペット
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Snippet:
    trigger: str
    desc: str          # tr() に通す英語の 1 行説明
    body: str          # ``$0`` がカーソルの位置


SNIPPETS = (
    Snippet("for", "for loop over a range", "for i in range($0):\n    pass"),
    Snippet("if", "if / else", "if $0:\n    pass\nelse:\n    pass"),
    Snippet("def", "function definition", "def $0(x):\n    return x"),
    Snippet("with", "with open(...) as f", "with open($0) as f:\n    data = f.read()"),
    Snippet("try", "try / except", "try:\n    $0\nexcept Exception as e:\n    print(e)"),
    Snippet("pipe", "pipeline of ops applied to the input image",
            "steps = pipeline([(\"gaussian\", 0.4, 0.5), (\"otsu\", 0.5, 0.5)])\nresult = steps(img)\nshow(result$0)"),
    Snippet("chain", "chain ops on the input image and show the result",
            "smooth = gaussian(img, a=0.4)\nedges = sobel_mag(smooth)\nshow(edges$0)"),
    Snippet("loadpipe", "load a saved pipeline from the project and run it",
            "steps = load_pipeline(\"$0\")\nresult = steps(img)\nshow(result)"),
)


def snippet_completions(prefix: str, tr: Callable = lambda s: s) -> list:
    out = []
    for sn in SNIPPETS:
        body = sn.body
        off = body.find("$0")
        body = body.replace("$0", "")
        out.append(Completion(sn.trigger, "snippet", tr(sn.desc), body, 6.0, doc=body,
                              cursor_offset=off if off >= 0 else None))
    return out


# --------------------------------------------------------------------------- #
# 既定の prelude の名前
# --------------------------------------------------------------------------- #
#: Program の前置きが用意する名前(studio_program.PRELUDE_RESERVED の写し + 結びの語)。供給元から差し替えられる。
DEFAULT_PRELUDE = {
    "img": ("variable", "the input image"), "image": ("variable", "the input image"),
    "show": ("function", "show a value as an image in the result window"),
    "op": ("function", "call an operator by name: op(\"gaussian\", img, a=0.4)"),
    "pipeline": ("function", "make a pipeline from [(op, a, b), ...]"),
    "current_pipeline": ("function", "the pipeline built from the stage list"),
    "load_pipeline": ("function", "load a saved pipeline file from the project"),
    "load_params": ("function", "load a parameter bundle file from the project"),
    "np": ("module", "numpy"), "fs": ("module", "the fullseye package"),
    "ui": ("function", "run a function on the GUI thread"),
    "show_window": ("function", "open a window from the program"),
    "studio_input": ("function", "the image Studio has open"), "studio_output": ("function", "path of the result file"),
}


# --------------------------------------------------------------------------- #
# 自前の供給元
# --------------------------------------------------------------------------- #
_IMPORT_LINE = re.compile(r"^\s*import\s+(?P<done>(?:[\w.]+(?:\s+as\s+\w+)?\s*,\s*)*)(?P<cur>[\w.]*)$")
_FROM_MODULE = re.compile(r"^\s*from\s+(?P<cur>[\w.]*)$")
_FROM_IMPORT = re.compile(r"^\s*from\s+(?P<mod>[\w.]+)\s+import\s+\(?(?P<done>(?:\w+(?:\s+as\s+\w+)?\s*,\s*)*)(?P<cur>\w*)$")
_ATTR_CHAIN = re.compile(r"(?<![\w.)\]'\"])(?P<root>[^\W\d]\w*(?:\.[^\W\d]\w*)*)\.(?P<cur>[^\W\d]?\w*)$")

_MODULE_NAMES: list | None = None


def module_names() -> list:
    """import できるトップレベルのモジュール名(標準 + 入っているパッケージ)。最初の 1 回だけ数える。"""
    global _MODULE_NAMES
    if _MODULE_NAMES is None:
        names = set(getattr(sys, "stdlib_module_names", ()))
        try:
            import pkgutil
            names.update(m.name for m in pkgutil.iter_modules() if not m.name.startswith("_"))
        except Exception:                                   # noqa: BLE001
            pass
        names.update(n for n in sys.modules if "." not in n and not n.startswith("_"))
        _MODULE_NAMES = sorted(names)
    return _MODULE_NAMES


def _kind_of_obj(obj) -> str:
    if inspect.ismodule(obj):
        return "module"
    if inspect.isclass(obj):
        return "class"
    if callable(obj):
        return "function"
    return "variable"


def _sig_text(obj) -> str:
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return ""
    except Exception:                                       # noqa: BLE001
        return ""


def _doc_of(obj) -> str:
    try:
        return inspect.getdoc(obj) or ""
    except Exception:                                       # noqa: BLE001
        return ""


def _describe_obj(name: str, obj) -> tuple:
    """``(1 行の説明, 詳しい説明)``。プロパティは呼ばない(``obj`` は既に解決済みの物だけ)。"""
    if inspect.ismodule(obj) or inspect.isclass(obj) or callable(obj):
        sig = _sig_text(obj)
        doc = _doc_of(obj)
        first = _first_sentence(doc, 90)
        one = (name + sig if sig and len(sig) < 60 else first) or type(obj).__name__
        return (one if one else first), (name + sig + "\n\n" + doc if sig else doc)
    return type(obj).__name__, ""


def _static_attr(obj, name: str):
    """プロパティを呼ばずに属性を取る。取れなければ ``None``(``_MISSING``)。"""
    try:
        return inspect.getattr_static(obj, name)
    except AttributeError:
        return _MISSING


_MISSING = object()


class FallbackProvider:
    """jedi なしの補完・シグネチャ・ホバー。``namespace`` は ``{名前: 値}``(prelude + 実行後の変数。呼び出しごとに引く)。"""

    def __init__(self, namespace=None, catalog: OpCatalog | None = None, prelude: Mapping | None = None,
                 project_files: ProjectFiles | None = None, usage: UsageStats | None = None,
                 tr: Callable = lambda s: s):
        self._namespace = namespace
        self.catalog = catalog
        self.prelude = dict(DEFAULT_PRELUDE if prelude is None else prelude)
        self.project_files = project_files
        self.usage = usage
        self.tr = tr
        self._op_names: frozenset | None = None

    # ---- 入力 ----
    def namespace(self) -> Mapping:
        ns = self._namespace
        if callable(ns):
            try:
                ns = ns()
            except Exception:                               # noqa: BLE001
                ns = None
        return ns or {}

    def op_names(self) -> frozenset:
        if self._op_names is None:
            try:
                self._op_names = frozenset(self.catalog.names()) if self.catalog is not None else frozenset()
            except Exception:                               # noqa: BLE001
                self._op_names = frozenset()
        return self._op_names

    def vocabulary(self) -> tuple:
        """色分けに渡す ``(op の名前, prelude の名前)``。"""
        return self.op_names(), frozenset(self.prelude) | frozenset(
            k for k in self.namespace() if isinstance(k, str) and not k.startswith("_") and k in self.prelude)

    # ---- 補完 ----
    def complete(self, text: str, line: int, col: int) -> list:
        lines = split_lines(text)
        if not (0 <= line < len(lines)):
            return []
        raw = lines[line]
        col = max(0, min(col, len(raw)))
        before = raw[:col]
        state = syn.triple_state_before(lines, line)
        toks, _st, open_str = syn.scan_line_detail(before, state)
        # コメントの中は出さない
        if toks and toks[-1][2] == "comment" and toks[-1][1] >= len(before):
            return []
        if open_str is not None:
            return self._complete_string(lines, line, col, before, open_str)
        m = _IMPORT_LINE.match(before)
        if m:
            return self._complete_modules(m.group("cur"))
        m = _FROM_MODULE.match(before)
        if m:
            return self._complete_modules(m.group("cur"))
        m = _FROM_IMPORT.match(before)
        if m:
            return self._complete_from_import(m.group("mod"), m.group("cur"))
        m = _ATTR_CHAIN.search(before)
        if m:
            return self._complete_attribute(text, m.group("root"), m.group("cur"))
        if re.search(r"(?<![\w.])\d+\.\d*$", before):
            return []                                        # 数の途中(3. や 3.1)
        if before.rstrip().endswith("."):
            return []                                        # 受け手を特定できない(``f().`` など)
        prefix = word_prefix(before)
        if re.search(r"\b(?:def|class)\s+\w*$", before):
            return []                                        # 新しい名前を付けているところ
        return self._complete_names(text, lines, line, col, before, prefix)

    def _complete_string(self, lines, line, col, before, open_str) -> list:
        start, quote, is_f = open_str
        qlen = len(quote)
        # 前置き(r, f ...)を飛ばして引用符の後ろの位置
        qpos = start
        while qpos < len(before) and before[qpos] not in "'\"":
            qpos += 1
        typed = before[qpos + qlen:] if qpos < len(before) else ""
        if self.project_files is None:
            return []
        ctx = call_context(lines, line, qpos)
        if ctx is None or ctx.callee is None:
            return []
        fn = ctx.callee.split(".")[-1]
        kind = FILE_ARG_FUNCS.get(fn)
        if kind is None or ctx.n_positional != 0 or ctx.current_kw not in (None, "name", "path", "file"):
            return []
        out = []
        try:
            names = list(self.project_files.files(kind))
        except Exception:                                    # noqa: BLE001
            return []
        for nm in names:
            shown = os.path.splitext(nm)[0] if kind in ("pipeline", "params") and fn.startswith("load_") else nm
            out.append(Completion(nm if kind == "image" or not fn.startswith("load_") else shown, "file",
                                  self.tr("%s file in the project") % self.tr(kind), score=0.0,
                                  replace_len=len(typed)))
        return rank(out, typed, self.usage)

    def _complete_modules(self, cur: str) -> list:
        if "." in cur:
            head, _, tail = cur.rpartition(".")
            mod = sys.modules.get(head)
            subs = []
            if mod is not None and hasattr(mod, "__path__"):
                try:
                    import pkgutil
                    subs = [m.name for m in pkgutil.iter_modules(mod.__path__)]
                except Exception:                            # noqa: BLE001
                    subs = []
            cands = [Completion(s, "module", self.tr("module"), score=10.0, replace_len=len(tail)) for s in subs]
            return rank(cands, tail, self.usage)
        cands = [Completion(n, "module", self.tr("module"), score=10.0 + (5 if n in sys.modules else 0))
                 for n in module_names()]
        return rank(cands, cur, self.usage)

    def _complete_from_import(self, mod: str, cur: str) -> list:
        obj = sys.modules.get(mod)
        if obj is None:
            return []                                        # 未 import のモジュールは勝手に import しない
        names = getattr(obj, "__all__", None) or [n for n in dir(obj) if not n.startswith("_")]
        cands = []
        for n in names:
            v = _static_attr(obj, n)
            kind = "variable" if v is _MISSING else _kind_of_obj(v)
            cands.append(Completion(n, kind, "", score=10.0))
        return rank(cands, cur, self.usage)

    def _resolve_root(self, text: str, dotted: str):
        """``np.linalg`` のような受け手の式を、``sys.modules`` と実行後の名前空間から静的に解決する。"""
        parts = dotted.split(".")
        ns = self.namespace()
        idx = cached_index(text)
        head = parts[0]
        if head in ns:
            obj = ns[head]
        elif head in idx.modules:
            mod = idx.modules[head]
            obj = sys.modules.get(mod)
            if obj is None:
                return _MISSING
            if mod.count(".") and "." not in head and head != mod:
                pass
        elif head in idx.imported:
            m, n = idx.imported[head]
            base = sys.modules.get(m)
            if base is None:
                return _MISSING
            obj = _static_attr(base, n)
        elif head == "fs" and "fullseye" in sys.modules:
            obj = sys.modules["fullseye"]                   # prelude の fs(Studio は fullseye を import 済み)
        elif head == "np" and "numpy" in sys.modules:
            obj = sys.modules["numpy"]
        else:
            return _MISSING
        for p in parts[1:]:
            if obj is _MISSING:
                return _MISSING
            obj = _static_attr(obj, p)
            if isinstance(obj, property):
                return _MISSING                              # プロパティは呼ばない
        return obj

    def _complete_attribute(self, text: str, root: str, cur: str) -> list:
        obj = self._resolve_root(text, root)
        cands = []
        ops = self.op_names()
        is_fs = root in ("fs", "fs.ledger") or root.endswith("ledger") and root.split(".")[0] == "fs"
        if obj is not _MISSING and obj is not None:
            try:
                names = [n for n in dir(obj) if cur.startswith("_") or not n.startswith("_")]
            except Exception:                                # noqa: BLE001
                names = []
            for n in names:
                if match_tier(n, cur) is None:
                    continue
                v = _static_attr(obj, n)
                if v is _MISSING or isinstance(v, (property, staticmethod, classmethod)) and not callable(v):
                    kind = "attribute"
                    v2 = None
                else:
                    v2 = v
                    kind = _kind_of_obj(v) if not isinstance(v, (property,)) else "attribute"
                    if kind == "variable":
                        kind = "attribute"
                if is_fs and n in ops:
                    cands.append(Completion(n, "op", "", score=15.0))
                    continue
                cands.append(self._lazy_completion(n, kind, v2, 12.0 if kind != "attribute" else 9.0))
        else:
            seen = cached_index(text).attrs.get(root.split(".")[-1], set())
            for n in sorted(seen):
                cands.append(Completion(n, "attribute", self.tr("seen in this file"), score=4.0))
        return self._fill_ops(rank(cands, cur, self.usage))

    def _lazy_completion(self, name: str, kind: str, obj, score: float, op: OpInfo | None = None) -> Completion:
        if op is not None:
            return self._op_completion(op, score + 3)
        detail = type(obj).__name__ if obj is not None else ""
        if obj is not None and (callable(obj) or inspect.ismodule(obj)):
            detail = {"module": self.tr("module"), "class": self.tr("class")}.get(kind, "") or ""
        return Completion(name, kind, detail, score=score,
                          doc_loader=(lambda o=obj, n=name: _describe_obj(n, o)[1] or _doc_of(o)) if obj is not None else None)

    def _op_completion(self, op: OpInfo, score: float, insert_call: bool = False) -> Completion:
        sorts = ", ".join(op.in_sorts) if op.in_sorts else ""
        io = ("%s -> %s" % (sorts, op.out_sort)) if (sorts or op.out_sort) else ""
        detail = (io + ("  " if io and op.summary else "") + op.summary).strip()
        lines = [op.name + "(" + ", ".join(p.text for p in op.params) + ")"]
        if io:
            lines.append(self.tr("input -> output") + ": " + io)
        if op.summary:
            lines.append(op.summary)
        for p in op.params:
            if p.doc and p.kind != "positional" or (p.doc and op.layer == "ledger"):
                lines.append("  %s: %s" % (p.name, p.doc))
        return Completion(op.name, "op", detail, "", score, doc="\n".join(lines))

    def _complete_names(self, text, lines, line, col, before, prefix) -> list:
        cands: list = []
        ctx = call_context(lines, line, col)
        idx = cached_index(text)
        ns = self.namespace()
        # キーワード引数名
        if ctx is not None and ctx.innermost and ctx.current_kw is None and ctx.callee:
            sig = self.resolve_signature(text, ctx.callee)
            if sig is not None:
                for p in sig.params:
                    if p.kind in ("keyword", "positional", "var_keyword") and p.name not in ctx.used_kwargs \
                            and not p.name.startswith("*") and p.kind != "var_keyword":
                        if p.kind == "positional" and sig.params.index(p) < ctx.n_positional:
                            continue                         # もう位置で渡した引数
                        cands.append(Completion(p.name + "=", "param", p.doc or p.text, p.name + "=",
                                                30.0 if p.kind == "keyword" else 26.0, doc=p.doc))
        # 本文の名前
        for name, ln in idx.variables.items():
            if name in idx.functions:
                kind, sc = "function", 22.0
            elif name in idx.classes:
                kind, sc = "class", 22.0
            elif name in idx.modules or name in idx.imported:
                kind, sc = "module", 18.0
            else:
                kind, sc = "variable", 24.0
            if name == prefix:
                continue                                      # 打っている最中の名前そのもの
            cands.append(Completion(name, kind, self.tr("line %d") % (ln + 1), score=sc))
        # 実行後の名前空間
        for name, val in list(ns.items())[:5000]:
            if not isinstance(name, str) or name.startswith("_") or name in self.prelude or name in self.op_names():
                continue                                     # op は台帳の候補(型と説明つき)を使う
            kind = _kind_of_obj(val)
            cands.append(Completion(name, "variable" if kind == "variable" else kind, type(val).__name__, score=23.0))
        # prelude
        for name, (kind, desc) in self.prelude.items():
            cands.append(Completion(name, kind, self.tr(desc), score=20.0))
        # op
        if self.catalog is not None:
            for name in self.op_names():
                if match_tier(name, prefix) is None:
                    continue
                if name in self.prelude:
                    continue
                cands.append(Completion(name, "op", "", score=14.0))      # 説明は順位が決まってから作る
        # 組み込み・予約語
        for name in syn._BUILTIN_NAMES:
            if match_tier(name, prefix) is not None:
                obj = getattr(builtins, name, None)
                cands.append(self._lazy_completion(name, _kind_of_obj(obj) if obj is not None else "function", obj, 8.0))
        for name in keyword.kwlist:
            cands.append(Completion(name, "keyword", self.tr("keyword"), score=9.0))
        if prefix:
            cands.extend(snippet_completions(prefix, self.tr))
        return self._fill_ops(rank(cands, prefix, self.usage))

    def _fill_ops(self, ranked: list) -> list:
        """順位の決まった候補のうち、説明の無い op だけ台帳から説明を作る(全 op ぶんは作らない)。"""
        if self.catalog is None:
            return ranked
        out = []
        for c in ranked:
            if c.kind == "op" and not c.detail:
                try:
                    info = self.catalog.get(c.name)
                except Exception:                            # noqa: BLE001
                    info = None
                if info is not None:
                    c = replace(self._op_completion(info, c.score), score=c.score)
            out.append(c)
        return out

    # ---- シグネチャ ----
    def resolve_signature(self, text: str, callee: str) -> Signature | None:
        parts = callee.split(".")
        name = parts[-1]
        idx = cached_index(text)
        plain = len(parts) == 1 or callee in ("fs." + name, "fs.ledger." + name, "ledger." + name)
        if len(parts) == 1 and name in idx.functions:
            sig = idx.functions[name]
            return Signature(name, sig.params, self.tr("defined in this file"))
        if plain and self.catalog is not None:
            info = self.catalog.get(name)
            if info is not None:
                return Signature(info.name, info.params, info.summary, info.out_sort)
        obj = self._resolve_root(text, callee) if len(parts) >= 1 else _MISSING
        if obj is _MISSING and len(parts) == 1 and name in builtins.__dict__:
            obj = getattr(builtins, name)
        if obj is _MISSING or obj is None:
            return None
        return signature_of_object(name, obj)

    def signature(self, text: str, line: int, col: int):
        """``(Signature, 今の引数の番号)``。呼び出しの中でなければ ``None``。"""
        lines = split_lines(text)
        if not (0 <= line < len(lines)):
            return None
        ctx = call_context(lines, line, min(col, len(lines[line])))
        if ctx is None or not ctx.callee:
            return None
        sig = self.resolve_signature(text, ctx.callee)
        if sig is None:
            return None
        return sig, sig.active_param(ctx.n_positional, ctx.current_kw, ctx.used_kwargs)

    # ---- ホバー ----
    def hover(self, text: str, line: int, col: int):
        lines = split_lines(text)
        if not (0 <= line < len(lines)):
            return None
        raw = lines[line]
        state = syn.triple_state_before(lines, line)
        toks, _st = syn.scan_line_base(raw, state)
        word, cat, a = None, None, 0
        for ta, tb, tc in toks:
            if ta <= col < tb or (col == tb and tc in syn._NAMEY):
                word, cat, a = raw[ta:tb], tc, ta
                break
        if word is None or cat not in syn._NAMEY + ("keyword", "decorator"):
            return None
        chain = raw[:a].rstrip()
        root = None
        if chain.endswith("."):
            m = re.search(r"([^\W\d]\w*(?:\.[^\W\d]\w*)*)\s*\.$", chain)
            root = m.group(1) if m else None
        full = (root + "." + word) if root else word
        sig = self.resolve_signature(text, full)
        if sig is not None:
            head = "".join(s for s, _b in sig.segments(None))
            return Hover(head, sig.summary)
        if word in self.prelude and not root:
            kind, desc = self.prelude[word]
            return Hover("%s  (%s)" % (word, kind), self.tr(desc))
        ns = self.namespace()
        if word in ns and not root:
            return Hover("%s: %s" % (word, type(ns[word]).__name__), "")
        if cat == "keyword":
            return Hover(word, self.tr("keyword"))
        return None


def signature_of_object(name: str, obj) -> Signature | None:
    """``inspect.signature``、取れなければ docstring の 1 行目(``zeros(shape, dtype=float, ...)``)から。"""
    try:
        sig = inspect.signature(obj)
    except (TypeError, ValueError):
        sig = None
    except Exception:                                       # noqa: BLE001
        sig = None
    doc = _doc_of(obj)
    summary = _first_sentence(doc, 100)
    if sig is not None:
        params = []
        for p in sig.parameters.values():
            kind = {p.VAR_POSITIONAL: "var_positional", p.VAR_KEYWORD: "var_keyword",
                    p.KEYWORD_ONLY: "keyword"}.get(p.kind, "positional")
            t = str(p)
            params.append(ParamInfo(p.name, t, "", kind))
        ret = "" if sig.return_annotation is inspect.Signature.empty else inspect.formatannotation(sig.return_annotation)
        return Signature(name, tuple(params), summary, ret)
    first = doc.split("\n", 1)[0] if doc else ""
    m = re.match(r"^\s*%s\((.*)\)" % re.escape(name), first)
    if m:
        out, depth, cur = [], 0, ""
        for ch in m.group(1):
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            if ch == "," and depth == 0:
                out.append(cur.strip())
                cur = ""
            else:
                cur += ch
        if cur.strip():
            out.append(cur.strip())
        params = []
        for t in out:
            if t in ("/", "*"):
                continue
            nm = re.match(r"\*{0,2}([A-Za-z_]\w*)", t)
            kind = "var_positional" if t.startswith("*") and not t.startswith("**") else (
                "var_keyword" if t.startswith("**") else "positional")
            params.append(ParamInfo(nm.group(1) if nm else t, t, "", kind))
        return Signature(name, tuple(params), _first_sentence("\n".join(doc.split("\n")[1:]).strip(), 100))
    return None


# --------------------------------------------------------------------------- #
# jedi(任意)
# --------------------------------------------------------------------------- #
_JEDI = {"mod": None, "tried": False}


def jedi_available() -> bool:
    if not _JEDI["tried"]:
        _JEDI["tried"] = True
        try:
            import jedi                                      # noqa: PLC0415
            _JEDI["mod"] = jedi
        except Exception:                                    # noqa: BLE001 — 無い・壊れている・塞がれている
            _JEDI["mod"] = None
    return _JEDI["mod"] is not None


def reset_jedi_cache() -> None:
    _JEDI.update(mod=None, tried=False)


_JEDI_KIND = {"module": "module", "class": "class", "instance": "variable", "function": "function",
              "param": "param", "keyword": "keyword", "statement": "variable", "property": "attribute",
              "path": "file"}


class JediProvider:
    """jedi による補完・シグネチャ。``namespace`` があれば ``jedi.Interpreter``(実行後の値を見る)。"""

    def __init__(self, namespace=None, usage: UsageStats | None = None):
        self._namespace = namespace
        self.usage = usage

    def _script(self, text):
        jedi = _JEDI["mod"]
        ns = self._namespace
        if callable(ns):
            ns = ns()
        if ns:
            return jedi.Interpreter(text, [dict(ns)])
        return jedi.Script(text)

    def complete(self, text: str, line: int, col: int) -> list:
        if not jedi_available():
            return []
        try:
            comps = self._script(text).complete(line + 1, col)
        except Exception:                                    # noqa: BLE001 — jedi の内部エラーで入力を止めない
            return []
        out = []
        for c in comps[:200]:
            kind = _JEDI_KIND.get(c.type, "variable")
            if kind == "file":
                continue
            try:
                detail = (c.description or "").replace("\n", " ")
            except Exception:                                # noqa: BLE001
                detail = ""
            out.append(Completion(c.name, kind, detail[:80], score=11.0,
                                  replace_len=None, doc_loader=(lambda cc=c: cc.docstring())))
        return out

    def signature(self, text: str, line: int, col: int):
        if not jedi_available():
            return None
        try:
            sigs = self._script(text).get_signatures(line + 1, col)
        except Exception:                                    # noqa: BLE001
            return None
        if not sigs:
            return None
        s = sigs[0]
        params = tuple(ParamInfo(p.name, p.to_string().replace("param ", "", 1), "", "positional") for p in s.params)
        idx = s.index
        return Signature(s.name or "", params, _first_sentence(s.docstring(), 100)), idx

    def hover(self, text: str, line: int, col: int):
        if not jedi_available():
            return None
        try:
            names = self._script(text).help(line + 1, col)
        except Exception:                                    # noqa: BLE001
            return None
        if not names:
            return None
        n = names[0]
        return Hover(n.full_name or n.name, _first_sentence(n.docstring(), 200))


class LineBase:
    """行が 1 始まりの供給元(``studio_program.complete`` など)を 0 始まりの世界へ包む。"""

    def __init__(self, source, base: int = 1):
        self.source = source
        self.base = int(base)

    def complete(self, text, line, col):
        return self.source.complete(text, line + self.base, col)

    def hover(self, text, line, col):
        return self.source.hover(text, line + self.base, col)


class CompositeProvider:
    """自前(op・prelude・スニペット・引数名・ファイル名)と jedi(一般の Python)を重ねる。"""

    def __init__(self, fallback: FallbackProvider, jedi: JediProvider | None = None,
                 usage: UsageStats | None = None):
        self.fallback = fallback
        self.jedi = jedi
        self.usage = usage or fallback.usage

    def complete(self, text: str, line: int, col: int) -> list:
        mine = self.fallback.complete(text, line, col)
        if self.jedi is None or not jedi_available():
            return mine
        theirs = self.jedi.complete(text, line, col)
        lines = split_lines(text)
        prefix = word_prefix(lines[line][:col]) if 0 <= line < len(lines) else ""
        have_names = {c.name for c in mine}
        extra = [c for c in theirs if c.name not in have_names]
        # 自前が属性を解決できなかった(空)ときは jedi の結果をそのまま使う
        return rank(list(mine) + extra, prefix, self.usage)

    def signature(self, text: str, line: int, col: int):
        r = self.fallback.signature(text, line, col)
        if r is None and self.jedi is not None:
            r = self.jedi.signature(text, line, col)
        return r

    def hover(self, text: str, line: int, col: int):
        r = self.fallback.hover(text, line, col)
        if r is None and self.jedi is not None:
            r = self.jedi.hover(text, line, col)
        return r


def default_provider(namespace=None, catalog: OpCatalog | None = None, prelude: Mapping | None = None,
                     project_files: ProjectFiles | None = None, usage: UsageStats | None = None,
                     tr: Callable = lambda s: s, use_jedi: bool = True):
    """既定の供給元。jedi があれば重ね、無ければ自前だけ。``catalog`` が ``None`` なら ``FullseyeOpCatalog()``。"""
    fb = FallbackProvider(namespace, FullseyeOpCatalog() if catalog is None else catalog, prelude,
                          project_files, usage, tr)
    jd = JediProvider(namespace, usage) if use_jedi and jedi_available() else None
    return CompositeProvider(fb, jd, usage)


# --------------------------------------------------------------------------- #
# 自動で出す条件
# --------------------------------------------------------------------------- #
def auto_trigger(before: str, typed: str) -> str | None:
    """文字 ``typed`` を打った直後(``before`` は打った後のカーソルの前の行)に自動で出すか。

    返り値 ``"dot"`` / ``"paren"`` / ``"import"`` / ``"word"`` / ``None``。
    ``"word"`` は識別子を 2 文字以上打ったとき(1 文字目は静かに待つ)。"""
    if typed == ".":
        return None if re.search(r"\d\.$", before) else "dot"
    if typed == "(":
        return "paren"
    if typed == " " and re.match(r"^\s*(?:from\s+[\w.]+\s+)?import\s$", before):
        return "import"
    if typed and (typed.isalnum() or typed == "_"):
        w = word_prefix(before)
        if len(w) >= 2 or (len(w) == 1 and before[:-1].endswith(".")):
            return "word"
    return None
