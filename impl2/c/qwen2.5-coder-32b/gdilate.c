#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a が構造要素の一辺の長さを決める。範囲は [0, 1] なので、3, 5, 7, 9 のいずれかにマッピングする。
    int k = (int)(a * 4) * 2 + 3;
    int k_half = k / 2;

    // 画像の端を処理する方法: 境界外のピクセルには 0 を仮定する。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = -1.0;
            for (int ky = -k_half; ky <= k_half; ky++) {
                for (int kx = -k_half; kx <= k_half; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] > max_val) {
                            max_val = in[ny * w + nx];
                        }
                    }
                }
            }
            out[y * w + x] = max_val;
        }
    }
}
