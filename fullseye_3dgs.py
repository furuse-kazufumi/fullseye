#!/usr/bin/env python
"""Fullseye 3DGS ―― sim シーンを1コマンドで3D Gaussian Splatting化。

  python fullseye_3dgs.py go2                 # builtin シーンを3DGS化
  python fullseye_3dgs.py scene.xml           # 任意のMJCFを3DGS化
  python fullseye_3dgs.py go2 --quality high  # 品質プリセット(fast/balanced/high)
  python fullseye_3dgs.py --list              # 使えるシーン一覧
  python fullseye_3dgs.py go2 --open          # 完了後に全周GIFを自動で開く

backend は自動: ネイティブ gsplat(高速・高精細)が使えればそれ、無ければ純PyTorch。
CUDA 環境(.gsplat-cuda)も自動で設定するので、vcvars 等を意識する必要はありません。
"""
from __future__ import annotations
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

BUILTIN = {
    "go2":     ("C:/dev/projects/mujoco_menagerie/unitree_go2/scene.xml", (0, 0, 0.18), 1.3, 22),
    "cassie":  ("C:/dev/projects/mujoco_menagerie/agility_cassie/scene.xml", (0, 0, 0.6), 2.2, 18),
    "apollo":  ("C:/dev/projects/mujoco_menagerie/apptronik_apollo/scene.xml", (0, 0, 0.8), 2.6, 15),
    "anymal":  ("C:/dev/projects/mujoco_menagerie/anybotics_anymal_c/scene.xml", (0, 0, 0.4), 1.8, 20),
    "spot":    ("C:/dev/projects/mujoco_menagerie/boston_dynamics_spot/scene.xml", (0, 0, 0.4), 1.8, 20),
}

PRESETS = {   # name: (res, n_gauss, iters, n_views)
    "fast":     (128, 8000, 600, 24),
    "balanced": (256, 20000, 1000, 36),
    "high":     (384, 45000, 1500, 48),
}


def _find_cl_dir():
    """MSVC cl.exe(Hostx64/x64)のディレクトリを探す(バージョンは自動)。無ければ None。"""
    import glob
    bases = [
        r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC",
        r"C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC",
        r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC",
    ]
    for base in bases:
        hits = sorted(glob.glob(os.path.join(base, "*", "bin", "Hostx64", "x64", "cl.exe")))
        if hits:
            return os.path.dirname(hits[-1])           # 最新バージョン
    return None


def setup_cuda_env(root: str = ROOT) -> bool:
    """永続 CUDA 12.8(.gsplat-cuda)を in-process で有効化。あれば True。"""
    lib = os.path.join(root, ".gsplat-cuda", "Library")
    if not os.path.isdir(lib):
        return False
    os.environ["CUDA_PATH"] = lib
    os.environ["CUDA_HOME"] = lib
    os.environ["TORCH_EXTENSIONS_DIR"] = os.path.join(root, ".gsplat-build")
    os.environ.setdefault("MAX_JOBS", "8")
    scripts = os.path.join(root, ".venv-gsplat", "Scripts")   # ninja.exe(検証用)
    if os.path.isdir(scripts):
        os.environ["PATH"] = scripts + os.pathsep + os.environ.get("PATH", "")
    # torch は cached build でも ninja 生成時に `where cl` を実行するため、cl.exe の
    # ディレクトリを PATH に通す(実コンパイルはしない=up-to-date なら no-op)。
    cl_dir = _find_cl_dir()
    if cl_dir:
        os.environ["PATH"] = cl_dir + os.pathsep + os.environ.get("PATH", "")
    for sub in ("bin", "nvvm/bin"):
        p = os.path.join(lib, *sub.split("/"))
        if os.path.isdir(p):
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
            try:
                os.add_dll_directory(p)
            except (OSError, AttributeError):
                pass
    return True


def native_available() -> bool:
    """ネイティブ gsplat が実際にラスタライズできるか(cached build のロード確認)。"""
    try:
        import torch
        import gsplat
        if not torch.cuda.is_available():
            return False
        N = 8
        d = "cuda"
        m = torch.zeros(N, 3, device=d)
        q = torch.zeros(N, 4, device=d); q[:, 0] = 1
        s = torch.full((N, 3), 0.05, device=d)
        o = torch.full((N,), 0.5, device=d)
        c = torch.rand(N, 3, device=d)
        vm = torch.eye(4, device=d)[None]; vm[0, 2, 3] = 3
        K = torch.tensor([[[100., 0, 32], [0, 100., 32], [0, 0, 1]]], device=d)
        gsplat.rasterization(m, q, s, o, c, vm, K, 64, 64)
        return True
    except Exception:
        return False


_DEMO_XML = (
    '<mujoco><worldbody><light pos="0 0 3" dir="0 0 -1"/>'
    '<geom name="floor" type="box" size="1 1 .02" pos="0 0 0" rgba=".4 .45 .5 1"/>'
    '<geom type="sphere" size=".18" pos=".25 0 .25" rgba=".85 .2 .2 1"/>'
    '<geom type="box" size=".12 .12 .12" pos="-.2 .2 .18" rgba=".2 .7 .3 1"/>'
    '<geom type="capsule" size=".08 .12" pos="-.15 -.2 .2" rgba=".25 .35 .85 1"/>'
    '</worldbody></mujoco>')


def _demo_scene_path():
    """合成デモシーン(外部アセット不要)を temp .xml に書き出しパスを返す。"""
    import tempfile
    p = os.path.join(tempfile.gettempdir(), "fullseye_3dgs_demo.xml")
    if not os.path.isfile(p):
        with open(p, "w", encoding="utf-8") as f:
            f.write(_DEMO_XML)
    return p


def resolve_scene(name: str):
    if name == "demo":
        return (_demo_scene_path(), (0, 0, 0.2), 1.3, 25)   # 外部アセット不要
    if name in BUILTIN:
        return BUILTIN[name]
    if os.path.isfile(name) and name.endswith(".xml"):
        return (name, (0, 0, 0.3), 2.0, 20)      # 汎用デフォルト
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Fullseye 3DGS ― sim シーンを1コマンドで3D Gaussian Splatting化",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("scene", nargs="?", help="builtin名(go2/cassie/apollo/anymal/spot) か .xml パス")
    ap.add_argument("--quality", choices=list(PRESETS), default="balanced", help="既定 balanced")
    ap.add_argument("--backend", choices=["auto", "gsplat", "torch"], default="auto")
    ap.add_argument("--out", default=None, help="出力先(既定: out/3dgs_<scene>)")
    ap.add_argument("--open", action="store_true", help="完了後に全周GIFを開く")
    ap.add_argument("--densify", action="store_true",
                    help="native時: 学習中にガウシアンを増やす(細部↑、floater増の可能性・実験的)")
    ap.add_argument("--motion", action="store_true",
                    help="native時: 静止でなく『動く3DGS』を生成(body リグ+サイン波モーション→motion.gif)")
    ap.add_argument("--frames", type=int, default=60, help="--motion のフレーム数(サイン波時)")
    ap.add_argument("--motion-file", default=None,
                    help="--motion時: 実際の qpos 軌道 .npy (F,nq) を再生(歩行など)")
    ap.add_argument("--list", action="store_true", help="使えるシーン一覧")
    a = ap.parse_args(argv)

    if a.list or not a.scene:
        print("Fullseye 3DGS ― 使えるシーン:")
        for k, (p, *_ ) in BUILTIN.items():
            ok = "○" if os.path.isfile(p) else "×(未配置)"
            print(f"  {k:8s} {ok}  {p}")
        print("  <path.xml>  任意のMJCFファイル")
        print("\n品質プリセット:", ", ".join(f"{k}({v[0]}px/{v[1]}gauss)" for k, v in PRESETS.items()))
        print("例:  python fullseye_3dgs.py go2 --quality high --open")
        return 0

    scene = resolve_scene(a.scene)
    if scene is None:
        print(f"[エラー] シーン '{a.scene}' が見つかりません。--list で一覧を確認してください。")
        return 2
    path, lookat, radius, elev = scene
    if not os.path.isfile(path):
        print(f"[エラー] MJCF が存在しません: {path}")
        return 2

    res, n_gauss, iters, n_views = PRESETS[a.quality]
    out = a.out or os.path.join(ROOT, "out", f"3dgs_{os.path.splitext(os.path.basename(a.scene))[0]}")

    # backend 決定
    have_env = setup_cuda_env()
    if a.backend == "auto":
        backend = "gsplat" if (have_env and native_available()) else "torch"
    else:
        backend = a.backend
        if backend == "gsplat" and not have_env:
            print("[警告] .gsplat-cuda が無いため native を使えません。torch にフォールバックします。")
            backend = "torch"

    print(f"■ Fullseye 3DGS")
    print(f"  シーン   : {a.scene}  ({path})")
    print(f"  品質     : {a.quality}  ({res}px / {n_gauss} gaussians / {iters} iters / {n_views} views)")
    print(f"  backend  : {backend}   {'(ネイティブCUDA=高速)' if backend=='gsplat' else '(純PyTorch)'}")
    print(f"  出力先   : {out}")
    print("  学習中 …")

    if backend == "gsplat" and a.motion:
        import gsplat_animate as AM
        print("   (motion: body リグ付け→サイン波モーションで『動く3DGS』を生成します)")
        r = AM.animate(path, out, n_views=n_views, iters=max(800, iters), res=res, radius=radius,
                       elevation_deg=elev, lookat=lookat, n_gauss=max(15000, n_gauss),
                       n_frames=a.frames, motion_file=getattr(a, "motion_file", None),
                       log=lambda m: print("   " + m, flush=True))
        gif = os.path.join(out, "motion.gif")
        print(f"\n✓ 完了: 動く3DGS {r['frames']}フレーム / {r['n']}ガウシアン")
        print(f"  motion GIF: {gif}")
        if a.open and os.path.isfile(gif):
            try:
                os.startfile(gif)
            except Exception:
                pass
        return 0
    if backend != "gsplat" and a.motion:
        print("[警告] --motion は native gsplat 専用です。静止3DGSに切り替えます。")

    if backend == "gsplat":
        import gsplat_train_native as N
        if a.densify:
            print("   (densify: 学習中にガウシアンを増やして細部を上げます)")
            r = N.train_densify(path, out, n_views=n_views, iters=max(iters, 1200), res=res,
                                radius=radius, elevation_deg=elev, lookat=lookat,
                                n_gauss_init=max(4000, n_gauss // 3),
                                log=lambda m: print("   " + m, flush=True))
        else:
            r = N.train(path, out, n_views=n_views, iters=iters, res=res, radius=radius,
                        elevation_deg=elev, lookat=lookat, n_gauss=n_gauss,
                        log=lambda m: print("   " + m, flush=True))
    else:
        import gsplat_cli as C
        r = C.run(path, out, n_views=n_views, iters=iters, width=res, height=res,
                  radius=radius, elevation_deg=elev, lookat=lookat,
                  log=lambda m: print("   " + m, flush=True))

    gif = os.path.join(out, "turntable.gif")
    ply = os.path.join(out, "gaussians.ply")
    print(f"\n✓ 完了: hold-out PSNR ≈ {r.get('test_psnr', r.get('best_test_psnr', 0)):.2f} dB")
    print(f"  全周GIF : {gif}")
    print(f"  新規視点: {os.path.join(out, 'novelview.png')}")
    if backend == "gsplat" and os.path.isfile(ply):
        print(f"  3DGS ply: {ply}  (SuperSplat 等の Web ビューアで開けます)")
    if a.open and os.path.isfile(gif):
        try:
            os.startfile(gif)  # Windows 既定ビューア
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
