# -*- coding: utf-8 -*-
"""収蔵番号を発行する —— 博物館の収蔵台帳の作法をそのまま持ち込む。

なぜ道具が要るか
================
展示の見出し番号は、これまで生成器が ``n += 1`` で**毎回数え直して**いた。
だから展示を 1 つ挟むだけで以降の番号が全部ずれ、**記事を分けるたびに番号が動く**。
番号は読者の索引であり外部リンクの宛先でもあるので、動く設計は壊れ続ける。

実際の博物館はこれを解いている —— **収蔵番号は受け入れた瞬間に 1 回だけ発行し、
二度と変えない・再利用しない。そして「どこに展示しているか」とは独立**である。
展示替えでも他館貸出でも番号は動かない。だからこの道具は:

* 番号を持たない展示にだけ新しい番号を出す(既存の行には**触らない**)
* 書式は ``2026.037``(受入年 + その年の連番)。年で区切るので桁が暴れず、
  「いつ入ったか」が番号だけで分かる
* 展示から消えた id を**勝手に除籍しない** —— 理由を書くのは人の仕事なので、
  ``--check`` が「番号は在るのに展示に無い」を落とす(fail-closed)
* 除籍しても**番号は欠番のまま**。再利用すると、古いリンクが別の展示を指す

``--check`` は書かずに検査だけする(CI と preflight 用)。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXHIBITS = os.path.join(_ROOT, "docs", "articles", "exhibits")
CAPTIONS = os.path.join(EXHIBITS, "poc_captions.json")
LEDGER = os.path.join(EXHIBITS, "exhibit_numbers.json")

#: 収蔵番号の書式。受入年 4 桁 + "." + その年の連番 3 桁以上。
NO_RE = re.compile(r"^(\d{4})\.(\d{3,})$")

LEDGER_NOTE = (
    "収蔵台帳。追記のみ。収蔵番号は受け入れた瞬間に 1 回だけ発行し、以後変えない・"
    "再利用しない。番号は「どこに展示しているか」とは独立なので、記事間の移動でも "
    "棟の分割でも動かない。除籍は retired に理由つきで記録し、番号は欠番のまま残す。"
    "訂正は消さずに note 欄へ。発行は tools/gen_exhibit_numbers.py。"
)


class LedgerError(SystemExit):
    pass


def load_ledger(path: str = LEDGER) -> dict:
    """台帳を読む。無ければ空の台帳を返す(初回発行のため)。"""
    if not os.path.exists(path):
        return {"_note": LEDGER_NOTE, "issued": {}, "retired": {}}
    with io.open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    d.setdefault("issued", {})
    d.setdefault("retired", {})
    return d


def _exhibits(path: str = CAPTIONS) -> list:
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)["exhibits"]


def all_numbers(ledger: dict) -> dict:
    """**これまでに発行した全番号** -> id。現役と除籍の両方を含む。

    再利用を防ぐ判定はここを見る —— 除籍した番号を空き番号と見なすと、
    古いリンクが別の展示を指すようになる。
    """
    out = {}
    for who in ("issued", "retired"):
        for eid, rec in (ledger.get(who) or {}).items():
            out[rec["no"]] = eid
    return out


def issue(exhibits: list, ledger: dict) -> list:
    """番号を持たない展示に、**作られた順**で新しい番号を出す。

    発行順を `added` にするのは、収蔵番号が「いつ受け入れたか」だけで決まり、
    どの翼・どの記事に置くかとは独立だから。同じ日のものは台帳内の現在の並びで
    決める(1 回きりの決定なので、以後は並べ替えても番号は動かない)。

    Returns:
        list: 新しく出した ``(id, 番号)``。既存の行は 1 つも触らない。
    """
    issued = ledger["issued"]
    taken = all_numbers(ledger)
    #: 年ごとの「これまでに使った最大の連番」。除籍分も数える(再利用しないため)。
    top = {}
    for no in taken:
        m = NO_RE.match(no)
        if not m:
            raise LedgerError("台帳に書式の違う番号がある: %r" % no)
        top[m.group(1)] = max(top.get(m.group(1), 0), int(m.group(2)))

    order = sorted(range(len(exhibits)), key=lambda i: (exhibits[i]["added"], i))
    fresh = []
    for i in order:
        ex = exhibits[i]
        if ex["id"] in issued:
            continue
        year = ex["added"][:4]
        top[year] = top.get(year, 0) + 1
        no = "%s.%03d" % (year, top[year])
        issued[ex["id"]] = {"no": no, "accessioned": ex["added"]}
        fresh.append((ex["id"], no))
    return fresh


def check(exhibits: list, ledger: dict) -> list:
    """台帳の健全性。**問題の一覧**を返す(空なら健全)。

    門がここを呼ぶ。中身は 4 つ:
    1. 展示に番号が在るか
    2. 番号が重複していないか(除籍分とも衝突しないか)
    3. 書式が ``2026.037`` か
    4. **番号は在るのに展示に無い** id が、除籍の記録を持っているか
    """
    bad = []
    ids = {e["id"] for e in exhibits}
    issued = ledger["issued"]
    retired = ledger["retired"]

    for e in exhibits:
        if e["id"] not in issued:
            bad.append("収蔵番号が無い展示: %s(gen_exhibit_numbers.py で発行する)" % e["id"])

    seen = {}
    for who, table in (("issued", issued), ("retired", retired)):
        for eid, rec in table.items():
            no = rec.get("no", "")
            if not NO_RE.match(no):
                bad.append("番号の書式が違う: %s -> %r(2026.037 の形)" % (eid, no))
            if no in seen:
                bad.append("番号が重複: %s を %s と %s が持っている" % (no, seen[no], eid))
            seen[no] = eid

    for eid in issued:
        if eid not in ids and eid not in retired:
            bad.append(
                "台帳に在るのに展示に無い: %s —— 外したのなら retired に理由を書くこと"
                "(番号は欠番のまま残し、再利用しない)" % eid)
    return bad


def _write(ledger: dict, path: str = LEDGER) -> None:
    ledger["_note"] = LEDGER_NOTE
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="書かずに検査だけ(未発行が在れば失敗)")
    a = ap.parse_args(argv)

    exhibits = _exhibits()
    ledger = load_ledger()

    if a.check:
        bad = check(exhibits, ledger)
        if bad:
            print("収蔵台帳に問題がある:", *("  - " + b for b in bad), sep="\n")
            return 1
        print("収蔵台帳 ok: 現役 %d / 除籍 %d" % (len(ledger["issued"]), len(ledger["retired"])))
        return 0

    fresh = issue(exhibits, ledger)
    bad = check(exhibits, ledger)
    if bad:
        print("発行したが台帳に問題が残る:", *("  - " + b for b in bad), sep="\n")
        return 1
    _write(ledger)
    if fresh:
        print("収蔵番号を %d 件発行:" % len(fresh))
        for eid, no in fresh:
            print("  %s  %s" % (no, eid))
    else:
        print("新しく発行するものは無い(現役 %d 件)" % len(ledger["issued"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
