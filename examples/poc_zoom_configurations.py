# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: ズームレンズ(多構成)を 1 つの処方で持ち、構成ごとに解析し、.zmx の MNUM 表で往復する。

【問い】間隔だけが違う 3 つの位置(広角・標準・望遠)を、構成ごとに処方を複製せず、差分だけで持てるか。
構成ごとの EFL・スポット・MTF が閉形式と合い、設計ソフトの多構成の表(``MNUM`` と ``THIC`` / ``CRVT`` / ``GLSS`` /
``PRAM`` の行)に書いて読み戻しても同じ構成が出るか。新 op 5 本(`lensconfig`、`opsoptics` の `lensconfig`):
`lens_configurations` / `lens_with_configuration` / `lens_configuration_table` / `lens_configuration_metrics` /
`lens_add_configuration`。`lens_file_read` / `lens_file_write` は `MNUM` の表を読み書きする。4 章:

  1. **閉形式**: 薄肉 2 枚(理想レンズ f1 = 100、f2 = 60 mm)の間隔 d = 10 / 20 / 30 mm。合成焦点距離
     f1·f2/(f1+f2−d) と後端焦点距離 f2·(f1−d)/(f1+f2−d)。門: 1e-9。単一の理想レンズの f を構成ごとに変えると、
     囲みエネルギーは Airy の 83.8 %(半径 1.2197 λ F#)。
  2. **実ガラスの 3 構成**: Cooke 三枚玉の前玉と中玉の間隔を変え、構成ごとに後端を合わせ直す(後端の厚みも構成の欄)。
     表(行 = 変わる量、列 = 構成)、EFL、視野 0° / 10° の RMS スポット、MTF。門: 構成ごとの EFL が違い、合わせ直した
     スポットは有限、基の処方は変わらない。
  3. **.zmx の往復**: 3 構成を MNUM 表つきの .zmx に書き、読み戻す。門: 構成ごとの全上書き値が 1e-12 で一致、EFL が 1e-12、
     書き→読み→書きで同じ表。
  4. **壊して確かめる**: 無い面・未知の欄は ValueError、構成ごとに口径が違う系は .zmx に書けないと拒否(黙って落とさない)。

【外部真値】薄肉 2 枚の閉形式、Airy の囲みエネルギー 83.8 %。表の行の形は公開のズームレンズ .zmx 24 本で確かめた
(docs/capabilities/sequential-lens-design-metrics.md)。【学習】0。【較正】0。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import lensconfig as LC  # noqa: E402
import lensfile as LF  # noqa: E402
import raytrace as RT  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
INF = float("inf")
FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def chapter_closed_form():
    print("\n1. 閉形式(薄肉 2 枚のズーム)")
    f1, f2 = 100.0, 60.0
    ds = (10.0, 20.0, 30.0)
    z = RT.lens_system([{"f": f1, "t": 20.0, "ap": 5.0}, {"f": f2, "t": None}], stop=0, object_mm=INF)
    z["configurations"] = [{"name": "d=%g" % d, "surfaces": {0: {"t": d}}} for d in ds]
    efl = LC.lens_configuration_metrics(z, "efl")["values"]
    bfl = LC.lens_configuration_metrics(z, "bfl")["values"]
    want_e = [f1 * f2 / (f1 + f2 - d) for d in ds]
    want_b = [f2 * (f1 - d) / (f1 + f2 - d) for d in ds]
    de = max(abs(a - b) for a, b in zip(efl, want_e))
    db = max(abs(a - b) for a, b in zip(bfl, want_b))
    for d, e, b in zip(ds, efl, bfl):
        print("   d = %4.1f mm   EFL %.6f mm   BFL %.6f mm" % (d, e, b))
    gate("構成 3 つの EFL は f1·f2/(f1+f2−d) と 1e-9 以内", len(efl) == 3 and de < 1e-9, "最大 %.1e" % de)
    gate("後端焦点距離も閉形式と 1e-9 以内", len(bfl) == 3 and db < 1e-9, "最大 %.1e" % db)
    z4 = LC.lens_add_configuration(z, {0: {"t": 15.0}}, name="d=15")             # 構成を 1 つ足した複製
    e4 = RT.paraxial_trace(LC.lens_with_configuration(z4, 3))["efl"]
    gate("構成を足した複製の 4 番目(k = 3)も閉形式と 1e-9 以内で、元の系は 3 構成のまま",
         abs(e4 - f1 * f2 / (f1 + f2 - 15.0)) < 1e-9 and len(z["configurations"]) == 3 and
         len(z4["configurations"]) == 4, "EFL %.6f mm" % e4)
    NUMBERS.update({"closed_efl_err": de, "closed_bfl_err": db})
    base = RT.lens_system([{"f": 50.0, "t": None, "ap": 5.0}], stop=0, object_mm=INF)
    fs = (40.0, 60.0, 90.0)
    base["configurations"] = [{"surfaces": {0: {"f": f}}} for f in fs]
    ee = []
    for k, f in enumerate(fs):
        one = dict(base, configurations=[base["configurations"][k]])
        r_um = 1.2197 * base["wavelength_um"] * f / 10.0
        ee.append(LC.lens_configuration_metrics(one, "encircled_energy", field=0.0, radius_um=r_um)["values"][0])
    print("   単一の理想レンズの f = %s mm: 半径 1.2197 λ F# の囲みエネルギー %s" % (fs, ["%.4f" % v for v in ee]))
    gate("囲みエネルギーは Airy の 83.8 %(1 pt 以内)", len(ee) == 3 and max(abs(v - 0.838) for v in ee) < 0.01,
         "最大 %.4f" % max(abs(v - 0.838) for v in ee))
    NUMBERS["airy_ee_worst"] = max(abs(v - 0.838) for v in ee)
    return z


def _triplet_zoom():
    p = LF.lens_file_read(None)
    surf = [dict(x) for x in p["system"]["surfaces"]]
    surf[0]["ap"] = 5.0                                   # the stop is the first surface: a fixed pupil
    s = RT.lens_system(surf, stop=0, object_mm=INF)
    gaps = {"wide": 4.5, "mid": 6.00755, "tele": 7.5}     # the air gap after the first lens
    s["configurations"] = [{"name": k, "surfaces": {1: {"t": v}}} for k, v in gaps.items()]
    refocus = []
    for k, c in enumerate(LC.lens_configurations(s)):    # refocus each position: the image distance is a table row too
        refocus.append(dict(s["configurations"][k]))
        refocus[-1]["surfaces"] = dict(refocus[-1]["surfaces"])
        refocus[-1]["surfaces"][len(c["surfaces"]) - 1] = {"t": float(RT.paraxial_trace(c)["bfl"])}
    s["configurations"] = refocus
    p["system"] = s
    return p


def chapter_triplet():
    print("\n2. 実ガラスの 3 構成(Cooke 三枚玉の前玉と中玉の間隔を変える)")
    p = _triplet_zoom()
    s = p["system"]
    t = LC.lens_configuration_table(s)
    for r in t["rows"]:
        print("   %-18s %s" % (r["operand"], ["%.5f" % v for v in r["values"]]))
    efl = LC.lens_configuration_metrics(s, "efl")["values"]
    rms0 = LC.lens_configuration_metrics(s, "rms_spot", field=0.0)["values"]
    rms10 = LC.lens_configuration_metrics(s, "rms_spot", field=10.0)["values"]
    mtf = LC.lens_configuration_metrics(s, "mtf", field=0.0, frequency_cpmm=30.0)["values"]
    for n, e, a, b, m in zip(t["names"], efl, rms0, rms10, mtf):
        print("   %-5s EFL %8.4f mm   RMS 0° %6.1f µm   10° %6.1f µm   MTF(30 本/mm, 軸上) %.3f" % (
            n, e, a * 1e3, b * 1e3, m))
    tele = LC.lens_with_configuration(s, 2)                                     # 望遠側の 1 つだけを取り出す
    gate("取り出した望遠側の処方は一覧の 3 番目と同じ", abs(RT.paraxial_trace(tele)["efl"] - efl[2]) < 1e-12 and
         tele["configuration"] == 2 and tele["configuration_name"] == "tele")
    NUMBERS.update({"efl_wide": efl[0], "efl_tele": efl[2], "rms0_wide_um": rms0[0] * 1e3,
                    "rms0_tele_um": rms0[2] * 1e3, "rms10_tele_um": rms10[2] * 1e3, "mtf30_mid": mtf[1]})
    gate("構成ごとの EFL は互いに 0.1 mm 以上違う", len(efl) == 3 and min(abs(efl[0] - efl[1]), abs(efl[1] - efl[2])) > 0.1,
         "%.3f / %.3f / %.3f mm" % tuple(efl))
    gate("合わせ直した軸上スポットは有限(< 100 µm)", len(rms0) == 3 and all(0.0 < v < 0.1 for v in rms0))
    gate("基の処方に構成の値が漏れない", s["surfaces"][1]["t"] == 6.00755 and "configuration" not in s)
    return p, t, efl, rms0, rms10


def chapter_roundtrip(p):
    print("\n3. .zmx の MNUM 表で往復")
    w = LF.lens_file_write(p)
    rows = w["rows"]
    print("   書いた行: %s、表のはじまり: %s" % (rows, w["text"].split("MNUM")[1].splitlines()[0].strip() or "MNUM"))
    q = LF.lens_file_read(w["text"])
    a = [RT.paraxial_trace(x)["efl"] for x in LC.lens_configurations(p["system"])]
    b = [RT.paraxial_trace(x)["efl"] for x in LC.lens_configurations(q["system"])]
    de = max(abs(x - y) / x for x, y in zip(a, b))
    worst = 0.0
    for ca, cb in zip(LC.lens_configurations(p["system"]), LC.lens_configurations(q["system"])):
        for sa, sb in zip(ca["surfaces"], cb["surfaces"]):
            for k in ("t", "k"):
                worst = max(worst, abs(sa[k] - sb[k]) / max(1.0, abs(sa[k])))
            if sa["R"] != INF or sb["R"] != INF:
                worst = max(worst, abs(sa["R"] - sb["R"]) / abs(sa["R"]))
    again = LF.lens_file_write(q)["text"].split("MNUM")[1]
    print("   読み戻し: %d 構成、EFL の相対差 %.1e、上書き値の最大差 %.1e" % (q["n_configurations"], de, worst))
    gate("構成数 3、書いた表の行 = 後端と間隔の 2 欄 × 3 構成を含む", q["n_configurations"] == 3 and rows["THIC"] >= 2)
    gate("構成ごとの EFL は往復で 1e-12 以内", len(a) == 3 and de < 1e-12, "%.1e" % de)
    gate("構成ごとの全上書き値(R / t / k)は 1e-12 以内", worst < 1e-12, "%.1e" % worst)
    gate("書き→読み→書きで同じ表", again == w["text"].split("MNUM")[1])
    NUMBERS.update({"roundtrip_efl_err": de, "roundtrip_value_err": worst})


def chapter_probes(z):
    print("\n4. 壊して確かめる")
    bad = [({"surfaces": {9: {"t": 1.0}}}, "does not exist"), ({"surfaces": {0: {"thickness": 1.0}}}, "no overridable"),
           ({"system": {"wavelength": 1.0}}, "no overridable system field")]
    n_ok = 0
    for cfg, msg in bad:
        zz = dict(z, configurations=[{}, cfg])
        try:
            LC.lens_configurations(zz)
        except ValueError as e:
            n_ok += int(msg in str(e))
    gate("無い面・未知の欄は ValueError(理由に名前が出る)", n_ok == 3)
    p = _triplet_zoom()
    p["system"]["configurations"][1]["surfaces"][2] = {"ap": 4.0}
    try:
        LF.lens_file_write(p)
        refused = False
    except ValueError as e:
        refused = "clear aperture" in str(e)
    gate("構成ごとに口径が違う系は .zmx に書けないと拒否(黙って落とさない)", refused)


def make_figure(efl, rms0, rms10, names):
    x = np.arange(1, len(names) + 1, dtype=float)
    figs.save_plot("zoom_configurations",
                   [("EFL [mm]", x, np.asarray(efl)), ("RMS スポット 軸上 [µm]", x, np.asarray(rms0) * 1e3),
                    ("RMS スポット 10° [µm]", x, np.asarray(rms10) * 1e3)],
                   xlabel="構成(1 = %s、2 = %s、3 = %s)" % tuple(names), ylabel="EFL [mm] / スポット [µm]",
                   colors=["emphasis", "right", "wrong"],
                   title="3 構成の三枚玉: 前玉と中玉の間隔だけで EFL が %.1f → %.1f mm" % (efl[0], efl[2]),
                   caption="間隔の差分だけを構成に持ち、後端は構成ごとに合わせ直す。スポットは構成ごとの 10° 視野で広がる。")


def main():
    t0 = time.time()
    c0 = time.process_time()
    print("PoC ズームレンズ(多構成)(予算 %s)" % ("reduced" if REDUCED else "full"))
    z = chapter_closed_form()
    p, t, efl, rms0, rms10 = chapter_triplet()
    chapter_roundtrip(p)
    chapter_probes(z)
    if not REDUCED and figs.target_dir() is not None:
        make_figure(efl, rms0, rms10, t["names"])
    cpu = time.process_time() - c0
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件" % (cpu, time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
