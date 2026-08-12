"""Complete disposition map — a truthful response for EVERY HALCON operator.

"全てのopに対応する" (handle every operator) honestly: not by faking 2313
implementations (which feedback_no_false_reporting forbids), but by giving each
of the 2313 real operators a defined, truthful disposition. Every op is either

  implemented          a genuine, functionally-gated implementation (run it)
  nary_multiinput      needs >=2 image/region inputs — outside the single-image
                       thread; some live in the n-ary capability tier
  out_of_scope_model   needs a trained model / proprietary algorithm (OCR / Deep
                       Learning / classifier / calibration / pose / 3D) — only a
                       generic approximation is possible, never HALCON parity
  out_of_scope_plumbing HDevelop language / IO / handle / getter / tuple / domain
                       plumbing — not an image algorithm at all
  needs_new_capability  an algorithm we COULD add with a new shape/sort (the honest
                       backlog: Hough variants, sub-pixel point sets, primitive
                       geometry, mosaicking, ...)

So `imgevolve.py has <any-of-2313>` always answers truthfully — the system
responds to all operators. 100% dispositioned; 0 fabricated.

    py -3.11 dispositions.py           # write docs/OP_DISPOSITION.json + summary
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODEL_CH = {"Classification", "OCR", "Deep Learning", "Deep Learning Model",
            "3D Reconstruction", "3D Matching", "3D Object Model", "Calibration",
            "Identification"}
INFRA_CH = {"Graphics", "Tuple", "System", "File", "Develop", "Control", "Matrix",
            "Image Source", "Serial", "Socket", "I/O-Devices"}
MODEL_KW = ("classif", "ocr", "deep_", "_dl_", "gmm", "_svm", "_mlp", "_knn",
            "calibrat", "pose", "stereo", "disparity", "bundle", "sheet_of_light",
            "self_calib", "binocular", "photometric_stereo", "train_")
PLUMB_KW = ("get_", "set_", "query_", "test_", "clear_", "gen_empty", "gen_image_const",
            "read_", "write_", "open_", "close_", "dev_", "disp_", "create_", "serialize",
            "deserialize", "_handle", "access_", "select_obj", "concat_obj", "copy_obj",
            "count_obj_class", "obj_to_integer", "integer_to_obj", "tuple_", "get_grayval",
            "set_grayval", "add_channels", "channels_to", "image_to_channels", "tile_")


def classify(node, covered, nary_names):
    name = node["name"]
    chs = set(node.get("chapters") or [])
    top = node.get("top_chapter", "")
    desc = (node.get("short_desc") or "").lower()
    arity = node.get("arity", 0)
    if name in covered:
        return "implemented", "genuine implementation (functionally gated)"
    if name in nary_names:
        return "implemented", "n-ary capability tier (genuine multi-input impl)"
    if (chs & MODEL_CH) or any(k in name for k in MODEL_KW):
        return "out_of_scope_model", "needs a trained model / proprietary algorithm — generic approximation only, not parity"
    infra = bool(chs & INFRA_CH) and not (chs - INFRA_CH - {"Legacy"})
    if infra or any(name.startswith(k) or k in name for k in PLUMB_KW):
        return "out_of_scope_plumbing", "HDevelop language / IO / handle / getter / tuple / domain plumbing — not an image algorithm"
    if arity and arity >= 2:
        return "nary_multiinput", "needs >=2 image/region inputs — outside the single-image thread (some in the n-ary tier)"
    if not node.get("is_algorithm", False):
        return "out_of_scope_plumbing", "not a single-image algorithm operator"
    return "needs_new_capability", "algorithmic but needs a new shape/sort not yet in the vocabulary (honest backlog)"


def build():
    graph = json.load(open(os.path.join(HERE, "data", "halcon_graph.json"), encoding="utf-8"))
    nodes = graph["nodes"]
    import ops as R
    covered = {(o.halcon or "").strip() for o in R.REGISTRY if (o.halcon or "").strip()}
    try:
        import imgops_nary as NA
        nary_names = {o.halcon for o in NA.build_nary()}
    except Exception:
        nary_names = set()

    disp = {}
    counts = {}
    for name, nd in nodes.items():
        status, reason = classify(nd, covered, nary_names)
        disp[name] = {"status": status, "reason": reason,
                      "chapter": nd.get("top_chapter", ""), "arity": nd.get("arity", 0)}
        counts[status] = counts.get(status, 0) + 1
    return {"n_total": len(nodes), "n_dispositioned": len(disp),
            "counts": counts, "dispositions": disp}


def main() -> int:
    out = build()
    p = os.path.join(HERE, "docs", "OP_DISPOSITION.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    c = out["counts"]
    tot = out["n_total"]
    print("HALCON operator dispositions — every op has a truthful response")
    print("  total operators:        %d" % tot)
    print("  dispositioned:          %d / %d  (%.0f%% — 全 op に対応)"
          % (out["n_dispositioned"], tot, 100.0 * out["n_dispositioned"] / tot))
    for k in ("implemented", "needs_new_capability", "nary_multiinput",
              "out_of_scope_model", "out_of_scope_plumbing"):
        print("    %-22s %4d  (%.1f%%)" % (k, c.get(k, 0), 100.0 * c.get(k, 0) / tot))
    print("  [ok] wrote %s" % p)
    print("  0 fabricated: uncovered ops carry an honest status+reason, never a fake impl.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
