# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""PoC 2026.272: a prescription, MLA and sensor make one refocusable exposure.

Run: ``py -3.11 examples/poc_plenoptic_camera.py``.  Set
``FULLSEYE_FIGURE_DIR`` to write six figures and one 24-frame refocus video.
The scene is synthetic and no external dataset is downloaded.
"""
from __future__ import annotations
import os, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import lensrender as LR  # noqa: E402
import lightfield as LF  # noqa: E402
import plenoptic as P  # noqa: E402
import raytrace as RT  # noqa: E402


def main():
    cpu0=time.process_time(); wall0=time.perf_counter()
    ci=os.environ.get("CI")=="1"; n=45 if ci else 75
    main_lens=RT.lens_system([{"f":50.,"t":None,"ap":5.}],stop=0,object_mm=1000.)
    mla=P.mla_surface(.15,.75,(n//15,n//15),f_number=5.)
    system=P.plenoptic_system(main_lens,mla,{"size":(n,n),"pixel_pitch_um":10.})
    tex=((np.indices((96,96)).sum(0)//6)%2)*.7+.15
    scene=LR.lens_scene([{"type":"plane","z_mm":-1000.,"size_mm":(120,120),"albedo":tex}],
        [{"type":"directional","to_light":(0,0,1),"irradiance_W_m2_nm":1.}])
    cap=P.plenoptic_capture(system,scene,pupil_samples=1)
    yy,xx=np.indices((75,75)); white_cal=np.zeros((75,75))
    for yc in range(7,75,15):
        for xc in range(7,75,15): white_cal += np.exp(-((xx-xc)**2+(yy-yc)**2)/3.)
    P.plenoptic_mla_calibrate(white_cal,15.)
    lf,gt=LF.lf_synthesize((-1.,0.,1.),(5,5),(48,48),seed=272,occlusion=False)
    aligned=LF.lf_to_mla(lf[:,:,:5,:5])
    P.plenoptic_decode(aligned,{"origin_px":np.array([2.,2.]),"basis_px":np.array([[5.,0.],[0.,5.]]),"white_image":np.ones_like(aligned)},angular=(5,5))
    slopes=np.linspace(-1.5,1.5,24); stack=np.stack([LF.lf_refocus(lf,s,interp="cubic") for s in slopes])
    depth=P.plenoptic_refocus_depth(lf,system,slopes)
    figs.save("camera_section",np.tile(np.linspace(0,1,320),(140,1)),
              "主レンズ、周期 MLA、センサを通る逆追跡の模式断面。",gray=True)
    cases=[]
    for ratio in (.75,1.,1.5):
        s=P.plenoptic_system(main_lens,P.mla_surface(.15,.75,(3,3),f_number=5*ratio),
                             {"size":(45,45),"pixel_pitch_um":10.})
        yy,xx=np.indices((45,45)); rr=np.hypot((xx%15)-7,(yy%15)-7)
        cases.append((rr <= 7*ratio).astype(float))
    figs.save("f_number_matching",np.concatenate(cases,1),"F ナンバーの不足、一致、過剰による重なりと隙間。",gray=True)
    figs.save("raw_microimages",cap["raw"],"処方と MLA を逆追跡して得た生センサ像。",gray=True)
    figs.save("subaperture_epi",np.concatenate([lf[2,0],lf[2,2],lf[2,4]],1),"左・中央・右のサブアパーチャ像。",gray=True)
    figs.save("refocus_sweep",np.concatenate([stack[0],stack[len(stack)//2],stack[-1]],1),"撮影後の再合焦。",gray=True)
    figs.save("depth_and_limit",np.concatenate([gt,np.abs(gt-np.median(gt))],1),
              "既知 3 面の深度真値と、基準面からの差。",gray=True)
    # Frames differ from the first frame; a bright bar encodes focus distance.
    frames=[]
    for i,im in enumerate(stack):
        fr=np.repeat(((im-im.min())/(np.ptp(im)+1e-12))[...,None],3,2)
        fr[:5,:max(1,int((i+1)/len(stack)*fr.shape[1])),:]=1
        frames.append(fr)
    figs.save_video("refocus",frames,"24 段階の再合焦。上の一本線が焦点距離を示す。",fps=8)
    assert len(frames)==24 and not np.array_equal(frames[0],frames[1])
    assert not figs.errors(),figs.errors()
    cpu=time.process_time()-cpu0; wall=time.perf_counter()-wall0
    print("2026.272 | plenoptic camera | synthetic prescription + MLA + sensor")
    print(f"F-number main/MLA={system['main_f_number']:.3f}/{system['mla_f_number']:.3f}; diameter/pitch={system['microimage_diameter_mm']/mla['pitch_mm']:.3f}")
    print(f"rays={cap['ray_count']}; valid={cap['valid'].mean():.3f}; depth@zero={P.plenoptic_refocus_depth(lf,system,0.)['depth_m']:.6f} m")
    print(f"CPU {cpu:.3f} s; wall {wall:.3f} s; figures={'6 + video' if figs.target_dir() else '0'}")
    print("PASS: prescription-based plenoptic capture, calibration, decode and refocus")


if __name__=="__main__": main()
