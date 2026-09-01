![From projections to voxels — the CT road](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingct_pipeline.gif)

*↑ **From projections to voxels, the whole CT road** — phantom, projection, sinogram, reconstruction, window, segmentation, voxels, mesh, in eight steps. A part whose volume is known in closed form (16839 mm³) rebuilt from 128 projections measures 16896 mm³ (+0.3%); reconstruction nRMS 0.0177, 67744 mesh faces, 27696 boundary points. Ops used: `radon_volume`, `fbp_volume`, `vol_window_level`, `vol_label`, `vol_region_props`, `marching_cubes`, `vol_boundary_points`.*

![More projections, and the image stands up](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingct_view_sweep.gif)

*↑ **More projections, and the image stands up** — the same object at 8, 16, 32, 64 and 128 views. Reconstruction nRMS improves 0.3635 → 0.0334, a factor of 10.9, while **the volume barely moves**: +3.4% → +0.3%. Streaks appear symmetrically in sign, so they cancel in a single integrated quantity. What does reveal the damage is the component count (175 against 1). Ops used: `projection_angles`, `ellipse_sinogram`, `filtered_backprojection`.*

[![View count and volume error, tiled](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_view_tiles_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_view_tiles.png)

*↑ **The same thing as a tile** — the truth top left, then 8 / 16 / 32 / 64 / 128 views. Labels carry the reconstruction nRMS and the volume error. At 8 views the inside of the skull is unreadable through the streaks, yet the volume is off by only +3.4%. Ops used: `ellipse_phantom`, `ellipse_sinogram`, `filtered_backprojection`.*

![A miscentred axis of rotation](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingct_center_shift.gif)

*↑ **Half a pixel of centre error is already a double image** — 0, 0.5, 1 and 2 px. Reconstruction nRMS goes 0.0250 → 0.0537 → 0.1016 → 0.1630: **half a pixel costs 2.1x the error** while looking merely soft rather than wrong. `sinogram_center_of_rotation` recovers it from the centre-of-mass identity to within 0.0029 px. Ops used: `sinogram_center_shift`, `sinogram_center_of_rotation`.*

[![When the angular range runs out](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_limited_angle_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_limited_angle.png)

*↑ **A limited angular range deletes specific directions, not detail in general** — 180, 120, 90 and 60 degrees. By the central-slice theorem the unmeasured wedge of the Fourier plane is simply empty. Measured as retained energy per 30-degree sector, a 90-degree scan holds 0.96 on the side it measured and falls to 0.07 on the side it did not. The surviving directions stay sharp, which is exactly what makes such a reconstruction convincing. Ops used: `ellipse_sinogram`, `filtered_backprojection`.*

[![Beam hardening (the cupping artefact)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_beam_hardening_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_beam_hardening.png)

*↑ **Beam hardening — the centre of a uniform disc sinks** — a real X-ray beam is not monochromatic, so a ray that survives a thicker path is harder and attenuates less per unit length, and the line integral stops being proportional to path length. The disc's centre-to-rim ratio drops 1.0006 → 0.9335, and `beam_hardening_correct` returns it to 1.0006. The difference panel (blue = lost, orange = gained) shows that only the centre sank. Ops used: `beam_hardening_apply`, `beam_hardening_correct`.*

[![Ring artefacts](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_rings_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_rings.png)

*↑ **Ring artefacts — one bad detector pixel becomes one perfect circle** — a detector bin with gain g is offset, after the logarithm, by **the same constant at every angle**. Back-projecting a constant column smears it into a circle about the rotation axis. A 2 % gain spread takes nRMS 0.0250 → 0.0643 (2.6x), and `ring_artifact_remove` brings it to 0.0358, undoing 72% of the damage. Ops used: `ring_artifact_apply`, `ring_artifact_remove`.*

[![Checking the volume](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_volume_check_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_volume_check.png)

*↑ **Checking the volume — what matters, and what does not** — the closed-form truth is 16839 mm³, and merely digitising it on this grid already gives 16863 mm³. On the left, sweeping the view count from 8 to 128 moves the answer by 522 mm³; on the right, sweeping the binarisation threshold from 0.30 to 0.70 moves it by 533 mm³. **The arbitrariness of the threshold matters 1x more than the view count**, so the number to publish alongside a volume is which threshold cut it, not how many views took it. Ops used: `radon_volume`, `fbp_volume`, `vol_label`, `vol_region_props`.*
