#!/usr/bin/env python3
"""Extract and close six teaching meshes from the BodyParts3D 4.0 archive.

The source archive is deliberately not stored in the repository.  Run this script
with the downloaded ``partof_BP3D_4.0_obj_99.zip``.  The already 99%-reduced OBJ
surfaces contain open seams. Vertices are welded and a fan is used only if that
leaves a small boundary loop. This is a measurement demonstration, not a
diagnostic model.
"""
from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import numpy as np

FILES = {
    "heart": "FJ2423", "liver": "FJ2824", "kidney_left": "FJ3145",
    "kidney_right": "FJ3147", "lung_left": "FJ2881", "lung_right": "FJ2921",
}


def read_obj(raw: bytes):
    vertices, faces = [], []
    for line in io.StringIO(raw.decode("ascii", errors="strict")):
        if line.startswith("v "):
            vertices.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            faces.append([int(x.split("/")[0]) - 1 for x in line.split()[1:4]])
    return np.asarray(vertices, dtype=np.float64), np.asarray(faces, dtype=np.int32)


def boundary_edges(faces):
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    undirected = np.sort(directed, axis=1)
    _, inverse, counts = np.unique(undirected, axis=0, return_inverse=True, return_counts=True)
    return directed[counts[inverse] == 1]


def weld(vertices, faces, relative_tolerance=1e-6):
    """Merge coincident seam vertices using a scale-derived quantisation."""
    tolerance = np.linalg.norm(np.ptp(vertices, axis=0)) * relative_tolerance
    keys = np.rint(vertices / tolerance).astype(np.int64)
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    out_v = vertices[first]
    out_f = inverse[faces]
    keep = (out_f[:, 0] != out_f[:, 1]) & (out_f[:, 1] != out_f[:, 2]) & (out_f[:, 2] != out_f[:, 0])
    return out_v, out_f[keep].astype(np.int32), tolerance


def cap_small_holes(vertices, faces):
    """Close every degree-two boundary component with an oppositely wound fan."""
    edges = boundary_edges(faces)
    adjacency = {}
    for a, b in edges:
        adjacency.setdefault(int(a), set()).add(int(b)); adjacency.setdefault(int(b), set()).add(int(a))
    if any(len(v) != 2 for v in adjacency.values()):
        raise ValueError("boundary is not a set of simple loops")
    components, unseen = [], set(adjacency)
    while unseen:
        seed = unseen.pop(); stack = [seed]; component = [seed]
        while stack:
            a = stack.pop()
            for b in adjacency[a]:
                if b in unseen:
                    unseen.remove(b); stack.append(b); component.append(b)
        components.append(component)
    out_v = [*vertices]
    out_f = [*faces]
    for component in components:
        centre = len(out_v); out_v.append(vertices[component].mean(axis=0))
        members = set(component)
        for a, b in edges:
            if int(a) in members:
                out_f.append([int(b), int(a), centre])
    return np.asarray(out_v), np.asarray(out_f, dtype=np.int32), len(components)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", type=Path)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "bodyparts3d")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(a.archive) as zf:
        for name, fid in FILES.items():
            path = "partof_BP3D_4.0_obj_99/%s.obj" % fid
            source_v, source_f = read_obj(zf.read(path))
            source_boundary = len(boundary_edges(source_f))
            vertices, faces, tolerance = weld(source_v, source_f)
            welded_boundary = len(boundary_edges(faces))
            if welded_boundary:
                vertices, faces, loops = cap_small_holes(vertices, faces)
                method = "vertex_weld_and_fan_cap"
            else:
                method, loops = "vertex_weld", 0
            signed_volume = np.einsum("ij,ij->i", vertices[faces[:, 0]],
                                      np.cross(vertices[faces[:, 1]], vertices[faces[:, 2]])).sum() / 6
            if signed_volume < 0:
                faces = faces[:, ::-1]
            after = len(boundary_edges(faces))
            np.savez_compressed(a.out / (name + ".npz"), vertices=vertices.astype(np.float32), faces=faces,
                                source_id=fid, source_vertices=len(source_v), source_faces=len(source_f),
                                source_boundary_edges=source_boundary, welded_boundary_edges=welded_boundary,
                                repaired_boundary_edges=after,
                                repair_method=method, boundary_loops=loops, weld_tolerance=tolerance)
            print(name, fid, method, "boundary", source_boundary, "->", welded_boundary, "->", after,
                  "V/F", len(vertices), len(faces))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
