# 地形の上を歩かせる(sim-native, GPU 不要)

sim シーンから **メッシュ地形** を作り、その上を **walker(四足/人型)** に歩かせて
**headless で GIF 化** するまでの一連。地形メッシュ化(TSDF)と歩行 GIF は **GPU 不要**
(`py -3.11` で動く)。3DGS 学習を挟む SuGaR 経路のみ GPU(`.venv-gsplat`)が要る。

## 最短(Qt ライク facade `fullseye3d`)

```python
import fullseye3d as f3d

# 起伏地形をメッシュ化(既定 method="tsdf" = GPU 不要・針無し・清潔)
mesh = f3d.Scene("rolling").mesh()            # -> Mesh(.export()/.preview())
mesh.export("rolling.ply")

# walker が地形を横断する姿を headless GIF 化(GPU 不要)
f3d.walk_gif("out/go2.gif", walker="go2", terrain="rolling", gait="trot")
```

## 共通 I/F(`unified.ops`)

| op | 役割 | GPU |
|----|------|-----|
| `tsdf_mesh` | sim 完全深度を TSDF 融合し watertight メッシュ化(針無し) | 不要 |
| `sugar_mesh` | 3DGS を表面整列 → Poisson でメッシュ抽出(深度監督つき) | 要 |
| `render_walk_gif` | walker を terrain 上で歩かせ headless GIF 化 | 不要 |
| `animate_mesh` | qpos 軌道で真値メッシュを desktop 窓再生(静的地形合成可) | 不要 |

```python
import unified as u
u.ops["tsdf_mesh"]("scene.xml", "out/mesh", n_views=48, voxel=0.02, radius=3.0,
                   elevation_deg=30, lookat=(0, 0, 0.15))
u.ops["render_walk_gif"]("out/walk.gif", walker="go2", terrain="rolling", gait="trot",
                         travel=2.2, ground_follow=True)
```

## headless 歩行 GIF(`world_render.render_walk_gif`)

Open3D の OffscreenRenderer は Windows で EGL headless 非対応のため、walker と terrain を
**MjSpec で 1 つの MuJoCo モデルに合成**(`<include>`/mesh も解決)し、MuJoCo 自身の
offscreen renderer で描画する。物理シミュレーションはせず qpos を `mj_forward` で流すだけ。

主な引数:
- `walker` / `terrain`: registry 名(`go2`/`anymal`/`spot`/`evis`、`rolling`/`terrain` …)
- `gait="trot"`(四足)または `motion="walk"`(motion npz を持つ walker)
- `travel`: >0 で root x を前進させ地形を横断(既定でカメラ追従 + 接地)
- `ground_follow`: `mj_ray` で地形高さを拾い root z を持ち上げ接地(travel>0 で自動 ON)
- `orbit_deg` / `elevation` / `distance` / `lookat`: 周回カメラ

四足(go2/anymal/spot)の trot は綺麗に接地横断する。

## registry の地形シーン

- `rolling`: 自己完結 XML の柱グリッド(滑らかな多周波 height、高さで着色)。連続起伏で歩行向き。
- `terrain`: 平床 + 低ドーム群(旧・単純)。

## honest limitations

- **evis(人型)** の `walk` motion(free2)は横倒し軌道で、直立歩行に見えない(データ由来)。
  四足は綺麗。人型直立歩行は torque-twin 系の別課題。
- **SuGaR メッシュの針状スパイク** は splat-from-Poisson の本質限界。地形メッシュには
  針の出ない **TSDF(`tsdf_mesh`)を推奨**。
