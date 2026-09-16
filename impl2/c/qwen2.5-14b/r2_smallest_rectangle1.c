#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。無視する。
    (void)a;
    (void)b;

    // 入力画像の高さと幅を取得
    int height = h;
    int width = w;

    // 入力画像の全画素数
    int num_pixels = height * width;

    // 出力画像を初期化
    memset(out, 0, num_pixels * sizeof(double));

    // 入力画像の最小・最大の行と列を求める
    int min_row = height;
    int max_row = -1;
    int min_col = width;
    int max_col = -1;

    // 入力画像を走査して最小・最大の行と列を求める
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            if (in[y * width + x] > 0.5) {
                if (y < min_row) min_row = y;
                if (y > max_row) max_row = y;
                if (x < min_col) min_col = x;
                if (x > max_col) max_col = x;
            }
        }
    }

    // 最小・最大の行と列が更新されていない場合、領域が存在しないと判断
    if (min_row == height || min_col == width) {
        return;
    }

    // 外接矩形を描画
    for (int y = min_row; y <= max_row; y++) {
        for (int x = min_col; x <= max_col; x++) {
            out[y * width + x] = 1.0;
        }
    }
}
