# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: ハエの脳の立体の上で、刺激の波が配線を伝わるのを見る ―― コネクトーム vs 次数保存 shuffle

前の展示(`poc_larval_connectome_reservoir`)は「読み出し精度ではコネクトームと乱数グラフの差が出ない」で
終わった。それは**配線に構造が無い**という意味ではない —— 精度という 1 つの数では見えないだけかもしれない。
この PoC は同じ道具(reservoir)を**見る**ことに使う: soma の座標を持つニューロンの部分グラフに、右の視葉
(視覚系)だけへ刺激を入れ、活動が脳から VNC(腹部神経索)へ伝わる様子を、脳の立体を回しながら色で描く。
隣に、各ニューロンの入出次数を保ったまま辺を繋ぎ替えたグラフ(`graph_degree_preserving_shuffle`)で
**同じ刺激・同じ入力行列**を回したものを並べる。

**主張は 1 つだけ**: コネクトームでは活動が視葉 → 中枢 → 下行ニューロンと**順に**進み(手元の実測では
36 步・上位 3,000 体の部分グラフでは VNC まで届かない)、shuffle では 3 步で全体に散る。配線の空間構造は、精度では見えなくても動きでは見える。数字は `graph_activity_spread`
(刺激の重心からの活動の平均距離)と `graph_activation_latency`(各ニューロンが初めて点いたステップ)で出す。

データ:
* MaleCNS(Janelia FlyEM、male CNS v1.0、minconf 0.5)の body annotations(soma の位置・左右・上位クラス)と
  connectome weights(pre / post / シナプス数)。**大きい(1 GB)ので実行時に取得しない**: 環境変数
  ``FULLSEYE_MALECNS_DIR`` に feather 2 本のあるディレクトリを指すと、soma を持つ体のうちシナプス総数の上位
  3,000 体の部分グラフを作って ``FULLSEYE_DATA_DIR``(既定 ``~/.cache/fullseye``)にキャッシュする
  (pyarrow が要る)。**repo には集計と図だけ**、生データも部分グラフも入れない。
* どちらも無いときは**合成の代替**: 脳 2 葉 + VNC の形をした点群に、距離が近いほど繋がりやすい有向グラフ
  (局所性を持つ配線)を張り、同じ経路を走らせて ``DATA: synthetic surrogate`` と理由を印字する。

走らせ方: ``py -3.11 examples/poc_malecns_activity_wave.py``(図は ``FULLSEYE_FIGURE_DIR`` があるときだけ)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

SEED = 20260920
N_NODES = 3000
T_STEPS, HOLD, PERIOD, LEAK, RHO, AMP = 36, 3, 18, 0.6, 1.0, 2.0
LAT_THRESH = 0.02                         # 「点いた」= 全体の最大の 2 %(動画の対数輝度で見える弱さと同じ)
UM_PER_VOXEL = 0.008                      # MaleCNS の座標は 8 nm ボクセル
ANNOT = "body-annotations-male-cns-v1.0-minconf-0.5.feather"
WEIGHTS = "connectome-weights-male-cns-v1.0-minconf-0.5.feather"
OPTIC = ("ol_intrinsic", "visual_projection", "visual_centrifugal")
DESC = ("descending_neuron", "ascending_neuron")
VNC = ("vnc_intrinsic", "vnc_motor", "vnc_efferent")
REGIONS = ("optic", "central", "desc/asc", "vnc")


def _cache_dir() -> str:
    base = os.environ.get("FULLSEYE_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "fullseye")
    d = os.path.join(base, "poc_malecns_activity_wave")
    os.makedirs(d, exist_ok=True)
    return d


def _extract_malecns(src: str, npz: str) -> None:
    """生 feather → soma を持つ体のうちシナプス総数上位 N_NODES 体の部分グラフ(2 パス、~30 s)。"""
    import pyarrow.ipc as ipc

    ann = ipc.open_file(os.path.join(src, ANNOT)).read_pandas()
    s = ann[ann["somaLocation"].notna()].reset_index(drop=True)
    body = s["bodyId"].to_numpy().astype(np.int64)
    order = np.argsort(body)
    body = body[order]
    P_all = np.stack(s["somaLocation"].values).astype(np.float32)[order]
    side_all = s["somaSide"].fillna("?").to_numpy().astype(str)[order]
    supc_all = s["superclass"].fillna("?").to_numpy().astype(str)[order]
    m = len(body)

    def look(ids):
        idx = np.searchsorted(body, ids)
        idx[idx >= m] = 0
        return idx, body[idx] == ids

    r = ipc.open_file(os.path.join(src, WEIGHTS))
    tot = np.zeros(m)
    for b in range(r.num_record_batches):
        t = r.get_batch(b)
        ip, okp = look(t.column("body_pre").to_numpy().astype(np.int64))
        iq, okq = look(t.column("body_post").to_numpy().astype(np.int64))
        w = t.column("weight").to_numpy().astype(np.float64)
        ok = okp & okq
        np.add.at(tot, ip[ok], w[ok])
        np.add.at(tot, iq[ok], w[ok])
    sel = np.sort(np.argsort(-tot)[:N_NODES])
    pos = np.full(m, -1, np.int64)
    pos[sel] = np.arange(len(sel))
    W = np.zeros((len(sel), len(sel)))
    for b in range(r.num_record_batches):
        t = r.get_batch(b)
        ip, okp = look(t.column("body_pre").to_numpy().astype(np.int64))
        iq, okq = look(t.column("body_post").to_numpy().astype(np.int64))
        w = t.column("weight").to_numpy().astype(np.float64)
        ok = okp & okq & (pos[ip] >= 0) & (pos[iq] >= 0)
        np.add.at(W, (pos[ip[ok]], pos[iq[ok]]), w[ok])
    np.savez_compressed(npz, W=W.astype(np.float32), P=P_all[sel], side=side_all[sel], superclass=supc_all[sel],
                        P_all=P_all, side_all=side_all)


def load_data() -> tuple[dict, str]:
    """{W, P, side, superclass, P_all} と来歴。"""
    npz = os.path.join(_cache_dir(), "malecns_top%d.npz" % N_NODES)
    src = os.environ.get("FULLSEYE_MALECNS_DIR")
    try:
        if not os.path.exists(npz):
            if not src or not os.path.exists(os.path.join(src, WEIGHTS)):
                raise FileNotFoundError("FULLSEYE_MALECNS_DIR is not set or has no %s" % WEIGHTS)
            _extract_malecns(src, npz)
        z = np.load(npz)
        d = {k: z[k] for k in ("W", "P", "side", "superclass", "P_all")}
        d["W"] = d["W"].astype(np.float64)
        d["P"] = d["P"].astype(np.float64)
        d["P_all"] = d["P_all"].astype(np.float64)
        return d, "MaleCNS v1.0 top-%d somatic neurons by synapse count (cache: %s)" % (N_NODES, npz)
    except Exception as exc:                                       # noqa: BLE001
        return synthetic_brain(), "synthetic surrogate (%s: %s)" % (type(exc).__name__, str(exc)[:80])


def synthetic_brain(n: int = 1200, n_bg: int = 20000) -> dict:
    """脳 2 葉 + VNC の形の点群と、距離が近いほど繋がりやすい有向グラフ(局所性のある配線)。"""
    rng = np.random.default_rng(SEED)

    def cloud(k, center, radii):
        u = rng.standard_normal((k, 3))
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        return center + u * (rng.random((k, 1)) ** (1 / 3)) * radii

    def body(k):
        parts = [cloud(k // 3, (-30.0, 0.0, 0.0), (28.0, 18.0, 22.0)), cloud(k // 3, (30.0, 0.0, 0.0), (28.0, 18.0, 22.0)),
                 cloud(k - 2 * (k // 3), (0.0, 0.0, -90.0), (16.0, 14.0, 55.0))]
        return np.vstack(parts)

    P = body(n)
    side = np.where(P[:, 0] < 0, "L", "R").astype(str)
    supc = np.full(n, "cb_intrinsic", dtype=object)
    supc[(np.abs(P[:, 0]) > 40) & (P[:, 2] > -40)] = "ol_intrinsic"
    supc[P[:, 2] < -40] = "vnc_intrinsic"
    supc[(P[:, 2] < -20) & (P[:, 2] >= -40)] = "descending_neuron"
    D = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2)
    prob = 0.6 * np.exp(-D / 12.0) + 0.002
    W = (rng.random((n, n)) < prob) * rng.integers(1, 20, (n, n)).astype(np.float64)
    np.fill_diagonal(W, 0.0)
    return {"W": W, "P": P, "side": side, "superclass": supc.astype(str), "P_all": body(n_bg)}


def region_of(supc: np.ndarray) -> np.ndarray:
    r = np.full(len(supc), "central", dtype=object)
    r[np.isin(supc, OPTIC)] = "optic"
    r[np.isin(supc, DESC)] = "desc/asc"
    r[np.isin(supc, VNC)] = "vnc"
    return r


def run_wave(W: np.ndarray, stim: np.ndarray) -> np.ndarray:
    """刺激ノードへのパルス列(t = 0..HOLD−1、PERIOD ごと)を reservoir に流した状態列 (T, n)。"""
    R, _ = fs.op_run("reservoir_from_graph", W, rho=RHO)
    U = np.zeros((T_STEPS, 1))
    U[(np.arange(T_STEPS) % PERIOD) < HOLD, 0] = 1.0
    w_in = np.zeros((W.shape[0], 1))
    w_in[stim, 0] = AMP
    X, _ = fs.op_run("reservoir_states", R, U, leak=LEAK, W_in=w_in)
    return np.asarray(X)


def header(width: int, text: str) -> np.ndarray:
    strip = np.full((40, width, 3), 0.06)
    return np.asarray(fs.text_box(strip, text, (6, 4), anchor="lt", font_size=14, color="neutral", box_alpha=0.0))


def main() -> int:
    t0 = time.time()
    data, prov = load_data()
    synthetic = prov.startswith("synthetic")
    print("DATA:", prov)
    W, P, side, supc, P_all = data["W"], data["P"], data["side"], data["superclass"], data["P_all"]
    n = W.shape[0]
    m = int((W > 0).sum())
    region = region_of(supc)
    stim = np.isin(supc, ("ol_intrinsic", "visual_projection")) & (side == "R")
    print("nodes %d edges %d  stimulated (right optic) %d  regions %s" % (
        n, m, int(stim.sum()), {r: int((region == r).sum()) for r in REGIONS}))
    assert stim.sum() >= 10, "刺激するニューロンが足りない(右の視覚系が %d)" % stim.sum()

    Wsh, _ = fs.op_run("graph_degree_preserving_shuffle", W, n_swaps=2 * m, seed=1)
    Wsh = np.asarray(Wsh)
    assert np.array_equal((W > 0).sum(0), (Wsh > 0).sum(0)) and np.array_equal((W > 0).sum(1), (Wsh > 0).sum(1))
    print("shuffle: edges changed %d of %d, degrees preserved" % (int(((W > 0) != (Wsh > 0)).sum() // 2), m))

    Xc, Xs = run_wave(W, stim), run_wave(Wsh, stim)
    unit = UM_PER_VOXEL if not synthetic else 1.0
    src = stim.astype(np.int64)
    spread = {}
    lat = {}
    for label, X in (("connectome", Xc), ("shuffle", Xs)):
        tab, _ = fs.op_run("graph_activity_spread", X, P, src)
        spread[label] = {k: np.asarray(v) for k, v in tab.items()}
        lat[label] = np.asarray(fs.op_run("graph_activation_latency", X, thresh=LAT_THRESH)[0])
    print("%-11s %s" % ("step", "  ".join("%5d" % t for t in (0, 1, 2, 3, 5, 8, 12, 17))))
    for label in ("connectome", "shuffle"):
        d = spread[label]["mean_distance"] * unit
        print("%-11s %s  (mean distance from the stimulus, %s)" % (
            label, "  ".join("%5.0f" % d[t] for t in (0, 1, 2, 3, 5, 8, 12, 17)), "um" if not synthetic else "units"))
    for label in ("connectome", "shuffle"):
        row = []
        for r in REGIONS:
            v = lat[label][(region == r) & (lat[label] >= 0)]
            row.append("%s %s" % (r, ("median %.0f (%d/%d lit)" % (np.median(v), len(v), int((region == r).sum()))) if len(v) else "never"))
        print("latency %-11s %s" % (label, " | ".join(row)))

    # --- 判定(合成でも同じ): 波は順に進み(距離が単調に伸びる)、shuffle は速く散る
    dc, ds = spread["connectome"]["mean_distance"], spread["shuffle"]["mean_distance"]
    assert np.all(np.diff(dc[:6]) >= -1e-9), "コネクトームの活動が刺激から順に離れていない: %s" % dc[:6]
    assert dc[2] < ds[2] and dc[3] < ds[3], "shuffle の方が広がりが遅い(配線の局所性が見えない): %s vs %s" % (dc[:4], ds[:4])
    dist = np.linalg.norm(P - P[stim].mean(0), axis=1)
    far = dist > np.percentile(dist, 75)
    reach = {}
    for label in ("connectome", "shuffle"):
        L = lat[label][far]
        lit = L[(L >= 0) & (L < PERIOD)]
        reach[label] = len(lit) / far.sum()
        print("far quarter of the nodes (%d): lit within the first %d steps %.1f %% (%s), median latency %s" % (
            far.sum(), PERIOD, 100 * reach[label], label, ("%.0f" % np.median(lit)) if len(lit) else "never"))
    assert reach["connectome"] < reach["shuffle"], "遠いノードがコネクトームの方に早く届いている(配線の局所性が見えない)"

    # --- 図(FULLSEYE_FIGURE_DIR があるときだけ)
    COL = {"L": (0.25, 0.75, 1.0), "R": (1.0, 0.6, 0.2)}
    colors = np.array([COL.get(s, (0.85, 0.85, 0.85)) for s in side])
    flip = lambda Q: np.column_stack([Q[:, 0], Q[:, 1], -Q[:, 2]])         # noqa: E731 - 脳を上、VNC を下に
    kw = dict(size=480, aspect=0.75, pitch=15.0, substeps=2, point_px=2, gain=200.0, background=flip(P_all))
    Vc = np.asarray(fs.op_run("points_activity_video", flip(P), Xc, colors=colors, **kw)[0])
    Vs = np.asarray(fs.op_run("points_activity_video", flip(P), Xs, colors=colors, **kw)[0])
    hc, hs = header(Vc.shape[2], "connectome"), header(Vs.shape[2], "degree-preserving shuffle")
    gap = np.full((Vc.shape[1] + hc.shape[0], 8, 3), 0.02)
    frames = [np.hstack([np.vstack([hc, Vc[k]]), gap, np.vstack([hs, Vs[k]])]) for k in range(Vc.shape[0])]
    figs.save_gif("activity_wave_connectome_vs_shuffle", frames, fps=12.0,
                  caption="a pulse into the right optic lobe (orange = right, blue = left somata; grey = all %d somata) "
                          "propagates through the real wiring (left) and through the same degrees rewired at random (right); "
                          "%d neurons, %d edges, %d steps, one brightness scale for every frame" % (len(P_all), n, m, T_STEPS))
    # ★同じ瞬間を 3 方向から(2026-09-20、ユーザー「いくつかの方向から発火状態を見れると良い」): 上段コネクトーム、下段 shuffle
    VIEWS = ((0.0, 0.0), (90.0, 0.0), (0.0, 90.0))
    kw3 = dict(size=300, aspect=0.75, substeps=2, point_px=2, gain=200.0, background=flip(P_all), views=VIEWS)
    V3c = np.asarray(fs.op_run("points_activity_video", flip(P), Xc, colors=colors, **kw3)[0])
    V3s = np.asarray(fs.op_run("points_activity_video", flip(P), Xs, colors=colors, **kw3)[0])
    h3 = header(V3c.shape[2], "dorsal | lateral | along the body axis     (top: connectome, bottom: degree-preserving shuffle)")
    frames3 = [np.vstack([h3, V3c[k], np.full((6, V3c.shape[2], 3), 0.02), V3s[k]]) for k in range(V3c.shape[0])]
    figs.save_gif("activity_wave_three_views", frames3, fps=12.0,
                  caption="the same pulse seen from three fixed directions at once (dorsal, lateral, along the body axis): "
                          "connectome on top, degree-preserving shuffle below; same colours and brightness scale as the rotating view")
    lmax = 6                                 # 色の尺度は 0..6 步(実測の潜時は 0〜3 に集まる。それより遅いものは最も遅い色)
    panels = []
    for label in ("connectome", "shuffle"):
        L = lat[label]
        tcol = np.clip(L / lmax, 0.0, 1.0)[:, None]
        ramp = np.where(tcol < 0.5, (1.0 - 2 * tcol) * np.array([[1.0, 0.95, 0.3]]) + 2 * tcol * np.array([[1.0, 0.45, 0.1]]),
                        (2.0 - 2 * tcol) * np.array([[1.0, 0.45, 0.1]]) + (2 * tcol - 1.0) * np.array([[0.2, 0.35, 1.0]]))
        ramp[L < 0] = (0.3, 0.3, 0.32)
        img = np.asarray(fs.op_run("points_activity_video", flip(P), np.ones((1, n)), colors=ramp, size=480, aspect=0.75,
                                   pitch=15.0, yaw_span=0.0, point_px=3, background=flip(P_all))[0])[0]
        panels.append(np.vstack([header(img.shape[1], "first step lit: " + label), img]))
    figs.save("activation_latency_map_connectome_vs_shuffle", np.hstack([panels[0], gap, panels[1]]),
              "when each neuron first lights up (yellow = step 0, orange = step %d, blue = step %d or later, grey = never within %d steps): "
              "connectome | shuffle" % (lmax // 2, lmax, T_STEPS))
    steps = spread["connectome"]["step"]
    figs.save_plot("activity_spread_mean_distance", [("connectome", steps, dc * unit), ("degree-preserving shuffle", steps, ds * unit)],
                   xlabel="step", ylabel="mean distance from stimulus (%s)" % ("um" if not synthetic else "units"),
                   title="how far the activity has travelled", caption="graph_activity_spread: |x|-weighted mean distance from the stimulated somata")
    assert not figs.errors(), figs.errors()
    print("elapsed %.0fs" % (time.time() - t0))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
