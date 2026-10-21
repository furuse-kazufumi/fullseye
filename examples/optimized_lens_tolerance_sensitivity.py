"""Feed an operand-optimised prescription directly into tolerance sensitivity."""
import lensmerit
import lenstol
import raytrace


def run():
    system = raytrace.example_system("singlet")
    operands = lensmerit.merit_default(system, rings=2)
    optimized = lensmerit.optimize_lens_operands(
        system, operands, variables=["c0"], iterations=2)
    table = lenstol.tolerance_table(optimized["system"], defaults={"radius_pct": 0.01})
    criteria = lenstol.tolerance_criteria(rms_spot={}, rings=2)
    sensitivity = lenstol.tolerance_sensitivity(optimized["system"], table, criteria)
    return {"optimization": optimized, "tolerance_table": table,
            "sensitivity": sensitivity}


if __name__ == "__main__":
    result = run()
    print(result["sensitivity"]["drivers"][0]["id"])
