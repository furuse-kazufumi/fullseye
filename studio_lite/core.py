# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_lite/core.py — ブラウザ版 Studio-lite(v0)の Python 側。**Pyodide の中で**読まれる(CPython でも同じに動く)。

ページ(``index.html``)は numpy 配列と JSON だけをこのモジュールとやり取りする。ここにあるのは Studio の
部品の**呼び出し**だけで、仕様の複製は持たない:

* ノブの見せ方 …… ``param_specs.spec_for`` / ``param_specs.format_display``(Studio と同じ表)
* 描画 …… ``studio.apply_display``(Studio の描画入口。gray / region overlay / shaded relief / height / 疑似カラー)
* レシピ …… ``engine.FullseyeEngine.to_dict``(``{"fullseye_pipeline": 1, "name", "stages": [[op, a, b], …]}``)で書き、
  ``studio.validate_pipeline_dict`` で読む(Studio の「Open pipeline」と同じ検査。4 要素の bypass つき段も受ける)
* 段の整合 …… ``engine.diagnose_stages``(Studio の Problems パネルと同じ)
* 走らせる …… ``api.apply`` を段ごとに(``engine.run_stepwise`` と同じ順序・同じノブの意味)

ブラウザで使える op の一覧は ``ops_subset.json``(実測の台帳: Pyodide で走って CPython と 1 ULP 以内で一致した op)を
ページが渡す。ここで op を推測して足すことはしない。
"""
from __future__ import annotations

import json
import time

import numpy as np

import api
import engine
import param_specs
import recipes
import studio                    # Qt は遅延 import なので、PySide6 の無い環境でも読める

_SUBSET: set = set()
_SUBSET_ROWS: dict = {}

DISPLAY_MODES = ["gray", "region overlay", "shaded relief", "height (color)"]


def set_subset(text: str) -> int:
    """``ops_subset.json`` の中身(文字列)を受け取り、使える op の集合にする。戻り値は op 数。"""
    d = json.loads(text)
    _SUBSET.clear()
    _SUBSET_ROWS.clear()
    for r in d["ops"]:
        _SUBSET.add(r["name"])
        _SUBSET_ROWS[r["name"]] = r
    return len(_SUBSET)


def display_modes() -> list:
    import imgio
    return DISPLAY_MODES + [c for c in imgio.COLORMAPS if c != "gray"]


def op_list() -> str:
    """ブラウザで使える op の表(JSON 文字列)。registry の順で、分類と sort を付ける。"""
    rows = []
    for o in api.REGISTRY:
        if o.name not in _SUBSET:
            continue
        doc = (o.fn.__doc__ or o.doc or "").strip().splitlines()
        rows.append({"name": o.name, "category": o.category, "in": o.in_sort, "out": o.out_sort,
                     "halcon": o.halcon, "doc": doc[0][:160] if doc else "",
                     "ms_browser": _SUBSET_ROWS[o.name].get("ms_browser"),
                     "ms_native": _SUBSET_ROWS[o.name].get("ms_native")})
    return json.dumps(rows, ensure_ascii=False)


def spec(name: str) -> str:
    """ノブ a / b の仕様(Studio と同じ ``param_specs``)。"""
    sp = param_specs.spec_for(name)
    out = {}
    for k in ("a", "b"):
        s = dict(sp[k])
        s["label_full"] = param_specs.spec_label(sp, k)
        out[k] = s
    return json.dumps(out, ensure_ascii=False)


def format_knob(name: str, letter: str, value: float) -> str:
    return param_specs.format_display(param_specs.spec_for(name)[letter], float(value))


def diagnose(stages_json: str) -> str:
    """段の整合(unknown op / sort 不一致)。Studio の Problems パネルと同じ関数。"""
    stages = [tuple(s) for s in json.loads(stages_json)]
    try:
        probs = engine.diagnose_stages(stages)
    except Exception as e:  # noqa: BLE001
        probs = ["%s: %s" % (type(e).__name__, e)]
    return json.dumps([str(p) for p in probs], ensure_ascii=False)


def _to_rgba(shown) -> bytes:
    x = np.asarray(shown)
    if x.ndim == 2:
        if x.dtype == bool:
            g = (x * 255).astype(np.uint8)
        elif x.dtype == np.uint8:
            g = x
        else:
            xf = x.astype(np.float64)
            fin = np.isfinite(xf)
            lo, hi = (float(xf[fin].min()), float(xf[fin].max())) if fin.any() else (0.0, 0.0)
            g = np.zeros(x.shape, np.uint8) if hi <= lo else np.clip((xf - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
            g[~fin] = 0
        rgb = np.stack([g, g, g], axis=-1)
    elif x.ndim == 3 and x.shape[-1] in (3, 4):
        rgb = x[..., :3]
        if rgb.dtype != np.uint8:
            rgb = np.clip(np.nan_to_num(rgb.astype(np.float64)) * (255.0 if rgb.max() <= 1.0 else 1.0), 0, 255).astype(np.uint8)
    else:
        raise ValueError("描画できない形 %s" % (x.shape,))
    out = np.empty(rgb.shape[:2] + (4,), np.uint8)
    out[..., :3] = rgb
    out[..., 3] = 255
    return out.tobytes()


def render(val, mode: str, base=None) -> dict:
    """Studio の描画入口 ``studio.apply_display`` を通して RGBA(bytes)にする。2-D でない結果は文字にする。"""
    if isinstance(val, np.ndarray) and val.ndim in (2, 3):
        shown = studio.apply_display(val, mode, base=base)
        rgba = _to_rgba(shown)
        h, w = np.asarray(shown).shape[:2]
        return {"kind": "image", "h": int(h), "w": int(w), "rgba": rgba, "dtype": str(val.dtype),
                "shape": list(val.shape)}
    if isinstance(val, np.ndarray):
        return {"kind": "text", "text": "%s %s" % (val.dtype, val.shape), "dtype": str(val.dtype), "shape": list(val.shape)}
    return {"kind": "text", "text": repr(val)[:400], "dtype": type(val).__name__, "shape": []}


def image_from_flat(flat, h: int, w: int):
    """JS の Float32Array(0..1 のグレー)を float32 画像にする。"""
    return np.frombuffer(flat.to_py() if hasattr(flat, "to_py") else flat, dtype=np.float32).reshape(int(h), int(w)).copy()


def run_chain(img, stages_json: str, mode: str = "gray") -> dict:
    """段ごとに ``api.apply`` を当て、各段の結果の描画(RGBA)と所要 ms を返す。失敗した段で止め、理由を返す。"""
    stages = [tuple(s[:3]) for s in json.loads(stages_json)]
    cur = img
    cards = [dict(render(img, "gray"), ms=None, op=None)]
    error = None
    for op, a, b in stages:
        t = time.perf_counter()
        try:
            cur = api.apply(cur, op, float(a), float(b))
        except Exception as e:  # noqa: BLE001
            error = {"op": op, "error": "%s: %s" % (type(e).__name__, str(e)[:300])}
            break
        ms = round((time.perf_counter() - t) * 1e3, 2)
        c = render(cur, mode, base=img)
        c["ms"] = ms
        c["op"] = op
        cards.append(c)
    return {"cards": cards, "error": error, "final": cards[-1]}


def run_chain_raw(img, stages_json: str):
    """描画なし —— 最終結果の配列そのもの(門の照合用)。"""
    cur = img
    for op, a, b in [tuple(s[:3]) for s in json.loads(stages_json)]:
        cur = api.apply(cur, op, float(a), float(b))
    return cur


def recipe_json(name: str, stages_json: str) -> str:
    """Studio / engine が読む形で書く(``FullseyeEngine.to_dict``)。"""
    stages = [tuple(s[:3]) for s in json.loads(stages_json)]
    return json.dumps(engine.FullseyeEngine(stages, name=name or "pipeline").to_dict(), ensure_ascii=False, indent=1)


def load_recipe(text: str) -> str:
    """Studio の検査(``validate_pipeline_dict``)で読む。bypass 印(4 要素目が true)のある段は **Studio と同じく走らせない**
    (``bypassed`` に名前を並べて列から外す。engine は印を黙って落として走らせるので、ここは Studio 側に合わせる)。
    ブラウザで使えない op が混ざっていれば ``unavailable`` に名前を並べる(黙って落とさない)。"""
    d = json.loads(text)
    stages = studio.validate_pipeline_dict(d)
    bypassed = [s[0] for s in stages if len(s) == 4 and s[3] is True]
    norm = [[s[0], float(s[1]), float(s[2])] for s in stages if not (len(s) == 4 and s[3] is True)]
    unavailable = [s[0] for s in norm if s[0] not in _SUBSET]
    return json.dumps({"name": d.get("name") or "pipeline", "stages": norm, "unavailable": unavailable,
                       "bypassed": bypassed}, ensure_ascii=False)


def builtin_recipes() -> str:
    """同梱レシピのうち、全段がブラウザで使えるもの。"""
    out = []
    for r in recipes.RECIPES:
        st = [[s[0], float(s[1]), float(s[2])] for s in r["stages"]]
        if all(s[0] in _SUBSET for s in st):
            out.append({"name": r["name"], "task": r.get("task"), "note": r.get("note", ""), "stages": st})
    return json.dumps(out, ensure_ascii=False)
