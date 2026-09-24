#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 注意機構を速くする工夫は、全部おなじ数の別の括り方だった。

★主張は「Transformer を実装しました」ではない。**LLM に至る系譜に出てくる
高速化・省メモリ化は、どれも近似ではなく恒等式の括り直しで、その等式は
機械精度で検算できる** —— 使うのは新しい族 `llmcore`(10 op)だけ。

しかも入力は**画像のパッチ列**にしてある(64x64 を 8x8 で切った 64 トークン)。
注意はトークン列の上の演算なので、画像を格子に切ればそのまま ViT の入口になり、
**絵の側でも主張が立つ**。

★★この PoC の芯は 7 つ:

  1. **FlashAttention は近似ではない。** タイル + online softmax は一括と
     一致する —— タイルの大きさを 7 通り(1 行〜64 行)振って最悪 **1.33e-15**。
     速さの出どころは計算を変えたことではなく、**(T, T) の行列を作らない**こと。
     ★外した予言: 「タイルを細かくするほど誤差が積もる」→ 積もりはするが
     **タイル 64 枚 1.33e-15 対 1 枚 1.22e-15 = 1.1 倍**にしかならない。
  2. **線形 Attention は結合則そのもの。** (QKᵀ)V == Q(KᵀV) が **1.18e-15**。
     O(T²d) と O(Td²) は同じ数の別の括り方で、交差点は **T == d**
     (T=64 で速度比 1.1)。★予言は途中まで当たって途中で外れる —— 比は T/d に
     沿って育つが(T=1024 で 11 倍前後)、**T=2048 では式が言う 32 倍に届かず
     15〜16 倍で頭打ち**になる。二次の側が帯域律速に入るから。
     ★ただしこの 2 つは**時間の測定**なので、恒等式と違って機械に依る。
  3. **因果マスクの下では、未来を書き換えても前の出力が 1 ビットも動かない**
     (**0.0e+00**)。これは同義反復ではない —— 実際に 32 行目から先の
     key/value を**別の乱数に差し替えて**測っており、後半は **0.403** 動く。
     KV Cache が成り立つ根拠がこれで、逐次に 1 行ずつ進めた結果は
     一括と **5.92e-16**。
  4. **注意の疎さは整数で数えられる。** 因果マスクの非ゼロは厳密に
     **T(T+1)/2 = 2080**、幅 9 の窓は **Σ min(i+1, W) = 540** ——
     どちらも**浮動小数の許容差が要らない**主張。
  5. **位置符号が無ければ、注意はパッチの順番を見ていない。** パッチを
     並べ替えて出力を戻すと**元と一致する**(**4.4e-16**)。RoPE を入れると
     一致しない(**0.018**)—— **それが位置符号の仕事**。絵で見ると、前者は
     同じ絵、後者は別の絵になる。
  6. **RoPE は回転なのでノルムを保ち、内積は相対位置だけで決まる。**
     ノルムの差は 64 本すべてで **4.44e-16**、位置の差を 7 に固定して絶対位置を
     40 通り動かした内積の幅が **1.11e-15**。
  7. **GQA の両端は厳密に既存の 2 つ。** `n_kv_heads == n_heads` で MHA、
     `== 1` で MQA と **0.0e+00** で一致し、中間(`n_kv_heads=2`)は
     どちらとも **0.942** 違う。「中間を取る」という主張が端で検算できる。

★外した予言をもう 1 つ残してある: online softmax の**途中の状態**が答えに単調に
近づくと読んだが、**単調ではない**(0.10 / 0.17 / 0.19 / 0.15 / 0.11 / 0.07 /
0.02 / 0.00 と上がってから下がる)—— 走っている最大値が更新されるたびに分母が
組み替わるので、途中の値は答えの近似ですらない。
**「途中経過が答えに近い」は online アルゴリズムの一般則ではない。**

ほかに絵の側の所見が 2 つ: **注意は凸結合なので値域を出ない**が(出力
[0.474, 0.502] ⊂ 入力 [0.025, 1.000])、**同時に幅が 35.4 倍に潰れる** ——
平均は対比を消す。そして**最大値を引くのは飾りではない**: スコアを大きくすると
素の `exp` は 64 行のうち **15 行**が inf/NaN になり、引けば 0 行になる。

★**新しい op を 10 本足した**(族 `llmcore`)。**torch は使っていない** ——
CI は torch を一部の Python にしか入れないので、任意依存を要る PoC は
環境によって落ちる(2026-09-24 に実際に落として学んだ)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

L = fs.ledger
_PASS = []

_INK = (0.10, 0.12, 0.18)
#: 注意の重みの色。暗部から明部へ —— 赤と緑は対にしない
_ATTN = [(0.0, (0.05, 0.06, 0.16)), (0.35, (0.14, 0.30, 0.56)),
         (0.70, (0.52, 0.62, 0.80)), (1.0, (1.00, 0.97, 0.90))]


def check(ok, label, detail=""):
    _PASS.append((bool(ok), label, detail))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label,
                            ("---- " + detail) if detail else ""))


def rel(a, b):
    """相対差(最大絶対差 ÷ 基準の最大絶対値)。"""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    return float(np.max(np.abs(a - b)) / max(np.max(np.abs(b)), 1e-300))


# --------------------------------------------------------------------------- #
# 画像 → パッチ列                                                               #
# --------------------------------------------------------------------------- #
def scene(size=64):
    """滑らかな縞と 2 つの塊。★一様乱数にしない —— 構造が無いと注意が全行一様になる。"""
    y, x = np.mgrid[0:size, 0:size].astype(float)
    img = 0.45 + 0.28 * np.sin(x / 5.0) * np.cos(y / 7.0)
    for cy, cx, r, amp in ((18.0, 20.0, 9.0, 0.45), (46.0, 44.0, 7.0, -0.38)):
        img = img + amp * np.exp(-((y - cy) ** 2 + (x - cx) ** 2) / (2.0 * r * r))
    return np.clip(img, 0.0, 1.0)


def to_patches(img, patch=8):
    """(H, W) → (T, patch²) のトークン列。T = (H/patch)·(W/patch)。"""
    h, w = img.shape
    ny, nx = h // patch, w // patch
    return img.reshape(ny, patch, nx, patch).transpose(0, 2, 1, 3).reshape(ny * nx, patch * patch)


def from_patches(tok, patch=8, grid=8):
    """(T, patch²) → (H, W)。``to_patches`` の逆。"""
    return tok.reshape(grid, grid, patch, patch).transpose(0, 2, 1, 3).reshape(grid * patch, grid * patch)


def project(tok, seed, width=32):
    """パッチ列を線形写像で (T, width) に。学習しない —— 固定の乱数射影。"""
    rng = np.random.default_rng(seed)
    return tok @ (rng.normal(size=(tok.shape[1], width)) / np.sqrt(tok.shape[1]))


# --------------------------------------------------------------------------- #
# 検査                                                                          #
# --------------------------------------------------------------------------- #
def run_checks():
    t0 = time.time()
    out = {}
    img = scene()
    tok = to_patches(img)
    t = tok.shape[0]
    q, k = project(tok, 1), project(tok, 2)
    v = tok
    out["img"], out["tok"], out["q"], out["k"], out["v"] = img, tok, q, k, v

    print("\n【1】注意の重みは確率分布で、疎さは整数で数えられる")
    s = L.attention_scores(q, k)
    w_full = L.attention_weights(s)
    w_cau = L.attention_weights(s, "causal")
    w_win = L.attention_weights(s, "window", window=9)
    out["w"] = (w_full, w_cau, w_win)
    out["rowsum"] = float(np.max(np.abs(w_full.sum(1) - 1.0)))
    check(out["rowsum"] < 1e-12, "行和が 1", "ずれ最大 %.2e" % out["rowsum"])
    cm = np.tril(np.ones((t, t), bool))
    check(np.max(np.abs(w_cau[~cm])) == 0.0, "★mask 位置が厳密に 0",
          "%.1e —— 許容差の要らない 0" % np.max(np.abs(w_cau[~cm])))
    tri = t * (t + 1) // 2
    win_truth = sum(min(i + 1, 9) for i in range(t))
    out["tri"], out["win"] = tri, win_truth
    check(int((w_cau > 0).sum()) == tri, "★因果の非ゼロ数が T(T+1)/2 と一致(整数)",
          "%d 個 —— 浮動小数の許容差が要らない" % tri)
    check(int((w_win > 0).sum()) == win_truth, "★窓の非ゼロ数が Σ min(i+1,W) と一致(整数)",
          "%d 個(W=9, T=%d)" % (win_truth, t))
    check(rel(L.attention_apply(w_full, v), L.attention_softmax(q, k, v)) == 0.0,
          "3 段に分けても一括と同じ", "スコア→重み→混ぜる の経路が一致")

    print("\n【2】最大値を引くのは飾りではない")
    big = L.attention_scores(q * 16.0, k * 16.0, scale=1.0)
    with np.errstate(over="ignore", invalid="ignore"):
        naive = np.exp(big) / np.exp(big).sum(1, keepdims=True)
    stable = L.attention_weights(big)
    n_bad = int((~np.isfinite(naive)).any(1).sum())
    out["naive_bad"], out["naive_max"] = n_bad, float(np.max(big))
    check(n_bad > 0 and np.isfinite(stable).all(),
          "★素の exp は %d / %d 行が壊れ、最大値を引けば 0 行" % (n_bad, t),
          "スコアの最大 %.1f —— exp(709) で倍精度の上限" % np.max(big))

    print("\n【3】FlashAttention は近似ではない")
    full = L.attention_softmax(q, k, v)
    tiles = [1, 2, 4, 8, 16, 32, 64]
    errs = [rel(L.attention_tiled(q, k, v, tile=tl), full) for tl in tiles]
    out["tiles"], out["tile_errs"] = tiles, errs
    out["tiled_worst"] = max(errs)
    check(max(errs) < 1e-13, "★タイルの大きさを %d 通り振っても一括と一致"
          % len(tiles), "最悪 %.2e(タイル %d 行〜%d 行)" % (max(errs), tiles[0], tiles[-1]))
    n_tiles = [-(-t // tl) for tl in tiles]
    out["n_tiles"] = n_tiles
    grow = errs[0] / errs[-1] if errs[-1] > 0 else float("inf")
    out["tile_grow"] = grow
    check(grow < 10.0, "★外した予言: 誤差はタイル数に比例して積もる",
          "%d 枚 %.2e vs %d 枚 %.2e —— %.1f 倍にしかならない"
          % (n_tiles[0], errs[0], n_tiles[-1], errs[-1], grow))
    fc = L.attention_softmax(q, k, v, "causal")
    e_cau = rel(L.attention_tiled(q, k, v, tile=8, mask="causal"), fc)
    check(e_cau < 1e-13, "因果マスクつきでも一致", "%.2e" % e_cau)

    print("\n【4】線形 Attention は結合則そのもの")
    assoc = rel(L.attention_linear(q, k, v), (q @ k.T) @ v)
    out["assoc"] = assoc
    check(assoc < 1e-12, "★(QKᵀ)V == Q(KᵀV)", "%.2e —— 同じ数の別の括り方" % assoc)
    lin_c = L.attention_linear(q, k, v, causal=True)
    ref_c = (np.tril(np.ones((t, t))) * (q @ k.T)) @ v
    check(rel(lin_c, ref_c) < 1e-12, "因果つきの累積状態も一致", "%.2e" % rel(lin_c, ref_c))

    d2 = 64
    rng = np.random.default_rng(3)
    ts, quad, lino = [], [], []
    for tt in (64, 128, 256, 512, 1024, 2048):
        qq = rng.normal(size=(tt, d2))
        kk = rng.normal(size=(tt, d2))
        vv = rng.normal(size=(tt, d2))
        a = time.perf_counter()
        for _ in range(3):
            (qq @ kk.T) @ vv
        b = time.perf_counter()
        for _ in range(3):
            qq @ (kk.T @ vv)
        c = time.perf_counter()
        ts.append(tt)
        quad.append((b - a) / 3 * 1e3)
        lino.append((c - b) / 3 * 1e3)
    ratios = [x / max(y, 1e-9) for x, y in zip(quad, lino)]
    out["ts"], out["quad"], out["lino"], out["ratios"] = ts, quad, lino, ratios
    out["ratio_2048"] = ratios[-1]
    check(ratios[0] < 2.0 and ratios[-2] > 3.0,
          "★交差点は T == d(=%d)" % d2,
          "T=64 で比 %.1f / T=1024 で %.1f" % (ratios[0], ratios[-2]))
    check(ratios[-1] < 32.0 * 0.75,
          "★外した予言: 比は T/d に沿って 32 倍まで育つ",
          "T=2048 の実測は %.1f 倍 —— 二次の側が帯域律速で頭打ち" % ratios[-1])

    print("\n【5】未来を書き換えても、前の出力は 1 ビットも動かない")
    cut = t // 2
    rng2 = np.random.default_rng(5)
    k2, v2 = k.copy(), v.copy()
    k2[cut:] = rng2.normal(size=(t - cut, k.shape[1]))
    v2[cut:] = rng2.normal(size=(t - cut, v.shape[1]))
    fc2 = L.attention_softmax(q, k2, v2, "causal")
    before = float(np.max(np.abs(fc[:cut] - fc2[:cut])))
    after = float(np.max(np.abs(fc[cut:] - fc2[cut:])))
    out["cut"], out["fut_before"], out["fut_after"] = cut, before, after
    out["row_diff"] = np.max(np.abs(fc - fc2), axis=1)
    check(before == 0.0 and after > 1e-3,
          "★%d 行目から先を別の乱数に差し替え" % cut,
          "前半 %.1e(厳密に 0)/ 後半 %.3f(動くべき)" % (before, after))
    inc = np.vstack([L.kv_cache_decode(q[i:i + 1], k[:i + 1], v[:i + 1]) for i in range(t)])
    kv = rel(inc, fc)
    out["kv"] = kv
    check(kv < 1e-13, "KV Cache: 1 行ずつ進めても一括と一致", "%.2e" % kv)

    print("\n【6】位置符号が無ければ、注意はパッチの順番を見ていない")
    perm = np.random.default_rng(9).permutation(t)
    inv = np.argsort(perm)
    o_perm = L.attention_softmax(q[perm], k[perm], v[perm])
    e_perm = float(np.max(np.abs(o_perm[inv] - full)))
    qr, kr = L.rope_rotate(q), L.rope_rotate(k)
    o_rope = L.attention_softmax(qr, kr, v)
    o_rope_p = L.attention_softmax(L.rope_rotate(q[perm]), L.rope_rotate(k[perm]), v[perm])
    e_rope = float(np.max(np.abs(o_rope_p[inv] - o_rope)))
    out["perm"], out["perm_rope"] = e_perm, e_rope
    out["perm_imgs"] = (from_patches(full), from_patches(o_perm[inv]),
                        from_patches(o_rope), from_patches(o_rope_p[inv]))
    check(e_perm < 1e-12 and e_rope > 1e-3,
          "★並べ替えて戻すと元に戻る(位置符号なし)",
          "%.1e ―― RoPE を入れると %.3f" % (e_perm, e_rope))

    print("\n【7】RoPE は回転なので、保つものが 2 つある")
    n0 = np.linalg.norm(q, axis=1)
    n1 = np.linalg.norm(qr, axis=1)
    rope_norm = float(np.max(np.abs(n1 - n0)))
    vals = [float(L.rope_rotate(q[0][None, :], positions=[10 + sh])[0]
                  @ L.rope_rotate(k[0][None, :], positions=[3 + sh])[0]) for sh in range(40)]
    rope_rel = float(max(vals) - min(vals))
    out["rope_norm"], out["rope_rel"] = rope_norm, rope_rel
    out["rope_vals"] = np.asarray(vals)
    out["rope_n0"], out["rope_n1"] = n0, n1
    check(rope_norm < 1e-12, "★ノルムを厳密に保つ", "%.2e(%d 本)" % (rope_norm, t))
    check(rope_rel < 1e-12, "★内積は相対位置だけで決まる",
          "位置の差 7 を固定して絶対位置 40 通り、幅 %.2e" % rope_rel)

    print("\n【8】GQA の両端は厳密に既存の 2 つ")
    nh, dh = 4, 8
    vq = project(tok, 4, width=nh * dh)
    g_mha = L.attention_grouped(q, k, vq, nh, nh)
    ref_mha = np.concatenate([L.attention_softmax(q[:, h * dh:(h + 1) * dh],
                                                  k[:, h * dh:(h + 1) * dh],
                                                  vq[:, h * dh:(h + 1) * dh])
                              for h in range(nh)], axis=1)
    g_mqa = L.attention_grouped(q, k[:, :dh], vq[:, :dh], nh, 1)
    ref_mqa = np.concatenate([L.attention_softmax(q[:, h * dh:(h + 1) * dh],
                                                  k[:, :dh], vq[:, :dh])
                              for h in range(nh)], axis=1)
    e_mha = float(np.max(np.abs(g_mha - ref_mha)))
    e_mqa = float(np.max(np.abs(g_mqa - ref_mqa)))
    g_gqa = L.attention_grouped(q, k[:, :2 * dh], vq[:, :2 * dh], nh, 2)
    mid = float(np.max(np.abs(g_gqa - g_mqa)))
    out["mha"], out["mqa"], out["gqa_mid"] = e_mha, e_mqa, mid
    check(e_mha == 0.0 and e_mqa == 0.0, "★n_kv_heads を両端に振ると MHA / MQA と厳密一致",
          "%.1e / %.1e" % (e_mha, e_mqa))
    check(mid > 1e-3, "中間(n_kv_heads=2)は両端のどちらとも違う", "MQA との差 %.3f" % mid)

    print("\n【9】RMS 正規化は、出力の RMS を厳密に 1 にする")
    y = L.rms_norm(q)
    rms = np.sqrt(np.mean(y * y, axis=1))
    y_eps = L.rms_norm(q, eps=1e-6)
    rms_eps = np.sqrt(np.mean(y_eps * y_eps, axis=1))
    out["rms"] = float(np.max(np.abs(rms - 1.0)))
    out["rms_eps"] = float(np.max(np.abs(rms_eps - 1.0)))
    check(out["rms"] < 1e-12, "★RMS が厳密に 1", "%.2e" % out["rms"])
    check(out["rms_eps"] > out["rms"], "eps を入れると 1 からずれる(それが eps の値段)",
          "%.2e" % out["rms_eps"])

    print("\n【10】注意は凸結合 —— 値域を出ないが、同時に対比を潰す")
    lo, hi = float(v.min()), float(v.max())
    olo, ohi = float(full.min()), float(full.max())
    out["range"] = (lo, hi, olo, ohi)
    out["contrast"] = (hi - lo) / max(ohi - olo, 1e-12)
    check(olo >= lo - 1e-12 and ohi <= hi + 1e-12, "出力は入力の値域を出ない",
          "[%.3f, %.3f] ⊂ [%.3f, %.3f]" % (olo, ohi, lo, hi))
    check(out["contrast"] > 2.0, "★同時に幅が縮む —— 平均は対比を潰す",
          "幅 %.3f → %.3f(%.1f 倍に潰れる)" % (hi - lo, ohi - olo, out["contrast"]))

    print("\n【11】★外した予言: online softmax の途中経過は答えに近づいていく")
    part_errs = []
    for j in range(1, 9):
        part = L.attention_tiled(q, k[:j * 8], v[:j * 8], tile=8)
        part_errs.append(rel(part, full))
    mono = all(part_errs[i] >= part_errs[i + 1] for i in range(len(part_errs) - 1))
    out["part_errs"], out["mono"] = part_errs, mono
    check(not mono, "★単調ではない(予言を外した)",
          "途中の相対差 " + " / ".join("%.2f" % e for e in part_errs))

    print("\n【12】fail-closed —— どの入口も op 名を名乗って止まる")
    cases = [
        ("rms_norm", lambda: L.rms_norm(np.zeros((3, 4))), "全 0 の行"),
        ("rope_rotate", lambda: L.rope_rotate(np.ones((4, 5))), "d が奇数"),
        ("attention_apply", lambda: L.attention_apply(np.ones((3, 3)), np.ones((3, 2))),
         "行和が 1 でない重み"),
        ("attention_softmax", lambda: L.attention_softmax(q, k, v[:3]), "長さの不一致"),
        ("attention_weights", lambda: L.attention_weights(s, "bogus"), "未知の mask"),
        ("attention_grouped", lambda: L.attention_grouped(q, k, vq, 3, 2), "頭数が倍数でない"),
        ("attention_tiled", lambda: L.attention_tiled(q, k, v, tile=0), "tile=0"),
        ("kv_cache_decode", lambda: L.kv_cache_decode(q, k, v), "1 行でない問い合わせ"),
    ]
    named = 0
    for op, fn, why in cases:
        try:
            fn()
            print("      通ってしまった: %s" % why)
        except ValueError as exc:
            if str(exc).startswith(op + ":"):
                named += 1
    out["named"] = named
    check(named == len(cases), "★%d 通りの誤りが全部 op 名を名乗って止まる" % len(cases),
          "「どの op が何を拒んだか」が読める")

    check(not fs.fallbacks(), "静かな代替実装に落ちていない",
          "fallbacks() は空 —— 数字はすべて本来の経路")
    out["t"] = t
    return t0, out


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def tone(a, stops=_ATTN, q_hi=0.999):
    """asinh で持ち上げてから色に。★狭義単調なので画素の大小は入れ替わらない。"""
    a = np.asarray(a, float)
    hi = float(np.quantile(a, q_hi))
    if hi <= 0:
        hi = float(np.max(a)) or 1.0
    u = np.arcsinh(a / (0.05 * hi)) / np.arcsinh(1.0 / 0.05)
    u = np.clip(u, 0.0, 1.0)
    return ramp(u, stops)


def ramp(u, stops):
    u = np.clip(np.asarray(u, float), 0.0, 1.0)
    out = np.zeros(u.shape + (3,))
    for (t0, c0), (t1, c1) in zip(stops[:-1], stops[1:]):
        m = (u >= t0) & (u <= t1)
        if not m.any():
            continue
        f = (u[m] - t0) / max(t1 - t0, 1e-12)
        for c in range(3):
            out[..., c][m] = c0[c] + (c1[c] - c0[c]) * f
    return out


def upscale(a, k):
    return np.repeat(np.repeat(a, k, axis=0), k, axis=1)


def draw_figures(out):
    t = out["t"]
    w_full, w_cau, w_win = out["w"]
    k = max(1, 320 // t)

    figs.save_grid("attention_masks",
                   [upscale(tone(w_full), k), upscale(tone(w_cau), k),
                    upscale(tone(w_win), k)],
                   ["全対(%d² = %d)" % (t, t * t),
                    "因果 —— 非ゼロ %d = T(T+1)/2" % out["tri"],
                    "窓 W=9 —— 非ゼロ %d = Σmin(i+1,W)" % out["win"]],
                   title="同じスコアに 3 通りのマスク", ncols=3,
                   caption=("行が問い合わせ、列が引かれる側。**マスクした位置は厳密に 0** で、"
                            "残った非ゼロの個数は**閉形式の整数と一致する** —— "
                            "浮動小数の許容差が要らない主張。"))

    figs.save_plot("tiled_exactness",
                   [("タイル + online softmax", np.asarray(out["n_tiles"], float),
                     np.asarray(out["tile_errs"]) * 1e16)],
                   xlabel="タイルの枚数", ylabel="一括との相対差 [×1e-16]",
                   title="FlashAttention は近似ではない",
                   kinds=["scatter"],
                   caption=("縦軸は **1e-16 単位**。タイルを %d 枚に割っても相対差は "
                            "**%.1e** —— 近似ではなく、同じ和を別の順で足しているだけ。"
                            "★外した予言: 誤差はタイル数に比例して積もる → "
                            "**%d 倍のタイル数で %.1f 倍**にしかならない。"
                            % (max(out["n_tiles"]), out["tiled_worst"],
                               max(out["n_tiles"]) // max(min(out["n_tiles"]), 1),
                               out["tile_grow"])))

    figs.save_plot("linear_crossover",
                   [("二次 (QK^T)V", np.asarray(out["ts"], float), np.asarray(out["quad"])),
                    ("線形 Q(K^T V)", np.asarray(out["ts"], float), np.asarray(out["lino"]))],
                   xlabel="列の長さ T", ylabel="1 回あたり [ms]",
                   title="同じ答えを出す 2 つの括り方",
                   caption=("**答えは同じ**(相対差 %.1e)。違うのは括り方だけで、"
                            "交差点は **T == d = 64**。★予言は途中で外れる —— "
                            "比は T/d に沿って育つが、T=2048 では式が言う 32 倍でなく "
                            "**%.1f 倍**で頭打ちになる(二次の側が帯域律速)。"
                            % (out["assoc"], out["ratio_2048"])))

    figs.save_plot("future_rewrite",
                   [("行ごとの出力の変化", np.arange(t, dtype=float), out["row_diff"])],
                   xlabel="トークンの位置", ylabel="出力の最大変化",
                   title="%d 行目から先の key/value を別の乱数に差し替えた" % out["cut"],
                   kinds=["bar"],
                   caption=("左半分は**厳密に 0**(%.1e)、右半分は **%.3f** 動く。"
                            "「未来を見ていない」は同義反復ではなく、"
                            "**実際に未来を壊して測った結果**。KV Cache が成り立つ根拠がこれで、"
                            "1 行ずつ進めた結果は一括と **%.1e**。"
                            % (out["fut_before"], out["fut_after"], out["kv"])))

    p0, p1, p2, p3 = out["perm_imgs"]
    figs.save_grid("patch_shuffle",
                   [out["img"], p0, p1, p2, p3],
                   ["元の絵", "注意で混ぜた絵", "パッチを並べ替えて戻した絵",
                    "RoPE つき", "RoPE つきで並べ替えて戻した絵"],
                   title="位置符号が無いと、注意はパッチの順番を見ていない", ncols=5,
                   gray=True,
                   caption=("2 枚目と 3 枚目は**差 %.1e** —— パッチを並べ替えてから戻すと"
                            "元に戻る(置換同変)。4 枚目と 5 枚目は **%.3f** 違う。"
                            "**それが位置符号の仕事**で、絵で見ると「同じ絵」と「別の絵」になる。"
                            % (out["perm"], out["perm_rope"])))

    figs.save_plot("rope_invariants",
                   [("位置の差 7 を固定した内積", np.arange(len(out["rope_vals"]), dtype=float),
                     out["rope_vals"])],
                   xlabel="絶対位置の下駄", ylabel="回した 2 本の内積",
                   title="RoPE が保つもの", kinds=["scatter"],
                   caption=("位置の差だけを 7 に固定して**絶対位置を 40 通り**動かしても、"
                            "内積の幅は **%.1e**。ノルムのほうも %d 本すべてで "
                            "**%.1e** しか動かない —— 回転だから。"
                            % (out["rope_rel"], t, out["rope_norm"])))

    figs.save_plot("rope_norm",
                   [("回す前", np.arange(t, dtype=float), out["rope_n0"]),
                    ("回した後", np.arange(t, dtype=float), out["rope_n1"])],
                   xlabel="トークンの位置", ylabel="行のノルム",
                   title="回転はノルムを動かさない", kinds=["line", "scatter"],
                   caption=("2 本の線は %d 本すべてで重なる(最大差 **%.1e**)。"
                            "RoPE は平面回転の直和なので、**保存量が閉形式で分かる**。"
                            % (t, out["rope_norm"])))

    figs.save_plot("online_partial",
                   [("途中の相対差", np.arange(1, len(out["part_errs"]) + 1, dtype=float),
                     np.asarray(out["part_errs"]))],
                   xlabel="足したタイルの枚数", ylabel="最終の答えとの相対差",
                   title="★外した予言: 途中経過は答えに近づいていく", kinds=["bar"],
                   caption=("**単調ではない**。走っている最大値が更新されるたびに分母が"
                            "組み替わるので、途中の値は答えの近似ですらない —— "
                            "「途中経過が答えに近い」は online アルゴリズムの一般則ではない。"))

    lo, hi, olo, ohi = out["range"]
    mixed = from_patches(L.attention_softmax(out["q"], out["k"], out["v"]))
    figs.save_grid("convex_mixing",
                   [out["img"], mixed, (mixed - mixed.min()) / max(float(np.ptp(mixed)), 1e-12)],
                   ["元の絵(幅 %.3f)" % (hi - lo),
                    "注意で混ぜた絵(同じ目盛り、幅 %.3f)" % (ohi - olo),
                    "同じ絵を伸ばし直したもの"],
                   title="注意は凸結合 —— 値域は出ないが、対比は潰れる", ncols=3,
                   gray=True,
                   caption=("行和が 1 なので出力は入力の凸結合で、値域 [%.3f, %.3f] を"
                            "出ない。**同時に幅が %.1f 倍に潰れる** —— 平均は対比を消す。"
                            "3 枚目で伸ばし直すと、何が残ったかが見える。"
                            % (lo, hi, out["contrast"])))

    rows = [
        ["注意の行和", "1", "ずれ %.1e" % out["rowsum"], "%d 行" % t],
        ["マスク位置の重み", "0", "0.0e+00", "厳密"],
        ["因果の非ゼロ数", "T(T+1)/2 = %d" % out["tri"], "%d" % out["tri"], "整数で一致"],
        ["窓の非ゼロ数", "Σ min(i+1,W) = %d" % out["win"], "%d" % out["win"], "整数で一致"],
        ["タイル + online softmax", "一括と同じ", "最悪 %.1e" % out["tiled_worst"],
         "%d 通りのタイル" % len(out["tiles"])],
        ["★タイル数で誤差が積もる", "比例するはず", "%.1f 倍" % out["tile_grow"],
         "外した予言"],
        ["(QK^T)V == Q(K^T V)", "0", "%.1e" % out["assoc"], "結合則"],
        ["線形との速度比 (T=1024)", "T/d = 16", "%.1f 倍" % out["ratios"][-2], "ほぼ式どおり"],
        ["★同 (T=2048)", "T/d = 32", "%.1f 倍" % out["ratio_2048"], "外した予言(帯域律速)"],
        ["未来を書き換えたときの前半", "0", "%.1e" % out["fut_before"], "後半は %.3f" % out["fut_after"]],
        ["KV Cache の逐次", "一括と同じ", "%.1e" % out["kv"], "%d 歩" % t],
        ["置換同変(位置符号なし)", "0", "%.1e" % out["perm"], "RoPE で %.3f" % out["perm_rope"]],
        ["RoPE のノルム保存", "0", "%.1e" % out["rope_norm"], "回転だから"],
        ["RoPE の相対位置", "0", "%.1e" % out["rope_rel"], "絶対位置 40 通り"],
        ["GQA == MHA / MQA", "0", "%.1e / %.1e" % (out["mha"], out["mqa"]), "両端で厳密"],
        ["RMS 正規化", "1", "ずれ %.1e" % out["rms"], "eps=1e-6 で %.1e" % out["rms_eps"]],
        ["注意で潰れる対比", "-", "%.1f 倍" % out["contrast"], "凸結合の代償"],
        ["★途中経過は単調に近づく", "単調のはず", "単調でない", "外した予言"],
        ["素の exp が壊す行", "-", "%d / %d 行" % (out["naive_bad"], t), "最大値を引けば 0"],
        ["op 名を名乗る誤り", "%d 通り" % out["named"], "%d 通り" % out["named"], "全部"],
    ]
    figs.save_table("numbers", ["量", "閉形式・真値", "実測", "備考"], rows,
                    title="この回の数字",
                    caption=("実測はすべて新族 **`llmcore`(10 op)**が返したもの。"
                             "**torch は使っていません。**"))


def main():
    t0, out = run_checks()
    if figs.enabled():
        draw_figures(out)
        errs = figs.errors()
        assert not errs, errs

    ok = sum(1 for v, _, _ in _PASS)
    good = sum(1 for v, _, _ in _PASS if v)
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (ok, good, time.time() - t0))
    if good != ok:
        for v, label, detail in _PASS:
            if not v:
                print("  NG: %s ---- %s" % (label, detail))
        return 1
    # ★門 tests/test_poc_scripts_run.py は exit 0 だけでなく PASS の印字も見る。
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
