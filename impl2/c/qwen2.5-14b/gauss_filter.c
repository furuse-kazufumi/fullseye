#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の処理のために、画像の境界を拡張する
    // 画像の端を重複させて折り返す (reflect)
    // これは、入力画像の境界を拡張した仮想的な画像を生成します。
    // 仮想的な画像のサイズは (h+2) x (w+2) になります。
    // 仮想的な画像の各画素は、元の画像の画素を重複させて折り返して生成します。

    // 仮想的な画像のサイズ
    int vh = h + 2;
    int vw = w + 2;

    // 仮想的な画像の配列
    double virtual_image[vh * vw];

    // 仮想的な画像の生成
    for (int y = 0; y < vh; y++) {
        for (int x = 0; x < vw; x++) {
            // 元の画像の範囲外の場合は、端の画素を重複させて折り返す
            int real_y = y - 1;
            int real_x = x - 1;
            if (real_y < 0 || real_y >= h || real_x < 0 || real_x >= w) {
                // 端の画素を重複させて折り返す
                real_y = (real_y < 0) ? 0 : (real_y >= h) ? h - 1 : real_y;
                real_x = (real_x < 0) ? 0 : (real_x >= w) ? w - 1 : real_x;
            }
            virtual_image[y * vw + x] = in[real_y * w + real_x];
        }
    }

    // ガウシアンフィルタの適用
    double sigma = 0.3 + 2.7 * a;
    double factor = 1.0 / (sigma * sqrt(2.0 * M_PI));
    double exponent = -0.5 / (sigma * sigma);

    // ガウシアンフィルタのカーネルサイズ
    int kernel_size = 5;
    int half_kernel = kernel_size / 2;

    // 出力画像の生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double weight_sum = 0.0;
            for (int ky = -half_kernel; ky <= half_kernel; ky++) {
                for (int kx = -half_kernel; kx <= half_kernel; kx++) {
                    int vy = y + ky + 1; // 仮想的な画像の y 座標
                    int vx = x + kx + 1; // 仮想的な画像の x 座標
                    double weight = factor * exp(kx * kx + ky * ky * exponent);
                    sum += virtual_image[vy * vw + vx] * weight;
                    weight_sum += weight;
                }
            }
            out[y * w + x] = sum / weight_sum;
        }
    }
}
