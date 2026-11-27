"""The one-way ledger of Studio 1.2.0's common gates (STUDIO_INTERACTION_RULES 2026-11-13 5.0 / 5.1, BRIEFS B3).

    py -3.11 tools/studio_interaction_ledger.py --check    exit 1 when a gate found more than the ledger (or new items)
    py -3.11 tools/studio_interaction_ledger.py --shrink   remove the items that are fixed, rewrite the ledger
                                                           (what is new is NOT added: fix it, or add it by hand with a
                                                           reason and an independent review)
    py -3.11 tools/studio_interaction_ledger.py --report   the table gate x count x D numbers
    py -3.11 tools/studio_interaction_ledger.py --create   write the ledger from what the gates find now (step 2 only)

The counts are the ones of tests/test_studio_interaction_gates_2026_11_13.py (the same functions in
tests/studio_gatekit.py). The window is built offscreen with a throw-away settings file, APPDATA and LOCALAPPDATA,
so the user's settings, desktop and data folder are never touched.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "tests" / "data" / "studio_interaction_ledger.json"


def _isolate(tmp):
    """Offscreen, and every place Studio could write points into ``tmp`` (set before Qt / studio are imported)."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["FULLSEYE_STUDIO_SETTINGS"] = str(Path(tmp) / "ledger_tool.ini")
    for name in ("APPDATA", "LOCALAPPDATA"):
        p = Path(tmp) / name.lower()
        p.mkdir(parents=True, exist_ok=True)
        os.environ[name] = str(p)
    os.environ.pop("FULLSEYE_STUDIO_PERSIST_LAYOUT", None)


def _kit():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("studio_gatekit", ROOT / "tests" / "studio_gatekit.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["studio_gatekit"] = mod
    spec.loader.exec_module(mod)
    return mod


def _newline(path):
    try:
        return "\r\n" if b"\r\n" in Path(path).read_bytes() else "\n"
    except FileNotFoundError:
        return "\n"


def _write(data, path=LEDGER):
    nl = _newline(path)
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(text.replace("\n", nl).encode("utf-8"))


def _sorted(items):
    return sorted(items, key=lambda i: (i["where"], i["text"]))


def report(kit, gates, found=None):
    """The table: gate | ledger count | found now (when counted) | D numbers of the items."""
    lines = ["gate          | ledger | now  | D numbers (items per D)", "-" * 78]
    for gate in kit.GATES:
        led = gates[gate]
        per = {}
        for i in led["items"]:
            per[i["d"]] = per.get(i["d"], 0) + 1
        ds = " ".join("%s:%d" % (d, n) for d, n in sorted(per.items())) or "-"
        now = "" if found is None else str(len(found[gate][0]))
        lines.append("%-13s | %6d | %4s | %s" % (gate, led["count"], now, ds))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--shrink", action="store_true")
    g.add_argument("--report", action="store_true")
    g.add_argument("--create", action="store_true")
    ap.add_argument("--no-count", action="store_true", help="--report: print the ledger without counting")
    args = ap.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="studio_ledger_", ignore_cleanup_errors=True) as tmp:
        _isolate(tmp)
        kit = _kit()
        if args.report and args.no_count:
            print(report(kit, kit.load_ledger()))
            return 0
        found = kit.count_everything(Path(tmp) / "gates.ini")
        for gate, (_items, examined) in found.items():
            kit.at_least(examined, kit.FLOORS[gate], gate)
        if args.create:
            data = {"_note": ("Studio 1.2.0 common gates: one-way ledger (more than this fails; fixed items are "
                              "removed with --shrink). Written by tools/studio_interaction_ledger.py --create on "
                              "the integration tree after step 2 (STUDIO_INTERACTION_RULES 5.0). D numbers are "
                              "given from the kind of place, as a guide."),
                    "gates": {gate: {"title": kit.GATES[gate][0], "owners": kit.GATES[gate][1],
                                     "count": len(found[gate][0]), "examined_at_creation": found[gate][1],
                                     "items": _sorted(found[gate][0])} for gate in kit.GATES}}
            _write(data)
            print(report(kit, data["gates"], found))
            return 0
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
        gates = data["gates"]
        bad = 0
        for gate in kit.GATES:
            new, fixed = kit.compare(gate, found[gate][0], gates)
            if new:
                bad += 1
                print("%s: %d NEW (not in the ledger):" % (gate, len(new)))
                for i in new[:60]:
                    print("   %s | %s | %s" % (i["d"], i["where"], i["text"]))
            if fixed:
                print("%s: %d fixed (in the ledger, not found now)%s" % (
                    gate, len(fixed), " -> removed" if args.shrink else ""))
                if args.shrink:
                    gone = {kit.key_of(i) for i in fixed}
                    gates[gate]["items"] = _sorted(i for i in gates[gate]["items"] if kit.key_of(i) not in gone)
                    gates[gate]["count"] = len(gates[gate]["items"])
        if args.shrink:
            _write(data)
        print(report(kit, gates, found))
        if args.check or args.shrink:
            return 1 if bad else 0
        return 0


if __name__ == "__main__":
    sys.exit(main())
