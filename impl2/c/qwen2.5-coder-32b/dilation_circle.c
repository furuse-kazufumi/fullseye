#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a が [0, 1] の範囲なので、半径を 1 から 4 にスケーリング
    int radius = (int)(1 + 3 * a);
    int diameter = 2 * radius + 1;

    // 画像の端を処理する方法: 境界外の画素は 0 と仮定する
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
            for (int ky = -radius; ky <= radius; ky++) {
                for (int kx = -radius; kx <= radius; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] == 1.0) {
                            double dist = sqrt(ky * ky + kx * kx);
                            if (dist <= radius) {
                                out[y * w + x] = 1.0;
                                break;
                            }
                        }
                    }
                }
                if (out[y * w + x] == 1.0) {
                    break;
                }
            }
        }
    }
}
