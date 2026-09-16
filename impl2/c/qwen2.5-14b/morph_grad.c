#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。つまみ a は構造要素の一辺を 3,5,7,9 に振る。
    // a の値によって構造要素のサイズが変わる。a ≈ 0.25, 0.49, 0.75 で切り替わる。
    int kernel_size = 3 + (int)(a * 3); // a の値に基づいてカーネルサイズを決定
    if (kernel_size > 9) kernel_size = 9; // カーネルサイズの上限を 9 に制限

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = 0.0;
    }

    // マスクのサイズを計算
    int mask_half_size = kernel_size / 2;

    // 画像の各ピクセルに対して処理を実行
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double max_val = -INFINITY;
            double min_val = INFINITY;

            // 現在のピクセルを中心としたマスク内のピクセルを処理
            for (int ky = -mask_half_size; ky <= mask_half_size; ++ky) {
                for (int kx = -mask_half_size; kx <= mask_half_size; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 画像の境界外の場合は無視
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) continue;

                    double val = in[ny * w + nx];
                    if (val > max_val) max_val = val;
                    if (val < min_val) min_val = val;
                }
            }

            // 最大値と最小値の差を出力画像に設定
            out[y * w + x] = max_val - min_val;
        }
    }

    // 正規化
    double max_out = -INFINITY;
    for (int i = 0; i < h * w; ++i) {
        if (out[i] > max_out) max_out = out[i];
    }
    for (int i = 0; i < h * w; ++i) {
        out[i] /= max_out;
    }
}
