"""`fullseye_abi.h` の 2 実装を **機械が作った入力**で突き合わせる(差分ファジング)。

手書きのケースは「書いた人が思いついた場所」しか踏まない。実際
`tests/test_rust_abi_parity.py` の 14 ケースは**全部通る** —— それは正しさの証拠では
なく、**探針が尽きた**という合図([[feedback_one_probe_input_is_not_coverage]])。
2 つの実装がある状態でいちばん効くのは、**探針を人間が考えるのをやめること**。

**乱数をそのまま撒かない。** 一様乱数の画像はしきい値を通すと run が細切れになり、
「斜めに接する」「1 画素だけ」「端で切れる」といった**構造**が確率的にほぼ出ない
([[feedback_random_test_data_hides_structural_defects]])。ここでは**文法から生成**する:
矩形・市松(周期を振る)・斜め接触・枠・縞・1 画素・定数・階段を、位置と大きさと
値域としきい値を振りながら重ねる。乱数は「雑音を足す」役にしか使わない。

食い違いが出たら **縮小(shrink)** する —— 32x32 の盤面のまま報告されても読めない。

使い方:

    cd rust/fullseye_core && cargo build --release
    py -3.11 tools/fs_abi_fuzz.py --cases 20000 [--seed 0] [--ops all]

戻り値: 食い違いが 1 件でもあれば 1、無ければ 0。
"""
from __future__ import annotations

import argparse
import ctypes as C
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import fslib  # noqa: E402

LIBNAME = {"win32": "fullseye_core.dll", "darwin": "libfullseye_core.dylib"}.get(
    sys.platform, "libfullseye_core.so")
LIB = ROOT / "rust" / "fullseye_core" / "target" / "release" / LIBNAME


def load_rust():
    if not LIB.exists():
        raise SystemExit(
            "Rust 実装が建っていない(%s)。`cd rust/fullseye_core && cargo build --release` を"
            "先に走らせること —— **建たなかった**ことを「食い違いが無い」と混ぜない。" % LIB.name)
    lib = C.CDLL(str(LIB))
    p = C.POINTER
    lib.fs_image_create.argtypes = [C.c_void_p, C.c_int32, C.c_int32, C.c_int64,
                                    C.c_double, C.c_double, p(C.c_void_p)]
    lib.fs_threshold.argtypes = [C.c_void_p, C.c_double, C.c_double, p(C.c_void_p)]
    lib.fs_gauss.argtypes = [C.c_void_p, C.c_double, p(C.c_void_p)]
    lib.fs_connection.argtypes = [C.c_void_p, p(C.c_void_p)]
    lib.fs_region_area.argtypes = [C.c_void_p, p(C.c_int64)]
    lib.fs_region_run_count.argtypes = [C.c_void_p, p(C.c_int64)]
    lib.fs_objectset_count.argtypes = [C.c_void_p, p(C.c_int64)]
    lib.fs_objectset_region.argtypes = [C.c_void_p, C.c_int64, p(C.c_void_p)]
    lib.fs_measure_all.argtypes = [C.c_void_p] + [p(C.c_void_p)] * 3
    lib.fs_select_shape.argtypes = [C.c_void_p, C.c_char_p, C.c_double, C.c_double,
                                    p(C.c_void_p)]
    lib.fs_tuple_length.argtypes = [C.c_void_p, p(C.c_int64)]
    lib.fs_tuple_get_real.argtypes = [C.c_void_p, C.c_int64, p(C.c_double)]
    lib.fs_debug_copy_pixels.argtypes = [C.c_void_p, p(C.c_double), C.c_int64]
    for n in ("fs_image_release", "fs_region_release", "fs_objectset_release",
              "fs_tuple_release"):
        getattr(lib, n).argtypes = [C.c_void_p]
        getattr(lib, n).restype = None
    return lib


# --------------------------------------------------------------------------- #
# 入力の文法 —— 「乱数の画像」ではなく「構造を重ねた画像」
# --------------------------------------------------------------------------- #
SHAPES = ("rect", "checker", "diag_touch", "frame", "stripes", "dot", "const", "ramp",
          # ★2026-09-14 追加。45,000 ケースを 3 秒で「食い違いなし」と言われたとき、
          #   信じるのではなく**自分が printf で挙げた「踏んでいない座標」**を足す。
          #   一致したときこそ探針を疑う([[feedback_one_probe_input_is_not_coverage]])。
          "ring", "nested", "comb", "spiral", "hline_pair", "corner_chain")


def _paint(a: np.ndarray, kind: str, rng: np.random.Generator) -> None:
    h, w = a.shape
    if kind == "rect":
        r0, c0 = int(rng.integers(0, h)), int(rng.integers(0, w))
        r1 = min(h, r0 + int(rng.integers(1, max(2, h // 2))))
        c1 = min(w, c0 + int(rng.integers(1, max(2, w // 2))))
        a[r0:r1, c0:c1] = 1.0
    elif kind == "checker":
        # 周期を振る: 周期 1 が 4/8 連結を分ける古典的な探針、2 以上は run が伸びる
        p = int(rng.integers(1, 4))
        yy, xx = np.indices((h, w))
        a[((yy // p) + (xx // p)) % 2 == 0] = 1.0
    elif kind == "diag_touch":
        # 角だけで触れる 2 つの塊 —— 4 連結なら 2 個、8 連結なら 1 個
        s = int(rng.integers(1, max(2, min(h, w) // 3)))
        r0, c0 = int(rng.integers(0, max(1, h - 2 * s))), int(rng.integers(0, max(1, w - 2 * s)))
        a[r0:r0 + s, c0:c0 + s] = 1.0
        a[r0 + s:r0 + 2 * s, c0 + s:c0 + 2 * s] = 1.0
    elif kind == "frame":
        a[0, :] = a[-1, :] = 1.0
        a[:, 0] = a[:, -1] = 1.0
    elif kind == "stripes":
        p = int(rng.integers(1, 4))
        if rng.random() < 0.5:
            a[::p, :] = 1.0
        else:
            a[:, ::p] = 1.0
    elif kind == "dot":
        a[int(rng.integers(0, h)), int(rng.integers(0, w))] = 1.0
    elif kind == "const":
        a[:, :] = float(rng.choice([0.0, 0.5, 1.0]))
    elif kind == "ramp":
        a[:, :] = np.tile(np.linspace(0.0, 1.0, w), (h, 1))
    elif kind == "ring":
        # 穴あき。run-length と dense mask で「穴」の扱いが分かれうる唯一の形
        yy, xx = np.indices((h, w))
        cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
        d = np.hypot(yy - cy, xx - cx)
        r = max(1.5, min(h, w) / 2.0 - 0.5)
        a[(d <= r) & (d >= r * 0.55)] = 1.0
    elif kind == "nested":
        # 入れ子(枠の中に枠)。`connection` は 2 個と答えるべきで、穴の内側を
        # 外側と同じ物体にしてしまう実装ならここで割れる
        for k in range(0, min(h, w) // 2, 2):
            a[k, k:w - k] = 1.0
            a[h - 1 - k, k:w - k] = 1.0
            a[k:h - k, k] = 1.0
            a[k:h - k, w - 1 - k] = 1.0
    elif kind == "comb":
        # 櫛。1 本の背骨から歯が生える = run が多く、連結は 1 個
        a[0, :] = 1.0
        a[:, ::2] = 1.0
    elif kind == "spiral":
        # 長い 1 本のつながり。union-find の経路圧縮を深く踏ませる
        r0, r1, c0, c1 = 0, h - 1, 0, w - 1
        while r0 <= r1 and c0 <= c1:
            a[r0, c0:c1 + 1] = 1.0
            a[r0:r1 + 1, c1] = 1.0
            r0 += 2
            c1 -= 2
    elif kind == "hline_pair":
        # 1 行だけ空けた 2 本の横線 —— 4/8 連結では**どちらでも 2 個**だが、
        # run の隣接判定を「行差 <= 1」と誤ると 1 個になる
        if h >= 3:
            a[0, :] = 1.0
            a[2, :] = 1.0
    elif kind == "corner_chain":
        # 角でつながる階段。8 連結なら 1 個、4 連結なら長さぶんの個数
        for k in range(min(h, w)):
            a[k, k] = 1.0


def gen_case(rng: np.random.Generator) -> dict:
    # 大きい盤面も少し混ぜる。小さい画像だけだと「端の効果が支配的で内部が無い」
    # 状態ばかりになり、カーネル半径や run の連結が長く伸びる経路を踏まない。
    if rng.random() < 0.12:
        h = int(rng.integers(24, 65))
        w = int(rng.integers(24, 65))
    else:
        h = int(rng.integers(1, 17))
        w = int(rng.integers(1, 17))
    a = np.zeros((h, w))
    for _ in range(int(rng.integers(1, 4))):
        _paint(a, str(rng.choice(SHAPES)), rng)
    if rng.random() < 0.3:                      # 雑音は味付けだけ
        a = np.clip(a + rng.random((h, w)) * 0.3, 0.0, 1.0)
    if rng.random() < 0.15:                     # 非有限を混ぜる
        a[int(rng.integers(0, h)), int(rng.integers(0, w))] = \
            float(rng.choice([np.nan, np.inf, -np.inf]))
    # 値域は [0,1] とは限らない(R-3: 取得層が名乗るもので、画素からは推測しない)。
    # ★2026-09-14: ここは長らく値域だけを振って**画素は 0..1 のまま**だった。相対しきい値は
    #   値域を通して解決されるので、値域 (100,300) では絶対値 100〜300 と比べられ、
    #   **100% が空**になっていた(実測: (100,300) は 780/780 が 0 画素、全体でも 63% が
    #   物体 0 個)。4000 ケースが 0.6 秒で「食い違いなし」だったのは頑健だからではなく、
    #   **connection も measure_all もほとんど踏んでいなかった**から
    #   ([[feedback_zero_findings_may_mean_never_executed]])。値域を名乗らせるなら
    #   **画素もその値域で描く**。
    vlo, vhi = [tuple(map(float, t)) for t in
                [(0.0, 1.0), (0.0, 255.0), (100.0, 300.0), (-1.0, 1.0)]][int(rng.integers(0, 4))]
    a = vlo + a * (vhi - vlo)
    if rng.random() < 0.2:                      # 値域の外に出た画素(R-3: clamp しない)
        a[int(rng.integers(0, h)), int(rng.integers(0, w))] = \
            float(vlo + rng.normal(0.5, 1.5) * (vhi - vlo))
    # ★しきい値は**画像に実在する値から**引く。独立に引いていたときは 41% が
    #   「選択 0 画素」で、物体が 2 個以上あるのは 14% だけだった —— `connection` の
    #   分岐(斜め接触・入れ子・多数)をほとんど踏んでいない。乱数で撒くと空ばかりに
    #   なるのは、しきい値も探針の一部だから
    #   ([[feedback_one_probe_input_is_not_coverage]]: 探針は入力画像だけではない)。
    #   2 割は「当てずっぽう」のまま残す —— 空・全面・範囲外という端も要る。
    span = (vhi - vlo) or 1.0
    rel = np.clip((a[np.isfinite(a)] - vlo) / span, -0.5, 1.5) if np.isfinite(a).any() else None
    if rel is not None and rel.size and rng.random() < 0.8:
        q = np.quantile(rel, [float(rng.random()), float(rng.random())])
        lo, hi = float(min(q)), float(max(q))
        if rng.random() < 0.5:                  # 幅を持たせて run をつなげる
            hi = float(hi + rng.random() * 0.3)
    else:
        lo = float(rng.choice([0.0, 0.25, 0.5, 0.75, 1.0, float(rng.random())]))
        hi = float(rng.choice([0.0, 0.25, 0.5, 0.75, 1.0, float(rng.random())]))
    if rng.random() < 0.85 and lo > hi:         # 逆区間は 15% だけ残す
        lo, hi = hi, lo
    return {"px": a, "lo": lo, "hi": hi, "vrange": (float(vlo), float(vhi)),
            "sigma": float(rng.choice([0.5, 1.0, 2.0, 3.5])),
            "feature": str(rng.choice(["area", "row", "column"])),
            "vmin": float(rng.choice([0.0, 1.0, 3.0, 10.0])),
            "vmax": float(rng.choice([0.0, 1.0, 3.0, 10.0, 1e9]))}


# --------------------------------------------------------------------------- #
# 2 実装を同じ入力に通して、観測できるものを全部そろえる
# --------------------------------------------------------------------------- #
def observe_rust(lib, c: dict, ops: set) -> dict:
    a = np.ascontiguousarray(c["px"], dtype=np.float64)
    img = C.c_void_p()
    st = lib.fs_image_create(a.ctypes.data_as(C.c_void_p), a.shape[0], a.shape[1],
                             a.strides[0], c["vrange"][0], c["vrange"][1], C.byref(img))
    if st != 0:
        return {"image": st}
    # 許容差を値域相対で取るために、値域の幅を観測に添える(比較専用の私的な鍵)。
    out: dict = {"image": 0, "_span": abs(c["vrange"][1] - c["vrange"][0]) or 1.0}
    if "gauss" in ops:
        g = C.c_void_p()
        sg = lib.fs_gauss(img, c["sigma"], C.byref(g))
        out["gauss_status"] = sg
        if sg == 0:
            buf = np.empty(a.size, dtype=np.float64)
            lib.fs_debug_copy_pixels(g, buf.ctypes.data_as(C.POINTER(C.c_double)), buf.size)
            out["gauss"] = buf.reshape(a.shape)
            lib.fs_image_release(g)
    reg = C.c_void_p()
    ts = lib.fs_threshold(img, c["lo"], c["hi"], C.byref(reg))
    out["threshold_status"] = ts
    if ts != 0:
        lib.fs_image_release(img)
        return out
    area, nrun = C.c_int64(), C.c_int64()
    lib.fs_region_area(reg, C.byref(area))
    lib.fs_region_run_count(reg, C.byref(nrun))
    out["area"], out["n_runs"] = int(area.value), int(nrun.value)
    objs = C.c_void_p()
    lib.fs_connection(reg, C.byref(objs))
    cnt = C.c_int64()
    lib.fs_objectset_count(objs, C.byref(cnt))
    out["n_comp"] = int(cnt.value)
    ta, tr, tc = C.c_void_p(), C.c_void_p(), C.c_void_p()
    lib.fs_measure_all(objs, C.byref(ta), C.byref(tr), C.byref(tc))

    def vals(t):
        n = C.c_int64()
        lib.fs_tuple_length(t, C.byref(n))
        o = []
        for i in range(int(n.value)):
            v = C.c_double()
            lib.fs_tuple_get_real(t, i, C.byref(v))
            o.append(float(v.value))
        return o
    triples = list(zip(vals(ta), vals(tr), vals(tc)))
    out["measure"] = sorted(triples)
    # ★並びそのものを観測する。`sorted` して比べていたので、**物体の順序を逆にする
    #   変異が 3,000 ケースで 1 件も殺せなかった**(2026-09-14 の変異解析)。契約は
    #   「最初の run の (row, col) 昇順」と明記しているのに、門がどこにも無かった ——
    #   観測していないものは、どれだけケースを撒いても出てこない。
    out["order"] = triples
    for t in (ta, tr, tc):
        lib.fs_tuple_release(t)
    sel = C.c_void_p()
    ss = lib.fs_select_shape(objs, c["feature"].encode(), c["vmin"], c["vmax"], C.byref(sel))
    out["select_status"] = ss
    if ss == 0:
        sc = C.c_int64()
        lib.fs_objectset_count(sel, C.byref(sc))
        out["n_select"] = int(sc.value)
        lib.fs_objectset_release(sel)
    lib.fs_objectset_release(objs)
    lib.fs_region_release(reg)
    lib.fs_image_release(img)
    return out


def observe_python(c: dict, ops: set) -> dict:
    a = np.ascontiguousarray(c["px"], dtype=np.float64)
    try:
        img = fslib.FImage(a, value_range=c["vrange"])
    except Exception:
        return {"image": 1}
    out: dict = {"image": 0}
    if "gauss" in ops:
        try:
            out["gauss"] = np.asarray(
                fslib._REGISTRY["gauss"]["numpy"](img, c["sigma"]).pixels, dtype=np.float64)
            out["gauss_status"] = 0
        except Exception:
            out["gauss_status"] = 1
    try:
        reg = fslib.threshold(img, c["lo"], c["hi"])
        out["threshold_status"] = 0
    except Exception:
        out["threshold_status"] = 1
        return out
    out["area"], out["n_runs"] = int(reg.area()), int(reg.run_count())
    objs = fslib.connection(reg)
    out["n_comp"] = len(objs.ids)
    ar, ro, co = fslib.measure_all(objs)
    triples = list(zip(map(float, ar), map(float, ro), map(float, co)))
    out["measure"] = sorted(triples)
    out["order"] = triples          # 並びも観測する(上の註を参照)
    try:
        sel = fslib.select_shape(objs, c["feature"], c["vmin"], c["vmax"])
        out["select_status"], out["n_select"] = 0, len(sel.ids)
    except Exception:
        out["select_status"] = 1
    return out


def compare(r: dict, p: dict) -> str | None:
    """食い違いを 1 行で返す。無ければ None。"""
    for k in ("image", "threshold_status", "gauss_status", "select_status"):
        rv, pv = (r.get(k, 0) != 0), (p.get(k, 0) != 0)
        if rv != pv:
            return "%s: Rust %s / Python %s" % (
                k, "拒否" if rv else "受理", "拒否" if pv else "受理")
    if "gauss" in r and "gauss" in p:
        finite = np.isfinite(r["gauss"]) & np.isfinite(p["gauss"])
        if finite.any():
            d = float(np.abs(r["gauss"] - p["gauss"])[finite].max())
            # ★許容差は**値域に対する相対**で取る。絶対値で 1e-5 と決めていたら、
            #   値域 (100,300) の画像で 1.04e-05 の差が「食い違い」として報告された ——
            #   が、切り分けると Rust vs scipy は **float64 のままなら 8.53e-14**、
            #   float32 を経由した途端 1.04e-05。つまり `fslib` の `astype(np.float32)`
            #   の丸めで、**欠陥ではなく私の測り方の欠陥**だった(値域比で見ると
            #   どの値域でも一様に 1.4〜5.2e-08 = float32 の相対精度)。
            #   [[feedback_second_instance_artifact_not_physics]] と同じ型 ——
            #   驚く結果は物理(実装の違い)で説明する前に道具を疑う。
            span = abs(r.get("_span", 1.0)) or 1.0
            if d / span > 1e-6:
                return "gauss: 最大差 %.3g(値域比 %.3g)" % (d, d / span)
        if (np.isfinite(r["gauss"]) != np.isfinite(p["gauss"])).any():
            return "gauss: 非有限の位置が違う"
    for k in ("area", "n_runs", "n_comp", "n_select"):
        if k in r and k in p and r[k] != p[k]:
            return "%s: Rust %s / Python %s" % (k, r[k], p[k])
    if "measure" in r and "measure" in p:
        if len(r["measure"]) != len(p["measure"]):
            return "measure: 個数 %d / %d" % (len(r["measure"]), len(p["measure"]))
        for g, w in zip(r["measure"], p["measure"]):
            if any(abs(x - y) > 1e-9 for x, y in zip(g, w)):
                return "measure: %s / %s" % (g, w)
    return None


def shrink(lib, c: dict, ops: set, why: str) -> dict:
    """食い違いを保ったまま盤面を小さくする。読めない証拠は証拠にならない。"""
    def still_bad(cand: dict) -> bool:
        try:
            return compare(observe_rust(lib, cand, ops), observe_python(cand, ops)) is not None
        except Exception:
            return False

    cur = dict(c)
    changed = True
    while changed:
        changed = False
        h, w = cur["px"].shape
        for sl in ([(slice(0, h // 2), slice(None)), (slice(h // 2, h), slice(None))]
                   if h > 1 else []) + \
                  ([(slice(None), slice(0, w // 2)), (slice(None), slice(w // 2, w))]
                   if w > 1 else []):
            cand = dict(cur)
            cand["px"] = np.ascontiguousarray(cur["px"][sl])
            if cand["px"].size and still_bad(cand):
                cur, changed = cand, True
                break
    return cur


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cases", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--ops", default="all", help="all | noguass(gauss を外す)")
    ap.add_argument("--max-report", type=int, default=8)
    args = ap.parse_args()

    lib = load_rust()
    ops = set() if args.ops == "nogauss" else {"gauss"}
    rng = np.random.default_rng(args.seed)
    found: list[tuple[str, dict]] = []
    seen: set[str] = set()
    t0 = time.perf_counter()
    for i in range(args.cases):
        c = gen_case(rng)
        try:
            why = compare(observe_rust(lib, c, ops), observe_python(c, ops))
        except Exception as e:                 # 片方が落ちるのも立派な食い違い
            why = "例外 %s: %s" % (type(e).__name__, e)
        if why is None:
            continue
        key = why.split(":")[0]
        if key in seen:
            continue
        seen.add(key)
        found.append((why, shrink(lib, c, ops, why)))
        if len(found) >= args.max_report:
            break
    dt = time.perf_counter() - t0

    print("%d ケース / %.1f 秒 / 食い違いの種類 %d" % (i + 1, dt, len(found)))
    if not found:
        print("食い違いなし —— **これは正しさの証明ではない**。文法が踏んでいない")
        print("座標(値域の混在、領域の入れ子、大きな画像)が残っている可能性を先に疑う。")
        return 0
    for why, c in found:
        print()
        print("★ %s" % why)
        print("  盤面 %s / 値域 %s / lo=%g hi=%g / sigma=%g / select %s [%g,%g]"
              % (c["px"].shape, c["vrange"], c["lo"], c["hi"], c["sigma"],
                 c["feature"], c["vmin"], c["vmax"]))
        print("  px = %s" % json.dumps(np.round(c["px"], 3).tolist()))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
