# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Push the local overview articles (ja/en) to their published Qiita items — safely.

Why a tool and not a one-liner: the 2026-09-02/03 update replaced seven chronological
addenda with five functional chapters and grew the exhibits from 41 to 151, so the
new body is ~2x the live one and references ~30 images that only exist on GitHub
once the repo is pushed. The failure modes this guards against are all silent:

* a PATCH with images that 404 on raw.githubusercontent.com (assets not pushed yet,
  or a markdown typo such as a stray backtick glued to the URL) -> broken pictures;
* a body that SHRANK (wrong file, truncated read) -> content loss;
* a local path or scratch reference leaking into a public article;
* title / tags / private state silently changed by a PATCH that omits them.

Flow (memory rule "public→public PATCH is fast; private→public may 502"):
  1. GET the live item, save a full backup JSON next to the log;
  2. read the local markdown, run the checks (paths, image HEAD 200, size guard);
  3. PATCH {title, body, tags, private (unchanged), tweet: false};
  4. GET again and verify the body length matches what was sent.

Usage:
  py -3.11 tools/qiita_patch_overview.py --check          # checks only, no write
  py -3.11 tools/qiita_patch_overview.py --lang ja         # PATCH one
  py -3.11 tools/qiita_patch_overview.py --lang ja --lang en
  py -3.11 tools/qiita_patch_overview.py --allow-shrink    # only if you MEAN it

Token: ``~/.config/qiita-cli/credentials.json`` (``write_qiita`` scope). Never printed.
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
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS = {"ja": "ef0422b143a1a3f09f92", "en": "78e39b421211128f7b56"}
ARTICLE = os.path.join(REPO, "docs", "articles", "fullseye_overview_qiita_{lang}.md")
LOG_DIR = os.path.join(REPO, "out", "qiita_patch")
API = "https://qiita.com/api/v2/items/{id}"
RAW_RE = re.compile(r"https://raw\.githubusercontent\.com/[^\s)\"'<>`]+")
LEAK_RE = re.compile(r"[A-Za-z]:\\\\|[A-Za-z]:/dev/|/c/dev/|scratchpad|AppData\\\\|TODO\b|FIXME\b")


def _token() -> str:
    p = os.path.expanduser("~/.config/qiita-cli/credentials.json")
    creds = json.load(open(p, encoding="utf-8"))
    name = creds.get("default", "qiita")
    for c in creds["credentials"]:
        if c["name"] == name:
            return c["accessToken"]
    raise SystemExit("no qiita-cli credential named %r in %s" % (name, p))


def _req(method: str, url: str, tok: str, payload=None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, json.load(r)


def _head(u: str):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=30)
        return u, r.status
    except Exception as e:                 # noqa: BLE001 - reported, not swallowed
        return u, getattr(e, "code", str(e))


def check_body(body: str) -> list[str]:
    """Return a list of problems (empty == safe to publish)."""
    problems = []
    for i, line in enumerate(body.splitlines(), 1):
        if LEAK_RE.search(line):
            problems.append("line %d: local path / scratch / TODO leaked: %s" % (i, line[:100]))
    # a raw URL glued to a backtick or paren is a markdown typo that 404s on Qiita
    for m in re.finditer(r"https://raw\.githubusercontent\.com/\S+?\.(?:png|jpg|jpeg|gif|svg)`", body):
        problems.append("URL glued to a backtick (renders as a 404 link): %s" % m.group(0)[-80:])
    urls = sorted(set(RAW_RE.findall(body)))
    with cf.ThreadPoolExecutor(16) as ex:
        res = list(ex.map(_head, urls))
    bad = [(u, s) for u, s in res if s != 200]
    for u, s in bad:
        problems.append("image not reachable (%s): %s" % (s, u))
    print("  images referenced: %d, reachable: %d, unreachable: %d" % (len(urls), len(urls) - len(bad), len(bad)))
    return problems


def run(lang: str, do_patch: bool, allow_shrink: bool) -> int:
    tok = _token()
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    iid = ITEMS[lang]
    _, live = _req("GET", API.format(id=iid), tok)
    backup = os.path.join(LOG_DIR, "backup_%s_%s.json" % (lang, stamp))
    io.open(backup, "w", encoding="utf-8").write(json.dumps(live, ensure_ascii=False))
    print("[%s] live: %d chars, private=%s, tags=%s -> backup %s"
          % (lang, len(live["body"]), live["private"], [t["name"] for t in live["tags"]], backup))

    body = io.open(ARTICLE.format(lang=lang), encoding="utf-8").read()
    print("[%s] local: %d chars" % (lang, len(body)))
    problems = check_body(body)
    if len(body) < 0.9 * len(live["body"]) and not allow_shrink:
        problems.append("local body is >10%% SHORTER than the live one (%d < %d); pass --allow-shrink to override"
                        % (len(body), len(live["body"])))
    if problems:
        print("[%s] NOT publishing — %d problem(s):" % (lang, len(problems)))
        for p in problems:
            print("   -", p)
        return 2
    print("[%s] checks passed" % lang)
    if not do_patch:
        return 0

    payload = {"title": live["title"], "body": body,
               "tags": [{"name": t["name"], "versions": t.get("versions", [])} for t in live["tags"]],
               "private": live["private"], "tweet": False}
    status, _ = _req("PATCH", API.format(id=iid), tok, payload)
    _, after = _req("GET", API.format(id=iid), tok)
    ok = status == 200 and len(after["body"]) == len(body)
    print("[%s] PATCH %s -> live now %d chars (%s)" % (lang, status, len(after["body"]), "verified" if ok else "MISMATCH"))
    io.open(os.path.join(LOG_DIR, "patch_log.txt"), "a", encoding="utf-8").write(
        "%s %s status=%s sent=%d live_after=%d ok=%s\n" % (stamp, lang, status, len(body), len(after["body"]), ok))
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lang", action="append", choices=sorted(ITEMS), help="which article(s); default both")
    ap.add_argument("--check", action="store_true", help="run the checks only (no PATCH)")
    ap.add_argument("--allow-shrink", action="store_true")
    a = ap.parse_args(argv)
    rc = 0
    for lang in (a.lang or sorted(ITEMS)):
        rc = max(rc, run(lang, do_patch=not a.check, allow_shrink=a.allow_shrink))
    return rc


if __name__ == "__main__":
    sys.exit(main())
