# lensfile gate data

Sequential prescriptions in the `.zmx` text format, written by Fullseye's own
`lensfile.lens_file_write` (so they carry no third-party file content):

| file | design | provenance of the numbers |
|---|---|---|
| `triplet_const.zmx` | Cooke triplet f/5, +-20 deg, constant indices 1.62041 / 1.62004 | radii and spacings from the optiland sample set (`optiland.samples.objectives.CookeTriplet`, MIT, (c) 2024 Kramer Harrison) |
| `triplet_catalog.zmx` | the same with catalogue glasses of Fullseye's material table | as above; glass coefficients refractiveindex.info database (CC0 1.0) |
| `double_gauss_const.zmx` | double Gauss f/5, constant d-line indices | radii and spacings from the optiland sample set (`DoubleGauss`, MIT) |
| `asphere_singlet.zmx` | even-asphere singlet (conic + r^4, r^6, r^8) | Fullseye test design |

`second_recorded.json` holds what two independent open-source readers computed
from these very files (each with its own .zmx parser, ray tracer and glass
model): ray-optics 0.9.8 (BSD-3-Clause) and optiland 0.6.3 (MIT). It was
produced on 2026-10-18 in a separate virtual environment (neither package is a
Fullseye dependency) by loading every file with `rayoptics.zemax.zmxread.read_lens_file`
and `optiland.fileio.load_zemax_file`, then recording first-order data, the
third-order (Seidel) sums of ray-optics and real-ray image coordinates of
optiland. optiland cannot evaluate a model glass with V_d = 0, so its entries
for the constant-index files are NaN and are not used.
