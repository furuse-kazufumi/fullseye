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

## Coordinate-break designs (`cb_*.zmx`, `coordbrk_recorded.json`)

Hand-written `.zmx` texts (Fullseye test designs, no third-party content) that exercise `COORDBRK` surfaces:

| file | what it contains |
|---|---|
| `cb_tilted_plate.zmx` | singlet, then a decentred three-axis tilted plate and its exact return (order flag 1, `PPAR` pickups of the negated values) |
| `cb_plate_x_undo.zmx` | collimated beam through an x-tilted plate; the return is the same angle negated (maps to the tracer's undo element) |
| `cb_fold_two_axis.zmx` | singlet, a decentred two-axis fold mirror, another decentred multi-axis break after the mirror (negative thicknesses) |
| `cb_off_axis_parabola.zmx` | paraboloid used 36 mm off its axis through a decentre (closed form: perfect point focus, EFL = f(1 + (h/2f)^2)) |
| `cb_three_mirrors.zmx` | three mirrors with dummy planes, tilt pickups and a decentre after two and after three reflections |

`coordbrk_recorded.json` holds optiland 0.6.3's (MIT) real-ray result for the same files: global intersection points and
direction cosines per surface row for 8-12 rays each (several fields with both x and y components, four pupil points),
and the index of every glass row at 0.55 um. Produced on 2026-10-19 in the separate virtual environment with

```
for each file: op = optiland.fileio.load_zemax_file(path)
               op.trace_generic(Hx, Hy, Px, Py, 0.55); read op.surface_group.x/y/z/L/M/N
```

(H = field / largest field radius, as optiland normalises it). optiland merges each coordinate break into the next
surface, so its rows are the object, the non-break surfaces in file order and the image. Its reader **does not use the
order flag (`PARM 6`)**: for `cb_tilted_plate.zmx` (order-1 return) the image-plane position is therefore not compared
(the closed-form check "the return restores the frame" replaces it). Model glasses are replaced by optiland's own index
at 0.55 um in the comparison (the two dispersion models differ in the fifth digit).
