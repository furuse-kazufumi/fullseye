#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用
    (void)a;
    (void)b;

    // Sobel カーネル
    const double sobel_x[3][3] = {{-1, 0, 1}, {-2, 0, 2}, {-1, 0, 1}};
    const double sobel_y[3][3] = {{-1, -2, -1}, {0, 0, 0}, {1, 2, 1}};

    // 端の扱い: 端画素を重複させて折り返す
    // 画像の端の計算では、境界外のピクセルは反対側のピクセルを使用する

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double Gx = 0.0;
            double Gy = 0.0;

            // Sobel オペレータを適用
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int y_pos = y + ky;
                    int x_pos = x + kx;

                    // 端の処理: 画像の端のピクセルを反対側のピクセルで置き換える
                    if (y_pos < 0) y_pos = -y_pos - 1;
                    if (y_pos >= h) y_pos = 2 * h - y_pos - 1;
                    if (x_pos < 0) x_pos = -x_pos - 1;
                    if (x_pos >= w) x_pos = 2 * w - x_pos - 1;

                    Gx += in[y_pos * w + x_pos] * sobel_x[ky + 1][kx + 1];
                    Gy += in[y_pos * w + x_pos] * sobel_y[ky + 1][kx + 1];
                }
            }

            // ユークリッドノルムを計算
            out[y * w + x] = hypot(Gx, Gy);
        }
    }

    // 正規化: 出力をその画像の最大値で正規化
    double max_val = 0.0;
    for (int i = 0; i < h * w; ++i) {
        if (out[i] > max_val) {
            max_val = out[i];
        }
    }
    if (max_val > 0.0) {
        for (int i = 0; i < h * w; ++i) {
            out[i] /= max_val;
        }
    }
}
