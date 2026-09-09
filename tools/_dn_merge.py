#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DESIGN_NOTES 訳のバッチ merge ヘルパ(一時: i18n 作業用)。

使い方:
    py -3.11 tools/_dn_merge.py <batch.json>

batch.json = {"<index>": {"en":..,"zh":..,"tw":..,"ko":..,"de":..}, ...}
index は scratchpad の dn_untranslated.json(ユニーク未訳 ja 原文の配列)への添字。
その添字の ja 原文をキーに docs/i18n/design_notes.json の strings に訳を足す。
en が省略 or 原文と同一(英語原文コメント)の場合は en を書かない。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNTR = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.environ.get("DN_SCRATCH", ""), "dn_untranslated.json")
TABLE = os.path.join(ROOT, "docs", "i18n", "design_notes.json")
LANGS = ("en", "zh", "tw", "ko", "de")


def main():
    batch_path = sys.argv[1]
    with open(UNTR, encoding="utf-8") as f:
        untr = json.load(f)
    with open(batch_path, encoding="utf-8") as f:
        batch = json.load(f)
    with open(TABLE, encoding="utf-8") as f:
        data = json.load(f)
    strings = data.setdefault("strings", {})

    added = 0
    for idx_s, langs in batch.items():
        ja = untr[int(idx_s)]
        entry = strings.setdefault(ja, {})
        for lang in LANGS:
            val = langs.get(lang)
            if not val:
                continue
            if lang == "en" and val.strip() == ja.strip():
                continue  # 英語原文: en は原文のまま(訳さない)
            entry[lang] = val
        added += 1

    with open(TABLE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("merged %d entries -> %d total strings" % (added, len(strings)))


if __name__ == "__main__":
    main()
