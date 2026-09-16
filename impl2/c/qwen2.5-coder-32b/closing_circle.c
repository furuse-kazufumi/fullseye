#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a が構造要素の半径を 1〜4 の範囲で振る。b は未使用。
    int radius = (int)(1 + 3 * a); // a が [0,1] の範囲なので、半径は 1 から 4 になる。

    // 一時的な出力バッファを確保
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        // メモリ確保に失敗した場合、出力を 0 で埋めて終了
        memset(out, 0, h * w * sizeof(double));
        return;
    }

    // 膨張 (dilation)
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] == 1.0) {
                for (int dy = -radius; dy <= radius; dy++) {
                    for (int dx = -radius; dx <= radius; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            temp[ny * w + nx] = 1.0;
                        }
                    }
                }
            }
        }
    }

    // 収縮 (erosion)
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
            if (temp[y * w + x] == 1.0) {
                int all_inside = 1;
                for (int dy = -radius; dy <= radius; dy++) {
                    for (int dx = -radius; dx <= radius; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            if (temp[ny * w + nx] != 1.0) {
                                all_inside = 0;
                                break;
                            }
                        } else {
                            all_inside = 0;
                            break;
                        }
                    }
                    if (!all_inside) break;
                }
                if (all_inside) {
                    out[y * w + x] = 1.0;
                }
            }
        }
    }

    // 一時的な出力バッファを解放
    free(temp);
}
