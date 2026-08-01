"""Register every HALCON operator into a RAD corpus as an LLM-navigable wiki.

One markdown page per operator (name, chapter, description, typed Python signature
from the mvtec-halcon binding, version presence, imgevolve coverage), grouped by
HALCON's own chapter taxonomy — which is a better, authoritative grouping than
TF-IDF/k-means. Per-chapter SKILL.md pages and a top INDEX.md make it navigable
like the other `.claude/skills/corpus/` sources; `rad-research` greps it directly.

stdlib only — no sklearn/anthropic needed (the taxonomy replaces clustering, the
official descriptions replace LLM summarization).

    py -3.11 halcon_rad_ingest.py --out C:/dev/docs/halcon_operators_corpus
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def load(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def op_page(op, version, py, analogs, ver_presence, siblings):
    """One operator note. Obsidian-compatible: YAML frontmatter + [[wikilinks]] so
    the same file is a RAD corpus doc, an LLM-wiki page, AND a second-brain graph
    node (chapter MOC + name-family siblings + imgevolve analog form the edges)."""
    name = op["name"]
    chapters = op["chapters"] or ["(unclassified)"]
    covered = bool(analogs)
    fm = ["---",
          "tags: [halcon-operator, %s, %s]" % (slug(chapters[0]),
                                               "covered" if covered else "uncovered"),
          "halcon_version: %s" % version,
          "chapter: %s" % chapters[0],
          "covered: %s" % str(covered).lower(),
          "aliases: [%s]" % name,
          "---"]
    lines = fm + ["# %s" % name, "",
                  "> %s" % (op.get("short_desc") or "(no description)"), "",
                  "**Chapter:** [[_chapter_%s|%s]] · **HALCON:** %s (in: %s) · "
                  "**imgevolve:** %s" % (
                      slug(chapters[0]), chapters[0], version,
                      "/".join(ver_presence) if ver_presence else version,
                      ("covered via %s" % ", ".join("`%s`" % a for a in analogs)
                       if covered else "not yet mapped")),
                  ""]
    sig = py.get(name) if py else None
    if sig:
        lines += ["## Signature (mvtec-halcon Python binding)", "",
                  "```python", "%s(%s) %s" % (name, sig.get("params", ""), sig.get("ret", "")),
                  "```", ""]
    if siblings:
        lines += ["## Related operators", "",
                  " · ".join("[[%s]]" % s for s in siblings), ""]
    lines += ["## Reference", "", op["url"], "",
              "<!-- rad: halcon-operator source=mvtec version=%s chapter=%s covered=%s -->"
              % (version, slug(chapters[0]), covered)]
    return "\n".join(lines) + "\n"


def chapter_skill(chapter, ops, n_cov):
    """Chapter MOC (Map of Content): a second-brain hub note linking every operator."""
    cslug = slug(chapter)
    lines = ["---", "tags: [halcon-chapter]", "aliases: [_chapter_%s]" % cslug, "---",
             "# HALCON chapter: %s" % chapter, "",
             "%d operators (%d mapped in imgevolve). Each links to its own note; this is "
             "the chapter hub (MOC)." % (len(ops), n_cov), "",
             "## Operators", ""]
    for o in sorted(ops, key=lambda x: x["name"]):
        cov = " ✓" if o["_covered"] else ""
        lines.append("- [[%s]]%s — %s" % (o["name"], cov, (o.get("short_desc") or "")[:100]))
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    # _corpus_v2 suffix + root SKILL.md => discoverable by `raptor-rad-ingest --reindex`
    ap.add_argument("--out", default="C:/dev/docs/halcon_operators_corpus_v2")
    ap.add_argument("--operators", default=os.path.join(DATA, "halcon_operators.json"))
    a = ap.parse_args()

    data = load("halcon_operators.json")
    if not data:
        sys.stderr.write("run halcon_scrape.py first (no data/halcon_operators.json)\n")
        return 2
    py = load("halcon_pyapi.json") or {}
    versions = load("halcon_versions.json")
    version = data["version"]

    # imgevolve coverage: real op -> [registry op names]
    sys.path.insert(0, HERE)
    import ops as R
    analog = {}
    for o in R.REGISTRY:
        h = (o.halcon or "").strip()
        if h:
            analog.setdefault(h, []).append(o.name)

    # version presence per op name
    presence = {}
    if versions:
        sets = {v: set(s) for v, s in versions["opsets"].items()}
        for name in {op["name"] for op in data["operators"]}:
            presence[name] = [v for v in versions["versions"] if name in sets[v]]

    # group by primary (top-level) chapter
    by_chapter = {}
    for op in data["operators"]:
        op = dict(op)
        op["_covered"] = op["name"] in analog
        by_chapter.setdefault((op["chapters"] or ["(unclassified)"])[0], []).append(op)

    os.makedirs(a.out, exist_ok=True)
    n_pages = n_cov_total = 0
    index = ["# HALCON Operator Reference — RAD corpus (LLM wiki)", "",
             "Every HALCON %s operator as a navigable page, grouped by chapter. "
             "Source: MVTec Operator Reference. Signatures: `mvtec-halcon` binding. "
             "`✓` = mapped by an imgevolve registry op." % version, "",
             "| chapter | operators | mapped | folder |", "|---|---|---|---|"]
    for chapter in sorted(by_chapter):
        ops = by_chapter[chapter]
        cslug = slug(chapter)
        cdir = os.path.join(a.out, cslug)
        docdir = os.path.join(cdir, "docs")
        os.makedirs(docdir, exist_ok=True)
        n_cov = sum(1 for o in ops if o["_covered"])
        n_cov_total += n_cov
        # name-family index within the chapter: first token -> op names
        fam = {}
        for o in ops:
            fam.setdefault(o["name"].split("_", 1)[0], []).append(o["name"])
        for op in ops:
            head = op["name"].split("_", 1)[0]
            siblings = [s for s in sorted(fam.get(head, [])) if s != op["name"]][:8]
            page = op_page(op, version, py, analog.get(op["name"], []),
                           presence.get(op["name"], []), siblings)
            with open(os.path.join(docdir, slug(op["name"]) + ".md"), "w", encoding="utf-8") as fh:
                fh.write(page)
            n_pages += 1
        with open(os.path.join(cdir, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write(chapter_skill(chapter, ops, n_cov))
        index.append("| %s | %d | %d | `%s/` |" % (chapter, len(ops), n_cov, cslug))
    index += ["", "**%d operator pages across %d chapters — %d mapped in imgevolve.**"
              % (n_pages, len(by_chapter), n_cov_total), ""]
    with open(os.path.join(a.out, "INDEX.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(index))

    # root SKILL.md — RAD frontmatter so `raptor-rad-ingest --reindex` registers it
    today = datetime.date.today().isoformat()
    desc = ("HALCON %s Operator Reference as a per-operator RAD corpus / LLM wiki / "
            "Obsidian second-brain vault: %d operators across %d chapters, each with the "
            "typed mvtec-halcon binding signature, version-presence, and imgevolve coverage. "
            "Grouped by HALCON's own chapter taxonomy (authoritative, not TF-IDF)."
            % (version, n_pages, len(by_chapter)))
    skill = ["---", "name: halcon_operators_corpus", "description: %s" % desc,
             "metadata:", "  node_type: rad_corpus", "  type: reference",
             "  domain: machine-vision", "  collected: %s" % today,
             "  primary_source: %s" % data["source"], "---", "",
             "# HALCON Operator Reference (RAD corpus / second brain)", "",
             "> FullSense 内部 RAD 知識源。`rad-research` が grep で参照。各オペレータ = 1 ノート"
             "(YAML frontmatter + `[[wikilink]]`)。Obsidian vault としても開ける(chapter MOC "
             "+ name-family でグラフ化)。", "",
             "%d operators, %d chapters, %d mapped in imgevolve. Navigate via `INDEX.md` or the "
             "per-chapter `SKILL.md`." % (n_pages, len(by_chapter), n_cov_total), ""]
    skill += index[4:]  # reuse the chapter table + summary
    with open(os.path.join(a.out, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(skill))

    print("[rad-ingest] %d operator pages, %d chapters (%d mapped) -> %s"
          % (n_pages, len(by_chapter), n_cov_total, a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
