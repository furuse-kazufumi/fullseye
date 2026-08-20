"""Fullseye 3D ―― 人間が使いやすい、Qt 風の流れるツールキット。

共通 I/F(unified の op)を、決まった手順で気持ちよく呼べるように薄く包んだ facade。

  import fullseye3d as f3d

  f3d.scenes()                                  # 使えるシーン一覧
  f3d.Scene("go2").splat(quality="high").show() # 3DGS 化して全周プレビュー
  f3d.Scene("go2").splat().export("go2.ply")    # 3DGS を .ply 書き出し
  f3d.Scene("go2").walk(gait="trot").show()     # トロットで歩く 3DGS
  terrain = f3d.Scene("terrain").mesh()         # SuGaR メッシュ抽出
  f3d.Scene("evis").walk(on=terrain).show()     # evis が地形メッシュ上を歩く

show() は desktop 窓(要 GL)、export()/preview() はファイル。GPU は自動設定。
"""
from __future__ import annotations
import os

_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "fullseye3d")


def _cuda():
    import fullseye_3dgs as F
    F.setup_cuda_env()


def scenes():
    """登録シーンの一覧 [(name, category, available)]。"""
    import scene_registry as R
    return [(n, s.get("category", ""), av) for n, s, av in R.entries()]


def _open(path):
    try:
        os.startfile(path)                       # Windows 既定ビューア
    except Exception:
        pass
    return path


class Splat:
    """3DGS 学習の結果(全周GIF / novelview / gaussians.ply)。"""

    def __init__(self, out_dir, info):
        self.dir = out_dir
        self.info = info
        self.psnr = info.get("test_psnr")

    def show(self):
        return _open(os.path.join(self.dir, "turntable.gif"))

    def export(self, path=None):
        src = os.path.join(self.dir, "gaussians.ply")
        if path and os.path.isfile(src):
            import shutil
            shutil.copy(src, path)
            return path
        return src


class Mesh:
    """SuGaR 抽出メッシュ(.ply)。walk(on=mesh) に渡せる。"""

    def __init__(self, ply, info=None):
        self.ply = ply
        self.info = info or {}

    def preview(self):
        p = os.path.join(os.path.dirname(self.ply), "mesh_preview.png")
        return _open(p) if os.path.isfile(p) else None

    def export(self, path=None):
        if path:
            import shutil
            shutil.copy(self.ply, path)
            return path
        return self.ply


class Scene:
    """1 つの sim シーン。splat()/mesh()/walk() を流れるように呼べる。"""

    def __init__(self, name):
        import scene_registry as R
        self.name = name
        self.spec = R.resolve(name)
        if self.spec is None:
            raise ValueError(f"scene '{name}' が見つかりません。f3d.scenes() を確認してください。")

    def _framing(self):
        return dict(radius=self.spec["radius"], elevation_deg=self.spec["elevation_deg"],
                    lookat=self.spec["lookat"])

    def splat(self, quality="balanced", densify=False, out=None):
        """3DGS 化。Splat(.show()/.export()) を返す。"""
        _cuda()
        import gsplat_train_native as N
        res, ng, iters, nv = {"fast": (128, 8000, 600, 24), "balanced": (256, 20000, 1000, 36),
                              "high": (384, 45000, 1500, 48)}[quality]
        out = out or os.path.join(_OUT, f"splat_{self.name}")
        fr = self._framing()
        if densify:
            info = N.train_densify(self.spec["xml"], out, n_views=nv, iters=max(iters, 1200),
                                   res=res, n_gauss_init=max(4000, ng // 3), **fr)
        else:
            info = N.train(self.spec["xml"], out, n_views=nv, iters=iters, res=res,
                           n_gauss=ng, **fr)
        return Splat(out, info)

    def mesh(self, quality="balanced", method="tsdf", out=None):
        """メッシュ抽出。method='tsdf'(既定)=sim 深度を TSDF 融合(GPU 不要・清潔・
        針無し・XY footprint ほぼ完璧)、method='sugar'=3DGS を表面整列→Poisson(要 GPU)。
        Mesh を返す。"""
        import unified as u
        out = out or os.path.join(_OUT, f"mesh_{self.name}")
        fr = self._framing()
        if method == "tsdf":
            res = {"fast": 200, "balanced": 240, "high": 300}[quality]
            vox = {"fast": 0.03, "balanced": 0.02, "high": 0.015}[quality]
            r = u.ops["tsdf_mesh"](self.spec["xml"], out, n_views=48, res=res, voxel=vox, **fr)
        else:
            _cuda()
            res, ng, iters = {"fast": (200, 8000, 1000), "balanced": (220, 9000, 1400),
                              "high": (256, 12000, 1800)}[quality]
            r = u.ops["sugar_mesh"](self.spec["xml"], out, n_views=40, iters=iters, res=res,
                                    n_gauss_init=ng, flatten=0.03, **fr)
        return Mesh(r["mesh_ply"], r)

    def walk(self, motion=None, gait=None, on=None, z_offset=0.16):
        """メッシュのまま歩かせる(散乱ゼロ)。on=Mesh を渡すとその上で歩く。

        launch する Popen を返す(desktop 窓)。GL が無い環境では None。"""
        _cuda()
        import numpy as np
        import scene_registry as R
        import sim_source as S
        xml = open(self.spec["xml"], encoding="utf-8").read()
        mpath = R.motion(self.name, motion) if (motion or not gait) else None
        if mpath:
            qpos = np.load(mpath).astype(float)
        elif gait:
            import gaits as G
            import mujoco
            m = mujoco.MjModel.from_xml_string(xml)
            d = mujoco.MjData(m); mujoco.mj_forward(m, d)
            qpos = G.build(m, np.asarray(d.qpos), gait, n_frames=60)
            if qpos is None:
                raise ValueError(f"gait '{gait}' はこのモデルで生成不可")
        else:
            raise ValueError("motion 名か gait を指定してください(例: walk / trot)")
        static = None
        if on is not None:
            qpos = qpos.copy(); qpos[:, 2] += z_offset
            static = on.ply if isinstance(on, Mesh) else str(on)
        return S.launch_animation(xml, qpos, title=f"{self.name}", static_mesh=static)


def demo_world_walk(terrain_name="rolling", **kw):
    """『起伏地形メッシュの上を evis がメッシュで歩く』を1呼び出しで(既定 TSDF=GPU不要)。"""
    terrain = Scene(terrain_name).mesh(**kw)
    return Scene("evis").walk(on=terrain)


def walk_gif(out_gif, walker="go2", terrain="rolling", gait="trot", motion=None, **kw):
    """walker が terrain 上を歩く姿を headless GIF 化(GPU 不要)。パスを返す。

    四足(go2/anymal/spot)は gait='trot'、人型は motion='walk' を渡す。
    """
    import world_render as WR
    if motion:
        gait = None
    r = WR.render_walk_gif(out_gif, walker=walker, terrain=terrain, gait=gait, motion=motion, **kw)
    return r["gif"]


def walk_physics(out_gif="out/walk_physics.gif", **kw):
    """go2 をトルク PD 制御＋mj_step の本物の物理(重力・接触・慣性)で衝突地形上を歩かせる。
    重心移動で胴体が pitch/roll しながら歩く様子を GIF＋テレメトリ図に(GPU 不要)。
    戻り値 dict(upright / forward_m / pitch_range_deg / roll_range_deg、実測値)。

    運動学プレビュー([[walk_gif]])と違い接触・慣性を解く=足は接地し、不安定なら転倒する。
    """
    import walk_physics as WP
    return WP.run_walk_physics(out_gif, **kw)


def jump_physics(out_gif="out/jump_physics.gif", **kw):
    """go2 をしゃがみ→爆発的伸展→弾道飛行(全足離地=接触0)→着地させる本物の物理ジャンプ。
    摩擦・重力・接触を mj_step で解く。GIF＋高さテレメトリ(GPU 不要)。
    戻り値 dict(jump_height_m / airtime_s / left_ground、実測値)。
    """
    import walk_physics as WP
    return WP.run_jump_physics(out_gif, **kw)


def pick_gif(out_gif="out/panda_pick.gif", **kw):
    """ロボットアームが実接触・摩擦でキューブを把持し別位置へ置く pick-and-place を
    headless GIF 化(GPU 不要)。戻り値 dict(lift_m / grasped / placed_z など、実測値)。

    グルーは一切使わず、把持成否は箱の実測高さで報告する(誇張なし)。
    """
    import pick_render as PR
    return PR.render_pick_gif(out_gif, **kw)


def sensor_fusion(out_png="out/sensor_fusion.png", **kw):
    """カメラ/GPS 相当の位置センサと IMU 相当の速度センサを Kalman フィルタで融合し、
    投射体を追跡した結果を図化(GPU 不要)。戻り値 dict(各手法の RMSE と fused_wins)。

    融合 RMSE は各センサ単体と正直に比較する — 勝てなければ fused_wins=False を返す。
    """
    import sensor_fusion as SF
    return SF.run_fusion_demo(out_png, **kw)


def bin_pick_gif(out_gif="out/bin_pick.gif", n_cubes=8, n_picks=3, **kw):
    """バラ積みされた部品を候補スコアリングで選び、6DoF IK で上面把持して bin から
    取り出す bin-picking を headless GIF 化(GPU 不要)。戻り値 dict(n_picked など、実測値)。

    グルー無し。成功数は「部品が実際に bin を出たか」で数える(誇張なし)。
    """
    import bin_pick as BP
    return BP.render_bin_pick_gif(out_gif, n_cubes=n_cubes, n_picks=n_picks, **kw)


def lidar_scan(out_png="out/lidar.png", **kw):
    """スピニング LIDAR を mj_ray の実レイキャストでシミュレートし点群を可視化
    (GPU 不要)。戻り値 dict(n_points / hit_ratio / mean_range_m、実測値)。
    """
    import lidar_sim as LS
    return LS.run_lidar_demo(out_png, **kw)


def focus_stack(out_png="out/focus_stack.png", **kw):
    """真値深度から被写界深度ボケの焦点スタックを合成し、局所シャープネス最大で全焦点画像に
    融合(焦点由来深度も復元、GPU 不要)。戻り値 dict(sharpness_gain / depth_focus_corr)。
    """
    import focus_stack as FS
    return FS.run_focus_stack_demo(out_png, **kw)


def event_camera(out_png="out/event_camera.png", **kw):
    """イベントカメラ(DVS)を対数輝度変化モデルで模倣し ON/OFF イベント列を生成
    (GPU 不要)。戻り値 dict(n_events / edge_corr、動くエッジ発火を実測)。
    """
    import event_camera as EC
    return EC.run_event_demo(out_png, **kw)


def stereo_depth(out_png="out/stereo.png", **kw):
    """平行2カメラのステレオペアを描画し、ブロックマッチング(既存 stereo.py)で深度推定して
    真値深度と誤差比較(GPU 不要)。戻り値 dict(depth_corr / median_err_m、実測値)。
    """
    import stereo_sim as SS
    return SS.run_stereo_demo(out_png, **kw)


def polarization(out_png="out/polarization.png", **kw):
    """偏光カメラを Fresnel 順モデルで模倣し DoLP/AoLP を可視化(GPU 不要)。無テクスチャ・
    鏡面・透過面でも表面方位を偏光が符号化することを示す。戻り値 dict(mean_dolp など)。
    """
    import polar_cam as PC
    return PC.run_polar_demo(out_png, **kw)
