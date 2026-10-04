# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""視触覚センサ(弾性膜 + カメラ)の合成と逆算 —— Hertz 接触とフォトメトリックステレオの閉形式を門に、球の押し込みから力を読む(2026-10-04)。

物理シミュ × Fullseye 系列の第 2 弾(「自作の罠は限界: 真値・門・被験者の 1 つを外から」)。外から来るものは閉形式 2 系統:
  * **弾性接触** = Hertz(Johnson, *Contact Mechanics*, CUP 1985): a³ = 3FR/(4E*)、δ = a²/R、p = p0√(1 − r²/a²)、半空間の表面変位
    (内側 δ − r²/(2R)、外側 Johnson 式 3.42a)。線接触 b² = 4(F/L)R/(πE*)。
  * **光学** = Woodham 1980 のフォトメトリックステレオ(N = L⁻¹I)+ Frankot-Chellappa 1988 の法線積分。弾性膜を 3 色の方向照明で
    撮って 1 枚で法線を読む原理は Johnson & Adelson, CVPR 2009(retrographic sensing)。
自分で作ったのは 3 つ: Hertz の外側解の **半径方向スロープの閉形式** dh/dr = (2/πR)[r arcsin(a/r) − a√(1 − a²/r²)](導出、r = a で
a/R に連続)、それを法線場のスロープ分布に 1 パラメータ a で当てる逆算(高さの積分を通らない)、δ の 1D 積分に Boussinesq の遠方場
ū_z ≈ F/(πE*r) の裾 r_max·s̄(r_max) を足す窓打ち切りの補正。被験者は Fullseye の既存 op(photometric 系 4 op、measure.fit_circle)。

門(numpy、常に走る、17 本): 複合弾性率の極限、Hertz の恒等式、圧力の面積分 = F・線積分 = F/L、表面変位の内外連続(値 δ/2・
傾き −a/R)とスロープ閉形式の導出検算(数値微分と 1e-7)、Frankot-Chellappa の往復、Woodham の厳密性(中央 < 0.05°)、
当てはめ経路 a ≤ 1 %・F ≤ 2 %(4 荷重)、δ 経路 δ ≤ 2 %・F ≤ 3 %、模型なしのリングは −0.7 px/a の予測どおり内側(分解能の限界)、
a ∝ F^{1/3}(指数 0.33 ± 0.01)、窓打ち切りの不足 = ū_z(r_max)/δ の閉形式(4.7 %)と 1 pt 以内、ambient を引かないと
δ が ambient/sin(仰角) ≈ 3.7 % 低い、照明仰角の 15° 較正ずれは斜面だけを壊す、雑音で単調に悪化、4 形状(球・円柱・直線エッジ・
スタンプ)の往復と円柱の幾何接触幅 √(2Rd − d²)、別被験者 tac_contact_mask は弾性の裾まで拾う。

図(FULLSEYE_FIGURE_DIR があるとき、7 枚): 圧痕まわりの等倍切り出し(62.5 µm/px)、4 形状のグリッド(合成 RGB + 復元高さ)、
力を 0 → 0.12 N に上げる GIF(左 合成 RGB、右 a–F の Hertz 曲線に点が増える)、復元高さと真値の断面、スロープ分布と Hertz 模型、
a–F に 2 経路の測定点、壊れる場所(較正ずれ・雑音)。

正直に: 小変形 Hertz(δ/R ≈ 0.09)、Lambertian・影なし・鏡面なし、膜は半無限、粘弾性・マーカーなし。模型なしのリングは a が 14 px の
分解能では 5 % 内側に出る(当てはめ経路が主、リングは第 2 実装)。試作 v1 で踏んだ罠: |∇h| のしきい値の帯は 9 % 内側(カスプが
非対称)、FFT 積分は深いへこみの振幅を 13 % 減衰、ambient 項が法線を 3.7 % 寝かせる。
Run: py -3.11 examples/poc_tacsim_elastic_membrane.py
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import measure as FM  # noqa: E402
import photometric as PH  # noqa: E402
import tacsim as T  # noqa: E402

try:
    import backends_tactile as TAC  # noqa: E402
except Exception:  # noqa: BLE001
    TAC = None

_GATES = []
_trapz = getattr(np, "trapezoid", None) or np.trapz
E_GEL, NU_GEL, R_BALL = 0.2e6, 0.48, 3.0e-3          # 柔らかいシリコン膜(E ≈ 0.2 MPa, ν ≈ 0.48)、剛体球 R = 3 mm
N_PX, FOV, AMB, ELEV = 256, 16.0e-3, 0.03, 55.0        # 256 px、視野 16 mm(62.5 µm/px)、ambient 0.03、仰角 55°
LOADS = (0.02, 0.05, 0.08, 0.12)


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def _pct(v, t):
    return 100.0 * (v - t) / t


def _scene(F, Estar, lights, noise=0.0, seed=0):
    hz = T.hertz_sphere(F, R_BALL, Estar)
    gh = T.membrane_indent_sphere(hz, N_PX, FOV)
    rgb = T.membrane_render_rgb(gh["normals"], lights, ambient=AMB, noise=noise, seed=seed)
    rec = T.membrane_recover(rgb, lights, gh["pitch"], ambient=AMB)
    return hz, gh, rgb, rec


def numpy_part():
    print("== 門(閉形式・合成・逆算・破れ)")
    Es = T.combined_modulus(E_GEL, NU_GEL)
    gate("複合弾性率: 剛体の押し込み子で E* = E/(1 − ν²)、同じ材料 2 体で E* = E/(2(1 − ν²))、E ≤ 0 は ValueError",
         abs(Es - E_GEL / (1 - NU_GEL ** 2)) < 1e-6 and abs(T.combined_modulus(E_GEL, NU_GEL, E_GEL, NU_GEL) - Es / 2) < 1e-6
         and _raises(lambda: T.combined_modulus(0.0, 0.3)), "E* = %.3f MPa" % (Es * 1e-6))
    F = 0.08
    hz = T.hertz_sphere(F, R_BALL, Es)
    a, d, p0 = hz["a"], hz["delta"], hz["p0"]
    gate("Hertz の恒等式: a² = Rδ、F = (4/3)E*√R δ^{3/2} = 4E*a³/(3R)、p0 = 3F/(2πa²) = 2E*a/(πR)、pm = (2/3)p0(相互に 1e-9)",
         abs(a * a - R_BALL * d) < 1e-18 and abs(T.hertz_force(R_BALL, Es, delta=d) - F) < 1e-9
         and abs(T.hertz_force(R_BALL, Es, a=a) - F) < 1e-9 and abs(p0 - 2 * Es * a / (math.pi * R_BALL)) < 1e-6
         and abs(hz["pm"] - 2 * p0 / 3) < 1e-6, "a = %.3f mm, δ = %.3f mm, p0 = %.1f kPa" % (a * 1e3, d * 1e3, p0 * 1e-3))
    rr = np.linspace(0, a, 20001)
    disk = 2 * math.pi * _trapz(T.hertz_pressure(rr, a, p0) * rr, rr)
    cyl = T.hertz_cylinder(50.0, R_BALL, Es)
    xs = np.linspace(-cyl["b"], cyl["b"], 20001)
    line = _trapz(cyl["p0"] * np.sqrt(np.maximum(0, 1 - (xs / cyl["b"]) ** 2)), xs)
    gate("圧力分布の積分: 球の p(r) をディスクで積分すると F、円柱の p(x) を線で積分すると F/L(どちらも < 0.1 %)、b² = 4(F/L)R/(πE*)",
         abs(disk - F) / F < 1e-3 and abs(line - 50.0) / 50.0 < 1e-3 and abs(cyl["b"] ** 2 - 4 * 50 * R_BALL / (math.pi * Es)) < 1e-18,
         "∫p dA = %.5f N, ∫p dx = %.3f N/m, b = %.3f mm" % (disk, line, cyl["b"] * 1e3))
    r_in = np.linspace(0, a, 200)
    uz_in = T.hertz_surface_uz(r_in, a, d, R_BALL)
    eps = 1e-7 * a
    step = abs(T.hertz_surface_uz(np.array([a - eps]), a, d, R_BALL)[0] - T.hertz_surface_uz(np.array([a + eps]), a, d, R_BALL)[0])
    r_all = np.linspace(0.05 * a, 5 * a, 3000)
    hnum = 1e-9
    num = -(T.hertz_surface_uz(r_all + hnum, a, d, R_BALL) - T.hertz_surface_uz(r_all - hnum, a, d, R_BALL)) / (2 * hnum)
    slope_err = float(np.max(np.abs(num - T._hertz_slope(r_all, a, R_BALL)) / (a / R_BALL)))
    gate("表面変位(Johnson 3.42a): ū_z(0) = δ、内側は δ − r²/(2R)(1e-12)、r = a で値 δ/2 が連続(段差 < 1e-9 m)、"
         "スロープの閉形式 (2/πR)[r arcsin(a/r) − a√(1−a²/r²)](導出)が数値微分と 1e-6 で一致し r = a で a/R",
         abs(uz_in[0] - d) < 1e-15 and np.max(np.abs(uz_in - (d - r_in ** 2 / (2 * R_BALL)))) < 1e-12 and step < 1e-9
         and slope_err < 1e-6 and abs(T._hertz_slope(np.array([a]), a, R_BALL)[0] - a / R_BALL) < 1e-15,
         "段差 %.1e m、スロープの相対誤差 max %.1e" % (step, slope_err))
    lights = T.membrane_lights(ELEV)
    t0 = time.time()
    hz, gh, rgb, rec = _scene(F, Es, lights)
    pitch = gh["pitch"]
    inside = gh["r"] < 1.5 * a
    z = PH.integrate_normals(gh["normals"]) * pitch
    rms_fc = float(np.sqrt(np.mean(((z - z[inside].mean()) - (gh["h"] - gh["h"][inside].mean()))[inside] ** 2)))
    gate("Frankot-Chellappa の往復: 真値の法線を integrate_normals して真の高さに戻る(r < 1.5a で RMS < δ の 1 %)",
         rms_fc < 0.01 * d, "RMS %.3f µm / δ %.1f µm" % (rms_fc * 1e6, d * 1e6))
    ang = PH.angular_error_deg(rec["normals"], gh["normals"])
    ndl = np.min(np.stack([gh["normals"] @ lights[k] for k in range(3)], 0), 0)
    lit = ndl > 0.05
    slope_px = (gh["normals"][..., 2] < 0.98) & lit
    gate("Woodham の厳密性(ambient を較正して引く): 影のない域で復元法線の中央角誤差 < 0.05°、99 % 点 < 1°",
         float(np.median(ang[lit])) < 0.05 and float(np.percentile(ang[lit], 99)) < 1.0,
         "中央 %.4f°, 99 %% %.3f°, 斜面の中央 %.3f°" % (np.median(ang[lit]), np.percentile(ang[lit], 99), np.median(ang[slope_px])))
    # 3 経路 × 4 荷重
    rows = []
    for Fi in LOADS:
        hzi, ghi, rgbi, reci = _scene(Fi, Es, lights)
        fit = T.contact_radius_fit(reci["normals"], ghi["X"], ghi["Y"], R_BALL, ghi["pitch"])
        ring = T.contact_radius_ring(reci["height"], ghi["pitch"])
        dB = T.membrane_delta_from_normals(reci["normals"], ghi["X"], ghi["Y"], ghi["pitch"])
        rows.append({"F": Fi, "a": hzi["a"], "delta": hzi["delta"], "a_fit": fit["a"], "a_ring": ring["a"], "a_ring_circle": ring["a_circle"],
                     "delta_B": dB, "F_fit": T.hertz_force(R_BALL, Es, a=fit["a"]), "F_delta": T.hertz_force(R_BALL, Es, delta=dB),
                     "a_px": hzi["a"] / ghi["pitch"], "ring_rms_px": ring["rms_px"], "fit_rms": fit["rms"]})
    e_afit = [abs(_pct(r["a_fit"], r["a"])) for r in rows]
    e_Ffit = [abs(_pct(r["F_fit"], r["F"])) for r in rows]
    gate("当てはめ経路(法線の半径スロープ分布に Hertz のスロープ模型を 1 パラメータ a で当てる): 4 荷重 0.02〜0.12 N で a ≤ 1 %、F ≤ 2 %",
         max(e_afit) < 1.0 and max(e_Ffit) < 2.0,
         "a 誤差 %s %%, F 誤差 %s %%" % ([round(v, 2) for v in e_afit], [round(v, 2) for v in e_Ffit]))
    e_d = [abs(_pct(r["delta_B"], r["delta"])) for r in rows]
    e_Fd = [abs(_pct(r["F_delta"], r["F"])) for r in rows]
    gate("δ 経路(半径スロープの 1D 積分 + Boussinesq 遠方場の裾 r_max·s̄(r_max)): δ ≤ 2 %、F = (4/3)E*√R δ^{3/2} ≤ 3 %",
         max(e_d) < 2.0 and max(e_Fd) < 3.0, "δ 誤差 %s %%, F 誤差 %s %%" % ([round(v, 2) for v in e_d], [round(v, 2) for v in e_Fd]))
    ring_bias = [_pct(r["a_ring"], r["a"]) for r in rows]
    ring_pred = [100 * (-0.7) / r["a_px"] for r in rows]
    circ_vs_med = [abs(_pct(r["a_ring_circle"], r["a_ring"])) for r in rows]
    gate("模型なしのリング(方位角 72 本の副画素ピーク → measure.fit_circle): 常に内側で、バイアスが分解能の予測 −0.7 px/a と 1.5 pt 以内 "
         "(a = 9〜16 px で −8〜−5 %。双線形補間がカスプを ~1 px 平滑する限界、正直に)、円当てはめの半径は中央値と 1 % 以内",
         all(b < 0 for b in ring_bias) and max(abs(b - p) for b, p in zip(ring_bias, ring_pred)) < 1.5 and max(circ_vs_med) < 1.0,
         "実測 %s %%, 予測 %s %%" % ([round(v, 1) for v in ring_bias], [round(v, 1) for v in ring_pred]))
    Fs = np.array([r["F"] for r in rows])
    ex_fit = float(np.polyfit(np.log(Fs), np.log([r["a_fit"] for r in rows]), 1)[0])
    ex_ring = float(np.polyfit(np.log(Fs), np.log([r["a_ring"] for r in rows]), 1)[0])
    gate("Hertz のスケーリング a ∝ F^{1/3}: 当てはめ経路の log-log 傾きが 0.333 ± 0.01、リングでも 0.30〜0.40(prefactor のバイアスは指数を変えない)",
         abs(ex_fit - 1 / 3) < 0.01 and 0.30 < ex_ring < 0.40, "指数 fit %.4f, ring %.3f" % (ex_fit, ex_ring))
    d_none = T.membrane_delta_from_normals(gh["normals"], gh["X"], gh["Y"], pitch, tail="none")
    d_tail = T.membrane_delta_from_normals(gh["normals"], gh["X"], gh["Y"], pitch)
    r_max = float(min(np.abs(gh["X"]).max(), np.abs(gh["Y"]).max()))
    tail_cf = T.hertz_surface_uz(np.array([r_max]), a, d, R_BALL)[0] / d
    gate("窓打ち切り(真値の法線で): 裾なしの δ の不足が閉形式 ū_z(r_max)/δ = %.1f %% と 1 pt 以内、Boussinesq の裾を足すと δ が 1 %% 以内"
         % (100 * tail_cf), abs(-_pct(d_none, d) / 100 - tail_cf) < 0.01 and abs(_pct(d_tail, d)) < 1.0,
         "裾なし %.2f %%, 裾あり %+.2f %%(r_max = %.1f mm = %.1f a)" % (_pct(d_none, d), _pct(d_tail, d), r_max * 1e3, r_max / a))
    rec0 = T.membrane_recover(rgb, lights, pitch)                           # ambient を引かない
    d0 = T.membrane_delta_from_normals(rec0["normals"], gh["X"], gh["Y"], pitch)
    pred_amb = 100 * AMB / math.sin(math.radians(ELEV))
    gate("破れ 1(ambient): 像の ambient 項 %.2f を引かずに解くと δ が ambient/sin(仰角) ≈ %.1f %% 低い(予測と 1 pt 以内)、引けば 1 %% 以内"
         % (AMB, pred_amb), abs(-_pct(d0, d) - pred_amb) < 1.0 and abs(_pct(d_tail, d)) < 1.0, "引かない %.2f %%, 引く %+.2f %%" % (_pct(d0, d), _pct(T.membrane_delta_from_normals(rec["normals"], gh["X"], gh["Y"], pitch), d)))
    img0 = np.maximum(rgb - AMB, 0)
    n_mis, _ = PH.photometric_stereo(np.moveaxis(img0, -1, 0), T.membrane_lights(ELEV - 15.0), lit_only=True)
    ang_mis = PH.angular_error_deg(n_mis, gh["normals"])
    flat = (gh["normals"][..., 2] > 0.9999) & lit
    gate("破れ 2(照明の較正): 仰角を 15° 誤ると斜面(nz < 0.98)の中央角誤差 > 2°、平坦域は方位対称で < 0.1°(ずれは斜面にだけ出る)",
         float(np.median(ang_mis[slope_px])) > 2.0 and float(np.median(ang_mis[flat])) < 0.1,
         "斜面 %.2f° → %.2f°, 平坦 %.3f°" % (np.median(ang[slope_px]), np.median(ang_mis[slope_px]), np.median(ang_mis[flat])))
    noise_rows = []
    for sig in (0.0, 0.01, 0.03):
        _, ghn, _, recn = _scene(F, Es, lights, noise=sig, seed=1)
        an = PH.angular_error_deg(recn["normals"], ghn["normals"])
        fitn = T.contact_radius_fit(recn["normals"], ghn["X"], ghn["Y"], R_BALL, ghn["pitch"])
        noise_rows.append((sig, float(np.median(an[slope_px])), _pct(T.hertz_force(R_BALL, Es, a=fitn["a"]), F), an))
    gate("破れ 3(雑音): 画素雑音 σ = 0 / 0.01 / 0.03 で斜面の法線誤差が単調に増え、σ = 0.03 でも当てはめ経路の F は 5 % 以内(分布に当てるので雑音に強い)",
         noise_rows[0][1] < noise_rows[1][1] < noise_rows[2][1] and abs(noise_rows[2][2]) < 5.0,
         "法線 %s°, F 誤差 %s %%" % ([round(r[1], 2) for r in noise_rows], [round(r[2], 2) for r in noise_rows]))
    shapes = {}
    ok_sh = True
    for sh in T.SHAPES:
        g = T.membrane_indent_shape(sh, 0.3e-3, n=128, fov=6.0e-3, R=R_BALL)
        rgb_s = T.membrane_render_rgb(g["normals"], lights, ambient=AMB)
        rec_s = T.membrane_recover(rgb_s, lights, g["pitch"], ambient=AMB)
        c = g["contact"]
        zr = rec_s["height"] - rec_s["height"][~c].mean()
        ht = g["h"] - g["h"][~c].mean()
        rms = float(np.sqrt(np.mean((zr[c] - ht[c]) ** 2)))
        shapes[sh] = {"g": g, "rgb": rgb_s, "rec": rec_s, "rms": rms}
        ok_sh &= rms < 0.10 * 0.3e-3
    cyl = shapes["cylinder"]["g"]
    half_w = 0.5 * float(cyl["contact"].sum(axis=1).max()) * cyl["pitch"]
    half_cf = math.sqrt(2 * R_BALL * 0.3e-3 - 0.3e-3 ** 2)
    gate("4 形状(球・円柱・直線エッジ・スタンプ、幾何学的な押し込み 0.3 mm)の往復: 復元高さの RMS が接触域で深さの 10 %% 未満、"
         "円柱の幾何接触半幅 √(2Rd − d²) = %.3f mm と 1 px 以内" % (half_cf * 1e3),
         ok_sh and abs(half_w - half_cf) < cyl["pitch"],
         "RMS %s µm, 半幅 %.3f mm" % ({k: round(v["rms"] * 1e6, 2) for k, v in shapes.items()}, half_w * 1e3))
    if TAC is not None:
        gray = rgb.mean(-1)
        gray = (gray - gray.min()) / (np.ptp(gray) + 1e-12)
        m = TAC.tac_contact_mask(gray, 0.3, 0.3) > 0.5
        rec_ = (m & gh["contact"]).sum() / max(1, gh["contact"].sum())
        ratio = m.sum() / max(1, gh["contact"].sum())
        gate("別被験者 tac_contact_mask(単画像の擬似参照)は接触円をほぼ覆う(recall > 0.7)が弾性の裾まで拾って過剰分割(面積比 > 1.5)—— "
             "閉形式 + 法線の物理ベースが要る理由", rec_ > 0.7 and ratio > 1.5, "recall %.2f, 面積比 %.2f" % (rec_, ratio))
    fit_true = T.contact_radius_fit(gh["normals"], gh["X"], gh["Y"], R_BALL, pitch, centre_xy=(0.0, 0.0))
    pts = np.column_stack([60 + 20 * np.sin(np.linspace(0, 2 * np.pi, 72, endpoint=False)), 70 + 20 * np.cos(np.linspace(0, 2 * np.pi, 72, endpoint=False))])
    fc = FM.fit_circle(pts)
    gate("第 2 実装の照合: 真の法線に当てた a は 0.3 % 以内(模型とデータが同じ Hertz)、リングが使う measure.fit_circle は厳密な円で 1e-9",
         abs(_pct(fit_true["a"], a)) < 0.3 and abs(fc["r"] - 20) < 1e-9 and abs(fc["cy"] - 60) < 1e-9,
         "a_fit(true) %+.3f %%, %.1f s" % (_pct(fit_true["a"], a), time.time() - t0))
    return {"Es": Es, "hz": hz, "gh": gh, "rgb": rgb, "rec": rec, "lights": lights, "rows": rows, "ang": ang, "ang_mis": ang_mis,
            "noise_rows": noise_rows, "shapes": shapes, "slope_px": slope_px, "lit": lit}


def _raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def _crop_up(img, cy, cx, half, up):
    """(H, W[, 3]) を (cy, cx) まわり ±half で切り出し、最近傍で up 倍(等倍の画素が見えるように)。"""
    y0, x0 = int(round(cy)) - half, int(round(cx)) - half
    c = img[y0:y0 + 2 * half, x0:x0 + 2 * half]
    return np.kron(c, np.ones((up, up) + (1,) * (c.ndim - 2)))


def figures(ctx):
    print("== 図")
    hz, gh, rgb, rec, Es = ctx["hz"], ctx["gh"], ctx["rgb"], ctx["rec"], ctx["Es"]
    a, d = hz["a"], hz["delta"]
    pitch = gh["pitch"]
    n = N_PX
    cy = cx = (n - 1) / 2.0
    half = int(round(2.2 * a / pitch))
    up = max(1, 300 // (2 * half))
    crop = np.clip(_crop_up(rgb, cy, cx, half, up), 0, 1)
    figs.save("tacsim_membrane_rgb_crop", crop,
              caption="球(R = 3 mm)を 0.08 N で押した弾性膜の合成像、圧痕まわり ±%.1f mm を等倍の画素で %d 倍に拡大(センサ分解能 %.1f µm/px、"
                      "接触半径 a = %.2f mm = %.1f px)。方位 90/210/330°・仰角 55° の 3 色照明で、各色チャネルが 1 光源の Lambertian 像。"
                      % (half * pitch * 1e3, up, pitch * 1e6, a * 1e3, a / pitch))
    panels, caps = [], []
    for sh in T.SHAPES:
        s = ctx["shapes"][sh]
        panels.append(np.clip(_crop_up(s["rgb"], 63.5, 63.5, 40, 3), 0, 1))
        caps.append("%s: synthetic" % sh)
    for sh in T.SHAPES:
        s = ctx["shapes"][sh]
        panels.append(_crop_up(s["rec"]["height"] * 1e6, 63.5, 63.5, 40, 3))
        caps.append("%s: recovered [µm], RMS %.1f µm" % (sh, s["rms"] * 1e6))
    figs.save_grid("tacsim_four_shapes", panels, ncols=4, captions=caps,
                   caption="球・円柱・直線エッジ・F 字スタンプを 0.3 mm 押し込んだ膜(幾何学的な追従、弾性の裾なし、46.9 µm/px、中央 ±1.9 mm を 3 倍)。"
                           "上 = 3 色照明の合成像、下 = フォトメトリックステレオ + Frankot-Chellappa で復元した高さ(接触域の RMS を併記)。")
    Fmax = LOADS[-1]
    a_max = T.hertz_sphere(Fmax, R_BALL, Es)["a"]
    half_g = int(round(2.0 * a_max / pitch))
    up_g = max(1, 300 // (2 * half_g))
    Ff = np.linspace(0.004, Fmax * 1.05, 60)
    curve = (3 * Ff * R_BALL / (4 * Es)) ** (1 / 3) * 1e3
    frames = []
    seen_F, seen_a = [], []
    for Fi in np.linspace(0.005, Fmax, 12):
        hzi, ghi, rgbi, reci = _scene(float(Fi), Es, ctx["lights"])
        fit = T.contact_radius_fit(reci["normals"], ghi["X"], ghi["Y"], R_BALL, ghi["pitch"])
        seen_F.append(float(Fi))
        seen_a.append(fit["a"] * 1e3)
        left = np.clip(_crop_up(rgbi, cy, cx, half_g, up_g), 0, 1)
        series = [("Hertz a = (3FR/4E*)^{1/3}", Ff, curve), ("recovered (slope fit)", np.array(seen_F), np.array(seen_a))]
        right = figs.render_plot(series, xlabel="load F [N]", ylabel="contact radius a [mm]", title="F = %.3f N" % Fi,
                                 size=(420, left.shape[0]), xlim=(0, Fmax * 1.05), ylim=(0, curve[-1] * 1.1),
                                 kinds=["line", "scatter"], styles=["dashed", None], colors=["reference", "emphasis"])
        frames.append(np.hstack([left, np.asarray(right, np.float64)]))
    figs.save_gif("tacsim_force_sweep", frames, fps=3.0,
                  caption="荷重を 0.005 → 0.12 N に上げる(12 コマ)。左 = 圧痕まわり ±%.1f mm の合成像(%.1f µm/px を %d 倍)、"
                          "右 = Hertz の a–F 曲線(破線 = 閉形式)に、各コマの像から当てはめ経路で読んだ a が点として増えていく。"
                          % (half_g * pitch * 1e3, pitch * 1e6, up_g))
    mid = n // 2
    x_mm = (np.arange(n) - (n - 1) / 2.0) * pitch * 1e3
    zr = rec["height"][mid]
    zr = (zr - zr.mean() + gh["h"][mid].mean()) * 1e6
    figs.save_plot("tacsim_height_cross_section", [("truth (Hertz ū_z)", x_mm, gh["h"][mid] * 1e6), ("recovered (photometric → integrate)", x_mm, zr)],
                   xlabel="x [mm]", ylabel="membrane height [µm]", title="Recovered vs Hertz dimple (R = 3 mm, F = 0.08 N)",
                   kinds=["line", "scatter"], styles=["dashed", None], colors=["reference", "emphasis"], size=(640, 400),
                   caption="中央行の断面。破線 = Hertz の閉形式(内側 δ − r²/(2R)、外側 Johnson 3.42a、δ = %.0f µm)、点 = 合成像から復元した高さ"
                           "(Frankot-Chellappa、平均を真値に合わせた)。遠方場の裾が窓の端(±8 mm)でも 0 に戻らないのが見える。" % (d * 1e6))
    fit = T.contact_radius_fit(rec["normals"], gh["X"], gh["Y"], R_BALL, pitch)
    sel = fit["r"] < 4 * a
    figs.save_plot("tacsim_slope_profile_fit",
                   [("Hertz slope model, a_fit = %.3f mm" % (fit["a"] * 1e3), fit["r"][sel] * 1e3, fit["model"][sel]),
                    ("measured radial slope (from normals)", fit["r"][sel] * 1e3, fit["slope"][sel]),
                    ("", [a * 1e3, a * 1e3], [0, float(fit["model"].max()) * 1.05])],
                   xlabel="r [mm]", ylabel="dh/dr", title="Radial slope profile vs Hertz model",
                   kinds=["line", "scatter", "line"], styles=["dashed", None, "dotted"], colors=["reference", "emphasis", "neutral"], size=(640, 400),
                   caption="法線場から取った半径方向スロープの方位平均(点)と、1 パラメータ a で当てた Hertz のスロープ模型(破線: 内側 r/R、"
                           "外側 (2/πR)[r arcsin(a/r) − a√(1−a²/r²)])。点線 = 真の a。カスプの位置が接触縁で、高さの積分を通らずに a が決まる。")
    rows = ctx["rows"]
    figs.save_plot("tacsim_hertz_a_vs_F",
                   [("Hertz a = (3FR/4E*)^{1/3}", Ff, curve), ("slope fit (primary)", [r["F"] for r in rows], [r["a_fit"] * 1e3 for r in rows]),
                    ("model-free ring (−0.7 px/a)", [r["F"] for r in rows], [r["a_ring"] * 1e3 for r in rows])],
                   xlabel="load F [N]", ylabel="contact radius a [mm]", title="Contact radius vs load: two readouts",
                   kinds=["line", "scatter", "scatter"], styles=["dashed", None, None], colors=["reference", "emphasis", "wrong"], size=(640, 400),
                   caption="破線 = Hertz の閉形式。当てはめ経路(主)は曲線に乗る(≤ 1 %)。模型なしのリングは常に内側で、ずれは分解能の予測 −0.7 px/a "
                           "どおり(a = 9 px で −8 %、16 px で −5 %)—— 模型を使わない代償を数で見せる。")
    emax = float(np.percentile(np.concatenate([ctx["ang_mis"].ravel(), ctx["noise_rows"][2][3].ravel()]), 99))
    figs.save_grid("tacsim_failure_modes", [ctx["ang"], ctx["ang_mis"], ctx["noise_rows"][2][3]], ncols=3, vrange=(0.0, emax),
                   captions=["correct lights (slope median %.2f°)" % np.median(ctx["ang"][ctx["slope_px"]]),
                             "elevation mis-calibrated 15° (%.2f°)" % np.median(ctx["ang_mis"][ctx["slope_px"]]),
                             "pixel noise σ = 0.03 (%.2f°)" % ctx["noise_rows"][2][1]],
                   caption="壊れる場所: 法線の角誤差 [deg]。左 = 正しい照明(ほぼ 0、接触縁の薄い輪は付着影)。中 = 仰角を 15° 誤って較正すると斜面全体が"
                           "系統的に悪化し、平坦域は方位対称で無傷。右 = 画素雑音 σ = 0.03 は一様に荒れるが、分布に当てる経路の F は 5 % 以内に残る。")
    print("  figures:", figs.errors() or "ok")


def main() -> int:
    t_all = time.time()
    ctx = numpy_part()
    if figs.enabled():
        figures(ctx)
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
