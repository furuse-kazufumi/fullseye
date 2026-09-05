# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""行列分解が「なぜか遅い」ときに最初に疑うところ — BLAS のスレッド数。

多コア機で SVD を含む処理が遅いとき、原因はアルゴリズムではなく **BLAS の
使われ方**であることが多い。OpenBLAS も MKL も既定でスレッド数を論理 CPU 数から
決めるが、**LAPACK の分解ではそれが速くならない**。分解の中の行列積が小さすぎて、
スレッドを起こして同期する費用のほうが高くつく。

このサンプルは 2 つのことをする:

  1. Fullseye の op(``dc_rpca_lowrank``)で、上限を掛けた場合と掛けない場合を
     測って**自分の機械の数字**を出す。ライブラリ側は既定で絞っているので、
     ここでは ``FULLSEYE_BLAS_THREADS=off`` で「掛けない状態」を再現する。
  2. **自分で書いた numpy コード**を ``fullseye.blas_threads`` で囲む。
     ライブラリ内部の対策はここまで届かないので、利用者が自分で塞ぐ。

実行::

    py -3.11 examples/blas_thread_budget.py

★ このサンプルは**速さを assert しない**。倍率は機械（コア数・BLAS の版・
熱の状態・他の負荷）で変わるので、閾値で判定すると別の機械で意味なく落ちる。
assert するのは「結果が一致すること」だけで、速さは測って**印字する**。
参考値(24 論理 CPU / OpenBLAS 0.3.31 / Windows): op が 4.04 倍、自前 SVD が 3.9 倍。

EXTEND: 自分の処理に当てはめるなら、行列の**短辺**を見ること。``16384x3`` の
最小二乗は「大きい行列」ではなく幅 3 の QR で、絞ると逆に遅くなる。判断の表と
実測は ``docs/ops/math/guides/blas_threads_and_memory.md``。
"""
from __future__ import annotations

import os
import statistics
import sys
import time

import numpy as np

# examples/ から親ディレクトリの Fullseye モジュールを使う定型
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs                                             # noqa: E402
import fsthreads                                                  # noqa: E402

SIZE = 192          # EXTEND: 画像を大きくしても RPCA は内部で 64x64 に落として解く
REPEAT = 5          # 中央値をとる回数。最小値ではなく中央値(常用の速さを表すため)


def structured_image(n):
    """構造のある入力。乱数だけだと低ランク成分が無く、RPCA の仕事が変わる。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    noise = 0.03 * np.random.default_rng(20260906).standard_normal((n, n))
    return np.clip(0.35 * grad + 0.45 * disk + checker + noise, 0.0, 1.0)


def median_time(fn, repeat=REPEAT):
    fn()                                            # 1 回捨てる(初回は確保が混ざる)
    return statistics.median(_timed(fn) for _ in range(repeat))


def _timed(fn):
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0


def main():
    print("=" * 70)
    print("BLAS スレッド上限 — 行列分解が速くなる/遅くなる境目")
    print("=" * 70)

    n_threads = fsthreads.current_threads()
    print(f"\n[0] この機械の BLAS スレッド数 = {n_threads}  "
          f"(上限を掛けられる: {fsthreads.available()})")
    if not fsthreads.available() or (n_threads or 1) < 2:
        print("    単コア相当の環境なので、以下の差はほぼ出ない(それが正しい挙動)。")

    # ---------------------------------------------------------------- #
    # 1) Fullseye の op —— ライブラリ側は既定で絞っている
    # ---------------------------------------------------------------- #
    img = structured_image(SIZE)

    def run_op():
        return fs.apply(img, "dc_rpca_lowrank", 0.5, 0.5)

    os.environ["FULLSEYE_BLAS_THREADS"] = "off"        # 修正前を再現
    t_off = median_time(run_op)
    out_off = run_op()
    os.environ["FULLSEYE_BLAS_THREADS"] = "auto"       # 既定(段数表で絞る)
    t_on = median_time(run_op)
    out_on = run_op()
    os.environ.pop("FULLSEYE_BLAS_THREADS", None)

    print(f"\n[1] op dc_rpca_lowrank ({SIZE}x{SIZE}) —— 内部で 64x64 の SVD を最大 60 回")
    print(f"    絞らない  {t_off * 1e3:8.1f} ms")
    print(f"    絞る      {t_on * 1e3:8.1f} ms   ({t_off / max(t_on, 1e-12):.2f} 倍)")

    diff = float(np.max(np.abs(out_off - out_on)))
    print(f"    結果の最大差 {diff:.3e}  (浮動小数の下位ビットのみ。"
          f"スレッド数で縮約の順序が変わるため)")
    assert diff < 1e-9, f"結果が実質的に変わっている: {diff}"
    assert out_off.shape == img.shape

    # ---------------------------------------------------------------- #
    # 2) 自分で書いた numpy —— ライブラリ内部の対策は**ここまで届かない**
    # ---------------------------------------------------------------- #
    rng = np.random.default_rng(0)
    mats = [rng.standard_normal((96, 96)) for _ in range(30)]

    def my_own_svd():
        return [np.linalg.svd(m, compute_uv=False) for m in mats]

    def my_own_svd_capped():
        # ★ここが要点。96x96 は「小さいから速い」のではなく、
        #   **小さいからこそ多スレッドが損**になる大きさ。ループの**外**に 1 回置く
        #   (1 回ごとに囲むと、絞る仕掛け自体の費用を 30 回払うことになる)。
        with fs.blas_threads(1):
            return [np.linalg.svd(m, compute_uv=False) for m in mats]

    t_plain = median_time(my_own_svd)
    t_capped = median_time(my_own_svd_capped)
    print(f"\n[2] 自前の numpy —— 96x96 の特異値を 30 回")
    print(f"    そのまま  {t_plain * 1e3:8.1f} ms")
    print(f"    絞る      {t_capped * 1e3:8.1f} ms   "
          f"({t_plain / max(t_capped, 1e-12):.2f} 倍)")
    sv_plain, sv_capped = my_own_svd(), my_own_svd_capped()
    sv_diff = max(float(np.max(np.abs(a - b))) for a, b in zip(sv_plain, sv_capped))
    print(f"    特異値の最大差 {sv_diff:.3e}")
    assert sv_diff < 1e-10, f"特異値が変わっている: {sv_diff}"

    # ---------------------------------------------------------------- #
    # 3) 絞ってはいけない側 —— 行列積は逆にスレッドで速くなる
    # ---------------------------------------------------------------- #
    big = rng.standard_normal((768, 768))
    t_gemm = median_time(lambda: big @ big, 3)
    with fs.blas_threads(1):
        t_gemm_1 = median_time(lambda: big @ big, 3)
    print(f"\n[3] 行列積 768x768 —— **これは絞ってはいけない**")
    print(f"    そのまま  {t_gemm * 1e3:8.1f} ms")
    print(f"    1 スレッド {t_gemm_1 * 1e3:8.1f} ms   "
          f"({t_gemm_1 / max(t_gemm, 1e-12):.2f} 倍 = 絞ると遅い)")
    print("    → だから Fullseye はプロセス全体ではなく**分解の周りだけ**を絞る。")

    # ---------------------------------------------------------------- #
    # 4) 短辺で決まる —— 縦長行列は「大きい行列」ではない
    # ---------------------------------------------------------------- #
    print(f"\n[4] 上限は行列の**短辺**で決まる(下限 {fsthreads.MIN_N})")
    for shape in ((16384, 3), (64, 64), (600, 600), (2048, 2048)):
        n = fsthreads.short_side(np.empty(shape, dtype=np.float32))
        cap = fsthreads.cap_for(n)
        verdict = "触らない" if cap is None else f"{cap} スレッドまで"
        print(f"    {str(shape):>14s}  短辺 {n:5d} -> {verdict}")
    assert fsthreads.cap_for(fsthreads.short_side(np.empty((16384, 3)))) is None, \
        "縦長行列を『大きい行列』と数えてはいけない"

    print("\n" + "=" * 70)
    print("PASS — 上限の有無で結果は一致し、速さだけが変わる")
    print("       (倍率は機械で変わる。閾値で判定していないのはそのため)")
    print("=" * 70)


if __name__ == "__main__":
    main()
