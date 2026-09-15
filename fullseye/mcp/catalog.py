# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""op のカタログと知識層の引き当て(MCP サーバの中身。プロトコルは知らない)。

★**1 つの正本に寄せない。** 2026-09-15 の実測で、``docs/OP_INDEX.json`` は 918 op、
``ops.REGISTRY`` は 901 op、``docs/ops/**/*.md`` のノートは 1943 枚、そのうち
索引に無いノートが 1022 枚あり、**541 個は ``fullseye`` facade に実在する関数**だった。
索引だけを見る検索は、実在する 541 個の機能を LLM から構造的に隠す ——
[[feedback_registered_only_gates_miss_unregistered]](登録済みを数える門は未登録に
盲目)と符号が逆の同じ形。だから **4 層(索引 / レジストリ / ノート / facade)を
別々に数え、返り値に出どころを付ける**。LLM は「索引にあるが facade に無い」
「ノートだけある」を区別して読める。
(同日の続き: 索引の生成器が台帳 33 族を数えるようになり、索引は 1,939 op。
ノートを持つ名前は全部索引に入った。層を分けて数える設計はそのまま —— 索引に
無い facade 関数がまだ 448 ある。)

知識層のノートは開発 checkout の Markdown(frontmatter つき)を正本にし、無ければ
wheel に同梱される ``studio_assets/op_help/<op>.html`` に落ちる。**どちらを使ったかは
返り値に書く**(黙って代替に落ちない)。
"""
from __future__ import annotations

import glob
import json
import os
import re
from dataclasses import dataclass, field

# fullseye/mcp/catalog.py -> fullseye/ -> repo root
_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(_PKG)
DOCS = os.path.join(ROOT, "docs")
OPS_DOCS = os.path.join(DOCS, "ops")
FIG_DIR = os.path.join(OPS_DOCS, "_fig")
OP_INDEX = os.path.join(DOCS, "OP_INDEX.json")
STUDIO_HELP = os.path.join(ROOT, "studio_assets", "op_help")

#: 図の変種 -> 説明。順序は「見せる価値」の順(入出力対比が最初)。
FIGURE_KINDS = (
    (".png", "入力 → 出力(合成入力 128x128、左が入力・右が出力)"),
    (".a.jpg", "つまみ a の掃引(0.1 / 0.5 / 0.9、b は既定)"),
    (".b.jpg", "つまみ b の掃引(0.1 / 0.5 / 0.9、a は既定)"),
    (".inputs.jpg", "別の入力(合成シーン / 写真 / 硬貨)での出力"),
    (".chain.jpg", "前置きの op と繋いだ段階図"),
    (".gif", "動画 / 体積 / ライトフィールドの補助アニメーション"),
)

#: ★5 層。最初は 4 層で組み、「索引にもレジストリにも facade にも無いノート」が
#: 480 枚残った。残骸かと思ったら **480 / 480 が ``fullseye.ledger`` で解決**した
#: (型付き台帳。レジストリでは ``tb_project``、台帳では ``project`` のように接頭辞が
#: 違う)。「無い」と言う前に全層を引く —— 4 層目まで引いて止めていたら、実在する
#: 480 個の機能を残骸と呼んでいた。
SOURCES = ("index", "registry", "ledger", "note", "facade")

_FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)


class CatalogError(RuntimeError):
    """カタログを組めない(正本が無い等)。黙って空のカタログにしない。"""


def _frontmatter(text: str) -> dict[str, str]:
    m = _FM_RE.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line[:1].isspace():
            continue
        k, _, v = line.partition(":")
        # `version: 0.1.11  # fullseye lib version ...` の末尾コメントを落とす
        v = v.split("#", 1)[0].strip()
        out[k.strip()] = v
    return out


@dataclass
class Entry:
    name: str
    sources: set = field(default_factory=set)
    in_sort: str | None = None
    out_sort: str | None = None
    category: str | None = None
    tier: str | None = None
    halcon: str | None = None
    dim: str | None = None
    note_paths: list = field(default_factory=list)

    def quality(self) -> int:
        """並べ替えに使う「揃っている性質」の数(0..3): 索引に載る / ノートがある /
        呼べる(registry か ledger か facade のどれか)。

        ★以前は ``len(sources)`` だった。索引が台帳 33 族を数えるようになった
        2026-09-15、"gauss" で `gaussian_beam`(facade+index+ledger+note の 4 層)が
        `gaussian`(index+note+registry の 3 層)を追い越した —— 台帳 op は facade にも
        出ているので**呼べる層が 2 重に数えられる**。呼べるかどうかは 1 つの性質。
        """
        s = self.sources
        return (("index" in s) + ("note" in s)
                + (bool(s & {"registry", "ledger", "facade"})))

    def row(self) -> dict:
        return {
            "name": self.name,
            "sources": sorted(self.sources),
            "in_sort": self.in_sort, "out_sort": self.out_sort,
            "category": self.category, "tier": self.tier,
            "halcon": self.halcon, "dim": self.dim,
            "has_note": bool(self.note_paths),
        }


class Catalog:
    """4 層を合わせた op の一覧。``load()`` で組む。"""

    def __init__(self, entries: dict[str, Entry], sorts: list[str]):
        self.entries = entries
        self.sorts = sorts

    # ------------------------------------------------------------------ build
    @classmethod
    def load(cls, *, with_facade: bool = True) -> "Catalog":
        if not os.path.exists(OP_INDEX):
            raise CatalogError(
                "docs/OP_INDEX.json が無い(%s)。`py -3.11 imgevolve.py index` で作る。"
                "無いまま空のカタログを返すと、検索が『該当なし』を正直に見せかける" % OP_INDEX)
        with open(OP_INDEX, encoding="utf-8") as f:
            idx = json.load(f)
        entries: dict[str, Entry] = {}

        def ent(name: str) -> Entry:
            e = entries.get(name)
            if e is None:
                e = entries[name] = Entry(name=name)
            return e

        # 1. 索引(機械可読。in/out sort と tier の正本)
        for o in idx["ops"]:
            e = ent(o["name"])
            e.sources.add("index")
            e.in_sort, e.out_sort = o.get("in_sort"), o.get("out_sort")
            e.category, e.tier, e.halcon = o.get("category"), o.get("tier"), o.get("halcon")

        # 2. レジストリ(`fullseye.apply` が実行できるもの)
        try:
            import ops as _ops
            for o in _ops.REGISTRY:
                e = ent(o.name)
                e.sources.add("registry")
                e.in_sort = e.in_sort or o.in_sort
                e.out_sort = e.out_sort or o.out_sort
                e.category = e.category or getattr(o, "category", None)
        except Exception as exc:                              # noqa: BLE001
            raise CatalogError("ops.REGISTRY を読めない: %r" % exc) from exc

        # 3. ノート(知識層。frontmatter の `op:` を持つ md だけ。ガイドは除外される)
        for p in glob.glob(os.path.join(OPS_DOCS, "**", "*.md"), recursive=True):
            if os.sep + "_fig" + os.sep in p:
                continue
            with open(p, encoding="utf-8") as f:
                fm = _frontmatter(f.read(1200))
            name = fm.get("op")
            if not name:
                continue
            e = ent(name)
            e.sources.add("note")
            e.note_paths.append(p)
            e.dim = e.dim or fm.get("dim")
            e.category = e.category or fm.get("category")
            e.in_sort = e.in_sort or fm.get("in")
            e.out_sort = e.out_sort or fm.get("out")
            e.halcon = e.halcon or fm.get("halcon")

        # 4. facade(`import fullseye` で呼べる名前)+ 5. 型付き台帳(`fullseye.ledger.<name>`)
        if with_facade:
            import fullseye
            for n in getattr(fullseye, "__all__", ()):
                if callable(getattr(fullseye, n, None)):
                    ent(n).sources.add("facade")
            led = getattr(fullseye, "ledger", None)
            if led is not None:
                for n in dir(led):
                    if not n.startswith("_"):
                        ent(n).sources.add("ledger")

        sorts = sorted(set(idx.get("sorts") or []) |
                       {e.in_sort for e in entries.values() if e.in_sort} |
                       {e.out_sort for e in entries.values() if e.out_sort})
        return cls(entries, sorts)

    # ----------------------------------------------------------------- search
    def search(self, query: str = "", *, in_sort: str | None = None,
               out_sort: str | None = None, source: str | None = None,
               limit: int = 20) -> dict:
        """部分一致検索。完全一致 > 前置き一致 > 部分一致 の順に並べる。

        返り値には**層別の内訳**(``by_sources``)を付ける —— 「該当 5 件」だけでは
        その 5 件が実行できる op なのかノートだけなのか分からない。
        """
        q = (query or "").strip().lower()
        toks = [t for t in re.split(r"[\s,]+", q) if t]
        hits = []
        for e in self.entries.values():
            if in_sort and e.in_sort != in_sort:
                continue
            if out_sort and e.out_sort != out_sort:
                continue
            if source and source not in e.sources:
                continue
            hay = " ".join(x for x in (e.name, e.halcon, e.category, e.dim, e.tier) if x).lower()
            if toks and not all(t in hay for t in toks):
                continue
            if not toks:
                rank = 2
            elif e.name.lower() == q or (e.halcon or "").lower() == q:
                rank = 0
            elif e.name.lower().startswith(q):
                rank = 1
            else:
                rank = 2
            # ★同点の割り方は `api.find_op` と同じにする: 別名を複数 op が共有するとき
            #   `name == halcon` の**正典**を先に。次に層が多い(実行もノートもある)方。
            #   実測 2026-09-15: "gauss" で `gauss_filter`(正典)と `gaussian` が同点になり、
            #   名前順だと `_` < `i` で前者が先に来た —— 偶然そうなっていたのを規則にした。
            canonical = 0 if (e.halcon and e.halcon == e.name) else 1
            hits.append(((rank, canonical, -e.quality(), e.name), e))
        hits.sort(key=lambda t: t[0])
        hits = [(k[0], k[3], e) for k, e in hits]
        total = len(hits)
        rows = [e.row() for _, _, e in hits[:limit]]
        by_sources: dict[str, int] = {}
        for _, _, e in hits:
            k = "+".join(sorted(e.sources))
            by_sources[k] = by_sources.get(k, 0) + 1
        return {"query": query, "total": total, "returned": len(rows),
                "truncated": total > len(rows), "by_sources": by_sources, "ops": rows}

    # ---------------------------------------------------------------- nearest
    def nearest(self, name: str, n: int = 5) -> list[str]:
        """typo に効く近い名前(編集距離)。

        ★最初は部分一致検索を流用していて、``gaussy`` → ``[]`` だった。部分一致は
        「打ち間違い」という**いちばん使う場面で必ず空**になる(2026-09-15 の実 stdio
        往復で発覚)。名前の完全一致は ``entries`` が答え、近さは編集距離が答える。
        """
        import difflib
        pool = list(self.entries)
        hits = difflib.get_close_matches(name, pool, n=n, cutoff=0.6)
        if len(hits) < n:
            # 接頭辞つき/なし(`project` ↔ `tb_project`)も拾う
            low = name.lower()
            for k in pool:
                kl = k.lower()
                if k not in hits and (kl.endswith("_" + low) or low.endswith("_" + kl)):
                    hits.append(k)
                if len(hits) >= n:
                    break
        return hits[:n]

    # ------------------------------------------------------------------- help
    def help(self, name: str) -> dict:
        """知識層のノートと図を引く。無ければ**理由つきで** found=False。"""
        e = self.entries.get(name)
        if e is None:
            return {"found": False, "name": name,
                    "reason": "どの層にも無い op 名(%s)" % " / ".join(SOURCES),
                    "nearest": self.nearest(name)}
        out: dict = {"found": True, **e.row()}
        body, fmt, src = None, None, None
        if e.note_paths:
            p = e.note_paths[0]
            with open(p, encoding="utf-8") as f:
                text = f.read()
            fm = _frontmatter(text)
            body = _FM_RE.sub("", text, count=1)
            fmt, src = "markdown", os.path.relpath(p, ROOT).replace(os.sep, "/")
            out["frontmatter"] = fm
            if len(e.note_paths) > 1:
                out["other_notes"] = [os.path.relpath(x, ROOT).replace(os.sep, "/")
                                      for x in e.note_paths[1:]]
        else:
            html = os.path.join(STUDIO_HELP, name + ".html")
            if os.path.exists(html):
                with open(html, encoding="utf-8") as f:
                    body = f.read()
                fmt, src = "html", os.path.relpath(html, ROOT).replace(os.sep, "/")
        out["body"] = body
        out["body_format"] = fmt
        out["body_source"] = src
        out["body_chars"] = len(body) if body else 0
        figs = []
        for ext, desc in FIGURE_KINDS:
            p = os.path.join(FIG_DIR, name + ext)
            if os.path.exists(p):
                figs.append({"path": p, "kind": ext, "description": desc,
                             "bytes": os.path.getsize(p)})
        out["figures"] = figs
        return out

    # --------------------------------------------------------------- coverage
    def coverage(self) -> dict:
        """4 層の交差を数える。**検索がどれだけ信用できるか**を LLM にも見せる。"""
        by = {s: {e.name for e in self.entries.values() if s in e.sources} for s in SOURCES}
        idx, reg, led, note, fac = by["index"], by["registry"], by["ledger"], by["note"], by["facade"]
        callable_ = idx | reg | led | fac
        note_only = sorted(note - callable_)
        return {
            "total_names": len(self.entries),
            "per_source": {s: len(v) for s, v in by.items()},
            "index_without_note": sorted(idx - note),
            "registry_not_in_index": sorted(reg - idx),
            "index_not_in_registry": sorted(idx - reg),
            "ledger_without_note": sorted(led - note),
            "facade_not_in_index": len(fac - idx),
            "note_only": len(note_only),
            "note_only_names": note_only,
        }
