"""Numerical gates for the three deep optics PoCs."""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    p=ROOT/"examples"/f"{name}.py"; s=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def test_wavefront_independent_paths_and_boundaries():
    *_,err,bounds=load("poc_wavefront_aberration_limits").compute(); assert err<.015; assert len(set(bounds.values()))>1
def test_mueller_rank_is_computed_and_complete_design_recovers():
    _,_,ranks,patherr,errs=load("poc_mueller_dofp_observability").compute(); assert ranks==(9,16); assert patherr<1e-12; assert errs["qwp_added"]<errs["linear_only"]
def test_slanted_edge_truth_and_sweep_gate():
    *_,rows,maxclean,_=load("poc_slanted_edge_sfr_limits").compute(); assert len(rows)==420; assert maxclean<.025
