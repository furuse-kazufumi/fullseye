"""Read a lens file, tolerance it, then inspect the worst prescription's MTF."""
import lensfile
import lensimage
import lenstol


def run():
    system = lensfile.lens_file_read(None)["system"]
    table = lenstol.tolerance_table(system, defaults={"radius_pct": 0.01})
    criteria = lenstol.tolerance_criteria(efl={"min": 1.0}, rings=2)
    monte_carlo = lenstol.tolerance_monte_carlo(system, table, criteria, trials=12, seed=7)
    worst = monte_carlo["worst_trial"]["prescription"]
    mtf = lensimage.through_focus_mtf(worst, frequency_cpmm=[20.0],
                                      defocus_mm=[-0.1, 0.0, 0.1], size=16)
    return {"tolerance_table": table, "monte_carlo": monte_carlo,
            "worst_through_focus_mtf": mtf}


if __name__ == "__main__":
    result = run()
    print(result["monte_carlo"]["worst_trial"]["values"])
