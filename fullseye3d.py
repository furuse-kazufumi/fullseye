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
        # load by PATH, not by text: menagerie scenes are <include>-based with relative
        # assets, and from_xml_string cannot resolve either (measured: go2 scene fails with
        # "Error opening file 'go2.xml'"). sim_source.MuJoCo accepts an .xml path directly.
        xml = self.spec["xml"]
        mpath = R.motion(self.name, motion) if (motion or not gait) else None
        if mpath:
            qpos = np.load(mpath).astype(float)
        elif gait:
            import gaits as G
            import mujoco
            m = mujoco.MjModel.from_xml_path(xml)
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


def evis_rl_perceive(qpos_npy, xml="C:/dev/projects/ms_human_700_jaw/scene_full_mjx.xml",
                     out_gif="out/evis_fullseye.gif", **kw):
    """Fullseye leverages the GPU-learned evis: take its physics rollout (a qpos trajectory
    from the MJX-PPO policy) and PERCEIVE it with Fullseye's unified vision — RGB, metric
    depth, and DVS events side by side. The control is learned on the GPU; the *seeing* is
    Fullseye's job. Returns honest perception stats. See ``evis_fullseye_bridge``."""
    import evis_fullseye_bridge as B
    return B.perceive_evis_walk(qpos_npy, xml, out_gif=out_gif, **kw)


def robot_pov(qpos_npy, xml, ego_body="torso_link", out_gif="out/robot_pov.gif", **kw):
    """ロボット視点の知覚を1行で: 頭部搭載カメラの RGB|深度|DVS(+三人称)4面 GIF。
    ``ego_body`` にセンサを載せる body 名(G1="torso_link", evis="pelvis" 等)。"""
    import evis_fullseye_bridge as B
    return B.perceive_evis_walk(qpos_npy, xml, out_gif=out_gif, ego_body=ego_body, **kw)


def g1_real_sensors(qpos_npy, xml="C:/dev/projects/mujoco_menagerie/unitree_g1/scene.xml",
                    out_gif="out/g1_real_sensors.gif", obstacles=True, **kw):
    """G1 実機センサ仕様の知覚を1行で: Livox Mid-360 BEV 点群 + RealSense D435i RGB/深度。
    仕様・取付位置は実測ベース(詳細 ``evis_fullseye_bridge.perceive_g1_real``)。"""
    import evis_fullseye_bridge as B
    return B.perceive_g1_real(qpos_npy, xml, out_gif=out_gif, obstacles=obstacles, **kw)


def pseudo_lidar(p_xy, yaw, obstacles, **kw):
    """歩行方策 G1VisionWalk が観測として食べるものと同一ジオメトリの平面疑似 LiDAR を
    単体計算(前方弧 K 本の正規化距離)。知覚と制御が同じ真実を共有するための toolkit 入口。"""
    import evis_fullseye_bridge as B
    return B.pseudo_lidar_rays(p_xy, yaw, obstacles, **kw)


def g1_walk_policy(params_pkl, ref_npy=None, **kw):
    """GPU 学習済み G1 歩行方策(brax ckpt)を Windows だけで実行する 1 行入口: numpy 推論
    (brax と数値一致を検証済み)+ネイティブ MuJoCo で歩かせ、距離/生存/横ずれ RMS を実測し
    追従カメラ動画を書き出す。vision=True で疑似 LiDAR+障害物版。段階 API は
    ``g1_policy_bridge.G1PolicySession``(load→reset→step→run→render を個別に呼べる)。"""
    import g1_policy_bridge as G
    if ref_npy is None:
        return G.g1_walk_policy(params_pkl, **kw)
    return G.g1_walk_policy(params_pkl, ref_npy, **kw)


def g1_training_curves(log_path):
    """G1 学習ログの進捗行を配列辞書に(step/reward/ep_len/perr/crash…)— GPU 機に触れず
    Studio 側で学習曲線をプロットするための toolkit 入口。"""
    import g1_policy_bridge as G
    return G.training_curves(log_path)


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


def hurdle_physics(out_gif="out/hurdle_physics.gif", **kw):
    """go2 が助走→爆発跳躍で障害物(バリア)を越え向こう側へ着地する本物の物理の走幅跳。
    摩擦・重力・接触を mj_step で解く。GIF＋軌道テレメトリ(GPU 不要)。
    戻り値 dict(cleared / success / final_x / peak_z、実測値)。
    """
    import walk_physics as WP
    return WP.run_hurdle_physics(out_gif, **kw)


def long_route(out_gif="out/long_route.gif", **kw):
    """go2 が粗さの変化する長い起伏地形を本物の物理で長距離(既定100m)歩き切る(GPU 不要)。
    戻り値 dict(distance_m / reached_target / upright / speed_mps、実測値)。"""
    import walk_physics as WP
    return WP.run_long_route(out_gif, **kw)


def route_planning(out_gif="out/route_planning.gif", **kw):
    """障害物をレイキャストで先読みし、候補方位をピラミッド探索(粗→細)で選んで差動旋回で回避し
    ゴール到達する本物の物理ナビ(俯瞰プラン付き、GPU 不要)。戻り値 dict(reached_goal など)。"""
    import walk_physics as WP
    return WP.run_route_planning(out_gif, **kw)


def figure8(out_gif="out/figure8.gif", **kw):
    """差動旋回で 8 の字系の曲線を各サイズで描く旋回制御の練習/較正(GPU 不要)。"""
    import walk_physics as WP
    return WP.run_figure8(out_gif, **kw)


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
