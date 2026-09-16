#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // この実装では、画像の端を最近傍補完で処理する。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            int count = 0;
            // 3x3 ネイバーボックスの平均を計算
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 境界外アクセスを防ぐ
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx];
                        count++;
                    }
                }
            }
            double structure = sum / count;
            double texture = in[y * w + x] - structure;
            // 出力は texture - 0.5
            out[y * w + x] = texture - 0.5;
        }
    }
}
