"""G1 歩行方策の実行サンプル — GPU/WSL 不要で「学習済みチェックポイントを歩かせる」。

Fullseye の方策実行には 2 つの入口がある(知覚サンプル perception_staged.py と同じ二層):

  1. **1 行ファサード** (``fullseye3d.g1_walk_policy(ckpt)``)
     「この ckpt を歩かせて動画と実測をくれ」という用途。中身は隠蔽。
  2. **G1PolicySession** (このサンプル)
     load → reset → step を 1 段ずつ呼ぶ。制御ループの中にユーザー自身の
     if/for を挟めるので、「転びそうになったら記録する」「レイ最小距離が
     縮んだら減速判定を観察する」のような実験がそのまま書ける。

仕組み(正直な内訳):
  * 方策 = brax PPO の 4×32 swish MLP + 観測正規化。ここでは **純 numpy** で
    再実装しており、brax 純正推論との数値一致(max 誤差 1.8e-7)を検証済み。
  * 物理 = ネイティブ MuJoCo。学習側(MJX)と同じ「足+床のみ衝突」「solver 6 回」
    に揃えてあるが、MJX とネイティブは同一ではない — 数字は「この物理での実測」。
  * 制御 = mocap 参照への残差: ctrl = clip(ref[i] + 0.4 * action)。

実行(チェックポイントと参照モーションがあること):

    py -3.11 examples/g1_policy_staged.py

拡張ポイントは EXTEND コメントで明示している。

外部アセット要件 / External asset requirement:
  このサンプルはリポジトリに同梱されていない外部アセットを **3 つ**必要とする:
  RL 学習済みチェックポイント .pkl / 参照モーション .npy / MuJoCo Menagerie の
  G1 シーン ``unitree_g1/scene.xml``。前 2 つは ``FULLSEYE_G1_ASSETS_DIR`` に
  両方を含むディレクトリを、シーンは ``FULLSEYE_G1_SCENE_XML`` にファイルを指定する
  (下の CKPT / REF / SCENE_XML を直接書いてもよい)。
  This example requires three external assets not bundled with this repo: an
  RL-trained checkpoint (.pkl), a reference motion (.npy), and the MuJoCo
  Menagerie G1 scene (``unitree_g1/scene.xml``). Point
  ``FULLSEYE_G1_ASSETS_DIR`` at a directory containing the first two and
  ``FULLSEYE_G1_SCENE_XML`` at the scene file.
"""
from __future__ import annotations

import os
import sys

# examples/ から親ディレクトリの Fullseye モジュールを使う定型
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from g1_policy_bridge import G1PolicySession  # noqa: E402

# ---------------------------------------------------------------------------
# 設定 — EXTEND: 別のチェックポイント/参照モーションを試すならここ
# ---------------------------------------------------------------------------
OUT_HUM = os.environ.get("FULLSEYE_G1_ASSETS_DIR")        # directory containing ckpt + ref motion
CKPT = os.path.join(OUT_HUM, "mjx_g1_walk12c_ckpt_15728640.pkl") if OUT_HUM else None  # 直進歩行(操舵観測つき)
REF = os.path.join(OUT_HUM, "g1_walk_cycle_straight.npy") if OUT_HUM else None         # 直進化した LAFAN1 歩行 1 周期
# EXTEND: MuJoCo Menagerie の G1 シーン。配布物にローカルパスを焼き込まない方針なので
# (2026-09-05 に出荷 7 ファイルから除去)、環境変数が唯一の既定になっている。
SCENE_XML = os.environ.get("FULLSEYE_G1_SCENE_XML", "")
SECS = 8.0                                                # 最大ロールアウト秒数

# EXTEND: 疑似 LiDAR+障害物版を試すなら vision 系 ckpt(walk13c 系)に替えて
# vision=True にする。obs 次元が合わない組合せはロード時に明示エラーで拒否される。
VISION = False

# 足りない物は**まとめて 1 度に**言う。2 つ直してから 3 つ目で落ちるのは案内として
# 不親切で、実際 2026-09-06 にシーン XML だけが抜けた状態で ValueError になった。
_missing = [label for label, path in (
    ("RL checkpoint (.pkl)", CKPT),
    ("reference motion (.npy)", REF),
    ("MuJoCo Menagerie scene unitree_g1/scene.xml", SCENE_XML),
) if not path or not os.path.exists(path)]
if _missing:
    raise SystemExit(
        "This staged example requires external assets not included in this repo.\n"
        "Missing:\n  - " + "\n  - ".join(_missing) + "\n"
        "Set FULLSEYE_G1_ASSETS_DIR to a directory holding the checkpoint and the "
        "reference motion, and FULLSEYE_G1_SCENE_XML to the scene file (or edit "
        "CKPT / REF / SCENE_XML in this script directly).\n"
        f"CKPT={CKPT}\nREF={REF}\nSCENE_XML={SCENE_XML}"
    )

# ---------------------------------------------------------------------------
# 1) ロード — ckpt(numpy 化)と参照モーション(制御 dt へ再サンプル)を 1 回だけ準備
# ---------------------------------------------------------------------------
s = G1PolicySession(CKPT, REF, xml=SCENE_XML, vision=VISION)
print(f"policy obs={s.pol['obs_size']} act={s.pol['act_size']} "
      f"ref={s.ref_n} frames @ dt={s.dt:.3f}s")

# ---------------------------------------------------------------------------
# 2) 段階実行 — reset して 1 制御ステップずつ回す。ループの中は自由に書ける。
#    (「答えだけ欲しい」なら s.run(secs=8) の 1 行で同じことができる)
# ---------------------------------------------------------------------------
obs = s.reset(start_frame=0)          # EXTEND: 別の位相から始めるなら start_frame
n_steps = int(SECS / s.dt)
worst_tilt = 0.0                      # 例: ロール/ピッチの最悪値を観察してみる

for k in range(n_steps):
    obs, done, info = s.step(obs)

    # EXTEND: ここが「条件分岐しながら」の場所。観測やシミュ状態を見て
    # 好きな計測・介入・記録を挟む。例として傾きの最悪値を追う:
    up_z = float(obs[5])              # obs[3:6] = 体幹系の重力方向(直立で z≈-1)
    worst_tilt = max(worst_tilt, 1.0 + up_z)

    if done:
        # info には学習と同じ終了理由が入る(fallen/deviated/offline/crashed)
        print(f"episode ended at {k * s.dt:.2f}s: "
              + ", ".join(r for r, v in info.items() if v))
        break

# ---------------------------------------------------------------------------
# 3) 実測 — 報酬ではなく「定規で測れる量」で言う(距離・生存・横ずれ)
# ---------------------------------------------------------------------------
import numpy as np  # noqa: E402

qp = np.stack(s.qpos_hist)
print(f"steps={len(qp) - 1}  forward={qp[-1, 0] - qp[0, 0]:.2f} m  "
      f"worst_tilt={worst_tilt:.3f}")

# ---------------------------------------------------------------------------
# 4) 成果物 — qpos 軌道(全知覚 op の入力になる)と追従カメラ動画
# ---------------------------------------------------------------------------
qpos_path = s.save_qpos("out/g1_policy_staged_qpos.npy")
video = s.render("out/g1_policy_staged.mp4")
print("saved:", qpos_path, "and", video)

# EXTEND: この qpos npy はそのまま知覚系サンプルに渡せる —
#   fullseye3d.g1_real_sensors(qpos_path)   # Mid-360 BEV + D435i の実機センサ視点
#   fullseye3d.robot_pov(qpos_path, XML)    # 頭部搭載 RGB/深度/DVS のロボット視点
# 「歩かせる」(この サンプル)と「見る」(perception_staged.py)が同じ軌道を共有する。
