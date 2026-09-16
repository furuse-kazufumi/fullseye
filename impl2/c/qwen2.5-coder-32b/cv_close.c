#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを計算 (3 から 9 まで)
    int se_size = 3 + 2 * (int)(a * 3);
    int se_radius = se_size / 2;

    // 一時的な出力バッファを確保
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        // メモリ確保に失敗した場合、出力を 0 で埋めて終了
        memset(out, 0, h * w * sizeof(double));
        return;
    }

    // 膨張処理 (dilation)
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = in[y * w + x];
            for (int dy = -se_radius; dy <= se_radius; dy++) {
                for (int dx = -se_radius; dx <= se_radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        max_val = fmax(max_val, in[ny * w + nx]);
                    }
                }
            }
            temp[y * w + x] = max_val;
        }
    }

    // 収縮処理 (erosion)
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = temp[y * w + x];
            for (int dy = -se_radius; dy <= se_radius; dy++) {
                for (int dx = -se_radius; dx <= se_radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        min_val = fmin(min_val, temp[ny * w + nx]);
                    }
                }
            }
            out[y * w + x] = min_val;
        }
    }

    // 一時的な出力バッファを解放
    free(temp);
}
