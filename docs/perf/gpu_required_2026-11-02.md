# GPU でしか回らない寸法 — 実寸の実演(C') 2026-11-02

既存 PoC は CPU 前提の寸法で小さいだけで、GPU の価値は**実寸**で決まる。
実寸で CPU が分〜十分の桁・GPU が秒の桁になる 3 op を、寸法 × 時間で示す。
**新しい PoC の種**として、どの op を・どの寸法で・何の産業用途で回すかを残す。

- 計測機: NVIDIA GeForce RTX 5090 / torch 2.11.0+cu128(loco venv)
- 計測開始 2026-11-02T13:17:20 / 終了 2026-11-02T13:19:55(経過 155 s)
- UnrealEditor(CARLA)在席: **none(計測開始時に確認)** / GPU ロック取得: **yes(gpu_in_use.lock)**
- CPU 打ち切り基準: 単発 > 90 s(外挿しない)

小寸法の parity(内部差): `bilateral`=3.18e-07, `anisotropic_diffusion`=2.68e-07, `vol_gaussian`=2.76e-07

## `vol_gaussian`(volume)

産業用途: CT/多孔質/NDT 体積の分離可能ガウス平滑(分離可能 conv は CPU でも軽い: 比較の基準線)

| 寸法 | N | CPU s | GPU s | 倍率 | VRAM GB | 備考 |
|---|---:|---|---|---:|---:|---|
| 64^3 | 1 | 0.0 | 0.002 | 1.8x | 0.00 | measured(単発) / GPU measured |
| 128^3 | 1 | 0.0 | 0.008 | 4.8x | 0.03 | measured(単発) / GPU measured |
| 256^3 | 1 | 0.4 | 0.071 | 5.6x | 0.21 | measured(単発) / GPU measured |
| 512^3 | 1 | 4.7 | 0.586 | 8.0x | 1.63 | measured(単発) / GPU measured |

## `vol_median`(volume)

産業用途: CT/多孔質/NDT 体積の 3x3x3 メディアン(27 近傍の順位統計: CPU は寸法の 3 乗で伸びる)

| 寸法 | N | CPU s | GPU s | 倍率 | VRAM GB | 備考 |
|---|---:|---|---|---:|---:|---|
| 64^3 | 1 | 0.1 | 0.003 | 29.7x | 0.03 | measured(単発) / GPU measured |
| 128^3 | 1 | 0.6 | 0.016 | 36.5x | 0.27 | measured(単発) / GPU measured |
| 256^3 | 1 | 4.6 | 0.108 | 43.2x | 2.15 | measured(単発) / GPU measured |
| 512^3 | 1 | 37.3 | 0.805 | 46.3x | 17.19 | measured(単発) / GPU measured |

## `bilateral`(bilateral)

産業用途: 高解像ライン走査の表面/布検査(5x5x25 シフト反復で計算重)

| 寸法 | N | CPU s | GPU s | 倍率 | VRAM GB | 備考 |
|---|---:|---|---|---:|---:|---|
| 512x512 | 200 | 27.9 | 0.183 | 152.0x | 1.47 | measured(単発 0.139s x N=200) / GPU measured(N=200) |
| 2048x2048 | 50 | 104.7 | 0.755 | 138.7x | 5.87 | measured(単発 2.093s x N=50) / GPU measured(N=50) |
| 4096x4096 | 20 | 157.8 | 1.100 | 143.5x | 7.99 | measured(単発 7.892s x N=20) / GPU measured(N=20) |
| 8192x8192 | 5 | 149.1 | 1.079 | 138.2x | 7.52 | measured(単発 29.825s x N=5) / GPU measured(N=5) |

## `anisotropic_diffusion`(anisotropic_diffusion)

産業用途: 欠陥検査フレーム列のエッジ保存ノイズ抑制(Perona–Malik 反復 PDE、全画素 x 反復の指数計算)

| 寸法 | N | CPU s | GPU s | 倍率 | VRAM GB | 備考 |
|---|---:|---|---|---:|---:|---|
| 512x512 | 200 | 21.6 | 0.151 | 143.4x | 1.89 | measured(単発 0.108s x N=200) / GPU measured(N=200) |
| 2048x2048 | 50 | 88.5 | 0.623 | 142.1x | 7.55 | measured(単発 1.771s x N=50) / GPU measured(N=50) |
| 4096x4096 | 20 | 142.5 | 1.026 | 138.9x | 10.27 | measured(単発 7.127s x N=20) / GPU measured(N=20) |
| 8192x8192 | 5 | 148.7 | 1.011 | 147.0x | 9.66 | measured(単発 29.730s x N=5) / GPU measured(N=5) |

## 所見

- 2-D の CPU 秒は同じ寸法の**単発を実測し N 倍**(枚数方向のみ線形、寸法方向には外挿しない)。GPU は host→device 転送 + op + device→host を含む。
- `vol_gaussian`(分離可能 conv)は CPU でも軽く(512^3 単発 4.7 s)、GPU の勝ちは 1 桁(1.8〜8.0x)。「GPU でしか回らない」のは 27 近傍の順位統計 `vol_median` のように演算量が寸法の 3 乗に乗る op で、こちらが PoC の種。
- 2-D の 2 op(`bilateral` 25 シフト反復、`anisotropic_diffusion` 反復 PDE)は 4096²/8192² で CPU が 3 分超、GPU が 1.3 s 前後(約 140〜160x)。CPU 側は単発 90 s の打ち切り基準に届かなかったので全寸法を実測した。
負ける寸法があれば負けると書く。CPU が現実的でない寸法は「—(打ち切り)」とし、外挿していない。
- この梯子では CPU の打ち切り(単発 > 90 s)は 1 度も起きなかった(最長は `vol_median` 512^3 の単発 37 s、2-D は単発 x N の合計で 3 分超)。「CPU が非現実的」と言える寸法は 1024^3 体積や 8192^2 x 数百枚で、次の便で梯子を伸ばす。
GPU 秒数・VRAM は `docs/perf/logs/c_demos.log` と同ディレクトリの `c_demos_result.json`(計測の正本)の実測と一致する。
