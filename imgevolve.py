"""imgevolve — single CLI entry point (designed to be usable by a future agent).

A future Claude Code session should be able to *use* this HALCON-parity library
without re-reading the source. Discover and invoke everything from here:

    py -3.11 imgevolve.py ops                    # list every implemented operator
    py -3.11 imgevolve.py ops --search edge      # search (registry + typed ledgers)
    py -3.11 imgevolve.py ops --sort region      # filter by input sort
    py -3.11 imgevolve.py ops find icp           # cross-layer search == fullseye.op_find
    py -3.11 imgevolve.py ops describe otsu      # one op, same shape in every tier
    py -3.11 imgevolve.py ops path image region  # chain types A -> B (== fullseye.op_path)
    py -3.11 imgevolve.py ops find icp --json    # stdout is JSON only (notes go to stderr)
    py -3.11 imgevolve.py has gauss_filter       # is a HALCON op implemented? how to call it
    py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
    py -3.11 imgevolve.py pipeline in.png out.png --ops "gauss_filter,sobel_amp,otsu"
    py -3.11 imgevolve.py coverage               # honest coverage numbers
    py -3.11 imgevolve.py index                  # (re)write docs/OP_INDEX.json (machine-readable)
    py -3.11 imgevolve.py algo list              # general-algorithm tier (sorts/reductions)
    py -3.11 imgevolve.py algo run quicksort --seq 3,1,2   # -> [1.0, 2.0, 3.0]
    py -3.11 imgevolve.py algo emit-c mergesort  # standalone, compilable C
    py -3.11 imgevolve.py algo difftest all      # honest gate (Python==oracle, C==Python bit-for-bit)
    py -3.11 imgevolve.py synth in.png out.png   # learn a texture -> synthesise a similar image
    py -3.11 imgevolve.py synth in.png out.png --method patch --size 320x320

Sorts: image (gray H*W [0,1]) / color (H*W*3 RGB) / region (binary) / feature
(scalar) / contour (XLD) / volume (3-D). `apply` loads the input to match the
op's in_sort and serialises the output by its out_sort (feature -> printed,
contour -> point count + optional raster).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _load_registry():
    import ops
    return ops


def _all_ops():
    """Every operator across the three tiers, as uniform dicts."""
    ops = _load_registry()
    rows = [{"name": o.name, "halcon": o.halcon, "in_sort": o.in_sort,
             "out_sort": o.out_sort, "category": o.category, "tier": "registry"}
            for o in ops.REGISTRY]
    # ★握り潰さない(2026-09-06 の敵対的レビュー)。`imgops_nary` は numpy と
    # scipy しか要らない一次モジュールなので、import に失敗するのは「壊れた
    # checkout」であって「その環境には無い機能」ではない。以前は
    # `except Exception: pass` で、**この関数が生成器と検査の両方を兼ねている**
    # ため、17 op が丸ごと消えた索引を CI が緑のまま公開できた。
    import imgops_nary as NA
    rows += [{"name": o.name, "halcon": o.halcon, "in_sort": o.in_sorts[0],
              "out_sort": o.out_sort, "category": "nary", "tier": "nary",
              "arity": o.arity, "in_sorts": list(o.in_sorts)}
             for o in NA.build_nary()]
    assert len(rows) > len(ops.REGISTRY), "nary 層が空(build_nary が何も返さない)"
    return rows


# ---- image I/O ------------------------------------------------------------- #
def _imread(path, sort):
    import cv2
    if sort == "color":
        im = cv2.imread(path, cv2.IMREAD_COLOR)
        if im is None:
            raise SystemExit("cannot read %s" % path)
        return (im[:, :, ::-1].astype(np.float64)) / 255.0     # BGR->RGB
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if im is None:
        raise SystemExit("cannot read %s" % path)
    g = im.astype(np.float64) / 255.0
    return (g > 0.5).astype(np.float64) if sort == "region" else g


def _imwrite(path, v):
    import cv2
    v = np.asarray(v)
    if v.ndim == 3 and v.shape[-1] == 3:
        out = np.clip(v * 255, 0, 255).astype(np.uint8)[:, :, ::-1]     # RGB->BGR
    else:
        out = np.clip(np.asarray(v, np.float64) * 255, 0, 255).astype(np.uint8)
    cv2.imwrite(path, out)


# ---- subcommands ----------------------------------------------------------- #
# ★入口の統一(2026-09-15)。それまで CLI は **レジストリ + HALCON 名しか見て
# いなかった**ので、`ops --search icp` は 0 件、`has frame_align` は exit 1 だった
# —— どちらも台帳(33 族 1,024 op)には**在る**。一方 `fullseye.op_find` は最初から
# 全層を横断している。つまり「無い」ではなく「**この入口からは見えない**」で、
# 呼ぶ側にその 2 つは区別できない([[feedback_registered_only_gates_miss_unregistered]])。
# `ops find|describe|path` は `fs.op_find` / `fs.op_assist` / `fs.op_path` と
# **同じ集合**を CLI から出す。どの層から来た情報かは必ず `tier` で言う。
def _note(msg, a):
    """人向けの注記。``--json`` のときは stdout を汚さないよう stderr へ。"""
    print(msg, file=sys.stderr if getattr(a, "json", False) else sys.stdout)


def _emit(obj):
    """``--json``: stdout は JSON だけ。"""
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")


def _frontmatter(path):
    """op ノートの frontmatter を最小限だけ読む(YAML 依存を持たない)。"""
    if not path or not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    for ln in lines[1:]:
        if ln.strip() == "---":
            break
        k, sep, v = ln.partition(":")
        if not sep:
            continue
        v = v.split("#")[0].strip()
        if v.startswith("[") and v.endswith("]"):
            v = [t.strip() for t in v[1:-1].split(",") if t.strip()]
        out[k.strip()] = v
    return out


def _op_rows():
    """索引の全行を ``name -> 行`` で(registry / color / nary / ledger の 4 層)。"""
    return {r["name"]: r for r in _build_op_index()["ops"]}


def _note_record(name):
    """``fullseye/data/OP_NOTES.json`` から op ノートの 1 件目(無ければ None)。"""
    p = os.path.join(HERE, "fullseye", "data", "OP_NOTES.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            recs = json.load(fh).get("notes", {}).get(name)
    except (OSError, ValueError):
        return None
    return recs[0] if recs else None


def _call_form(row):
    """その op の**呼び方**。層で違うことを黙らせない。"""
    tier, name = (row or {}).get("tier"), (row or {}).get("name", "?")
    if tier == "ledger":
        return 'fullseye.op_run("%s", ...) / fullseye.%s(...)' % (name, name)
    if tier == "nary":
        return "imgops_nary.build_nary() —— %d 入力" % (row.get("arity") or 2)
    if tier in ("registry", "color"):
        return 'fullseye.apply(img, "%s", a, b) / imgevolve.py apply %s <in> <out>' % (name, name)
    return "(不明)"


def _layer_census():
    """いま**実際に見た**層の内訳(「0 件」と「見ていない」を区別するため)。"""
    idx = _build_op_index()
    return {"n_ops": idx["n_ops"], "tiers": idx["tiers"], "n_sorts": len(idx["sorts"])}


def _census_line(c):
    return ("見た層: " + " / ".join("%s %d" % (k, v) for k, v in sorted(c["tiers"].items()))
            + " = %d op(型語彙 %d)" % (c["n_ops"], c["n_sorts"]))


def _describe_op(name):
    """どの層の op でも**同じ形**で返す(見つからなければ None)。例外は投げない。

    台帳 op は :func:`fullseye.op_assist` そのもの。レジストリ側(`op_assist` が
    ``ValueError`` を投げる op)は**索引 + ノートの frontmatter**から同じキーに
    整える —— 呼ぶ側が層ごとに分岐しなくて済むように。
    """
    import opassist
    row = _op_rows().get(name)
    try:
        d = opassist.assist(name)
        d["tier"] = (row or {}).get("tier", "ledger")
        d["source"] = "opassist.assist(型付き台帳)"
    except ValueError:
        if row is None:
            return None
        rec = _note_record(name) or {}
        fm = _frontmatter(os.path.join(HERE, rec["path"].replace("/", os.sep))) if rec.get("path") else {}
        doc = ""
        if row["tier"] in ("registry", "color"):
            op = _find_op(_load_registry(), name)
            doc = ((getattr(op, "fn", None).__doc__ or "").strip().splitlines() or [""])[0] if op else ""
        params = [{"name": "image", "kind": "data", "sort": row.get("in_sort"), "required": True}]
        if row["tier"] in ("registry", "color"):
            params += [{"name": k, "kind": "number", "default": 0.5, "required": False,
                        "doc": "つまみ %s ∈ [0,1](2-D レジストリは 1 画像 + 2 スカラ)" % k}
                       for k in ("a", "b")]
        d = {"op": name, "ledger": "ops", "module": row.get("ledger") or "ops",
             "category": row.get("category"), "doc": doc or fm.get("op", ""),
             "params": params, "presets": {}, "inputs": {}, "next": [],
             "preflight": [], "accepts": {},
             "tier": row["tier"],
             "source": "docs/OP_INDEX.json + ノートの frontmatter(op_assist は台帳専用)"}
        # 「その型を作れる op / 受け取れる op」は台帳側の知識。引けなくても
        # describe は落とさない(補助情報であって、この op の仕様ではない)。
        in_sort, out_sort = row.get("in_sort"), row.get("out_sort")
        try:
            d["inputs"] = {in_sort: opassist.producers(in_sort)} if in_sort else {}
        except Exception:                                # noqa: BLE001 — 補助情報
            d["inputs"] = {}
        try:
            d["next"] = opassist.consumers(out_sort) if out_sort else []
        except Exception:                                # noqa: BLE001 — 補助情報
            d["next"] = []
        d["note"] = rec.get("path")
        d["examples"] = fm.get("examples", [])
    row = row or {"tier": d.get("tier"), "name": name}
    row.setdefault("name", name)
    d["dim"] = row.get("dim") or ("2d" if row.get("tier") in ("registry", "color", "nary") else "")
    d["in_sort"], d["out_sort"] = row.get("in_sort"), row.get("out_sort")
    d["halcon"] = row.get("halcon") or ""
    d["call"] = _call_form(row)
    return d


def _cmd_ops_find(a):
    """`fs.op_find` の横断検索(registry / color / nary / 台帳 33 族)をそのまま出す。"""
    import opassist
    q = " ".join(a.args).strip()
    if not q:
        _note("find は探す語が要る: imgevolve.py ops find icp", a)
        return 2
    lim = max(int(a.limit), 1)
    idx = _op_rows()
    rows = []
    # 絞り込み(--dim/--in/--out)で落ちる分を見越して広めに引いてから切る。
    for h in opassist.find(q, limit=lim * 8 if (a.dim or a.in_sort or a.out_sort) else lim):
        r = idx.get(h["op"], {})
        tier = r.get("tier") or ("registry" if h["ledger"] == "ops" else "ledger")
        row = {"op": h["op"], "tier": tier, "ledger": h["ledger"], "module": h["module"],
               "dim": r.get("dim") or ("2d" if tier in ("registry", "color", "nary") else ""),
               "category": h["category"], "in_sort": r.get("in_sort"), "out_sort": r.get("out_sort"),
               "halcon": r.get("halcon") or "", "call": h["call"], "score": h["score"],
               "doc": h["doc"]}
        if a.dim and row["dim"] != a.dim:
            continue
        if a.in_sort and row["in_sort"] != a.in_sort:
            continue
        if a.out_sort and row["out_sort"] != a.out_sort:
            continue
        rows.append(row)
    rows = rows[:lim]
    if a.json:
        _emit(rows)
        return 0
    for r in rows:
        print("%-26s %-9s->%-9s [%s/%s] score=%-3d %s"
              % (r["op"], r["in_sort"] or "-", r["out_sort"] or "-", r["tier"],
                 r["dim"] or r["category"] or "-", r["score"], (r["doc"] or "")[:60]))
    c = _layer_census()
    print("--- %d hits for %r ---" % (len(rows), q))
    print(_census_line(c))
    return 0


def _cmd_ops_describe(a):
    """1 op の仕様を層に関係なく同じ形で。**どの層から来たかを必ず言う**。"""
    import opassist
    if len(a.args) != 1:
        _note("describe は op 名を 1 つ: imgevolve.py ops describe otsu", a)
        return 2
    name = a.args[0]
    d = _describe_op(name)
    if d is None:
        near = [h["op"] for h in opassist.find(name, limit=8)]
        c = _layer_census()
        if a.json:
            _emit({"op": name, "error": "unknown op", "near": near, "searched": c})
        else:
            print("unknown op: %s —— どの層にも無い" % name)
            print(_census_line(c))
            if near:
                print("  近い: " + ", ".join(near))
        return 1
    if a.json:
        _emit(d)
        return 0
    print("%s  [tier=%s]  %s -> %s" % (d["op"], d["tier"], d["in_sort"] or "-", d["out_sort"] or "-"))
    print("  出どころ: %s" % d["source"])
    print("  呼び方  : %s" % d["call"])
    if d.get("doc"):
        print("  説明    : %s" % d["doc"])
    if d.get("halcon"):
        print("  HALCON  : %s" % d["halcon"])
    for spec in d.get("params", []):
        print("  param   : %-14s %-7s %s" % (spec.get("name"), spec.get("kind"),
                                             spec.get("sort") or spec.get("doc") or ""))
    if d.get("presets"):
        print("  presets : %s" % ", ".join(sorted(d["presets"])))
    if d.get("next"):
        print("  次に繋ぐ: %s" % ", ".join(d["next"][:12]))
    if d.get("preflight"):
        for w in d["preflight"]:
            print("  注意    : %s" % w)
    if d.get("note"):
        print("  ノート  : %s" % d["note"])
    return 0


def _cmd_ops_path(a):
    """型 A → 型 B の op 列。空なら**どの層を見たか**と近い候補を必ず出す。"""
    import difflib

    import opassist
    if len(a.args) != 2:
        _note("path は型を 2 つ: imgevolve.py ops path image region", a)
        return 2
    src, dst = a.args
    idx = _build_op_index()
    rows = {r["name"]: r for r in idx["ops"]}
    known = set(idx["sorts"])
    c = _layer_census()
    unknown = [s for s in (src, dst) if s not in known]
    if unknown:
        near = {s: difflib.get_close_matches(s, sorted(known), n=5, cutoff=0.5) for s in unknown}
        if a.json:
            _emit({"from": src, "to": dst, "chains": [], "error": "unknown sort",
                   "unknown": unknown, "near": near, "searched": c})
        else:
            print("型語彙に無い: %s" % ", ".join(unknown))
            print(_census_line(c))
            for s, n in near.items():
                print("  %s に近い型: %s" % (s, ", ".join(n) or "(無し)"))
        return 1
    chains = opassist.path(src, dst)
    lim = max(int(a.limit), 1)
    if a.json:
        _emit({"from": src, "to": dst, "n_chains": len(chains), "chains": chains[:lim],
               "steps": [[{"op": n, "tier": (rows.get(n) or {}).get("tier"),
                           "call": _call_form(rows.get(n) or {"name": n})} for n in ch]
                         for ch in chains[:lim]],
               "searched": c})
        return 0
    if not chains:
        print("%s -> %s: 4 段以内に経路なし" % (src, dst))
        print(_census_line(c))
        print("  %s を出す op: %s" % (dst, ", ".join(
            sorted(n for n, r in rows.items() if r.get("out_sort") == dst)[:10]) or "(無し)"))
        print("  %s を受ける op: %s" % (src, ", ".join(
            sorted(n for n, r in rows.items() if r.get("in_sort") == src)[:10]) or "(無し)"))
        return 0
    print("%s -> %s: %d 本(最短 %d 段)" % (src, dst, len(chains), len(chains[0])))
    for ch in chains[:lim]:
        print("  " + " → ".join(ch))
        for n in ch:
            r = rows.get(n) or {"name": n}
            print("      %-24s [%s] %s" % (n, r.get("tier") or "?", _call_form(r)))
    if len(chains) > lim:
        print("  …ほか %d 本(--limit で増やす)" % (len(chains) - lim))
    print(_census_line(c))
    return 0


def cmd_ops(a):
    """`ops` / `ops find` / `ops describe` / `ops path`。"""
    act = getattr(a, "action", None)
    if act == "find":
        return _cmd_ops_find(a)
    if act == "describe":
        return _cmd_ops_describe(a)
    if act == "path":
        return _cmd_ops_path(a)
    return _cmd_ops_list(a)


def _cmd_ops_list(a):
    """一覧 / `--search`。★`--search` は **既定で横断**(旧挙動は `--registry-only`)。

    行の書式は前と同じ(レジストリ行は 1 文字も変えていない)。変えたのは
    **見える範囲**と末尾の内訳行 —— `--search icp` が 0 件を返す入口は、
    「無い」と「見えない」を混同させるので既定にしておけない。
    """
    rows = _all_ops()
    kw = (a.search or "").lower()

    def _hit(r):
        return (not a.sort or r["in_sort"] == a.sort) and (
            not kw or kw in (r["name"] + " " + (r["halcon"] or "") + " " + r["category"]).lower())

    for r in sorted(rows, key=lambda r: (r["tier"], r["in_sort"], r["name"])):
        if not _hit(r):
            continue
        print("%-26s %-8s->%-8s  halcon=%-24s [%s/%s]"
              % (r["name"], r["in_sort"], r["out_sort"], r["halcon"] or "-", r["tier"], r["category"]))
    n_reg = sum(1 for r in rows if _hit(r))
    if not kw or getattr(a, "registry_only", False):
        print("--- %d ops match ---" % n_reg)
        return 0
    import opassist
    idx = _op_rows()
    extra = []
    for h in opassist.find(kw, limit=200):
        r = idx.get(h["op"])
        if not r or r["tier"] in ("registry", "color", "nary") or h["op"] in {x["op"] for x in extra}:
            continue
        if a.sort and r.get("in_sort") != a.sort:
            continue
        extra.append({"op": h["op"], "row": r, "doc": h["doc"]})
    for e in extra[:50]:
        r = e["row"]
        print("%-26s %-8s->%-8s  ledger=%-24s [%s/%s]"
              % (r["name"], r.get("in_sort") or "-", r.get("out_sort") or "-",
                 r.get("ledger") or "-", r["tier"], r.get("dim") or r.get("category") or "-"))
    print("--- %d ops match (registry+nary %d / 台帳 %d) ---"
          % (n_reg + len(extra), n_reg, len(extra)))
    if extra:
        print("台帳 op の詳細は `imgevolve.py ops describe <名前>`、"
              "横断検索は `imgevolve.py ops find %s`(採点つき)" % kw)
    return 0


def _disposition(op):
    p = os.path.join(HERE, "docs", "OP_DISPOSITION.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))["dispositions"].get(op)


def cmd_has(a):
    rows = _all_ops()
    q = a.op.lower()
    hits = [r for r in rows if q in (r["name"].lower(), (r["halcon"] or "").lower())]
    if not hits:
        # ★台帳(33 族 1,024 op)を見てから「無い」と言う(2026-09-15)。それまで
        #   `has frame_align` は exit 1 で「HALCON リファレンスに無い」と答えて
        #   いたが、`frame_align` は opsvideostream に**実装済み**だった。
        led = _op_rows().get(a.op)
        if led is not None and led["tier"] == "ledger":
            print("IMPLEMENTED: name=%s  %s->%s  tier=ledger (%s)"
                  % (led["name"], led.get("in_sort") or "-", led.get("out_sort") or "-",
                     led.get("ledger")))
            print("  call: %s" % _call_form(led))
            print("  detail: py -3.11 imgevolve.py ops describe %s" % led["name"])
            return 0
        # Every one of the 2313 real ops still gets a truthful response.
        d = _disposition(a.op)
        if d:
            print("NOT genuinely implemented: %s" % a.op)
            print("  disposition: %s" % d["status"])
            print("  reason: %s  [chapter=%s, arity=%d]" % (d["reason"], d["chapter"], d["arity"]))
            return 0
        near = [r for r in rows if q in r["name"].lower() or q in (r["halcon"] or "").lower()]
        print("unknown op: %s (not in the HALCON reference)" % a.op)
        if near:
            print("  near:", ", ".join(sorted({r["halcon"] or r["name"] for r in near}))[:400])
        return 1
    for r in hits:
        print("IMPLEMENTED: halcon=%s  name=%s  %s->%s  tier=%s"
              % (r["halcon"], r["name"], r["in_sort"], r["out_sort"], r["tier"]))
        if r["tier"] == "registry":
            print("  call: py -3.11 imgevolve.py apply %s <in> <out> --a A --b B" % (r["halcon"] or r["name"]))
        else:
            print("  n-ary (%d inputs) — use imgops_nary.build_nary() programmatically" % r.get("arity", 2))
    return 0


def _find_op(ops, key):
    # Exact op name wins; only then fall back to the HALCON alias. Several ops
    # share a halcon alias (e.g. remove_small carries halcon='select_shape'),
    # so first-match-wins on (name OR halcon) could bind `apply <name>` to an
    # unrelated op. Among halcon matches, prefer the canonical op (name==halcon).
    for o in ops.REGISTRY:
        if o.name == key:
            return o
    halcon_hits = [o for o in ops.REGISTRY if o.halcon == key]
    if not halcon_hits:
        return None
    for o in halcon_hits:
        if o.name == o.halcon:
            return o
    return halcon_hits[0]


def cmd_apply(a):
    ops = _load_registry()
    op = _find_op(ops, a.op)
    if op is None:
        raise SystemExit("unknown op %r (try: imgevolve.py has %s)" % (a.op, a.op))
    v = _imread(a.inp, op.in_sort)
    out = ops.RT[op.name](v, a.a, a.b)
    if op.out_sort == "feature":
        print("feature %s = %s" % (op.halcon or op.name, float(np.asarray(out).reshape(-1)[0])))
        return 0
    if op.out_sort == "contour":
        H, W = out["shape"]
        mask = np.zeros((H, W), np.float64)
        for c in out["cs"]:
            idx = np.clip(np.round(c).astype(int), [0, 0], [H - 1, W - 1])
            mask[idx[:, 0], idx[:, 1]] = 1.0
        _imwrite(a.out, mask)
        print("contour %s: %d contours -> %s (rasterised)" % (op.halcon or op.name, len(out["cs"]), a.out))
        return 0
    _imwrite(a.out, out)
    print("applied %s (%s->%s) -> %s" % (op.halcon or op.name, op.in_sort, op.out_sort, a.out))
    return 0


def cmd_pipeline(a):
    ops = _load_registry()
    names = [s.strip() for s in a.ops.split(",") if s.strip()]
    resolved = []
    for nm in names:
        op = _find_op(ops, nm)
        if op is None:
            raise SystemExit("unknown op in pipeline: %r" % nm)
        resolved.append(op)
    v = _imread(a.inp, resolved[0].in_sort)
    for op in resolved:
        v = ops.RT[op.name](v, a.a, a.b)
    if isinstance(v, np.ndarray):
        _imwrite(a.out, v)
        print("pipeline %s -> %s %s" % (" -> ".join(names), a.out, getattr(v, "shape", "")))
    else:
        print("pipeline %s -> %s" % (" -> ".join(names), type(v).__name__))
    return 0


def cmd_run(a):
    """Run a saved pipeline (Studio JSON or an ops string) via FullseyeEngine."""
    import engine
    import imgio
    if str(a.pipeline).lower().endswith(".json"):
        eng = engine.FullseyeEngine.load(a.pipeline)
    else:
        eng = engine.FullseyeEngine.from_ops(a.pipeline, a=a.a, b=a.b)

    if a.describe or a.to_python:
        if a.to_python:
            print(eng.to_python())
        else:
            print("pipeline %r: %s -> %s" % (eng.name, eng.input_sort(), eng.output_sort()))
            for d in eng.describe():
                mark = "" if d["known"] else "   [UNKNOWN OP]"
                print("  %2d. %-24s a=%.2f b=%.2f   [%s -> %s]%s"
                      % (d["index"], d["op"], d["a"], d["b"], d["in_sort"], d["out_sort"], mark))
            for p in eng.validate():
                print("  ! %-7s stage %d: %s" % (p["severity"], p["index"], p["message"]))
        if a.inp is None:
            return 0

    errors = [p for p in eng.validate() if p["severity"] == "error"]
    if errors:
        raise SystemExit("pipeline has errors: " + "; ".join(p["message"] for p in errors))
    if a.inp is None:
        raise SystemExit("need an input image (or use --describe / --to-python)")

    img = imgio.load(a.inp)
    if a.stepwise:
        for i, s in enumerate(eng.run_stepwise(img)):
            shp = getattr(s, "shape", type(s).__name__)
            if a.out and isinstance(s, np.ndarray) and s.ndim in (2, 3):
                base, ext = os.path.splitext(a.out)
                imgio.save("%s_%02d%s" % (base, i, ext or ".png"), s)
            print("  step %2d  %-24s -> %s" % (i, eng.stages[i][0], shp))
        return 0

    result = eng.run(img, upto=a.upto)
    if isinstance(result, np.ndarray) and result.ndim in (2, 3):
        if a.out:
            imgio.save(a.out, result)
            print("run %s -> %s %s" % (eng.name, a.out, result.shape))
        else:
            print("run %s -> result %s (pass --out to save)" % (eng.name, result.shape))
    else:
        print("run %s -> %s = %r" % (eng.name, type(result).__name__, result))
    return 0


def cmd_coverage(a):
    import honest_summary
    return honest_summary.main()


def cmd_parity(a):
    import parity
    return parity.main()


def cmd_accel(a):
    import sys as _s
    _s.argv = ["accel.py", "--device", a.device]
    import accel
    return accel.main()


def cmd_bench(a):
    import sys as _s
    _s.argv = ["bench.py", "--n", str(a.n), "--size", str(a.size), "--device", a.device]
    import bench
    return bench.main()


def _build_op_index():
    """`docs/OP_INDEX.json` の中身をそのまま返す(書き込みはしない)。

    ★`cmd_index` から切り出した(2026-09-06)。名前を `_` で始めるのは、これが CLI と
    検査のための内部関数で、ファサードから届く公開 API ではないから
    (`tests/test_public_reachability.py` が「見えない公開名」を数えて止める)。以前は組み立てが `cmd_index` の
    中にしか無く、鮮度を確かめる検査は `_all_ops()` を呼ぶしかなかった。すると
    **tier の再分類(color)が検査から見えない**ので、検査は「ずれている」と
    言い続けるか、tier を見ないよう緩めるかの二択になる。生成物そのものを
    返す関数を 1 つ置けば、検査は**公開されるものと同じもの**と比べられる。
    """
    rows = _all_ops()
    # 握り潰さない —— color 層が黙って空になると、tier の内訳だけが静かに縮む。
    import backends_color as CL
    col = set(CL.coverage()["halcon_names"])
    assert col, "color 層が空(backends_color.coverage が何も返さない)"
    for r in rows:
        if r["halcon"] in col:
            r["tier"] = "color"
    rows += _ledger_rows({r["name"] for r in rows})
    return {
        "n_ops": len(rows),
        "tiers": {t: sum(1 for r in rows if r["tier"] == t) for t in
                  sorted({r["tier"] for r in rows})},
        # 台帳 op には入力ゼロ(カタログを返すだけ)のものがあり in_sort が None。
        # None を sort の語彙に混ぜない(MCP が in_sort の enum に使う)。
        "sorts": sorted({r["in_sort"] for r in rows if r["in_sort"]}
                        | {r["out_sort"] for r in rows if r["out_sort"]}),
        "ops": sorted(rows, key=lambda r: (r["tier"], r["name"])),
    }


def _ledger_rows(taken):
    """型付き台帳(``opassist._LEDGERS`` の 33 族)を索引の行にする。

    ★2026-09-15 まで索引は ``ops.REGISTRY`` + n-ary の 918 op だけで、**台帳の
    1,025 op(optics 124 / 3d 357 / annotate 51 / reprconv 42 …)が 1 つも載って
    いなかった**。台帳は ``fullseye.op_find``(語幹検索)と ``fullseye.ledger``
    (属性呼び出し)から届くのに、機械可読の入口からは構造的に見えない ——
    [[feedback_registered_only_gates_miss_unregistered]] と同じ形で、索引の
    件数の門は「レジストリと一致」を見ていたので欠落に盲目だった。

    族の一覧は **``opassist._LEDGERS`` を正本にする**(``fs.op_find`` /
    ``fs.ledger`` が引く集合と同じ)。ここに別の表を持つと、族を足したときに
    片方だけ増える。

    * ``tier`` は ``"ledger"``、``ledger`` に台帳モジュール名、``dim`` に
      ノートの置き場(``docs/ops/<dim>/``)、``in_sorts`` に宣言入力の全部。
    * ``in_sort`` は宣言入力の先頭(無ければ None)。台帳の型語彙(``table`` /
      ``pairs`` / ``image2d`` …)はそのまま —— 2-D の語彙に翻訳すると
      「繋がる鎖」を偽る。
    * 同名は**先に来た族が勝つ**(``fullseye.ledger`` と同じ規則。実測の重複は
      ``gaussians_to_voxel`` の ops3d / opsreprconv だけ)。2-D レジストリと同名の
      台帳 op(``ops1d`` の 2 件、``ops3d`` の 1 件)は 2-D 側の行を残す ——
      その名前で ``fullseye.apply`` が動くのはそちらだから。
    * 族の import 失敗は**握らない**。台帳は numpy/scipy だけで組める一次モジュール
      なので、失敗は「壊れた checkout」であって「無い機能」ではない。
    """
    import importlib

    import opassist
    rows = []
    seen = set(taken)
    for mod_name, table in opassist._LEDGERS:
        mod = importlib.import_module(mod_name)
        entries = getattr(mod, table)
        assert isinstance(entries, dict) and entries, "%s.%s が空" % (mod_name, table)
        dim = "3d" if mod_name == "ops3d" else ("oned" if mod_name == "ops1d"
                                                 else mod_name[len("ops"):])
        for name, info in entries.items():
            if name in seen:
                continue
            seen.add(name)
            ins = list(info.get("in") or [])
            rows.append({"name": name, "halcon": "", "in_sort": ins[0] if ins else None,
                         "out_sort": info.get("out"), "category": info.get("category"),
                         "tier": "ledger", "ledger": mod_name, "dim": dim,
                         "in_sorts": ins})
    assert rows, "台帳層が空(opassist._LEDGERS が 1 op も返さない)"
    return rows


def cmd_index(a):
    out = _build_op_index()
    rows = out["ops"]
    p = a.out or os.path.join(HERE, "docs", "OP_INDEX.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[index] %d ops (%s) -> %s" % (len(rows), out["tiers"], p))
    return 0


def cmd_algo(a):
    """General-algorithm tier (algo-c parity): list / run / emit C or Python / difftest.

    A separate, opt-in tier from the image ops (sequences, not rasters). See
    ``algo.py`` and ``docs/GENERAL_ALGORITHMS.md``.
    """
    import algo
    if a.action == "list":
        for op in algo.ALGO_REGISTRY:
            print("%-10s %-4s->%-6s [%-6s]  %s"
                  % (op.name, op.in_sort, op.out_sort, op.category, op.provenance))
        print("--- %d general-algorithm ops (seq/scalar tier) ---" % len(algo.ALGO_REGISTRY))
        return 0
    if a.action == "run":
        if a.op is None or algo.find_algo(a.op) is None:
            raise SystemExit("run needs a known op (try: imgevolve.py algo list)")
        seq = [float(x) for x in a.seq.split(",") if x.strip()]
        print(algo.run_algo(a.op, seq))
        return 0
    if a.action in ("emit-c", "emit-py"):
        import algo_codegen
        if a.op is None or algo.find_algo(a.op) is None:
            raise SystemExit("%s needs a known op (try: imgevolve.py algo list)" % a.action)
        op = algo.ALGO_BY_NAME[a.op]
        print(algo_codegen.emit_c(op) if a.action == "emit-c" else algo_codegen.emit_python(op))
        return 0
    if a.action == "difftest":
        import algo_difftest
        cc = None if a.no_c else "auto"
        names = algo.algo_names() if a.op in (None, "all") else [a.op]
        rc = 0
        for nm in names:
            if algo.find_algo(nm) is None:
                raise SystemExit("unknown algo op: %r (try: imgevolve.py algo list)" % nm)
            r = algo_difftest.difftest(nm, a.workdir, cc=cc)
            cb = r["c_backend"]
            extra = (" bit_identical=%s" % cb.get("c_vs_python_bit_identical")) if cb.get("status") == "ran" else ""
            print("[algo:%s] python pass=%s | C %s%s | c_verified=%s -> passed=%s"
                  % (nm, r["python_pass"], cb.get("status"), extra, r["c_verified"], r["passed"]))
            if not r["passed"]:
                rc = 1
        return rc
    return 0


def cmd_synth(a):
    """Learn a texture from an image and synthesise a NEW, similar one (synth.py)."""
    import imgio
    import synth
    img = imgio.load(a.inp)
    size = None
    if a.size:
        h, w = a.size.lower().split("x")
        size = (int(h), int(w))
    out = synth.synthesize_like(img, size=size, seed=a.seed, method=a.method)
    imgio.save(a.out, out)
    d = synth.feature_distance(img, out)
    nov = synth.patch_novelty(out, img)
    pyr = synth.pyramid_stat_distance(img, out)            # per-scale marginal match
    print("synth %s -> %s  spectrum_l2=%.4f hist_chi2=%.4f pyramid=%.4f novelty=%.5f"
          % (a.method, a.out, d["spectrum_l2"], d["hist_chi2"], pyr, nov))
    return 0


def cmd_samples(a):
    """Opt-in sample datasets: list URLs / open the save folder / (optionally) fetch.

    Nothing is bundled in the wheel — you fetch each dataset from its own source,
    so fullseye never redistributes third-party data.
    """
    import sample_data as sd
    act = a.action
    if act == "where":
        print(sd.data_dir()); return 0
    if act == "open":
        print("samples folder: %s" % sd.open_dir()); return 0
    if act == "list":
        print("Sample data is NOT bundled - fetch it from the source URL below.")
        print("folder: %s   (open it with: fullseye samples open)\n" % sd.data_dir())
        for e in sd.catalog():
            if a.category and e["category"] != a.category:
                continue
            have = "[have]" if sd.verify(e["id"]) else "[    ]"
            size = ("%.0f MB" % (e["bytes"] / 1e6)) if e.get("bytes") else "?"
            print("%s %-15s %-8s %s" % (have, e["id"], e["category"], e["name"]))
            print("        %s  commercial=%s  %s" % (e["license"], e["commercial"], size))
            print("        url : %s"
                  % (e["url"] or ("(no direct URL - source page) " + e["source_page"])))
            if e.get("attribution"):
                print("        cite: %s" % e["attribution"])
        return 0
    if act == "verify":
        ids = list(sd._BY_ID) if a.all else ([a.id] if a.id else [])
        if not ids:
            print("give a sample id or --all"); return 2
        rc = 0
        for i in ids:
            ok = sd.verify(i)
            print("%-15s %s" % (i, "OK" if ok else "missing/mismatch"))
            rc = rc or (0 if ok else 1)
        return rc
    if act == "download":
        if a.all:
            ids = [e["id"] for e in sd.catalog() if e["access"] == "direct"]
        elif a.category:
            ids = [e["id"] for e in sd.catalog()
                   if e["category"] == a.category and e["access"] == "direct"]
        elif a.id:
            ids = [a.id]
        else:
            print("give a sample id, --all, or --category <cat>"); return 2
        for i in ids:
            try:
                sd.download(i, yes=a.yes)
            except Exception as ex:  # fail-closed: report and move on
                print("[%s] error: %s" % (i, ex))
        if not a.yes:
            print("\n(nothing downloaded - add --yes to opt in)")
        return 0
    print("unknown action %r" % act); return 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ops", help="list/search operators; find|describe|path で全層を横断")
    p.add_argument("action", nargs="?", default=None, choices=["find", "describe", "path"],
                   help="find <語> / describe <op> / path <in_sort> <out_sort>(省略で一覧)")
    p.add_argument("args", nargs="*", help="action の引数")
    p.add_argument("--search", default="", help="一覧を語で絞る(既定で台帳も横断)")
    p.add_argument("--registry-only", action="store_true", dest="registry_only",
                   help="--search を旧挙動(レジストリ + HALCON 名だけ)に戻す")
    p.add_argument("--sort", default="", help="in_sort で絞る")
    p.add_argument("--limit", type=int, default=20, help="find / path の表示件数")
    p.add_argument("--dim", default="", help="find: 族で絞る(2d / 3d / optics …)")
    p.add_argument("--in", dest="in_sort", default="", help="find: in_sort で絞る")
    p.add_argument("--out", dest="out_sort", default="", help="find: out_sort で絞る")
    p.add_argument("--json", action="store_true", help="stdout を JSON だけにする(注記は stderr)")
    p.set_defaults(fn=cmd_ops)

    p = sub.add_parser("has", help="is a HALCON op implemented + how to call it")
    p.add_argument("op")
    p.set_defaults(fn=cmd_has)

    p = sub.add_parser("apply", help="apply one operator to an image")
    p.add_argument("op"); p.add_argument("inp"); p.add_argument("out")
    p.add_argument("--a", type=float, default=0.5); p.add_argument("--b", type=float, default=0.5)
    p.set_defaults(fn=cmd_apply)

    p = sub.add_parser("pipeline", help="apply a comma-separated op sequence")
    p.add_argument("inp"); p.add_argument("out"); p.add_argument("--ops", required=True)
    p.add_argument("--a", type=float, default=0.5); p.add_argument("--b", type=float, default=0.5)
    p.set_defaults(fn=cmd_pipeline)

    p = sub.add_parser("run", help="run a saved pipeline (JSON or ops string) via FullseyeEngine")
    p.add_argument("pipeline", help="a pipeline .json (Studio 'Save pipeline') or a comma-separated ops string")
    p.add_argument("inp", nargs="?", default=None, help="input image (omit with --describe / --to-python)")
    p.add_argument("--out", default="", help="save the result here")
    p.add_argument("--upto", type=int, default=None, help="run only stages 0..N")
    p.add_argument("--stepwise", action="store_true", help="report/save each stage's result")
    p.add_argument("--describe", action="store_true", help="print pipeline I/O + validation, then exit if no input")
    p.add_argument("--to-python", action="store_true", dest="to_python", help="print the pipeline as a Python function")
    p.add_argument("--a", type=float, default=0.5); p.add_argument("--b", type=float, default=0.5)
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("coverage", help="print honest coverage numbers")
    p.set_defaults(fn=cmd_coverage)

    p = sub.add_parser("index", help="(re)write machine-readable docs/OP_INDEX.json")
    p.add_argument("--out", default="")
    p.set_defaults(fn=cmd_index)

    p = sub.add_parser("parity", help="cross-backend parity evidence (independent impls agree)")
    p.set_defaults(fn=cmd_parity)

    p = sub.add_parser("accel", help="GPU-ready batch backend: parity vs CPU registry ops")
    p.add_argument("--device", default="cpu")
    p.set_defaults(fn=cmd_accel)

    p = sub.add_parser("bench", help="throughput: CPU baseline vs batch (add --device cuda on a GPU)")
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--size", type=int, default=256)
    p.add_argument("--device", default="cpu")
    p.set_defaults(fn=cmd_bench)

    p = sub.add_parser("algo", help="general-algorithm tier (algo-c): list/run/emit-c/emit-py/difftest")
    p.add_argument("action", choices=["list", "run", "emit-c", "emit-py", "difftest"])
    p.add_argument("op", nargs="?", default=None, help="op name (or 'all' for difftest)")
    p.add_argument("--seq", default="", help="run: comma-separated numbers, e.g. --seq 3,1,2")
    p.add_argument("--workdir", default="out/algo", help="difftest: where to emit/compile")
    p.add_argument("--no-c", action="store_true", help="difftest: force the honest C skip")
    p.set_defaults(fn=cmd_algo)

    p = sub.add_parser("synth", help="learn a texture from an image and synthesise a similar one")
    p.add_argument("inp"); p.add_argument("out")
    p.add_argument("--method", default="spectral", choices=["spectral", "pyramid", "patch"])
    p.add_argument("--size", default="", help="output HxW, e.g. 256x256 (default: source size)")
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_synth)

    p = sub.add_parser("samples",
                       help="opt-in sample datasets (not bundled): list URLs / open folder / fetch")
    p.add_argument("action", choices=["list", "open", "where", "download", "verify"],
                   help="list: show datasets+URLs; open: open the save folder; "
                        "download/verify: optional convenience")
    p.add_argument("id", nargs="?", default=None, help="a sample id (see `samples list`)")
    p.add_argument("--all", action="store_true", help="apply to all direct-download entries")
    p.add_argument("--category", default="", help="filter by category (mesh/volume/image/...)")
    p.add_argument("--yes", action="store_true",
                   help="opt in to actually download (otherwise only prints what would be fetched)")
    p.set_defaults(fn=cmd_samples)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
