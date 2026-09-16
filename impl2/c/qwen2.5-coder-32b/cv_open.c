#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを計算 (3 <= k <= 9)
    int k = 3 + 2 * (int)(a * 3);
    int half_k = k / 2;

    // 一時的な画像バッファを確保
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        // メモリ確保に失敗した場合、出力を0で埋めて終了
        memset(out, 0, h * w * sizeof(double));
        return;
    }

    // 収縮 (erosion) 処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = 1.0;
            for (int dy = -half_k; dy <= half_k; dy++) {
                for (int dx = -half_k; dx <= half_k; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double val = in[ny * w + nx];
                        if (val < min_val) {
                            min_val = val;
                        }
                    }
                }
            }
            temp[y * w + x] = min_val;
        }
    }

    // 膨張 (dilation) 処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = 0.0;
            for (int dy = -half_k; dy <= half_k; dy++) {
                for (int dx = -half_k; dx <= half_k; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double val = temp[ny * w + nx];
                        if (val > max_val) {
                            max_val = val;
                        }
                    }
                }
            }
            out[y * w + x] = max_val;
        }
    }

    // 一時的な画像バッファを解放
    free(temp);
}
