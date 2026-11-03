# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""買う前に受入試験をかける —— 光学式 3D センサの仮想受入試験(VDI/VDE 2634 Part 2 の考え方)と誤差の予算。

Virtual acceptance test of optical 3-D sensors before buying one, and which error source decides the verdict.

1. 3 つの設計案(三角測量 = 構造化光/ステレオの雑音則、iToF 50 MHz で白い試験体、同じ iToF で黒い試験体)を、
   同じ配置(探針の球 1・ダンベル 7 姿勢・平面 7 姿勢)で「測る」。評価 op は実機の点群と同じもの。
2. 閉形式の答え合わせ: 雑音も誤差も無いセンサ → 全評価量 0、距離の尺度 s → SD = (s − 1)·L。
3. iToF 案の誤差の予算: ショット雑音・暗い試験体・fx/fy の校正誤差・距離の尺度・多重反射を 1 つずつ入れ、
   どれが MPE(仮の仕様)を超えるかを数える。

★「準拠」ではなく「考え方に沿った」評価(規格の本文は写していない。定義は公開文献から、acceptance3d の docstring)。
★多重反射は「全画素に一様な第 2 経路」の最も粗いモデル。三角測量は縞を描いて復号せず、雑音則 σ_z = z²σ_d/(f b) だけ。

    PYTHONPATH=. py -3.11 examples/poc_virtual_acceptance_3d.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

import fullseye as fs  # noqa: E402

#: 仮の仕様(メーカーが決める値の例。規格の値ではない)/ an illustrative spec, not a normative value
MPE = {"pf": 3.0, "ps": 1.0, "sd": 0.5, "f": 3.0}

DESIGNS = {
    "triangulation b=100 mm, 0.05 px": {"kind": "triangulation", "baseline_mm": 100.0, "disparity_sigma_px": 0.05},
    "iToF 50 MHz, white artefacts": {"kind": "itof", "sphere_reflectivity": 1.0},
    "iToF 50 MHz, matte black sphere": {"kind": "itof", "sphere_reflectivity": 0.1},
}


def _worst(v):
    v = np.asarray(v, float)
    return float(v[np.argmax(np.abs(v))])


def main():
    layout = fs.ledger.acceptance_layout()
    L, D = layout["bar_length_mm"], layout["sphere_diameter_mm"]
    print("measuring volume %s mm at z = %.0f mm, sphere %.0f mm, ball bar L = %.1f mm"
          % (layout["volume_mm"].tolist(), layout["center_mm"][2], D, L))

    # --- 閉形式の答え合わせ / closed-form checks ----------------------------------------------
    ideal = fs.ledger.virtual_acceptance_test({"kind": "ideal"}, layout)
    for q in ("pf", "ps", "sd", "f"):
        assert max(abs(v) for v in ideal[q]) < 1e-6, (q, ideal[q])
    s = 1.0005
    scaled = fs.ledger.virtual_acceptance_test({"kind": "itof", "noise": False, "range_scale": s}, layout)
    assert np.allclose(scaled["sd"], (s - 1) * L, atol=1e-6), scaled["sd"]
    print("ideal sensor: all |PF|,|PS|,|SD|,|F| < 1e-6 mm;  range scale %.4f: SD = %.4f mm = (s-1)L = %.4f mm"
          % (s, scaled["sd"][0], (s - 1) * L))

    # --- 3 つの設計案 / three designs ------------------------------------------------------------
    print("\nMPE (illustrative spec): %s mm" % MPE)
    print("%-34s %8s %8s %8s %8s  %s" % ("design", "PF", "PS", "SD", "F", "verdict (decided by)"))
    rows = {}
    for name, sensor in DESIGNS.items():
        r = fs.ledger.virtual_acceptance_test(sensor, layout, MPE)
        rows[name] = r
        v = r["verdict"]
        print("%-34s %8.3f %8.3f %8.3f %8.3f  %s (%s, x%.2f)"
              % (name, _worst(r["pf"]), _worst(r["ps"]), _worst(r["sd"]), _worst(r["f"]),
                 "pass" if v["passed"] else "FAIL", v["decided_by"], v["max_ratio"]))
    white = rows["iToF 50 MHz, white artefacts"]["probe"][0]["residual_rms"]
    black = rows["iToF 50 MHz, matte black sphere"]["probe"][0]["residual_rms"]
    print("iToF residual rms on the sphere: white %.3f mm, black %.3f mm (x%.2f; shot-noise limit sqrt(10) = 3.16)"
          % (white, black, black / white))
    assert 2.3 < black / white < 4.2
    assert rows["triangulation b=100 mm, 0.05 px"]["verdict"]["passed"]
    assert not rows["iToF 50 MHz, matte black sphere"]["verdict"]["passed"]

    # --- 誤差の予算 / error budget of the iToF design --------------------------------------------
    factors = {"shot noise": {"noise": True},
               "black sphere (rho 0.1)": {"noise": True, "sphere_reflectivity": 0.1},
               "fx/fy +0.1 %": {"fx_rel_error": 0.001, "fy_rel_error": 0.001},
               "range scale +0.05 %": {"range_scale": 1.0005},
               "multipath 2 %": {"multipath_amplitude": 0.02}}
    b = fs.ledger.acceptance_error_budget({"kind": "itof"}, factors, MPE, layout, n_repeat=2)
    print("\nerror budget (iToF, one factor at a time on a noise-free, error-free baseline)")
    print("%-26s %8s %8s %8s %8s  %s" % ("factor", "PF", "PS", "SD", "F", "worst / MPE"))
    for name in ["(baseline)"] + list(factors) + ["(all together)"]:
        r = b["baseline"] if name == "(baseline)" else b["all"] if name == "(all together)" else b["factors"][name]
        v = r["verdict"]
        print("%-26s %8.3f %8.3f %8.3f %8.3f  x%.2f on %s" % (name, r["pf"], r["ps"], r["sd"], r["f"],
                                                              v["max_ratio"], v["decided_by"]))
    print("decisive (exceeds the MPE alone): %s" % b["decisive"])
    assert b["baseline"]["verdict"]["max_ratio"] < 1e-6
    assert b["decisive"] == ["black sphere (rho 0.1)"]
    assert abs(b["factors"]["range scale +0.05 %"]["sd"] - 0.0005 * L) < 1e-6
    sd_single = sum(abs(b["factors"][k]["sd"]) for k in ("fx/fy +0.1 %", "range scale +0.05 %", "multipath 2 %"))
    print("note: the SD contributions have opposite signs and partly cancel together "
          "(sum of single |SD| %.3f mm vs all-together SD %.3f mm) -- a one-at-a-time ranking does not add up."
          % (sd_single, b["all"]["sd"]))
    print("PASS")


if __name__ == "__main__":
    main()
