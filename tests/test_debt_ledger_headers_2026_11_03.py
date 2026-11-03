"""負債台帳(``docs/*_DEBT.json``)のヘッダの件数が中身と一致すること。

2026-11-03 の完成度監査(A-10): ``docs/LEDGER_CONTRACT_DEBT.json`` の ``counts.refused`` が 66 なのに、
``debt.refused`` の項目は 65 だった。2026-10-11 の commit 2efed981b7 が ``annotate_colorbar`` を手で
外したときに ``counts`` を直し忘れた。ラチェットの門(``tests/test_ledger_contracts.py``)は ``debt`` の
中身だけを見るので、ヘッダのずれは誰にも見えなかった。読む人と道具はヘッダの数字を引用する。

門: ``counts`` + ``debt`` の形の台帳は、区分の集合が同じで、区分ごとに ``counts[k] == len(debt[k])``。
``total`` + ``per_file`` の形は ``total == sum(per_file.values())``。どちらの形でもない ``*_DEBT.json`` が
増えたら落ちる(黙って数えずに通さない)。
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _debt_files():
    paths = sorted(glob.glob(os.path.join(ROOT, "docs", "*_DEBT.json")))
    # 3 本(契約・隙間・空の assert)。読み方が壊れて 0 本で通るのを防ぐ。
    assert len(paths) >= 3, paths
    return paths


def test_every_debt_file_header_matches_its_body():
    checked = []
    bad = []
    for p in _debt_files():
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        name = os.path.basename(p)
        if "counts" in d and "debt" in d:
            actual = {k: len(v) for k, v in d["debt"].items()}
            if set(actual) != set(d["counts"]):
                bad.append("%s: 区分が違う counts=%s debt=%s" % (name, sorted(d["counts"]), sorted(actual)))
            for k in sorted(set(actual) & set(d["counts"])):
                if d["counts"][k] != actual[k]:
                    bad.append("%s: counts.%s=%d だが debt.%s は %d 件" % (name, k, d["counts"][k], k, actual[k]))
            checked.append(name)
        elif "total" in d and "per_file" in d:
            s = sum(d["per_file"].values())
            if d["total"] != s:
                bad.append("%s: total=%d だが per_file の合計は %d" % (name, d["total"], s))
            checked.append(name)
        else:
            bad.append("%s: counts+debt でも total+per_file でもない(この門が数えられない形)" % name)
    assert len(checked) >= 3, checked
    assert not bad, "\n".join(bad)
