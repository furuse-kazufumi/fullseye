# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""op 名は台帳をまたいで一意であること。

op 名は addressing の鍵である ―― ``opsX.get(name)`` / ``docs/ops`` のリンク /
Studio のヘルプ / 連鎖ファザーの ``--script`` は全部これで引く。同じ名前が
2 つの台帳にあると、名前で引く側では**片方がもう片方を隠す**。しかも隠れた
方は「テストも通るし単体では動く」ので、消えていること自体に気づけない。

2026-09-02、``tools/chain_fuzz.py`` の台帳を集めた総数(707)と一意な op 名の数
(706)が 1 だけ食い違ったことで最初の 1 件が見つかった。数が合わないことが
唯一の手掛かりだった —— だからここで恒久的に数えておく。
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))


#: 既知の衝突。**新しい衝突を増やさない**ための記録であって、これで良いという
#: 意味ではない。解消には公開されている op 名の改名が要るので、独断では行わない。
KNOWN_NAME_COLLISIONS = {
    "gaussians_to_voxel":
        "match3d.gaussians_to_voxel(means, scales, opacities, size, bounds) と "
        "reprconv.gaussians_to_voxel(gaussians, shape, origin, spacing, truncate) が "
        "**別の関数**なのに同名。前者は 3DGS の生の配列を、後者は ledger 型 "
        "'gaussians' の dict を取る(2026-09-02 実測、同一オブジェクトではない)。"
        "docs/ops は dim ごとのディレクトリに分かれるのでノートは両方残るが、"
        "名前で引く経路(chain_fuzz の --script / --minimize)では片方しか見えない。"
        "どちらも公開ファサード(api.py / fullseye/__init__.py)には出ていないので "
        "改名しても facade の破壊ではないが、台帳経由で呼んでいる利用者はいうる。",
}


def _catalog():
    pytest.importorskip("chain_fuzz", reason="tools/chain_fuzz.py が読めない")
    import chain_fuzz
    return chain_fuzz.catalog()


def test_op_names_are_unique_across_ledgers():
    """同じ op 名が 2 つ以上の台帳に現れない(既知の 1 件を除く)。"""
    entries = _catalog()
    seen = {}
    for name, fam, ins, out, fn in entries:
        seen.setdefault(name, []).append((fam, getattr(fn, "__module__", "?")))
    dup = {n: v for n, v in seen.items() if len(v) > 1}
    new = {n: v for n, v in dup.items() if n not in KNOWN_NAME_COLLISIONS}
    assert not new, (
        "op 名が台帳をまたいで衝突している(新規): %s\n"
        "名前は addressing の鍵なので、片方が名前で引く経路から消える。" % new)


def test_known_collisions_are_still_real():
    """直ったのに一覧へ残り続けない(KNOWN_LEDGER_GAPS と同じ規律)。"""
    entries = _catalog()
    seen = {}
    for name, *_rest in entries:
        seen[name] = seen.get(name, 0) + 1
    stale = sorted(n for n in KNOWN_NAME_COLLISIONS if seen.get(n, 0) < 2)
    assert not stale, ("KNOWN_NAME_COLLISIONS に残っているが実際は衝突していない: %s"
                       " — 直ったなら一覧から消すこと" % stale)


def test_catalog_size_matches_distinct_names():
    """総数と一意名の差 = 衝突の数。既知分ちょうどに一致すること。

    最初の 1 件はこの差が 1 だったことだけが手掛かりだった。差そのものを
    検査にしておくと、名前を潰した瞬間に落ちる。
    """
    entries = _catalog()
    distinct = len({n for n, *_ in entries})
    extra = len(entries) - distinct
    expected = sum(1 for n in KNOWN_NAME_COLLISIONS)
    assert extra == expected, (
        f"台帳エントリ {len(entries)} / 一意な op 名 {distinct} = 差 {extra}、"
        f"既知の衝突は {expected} 件")
