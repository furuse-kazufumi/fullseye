# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC 展示館の記事(ja / en)を Qiita へ **限定共有**で投稿 / 更新する。

    py -3.11 tools/qiita_post_poc.py --check                 # 検査だけ(書かない)
    py -3.11 tools/qiita_post_poc.py --lang ja --lang en     # 未投稿なら POST(private)、投稿済なら PATCH
    py -3.11 tools/qiita_post_poc.py --lang ja --public      # 限定共有 → 公開(明示したときだけ)

正本は ``docs/articles/fullseye_poc_museum_qiita_<lang>.md``(``tools/gen_wingpoc_gallery.py``
の生成物)。投稿した item id は ``docs/articles/exhibits/qiita_items.json`` に残し、2 回目
以降は同じ item を PATCH する(新規を量産しない)。

fail-closed の検査(``tools/qiita_patch_overview.py`` と同じ思想):

* 本文にローカルパス / scratchpad / TODO が混ざっていたら止める。
* 画像の raw URL を全部 HEAD して 200 でなければ止める(push 前に投稿すると壊れた
  画像で公開されるため)。
* PATCH で本文が縮むときは ``--allow-shrink`` が無ければ止める。
* ``private`` は既定 True。公開へ倒すのは ``--public`` を明示したときだけ
  (限定共有 → 公開の遷移は 502 を返すことがある: raptor memory
  ``reference_qiita_large_article_publish_502``。その場合は Qiita の画面から公開する)。

トークンは ``~/.config/qiita-cli/credentials.json``(write_qiita)。**絶対に印字しない**。
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLE = os.path.join(REPO, "docs", "articles", "fullseye_poc_museum_qiita_{lang}.md")
CAPTIONS = os.path.join(REPO, "docs", "articles", "exhibits", "poc_captions.json")
ITEMS_FILE = os.path.join(REPO, "docs", "articles", "exhibits", "qiita_items.json")
LOG_DIR = os.path.join(REPO, "out", "qiita_post_poc")
API_ITEMS = "https://qiita.com/api/v2/items"
RAW_RE = re.compile(r"https://raw\.githubusercontent\.com/[^\s)\"'<>`]+")
LEAK_RE = re.compile(r"[A-Za-z]:\\|[A-Za-z]:/dev/|/c/dev/|scratchpad|AppData\\|TODO\b|FIXME\b")


def _token() -> str:
    p = os.path.expanduser("~/.config/qiita-cli/credentials.json")
    creds = json.load(open(p, encoding="utf-8"))
    name = creds.get("default", "qiita")
    for c in creds["credentials"]:
        if c["name"] == name:
            return c["accessToken"]
    raise SystemExit("no qiita-cli credential named %r in %s" % (name, p))


def _req(method: str, url: str, tok: str, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


def _head(u: str):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=30)
        return u, r.status
    except urllib.error.HTTPError as e:
        return u, e.code
    except Exception as e:                                        # noqa: BLE001
        return u, str(e)


def check_body(body: str) -> list[str]:
    errs = []
    for m in LEAK_RE.finditer(body):
        errs.append("leak: %r" % body[max(0, m.start() - 30):m.end() + 30])
    urls = sorted(set(RAW_RE.findall(body)))
    with cf.ThreadPoolExecutor(8) as ex:
        for u, st in ex.map(_head, urls):
            if st != 200:
                errs.append("image %s -> %s" % (u, st))
    print("  images: %d (all 200)" % len(urls) if not any(e.startswith("image") for e in errs)
          else "  images: %d (%d broken)" % (len(urls), sum(e.startswith("image") for e in errs)))
    return errs


def _items() -> dict:
    if os.path.exists(ITEMS_FILE):
        return json.load(open(ITEMS_FILE, encoding="utf-8"))
    return {}


def _save_items(d: dict) -> None:
    io.open(ITEMS_FILE, "w", encoding="utf-8", newline="\n").write(
        json.dumps(d, ensure_ascii=False, indent=1) + "\n")


def run(lang: str, write: bool, public: bool, allow_shrink: bool) -> int:
    cap = json.load(open(CAPTIONS, encoding="utf-8"))
    title = cap["meta"]["title_" + lang]
    tags = [{"name": t, "versions": []} for t in cap["meta"].get("qiita_tags", ["画像処理", "Python"])]
    body = io.open(ARTICLE.format(lang=lang), encoding="utf-8").read()
    print("[%s] local: %d chars, title=%r" % (lang, len(body), title))
    errs = check_body(body)
    if errs:
        print("\n".join("  ! " + e for e in errs))
        return 2
    if not write:
        print("[%s] check only - nothing written" % lang)
        return 0
    tok = _token()
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    items = _items()
    cur = items.get(lang)
    if cur:
        live = _req("GET", API_ITEMS + "/" + cur["id"], tok)
        backup = os.path.join(LOG_DIR, "%s-%s-backup.json" % (lang, stamp))
        io.open(backup, "w", encoding="utf-8").write(json.dumps(live, ensure_ascii=False, indent=1))
        print("[%s] live: %d chars, private=%s -> backup %s" % (lang, len(live["body"]), live["private"], backup))
        if len(body) < len(live["body"]) and not allow_shrink:
            print("[%s] ! body would SHRINK (%d -> %d); pass --allow-shrink if intended"
                  % (lang, len(live["body"]), len(body)))
            return 3
        private = (live["private"] and not public)
        res = _req("PATCH", API_ITEMS + "/" + cur["id"], tok,
                   {"title": title, "body": body, "tags": tags, "private": private, "tweet": False})
        verb = "patched"
    else:
        res = _req("POST", API_ITEMS, tok,
                   {"title": title, "body": body, "tags": tags, "private": not public, "tweet": False})
        verb = "posted"
    items[lang] = {"id": res["id"], "url": res["url"], "private": res["private"],
                   "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    _save_items(items)
    back = _req("GET", API_ITEMS + "/" + res["id"], tok)
    ok = len(back["body"]) == len(body)
    print("[%s] %s -> %s (private=%s, %d chars, verify %s)"
          % (lang, verb, res["url"], res["private"], len(back["body"]), "ok" if ok else "MISMATCH"))
    return 0 if ok else 4


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", action="append", choices=["ja", "en"])
    ap.add_argument("--check", action="store_true", help="検査だけ(書かない)")
    ap.add_argument("--public", action="store_true", help="限定共有ではなく公開にする(明示時のみ)")
    ap.add_argument("--allow-shrink", action="store_true")
    a = ap.parse_args(argv)
    langs = a.lang or ["ja", "en"]
    rc = 0
    for lang in langs:
        rc = max(rc, run(lang, write=not a.check, public=a.public, allow_shrink=a.allow_shrink))
    return rc


if __name__ == "__main__":
    sys.exit(main())
