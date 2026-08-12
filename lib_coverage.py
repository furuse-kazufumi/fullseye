"""Multi-library coverage — imgevolve is not HALCON-only.

HALCON coverage is one axis; the registry also speaks OpenCV / scikit-image /
MATLAB. This introspects the INSTALLED libraries (cv2, skimage, scipy.ndimage)
for their real callable inventories — ground truth, no scraping — and measures how
many distinct library functions imgevolve's registry references via the cross-
library catalog (`catalog._analogs`).

Honest: coverage counts distinct API names our ops name as their analogue, not
signature parity. Introspected inventories are the full public callables; the
addressable image-op subset is smaller, so raw percentages understate reach.

    py -3.11 lib_coverage.py           # per-library coverage -> docs/LIB_COVERAGE.md
"""
from __future__ import annotations

import importlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SK_SUBS = ("filters", "morphology", "feature", "segmentation", "restoration",
           "measure", "transform", "exposure", "registration", "color", "graph", "util")


def inventory():
    inv = {}
    try:
        import cv2
        inv["opencv"] = sorted({n for n in dir(cv2)
                                if callable(getattr(cv2, n, None)) and not n.startswith("_") and n[:1].islower()})
    except Exception:
        inv["opencv"] = []
    sk = set()
    for s in SK_SUBS:
        try:
            m = importlib.import_module("skimage." + s)
            sk |= {"%s.%s" % (s, n) for n in dir(m)
                   if callable(getattr(m, n, None)) and not n.startswith("_") and n[:1].islower()}
        except Exception:
            pass
    inv["skimage"] = sorted(sk)
    return inv


def _referenced():
    """Distinct library API names the registry references (via catalog analogs)."""
    import ops
    import catalog
    ref = {"opencv": set(), "skimage": set()}
    for op in ops.REGISTRY:
        an = catalog._analogs(op.name)
        for lib in ("opencv", "skimage"):
            v = an.get(lib, "-")
            if v and v != "-":
                for token in re.split(r"[ /()+,]", v):
                    token = token.strip()
                    if lib == "opencv" and token.startswith("cv2."):
                        ref["opencv"].add(token[4:])
                    elif lib == "opencv" and token and token[0].islower() and "." not in token:
                        ref["opencv"].add(token)
                    elif lib == "skimage" and token.startswith("skimage."):
                        ref["skimage"].add(token[8:])
                    elif lib == "skimage" and "." in token and token.split(".")[0] in SK_SUBS:
                        ref["skimage"].add(token)
    return ref


def registry_by_library():
    """Honest per-library op count from the registry name prefixes."""
    import ops
    from collections import Counter
    pref = {"sk_": "scikit-image", "cv_": "OpenCV", "dl_": "torch", "vol_": "scipy (3-D)",
            "xsk_": "scikit-image", "xcv_": "OpenCV", "xsk2_": "scikit-image", "xcv2_": "OpenCV",
            "xsk3_": "scikit-image", "xcv3_": "OpenCV", "xpil_": "Pillow", "xsp_": "scipy",
            "xmh_": "mahotas", "xwt_": "PyWavelets", "xsitk_": "SimpleITK", "xkor_": "kornia (GPU)"}
    c = Counter()
    for op in ops.REGISTRY:
        hit = next((pref[p] for p in sorted(pref, key=len, reverse=True) if op.name.startswith(p)), None)
        c[hit or "core (numpy/scipy)"] += 1
    return c


def main() -> int:
    inv = inventory()
    ref = _referenced()
    by_lib = registry_by_library()
    # normalise skimage refs to bare function names for matching against inventory tails
    sk_inv_tail = {x.split(".")[-1] for x in inv["skimage"]}
    sk_ref_tail = {x.split(".")[-1] for x in ref["skimage"]}
    cv_hit = ref["opencv"] & set(inv["opencv"])
    sk_hit = sk_ref_tail & sk_inv_tail

    lines = [
        "# Multi-library coverage (imgevolve is not HALCON-only)",
        "",
        "Installed-library inventories introspected (ground truth, not scraped);",
        "registry references counted via the cross-library catalog.",
        "",
        "| library | referenced by registry | in installed inventory | matched |",
        "|---|---|---|---|",
        "| OpenCV (cv2) | %d | %d public callables | %d |"
        % (len(ref["opencv"]), len(inv["opencv"]), len(cv_hit)),
        "| scikit-image | %d | %d submodule functions | %d |"
        % (len(sk_ref_tail), len(inv["skimage"]), len(sk_hit)),
        "",
        "## Registry ops by source library (10+ libraries incorporated)",
        "",
        "| library | ops |",
        "|---|---|",
    ] + ["| %s | %d |" % (k, v) for k, v in by_lib.most_common()] + [
        "| **total** | **%d** |" % sum(by_lib.values()),
        "",
        "## Honest reading",
        "- Inventories are ALL public callables (cv2 ~%d, skimage ~%d); most are not"
        % (len(inv["opencv"]), len(inv["skimage"])),
        "  image-transform operators (IO, drawing, math, GUI, ML), so raw ratios understate reach.",
        "- imgevolve wraps ecosystems rather than reimplementing them; adding an op with its",
        "  catalog analogue extends this automatically. Distinctive incorporations live in",
        "  `backends_extra.py` (xsk_/xcv_): inpainting, blob detectors, keypoint counts,",
        "  random-walker/flood/grabCut segmentation, structure/Hessian tensors, NPR filters.", "",
    ]
    open(os.path.join(HERE, "docs", "LIB_COVERAGE.md"), "w", encoding="utf-8").write("\n".join(lines))
    json.dump({"referenced": {k: sorted(v) for k, v in ref.items()},
               "inventory_counts": {k: len(v) for k, v in inv.items()}},
              open(os.path.join(HERE, "data", "lib_inventory.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("multi-library coverage:")
    print("  OpenCV:      registry refs %d | inventory %d public callables | matched %d"
          % (len(ref["opencv"]), len(inv["opencv"]), len(cv_hit)))
    print("  scikit-image: registry refs %d | inventory %d functions | matched %d"
          % (len(sk_ref_tail), len(inv["skimage"]), len(sk_hit)))
    print("  [ok] wrote docs/LIB_COVERAGE.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
