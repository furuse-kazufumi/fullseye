# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lens_defect_dataset_demo — 設計したレンズで欠陥画像を撮る(lensimage 4 op)。

    py -3.11 examples/lens_defect_dataset_demo.py

【この例が解く問題】
raytrace は「このレンズはどれだけボケるか」を数字で返すが、検査 AI を鍛えるのに
要るのは**そのレンズで撮った画像と、像に揃った正解マスク**である。同じ f≈100 /
f/4 の singlet と doublet を処方のまま使い、
(1) 実収差瞳の回折 PSF(psf_from_opd)を視野 0 / 2 / 4 deg で出し、Strehl と
    RMS スポットを表にする(doublet が全視野で勝つ)。
(2) 無収差の瞳(1 mm 絞り)が Airy パターンになることを、第 1 暗環 1.22·λ·F# と
    暗環内エネルギー 83.8 % で機械的に確かめる。
(3) 歪曲表(distortion_map): 放物面鏡はゼロ、singlet は樽型(負)。
(4) defectgen の欠陥を doublet 越しに 4 枚描き(defect_dataset)、PNG と
    annotations.json を一時ディレクトリへ書き、マスクが**同じ歪曲だけ**通って
    像に揃っていること(IoU > 0.5)を検証する。

【グラウンドトゥルース(数値で嘘を弾く)】
1. Airy: 第 1 暗環 = 1.22·λ·F# の 3 % 以内、暗環内エネルギー 83.8 ± 1 %。
2. f/4 singlet(球面収差 11 波)の軸上 Strehl < 0.05、doublet はそれより大きい。
3. 放物面鏡の歪曲 |%| < 1e-6、singlet の 15 deg 歪曲は負(樽型)。
4. δ 画像を放物面鏡で描くと画素積分 Airy PSF に一致(max |diff| < 1e-12)。
5. データセット 4 件: 画像とマスクの形が一致、bbox は画像内、seed 再現、
   傷マスクと描画された欠陥領域の IoU > 0.5。
"""
import json
import math
import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import defectgen as DG  # noqa: E402
import lensimage as LI  # noqa: E402
import raytrace as RT  # noqa: E402

INF = float("inf")


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    return bool(cond)


def main():
    ok = True
    singlet = RT.example_system("singlet")
    doublet = RT.example_system("doublet")
    parab = RT.example_system("paraboloid")

    print("(1) per-field PSF: Strehl / RMS spot [mm]")
    fields = (0.0, 2.0, 4.0)
    rows = {}
    for name, s in (("singlet", singlet), ("doublet", doublet)):
        g = LI.psf_field_grid(s, fields=fields)
        rows[name] = g
        for f, st, rms in zip(g["fields"], g["strehl"], g["rms_spot_mm"]):
            print("  %-8s field %4.1f deg  Strehl %.4f  rms_spot %.4f mm  sample %.3f um"
                  % (name, f, st, rms, g["sample_um"][0]))
    ok &= check(rows["singlet"]["strehl"][0] < 0.05, "singlet on-axis Strehl < 0.05 (11 waves SA)")
    ok &= check(all(d > s for d, s in zip(rows["doublet"]["strehl"], rows["singlet"]["strehl"])),
                "doublet Strehl beats the singlet at every field")

    print("(2) unaberrated pupil -> Airy pattern")
    small = RT.lens_system([{"R": 51.68, "t": 5, "n": 1.5168, "ap": 1.0},
                            {"R": INF, "t": None, "n": 1.0}], stop=0)
    para = RT.paraxial_trace(small)
    fno = 1.0 / (2.0 * para["na_image"])
    wl = small["wavelength_um"]
    psf, _ref, dx, _n = LI._psf_core(small, 0.0, 128, None, 16)
    M = psf.shape[0]
    yy, xx = np.mgrid[:M, :M]
    r = np.hypot(yy - M // 2, xx - M // 2) * dx
    r1 = 1.22 * wl * fno
    edges = np.arange(0.0, 2.0 * r1, dx)
    prof = np.array([psf[(r >= a) & (r < a + dx)].mean() if ((r >= a) & (r < a + dx)).any() else np.inf
                     for a in edges])
    zero = edges[int(np.argmin(prof[: int(0.7 * len(edges))]))]
    ee = psf[r <= r1].sum() / psf.sum()
    print("  first dark ring %.2f um (theory %.2f), encircled energy %.4f" % (zero, r1, ee))
    ok &= check(abs(zero / r1 - 1.0) < 0.03, "first dark ring at 1.22 lambda F# within 3 %")
    ok &= check(abs(ee - 0.838) < 0.01, "83.8 % of the energy inside the first ring")

    print("(3) distortion")
    dp = LI.distortion_map(parab)
    ds = LI.distortion_map(singlet, fields=[0.0, 5.0, 10.0, 15.0])
    print("  paraboloid max |%%| = %.2e, singlet at 15 deg = %.4f %%" % (max(abs(v) for v in dp["distortion_pct"]), ds["distortion_pct"][-1]))
    ok &= check(max(abs(v) for v in dp["distortion_pct"]) < 1e-6, "paraboloid: zero distortion")
    ok &= check(ds["distortion_pct"][-1] < 0.0, "singlet: barrel (negative) distortion")

    print("(4) delta through the paraboloid = pixel-integrated Airy PSF")
    img = np.zeros((65, 65))
    img[32, 32] = 1.0
    out = LI.render_through_lens(img, parab, 1.0, zones=1, illumination="none")
    pp = LI.psf_from_opd(parab, pixel_pitch_um=1.0, oversample=4)
    c = pp.shape[0] // 2
    ok &= check(np.abs(pp[c - 32:c + 33, c - 32:c + 33] - out).max() < 1e-12, "render == psf_from_opd")

    print("(5) defect dataset through the doublet")
    with tempfile.TemporaryDirectory() as td:
        recs = LI.defect_dataset(4, system=doublet, size=(192, 192), seed=5, out_dir=td)
        ann = json.load(open(os.path.join(td, "annotations.json"), encoding="utf-8"))
        ok &= check(len(recs) == 4 and len(ann["images"]) == 4, "4 records + annotations.json")
        ok &= check(all(os.path.exists(r["image"]) and os.path.exists(r["mask"]) for r in recs), "PNG files written")
        for a in ann["annotations"]:
            x, y, w, h = a["bbox"]
            ok &= 0 <= x and 0 <= y and x + w <= 192 and y + h <= 192
        check(ok, "every bbox inside the image")
        print("  lens:", {k: round(v, 4) for k, v in recs[0]["lens"].items()})
    recs_a = LI.defect_dataset(2, system=doublet, size=(96, 96), seed=9)
    recs_b = LI.defect_dataset(2, system=doublet, size=(96, 96), seed=9)
    ok &= check(all(np.array_equal(a["image"], b["image"]) for a, b in zip(recs_a, recs_b)), "seed reproducible")
    # alignment: a scratch rendered through the lens vs its distortion-only mask
    bg = DG.surface_texture((256, 256), seed=1)
    dimg, dm = DG.defect_scratch((256, 256), length_px=150, width_px=5, angle_deg=30, contrast=-0.4, seed=2)
    comp = DG.composite_defect(bg, dimg, dm)
    r0 = LI.render_through_lens(bg, doublet, 5.5, illumination="none")
    r1 = LI.render_through_lens(comp, doublet, 5.5, illumination="none")
    diff = np.abs(r1 - r0)
    region = diff > 0.5 * diff.max()
    model = LI._lens_model(doublet, (256, 256), 5.5, 3, None, None, None, "traced")
    dmw = LI._remap(dm.astype(np.float64), model, order=0) > 0.5
    iou = (region & dmw).sum() / (region | dmw).sum()
    print("  scratch mask IoU after distortion = %.3f" % iou)
    ok &= check(iou > 0.5, "mask stays aligned with the blurred defect (IoU > 0.5)")
    print("ALL OK" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
