#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は半径 r を設定する。a の値を 0.11, 0.29, 0.51, 0.69, 0.91 に近い値で切り替える。
    // これらの値は仕様書で指定されている。
    int r = (a < 0.11) ? 1 : (a < 0.29) ? 2 : (a < 0.51) ? 3 : (a < 0.69) ? 4 : (a < 0.91) ? 5 : 6;

    // 出力を 0 で初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 各ピクセルについて、その周囲の対称性を測定
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double asymmetry = 0.0;
            int count = 0;

            // 端のピクセルは最近傍で埋める
            for (int d = 1; d <= r; d++) {
                int left = x - d;
                int right = x + d;

                // 左端
                if (left < 0) {
                    left = 0;
                }
                // 右端
                if (right >= w) {
                    right = w - 1;
                }

                // 異なる距離 d での対称性を測定
                asymmetry += (1.0 / d) * fabs(in[y * w + left] - in[y * w + right]);
                count++;
            }

            // 異なる距離 d での対称性の平均を計算
            asymmetry /= count;

            // 出力を正規化
            out[y * w + x] = asymmetry;
        }
    }

    // 正規化
    double max_value = 0.0;
    for (int i = 0; i < h * w; i++) {
        if (out[i] > max_value) {
            max_value = out[i];
        }
    }
    if (max_value > 0.0) {
        for (int i = 0; i < h * w; i++) {
            out[i] /= max_value;
        }
    }
}
