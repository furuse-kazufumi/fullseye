#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 焦点距離 f と基線長 baseline の計算
    double f = 200 + 600 * a;
    double baseline = 0.05 + 0.15 * b;

    // 出力画像の各ピクセルに対して計算を行う
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 入力画像のピクセル値を取得
            double v = in[y * w + x];

            // 視差の計算
            double disp = v * 63 + 0.5;

            // 深度 Z の計算
            double z = f * baseline / disp;

            // min-max 正規化
            double min_z = f * baseline / (63 + 0.5);
            double max_z = f * baseline / 0.5;
            double normalized_z = (z - min_z) / (max_z - min_z);

            // 正規化された深度を出力画像に格納
            out[y * w + x] = normalized_z;
        }
    }
}
