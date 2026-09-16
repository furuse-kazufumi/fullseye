#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 局所窓サイズの計算
    int window_size = 2 * (int)(a * 6) + 3;
    // 窓サイズが奇数であることを確認
    if (window_size % 2 == 0) {
        window_size++;
    }

    // 窓の半径
    int radius = window_size / 2;

    // 辺の処理
    // 画像の端の画素については、端の画素値を用いて計算を行う。
    // これは、端の画素値が局所的な平均と標準偏差の計算に影響を与える可能性があるため。

    // 画像の各画素に対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double sum_sq = 0.0;
            int count = 0;

            // 局所的な平均と標準偏差を計算
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 画像の範囲内に収まるか確認
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double pixel = in[ny * w + nx];
                        sum += pixel;
                        sum_sq += pixel * pixel;
                        count++;
                    }
                }
            }

            double mean = sum / count;
            double std_dev = sqrt((sum_sq / count) - (mean * mean));

            // Niblackのしきい値を計算
            double threshold = mean * (1.0 + std_dev);

            // しきい値を超える画素を1.0、それ以下の画素を0.0として出力
            out[y * w + x] = (in[y * w + x] > threshold) ? 1.0 : 0.0;
        }
    }
}
