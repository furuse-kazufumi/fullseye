#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は [0,1] の範囲で、{3,5,7,9} のいずれかにマッピングされる。
    // ここでは a が 0.1 から 0.9 の範囲で、{3,5,7,9} のいずれかにマッピングされるようにする。
    int kernel_size = (int)(a * 4 + 1); // 0.1 -> 3, 0.5 -> 5, 0.9 -> 9
    if (kernel_size < 3) kernel_size = 3; // 最小値は 3
    if (kernel_size > 9) kernel_size = 9; // 最大値は 9

    // 画像の端をどのように処理するか。ここでは境界画素を 0 で埋める。
    // これはクロージング操作の一般的な手法であり、領域の外側を 0 で埋める。
    int pad = kernel_size / 2;
    int padded_h = h + 2 * pad;
    int padded_w = w + 2 * pad;
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    memset(padded_in, 0, padded_h * padded_w * sizeof(double));

    // 入力画像をパディング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + pad) * padded_w + (x + pad)] = in[y * w + x];
        }
    }

    // ダイレクトマーカーを計算
    double* direct_markers = (double*)malloc(padded_h * padded_w * sizeof(double));
    memset(direct_markers, 0, padded_h * padded_w * sizeof(double));

    // ダイレクトマーカーの計算
    for (int y = pad; y < padded_h - pad; y++) {
        for (int x = pad; x < padded_w - pad; x++) {
            direct_markers[y * padded_w + x] = padded_in[y * padded_w + x];
            for (int ky = -pad; ky <= pad; ky++) {
                for (int kx = -pad; kx <= pad; kx++) {
                    if (padded_in[(y + ky) * padded_w + (x + kx)] == 1) {
                        direct_markers[y * padded_w + x] = 1;
                        break;
                    }
                }
                if (direct_markers[y * padded_w + x] == 1) break;
            }
        }
    }

    // ダイレクトマーカーを元の画像サイズにリサイズ
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = direct_markers[(y + pad) * padded_w + (x + pad)];
        }
    }

    free(padded_in);
    free(direct_markers);
}
