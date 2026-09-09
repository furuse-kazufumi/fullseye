#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DESIGN_NOTES 訳のバッチ merge ヘルパ(一時: i18n 作業用)。

使い方:
    py -3.11 tools/_dn_merge.py <batch.json> [untranslated.json]

batch.json は次の 2 形式を混在可:
    {"by_index": {"<idx>": {langs}}, "by_text": {"<exact source text>": {langs}}}
  もしくは後方互換で {"<idx>": {langs}} (= by_index のみ)。
idx は untranslated.json(ユニーク未訳 ja 原文の配列)への添字。
langs = {"ja":.., "en":.., "zh":.., "tw":.., "ko":.., "de":..} の必要な分だけ。
en は原文と同一(英語原文)のとき書かない。ja は英語原文の日本語版に使う。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = os.path.join(ROOT, "docs", "i18n", "design_notes.json")
LANGS = ("ja", "en", "zh", "tw", "ko", "de")


def _apply(strings, key_text, langs):
    entry = strings.setdefault(key_text, {})
    for lang in LANGS:
        val = langs.get(lang)
        if not val:
            continue
        if lang == "en" and val.strip() == key_text.strip():
            continue  # 英語原文: en は原文のまま
        entry[lang] = val


def main():
    batch_path = sys.argv[1]
    untr_path = sys.argv[2] if len(sys.argv) > 2 else None
    with open(batch_path, encoding="utf-8") as f:
        batch = json.load(f)
    with open(TABLE, encoding="utf-8") as f:
        data = json.load(f)
    strings = data.setdefault("strings", {})

    by_index = batch.get("by_index")
    by_text = batch.get("by_text")
    if by_index is None and by_text is None:
        by_index = batch  # 後方互換: フラット = by_index

    added = 0
    if by_index:
        with open(untr_path, encoding="utf-8") as f:
            untr = json.load(f)
        for idx_s, langs in by_index.items():
            _apply(strings, untr[int(idx_s)], langs)
            added += 1
    if by_text:
        for text, langs in by_text.items():
            _apply(strings, text, langs)
            added += 1

    with open(TABLE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("merged %d entries -> %d total strings" % (added, len(strings)))


if __name__ == "__main__":
    main()
