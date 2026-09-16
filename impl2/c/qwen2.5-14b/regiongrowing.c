#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数の計算
    double seed_threshold = 0.5 + 0.3 * a;
    int dilation_iterations = (int)(1 + 4 * b);

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 0.0;
        }
    }

    // シード領域の生成
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (in[y * w + x] > seed_threshold) {
                out[y * w + x] = 1.0;
            }
        }
    }

    // 膨張処理
    for (int i = 0; i < dilation_iterations; ++i) {
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                if (out[y * w + x] == 1.0) {
                    // 上
                    if (y > 0 && out[(y - 1) * w + x] == 0.0) {
                        out[(y - 1) * w + x] = 1.0;
                    }
                    // 下
                    if (y < h - 1 && out[(y + 1) * w + x] == 0.0) {
                        out[(y + 1) * w + x] = 1.0;
                    }
                    // 左
                    if (x > 0 && out[y * w + x - 1] == 0.0) {
                        out[y * w + x - 1] = 1.0;
                    }
                    // 右
                    if (x < w - 1 && out[y * w + x + 1] == 0.0) {
                        out[y * w + x + 1] = 1.0;
                    }
                }
            }
        }
    }
}
