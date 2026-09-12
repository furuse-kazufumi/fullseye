<!-- i18n-source-sha: 37bc63784e56 -->
# Fullseye 3DGS —— 使用方法（一行指令）

[日本語](./3DGS_USAGE.md) · [English](./3DGS_USAGE.en.md) · [简体中文](./3DGS_USAGE.zh.md) · **繁體中文** · [한국어](./3DGS_USAGE.ko.md) · [Deutsch](./3DGS_USAGE.de.md)

把 MuJoCo 的模擬場景轉換成 **3D Gaussian Splatting**，產生可以全方位旋轉觀看的 GIF 以及新視角影像。相機姿態使用模擬的真值，因此**不需要 COLMAP**。

## 最簡單的用法

在 imgevolve 資料夾中：

```bat
3dgs go2 --open
```

只要這一條指令，就會把 go2（四足機器人）轉換成 3DGS，並自動開啟完成的全方位 GIF。

- 更換場景：`3dgs cassie` / `3dgs apollo` / `3dgs anymal` / `3dgs spot`
- 使用自己的 MJCF：`3dgs <本機工作路徑>\path\to\scene.xml`
- 檢視清單：`3dgs --list`

## 品質預設

```bat
3dgs go2 --quality fast       :: 128px / 8 千個高斯(數秒完成,適合預覽)
3dgs go2 --quality balanced   :: 256px / 2 萬個高斯(預設)
3dgs go2 --quality high       :: 384px / 4.5 萬個高斯(最精細)
```

## 更精緻(densify)

```bat
3dgs go2 --quality high --densify --open
```

加上 `--densify` 後，訓練過程中會**自動增加高斯數量以提升細節**（僅限 native gsplat）。以 go2 為例，會從約 8 千個成長到約 5 萬個，機身與腿部會更加平滑。通常幾秒到十幾秒即可完成。

## backend 自動選擇

- 若可使用 **native gsplat**（tile CUDA），會自動採用（速度快、精細度高，可達每秒數百 it）
- 若無法使用，會自動回退為**純 PyTorch**（較慢，但能運作）
- 也可透過 `--backend torch` / `--backend gsplat` 明確指定

環境（CUDA / 編譯器）由 launcher 自動設定，不必在意 vcvars 之類的設定。

## 從 Studio 使用

啟動 `spikes/studio_app.py` → 在「以 3D 檢視模擬模型 / 轉換為 3DGS」面板中，選擇場景名稱（點選標籤或直接輸入）與品質，按下「3DGS 訓練 🎇」→ 完成後會開啟全方位 GIF。

## 輸出

在 `out/3dgs_<scene>/`（或 `--out` 指定的目錄）下會產生：
- `turntable.gif` … 全方位預覽
- `novelview.png` … 左 = 真值 / 右 = 新視角渲染
- `gaussians.npz` … 訓練完成的高斯(npz)
- `gaussians.ply` … 標準 3DGS .ply 格式(native 模式下)。可**拖放到 SuperSplat 等網頁檢視器**中開啟
- `report.json` … PSNR 等指標

## 必要環境

- 用於 GPU 訓練的 venv `.venv-gsplat`（torch cu128）
- 若要使用 native，需要 `.gsplat-cuda`（CUDA 12.8）+ VS BuildTools 的 C++ 工具。詳情與重現步驟請見 `docs/GSPLAT_NATIVE_WINDOWS.md`

> 誠實說明：`--densify` 的效果依場景而異。像 go2 這樣的整塊結構會變得很乾淨，但像 cassie 這樣細長的雙足機器人，可能會對訓練視角過度配適，使得 hold-out 稍微變軟。建議先不加這個選項試試看，覺得不夠再加上。

## 播放動作(--motion)

```bat
3dgs go2 --motion --open
```

不再是靜止畫面，而是產生**運動中機器人的 3DGS**。原理如下：
1. 在標準姿勢下訓練 3DGS
2. 透過 **segmentation** 判定每個高斯來自 MuJoCo 的哪個 body（連桿）並完成綁定
3. 移動關節（預設 = 正弦波），用每一幀的 body 姿態（模擬真值）進行剛體蒙皮 → 重新算繪 → 產生 `motion.gif`

由於機器人是剛性連桿的集合，因此不需要完整的 4D-GS 就能自然運動。可透過 `--frames N` 變更幀數。

> 誠實說明：預設的動作是用於示範的正弦波（並非實際的行走策略）。由於模擬姿態是真值，不會發生結構性崩壞，但腳部附近可能出現輕微雜訊（初始化點的 body 歸屬邊界處）。

### 自動產生步態(gait)

```bat
3dgs go2 --motion --gait trot --open
```

`--gait trot` 會自動產生並播放**四足的 trot 步態**（對角腿同相位交替邁步）。會依關節名稱（FL/FR/RL/RR 或 LF/RF/LH/RH + thigh/calf）自動偵測腿部，因此適用於 go2 與 anymal。無法偵測的模型會回退為正弦波。若要使用實際行走策略的輸出，可用 `--motion-file traj.npy`（qpos 軌跡 (F,nq)）。
