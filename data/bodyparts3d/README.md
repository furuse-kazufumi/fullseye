# BodyParts3D organ meshes

These six meshes are derived from `partof_BP3D_4.0_obj_99.zip`, BodyParts3D
version 4.0 (the 99% polygon-reduced PART-OF archive), downloaded 2026-10-26.
`tools/import_bodyparts3d_organs.py` records the source element ID and welds
coincident seam vertices with a tolerance of one millionth of the bounding-box
diagonal. The apparent source boundaries (heart 34, liver 1,522, kidneys 10/22,
lungs 6/10 edges) all close to zero by welding alone; no convex hull is used.
If a future source leaves a small loop, the importer can close it with a triangle
fan and records that method in the NPZ. The source's 99% reduction still loses
fine anatomy and is unsuitable for diagnosis.

BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International
