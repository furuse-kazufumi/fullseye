/* fullseye_abi.h を **#include して** 呼ぶ例。
 *
 * ★これが今まで 1 つも無かった。Python(ctypes)・C#(P/Invoke)・Lua(FFI)は
 *   どれも**宣言を書き写す**ので、全員が同じ写し間違いをしていれば一致してしまう。
 *   実際 2026-09-14 に、`fs_image_create` の第 5 引数 `fs_dtype_t dtype` が
 *   **ヘッダにだけ在って実装と 3 つの FFI 宣言に無い**状態が見つかった ——
 *   差分ファジング 60,000 ケース × 3 シードも変異解析 10/10 も素通りしていた。
 *   C ABI の引数ずれは実行時に何の兆候も出さず、黙って別の値を掴む。
 *
 *   **ヘッダを読む呼び手が 1 つあれば、コンパイラがその場で止める。**
 *   これがこの例の存在理由で、速度や機能のためではない。
 *
 * 建て方(Windows / clang):
 *   cd rust/fullseye_core && cargo build --release
 *   clang -std=c11 -Wall -Wextra -I../.. examples/c/main.c \
 *         target/release/fullseye_core.dll.lib -o examples/c/fs_example.exe
 *   cp target/release/fullseye_core.dll examples/c/     # ★実行時に必要
 *   cd examples/c && ./fs_example.exe
 *
 *   ★`.lib`(インポートライブラリ)でリンクしても、**実行時は DLL を別に探す**。
 *     置き忘れると exe は何も印字せずに終わる —— 最初これを「ビルドが通ったから
 *     動いた」と読みかけた。`EXIT=0` も `head` の終了コードで、exe のものでは
 *     なかった。「走った」と「意味のある出力が出た」は別に数える。
 *
 * Linux / macOS:
 *   clang -std=c11 -Wall -Wextra -I../.. examples/c/main.c \
 *         -Ltarget/release -lfullseye_core -o examples/c/fs_example
 *   LD_LIBRARY_PATH=target/release ./examples/c/fs_example
 */
#include <stdio.h>
#include "fullseye_abi.h"

/* R-1: すべての関数が状態コードを返す。黙って代替値を使わない。 */
static int check(fs_status_t st, const char *what)
{
    if (st != FS_OK) {
        fprintf(stderr, "%s が status %d を返した\n", what, (int)st);
        return 1;
    }
    return 0;
}

int main(void)
{
    enum { N = 8 };
    double px[N * N];
    for (int r = 0; r < N; ++r)
        for (int c = 0; c < N; ++c)
            px[r * N + c] = (double)((r + c) % 2);      /* 市松 */

    fs_image_t *img = NULL;
    if (check(fs_image_create(px, N, N, (int64_t)(N * sizeof(double)),
                              FS_DTYPE_F64, 0.0, 1.0, &img), "fs_image_create"))
        return 1;

    fs_dtype_t dt;
    if (check(fs_image_dtype(img, &dt), "fs_image_dtype")) return 1;
    printf("dtype 読み返し: %d (FS_DTYPE_F64 = %d)\n", (int)dt, (int)FS_DTYPE_F64);

    /* lo/hi は 0..1 の相対値。画像が名乗る値域を通して解決される(R-3)。 */
    fs_region_t *reg = NULL;
    if (check(fs_threshold(img, 0.5, 1.0, &reg), "fs_threshold")) return 1;

    int64_t area = 0, runs = 0, n = 0;
    if (check(fs_region_area(reg, &area), "fs_region_area")) return 1;
    if (check(fs_region_run_count(reg, &runs), "fs_region_run_count")) return 1;

    fs_objectset_t *objs = NULL;
    if (check(fs_connection(reg, &objs), "fs_connection")) return 1;
    if (check(fs_objectset_count(objs, &n), "fs_objectset_count")) return 1;

    printf("面積 %lld / run %lld / 物体 %lld\n",
           (long long)area, (long long)runs, (long long)n);

    /* 契約は 8 連結なので市松は 1 個(4 連結なら 32 個)。 */
    int ok = (area == 32 && n == 1);
    printf(ok ? "契約どおり: 8x8 の市松は 8 連結で 1 個\n"
              : "★契約と違う\n");

    /* 逆さの区間は「空」ではなく **失敗**(R-1)。 */
    fs_region_t *bad_reg = NULL;
    fs_status_t bad = fs_threshold(img, 0.8, 0.2, &bad_reg);
    if (bad != FS_OK)
        printf("逆さの区間 lo>hi は status %d で拒まれた\n", (int)bad);
    else
        printf("★逆さの区間が通ってしまった\n");

    /* ---- 汎用入口 fs_apply: op 名 + JSON で呼ぶ。どの経路で走ったかが info に必ず出る ----
     * native 経路(契約の 5 op は Rust 実装がある)。出力の画素は契約の中では読めない
     * ので、threshold に通して面積で観測する(ヘッダの註のとおり)。 */
    fs_handle_t in = { FS_KIND_IMAGE, img };
    fs_handle_t out[4];
    int n_out = 0;
    fs_apply_info_t info;
    fs_status_t st = fs_apply("gauss", &in, 1, "{\"sigma\": 1.0}", FS_ROUTE_AUTO,
                              out, 4, &n_out, &info);
    int apply_ok = 0;
    if (st == FS_OK && n_out == 1 && out[0].kind == FS_KIND_IMAGE) {
        fs_region_t *r2 = NULL;
        int64_t a2 = 0;
        if (fs_threshold((fs_image_t *)out[0].ptr, 0.5, 1.0, &r2) == FS_OK &&
            fs_region_area(r2, &a2) == FS_OK) {
            printf("fs_apply gauss: route=%s backend=%s degraded=%d 面積(>=0.5) %lld\n",
                   info.route, info.backend, info.degraded, (long long)a2);
            apply_ok = 1;
        }
        fs_region_release(r2);
        fs_image_release((fs_image_t *)out[0].ptr);
    } else {
        printf("fs_apply gauss が status %d: %s\n", (int)st, info.message);
    }

    /* python 経路(レジストリの op。`embed` feature で建てたときだけ動く。無ければ
     * FS_E_NO_PYTHON と理由が返る —— それは失敗ではなく「この経路は無い」という答え)。 */
    st = fs_apply("gaussian", &in, 1, "{\"a\": 0.5}", FS_ROUTE_AUTO, out, 4, &n_out, &info);
    if (st == FS_OK && n_out == 1 && out[0].kind == FS_KIND_IMAGE) {
        fs_region_t *r3 = NULL;
        int64_t a3 = 0;
        if (fs_threshold((fs_image_t *)out[0].ptr, 0.5, 1.0, &r3) == FS_OK &&
            fs_region_area(r3, &a3) == FS_OK)
            printf("fs_apply gaussian: route=%s backend=%s degraded=%d 面積(>=0.5) %lld\n",
                   info.route, info.backend, info.degraded, (long long)a3);
        fs_region_release(r3);
        fs_image_release((fs_image_t *)out[0].ptr);
    } else if (st == FS_E_NO_PYTHON) {
        printf("fs_apply gaussian: python 経路なし(%s)\n", info.message);
    } else {
        printf("fs_apply gaussian が status %d: %s\n", (int)st, info.message);
        apply_ok = 0;
    }

    fs_objectset_release(objs);
    fs_region_release(reg);
    fs_image_release(img);
    return (ok && bad != FS_OK && apply_ok) ? 0 : 1;
}
