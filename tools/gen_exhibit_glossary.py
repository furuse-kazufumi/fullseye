#!/usr/bin/env python3
"""tools の抽出辞書から公開用語集 JSON を生成する。"""
from __future__ import annotations

import json

from exhibit_glossary import GLOSSARY, load_source

PUBLIC_KEYS = ("match", "ja", "en", "source", "review")


def build() -> dict:
    source = load_source()
    out = {}
    for term_id, entry in source.items():
        public = {k: entry[k] for k in PUBLIC_KEYS}
        # 将来の翻訳は ``de`` のような言語鍵を source に足せば、そのまま公開 JSON へ出す。
        public.update({k: v for k, v in entry.items()
                       if len(k) == 2 and k.isalpha() and k not in public})
        out[term_id] = public
    return out


def main() -> int:
    data = json.dumps(build(), ensure_ascii=False, indent=1) + "\n"
    GLOSSARY.parent.mkdir(parents=True, exist_ok=True)
    GLOSSARY.write_text(data, encoding="utf-8", newline="\n")
    print("wrote %d terms -> %s" % (len(build()), GLOSSARY))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
