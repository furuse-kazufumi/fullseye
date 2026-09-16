#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端の処理は周期境界条件を採用する。
    // これは仕様書で明示的に指定されている。
    
    // ルールセットの選択
    int birth_rule = 3; // B3
    int survival_rule = 23; // S23
    if (a < 0.33) {
        birth_rule = 2; // B2
        survival_rule = 0; // S
    } else if (a < 0.67) {
        birth_rule = 36; // B36
        survival_rule = 23; // S23
    } else if (a < 1.0) {
        birth_rule = 3678; // B3678
        survival_rule = 34678; // S34678
    }

    // 世代数の計算
    int generations = (int)(9 * b) + 1;

    // 画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = (in[y * w + x] >= 0.5) ? 1.0 : 0.0;
        }
    }

    // ゲームの実行
    for (int gen = 0; gen < generations; gen++) {
        double* temp = (double*)malloc(h * w * sizeof(double));
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int live_neighbors = 0;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (dy == 0 && dx == 0) continue;
                        int ny = (y + dy + h) % h;
                        int nx = (x + dx + w) % w;
                        live_neighbors += (int)out[ny * w + nx];
                    }
                }
                if (out[y * w + x] == 0 && live_neighbors == birth_rule) {
                    temp[y * w + x] = 1.0;
                } else if (out[y * w + x] == 1 && (survival_rule & (1 << live_neighbors)) != 0) {
                    temp[y * w + x] = 1.0;
                } else {
                    temp[y * w + x] = 0.0;
                }
            }
        }
        free(out);
        out = temp;
    }
}
