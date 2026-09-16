#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a が [0,1] の範囲なので、3, 5, 7, 9 のいずれかにマッピング
    int side_length = (int)(a * 4) * 2 + 3;
    int half_side = side_length / 2;

    // 一時的な出力バッファを確保
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        // メモリ確保に失敗した場合、出力を 0 で埋めて終了
        memset(out, 0, h * w * sizeof(double));
        return;
    }

    // ダイレクトリゼーション (Dilation)
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            temp[y * w + x] = 0.0;
            for (int dy = -half_side; dy <= half_side; dy++) {
                for (int dx = -half_side; dx <= half_side; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] == 1.0) {
                            temp[y * w + x] = 1.0;
                            break;
                        }
                    }
                }
                if (temp[y * w + x] == 1.0) {
                    break;
                }
            }
        }
    }

    // エロージョン (Erosion)
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 1.0;
            for (int dy = -half_side; dy <= half_side; dy++) {
                for (int dx = -half_side; dx <= half_side; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (temp[ny * w + nx] == 0.0) {
                            out[y * w + x] = 0.0;
                            break;
                        }
                    } else {
                        out[y * w + x] = 0.0;
                        break;
                    }
                }
                if (out[y * w + x] == 0.0) {
                    break;
                }
            }
        }
    }

    // 一時的な出力バッファを解放
    free(temp);
}
