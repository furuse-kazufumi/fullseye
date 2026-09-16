#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は局所窓のサイズ(blockSize)を 3〜15(奇数)に、b は局所平均から引く定数 C を 0〜10 に振る
    int blockSize = 2 * (int)(a * 6) + 3; // 3, 5, 7, 9, 11, 13, 15
    int C = (int)(b * 10); // 0, 1, 2, ..., 10

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = 0.0;
    }

    // 局所平均を計算し、しきい値を適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            int count = 0;

            // 局所窓内の画素を走査
            for (int dy = -blockSize / 2; dy <= blockSize / 2; ++dy) {
                for (int dx = -blockSize / 2; dx <= blockSize / 2; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 画像の境界外を無視
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx];
                        ++count;
                    }
                }
            }

            // 局所平均を計算
            double mean = sum / count;

            // しきい値を適用
            if (in[y * w + x] > (mean - C)) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
