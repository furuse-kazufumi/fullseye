#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Record the text every audited PoC figure draws, for the non-Japanese ViEW2026 story GIFs.

The PoC figures are drawn with Japanese labels.  The ViEW2026 pages in English, Chinese,
Korean, German, ... all show the ``en`` story GIF, so a figure whose title or axis says only
Japanese should not appear there.  Guessing that from the pixels is unreliable (no OCR is
available and small labels are easy to miss), so this tool **runs the PoC** and records the
exact strings it hands to the text renderer for each saved figure:

    py -3.11 tools/audit_view2026_figure_text.py                 # every PoC in AUDITED_POCS
    py -3.11 tools/audit_view2026_figure_text.py poc_tdi_linescan # one PoC
    py -3.11 tools/audit_view2026_figure_text.py --check          # ledger still matches the figures?

How the strings are captured (in a child process, figures written to a temporary folder,
never into the repo):

* ``PIL.ImageDraw.ImageDraw.text`` (every Fullseye label ends here), ``annotate.text_box`` and
  ``annotate.annotate_figure_grid`` (captions/title) are wrapped to append their text to a buffer.
* Every public ``examplefig.save*`` function is wrapped.  When the outermost call returns and the
  figure manifest has grown, the buffered strings are attributed to the new figure(s) and the
  buffer is cleared.

Limits (honest):

* Text drawn into an image that is **re-used** by a later figure is attributed only to the first
  figure saved after it was drawn.  The later figure could then look text-free here although it
  carries the label.  The story GIF frames chosen from this ledger are therefore also checked by
  eye at native size before publishing.
* Text that a later figure draws *before* an earlier figure is saved lands on the earlier figure
  (conservative: that figure is then classed as Japanese and not used).
* A figure the run did not produce (for example a real-data chapter without ``FULLSEYE_DATA_DIR``)
  is recorded as ``unaudited`` and is never used on the non-Japanese pages.

The ledger stores the SHA-256 of each repo figure.  The story GIF tool treats a figure whose
current bytes differ from the ledger as ``unaudited`` (fail-closed), and ``--check`` reports it so
the audit is re-run whenever a PoC figure is regenerated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "articles" / "assets" / "poc"
EXAMPLES = ROOT / "examples"
LEDGER = ROOT / "docs" / "view2026" / "figure_text.json"

#: The PoCs whose figures are audited: the featured story GIFs whose ``en`` version showed
#: Japanese labels (2026-11-23 review of the featured 30) plus the three motion exhibits that
#: gained a story GIF in the same change.
AUDITED_POCS = (
    "poc_industrial_oct",
    "poc_photoelasticity",
    "poc_cad_scan_deviation",
    "poc_fourier_ptychography",
    "poc_tdi_linescan",
    "poc_illumination_cone_vs_na",
    "poc_polarization_specular",
    "poc_moire_alignment",
    "poc_tem_ctf_thon_rings",
    "poc_solar_el_inspection",
    "poc_registration_basin",
    "poc_interferometry_step",
    "poc_lidar_terrain_change",
)

#: Hiragana, katakana (incl. half-width), CJK unified ideographs and the CJK punctuation block.
CJK_RE = re.compile("[　-〿぀-ヿㇰ-ㇿ㐀-䶿一-鿿"
                    "豈-﫿＀-￯]")
#: A Latin word of at least this many letters counts as English on a bilingual label.
MIN_LATIN_RUN = 3
LATIN_RUN_RE = re.compile("[A-Za-z]{%d,}" % MIN_LATIN_RUN)
#: Bilingual labels in the PoCs are written ``日本語 / English``.
BILINGUAL_SEPARATOR = "/"

#: Figure text classes.  ``none``: no string drawn; ``latin``: no CJK character in any string;
#: ``bilingual``: every string with CJK also carries a ``/``-separated segment with no CJK and an
#: English word; ``japanese``: at least one string has CJK and no such English segment;
#: ``unaudited``: the audit run did not produce this figure.
CLASS_NONE, CLASS_LATIN, CLASS_BILINGUAL, CLASS_JAPANESE, CLASS_UNAUDITED = (
    "none", "latin", "bilingual", "japanese", "unaudited")
#: Classes a non-Japanese page may show.
ENGLISH_READY = frozenset((CLASS_NONE, CLASS_LATIN, CLASS_BILINGUAL))

#: One PoC run may not take longer than this (the slowest audited PoC takes about 4 minutes).
RUN_TIMEOUT_S = 1800
#: Environment variable the child reads to know where to write its capture.
CHILD_OUT_ENV = "FULLSEYE_TEXT_AUDIT_OUT"
#: examplefig's output-folder variable (figures go to a temporary folder, never the repo).
FIGURE_DIR_ENV = "FULLSEYE_FIGURE_DIR"
#: Same folder as the PoCs use for real data; inherited from the caller when it is set.
DATA_DIR_ENV = "FULLSEYE_DATA_DIR"


#: Legend markers drawn in front of a series name (the katakana middle dot is a bullet there, not
#: Japanese text).  They are removed before a string is classified.
NON_TEXT_MARKS = "\u30fb"


def classify_string(text: str) -> str:
    """Class of one drawn string (``latin`` / ``bilingual`` / ``japanese``)."""
    text = text.translate({ord(c): " " for c in NON_TEXT_MARKS})
    if not CJK_RE.search(text):
        return CLASS_LATIN
    for part in text.split(BILINGUAL_SEPARATOR):
        if not CJK_RE.search(part) and LATIN_RUN_RE.search(part):
            return CLASS_BILINGUAL
    return CLASS_JAPANESE


def classify(texts: list[str] | None) -> str:
    """Class of one figure from every string drawn for it (``None`` = not produced)."""
    if texts is None:
        return CLASS_UNAUDITED
    strings = [t for t in texts if t.strip()]
    if not strings:
        return CLASS_NONE
    kinds = {classify_string(t) for t in strings}
    if CLASS_JAPANESE in kinds:
        return CLASS_JAPANESE
    return CLASS_BILINGUAL if CLASS_BILINGUAL in kinds else CLASS_LATIN


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- child

def _child(poc: Path, out_json: Path) -> int:
    """Run one PoC with the text hooks installed and write ``{figure file: [strings]}``."""
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    from PIL import ImageDraw

    import annotate
    import examplefig

    buffer: list[str] = []
    captured: dict[str, list[str]] = {}
    depth = [0]

    def note(value) -> None:
        if value is None:
            return
        if isinstance(value, (list, tuple)):
            for v in value:
                note(v)
            return
        buffer.append(str(value))

    pil_text = ImageDraw.ImageDraw.text

    def text(self, xy, txt, *args, **kwargs):
        note(txt)
        return pil_text(self, xy, txt, *args, **kwargs)

    ImageDraw.ImageDraw.text = text

    def wrap_note(module, name, *, fields):
        original = getattr(module, name, None)
        if original is None:
            return

        def wrapped(*args, **kwargs):
            for index, key in fields:
                if key in kwargs:
                    note(kwargs[key])
                elif index is not None and len(args) > index:
                    note(args[index])
            return original(*args, **kwargs)

        setattr(module, name, wrapped)

    wrap_note(annotate, "text_box", fields=((1, "text"),))
    wrap_note(annotate, "annotate_figure_grid", fields=((None, "captions"), (None, "title")))
    try:
        import fullseye
        for name in ("text_box", "annotate_figure_grid"):
            if hasattr(fullseye, name) and hasattr(annotate, name):
                setattr(fullseye, name, getattr(annotate, name))
    except ImportError:
        pass

    def wrap_save(name):
        original = getattr(examplefig, name)

        def wrapped(*args, **kwargs):
            before = len(examplefig._manifest)
            depth[0] += 1
            try:
                return original(*args, **kwargs)
            finally:
                depth[0] -= 1
                if depth[0] == 0:
                    for entry in examplefig._manifest[before:]:
                        captured[entry["file"]] = list(dict.fromkeys(buffer))
                    if len(examplefig._manifest) > before:
                        buffer.clear()

        setattr(examplefig, name, wrapped)

    for name in sorted(n for n in dir(examplefig) if n.startswith("save") and
                       callable(getattr(examplefig, n))):
        wrap_save(name)

    sys.argv = [str(poc)]
    code = 0
    try:
        runpy.run_path(str(poc), run_name="__main__")
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    out_json.write_text(json.dumps({"exit_code": code, "figures": captured},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


# --------------------------------------------------------------------------- parent

def _load_ledger() -> dict:
    if LEDGER.is_file():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {}


def audit(pid: str) -> dict:
    """Run one PoC in a child process and return its ledger entry."""
    poc = EXAMPLES / ("%s.py" % pid)
    folder = ASSETS / pid
    if not poc.is_file() or not (folder / "figures.json").is_file():
        raise SystemExit("PoC or its figures.json is missing: %s" % pid)
    with tempfile.TemporaryDirectory(prefix="fs_text_audit_") as tmp:
        tmp_path = Path(tmp)
        out_json = tmp_path / "capture.json"
        env = dict(os.environ)
        env[FIGURE_DIR_ENV] = str(tmp_path / "figures")
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--child", str(poc),
                               str(out_json)], cwd=str(ROOT), env=env, timeout=RUN_TIMEOUT_S,
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if proc.returncode != 0 or not out_json.is_file():
            tail = proc.stderr.decode("utf-8", "replace")[-2000:]
            raise SystemExit("audit run failed for %s (exit %s):\n%s" % (pid, proc.returncode, tail))
        capture = json.loads(out_json.read_text(encoding="utf-8"))
        if capture["exit_code"] != 0:
            raise SystemExit("%s exited with %s during the audit run" % (pid, capture["exit_code"]))
        run_dir = tmp_path / "figures"
        figures = json.loads((folder / "figures.json").read_text(encoding="utf-8"))
        rows = {}
        for row in figures:
            name = row["file"]
            repo_file = folder / name
            if not repo_file.is_file():
                continue
            texts = capture["figures"].get(name)
            run_file = run_dir / name
            rows[name] = {
                "class": classify(texts),
                "sha256": sha256_file(repo_file),
                "same_bytes_as_audit_run": run_file.is_file() and
                sha256_file(run_file) == sha256_file(repo_file),
                "japanese_strings": [t for t in (texts or []) if classify_string(t) == CLASS_JAPANESE],
            }
    return {"poc": poc.relative_to(ROOT).as_posix(),
            "data_dir_set": bool(os.environ.get(DATA_DIR_ENV, "").strip()),
            "figures": rows}


def write_ledger(entries: dict) -> None:
    ledger = {"_": "Generated by tools/audit_view2026_figure_text.py; do not edit.",
              "schema": 1,
              "classes": {CLASS_NONE: "no text drawn", CLASS_LATIN: "no CJK character",
                          CLASS_BILINGUAL: "every CJK string has a '/'-separated English part",
                          CLASS_JAPANESE: "some string is Japanese only",
                          CLASS_UNAUDITED: "the audit run did not produce this figure"},
              "english_ready": sorted(ENGLISH_READY),
              "min_latin_run": MIN_LATIN_RUN,
              "entries": {k: entries[k] for k in sorted(entries)}}
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1) + "\n",
                      encoding="utf-8", newline="\n")


def stale(ledger: dict) -> list[str]:
    """Figures whose current bytes differ from the audit, plus audited PoCs missing from it."""
    out = []
    entries = ledger.get("entries", {})
    for pid in AUDITED_POCS:
        if pid not in entries:
            out.append("%s: not audited" % pid)
            continue
        for name, row in entries[pid]["figures"].items():
            path = ASSETS / pid / name
            if not path.is_file():
                out.append("%s/%s: missing" % (pid, name))
            elif sha256_file(path) != row["sha256"]:
                out.append("%s/%s: changed since the audit" % (pid, name))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pocs", nargs="*", help="PoC ids (default: every id in AUDITED_POCS)")
    ap.add_argument("--check", action="store_true", help="only verify the ledger is current")
    ap.add_argument("--child", nargs=2, metavar=("POC", "OUT_JSON"), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.child:
        return _child(Path(args.child[0]), Path(args.child[1]))
    if args.check:
        problems = stale(_load_ledger())
        for line in problems:
            print(line)
        print("figure text ledger: %s" % ("stale (%d)" % len(problems) if problems else "current"))
        return 1 if problems else 0
    unknown = [p for p in args.pocs if p not in AUDITED_POCS]
    if unknown:
        raise SystemExit("not in AUDITED_POCS: %s" % unknown)
    entries = dict(_load_ledger().get("entries", {}))
    for pid in args.pocs or AUDITED_POCS:
        entries[pid] = audit(pid)
        counts: dict[str, int] = {}
        for row in entries[pid]["figures"].values():
            counts[row["class"]] = counts.get(row["class"], 0) + 1
        print("%s: %s" % (pid, ", ".join("%s %d" % kv for kv in sorted(counts.items()))))
        write_ledger(entries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
