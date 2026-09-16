#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。つまみ a はガウシアン σ のスケーリングファクターとして使用。
    double sigma = 0.5 + 2.0 * a;

    // 出力画像の最大値を追跡するための変数
    double max_response = 0.0;

    // Harris コーナー応答の計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 画像の端を無視する。端の処理は仕様書に明記されていないため、端のピクセルは計算しない。
            if (x == 0 || y == 0 || x == w - 1 || y == h - 1) {
                out[y * w + x] = 0.0;
                continue;
            }

            // Harris コーナー応答の計算
            double Ix = (in[(y) * w + (x + 1)] - in[(y) * w + (x - 1)]) / (2.0 * sigma);
            double Iy = (in[(y + 1) * w + (x)] - in[(y - 1) * w + (x)]) / (2.0 * sigma);
            double Ixx = (in[(y) * w + (x + 1)] - 2 * in[(y) * w + (x)] + in[(y) * w + (x - 1)]) / (sigma * sigma);
            double Iyy = (in[(y + 1) * w + (x)] - 2 * in[(y) * w + (x)] + in[(y - 1) * w + (x)]) / (sigma * sigma);
            double Ixy = (in[(y + 1) * w + (x + 1)] - in[(y + 1) * w + (x - 1)] - in[(y - 1) * w + (x + 1)] + in[(y - 1) * w + (x - 1)]) / (4.0 * sigma * sigma);

            double det = Ixx * Iyy - Ixy * Ixy;
            double trace = Ixx + Iyy;
            double response = det - 0.05 * trace * trace;

            // 出力画像の最大値を更新
            if (response > max_response) {
                max_response = response;
            }

            // 出力を [0,1] の範囲に正規化
            out[y * w + x] = response / max_response;
        }
    }
}
