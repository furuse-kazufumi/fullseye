#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 結構要素のサイズを計算 (3 + 2 * int(a * 3)) で、最小3、最大9
    int se_size = 3 + 2 * (int)(a * 3);
    if (se_size < 3) se_size = 3;
    if (se_size > 9) se_size = 9;

    // 結構要素の半径
    int se_radius = se_size / 2;

    // 開処理結果を一時的に保存する配列
    double* opened = (double*)malloc(h * w * sizeof(double));
    if (opened == NULL) return;

    // 各ピクセルに対して開処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = 1.0;
            for (int sy = -se_radius; sy <= se_radius; sy++) {
                for (int sx = -se_radius; sx <= se_radius; sx++) {
                    int ny = y + sy;
                    int nx = x + sx;
                    // 境界外のピクセルにはゼロを仮定 (境界処理)
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double val = in[ny * w + nx];
                        if (val < min_val) min_val = val;
                    }
                }
            }
            opened[y * w + x] = min_val;
        }
    }

    // トップハット変換: 元画像 - 開処理結果
    double max_diff = 0.0;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double diff = in[y * w + x] - opened[y * w + x];
            out[y * w + x] = diff;
            if (diff > max_diff) max_diff = diff;
        }
    }

    // 正規化: 出力を最大値で割る
    if (max_diff > 0.0) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                out[y * w + x] /= max_diff;
            }
        }
    }

    // 動的確保したメモリを解放
    free(opened);
}
