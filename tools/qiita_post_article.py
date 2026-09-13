# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``docs/articles/<stem>_<lang>.md`` の記事を Qiita へ **限定共有**で投稿 / 更新する。

    py -3.11 tools/qiita_post_article.py --stem qiita_flybrain_closedloop --check
    py -3.11 tools/qiita_post_article.py --stem qiita_flybrain_closedloop --lang ja --lang en
    py -3.11 tools/qiita_post_article.py --stem qiita_flybrain_closedloop --lang ja --public

``tools/qiita_post_poc.py`` は PoC 展示館 1 本、``tools/qiita_patch_overview.py`` は総集編
1 本に固定されている。**記事が増えるたびに投稿器を写経するのをやめる**ためにこれを置く ——
記事の stem を渡せば同じ検査・同じ item 追跡で投稿できる。

正本は ``docs/articles/<stem>_<lang>.md``(手書き)。**題は本文の最初の見出し**から取る
(記事とタイトルが黙ってずれるのを防ぐため、別の場所に題を書かない)。タグと投稿済み
item id は ``docs/articles/qiita_articles.json`` に記録し、2 回目以降は同じ item を PATCH
する(新規を量産しない)。

fail-closed の検査(``qiita_post_poc.py`` と同じ思想):

* 本文にローカルパス / scratchpad / TODO が混ざっていたら止める。
* 画像の raw URL を全部 HEAD して 200 でなければ止める(push 前に投稿すると壊れた画像で
  公開されるため)。
* PATCH で本文が縮むときは ``--allow-shrink`` が無ければ止める。
* ``private`` は既定 True。公開へ倒すのは ``--public`` を明示したときだけ。

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
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES = os.path.join(REPO, "docs", "articles")
REGISTRY = os.path.join(ARTICLES, "qiita_articles.json")
LOG_DIR = os.path.join(REPO, "out", "qiita_post_article")
API_ITEMS = "https://qiita.com/api/v2/items"
RAW_RE = re.compile(r"https://raw\.githubusercontent\.com/[^\s)\"'<>`]+")
LEAK_RE = re.compile(r"[A-Za-z]:\\|[A-Za-z]:/dev/|/c/dev/|scratchpad|AppData\\|TODO\b|FIXME\b")
DEFAULT_TAGS = ["Python", "機械学習"]


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


def article_path(stem: str, lang: str) -> str:
    return os.path.join(ARTICLES, "%s_%s.md" % (stem, lang))


def title_of(body: str) -> str:
    """本文の最初の見出し = 題。見出しが無ければ止める(題を推測しない)。"""
    for line in body.splitlines():
        t = line.strip()
        if t.startswith("# "):
            return t[2:].strip()
    raise SystemExit("no '# ' heading found - the article must carry its own title")


def check_body(body: str) -> list[str]:
    errs = []
    for m in LEAK_RE.finditer(body):
        errs.append("leak: %r" % body[max(0, m.start() - 30):m.end() + 30])
    urls = sorted(set(RAW_RE.findall(body)))
    broken = 0
    with cf.ThreadPoolExecutor(8) as ex:
        for u, st in ex.map(_head, urls):
            if st != 200:
                errs.append("image %s -> %s" % (u, st))
                broken += 1
    print("  images: %d (%s)" % (len(urls), "all 200" if not broken else "%d broken" % broken))
    return errs


def _registry() -> dict:
    if os.path.exists(REGISTRY):
        return json.load(open(REGISTRY, encoding="utf-8"))
    return {}


def _save_registry(d: dict) -> None:
    io.open(REGISTRY, "w", encoding="utf-8", newline="\n").write(
        json.dumps(d, ensure_ascii=False, indent=1) + "\n")


def run(stem: str, lang: str, write: bool, public: bool, allow_shrink: bool) -> int:
    path = article_path(stem, lang)
    if not os.path.exists(path):
        print("! no such article: %s_%s.md" % (stem, lang))
        return 2
    body = io.open(path, encoding="utf-8").read()
    title = title_of(body)
    reg = _registry()
    entry = reg.setdefault(stem, {"tags": DEFAULT_TAGS, "items": {}})
    tags = [{"name": t, "versions": []} for t in entry.get("tags", DEFAULT_TAGS)]
    print("[%s/%s] local: %d chars, title=%r" % (stem, lang, len(body), title))
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
    cur = entry["items"].get(lang)
    if cur:
        live = _req("GET", API_ITEMS + "/" + cur["id"], tok)
        backup = os.path.join(LOG_DIR, "%s-%s-%s-backup.json" % (stem, lang, stamp))
        io.open(backup, "w", encoding="utf-8").write(json.dumps(live, ensure_ascii=False, indent=1))
        print("[%s] live: %d chars, private=%s -> backup %s"
              % (lang, len(live["body"]), live["private"], backup))
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
    entry["items"][lang] = {
        "id": res["id"], "url": res["url"], "private": res["private"],
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    _save_registry(reg)
    back = _req("GET", API_ITEMS + "/" + res["id"], tok)
    ok = len(back["body"]) == len(body)
    print("[%s] %s -> %s (private=%s, %d chars, verify %s)"
          % (lang, verb, res["url"], res["private"], len(back["body"]), "ok" if ok else "MISMATCH"))
    return 0 if ok else 4


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stem", required=True, help="docs/articles/<stem>_<lang>.md")
    ap.add_argument("--lang", action="append", help="ja / en / ... (default: both ja and en)")
    ap.add_argument("--check", action="store_true", help="検査だけ(書かない)")
    ap.add_argument("--public", action="store_true", help="限定共有ではなく公開にする(明示時のみ)")
    ap.add_argument("--allow-shrink", action="store_true")
    a = ap.parse_args(argv)
    rc = 0
    for lang in (a.lang or ["ja", "en"]):
        rc = run(a.stem, lang, not a.check, a.public, a.allow_shrink) or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
