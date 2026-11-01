"""生の輝度しきい値と、正規化後の kσ / P-tile の移植性を真値で測る PoC。

合成品の欠陥マスクを先に固定し、照明利得・オフセット・読み出し雑音・材質の
明るさだけを変える。基準画像で合わせたつまみを別条件へそのまま移し、IoU 0.98
を満たさない場合だけ同じ決定的な候補列で再調整する。評価回数は「移植に失敗した
あと、合格するつまみへ達するまでに採点した追加候補数」であり、実行時間ではない。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from normalized_threshold import image_standardize, ptile_threshold, sigma_threshold


SLUG = "poc_threshold_transfer_after_normalization"
ROOT = Path(__file__).resolve().parents[1]
PUBLIC_OUT = ROOT / "docs" / "articles" / "assets" / "poc" / SLUG
OUT = PUBLIC_OUT if os.environ.get("FULLSEYE_FIGURE_DIR") else Path(tempfile.mkdtemp(prefix=SLUG + "_"))
TARGET_IOU = 0.98


CONDITIONS = [
    ("baseline", 1.00, 0.00, 0.40, 0.020),
    ("gain_x1.35", 1.35, 0.00, 0.40, 0.020),
    ("offset_+0.18", 1.00, 0.18, 0.40, 0.020),
    ("noise_x2", 1.00, 0.00, 0.40, 0.040),
    ("material_+0.18", 1.00, 0.00, 0.58, 0.020),
    ("combined", 0.85, 0.08, 0.55, 0.030),
]


def truth_mask(shape=(192, 256)) -> np.ndarray:
    yy, xx = np.indices(shape)
    circle = (yy - 58) ** 2 + (xx - 74) ** 2 <= 15 ** 2
    scratch = (np.abs(yy - (0.34 * xx + 67)) <= 2) & (xx > 112) & (xx < 222)
    pit = ((yy - 142) ** 2 / 9 ** 2 + (xx - 54) ** 2 / 18 ** 2) <= 1
    return circle | scratch | pit


def make_image(gain: float, offset: float, material: float, noise: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    truth = truth_mask()
    yy, xx = np.indices(truth.shape)
    # 材質の微細な模様。条件を跨いでも同じ品物だが、撮像雑音だけは独立。
    texture = 0.006 * np.sin(xx / 11.0) + 0.004 * np.cos(yy / 17.0)
    rng = np.random.default_rng(seed)
    latent = material + texture + 0.24 * truth
    observed = gain * latent + offset + rng.normal(0.0, noise, truth.shape)
    return observed.astype(np.float64), truth


def score(mask: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    mask = np.asarray(mask, bool)
    tp = int(np.count_nonzero(mask & truth))
    fp = int(np.count_nonzero(mask & ~truth))
    fn = int(np.count_nonzero(~mask & truth))
    tn = int(np.count_nonzero(~mask & ~truth))
    return {"iou": tp / (tp + fp + fn), "fpr": fp / (fp + tn), "fnr": fn / (fn + tp)}


def raw_mask(image: np.ndarray, threshold: float) -> np.ndarray:
    return image > threshold


def sigma_mask(image: np.ndarray, k: float) -> np.ndarray:
    z = image_standardize(image, method="robust")
    return sigma_threshold(z, k=k, polarity="bright")


def ptile_mask(image: np.ndarray, p: float) -> np.ndarray:
    threshold = ptile_threshold(image, p=p, polarity="bright")
    return image > threshold


def alternating(center: float, step: float, n: int, lo: float, hi: float) -> list[float]:
    values = [center]
    for j in range(1, n + 1):
        values.extend((center + j * step, center - j * step))
    return [float(x) for x in values if lo < x < hi]


def tune(image, truth, fn, candidates) -> tuple[float, int, dict[str, float]]:
    for evaluations, value in enumerate(candidates, 1):
        metrics = score(fn(image, value), truth)
        if metrics["iou"] >= TARGET_IOU:
            return value, evaluations, metrics
    best = max(((score(fn(image, value), truth)["iou"], value) for value in candidates), key=lambda x: x[0])
    raise AssertionError(f"no candidate reached IoU {TARGET_IOU}: best={best}")


def measure() -> tuple[list[dict], dict, dict]:
    images = {}
    for seed, (name, gain, offset, material, noise) in enumerate(CONDITIONS, 196):
        images[name] = make_image(gain, offset, material, noise, seed)
    area_p = float(np.mean(next(iter(images.values()))[1]))
    methods = {
        "raw": (raw_mask, alternating(0.52, 0.02, 30, 0.0, 1.5)),
        "k_sigma": (sigma_mask, alternating(3.0, 0.25, 10, 0.25, 8.0)),
        "p_tile": (ptile_mask, alternating(area_p, 0.0025, 15, 0.001, 0.25)),
    }
    baseline = images["baseline"]
    selected, rows = {}, []
    for method, (fn, candidates) in methods.items():
        value, evaluations, metrics = tune(*baseline, fn, candidates)
        selected[method] = value
        rows.append({"condition": "baseline", "method": method, "parameter": value,
                     "transfer_iou": metrics["iou"], "fpr": metrics["fpr"], "fnr": metrics["fnr"],
                     "tuning_evaluations": evaluations, "retuned": False})
    for name, *_ in CONDITIONS[1:]:
        image, truth = images[name]
        for method, (fn, candidates0) in methods.items():
            value = selected[method]
            metrics = score(fn(image, value), truth)
            evaluations, retuned = 0, False
            used = value
            if metrics["iou"] < TARGET_IOU:
                # 既に不合格と分かった移植値は数えず、次の候補から追加評価を数える。
                candidates = [x for x in alternating(value,
                              {"raw": 0.02, "k_sigma": 0.25, "p_tile": 0.0025}[method],
                              30, 0.0 if method == "raw" else 0.001,
                              1.5 if method == "raw" else (8.0 if method == "k_sigma" else 0.25))
                              if not np.isclose(x, value)]
                used, evaluations, _ = tune(image, truth, fn, candidates)
                retuned = True
            rows.append({"condition": name, "method": method, "parameter": value,
                         "retuned_parameter": used if retuned else None,
                         "transfer_iou": metrics["iou"], "fpr": metrics["fpr"], "fnr": metrics["fnr"],
                         "tuning_evaluations": evaluations, "retuned": retuned})
    return rows, selected, images


def save_figure(rows: list[dict], selected: dict, images: dict) -> dict:
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(16, 9), dpi=100)
    gs = fig.add_gridspec(3, len(CONDITIONS), height_ratios=(1.0, 1.0, 0.8))
    for col, (name, *_rest) in enumerate(CONDITIONS):
        image, truth = images[name]
        ax = fig.add_subplot(gs[0, col])
        ax.imshow(image, cmap="gray")
        ax.set_title(name)
        ax.axis("off")
        ax = fig.add_subplot(gs[1, col])
        ax.imshow(sigma_mask(image, selected["k_sigma"]), cmap="gray", vmin=0, vmax=1)
        ax.contour(truth, levels=[0.5], colors=["#f28e2b"], linewidths=0.8)
        ax.set_title("fixed kσ (orange=truth)")
        ax.axis("off")
    ax = fig.add_subplot(gs[2, :])
    x = np.arange(len(CONDITIONS))
    width = 0.24
    for j, method in enumerate(("raw", "k_sigma", "p_tile")):
        vals = [next(r["tuning_evaluations"] for r in rows if r["condition"] == c[0] and r["method"] == method)
                for c in CONDITIONS]
        ax.bar(x + (j - 1) * width, vals, width, label=method)
    ax.set_xticks(x, [c[0] for c in CONDITIONS])
    ax.set_ylabel("additional tuning evaluations (baseline includes initial tuning)")
    ax.set_title("A raw grey-level threshold needs retuning; normalized knobs transfer")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    filename = "01_threshold_transfer.png"
    fig.savefig(OUT / filename)
    plt.close(fig)
    return {"file": filename, "name": "threshold_transfer",
            "caption": "Synthetic product images under gain, offset, noise, and material-brightness changes; fixed robust k-sigma masks and the measured retuning evaluations for raw, k-sigma, and P-tile thresholds.",
            "shape": [900, 1600, 4]}


def main() -> None:
    rows, selected, images = measure()
    figure = save_figure(rows, selected, images)
    summary = {"target_iou": TARGET_IOU, "selected_on_baseline": selected,
               "defect_area_fraction": float(np.mean(truth_mask())), "conditions": rows,
               "additional_evaluations": {m: int(sum(r["tuning_evaluations"] for r in rows if r["method"] == m))
                                          for m in ("raw", "k_sigma", "p_tile")}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "figures.json").write_text(json.dumps([figure], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("condition\tmethod\tIoU\tFPR\tFNR\tevaluations")
    for row in rows:
        print("{condition}\t{method}\t{transfer_iou:.4f}\t{fpr:.4f}\t{fnr:.4f}\t{tuning_evaluations}".format(**row))
    print(json.dumps(summary["additional_evaluations"], ensure_ascii=False))
    assert summary["additional_evaluations"]["raw"] > summary["additional_evaluations"]["k_sigma"]
    assert summary["additional_evaluations"]["raw"] > summary["additional_evaluations"]["p_tile"]
    assert all(r["transfer_iou"] >= TARGET_IOU for r in rows if r["method"] in ("k_sigma", "p_tile"))
    print("PASS", SLUG)


if __name__ == "__main__":
    main()
