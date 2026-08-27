# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""spline_curve — 疎な点列を滑らかに補間(開曲線/閉曲線・2D/3D・時間軸の変形)。

    py -3.11 examples/spline_curve.py

【用途(分かりやすく)】
デジタイズした輪郭や軌跡は点が疎で不揃い。スプラインで滑らかに補間・再サンプルして
密で扱いやすい曲線に直す。輪郭は **閉曲線**(ループが滑らかに閉じる)、プロファイルや
軌跡は **開曲線**。同じ API で **3D 空間曲線**、さらに座標を時間で補間すれば **時間軸の
変形(キーフレーム間の滑らかな遷移)** も表せる。

【グラウンドトゥルース(beat-the-null)】
1. 閉曲線: 円周上の疎点を閉スプラインで再サンプルすると円周に乗り、シームが滑らかに
   閉じる。同じ点を開スプラインにすると閉じず隙間が残る(閉と開の使い分けが効く)。
2. 3D: ヘリックス上の疎点を再サンプルするとヘリックス上に乗る(半径一定)。
3. 時間変形: 既知の滑らかな軌跡をキーフレーム時刻で標本化し、各座標を時間でスプライン
   補間すると、キーフレームを厳密に通り、間も真の軌跡に近い。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import signal1d as S  # noqa: E402


def main():
    # 1) 閉曲線 vs 開曲線(2D 輪郭)
    th = np.linspace(0, 2 * np.pi, 13, endpoint=False)
    circle = np.column_stack([50 + 30 * np.cos(th), 50 + 30 * np.sin(th)])
    closed = S.spline_curve_resample(circle, 200, closed=True)
    opened = S.spline_curve_resample(circle, 200, closed=False)
    r = np.hypot(closed[:, 0] - 50, closed[:, 1] - 50)
    seam_closed = float(np.hypot(*(closed[0] - closed[-1])))
    seam_open = float(np.hypot(*(opened[0] - opened[-1])))
    print(f"閉曲線: 半径 {r.mean():.2f}±{r.std():.3f}、シーム隙間 {seam_closed:.2f} / "
          f"開曲線のシーム隙間 {seam_open:.2f}")
    assert r.std() < 0.5 and abs(r.mean() - 30) < 0.5
    assert seam_closed < 3.0 < seam_open           # 閉は滑らかに閉じ、開は閉じない

    # 2) 3D 空間曲線(ヘリックス)
    t = np.linspace(0, 4 * np.pi, 30)
    helix = np.column_stack([np.cos(t), np.sin(t), t / 6.0])
    rs = S.spline_curve_resample(helix, 300, closed=False)
    print(f"3D ヘリックス: 再サンプル {rs.shape}、半径ばらつき {np.hypot(rs[:, 0], rs[:, 1]).std():.3f}")
    assert rs.shape == (300, 3) and np.hypot(rs[:, 0], rs[:, 1]).std() < 0.05

    # 3) 時間軸の変形: 各座標を時間でスプライン補間(キーフレーム間を滑らかに)
    key_t = np.linspace(0.0, 1.0, 8)                       # 8 キーフレーム時刻
    traj = np.column_stack([np.sin(2 * np.pi * key_t), np.cos(2 * np.pi * key_t)])  # 既知の滑らかな軌跡
    sx = S.spline_fit(key_t, traj[:, 0], smooth=0.0)
    sy = S.spline_fit(key_t, traj[:, 1], smooth=0.0)
    # キーフレームを厳密に通る
    at_keys = np.column_stack([S.spline_eval(sx, key_t), S.spline_eval(sy, key_t)])
    key_err = float(np.abs(at_keys - traj).max())
    # 間も真の軌跡に近い
    ft = np.linspace(0, 1, 200)
    dense = np.column_stack([S.spline_eval(sx, ft), S.spline_eval(sy, ft)])
    true_dense = np.column_stack([np.sin(2 * np.pi * ft), np.cos(2 * np.pi * ft)])
    mid_err = float(np.abs(dense - true_dense).max())
    print(f"時間変形: キーフレーム誤差 {key_err:.2e}(厳密通過)、中間の軌跡誤差 {mid_err:.3f}")
    assert key_err < 1e-9 and mid_err < 0.05

    print("\nPASS: 疎な点列を開/閉・2D/3D で滑らかに補間でき(閉は閉じ開は閉じない)、"
          "座標を時間でスプライン補間すればキーフレームを厳密に通る時間変形を表せる。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
