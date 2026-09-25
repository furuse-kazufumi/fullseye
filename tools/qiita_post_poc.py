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


#: 既定で投稿する記事の種類。★手書きの `external` は**名指ししたときだけ**扱う —— 引数無しの
#: 一括投稿が、生成物でない記事(数学の回など)を巻き込まないようにする。
DEFAULT_KINDS = ("index", "generated")


def _parts(cap: dict, kinds=DEFAULT_KINDS) -> list:
    """投稿できる記事。既定は案内 + 生成された棟で、手書きの `external` は入らない。"""
    return [p for p in cap["meta"].get("parts", [{"id": "entrance", "kind": "index"}])
            if p["kind"] in kinds]


def _slot(part: dict, lang: str) -> str:
    """`qiita_items.json` の鍵。

    ★案内は `ja` / `en` のまま据え置く —— 既存の枠がその鍵で記録されており、
    変えると同じ記事に PATCH できず**新しい記事を量産**してしまう。
    """
    return lang if part["kind"] == "index" else "%s.%s" % (part["id"], lang)


def _body_path(part: dict, lang: str) -> str:
    if part["kind"] == "index":
        return ARTICLE.format(lang=lang)
    if part["kind"] == "external":
        #: 手書きの記事は生成物でないので、原稿の名前を台帳から引く。
        return os.path.join(REPO, "docs", "articles", part["article_" + lang])
    return os.path.join(REPO, "docs", "articles",
                        "fullseye_poc_museum_%s_qiita_%s.md" % (part["slug"], lang))


def run(lang: str, write: bool, public: bool, allow_shrink: bool, part=None) -> int:
    cap = json.load(open(CAPTIONS, encoding="utf-8"))
    part = part or _parts(cap)[0]
    title = part.get("title_" + lang) or cap["meta"]["title_" + lang]
    tags = [{"name": t, "versions": []} for t in cap["meta"].get("qiita_tags", ["画像処理", "Python"])]
    body = io.open(_body_path(part, lang), encoding="utf-8").read()
    slot = _slot(part, lang)
    lang = slot   # 以後のログと鍵は記事単位で引く
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
    ap.add_argument("--part", action="append",
                    help="投稿する記事の id(既定 = 案内と全部の棟)。手書きの記事は名指ししたときだけ")
    ap.add_argument("--check", action="store_true", help="検査だけ(書かない)")
    ap.add_argument("--public", action="store_true", help="限定共有ではなく公開にする(明示時のみ)")
    ap.add_argument("--allow-shrink", action="store_true")
    a = ap.parse_args(argv)
    langs = a.lang or ["ja", "en"]
    cap = json.load(open(CAPTIONS, encoding="utf-8"))
    parts = _parts(cap)
    if a.part:
        #: 名指しされたときだけ手書きの記事も候補に入れる。
        parts = _parts(cap, kinds=DEFAULT_KINDS + ("external",))
        want = set(a.part)
        known = {p["id"] for p in parts}
        bad = sorted(want - known)
        if bad:
            print("そんな記事は無い: %s(在るのは %s)" % (", ".join(bad), ", ".join(sorted(known))))
            return 2
        parts = [p for p in parts if p["id"] in want]
    rc = 0
    for part in parts:
        for lang in langs:
            rc = max(rc, run(lang, write=not a.check, public=a.public,
                             allow_shrink=a.allow_shrink, part=part))
    return rc


if __name__ == "__main__":
    sys.exit(main())
