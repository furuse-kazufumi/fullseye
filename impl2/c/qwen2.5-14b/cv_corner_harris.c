#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Harris コーナー検出のパラメータ
    const int blockSize = 2;
    const int apertureSize = 3;
    const double k = 0.04;

    // 出力画像の最大値を初期化
    double max_response = 0.0;

    // 画像の各ピクセルに対してHarris応答を計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // ピクセルのインデックス
            int idx = y * w + x;

            // ピクセルの値
            double pixel_value = in[idx];

            // 周囲のピクセルを取得
            double Ix = 0.0, Iy = 0.0;
            for (int dy = -blockSize; dy <= blockSize; ++dy) {
                for (int dx = -blockSize; dx <= blockSize; ++dx) {
                    int ny = y + dy, nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double delta = in[ny * w + nx] - pixel_value;
                        Ix += delta * dx;
                        Iy += delta * dy;
                    }
                }
            }

            // Ix, Iy の平滑化
            Ix /= (blockSize * 2 + 1) * (blockSize * 2 + 1);
            Iy /= (blockSize * 2 + 1) * (blockSize * 2 + 1);

            // Harris応答の計算
            double Sxx = Ix * Ix;
            double Syy = Iy * Iy;
            double Sxy = Ix * Iy;
            double det = Sxx * Syy - Sxy * Sxy;
            double trace = Sxx + Syy;
            double response = det - k * trace * trace;

            // 出力画像に書き込み
            out[idx] = response;

            // 最大応答を更新
            if (response > max_response) {
                max_response = response;
            }
        }
    }

    // 出力画像を最大応答で正規化
    for (int i = 0; i < h * w; ++i) {
        out[i] /= max_response;
    }
}
