# wing3d 生成物の実測(読み戻して確認した値)

生成: `py -3.11 tools/gen_wing3d_gallery.py`  seed `20260902`

| 展示 | 形式 | ファイル | 実測 | SHA-256 (先頭 16) |
|---|---|---|---|---|
| domain | GIF+mp4 | `media/wing3d_domain_memory.gif` | 40 フレーム, 1120x690, 0.48 MB, 256 色, mp4 0.07 MB | `8a3b89df7c282535` |
| boundary | GIF+mp4 | `media/wing3d_boundary_shell.gif` | 36 フレーム, 1120x640, 2.74 MB, 128 色, mp4 1.59 MB | `d56e8ff18bc8163e` |
| rle | PNG | `wing3d_rle_compression.png` | 1120x786, 109 kB | `5ed1e9464bf1367d` |
| windowing | GIF+mp4 | `media/wing3d_ct_windowing.gif` | 40 フレーム, 1120x726, 0.50 MB, 256 色, mp4 0.08 MB | `5e745b230bbe437a` |
| vesselness | PNG | `wing3d_vesselness_control.png` | 1120x700, 89 kB | `b646c9422e87ca3f` |
| skeleton | GIF+mp4 | `media/wing3d_skeleton_graph.gif` | 48 フレーム, 1120x660, 1.41 MB, 256 色, mp4 0.26 MB | `0c27c243f2169388` |
| wall | PNG | `wing3d_wall_thickness.png` | 1120x792, 108 kB | `705ea090f2bce633` |
| rl | GIF+mp4 | `media/wing3d_richardson_lucy.gif` | 18 フレーム, 1120x660, 0.63 MB, 256 色, mp4 0.09 MB | `8e09464195d23fa5` |
| visualhull | GIF+mp4 | `media/wing3d_visual_hull.gif` | 16 フレーム, 1120x690, 0.67 MB, 256 色, mp4 0.22 MB | `e923601ba8825626` |
| obb | GIF+mp4 | `media/wing3d_obb_innerbox.gif` | 48 フレーム, 1120x700, 2.23 MB, 256 色, mp4 0.49 MB | `de353b6f6102dc53` |
| icp | GIF+mp4 | `media/wing3d_icp_registration.gif` | 18 フレーム, 1120x660, 0.58 MB, 256 色, mp4 0.43 MB | `7fa6f0a6cec5647f` |
| anisotropic | PNG | `wing3d_anisotropic_voxel.png` | 1120x700, 92 kB | `f44819cdeb1d8304` |
| mip | GIF+mp4 | `media/wing3d_mip_turntable.gif` | 36 フレーム, 1120x640, 2.65 MB, 64 色, mp4 0.41 MB | `19d183d9e10214a4` |
| distance | GIF+mp4 | `media/wing3d_distance_transform.gif` | 46 フレーム, 1120x660, 0.61 MB, 256 色, mp4 0.09 MB | `548d5d82d1a75960` |
| connectivity | PNG | `wing3d_boundary_connectivity.png` | 948x768, 33 kB | `ea715605379f6e41` |
| pipeline | GIF | `media/wing3d_pipeline_flow.gif` | 7 フレーム, 900x588, 0.33 MB | `79f70ee88eb6cbcf` |
| zsweep | GIF+mp4 | `media/wing3d_slice_zsweep.gif` | 96 フレーム, 1120x748, 1.16 MB, 256 色, mp4 0.16 MB | `59e378261b580ace` |
| mpr | GIF+mp4 | `media/wing3d_mpr_crosshair.gif` | 60 フレーム, 1120x620, 1.18 MB, 256 色, mp4 0.22 MB | `7480c3d1fd5b2c4c` |
| oblique | GIF+mp4 | `media/wing3d_oblique_slice.gif` | 36 フレーム, 1120x640, 0.91 MB, 256 色, mp4 0.11 MB | `19fb9c8851196342` |
| windowsweep | GIF+mp4 | `media/wing3d_window_sweep.gif` | 70 フレーム, 1120x660, 1.44 MB, 256 色, mp4 0.20 MB | `2bb491b5e7634356` |
| isosurface | GIF+mp4 | `media/wing3d_isosurface_sweep.gif` | 40 フレーム, 1120x640, 1.18 MB, 256 色, mp4 0.31 MB | `9858bde5a3a5d786` |
| vessel | GIF+mp4 | `media/wing3d_vessel_reslice.gif` | 49 フレーム, 1120x664, 0.96 MB, 256 色, mp4 0.15 MB | `78648d300d2e25c2` |
