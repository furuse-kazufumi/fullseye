"""OpenCV(cv2, CPU)との処理速度比較ベンチ。imgevolve の GPU op(accel / accel_match /
accel_vol、RTX 5090 / torch cu128)を、同じ処理の OpenCV CPU 実装と突き合わせて実績を残す。

honest 方針([[feedback_benchmark_honest_disclosure]] / [[feedback_benchmark_thermal_steady_state]]):
- warmup 後に複数回計測して中央値、CUDA は synchronize。
- cv2 は単画像 API なのでバッチはループ(= 実運用の cv2 バッチ処理)。GPU はバッチ常駐。
- **小さい単発画像では cv2 CPU が勝つ**(GPU は転送/起動律速)。GPU が効くのは
  バッチ・大画像・常駐パイプライン。勝ち負け両方を正直に表に出す。

実行: loco venv(cv2 + torch cuda)で `python bench_vs_opencv.py`。docs/BENCH_VS_OPENCV.md を生成。
"""
import sys
import time

import numpy as np

sys.path.insert(0, r"C:\dev\projects\imgevolve")
import cv2
import torch
import accel
import accel_match as M

DEV = "cuda" if torch.cuda.is_available() else "cpu"


def _sync():
    if DEV == "cuda":
        torch.cuda.synchronize()


def _timed(fn, reps=7):
    fn()                                    # warmup
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        _sync()
        ts.append(time.perf_counter() - t0)
    return float(np.median(ts))


def _imgs(size, B, seed=0):
    rng = np.random.default_rng(seed)
    return [np.clip(rng.random((size, size)), 0, 1).astype(np.float64) for _ in range(B)]


# ---- op ペア: (名前, cv2_CPU_fn(imgs)->list, gpu_fn(imgs)->None(実行のみ)) ---------- #
def _disk_se(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


SHARPEN_K = np.array([[0, -0.5, 0], [-0.5, 1 + 2.0, -0.5], [0, -0.5, 0]], np.float32)


def op_pairs():
    return [
        ("gaussian σ=2.0",
         lambda ims: [cv2.GaussianBlur(x.astype(np.float32), (0, 0), 2.0) for x in ims],
         lambda ims: accel.run_batch("gauss_filter", ims, (2.0 - 0.3) / 2.7, 0.4, DEV)),
        ("median 5x5",
         lambda ims: [cv2.medianBlur(x.astype(np.float32), 5) for x in ims],
         lambda ims: accel.run_batch("median_image", ims, 0.4, 0.4, DEV)),   # _k(0.4)=5
        ("box mean 5x5",
         lambda ims: [cv2.blur(x.astype(np.float32), (5, 5)) for x in ims],
         lambda ims: accel.run_batch("mean_image", ims, 0.4, 0.4, DEV)),
        ("dilate 5x5",
         lambda ims: [cv2.dilate(x.astype(np.float32), np.ones((5, 5), np.uint8)) for x in ims],
         lambda ims: accel.run_batch("gdilate", ims, 0.4, 0.4, DEV)),
        ("erode 5x5",
         lambda ims: [cv2.erode(x.astype(np.float32), np.ones((5, 5), np.uint8)) for x in ims],
         lambda ims: accel.run_batch("gerode", ims, 0.4, 0.4, DEV)),
        ("sobel mag",
         lambda ims: [cv2.magnitude(cv2.Sobel(x.astype(np.float32), cv2.CV_32F, 1, 0),
                                    cv2.Sobel(x.astype(np.float32), cv2.CV_32F, 0, 1)) for x in ims],
         lambda ims: accel.run_batch("sobel_amp", ims, 0.5, 0.4, DEV)),
        ("threshold",
         lambda ims: [cv2.threshold(x.astype(np.float32), 0.5, 1.0, cv2.THRESH_BINARY)[1] for x in ims],
         lambda ims: accel.run_batch("threshold", ims, 0.5, 0.4, DEV)),
        ("sharpen 3x3",
         lambda ims: [np.clip(cv2.filter2D(x.astype(np.float32), -1, SHARPEN_K), 0, 1) for x in ims],
         lambda ims: accel.run_batch("cv_sharpen", ims, 0.5, 0.4, DEV)),
        ("morph open disk",
         lambda ims: [cv2.morphologyEx((x > 0.5).astype(np.uint8), cv2.MORPH_OPEN, _disk_se(2)) for x in ims],
         lambda ims: accel.run_batch("opening_circle", ims, 0.56, 0.4, DEV)),  # _rad(0.56)=2
    ]


def bench_ops(size, B):
    rows = []
    for name, cpu_fn, gpu_fn in op_pairs():
        ims = _imgs(size, B)
        tc = _timed(lambda: cpu_fn(ims), reps=5)
        tg = _timed(lambda: gpu_fn(ims), reps=7)
        rows.append((name, tc * 1e3, tg * 1e3, tc / tg, B / tg, B / tc))
    return rows


def bench_template(size, B):
    rng = np.random.default_rng(1)
    T = rng.random((15, 15)).astype(np.float32)
    ims = [np.clip(rng.random((size, size)), 0, 1).astype(np.float32) for _ in range(B)]

    def cpu():
        out = []
        for x in ims:
            r = cv2.matchTemplate(x, T, cv2.TM_CCOEFF_NORMED)
            out.append(cv2.minMaxLoc(r))
        return out
    imf = [x.astype(np.float64) for x in ims]
    tc = _timed(cpu, reps=5)
    tg = _timed(lambda: M.ncc_locate_batch(imf, T.astype(np.float64), DEV), reps=7)
    return ("NCC template match", tc * 1e3, tg * 1e3, tc / tg, B / tg, B / tc)


def bench_pipeline(size, B):
    """binarize champion(threshold→opening→dilate→erode→dilate→projective)を
    cv2 CPU 逐次 vs GPU 常駐で比較(E2E の本丸=常駐で転送償却)。"""
    ims = _imgs(size, B, seed=3)
    se = _disk_se(2)
    cross = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))

    def cpu():
        out = []
        for x in ims:
            m = (x > 0.48).astype(np.uint8)
            m = cv2.morphologyEx(m, cv2.MORPH_OPEN, se)
            m = cv2.dilate(m, cross, iterations=2)
            m = cv2.erode(m, se)
            m = cv2.dilate(m, cross, iterations=2)
            out.append(m)
        return out
    steps = [("threshold", 0.48, 0.22), ("opening_circle", 0.62, 0.21),
             ("reg_dilate", 0.63, 0.46), ("erosion_golay", 0.56, 0.48),
             ("reg_dilate", 0.59, 0.82)]
    tc = _timed(cpu, reps=5)
    tg = _timed(lambda: accel.run_pipeline(steps, ims, DEV), reps=7)
    return ("binarize pipeline (5-op resident)", tc * 1e3, tg * 1e3, tc / tg, B / tg, B / tc)


def bench_breakdown(size=512, B=32):
    """GPU 時間の内訳: 転送 vs 実計算。単発 op が遅い真因を数値で示す。"""
    from accel import _gauss_kernel, _sep_conv_sym
    ims = _imgs(size, B)
    t_xfer = _timed(lambda: accel._from_batch(accel._to_batch(ims, DEV)))
    tb = accel._to_batch(ims, DEV); _sync()
    t_comp = _timed(lambda: _sep_conv_sym(tb, _gauss_kernel(2.0, DEV)))
    return t_xfer * 1e3, t_comp * 1e3


def bench_resident_scaling(size=512, B=32):
    """N-op を「cv2 逐次」vs「GPU 常駐(転送1回)」で。転送償却の交差点を示す。"""
    ims = _imgs(size, B, seed=5)
    rows = []
    for n in (1, 3, 5, 10, 20):
        steps = [("gauss_filter", 0.63, 0.4)] * n

        def cv():
            out = []
            for x in ims:
                y = x.astype(np.float32)
                for _ in range(n):
                    y = cv2.GaussianBlur(y, (0, 0), 2.0)
                out.append(y)
            return out
        tc = _timed(cv, reps=5)
        tg = _timed(lambda s=steps: accel.run_pipeline(s, ims, DEV), reps=7)
        rows.append((n, tc * 1e3, tg * 1e3, tc / tg))
    return rows


def bench_compute_heavy(size=512, B=32):
    """計算が重い op(GPU の本領)。転送を計算が上回るので単発でも GPU が有利になりうる。"""
    rows = []
    ims = _imgs(size, B, seed=7)
    # 大 σ gaussian(σ=8、kernel ~65): cv2 も分離可能だが GPU の並列が効く
    tc = _timed(lambda: [cv2.GaussianBlur(x.astype(np.float32), (0, 0), 8.0) for x in ims], reps=5)
    tg = _timed(lambda: accel.run_batch("gauss_filter", ims, (8.0 - 0.3) / 2.7, 0.4, DEV), reps=7)
    rows.append(("gaussian σ=8 (大kernel)", "cv2", tc * 1e3, tg * 1e3, tc / tg))
    # sk_tv(Chambolle TV、~200 反復): cv2 に同一 TV は無いので GPU vs CPU-torch(同一実装)
    ims2 = _imgs(size, min(B, 8), seed=8)
    tc2 = _timed(lambda: accel.run_batch("sk_tv", ims2, 0.5, 0.0, "cpu"), reps=3)
    tg2 = _timed(lambda: accel.run_batch("sk_tv", ims2, 0.5, 0.0, DEV), reps=5)
    rows.append((f"sk_tv TV denoise (B={len(ims2)})", "CPU-torch", tc2 * 1e3, tg2 * 1e3, tc2 / tg2))
    return rows


def bench_volume():
    """3D は cv2 に無いので scipy 比。GPU の本領(voxel 数が大)。"""
    from scipy import ndimage
    import accel_vol as V
    rng = np.random.default_rng(0)
    rows = []
    for size, B in [(32, 32), (64, 16), (128, 4)]:
        vols = [np.clip(rng.random((size, size, size)), 0, 1) for _ in range(B)]

        def sp():
            out = []
            for v in vols:
                x = np.clip(ndimage.median_filter(v, 3), 0, 1)
                x = np.clip(ndimage.median_filter(x, 3), 0, 1)
                x = np.clip(ndimage.grey_erosion(x, size=3), 0, 1)
                x = np.clip(ndimage.grey_dilation(x, size=3), 0, 1)
                out.append(x)
            return out
        steps = [("vol_median_g", 0.83, 0.04), ("vol_median_g", 0.51, 0.73),
                 ("vol_erode_g", 0.51, 1.0), ("vol_dilate_g", 0.89, 0.26)]
        ts = _timed(sp, reps=3)
        tg = _timed(lambda s=steps, vv=vols: V.run_pipeline_vol(s, vv, DEV), reps=5)
        rows.append((f"{size}³×{B}", ts * 1e3, tg * 1e3, ts / tg))
    return rows


def main():
    L = []
    L.append("# imgevolve GPU op vs OpenCV(CPU)処理速度ベンチ\n")
    L.append(f"- GPU: **{torch.cuda.get_device_name(0) if DEV=='cuda' else 'CPU'}** / torch {torch.__version__}")
    L.append(f"- OpenCV: cv2 {cv2.__version__}(CPU、単画像 API をバッチループ)")
    L.append("- 計測: warmup 後 中央値、CUDA synchronize。speedup = cv2CPU / GPU。\n")

    xfer, comp = bench_breakdown()
    L.append("## 結論(honest)\n")
    L.append(f"- **単発の軽量 2D フィルタは OpenCV CPU が速い**。cv2 は SIMD/多スレッドで極限まで最適化されており、"
             f"GPU 側は **host↔device 転送が律速**(512²×32 で転送のみ **{xfer:.0f} ms**、対して gaussian の"
             f"実計算は **{comp:.2f} ms** = 転送の約 {xfer/comp:.0f} 分の 1)。データが一度 GPU に載れば計算は桁違いに速いが、"
             f"1 op だけでは転送を取り戻せない。")
    L.append("- **GPU が OpenCV に勝つのは 3 条件**: (1) 計算が重い op(NCC テンプレートマッチング)、"
             "(2) **多 op を常駐で連鎖**して転送を償却(= E2E 本丸 `accel.run_pipeline`)、(3) **3D**(cv2 に無い)。")
    L.append("- imgevolve の設計(常駐パイプライン + 進化 champion を丸ごと GPU)はまさに (2) を突く。"
             "以前の「64x/3-5x」は **scipy 比**であり、最強 CPU=cv2 比では上記の通り条件付き。正直に開示する。")
    L.append("- **cv2 ≒ HALCON 級の最適化 CPU** なので、この比較は fullseye が目標とする HALCON との"
             "性能差の予測にもなる(単発は HALCON 級 CPU が速い / 常駐多op・NCC・3D で GPU が上回る、と読める)。\n")

    ch = bench_compute_heavy()
    L.append("## 計算が重い op(GPU の本領、単発でも勝ちうる)\n")
    L.append("| op | baseline | baseline (ms) | GPU (ms) | speedup |")
    L.append("|---|---|---:|---:|---:|")
    for name, base, tc, tg, sp in ch:
        mark = "**GPU**" if sp >= 1 else base
        L.append(f"| {name} | {base} | {tc:.1f} | {tg:.1f} | {sp:.1f}× ({mark}) |")
    L.append("")

    L.append("## 常駐パイプラインの転送償却(N-op、512²×32)\n")
    L.append("同じ gaussian を N 回。cv2 は逐次、GPU は転送1回で N op 連鎖。**N が増えるほど GPU 有利**。\n")
    L.append("| N op | cv2 CPU (ms) | GPU 常駐 (ms) | speedup |")
    L.append("|---:|---:|---:|---:|")
    for n, tc, tg, sp in bench_resident_scaling():
        mark = "**GPU**" if sp >= 1 else "cv2"
        L.append(f"| {n} | {tc:.1f} | {tg:.1f} | {sp:.1f}× ({mark}) |")

    L.append("\n## 3D volume(cv2 に 3D 無し → scipy 比)\n")
    L.append("| size×batch | scipy CPU (ms) | GPU (ms) | speedup |")
    L.append("|---|---:|---:|---:|")
    for name, ts, tg, sp in bench_volume():
        L.append(f"| {name} | {ts:.0f} | {tg:.1f} | **{sp:.0f}×** |")

    for size, B in [(512, 32), (1024, 16), (256, 1)]:
        L.append(f"\n## 単発 op 比較 {size}×{size}, batch={B}\n")
        L.append("| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |")
        L.append("|---|---:|---:|---:|---:|---:|")
        rows = bench_ops(size, B)
        rows.append(bench_template(size, B))
        rows.append(bench_pipeline(size, B))
        for name, tc, tg, sp, gips, cips in rows:
            mark = "**GPU**" if sp >= 1 else "cv2"
            L.append(f"| {name} | {tc:.2f} | {tg:.2f} | {sp:.1f}× ({mark}) | {gips:.0f} | {cips:.0f} |")

    out = "\n".join(L) + "\n"
    with open(r"C:\dev\projects\imgevolve\docs\BENCH_VS_OPENCV.md", "w", encoding="utf-8") as f:
        f.write(out)
    print(out)


if __name__ == "__main__":
    main()
