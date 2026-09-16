#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像のグリッドサイズを計算
    int grid_size = h * w;
    // 粒子の初期スケール K を計算
    int K = 4 + (int)(12 * a);
    // 粒子の最大値を計算
    double max_value = 0.0;

    // 画像を整数の粒高さに変換
    int* grains = (int*)malloc(grid_size * sizeof(int));
    for (int i = 0; i < grid_size; i++) {
        grains[i] = (int)round(K * in[i]);
        if (grains[i] > max_value) {
            max_value = grains[i];
        }
    }

    // 粒子の安定化ループ
    int sweep_count = 1 + (int)(50 * b);
    int budget = _SANDPILE_BUDGET; // 假设_SANDPILE_BUDGET为一个全局定义的常量，表示总工作预算
    for (int sweep = 0; sweep < sweep_count && budget > 0; sweep++) {
        int* new_grains = (int*)malloc(grid_size * sizeof(int));
        memcpy(new_grains, grains, grid_size * sizeof(int));

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int index = y * w + x;
                if (grains[index] >= 4) {
                    new_grains[index] -= 4;
                    if (x > 0) new_grains[index - 1]++;
                    if (x < w - 1) new_grains[index + 1]++;
                    if (y > 0) new_grains[index - w]++;
                    if (y < h - 1) new_grains[index + w]++;
                    budget -= 4; // 每次更新减少预算
                }
            }
        }
        free(grains);
        grains = new_grains;
    }

    // 最終的な粒高さを出力に変換
    for (int i = 0; i < grid_size; i++) {
        out[i] = (double)grains[i] / max_value;
    }

    free(grains);
}
