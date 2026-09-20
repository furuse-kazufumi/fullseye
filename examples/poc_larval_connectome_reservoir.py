# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 幼虫コネクトームを固定の reservoir にして手書き数字を読み出す ―― 配線は効くのか、それとも reservoir なら何でもよいのか

先行研究(Yu, Vogelstein ら「Biological Processing Units」2025)は、ショウジョウバエ幼虫の完全コネクトーム
(約 3,000 ニューロン)をそのまま固定の再帰網にし、読み出しだけ学習して MNIST 98 % を報告した。ただし要旨には
**配線の統計を保った乱数グラフとの対照**が無い。この PoC はその対照を置く: 同じ次数列を保って辺を繋ぎ替えた
グラフ(`graph_degree_preserving_shuffle`)、同じ密度の Erdős–Rényi、同じ規模のガウス乱数 reservoir、そして
reservoir 無し(生画素の ridge)。読み出しは全部同じ閉形式の ridge 回帰(`ridge_readout`)。

**主張は 1 つだけ**: 「読み出せる」は本当で、「配線が効く」は言えない(手元の実測: コネクトーム ≈ 次数保存 shuffle ≈ 乱数)。
BPU 論文の 98 % は全 MNIST + 調整済みの値で、ここでは再現を主張しない(部分集合・小さな格子で正直に選んだ設定)。

データ:
* Winding et al. 2023 Science「The connectome of an insect brain」の Supplementary Data S1(all-all 接続行列、
  2,952 ニューロン、重み = シナプス数)。GitHub のミラー(brain-networks/larval-drosophila-connectome)から
  実行時にダウンロードして手元にキャッシュする(``FULLSEYE_DATA_DIR`` か ``~/.cache/fullseye``)。**repo には
  再配布しない**(この PoC が commit するのは集計値と図だけ)。
* MNIST(IDX 形式、ossci のミラー)。同じくキャッシュ。
* どちらかが取れないときは**合成の代替**(同じ規模の有向グラフ / 線形分離可能な合成クラス)で同じ経路を走らせ、
  出力の先頭に ``DATA: synthetic surrogate`` と理由を印字する ―― 実測の主張はしない。

走らせ方: ``py -3.11 examples/poc_larval_connectome_reservoir.py``(図は ``FULLSEYE_FIGURE_DIR`` があるときだけ)。
"""
from __future__ import annotations

import gzip
import io
import os
import sys
import time
import zipfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

SEED = 20260920
S1_URL = "https://raw.githubusercontent.com/brain-networks/larval-drosophila-connectome/main/Supplementary-Data-S1.zip"
MNIST_URL = "https://ossci-datasets.s3.amazonaws.com/mnist/"
N_TRAIN, N_VAL, N_TEST = 3000, 1000, 1000
#: ★CI(2 コア)では full の設定が 600 秒の枠を超えて -1(timeout)になった(2026-09-20、run 35501201432)。
#:   FULLSEYE_POC_BUDGET=reduced(CI では既定)で標本・格子・seed を減らす。展示の数字は full の実測で、
#:   reduced は「同じ経路が走る」ことの証拠に留める(先頭に BUDGET: を印字)。
REDUCED = (os.environ.get("FULLSEYE_POC_BUDGET") or ("reduced" if os.environ.get("CI") else "full")) == "reduced"
if REDUCED:
    N_TRAIN, N_VAL, N_TEST = 1000, 500, 500
SEEDS = (0, 1) if REDUCED else (0, 1, 2)


def _cache_dir() -> str:
    base = os.environ.get("FULLSEYE_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "fullseye")
    d = os.path.join(base, "poc_larval_connectome_reservoir")
    os.makedirs(d, exist_ok=True)
    return d


def _fetch(url: str, timeout: float = 60.0) -> bytes:
    import urllib.request
    with urllib.request.urlopen(url, timeout=timeout) as r:      # noqa: S310 - fixed https URLs above
        return r.read()


def load_connectome() -> tuple[np.ndarray, str]:
    """(W, provenance)。W は conn_graph(n×n、W[pre, post] = シナプス数)。取れなければ合成の代替。"""
    npy = os.path.join(_cache_dir(), "winding2023_all_all.npy")
    if os.path.exists(npy):
        return np.load(npy).astype(np.float64), "cache: " + npy
    try:
        z = zipfile.ZipFile(io.BytesIO(_fetch(S1_URL)))
        name = [n for n in z.namelist() if n.endswith("all-all_connectivity_matrix.csv") and "__MACOSX" not in n][0]
        raw = z.read(name).decode("utf-8")
        ncol = raw.split("\n", 1)[0].count(",")
        W = np.loadtxt(io.StringIO(raw), delimiter=",", skiprows=1, usecols=range(1, ncol + 1), dtype=np.float64)
        np.save(npy, W.astype(np.float32))
        return W, "downloaded: Winding 2023 S1 all-all (%d neurons)" % W.shape[0]
    except Exception as exc:                                       # noqa: BLE001 - offline / mirror gone: say so, do not invent
        rng = np.random.default_rng(SEED)
        n, m = 2952, 110677
        # 次数が重い裾を持つ有向グラフ(実物の粗い形だけ真似る。実物ではない)
        p = rng.pareto(1.5, n) + 1.0
        p /= p.sum()
        src = rng.choice(n, size=m, p=p)
        dst = rng.choice(n, size=m, p=p)
        W = np.zeros((n, n))
        np.add.at(W, (src, dst), rng.integers(1, 6, size=m).astype(float))
        return W, "synthetic surrogate (%s: %s)" % (type(exc).__name__, str(exc)[:80])


def load_digits() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str]:
    """(X_train, y_train, X_test, y_test, provenance)。X は N×784 in [0, 1]。取れなければ合成の代替。"""
    npz = os.path.join(_cache_dir(), "mnist_subset.npz")
    if os.path.exists(npz):
        d = np.load(npz)
        return d["Xtr"], d["ytr"], d["Xte"], d["yte"], "cache: " + npz

    def idx_images(b: bytes) -> np.ndarray:
        n, h, w = int.from_bytes(b[4:8], "big"), int.from_bytes(b[8:12], "big"), int.from_bytes(b[12:16], "big")
        return np.frombuffer(b, dtype=np.uint8, offset=16).reshape(n, h * w)

    def idx_labels(b: bytes) -> np.ndarray:
        return np.frombuffer(b, dtype=np.uint8, offset=8).astype(np.int64)

    try:
        get = lambda f: gzip.decompress(_fetch(MNIST_URL + f))    # noqa: E731
        Xtr = idx_images(get("train-images-idx3-ubyte.gz"))[: N_TRAIN + N_VAL] / 255.0
        ytr = idx_labels(get("train-labels-idx1-ubyte.gz"))[: N_TRAIN + N_VAL]
        Xte = idx_images(get("t10k-images-idx3-ubyte.gz"))[:N_TEST] / 255.0
        yte = idx_labels(get("t10k-labels-idx1-ubyte.gz"))[:N_TEST]
        np.savez_compressed(npz, Xtr=Xtr.astype(np.float32), ytr=ytr, Xte=Xte.astype(np.float32), yte=yte)
        return Xtr, ytr, Xte, yte, "downloaded: MNIST (%d train+val, %d test)" % (len(ytr), len(yte))
    except Exception as exc:                                       # noqa: BLE001
        rng = np.random.default_rng(SEED + 1)
        proto = rng.random((10, 784))
        def mk(n):
            y = rng.integers(0, 10, n)
            return np.clip(proto[y] + 0.35 * rng.standard_normal((n, 784)), 0, 1), y
        Xtr, ytr = mk(N_TRAIN + N_VAL)
        Xte, yte = mk(N_TEST)
        return Xtr, ytr, Xte, yte, "synthetic surrogate (%s: %s)" % (type(exc).__name__, str(exc)[:80])


def one_hot(y: np.ndarray) -> np.ndarray:
    return np.eye(10)[y]


def encode(Wres: np.ndarray, X: np.ndarray, in_scale: float, seed: int) -> np.ndarray:
    """reservoir の最終状態 + 生画素(標準的な ESN の読み出し特徴)。"""
    S, _ = fs.op_run("reservoir_encode", Wres, X, steps=6, in_scale=in_scale, leak=0.3, seed=seed)
    return np.hstack([np.asarray(S), X])


def fit_eval(F_tr, y_tr, F_te, y_te, alpha: float) -> float:
    Wout, _ = fs.op_run("ridge_readout", F_tr, one_hot(y_tr), alpha=alpha)
    P, _ = fs.op_run("ridge_predict", F_te, Wout)
    return float((np.asarray(P).argmax(1) == y_te).mean())


def main() -> int:
    t0 = time.time()
    if REDUCED:
        print("BUDGET: reduced (%d train / %d val / %d test, %d seeds) — the exhibit numbers come from the full run" % (N_TRAIN, N_VAL, N_TEST, len(SEEDS)))
    W, prov_w = load_connectome()
    Xall, yall, Xte, yte, prov_x = load_digits()
    synthetic = "synthetic" in prov_w or "synthetic" in prov_x
    print("DATA: %s" % ("synthetic surrogate — no empirical claim below" if synthetic else "real"))
    print("  connectome: %s" % prov_w)
    print("  digits    : %s" % prov_x)
    Xtr, ytr, Xva, yva = Xall[:N_TRAIN], yall[:N_TRAIN], Xall[N_TRAIN:N_TRAIN + N_VAL], yall[N_TRAIN:N_TRAIN + N_VAL]
    n = W.shape[0]
    dt, _ = fs.op_run("graph_degree_table", W)                    # 列名 → 配列の dict(この repo の table)
    deg = np.column_stack([dt["in_degree"], dt["out_degree"]])
    print("graph: %d nodes, %d edges, %d self-loops, radius %.1f" % (n, int((W != 0).sum()), int((np.diag(W) != 0).sum()),
                                                                     fs.op_run("graph_spectral_radius", W)[0]))

    # 1. 対照グラフ(op で作れるものは op で)
    rng = np.random.default_rng(SEED)
    Wsh, _ = fs.op_run("graph_degree_preserving_shuffle", W, seed=1)
    Wsh = np.asarray(Wsh)
    dsh = fs.op_run("graph_degree_table", Wsh)[0]
    assert np.array_equal(deg, np.column_stack([dsh["in_degree"], dsh["out_degree"]])), "shuffle が次数を変えた"
    assert not np.array_equal(W != 0, Wsh != 0), "shuffle が辺を変えていない"
    m = int((W != 0).sum())
    Wer = np.zeros_like(W)
    Wer.flat[rng.choice(n * n, size=m, replace=False)] = rng.permutation(W[W != 0])
    Wg = rng.standard_normal((n, n)) * (rng.random((n, n)) < m / (n * n))
    variants = [("larval connectome", W), ("degree-preserving shuffle", Wsh),
                ("Erdős–Rényi, same density", Wer), ("Gaussian sparse random", Wg)]
    scaled = []
    for label, A in variants:
        Ares, _ = fs.op_run("reservoir_from_graph", A, rho=0.9)
        Ares = np.asarray(Ares)
        assert abs(fs.op_run("graph_spectral_radius", Ares)[0] - 0.9) < 1e-6, label
        scaled.append((label, Ares))

    # 2. 設定はコネクトームの検証分割で 1 度だけ選び、全対照に同じ設定を使う(公平)
    grid = [(0.1, 1.0), (0.05, 1.0)] if REDUCED else [(s, a) for s in (0.02, 0.05, 0.1) for a in (1e-2, 1.0)]
    best, best_acc = None, -1.0
    for in_scale, alpha in grid:
        acc = fit_eval(encode(scaled[0][1], Xtr, in_scale, 0), ytr, encode(scaled[0][1], Xva, in_scale, 0), yva, alpha)
        if acc > best_acc:
            best, best_acc = (in_scale, alpha), acc
    in_scale, alpha = best
    print("chosen on validation (connectome): in_scale=%g alpha=%g (val acc %.3f)" % (in_scale, alpha, best_acc))

    # 3. 本番: 訓練 = train+val、評価 = test、seed 3 本
    Xfit, yfit = Xall, yall
    base = fit_eval(np.asarray(Xfit), yfit, np.asarray(Xte), yte, alpha)
    results = {"no reservoir (ridge on pixels)": (base, 0.0)}
    print("%-34s %.3f" % ("no reservoir (ridge on pixels)", base))
    for label, Ares in scaled:
        accs = [fit_eval(encode(Ares, Xfit, in_scale, s), yfit, encode(Ares, Xte, in_scale, s), yte, alpha) for s in SEEDS]
        results[label] = (float(np.mean(accs)), float(np.std(accs)))
        print("%-34s %.3f ± %.3f" % (label, np.mean(accs), np.std(accs)))

    # 4. 所見(数字で固定する。落ちたら「穴が塞がった」か「壊れた」かのどちらか)
    conn, shuf = results["larval connectome"][0], results["degree-preserving shuffle"][0]
    for label, (acc, _) in results.items():
        assert acc > 0.5, "%s が偶然(0.1)に近い: %.3f" % (label, acc)
    if not synthetic:
        gap = conn - shuf
        print("finding: connectome − shuffle = %+.3f (%d seeds; |gap| < %.2f means the wiring is not what the readout uses)"
              % (gap, len(SEEDS), 0.05 if REDUCED else 0.03))
        assert abs(gap) < (0.05 if REDUCED else 0.03), "配線固有の効果が出た(良い変化 — この節と docstring を書き換えること): %+.3f" % gap

    # 5. 図(FULLSEYE_FIGURE_DIR があるときだけ)。★2,952² の隣接行列をそのまま描くと 1.3 % の点で一色になり、
    #   Fiedler 配置は重い裾の次数分布で 1 点に潰れる(2026-09-20 に実際にそうなった)。升に集約し、対照と並べる。
    def binned(A, order, k=96):
        B = A[np.ix_(order, order)]
        e = np.linspace(0, len(order), k + 1).astype(int)
        return np.array([[B[e[i]:e[i + 1], e[j]:e[j + 1]].sum() for j in range(k)] for i in range(k)])

    order = np.argsort(-deg.sum(1))                                  # 次数の高い順(ハブが左上)
    tiles = [np.log1p(binned(A, order)) for A in (W, Wsh)]
    top = max(t.max() for t in tiles)
    gap = np.zeros((96, 6))
    figs.save("adjacency_binned_connectome_vs_shuffle", np.kron(np.hstack([tiles[0] / top, gap, tiles[1] / top]), np.ones((4, 4))),
              "adjacency summed into 96x96 bins, nodes sorted by degree (hubs top-left): connectome | degree-preserving shuffle")
    sub = order[:300]
    x0 = np.asarray(Xte[:1])
    rasters = []
    for _, Ares in scaled[:2]:
        cols = [np.asarray(fs.op_run("reservoir_encode", Ares, x0, steps=k, in_scale=in_scale, leak=0.3, seed=0)[0])[0, sub]
                for k in range(1, 7)]
        R = np.abs(np.stack(cols, 1))                                 # 300 neurons x 6 steps
        rasters.append(np.repeat(R / max(R.max(), 1e-9), 40, axis=1))
    figs.save("activity_raster_connectome_vs_shuffle", np.hstack([rasters[0], np.zeros((300, 12)), rasters[1]]),
              "|state| of the 300 highest-degree neurons over 6 steps for one test digit: connectome | shuffle")
    bars = np.zeros((len(results) * 24, 400))
    for k, (label, (acc, _)) in enumerate(results.items()):
        bars[k * 24 + 4:k * 24 + 20, :int(acc * 399)] = 1.0
    figs.save("accuracy_bars", bars, "test accuracy per reservoir variant (rows: no reservoir, connectome, shuffle, ER, Gaussian)")
    assert not figs.errors(), figs.errors()                             # 図の失敗を黙って捨てない
    print("elapsed %.0fs" % (time.time() - t0))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
