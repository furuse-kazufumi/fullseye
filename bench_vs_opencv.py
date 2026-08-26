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


def main():
    lines = []
    lines.append(f"# imgevolve GPU op vs OpenCV(CPU)処理速度ベンチ\n")
    lines.append(f"- GPU: **{torch.cuda.get_device_name(0) if DEV=='cuda' else 'CPU'}** / torch {torch.__version__}")
    lines.append(f"- OpenCV: cv2 {cv2.__version__}(CPU、単画像 API をバッチループ)")
    lines.append(f"- 計測: warmup 後 中央値、CUDA synchronize。speedup = cv2CPU / GPU。\n")
    lines.append("honest: **小さい単発画像は cv2 CPU が速い**(GPU は転送/起動律速)。"
                 "GPU が効くのは**バッチ・大画像・常駐パイプライン**。以下は勝ち負け両方を出す。\n")

    for size, B in [(512, 32), (1024, 16), (256, 1)]:
        lines.append(f"\n## {size}×{size}, batch={B}\n")
        lines.append("| op | cv2 CPU (ms) | GPU (ms) | speedup | GPU img/s | cv2 img/s |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        rows = bench_ops(size, B)
        rows.append(bench_template(size, B))
        rows.append(bench_pipeline(size, B))
        for name, tc, tg, sp, gips, cips in rows:
            mark = "**GPU**" if sp >= 1 else "cv2"
            lines.append(f"| {name} | {tc:.2f} | {tg:.2f} | {sp:.1f}× ({mark}) | "
                         f"{gips:.0f} | {cips:.0f} |")

    out = "\n".join(lines) + "\n"
    with open(r"C:\dev\projects\imgevolve\docs\BENCH_VS_OPENCV.md", "w", encoding="utf-8") as f:
        f.write(out)
    print(out)


if __name__ == "__main__":
    main()
