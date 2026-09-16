#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は矩形を内側へ縮める割合、b は未使用。b は無視する。
    // 入力画像は 0.0 か 1.0 の二値画像。1.0 が領域に属する画素を表す。

    // 出力画像は 0.0 か 1.0 の二値画像。1.0 が矩形領域を表す。

    // まず、入力画像から前景画素の位置を取得する。
    int* foreground_positions = (int*)malloc(h * w * sizeof(int));
    int fg_count = 0;

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) {
                foreground_positions[fg_count++] = y * w + x;
            }
        }
    }

    // 前景画素の位置から、矩形の高さと幅を計算する。
    int max_height = 0;
    int max_width = 0;

    for (int i = 0; i < fg_count; i++) {
        int y = foreground_positions[i] / w;
        int x = foreground_positions[i] % w;

        int height = 1;
        int width = 1;

        // 上方向に高さを増やす。
        while (y - height >= 0 && in[(y - height) * w + x] > 0.5) {
            height++;
        }

        // 下方向に高さを増やす。
        while (y + height < h && in[(y + height) * w + x] > 0.5) {
            height++;
        }

        // 左方向に幅を増やす。
        while (x - width >= 0 && in[y * w + x - width] > 0.5) {
            width++;
        }

        // 右方向に幅を増やす。
        while (x + width < w && in[y * w + x + width] > 0.5) {
            width++;
        }

        if (height > max_height) {
            max_height = height;
        }

        if (width > max_width) {
            max_width = width;
        }
    }

    // 矩形を内側へ縮める。
    int shrink_height = round(max_height * a * 0.3 / 2);
    int shrink_width = round(max_width * a * 0.3 / 2);

    max_height -= shrink_height * 2;
    max_width -= shrink_width * 2;

    // 出力画像を初期化する。
    memset(out, 0, h * w * sizeof(double));

    // 矩形領域を出力画像に描画する。
    for (int y = shrink_height; y < h - shrink_height; y++) {
        for (int x = shrink_width; x < w - shrink_width; x++) {
            if (y - shrink_height < max_height && x - shrink_width < max_width) {
                out[y * w + x] = 1.0;
            }
        }
    }

    // メモリを解放する。
    free(foreground_positions);
}
