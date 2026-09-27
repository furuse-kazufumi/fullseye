# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsgraph — fullseye graph-invariant op registry (wiring matrices).

Motivation (2026-09-27): a connectome, a vessel network or a pipe map becomes an
adjacency matrix, and fullseye had nothing that asks "is this wiring more than its
degree sequence?". graphinv.py answers with exact integer identities and a
degree-preserving null (Maslov & Sneppen 2002 / Milo et al. 2002), worked on the
public C. elegans connectome (Cook et al. 2019; 302 listed - 300 wired == CANL, CANR).

Type vocabulary: **no new word**. Every op eats a square ``matrix`` and returns a
``table`` (dict of integers, ratios and degree arrays) — the sorts opsspc already uses —
except ``graph_edge_consensus``, which eats a ``table`` ``{individual: matrix}`` (K wirings
on one node order; Witvliet et al. 2021 give 8 worms from birth to adulthood).

Usage:
    import opsgraph
    opsgraph.list_ops("null")
    opsgraph.get("graph_cycle3")(adj)
"""
import graphinv
import physarum_search
import treemorph

_MOD = {"graphinv": graphinv, "treemorph": treemorph, "physarum_search": physarum_search}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    "degree": [
        ("graph_degree_summary", "graphinv", ["matrix"], "table"),
    ],
    "motif": [
        ("graph_cycle3", "graphinv", ["matrix"], "table"),
    ],
    # ★比べられる数字はヌルで割った比だけ。素の個数は規模で決まる。
    "null": [
        ("graph_degree_preserving_null", "graphinv", ["matrix"], "table"),
    ],
    # 対称操作(左右の対を入れ替える)。恒等ペアで 1.0 が門。
    "symmetry": [
        ("graph_swap_symmetry", "graphinv", ["matrix"], "table"),
    ],
    # 個体と個体(K 枚の配線を同じ節点順で重ねる)。入力は table {個体名: 行列}。
    # ★matrix の束を images に載せない —— 画像を渡すと全画素 > 0 で「全結合が全員に在る」
    #   というもっともらしい嘘を返す。table なら他 op の表を渡しても op が断る。
    "population": [
        ("graph_edge_consensus", "graphinv", ["table"], "table"),
        # 2 時点(または 2 個体)の間で、どの節点にどれだけ重みが足されたか(入力と出力を分ける)。
        ("graph_strength_growth", "graphinv", ["matrix", "matrix"], "table"),
    ],
    # 神経の木(SWC)。木はグラフの一種なのでこの台帳に置く。入口は text(SWC の本文か
    # パス)で、読んだ時点で構造の約束(根 1・親 id < 子 id・節点 = 辺 + 1)を検査する。
    # 3-D の Sholl は回転で整数が 1 つも動かない —— 投影(plane=)は動く、が PoC の主題。
    "tree": [
        ("tree_from_swc", "treemorph", ["text"], "table"),
        ("tree_morphometry", "treemorph", ["table"], "table"),
        ("tree_sholl", "treemorph", ["table"], "table"),
        # 走行長(ERL): 正解の骨格の上を候補のラベル(節点ごとの 1-D 整数列 = signal の席)で走る。
        ("tree_run_length", "treemorph", ["table", "signal"], "table"),
    ],
    # 流れで道を探す(粘菌 Tero 2010 の管の力学)。定理が門: 最短路が一意なら導電度はその指示関数に
    # 収束する(Bonifaci 2012)。真値は Dijkstra(scipy)と route_through_array(skimage)。
    "flow": [
        ("graph_physarum_path", "physarum_search", ["matrix"], "table"),
        ("physarum_route", "physarum_search", ["image2d"], "table"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = fn.__doc__.strip().splitlines()[0] if fn is not None and fn.__doc__ else ""
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "func": fn, "doc": doc}
    return reg


OPSGRAPH = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSGRAPH.items() if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。空 — 全 op が dict(= table)を素で返す。
ADAPTERS = {}


def get(name):
    """op 名から関数を引く(無ければ KeyError)。"""
    return OPSGRAPH[name]["func"]


def info(name):
    """op の登録情報(category / in / out / doc)。"""
    m = OPSGRAPH[name]
    return {k: m[k] for k in ("category", "module", "in", "out", "doc")}


def call(name, *args, **kwargs):
    """登録名で呼ぶ。"""
    return get(name)(*args, **kwargs)


def missing():
    """台帳に在るが実体が無い op(ゼロであることを試験が確かめる)。"""
    return [n for n, m in OPSGRAPH.items() if m["func"] is None]
