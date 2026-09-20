# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 複眼が見る像と、脳のどこが反応するかを並べる ―― 個眼を指でなぞると応答が配線を伝わる

前の展示(`poc_malecns_activity_wave`)は右視葉の全体に刺激を入れた。この PoC は **個眼 1 つ分** の解像度で入れる:
MaleCNS の注釈には視葉ニューロンごとに六角柱(``assignedOlHex1/2`` = 網膜の個眼に対応する柱)が付いている。
右眼の 892 柱それぞれの視葉ニューロン(柱ごとに上位 3 体)と中枢・下行のハブ(1,400 体)を部分グラフにし、
柱を 1 つずつ刺激して、応答がどこに出るかを脳の立体に描く。隣に**同じ入力行列**で次数保存 shuffle。

**主張は 1 つだけ**: 刺激した柱の位置(眼の上の座標)と、応答した視葉ニューロンの重心(脳の座標)の間に単調な
対応(網膜部位対応、retinotopy)がコネクトームにはあり、次数保存 shuffle には無い。数字は柱の座標と応答重心の
相関係数(``graph_activity_spread`` と同じ |x| 重み)。

図:
1. ``eye_sweep``: 個眼の刺激を眼の一行に沿って動かす GIF。左 = 複眼(刺激した柱を黄で縁取り)、右 = 脳の立体
   (黄 = 刺激ノード、橙/青 = 応答、尺度 = 刺激を除いた応答の最大)。上段コネクトーム、下段 shuffle。
2. ``image_through_the_eye``: 縦縞が視野を横切る像を ``fly_hex_resample`` で個眼に落とし、個眼の明るさをそのまま
   刺激にして脳に入れる GIF。左 = 複眼が見る像、右 = 応答。
3. ``retinotopy_scatter``: 刺激した柱の横座標 vs 応答重心の横座標(コネクトーム / shuffle)。
4. ``retinotopy_vs_bits``: 個眼信号を ``fly_hex_quantize`` で 1〜8 ビットに落としたときの網膜部位対応(複眼は量子化器)。

Studio では Tools ▸ 「Compound eye → brain」が同じ部品で対話的に動く(マウスで刺激位置、ドラッグで視点)。
データ: 手元の MaleCNS から部分グラフを作ってキャッシュ(生データも部分グラフも commit しない)。無ければ合成の
代替(脳 2 葉 + VNC に六角柱つきの右眼、距離依存の配線)で同じ経路を走らせ ``DATA: synthetic surrogate`` と印字する。

走らせ方: ``py -3.11 examples/poc_eye_to_brain.py``(図は ``FULLSEYE_FIGURE_DIR`` があるときだけ)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402
import eyebrain  # noqa: E402

STEPS_PER_STOP = 10
N_STOPS = 12
EYE = 300
BRAIN = 300
VIEWS = ((0.0, 15.0), (90.0, 0.0))                 # 背側 | 側面


def flip(Q: np.ndarray) -> np.ndarray:
    return np.column_stack([Q[:, 0], Q[:, 1], -Q[:, 2]])


def header(width: int, text: str) -> np.ndarray:
    strip = np.full((40, width, 3), 0.06)
    return np.asarray(fs.text_box(strip, text, (6, 4), anchor="lt", font_size=12, color="neutral", box_alpha=0.0))


def render_brain(eb: eyebrain.EyeBrain, x: np.ndarray, stim: np.ndarray, peak: float, size: int = BRAIN) -> np.ndarray:
    """1 コマ: 明るさ(尺度 = 応答の最大)を points_activity_video に渡す —— 明るいノードは一回り大きく描かれ、
    応答の無いノードは背景の soma と同じ暗さに沈む。刺激ノードは黄で明るさ 1。固定視点。"""
    b = eb.brightness(x, stim, peak)
    # ★背側から見るだけだと、像の左右(方位角)は soma の y 軸 = 奥行きに写り、応答の移動が見えない
    #   (2026-09-20 に実測: 縞を動かしても同じ場所が光って見えた)。背側と側面の 2 方向を並べる。
    V, _ = fs.op_run("points_activity_video", flip(eb.P), b[None, :], colors=eb.node_colors(stim), size=size,
                     aspect=0.75, views=VIEWS, point_px=2, gain=20.0, background=flip(eb.P_all))
    return np.asarray(V)[0]


def response_centroid(eb: eyebrain.EyeBrain, X: np.ndarray, stim: np.ndarray) -> np.ndarray:
    """刺激ノードを除いた視葉ニューロンの |x| 重みつき重心(soma 座標)。"""
    A = np.abs(X).max(axis=0)
    A[stim > 0] = 0.0
    A[eb.node_col < 0] = 0.0
    w = A / max(A.sum(), 1e-12)
    return w @ eb.P


def main() -> int:
    t0 = time.time()
    eb = eyebrain.load()
    synthetic = eb.provenance.startswith("synthetic")
    print("DATA:", eb.provenance)
    print("nodes %d  eye columns %d  ommatidia %d  edges %d" % (eb.n, len(eb.columns), len(eb.lattice["uv"]), int((eb.W > 0).sum())))

    # --- 1. 個眼を一行に沿って動かす: 柱の横座標 vs 応答重心
    cu = eb.columns - eb.columns.mean(axis=0)
    row_cols = np.nonzero(np.abs(cu[:, 1]) <= 1.0)[0]                   # 中央の一行(hex2 ≈ 0)
    row_cols = row_cols[np.argsort(cu[row_cols, 0])]
    stops = row_cols[np.linspace(0, len(row_cols) - 1, N_STOPS).astype(int)]
    xs, cen = [], {"connectome": [], "shuffle": []}
    frames = []
    for k in stops:
        stim = eb.stimulus_for_column(int(k), radius=1)
        xs.append(float(cu[k, 0]))
        per = {}
        for label, sh in (("connectome", False), ("shuffle", True)):
            X = eb.run_wave(stim, steps=STEPS_PER_STOP, shuffle=sh)
            per[label] = (X, eb.response_peak(X, stim))
            cen[label].append(response_centroid(eb, X, stim))
        eye_img = eb.eye_view(None, EYE, highlight=eb.column_neighbourhood(int(k), 1))
        for t in range(STEPS_PER_STOP):
            panels = []
            for label in ("connectome", "shuffle"):
                X, pk = per[label]
                panels.append(render_brain(eb, X[t], stim, pk))
            right = np.vstack([panels[0], np.full((8, panels[0].shape[1], 3), 0.02), panels[1]])
            pad = right.shape[0] - EYE
            left = np.vstack([np.full((pad // 2, EYE, 3), 0.06), eye_img, np.full((pad - pad // 2, EYE, 3), 0.06)])
            frames.append(np.hstack([left, np.full((right.shape[0], 8, 3), 0.02), right]))
    for label in cen:
        cen[label] = np.asarray(cen[label])
    corr = {label: float(np.corrcoef(xs, cen[label][:, 0])[0, 1]) for label in cen}
    print("retinotopy: corr(column x, response centroid x) connectome %+.3f  shuffle %+.3f  (%d stops)" % (corr["connectome"], corr["shuffle"], len(stops)))
    assert abs(corr["connectome"]) > 0.7, "コネクトームに網膜部位対応が見えない: %+.3f" % corr["connectome"]
    assert abs(corr["connectome"]) > abs(corr["shuffle"]) + 0.3, "shuffle でも対応が残っている: %+.3f vs %+.3f" % (corr["connectome"], corr["shuffle"])

    # --- 2. 像を眼に通す: 縦縞が視野を横切る
    frames2 = []
    W_IMG = 128
    for s in np.linspace(-20, W_IMG + 4, 16):
        img = np.zeros((W_IMG, W_IMG))
        lo, hi = int(max(0, s)), int(min(W_IMG, s + 16))
        img[:, lo:hi] = 1.0
        sig = eb.eye_signal(img)
        stim = eb.stimulus_from_signal(sig)
        X = eb.run_wave(stim, steps=6)
        pk = eb.response_peak(X, stim)
        eye_img = eb.eye_view(sig, EYE)
        brain = render_brain(eb, X[4], stim, pk, size=EYE)
        frames2.append(np.hstack([np.vstack([header(EYE, "what the eye sees"), eye_img]), np.full((EYE + 40, 8, 3), 0.02),
                                  np.vstack([header(brain.shape[1], "where the brain responds"), brain])]))
    mid = np.zeros((W_IMG, W_IMG)); mid[:, W_IMG // 2 - 8: W_IMG // 2 + 8] = 1.0
    sig_mid = eb.eye_signal(mid)
    print("image mode (bar at the centre): %d ommatidia > 0.5, %d stimulated neurons" % (int((sig_mid > 0.5).sum()), int((eb.stimulus_from_signal(sig_mid) > 0).sum())))

    # --- 3. 複眼は量子化器: 個眼信号を n ビットに落としても網膜部位対応は残るか(ユーザー 2026-09-20「複眼は量子化しやすそう」)
    def retinotopy_from_images(bits):
        xs_b, cx_b = [], []
        xx = np.arange(W_IMG, dtype=float)
        for lo in np.linspace(12, W_IMG - 12, 10):
            # ★2 値の縞では 1 ビットでも相関 0.99 で量子化の効き目が測れない(実測)。背景 0.5 に +0.3 の
            #   滑らかな縞(σ = 6 px)= 低コントラストの像で、ビット数が信号を潰す条件にする。
            img = np.tile(0.5 + 0.3 * np.exp(-0.5 * ((xx - lo) / 6.0) ** 2), (W_IMG, 1))
            sig = eb.eye_signal(img)
            if bits == "raw":                                                       # 適応なし(背景も刺激になる)
                pass
            elif bits is None:                                                      # 適応あり・連続値 = 量子化なしの同じ対数圧縮
                y = np.log1p(sig / max(float(sig.mean()), 1e-12)); y = y - y.min()
                sig = y / max(float(y.max()), 1e-9)
            else:
                sig = np.asarray(fs.op_run("fly_hex_quantize", sig, bits=bits, mode="log")[0])
            stim = eb.stimulus_from_signal(sig)
            if not (stim > 0).any():
                continue
            X = eb.run_wave(stim, steps=6)
            xs_b.append(lo); cx_b.append(response_centroid(eb, X, stim)[1])       # 像の左右は soma の y に写る
        return float(abs(np.corrcoef(xs_b, cx_b)[0, 1])) if len(xs_b) >= 3 else float("nan")
    bits_list = [1, 2, 3, 4, 6, 8]
    corr_bits = [retinotopy_from_images(b) for b in bits_list]
    corr_full = retinotopy_from_images(None)
    corr_raw = retinotopy_from_images("raw")
    print("bits -> |corr(bar x, response centroid)|: " + "  ".join("%d:%.2f" % (b, c) for b, c in zip(bits_list, corr_bits))
          + "  float(adapted):%.2f  float(raw, no adaptation):%.2f" % (corr_full, corr_raw))
    # ★実測(2026-09-20): 効いているのはビット数ではなく「背景を引く」適応。背景 0.5 の像を適応なしで入れると
    #   全柱が刺激され重心が動かない(実データで 0.63)。適応した連続値と 8 ビットは同じ(0.99)。
    assert abs(corr_bits[-1] - corr_full) < 0.15, "8 ビットが適応済みの連続値と違う: %.2f vs %.2f" % (corr_bits[-1], corr_full)
    if not synthetic:
        assert corr_full > corr_raw + 0.2, "適応(背景を引く)の効き目が見えない: %.2f vs %.2f" % (corr_full, corr_raw)

    # --- 図
    h = header(frames[0].shape[1], "cursor column → response, dorsal | lateral  (top: connectome / bottom: shuffle)")
    figs.save_gif("eye_sweep", [np.vstack([h, f]) for f in frames], fps=10.0,
                  caption="a stimulus of one eye column (+ its 6 neighbours) moves along a row of the right eye; "
                          "yellow = stimulated neurons, orange/blue = response (scale = response peak); "
                          "the connectome answers retinotopically, the shuffle does not")
    figs.save_gif("image_through_the_eye", frames2, fps=6.0,
                  caption="a bar crossing the visual field, resampled onto the ommatidial lattice (fly_hex_resample) and fed "
                          "into the wiring as per-column stimulus; the response follows the bar")
    figs.save_plot("retinotopy_scatter", [("connectome", np.asarray(xs), cen["connectome"][:, 0]), ("degree-preserving shuffle", np.asarray(xs), cen["shuffle"][:, 0])],
                   xlabel="stimulated column (hex x)", ylabel="response centroid x (soma coordinate)",
                   title="retinotopy: corr %+.2f vs %+.2f" % (corr["connectome"], corr["shuffle"]),
                   caption="|x|-weighted centroid of the responding optic-lobe neurons vs the stimulated column")
    figs.save_plot("retinotopy_vs_bits", [("log-quantized eye signal", np.asarray(bits_list, float), np.asarray(corr_bits)),
                                          ("float, adapted", np.asarray([1.0, 8.0]), np.asarray([corr_full, corr_full])),
                                          ("float, raw (no adaptation)", np.asarray([1.0, 8.0]), np.asarray([corr_raw, corr_raw]))],
                   xlabel="bits per ommatidium", ylabel="|corr| (bar position vs response centroid)",
                   title="how many bits does the wiring need? adaptation matters more than bits",
                   caption="fly_hex_quantize(mode=log): a low-contrast soft bar (0.5 + 0.3, sigma 6 px) crossing the visual field is quantized to n bits per ommatidium before entering the wiring")
    assert not figs.errors(), figs.errors()
    print("elapsed %.0fs" % (time.time() - t0))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
