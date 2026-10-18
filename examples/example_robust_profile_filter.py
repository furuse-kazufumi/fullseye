# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""傷つき断面のうねりを引く —— 線形ガウスは傷に引かれ、ロバスト版は引かれない(呼び出し例)。

    py -3.11 examples/example_robust_profile_filter.py

【この例が解く問題】
断面から平均線(うねり)を引いて粗さを残すとき、深い傷が 1 本あると線形のガウスフィルタは
平均線を傷の側へ凹ませる。``robust_gaussian_profile`` / ``robust_spline_profile``
(``roughness`` 族の新 op)は傷の重みを下げて反復するので、平均線は傷を無視する。

【グラウンドトゥルース】
真のうねりは解析的な正弦(振幅 2 µm、波長 600 µm)。これに雑音(σ 0.3 µm)と傷を足す。
平均線の真値からの最大ずれが「引きずり量」。

【呼び出し】
    rough, mean_line, info = fs.ledger.robust_gaussian_profile.raw(z, dx, lambda_c)
台帳経由(``fs.ledger.robust_gaussian_profile(z, dx, lambda_c)``)は粗さだけを返す。
``info`` は反復回数・収束・重みの要約。収束しなければ値を返さず ``ValueError``(fail-closed)。

EXTEND: ``z`` をスタイラス計の断面に差し替え、``dx`` と ``lambda_c`` を測定条件に合わせる。
面(2 次元の高さ場)は ``robust_gaussian_surface``。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fullseye as fs  # noqa: E402

DX, LAMBDA_C, N = 1.0, 80.0, 2400


def main() -> bool:
    x = np.arange(N) * DX
    true_mean = 2.0 * np.sin(2 * np.pi * x / 600.0)
    rng = np.random.default_rng(0)
    z = true_mean + 0.3 * rng.standard_normal(N)
    for s in (500, 900, 1300, 1700):
        z[s:s + 8] -= 6.0                                   # 深さ 6 µm・幅 8 µm の傷 4 本
    inner = slice(150, N - 150)

    r_lin, m_lin, _ = fs.ledger.robust_gaussian_profile.raw(z, DX, LAMBDA_C, robust=False)
    r_rob, m_rob, info = fs.ledger.robust_gaussian_profile.raw(z, DX, LAMBDA_C)
    _, m_spl, info_s = fs.ledger.robust_spline_profile.raw(z, DX, LAMBDA_C)

    def drag(m):
        return float(np.max(np.abs(m - true_mean)[inner]))

    print("引きずり量(平均線の真値からの最大ずれ µm)")
    print("  線形ガウス       %.3f" % drag(m_lin))
    print("  ロバストガウス   %.3f  (反復 %d 回)" % (drag(m_rob), info["iterations"]))
    print("  ロバストスプライン %.3f  (反復 %d 回)" % (drag(m_spl), info_s["iterations"]))
    assert drag(m_rob) < 0.25 * drag(m_lin) and drag(m_spl) < 0.25 * drag(m_lin)
    # 台帳経由は粗さだけを返す
    assert np.allclose(fs.ledger.robust_gaussian_profile(z, DX, LAMBDA_C), r_rob)
    try:
        fs.ledger.robust_gaussian_profile(z, DX, LAMBDA_C, max_iter=1)
        raise AssertionError("収束していないのに値が返った")
    except ValueError as exc:
        print("max_iter=1 は拒否される: %s" % str(exc)[:60])
    print("PASS")
    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
