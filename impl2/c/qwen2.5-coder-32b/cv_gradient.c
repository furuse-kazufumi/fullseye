#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 結構要素のサイズを計算 (3 から 9 まで)
    int se_size = 3 + 2 * (int)(a * 3);
    int se_radius = se_size / 2;

    // 画像の端を処理する方法: 境界外のピクセルは 0 と仮定する
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = -1.0;
            double min_val = 2.0;

            for (int ky = -se_radius; ky <= se_radius; ky++) {
                for (int kx = -se_radius; kx <= se_radius; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double val = in[ny * w + nx];
                        if (val > max_val) max_val = val;
                        if (val < min_val) min_val = val;
                    }
                }
            }

            out[y * w + x] = max_val - min_val;
        }
    }
}
