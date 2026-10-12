# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 複素スペクトルと 1-D 信号の橋渡し op(tb_cx_* 7 本・tb_negate_funct_1d・tb_zero_crossing_rate)を往復と閉形式で確かめる

平たく言うと:
  ``tb_`` で始まる op は、型つきカタログの関数(``complexops.cx_ifft`` など)を進化の語彙
  ``op(v, a, b)`` から呼べるようにした**橋渡し**。中身は同じ実装なので、ここでは利用者の入口
  ``fullseye.apply(v, "tb_…")`` で呼んだ値を、numpy で独立に作った答えと照合する:
  画像 → ``cx_fft`` → ``tb_cx_ifft`` で元の画像に戻る(往復)、パーセバルの等式、1 画素ずらした点の
  位相が線形に回る、ガウスの低域通過の伝達関数を numpy で作って掛けたものと一致、など。
  1-D の 2 本は、元の関数(``funct1d.negate_funct_1d`` / ``dsp.zero_crossing_rate``)とも並べて呼ぶ。
  各行に「何を期待し、何が出て、合ったか」を印字し、外れたら exit 1。

確かめ方(op ごとの真値):
  * tb_cx_ifft            —— cx_fft の逆: 実部が元の画像に 1e-12 で戻る
  * tb_cx_real / tb_cx_imag —— np.real / np.imag と一致し、real + i·imag で元の複素場が組み直せる
  * tb_cx_magnitude       —— 直流の大きさ = 画素の総和、パーセバル Σ|F|² = H·W·Σ f²
  * tb_cx_phase           —— 表示用 (angle + π)/2π: 位相 0 の直流が 0.5、1 画素ずらした点の位相が −2π k/W で回る
  * tb_cx_log_magnitude   —— log(1 + |F|) を最大値で割ったもの、最大(= 1)は直流
  * tb_cx_apply_transfer_function —— a = 0.5 で σ = 0.26 周期/画素のガウス H を掛けた複素スペクトル。直流は H(0) = 1 で不変
  * tb_negate_funct_1d    —— −y と一致、2 回で元に戻る(元の関数 negate_funct_1d とも一致)
  * tb_zero_crossing_rate —— 符号の反転の数 / (n − 1)。docstring の例 [1, 0, 1, 0, 1] → 0、[1, 0, −1] → 0.5、周期 8 の矩形波

    py -3.11 examples/gallery_spectrum_signal_bridge.py
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import complexops  # noqa: E402
import dsp  # noqa: E402
import fullseye  # noqa: E402
import funct1d  # noqa: E402

ROWS: list = []
H_, W_ = 24, 32
RNG = np.random.default_rng(7)
IMG = RNG.random((H_, W_))


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def run(v, name, a=0.5, b=0.5):
    """利用者の入口(``fullseye.apply``)。失敗は握り潰さない。"""
    return fullseye.apply(v, name, a, b, on_error="raise")


def _err(x, y) -> float:
    return float(np.max(np.abs(np.asarray(x) - np.asarray(y))))


def demo_spectrum() -> None:
    F = complexops.cx_fft(IMG)                                     # 中心化した複素スペクトル(直流 = 配列の中央)
    c = (H_ // 2, W_ // 2)

    back = np.asarray(run(F, "tb_cx_ifft"))
    check("tb_cx_ifft", "画像 → cx_fft → tb_cx_ifft", "元の画像(実部)", f"最大差 {_err(back, IMG):.1e}、{back.dtype}",
          _err(back, IMG) < 1e-12 and back.dtype == np.float64)

    re = np.asarray(run(F, "tb_cx_real"))
    im = np.asarray(run(F, "tb_cx_imag"))
    check("tb_cx_real", "複素場の実部", "np.real(F)", f"最大差 {_err(re, F.real):.1e}", _err(re, F.real) == 0.0)
    check("tb_cx_imag", "複素場の虚部 / real + i·imag", "np.imag(F) / F に戻る", f"{_err(im, F.imag):.1e} / {_err(re + 1j * im, F):.1e}",
          _err(im, F.imag) == 0.0 and _err(re + 1j * im, F) == 0.0)

    mag = np.asarray(run(F, "tb_cx_magnitude"))
    parse = float((mag ** 2).sum()) / (H_ * W_ * float((IMG ** 2).sum()))
    check("tb_cx_magnitude", "直流の大きさ", f"画素の総和 {IMG.sum():.6f}", f"{mag[c]:.6f}", abs(mag[c] - IMG.sum()) < 1e-9)
    check("tb_cx_magnitude", "パーセバル Σ|F|² / (H·W·Σf²)", "1", f"{parse:.15f}", abs(parse - 1.0) < 1e-12)

    ph = np.asarray(run(F, "tb_cx_phase"))
    check("tb_cx_phase", "表示用の位相 (angle + π)/2π", "numpy で同じ式 / 直流(位相 0)は 0.5",
          f"最大差 {_err(ph, (np.angle(F) + np.pi) / (2 * np.pi)):.1e} / {ph[c]:.6f}",
          _err(ph, (np.angle(F) + np.pi) / (2 * np.pi)) < 1e-15 and abs(ph[c] - 0.5) < 1e-15)
    delta = np.zeros((H_, W_))
    delta[0, 1] = 1.0                                              # 原点から右へ 1 画素ずらした点
    phd = np.asarray(run(complexops.cx_fft(delta), "tb_cx_phase"))
    k = np.arange(W_) - W_ // 2
    rad = phd[c[0], :] * 2 * np.pi - np.pi                         # 表示用から生のラジアンへ戻す
    want = np.angle(np.exp(-2j * np.pi * k / W_))                  # シフト定理: e^{−2πi k/W}(折り返し後)
    wrap = np.angle(np.exp(1j * (rad - want)))
    check("tb_cx_phase", "1 画素ずらした点の位相(中央の行)", "−2π k/W(シフト定理)", f"最大差 {np.abs(wrap).max():.1e} rad",
          np.abs(wrap).max() < 1e-12)

    lm = np.asarray(run(F, "tb_cx_log_magnitude"))
    want = np.log1p(np.abs(F)) / np.log1p(np.abs(F)).max()
    check("tb_cx_log_magnitude", "log(1 + |F|) / 最大", "numpy で同じ式・最大 1 は直流",
          f"最大差 {_err(lm, want):.1e}、最大 {lm.max():.6f} の位置 {tuple(int(i) for i in np.unravel_index(lm.argmax(), lm.shape))}",
          _err(lm, want) < 1e-15 and lm[c] == 1.0)

    a = 0.5
    sigma = 0.02 + 0.48 * a                                        # docstring: σ = 0.02 + 0.48 a 周期/画素
    fy = np.fft.fftshift(np.fft.fftfreq(H_))
    fx = np.fft.fftshift(np.fft.fftfreq(W_))
    r2 = fy[:, None] ** 2 + fx[None, :] ** 2
    Hgauss = np.exp(-r2 / (2 * sigma ** 2))
    G = np.asarray(run(F, "tb_cx_apply_transfer_function", a))
    check("tb_cx_apply_transfer_function", f"a = {a}: σ = {sigma:.2f} 周期/画素のガウス低域", "F·H(numpy で作った H)",
          f"最大差 {_err(G, F * Hgauss):.1e}、{G.dtype}", _err(G, F * Hgauss) < 1e-9 and np.iscomplexobj(G))
    smooth = np.asarray(run(G, "tb_cx_ifft"))
    check("tb_cx_apply_transfer_function", "直流は H(0) = 1 で不変 → 逆変換の平均", f"元の平均 {IMG.mean():.12f}",
          f"{smooth.mean():.12f}、分散 {IMG.var():.4f} → {smooth.var():.4f}",
          abs(smooth.mean() - IMG.mean()) < 1e-12 and smooth.var() < IMG.var())


def demo_signal_1d() -> None:
    t = np.arange(50)
    y = np.sin(2 * np.pi * t / 17.0) + 0.3 * np.cos(2 * np.pi * t / 5.0)
    neg = np.asarray(run(y, "tb_negate_funct_1d"))
    twice = np.asarray(run(neg, "tb_negate_funct_1d"))
    base = funct1d.negate_funct_1d(y)
    check("tb_negate_funct_1d", "50 点の 1-D 関数", "−y / 2 回で y / 元の関数と同じ",
          f"{_err(neg, -y):.1e} / {_err(twice, y):.1e} / {_err(neg, base):.1e}",
          _err(neg, -y) == 0.0 and _err(twice, y) == 0.0 and _err(neg, base) == 0.0)
    check("tb_negate_funct_1d", "空の関数(0 点)", "空のまま返る(元の関数の約束)", f"{funct1d.negate_funct_1d(np.zeros(0)).shape}",
          funct1d.negate_funct_1d(np.zeros(0)).shape == (0,))

    cases = [([1.0, 0.0, 1.0, 0.0, 1.0], 0.0, "docstring の例(0 に触れるだけ)"),
             ([1.0, 0.0, -1.0], 0.5, "docstring の例(0 を挟んで反転)"),
             ([1.0, -1.0] * 10, 1.0, "毎回反転(20 点)")]
    sq = np.where((np.arange(64) // 4) % 2 == 0, 1.0, -1.0)         # 周期 8 の矩形波: 64 点で 15 回反転
    cases.append((sq, 15.0 / 63.0, "周期 8 の矩形波 64 点(15 回 / 63 組)"))
    for x, want, what in cases:
        got = float(run(np.asarray(x), "tb_zero_crossing_rate"))
        got_base = float(dsp.zero_crossing_rate(np.asarray(x)))
        check("tb_zero_crossing_rate", what, f"{want:.6f}(元の関数も同じ)", f"{got:.6f} / {got_base:.6f}",
              math.isclose(got, want, abs_tol=1e-15) and got == got_base)
    try:
        dsp.zero_crossing_rate(np.zeros(0))
        refused = False
    except ValueError:
        refused = True
    check("tb_zero_crossing_rate", "空の入力(元の関数)", "ValueError で拒む(docstring)", "拒んだ" if refused else "値を返した", refused)


def main() -> int:
    t0 = time.time()
    demo_spectrum()
    demo_signal_1d()
    w_op = max(len(r[0]) for r in ROWS)
    print(f"{'op':<{w_op}} | 確かめたこと | 期待 | 出た値 | 判定")
    for op, what, exp, got, ok in ROWS:
        print(f"{op:<{w_op}} | {what} | {exp} | {got} | {'合格' if ok else '★不合格'}")
    bad = [r for r in ROWS if not r[4]]
    if bad:
        print(f"FAIL: {len(bad)}/{len(ROWS)} 行が外れた({', '.join(sorted({r[0] for r in bad}))})")
        return 1
    print(f"PASS: {len({r[0] for r in ROWS})} op を {len(ROWS)} 行の真値で確認({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
