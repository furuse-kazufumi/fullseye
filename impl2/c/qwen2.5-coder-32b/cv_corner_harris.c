#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ブロックサイズとSobelカーネルサイズは固定
    const int blockSize = 2;
    const int ksize = 3;
    const double k = 0.04;

    // Sobelカーネルの定義
    const double sobel_x[3][3] = {
        {-1, 0, 1},
        {-2, 0, 2},
        {-1, 0, 1}
    };
    const double sobel_y[3][3] = {
        {-1, -2, -1},
        { 0,  0,  0},
        { 1,  2,  1}
    };

    // 画像の端をどう処理するか: ここではゼロパディングを使用する
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double Ix = 0.0, Iy = 0.0;

            // Sobelフィルタリング
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // ゼロパディング
                    double pixel = (ny >= 0 && ny < h && nx >= 0 && nx < w) ? in[ny * w + nx] : 0.0;

                    Ix += pixel * sobel_x[ky + 1][kx + 1];
                    Iy += pixel * sobel_y[ky + 1][kx + 1];
                }
            }

            // Ix^2, Iy^2, Ix*Iy の計算
            double Ix2 = Ix * Ix;
            double Iy2 = Iy * Iy;
            double IxIy = Ix * Iy;

            // ブロック内の和を計算
            double sum_Ix2 = 0.0, sum_Iy2 = 0.0, sum_IxIy = 0.0;
            for (int ky = -blockSize; ky <= blockSize; ky++) {
                for (int kx = -blockSize; kx <= blockSize; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // ゼロパディング
                    double weight = (ny >= 0 && ny < h && nx >= 0 && nx < w) ? 1.0 : 0.0;

                    sum_Ix2 += Ix2 * weight;
                    sum_Iy2 += Iy2 * weight;
                    sum_IxIy += IxIy * weight;
                }
            }

            // Harris応答の計算
            double det = sum_Ix2 * sum_Iy2 - sum_IxIy * sum_IxIy;
            double trace = sum_Ix2 + sum_Iy2;
            double R = det - k * trace * trace;

            // 出力を [0, 1] にクリッピング
            out[y * w + x] = fmax(0.0, fmin(1.0, R));
        }
    }
}
