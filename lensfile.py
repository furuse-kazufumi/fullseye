# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lensfile — read and write sequential lens prescriptions in the ``.zmx`` text format.

``.zmx`` is the plain-text prescription format that commercial sequential
optical-design programs save and exchange (one keyword per line: ``SURF``,
``CURV``, ``DISZ``, ``GLAS`` ...). This module turns such a file into the
prescription every other optics op already consumes — ``raytrace.lens_system``
— and writes one back, so a design can travel both ways between Fullseye and a
design program. Glass catalogues in the companion ``.agf`` format are read by
``materials.read_glass_catalog_agf`` (point ``glass_dir`` or the environment
variable ``FULLSEYE_GLASS_DIR`` at your own catalogue files; none are bundled).

The ops::

    lens_file_read(source)          -> prescription  (system + fields + wavelengths + report)
    lens_file_system(prescription)  -> raytrace.lens_system at one field / wavelength
    lens_file_write(prescription)   -> .zmx text (optionally the geometry of an edited system)
    lens_file_report(source)        -> keyword inventory: read / ignored / unsupported

(``MNUM`` multi-configuration tables are read into ``system["configurations"]`` and written back from it.)

**Fail-closed.** Every keyword in the file is classified as *read* (it changes
the model), *ignored* (it cannot change a sequential real-ray trace: display
settings, coatings, tolerance and merit-function rows, mechanical sizes) or
*unsupported* (it would change the geometry or the rays and Fullseye cannot
represent it). An unsupported item refuses the import with a message naming the
surface and the keyword. A few items have an honest approximation; they are
imported only with ``allow_partial=True`` and the result then carries
``approximate=True`` and lists each approximation. Nothing is dropped silently.

Supported (exact): surface types ``STANDARD`` (sphere / conic) and ``EVENASPH``
(``PARM 2..9`` = r⁴ … r¹⁸; a non-zero r² term ``PARM 1`` is refused), mirrors
(``GLAS MIRROR``; the signed thicknesses after a mirror become the positive
travel distances ``raytrace`` expects), the stop, units ``MM / CM / IN / METER``
(converted to mm, aspheric coefficients by their own power of the scale), the
aperture types entrance-pupil diameter (``ENPD``), image-space F/# (``FNUM``)
and float-by-stop-size (``FLOA``), field types angle (``FTYP 0``), object height
(``FTYP 1``) and paraxial image height (``FTYP 2``, converted through the
paraxial chief ray), up to 12 fields with weights, wavelengths (``WAVM`` /
``WAVL``) with weights and the primary one (``PWAV``), surface apertures
(``CLAP`` / ``FLAP`` → ``ap``), the per-field vignetting factors
(``VDXN`` / ``VDYN`` / ``VCXN`` / ``VCYN`` / ``VANN`` → ``system["vignetting"]``, applied by
``raytrace`` as a pupil decentre / compression, and written back), glasses by catalogue name (Fullseye's material
table or your ``.agf`` files — the file's own n_d is checked against the
catalogue to 5e-4, so a same-named glass from another maker is refused), model
glasses (``___BLANK``: n_d, V_d), six-digit glass codes and constant indices.
Curvature and thickness pickups are verified against their source surface and
kept; other solves are kept as the values the file stores (the geometry at save
time) and listed in ``solves``.

Approximations allowed only with ``allow_partial=True``: a glass name found in
no catalogue (falls back to the file's n_d, V_d model), object-space NA
(``OBNA``, converted paraxially), real-image-height fields (``FTYP 3``,
converted paraxially), a curved image surface (treated as flat), non-circular or decentred apertures
(ignored), non-standard temperature / pressure (``ENVD``), a multi-configuration
file with coordinate breaks (configuration 1 only), multi-configuration operands other than the ones
listed below, and unknown surface-level keywords.

Refused always: ideal (paraxial) surfaces and every other surface type, an r²
aspheric term, sequential-mode off (``MODE`` not ``SEQ``), a negative travel
distance (a surface placed behind the light), telecentric object space, an
inconsistent pickup, an infinite thickness after the object, surface tilt /
decentre data in ``SCBD`` (its layout is not documented in the sources checked).

**Coordinate breaks** (``TYPE COORDBRK``, tilted / decentred / folded systems).
A file with a coordinate break is read into ``raytrace3d.noncoaxial_system``
instead of ``raytrace.lens_system``: ``lens_file_read()["system"]`` is then the
non-coaxial table, ``["noncoaxial"]`` is True, ``lens_file_system`` returns a
``noncoaxial_system`` for the chosen field, and ``["surface_records"][j]`` lists
the tracer records that surface ``j`` became. The convention (from the format's
documentation, KA-01638; the tilt sign also checked against a published design; see ``tests/data/lensfile/README.md``):

* ``PARM 1, 2`` = decentre x, y; ``PARM 3, 4, 5`` = tilt about x, y, z in
  degrees (right-hand rule: a positive x tilt turns +z towards -y); ``PARM 6`` =
  order. Order 0: decentre first, then intrinsic rotations x-y-z, matrix
  ``Rx(ax)·Ry(ay)·Rz(az)`` (the format's documentation, KA-01638). Any other
  value: intrinsic z-y-x, ``Rz·Ry·Rx``, then decentre along the tilted axes.
  ``DISZ`` is the thickness after the break along the new z axis. These are
  exactly the tracer's ``"xyz"`` and ``"zyx"`` breaks.
* A file keeps one frame through a mirror and uses negative thicknesses after
  it; the tracer flips its frame at every reflection. The importer converts
  (``dy -> -dy``, ``ay -> -ay``, ``az -> -az`` after an odd number of mirrors,
  radii and aspheric terms flip sign, thicknesses become positive distances).
* A later break that is exactly the inverse of an earlier one (order flipped,
  every parameter negated, which is what a pickup with scale -1 stores) becomes
  the tracer's ``undo`` element; ``PPAR`` pickups of ``PARM`` values are
  verified against their source surface (a stale value is refused).
* A flat, bare air-to-air plane without aperture (the usual dummy surface next
  to a break or a mirror) is merged into the preceding thickness: it cannot
  change a ray, and a sequential program lets rays meet it "behind" the previous
  vertex, which the tracer rejects. It is listed in ``report["notes"]``.
* Supported with breaks: aperture ``ENPD`` / ``FNUM`` (object at infinity;
  converted to the stop radius through real axial rays, area-preserving when the
  stop is tilted) and ``FLOA``; fields ``FTYP 0`` (angle) and ``1`` (object
  height) kept as ``(x, y)`` with the sign of the file. Refused: ``OBNA``,
  image-height fields, ``ENPD`` / ``FNUM`` with a finite object, a break in front
  of the first surface (it would move the object space), a break that carries a
  glass / curvature / the stop, a negative travel distance.

**Multiple configurations** (zoom / switchable systems). ``MNUM n active`` declares *n* configurations and the
table that follows holds one row per operand and configuration, ``OPERAND surface config value ...`` with
the configuration 1-based: ``THIC`` thickness, ``CRVT`` curvature (1/length, like ``CURV``), ``GLSS`` glass
name (``MIRROR``, or nothing for air), ``PRAM`` a surface parameter (its number is the second number after
the value) and ``PAR1`` ... ``PAR9`` the same parameter in one word. ``lens_file_read`` builds every
configuration (the surface blocks hold the active one), keeps the first as the system and stores the others
as sparse overrides in ``system["configurations"]``; resolve them with ``lensconfig.lens_configurations``.
``SDIA`` (semi-diameter, not read by this importer either), ``MOFF`` and ``MCOM`` are ignored and reported; any
other operand is unsupported (``allow_partial=True`` drops it and marks the result approximate). A row must
list every configuration (a partial row is refused). ``lens_file_write`` of a system that carries
``configurations`` writes configuration 1 as the surface blocks, ``MNUM n 1`` and the rows of every operand
that varies; it refuses (``ValueError``) what these lines cannot carry: a different aperture, field,
wavelength, stop, conic constant, clear aperture or surface type in a later configuration, a model glass in a
glass row, and (for a file with an F/# aperture) a stop aperture that does not follow the F/#. Curvature,
thickness and parameter pickups are frozen at the written values (listed in ``dropped_solves``).
Evidence for the line layout: public files (24 zoom lenses read in full, plus samples of every operand: rows, order, the active
configuration) and the two public readers (which skip the table); see
``docs/capabilities/sequential-lens-design-metrics.md``. The writer was checked by reading its output back
and by reading real zoom files back after a write.

Conventions: lengths in mm, wavelengths in µm (the file's own unit), field
angles in degrees. For coaxial files fields are folded to their radial
magnitude (``hypot(x, y)`` for heights, the angle whose tangent is
``hypot(tan θx, tan θy)`` for angles), which is exact for the rotationally
symmetric systems of that path; with coordinate breaks fields stay ``(x, y)``
(ray direction cosines ∝ ``(tan θx, tan θy, 1)``, positive = towards +x / +y).

Round trip: ``lens_file_read(lens_file_write(p))`` reproduces the surfaces,
glasses, apertures, fields and wavelengths of ``p`` exactly (tested), coordinate
breaks and their pickups included. ``lens_file_write(system=<noncoaxial_system>)``
writes the break elements of a non-coaxial system back as ``COORDBRK`` surfaces.
Keywords that were *ignored* are not written back.
"""
from __future__ import annotations

import copy
import io
import math
import os
import re

import numpy as np

import lensconfig as LC
import raytrace as RT
import raytrace3d as R3

INF = float("inf")

__all__ = ["ZMX_EXAMPLE", "lens_file_read", "lens_file_system", "lens_file_write", "lens_file_report"]

#: Length of one file unit in millimetres.
_UNITS = {"MM": 1.0, "CM": 10.0, "IN": 25.4, "INCH": 25.4, "METER": 1000.0, "M": 1000.0}

#: Aperture keywords and field-type codes this module understands.
_FIELD_TYPES = {0: "angle", 1: "object_height", 2: "paraxial_image_height", 3: "real_image_height"}

#: Keywords read into the model.
_READ_TOP = frozenset(("VERS", "MODE", "NAME", "NOTE", "UNIT", "ENPD", "FNUM", "FLOA", "OBNA", "FTYP",
                       "XFLN", "YFLN", "XFLD", "YFLD", "FWGN", "FWGT", "WAVM", "WAVL", "WWGT", "PWAV",
                       "GCAT", "RAIM", "VDXN", "VDYN", "VCXN", "VCYN", "VANN", "ENVD", "MNUM"))
_READ_SURF = frozenset(("SURF", "TYPE", "CURV", "DISZ", "GLAS", "CONI", "PARM", "DIAM", "STOP", "COMM",
                        "FLAP", "CLAP", "PZUP", "PPAR", "OBDC", "SQAP", "OBSC", "ELAP", "SCBD"))

#: Keywords that cannot change a sequential real-ray trace, with the reason (reported, not silently skipped).
_IGNORED = {
    "PFIL": "file / display preference", "LANG": "user-interface language", "PICB": "display preference",
    "HIDE": "drawing visibility", "SLAB": "surface label", "POPS": "physical-optics settings",
    "SDMA": "semi-diameter margin (drawing sizes)", "GFAC": "glass-cost factor", "PUSH": "lens-push settings",
    "ROPD": "OPD reference setting", "POLS": "polarisation settings", "GLRS": "glass substitution settings",
    "GSTD": "glass-substitution template", "NSCD": "non-sequential settings", "COFN": "coating / profile file names",
    "BLNK": "blank line marker", "FIMP": "import settings", "MEMA": "mechanical semi-aperture (drawing only)",
    "OMMA": "mechanical-aperture display", "OEMA": "mechanical-aperture display", "HYPR": "hyperhemisphere flag",
    "RCMF": "comment field", "AUTH": "author", "TOL": "tolerance data", "TOLE": "tolerance data",
    "MOFF": "multi-configuration row (configuration settings; name strings, no geometry)",
    "MCOM": "multi-configuration row comment", "COAT": "coating (transmission, not geometry)",
    "MIRR": "mirror-substrate drawing", "VDSZ": "vignetting display", "MAZH": "maximum zone height (display)",
    "VPAR": "variable flag", "VCON": "variable flag", "DMFS": "default-merit settings",
    "TRAC": "ray-trace display setting", "TCED": "TCE data (thermal analysis)", "TCMM": "thermal data",
    "GLCB": "glass-catalogue settings", "ISNA": "ideal-surface settings",
}

#: Top-level merit-function / settings rows written after the surfaces (operand name + numbers).
_MERIT_HINT = "merit-function or settings row (optimisation data, not geometry)"

#: The bundled example: a Cooke triplet (f ≈ 50 mm, f/5, ±20°) with model glasses, written by
#: Fullseye. Radii and spacings: the classic 40-degree-field triplet as published in the MIT-licensed
#: optiland sample set (``optiland.samples.objectives.CookeTriplet``, © 2024 Kramer Harrison);
#: the two glasses are given by n_d / V_d only (a dense barium crown 620/603 and a flint 620/364).
ZMX_EXAMPLE = """VERS 0
MODE SEQ
NAME Cooke triplet f/5 (model glasses)
NOTE 0 Radii and spacings: optiland sample set (MIT). Glasses by n_d and V_d.
UNIT MM X W X CM MR CPMM
ENPD 10
ENVD 20 1 0
FTYP 0 0 3 3 0 0 0
XFLN 0 0 0 0 0 0 0 0 0 0 0 0
YFLN 0 14 20 0 0 0 0 0 0 0 0 0
FWGN 1 1 1 1 1 1 1 1 1 1 1 1
WAVM 1 0.48613 1
WAVM 2 0.58756 1
WAVM 3 0.65627 1
PWAV 2
SURF 0
  TYPE STANDARD
  CURV 0 0 0 0 0 ""
  DISZ INFINITY
SURF 1
  TYPE STANDARD
  CURV 0.045426484276303865 0 0 0 0 ""
  DISZ 3.25896
  GLAS ___BLANK 1 0 1.62041 60.32 0 0 0 0 0 0
  DIAM 7.0 0 0 0 1 ""
SURF 2
  TYPE STANDARD
  CURV -0.0022948388798212154 0 0 0 0 ""
  DISZ 6.00755
  DIAM 7.0 0 0 0 1 ""
SURF 3
  TYPE STANDARD
  CURV -0.04501811528959253 0 0 0 0 ""
  DISZ 0.99997
  GLAS ___BLANK 1 0 1.62004 36.37 0 0 0 0 0 0
  DIAM 5.0 0 0 0 1 ""
SURF 4
  STOP
  TYPE STANDARD
  CURV 0.04928069891858434 0 0 0 0 ""
  DISZ 4.75041
  DIAM 5.0 0 0 0 1 ""
SURF 5
  TYPE STANDARD
  CURV 0.012549633801685667 0 0 0 0 ""
  DISZ 2.95208
  GLAS ___BLANK 1 0 1.62041 60.32 0 0 0 0 0 0
  DIAM 7.0 0 0 0 1 ""
SURF 6
  TYPE STANDARD
  CURV -0.05436162330330578 0 0 0 0 ""
  DISZ 42.20778
  DIAM 7.0 0 0 0 1 ""
SURF 7
  TYPE STANDARD
  CURV 0 0 0 0 0 ""
  DISZ 0
"""


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _num(tok, what, op="lens_file_read"):
    try:
        v = float(tok)
    except (TypeError, ValueError):
        raise ValueError("%s: %s: %r is not a number" % (op, what, tok)) from None
    if not math.isfinite(v):
        raise ValueError("%s: %s: %r is not finite" % (op, what, tok))
    return v


def _decode(raw: bytes, op: str):
    """Bytes of a .zmx file -> (text, encoding name). Refuses archives and binary data."""
    if raw[:2] in (b"\xea\x00", b"\xec\x03"):
        raise ValueError("%s: this looks like a packed .zar archive, not a .zmx text — unpack it first "
                         "(the .zmx is one of its members)" % op)
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16"), "utf-16"
    head = raw[:400]
    if head and head.count(b"\x00") * 3 > len(head):
        odd_zero = all(b == 0 for b in head[1::2])
        even_zero = all(b == 0 for b in head[0::2])
        if odd_zero or even_zero:
            enc = "utf-16-le" if odd_zero else "utf-16-be"
            return raw.decode(enc), enc + " (no BOM, detected)"
        raise ValueError("%s: the file contains NUL bytes but is not UTF-16 text — not a .zmx prescription" % op)
    if b"\x00" in raw:
        raise ValueError("%s: the file contains NUL bytes — not a .zmx prescription text" % op)
    try:
        return raw.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def _source_text(source, op):
    if source is None:
        return ZMX_EXAMPLE, "ZMX_EXAMPLE", "ascii"
    if isinstance(source, (bytes, bytearray)):
        text, enc = _decode(bytes(source), op)
        return text, "<bytes>", enc
    if not isinstance(source, str):
        raise ValueError("%s: source must be a .zmx path, the file's text, bytes or None (the bundled example), "
                         "got %r" % (op, type(source).__name__))
    if "\n" in source or source.lstrip().startswith(("VERS", "MODE", "SURF")):
        if "\x00" in source:
            raise ValueError("%s: the text contains NUL characters — decode the file as UTF-16 first, or pass its "
                             "path / bytes" % op)
        return source, "<text>", "str"
    if not os.path.isfile(source):
        raise ValueError("%s: %r is neither an existing .zmx file nor prescription text" % (op, source))
    with io.open(source, "rb") as fh:
        raw = fh.read()
    text, enc = _decode(raw, op)
    return text, os.path.basename(source), enc


class _Report:
    """Keyword inventory: every line ends up in exactly one of read / ignored / unsupported."""

    def __init__(self):
        self.read = {}
        self.ignored = {}
        self.unsupported = []          # (where, keyword, message, approximable)
        self.notes = []

    def r(self, kw):
        self.read[kw] = self.read.get(kw, 0) + 1

    def i(self, kw, why):
        d = self.ignored.setdefault(kw, {"count": 0, "reason": why})
        d["count"] += 1

    def u(self, where, kw, msg, approximable=False):
        self.unsupported.append({"where": where, "keyword": kw, "message": msg, "approximable": bool(approximable)})

    def as_dict(self):
        return {"read": dict(sorted(self.read.items())),
                "ignored": {k: dict(v) for k, v in sorted(self.ignored.items())},
                "unsupported": list(self.unsupported), "notes": list(self.notes),
                "n_read": int(sum(self.read.values())),
                "n_ignored": int(sum(v["count"] for v in self.ignored.values())),
                "n_unsupported": len(self.unsupported)}


# --------------------------------------------------------------------------- #
# parsing (text -> file-level model, lengths in mm)
# --------------------------------------------------------------------------- #
def _new_surface(idx):
    return {"index": idx, "type": "STANDARD", "curv": 0.0, "disz": 0.0, "glass": None, "conic": 0.0,
            "parm": {}, "diam": 0.0, "diam_type": 0, "stop": False, "comment": "", "aperture": None,
            "curv_solve": None, "pzup": None, "ppar": []}


def _parse(text, op):
    rep = _Report()
    top = {"name": "", "notes": [], "unit": "MM", "mode": "SEQ", "aperture": None, "ftyp": None,
           "x": None, "y": None, "w": None, "wavm": {}, "wavl": None, "wwgt": None, "pwav": None,
           "vign": {}, "envd": None, "mnum": 1, "mcur": 1, "mce": [], "raim": None, "telecentric": False}
    surfs = []
    cur = None
    mce_on = False                       # lines after MNUM are the multi-configuration table
    for lineno, line in enumerate(text.splitlines(), 1):
        toks = line.split()
        if not toks:
            continue
        kw = toks[0].upper()
        indented = line[:1] in (" ", "\t")
        where = "line %d" % lineno if cur is None else "surface %d (line %d)" % (cur["index"], lineno)
        # ---- surface block ------------------------------------------------ #
        if kw == "SURF":
            if len(toks) < 2:
                raise ValueError("%s: line %d: SURF without a number" % (op, lineno))
            idx = int(_num(toks[1], "SURF number", op))
            if idx != len(surfs):
                raise ValueError("%s: line %d: SURF %d out of order (expected %d)" % (op, lineno, idx, len(surfs)))
            cur = _new_surface(idx)
            surfs.append(cur)
            rep.r(kw)
            continue
        if cur is not None and kw in _READ_SURF:
            rep.r(kw)
            args = toks[1:]
            if kw == "TYPE":
                cur["type"] = args[0].upper() if args else ""
            elif kw == "CURV":
                cur["curv"] = _num(args[0], "%s CURV" % where, op)
                st = int(_num(args[1], "%s CURV solve" % where, op)) if len(args) > 1 else 0
                if st not in (0, 1):
                    cur["curv_solve"] = [a for a in args[1:5]]
            elif kw == "DISZ":
                if args[0].upper() == "INFINITY":
                    cur["disz"] = INF
                else:
                    cur["disz"] = _num(args[0], "%s DISZ" % where, op)
            elif kw == "GLAS":
                cur["glass"] = {"name": args[0], "tokens": args[1:]}
            elif kw == "CONI":
                cur["conic"] = _num(args[0], "%s CONI" % where, op)
            elif kw == "PARM":
                if len(args) < 2:
                    raise ValueError("%s: %s: PARM needs an index and a value" % (op, where))
                cur["parm"][int(_num(args[0], "%s PARM index" % where, op))] = _num(args[1], "%s PARM" % where, op)
            elif kw == "DIAM":
                cur["diam"] = _num(args[0], "%s DIAM" % where, op)
                cur["diam_type"] = int(_num(args[1], "%s DIAM type" % where, op)) if len(args) > 1 else 0
            elif kw == "STOP":
                cur["stop"] = True
            elif kw == "COMM":
                cur["comment"] = line.split(None, 1)[1].strip() if len(toks) > 1 else ""
            elif kw in ("FLAP", "CLAP"):
                r = _num(args[1], "%s %s radius" % (where, kw), op) if len(args) > 1 else 0.0
                rmin = _num(args[0], "%s %s min radius" % (where, kw), op) if args else 0.0
                if rmin != 0.0:
                    rep.u(where, kw, "annular aperture (inner radius %g) is not supported" % rmin, approximable=True)
                cur["aperture"] = {"kind": kw, "r": r}
            elif kw == "PZUP":
                cur["pzup"] = [a for a in args[:4]]
            elif kw == "PPAR":
                if len(args) < 4:
                    raise ValueError("%s: %s: PPAR needs a parameter number, a source surface, a scale and an offset"
                                     % (op, where))
                cur["ppar"].append([int(_num(args[0], "%s PPAR parameter" % where, op)),
                                    int(_num(args[1], "%s PPAR source" % where, op)),
                                    _num(args[2], "%s PPAR scale" % where, op),
                                    _num(args[3], "%s PPAR offset" % where, op)])
            elif kw == "OBDC":
                if any(_num(a, "%s OBDC" % where, op) != 0.0 for a in args[:2]):
                    rep.u(where, kw, "decentred aperture is ignored (rays are clipped by a centred one)",
                          approximable=True)
            elif kw in ("SQAP", "OBSC", "ELAP"):
                rep.u(where, kw, "non-circular aperture / obscuration %s is ignored" % kw, approximable=True)
            elif kw == "SCBD":
                if any(_num(a, "%s SCBD" % where, op) != 0.0 for a in args[1:]):
                    rep.u(where, kw, "surface tilt / decentre data (SCBD) — tilted or decentred surfaces are "
                          "not supported by this importer (use the non-coaxial tracer)")
            continue
        # ---- top level ---------------------------------------------------- #
        if kw in _READ_TOP and not (cur is not None and indented and kw not in ("NOTE",)):
            rep.r(kw)
            args = toks[1:]
            if kw == "MODE":
                top["mode"] = args[0].upper() if args else ""
            elif kw == "NAME":
                top["name"] = line.split(None, 1)[1].strip() if len(toks) > 1 else ""
            elif kw == "NOTE":
                top["notes"].append(line.split(None, 2)[2].strip() if len(toks) > 2 else "")
            elif kw == "UNIT":
                top["unit"] = args[0].upper() if args else ""
            elif kw == "ENPD":
                top["aperture"] = ("ENPD", _num(args[0], "ENPD", op), 0)
            elif kw == "FNUM":
                top["aperture"] = ("FNUM", _num(args[0], "FNUM", op),
                                   int(_num(args[1], "FNUM kind", op)) if len(args) > 1 else 0)
            elif kw == "OBNA":
                top["aperture"] = ("OBNA", _num(args[0], "OBNA", op),
                                   int(_num(args[1], "OBNA kind", op)) if len(args) > 1 else 0)
            elif kw == "FLOA":
                top["aperture"] = ("FLOA", 0.0, 0)
            elif kw == "FTYP":
                vals = [int(_num(a, "FTYP", op)) for a in args]
                top["ftyp"] = vals
                if len(vals) > 1 and vals[1] == 1:
                    top["telecentric"] = True
            elif kw in ("XFLN", "XFLD"):
                top["x"] = [_num(a, kw, op) for a in args]
            elif kw in ("YFLN", "YFLD"):
                top["y"] = [_num(a, kw, op) for a in args]
            elif kw in ("FWGN", "FWGT"):
                top["w"] = [_num(a, kw, op) for a in args]
            elif kw == "WAVM":
                top["wavm"][int(_num(args[0], "WAVM slot", op))] = (
                    _num(args[1], "WAVM wavelength", op), _num(args[2], "WAVM weight", op) if len(args) > 2 else 1.0)
            elif kw == "WAVL":
                top["wavl"] = [_num(a, "WAVL", op) for a in args]
            elif kw == "WWGT":
                top["wwgt"] = [_num(a, "WWGT", op) for a in args]
            elif kw == "PWAV":
                top["pwav"] = int(_num(args[0], "PWAV", op))
            elif kw in ("VDXN", "VDYN", "VCXN", "VCYN", "VANN"):
                top["vign"][kw] = [_num(a, kw, op) for a in args]
            elif kw == "ENVD":
                top["envd"] = [_num(a, "ENVD", op) for a in args[:3]]
            elif kw == "MNUM":
                top["mnum"] = int(_num(args[0], "MNUM", op)) if args else 1
                top["mcur"] = int(_num(args[1], "MNUM active configuration", op)) if len(args) > 1 else 1
                if top["mnum"] < 1 or not 1 <= top["mcur"] <= top["mnum"]:
                    raise ValueError("%s: line %d: MNUM %d %d — the active configuration must be 1..%d"
                                     % (op, lineno, top["mnum"], top["mcur"], max(top["mnum"], 1)))
                mce_on = True
            elif kw == "RAIM":
                top["raim"] = args
            continue
        if kw in _IGNORED:
            rep.i(kw, _IGNORED[kw])
            continue
        if mce_on and not indented:
            _parse_mce_row(top, rep, toks, kw, lineno, op)
            continue
        if cur is not None and indented:
            rep.u(where, kw, "unknown surface keyword %s — it may change the geometry" % kw, approximable=True)
            continue
        rep.i(kw, _MERIT_HINT if cur is not None else "unknown top-level setting (not geometry)")
    top["mce_ok"] = top["mnum"] > 1 and not any(sf["type"] == "COORDBRK" for sf in surfs)
    return top, surfs, rep


# Multi-configuration table (lines after ``MNUM n active``). Row layout, from public files
# (see docs/capabilities/sequential-lens-design-metrics.md): ``OPERAND p1 config value ...`` with
# p1 = surface, config 1-based, and for PRAM the parameter number as the 2nd token after the value.
_MCE_READ = {"THIC": "thickness", "CRVT": "curvature", "GLSS": "glass", "PRAM": "surface parameter"}
_MCE_PARN = re.compile(r"^PAR([1-9])$")
_MCE_IGNORED = {"SDIA": "semi-diameter (display size; this importer does not read DIAM either, rays are clipped "
                        "by CLAP / FLAP only)"}


def _parse_mce_row(top, rep, toks, kw, lineno, op):
    """One multi-configuration row -> ``top["mce"]`` (supported), ignored, or unsupported (never dropped silently)."""
    where = "line %d" % lineno
    if kw in _MCE_IGNORED:
        rep.i(kw, _MCE_IGNORED[kw])
        return
    parn = _MCE_PARN.match(kw)
    if kw not in _MCE_READ and not parn:
        rep.u(where, kw, "multi-configuration operand %s is not supported (read: THIC CRVT GLSS PRAM PARn); "
              "the configurations would differ from the file" % kw, approximable=True)
        return
    if len(toks) < 3:
        raise ValueError("%s: %s: %s row needs a surface and a configuration number" % (op, where, kw))
    surf = int(_num(toks[1], "%s %s surface" % (where, kw), op))
    cfg = int(_num(toks[2], "%s %s configuration" % (where, kw), op))
    value = toks[3] if len(toks) > 3 else ""
    p2 = None
    if kw == "PRAM":
        if len(toks) < 6:
            raise ValueError("%s: %s: PRAM row needs its parameter number (the 2nd number after the value)"
                             % (op, where))
        p2 = int(_num(toks[5], "%s PRAM parameter" % where, op))
    elif parn:
        p2 = int(parn.group(1))
        kw = "PRAM"
        rep.notes.append("%s: %s read as parameter %d (PARn: by analogy with the verified PAR3)" % (where, toks[0], p2))
    if kw != "GLSS":
        value = _num(value, "%s %s value" % (where, toks[0]), op)
    rep.r(toks[0].upper())
    top["mce"].append({"kw": kw, "surf": surf, "cfg": cfg, "value": value, "p2": p2, "where": where})


def _mce_apply(surfs, rows, cfg, op):
    """Apply configuration *cfg* (1-based) of the table to file-level surfaces (file units, before scaling)."""
    for r in rows:
        if r["cfg"] != cfg:
            continue
        sf = surfs[r["surf"]]
        v = r["value"]
        if r["kw"] == "THIC":
            sf["disz"] = INF if (r["surf"] == 0 and v >= 1e10) else v
            sf["pzup"] = None                       # a thickness pickup no longer holds once the value is set
        elif r["kw"] == "CRVT":
            sf["curv"] = v
            sf["curv_solve"] = None
        elif r["kw"] == "GLSS":
            name = v.strip('"')
            sf["glass"] = None if name == "" else {"name": name, "tokens": []}
        else:
            sf["parm"][r["p2"]] = v
            sf["ppar"] = [x for x in sf["ppar"] if x[0] != r["p2"]]


def _mce_check(top, nsurf, op):
    """Every row group must give a value for every configuration (a partial row is ambiguous): fail-closed."""
    n = top["mnum"]
    groups = {}
    for r in top["mce"]:
        if not 1 <= r["cfg"] <= n:
            raise ValueError("%s: %s: %s names configuration %d but MNUM declares %d" % (op, r["where"], r["kw"],
                                                                                       r["cfg"], n))
        if not 0 <= r["surf"] < nsurf:
            raise ValueError("%s: %s: %s names surface %d which does not exist" % (op, r["where"], r["kw"], r["surf"]))
        groups.setdefault((r["kw"], r["surf"], r["p2"]), []).append(r["cfg"])
    for key, cfgs in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or 0)):
        if sorted(cfgs) != list(range(1, n + 1)):
            raise ValueError("%s: multi-configuration row %s surface %d%s has configurations %s, expected 1..%d — "
                             "a row must give every configuration" % (
                                 op, key[0], key[1], "" if key[2] is None else " parameter %d" % key[2],
                                 sorted(cfgs), n))


# --------------------------------------------------------------------------- #
# glass resolution
# --------------------------------------------------------------------------- #
def _model_medium(nd, vd):
    if vd == 0.0:
        return float(nd)
    return (float(nd), float(vd))


def _user_catalogue(glass_dir, op):
    if glass_dir is None:
        glass_dir = os.environ.get("FULLSEYE_GLASS_DIR") or None
    if glass_dir is None:
        return {}, None
    import materials as _mat
    recs = _mat.read_glass_catalog_agf(glass_dir)
    out = {}
    for r in recs:
        out.setdefault(r["name"], r)                     # first catalogue wins (sorted file order)
    return out, glass_dir


def _table_glass(key):
    """Exact (case-insensitive) name of a transparent material in Fullseye's tables, or None.

    Aliases are deliberately **not** followed: in a lens file ``F2`` or ``SK16`` names the old lead
    glass, while the table's alias points to the lead-free ``N-`` glass of another melt (n_d / V_d
    differ in the 4th-5th digit) -- a silent substitution the importer must not make."""
    import materials as _mat
    if key in RT._SELLMEIER:
        return key
    rec = _mat._RECORDS.get(key)
    if rec is not None and rec["class"] in RT._MATERIAL_CLASSES:
        return key
    return None


def _table_alias(key):
    import materials as _mat
    a = RT._GLASS_ALIASES.get(key) or _mat._ALIASES.get(key)
    return a if a and a != key else None


def _resolve_glass(g, where, user_cat, rep, allow_partial, op, nd_tol=5e-4):
    """GLAS tokens -> (medium for raytrace, glass record for the writer, is_mirror)."""
    name = g["name"]
    tk = g["tokens"]
    nd = _num(tk[2], "%s GLAS n_d" % where, op) if len(tk) > 2 else 0.0
    vd = _num(tk[3], "%s GLAS V_d" % where, op) if len(tk) > 3 else 0.0
    up = name.upper()
    # On a catalogue-glass line the n_d / V_d columns are only the model-glass defaults unless the program
    # filled them in; files in the wild carry the placeholder (1.5, 40) next to N-BK7 or TAF3. Treat that
    # pair as "no information": neither checked against the catalogue nor used as a fallback model.
    placeholder = up not in ("___BLANK", "MIRROR") and nd == 1.5 and vd == 40.0
    if placeholder:
        nd, vd = 0.0, 0.0
    if up == "MIRROR":
        return None, {"kind": "mirror", "name": "MIRROR"}, True
    if up == "___BLANK":
        if not nd >= 1.0 or vd < 0.0:
            raise ValueError("%s: %s: model glass needs n_d >= 1 and V_d >= 0 (got %g, %g)" % (op, where, nd, vd))
        return _model_medium(nd, vd), {"kind": "model", "name": "___BLANK", "nd": nd, "vd": vd}, False
    if name.isdigit() and len(name) == 6:
        nd6 = 1.0 + int(name[:3]) / 1000.0
        vd6 = int(name[3:]) / 10.0
        rep.notes.append("%s: six-digit glass code %s read as the model glass n_d %.3f, V_d %.1f" % (where, name, nd6, vd6))
        return (nd6, vd6), {"kind": "code", "name": name, "nd": nd6, "vd": vd6}, False
    medium = None
    src = None
    key = up
    if key in user_cat:
        medium = {"material": user_cat[key], "offset": 0.0}
        src = "user .agf catalogue"
    else:
        exact = _table_glass(key)
        if exact is not None:
            medium = exact
            src = "material table"
        else:
            alias = _table_alias(key)
            if alias is not None:
                rep.notes.append("%s: %s is not in the material table under that exact name; the table's alias "
                                 "points to %s, a different glass, so it was not used" % (where, name, alias))
    if medium is not None:
        n_here = RT.refractive_index(medium, RT.WL_D)
        if nd > 1.0 and abs(n_here - nd) > nd_tol:
            raise ValueError("%s: %s: glass %s from the %s has n_d %.5f but the file says %.5f (|diff| > %g) — a "
                             "different glass of the same name; put the right .agf in glass_dir" %
                             (op, where, name, src, n_here, nd, nd_tol))
        return medium, {"kind": "name", "name": name, "nd": nd if nd > 1.0 else n_here, "vd": vd,
                        "source": src}, False
    if nd >= 1.0 and vd > 0.0:
        msg = ("glass %s is in no catalogue (Fullseye's material table%s); with allow_partial=True it is replaced "
               "by the model glass n_d %.5f, V_d %.2f from the GLAS line" %
               (name, " or the .agf files in glass_dir" if user_cat else "; set glass_dir to your .agf files",
                nd, vd))
        rep.u(where, "GLAS", msg, approximable=True)
        return (nd, vd), {"kind": "name", "name": name, "nd": nd, "vd": vd, "source": "model fallback"}, False
    raise ValueError("%s: %s: glass %s is in no catalogue and the GLAS line has no n_d / V_d to fall back on" %
                     (op, where, name))


# --------------------------------------------------------------------------- #
# file-level model -> prescription
# --------------------------------------------------------------------------- #
def _fields(top, op, rep):
    ft = top["ftyp"] or []
    ftype = ft[0] if ft else 0
    if ftype not in _FIELD_TYPES:
        raise ValueError("%s: field type %d (FTYP) is not supported (0 angle, 1 object height, 2 paraxial image "
                         "height, 3 real image height)" % (op, ftype))
    nf = ft[2] if len(ft) > 2 and ft[2] > 0 else None
    ys = top["y"] if top["y"] is not None else [0.0]
    xs = top["x"] if top["x"] is not None else [0.0] * len(ys)
    ws = top["w"] if top["w"] is not None else [1.0] * len(ys)
    n = nf if nf is not None else len(ys)
    if n > len(ys) or n > len(xs):
        raise ValueError("%s: FTYP declares %d fields but only %d are given" % (op, n, min(len(ys), len(xs))))
    ws = (list(ws) + [1.0] * n)[:n]
    vg = top["vign"]

    def _v(kw, i):
        vals = vg.get(kw)
        return float(vals[i]) if vals and i < len(vals) else 0.0

    fields = [{"x": xs[i], "y": ys[i], "weight": ws[i], "vdx": _v("VDXN", i), "vdy": _v("VDYN", i),
               "vcx": _v("VCXN", i), "vcy": _v("VCYN", i), "van": _v("VANN", i)} for i in range(n)]
    return _FIELD_TYPES[ftype], fields


def _wavelengths(top, op):
    ft = top["ftyp"] or []
    nw = ft[3] if len(ft) > 3 and ft[3] > 0 else None
    if top["wavm"]:
        slots = sorted(top["wavm"])
        if nw is not None:
            slots = [s for s in slots if s <= nw]
            if len(slots) != nw:
                raise ValueError("%s: FTYP declares %d wavelengths but WAVM gives slots %s" % (op, nw, slots))
        wl = [{"um": top["wavm"][s][0], "weight": top["wavm"][s][1]} for s in slots]
        prim_slot = top["pwav"] if top["pwav"] is not None else slots[0]
        if prim_slot not in slots:
            raise ValueError("%s: primary wavelength PWAV %d is not one of the active slots %s" % (op, prim_slot, slots))
        primary = slots.index(prim_slot)
    elif top["wavl"]:
        vals = top["wavl"][:nw] if nw else top["wavl"]
        wts = (top["wwgt"] or [1.0] * len(vals))
        wl = [{"um": v, "weight": (wts[i] if i < len(wts) else 1.0)} for i, v in enumerate(vals)]
        primary = (top["pwav"] - 1) if top["pwav"] else 0
        if not 0 <= primary < len(wl):
            raise ValueError("%s: primary wavelength PWAV %r is out of range" % (op, top["pwav"]))
    else:
        raise ValueError("%s: the file defines no wavelength (WAVM / WAVL)" % op)
    for w in wl:
        if not (0.1 <= w["um"] <= 50.0):
            raise ValueError("%s: wavelength %g um is out of range (0.1-50 um; the format stores um)" % (op, w["um"]))
    return wl, primary


def _radial_field(ftype, f, efl, mag, obj_inf):
    """(x, y) field of the file -> the scalar radial field raytrace takes (deg or mm)."""
    if ftype == "angle":
        tx, ty = math.tan(math.radians(f["x"])), math.tan(math.radians(f["y"]))
        return math.degrees(math.atan(math.hypot(tx, ty)))
    h = math.hypot(f["x"], f["y"])
    if ftype == "object_height":
        return h
    # paraxial / real image height -> object space through the paraxial chief ray
    if obj_inf:
        return math.degrees(math.atan(h / abs(efl)))
    return h / abs(mag)


def _build(top, surfs, rep, op, allow_partial, glass_dir):
    if top["mode"] != "SEQ":
        raise ValueError("%s: MODE %s — only sequential (SEQ) prescriptions are supported" % (op, top["mode"]))
    if top["unit"] not in _UNITS:
        raise ValueError("%s: UNIT %r is not one of %s" % (op, top["unit"], ", ".join(sorted(_UNITS))))
    s = _UNITS[top["unit"]]
    if len(surfs) < 3:
        raise ValueError("%s: a prescription needs an object, at least one surface and an image (got %d SURF)" %
                         (op, len(surfs)))
    if top["telecentric"]:
        raise ValueError("%s: object-space telecentric systems (FTYP ... 1) are not supported by this importer" % op)
    user_cat, gdir = _user_catalogue(glass_dir, op)
    # ---- parameter pickups (PPAR) are verified against their source, in file units ----
    ppar_solves = []
    for sf in surfs:
        where = "surface %d" % sf["index"]
        for (pn, src, scale, off) in sf["ppar"]:
            if pn < 1:
                rep.u(where, "PPAR", "pickup of parameter %d (not a PARM) is not supported" % pn)
                continue
            if not 0 <= src < len(surfs):
                raise ValueError("%s: %s: parameter pickup from surface %d which does not exist" % (op, where, src))
            want = scale * surfs[src]["parm"].get(pn, 0.0) + off
            have = sf["parm"].get(pn, 0.0)
            if abs(want - have) > 1e-9 * max(1.0, abs(have)):
                raise ValueError("%s: %s: parameter pickup PARM %d from surface %d (scale %g, offset %g) gives %.10g but "
                                 "the file stores %.10g — stale or corrupted file" % (op, where, pn, src, scale, off,
                                                                                        want, have))
            ppar_solves.append({"surface": sf["index"], "what": "PARM %d" % pn, "kind": "pickup", "source": src,
                                "scale": scale, "status": "verified"})
    # ---- surface types and unit scaling -------------------------------------
    for sf in surfs:
        where = "surface %d" % sf["index"]
        t = sf["type"]
        if t not in ("STANDARD", "EVENASPH", "COORDBRK"):
            hint = {"PARAXIAL": " (an ideal thin lens has no real-ray model here)"}.get(t, "")
            rep.u(where, "TYPE", "surface type %s is not supported%s" % (t, hint))
        sf["curv"] = sf["curv"] / s
        if math.isfinite(sf["disz"]):
            sf["disz"] = sf["disz"] * s
        sf["diam"] *= s
        if sf["aperture"]:
            sf["aperture"]["r"] *= s
        if t == "COORDBRK":
            bad = sorted(k for k in sf["parm"] if k < 1 or k > 6)
            if bad:
                rep.u(where, "PARM", "coordinate-break parameter(s) %s outside 1..6" % bad)
            if sf["glass"] is not None:
                rep.u(where, "GLAS", "a coordinate break cannot carry a glass")
            if sf["stop"]:
                rep.u(where, "STOP", "the stop cannot be a coordinate break")
            if sf["curv"] != 0.0:
                rep.u(where, "CURV", "a coordinate break (COORDBRK) has no curvature (CURV %g)" % sf["curv"])
            # PARM 1, 2 are decentres (lengths); 3-5 are tilts (degrees); 6 is the order flag
            sf["parm"] = {k: (v * s if k in (1, 2) else v) for k, v in sf["parm"].items()}
        elif t == "EVENASPH":
            p1 = sf["parm"].get(1, 0.0)
            if p1 != 0.0:
                rep.u(where, "PARM", "even-asphere r^2 term (PARM 1 = %g) is not representable; refit it into "
                      "the curvature first" % p1)
            bad = sorted(k for k in sf["parm"] if k < 1 or k > 9)
            if bad:
                rep.u(where, "PARM", "even-asphere parameter(s) %s outside 1..9" % bad)
            # coefficient of r^(2k) in file units -> mm: a * s^(1-2k)
            sf["parm"] = {k: v * s ** (1 - 2 * k) for k, v in sf["parm"].items()}
        elif sf["parm"] and any(v != 0.0 for v in sf["parm"].values()) and t == "STANDARD":
            rep.notes.append("%s: PARM values on a STANDARD surface have no effect and were not used" % where)
    # ---- environment / configurations / vignetting -------------------------
    if top["envd"] is not None and len(top["envd"]) >= 2 and (abs(top["envd"][0] - 20.0) > 1e-9 or
                                                               abs(top["envd"][1] - 1.0) > 1e-9):
        rep.u("system", "ENVD", "temperature %g C / pressure %g atm differ from the catalogue reference (20 C, "
              "1 atm); indices are used at the reference" % (top["envd"][0], top["envd"][1]), approximable=True)
    if top["mnum"] > 1 and not top.get("mce_ok"):
        rep.u("system", "MNUM", "%d configurations — only configuration 1 (the stored prescription) is imported"
              % top["mnum"], approximable=True)
    if top["raim"] and len(top["raim"]) > 1 and top["raim"][1] not in ("0",):
        rep.notes.append("ray aiming (RAIM) is on in the file; Fullseye aims the chief ray at the stop centre and "
                         "launches the other rays on the paraxial entrance pupil")
    xs_ = top["x"] or []
    for i, x in enumerate(xs_[:12]):                      # off-meridian field points are folded onto +y
        if x != 0.0 and any(i < len(top["vign"].get(k, [])) and top["vign"][k][i] != 0.0 for k in top["vign"]):
            rep.u("field %d" % (i + 1), "VDXN/VDYN/VCXN/VCYN",
                  "vignetting factors of an off-meridian field point (x != 0) are applied without rotating the "
                  "pupil to the field's azimuth (fields are folded onto +y)", approximable=True)
    img = surfs[-1]
    if img["curv"] != 0.0:
        rep.u("surface %d" % img["index"], "CURV", "curved image surface (R = %g mm) is treated as a plane" %
              (1.0 / img["curv"]), approximable=True)
    # ---- the glasses ---------------------------------------------------------
    media = []                                            # medium after each surface (None for a mirror)
    mirrors = []
    for sf in surfs:
        where = "surface %d" % sf["index"]
        if sf["glass"] is None:
            sf["glass_rec"] = None
            media.append(1.0)
            mirrors.append(False)
            continue
        med, grec, mir = _resolve_glass(sf["glass"], where, user_cat, rep, allow_partial, op)
        sf["glass_rec"] = grec
        media.append(med)
        mirrors.append(mir)
    # ---- pickups ---------------------------------------------------------------
    solves = list(ppar_solves)
    for sf in surfs:
        where = "surface %d" % sf["index"]
        if sf["curv_solve"]:
            st = int(_num(sf["curv_solve"][0], "%s CURV solve" % where, op))
            if st == 4:
                src = int(_num(sf["curv_solve"][1], "%s pickup source" % where, op))
                scale = _num(sf["curv_solve"][2], "%s pickup scale" % where, op) if len(sf["curv_solve"]) > 2 else 1.0
                off = _num(sf["curv_solve"][3], "%s pickup offset" % where, op) if len(sf["curv_solve"]) > 3 else 0.0
                if not 0 <= src < len(surfs):
                    raise ValueError("%s: %s: curvature pickup from surface %d which does not exist" % (op, where, src))
                want = scale * surfs[src]["curv"] + off / 1.0
                if abs(want - sf["curv"]) > 1e-9 * max(1.0, abs(sf["curv"])) and \
                        abs(scale * surfs[src]["curv"] - sf["curv"]) > 1e-9 * max(1.0, abs(sf["curv"])):
                    raise ValueError("%s: %s: curvature pickup from surface %d (scale %g) gives %.10g but the file "
                                     "stores %.10g — stale or corrupted file" % (op, where, src, scale, want, sf["curv"]))
                solves.append({"surface": sf["index"], "what": "curvature", "kind": "pickup", "source": src,
                               "scale": scale, "status": "verified"})
            else:
                solves.append({"surface": sf["index"], "what": "curvature", "kind": "solve type %d" % st,
                               "status": "frozen at the stored value"})
        if sf["pzup"]:
            src = int(_num(sf["pzup"][0], "%s PZUP source" % where, op))
            scale = _num(sf["pzup"][1], "%s PZUP scale" % where, op) if len(sf["pzup"]) > 1 else 1.0
            off = _num(sf["pzup"][2], "%s PZUP offset" % where, op) * s if len(sf["pzup"]) > 2 else 0.0
            if not 0 <= src < len(surfs):
                raise ValueError("%s: %s: thickness pickup from surface %d which does not exist" % (op, where, src))
            want = scale * surfs[src]["disz"] + off
            if abs(want - sf["disz"]) > 1e-9 * max(1.0, abs(sf["disz"])):
                raise ValueError("%s: %s: thickness pickup from surface %d gives %.10g but the file stores %.10g — "
                                 "stale or corrupted file" % (op, where, src, want, sf["disz"]))
            solves.append({"surface": sf["index"], "what": "thickness", "kind": "pickup", "source": src,
                           "scale": scale, "status": "verified"})
    # ---- refuse now if anything unsupported is not approximable -------------
    hard = [u for u in rep.unsupported if not u["approximable"]]
    soft = [u for u in rep.unsupported if u["approximable"]]
    if hard:
        raise ValueError("%s: cannot import faithfully — %s" % (
            op, "; ".join("%s: %s" % (u["where"], u["message"]) for u in hard)))
    if soft and not allow_partial:
        raise ValueError("%s: the import would be approximate — %s. Pass allow_partial=True to import anyway "
                         "(the result is then marked approximate)" % (
                             op, "; ".join("%s: %s" % (u["where"], u["message"]) for u in soft)))
    if any(sf["type"] == "COORDBRK" for sf in surfs):
        return _build_nc(top, surfs, rep, op, allow_partial, media, mirrors, s, solves, gdir)
    # ---- surfaces -> raytrace ---------------------------------------------------
    obj = surfs[0]
    if obj["disz"] == INF:
        object_mm = INF
    else:
        object_mm = obj["disz"]
        if not object_mm > 0.0:
            raise ValueError("%s: object distance %g mm must be > 0 (or INFINITY)" % (op, object_mm))
    if mirrors[0]:
        raise ValueError("%s: the object surface cannot be a mirror" % op)
    index_object = media[0]
    lens = []
    direction = 1.0
    prev_medium = index_object
    stop = None
    for j in range(1, len(surfs) - 1):
        sf = surfs[j]
        where = "surface %d" % sf["index"]
        if sf["stop"]:
            stop = j - 1
        if mirrors[j]:
            direction = -direction
            med = prev_medium
        else:
            med = media[j]
        if not math.isfinite(sf["disz"]):
            raise ValueError("%s: %s: infinite thickness is only allowed on the object surface" % (op, where))
        t = sf["disz"] * direction
        if t < -1e-12:
            raise ValueError("%s: %s: thickness %g mm runs against the light (a surface placed behind it) — not "
                             "supported" % (op, where, sf["disz"]))
        t = max(0.0, t)
        rec = {"R": INF if sf["curv"] == 0.0 else 1.0 / sf["curv"], "t": t, "n": med, "k": sf["conic"]}
        if mirrors[j]:
            rec["mirror"] = True
        if sf["type"] == "EVENASPH":
            asph = [sf["parm"].get(k, 0.0) for k in range(2, 10)]
            while asph and asph[-1] == 0.0:
                asph.pop()
            if asph:
                rec["asph"] = tuple(asph)
        if sf["aperture"] is not None and sf["aperture"]["r"] > 0.0:
            rec["ap"] = sf["aperture"]["r"]
        lens.append(rec)
        prev_medium = med
    if stop is None:
        if any(sf["stop"] for sf in (surfs[0], surfs[-1])):
            raise ValueError("%s: the stop must be one of the lens surfaces, not the object or the image" % op)
        stop = 0
        rep.notes.append("no STOP in the file: the first surface is taken as the stop")
    fields_type, fields = _fields(top, op, rep)
    wls, primary = _wavelengths(top, op)
    wl0 = wls[primary]["um"]
    if fields_type == "object_height":
        if object_mm == INF:
            raise ValueError("%s: object-height fields need a finite object distance" % op)
        for f in fields:
            f["x"] *= s
            f["y"] *= s
    elif fields_type in ("paraxial_image_height", "real_image_height"):
        for f in fields:
            f["x"] *= s
            f["y"] *= s
    # aperture: build with a unit stop, then scale (pupil sizes are linear in the stop radius)
    ap = top["aperture"]
    if ap is None:
        raise ValueError("%s: the file has no system aperture (ENPD / FNUM / FLOA / OBNA)" % op)
    stop_given = lens[stop].get("ap")
    trial = [dict(r) for r in lens]
    trial[stop]["ap"] = 1.0
    try:
        sys1 = RT.lens_system(trial, stop=stop, object_mm=object_mm, wavelength_um=wl0, index_object=index_object)
        for w in wls:                                     # every declared wavelength must be evaluable
            RT.with_wavelength(sys1, w["um"])
    except ValueError as e:
        raise ValueError("%s: the prescription cannot be built: %s" % (op, e)) from None
    p1 = RT.paraxial_trace(sys1)
    kind, val, sub = ap
    if kind == "ENPD":
        if not val > 0.0:
            raise ValueError("%s: ENPD must be > 0" % op)
        stop_r = (val * s / 2.0) / p1["ep_radius"]
    elif kind == "FNUM":
        if sub != 0:
            rep.u("system", "FNUM", "FNUM kind %d (paraxial working F/#) is converted as image-space F/#" % sub,
                  approximable=True)
            if not allow_partial:
                raise ValueError("%s: FNUM kind %d (working F/#) is not supported; pass allow_partial=True to read it "
                                 "as the image-space F/#" % (op, sub))
        if not val > 0.0 or not math.isfinite(p1["efl"]):
            raise ValueError("%s: FNUM needs a focusing system and F/# > 0" % op)
        stop_r = (abs(p1["efl"]) / val / 2.0) / p1["ep_radius"]
    elif kind == "FLOA":
        d = surfs[stop + 1]["diam"]
        if not d > 0.0:
            raise ValueError("%s: float-by-stop-size (FLOA) needs the stop's semi-diameter (DIAM > 0)" % op)
        stop_r = d
    elif kind == "OBNA":
        if object_mm == INF:
            raise ValueError("%s: object-space NA needs a finite object" % op)
        msg = "object-space NA %g converted paraxially (EP radius = distance to EP x tan(asin(NA/n)))" % val
        rep.u("system", "OBNA", msg, approximable=True)
        if not allow_partial:
            raise ValueError("%s: %s; pass allow_partial=True" % (op, msg))
        if sub != 0 or not 0.0 < val < RT.refractive_index(index_object, wl0):
            raise ValueError("%s: OBNA %g (kind %d) is not a valid numerical aperture" % (op, val, sub))
        u = math.tan(math.asin(val / RT.refractive_index(index_object, wl0)))
        ep_r = u * (object_mm + p1["ep_position"])
        stop_r = ep_r / p1["ep_radius"]
    else:                                                  # pragma: no cover - parse only yields the above
        raise ValueError("%s: aperture %s not supported" % (op, kind))
    if stop_given is not None and abs(stop_given - stop_r) > 1e-9 * max(1.0, stop_r) and kind != "FLOA":
        rep.notes.append("the stop's own aperture (%.6g mm) is replaced by the system aperture (%.6g mm)" %
                         (stop_given, stop_r))
    lens[stop]["ap"] = float(stop_r)
    system = RT.lens_system(lens, stop=stop, object_mm=object_mm, wavelength_um=wl0, index_object=index_object)
    para = RT.paraxial_trace(system)
    for f in fields:
        f["field"] = _radial_field(fields_type, f, para["efl"], para["magnification"], object_mm == INF)
    _attach_vignetting(system, fields, rep)
    if fields_type == "real_image_height":
        rep.u("system", "FTYP", "real-image-height fields converted through the paraxial chief ray", approximable=True)
        if not allow_partial:
            raise ValueError("%s: real-image-height fields (FTYP 3) are only converted paraxially; pass "
                             "allow_partial=True" % op)
    if fields_type == "paraxial_image_height":
        rep.notes.append("paraxial-image-height fields converted to %s through the paraxial chief ray (exact in "
                         "paraxial optics)" % ("angles" if object_mm == INF else "object heights"))
    approx = bool(rep.unsupported)
    return {"system": system, "fields": fields, "field_type": fields_type, "wavelengths": wls, "primary": primary,
            "solves": solves, "approximate": approx, "glass_dir": gdir}


_VIG_FIELD_KEYS = ("vdx", "vdy", "vcx", "vcy", "van")


def _attach_vignetting(system, fields, rep):
    """Put the per-field vignetting factors on the system as ``system["vignetting"]`` (radial-field keyed)."""
    recs = {}
    for i, f in enumerate(fields):
        vals = {k: f[k] for k in _VIG_FIELD_KEYS}
        if not any(v != 0.0 for v in vals.values()):
            continue
        key = f["field"]
        if key in recs and recs[key] != vals:
            raise ValueError("lens_file_read: fields 1..%d include two with the same radial field %g but different "
                             "vignetting factors (the importer folds fields onto +y, so they cannot both be kept)"
                             % (len(fields), key))
        recs[key] = vals
    if not recs:
        return
    # fields without factors get explicit zero records, so that a field between two listed ones is
    # interpolated toward zero rather than held at the nearest non-zero record
    for f in fields:
        recs.setdefault(f["field"], {k: 0.0 for k in _VIG_FIELD_KEYS})
    system["vignetting"] = RT._vignetting_table([dict(v, field=k) for k, v in recs.items()])


# --------------------------------------------------------------------------- #
# coordinate breaks -> raytrace3d break elements
# --------------------------------------------------------------------------- #
def _z(v):
    """Normalise -0.0 to 0.0 (a sign flip of zero must not leak into the model)."""
    return float(v) + 0.0


def _break_elements(parm, direction, t):
    """One COORDBRK surface (``PARM 1..6``) -> one ``raytrace3d`` break element.

    Format convention (the format's documentation, KA-01638; the tilt sign also checked against a published
    design): the break decentres by ``(PARM 1, PARM 2)`` and tilts by ``PARM 3, 4, 5`` degrees about x, y, z with
    the right-hand rule. Order flag ``PARM 6 = 0``: decentre first, then intrinsic rotations x-y-z, i.e. the matrix
    ``Rx(ax)·Ry(ay)·Rz(az)`` (the tracer's ``"xyz"`` break); a non-zero flag: intrinsic z-y-x, ``Rz·Ry·Rx``, then
    decentre along the tilted axes (the tracer's ``"zyx"``). ``t`` is the thickness after the break along the
    new z.

    ``raytrace3d`` flips its local frame at every reflection (a rotation of 180° about x), a file keeps its frame
    and uses negative thicknesses instead. With ``direction = -1`` (after an odd number of mirrors) the break is
    therefore conjugated by that flip: ``dy -> -dy``, ``ay -> -ay``, ``az -> -az`` (``dx`` and ``ax`` are
    unchanged).
    """
    def g(i):
        return float(parm.get(i, 0.0))
    d = (_z(g(1)), _z(direction * g(2)))
    a = (_z(g(3)), _z(direction * g(4)), _z(direction * g(5)))
    order1 = g(6) != 0.0
    # flag 0 = decentre, then intrinsic x-y-z (Rx·Ry·Rz) = the tracer's "xyz"; flag 1 = intrinsic z-y-x (Rz·Ry·Rx),
    # then decentre along the tilted axes = the tracer's "zyx"
    return [{"type": "break", "decenter": d, "tilt": a, "order": "zyx" if order1 else "xyz", "t": t}]


def _is_undo_of(b, c, tol=1e-12):
    """True when break *b* is, numerically, the exact inverse of break *c* (``raytrace3d``'s undo)."""
    if b["type"] != "break" or c["type"] != "break" or "undo" in b or "undo" in c:
        return False
    if any(abs(x + y) > tol for x, y in zip(b["decenter"], c["decenter"])):
        return False
    if any(abs(x + y) > tol for x, y in zip(b["tilt"], c["tilt"])):
        return False
    d_zero = c["decenter"][0] == 0.0 and c["decenter"][1] == 0.0
    nz = sum(1 for v in c["tilt"] if v != 0.0)
    if nz == 0 or (d_zero and nz <= 1):          # the two orders coincide: either label is the inverse
        return True
    return b["order"] != c["order"]


def _mark_undos(elements):
    """Replace a break that exactly undoes an earlier one by ``{"type": "break", "undo": j}``.

    Scans backwards for the nearest earlier break that is not yet undone, so ``CB(a) CB(b) CB(-b) CB(-a)``
    pairs up like brackets. Returns the number of undo elements made."""
    used = set()
    n = 0
    for i, e in enumerate(elements):
        if e.get("type") != "break" or "undo" in e:
            continue
        for j in range(i - 1, -1, -1):
            c = elements[j]
            if c.get("type") == "break" and "undo" not in c and j not in used and _is_undo_of(e, c):
                elements[i] = {"type": "break", "undo": j, "t": e["t"]}
                used.add(j)
                n += 1
                break
    return n


def _nc_fields(top, s, object_mm, op, rep):
    ftype, fields = _fields(top, op, rep)
    if ftype not in ("angle", "object_height"):
        raise ValueError("%s: field type %s is not supported with coordinate breaks (only angle and object height "
                         "can be placed without the paraxial image-height conversion)" % (op, ftype))
    if ftype == "object_height":
        if object_mm == INF:
            raise ValueError("%s: object-height fields need a finite object distance" % op)
        for f in fields:
            f["x"] *= s
            f["y"] *= s
    for f in fields:
        # ray direction cosines ~ (tan fx, tan fy, 1): the sign is that of the file (positive = towards +x / +y)
        f["field"] = (float(f["x"]), float(f["y"]))
    return ftype, fields


def _build_nc(top, surfs, rep, op, allow_partial, media, mirrors, s, solves, gdir):
    """Surfaces with coordinate breaks -> a ``raytrace3d.noncoaxial_system`` (the file's frame is kept, thicknesses
    after a mirror are the positive travel distances the tracer expects)."""
    n = len(surfs)
    if surfs[0]["type"] == "COORDBRK" or surfs[-1]["type"] == "COORDBRK":
        raise ValueError("%s: the object and the image surface cannot be coordinate breaks" % op)
    obj = surfs[0]
    if obj["disz"] == INF:
        object_mm = INF
    else:
        object_mm = obj["disz"]
        if not object_mm > 0.0:
            raise ValueError("%s: object distance %g mm must be > 0 (or INFINITY)" % (op, object_mm))
    if mirrors[0]:
        raise ValueError("%s: the object surface cannot be a mirror" % op)
    index_object = media[0]
    first_real = next((j for j in range(1, n - 1) if surfs[j]["type"] != "COORDBRK"), None)
    if first_real is None:
        raise ValueError("%s: no real surface between the object and the image" % op)
    for j in range(1, first_real):
        p = surfs[j]["parm"]
        if any(p.get(k, 0.0) != 0.0 for k in (1, 2, 3, 4, 5)) or surfs[j]["disz"] != 0.0:
            raise ValueError("%s: surface %d: a coordinate break in front of the first surface would move the object "
                             "space; that convention is not verified here — put it behind the first surface" % (op, j))
    elements, srec = [], [[] for _ in surfs]
    direction = 1.0
    stop, stop_j = None, None
    cur_medium = index_object
    n_merged = 0
    for j in range(1, n - 1):
        sf = surfs[j]
        where = "surface %d" % sf["index"]
        if not math.isfinite(sf["disz"]):
            raise ValueError("%s: %s: infinite thickness is only allowed on the object surface" % (op, where))
        if sf["type"] == "COORDBRK":
            t = sf["disz"] * direction
            if t < -1e-12:
                raise ValueError("%s: %s: thickness %g mm runs against the light (a surface placed behind it) — not "
                                 "supported" % (op, where, sf["disz"]))
            for b in _break_elements(sf["parm"], direction, _z(max(0.0, t))):
                srec[j].append(len(elements))
                elements.append(b)
            continue
        pre = direction
        if mirrors[j]:
            direction = -direction
        t = sf["disz"] * direction
        if t < -1e-12:
            raise ValueError("%s: %s: thickness %g mm runs against the light (a surface placed behind it) — not "
                             "supported" % (op, where, sf["disz"]))
        # A flat, bare air-to-air plane that is neither the stop nor an aperture does nothing to a ray; a sequential
        # program still intersects it, even "behind" the previous surface, which the tracer rejects (a dummy plane
        # at a mirror vertex catches rays off-vertex on the wrong side). Its thickness joins the previous element.
        flat = sf["curv"] == 0.0 and (sf["type"] == "STANDARD" or not any(v != 0.0 for v in sf["parm"].values()))
        if (elements and flat and not mirrors[j] and media[j] == cur_medium and sf["aperture"] is None
                and not sf["stop"]):
            elements[-1]["t"] = _z(elements[-1]["t"] + max(0.0, t))
            n_merged += 1
            continue
        if not mirrors[j]:
            cur_medium = media[j]
        el = {"R": INF if sf["curv"] == 0.0 else pre / sf["curv"], "t": _z(max(0.0, t)), "k": sf["conic"]}
        if sf["type"] == "EVENASPH":
            asph = [sf["parm"].get(k, 0.0) for k in range(2, 10)]
            while asph and asph[-1] == 0.0:
                asph.pop()
            if asph:
                el["asph"] = tuple(_z(pre * a) for a in asph)
        if mirrors[j]:
            el["mirror"] = True
        else:
            el["n"] = media[j]
        if sf["aperture"] is not None and sf["aperture"]["r"] > 0.0:
            el["ap"] = sf["aperture"]["r"]
        if sf["stop"]:
            stop, stop_j = len(elements), j
        srec[j].append(len(elements))
        elements.append(el)
    if stop is None:
        if any(sf["stop"] for sf in (surfs[0], surfs[-1])):
            raise ValueError("%s: the stop must be one of the lens surfaces, not the object or the image" % op)
        stop, stop_j = srec[first_real][0], first_real
        rep.notes.append("no STOP in the file: the first surface is taken as the stop")
    if n_merged:
        rep.notes.append("%d flat air-to-air plane(s) without aperture were merged into the preceding thickness (they "
                         "do not change a ray; the tracer would reject rays that meet them 'behind' a vertex)"
                         % n_merged)
    n_undo = _mark_undos(elements)
    if n_undo:
        rep.notes.append("%d coordinate break(s) undo an earlier one exactly and are mapped to the tracer's undo "
                         "element" % n_undo)
    ftype, fields = _nc_fields(top, s, object_mm, op, rep)
    wls, primary = _wavelengths(top, op)
    wl0 = wls[primary]["um"]
    ap = top["aperture"]
    if ap is None:
        raise ValueError("%s: the file has no system aperture (ENPD / FNUM / FLOA / OBNA)" % op)
    kind, val, sub = ap
    if kind == "OBNA":
        raise ValueError("%s: object-space NA (OBNA) is not supported together with coordinate breaks" % op)
    if kind in ("ENPD", "FNUM") and object_mm != INF:
        raise ValueError("%s: %s with a finite object is not supported together with coordinate breaks (use FLOA "
                         "or an object at infinity)" % (op, kind))
    stop_given = elements[stop].get("ap")
    trial = [dict(e) for e in elements]
    trial[stop]["ap"] = 1.0
    try:
        sys1 = R3.noncoaxial_system(trial, stop=stop, object_mm=object_mm, wavelength_um=wl0,
                                    index_object=index_object)
        for w in wls:                                     # every declared wavelength must be evaluable
            R3.noncoaxial_system(trial, stop=stop, object_mm=object_mm, wavelength_um=w["um"],
                                 index_object=index_object)
        Js = Jo = None
        if object_mm == INF:
            Js, Jo = R3._axis_jacobians(sys1)
    except ValueError as e:
        raise ValueError("%s: the prescription cannot be built: %s" % (op, e)) from None
    pupil = {"entrance_radius_mm": None, "stop_radius_mm": None, "stop_per_entrance": None, "anisotropy": None,
             "efl_mm": None}
    scale = None
    if Js is not None:
        det = abs(float(np.linalg.det(Js)))
        sv = np.linalg.svd(Js, compute_uv=False)
        if not det > 1e-18:
            raise ValueError("%s: the stop is not reached by an axial beam (degenerate pupil map)" % op)
        scale = math.sqrt(det)
        pupil["stop_per_entrance"] = scale
        pupil["anisotropy"] = float(sv[0] / sv[1])
        detj = abs(float(np.linalg.det(Jo)))
        pupil["efl_mm"] = (1.0 / math.sqrt(detj)) if detj > 1e-18 else None
    if kind == "ENPD":
        if not val > 0.0:
            raise ValueError("%s: ENPD must be > 0" % op)
        pupil["entrance_radius_mm"] = val * s / 2.0
        stop_r = pupil["entrance_radius_mm"] * scale
    elif kind == "FNUM":
        if sub != 0:
            rep.u("system", "FNUM", "FNUM kind %d (paraxial working F/#) is converted as image-space F/#" % sub,
                  approximable=True)
            if not allow_partial:
                raise ValueError("%s: FNUM kind %d (working F/#) is not supported; pass allow_partial=True to read it "
                                 "as the image-space F/#" % (op, sub))
        if not val > 0.0 or pupil["efl_mm"] is None:
            raise ValueError("%s: FNUM needs a focusing system and F/# > 0" % op)
        pupil["entrance_radius_mm"] = pupil["efl_mm"] / val / 2.0
        stop_r = pupil["entrance_radius_mm"] * scale
    else:                                                  # FLOA
        d = surfs[stop_j]["diam"]
        if not d > 0.0:
            raise ValueError("%s: float-by-stop-size (FLOA) needs the stop's semi-diameter (DIAM > 0)" % op)
        stop_r = d
        if scale is not None:
            pupil["entrance_radius_mm"] = stop_r / scale
    pupil["stop_radius_mm"] = float(stop_r)
    if pupil["anisotropy"] is not None and pupil["anisotropy"] > 1.0 + 1e-6:
        rep.notes.append("the stop is tilted or anamorphic (entrance-to-stop scale differs by %.4g between its two "
                         "directions): the stop radius preserves the area of the entrance pupil, and rays aimed at "
                         "the stop fill a circle on the stop, not on the entrance pupil. Launch your own beam for an "
                         "exact circular entrance pupil." % pupil["anisotropy"])
    if stop_given is not None and abs(stop_given - stop_r) > 1e-9 * max(1.0, stop_r) and kind != "FLOA":
        rep.notes.append("the stop's own aperture (%.6g mm) is replaced by the system aperture (%.6g mm)" %
                         (stop_given, stop_r))
    elements[stop]["ap"] = float(stop_r)
    try:
        system = R3.noncoaxial_system(elements, stop=stop, object_mm=object_mm, wavelength_um=wl0,
                                      index_object=index_object, field=fields[0]["field"])
    except ValueError as e:
        raise ValueError("%s: the prescription cannot be built: %s" % (op, e)) from None
    approx = bool(rep.unsupported)
    return {"system": system, "fields": fields, "field_type": ftype, "wavelengths": wls, "primary": primary,
            "solves": solves, "approximate": approx, "glass_dir": gdir, "noncoaxial": True, "pupil": pupil,
            "surface_records": srec}


def _surface_snapshot(sf):
    """The file-level surface as the writer needs it (mm, plain values)."""
    out = {k: sf[k] for k in ("index", "type", "curv", "disz", "conic", "diam", "diam_type", "stop", "comment")}
    out["parm"] = {int(k): float(v) for k, v in sorted(sf["parm"].items())}
    out["glass"] = None if sf.get("glass_rec") is None else dict(sf["glass_rec"])
    out["aperture"] = None if sf["aperture"] is None else dict(sf["aperture"])
    out["curv_solve"] = None if sf["curv_solve"] is None else list(sf["curv_solve"])
    out["pzup"] = None if sf["pzup"] is None else list(sf["pzup"])
    out["ppar"] = [list(x) for x in sf["ppar"]]
    return out


# --------------------------------------------------------------------------- #
# public ops
# --------------------------------------------------------------------------- #
def lens_file_read(source=None, allow_partial: bool = False, glass_dir=None) -> dict:
    """``.zmx`` の逐次レンズ処方を Fullseye の処方として読む(``table``)。

    *source* is a file path, the file's text, its bytes, or ``None`` for the
    bundled example :data:`ZMX_EXAMPLE` (a Cooke triplet, f ≈ 50 mm, f/5).
    Encodings: UTF-16 with a byte-order mark (what current design programs save),
    UTF-16 without one (detected from the NUL pattern), UTF-8 and Latin-1.
    *glass_dir* (or the environment variable ``FULLSEYE_GLASS_DIR``) is a
    directory of ``.agf`` glass catalogues searched before the built-in material
    table. *allow_partial* admits the approximations listed in the module help
    and marks the result ``approximate=True``; without it they are refused.

    Returns ``{"system", "name", "notes", "unit", "aperture", "field_type",
    "fields", "wavelengths", "primary", "surfaces", "solves", "approximate",
    "encoding", "source", "report"}``: ``system`` is a ready
    ``raytrace.lens_system`` at the primary wavelength (field 0 — pick a field
    with :func:`lens_file_system`), ``fields`` are ``{"x", "y", "weight",
    "field"}`` with ``field`` the radial value raytrace takes (degrees or mm),
    ``surfaces`` is the file-level model (curvatures in 1/mm, signed thicknesses
    as the file stores them, glasses, apertures, solves) that
    :func:`lens_file_write` writes back, and ``report`` classifies every keyword
    as read / ignored / unsupported (see :func:`lens_file_report`).

    A file with an ``MNUM`` table (more than one configuration) is read into the active
    configuration plus ``system["configurations"]``, a list with one sparse override dict per
    configuration (see ``lensconfig``); the result also carries ``n_configurations`` and
    ``active_configuration`` (0-based).

    A file with ``COORDBRK`` surfaces is read into a
    ``raytrace3d.noncoaxial_system`` (``noncoaxial`` is True, ``system`` is that
    table, each field's ``field`` is the pair ``(x, y)``, ``pupil`` holds the
    entrance-pupil radius, stop radius and effective focal length found with real
    axial rays, ``surface_records[j]`` the tracer records of file surface ``j``);
    the conventions are in the module help.

    Example::

        p = lens_file_read("triplet.zmx")
        RT.paraxial_trace(p["system"])["efl"]
        sysf = lens_file_system(p, field_index=2)       # the 20-degree field
        RT.spot_stats(sysf)
        q = lens_file_read("folded.zmx")                # tilts / decentres: a non-coaxial system
        raytrace3d.noncoaxial_spot(lens_file_system(q, field_index=1))["rms_radius"]
    """
    op = "lens_file_read"
    if not isinstance(allow_partial, (bool, np.bool_)):
        raise ValueError("%s: allow_partial must be True or False" % op)
    text, label, enc = _source_text(source, op)
    top, surfs, rep = _parse(text, op)
    if not surfs:
        raise ValueError("%s: no SURF record — not a sequential prescription" % op)
    configs = None
    if top["mce_ok"]:
        _mce_check(top, len(surfs), op)
        spare = [copy.deepcopy(surfs) for _ in range(top["mnum"])]          # _build scales the surfaces in place
        for k in range(top["mnum"]):
            _mce_apply(spare[k], top["mce"], k + 1, op)
        surfs[:] = spare[top["mcur"] - 1]                                    # the stored prescription = active config
    built = _build(top, surfs, rep, op, bool(allow_partial), glass_dir)
    if top["mce_ok"]:
        configs = []
        for k in range(top["mnum"]):
            if k == top["mcur"] - 1:
                other = built["system"]
            else:
                other = _build(top, spare[k], _Report(), op, bool(allow_partial), glass_dir)["system"]
            configs.append(_config_diff(built["system"], other, "config %d" % (k + 1), k + 1, op))
        built["system"]["configurations"] = configs
    ap = top["aperture"]
    return {"format": "zmx", "source": label, "encoding": enc, "name": top["name"], "notes": top["notes"],
            "unit": top["unit"],
            "aperture": {"type": ap[0], "value": ap[1] * (_UNITS[top["unit"]] if ap[0] == "ENPD" else 1.0),
                         "kind": ap[2]},
            "field_type": built["field_type"], "fields": built["fields"],
            "wavelengths": built["wavelengths"], "primary": built["primary"],
            "system": built["system"], "surfaces": [_surface_snapshot(sf) for sf in surfs],
            "solves": built["solves"], "approximate": built["approximate"], "glass_dir": built["glass_dir"],
            "noncoaxial": bool(built.get("noncoaxial", False)), "pupil": built.get("pupil"),
            "surface_records": built.get("surface_records"), "report": rep.as_dict(),
            "n_configurations": top["mnum"] if configs is not None else 1,
            "active_configuration": top["mcur"] - 1 if configs is not None else 0}


def _same(a, b, tol=0.0):
    """Value equality for override diffs: numbers within *tol* (relative), containers element-wise."""
    if isinstance(a, dict) or isinstance(b, dict):
        return isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys() and \
            all(_same(a[k], b[k], tol) for k in a)
    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        return isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and len(a) == len(b) and \
            all(_same(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (int, float, np.floating, np.integer)) and isinstance(b, (int, float, np.floating, np.integer)) \
            and not isinstance(a, bool) and not isinstance(b, bool):
        if a == b:
            return True
        return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tol * max(abs(a), abs(b))
    return a == b


_DIFF_SURFACE = ("R", "t", "n", "k", "ap", "asph", "mirror", "f")
_DIFF_SYSTEM = ("wavelength_um", "field", "stop", "object_mm", "image_mm", "aim")


def _config_diff(base, other, name, number, op):
    """Sparse override that turns the coaxial system *base* into *other* (same surface count required)."""
    if len(base["surfaces"]) != len(other["surfaces"]):
        raise ValueError("%s: configuration %d has %d lens surfaces, the active one %d — the configurations of a "
                         "file must share one surface list" % (op, number, len(other["surfaces"]),
                                                               len(base["surfaces"])))
    surf = {}
    for i, (a, b) in enumerate(zip(base["surfaces"], other["surfaces"])):
        d = {k: copy.deepcopy(b[k]) for k in _DIFF_SURFACE if not _same(a.get(k), b.get(k))}
        if d:
            surf[i] = d
    sysf = {k: copy.deepcopy(other[k]) for k in _DIFF_SYSTEM if not _same(base.get(k), other.get(k))}
    out = {"name": name}
    if surf:
        out["surfaces"] = surf
    if sysf:
        out["system"] = sysf
    return out


def _check_prescription(p, op):
    if not isinstance(p, dict) or "system" not in p or "fields" not in p or "wavelengths" not in p:
        raise ValueError("%s: expected the dict returned by lens_file_read(), got %r" % (op, type(p).__name__))
    return p


def lens_file_system(prescription=None, field_index: int = 0, wavelength_index=None) -> dict:
    """読み込んだ処方を、視野 1 つ・波長 1 つの ``raytrace.lens_system`` にする(``table``)。

    *field_index* picks one of ``prescription["fields"]`` (0-based; its radial
    value becomes the system's default field), *wavelength_index* one of
    ``prescription["wavelengths"]`` (default: the primary). Every raytrace /
    lensimage / lensopt op then works on the result. ``None`` reads the bundled
    example first. For a file with coordinate breaks the result is a
    ``raytrace3d.noncoaxial_system`` (use the ``raytrace3d`` ops on it) at the
    field ``(x, y)`` of the file.

    Example::

        p = lens_file_read("triplet.zmx")
        for i in range(len(p["fields"])):
            print(RT.spot_stats(lens_file_system(p, field_index=i))["rms_radius"])
    """
    op = "lens_file_system"
    p = lens_file_read(None) if prescription is None else _check_prescription(prescription, op)
    nf = len(p["fields"])
    if isinstance(field_index, (bool, np.bool_)) or not isinstance(field_index, (int, np.integer)) \
            or not 0 <= int(field_index) < nf:
        raise ValueError("%s: field_index must be 0..%d, got %r" % (op, nf - 1, field_index))
    wi = p["primary"] if wavelength_index is None else wavelength_index
    nw = len(p["wavelengths"])
    if isinstance(wi, (bool, np.bool_)) or not isinstance(wi, (int, np.integer)) or not 0 <= int(wi) < nw:
        raise ValueError("%s: wavelength_index must be 0..%d, got %r" % (op, nw - 1, wavelength_index))
    s = p["system"]
    if p.get("noncoaxial"):
        return R3.noncoaxial_system([dict(e) for e in s["elements"]], stop=s["stop_arg"], object_mm=s["object_mm"],
                                    wavelength_um=p["wavelengths"][int(wi)]["um"], index_object=s["index_object_arg"],
                                    field=p["fields"][int(field_index)]["field"])
    out = RT.lens_system([dict(x) for x in s["surfaces"]], stop=s["stop"], object_mm=s["object_mm"],
                         wavelength_um=p["wavelengths"][int(wi)]["um"], index_object=s["index_object"],
                         image_mm=s["image_mm"], field=p["fields"][int(field_index)]["field"],
                         aim=s.get("aim", "paraxial"), vignetting=s.get("vignetting"))
    if s.get("configurations"):
        out["configurations"] = copy.deepcopy(s["configurations"])           # resolve with lensconfig
    return out


# --------------------------------------------------------------------------- #
# writer
# --------------------------------------------------------------------------- #
def _g(v):
    """Shortest text that reads back to the same float."""
    if v == INF:
        return "INFINITY"
    r = repr(float(v))
    return r[:-2] if r.endswith(".0") else r


def _glass_from_medium(med, op, where):
    """A raytrace medium -> a glass record for the writer (None for air)."""
    if isinstance(med, (int, float, np.floating, np.integer)) and not isinstance(med, bool):
        n = float(med)
        if n == 1.0:
            return None
        return {"kind": "model", "name": "___BLANK", "nd": n, "vd": 0.0}
    if isinstance(med, (tuple, list)) and len(med) == 2:
        return {"kind": "model", "name": "___BLANK", "nd": float(med[0]), "vd": float(med[1])}
    if isinstance(med, str):
        nd = RT.refractive_index(med, RT.WL_D)
        nf, nc = RT.refractive_index(med, RT.WL_F), RT.refractive_index(med, RT.WL_C)
        return {"kind": "name", "name": RT.glass_catalog(med).get("name", med), "nd": nd,
                "vd": (nd - 1.0) / (nf - nc) if nf > nc else 0.0}
    if isinstance(med, dict) and "material" in med:
        m = med["material"]
        name = m["name"] if isinstance(m, dict) else str(m)
        nd = RT.refractive_index(med, RT.WL_D)
        nf, nc = RT.refractive_index(med, RT.WL_F), RT.refractive_index(med, RT.WL_C)
        return {"kind": "name", "name": name, "nd": nd, "vd": (nd - 1.0) / (nf - nc) if nf > nc else 0.0}
    if isinstance(med, dict) and "A" in med and "nd" in med:
        return {"kind": "model", "name": "___BLANK", "nd": float(med["nd"]), "vd": float(med["vd"])}
    if isinstance(med, dict) and "sellmeier" in med:
        try:
            RT.glass_catalog(med.get("name", ""))
        except ValueError:
            raise ValueError("%s: %s: a custom Sellmeier medium %r has no catalogue name a reader could resolve — "
                             "give it a catalogue name or an (n_d, V_d) model" % (op, where, med.get("name"))) from None
        return _glass_from_medium(med["name"], op, where)
    raise ValueError("%s: %s: medium %r cannot be written as a GLAS record" % (op, where, med))


def _file_breaks(b, direction):
    """A tracer break -> a list of ``(decenter, tilt, order_flag)`` file coordinate breaks (the inverse of
    :func:`_break_elements`; *direction* is the file's side of the reflection flip)."""
    d = (_z(b["decenter"][0]), _z(direction * b["decenter"][1]))
    a = (_z(b["tilt"][0]), _z(direction * b["tilt"][1]), _z(direction * b["tilt"][2]))
    return [(d, a, 0 if b["order"] == "xyz" else 1)]


def _surfaces_from_nc(system, template, op):
    """Geometry of a ``raytrace3d.noncoaxial_system`` -> file-level surfaces (coordinate breaks included)."""
    recs = system["records"]
    if tuple(system["image_tilt"]) != (0.0, 0.0) or tuple(system["object_tilt"]) != (0.0, 0.0):
        raise ValueError("%s: a tilted image or object plane cannot be written; add the tilt as a coordinate break"
                         % op)
    lay = R3._layout(system)
    dirs, d = [], 1.0
    for r in recs:
        dirs.append(d)
        if r["kind"] == "surface" and r["reflect"]:
            d = -d
    obj = {"index": 0, "type": "STANDARD", "curv": 0.0, "disz": system["object_mm"], "conic": 0.0, "diam": 0.0,
           "diam_type": 0, "stop": False, "comment": "", "parm": {}, "aperture": None, "curv_solve": None,
           "pzup": None, "ppar": [], "glass": _glass_from_medium(system["index_object_arg"], op, "object")}
    out = [obj]

    def blank(typ):
        return {"index": 0, "type": typ, "curv": 0.0, "disz": 0.0, "conic": 0.0, "diam": 0.0, "diam_type": 0,
                "stop": False, "comment": "", "parm": {}, "aperture": None, "curv_solve": None, "pzup": None,
                "ppar": [], "glass": None}
    for k, r in enumerate(recs):
        where = "record %d" % k
        pre = dirs[k]
        t_trace = lay["image_mm"] if k == len(recs) - 1 else r["t"]
        if r["kind"] == "surface":
            if tuple(r["decenter"]) != (0.0, 0.0) or tuple(r["tilt"]) != (0.0, 0.0):
                raise ValueError("%s: %s: a per-surface decenter / tilt cannot be written; use a coordinate break "
                                 "before and after it" % (op, where))
            if r["beamsplitter"] is not None:
                raise ValueError("%s: %s: a beamsplitter surface cannot be written as a sequential .zmx surface"
                                 % (op, where))
            post = -pre if r["reflect"] else pre
            sf = blank("STANDARD")
            asph = list(r["asph"])
            if asph:
                sf["type"] = "EVENASPH"
                sf["parm"] = {1: 0.0}
                sf["parm"].update({i + 2: _z(pre * float(a)) for i, a in enumerate(asph)})
            sf["curv"] = 0.0 if r["R"] == INF else _z(pre / r["R"])
            sf["conic"] = float(r["k"])
            sf["disz"] = _z(float(t_trace) * post)
            sf["glass"] = ({"kind": "mirror", "name": "MIRROR"} if r["reflect"]
                           else _glass_from_medium(r["n"], op, where))
            if k == system["stop"]:
                sf["stop"] = True
                sf["diam"] = float(r["ap"])             # the stop's semi-diameter (FLOA reads it back)
            elif r["ap"] is not None:
                sf["aperture"] = {"kind": "CLAP", "r": float(r["ap"])}
            if r["label"]:
                sf["comment"] = r["label"].replace("\n", " ")
            out.append(sf)
        else:
            if r["kind"] == "break":
                parts = _file_breaks(r, pre)
            else:
                # A return goes back to the frame at the entry of record `to` and then runs t along its axis. As one
                # break of order 1 (tilt, then decentre along the new axes, then the thickness): tilt = Ft relative
                # to Fc, offset e = Ft^T (o_t - o_c) + (0, 0, t).
                if dirs[k] != dirs[r["to"]]:
                    raise ValueError("%s: %s: a return across an odd number of reflections cannot be written as a "
                                     "coordinate break" % (op, where))
                Fc, oc = lay["entry"][k]
                Ft, ot = lay["entry"][r["to"]]
                e = Ft.T @ (ot - oc) + np.array([0.0, 0.0, float(t_trace)])
                if e[2] < -1e-9:
                    raise ValueError("%s: %s: the return would need a negative thickness (%.6g mm); lengthen the gap "
                                     "after it" % (op, where, e[2]))
                a = R3._euler_zyx(Fc.T @ Ft)
                sf = blank("COORDBRK")
                sf["parm"] = {1: _z(e[0]), 2: _z(pre * e[1]), 3: _z(a[0]), 4: _z(pre * a[1]), 5: _z(pre * a[2]),
                              6: 1.0}
                sf["disz"] = _z(pre * max(0.0, float(e[2])))
                if r["label"]:
                    sf["comment"] = r["label"].replace("\n", " ")
                out.append(sf)
                continue
            for i, (dc, tl, flag) in enumerate(parts):
                sf = blank("COORDBRK")
                sf["parm"] = {1: dc[0], 2: dc[1], 3: tl[0], 4: tl[1], 5: tl[2], 6: float(flag)}
                sf["disz"] = _z(float(t_trace) * pre) if i == len(parts) - 1 else 0.0
                if r["label"]:
                    sf["comment"] = r["label"].replace("\n", " ")
                out.append(sf)
    out.append(blank("STANDARD"))
    for i, sf in enumerate(out):
        sf["index"] = i
    if template is not None and len(template) == len(out) and \
            [x["type"] == "COORDBRK" for x in template] == [x["type"] == "COORDBRK" for x in out]:
        out = [_keep_extras(new, old) for new, old in zip(out, template)]
    return out


def _keep_extras(new, old):
    """Carry the template's display data and still-valid solves over to a rebuilt surface."""
    sf = dict(new)
    for key in ("diam", "diam_type", "comment"):
        if not new.get(key) and old.get(key):
            sf[key] = old[key]
    if old.get("aperture") and new.get("aperture"):
        sf["aperture"] = dict(new["aperture"], kind=old["aperture"]["kind"])
    og, ng = old.get("glass"), new.get("glass")
    if og and ng and og.get("kind") in ("name", "model", "code") and ng["kind"] == og["kind"] \
            and og.get("name") == ng["name"] and abs(og.get("nd", 0) - ng["nd"]) < 5e-4:
        sf["glass"] = og
    if old.get("curv_solve") is not None and new["curv"] == old.get("curv"):
        sf["curv_solve"] = old["curv_solve"]
    if old.get("pzup") is not None and new["disz"] == old.get("disz"):
        sf["pzup"] = old["pzup"]
    if old.get("ppar") and new["parm"] == old.get("parm"):
        sf["ppar"] = [list(x) for x in old["ppar"]]
    return sf


def _nc_enpd(sysd):
    """Entrance-pupil diameter (mm) of a non-coaxial system at an infinite object, from its stop radius."""
    Js, _ = R3._axis_jacobians(sysd)
    det = abs(float(np.linalg.det(Js)))
    if not det > 1e-18:
        raise ValueError("lens_file_write: the stop is not reached by an axial beam")
    return 2.0 * sysd["records"][sysd["stop"]]["ap"] / math.sqrt(det)


def _header_from_nc(system, op):
    """A prescription header (aperture, field, wavelength) for a non-coaxial system written without a file."""
    inf = system["object_mm"] == INF
    fx, fy = system["field"]
    ap = ({"type": "ENPD", "value": _nc_enpd(system), "kind": 0} if inf else {"type": "FLOA", "value": 0.0, "kind": 0})
    return {"name": "", "notes": [], "aperture": ap, "field_type": "angle" if inf else "object_height",
            "fields": [{"x": fx, "y": fy, "weight": 1.0}],
            "wavelengths": [{"um": system["wavelength_um"], "weight": 1.0}], "primary": 0,
            "surfaces": None, "system": system, "noncoaxial": True}


def _is_nc(system):
    return isinstance(system, dict) and system.get("kind") == "noncoaxial_system"


def _surfaces_from_system(system, template, op):
    """Geometry of an (edited) lens_system -> file-level surfaces, keeping the template's extras."""
    if _is_nc(system):
        return _surfaces_from_nc(system, template, op)
    RT._check_system(system)
    lens = system["surfaces"]
    tpl = template if (template is not None and len(template) == len(lens) + 2) else None
    out = []
    obj = {"index": 0, "type": "STANDARD", "curv": 0.0, "disz": system["object_mm"], "conic": 0.0, "diam": 0.0,
           "diam_type": 0, "stop": False, "comment": "", "parm": {}, "aperture": None, "curv_solve": None,
           "pzup": None, "glass": _glass_from_medium(system["index_object"], op, "object")}
    if tpl:
        obj = dict(tpl[0], disz=system["object_mm"])
    out.append(obj)
    direction = 1.0
    for i, s in enumerate(lens):
        where = "surface %d" % (i + 1)
        base = dict(tpl[i + 1]) if tpl else {"index": i + 1, "diam": 0.0, "diam_type": 0, "comment": "",
                                             "curv_solve": None, "pzup": None, "aperture": None}
        if s["mirror"]:
            direction = -direction
            glass = {"kind": "mirror", "name": "MIRROR"}
        else:
            glass = _glass_from_medium(s["n"], op, where)
            old = base.get("glass")
            if old and glass and old.get("kind") in ("name", "model", "code") and glass["kind"] == old["kind"] \
                    and old.get("name") == glass["name"] and abs(old.get("nd", 0) - glass["nd"]) < 5e-4:
                glass = old                                     # unchanged: keep the file's own record
        if s["decenter"] != (0.0, 0.0) or s["tilt"] != (0.0, 0.0):
            raise ValueError("%s: %s: tilted / decentred surfaces cannot be written as a coaxial prescription" %
                             (op, where))
        t = s["t"]
        if t is None:
            t = RT.paraxial_trace(system)["bfl"] if system["image_mm"] is None else system["image_mm"]
        asph = list(s["asph"])
        typ = "EVENASPH" if asph or base.get("type") == "EVENASPH" else "STANDARD"
        parm = {1: 0.0} if typ == "EVENASPH" else {}
        parm.update({k + 2: float(a) for k, a in enumerate(asph)})
        ap = base.get("aperture")
        if i == system["stop"]:
            ap = None                                            # the system aperture sets the stop
        elif s["ap"] is not None:
            ap = {"kind": (ap or {}).get("kind", "CLAP"), "r": float(s["ap"])}
        else:
            ap = None
        curv = 0.0 if s["R"] == INF else 1.0 / s["R"]
        cs = base.get("curv_solve")
        if cs is not None and curv != base.get("curv"):
            cs = None                                            # an edited value no longer obeys its solve
        pz = base.get("pzup")
        disz = float(t) * direction
        if pz is not None and disz != base.get("disz"):
            pz = None
        out.append(dict(base, index=i + 1, type=typ, curv=curv, disz=disz, conic=float(s["k"]), parm=parm,
                        glass=glass, stop=(i == system["stop"]), aperture=ap, curv_solve=cs, pzup=pz))
    img = dict(tpl[-1]) if tpl else {"index": len(lens) + 1, "type": "STANDARD", "curv": 0.0, "disz": 0.0,
                                      "conic": 0.0, "diam": 0.0, "diam_type": 0, "stop": False, "comment": "",
                                      "parm": {}, "aperture": None, "curv_solve": None, "pzup": None, "glass": None}
    img["index"] = len(lens) + 1
    out.append(img)
    return out


def _vignetting_for_write(fields, system):
    """The factors to write for each field: the prescription's own, replaced by *system*'s record of the same field."""
    out = []
    recs = list((system or {}).get("vignetting") or ())
    for f in fields:
        v = {k: float(f.get(k, 0.0)) for k in _VIG_FIELD_KEYS}
        for r in recs:
            if abs(r["field"] - f["field"]) <= 1e-9 * max(1.0, abs(f["field"])):
                v = {k: float(r[k]) for k in _VIG_FIELD_KEYS}
        out.append(v)
    return out


def _glass_row_value(g, where, number, op):
    """The GLSS value of a file-level glass record (a name, MIRROR, or empty for air); anything else is refused."""
    key = _glass_key(g)
    if key is None:
        return ""
    if key[0] in ("mirror", "name"):
        return key[1]
    raise ValueError("%s: configuration %d changes the medium of %s to a %s glass (%s); the multi-configuration "
                     "glass row carries a catalogue name, MIRROR or nothing, so a model / coded glass cannot be "
                     "written" % (op, number, where, key[0], g["name"]))


def _write_multi(p, sysd, path, encoding, op):
    """Write a system that carries ``configurations``: configuration 1 as the surface blocks, the rest as table rows."""
    resolved = LC.lens_configurations(sysd)
    n = len(resolved)
    frozen = [dict(sf, curv_solve=None, pzup=None, ppar=[]) for sf in (p["surfaces"] or [])]
    dropped = [{"surface": a["index"], "what": w}
               for a in (p["surfaces"] or []) for w, key in (("curvature solve", "curv_solve"),
                                                            ("thickness pickup", "pzup"),
                                                            ("parameter pickup", "ppar")) if a.get(key)]
    p0 = dict(p, surfaces=frozen)
    for k, r in enumerate(resolved[1:], 2):
        for key in ("wavelength_um", "field", "aim", "vignetting"):
            if not _same(resolved[0].get(key), r.get(key)):
                raise ValueError("%s: configuration %d changes the system setting %s; the multi-configuration "
                                 "lines verified for this format carry only thickness, curvature, glass and "
                                 "surface parameters" % (op, k, key))
    texts = [lens_file_write(p0, system=r, encoding="ascii")["text"] for r in resolved]
    ap0 = p["aperture"]
    if ap0["type"] == "FNUM" and ap0["kind"] == 0:
        # an F/# file keeps the F/# fixed and lets the pupil follow the focal length: check that every
        # configuration's pupil is the one that F/# implies, then write the F/# line instead of ENPD
        for k, (t, r) in enumerate(zip(texts, resolved), 1):
            enpd = float(next(ln for ln in t.splitlines() if ln.startswith("ENPD ")).split()[1])
            want = abs(RT.paraxial_trace(r)["efl"]) / ap0["value"]
            if abs(enpd - want) > 1e-6 * max(1.0, want):
                raise ValueError("%s: configuration %d has an entrance pupil of %.6g mm but F/%g implies %.6g mm; "
                                 "the file would carry one F/# for all configurations — set the stop aperture "
                                 "to follow it" % (op, k, enpd, ap0["value"], want))
        texts = [re.sub(r"(?m)^ENPD .*$", "FNUM %s 0" % _g(ap0["value"]), t, count=1) for t in texts]
    parsed = [_parse(t, op) for t in texts]
    head0 = texts[0].split("\nSURF 0")[0]
    surfs0 = parsed[0][1]
    rows = {"GLSS": [], "THIC": [], "CRVT": [], "PRAM": []}      # (surface, parameter) -> value per configuration
    per = []                                                       # per configuration file-level surfaces
    for k in range(1, n):
        head = texts[k].split("\nSURF 0")[0]
        if head != head0:
            a, b = head0.splitlines(), head.splitlines()
            bad = next((x for x in zip(a, b) if x[0] != x[1]), (None, None))
            raise ValueError("%s: configuration %d differs from configuration 1 in a system setting (%r vs %r); "
                             "the multi-configuration lines verified for this format carry only thickness, "
                             "curvature, glass and surface parameters" % (op, k + 1, bad[0], bad[1]))
        per.append(parsed[k][1])
    allsurf = [surfs0] + per
    for i, sf0 in enumerate(surfs0):
        where = "surface %d" % i
        for k, sk in enumerate(allsurf[1:], 2):
            sf = sk[i] if i < len(sk) else None
            if sf is None or len(sk) != len(surfs0):
                raise ValueError("%s: configuration %d has a different number of surfaces" % (op, k))
            for key in ("type", "conic", "stop", "diam", "diam_type", "aperture", "comment"):
                if not _same(sf0[key], sf[key]):
                    raise ValueError("%s: configuration %d changes %s of %s (%r -> %r); the multi-configuration "
                                     "lines verified for this format cannot carry it" % (
                                         op, k, {"aperture": "the clear aperture (CLAP / FLAP)", "conic": "the conic "
                                                 "constant", "stop": "the stop", "diam": "the semi-diameter",
                                                 "diam_type": "the semi-diameter", "type": "the surface type",
                                                 "comment": "the comment"}[key], where, sf0[key], sf[key]))
            if sf0["parm"].get(1, 0.0) != sf["parm"].get(1, 0.0):
                raise ValueError("%s: configuration %d changes the r^2 term of %s" % (op, k, where))
    for i, sf0 in enumerate(surfs0):
        vals = [sk[i] for sk in allsurf]
        if len({v["curv"] for v in vals}) > 1:
            rows["CRVT"].append((i, None, [v["curv"] for v in vals]))
        if len({v["disz"] for v in vals}) > 1:
            rows["THIC"].append((i, None, [v["disz"] for v in vals]))
        gs0 = _glass_key(sf0["glass"])
        if any(_glass_key(sk[i]["glass"]) != gs0 for sk in per):
            glass_vals = [_glass_row_value(sf0["glass"], "surface %d" % i, 1, op)] + [
                _glass_row_value(sk[i]["glass"], "surface %d" % i, k, op) for k, sk in enumerate(per, 2)]
            rows["GLSS"].append((i, None, glass_vals))
        keys = sorted({q for v in vals for q in v["parm"] if q >= 2})
        for q in keys:
            pv = [v["parm"].get(q, 0.0) for v in vals]
            if len(set(pv)) > 1:
                rows["PRAM"].append((i, q, pv))
    lines = [texts[0].rstrip("\n"), "MNUM %d 1" % n]
    for kw in ("GLSS", "THIC", "CRVT", "PRAM"):
        for (i, q, vs) in rows[kw]:
            for k, v in enumerate(vs, 1):
                if kw == "GLSS":
                    lines.append(("GLSS %3d %3d %s 0 0" % (i, k, v)) if v else ("GLSS %3d %3d" % (i, k)))
                    continue
                if kw == "THIC" and v == INF:
                    v = 1e10
                tail = "0 %d 0 1 1 1.000000000000E+000 0.000000000000E+000 0" % (q if q is not None else 0)
                lines.append("%s %3d %3d %s %s" % (kw, i, k, _g(v), tail))
    text = "\n".join(lines) + "\n"
    if path is not None:
        data = text.encode("utf-16") if encoding == "utf-16" else text.encode("ascii", errors="strict")
        with io.open(path, "wb") as fh:
            fh.write(data)
    return {"text": text, "path": path, "n_surfaces": len(surfs0), "encoding": encoding,
            "dropped_solves": dropped, "n_configurations": n,
            "rows": {kw: len(v) for kw, v in rows.items()}}


def _glass_key(g):
    """Identity of a parsed GLAS line for comparing configurations (name, MIRROR, or model / code values)."""
    if g is None:
        return None
    up = g["name"].upper()
    if up == "MIRROR":
        return ("mirror", "MIRROR")
    if up == "___BLANK" or (g["name"].isdigit() and len(g["name"]) == 6):
        tk = g["tokens"]
        return ("model", g["name"], tk[2] if len(tk) > 2 else None, tk[3] if len(tk) > 3 else None)
    return ("name", g["name"])


def lens_file_write(prescription=None, system=None, path=None, encoding: str = "ascii") -> dict:
    """処方を、:func:`lens_file_read` と設計ソフトが読める ``.zmx`` のテキストに書く(``table``)。

    *prescription* is the dict from :func:`lens_file_read` (``None``: the
    bundled example). *system* — optional — is an edited ``raytrace.lens_system``
    (for example the output of ``lensopt.optimize_lens``): its radii, thicknesses,
    conics, aspheric terms and media replace the prescription's surfaces while
    the fields, wavelengths, aperture type, comments and still-valid solves are
    kept (a solve whose value was edited is dropped from the output and listed
    in ``dropped_solves``). The stop size is written as the system aperture: an
    entrance-pupil diameter (``ENPD``) recomputed from *system* when the
    prescription used ``ENPD`` or ``FNUM``.

    *path* (optional) writes the file; *encoding* ``"ascii"`` (default, plain
    text that diffs well) or ``"utf-16"`` (with byte-order mark, what current
    design programs save). Media: an ``(n_d, V_d)`` pair or a plain index becomes
    a model glass, a catalogue name or ``.agf`` record its name with n_d / V_d
    on the line; a custom Sellmeier medium without a catalogue name is refused
    (a reader could not resolve it). *system* may also be a
    ``raytrace3d.noncoaxial_system`` (the prescription is then optional): its break
    and return elements become ``COORDBRK`` surfaces (order flag 0 / 1 for the
    tracer's "xyz" / "zyx" breaks), an entrance-pupil diameter is recomputed from the stop radius.
    Refused: a beamsplitter surface, a per-surface decenter / tilt (put a break
    around it), a tilted image or object plane, a return across an odd number of
    reflections or one that would need a negative thickness. A coaxial
    ``raytrace.lens_system`` with tilted / decentred surfaces is still refused.

    A *system* (or a prescription's system) that carries ``configurations`` is written as a multi-
    configuration file: configuration 1 as the surface blocks, then ``MNUM`` and one row per varying
    thickness / curvature / glass / aspheric parameter and configuration (see the module help for what is
    refused); the result then also has ``n_configurations`` and ``rows`` (row counts per operand).

    Returns ``{"text", "path", "n_surfaces", "encoding", "dropped_solves"}``.

    Example::

        p = lens_file_read("triplet.zmx")
        best = lensopt.optimize_lens(p["system"])["system"]
        lens_file_write(p, system=best, path="triplet_reoptimised.zmx")
    """
    op = "lens_file_write"
    if prescription is None and system is not None and _is_nc(system):
        p = _header_from_nc(system, op)
    else:
        p = lens_file_read(None) if prescription is None else _check_prescription(prescription, op)
    if encoding not in ("ascii", "utf-16"):
        raise ValueError("%s: encoding must be 'ascii' or 'utf-16', got %r" % (op, encoding))
    sys_in = system if system is not None else p["system"]
    if not _is_nc(sys_in) and sys_in.get("configurations") and len(sys_in["configurations"]) > 1:
        return _write_multi(p, sys_in, path, encoding, op)
    if not _is_nc(sys_in) and sys_in.get("configurations"):
        system = LC.lens_with_configuration(sys_in, 0)            # one configuration: a plain single-config file
    dropped = []
    if system is not None:
        surfs = _surfaces_from_system(system, p["surfaces"], op)
        for a, b in zip(p["surfaces"] or [], surfs):
            if a.get("curv_solve") and not b.get("curv_solve"):
                dropped.append({"surface": a["index"], "what": "curvature solve"})
            if a.get("pzup") and not b.get("pzup"):
                dropped.append({"surface": a["index"], "what": "thickness pickup"})
            if a.get("ppar") and not b.get("ppar"):
                dropped.append({"surface": a["index"], "what": "parameter pickup"})
        sysd = system
    else:
        surfs = p["surfaces"]
        sysd = p["system"]
    ap = p["aperture"]
    nc = _is_nc(sysd)
    para = None if nc else RT.paraxial_trace(sysd)
    lines = ["VERS 0", "MODE SEQ"]
    if p.get("name"):
        lines.append("NAME " + p["name"])
    for nt in p.get("notes", []):
        lines.append("NOTE 0 " + nt)
    lines.append("UNIT MM X W X CM MR CPMM")
    if ap["type"] == "FLOA":
        lines.append("FLOA")
    elif ap["type"] == "FNUM" and system is None:
        lines.append("FNUM %s %d" % (_g(ap["value"]), ap["kind"]))
    elif ap["type"] == "OBNA" and system is None:
        lines.append("OBNA %s %d" % (_g(ap["value"]), ap["kind"]))
    elif nc:
        lines.append("ENPD %s" % _g(ap["value"] if system is None and ap["type"] == "ENPD" else _nc_enpd(sysd)))
    else:
        lines.append("ENPD %s" % _g(2.0 * para["ep_radius"]))
    lines.append("ENVD 20 1 0")
    ftcode = {v: k for k, v in _FIELD_TYPES.items()}[p["field_type"]]
    nf, nw = len(p["fields"]), len(p["wavelengths"])
    if nf > 12:
        raise ValueError("%s: the format holds at most 12 fields (got %d)" % (op, nf))
    lines.append("FTYP %d 0 %d %d 0 0 0" % (ftcode, nf, nw))
    pad = 12 - nf
    lines.append("XFLN " + " ".join([_g(f["x"]) for f in p["fields"]] + ["0"] * pad))
    lines.append("YFLN " + " ".join([_g(f["y"]) for f in p["fields"]] + ["0"] * pad))
    lines.append("FWGN " + " ".join([_g(f["weight"]) for f in p["fields"]] + ["1"] * pad))
    vfields = _vignetting_for_write(p["fields"], system)
    if any(v[k] != 0.0 for v in vfields for k in _VIG_FIELD_KEYS):
        for kw, key in (("VDXN", "vdx"), ("VDYN", "vdy"), ("VCXN", "vcx"), ("VCYN", "vcy"), ("VANN", "van")):
            lines.append(kw + " " + " ".join([_g(v[key]) for v in vfields] + ["0"] * pad))
    for k, w in enumerate(p["wavelengths"], 1):
        lines.append("WAVM %d %s %s" % (k, _g(w["um"]), _g(w["weight"])))
    lines.append("PWAV %d" % (p["primary"] + 1))
    for sf in surfs:
        lines.append("SURF %d" % sf["index"])
        if sf.get("stop"):
            lines.append("  STOP")
        lines.append("  TYPE %s" % sf["type"])
        if sf.get("comment"):
            lines.append("  COMM %s" % sf["comment"])
        cs = sf.get("curv_solve")
        lines.append("  CURV %s %s \"\"" % (_g(sf["curv"]), " ".join(cs + ["0"] * (4 - len(cs))) if cs else "0 0 0 0"))
        if sf["type"] == "EVENASPH":
            for k in sorted(sf["parm"]):
                lines.append("  PARM %d %s" % (k, _g(sf["parm"][k])))
        elif sf["type"] == "COORDBRK":
            for k in range(1, 7):
                lines.append("  PARM %d %s" % (k, _g(sf["parm"].get(k, 0.0))))
        for (pn, src, scale, off) in sf.get("ppar") or []:
            lines.append("  PPAR %d %d %s %s 0" % (pn, src, _g(scale), _g(off)))
        lines.append("  DISZ %s" % _g(sf["disz"]))
        if sf.get("pzup"):
            lines.append("  PZUP " + " ".join(sf["pzup"]))
        g = sf.get("glass")
        if g is not None:
            if g["kind"] == "mirror":
                lines.append("  GLAS MIRROR 0 0 1.5 40 0 0 0 0 0 0")
            elif g["kind"] == "model":
                lines.append("  GLAS ___BLANK 1 0 %s %s 0 0 0 0 0 0" % (_g(g["nd"]), _g(g["vd"])))
            else:
                lines.append("  GLAS %s 0 0 %s %s 0 0 0 0 0 0" % (g["name"], _g(g["nd"]), _g(g.get("vd", 0.0))))
        if sf.get("conic", 0.0) != 0.0:
            lines.append("  CONI %s" % _g(sf["conic"]))
        if sf.get("diam", 0.0) > 0.0:
            lines.append("  DIAM %s %d 0 0 1 \"\"" % (_g(sf["diam"]), int(sf.get("diam_type", 0))))
        a = sf.get("aperture")
        if a is not None and a["r"] > 0.0:
            lines.append("  %s 0 %s 0" % (a["kind"], _g(a["r"])))
    text = "\n".join(lines) + "\n"
    if path is not None:
        data = text.encode("utf-16") if encoding == "utf-16" else text.encode("ascii", errors="strict")
        with io.open(path, "wb") as fh:
            fh.write(data)
    return {"text": text, "path": path, "n_surfaces": len(surfs), "encoding": encoding, "dropped_solves": dropped}


def lens_file_report(source=None) -> dict:
    """``.zmx`` を読み込まずに分類する —— 何を読み / 無視し / 拒否するか(``table``)。

    Parses every line and classifies each keyword — never raises for an
    unsupported feature (that is what it reports); it raises only for text that
    is not a prescription at all. Returns ``{"source", "encoding", "n_surfaces",
    "surface_types", "importable", "needs_allow_partial", "read", "ignored",
    "unsupported", "notes", "error"}``: ``importable`` is True when
    :func:`lens_file_read` succeeds without ``allow_partial``,
    ``needs_allow_partial`` when it succeeds only with it, and ``error`` is the
    refusal message otherwise. Use it to triage a folder of files.

    Example::

        r = lens_file_report("legacy_design.zmx")
        r["importable"], [u["message"] for u in r["unsupported"]]
    """
    op = "lens_file_report"
    text, label, enc = _source_text(source, op)
    top, surfs, rep = _parse(text, op)
    if not surfs:
        raise ValueError("%s: no SURF record — not a sequential prescription" % op)
    types = {}
    for sf in surfs:
        types[sf["type"]] = types.get(sf["type"], 0) + 1
    importable, partial, err = False, False, None
    try:
        lens_file_read(text, allow_partial=False)
        importable = True
    except ValueError as e:
        err = str(e)
        try:
            lens_file_read(text, allow_partial=True)
            partial = True
        except ValueError as e2:
            err = str(e2)
    # re-run the build on a copy to collect the unsupported list the way the importer sees it
    rep2 = _Report()
    rep2.read, rep2.ignored, rep2.unsupported, rep2.notes = dict(rep.read), dict(rep.ignored), list(rep.unsupported), []
    try:
        _build(top, [dict(sf, parm=dict(sf["parm"]), aperture=(dict(sf["aperture"]) if sf["aperture"] else None))
                     for sf in surfs], rep2, op, True, None)
    except ValueError:
        pass
    d = rep2.as_dict()
    return {"source": label, "encoding": enc, "n_surfaces": len(surfs), "surface_types": types,
            "importable": importable, "needs_allow_partial": partial, "read": d["read"], "ignored": d["ignored"],
            "unsupported": d["unsupported"], "notes": d["notes"], "error": err}
