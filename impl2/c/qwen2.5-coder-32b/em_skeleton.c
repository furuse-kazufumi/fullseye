#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を処理する方法: 境界外の画素は背景(0.0)と仮定する。
    // これは仕様書で明示されていないため、この選択を明記します。

    int y, x;
    int changes;
    double* temp = (double*)malloc(h * w * sizeof(double));

    // 初期化
    memcpy(out, in, h * w * sizeof(double));

    do {
        changes = 0;
        memcpy(temp, out, h * w * sizeof(double));

        for (y = 0; y < h; y++) {
            for (x = 0; x < w; x++) {
                if (out[y * w + x] == 1.0) {
                    int nb = 0; // 8近傍の前景画素数
                    int bg = 0; // 4近傍の背景画素数
                    int transitions = 0; // 0 -> 1 の遷移数

                    // 8近傍の前景画素数を数える
                    for (int dy = -1; dy <= 1; dy++) {
                        for (int dx = -1; dx <= 1; dx++) {
                            if (dy == 0 && dx == 0) continue;
                            int ny = y + dy;
                            int nx = x + dx;
                            if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                                if (temp[ny * w + nx] == 1.0) nb++;
                            }
                        }
                    }

                    // 4近傍の背景画素数と 0 -> 1 の遷移数を数える
                    for (int i = 0; i < 4; i++) {
                        int dy = (i == 0 || i == 3) ? -1 : 1;
                        int dx = (i == 0 || i == 1) ? 1 : -1;
                        int ny = y + dy;
                        int nx = x + dx;
                        int prev_ny = y + (i == 0 ? -1 : (i == 1 ? 1 : 0));
                        int prev_nx = x + (i == 1 ? 1 : (i == 2 ? -1 : 0));

                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            if (temp[ny * w + nx] == 0.0) bg++;
                        }
                        if (prev_ny >= 0 && prev_ny < h && prev_nx >= 0 && prev_nx < w) {
                            if (temp[prev_ny * w + prev_nx] == 0.0 && temp[ny * w + nx] == 1.0) transitions++;
                        }
                    }

                    // simple かつ perfect な画素を特定
                    if (nb >= 2 && nb <= 6 && transitions == 1 && bg == 1) {
                        out[y * w + x] = 0.0;
                        changes = 1;
                    }
                }
            }
        }
    } while (changes);

    free(temp);
}
