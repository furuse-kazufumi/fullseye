"""Lighthouse virtual factory honesty and smoke gates."""
import importlib.util
import sys
from pathlib import Path
import pytest
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
        model=vf._training_model(kind,vf.QUICK_TRAIN_SEEDS)
        threshold,metric=vf.tune(kind,vf.baseline_detector,vf.QUICK_TRAIN_SEEDS,model)
        assert threshold > 0
        assert 0 < metric["miss_rate"][0] < 100
        assert 0 < metric["false_positive_rate"][0] < 100

def test_good_parts_have_structural_variation_beyond_sensor_noise():
    for kind in vf.KINDS:
        good=[]
        for seed in vf.TRAIN_SEEDS:
            image,truth=vf.GENERATORS[kind](seed)
            if not truth.defective:
                good.append(image)
            if len(good)==3: break
        assert len(good)==3
        if kind=="bevel":
            # Point count changes through scanner dropout and pose changes in metric coordinates.
            assert len({len(x) for x in good})>1 or abs(good[0][:,0].mean()-good[1][:,0].mean())>.05
        else:
            assert float(abs(good[0]-good[1]).mean())>.003

def test_both_methods_receive_the_same_training_model(monkeypatch):
    model=vf._training_model("tyre",vf.QUICK_TRAIN_SEEDS)
    seen=[]
    def fake_score(kind,seeds,detector,params,variation=1.0):
        seen.append((detector.__name__,id(params.get("model"))))
        metric={"miss_rate":[10,1,20],"false_positive_rate":[10,1,20]}
        return metric,[]
    monkeypatch.setattr(vf,"score",fake_score)
    vf.tune("tyre",vf.baseline_detector,vf.QUICK_TRAIN_SEEDS,model)
    vf.tune("tyre",vf.fullseye_detector,vf.QUICK_TRAIN_SEEDS,model)
    assert {mid for _,mid in seen}=={id(model)}

def test_proposed_detector_calls_multiple_fullseye_ops():
    model=vf._training_model("tyre",vf.QUICK_TRAIN_SEEDS)
    image,_=vf.tyre(123)
    vf._OP_CALLS.clear()
    vf.fullseye_detector(image,"tyre",threshold=3,model=model)
    assert {"varmodel_score","gclose"} <= set(vf._OP_CALLS)
    assert {"varmodel_alignment","varmodel_fit"} <= set(vf.FULLSEYE_OPS)


def test_evolution_never_sees_evaluation_seeds_and_is_reproducible(monkeypatch):
    monkeypatch.setattr(vf, "score", lambda kind, seeds, detector, params: (
        {"miss_rate": [params["threshold"] % 17, 0, 0],
         "false_positive_rate": [params["threshold"] % 7, 0, 0]}, []))
    model = {"variation": object()}
    a = vf.evolve_pipeline("tyre", vf.TRAIN_SEEDS[:24], model, 12)
    b = vf.evolve_pipeline("tyre", vf.TRAIN_SEEDS[:24], model, 12)
    assert not set(a["seen_seeds"]) & set(vf.HOLDOUT_SEEDS)
    assert a["pipeline"] == b["pipeline"]
    with pytest.raises(ValueError, match="evaluation seeds"):
        vf.evolve_pipeline("tyre", vf.HOLDOUT_SEEDS[:2], model, 2)


def test_evolution_pipeline_is_typed_and_uses_fullseye_vocabulary():
    assert vf.EVOLUTION_VOCABULARY["preprocess"] == ("varmodel_score",)
    assert {"gclose", "gopen"} <= set(vf.EVOLUTION_VOCABULARY["morphology"])
