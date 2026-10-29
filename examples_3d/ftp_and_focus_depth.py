# Copyright (c) 2026 Kazufumi Furuse. Licensed under Apache-2.0.
"""Single-shot fringe FTP and focus-stack depth, both checked against synthetic truth."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy.ndimage import gaussian_filter

from fringe import fringe_ftp_phase, synthesize_fringes
from reconstruction import depth_from_focus
import examplefig


def main():
    rows, cols = 96, 128
    yy, xx = np.mgrid[:rows, :cols]

    height = .25 * np.sin(2 * np.pi * xx / cols) + .18 * np.cos(2 * np.pi * yy / rows)
    frame = synthesize_fringes(height, n_steps=3, freq=12, phase_gain=2.0)[0]
    recovered, ftp = fringe_ftp_phase(frame, carrier_axis="x", k=.5, return_info=True)
    ftp_rmse = float(np.sqrt(np.mean(((recovered - recovered.mean()) - height) ** 2)))

    texture = gaussian_filter(np.random.default_rng(9).normal(size=(rows, cols)), .6)
    true_index = np.where(xx < cols // 3, 0, np.where(xx < 2 * cols // 3, 1, 2))
    stack = []
    for focus in range(3):
        image = np.zeros_like(texture)
        for depth in range(3):
            layer = gaussian_filter(texture, .25 + 1.8 * abs(depth - focus))
            image[true_index == depth] = layer[true_index == depth]
        stack.append(image)
    result = depth_from_focus(stack, focus_positions=[10., 20., 30.])
    valid = np.ones_like(true_index, dtype=bool)
    valid[:, cols // 3 - 5:cols // 3 + 5] = False
    valid[:, 2 * cols // 3 - 5:2 * cols // 3 + 5] = False
    focus_accuracy = float(np.mean(result["index"][valid] == true_index[valid]))

    print(f"FTP carrier period: {ftp['carrier_period']:.6f} px (truth {cols / 12:.6f})")
    print(f"FTP height RMSE: {ftp_rmse:.6f}")
    print(f"focus-stack index accuracy: {focus_accuracy:.3%}")
    examplefig.save("single_fringe", frame, "FTP に入力する搬送波縞 1 枚")
    examplefig.save("ftp_height", recovered, "搬送波ランプを除いた FTP 復元高さ")
    examplefig.save("focus_depth", result["depth"], "焦点スタックから復元した深さ")
    assert ftp_rmse < .012
    assert focus_accuracy > .96
    assert np.all(depth_from_focus([np.ones((8, 8))] * 3)["sharpness"] == 0)


if __name__ == "__main__":
    main()
