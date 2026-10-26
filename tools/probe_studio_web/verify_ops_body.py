# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""探針(probe)の共通本体 2: **全 op を実際に走らせて**ブラウザで動くものを数える(名前や import で推測しない)。

    py -3.11 verify_ops_body.py <out dir> [tag]         # CPython 側(tag 既定 native)
    (Pyodide 側は verify_ops_pyodide.mjs が同じファイルを読む。tag = pyodide)

入力は studio_assets/sample_images/coins.png を 256×256 に切った float32(0..1)と、その otsu 領域。
registry の in_sort が image / region の op 全部に ``api.apply(x, name, 0.5, 0.5)`` を 1 回ずつ当て、
結果(ndarray なら中身、それ以外なら repr)と所要 ms を記録する。中身は ``<out>/<tag>_outputs.npz`` に
op 名をキーにして保存し、別の実行(CPython と Pyodide)との比較は compare_outputs.py が ULP で行う。

**時間の上限**: 1 op が 20 s を超えたら以後の op は飛ばさず、その op だけ「timeout」と記す(壁時計で測るので
止めることはできない —— 記録して次へ進む)。
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback


def load_input(root: str):
    import numpy as np
    path = os.path.join(root, "studio_assets", "sample_images", "coins.png")
    try:
        from PIL import Image
        im = np.asarray(Image.open(path).convert("L"), dtype=np.float32) / 255.0
    except Exception:  # noqa: BLE001  —— Pillow が無い環境(Pyodide の最小構成)は PNG を自前で読む
        im = _read_png_gray(path)
    im = im[:256, :256]
    return np.ascontiguousarray(im, dtype=np.float32)


def _read_png_gray(path: str):
    """8 bit グレースケール PNG(フィルタつき)だけを読む最小のデコーダ(Pillow の無い環境用)。"""
    import struct
    import zlib
    import numpy as np
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "PNG ではない"
    pos, idat, w, h, ctype = 8, b"", 0, 0, 0
    while pos < len(data):
        ln, typ = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", body[:10])
            assert depth == 8 and ctype in (0, 2, 4, 6), "8 bit 以外は読まない(depth=%d ctype=%d)" % (depth, ctype)
        elif typ == b"IDAT":
            idat += body
        pos += 12 + ln
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(idat)
    stride = w * ch
    out = np.zeros((h, stride), np.uint8)
    prev = np.zeros(stride, np.int32)
    p = 0
    for y in range(h):
        ft = raw[p]
        line = np.frombuffer(raw[p + 1:p + 1 + stride], np.uint8).astype(np.int32)
        p += 1 + stride
        cur = line.copy()
        if ft == 1:
            for i in range(ch, stride):
                cur[i] = (cur[i] + cur[i - ch]) & 255
        elif ft == 2:
            cur = (cur + prev) & 255
        elif ft == 3:
            for i in range(stride):
                left = cur[i - ch] if i >= ch else 0
                cur[i] = (cur[i] + ((left + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                a = cur[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[i] = (cur[i] + pr) & 255
        out[y] = cur
        prev = cur
    px = out.reshape(h, w, ch)
    if ch >= 3:
        g = 0.299 * px[..., 0] + 0.587 * px[..., 1] + 0.114 * px[..., 2]
    else:
        g = px[..., 0].astype(np.float32)
    return (g / 255.0).astype(np.float32)


def run_all(root: str, out_dir: str, tag: str, per_op_limit_s: float = 20.0) -> dict:
    import numpy as np
    sys.path.insert(0, root)
    t0 = time.perf_counter()
    import api
    import ops
    import_s = round(time.perf_counter() - t0, 2)
    img = load_input(root)
    reg = np.asarray(api.apply(img, "otsu", 0.5, 0.5)).astype(bool)
    cands = [o for o in ops.REGISTRY if o.in_sort in ("image", "region")]
    rows, arrays = {}, {}
    for o in cands:
        x = img if o.in_sort == "image" else reg
        t = time.perf_counter()
        try:
            r = api.apply(x, o.name, 0.5, 0.5)
            ms = (time.perf_counter() - t) * 1e3
            if isinstance(r, np.ndarray):
                arrays[o.name] = r
                rows[o.name] = {"ok": True, "ms": round(ms, 2), "kind": "ndarray", "dtype": str(r.dtype),
                                "shape": list(r.shape), "in": o.in_sort, "out": o.out_sort,
                                "finite": bool(np.all(np.isfinite(r))) if r.dtype.kind in "fc" else True}
            else:
                rows[o.name] = {"ok": True, "ms": round(ms, 2), "kind": type(r).__name__, "repr": repr(r)[:200],
                                "in": o.in_sort, "out": o.out_sort}
            if ms > per_op_limit_s * 1e3:
                rows[o.name]["timeout"] = True
        except BaseException as e:  # noqa: BLE001
            rows[o.name] = {"ok": False, "ms": round((time.perf_counter() - t) * 1e3, 2),
                            "error": "%s: %s" % (type(e).__name__, str(e)[:300]), "in": o.in_sort, "out": o.out_sort}
    os.makedirs(out_dir, exist_ok=True)
    np.savez_compressed(os.path.join(out_dir, "%s_outputs.npz" % tag), **arrays)
    summary = {"tag": tag, "python": sys.version.split()[0], "platform": sys.platform, "import_s": import_s,
               "n_candidates": len(cands), "n_ok": sum(1 for r in rows.values() if r["ok"]),
               "n_fail": sum(1 for r in rows.values() if not r["ok"]),
               "total_ms": round(sum(r["ms"] for r in rows.values()), 1), "rows": rows}
    with open(os.path.join(out_dir, "%s_verify.json" % tag), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    return summary


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    s = run_all(root, sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "native")
    print(json.dumps({k: v for k, v in s.items() if k != "rows"}, ensure_ascii=False))
