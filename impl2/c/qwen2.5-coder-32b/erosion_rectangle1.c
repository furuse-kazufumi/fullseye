#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a が正方形の一辺を {3,5,7,9} で振る。b は未使用。
    int k_values[] = {3, 5, 7, 9};
    int k_index = (int)(a * 3.999); // a が [0,1] の範囲なので、0, 1, 2, 3 にマッピング
    int k = k_values[k_index];
    int half_k = k / 2;

    // 画像の端を処理する方法: 境界外の画素は 0 と仮定する
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int is_region = 1;
            for (int ky = -half_k; ky <= half_k; ky++) {
                for (int kx = -half_k; kx <= half_k; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] == 0.0) {
                            is_region = 0;
                            break;
                        }
                    } else {
                        // 境界外の画素は 0 と仮定
                        is_region = 0;
                        break;
                    }
                }
                if (!is_region) break;
            }
            out[y * w + x] = is_region ? 1.0 : 0.0;
        }
    }
}
