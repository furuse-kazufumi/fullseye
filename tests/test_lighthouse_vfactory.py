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
    assert len(vf.TRAIN_SEEDS) >= 200
    assert len(vf.HOLDOUT_SEEDS) >= 500

def test_equal_search_budget_and_training_only(monkeypatch):
    seen=[]
    original=vf.score
    def guarded(kind,seeds,detector,params):
        assert not (set(seeds) & set(vf.HOLDOUT_SEEDS))
        seen.append((detector.__name__,tuple(seeds)))
        return original(kind,seeds,detector,params)
    monkeypatch.setattr(vf,"score",guarded)
    vf.tune("tyre",vf.baseline_detector,vf.QUICK_TRAIN_SEEDS)
    vf.tune("tyre",vf.fullseye_detector,vf.QUICK_TRAIN_SEEDS)
    assert sum(n=="baseline_detector" for n,_ in seen)==vf.SEARCH_BUDGET
    assert sum(n=="fullseye_detector" for n,_ in seen)==vf.SEARCH_BUDGET

def test_tuned_baselines_are_not_all_or_nothing():
    for kind in vf.KINDS:
        threshold,metric=vf.tune(kind,vf.baseline_detector,vf.QUICK_TRAIN_SEEDS)
        assert threshold > 0
        assert 0 < metric["miss_rate"][0] < 100
        assert 0 < metric["false_positive_rate"][0] < 100
