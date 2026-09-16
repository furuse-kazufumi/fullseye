#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // カーネルサイズの決定
    int kernel_size = 3 + (int)(a * 3); // 3, 5, 7, 9 のいずれか
    if (kernel_size < 3) kernel_size = 3;
    if (kernel_size > 9) kernel_size = 9;

    // 出力画像の最大値を初期化
    double max_output = 0.0;

    // ラプラシアンフィルタの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double laplacian = 0.0;

            // ラプラシアンフィルタのカーネルを適用
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 画像の境界外を処理するための補間
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) {
                        laplacian += in[y * w + x] * 0.0; // 境界外は 0 とする
                    } else {
                        laplacian += in[ny * w + nx] * (kx * kx + ky * ky - (kernel_size / 2) * (kernel_size / 2));
                    }
                }
            }

            // 絶対値を取って最大値を更新
            laplacian = fabs(laplacian);
            if (laplacian > max_output) {
                max_output = laplacian;
            }

            // 出力画像に書き込み
            out[y * w + x] = laplacian;
        }
    }

    // 出力画像を最大値で正規化
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_output;
    }
}
