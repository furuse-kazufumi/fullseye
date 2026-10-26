# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""optional 依存(cv2 / scikit-image / Pillow)が無い環境で、op が**別の答えを黙って返さない**ことを確かめる門の道具。

    py -3.11 tools/check_fallback_parity.py --ops circularity,closing_circle        # 名指し
    py -3.11 tools/check_fallback_parity.py --ops-file ops.txt --knobs "0.5,0.5;0.2,0.8"
    py -3.11 tools/check_fallback_parity.py --all                                     # image / region 入力の登録 op 全部
    py -3.11 tools/check_fallback_parity.py --ops ... --json out.json --out <dir>

**やること**: 同じ入力・同じノブで op を 2 つのサブプロセスで走らせる。片方は full(何も塞がない)、
もう片方は **min**(``sys.meta_path`` の先頭に置いた finder が ``--block`` のモジュール(既定
``cv2,skimage,PIL``)の import を ``ImportError`` にする)。出力を ULP で照合する。照合の段は
Studio-web 探針の ``compare_outputs.py`` と同じ(bit 一致 / 4 ULP かつ 1e-12 以内 / それ以上)。

**判定**(op × 入力 × ノブ ごと):

* ``bit_identical``        両方走って bit 一致(bool / 整数は完全一致、浮動小数は view を整数にして一致)
* ``within_ulp``           両方走って 4 ULP 以内かつ絶対差 1e-12 以内(wasm の sqrt / hypot の丸めと同じ許容)
* ``missing_dependency``   min 側が :class:`backend_safe.MissingDependencyError` を投げた(fail-closed。何が無くて
                           何を入れればよいかを言う例外 —— 別の答えを返していない)
* ``differs``              両方走ったが答えが違う —— **これが「fail-soft の罠」**。門はこれを赤にする
* ``shape_or_dtype_differs`` / ``min_error`` / ``full_error`` / ``nonarray_differs``  それ以外の不一致

**なぜサブプロセスか**: Pyodide は要らない。CPython で import を塞げば同じ経路に入る(``_HAS_SK`` /
``_HAS_CV`` は import の成否で決まる)。2026-10-25 の探針では、full では走る 488 op のうち 89 op が min で
**例外なく走って別の値を返した**(領域特徴 23 本が全部「面積率」など)。

**入力**: ``studio_assets/sample_images/coins.png`` を 256x256 に切った float32(0..1)と、その otsu 領域
(full 側の親プロセスで作り、両方のサブプロセスに同じ ``.npy`` を渡す)。``--synthetic`` で構造の違う
合成画像(矩形・円・細線・穴)を 2 枚目として足す(探針 1 枚は網羅ではない)。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: 照合の段(compare_outputs.py の ``--ledger-ulp`` / ``--ledger-abs`` の既定と同じ)。
LEDGER_ULP = 4
LEDGER_ABS = 1e-12
DEFAULT_BLOCK = ("cv2", "skimage", "PIL")
DEFAULT_KNOBS = ((0.5, 0.5),)
#: fail-closed と認める例外の型名(backend_safe.MissingDependencyError とその派生)。
MISSING_DEP_TYPES = ("MissingDependencyError",)


# --------------------------------------------------------------------------- #
# 子プロセス側                                                                 #
# --------------------------------------------------------------------------- #
class _ImportBlocker:
    """``sys.meta_path`` の先頭に置くと、名指しの top-level module(とそのサブモジュール)の import を拒む。"""

    def __init__(self, names):
        self.names = frozenset(names)

    def find_spec(self, fullname, path=None, target=None):  # noqa: D401 - importlib protocol
        top = fullname.split(".", 1)[0]
        if top in self.names:
            raise ImportError("import of %r is blocked by tools/check_fallback_parity.py (min 構成の再現)" % fullname)
        return None


def _child_main(args) -> int:
    """``--child``: 入力 ``.npz`` を読み、op を走らせ、出力を ``.npz`` + rows ``.json`` に書く。"""
    import numpy as np
    blocked = [b for b in args.block.split(",") if b]
    if blocked:
        sys.meta_path.insert(0, _ImportBlocker(blocked))
        for b in blocked:
            assert b not in sys.modules, "%s is already imported in the child" % b
    sys.path.insert(0, ROOT)
    import api
    import ops
    import backend_safe
    present = {b: (b in sys.modules) for b in blocked}
    inputs = np.load(args.inputs)
    names = [n for n in args.ops.split(",") if n]
    knobs = _parse_knobs(args.knobs)
    reg = {o.name: o for o in ops.REGISTRY}
    rows, arrays = {}, {}
    for name in names:
        o = reg.get(name)
        if o is None:
            rows[name] = {"ok": False, "error": "KeyError: not registered"}
            continue
        for in_name in sorted(k[4:] for k in inputs.files if k.startswith("img_")):
            x = inputs["img_" + in_name] if o.in_sort == "image" else inputs["reg_" + in_name]
            for (a, b) in knobs:
                key = "%s|%s|%g,%g" % (name, in_name, a, b)
                try:
                    backend_safe.clear_fallbacks()
                    r = api.apply(x, name, a, b)
                    fb = backend_safe.fallback_counts()
                    row = {"ok": True, "in": o.in_sort, "out": o.out_sort, "fallbacks": sum(fb.values())}
                    if isinstance(r, np.ndarray):
                        arrays[key] = r
                        row.update(kind="ndarray", dtype=str(r.dtype), shape=list(r.shape))
                    elif isinstance(r, dict) and "cs" in r:
                        cs = list(r["cs"])
                        row.update(kind="contour", n_cs=len(cs), shape=list(r.get("shape", ())))
                        for i, c in enumerate(cs):
                            arrays["%s|cs%d" % (key, i)] = np.asarray(c)
                    elif isinstance(r, (float, int, np.floating, np.integer, bool, np.bool_)):
                        arrays[key] = np.asarray(r)
                        row.update(kind="scalar", dtype=str(np.asarray(r).dtype))
                    else:
                        row.update(kind=type(r).__name__, repr=repr(r)[:400])
                    rows[key] = row
                except BaseException as e:  # noqa: BLE001 - 記録して次へ(fail-closed の例外もここで拾う)
                    rows[key] = {"ok": False, "in": o.in_sort, "out": o.out_sort,
                                 "error_type": type(e).__name__, "error": str(e)[:600]}
    np.savez_compressed(args.out_npz, **arrays)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump({"blocked": blocked, "blocked_present_after_run": present, "python": sys.version.split()[0],
                   "rows": rows}, f, ensure_ascii=False, indent=1)
    return 0


# --------------------------------------------------------------------------- #
# 親プロセス側                                                                 #
# --------------------------------------------------------------------------- #
def _parse_knobs(s):
    out = []
    for part in str(s).split(";"):
        part = part.strip()
        if not part:
            continue
        a, b = part.split(",")
        out.append((float(a), float(b)))
    return out or list(DEFAULT_KNOBS)


def make_inputs(path, synthetic=False):
    """full 側(親)で入力を作って ``.npz`` に書く。両方の子が同じ配列を読む。"""
    import numpy as np
    sys.path.insert(0, ROOT)
    import api
    png = os.path.join(ROOT, "studio_assets", "sample_images", "coins.png")
    from PIL import Image
    img = np.asarray(Image.open(png).convert("L"), dtype=np.float32) / 255.0
    img = np.ascontiguousarray(img[:256, :256], dtype=np.float32)
    reg = np.asarray(api.apply(img, "otsu", 0.5, 0.5)).astype(bool)
    arrays = {"img_coins": img, "reg_coins": reg}
    if synthetic:
        s = synthetic_image()
        arrays["img_synth"] = s
        arrays["reg_synth"] = np.asarray(api.apply(s, "otsu", 0.5, 0.5)).astype(bool)
    np.savez_compressed(path, **arrays)
    return sorted(arrays)


def synthetic_image(size=128):
    """構造の違う 2 枚目: 矩形・円・穴あき円・斜めの細線・なだらかな階調(float32、決定的)。"""
    import numpy as np
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    img = 0.15 + 0.2 * (xx / size)
    img[20:60, 15:45] = 0.9                                         # 矩形
    img[(yy - 40) ** 2 + (xx - 90) ** 2 <= 22 ** 2] = 0.85          # 円
    img[(yy - 40) ** 2 + (xx - 90) ** 2 <= 6 ** 2] = 0.1            # 穴
    img[(yy - 95) ** 2 + (xx - 35) ** 2 <= 18 ** 2] = 0.7           # 暗めの円
    for t in range(0, 70):                                          # 斜めの 2 画素線
        r, c = 70 + t // 2, 50 + t
        if r + 1 < size and c < size:
            img[r:r + 2, c] = 0.95
    rng = np.random.default_rng(7)
    img = img + rng.normal(0.0, 0.01, img.shape).astype(np.float32)
    return np.clip(img, 0, 1).astype(np.float32)


def ulp_diff(a, b):
    """(最大 ULP 差 | None, 最大絶対差)。compare_outputs.py と同じ定義。"""
    import numpy as np
    a = np.atleast_1d(np.asarray(a))        # 0 次元(スカラ結果)も同じ道で測る
    b = np.atleast_1d(np.asarray(b))
    if a.dtype.kind in "fc" and b.dtype.kind in "fc":
        dt = np.result_type(a.dtype, b.dtype)
        a = a.astype(dt)
        b = b.astype(dt)
        if dt == np.float32:
            ia, ib = a.view(np.int32).astype(np.int64), b.view(np.int32).astype(np.int64)
        elif dt == np.float64:
            ia, ib = a.view(np.int64), b.view(np.int64)
        else:
            return None, float(np.nanmax(np.abs(a - b))) if a.size else 0.0
        both_nan = np.isnan(a) & np.isnan(b)
        d = np.abs(ia - ib)
        d[both_nan] = 0
        absd = np.abs(a - b)
        absd[both_nan] = 0
        return int(d.max()) if d.size else 0, float(np.nanmax(absd)) if absd.size else 0.0
    eq = np.array_equal(a, b)
    return (0 if eq else None), (0.0 if eq else float(np.max(np.abs(a.astype(np.float64) - b.astype(np.float64)))))


def _verdict_arrays(xa, xb):
    if xa.shape != xb.shape or str(xa.dtype) != str(xb.dtype):
        return "shape_or_dtype_differs", {"a": [list(xa.shape), str(xa.dtype)], "b": [list(xb.shape), str(xb.dtype)]}
    u, d = ulp_diff(xa, xb)
    if u == 0:
        return "bit_identical", {"max_ulp": 0, "max_abs": 0.0}
    if u is not None and u <= LEDGER_ULP and d <= LEDGER_ABS:
        return "within_ulp", {"max_ulp": u, "max_abs": d}
    return "differs", {"max_ulp": u, "max_abs": d}


def compare(full_json, full_npz, min_json, min_npz):
    import numpy as np
    A = json.load(open(full_json, encoding="utf-8"))
    B = json.load(open(min_json, encoding="utf-8"))
    za = np.load(full_npz)
    zb = np.load(min_npz)
    per = {}
    for key in sorted(set(A["rows"]) | set(B["rows"])):
        ra, rb = A["rows"].get(key), B["rows"].get(key)
        if ra is None or rb is None:
            per[key] = {"verdict": "missing_row"}
            continue
        if not ra.get("ok"):
            per[key] = {"verdict": "full_error", "error": ra.get("error"), "error_type": ra.get("error_type")}
            continue
        if not rb.get("ok"):
            et = rb.get("error_type", "")
            v = "missing_dependency" if et in MISSING_DEP_TYPES else "min_error"
            per[key] = {"verdict": v, "error_type": et, "error": rb.get("error")}
            continue
        if ra.get("kind") != rb.get("kind"):
            per[key] = {"verdict": "nonarray_differs", "a": ra.get("kind"), "b": rb.get("kind")}
            continue
        kind = ra.get("kind")
        if kind in ("ndarray", "scalar"):
            v, info = _verdict_arrays(za[key], zb[key])
        elif kind == "contour":
            if ra["n_cs"] != rb["n_cs"] or ra["shape"] != rb["shape"]:
                v, info = "nonarray_differs", {"a": ra["n_cs"], "b": rb["n_cs"]}
            else:
                v, info = "bit_identical", {"max_ulp": 0, "max_abs": 0.0, "n_cs": ra["n_cs"]}
                for i in range(ra["n_cs"]):
                    vi, ii = _verdict_arrays(za["%s|cs%d" % (key, i)], zb["%s|cs%d" % (key, i)])
                    if vi != "bit_identical":
                        v, info = vi, dict(ii, n_cs=ra["n_cs"], first_bad_contour=i)
                        if vi == "differs":
                            break
        else:
            same = ra.get("repr") == rb.get("repr")
            v, info = ("bit_identical" if same else "nonarray_differs"), {"a": ra.get("repr"), "b": rb.get("repr")}
        info["verdict"] = v
        info["min_fallbacks"] = rb.get("fallbacks", 0)
        per[key] = info
    return per


def run(ops, block=DEFAULT_BLOCK, knobs=DEFAULT_KNOBS, out_dir=None, synthetic=False, python=None):
    """op 名の列を full / min の 2 サブプロセスで走らせ、照合結果 ``{key: {...}}`` を返す。

    ``key`` は ``"<op>|<input>|<a>,<b>"``。``out_dir`` を与えるとそこに入力・出力を残す(無ければ一時 dir)。
    """
    python = python or sys.executable
    tmp = out_dir or tempfile.mkdtemp(prefix="fallback_parity_")
    os.makedirs(tmp, exist_ok=True)
    inputs = os.path.join(tmp, "inputs.npz")
    make_inputs(inputs, synthetic=synthetic)
    knob_s = ";".join("%g,%g" % k for k in knobs)
    outs = {}
    for tag, blk in (("full", ""), ("min", ",".join(block))):
        npz = os.path.join(tmp, "%s_outputs.npz" % tag)
        js = os.path.join(tmp, "%s_rows.json" % tag)
        cmd = [python, os.path.abspath(__file__), "--child", "--inputs", inputs, "--ops", ",".join(ops),
               "--knobs", knob_s, "--block", blk, "--out-npz", npz, "--out-json", js]
        env = dict(os.environ)
        env.pop("FULLSEYE_ON_ERROR", None)          # 既定の policy("fallback")で測る —— 罠が出る条件そのもの
        env.pop("FULLSEYE_STRICT", None)
        env.pop("IMGEVOLVE_STRICT_BACKENDS", None)
        env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=ROOT)
        with open(os.path.join(tmp, "%s_stderr.txt" % tag), "w", encoding="utf-8") as f:
            f.write(p.stdout + "\n" + p.stderr)
        if p.returncode != 0 or not os.path.exists(js):
            raise RuntimeError("%s child failed (rc=%d):\n%s" % (tag, p.returncode, (p.stderr or p.stdout)[-3000:]))
        outs[tag] = (js, npz)
    per = compare(outs["full"][0], outs["full"][1], outs["min"][0], outs["min"][1])
    mins = json.load(open(outs["min"][0], encoding="utf-8"))
    assert not any(mins["blocked_present_after_run"].values()), \
        "blocker leaked: %r" % mins["blocked_present_after_run"]
    return per


def summarize(per):
    counts = {}
    for v in per.values():
        counts[v["verdict"]] = counts.get(v["verdict"], 0) + 1
    return counts


def _all_candidates():
    sys.path.insert(0, ROOT)
    import ops
    return [o.name for o in ops.REGISTRY if o.in_sort in ("image", "region")]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--inputs", help=argparse.SUPPRESS)
    ap.add_argument("--out-npz", help=argparse.SUPPRESS)
    ap.add_argument("--out-json", help=argparse.SUPPRESS)
    ap.add_argument("--ops", default="", help="op 名(カンマ区切り)")
    ap.add_argument("--ops-file", help="op 名を 1 行 1 つ書いたファイル(# 以降は無視)")
    ap.add_argument("--all", action="store_true", help="image / region 入力の登録 op 全部")
    ap.add_argument("--block", default=",".join(DEFAULT_BLOCK), help="min 側で塞ぐ import 名(既定 cv2,skimage,PIL)")
    ap.add_argument("--knobs", default="0.5,0.5", help='"a,b;a,b" の列(既定 0.5,0.5)')
    ap.add_argument("--synthetic", action="store_true", help="合成画像を 2 枚目の入力として足す")
    ap.add_argument("--out", help="入力・出力・stderr を残す dir(既定: 一時 dir)")
    ap.add_argument("--json", help="照合結果をこの JSON に書く")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    if args.child:
        return _child_main(args)
    names = [n for n in args.ops.split(",") if n]
    if args.ops_file:
        with open(args.ops_file, encoding="utf-8") as f:
            names += [ln.split("#", 1)[0].strip() for ln in f if ln.split("#", 1)[0].strip()]
    if args.all:
        names += _all_candidates()
    names = list(dict.fromkeys(names))
    if not names:
        ap.error("--ops / --ops-file / --all のどれかで op を指定する")
    per = run(names, block=tuple(b for b in args.block.split(",") if b), knobs=_parse_knobs(args.knobs),
              out_dir=args.out, synthetic=args.synthetic)
    counts = summarize(per)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"block": args.block, "knobs": args.knobs, "n_ops": len(names), "summary": counts, "per": per},
                      f, ensure_ascii=False, indent=1)
    if not args.quiet:
        print(json.dumps(counts, ensure_ascii=False))
        bad = {k: v for k, v in per.items() if v["verdict"] not in ("bit_identical", "within_ulp", "missing_dependency")}
        for k in sorted(bad):
            print("  %-56s %s %s" % (k, bad[k]["verdict"], {kk: vv for kk, vv in bad[k].items() if kk != "verdict"}))
    bad_n = sum(n for v, n in counts.items() if v not in ("bit_identical", "within_ulp", "missing_dependency"))
    return 1 if bad_n else 0


if __name__ == "__main__":
    raise SystemExit(main())
