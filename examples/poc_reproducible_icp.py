# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""点の順を入れ替えても 1 ビットも動かない位置合わせ —— Ozaki スキームの FP64 の縮約。誤差は段で落ち、上界で保証する(2026-10-05)。

同じ 20 万点の点群を、点の順だけ入れ替えて Kabsch の回転を解く。普通の FP64 の行列積(DGEMM)は足す順で下位ビットが動くので、
回転は入れ替えるたびに 1e-16〜1e-15 だけ別の値になる。新モジュール ozakimm(6 op)は縮約を正確な整数の部分積に分けて計算し、
点の順・BLAS のスレッド数に依らず **同じビット** を返す。代わりに CPU では遅い(DGEMM の 15〜83 倍)。GPU で FP64 を
速くしたいなら、自前の実装でなく cuBLAS 13.4 の FP64 エミュレーション(opt-in)が速い —— 手元の測定表を描く。

何が外から来るか:
  * **正確な真値**: 行列積を Python の整数(と分数)で計算し、正確に丸めた値。階段と上界の門はこれと比べる。
  * **方式の式**: Ozaki-I(arXiv 2306.11975 の固定小数点の切り出し)と Ozaki-II(arXiv 2504.08009 の中国剰余定理)。
    定数倍で壊れない拡大の考え方は arXiv 2606.29129(旧 fast mode の欠陥の報告)。
  * **GPU の速さ**: 手元の RTX 5090 で測った cuBLAS 13.3 / 13.4 の表(examples/data の JSON。--full で GPU があれば測り直す)。

門(既定): 階段(Ozaki-I・II)、上界の破れ 0、点の順 11 通りで Ozaki は 1 通り、スレッド数 1/2/4/8 で同じビット、
2 の冪の定数倍で答えも正確に同じ倍率(2606.29129 の欠陥が無い)、Kabsch の回転の復元、fail-closed、探針が例外を出さない、
入口、所要。--full: 点を 20 万に、CPU の速さを測り、GPU があれば cuBLAS を測る。
図(既定の出力先は out/figures/<PoC 名>/、FULLSEYE_FIGURE_DIR で変更): 誤差の階段、点の順を入れ替えたときの回転の差、
同じビットか違うビットかの表、GPU の FP64 相当の速さ(記録)、CPU の遅さの表。
Run: py -3.11 examples/poc_reproducible_icp.py [--full]
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import ozakimm as om  # noqa: E402

FULL = "--full" in sys.argv
N_POINTS = 200_000 if FULL else 50_000
N_SHUFFLES = 11
RECORDED = Path(__file__).resolve().parent / "data" / "fp64_emulation_measured_2026_10_05.json"
U = 2.0 ** -53
_GATES: list[tuple[str, bool]] = []


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    except Exception as exc:  # noqa: BLE001  別の例外は fail-closed ではない
        print("    (wrong exception %s: %s)" % (type(exc).__name__, exc))
    return False


def _blas_threads(n):
    from threadpoolctl import threadpool_limits
    return threadpool_limits(n)


# ======================================================================================================================
def staircase() -> dict:
    print("== 誤差の階段(正確な真値 = Python の整数)")
    rng = np.random.default_rng(7)
    out = {"phi": [0.5, 2.0, 4.0], "oz1": {}, "oz2": {}, "dgemm": {}, "auto": {}}
    ok_mono, ok_floor, ok_auto, viol, n_checked = True, True, True, 0, 0
    for phi in out["phi"]:
        A = om._test_matrix(16, 160, phi, rng)
        B = om._test_matrix(160, 16, phi, rng)
        R = om._exact_matmul(A, B)
        den = np.abs(A) @ np.abs(B)
        e1 = [float(np.max(np.abs(om.matmul_ozaki(A, B, s) - R) / den)) for s in range(1, 15)]
        e2 = [float(np.max(np.abs(om.matmul_ozaki(A, B, s, "ozaki2") - R) / den)) for s in range(2, 21)]
        ed = float(np.max(np.abs(A @ B - R) / den))
        assert len(e1) == 14 and len(e2) == 19
        ok_mono &= all(b <= a * 1.01 + 2 * U for a, b in zip(e1, e1[1:]))
        ok_floor &= e1[-1] <= max(ed, 2 * U) and e1[0] > 1e-3
        C, info = om.matmul_ozaki(A, B, return_info=True)
        ea = float(np.max(np.abs(C - R) / den))
        ok_auto &= ea <= 4 * U
        for s in range(1, 13):
            lim = om.ozaki_error_bound(A, B, s) + (s + 1) * U * den
            viol += int(np.sum(np.abs(om.matmul_ozaki(A, B, s) - R) > lim))
            n_checked += R.size
        out["oz1"][phi], out["oz2"][phi], out["dgemm"][phi] = e1, e2, ed
        out["auto"][phi] = (info["n_slices"], ea)
        print("    φ=%.1f: 1 枚 %.1e → 14 枚 %.1e(DGEMM %.1e)、自動 %d 枚 %.1e、Ozaki-II 20 法 %.1e"
              % (phi, e1[0], e1[-1], ed, info["n_slices"], ea, e2[-1]))
    gate("門 1 階段: Ozaki-I の誤差は枚数とともに単調に落ち、14 枚で DGEMM の水準に届く(φ = 0.5 / 2 / 4)", ok_mono and ok_floor)
    gate("門 2 自動の枚数は上界から選ばれ、正確な真値との差は 4 u 以内", ok_auto,
         ", ".join("φ=%.1f→%d 枚" % (p, out["auto"][p][0]) for p in out["phi"]))
    gate("門 3 打ち切りの上界は破れない(%d 要素 × 12 枚の組)" % (n_checked // 12), viol == 0 and n_checked == 3 * 12 * 256,
         "破れ %d / %d" % (viol, n_checked))
    ok2 = all(out["oz2"][p][-1] <= max(out["dgemm"][p], 2 * U) for p in (0.5, 2.0))
    gate("門 4 Ozaki-II(中国剰余定理)も 20 法で DGEMM の水準(φ ≤ 2)", ok2,
         ", ".join("φ=%.1f %.1e" % (p, out["oz2"][p][-1]) for p in out["phi"]))
    return out


def order_and_threads() -> dict:
    print("== 点の順とスレッド数(%d 点、Kabsch)" % N_POINTS)
    rng = np.random.default_rng(10)
    P = 1000.0 + rng.normal(0, 0.5, (N_POINTS, 3))          # 原点から遠い点群(実測の座標系でよくある)
    Rt = np.linalg.qr(rng.normal(size=(3, 3)))[0]
    if np.linalg.det(Rt) < 0:
        Rt[:, 0] *= -1
    Q = P @ Rt.T + np.array([0.3, -1.2, 2.0]) + 1e-4 * rng.normal(size=(N_POINTS, 3))

    def native(Pp, Qp):
        cp, cq = Pp.mean(0), Qp.mean(0)
        U_, _, Vt = np.linalg.svd((Pp - cp).T @ (Qp - cq))
        d = 1.0 if np.linalg.det(Vt.T @ U_.T) >= 0 else -1.0
        return Vt.T @ np.diag([1.0, 1.0, d]) @ U_.T

    r_nat, r_oz, d_nat, d_oz = [], [], [], []
    for t in range(N_SHUFFLES + 1):
        p = rng.permutation(N_POINTS) if t else np.arange(N_POINTS)
        r_nat.append(native(P[p], Q[p]))
        r_oz.append(om.kabsch_reproducible(P[p], Q[p])["R"])
        if t:
            d_nat.append(float(np.max(np.abs(r_nat[-1] - r_nat[0]))))
            d_oz.append(float(np.max(np.abs(r_oz[-1] - r_oz[0]))))
    assert len(d_nat) == N_SHUFFLES and len(d_oz) == N_SHUFFLES
    n_nat = len({r.tobytes() for r in r_nat})
    n_oz = len({r.tobytes() for r in r_oz})
    gate("門 5 点の順を %d 回入れ替えても Ozaki の Kabsch は 1 通りの回転(ビット単位)" % N_SHUFFLES, n_oz == 1,
         "Ozaki %d 通り / 普通の FP64 %d 通り(最大の差 %.1e)" % (n_oz, n_nat, max(d_nat)))
    rot_err = float(np.max(np.abs(r_oz[0] - Rt)))
    gate("門 6 回転の復元(雑音 1e-4 の点群)", rot_err < 1e-6, "max |R − R_true| = %.1e" % rot_err)

    X, Y = (P - P.mean(0)).T, Q - Q.mean(0)
    h_nat, h_oz = [], []
    for n in (1, 2, 4, 8):
        with _blas_threads(n):
            h_nat.append(X @ Y)
            h_oz.append(om.matmul_reproducible(X, Y))
    t_nat = len({h.tobytes() for h in h_nat})
    t_oz = len({h.tobytes() for h in h_oz})
    gate("門 7 BLAS のスレッド数 1 / 2 / 4 / 8 で Ozaki は同じビット", t_oz == 1, "Ozaki %d 通り / 普通の FP64 %d 通り" % (t_oz, t_nat))
    rel = float(np.max(np.abs(h_oz[0] - h_nat[0])) / np.max(np.abs(h_nat[0])))
    Hc = om.cross_covariance_reproducible(P, Q)
    Hp = om.cross_covariance_reproducible(P[::-1], Q[::-1])
    same = np.array_equal(Hc, Hp) and np.array_equal(Hc, om.kabsch_reproducible(P, Q)["H"])
    gate("門 8 普通の FP64 との差は丸めの範囲(H の最大要素に対し 1e-12 未満)、相互共分散の op は逆順でも Kabsch の H と同じビット",
         rel < 1e-12 and same, "%.1e" % rel)

    ts = {}
    for name, fn in (("dgemm", lambda: X @ Y), ("ozaki", lambda: om.matmul_reproducible(X, Y))):
        fn()
        t0 = time.perf_counter()
        for _ in range(3):
            fn()
        ts[name] = (time.perf_counter() - t0) / 3
    print("    3×%d @ %d×3: 普通の FP64 %.2f ms、matmul_reproducible %.1f ms(%.0f 倍)"
          % (N_POINTS, N_POINTS, 1e3 * ts["dgemm"], 1e3 * ts["ozaki"], ts["ozaki"] / ts["dgemm"]))
    return {"d_nat": d_nat, "d_oz": d_oz, "n_nat": n_nat, "n_oz": n_oz, "t_nat": t_nat, "t_oz": t_oz, "times": ts}


def scale_and_fail_closed() -> None:
    print("== 定数倍(arXiv 2606.29129)と fail-closed")
    A, B = np.ones((16, 1024)), np.ones((1024, 16))
    ok = True
    for k in (-2, -5, -10, -20, 7):
        for f in (lambda a, b: om.matmul_ozaki(a, b, 16, "ozaki2"), lambda a, b: om.matmul_ozaki(a, b, 8),
                  om.matmul_reproducible):
            ok &= bool(np.all(f(np.ldexp(A, k), B) == np.ldexp(1024.0, k)))
    rng = np.random.default_rng(3)
    Ar, Br = om._test_matrix(8, 1024, 0.5, rng), om._test_matrix(1024, 8, 0.5, rng)
    worst = 0.0
    for c in (2.0 ** -3, 2.0 ** -5, 2.0 ** -10, 3.7):
        R = om._exact_matmul(c * Ar, Br)
        den = np.abs(c * Ar) @ np.abs(Br)
        worst = max(worst, float(np.max(np.abs(om.matmul_ozaki(c * Ar, Br, 18, "ozaki2") - R) / den)))
    gate("門 9 入力を 2 の冪倍すると答えも正確に同じ倍率、乱数行列を c = 2⁻³〜2⁻¹⁰ 倍しても精度は FP64 の水準"
         "(旧 fast mode は c ≤ 2⁻² で相対誤差 約 1 と報告されている)", ok and worst < 4 * U, "最悪 %.1e" % worst)
    M = np.ones((3, 4))
    cases = [_raises(om.matmul_ozaki, np.full((3, 4), np.nan), np.ones((4, 2))),
             _raises(om.matmul_ozaki, M, M), _raises(om.matmul_ozaki, M, np.ones((4, 2)), 0),
             _raises(om.matmul_ozaki, M, np.ones((4, 2)), True),
             _raises(om.matmul_ozaki, M, np.ones((4, 2)), 3, "ozaki3"),
             _raises(om.matmul_ozaki, M, np.ones((4, 2)), None, "ozaki2"),
             _raises(om.matmul_reproducible, np.array([[1.0, 1e-100]]), np.array([[0.0], [1e-100]])),
             _raises(om.ozaki_error_bound, M, np.ones((4, 2)), 0),
             _raises(om.kabsch_reproducible, M, M),
             _raises(om.cross_covariance_reproducible, np.ones((5, 3)), np.ones((4, 3)))]
    C, info = om.matmul_ozaki(np.array([[1.0, 1e-100]]), np.array([[0.0], [1e-100]]), on_insufficient="fallback",
                              return_info=True)
    cases.append(bool(info["fallback"]))
    gate("門 10 測れない入力は ValueError、届かない精度で float64 に戻すのは明示したときだけ(%d 通り)" % len(cases),
         len(cases) == 11 and all(cases), "通った %d / %d" % (sum(cases), len(cases)))


def probe_and_entry() -> dict:
    print("== GPU の FP64 エミュレーションの探針と入口")
    try:
        pr = om.fp64_emulation_probe()
        ok = isinstance(pr["available"], bool) and len(pr["rows"]) >= 1
    except Exception as exc:  # noqa: BLE001  探針は例外を出さない約束
        pr, ok = {"available": False, "rows": [], "error": repr(exc)}, False
    for row in pr.get("rows", []):
        print("    %s: loaded=%s version=%s emulation_api=%s gpu=%s (%s)"
              % (row["library"], row["loaded"], row["cublas_version"], row["emulation_api"], row["gpu"], row["reason"]))
    gate("門 11 探針は GPU / CUDA の有無に依らず例外を出さず表を返す", ok, "available=%s" % pr.get("available"))
    docs_ok = all(getattr(om, n).__doc__ and "](" not in getattr(om, n).__doc__ for n in om.__all__)
    gate("門 12 入口: __all__ の 6 op が実在し、docstring があり Markdown のリンク記法を含まない",
         len(om.__all__) == 6 and docs_ok)
    return pr


def cpu_speed() -> list:
    print("== CPU の速さ(--full、正方行列)")
    rng = np.random.default_rng(5)
    rows = []
    for n in (256, 512, 1024):
        A, B = om._test_matrix(n, n, 0.5, rng), om._test_matrix(n, n, 0.5, rng)
        res = {}
        for name, fn in (("dgemm", lambda: A @ B), ("ozaki1_8", lambda: om.matmul_ozaki(A, B, 8)),
                         ("ozaki2_16", lambda: om.matmul_ozaki(A, B, 16, "ozaki2"))):
            fn()
            t0 = time.perf_counter()
            for _ in range(2):
                fn()
            res[name] = (time.perf_counter() - t0) / 2
        rows.append({"n": n, **res})
        print("    n=%d: DGEMM %.2f ms、Ozaki-I 8 枚 %.0f 倍、Ozaki-II 16 法 %.0f 倍"
              % (n, 1e3 * res["dgemm"], res["ozaki1_8"] / res["dgemm"], res["ozaki2_16"] / res["dgemm"]))
    return rows


def gpu_measure(pr: dict) -> list:
    """GPU があれば cuBLAS の DGEMM をネイティブとエミュレーションで測る(ctypes だけ、失敗したら空)。"""
    import ctypes as C
    import os
    lib_path = next(r["path"] for r in pr["rows"] if r["gpu"])
    try:
        d = os.path.dirname(lib_path) if lib_path and os.path.isabs(lib_path) else ""
        if d and hasattr(os, "add_dll_directory"):
            os.add_dll_directory(d)
        rt = C.CDLL(os.path.join(d, "cudart64_13.dll") if os.name == "nt" else "libcudart.so.13")
        cb = C.CDLL(lib_path)
        h = C.c_void_p()
        if cb.cublasCreate_v2(C.byref(h)) != 0:
            return []
        cb.cublasDgemm_v2.argtypes = [C.c_void_p, C.c_int, C.c_int, C.c_int, C.c_int, C.c_int, C.POINTER(C.c_double),
                                      C.c_void_p, C.c_int, C.c_void_p, C.c_int, C.POINTER(C.c_double), C.c_void_p, C.c_int]
        rng = np.random.default_rng(3)
        out = []
        for n in (2048, 4096):
            for phi in (0.5, 4.0):
                A, B = om._test_matrix(n, n, phi, rng), om._test_matrix(n, n, phi, rng)
                ref, den = A @ B, np.abs(A) @ np.abs(B)
                ptr = []
                for X in (A, B, np.zeros((n, n))):
                    p = C.c_void_p()
                    rt.cudaMalloc(C.byref(p), C.c_size_t(X.nbytes))
                    rt.cudaMemcpy(p, np.ascontiguousarray(X).ctypes.data_as(C.c_void_p), C.c_size_t(X.nbytes), 1)
                    ptr.append(p)
                row = {"n": n, "phi": phi}
                for name, mode, strat in (("native", 0, 0), ("emul_performant", 8, 1)):
                    cb.cublasSetMathMode(h, mode)
                    cb.cublasSetEmulationStrategy(h, strat)
                    one, zero = C.c_double(1.0), C.c_double(0.0)

                    def call():
                        return cb.cublasDgemm_v2(h, 0, 0, n, n, n, C.byref(one), ptr[1], n, ptr[0], n, C.byref(zero), ptr[2], n)
                    for _ in range(3):
                        call()
                    rt.cudaDeviceSynchronize()
                    t0 = time.perf_counter()
                    for _ in range(10):
                        call()
                    rt.cudaDeviceSynchronize()
                    dt = (time.perf_counter() - t0) / 10
                    Cm = np.zeros((n, n))
                    rt.cudaMemcpy(Cm.ctypes.data_as(C.c_void_p), ptr[2], C.c_size_t(Cm.nbytes), 2)
                    row[name] = {"tflops": 2 * n ** 3 / dt / 1e12, "err_over_absAB": float(np.max(np.abs(Cm - ref) / den))}
                for p in ptr:
                    rt.cudaFree(p)
                out.append(row)
                print("    n=%d φ=%.1f: ネイティブ %.2f TFLOPS、エミュレーション %.2f TFLOPS(誤差 %.1e)"
                      % (n, phi, row["native"]["tflops"], row["emul_performant"]["tflops"], row["emul_performant"]["err_over_absAB"]))
        cb.cublasDestroy_v2(h)
        return out
    except Exception as exc:  # noqa: BLE001  測れなければ記録の表だけ描く
        print("    GPU の測定は飛ばした: %s" % type(exc).__name__)
        return []


# ======================================================================================================================
# 図
# ======================================================================================================================
FLOOR = -18.0     # 「差 0」を対数軸に置く場所


def _lg(v):
    return math.log10(v) if v > 0 else FLOOR


def figures(st: dict, od: dict, cpu: list, gpu_live: list) -> None:
    print("== 図")
    ser, styles, colors = [], [], []
    col = {0.5: "reference", 2.0: "emphasis", 4.0: "wrong"}
    for phi in st["phi"]:
        s = np.arange(1, 15)
        ser.append(("Ozaki-I, phi = %g" % phi, s * (s + 1) / 2, [_lg(v) for v in st["oz1"][phi]]))
        styles.append(None)
        colors.append(col[phi])
    for phi in st["phi"]:
        ser.append(("DGEMM, phi = %g" % phi if phi == 0.5 else "", [1, 105], [_lg(st["dgemm"][phi])] * 2))
        styles.append("dashed")
        colors.append(col[phi])
    figs.save_plot("error_staircase_ozaki1", ser, xlabel="number of exact low-precision products  s(s+1)/2",
                   ylabel="log10 max |C - exact| / (|A||B|)", title="Each extra slice drops the error by a step until it meets FP64",
                   styles=styles, colors=colors, size=(720, 420),
                   caption="分割数(枚数)を 1 枚増やすたびに誤差が約 2⁻⁷ ずつ落ち、破線(普通の FP64 の積の誤差)に届いて止まる。"
                           "真値は Python の整数で計算した正確な値。指数の幅 φ が広いほど枚数が要る(自動選択: %s)。"
                           % "、".join("φ=%g → %d 枚" % (p, st["auto"][p][0]) for p in st["phi"]))
    ser2 = []
    for phi in st["phi"]:
        s = np.arange(2, 21)
        ser2.append(("Ozaki-II, phi = %g" % phi, s, [_lg(v) for v in st["oz2"][phi]]))
    figs.save_plot("error_staircase_ozaki2", ser2, xlabel="number of moduli (= products)", ylabel="log10 max relative error",
                   title="Ozaki-II (Chinese remainder theorem): fewer products, same floor",
                   colors=["reference", "emphasis", "wrong"], size=(720, 420),
                   caption="Ozaki-II は積の回数 = 法の数。φ が広いと同じ法の数では FP64 に届かない(φ=4 で 20 法 %.1e)。"
                           % st["oz2"][4.0][-1])
    k = np.arange(1, N_SHUFFLES + 1)
    figs.save_plot("kabsch_rotation_under_shuffles",
                   [("ordinary FP64 (DGEMM)", k, [_lg(v) for v in od["d_nat"]]),
                    ("Ozaki (matmul_reproducible)", k, [_lg(v) for v in od["d_oz"]]),
                    ("exactly 0", [0.5, N_SHUFFLES + 0.5], [FLOOR, FLOOR])],
                   kinds=["scatter", "scatter", "line"], styles=[None, None, "dotted"],
                   colors=["wrong", "right", "neutral"], xlabel="shuffle #", ylabel="log10 max |R(shuffled) - R(original)|",
                   title="Same %d points, shuffled %d times: does the Kabsch rotation move?" % (N_POINTS, N_SHUFFLES),
                   ylim=(FLOOR - 0.5, -12.0), size=(720, 400),
                   caption="点の順を入れ替えるだけで、普通の FP64 の回転は %d 通りに分かれた(最大の差 %.1e)。Ozaki 版は %d 通り"
                           "(全部ビット単位で同じ、点線 = 差 0)。" % (od["n_nat"], max(od["d_nat"]), od["n_oz"]))
    figs.save_table("same_bits_or_not", ["what changes", "ordinary FP64: distinct results", "Ozaki: distinct results"],
                    [["point order (%d shuffles + original)" % N_SHUFFLES, str(od["n_nat"]), str(od["n_oz"])],
                     ["BLAS threads 1 / 2 / 4 / 8 (cross-covariance H)", str(od["t_nat"]), str(od["t_oz"])],
                     ["time for the 3x3 H of %d points" % N_POINTS, "%.2f ms" % (1e3 * od["times"]["dgemm"]),
                      "%.0f ms" % (1e3 * od["times"]["ozaki"])]],
                    title="Same answer, bit for bit?",
                    caption="違う結果の数(1 = どの条件でも同じビット)。この計算機での値。普通の FP64 がスレッド数で動くかは BLAS の分け方次第。")
    rec = json.loads(RECORDED.read_text(encoding="utf-8"))
    for phi in (0.5, 4.0):
        ser3, cols3, sty3 = [], [], []
        for ver, c in (("13.3", "emphasis"), ("13.4", "right")):
            rows = [r for r in rec["cublas"][ver]["rows"] if r["phi"] == phi]
            ser3.append(("cuBLAS %s emulation" % ver, [math.log2(r["n"]) for r in rows], [r["emul_performant"]["tflops"] for r in rows]))
            cols3.append(c)
            sty3.append(None)
        rows = [r for r in rec["cublas"]["13.4"]["rows"] if r["phi"] == phi]
        ser3.append(("native FP64", [math.log2(r["n"]) for r in rows], [r["native"]["tflops"] for r in rows]))
        cols3.append("neutral")
        sty3.append("dashed")
        live = [r for r in gpu_live if r["phi"] == phi]
        if live:
            ser3.append(("measured now (emulation)", [math.log2(r["n"]) for r in live], [r["emul_performant"]["tflops"] for r in live]))
            cols3.append("reference")
            sty3.append("dotted")
        figs.save_plot("gpu_fp64_emulation_phi_%s" % str(phi).replace(".", "_"), ser3, xlabel="log2 n (square matrices)",
                       ylabel="TFLOPS (FP64-equivalent)", title="GPU FP64 throughput, phi = %g (recorded on %s)" % (phi, rec["gpu"].split(",")[0]),
                       colors=cols3, styles=sty3, size=(720, 400),
                       caption="手元の 1 台での測定(%s)。φ = %g で cuBLAS 13.3 のエミュレーションは%s、13.4 は n=8192 で %.1f TFLOPS(ネイティブ %.2f)。"
                               "速さが要るならこちら。ただし cuBLAS はエミュレーション中のビット単位の再現を保証しない。"
                               % (rec["measured"], phi, "ネイティブに戻った" if phi > 1 else "速くなり",
                                  [r for r in rec["cublas"]["13.4"]["rows"] if r["phi"] == phi and r["n"] == 8192][0]["emul_performant"]["tflops"],
                                  [r for r in rec["cublas"]["13.4"]["rows"] if r["phi"] == phi and r["n"] == 8192][0]["native"]["tflops"]))
    crow = cpu or [{"n": r["n"], "dgemm": r["dgemm_s"], "ozaki1_8": r["ozaki1_8_slices_s"], "ozaki2_16": r["ozaki2_16_moduli_s"]}
                   for r in rec["cpu"]["rows"]]
    figs.save_table("cpu_is_not_faster", ["n", "DGEMM", "Ozaki-I 8 slices", "Ozaki-II 16 moduli"],
                    [[str(r["n"]), "%.2f ms" % (1e3 * r["dgemm"]), "%.0f x slower" % (r["ozaki1_8"] / r["dgemm"]),
                      "%.0f x slower" % (r["ozaki2_16"] / r["dgemm"])] for r in crow],
                    title="CPU: same bits, not speed",
                    caption=("この計算機で今測った値。" if cpu else "記録の表(%s、%s)。--full で測り直す。" % (rec["measured"], rec["cpu"]["blas"]))
                    + "正方行列の積は DGEMM の 1〜2 桁遅い。")
    print("  figures:", figs.errors() or "ok")


# ======================================================================================================================
def main() -> int:
    t_all = time.time()
    st = staircase()
    od = order_and_threads()
    scale_and_fail_closed()
    pr = probe_and_entry()
    cpu, gpu_live = [], []
    if FULL:
        cpu = cpu_speed()
        if pr.get("available"):
            gpu_live = gpu_measure(pr)
        else:
            skip("GPU の測定", "cuBLAS 13 の FP64 エミュレーションが使えない(記録の表だけ描く)")
    dt = time.time() - t_all
    budget = 120 if FULL else 30
    gate("門 13 所要 ≤ %d s" % budget, dt <= budget, "%.1f s" % dt)
    if figs.enabled():
        figures(st, od, cpu, gpu_live)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all))
    if n_ng or figs.errors():
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
