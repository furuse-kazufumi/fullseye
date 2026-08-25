"""§4b の本体 — 時間予算つきの適応度は「安いが十分な」検出器を自力で見つけるか。

正本 = ``docs/HIGHSPEED_VISION.md`` §4b。

## 問い

ユーザーの一次観察(東大 山川研究室でじゃんけんロボットの実機を見た):

> 手のひらを中心に円弧状のプロファイルを取り、指の本数を数える。
> ルールベースを GPU で回しているだけ。

**人間の設計者は「安いが十分」に到達していた。** Fullseye は
「アルゴリズムを設計する AI」なのだから、同じ場所に到達できるべきである。
ところが今の進化は精度だけで選抜している(`evolve.py`: "Fitness is the TRAIN
score only")。それでは「重くて正確なもの」が必ず勝つ。

そこで **適応度を 2 通り用意して、選ばれる検出器が違うかを測る**。

    適応度 A(従来)   静止画での誤差だけ。速さは見ない
    適応度 B(時間予算) 閉ループ RMSE。**実行時間がそのまま遅延として効く**

## 探索空間(意図的に小さく、解釈できる形にする)

    use_window   前フレーム重心まわりの小窓だけ見るか(Self-Windowing)
    w            窓の一辺 [px]
    stride       行と列を何本に 1 本走査するか
    thresh       赤判定のしきい値
    method       重心 / テンプレート照合
    tpl_n        テンプレートの一辺(method=template のとき)

**円弧プロファイルの直系** は `use_window=True` + 大きめ `stride` の組。
進化がそこへ行くかどうかが見どころ。

## 事前登録した予測(実行前)

- **適応度 A は use_window=False・stride=1**(全画素を見る最も正確なもの)を選ぶ
- **適応度 B は use_window=True** を選ぶ。stride も 1 より大きくなる
- **2 つの適応度が選ぶ個体は違う**(= P3)
- 外れる可能性: B でも全画面が勝つ。その場合は解像度 1024 でも
  全画面がまだ予算に入っているということで、作動点を上げ直す
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import vloop
from vloop import VLoop, VLoopCfg

RES = 1024
STEPS = 600               # 1 評価の長さ。高い個体が居るので H1 より短く
POP = 8
GENS = 8
N_STATIC = 24             # 静止画の評価に使うフレーム数
COST_CAP_MS = 80.0        # これを超える個体は閉ループを回さず失格にする(時間の保護)
SPEED = 1.0               # 目標の速さ倍率。**静止画の適応度は原理的にこれに反応できない**
                          #   (静止画評価に対象の速さが入らないため)。時間予算つきだけが
                          #   作動点に適応できる、というのがこの軸を置く理由
NOISE_P = 0.0             # 偽の赤画素の割合。**0 だと支配解ができて適応度が分岐しない**
                          #   実測(交換の前線): p=0.001 で静止画 1 位 = テンプレート、
                          #   閉ループ 1 位 = 窓重心 と割れる。そこが検定になる作動点


# --------------------------------------------------------------------------
# 遺伝子 -> 検出器
# --------------------------------------------------------------------------
GENE_SPEC = {
    "use_window": (0, 1),
    "w":          (16, 512),
    "stride":     (1, 8),
    "thresh":     (60, 200),
    "method":     (0, 1),          # 0 = 重心, 1 = テンプレート照合
    "tpl_n":      (9, 81),
}


def random_gene(rng) -> dict:
    return {k: int(rng.integers(lo, hi + 1)) for k, (lo, hi) in GENE_SPEC.items()}


def mutate(g: dict, rng, rate: float = 0.4) -> dict:
    out = dict(g)
    for k, (lo, hi) in GENE_SPEC.items():
        if rng.random() < rate:
            span = max(1, (hi - lo) // 4)
            out[k] = int(np.clip(g[k] + rng.integers(-span, span + 1), lo, hi))
    return out


def _mask(img, thresh):
    r = img[:, :, 0].astype(np.int16)
    g = img[:, :, 1].astype(np.int16)
    b = img[:, :, 2].astype(np.int16)
    return (r > thresh) & (r - g > 60) & (r - b > 60)


def _cyx(mask, y0=0.0, x0=0.0, s=1):
    m00 = float(mask.sum())
    if m00 < 3.0:
        return None
    rows = np.arange(mask.shape[0], dtype=float) * s + y0
    cols = np.arange(mask.shape[1], dtype=float) * s + x0
    return (float((mask.sum(1) * rows).sum() / m00),
            float((mask.sum(0) * cols).sum() / m00))


def _tpl(n):
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot(y - (n - 1) / 2, x - (n - 1) / 2)
    t = (r <= (n - 1) / 2).astype(float)
    return t - t.mean()


_TPL_CACHE: dict[int, np.ndarray] = {}


def detect(img, st, g: dict):
    """遺伝子が指す検出器を実行し、列位置と次の state を返す。"""
    H, W = img.shape[0], img.shape[1]
    s = max(1, int(g["stride"]))

    if g["use_window"] and st.get("yx") is not None:
        cy, cx = int(round(st["yx"][0])), int(round(st["yx"][1]))
        h = max(8, int(g["w"])) // 2
        y0, y1 = max(0, cy - h), min(H, cy + h)
        x0, x1 = max(0, cx - h), min(W, cx + h)
        sub = img[y0:y1:s, x0:x1:s]
        off = (y0, x0)
    else:
        sub = img[::s, ::s]
        off = (0, 0)

    if g["method"] == 0:
        yx = _cyx(_mask(sub, g["thresh"]), off[0], off[1], s)
    else:
        n = max(5, int(g["tpl_n"]) // s) | 1
        if n not in _TPL_CACHE:
            _TPL_CACHE[n] = _tpl(n)
        from scipy.signal import fftconvolve
        r = sub[:, :, 0].astype(float) - sub[:, :, 1].astype(float)
        if min(r.shape) <= n:
            yx = None
        else:
            resp = fftconvolve(r, _TPL_CACHE[n][::-1, ::-1], mode="same")
            j = int(np.argmax(resp))
            yy, xx = np.unravel_index(j, resp.shape)
            yx = (None if resp[yy, xx] < 100.0
                  else (yy * s + off[0], xx * s + off[1]))

    if yx is None:
        if g["use_window"] and st.get("yx") is not None:
            return None, {"yx": None}         # 次フレームは全画面へ復帰
        return None, {"yx": None}
    return yx[1], {"yx": yx}


# --------------------------------------------------------------------------
# 評価
# --------------------------------------------------------------------------
_LOOP: dict[int, VLoop] = {}


def loop_for(res: int) -> VLoop:
    if res not in _LOOP:
        _LOOP[res] = VLoop(VLoopCfg(res=res, steps=STEPS))
    return _LOOP[res]


_FRAMES: dict[int, tuple] = {}


def frames_for(res: int):
    """静止画の評価用フレーム(真値つき)。雑音も込みで 1 度だけ作って使い回す
    (全個体が同じフレームを見る = 公平)。"""
    key = (res, NOISE_P)
    if key in _FRAMES:
        return _FRAMES[key]
    lp = loop_for(res)
    rng = np.random.default_rng(1234)
    xs = np.linspace(-0.42, 0.42, N_STATIC)
    imgs = []
    for x in xs:
        lp.data.qpos[lp.tx] = float(x)
        vloop.mujoco.mj_forward(lp.model, lp.data)
        lp.renderer.update_scene(lp.data, camera="top")
        imgs.append(_noise(lp.renderer.render().copy(), rng))
    _FRAMES[key] = (imgs, np.array(xs, dtype=float))
    return _FRAMES[key]


def _noise(img, rng, sigma: float = 8.0):
    """偽の赤画素 + ガウス雑音。NOISE_P = 0 なら素通し。"""
    if NOISE_P <= 0.0:
        return img
    out = img.astype(np.int16) + rng.normal(0.0, sigma, img.shape).astype(np.int16)
    n = int(NOISE_P * img.shape[0] * img.shape[1])
    if n:
        yy = rng.integers(0, img.shape[0], n)
        xx = rng.integers(0, img.shape[1], n)
        out[yy, xx, 0], out[yy, xx, 1], out[yy, xx, 2] = 255, 20, 20
    return np.clip(out, 0, 255).astype(np.uint8)


def static_score(g: dict, res: int = RES) -> tuple[float, float]:
    """(静止画の平均誤差 [m], 1 フレームあたりの実行時間 [ms])。"""
    imgs, truth = frames_for(res)
    lp = loop_for(res)
    st, est = {}, []
    for img in imgs:
        u, st = detect(img, st, g)
        est.append(np.nan if u is None else lp.pix_to_x(u))
    t0 = time.perf_counter()
    st2 = {}
    for img in imgs:
        _, st2 = detect(img, st2, g)
    ms = (time.perf_counter() - t0) / len(imgs) * 1000.0
    est = np.array(est, dtype=float)
    ok = np.isfinite(est)
    if ok.sum() < len(est) * 0.5:
        return float("inf"), ms
    return float(np.abs(est[ok] - truth[ok]).mean()), ms


def loop_score(g: dict, ms: float, res: int = RES, phase: float = 0.0) -> float:
    """閉ループ RMSE。**実行時間 ms をそのまま遅延に食わせる**。"""
    if ms > COST_CAP_MS:
        return float("inf")
    lat = int(round(ms))
    c = VLoopCfg(res=res, steps=STEPS, n_compute=lat,
                 f1=0.7 * SPEED, f2=1.9 * SPEED)
    lp = loop_for(res)
    m, d = lp.model, lp.data
    vloop.mujoco.mj_resetData(m, d)
    rng = np.random.default_rng(4321)
    meas: list[float | None] = [None] * (lat + 1)
    cmd_buf = [0.0]
    err = np.zeros(STEPS)
    st: dict = {}
    for k in range(STEPS):
        xt = float(vloop.target_x(k, c, phase))
        d.qpos[lp.tx] = xt
        d.qvel[lp.tx] = 0.0
        vloop.mujoco.mj_forward(m, d)
        lp.renderer.update_scene(d, camera="top")
        u, st = detect(_noise(lp.renderer.render(), rng), st, g)
        meas.append(None if u is None else float(lp.pix_to_x(u)))
        ready = meas.pop(0)
        cmd = ready if ready is not None else cmd_buf[-1]
        cmd_buf.append(float(np.clip(cmd, -1.0, 1.0)))
        d.ctrl[0] = cmd_buf.pop(0)
        vloop.mujoco.mj_step(m, d)
        err[k] = abs(float(d.qpos[lp.px]) - xt)
    w = int(STEPS * 0.2)
    return float(np.sqrt((err[w:] ** 2).mean()))


def describe(g: dict) -> str:
    meth = "重心" if g["method"] == 0 else f"テンプレート({g['tpl_n']})"
    win = f"窓{g['w']}" if g["use_window"] else "全画面"
    return f"{win}/間引き1-{g['stride']}/しきい{g['thresh']}/{meth}"


def evolve(fitness: str, seed: int = 0, log=None) -> dict:
    """fitness = 'static'(精度だけ)or 'loop'(時間予算つき)。"""
    rng = np.random.default_rng(seed)
    pop = [random_gene(rng) for _ in range(POP)]
    best = None
    for gen in range(GENS):
        scored = []
        for g in pop:
            err, ms = static_score(g)
            f = err if fitness == "static" else loop_score(g, ms)
            scored.append((f, err, ms, g))
        scored.sort(key=lambda r: (np.inf if not np.isfinite(r[0]) else r[0]))
        if best is None or scored[0][0] < best[0]:
            best = scored[0]
        line = (f"    世代 {gen:>2}  最良 {scored[0][0]:.5f}  "
                f"静止画 {scored[0][1] * 1000:.2f} mm  "
                f"費用 {scored[0][2]:.2f} ms  {describe(scored[0][3])}")
        print(line, flush=True)
        if log is not None:
            log.append({"gen": gen, "fit": float(scored[0][0]),
                        "err_mm": float(scored[0][1] * 1000),
                        "ms": float(scored[0][2]), "gene": scored[0][3]})
        elite = [r[3] for r in scored[: POP // 2]]
        pop = elite + [mutate(elite[int(rng.integers(0, len(elite)))], rng)
                       for _ in range(POP - len(elite))]
    return {"fit": float(best[0]), "err": float(best[1]), "ms": float(best[2]),
            "gene": best[3]}


def main():
    if not vloop.available():
        print("mujoco が無い")
        return
    print("§4b — 時間予算つきの適応度は「安いが十分」を自力で見つけるか")
    print(f"  解像度 {RES} / 個体 {POP} x 世代 {GENS} / 1 評価 {STEPS} 歩"
          f" / 雑音 p={NOISE_P}")
    out = {}
    for fit in ("static", "loop"):
        name = "適応度 A(精度だけ)" if fit == "static" else "適応度 B(時間予算)"
        print(f"\n  {name}")
        log: list = []
        out[fit] = evolve(fit, seed=0, log=log)
        out[fit + "_log"] = log

    a, b = out["static"], out["loop"]
    print("\n  結果")
    print(f"   {'':<14}{'選ばれた検出器':<40}{'静止画 mm':>11}{'費用 ms':>10}")
    print(f"   {'適応度 A':<14}{describe(a['gene']):<40}"
          f"{a['err'] * 1000:11.2f}{a['ms']:10.2f}")
    print(f"   {'適応度 B':<14}{describe(b['gene']):<40}"
          f"{b['err'] * 1000:11.2f}{b['ms']:10.2f}")

    print("\n  交差評価(それぞれを相手の物差しで測る)")
    a_loop = loop_score(a["gene"], a["ms"])
    b_loop = b["fit"]
    print(f"   A が選んだものを閉ループで  {a_loop:.4f}")
    print(f"   B が選んだものを閉ループで  {b_loop:.4f}")
    print(f"   A が選んだものの静止画誤差  {a['err'] * 1000:.2f} mm")
    print(f"   B が選んだものの静止画誤差  {b['err'] * 1000:.2f} mm")

    diff = describe(a["gene"]) != describe(b["gene"])
    print(f"\n  P3 の判定: 2 つの適応度が選んだ検出器は"
          f"{'**違う**' if diff else '同じ'}")
    print(f"  Self-Windowing を選んだか: A={bool(a['gene']['use_window'])} "
          f"B={bool(b['gene']['use_window'])}")

    Path("out").mkdir(exist_ok=True)
    Path("out/vloop_evolve.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n  -> out/vloop_evolve.json")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        NOISE_P = float(sys.argv[1])
    main()
