#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は半径を決めるパラメータ。b は未使用。
    int radius = 1 + (int)(a * 4);
    int struct_elem_size = 2 * radius + 1;

    // 構造要素の初期化
    int* struct_elem = (int*)malloc(struct_elem_size * struct_elem_size * sizeof(int));
    if (struct_elem == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 半径 r の円板を構造要素として作成
    for (int y = -radius; y <= radius; y++) {
        for (int x = -radius; x <= radius; x++) {
            if (pow(x, 2) + pow(y, 2) <= pow(radius, 2)) {
                struct_elem[(y + radius) * struct_elem_size + (x + radius)] = 1;
            } else {
                struct_elem[(y + radius) * struct_elem_size + (x + radius)] = 0;
            }
        }
    }

    // 画像の各画素に対して構造要素を適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0; // 初期化
            for (int sy = -radius; sy <= radius; sy++) {
                for (int sx = -radius; sx <= radius; sx++) {
                    int ny = y + sy;
                    int nx = x + sx;
                    // 画像の境界外の場合はスキップ
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) continue;
                    // 構造要素の画素が 1 で、画像の画素も 1 の場合のみ out に 1 を設定
                    if (struct_elem[(sy + radius) * struct_elem_size + (sx + radius)] == 1 && in[ny * w + nx] == 1) {
                        out[y * w + x] = 1;
                        break;
                    }
                }
                if (out[y * w + x] == 1) break;
            }
        }
    }

    free(struct_elem);
}
