# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 光学設計ファイル(.zmx)を読んで、解析して、直して、書き戻す —— 処方の往復と、別の 2 実装との照合。

【問い】市販の逐次光線追跡の設計ソフトで作ったレンズを、そのまま Fullseye の解析(実光線・Seidel・PSF・MTF・
最適化)に載せ、直した処方を同じ形式で返せるか。新 op 4 本(`lensfile`、`opsoptics` の `lensfile`):
`lens_file_read` / `lens_file_system` / `lens_file_write` / `lens_file_report`。7 章:

  1. **読む**: 同梱の Cooke 三枚玉(f ≈ 50 mm、F/5、±20°、硝材は n_d・ν_d のモデル)を読み、全キーワードを
     「読んだ / 無視した(理由つき)/ 扱えない」に分ける。門: 扱えないが 0 件、近似の印が立たない。
  2. **別の 2 実装と照合**: 同じファイルを ray-optics(BSD-3)と optiland(MIT)が**それぞれ自分の読み手で**読んで
     出した値(tests/data/lensfile の記録値)と比べる。門: EFL・BFL・入射瞳が 1e-12、Seidel 和 5 本が 1e-6、
     実光線の像面座標が 1e-6 mm(カタログ硝材の三枚玉と非球面の単レンズ)。
  3. **断面図・スポット・Seidel**: 3 視野 × 3 波長のスポット、面ごとの Seidel 係数。門: 面ごとの和が合計と一致、
     軸上の主光線は原点、視野 20° の主光線の高さが f·tan θ と 1 % 以内(歪曲の大きさ)。
  4. **MTF**: 実収差の瞳から FFT で PSF と MTF。門: 軸上の MTF は回折限界(閉形式)を超えない、Strehl < 1。
  5. **直して書き戻す**: 中央の負レンズの硝材を別のフリント(648/338)に差し替えると処方が崩れる。`lensopt` で
     曲率 6 本を最適化(EFL を元の値に固定)→ `.zmx` に書く → 読み直す。門: 崩れた RMS が設計の 1.3 倍以内に戻る、
     読み直した処方が書いた処方と完全一致、視野・波長・口径が保たれる。
  6. **壊して確かめる**: 曲率つきの座標変換面・未知の面・別名の硝材・曲率の符号の反転。門: 前の 3 つは拒否(理由つき、`lens_file_report` は例外でなく理由を返す)、
     符号の反転は読めてしまう(読み手には分からない)が、第 2 実装との EFL の門が赤になる。
  7. **折り返し(座標変換面)**: 三枚玉の後ろに 45° の折り返し鏡を `COORDBRK` で足した .zmx を読む —— 傾き・偏心は
     `raytrace3d.noncoaxial_system` の break 要素に写り(`lens_file_system` は視野 (x, y) のまま非共軸の系を返す)、
     書き戻しても同じ。門: 折り返した像 = 展開した像の Householder 鏡映(1e-9 mm)、入射瞳の換算(ENPD → 絞りの半径・EFL)が
     共軸の近軸量と 1e-6、書き戻して読み直すと面の表が完全一致、傾きの符号を反転すると鏡映の門が赤。

【外部真値】ray-optics 0.9.8(BSD-3)・optiland 0.6.3(MIT)がそれぞれ読んだ値(記録値。手元に入っていれば
tests/test_lensfile.py がその場で計算し直す)、回折限界の MTF の閉形式、近軸の f·tan θ。【学習】0。【較正】0。

★所見(この PoC を作る途中で見つかり、直したもの): `raytrace` の円錐面の交点は「|t| の小さい根」を選んでいて、
前の面から長い空気間隔の後に R < 0 の面がある望遠型で、**全光線が「けられ」に化けていた**(球の裏側 t < 0 を拾う)。
頂点を含む葉の根を選ぶように直した(tests/test_raytrace_conic_branch_2026_10_18.py)。
★所見 2: 硝材の名前の別名(古い鉛ガラスの名 → 無鉛の N- 硝材)を辿ると、別の硝材に黙って置き換わる。
読み手は別名を辿らず、カタログ(`.agf`)に無ければ拒否する。
★所見 3: 公開の .zmx 15 本を分類すると(最初の記録)、そのまま読めるのが 2、近似の印つきが 1、拒否が 12
(座標変換面・傾き 6、物体側テレセン 1、カタログに無い硝材 5)—— 次の仕事の順番はこの内訳から決めた。座標変換面は
その次の回で読めるようにした(7 章)。
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import lensfile as LF  # noqa: E402
import lensimage as LI  # noqa: E402
import lensopt as LO  # noqa: E402
import optdraw as OD  # noqa: E402
import optics as OP  # noqa: E402
import raytrace as RT  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests", "data", "lensfile")

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def chapter_read():
    print("\n1. 読む(同梱の Cooke 三枚玉)")
    p = LF.lens_file_read(None)
    rep = p["report"]
    pa = RT.paraxial_trace(p["system"])
    NUMBERS.update({"efl": pa["efl"], "bfl": pa["bfl"], "fno": pa["fno"]})
    print("   読んだ %d 行 / 無視 %d 行 / 扱えない %d 件、面 %d、視野 %s°、波長 %s µm(主 %.5f)" % (
        rep["n_read"], rep["n_ignored"], rep["n_unsupported"], len(p["surfaces"]),
        [f["field"] for f in p["fields"]], [w["um"] for w in p["wavelengths"]], p["wavelengths"][p["primary"]]["um"]))
    print("   EFL %.6f mm、BFL %.6f mm、F/%.4f、入射瞳の直径 %.4f mm" % (pa["efl"], pa["bfl"], pa["fno"], 2 * pa["ep_radius"]))
    gate("扱えないキーワード 0 件・近似の印なし", rep["n_unsupported"] == 0 and p["approximate"] is False)
    gate("入射瞳の直径はファイルの ENPD 10 mm(絞りの半径は逆算 %.4f mm)" % p["system"]["surfaces"][p["system"]["stop"]]["ap"],
         abs(2 * pa["ep_radius"] - 10.0) < 1e-12)
    return p


def chapter_second():
    print("\n2. 別の 2 実装(ray-optics・optiland)が同じファイルを読んだ値と照合(記録値)")
    rec = json.load(open(os.path.join(DATA, "second_recorded.json"), encoding="utf-8"))
    rows = []
    worst = {"efl": 0.0, "seidel": 0.0, "ray": 0.0}
    n_rays = 0
    for name in sorted(rec):
        p = LF.lens_file_read(os.path.join(DATA, name))
        pa = RT.paraxial_trace(p["system"])
        ro = rec[name]["rayoptics"]
        d_efl = abs(pa["efl"] - ro["efl"]) / ro["efl"]
        se = RT.seidel_coefficients(LF.lens_file_system(p, field_index=len(p["fields"]) - 1))["total"]
        scale = max(abs(v) for v in ro["seidel"].values())
        d_se = max(abs(se[k.replace("-", "_")] - v) for k, v in ro["seidel"].items()) / scale
        ol = rec[name]["optiland"]
        d_ray = float("nan")
        if "error" not in ol and math.isfinite(ol["efl"]):
            s = RT.with_wavelength(p["system"], ol["wl"])
            e = RT.paraxial_trace(s)["ep_radius"]
            dys = []
            for k, yv in ol["axis_rays"].items():
                r = RT.trace_rays(s, np.array([[0.0, float(k) * e, -1.0]]), np.array([[0.0, 0.0, 1.0]]))
                dys.append(abs(r["points"][0, -1, 1] - yv))
            for fr in ol["field_rays"]:
                P1, D = np.array(fr["p1"]), np.array(fr["dir"])
                O = P1 + ((-5.0 - P1[2]) / D[2]) * D
                r = RT.trace_rays(s, O[None], D[None])
                dys.append(abs(r["points"][0, -1, 1] - fr["image_y"]))
            d_ray = float(max(dys))
            n_rays += len(dys)
            worst["ray"] = max(worst["ray"], d_ray)
        worst["efl"] = max(worst["efl"], d_efl)
        worst["seidel"] = max(worst["seidel"], d_se)
        label = {"triplet_const.zmx": "三枚玉(屈折率一定)", "triplet_catalog.zmx": "三枚玉(カタログ硝材)",
                 "double_gauss_const.zmx": "ダブルガウス F/5", "asphere_singlet.zmx": "非球面の単レンズ"}[name]
        rows.append([label, "%.6f" % pa["efl"], "%.1e" % d_efl, "%.1e" % d_se, "—" if math.isnan(d_ray) else "%.1e" % d_ray])
        print("   %-22s EFL %.6f  相対差 %.1e  Seidel %.1e  実光線 %s mm" % (label, pa["efl"], d_efl, d_se,
                                                                       "—" if math.isnan(d_ray) else "%.1e" % d_ray))
    NUMBERS.update({"worst_efl": worst["efl"], "worst_seidel": worst["seidel"], "worst_ray": worst["ray"], "n_rays": n_rays})
    gate("近軸(EFL)は 4 設計とも 2 実装と 1e-12 以内", worst["efl"] < 1e-12, "最大 %.1e" % worst["efl"])
    gate("Seidel 和 5 本は ray-optics の 3 次収差と 1e-6 以内(最大の和で規格化)", worst["seidel"] < 1e-6, "最大 %.1e" % worst["seidel"])
    gate("実光線 %d 本の像面座標は optiland と 1e-6 mm 以内" % n_rays, n_rays == 14 and worst["ray"] < 1e-6, "最大 %.1e mm" % worst["ray"])
    return rows


def chapter_analysis(p):
    print("\n3. 断面図・スポット・Seidel")
    spots = []
    for fi in range(len(p["fields"])):
        for wi in range(len(p["wavelengths"])):
            s = LF.lens_file_system(p, field_index=fi, wavelength_index=wi)
            img = p["system"]["surfaces"][-1]["t"]
            b = RT.ray_bundle(s, rings=8, image_mm=img, pupil_fill=0.98)
            xy = b["image_xy"][b["valid"]]
            spots.append((fi, wi, xy, b["chief_xy"]))
    chief0 = [c for fi, wi, xy, c in spots if fi == 0 and wi == p["primary"]][0]
    gate("軸上の主光線は像の原点(|y| < 1e-12 mm)", abs(chief0[1]) < 1e-12)
    s20 = LF.lens_file_system(p, field_index=2)
    ys = [c for fi, wi, xy, c in spots if fi == 2 and wi == p["primary"]][0][1]
    ideal = NUMBERS["efl"] * math.tan(math.radians(20.0))
    dist = (abs(ys) - ideal) / ideal
    NUMBERS["distortion_20"] = dist
    gate("視野 20° の主光線の高さ %.4f mm は f·tan θ = %.4f mm と 1 %% 以内(歪曲 %+.2f %%)" % (abs(ys), ideal, 100 * dist),
         abs(dist) < 0.01)
    rms = {}
    for fi in range(len(p["fields"])):
        pool = np.concatenate([xy for f, w, xy, c in spots if f == fi], 0)
        rms[fi] = float(np.sqrt(np.mean(np.sum((pool - pool.mean(0)) ** 2, 1))))
    NUMBERS.update({"rms0_um": 1e3 * rms[0], "rms20_um": 1e3 * rms[2]})
    print("   多色の RMS スポット: 0° %.2f µm、14° %.2f µm、20° %.2f µm" % (1e3 * rms[0], 1e3 * rms[1], 1e3 * rms[2]))
    se = RT.seidel_coefficients(s20)
    tot = se["total"]
    sums = {k: sum(r[k] for r in se["per_surface"]) for k in tot}
    gate("面ごとの Seidel 係数の和が合計と一致(7 本、1e-15)", all(abs(sums[k] - tot[k]) < 1e-15 for k in tot))
    print("   Seidel 和(20°): S_I %.5f  S_II %.5f  S_III %.5f  S_IV %.5f  S_V %.5f mm" %
          tuple(tot[k] for k in ("S_I", "S_II", "S_III", "S_IV", "S_V")))
    return spots, se


def chapter_mtf(p):
    print("\n4. MTF(実収差の瞳 → FFT)")
    s0 = LF.lens_file_system(p, field_index=0)
    psf, _ref, dx_um, _n = LI._psf_core(s0, 0.0, None, None, 4)
    psf = psf / psf.sum()
    mtf = OP.psf_to_mtf(psf, pixel_pitch_um=dx_um)
    fno = RT.paraxial_trace(s0)["fno"]
    lim = OP.mtf_diffraction(fno, s0["wavelength_um"], 128)
    f = mtf[:, 0]
    keep = f < lim[-1, 0]
    lim_i = np.interp(f[keep], lim[:, 0], lim[:, 1])
    over = float(np.max(mtf[keep, 1] - lim_i))
    gate("軸上の MTF は回折限界(閉形式)を超えない(最大の超過 %.3f ≤ 0.02、半径平均の格子の屑)" % over, over <= 0.02)
    mtf50 = float(np.interp(50.0, f, mtf[:, 1]))
    NUMBERS.update({"mtf50": mtf50, "fno": fno, "cutoff": float(lim[-1, 0])})
    print("   F/%.3f、遮断周波数 %.0f 本/mm、50 本/mm の MTF %.3f(回折限界 %.3f)" % (
        fno, lim[-1, 0], mtf50, float(np.interp(50.0, lim[:, 0], lim[:, 1]))))
    gate("50 本/mm の MTF %.3f は回折限界より低く 0 より大きい(収差がある実レンズ)" % mtf50,
         0.0 < mtf50 < float(np.interp(50.0, lim[:, 0], lim[:, 1])))
    s20 = LF.lens_file_system(p, field_index=2)
    psf20, _r, dx20, _n = LI._psf_core(s20, 20.0, None, None, 4)
    psf20 = psf20 / psf20.sum()
    otf = np.abs(np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(psf20))))
    otf /= otf.max()
    n = otf.shape[0]
    c = n // 2
    fr = np.arange(n // 2) / (n * dx20 * 1e-3)                # cycles/mm
    tan = otf[c:c + n // 2, c]                               # along y (tangential)
    sag = otf[c, c:c + n // 2]                               # along x (sagittal)
    return (mtf, lim, fr, tan, sag)


#: 中央の負レンズの硝材を差し替える先: 重いフリント 648/338(n_d 1.64769、ν_d 33.84)。元は 620/364。
SUBSTITUTE_FLINT = (1.64769, 33.84)


def chapter_edit(p):
    print("\n5. 硝材を差し替えて崩れた処方を、lensopt で直して .zmx に書き戻す")
    s = LF.lens_file_system(p, field_index=0)
    fields = [f["field"] for f in p["fields"]]
    wls = [w["um"] for w in p["wavelengths"]]
    kw = dict(fields=fields, wavelengths=wls, rings=3)
    m0 = LO.merit_function(s, **kw)
    surf = [dict(x) for x in s["surfaces"]]
    surf[2]["n"] = SUBSTITUTE_FLINT
    broken = RT.lens_system(surf, stop=s["stop"], object_mm=s["object_mm"], wavelength_um=s["wavelength_um"],
                            index_object=s["index_object"])
    m1 = LO.merit_function(broken, **kw)
    iters = 8 if REDUCED else 30
    res = LO.optimize_lens(broken, efl_target=RT.paraxial_trace(s)["efl"], iterations=iters, **kw)
    NUMBERS.update({"rms_design_um": 1e3 * m0["rms_spot"], "rms_before_um": 1e3 * res["rms_initial"],
                    "rms_after_um": 1e3 * res["rms_final"], "efl_after": res["efl_final"]})
    print("   RMS(3 視野 × 3 波長): 設計 %.2f µm → 中央の硝材を 648/338 に差し替え %.2f µm → 曲率 6 本を最適化 %.2f µm"
          "(EFL %.4f → %.4f mm、反復 %d)" % (1e3 * m0["rms_spot"], 1e3 * m1["rms_spot"], 1e3 * res["rms_final"],
                                          res["efl_initial"], res["efl_final"], res["iterations"]))
    gate("硝材の差し替えで処方が崩れる(RMS %.1f → %.1f µm、EFL %.2f mm)" % (
        1e3 * m0["rms_spot"], 1e3 * m1["rms_spot"], RT.paraxial_trace(broken)["efl"]), m1["rms_spot"] > 1.5 * m0["rms_spot"])
    gate("最適化で設計の RMS の 1.3 倍以内まで戻る(%.1f µm)" % (1e3 * res["rms_final"]),
         res["rms_final"] < 1.3 * m0["rms_spot"])
    gate("EFL を元の値に保つ(|ΔEFL| < 0.05 mm)", abs(res["efl_final"] - RT.paraxial_trace(s)["efl"]) < 0.05)
    w = LF.lens_file_write(p, system=res["system"])
    q = LF.lens_file_read(w["text"])
    same = all(a[k] == b[k] for a, b in zip(q["system"]["surfaces"], res["system"]["surfaces"]) for k in ("R", "t", "k", "asph"))
    gate("書いた .zmx を読み直すと処方が完全一致(R・t・円錐・非球面、%d 面)" % len(q["system"]["surfaces"]), same)
    gate("視野・波長・主波長が保たれる", q["fields"] == p["fields"] and q["wavelengths"] == p["wavelengths"]
         and q["primary"] == p["primary"])
    gate("入射瞳の直径が保たれる(%.6f mm)" % (2 * RT.paraxial_trace(q["system"])["ep_radius"]),
         abs(RT.paraxial_trace(q["system"])["ep_radius"] - RT.paraxial_trace(res["system"])["ep_radius"]) < 1e-12)
    return res, w["text"]


def chapter_probes():
    print("\n6. 壊して確かめる")
    t = LF.ZMX_EXAMPLE
    cases = [("曲率つきの座標変換面", t.replace("SURF 2\n  TYPE STANDARD", "SURF 2\n  TYPE COORDBRK"), "COORDBRK"),
             ("未知の面のキーワード", t.replace("  DISZ 6.00755\n", "  DISZ 6.00755\n  ZZZZ 1 2 3\n"), "allow_partial"),
             ("別名でしか表に無い硝材", t.replace("___BLANK 1 0 1.62004 36.37", "F2 0 0 1.5 40"), "no catalogue")]
    for label, text, key in cases:
        try:
            LF.lens_file_read(text)
            gate("%s は拒否される" % label, False)
        except ValueError as e:
            gate("%s は拒否される" % label, key in str(e), str(e)[:110] + "…")
    # lens_file_report: 読み込まずに分類する(古いファイルの束の仕分け)。例外を出さずに理由を返す。
    r = LF.lens_file_report(cases[0][1])
    vig = LF.lens_file_report(t.replace("PWAV 2\n", "PWAV 2\nVDYN 0 0.1 0.2 0 0 0 0 0 0 0 0 0\n"))
    print("   lens_file_report: 曲率つきの座標変換面 → 読める %s / 近似なら %s、面の種類 %s;ケラレ係数つき → 読める %s / 近似なら %s" % (
        r["importable"], r["needs_allow_partial"], r["surface_types"], vig["importable"], vig["needs_allow_partial"]))
    gate("lens_file_report は拒否の理由を例外でなく返し、近似で読めるものを分ける",
         r["importable"] is False and r["needs_allow_partial"] is False and "COORDBRK" in (r["error"] or "")
         and vig["importable"] is False and vig["needs_allow_partial"] is True)
    rec = json.load(open(os.path.join(DATA, "second_recorded.json"), encoding="utf-8"))["triplet_const.zmx"]["rayoptics"]
    src = open(os.path.join(DATA, "triplet_const.zmx"), encoding="ascii").read()
    bad = LF.lens_file_read(src.replace("CURV 0.045426484276303865", "CURV -0.045426484276303865"))
    d = abs(RT.paraxial_trace(bad["system"])["efl"] - rec["efl"])
    gate("第 1 面の曲率の符号を反転すると第 2 実装との EFL の門が赤(差 %.1f mm)" % d, d > 1.0)


def chapter_coordbrk(p):
    print("\n7. 折り返し(座標変換面 COORDBRK)")
    import raytrace3d as R3
    tail = '  DISZ 42.20778\n  DIAM 7.0 0 0 0 1 ""\nSURF 7\n  TYPE STANDARD\n  CURV 0 0 0 0 0 ""\n  DISZ 0\n'
    assert LF.ZMX_EXAMPLE.count(tail) == 1
    cb = ('SURF %d\n  TYPE COORDBRK\n  PARM 1 0\n  PARM 2 0\n  PARM 3 45\n  PARM 4 0\n  PARM 5 0\n  PARM 6 0\n  DISZ %s\n')
    fold = ('  DISZ 20\n  DIAM 7.0 0 0 0 1 ""\n' + cb % (7, "0") +
            'SURF 8\n  TYPE STANDARD\n  CURV 0 0 0 0 0 ""\n  DISZ 0\n  GLAS MIRROR 0 0 1.5 40 0 0 0 0 0 0\n' +
            cb % (9, "-22.20778") + 'SURF 10\n  TYPE STANDARD\n  CURV 0 0 0 0 0 ""\n  DISZ 0\n')
    text = LF.ZMX_EXAMPLE.replace(tail, fold)
    q = LF.lens_file_read(text)
    sysd = q["system"]
    lay = R3.noncoaxial_layout(sysd)
    print("   %d 面 → 記録 %d 本(break %d 本・鏡 %d 枚)、像面の法線 %s、x の視野は半径に畳まず (x, y) のまま %s" % (
        len(q["surfaces"]), len(sysd["records"]), sum(1 for r in sysd["records"] if r["kind"] == "break"),
        lay["n_reflections"], np.round(lay["image"]["normal"], 6).tolist(), [f["field"] for f in q["fields"]]))
    # 入射瞳の換算: 共軸の近軸量と一致(ENPD → 絞りの半径、実光線の有効焦点距離)
    para = RT.paraxial_trace(p["system"])
    ap0 = p["system"]["surfaces"][p["system"]["stop"]]["ap"]
    gate("入射瞳の換算: 絞りの半径 %.6f mm・EFL %.6f mm は共軸の近軸量と 1e-6" % (q["pupil"]["stop_radius_mm"], q["pupil"]["efl_mm"]),
         abs(q["pupil"]["stop_radius_mm"] - ap0) < 1e-6 * ap0 and abs(q["pupil"]["efl_mm"] - abs(para["efl"])) < 1e-6 * abs(para["efl"]))
    # 折り返した像 = 展開した像の Householder 鏡映(鏡の頂点 p0、法線 n)
    unfolded = R3.noncoaxial_system(p["system"])
    z_mirror = sum(s_["t"] for s_ in p["system"]["surfaces"][:-1]) + 20.0
    n = RT._rot(45.0, 0.0)[:, 2]
    p0 = np.array([0.0, 0.0, z_mirror])
    worst = 0.0
    for f in q["fields"]:
        a = R3._chief(sysd, f["field"])["points"][0, -1]
        b = R3._chief(unfolded, f["field"])["points"][0, -1]
        worst = max(worst, float(np.abs(a - (b - 2.0 * ((b - p0) @ n) * n)).max()))
    gate("折り返した像 = 展開した像の Householder 鏡映(3 視野の主光線、最大 %.1e mm)" % worst, worst < 1e-9)
    # 書き戻し
    w = LF.lens_file_write(q)
    r = LF.lens_file_read(w["text"])
    gate("書き戻して読み直すと面の表が完全一致(COORDBRK %d 面を含む)" % sum(1 for x in r["surfaces"] if x["type"] == "COORDBRK"),
         r["surfaces"] == q["surfaces"] and "TYPE COORDBRK" in w["text"] and r["system"]["elements"] == sysd["elements"])
    # 編集した非共軸の系 (system=) も COORDBRK で書ける
    w2 = LF.lens_file_write(None, system=R3.noncoaxial_example("periscope"))
    gate("noncoaxial_system の break から COORDBRK を書き、読み直した系が同じ光線を追う",
         "TYPE COORDBRK" in w2["text"] and LF.lens_file_read(w2["text"])["noncoaxial"])
    # 探針: 鏡の前の傾きの符号を反転すると、像は鏡映から外れる
    bad = LF.lens_file_read(text.replace("PARM 3 45\n  PARM 4 0\n  PARM 5 0\n  PARM 6 0\n  DISZ 0\n", "PARM 3 -45\n  PARM 4 0\n  PARM 5 0\n  PARM 6 0\n  DISZ 0\n", 1))
    bad_n = np.array(R3.noncoaxial_layout(bad["system"])["image"]["normal"])
    gate("鏡の前の傾きの符号を反転すると像面の向きが変わり鏡映の門が赤(法線の差 %.2f)" % np.abs(bad_n - lay["image"]["normal"]).max(),
         np.abs(bad_n - np.array(lay["image"]["normal"])).max() > 0.5)
    return worst


def make_figures(p, spots, se, mtfs, opt, rows):
    s20 = LF.lens_file_system(p, field_index=2)
    d = OD.lens_section_drawing(s20, fields=[0.0, 14.0, 20.0], rays=5, title="Cooke triplet f/5 (.zmx import)")
    figs.save("layout", OD.drawing_raster(d, dpi=110).astype(np.float64) / 255.0,
              caption="読み込んだ処方の子午断面図(optdraw)。視野 0・14・20° の実光線 5 本ずつ、寸法は EFL・BFL・全長・像高。")
    series, colors = [], []
    cols = ("reference", "emphasis", "wrong")
    names = ("F 486 nm", "d 588 nm", "C 656 nm")
    for fi in range(3):
        cy = [sp for sp in spots if sp[0] == fi and sp[1] == p["primary"]][0][2][:, 1].mean()
        for wi in range(3):
            xy = [sp for sp in spots if sp[0] == fi and sp[1] == wi][0][2]
            series.append((names[wi] if fi == 0 else "", 1e3 * xy[:, 0] + 100.0 * fi, 1e3 * (xy[:, 1] - cy) - 100.0 * wi))
            colors.append(cols[wi])
    figs.save_plot("spot_diagram", series, xlabel="x [µm](列 = 視野 0° / 14° / 20°、100 µm 間隔)",
                   ylabel="y − d 線の重心 [µm](行 = F / d / C、100 µm 間隔)", kinds=["scatter"] * len(series),
                   colors=colors, aspect="equal", size=(560, 560),
                   title="スポット: RMS 0° %.1f µm / 20° %.1f µm" % (NUMBERS["rms0_um"], NUMBERS["rms20_um"]),
                   caption="3 視野 × 3 波長(瞳の 98 % を 8 輪)。各スポットは d 線の重心を基準に置いたので、F / C の行の上下のずれが倍率の色収差、広がりが球面収差・コマ・非点。")
    per = list(se["per_surface"]) + [dict(se["total"], surface="sum")]
    x = np.arange(1, len(per) + 1, dtype=float)
    x[-1] += 0.6
    keys = ("S_I", "S_II", "S_III", "S_IV", "S_V")
    sseries = []
    for j, k in enumerate(keys):
        xs = np.repeat(x + (j - 2) * 0.13, 2)
        ys = np.ravel([[0.0, r[k]] for r in per])
        for i in range(len(per)):
            sseries.append((k if i == 0 else "", xs[2 * i:2 * i + 2], ys[2 * i:2 * i + 2]))
    figs.save_plot("seidel_bars", sseries, xlabel="面の番号(視野 20°)、右端 = 合計", ylabel="Seidel 係数 [mm]",
                   xlim=(0.4, float(x[-1]) + 0.6),
                   colors=[("reference", "emphasis", "right", "wrong", "neutral")[j] for j in range(5) for _ in per],
                   title="面ごとの Seidel 係数(縦棒)—— 前後の正レンズの寄与を中央の負レンズが打ち消す",
                   caption="S_I 球面、S_II コマ、S_III 非点、S_IV ペッツバール、S_V 歪曲。和は ray-optics の 3 次収差と 1e-6 で一致。")
    mtf, lim, fr, tan, sag = mtfs
    keep = fr <= lim[-1, 0]
    k0 = mtf[:, 0] <= lim[-1, 0]
    figs.save_plot("mtf", [("軸上(FFT、半径平均)", mtf[k0, 0], mtf[k0, 1]),
                           ("20° 子午", fr[keep], tan[keep]), ("20° 球欠", fr[keep], sag[keep]),
                           ("回折限界 F/%.2f" % NUMBERS["fno"], lim[:, 0], lim[:, 1])],
                   xlabel="空間周波数 [本/mm]", ylabel="MTF", ylim=(0.0, 1.02), xlim=(0.0, float(lim[-1, 0])),
                   styles=[None, None, "dotted", "dashed"], colors=["emphasis", "right", "wrong", "reference"],
                   title="MTF: 50 本/mm で %.2f(軸上)" % NUMBERS["mtf50"],
                   caption="実収差の瞳(OPD)から PSF を FFT で作り、その FFT が MTF。破線は無収差の円形瞳の閉形式(上限)。")
    res, _text = opt
    h = np.asarray(res["history"], float)
    if len(h) >= 2:
        figs.save_plot("optimisation", [("merit", np.arange(len(h), dtype=float), np.log10(h))],
                       xlabel="反復(受理したステップ)", ylabel="log10(merit = Σ 横収差² [mm²])", kinds=["line"], title="硝材を差し替えて崩れた処方を直す: RMS %.1f → %.1f µm(設計 %.1f)" % (
                           NUMBERS["rms_before_um"], NUMBERS["rms_after_um"], NUMBERS["rms_design_um"]),
                       caption="中央の負レンズを重いフリント 648/338 に差し替えて崩れた三枚玉を、6 面の曲率を変数に EFL を元の値に固定して直す。結果を .zmx に書き戻す。")
    figs.save_table("second_implementations", ["設計", "EFL [mm]", "EFL の相対差", "Seidel の差", "実光線の差 [mm]"], rows,
                    title="別の 2 実装(ray-optics / optiland)が同じ .zmx を読んだ値との差",
                    caption="記録値(tests/data/lensfile/second_recorded.json)。optiland は n_d だけの硝材(ν_d = 0)を評価できないので —。")


def main():
    t0 = time.time()
    c0 = time.process_time()
    print("PoC 光学設計ファイル(.zmx)の往復(予算 %s)" % ("reduced" if REDUCED else "full"))
    p = chapter_read()
    rows = chapter_second()
    spots, se = chapter_analysis(p)
    mtfs = chapter_mtf(p)
    opt = chapter_edit(p)
    chapter_probes()
    NUMBERS["fold_worst_mm"] = chapter_coordbrk(p)
    if not REDUCED and figs.target_dir() is not None:
        make_figures(p, spots, se, mtfs, opt, rows)
    cpu = time.process_time() - c0
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件" % (cpu, time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
