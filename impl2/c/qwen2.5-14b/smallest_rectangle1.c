#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。無視する。
    (void)a;
    (void)b;

    // 入力画像の領域を表す 1 の位置を取得
    int* x_coords = (int*)malloc(h * w * sizeof(int));
    int* y_coords = (int*)malloc(h * w * sizeof(int));
    int count = 0;

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] == 1.0) {
                x_coords[count] = x;
                y_coords[count] = y;
                count++;
            }
        }
    }

    // 領域が空の場合、全ゼロを返す
    if (count == 0) {
        memset(out, 0, h * w * sizeof(double));
        free(x_coords);
        free(y_coords);
        return;
    }

    // 最小外接矩形の座標を計算
    int min_x = x_coords[0];
    int max_x = x_coords[0];
    int min_y = y_coords[0];
    int max_y = y_coords[0];

    for (int i = 1; i < count; i++) {
        if (x_coords[i] < min_x) min_x = x_coords[i];
        if (x_coords[i] > max_x) max_x = x_coords[i];
        if (y_coords[i] < min_y) min_y = y_coords[i];
        if (y_coords[i] > max_y) max_y = y_coords[i];
    }

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 最小外接矩形を描画
    for (int y = min_y; y <= max_y; y++) {
        for (int x = min_x; x <= max_x; x++) {
            out[y * w + x] = 1.0;
        }
    }

    // メモリを解放
    free(x_coords);
    free(y_coords);
}
