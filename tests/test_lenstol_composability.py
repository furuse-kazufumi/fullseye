"""Tolerance tables remain ordinary table-sort values across optical ops."""
import numpy as np

import lensrender as LR
import lenstol as LT
import raytrace as RT
import studio_search
from examples import lensfile_tolerance_worst_mtf as sample_file
from examples import optimized_lens_tolerance_sensitivity as sample_optimised


def test_both_tolerancing_composition_samples_run():
    a = sample_file.run()
    b = sample_optimised.run()
    assert isinstance(a["tolerance_table"], list)
    assert isinstance(a["monte_carlo"], dict)
    assert a["worst_through_focus_mtf"]["tangential"].size > 0
    assert isinstance(b["optimization"], dict)
    assert isinstance(b["sensitivity"]["drivers"], list) and b["sensitivity"]["drivers"]


def test_worst_trial_prescription_renders_as_a_valid_image():
    s = RT.example_system("singlet")
    table = LT.tolerance_table(s, defaults={"radius_pct": 0.01})
    criteria = LT.tolerance_criteria(rms_spot={}, rings=2)
    run = LT.tolerance_monte_carlo(s, table, criteria, trials=5, seed=4)
    worst = run["worst_trial"]
    assert worst["index"] in range(5) and worst["draws"]
    rendered = LR.render_scene_through_lens(
        worst["prescription"], sensor={"size": (4, 5), "pixel_pitch_um": 10.0},
        pupil_samples=2, wavelengths=[0.588], add_noise=False)
    assert rendered["image"].shape == (4, 5)
    assert np.all(np.isfinite(rendered["image"]))


def test_studio_search_lists_tolerancing_for_a_prescription_selection():
    prescription = RT.example_system("singlet")
    result = studio_search.search_grouped("lens tolerance", current_value=prescription, k=40,
                                          lang="en")
    names = {row["name"] for row in result["applicable"]}
    assert names & {"tolerance_table", "tolerance_sensitivity", "tolerance_monte_carlo"}
    assert not names.isdisjoint({"tolerance_table", "tolerance_sensitivity", "tolerance_monte_carlo"})
