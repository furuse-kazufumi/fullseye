#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端をゼロパディングする。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double dx = 0.0, dy = 0.0;

            if (x > 0 && x < w - 1 && y > 0 && y < h - 1) {
                // Scharr カーネルの適用
                dx = 3 * (in[(y+1)*w + (x+1)] - in[(y+1)*w + (x-1)]) +
                     10 * (in[y*w + (x+1)] - in[y*w + (x-1)]) +
                     3 * (in[(y-1)*w + (x+1)] - in[(y-1)*w + (x-1)]);

                dy = 3 * (in[(y+1)*w + (x+1)] - in[(y-1)*w + (x+1)]) +
                     10 * (in[(y+1)*w + x] - in[(y-1)*w + x]) +
                     3 * (in[(y+1)*w + (x-1)] - in[(y-1)*w + (x-1)]);
            }

            // 勾配強度の計算
            out[y*w + x] = fabs(dx) + fabs(dy);
        }
    }
}
