#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Harris コーナー応答の計算には、画像の各ピクセルにおける x, y 方向の微分が
    // 必要となる。ここでは、単純な中心差分を使用する。
    // また、スコア係数 k は a から計算される。b は使用しない。
    double k = 0.04 + 0.02 * a;

    // 画像の各ピクセルに対して、Harris コーナー応答を計算する。
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            // x, y 方向の微分を計算
            double dx = in[(y + 1) * w + x] - in[(y - 1) * w + x];
            double dy = in[y * w + (x + 1)] - in[y * w + (x - 1)];

            // Ixx, Iyy, Ixy の計算
            double Ixx = dx * dx;
            double Iyy = dy * dy;
            double Ixy = dx * dy;

            // Harris マトリクスのトレースと行列式の計算
            double trace = Ixx + Iyy;
            double det = Ixx * Iyy - Ixy * Ixy;

            // Harris コーナー応答の計算
            double response = det - k * trace * trace;

            // 出力を正規化する。画像全体の最大値で正規化する。
            // 画像全体の最大値を計算するため、一時的な変数 max に初期化。
            double max_response = response;
            for (int y2 = 1; y2 < h - 1; y2++) {
                for (int x2 = 1; x2 < w - 1; x2++) {
                    double dx2 = in[(y2 + 1) * w + x2] - in[(y2 - 1) * w + x2];
                    double dy2 = in[y2 * w + (x2 + 1)] - in[y2 * w + (x2 - 1)];
                    double Ixx2 = dx2 * dx2;
                    double Iyy2 = dy2 * dy2;
                    double Ixy2 = dx2 * dy2;
                    double trace2 = Ixx2 + Iyy2;
                    double det2 = Ixx2 * Iyy2 - Ixy2 * Ixy2;
                    double response2 = det2 - k * trace2 * trace2;
                    if (response2 > max_response) {
                        max_response = response2;
                    }
                }
            }

            // 出力を正規化
            out[y * w + x] = response / max_response;
        }
    }

    // 画像の端のピクセルは、端のピクセルの値をコピーする。
    // これは、端のピクセルの値が計算に必要ないため。
    for (int y = 0; y < h; y++) {
        out[y * w] = in[y * w];
        out[y * w + w - 1] = in[y * w + w - 1];
    }
    for (int x = 0; x < w; x++) {
        out[x] = in[x];
        out[(h - 1) * w + x] = in[(h - 1) * w + x];
    }
}
