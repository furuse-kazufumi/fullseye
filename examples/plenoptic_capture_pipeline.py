"""Existing lens and scene generators -> plenoptic capture."""
import numpy as np
import lensrender as LR
import plenoptic as P
import raytrace as RT

def main():
    main_lens = RT.lens_system([{"f": 50., "t": None, "ap": 5.}], stop=0, object_mm=1000.)
    mla = P.mla_surface(.15, .75, (6, 6), f_number=5.)
    system = P.plenoptic_system(main_lens, mla, {"size": (96, 96), "pixel_pitch_um": 9.375})
    texture = .15 + .7*((np.indices((128, 128)).sum(0)//8) % 2)
    scene = LR.lens_scene([{"type": "plane", "z_mm": -1000., "size_mm": (120, 120),
                            "albedo": texture}],
                          [{"type": "directional", "to_light": (0, 0, 1),
                            "irradiance_W_m2_nm": 1.}])
    capture = P.plenoptic_capture(system, scene)
    assert capture["raw"].shape == (96, 96)
    assert capture["ray_count"] == 96*96
    print("PASS: lens_system + lens_scene -> plenoptic_capture")


if __name__ == "__main__":
    main()
