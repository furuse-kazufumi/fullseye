#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Prewitt オペレータのカーネル
    const double kernel_x[3][3] = {{1, 0, -1}, {1, 0, -1}, {1, 0, -1}};
    const double kernel_y[3][3] = {{1, 1, 1}, {0, 0, 0}, {-1, -1, -1}};

    // 出力画像の最大値を初期化
    double max_out = 0.0;

    // 各画素について Prewitt オペレータを適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double gx = 0.0, gy = 0.0;

            // Prewitt オペレータの適用
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 端の画素は折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;

                    gx += kernel_x[ky + 1][kx + 1] * in[ny * w + nx];
                    gy += kernel_y[ky + 1][kx + 1] * in[ny * w + nx];
                }
            }

            // 振幅を計算
            double amp = sqrt(gx * gx + gy * gy);

            // 最大値を更新
            if (amp > max_out) {
                max_out = amp;
            }

            // 出力画像に結果を保存
            out[y * w + x] = amp;
        }
    }

    // 出力を最大値で正規化
    for (int i = 0; i < h * w; ++i) {
        out[i] /= max_out;
    }
}
