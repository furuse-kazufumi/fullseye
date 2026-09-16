#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用
    int iterations = (int)(a * 4.0); // a は [0,1] なので、最大 4 回の反復
    if (iterations < 0) iterations = 0;
    if (iterations > 4) iterations = 4;

    // 一時的な領域を確保
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        // メモリ確保に失敗した場合、出力を 0 で埋めて終了
        memset(out, 0, h * w * sizeof(double));
        return;
    }

    // 初期状態をコピー
    memcpy(temp, in, h * w * sizeof(double));

    // 4近傍の座標変化
    const int dx[] = {-1, 1, 0, 0};
    const int dy[] = {0, 0, -1, 1};

    // 収縮処理
    for (int iter = 0; iter < iterations; iter++) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                if (temp[y * w + x] == 1.0) {
                    int is_eroded = 0;
                    for (int k = 0; k < 4; k++) {
                        int nx = x + dx[k];
                        int ny = y + dy[k];
                        // 境界外アクセスを防ぐ
                        if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                            if (temp[ny * w + nx] == 0.0) {
                                is_eroded = 1;
                                break;
                            }
                        }
                    }
                    if (is_eroded) {
                        out[y * w + x] = 0.0;
                    } else {
                        out[y * w + x] = 1.0;
                    }
                } else {
                    out[y * w + x] = 0.0;
                }
            }
        }
        // 次の反復のために出力を一時領域にコピー
        memcpy(temp, out, h * w * sizeof(double));
    }

    // 一時領域を解放
    free(temp);
}
