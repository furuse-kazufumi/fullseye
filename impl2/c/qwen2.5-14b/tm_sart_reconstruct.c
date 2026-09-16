#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 反復回数の計算
    int iterations = round(1 + a * 4); // 1 から 5 の間の整数
    double relaxation = 0.05 + b * 0.35; // 0.05 から 0.4 の間の実数

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = 0.0;
    }

    // SART アルゴリズムの実装
    for (int iter = 0; iter < iterations; ++iter) {
        // 仮の投影データの生成 (ここでは入力画像をそのまま使用)
        double* projection = (double*)malloc(h * w * sizeof(double));
        for (int i = 0; i < h * w; ++i) {
            projection[i] = in[i];
        }

        // 逆投影 (back-projection)
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                double sum = 0.0;
                for (int i = 0; i < h * w; ++i) {
                    double angle = i / (double)(h * w - 1); // 0 から 1 の間の角度
                    double distance = sqrt((x - w / 2) * (x - w / 2) + (y - h / 2) * (y - h / 2)); // ピクセルから中心までの距離
                    double weight = cos(angle) * distance; // 重み付け
                    sum += projection[i] * weight;
                }
                out[y * w + x] += relaxation * sum;
            }
        }

        // 重み付けの更新
        for (int i = 0; i < h * w; ++i) {
            projection[i] *= relaxation;
        }

        // メモリの解放
        free(projection);
    }

    // 出力画像の正規化
    double max_value = 0.0;
    for (int i = 0; i < h * w; ++i) {
        if (out[i] > max_value) {
            max_value = out[i];
        }
    }
    if (max_value > 0.0) {
        for (int i = 0; i < h * w; ++i) {
            out[i] /= max_value;
        }
    }
}
