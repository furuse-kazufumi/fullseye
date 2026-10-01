# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsearch — op 名を打つそばから引く索引(Studio の補完・Operator 検索用、Qt を使わない)。

名前順の一覧を 1 本持ち、そこから 2 つの並びを作るだけ:

* ``names``    — 小文字にした op 名の昇順。**先頭一致**は二分探索(``bisect``)1 回で範囲が決まる。
* ``suffixes`` — 各名前の末尾の切れ端(``vx_warp_affine`` → ``x_warp_affine``, ``_warp_affine``, … ``e``)を
  ``(切れ端, 名前の番号)`` で昇順に並べた**接尾辞配列**。**途中一致**(HDevelop のツールヒントのように、
  打った文字を名前のどこかに含む op)も、この並びへの二分探索 1 回で範囲が決まる。

打鍵ごとの手間は O(log N + 当たった件数)で、全件を舐めない。順位は
**完全一致 → 先頭一致 → ``_`` の区切りの直後で一致 → 途中一致**、同じ順位の中は名前順。

★名前順の一覧は門の真値も兼ねる: 「全件を愚直に調べた答え = 二分探索の答え」を
``tests/test_opsearch.py`` が乱数と構造のある問い合わせ(区切り・1 文字・無い語・大文字)で確かめる。
"""
from __future__ import annotations

from bisect import bisect_left
from typing import Iterable, List, Sequence, Tuple

__all__ = ["OpNameIndex", "RANKS"]

#: 順位の名前(小さいほど上)。``search(..., with_rank=True)`` が返す。
RANKS = ("exact", "prefix", "word", "contains")


class OpNameIndex:
    """op 名の索引。大文字小文字は区別しない(表示は元の綴り)。

    Parameters
    ----------
    names : iterable of str
        op 名。重複は 1 つにまとめる。空文字は捨てる。
    """

    def __init__(self, names: Iterable[str]):
        uniq = {}
        for n in names:
            if not isinstance(n, str):
                raise TypeError("OpNameIndex: op 名は str(来たのは %r)" % (type(n).__name__,))
            if n and n.lower() not in uniq:
                uniq[n.lower()] = n
        self._lower: List[str] = sorted(uniq)                     # 名前順の一覧(小文字)
        self._orig: List[str] = [uniq[k] for k in self._lower]    # 表示用の元の綴り
        suf: List[Tuple[str, int]] = []
        for i, k in enumerate(self._lower):
            for s in range(1, len(k)):                            # s = 0 は先頭一致の並びで足りる
                suf.append((k[s:], i))
        suf.sort()
        self._suf_keys: List[str] = [k for k, _ in suf]
        self._suf_ids: List[int] = [i for _, i in suf]
        self._suf_pos: List[int] = [len(self._lower[i]) - len(k) for k, i in suf]   # 名前の中の開始位置

    def __len__(self) -> int:
        return len(self._lower)

    @property
    def names(self) -> List[str]:
        """名前順の一覧(元の綴り)。"""
        return list(self._orig)

    def _prefix_range(self, keys: Sequence[str], q: str) -> Tuple[int, int]:
        lo = bisect_left(keys, q)
        hi = bisect_left(keys, q + "\U0010ffff", lo)              # q で始まる最後の次
        return lo, hi

    def prefix(self, query: str) -> List[str]:
        """``query`` で始まる op 名(名前順)。二分探索 1 回。"""
        q = query.lower()
        lo, hi = self._prefix_range(self._lower, q)
        return self._orig[lo:hi]

    def search(self, query: str, limit: int | None = 50, with_rank: bool = False):
        """``query`` を名前のどこかに含む op 名を、順位 → 名前順で返す。

        ``limit`` 件で打ち切る(None なら全部)。``with_rank`` なら ``(名前, 順位名)`` の列。
        空の問い合わせは空を返す(全件を出さない —— 補完の一覧が 2,000 行になる)。
        """
        if not isinstance(query, str):
            raise TypeError("search: query は str(来たのは %r)" % (type(query).__name__,))
        if limit is not None and limit < 0:
            raise ValueError("search: limit は 0 以上か None(来たのは %r)" % (limit,))
        q = query.strip().lower()
        if not q:
            return []
        rank = {}
        lo, hi = self._prefix_range(self._lower, q)
        for i in range(lo, hi):
            rank[i] = 0 if self._lower[i] == q else 1
        if limit is not None and len(rank) >= limit:          # 先頭一致だけで足りる: 切れ端の並びを見ない
            order = sorted(rank, key=lambda i: (rank[i], i))[:limit]
            if with_rank:
                return [(self._orig[i], RANKS[rank[i]]) for i in order]
            return [self._orig[i] for i in order]
        lo, hi = self._prefix_range(self._suf_keys, q)
        for j in range(lo, hi):
            i = self._suf_ids[j]
            if i in rank and rank[i] <= 2:
                continue
            p = self._suf_pos[j]
            r = 2 if self._lower[i][p - 1] == "_" else 3
            if r < rank.get(i, 9):
                rank[i] = r
        order = sorted(rank, key=lambda i: (rank[i], i))
        if limit is not None:
            order = order[:limit]
        if with_rank:
            return [(self._orig[i], RANKS[rank[i]]) for i in order]
        return [self._orig[i] for i in order]


def brute_force_search(names: Iterable[str], query: str, limit: int | None = None):
    """門の真値: 全件を愚直に調べる版(``OpNameIndex.search`` と同じ順位の規則)。"""
    uniq = {}
    for n in names:
        if n and n.lower() not in uniq:
            uniq[n.lower()] = n
    q = query.strip().lower()
    if not q:
        return []
    out = []
    for k in sorted(uniq):
        if k == q:
            r = 0
        elif k.startswith(q):
            r = 1
        elif ("_" + q) in k:
            r = 2
        elif q in k:
            r = 3
        else:
            continue
        out.append((r, k))
    out.sort()
    res = [uniq[k] for _, k in out]
    return res if limit is None else res[:limit]
