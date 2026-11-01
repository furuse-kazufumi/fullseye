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
import examplefig as figs
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

CONDITION_JA = {
    "baseline": "基準",
    "gain_x1.35": "利得 1.35 倍",
    "offset_+0.18": "オフセット +0.18",
    "noise_x2": "雑音 2 倍",
    "material_+0.18": "材質 +0.18",
    "combined": "複合条件",
}

METHOD_JA = {"raw": "生のしきい値", "k_sigma": "kσ", "p_tile": "P-tile"}


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


def _row(rows: list[dict], condition: str, method: str) -> dict:
    return next(r for r in rows if r["condition"] == condition and r["method"] == method)


def _mask_with_truth(mask: np.ndarray, truth: np.ndarray) -> np.ndarray:
    """二値像を白黒、真値の内側輪郭を橙で描く。補間は一切しない。"""
    mask = np.asarray(mask, bool)
    truth = np.asarray(truth, bool)
    interior = truth.copy()
    interior[1:-1, 1:-1] &= (truth[:-2, 1:-1] & truth[2:, 1:-1]
                               & truth[1:-1, :-2] & truth[1:-1, 2:])
    outline = truth & ~interior
    rgb = np.repeat(mask[..., None], 3, axis=2).astype(np.float64)
    rgb[outline] = (0.95, 0.45, 0.05)
    return rgb


def _save_conditions(rows: list[dict], selected: dict, images: dict) -> None:
    panels, captions, gray = [], [], []
    for name, *_ in CONDITIONS:
        panels.append(images[name][0])
        captions.append(CONDITION_JA[name])
        gray.append(True)
    for method, fn in (("raw", raw_mask), ("k_sigma", sigma_mask)):
        for name, *_ in CONDITIONS:
            image, truth = images[name]
            iou = _row(rows, name, method)["transfer_iou"]
            panels.append(_mask_with_truth(fn(image, selected[method]), truth))
            captions.append("%s移送 | IoU %.4f" % (METHOD_JA[method], iou))
            gray.append(False)
    figs.save_grid(
        "threshold_transfer",
        panels,
        captions=captions,
        title="同じ欠陥を6条件で撮像: 上段=入力、中段=生のしきい値、下段=kσ（橙=真値）",
        ncols=len(CONDITIONS),
        gray=gray,
        caption="基準像で決めた同じしきい値を移送した。利得・オフセット・材質変化では生のしきい値の"
                "二値像がほぼ白く崩れる一方、頑健標準化後の kσ は真値の輪郭を保つ。",
    )


def _save_grouped_bars(name: str, rows: list[dict], field: str, title: str,
                       ylabel: str, ylim: tuple[float, float], value_fmt: str,
                       footer_note: str = "") -> None:
    """examplefig の棒グラフへ数値ラベルを重ねて保存する。"""
    import fullseye as fs

    size, scale = (1080, 600), 2
    offsets = {"raw": -0.24, "k_sigma": 0.0, "p_tile": 0.24}
    colors = {"raw": "wrong", "k_sigma": "right", "p_tile": "emphasis"}
    series, kinds, roles, labels = [], [], [], []
    for method in ("raw", "k_sigma", "p_tile"):
        for i, (condition, *_) in enumerate(CONDITIONS):
            value = float(_row(rows, condition, method)[field])
            series.append((METHOD_JA[method] if i == 0 else "", [i + offsets[method]], [value]))
            kinds.append("bar")
            roles.append(colors[method])
            labels.append((i + offsets[method], value, value_fmt % value))
    mapping = "条件 0=基準、1=利得1.35倍、2=オフセット+0.18、3=雑音2倍、4=材質+0.18、5=複合"
    xlabel = mapping + ((" | " + footer_note) if footer_note else "")
    image = figs.render_plot(
        series,
        xlabel=xlabel,
        ylabel=ylabel,
        title=title,
        size=size,
        xlim=(-0.65, 5.65),
        ylim=ylim,
        kinds=kinds,
        colors=roles,
        scale=scale,
    )
    # render_plot は明示 ylim に上下 6 % の余白を加える。同じ変換で棒上へ値を置く。
    pad = 0.06 * (ylim[1] - ylim[0])
    plotted_ylim = (ylim[0] - pad, ylim[1] + pad)
    ax = fs.axes_transform((72 * scale, 44 * scale,
                            (size[0] - 96) * scale, (size[1] - 108) * scale),
                           (-0.65, 5.65), plotted_ylim)
    x0, y0, width, height = ax["rect"]
    for x, value, label in labels:
        px = x0 + (x - ax["xlim"][0]) / (ax["xlim"][1] - ax["xlim"][0]) * (width - 1)
        py = y0 + (height - 1) - ((value - ax["ylim"][0])
             / (ax["ylim"][1] - ax["ylim"][0]) * (height - 1))
        image = np.asarray(fs.text_box(image, label, (px, max(y0 + 18, py - 5)),
                                       anchor="cb", font_size=9 * scale, pad=2 * scale,
                                       box_alpha=0.82))
    figs.save(name, image, caption=(
        "基準像で選んだ値を各条件へそのまま移した結果。棒上の数値は" + ylabel + "。"
    ))


def save_figures(rows: list[dict], selected: dict, images: dict) -> None:
    _save_conditions(rows, selected, images)
    _save_grouped_bars(
        "transfer_iou", rows, "transfer_iou",
        "基準像で決めたしきい値を移送した後の IoU",
        "IoU", (0.0, 1.08), "%.3f",
    )
    _save_grouped_bars(
        "tuning_evaluations", rows, "tuning_evaluations",
        "IoU 0.98へ戻すまでに要した評価回数",
        "評価回数", (0.0, 15.0), "%.0f",
        footer_note="基準は初期調整を含む",
    )


def main() -> None:
    rows, selected, images = measure()
    if figs.enabled():
        save_figures(rows, selected, images)
    summary = {"target_iou": TARGET_IOU, "selected_on_baseline": selected,
               "defect_area_fraction": float(np.mean(truth_mask())), "conditions": rows,
               "additional_evaluations": {m: int(sum(r["tuning_evaluations"] for r in rows if r["method"] == m))
                                          for m in ("raw", "k_sigma", "p_tile")}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("condition\tmethod\tIoU\tFPR\tFNR\tevaluations")
    for row in rows:
        print("{condition}\t{method}\t{transfer_iou:.4f}\t{fpr:.4f}\t{fnr:.4f}\t{tuning_evaluations}".format(**row))
    print(json.dumps(summary["additional_evaluations"], ensure_ascii=False))
    assert summary["additional_evaluations"]["raw"] > summary["additional_evaluations"]["k_sigma"]
    assert summary["additional_evaluations"]["raw"] > summary["additional_evaluations"]["p_tile"]
    assert all(r["transfer_iou"] >= TARGET_IOU for r in rows if r["method"] in ("k_sigma", "p_tile"))
    assert not figs.errors(), figs.errors()
    print("PASS", SLUG)


if __name__ == "__main__":
    main()
