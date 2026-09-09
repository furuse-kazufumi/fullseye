#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent 出力の DESIGN_NOTES 訳バッチを検証してから merge する(一時)。

使い方:
    py -3.11 tools/_dn_verify_merge.py <master.json> <out_0.json> [out_1.json ...]

各 out は {"by_index": {"<idx>": {"en","zh","tw","ko","de"}}} 形式。
検証: 言語ごとに不正な字種を弾く —
  en/de/ko : かな・CJK 漢字を含んではいけない(ko はハングルのみ可)
  zh/tw    : かな・ハングルを含んではいけない(漢字は可)
違反エントリは**除外**して報告(混入を公開物に流さない)。
合格分を docs/i18n/design_notes.json に merge する。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = os.path.join(ROOT, "docs", "i18n", "design_notes.json")

KANA = re.compile(r"[ぁ-んァ-ヶ]")
HANGUL = re.compile(r"[가-힣]")
CJK = re.compile(r"[㐀-鿿豈-﫿]")


def _bad(lang, s):
    if not s:
        return "empty"
    if KANA.search(s):
        return "kana"
    if lang in ("en", "de"):
        if CJK.search(s) or HANGUL.search(s):
            return "cjk/hangul in latin lang"
    if lang == "ko":
        if CJK.search(s):
            return "kanji in ko"
    if lang in ("zh", "tw"):
        if HANGUL.search(s):
            return "hangul in zh"
    return None


def main():
    master_path = sys.argv[1]
    out_paths = sys.argv[2:]
    with open(master_path, encoding="utf-8") as f:
        master = json.load(f)
    with open(TABLE, encoding="utf-8") as f:
        data = json.load(f)
    strings = data.setdefault("strings", {})

    ok = 0
    flagged = []
    for op in out_paths:
        with open(op, encoding="utf-8") as f:
            batch = json.load(f)
        bi = batch.get("by_index", batch)
        for idx_s, langs in bi.items():
            ja = master[int(idx_s)]
            entry = strings.setdefault(ja, {})
            good = {}
            for lang in ("en", "zh", "tw", "ko", "de"):
                val = (langs.get(lang) or "").strip()
                reason = _bad(lang, val)
                if reason:
                    flagged.append((os.path.basename(op), idx_s, lang, reason))
                    continue
                good[lang] = val
            if len(good) == 5:
                entry.update(good)
                ok += 1
            else:
                # 5 言語そろわないものは表に入れない(部分訳を残さない)
                flagged.append((os.path.basename(op), idx_s, "*", "incomplete (%d/5)" % len(good)))

    with open(TABLE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("merged %d complete entries; flagged %d" % (ok, len(flagged)))
    for f in flagged[:40]:
        print("  FLAG", f)


if __name__ == "__main__":
    main()
