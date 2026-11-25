"""Rendered particle-microscopy evidence gates / 粒子顕微鏡 PoC の描画証拠を検査する。"""
from __future__ import annotations

import numpy as np

import fullseye as fs
from examples import poc_compendial_particle_microscopy as poc


def _role_rgb(role):
    """Read one exact role colour through the public renderer / 描画器から役色を得る。"""
    probe = np.ones((9, 9, 3), dtype=float)
    rendered = np.asarray(fs.draw_line(probe, (4, 1), (4, 7), color=role, width=1))
    return rendered[4, 4]


def test_all_three_cdf_bases_draw_six_dx_lines_at_their_data_coordinate_columns():
    truth = np.linspace(0.0045, 0.0085, 60)
    estimated = truth + 0.00015
    checked = 0
    for basis, exponent in (("number", 0), ("area", 2), ("volume", 3)):
        truth_weight = np.power(truth, exponent)
        estimated_weight = np.power(estimated, exponent)
        report = {"quantiles": {basis: {
            "D%d" % q: {"value": poc._midpoint_truth(estimated, estimated_weight, q)}
            for q in (10, 50, 90)}}}
        panel = poc._cdf_panel(basis, truth, estimated, truth_weight, report)
        markers = poc._cdf_marker_specs(basis, truth, truth_weight, report)
        xlim = (float(truth.min()), float(estimated.max()))
        marker_font = poc.CDF_TEXT_SIZE * poc.CDF_SCALE
        marker_row_height = max(fs.measure_text(marker["label"], font_size=marker_font)["height"]
                                for marker in markers) + 8 * poc.CDF_SCALE
        marker_band_height = 2 * marker_row_height + 4 * poc.CDF_SCALE
        expected_line_height = ((poc.CDF_LOGICAL_SIZE[1] - 108) * poc.CDF_SCALE
                                - marker_band_height)
        axis_left = 72 * poc.CDF_SCALE
        axis_width = (poc.CDF_LOGICAL_SIZE[0] - 96) * poc.CDF_SCALE
        for marker in markers:
            # 文書化した axes_transform の式を独立に使い、render_plot の座標は流用しない。
            # Independently use the documented transform, not renderer-returned coordinates.
            expected = axis_left + int(round((marker["x"] - xlim[0]) / (xlim[1] - xlim[0])
                                             * (axis_width - 1)))
            rgb = _role_rgb(marker["color"])
            longest = 0
            for col in range(expected - 3, expected + 4):
                exact_role_pixels = np.all(np.isclose(panel[:, col], rgb, rtol=0.0, atol=1e-12), axis=1)
                longest = max(longest, int(exact_role_pixels.sum()))
            assert longest >= expected_line_height - 2, (basis, marker["label"], expected, longest)
            checked += 1
    assert checked == 3 * 6


def test_cdf_declared_minimum_text_height_exceeds_1080p_gate():
    rendered_font_px = poc.CDF_TEXT_SIZE * poc.CDF_SCALE
    rendered_height = poc.CDF_LOGICAL_SIZE[1] * poc.CDF_SCALE
    assert rendered_font_px * 1080 / rendered_height >= poc.MIN_TEXT_HEIGHT_1080_PX
