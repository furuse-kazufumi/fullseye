<!-- i18n-source-sha: de960d71d9b6 -->
# Walking a Character Over Terrain (sim-native, no GPU required)

[日本語](./TERRAIN_WALK.md) · **English**

The full flow from building a **mesh terrain** out of a sim scene to letting a **walker (quadruped / humanoid)** walk across it and rendering it **headless into a GIF**. Meshing the terrain (TSDF) and the walking GIF are **GPU-free** (they run under `py -3.11`). Only the SuGaR path, which inserts 3DGS training, requires a GPU (`.venv-gsplat`).

## Shortest path (Qt-like facade `fullseye3d`)

```python
import fullseye3d as f3d

# Mesh an undulating terrain (default method="tsdf" = no GPU, no spikes, clean)
mesh = f3d.Scene("rolling").mesh()            # -> Mesh(.export()/.preview())
mesh.export("rolling.ply")

# Render, headless, the walker crossing the terrain as a GIF (no GPU)
f3d.walk_gif("out/go2.gif", walker="go2", terrain="rolling", gait="trot")
```

## Common interface (`unified.ops`)

| op | Role | GPU |
|----|------|-----|
| `tsdf_mesh` | TSDF-fuse the sim's exact depth into a watertight mesh (no spikes) | Not required |
| `sugar_mesh` | Surface-align 3DGS → extract mesh via Poisson (depth-supervised) | Required |
| `render_walk_gif` | Walk the walker over the terrain and render a headless GIF | Not required |
| `animate_mesh` | Play the ground-truth mesh in a desktop window along a qpos trajectory (can composite a static terrain) | Not required |

```python
import unified as u
u.ops["tsdf_mesh"]("scene.xml", "out/mesh", n_views=48, voxel=0.02, radius=3.0,
                   elevation_deg=30, lookat=(0, 0, 0.15))
u.ops["render_walk_gif"]("out/walk.gif", walker="go2", terrain="rolling", gait="trot",
                         travel=2.2, ground_follow=True)
```

## Headless walking GIF (`world_render.render_walk_gif`)

Because Open3D's OffscreenRenderer does not support EGL headless rendering on Windows, the walker and terrain are **composited into a single MuJoCo model with MjSpec** (resolving `<include>` and mesh references too) and drawn with MuJoCo's own offscreen renderer. No physics simulation is run; the qpos is simply pushed through `mj_forward`.

Main arguments:
- `walker` / `terrain`: registry names (`go2` / `anymal` / `spot` / `evis`, `rolling` / `terrain` …)
- `gait="trot"` (quadruped) or `motion="walk"` (for a walker that carries a motion npz)
- `travel`: when >0, advance root x to cross the terrain (camera follow + ground contact by default)
- `ground_follow`: use `mj_ray` to sample the terrain height and lift root z so the feet stay in contact (auto-ON when travel>0)
- `orbit_deg` / `elevation` / `distance` / `lookat`: orbiting camera

The trot of the quadrupeds (go2 / anymal / spot) crosses the terrain with clean ground contact.

## registry terrain scenes

- `rolling`: a self-contained XML pillar grid (smooth multi-frequency height, coloured by height). Continuous undulation, well-suited to walking.
- `terrain`: flat floor + low domes (older, simpler).

## honest limitations

- The `walk` motion (free2) of **evis (humanoid)** has a sideways-toppling trajectory and does not look like upright walking (this comes from the data itself).
  The quadrupeds are clean. Upright humanoid walking is a separate problem for the torque-twin line of work.
- The **needle-like spikes of the SuGaR mesh** are an intrinsic limitation of splat-from-Poisson. For terrain meshes, the spike-free **TSDF (`tsdf_mesh`) is recommended**.
