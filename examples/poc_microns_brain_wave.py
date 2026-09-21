# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: MICrONS の脳の波 ―― 1 mm³ の視覚野で、配線は実測の応答をどこまで説明するか

MICrONS(マウス V1 + 高次視覚野の約 1 mm³)は、**同じニューロンについて電子顕微鏡の配線と 2 光子の活動の両方**を持つ
唯一級のデータ。Ding ら 2025(Nature、doi:10.1038/s41586-025-08840-3)の公開表には 12,894 体の soma 位置・皮質層・
視覚野(V1 / RL / AL / LM)・自然動画への試行平均応答(120 コマ)と、校正済みの軸索 148 本から出る 1.69 M 対
(Connected 8,128 / ADP = 軸索と樹状突起が近接するのに結合していない 287 k / Same region 1.40 M)がある。

この PoC は、その実測の応答を**1 mm³ の脳の波としてそのまま見せ**(``points_activity_video``)、配線がその波をどこまで
説明するかを 3 つの物差しで測る:

**主張(実データで確かめる)**:
1. like-to-like の再現: 結合している対の信号相関は近接して結合していない対より高く、それは同じ領域の対より高い
   (0.071 > 0.045 > 0.025)。pre ごとに相手をシャッフルする置換帰無(ADP を候補に)では差が SD の 10 倍を超える。
2. 配線は近接以上を足す: 各軸索(pre)の応答と「相手の応答の平均」の相関(同じ 120 コマ上の類似度で、holdout の予測
   ではない)は、結合相手で 0.24、同数の近接相手(ADP)で 0.18、同数の同領域相手で 0.12。pre ごとの対で 7 割が結合相手
   のほうを勝たせる。自分が相手に混ざる行は除く。
3. 配線の波: 148 本の pre の実測応答を conngraph の reservoir(4,096 体の部分グラフ、軸索 → 軸索の辺は落とす)に流し、
   **1 コマ遅れ**の post の状態と実測応答の相関は 0.09、次数保存シャッフル 20 本の対照はどれも下(平均 0.05)。利得を
   0.3 / 3 倍にしても順序は同じ。**正直な内訳**: 絶対値は小さい —— 校正済みの軸索 148 本から post 1 体あたり 2 本弱
   しか入力がない一段のグラフで、波の広がり(刺激からの平均距離 ≈ 310 µm)は対照と同じ。空間の局所性は「候補の集合
   (ADP)」に既に入っていて、「誰を選ぶか」には入っていない。

図:
1. ``brain_wave``(GIF): 12,894 体の soma に実測応答(各細胞の 95 パーセンタイルで正規化)を載せ、1 mm³ を回しながら
   120 コマを流す。色 = 視覚野(V1 青 / RL 黄 / AL 緑 / LM 赤)。
2. ``like_to_like``: 同領域の対の信号相関を soma 間距離で束ねた曲線と、Connected / ADP の平均。
3. ``wiring_vs_proximity``: pre ごとの「結合相手で予測」vs「近接相手で予測」の散布(対角より上 = 配線が勝つ)。
4. ``wave_on_wiring``(GIF): 部分グラフの reservoir 状態(pre 黄、post は視覚野の色)を全 soma(灰)の上に載せて回す。
5. ``numbers``: 数字の表。

データ: ``FULLSEYE_MICRONS_DIR``(既定 ``~/.cache/fullseye/microns``)に ``node_data_v1.pkl`` / ``edge_data_v1.pkl``
(bossdb-open-data の ``iarpa_microns/minnie/functional_data/functional_connectomics/node_and_edge_properties/v1/``、
引用: Ding et al. 2025)があれば実データ(pandas で 1 回だけ読んで ``~/.cache/fullseye/poc_microns_brain_wave/`` に
npz 化、生データも部分グラフも commit しない)。無ければ合成の皮質(潜在 8 本の共有信号 + 近接候補からの like-to-like
結合)で同じ手順を回す。

走らせ方: ``py -3.11 examples/poc_microns_brain_wave.py``(図は ``out/figures/poc_microns_brain_wave/``)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
POC = "poc_microns_brain_wave"
CACHE = os.path.join(os.environ.get("FULLSEYE_DATA_DIR", os.path.join(os.path.expanduser("~"), ".cache", "fullseye")), POC)
SRC = os.environ.get("FULLSEYE_MICRONS_DIR", os.path.join(os.path.expanduser("~"), ".cache", "fullseye", "microns"))
AREAS = ("V1", "RL", "AL", "LM")
POPS = ("Connected", "ADP", "Same region")
AREA_COLOURS = np.array([[0.55, 0.65, 1.0], [1.0, 0.85, 0.3], [0.4, 0.9, 0.5], [1.0, 0.45, 0.35]])
MAX_NODES = 4096
N_PERM = 50 if REDUCED else 200


# --------------------------------------------------------------------------- #
# データ                                                                        #
# --------------------------------------------------------------------------- #
def _extract_microns(src: str, npz: str) -> None:
    """公開表(pandas の pickle)→ 配列。pandas 2 以降には無い ``pandas.core.indexes.numeric`` を空の互換モジュールで埋める。"""
    import pickle
    import types

    import pandas as pd

    if "pandas.core.indexes.numeric" not in sys.modules:
        shim = types.ModuleType("pandas.core.indexes.numeric")

        class _Legacy(pd.Index):
            def __new__(cls, *a, **k):
                return pd.Index(*a, **k)

        for nm in ("Int64Index", "UInt64Index", "Float64Index", "NumericIndex", "IntegerIndex"):
            setattr(shim, nm, _Legacy)
        sys.modules["pandas.core.indexes.numeric"] = shim
    with open(os.path.join(src, "node_data_v1.pkl"), "rb") as f:
        nd = pickle.load(f)
    with open(os.path.join(src, "edge_data_v1.pkl"), "rb") as f:
        ed = pickle.load(f)
    nid = nd["nucleus_id"].to_numpy().astype(np.int64)
    pos = {int(k): i for i, k in enumerate(nid)}
    R = np.stack([np.asarray(x, np.float32) for x in nd["in_vivo_mean_resp"]])
    P = (nd[["nucleus_x", "nucleus_y", "nucleus_z"]].to_numpy(np.float64) / 1e3).astype(np.float32)   # nm → µm
    area = np.array([AREAS.index(a) if a in AREAS else 0 for a in nd["brain_area"].astype(str)], np.int8)
    layer = nd["layer"].astype(str).to_numpy()
    pre = ed["pre_nucleus_id"].map(pos).to_numpy().astype(np.int32)
    post = ed["post_nucleus_id"].map(pos).to_numpy().astype(np.int32)
    popn = ed["population"].astype(str).to_numpy()
    pop = np.full(len(popn), -1, np.int8)
    for k, name in enumerate(POPS):
        pop[popn == name] = k
    ok = pop >= 0
    os.makedirs(os.path.dirname(npz), exist_ok=True)
    np.savez_compressed(npz, R=R, P=P, area=area, layer=layer, pre=pre[ok], post=post[ok], pop=pop[ok],
                        sc=ed["in_vivo_sig_corr"].to_numpy(np.float32)[ok], nsyn=ed["n_synapses"].to_numpy(np.float32)[ok])


def load_data() -> dict:
    """{R, P, area, pre, post, pop, sc, nsyn, src}。実データ(cache)か合成。"""
    npz = os.path.join(CACHE, "microns_v1.npz")
    have_src = os.path.isfile(os.path.join(SRC, "node_data_v1.pkl")) and os.path.isfile(os.path.join(SRC, "edge_data_v1.pkl"))
    if not REDUCED and (os.path.isfile(npz) or have_src):
        if not os.path.isfile(npz):
            _extract_microns(SRC, npz)
        z = np.load(npz)
        d = {k: z[k] for k in ("R", "P", "area", "pre", "post", "pop", "sc", "nsyn")}
        d["R"] = d["R"].astype(np.float64)
        d["src"] = ("MICrONS functional connectomics v1 (Ding et al. 2025, Nature): %d neurons, %d Connected / %d ADP / %d Same-region pairs"
                    % (len(d["R"]), int((d["pop"] == 0).sum()), int((d["pop"] == 1).sum()), int((d["pop"] == 2).sum())))
        return d
    return synthetic_cortex()


def synthetic_cortex(n: int = 1500, T: int = 120, n_pre: int = 30, k_latent: int = 8, seed: int = 0) -> dict:
    """合成の皮質: 潜在信号 8 本の重みつき和 + 雑音が応答、近接候補(150 µm 以内)から調律の似た相手に結合(like-to-like)。"""
    rng = np.random.default_rng(seed)
    P = rng.random((n, 3)) * np.array([1000.0, 600.0, 500.0])
    area = (P[:, 0] > 650.0).astype(np.int8)                                   # 左 = V1、右 = RL
    latent = rng.standard_normal((k_latent, T))
    tune = rng.standard_normal((n, k_latent))
    tune /= np.linalg.norm(tune, axis=1, keepdims=True)
    R = np.maximum(tune @ latent + 0.8 * rng.standard_normal((n, T)), 0.0) + 0.05
    sim = tune @ tune.T
    pres = rng.choice(n, n_pre, replace=False)
    pre, post, pop = [], [], []
    for p in pres:
        d = np.linalg.norm(P - P[p], axis=1)
        near = np.nonzero((d < 150.0) & (d > 0))[0]
        prob = np.exp(3.0 * sim[p, near])
        prob /= prob.sum()
        k = min(len(near) // 5, 40)
        conn = rng.choice(near, k, replace=False, p=prob)
        adp = np.setdiff1d(near, conn)
        far = rng.choice(np.setdiff1d(np.nonzero(d >= 150.0)[0], [p]), 300, replace=False)
        for grp, code in ((conn, 0), (adp, 1), (far, 2)):
            pre.extend([p] * len(grp))
            post.extend(grp.tolist())
            pop.extend([code] * len(grp))
    pre, post, pop = np.array(pre, np.int32), np.array(post, np.int32), np.array(pop, np.int8)
    Rz = _zscore_rows(R)
    sc = (Rz[pre] * Rz[post]).mean(axis=1).astype(np.float32)
    nsyn = (1.0 + (rng.random(len(pre)) < 0.1)).astype(np.float32)
    return {"R": R, "P": P.astype(np.float32), "area": area, "pre": pre, "post": post, "pop": pop, "sc": sc, "nsyn": nsyn,
            "src": "synthetic cortex (%d neurons, %d axons, like-to-like wiring among neighbours within 150 um)" % (n, n_pre)}


def _zscore_rows(R: np.ndarray) -> np.ndarray:
    return (R - R.mean(axis=1, keepdims=True)) / np.maximum(R.std(axis=1, keepdims=True), 1e-9)


def order_text(names, values) -> str:
    """値の順に名前を並べ、隣り合う大小を確かめて '>' / '=' で繋ぐ(確かめる前に不等号を印字しない)。"""
    order = np.argsort(-np.asarray(values, float))
    out = names[order[0]]
    for a, b in zip(order[:-1], order[1:]):
        out += (" > " if values[a] > values[b] else " = ") + names[b]
    return out


def _highlights(A: np.ndarray, lo: float = 75.0, hi: float = 99.0) -> np.ndarray:
    """(T, n) の各列(細胞)を自分の lo → hi パーセンタイルで 0 → 1 に(それ未満は消灯)。

    中央値を 0 にすると定義上いつも半分が点いて波に見えないので、**各細胞が自分の上位 4 分の 1 にいる瞬間だけ**点ける。
    """
    a = np.percentile(A, lo, axis=0)
    b = np.percentile(A, hi, axis=0)
    return np.clip((A - a) / np.maximum(b - a, 1e-9), 0.0, 1.0)


def _corr(a: np.ndarray, b: np.ndarray) -> float | None:
    """ピアソン相関。どちらかが定数なら None(corrcoef の NaN を黙って平均に混ぜない)。"""
    if a.std() < 1e-9 or b.std() < 1e-9:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _per_pre(pre: np.ndarray):
    """pre ごとの辺 index の一覧(1 回だけ並べ替える)。"""
    order = np.argsort(pre, kind="stable")
    pres = np.unique(pre)
    lo = np.searchsorted(pre[order], pres, side="left")
    hi = np.searchsorted(pre[order], pres, side="right")
    return pres, [order[a:b] for a, b in zip(lo, hi)]


# --------------------------------------------------------------------------- #
# 3 つの物差し                                                                  #
# --------------------------------------------------------------------------- #
def like_to_like(sc: np.ndarray, pre: np.ndarray, pop: np.ndarray, n_perm: int, seed: int = 0):
    """信号相関の平均(Connected / ADP / Same)と、pre ごとに Connected と ADP の札を混ぜる置換帰無(差の分布)。"""
    means = np.array([float(sc[pop == k].mean()) for k in range(3)])
    obs = means[0] - means[1]
    pres, groups = _per_pre(pre)
    cand = [ix[pop[ix] <= 1] for ix in groups]
    kcon = [int((pop[ix] == 0).sum()) for ix in cand]
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    for it in range(n_perm):
        sc_c, sc_a, n_c, n_a = 0.0, 0.0, 0, 0
        for ix, k in zip(cand, kcon):
            v = rng.permutation(sc[ix])
            sc_c += v[:k].sum()
            sc_a += v[k:].sum()
            n_c += k
            n_a += len(v) - k
        null[it] = sc_c / max(n_c, 1) - sc_a / max(n_a, 1)
    return means, obs, null


def partner_prediction(Rz: np.ndarray, pre: np.ndarray, post: np.ndarray, pop: np.ndarray, nsyn: np.ndarray,
                       n_draw: int = 20, seed: int = 0):
    """pre ごとの「自分の応答と相手の応答の平均との相関」: 結合相手 / シナプス数で重みづけ / 同数の ADP / 同数の Same。

    学習も holdout も無い同じ 120 コマ上の**類似度**であって、予測の検証ではない(印字もそう呼ぶ)。相手に自分が
    混ざる行(pre == post)は除く。自分か相手平均が定数なら、その pre は数えない。
    """
    rng = np.random.default_rng(seed)
    pres, groups = _per_pre(pre)
    rows = []
    for p, ix in zip(pres, groups):
        ix = ix[post[ix] != p]                                                 # 自己は相手に含めない(リーク防止)
        cp, ap, sp = (post[ix[pop[ix] == k]] for k in range(3))
        k = len(cp)
        if k < 3 or len(ap) < k or len(sp) < k:
            continue
        w = nsyn[ix[pop[ix] == 0]]
        z = Rz[p]
        rc = _corr(z, Rz[cp].mean(axis=0))
        rw = _corr(z, (Rz[cp] * w[:, None]).sum(axis=0) / w.sum())
        ra = [_corr(z, Rz[rng.choice(ap, k, replace=False)].mean(axis=0)) for _ in range(n_draw)]
        rs = [_corr(z, Rz[rng.choice(sp, k, replace=False)].mean(axis=0)) for _ in range(n_draw)]
        ra = [v for v in ra if v is not None]
        rs = [v for v in rs if v is not None]
        if rc is None or rw is None or not ra or not rs:
            continue
        rows.append((rc, rw, float(np.mean(ra)), float(np.mean(rs))))
    return np.array(rows)


def distance_curve(sc: np.ndarray, P: np.ndarray, pre: np.ndarray, post: np.ndarray, pop: np.ndarray,
                   edges=(0, 50, 100, 150, 200, 300, 400, 600, 900)):
    """同領域の対の信号相関を soma 間距離(µm)で束ねる: (bin の中心, 平均, 本数)。"""
    sel = pop == 2
    d = np.linalg.norm(P[pre[sel]].astype(np.float64) - P[post[sel]].astype(np.float64), axis=1)
    v = sc[sel].astype(np.float64)
    centres, means, counts = [], [], []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (d >= a) & (d < b)
        if m.sum() >= 20:
            centres.append(0.5 * (a + b))
            means.append(float(v[m].mean()))
            counts.append(int(m.sum()))
    return np.array(centres), np.array(means), np.array(counts)


def wave_on_wiring(L, R: np.ndarray, Rz: np.ndarray, P: np.ndarray, pre: np.ndarray, post: np.ndarray,
                   pop: np.ndarray, nsyn: np.ndarray, n_shuffle: int = 20, gains=(0.3, 1.0, 3.0)):
    """148 本の pre の実測応答を部分グラフ(pre + シナプス数上位の post ≤ MAX_NODES)の reservoir に流す。

    軸索どうしの辺(post も pre)は落とし、役割を「入力を受ける軸索」と「配線で駆動される標的」に分ける。重みは
    W / max(W) に ``gain`` を掛ける(最大シナプス数 = gain)。利得は恣意なので 3 段で感度を出し、主結果は gain 1。
    帰無は次数保存シャッフル ``n_shuffle`` 本(平均・SD・経験 p)。
    """
    con = pop == 0
    pres = np.unique(pre[con])
    deg = np.zeros(len(R))
    np.add.at(deg, post[con], nsyn[con])
    deg[pres] = 0.0
    posts = np.argsort(-deg)[: MAX_NODES - len(pres)]
    posts = posts[deg[posts] > 0]
    nodes = np.concatenate([pres, posts])
    loc = np.full(len(R), -1, np.int64)
    loc[nodes] = np.arange(len(nodes))
    ok = con & (loc[pre] >= 0) & (loc[post] >= 0) & ~np.isin(post, pres)  # 軸索 → 軸索の辺は落とす(役割を分ける)
    n_dropped = int((con & (loc[pre] >= 0) & np.isin(post, pres)).sum())
    syn = np.column_stack([loc[pre[ok]], loc[post[ok]], nsyn[ok]]).astype(np.float64)
    W = L.graph_from_synapses(syn, n=len(nodes))
    U = Rz[pres].T                                                             # (T, n_pre): 実測応答が入力
    W_in = np.zeros((len(nodes), len(pres)))
    W_in[np.arange(len(pres)), np.arange(len(pres))] = 1.0
    source = (np.arange(len(nodes)) < len(pres)).astype(np.int64)
    ip = np.arange(len(pres), len(nodes))
    Rp = Rz[nodes[ip]].T

    wmax = max(float(W.max()), 1e-9)

    def run(Wx, gain=1.0):
        X = L.reservoir_states(Wx * (gain / wmax), U, nonlinearity="tanh", leak=1.0, W_in=W_in)
        # reservoir は 1 ステップで 1 段進む: post の状態 x[t] は pre の入力 u[t−1] から来るので、実測とは 1 コマずらして比べる
        Xp = X[1:, ip]
        Rq = Rp[:-1]
        r = [_corr(Xp[:, j], Rq[:, j]) for j in range(Xp.shape[1])]
        r = np.array([v for v in r if v is not None])
        spread = L.graph_activity_spread(np.abs(X), P[nodes].astype(np.float64), source)
        return r, float(spread["mean_distance"][len(spread["mean_distance"]) // 10:].mean()), X

    r_real, dist_real, X = run(W)
    shuffles = [L.graph_degree_preserving_shuffle(W, seed=s) for s in range(n_shuffle)]
    shuf = [run(Ws)[:2] for Ws in shuffles]
    r_shuf = np.array([r.mean() for r, _ in shuf])
    p_emp = (1 + int((r_shuf >= r_real.mean()).sum())) / (n_shuffle + 1)
    sens = [(g, run(W, g)[0].mean(), np.mean([run(Ws, g)[0].mean() for Ws in shuffles[:3]])) for g in gains if g != 1.0]
    return {"nodes": nodes, "n_pre": len(pres), "n_edges": int(ok.sum()), "n_dropped": n_dropped, "X": X,
            "r_real": r_real, "dist_real": dist_real, "r_shuf": r_shuf, "p_emp": p_emp,
            "dist_shuf": np.array([d for _, d in shuf]), "sensitivity": sens}


# --------------------------------------------------------------------------- #
# 本体                                                                          #
# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.time()
    L = fs.ledger
    rows = []
    data = load_data()
    R, P, area, pre, post, pop, sc, nsyn = (data[k] for k in ("R", "P", "area", "pre", "post", "pop", "sc", "nsyn"))
    real = data["src"].startswith("MICrONS")
    n, T = R.shape
    print("DATA: %s" % data["src"])
    print("neurons %d, frames %d, areas: %s" % (n, T, ", ".join("%s %d" % (AREAS[a], int((area == a).sum())) for a in range(4) if (area == a).any())))
    Rz = _zscore_rows(R)

    # 1. like-to-like
    means, obs, null = like_to_like(sc, pre, pop, N_PERM)
    z = (obs - null.mean()) / max(null.std(), 1e-12)
    n_ge = int((null >= obs).sum())
    p_txt = ("p < %.4f" % (1.0 / (len(null) + 1))) if n_ge == 0 else ("p = %.3f" % ((1 + n_ge) / (len(null) + 1)))
    print("1. like-to-like: in vivo signal corr  Connected %.4f / ADP %.4f / Same region %.4f  -> %s"
          % (means[0], means[1], means[2], order_text(("Connected", "ADP", "Same region"), means)))
    print("   Connected - ADP = %.4f; per-axon shuffle null mean %.4f sd %.4f -> %.1f sd, %s (%d permutations)"
          % (obs, null.mean(), null.std(), z, p_txt, len(null)))
    rows.append(("signal corr mean: C / ADP / Same", "%.4f / %.4f / %.4f" % tuple(means), "C > A > S"))
    rows.append(("C - ADP vs per-axon shuffle null", "%.4f vs %.4f +- %.4f (%.0f sd)" % (obs, null.mean(), null.std(), z), "> 5 sd (real)"))

    # 2. 配線 vs 近接 vs 無作為
    pp = partner_prediction(Rz, pre, post, pop, nsyn)
    m = pp.mean(axis=0)
    win_a, win_s = float((pp[:, 0] > pp[:, 2]).mean()), float((pp[:, 0] > pp[:, 3]).mean())
    print("2. each axon's response vs the mean response of its partners (a similarity on the same %d frames, not a held-out prediction; n=%d axons): "
          "Connected %.3f (synapse-weighted %.3f) / ADP-matched %.3f / Same-matched %.3f  -> %s"
          % (T, len(pp), m[0], m[1], m[2], m[3], order_text(("Connected", "ADP", "Same"), (m[0], m[2], m[3]))))
    print("   paired: Connected beats ADP for %.0f%% of axons, beats Same region for %.0f%%" % (100 * win_a, 100 * win_s))
    rows.append(("axon vs partner-mean corr: C / weighted / ADP / Same", "%.3f / %.3f / %.3f / %.3f" % tuple(m), "C > A > S"))
    rows.append(("axons where C beats ADP / Same", "%.0f%% / %.0f%%" % (100 * win_a, 100 * win_s), "> 60% (real)"))
    dc, dm, dn = distance_curve(sc, P, pre, post, pop)
    if len(dc):
        print("   same-region signal corr by soma distance: " + ", ".join("%d um %.4f (n=%d)" % (c, v, k) for c, v, k in zip(dc, dm, dn)))
    dsoma = np.linalg.norm(P[pre].astype(np.float64) - P[post].astype(np.float64), axis=1)
    dmean = [float(dsoma[pop == k].mean()) for k in range(3)]
    print("   mean soma distance of the pairs (um): Connected %.0f / ADP %.0f / Same region %.0f -> ADP is the distance-matched control" % tuple(dmean))
    rows.append(("soma distance (um): C / ADP / Same", "%.0f / %.0f / %.0f" % tuple(dmean), "ADP ~ Connected"))

    # 3. 配線の波
    wv = wave_on_wiring(L, R, Rz, P, pre, post, pop, nsyn)
    print("3. the wave on the wiring: subgraph %d nodes (%d axons + %d targets), %d edges (%d axon-to-axon edges dropped); "
          "corr(reservoir state one frame later, measured) mean %.4f over %d targets"
          % (len(wv["nodes"]), wv["n_pre"], len(wv["nodes"]) - wv["n_pre"], wv["n_edges"], wv["n_dropped"], wv["r_real"].mean(), len(wv["r_real"])))
    print("   degree-preserving shuffle x%d: mean %.4f sd %.4f (max %.4f), empirical p = %.3f; activity mean distance from the axons: real %.0f um vs shuffled %.0f um"
          % (len(wv["r_shuf"]), wv["r_shuf"].mean(), wv["r_shuf"].std(), wv["r_shuf"].max(), wv["p_emp"], wv["dist_real"], wv["dist_shuf"].mean()))
    print("   gain sensitivity (max synapse count -> weight): " + "; ".join("gain %.1f: real %.4f vs shuffled %.4f" % t for t in wv["sensitivity"]))
    rows.append(("wave corr: real / shuffled mean +- sd (n)", "%.4f / %.4f +- %.4f (%d)" % (wv["r_real"].mean(), wv["r_shuf"].mean(), wv["r_shuf"].std(), len(wv["r_shuf"])), "real > every shuffle"))
    rows.append(("wave gain sensitivity: real / shuffled", "; ".join("g%.1f %.3f / %.3f" % t for t in wv["sensitivity"]), "order kept"))
    rows.append(("wave mean distance (um): real / shuffled", "%.0f / %.0f" % (wv["dist_real"], wv["dist_shuf"].mean()), "same (honest)"))
    rows.append(("inputs per target in the subgraph", "%.2f" % (wv["n_edges"] / max(len(wv["nodes"]) - wv["n_pre"], 1)), "why the wave is faint"))

    assert means[0] > means[2], means                                          # like-to-like(合成でも)
    assert m[0] > m[3], m                                                      # 結合相手 > 無作為(合成でも)
    if real:
        assert means[0] > means[1] > means[2], means
        assert z > 5.0, z
        assert m[0] > m[2] > m[3], m
        assert win_a > 0.6, win_a
        assert wv["r_real"].mean() > wv["r_shuf"].max(), (wv["r_real"].mean(), wv["r_shuf"])   # 20 本のシャッフル全部より上
        assert all(r > s for _g, r, s in wv["sensitivity"]), wv["sensitivity"]                  # 利得を 0.3 / 3 倍にしても順序は同じ
    else:
        print("   (synthetic cortex: the bars are properties of the real data and are not asserted here)")

    if figs.enabled():
        # 1. 脳の波: 実測応答を各細胞の 95 パーセンタイルで正規化して 1 mm³ に載せる
        Pf = P.astype(np.float64)
        Pf = np.column_stack([Pf[:, 0], Pf[:, 2], -Pf[:, 1]])                # y は皮質の深さ(下向き): 上を軟膜に
        Rn = _highlights(R.T)                                                 # (T, n): 各細胞が自分の上位 1/4 にいる瞬間だけ点く
        step = 3 if REDUCED else 1
        cols = AREA_COLOURS[np.clip(area, 0, 3)]
        vid = L.points_activity_video(Pf, Rn[::step], colors=cols, size=180 if REDUCED else 320, gain=3.0, point_px=2,
                                      pitch=20.0, yaw_span=360.0)
        figs.save_gif("brain_wave", vid, fps=10.0,
                      caption="the measured brain wave: %d neurons at their soma positions in the 1 mm^3 volume, a cell lights when its trial-averaged response to the natural movie is in its own top quartile (scaled from its 75th to its 99th percentile), %d frames while the volume turns; colours = V1 blue, RL yellow, AL green, LM red; %s"
                              % (n, Rn[::step].shape[0], data["src"].split(":")[0]))
        # 2. like-to-like と距離
        series = [("same region pairs by soma distance", dc, dm)] if len(dc) else []
        xs = dc if len(dc) else np.array([0.0, 1.0])
        series += [("Connected mean", xs, np.full(len(xs), means[0])), ("ADP (touching, unconnected) mean", xs, np.full(len(xs), means[1]))]
        figs.save_plot("like_to_like", series, xlabel="soma distance (um)", ylabel="in vivo signal correlation",
                       title="like-to-like: connected > touching > same region",
                       caption="signal correlation of the in vivo responses: pairs in the same region binned by soma distance (curve), against the means of the connected pairs and of the ADP pairs whose axon and dendrite touch without a synapse; the per-axon permutation null of Connected - ADP has sd %.4f" % null.std())
        # 3. 配線 vs 近接(pre ごとの対)
        lim = (min(pp[:, 2].min(), pp[:, 0].min()) - 0.05, max(pp[:, 2].max(), pp[:, 0].max()) + 0.05)
        figs.save_plot("wiring_vs_proximity", [("axons (%d)" % len(pp), pp[:, 2], pp[:, 0]), ("equal", np.array(lim), np.array(lim))],
                       kinds=["scatter", "line"], xlabel="x: k touching, unconnected partners",
                       ylabel="y: its k connected partners (corr)", title="wiring adds to proximity",
                       caption="each axon's response predicted from the mean response of its connected partners (y) versus the same number of touching-but-unconnected partners (x): above the diagonal the wiring beats proximity (%.0f%% of axons)" % (100 * win_a))
        # 4. 配線の波
        nodes, X = wv["nodes"], wv["X"]
        Pn = Pf[nodes]
        cn = AREA_COLOURS[np.clip(area[nodes], 0, 3)].copy()
        cn[: wv["n_pre"]] = [1.0, 1.0, 0.6]
        Xa = _highlights(np.maximum(X, 0.0))[:: (3 if REDUCED else 2)]      # 正の駆動が自分の上位 1/4 にある瞬間だけ点く
        vid2 = L.points_activity_video(Pn, Xa, colors=cn, size=180 if REDUCED else 320, gain=3.0, point_px=2,
                                       pitch=20.0, yaw_span=180.0, background=Pf)
        figs.save_gif("wave_on_wiring", vid2, fps=8.0,
                      caption="the measured responses of the %d proofread axons (pale yellow) driven through the reservoir of the %d-node connected subgraph over all somata (grey): a target lights when the drive it receives through its real synapses is in its own top quartile; correlation of the reservoir states with the measured responses %.3f vs %.3f for a degree-preserving shuffle"
                              % (wv["n_pre"], len(nodes), wv["r_real"].mean(), wv["r_shuf"].mean()))
        figs.save_table("numbers", ["quantity", "value", "bar"], rows, title="MICrONS brain wave PoC numbers",
                        caption="every number, with the bar it had to clear")
        assert not figs.errors(), figs.errors()
    print("elapsed %.0fs" % (time.time() - t0))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
