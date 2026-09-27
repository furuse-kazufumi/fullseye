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

_MOD = {"graphinv": graphinv}

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
