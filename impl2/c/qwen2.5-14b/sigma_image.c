#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの決定
    int window_size = 3 + (int)(a * 3); // a が 0.1 から 0.9 まで動くと、window_size は 3 から 9 まで動く
    window_size = window_size > 1 ? window_size : 3; // 最小値は 3

    // 許容帯域の決定
    double sigma = b * 0.4; // b が 0.1 から 0.9 まで動くと、sigma は 0.04 から 0.36 まで動く

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // シグマフィルタの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double mean = 0.0;
            int count = 0;

            // 窓内の画素の平均を計算
            for (int dy = -window_size / 2; dy <= window_size / 2; dy++) {
                for (int dx = -window_size / 2; dx <= window_size / 2; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 端の処理: 入力画像の端を折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;

                    double pixel = in[ny * w + nx];
                    if (fabs(pixel - in[y * w + x]) < sigma) {
                        mean += pixel;
                        count++;
                    }
                }
            }

            // 平均を計算
            if (count > 0) {
                mean /= count;
                out[y * w + x] = mean;
            }
        }
    }
}
