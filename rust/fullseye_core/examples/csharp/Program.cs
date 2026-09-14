// fullseye_abi.h を C# から直接叩く見本。**バインディング層は無い。**
//
// 8x8 の市松模様を閾値処理して連結成分を数える。契約は 8 連結なので答えは 1 個
// (4 連結だと 32 個になる —— 同じ op が backend で 4/8 に分かれていた実際のバグの探針)。
using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;

static class Fs
{
    const string L = "fullseye_core";

    // ★fs_dtype_t は契約の第 5 引数。ここが抜けていた(2026-09-14)——
    //   ヘッダは 8 引数、実装と 3 つの FFI 宣言は 7 引数で、**C ABI がずれたまま**
    //   どのテストも通っていた。FFI で宣言を書き写す言語どうしを突き合わせても、
    //   全員が同じ写し間違いをしていれば一致してしまう。
    internal const int FS_DTYPE_F64 = 4;

    [DllImport(L)] internal static extern int fs_image_create(
        double[] pixels, int height, int width, long rowStrideBytes,
        int dtype, double rangeLo, double rangeHi, out IntPtr img);
    [DllImport(L)] internal static extern int fs_image_dtype(IntPtr img, out int dtype);
    [DllImport(L)] internal static extern int fs_threshold(
        IntPtr img, double lo, double hi, out IntPtr reg);
    [DllImport(L)] internal static extern int fs_region_area(IntPtr reg, out long area);
    [DllImport(L)] internal static extern int fs_region_run_count(IntPtr reg, out long n);
    [DllImport(L)] internal static extern int fs_connection(IntPtr reg, out IntPtr objs);
    [DllImport(L)] internal static extern int fs_objectset_count(IntPtr objs, out long n);
    [DllImport(L)] internal static extern int fs_abi_version(out int major, out int minor);
    [DllImport(L)] internal static extern void fs_image_release(IntPtr p);
    [DllImport(L)] internal static extern void fs_region_release(IntPtr p);
    [DllImport(L)] internal static extern void fs_objectset_release(IntPtr p);

    // cargo の出力先は NuGet の探索路に無いので、自分で教える。
    internal static void Locate()
    {
        NativeLibrary.SetDllImportResolver(Assembly.GetExecutingAssembly(), (name, asm, path) =>
        {
            if (name != L) return IntPtr.Zero;
            string name_os = OperatingSystem.IsWindows() ? "fullseye_core.dll"
                           : OperatingSystem.IsMacOS()   ? "libfullseye_core.dylib"
                                                         : "libfullseye_core.so";
            // examples/csharp/bin/<cfg>/<tfm>/ から ../../../../../target/release/
            var dir = AppContext.BaseDirectory;
            for (int i = 0; i < 8 && dir != null; i++)
            {
                var cand = Path.Combine(dir, "target", "release", name_os);
                if (File.Exists(cand)) return NativeLibrary.Load(cand);
                dir = Path.GetDirectoryName(dir.TrimEnd(Path.DirectorySeparatorChar));
            }
            throw new DllNotFoundException(
                "fullseye_core を見つけられない。`cargo build --release` を先に走らせること —— " +
                "**建たなかった**ことを「呼べない」と混ぜない。");
        });
    }
}

class Program
{
    // R-1: すべての関数が状態コードを返す。黙って代替値を使わない。
    static void Check(int st, string what)
    {
        if (st != 0) throw new Exception($"{what} が status {st} を返した");
    }

    static int Main()
    {
        Fs.Locate();
        Check(Fs.fs_abi_version(out int major, out int minor), "fs_abi_version");
        Console.WriteLine($"ABI {major}.{minor}");

        const int N = 8;
        var px = new double[N * N];
        for (int r = 0; r < N; r++)
            for (int c = 0; c < N; c++)
                px[r * N + c] = (r + c) % 2;          // 市松

        Check(Fs.fs_image_create(px, N, N, N * sizeof(double), Fs.FS_DTYPE_F64,
                                 0.0, 1.0, out var img), "fs_image_create");
        Check(Fs.fs_image_dtype(img, out int dt), "fs_image_dtype");
        Console.WriteLine($"dtype 読み返し: {dt}(FS_DTYPE_F64 = {Fs.FS_DTYPE_F64})");
        // lo/hi は 0..1 の相対値。画像が名乗る値域を通して解決される(R-3)。
        Check(Fs.fs_threshold(img, 0.5, 1.0, out var reg), "fs_threshold");
        Check(Fs.fs_region_area(reg, out long area), "fs_region_area");
        Check(Fs.fs_region_run_count(reg, out long runs), "fs_region_run_count");
        Check(Fs.fs_connection(reg, out var objs), "fs_connection");
        Check(Fs.fs_objectset_count(objs, out long n), "fs_objectset_count");

        Console.WriteLine($"面積 {area} / run {runs} / 物体 {n}");
        bool ok = area == 32 && n == 1;
        Console.WriteLine(ok
            ? "契約どおり: 8x8 の市松は 8 連結で 1 個"
            : $"★契約と違う: 物体 {n} 個(8 連結なら 1、4 連結なら 32)");

        // 逆さの区間は「空」ではなく**失敗**(R-1)。
        int bad = Fs.fs_threshold(img, 0.8, 0.2, out _);
        Console.WriteLine(bad != 0
            ? $"逆さの区間 lo>hi は status {bad} で拒まれた"
            : "★逆さの区間が通ってしまった");

        Fs.fs_objectset_release(objs);
        Fs.fs_region_release(reg);
        Fs.fs_image_release(img);
        return (ok && bad != 0) ? 0 : 1;
    }
}
