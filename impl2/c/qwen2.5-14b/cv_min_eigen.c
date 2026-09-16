#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は近傍サイズを決める。b は未使用。
    int blockSize = 3 + 2 * (int)(a * 2); // 近傍サイズの計算
    blockSize = (blockSize % 2 == 0) ? blockSize + 1 : blockSize; // 奇数に保つ

    // 出力画像の最大値を初期化
    double maxOutput = 0.0;

    // 各ピクセルについて計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 構造テンソルの計算
            double Ix = 0.0, Iy = 0.0, Ixx = 0.0, Iyy = 0.0, Ixy = 0.0;
            for (int dy = -blockSize / 2; dy <= blockSize / 2; ++dy) {
                for (int dx = -blockSize / 2; dx <= blockSize / 2; ++dx) {
                    int nx = x + dx, ny = y + dy;
                    if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue; // 端の処理
                    double I = in[ny * w + nx];
                    Ix += I * dx;
                    Iy += I * dy;
                    Ixx += I * dx * dx;
                    Iyy += I * dy * dy;
                    Ixy += I * dx * dy;
                }
            }

            // 構造テンソルの固有値を計算
            double trace = Ixx + Iyy;
            double det = Ixx * Iyy - Ixy * Ixy;
            double minEigenValue = (trace - sqrt(trace * trace - 4 * det)) / 2;

            // 出力画像の最大値を更新
            if (minEigenValue > maxOutput) maxOutput = minEigenValue;

            // 出力画像に書き込み
            out[y * w + x] = minEigenValue;
        }
    }

    // 出力画像を正規化
    for (int i = 0; i < h * w; ++i) {
        out[i] /= maxOutput;
    }
}
