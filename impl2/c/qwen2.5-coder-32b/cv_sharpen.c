#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 使用しないパラメータ b は無視する
    // 端の扱い: 端画素を重複させずに折り返す (BORDER_REFLECT_101)

    double kernel[9] = {
        -a, -a, -a,
        -a, 1 + 4 * a, -a,
        -a, -a, -a
    };

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 端の処理: 折り返し (BORDER_REFLECT_101)
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;

                    sum += in[ny * w + nx] * kernel[(ky + 1) * 3 + (kx + 1)];
                }
            }
            // 出力を [0, 1] にクリッピング
            out[y * w + x] = fmax(0.0, fmin(1.0, sum));
        }
    }
}
