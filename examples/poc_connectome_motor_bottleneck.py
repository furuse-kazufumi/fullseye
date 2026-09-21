# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 動きの量子化 ―― 脳から筋へ、命令の次元はどこで落ちるか(ハエの首と RL の関節を同じ物差しで)

人は手を上げるとき筋肉を 1 本ずつ意識しない。脳の何万ものニューロンの状態が、体を動かす段階では**少数の命令**に
畳まれているはずで、ハエではその畳み込みの場所が配線に見えている: 中枢脳の介在ニューロン 32,164 体が、脳から腹髄へ
降りる**下行ニューロン(DN)1,314 体**という細い首を通り、腹髄の介在 13,161 体を経て**運動ニューロン(MN)708 体**へ
至る(MaleCNS v1.0 の superclass 別の体数、手元で数えた)。

この PoC は「命令の次元がどこで落ちるか」を 1 つの数式 —— 状態の共分散の participation ratio
``PR = (Σλ)² / Σλ``(Gao et al. 2017)—— で読み、**同じ数式を Physical AI(G1 ヒューマノイドの RL 方策が生む関節
軌道、evis の筋活動)に当てる**。

**主張(実データで確かめる)**:
1. 脳の層に乱数の疎な刺激(N = 400 通り)を入れて前向きに通すと、実効次元は 脳 > DN > 腹髄 > MN と単調に落ちる。
2. その落ち方は**層の大きさのせいではない**: 脳の状態から MN と同じ本数(708)の列を抜いても次元は高いまま。
3. 腹髄 → MN の落ち方は**配線の特異性**による: 各受け手の入力重みの多重集合を保って送り手だけを混ぜた対照
   (``graph_block_shuffle``)では MN の次元が実配線の 2 倍以上残る(疎な発火 kWTA のとき)。DN の段では対照と差が
   なく、首の圧縮は fan-in(収束)そのもので起きる。**正直な内訳**: 生の PR は「少数の刺激が MN を強く駆動する」
   裾の重さにも引かれる(実配線の MN の応答ノルムは中央値の 13 倍の刺激がある)ので、各刺激の状態を単位ノルムに
   揃えた**向きだけの次元**も測る —— それでも実配線は対照より 1.5 倍以上低い(kWTA)、線形では 3 倍以上低い。
4. MN に出た命令の次元(生の PR ≈ 2〜4)は、G1 の RL 方策が生む歩行の関節軌道の次元(≈ 2〜4)と同じ桁。ダンス・
   格闘のような多様な動きでは 9〜12 に上がる。桁の比較であって同一性の主張ではない(刺激応答の集合と時系列は
   別の物)。

図:
1. ``funnel``: 層ごとの実効次元(実配線 kWTA / 対照 kWTA / 線形)。``funnel_direction``: 各刺激を単位ノルムに揃えた向きだけの次元。
2. ``activity_flow``(GIF): 1 つの刺激が脳 → DN → 腹髄 → MN と soma の位置の上を流れる様子。
3. ``command_space``: MN の状態の主成分平面(実配線 vs 対照)。
4. ``physical_ai``: 同じ数式を当てた G1 の関節軌道と evis の筋活動の次元、MN の線と並べて。
5. ``numbers``: 数字の表。

データ: ``FULLSEYE_MALECNS_DIR``(feather 2 本)があれば MaleCNS v1.0(Janelia、CC BY 4.0、生データと部分グラフは
commit しない、cache は ``~/.cache/fullseye/poc_connectome_motor_bottleneck/``)。無ければ合成の層状配線(モジュール
構造つき)で同じ手順を回す。Physical AI 側は ``FULLSEYE_G1_QPOS_DIR``(``*_qpos.npy``)と ``FULLSEYE_EVIS_CORPUS``
(``hillco_corpus.npz``)があれば実データ、無ければ合成の歩容(正弦の 2 位相 + 雑音)。

走らせ方: ``py -3.11 examples/poc_connectome_motor_bottleneck.py``(図は ``out/figures/poc_connectome_motor_bottleneck/``)。
"""
from __future__ import annotations

import glob
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
POC = "poc_connectome_motor_bottleneck"
CACHE = os.path.join(os.environ.get("FULLSEYE_DATA_DIR", os.path.join(os.path.expanduser("~"), ".cache", "fullseye")), POC)
ANNOT = "body-annotations-male-cns-v1.0-minconf-0.5.feather"
WEIGHTS = "connectome-weights-male-cns-v1.0-minconf-0.5.feather"
LAYERS = ("brain", "DN", "VNC", "MN")
K_BRAIN, K_VNC = 1000, 1000            # 4 層合計 4,022 ≤ conngraph.MAX_NODES
N_STIM = 400
ACTIVE = 0.10


# --------------------------------------------------------------------------- #
# データ                                                                        #
# --------------------------------------------------------------------------- #
def _extract_malecns(src: str, npz: str) -> None:
    """生 feather → 脳(DN への出力が多い cb_intrinsic 上位 K)→ DN 全部 → 腹髄介在(DN から受け MN へ出す上位 K)→ MN 全部。"""
    import pyarrow.ipc as ipc
    ann = ipc.open_file(os.path.join(src, ANNOT)).read_pandas()
    body = ann["bodyId"].to_numpy().astype(np.int64)
    order = np.argsort(body)
    body = body[order]
    supc = ann["superclass"].fillna("?").to_numpy().astype(str)[order]
    loc = ann["somaLocation"].values[order]
    m = len(body)
    lay = np.full(m, -1, np.int8)
    for k, name in enumerate(("cb_intrinsic", "descending_neuron", "vnc_intrinsic", "vnc_motor")):
        lay[supc == name] = k

    def look(ids):
        idx = np.searchsorted(body, ids)
        idx[idx >= m] = 0
        return idx, body[idx] == ids

    r = ipc.open_file(os.path.join(src, WEIGHTS))
    w_b2d, w_v_from_d, w_v2m = np.zeros(m), np.zeros(m), np.zeros(m)
    for b in range(r.num_record_batches):
        t = r.get_batch(b)
        ip, okp = look(t.column("body_pre").to_numpy().astype(np.int64))
        iq, okq = look(t.column("body_post").to_numpy().astype(np.int64))
        w = t.column("weight").to_numpy().astype(np.float64)
        ok = okp & okq
        ip, iq, w = ip[ok], iq[ok], w[ok]
        lp, lq = lay[ip], lay[iq]
        s = (lp == 0) & (lq == 1)
        np.add.at(w_b2d, ip[s], w[s])
        s = (lp == 1) & (lq == 2)
        np.add.at(w_v_from_d, iq[s], w[s])
        s = (lp == 2) & (lq == 3)
        np.add.at(w_v2m, ip[s], w[s])
    brain = np.argsort(-w_b2d)[:K_BRAIN]
    brain = brain[w_b2d[brain] > 0]
    score = np.sqrt(w_v_from_d * w_v2m)
    vnc = np.argsort(-score)[:K_VNC]
    vnc = vnc[score[vnc] > 0]
    dn, mn = np.nonzero(lay == 1)[0], np.nonzero(lay == 3)[0]
    sel = np.concatenate([brain, dn, vnc, mn])
    layer = np.concatenate([np.zeros(len(brain), int), np.ones(len(dn), int), np.full(len(vnc), 2), np.full(len(mn), 3)])
    pos = np.full(m, -1, np.int64)
    pos[sel] = np.arange(len(sel))
    W = np.zeros((len(sel), len(sel)), np.float32)
    for b in range(r.num_record_batches):
        t = r.get_batch(b)
        ip, okp = look(t.column("body_pre").to_numpy().astype(np.int64))
        iq, okq = look(t.column("body_post").to_numpy().astype(np.int64))
        w = t.column("weight").to_numpy().astype(np.float64)
        ok = okp & okq & (pos[ip] >= 0) & (pos[iq] >= 0)
        np.add.at(W, (pos[ip[ok]], pos[iq[ok]]), w[ok])
    P = np.stack([np.asarray(x, float) if x is not None else np.full(3, np.nan) for x in loc[sel]]).astype(np.float32)
    counts = {name: int((supc == name).sum()) for name in ("cb_intrinsic", "descending_neuron", "vnc_intrinsic", "vnc_motor")}
    os.makedirs(os.path.dirname(npz), exist_ok=True)
    np.savez_compressed(npz, W=W, layer=layer, P=P, counts=np.array([counts[k] for k in counts], np.int64))


def load_layers():
    """{W, layer, P, counts, src}。実データ(cache)か合成。"""
    src = os.environ.get("FULLSEYE_MALECNS_DIR")
    npz = os.path.join(CACHE, "layers_k%d_%d.npz" % (K_BRAIN, K_VNC))
    if not REDUCED and (os.path.isfile(npz) or (src and os.path.isfile(os.path.join(src, WEIGHTS)))):
        if not os.path.isfile(npz):
            _extract_malecns(src, npz)
        z = np.load(npz)
        return {"W": z["W"].astype(np.float64), "layer": z["layer"], "P": z["P"], "counts": z["counts"].tolist(),
                "src": "MaleCNS v1.0 (Janelia, CC BY 4.0), subgraph brain %d / DN %d / VNC %d / MN %d"
                       % tuple(int((z["layer"] == a).sum()) for a in range(4))}
    return synthetic_layers()


def synthetic_layers(sizes=(400, 120, 300, 60), seed=0):
    """合成の層状配線: 腹髄の介在は 6 つのモジュール、MN の各プールは 1 モジュールから受ける(構造のある配線)。"""
    rng = np.random.default_rng(seed)
    layer = np.repeat(np.arange(4), sizes)
    n = len(layer)
    W = np.zeros((n, n))
    idx = [np.nonzero(layer == a)[0] for a in range(4)]
    W[np.ix_(idx[0], idx[1])] = rng.random((sizes[0], sizes[1])) * (rng.random((sizes[0], sizes[1])) < 0.05)
    module_v = rng.integers(0, 6, sizes[2])
    module_m = np.repeat(np.arange(6), int(np.ceil(sizes[3] / 6)))[:sizes[3]]
    for i, d in enumerate(idx[1]):
        mods = rng.choice(6, 2, replace=False)
        tgt = idx[2][np.isin(module_v, mods)]
        W[d, rng.choice(tgt, max(1, len(tgt) // 4), replace=False)] = rng.random(max(1, len(tgt) // 4))
    for j, mm in enumerate(idx[3]):
        srcs = idx[2][module_v == module_m[j]]
        W[rng.choice(srcs, max(1, len(srcs) // 2), replace=False), mm] = rng.random(max(1, len(srcs) // 2))
    P = rng.random((n, 3)) * 100.0
    P[:, 2] -= layer * 40.0                                                # 層ごとに奥行きをずらす
    return {"W": W, "layer": layer, "P": P.astype(np.float32), "counts": list(sizes),
            "src": "synthetic layered wiring (6 VNC modules, one module per MN pool)"}


def unit_rows(X: np.ndarray, layer: np.ndarray) -> np.ndarray:
    """層ごとに各刺激(行)の状態を単位ノルムに(大きさを捨てて向きだけを残す)。"""
    Y = X.copy()
    for a in range(int(layer.max()) + 1):
        cols = layer == a
        blk = Y[:, cols]
        Y[:, cols] = blk / np.maximum(np.linalg.norm(blk, axis=1, keepdims=True), 1e-12)
    return Y


def stimuli(n0: int, N: int, frac: float = 0.05, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    U = np.zeros((N, n0))
    k = max(1, int(frac * n0))
    for i in range(N):
        U[i, rng.choice(n0, k, replace=False)] = rng.random(k)
    return U


def physical_ai_series():
    """(名前, 系列 (T, d)) の一覧。G1 の関節軌道と evis の筋活動があれば実データ、無ければ合成の歩容。"""
    out = []
    d = os.environ.get("FULLSEYE_G1_QPOS_DIR")
    if d and not REDUCED:
        for f in sorted(glob.glob(os.path.join(d, "g1_*_qpos.npy"))):
            q = np.load(f).astype(np.float64)
            q = q[:, 7:] if q.shape[1] == 36 else q                     # 先頭 7 列 = 基底の位置と四元数
            if q.shape[0] >= 100:
                out.append(("G1 " + os.path.basename(f).replace("_qpos.npy", ""), q))
    ev = os.environ.get("FULLSEYE_EVIS_CORPUS")
    if ev and not REDUCED and os.path.isfile(ev):
        z = np.load(ev, allow_pickle=True)
        for name, a in list(zip(z["names"], z["acts"]))[:20]:
            out.append(("evis muscles " + str(name), np.asarray(a, float).T))
    if not out:
        rng = np.random.default_rng(0)
        t = np.arange(600) / 30.0
        ph = rng.random(29) * 2 * np.pi
        gait = np.stack([np.sin(2 * np.pi * 1.2 * t + p) * (0.3 + 0.7 * rng.random()) for p in ph], axis=1)
        gait[:, ::2] *= np.sin(2 * np.pi * 0.6 * t)[:, None] ** 2 * 0.5 + 0.75
        out.append(("synthetic gait (29 joints, 2 phases)", gait + 0.02 * rng.standard_normal(gait.shape)))
    return out


# --------------------------------------------------------------------------- #
# 本体                                                                          #
# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.time()
    L = fs.ledger
    rows = []
    data = load_layers()
    W, layer, P = data["W"], data["layer"], data["P"]
    n = [int((layer == a).sum()) for a in range(4)]
    print("DATA: %s" % data["src"])
    print("superclass counts (whole dataset): brain-intrinsic %d / DN %d / VNC-intrinsic %d / MN %d" % tuple(data["counts"]))
    N = 120 if REDUCED else N_STIM
    U = stimuli(n[0], N)
    Xk = L.graph_layer_propagate(W, layer, U, activation="kwta", active_frac=ACTIVE)
    Xl = L.graph_layer_propagate(W, layer, U, activation="linear")
    tk = L.states_layer_dimension(Xk, layer)
    tl = L.states_layer_dimension(Xl, layer)
    Xshuf = [L.graph_layer_propagate(L.graph_block_shuffle(W, layer, seed=s), layer, U, activation="kwta", active_frac=ACTIVE)
             for s in range(3)]
    shuf = [L.states_layer_dimension(Xs_, layer) for Xs_ in Xshuf]
    pr_shuf = np.mean([t["participation_ratio"] for t in shuf], axis=0)
    prk, prl = tk["participation_ratio"], tl["participation_ratio"]
    # 向きだけの次元(各刺激の状態を単位ノルムに)
    prk_u = L.states_layer_dimension(unit_rows(Xk, layer), layer)["participation_ratio"]
    prl_u = L.states_layer_dimension(unit_rows(Xl, layer), layer)["participation_ratio"]
    Xlshuf = L.graph_layer_propagate(L.graph_block_shuffle(W, layer, seed=0), layer, U, activation="linear")
    pr_shuf_u = np.mean([L.states_layer_dimension(unit_rows(Xs_, layer), layer)["participation_ratio"] for Xs_ in Xshuf], axis=0)
    prl_shuf = L.states_layer_dimension(Xlshuf, layer)["participation_ratio"]
    prl_shuf_u = L.states_layer_dimension(unit_rows(Xlshuf, layer), layer)["participation_ratio"]
    mn_norm = np.linalg.norm(Xk[:, layer == 3], axis=1)
    print("effective dimension (PR, N=%d stimuli, kWTA %.0f%%): " % (N, 100 * ACTIVE) +
          " > ".join("%s(n=%d) %.1f" % (LAYERS[a], n[a], prk[a]) for a in range(4)))
    print("  linear:                    " + " > ".join("%s %.1f" % (LAYERS[a], prl[a]) for a in range(4)))
    print("  block-shuffled control:    " + " > ".join("%s %.1f" % (LAYERS[a], pr_shuf[a]) for a in range(4)))
    print("  direction only (unit-norm rows), kWTA: real " + " > ".join("%s %.1f" % (LAYERS[a], prk_u[a]) for a in range(4))
          + "  | shuffled " + " > ".join("%s %.1f" % (LAYERS[a], pr_shuf_u[a]) for a in range(4)))
    print("  direction only, linear:               real " + " > ".join("%s %.1f" % (LAYERS[a], prl_u[a]) for a in range(4))
          + "  | shuffled " + " > ".join("%s %.1f" % (LAYERS[a], prl_shuf_u[a]) for a in range(4)))
    print("  MN response norm across stimuli (real, kWTA): median %.1f, max %.1f (%.1f x median) -> the raw PR is pulled by a heavy tail"
          % (np.median(mn_norm), mn_norm.max(), mn_norm.max() / max(np.median(mn_norm), 1e-12)))
    rng = np.random.default_rng(0)
    brain_sub = L.states_participation_ratio(Xk[:, layer == 0][:, rng.choice(n[0], n[3], replace=False)])
    print("  size-matched control: brain states with %d columns: PR %.1f (MN itself %.1f)" % (n[3], brain_sub, prk[3]))
    real = data["src"].startswith("MaleCNS")
    assert prk[0] > prk[1] > prk[2] > prk[3] > 0, prk                     # 1. 単調に落ちる(合成でも)
    if real:                                                              # 2〜4 は実配線の性質。合成では検証しない
        assert brain_sub > 3.0 * prk[1], (brain_sub, prk[1])              # 2. 層の大きさのせいではない
        assert pr_shuf[3] > 2.0 * prk[3], (pr_shuf[3], prk[3])            # 3. 腹髄 → MN は配線の特異性
        assert abs(pr_shuf[1] - prk[1]) < 0.25 * prk[1], (pr_shuf[1], prk[1])  #  首の段は対照と同じ(fan-in の圧縮)
        assert prk_u[0] > prk_u[1] > prk_u[2] > prk_u[3] > 0, prk_u           #    向きだけでも単調に落ちる
        assert pr_shuf_u[3] > 1.5 * prk_u[3], (pr_shuf_u[3], prk_u[3])        #    向きだけでも配線の特異性(kWTA)
        assert prl_shuf_u[3] > 3.0 * prl_u[3], (prl_shuf_u[3], prl_u[3])      #    線形ではさらに大きい
    else:
        print("  (synthetic wiring: claims 2-4 are properties of the real wiring and are not asserted here)")
    for a in range(4):
        rows.append(("PR %s (n=%d): real kWTA / shuffled / linear" % (LAYERS[a], n[a]),
                     "%.1f / %.1f / %.1f" % (prk[a], pr_shuf[a], prl[a]), "-"))
    rows.append(("size-matched: brain with %d columns" % n[3], "%.1f" % brain_sub, "> 3 x PR(DN)"))
    rows.append(("direction-only PR MN: real kWTA / shuffled kWTA / real linear / shuffled linear",
                 "%.1f / %.1f / %.1f / %.1f" % (prk_u[3], pr_shuf_u[3], prl_u[3], prl_shuf_u[3]), "shuffled > 1.5x (kWTA), > 3x (linear)"))
    rows.append(("MN response norm across stimuli: median / max", "%.1f / %.1f" % (np.median(mn_norm), mn_norm.max()), "heavy tail"))

    series = physical_ai_series()
    pr_ai = [(name, L.states_participation_ratio(q), q.shape) for name, q in series]
    for name, pr, shp in pr_ai:
        print("Physical AI  %-40s T=%5d d=%3d  PR %.2f" % (name, shp[0], shp[1], pr))
    walks = [pr for name, pr, _ in pr_ai if "walk" in name or "run" in name or "gait" in name]
    if walks:
        print("  locomotion PR median %.2f  vs  MN command PR %.1f" % (np.median(walks), prk[3]))
        rows.append(("locomotion (G1 walk / run) PR median", "%.2f" % np.median(walks), "MN %.1f" % prk[3]))
    for name, pr, _ in pr_ai[:12]:
        rows.append(("PR " + name, "%.2f" % pr, "-"))

    if figs.enabled():
        x = np.arange(4, dtype=float)
        lg = lambda v: np.log10(np.maximum(v, 1e-3))  # noqa: E731 - 3 桁落ちるので対数で
        figs.save_plot("funnel", [("real wiring, kWTA %.0f%%" % (100 * ACTIVE), x, lg(prk)), ("block-shuffled control, kWTA", x, lg(pr_shuf)),
                                  ("real wiring, linear", x, lg(prl))],
                       xlabel="layer: 0 brain (n=%d), 1 DN (%d), 2 VNC (%d), 3 MN (%d)" % tuple(n), ylabel="log10 participation ratio",
                       title="where the command dimension collapses",
                       caption="effective dimension of the states each layer takes under %d random sparse stimuli of the brain layer: real wiring vs a control that keeps every receiver's input weights but shuffles who sends them; the neck (DN) compresses by convergence alone, the VNC -> MN stage compresses by the specific wiring" % N)
        figs.save_plot("funnel_direction", [("real wiring, kWTA (unit-norm)", x, lg(prk_u)), ("shuffled, kWTA (unit-norm)", x, lg(pr_shuf_u)),
                                            ("real wiring, linear (unit-norm)", x, lg(prl_u)), ("shuffled, linear (unit-norm)", x, lg(prl_shuf_u))],
                       xlabel="layer: 0 brain, 1 DN, 2 VNC, 3 MN", ylabel="log10 participation ratio",
                       title="direction only: each stimulus response scaled to unit norm",
                       caption="the same funnel after every stimulus response is scaled to unit norm (magnitude removed, direction kept): the real wiring still leaves fewer MN directions than the shuffled control, so the collapse is not only a few strong responses")
        # 活動の流れ: 1 つの刺激を層ごとに点灯(8 コマ、前の層は薄く残す)
        ok = np.isfinite(P).all(axis=1)
        Pq = np.where(ok[:, None], P, np.nanmean(P[ok], axis=0))
        if real:
            Pq = np.column_stack([Pq[:, 0], Pq[:, 1], -Pq[:, 2]])          # MaleCNS の z は下向き: 脳を上、腹髄を下に
        act = np.abs(Xk[0]) / max(float(np.abs(Xk[0]).max()), 1e-12)
        frames = []
        for step in range(8):
            a_now = step // 2
            f = np.zeros(len(layer))
            for a in range(a_now + 1):
                f[layer == a] = act[layer == a] * (1.0 if a == a_now else 0.35)
            frames.append(f)
        X_flow = np.stack(frames)
        cols = np.array([[0.55, 0.65, 1.0], [1.0, 0.85, 0.3], [0.4, 0.9, 0.5], [1.0, 0.45, 0.35]])[layer]
        vid = L.points_activity_video(Pq, X_flow, colors=cols, size=240 if REDUCED else 360)
        figs.save_gif("activity_flow", vid, fps=2.0,
                      caption="one stimulus flowing brain (blue) -> DN (yellow) -> VNC (green) -> MN (red) over the soma positions; %s" % data["src"])
        # MN の命令空間
        Xs = L.graph_layer_propagate(L.graph_block_shuffle(W, layer, seed=0), layer, U, activation="kwta", active_frac=ACTIVE)
        panels, caps = [], []
        for label, Xm in (("real wiring", Xk[:, layer == 3]), ("block-shuffled", Xs[:, layer == 3])):
            Xc = Xm - Xm.mean(axis=0)
            _u, s, vt = np.linalg.svd(Xc, full_matrices=False)
            pc = Xc @ vt[:2].T
            panels.append(("PR %.1f" % L.states_participation_ratio(Xm), pc[:, 0], pc[:, 1]))
            caps.append(label)
        figs.save_plot("command_space", panels, xlabel="PC 1", ylabel="PC 2", title="MN command space (real vs shuffled)",
                       kinds=["scatter", "scatter"],
                       caption="the %d stimuli projected on the first two principal components of the MN states: real wiring folds them onto a few directions, the shuffled control spreads them" % N)
        names = [nm for nm, _pr, _s in pr_ai][:14]
        vals = np.array([pr for _nm, pr, _s in pr_ai][:14])
        figs.save_plot("physical_ai", [("Physical AI sequences", np.arange(len(vals), dtype=float), vals),
                                       ("fly MN command PR", np.arange(len(vals), dtype=float), np.full(len(vals), prk[3]))],
                       xlabel="sequence index (names in the numbers table)", size=(720, 400),
                       ylabel="participation ratio", title="the same formula on Physical AI",
                       caption="participation ratio of joint-angle trajectories (G1 humanoid, RL policies and mocap retargets) and of muscle activations (evis), next to the fly's MN command dimension under random brain input")
        figs.save_table("numbers", ["quantity", "value", "bar"], rows, title="motor bottleneck PoC numbers",
                        caption="every number, with the bar it had to clear")
        assert not figs.errors(), figs.errors()
    print("elapsed %.0fs" % (time.time() - t0))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
