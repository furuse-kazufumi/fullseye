#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用なので無視する
    int iterations = (int)(a * 4.0); // a は [0,1] なので、4回まで反復する
    if (iterations < 0) iterations = 0;
    if (iterations > 4) iterations = 4;

    // 一時的な領域を確保
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        // メモリ確保に失敗した場合、出力を入力と同じにする
        memcpy(out, in, h * w * sizeof(double));
        return;
    }

    // 初期状態をコピー
    memcpy(temp, in, h * w * sizeof(double));

    // 4近傍の方向ベクトル
    int dx[] = {-1, 1, 0, 0};
    int dy[] = {0, 0, -1, 1};

    for (int iter = 0; iter < iterations; iter++) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                if (temp[y * w + x] == 1.0) {
                    for (int dir = 0; dir < 4; dir++) {
                        int nx = x + dx[dir];
                        int ny = y + dy[dir];
                        if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                            out[ny * w + nx] = 1.0;
                        }
                    }
                }
            }
        }
        // temp を out と交換
        memcpy(temp, out, h * w * sizeof(double));
    }

    // 最終結果を out にコピー
    memcpy(out, temp, h * w * sizeof(double));

    // 一時的な領域を解放
    free(temp);
}
