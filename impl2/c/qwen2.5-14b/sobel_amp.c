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
            double gx = 0.0, gy = 0.0;

            // Sobel カーネルを適用
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int y1 = y + ky;
                    int x1 = x + kx;

                    // 端の処理: 端画素を重複させて折り返す
                    if (y1 < 0) y1 = -y1;
                    if (y1 >= h) y1 = h - (y1 - h + 1);
                    if (x1 < 0) x1 = -x1;
                    if (x1 >= w) x1 = w - (x1 - w + 1);

                    gx += in[y1 * w + x1] * sobel_x[ky + 1][kx + 1];
                    gy += in[y1 * w + x1] * sobel_y[ky + 1][kx + 1];
                }
            }

            // 勾配ベクトルの大きさを求める
            double amp = hypot(gx, gy);

            // 出力をその画像の最大値で正規化
            out[y * w + x] = amp;
        }
    }

    // 最大値を求める
    double max_amp = 0.0;
    for (int i = 0; i < h * w; ++i) {
        if (out[i] > max_amp) {
            max_amp = out[i];
        }
    }

    // 正規化
    if (max_amp > 0.0) {
        for (int i = 0; i < h * w; ++i) {
            out[i] /= max_amp;
        }
    }
}
