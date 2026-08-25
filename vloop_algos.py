"""§4b — 閉ループでの最適アルゴリズムは、静止画での最高精度アルゴリズムか。

正本 = ``docs/HIGHSPEED_VISION.md`` の §3b(研究の問い)と §4b(時間予算つき適応度)。

## 何を測るか

H1 の台(``vloop.py``)の上で、**同じ課題を違う値段の検出器で解く**。要点は

> **検出器の実行時間を、そのまま閉ループの遅延として食わせる。**

5 ms かかるアルゴリズムは 5 ms の遅延そのものである。静止画のベンチマークは
この事実を落としているので、精度だけで順位を付けると閉ループでは負ける。

## 事前登録した予測(実行前に書いた)

- **P4(本命)**: 静止画での精度順位と閉ループでの順位が **入れ替わる**。
  具体的には、いちばん正確な NCC テンプレート照合が閉ループでは負け、
  いちばん粗い Self-Windowing 重心が勝つ
- **P3**: 精度だけの評価と、時間予算つきの評価で **選ばれる検出器が違う**
- 外れる可能性: numpy の実装差が大きすぎて、値段の差がアルゴリズムの差ではなく
  実装の差になる。その場合は「画素に触れた回数」による実装非依存の費用でも測り、
  両方を並べて開示する(下の `cost_ops`)

## 費用の測り方 — 2 通り並べる(honest)

1. **実測の壁時計**(この CPU の numpy 実装での中央値)。実装依存。
2. **画素に触れた回数**(宣言値)。実装非依存だが定数倍を無視する。

どちらか一方だけでは誤解を招く。**GPU / FPGA / ビジョンチップに載せれば定数は
変わるが、オーダーは変わらない** —— 石川研がハードで解いたのはこの定数の部分。

    import vloop_algos
    vloop_algos.main()
"""
from __future__ import annotations

import time
from dataclasses import dataclass, replace

import numpy as np

import vloop
from vloop import VLoop, VLoopCfg

RES = 1024                # **作動点**。ここで初めて全画面処理が 1 ms 予算に入らない
                          #   実測 res 128/512/1024 で 全画面重心 0.02/0.43/2.89 ms、
                          #   球径 6/26/53 px。128 では全部が 0 ms に丸まり、
                          #   遅延軸がまったく効かなかった(最初の試行は失敗)
LOOP_STEPS = 1200         # 高解像度は 1 歩が高いので H1 の 3000 より短く
LOOP_PHASES = (0.0, 0.9)
THROUGHPUT = 2.0e8        # 画素演算/秒。cost_ops を ms に直すための宣言値


# --------------------------------------------------------------------------
# 検出器 — いずれも「赤い球の列位置」を返す。state は次フレームへ持ち越す
# --------------------------------------------------------------------------
def _mask(img):
    r = img[:, :, 0].astype(np.int16)
    g = img[:, :, 1].astype(np.int16)
    b = img[:, :, 2].astype(np.int16)
    return (r > 110) & (r - g > 60) & (r - b > 60)


def _cx(mask, col_offset=0.0):
    m00 = float(mask.sum())
    if m00 < 3.0:
        return None
    cols = np.arange(mask.shape[1], dtype=float) + col_offset
    return float((mask * cols[None, :]).sum() / m00)


def full_centroid(img, st):
    """全画面のしきい値 + 重心。素直だが毎フレーム全画素に触る。"""
    return _cx(_mask(img)), st


def _cyx(mask):
    """重心を (行, 列) で返す。0 次と 1 次のモーメントだけ。"""
    m00 = float(mask.sum())
    if m00 < 3.0:
        return None
    rows = np.arange(mask.shape[0], dtype=float)
    cols = np.arange(mask.shape[1], dtype=float)
    return (float((mask.sum(1) * rows).sum() / m00),
            float((mask.sum(0) * cols).sum() / m00))


def _full_yx(img):
    r = _cyx(_mask(img))
    return r


def window_centroid(img, st, w=128):
    """Self-Windowing — 前フレームの重心まわりの **2 次元の小窓** だけ処理する。

    石川研の高速化の中核。**計算量が画面の大きさでなく対象の大きさで決まる**。
    見失ったら次フレームだけ全画面に戻す(復帰の代償も費用に含める)。

    最初の実装は列だけを切っていて(``img[:, lo:hi]``)、行は全部走査していた。
    それでは画面の高さに比例したままで Self-Windowing になっていない。
    """
    H, W = img.shape[0], img.shape[1]
    last = st.get("yx")
    if last is not None:
        cy, cx = int(round(last[0])), int(round(last[1]))
        y0, y1 = max(0, cy - w // 2), min(H, cy + w // 2)
        x0, x1 = max(0, cx - w // 2), min(W, cx + w // 2)
        sub = _cyx(_mask(img[y0:y1, x0:x1]))
        if sub is not None:
            yx = (sub[0] + y0, sub[1] + x0)
            return yx[1], {"yx": yx}
    yx = _full_yx(img)                      # 初回 or 見失い -> 全画面へ復帰
    return (None if yx is None else yx[1]), {"yx": yx}


def coarse_centroid(img, st, k=4):
    """1/k に間引いてから重心。安いが量子化で粗くなる。"""
    sub = img[::k, ::k]
    u = _cx(_mask(sub))
    return (None if u is None else u * k), st


def row_scan(img, st, k=4):
    """行を k 本に 1 本だけ走査。列の分解能は保つ。"""
    sub = img[::k, :]
    return _cx(_mask(sub)), st


def _template(n=53):
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot(y - (n - 1) / 2, x - (n - 1) / 2)
    t = (r <= (n - 1) / 2).astype(float)
    return t - t.mean()


_TPL = _template()


def ncc_template(img, st):
    """テンプレート照合 + 放物線あてはめのサブピクセル。いちばん正確で高い。"""
    from scipy.signal import fftconvolve
    r = img[:, :, 0].astype(float) - img[:, :, 1].astype(float)
    resp = fftconvolve(r, _TPL[::-1, ::-1], mode="same")
    j = int(np.argmax(resp))
    yy, xx = np.unravel_index(j, resp.shape)
    if resp[yy, xx] < 200.0:
        return None, st
    if 0 < xx < resp.shape[1] - 1:                # 放物線でサブピクセル
        a, b, c = resp[yy, xx - 1], resp[yy, xx], resp[yy, xx + 1]
        den = a - 2 * b + c
        d = 0.0 if abs(den) < 1e-9 else 0.5 * (a - c) / den
        return float(xx + np.clip(d, -1, 1)), st
    return float(xx), st


DETECTORS = {
    "全画面重心": (full_centroid, lambda h, w: h * w),
    "窓重心(2次元)": (window_centroid, lambda h, w: 128 * 128),
    "間引き重心(1/4)": (coarse_centroid, lambda h, w: h * w / 16),
    "行走査(1/4)": (row_scan, lambda h, w: h * w / 4),
    "テンプレート照合": (ncc_template, lambda h, w: 6 * h * w * np.log2(h * w)),
}


# --------------------------------------------------------------------------
# 1. 静止画での精度と値段
# --------------------------------------------------------------------------
def bench_static(n_frames: int = 60, res: int = RES) -> dict:
    """真値つきフレームを作り、各検出器の誤差と実行時間を測る。"""
    base = VLoopCfg(res=res)
    loop = VLoop(base)
    xs = np.linspace(-0.42, 0.42, n_frames)
    frames, truth = [], []
    for x in xs:
        loop.data.qpos[loop.tx] = float(x)
        vloop.mujoco.mj_forward(loop.model, loop.data)
        loop.renderer.update_scene(loop.data, camera="top")
        frames.append(loop.renderer.render().copy())
        truth.append(float(x))
    truth = np.array(truth)

    out = {}
    for name, (fn, ops) in DETECTORS.items():
        st, est = {}, []
        for img in frames:                        # 1 巡目で state を温める
            u, st = fn(img, st)
            est.append(np.nan if u is None else loop.pix_to_x(u))
        t0 = time.perf_counter()
        reps = 3
        for _ in range(reps):
            st2 = {}
            for img in frames:
                _, st2 = fn(img, st2)
        ms = (time.perf_counter() - t0) / (reps * len(frames)) * 1000.0
        est = np.array(est, dtype=float)
        ok = np.isfinite(est)
        out[name] = {
            "err_mm": float(np.abs(est[ok] - truth[ok]).mean() * 1000.0),
            "miss": int((~ok).sum()),
            "ms": ms,
            "ops_ms": float(ops(res, res) / THROUGHPUT * 1000.0),
        }
    return out


# --------------------------------------------------------------------------
# 2. 閉ループ — 実行時間をそのまま遅延として食わせる
# --------------------------------------------------------------------------
def run_in_loop(name: str, latency_ms: int, phases=(0.0, 0.9, 1.8),
                res: int = RES, extra_ms: int = 0) -> float:
    """その検出器を実際に閉ループで回す。latency_ms は n_compute に載せる。"""
    fn = DETECTORS[name][0]
    base = VLoopCfg(res=res, n_compute=int(latency_ms) + int(extra_ms))
    loop = VLoop(base)
    rmses = []
    for ph in phases:
        rmses.append(_run_with(loop, base, fn, ph))
    return float(np.mean(rmses))


def _run_with(loop: VLoop, c: VLoopCfg, fn, phase: float) -> float:
    """vloop.VLoop.run の検出器差し替え版(重心固定でなく fn を使う)。"""
    m, d = loop.model, loop.data
    vloop.mujoco.mj_resetData(m, d)
    meas_buf: list[float | None] = [None] * (c.n_compute + 1)
    cmd_buf: list[float] = [0.0] * (c.n_act + 1)
    err = np.zeros(c.steps)
    st: dict = {}
    for k in range(c.steps):
        xt = float(vloop.target_x(k, c, phase))
        d.qpos[loop.tx] = xt
        d.qvel[loop.tx] = 0.0
        vloop.mujoco.mj_forward(m, d)
        loop.renderer.update_scene(d, camera="top")
        img = loop.renderer.render()

        u, st = fn(img, st)
        meas_buf.append(None if u is None else float(loop.pix_to_x(u)))
        ready = meas_buf.pop(0)
        cmd = ready if ready is not None else cmd_buf[-1]
        cmd_buf.append(float(np.clip(cmd, -1.0, 1.0)))
        d.ctrl[0] = cmd_buf.pop(0)
        vloop.mujoco.mj_step(m, d)
        err[k] = abs(float(d.qpos[loop.px]) - xt)
    w = int(c.steps * c.warmup_frac)
    return float(np.sqrt((err[w:] ** 2).mean()))


_LOOP_CACHE: dict[int, VLoop] = {}


def _loop_for(res: int) -> VLoop:
    """GL コンテキストは解像度ごとに 1 つだけ作って使い回す。"""
    if res not in _LOOP_CACHE:
        _LOOP_CACHE[res] = VLoop(VLoopCfg(res=res, steps=LOOP_STEPS))
    return _LOOP_CACHE[res]


# --------------------------------------------------------------------------
# 3. 雑音を入れて「精度が効く領域」まで課題を難しくする -> 交換の前線
# --------------------------------------------------------------------------
def add_noise(img, rng, p_bad: float, sigma: float = 8.0):
    """センサ雑音。**赤い偽画素** を撒くのがしきい値 + 重心には効く。

    現実の対応物 = ホットピクセル、反射、赤い別物。全画面の重心は遠くの外れ値に
    引きずられるが、小窓しか見ない Self-Windowing は構造的にそれを見ない。
    """
    if p_bad <= 0.0 and sigma <= 0.0:
        return img
    out = img.astype(np.int16)
    if sigma > 0.0:
        out += rng.normal(0.0, sigma, out.shape).astype(np.int16)
    if p_bad > 0.0:
        n = int(p_bad * img.shape[0] * img.shape[1])
        if n:
            yy = rng.integers(0, img.shape[0], n)
            xx = rng.integers(0, img.shape[1], n)
            out[yy, xx, 0] = 255
            out[yy, xx, 1] = 20
            out[yy, xx, 2] = 20
    return np.clip(out, 0, 255).astype(np.uint8)


def bench_static_noise(p_bad: float, n_frames: int = 40, res: int = RES,
                       seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    loop = _loop_for(res)
    xs = np.linspace(-0.42, 0.42, n_frames)
    frames, truth = [], []
    for x in xs:
        loop.data.qpos[loop.tx] = float(x)
        vloop.mujoco.mj_forward(loop.model, loop.data)
        loop.renderer.update_scene(loop.data, camera="top")
        frames.append(add_noise(loop.renderer.render(), rng, p_bad))
        truth.append(float(x))
    truth = np.array(truth)
    out = {}
    for name, (fn, _) in DETECTORS.items():
        st, est = {}, []
        for img in frames:
            u, st = fn(img, st)
            est.append(np.nan if u is None else loop.pix_to_x(u))
        est = np.array(est, dtype=float)
        ok = np.isfinite(est)
        out[name] = float(np.abs(est[ok] - truth[ok]).mean() * 1000.0)             if ok.any() else float("nan")
    return out


def run_in_loop_noise(name: str, latency_ms: int, p_bad: float,
                      res: int = RES, steps: int = 800,
                      phase: float = 0.0, seed: int = 0) -> float:
    fn = DETECTORS[name][0]
    c = VLoopCfg(res=res, steps=steps, n_compute=int(latency_ms))
    loop = _loop_for(res)
    rng = np.random.default_rng(seed)
    m, d = loop.model, loop.data
    vloop.mujoco.mj_resetData(m, d)
    meas_buf: list[float | None] = [None] * (c.n_compute + 1)
    cmd_buf: list[float] = [0.0]
    err = np.zeros(steps)
    st: dict = {}
    for k in range(steps):
        xt = float(vloop.target_x(k, c, phase))
        d.qpos[loop.tx] = xt
        d.qvel[loop.tx] = 0.0
        vloop.mujoco.mj_forward(m, d)
        loop.renderer.update_scene(d, camera="top")
        img = add_noise(loop.renderer.render(), rng, p_bad)
        u, st = fn(img, st)
        meas_buf.append(None if u is None else float(loop.pix_to_x(u)))
        ready = meas_buf.pop(0)
        cmd = ready if ready is not None else cmd_buf[-1]
        cmd_buf.append(float(np.clip(cmd, -1.0, 1.0)))
        d.ctrl[0] = cmd_buf.pop(0)
        vloop.mujoco.mj_step(m, d)
        err[k] = abs(float(d.qpos[loop.px]) - xt)
    w = int(steps * c.warmup_frac)
    return float(np.sqrt((err[w:] ** 2).mean()))


def frontier(levels=(0.0, 0.0002, 0.001, 0.005), lat: dict | None = None):
    """雑音を上げながら、静止画の精度と閉ループ RMSE の両方を追う。"""
    print("")
    print("  3. 雑音を入れる — 精度が効く領域まで難しくする")
    print(f"     偽の赤画素を p の割合で撒く(ホットピクセル / 反射 / 赤い別物)")
    print(f"\n静止画の誤差 mm")
    hdr = "".join(f"{n:>16}" for n in DETECTORS)
    print(f"     {'p':>8}{hdr}")
    stat = {}
    for p_bad in levels:
        stat[p_bad] = bench_static_noise(p_bad)
        print(f"     {p_bad:>8.4f}" + "".join(
            f"{stat[p_bad][n]:16.2f}" for n in DETECTORS))
    print(f"\n閉ループ RMSE m(実行時間を遅延として食わせたまま)")
    print(f"     {'p':>8}{hdr}")
    loop_r = {}
    for p_bad in levels:
        loop_r[p_bad] = {n: run_in_loop_noise(n, lat[n], p_bad)
                         for n in DETECTORS}
        print(f"     {p_bad:>8.4f}" + "".join(
            f"{loop_r[p_bad][n]:16.4f}" for n in DETECTORS), flush=True)
    print(f"\n各雑音水準での閉ループ 1 位")
    for p_bad in levels:
        best = min(loop_r[p_bad], key=lambda n: loop_r[p_bad][n])
        sbest = min(stat[p_bad], key=lambda n: stat[p_bad][n])
        print(f"     p={p_bad:.4f}  閉ループ 1 位 {best:<16}"
              f"静止画 1 位 {sbest}")
    return stat, loop_r


def main():
    if not vloop.available():
        print("mujoco が無い")
        return
    print("§4b — 閉ループでの最適検出器は、静止画での最高精度検出器か")
    print(f"  解像度 {RES}x{RES} / 費用は 2 通り(実測の壁時計 と 画素演算数)")

    st = bench_static()
    print(f"\n  1. 静止画での精度と値段")
    print(f"  {'検出器':<18}{'誤差 mm':>10}{'見失い':>8}"
          f"{'実測 ms':>10}{'画素演算 ms':>13}")
    for n, v in st.items():
        print(f"  {n:<18}{v['err_mm']:10.2f}{v['miss']:>8}"
              f"{v['ms']:10.2f}{v['ops_ms']:13.3f}")

    acc_rank = sorted(st, key=lambda n: st[n]["err_mm"])
    print(f"\n  静止画の精度順位: {' > '.join(acc_rank)}")

    print(f"\n  2. 閉ループ(実行時間をそのまま遅延に食わせる)")
    print(f"  {'検出器':<18}{'遅延 ms':>9}{'閉ループ RMSE m':>17}")
    loop_res = {}
    for n in DETECTORS:
        lat = int(round(st[n]["ms"]))
        loop_res[n] = run_in_loop(n, lat)
        print(f"  {n:<18}{lat:>9}{loop_res[n]:17.4f}", flush=True)

    loop_rank = sorted(loop_res, key=lambda n: loop_res[n])
    print(f"\n  閉ループの順位:   {' > '.join(loop_rank)}")

    same = acc_rank == loop_rank
    print(f"\n  P4 の判定: 順位は{'変わらなかった' if same else '**入れ替わった**'}")
    if not same:
        print(f"    静止画 1 位 = {acc_rank[0]} -> 閉ループでは "
              f"{loop_rank.index(acc_rank[0]) + 1} 位")
        print(f"    閉ループ 1 位 = {loop_rank[0]} は静止画では "
              f"{acc_rank.index(loop_rank[0]) + 1} 位")

    # 対照: 全部を遅延 0 で回すと順位はどうなるか(= 精度だけの評価)
    print(f"\n  対照: 全部を遅延 0 で回した場合(精度だけの評価に相当)")
    zero = {n: run_in_loop(n, 0) for n in DETECTORS}
    for n in sorted(zero, key=lambda x: zero[x]):
        print(f"   {n:<18}{zero[n]:10.4f}")
    print(f"  遅延 0 の順位:    {' > '.join(sorted(zero, key=lambda n: zero[n]))}")

    frontier(lat={n: int(round(st[n]["ms"])) for n in DETECTORS})


if __name__ == "__main__":
    main()
