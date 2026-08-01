"""Scrape the MVTec HALCON operator reference into a local JSON catalog.

Replaces the hand-curated ~63-operator guess in halcon_coverage.py with the real
operator set mined from MVTec's public operator reference (~2380 ops). stdlib only.

Output (default `data/halcon_operators.json`) drives `halcon_coverage.py`, which
measures imgevolve's `Op.halcon` analogues against the *real* reference instead of
memory. Re-run when bumping the HALCON version.

    py -3.11 halcon_scrape.py --version 2311 --out data/halcon_operators.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (imgevolve halcon-catalog; research)"}
# href pages that are navigation / infrastructure, never operators.
_NON_OP = {"index", "index_by_name", "legal_notes"}
# an operator page href: lowercase/digit/underscore token + .html
_OP_RE = re.compile(r'href="([a-z0-9_]+)\.html"')
# precise operator entry in index_by_name.html: <dt><a href="name.html">
_DT_RE = re.compile(r'<dt><a href="([a-z0-9_]+)\.html">')
# name/description pairing in the alphabetical index
_DESC_RE = re.compile(r'<dt><a href="([a-z0-9_]+)\.html">.*?</dt>\s*<dd>(.*?)</dd>', re.S)
# chapter TOC pages
_TOC_RE = re.compile(r"toc_[a-z0-9_]+\.html")
# chapter title map from index.html: <a href="toc_x.html">Title</a>
_TITLE_RE = re.compile(r'<a href="(toc_[a-z0-9_]+)\.html">([^<]+)</a>')
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def fetch(url, retries=3, timeout=30):
    last = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last = "%s: %s" % (type(e).__name__, e)
            time.sleep(1.5 * (attempt + 1))
    sys.stderr.write("  [warn] failed %s: %s\n" % (url, last))
    return ""


def op_pages(html):
    """All operator-page names referenced in `html` (minus navigation pages)."""
    return {n for n in _OP_RE.findall(html) if n not in _NON_OP}


def descriptions(index_html, ops):
    """Map operator name -> short description from index_by_name.html."""
    out = {}
    for name, raw in _DESC_RE.findall(index_html):
        if name in ops:
            out[name] = _WS_RE.sub(" ", _TAG_RE.sub("", raw)).strip()
    return out


def clean_title(raw):
    """'1D Measuring (...)' -> '1D Measuring'."""
    return _WS_RE.sub(" ", raw.replace("(...)", "")).strip()


def top_level_parent(toc, tops):
    """Roll a (possibly nested) toc name up to its top-level chapter toc.

    `tops` = set of top-level toc names (e.g. 'toc_filters'). A sub-chapter
    'toc_filters_smoothing' rolls up to 'toc_filters'. Longest match wins.
    """
    best = ""
    for t in tops:
        if toc == t or toc.startswith(t + "_"):
            if len(t) > len(best):
                best = t
    return best or toc


def scrape(version, pause, log):
    base = "https://www.mvtec.com/doc/halcon/%s/en/" % version
    log("[1/3] operator index: %sindex_by_name.html" % base)
    idx = fetch(base + "index_by_name.html")
    if not idx:
        raise SystemExit("could not fetch index_by_name.html -- aborting")
    ops = set(_DT_RE.findall(idx))
    log("      operators found: %d" % len(ops))
    desc = descriptions(idx, ops)
    log("      descriptions parsed: %d/%d" % (len(desc), len(ops)))

    log("[2/3] chapter titles + TOC list: %sindex.html" % base)
    index_html = fetch(base + "index.html")
    titles = {toc: clean_title(t) for toc, t in _TITLE_RE.findall(index_html)}
    tocs = sorted(set(_TOC_RE.findall(index_html)))
    tops = {t[:-5] for t in tocs if t[:-5].count("_") == 1}  # strip '.html'
    log("      chapters (all TOCs): %d   top-level: %d" % (len(tocs), len(tops)))

    log("[3/3] per-chapter membership (rolled up to top-level)")
    op_chapters = {o: set() for o in ops}
    chapter_ops = {}  # top-level label -> set of ops
    for i, toc in enumerate(tocs, 1):
        html = fetch(base + toc)
        parent = top_level_parent(toc[:-5], tops)
        label = titles.get(parent) or titles.get(toc[:-5]) or parent
        members = op_pages(html) & ops
        bucket = chapter_ops.setdefault(label, set())
        for o in members:
            op_chapters[o].add(label)
            bucket.add(o)
        if i % 20 == 0 or i == len(tocs):
            log("      %3d/%d tocs scanned" % (i, len(tocs)))
        if pause:
            time.sleep(pause)

    orphans = sorted(o for o in ops if not op_chapters[o])
    operators = [
        {"name": o, "chapters": sorted(op_chapters[o]),
         "url": "%s%s.html" % (base, o), "short_desc": desc.get(o, "")}
        for o in sorted(ops)
    ]
    return {
        "version": version, "source": base, "n_operators": len(ops),
        "n_chapters": len(tocs), "n_top_level": len(tops),
        "chapters": {k: len(v) for k, v in sorted(chapter_ops.items())},
        "orphan_operators": orphans,
        "desc_coverage": "%d/%d" % (len(desc), len(ops)),
        "operators": operators,
    }


def op_set(version):
    """Just the operator-name set for one version (1 request, no toc walk)."""
    base = "https://www.mvtec.com/doc/halcon/%s/en/" % version
    idx = fetch(base + "index_by_name.html")
    if not idx:
        raise SystemExit("could not fetch index_by_name.html for v%s" % version)
    return sorted(set(_DT_RE.findall(idx)))


def scrape_op_sets(versions, log):
    """Multi-version operator-name snapshot for version-drift analysis.

    HALCON's operator set changes between releases (e.g. bilateral_filter and
    guided_filter appear from 13 onward, not in 12). Capturing several versions
    lets coverage tell 'name never existed' (real error) apart from 'exists in
    other versions' (version drift) — honest disclosure across releases.
    """
    opsets = {}
    for v in versions:
        opsets[v] = op_set(v)
        log("  v%-6s ops=%d" % (v, len(opsets[v])))
    union = sorted(set().union(*[set(s) for s in opsets.values()])) if opsets else []
    return {"versions": versions, "counts": {v: len(s) for v, s in opsets.items()},
            "n_union": len(union), "opsets": opsets}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", default="2311", help="HALCON docs version, e.g. 2311")
    ap.add_argument("--out", default=os.path.join(HERE, "data", "halcon_operators.json"))
    ap.add_argument("--pause", type=float, default=0.15, help="seconds between requests")
    ap.add_argument("--op-sets", action="store_true",
                    help="snapshot operator-name sets across --versions (no toc walk)")
    ap.add_argument("--versions", default="12,13,2311,2411",
                    help="comma list of versions for --op-sets")
    ap.add_argument("--opsets-out", default=os.path.join(HERE, "data", "halcon_versions.json"))
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    def log(m):
        if not a.quiet:
            sys.stderr.write(m + "\n")

    if a.op_sets:
        vers = [v.strip() for v in a.versions.split(",") if v.strip()]
        log("[op-sets] snapshotting %d versions" % len(vers))
        snap = scrape_op_sets(vers, log)
        os.makedirs(os.path.dirname(a.opsets_out), exist_ok=True)
        with open(a.opsets_out, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, ensure_ascii=False)
        log("[ok] union=%d across %s -> %s" % (snap["n_union"], vers, a.opsets_out))
        print(a.opsets_out)
        return 0

    data = scrape(a.version, a.pause, log)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    log("[ok] %d operators, %d top-level chapters -> %s"
        % (data["n_operators"], data["n_top_level"], a.out))
    print(a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
