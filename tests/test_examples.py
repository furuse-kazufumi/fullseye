"""Smoke tests: the example scripts run end-to-end on synthetic data and produce
sane results, so the cross-project templates stay working."""
import importlib.util
import os

_EX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_EX, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_perception_pipeline_runs():
    r = _load("perception_pipeline").run()
    assert r["n_points"] > 0
    assert 0.0 <= r["walkable_frac"] <= 1.0
    assert r["depth_valid_frac"] > 0.0


def test_segment_and_classify_runs():
    labelled = _load("segment_and_classify").run()
    assert len(labelled) == 3                       # two disks + one square
    names = [name for name, *_ in labelled]
    assert names.count("disk") == 2 and names.count("square") == 1
