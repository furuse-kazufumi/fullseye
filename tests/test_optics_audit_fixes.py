import importlib.util
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"examples"/(name+".py"))
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def test_o05_central_difference_transfer():
    m=load("poc_slanted_edge_sfr_limits")
    assert m.derivative_correction([0])[0] == 1
    assert abs(m.derivative_correction([.5])[0]-1.1107207345) < 1e-9

def test_o06_strehl_definitions_for_coma():
    m=load("poc_wavefront_aberration_limits")
    a=m.strehl_definitions(rms=.2); b=m.strehl_definitions(rms=.3)
    assert abs(a["fixed_axis_ratio"]-.18156)<.004
    assert abs(a["same_plane_peak_ratio"]-.21781)<.004
    assert abs(b["fixed_axis_ratio"]-.01269)<.002
    assert abs(b["same_plane_peak_ratio"]-.14368)<.004
    assert abs(a["peak_shift_px"][1])==8 and abs(b["peak_shift_px"][1])==17

def test_o07_pixel_sampling_counterexample():
    m=load("poc_laser_line_speckle_floor")
    got=[m.sampled_gaussian_centroid(pitch=p) for p in (.5,1,2)]
    assert np.allclose(got,[.22997,.17659,.01023],atol=6e-4)

def test_o01_raw_causally_changes_decode_refocus_and_depth():
    import plenoptic as p, lightfield as lf
    from scipy.ndimage import gaussian_filter
    n=48; pitch=8; white=np.zeros((n,n)); white[4::pitch,4::pitch]=1
    white=gaussian_filter(white,1); cal=p.plenoptic_mla_calibrate(white,pitch,max_residual_px=.3)
    raw1=white*(1+np.linspace(0,1,n)[None,:]); raw2=raw1.copy(); raw2[:,n//2:]*=.4
    a=p.plenoptic_decode(raw1,cal,angular=(5,5)); b=p.plenoptic_decode(raw2,cal,angular=(5,5))
    assert not np.allclose(a,b)
    assert not np.allclose(lf.lf_refocus(a,.3),lf.lf_refocus(b,.3))
    sa,_=lf.lf_depth_from_focus(a,np.linspace(-.5,.5,5),window=3)
    sb,_=lf.lf_depth_from_focus(b,np.linspace(-.5,.5,5),window=3)
    assert np.any(sa!=sb)


def test_o01_capture_flat_field_calibrates_full_scale_lattice():
    """The matching optical flat, not a finite white specimen, calibrates MLA centres."""
    m=load("poc_plenoptic_camera")
    import plenoptic as p, raytrace as rt
    lens=m.prescription(); para=rt.paraxial_trace(lens)
    n_main=abs(float(para["efl"]))/(2*float(para["xp_radius"]))
    mla=p.mla_surface(.15,.75,(32,32),f_number=n_main,shape="square")
    system=p.plenoptic_system(lens,mla,{"size":(480,480),"pixel_pitch_um":10})
    cap=p.plenoptic_capture(system,m.inspection_scene(),pupil_samples=1)
    cal=p.plenoptic_mla_calibrate(cap["white_image"],15,max_residual_px=.3)
    assert cal["residual_px"] < 1e-6
    assert abs(cal["pitch_px"]-15) < 1e-6
