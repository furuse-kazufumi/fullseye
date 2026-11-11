# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""MCP で実行できる op のうち、**出力が入力の中身に依存しない** op を機械的に洗い出す。

    py -3.11 tools/gen_mcp_input_independent.py           # fullseye/data/MCP_INPUT_INDEPENDENT.json を書く
    py -3.11 tools/gen_mcp_input_independent.py --check   # 書かずに、commit 済みと一致するか(不一致で exit 1)

★2026-11-10(独立レビュー第 2 巡 N1): ``fullseye_score_pipeline`` の依存の門は参照を辿るだけだった。
``hx_gen_checker_region`` / ``hx_gen_ellipse`` のような生成の op は ``have:<入力>`` を形のためだけに読むので
門を通り、画像を見ない処理で blob の 50 課題中 9 課題が 3 回以内に合格した。採点はこの一覧の op を断る。

方法: MCP で実行できる 1 入力の op ごとに、中身の違う 7 つの入力(雑音・円のある勾配・縞と暗い四角・大きな円・粗い市松と、
計数・キズの課題の画像。同じ形 128x128)を ``fullseye_pipeline`` と同じ実行器に通し、7 つとも走って出力がバイト単位で同じなら載せる。
入力の型が画像以外の op には、同じ 3 枚を変換の op(``otsu`` → region など)に通した物を渡す。

この環境で走らなかった op(任意の依存が無い、形が合わない)は判定できない。その op について commit 済みの
一覧に載っていればそのまま残す(依存の揃った環境で作った判定を、揃っていない環境で消さない)。
一覧は拒否の側にだけ使う(ここに無い op が入力に依存する保証はしない —— 採点は実行時の検査も別に行う)。

TODO(2026-11-10、独立レビュー第 3 巡 R1): いまは**既定のつまみ(a = b = 0.5)だけ**で判定している。つまみの端
(しきい値の a = 0 / 1 など)で出力が定数になる (op, つまみ) の組は一覧に載らない。つまみの端と中央
(a, b ∈ {0, 0.5, 1} の 9 通り)を調べて組で断る形にすると、走らせる回数が 9 倍(この機械で約 2 分 → 約 17 分)
になり、regen_all の鎖に入れるには重い。実害は採点の隠れた双子の検査(双子の真値にも合格を求める)で
塞いでいるので、今回は既定のつまみのままにした。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "fullseye", "data", "MCP_INPUT_INDEPENDENT.json")
#: 画像から各入力の型を作る変換の op(中身の違いが残るもの)。
CONVERTERS = {
    "region": "otsu", "contour": "threshold_sub_pix", "points": "img_to_points", "signal": "img_to_signal",
    "matrix": "img_to_matrix", "volume": "img_to_volume", "seq<image>": "img_to_video",
    "cimage": "img_to_cimage", "qimage": "img_to_monogenic", "lightfield": "img_to_lightfield",
    "keypoints": "img_to_keypoints", "rgbimage": "img_to_rgb", "beatcube": "img_to_beatcube",
}


def _bases():
    import numpy as np
    h = w = 128                                         # 課題の画像と同じ大きさ
    yy, xx = np.mgrid[:h, :w].astype(np.float64)
    a = np.random.default_rng(1).random((h, w))
    b = 0.2 + 0.4 * xx / (w - 1)
    for cy, cx, r in ((32, 40, 12), (80, 88, 16), (100, 28, 10)):
        b[(yy - cy) ** 2 + (xx - cx) ** 2 <= r * r] = 0.9
    c = 0.5 + 0.3 * np.sin(2 * np.pi * xx / 9.0)
    c[40:72, 52:84] = 0.05
    # 大きな明るい円(ハフ・特徴点・領域の op が何かを返す大きさ)と、粗い市松(強い角と端)
    d = np.full((h, w), 0.1) + 0.05 * np.random.default_rng(2).random((h, w))
    d[(yy - 60) ** 2 + (xx - 68) ** 2 <= 36 ** 2] = 0.95
    e = (((yy // 16) + (xx // 16)) % 2).astype(np.float64) * 0.8 + 0.1
    # 採点の課題の画像そのもの(公開モード、seed 0)。合成の 5 枚だけでは、しきい値・ハフ・コントラスト判定の
    # op が 5 枚とも同じ(空・0)を返して誤って載った(2026-11-10 の初版で 3 件)。
    from fullseye.mcp.tasks import generate
    f = generate("blob_count", 0)[0]
    g = generate("defect_inspect", 0)[0]
    return [a, b, c, d, e, f, g]


def _canon(value) -> str:
    import numpy as np
    h = hashlib.sha256()

    def walk(v):
        if isinstance(v, np.ndarray):
            h.update(b"A%s|%s|" % (str(v.dtype).encode(), str(v.shape).encode()))
            h.update(np.ascontiguousarray(v).tobytes())
        elif isinstance(v, dict):
            h.update(b"D")
            for k in sorted(v, key=str):
                h.update(str(k).encode() + b"=")
                walk(v[k])
        elif isinstance(v, (list, tuple)):
            h.update(b"L%d|" % len(v))
            for x in v:
                walk(x)
        elif isinstance(v, (np.generic,)):
            walk(np.asarray(v))
        else:
            h.update(("S" + type(v).__name__ + repr(v)).encode())
    walk(value)
    return h.hexdigest()


def _run(cat, store, value, sort, op):
    """``fullseye_pipeline`` と同じ実行器で 1 段だけ走らせ、出力の値を返す(失敗は None)。"""
    from fullseye.mcp.server import _pipeline_dag
    handle = store.put(value, sort=sort, provenance=[{"scan": op}])["handle"]
    res = _pipeline_dag({"handle": handle, "stages": [{"op": op}], "vision": "none"}, cat, store,
                        max_structured_bytes=1 << 30)
    if res.get("isError"):
        return None
    rows = (res.get("structuredContent") or {}).get("outputs") or []
    if not rows:
        return None
    return store.get(rows[-1]["handle"])[1]


def build(previous: dict | None) -> dict:
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import numpy as np
    from types import SimpleNamespace
    from fullseye.mcp.handles import HandleStore
    from fullseye.opsearch import _graph, known_sorts
    warnings.simplefilter("ignore")
    np.seterr(all="ignore")
    # 実行器が catalog から使うのは知らない op 名の近い候補だけ。op ノート(docs/ops)を読まない軽い代役にする
    cat = SimpleNamespace(sorts=known_sorts(), nearest=lambda name: [])
    store = HandleStore(roots=[], max_items=64)
    bases = _bases()
    n = len(bases)
    inputs = {"image": bases, "color": [np.stack([b, np.roll(b, 7, 1), 1 - b], -1) for b in bases],
              "images": [np.stack([b, np.roll(b, 5, 0), 1 - b, b.T]) for b in bases]}
    for sort, conv in CONVERTERS.items():
        try:
            derived = [_run(cat, store, b, "image", conv) for b in bases]
        except Exception:                                   # noqa: BLE001 - 変換が無い環境では判定しない
            continue
        if all(d is not None for d in derived) and len({_canon(d) for d in derived}) == n:
            inputs[sort] = derived
    edges = [e for e in _graph()["edges"] if e.get("verified_executable") and len(e.get("inputs") or []) == 1]
    flagged, tested = {}, set()
    for e in sorted(edges, key=lambda e: e["op"]):
        sort = e["inputs"][0]
        if sort not in inputs:
            continue
        outs = []
        for value in inputs[sort]:
            try:
                out = _run(cat, store, value, sort, e["op"])
            except Exception:                               # noqa: BLE001 - 走らない op は判定しない
                out = None
            if out is None:
                break
            outs.append(_canon(out))
        if len(outs) != len(inputs[sort]):
            continue
        tested.add(e["op"])
        if len(set(outs)) == 1:
            flagged[e["op"]] = {"in_sort": sort, "out_sort": e.get("output")}
    # 判定できなかった op は commit 済みの判定を残す
    for op, row in ((previous or {}).get("ops") or {}).items():
        if op not in tested and op not in flagged:
            flagged[op] = row
    return {"method": ("1-input MCP-executable ops (default knobs) run on 7 inputs with different content and the same "
                       "128x128 shape (noise / gradient with discs / stripes with a dark square / a large disc / a coarse "
                       "checkerboard / the blob_count and defect_inspect task images; other sorts via a converter op); "
                       "listed when all 7 outputs are byte-identical. Ops that could not run here keep their "
                       "committed entry. Used by fullseye_score_pipeline as a deny list."),
            "ops": {k: flagged[k] for k in sorted(flagged)}}


def render(previous: dict | None) -> str:
    return json.dumps(build(previous), ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="書かずに commit 済みと比べる(不一致で exit 1)")
    args = ap.parse_args(argv)
    previous = None
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as fh:
            previous = json.load(fh)
    text = render(previous)
    if args.check:
        with open(OUT, encoding="utf-8") as fh:
            same = fh.read() == text
        print("up to date" if same else "MCP_INPUT_INDEPENDENT.json is stale: run tools/gen_mcp_input_independent.py")
        return 0 if same else 1
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s (%d ops)" % (os.path.relpath(OUT, ROOT), len(json.loads(text)["ops"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
