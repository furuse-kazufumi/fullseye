#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a を使用して分解段数を決定
    int decomposition_level = 1 + (int)(a * 3);
    if (decomposition_level < 1) decomposition_level = 1;
    if (decomposition_level > 4) decomposition_level = 4;

    // 出力画像をクリア
    for (int i = 0; i < h * w; ++i) {
        out[i] = 0.0;
    }

    // 低周波成分のみを使用して画像を再構成
    for (int level = 0; level < decomposition_level; ++level) {
        int current_h = h;
        int current_w = w;
        for (int i = 0; i < level; ++i) {
            current_h = (current_h + 1) / 2;
            current_w = (current_w + 1) / 2;
        }

        // 低周波成分を取得
        for (int y = 0; y < current_h; ++y) {
            for (int x = 0; x < current_w; ++x) {
                int in_index = (y * 2) * w + (x * 2);
                double low_freq = in[in_index];
                out[y * w + x] = low_freq;
            }
        }

        // 出力画像を拡大
        for (int y = 0; y < current_h; ++y) {
            for (int x = 0; x < current_w; ++x) {
                int out_index = y * w + x;
                for (int dy = 0; dy < 2; ++dy) {
                    for (int dx = 0; dx < 2; ++dx) {
                        int in_index = (y * 2 + dy) * w + (x * 2 + dx);
                        if (in_index < h * w) {
                            out[out_index] += out[in_index];
                        }
                    }
                }
                out[out_index] /= 4.0;
            }
        }
    }

    // 出力を [0,1] の範囲にクリップ
    for (int i = 0; i < h * w; ++i) {
        if (out[i] < 0.0) out[i] = 0.0;
        if (out[i] > 1.0) out[i] = 1.0;
    }
}
