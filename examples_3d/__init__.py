"""Runnable worked-example scripts for Fullseye's 3-D vision toolkit.

Each ``<id>.py`` here is a self-contained, self-asserting demonstration that loads
data, calls the 3-D operators, prints a ground-truth check and asserts it. They are
indexed and run by the top-level :mod:`examples3d` registry (which is what Studio's
"3-D Examples" gallery and ``docs/EXAMPLES_3D.md`` enumerate). The scripts are meant
to be *read* and *run standalone*, not imported::

    PYTHONPATH=<repo> py -3.11 examples_3d/cad_to_scan.py

They ship in the wheel so ``examples3d.code(id)`` / ``examples3d.validate()`` work
from an installed package.
"""
