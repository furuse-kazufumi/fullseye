#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // blockSize は奇数でなければならない。a は [0,1] の範囲で与えられるため、3 から 15 の範囲に変換する。
    int blockSize = 2 * (int)(a * 6) + 3;
    // C は 0 から 10 の範囲で与えられるため、0 から 10 の範囲に変換する。
    int C = (int)(b * 10);

    // ガウスカーネルの作成
    int kernelSize = blockSize;
    double sigma = 0.3 * ((double)kernelSize - 1) + 0.8;
    double sum = 0.0;
    double kernel[kernelSize * kernelSize];
    for (int y = 0; y < kernelSize; y++) {
        for (int x = 0; x < kernelSize; x++) {
            int i = y * kernelSize + x;
            double dx = (x - (kernelSize - 1) / 2.0);
            double dy = (y - (kernelSize - 1) / 2.0);
            kernel[i] = exp(-(dx * dx + dy * dy) / (2 * sigma * sigma));
            sum += kernel[i];
        }
    }
    for (int i = 0; i < kernelSize * kernelSize; i++) {
        kernel[i] /= sum;
    }

    // 出力画像の初期化
    for (int i = 0; i < h * w; i++) {
        out[i] = 0.0;
    }

    // 画像の各ピクセルに対して処理を実行
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double mean = 0.0;
            int count = 0;
            for (int ky = -kernelSize / 2; ky <= kernelSize / 2; ky++) {
                for (int kx = -kernelSize / 2; kx <= kernelSize / 2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // 画像の境界外を処理しない
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        int index = ny * w + nx;
                        mean += in[index] * kernel[(ky + kernelSize / 2) * kernelSize + (kx + kernelSize / 2)];
                        count++;
                    }
                }
            }
            mean /= count;
            // しきい値の計算
            double threshold = mean - C;
            // 二値化処理
            out[y * w + x] = (in[y * w + x] > threshold) ? 1.0 : 0.0;
        }
    }
}
