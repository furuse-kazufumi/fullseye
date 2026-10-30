"""Lighthouse virtual factory honesty and smoke gates."""
import importlib.util
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("lighthouse_vfactory",ROOT/"examples/lighthouse_vfactory.py")
vf=importlib.util.module_from_spec(spec); sys.modules[spec.name]=vf; spec.loader.exec_module(vf)

def test_detectors_cannot_read_truth():
    assert vf.audit_detector_boundary()
    for detector in (vf.baseline_detector,vf.fullseye_detector):
        assert "truth" not in detector.__annotations__

def test_generators_and_detectors_are_deterministic_and_separate():
    for kind,gen in vf.GENERATORS.items():
        a,t=gen(123); b,u=gen(123)
        assert (a==b).all() and t==u
        assert isinstance(vf.baseline_detector(a,kind),dict)
        assert isinstance(vf.fullseye_detector(a,kind,threshold=1.5 if kind=="bevel" else .08),dict)

def test_train_and_holdout_do_not_overlap():
    assert set(vf.TRAIN_SEEDS).isdisjoint(vf.HOLDOUT_SEEDS)
