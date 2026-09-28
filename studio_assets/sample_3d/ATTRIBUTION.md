# 3-D sample data — sources & attribution

## itokawa_points.npy
Decimated surface point cloud of near-Earth asteroid **25143 Itokawa**, derived from
the **Gaskell shape model** produced from JAXA *Hayabusa* mission imagery.

- Source: JAXA DARTS archive — https://data.darts.isas.jaxa.jp/pub/hayabusa/shape/gaskell/
  (file `itokawa_f0049152.stl`, "generated from tri2stl by Naru Hirata").
- The Gaskell Itokawa shape model is co-archived at the **NASA PDS Small Bodies Node**
  (public-domain scientific data).
- Please cite: Gaskell, R. W., et al. (2008), *Characterizing and navigating small bodies
  with imaging data*, Meteoritics & Planetary Science 43(6), 1049-1061; and the Hayabusa/AMICA
  shape dataset. Shipped here as a small derived point cloud for demonstration.

## skeleton_ct.npy
Synthetic X-ray-CT density volume built by voxelising anatomical hand-bone meshes from the
**MS-Human-700** musculoskeletal model (bone geometry), arranged in a dummy hand pose. Used
only to demonstrate Fullseye's volumetric / tomography operators on realistic bone shapes.

## kenney/ (car-kit, city-kit-roads)
Low-poly vehicle, traffic-light, sign and street-light meshes (OBJ + one colour-map texture per kit)
from **Kenney** — *Car Kit 3.1* and *City Kit Roads 2.1*, https://kenney.nl — released under
**CC0 1.0** (public domain dedication; `License.txt` in each folder is the original). Only the files
`driveworld.ASSETS` reads are shipped (9 meshes, 2 textures). Credit is not required by the licence;
we credit Kenney anyway. Used by `driveworld` to populate the driving-school world with cars and signals.
