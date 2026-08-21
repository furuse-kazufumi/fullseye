"""段階的知覚 API のサンプル — 「1 行ツールキット」と「条件分岐しながら段階的に」の対比。

Fullseye のロボット知覚には 2 つの入口がある:

  1. **1 行ファサード** (``fullseye3d.g1_real_sensors(...)`` など)
     「答え(GIF)をくれ」という用途。中で何が起きるかは隠蔽される。
  2. **PerceptionSession** (このサンプル)
     同じ機構を 1 オペレータずつ呼ぶ。ユーザー自身の if/for を段階の間に
     挟めるので、「安いセンサで見て、必要な時だけ高いセンサを使う」という
     実ロボットと同じ知覚戦略をそのまま書ける。

実行 (学習済みロールアウトがあること):

    py -3.11 examples/perception_staged.py

拡張ポイントは EXTEND コメントで明示している。自分のロボット/センサ/条件に
差し替えるときはそこだけ触ればよい。
"""
from __future__ import annotations

import os
import sys

import numpy as np

# examples/ から親ディレクトリの Fullseye モジュールを使う定型
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evis_fullseye_bridge import PerceptionSession  # noqa: E402

# ---------------------------------------------------------------------------
# 設定 — EXTEND: 対象ロボットを替えるならここ (qpos npy / シーン xml / センサ搭載 body)
# ---------------------------------------------------------------------------
QPOS = "C:/dev/projects/onocollo-complete/out/humanoid/g1_walk9_37M_qpos.npy"
XML = "C:/dev/projects/mujoco_menagerie/unitree_g1/scene.xml"
EGO_BODY = "torso_link"      # G1 は頭部が torso_link に剛結。evis なら "pelvis" など

# EXTEND: 障害物マップを替えるならここ。各行 [x, y, 半径]。
# (学習環境 G1VisionWalk はこれをエピソードごとにランダム生成している —
#  ここでは「地図として知っている障害物」を疑似 LiDAR に見せる、という設定)
OBSTACLES = np.array([
    [3.0, 0.4, 0.30],
    [5.0, -0.6, 0.30],
    [7.5, 0.2, 0.30],
])

# EXTEND: 知覚戦略のしきい値。近接判定(正規化距離 0..1)と DVS 発火数。
NEAR = 0.5                    # レイ最小値がこれ未満 = 「何かが 2m 以内」(0.5×射程4m)
EV_BUSY = 3000                # DVS イベント数がこれ超 = 「視界が大きく動いた」


def main() -> None:
    # ------------------------------------------------------------------
    # セッションを開く。この時点ではモデル読込と最初の順運動学だけで、
    # レンダラ(GL)はまだ作られない — 数値センサだけなら GL 不要のまま進む。
    # ------------------------------------------------------------------
    with PerceptionSession(QPOS, XML, ego_body=EGO_BODY) as ps:
        print(f"rollout: {len(ps)} frames, model nq={ps.qpos.shape[1]}")

        n_render = 0          # 高コスト段(描画)を実際に何回呼んだかの実測
        log = []              # あとで集計する知覚ログ

        # EXTEND: フレームの回り方を替えるならここ (逆再生・二分探索・特定区間だけ 等)
        for k in range(0, len(ps), 10):
            # ---- 段階 1: 姿勢を合わせる(順運動学のみ・ミリ秒) ----------------
            ps.seek(k)
            pose = ps.pose()  # {"x","y","z","yaw"} — 位置ベースの条件分岐に使える

            # ---- 段階 2: 安い数値センサから見る(GL 不要) --------------------
            # 疑似 LiDAR は学習方策 G1VisionWalk の観測と同一ジオメトリ。
            # 「方策が何を見て歩いているか」をそのまま外から覗ける。
            rays = ps.lidar(OBSTACLES)
            rec = {"k": k, "x": pose["x"], "ray_min": float(rays.min())}

            # ---- 段階 3: 条件を満たした時だけ高いセンサを使う ----------------
            # 実ロボットの省電力知覚と同じ発想:
            #   遠い → 数値センサだけで十分 / 近い → 画像・イベントも撮る
            if rays.min() < NEAR:
                # EXTEND: 発火時の追加センシングを替えるならここ
                # (ego_depth() で深度、mid360() で本物のレイキャスト点群も呼べる)
                ev_img, n_ev = ps.dvs()          # イベントカメラ(前回呼び出しとの差分)
                n_render += 1
                rec["dvs_events"] = n_ev
                if n_ev > EV_BUSY:
                    # 視界が大きく流れている = 移動中に障害物へ接近している状況。
                    # EXTEND: ここに「回避プランナを呼ぶ」「点群を保存する」等を接続
                    pts = ps.mid360()            # 実レイキャスト点群 (M,3)
                    rec["mid360_pts"] = int(len(pts))
            log.append(rec)

        # ------------------------------------------------------------------
        # 集計 — 「何を・いつ・どれだけ見たか」を正直に出す。
        # 高コスト段を全フレームの一部でしか呼んでいないことが数字で分かる。
        # ------------------------------------------------------------------
        near_frames = [r for r in log if r["ray_min"] < NEAR]
        print(f"frames scanned      : {len(log)} (stride 10)")
        print(f"near events (<{NEAR}) : {len(near_frames)}")
        print(f"renders actually run: {n_render}  <- 条件分岐で描画を節約した実数")
        for r in near_frames[:5]:
            print("  ", r)


if __name__ == "__main__":
    main()
