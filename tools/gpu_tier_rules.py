#!/usr/bin/env python3
"""GPU tier classification for every operator (4-way), by type and family.

Each operator gets a ``gpu_tier`` in exactly four values:

* ``required`` — GPU is practically mandatory: on CPU the realistic problem size
  is infeasible (minutes-to-hours or OOM). Assigned **by name** from the
  hand-maintained roster ``fullseye/data/gpu_required.json`` (every name there
  must be a real operator; :func:`check_roster` is the gate).
* ``suitable`` — GPU-friendly: dense images / volumes / signals / matrices /
  video, where per-element parallelism and fused kernels help.
* ``partial`` — only batch-over-frames helps: region / contour / label /
  geometry-collection / feature / measurement operators.
* ``none`` — no benefit: scalar / table / I-O / string / handle / metadata.

Rule: ``gpu_tier = required`` if the op name is in the roster, else the stronger
(by :data:`TIER_RANK`) of ``SORT_TIER[in_sort]`` and ``SORT_TIER[out_sort]``.
The classification is derived from the machine-readable index, never hand-set per
op (手で付けるのは required の名簿だけ) — so it cannot drift from the registry.

    py -3.11 tools/gpu_tier_rules.py            # (re)write docs/perf/GPU_TIERS.md
    py -3.11 tools/gpu_tier_rules.py --check    # rebuild and fail (exit 1) on drift
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TIER_RANK = {"none": 0, "partial": 1, "suitable": 2, "required": 3}
TIERS = ("required", "suitable", "partial", "none")

#: sort(型) -> 既定 tier。in_sort / out_sort の両方をこの表で引き、強い方を採る。
#: 密な数値配列(画像/体積/信号/行列/動画)は suitable、領域・輪郭・ラベル・幾何の
#: 集まり・特徴・計測は partial、スカラー/表/I-O/文字列/ハンドルは none。
SORT_TIER = {
    # --- suitable: dense numeric arrays (per-element / per-voxel GPU parallelism) ---
    "image": "suitable", "image2d": "suitable", "cimage": "suitable", "qimage": "suitable",
    "images": "suitable", "rgb": "suitable", "rgba": "suitable", "rgba_premul": "suitable",
    "rgbimage": "suitable", "rgbvideo": "suitable", "rgbvolume": "suitable", "video": "suitable",
    "volseq": "suitable", "volume": "suitable", "voxel": "suitable", "depth": "suitable",
    "sdf": "suitable", "zscan": "suitable", "sinogram": "suitable", "sinostack": "suitable",
    "lightfield": "suitable", "pointmap": "suitable", "normalmap": "suitable", "histcube": "suitable",
    "mask": "suitable", "signal": "suitable", "matrix": "suitable", "coordgrid": "suitable",
    "flow2d": "suitable", "flow_dense": "suitable", "gradient": "suitable", "hessian": "suitable",
    "curvature": "suitable", "lab": "suitable", "stokes": "suitable", "jones": "suitable",
    "polsweep": "suitable", "deformation": "suitable", "beatcube": "suitable", "attnmap": "suitable",
    "transport_plan": "suitable", "sprites": "suitable", "frame": "suitable", "color": "suitable",
    "gaussians": "suitable", "sweep": "suitable",
    # --- partial: region / contour / label / geometry collections / feature / measurement ---
    "region": "partial", "rle_region": "partial", "labels": "partial", "labels2d": "partial",
    "contour": "partial", "keypoints": "partial", "points": "partial", "positions": "partial",
    "position": "partial", "pairs": "partial", "cpoints": "partial", "descriptor": "partial",
    "normals": "partial", "mesh": "partial", "poly_surface": "partial", "bspline_curve": "partial",
    "bspline_surface": "partial", "primitive": "partial", "pose": "partial", "flow_scattered": "partial",
    "graph": "partial", "conn_graph": "partial", "shapeset": "partial", "shapemodel": "partial",
    "feature": "partial", "measurement": "partial", "rot_scale": "partial", "shift": "partial",
    "vector": "partial", "indices": "partial", "roots": "partial", "axes": "partial",
    "match": "partial", "synapse_table": "partial",
    # --- none: scalar / table / I-O / string / handle / metadata ---
    "table": "none", "any": "none", "scalar": "none", "cscalar": "none", "counts": "none",
    "countrate": "none", "score": "none", "metrics": "none", "text": "none", "tokens": "none",
    "angle": "none", "design": "none", "file": "none", "lut": "none", "calresult": "none",
    "measurehandle": "none", "metrologymodel": "none", "simmodel": "none", "efdmodel": "none",
    "enum": "none", "phash": "none", "fingerprint": "none",
}


def load_required() -> set:
    """``fullseye/data/gpu_required.json`` の正本名簿(全 required op 名)を集合で返す。"""
    data = json.loads((ROOT / "fullseye" / "data" / "gpu_required.json").read_text(encoding="utf-8"))
    names: set = set()
    for group in data["required"].values():
        names.update(group)
    return names


def _sort_tier(sort) -> str:
    return SORT_TIER.get(sort, "none") if sort else "none"


def tier_for(op: dict, required: set) -> str:
    """1 op の gpu_tier。required 名簿にあれば required、無ければ in/out 型の強い方。"""
    if op.get("name") in required:
        return "required"
    cand = (_sort_tier(op.get("in_sort")), _sort_tier(op.get("out_sort")))
    return max(cand, key=lambda t: TIER_RANK[t])


def assign(rows, required=None) -> None:
    """各 op 行に ``gpu_tier`` を in-place で付ける(imgevolve.py index から呼ぶ)。"""
    if required is None:
        required = load_required()
    for op in rows:
        op["gpu_tier"] = tier_for(op, required)


def check_roster(op_names: set) -> list:
    """required 名簿のうち実在しない op 名を返す(空なら全実在)。"""
    return sorted(load_required() - set(op_names))


def unknown_sorts(ops) -> list:
    """SORT_TIER に無い型(新設 sort が黙って none に落ちるのを拒む)。"""
    seen: set = set()
    for o in ops:
        for key in ("in_sort", "out_sort"):
            s = o.get(key)
            if s and s not in SORT_TIER:
                seen.add(s)
    return sorted(seen)


def family_table(ops) -> list:
    """族(category)ごとの (family, required, suitable, partial, none, total)。合計降順。"""
    fam: dict = {}
    for o in ops:
        f = o.get("category") or "unknown"
        row = fam.setdefault(f, {t: 0 for t in TIERS})
        row[o["gpu_tier"]] += 1
    out = []
    for f, row in fam.items():
        total = sum(row.values())
        out.append((f, row["required"], row["suitable"], row["partial"], row["none"], total))
    out.sort(key=lambda r: (-r[5], r[0]))
    return out


def gpu_coverage(ops) -> dict:
    """GPU 対応率 = gpu_status あり ÷ (required + suitable)。現状値をそのまま出す。"""
    have_gpu = sum(1 for o in ops if o.get("gpu_tier") and o.get("gpu_accel"))
    denom = sum(1 for o in ops if o["gpu_tier"] in ("required", "suitable"))
    # honest disclosure: gpu 経路を持つが required/suitable 外(partial)の op 数
    gpu_in_partial = sum(1 for o in ops if o.get("gpu_accel") and o["gpu_tier"] == "partial")
    gpu_in_none = sum(1 for o in ops if o.get("gpu_accel") and o["gpu_tier"] == "none")
    return {"have_gpu": have_gpu, "denom": denom,
            "rate": (have_gpu / denom) if denom else 0.0,
            "gpu_in_partial": gpu_in_partial, "gpu_in_none": gpu_in_none}


def _load_index() -> dict:
    return json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))


def render_md(idx: dict) -> str:
    ops = idx["ops"]
    # gpu_accel を opdocs と同じ経路で足す(索引には gpu_accel が無いので実装台帳から導く)
    _attach_gpu_accel(ops)
    required = load_required()
    for o in ops:
        if "gpu_tier" not in o:
            o["gpu_tier"] = tier_for(o, required)
    counts = {t: sum(1 for o in ops if o["gpu_tier"] == t) for t in TIERS}
    cov = gpu_coverage(ops)
    missing = check_roster({o["name"] for o in ops})
    unk = unknown_sorts(ops)
    L = ["# GPU tier 分類 — 全 op の 4 段台帳", "",
         "`tools/gpu_tier_rules.py` が機械可読索引 (`docs/OP_INDEX.json`) と正本名簿 "
         "(`fullseye/data/gpu_required.json`) から生成する。手書きしない。", "",
         "## 4 段の定義", "",
         "| tier | 意味 | 判定 |", "|---|---|---|",
         "| `required` | GPU 必須(CPU では実寸が非現実的) | 名簿 `gpu_required.json` に名指し |",
         "| `suitable` | GPU 向き(密な画像・体積・信号・行列・動画) | in/out 型が密配列 |",
         "| `partial` | 部分的(枚数方向のバッチだけ効く) | 領域・輪郭・ラベル・幾何・特徴・計測 |",
         "| `none` | 恩恵なし | スカラー・表・I/O・文字列・ハンドル |", "",
         "判定規則: 名簿にあれば `required`、無ければ `in_sort`/`out_sort` を型表で引き強い方 "
         "(`required` > `suitable` > `partial` > `none`)。", "",
         "## 全体の内訳", "",
         "| tier | 件数 |", "|---|---:|"]
    for t in TIERS:
        L.append("| `%s` | %d |" % (t, counts[t]))
    L.append("| **合計** | **%d** |" % len(ops))
    L += ["", "## GPU 対応率", "",
          "指標 = `gpu_status=あり` の件数 ÷ (`required` + `suitable`) の件数"
          "(件数÷全体ではない)。現状値をそのまま書く(低くてよい)。", "",
          "- gpu 経路あり: **%d**" % cov["have_gpu"],
          "- `required` + `suitable`: **%d**" % cov["denom"],
          "- **GPU 対応率 = %.1f%%** (%d / %d)" % (100 * cov["rate"], cov["have_gpu"], cov["denom"]),
          ""]
    if cov["gpu_in_partial"] or cov["gpu_in_none"]:
        L.append("正直な内訳: gpu 経路を持つ op のうち %d 件は `partial`(領域モルフォロジ等)、"
                 "%d 件は `none` で、分母には入らない(分子にのみ計上)。"
                 % (cov["gpu_in_partial"], cov["gpu_in_none"]))
        L.append("")
    L += ["## 族別の内訳", "",
          "| 族 | required | suitable | partial | none | 合計 |",
          "|---|---:|---:|---:|---:|---:|"]
    for f, req, su, pa, no, tot in family_table(ops):
        L.append("| %s | %d | %d | %d | %d | %d |" % (f, req, su, pa, no, tot))
    L += ["", "## required 名簿の実在検査", ""]
    L.append("名簿の op が全部実在: **%s**%s" %
             ("はい" if not missing else "いいえ",
              "" if not missing else "(不在: %s)" % ", ".join(missing)))
    if unk:
        L.append("")
        L.append("⚠ 型表 `SORT_TIER` に無い型(none に落ちている): %s" % ", ".join(unk))
    L.append("")
    return "\n".join(L)


def _attach_gpu_accel(ops) -> None:
    """索引の各 op に gpu_accel(実装台帳由来)を足す。opdocs._records と同じ導出。"""
    sys.path.insert(0, str(ROOT))
    import accel
    import accel_match
    import accel_vol
    gpu_names = {core: name for name, (_fn, core, _hal) in accel.ACCEL.items()}
    gpu_names.update({core: name for name, (_fn, core) in accel_vol.VOL_ACCEL.items()})
    gpu_names.update({core: name for core, name in accel_match.MATCH_ACCEL.items()})
    seen: set = set()
    for o in ops:
        nm = gpu_names.get(o["name"])
        o["gpu_accel"] = nm if nm and o["name"] not in seen else None
        if o["gpu_accel"]:
            seen.add(o["name"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="rebuild and fail on drift")
    a = ap.parse_args(argv)
    out = ROOT / "docs" / "perf" / "GPU_TIERS.md"
    text = render_md(_load_index())
    if a.check:
        old = out.read_text(encoding="utf-8") if out.exists() else ""
        if old != text:
            print("[gpu_tier_rules] DRIFT: %s is stale (run without --check)" % out)
            return 1
        print("[gpu_tier_rules] %s up to date" % out)
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print("[gpu_tier_rules] wrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
